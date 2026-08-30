from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from canonical_json import canonical_json, sha256_canonical_json

REQUEST_SCHEMA = "liquidity-s1-semantic-request/1.0.0"
PLAN_SCHEMA = "liquidity-s1-acquisition-plan/1.0.0"
BOOK_SCHEMA = "liquidity-s1-normalized-book/1.0.0"
QUANTITY_SCHEMA = "liquidity-s1-quantity-semantics/1.0.0"
RESOURCE_SCHEMA = "liquidity-s1-qualified-resource/1.0.0"
TEMPORAL_AUTHORITY_OWNER = "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1::tools/current_data_transport.py"
TEMPORAL_PROVENANCE_FIELDS = {
    "authority_owner",
    "evaluated_at_utc",
    "evaluation_time_ms",
    "observation_timestamp_ms",
    "derived_age_seconds",
}

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

QUANTITY_FIELDS = {
    "schema_version",
    "provider_id",
    "instrument_id",
    "book_kind",
    "model",
    "native_quantity",
    "native_quantity_unit",
    "contract_quantity",
    "base_equivalent",
    "quote_equivalent",
    "consumer_qualified_equivalent",
    "conversion_formula_id",
    "conversion_formula_version",
    "instrument_spec_identity",
    "native_quantity_preserved",
    "quantity_sha256",
}

QUALIFIED_RESOURCE_FIELDS = {
    "schema_version",
    "series_id",
    "provider_id",
    "instrument_id",
    "book_kind",
    "representation",
    "observation_id",
    "observation_sha256",
    "temporal_provenance",
    "age_seconds",
    "freshness_verdict",
    "qualification_state",
    "coherent_observation",
    "requested_bid_coverage_bps",
    "requested_ask_coverage_bps",
    "achieved_bid_coverage_bps",
    "achieved_ask_coverage_bps",
    "coverage_complete_bid",
    "coverage_complete_ask",
    "truncated",
    "extrapolation_allowed",
    "quantity_semantics",
    "normalized_book",
    "qualification_request",
    "request_satisfaction",
    "request_satisfied",
    "resource_sha256",
}

PROVIDER_CAPABILITY_FIELDS = {
    "provider_id",
    "book_kind",
    "raw_book_capability",
    "selectable_depth_limit",
    "qualified_provider_depth_parameter",
}

PLAN_FIELDS = {
    "schema_version",
    "plan_kind",
    "provider_id",
    "instrument_id",
    "book_kind",
    "requested_representation",
    "requested_bid_coverage_bps",
    "requested_ask_coverage_bps",
    "target_bps",
    "bucket_bps",
    "freshness",
    "completeness",
    "observation_rule",
    "retry_semantics",
    "stitching",
    "provider_capability_state",
    "provider_depth_bound",
    "network_execution",
    "plan_sha256",
}

PLAN_RESULT_FIELDS = {
    "decision",
    "network_required",
    "resource_satisfaction",
    "acquisition_plan",
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


def _nonnegative_int(value: Any, field: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field}_INVALID")
    return int(value)


def _current_data_temporal_owner():
    try:
        import current_data_transport as temporal_owner
    except ImportError:
        try:
            from tools import current_data_transport as temporal_owner
        except ImportError as exc:
            raise LiquidityS1Error("TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    for name in ("_utc_now", "_format_utc", "_parse_utc"):
        _require(callable(getattr(temporal_owner, name, None)), "TEMPORAL_AUTHORITY_UNAVAILABLE")
    return temporal_owner


def _derive_temporal_provenance(
    normalized_book: Mapping[str, Any],
    *,
    evaluated_at_utc: str,
    evaluation_time_ms: int,
) -> dict[str, Any]:
    temporal_owner = _current_data_temporal_owner()
    try:
        parsed = temporal_owner._parse_utc(evaluated_at_utc, "liquidity_s1.evaluated_at_utc")
        canonical_utc = temporal_owner._format_utc(parsed)
    except Exception as exc:
        raise LiquidityS1Error("TEMPORAL_EVALUATION_TIME_INVALID") from exc
    _require(canonical_utc == evaluated_at_utc, "TEMPORAL_EVALUATION_TIME_NOT_CANONICAL")
    evaluation_ms = _nonnegative_int(evaluation_time_ms, "TEMPORAL_EVALUATION_TIME_MS")
    parsed_second_ms = int(parsed.timestamp()) * 1000
    _require(
        parsed_second_ms <= evaluation_ms < parsed_second_ms + 1000,
        "TEMPORAL_EVALUATION_TIME_MISMATCH",
    )
    observation_timestamp_ms = _positive_int(
        normalized_book.get("timestamp_ms"),
        "OBSERVATION_TIMESTAMP_MS",
    )
    _require(evaluation_ms >= observation_timestamp_ms, "OBSERVATION_TIMESTAMP_IN_FUTURE")
    derived_age_seconds = (evaluation_ms - observation_timestamp_ms) // 1000
    return {
        "authority_owner": TEMPORAL_AUTHORITY_OWNER,
        "evaluated_at_utc": canonical_utc,
        "evaluation_time_ms": evaluation_ms,
        "observation_timestamp_ms": observation_timestamp_ms,
        "derived_age_seconds": derived_age_seconds,
    }


def _capture_temporal_provenance(normalized_book: Mapping[str, Any]) -> dict[str, Any]:
    temporal_owner = _current_data_temporal_owner()
    try:
        current = temporal_owner._utc_now()
        offset = current.utcoffset()
        _require(
            offset is not None and offset.total_seconds() == 0,
            "TEMPORAL_AUTHORITY_NOT_UTC",
        )
        evaluation_time_ms = int(current.timestamp() * 1000)
        evaluated_at_utc = temporal_owner._format_utc(current)
    except LiquidityS1Error:
        raise
    except Exception as exc:
        raise LiquidityS1Error("TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    return _derive_temporal_provenance(
        normalized_book,
        evaluated_at_utc=evaluated_at_utc,
        evaluation_time_ms=evaluation_time_ms,
    )


def _validate_temporal_provenance(
    temporal_provenance: Mapping[str, Any],
    normalized_book: Mapping[str, Any],
) -> dict[str, Any]:
    _require(isinstance(temporal_provenance, Mapping), "TEMPORAL_PROVENANCE_REQUIRED")
    _require(set(temporal_provenance) == TEMPORAL_PROVENANCE_FIELDS, "TEMPORAL_PROVENANCE_FIELDS_INVALID")
    _require(
        temporal_provenance.get("authority_owner") == TEMPORAL_AUTHORITY_OWNER,
        "TEMPORAL_AUTHORITY_OWNER_INVALID",
    )
    evaluated_at_utc = temporal_provenance.get("evaluated_at_utc")
    _require(isinstance(evaluated_at_utc, str), "TEMPORAL_EVALUATION_TIME_INVALID")
    canonical = _derive_temporal_provenance(
        normalized_book,
        evaluated_at_utc=evaluated_at_utc,
        evaluation_time_ms=temporal_provenance.get("evaluation_time_ms"),
    )
    _require(dict(temporal_provenance) == canonical, "TEMPORAL_PROVENANCE_NOT_CANONICAL")
    return canonical


def _single_line_identity(value: Any, field: str) -> str:
    _require(
        isinstance(value, str) and bool(value) and "\n" not in value and "\r" not in value,
        f"{field}_INVALID",
    )
    return value


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
    series_id = _single_line_identity(payload.get("series_id"), "SERIES_ID")
    provider_id = _single_line_identity(payload.get("provider_id"), "PROVIDER_ID")
    instrument_id = _single_line_identity(payload.get("instrument_id"), "INSTRUMENT_ID")
    book_kind = payload.get("book_kind")
    representation = payload.get("representation")
    _require(book_kind in BOOK_KINDS, "BOOK_KIND_UNKNOWN")
    _require(representation in REPRESENTATIONS, "REPRESENTATION_UNKNOWN")
    target = _decimal(payload.get("target_bps"), "TARGET_BPS", positive=True)
    bid_target = _decimal(
        payload.get("requested_bid_coverage_bps", target),
        "REQUESTED_BID_COVERAGE_BPS",
        positive=True,
    )
    ask_target = _decimal(
        payload.get("requested_ask_coverage_bps", target),
        "REQUESTED_ASK_COVERAGE_BPS",
        positive=True,
    )
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
    _require(
        isinstance(quantity.get("consumer_equivalent_required"), bool),
        "CONSUMER_EQUIVALENT_REQUIREMENT_INVALID",
    )
    return {
        "schema_version": REQUEST_SCHEMA,
        "series_id": series_id,
        "provider_id": provider_id,
        "instrument_id": instrument_id,
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
    return existing == requested or (existing == "RAW" and requested == "PROFILE")


def _normalize_levels(levels: Any, side: str) -> list[list[str]]:
    _require(
        isinstance(levels, Sequence) and not isinstance(levels, (str, bytes)) and bool(levels),
        f"{side}_LEVELS_INVALID",
    )
    parsed: list[tuple[Decimal, Decimal]] = []
    for row in levels:
        _require(
            isinstance(row, Sequence) and not isinstance(row, (str, bytes)) and len(row) >= 2,
            f"{side}_LEVEL_INVALID",
        )
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
    observation_id = _single_line_identity(observation.get("observation_id"), "OBSERVATION_ID")
    provider_id = _single_line_identity(observation.get("provider_id"), "PROVIDER_ID")
    instrument_id = _single_line_identity(observation.get("instrument_id"), "INSTRUMENT_ID")
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
        "observation_id": observation_id,
        "provider_id": provider_id,
        "instrument_id": instrument_id,
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
    observation_id = _single_line_identity(normalized_book.get("observation_id"), "OBSERVATION_ID")
    provider_id = _single_line_identity(normalized_book.get("provider_id"), "PROVIDER_ID")
    instrument_id = _single_line_identity(normalized_book.get("instrument_id"), "INSTRUMENT_ID")
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
        "observation_id": observation_id,
        "provider_id": provider_id,
        "instrument_id": instrument_id,
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
    _require(isinstance(supplied_hash, str) and supplied_hash == expected_hash, "OBSERVATION_SHA256_MISMATCH")
    canonical["observation_sha256"] = expected_hash
    return canonical


def assert_one_coherent_provider_observation(observations: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Cardinality guard only; it deliberately does not confer validation or provider authority."""
    _require(
        isinstance(observations, Sequence)
        and not isinstance(observations, (str, bytes))
        and len(observations) == 1,
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
    provider_id: str,
    instrument_id: str,
    book_kind: str,
    native_quantity: Any,
    native_quantity_unit: str,
    contract_quantity: Any | None = None,
    conversion_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the only S1-local canonical quantity result.

    S1 has no canonical conversion-qualification owner. Any conversion authority
    is therefore rejected rather than interpreting caller-authored `qualified=true`
    as authority. Native quantity remains preserved and consumer-equivalent
    conversion stays explicitly unqualified.
    """
    provider = _single_line_identity(provider_id, "PROVIDER_ID")
    instrument = _single_line_identity(instrument_id, "INSTRUMENT_ID")
    _require(book_kind in BOOK_KINDS, "BOOK_KIND_UNKNOWN")
    native = _decimal(native_quantity, "NATIVE_QUANTITY", nonnegative=True)
    unit = _single_line_identity(native_quantity_unit, "NATIVE_QUANTITY_UNIT")
    contract_value = (
        None
        if contract_quantity is None
        else _canonical_decimal(_decimal(contract_quantity, "CONTRACT_QUANTITY", nonnegative=True))
    )
    if conversion_authority is not None:
        _require(isinstance(conversion_authority, Mapping), "CONVERSION_AUTHORITY_INVALID")
        raise LiquidityS1Error("CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1")

    result = {
        "schema_version": QUANTITY_SCHEMA,
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "model": "PRODUCT_AWARE_NATIVE_FIRST",
        "native_quantity": _canonical_decimal(native),
        "native_quantity_unit": unit,
        "contract_quantity": contract_value,
        "base_equivalent": None,
        "quote_equivalent": None,
        "consumer_qualified_equivalent": False,
        "conversion_formula_id": None,
        "conversion_formula_version": None,
        "instrument_spec_identity": None,
        "native_quantity_preserved": True,
    }
    result["quantity_sha256"] = sha256_canonical_json(result)
    return result


def validate_quantity_semantics(quantity_semantics: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(quantity_semantics, Mapping), "QUANTITY_SEMANTICS_INVALID")
    _require(set(quantity_semantics) == QUANTITY_FIELDS, "QUANTITY_SEMANTICS_FIELDS_INVALID")
    _require(quantity_semantics.get("schema_version") == QUANTITY_SCHEMA, "QUANTITY_SEMANTICS_SCHEMA_INVALID")
    provider = _single_line_identity(quantity_semantics.get("provider_id"), "QUANTITY_PROVIDER_ID")
    instrument = _single_line_identity(quantity_semantics.get("instrument_id"), "QUANTITY_INSTRUMENT_ID")
    book_kind = quantity_semantics.get("book_kind")
    _require(book_kind in BOOK_KINDS, "QUANTITY_BOOK_KIND_UNKNOWN")
    _require(quantity_semantics.get("model") == "PRODUCT_AWARE_NATIVE_FIRST", "QUANTITY_MODEL_INVALID")
    native = _decimal(quantity_semantics.get("native_quantity"), "NATIVE_QUANTITY", nonnegative=True)
    unit = _single_line_identity(quantity_semantics.get("native_quantity_unit"), "NATIVE_QUANTITY_UNIT")
    contract_raw = quantity_semantics.get("contract_quantity")
    contract = None if contract_raw is None else _canonical_decimal(
        _decimal(contract_raw, "CONTRACT_QUANTITY", nonnegative=True)
    )
    _require(quantity_semantics.get("base_equivalent") is None, "UNQUALIFIED_BASE_EQUIVALENT_PRESENT")
    _require(quantity_semantics.get("quote_equivalent") is None, "UNQUALIFIED_QUOTE_EQUIVALENT_PRESENT")
    _require(
        quantity_semantics.get("consumer_qualified_equivalent") is False,
        "CONSUMER_EQUIVALENT_NOT_QUALIFIED_IN_S1",
    )
    _require(quantity_semantics.get("conversion_formula_id") is None, "UNQUALIFIED_CONVERSION_FORMULA_PRESENT")
    _require(quantity_semantics.get("conversion_formula_version") is None, "UNQUALIFIED_CONVERSION_FORMULA_PRESENT")
    _require(quantity_semantics.get("instrument_spec_identity") is None, "UNQUALIFIED_INSTRUMENT_SPEC_PRESENT")
    _require(quantity_semantics.get("native_quantity_preserved") is True, "NATIVE_QUANTITY_NOT_PRESERVED")

    canonical = {
        "schema_version": QUANTITY_SCHEMA,
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "model": "PRODUCT_AWARE_NATIVE_FIRST",
        "native_quantity": _canonical_decimal(native),
        "native_quantity_unit": unit,
        "contract_quantity": contract,
        "base_equivalent": None,
        "quote_equivalent": None,
        "consumer_qualified_equivalent": False,
        "conversion_formula_id": None,
        "conversion_formula_version": None,
        "instrument_spec_identity": None,
        "native_quantity_preserved": True,
    }
    expected_hash = sha256_canonical_json(canonical)
    _require(quantity_semantics.get("quantity_sha256") == expected_hash, "QUANTITY_SHA256_MISMATCH")
    canonical["quantity_sha256"] = expected_hash
    _require(dict(quantity_semantics) == canonical, "QUANTITY_SEMANTICS_NOT_CANONICAL")
    return canonical


def _evaluate_validated_resource(
    resource: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    evaluation_age_seconds: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    if resource["provider_id"] != request["provider_id"]:
        reasons.append("PROVIDER_MISMATCH")
    if resource["instrument_id"] != request["instrument_id"]:
        reasons.append("INSTRUMENT_MISMATCH")
    if resource["book_kind"] != request["book_kind"]:
        reasons.append("BOOK_KIND_MISMATCH")
    if not _representation_compatible(str(resource["representation"]), str(request["representation"])):
        reasons.append("REPRESENTATION_NOT_DOMINATING")

    age = _nonnegative_int(evaluation_age_seconds, "EVALUATION_AGE_SECONDS")
    if age > request["freshness"]["max_age_seconds"]:
        reasons.append("STALE")

    bid = _decimal(resource["achieved_bid_coverage_bps"], "ACHIEVED_BID_COVERAGE_BPS", nonnegative=True)
    ask = _decimal(resource["achieved_ask_coverage_bps"], "ACHIEVED_ASK_COVERAGE_BPS", nonnegative=True)
    req_bid = _decimal(request["requested_bid_coverage_bps"], "REQUESTED_BID_COVERAGE_BPS", positive=True)
    req_ask = _decimal(request["requested_ask_coverage_bps"], "REQUESTED_ASK_COVERAGE_BPS", positive=True)
    if bid < req_bid:
        reasons.append("BID_COVERAGE_INSUFFICIENT")
    if ask < req_ask:
        reasons.append("ASK_COVERAGE_INSUFFICIENT")

    quantity = resource["quantity_semantics"]
    if request["quantity_semantics"]["consumer_equivalent_required"] and quantity["consumer_qualified_equivalent"] is not True:
        reasons.append("CONSUMER_EQUIVALENT_NOT_QUALIFIED")

    if reasons:
        return {"status": "UNSATISFIED", "reusable": False, "reasons": sorted(set(reasons))}
    return {"status": "SATISFIED", "reusable": True, "reasons": []}


def _resource_material(
    *,
    request: Mapping[str, Any],
    book: Mapping[str, Any],
    temporal_provenance: Mapping[str, Any],
    quantity: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = compute_side_coverage(book, request)
    temporal = _validate_temporal_provenance(temporal_provenance, book)
    age_seconds = temporal["derived_age_seconds"]
    freshness_verdict = "FRESH" if age_seconds <= request["freshness"]["max_age_seconds"] else "STALE"
    return {
        "schema_version": RESOURCE_SCHEMA,
        "series_id": request["series_id"],
        "provider_id": book["provider_id"],
        "instrument_id": book["instrument_id"],
        "book_kind": book["book_kind"],
        "representation": book["source_representation"],
        "observation_id": book["observation_id"],
        "observation_sha256": book["observation_sha256"],
        "temporal_provenance": temporal,
        "age_seconds": age_seconds,
        "freshness_verdict": freshness_verdict,
        "qualification_state": "QUALIFIED",
        "coherent_observation": True,
        **coverage,
        "quantity_semantics": dict(quantity),
        "normalized_book": dict(book),
        "qualification_request": dict(request),
    }


def qualify_liquidity_resource(
    normalized_book: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    *,
    age_seconds: int | None = None,
    quantity_semantics: Mapping[str, Any],
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    book = validate_normalized_order_book(normalized_book)
    _require(book["provider_id"] == request["provider_id"], "PROVIDER_MISMATCH")
    _require(book["instrument_id"] == request["instrument_id"], "INSTRUMENT_MISMATCH")
    _require(book["book_kind"] == request["book_kind"], "BOOK_KIND_MISMATCH")
    temporal = _capture_temporal_provenance(book)
    if age_seconds is not None:
        caller_age = _nonnegative_int(age_seconds, "CALLER_AGE_SECONDS")
        _require(caller_age == temporal["derived_age_seconds"], "CALLER_AGE_SECONDS_MISMATCH")
    quantity = validate_quantity_semantics(quantity_semantics)
    _require(quantity["provider_id"] == request["provider_id"], "QUANTITY_PROVIDER_MISMATCH")
    _require(quantity["instrument_id"] == request["instrument_id"], "QUANTITY_INSTRUMENT_MISMATCH")
    _require(quantity["book_kind"] == request["book_kind"], "QUANTITY_BOOK_KIND_MISMATCH")

    resource = _resource_material(
        request=request,
        book=book,
        temporal_provenance=temporal,
        quantity=quantity,
    )
    result = _evaluate_validated_resource(
        resource,
        request,
        evaluation_age_seconds=resource["age_seconds"],
    )
    resource["request_satisfaction"] = result["status"]
    resource["request_satisfied"] = result["status"] == "SATISFIED"
    resource["resource_sha256"] = sha256_canonical_json(resource)
    return resource


def validate_qualified_liquidity_resource(resource: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(resource, Mapping), "QUALIFIED_RESOURCE_OBJECT_REQUIRED")
    _require(set(resource) == QUALIFIED_RESOURCE_FIELDS, "QUALIFIED_RESOURCE_FIELDS_INVALID")
    _require(resource.get("schema_version") == RESOURCE_SCHEMA, "QUALIFIED_RESOURCE_SCHEMA_INVALID")

    request_raw = resource.get("qualification_request")
    book_raw = resource.get("normalized_book")
    quantity_raw = resource.get("quantity_semantics")
    _require(isinstance(request_raw, Mapping), "QUALIFICATION_REQUEST_MISSING")
    _require(isinstance(book_raw, Mapping), "QUALIFIED_RESOURCE_BOOK_MISSING")
    _require(isinstance(quantity_raw, Mapping), "QUALIFIED_RESOURCE_QUANTITY_MISSING")
    request = normalize_liquidity_request(request_raw)
    book = validate_normalized_order_book(book_raw)
    quantity = validate_quantity_semantics(quantity_raw)
    temporal_raw = resource.get("temporal_provenance")
    _require(isinstance(temporal_raw, Mapping), "RESOURCE_TEMPORAL_PROVENANCE_MISSING")
    temporal = _validate_temporal_provenance(temporal_raw, book)
    age = temporal["derived_age_seconds"]
    _require(resource.get("age_seconds") == age, "RESOURCE_AGE_SECONDS_MISMATCH")

    _require(resource.get("series_id") == request["series_id"], "RESOURCE_SERIES_ID_MISMATCH")
    _require(resource.get("provider_id") == request["provider_id"] == book["provider_id"], "RESOURCE_PROVIDER_MISMATCH")
    _require(
        resource.get("instrument_id") == request["instrument_id"] == book["instrument_id"],
        "RESOURCE_INSTRUMENT_MISMATCH",
    )
    _require(resource.get("book_kind") == request["book_kind"] == book["book_kind"], "RESOURCE_BOOK_KIND_MISMATCH")
    _require(resource.get("representation") == book["source_representation"], "RESOURCE_REPRESENTATION_MISMATCH")
    _require(resource.get("observation_id") == book["observation_id"], "RESOURCE_OBSERVATION_ID_MISMATCH")
    _require(
        resource.get("observation_sha256") == book["observation_sha256"],
        "RESOURCE_OBSERVATION_SHA256_MISMATCH",
    )
    _require(resource.get("qualification_state") == "QUALIFIED", "RESOURCE_QUALIFICATION_STATE_INVALID")
    _require(resource.get("coherent_observation") is True, "RESOURCE_COHERENCE_INVALID")
    _require(quantity["provider_id"] == request["provider_id"], "QUANTITY_PROVIDER_MISMATCH")
    _require(quantity["instrument_id"] == request["instrument_id"], "QUANTITY_INSTRUMENT_MISMATCH")
    _require(quantity["book_kind"] == request["book_kind"], "QUANTITY_BOOK_KIND_MISMATCH")

    canonical = _resource_material(
        request=request,
        book=book,
        temporal_provenance=temporal,
        quantity=quantity,
    )
    _require(
        resource.get("freshness_verdict") == canonical["freshness_verdict"],
        "RESOURCE_FRESHNESS_VERDICT_MISMATCH",
    )
    for field in (
        "requested_bid_coverage_bps",
        "requested_ask_coverage_bps",
        "achieved_bid_coverage_bps",
        "achieved_ask_coverage_bps",
        "coverage_complete_bid",
        "coverage_complete_ask",
        "truncated",
        "extrapolation_allowed",
    ):
        _require(resource.get(field) == canonical[field], f"RESOURCE_{field.upper()}_MISMATCH")
    own = _evaluate_validated_resource(
        canonical,
        request,
        evaluation_age_seconds=age,
    )
    canonical["request_satisfaction"] = own["status"]
    canonical["request_satisfied"] = own["status"] == "SATISFIED"
    _require(
        resource.get("request_satisfaction") == canonical["request_satisfaction"],
        "RESOURCE_REQUEST_SATISFACTION_MISMATCH",
    )
    _require(
        resource.get("request_satisfied") == canonical["request_satisfied"],
        "RESOURCE_REQUEST_SATISFIED_MISMATCH",
    )
    expected_hash = sha256_canonical_json(canonical)
    _require(resource.get("resource_sha256") == expected_hash, "RESOURCE_SHA256_MISMATCH")
    canonical["resource_sha256"] = expected_hash
    _require(dict(resource) == canonical, "QUALIFIED_RESOURCE_NOT_CANONICAL")
    return canonical


def evaluate_resource_satisfaction(
    existing_resource: Mapping[str, Any] | None,
    semantic_request: Mapping[str, Any],
) -> dict[str, Any]:
    request = normalize_liquidity_request(semantic_request)
    if existing_resource is None:
        return {"status": "UNSATISFIED", "reusable": False, "reasons": ["RESOURCE_ABSENT"]}
    try:
        resource = validate_qualified_liquidity_resource(existing_resource)
    except LiquidityS1Error as exc:
        return {
            "status": "NOT_QUALIFIED",
            "reusable": False,
            "reasons": [f"RESOURCE_REVALIDATION_FAILED:{exc}"],
        }
    try:
        current_temporal = _capture_temporal_provenance(resource["normalized_book"])
    except LiquidityS1Error as exc:
        return {
            "status": "NOT_QUALIFIED",
            "reusable": False,
            "reasons": [f"RESOURCE_CURRENT_FRESHNESS_FAILED:{exc}"],
        }
    return _evaluate_validated_resource(
        resource,
        request,
        evaluation_age_seconds=current_temporal["derived_age_seconds"],
    )


def validate_provider_capability_for_s1(
    provider_capability: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the S1 planner input without turning it into S2 authority.

    Provider capability facts are owned by existing provider contracts; physical
    depth qualification is owned by S2. S1 therefore never accepts a caller
    mapping as proof that a provider depth parameter is qualified.
    """
    request = normalize_liquidity_request(semantic_request)
    _require(isinstance(provider_capability, Mapping), "PROVIDER_CAPABILITY_INVALID")
    _require(set(provider_capability) == PROVIDER_CAPABILITY_FIELDS, "PROVIDER_CAPABILITY_FIELDS_INVALID")
    _require(provider_capability.get("provider_id") == request["provider_id"], "CAPABILITY_PROVIDER_MISMATCH")
    _require(provider_capability.get("book_kind") == request["book_kind"], "CAPABILITY_BOOK_KIND_MISMATCH")
    raw_state = provider_capability.get("raw_book_capability")
    _require(
        raw_state in {"CONFIRMED", "AVAILABLE_EXTERNALLY", "UNKNOWN", "NOT_QUALIFIED"},
        "RAW_BOOK_CAPABILITY_STATE_INVALID",
    )
    depth_status = provider_capability.get("selectable_depth_limit")
    qualified_limit = provider_capability.get("qualified_provider_depth_parameter")
    if depth_status == "QUALIFIED" or qualified_limit is not None:
        raise LiquidityS1Error("PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1")
    _require(
        depth_status in {"NOT_NORMATIVELY_DOCUMENTED", "NOT_QUALIFIED", "UNKNOWN"},
        "SELECTABLE_DEPTH_LIMIT_STATE_INVALID",
    )
    return {
        "provider_id": request["provider_id"],
        "book_kind": request["book_kind"],
        "raw_book_capability": raw_state,
        "selectable_depth_limit": depth_status,
        "qualified_provider_depth_parameter": None,
    }


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

    capability = validate_provider_capability_for_s1(provider_capability, request)
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
        "provider_capability_state": {
            "raw_book_capability": capability["raw_book_capability"],
            "depth_qualification_owner": "S2_PROVIDER_CAPABILITY_QUALIFICATION",
        },
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


def validate_liquidity_acquisition_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Revalidate a serialized S1 acquisition plan before it crosses a trust boundary.

    `plan_sha256` is integrity evidence only. It never upgrades caller-authored
    provider depth or capability claims into S2-qualified authority.
    """
    _require(isinstance(plan, Mapping), "ACQUISITION_PLAN_REQUIRED")
    _require(set(plan) == PLAN_FIELDS, "ACQUISITION_PLAN_FIELDS_INVALID")
    _require(plan.get("schema_version") == PLAN_SCHEMA, "ACQUISITION_PLAN_SCHEMA_INVALID")
    _require(plan.get("plan_kind") == "DYNAMIC_DEPTH_ACQUISITION_PLAN", "ACQUISITION_PLAN_KIND_INVALID")

    provider_id = _single_line_identity(plan.get("provider_id"), "PLAN_PROVIDER_ID")
    instrument_id = _single_line_identity(plan.get("instrument_id"), "PLAN_INSTRUMENT_ID")
    book_kind = plan.get("book_kind")
    representation = plan.get("requested_representation")
    _require(book_kind in BOOK_KINDS, "PLAN_BOOK_KIND_UNKNOWN")
    _require(representation in REPRESENTATIONS, "PLAN_REPRESENTATION_UNKNOWN")

    requested_bid = _canonical_decimal(
        _decimal(plan.get("requested_bid_coverage_bps"), "PLAN_REQUESTED_BID_COVERAGE_BPS", positive=True)
    )
    requested_ask = _canonical_decimal(
        _decimal(plan.get("requested_ask_coverage_bps"), "PLAN_REQUESTED_ASK_COVERAGE_BPS", positive=True)
    )
    target = _canonical_decimal(_decimal(plan.get("target_bps"), "PLAN_TARGET_BPS", positive=True))
    bucket = _canonical_decimal(_decimal(plan.get("bucket_bps"), "PLAN_BUCKET_BPS", positive=True))

    freshness = plan.get("freshness")
    _require(
        isinstance(freshness, Mapping) and set(freshness) == {"max_age_seconds"},
        "PLAN_FRESHNESS_INVALID",
    )
    max_age = _positive_int(freshness.get("max_age_seconds"), "PLAN_MAX_AGE_SECONDS")
    completeness = plan.get("completeness")
    _require(
        isinstance(completeness, Mapping) and set(completeness) == {"required"},
        "PLAN_COMPLETENESS_INVALID",
    )
    _require(isinstance(completeness.get("required"), bool), "PLAN_COMPLETENESS_REQUIRED_INVALID")

    _require(plan.get("observation_rule") == "ONE_COHERENT_PROVIDER_OBSERVATION", "PLAN_OBSERVATION_RULE_INVALID")
    _require(plan.get("retry_semantics") == "NEW_OBSERVATION", "PLAN_RETRY_SEMANTICS_INVALID")
    _require(plan.get("stitching") == "FORBIDDEN", "PLAN_STITCHING_INVALID")
    _require(plan.get("network_execution") == "NOT_IMPLEMENTED_BY_S1", "PLAN_NETWORK_EXECUTION_INVALID")

    capability_state = plan.get("provider_capability_state")
    _require(
        isinstance(capability_state, Mapping)
        and set(capability_state) == {"raw_book_capability", "depth_qualification_owner"},
        "PLAN_PROVIDER_CAPABILITY_STATE_INVALID",
    )
    raw_state = capability_state.get("raw_book_capability")
    _require(
        raw_state in {"CONFIRMED", "AVAILABLE_EXTERNALLY", "UNKNOWN", "NOT_QUALIFIED"},
        "PLAN_RAW_BOOK_CAPABILITY_STATE_INVALID",
    )
    _require(
        capability_state.get("depth_qualification_owner") == "S2_PROVIDER_CAPABILITY_QUALIFICATION",
        "PLAN_DEPTH_QUALIFICATION_OWNER_INVALID",
    )

    depth_bound = plan.get("provider_depth_bound")
    _require(
        isinstance(depth_bound, Mapping)
        and set(depth_bound) == {"status", "qualified_provider_depth_parameter"},
        "PLAN_PROVIDER_DEPTH_BOUND_INVALID",
    )
    _require(
        depth_bound.get("status") == "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
        "PLAN_PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
    )
    _require(
        depth_bound.get("qualified_provider_depth_parameter") is None,
        "PLAN_QUALIFIED_PROVIDER_DEPTH_PARAMETER_FORBIDDEN",
    )

    canonical = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": "DYNAMIC_DEPTH_ACQUISITION_PLAN",
        "provider_id": provider_id,
        "instrument_id": instrument_id,
        "book_kind": book_kind,
        "requested_representation": representation,
        "requested_bid_coverage_bps": requested_bid,
        "requested_ask_coverage_bps": requested_ask,
        "target_bps": target,
        "bucket_bps": bucket,
        "freshness": {"max_age_seconds": max_age},
        "completeness": {"required": completeness["required"]},
        "observation_rule": "ONE_COHERENT_PROVIDER_OBSERVATION",
        "retry_semantics": "NEW_OBSERVATION",
        "stitching": "FORBIDDEN",
        "provider_capability_state": {
            "raw_book_capability": raw_state,
            "depth_qualification_owner": "S2_PROVIDER_CAPABILITY_QUALIFICATION",
        },
        "provider_depth_bound": {
            "status": "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
            "qualified_provider_depth_parameter": None,
        },
        "network_execution": "NOT_IMPLEMENTED_BY_S1",
    }
    expected_hash = sha256_canonical_json(canonical)
    _require(plan.get("plan_sha256") == expected_hash, "PLAN_SHA256_MISMATCH")
    canonical["plan_sha256"] = expected_hash
    _require(dict(plan) == canonical, "ACQUISITION_PLAN_NOT_CANONICAL")
    return canonical


def canonical_plan_bytes(result: Mapping[str, Any]) -> bytes:
    _require(isinstance(result, Mapping), "PLAN_RESULT_OBJECT_REQUIRED")
    _require(set(result) == PLAN_RESULT_FIELDS, "PLAN_RESULT_FIELDS_INVALID")
    _require(result.get("decision") == "ACQUISITION_REQUIRED", "PLAN_RESULT_DECISION_INVALID")
    _require(result.get("network_required") is True, "PLAN_RESULT_NETWORK_REQUIRED_INVALID")
    satisfaction = result.get("resource_satisfaction")
    _require(isinstance(satisfaction, Mapping), "PLAN_RESULT_SATISFACTION_INVALID")
    _require(satisfaction.get("status") in {"UNSATISFIED", "NOT_QUALIFIED"}, "PLAN_RESULT_SATISFACTION_INVALID")
    _require(satisfaction.get("reusable") is False, "PLAN_RESULT_SATISFACTION_INVALID")
    _require(isinstance(satisfaction.get("reasons"), list), "PLAN_RESULT_SATISFACTION_INVALID")
    plan = validate_liquidity_acquisition_plan(result.get("acquisition_plan"))
    return canonical_json(plan).encode("utf-8")