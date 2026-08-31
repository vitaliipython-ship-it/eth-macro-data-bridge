from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "tools/validation"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import validate_liquidity_g1_durability as g1
from liquidity_s1_runtime import normalize_order_book_observation


class LiquidityG1DurabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = g1.load_contract(ROOT)
        self.base = {
            "provider_id": "binance-spot",
            "instrument_id": "ETHUSDT",
            "book_kind": "L2_LEVEL_BOOK",
            "observation_id": "obs-1",
            "observation_sha256": "a" * 64,
        }

    def test_01_exact_contract_shape_and_validator(self) -> None:
        self.assertEqual(set(self.contract), g1.TOP_LEVEL_FIELDS)
        g1.validate_g1(ROOT)

    def test_02_observation_identity_stable_across_semantic_requests(self) -> None:
        one = {**self.base, "request_sha256": "1" * 64, "target_bps": 250}
        two = {**self.base, "request_sha256": "2" * 64, "target_bps": 500}
        self.assertEqual(g1.observation_identity_material(one), g1.observation_identity_material(two))

    def test_03_request_sha_is_excluded(self) -> None:
        identity = self.contract["observation_identity"]
        self.assertNotIn("request_sha256", identity["semantic_identity_fields"])
        self.assertTrue(identity["request_identity_excluded"])

    def test_04_same_identity_same_sha_is_idempotent(self) -> None:
        self.assertEqual(g1.dedupe_verdict(self.base, dict(self.base)), "IDEMPOTENT_DUPLICATE")

    def test_05_same_identity_different_sha_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "IMMUTABLE_OBSERVATION_CONFLICT"):
            g1.dedupe_verdict(self.base, {**self.base, "observation_sha256": "b" * 64})

    def test_06_partial_500_book_is_durable_without_extrapolation(self) -> None:
        value = g1.history_target_assessment(230.0, 410.0)
        self.assertTrue(value["history_target_truncated"])
        self.assertFalse(value["history_target_complete_bid"])
        self.assertFalse(value["history_target_complete_ask"])
        self.assertFalse(value["extrapolation_allowed"])
        self.assertTrue(value["durable_observation_allowed"])

    def test_07_legacy_100_level_fixture_is_partial_not_synthetic_500_complete(self) -> None:
        bids = [[f"{1000 - i * 0.1:.1f}", "1"] for i in range(100)]
        asks = [[f"{1000.1 + i * 0.1:.1f}", "1"] for i in range(100)]
        normalized = normalize_order_book_observation({
            "observation_id": "legacy-100",
            "provider_id": "binance-spot",
            "instrument_id": "ETHUSDT",
            "book_kind": "L2_LEVEL_BOOK",
            "source_representation": "RAW",
            "timestamp_ms": 1_700_000_000_000,
            "bids": bids,
            "asks": asks,
        })
        assessment = g1.history_target_assessment(
            float(normalized["achieved_bid_coverage_bps"]),
            float(normalized["achieved_ask_coverage_bps"]),
        )
        legacy = self.contract["legacy_compatibility"]
        self.assertEqual(len(normalized["bids"]), 100)
        self.assertEqual(len(normalized["asks"]), 100)
        self.assertTrue(assessment["history_target_truncated"])
        self.assertFalse(assessment["extrapolation_allowed"])
        self.assertTrue(legacy["legacy_100_level_history_valid"])
        self.assertFalse(legacy["legacy_100_level_history_relabelled_as_500_bps_complete"])
        self.assertFalse(legacy["synthetic_deep_backfill"])

    def test_08_cadence_does_not_change_identity(self) -> None:
        hourly = {**self.base, "cadence": "HOURLY"}
        five_minute = {**self.base, "cadence": "FIVE_MINUTE"}
        self.assertEqual(g1.observation_identity_material(hourly), g1.observation_identity_material(five_minute))
        self.assertFalse(self.contract["cadence_independence"]["cadence_is_semantic_identity"])

    def test_09_storage_locator_does_not_change_identity(self) -> None:
        git = {**self.base, "resource_path": "liquidity/snapshots/a.json"}
        server = {**self.base, "database_locator": "opaque"}
        self.assertEqual(g1.observation_identity_material(git), g1.observation_identity_material(server))
        self.assertFalse(self.contract["storage_independence"]["storage_backend_is_semantic_identity"])

    def test_10_no_lookahead_vocabulary(self) -> None:
        value = self.contract["market_time"]
        self.assertEqual(set(value["vocabulary"]), {"observation_time", "known_at", "retrieved_at", "durable_publication_time"})
        self.assertTrue(value["observation_time_semantically_distinct_from_known_at"])
        self.assertTrue(value["known_at_after_cutoff_excluded"])

    def test_11_structural_no_second_authority_guards(self) -> None:
        self.assertTrue(all(value is False for value in self.contract["authority_reuse"].values()))

    def test_12_program_map_stage_and_next_task_are_consistent(self) -> None:
        text = (ROOT / g1.PROGRAM_MAP_PATH).read_text(encoding="utf-8")
        self.assertIn("G1=CLOSED", text)
        self.assertIn("CURRENT_STAGE=G2-A", text)
        self.assertIn("LAST_CONFIRMED_GATE=G1_OWNER_INTEGRATION_AND_POSTMERGE_READBACK_PASS", text)
        self.assertIn(
            "NEXT_EXACT_TASK=ETH-LIQUIDITY-G2A-HOURLY-BASELINE-FRESH-CURRENT-DURABLE-ACCUMULATION-AND-LEGACY-FIXED-DEPTH-SUCCESSION-PREIMPLEMENTATION-R01",
            text,
        )
        self.assertIn("BLOCKERS=NONE", text)
        self.assertNotIn("CURRENT_STAGE=G1", text)
        self.assertNotIn("G1_CONTRACT_IMPLEMENTATION_CANDIDATE_QUALIFIED_PENDING_OWNER_INTEGRATION", text)
        self.assertNotIn("NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK", text)

    def test_13_russian_docs_are_repository_authority_not_external_dependency(self) -> None:
        program = (ROOT / g1.PROGRAM_MAP_PATH).read_text(encoding="utf-8")
        human = (ROOT / g1.HUMAN_PATH).read_text(encoding="utf-8")
        self.assertRegex(program, r"[А-Яа-яЁё]")
        self.assertRegex(human, r"[А-Яа-яЁё]")
        self.assertIn("EVIDENCE_ONLY", program)
        self.assertNotIn("скачать внешний", program.lower())


if __name__ == "__main__":
    unittest.main()
