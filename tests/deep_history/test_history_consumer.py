from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.history_consumer import read_history


class HistoryConsumerTests(unittest.TestCase):
    def test_one_step_adapter_preserves_resolution_plan_authority(self):
        plan = {
            "plan_sha256": "a" * 64,
            "request": {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h"},
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


if __name__ == "__main__":
    unittest.main()
