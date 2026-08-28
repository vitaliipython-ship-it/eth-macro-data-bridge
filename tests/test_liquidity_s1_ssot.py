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
    def test_01_canonical_entrypoint_and_bridge_binding(self):
        bridge = load_json("bridge-contract.json")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(
            bridge["semantic_contracts"]["liquidity_s1"],
            {
                "contract_id": "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1",
                "path": "contracts/liquidity-s1-semantic-contract-v1.json",
                "status": "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE",
                "runtime_active": False,
            },
        )
        self.assertIn("→ semantic_contracts.liquidity_s1", agents)
        self.assertIn("→ contracts/liquidity-s1-semantic-contract-v1.json", agents)
        self.assertIn("`runtime_active=false`", agents)

    def test_02_active_route_is_unchanged_and_single_contour(self):
        bridge = load_json("bridge-contract.json")
        contract = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        sem = bridge["semantic_resolution"]
        self.assertEqual(sem["status"], "ACTIVE")
        self.assertEqual(sem["discovery_route_authority"], "canonical_paths.capability_index")
        self.assertEqual(sem["resolver"]["interface"], "tools/capability_index.py")
        self.assertEqual(sem["resolver"]["resolution_plan_schema"], "market-data-resolution-plan/1.0.0")
        self.assertEqual(sem["reader"], {"interface": "tools/history_access.py", "input_authority": "ResolutionPlan"})
        self.assertEqual(sem["consumer"]["interface"], "tools/history_consumer.py")
        self.assertEqual(sem["current_data"]["acquisition"]["producer"], "src/collector.py")
        self.assertFalse(sem["current_data"]["acquisition"]["second_collector"])
        self.assertFalse(sem["current_data"]["series_output"]["second_resolver"])
        self.assertFalse(sem["current_data"]["series_output"]["second_reader"])
        arch = contract["architecture"]
        self.assertEqual(arch["market_data_foundation_contour_count"], 1)
        for key in ("second_catalog", "second_resolver", "second_reader",
                    "second_collector", "second_refresh_transport"):
            self.assertFalse(arch[key], key)

    def test_03_real_repository_audit_scans_current_and_excludes_history(self):
        findings, stats = ssot.audit_active_current_semantics(ROOT)
        self.assertEqual(findings, [])
        self.assertGreaterEqual(stats["active_current_path_count"], 10)
        self.assertGreater(stats["historical_excluded_count"], 0)
        self.assertGreaterEqual(stats["audited_path_count"], stats["active_current_path_count"])
        self.assertEqual(
            ssot.classify_path("docs/handoffs/d8-vps-runtime-integration-handoff-v1.md"),
            ssot.HISTORICAL_EVIDENCE,
        )

    def test_04_injected_active_contradiction_is_detected(self):
        contract = copy.deepcopy(load_json("contracts/liquidity-s1-semantic-contract-v1.json"))
        contract["architecture"]["second_collector"] = True
        findings, _ = ssot.audit_active_current_semantics(
            ROOT,
            overrides={
                "contracts/liquidity-s1-semantic-contract-v1.json": json.dumps(contract),
            },
        )
        invariants = {item["invariant"] for item in findings}
        self.assertIn("no_second_collector", invariants)
        self.assertTrue(all(item["classification"] != ssot.HISTORICAL_EVIDENCE for item in findings))

    def test_05_mapping_is_mutation_truthful(self):
        human = (ROOT / "docs/semantics/liquidity-s1-semantic-contract-v1.md").read_text(encoding="utf-8")
        mapping = ssot._mapping(human)
        currentized = {path for path, statuses in mapping.items() if "CURRENTIZE" in statuses}
        self.assertTrue(currentized <= ssot.CURRENT_TASK_CURRENTIZE_PATHS)
        self.assertEqual(
            mapping["docs/semantics/d8-vps-unified-acquisition-runtime-v1.md"],
            {"NO_CHANGE_ALREADY_COMPATIBLE"},
        )
        self.assertEqual(
            mapping["docs/semantics/kraken-futures-cvd.md"],
            {"HISTORICAL_REFERENCE_ONLY"},
        )
        self.assertIn(
            "CURRENTIZE",
            mapping["docs/semantics/d9-operational-status-and-agent-usage-v1.md"],
        )

    def test_06_adversarial_depth_book_and_quantity_contracts(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        req = c["dynamic_depth_acquisition_plan"]["semantic_request"]
        planner = c["dynamic_depth_acquisition_plan"]["planner"]
        self.assertFalse(req["provider_specific_depth_or_level_limit_is_agent_knowledge"])
        self.assertIn(500, req["minimum_required_target_bps_examples"])
        self.assertEqual(planner["sequential_rest_depth_escalation_stitched_as_one_observation"], "FORBIDDEN")
        self.assertFalse(planner["s1_executes_network"])
        self.assertFalse(c["book_kind"]["kraken_grouped_book_equals_aife_profile"])
        self.assertFalse(c["book_kind"]["l3_equals_ordinary_l2_raw"])
        self.assertEqual(c["provider_boundaries"]["kraken_spot"]["raw_book_in_current_bridge"], "ABSENT")
        self.assertEqual(
            c["provider_boundaries"]["kraken_futures"]["selectable_depth_limit"],
            "NOT_NORMATIVELY_DOCUMENTED",
        )
        self.assertFalse(c["provider_boundaries"]["kraken_futures"]["pf_may_substitute_for_pi"])
        self.assertEqual(c["derivatives_quantity"]["model"], "PRODUCT_AWARE_NATIVE_FIRST")
        self.assertEqual(
            c["derivatives_quantity"]["universal_provider_qty_to_base_quantity_mapping"],
            "FORBIDDEN",
        )

    def test_07_false_zero_downstream_and_stage_boundaries_stay_fail_closed(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        validity = c["observation_value_validity"]
        downstream = c["downstream_projection"]
        stages = c["stage_boundaries"]
        self.assertFalse(validity["unobserved_data_may_masquerade_as_observed_zero"])
        self.assertFalse(validity["coverage_complete_alone_proves_separate_provider_native_numeric_value"])
        self.assertFalse(validity["provider_native_present_equals_consumer_qualified_available"])
        self.assertFalse(downstream["not_qualified_cvd_may_appear_as_ordinary_consumer_zero"])
        self.assertFalse(downstream["source_conflict_may_become_available"])
        self.assertTrue(downstream["validity_envelope_must_be_preserved"])
        self.assertEqual(stages["request_aware_network_acquisition"], "NOT_IMPLEMENTED_BY_S1")
        self.assertFalse(stages["S1"]["provider_network_rollout"])
        self.assertFalse(stages["S2"]["active_in_this_contract_installation"])
        self.assertFalse(stages["S3"]["active_in_this_contract_installation"])

    def test_08_od01_is_open_and_scheduler_is_not_repaired_here(self):
        c = load_json("contracts/liquidity-s1-semantic-contract-v1.json")
        workflow = (ROOT / ".github/workflows/update-market.yml").read_text(encoding="utf-8")
        od01 = c["od01"]
        self.assertEqual(od01["status"], "OPEN_TRACKED_INTEGRATION_GATE")
        self.assertEqual(od01["workflow_observed_schedule"], "17 * * * *")
        self.assertEqual(od01["contract_declared_schedule"], "35 * * * *")
        self.assertFalse(od01["resolved_by_this_installation"])
        self.assertFalse(od01["scheduler_behavior_changed_by_this_installation"])
        self.assertIn('cron: "17 * * * *"', workflow)


if __name__ == "__main__":
    unittest.main()
