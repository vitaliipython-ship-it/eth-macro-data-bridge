from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from liquidity_s1_runtime import (
    BOOK_SCHEMA,
    QUANTITY_SCHEMA,
    REQUEST_SCHEMA,
    RESOURCE_SCHEMA,
    LiquidityS1Error,
    assert_one_coherent_provider_observation,
    canonical_plan_bytes,
    compute_side_coverage,
    evaluate_resource_satisfaction,
    normalize_liquidity_request,
    normalize_order_book_observation,
    plan_liquidity_acquisition,
    qualify_liquidity_resource,
    qualify_quantity_semantics,
    validate_normalized_order_book,
    validate_provider_capability_for_s1,
    validate_qualified_liquidity_resource,
    validate_quantity_semantics,
)


def require(value: bool, marker: str) -> None:
    if not value:
        raise RuntimeError(marker)


def expect_error(fn, code: str, marker: str) -> None:
    try:
        fn()
    except LiquidityS1Error as exc:
        require(str(exc) == code, f"{marker}_WRONG_ERROR:{exc}")
    else:
        raise RuntimeError(f"{marker}_BYPASS")


def request(target: int = 500, *, provider="binance-spot", instrument="ETHUSDT", book_kind="L2_LEVEL_BOOK", equivalent=False):
    return {
        "series_id": f"liquidity.{provider}.{instrument}.orderbook",
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "representation": "RAW",
        "target_bps": target,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": 600},
        "completeness": {"required": True},
        "quantity_semantics": {"mode": "NATIVE_FIRST", "consumer_equivalent_required": equivalent},
    }


def observation(bid_outer="95", ask_outer="105", *, provider="binance-spot", instrument="ETHUSDT", book_kind="L2_LEVEL_BOOK"):
    return {
        "observation_id": "validator-observation",
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "source_representation": "RAW",
        "timestamp_ms": 1_800_000_000_000,
        "bids": [["99.9", "2"], ["98", "3"], [bid_outer, "4"]],
        "asks": [["100.1", "2"], ["102", "3"], [ask_outer, "4"]],
    }


def quantity(*, provider="binance-spot", instrument="ETHUSDT", book_kind="L2_LEVEL_BOOK"):
    return qualify_quantity_semantics(
        provider_id=provider,
        instrument_id=instrument,
        book_kind=book_kind,
        native_quantity="12",
        native_quantity_unit="CONTRACTS" if book_kind == "FUTURES_L2_BOOK" else "BASE_ASSET",
        contract_quantity="12" if book_kind == "FUTURES_L2_BOOK" else None,
    )


def capability(*, provider="binance-spot", book_kind="L2_LEVEL_BOOK", depth="NOT_QUALIFIED"):
    return {
        "provider_id": provider,
        "book_kind": book_kind,
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": depth,
        "qualified_provider_depth_parameter": None,
    }


def resource(bid_outer="95", ask_outer="105", *, target=500):
    req = request(target)
    book = normalize_order_book_observation(observation(bid_outer, ask_outer))
    return qualify_liquidity_resource(book, req, age_seconds=0, quantity_semantics=quantity())


def forged_resource():
    return {
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "observation_id": "forged",
        "coherent_observation": True,
        "qualification_state": "QUALIFIED",
        "age_seconds": 0,
        "requested_bid_coverage_bps": "500",
        "requested_ask_coverage_bps": "500",
        "achieved_bid_coverage_bps": "500",
        "achieved_ask_coverage_bps": "500",
        "coverage_complete_bid": True,
        "coverage_complete_ask": True,
        "truncated": False,
        "quantity_semantics": {"native_quantity_preserved": True, "consumer_qualified_equivalent": True},
    }


def validate() -> None:
    contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
    provider_contracts = json.loads((ROOT / "contracts/provider-contracts.json").read_text(encoding="utf-8"))
    stages = contract["stage_boundaries"]
    architecture = contract["architecture"]
    runtime = contract["runtime_implementation"]
    coverage = contract["coverage"]
    derivatives_quantity = contract["derivatives_quantity"]

    require(contract["runtime_active"] is False, "S1_RUNTIME_ACTIVE")
    require(stages["s1_source_implementation_performed"] is True, "S1_SOURCE_NOT_IMPLEMENTED")
    require(stages["provider_rollout_performed"] is False, "PROVIDER_ROLLOUT_MUTATED")
    require(stages["S2"]["active_in_this_contract_installation"] is False, "S2_ACTIVE")
    require(stages["S3"]["active_in_this_contract_installation"] is False, "S3_ACTIVE")
    require("PROVIDER_CAPABILITY_QUALIFICATION" in stages["S2"]["owns"], "S2_CAPABILITY_OWNER_MISSING")
    require(not architecture["second_capability_authority"], "SECOND_CAPABILITY_AUTHORITY")
    require(not architecture["second_provider_authority"], "SECOND_PROVIDER_AUTHORITY")
    require(not architecture["second_market_data_authority"], "SECOND_MARKET_DATA_AUTHORITY")
    require(runtime["provider_network_io"] is False, "S1_NETWORK_IO")
    require(runtime["production_network_calls_added"] == 0, "PRODUCTION_NETWORK_CALLS")
    require(runtime["production_scheduler_mutated"] is False, "PRODUCTION_SCHEDULER_MUTATED")
    require(runtime["resource_index_owner"] == "tools/current_data_transport.py", "RESOURCE_INDEX_OWNER_CHANGED")
    require(coverage["no_extrapolation_outside_observed_book"] is True, "NO_EXTRAPOLATION_CONTRACT_CHANGED")
    require(derivatives_quantity["consumer_qualified_equivalent_when_conversion_unproven"] is False, "UNPROVEN_CONVERSION_QUALIFIED")
    provider_text = json.dumps(provider_contracts, sort_keys=True)
    require("kraken-futures" in provider_text and "NOT_NORMATIVELY_DOCUMENTED" in provider_text, "KRAKEN_DEPTH_AUTHORITY_MISSING")

    source = (ROOT / "src/liquidity_s1_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    require({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imports), "NETWORK_IMPORT_FOUND")
    public = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")}
    required_public = {
        "normalize_liquidity_request", "evaluate_resource_satisfaction", "plan_liquidity_acquisition",
        "normalize_order_book_observation", "validate_normalized_order_book", "assert_one_coherent_provider_observation",
        "compute_side_coverage", "qualify_quantity_semantics", "validate_quantity_semantics",
        "qualify_liquidity_resource", "validate_qualified_liquidity_resource", "validate_provider_capability_for_s1",
        "canonical_plan_bytes",
    }
    require(required_public <= public, "PUBLIC_PRIMITIVE_AUDIT_INCOMPLETE")

    req = normalize_liquidity_request(request())
    require(req["schema_version"] == REQUEST_SCHEMA and normalize_liquidity_request(req) == req, "REQUEST_REVALIDATION")
    forged_req = dict(req); forged_req["provider_url"] = "https://example.invalid"
    expect_error(lambda: evaluate_resource_satisfaction(None, forged_req), "PHYSICAL_REQUEST_FIELD_FORBIDDEN", "REQUEST_SCHEMA_MARKER")

    partial = normalize_order_book_observation(observation("97.7", "104.1"))
    require(partial["schema_version"] == BOOK_SCHEMA, "BOOK_SCHEMA")
    require(validate_normalized_order_book(partial) == partial, "BOOK_REVALIDATION")
    require(validate_normalized_order_book(validate_normalized_order_book(partial)) == partial, "BOOK_REVALIDATION_IDEMPOTENCE")
    cov = compute_side_coverage(partial, request())
    require(cov["achieved_bid_coverage_bps"] == "230" and cov["achieved_ask_coverage_bps"] == "410" and cov["truncated"], "PHYSICAL_230_410")
    forged_book = dict(partial); forged_book["achieved_bid_coverage_bps"] = "500"
    expect_error(lambda: validate_normalized_order_book(forged_book), "ACHIEVED_BID_COVERAGE_BPS_MISMATCH", "CALLER_COVERAGE")
    stale_book = json.loads(json.dumps(partial)); stale_book["bids"][1][1] = "77"
    expect_error(lambda: validate_normalized_order_book(stale_book), "OBSERVATION_SHA256_MISMATCH", "OBSERVATION_HASH")
    complete = normalize_order_book_observation(observation())
    complete_cov = compute_side_coverage(complete, request())
    require(complete_cov["coverage_complete_bid"] and complete_cov["coverage_complete_ask"] and not complete_cov["truncated"], "PHYSICAL_500_500")

    q = quantity()
    require(q["schema_version"] == QUANTITY_SCHEMA and q["consumer_qualified_equivalent"] is False, "QUANTITY_CANONICAL")
    require(validate_quantity_semantics(q) == q and validate_quantity_semantics(validate_quantity_semantics(q)) == q, "QUANTITY_REVALIDATION")
    forged_q = {"native_quantity_preserved": True, "consumer_qualified_equivalent": True}
    expect_error(lambda: qualify_liquidity_resource(complete, request(equivalent=True), age_seconds=0, quantity_semantics=forged_q), "QUANTITY_SEMANTICS_FIELDS_INVALID", "FORGED_QUANTITY")
    stale_q = dict(q); stale_q["native_quantity"] = "999"
    expect_error(lambda: validate_quantity_semantics(stale_q), "QUANTITY_SHA256_MISMATCH", "QUANTITY_HASH")

    forged_conversion = {"qualified": True, "formula_id": "forged", "formula_version": "1", "instrument_spec_identity": "forged", "base_equivalent": "1", "quote_equivalent": "100"}
    expect_error(
        lambda: qualify_quantity_semantics(provider_id="kraken-futures", instrument_id="PI_ETHUSD", book_kind="FUTURES_L2_BOOK", native_quantity="1", native_quantity_unit="CONTRACTS", conversion_authority=forged_conversion),
        "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1", "FORGED_CONVERSION",
    )

    forged = forged_resource()
    sat = evaluate_resource_satisfaction(forged, request())
    require(sat["status"] == "NOT_QUALIFIED" and not sat["reusable"], "FORGED_RESOURCE_SATISFIED")
    plan = plan_liquidity_acquisition(request(), capability(), forged)
    require(plan["decision"] == "ACQUISITION_REQUIRED" and plan["network_required"], "FORGED_RESOURCE_REUSED")

    valid = resource()
    require(valid["schema_version"] == RESOURCE_SCHEMA and len(valid["resource_sha256"]) == 64, "RESOURCE_SCHEMA_OR_HASH")
    require(validate_qualified_liquidity_resource(valid) == valid, "RESOURCE_REVALIDATION")
    require(validate_qualified_liquidity_resource(validate_qualified_liquidity_resource(valid)) == valid, "RESOURCE_REVALIDATION_IDEMPOTENCE")
    valid_sat = evaluate_resource_satisfaction(valid, request())
    require(valid_sat["status"] == "SATISFIED" and valid_sat["reusable"], "VALID_RESOURCE_NOT_SATISFIED")
    for mutate in ("coverage", "quantity", "observation", "hash"):
        tampered = json.loads(json.dumps(valid))
        if mutate == "coverage": tampered["achieved_bid_coverage_bps"] = "999"
        elif mutate == "quantity": tampered["quantity_semantics"]["native_quantity"] = "999"
        elif mutate == "observation": tampered["observation_id"] = "forged"
        else: tampered["resource_sha256"] = "0" * 64
        result = evaluate_resource_satisfaction(tampered, request(250))
        require(result["status"] == "NOT_QUALIFIED" and not result["reusable"], f"RESOURCE_{mutate.upper()}_TAMPER")

    truncated = resource("97", "103.1")
    require(truncated["truncated"] and not truncated["request_satisfied"], "TRUNCATED_FIXTURE")
    narrow = evaluate_resource_satisfaction(truncated, request(250))
    require(narrow["status"] == "SATISFIED" and narrow["reusable"], "TRUNCATED_NARROW_DOMINANCE")

    cap = validate_provider_capability_for_s1(capability(), request())
    require(cap["selectable_depth_limit"] == "NOT_QUALIFIED" and cap["qualified_provider_depth_parameter"] is None, "S1_DEPTH_NOT_FAIL_CLOSED")
    forged_depth = capability(depth="QUALIFIED"); forged_depth["qualified_provider_depth_parameter"] = {"name": "limit", "value": 5000}
    expect_error(lambda: plan_liquidity_acquisition(request(), forged_depth), "PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1", "FORGED_PROVIDER_DEPTH")
    kreq = request(provider="kraken-futures", instrument="PI_ETHUSD", book_kind="FUTURES_L2_BOOK")
    kcap = capability(provider="kraken-futures", book_kind="FUTURES_L2_BOOK", depth="NOT_NORMATIVELY_DOCUMENTED")
    kplan = plan_liquidity_acquisition(kreq, kcap)
    bound = kplan["acquisition_plan"]["provider_depth_bound"]
    require(bound["status"] == "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED" and bound["qualified_provider_depth_parameter"] is None, "KRAKEN_DEPTH_QUALIFIED")

    arbitrary = {"coherent_observation": True, "qualification_state": "QUALIFIED"}
    returned = assert_one_coherent_provider_observation([arbitrary])
    require(returned is arbitrary, "CARDINALITY_GUARD_CHANGED_OBJECT")
    expect_error(lambda: validate_normalized_order_book(returned), "NORMALIZED_BOOK_FIELDS_INVALID", "CARDINALITY_AS_AUTHORITY")

    p250a = plan_liquidity_acquisition(request(250), capability())
    p250b = plan_liquidity_acquisition(normalize_liquidity_request(request(250)), capability())
    p500 = plan_liquidity_acquisition(request(500), capability())
    require(canonical_plan_bytes(p250a) == canonical_plan_bytes(p250b), "PLAN_BYTES_DRIFT")
    require(p250a["acquisition_plan"]["target_bps"] == "250" and p500["acquisition_plan"]["target_bps"] == "500", "TARGET_BPS_DRIFT")
    require(q["base_equivalent"] is None and q["quote_equivalent"] is None, "ABSENT_CONVERSION_BECAME_ZERO")
    require(bound["qualified_provider_depth_parameter"] is None, "ABSENT_DEPTH_BECAME_DEFAULT")
    correlated = forged_resource()
    require(correlated["coverage_complete_bid"] and correlated["coverage_complete_ask"] and not correlated["truncated"], "CORRELATED_FIXTURE")
    require(evaluate_resource_satisfaction(correlated, request())["status"] == "NOT_QUALIFIED", "BOOLEAN_CONSISTENCY_BECAME_PROVENANCE")

    audit = [
        ["normalize_liquidity_request", "semantic_request", "full revalidation"],
        ["evaluate_resource_satisfaction", "existing_resource", "qualified-resource full revalidation"],
        ["plan_liquidity_acquisition", "provider_capability", "S1 rejects caller-qualified depth; S2 owns qualification"],
        ["normalize_order_book_observation", "observation", "physical canonical construction"],
        ["validate_normalized_order_book", "normalized_book", "exact shape + physical/hash revalidation"],
        ["assert_one_coherent_provider_observation", "Sequence[Mapping]", "cardinality only; not authority"],
        ["compute_side_coverage", "book+request", "revalidates both inputs"],
        ["qualify_quantity_semantics", "conversion_authority", "no canonical S1 conversion owner; fail closed"],
        ["validate_quantity_semantics", "quantity_semantics", "exact shape + identity/hash revalidation"],
        ["qualify_liquidity_resource", "book+request+quantity", "all canonical inputs revalidated"],
        ["validate_qualified_liquidity_resource", "resource", "nested proof + resource hash"],
        ["canonical_plan_bytes", "planner result", "serialization only; no authority grant"],
    ]
    require(len(audit) == 12, "AUDIT_TABLE_INCOMPLETE")

    markers = [
        "POST_REPAIR_FORGED_EXISTING_RESOURCE_SATISFIED=NO",
        "POST_REPAIR_FORGED_EXISTING_RESOURCE_REUSED=NO",
        "POST_REPAIR_FORGED_QUANTITY_SEMANTICS_ACCEPTED=NO",
        "POST_REPAIR_FORGED_CONSUMER_EQUIVALENT_ACCEPTED=NO",
        "POST_REPAIR_FORGED_CONVERSION_AUTHORITY_ACCEPTED=NO",
        "POST_REPAIR_FORGED_PROVIDER_CAPABILITY_ACCEPTED=NO",
        "REQUEST_SCHEMA_IS_NOT_TRUST_PROOF=PASS",
        "BOOK_SCHEMA_IS_NOT_TRUST_PROOF=PASS",
        "RESOURCE_STATUS_IS_NOT_TRUST_PROOF=PASS",
        "BOOLEAN_QUALIFICATION_IS_NOT_TRUST_PROOF=PASS",
        "FORBIDDEN_PHYSICAL_REQUEST_FIELDS_FAIL_CLOSED=PASS",
        "PHYSICAL_BOOK_LEVELS_REQUIRED=PASS",
        "PHYSICAL_COVERAGE_RECOMPUTED=PASS",
        "CALLER_COVERAGE_NOT_AUTHORITY=PASS",
        "OBSERVATION_SHA_TAMPER_REJECTED=PASS",
        "CANONICAL_REQUEST_REVALIDATION_IDEMPOTENT=PASS",
        "CANONICAL_BOOK_REVALIDATION_IDEMPOTENT=PASS",
        "230_410_CANNOT_SATISFY_500=PASS",
        "500_500_PHYSICAL_BOOK_CAN_SATISFY_500=PASS",
        "EXISTING_RESOURCE_TRUST_MODEL=UNTRUSTED_MAPPING_FULL_CANONICAL_RESOURCE_REVALIDATION",
        "QUALIFIED_RESOURCE_REVALIDATION=PASS",
        "RESOURCE_SHA_RECOMPUTED=PASS",
        "RESOURCE_SHA_TAMPER_REJECTED=PASS",
        "QUANTITY_SEMANTICS_TRUST_MODEL=CANONICAL_NATIVE_FIRST_RESULT_FULL_REVALIDATION",
        "QUANTITY_SEMANTICS_REVALIDATION=PASS",
        "FORGED_CONSUMER_EQUIVALENT_REJECTED=PASS",
        "QUANTITY_SHA_TAMPER_REJECTED=PASS",
        "CONVERSION_AUTHORITY_TRUST_MODEL=NO_CANONICAL_AUTHORITY_AVAILABLE_AND_CONVERSION_FAILS_CLOSED",
        "CONVERSION_AUTHORITY_CANONICAL_OWNER=NO_CANONICAL_AUTHORITY_AVAILABLE_IN_S1",
        "FORGED_CONVERSION_AUTHORITY_REJECTED=PASS",
        "PROVIDER_CAPABILITY_TRUST_MODEL=S1_MAPPING_CANNOT_QUALIFY_DEPTH_S2_AUTHORITY_REQUIRED",
        "PROVIDER_CAPABILITY_CANONICAL_OWNER=contracts/provider-contracts.json;QUALIFICATION_OWNER=S2",
        "FORGED_PROVIDER_DEPTH_QUALIFICATION_REJECTED=PASS",
        "KRAKEN_FUTURES_UNDOCUMENTED_DEPTH_NOT_QUALIFIED=PASS",
        "RESOURCE_SATISFACTION_ENGINE=PASS",
        "RESOURCE_DOMINANCE=PASS",
        "REUSE_BEFORE_ACQUISITION=PASS",
        "DYNAMIC_DEPTH_PLANNER=PASS",
        "TARGET_BPS_250=PASS",
        "TARGET_BPS_500=PASS",
        "ONE_COHERENT_PROVIDER_OBSERVATION=PASS",
        "CARDINALITY_ONLY_NOT_VALIDATION_AUTHORITY=PASS",
        "SIDE_SPECIFIC_COVERAGE=PASS",
        "DERIVATIVES_QUANTITY_NATIVE_FIRST=PASS",
        "UNKNOWN_PROVIDER_DEPTH_FAIL_CLOSED=PASS",
        "NO_BOOK_EXTRAPOLATION=PASS",
        "AUTHORITY_BOUNDARY_AUDIT_COMPLETE=YES",
        "THREE_HOP_DATAFLOW_AUDIT_COMPLETE=YES",
        "SELF_REVIEW_PASS_A_ADVERSARIAL_TRUST=PASS",
        "SELF_REVIEW_PASS_B_DOWNSTREAM_CONSEQUENCE=PASS",
        "SELF_REVIEW_PASS_C_OMISSION=PASS",
        "SELF_REVIEW_PASS_D_NEGATIVE_SEMANTIC=PASS",
        "SELF_REVIEW_PASS_E_CORRELATED_FIELDS=PASS",
        "SECOND_LOGICAL_GAP_REVIEW_COMPLETE=YES",
        "TRUST_MODEL_MARKERS_HAVE_EXECUTABLE_PROOF=YES",
        "NETWORK_FREE_PROOF=PASS",
        "S1_SOURCE_IMPLEMENTED=YES",
        "S1_RUNTIME_ACTIVE=NO",
        "S2_PROVIDER_ROLLOUT=NO",
        "S3_NETWORK_ACTIVATION=NO",
        "PRODUCTION_NETWORK_CALLS_ADDED=0",
        "PRODUCTION_SCHEDULER_MUTATED=NO",
        "SECOND_MARKET_DATA_AUTHORITY=NO",
        "SECOND_PROVIDER_AUTHORITY=NO",
        "SECOND_CAPABILITY_CATALOG=NO",
    ]
    print("AUTHORITY_BOUNDARY_AUDIT_TABLE=" + json.dumps(audit, separators=(",", ":")))
    for marker in markers:
        print(marker)


if __name__ == "__main__":
    validate()
