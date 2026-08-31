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

S2_PLAN_SCHEMA = "liquidity-s2-kraken-futures-provider-plan/1.0.0"
S2_RESULT_SCHEMA = "liquidity-s2-kraken-futures-normalized-result/1.0.0"
PROVENANCE_SCHEMA = "liquidity-s2-kraken-futures-provider-provenance/1.0.0"
PROVIDER_ID = "kraken-futures"
BOOK_KIND = "FUTURES_L2_BOOK"
CANONICAL_ROUTE_ID = "KRAKEN_FUTURES_WS_BOOK_INITIAL_SNAPSHOT"
NETWORK_EXECUTION_STATE = "S3_NOT_ACTIVE"
DEPTH_KNOWLEDGE_STATE = "NOT_NORMATIVELY_DOCUMENTED"
PROVIDER_LIMIT_STATE = "UNKNOWN_NOT_NORMATIVELY_DOCUMENTED"
MESSAGE_INTEGRITY_STATE = "SEQUENCE_FIELD_STRUCTURALLY_VALID_NO_CHECKSUM_CLAIM"
MAX_RAW_RESOURCE_BYTES_HARD_CAP = 8 * 1024 * 1024
MAX_PROVIDER_OBSERVATIONS_PER_SEMANTIC_REQUEST = 1
MAX_PHYSICAL_ROUTES_PER_OBSERVATION = 1
SUPPORTED_TARGET_BPS = {"250", "500"}
SUPPORTED_INSTRUMENTS = {"PI_ETHUSD", "PI_XBTUSD"}

RESULT_FIELDS = {
    "schema_version",
    "provider_plan",
    "provider_plan_sha256",
    "provider_id",
    "instrument_id",
    "provider_product_id",
    "route_id",
    "provider_depth_parameter_name",
    "provider_requested_level_count",
    "provider_normative_max_depth",
    "depth_knowledge_state",
    "actual_observed_bid_level_count",
    "actual_observed_ask_level_count",
    "provider_limit_exhausted",
    "provider_message_integrity",
    "provider_provenance",
    "provider_provenance_sha256",
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


class KrakenFuturesS2Error(ValueError):
    """Fail-closed DB-D2 provider qualification/adapter error."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise KrakenFuturesS2Error(code)


def _positive_int(value: Any, code: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value > 0, code)
    return value


def _decimal(value: Any, code: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise KrakenFuturesS2Error(code)
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise KrakenFuturesS2Error(code) from None
    _require(parsed.is_finite(), code)
    _require(parsed > 0 if positive else parsed >= 0, code)
    return parsed


def _canonical_number(value: Any, code: str) -> str:
    parsed = _decimal(value, code, positive=True)
    return format(parsed, "f")


def _canonical_observation_timestamp_ms() -> int:
    try:
        current = current_data_transport._utc_now()
        offset = current.utcoffset()
    except Exception as exc:
        raise KrakenFuturesS2Error("S1_TEMPORAL_AUTHORITY_UNAVAILABLE") from exc
    _require(
        offset is not None and offset.total_seconds() == 0,
        "S1_TEMPORAL_AUTHORITY_NOT_UTC",
    )
    return _positive_int(
        int(current.timestamp() * 1000),
        "S1_TEMPORAL_AUTHORITY_TIMESTAMP_INVALID",
    )


def _load_provider_contract() -> dict[str, Any]:
    raw = json.loads(PROVIDER_CONTRACT_PATH.read_text(encoding="utf-8"))
    _require(raw.get("schema_version") == "1.0.0", "PROVIDER_CONTRACT_SCHEMA_INVALID")
    _require(isinstance(raw.get("contracts"), list), "PROVIDER_CONTRACTS_INVALID")
    return raw


def _find_contract() -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for record in _load_provider_contract()["contracts"]:
        capability = (
            record.get("order_book_capability")
            if isinstance(record, Mapping)
            else None
        )
        if (
            isinstance(capability, Mapping)
            and capability.get("provider_id") == PROVIDER_ID
        ):
            matches.append(dict(record))
    _require(
        len(matches) == 1,
        "KRAKEN_FUTURES_PROVIDER_CAPABILITY_OWNER_NOT_UNIQUE",
    )
    record = matches[0]
    capability = record["order_book_capability"]
    _require(
        capability.get("qualification_state") == "S2_QUALIFIED_NETWORK_INACTIVE",
        "KRAKEN_FUTURES_CAPABILITY_NOT_S2_QUALIFIED",
    )
    _require(
        capability.get("semantic_capability_id")
        == "KRAKEN_FUTURES_RAW_L2_SEMANTIC_CAPABILITY",
        "KRAKEN_FUTURES_SEMANTIC_CAPABILITY_ID_INVALID",
    )
    _require(
        capability.get("book_kind") == BOOK_KIND,
        "KRAKEN_FUTURES_BOOK_KIND_INVALID",
    )
    _require(
        capability.get("supported_instruments") == ["PI_ETHUSD", "PI_XBTUSD"],
        "KRAKEN_FUTURES_INITIAL_INSTRUMENT_SCOPE_INVALID",
    )
    _require(
        capability.get("canonical_route_id") == CANONICAL_ROUTE_ID,
        "KRAKEN_FUTURES_CANONICAL_ROUTE_INVALID",
    )
    _require(
        capability.get("selectable_depth_limit") == DEPTH_KNOWLEDGE_STATE,
        "KRAKEN_FUTURES_DEPTH_KNOWLEDGE_OVERCLAIM",
    )
    _require(
        capability.get("normative_max_depth") == DEPTH_KNOWLEDGE_STATE,
        "KRAKEN_FUTURES_NORMATIVE_MAX_DEPTH_OVERCLAIM",
    )
    _require(
        capability.get("provider_depth_parameter_name") is None,
        "KRAKEN_FUTURES_PROVIDER_DEPTH_PARAMETER_INVENTED",
    )
    _require(
        capability.get("coverage_guaranteed_by_level_count") is False,
        "KRAKEN_FUTURES_LEVEL_COUNT_CANNOT_GUARANTEE_COVERAGE",
    )
    _require(
        capability.get("pf_substitution_for_pi") is False,
        "KRAKEN_FUTURES_PF_PI_SUBSTITUTION_FORBIDDEN",
    )
    _require(
        capability.get("stateful_ws_local_book_active") is False,
        "KRAKEN_FUTURES_STATEFUL_WS_FORBIDDEN",
    )
    _require(
        capability.get("network_activation") == NETWORK_EXECUTION_STATE,
        "KRAKEN_FUTURES_S3_BOUNDARY_INVALID",
    )
    routes = capability.get("routes")
    _require(
        isinstance(routes, Mapping) and set(routes) == {CANONICAL_ROUTE_ID},
        "KRAKEN_FUTURES_ROUTES_INVALID",
    )
    return deepcopy(record)


def get_kraken_futures_provider_capability() -> dict[str, Any]:
    return _find_contract()


def get_kraken_futures_route() -> dict[str, Any]:
    return deepcopy(
        _find_contract()["order_book_capability"]["routes"][CANONICAL_ROUTE_ID]
    )


def _instrument_binding(instrument_id: str) -> dict[str, Any]:
    _require(
        instrument_id in SUPPORTED_INSTRUMENTS,
        "KRAKEN_FUTURES_INSTRUMENT_UNSUPPORTED",
    )
    capability = _find_contract()["order_book_capability"]
    mapping = capability.get("instrument_identity_map")
    _require(
        isinstance(mapping, Mapping) and set(mapping) == SUPPORTED_INSTRUMENTS,
        "KRAKEN_FUTURES_INSTRUMENT_MAP_INVALID",
    )
    binding = mapping.get(instrument_id)
    _require(
        isinstance(binding, Mapping),
        "KRAKEN_FUTURES_INSTRUMENT_BINDING_INVALID",
    )
    _require(
        binding.get("semantic_instrument_id") == instrument_id,
        "KRAKEN_FUTURES_SEMANTIC_INSTRUMENT_BINDING_INVALID",
    )
    _require(
        binding.get("ws_product_id") == instrument_id,
        "KRAKEN_FUTURES_WS_PRODUCT_BINDING_INVALID",
    )
    _require(
        binding.get("pf_substitution_allowed") is False,
        "KRAKEN_FUTURES_PF_SUBSTITUTION_FORBIDDEN",
    )
    return dict(binding)


def _validated_s1_acquisition(
    s1_planner_result: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    _require(
        isinstance(s1_planner_result, Mapping),
        "S1_PLANNER_RESULT_REQUIRED",
    )
    try:
        canonical = canonical_plan_bytes(s1_planner_result)
    except LiquidityS1Error as exc:
        raise KrakenFuturesS2Error(
            f"S1_PLAN_REVALIDATION_FAILED:{exc}"
        ) from exc
    _require(
        s1_planner_result.get("decision") == "ACQUISITION_REQUIRED",
        "S1_RESOURCE_SATISFACTION_BEFORE_PROVIDER_REQUIRED",
    )
    _require(
        s1_planner_result.get("network_required") is True,
        "S1_ACQUISITION_REQUIRED_STATE_INVALID",
    )
    plan = s1_planner_result.get("acquisition_plan")
    _require(isinstance(plan, Mapping), "S1_ACQUISITION_PLAN_REQUIRED")
    _require(
        plan.get("provider_id") == PROVIDER_ID,
        "KRAKEN_FUTURES_PROVIDER_ID_UNSUPPORTED",
    )
    _require(
        plan.get("instrument_id") in SUPPORTED_INSTRUMENTS,
        "KRAKEN_FUTURES_INSTRUMENT_UNSUPPORTED",
    )
    _require(
        plan.get("book_kind") == BOOK_KIND,
        "KRAKEN_FUTURES_BOOK_KIND_MISMATCH",
    )
    _require(
        str(plan.get("target_bps")) in SUPPORTED_TARGET_BPS,
        "KRAKEN_FUTURES_TARGET_BPS_UNSUPPORTED",
    )
    bound = plan.get("provider_depth_bound")
    _require(
        isinstance(bound, Mapping)
        and bound.get("status") == "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED"
        and bound.get("qualified_provider_depth_parameter") is None,
        "KRAKEN_FUTURES_S1_DEPTH_BOUND_MUST_REMAIN_UNQUALIFIED",
    )
    return dict(plan), canonical


def _bind_semantic_request_to_s1_plan(
    semantic_request: Mapping[str, Any],
    s1_plan: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        request = normalize_liquidity_request(semantic_request)
    except LiquidityS1Error as exc:
        raise KrakenFuturesS2Error(
            f"S1_REQUEST_REVALIDATION_FAILED:{exc}"
        ) from exc
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
        _require(
            request[request_field] == s1_plan.get(plan_field),
            f"S1_REQUEST_PLAN_BINDING_MISMATCH:{request_field}",
        )
    return request


def build_kraken_futures_provider_plan(
    s1_planner_result: Mapping[str, Any],
    *,
    max_raw_resource_bytes: int,
) -> dict[str, Any]:
    s1_plan, s1_bytes = _validated_s1_acquisition(s1_planner_result)
    raw_bytes = _positive_int(
        max_raw_resource_bytes,
        "MAX_RAW_RESOURCE_BYTES_INVALID",
    )
    _require(
        raw_bytes <= MAX_RAW_RESOURCE_BYTES_HARD_CAP,
        "MAX_RAW_RESOURCE_BYTES_EXCEEDS_HARD_CAP",
    )
    contract = _find_contract()
    capability = contract["order_book_capability"]
    route = capability["routes"][CANONICAL_ROUTE_ID]
    binding = _instrument_binding(str(s1_plan["instrument_id"]))
    _require(
        route.get("provider_depth_parameter_name") is None,
        "KRAKEN_FUTURES_PROVIDER_DEPTH_PARAMETER_INVENTED",
    )
    _require(
        route.get("selectable_depth_limit") == DEPTH_KNOWLEDGE_STATE,
        "KRAKEN_FUTURES_ROUTE_DEPTH_KNOWLEDGE_OVERCLAIM",
    )
    material: dict[str, Any] = {
        "schema_version": S2_PLAN_SCHEMA,
        "provider_id": PROVIDER_ID,
        "provider_product": contract["product"],
        "instrument_id": s1_plan["instrument_id"],
        "provider_product_id": binding["ws_product_id"],
        "book_kind": s1_plan["book_kind"],
        "source_representation": "RAW",
        "requested_target_bps": str(s1_plan["target_bps"]),
        "route_id": CANONICAL_ROUTE_ID,
        "transport": route["transport"],
        "endpoint": route["endpoint"],
        "feed": route["feed"],
        "provider_depth_parameter_name": None,
        "provider_requested_level_count": None,
        "provider_normative_max_depth": DEPTH_KNOWLEDGE_STATE,
        "depth_knowledge_state": DEPTH_KNOWLEDGE_STATE,
        "read_bound_model": "ONE_INITIAL_SNAPSHOT_PLUS_MAX_RAW_RESOURCE_BYTES",
        "max_raw_resource_bytes": raw_bytes,
        "max_provider_observations_per_semantic_request":
            MAX_PROVIDER_OBSERVATIONS_PER_SEMANTIC_REQUEST,
        "max_physical_routes_per_observation":
            MAX_PHYSICAL_ROUTES_PER_OBSERVATION,
        "provider_capability_sha256": sha256_canonical_json(capability),
        "s1_plan_sha256": s1_plan["plan_sha256"],
        "s1_plan_bytes_sha256": hashlib.sha256(s1_bytes).hexdigest(),
        "coverage_guaranteed_by_level_count": False,
        "rest_ws_stitching_allowed": False,
        "sequential_observation_stitching_allowed": False,
        "retry_semantics": "NEW_OBSERVATION",
        "stateful_ws_local_book_active": False,
        "network_execution": NETWORK_EXECUTION_STATE,
    }
    material["provider_plan_sha256"] = sha256_canonical_json(material)
    return material


def validate_kraken_futures_provider_plan(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
) -> dict[str, Any]:
    _require(
        isinstance(provider_plan, Mapping),
        "KRAKEN_FUTURES_PROVIDER_PLAN_REQUIRED",
    )
    _require(
        provider_plan.get("schema_version") == S2_PLAN_SCHEMA,
        "KRAKEN_FUTURES_PROVIDER_PLAN_SCHEMA_INVALID",
    )
    expected = build_kraken_futures_provider_plan(
        s1_planner_result,
        max_raw_resource_bytes=_positive_int(
            provider_plan.get("max_raw_resource_bytes"),
            "MAX_RAW_RESOURCE_BYTES_INVALID",
        ),
    )
    _require(
        dict(provider_plan) == expected,
        "KRAKEN_FUTURES_PROVIDER_PLAN_REVALIDATION_MISMATCH",
    )
    return expected


def _raw_size(value: Mapping[str, Any]) -> int:
    return len(
        json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    )


def _provider_provenance(
    plan: Mapping[str, Any],
    raw_response: Mapping[str, Any],
) -> dict[str, Any]:
    _require(
        isinstance(raw_response, Mapping),
        "ONE_KRAKEN_FUTURES_WS_SNAPSHOT_REQUIRED",
    )
    _require(
        set(raw_response)
        == {"feed", "product_id", "timestamp", "seq", "tickSize", "bids", "asks"},
        "KRAKEN_FUTURES_WS_SNAPSHOT_FIELDS_INVALID",
    )
    _require(
        raw_response.get("feed") == "book_snapshot",
        "KRAKEN_FUTURES_INITIAL_SNAPSHOT_REQUIRED",
    )
    _require(
        raw_response.get("product_id") == plan["provider_product_id"],
        "KRAKEN_FUTURES_PRODUCT_ID_MISMATCH",
    )
    timestamp = _positive_int(
        raw_response.get("timestamp"),
        "KRAKEN_FUTURES_PROVIDER_TIMESTAMP_INVALID",
    )
    sequence = _positive_int(
        raw_response.get("seq"),
        "KRAKEN_FUTURES_SEQUENCE_INVALID",
    )
    _require(
        raw_response.get("tickSize") is None,
        "KRAKEN_FUTURES_TICK_SIZE_FIELD_NOT_NULL",
    )
    return {
        "schema_version": PROVENANCE_SCHEMA,
        "feed": "book_snapshot",
        "provider_product_id": plan["provider_product_id"],
        "provider_timestamp_ms": timestamp,
        "sequence": sequence,
        "tick_size": None,
        "timestamp_role": "PROVIDER_PROVENANCE_NOT_S1_FRESHNESS_AUTHORITY",
        "sequence_role": "SUBSCRIPTION_MESSAGE_SEQUENCE_NUMBER_STRUCTURAL_ONLY",
        "checksum_semantics": "NOT_NORMATIVELY_DOCUMENTED_FOR_CHOSEN_ROUTE",
    }


def _snapshot_levels(
    plan: Mapping[str, Any],
    raw_response: Mapping[str, Any],
) -> tuple[list[list[str]], list[list[str]], dict[str, Any]]:
    provenance = _provider_provenance(plan, raw_response)
    bids = raw_response.get("bids")
    asks = raw_response.get("asks")
    _require(
        isinstance(bids, list) and isinstance(asks, list) and bids and asks,
        "KRAKEN_FUTURES_WS_EMPTY_BOOK",
    )

    def convert(rows: Sequence[Any], side: str) -> list[list[str]]:
        converted: list[list[str]] = []
        for row in rows:
            _require(
                isinstance(row, Mapping) and set(row) == {"price", "qty"},
                f"KRAKEN_FUTURES_WS_{side}_LEVEL_INVALID",
            )
            converted.append(
                [
                    _canonical_number(
                        row.get("price"),
                        f"KRAKEN_FUTURES_WS_{side}_PRICE_INVALID",
                    ),
                    _canonical_number(
                        row.get("qty"),
                        f"KRAKEN_FUTURES_WS_{side}_QTY_INVALID",
                    ),
                ]
            )
        return converted

    return convert(bids, "BID"), convert(asks, "ASK"), provenance


def normalize_kraken_futures_ws_snapshot(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    plan = validate_kraken_futures_provider_plan(
        provider_plan,
        s1_planner_result,
    )
    _require(
        _raw_size(raw_response) <= plan["max_raw_resource_bytes"],
        "KRAKEN_FUTURES_RAW_RESOURCE_BYTES_EXCEEDED",
    )
    bids, asks, _provenance = _snapshot_levels(plan, raw_response)
    _require(
        isinstance(observation_id, str)
        and observation_id.strip() == observation_id
        and observation_id,
        "OBSERVATION_ID_INVALID",
    )
    canonical_timestamp_ms = _canonical_observation_timestamp_ms()
    if observation_timestamp_ms is not None:
        claim = _positive_int(
            observation_timestamp_ms,
            "CALLER_OBSERVATION_TIMESTAMP_MS_INVALID",
        )
        _require(
            claim == canonical_timestamp_ms,
            "CALLER_OBSERVATION_TIMESTAMP_NOT_AUTHORITY",
        )
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
        return validate_normalized_order_book(
            normalize_order_book_observation(only)
        )
    except LiquidityS1Error as exc:
        raise KrakenFuturesS2Error(
            f"S1_BOOK_REVALIDATION_FAILED:{exc}"
        ) from exc


def _native_quantity_total(book: Mapping[str, Any]) -> str:
    canonical = validate_normalized_order_book(book)
    total = Decimal("0")
    for side in ("bids", "asks"):
        for level in canonical[side]:
            total += _decimal(
                level[1],
                "KRAKEN_FUTURES_NATIVE_QUANTITY_INVALID",
            )
    return format(total, "f")


def build_kraken_futures_liquidity_resource(
    provider_plan: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    *,
    observation_id: str,
    observation_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    plan = validate_kraken_futures_provider_plan(
        provider_plan,
        s1_planner_result,
    )
    s1_plan, _ = _validated_s1_acquisition(s1_planner_result)
    request = _bind_semantic_request_to_s1_plan(
        semantic_request,
        s1_plan,
    )
    book = normalize_kraken_futures_ws_snapshot(
        plan,
        s1_planner_result,
        raw_response,
        observation_id=observation_id,
        observation_timestamp_ms=observation_timestamp_ms,
    )
    provenance = _provider_provenance(plan, raw_response)
    provenance_sha = sha256_canonical_json(provenance)
    capability = _find_contract()["order_book_capability"]
    try:
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
            qualify_liquidity_resource(
                book,
                request,
                quantity_semantics=quantity,
            )
        )
        coverage = compute_side_coverage(book, request)
    except LiquidityS1Error as exc:
        raise KrakenFuturesS2Error(
            f"S1_RESOURCE_QUALIFICATION_FAILED:{exc}"
        ) from exc

    _require(
        resource["truncated"] == coverage["truncated"],
        "KRAKEN_FUTURES_TRUNCATED_STATE_MISMATCH",
    )
    result = {
        "schema_version": S2_RESULT_SCHEMA,
        "provider_plan": dict(plan),
        "provider_plan_sha256": plan["provider_plan_sha256"],
        "provider_id": PROVIDER_ID,
        "instrument_id": plan["instrument_id"],
        "provider_product_id": plan["provider_product_id"],
        "route_id": plan["route_id"],
        "provider_depth_parameter_name": None,
        "provider_requested_level_count": None,
        "provider_normative_max_depth": DEPTH_KNOWLEDGE_STATE,
        "depth_knowledge_state": DEPTH_KNOWLEDGE_STATE,
        "actual_observed_bid_level_count": len(book["bids"]),
        "actual_observed_ask_level_count": len(book["asks"]),
        "provider_limit_exhausted": PROVIDER_LIMIT_STATE,
        "provider_message_integrity": MESSAGE_INTEGRITY_STATE,
        "provider_provenance": provenance,
        "provider_provenance_sha256": provenance_sha,
        "requested_target_bps": plan["requested_target_bps"],
        "achieved_bid_coverage_bps": coverage["achieved_bid_coverage_bps"],
        "achieved_ask_coverage_bps": coverage["achieved_ask_coverage_bps"],
        "coverage_complete_bid": coverage["coverage_complete_bid"],
        "coverage_complete_ask": coverage["coverage_complete_ask"],
        "coverage_complete":
            coverage["coverage_complete_bid"] and coverage["coverage_complete_ask"],
        "truncated": coverage["truncated"],
        "normalized_book": book,
        "quantity_semantics": quantity,
        "qualified_resource": resource,
        "network_execution": NETWORK_EXECUTION_STATE,
    }
    result["result_sha256"] = sha256_canonical_json(result)
    return result


def validate_kraken_futures_liquidity_result(
    result: Mapping[str, Any],
    semantic_request: Mapping[str, Any],
    s1_planner_result: Mapping[str, Any],
) -> dict[str, Any]:
    _require(
        isinstance(result, Mapping),
        "KRAKEN_FUTURES_RESULT_REQUIRED",
    )
    _require(
        set(result) == RESULT_FIELDS,
        "KRAKEN_FUTURES_RESULT_FIELDS_INVALID",
    )
    _require(
        result.get("schema_version") == S2_RESULT_SCHEMA,
        "KRAKEN_FUTURES_RESULT_SCHEMA_INVALID",
    )
    s1_plan, _ = _validated_s1_acquisition(s1_planner_result)
    request = _bind_semantic_request_to_s1_plan(
        semantic_request,
        s1_plan,
    )

    provider_plan = result.get("provider_plan")
    _require(
        isinstance(provider_plan, Mapping),
        "KRAKEN_FUTURES_RESULT_PROVIDER_PLAN_REQUIRED",
    )
    plan = validate_kraken_futures_provider_plan(
        provider_plan,
        s1_planner_result,
    )
    _require(
        result.get("provider_plan_sha256")
        == plan["provider_plan_sha256"],
        "KRAKEN_FUTURES_RESULT_PROVIDER_PLAN_SHA_MISMATCH",
    )
    _require(
        result.get("provider_id") == plan["provider_id"] == PROVIDER_ID,
        "KRAKEN_FUTURES_RESULT_PROVIDER_MISMATCH",
    )
    _require(
        result.get("instrument_id")
        == plan["instrument_id"]
        == request["instrument_id"],
        "KRAKEN_FUTURES_RESULT_INSTRUMENT_MISMATCH",
    )
    _require(
        result.get("provider_product_id")
        == plan["provider_product_id"]
        == _instrument_binding(request["instrument_id"])["ws_product_id"],
        "KRAKEN_FUTURES_RESULT_PRODUCT_ID_MISMATCH",
    )
    _require(
        result.get("route_id") == plan["route_id"] == CANONICAL_ROUTE_ID,
        "KRAKEN_FUTURES_RESULT_ROUTE_INVALID",
    )
    _require(
        result.get("provider_depth_parameter_name") is None
        and plan["provider_depth_parameter_name"] is None,
        "KRAKEN_FUTURES_RESULT_DEPTH_PARAMETER_INVENTED",
    )
    _require(
        result.get("provider_requested_level_count") is None
        and plan["provider_requested_level_count"] is None,
        "KRAKEN_FUTURES_RESULT_LEVEL_COUNT_INVENTED",
    )
    _require(
        result.get("provider_normative_max_depth")
        == plan["provider_normative_max_depth"]
        == DEPTH_KNOWLEDGE_STATE,
        "KRAKEN_FUTURES_RESULT_MAX_DEPTH_INVENTED",
    )
    _require(
        result.get("depth_knowledge_state") == DEPTH_KNOWLEDGE_STATE,
        "KRAKEN_FUTURES_RESULT_DEPTH_KNOWLEDGE_INVALID",
    )
    _require(
        result.get("provider_limit_exhausted") == PROVIDER_LIMIT_STATE,
        "KRAKEN_FUTURES_RESULT_PROVIDER_LIMIT_STATE_INVALID",
    )
    _require(
        result.get("provider_message_integrity") == MESSAGE_INTEGRITY_STATE,
        "KRAKEN_FUTURES_RESULT_INTEGRITY_STATE_INVALID",
    )
    _require(
        result.get("network_execution") == NETWORK_EXECUTION_STATE,
        "KRAKEN_FUTURES_RESULT_S3_BOUNDARY_INVALID",
    )

    provenance = result.get("provider_provenance")
    _require(
        isinstance(provenance, Mapping),
        "KRAKEN_FUTURES_RESULT_PROVENANCE_REQUIRED",
    )
    _require(
        set(provenance)
        == {
            "schema_version",
            "feed",
            "provider_product_id",
            "provider_timestamp_ms",
            "sequence",
            "tick_size",
            "timestamp_role",
            "sequence_role",
            "checksum_semantics",
        },
        "KRAKEN_FUTURES_RESULT_PROVENANCE_FIELDS_INVALID",
    )
    _require(
        provenance.get("schema_version") == PROVENANCE_SCHEMA,
        "KRAKEN_FUTURES_RESULT_PROVENANCE_SCHEMA_INVALID",
    )
    _require(
        provenance.get("feed") == "book_snapshot",
        "KRAKEN_FUTURES_RESULT_PROVENANCE_FEED_INVALID",
    )
    _require(
        provenance.get("provider_product_id") == plan["provider_product_id"],
        "KRAKEN_FUTURES_RESULT_PROVENANCE_PRODUCT_MISMATCH",
    )
    _positive_int(
        provenance.get("provider_timestamp_ms"),
        "KRAKEN_FUTURES_RESULT_PROVIDER_TIMESTAMP_INVALID",
    )
    _positive_int(
        provenance.get("sequence"),
        "KRAKEN_FUTURES_RESULT_SEQUENCE_INVALID",
    )
    _require(
        provenance.get("tick_size") is None,
        "KRAKEN_FUTURES_RESULT_TICK_SIZE_INVALID",
    )
    _require(
        provenance.get("timestamp_role")
        == "PROVIDER_PROVENANCE_NOT_S1_FRESHNESS_AUTHORITY",
        "KRAKEN_FUTURES_RESULT_TIMESTAMP_ROLE_INVALID",
    )
    _require(
        provenance.get("sequence_role")
        == "SUBSCRIPTION_MESSAGE_SEQUENCE_NUMBER_STRUCTURAL_ONLY",
        "KRAKEN_FUTURES_RESULT_SEQUENCE_ROLE_INVALID",
    )
    _require(
        provenance.get("checksum_semantics")
        == "NOT_NORMATIVELY_DOCUMENTED_FOR_CHOSEN_ROUTE",
        "KRAKEN_FUTURES_RESULT_CHECKSUM_OVERCLAIM",
    )
    _require(
        result.get("provider_provenance_sha256")
        == sha256_canonical_json(provenance),
        "KRAKEN_FUTURES_RESULT_PROVENANCE_SHA_MISMATCH",
    )

    try:
        book = validate_normalized_order_book(result.get("normalized_book"))
        quantity = validate_quantity_semantics(result.get("quantity_semantics"))
        resource = validate_qualified_liquidity_resource(
            result.get("qualified_resource")
        )
        coverage = compute_side_coverage(book, request)
    except LiquidityS1Error as exc:
        raise KrakenFuturesS2Error(
            f"S1_RESULT_REVALIDATION_FAILED:{exc}"
        ) from exc

    _require(
        book["provider_id"] == PROVIDER_ID
        and book["instrument_id"] == request["instrument_id"]
        and book["book_kind"] == BOOK_KIND,
        "KRAKEN_FUTURES_RESULT_BOOK_IDENTITY_MISMATCH",
    )
    _require(
        quantity["provider_id"] == PROVIDER_ID
        and quantity["instrument_id"] == request["instrument_id"]
        and quantity["book_kind"] == BOOK_KIND,
        "KRAKEN_FUTURES_RESULT_QUANTITY_IDENTITY_MISMATCH",
    )
    _require(
        quantity["native_quantity"] == _native_quantity_total(book),
        "KRAKEN_FUTURES_RESULT_NATIVE_QUANTITY_NOT_REBOUND_TO_BOOK",
    )
    capability = _find_contract()["order_book_capability"]
    _require(
        quantity["native_quantity_unit"] == capability["native_quantity_unit_id"],
        "KRAKEN_FUTURES_RESULT_NATIVE_QUANTITY_UNIT_MISMATCH",
    )
    _require(
        resource["normalized_book"] == book,
        "KRAKEN_FUTURES_RESULT_RESOURCE_BOOK_MISMATCH",
    )
    _require(
        resource["quantity_semantics"] == quantity,
        "KRAKEN_FUTURES_RESULT_RESOURCE_QUANTITY_MISMATCH",
    )
    _require(
        resource["qualification_request"] == request,
        "KRAKEN_FUTURES_RESULT_REQUEST_REBIND_MISMATCH",
    )
    _require(
        resource["provider_id"] == PROVIDER_ID
        and resource["instrument_id"] == request["instrument_id"]
        and resource["book_kind"] == BOOK_KIND,
        "KRAKEN_FUTURES_RESULT_RESOURCE_IDENTITY_MISMATCH",
    )
    _require(
        result.get("requested_target_bps")
        == request["target_bps"]
        == plan["requested_target_bps"],
        "KRAKEN_FUTURES_RESULT_TARGET_BPS_MISMATCH",
    )
    _require(
        result.get("actual_observed_bid_level_count") == len(book["bids"]),
        "KRAKEN_FUTURES_RESULT_BID_LEVEL_COUNT_MISMATCH",
    )
    _require(
        result.get("actual_observed_ask_level_count") == len(book["asks"]),
        "KRAKEN_FUTURES_RESULT_ASK_LEVEL_COUNT_MISMATCH",
    )
    for field in (
        "achieved_bid_coverage_bps",
        "achieved_ask_coverage_bps",
        "coverage_complete_bid",
        "coverage_complete_ask",
        "truncated",
    ):
        _require(
            result.get(field) == coverage[field] == resource[field],
            f"KRAKEN_FUTURES_RESULT_{field.upper()}_MISMATCH",
        )
    expected_complete = (
        coverage["coverage_complete_bid"]
        and coverage["coverage_complete_ask"]
    )
    _require(
        result.get("coverage_complete") == expected_complete,
        "KRAKEN_FUTURES_RESULT_COVERAGE_COMPLETE_MISMATCH",
    )
    _require(
        not (result.get("truncated") is True and expected_complete),
        "KRAKEN_FUTURES_TRUNCATED_CANNOT_BE_COMPLETE",
    )

    material = dict(result)
    supplied_hash = material.pop("result_sha256", None)
    _require(
        supplied_hash == sha256_canonical_json(material),
        "KRAKEN_FUTURES_RESULT_SHA256_MISMATCH",
    )
    return dict(result)

S3_EXECUTION_DELEGATION = "REQUEST_SCOPED_S3_EXECUTOR_AFTER_S2_REVALIDATION"
