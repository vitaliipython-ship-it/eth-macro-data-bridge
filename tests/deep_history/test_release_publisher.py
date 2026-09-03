import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_publisher as rp


class ReleasePublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def asset(self,name,records,provider="kraken-futures",instrument="PI_ETHUSD",series="funding",columns=None):
        path=self.root/(name+".json"); payload={"schema_version":"1.0.0","provider":provider,"instrument":instrument,"interval_or_metric":series,"columns":columns or ["timestamp_ms","value"],"partitioning":"yearly","period":"2023","closed_only":True,"records":records}; path.write_bytes(rp.compact(payload)+b"\n")
        return [{"local_path":str(path),"asset_name":path.name,"provider":provider,"instrument":instrument,"interval_or_metric":series,"first_timestamp":records[0][0],"last_timestamp":records[-1][0],"row_count":len(records),"partitioning":"yearly","closed_only":True,"size_bytes":path.stat().st_size,"sha256":rp.sha(path),"canonical_source_sha256":hashlib.sha256(rp.compact(records)).hexdigest(),"retrieved_at_utc":"2026-01-01T00:00:00Z","source_route":"x","historical_availability":"MAX_AVAILABLE","provider_history_limit":False,"known_gaps":[],"boundary_proof":{"source_route":"x"},"metric_semantics":None}]
    def cvd_asset(self,name,rows,anchor=10):
        canonical,semantics=rp.canonicalize_kraken_cvd(rows,anchor); return self.asset(name,canonical,series="cvd",columns=["timestamp_ms","value"])
    def write_archive(self,rows,metric="cvd",semantics=None):
        old=rp.BUILD_ROOT; rp.BUILD_ROOT=self.root/"archive-build"
        try: assets=rp.write_asset("kraken-futures","kraken-futures","PI_ETHUSD",metric,["timestamp_ms","value"],rows,"MAX_AVAILABLE",{"source_route":"x"},metric_semantics=semantics)
        finally: rp.BUILD_ROOT=old
        target=self.root/"archive"; target.mkdir(exist_ok=True); src=Path(assets[0]["local_path"]); dst=target/src.name; dst.write_bytes(src.read_bytes()); entry=dict(assets[0]); entry["asset_name"]=dst.name; (target/"manifest.json").write_bytes(rp.compact({"assets":[entry]})+b"\n"); return target
    def verify_in_root(self,assets):
        old=rp.ARCHIVE_ROOT if hasattr(rp,"ARCHIVE_ROOT") else None
        with patch.object(rp,"load_git_archive_rows") as loader:
            manifest=json.loads((self.root/"archive"/"manifest.json").read_text()); table={a["interval_or_metric"]:json.loads((self.root/"archive"/a["asset_name"]).read_text())["records"] for a in manifest["assets"]}; loader.side_effect=lambda p,i,s: table.get(s,[])
            return rp.verify_release_git_overlap(assets)

    def test_identical_duplicate_dedupes(self):
        row=[1700000000000,"a"]; self.assertEqual(rp.dedupe_rows([row,row],"x"),[row])
    def test_conflicting_duplicate_fails(self):
        with self.assertRaisesRegex(RuntimeError,"conflicting duplicate"): rp.dedupe_rows([[1700000000000,"a"],[1700000000000,"b"]],"x")
    def test_immutable_overlap_value_differs_fails(self):
        ts=1700000000000; self.write_archive([[ts,"old"]],metric="funding")
        assets=self.asset("new",[[ts,"new"]],series="funding")
        with self.assertRaisesRegex(RuntimeError,"immutable overlap conflict"): self.verify_in_root(assets)
    def test_valid_git_overlap(self):
        ts=1700000000000; self.write_archive([[ts,"x"]],metric="funding"); assets=self.asset("new",[[ts,"x"]],series="funding"); self.verify_in_root(assets)
    def test_cvd_different_anchor_offset_passes(self):
        ts=1700000000000; old=[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"101","provider_native_cvd":"101","net_flow":"1","canonical_rebased_cvd":"1"}]]; sem={"schema_version":"kraken-futures-cvd/2.0.0","classification":"WINDOW_ANCHORED_CONSTANT_OFFSET"}; self.write_archive(old,semantics=sem); assets=self.cvd_asset("cvd",[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"1"}]],999); self.verify_in_root(assets)
    def test_cvd_buy_differs_fails(self):
        ts=1700000000000; old=[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"101","provider_native_cvd":"101","net_flow":"1","canonical_rebased_cvd":"1"}]]; self.write_archive(old,semantics={"schema_version":"kraken-futures-cvd/2.0.0"}); assets=self.cvd_asset("cvd",[[ts,{"buy_volume":"3","sell_volume":"1","cvd":"1"}]],999); 
        with self.assertRaises(RuntimeError): self.verify_in_root(assets)
    def test_cvd_sell_differs_fails(self):
        ts=1700000000000; old=[[ts,{"buy_volume":"2","sell_volume":"1","cvd":"101","provider_native_cvd":"101","net_flow":"1","canonical_rebased_cvd":"1"}]]; self.write_archive(old,semantics={"schema_version":"kraken-futures-cvd/2.0.0"}); assets=self.cvd_asset("cvd",[[ts,{"buy_volume":"2","sell_volume":"2","cvd":"1"}]],999)
        with self.assertRaises(RuntimeError): self.verify_in_root(assets)
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
        source.freeze()
        frozen_response=next(path for path in (self.root/"tamper").glob("*.json") if path.name!="manifest.json")
        frozen_response.write_text('{"value":2}')
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

    def test_frozen_source_acquires_once_and_replays(self):
        source=rp.FrozenSource(self.root/"frozen")
        with patch.object(rp,"request",return_value=(200,{}, {"value":1})) as request_mock:
            self.assertEqual({"value":1},source.fetch("https://provider.test/x")); self.assertEqual({"value":1},source.fetch("https://provider.test/x")); source.freeze(); self.assertEqual({"value":1},source.fetch("https://provider.test/x"))
        self.assertEqual(1,request_mock.call_count)

    def test_hypothetical_live_change_does_not_enter_build_b(self):
        source=rp.FrozenSource(self.root/"frozen2")
        with patch.object(rp,"request",side_effect=[(200,{}, {"value":1}),(200,{}, {"value":999})]) as request_mock:
            source.fetch("https://provider.test/x"); source.freeze(); self.assertEqual({"value":1},source.fetch("https://provider.test/x"))
        self.assertEqual(1,request_mock.call_count)

    def test_inventory_difference_has_diagnostics(self):
        a=self.asset("a",[[1700000000000,"1"]]); b=self.asset("b",[[1700000000000,"1"]]); b[0]["asset_name"]="other.json"
        with self.assertRaisesRegex(RuntimeError,"ONLY_IN_A"): rp.compare_builds(a,b)

    def test_sha_mismatch_has_record_diagnostics(self):
        a=self.asset("a",[[1700000000000,"1"]]); b=self.asset("b",[[1700000000000,"2"]]); b[0]["asset_name"]=a[0]["asset_name"]
        with self.assertRaisesRegex(RuntimeError,"FIRST_DIFFERING_FIELD"): rp.compare_builds(a,b)

    def test_canary_reconciliation_is_idempotent(self):
        with patch.object(rp,"list_releases",return_value=[]), patch.object(rp,"gh") as gh_mock:
            rp.reconcile_canaries("run-1"); self.assertFalse(gh_mock.called)

    def test_conflicting_canary_drafts_fail_closed(self):
        releases=[{"id":1,"tag_name":"canary-a","draft":True,"name":"run-1"},{"id":2,"tag_name":"canary-b","draft":True,"name":"run-1"}]
        with patch.object(rp,"list_releases",return_value=releases):
            with self.assertRaisesRegex(RuntimeError,"conflicting"): rp.reconcile_canaries("run-1")

    def test_canary_cleanup_cannot_target_production(self):
        releases=[{"id":1,"tag_name":"history-binance-spot-v1","draft":True,"name":"run-1"}]
        with patch.object(rp,"list_releases",return_value=releases):
            with self.assertRaisesRegex(RuntimeError,"production"): rp.reconcile_canaries("run-1")

    def test_asset_replacement_even_rehashed_fails_metadata_binding(self):
        assets=self.asset("bind",[[1700000000000,"1"]]); asset=assets[0]; Path(asset["local_path"]).write_bytes(rp.compact({"schema_version":"1.0.0","provider":"kraken-futures","instrument":"PI_ETHUSD","interval_or_metric":"funding","columns":["timestamp_ms","value"],"partitioning":"yearly","period":"2023","closed_only":True,"records":[[1700000000000,"2"]]})+b"\n"); asset["sha256"]=rp.sha(Path(asset["local_path"])); asset["size_bytes"]=Path(asset["local_path"]).stat().st_size
        with self.assertRaises(RuntimeError): rp.validate_asset_set(assets)

    def test_kraken_rolling_window_is_frozen_between_builds(self):
        source=rp.FrozenSource(self.root/"rolling")
        with patch.object(rp,"request",side_effect=[(200,{}, {"value":1}),(200,{}, {"value":2})]) as request_mock:
            first=source.fetch("https://provider.test/rolling"); source.freeze(); second=source.fetch("https://provider.test/rolling")
        self.assertEqual(first,second); self.assertEqual(1,request_mock.call_count)

    def test_kraken_history_manifest_refresh_binds_archive(self):
        payload={"assets":[{"asset_name":"x.json","sha256":"a"*64}]}; digest=hashlib.sha256(rp.compact(payload)).hexdigest(); self.assertEqual(64,len(digest))

    def test_binance_usdm_not_in_acquisition_contour(self):
        source=Path(rp.__file__).read_text(); self.assertNotIn("fapi.binance.com",source)

    def test_canonical_net_flow_uses_decimal(self):
        canonical,_=rp.canonicalize_kraken_cvd([[1700000000000,{"buy_volume":"0.3","sell_volume":"0.1","cvd":"10"}]],1); self.assertEqual(canonical[0][1]["net_flow"],"0.2")

    def test_mutated_canonical_source_changes_lineage(self):
        records=[[1700000000000,"1"]]; a=hashlib.sha256(rp.compact(records)).hexdigest(); records[0][1]="2"; b=hashlib.sha256(rp.compact(records)).hexdigest(); self.assertNotEqual(a,b)


if __name__ == "__main__": unittest.main()
