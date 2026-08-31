from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import (
    LiquidityS1Error,
    assert_one_coherent_provider_observation,
    canonical_plan_bytes,
    compute_side_coverage,
    normalize_liquidity_request,
    normalize_order_book_observation,
    qualify_liquidity_resource,
    qualify_quantity_semantics,
    validate_normalized_order_book,
    validate_qualified_liquidity_resource,
    validate_quantity_semantics,
)

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_CONTRACT_PATH = ROOT / "contracts/provider-contracts.json"

S2_PLAN_SCHEMA = "liquidity-s2-binance-provider-plan/1.0.0"
S2_RESULT_SCHEMA = "liquidity-s2-binance-normalized-result/1.0.0"
MAX_REST_LEVELS_PER_SIDE_HARD_ARCHITECTURAL_CAP = 5000
MAX_RAW_RESOURCE_BYTES_HARD_CAP = 8 * 1024 * 1024
SUPPORTED_TARGET_BPS = {"250", "500"}
SUPPORTED_INSTRUMENTS = {"ETHUSDT", "BTCUSDT"}
SUPPORTED_PROVIDER_IDS = {"binance-spot", "binance-usdm"}
NETWORK_EXECUTION_STATE = "S3_NOT_ACTIVE"


class BinanceS2Error(ValueError):
    """Fail-closed DB-C provider qualification/adapter error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise BinanceS2Error(code)


def _positive_int(value: Any, code: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value > 0, code)
    return value


def _decimal(value: Any, code: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise BinanceS2Error(code) from None
    _require(parsed.is_finite() and parsed >= 0, code)
    return parsed


def _canonical_observation_timestamp_ms() -> int:
    """Capture observation time from the canonical current-data temporal authority.

    The S2 adapter must not let a caller or provider response field become the
    freshness clock. S1 already declares tools/current_data_transport.py as the
    temporal authority, so DB-C reuses that exact clock for acquisition time.
    """
    try:
        current = current_data_transport._utc_now()
        offset = current.utcoffset()
    except Exception as exc:
        raise BinanceS2Error("S1_TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    _require(offset is not None and offset.total_seconds() == 0, "S1_TEMPORAL_AUTHORITY_NOT_UTC")
    return _positive_int(int(current.timestamp() * 1000), "S1_TEMPORAL_AUTHORITY_TIMESTAMP_INVALID")


def _load_provider_contract() -> dict[str, Any]:
    raw = json.loads(PROVIDER_CONTRACT_PATH.read_text(encoding="utf-8"))
    _require(raw.get("schema_version") == "1.0.0", "PROVIDER_CONTRACT_SCHEMA_INVALID")
    _require(isinstance(raw.get("contracts"), list), "PROVIDER_CONTRACTS_INVALID")
    return raw


def _find_binance_order_book_contract(provider_id: str) -> dict[str, Any]:
    _require(provider_id in SUPPORTED_PROVIDER_IDS, "BINANCE_PROVIDER_ID_UNSUPPORTED")
    matches: list[dict[str, Any]] = []
    for record in _load_provider_contract()["contracts"]:
        capability = record.get("order_book_capability") if isinstance(record, Mapping) else None
        if isinstance(capability, Mapping) and capability.get("provider_id") == provider_id:
            matches.append(dict(record))
    _require(len(matches) == 1, "BINANCE_PROVIDER_CAPABILITY_OWNER_NOT_UNIQUE")
    record = matches[0]
    capability = record["order_book_capability"]
    _require(capability.get("qualification_state") == "S2_QUALIFIED_NETWORK_INACTIVE", "BINANCE_CAPABILITY_NOT_S2_QUALIFIED")
    _require(capability.get("network_activation") == "S3_NOT_ACTIVE", "BINANCE_CAPABILITY_S3_BOUNDARY_INVALID")
    _require(capability.get("pagination_allowed") is False, "BINANCE_DEPTH_PAGINATION_FORBIDDEN")
    _require(capability.get("sequential_rest_stitching_allowed") is False, "BINANCE_DEPTH_STITCHING_FORBIDDEN")
    _require(capability.get("coverage_guaranteed_by_level_count") is False, "BINANCE_LEVEL_COUNT_CANNOT_GUARANTEE_COVERAGE")
    max_depth = _positive_int(capability.get("normative_max_depth"), "BINANCE_NORMATIVE_MAX_DEPTH_INVALID")
    _require(max_depth <= MAX_REST_LEVELS_PER_SIDE_HARD_ARCHITECTURAL_CAP, "BINANCE_PROVIDER_DEPTH_EXCEEDS_AIFE_CAP")
    _require(capability.get("book_kind") in {"L2_LEVEL_BOOK", "FUTURES_L2_BOOK"}, "BINANCE_BOOK_KIND_INVALID")
    expected_host = "https://api.binance.com" if provider_id == "binance-spot" else "https://fapi.binance.com"
    _require(capability.get("canonical_base_host") == expected_host, "BINANCE_CANONICAL_BASE_HOST_INVALID")
    _require(capability.get("supported_instruments") == ["ETHUSDT", "BTCUSDT"], "BINANCE_INITIAL_INSTRUMENT_SCOPE_INVALID")
    return deepcopy(record)


def get_binance_provider_capability(provider_id: str) -> dict[str, Any]:
    """Return a defensive copy of canonical S2-qualified provider capability."""
    return _find_binance_order_book_contract(provider_id)


def _depth_is_supported(capability: Mapping[str, Any], depth: int) -> bool:
    supported = capability.get("supported_depth_values")
    _require(isinstance(supported, Mapping), "BINANCE_SUPPORTED_DEPTHS_INVALID")
    mode = supported.get("mode")
    if mode == "INTEGER_RANGE":
        minimum = _positive_int(supported.get("minimum"), "BINANCE_SUPPORTED_DEPTH_MIN_INVALID")
        maximum = _positive_int(supported.get("maximum"), "BINANCE_SUPPORTED_DEPTH_MAX_INVALID")
        return minimum <= depth <= maximum
    if mode == "EXACT_SET":
        values = supported.get("values")
        _require(isinstance(values, list) and values, "BINANCE_SUPPORTED_DEPTH_SET_INVALID")
        return depth in values
    raise BinanceS2Error("BINANCE_SUPPORTED_DEPTH_MODEL_INVALID")


def _request_weight(capability: Mapping[str, Any], depth: int) -> int:
    table = capability.get("request_weight_by_depth")
    _require(isinstance(table, list) and table, "BINANCE_REQUEST_WEIGHT_TABLE_INVALID")
    matches: list[int] = []
    for row in table:
        _require(isinstance(row, Mapping), "BINANCE_REQUEST_WEIGHT_ROW_INVALID")
        weight = _positive_int(row.get("weight"), "BINANCE_REQUEST_WEIGHT_INVALID")
        if "values" in row:
            values = row.get("values")
            _require(isinstance(values, list), "BINANCE_REQUEST_WEIGHT_VALUES_INVALID")
            if depth in values:
                matches.append(weight)
        else:
            minimum = _positive_int(row.get("minimum"), "BINANCE_REQUEST_WEIGHT_MIN_INVALID")
            maximum = _positive_int(row.get("maximum"), "BINANCE_REQUEST_WEIGHT_MAX_INVALID")
            if minimum <= depth <= maximum:
                matches.append(weight)
    _require(len(matches) == 1, "BINANCE_REQUEST_WEIGHT_NOT_UNIQUELY_QUALIFIED")
    return matches[0]


def _validated_s1_acquisition(s1_planner_result: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    _require(isinstance(s1_planner_result, Mapping), "S1_PLANNER_RESULT_REQUIRED")
    try:
        canonical = canonical_plan_bytes(s1_planner_result)
    except LiquidityS1Error as exc:
        raise BinanceS2Error(f"S1_PLAN_REVALIDATION_FAILED:{exc}") from exc
    _require(s1_planner_result.get("decision") == "ACQUISITION_REQUIRED", "S1_RESOURCE_SATISFACTION_BEFORE_PROVIDER_REQUIRED")
    _require(s1_planner_result.get("network_required") is True, "S1_ACQUISITION_REQUIRED_STATE_INVALID")
    plan = s1_planner_result.get("acquisition_plan")
    _require(isinstance(plan, Mapping), "S1_ACQUISITION_PLAN_REQUIRED")
    provider_id = plan.get("provider_id")
    instrument_id = plan.get("instrument_id")
    target_bps = str(plan.get("target_bps"))
    _require(provider_id in SUPPORTED_PROVIDER_IDS, "BINANCE_PROVIDER_ID_UNSUPPORTED")
    _require(instrument_id in SUPPORTED_INSTRUMENTS, "BINANCE_INSTRUMENT_UNSUPPORTED")
    _require(target_bps in SUPPORTED_TARGET_BPS, "BINANCE_TARGET_BPS_UNSUPPORTED")
    return dict(plan), canonical


def _bind_semantic_request_to_s1_plan(
    semantic_request: Mapping[str, Any],
    s1_plan: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        request = normalize_liquidity_request(semantic_request)
    except LiquidityS1Error as exc:
        raise BinanceS2Error(f"S1_REQUEST_REVALIDATION_FAILED:{exc}") from exc
    bindings = {
        "provider_id": "provider_id",
        "instrument_id": "instrument_id",
        "book_kind": "book_kind",
        "representation": "requested_representation",
        "requested_bid_coverage_bps": "requested_bid_coverage_bps",
        "requested_ask_coverage_bps": "requested_ask_coverage_bps",
        "target_bps": "target_bps",
        "bucket_bps": "bucket_bps",
        "freshness": "freshness",
        "completeness": "completeness",
    }
    for request_field, plan_field in bindings.items():
        _require(request[request_field] == s1_plan.get(plan_field), f"S1_REQUEST_PLAN_BINDING_MISMATCH:{request_field}")
    return request


def build_binance_provider_plan(
    s1_planner_result: Mapping[str, Any],
    *,
    request_weight_budget: int,
    max_raw_resource_bytes: int,
) -> dict[str, Any]:
    """Map an already validated S1 acquisition requirement to one bounded S2 REST plan.

    DB-C deliberately chooses the first-party documented provider maximum for a
    single REST observation. There is no qualified level-count -> bps mapping,
    so a shallower count must not be presented as semantically sufficient.
    """
    s1_plan, s1_bytes = _validated_s1_acquisition(s1_planner_result)
    budget = _positive_int(request_weight_budget, "REQUEST_WEIGHT_BUDGET_INVALID")
    raw_bytes = _positive_int(max_raw_resource_bytes, "MAX_RAW_RESOURCE_BYTES_INVALID")
    _require(raw_bytes <= MAX_RAW_RESOURCE_BYTES_HARD_CAP, "MAX_RAW_RESOURCE_BYTES_EXCEEDS_HARD_CAP")

    provider_id = str(s1_plan["provider_id"])
    contract = _find_binance_order_book_contract(provider_id)
    capability = contract["order_book_capability"]
    _require(s1_plan.get("book_kind") == capability["book_kind"], "BINANCE_BOOK_KIND_MISMATCH")
    _require(s1_plan.get("instrument_id") in capability["supported_instruments"], "BINANCE_INSTRUMENT_NOT_QUALIFIED")

    depth = _positive_int(capability["normative_max_depth"], "BINANCE_NORMATIVE_MAX_DEPTH_INVALID")
    _require(_depth_is_supported(capability, depth), "BINANCE_NORMATIVE_MAX_DEPTH_NOT_SUPPORTED")
    weight = _request_weight(capability, depth)
    _require(budget >= weight, "REQUEST_WEIGHT_BUDGET_INSUFFICIENT_FOR_QUALIFIED_MAX")

    material: dict[str, Any] = {
        "schema_version": S2_PLAN_SCHEMA,
        "provider_id": provider_id,
        "provider_product": contract["product"],
        "instrument_id": s1_plan["instrument_id"],
        "book_kind": s1_plan["book_kind"],
        "source_representation": "RAW",
        "requested_target_bps": str(s1_plan["target_bps"]),
        "endpoint_family": capability["endpoint_family"],
        "canonical_base_host": capability["canonical_base_host"],
        "endpoint_path": capability["endpoint_path"],
        "http_method": "GET",
        "provider_depth_parameter_name": "limit",
        "provider_requested_level_count": depth,
        "provider_normative_max_depth": depth,
        "request_weight": weight,
        "request_weight_budget": budget,
        "max_raw_resource_bytes": raw_bytes,
        "provider_capability_sha256": sha256_canonical_json(capability),
        "s1_plan_sha256": s1_plan["plan_sha256"],
        "s1_plan_bytes_sha256": hashlib.sha256(s1_bytes).hexdigest(),
        "coverage_guaranteed_by_level_count": False,
        "one_rest_response_one_observation": True,
        "pagination_allowed": False,
        "sequential_rest_stitching_allowed": False,
        "retry_semantics": "NEW_OBSERVATION",
        "network_execution": NETWORK_EXECUTION_STATE,
    }
    material["provider_plan_sha256"] = sha256_canonical_json(material)
    return material


def validate_binance_provider_plan(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
) -> dict[str, Any]:
    _require(isinstance(provider_plan, Mapping), "BINANCE_PROVIDER_PLAN_REQUIRED")
    expected_fields = {
        "schema_version", "provider_id", "provider_product", "instrument_id", "book_kind",
        "source_representation", "requested_target_bps", "endpoint_family", "canonical_base_host", "endpoint_path",
        "http_method", "provider_depth_parameter_name", "provider_requested_level_count",
        "provider_normative_max_depth", "request_weight", "request_weight_budget",
        "max_raw_resource_bytes", "provider_capability_sha256", "s1_plan_sha256",
        "s1_plan_bytes_sha256", "coverage_guaranteed_by_level_count",
        "one_rest_response_one_observation", "pagination_allowed",
        "sequential_rest_stitching_allowed", "retry_semantics", "network_execution",
        "provider_plan_sha256",
    }
    _require(set(provider_plan) == expected_fields, "BINANCE_PROVIDER_PLAN_FIELDS_INVALID")
    _require(provider_plan.get("schema_version") == S2_PLAN_SCHEMA, "BINANCE_PROVIDER_PLAN_SCHEMA_INVALID")
    expected = build_binance_provider_plan(
        s1_planner_result,
        request_weight_budget=_positive_int(provider_plan.get("request_weight_budget"), "REQUEST_WEIGHT_BUDGET_INVALID"),
        max_raw_resource_bytes=_positive_int(provider_plan.get("max_raw_resource_bytes"), "MAX_RAW_RESOURCE_BYTES_INVALID"),
    )
    _require(dict(provider_plan) == expected, "BINANCE_PROVIDER_PLAN_REVALIDATION_MISMATCH")
    return expected


def _raw_response_size(raw_response: Mapping[str, Any]) -> int:
    return len(json.dumps(raw_response, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _raw_response_levels(provider_id: str, raw_response: Mapping[str, Any]) -> tuple[Sequence[Any], Sequence[Any]]:
    _require(isinstance(raw_response, Mapping), "ONE_BINANCE_REST_RESPONSE_MAPPING_REQUIRED")
    allowed = {"lastUpdateId", "bids", "asks"} if provider_id == "binance-spot" else {"lastUpdateId", "E", "T", "bids", "asks"}
    _require(set(raw_response) == allowed, "BINANCE_RESPONSE_FIELDS_INVALID")
    _require(isinstance(raw_response.get("lastUpdateId"), int), "BINANCE_LAST_UPDATE_ID_INVALID")
    if provider_id == "binance-usdm":
        _require(isinstance(raw_response.get("E"), int) and isinstance(raw_response.get("T"), int), "BINANCE_USDM_RESPONSE_TIMESTAMPS_INVALID")
    bids = raw_response.get("bids")
    asks = raw_response.get("asks")
    _require(isinstance(bids, list) and isinstance(asks, list), "BINANCE_RESPONSE_LEVELS_INVALID")
    _require(bool(bids) and bool(asks), "BINANCE_RESPONSE_EMPTY_BOOK")
    return bids, asks


def normalize_binance_order_book_response(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    """Cross one provider response through the canonical S1 physical-book boundary.

    ``observation_timestamp_ms`` is backward-compatible consistency evidence
    only. It cannot set freshness time; canonical current-data acquisition time
    is authoritative and a mismatching caller claim fails closed.
    """
    plan = validate_binance_provider_plan(provider_plan, s1_planner_result)
    _require(_raw_response_size(raw_response) <= plan["max_raw_resource_bytes"], "BINANCE_RAW_RESOURCE_BYTES_EXCEEDED")
    bids, asks = _raw_response_levels(plan["provider_id"], raw_response)
    requested = plan["provider_requested_level_count"]
    _require(len(bids) <= requested and len(asks) <= requested, "BINANCE_RESPONSE_EXCEEDS_REQUESTED_DEPTH")
    _require(isinstance(observation_id, str) and observation_id.strip() == observation_id and observation_id, "OBSERVATION_ID_INVALID")
    canonical_timestamp_ms = _canonical_observation_timestamp_ms()
    if observation_timestamp_ms is not None:
        claimed_timestamp_ms = _positive_int(observation_timestamp_ms, "CALLER_OBSERVATION_TIMESTAMP_MS_INVALID")
        _require(
            claimed_timestamp_ms == canonical_timestamp_ms,
            "CALLER_OBSERVATION_TIMESTAMP_NOT_AUTHORITY",
        )

    observation = {
        "observation_id": observation_id,
        "provider_id": plan["provider_id"],
        "instrument_id": plan["instrument_id"],
        "book_kind": plan["book_kind"],
        "source_representation": "RAW",
        "timestamp_ms": canonical_timestamp_ms,
        "bids": bids,
        "asks": asks,
    }
    try:
        only = assert_one_coherent_provider_observation([observation])
        normalized = normalize_order_book_observation(only)
        return validate_normalized_order_book(normalized)
    except LiquidityS1Error as exc:
        raise BinanceS2Error(f"S1_BOOK_REVALIDATION_FAILED:{exc}") from exc


def _native_quantity_total(normalized_book: Mapping[str, Any]) -> str:
    book = validate_normalized_order_book(normalized_book)
    total = Decimal("0")
    for side in ("bids", "asks"):
        for level in book[side]:
            total += _decimal(level[1], "BINANCE_NATIVE_QUANTITY_INVALID")
    return format(total, "f")


def build_binance_liquidity_resource(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    """Build a network-inactive S2 result whose trust boundaries remain S1-owned."""
    plan = validate_binance_provider_plan(provider_plan, s1_planner_result)
    s1_plan, _ = _validated_s1_acquisition(s1_planner_result)
    request = _bind_semantic_request_to_s1_plan(semantic_request, s1_plan)
    book = normalize_binance_order_book_response(
        plan,
        s1_planner_result,
        raw_response,
        observation_id=observation_id,
        observation_timestamp_ms=observation_timestamp_ms,
    )
    contract = _find_binance_order_book_contract(plan["provider_id"])
    capability = contract["order_book_capability"]
    quantity = qualify_quantity_semantics(
        provider_id=plan["provider_id"],
        instrument_id=plan["instrument_id"],
        book_kind=plan["book_kind"],
        native_quantity=_native_quantity_total(book),
        native_quantity_unit=capability["native_quantity_unit_id"],
    )
    quantity = validate_quantity_semantics(quantity)
    resource = qualify_liquidity_resource(book, request, quantity_semantics=quantity)
    resource = validate_qualified_liquidity_resource(resource)
    coverage = compute_side_coverage(book, request)
    _require(resource["truncated"] == coverage["truncated"], "BINANCE_TRUNCATED_STATE_MISMATCH")
    _require(not (resource["truncated"] and resource["request_satisfied"]), "BINANCE_TRUNCATED_CANNOT_BE_COMPLETE")

    result = {
        "schema_version": S2_RESULT_SCHEMA,
        "provider_plan_sha256": plan["provider_plan_sha256"],
        "provider_id": plan["provider_id"],
        "instrument_id": plan["instrument_id"],
        "provider_requested_level_count": plan["provider_requested_level_count"],
        "actual_observed_bid_level_count": len(book["bids"]),
        "actual_observed_ask_level_count": len(book["asks"]),
        "provider_limit_exhausted": plan["provider_requested_level_count"] == plan["provider_normative_max_depth"],
        "requested_target_bps": plan["requested_target_bps"],
        "achieved_bid_coverage_bps": coverage["achieved_bid_coverage_bps"],
        "achieved_ask_coverage_bps": coverage["achieved_ask_coverage_bps"],
        "coverage_complete_bid": coverage["coverage_complete_bid"],
        "coverage_complete_ask": coverage["coverage_complete_ask"],
        "coverage_complete": coverage["coverage_complete_bid"] and coverage["coverage_complete_ask"],
        "truncated": coverage["truncated"],
        "normalized_book": book,
        "quantity_semantics": quantity,
        "qualified_resource": resource,
        "network_execution": NETWORK_EXECUTION_STATE,
    }
    result["result_sha256"] = sha256_canonical_json(result)
    return result


def validate_binance_liquidity_result(result: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(result, Mapping), "BINANCE_RESULT_REQUIRED")
    _require(result.get("schema_version") == S2_RESULT_SCHEMA, "BINANCE_RESULT_SCHEMA_INVALID")
    _require(result.get("network_execution") == NETWORK_EXECUTION_STATE, "BINANCE_RESULT_S3_BOUNDARY_INVALID")
    _require(result.get("coverage_complete") == (
        result.get("coverage_complete_bid") is True and result.get("coverage_complete_ask") is True
    ), "BINANCE_RESULT_COVERAGE_COMPLETE_MISMATCH")
    _require(not (result.get("truncated") is True and result.get("coverage_complete") is True), "BINANCE_TRUNCATED_CANNOT_BE_COMPLETE")
    book = validate_normalized_order_book(result.get("normalized_book"))
    quantity = validate_quantity_semantics(result.get("quantity_semantics"))
    resource = validate_qualified_liquidity_resource(result.get("qualified_resource"))
    _require(book["provider_id"] == result.get("provider_id"), "BINANCE_RESULT_PROVIDER_MISMATCH")
    _require(book["instrument_id"] == result.get("instrument_id"), "BINANCE_RESULT_INSTRUMENT_MISMATCH")
    _require(quantity["provider_id"] == result.get("provider_id"), "BINANCE_RESULT_QUANTITY_PROVIDER_MISMATCH")
    _require(resource["observation_sha256"] == book["observation_sha256"], "BINANCE_RESULT_RESOURCE_BOOK_MISMATCH")
    material = dict(result)
    supplied_hash = material.pop("result_sha256", None)
    _require(supplied_hash == sha256_canonical_json(material), "BINANCE_RESULT_SHA256_MISMATCH")
    return dict(result)

S3_EXECUTION_DELEGATION = "REQUEST_SCOPED_S3_EXECUTOR_AFTER_S2_REVALIDATION"
