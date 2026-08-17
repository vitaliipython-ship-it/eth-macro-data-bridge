from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from deribit_history import collect_deribit_history


class D9DeribitHistoryTests(unittest.TestCase):
    def test_funding_continues_active_while_ohlcv_stays_candidate(self):
        now = 1786968000000

        def get(url: str):
            if "get_funding_rate_history" in url:
                return {
                    "result": [
                        {
                            "timestamp": now - 3600000,
                            "index_price": 2000,
                            "interest_8h": 0.0001,
                            "interest_1h": 0.00001,
                            "prev_index_price": 1999,
                        }
                    ]
                }
            if "get_tradingview_chart_data" in url:
                return {
                    "result": {
                        "ticks": [now - 7200000],
                        "open": [1990],
                        "high": [2010],
                        "low": [1980],
                        "close": [2000],
                        "volume": [123.4],
                    }
                }
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                result = collect_deribit_history(get, now)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["active_series"], 2)
                self.assertEqual(result["candidate_series"], 4)
                funding = Path("derivatives/archive/deribit-perpetual/ETH-PERPETUAL-funding-1h.json")
                ohlcv = Path("derivatives/archive/deribit-perpetual/ETH-PERPETUAL-ohlcv-1h.json")
                self.assertTrue(funding.is_file())
                self.assertTrue(ohlcv.is_file())
                funding_payload = json.loads(funding.read_text())
                ohlcv_payload = json.loads(ohlcv.read_text())
                self.assertEqual(funding_payload["provider"], "deribit-perpetual")
                self.assertEqual(funding_payload["metric"], "funding")
                self.assertNotIn("interval", funding_payload)
                self.assertEqual(ohlcv_payload["metric"], "OHLCV-1h")
                self.assertNotIn("interval", ohlcv_payload)
                manifest = json.loads(Path("derivatives/deribit-history-manifest.json").read_text())
                active_keys = {(row["instrument"], row["metric"]) for row in manifest["series"]}
                candidate_keys = {(row["instrument"], row["metric"]) for row in manifest["d9_candidate_series"]}
                self.assertIn(("ETH-PERPETUAL", "funding"), active_keys)
                self.assertNotIn(("ETH-PERPETUAL", "OHLCV-1h"), active_keys)
                self.assertIn(("ETH-PERPETUAL", "OHLCV-1h"), candidate_keys)
                self.assertEqual(manifest["d9_candidate_status"], "DERIBIT_H1_WARM_NOT_ACTIVE")
            finally:
                os.chdir(previous)

    def test_repeat_is_idempotent(self):
        now = 1786968000000

        def get(url: str):
            if "get_funding_rate_history" in url:
                return {"result": []}
            return {"result": {"ticks": [], "open": [], "high": [], "low": [], "close": [], "volume": []}}

        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                first = collect_deribit_history(get, now)
                second = collect_deribit_history(get, now)
                self.assertEqual(first["active_series"], 0)
                self.assertEqual(first["candidate_series"], 0)
                self.assertEqual(second["active_series"], 0)
                self.assertEqual(second["candidate_series"], 0)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
