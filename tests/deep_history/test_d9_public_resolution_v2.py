from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import history_access_v2
import resolution_v2


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_json(path: Path, value) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = compact(value)
    path.write_bytes(raw)
    return raw


def iso(ms: int) -> str:
    from datetime import datetime, timezone
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


class D94PublicRouteTests(unittest.TestCase):
    def test_public_resolver_defaults_v1_and_explicitly_exposes_v2(self):
        v1_result = subprocess.run(
            [
                sys.executable,
                "tools/capability_index.py",
                "resolve",
                "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "--from", "2022-06-18T00:00:00Z",
                "--to", "2022-06-19T00:00:00Z",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(v1_result.stdout)["schema_version"], "market-data-resolution-plan/1.0.0")

        run = [
            row for row in resolution_v2._ledger_rows(ROOT)
            if row["series_or_capability"] == "options.deribit-options.ETH.surface-snapshots"
            and row["status"] == "OBSERVED_STATE"
        ][-1]
        start = run["expected_schedule_at_ms"]
        v2_result = subprocess.run(
            [
                sys.executable,
                "tools/capability_index.py",
                "resolve",
                "options.deribit-options.ETH.surface-snapshots",
                "--from", iso(start),
                "--to", iso(start + 1000),
                "--plan-version", "2",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        plan = json.loads(v2_result.stdout)
        self.assertEqual(plan["schema_version"], "market-data-resolution-plan/2.0.0")
        self.assertEqual(plan["series"]["coverage_semantics"], "SAMPLED_SCHEDULE")
        self.assertEqual(plan["authority"]["d9_activation_status"], "CANDIDATE_NOT_ACTIVE")

    def test_public_reader_dispatches_v2_plan_without_second_entrypoint(self):
        run = [
            row for row in resolution_v2._ledger_rows(ROOT)
            if row["series_or_capability"] == "liquidity.orderbook-snapshots"
            and row["status"] == "OBSERVED_STATE"
        ][-1]
        start = run["expected_schedule_at_ms"]
        plan = resolution_v2.resolve_capability_v2(
            "liquidity.orderbook-snapshots", iso(start), iso(start + 1000), root=ROOT
        )
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "plan.json"
            plan_path.write_bytes(compact(plan))
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/history_access.py",
                    "slice",
                    "--plan", str(plan_path),
                    "--format", "json",
                    "--cache-dir", str(Path(td) / "cache"),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
        rows = json.loads(result.stdout)
        diagnostics = json.loads(result.stderr)
        self.assertEqual(len(rows), 1)
        self.assertIn("snapshots", rows[0]["value"])
        self.assertEqual(diagnostics["schema_version"], "history-access-diagnostics/2.0.0")
        self.assertEqual(diagnostics["status"], "PASS")


class D94PolicyBoundaryTests(unittest.TestCase):
    def _plan(self, root: Path, *, current_policy: str, storage: str, raw: bytes, path: str, start: int, step: int):
        plan = {
            "schema_version":"market-data-resolution-plan/2.0.0",
            "plan_kind":"MARKET_DATA_RESOLUTION_PLAN",
            "authority":{"qualification_mode":True,"d9_activation_status":"CANDIDATE_NOT_ACTIVE"},
            "request":{
                "series_id":"spot.binance-spot.ETHUSDT.ohlcv.1h",
                "start_ms":start,
                "end_ms":start+step,
                "effective_start_ms":start,
                "cutoff_ms":None,
                "current_policy":current_policy,
            },
            "series":{
                "series_id":"spot.binance-spot.ETHUSDT.ohlcv.1h",
                "instrument":"ETHUSDT",
                "source_interval_or_metric":"1h",
                "series_kind":"OHLCV",
                "coverage_semantics":"FIXED_GRID",
                "finality_policy":"PROVISIONAL_ALLOWED_EXPLICITLY",
                "revision_policy":"IMMUTABLE",
                "interval_ms":step,
                "coverage_boundary_evidence":{
                    "kind":"AVAILABLE_START","declared_start_ms":start,
                    "requested_start_ms":start,"effective_start_ms":start,
                },
                "collection_gaps":[],
            },
            "segments":[{
                "segment_id":"hot:fixture",
                "storage":storage,
                "source_manifest_path":None,
                "resource_path":path,
                "sha256":hashlib.sha256(raw).hexdigest(),
                "size_bytes":len(raw),
                "generation_id":None,
                "first_timestamp_ms":start,
                "last_timestamp_ms":start,
                "read_start_ms":start,
                "read_end_ms":start+step,
                "source_provider":"binance",
                "instrument":"ETHUSDT",
                "source_interval_or_metric":"1h",
                "known_gaps":[],
                "physical_descriptor":{"resource_path":path},
            }],
        }
        plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
        return plan

    def test_hot_requires_explicit_provisional_policy_and_marks_receipt(self):
        start = 1785542400000
        step = 3600000
        payload = {
            "schema_version":"1.0.0","provider":"binance","symbol":"ETHUSDT","interval":"1h",
            "columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms"],
            "records":[[start,"1","2","0.5","1.5","10",start+step-1]],
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = write_json(root / "data/current.json", payload)
            denied = self._plan(root, current_policy="FINALIZED_ONLY", storage="HOT_CURRENT_RESOURCE", raw=raw, path="data/current.json", start=start, step=step)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.validate_resolution_plan_v2(denied)
            self.assertEqual(caught.exception.code, "INVALID_RESOLUTION_PLAN")

            allowed = self._plan(root, current_policy="INCLUDE_CURRENT_PROVISIONAL", storage="HOT_CURRENT_RESOURCE", raw=raw, path="data/current.json", start=start, step=step)
            rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                allowed, root=root, cache_dir=root / "cache"
            )
        self.assertEqual(rows[0]["finality"], "PROVISIONAL")
        self.assertTrue(diagnostics["provisional_included"])
        self.assertEqual(diagnostics["receipt"]["finality"], "PROVISIONAL_INCLUDED")

    def test_provider_boundary_is_not_internal_gap_and_internal_gap_still_fails_strict(self):
        start = 1785542400000
        step = 3600000
        coverage = start + step
        end = start + 4 * step
        profile_id = "kraken-spot.history.provider-limited.hot"
        series_id = "spot.kraken-spot.ETHUSD.ohlcv.1h"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_json(root / "bridge-contract.json", {"disabled_providers":{}})
            write_json(root / "history/capability-index.json", {
                "schema_version":"1.0.0","catalog_id":"eth-macro-data-bridge-capability-index",
                "generation_policy":"DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
                "authority":{"route_policy":"bridge-contract.json","provider_contracts":"contracts/provider-contracts.json","cold_history_manifest":"history/release-manifest.json","hot_history_manifests":["history/manifest.json"]},
                "provider_policies":[{"provider_id":"kraken-spot","domain":"spot","status":"ACTIVE","authority_role":"CORROBORATION"}],
                "profiles":{profile_id:{
                    "provider_id":"kraken-spot","source_provider":"kraken","history_mode":"PROVIDER_LIMITED",
                    "availability_status":"PROVIDER_HISTORY_LIMIT","semantics_ref":None,
                    "cold_manifest_path":"history/release-manifest.json","release_tag":"history-kraken-spot-v1",
                    "hot_manifest_path":"history/manifest.json",
                }},
                "series":[{"series_id":series_id,"profile_id":profile_id,"instrument":"ETHUSD","series":"ohlcv","interval":"1h","source_interval_or_metric":"1h"}],
                "forward_capabilities":[],
            })
            write_json(root / "history/release-manifest.json", {
                "schema_version":"1.0.0","generated_at_utc":"2026-08-01T00:00:00Z",
                "storage_backend":"GITHUB_RELEASE_ASSET","asset_inventory":[],"series_inventory":[],
            })
            write_json(root / "history/manifest.json", {
                "schema_version":"1.0.0","series":[{
                    "provider":"kraken","symbol":"ETHUSD","interval":"1h",
                    "first_timestamp":coverage,"last_timestamp":start+3*step,
                    "historical_backfill":"PROVIDER_LIMITED","provider_history_limit":True,
                }],
            })
            payload = {
                "schema_version":"1.0.0","provider":"kraken","symbol":"ETHUSD","interval":"1h",
                "columns":["open_time_ms","open","high","low","close","volume","close_time_ms"],
                "records":[
                    [coverage,"1","2","0.5","1.5","10",coverage+step-1],
                    [coverage+2*step,"2","3","1","2.5","20",coverage+3*step-1],
                ],
            }
            write_json(root / "history/kraken/ETHUSD/1h/2026/08.json", payload)
            plan = resolution_v2.resolve_capability_v2(series_id, iso(start), iso(end), root=root)
            self.assertEqual(plan["request"]["effective_start_ms"], coverage)
            self.assertEqual(plan["series"]["coverage_boundary_evidence"]["kind"], "PROVIDER_HISTORY_LIMIT")
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.materialize_resolution_plan_v2(plan, root=root, cache_dir=root/"strict")
            self.assertEqual(caught.exception.code, "DATA_GAP")
            rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                plan, root=root, cache_dir=root/"permissive", mode="permissive"
            )
        self.assertEqual(len(rows), 2)
        self.assertIsNotNone(diagnostics["provider_boundary"])
        self.assertEqual(diagnostics["internal_gap_count"], 1)
        self.assertEqual(diagnostics["status"], "DEGRADED")

    def test_sampled_cold_snapshot_object_reader_is_resolution_plan_only(self):
        start = 1785542400000
        end = start + 3600000
        series_id = "options.deribit-options.ETH.surface-snapshots"
        payload = {
            "schema_version":"market-data-cold-asset/1.1.0",
            "generation_id":"history-snapshots-v1-2026-W31",
            "series_id":series_id,
            "series_kind":"HIGH_CARDINALITY_SNAPSHOT",
            "record_encoding":{"kind":"SNAPSHOT_OBJECT"},
            "coverage_start_ms":start,
            "coverage_end_ms":end,
            "known_gaps":[],
            "records":[{"expected_schedule_at_ms":start,"payload":{"timestamp_ms":start,"options":[{"instrument_name":"ETH-TEST-C"}]}}],
        }
        raw = compact(payload)
        plan = {
            "schema_version":"market-data-resolution-plan/2.0.0","plan_kind":"MARKET_DATA_RESOLUTION_PLAN",
            "authority":{"qualification_mode":True,"d9_activation_status":"CANDIDATE_NOT_ACTIVE"},
            "request":{"series_id":series_id,"start_ms":start,"end_ms":end,"effective_start_ms":start,"cutoff_ms":None,"current_policy":"FINALIZED_ONLY"},
            "series":{
                "series_id":series_id,"instrument":None,"source_interval_or_metric":series_id,
                "series_kind":"OPTION_SURFACE","coverage_semantics":"SAMPLED_SCHEDULE",
                "finality_policy":"OBSERVED_SNAPSHOT","revision_policy":"IMMUTABLE","interval_ms":None,
                "coverage_boundary_evidence":{"kind":"FORWARD_ONLY_START","declared_start_ms":start,"requested_start_ms":start,"effective_start_ms":start},
                "collection_gaps":[],
            },
            "segments":[{
                "segment_id":"generation-cold:sampled:1","storage":"GITHUB_RELEASE_ASSET",
                "source_manifest_path":"history/generations/history-snapshots-v1-2026-W31.json",
                "release_tag":"history-snapshots-v1-2026-W31","asset_id":1,"asset_name":"options.json",
                "browser_download_url":"https://example.invalid/options.json","sha256":hashlib.sha256(raw).hexdigest(),
                "size_bytes":len(raw),"immutable":True,"generation_id":"history-snapshots-v1-2026-W31",
                "first_timestamp_ms":start,"last_timestamp_ms":start,"read_start_ms":start,"read_end_ms":end,
                "source_provider":"deribit-options","instrument":None,"source_interval_or_metric":series_id,
                "known_gaps":[],"physical_descriptor":{"release_tag":"history-snapshots-v1-2026-W31","asset_id":1,"asset_name":"options.json","browser_download_url":"https://example.invalid/options.json","immutable":True},
            }],
        }
        plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                plan, root=Path(td), cache_dir=Path(td)/"cache",
                opener=lambda *_args, **_kwargs: _Response(raw),
            )
        self.assertEqual(rows[0]["value"]["options"][0]["instrument_name"], "ETH-TEST-C")
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["receipt"]["observation_count"], 1)


if __name__ == "__main__":
    unittest.main()
