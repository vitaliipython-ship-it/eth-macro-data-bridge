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
    contract = read_json("contracts/liquidity-s1-semantic-contract-v1.json")
    providers = read_json("contracts/provider-contracts.json")
    bridge = read_json("bridge-contract.json")
    semantics = read_text("docs/semantics/liquidity-s1-semantic-contract-v1.md")
    capability_doc = read_text("docs/semantics/capability-index.md")
    current_doc = read_text("docs/semantics/fresh-current-agent-transport-v1.md")
    d8_doc = read_text("docs/semantics/d8-vps-unified-acquisition-runtime-v1.md")
    cvd_doc = read_text("docs/semantics/kraken-futures-cvd.md")
    workflow = read_text(".github/workflows/update-market.yml")

    require(
        contract["contract_id"] == "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1",
        "unexpected liquidity S1 contract id",
    )
    require(
        contract["status"] == "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE",
        "liquidity S1 contract must remain non-active",
    )
    require(
        contract["authority"]["canonical_owner"]
        == "contracts/liquidity-s1-semantic-contract-v1.json",
        "canonical liquidity S1 owner drifted",
    )
    require(
        contract["authority"]["route_provider_policy_authority"] == "bridge-contract.json",
        "bridge-contract must remain route/provider-policy authority",
    )
    require(
        contract["authority"]["standalone_correction_artifacts_role"]
        == "HISTORICAL_EVIDENCE_ONLY_NOT_CANONICAL_SSOT",
        "standalone correction artifact became semantic authority",
    )

    architecture = contract["architecture"]
    require(
        architecture["model"] == "ARCH_B_CAPABILITY_SELECTIVE_EXTENSION",
        "ARCH_B model not retained",
    )
    require(architecture["market_data_foundation_contour_count"] == 1, "second foundation contour introduced")
    for field in (
        "second_catalog",
        "second_resolver",
        "second_reader",
        "second_collector",
        "second_refresh_transport",
        "second_capability_authority",
        "second_provider_authority",
    ):
        require(architecture[field] is False, f"{field} must remain false")

    stages = contract["stage_boundaries"]
    require(stages["acquisition_plan_contract"] == "DEFINED_IN_S1", "AcquisitionPlan not owned by S1")
    require(
        stages["request_aware_network_acquisition"] == "NOT_IMPLEMENTED_BY_S1",
        "S1 must not activate request-aware network acquisition",
    )
    require(stages["S1"]["provider_network_rollout"] is False, "S1 provider rollout activated")
    require(stages["S2"]["active_in_this_contract_installation"] is False, "S2 activated")
    require(stages["S3"]["active_in_this_contract_installation"] is False, "S3 activated")
    require(stages["s1_source_implementation_performed"] is False, "S1 source implementation claimed")
    require(stages["provider_rollout_performed"] is False, "provider rollout claimed")

    dynamic = contract["dynamic_depth_acquisition_plan"]
    require(dynamic["contract"] == "DYNAMIC_DEPTH_ACQUISITION_PLAN_V1", "dynamic depth contract missing")
    require(
        dynamic["flow"]
        == [
            "SEMANTIC_COVERAGE_REQUEST",
            "RESOURCE_SATISFACTION_CHECK",
            "DYNAMIC_DEPTH_ACQUISITION_PLANNER",
            "EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN",
            "ONE_COHERENT_PROVIDER_OBSERVATION",
        ],
        "dynamic-depth flow drifted",
    )
    request = dynamic["semantic_request"]
    require(
        set(("representation", "target_bps", "bucket_bps", "freshness", "completeness"))
        <= set(request["required_fields"]),
        "semantic coverage request vocabulary incomplete",
    )
    require({250, 500} <= set(request["minimum_required_target_bps_examples"]), "250/500 bps not expressible")
    require(request["provider_specific_depth_or_level_limit_is_agent_knowledge"] is False, "agent must not guess provider depth")
    planner = dynamic["planner"]
    require(planner["exactly_one_provider_acquisition_plan_per_observation"] is True, "one provider plan invariant lost")
    require(planner["sequential_rest_depth_escalation_stitched_as_one_observation"] == "FORBIDDEN", "REST stitching allowed")
    require(planner["retry_semantics"] == "NEW_OBSERVATION", "retry must create a new observation")
    require(planner["s1_executes_network"] is False, "S1 network execution activated")

    reuse = contract["resource_satisfaction"]
    require(reuse["check_before_network_acquisition"] is True, "resource satisfaction must precede acquisition")
    require(
        {
            "provider",
            "market_instrument_identity",
            "book_kind",
            "representation",
            "freshness",
            "side_coverage",
            "actual_coverage_bps",
            "completeness",
            "integrity",
        }
        <= set(reuse["dominance_dimensions"]),
        "resource dominance dimensions incomplete",
    )
    require(reuse["deeper_fresh_coherent_raw_may_satisfy_narrower_profile"] is True, "RAW->PROFILE reuse lost")
    require(reuse["reacquire_when_dominating_resource_exists"] is False, "unnecessary reacquisition allowed")

    coverage = contract["coverage"]
    require(coverage["requested_target_coverage_is_distinct_from_provider_acquisition_depth"] is True, "target/depth collapsed")
    require(coverage["provider_acquisition_depth_is_distinct_from_actual_achieved_coverage"] is True, "depth/actual coverage collapsed")
    require(set(coverage["side_specific_fields"]) == {"bid_coverage", "ask_coverage", "common_complete_bps"}, "side coverage fields drifted")
    require(coverage["no_extrapolation_outside_observed_book"] is True, "book extrapolation allowed")
    require(coverage["mandatory_completeness_target_missed"] == "FAIL_CLOSED", "mandatory completeness not fail closed")
    require(coverage["target_bps_500_expressible"] is True, "500 bps request not expressible")

    books = contract["book_kind"]
    require(
        {"L2_LEVEL_BOOK", "PROVIDER_GROUPED_L2", "L3_ORDER_BOOK", "FUTURES_L2_BOOK"}
        <= set(books["semantic_book_kinds"]),
        "book-kind model incomplete",
    )
    require(set(books["representations"]) == {"RAW", "NORMALIZED", "PROFILE", "SUMMARY"}, "representation set drifted")
    require(books["kraken_grouped_book_equals_aife_profile"] is False, "GroupedBook collapsed into PROFILE")
    require(books["l3_equals_ordinary_l2_raw"] is False, "L3 collapsed into L2 RAW")
    require(books["representations_are_independent_analytical_votes"] is False, "representations became votes")

    boundaries = contract["provider_boundaries"]
    spot = boundaries["kraken_spot"]
    require(spot["provider_raw_book_capability"] == "AVAILABLE_EXTERNALLY", "Kraken Spot provider capability missing")
    require(spot["raw_book_in_current_bridge"] == "ABSENT", "Kraken Spot RAW falsely claimed current")
    require(spot["endpoint_existence_implies_current_aife_resource"] is False, "provider endpoint became AIFE resource")
    futures = boundaries["kraken_futures"]
    require(futures["raw_l2_book"] == "PROVIDER_CAPABILITY_CONFIRMED", "Kraken Futures raw L2 boundary missing")
    require(futures["selectable_depth_limit"] == "NOT_NORMATIVELY_DOCUMENTED", "Kraken Futures depth limit invented")
    require(futures["normative_max_depth_invented"] is False, "normative Kraken Futures max invented")
    require(futures["first_raw_book_instruments"] == ["PI_ETHUSD", "PI_XBTUSD"], "PI raw-book identities drifted")
    require(futures["pf_may_substitute_for_pi"] is False, "PF may substitute PI")

    quantity = contract["derivatives_quantity"]
    require(quantity["model"] == "PRODUCT_AWARE_NATIVE_FIRST", "derivatives quantity model not native-first")
    require(quantity["universal_provider_qty_to_base_quantity_mapping"] == "FORBIDDEN", "generic base quantity mapping allowed")
    require(quantity["base_equivalent_nullable"] is True and quantity["quote_notional_nullable"] is True, "derived equivalents must be nullable")
    require(quantity["unproven_conversion_result"] == "UNAVAILABLE_OR_NULL", "unproven conversion not fail closed")
    require(quantity["pi_pf_identity_distinct"] is True and quantity["pi_pf_silent_substitution"] is False, "PI/PF identity collapsed")

    validity = contract["observation_value_validity"]
    require(validity["global_invariant"] == "OBSERVATION_COVERAGE_NE_VALUE_VALIDITY", "coverage/value invariant lost")
    require(
        {"VALID_ZERO", "UNAVAILABLE", "NOT_QUALIFIED", "SOURCE_CONFLICT", "MISALIGNED", "UNKNOWN", "PARTIAL", "INCOMPLETE"}
        <= set(validity["states"]),
        "validity state model incomplete",
    )
    require(validity["unobserved_data_may_masquerade_as_observed_zero"] is False, "unobserved data may become zero")
    require(validity["valid_zero"]["requires_source_observed"] is True, "valid zero lacks observation proof")
    require(validity["valid_zero"]["requires_coverage_complete"] is True, "valid zero lacks completeness proof")
    require(validity["coverage_complete_alone_proves_separate_provider_native_numeric_value"] is False, "coverage alone proves value")
    require(validity["provider_native_present_equals_consumer_qualified_available"] is False, "provider-native presence collapsed into availability")

    flow = contract["kraken_futures_trade_flow"]
    require(flow["trade_count"]["raw_execution_reconciliation"] == "QUALIFIED", "trade-count reconciliation lost")
    require(flow["trade_count"]["analytics_interval_seconds"] == 300, "Kraken trade-count interval drifted")
    require(flow["trade_count"]["accepted_current_timestamp_semantics"] == "BUCKET_END", "Kraken timestamp semantics drifted")
    require(flow["trade_count"]["raw_bucket_semantics"] == "[bucket_start,bucket_end)", "raw bucket semantics drifted")
    require(flow["trade_count"]["mismatch"] == "SOURCE_CONFLICT", "source conflict semantics lost")
    require(flow["trade_volume"]["raw_history_size_to_analytics_base_volume_equivalence"] == "NOT_QUALIFIED", "trade volume overqualified")
    require(flow["aggressor_differential"]["pi_raw_size_quantity_unit_equivalence"] == "NOT_QUALIFIED", "aggressor quantity overqualified")
    require(flow["cvd"]["raw_delta_state_equivalence"] == "NOT_QUALIFIED", "CVD raw/state equivalence overqualified")
    require(flow["l2_derived_executed_trades"] is False, "L2-derived executed trades allowed")
    require(flow["invented_raw_quantity_conversion"] is False, "raw quantity conversion invented")

    downstream = contract["downstream_projection"]
    require(downstream["route"] == ["DERIVATIVES", "ANALYTICS", "CURRENT_DATA", "CONSUMER"], "validity route drifted")
    require(downstream["validity_envelope_must_be_preserved"] is True, "validity envelope may be stripped")
    require(downstream["not_qualified_cvd_may_appear_as_ordinary_consumer_zero"] is False, "NOT_QUALIFIED CVD may become zero")
    require(downstream["source_conflict_may_become_available"] is False, "SOURCE_CONFLICT may become AVAILABLE")

    od01 = contract["od01"]
    require(od01["status"] == "OPEN_TRACKED_INTEGRATION_GATE", "OD-01 must remain open")
    require(od01["workflow_observed_schedule"] == "17 * * * *", "OD-01 workflow side drifted")
    require(od01["contract_declared_schedule"] == "35 * * * *", "OD-01 contract side drifted")
    require(od01["resolved_by_this_installation"] is False, "OD-01 resolved without owner decision")
    require(od01["scheduler_behavior_changed_by_this_installation"] is False, "scheduler changed during semantic install")
    require('cron: "17 * * * *"' in workflow, "actual workflow no longer matches tracked OD-01 observation")

    install = contract["installation_boundaries"]
    for field in (
        "active_data_routes_changed",
        "provider_activation_changed",
        "new_network_acquisition_path",
        "deep_book_provider_rollout",
        "s1_general_source_implementation",
        "s2_provider_adapter_rollout",
        "s3_network_activation",
    ):
        require(install[field] is False, f"installation boundary violated: {field}")

    require(bridge["semantic_resolution"]["status"] == "ACTIVE", "active semantic route changed")
    require(
        bridge["semantic_resolution"]["resolver"]["resolution_plan_schema"]
        == "market-data-resolution-plan/1.0.0",
        "active ResolutionPlan changed",
    )
    require(bridge["semantic_resolution"]["reader"]["input_authority"] == "ResolutionPlan", "reader authority changed")
    require(bridge["semantic_resolution"]["current_data"]["acquisition"]["second_collector"] is False, "second collector introduced")
    require(bridge["semantic_resolution"]["current_data"]["series_output"]["second_resolver"] is False, "second current resolver introduced")
    require(bridge["semantic_resolution"]["current_data"]["series_output"]["second_reader"] is False, "second current reader introduced")
    require(bridge["no_silent_provider_substitution"] is True, "provider substitution policy weakened")

    provider_rows = {(row["provider"], row["product"]): row for row in providers["contracts"]}
    spot_provider = provider_rows[("kraken", "Spot Order Book")]
    require(spot_provider["provider_raw_book_capability"] == "AVAILABLE_EXTERNALLY", "provider contract lost Kraken Spot capability")
    require(spot_provider["current_aife_raw_book_resource"] == "ABSENT", "provider contract falsely claims current Kraken Spot RAW")
    futures_provider = provider_rows[("kraken", "Futures Raw L2 Order Book")]
    require(futures_provider["selectable_depth_limit"] == "NOT_NORMATIVELY_DOCUMENTED", "provider contract invented Futures depth")
    require(futures_provider["pf_substitution_for_pi"] is False, "provider contract permits PF substitution")

    require("250 bps" in semantics and "500 bps" in semantics, "human S1 semantics lost 250/500 coverage")
    require("REQUEST_AWARE_NETWORK_ACQUISITION=NOT_IMPLEMENTED_BY_S1" in semantics, "human S1 boundary drifted")
    require("S1 liquidity — additive semantic extension" in capability_doc, "capability owner not currentized")
    require("OD01_STATUS=OPEN_TRACKED_INTEGRATION_GATE" in current_doc, "current-data doc lost OD-01")
    require("OBSERVATION_COVERAGE != VALUE_VALIDITY" in current_doc, "current-data doc lost value-validity invariant")

    # Existing bounded D8 depth is an implementation-specific predecessor bound, not a provider max-depth contract.
    require("bounded depth snapshot (`limit=100`)" in d8_doc, "expected current D8 fixed-bound predecessor changed unexpectedly")
    require("provider-native `cvd`" in cvd_doc, "historical Kraken CVD contract unexpectedly missing")

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
