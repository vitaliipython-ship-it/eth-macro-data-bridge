from __future__ import annotations

import hashlib
import json
import sqlite3

from d8_d9_forwarder import ForwardContractError
from d8_d9_forwarder_integrity import D8ToD9Forwarder
from tests.d8.test_d8_d9_forwarder import D8D9ForwarderCase, canonical_json


def ledger_binding(row):
    bound = {
        "capability_id": row["capability_id"],
        "provider": row["provider"],
        "status": row["status"],
        "failure_class": row.get("failure_class"),
        "provider_timestamp_at": row.get("provider_timestamp_at"),
        "retrieved_at": row["retrieved_at"],
        "known_at": row["known_at"],
        "collected_at": row["collected_at"],
        "fingerprint": row.get("fingerprint"),
        "spool_ref": row.get("spool_ref"),
        "freshness": row["freshness"],
        "gap_semantics": row.get("gap_semantics"),
    }
    return hashlib.sha256(canonical_json(bound).encode()).hexdigest()


class D8D9ForwarderIntegrityCase(D8D9ForwarderCase):
    """Run the original 16-case matrix through the integrity-bound successor."""

    def _create_state(self):
        super()._create_state()
        with sqlite3.connect(self.db_path) as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS cycle_checkpoints(
                  cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL, checkpoint_attempt INTEGER NOT NULL,
                  expected_count INTEGER NOT NULL, membership_sha256 TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                  ledger_sha256 TEXT NOT NULL, created_at INTEGER NOT NULL,
                  PRIMARY KEY(cycle_id, capability_id));
                CREATE TABLE IF NOT EXISTS cycle_checkpoint_observations(
                  cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL, position INTEGER NOT NULL,
                  observation_id TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                  PRIMARY KEY(cycle_id, capability_id, position),
                  UNIQUE(cycle_id, capability_id, observation_id));
                """
            )

    def setUp(self):
        super().setUp()
        self.forwarder = D8ToD9Forwarder(self.state_root, self.warm_root)

    def _insert_observation(self, envelope, *, attempt=1, created_at=1787072403000):
        super()._insert_observation(envelope, attempt=attempt, created_at=created_at)
        self._refresh_checkpoint(envelope["canonical_cycle_id"], envelope["capability_id"], attempt)

    def _refresh_checkpoint(self, cycle_id, capability_id, attempt=1):
        with self._db() as db:
            rows = db.execute(
                "SELECT observation_id,payload_json FROM spool WHERE cycle_id=? AND capability_id=? "
                "ORDER BY created_at,observation_id",
                (cycle_id, capability_id),
            ).fetchall()
            payloads = [json.loads(row["payload_json"]) for row in rows]
            observation_ids = [row["observation_id"] for row in rows]
            ledger = db.execute(
                "SELECT * FROM capability_ledger WHERE cycle_id=? AND capability_id=? AND attempt=?",
                (cycle_id, capability_id, attempt),
            ).fetchone()
            self.assertIsNotNone(ledger)
            ledger_view = {
                "capability_id": capability_id,
                "provider": ledger["provider"],
                "status": ledger["status"],
                "failure_class": ledger["failure_class"],
                "provider_timestamp_at": ledger["provider_timestamp_at"],
                "retrieved_at": ledger["retrieved_at"],
                "known_at": ledger["known_at"],
                "collected_at": ledger["collected_at"],
                "fingerprint": ledger["fingerprint"],
                "spool_ref": ledger["spool_ref"],
                "freshness": json.loads(ledger["freshness_json"]),
                "gap_semantics": ledger["gap_semantics"],
            }
            db.execute(
                "DELETE FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=?",
                (cycle_id, capability_id),
            )
            db.execute(
                "DELETE FROM cycle_checkpoints WHERE cycle_id=? AND capability_id=?",
                (cycle_id, capability_id),
            )
            membership_sha = hashlib.sha256(canonical_json(observation_ids).encode()).hexdigest()
            payload_sha = hashlib.sha256(canonical_json(payloads).encode()).hexdigest()
            db.execute(
                "INSERT INTO cycle_checkpoints VALUES(?,?,?,?,?,?,?,?)",
                (cycle_id, capability_id, attempt, len(rows), membership_sha, payload_sha, ledger_binding(ledger_view), 1787072403000),
            )
            for position, row in enumerate(rows):
                payload_json = row["payload_json"]
                db.execute(
                    "INSERT INTO cycle_checkpoint_observations VALUES(?,?,?,?,?,?)",
                    (
                        cycle_id,
                        capability_id,
                        position,
                        row["observation_id"],
                        payload_json,
                        hashlib.sha256(payload_json.encode()).hexdigest(),
                    ),
                )

    def test_spool_observation_requires_complete_checkpoint_v2_membership(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        with self._db() as db:
            db.execute(
                "DELETE FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=?",
                (env["canonical_cycle_id"], env["capability_id"]),
            )
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072405000)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")

    def test_checkpoint_cycle_local_payload_must_match_spool_envelope(self):
        self._insert_cycle()
        env = self._envelope()
        self._insert_observation(env)
        with self._db() as db:
            row = db.execute(
                "SELECT payload_json FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=?",
                (env["canonical_cycle_id"], env["capability_id"]),
            ).fetchone()
            changed = json.loads(row[0])
            changed["known_at"] = "2026-08-18T17:00:09.000Z"
            changed_json = canonical_json(changed)
            db.execute(
                "UPDATE cycle_checkpoint_observations SET payload_json=?,payload_sha256=? "
                "WHERE cycle_id=? AND capability_id=?",
                (
                    changed_json,
                    hashlib.sha256(changed_json.encode()).hexdigest(),
                    env["canonical_cycle_id"],
                    env["capability_id"],
                ),
            )
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072405000)
        self.assertEqual(self._spool_state(env["observation_id"]), "PENDING")

    def test_gap_only_terminal_cycle_materializes_collection_run_without_observation(self):
        statuses = {
            "kraken-spot.m5": {"status": "FAIL", "provider": "kraken-spot"},
            "kraken-futures.analytics": {"status": "NOT_DUE", "provider": "kraken-futures"},
        }
        self._insert_cycle(statuses=statuses)
        with self._db() as db:
            db.execute(
                "INSERT INTO capability_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "cycle-1", "kraken-spot.m5", 1, "kraken-spot", "PROVIDER_FAILURE", "PROVIDER_TIMEOUT",
                    None, "2026-08-18T17:00:02.000Z", "2026-08-18T17:00:02.000Z",
                    "2026-08-18T17:00:02.000Z", None, None, "NOT_PROMOTED",
                    json.dumps({"status": "COLLECTION_GAP", "age_seconds": None, "target_cadence_seconds": 300}),
                    "COLLECTION_GAP_NO_SYNTHETIC_FILL", "source-parent", "eth-macro-d8-runtime/1.0.0",
                ),
            )
        result = self.forwarder.forward_pending(now_ms=1787072405000)
        self.assertEqual(result["ack_state"], "NOOP")
        self.assertEqual(result["provider_reacquisition_count"], 0)
        self.assertEqual(result["durable_commit_status"], "COMMITTED")
        self.assertEqual(self._warm_records(), [])
        ledger_path = next((self.warm_root / "collection-runs").rglob("runs.json"))
        runs = json.loads(ledger_path.read_text())["runs"]
        statuses = {row["series_or_capability"]: row["status"] for row in runs}
        self.assertEqual(statuses["kraken-spot.m5"], "PROVIDER_FAILURE")
        self.assertEqual(statuses["kraken-futures.analytics"], "NOT_DUE")
        second = self.forwarder.forward_pending(now_ms=1787072406000)
        self.assertEqual(second["durable_commit_status"], "NOOP")
        self.assertEqual(len(json.loads(ledger_path.read_text())["runs"]), 2)

    def test_binance_usdm_lifecycle_target_is_series_bound(self):
        self._insert_cycle(statuses={"binance-usdm.m5-current": {"status": "PASS", "provider": "binance-usdm"}})
        env = self._envelope(
            capability="binance-usdm.m5-current",
            provider="binance-usdm",
            series="derivatives.binance-usdm.ETHUSDT.perp-ohlcv.5m",
            target="SAMPLED_SCHEDULE",
            value=[1787072100000, "1", "2", "0.5", "1.5", "10", 1787072399999],
        )
        self._insert_observation(env)
        with self.assertRaises(ForwardContractError):
            self.forwarder.forward_pending(now_ms=1787072405000)


if __name__ == "__main__":
    import unittest

    unittest.main()
