from __future__ import annotations

import ast
import json
import math
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import current_data_transport
from canonical_json import sha256_canonical_json

from liquidity_s1_runtime import (
    BOOK_SCHEMA,
    QUANTITY_SCHEMA,
    REQUEST_SCHEMA,
    RESOURCE_SCHEMA,
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
    validate_normalized_order_book,
    validate_provider_capability_for_s1,
    validate_qualified_liquidity_resource,
    validate_quantity_semantics,
)

ROOT = Path(__file__).resolve().parents[1]
TEST_EVALUATION_TIME_MS = 1_800_000_600_000
TEST_EVALUATION_TIME_UTC = "2027-01-15T08:10:00Z"


def _evaluation_datetime(timestamp_ms: int = TEST_EVALUATION_TIME_MS) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)


def request(
    target=250,
    *,
    provider="binance-spot",
    instrument="ETHUSDT",
    book_kind="L2_LEVEL_BOOK",
    representation="RAW",
    max_age=600,
    equivalent=False,
):
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


def observation(
    bid_outer="95",
    ask_outer="105",
    *,
    provider="binance-spot",
    instrument="ETHUSDT",
    book_kind="L2_LEVEL_BOOK",
    source_representation="RAW",
    oid="obs-1",
    timestamp_ms=TEST_EVALUATION_TIME_MS,
):
    return {
        "observation_id": oid,
        "provider_id": provider,
        "instrument_id": instrument,
        "book_kind": book_kind,
        "source_representation": source_representation,
        "timestamp_ms": timestamp_ms,
        "bids": [["99.9", "2"], ["98", "3"], [bid_outer, "4"]],
        "asks": [["100.1", "2"], ["102", "3"], [ask_outer, "4"]],
    }


def quantity(
    *,
    provider="binance-spot",
    instrument="ETHUSDT",
    book_kind="L2_LEVEL_BOOK",
    native="12",
    unit="BASE_ASSET",
    contract=None,
):
    return qualify_quantity_semantics(
        provider_id=provider,
        instrument_id=instrument,
        book_kind=book_kind,
        native_quantity=native,
        native_quantity_unit=unit,
        contract_quantity=contract,
    )


def capability(
    *,
    provider="binance-spot",
    book_kind="L2_LEVEL_BOOK",
    raw="CONFIRMED",
    depth="NOT_QUALIFIED",
):
    return {
        "provider_id": provider,
        "book_kind": book_kind,
        "raw_book_capability": raw,
        "selectable_depth_limit": depth,
        "qualified_provider_depth_parameter": None,
    }


def legit_resource(
    *,
    bid_outer="95",
    ask_outer="105",
    creator_target=500,
    provider="binance-spot",
    instrument="ETHUSDT",
    book_kind="L2_LEVEL_BOOK",
    representation="RAW",
    age=0,
    equivalent=False,
):
    req = request(
        creator_target,
        provider=provider,
        instrument=instrument,
        book_kind=book_kind,
        representation=representation,
        equivalent=equivalent,
    )
    book = normalize_order_book_observation(
        observation(
            bid_outer,
            ask_outer,
            provider=provider,
            instrument=instrument,
            book_kind=book_kind,
            source_representation="RAW",
            timestamp_ms=TEST_EVALUATION_TIME_MS - age * 1000,
        )
    )
    q = quantity(provider=provider, instrument=instrument, book_kind=book_kind)
    return qualify_liquidity_resource(book, req, age_seconds=age, quantity_semantics=q)


def forged_existing() -> dict:
    return {
        "provider_id": "binance-spot",
        "instrument_id": "ETHUSDT",
        "book_kind": "L2_LEVEL_BOOK",
        "representation": "RAW",
        "observation_id": "forged",
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


class S1RuntimeTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime())
        clock.start()
        self.addCleanup(clock.stop)

    def test_001_request_250_normalizes(self):
        self.assertEqual(normalize_liquidity_request(request(250))["target_bps"], "250")

    def test_002_request_500_normalizes(self):
        self.assertEqual(normalize_liquidity_request(request(500))["target_bps"], "500")

    def test_003_request_canonical_revalidation_idempotent(self):
        a = normalize_liquidity_request(request())
        self.assertEqual(normalize_liquidity_request(a), a)

    def test_004_request_schema_marker_is_not_trust_proof_for_physical_field(self):
        bad = normalize_liquidity_request(request())
        bad["provider_url"] = "https://example.invalid"
        with self.assertRaisesRegex(LiquidityS1Error, "PHYSICAL_REQUEST_FIELD_FORBIDDEN"):
            evaluate_resource_satisfaction(None, bad)

    def test_005_request_schema_marker_is_not_trust_proof_for_unknown_field(self):
        bad = normalize_liquidity_request(request())
        bad["unexpected"] = True
        with self.assertRaisesRegex(LiquidityS1Error, "UNKNOWN_REQUEST_FIELD"):
            evaluate_resource_satisfaction(None, bad)

    def test_006_request_unknown_book_kind_fails(self):
        bad = request()
        bad["book_kind"] = "MAGIC"
        with self.assertRaisesRegex(LiquidityS1Error, "BOOK_KIND_UNKNOWN"):
            normalize_liquidity_request(bad)

    def test_007_request_unknown_representation_fails(self):
        bad = request()
        bad["representation"] = "MAGIC"
        with self.assertRaisesRegex(LiquidityS1Error, "REPRESENTATION_UNKNOWN"):
            normalize_liquidity_request(bad)

    def test_008_request_nonpositive_target_fails(self):
        bad = request()
        bad["target_bps"] = 0
        with self.assertRaisesRegex(LiquidityS1Error, "TARGET_BPS_NOT_POSITIVE"):
            normalize_liquidity_request(bad)

    def test_009_request_invalid_freshness_fails(self):
        bad = request()
        bad["freshness"] = {"max_age_seconds": 0}
        with self.assertRaisesRegex(LiquidityS1Error, "MAX_AGE_SECONDS_INVALID"):
            normalize_liquidity_request(bad)

    def test_010_request_invalid_quantity_requirement_fails(self):
        bad = request()
        bad["quantity_semantics"]["consumer_equivalent_required"] = "yes"
        with self.assertRaisesRegex(LiquidityS1Error, "CONSUMER_EQUIVALENT_REQUIREMENT_INVALID"):
            normalize_liquidity_request(bad)

    def test_011_book_normalization_midpoint_and_hash(self):
        book = normalize_order_book_observation(observation())
        self.assertEqual(book["reference_price"], "100")
        self.assertEqual(book["achieved_bid_coverage_bps"], "500")
        self.assertEqual(book["achieved_ask_coverage_bps"], "500")
        self.assertEqual(len(book["observation_sha256"]), 64)

    def test_012_book_revalidation_idempotent(self):
        book = normalize_order_book_observation(observation())
        self.assertEqual(validate_normalized_order_book(book), book)
        self.assertEqual(validate_normalized_order_book(validate_normalized_order_book(book)), book)

    def test_013_book_schema_marker_without_levels_fails(self):
        forged = {
            "schema_version": BOOK_SCHEMA,
            "observation_id": "x",
            "provider_id": "binance-spot",
            "instrument_id": "ETHUSDT",
        }
        with self.assertRaisesRegex(LiquidityS1Error, "NORMALIZED_BOOK_FIELDS_INVALID"):
            validate_normalized_order_book(forged)

    def test_014_book_forged_coverage_fails(self):
        book = normalize_order_book_observation(observation("97.7", "104.1"))
        book["achieved_bid_coverage_bps"] = "500"
        with self.assertRaisesRegex(LiquidityS1Error, "ACHIEVED_BID_COVERAGE_BPS_MISMATCH"):
            validate_normalized_order_book(book)

    def test_015_book_forged_midpoint_fails(self):
        book = normalize_order_book_observation(observation())
        book["reference_price"] = "999"
        with self.assertRaisesRegex(LiquidityS1Error, "REFERENCE_PRICE_MISMATCH"):
            validate_normalized_order_book(book)

    def test_016_book_forged_best_bid_fails(self):
        book = normalize_order_book_observation(observation())
        book["best_bid"] = "1"
        with self.assertRaisesRegex(LiquidityS1Error, "BEST_BID_MISMATCH"):
            validate_normalized_order_book(book)

    def test_017_book_forged_hash_fails(self):
        book = normalize_order_book_observation(observation())
        book["observation_sha256"] = "0" * 64
        with self.assertRaisesRegex(LiquidityS1Error, "OBSERVATION_SHA256_MISMATCH"):
            validate_normalized_order_book(book)

    def test_018_book_level_tamper_stale_hash_fails(self):
        book = normalize_order_book_observation(observation())
        book["bids"][1][1] = "33"
        with self.assertRaisesRegex(LiquidityS1Error, "OBSERVATION_SHA256_MISMATCH"):
            validate_normalized_order_book(book)

    def test_019_book_crossed_fails(self):
        obs = observation()
        obs["bids"][0][0] = "101"
        with self.assertRaisesRegex(LiquidityS1Error, "CROSSED_OR_LOCKED_BOOK"):
            normalize_order_book_observation(obs)

    def test_020_book_unsorted_fails(self):
        obs = observation()
        obs["bids"][0], obs["bids"][1] = obs["bids"][1], obs["bids"][0]
        with self.assertRaisesRegex(LiquidityS1Error, "BID_UNSORTED"):
            normalize_order_book_observation(obs)

    def test_021_book_duplicate_fails(self):
        obs = observation()
        obs["asks"][1][0] = obs["asks"][0][0]
        with self.assertRaisesRegex(LiquidityS1Error, "ASK_DUPLICATE_PRICE"):
            normalize_order_book_observation(obs)

    def test_022_book_nonfinite_quantity_fails(self):
        obs = observation()
        obs["bids"][0][1] = math.inf
        with self.assertRaisesRegex(LiquidityS1Error, "BID_QUANTITY_NON_FINITE"):
            normalize_order_book_observation(obs)

    def test_023_book_negative_quantity_fails(self):
        obs = observation()
        obs["asks"][0][1] = "-1"
        with self.assertRaisesRegex(LiquidityS1Error, "ASK_QUANTITY_NOT_POSITIVE"):
            normalize_order_book_observation(obs)

    def test_024_230_410_cannot_satisfy_500(self):
        book = normalize_order_book_observation(observation("97.7", "104.1"))
        cov = compute_side_coverage(book, request(500))
        self.assertEqual((cov["achieved_bid_coverage_bps"], cov["achieved_ask_coverage_bps"]), ("230", "410"))
        self.assertTrue(cov["truncated"])

    def test_025_500_500_physical_book_can_satisfy_500(self):
        book = normalize_order_book_observation(observation())
        cov = compute_side_coverage(book, request(500))
        self.assertTrue(cov["coverage_complete_bid"])
        self.assertTrue(cov["coverage_complete_ask"])
        self.assertFalse(cov["truncated"])

    def test_026_native_quantity_builder_returns_canonical_schema(self):
        q = quantity()
        self.assertEqual(q["schema_version"], QUANTITY_SCHEMA)
        self.assertEqual(q["model"], "PRODUCT_AWARE_NATIVE_FIRST")
        self.assertTrue(q["native_quantity_preserved"])
        self.assertFalse(q["consumer_qualified_equivalent"])

    def test_027_quantity_revalidation_idempotent(self):
        q = quantity()
        self.assertEqual(validate_quantity_semantics(q), q)
        self.assertEqual(validate_quantity_semantics(validate_quantity_semantics(q)), q)

    def test_028_arbitrary_consumer_equivalent_mapping_rejected(self):
        forged = {"native_quantity_preserved": True, "consumer_qualified_equivalent": True}
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SEMANTICS_FIELDS_INVALID"):
            qualify_liquidity_resource(
                normalize_order_book_observation(observation()),
                request(500, equivalent=True),
                age_seconds=0,
                quantity_semantics=forged,
            )

    def test_029_native_preserved_boolean_alone_is_not_qualification(self):
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SEMANTICS_FIELDS_INVALID"):
            validate_quantity_semantics({"native_quantity_preserved": True})

    def test_030_consumer_equivalent_required_fails_without_conversion(self):
        r = legit_resource(equivalent=True)
        x = evaluate_resource_satisfaction(r, request(500, equivalent=True))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("CONSUMER_EQUIVALENT_NOT_QUALIFIED", x["reasons"])

    def test_031_quantity_boolean_tamper_stale_hash_fails(self):
        q = quantity()
        q["consumer_qualified_equivalent"] = True
        with self.assertRaisesRegex(LiquidityS1Error, "CONSUMER_EQUIVALENT_NOT_QUALIFIED_IN_S1"):
            validate_quantity_semantics(q)

    def test_032_quantity_native_tamper_stale_hash_fails(self):
        q = quantity()
        q["native_quantity"] = "999"
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SHA256_MISMATCH"):
            validate_quantity_semantics(q)

    def test_033_quantity_unknown_field_fails(self):
        q = quantity()
        q["unexpected"] = True
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SEMANTICS_FIELDS_INVALID"):
            validate_quantity_semantics(q)

    def test_034_quantity_wrong_instrument_fails_resource_binding(self):
        q = quantity(instrument="BTCUSDT")
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_INSTRUMENT_MISMATCH"):
            qualify_liquidity_resource(
                normalize_order_book_observation(observation()),
                request(500),
                age_seconds=0,
                quantity_semantics=q,
            )

    def test_035_quantity_wrong_provider_fails_resource_binding(self):
        q = quantity(provider="kraken-spot")
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_PROVIDER_MISMATCH"):
            qualify_liquidity_resource(
                normalize_order_book_observation(observation()),
                request(500),
                age_seconds=0,
                quantity_semantics=q,
            )

    def test_036_quantity_wrong_book_kind_fails_resource_binding(self):
        q = quantity(book_kind="PROVIDER_GROUPED_L2")
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_BOOK_KIND_MISMATCH"):
            qualify_liquidity_resource(
                normalize_order_book_observation(observation()),
                request(500),
                age_seconds=0,
                quantity_semantics=q,
            )

    def test_037_quantity_negative_native_fails(self):
        with self.assertRaisesRegex(LiquidityS1Error, "NATIVE_QUANTITY_NEGATIVE"):
            quantity(native="-1")

    def test_038_quantity_nonfinite_native_fails(self):
        with self.assertRaisesRegex(LiquidityS1Error, "NATIVE_QUANTITY_NON_FINITE"):
            quantity(native="NaN")

    def test_039_quantity_negative_contract_fails(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CONTRACT_QUANTITY_NEGATIVE"):
            quantity(contract="-1")

    def test_040_quantity_forged_equivalent_fields_fail(self):
        q = quantity()
        q["base_equivalent"] = "1"
        with self.assertRaisesRegex(LiquidityS1Error, "UNQUALIFIED_BASE_EQUIVALENT_PRESENT"):
            validate_quantity_semantics(q)

    def test_041_quantity_forged_formula_identity_fails(self):
        q = quantity()
        q["conversion_formula_id"] = "forged"
        with self.assertRaisesRegex(LiquidityS1Error, "UNQUALIFIED_CONVERSION_FORMULA_PRESENT"):
            validate_quantity_semantics(q)

    def test_042_conversion_qualified_true_is_not_authority(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority={"qualified": True},
            )

    def test_043_fake_formula_does_not_qualify(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority={
                    "qualified": True,
                    "formula_id": "forged",
                    "formula_version": "1",
                    "instrument_spec_identity": "forged",
                    "base_equivalent": "1",
                    "quote_equivalent": "100",
                },
            )

    def test_044_fake_instrument_spec_does_not_qualify(self):
        forged = {
            "qualified": True,
            "formula_id": "x",
            "formula_version": "1",
            "instrument_spec_identity": "forged",
            "base_equivalent": "1",
            "quote_equivalent": "100",
        }
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority=forged,
            )

    def test_045_caller_equivalent_outputs_do_not_qualify(self):
        forged = {
            "qualified": True,
            "formula_id": "x",
            "formula_version": "1",
            "instrument_spec_identity": "x",
            "base_equivalent": "999",
            "quote_equivalent": "999",
        }
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="binance-spot",
                instrument_id="ETHUSDT",
                book_kind="L2_LEVEL_BOOK",
                native_quantity="1",
                native_quantity_unit="BASE_ASSET",
                conversion_authority=forged,
            )

    def test_046_wrong_provider_conversion_authority_cannot_qualify(self):
        forged = {"qualified": True, "provider_id": "wrong"}
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority=forged,
            )

    def test_047_wrong_instrument_conversion_authority_cannot_qualify(self):
        forged = {"qualified": True, "instrument_id": "PF_ETHUSD"}
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority=forged,
            )

    def test_048_nonfinite_conversion_output_cannot_qualify(self):
        forged = {"qualified": True, "base_equivalent": "NaN"}
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority=forged,
            )

    def test_049_missing_conversion_authority_stays_fail_closed_false(self):
        q = quantity(provider="kraken-futures", instrument="PI_ETHUSD", book_kind="FUTURES_L2_BOOK", unit="CONTRACTS")
        self.assertFalse(q["consumer_qualified_equivalent"])
        self.assertIsNone(q["base_equivalent"])
        self.assertIsNone(q["quote_equivalent"])

    def test_050_legitimate_resource_schema_and_hash(self):
        r = legit_resource()
        self.assertEqual(r["schema_version"], RESOURCE_SCHEMA)
        self.assertEqual(len(r["resource_sha256"]), 64)

    def test_051_legitimate_resource_revalidates(self):
        r = legit_resource()
        self.assertEqual(validate_qualified_liquidity_resource(r), r)

    def test_052_legitimate_resource_validation_idempotent(self):
        r = legit_resource()
        self.assertEqual(validate_qualified_liquidity_resource(validate_qualified_liquidity_resource(r)), r)

    def test_053_arbitrary_qualified_mapping_cannot_satisfy(self):
        x = evaluate_resource_satisfaction(forged_existing(), request(500))
        self.assertEqual(x["status"], "NOT_QUALIFIED")
        self.assertFalse(x["reusable"])

    def test_054_fake_500_500_cannot_satisfy_without_resource_proof(self):
        x = evaluate_resource_satisfaction(forged_existing(), request(250))
        self.assertNotEqual(x["status"], "SATISFIED")
        self.assertFalse(x["reusable"])

    def test_055_fake_coherent_true_is_not_proof(self):
        forged = forged_existing()
        forged["coherent_observation"] = True
        x = evaluate_resource_satisfaction(forged, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_056_missing_resource_schema_fails(self):
        r = legit_resource()
        del r["schema_version"]
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_057_invalid_resource_schema_fails(self):
        r = legit_resource()
        r["schema_version"] = "forged"
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_058_unknown_resource_field_fails(self):
        r = legit_resource()
        r["unexpected"] = True
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_059_forged_resource_hash_fails(self):
        r = legit_resource()
        r["resource_sha256"] = "0" * 64
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")
        self.assertIn("RESOURCE_SHA256_MISMATCH", x["reasons"][0])

    def test_060_tampered_coverage_stale_resource_hash_fails(self):
        r = legit_resource()
        r["achieved_bid_coverage_bps"] = "999"
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_061_tampered_quantity_stale_resource_hash_fails(self):
        r = legit_resource()
        r["quantity_semantics"]["native_quantity"] = "999"
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_062_tampered_observation_binding_stale_resource_hash_fails(self):
        r = legit_resource()
        r["observation_id"] = "forged"
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_063_tampered_qualification_state_is_not_credential(self):
        r = legit_resource()
        r["qualification_state"] = "QUALIFIED_FORGED"
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_064_tampered_coherent_boolean_is_not_credential(self):
        r = legit_resource()
        r["coherent_observation"] = False
        x = evaluate_resource_satisfaction(r, request())
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_065_valid_deeper_resource_dominates_narrower_request(self):
        r = legit_resource(bid_outer="94", ask_outer="106", creator_target=500)
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "SATISFIED")
        self.assertTrue(x["reusable"])

    def test_066_valid_truncated_but_sufficient_narrower_resource_reuses(self):
        r = legit_resource(bid_outer="97", ask_outer="103.1", creator_target=500)
        self.assertTrue(r["truncated"])
        self.assertFalse(r["request_satisfied"])
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "SATISFIED")
        self.assertTrue(x["reusable"])

    def test_067_valid_230_410_resource_not_enough_for_500(self):
        r = legit_resource(bid_outer="97.7", ask_outer="104.1", creator_target=500)
        x = evaluate_resource_satisfaction(r, request(500))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertFalse(x["reusable"])

    def test_068_stale_valid_resource_not_reusable(self):
        r = legit_resource(age=601)
        x = evaluate_resource_satisfaction(r, request(250, max_age=600))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("STALE", x["reasons"])

    def test_069_wrong_provider_valid_resource_not_reusable(self):
        r = legit_resource(provider="kraken-spot")
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("PROVIDER_MISMATCH", x["reasons"])

    def test_070_wrong_instrument_valid_resource_not_reusable(self):
        r = legit_resource(instrument="BTCUSDT")
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("INSTRUMENT_MISMATCH", x["reasons"])

    def test_071_raw_valid_resource_can_satisfy_profile(self):
        r = legit_resource()
        x = evaluate_resource_satisfaction(r, request(250, representation="PROFILE"))
        self.assertEqual(x["status"], "SATISFIED")

    def test_072_summary_does_not_dominate_raw(self):
        req = request(500, representation="SUMMARY")
        obs = observation(source_representation="SUMMARY")
        book = normalize_order_book_observation(obs)
        r = qualify_liquidity_resource(
            book,
            req,
            age_seconds=0,
            quantity_semantics=quantity(),
        )
        x = evaluate_resource_satisfaction(r, request(250, representation="RAW"))
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertIn("REPRESENTATION_NOT_DOMINATING", x["reasons"])

    def test_073_missing_resource_returns_unsatisfied_not_qualified_trust(self):
        x = evaluate_resource_satisfaction(None, request())
        self.assertEqual(x["status"], "UNSATISFIED")
        self.assertFalse(x["reusable"])

    def test_074_arbitrary_resource_cannot_cause_planner_reuse(self):
        result = plan_liquidity_acquisition(request(500), capability(), forged_existing())
        self.assertEqual(result["decision"], "ACQUISITION_REQUIRED")
        self.assertTrue(result["network_required"])

    def test_075_provider_capability_s1_valid_unqualified_depth(self):
        cap = validate_provider_capability_for_s1(capability(), request())
        self.assertEqual(cap["selectable_depth_limit"], "NOT_QUALIFIED")
        self.assertIsNone(cap["qualified_provider_depth_parameter"])

    def test_076_confirmed_raw_flag_cannot_qualify_depth(self):
        result = plan_liquidity_acquisition(request(500), capability(raw="CONFIRMED"))
        self.assertEqual(result["acquisition_plan"]["provider_depth_bound"]["status"], "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED")

    def test_077_arbitrary_qualified_depth_status_rejected(self):
        cap = capability(depth="QUALIFIED")
        with self.assertRaisesRegex(LiquidityS1Error, "PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1"):
            plan_liquidity_acquisition(request(500), cap)

    def test_078_fake_limit_5000_rejected(self):
        cap = capability()
        cap["qualified_provider_depth_parameter"] = {"name": "limit", "value": 5000}
        with self.assertRaisesRegex(LiquidityS1Error, "PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1"):
            plan_liquidity_acquisition(request(500), cap)

    def test_079_provider_capability_wrong_provider_fails(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CAPABILITY_PROVIDER_MISMATCH"):
            plan_liquidity_acquisition(request(), capability(provider="kraken-spot"))

    def test_080_provider_capability_wrong_book_kind_fails(self):
        with self.assertRaisesRegex(LiquidityS1Error, "CAPABILITY_BOOK_KIND_MISMATCH"):
            plan_liquidity_acquisition(request(), capability(book_kind="PROVIDER_GROUPED_L2"))

    def test_081_provider_capability_unknown_field_fails(self):
        cap = capability()
        cap["unexpected"] = True
        with self.assertRaisesRegex(LiquidityS1Error, "PROVIDER_CAPABILITY_FIELDS_INVALID"):
            plan_liquidity_acquisition(request(), cap)

    def test_082_provider_capability_unknown_state_fails(self):
        cap = capability(raw="FORGED")
        with self.assertRaisesRegex(LiquidityS1Error, "RAW_BOOK_CAPABILITY_STATE_INVALID"):
            plan_liquidity_acquisition(request(), cap)

    def test_083_kraken_futures_undocumented_depth_remains_not_qualified(self):
        req = request(
            500,
            provider="kraken-futures",
            instrument="PI_ETHUSD",
            book_kind="FUTURES_L2_BOOK",
        )
        cap = capability(
            provider="kraken-futures",
            book_kind="FUTURES_L2_BOOK",
            depth="NOT_NORMATIVELY_DOCUMENTED",
        )
        result = plan_liquidity_acquisition(req, cap)
        self.assertEqual(
            result["acquisition_plan"]["provider_depth_bound"]["status"],
            "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED",
        )

    def test_084_s1_does_not_guess_provider_depth(self):
        result = plan_liquidity_acquisition(request(500), capability())
        self.assertIsNone(
            result["acquisition_plan"]["provider_depth_bound"]["qualified_provider_depth_parameter"]
        )

    def test_085_s2_qualification_owner_declared_but_inactive(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        self.assertIn("PROVIDER_CAPABILITY_QUALIFICATION", contract["stage_boundaries"]["S2"]["owns"])
        self.assertFalse(contract["stage_boundaries"]["S2"]["active_in_this_contract_installation"])

    def test_086_reuse_before_capability_validation(self):
        r = legit_resource()
        result = plan_liquidity_acquisition(request(250), {"totally": "untrusted"}, r)
        self.assertEqual(result["decision"], "REUSE")
        self.assertFalse(result["network_required"])

    def test_087_planner_deterministic_with_unqualified_capability(self):
        a = plan_liquidity_acquisition(request(500), capability())
        b = plan_liquidity_acquisition(normalize_liquidity_request(request(500)), capability())
        self.assertEqual(canonical_plan_bytes(a), canonical_plan_bytes(b))
        self.assertEqual(a["acquisition_plan"]["plan_sha256"], b["acquisition_plan"]["plan_sha256"])

    def test_088_planner_preserves_target_250(self):
        result = plan_liquidity_acquisition(request(250), capability())
        self.assertEqual(result["acquisition_plan"]["target_bps"], "250")

    def test_089_planner_preserves_target_500(self):
        result = plan_liquidity_acquisition(request(500), capability())
        self.assertEqual(result["acquisition_plan"]["target_bps"], "500")

    def test_090_planner_network_execution_stays_inactive(self):
        result = plan_liquidity_acquisition(request(500), capability())
        self.assertEqual(result["acquisition_plan"]["network_execution"], "NOT_IMPLEMENTED_BY_S1")

    def test_091_one_observation_guard_rejects_two(self):
        with self.assertRaisesRegex(LiquidityS1Error, "MULTI_OBSERVATION_STITCHING_FORBIDDEN"):
            assert_one_coherent_provider_observation([observation(oid="a"), observation(oid="b")])

    def test_092_one_observation_guard_is_cardinality_only_not_validation(self):
        arbitrary = {"qualification_state": "QUALIFIED", "coherent_observation": True}
        self.assertIs(assert_one_coherent_provider_observation([arbitrary]), arbitrary)
        with self.assertRaises(LiquidityS1Error):
            validate_normalized_order_book(arbitrary)

    def test_093_one_observation_normalized_downstream_still_validates(self):
        raw = assert_one_coherent_provider_observation([observation()])
        book = normalize_order_book_observation(raw)
        self.assertEqual(book["schema_version"], BOOK_SCHEMA)

    def test_094_three_hop_forged_resource_to_satisfaction_to_planner_cannot_reuse(self):
        forged = forged_existing()
        sat = evaluate_resource_satisfaction(forged, request(500))
        plan = plan_liquidity_acquisition(request(500), capability(), forged)
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")
        self.assertTrue(plan["network_required"])

    def test_095_three_hop_forged_conversion_cannot_reach_resource(self):
        forged_conversion = {
            "qualified": True,
            "formula_id": "forged",
            "formula_version": "1",
            "instrument_spec_identity": "forged",
            "base_equivalent": "1",
            "quote_equivalent": "100",
        }
        with self.assertRaisesRegex(LiquidityS1Error, "CONVERSION_AUTHORITY_NOT_AVAILABLE_IN_S1"):
            qualify_quantity_semantics(
                provider_id="kraken-futures",
                instrument_id="PI_ETHUSD",
                book_kind="FUTURES_L2_BOOK",
                native_quantity="1",
                native_quantity_unit="CONTRACTS",
                conversion_authority=forged_conversion,
            )

    def test_096_three_hop_forged_quantity_cannot_reach_satisfaction(self):
        book = normalize_order_book_observation(observation())
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SEMANTICS_FIELDS_INVALID"):
            qualify_liquidity_resource(
                book,
                request(500, equivalent=True),
                age_seconds=0,
                quantity_semantics={
                    "native_quantity_preserved": True,
                    "consumer_qualified_equivalent": True,
                },
            )

    def test_097_three_hop_forged_provider_depth_never_enters_plan(self):
        cap = capability(depth="QUALIFIED")
        cap["qualified_provider_depth_parameter"] = {"name": "limit", "value": 5000}
        with self.assertRaisesRegex(LiquidityS1Error, "PROVIDER_DEPTH_QUALIFICATION_NOT_AVAILABLE_IN_S1"):
            plan_liquidity_acquisition(request(500), cap)

    def test_098_boolean_consistency_without_provenance_cannot_satisfy(self):
        forged = forged_existing()
        self.assertTrue(forged["coverage_complete_bid"])
        self.assertTrue(forged["coverage_complete_ask"])
        self.assertFalse(forged["truncated"])
        x = evaluate_resource_satisfaction(forged, request(500))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_099_resource_hash_is_not_decorative(self):
        r = legit_resource()
        stale = r["resource_sha256"]
        r["temporal_provenance"]["evaluated_at_utc"] = "2027-01-15T08:10:01Z"
        r["temporal_provenance"]["evaluation_time_ms"] = TEST_EVALUATION_TIME_MS + 1000
        r["temporal_provenance"]["derived_age_seconds"] = 1
        r["age_seconds"] = 1
        self.assertEqual(r["resource_sha256"], stale)
        with self.assertRaisesRegex(LiquidityS1Error, "RESOURCE_SHA256_MISMATCH"):
            validate_qualified_liquidity_resource(r)

    def test_100_quantity_hash_is_not_decorative(self):
        q = quantity()
        stale = q["quantity_sha256"]
        q["native_quantity"] = "13"
        self.assertEqual(q["quantity_sha256"], stale)
        with self.assertRaisesRegex(LiquidityS1Error, "QUANTITY_SHA256_MISMATCH"):
            validate_quantity_semantics(q)

    def test_101_request_hash_or_schema_never_shortcuts_validation(self):
        bad = normalize_liquidity_request(request())
        bad["freshness"] = {"max_age_seconds": -1}
        with self.assertRaisesRegex(LiquidityS1Error, "MAX_AGE_SECONDS_INVALID"):
            plan_liquidity_acquisition(bad, capability())

    def test_102_book_hash_never_shortcuts_physical_validation(self):
        book = normalize_order_book_observation(observation())
        book["bids"][0][0] = "101"
        with self.assertRaisesRegex(LiquidityS1Error, "CROSSED_OR_LOCKED_BOOK"):
            compute_side_coverage(book, request(500))

    def test_103_absence_of_conversion_is_not_zero(self):
        q = quantity()
        self.assertIsNone(q["base_equivalent"])
        self.assertIsNone(q["quote_equivalent"])
        self.assertFalse(q["consumer_qualified_equivalent"])

    def test_104_absence_of_provider_depth_is_not_zero_or_default(self):
        plan = plan_liquidity_acquisition(request(500), capability())
        bound = plan["acquisition_plan"]["provider_depth_bound"]
        self.assertEqual(bound["status"], "PROVIDER_DEPTH_BOUND_NOT_QUALIFIED")
        self.assertIsNone(bound["qualified_provider_depth_parameter"])

    def test_105_resource_request_satisfaction_is_derived_not_caller_authority(self):
        r = legit_resource()
        r["request_satisfaction"] = "UNSATISFIED"
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_106_resource_request_satisfied_boolean_is_derived(self):
        r = legit_resource()
        r["request_satisfied"] = False
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_107_resource_nested_book_tamper_rejected_even_if_top_level_untouched(self):
        r = legit_resource()
        r["normalized_book"]["bids"][1][1] = "777"
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_108_resource_nested_request_tamper_rejected(self):
        r = legit_resource()
        r["qualification_request"]["provider_url"] = "https://example.invalid"
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_109_resource_nested_quantity_identity_tamper_rejected(self):
        r = legit_resource()
        r["quantity_semantics"]["instrument_id"] = "BTCUSDT"
        x = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(x["status"], "NOT_QUALIFIED")

    def test_110_network_free_source_boundary(self):
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

    def test_111_no_second_authority_contract_flags(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        architecture = contract["architecture"]
        self.assertFalse(architecture["second_capability_authority"])
        self.assertFalse(architecture["second_provider_authority"])
        self.assertFalse(architecture["second_market_data_authority"])

    def test_112_s1_s2_s3_runtime_boundary_unchanged(self):
        contract = json.loads((ROOT / "contracts/liquidity-s1-semantic-contract-v1.json").read_text(encoding="utf-8"))
        self.assertTrue(contract["stage_boundaries"]["s1_source_implementation_performed"])
        self.assertFalse(contract["runtime_active"])
        self.assertFalse(contract["stage_boundaries"]["S2"]["active_in_this_contract_installation"])
        self.assertFalse(contract["stage_boundaries"]["S3"]["active_in_this_contract_installation"])

    def test_113_old_observation_forged_zero_age_is_rejected(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-zero-age"))
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(book, req, age_seconds=0, quantity_semantics=quantity())

    def test_114_old_observation_forged_small_age_is_rejected(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-small-age"))
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(book, req, age_seconds=1, quantity_semantics=quantity())

    def test_115_future_observation_timestamp_fails_closed(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=TEST_EVALUATION_TIME_MS + 1, oid="future"))
        with self.assertRaisesRegex(LiquidityS1Error, "OBSERVATION_TIMESTAMP_IN_FUTURE"):
            qualify_liquidity_resource(book, req, quantity_semantics=quantity())

    def test_116_missing_temporal_authority_fails_closed(self):
        book = normalize_order_book_observation(observation())
        with patch.object(current_data_transport, "_utc_now", side_effect=RuntimeError("clock unavailable")):
            with self.assertRaisesRegex(LiquidityS1Error, "TEMPORAL_AUTHORITY_UNAVAILABLE"):
                qualify_liquidity_resource(book, request(500), quantity_semantics=quantity())
        r = legit_resource()
        with patch.object(current_data_transport, "_utc_now", side_effect=RuntimeError("clock unavailable")):
            sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_117_malformed_temporal_authority_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["authority_owner"] = "caller"
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_118_negative_derived_age_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["derived_age_seconds"] = -1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_119_stale_resource_remains_non_reusable(self):
        r = legit_resource(age=601)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=600))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertIn("STALE", sat["reasons"])
        self.assertFalse(sat["reusable"])

    def test_120_exact_freshness_boundary_is_reusable(self):
        r = legit_resource(age=60)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "SATISFIED")
        self.assertTrue(sat["reusable"])

    def test_121_one_second_beyond_freshness_boundary_is_stale(self):
        r = legit_resource(age=61)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertIn("STALE", sat["reasons"])

    def test_122_tampered_observation_timestamp_with_stale_hash_fails(self):
        r = legit_resource()
        r["normalized_book"]["timestamp_ms"] -= 1000
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_123_tampered_derived_age_with_stale_hash_fails(self):
        r = legit_resource()
        r["age_seconds"] = 1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_124_tampered_temporal_provenance_with_stale_hash_fails(self):
        r = legit_resource()
        r["temporal_provenance"]["evaluated_at_utc"] = "2027-01-15T08:10:01Z"
        r["temporal_provenance"]["evaluation_time_ms"] = TEST_EVALUATION_TIME_MS + 1000
        r["temporal_provenance"]["derived_age_seconds"] = 1
        r["age_seconds"] = 1
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertIn("RESOURCE_SHA256_MISMATCH", sat["reasons"][0])

    def test_125_canonical_resource_temporal_revalidation_idempotent(self):
        r = legit_resource(age=1)
        self.assertEqual(validate_qualified_liquidity_resource(r), r)
        self.assertEqual(validate_qualified_liquidity_resource(validate_qualified_liquidity_resource(r)), r)

    def test_126_legitimate_fresh_resource_remains_reusable(self):
        r = legit_resource(age=0)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "SATISFIED")
        self.assertTrue(sat["reusable"])

    def test_127_legitimate_stale_resource_remains_non_reusable(self):
        r = legit_resource(age=61)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=60))
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])

    def test_128_planner_cannot_bypass_current_freshness_revalidation(self):
        req = request(500, max_age=60)
        old_timestamp = TEST_EVALUATION_TIME_MS - 3600 * 1000
        old_book = normalize_order_book_observation(observation(timestamp_ms=old_timestamp, oid="historically-fresh"))
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(old_timestamp)):
            historical = qualify_liquidity_resource(old_book, req, age_seconds=0, quantity_semantics=quantity())
        self.assertEqual(historical["request_satisfaction"], "SATISFIED")
        sat = evaluate_resource_satisfaction(historical, req)
        plan = plan_liquidity_acquisition(req, capability(), historical)
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])
        self.assertIn("STALE", sat["reasons"])
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")
        self.assertTrue(plan["network_required"])


    def test_129_old_observation_without_caller_age_derives_stale(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(
            observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-no-caller-age")
        )
        resource = qualify_liquidity_resource(book, req, quantity_semantics=quantity())
        self.assertEqual(resource["age_seconds"], 3600)
        self.assertEqual(resource["freshness_verdict"], "STALE")
        self.assertFalse(resource["request_satisfied"])

    def test_130_old_observation_caller_age_below_threshold_cannot_upgrade(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(
            observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="old-forged-59")
        )
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(book, req, age_seconds=59, quantity_semantics=quantity())

    def test_131_current_data_integer_second_boundary_policy_is_preserved(self):
        req = request(500, max_age=60)
        cases = [
            (59_999, "FRESH", True),
            (60_000, "FRESH", True),
            (60_001, "FRESH", True),
            (60_999, "FRESH", True),
            (61_000, "STALE", False),
        ]
        for delta_ms, verdict, reusable in cases:
            with self.subTest(delta_ms=delta_ms):
                book = normalize_order_book_observation(
                    observation(timestamp_ms=TEST_EVALUATION_TIME_MS - delta_ms, oid=f"boundary-{delta_ms}")
                )
                resource = qualify_liquidity_resource(book, req, quantity_semantics=quantity())
                self.assertEqual(resource["freshness_verdict"], verdict)
                sat = evaluate_resource_satisfaction(resource, req)
                self.assertEqual(sat["reusable"], reusable)

    def test_132_millisecond_clock_precision_does_not_false_future_same_second(self):
        base_ms = TEST_EVALUATION_TIME_MS
        clock = _evaluation_datetime(base_ms).replace(microsecond=900_000)
        book = normalize_order_book_observation(
            observation(timestamp_ms=base_ms + 500, oid="same-second-ms")
        )
        with patch.object(current_data_transport, "_utc_now", return_value=clock):
            resource = qualify_liquidity_resource(book, request(500), quantity_semantics=quantity())
        self.assertEqual(resource["temporal_provenance"]["evaluation_time_ms"], base_ms + 900)
        self.assertEqual(resource["age_seconds"], 0)

    def test_133_naive_canonical_clock_fails_closed(self):
        book = normalize_order_book_observation(observation())
        naive = datetime(2027, 1, 15, 8, 10, 0)
        with patch.object(current_data_transport, "_utc_now", return_value=naive):
            with self.assertRaisesRegex(LiquidityS1Error, "TEMPORAL_AUTHORITY_NOT_UTC"):
                qualify_liquidity_resource(book, request(500), quantity_semantics=quantity())

    def test_134_non_utc_canonical_clock_fails_closed(self):
        book = normalize_order_book_observation(observation())
        non_utc = datetime(2027, 1, 15, 10, 10, 0, tzinfo=timezone(timedelta(hours=2)))
        with patch.object(current_data_transport, "_utc_now", return_value=non_utc):
            with self.assertRaisesRegex(LiquidityS1Error, "TEMPORAL_AUTHORITY_NOT_UTC"):
                qualify_liquidity_resource(book, request(500), quantity_semantics=quantity())

    def test_135_malformed_persisted_evaluation_time_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["evaluated_at_utc"] = "2027-01-15T10:10:00+02:00"
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_136_evaluation_millisecond_inconsistency_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["evaluation_time_ms"] += 1000
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_137_missing_temporal_provenance_fails_closed(self):
        r = legit_resource()
        del r["temporal_provenance"]
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_138_unknown_temporal_provenance_field_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["caller_fresh"] = True
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_139_forged_authority_owner_recomputed_hash_still_fails_closed(self):
        r = legit_resource()
        r["temporal_provenance"]["authority_owner"] = "caller"
        material = dict(r)
        material.pop("resource_sha256")
        r["resource_sha256"] = sha256_canonical_json(material)
        sat = evaluate_resource_satisfaction(r, request(250))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_140_attacker_recomputed_structural_hash_cannot_create_current_freshness(self):
        req = request(500, max_age=60)
        r = legit_resource(age=3600)
        observation_ms = r["normalized_book"]["timestamp_ms"]
        historical = _evaluation_datetime(observation_ms)
        r["temporal_provenance"] = {
            "authority_owner": r["temporal_provenance"]["authority_owner"],
            "evaluated_at_utc": historical.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "evaluation_time_ms": observation_ms,
            "observation_timestamp_ms": observation_ms,
            "derived_age_seconds": 0,
        }
        r["age_seconds"] = 0
        r["freshness_verdict"] = "FRESH"
        r["request_satisfaction"] = "SATISFIED"
        r["request_satisfied"] = True
        material = dict(r)
        material.pop("resource_sha256")
        r["resource_sha256"] = sha256_canonical_json(material)
        validate_qualified_liquidity_resource(r)
        sat = evaluate_resource_satisfaction(r, req)
        plan = plan_liquidity_acquisition(req, capability(), r)
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])
        self.assertIn("STALE", sat["reasons"])
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")

    def test_141_resource_satisfaction_uses_one_coherent_clock_instant(self):
        r = legit_resource(age=0)
        clock = _evaluation_datetime()
        with patch.object(current_data_transport, "_utc_now", side_effect=[clock, clock]) as mocked:
            sat = evaluate_resource_satisfaction(r, request(250))
        self.assertTrue(sat["reusable"])
        self.assertEqual(mocked.call_count, 1)

    def test_142_planner_uses_one_coherent_clock_instant(self):
        r = legit_resource(age=0)
        clock = _evaluation_datetime()
        with patch.object(current_data_transport, "_utc_now", side_effect=[clock, clock]) as mocked:
            plan = plan_liquidity_acquisition(request(250), capability(), r)
        self.assertEqual(plan["decision"], "REUSE")
        self.assertEqual(mocked.call_count, 1)

    def test_143_repeated_planner_evaluation_changes_only_with_current_time(self):
        req = request(500, max_age=60)
        base_ms = TEST_EVALUATION_TIME_MS - 3600 * 1000
        book = normalize_order_book_observation(observation(timestamp_ms=base_ms, oid="time-advance"))
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(base_ms)):
            historical = qualify_liquidity_resource(book, req, age_seconds=0, quantity_semantics=quantity())
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(base_ms + 60_999)):
            before = plan_liquidity_acquisition(req, capability(), historical)
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(base_ms + 61_000)):
            after = plan_liquidity_acquisition(req, capability(), historical)
        self.assertEqual(before["decision"], "REUSE")
        self.assertEqual(after["decision"], "ACQUISITION_REQUIRED")

    def test_144_serialized_resource_is_revalidated_against_current_time(self):
        req = request(500, max_age=60)
        old_ms = TEST_EVALUATION_TIME_MS - 3600 * 1000
        book = normalize_order_book_observation(observation(timestamp_ms=old_ms, oid="serialized-old"))
        with patch.object(current_data_transport, "_utc_now", return_value=_evaluation_datetime(old_ms)):
            historical = qualify_liquidity_resource(book, req, age_seconds=0, quantity_semantics=quantity())
        round_trip = json.loads(json.dumps(historical))
        sat = evaluate_resource_satisfaction(round_trip, req)
        self.assertEqual(sat["status"], "UNSATISFIED")
        self.assertFalse(sat["reusable"])

    def test_145_extremely_old_timestamp_is_stale_not_fresh(self):
        req = request(500, max_age=60)
        book = normalize_order_book_observation(observation(timestamp_ms=1, oid="epoch-old"))
        resource = qualify_liquidity_resource(book, req, quantity_semantics=quantity())
        self.assertEqual(resource["freshness_verdict"], "STALE")
        self.assertFalse(evaluate_resource_satisfaction(resource, req)["reusable"])

    def test_146_forged_freshness_verdict_recomputed_hash_cannot_override_semantics(self):
        r = legit_resource(age=601)
        r["freshness_verdict"] = "FRESH"
        material = dict(r)
        material.pop("resource_sha256")
        r["resource_sha256"] = sha256_canonical_json(material)
        sat = evaluate_resource_satisfaction(r, request(250, max_age=600))
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])

    def test_147_public_temporal_consumers_fail_closed_on_forged_old_resource(self):
        req = request(500, max_age=60)
        old_book = normalize_order_book_observation(
            observation(timestamp_ms=TEST_EVALUATION_TIME_MS - 3600 * 1000, oid="public-old")
        )
        with self.assertRaisesRegex(LiquidityS1Error, "CALLER_AGE_SECONDS_MISMATCH"):
            qualify_liquidity_resource(old_book, req, age_seconds=0, quantity_semantics=quantity())
        forged = legit_resource(age=3600)
        forged["temporal_provenance"]["authority_owner"] = "caller"
        with self.assertRaises(LiquidityS1Error):
            validate_qualified_liquidity_resource(forged)
        sat = evaluate_resource_satisfaction(forged, req)
        plan = plan_liquidity_acquisition(req, capability(), forged)
        self.assertEqual(sat["status"], "NOT_QUALIFIED")
        self.assertFalse(sat["reusable"])
        self.assertEqual(plan["decision"], "ACQUISITION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
