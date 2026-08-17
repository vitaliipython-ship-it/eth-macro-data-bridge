from __future__ import annotations

import unittest

from intelligence import depth_metrics


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


if __name__ == "__main__":
    unittest.main()
