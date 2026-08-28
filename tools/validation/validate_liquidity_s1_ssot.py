from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    c = read_json("contracts/liquidity-s1-semantic-contract-v1.json")
    providers = read_json("contracts/provider-contracts.json")
    bridge = read_json("bridge-contract.json")
    human = read_text("docs/semantics/liquidity-s1-semantic-contract-v1.md")
    capability = read_text("docs/semantics/capability-index.md")
    current = read_text("docs/semantics/fresh-current-agent-transport-v1.md")
    update_workflow = read_text(".github/workflows/update-market.yml")

    require(c["contract_id"] == "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1", "contract id drifted")
    require(c["status"] == "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE", "S1 contract activated")
    require(c["authority"]["canonical_owner"] == "contracts/liquidity-s1-semantic-contract-v1.json", "canonical owner drifted")
    require(c["authority"]["route_provider_policy_authority"] == "bridge-contract.json", "route authority drifted")
    require(c["authority"]["standalone_correction_artifacts_role"] == "HISTORICAL_EVIDENCE_ONLY_NOT_CANONICAL_SSOT", "standalone artifact became SSOT")

    arch = c["architecture"]
    require(arch["model"] == "ARCH_B_CAPABILITY_SELECTIVE_EXTENSION", "ARCH_B not retained")
    require(arch["market_data_foundation_contour_count"] == 1, "second foundation contour introduced")
    for key in ("second_catalog", "second_resolver", "second_reader", "second_collector", "second_refresh_transport", "second_capability_authority", "second_provider_authority"):
        require(arch[key] is False, f"{key} must remain false")

    stages = c["stage_boundaries"]
    require(stages["acquisition_plan_contract"] == "DEFINED_IN_S1", "AcquisitionPlan not in S1")
    require(stages["request_aware_network_acquisition"] == "NOT_IMPLEMENTED_BY_S1", "S1 network acquisition activated")
    require(stages["S1"]["provider_network_rollout"] is False, "S1 provider rollout activated")
    require(stages["S2"]["active_in_this_contract_installation"] is False, "S2 activated")
    require(stages["S3"]["active_in_this_contract_installation"] is False, "S3 activated")

    dynamic = c["dynamic_depth_acquisition_plan"]
    require(dynamic["flow"] == [
        "SEMANTIC_COVERAGE_REQUEST",
        "RESOURCE_SATISFACTION_CHECK",
        "DYNAMIC_DEPTH_ACQUISITION_PLANNER",
        "EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN",
        "ONE_COHERENT_PROVIDER_OBSERVATION",
    ], "dynamic-depth flow drifted")
    request = dynamic["semantic_request"]
    require({"representation", "target_bps", "bucket_bps", "freshness", "completeness"} <= set(request["required_fields"]), "request vocabulary incomplete")
    require({250, 500} <= set(request["minimum_required_target_bps_examples"]), "250/500 bps not expressible")
    require(request["provider_specific_depth_or_level_limit_is_agent_knowledge"] is False, "agent must not guess provider depth")
    planner = dynamic["planner"]
    require(planner["exactly_one_provider_acquisition_plan_per_observation"] is True, "one-plan invariant lost")
    require(planner["sequential_rest_depth_escalation_stitched_as_one_observation"] == "FORBIDDEN", "REST stitching allowed")
    require(planner["retry_semantics"] == "NEW_OBSERVATION" and planner["s1_executes_network"] is False, "planner boundary violated")

    reuse = c["resource_satisfaction"]
    require(reuse["check_before_network_acquisition"] is True, "reuse check missing")
    require({"provider", "market_instrument_identity", "book_kind", "representation", "freshness", "side_coverage", "actual_coverage_bps", "completeness", "integrity"} <= set(reuse["dominance_dimensions"]), "dominance dimensions incomplete")
    require(reuse["deeper_fresh_coherent_raw_may_satisfy_narrower_profile"] is True, "RAW->PROFILE reuse lost")
    require(reuse["reacquire_when_dominating_resource_exists"] is False, "unnecessary reacquisition allowed")

    coverage = c["coverage"]
    require(coverage["requested_target_coverage_is_distinct_from_provider_acquisition_depth"] is True, "target/depth collapsed")
    require(coverage["provider_acquisition_depth_is_distinct_from_actual_achieved_coverage"] is True, "depth/actual collapsed")
    require(set(coverage["side_specific_fields"]) == {"bid_coverage", "ask_coverage", "common_complete_bps"}, "side coverage fields drifted")
    require(coverage["no_extrapolation_outside_observed_book"] is True, "extrapolation allowed")
    require(coverage["mandatory_completeness_target_missed"] == "FAIL_CLOSED", "mandatory completeness not fail closed")
    require(coverage["target_bps_500_expressible"] is True, "500 bps not expressible")

    books = c["book_kind"]
    require({"L2_LEVEL_BOOK", "PROVIDER_GROUPED_L2", "L3_ORDER_BOOK", "FUTURES_L2_BOOK"} <= set(books["semantic_book_kinds"]), "book-kind model incomplete")
    require(set(books["representations"]) == {"RAW", "NORMALIZED", "PROFILE", "SUMMARY"}, "representations drifted")
    require(books["kraken_grouped_book_equals_aife_profile"] is False, "GroupedBook collapsed into PROFILE")
    require(books["l3_equals_ordinary_l2_raw"] is False, "L3 collapsed into L2 RAW")

    spot = c["provider_boundaries"]["kraken_spot"]
    require(spot["provider_raw_book_capability"] == "AVAILABLE_EXTERNALLY", "Kraken Spot capability missing")
    require(spot["raw_book_in_current_bridge"] == "ABSENT", "Kraken Spot RAW falsely current")
    futures = c["provider_boundaries"]["kraken_futures"]
    require(futures["raw_l2_book"] == "PROVIDER_CAPABILITY_CONFIRMED", "Kraken Futures raw L2 missing")
    require(futures["selectable_depth_limit"] == "NOT_NORMATIVELY_DOCUMENTED", "Kraken Futures max invented")
    require(futures["normative_max_depth_invented"] is False, "normative max invented")
    require(futures["first_raw_book_instruments"] == ["PI_ETHUSD", "PI_XBTUSD"] and futures["pf_may_substitute_for_pi"] is False, "PI/PF identity violated")

    qty = c["derivatives_quantity"]
    require(qty["model"] == "PRODUCT_AWARE_NATIVE_FIRST", "quantity model not native-first")
    require(qty["universal_provider_qty_to_base_quantity_mapping"] == "FORBIDDEN", "generic base mapping allowed")
    require(qty["base_equivalent_nullable"] is True and qty["quote_notional_nullable"] is True, "derived equivalents not nullable")
    require(qty["unproven_conversion_result"] == "UNAVAILABLE_OR_NULL", "unproven conversion not fail closed")
    require(qty["pi_pf_identity_distinct"] is True and qty["pi_pf_silent_substitution"] is False, "PI/PF identity collapsed")

    validity = c["observation_value_validity"]
    require(validity["global_invariant"] == "OBSERVATION_COVERAGE_NE_VALUE_VALIDITY", "coverage/value invariant lost")
    require({"VALID_ZERO", "UNAVAILABLE", "NOT_QUALIFIED", "SOURCE_CONFLICT", "MISALIGNED", "UNKNOWN", "PARTIAL", "INCOMPLETE"} <= set(validity["states"]), "validity states incomplete")
    require(validity["unobserved_data_may_masquerade_as_observed_zero"] is False, "unobserved data may become zero")
    require(validity["coverage_complete_alone_proves_separate_provider_native_numeric_value"] is False, "coverage alone proves value")
    require(validity["provider_native_present_equals_consumer_qualified_available"] is False, "provider-native presence collapsed into availability")

    flow = c["kraken_futures_trade_flow"]
    require(flow["trade_count"]["raw_execution_reconciliation"] == "QUALIFIED", "trade-count reconciliation lost")
    require(flow["trade_count"]["analytics_interval_seconds"] == 300 and flow["trade_count"]["accepted_current_timestamp_semantics"] == "BUCKET_END", "trade-count time contract drifted")
    require(flow["trade_count"]["raw_bucket_semantics"] == "[bucket_start,bucket_end)" and flow["trade_count"]["mismatch"] == "SOURCE_CONFLICT", "trade-count conflict contract drifted")
    require(flow["trade_volume"]["raw_history_size_to_analytics_base_volume_equivalence"] == "NOT_QUALIFIED", "trade-volume overqualified")
    require(flow["aggressor_differential"]["pi_raw_size_quantity_unit_equivalence"] == "NOT_QUALIFIED", "aggressor overqualified")
    require(flow["cvd"]["raw_delta_state_equivalence"] == "NOT_QUALIFIED", "CVD overqualified")
    require(flow["l2_derived_executed_trades"] is False and flow["invented_raw_quantity_conversion"] is False, "forbidden derivation enabled")

    downstream = c["downstream_projection"]
    require(downstream["route"] == ["DERIVATIVES", "ANALYTICS", "CURRENT_DATA", "CONSUMER"], "downstream route drifted")
    require(downstream["validity_envelope_must_be_preserved"] is True, "validity envelope may be stripped")
    require(downstream["not_qualified_cvd_may_appear_as_ordinary_consumer_zero"] is False, "NOT_QUALIFIED CVD may become zero")
    require(downstream["source_conflict_may_become_available"] is False, "SOURCE_CONFLICT may become AVAILABLE")

    od01 = c["od01"]
    require(od01["status"] == "OPEN_TRACKED_INTEGRATION_GATE", "OD-01 not open")
    require(od01["workflow_observed_schedule"] == "17 * * * *" and od01["contract_declared_schedule"] == "35 * * * *", "OD-01 sides drifted")
    require(od01["resolved_by_this_installation"] is False and od01["scheduler_behavior_changed_by_this_installation"] is False, "OD-01 silently resolved")
    require('cron: "17 * * * *"' in update_workflow, "actual workflow no longer matches tracked OD-01")

    for key, value in c["installation_boundaries"].items():
        require(value is False, f"installation boundary violated: {key}")

    require(bridge["semantic_resolution"]["status"] == "ACTIVE", "active semantic route changed")
    require(bridge["semantic_resolution"]["resolver"]["resolution_plan_schema"] == "market-data-resolution-plan/1.0.0", "active ResolutionPlan changed")
    require(bridge["semantic_resolution"]["reader"]["input_authority"] == "ResolutionPlan", "reader authority changed")
    require(bridge["semantic_resolution"]["current_data"]["acquisition"]["second_collector"] is False, "second collector introduced")
    require(bridge["semantic_resolution"]["current_data"]["series_output"]["second_resolver"] is False, "second resolver introduced")
    require(bridge["semantic_resolution"]["current_data"]["series_output"]["second_reader"] is False, "second reader introduced")
    require(bridge["no_silent_provider_substitution"] is True, "provider substitution policy weakened")

    rows = {(row["provider"], row["product"]): row for row in providers["contracts"]}
    require(rows[("kraken", "Spot Order Book")]["current_aife_raw_book_resource"] == "ABSENT", "provider contract falsely claims Kraken Spot RAW")
    require(rows[("kraken", "Spot Order Book")]["grouped_book_equals_aife_profile"] is False, "provider contract collapses GroupedBook")
    require(rows[("kraken", "Futures Raw L2 Order Book")]["selectable_depth_limit"] == "NOT_NORMATIVELY_DOCUMENTED", "provider contract invents Futures depth")
    require(rows[("kraken", "Futures Raw L2 Order Book")]["pf_substitution_for_pi"] is False, "provider contract permits PF substitution")

    require("MACHINE_AUTHORITY=contracts/liquidity-s1-semantic-contract-v1.json" in human, "human authority pointer drifted")
    require("S1 liquidity — additive semantic extension" in capability, "capability owner not currentized")
    require("OD01_STATUS=OPEN_TRACKED_INTEGRATION_GATE" in current, "current-data doc lost OD-01")

    print("LIQUIDITY_S1_SSOT_CONTRACT=PASS")
    print("ARCH_B_STATUS=RETAINED")
    print("DYNAMIC_DEPTH_SEMANTICS=PASS")
    print("RESOURCE_SATISFACTION=PASS")
    print("ONE_COHERENT_OBSERVATION=PASS")
    print("PROFILE_500_BPS_EXPRESSIBLE=YES")
    print("SIDE_SPECIFIC_COVERAGE=PASS")
    print("BOOK_KIND_MODEL=PASS")
    print("KRAKEN_BOUNDARIES=PASS")
    print("NATIVE_FIRST_QUANTITY=PASS")
    print("OBSERVATION_VALUE_VALIDITY=PASS")
    print("PROVIDER_NATIVE_VS_CONSUMER_QUALIFIED=PASS")
    print("DOWNSTREAM_VALIDITY=PASS")
    print("S1_S2_S3_BOUNDARY=PASS")
    print("OD01_OPEN_GATE=PASS")
    print("ACTIVE_ROUTE_UNCHANGED=PASS")
    print("NO_PROVIDER_ROLLOUT=PASS")
    print("ACTIVE_SSOT_CONTRADICTION_COUNT=0")
    print("LIQUIDITY_S1_SSOT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
