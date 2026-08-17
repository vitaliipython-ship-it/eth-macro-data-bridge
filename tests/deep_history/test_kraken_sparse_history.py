import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import history_access as ha
from tools.deep_history import kraken_ohlcvt_archive as ka

STEP=300000
START=1640995200000


def sparse_plan(raw,path,coverage="TRADES_ONLY_SPARSE"):
    plan={"schema_version":"market-data-resolution-plan/1.0.0","plan_kind":"MARKET_DATA_RESOLUTION_PLAN","authority":{"route_policy":"bridge-contract.json","capability_index":"history/capability-index.json","cold_manifest":"history/release-manifest.json","hot_manifest":"history/manifest.json"},"request":{"series_id":"spot.kraken-spot.ETHUSD.ohlcv.5m","start_ms":START,"end_ms":START+3*STEP,"cutoff_ms":None},"series":{"series_id":"spot.kraken-spot.ETHUSD.ohlcv.5m","profile_id":"kraken-spot.history.provider-limited.hot","instrument":"ETHUSD","series":"ohlcv","interval":"5m","source_interval_or_metric":"5m","provider_id":"kraken-spot","source_provider":"kraken","history_mode":"PROVIDER_LIMITED","availability_status":"PASS","interval_ms":STEP,"coverage_semantics":coverage},"segments":[{"segment_id":"warm:sparse","storage":"GIT_WARM_RESOURCE","source_manifest_path":"history/manifest.json","sha256":hashlib.sha256(raw).hexdigest(),"size_bytes":len(raw),"first_timestamp_ms":START,"last_timestamp_ms":START+2*STEP,"read_start_ms":START,"read_end_ms":START+3*STEP,"source_provider":"kraken","instrument":"ETHUSD","source_interval_or_metric":"5m","resource_path":path}]}
    plan["plan_sha256"]=hashlib.sha256(ha.compact(plan)).hexdigest()
    return plan


class KrakenSparseSemanticsTests(unittest.TestCase):
    def test_sparse_no_trade_interval_passes_strict_without_fill(self):
        payload={"schema_version":"1.0.0","provider":"kraken","symbol":"ETHUSD","interval":"5m","columns":["open_time_ms","open","high","low","close","volume","close_time_ms"],"records":[[START,"10","11","9","10.5","2",START+STEP-1],[START+2*STEP,"12","13","11","12.5","3",START+3*STEP-1]]}
        raw=(json.dumps(payload,separators=(",",":"))+"\n").encode()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"sparse.json").write_bytes(raw)
            rows,diagnostics=ha.materialize_resolution_plan(sparse_plan(raw,"sparse.json"),root=root,cache_dir=root/"cache",mode="strict")
        self.assertEqual([row[0] for row in rows],[START,START+2*STEP])
        self.assertEqual((diagnostics["status"],diagnostics["gap_count"]),("PASS",0))
        self.assertEqual(diagnostics["provider_no_trade_intervals_count"],1)
        self.assertEqual(diagnostics["provider_no_trade_intervals_preview_ms"],[START+STEP])

    def test_fixed_grid_gap_still_fails_strict(self):
        payload={"schema_version":"1.0.0","provider":"kraken","symbol":"ETHUSD","interval":"5m","columns":["open_time_ms","open","high","low","close","volume","close_time_ms"],"records":[[START,"10","11","9","10.5","2",START+STEP-1]]}
        raw=(json.dumps(payload,separators=(",",":"))+"\n").encode()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"fixed.json").write_bytes(raw)
            with self.assertRaises(ha.HistoryAccessError) as ctx:
                ha.materialize_resolution_plan(sparse_plan(raw,"fixed.json","FIXED_GRID"),root=root,cache_dir=root/"cache",mode="strict")
        self.assertEqual(ctx.exception.code,"DATA_GAP")


class KrakenArchiveParserTests(unittest.TestCase):
    def test_parser_preserves_trade_rows_without_synthetic_fill(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/"Kraken_OHLCVT.zip"
            with zipfile.ZipFile(archive,"w") as zf:
                zf.writestr("master/ETHUSD_5.csv","1609459200,10,11,9,10.5,2,3\n1609459800,12,13,11,12.5,3,4\n")
                zf.writestr("master/ETHUSD_1440.csv","1609459200,10,13,9,12.5,5,7\n")
            rows,member=ka.parse_member(archive,"5m")
        self.assertEqual(member,"master/ETHUSD_5.csv")
        self.assertEqual([row[0] for row in rows],[1609459200000,1609459800000])
        self.assertNotIn(1609459500000,[row[0] for row in rows])

    def test_missing_member_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/"Kraken_OHLCVT.zip"
            with zipfile.ZipFile(archive,"w") as zf:
                zf.writestr("master/XBTUSD_5.csv","1609459200,10,11,9,10.5,2,3\n")
            with self.assertRaises(RuntimeError):
                ka.parse_member(archive,"5m")


if __name__=="__main__":
    unittest.main()
