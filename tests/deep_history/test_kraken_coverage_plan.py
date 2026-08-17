import hashlib
import unittest
from unittest import mock

from tools import capability_index as ci


class KrakenCoveragePlanTests(unittest.TestCase):
    def test_v1_kraken_ohlcv_plan_declares_sparse_coverage(self):
        base={"schema_version":"market-data-resolution-plan/1.0.0","series":{"source_provider":"kraken","series":"ohlcv"},"request":{},"segments":[],"plan_sha256":"old"}
        with mock.patch.object(ci._v1,"resolve_capability",return_value=base):
            plan=ci.resolve_capability("spot.kraken-spot.ETHUSD.ohlcv.5m","2022-01-01T00:00:00Z","2022-01-01T01:00:00Z")
        self.assertEqual(plan["series"]["coverage_semantics"],"TRADES_ONLY_SPARSE")
        digest=plan.pop("plan_sha256")
        self.assertEqual(digest,hashlib.sha256(ci._v1.compact(plan)).hexdigest())

    def test_v1_binance_plan_remains_fixed_grid(self):
        base={"schema_version":"market-data-resolution-plan/1.0.0","series":{"source_provider":"binance","series":"ohlcv"},"request":{},"segments":[],"plan_sha256":"old"}
        with mock.patch.object(ci._v1,"resolve_capability",return_value=base):
            plan=ci.resolve_capability("spot.binance-spot.ETHUSDT.ohlcv.5m","2022-01-01T00:00:00Z","2022-01-01T01:00:00Z")
        self.assertEqual(plan["series"]["coverage_semantics"],"FIXED_GRID")


if __name__=="__main__":
    unittest.main()
