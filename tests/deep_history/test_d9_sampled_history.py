from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from sampled_history import (
    acquire_g2a_baseline,
    benchmark_g2a_acquisitions,
    persist_sampled_intelligence,
)


class D9SampledHistoryTests(unittest.TestCase):
    def fixture(self, root: Path, now: int):
        option_path = Path("options/snapshots/2026/08/17") / f"{now}.json"
        liquidity_path = Path("liquidity/snapshots/2026/08/17") / f"{now}.json"
        option_path.parent.mkdir(parents=True, exist_ok=True)
        liquidity_path.parent.mkdir(parents=True, exist_ok=True)
        option_path.write_text("{}")
        liquidity_path.write_text("{}")
        return {
            "derivatives": {
                "providers": {
                    "deribit-perpetual": {
                        "status": "PASS",
                        "instruments": {
                            "ETH-PERPETUAL": {
                                "timestamp_ms": now - 1000,
                                "mark_price": 2000,
                                "index_price": 1999,
                                "open_interest": 10,
                                "current_funding": 0.0,
                                "funding_8h": 0.0,
                                "volume_24h": 100,
                                "volume_usd_24h": 200000,
                            }
                        },
                    }
                }
            },
            "options": {"providers": {"deribit": {"status": "PASS", "latest_surface": option_path.as_posix()}}},
            "liquidity": {"collection": {"status": "PASS", "latest_path": liquidity_path.as_posix()}},
        }

    @unittest.skipUnless(
        os.environ.get("GITHUB_REF")
        == "refs/heads/agent/g2a-s3-first-failure-diagnostic-r01",
        "actual network benchmark is branch-scoped qualification evidence",
    )
    def test_actual_g2a_six_capability_benchmark_qualification(self):
        acquisitions = acquire_g2a_baseline()
        benchmark = benchmark_g2a_acquisitions(acquisitions)
        self.assertEqual(benchmark["status"], "PASS")
        self.assertEqual(benchmark["capability_count"], 6)
        self.assertEqual(benchmark["history_target_bps"], "500")
        self.assertEqual(
            benchmark["serializer"],
            "src/sampled_history.py::serialize_durable_l2_observation",
        )
        public = {key: value for key, value in benchmark.items() if key != "records"}
        print(
            "G2A_ACTUAL_BENCHMARK_JSON="
            + json.dumps(public, sort_keys=True, separators=(",", ":"))
        )

    def test_sampled_state_and_ledger_are_durable_and_idempotent(self):
        now = 1786964700000
        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                intelligence = self.fixture(Path(temp), now)
                first = persist_sampled_intelligence(
                    intelligence,
                    expected_ms=now,
                    started_ms=now,
                    completed_ms=now + 2000,
                    target_cadence_seconds=3600,
                )
                second = persist_sampled_intelligence(
                    intelligence,
                    expected_ms=now,
                    started_ms=now,
                    completed_ms=now + 2000,
                    target_cadence_seconds=3600,
                )
                self.assertEqual(first["run_count"], 3)
                self.assertEqual(second["run_count"], 3)
                ledger = json.loads(Path(first["ledger_path"]).read_text())
                self.assertEqual(len(ledger["runs"]), 3)
                self.assertTrue(all(row["known_at"] and row["retrieved_at"] for row in ledger["runs"]))
                self.assertTrue(all("freshness" in row for row in ledger["runs"]))
                derivative_ref = next(row["snapshot_ref"] for row in ledger["runs"] if row["provider"] == "deribit-perpetual")
                snapshot = json.loads(Path(derivative_ref).read_text())
                self.assertEqual(snapshot["schema_version"], "market-data-sampled-observation/1.0.0")
                self.assertIn("ETH-PERPETUAL", snapshot["instruments"])
            finally:
                os.chdir(previous)

    def test_missing_sample_is_explicit_failure_not_synthetic_state(self):
        now = 1786964700000
        intelligence = {
            "derivatives": {"providers": {"deribit-perpetual": {"status": "DEGRADED"}}},
            "options": {"providers": {"deribit": {"status": "DEGRADED"}}},
            "liquidity": {"collection": {"status": "FAIL"}},
        }
        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                result = persist_sampled_intelligence(
                    intelligence,
                    expected_ms=now,
                    started_ms=now,
                    completed_ms=now + 1000,
                )
                ledger = json.loads(Path(result["ledger_path"]).read_text())
                self.assertEqual({row["status"] for row in ledger["runs"]}, {"PROVIDER_FAILURE"})
                self.assertTrue(all(row["snapshot_ref"] is None for row in ledger["runs"]))
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
