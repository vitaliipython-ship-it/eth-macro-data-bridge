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

    def _program_text(self) -> str:
        return (ROOT / g1.PROGRAM_MAP_PATH).read_text(encoding="utf-8")

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
        self.assertEqual(
            self.contract["storage_independence"]["durable_l2_physical_locator"],
            "history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json",
        )
        self.assertEqual(self.contract["storage_independence"]["legacy_snapshot_namespace"], "liquidity/snapshots/**")

    def test_10_no_lookahead_vocabulary(self) -> None:
        value = self.contract["market_time"]
        self.assertEqual(set(value["vocabulary"]), {"observation_time", "known_at", "retrieved_at", "durable_publication_time"})
        self.assertTrue(value["observation_time_semantically_distinct_from_known_at"])
        self.assertTrue(value["known_at_after_cutoff_excluded"])

    def test_11_structural_no_second_authority_guards(self) -> None:
        self.assertTrue(all(value is False for value in self.contract["authority_reuse"].values()))
        stages = self.contract["stage_boundaries"]
        self.assertTrue(stages["g2_a_writer_implemented"])
        self.assertFalse(stages["g2_b_reader_implemented"])
        self.assertEqual(stages["provider_network_calls_per_canonical_hourly_run"], 6)
        self.assertEqual(stages["binance_usdm_github_network_calls"], 0)
        self.assertFalse(stages["d8_provider_authority_transition"])
        self.assertFalse(stages["d9_authority_activation"])

    def test_12_program_map_stage_and_next_task_are_consistent(self) -> None:
        text = self._program_text()
        self.assertIn("G1=CLOSED", text)
        self.assertIn("CURRENT_STAGE=G2-A", text)
        self.assertIn("G2A_PREIMPLEMENTATION=PASS", text)
        self.assertIn("G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS", text)
        self.assertIn("G2A_COUPLED_DB_C_VALIDATION_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE", text)
        self.assertIn("G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS", text)
        self.assertIn("G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES", text)
        self.assertIn("G2A_S3_HOST_BINDING_TEST_COUPLED_SCOPE_REVIEW=PASS", text)
        self.assertIn("G2A_S3_HOST_BINDING_TEST_COUPLED_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE", text)
        self.assertIn("G2A_KRAKEN_SPOT_FIRST_ACTUAL_FAILURE_RCA_REVIEW=PASS", text)
        self.assertIn("G2A_KRAKEN_SPOT_PRODUCTION_JSON_NUMERIC_COMPATIBILITY_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE", text)
        self.assertIn("PRODUCTION_COMPATIBILITY_DEFECT=RESOLVED_R04", text)
        self.assertIn("EXACT_RUN_ROOT_CAUSE_PROVEN=NO", text)
        self.assertIn("OBSERVED_FAILURE_CAUSAL_BINDING=HIGH_CONFIDENCE", text)
        self.assertIn("FLOAT_ACCEPTANCE_WITHOUT_PRECISION_PRESERVATION_SAFE=NO", text)
        self.assertIn("LIVE_WIRE_NUMERIC_DECODING_COVERAGE_GAP=RESOLVED_R04", text)
        self.assertIn("MINIMAL_CORRECT_REPAIR_PATH=src/liquidity_s3_executor.py", text)
        self.assertIn("G2A_REAUTHORIZED=YES", text)
        self.assertIn("READY_FOR_G2A_IMPLEMENTATION=YES", text)
        self.assertIn("ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES", text)
        self.assertIn("ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS_R04_REUSED", text)
        self.assertIn("SECOND_CONTROLLED_G2A_REQUALIFICATION=NO", text)
        self.assertIn("LEGACY_FIXED_100_RETIREMENT=COMPLETE_IN_CANDIDATE", text)
        self.assertIn("G2A_IMPLEMENTATION_CANDIDATE=READY_FOR_OWNER_REVIEW", text)
        self.assertIn("G2A_OWNER_INTEGRATION=PENDING", text)
        self.assertIn("G2B_STARTED=NO", text)
        declared_count, parsed_paths = g1.validate_frozen_g2a_implementation_scope(text)
        self.assertEqual(declared_count, 21)
        self.assertEqual(parsed_paths, g1.FROZEN_G2A_IMPLEMENTATION_PATHS)
        self.assertEqual(len(parsed_paths), 21)
        self.assertEqual(len(set(parsed_paths)), 21)
        self.assertEqual(parsed_paths[-1], "src/liquidity_s3_executor.py")
        self.assertEqual(
            parsed_paths[-6:],
            (
                "contracts/provider-contracts.json",
                "src/liquidity_s2_binance_adapter.py",
                "tools/validation/validate_liquidity_s2_binance_adapter.py",
                "tests/test_liquidity_s2_binance_adapter.py",
                "tests/test_liquidity_s3_executor.py",
                "src/liquidity_s3_executor.py",
            ),
        )
        self.assertIn("NEW_PATH_COUNT=0", text)
        self.assertIn("AUTHORIZED_SCOPE_EXPANSION_PATH=tests/test_liquidity_s3_executor.py", text)
        self.assertIn("AUTHORIZED_SCOPE_EXPANSION_PATH=src/liquidity_s3_executor.py", text)
        self.assertIn("PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=20", text)
        self.assertIn("EXACT_IMPLEMENTATION_PATH_COUNT=21", text)
        self.assertIn("FAILED_ACQUISITION_RUN=33549822547", text)
        self.assertIn("FAILED_CARRIER_HEAD=a46de92f265cbdd49667b815ec7c5693a8d048e4", text)
        self.assertIn("FAILED_CARRIER_TREE=4bf3d4b7d5c777560bb7778a82c181f9449e1932", text)
        self.assertIn("FAILED_CAPABILITY=liquidity.kraken-spot.ETHUSD.orderbook", text)
        self.assertIn("FAILED_TERMINAL_STATUS=FAIL_MALFORMED_PAYLOAD", text)
        self.assertIn("NETWORK_ATTEMPT_COUNT=1", text)
        self.assertIn("RAW_MESSAGE_COUNT=3", text)
        self.assertIn("RAW_OBSERVATION_BYTES=71232", text)
        self.assertIn("R04_REPAIRED_WIP_HEAD=d4726243ff0ab719f668d764a858dd7bea8e1f6d", text)
        self.assertIn("R04_PRE_NETWORK_CI_RUN=33560282658", text)
        self.assertIn("R04_QUALIFICATION_CARRIER_HEAD=743bb18cdedb414476a0ccdc191a0f7cea9154f3", text)
        self.assertIn("R04_CONTROLLED_QUALIFICATION_RUN=33560525938", text)
        self.assertIn("SIX_CAPABILITY_GENERATION_BYTES=547874", text)
        self.assertIn("PHYSICAL_DURABLE_L2_PARTITION=history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json", text)
        self.assertIn("EVENT_WINDOW_NAMESPACE_COLLISION=RESOLVED", text)
        self.assertIn(
            "LAST_CONFIRMED_GATE=R04_SIX_CAPABILITY_AND_SUCCESSOR_BYTE_BENCHMARK_PASS_PLUS_R05_NETWORK_FREE_FINALIZATION",
            text,
        )
        self.assertIn(
            "NEXT_EXACT_TASK=CANONICAL_EXACT_SHA_CI_THEN_ONE_IMPLEMENTATION_PR_THEN_PR_CI_THEN_OWNER_REVIEW_NO_MERGE_BY_THIS_TASK",
            text,
        )
        self.assertNotIn("CURRENT_STAGE=G1", text)
        self.assertNotIn("NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK", text)
        self.assertNotIn("LAST_CONFIRMED_GATE=G1_OWNER_INTEGRATION_AND_POSTMERGE_READBACK_PASS", text)
        self.assertNotIn("LAST_CONFIRMED_GATE=G2A_PROVEN_DB_C_VALIDATION_COUPLED_SCOPE_EXPANSION_OWNER_AUTHORIZATION_PASS", text)
        active_resume = text.split("## Resume / continuation", 1)[-1]
        self.assertNotIn(
            "CONTINUATION_MODE=RESUME_G2A_WIP_FROM_4FB04DAF_ON_FRESH_POST_GOVERNANCE_AUTHORITY_REPAIR_KRAKEN_SPOT_PRECISION_DECODE_THEN_PRENETWORK_AND_ONE_CONTROLLED_SIX_CAPABILITY_REQUALIFICATION",
            active_resume,
        )

    def test_13_exact_scope_extra_path_fails_closed(self) -> None:
        text = self._program_text()
        anchor = "src/liquidity_s3_executor.py\n```"
        mutated = text.replace(
            anchor,
            "src/liquidity_s3_executor.py\nunauthorized/extra.py\n```",
            1,
        )
        self.assertNotEqual(mutated, text)
        with self.assertRaisesRegex(ValueError, "G2A_IMPLEMENTATION_SCOPE_PARSED_COUNT:22"):
            g1.validate_frozen_g2a_implementation_scope(mutated)

    def test_14_exact_scope_missing_path_fails_closed(self) -> None:
        text = self._program_text()
        mutated = text.replace("src/intelligence.py\n", "", 1)
        self.assertNotEqual(mutated, text)
        with self.assertRaisesRegex(ValueError, "G2A_IMPLEMENTATION_SCOPE_PARSED_COUNT:20"):
            g1.validate_frozen_g2a_implementation_scope(mutated)

    def test_15_exact_scope_substitution_fails_closed(self) -> None:
        text = self._program_text()
        mutated = text.replace("src/sampled_history.py\n", "src/not-authorized.py\n", 1)
        self.assertNotEqual(mutated, text)
        with self.assertRaisesRegex(ValueError, "G2A_IMPLEMENTATION_SCOPE_EXACT_SET_MISMATCH"):
            g1.validate_frozen_g2a_implementation_scope(mutated)

    def test_16_exact_scope_duplicate_path_fails_closed(self) -> None:
        text = self._program_text()
        anchor = "src/liquidity_s3_executor.py\n```"
        mutated = text.replace(
            anchor,
            "src/liquidity_s3_executor.py\n"
            "src/liquidity_s3_executor.py\n```",
            1,
        )
        self.assertNotEqual(mutated, text)
        with self.assertRaisesRegex(ValueError, "G2A_IMPLEMENTATION_SCOPE_DUPLICATE_PATHS:1"):
            g1.validate_frozen_g2a_implementation_scope(mutated)

    def test_17_russian_docs_are_repository_authority_not_external_dependency(self) -> None:
        program = self._program_text()
        human = (ROOT / g1.HUMAN_PATH).read_text(encoding="utf-8")
        self.assertRegex(program, r"[А-Яа-яЁё]")
        self.assertRegex(human, r"[А-Яа-яЁё]")
        self.assertIn("EVIDENCE_ONLY", program)
        self.assertNotIn("скачать внешний", program.lower())


if __name__ == "__main__":
    unittest.main()
