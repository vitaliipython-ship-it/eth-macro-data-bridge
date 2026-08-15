import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_publisher as rp
import intelligence


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

    def cvd_asset(self,build,rows,anchor=1):
        canonical,semantics=rp.canonicalize_kraken_cvd(rows,anchor); old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/build
        try: return rp.write_asset("kraken-futures","kraken-futures","PI_ETHUSD","cvd",["timestamp_ms","canonical_value"],canonical,"MAX_AVAILABLE",{"source_route":"https://provider.test/cvd","boundary_status":"MAX_AVAILABLE"},metric_semantics=semantics)
        finally: rp.BUILD_ROOT=old

    def write_archive(self,records,metric="cvd",semantics=None,path="derivatives/archive/part.json"):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True)
        payload={"provider":"kraken-futures","instrument":"PI_ETHUSD","metric":metric,"records":records}
        if semantics: payload["metric_semantics"]=semantics
        target.write_text(json.dumps(payload)); return target

    def verify_in_root(self,assets):
        cwd=Path.cwd()
        try: os.chdir(self.root); return rp.verify_git_overlap(assets)
        finally: os.chdir(cwd)

    def test_immutable_overlap_value_differs_fails(self):
        row=[1700000000000,"old"]; self.write_archive([row],metric="funding")
        old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/"immutable"
        try: assets=rp.write_asset("domain","kraken-futures","PI_ETHUSD","funding",["timestamp_ms","value"],[[row[0],"new"]],"MAX_AVAILABLE",{"source_route":"x"})
        finally: rp.BUILD_ROOT=old
        with self.assertRaisesRegex(RuntimeError,"overlap conflict"): self.verify_in_root(assets)

    def test_cvd_different_anchor_offset_passes(self):
        ts=1700000000000; self.write_archive([[ts,{"buy_volume":"2","sell_volume":"1","cvd":"99"}]])
        self.verify_in_root(self.cvd_asset("cvd-pass",[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"0"}]],2))

    def test_cvd_buy_differs_fails(self):
        ts=1700000000000; self.write_archive([[ts,{"buy_volume":"2","sell_volume":"1","cvd":"1"}]])
        with self.assertRaises(RuntimeError): self.verify_in_root(self.cvd_asset("cvd-buy",[[ts,{"buy_volume":"3","sell_volume":"1","cvd":"2"}]]))

    def test_cvd_sell_differs_fails(self):
        ts=1700000000000; self.write_archive([[ts,{"buy_volume":"2","sell_volume":"1","cvd":"1"}]])
        with self.assertRaises(RuntimeError): self.verify_in_root(self.cvd_asset("cvd-sell",[[ts,{"buy_volume":"2","sell_volume":"0","cvd":"2"}]]))

    def test_conflicting_duplicate_fails(self):
        ts=1700000000000
        with self.assertRaisesRegex(RuntimeError,"conflicting duplicate"): rp.dedupe_rows([[ts,"a"],[ts,"b"]],"test")

    def test_identical_duplicate_dedupes(self):
        ts=1700000000000; self.assertEqual(rp.dedupe_rows([[ts,"a"],[ts,"a"]],"test"),[[ts,"a"]])

    def test_unknown_cumulative_metric_remains_strict(self):
        ts=1700000000000; self.write_archive([[ts,{"value":"1"}]],metric="running-total")
        old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/"unknown"
        try: assets=rp.write_asset("domain","kraken-futures","PI_ETHUSD","running-total",["timestamp_ms","value"],[[ts,{"value":"2"}]],"MAX_AVAILABLE",{"source_route":"x"})
        finally: rp.BUILD_ROOT=old
        with self.assertRaises(RuntimeError): self.verify_in_root(assets)

    def test_timestamp_unit_mismatch_fails(self):
        with self.assertRaisesRegex(RuntimeError,"timestamp unit"): rp.dedupe_rows([[1700000000,"a"]],"test")

    def test_partition_boundary_duplicate_detected(self):
        ts=1700000000000; a=self.asset("p1",[[ts,"a"]]); b=self.asset("p2",[[ts,"a"]])
        with self.assertRaisesRegex(RuntimeError,"across partitions"): rp.validate_asset_set(a+b)

    def test_pagination_boundary_omission_detectable_as_gap(self):
        old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/"gap"
        try: assets=rp.write_asset("domain","kraken-futures","PI_ETHUSD","funding",["timestamp_ms","value"],[[1700000000000,"a"],[1700000600000,"b"]],"MAX_AVAILABLE",{"source_route":"x"})
        finally: rp.BUILD_ROOT=old
        with self.assertRaisesRegex(RuntimeError,"pagination boundary omission"): rp.validate_asset_set(assets)

    def test_manifest_row_count_mismatch_fails(self):
        assets=self.asset("count",[[1700000000000,"a"]]); assets[0]["row_count"]=2
        with self.assertRaisesRegex(RuntimeError,"row_count"): rp.validate_asset_set(assets)

    def test_manifest_first_timestamp_mismatch_fails(self):
        assets=self.asset("first",[[1700000000000,"a"]]); assets[0]["first_timestamp"]+=1
        with self.assertRaisesRegex(RuntimeError,"boundary"): rp.validate_asset_set(assets)

    def test_manifest_last_timestamp_mismatch_fails(self):
        assets=self.asset("last",[[1700000000000,"a"]]); assets[0]["last_timestamp"]+=1
        with self.assertRaisesRegex(RuntimeError,"boundary"): rp.validate_asset_set(assets)

    def test_frozen_source_tamper_fails(self):
        source=rp.FrozenSource(self.root/"tamper")
        with patch.object(rp,"request",return_value=(200,{}, {"value":1})): source.fetch("https://provider.test/x")
        source.freeze(); next((self.root/"tamper").glob("*.json")).write_text('{"value":2}')
        with self.assertRaisesRegex(RuntimeError,"integrity"): source.fetch("https://provider.test/x")

    def test_build_b_hidden_network_request_fails(self):
        source=rp.FrozenSource(self.root/"hidden"); source.freeze()
        with self.assertRaisesRegex(RuntimeError,"frozen source missing"): source.fetch("https://provider.test/not-acquired")

    def test_provider_window_fixture_constant_offset(self):
        a=[[1700000000000,{"buy_volume":"2","sell_volume":"1","cvd":"101"}],[1700000300000,{"buy_volume":"0","sell_volume":"3","cvd":"98"}]]
        b=[[t,{**v,"cvd":str(int(v["cvd"])-100)}] for t,v in a]
        self.assertEqual({int(x[1]["cvd"])-int(y[1]["cvd"]) for x,y in zip(a,b)},{100})
        self.assertTrue(all(x[1]["buy_volume"]==y[1]["buy_volume"] and x[1]["sell_volume"]==y[1]["sell_volume"] for x,y in zip(a,b)))

    def test_old_git_row_new_canonical_row_explicit_pass(self):
        ts=1700000000000; self.write_archive([[ts,{"buy_volume":"0","sell_volume":"0","cvd":"0"}]])
        assets=self.cvd_asset("migration",[[ts,{"buy_volume":"0","sell_volume":"0","cvd":"50934"}]],10)
        self.verify_in_root(assets)

    def test_same_anchor_canonical_mismatch_fails(self):
        ts=1700000000000; rows=[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"5"}]]; canonical,semantics=rp.canonicalize_kraken_cvd(rows,10)
        canonical[0][1]["canonical_rebased_cvd"]="999"; self.write_archive(canonical,semantics=semantics)
        with self.assertRaises(RuntimeError): self.verify_in_root(self.cvd_asset("same-anchor",rows,10))

    def test_unknown_cvd_schema_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"unknown Kraken CVD schema"): rp.canonicalize_kraken_cvd([[1700000000000,{"cvd":"0"}]],1)

    def test_canonical_net_flow_uses_decimal(self):
        rows,_=rp.canonicalize_kraken_cvd([[1700000000000,{"buy_volume":"0.3","sell_volume":"0.1","cvd":"9"}]],1)
        self.assertEqual(rows[0][1]["net_flow"],"0.2")

    def test_asset_replacement_even_rehashed_fails_metadata_binding(self):
        assets=self.asset("replace",[[1700000000000,"a"]]); path=Path(assets[0]["local_path"]); payload=json.loads(path.read_text()); payload["records"][0][1]="b"; path.write_bytes(rp.compact(payload)+b"\n")
        assets[0]["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest(); assets[0]["size_bytes"]=path.stat().st_size
        with self.assertRaisesRegex(RuntimeError,"canonical hash"): rp.validate_asset_set(assets)

    def test_overlap_failure_has_zero_publication_calls(self):
        with patch.object(rp,"gh") as gh_call:
            ts=1700000000000; self.write_archive([[ts,"old"]],metric="funding")
            old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/"no-publish"
            try: assets=rp.write_asset("domain","kraken-futures","PI_ETHUSD","funding",["timestamp_ms","value"],[[ts,"new"]],"MAX_AVAILABLE",{"source_route":"x"})
            finally: rp.BUILD_ROOT=old
            with self.assertRaises(RuntimeError): self.verify_in_root(assets)
            gh_call.assert_not_called()

    def test_kraken_history_manifest_refresh_binds_archive(self):
        cwd=Path.cwd(); ts=1700000000000
        try:
            os.chdir(self.root)
            for symbol in intelligence.KRAKEN_SYMBOLS:
                for metric in intelligence.KRAKEN_METRICS:
                    path=Path("derivatives/archive/2023/11/14/kraken-futures")/f"{symbol}-{metric}.json"; path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps({"records":[[ts,{"value":"1"}]]}))
            series=intelligence.refresh_kraken_history_manifest(ts+1)
            manifest=json.loads(Path("derivatives/history-manifest.json").read_text())
            self.assertEqual(len(series),26); self.assertEqual(manifest["as_of_ms"],ts+1); self.assertTrue(all(item["row_count"]==1 for item in manifest["series"]))
        finally: os.chdir(cwd)

    def test_binance_usdm_not_in_acquisition_contour(self):
        source=Path(rp.__file__).read_text(); acquisition=source[source.index("def binance_assets"):source.index("def kraken_spot_assets")]
        self.assertNotIn("fapi",acquisition); self.assertNotIn("binance-usdm",acquisition)


if __name__=="__main__": unittest.main()
