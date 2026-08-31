from __future__ import annotations

import hashlib
import json
import zlib
from copy import deepcopy
from datetime import datetime
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

S2_PLAN_SCHEMA = "liquidity-s2-kraken-spot-provider-plan/1.0.0"
S2_RESULT_SCHEMA = "liquidity-s2-kraken-spot-normalized-result/1.0.0"
PROVIDER_ID = "kraken-spot"
BOOK_KIND = "L2_LEVEL_BOOK"
CANONICAL_ROUTE_ID = "KRAKEN_SPOT_WS_V2_BOOK_INITIAL_SNAPSHOT"
REST_ROUTE_ID = "KRAKEN_SPOT_REST_DEPTH_SNAPSHOT"
NETWORK_EXECUTION_STATE = "S3_NOT_ACTIVE"
MAX_RAW_RESOURCE_BYTES_HARD_CAP = 8 * 1024 * 1024
MAX_PROVIDER_OBSERVATIONS_PER_SEMANTIC_REQUEST = 1
MAX_PHYSICAL_ROUTES_PER_OBSERVATION = 1
MAX_REST_CALLS_PER_OBSERVATION = 1
SUPPORTED_TARGET_BPS = {"250", "500"}
SUPPORTED_INSTRUMENTS = {"ETHUSD", "BTCUSD"}
RESULT_FIELDS = {
    "schema_version",
    "provider_plan",
    "provider_plan_sha256",
    "provider_id",
    "instrument_id",
    "route_id",
    "provider_requested_level_count",
    "actual_observed_bid_level_count",
    "actual_observed_ask_level_count",
    "provider_limit_exhausted",
    "provider_message_integrity",
    "requested_target_bps",
    "achieved_bid_coverage_bps",
    "achieved_ask_coverage_bps",
    "coverage_complete_bid",
    "coverage_complete_ask",
    "coverage_complete",
    "truncated",
    "normalized_book",
    "quantity_semantics",
    "qualified_resource",
    "network_execution",
    "result_sha256",
}


class KrakenSpotS2Error(ValueError):
    """Fail-closed DB-D1 provider qualification/adapter error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise KrakenSpotS2Error(code)


def _positive_int(value: Any, code: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value > 0, code)
    return value


def _decimal(value: Any, code: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise KrakenSpotS2Error(code)
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise KrakenSpotS2Error(code) from None
    _require(parsed.is_finite(), code)
    _require(parsed > 0 if positive else parsed >= 0, code)
    return parsed


def _canonical_observation_timestamp_ms() -> int:
    try:
        current = current_data_transport._utc_now()
        offset = current.utcoffset()
    except Exception as exc:
        raise KrakenSpotS2Error("S1_TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    _require(offset is not None and offset.total_seconds() == 0, "S1_TEMPORAL_AUTHORITY_NOT_UTC")
    return _positive_int(int(current.timestamp() * 1000), "S1_TEMPORAL_AUTHORITY_TIMESTAMP_INVALID")


def _load_provider_contract() -> dict[str, Any]:
    raw = json.loads(PROVIDER_CONTRACT_PATH.read_text(encoding="utf-8"))
    _require(raw.get("schema_version") == "1.0.0", "PROVIDER_CONTRACT_SCHEMA_INVALID")
    _require(isinstance(raw.get("contracts"), list), "PROVIDER_CONTRACTS_INVALID")
    return raw


def _find_contract() -> dict[str, Any]:
    matches = []
    for record in _load_provider_contract()["contracts"]:
        capability = record.get("order_book_capability") if isinstance(record, Mapping) else None
        if isinstance(capability, Mapping) and capability.get("provider_id") == PROVIDER_ID:
            matches.append(dict(record))
    _require(len(matches) == 1, "KRAKEN_SPOT_PROVIDER_CAPABILITY_OWNER_NOT_UNIQUE")
    record = matches[0]
    capability = record["order_book_capability"]
    _require(capability.get("qualification_state") == "S2_QUALIFIED_NETWORK_INACTIVE", "KRAKEN_SPOT_CAPABILITY_NOT_S2_QUALIFIED")
    _require(capability.get("semantic_capability_id") == "KRAKEN_SPOT_L2_SEMANTIC_CAPABILITY", "KRAKEN_SPOT_SEMANTIC_CAPABILITY_ID_INVALID")
    _require(capability.get("book_kind") == BOOK_KIND, "KRAKEN_SPOT_BOOK_KIND_INVALID")
    _require(capability.get("supported_instruments") == ["ETHUSD", "BTCUSD"], "KRAKEN_SPOT_INITIAL_INSTRUMENT_SCOPE_INVALID")
    _require(capability.get("canonical_route_id") == CANONICAL_ROUTE_ID, "KRAKEN_SPOT_CANONICAL_ROUTE_INVALID")
    _require(capability.get("automatic_fallback") is False, "KRAKEN_SPOT_AUTOMATIC_FALLBACK_FORBIDDEN")
    _require(capability.get("rest_ws_stitching_allowed") is False, "KRAKEN_SPOT_ROUTE_STITCHING_FORBIDDEN")
    _require(capability.get("coverage_guaranteed_by_level_count") is False, "KRAKEN_SPOT_LEVEL_COUNT_CANNOT_GUARANTEE_COVERAGE")
    _require(capability.get("stateful_ws_local_book_active") is False, "KRAKEN_SPOT_STATEFUL_WS_FORBIDDEN")
    _require(capability.get("network_activation") == NETWORK_EXECUTION_STATE, "KRAKEN_SPOT_S3_BOUNDARY_INVALID")
    routes = capability.get("routes")
    _require(isinstance(routes, Mapping) and set(routes) == {REST_ROUTE_ID, CANONICAL_ROUTE_ID}, "KRAKEN_SPOT_ROUTES_INVALID")
    return deepcopy(record)


def get_kraken_spot_provider_capability() -> dict[str, Any]:
    return _find_contract()


def get_kraken_spot_route(route_id: str) -> dict[str, Any]:
    _require(route_id in {REST_ROUTE_ID, CANONICAL_ROUTE_ID}, "KRAKEN_SPOT_ROUTE_UNSUPPORTED")
    return deepcopy(_find_contract()["order_book_capability"]["routes"][route_id])


def validate_kraken_spot_rest_depth(count: int) -> int:
    count = _positive_int(count, "KRAKEN_SPOT_REST_COUNT_INVALID")
    route = get_kraken_spot_route(REST_ROUTE_ID)
    supported = route.get("supported_depth_values")
    _require(isinstance(supported, Mapping) and supported.get("mode") == "INTEGER_RANGE", "KRAKEN_SPOT_REST_DEPTH_MODEL_INVALID")
    minimum = _positive_int(supported.get("minimum"), "KRAKEN_SPOT_REST_MIN_DEPTH_INVALID")
    maximum = _positive_int(supported.get("maximum"), "KRAKEN_SPOT_REST_MAX_DEPTH_INVALID")
    _require(minimum <= count <= maximum, "KRAKEN_SPOT_REST_COUNT_UNSUPPORTED")
    return count


def validate_kraken_spot_ws_depth(depth: int) -> int:
    depth = _positive_int(depth, "KRAKEN_SPOT_WS_DEPTH_INVALID")
    route = get_kraken_spot_route(CANONICAL_ROUTE_ID)
    supported = route.get("supported_depth_values")
    _require(isinstance(supported, Mapping) and supported.get("mode") == "EXACT_SET", "KRAKEN_SPOT_WS_DEPTH_MODEL_INVALID")
    values = supported.get("values")
    _require(isinstance(values, list) and values, "KRAKEN_SPOT_WS_DEPTH_SET_INVALID")
    _require(depth in values, "KRAKEN_SPOT_WS_DEPTH_UNSUPPORTED")
    return depth


def _instrument_binding(instrument_id: str) -> dict[str, Any]:
    _require(instrument_id in SUPPORTED_INSTRUMENTS, "KRAKEN_SPOT_INSTRUMENT_UNSUPPORTED")
    capability = _find_contract()["order_book_capability"]
    mapping = capability.get("instrument_identity_map")
    _require(isinstance(mapping, Mapping) and set(mapping) == SUPPORTED_INSTRUMENTS, "KRAKEN_SPOT_INSTRUMENT_MAP_INVALID")
    binding = mapping.get(instrument_id)
    _require(isinstance(binding, Mapping), "KRAKEN_SPOT_INSTRUMENT_BINDING_INVALID")
    _require(binding.get("semantic_instrument_id") == instrument_id, "KRAKEN_SPOT_SEMANTIC_INSTRUMENT_BINDING_INVALID")
    return dict(binding)


def _validated_s1_acquisition(s1_planner_result: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    _require(isinstance(s1_planner_result, Mapping), "S1_PLANNER_RESULT_REQUIRED")
    try:
        canonical = canonical_plan_bytes(s1_planner_result)
    except LiquidityS1Error as exc:
        raise KrakenSpotS2Error(f"S1_PLAN_REVALIDATION_FAILED:{exc}") from exc
    _require(s1_planner_result.get("decision") == "ACQUISITION_REQUIRED", "S1_RESOURCE_SATISFACTION_BEFORE_PROVIDER_REQUIRED")
    _require(s1_planner_result.get("network_required") is True, "S1_ACQUISITION_REQUIRED_STATE_INVALID")
    plan = s1_planner_result.get("acquisition_plan")
    _require(isinstance(plan, Mapping), "S1_ACQUISITION_PLAN_REQUIRED")
    _require(plan.get("provider_id") == PROVIDER_ID, "KRAKEN_SPOT_PROVIDER_ID_UNSUPPORTED")
    _require(plan.get("instrument_id") in SUPPORTED_INSTRUMENTS, "KRAKEN_SPOT_INSTRUMENT_UNSUPPORTED")
    _require(plan.get("book_kind") == BOOK_KIND, "KRAKEN_SPOT_BOOK_KIND_MISMATCH")
    _require(str(plan.get("target_bps")) in SUPPORTED_TARGET_BPS, "KRAKEN_SPOT_TARGET_BPS_UNSUPPORTED")
    return dict(plan), canonical


def _bind_semantic_request_to_s1_plan(semantic_request: Mapping[str, Any], s1_plan: Mapping[str, Any]) -> dict[str, Any]:
    try:
        request = normalize_liquidity_request(semantic_request)
    except LiquidityS1Error as exc:
        raise KrakenSpotS2Error(f"S1_REQUEST_REVALIDATION_FAILED:{exc}") from exc
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


def build_kraken_spot_provider_plan(s1_planner_result: Mapping[str, Any], *, max_raw_resource_bytes: int) -> dict[str, Any]:
    s1_plan, s1_bytes = _validated_s1_acquisition(s1_planner_result)
    raw_bytes = _positive_int(max_raw_resource_bytes, "MAX_RAW_RESOURCE_BYTES_INVALID")
    _require(raw_bytes <= MAX_RAW_RESOURCE_BYTES_HARD_CAP, "MAX_RAW_RESOURCE_BYTES_EXCEEDS_HARD_CAP")
    contract = _find_contract()
    capability = contract["order_book_capability"]
    route = capability["routes"][CANONICAL_ROUTE_ID]
    depth = _positive_int(route.get("normative_max_depth"), "KRAKEN_SPOT_WS_NORMATIVE_MAX_DEPTH_INVALID")
    validate_kraken_spot_ws_depth(depth)
    binding = _instrument_binding(str(s1_plan["instrument_id"]))
    provider_symbol = binding.get("ws_v2_symbol")
    _require(isinstance(provider_symbol, str) and provider_symbol, "KRAKEN_SPOT_WS_SYMBOL_INVALID")
    material: dict[str, Any] = {
        "schema_version": S2_PLAN_SCHEMA,
        "provider_id": PROVIDER_ID,
        "provider_product": contract["product"],
        "instrument_id": s1_plan["instrument_id"],
        "book_kind": s1_plan["book_kind"],
        "source_representation": "RAW",
        "requested_target_bps": str(s1_plan["target_bps"]),
        "route_selection_policy": capability["route_selection_policy"],
        "route_id": CANONICAL_ROUTE_ID,
        "transport": route["transport"],
        "endpoint": route["endpoint"],
        "channel": route["channel"],
        "provider_symbol": provider_symbol,
        "provider_depth_parameter_name": "depth",
        "provider_requested_level_count": depth,
        "provider_normative_max_depth": depth,
        "snapshot": True,
        "checksum_policy": route["checksum_semantics"],
        "max_raw_resource_bytes": raw_bytes,
        "max_provider_observations_per_semantic_request": MAX_PROVIDER_OBSERVATIONS_PER_SEMANTIC_REQUEST,
        "max_physical_routes_per_observation": MAX_PHYSICAL_ROUTES_PER_OBSERVATION,
        "provider_capability_sha256": sha256_canonical_json(capability),
        "s1_plan_sha256": s1_plan["plan_sha256"],
        "s1_plan_bytes_sha256": hashlib.sha256(s1_bytes).hexdigest(),
        "coverage_guaranteed_by_level_count": False,
        "rest_ws_stitching_allowed": False,
        "sequential_rest_stitching_allowed": False,
        "automatic_fallback": False,
        "retry_semantics": "NEW_OBSERVATION",
        "network_execution": NETWORK_EXECUTION_STATE,
    }
    material["provider_plan_sha256"] = sha256_canonical_json(material)
    return material


def validate_kraken_spot_provider_plan(provider_plan: Mapping[str, Any], s1_planner_result: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(provider_plan, Mapping), "KRAKEN_SPOT_PROVIDER_PLAN_REQUIRED")
    _require(provider_plan.get("schema_version") == S2_PLAN_SCHEMA, "KRAKEN_SPOT_PROVIDER_PLAN_SCHEMA_INVALID")
    expected = build_kraken_spot_provider_plan(
        s1_planner_result,
        max_raw_resource_bytes=_positive_int(provider_plan.get("max_raw_resource_bytes"), "MAX_RAW_RESOURCE_BYTES_INVALID"),
    )
    _require(dict(provider_plan) == expected, "KRAKEN_SPOT_PROVIDER_PLAN_REVALIDATION_MISMATCH")
    return expected


def _raw_size(value: Mapping[str, Any]) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8"))


def _provider_level_value(value: Any, code: str) -> str:
    _require(isinstance(value, (str, Decimal)), code)
    _decimal(value, code, positive=True)
    return str(value) if isinstance(value, str) else format(value, "f")


def _checksum_component(value: str) -> str:
    compact = value.replace(".", "").lstrip("0")
    return compact or "0"


def compute_kraken_ws_v2_checksum(bids: Sequence[Mapping[str, Any]], asks: Sequence[Mapping[str, Any]]) -> int:
    _require(isinstance(bids, Sequence) and not isinstance(bids, (str, bytes)), "KRAKEN_SPOT_WS_BIDS_INVALID")
    _require(isinstance(asks, Sequence) and not isinstance(asks, (str, bytes)), "KRAKEN_SPOT_WS_ASKS_INVALID")
    bid_rows = []
    ask_rows = []
    for side, rows, target in (("BID", bids, bid_rows), ("ASK", asks, ask_rows)):
        for row in rows:
            _require(isinstance(row, Mapping) and set(row) == {"price", "qty"}, f"KRAKEN_SPOT_WS_{side}_LEVEL_INVALID")
            price = _provider_level_value(row.get("price"), f"KRAKEN_SPOT_WS_{side}_PRICE_INVALID")
            qty = _provider_level_value(row.get("qty"), f"KRAKEN_SPOT_WS_{side}_QTY_INVALID")
            target.append((Decimal(price), price, qty))
    bid_rows.sort(key=lambda row: row[0], reverse=True)
    ask_rows.sort(key=lambda row: row[0])
    material = "".join(_checksum_component(price) + _checksum_component(qty) for _, price, qty in ask_rows[:10])
    material += "".join(_checksum_component(price) + _checksum_component(qty) for _, price, qty in bid_rows[:10])
    return zlib.crc32(material.encode("utf-8")) & 0xFFFFFFFF


def _validate_provider_timestamp(value: Any) -> str:
    _require(
        isinstance(value, str) and value.endswith("Z") and "\n" not in value and "\r" not in value,
        "KRAKEN_SPOT_PROVIDER_TIMESTAMP_INVALID",
    )
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise KrakenSpotS2Error("KRAKEN_SPOT_PROVIDER_TIMESTAMP_INVALID") from exc
    return value


def _ws_snapshot_levels(plan: Mapping[str, Any], raw_response: Mapping[str, Any]) -> tuple[list[list[str]], list[list[str]], str, int]:
    _require(isinstance(raw_response, Mapping), "ONE_KRAKEN_WS_SNAPSHOT_MAPPING_REQUIRED")
    _require(set(raw_response) == {"channel", "type", "data"}, "KRAKEN_SPOT_WS_RESPONSE_FIELDS_INVALID")
    _require(
        raw_response.get("channel") == "book" and raw_response.get("type") == "snapshot",
        "KRAKEN_SPOT_WS_INITIAL_SNAPSHOT_REQUIRED",
    )
    data = raw_response.get("data")
    _require(
        isinstance(data, list) and len(data) == 1 and isinstance(data[0], Mapping),
        "ONE_KRAKEN_WS_SNAPSHOT_DATA_ITEM_REQUIRED",
    )
    item = data[0]
    _require(set(item) == {"symbol", "bids", "asks", "checksum", "timestamp"}, "KRAKEN_SPOT_WS_SNAPSHOT_FIELDS_INVALID")
    _require(item.get("symbol") == plan["provider_symbol"], "KRAKEN_SPOT_WS_SYMBOL_MISMATCH")
    bids, asks = item.get("bids"), item.get("asks")
    _require(isinstance(bids, list) and isinstance(asks, list) and bids and asks, "KRAKEN_SPOT_WS_EMPTY_BOOK")
    _require(
        len(bids) <= plan["provider_requested_level_count"] and len(asks) <= plan["provider_requested_level_count"],
        "KRAKEN_SPOT_WS_RESPONSE_EXCEEDS_REQUESTED_DEPTH",
    )
    supplied = item.get("checksum")
    _require(
        isinstance(supplied, int) and not isinstance(supplied, bool) and 0 <= supplied <= 0xFFFFFFFF,
        "KRAKEN_SPOT_WS_CHECKSUM_MALFORMED",
    )
    expected = compute_kraken_ws_v2_checksum(bids, asks)
    _require(supplied == expected, "KRAKEN_SPOT_WS_CHECKSUM_MISMATCH")
    timestamp = _validate_provider_timestamp(item.get("timestamp"))
    normalized_bids = [
        [
            _provider_level_value(level["price"], "KRAKEN_SPOT_WS_BID_PRICE_INVALID"),
            _provider_level_value(level["qty"], "KRAKEN_SPOT_WS_BID_QTY_INVALID"),
        ]
        for level in bids
    ]
    normalized_asks = [
        [
            _provider_level_value(level["price"], "KRAKEN_SPOT_WS_ASK_PRICE_INVALID"),
            _provider_level_value(level["qty"], "KRAKEN_SPOT_WS_ASK_QTY_INVALID"),
        ]
        for level in asks
    ]
    return normalized_bids, normalized_asks, timestamp, supplied


def normalize_kraken_spot_ws_snapshot(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    plan = validate_kraken_spot_provider_plan(provider_plan, s1_planner_result)
    _require(_raw_size(raw_response) <= plan["max_raw_resource_bytes"], "KRAKEN_SPOT_RAW_RESOURCE_BYTES_EXCEEDED")
    bids, asks, _provider_timestamp, _checksum = _ws_snapshot_levels(plan, raw_response)
    _require(
        isinstance(observation_id, str) and observation_id.strip() == observation_id and observation_id,
        "OBSERVATION_ID_INVALID",
    )
    canonical_timestamp_ms = _canonical_observation_timestamp_ms()
    if observation_timestamp_ms is not None:
        claim = _positive_int(observation_timestamp_ms, "CALLER_OBSERVATION_TIMESTAMP_MS_INVALID")
        _require(claim == canonical_timestamp_ms, "CALLER_OBSERVATION_TIMESTAMP_NOT_AUTHORITY")
    observation = {
        "observation_id": observation_id,
        "provider_id": PROVIDER_ID,
        "instrument_id": plan["instrument_id"],
        "book_kind": BOOK_KIND,
        "source_representation": "RAW",
        "timestamp_ms": canonical_timestamp_ms,
        "bids": bids,
        "asks": asks,
    }
    try:
        only = assert_one_coherent_provider_observation([observation])
        return validate_normalized_order_book(normalize_order_book_observation(only))
    except LiquidityS1Error as exc:
        raise KrakenSpotS2Error(f"S1_BOOK_REVALIDATION_FAILED:{exc}") from exc


def normalize_kraken_spot_rest_snapshot(
    instrument_id: str,
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    route = get_kraken_spot_route(REST_ROUTE_ID)
    binding = _instrument_binding(instrument_id)
    _require(
        isinstance(raw_response, Mapping) and set(raw_response) == {"error", "result"},
        "ONE_KRAKEN_REST_RESPONSE_MAPPING_REQUIRED",
    )
    _require(raw_response.get("error") == [], "KRAKEN_SPOT_REST_PROVIDER_ERROR")
    result = raw_response.get("result")
    expected_key = binding["rest_asset_version_1_result_key"]
    _require(
        isinstance(result, Mapping) and set(result) == {expected_key},
        "KRAKEN_SPOT_REST_PAIR_IDENTITY_MISMATCH",
    )
    book = result[expected_key]
    _require(isinstance(book, Mapping) and set(book) == {"bids", "asks"}, "KRAKEN_SPOT_REST_BOOK_FIELDS_INVALID")
    bids, asks = book.get("bids"), book.get("asks")
    _require(isinstance(bids, list) and isinstance(asks, list) and bids and asks, "KRAKEN_SPOT_REST_EMPTY_BOOK")
    max_depth = route["normative_max_depth"]
    _require(len(bids) <= max_depth and len(asks) <= max_depth, "KRAKEN_SPOT_REST_RESPONSE_EXCEEDS_MAX_DEPTH")
    converted = []
    for rows in (bids, asks):
        levels = []
        for row in rows:
            _require(isinstance(row, list) and len(row) == 3, "KRAKEN_SPOT_REST_LEVEL_INVALID")
            price = _provider_level_value(row[0], "KRAKEN_SPOT_REST_PRICE_INVALID")
            qty = _provider_level_value(row[1], "KRAKEN_SPOT_REST_QTY_INVALID")
            _decimal(row[2], "KRAKEN_SPOT_REST_LEVEL_TIMESTAMP_INVALID")
            levels.append([price, qty])
        converted.append(levels)
    canonical_timestamp_ms = _canonical_observation_timestamp_ms()
    if observation_timestamp_ms is not None:
        claim = _positive_int(observation_timestamp_ms, "CALLER_OBSERVATION_TIMESTAMP_MS_INVALID")
        _require(claim == canonical_timestamp_ms, "CALLER_OBSERVATION_TIMESTAMP_NOT_AUTHORITY")
    observation = {
        "observation_id": observation_id,
        "provider_id": PROVIDER_ID,
        "instrument_id": instrument_id,
        "book_kind": BOOK_KIND,
        "source_representation": "RAW",
        "timestamp_ms": canonical_timestamp_ms,
        "bids": converted[0],
        "asks": converted[1],
    }
    try:
        return validate_normalized_order_book(
            normalize_order_book_observation(assert_one_coherent_provider_observation([observation]))
        )
    except LiquidityS1Error as exc:
        raise KrakenSpotS2Error(f"S1_BOOK_REVALIDATION_FAILED:{exc}") from exc


def _native_quantity_total(book: Mapping[str, Any]) -> str:
    canonical = validate_normalized_order_book(book)
    total = Decimal("0")
    for side in ("bids", "asks"):
        for level in canonical[side]:
            total += _decimal(level[1], "KRAKEN_SPOT_NATIVE_QUANTITY_INVALID")
    return format(total, "f")


def build_kraken_spot_liquidity_resource(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    plan = validate_kraken_spot_provider_plan(provider_plan, s1_planner_result)
    s1_plan, _ = _validated_s1_acquisition(s1_planner_result)
    request = _bind_semantic_request_to_s1_plan(semantic_request, s1_plan)
    book = normalize_kraken_spot_ws_snapshot(
        plan,
        s1_planner_result,
        raw_response,
        observation_id=observation_id,
        observation_timestamp_ms=observation_timestamp_ms,
    )
    capability = _find_contract()["order_book_capability"]
    quantity = validate_quantity_semantics(
        qualify_quantity_semantics(
            provider_id=PROVIDER_ID,
            instrument_id=plan["instrument_id"],
            book_kind=BOOK_KIND,
            native_quantity=_native_quantity_total(book),
            native_quantity_unit=capability["native_quantity_unit_id"],
        )
    )
    resource = validate_qualified_liquidity_resource(
        qualify_liquidity_resource(book, request, quantity_semantics=quantity)
    )
    coverage = compute_side_coverage(book, request)
    _require(resource["truncated"] == coverage["truncated"], "KRAKEN_SPOT_TRUNCATED_STATE_MISMATCH")
    result = {
        "schema_version": S2_RESULT_SCHEMA,
        "provider_plan": dict(plan),
        "provider_plan_sha256": plan["provider_plan_sha256"],
        "provider_id": PROVIDER_ID,
        "instrument_id": plan["instrument_id"],
        "route_id": plan["route_id"],
        "provider_requested_level_count": plan["provider_requested_level_count"],
        "actual_observed_bid_level_count": len(book["bids"]),
        "actual_observed_ask_level_count": len(book["asks"]),
        "provider_limit_exhausted": plan["provider_requested_level_count"] == plan["provider_normative_max_depth"],
        "provider_message_integrity": "KRAKEN_WS_V2_CRC32_TOP10_VALIDATED",
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


def validate_kraken_spot_liquidity_result(
    result: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
) -> dict[str, Any]:
    _require(isinstance(result, Mapping), "KRAKEN_SPOT_RESULT_REQUIRED")
    _require(set(result) == RESULT_FIELDS, "KRAKEN_SPOT_RESULT_FIELDS_INVALID")
    _require(result.get("schema_version") == S2_RESULT_SCHEMA, "KRAKEN_SPOT_RESULT_SCHEMA_INVALID")

    provider_plan = result.get("provider_plan")
    _require(isinstance(provider_plan, Mapping), "KRAKEN_SPOT_RESULT_PROVIDER_PLAN_REQUIRED")
    plan = validate_kraken_spot_provider_plan(provider_plan, s1_planner_result)
    _require(result.get("provider_plan_sha256") == plan["provider_plan_sha256"], "KRAKEN_SPOT_RESULT_PROVIDER_PLAN_SHA_MISMATCH")
    _require(result.get("provider_id") == plan["provider_id"] == PROVIDER_ID, "KRAKEN_SPOT_RESULT_PROVIDER_MISMATCH")
    _require(result.get("instrument_id") == plan["instrument_id"], "KRAKEN_SPOT_RESULT_INSTRUMENT_MISMATCH")
    _require(result.get("route_id") == plan["route_id"] == CANONICAL_ROUTE_ID, "KRAKEN_SPOT_RESULT_ROUTE_INVALID")
    _require(
        result.get("provider_requested_level_count") == plan["provider_requested_level_count"],
        "KRAKEN_SPOT_RESULT_PROVIDER_DEPTH_MISMATCH",
    )
    _require(
        result.get("provider_limit_exhausted")
        == (plan["provider_requested_level_count"] == plan["provider_normative_max_depth"]),
        "KRAKEN_SPOT_RESULT_PROVIDER_LIMIT_STATE_MISMATCH",
    )
    _require(
        result.get("provider_message_integrity") == "KRAKEN_WS_V2_CRC32_TOP10_VALIDATED",
        "KRAKEN_SPOT_RESULT_INTEGRITY_STATE_INVALID",
    )
    _require(result.get("network_execution") == NETWORK_EXECUTION_STATE, "KRAKEN_SPOT_RESULT_S3_BOUNDARY_INVALID")

    book = validate_normalized_order_book(result.get("normalized_book"))
    quantity = validate_quantity_semantics(result.get("quantity_semantics"))
    resource = validate_qualified_liquidity_resource(result.get("qualified_resource"))
    request = normalize_liquidity_request(resource["qualification_request"])

    _require(resource["normalized_book"] == book, "KRAKEN_SPOT_RESULT_RESOURCE_BOOK_MISMATCH")
    _require(resource["quantity_semantics"] == quantity, "KRAKEN_SPOT_RESULT_RESOURCE_QUANTITY_MISMATCH")
    _require(book["provider_id"] == PROVIDER_ID and book["instrument_id"] == result.get("instrument_id"), "KRAKEN_SPOT_RESULT_BOOK_IDENTITY_MISMATCH")
    _require(quantity["provider_id"] == PROVIDER_ID and quantity["instrument_id"] == result.get("instrument_id"), "KRAKEN_SPOT_RESULT_QUANTITY_IDENTITY_MISMATCH")
    _require(resource["provider_id"] == PROVIDER_ID and resource["instrument_id"] == result.get("instrument_id"), "KRAKEN_SPOT_RESULT_RESOURCE_IDENTITY_MISMATCH")
    _require(request["provider_id"] == PROVIDER_ID and request["instrument_id"] == result.get("instrument_id"), "KRAKEN_SPOT_RESULT_REQUEST_IDENTITY_MISMATCH")
    _require(request["target_bps"] == result.get("requested_target_bps") == plan["requested_target_bps"], "KRAKEN_SPOT_RESULT_TARGET_BPS_MISMATCH")

    _require(result.get("actual_observed_bid_level_count") == len(book["bids"]), "KRAKEN_SPOT_RESULT_BID_LEVEL_COUNT_MISMATCH")
    _require(result.get("actual_observed_ask_level_count") == len(book["asks"]), "KRAKEN_SPOT_RESULT_ASK_LEVEL_COUNT_MISMATCH")
    for field in (
        "achieved_bid_coverage_bps",
        "achieved_ask_coverage_bps",
        "coverage_complete_bid",
        "coverage_complete_ask",
        "truncated",
    ):
        _require(result.get(field) == resource[field], f"KRAKEN_SPOT_RESULT_{field.upper()}_MISMATCH")
    expected_complete = resource["coverage_complete_bid"] and resource["coverage_complete_ask"]
    _require(result.get("coverage_complete") == expected_complete, "KRAKEN_SPOT_RESULT_COVERAGE_COMPLETE_MISMATCH")
    _require(not (result.get("truncated") is True and expected_complete), "KRAKEN_SPOT_TRUNCATED_CANNOT_BE_COMPLETE")

    material = dict(result)
    supplied_hash = material.pop("result_sha256", None)
    _require(supplied_hash == sha256_canonical_json(material), "KRAKEN_SPOT_RESULT_SHA256_MISMATCH")
    return dict(result)

S3_EXECUTION_DELEGATION = "REQUEST_SCOPED_S3_EXECUTOR_AFTER_S2_REVALIDATION"
