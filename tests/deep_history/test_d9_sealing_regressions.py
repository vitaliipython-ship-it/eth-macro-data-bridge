from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import history_sealer as sealer


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


class D9SealingFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for rel in ("history", "derivatives/archive", "options", "contracts"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        (self.root / "history/release-manifest.json").write_text(compact({"series_inventory": []}), encoding="utf-8")
        self.spot = []
        self.kraken = []
        self.write_spot_manifest()
        self.write_kraken_manifest()
        (self.root / "derivatives/deribit-history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[],"d9_candidate_series":[]}), encoding="utf-8")
        (self.root / "options/history-manifest.json").write_text(compact({"schema_version":"1.0.0","deribit_dvol":{"historical_backfill":"UNAVAILABLE_BY_PROVIDER"}}), encoding="utf-8")
        self.write_semantics(1800)
        self.write_contract()

    def tearDown(self):
        self.temp.cleanup()

    def write_contract(self, *, generic=3600, revision=None):
        if revision is None:
            revision = {
                "STRICT_OVERLAP_REQUIRED":0,
                "WINDOW_ANCHORED_CUMULATIVE":0,
                "PROVIDER_REVISABLE_SNAPSHOT":10800,
            }
        value = {
            "schema_version":"d9-sealing-candidate/1.1.0",
            "status":"CANDIDATE_NOT_ACTIVE",
            "legacy_cold_authority":"history/release-manifest.json",
            "generation_schema":"schema/history-generation.schema.json",
            "generation_index_schema":"schema/history-generation-index.schema.json",
            "sealer":"tools/deep_history/history_sealer.py",
            "daily_workflow":".github/workflows/seal-history.yml",
            "period_policy":{"regular_grid":"COMPLETED_MONTH_ONLY","high_cardinality_snapshot":"COMPLETED_ISO_WEEK_ONLY_AFTER_WARM_BACKEND_QUALIFICATION","active_period_sealing":False},
            "generation_membership":{"policy_version":"d9-generation-membership/1.0.0","authority":"CANONICAL_WARM_MANIFESTS","late_history_change":"IMMUTABLE_SUCCESSOR_OR_FAIL_CLOSED"},
            "finalization_policy":{
                "policy_version":"d9-cold-finalization/1.0.0",
                "regular_grid_default_finalization_lag_seconds":generic,
                "provider_overrides":{"kraken-futures":{"ingestion_stabilization_source":"derivatives/metric-semantics.json"}},
                "metric_overrides":{},
                "revision_class_lag_seconds":revision,
                "missing_required_revision_policy":"FAIL_CLOSED",
            },
            "publication":{"backend":"GITHUB_RELEASE","reuse_existing_release_primitives":True,"deterministic_ab":True,"remote_binary_readback":True,"remote_size_match":True,"remote_sha256_match":True,"candidate_only":True,"candidate_generation_root":"history/generations","candidate_index":"history/generation-index.json","install_legacy_manifest":False,"warm_cleanup":False},
            "activation_gate":{"requires_d9_4_cross_boundary_semantic_read":True,"legacy_cold_remains_active_until_pass":True,"new_generation_authority":"CANDIDATE_NOT_ACTIVE"},
            "high_cardinality_warm":{"status":"BLOCKED_TEST","cold_sealing_enabled":False},
        }
        (self.root / "contracts/d9-sealing-candidate.json").write_text(compact(value), encoding="utf-8")

    def write_semantics(self, stabilization):
        value = {
            "schema_version":"1.0.0","provider":"kraken-futures","resolution_seconds":300,
            "archive_ingestion":{"stabilization_seconds":stabilization},
            "metrics":{
                "open-interest":{"classification":"STRICT_OVERLAP_REQUIRED"},
                "cvd":{"classification":"WINDOW_ANCHORED_CUMULATIVE"},
                "spreads":{"classification":"PROVIDER_REVISABLE_SNAPSHOT"},
            },
        }
        (self.root / "derivatives/metric-semantics.json").write_text(compact(value), encoding="utf-8")

    def write_spot_manifest(self):
        (self.root / "history/manifest.json").write_text(compact({"schema_version":"1.0.0","series":self.spot}), encoding="utf-8")

    def write_kraken_manifest(self):
        (self.root / "derivatives/history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":self.kraken}), encoding="utf-8")

    def declare_spot(self, symbol, coverage_start, limited=False):
        self.spot = [row for row in self.spot if row["symbol"] != symbol]
        self.spot.append({"provider":"binance","symbol":symbol,"interval":"1h","first_timestamp":coverage_start,"last_timestamp":coverage_start,"historical_backfill":"PASS","provider_history_limit":limited})
        self.write_spot_manifest()

    def declare_kraken(self, metric, coverage_start):
        self.kraken = [row for row in self.kraken if row["metric"] != metric]
        self.kraken.append({"provider":"kraken-futures","instrument":"PI_ETHUSD","metric":metric,"first_timestamp":coverage_start,"last_timestamp":coverage_start,"historical_backfill":"PASS"})
        self.write_kraken_manifest()

    def write_spot_month(self, symbol, *, coverage_start=None, complete=True, close="1.5"):
        start, end = sealer.month_bounds(2026, 2)
        first = max(start, coverage_start if coverage_start is not None else start)
        rows = [[ts,"1","2","0.5",close,"10",ts+3599999] for ts in range(first, end, 3600000)]
        if not complete:
            rows.pop(len(rows)//2)
        value = {"schema_version":"1.0.0","provider":"binance","symbol":symbol,"interval":"1h","records":rows}
        path = self.root / f"history/binance/{symbol}/1h/2026/02.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(compact(value), encoding="utf-8")
        for row in self.spot:
            if row["symbol"] == symbol and rows:
                row["last_timestamp"] = rows[-1][0]
        self.write_spot_manifest()
        return path

    def write_kraken_month(self, metric, *, value="1", complete=True):
        start, end = sealer.month_bounds(2026, 2)
        rows = [[ts,value] for ts in range(start, end, 300000)]
        if not complete:
            rows.pop(len(rows)//2)
        payload = {"schema_version":"1.0.0","provider":"kraken-futures","instrument":"PI_ETHUSD","metric":metric,"records":rows}
        path = self.root / f"derivatives/archive/2026/02/PI_ETHUSD-{metric}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(compact(payload), encoding="utf-8")
        for row in self.kraken:
            if row["metric"] == metric and rows:
                row["last_timestamp"] = rows[-1][0]
        self.write_kraken_manifest()
        return path

    def as_of(self, seconds_after_close):
        return sealer.month_bounds(2026, 2)[1] + seconds_after_close * 1000

    def mark_immutable(self, generation_id, series_ids):
        root = self.root / "history/generations"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{generation_id}.json"
        assets = [{"asset_name":f"{sid}.json","series_id":sid,"sha256":"a"*64,"size_bytes":1,"record_count":1,"first_timestamp_ms":0,"last_timestamp_ms":0,"source_warm_resources":[{"path":"warm.json","sha256":"b"*64,"size_bytes":1}],"remote_asset_id":1,"browser_download_url":"https://example.invalid/asset"} for sid in series_ids]
        manifest = {"schema_version":"market-data-history-generation/1.0.0","generation_id":generation_id,"storage_role":"COLD","state":"CANDIDATE","series_kind":"REGULAR_GRID","coverage_start_ms":0,"coverage_end_ms":0,"assets":assets,"known_gaps":[],"supersedes":None,"publication":{"publish_status":"PASS","readback_status":"PASS","size_match":"PASS","sha256_match":"PASS","overlap_proof":"PASS","cross_boundary_semantic_read":"NOT_RUN","activation_status":"NOT_ACTIVE","release_tag":generation_id,"release_id":1,"release_immutable":True}}
        path.write_text(compact(manifest), encoding="utf-8")
        index = {"schema_version":"market-data-history-generation-index/1.0.0","status":"CANDIDATE_NOT_ACTIVE","legacy_cold_manifest":"history/release-manifest.json","generations":[{"generation_id":generation_id,"generation_manifest_path":path.relative_to(self.root).as_posix(),"series_ids":sorted(series_ids),"seal_start_ms":0,"seal_end_ms":0,"authority_status":"CANDIDATE_NOT_ACTIVE","supersedes":None}]}
        (self.root / "history/generation-index.json").write_text(compact(index), encoding="utf-8")
        return path


class D9AtomicityReproductionTests(D9SealingFixture):
    def test_A_partial_membership_is_not_a_generation_candidate(self):
        start, _ = sealer.month_bounds(2026, 2)
        self.declare_spot("AUSDT", start); self.declare_spot("BUSDT", start)
        self.write_spot_month("AUSDT")
        self.assertEqual(sealer.build(self.as_of(7200), self.root/"out", self.root), [])

    def test_B_complete_membership_builds_one_atomic_generation(self):
        start, _ = sealer.month_bounds(2026, 2)
        self.declare_spot("AUSDT", start); self.declare_spot("BUSDT", start)
        self.write_spot_month("AUSDT"); self.write_spot_month("BUSDT")
        found = sealer.build(self.as_of(7200), self.root/"out", self.root)
        self.assertEqual(len(found), 1); self.assertEqual(len(found[0]["assets"]), 2)

    def test_C_repair_transitions_not_ready_to_ready(self):
        start, _ = sealer.month_bounds(2026, 2)
        self.declare_spot("AUSDT", start); self.declare_spot("BUSDT", start)
        self.write_spot_month("AUSDT")
        self.assertEqual(sealer.build(self.as_of(7200), self.root/"first", self.root), [])
        self.write_spot_month("BUSDT")
        self.assertEqual(len(sealer.build(self.as_of(7200), self.root/"second", self.root)), 1)

    def test_D_undeclared_physical_series_does_not_expand_membership(self):
        start, _ = sealer.month_bounds(2026, 2)
        self.declare_spot("AUSDT", start); self.write_spot_month("AUSDT"); self.write_spot_month("ROGUE")
        found = sealer.build(self.as_of(7200), self.root/"out", self.root)
        self.assertEqual([a["series_id"] for a in found[0]["assets"]], ["spot.binance-spot.AUSDT.ohlcv.1h"])

    def test_E_mid_period_coverage_requires_only_applicable_span(self):
        start, _ = sealer.month_bounds(2026, 2); mid = start + 14*86400000
        self.declare_spot("AUSDT", mid, limited=True); self.write_spot_month("AUSDT", coverage_start=mid)
        found = sealer.build(self.as_of(7200), self.root/"out", self.root)
        self.assertEqual(len(found), 1); self.assertEqual(found[0]["assets"][0]["first_timestamp_ms"], mid)

    def test_F_late_semantic_series_requires_successor(self):
        start, _ = sealer.month_bounds(2026, 2); original = "history-grid-v1-2026-02"
        self.declare_spot("AUSDT", start); self.write_spot_month("AUSDT")
        path = self.mark_immutable(original, ["spot.binance-spot.AUSDT.ohlcv.1h"]); before = path.read_bytes()
        self.declare_spot("BUSDT", start); self.write_spot_month("BUSDT")
        found = sealer.build(self.as_of(7200), self.root/"out", self.root)
        self.assertNotEqual(found[0]["generation_id"], original); self.assertEqual(found[0]["supersedes"], original); self.assertEqual(path.read_bytes(), before)

    def test_G_late_backfill_requires_successor(self):
        start, _ = sealer.month_bounds(2026, 2); mid = start + 14*86400000; original = "history-grid-v1-2026-02"
        self.declare_spot("AUSDT", mid, limited=True); self.write_spot_month("AUSDT", coverage_start=mid)
        path = self.mark_immutable(original, ["spot.binance-spot.AUSDT.ohlcv.1h"]); before = path.read_bytes()
        self.declare_spot("AUSDT", start); self.write_spot_month("AUSDT", coverage_start=start)
        found = sealer.build(self.as_of(7200), self.root/"out", self.root)
        self.assertNotEqual(found[0]["generation_id"], original); self.assertEqual(found[0]["supersedes"], original); self.assertEqual(path.read_bytes(), before)

    def test_H_remote_immutable_membership_mismatch_fails_closed(self):
        raw = b"a"
        manifest = {"generation_id":"history-grid-v1-2026-02","assets":[{"asset_name":"A.json","series_id":"A","sha256":hashlib.sha256(raw).hexdigest(),"size_bytes":1},{"asset_name":"B.json","series_id":"B","sha256":hashlib.sha256(b"b").hexdigest(),"size_bytes":1}],"_asset_paths":{},"_manifest_path":str(self.root/"unused.json")}
        remote = {"id":77,"tag_name":"history-grid-v1-2026-02","draft":False,"immutable":True}
        with mock.patch.object(sealer.release,"release_by_tag",return_value=remote), mock.patch.object(sealer.release,"gh",return_value=remote), mock.patch.object(sealer.release,"list_assets",return_value=[{"id":1,"name":"A.json","size":1,"browser_download_url":"https://example.invalid/A"}]), mock.patch.object(sealer.release,"download_release_asset",return_value=raw):
            with self.assertRaises(RuntimeError): sealer.publish_generation(manifest)


class D9FinalizationReproductionTests(D9SealingFixture):
    def setUp(self):
        super().setUp(); start, _ = sealer.month_bounds(2026, 2); self.declare_spot("AUSDT", start); self.write_spot_month("AUSDT")

    def use_kraken(self, metric, *, stabilization=1800):
        start, _ = sealer.month_bounds(2026, 2); self.spot=[]; self.write_spot_manifest(); self.write_semantics(stabilization); self.declare_kraken(metric, start); self.write_kraken_month(metric)

    def test_1_active_period_is_not_ready(self):
        end = sealer.month_bounds(2026, 2)[1]; self.assertEqual(sealer.detect(end-1, self.root), [])

    def test_2_just_closed_period_is_not_ready(self):
        end = sealer.month_bounds(2026, 2)[1]; self.assertEqual(sealer.detect(end, self.root), [])

    def test_3_inside_finalization_lag_is_not_ready(self):
        self.assertEqual(sealer.detect(self.as_of(1800), self.root), [])

    def test_4_after_finalization_lag_is_eligible_if_complete(self):
        self.assertEqual(len(sealer.detect(self.as_of(7200), self.root)), 1)

    def test_5_provider_stabilization_larger_than_generic_lag_wins(self):
        self.use_kraken("open-interest", stabilization=7200); self.assertEqual(sealer.detect(self.as_of(5400), self.root), [])

    def test_6_revision_class_cutoff_larger_than_generic_lag_wins(self):
        self.use_kraken("spreads"); self.assertEqual(sealer.detect(self.as_of(7200), self.root), [])

    def test_7_late_revision_before_freeze_is_included(self):
        self.use_kraken("spreads"); self.write_kraken_month("spreads", value="2")
        found = sealer.build(self.as_of(14400), self.root/"out", self.root); asset = Path(found[0]["_asset_paths"][found[0]["assets"][0]["asset_name"]]); payload = json.loads(asset.read_text(encoding="utf-8")); self.assertEqual(payload["records"][-1][1], "2")

    def test_8_revision_after_immutable_requires_successor(self):
        self.use_kraken("spreads"); original="history-grid-v1-2026-02"; path=self.mark_immutable(original,["derivatives.kraken-futures.PI_ETHUSD.spreads"]); before=path.read_bytes(); self.write_kraken_month("spreads", value="2")
        found=sealer.build(self.as_of(14400), self.root/"out", self.root); self.assertNotEqual(found[0]["generation_id"],original); self.assertEqual(found[0]["supersedes"],original); self.assertEqual(path.read_bytes(),before)

    def test_9_missing_required_revisable_policy_fails_closed(self):
        self.write_contract(revision={"STRICT_OVERLAP_REQUIRED":0,"WINDOW_ANCHORED_CUMULATIVE":0}); self.use_kraken("spreads")
        with self.assertRaises(RuntimeError): sealer.detect(self.as_of(86400), self.root)


if __name__ == "__main__":
    unittest.main()
