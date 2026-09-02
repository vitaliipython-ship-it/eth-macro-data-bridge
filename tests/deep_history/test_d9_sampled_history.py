from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from canonical_json import sha256_canonical_json
from history_store import ImmutableHistoryConflict
from sampled_history import (
    acquire_g2a_baseline,
    apply_fresh_current_durable_observation_artifact,
    benchmark_g2a_acquisitions,
    build_fresh_current_durable_observation_artifact,
    durable_partition_path,
    persist_durable_l2_observation,
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

    def durable_record(self, *, observation_sha: str = "a" * 64) -> dict:
        record = {
            "schema_version": "liquidity-durable-l2-observation/1.0.0",
            "history_family": "liquidity.orderbook-snapshots",
            "provider_id": "binance-spot",
            "instrument_id": "ETHUSDT",
            "book_kind": "L2_LEVEL_BOOK",
            "observation_id": "fixture-observation",
            "observation_sha256": observation_sha,
            "durable_identity_sha256": "d" * 64,
            "observation_time_ms": 1786964700000,
            "observation_time_utc": "2026-08-17T09:45:00.000Z",
            "known_at_utc": "2026-08-17T09:45:01.000Z",
            "observation_time_role": "MARKET_OBSERVATION_TIME",
            "known_at_role": "WHEN_THE_OBSERVATION_BECAME_KNOWN_TO_THE_EXECUTION_PATH",
            "generation_time_is_observation_time": False,
            "publication_time_is_observation_time": False,
            "request_time_is_observation_time": False,
            "coverage": {
                "history_target_bps": "500",
                "achieved_bid_coverage_bps": "230",
                "achieved_ask_coverage_bps": "410",
                "coverage_complete_bid": False,
                "coverage_complete_ask": False,
                "truncated": True,
                "extrapolation_allowed": False,
            },
            "quantity_semantics": {"mode": "NATIVE_FIRST"},
            "normalized_book": {"observation_sha256": observation_sha},
            "provenance": {
                "capability_series_id": "liquidity.binance-spot.ETHUSDT.orderbook",
                "provider_plan_sha256": "1" * 64,
                "provider_capability_sha256": "2" * 64,
                "s3_execution_policy_sha256": "3" * 64,
                "s3_execution_receipt_sha256": "4" * 64,
                "provider_endpoint_binding_sha256": "5" * 64,
                "physical_action_sha256": "6" * 64,
                "one_observation_proof": True,
                "one_request_or_session_proof": True,
                "provider_specific_integrity_or_coherence_evidence_sha256": "7" * 64,
            },
        }
        record["durable_record_sha256"] = sha256_canonical_json(record)
        return record

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

    def test_g2a_partition_is_outside_legacy_event_window_namespace(self):
        path = durable_partition_path(1786964700000, root=Path("repo"))
        self.assertEqual(
            path.as_posix(),
            "repo/history/liquidity-orderbook-snapshots/2026/08/17/observations.json",
        )
        self.assertNotIn("liquidity/snapshots", path.as_posix())

    def test_g2a_durable_observation_append_dedupe_and_conflict_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self.durable_record()
            first = persist_durable_l2_observation(record, root=root)
            second = persist_durable_l2_observation(record, root=root)
            self.assertEqual(first["status"], "APPENDED")
            self.assertEqual(second["status"], "DEDUPLICATED")
            self.assertEqual(first["path"], second["path"])
            conflict = self.durable_record(observation_sha="b" * 64)
            with self.assertRaisesRegex(ImmutableHistoryConflict, "IMMUTABLE_OBSERVATION_CONFLICT"):
                persist_durable_l2_observation(conflict, root=root)

    def test_fresh_current_reuse_modes_create_no_fake_history(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "artifact"
            repo = Path(temp) / "repo"
            artifact.mkdir()
            repo.mkdir()
            (artifact / "resource-index.json").write_text(
                json.dumps(
                    {
                        "liquidity_resources": [
                            {"acquisition_mode": "SAME_EXECUTION_REUSE"},
                            {"acquisition_mode": "LEGACY_PERSISTED_REQUALIFICATION"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            transfer = build_fresh_current_durable_observation_artifact(artifact)
            self.assertEqual(transfer["observation_count"], 0)
            self.assertFalse(transfer["same_execution_reuse_creates_history"])
            self.assertFalse(transfer["persisted_reuse_creates_history"])
            applied = apply_fresh_current_durable_observation_artifact(artifact, root=repo)
            self.assertEqual(applied["status"], "PASS")
            self.assertEqual(applied["appended"], 0)
            self.assertEqual(applied["deduplicated"], 0)
            self.assertFalse((repo / "history/liquidity-orderbook-snapshots").exists())


if __name__ == "__main__":
    unittest.main()
