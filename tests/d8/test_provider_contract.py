from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import acquisition_core as ac
import collector
import intelligence

BASE_MS = int(datetime(2026, 8, 17, 19, 0, tzinfo=timezone.utc).timestamp() * 1000)


def closed_row(offset_minutes: int = 5):
    ts = BASE_MS - offset_minutes * 60_000
    return [ts, "1900", "1910", "1890", "1905", "12.5", True]


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
        self.assertIs(ac.collect_options, intelligence.collect_options)
        self.assertIs(ac.collect_liquidity, intelligence.collect_liquidity)

    @patch("acquisition_core.binance")
    def test_binance_spot_runtime_mapping_and_legacy_parity(self, mock_binance):
        row = closed_row()
        mock_binance.return_value = ("https://spot.fixture", [row], [])
        result = self.collect("binance-spot.m5")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["observations"]), 3)
        eth = result["observations"][0]
        self.assertEqual(eth["series_id"], "spot.binance-spot.ETHUSDT.ohlcv.5m")
        self.assertEqual(eth["value"], {"open_time_ms": row[0], "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5], "closed": True})
        self.assertEqual(eth["d9_target"], "FIXED_GRID")

    @patch("acquisition_core.kraken")
    def test_kraken_spot_runtime_mapping(self, mock_kraken):
        mock_kraken.return_value = ("XETHZUSD", [closed_row()], [])
        result = self.collect("kraken-spot.m5")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual({o["series_id"] for o in result["observations"]}, {"spot.kraken-spot.ETHUSD.ohlcv.5m", "spot.kraken-spot.BTCUSD.ohlcv.5m"})

    @patch.object(ac.CanonicalAcquisitionCore, "_binance_usdm_supplemental")
    @patch("acquisition_core.collect_binance")
    def test_binance_usdm_runtime_mapping(self, mock_collect, mock_supplemental):
        def fake_collect(_get, _now):
            p = Path("perp.json")
            p.write_text(json.dumps({"records": [[BASE_MS - 300_000, "1", "2", "0.5", "1.5", "10", BASE_MS - 1, "15", 4, "5", "6"]]}))
            return {"status": "PASS", "route": "https://fapi.fixture", "instruments": {"ETHUSDT": {"latest_kline_path": p.as_posix(), "latest": {"timestamp_ms": BASE_MS, "mark_price": "1905", "index_price": "1904", "basis_bps": "5.25", "funding_rate": "0.0001", "open_interest": "1000"}}}}
        mock_collect.side_effect = fake_collect
        mock_supplemental.return_value = [{"series_id": "liquidity.binance-usdm.ETHUSDT.depth", "provider_timestamp_at": ac._iso(BASE_MS), "provider_route": "https://fapi.fixture", "finality": "OBSERVED_STATE", "freshness": {"status": "LIVE_USABLE", "age_seconds": 0, "target_cadence_seconds": 300}, "value": {"depth": "fixture"}, "d9_target": "SAMPLED_SCHEDULE"}]
        result = self.collect("binance-usdm.m5-current")
        ids = {o["series_id"] for o in result["observations"]}
        self.assertIn("derivatives.binance-usdm.ETHUSDT.current", ids)
        self.assertIn("derivatives.binance-usdm.ETHUSDT.perp-ohlcv.5m", ids)
        self.assertIn("liquidity.binance-usdm.ETHUSDT.depth", ids)

    @patch("acquisition_core.collect_kraken")
    def test_kraken_futures_runtime_mapping(self, mock_collect):
        mock_collect.return_value = {"status": "PASS", "instruments": {"PI_ETHUSD": {"metrics": {"open-interest": {"latest": [BASE_MS, {"value": 123}], "last_timestamp": BASE_MS}}}}}
        result = self.collect("kraken-futures.analytics")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["observations"][0]["series_id"], "derivatives.kraken-futures.PI_ETHUSD.open-interest")
        self.assertEqual(result["observations"][0]["d9_target"], "SAMPLED_SCHEDULE")

    @patch("acquisition_core.collect_deribit_perpetual")
    def test_deribit_perpetual_runtime_mapping(self, mock_collect):
        mock_collect.return_value = {"status": "PASS", "instruments": {"ETH-PERPETUAL": {"timestamp_ms": BASE_MS, "mark_price": 1905}}}
        result = self.collect("deribit-perpetual.current")
        self.assertEqual(result["observations"][0]["series_id"], "derivatives.deribit-perpetual.ETH-PERPETUAL.current")

    @patch("acquisition_core.collect_options")
    def test_deribit_options_runtime_mapping(self, mock_collect):
        def fake(_get, _now):
            p = Path("surface.json"); p.write_text(json.dumps({"schema_version": "fixture", "selected_greeks": []}))
            d = Path("dvol.json"); d.write_text(json.dumps({"records": [[BASE_MS-3_600_000, "30", "31", "29", "30.5"]]}))
            return {"status": "PASS", "latest_surface": p.as_posix(), "dvol_latest_path": d.as_posix()}
        mock_collect.side_effect = fake
        result = self.collect("deribit-options.surface-dvol")
        self.assertEqual(result["status"], "PASS")
        ids={o["series_id"] for o in result["observations"]}
        self.assertIn("options.deribit-options.ETH.surface-snapshots",ids)
        self.assertIn("options.deribit-options.ETH.dvol.1h",ids)

    @patch("acquisition_core.collect_liquidity")
    def test_liquidity_runtime_mapping(self, mock_collect):
        def fake(_get, _now, _selected, _kraken_status):
            p = Path("liquidity.json"); p.write_text(json.dumps({"schema_version": "fixture", "snapshots": []}))
            return {"status": "PASS", "latest_path": p.as_posix()}
        mock_collect.side_effect = fake
        result = self.collect("liquidity.current")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["observations"][0]["series_id"], "liquidity.orderbook-snapshots")



if __name__ == "__main__":
    unittest.main()
