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


if __name__ == "__main__":
    unittest.main()
