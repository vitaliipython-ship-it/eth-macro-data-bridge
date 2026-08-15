import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_publisher as rp


class ReleasePublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def asset(self,build,rows,name="series"):
        old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/build
        try:
            return rp.write_asset("domain","provider","instrument",name,["timestamp_ms","value"],rows,"MAX_AVAILABLE",{"source_route":"https://provider.test/data","boundary_status":"MAX_AVAILABLE"})
        finally: rp.BUILD_ROOT=old

    def test_frozen_source_acquires_once_and_replays(self):
        calls=[]; live=[[1,"a"],[2,"b"]]
        def fake(url): calls.append(url); return 200,{},live
        source=rp.FrozenSource(self.root/"frozen")
        with patch.object(rp,"request",side_effect=fake): self.assertEqual(source.fetch("https://provider.test/data?b=2&a=1"),live)
        source.freeze(); live.append([3,"moving-window"])
        self.assertEqual(source.fetch("https://provider.test/data?a=1&b=2"),[[1,"a"],[2,"b"]])
        self.assertEqual(len(calls),1)

    def test_hypothetical_live_change_does_not_enter_build_b(self):
        responses=iter([{"result":[[1,"authoritative"]]},{"result":[[2,"later-live"]]}]); calls=[]
        def fake(url): calls.append(url); return 200,{},next(responses)
        source=rp.FrozenSource(self.root/"frozen-live")
        with patch.object(rp,"request",side_effect=fake): first=source.fetch("https://provider.test/window?since=0")
        source.freeze(); second=source.fetch("https://provider.test/window?since=0")
        self.assertEqual(first,second); self.assertEqual(len(calls),1)

    def test_kraken_rolling_window_is_frozen_between_builds(self):
        window={"error":[],"result":{"XETHZUSD":[[1700000000,"1","2","0","1","1","1","1"]],"last":1700000000}}
        source=rp.FrozenSource(self.root/"frozen-kraken")
        with patch.object(rp,"request",return_value=(200,{},window)) as call: first=source.fetch("https://api.kraken.com/0/public/OHLC?pair=ETHUSD&interval=5&since=0")
        source.freeze(); second=source.fetch("https://api.kraken.com/0/public/OHLC?since=0&interval=5&pair=ETHUSD")
        self.assertEqual(first,second); self.assertEqual(call.call_count,1)

    def test_same_frozen_rows_build_identically(self):
        a=self.asset("a",[[1700000000000,"1"]]); b=self.asset("b",[[1700000000000,"1"]])
        rp.compare_builds(a,b); self.assertEqual(a[0]["sha256"],b[0]["sha256"])

    def test_mutated_canonical_source_changes_lineage(self):
        a=self.asset("a",[[1700000000000,"1"]]); b=self.asset("b",[[1700000000000,"2"]])
        self.assertNotEqual(a[0]["canonical_source_sha256"],b[0]["canonical_source_sha256"])
        with self.assertRaises(RuntimeError): rp.compare_builds(a,b)

    def test_inventory_difference_has_diagnostics(self):
        a=self.asset("a",[[1700000000000,"1"]],"a"); output=io.StringIO()
        with contextlib.redirect_stdout(output),self.assertRaises(RuntimeError): rp.compare_builds(a,[])
        self.assertIn("ONLY_IN_A=provider--instrument--a--2023.json",output.getvalue())

    def test_sha_mismatch_has_record_diagnostics(self):
        a=self.asset("a",[[1700000000000,"1"]]); b=self.asset("b",[[1700000000000,"2"]]); output=io.StringIO()
        with contextlib.redirect_stdout(output),self.assertRaises(RuntimeError): rp.compare_builds(a,b)
        text=output.getvalue(); self.assertIn("SHA_MISMATCH_COUNT=1",text); self.assertIn("FIRST_DIFFERING_RECORD_TIMESTAMP=1700000000000",text)

    def test_canary_reconciliation_is_idempotent(self):
        draft={"id":1,"draft":True,"tag_name":"history-storage-canary-v1","body":"cutoff="+rp.AS_OF_UTC}
        with patch.object(rp,"list_releases",return_value=[draft]),patch.object(rp,"gh") as call:
            self.assertIs(rp.reconcile_canary_draft("history-storage-canary-v1","body"),draft); call.assert_not_called()

    def test_conflicting_canary_drafts_fail_closed(self):
        drafts=[{"id":1,"draft":True,"tag_name":"history-storage-canary-v1","body":rp.AS_OF_UTC},{"id":2,"draft":True,"tag_name":"history-storage-canary-v1","body":rp.AS_OF_UTC}]
        with patch.object(rp,"list_releases",return_value=drafts),self.assertRaises(RuntimeError): rp.reconcile_canary_draft("history-storage-canary-v1","body")

    def test_canary_cleanup_cannot_target_production(self):
        with self.assertRaises(RuntimeError): rp.delete_canary_draft({"id":1,"draft":True,"tag_name":rp.TAGS["binance-spot"]},rp.TAGS["binance-spot"])

    def test_valid_git_overlap(self):
        cwd=Path.cwd()
        try:
            os.chdir(self.root); path=Path("history/provider/instrument/series/2023.json"); path.parent.mkdir(parents=True); row=[1700000000000,"1"]
            path.write_text(json.dumps({"provider":"provider","symbol":"instrument","interval":"series","records":[row]}))
            assets=self.asset("a",[row]); rp.verify_git_overlap(assets)
        finally: os.chdir(cwd)

    def test_binance_usdm_not_in_acquisition_contour(self):
        source=Path(rp.__file__).read_text(); acquisition=source[source.index("def binance_assets"):source.index("def kraken_spot_assets")]
        self.assertNotIn("fapi",acquisition); self.assertNotIn("binance-usdm",acquisition)


if __name__=="__main__": unittest.main()
