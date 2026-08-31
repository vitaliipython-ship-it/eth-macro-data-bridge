from __future__ import annotations

import ast
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import (
    LiquidityS1Error,
    assert_one_coherent_provider_observation,
    normalize_liquidity_request,
    plan_liquidity_acquisition,
    qualify_liquidity_resource,
)
from liquidity_s2_kraken_futures_adapter import (
    BOOK_KIND,
    CANONICAL_ROUTE_ID,
    DEPTH_KNOWLEDGE_STATE,
    MAX_RAW_RESOURCE_BYTES_HARD_CAP,
    MESSAGE_INTEGRITY_STATE,
    NETWORK_EXECUTION_STATE,
    PROVIDER_ID,
    PROVIDER_LIMIT_STATE,
    KrakenFuturesS2Error,
    build_kraken_futures_liquidity_resource,
    build_kraken_futures_provider_plan,
    get_kraken_futures_provider_capability,
    get_kraken_futures_route,
    normalize_kraken_futures_ws_snapshot,
    validate_kraken_futures_liquidity_result,
    validate_kraken_futures_provider_plan,
)

ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1_800_000_600_000
NOW = datetime.fromtimestamp(NOW_MS / 1000, timezone.utc)


def request(
    target: int = 500,
    *,
    instrument: str = "PI_ETHUSD",
    equivalent: bool = False,
) -> dict:
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
            "consumer_equivalent_required": equivalent,
        },
    }


def s1_capability() -> dict:
    return {
        "provider_id": PROVIDER_ID,
        "book_kind": BOOK_KIND,
        "raw_book_capability": "CONFIRMED",
        "selectable_depth_limit": DEPTH_KNOWLEDGE_STATE,
        "qualified_provider_depth_parameter": None,
    }


def s1_plan(
    target: int = 500,
    *,
    instrument: str = "PI_ETHUSD",
    existing_resource=None,
    equivalent: bool = False,
):
    req = request(target, instrument=instrument, equivalent=equivalent)
    return req, plan_liquidity_acquisition(
        req,
        s1_capability(),
        existing_resource,
    )


def provider_plan(
    target: int = 500,
    *,
    instrument: str = "PI_ETHUSD",
    max_bytes: int = 1_000_000,
):
    req, plan = s1_plan(target, instrument=instrument)
    return req, plan, build_kraken_futures_provider_plan(
        plan,
        max_raw_resource_bytes=max_bytes,
    )


def ws_snapshot(
    plan: dict,
    *,
    bid_outer: str = "90",
    ask_outer: str = "110",
    product_id: str | None = None,
    seq: int = 42,
    timestamp: int = 1_800_000_599_000,
):
    return {
        "feed": "book_snapshot",
        "product_id": product_id or plan["provider_product_id"],
        "timestamp": timestamp,
        "seq": seq,
        "tickSize": None,
        "bids": [
            {"price": Decimal("99.9"), "qty": Decimal("2")},
            {"price": Decimal("98"), "qty": Decimal("3")},
            {"price": Decimal(bid_outer), "qty": Decimal("4")},
        ],
        "asks": [
            {"price": Decimal("100.1"), "qty": Decimal("2")},
            {"price": Decimal("102"), "qty": Decimal("3")},
            {"price": Decimal(ask_outer), "qty": Decimal("4")},
        ],
    }


def recompute_plan_hash(plan: dict) -> dict:
    material = dict(plan)
    material.pop("provider_plan_sha256", None)
    plan["provider_plan_sha256"] = sha256_canonical_json(material)
    return plan


def recompute_result_hash(result: dict) -> dict:
    material = dict(result)
    material.pop("result_sha256", None)
    result["result_sha256"] = sha256_canonical_json(material)
    return result


class KrakenFuturesS2AdapterTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(current_data_transport, "_utc_now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def build_result(self, target=500, *, instrument="PI_ETHUSD", bid_outer="90", ask_outer="110"):
        req, s1, plan = provider_plan(target, instrument=instrument)
        raw = ws_snapshot(plan, bid_outer=bid_outer, ask_outer=ask_outer)
        result = build_kraken_futures_liquidity_resource(
            plan,
            s1,
            req,
            raw,
            observation_id="obs",
        )
        return req, s1, plan, raw, result

    def test_A_provider_capability_owner_is_unique(self):
        capability = get_kraken_futures_provider_capability()["order_book_capability"]
        self.assertEqual(capability["provider_id"], PROVIDER_ID)

    def test_B_s2_qualified_but_network_inactive(self):
        capability = get_kraken_futures_provider_capability()["order_book_capability"]
        self.assertEqual(capability["qualification_state"], "S2_QUALIFIED_NETWORK_INACTIVE")
        self.assertEqual(capability["network_activation"], NETWORK_EXECUTION_STATE)

    def test_C_semantic_request_normalization(self):
        normalized = normalize_liquidity_request(request())
        self.assertEqual(normalized["target_bps"], "500")
        self.assertNotIn("depth", normalized)

    def test_D_target_250_bps_representable(self):
        _, _, plan = provider_plan(250)
        self.assertEqual(plan["requested_target_bps"], "250")

    def test_E_target_500_bps_representable(self):
        _, _, plan = provider_plan(500)
        self.assertEqual(plan["requested_target_bps"], "500")

    def test_F_caller_cannot_choose_provider_depth(self):
        forged = request()
        forged["depth"] = 100
        with self.assertRaises(LiquidityS1Error):
            normalize_liquidity_request(forged)

    def test_G_caller_cannot_choose_route(self):
        forged = request()
        forged["websocket_endpoint"] = "wss://futures.kraken.com/ws/v1"
        with self.assertRaises(LiquidityS1Error):
            normalize_liquidity_request(forged)

    def test_H_caller_cannot_choose_product_identity(self):
        forged = request()
        forged["provider_product_id"] = "PF_ETHUSD"
        with self.assertRaises(LiquidityS1Error):
            normalize_liquidity_request(forged)

    def test_I_exact_eth_product_mapping(self):
        _, _, plan = provider_plan(instrument="PI_ETHUSD")
        self.assertEqual(plan["provider_product_id"], "PI_ETHUSD")

    def test_J_exact_btc_xbt_product_mapping(self):
        _, _, plan = provider_plan(instrument="PI_XBTUSD")
        self.assertEqual(plan["provider_product_id"], "PI_XBTUSD")

    def test_K_wrong_product_response_rejected(self):
        _, s1, plan = provider_plan()
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(
                plan,
                s1,
                ws_snapshot(plan, product_id="PF_ETHUSD"),
                observation_id="bad",
            )

    def test_L_malformed_book_rejected(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw.pop("asks")
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_M_unsorted_bids_rejected(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["bids"][0], raw["bids"][1] = raw["bids"][1], raw["bids"][0]
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_N_unsorted_asks_rejected(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["asks"][0], raw["asks"][1] = raw["asks"][1], raw["asks"][0]
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_O_crossed_book_rejected(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["bids"][0]["price"] = Decimal("101")
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_P_malformed_numeric_rejected(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["bids"][0]["qty"] = "NaN"
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_Q_provider_native_quantity_preserved(self):
        _, _, _, _, result = self.build_result()
        quantity = result["quantity_semantics"]
        self.assertEqual(quantity["native_quantity"], "18")
        self.assertTrue(quantity["native_quantity_preserved"])

    def test_R_no_unqualified_quantity_conversion(self):
        _, _, _, _, result = self.build_result()
        quantity = result["quantity_semantics"]
        self.assertIsNone(quantity["base_equivalent"])
        self.assertIsNone(quantity["quote_equivalent"])
        self.assertFalse(quantity["consumer_qualified_equivalent"])

    def test_S_unknown_conversion_is_not_zero(self):
        _, _, _, _, result = self.build_result()
        quantity = result["quantity_semantics"]
        self.assertNotEqual(quantity["base_equivalent"], 0)
        self.assertNotEqual(quantity["quote_equivalent"], 0)

    def test_T_provider_timestamp_is_not_freshness_authority(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan, timestamp=1)
        book = normalize_kraken_futures_ws_snapshot(
            plan,
            s1,
            raw,
            observation_id="provider-time",
        )
        self.assertEqual(book["timestamp_ms"], NOW_MS)

    def test_U_caller_timestamp_is_not_freshness_authority(self):
        _, s1, plan = provider_plan()
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(
                plan,
                s1,
                ws_snapshot(plan),
                observation_id="caller-time",
                observation_timestamp_ms=NOW_MS - 1,
            )

    def test_V_no_extrapolation_beyond_observed_book(self):
        _, _, _, _, result = self.build_result(
            bid_outer="97",
            ask_outer="103",
        )
        self.assertFalse(result["qualified_resource"]["extrapolation_allowed"])

    def test_W_side_specific_coverage_preserved(self):
        _, _, _, _, result = self.build_result(
            bid_outer="94",
            ask_outer="103",
        )
        self.assertNotEqual(
            result["achieved_bid_coverage_bps"],
            result["achieved_ask_coverage_bps"],
        )

    def test_X_target_miss_cannot_become_complete(self):
        _, _, _, _, result = self.build_result(
            500,
            bid_outer="97",
            ask_outer="103",
        )
        self.assertTrue(result["truncated"])
        self.assertFalse(result["coverage_complete"])

    def test_Y_unknown_provider_max_depth_not_invented(self):
        _, _, plan = provider_plan()
        self.assertEqual(plan["provider_normative_max_depth"], DEPTH_KNOWLEDGE_STATE)
        self.assertIsNone(plan["provider_requested_level_count"])
        self.assertIsNone(plan["provider_depth_parameter_name"])

    def test_Z_retry_creates_new_observation(self):
        _, _, plan = provider_plan()
        self.assertEqual(plan["retry_semantics"], "NEW_OBSERVATION")

    def test_AA_sequential_observations_cannot_be_stitched(self):
        with self.assertRaises(LiquidityS1Error):
            assert_one_coherent_provider_observation([{"a": 1}, {"a": 2}])

    def test_AB_alternate_routes_cannot_be_stitched(self):
        capability = get_kraken_futures_provider_capability()["order_book_capability"]
        self.assertEqual(set(capability["routes"]), {CANONICAL_ROUTE_ID})
        self.assertFalse(capability["rest_ws_stitching_allowed"])

    def test_AC_sequence_integrity_pass_does_not_imply_coverage_pass(self):
        _, _, _, _, result = self.build_result(
            500,
            bid_outer="97",
            ask_outer="103",
        )
        self.assertEqual(result["provider_message_integrity"], MESSAGE_INTEGRITY_STATE)
        self.assertFalse(result["coverage_complete"])

    def test_AD_bad_sequence_state_fails_closed(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan, seq=0)
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_AE_outer_result_tamper_detected(self):
        req, s1, _, _, result = self.build_result()
        result["coverage_complete"] = False
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(result, req, s1)

    def test_AF_correlated_field_tamper_and_recomputed_outer_hash_rejected(self):
        req, s1, _, _, result = self.build_result(500)
        forged_request = request(250)
        forged_resource = qualify_liquidity_resource(
            result["normalized_book"],
            forged_request,
            quantity_semantics=result["quantity_semantics"],
        )
        forged = deepcopy(result)
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
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AG_request_target_tamper_with_outer_hash_rejected(self):
        req, s1, _, _, result = self.build_result(500)
        forged_request = deepcopy(req)
        forged_request["target_bps"] = 250
        recompute_result_hash(result)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(result, forged_request, s1)

    def test_AH_provider_plan_tamper_rejected(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_product_id": "PF_ETHUSD"})
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_provider_plan(forged, s1)

    def test_AI_normalized_book_tamper_rejected(self):
        req, s1, _, _, result = self.build_result()
        forged = deepcopy(result)
        forged["normalized_book"]["bids"][-1][0] = "91"
        material = dict(forged["normalized_book"])
        material.pop("observation_sha256")
        forged["normalized_book"]["observation_sha256"] = sha256_canonical_json(material)
        recompute_result_hash(forged)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AJ_quantity_tamper_rejected(self):
        req, s1, _, _, result = self.build_result()
        forged = deepcopy(result)
        forged["quantity_semantics"]["native_quantity"] = "999"
        material = dict(forged["quantity_semantics"])
        material.pop("quantity_sha256")
        forged["quantity_semantics"]["quantity_sha256"] = sha256_canonical_json(material)
        recompute_result_hash(forged)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AK_coverage_truncated_tamper_rejected(self):
        req, s1, _, _, result = self.build_result(bid_outer="97", ask_outer="103")
        forged = deepcopy(result)
        forged["truncated"] = False
        forged["coverage_complete"] = True
        recompute_result_hash(forged)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AL_provider_instrument_tamper_rejected(self):
        req, s1, _, _, result = self.build_result()
        forged = deepcopy(result)
        forged["instrument_id"] = "PI_XBTUSD"
        recompute_result_hash(forged)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AM_network_activation_remains_s3_not_active(self):
        _, _, plan = provider_plan()
        self.assertEqual(plan["network_execution"], NETWORK_EXECUTION_STATE)

    def test_AN_no_production_network_side_effect_imports(self):
        tree = ast.parse(
            (ROOT / "src/liquidity_s2_kraken_futures_adapter.py").read_text(encoding="utf-8")
        )
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(
            imports.isdisjoint({"urllib", "requests", "http", "socket", "aiohttp", "websockets"})
        )

    def test_AO_deterministic_repeatability(self):
        req, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        first = build_kraken_futures_liquidity_resource(
            plan, s1, req, raw, observation_id="same"
        )
        second = build_kraken_futures_liquidity_resource(
            plan, s1, req, raw, observation_id="same"
        )
        self.assertEqual(first, second)

    def test_AP_raw_byte_bound_enforced(self):
        req, s1, plan = provider_plan(max_bytes=100)
        with self.assertRaises(KrakenFuturesS2Error):
            build_kraken_futures_liquidity_resource(
                plan, s1, req, ws_snapshot(plan), observation_id="too-large"
            )

    def test_AQ_hard_raw_byte_cap_enforced(self):
        _, s1 = s1_plan()
        with self.assertRaises(KrakenFuturesS2Error):
            build_kraken_futures_provider_plan(
                s1,
                max_raw_resource_bytes=MAX_RAW_RESOURCE_BYTES_HARD_CAP + 1,
            )

    def test_AR_tick_size_must_match_documented_null_snapshot_field(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["tickSize"] = "0.5"
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_AS_initial_snapshot_feed_required(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["feed"] = "book"
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_AT_empty_side_fails_closed(self):
        _, s1, plan = provider_plan()
        raw = ws_snapshot(plan)
        raw["asks"] = []
        with self.assertRaises(KrakenFuturesS2Error):
            normalize_kraken_futures_ws_snapshot(plan, s1, raw, observation_id="bad")

    def test_AU_pf_substitution_explicitly_forbidden(self):
        capability = get_kraken_futures_provider_capability()["order_book_capability"]
        self.assertFalse(capability["pf_substitution_for_pi"])

    def test_AV_route_has_no_selectable_depth_parameter(self):
        route = get_kraken_futures_route()
        self.assertIsNone(route["provider_depth_parameter_name"])
        self.assertEqual(route["selectable_depth_limit"], DEPTH_KNOWLEDGE_STATE)

    def test_AW_provider_limit_exhaustion_remains_unknown_not_false(self):
        _, _, _, _, result = self.build_result()
        self.assertEqual(result["provider_limit_exhausted"], PROVIDER_LIMIT_STATE)
        self.assertIsNot(result["provider_limit_exhausted"], False)

    def test_AX_provenance_hash_tamper_rejected(self):
        req, s1, _, _, result = self.build_result()
        forged = deepcopy(result)
        forged["provider_provenance"]["sequence"] += 1
        recompute_result_hash(forged)
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_liquidity_result(forged, req, s1)

    def test_AY_provenance_positive_sequence_is_structural_only(self):
        _, _, _, _, result = self.build_result()
        self.assertEqual(
            result["provider_provenance"]["sequence_role"],
            "SUBSCRIPTION_MESSAGE_SEQUENCE_NUMBER_STRUCTURAL_ONLY",
        )

    def test_AZ_no_checksum_semantics_invented(self):
        _, _, _, _, result = self.build_result()
        self.assertEqual(
            result["provider_provenance"]["checksum_semantics"],
            "NOT_NORMATIVELY_DOCUMENTED_FOR_CHOSEN_ROUTE",
        )

    def test_BA_full_result_revalidation_passes_for_valid_result(self):
        req, s1, _, _, result = self.build_result()
        self.assertEqual(validate_kraken_futures_liquidity_result(result, req, s1), result)

    def test_BB_resource_reuse_prevents_new_provider_plan(self):
        req, _, _, _, result = self.build_result(250)
        reused = plan_liquidity_acquisition(req, s1_capability(), result["qualified_resource"])
        self.assertEqual(reused["decision"], "REUSE")
        with self.assertRaises(KrakenFuturesS2Error):
            build_kraken_futures_provider_plan(reused, max_raw_resource_bytes=1_000_000)

    def test_BC_result_level_counts_derive_from_observed_book_only(self):
        _, _, _, _, result = self.build_result()
        self.assertEqual(
            result["actual_observed_bid_level_count"],
            len(result["normalized_book"]["bids"]),
        )
        self.assertEqual(
            result["actual_observed_ask_level_count"],
            len(result["normalized_book"]["asks"]),
        )

    def test_BD_provider_timestamp_preserved_as_provenance(self):
        _, _, plan = provider_plan()
        raw = ws_snapshot(plan, timestamp=123456789)
        req, s1 = s1_plan()
        result = build_kraken_futures_liquidity_resource(
            plan, s1, req, raw, observation_id="prov"
        )
        self.assertEqual(result["provider_provenance"]["provider_timestamp_ms"], 123456789)
        self.assertEqual(result["normalized_book"]["timestamp_ms"], NOW_MS)

    def test_BE_caller_cannot_forge_unknown_depth_into_zero(self):
        _, s1, plan = provider_plan()
        forged = recompute_plan_hash({**plan, "provider_normative_max_depth": 0})
        with self.assertRaises(KrakenFuturesS2Error):
            validate_kraken_futures_provider_plan(forged, s1)


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: Kraken Futures S3 delegation retains PI/no-depth/no-checksum authority
