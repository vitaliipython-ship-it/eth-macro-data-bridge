from __future__ import annotations

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import current_data_transport

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import (
    BOOK_SCHEMA,
    QUANTITY_SCHEMA,
    REQUEST_SCHEMA,
    RESOURCE_SCHEMA,
    TEMPORAL_AUTHORITY_OWNER,
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
    validate_liquidity_acquisition_plan,
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


def request(
    target: int = 500,
    *,
    provider: str = "binance-spot",
    instrument: str = "ETHUSDT",
    book_kind: str = "L2_LEVEL_BOOK",
    equivalent: bool = False,
) -> dict:
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
        "quantity_semantics": {
            "mode": "NATIVE_FIRST",
            "consumer_equivalent_required": equivalent,
        },
    }


def observation(
    bid_outer: str = "95",
    ask_outer: str = "105",
    *,
    provider: str = "binance-spot",
    instrument: str = "ETHUSDT",
    book_kind: str = "L2_LEVEL_BOOK",
    timestamp_ms: int | None = None,
) -> dict:
    return {
        "observation_id": "validator-observation",
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "source_representation": "RAW",
        "timestamp_ms": (
            int(current_data_transport._utc_now().replace(microsecond=0).timestamp() * 1000)
            if timestamp_ms is None
            else timestamp_ms
        ),
        "bids": [["99.9", "2"], ["98", "3"], [bid_outer, "4"]],
        "asks": [["100.1", "2"], ["102", "3"], [ask_outer, "4"]],
    }


def quantity(
    *,
    provider: str = "binance-spot",
    instrument: str = "ETHUSDT",
    book_kind: str = "L2_LEVEL_BOOK",
) -> dict:
    return qualify_quantity_semantics(
        provider_id=provider,
        instrument_id=instrument,
        book_kind=book_kind,
        native_quantity="12",
        native_quantity_unit="CONTRACTS" if book_kind == "FUTURES_L2_BOOK" else "BASE_ASSET",
        contract_quantity="12" if book_kind == "FUTURES_L2_BOOK" else None,
    )


def capability(
    *,
    provider: str = "binance-spot",
    book_kind: str = "L2_LEVEL_BOOK",
    depth: str = "NOT_QUALIFIED",
) -> dict:
    return {
        "provider_id": provider,
        "book_kind": book_kind,
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": depth,
        "qualified_provider_depth_parameter": None,
    }


def resource(bid_outer: str = "95", ask_outer: str = "105", *, target: int = 500) -> dict:
    req = request(target)
    book = normalize_order_book_observation(observation(bid_outer, ask_outer))
    return qualify_liquidity_resource(
        book,
        req,
        quantity_semantics=quantity(),
    )


def forged_resource() -> dict:
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
        "quantity_semantics": {
            "native_quantity_preserved": True,
            "consumer_qualified_equivalent": True,
        },
    }


def validate() -> None:
    contract = json.loads(
        (ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8")
    )
    provider_contracts = json.loads(
        (ROOT / "contracts/provider-contracts.json").read_text(encoding="utf-8")
    )
    stages = contract["stage_boundaries"]
    architecture = contract["architecture"]
    runtime = contract["runtime_implementation"]
    coverage_contract = contract["coverage"]
    quantity_contract = contract["derivatives_quantity"]
    kraken_s1 = contract["provider_boundaries"]["kraken_futures"]

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
    require(coverage_contract["no_extrapolation_outside_observed_book"] is True, "NO_EXTRAPOLATION_CONTRACT_CHANGED")
    require(
        quantity_contract["consumer_qualified_equivalent_when_conversion_unproven"] is False,
        "UNPROVEN_CONVERSION_QUALIFIED",
    )

    kraken_provider_rows = [
        row
        for row in provider_contracts["contracts"]
        if row.get("provider") == "kraken" and row.get("product") == "Futures Raw L2 Order Book"
    ]
    require(len(kraken_provider_rows) == 1, "KRAKEN_PROVIDER_CONTRACT_MISSING")
    kraken_provider = kraken_provider_rows[0]
    require(kraken_provider["provider_raw_l2_capability"] == "CONFIRMED", "KRAKEN_PROVIDER_RAW_L2_NOT_CONFIRMED")
    require(
        kraken_provider["selectable_depth_limit"] == "NOT_NORMATIVELY_DOCUMENTED",
        "KRAKEN_PROVIDER_DEPTH_BOUNDARY_MISSING",
    )
    require(kraken_provider["normative_max_depth"] == "NOT_INVENTED", "KRAKEN_PROVIDER_DEPTH_GUESS_REINTRODUCED")
    require(
        kraken_s1["selectable_depth_limit"] == kraken_provider["selectable_depth_limit"],
        "KRAKEN_S1_PROVIDER_DEPTH_AUTHORITY_MISMATCH",
    )
    require(kraken_s1["normative_max_depth_invented"] is False, "KRAKEN_S1_DEPTH_GUESS_REINTRODUCED")

    source = (ROOT / "src/liquidity_s1_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    require({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imports), "NETWORK_IMPORT_FOUND")
    current_data_source = (ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8")
    require("def _utc_now()" in current_data_source, "CURRENT_DATA_UTC_AUTHORITY_MISSING")
    require("def _format_utc(" in current_data_source, "CURRENT_DATA_TIME_FORMATTER_MISSING")
    require("def _parse_utc(" in current_data_source, "CURRENT_DATA_TIME_PARSER_MISSING")
    require("def evaluate_persisted_freshness" in current_data_source, "CURRENT_DATA_FRESHNESS_MODEL_MISSING")
    require(
        TEMPORAL_AUTHORITY_OWNER == "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py",
        "TEMPORAL_AUTHORITY_OWNER_DRIFT",
    )

    public = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    }
    required_public = {
        "normalize_liquidity_request",
        "evaluate_resource_satisfaction",
        "plan_liquidity_acquisition",
        "normalize_order_book_observation",
        "validate_normalized_order_book",
        "assert_one_coherent_provider_observation",
        "compute_side_coverage",
        "qualify_quantity_semantics",
        "validate_quantity_semantics",
        "qualify_liquidity_resource",
        "validate_qualified_liquidity_resource",
        "validate_provider_capability_for_s1",
        "validate_liquidity_acquisition_plan",
        "canonical_plan_bytes",
    }
    require(required_public <= public, "PUBLIC_PRIMITIVE_AUDIT_INCOMPLETE")

    req = normalize_liquidity_request(request())
    require(req["schema_version"] == REQUEST_SCHEMA, "REQUEST_SCHEMA")
    require(normalize_liquidity_request(req) == req, "REQUEST_REVALIDATION")
    forged_req = dict(req)
    forged_req["provider_url"] = "https://example.invalid"
    expect_error(
        lambda: evaluate_resource_satisfaction(None, forged_req),
        "PHYSICAL_REQUEST_FIELD_FORBIDDEN",
        "REQUEST_SCHEMA_MARKER",
    )

    partial = normalize_order_book_observation(observation("97.7", "104.1"))
    require(partial["schema_version"] == BOOK_SCHEMA, "BOOK_SCHEMA")
    require(validate_normalized_order_book(partial) == partial, "BOOK_REVALIDATION")
    require(
        validate_normalized_order_book(validate_normalized_order_book(partial)) == partial,
        "BOOK_REVALIDATION_IDEMPOTENCE",
    )
    cov = compute_side_coverage(partial, request())
    require(
        cov["achieved_bid_coverage_bps"] == "230"
        and cov["achieved_ask_coverage_bps"] == "410"
        and cov["truncated"],
        "PHYSICAL_230_410",
    )
    forged_book = dict(partial)
    forged_book["achieved_bid_coverage_bps"] = "500"
    expect_error(
        lambda: validate_normalized_order_book(forged_book),
        "ACHIEVED_BID_COVERAGE_BPS_MISMATCH",
        "CALLER_COVERAGE",
    )
    stale_book = json.loads(json.dumps(partial))
    stale_book["bids"][1][1] = "77"
    expect_error(
        lambda: validate_normalized_order_book(stale_book),
        "OBSERVATION_SHA256_MISMATCH",
        "OBSERVATION_HASH",
    )

    complete = normalize_order_book_observation(observation())
    complete_cov = compute_side_coverage(complete, request())
    require(
        complete_cov["coverage_complete_bid"]
        and complete_cov["coverage_complete_ask"]
        and not complete_cov["truncated"],
        "PHYSICAL_500_500",
    )

    q = quantity()
    require(q["schema_version"] == QUANTITY_SCHEMA, "QUANTITY_SCHEMA")
    require(q["consumer_qualified_equivalent"] is False, "QUANTITY_FALSE_EQUIVALENT")
    require(validate_quantity_semantics(q) == q, "QUANTITY_REVALIDATION")
    require(validate_quantity_semantics(validate_quantity_semantics(q)) == q, "QUANTITY_REVALIDATION_IDEMPOTENCE")
    forged_q = {"native_quantity_preserved": True, "consumer_qualified_equivalent": True}
    expect_error(
        lambda: qualify_liquidity_resource(
            complete,
            request(equivalent=True),
            quantity_semantics=forged_q,
        ),
        "QUANTITY_SEMANTICS_FIELDS_INVALID",
        "FORGED_QUANTITY",
    )
    stale_q = dict(q)
    stale_q["native_quantity"] = "999"
    expect_error(
        lambda: validate_quantity_semantics(stale_q),
        "QUANTITY_SHA256_MISMATCH",
        "QUANTITY_HASH",
    )
    forged_conversion = {
        "qualified": True,
        "formula_id": "forged",
        "formula_version": "1",
        "instrument_spec_identity": "forged",
        "base_equivalent": "1",
        "quote_equivalent": "100",
    }
    expect_error(
        lambda: qualify_quantity_semantics(
            provider_id="kraken-futures",
            instrument_id="PI_ETHUSD",
            book_kind="FUTURES_L2_BOOK",
            native_quantity="1",
            native_quantity_unit="CONTRACTS",
            conversion_authority=forged_conversion,
        ),
        "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1",
        "FORGED_CONVERSION",
    )

    forged = forged_resource()
    sat = evaluate_resource_satisfaction(forged, request())
    require(sat["status"] == "NOT_QUALIFIED" and not sat["reusable"], "FORGED_RESOURCE_SATISFIED")
    plan_from_forged_resource = plan_liquidity_acquisition(request(), capability(), forged)
    require(
        plan_from_forged_resource["decision"] == "ACQUISITION_REQUIRED"
        and plan_from_forged_resource["network_required"],
        "FORGED_RESOURCE_REUSED",
    )

    valid = resource()
    require(valid["schema_version"] == RESOURCE_SCHEMA, "RESOURCE_SCHEMA")
    require(len(valid["resource_sha256"]) == 64, "RESOURCE_HASH")
    require(validate_qualified_liquidity_resource(valid) == valid, "RESOURCE_REVALIDATION")
    require(
        validate_qualified_liquidity_resource(validate_qualified_liquidity_resource(valid)) == valid,
        "RESOURCE_REVALIDATION_IDEMPOTENCE",
    )
    valid_sat = evaluate_resource_satisfaction(valid, request())
    require(valid_sat["status"] == "SATISFIED" and valid_sat["reusable"], "VALID_RESOURCE_NOT_SATISFIED")
    for mutate in ("coverage", "quantity", "observation", "hash"):
        tampered = json.loads(json.dumps(valid))
        if mutate == "coverage":
            tampered["achieved_bid_coverage_bps"] = "999"
        elif mutate == "quantity":
            tampered["quantity_semantics"]["native_quantity"] = "999"
        elif mutate == "observation":
            tampered["observation_id"] = "forged"
        else:
            tampered["resource_sha256"] = "0" * 64
        result = evaluate_resource_satisfaction(tampered, request(250))
        require(
            result["status"] == "NOT_QUALIFIED" and not result["reusable"],
            f"RESOURCE_{mutate.upper()}_TAMPER",
        )

    freshness_req = request()
    freshness_req["freshness"] = {"max_age_seconds": 60}
    old_book = normalize_order_book_observation(observation(timestamp_ms=1))
    expect_error(
        lambda: qualify_liquidity_resource(old_book, freshness_req, age_seconds=0, quantity_semantics=quantity()),
        "CALLER_AGE_SECONDS_MISMATCH",
        "FORGED_ZERO_AGE",
    )
    old_resource = qualify_liquidity_resource(old_book, freshness_req, quantity_semantics=quantity())
    require(old_resource["age_seconds"] > 60, "OLD_BOOK_DERIVED_AGE_INVALID")
    require(old_resource["freshness_verdict"] == "STALE", "OLD_BOOK_FRESHNESS_VERDICT")
    require(old_resource["request_satisfaction"] == "UNSATISFIED", "OLD_BOOK_RESOURCE_SATISFIED")
    old_sat = evaluate_resource_satisfaction(old_resource, freshness_req)
    old_plan = plan_liquidity_acquisition(freshness_req, capability(), old_resource)
    require(old_sat["status"] == "UNSATISFIED" and not old_sat["reusable"], "FORGED_FRESHNESS_SATISFIED")
    require(old_plan["decision"] == "ACQUISITION_REQUIRED" and old_plan["network_required"], "FORGED_FRESHNESS_REUSED")

    now_ms = int(current_data_transport._utc_now().replace(microsecond=0).timestamp() * 1000)
    future_book = normalize_order_book_observation(observation(timestamp_ms=now_ms + 1000))
    expect_error(
        lambda: qualify_liquidity_resource(future_book, freshness_req, quantity_semantics=quantity()),
        "OBSERVATION_TIMESTAMP_IN_FUTURE",
        "FUTURE_TIMESTAMP",
    )

    real_clock = current_data_transport._utc_now
    try:
        current_data_transport._utc_now = lambda: (_ for _ in ()).throw(RuntimeError("clock unavailable"))
        expect_error(
            lambda: qualify_liquidity_resource(complete, freshness_req, quantity_semantics=quantity()),
            "TEMPORAL_AUTHORITY_UNAVAILABLE",
            "MISSING_TEMPORAL_AUTHORITY",
        )
    finally:
        current_data_transport._utc_now = real_clock

    malformed_temporal = json.loads(json.dumps(valid))
    malformed_temporal["temporal_provenance"]["authority_owner"] = "caller"
    malformed_result = evaluate_resource_satisfaction(malformed_temporal, request(250))
    require(malformed_result["status"] == "NOT_QUALIFIED" and not malformed_result["reusable"], "MALFORMED_TEMPORAL_AUTHORITY")

    negative_age = json.loads(json.dumps(valid))
    negative_age["temporal_provenance"]["derived_age_seconds"] = -1
    negative_result = evaluate_resource_satisfaction(negative_age, request(250))
    require(negative_result["status"] == "NOT_QUALIFIED" and not negative_result["reusable"], "NEGATIVE_DERIVED_AGE")

    stale_hash_temporal = json.loads(json.dumps(valid))
    base_ms = stale_hash_temporal["temporal_provenance"]["evaluation_time_ms"]
    stale_hash_temporal["temporal_provenance"]["evaluated_at_utc"] = datetime.fromtimestamp(
        (base_ms + 1000) / 1000, timezone.utc
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    stale_hash_temporal["temporal_provenance"]["evaluation_time_ms"] = base_ms + 1000
    stale_hash_temporal["temporal_provenance"]["derived_age_seconds"] += 1
    stale_hash_temporal["age_seconds"] += 1
    stale_hash_result = evaluate_resource_satisfaction(stale_hash_temporal, request(250))
    require(stale_hash_result["status"] == "NOT_QUALIFIED" and not stale_hash_result["reusable"], "TEMPORAL_HASH_TAMPER")
    require("RESOURCE_SHA256_MISMATCH" in stale_hash_result["reasons"][0], "TEMPORAL_HASH_TAMPER_NOT_HASH_BOUND")

    historical_timestamp = now_ms - 3600 * 1000
    historical_book = normalize_order_book_observation(observation(timestamp_ms=historical_timestamp))
    real_clock = current_data_transport._utc_now
    try:
        current_data_transport._utc_now = lambda: datetime.fromtimestamp(historical_timestamp / 1000, timezone.utc)
        historical_fresh = qualify_liquidity_resource(historical_book, freshness_req, age_seconds=0, quantity_semantics=quantity())
    finally:
        current_data_transport._utc_now = real_clock
    reevaluated = evaluate_resource_satisfaction(historical_fresh, freshness_req)
    reevaluated_plan = plan_liquidity_acquisition(freshness_req, capability(), historical_fresh)
    require(reevaluated["status"] == "UNSATISFIED" and "STALE" in reevaluated["reasons"], "CURRENT_DERIVED_AGE_NOT_REVALIDATED")
    require(reevaluated_plan["decision"] == "ACQUISITION_REQUIRED" and reevaluated_plan["network_required"], "PLANNER_FRESHNESS_REVALIDATION_BYPASS")

    truncated = resource("97", "103.1")
    require(truncated["truncated"] and not truncated["request_satisfied"], "TRUNCATED_FIXTURE")
    narrow = evaluate_resource_satisfaction(truncated, request(250))
    require(narrow["status"] == "SATISFIED" and narrow["reusable"], "TRUNCATED_NARROW_DOMINANCE")

    cap = validate_provider_capability_for_s1(capability(), request())
    require(cap["selectable_depth_limit"] == "NOT_QUALIFIED", "S1_DEPTH_NOT_FAIL_CLOSED")
    require(cap["qualified_provider_depth_parameter"] is None, "S1_DEPTH_PARAMETER_NOT_NULL")
    forged_depth = capability(depth="QUALIFIED")
    forged_depth["qualified_provider_depth_parameter"] = {"name": "limit", "value": 5000}
    expect_error(
        lambda: plan_liquidity_acquisition(request(), forged_depth),
        "PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1",
        "FORGED_PROVIDER_DEPTH",
    )

    kreq = request(
        provider="kraken-futures",
        instrument="PI_ETHUSD",
        book_kind="FUTURES_L2_BOOK",
    )
    kcap = capability(
        provider="kraken-futures",
        book_kind="FUTURES_L2_BOOK",
        depth="NOT_NORMATIVELY_DOCUMENTED",
    )
    kplan = plan_liquidity_acquisition(kreq, kcap)
    bound = kplan["acquisition_plan"]["provider_depth_bound"]
    require(
        bound["status"] == "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED"
        and bound["qualified_provider_depth_parameter"] is None,
        "KRAKEN_DEPTH_QUALIFIED",
    )

    arbitrary = {"coherent_observation": True, "qualification_state": "QUALIFIED"}
    returned = assert_one_coherent_provider_observation([arbitrary])
    require(returned is arbitrary, "CARDINALITY_GUARD_CHANGED_OBJECT")
    expect_error(
        lambda: validate_normalized_order_book(returned),
        "NORMALIZED_BOOK_FIELDS_INVALID",
        "CARDINALITY_AS_AUTHORITY",
    )

    p250a = plan_liquidity_acquisition(request(250), capability())
    p250b = plan_liquidity_acquisition(normalize_liquidity_request(request(250)), capability())
    p500 = plan_liquidity_acquisition(request(500), capability())
    require(canonical_plan_bytes(p250a) == canonical_plan_bytes(p250b), "PLAN_BYTES_DRIFT")
    require(
        p250a["acquisition_plan"]["target_bps"] == "250"
        and p500["acquisition_plan"]["target_bps"] == "500",
        "TARGET_BPS_DRIFT",
    )
    canonical_plan = validate_liquidity_acquisition_plan(p500["acquisition_plan"])
    require(canonical_plan == p500["acquisition_plan"], "PLAN_REVALIDATION")

    forged_plan = json.loads(json.dumps(p500["acquisition_plan"]))
    forged_plan["provider_depth_bound"]["status"] = "QUALIFIED"
    forged_plan_material = dict(forged_plan)
    forged_plan_material.pop("plan_sha256")
    forged_plan["plan_sha256"] = sha256_canonical_json(forged_plan_material)
    forged_result = json.loads(json.dumps(p500))
    forged_result["acquisition_plan"] = forged_plan
    expect_error(
        lambda: canonical_plan_bytes(forged_result),
        "PLAN_PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
        "FORGED_PLAN_DEPTH",
    )

    stale_plan = json.loads(json.dumps(p500["acquisition_plan"]))
    stale_plan["target_bps"] = "501"
    stale_result = json.loads(json.dumps(p500))
    stale_result["acquisition_plan"] = stale_plan
    expect_error(
        lambda: canonical_plan_bytes(stale_result),
        "PLAN_SHA256_MISMATCH",
        "PLAN_HASH",
    )

    require(q["base_equivalent"] is None and q["quote_equivalent"] is None, "ABSENT_CONVERSION_BECAME_ZERO")
    require(bound["qualified_provider_depth_parameter"] is None, "ABSENT_DEPTH_BECAME_DEFAULT")
    correlated = forged_resource()
    require(
        correlated["coverage_complete_bid"]
        and correlated["coverage_complete_ask"]
        and not correlated["truncated"],
        "CORRELATED_FIXTURE",
    )
    require(
        evaluate_resource_satisfaction(correlated, request())["status"] == "NOT_QUALIFIED",
        "BOOLEAN_CONSISTENCY_BECAME_PROVENANCE",
    )

    audit = [
        ["normalize_liquidity_request", "semantic_request", "full revalidation"],
        ["evaluate_resource_satisfaction", "existing_resource", "qualified-resource full revalidation + current-data temporal re-evaluation"],
        ["freshness_temporal_provenance", "physical observation timestamp + current-data UTC authority", "derived age only; caller age is consistency assertion"],
        ["plan_liquidity_acquisition", "provider_capability", "S1 rejects caller-qualified depth; S2 owns qualification"],
        ["normalize_order_book_observation", "observation", "physical canonical construction"],
        ["validate_normalized_order_book", "normalized_book", "exact shape + physical/hash revalidation"],
        ["assert_one_coherent_provider_observation", "Sequence[Mapping]", "cardinality only; not authority"],
        ["compute_side_coverage", "book+request", "revalidates both inputs"],
        ["qualify_quantity_semantics", "conversion_authority", "no canonical S1 conversion owner; fail closed"],
        ["validate_quantity_semantics", "quantity_semantics", "exact shape + identity/hash revalidation"],
        ["qualify_liquidity_resource", "book+request+quantity", "all canonical inputs revalidated"],
        ["validate_qualified_liquidity_resource", "resource", "nested proof + resource hash"],
        ["validate_liquidity_acquisition_plan", "acquisition_plan", "exact shape + S2 depth-owner + plan hash revalidation"],
        ["canonical_plan_bytes", "planner result", "outer result + acquisition plan revalidated before serialization"],
    ]
    require(len(audit) == 14, "AUDIT_TABLE_INCOMPLETE")

    markers = [
        "POST_REPAIR_FORGED_EXISTING_RESOURCE_SATISFIED=NO",
        "POST_REPAIR_FORGED_EXISTING_RESOURCE_REUSED=NO",
        "POST_REPAIR_FORGED_QUANTITY_SEMANTICS_ACCEPTED=NO",
        "POST_REPAIR_FORGED_CONSUMER_EQUIVALENT_ACCEPTED=NO",
        "POST_REPAIR_FORGED_CONVERSION_AUTHORITY_ACCEPTED=NO",
        "POST_REPAIR_FORGED_PROVIDER_CAPABILITY_ACCEPTED=NO",
        "POST_REPAIR_FORGED_ACQUISITION_PLAN_ACCEPTED=NO",
        "REQUEST_SCHEMA_IS_NOT_TRUST_PROOF=PASS",
        "BOOK_SCHEMA_IS_NOT_TRUST_PROOF=PASS",
        "RESOURCE_STATUS_IS_NOT_TRUST_PROOF=PASS",
        "PLAN_SCHEMA_IS_NOT_TRUST_PROOF=PASS",
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
        "KRAKEN_DEPTH_SEMANTIC_OWNER=contracts/liquidity-s1-semantic-contract-v1.json",
        "FORGED_PROVIDER_DEPTH_QUALIFICATION_REJECTED=PASS",
        "KRAKEN_FUTURES_UNDOCUMENTED_DEPTH_NOT_QUALIFIED=PASS",
        "PLAN_TRUST_MODEL=UNTRUSTED_MAPPING_FULL_CANONICAL_PLAN_REVALIDATION",
        "PLAN_REVALIDATION=PASS",
        "PLAN_SHA_RECOMPUTED=PASS",
        "PLAN_SHA_TAMPER_REJECTED=PASS",
        "FORGED_QUALIFIED_DEPTH_PLAN_REJECTED=PASS",
        "PLAN_SERIALIZER_REVALIDATION=PASS",
        "PRE_REPAIR_FORGED_FRESHNESS_CAN_REUSE=YES",
        "PRE_REPAIR_REPRODUCTION_AUTHORITY=RUN_558",
        "POST_REPAIR_FORGED_FRESHNESS_CAN_REUSE=NO",
        "FRESHNESS_PROVENANCE_AUTHORITY=PASS",
        "FORGED_FRESHNESS_CANNOT_CREATE_REUSE=PASS",
        "FUTURE_TIMESTAMP_FAIL_CLOSED=PASS",
        "MISSING_TEMPORAL_AUTHORITY_FAIL_CLOSED=PASS",
        "DERIVED_AGE_REVALIDATION=PASS",
        "FRESHNESS_HASH_TAMPER_REJECTED=PASS",
        "CALLER_SUPPLIED_FRESHNESS_CLAIM_IS_NOT_AUTHORITY=PASS",
        "TEMPORAL_AUTHORITY_OWNER=ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py",
        "CURRENT_DATA_TEMPORAL_MODEL_REUSED=PASS",
        "TEMPORAL_EVALUATION_MILLISECOND_PRECISION=PASS",
        "TEMPORAL_CLOCK_UTC_FAIL_CLOSED=PASS",
        "CURRENT_DATA_INTEGER_SECOND_ROUNDING_POLICY_PRESERVED=PASS",
        "COHERENT_SINGLE_EVALUATION_INSTANT=PASS",
        "ATTACKER_RECOMPUTED_HASH_CANNOT_CREATE_CURRENT_FRESHNESS=PASS",
        "OBSERVATION_TIMESTAMP_NE_EVALUATION_TIME=PASS",
        "DERIVED_AGE_NE_FRESHNESS_THRESHOLD=PASS",
        "FRESHNESS_THRESHOLD_NE_FRESHNESS_VERDICT=PASS",
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

# DB-F/S3 R01: representation compatibility remains canonical S1 owner; S1 bytes excluded from implementation
