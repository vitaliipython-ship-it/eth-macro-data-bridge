from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from d8_d9_forwarder import D8ToD9Forwarder, ForwardContractError, InjectedForwardCrash


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def observation_id(provider, series_id, provider_timestamp_at, fp):
    raw = f"{provider}|{series_id}|{provider_timestamp_at or 'NONE'}|{fp}".encode()
    return "obs-" + hashlib.sha256(raw).hexdigest()


class D8D9ForwarderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_root = self.root / "state"
        self.warm_root = self.root / "history"
        self.state_root.mkdir()
        self.db_path = self.state_root / "d8-runtime.sqlite3"
        self._create_state()
        self.forwarder = D8ToD9Forwarder(self.state_root, self.warm_root)

    def tearDown(self):
        self.tmp.cleanup()

    def _db(self):
        db = sqlite3.connect(self.db_path, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        return db

    def _create_state(self):
        with sqlite3.connect(self.db_path, factory=ClosingConnection) as db:
            db.executescript("""
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta(key,value) VALUES('state_schema_version','2');
            CREATE TABLE cycles(
              cycle_id TEXT PRIMARY KEY, slot TEXT UNIQUE NOT NULL, expected_at TEXT NOT NULL,
              attempt INTEGER NOT NULL, status TEXT NOT NULL, started_at TEXT, completed_at TEXT,
              response_json TEXT, source_revision TEXT NOT NULL, runtime_revision TEXT NOT NULL);
            CREATE TABLE spool(
              observation_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL,
              payload_json TEXT NOT NULL, payload_bytes INTEGER NOT NULL, created_at INTEGER NOT NULL,
              expires_at INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING');
            CREATE TABLE capability_ledger(
              cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL, attempt INTEGER NOT NULL,
              provider TEXT NOT NULL, status TEXT NOT NULL, failure_class TEXT,
              provider_timestamp_at TEXT, retrieved_at TEXT NOT NULL, known_at TEXT NOT NULL,
              collected_at TEXT NOT NULL, fingerprint TEXT, spool_ref TEXT,
              promotion_result TEXT NOT NULL, freshness_json TEXT NOT NULL, gap_semantics TEXT,
              source_revision TEXT NOT NULL, runtime_revision TEXT NOT NULL,
              PRIMARY KEY(cycle_id, capability_id, attempt));
            CREATE TABLE hot(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), cycle_id TEXT NOT NULL,
              promoted_at TEXT NOT NULL, payload_json TEXT NOT NULL);
            """)

    def _insert_cycle(self, cycle_id="cycle-1", attempt=1, statuses=None):
        slot = "2026-08-18T17:00:00.000Z"
        if statuses is None:
            statuses = {"binance-spot.m5": {"status": "PASS", "provider": "binance-spot"}}
        response = {
            "schema_version": "eth-macro-d8-collect-cycle-response/1.0.0",
            "cycle_id": cycle_id,
            "expected_schedule_at": slot,
            "overall_status": "PASS",
            "capability_statuses": statuses,
            "completed_at": "2026-08-18T17:00:03.000Z",
        }
        with self._db() as db:
            db.execute(
                "INSERT INTO cycles VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    cycle_id, slot, slot, attempt, "PASS",
                    "2026-08-18T17:00:01.000Z", "2026-08-18T17:00:03.000Z",
                    json.dumps(response), "source-parent", "eth-macro-d8-runtime/1.0.0",
                ),
            )

    def _envelope(
        self,
        *,
        capability="binance-spot.m5",
        provider="binance-spot",
        series="spot.binance-spot.ETHUSDT.ohlcv.5m",
        target="FIXED_GRID",
        value=None,
        finality="FINALIZED",
        cycle_id="cycle-1",
        provider_timestamp="2026-08-18T16:55:00.000Z",
        known_at="2026-08-18T17:00:02.000Z",
        source_revision="source-parent",
    ):
        if value is None:
            value = {
                "open_time_ms": 1787072100000,
                "open": "1800",
                "high": "1810",
                "low": "1795",
                "close": "1805",
                "volume": "12.5",
                "closed": True,
            }
        fp = fingerprint(value)
        oid = observation_id(provider, series, provider_timestamp, fp)
        return {
            "schema_version": "market-data-d8-runtime-observation/1.0.0",
            "observation_id": oid,
            "fingerprint": fp,
            "provider": provider,
            "source_identity": provider,
            "capability_id": capability,
            "series_id": series,
            "provider_timestamp_at": provider_timestamp,
            "retrieved_at": "2026-08-18T17:00:02.000Z",
            "known_at": known_at,
            "collected_at": "2026-08-18T17:00:02.000Z",
            "canonical_cycle_id": cycle_id,
            "canonical_slot": "2026-08-18T17:00:00.000Z",
            "finality": finality,
            "freshness": {"status": "LIVE_USABLE", "age_seconds": 300, "target_cadence_seconds": 300},
            "validation_status": "PASS",
            "provenance": {
                "runtime_contract": "eth-macro-d8-runtime/1.0.0",
                "source_revision": source_revision,
                "provider_route": "fixture",
            },
            "d9_forward_seam": {
                "identity_preserved": True,
                "known_at_preserved": True,
                "finality_preserved": True,
                "collection_gap_compatible": True,
                "target": target,
            },
            "value": value,
        }

    def _insert_observation(self, envelope, *, attempt=1, created_at=1787072403000):
        with self._db() as db:
            raw = canonical_json(envelope)
            db.execute(
                "INSERT INTO spool(observation_id,cycle_id,capability_id,payload_json,payload_bytes,created_at,expires_at,state) "
                "VALUES(?,?,?,?,?,?,?,'PENDING')",
                (
                    envelope["observation_id"], envelope["canonical_cycle_id"], envelope["capability_id"],
                    raw, len(raw.encode()), created_at, created_at + 604800000,
                ),
            )
            db.execute(
                "INSERT OR IGNORE INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    envelope["canonical_cycle_id"], envelope["capability_id"], attempt,
                    envelope["provider"], "OBSERVED_STATE", None,
                    envelope["provider_timestamp_at"], envelope["retrieved_at"], envelope["known_at"],
                    envelope["collected_at"], envelope["fingerprint"], envelope["observation_id"],
                    "PROMOTED", json.dumps(envelope["freshness"]), None,
                    envelope["provenance"]["source_revision"], "eth-macro-d8-runtime/1.0.0",
                ),
            )

    def _spool_state(self, oid):
        with self._db() as db:
            return db.execute("SELECT state FROM spool WHERE observation_id=?", (oid,)).fetchone()[0]

    def _warm_records(self):
        paths = list((self.warm_root / "d8-origin").rglob("*.json"))
        records = []
        for path in paths:
            records.extend(json.loads(path.read_text())["observations"])
        return records

    def test_basic_pending_to_warm_to_forwarded(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        result = self.forwarder.forward_pending(now_ms=1787072405000)
        self.assertEqual(result["ack_state"], "ACKED")
        self.assertEqual(result["provider_reacquisition_count"], 0)
        self.assertEqual(self._spool_state(env["observation_id"]), "FORWARDED")
        self.assertEqual(self._warm_records(), [env])

    def test_same_observation_twice_has_one_warm_identity(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        self.forwarder.forward_pending(now_ms=1787072405000)
        with self._db() as db:
            db.execute("UPDATE spool SET state='PENDING' WHERE observation_id=?", (env["observation_id"],))
        result = self.forwarder.forward_pending(now_ms=1787072406000)
        self.assertEqual(result["already_present_observation_ids"], [env["observation_id"]])
        self.assertEqual(len(self._warm_records()), 1)

    def test_duplicate_batch_does_not_duplicate_warm(self):
        self._insert_cycle()
        first = self._envelope(series="spot.binance-spot.ETHUSDT.ohlcv.5m")
        second = self._envelope(
            series="spot.binance-spot.BTCUSDT.ohlcv.5m",
            value={**first["value"], "close": "60000"},
        )
        self._insert_observation(first, created_at=1)
        self._insert_observation(second, created_at=2)
        self.forwarder.forward_pending(now_ms=1787072405000)
        with self._db() as db:
            db.execute("UPDATE spool SET state='PENDING'")
        self.forwarder.forward_pending(now_ms=1787072406000)
        self.assertEqual(len(self._warm_records()), 2)

    def test_crash_before_warm_commit_preserves_pending(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        def crash(point):
            if point == "before_warm_commit":
                raise InjectedForwardCrash(point)
        with self.assertRaises(InjectedForwardCrash):
            self.forwarder.forward_pending(now_ms=1787072405000, failpoint=crash)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")
        self.assertEqual(self._warm_records(), [])

    def test_crash_after_warm_before_ack_retries_safely(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        def crash(point):
            if point == "after_warm_commit_before_ack":
                raise InjectedForwardCrash(point)
        with self.assertRaises(InjectedForwardCrash):
            self.forwarder.forward_pending(now_ms=1787072405000, failpoint=crash)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")
        self.assertEqual(len(self._warm_records()), 1)
        result = self.forwarder.forward_pending(now_ms=1787072406000)
        self.assertEqual(result["already_present_observation_ids"], [env["observation_id"]])
        self.assertEqual(self._spool_state(env["observation_id"]), "FORWARDED")
        self.assertEqual(len(self._warm_records()), 1)

    def test_immutable_identity_conflict_fails_closed(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        self.forwarder.forward_pending(now_ms=1787072405000)
        path = next((self.warm_root / "d8-origin").rglob("*.json"))
        payload = json.loads(path.read_text())
        payload["observations"][0]["known_at"] = "2026-08-18T17:00:09.000Z"
        path.write_text(json.dumps(payload))
        with self._db() as db:
            db.execute("UPDATE spool SET state='PENDING' WHERE observation_id=?", (env["observation_id"],))
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072406000)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")

    def test_corrupt_fingerprint_fails_closed(self):
        self._insert_cycle()
        env = self._envelope()
        env["fingerprint"] = "0" * 64
        with self._db() as db:
            raw = canonical_json(env)
            db.execute(
                "INSERT INTO spool VALUES(?,?,?,?,?,?,?,'PENDING')",
                (env["observation_id"], env["canonical_cycle_id"], env["capability_id"], raw, len(raw), 1, 9999999999999),
            )
            db.execute(
                "INSERT OR IGNORE INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (env["canonical_cycle_id"], env["capability_id"], 1, env["provider"], "OBSERVED_STATE", None,
                 env["provider_timestamp_at"], env["retrieved_at"], env["known_at"], env["collected_at"],
                 env["fingerprint"], env["observation_id"], "PROMOTED", json.dumps(env["freshness"]), None,
                 "source-parent", "eth-macro-d8-runtime/1.0.0"),
            )
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072405000)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")

    def test_schema_mismatch_fails_closed(self):
        self._insert_cycle()
        env = self._envelope()
        env["schema_version"] = "wrong"
        self._insert_observation(env)
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072405000)

    def test_collection_gap_and_not_due_are_preserved_without_synthetic_observation(self):
        statuses = {
            "binance-spot.m5": {"status": "PASS", "provider": "binance-spot"},
            "kraken-spot.m5": {"status": "FAIL", "provider": "kraken-spot"},
            "kraken-futures.analytics": {"status": "NOT_DUE", "provider": "kraken-futures"},
        }
        self._insert_cycle(statuses=statuses)
        env = self._envelope()
        self._insert_observation(env)
        with self._db() as db:
            db.execute(
                "INSERT OR IGNORE INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "cycle-1", "kraken-spot.m5", 1, "kraken-spot", "PROVIDER_FAILURE", "PROVIDER_TIMEOUT",
                    None, "2026-08-18T17:00:02.000Z", "2026-08-18T17:00:02.000Z",
                    "2026-08-18T17:00:02.000Z", None, None, "NOT_PROMOTED",
                    json.dumps({"status": "COLLECTION_GAP", "age_seconds": None, "target_cadence_seconds": 300}),
                    "COLLECTION_GAP_NO_SYNTHETIC_FILL", "source-parent", "eth-macro-d8-runtime/1.0.0",
                ),
            )
        self.forwarder.forward_pending(now_ms=1787072405000)
        ledger_path = next((self.warm_root / "collection-runs").rglob("runs.json"))
        runs = json.loads(ledger_path.read_text())["runs"]
        statuses = {row["series_or_capability"]: row["status"] for row in runs}
        self.assertEqual(statuses["kraken-spot.m5"], "PROVIDER_FAILURE")
        self.assertEqual(statuses["kraken-futures.analytics"], "NOT_DUE")
        self.assertEqual(len(self._warm_records()), 1)
        self.assertTrue(all(row["synthetic_fill"] is False for row in runs))

    def test_validation_failure_remains_distinct(self):
        statuses = {
            "binance-spot.m5": {"status": "PASS", "provider": "binance-spot"},
            "kraken-spot.m5": {"status": "FAIL", "provider": "kraken-spot"},
        }
        self._insert_cycle(statuses=statuses)
        env = self._envelope()
        self._insert_observation(env)
        with self._db() as db:
            db.execute(
                "INSERT OR IGNORE INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("cycle-1","kraken-spot.m5",1,"kraken-spot","PROVIDER_FAILURE","VALIDATION_FAILED",None,
                 "2026-08-18T17:00:02.000Z","2026-08-18T17:00:02.000Z","2026-08-18T17:00:02.000Z",
                 None,None,"NOT_PROMOTED",json.dumps({"status":"COLLECTION_GAP"}),"COLLECTION_GAP_NO_SYNTHETIC_FILL",
                 "source-parent","eth-macro-d8-runtime/1.0.0"),
            )
        self.forwarder.forward_pending(now_ms=1787072405000)
        ledger_path = next((self.warm_root / "collection-runs").rglob("runs.json"))
        runs = json.loads(ledger_path.read_text())["runs"]
        row = next(r for r in runs if r["series_or_capability"] == "kraken-spot.m5")
        self.assertEqual(row["status"], "VALIDATION_FAILURE")
        self.assertEqual(row["error_class"], "VALIDATION_FAILED")

    def test_known_at_finality_and_provenance_are_byte_semantically_preserved(self):
        self._insert_cycle()
        env = self._envelope(known_at="2026-08-18T17:00:02.123Z", source_revision="old-source")
        self._insert_observation(env)
        self.forwarder.forward_pending(now_ms=1787072405000)
        row = self._warm_records()[0]
        self.assertEqual(row["observation_id"], env["observation_id"])
        self.assertEqual(row["known_at"], env["known_at"])
        self.assertEqual(row["finality"], "FINALIZED")
        self.assertEqual(row["provenance"], env["provenance"])

    def test_fixed_grid_and_sampled_schedule_have_distinct_warm_mapping(self):
        self._insert_cycle(statuses={
            "binance-spot.m5":{"status":"PASS","provider":"binance-spot"},
            "deribit-perpetual.current":{"status":"PASS","provider":"deribit-perpetual"},
        })
        fixed = self._envelope()
        sampled = self._envelope(
            capability="deribit-perpetual.current",
            provider="deribit-perpetual",
            series="derivatives.deribit-perpetual.ETH-PERPETUAL.current",
            target="SAMPLED_SCHEDULE",
            value={"mark_price": "1805"},
            finality="OBSERVED_STATE",
        )
        self._insert_observation(fixed, created_at=1)
        self._insert_observation(sampled, created_at=2)
        self.forwarder.forward_pending(now_ms=1787072405000)
        paths = [p.as_posix() for p in (self.warm_root / "d8-origin").rglob("*.json")]
        self.assertTrue(any("fixed-grid" in p for p in paths))
        self.assertTrue(any("sampled-schedule" in p for p in paths))

    def test_no_provider_reacquisition_surface(self):
        source = Path(__import__("d8_d9_forwarder").__file__).read_text()
        self.assertNotIn("acquisition_core", source)
        self.assertNotIn("collector import", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)

    def test_internal_hot_read_is_read_only_and_not_agent_api(self):
        self._insert_cycle()
        env = self._envelope()
        hot = {
            "schema_version": "eth-macro-d8-hot/1.0.0",
            "cycle_id": "cycle-1",
            "slot": "2026-08-18T17:00:00.000Z",
            "observations": [env],
        }
        with self._db() as db:
            db.execute("INSERT INTO hot VALUES(1,?,?,?)", ("cycle-1","2026-08-18T17:00:03.000Z",canonical_json(hot)))
        result = self.forwarder.read_hot_snapshot()
        self.assertEqual(result["transport_contract"], "d8-hot-internal-physical-source/1.0.0")
        self.assertFalse(result["agent_facing"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["payload"], hot)

    def test_state_schema_mismatch_fails_closed(self):
        with self._db() as db:
            db.execute("UPDATE meta SET value='3' WHERE key='state_schema_version'")
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending()

    def test_wrong_lifecycle_mapping_fails_closed(self):
        self._insert_cycle()
        env = self._envelope(target="SAMPLED_SCHEDULE")
        self._insert_observation(env)
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending()


if __name__ == "__main__":
    unittest.main()
