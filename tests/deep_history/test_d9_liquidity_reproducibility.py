from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import history_access
import resolution_v2
from event_window import nearest_v4
from intelligence import (
    LiquidityProfileError,
    depth_metrics,
    deterministic_legacy_liquidity_profiles,
    deterministic_liquidity_profile,
    deterministic_liquidity_summary,
    deterministic_profile_from_durable_observation,
    liquidity_derivation_policy_identity,
)
from liquidity_s1_runtime import normalize_order_book_observation, qualify_quantity_semantics
from sampled_history import durable_partition_path, persist_sampled_intelligence


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


class DeterministicProfileSummaryTests(unittest.TestCase):
    def _canonical_source(self):
        timestamp = 1788393600000
        book = normalize_order_book_observation({
            "observation_id": "profile-summary-fixture",
            "provider_id": "binance-spot",
            "instrument_id": "ETHUSDT",
            "book_kind": "L2_LEVEL_BOOK",
            "source_representation": "RAW",
            "timestamp_ms": timestamp,
            "bids": [["99.99", "10000"], ["99.9", "10000"], ["99.75", "10000"], ["99.5", "10000"]],
            "asks": [["100.01", "10000"], ["100.1", "10000"], ["100.25", "10000"], ["100.5", "10000"]],
        })
        quantity = qualify_quantity_semantics(
            provider_id="binance-spot",
            instrument_id="ETHUSDT",
            book_kind="L2_LEVEL_BOOK",
            native_quantity="80000",
            native_quantity_unit="BASE_ASSET",
        )
        coverage = {
            "history_target_bps": "50",
            "coverage_complete_bid": True,
            "coverage_complete_ask": True,
            "truncated": False,
            "extrapolation_allowed": False,
        }
        return timestamp, book, quantity, coverage

    def _valid_successor_observation(self):
        partitions = sorted(
            (ROOT / "history/liquidity-orderbook-snapshots").rglob("observations.json"),
            reverse=True,
        )
        self.assertTrue(partitions)
        for partition in partitions:
            payload = json.loads(partition.read_text(encoding="utf-8"))
            for observation in payload.get("observations", []):
                if not isinstance(observation, dict):
                    continue
                try:
                    history_access._v2._validate_g2b_observation(observation)
                except history_access._v2.HistoryAccessV2Error:
                    continue
                return observation
        self.fail("repository has no valid G2-B successor durable observation fixture")

    def test_profile_formula_identity_and_summary_are_deterministic(self):
        timestamp, book, quantity, coverage = self._canonical_source()
        profile = deterministic_liquidity_profile(
            book,
            source_known_at=_iso(timestamp + 1000),
            quantity_semantics=quantity,
            source_coverage=coverage,
        )
        replay = deterministic_liquidity_profile(
            json.loads(json.dumps(book)),
            source_known_at=_iso(timestamp + 1000),
            quantity_semantics=json.loads(json.dumps(quantity)),
            source_coverage=json.loads(json.dumps(coverage)),
        )
        self.assertEqual(profile, replay)
        self.assertEqual(profile["mid_price"], "100")
        self.assertEqual(profile["spread_absolute"], "0.02")
        self.assertEqual(profile["spread_bps"], "2")
        self.assertEqual(profile["depth_10bps_bid_quote"], "1998900")
        self.assertEqual(profile["depth_10bps_ask_quote"], "2001100")
        self.assertEqual(profile["depth_25bps_bid_quote"], "2996400")
        self.assertEqual(profile["depth_25bps_ask_quote"], "3003600")
        self.assertEqual(profile["depth_50bps_bid_quote"], "3991400")
        self.assertEqual(profile["depth_50bps_ask_quote"], "4008600")
        self.assertEqual(profile["imbalance_10bps"], "-0.00055")
        self.assertEqual(profile["imbalance_25bps"], "-0.0012")
        self.assertEqual(profile["imbalance_50bps"], "-0.00215")
        self.assertEqual(profile["slippage_buy_10000"], {"vwap": "100.01", "impact_bps": "1", "availability_state": "AVAILABLE"})
        self.assertEqual(profile["slippage_sell_10000"], {"vwap": "99.99", "impact_bps": "1", "availability_state": "AVAILABLE"})
        self.assertEqual(profile["slippage_buy_100000"], {"vwap": "100.01", "impact_bps": "1", "availability_state": "AVAILABLE"})
        self.assertEqual(profile["slippage_sell_100000"], {"vwap": "99.99", "impact_bps": "1", "availability_state": "AVAILABLE"})
        self.assertEqual(profile["slippage_buy_1000000"], {"vwap": "100.01", "impact_bps": "1", "availability_state": "AVAILABLE"})
        self.assertEqual(profile["slippage_sell_1000000"], {"vwap": "99.98999099189270343308978081", "impact_bps": "1.000900810729656691021919", "availability_state": "AVAILABLE"})
        policy = liquidity_derivation_policy_identity()
        self.assertEqual(profile["derivation_policy_identity"], policy)
        self.assertEqual(policy, liquidity_derivation_policy_identity())
        self.assertEqual(len(profile["profile_sha256"]), 64)

        summary = deterministic_liquidity_summary(profile)
        self.assertEqual(summary, deterministic_liquidity_summary(replay))
        self.assertEqual(summary["profile_sha256"], profile["profile_sha256"])
        self.assertEqual(len(summary["summary_sha256"]), 64)
        self.assertNotIn("depth_10bps_bid_quote", summary)
        self.assertNotIn("imbalance_10bps", summary)
        self.assertNotIn("slippage_buy_10000", summary)

    def test_source_hash_binary_float_and_profile_masquerade_fail_closed(self):
        timestamp, book, quantity, coverage = self._canonical_source()
        tampered = json.loads(json.dumps(book))
        tampered["bids"][0][0] = "99.98"
        with self.assertRaises(LiquidityProfileError):
            deterministic_liquidity_profile(
                tampered,
                source_known_at=_iso(timestamp + 1000),
                quantity_semantics=quantity,
                source_coverage=coverage,
            )
        binary_float = json.loads(json.dumps(book))
        binary_float["bids"][0][0] = 99.99
        with self.assertRaises(LiquidityProfileError):
            deterministic_liquidity_profile(
                binary_float,
                source_known_at=_iso(timestamp + 1000),
                quantity_semantics=quantity,
                source_coverage=coverage,
            )
        profile = deterministic_liquidity_profile(
            book,
            source_known_at=_iso(timestamp + 1000),
            quantity_semantics=quantity,
            source_coverage=coverage,
        )
        masquerade = json.loads(json.dumps(profile))
        masquerade["representation"] = "NORMALIZED"
        with self.assertRaises(LiquidityProfileError):
            deterministic_liquidity_summary(masquerade)

    def test_partial_truncated_and_unproved_legacy_quantity_remain_fail_closed(self):
        timestamp = 1788393600000
        payload = {
            "schema_version": "1.0.0",
            "timestamp_ms": timestamp,
            "snapshots": [{
                "schema_version": "1.0.0",
                "provider": "deribit",
                "instrument": "ETH-TEST-C",
                "timestamp_ms": timestamp,
                "native_amount_unit": "UNDERLYING_COIN",
                "normalized_notional_unit": "USD",
                "normalization_formula": "amount_underlying*option_price_underlying*underlying_index_usd",
                "normalization_confidence": "HIGH",
                "raw": {
                    "bids": [["0.05", "10"], ["0.04", "10"]],
                    "asks": [["0.06", "10"], ["0.07", "10"]],
                },
                "depth": {"10": {"status": "TRUNCATED"}},
            }],
        }
        profiles = deterministic_legacy_liquidity_profiles(
            payload,
            legacy_resource_sha256="a" * 64,
            source_known_at=_iso(timestamp + 1000),
        )
        self.assertEqual(len(profiles), 1)
        profile = profiles[0]
        self.assertEqual(profile["availability_state"]["top_of_book"], "AVAILABLE")
        self.assertEqual(profile["availability_state"]["quantity_metrics"], "UNAVAILABLE_QUANTITY_SEMANTICS")
        self.assertIsNone(profile["depth_10bps_bid_quote"])
        self.assertEqual(profile["depth_10bps_status"], "UNAVAILABLE_QUANTITY_SEMANTICS")
        self.assertEqual(profile["slippage_buy_10000"]["availability_state"], "UNAVAILABLE_QUANTITY_SEMANTICS")
        self.assertTrue(profile["coverage_fidelity"]["truncated"])
        self.assertFalse(profile["coverage_fidelity"]["extrapolation_allowed"])
        self.assertEqual(deterministic_liquidity_summary(profile)["quantity_semantics_status"], "UNAVAILABLE")

    def test_successor_current_formula_parity_preserves_source_time_and_known_at(self):
        timestamp, book, quantity, coverage = self._canonical_source()
        known_at = _iso(timestamp + 1000)
        current = deterministic_liquidity_profile(
            book,
            source_known_at=known_at,
            quantity_semantics=quantity,
            source_coverage=coverage,
            source_schema="liquidity-durable-l2-observation/1.0.0",
        )
        durable = {
            "schema_version": "liquidity-durable-l2-observation/1.0.0",
            "observation_time_ms": timestamp,
            "known_at_utc": known_at,
            "provider_id": book["provider_id"],
            "instrument_id": book["instrument_id"],
            "book_kind": book["book_kind"],
            "observation_id": book["observation_id"],
            "observation_sha256": book["observation_sha256"],
            "normalized_book": book,
            "quantity_semantics": quantity,
            "coverage": coverage,
        }
        historical = deterministic_profile_from_durable_observation(durable)
        formula_fields = (
            "mid_price",
            "spread_absolute",
            "spread_bps",
            "depth_10bps_bid_quote",
            "depth_10bps_ask_quote",
            "depth_25bps_bid_quote",
            "depth_25bps_ask_quote",
            "depth_50bps_bid_quote",
            "depth_50bps_ask_quote",
            "depth_10bps_status",
            "depth_25bps_status",
            "depth_50bps_status",
            "imbalance_10bps",
            "imbalance_25bps",
            "imbalance_50bps",
            "slippage_buy_10000",
            "slippage_sell_10000",
            "slippage_buy_100000",
            "slippage_sell_100000",
            "slippage_buy_1000000",
            "slippage_sell_1000000",
            "availability_state",
            "quantity_semantics_status",
            "derivation_policy_identity",
        )
        for field in formula_fields:
            self.assertEqual(current[field], historical[field], field)
        self.assertEqual(current["coverage_fidelity"]["source_class"], "CANONICAL_NORMALIZED_L2")
        self.assertEqual(historical["coverage_fidelity"]["source_class"], "SUCCESSOR_DURABLE_L2")
        self.assertEqual(historical["source_market_observation_time"], timestamp)
        self.assertEqual(historical["source_known_at"], known_at)

    def test_public_reader_binds_profile_and_summary_on_existing_g2b_route(self):
        observation = self._valid_successor_observation()
        start = observation["observation_time_ms"]
        base_plan = resolution_v2.resolve_capability_v2(
            resolution_v2.G2B_FAMILY,
            _iso(start),
            _iso(start + 1),
            root=ROOT,
        )
        with tempfile.TemporaryDirectory() as temp:
            for representation in ("PROFILE", "SUMMARY"):
                bound = history_access.bind_liquidity_representation(base_plan, representation)
                self.assertEqual(
                    bound["authority"]["liquidity_derivation"]["storage_model"],
                    "ON_READ_DERIVATION",
                )
                rows, diagnostics = history_access.materialize_resolution_plan_any(
                    bound,
                    cache_dir=Path(temp) / representation.lower(),
                )
                self.assertTrue(rows)
                self.assertEqual(diagnostics["requested_representation"], representation)
                self.assertEqual(
                    diagnostics["derivation_policy_identity"],
                    bound["authority"]["liquidity_derivation"]["derivation_policy_identity"],
                )
                self.assertTrue(all(row["value"]["representation"] == representation for row in rows))
                self.assertTrue(all(row["value"]["source_market_observation_time"] == row["timestamp_ms"] for row in rows))


class D9LiquidityReproducibilityTests(unittest.TestCase):
    def test_order_book_snapshot_preserves_every_level_used_by_calculation(self):
        bids = [[str(2000 - index), str(1 + index / 100)] for index in range(100)]
        asks = [[str(2001 + index), str(1 + index / 100)] for index in range(100)]
        result = depth_metrics({"bids": bids, "asks": asks}, 1786965000000, "binance-spot", "ETHUSDT")
        self.assertEqual(result["raw_level_count"], {"bids": 100, "asks": 100})
        self.assertEqual(len(result["raw"]["bids"]), 100)
        self.assertEqual(len(result["raw"]["asks"]), 100)
        self.assertEqual(result["raw"]["bids"][-1], bids[-1])
        self.assertEqual(result["raw"]["asks"][-1], asks[-1])

    def test_snapshot_does_not_invent_binance_usdm_collection(self):
        result = depth_metrics(
            {"bids": [["2000", "1"]], "asks": [["2001", "1"]]},
            1786965000000,
            "binance-spot",
            "ETHUSDT",
        )
        self.assertEqual(result["provider"], "binance-spot")
        self.assertNotEqual(result["provider"], "binance-usdm")

    def test_g2a_successor_partition_is_invisible_to_legacy_nearest_v4_snapshot_decoder(self):
        timestamp_ms = 1786965000000
        event_ms = timestamp_ms + 1_000
        legacy_payload = {
            "timestamp_ms": timestamp_ms,
            "snapshots": [{"provider": "binance-spot", "instrument": "ETHUSDT"}],
        }
        successor_payload = {
            "schema_version": "liquidity-durable-l2-observation-partition/1.0.0",
            "date_utc": "2026-08-17",
            "history_family": "liquidity.orderbook-snapshots",
            "observations": [
                {
                    "provider_id": "binance-spot",
                    "instrument_id": "ETHUSDT",
                    "book_kind": "L2_LEVEL_BOOK",
                    "observation_time_ms": timestamp_ms,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "liquidity/snapshots/2026/08/17" / f"{timestamp_ms}.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(json.dumps(legacy_payload) + "\n", encoding="utf-8")
            successor = durable_partition_path(timestamp_ms, root=root)
            successor.parent.mkdir(parents=True, exist_ok=True)
            successor.write_text(json.dumps(successor_payload) + "\n", encoding="utf-8")
            self.assertTrue(successor.as_posix().endswith("history/liquidity-orderbook-snapshots/2026/08/17/observations.json"))
            self.assertNotIn("/liquidity/snapshots/", successor.as_posix())

            previous = Path.cwd()
            try:
                os.chdir(root)
                package = nearest_v4(event_ms)
            finally:
                os.chdir(previous)

            self.assertIsNotNone(package["liquidity"])
            assert package["liquidity"] is not None
            self.assertEqual(package["liquidity"]["source_timestamp"], timestamp_ms)
            self.assertEqual(package["liquidity"]["data"], legacy_payload)
            self.assertEqual(package["liquidity"]["source_path"], legacy.relative_to(root).as_posix())

    def test_g2a_writer_keeps_durable_records_out_of_d9_sampled_ledger_until_g2b(self):
        now = 1786965000000
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            option_path = root / "options/snapshots/2026/08/17" / f"{now}.json"
            liquidity_path = root / "liquidity/snapshots/2026/08/17" / f"{now}.json"
            option_path.parent.mkdir(parents=True, exist_ok=True)
            liquidity_path.parent.mkdir(parents=True, exist_ok=True)
            option_path.write_text("{}\n", encoding="utf-8")
            liquidity_path.write_text("{}\n", encoding="utf-8")
            intelligence = {
                "derivatives": {
                    "providers": {
                        "deribit-perpetual": {
                            "status": "PASS",
                            "instruments": {
                                "ETH-PERPETUAL": {
                                    "timestamp_ms": now - 1000,
                                    "mark_price": 2000,
                                    "index_price": 1999,
                                    "open_interest": 10,
                                    "current_funding": 0.0,
                                    "funding_8h": 0.0,
                                    "volume_24h": 100,
                                    "volume_usd_24h": 200000,
                                }
                            },
                        }
                    }
                },
                "options": {"providers": {"deribit": {"status": "PASS", "latest_surface": option_path.as_posix()}}},
                "liquidity": {"collection": {"status": "PASS", "latest_path": liquidity_path.as_posix()}},
            }
            fake_g2a = {
                "status": "PASS",
                "acquisition_route": "S1_TO_S2_TO_S3",
                "capability_count": 6,
                "records": [],
                "persistence": [],
            }
            previous = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch("sampled_history.persist_g2a_baseline", return_value=fake_g2a):
                    result = persist_sampled_intelligence(
                        intelligence,
                        expected_ms=now,
                        started_ms=now,
                        completed_ms=now + 2000,
                        target_cadence_seconds=3600,
                        enable_g2a=True,
                    )
            finally:
                os.chdir(previous)

            self.assertEqual(result["g2a"], fake_g2a)
            self.assertEqual(result["run_count"], 3)
            ledger = json.loads((root / result["ledger_path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(ledger["runs"]), 3)
            self.assertEqual(
                {row["series_or_capability"] for row in ledger["runs"]},
                {
                    "derivatives.deribit-perpetual.current-snapshot",
                    "options.deribit-options.ETH.surface-snapshots",
                    "liquidity.orderbook-snapshots",
                },
            )
            liquidity_row = next(
                row for row in ledger["runs"]
                if row["series_or_capability"] == "liquidity.orderbook-snapshots"
            )
            self.assertEqual(liquidity_row["run_id"], f"liquidity-orderbook:{now}")
            self.assertEqual(liquidity_row["provider"], "multi-provider")
            self.assertFalse(any(str(row["run_id"]).startswith("liquidity-g2a:") for row in ledger["runs"]))


if __name__ == "__main__":
    unittest.main()
