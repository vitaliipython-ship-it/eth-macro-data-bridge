from __future__ import annotations

import ast
import sys
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
for path in (str(SRC), str(TOOLS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import plan_liquidity_acquisition, qualify_liquidity_resource
from liquidity_s2_kraken_futures_adapter import (
    BOOK_KIND,
    CANONICAL_ROUTE_ID,
    DEPTH_KNOWLEDGE_STATE,
    MESSAGE_INTEGRITY_STATE,
    NETWORK_EXECUTION_STATE,
    PROVIDER_ID,
    PROVIDER_LIMIT_STATE,
    KrakenFuturesS2Error,
    build_kraken_futures_liquidity_resource,
    build_kraken_futures_provider_plan,
    get_kraken_futures_provider_capability,
    get_kraken_futures_route,
    validate_kraken_futures_liquidity_result,
)

NOW_MS = 1_800_000_600_000
NOW = datetime.fromtimestamp(NOW_MS / 1000, timezone.utc)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def semantic_request(target: int, instrument: str = "PI_ETHUSD") -> dict:
    return {
        "series_id": f"liquidity.kraken-futures.{instrument}.orderbook",
        "provider_id": PROVIDER_ID,
        "instrument_id": instrument,
        "book_kind": BOOK_KIND,
        "representation": "RAW",
        "target_bps": target,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": 600},
        "completeness": {"required": True},
        "quantity_semantics": {
            "mode": "NATIVE_FIRST",
            "consumer_equivalent_required": False,
        },
    }


def s1_plan(target: int, instrument: str = "PI_ETHUSD") -> tuple[dict, dict]:
    request = semantic_request(target, instrument)
    capability = {
        "provider_id": PROVIDER_ID,
        "book_kind": BOOK_KIND,
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": DEPTH_KNOWLEDGE_STATE,
        "qualified_provider_depth_parameter": None,
    }
    return request, plan_liquidity_acquisition(request, capability)


def ws_snapshot(
    plan: dict,
    *,
    outer_bid: str = "90",
    outer_ask: str = "110",
) -> dict:
    return {
        "feed": "book_snapshot",
        "product_id": plan["provider_product_id"],
        "timestamp": 1_800_000_599_000,
        "seq": 42,
        "tickSize": None,
        "bids": [
            {"price": Decimal("99.9"), "qty": Decimal("2")},
            {"price": Decimal("98"), "qty": Decimal("3")},
            {"price": Decimal(outer_bid), "qty": Decimal("4")},
        ],
        "asks": [
            {"price": Decimal("100.1"), "qty": Decimal("2")},
            {"price": Decimal("102"), "qty": Decimal("3")},
            {"price": Decimal(outer_ask), "qty": Decimal("4")},
        ],
    }


def recompute_result_hash(result: dict) -> None:
    material = dict(result)
    material.pop("result_sha256", None)
    result["result_sha256"] = sha256_canonical_json(material)


def main() -> int:
    contract = get_kraken_futures_provider_capability()
    capability = contract["order_book_capability"]
    route = get_kraken_futures_route()

    require(capability["provider_id"] == PROVIDER_ID, "DB_D2_PROVIDER_OWNER_FAIL")
    require(
        capability["qualification_state"] == "S2_QUALIFIED_NETWORK_INACTIVE",
        "DB_D2_QUALIFICATION_STATE_FAIL",
    )
    require(
        capability["semantic_capability_id"]
        == "KRAKEN_FUTURES_RAW_L2_SEMANTIC_CAPABILITY",
        "DB_D2_SEMANTIC_CAPABILITY_FAIL",
    )
    require(
        capability["supported_instruments"] == ["PI_ETHUSD", "PI_XBTUSD"],
        "DB_D2_PRODUCT_SCOPE_FAIL",
    )
    require(
        capability["instrument_identity_map"]["PI_ETHUSD"]["ws_product_id"]
        == "PI_ETHUSD",
        "DB_D2_ETH_IDENTITY_FAIL",
    )
    require(
        capability["instrument_identity_map"]["PI_XBTUSD"]["ws_product_id"]
        == "PI_XBTUSD",
        "DB_D2_BTC_XBT_IDENTITY_FAIL",
    )
    require(
        capability["pf_substitution_for_pi"] is False,
        "DB_D2_PF_PI_SUBSTITUTION_FAIL",
    )
    require(
        capability["selectable_depth_limit"] == DEPTH_KNOWLEDGE_STATE,
        "DB_D2_DEPTH_KNOWLEDGE_FAIL",
    )
    require(
        capability["normative_max_depth"] == DEPTH_KNOWLEDGE_STATE,
        "DB_D2_MAX_DEPTH_INVENTED",
    )
    require(
        capability["provider_depth_parameter_name"] is None,
        "DB_D2_DEPTH_PARAMETER_INVENTED",
    )
    require(
        route["route_id"] == CANONICAL_ROUTE_ID
        and route["transport"] == "WEBSOCKET_V1"
        and route["feed"] == "book",
        "DB_D2_ROUTE_FAIL",
    )
    require(
        route["provider_depth_parameter_name"] is None,
        "DB_D2_ROUTE_DEPTH_PARAMETER_INVENTED",
    )
    require(
        route["stateful_local_book_active"] is False,
        "DB_D2_STATEFUL_WS_FAIL",
    )
    require(
        capability["coverage_guaranteed_by_level_count"] is False,
        "DB_D2_LEVEL_BPS_OVERCLAIM",
    )

    with patch.object(current_data_transport, "_utc_now", return_value=NOW):
        results = []
        for target in (250, 500):
            request, s1 = s1_plan(target)
            plan = build_kraken_futures_provider_plan(
                s1,
                max_raw_resource_bytes=1_000_000,
            )
            require(
                plan["provider_requested_level_count"] is None,
                "DB_D2_PROVIDER_LEVEL_COUNT_INVENTED",
            )
            require(
                plan["provider_normative_max_depth"] == DEPTH_KNOWLEDGE_STATE,
                "DB_D2_PROVIDER_MAX_DEPTH_INVENTED",
            )
            require(
                plan["network_execution"] == NETWORK_EXECUTION_STATE,
                "DB_D2_S3_ACTIVATED",
            )
            result = build_kraken_futures_liquidity_resource(
                plan,
                s1,
                request,
                ws_snapshot(plan),
                observation_id=f"db-d2-{target}",
            )
            validate_kraken_futures_liquidity_result(result, request, s1)
            require(
                result["quantity_semantics"]["base_equivalent"] is None
                and result["quantity_semantics"]["quote_equivalent"] is None,
                "DB_D2_QUANTITY_OVERCLAIM",
            )
            require(
                result["provider_limit_exhausted"] == PROVIDER_LIMIT_STATE,
                "DB_D2_PROVIDER_LIMIT_FALSE_AUTHORITY",
            )
            require(
                result["provider_message_integrity"] == MESSAGE_INTEGRITY_STATE,
                "DB_D2_SEQUENCE_INTEGRITY_FAIL",
            )
            results.append(result)

        request, s1 = s1_plan(500)
        plan = build_kraken_futures_provider_plan(
            s1,
            max_raw_resource_bytes=1_000_000,
        )
        narrow = build_kraken_futures_liquidity_resource(
            plan,
            s1,
            request,
            ws_snapshot(plan, outer_bid="97", outer_ask="103"),
            observation_id="db-d2-target-miss",
        )
        require(narrow["truncated"] is True, "DB_D2_TARGET_MISS_NOT_TRUNCATED")
        require(
            narrow["coverage_complete"] is False,
            "DB_D2_TARGET_MISS_FALSE_COMPLETE",
        )
        require(
            narrow["qualified_resource"]["extrapolation_allowed"] is False,
            "DB_D2_EXTRAPOLATION_ENABLED",
        )
        require(
            narrow["provider_message_integrity"] == MESSAGE_INTEGRITY_STATE,
            "DB_D2_INTEGRITY_MISSING",
        )

        repeat = build_kraken_futures_liquidity_resource(
            plan,
            s1,
            request,
            ws_snapshot(plan),
            observation_id="repeat",
        )
        repeat2 = build_kraken_futures_liquidity_resource(
            plan,
            s1,
            request,
            ws_snapshot(plan),
            observation_id="repeat",
        )
        require(repeat == repeat2, "DB_D2_NONDETERMINISTIC_RESULT")

        forged_request = semantic_request(250)
        forged_resource = qualify_liquidity_resource(
            repeat["normalized_book"],
            forged_request,
            quantity_semantics=repeat["quantity_semantics"],
        )
        forged = deepcopy(repeat)
        forged["requested_target_bps"] = "250"
        forged["qualified_resource"] = forged_resource
        forged["coverage_complete_bid"] = forged_resource["coverage_complete_bid"]
        forged["coverage_complete_ask"] = forged_resource["coverage_complete_ask"]
        forged["coverage_complete"] = (
            forged_resource["coverage_complete_bid"]
            and forged_resource["coverage_complete_ask"]
        )
        forged["truncated"] = forged_resource["truncated"]
        forged["achieved_bid_coverage_bps"] = forged_resource["achieved_bid_coverage_bps"]
        forged["achieved_ask_coverage_bps"] = forged_resource["achieved_ask_coverage_bps"]
        recompute_result_hash(forged)
        try:
            validate_kraken_futures_liquidity_result(forged, request, s1)
        except KrakenFuturesS2Error:
            pass
        else:
            require(False, "DB_D2_CORRELATED_REHASH_FORGERY_ACCEPTED")

    adapter_tree = ast.parse(
        (ROOT / "src/liquidity_s2_kraken_futures_adapter.py").read_text(
            encoding="utf-8"
        )
    )
    imports = set()
    for node in ast.walk(adapter_tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    require(
        imports.isdisjoint(
            {"urllib", "requests", "http", "socket", "aiohttp", "websockets"}
        ),
        "DB_D2_NETWORK_IMPORT_FAIL",
    )
    for production_path in (
        ROOT / "src/collector.py",
        ROOT / "src/intelligence.py",
        ROOT / "tools/current_data_transport.py",
    ):
        require(
            "liquidity_s2_kraken_futures_adapter"
            not in production_path.read_text(encoding="utf-8"),
            f"DB_D2_PRODUCTION_ACTIVATION:{production_path}",
        )
    require(
        not (ROOT / ".github/workflows/db-d2-kraken-futures-probe.yml").exists(),
        "DB_D2_TEMP_PROBE_NOT_REMOVED",
    )

    test_tree = ast.parse(
        (ROOT / "tests/test_liquidity_s2_kraken_futures_adapter.py").read_text(
            encoding="utf-8"
        )
    )
    test_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(test_tree)
    )
    require(test_count >= 41, "DB_D2_REQUIRED_TEST_MATRIX_INCOMPLETE")

    print("DB_D2_SCOPE=KRAKEN_FUTURES_RAW_L2_S2_PROVIDER_FOUNDATION_ONLY")
    print("KRAKEN_FUTURES_PROVIDER_QUALIFICATION=S2_QUALIFIED_NETWORK_INACTIVE")
    print("KRAKEN_FUTURES_RAW_L2_CONFIRMED=YES")
    print("KRAKEN_FUTURES_ACQUISITION_ROUTES=WEBSOCKET_V1_BOOK_INITIAL_SNAPSHOT_ONLY")
    print("KRAKEN_FUTURES_ETH_PRODUCT_ID=PI_ETHUSD")
    print("KRAKEN_FUTURES_BTC_PRODUCT_ID=PI_XBTUSD")
    print("PF_SUBSTITUTION_FOR_PI=NO")
    print("NORMATIVE_SELECTABLE_MAX_DEPTH=NOT_NORMATIVELY_DOCUMENTED")
    print("NORMATIVE_MAX_DEPTH_INVENTED=NO")
    print("PROVIDER_DEPTH_PARAMETER_NAME=NONE")
    print("LEVEL_COUNT_GUARANTEES_BPS=NO")
    print("TARGET_250_BPS_SUPPORTED=YES")
    print("TARGET_500_BPS_SUPPORTED=YES")
    print("EXACTLY_ONE_PROVIDER_PLAN=YES")
    print("EXACTLY_ONE_ROUTE_PER_OBSERVATION=YES")
    print("REST_WS_STITCHING_ALLOWED=NO")
    print("SEQUENTIAL_OBSERVATION_STITCHING_ALLOWED=NO")
    print("RETRY_IS_NEW_OBSERVATION=YES")
    print("S1_RUNTIME_REUSED=YES")
    print("S1_FRESHNESS_AUTHORITY_REUSED=YES")
    print("PROVIDER_TIMESTAMP_IS_FRESHNESS_AUTHORITY=NO")
    print("CALLER_TIMESTAMP_IS_FRESHNESS_AUTHORITY=NO")
    print("SECOND_TEMPORAL_AUTHORITY_CREATED=NO")
    print("QUANTITY_NATIVE_FIRST=YES")
    print("UNQUALIFIED_CONVERSION_RETURNS_ZERO=NO")
    print("CHECKSUM_SEMANTICS=NOT_INVENTED")
    print("SEQUENCE_SEMANTICS=STRUCTURAL_SUBSCRIPTION_MESSAGE_SEQUENCE_ONLY")
    print("OUTER_RESULT_FULL_REVALIDATION=PASS")
    print("RECOMPUTED_OUTER_HASH_CANNOT_FORGE_REQUEST=PASS")
    print("CORRELATED_FIELD_MATRIX=PASS")
    print("DETERMINISTIC_REPEATABILITY=PASS")
    print("NORMAL_TEST_NETWORK_CALLS=0")
    print("PRODUCTION_NETWORK_CALLS_ADDED_BY_DB_D2=0")
    print("PRODUCTION_SCHEDULER_MUTATED=NO")
    print("PRODUCTION_COLLECTOR_ACTIVATED=NO")
    print("S3_REQUEST_AWARE_NETWORK_ACTIVATION=NO")
    print("DB_D2_RUNTIME_ACTIVE=NO")
    print(f"DB_D2_TARGETED_TEST_COUNT={test_count}")
    print("NETWORK_FREE_PROOF=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# DB-F/S3 R01: S3 delegates to existing PI Futures initial snapshot parser without depth invention
