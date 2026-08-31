from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validation import validate_liquidity_s1_ssot as ssot

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class LiquidityS1SsotTests(unittest.TestCase):
    def _inject(self, mutate, invariant: str):
        c = copy.deepcopy(load_json("contracts/liquidity-s1-semantic-contract-v1.json"))
        mutate(c)
        findings, _ = ssot.audit_active_current_semantics(
            ROOT, overrides={"contracts/liquidity-s1-semantic-contract-v1.json": json.dumps(c)})
        self.assertIn(invariant, {x["invariant"] for x in findings})

    def test_01_canonical_owner_and_entrypoint(self):
        b = load_json("bridge-contract.json")
        a = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertFalse(b["semantic_contracts"]["liquidity_s1"]["runtime_active"])
        self.assertIn("→ semantic_contracts.liquidity_s1", a)

    def test_02_arch_b_single_foundation(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        self.assertEqual(c["architecture"]["model"], "ARCH_B_CAPABILITY_SELECTIVE_EXTENSION")
        self.assertEqual(c["architecture"]["market_data_foundation_contour_count"], 1)

    def test_03_computed_audit_excludes_history(self):
        findings, stats = ssot.audit_active_current_semantics(ROOT)
        self.assertEqual(findings, [])
        self.assertGreater(stats["historical_excluded_count"], 0)
        self.assertGreater(stats["audited_path_count"], stats["active_current_path_count"])

    def test_04_second_collector_fails_closed(self):
        self._inject(lambda c: c["architecture"].__setitem__("second_collector", True), "no_second_collector")

    def test_05_second_resolver_fails_closed(self):
        self._inject(lambda c: c["architecture"].__setitem__("second_resolver", True), "no_second_resolver")

    def test_06_second_market_data_authority_fails_closed(self):
        self._inject(lambda c: c["architecture"].__setitem__("second_market_data_authority", True), "no_second_market_data_authority")

    def test_07_runtime_active_before_stage_fails_closed(self):
        self._inject(lambda c: c.__setitem__("runtime_active", True), "runtime_inactive")

    def test_08_s2_rollout_claim_fails_closed(self):
        self._inject(lambda c: c["stage_boundaries"]["S2"].__setitem__("active_in_this_contract_installation", True), "s1_s2_s3_boundary")

    def test_09_unproven_derivatives_equivalence_not_qualified(self):
        q = load_json("contracts/liquidity-s1-semantic-contract-v1.json")["derivatives_quantity"]
        self.assertTrue(q["base_equivalent_nullable"])
        self.assertTrue(q["quote_equivalent_nullable"])
        self.assertFalse(q["consumer_qualified_equivalent_when_conversion_unproven"])

    def test_10_requested_500_observed_230_410_is_truncated(self):
        ex = load_json("contracts/liquidity-s1-semantic-contract-v1.json")["coverage"]["incomplete_example"]
        self.assertEqual((ex["requested_bid_coverage_bps"], ex["requested_ask_coverage_bps"]), (500, 500))
        self.assertEqual((ex["achieved_bid_coverage_bps"], ex["achieved_ask_coverage_bps"]), (230, 410))
        self.assertFalse(ex["coverage_complete_bid"]); self.assertFalse(ex["coverage_complete_ask"])
        self.assertTrue(ex["truncated"]); self.assertFalse(ex["extrapolation_allowed"])

    def test_11_pr283_fail_closed_and_valid_zero(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        self.assertIn("VALID_ZERO", c["observation_value_validity"]["states"])
        self.assertFalse(c["observation_value_validity"]["unobserved_data_may_masquerade_as_observed_zero"])
        self.assertEqual(c["kraken_futures_trade_flow"]["trade_count"]["mismatch"], "SOURCE_CONFLICT")
        self.assertEqual(c["kraken_futures_trade_flow"]["cvd"]["raw_delta_state_equivalence"], "NOT_QUALIFIED")

    def test_12_pr299_relevance_and_stale_od01(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        cur = c["currentization"]
        self.assertEqual(set(cur["pr299_request_scope_semantics"]["failure_relevance_classes"]),
                         {"GLOBAL_STRUCTURAL", "REQUESTED_RESOURCE", "REQUESTED_DOMAIN", "UNREQUESTED_RESOURCE"})
        self.assertTrue(cur["pr299_request_scope_semantics"]["unrelated_degraded_metric_poisoning_forbidden"])
        self.assertFalse(cur["stale_od01_reintroduced"]); self.assertNotIn("od01", c)

    def test_13_dynamic_depth_book_provider_boundaries(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        req = c["dynamic_depth_acquisition_plan"]["semantic_request"]
        self.assertEqual(set(req["minimum_required_target_bps_examples"]), {250, 500})
        self.assertFalse(req["provider_specific_depth_or_level_limit_is_agent_knowledge"])
        self.assertEqual(c["provider_boundaries"]["kraken_spot"]["raw_book_in_current_bridge"], "ABSENT")
        self.assertEqual(c["provider_boundaries"]["kraken_futures"]["selectable_depth_limit"], "NOT_NORMATIVELY_DOCUMENTED")
        self.assertFalse(c["provider_boundaries"]["kraken_futures"]["pf_may_substitute_for_pi"])


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: S1 bytes remain owner of representation compatibility
