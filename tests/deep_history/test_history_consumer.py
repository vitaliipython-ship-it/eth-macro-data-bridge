from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.history_consumer import HistoryConsumerError, _format_utc_ms, latest_history, read_history


class HistoryConsumerTests(unittest.TestCase):
    def test_one_step_adapter_preserves_resolution_plan_authority(self):
        plan = {
            "plan_sha256": "a" * 64,
            "request": {
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "start_ms": 1704067200000,
                "end_ms": 1704070800000,
                "cutoff_ms": None,
            },
        }
        rows = [(1704067200000, "1", "2", "0.5", "1.5", "10")]
        diagnostics = {
            "requested_start": "2024-01-01T00:00:00Z",
            "requested_end": "2024-01-01T01:00:00Z",
            "status": "PASS",
            "rows": 1,
            "expected_rows": 1,
            "gap_count": 0,
            "duplicates": 0,
            "sources": [{"segment_id": "cold:a", "storage": "GITHUB_RELEASE_ASSET", "locator": "asset.json", "sha256": "b" * 64, "rows": 1}],
        }

        with tempfile.TemporaryDirectory() as cache, patch(
            "tools.history_consumer.resolve_capability", return_value=plan
        ) as resolver, patch(
            "tools.history_consumer.materialize_resolution_plan", return_value=(rows, diagnostics)
        ) as materializer:
            returned_plan, payload, returned_diagnostics, receipt = read_history(
                "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "2024-01-01T00:00:00Z",
                "2024-01-01T01:00:00Z",
                cache_dir=Path(cache),
            )

        resolver.assert_called_once_with(
            "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "2024-01-01T00:00:00Z",
            "2024-01-01T01:00:00Z",
            None,
        )
        self.assertIs(returned_plan, plan)
        self.assertEqual(materializer.call_args.args[0], plan)
        self.assertEqual(returned_diagnostics, diagnostics)
        self.assertIn("2024-01-01T00:00:00Z,1,2,0.5,1.5,10", payload)
        self.assertEqual(receipt["plan_sha256"], "a" * 64)
        self.assertEqual(receipt["route"]["reader_input_authority"], "ResolutionPlan")
        self.assertEqual(receipt["rows"], 1)
        self.assertEqual(receipt["gap_count"], 0)
        self.assertEqual(receipt["duplicates"], 0)
        self.assertEqual(receipt["output_sha256"], hashlib.sha256(payload.encode("utf-8")).hexdigest())

    def test_latest_uses_actual_declared_finalized_anchor_and_existing_read(self):
        latest_open = 1787751000000
        step = 300000
        payload = json.dumps([
            {"open_time": _format_utc_ms(latest_open - step), "open":"1", "high":"2", "low":"0", "close":"1", "volume":"10"},
            {"open_time": _format_utc_ms(latest_open), "open":"1", "high":"2", "low":"0", "close":"1", "volume":"10"},
        ]) + "\n"
        diagnostics = {"status":"PASS", "rows":2, "expected_rows":2, "gap_count":0, "duplicates":0}
        receipt = {"semantic_receipt":{"finality":"FINALIZED"}}
        with patch(
            "tools.history_consumer._actual_latest_finalized_timestamp",
            return_value=({}, latest_open, step, "history/manifest.json"),
        ), patch(
            "tools.history_consumer.read_history",
            return_value=({"plan_sha256":"a" * 64}, payload, diagnostics, receipt),
        ) as reader:
            _plan, _payload, _diagnostics, result = latest_history(
                "spot.binance-spot.ETHUSDT.ohlcv.5m",
                2,
                cutoff_utc="2026-08-26T14:00:00Z",
            )
        reader.assert_called_once_with(
            "spot.binance-spot.ETHUSDT.ohlcv.5m",
            _format_utc_ms(latest_open + step - 2 * step),
            _format_utc_ms(latest_open + step),
            cutoff_utc="2026-08-26T14:00:00Z",
            mode="strict",
            output_format="json",
            cache_dir=None,
            current_policy="FINALIZED_ONLY",
        )
        self.assertEqual(result["latest_selection"]["latest_open_timestamp_ms"], latest_open)
        self.assertFalse(result["latest_selection"]["local_guessed_schedule_is_authority"])

    def test_latest_rejects_non_finalized_semantic_receipt(self):
        latest_open = 1787751000000
        step = 300000
        payload = json.dumps([{"open_time": _format_utc_ms(latest_open), "open":"1", "high":"2", "low":"0", "close":"1", "volume":"10"}]) + "\n"
        diagnostics = {"status":"PASS", "rows":1, "expected_rows":1, "gap_count":0, "duplicates":0}
        receipt = {"semantic_receipt":{"finality":"PROVISIONAL"}}
        with patch(
            "tools.history_consumer._actual_latest_finalized_timestamp",
            return_value=({}, latest_open, step, "history/manifest.json"),
        ), patch(
            "tools.history_consumer.read_history",
            return_value=({"plan_sha256":"a" * 64}, payload, diagnostics, receipt),
        ), self.assertRaises(HistoryConsumerError) as caught:
            latest_history(
                "spot.binance-spot.ETHUSDT.ohlcv.5m",
                1,
                cutoff_utc="2026-08-26T14:00:00Z",
            )
        self.assertEqual(caught.exception.code, "LATEST_OPEN_BAR_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
