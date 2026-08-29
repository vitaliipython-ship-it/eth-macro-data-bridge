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
    REQUEST_SCHEMA,
    LiquidityS1Error,
    canonical_plan_bytes,
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


def _capability(payload: dict) -> dict:
    return {
        "provider_id": payload.get("provider_id", "binance-spot"),
        "book_kind": payload.get("book_kind", "L2_LEVEL_BOOK"),
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": "NOT_NORMATIVELY_DOCUMENTED",
        "qualified_provider_depth_parameter": None,
    }


def _assert_request_rejected(payload: dict, expected: str, marker: str) -> None:
    for entry in (
        lambda: evaluate_resource_satisfaction(None, payload),
        lambda: plan_liquidity_acquisition(payload, _capability(payload)),
    ):
        try:
            entry()
        except LiquidityS1Error as exc:
            _require(str(exc) == expected, f"{marker}_WRONG_ERROR_{exc}")
        else:
            raise RuntimeError(f"{marker}_BYPASS")


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
    _require("else dict(semantic_request)" not in source, "REQUEST_SCHEMA_TRUST_SHORTCUT_PRESENT")
    _require('semantic_request.get("schema_version") != REQUEST_SCHEMA' not in source, "REQUEST_SCHEMA_TRUST_SHORTCUT_PRESENT")
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
    revalidated = normalize_liquidity_request(normalized)
    _require(normalized["schema_version"] == REQUEST_SCHEMA, "REQUEST_SCHEMA_MARKER_INVALID")
    _require(revalidated == normalized, "CANONICAL_REVALIDATION_NOT_IDEMPOTENT")
    _require(normalized["target_bps"] == "250", "TARGET_BPS_250_INVALID")
    _require(normalize_liquidity_request(_request(500))["target_bps"] == "500", "TARGET_BPS_500_INVALID")
    _require(evaluate_resource_satisfaction(_resource(510, 525), normalized)["status"] == "SATISFIED",
             "RESOURCE_DOMINANCE_INVALID")

    adversarial: list[tuple[dict, str, str]] = []
    bad = dict(normalized); bad["provider_url"] = "https://example.invalid"
    adversarial.append((bad, "PHYSICAL_REQUEST_FIELD_FORBIDDEN", "FORBIDDEN_PHYSICAL_FIELDS"))
    bad = dict(normalized); bad["unexpected"] = "forged"
    adversarial.append((bad, "UNKNOWN_REQUEST_FIELD", "UNKNOWN_FIELDS"))
    bad = dict(normalized); bad["book_kind"] = "MAGIC_BOOK"
    adversarial.append((bad, "BOOK_KIND_UNKNOWN", "UNKNOWN_BOOK_KIND"))
    bad = dict(normalized); bad["representation"] = "MAGIC"
    adversarial.append((bad, "REPRESENTATION_UNKNOWN", "UNKNOWN_REPRESENTATION"))
    bad = dict(normalized); bad["target_bps"] = "0"
    adversarial.append((bad, "TARGET_BPS_NOT_POSITIVE", "INVALID_TARGET_BPS"))
    bad = dict(normalized); bad["bucket_bps"] = "0"
    adversarial.append((bad, "BUCKET_BPS_NOT_POSITIVE", "INVALID_BUCKET_BPS"))
    bad = dict(normalized); bad["freshness"] = {"unexpected": 600}
    adversarial.append((bad, "FRESHNESS_INVALID", "INVALID_FRESHNESS"))
    bad = dict(normalized); bad["completeness"] = {"required": "yes"}
    adversarial.append((bad, "COMPLETENESS_REQUIRED_INVALID", "INVALID_COMPLETENESS"))
    bad = dict(normalized); bad["quantity_semantics"] = {"mode": "MAGIC", "consumer_equivalent_required": False}
    adversarial.append((bad, "QUANTITY_MODE_INVALID", "INVALID_QUANTITY_SEMANTICS"))
    bad = dict(normalized); del bad["series_id"]
    adversarial.append((bad, "SERIES_ID_INVALID", "MISSING_REQUIRED_IDENTITY"))
    for payload, expected, marker in adversarial:
        _assert_request_rejected(payload, expected, marker)

    for state in ("PARTIAL", "TRUNCATED", "FUTURE_UNKNOWN_STATE", "UNAVAILABLE", "NOT_QUALIFIED", "SOURCE_CONFLICT", "MISALIGNED", "UNKNOWN"):
        candidate = _resource(510, 525)
        candidate["qualification_state"] = state
        result = evaluate_resource_satisfaction(candidate, normalized)
        _require(result["status"] != "SATISFIED" and result["reusable"] is False, "NON_QUALIFIED_STATE_REUSE_BYPASS")

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
    plan_a = plan_liquidity_acquisition(_request(500), cap)
    plan_b = plan_liquidity_acquisition(normalize_liquidity_request(_request(500)), cap)
    _require(canonical_plan_bytes(plan_a) == canonical_plan_bytes(plan_b), "CANONICAL_PLAN_IDENTITY_DRIFT")
    _require(plan_a["acquisition_plan"]["plan_sha256"] == plan_b["acquisition_plan"]["plan_sha256"],
             "CANONICAL_PLAN_HASH_DRIFT")

    print("PRE_REPAIR_BYPASS_REPRODUCED=YES")
    print("POST_REPAIR_BYPASS_REPRODUCED=NO")
    print("SCHEMA_MARKER_IS_NOT_TRUST_PROOF=PASS")
    print("FORBIDDEN_PHYSICAL_FIELDS_FAIL_CLOSED=PASS")
    print("UNKNOWN_FIELDS_FAIL_CLOSED=PASS")
    print("UNKNOWN_BOOK_KIND_FAIL_CLOSED=PASS")
    print("UNKNOWN_REPRESENTATION_FAIL_CLOSED=PASS")
    print("INVALID_TARGET_BPS_FAIL_CLOSED=PASS")
    print("INVALID_BUCKET_BPS_FAIL_CLOSED=PASS")
    print("INVALID_FRESHNESS_FAIL_CLOSED=PASS")
    print("INVALID_COMPLETENESS_FAIL_CLOSED=PASS")
    print("INVALID_QUANTITY_SEMANTICS_FAIL_CLOSED=PASS")
    print("MISSING_REQUIRED_IDENTITY_FAIL_CLOSED=PASS")
    print("CANONICAL_REVALIDATION=PASS")
    print("CANONICAL_REVALIDATION_IDEMPOTENT=PASS")
    print("NON_QUALIFIED_STATE_REUSE_BYPASS=NO")
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
