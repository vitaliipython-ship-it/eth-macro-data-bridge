from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validation" / "validate_liquidity_s1_ssot.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_liquidity_s1_ssot", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load liquidity S1 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiquidityS1SsotTests(unittest.TestCase):
    def test_01_full_ssot_validator_passes(self):
        load_validator().main()

    def test_02_adversarial_expected_answers_are_contractual(self):
        contract = load_validator().read_json("contracts/liquidity-s1-semantic-contract-v1.json")
        dynamic = contract["dynamic_depth_acquisition_plan"]
        coverage = contract["coverage"]
        books = contract["book_kind"]
        boundaries = contract["provider_boundaries"]
        quantity = contract["derivatives_quantity"]
        validity = contract["observation_value_validity"]
        downstream = contract["downstream_projection"]
        stages = contract["stage_boundaries"]

        self.assertFalse(dynamic["semantic_request"]["provider_specific_depth_or_level_limit_is_agent_knowledge"])
        self.assertEqual(dynamic["planner"]["sequential_rest_depth_escalation_stitched_as_one_observation"], "FORBIDDEN")
        self.assertTrue(coverage["target_bps_500_expressible"])
        self.assertEqual(boundaries["kraken_spot"]["raw_book_in_current_bridge"], "ABSENT")
        self.assertFalse(books["kraken_grouped_book_equals_aife_profile"])
        self.assertEqual(boundaries["kraken_futures"]["selectable_depth_limit"], "NOT_NORMATIVELY_DOCUMENTED")
        self.assertEqual(quantity["universal_provider_qty_to_base_quantity_mapping"], "FORBIDDEN")
        self.assertFalse(quantity["pi_pf_silent_substitution"])
        self.assertFalse(validity["unobserved_data_may_masquerade_as_observed_zero"])
        self.assertFalse(validity["coverage_complete_alone_proves_separate_provider_native_numeric_value"])
        self.assertFalse(downstream["not_qualified_cvd_may_appear_as_ordinary_consumer_zero"])
        self.assertFalse(downstream["source_conflict_may_become_available"])
        self.assertEqual(stages["acquisition_plan_contract"], "DEFINED_IN_S1")
        self.assertEqual(stages["request_aware_network_acquisition"], "NOT_IMPLEMENTED_BY_S1")
        self.assertFalse(contract["installation_boundaries"]["deep_book_provider_rollout"])
        self.assertEqual(
            contract["authority"]["standalone_correction_artifacts_role"],
            "HISTORICAL_EVIDENCE_ONLY_NOT_CANONICAL_SSOT",
        )


if __name__ == "__main__":
    unittest.main()
