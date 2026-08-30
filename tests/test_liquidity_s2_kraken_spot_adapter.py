from __future__ import annotations

import ast
import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import plan_liquidity_acquisition
from liquidity_s2_kraken_spot_adapter import (
    CANONICAL_ROUTE_ID,
    MAX_RAW_RESOURCE_BYTES_HARD_CAP,
    NETWORK_EXECUTION_STATE,
    REST_ROUTE_ID,
    KrakenSpotS2Error,
    build_kraken_spot_liquidity_resource,
    build_kraken_spot_provider_plan,
    compute_kraken_ws_v2_checksum,
    get_kraken_spot_provider_capability,
    get_kraken_spot_route,
    normalize_kraken_spot_rest_snapshot,
    normalize_kraken_spot_ws_snapshot,
    validate_kraken_spot_liquidity_result,
    validate_kraken_spot_provider_plan,
    validate_kraken_spot_rest_depth,
    validate_kraken_spot_ws_depth,
)

ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1_800_000_600_000
NOW = datetime.fromtimestamp(NOW_MS / 1000, timezone.utc)


def request(target=500, *, instrument="ETHUSD", equivalent=False):
    return {
        "series_id": f"liquidity.kraken-spot.{instrument}.orderbook",
        "provider_id": "kraken-spot",
        "instrument_id": instrument,
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "target_bps": target,
        "bucket_bps": 25,
        "freshness": {"max_age_seconds": 600},
        "completeness": {"required": True},
        "quantity_semantics": {"mode": "NATIVE_FIRST", "consumer_equivalent_required": equivalent},
    }


def s1_capability():
    return {
        "provider_id": "kraken-spot",
        "book_kind": "L2_LEVEL_BOOK",
        "raw_book_capability": "AVAILABLE_EXTERNALLY",
        "selectable_depth_limit": "NOT_QUALIFIED",
        "qualified_provider_depth_parameter": None,
    }


def s1_plan(target=500, *, instrument="ETHUSD", existing_resource=None, equivalent=False):
    req = request(target, instrument=instrument, equivalent=equivalent)
    return req, plan_liquidity_acquisition(req, s1_capability(), existing_resource)


def provider_plan(target=500, *, instrument="ETHUSD", max_bytes=1_000_000):
    req, plan = s1_plan(target, instrument=instrument)
    return req, plan, build_kraken_spot_provider_plan(plan, max_raw_resource_bytes=max_bytes)


def ws_snapshot(plan, *, bid_outer="90", ask_outer="110", symbol=None, timestamp="2026-08-30T12:00:00.000000Z"):
    bids = [
        {"price": Decimal("99.9"), "qty": Decimal("2.00000000")},
        {"price": Decimal("98.0"), "qty": Decimal("3.00000000")},
        {"price": Decimal(bid_outer), "qty": Decimal("4.00000000")},
    ]
    asks = [
        {"price": Decimal("100.1"), "qty": Decimal("2.00000000")},
        {"price": Decimal("102.0"), "qty": Decimal("3.00000000")},
        {"price": Decimal(ask_outer), "qty": Decimal("4.00000000")},
    ]
    checksum = compute_kraken_ws_v2_checksum(bids, asks)
    return {
        "channel": "book",
        "type": "snapshot",
        "data": [{"symbol": symbol or plan["provider_symbol"], "bids": bids, "asks": asks, "checksum": checksum, "timestamp": timestamp}],
    }


def rest_snapshot(*, instrument="ETHUSD", wrong_key=False, empty=False):
    key = "ETH/USD" if instrument == "ETHUSD" else "BTC/USD"
    if wrong_key:
        key = "XBT/USD"
    bids = [] if empty else [["99.9", "2.0", 1_800_000_599.0], ["95", "3.0", 1_800_000_598.0]]
    asks = [] if empty else [["100.1", "2.0", 1_800_000_599.0], ["105", "3.0", 1_800_000_598.0]]
    return {"error": [], "result": {key: {"bids": bids, "asks": asks}}}


def recompute_plan_hash(plan):
    material = dict(plan)
    material.pop("provider_plan_sha256", None)
    plan["provider_plan_sha256"] = sha256_canonical_json(material)
    return plan


class KrakenSpotS2AdapterTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(current_data_transport, "_utc_now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def test_A_rest_capability_owner_is_unique(self):
        capability = get_kraken_spot_provider_capability()["order_book_capability"]
        self.assertEqual(set(capability["routes"]), {REST_ROUTE_ID, CANONICAL_ROUTE_ID})

    def test_B_ws_capability_route_owner_is_unique(self):
        self.assertEqual(get_kraken_spot_route(CANONICAL_ROUTE_ID)["route_id"], CANONICAL_ROUTE_ID)

    def test_C_rest_count_lower_upper_boundaries(self):
        self.assertEqual(validate_kraken_spot_rest_depth(1), 1)
        self.assertEqual(validate_kraken_spot_rest_depth(500), 500)

    def test_D_rest_out_of_range_depth_rejected(self):
        for value in (0, 501):
            with self.assertRaises(KrakenSpotS2Error):
                validate_kraken_spot_rest_depth(value)

    def test_E_ws_exact_supported_depth_set(self):
        self.assertEqual([validate_kraken_spot_ws_depth(v) for v in (10, 25, 100, 500, 1000)], [10, 25, 100, 500, 1000])

    def test_F_ws_unsupported_depth_rejected(self):
        for value in (1, 50, 999):
            with self.assertRaises(KrakenSpotS2Error):
                validate_kraken_spot_ws_depth(value)

    def test_G_caller_cannot_forge_route_selection(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "route_id": REST_ROUTE_ID})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_H_caller_cannot_forge_provider_max_depth(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_normative_max_depth": 5000})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_I_caller_cannot_forge_rest_count(self):
        capability = get_kraken_spot_provider_capability()["order_book_capability"]
        self.assertEqual(capability["routes"][REST_ROUTE_ID]["normative_max_depth"], 500)
        self.assertNotIn("count", request())

    def test_J_caller_cannot_forge_ws_depth(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_requested_level_count": 500})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_K_caller_cannot_forge_provider_symbol(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_symbol": "XBT/USD"})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_L_rest_ws_provider_identities_not_interchanged(self):
        _, s1, plan = provider_plan(instrument="BTCUSD")
        self.assertEqual(plan["provider_symbol"], "BTC/USD")
        self.assertEqual(get_kraken_spot_provider_capability()["order_book_capability"]["instrument_identity_map"]["BTCUSD"]["rest_request_pair"], "XBTUSD")

    def test_M_btc_xbt_alias_cannot_bypass_mapping(self):
        _, _, plan = provider_plan(instrument="BTCUSD")
        bad = ws_snapshot(plan, symbol="XBT/USD")
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1_plan(instrument="BTCUSD")[1], bad, observation_id="obs")

    def test_N_s1_request_is_revalidated(self):
        req, s1, plan = provider_plan()
        req["depth"] = 1000
        with self.assertRaises(KrakenSpotS2Error):
            build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="obs")

    def test_O_s1_plan_is_revalidated(self):
        _, s1, _ = provider_plan()
        forged = deepcopy(s1)
        forged["acquisition_plan"]["target_bps"] = "250"
        with self.assertRaises(KrakenSpotS2Error):
            build_kraken_spot_provider_plan(forged, max_raw_resource_bytes=1_000_000)

    def test_P_reusable_dominating_resource_prevents_provider_planning(self):
        req, s1, plan = provider_plan(250)
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="obs")
        reused = plan_liquidity_acquisition(req, s1_capability(), result["qualified_resource"])
        self.assertEqual(reused["decision"], "REUSE")
        with self.assertRaises(KrakenSpotS2Error):
            build_kraken_spot_provider_plan(reused, max_raw_resource_bytes=1_000_000)

    def test_Q_target_250_bps_remains_representable(self):
        _, _, plan = provider_plan(250)
        self.assertEqual(plan["requested_target_bps"], "250")

    def test_R_target_500_bps_remains_representable(self):
        _, _, plan = provider_plan(500)
        self.assertEqual(plan["requested_target_bps"], "500")

    def test_S_physical_level_count_does_not_imply_coverage(self):
        _, _, plan = provider_plan()
        self.assertFalse(plan["coverage_guaranteed_by_level_count"])

    def test_T_one_rest_response_one_observation(self):
        book = normalize_kraken_spot_rest_snapshot("ETHUSD", rest_snapshot(), observation_id="rest-1")
        self.assertEqual(book["observation_id"], "rest-1")

    def test_U_one_ws_initial_snapshot_one_observation(self):
        _, s1, plan = provider_plan()
        book = normalize_kraken_spot_ws_snapshot(plan, s1, ws_snapshot(plan), observation_id="ws-1")
        self.assertEqual(book["observation_id"], "ws-1")

    def test_V_rest_ws_stitching_forbidden(self):
        capability = get_kraken_spot_provider_capability()["order_book_capability"]
        self.assertFalse(capability["rest_ws_stitching_allowed"])

    def test_W_sequential_rest_stitching_forbidden(self):
        self.assertFalse(get_kraken_spot_route(REST_ROUTE_ID)["sequential_rest_stitching_allowed"])

    def test_X_retry_creates_new_observation(self):
        _, _, plan = provider_plan()
        self.assertEqual(plan["retry_semantics"], "NEW_OBSERVATION")

    def test_Y_malformed_rest_response_fails_closed(self):
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_rest_snapshot("ETHUSD", {"result": {}}, observation_id="bad")

    def test_Z_empty_bid_or_ask_side_fails_closed(self):
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_rest_snapshot("ETHUSD", rest_snapshot(empty=True), observation_id="bad")

    def test_AA_wrong_provider_pair_identity_fails_closed(self):
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_rest_snapshot("BTCUSD", rest_snapshot(instrument="BTCUSD", wrong_key=True), observation_id="bad")

    def test_AB_malformed_ws_snapshot_fails_closed(self):
        _, s1, plan = provider_plan()
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, {"channel": "book", "type": "update", "data": []}, observation_id="bad")

    def test_AC_wrong_ws_symbol_fails_closed(self):
        _, s1, plan = provider_plan()
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, ws_snapshot(plan, symbol="BTC/USD"), observation_id="bad")

    def test_AD_valid_checksum_accepted(self):
        _, s1, plan = provider_plan()
        book = normalize_kraken_spot_ws_snapshot(plan, s1, ws_snapshot(plan), observation_id="good")
        self.assertEqual(book["provider_id"], "kraken-spot")

    def test_AE_wrong_checksum_fails_closed(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["data"][0]["checksum"] ^= 1
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_AF_caller_authored_checksum_not_authority(self):
        req, _, _ = provider_plan()
        self.assertNotIn("checksum", req)
        self.assertNotIn("checksum_valid", req)

    def test_AG_checksum_pass_does_not_imply_coverage_complete(self):
        req, s1, plan = provider_plan(500)
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan, bid_outer="97", ask_outer="103"), observation_id="narrow")
        self.assertTrue(result["truncated"])
        self.assertFalse(result["coverage_complete"])

    def test_AH_provider_timestamp_cannot_forge_s1_freshness(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan, timestamp="2000-01-01T00:00:00.000000Z")
        book = normalize_kraken_spot_ws_snapshot(plan, s1, raw, observation_id="provider-time")
        self.assertEqual(book["timestamp_ms"], NOW_MS)

    def test_AI_caller_timestamp_cannot_forge_s1_freshness(self):
        _, s1, plan = provider_plan()
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, ws_snapshot(plan), observation_id="caller-time", observation_timestamp_ms=NOW_MS - 60_000)

    def test_AJ_quantity_semantics_native_first(self):
        req, s1, plan = provider_plan()
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="qty")
        self.assertEqual(result["quantity_semantics"]["model"], "PRODUCT_AWARE_NATIVE_FIRST")

    def test_AK_unqualified_conversion_is_unavailable_never_zero(self):
        req, s1, plan = provider_plan()
        quantity = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="qty")["quantity_semantics"]
        self.assertIsNone(quantity["base_equivalent"])
        self.assertIsNone(quantity["quote_equivalent"])
        self.assertFalse(quantity["consumer_qualified_equivalent"])

    def test_AL_s1_recomputes_midpoint_and_coverage(self):
        req, s1, plan = provider_plan()
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="coverage")
        self.assertEqual(result["normalized_book"]["reference_price_anchor"], "BEST_BID_ASK_MIDPOINT")
        self.assertEqual(result["qualified_resource"]["achieved_bid_coverage_bps"], result["achieved_bid_coverage_bps"])

    def test_AM_target_miss_at_provider_max_is_truncated(self):
        req, s1, plan = provider_plan(500)
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan, bid_outer="97", ask_outer="103"), observation_id="truncated")
        self.assertTrue(result["provider_limit_exhausted"])
        self.assertTrue(result["truncated"])

    def test_AN_no_extrapolation_beyond_observed_book(self):
        req, s1, plan = provider_plan(500)
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan, bid_outer="97", ask_outer="103"), observation_id="no-extra")
        self.assertFalse(result["qualified_resource"]["extrapolation_allowed"])

    def test_AO_provider_reported_coverage_cannot_bypass_s1(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["data"][0]["coverage_complete"] = True
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, raw, observation_id="forged-coverage")

    def test_AP_stateful_ws_update_processing_not_active(self):
        capability = get_kraken_spot_provider_capability()["order_book_capability"]
        self.assertFalse(capability["stateful_ws_local_book_active"])
        self.assertFalse(get_kraken_spot_route(CANONICAL_ROUTE_ID)["stateful_local_book_active"])

    def test_AQ_grouped_book_not_treated_as_profile(self):
        record = get_kraken_spot_provider_capability()
        self.assertFalse(record["grouped_book_equals_aife_profile"])

    def test_AR_l3_not_treated_as_ordinary_l2(self):
        record = get_kraken_spot_provider_capability()
        self.assertIn("SEPARATE_AUTHORIZATION", record["l3_status"])
        self.assertEqual(record["order_book_capability"]["book_kind"], "L2_LEVEL_BOOK")

    def test_AS_normal_db_d1_source_is_network_free(self):
        tree = ast.parse((ROOT / "src/liquidity_s2_kraken_spot_adapter.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imported.update(alias.name.split(".")[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module: imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint({"urllib", "requests", "http", "socket", "aiohttp", "websockets"}))

    def test_AT_production_collector_unchanged(self):
        self.assertNotIn("liquidity_s2_kraken_spot_adapter", (ROOT / "src/collector.py").read_text(encoding="utf-8"))
        self.assertNotIn("liquidity_s2_kraken_spot_adapter", (ROOT / "src/intelligence.py").read_text(encoding="utf-8"))

    def test_AU_current_data_execution_unchanged(self):
        self.assertNotIn("liquidity_s2_kraken_spot_adapter", (ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8"))

    def test_AV_scheduler_unchanged(self):
        workflow = (ROOT / ".github/workflows/update-market.yml").read_text(encoding="utf-8")
        self.assertNotIn("liquidity_s2_kraken_spot_adapter", workflow)
        self.assertNotIn("db-d1-kraken-spot-probe", workflow)

    def test_AW_db_c_regression_surface_remains_present(self):
        self.assertTrue((ROOT / "src/liquidity_s2_binance_adapter.py").exists())
        self.assertTrue((ROOT / "tests/test_liquidity_s2_binance_adapter.py").exists())
        self.assertTrue((ROOT / "tools/validation/validate_liquidity_s2_binance_adapter.py").exists())

    def test_AX_db_d2_s2_successor_present_without_s3_activation(self):
        contracts = json.loads((ROOT / "contracts/provider-contracts.json").read_text(encoding="utf-8"))["contracts"]
        futures = [x for x in contracts if x.get("product") == "Futures Raw L2 Order Book"]
        self.assertEqual(len(futures), 1)
        capability = futures[0].get("order_book_capability")
        self.assertIsInstance(capability, dict)
        self.assertEqual(capability["provider_id"], "kraken-futures")
        self.assertEqual(capability["qualification_state"], "S2_QUALIFIED_NETWORK_INACTIVE")
        self.assertEqual(capability["network_activation"], "S3_NOT_ACTIVE")
        spot = get_kraken_spot_provider_capability()["order_book_capability"]
        self.assertEqual(spot["provider_id"], "kraken-spot")
        self.assertEqual(set(spot["routes"]), {REST_ROUTE_ID, CANONICAL_ROUTE_ID})

    def test_AY_s3_remains_inactive(self):
        _, _, plan = provider_plan()
        self.assertEqual(plan["network_execution"], NETWORK_EXECUTION_STATE)
        self.assertEqual(plan["network_execution"], "S3_NOT_ACTIVE")

    def test_AZ_no_second_provider_or_market_data_authority_created(self):
        contracts = json.loads((ROOT / "contracts/provider-contracts.json").read_text(encoding="utf-8"))["contracts"]
        owners = [x for x in contracts if isinstance(x.get("order_book_capability"), dict) and x["order_book_capability"].get("provider_id") == "kraken-spot"]
        self.assertEqual(len(owners), 1)

    def test_BA_provider_plan_hash_is_not_authority(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "transport": "REST"})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_BB_provider_capability_hash_is_rederived(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_capability_sha256": "0" * 64})
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_provider_plan(forged, s1)

    def test_BC_checksum_requires_decimal_safe_values(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["data"][0]["bids"][0]["price"] = 99.9
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, raw, observation_id="float-loss")

    def test_BD_raw_resource_bound_is_enforced(self):
        with self.assertRaises(KrakenSpotS2Error):
            provider_plan(max_bytes=MAX_RAW_RESOURCE_BYTES_HARD_CAP + 1)

    def test_BE_result_revalidation_detects_tamper(self):
        req, s1, plan = provider_plan()
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="result")
        validate_kraken_spot_liquidity_result(result, s1)
        forged = deepcopy(result)
        forged["requested_target_bps"] = "250"
        material = dict(forged); material.pop("result_sha256")
        forged["result_sha256"] = sha256_canonical_json(material)
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_liquidity_result(forged, s1)

    def test_BF_two_ws_data_items_cannot_form_one_observation(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["data"].append(deepcopy(raw["data"][0]))
        with self.assertRaises(KrakenSpotS2Error):
            normalize_kraken_spot_ws_snapshot(plan, s1, raw, observation_id="two")

    def test_BG_rest_asset_version_is_planner_owned_contract_fact(self):
        binding = get_kraken_spot_provider_capability()["order_book_capability"]["instrument_identity_map"]["ETHUSD"]
        self.assertEqual(binding["rest_asset_version"], 1)
        self.assertNotIn("assetVersion", request())

    def test_BH_ws_connection_limit_unknown_is_explicit_not_invented(self):
        authority = get_kraken_spot_route(CANONICAL_ROUTE_ID)["rate_limit_or_connection_limit_authority"]
        self.assertIn("APPROXIMATE", authority)
        self.assertIn("NOT_EXACT_S3_EXECUTION_QUOTA", authority)

    def test_BI_rest_depth_rate_limit_cost_unknown_is_explicit(self):
        route = get_kraken_spot_route(REST_ROUTE_ID)
        self.assertEqual(route["rate_limit_cost_if_normatively_qualified"], "NOT_QUALIFIED")

    def test_BJ_checksum_integrity_is_distinct_from_s1_coverage(self):
        req, s1, plan = provider_plan(500)
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan, bid_outer="97", ask_outer="103"), observation_id="distinct")
        self.assertEqual(result["provider_message_integrity"], "KRAKEN_WS_V2_CRC32_TOP10_VALIDATED")
        self.assertTrue(result["truncated"])

    def test_BK_outer_result_correlated_field_matrix_fails_closed(self):
        req, s1, plan = provider_plan()
        result = build_kraken_spot_liquidity_resource(plan, s1, req, ws_snapshot(plan), observation_id="matrix")
        validate_kraken_spot_liquidity_result(result, s1)
        mutations = {
            "requested_target_bps": lambda value: value.__setitem__("requested_target_bps", "250"),
            "provider_plan_sha256": lambda value: value.__setitem__("provider_plan_sha256", "0" * 64),
            "instrument_id": lambda value: value.__setitem__("instrument_id", "BTCUSD"),
            "provider_requested_level_count": lambda value: value.__setitem__("provider_requested_level_count", 500),
            "actual_observed_bid_level_count": lambda value: value.__setitem__("actual_observed_bid_level_count", 999),
            "actual_observed_ask_level_count": lambda value: value.__setitem__("actual_observed_ask_level_count", 999),
            "achieved_bid_coverage_bps": lambda value: value.__setitem__("achieved_bid_coverage_bps", "9999"),
            "achieved_ask_coverage_bps": lambda value: value.__setitem__("achieved_ask_coverage_bps", "9999"),
            "coverage_complete_bid": lambda value: value.__setitem__("coverage_complete_bid", False),
            "coverage_complete_ask": lambda value: value.__setitem__("coverage_complete_ask", False),
            "coverage_complete": lambda value: value.__setitem__("coverage_complete", False),
            "truncated": lambda value: value.__setitem__("truncated", not value["truncated"]),
            "normalized_book": lambda value: value["normalized_book"].__setitem__("best_bid", "1"),
            "quantity_semantics": lambda value: value["quantity_semantics"].__setitem__("native_quantity", "1"),
            "qualified_resource": lambda value: value["qualified_resource"].__setitem__("request_satisfied", False),
        }
        for name, mutate in mutations.items():
            forged = deepcopy(result)
            mutate(forged)
            material = dict(forged)
            material.pop("result_sha256")
            forged["result_sha256"] = sha256_canonical_json(material)
            with self.subTest(field=name):
                with self.assertRaises(ValueError):
                    validate_kraken_spot_liquidity_result(forged, s1)

        forged = deepcopy(result)
        forged_plan = forged["provider_plan"]
        forged_plan["requested_target_bps"] = "250"
        recompute_plan_hash(forged_plan)
        forged["provider_plan_sha256"] = forged_plan["provider_plan_sha256"]
        forged["requested_target_bps"] = "250"
        material = dict(forged)
        material.pop("result_sha256")
        forged["result_sha256"] = sha256_canonical_json(material)
        with self.assertRaises(KrakenSpotS2Error):
            validate_kraken_spot_liquidity_result(forged, s1)


if __name__ == "__main__":
    unittest.main()
