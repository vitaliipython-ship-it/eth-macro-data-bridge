from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import acquisition_core as ac
import collector
import deribit_history
import intelligence

BASE_MS = int(datetime(2026, 8, 17, 19, 0, tzinfo=timezone.utc).timestamp() * 1000)


def binance_native(offset_minutes: int = 5):
    ts = BASE_MS - offset_minutes * 60_000
    return [ts, "1900", "1910", "1890", "1905", "12.5", BASE_MS - 1, "23812.5", 42, "7.1", "13520.5"]


def kraken_native(offset_minutes: int = 5):
    ts = BASE_MS - offset_minutes * 60_000
    return [ts, "1900", "1910", "1890", "1905", "1902.5", "12.5", 42, BASE_MS]


class ProviderContractCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.core = ac.CanonicalAcquisitionCore()

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self, capability):
        return self.core.collect(capability, expected_ms=BASE_MS, cycle_id="fixture-cycle", staging_root=self.root)

    def test_shared_provider_logic_identity(self):
        self.assertIs(ac.binance, collector.binance)
        self.assertIs(ac.kraken, collector.kraken)
        self.assertIs(ac.collect_binance, intelligence.collect_binance)
        self.assertIs(ac.collect_kraken, intelligence.collect_kraken)
        self.assertIs(ac.collect_deribit_perpetual, intelligence.collect_deribit_perpetual)
        self.assertIs(ac.collect_deribit_history, deribit_history.collect_deribit_history)
        self.assertIs(ac.collect_options, intelligence.collect_options)
        self.assertIs(ac.collect_liquidity, intelligence.collect_liquidity)

    @patch("acquisition_core.binance")
    def test_binance_spot_rich_native_mapping(self, mock_binance):
        row = binance_native()
        mock_binance.return_value = ("https://spot.fixture", [], [row])
        result = self.collect("binance-spot.m5")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["observations"]), 3)
        eth = next(o for o in result["observations"] if o["series_id"] == "spot.binance-spot.ETHUSDT.ohlcv.5m")
        self.assertEqual(eth["value"]["base_volume"], "12.5")
        self.assertEqual(eth["value"]["quote_volume"], "23812.5")
        self.assertEqual(eth["value"]["trade_count"], 42)
        self.assertEqual(eth["value"]["taker_buy_base_volume"], "7.1")
        self.assertEqual(eth["value"]["taker_buy_quote_volume"], "13520.5")
        self.assertEqual(eth["value"]["close_time_ms"], BASE_MS - 1)
        self.assertTrue(eth["value"]["closed"])
        self.assertEqual(eth["d9_target"], "FIXED_GRID")

    @patch("acquisition_core.binance")
    def test_binance_all_native_timeframe_capabilities_use_provider_interval(self, mock_binance):
        for capability, interval, minutes in (("binance-spot.15m", "15m", 15), ("binance-spot.1h", "1h", 60), ("binance-spot.4h", "4h", 240), ("binance-spot.1d", "1d", 1440), ("binance-spot.1w", "1w", 10080)):
            ts = BASE_MS - minutes * 60_000
            row = [ts, "1", "2", "0.5", "1.5", "10", BASE_MS - 1, "15", 3, "4", "5"]
            mock_binance.return_value = ("https://spot.fixture", [], [row])
            result = self.collect(capability)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(all(o["series_id"].endswith("." + interval) for o in result["observations"]))
            self.assertEqual(mock_binance.call_args.args[1], interval)

    @patch("acquisition_core.kraken")
    def test_kraken_spot_rich_native_mapping(self, mock_kraken):
        row = kraken_native()
        mock_kraken.return_value = ("XETHZUSD", [], [row])
        result = self.collect("kraken-spot.m5")
        self.assertEqual(result["status"], "PASS")
        eth = next(o for o in result["observations"] if o["series_id"] == "spot.kraken-spot.ETHUSD.ohlcv.5m")
        self.assertEqual(eth["value"]["vwap"], "1902.5")
        self.assertEqual(eth["value"]["volume"], "12.5")
        self.assertEqual(eth["value"]["trade_count"], 42)
        self.assertEqual(eth["value"]["close_time_ms"], BASE_MS)

    @patch("acquisition_core.kraken")
    def test_kraken_all_native_timeframe_capabilities_use_provider_interval(self, mock_kraken):
        for capability, interval, minutes in (("kraken-spot.15m", "15m", 15), ("kraken-spot.1h", "1h", 60), ("kraken-spot.4h", "4h", 240), ("kraken-spot.1d", "1d", 1440), ("kraken-spot.1w", "1w", 10080)):
            ts = BASE_MS - minutes * 60_000
            row = [ts, "1", "2", "0.5", "1.5", "1.2", "10", 3, BASE_MS]
            mock_kraken.return_value = ("XETHZUSD", [], [row])
            result = self.collect(capability)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(all(o["series_id"].endswith("." + interval) for o in result["observations"]))
            self.assertEqual(mock_kraken.call_args.args[1], interval)

    @patch.object(ac.CanonicalAcquisitionCore, "_binance_usdm_supplemental")
    @patch("acquisition_core.collect_binance")
    def test_binance_usdm_reuses_fetched_oi_and_funding_history(self, mock_collect, mock_supplemental):
        def fake_collect(_get, _now):
            p = Path("perp.json")
            p.write_text(json.dumps({"records": [[BASE_MS - 300_000, "1", "2", "0.5", "1.5", "10", BASE_MS - 1, "15", 4, "5", "6"]]}))
            return {"status": "PASS", "route": "https://fapi.fixture", "instruments": {"ETHUSDT": {
                "latest_kline_path": p.as_posix(),
                "latest": {"timestamp_ms": BASE_MS, "mark_price": "1905", "index_price": "1904", "basis_bps": "5.25", "funding_rate": "0.0001", "open_interest": "1000"},
                "open_interest_history_rows": [
                    {"timestamp": BASE_MS - 600_000, "sumOpenInterest": "100", "sumOpenInterestValue": "190000", "instrument": "ETHUSDT", "known_at": ac._iso(BASE_MS), "provenance": {"source_endpoint": "openInterestHist"}},
                    {"timestamp": BASE_MS - 300_000, "sumOpenInterest": "101", "sumOpenInterestValue": "192000", "instrument": "ETHUSDT", "known_at": ac._iso(BASE_MS), "provenance": {"source_endpoint": "openInterestHist"}},
                ],
                "funding_history_rows": [
                    {"fundingTime": BASE_MS - 8 * 3600_000, "fundingRate": "0.0001", "markPrice": "1900", "instrument": "ETHUSDT", "known_at": ac._iso(BASE_MS), "provenance": {"source_endpoint": "fundingRate"}},
                    {"fundingTime": BASE_MS, "fundingRate": "0.0002", "markPrice": "1905", "instrument": "ETHUSDT", "known_at": ac._iso(BASE_MS), "provenance": {"source_endpoint": "fundingRate"}},
                ],
            }}}
        mock_collect.side_effect = fake_collect
        mock_supplemental.return_value = []
        result = self.collect("binance-usdm.m5-current")
        ids = [o["series_id"] for o in result["observations"]]
        self.assertEqual(ids.count("derivatives.binance-usdm.ETHUSDT.open-interest-history.5m"), 2)
        self.assertEqual(ids.count("derivatives.binance-usdm.ETHUSDT.funding-history"), 2)
        oi = next(o for o in result["observations"] if o["series_id"].endswith("open-interest-history.5m"))
        self.assertIn("sumOpenInterestValue", oi["value"])
        funding = next(o for o in result["observations"] if o["series_id"].endswith("funding-history"))
        self.assertIn("markPrice", funding["value"])
        mock_collect.assert_called_once()

    @patch("acquisition_core.collect_kraken")
    def test_kraken_futures_promotes_all_bounded_rows_and_revision_class(self, mock_collect):
        mock_collect.return_value = {"status": "PASS", "instruments": {"PI_ETHUSD": {"metrics": {
            "open-interest": {"eligible_rows": [[BASE_MS - 600_000, {"value": 121}], [BASE_MS - 300_000, {"value": 123}]]},
            "spreads": {"eligible_rows": [[BASE_MS - 600_000, {"bid": 1, "ask": 2}], [BASE_MS - 300_000, {"bid": 1.1, "ask": 2.1}]]},
        }}}}
        result = self.collect("kraken-futures.analytics")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["observations"]), 4)
        spread_rows = [o for o in result["observations"] if o["series_id"].endswith(".spreads")]
        self.assertEqual(len(spread_rows), 2)
        self.assertTrue(all(o["revision_classification"] == "PROVIDER_REVISABLE_SNAPSHOT" for o in spread_rows))
        self.assertTrue(all("revision_classification" not in o for o in result["observations"] if o["series_id"].endswith(".open-interest")))

    @patch("acquisition_core.collect_deribit_perpetual")
    def test_deribit_perpetual_runtime_mapping(self, mock_collect):
        mock_collect.return_value = {"status": "PASS", "instruments": {"ETH-PERPETUAL": {"timestamp_ms": BASE_MS, "mark_price": 1905}}}
        result = self.collect("deribit-perpetual.current")
        self.assertEqual(result["observations"][0]["series_id"], "derivatives.deribit-perpetual.ETH-PERPETUAL.current")

    @patch("acquisition_core.collect_deribit_history")
    def test_deribit_perpetual_h1_promotes_funding_and_ohlcv_rows(self, mock_history):
        mock_history.return_value = {"status": "PASS", "resources": [
            {"instrument": "ETH-PERPETUAL", "metric": "funding", "columns": list(ac.FUNDING_COLUMNS), "path": "funding.json", "projection_overlap_ms": 86400000, "projection_rows": [[BASE_MS - 3600_000, "1900", "0.001", "0.0001", "1899"], [BASE_MS, "1905", "0.002", "0.0002", "1900"]]},
            {"instrument": "ETH-PERPETUAL", "metric": "OHLCV-1h", "columns": list(ac.OHLCV_COLUMNS), "path": "ohlcv.json", "projection_overlap_ms": 86400000, "projection_rows": [[BASE_MS - 3600_000, "1890", "1910", "1880", "1900", "100"]]},
        ]}
        result = self.collect("deribit-perpetual.h1-history")
        ids = [o["series_id"] for o in result["observations"]]
        self.assertEqual(ids.count("derivatives.deribit-perpetual.ETH-PERPETUAL.funding.1h"), 2)
        self.assertEqual(ids.count("derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h"), 1)
        self.assertTrue(all(o["finality"] == "FINALIZED" for o in result["observations"]))

    @patch("acquisition_core.collect_liquidity")
    @patch("acquisition_core.collect_options")
    def test_deribit_options_promotes_all_dvol_and_same_execution_selected_books(self, mock_options, mock_liquidity):
        def fake_options(_get, _now):
            p = Path("surface.json")
            p.write_text(json.dumps({"schema_version": "fixture", "selected_greeks": [{"instrument_name": "ETH-28AUG26-2000-C"}]}))
            return {"status": "PASS", "latest_surface": p.as_posix(), "dvol_rows": [[BASE_MS - 2 * 3600_000, "30", "31", "29", "30.5"], [BASE_MS - 3600_000, "31", "32", "30", "31.5"]], "dvol_overlap_ms": 86400000, "selected_option_names": ["ETH-28AUG26-2000-C"]}
        mock_options.side_effect = fake_options
        mock_liquidity.return_value = {"status": "PASS", "snapshots": [
            {"provider": "deribit", "instrument": "ETH-PERPETUAL", "timestamp_ms": BASE_MS, "depth": {}},
            {"provider": "deribit", "instrument": "ETH-28AUG26-2000-C", "timestamp_ms": BASE_MS, "depth": {"10": {}}},
        ]}
        result = self.collect("deribit-options.surface-dvol")
        self.assertEqual(result["status"], "PASS")
        ids = [o["series_id"] for o in result["observations"]]
        self.assertEqual(ids.count("options.deribit-options.ETH.dvol.1h"), 2)
        self.assertIn("liquidity.deribit-options.ETH-28AUG26-2000-C.selected-book", ids)
        selected = next(o for o in result["observations"] if o["series_id"].endswith("selected-book"))
        self.assertEqual(selected["provenance"]["selection_source"], "collect_options.selected_option_names")
        self.assertEqual(mock_liquidity.call_args.args[2], ["ETH-28AUG26-2000-C"])
        mock_options.assert_called_once()

    @patch("acquisition_core.collect_liquidity")
    def test_liquidity_current_remains_general_contour(self, mock_collect):
        def fake(_get, _now, _selected, _kraken_status):
            p = Path("liquidity.json"); p.write_text(json.dumps({"schema_version": "fixture", "snapshots": []}))
            return {"status": "PASS", "latest_path": p.as_posix()}
        mock_collect.side_effect = fake
        result = self.collect("liquidity.current")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["observations"][0]["series_id"], "liquidity.orderbook-snapshots")
        self.assertEqual(mock_collect.call_args.args[2], [])


if __name__ == "__main__":
    unittest.main()
