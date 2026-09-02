from __future__ import annotations

import ast
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import evaluate_resource_satisfaction, plan_liquidity_acquisition
from liquidity_s2_binance_adapter import (
    MAX_RAW_RESOURCE_BYTES_HARD_CAP,
    MAX_REST_LEVELS_PER_SIDE_HARD_ARCHITECTURAL_CAP,
    BinanceS2Error,
    build_binance_liquidity_resource,
    build_binance_provider_plan,
    get_binance_provider_capability,
    normalize_binance_order_book_response,
    validate_binance_liquidity_result,
    validate_binance_provider_plan,
)

ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1_800_000_600_000
NOW = datetime.fromtimestamp(NOW_MS / 1000, timezone.utc)


def request(target=500, *, provider="binance-spot", instrument="ETHUSDT", equivalent=False):
    book_kind = "L2_LEVEL_BOOK" if provider == "binance-spot" else "FUTURES_L2_BOOK"
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


def s1_capability(provider="binance-spot"):
    return {
        "provider_id": provider,
        "book_kind": "L2_LEVEL_BOOK" if provider == "binance-spot" else "FUTURES_L2_BOOK",
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": "NOT_QUALIFIED",
        "qualified_provider_depth_parameter": None,
    }


def s1_plan(target=500, *, provider="binance-spot", instrument="ETHUSDT", equivalent=False):
    req = request(target, provider=provider, instrument=instrument, equivalent=equivalent)
    return req, plan_liquidity_acquisition(req, s1_capability(provider))


def provider_plan(target=500, *, provider="binance-spot", instrument="ETHUSDT", max_bytes=1_000_000):
    req, plan = s1_plan(target, provider=provider, instrument=instrument)
    budget = 250 if provider == "binance-spot" else 20
    return req, plan, build_binance_provider_plan(
        plan,
        request_weight_budget=budget,
        max_raw_resource_bytes=max_bytes,
    )


def raw_book(*, provider="binance-spot", bid_outer="95", ask_outer="105"):
    payload = {
        "lastUpdateId": 123456,
        "bids": [["99.9", "2"], ["98", "3"], [bid_outer, "4"]],
        "asks": [["100.1", "2"], ["102", "3"], [ask_outer, "4"]],
    }
    if provider == "binance-usdm":
        payload["E"] = NOW_MS
        payload["T"] = NOW_MS
    return payload


class BinanceS2AdapterTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(current_data_transport, "_utc_now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def test_001_spot_target_250_maps_only_to_s2_qualified_depth(self):
        _, _, plan = provider_plan(250)
        self.assertEqual(plan["provider_requested_level_count"], 5000)
        self.assertEqual(plan["provider_normative_max_depth"], 5000)
        self.assertEqual(plan["request_weight"], 250)
        self.assertFalse(plan["coverage_guaranteed_by_level_count"])

    def test_002_spot_target_500_maps_only_to_s2_qualified_depth(self):
        _, _, plan = provider_plan(500)
        self.assertEqual(plan["provider_requested_level_count"], 5000)
        self.assertEqual(plan["endpoint_path"], "/api/v3/depth")
        self.assertEqual(plan["canonical_base_host"], "https://data-api.binance.vision")

    def test_003_usdm_target_250_uses_independently_qualified_max(self):
        _, _, plan = provider_plan(250, provider="binance-usdm")
        self.assertEqual(plan["provider_requested_level_count"], 1000)
        self.assertEqual(plan["request_weight"], 20)
        self.assertEqual(plan["endpoint_path"], "/fapi/v1/depth")

    def test_004_usdm_target_500_uses_independently_qualified_max(self):
        _, _, plan = provider_plan(500, provider="binance-usdm")
        self.assertEqual(plan["provider_requested_level_count"], 1000)
        self.assertNotEqual(plan["provider_requested_level_count"], 5000)

    def test_005_unsupported_or_caller_forged_physical_depth_cannot_be_emitted(self):
        _, s1, plan = provider_plan(500)
        forged = dict(plan)
        forged["provider_requested_level_count"] = 4999
        material = dict(forged)
        material.pop("provider_plan_sha256")
        forged["provider_plan_sha256"] = sha256_canonical_json(material)
        with self.assertRaisesRegex(BinanceS2Error, "PROVIDER_PLAN_REVALIDATION_MISMATCH"):
            validate_binance_provider_plan(forged, s1)

    def test_006_provider_maximum_is_contract_owned_not_caller_authored(self):
        spot = get_binance_provider_capability("binance-spot")["order_book_capability"]
        usdm = get_binance_provider_capability("binance-usdm")["order_book_capability"]
        self.assertEqual(spot["normative_max_depth"], 5000)
        self.assertEqual(usdm["normative_max_depth"], 1000)
        self.assertLessEqual(spot["normative_max_depth"], MAX_REST_LEVELS_PER_SIDE_HARD_ARCHITECTURAL_CAP)
        self.assertLessEqual(usdm["normative_max_depth"], MAX_REST_LEVELS_PER_SIDE_HARD_ARCHITECTURAL_CAP)

    def test_007_spot_limits_are_not_reused_for_usdm(self):
        spot = get_binance_provider_capability("binance-spot")["order_book_capability"]
        usdm = get_binance_provider_capability("binance-usdm")["order_book_capability"]
        self.assertEqual(spot["supported_depth_values"]["mode"], "INTEGER_RANGE")
        self.assertEqual(usdm["supported_depth_values"]["mode"], "EXACT_SET")
        self.assertNotEqual(spot["request_weight_by_depth"], usdm["request_weight_by_depth"])

    def test_008_usdm_limits_are_not_reused_for_spot(self):
        _, _, spot_plan = provider_plan(500)
        _, _, usdm_plan = provider_plan(500, provider="binance-usdm")
        self.assertEqual(spot_plan["provider_product"], "Spot Order Book")
        self.assertEqual(usdm_plan["provider_product"], "USDⓈ-M Futures")
        self.assertNotEqual(spot_plan["endpoint_path"], usdm_plan["endpoint_path"])

    def test_009_request_weight_budget_is_enforced(self):
        _, s1 = s1_plan(500)
        with self.assertRaisesRegex(BinanceS2Error, "REQUEST_WEIGHT_BUDGET_INSUFFICIENT"):
            build_binance_provider_plan(s1, request_weight_budget=249, max_raw_resource_bytes=1_000_000)
        _, usdm = s1_plan(500, provider="binance-usdm")
        with self.assertRaisesRegex(BinanceS2Error, "REQUEST_WEIGHT_BUDGET_INSUFFICIENT"):
            build_binance_provider_plan(usdm, request_weight_budget=19, max_raw_resource_bytes=1_000_000)

    def test_010_raw_resource_hard_bound_is_enforced_at_plan_time(self):
        _, s1 = s1_plan(500)
        with self.assertRaisesRegex(BinanceS2Error, "MAX_RAW_RESOURCE_BYTES_EXCEEDS_HARD_CAP"):
            build_binance_provider_plan(
                s1,
                request_weight_budget=250,
                max_raw_resource_bytes=MAX_RAW_RESOURCE_BYTES_HARD_CAP + 1,
            )

    def test_011_raw_resource_bytes_are_enforced_on_response(self):
        req, s1, plan = provider_plan(500, max_bytes=30)
        with self.assertRaisesRegex(BinanceS2Error, "BINANCE_RAW_RESOURCE_BYTES_EXCEEDED"):
            normalize_binance_order_book_response(
                plan, s1, raw_book(), observation_id="one", observation_timestamp_ms=NOW_MS
            )
        self.assertEqual(req["provider_id"], "binance-spot")

    def test_012_one_rest_response_creates_one_observation(self):
        _, s1, plan = provider_plan(500)
        book = normalize_binance_order_book_response(
            plan, s1, raw_book(), observation_id="one", observation_timestamp_ms=NOW_MS
        )
        self.assertEqual(book["observation_id"], "one")
        self.assertEqual(book["provider_id"], "binance-spot")

    def test_013_two_sequential_responses_cannot_be_stitched(self):
        _, s1, plan = provider_plan(500)
        with self.assertRaisesRegex(BinanceS2Error, "ONE_BINANCE_REST_RESPONSE_MAPPING_REQUIRED"):
            normalize_binance_order_book_response(
                plan,
                s1,
                [raw_book(), raw_book()],
                observation_id="forbidden",
                observation_timestamp_ms=NOW_MS,
            )

    def test_014_provider_max_reached_but_coverage_insufficient_is_truncated(self):
        req, s1, plan = provider_plan(500)
        result = build_binance_liquidity_resource(
            plan,
            s1,
            req,
            raw_book(bid_outer="97.7", ask_outer="104.1"),
            observation_id="truncated",
            observation_timestamp_ms=NOW_MS,
        )
        self.assertTrue(result["provider_limit_exhausted"])
        self.assertTrue(result["truncated"])
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["achieved_bid_coverage_bps"], "230")
        self.assertEqual(result["achieved_ask_coverage_bps"], "410")

    def test_015_truncated_cannot_become_complete(self):
        req, s1, plan = provider_plan(500)
        result = build_binance_liquidity_resource(
            plan, s1, req, raw_book(bid_outer="97.7", ask_outer="104.1"),
            observation_id="truncated", observation_timestamp_ms=NOW_MS,
        )
        forged = dict(result)
        forged["coverage_complete"] = True
        material = dict(forged)
        material.pop("result_sha256")
        forged["result_sha256"] = sha256_canonical_json(material)
        with self.assertRaisesRegex(BinanceS2Error, "COVERAGE_COMPLETE_MISMATCH|TRUNCATED_CANNOT_BE_COMPLETE"):
            validate_binance_liquidity_result(forged)

    def test_016_provider_claimed_coverage_cannot_bypass_s1_recomputation(self):
        _, s1, plan = provider_plan(500)
        forged = raw_book(bid_outer="97.7", ask_outer="104.1")
        forged["achieved_bid_coverage_bps"] = "500"
        forged["coverage_complete"] = True
        with self.assertRaisesRegex(BinanceS2Error, "BINANCE_RESPONSE_FIELDS_INVALID"):
            normalize_binance_order_book_response(
                plan, s1, forged, observation_id="forged", observation_timestamp_ms=NOW_MS
            )

    def test_017_unsorted_provider_levels_fail_closed_in_s1(self):
        _, s1, plan = provider_plan(500)
        payload = raw_book()
        payload["bids"][0], payload["bids"][1] = payload["bids"][1], payload["bids"][0]
        with self.assertRaisesRegex(BinanceS2Error, "S1_BOOK_REVALIDATION_FAILED:BID_UNSORTED"):
            normalize_binance_order_book_response(
                plan, s1, payload, observation_id="unsorted", observation_timestamp_ms=NOW_MS
            )

    def test_018_crossed_provider_levels_fail_closed_in_s1(self):
        _, s1, plan = provider_plan(500)
        payload = raw_book()
        payload["bids"][0][0] = "101"
        with self.assertRaisesRegex(BinanceS2Error, "S1_BOOK_REVALIDATION_FAILED:CROSSED_OR_LOCKED_BOOK"):
            normalize_binance_order_book_response(
                plan, s1, payload, observation_id="crossed", observation_timestamp_ms=NOW_MS
            )

    def test_019_wrong_semantic_instrument_identity_fails_closed(self):
        req, s1, plan = provider_plan(500, instrument="ETHUSDT")
        wrong = request(500, instrument="BTCUSDT")
        with self.assertRaisesRegex(BinanceS2Error, "S1_REQUEST_PLAN_BINDING_MISMATCH:instrument_id"):
            build_binance_liquidity_resource(
                plan, s1, wrong, raw_book(), observation_id="wrong", observation_timestamp_ms=NOW_MS
            )
        self.assertEqual(req["instrument_id"], "ETHUSDT")

    def test_020_unknown_consumer_quantity_equivalence_remains_fail_closed(self):
        req, s1 = s1_plan(500, equivalent=True)
        plan = build_binance_provider_plan(s1, request_weight_budget=250, max_raw_resource_bytes=1_000_000)
        result = build_binance_liquidity_resource(
            plan, s1, req, raw_book(), observation_id="quantity", observation_timestamp_ms=NOW_MS
        )
        q = result["quantity_semantics"]
        self.assertFalse(q["consumer_qualified_equivalent"])
        self.assertIsNone(q["base_equivalent"])
        self.assertIsNone(q["quote_equivalent"])
        self.assertFalse(result["qualified_resource"]["request_satisfied"])

    def test_021_resource_reuse_remains_before_provider_acquisition(self):
        req, s1, plan = provider_plan(500)
        complete = build_binance_liquidity_resource(
            plan, s1, req, raw_book(), observation_id="existing", observation_timestamp_ms=NOW_MS
        )["qualified_resource"]
        narrower = request(250)
        reuse = plan_liquidity_acquisition(narrower, {"totally": "untrusted"}, complete)
        self.assertEqual(reuse["decision"], "REUSE")
        self.assertFalse(reuse["network_required"])
        with self.assertRaisesRegex(BinanceS2Error, "S1_PLAN_REVALIDATION_FAILED"):
            build_binance_provider_plan(reuse, request_weight_budget=250, max_raw_resource_bytes=1_000_000)
        self.assertTrue(evaluate_resource_satisfaction(complete, narrower)["reusable"])

    def test_022_normal_db_c_source_is_network_free(self):
        source = (ROOT / "src/liquidity_s2_binance_adapter.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue({"urllib", "requests", "http", "socket", "aiohttp"}.isdisjoint(imported))
        self.assertNotIn("urlopen", source)
        self.assertNotIn("requests.", source)

    def test_023_legacy_fixed_100_spot_acquisition_is_replaced_by_canonical_g2a_successor(self):
        source = (ROOT / "src/intelligence.py").read_text(encoding="utf-8")
        self.assertNotIn('provider("binance-spot",spot)', source)
        self.assertIn("CANONICAL_G2A_S3_DURABLE_BASELINE", source)
        self.assertIn('"legacy_fixed_100_network_calls":0', source)
        self.assertIn('providers["binance-usdm"]={"status":"DISABLED_BY_POLICY"', source)

    def test_024_s1_contract_and_usdm_policy_boundaries_remain_inactive(self):
        s1_contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        self.assertFalse(s1_contract["stage_boundaries"]["S3"]["active_in_this_contract_installation"])
        self.assertFalse(s1_contract["runtime_implementation"]["s3_active"])
        self.assertEqual(bridge["disabled_providers"]["binance-usdm"]["status"], "DISABLED_BY_POLICY")
        self.assertEqual(bridge["disabled_providers"]["binance-usdm"]["network_calls"], 0)

    def test_025_no_second_collector_catalog_resolver_reader_or_authority(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        architecture = contract["architecture"]
        self.assertFalse(architecture["second_collector"])
        self.assertFalse(architecture["second_catalog"] if "second_catalog" in architecture else architecture["second_capability_authority"])
        self.assertFalse(architecture["second_resolver"])
        self.assertFalse(architecture["second_reader"])
        self.assertFalse(architecture["second_provider_authority"])
        self.assertFalse(architecture["second_market_data_authority"])

    def test_026_provider_plan_tampered_weight_recomputed_hash_is_not_authority(self):
        _, s1, plan = provider_plan(500)
        forged = dict(plan)
        forged["request_weight"] = 1
        material = dict(forged)
        material.pop("provider_plan_sha256")
        forged["provider_plan_sha256"] = sha256_canonical_json(material)
        with self.assertRaisesRegex(BinanceS2Error, "PROVIDER_PLAN_REVALIDATION_MISMATCH"):
            validate_binance_provider_plan(forged, s1)

    def test_027_provider_plan_tampered_product_identity_is_not_authority(self):
        _, s1, plan = provider_plan(500)
        forged = dict(plan)
        forged["provider_product"] = "USDⓈ-M Futures"
        material = dict(forged)
        material.pop("provider_plan_sha256")
        forged["provider_plan_sha256"] = sha256_canonical_json(material)
        with self.assertRaisesRegex(BinanceS2Error, "PROVIDER_PLAN_REVALIDATION_MISMATCH"):
            validate_binance_provider_plan(forged, s1)

    def test_028_level_count_coverage_and_completion_are_distinct(self):
        req, s1, plan = provider_plan(500)
        result = build_binance_liquidity_resource(
            plan, s1, req, raw_book(bid_outer="97.7", ask_outer="104.1"),
            observation_id="distinct", observation_timestamp_ms=NOW_MS,
        )
        self.assertEqual(result["provider_requested_level_count"], 5000)
        self.assertEqual(result["actual_observed_bid_level_count"], 3)
        self.assertEqual(result["achieved_bid_coverage_bps"], "230")
        self.assertFalse(result["coverage_complete"])
        self.assertTrue(result["truncated"])

    def test_029_plan_identity_is_deterministic(self):
        _, s1a = s1_plan(500)
        _, s1b = s1_plan(500)
        a = build_binance_provider_plan(s1a, request_weight_budget=250, max_raw_resource_bytes=1_000_000)
        b = build_binance_provider_plan(s1b, request_weight_budget=250, max_raw_resource_bytes=1_000_000)
        self.assertEqual(a, b)
        self.assertEqual(a["provider_plan_sha256"], b["provider_plan_sha256"])

    def test_030_result_revalidation_detects_tamper(self):
        req, s1, plan = provider_plan(500)
        result = build_binance_liquidity_resource(
            plan, s1, req, raw_book(), observation_id="valid", observation_timestamp_ms=NOW_MS
        )
        self.assertEqual(validate_binance_liquidity_result(result), result)
        result["achieved_bid_coverage_bps"] = "0"
        with self.assertRaisesRegex(BinanceS2Error, "RESULT_SHA256_MISMATCH"):
            validate_binance_liquidity_result(result)


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: Binance canonical base host is now S2 plan material
