from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from canonical_json import canonical_json, sha256_canonical_json

REQUEST_SCHEMA = "liquidity-s1-semantic-request/1.0.0"
PLAN_SCHEMA = "liquidity-s1-acquisition-plan/1.0.0"
BOOK_SCHEMA = "liquidity-s1-normalized-book/1.0.0"
RESOURCE_SCHEMA = "liquidity-s1-qualified-resource/1.0.0"

BOOK_KINDS = {
    "L2_LEVEL_BOOK",
    "PROVIDER_GROUPED_L2",
    "L3_ORDER_BOOK",
    "FUTURES_L2_BOOK",
}
REPRESENTATIONS = {"RAW", "NORMALIZED", "PROFILE", "SUMMARY"}
FAIL_CLOSED_STATES = {
    "UNAVAILABLE",
    "NOT_QUALIFIED",
    "SOURCE_CONFLICT",
    "MISALIGNED",
    "UNKNOWN",
}
FORBIDDEN_REQUEST_FIELDS = {
    "provider_url",
    "rest_endpoint",
    "websocket_endpoint",
    "filesystem_path",
    "manifest_path",
    "resource_path",
    "provider_level_count",
    "provider_depth_parameter",
    "depth",
    "limit",
}
MIDPOINT_ANCHOR = "BEST_BID_ASK_MIDPOINT"
NORMALIZED_BOOK_FIELDS = {
    "schema_version",
    "observation_id",
    "observation_sha256",
    "provider_id",
    "instrument_id",
    "book_kind",
    "source_representation",
    "representation",
    "timestamp_ms",
    "reference_price_anchor",
    "reference_price",
    "best_bid",
    "best_ask",
    "bids",
    "asks",
    "achieved_bid_coverage_bps",
    "achieved_ask_coverage_bps",
    "native_quantity_preserved",
}


class LiquidityS1Error(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise LiquidityS1Error(code)


def _decimal(value: Any, field: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise LiquidityS1Error(f"{field}_INVALID")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LiquidityS1Error(f"{field}_INVALID") from exc
    if not number.is_finite():
        raise LiquidityS1Error(f"{field}_NON_FINITE")
    if positive and number <= 0:
        raise LiquidityS1Error(f"{field}_NOT_POSITIVE")
    if nonnegative and number < 0:
        raise LiquidityS1Error(f"{field}_NEGATIVE")
    return number


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _positive_int(value: Any, field: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value > 0, f"{field}_INVALID")
    return int(value)


def normalize_liquidity_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(payload, Mapping), "REQUEST_OBJECT_REQUIRED")
    forbidden = set(payload) & FORBIDDEN_REQUEST_FIELDS
    _require(not forbidden, "PHYSICAL_REQUEST_FIELD_FORBIDDEN")
    allowed = {
        "schema_version",
        "series_id",
        "provider_id",
        "instrument_id",
        "book_kind",
        "representation",
        "target_bps",
        "requested_bid_coverage_bps",
        "requested_ask_coverage_bps",
        "bucket_bps",
        "freshness",
        "completeness",
        "quantity_semantics",
    }
    _require(not (set(payload) - allowed), "UNKNOWN_REQUEST_FIELD")
    _require(payload.get("schema_version", REQUEST_SCHEMA) == REQUEST_SCHEMA, "REQUEST_SCHEMA_INVALID")
    for field in ("series_id", "provider_id", "instrument_id"):
        value = payload.get(field)
        _require(isinstance(value, str) and bool(value) and "\n" not in value and "\r" not in value, f"{field.upper()}_INVALID")
    book_kind = payload.get("book_kind")
    representation = payload.get("representation")
    _require(book_kind in BOOK_KINDS, "BOOK_KIND_UNKNOWN")
    _require(representation in REPRESENTATIONS, "REPRESENTATION_UNKNOWN")
    target = _decimal(payload.get("target_bps"), "TARGET_BPS", positive=True)
    bid_target = _decimal(payload.get("requested_bid_coverage_bps", target), "REQUESTED_BID_COVERAGE_BPS", positive=True)
    ask_target = _decimal(payload.get("requested_ask_coverage_bps", target), "REQUESTED_ASK_COVERAGE_BPS", positive=True)
    bucket = _decimal(payload.get("bucket_bps"), "BUCKET_BPS", positive=True)
    freshness = payload.get("freshness")
    _require(isinstance(freshness, Mapping) and set(freshness) == {"max_age_seconds"}, "FRESHNESS_INVALID")
    max_age = _positive_int(freshness.get("max_age_seconds"), "MAX_AGE_SECONDS")
    completeness = payload.get("completeness")
    _require(isinstance(completeness, Mapping) and set(completeness) == {"required"}, "COMPLETENESS_INVALID")
    _require(isinstance(completeness.get("required"), bool), "COMPLETENESS_REQUIRED_INVALID")
    quantity = payload.get("quantity_semantics", {"mode": "NATIVE_FIRST", "consumer_equivalent_required": False})
    _require(isinstance(quantity, Mapping), "QUANTITY_SEMANTICS_INVALID")
    _require(set(quantity) == {"mode", "consumer_equivalent_required"}, "QUANTITY_SEMANTICS_INVALID")
    _require(quantity.get("mode") == "NATIVE_FIRST", "QUANTITY_MODE_INVALID")
    _require(isinstance(quantity.get("consumer_equivalent_required"), bool), "CONSUMER_EQUIVALENT_REQUIREMENT_INVALID")
    return {
        "schema_version": REQUEST_SCHEMA,
        "series_id": payload["series_id"],
        "provider_id": payload["provider_id"],
        "instrument_id": payload["instrument_id"],
        "book_kind": book_kind,
        "representation": representation,
        "target_bps": _canonical_decimal(target),
        "requested_bid_coverage_bps": _canonical_decimal(bid_target),
        "requested_ask_coverage_bps": _canonical_decimal(ask_target),
        "bucket_bps": _canonical_decimal(bucket),
        "freshness": {"max_age_seconds": max_age},
        "completeness": {"required": completeness["required"]},
        "quantity_semantics": {
            "mode": "NATIVE_FIRST",
            "consumer_equivalent_required": quantity["consumer_equivalent_required"],
        },
    }


def _representation_compatible(existing: str, requested: str) -> bool:
    # Accepted S1 SSOT only proves exact representation reuse plus RAW -> PROFILE derivation.
    return existing == requested or (existing == "RAW" and requested == "PROFILE")


def evaluate_resource_satisfaction(
    existing_resource: Mapping[str, Any] | None,
    semantic_request: Mapping[str, Any],
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    if existing_resource is None:
        return {"status": "UNSATISFIED", "reusable": False, "reasons": ["RESOURCE_ABSENT"]}
    reasons: list[str] = []
    for field in ("provider_id", "instrument_id", "book_kind", "representation", "observation_id"):
        if not isinstance(existing_resource.get(field), str) or not existing_resource.get(field):
            reasons.append(f"{field.upper()}_MISSING")
    if reasons:
        return {"status": "NOT_QUALIFIED", "reusable": False, "reasons": sorted(reasons)}
    if existing_resource["provider_id"] != request["provider_id"]:
        reasons.append("PROVIDER_MISMATCH")
    if existing_resource["instrument_id"] != request["instrument_id"]:
        reasons.append("INSTRUMENT_MISMATCH")
    if existing_resource["book_kind"] != request["book_kind"]:
        reasons.append("BOOK_KIND_MISMATCH")
    if not _representation_compatible(existing_resource["representation"], request["representation"]):
        reasons.append("REPRESENTATION_NOT_DOMINATING")

    if existing_resource.get("coherent_observation") is not True:
        reasons.append("OBSERVATION_NOT_COHERENT")
    state = existing_resource.get("qualification_state")
    if state != "QUALIFIED":
        reasons.append(f"QUALIFICATION_{state or 'MISSING'}")
    age = existing_resource.get("age_seconds")
    if not isinstance(age, int) or isinstance(age, bool) or age < 0:
        reasons.append("FRESHNESS_NOT_QUALIFIED")
    elif age > request["freshness"]["max_age_seconds"]:
        reasons.append("STALE")

    try:
        bid = _decimal(existing_resource.get("achieved_bid_coverage_bps"), "ACHIEVED_BID_COVERAGE_BPS", nonnegative=True)
        ask = _decimal(existing_resource.get("achieved_ask_coverage_bps"), "ACHIEVED_ASK_COVERAGE_BPS", nonnegative=True)
        req_bid = _decimal(request["requested_bid_coverage_bps"], "REQUESTED_BID_COVERAGE_BPS", positive=True)
        req_ask = _decimal(request["requested_ask_coverage_bps"], "REQUESTED_ASK_COVERAGE_BPS", positive=True)
        own_bid_req = _decimal(existing_resource.get("requested_bid_coverage_bps"), "RESOURCE_REQUESTED_BID_COVERAGE_BPS", positive=True)
        own_ask_req = _decimal(existing_resource.get("requested_ask_coverage_bps"), "RESOURCE_REQUESTED_ASK_COVERAGE_BPS", positive=True)
        own_bid_complete = existing_resource.get("coverage_complete_bid")
        own_ask_complete = existing_resource.get("coverage_complete_ask")
        truncated = existing_resource.get("truncated")
        if not isinstance(own_bid_complete, bool) or own_bid_complete != (bid >= own_bid_req):
            reasons.append("BID_COMPLETENESS_MARKER_INCONSISTENT")
        if not isinstance(own_ask_complete, bool) or own_ask_complete != (ask >= own_ask_req):
            reasons.append("ASK_COMPLETENESS_MARKER_INCONSISTENT")
        if not isinstance(truncated, bool) or truncated != (not (bool(own_bid_complete) and bool(own_ask_complete))):
            reasons.append("TRUNCATION_MARKER_INCONSISTENT")
        if bid < req_bid:
            reasons.append("BID_COVERAGE_INSUFFICIENT")
        if ask < req_ask:
            reasons.append("ASK_COVERAGE_INSUFFICIENT")
    except LiquidityS1Error:
        reasons.append("COVERAGE_NOT_QUALIFIED")

    quantity = existing_resource.get("quantity_semantics")
    if not isinstance(quantity, Mapping) or quantity.get("native_quantity_preserved") is not True:
        reasons.append("NATIVE_QUANTITY_NOT_PRESERVED")
    elif request["quantity_semantics"]["consumer_equivalent_required"] and quantity.get("consumer_qualified_equivalent") is not True:
        reasons.append("CONSUMER_EQUIVALENT_NOT_QUALIFIED")

    if reasons:
        fail_closed = any(
            reason.startswith("QUALIFICATION_") and reason.removeprefix("QUALIFICATION_") in FAIL_CLOSED_STATES
            for reason in reasons
        )
        return {
            "status": "NOT_QUALIFIED" if fail_closed else "UNSATISFIED",
            "reusable": False,
            "reasons": sorted(set(reasons)),
        }
    return {"status": "SATISFIED", "reusable": True, "reasons": []}


def plan_liquidity_acquisition(
    semantic_request: Mapping[str, Any],
    provider_capability: Mapping[str, Any],
    existing_resource: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    satisfaction = evaluate_resource_satisfaction(existing_resource, request)
    if satisfaction["status"] == "SATISFIED":
        return {
            "decision": "REUSE",
            "network_required": False,
            "resource_satisfaction": satisfaction,
            "acquisition_plan": None,
        }

    _require(isinstance(provider_capability, Mapping), "PROVIDER_CAPABILITY_INVALID")
    _require(provider_capability.get("provider_id") == request["provider_id"], "CAPABILITY_PROVIDER_MISMATCH")
    _require(provider_capability.get("book_kind") == request["book_kind"], "CAPABILITY_BOOK_KIND_MISMATCH")
    _require(provider_capability.get("raw_book_capability") in {"CONFIRMED", "AVAILABLE_EXTERNALLY"}, "RAW_BOOK_CAPABILITY_NOT_QUALIFIED")
    depth_status = provider_capability.get("selectable_depth_limit")
    qualified_limit = provider_capability.get("qualified_provider_depth_parameter")
    if depth_status == "NOT_NORMATIVELY_DOCUMENTED":
        _require(qualified_limit is None, "UNQUALIFIED_DEPTH_PARAMETER_PRESENT")
        bound = {
            "status": "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
            "qualified_provider_depth_parameter": None,
        }
    elif depth_status == "QUALIFIED":
        _require(
            isinstance(qualified_limit, Mapping)
            and isinstance(qualified_limit.get("name"), str)
            and bool(qualified_limit.get("name"))
            and qualified_limit.get("value") is not None,
            "QUALIFIED_DEPTH_PARAMETER_INVALID",
        )
        bound = {
            "status": "QUALIFIED",
            "qualified_provider_depth_parameter": dict(qualified_limit),
        }
    else:
        _require(qualified_limit is None, "UNQUALIFIED_DEPTH_PARAMETER_PRESENT")
        bound = {
            "status": "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
            "qualified_provider_depth_parameter": None,
        }

    plan = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": "DYNAMIC_DEPTH_ACQUISITION_PLAN",
        "provider_id": request["provider_id"],
        "instrument_id": request["instrument_id"],
        "book_kind": request["book_kind"],
        "requested_representation": request["representation"],
        "requested_bid_coverage_bps": request["requested_bid_coverage_bps"],
        "requested_ask_coverage_bps": request["requested_ask_coverage_bps"],
        "target_bps": request["target_bps"],
        "bucket_bps": request["bucket_bps"],
        "freshness": request["freshness"],
        "completeness": request["completeness"],
        "observation_rule": "ONE_COHERENT_PROVIDER_OBSERVATION",
        "retry_semantics": "NEW_OBSERVATION",
        "stitching": "FORBIDDEN",
        "provider_depth_bound": bound,
        "network_execution": "NOT_IMPLEMENTED_BY_S1",
    }
    plan["plan_sha256"] = sha256_canonical_json(plan)
    return {
        "decision": "ACQUISITION_REQUIRED",
        "network_required": True,
        "resource_satisfaction": satisfaction,
        "acquisition_plan": plan,
    }


def _normalize_levels(levels: Any, side: str) -> list[list[str]]:
    _require(isinstance(levels, Sequence) and not isinstance(levels, (str, bytes)) and bool(levels), f"{side}_LEVELS_INVALID")
    parsed: list[tuple[Decimal, Decimal]] = []
    for row in levels:
        _require(isinstance(row, Sequence) and not isinstance(row, (str, bytes)) and len(row) >= 2, f"{side}_LEVEL_INVALID")
        price = _decimal(row[0], f"{side}_PRICE", positive=True)
        qty = _decimal(row[1], f"{side}_QUANTITY", positive=True)
        parsed.append((price, qty))
    prices = [row[0] for row in parsed]
    _require(len(prices) == len(set(prices)), f"{side}_DUPLICATE_PRICE")
    expected = sorted(prices, reverse=(side == "BID"))
    _require(prices == expected, f"{side}_UNSORTED")
    return [[_canonical_decimal(price), _canonical_decimal(qty)] for price, qty in parsed]


def normalize_order_book_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(observation, Mapping), "OBSERVATION_OBJECT_REQUIRED")
    for field in ("observation_id", "provider_id", "instrument_id"):
        value = observation.get(field)
        _require(isinstance(value, str) and bool(value), f"{field.upper()}_MISSING")
    book_kind = observation.get("book_kind")
    representation = observation.get("source_representation")
    _require(book_kind in BOOK_KINDS, "BOOK_KIND_UNKNOWN")
    _require(representation in REPRESENTATIONS, "REPRESENTATION_UNKNOWN")
    timestamp = _positive_int(observation.get("timestamp_ms"), "TIMESTAMP_MS")
    bids = _normalize_levels(observation.get("bids"), "BID")
    asks = _normalize_levels(observation.get("asks"), "ASK")
    best_bid = Decimal(bids[0][0])
    best_ask = Decimal(asks[0][0])
    _require(best_bid < best_ask, "CROSSED_OR_LOCKED_BOOK")
    midpoint = (best_bid + best_ask) / Decimal(2)
    outer_bid = Decimal(bids[-1][0])
    outer_ask = Decimal(asks[-1][0])
    bid_cov = (midpoint - outer_bid) / midpoint * Decimal(10000)
    ask_cov = (outer_ask - midpoint) / midpoint * Decimal(10000)
    _require(bid_cov >= 0 and ask_cov >= 0, "COVERAGE_NEGATIVE")
    for claim_name, physical in (
        ("claimed_bid_coverage_bps", bid_cov),
        ("claimed_ask_coverage_bps", ask_cov),
    ):
        if claim_name in observation:
            claim = _decimal(observation[claim_name], claim_name.upper(), nonnegative=True)
            _require(claim <= physical, "CLAIMED_COVERAGE_EXCEEDS_OBSERVED_BOOK")
    normalized = {
        "schema_version": BOOK_SCHEMA,
        "observation_id": observation["observation_id"],
        "provider_id": observation["provider_id"],
        "instrument_id": observation["instrument_id"],
        "book_kind": book_kind,
        "source_representation": representation,
        "representation": "NORMALIZED",
        "timestamp_ms": timestamp,
        "reference_price_anchor": MIDPOINT_ANCHOR,
        "reference_price": _canonical_decimal(midpoint),
        "best_bid": bids[0][0],
        "best_ask": asks[0][0],
        "bids": bids,
        "asks": asks,
        "achieved_bid_coverage_bps": _canonical_decimal(bid_cov),
        "achieved_ask_coverage_bps": _canonical_decimal(ask_cov),
        "native_quantity_preserved": True,
    }
    normalized["observation_sha256"] = sha256_canonical_json(normalized)
    return normalized


def validate_normalized_order_book(normalized_book: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(normalized_book, Mapping), "NORMALIZED_BOOK_OBJECT_REQUIRED")
    _require(set(normalized_book) == NORMALIZED_BOOK_FIELDS, "NORMALIZED_BOOK_FIELDS_INVALID")
    _require(normalized_book.get("schema_version") == BOOK_SCHEMA, "NORMALIZED_BOOK_SCHEMA_INVALID")
    for field in ("observation_id", "provider_id", "instrument_id"):
        value = normalized_book.get(field)
        _require(
            isinstance(value, str) and bool(value) and "\n" not in value and "\r" not in value,
            f"{field.upper()}_INVALID",
        )
    book_kind = normalized_book.get("book_kind")
    source_representation = normalized_book.get("source_representation")
    _require(book_kind in BOOK_KINDS, "BOOK_KIND_UNKNOWN")
    _require(source_representation in REPRESENTATIONS, "REPRESENTATION_UNKNOWN")
    _require(normalized_book.get("representation") == "NORMALIZED", "NORMALIZED_REPRESENTATION_REQUIRED")
    timestamp = _positive_int(normalized_book.get("timestamp_ms"), "TIMESTAMP_MS")
    _require(normalized_book.get("reference_price_anchor") == MIDPOINT_ANCHOR, "REFERENCE_PRICE_ANCHOR_INVALID")
    _require(normalized_book.get("native_quantity_preserved") is True, "NATIVE_QUANTITY_NOT_PRESERVED")

    bids = _normalize_levels(normalized_book.get("bids"), "BID")
    asks = _normalize_levels(normalized_book.get("asks"), "ASK")
    _require(normalized_book.get("bids") == bids, "BID_LEVELS_NOT_CANONICAL")
    _require(normalized_book.get("asks") == asks, "ASK_LEVELS_NOT_CANONICAL")
    best_bid = Decimal(bids[0][0])
    best_ask = Decimal(asks[0][0])
    _require(best_bid < best_ask, "CROSSED_OR_LOCKED_BOOK")
    midpoint = (best_bid + best_ask) / Decimal(2)
    outer_bid = Decimal(bids[-1][0])
    outer_ask = Decimal(asks[-1][0])
    bid_cov = (midpoint - outer_bid) / midpoint * Decimal(10000)
    ask_cov = (outer_ask - midpoint) / midpoint * Decimal(10000)
    _require(bid_cov >= 0 and ask_cov >= 0, "COVERAGE_NEGATIVE")
    derived = {
        "reference_price": _canonical_decimal(midpoint),
        "best_bid": bids[0][0],
        "best_ask": asks[0][0],
        "achieved_bid_coverage_bps": _canonical_decimal(bid_cov),
        "achieved_ask_coverage_bps": _canonical_decimal(ask_cov),
    }
    for field, expected in derived.items():
        _require(normalized_book.get(field) == expected, f"{field.upper()}_MISMATCH")

    canonical = {
        "schema_version": BOOK_SCHEMA,
        "observation_id": normalized_book["observation_id"],
        "provider_id": normalized_book["provider_id"],
        "instrument_id": normalized_book["instrument_id"],
        "book_kind": book_kind,
        "source_representation": source_representation,
        "representation": "NORMALIZED",
        "timestamp_ms": timestamp,
        "reference_price_anchor": MIDPOINT_ANCHOR,
        "reference_price": derived["reference_price"],
        "best_bid": derived["best_bid"],
        "best_ask": derived["best_ask"],
        "bids": bids,
        "asks": asks,
        "achieved_bid_coverage_bps": derived["achieved_bid_coverage_bps"],
        "achieved_ask_coverage_bps": derived["achieved_ask_coverage_bps"],
        "native_quantity_preserved": True,
    }
    expected_hash = sha256_canonical_json(canonical)
    supplied_hash = normalized_book.get("observation_sha256")
    _require(
        isinstance(supplied_hash, str) and supplied_hash == expected_hash,
        "OBSERVATION_SHA256_MISMATCH",
    )
    canonical["observation_sha256"] = expected_hash
    return canonical


def assert_one_coherent_provider_observation(observations: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    _require(
        isinstance(observations, Sequence) and not isinstance(observations, (str, bytes)) and len(observations) == 1,
        "MULTI_OBSERVATION_STITCHING_FORBIDDEN",
    )
    observation = observations[0]
    _require(isinstance(observation, Mapping), "OBSERVATION_OBJECT_REQUIRED")
    return observation


def compute_side_coverage(
    normalized_book: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    book = validate_normalized_order_book(normalized_book)
    _require(book["provider_id"] == request["provider_id"], "PROVIDER_MISMATCH")
    _require(book["instrument_id"] == request["instrument_id"], "INSTRUMENT_MISMATCH")
    _require(book["book_kind"] == request["book_kind"], "BOOK_KIND_MISMATCH")
    bid = _decimal(book["achieved_bid_coverage_bps"], "ACHIEVED_BID_COVERAGE_BPS", nonnegative=True)
    ask = _decimal(book["achieved_ask_coverage_bps"], "ACHIEVED_ASK_COVERAGE_BPS", nonnegative=True)
    req_bid = _decimal(request["requested_bid_coverage_bps"], "REQUESTED_BID_COVERAGE_BPS", positive=True)
    req_ask = _decimal(request["requested_ask_coverage_bps"], "REQUESTED_ASK_COVERAGE_BPS", positive=True)
    complete_bid = bid >= req_bid
    complete_ask = ask >= req_ask
    return {
        "requested_bid_coverage_bps": request["requested_bid_coverage_bps"],
        "requested_ask_coverage_bps": request["requested_ask_coverage_bps"],
        "achieved_bid_coverage_bps": _canonical_decimal(bid),
        "achieved_ask_coverage_bps": _canonical_decimal(ask),
        "coverage_complete_bid": complete_bid,
        "coverage_complete_ask": complete_ask,
        "truncated": not (complete_bid and complete_ask),
        "extrapolation_allowed": False,
    }


def qualify_quantity_semantics(
    *,
    native_quantity: Any,
    native_quantity_unit: str,
    contract_quantity: Any | None = None,
    conversion_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    native = _decimal(native_quantity, "NATIVE_QUANTITY", nonnegative=True)
    _require(isinstance(native_quantity_unit, str) and bool(native_quantity_unit), "NATIVE_QUANTITY_UNIT_INVALID")
    contract_value = None if contract_quantity is None else _canonical_decimal(
        _decimal(contract_quantity, "CONTRACT_QUANTITY", nonnegative=True)
    )
    out = {
        "model": "PRODUCT_AWARE_NATIVE_FIRST",
        "native_quantity": _canonical_decimal(native),
        "native_quantity_unit": native_quantity_unit,
        "contract_quantity": contract_value,
        "base_equivalent": None,
        "quote_equivalent": None,
        "consumer_qualified_equivalent": False,
        "conversion_formula_id": None,
        "conversion_formula_version": None,
        "instrument_spec_identity": None,
        "native_quantity_preserved": True,
    }
    if conversion_authority is None:
        return out
    _require(isinstance(conversion_authority, Mapping), "CONVERSION_AUTHORITY_INVALID")
    _require(conversion_authority.get("qualified") is True, "CONVERSION_NOT_QUALIFIED")
    required = ("formula_id", "formula_version", "instrument_spec_identity", "base_equivalent", "quote_equivalent")
    _require(all(conversion_authority.get(field) is not None for field in required), "CONVERSION_AUTHORITY_INCOMPLETE")
    out.update({
        "base_equivalent": _canonical_decimal(_decimal(conversion_authority["base_equivalent"], "BASE_EQUIVALENT", nonnegative=True)),
        "quote_equivalent": _canonical_decimal(_decimal(conversion_authority["quote_equivalent"], "QUOTE_EQUIVALENT", nonnegative=True)),
        "consumer_qualified_equivalent": True,
        "conversion_formula_id": str(conversion_authority["formula_id"]),
        "conversion_formula_version": str(conversion_authority["formula_version"]),
        "instrument_spec_identity": str(conversion_authority["instrument_spec_identity"]),
    })
    return out


def qualify_liquidity_resource(
    normalized_book: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    *,
    age_seconds: int,
    quantity_semantics: Mapping[str, Any],
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    book = validate_normalized_order_book(normalized_book)
    _require(book["provider_id"] == request["provider_id"], "PROVIDER_MISMATCH")
    _require(book["instrument_id"] == request["instrument_id"], "INSTRUMENT_MISMATCH")
    _require(book["book_kind"] == request["book_kind"], "BOOK_KIND_MISMATCH")
    _require(isinstance(age_seconds, int) and not isinstance(age_seconds, bool) and age_seconds >= 0, "AGE_SECONDS_INVALID")
    coverage = compute_side_coverage(book, request)
    _require(isinstance(quantity_semantics, Mapping), "QUANTITY_SEMANTICS_INVALID")
    _require(quantity_semantics.get("native_quantity_preserved") is True, "NATIVE_QUANTITY_NOT_PRESERVED")
    resource = {
        "schema_version": RESOURCE_SCHEMA,
        "series_id": request["series_id"],
        "provider_id": book["provider_id"],
        "instrument_id": book["instrument_id"],
        "book_kind": book["book_kind"],
        "representation": book["source_representation"],
        "observation_id": book["observation_id"],
        "observation_sha256": book["observation_sha256"],
        "age_seconds": age_seconds,
        "qualification_state": "QUALIFIED",
        "coherent_observation": True,
        **coverage,
        "quantity_semantics": dict(quantity_semantics),
    }
    result = evaluate_resource_satisfaction(resource, request)
    resource["request_satisfaction"] = result["status"]
    resource["request_satisfied"] = result["status"] == "SATISFIED"
    resource["resource_sha256"] = sha256_canonical_json(resource)
    return resource


def canonical_plan_bytes(result: Mapping[str, Any]) -> bytes:
    plan = result.get("acquisition_plan")
    _require(isinstance(plan, Mapping), "ACQUISITION_PLAN_REQUIRED")
    return canonical_json(plan).encode("utf-8")
