from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import history_access_v2
import resolution_v2

from canonical_json import canonical_json_bytes
from github_history_publication import (
    CONTROL_PATH as RAW_CONTROL_PATH,
    RAW_TRANSFER_REPRESENTATION,
    raw_transfer_control_entry,
    raw_transfer_resource_identity,
    raw_transfer_resource_path,
)
from raw_chain_transfer_core import physical_block_bundle_sha256, serialize_physical_block_bundle
from tests.deep_history.test_raw_chain_transfer_physical_route import (
    BLOCK_HASH, OTHER_BLOCK_HASH, FakeTransport as RawTransferFakeTransport,
    base_trace, build_bundle, one_tx_transport,
)


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", "," if False else ":"))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


class _Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        if self.offset >= len(self.raw):
            return b""
        if size < 0:
            size = len(self.raw) - self.offset
        chunk = self.raw[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class D94RepositoryProjectionTests(unittest.TestCase):
    def test_runtime_projection_has_semantic_profiles_without_second_catalog(self):
        index = resolution_v2.build_index_v2(ROOT)
        ids = {row["series_id"]: row for row in index["series"]}
        self.assertIn("options.deribit-options.ETH.surface-snapshots", ids)
        self.assertIn("liquidity.orderbook-snapshots", ids)
        self.assertIn("derivatives.deribit-perpetual.current-snapshot", ids)
        spreads = ids["derivatives.kraken-futures.PI_ETHUSD.spreads"]
        open_interest = ids["derivatives.kraken-futures.PI_ETHUSD.open-interest"]
        self.assertNotEqual(spreads["profile_id"], open_interest["profile_id"])
        self.assertEqual(index["profiles"][spreads["profile_id"]]["revision_policy"], "PROVIDER_REVISABLE_SNAPSHOT")
        self.assertEqual(index["profiles"][open_interest["profile_id"]]["revision_policy"], "STRICT_OVERLAP_REQUIRED")
        self.assertEqual(index["authority"]["projection"], "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG")
        self.assertFalse((ROOT / "history/capability-index-v2.json").exists())

    def test_real_option_and_liquidity_snapshots_are_sampled_not_grid_reconstructed(self):
        rows = resolution_v2._ledger_rows(ROOT)
        wanted = (
            "options.deribit-options.ETH.surface-snapshots",
            "liquidity.orderbook-snapshots",
        )
        for series_id in wanted:
            run = [row for row in rows if row["series_or_capability"] == series_id and row["status"] == "OBSERVED_STATE"][-1]
            start = run["expected_schedule_at_ms"]
            plan = resolution_v2.resolve_capability_v2(series_id, iso(start), iso(start + 1000), root=ROOT)
            self.assertEqual(plan["series"]["coverage_semantics"], "SAMPLED_SCHEDULE")
            self.assertEqual(len(plan["segments"]), 1)
            observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                plan, root=ROOT, cache_dir=ROOT / ".d9-test-cache-unused"
            )
            self.assertEqual(len(observations), 1)
            self.assertEqual(observations[0]["timestamp_ms"], start)
            self.assertEqual(diagnostics["internal_gap_count"], 0)
            self.assertEqual(diagnostics["collection_gap_count"], 0)
            self.assertEqual(diagnostics["status"], "PASS")
            if series_id.startswith("options."):
                self.assertIn("options", observations[0]["value"])
                self.assertEqual(plan["series"]["series_kind"], "OPTION_SURFACE")
            else:
                self.assertIn("snapshots", observations[0]["value"])
                self.assertEqual(plan["series"]["series_kind"], "ORDER_BOOK_SNAPSHOT")


class D94SyntheticFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "history").mkdir(parents=True)
        write_json(self.root / "bridge-contract.json", {"disabled_providers": {}})

    def tearDown(self):
        self.temp.cleanup()

    def write_base_index(self, *, series=None, profiles=None, policies=None, forward=None):
        write_json(
            self.root / "history/capability-index.json",
            {
                "schema_version": "1.1.0",
                "catalog_id": "eth-macro-data-bridge-capability-index",
                "generation_policy": "DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
                "authority": {
                    "route_policy": "bridge-contract.json",
                    "provider_contracts": "contracts/provider-contracts.json",
                    "cold_history_manifest": "history/release-manifest.json",
                    "hot_history_manifests": [],
                },
                "provider_policies": policies or [],
                "profiles": profiles or {},
                "series": series or [],
                "forward_capabilities": forward or [],
                "requestable_capabilities": [],
            },
        )

    def test_explicit_sampled_collection_gap_materializes_without_synthetic_fill(self):
        self.write_base_index(
            policies=[{"provider_id":"deribit-options","domain":"options","status":"ACTIVE","authority_role":"OPTIONS"}],
            forward=[{
                "capability_id":"options.deribit-options.ETH.surface-snapshots",
                "domain":"options","history_mode":"FORWARD_ONLY","availability_status":"PASS",
                "historical_backfill_status":"UNAVAILABLE_BY_PROVIDER","manifest_path":"options/manifest.json",
            }],
        )
        ts = 1785542400000
        ledger = {
            "schema_version":"market-data-collection-run-ledger/1.0.0",
            "date_utc":"2026-08-01",
            "runs":[{
                "run_id":"gap-1","expected_schedule_at":iso(ts),"collection_started_at":iso(ts+1000),
                "collection_completed_at":iso(ts+2000),"provider":"deribit-options",
                "series_or_capability":"options.deribit-options.ETH.surface-snapshots",
                "status":"COLLECTION_GAP","snapshot_ref":None,"error_class":"PROVIDER_TIMEOUT",
                "provider_timestamp_at":None,"known_at":iso(ts+2000),"retrieved_at":iso(ts+2000),
                "freshness":{"status":"COLLECTION_GAP","age_seconds":None,"target_cadence_seconds":3600},
            }],
        }
        write_json(self.root / "history/collection-runs/2026/08/01/runs.json", ledger)
        plan = resolution_v2.resolve_capability_v2(
            "options.deribit-options.ETH.surface-snapshots", iso(ts), iso(ts+1000), root=self.root
        )
        self.assertEqual(plan["segments"], [])
        self.assertEqual(plan["series"]["collection_gaps"][0]["status"], "COLLECTION_GAP")
        observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(
            plan, root=self.root, cache_dir=self.root / "cache"
        )
        self.assertEqual(observations, [])
        self.assertEqual(diagnostics["collection_gap_count"], 1)
        self.assertEqual(diagnostics["internal_gap_count"], 0)
        self.assertEqual(diagnostics["status"], "DEGRADED")

    def _write_regular_binance_fixture(self):
        start = 1782864000000
        step = 3600000
        profile_id = "binance-spot.history.max-available.hot"
        series_id = "spot.binance-spot.ETHUSDT.ohlcv.1h"
        profile = {
            "provider_id":"binance-spot","source_provider":"binance","history_mode":"MAX_AVAILABLE",
            "availability_status":"PASS","semantics_ref":None,"cold_manifest_path":"history/release-manifest.json",
            "release_tag":"history-binance-spot-v1","hot_manifest_path":"history/manifest.json",
        }
        row = {"series_id":series_id,"profile_id":profile_id,"instrument":"ETHUSDT","series":"ohlcv","interval":"1h","source_interval_or_metric":"1h"}
        self.write_base_index(series=[row], profiles={profile_id:profile}, policies=[{"provider_id":"binance-spot","domain":"spot","status":"ACTIVE","authority_role":"PRIMARY"}])
        write_json(self.root / "history/manifest.json", {"schema_version":"1.0.0","series":[{"provider":"binance","symbol":"ETHUSDT","interval":"1h","first_timestamp":start,"last_timestamp":start+step,"historical_backfill":"PASS","provider_history_limit":False}]})
        write_json(self.root / "history/release-manifest.json", {"storage_backend":"GITHUB_RELEASE_ASSET","generated_at_utc":"2026-07-01T00:00:00Z","asset_inventory":[],"series_inventory":[]})
        warm = {"schema_version":"1.0.0","provider":"binance","symbol":"ETHUSDT","interval":"1h","columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms"],"records":[[start+step,"2","3","1","2.5","20",start+2*step-1]]}
        write_json(self.root / "history/binance/ETHUSDT/1h/2026/07.json", warm)
        cold_payload = {
            "schema_version":"market-data-cold-asset/1.1.0","generation_id":"history-grid-v1-2026-07",
            "series_id":series_id,"series_kind":"REGULAR_GRID",
            "record_encoding":{"kind":"POSITIONAL_COLUMNS","columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms"]},
            "coverage_start_ms":start,"coverage_end_ms":start+step,"known_gaps":[],
            "records":[[start,"1","2","0.5","1.5","10",start+step-1]],
        }
        cold_raw = history_access_v2.compact(cold_payload)
        generation = {
            "schema_version":"market-data-history-generation/1.1.0","generation_id":"history-grid-v1-2026-07",
            "candidate_fingerprint":"f"*64,"period":"2026-07","storage_role":"COLD","state":"CANDIDATE",
            "series_kind":"REGULAR_GRID","coverage_start_ms":start,"coverage_end_ms":start+step,
            "membership":{},"finalization":{},"assets":[{
                "asset_name":"eth.json","series_id":series_id,"sha256":hashlib.sha256(cold_raw).hexdigest(),
                "size_bytes":len(cold_raw),"record_count":1,"first_timestamp_ms":start,"last_timestamp_ms":start,
                "source_warm_resources":[],"remote_asset_id":77,"browser_download_url":"https://example.invalid/eth.json",
            }],"known_gaps":[],"supersedes":None,
            "publication":{"publish_status":"PASS","readback_status":"PASS","size_match":"PASS","sha256_match":"PASS","overlap_proof":"PASS","cross_boundary_semantic_read":"NOT_RUN","activation_status":"NOT_ACTIVE","release_tag":"history-grid-v1-2026-07","release_id":7,"release_immutable":True},
        }
        write_json(self.root / "history/generations/history-grid-v1-2026-07.json", generation)
        write_json(self.root / "history/generation-index.json", {"schema_version":"market-data-history-generation-index/1.1.0","status":"CANDIDATE_NOT_ACTIVE","legacy_cold_manifest":"history/release-manifest.json","generations":[{"generation_id":"history-grid-v1-2026-07","generation_manifest_path":"history/generations/history-grid-v1-2026-07.json","period":"2026-07","candidate_fingerprint":"f"*64,"series_ids":[series_id],"seal_start_ms":start,"seal_end_ms":start+step,"authority_status":"CANDIDATE_NOT_ACTIVE","supersedes":None}]})
        return start, step, series_id, cold_raw

    def test_candidate_generation_is_qualification_only_and_reads_into_warm_tail(self):
        start, step, series_id, cold_raw = self._write_regular_binance_fixture()
        with self.assertRaises(RuntimeError):
            resolution_v2.resolve_capability_v2(series_id, iso(start), iso(start+2*step), root=self.root)
        plan = resolution_v2.resolve_capability_v2(series_id, iso(start), iso(start+2*step), qualification_mode=True, root=self.root)
        self.assertEqual([segment["generation_id"] for segment in plan["segments"]], ["history-grid-v1-2026-07", None])
        observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(
            plan, root=self.root, cache_dir=self.root / "cache", opener=lambda *_args, **_kwargs: _Response(cold_raw)
        )
        self.assertEqual([row["value"]["close"] for row in observations], ["1.5", "2.5"])
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["receipt"]["observation_count"], 2)

    def test_revision_cutoff_and_source_snapshot_binding(self):
        ts = 1785542400000
        step = 300000
        series_id = "derivatives.kraken-futures.PI_ETHUSD.spreads"
        profile_id = "kraken-futures.history.provider-limited.hot"
        profile = {
            "provider_id":"kraken-futures","source_provider":"kraken-futures","history_mode":"PROVIDER_LIMITED",
            "availability_status":"PROVIDER_HISTORY_LIMIT","semantics_ref":"derivatives/metric-semantics.json",
            "cold_manifest_path":"history/release-manifest.json","release_tag":"history-kraken-futures-v1",
            "hot_manifest_path":"derivatives/history-manifest.json",
        }
        row = {"series_id":series_id,"profile_id":profile_id,"instrument":"PI_ETHUSD","series":"spreads","interval":None,"source_interval_or_metric":"spreads"}
        self.write_base_index(series=[row], profiles={profile_id:profile}, policies=[{"provider_id":"kraken-futures","domain":"derivatives","status":"ACTIVE","authority_role":"HISTORY"}])
        write_json(self.root / "history/release-manifest.json", {"storage_backend":"GITHUB_RELEASE_ASSET","generated_at_utc":"2026-08-01T00:00:00Z","asset_inventory":[],"series_inventory":[]})
        write_json(self.root / "derivatives/history-manifest.json", {"schema_version":"1.0.0","series":[{"provider":"kraken-futures","instrument":"PI_ETHUSD","metric":"spreads","first_timestamp":ts,"last_timestamp":ts,"historical_backfill":"PASS"}]})
        write_json(self.root / "derivatives/metric-semantics.json", {"schema_version":"1.0.0","provider":"kraken-futures","metrics":{"spreads":{"classification":"PROVIDER_REVISABLE_SNAPSHOT"}}})
        base_row = [ts,{"bid.best_price":"1","ask.best_price":"2"}]
        revised_row = [ts,{"bid.best_price":"1.1","ask.best_price":"2.1"}]
        write_json(self.root / "derivatives/archive/2026/08/PI_ETHUSD-spreads.json", {"schema_version":"1.0.0","provider":"kraken-futures","instrument":"PI_ETHUSD","metric":"spreads","records":[base_row]})
        known_at = iso(ts + 2*step)
        source_ref = "derivatives/revisions/source/PI_ETHUSD-spreads-source.json"
        write_json(self.root / source_ref, {"schema_version":"kraken-revision-source-observation/1.0.0","provider":"kraken-futures","instrument":"PI_ETHUSD","metric":"spreads","retrieved_at":known_at,"observed_rows":[revised_row]})
        evidence_ref = "derivatives/revisions/evidence/PI_ETHUSD-spreads-r1.json"
        evidence = {
            "schema_version":"market-data-provider-revision/1.0.0","revision_id":"r1","classification":"PROVIDER_REVISABLE_SNAPSHOT",
            "effective_timestamp":ts,"known_at_utc":known_at,"provider":"kraken-futures","instrument":"PI_ETHUSD","metric":"spreads",
            "previous_value_fingerprint":hashlib.sha256(canonical(base_row)).hexdigest(),"observed_value":revised_row,
            "source_snapshot_ref":source_ref,"revision_of":f"kraken-futures/PI_ETHUSD/spreads/{ts}",
        }
        write_json(self.root / evidence_ref, evidence)

        pre = resolution_v2.resolve_capability_v2(series_id, iso(ts), iso(ts+step), cutoff_utc=iso(ts+step), root=self.root)
        pre_rows, _ = history_access_v2.materialize_resolution_plan_v2(pre, root=self.root, cache_dir=self.root/"pre")
        self.assertEqual(pre_rows[0]["value"], base_row[1])

        post = resolution_v2.resolve_capability_v2(series_id, iso(ts), iso(ts+step), cutoff_utc=iso(ts+3*step), root=self.root)
        post_rows, post_diag = history_access_v2.materialize_resolution_plan_v2(post, root=self.root, cache_dir=self.root/"post")
        self.assertEqual(post_rows[0]["value"], revised_row[1])
        self.assertEqual(post_diag["revisions_applied"][0]["revision_id"], "r1")

        write_json(self.root / source_ref, {"schema_version":"kraken-revision-source-observation/1.0.0","provider":"kraken-futures","instrument":"PI_ETHUSD","metric":"spreads","retrieved_at":known_at,"observed_rows":[base_row]})
        with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
            history_access_v2.materialize_resolution_plan_v2(post, root=self.root, cache_dir=self.root/"tamper")
        self.assertEqual(caught.exception.code, "CHECKSUM_MISMATCH")


class SelectiveV2EventSeriesTests(unittest.TestCase):
    BASE = 1780000000000
    SERIES = "events.synthetic.chain-canonicality"

    def _observations(self):
        return [
            {"observation_id":"o-original","chain_id":"eip155:1","block_height":100,"block_hash":"0xaaa","event_time_ms":self.BASE+100,"observation_known_at":iso(self.BASE+500),"finality":"FINALIZED","value":{"kind":"GENERIC_EVENT","value":"original"}},
            {"observation_id":"o-replacement","chain_id":"eip155:1","block_height":100,"block_hash":"0xbbb","event_time_ms":self.BASE+200,"observation_known_at":iso(self.BASE+600),"finality":"FINALIZED","value":{"kind":"GENERIC_EVENT","value":"replacement"}},
        ]

    def _revision(self, known_at=None):
        return {"schema_version":"chain-canonicality-revision/1.0.0","revision_id":"r1","chain_id":"eip155:1","block_height":100,"previous_canonical_block_hash":"0xaaa","canonical_block_hash":"0xbbb","revision_known_at":iso(known_at or self.BASE+4000),"source_provenance":{"authority":"SYNTHETIC_FIXTURE","evidence_id":"r1"}}

    def _plan(self, cutoff, *, observations=None, revisions=None, current_policy="FINALIZED_ONLY"):
        return resolution_v2.resolve_event_series_v2(
            self.SERIES, iso(self.BASE), iso(self.BASE+1000),
            observations=self._observations() if observations is None else observations,
            canonicality_revisions=[self._revision()] if revisions is None else revisions,
            cutoff_utc=iso(cutoff), current_policy=current_policy,
        )

    def test_t01_t04_event_branch_is_distinct_and_existing_semantics_remain(self):
        plan = self._plan(self.BASE+3000)
        self.assertEqual(plan["series"]["coverage_semantics"], "EVENT_DRIVEN")
        self.assertIsNone(plan["series"]["interval_ms"])
        self.assertEqual(plan["segments"], [])
        index = resolution_v2.build_index_v2(ROOT)
        fixed = next(row for row in index["series"] if row["series_id"] == "spot.binance-spot.ETHUSDT.ohlcv.5m")
        sampled = next(row for row in index["series"] if row["series_id"] == "options.deribit-options.ETH.surface-snapshots")
        self.assertEqual(index["profiles"][fixed["profile_id"]]["coverage_semantics"], "FIXED_GRID")
        self.assertEqual(index["profiles"][sampled["profile_id"]]["coverage_semantics"], "SAMPLED_SCHEDULE")
        self.assertIsInstance(index["profiles"][fixed["profile_id"]].get("interval_ms", 300000), int)

    def test_t05_t07_chain_revision_schema_is_distinct_from_provider_revision(self):
        capability = json.loads((ROOT / "schema/capability-index-v2.schema.json").read_text())
        profile = capability["properties"]["profiles"]["additionalProperties"]
        revisions = set(profile["properties"]["revision_policy"]["enum"])
        self.assertIn("CHAIN_CANONICALITY_REVISION", revisions)
        self.assertIn("PROVIDER_REVISABLE_SNAPSHOT", revisions)
        self.assertNotEqual("CHAIN_CANONICALITY_REVISION", "PROVIDER_REVISABLE_SNAPSHOT")
        plan_schema = json.loads((ROOT / "schema/market-data-resolution-plan-v2.schema.json").read_text())
        self.assertIn("CHAIN_CANONICALITY_REVISION", plan_schema["$defs"]["seriesDescriptor"]["properties"]["revision_policy"]["enum"])
        index = resolution_v2.build_index_v2(ROOT)
        spreads = next(row for row in index["series"] if row["series_id"] == "derivatives.kraken-futures.PI_ETHUSD.spreads")
        self.assertEqual(index["profiles"][spreads["profile_id"]]["revision_policy"], "PROVIDER_REVISABLE_SNAPSHOT")

    def test_t08_t11_pit_reorg_switches_only_after_revision_known_at_and_preserves_evidence(self):
        pre = self._plan(self.BASE+3000)
        pre_rows, pre_diag = history_access_v2.materialize_resolution_plan_v2(pre, root=ROOT)
        post = self._plan(self.BASE+5000)
        post_rows, post_diag = history_access_v2.materialize_resolution_plan_v2(post, root=ROOT)
        self.assertEqual([row["observation_id"] for row in pre_rows], ["o-original"])
        self.assertEqual(pre_diag["canonicality_revisions_applied"], [])
        self.assertEqual([row["observation_id"] for row in post_rows], ["o-replacement"])
        self.assertEqual([row["revision_id"] for row in post_diag["canonicality_revisions_applied"]], ["r1"])
        self.assertEqual([row["observation_id"] for row in post["event_series"]["observations"]], ["o-original", "o-replacement"])
        self.assertNotIn("revision_id", post["event_series"]["observations"][0])

    def test_t12_t14_finality_vocabulary_is_not_canonicality_state(self):
        observations = self._observations() + [
            {"observation_id":"o-provisional","chain_id":"eip155:1","block_height":101,"block_hash":"0xccc","event_time_ms":self.BASE+300,"observation_known_at":iso(self.BASE+700),"finality":"PROVISIONAL","value":{"kind":"GENERIC_EVENT","value":"pending"}}
        ]
        finalized = self._plan(self.BASE+3000, observations=observations, revisions=[])
        finalized_rows, _ = history_access_v2.materialize_resolution_plan_v2(finalized, root=ROOT)
        self.assertNotIn("o-provisional", {row["observation_id"] for row in finalized_rows})
        inclusive = self._plan(self.BASE+3000, observations=observations, revisions=[], current_policy="INCLUDE_CURRENT_PROVISIONAL")
        inclusive_rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(inclusive, root=ROOT)
        self.assertIn("o-provisional", {row["observation_id"] for row in inclusive_rows})
        self.assertEqual({row["finality"] for row in inclusive_rows}, {"FINALIZED", "PROVISIONAL"})
        self.assertEqual(diagnostics["receipt"]["finality"], "PROVISIONAL_INCLUDED")
        self.assertNotIn("ORPHANED", {row["finality"] for row in inclusive_rows})
        self.assertNotIn("SUPERSEDED_NON_CANONICAL", {row["finality"] for row in inclusive_rows})

    def test_t15_explicit_consumer_uses_existing_v2_reader_and_receipt(self):
        from tools.history_consumer import read_explicit_v2_event_series
        plan = self._plan(self.BASE+5000)
        _, payload, diagnostics, receipt = read_explicit_v2_event_series(plan, root=ROOT)
        self.assertEqual(diagnostics["coverage_semantics"], "EVENT_DRIVEN")
        self.assertEqual(receipt["receipt_schema_version"], "history-access-receipt/2.0.0")
        self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(), receipt["output_sha256"])
        self.assertIsNone(receipt["revision_context"])

    def test_t16_t18_v1_bytes_and_existing_v2_routes_are_preserved(self):
        from tests.deep_history import test_d62_history_access as fx
        from tools.history_access import materialize_resolution_plan
        cold = fx.encoded(fx.cold_payload([fx.record(fx.START,100), fx.record(fx.START+fx.STEP,101)]))
        warm = fx.encoded(fx.warm_payload([fx.record(fx.START+2*fx.STEP,102), fx.record(fx.START+3*fx.STEP,103)]))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=root/"history/warm.json"; path.parent.mkdir(); path.write_bytes(warm)
            segments=[fx.segment("GITHUB_RELEASE_ASSET",cold,fx.START,fx.START+2*fx.STEP,url="https://example.invalid/cold.json"),fx.segment("GIT_WARM_RESOURCE",warm,fx.START+2*fx.STEP,fx.START+4*fx.STEP,path="history/warm.json")]
            rows, diagnostics = materialize_resolution_plan(fx.plan_for(segments), root=root, cache_dir=root/"cache", opener=lambda *_a,**_k: fx.Response(cold))
        payload=(json.dumps(rows,separators=(",",":"))+"\n").encode()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), "6e752a8d6095f650d4f609b843264a0d528595d01dc49b829132f3944f4ac23b")
        self.assertEqual(diagnostics["status"], "PASS")
        sampled_run = [row for row in resolution_v2._ledger_rows(ROOT) if row["series_or_capability"] == "options.deribit-options.ETH.surface-snapshots" and row["status"] == "OBSERVED_STATE"][-1]
        sampled_start = sampled_run["expected_schedule_at_ms"]
        sampled_plan = resolution_v2.resolve_capability_v2("options.deribit-options.ETH.surface-snapshots", iso(sampled_start), iso(sampled_start+1000), root=ROOT)
        self.assertEqual(sampled_plan["series"]["coverage_semantics"], "SAMPLED_SCHEDULE")

    def test_t19_t24_activation_zero_job_provider_storage_and_raw_transfer_boundaries(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text())
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertTrue(selective["source_implemented"])
        self.assertFalse(selective["production_activated"])
        self.assertFalse(selective["d9_global_active"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(selective["provider_selected"])
        self.assertFalse(selective["storage_selected"])
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        portability = bridge["storage_portability"]
        self.assertTrue(portability["d6_resolution_plan_v1_active"])
        self.assertFalse(portability["resolution_plan_v2_active"])
        current_status = json.loads((ROOT / "contracts/d8-a2-physical-qualification-status-v1.json").read_text())["authority"]
        self.assertEqual(current_status["active_default_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertEqual(current_status["active_resolution_plan"], "market-data-resolution-plan/1.0.0")
        self.assertFalse(current_status["d9_active"])
        zero = bridge["semantic_resolution"]["current_data"]["zero_job_recovery"]
        zero_sha = hashlib.sha256(json.dumps(zero,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(zero_sha, "f4611f4b301834f8d07be7448e2ae6b85616b3a5aa56e7657678531146e0e01c")
        catalog = json.loads((ROOT / "history/capability-index.json").read_text())
        ids = [str(row.get("series_id") or row.get("capability_id") or "") for section in ("series","forward_capabilities","requestable_capabilities") for row in catalog.get(section,[]) if isinstance(row,dict)]
        self.assertFalse(any("raw-transfer" in value.lower() for value in ids))


class RawTransferDurableV2WiringTests(unittest.TestCase):
    START_UTC = "2025-09-11T13:00:00Z"
    END_UTC = "2025-09-11T14:00:00Z"
    CUTOFF_UTC = "2026-09-10T12:30:00Z"

    @staticmethod
    def _bundle(*, zero=True, block_hash=BLOCK_HASH, known_at="2026-09-10T12:00:00Z", prior=None):
        finalized = {"number": "0x64", "hash": block_hash}
        if zero:
            transport = RawTransferFakeTransport(block_hash=block_hash, finalized=finalized)
        else:
            transport = one_tx_transport(trace=base_trace(value=3), block_hash=block_hash, finalized=finalized)
        return build_bundle(transport, known_at=known_at, block_ref=block_hash, prior=prior)

    @staticmethod
    def _entry(bundle, *, data_commit_sha="a" * 40):
        raw = serialize_physical_block_bundle(bundle)
        identity = physical_block_bundle_sha256(bundle)
        resource_id = raw_transfer_resource_identity(bundle)
        path = raw_transfer_resource_path(resource_id)
        entry = raw_transfer_control_entry(
            bundle,
            resource_id=resource_id,
            content_identity=identity,
            data_commit_sha=data_commit_sha,
            resource_path=path,
            resource_bytes=raw,
        )
        return entry, path, raw

    @staticmethod
    def _write_root(root: Path, bundles):
        entries = []
        for index, bundle in enumerate(bundles, start=1):
            entry, path, raw = RawTransferDurableV2WiringTests._entry(bundle, data_commit_sha=f"{index:040x}")
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            entries.append(entry)
        manifest = {
            "schema_version": "market-data-d8-origin-publication-manifest/1.0.0",
            "backend_profile": "GITHUB_FIRST_V1",
            "representation": "EXACT_D8_ENVELOPE",
            "publications": [],
            "raw_transfer_representation": RAW_TRANSFER_REPRESENTATION,
            "raw_transfer_blocks": entries,
        }
        control = root / RAW_CONTROL_PATH
        control.parent.mkdir(parents=True, exist_ok=True)
        control.write_bytes(canonical_json_bytes(manifest) + b"\n")
        return entries

    def _plan(self, root: Path, *, cutoff=None):
        return resolution_v2.resolve_event_series_v2(
            "blockchain.raw-transfer-facts",
            self.START_UTC,
            self.END_UTC,
            observations=None,
            canonicality_revisions=None,
            cutoff_utc=cutoff or self.CUTOFF_UTC,
            current_policy="FINALIZED_ONLY",
            root=root,
            chain_id="1",
            block_height_start=100,
            block_height_end=101,
        )

    def test_raw_transfer_nonzero_publication_resolution_reader_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self._bundle(zero=False)
            entries = self._write_root(root, [bundle])
            plan = self._plan(root)
            history_access_v2.validate_resolution_plan_v2(plan)
            rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["observation_id"], bundle["observations"][0]["observation_id"])
            self.assertEqual(diagnostics["coverage_evidence"][0]["state"], "COVERED_NONZERO_BLOCK")
            self.assertEqual(diagnostics["coverage_evidence"][0]["resource_ref"], entries[0]["resource_ref"])
            self.assertEqual(diagnostics["receipt"]["receipt_schema_version"], "history-access-receipt/2.0.0")
            self.assertEqual(diagnostics["receipt"]["observation_count"], 1)
            self.assertEqual(diagnostics["receipt"]["coverage_evidence_sha256"], diagnostics["receipt"]["revision_context"]["coverage_evidence_sha256"])
            forbidden = {"provider_url", "filesystem_path", "release_tag", "asset_name", "asset_id", "database_locator", "backend_hostname", "credential"}
            self.assertFalse(forbidden & set(plan["request"]))

    def test_raw_transfer_covered_zero_is_valid_semantic_zero_with_explicit_coverage(self):
        from tools.history_consumer import read_explicit_v2_event_series
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self._bundle(zero=True)
            entries = self._write_root(root, [bundle])
            plan = self._plan(root)
            _, payload, diagnostics, receipt = read_explicit_v2_event_series(plan, root=root, mode="strict")
            self.assertEqual(payload, "[]\n")
            self.assertEqual(receipt["observation_count"], 0)
            self.assertEqual(diagnostics["coverage_evidence"], [{
                "state": "COVERED_ZERO_EVENT_BLOCK",
                "resource_ref": entries[0]["resource_ref"],
                "content_identity": entries[0]["sha256"],
                "coverage_complete": True,
                "coverage_key": bundle["coverage"]["key"],
                "zero_event_classification": "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE",
                "finality": "FINALIZED",
                "observation_known_at": bundle["observation_known_at"],
            }])
            self.assertEqual(receipt["coverage_evidence_sha256"], receipt["revision_context"]["coverage_evidence_sha256"])

    def test_raw_transfer_no_resource_incomplete_and_tampered_coverage_are_not_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(RuntimeError, "RAW_TRANSFER_RESOURCE_UNAVAILABLE"):
                self._plan(root)

        for mutation, expected_code in (("incomplete", "COVERAGE_GAP"), ("zero-proof", "COVERAGE_GAP")):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                bundle = self._bundle(zero=True)
                if mutation == "incomplete":
                    bundle["coverage"]["complete"] = False
                else:
                    bundle["coverage"]["zero_event_classification"] = None
                raw = canonical_json_bytes(bundle)
                identity = hashlib.sha256(raw).hexdigest()
                rid = raw_transfer_resource_identity(bundle)
                path = raw_transfer_resource_path(rid)
                entry = raw_transfer_control_entry(
                    bundle, resource_id=rid, content_identity=identity, data_commit_sha="a" * 40,
                    resource_path=path, resource_bytes=raw,
                )
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                manifest = {
                    "schema_version": "market-data-d8-origin-publication-manifest/1.0.0",
                    "backend_profile": "GITHUB_FIRST_V1", "representation": "EXACT_D8_ENVELOPE",
                    "publications": [], "raw_transfer_representation": RAW_TRANSFER_REPRESENTATION,
                    "raw_transfer_blocks": [entry],
                }
                control = root / RAW_CONTROL_PATH
                control.parent.mkdir(parents=True, exist_ok=True)
                control.write_bytes(canonical_json_bytes(manifest) + b"\n")
                plan = self._plan(root)
                with self.assertRaises(history_access_v2.HistoryAccessV2Error) as ctx:
                    history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
                self.assertEqual(ctx.exception.code, expected_code)

    def test_raw_transfer_tampered_bundle_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = self._bundle(zero=True)
            entries = self._write_root(root, [bundle])
            plan = self._plan(root)
            path = root / entries[0]["resource_path"]
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as ctx:
                history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
            self.assertEqual(ctx.exception.code, "INTEGRITY_FAILURE")

    def test_raw_transfer_pit_reorg_switches_only_after_revision_and_preserves_both_resources(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._bundle(zero=True, block_hash=OTHER_BLOCK_HASH, known_at="2026-09-10T12:00:00Z")
            prior = {"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH}
            new = self._bundle(zero=True, block_hash=BLOCK_HASH, known_at="2026-09-10T12:10:00Z", prior=prior)
            entries = self._write_root(root, [old, new])
            pre = self._plan(root, cutoff="2026-09-10T12:05:00Z")
            pre_rows, pre_diag = history_access_v2.materialize_resolution_plan_v2(pre, root=root, mode="strict")
            post = self._plan(root, cutoff="2026-09-10T12:20:00Z")
            post_rows, post_diag = history_access_v2.materialize_resolution_plan_v2(post, root=root, mode="strict")
            self.assertEqual(pre_rows, [])
            self.assertEqual(post_rows, [])
            self.assertEqual(pre_diag["canonicality_state"], [{"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH}])
            self.assertEqual(post_diag["canonicality_state"], [{"chain_id": "1", "block_height": 100, "block_hash": BLOCK_HASH}])
            self.assertEqual(pre_diag["canonicality_revisions_applied"], [])
            self.assertEqual([row["revision_id"] for row in post_diag["canonicality_revisions_applied"]], [new["canonicality_revisions"][0]["revision_id"]])
            self.assertEqual(pre_diag["addressable_resource_refs"], [entries[0]["resource_ref"]])
            self.assertEqual(set(post_diag["addressable_resource_refs"]), {entry["resource_ref"] for entry in entries})
            self.assertEqual(post_diag["superseded_resource_count"], 1)
            self.assertNotEqual(entries[0]["resource_ref"], entries[1]["resource_ref"])

    def test_raw_transfer_candidate_bridge_state_stays_network_inactive_and_single_family(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text())
        raw = bridge["semantic_contracts"]["raw_chain_transfer_fact"]
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertEqual(raw["status"], "CONTRACT_BOUND_RUNTIME_ROUTE_NOT_IMPLEMENTED")
        self.assertFalse(raw["runtime_active"])
        self.assertTrue(selective["raw_transfer_wiring_source_implemented"])
        self.assertEqual(selective["raw_transfer_network_inactive_qualification"], "PASS")
        self.assertEqual(selective["raw_transfer_live_provider_qualification"], "NOT_STARTED")
        self.assertEqual(selective["raw_transfer_wiring_candidate_status"], "SOURCE_OWNER_INTEGRATED_NOT_RUNTIME_ACTIVE")
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        self.assertFalse(selective["production_activated"])
        self.assertFalse(selective["d9_global_active"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(bridge["storage_portability"]["resolution_plan_v2_active"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_root(root, [self._bundle(zero=True)])
            plan = self._plan(root)
            self.assertEqual(
                plan["authority"]["raw_transfer_wiring_source"],
                selective["raw_transfer_wiring_candidate_status"],
            )
            history_access_v2.validate_resolution_plan_v2(plan)
            stale_plan = json.loads(json.dumps(plan))
            stale_plan["authority"]["raw_transfer_wiring_source"] = (
                "SOURCE_" + "CANDIDATE_NOT_OWNER_INTEGRATED_NOT_RUNTIME_ACTIVE"
            )
            stale_plan["plan_sha256"] = history_access_v2._plan_digest(stale_plan)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as ctx:
                history_access_v2.validate_resolution_plan_v2(stale_plan)
            self.assertEqual(ctx.exception.code, "INVALID_RESOLUTION_PLAN")



if __name__ == "__main__":
    unittest.main()
