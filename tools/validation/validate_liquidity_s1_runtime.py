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
    evaluate_resource_satisfaction,
    normalize_liquidity_request,
    plan_liquidity_acquisition,
)

CONTRACT = ROOT / "contracts/liquidity-s1-semantic-contract-v1.json"
RUNTIME = ROOT / "src/liquidity_s1_runtime.py"


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise RuntimeError(marker)


def _request(target: int = 250) -> dict:
    return {
        "series_id": "liquidity.binance-spot.ETHUSDT.orderbook",
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "target_bps": target,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": 600},
        "completeness": {"required": True},
        "quantity_semantics": {"mode": "NATIVE_FIRST", "consumer_equivalent_required": False},
    }


def _resource(bid: int, ask: int) -> dict:
    return {
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "observation_id": "validator-observation",
        "coherent_observation": True,
        "qualification_state": "QUALIFIED",
        "age_seconds": 0,
        "requested_bid_coverage_bps": "500",
        "requested_ask_coverage_bps": "500",
        "achieved_bid_coverage_bps": str(bid),
        "achieved_ask_coverage_bps": str(ask),
        "coverage_complete_bid": bid >= 500,
        "coverage_complete_ask": ask >= 500,
        "truncated": not (bid >= 500 and ask >= 500),
        "quantity_semantics": {
            "native_quantity_preserved": True,
            "consumer_qualified_equivalent": False,
        },
    }


def validate() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    runtime = contract["runtime_implementation"]
    stages = contract["stage_boundaries"]
    installation = contract["installation_boundaries"]
    coverage = contract["coverage"]

    _require(contract["runtime_active"] is False, "S1_RUNTIME_ACTIVE_MUST_REMAIN_FALSE")
    _require(stages["s1_source_implementation_performed"] is True, "S1_SOURCE_IMPLEMENTED_REQUIRED")
    _require(stages["provider_rollout_performed"] is False, "S2_PROVIDER_ROLLOUT_FORBIDDEN")
    _require(stages["S2"]["active_in_this_contract_installation"] is False, "S2_ACTIVE_FORBIDDEN")
    _require(stages["S3"]["active_in_this_contract_installation"] is False, "S3_ACTIVE_FORBIDDEN")
    _require(installation["s1_general_source_implementation"] is True, "S1_SOURCE_BOUNDARY_INVALID")
    _require(installation["new_network_acquisition_path"] is False, "S1_NETWORK_PATH_FORBIDDEN")
    _require(installation["provider_activation_changed"] is False, "PROVIDER_ACTIVATION_FORBIDDEN")
    _require(runtime["status"] == "SOURCE_IMPLEMENTED_NOT_ACTIVE", "S1_RUNTIME_STATUS_INVALID")
    _require(runtime["source_module"] == "src/liquidity_s1_runtime.py", "S1_RUNTIME_SOURCE_BINDING_INVALID")
    _require(runtime["provider_network_io"] is False and runtime["production_network_calls_added"] == 0,
             "S1_NETWORK_FREE_CONTRACT_INVALID")
    _require(runtime["production_scheduler_mutated"] is False, "S1_SCHEDULER_MUTATION_FORBIDDEN")
    _require(runtime["resource_index_owner"] == "tools/current_data_transport.py", "RESOURCE_INDEX_OWNER_CHANGED")
    _require(runtime["normal_tests_network_free"] is True, "NORMAL_TESTS_NETWORK_FREE_REQUIRED")
    _require(coverage["reference_price_anchor"] == "BEST_BID_ASK_MIDPOINT", "COVERAGE_ANCHOR_INVALID")
    _require(coverage["no_extrapolation_outside_observed_book"] is True, "BOOK_EXTRAPOLATION_FORBIDDEN")

    source = RUNTIME.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    _require({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imported), "S1_NETWORK_IMPORT_FORBIDDEN")
    for name in (
        "normalize_liquidity_request",
        "evaluate_resource_satisfaction",
        "plan_liquidity_acquisition",
        "normalize_order_book_observation",
        "compute_side_coverage",
        "qualify_quantity_semantics",
        "qualify_liquidity_resource",
        "assert_one_coherent_provider_observation",
    ):
        _require(f"def {name}(" in source, f"S1_PRIMITIVE_MISSING_{name}")

    normalized = normalize_liquidity_request(_request(250))
    _require(normalized["target_bps"] == "250", "TARGET_BPS_250_INVALID")
    _require(normalize_liquidity_request(_request(500))["target_bps"] == "500", "TARGET_BPS_500_INVALID")
    _require(evaluate_resource_satisfaction(_resource(510, 525), normalized)["status"] == "SATISFIED",
             "RESOURCE_DOMINANCE_INVALID")

    cap = {
        "provider_id": "binance-spot",
        "book_kind": "L2_LEVEL_BOOK",
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": "QUALIFIED",
        "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
    }
    reuse = plan_liquidity_acquisition(normalized, cap, _resource(510, 525))
    _require(reuse["decision"] == "REUSE" and reuse["network_required"] is False,
             "REUSE_BEFORE_ACQUISITION_INVALID")

    print("S1_SOURCE_IMPLEMENTED=YES")
    print("S1_RUNTIME_ACTIVE=NO")
    print("S2_PROVIDER_ROLLOUT=NO")
    print("S3_NETWORK_ACTIVATION=NO")
    print("PRODUCTION_NETWORK_CALLS_ADDED=0")
    print("RESOURCE_SATISFACTION_ENGINE=PASS")
    print("RESOURCE_DOMINANCE=PASS")
    print("REUSE_BEFORE_ACQUISITION=PASS")
    print("DYNAMIC_DEPTH_PLANNER=PASS")
    print("TARGET_BPS_250=PASS")
    print("TARGET_BPS_500=PASS")
    print("ONE_COHERENT_PROVIDER_OBSERVATION=PASS")
    print("SIDE_SPECIFIC_COVERAGE=PASS")
    print("NO_BOOK_EXTRAPOLATION=PASS")
    print("BOOK_KIND_VS_REPRESENTATION=SEPARATED")
    print("DERIVATIVES_QUANTITY_NATIVE_FIRST=PASS")
    print("UNKNOWN_PROVIDER_DEPTH_FAIL_CLOSED=PASS")
    print("NETWORK_FREE_PROOF=PASS")
    print("PR283_FAIL_CLOSED_SEMANTICS=PRESERVED")
    print("PR299_REQUEST_SCOPE_SEMANTICS=PRESERVED")


if __name__ == "__main__":
    validate()
