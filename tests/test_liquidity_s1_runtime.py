from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

from liquidity_s1_runtime import (
    BOOK_SCHEMA,
    LiquidityS1Error,
    assert_one_coherent_provider_observation,
    canonical_plan_bytes,
    compute_side_coverage,
    evaluate_resource_satisfaction,
    normalize_liquidity_request,
    normalize_order_book_observation,
    plan_liquidity_acquisition,
    qualify_liquidity_resource,
    qualify_quantity_semantics,
)

ROOT = Path(__file__).resolve().parents[1]


def request(target=250, *, provider="binance-spot", instrument="ETHUSDT",
            book_kind="L2_LEVEL_BOOK", representation="RAW", max_age=600,
            equivalent=False):
    return {
        "series_id": f"liquidity.{provider}.{instrument}.orderbook",
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "representation": representation,
        "target_bps": target,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": max_age},
        "completeness": {"required": True},
        "quantity_semantics": {
            "mode": "NATIVE_FIRST",
            "consumer_equivalent_required": equivalent,
        },
    }


def resource(bid=250, ask=250, *, req_bid=250, req_ask=250, provider="binance-spot",
             instrument="ETHUSDT", book_kind="L2_LEVEL_BOOK", representation="RAW",
             state="QUALIFIED", age=0, coherent=True, consumer_equiv=False):
    bid_ok = bid >= req_bid
    ask_ok = ask >= req_ask
    return {
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "representation": representation,
        "observation_id": "obs-1",
        "coherent_observation": coherent,
        "qualification_state": state,
        "age_seconds": age,
        "requested_bid_coverage_bps": str(req_bid),
        "requested_ask_coverage_bps": str(req_ask),
        "achieved_bid_coverage_bps": str(bid),
        "achieved_ask_coverage_bps": str(ask),
        "coverage_complete_bid": bid_ok,
        "coverage_complete_ask": ask_ok,
        "truncated": not (bid_ok and ask_ok),
        "quantity_semantics": {
            "native_quantity_preserved": True,
            "consumer_qualified_equivalent": consumer_equiv,
        },
    }


def observation(bid_outer="95", ask_outer="105", *, provider="binance-spot",
                instrument="ETHUSDT", book_kind="L2_LEVEL_BOOK",
                source_representation="RAW", oid="obs-1"):
    return {
        "observation_id": oid,
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "source_representation": source_representation,
        "timestamp_ms": 1_800_000_000_000,
        "bids": [["99.9", "2"], ["98", "3"], [bid_outer, "4"]],
        "asks": [["100.1", "2"], ["102", "3"], [ask_outer, "4"]],
    }


class S1RuntimeTests(unittest.TestCase):
    def test_01_exact_coverage_reuse(self):
        x = evaluate_resource_satisfaction(resource(), request())
        self.assertEqual(x["status"], "SATISFIED")
        self.assertTrue(x["reusable"])

    def test_02_dominating_resource_reuse(self):
        x = evaluate_resource_satisfaction(resource(500, 500, req_bid=500, req_ask=500), request(250))
        self.assertEqual(x["status"], "SATISFIED")

    def test_03_bid_insufficient(self):
        x = evaluate_resource_satisfaction(resource(230, 500, req_bid=500, req_ask=500), request(250))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("BID_COVERAGE_INSUFFICIENT", x["reasons"])

    def test_04_ask_insufficient(self):
        x = evaluate_resource_satisfaction(resource(500, 230, req_bid=500, req_ask=500), request(250))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("ASK_COVERAGE_INSUFFICIENT", x["reasons"])

    def test_05_both_insufficient_for_500_and_truncated(self):
        x = evaluate_resource_satisfaction(resource(230, 240, req_bid=500, req_ask=500), request(500))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertTrue(resource(230, 240, req_bid=500, req_ask=500)["truncated"])

    def test_06_stale_resource_not_reusable(self):
        x = evaluate_resource_satisfaction(resource(500, 500, req_bid=500, req_ask=500, age=601), request())
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("STALE", x["reasons"])

    def test_07_not_qualified_resource(self):
        x = evaluate_resource_satisfaction(resource(state="NOT_QUALIFIED"), request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_08_source_conflict_resource(self):
        x = evaluate_resource_satisfaction(resource(state="SOURCE_CONFLICT"), request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_09_wrong_instrument(self):
        x = evaluate_resource_satisfaction(resource(instrument="BTCUSDT"), request())
        self.assertIn("INSTRUMENT_MISMATCH", x["reasons"])

    def test_10_wrong_provider(self):
        x = evaluate_resource_satisfaction(resource(provider="kraken-spot"), request())
        self.assertIn("PROVIDER_MISMATCH", x["reasons"])

    def test_11_wrong_book_kind(self):
        x = evaluate_resource_satisfaction(
            resource(book_kind="PROVIDER_GROUPED_L2"),
            request(book_kind="L2_LEVEL_BOOK"),
        )
        self.assertIn("BOOK_KIND_MISMATCH", x["reasons"])

    def test_12_summary_cannot_masquerade_as_raw(self):
        x = evaluate_resource_satisfaction(resource(representation="SUMMARY"), request(representation="RAW"))
        self.assertIn("REPRESENTATION_NOT_DOMINATING", x["reasons"])

    def test_13_raw_can_satisfy_narrower_profile(self):
        x = evaluate_resource_satisfaction(
            resource(500, 500, req_bid=500, req_ask=500, representation="RAW"),
            request(250, representation="PROFILE"),
        )
        self.assertEqual(x["status"], "SATISFIED")

    def test_14_truncated_deeper_resource_can_satisfy_narrower_request(self):
        x = evaluate_resource_satisfaction(
            resource(300, 310, req_bid=500, req_ask=500),
            request(250),
        )
        self.assertEqual(x["status"], "SATISFIED")

    def test_15_500_bps_truncation_no_extrapolation(self):
        book = normalize_order_book_observation(observation("97.7", "104.1"))
        cov = compute_side_coverage(book, request(500))
        self.assertEqual(cov["achieved_bid_coverage_bps"], "230")
        self.assertEqual(cov["achieved_ask_coverage_bps"], "410")
        self.assertFalse(cov["coverage_complete_bid"])
        self.assertFalse(cov["coverage_complete_ask"])
        self.assertTrue(cov["truncated"])
        self.assertFalse(cov["extrapolation_allowed"])

    def test_16_native_derivatives_quantity_without_conversion(self):
        q = qualify_quantity_semantics(native_quantity="12", native_quantity_unit="CONTRACTS", contract_quantity="12")
        self.assertEqual(q["native_quantity"], "12")
        self.assertEqual(q["contract_quantity"], "12")
        self.assertIsNone(q["base_equivalent"])
        self.assertIsNone(q["quote_equivalent"])
        self.assertFalse(q["consumer_qualified_equivalent"])

    def test_17_deterministic_planner(self):
        cap = {
            "provider_id": "binance-spot",
            "book_kind": "L2_LEVEL_BOOK",
            "raw_book_capability": "CONFIRMED",
            "selectable_depth_limit": "QUALIFIED",
            "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
        }
        a = plan_liquidity_acquisition(request(500), cap, resource(250, 250))
        b = plan_liquidity_acquisition(request(500), cap, resource(250, 250))
        self.assertEqual(canonical_plan_bytes(a), canonical_plan_bytes(b))
        self.assertEqual(a["acquisition_plan"]["plan_sha256"], b["acquisition_plan"]["plan_sha256"])

    def test_18_unknown_provider_depth_bound_fails_closed(self):
        cap = {
            "provider_id": "kraken-futures",
            "book_kind": "FUTURES_L2_BOOK",
            "raw_book_capability": "CONFIRMED",
            "selectable_depth_limit": "NOT_NORMATIVELY_DOCUMENTED",
            "qualified_provider_depth_parameter": None,
        }
        result = plan_liquidity_acquisition(
            request(500, provider="kraken-futures", instrument="PI_ETHUSD", book_kind="FUTURES_L2_BOOK"),
            cap,
        )
        bound = result["acquisition_plan"]["provider_depth_bound"]
        self.assertEqual(bound["status"], "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED")
        self.assertIsNone(bound["qualified_provider_depth_parameter"])

    def test_19_one_observation_invariant(self):
        a = observation(oid="a")
        b = observation(oid="b")
        with self.assertRaisesRegex(LiquidityS1Error, "MULTI_OBSERVATION_STITCHING_FORBIDDEN"):
            assert_one_coherent_provider_observation([a, b])
        self.assertIs(assert_one_coherent_provider_observation([a]), a)

    def test_20_reuse_before_acquisition(self):
        cap = {
            "provider_id": "binance-spot",
            "book_kind": "L2_LEVEL_BOOK",
            "raw_book_capability": "CONFIRMED",
            "selectable_depth_limit": "QUALIFIED",
            "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
        }
        result = plan_liquidity_acquisition(
            request(250), cap, resource(500, 500, req_bid=500, req_ask=500)
        )
        self.assertEqual(result["decision"], "REUSE")
        self.assertFalse(result["network_required"])
        self.assertIsNone(result["acquisition_plan"])

    def test_21_semantic_request_rejects_physical_fields(self):
        bad = request()
        bad["provider_url"] = "https://example.invalid"
        with self.assertRaisesRegex(LiquidityS1Error, "PHYSICAL_REQUEST_FIELD_FORBIDDEN"):
            normalize_liquidity_request(bad)

    def test_22_normalization_preserves_midpoint_anchor_and_order(self):
        book = normalize_order_book_observation(observation())
        self.assertEqual(book["schema_version"], BOOK_SCHEMA)
        self.assertEqual(book["reference_price_anchor"], "BEST_BID_ASK_MIDPOINT")
        self.assertEqual(book["reference_price"], "100")
        self.assertEqual(book["bids"][0][0], "99.9")
        self.assertEqual(book["asks"][0][0], "100.1")

    def test_23_nan_and_infinity_fail_closed(self):
        for bad in (math.nan, math.inf, -math.inf):
            obs = observation()
            obs["bids"][0][1] = bad
            with self.assertRaises(LiquidityS1Error):
                normalize_order_book_observation(obs)

    def test_24_negative_quantity_and_coverage_fail_closed(self):
        obs = observation()
        obs["bids"][0][1] = "-1"
        with self.assertRaises(LiquidityS1Error):
            normalize_order_book_observation(obs)
        r = resource()
        r["achieved_bid_coverage_bps"] = "-1"
        self.assertNotEqual(evaluate_resource_satisfaction(r, request())["status"], "SATISFIED")

    def test_25_crossed_book_rejected(self):
        obs = observation()
        obs["bids"][0][0] = "101"
        with self.assertRaisesRegex(LiquidityS1Error, "CROSSED_OR_LOCKED_BOOK"):
            normalize_order_book_observation(obs)

    def test_26_unsorted_and_duplicate_levels_rejected(self):
        obs = observation()
        obs["bids"][0], obs["bids"][1] = obs["bids"][1], obs["bids"][0]
        with self.assertRaisesRegex(LiquidityS1Error, "BID_UNSORTED"):
            normalize_order_book_observation(obs)
        obs = observation()
        obs["asks"][1][0] = obs["asks"][0][0]
        with self.assertRaisesRegex(LiquidityS1Error, "ASK_DUPLICATE_PRICE"):
            normalize_order_book_observation(obs)

    def test_27_missing_identity_and_unknown_kind_representation_rejected(self):
        for field in ("observation_id", "provider_id", "instrument_id"):
            obs = observation()
            obs[field] = ""
            with self.assertRaises(LiquidityS1Error):
                normalize_order_book_observation(obs)
        obs = observation()
        obs["book_kind"] = "MAGIC_BOOK"
        with self.assertRaisesRegex(LiquidityS1Error, "BOOK_KIND_UNKNOWN"):
            normalize_order_book_observation(obs)
        obs = observation()
        obs["source_representation"] = "MAGIC"
        with self.assertRaisesRegex(LiquidityS1Error, "REPRESENTATION_UNKNOWN"):
            normalize_order_book_observation(obs)

    def test_28_unsupported_conversion_rejected(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_NOT_QUALIFIED"):
            qualify_quantity_semantics(
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority={"qualified": False},
            )

    def test_29_inconsistent_truncation_markers_not_reusable(self):
        r = resource(230, 410, req_bid=500, req_ask=500)
        r["truncated"] = False
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertIn("TRUNCATION_MARKER_INCONSISTENT", x["reasons"])

    def test_30_claimed_coverage_cannot_exceed_outermost_level(self):
        obs = observation("97.7", "104.1")
        obs["claimed_bid_coverage_bps"] = "250"
        with self.assertRaisesRegex(LiquidityS1Error, "CLAIMED_COVERAGE_EXCEEDS_OBSERVED_BOOK"):
            normalize_order_book_observation(obs)

    def test_31_network_free_source_boundary(self):
        source = (ROOT / "src/liquidity_s1_runtime.py").read_text(encoding="utf-8")
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

    def test_32_synthetic_500bps_e2e(self):
        req = request(500, representation="PROFILE")
        cap = {
            "provider_id": "binance-spot",
            "book_kind": "L2_LEVEL_BOOK",
            "raw_book_capability": "CONFIRMED",
            "selectable_depth_limit": "QUALIFIED",
            "qualified_provider_depth_parameter": {"name": "limit", "value": 5000},
        }
        existing = resource(250, 250, req_bid=250, req_ask=250)
        plan = plan_liquidity_acquisition(req, cap, existing)
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")
        normalized = normalize_order_book_observation(observation("94.9", "105.1"))
        q = qualify_quantity_semantics(native_quantity="1", native_quantity_unit="BASE_ASSET")
        qualified = qualify_liquidity_resource(normalized, req, age_seconds=0, quantity_semantics=q)
        self.assertTrue(qualified["request_satisfied"])
        self.assertFalse(qualified["truncated"])

    def test_33_synthetic_truncated_e2e(self):
        req = request(500, representation="PROFILE")
        normalized = normalize_order_book_observation(observation("97.7", "104.1"))
        q = qualify_quantity_semantics(native_quantity="1", native_quantity_unit="BASE_ASSET")
        qualified = qualify_liquidity_resource(normalized, req, age_seconds=0, quantity_semantics=q)
        self.assertFalse(qualified["request_satisfied"])
        self.assertTrue(qualified["truncated"])
        self.assertEqual(qualified["achieved_bid_coverage_bps"], "230")
        self.assertEqual(qualified["achieved_ask_coverage_bps"], "410")


if __name__ == "__main__":
    unittest.main()
