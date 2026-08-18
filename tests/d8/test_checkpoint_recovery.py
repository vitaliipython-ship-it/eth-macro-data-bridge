from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from d8_runtime import (
    CAPABILITY_POLICY,
    D8Runtime,
    D8State,
    DeterministicMockAcquisition,
    RuntimeConfig,
    StateError,
    cycle_id_for,
    fingerprint_payload,
    observation_id,
    utc_iso,
)

BASE_MS = int(datetime(2026, 8, 18, 11, 55, tzinfo=timezone.utc).timestamp() * 1000)
B_MS = BASE_MS + 5 * 60_000


def request(ms):
    return {
        "schema_version": "eth-macro-d8-collect-cycle-request/1.0.0",
        "expected_schedule_at": utc_iso(ms),
        "canonical_slot": "M5",
        "trace_id": "checkpoint-regression",
    }


class CrossCycleCore:
    def __init__(self):
        self.calls = {}
        self.crash_cycle = None
        self.crashed = False

    def collect(self, capability_id, *, expected_ms, cycle_id, staging_root):
        self.calls[(cycle_id, capability_id)] = self.calls.get((cycle_id, capability_id), 0) + 1
        if (
            cycle_id == self.crash_cycle
            and capability_id == "deribit-perpetual.current"
            and not self.crashed
        ):
            self.crashed = True
            raise StateError("STATE_IO: crash after multiple checkpoints")

        if capability_id == "binance-usdm.m5-current":
            rows = []
            daily_ts = "2026-08-18T00:00:00.000Z"
            for symbol, value in (("ETHUSDT", "X"), ("BTCUSDT", "Y")):
                rows.append(
                    {
                        "series_id": f"derivatives.binance-usdm.{symbol}.perp-ohlcv.1d",
                        "provider_timestamp_at": daily_ts,
                        "finality": "FINALIZED",
                        "freshness": {
                            "status": "LIVE_USABLE",
                            "age_seconds": 0,
                            "target_cadence_seconds": 86400,
                        },
                        "value": {"symbol": symbol, "bar": value},
                        "d9_target": "FIXED_GRID",
                    }
                )
            for idx in range(10):
                rows.append(
                    {
                        "series_id": f"derivatives.binance-usdm.fixture-{idx}",
                        "provider_timestamp_at": utc_iso(expected_ms),
                        "finality": "OBSERVED_STATE",
                        "freshness": {
                            "status": "LIVE_USABLE",
                            "age_seconds": 0,
                            "target_cadence_seconds": 300,
                        },
                        "value": {"slot_ms": expected_ms, "idx": idx},
                        "d9_target": "SAMPLED_SCHEDULE",
                    }
                )
            return {"status": "PASS", "observations": rows}

        provider = next(c["provider"] for c in CAPABILITY_POLICY if c["id"] == capability_id)
        return {
            "status": "PASS",
            "observations": [
                {
                    "series_id": f"fixture.{provider}.{capability_id}",
                    "provider_timestamp_at": utc_iso(expected_ms),
                    "finality": "FINALIZED",
                    "freshness": {
                        "status": "LIVE_USABLE",
                        "age_seconds": 0,
                        "target_cadence_seconds": 300,
                    },
                    "value": {"slot_ms": expected_ms, "capability": capability_id},
                    "d9_target": "FIXED_GRID",
                }
            ],
        }


class CheckpointRepairCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def cfg(self, profile="VPS_SHADOW"):
        return RuntimeConfig(
            state_root=self.root,
            profile=profile,
            source_revision="repair-fixture",
            lease_seconds=60,
        )

    def runtime(self, core, now_ms):
        return D8Runtime(self.cfg(), core, clock_ms=lambda: now_ms + 30_000)

    def _checkpoint_one(self):
        rt = self.runtime(DeterministicMockAcquisition(), BASE_MS)
        cid = cycle_id_for(utc_iso(BASE_MS))
        cap = next(c for c in CAPABILITY_POLICY if c["id"] == "binance-spot.m5")
        obs = rt._normalize_observations(
            cap,
            [{
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m",
                "provider_timestamp_at": utc_iso(BASE_MS),
                "finality": "FINALIZED",
                "freshness": {"status": "LIVE_USABLE", "age_seconds": 0, "target_cadence_seconds": 300},
                "value": {"close": "1900"},
            }],
            cid,
            utc_iso(BASE_MS),
            BASE_MS + 1_000,
        )
        with rt.state.connect() as db:
            db.execute(
                "INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,source_revision,runtime_revision) "
                "VALUES(?,?,?,?,?,?,?)",
                (cid, utc_iso(BASE_MS), utc_iso(BASE_MS), 1, "STARTED", "x", "x"),
            )
        ledger = rt._ledger_row(cap, "PASS", None, obs, BASE_MS + 1_000)
        rt.state.checkpoint_capability(
            cycle_id=cid,
            attempt=1,
            ledger_row=ledger,
            observations=obs,
            now_ms=BASE_MS + 1_000,
        )
        return rt, cid, cap["id"], obs

    def test_complete_checkpoint_restarts_without_provider_reacquisition_cross_cycle(self):
        core = CrossCycleCore()
        rt_a = self.runtime(core, BASE_MS)
        code_a, res_a = rt_a.collect_cycle(request(BASE_MS))
        self.assertEqual((code_a, res_a["overall_status"]), (200, "PASS"))

        cid_a = res_a["cycle_id"]
        cid_b = cycle_id_for(utc_iso(B_MS))
        core.crash_cycle = cid_b
        rt_b1 = self.runtime(core, B_MS)
        code_b1, _ = rt_b1.collect_cycle(request(B_MS))
        self.assertEqual(code_b1, 503)
        before_retry = core.calls[(cid_b, "binance-usdm.m5-current")]

        recovered, _ = rt_b1.state.load_checkpoint(cid_b, "binance-usdm.m5-current")
        self.assertEqual(len(recovered), 12)
        ids_b = [o["observation_id"] for o in recovered]
        self.assertEqual(len(ids_b), len(set(ids_b)))

        with rt_b1.state.connect() as db:
            members_a = {
                row[0] for row in db.execute(
                    "SELECT observation_id FROM cycle_checkpoint_observations "
                    "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current'",
                    (cid_a,),
                ).fetchall()
            }
            members_b = {
                row[0] for row in db.execute(
                    "SELECT observation_id FROM cycle_checkpoint_observations "
                    "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current'",
                    (cid_b,),
                ).fetchall()
            }
            self.assertEqual((len(members_a), len(members_b)), (12, 12))
            global_rows = db.execute(
                "SELECT observation_id,payload_json FROM spool "
                "WHERE capability_id='binance-usdm.m5-current'"
            ).fetchall()
        global_ids = {row["observation_id"] for row in global_rows}
        self.assertLess(len(global_ids), 24)

        rt_b2 = self.runtime(core, B_MS)
        code_b2, res_b = rt_b2.collect_cycle(request(B_MS))
        self.assertEqual((code_b2, res_b["overall_status"]), (200, "PASS"))
        self.assertTrue(
            res_b["capability_statuses"]["binance-usdm.m5-current"]["reused_durable_checkpoint"]
        )
        self.assertEqual(
            core.calls[(cid_b, "binance-usdm.m5-current")],
            before_retry,
        )

        with rt_b2.state.connect() as db:
            hot = json.loads(
                db.execute("SELECT payload_json FROM hot WHERE singleton=1").fetchone()[0]
            )
            hot_usdm = [
                o for o in hot["observations"]
                if o["capability_id"] == "binance-usdm.m5-current"
            ]
        self.assertEqual(len(hot_usdm), 12)
        self.assertTrue(all(o["canonical_cycle_id"] == cid_b for o in hot_usdm))
        self.assertTrue(all(o["canonical_slot"] == utc_iso(B_MS) for o in hot_usdm))

        daily = {
            o["series_id"]: o for o in hot_usdm
            if o["series_id"].endswith(".perp-ohlcv.1d")
        }
        self.assertEqual(len(daily), 2)
        daily_ids = {item["observation_id"] for item in daily.values()}
        self.assertTrue(daily_ids.issubset(members_a))
        self.assertTrue(daily_ids.issubset(members_b))
        for item in daily.values():
            with rt_b2.state.connect() as db:
                global_payload = json.loads(
                    db.execute(
                        "SELECT payload_json FROM spool WHERE observation_id=?",
                        (item["observation_id"],),
                    ).fetchone()[0]
                )
            self.assertEqual(global_payload["observation_id"], item["observation_id"])
            self.assertEqual(global_payload["canonical_cycle_id"], cid_a)
            self.assertEqual(item["canonical_cycle_id"], cid_b)
            self.assertEqual(item["canonical_slot"], utc_iso(B_MS))
            for field in ("retrieved_at", "known_at", "collected_at"):
                self.assertNotEqual(global_payload[field], item[field])

    def test_missing_membership_rejected_without_partial_reuse(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "DELETE FROM cycle_checkpoint_observations "
                "WHERE cycle_id=? AND capability_id=? AND position=0",
                (cid, cap),
            )
        recovered, ledger = rt.state.load_checkpoint(cid, cap)
        self.assertEqual(recovered, [])
        self.assertIsNone(ledger)

    def test_corrupt_payload_rejected(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "UPDATE cycle_checkpoint_observations SET payload_json='{}' "
                "WHERE cycle_id=? AND capability_id=? AND position=0",
                (cid, cap),
            )
        self.assertEqual(rt.state.load_checkpoint(cid, cap), ([], None))

    def test_expected_count_mismatch_rejected(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "UPDATE cycle_checkpoints SET expected_count=2 "
                "WHERE cycle_id=? AND capability_id=?",
                (cid, cap),
            )
        self.assertEqual(rt.state.load_checkpoint(cid, cap), ([], None))

    def test_membership_hash_mismatch_rejected(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "UPDATE cycle_checkpoints SET membership_sha256=? "
                "WHERE cycle_id=? AND capability_id=?",
                ("0" * 64, cid, cap),
            )
        self.assertEqual(rt.state.load_checkpoint(cid, cap), ([], None))

    def test_ledger_binding_mismatch_rejected(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "UPDATE capability_ledger SET known_at=? "
                "WHERE cycle_id=? AND capability_id=? AND attempt=1",
                ("2026-08-18T00:00:00.000Z", cid, cap),
            )
        self.assertEqual(rt.state.load_checkpoint(cid, cap), ([], None))

    def test_ledger_success_without_checkpoint_is_not_reusable(self):
        rt, cid, cap, _ = self._checkpoint_one()
        with rt.state.connect() as db:
            db.execute(
                "DELETE FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=?",
                (cid, cap),
            )
            db.execute(
                "DELETE FROM cycle_checkpoints WHERE cycle_id=? AND capability_id=?",
                (cid, cap),
            )
        recovered, ledger = rt.state.load_checkpoint(cid, cap)
        self.assertEqual(recovered, [])
        self.assertIsNone(ledger)

    def test_mark_forwarded_remains_global_observation_identity(self):
        rt, cid, cap, obs = self._checkpoint_one()
        oid = obs[0]["observation_id"]
        self.assertEqual(rt.state.mark_forwarded([oid], BASE_MS + 60_000), 1)
        self.assertEqual(rt.state.mark_forwarded([oid], BASE_MS + 60_001), 0)
        with rt.state.connect() as db:
            rows = db.execute(
                "SELECT COUNT(*) FROM spool WHERE observation_id=? AND state='FORWARDED'",
                (oid,),
            ).fetchone()[0]
        self.assertEqual(rows, 1)

    def test_v1_migration_is_additive_idempotent_and_safe_reacquire(self):
        db_path = self.root / "d8-runtime.sqlite3"
        db = sqlite3.connect(db_path)
        db.executescript(
            """
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta VALUES('state_schema_version','1');
            CREATE TABLE cycles(
              cycle_id TEXT PRIMARY KEY, slot TEXT UNIQUE NOT NULL, expected_at TEXT NOT NULL,
              attempt INTEGER NOT NULL, status TEXT NOT NULL, started_at TEXT, completed_at TEXT,
              response_json TEXT, source_revision TEXT NOT NULL, runtime_revision TEXT NOT NULL);
            CREATE TABLE leases(
              slot TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, owner_id TEXT NOT NULL,
              acquired_at INTEGER NOT NULL, lease_until INTEGER NOT NULL);
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
            """
        )
        pass_slot = "2026-08-18T11:50:00.000Z"
        pass_response = json.dumps({
            "cycle_id": "legacy-pass",
            "overall_status": "PASS",
            "completed_at": pass_slot,
        })
        db.execute(
            "INSERT INTO cycles VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("legacy-pass", pass_slot, pass_slot, 1, "PASS", pass_slot, pass_slot, pass_response, "old", "old"),
        )
        recover_slot = "2026-08-18T11:55:00.000Z"
        db.execute(
            "INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,source_revision,runtime_revision) "
            "VALUES(?,?,?,?,?,?,?)",
            ("legacy-recover", recover_slot, recover_slot, 1, "COLLECTED", "old", "old"),
        )
        for oid, state in (("pending-id", "PENDING"), ("forwarded-id", "FORWARDED")):
            payload = json.dumps({"observation_id": oid})
            db.execute(
                "INSERT INTO spool VALUES(?,?,?,?,?,?,?,?)",
                (oid, "legacy-recover", "binance-spot.m5", payload, len(payload), BASE_MS, BASE_MS + 9999999, state),
            )
        db.execute(
            "INSERT INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-recover", "binance-spot.m5", 1, "binance-spot", "OBSERVED_STATE", None,
                utc_iso(BASE_MS), utc_iso(BASE_MS), utc_iso(BASE_MS), utc_iso(BASE_MS),
                "legacy-fingerprint", "pending-id", "PENDING", "{}", None, "old", "old",
            ),
        )
        hot_payload = json.dumps({"cycle_id": "legacy-pass", "observations": []})
        db.execute(
            "INSERT INTO hot VALUES(?,?,?,?)",
            (1, "legacy-pass", pass_slot, hot_payload),
        )
        db.commit()
        db.close()

        state1 = D8State(self.cfg())
        with state1.connect() as db2:
            self.assertEqual(
                db2.execute("SELECT value FROM meta WHERE key='state_schema_version'").fetchone()[0],
                "2",
            )
            self.assertEqual(db2.execute("SELECT COUNT(*) FROM spool").fetchone()[0], 2)
            self.assertEqual(
                db2.execute("SELECT state FROM spool WHERE observation_id='forwarded-id'").fetchone()[0],
                "FORWARDED",
            )
            self.assertEqual(db2.execute("SELECT cycle_id FROM hot WHERE singleton=1").fetchone()[0], "legacy-pass")
            self.assertEqual(db2.execute("SELECT COUNT(*) FROM capability_ledger").fetchone()[0], 1)
            self.assertEqual(db2.execute("SELECT COUNT(*) FROM cycle_checkpoints").fetchone()[0], 0)

        owner, prior, attempt, _ = state1.acquire(
            slot=pass_slot, cycle_id="legacy-pass", now_ms=BASE_MS
        )
        self.assertEqual(owner, "REPLAY")
        self.assertEqual(prior["overall_status"], "PASS")
        self.assertEqual(attempt, 1)
        self.assertEqual(state1.load_checkpoint("legacy-recover", "binance-spot.m5"), ([], None))

        # Second open is an idempotent no-op on preserved data.
        state2 = D8State(self.cfg())
        with state2.connect() as db3:
            self.assertEqual(db3.execute("SELECT COUNT(*) FROM spool").fetchone()[0], 2)
            self.assertEqual(db3.execute("SELECT COUNT(*) FROM hot").fetchone()[0], 1)
            self.assertEqual(db3.execute("SELECT COUNT(*) FROM capability_ledger").fetchone()[0], 1)
            self.assertEqual(db3.execute("SELECT COUNT(*) FROM cycle_checkpoints").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
