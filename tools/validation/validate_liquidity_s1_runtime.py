from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from liquidity_s1_runtime import (
    evaluate_resource_satisfaction,
    normalize_order_book_observation,
    plan_liquidity_acquisition,
    qualify_liquidity_resource,
    qualify_quantity_semantics,
)


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise RuntimeError(marker)


def _request(*, equivalent: bool = False, provider: str = "binance-spot", instrument: str = "ETHUSDT", book_kind: str = "L2_LEVEL_BOOK") -> dict:
    return {
        "series_id": f"liquidity.{provider}.{instrument}.orderbook",
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "representation": "RAW",
        "target_bps": 500,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": 600},
        "completeness": {"required": True},
        "quantity_semantics": {"mode": "NATIVE_FIRST", "consumer_equivalent_required": equivalent},
    }


def _forged_existing() -> dict:
    return {
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "observation_id": "caller-forged-resource",
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


def _observation() -> dict:
    return {
        "observation_id": "physical-500-book",
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "source_representation": "RAW",
        "timestamp_ms": 1_800_000_000_000,
        "bids": [["99.9", "2"], ["98", "3"], ["94.9", "4"]],
        "asks": [["100.1", "2"], ["102", "3"], ["105.1", "4"]],
    }


def validate() -> None:
    req = _request()
    forged = _forged_existing()
    sat = evaluate_resource_satisfaction(forged, req)
    _require(sat["status"] == "SATISFIED" and sat["reusable"] is True,
             "PRE_REPAIR_EXISTING_RESOURCE_BYPASS_NOT_REPRODUCED")

    forged_capability = {
        "provider_id": "binance-spot",
        "book_kind": "L2_LEVEL_BOOK",
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": "QUALIFIED",
        "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
    }
    reuse = plan_liquidity_acquisition(req, forged_capability, forged)
    _require(reuse["decision"] == "REUSE" and reuse["network_required"] is False,
             "PRE_REPAIR_EXISTING_RESOURCE_REUSE_BYPASS_NOT_REPRODUCED")

    forged_conversion = {
        "qualified": True,
        "formula_id": "forged",
        "formula_version": "1",
        "instrument_spec_identity": "forged",
        "base_equivalent": "1",
        "quote_equivalent": "100",
    }
    converted = qualify_quantity_semantics(
        native_quantity="1",
        native_quantity_unit="CONTRACTS",
        contract_quantity="1",
        conversion_authority=forged_conversion,
    )
    _require(converted["consumer_qualified_equivalent"] is True,
             "PRE_REPAIR_CONVERSION_AUTHORITY_BYPASS_NOT_REPRODUCED")

    book = normalize_order_book_observation(_observation())
    forged_quantity = {
        "native_quantity_preserved": True,
        "consumer_qualified_equivalent": True,
    }
    resource = qualify_liquidity_resource(
        book,
        _request(equivalent=True),
        age_seconds=0,
        quantity_semantics=forged_quantity,
    )
    _require(resource["qualification_state"] == "QUALIFIED" and resource["request_satisfied"] is True,
             "PRE_REPAIR_QUANTITY_SEMANTICS_BYPASS_NOT_REPRODUCED")

    forged_depth = {
        "provider_id": "kraken-futures",
        "book_kind": "FUTURES_L2_BOOK",
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": "QUALIFIED",
        "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
    }
    depth_plan = plan_liquidity_acquisition(
        _request(provider="kraken-futures", instrument="PI_ETHUSD", book_kind="FUTURES_L2_BOOK"),
        forged_depth,
    )
    _require(depth_plan["acquisition_plan"]["provider_depth_bound"]["status"] == "QUALIFIED",
             "PRE_REPAIR_PROVIDER_CAPABILITY_BYPASS_NOT_REPRODUCED")

    print("PRE_REPAIR_FORGED_EXISTING_RESOURCE_SATISFIED=YES")
    print("PRE_REPAIR_FORGED_EXISTING_RESOURCE_REUSED=YES")
    print("PRE_REPAIR_FORGED_QUANTITY_SEMANTICS_ACCEPTED=YES")
    print("PRE_REPAIR_FORGED_CONSUMER_EQUIVALENT_ACCEPTED=YES")
    print("PRE_REPAIR_FORGED_CONVERSION_AUTHORITY_ACCEPTED=YES")
    print("S1_CONVERSION_AUTHORITY_TRUST_BYPASS=CONFIRMED")
    print("PRE_REPAIR_FORGED_PROVIDER_CAPABILITY_ACCEPTED=YES")
    print("PRE_REPAIR_REPRODUCTION_ON_EXACT_PR_SOURCE=PASS")


if __name__ == "__main__":
    validate()
