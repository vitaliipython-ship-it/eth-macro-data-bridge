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
                "schema_version":"1.1.0","catalog_id":"eth-macro-data-bridge-capability-index",
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
                "requestable_capabilities":[],
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


class G2BReaderSuccessorTests(unittest.TestCase):
    FAMILY = "liquidity.orderbook-snapshots"

    def _copy(self, value):
        return json.loads(json.dumps(value))

    def _actual_successor_observation(self):
        base = ROOT / "history/liquidity-orderbook-snapshots"
        for path in sorted(base.rglob("observations.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != resolution_v2.G2B_PARTITION_SCHEMA:
                continue
            for observation in payload.get("observations", []):
                if not isinstance(observation, dict):
                    continue
                try:
                    history_access_v2._validate_g2b_observation(observation)
                except history_access_v2.HistoryAccessV2Error:
                    continue
                return self._copy(observation)
        self.fail("repository has no valid G2-A successor durable observation fixture")

    def _base_root(self, root: Path) -> None:
        contract = json.loads((ROOT / resolution_v2.G2B_CONTRACT_PATH).read_text(encoding="utf-8"))
        write_json(root / resolution_v2.G2B_CONTRACT_PATH, contract)
        write_json(root / "bridge-contract.json", {
            "disabled_providers": {},
            "semantic_contracts": {
                "liquidity_durable_l2": {
                    "contract_id": resolution_v2.G2B_CONTRACT_ID,
                    "path": resolution_v2.G2B_CONTRACT_PATH,
                }
            },
        })
        write_json(root / "history/capability-index.json", {
            "schema_version": "1.1.0",
            "catalog_id": "eth-macro-data-bridge-capability-index",
            "generation_policy": "DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
            "authority": {
                "route_policy": "bridge-contract.json",
                "provider_contracts": "contracts/provider-contracts.json",
                "cold_history_manifest": "history/release-manifest.json",
                "hot_history_manifests": [],
            },
            "provider_policies": [],
            "profiles": {},
            "series": [],
            "forward_capabilities": [],
            "requestable_capabilities": [],
        })

    def _write_successor(self, root: Path, observations) -> str:
        first = observations[0]
        timestamp = first["observation_time_ms"]
        path = resolution_v2._g2b_day_paths(
            {"locator_pattern": resolution_v2.G2B_LOCATOR_PATTERN}, timestamp, timestamp + 1
        )[0][1]
        day = Path(path).parts[-4:-1]
        date_utc = f"{day[0]}-{day[1]}-{day[2]}"
        write_json(root / path, {
            "schema_version": resolution_v2.G2B_PARTITION_SCHEMA,
            "date_utc": date_utc,
            "history_family": self.FAMILY,
            "observations": observations,
        })
        return path

    def _write_legacy(self, root: Path, timestamp: int) -> dict:
        from datetime import datetime, timezone
        day = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
        snapshot_ref = f"liquidity/snapshots/{day:%Y/%m/%d}/{timestamp}.json"
        payload = {"schema_version": "1.0.0", "timestamp_ms": timestamp, "snapshots": []}
        write_json(root / snapshot_ref, payload)
        known_at = timestamp + 1000
        ledger_path = f"history/collection-runs/{day:%Y/%m/%d}/runs.json"
        write_json(root / ledger_path, {
            "schema_version": resolution_v2.LEDGER_SCHEMA,
            "date_utc": f"{day:%Y-%m-%d}",
            "runs": [{
                "run_id": f"legacy:{timestamp}",
                "expected_schedule_at": iso(timestamp),
                "collection_started_at": iso(timestamp),
                "collection_completed_at": iso(known_at),
                "provider": "multi-provider",
                "series_or_capability": self.FAMILY,
                "status": "OBSERVED_STATE",
                "snapshot_ref": snapshot_ref,
                "error_class": None,
                "provider_timestamp_at": iso(timestamp),
                "known_at": iso(known_at),
                "retrieved_at": iso(known_at),
                "freshness": {"status": "PASS", "age_seconds": 1, "target_cadence_seconds": 3600},
            }],
        })
        return payload

    def _plan(self, root: Path, start: int, end: int, cutoff: int | None = None):
        return resolution_v2.resolve_capability_v2(
            self.FAMILY, iso(start), iso(end), cutoff_utc=iso(cutoff) if cutoff is not None else None, root=root
        )

    def _read(self, root: Path, plan):
        return history_access_v2.materialize_resolution_plan_v2(plan, root=root, cache_dir=root / "cache")

    def _rehash_plan(self, plan):
        plan["plan_sha256"] = hashlib.sha256(compact({k: v for k, v in plan.items() if k != "plan_sha256"})).hexdigest()
        return plan

    def _rehash_durable_record(self, observation):
        body = dict(observation)
        body.pop("durable_record_sha256", None)
        observation["durable_record_sha256"] = history_access_v2._fingerprint(body)
        return observation

    def _make_partial(self, observation):
        result = self._copy(observation)
        book = result["normalized_book"]
        book["achieved_bid_coverage_bps"] = 0.0
        book["achieved_ask_coverage_bps"] = 0.0
        book_body = dict(book)
        book_body.pop("observation_sha256", None)
        observation_sha = history_access_v2._fingerprint(book_body)
        book["observation_sha256"] = observation_sha
        result["observation_sha256"] = observation_sha
        coverage = result["coverage"]
        coverage["achieved_bid_coverage_bps"] = 0.0
        coverage["achieved_ask_coverage_bps"] = 0.0
        coverage["coverage_complete_bid"] = False
        coverage["coverage_complete_ask"] = False
        coverage["truncated"] = True
        coverage["extrapolation_allowed"] = False
        identity_body = {key: result[key] for key in ("provider_id", "instrument_id", "book_kind", "observation_id")}
        result["durable_identity_sha256"] = history_access_v2._fingerprint(identity_body)
        return self._rehash_durable_record(result)

    def test_g2b_arbitrary_history_horizon_is_absent(self):
        binding = {"locator_pattern": resolution_v2.G2B_LOCATOR_PATTERN}
        start = 1704067200000
        paths = resolution_v2._g2b_day_paths(binding, start, start + 371 * 86400000)
        self.assertEqual(len(paths), 371)

    def test_g2b_legacy_only_successor_only_and_mixed_resolution_and_read(self):
        successor = self._actual_successor_observation()
        successor_ts = successor["observation_time_ms"]
        successor_known = history_access_v2._parse_utc_ms(successor["known_at_utc"])
        legacy_ts = successor_ts - 60000
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            legacy_payload = self._write_legacy(root, legacy_ts)
            legacy_plan = self._plan(root, legacy_ts, legacy_ts + 1, legacy_ts + 1000)
            self.assertEqual([row["schema_class"] for row in legacy_plan["segments"]], [resolution_v2.G2B_LEGACY_CLASS])
            legacy_rows, legacy_diag = self._read(root, legacy_plan)
            self.assertEqual(legacy_rows[0]["schema_class"], resolution_v2.G2B_LEGACY_CLASS)
            self.assertEqual(legacy_rows[0]["value"], legacy_payload)
            self.assertEqual(legacy_diag["mixed_schema_policy"], "EXPLICIT_SCHEMA_BOUNDARY")

            self._write_successor(root, [successor])
            successor_plan = self._plan(root, successor_ts, successor_ts + 1, successor_known)
            self.assertEqual([row["schema_class"] for row in successor_plan["segments"]], [resolution_v2.G2B_SUCCESSOR_CLASS])
            successor_rows, successor_diag = self._read(root, successor_plan)
            self.assertEqual(successor_rows[0]["schema_class"], resolution_v2.G2B_SUCCESSOR_CLASS)
            self.assertEqual(successor_rows[0]["durable_identity_sha256"], successor["durable_identity_sha256"])
            self.assertEqual(successor_diag["schema_class_counts"], {resolution_v2.G2B_SUCCESSOR_CLASS: 1})

            mixed_plan = self._plan(root, legacy_ts, successor_ts + 1, successor_known)
            self.assertEqual(
                {row["schema_class"] for row in mixed_plan["segments"]},
                {resolution_v2.G2B_LEGACY_CLASS, resolution_v2.G2B_SUCCESSOR_CLASS},
            )
            mixed_rows, mixed_diag = self._read(root, mixed_plan)
            self.assertEqual(
                {row["schema_class"] for row in mixed_rows},
                {resolution_v2.G2B_LEGACY_CLASS, resolution_v2.G2B_SUCCESSOR_CLASS},
            )
            self.assertEqual(mixed_diag["mixed_schema_policy"], "EXPLICIT_SCHEMA_BOUNDARY")

    def test_g2b_known_at_cutoff_inclusion_exclusion_and_forged_plan_fail_closed(self):
        observation = self._actual_successor_observation()
        timestamp = observation["observation_time_ms"]
        known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
        self.assertGreaterEqual(known_at, timestamp + 1)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            self._write_successor(root, [observation])
            included = self._plan(root, timestamp, timestamp + 1, known_at)
            rows, _ = self._read(root, included)
            self.assertEqual(len(rows), 1)
            excluded, _ = resolution_v2._g2b_successor_segments(root, timestamp, timestamp + 1, known_at - 1)
            self.assertEqual(excluded, [])
            forged = self._copy(included)
            forged["segments"][0]["successor_observations"][0]["known_at_ms"] = known_at + 1
            self._rehash_plan(forged)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.validate_resolution_plan_v2(forged)
            self.assertEqual(caught.exception.code, "G2B_KNOWN_AT_AFTER_CUTOFF")

    def test_g2b_same_identity_same_sha_dedupes_and_different_sha_conflicts(self):
        observation = self._actual_successor_observation()
        timestamp = observation["observation_time_ms"]
        known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            self._write_successor(root, [observation, self._copy(observation)])
            plan = self._plan(root, timestamp, timestamp + 1, known_at)
            self.assertEqual(len(plan["segments"][0]["successor_observations"]), 1)
            rows, _ = self._read(root, plan)
            self.assertEqual(len(rows), 1)

            conflicting = self._copy(observation)
            conflicting["observation_sha256"] = "0" * 64
            self._write_successor(root, [observation, conflicting])
            with self.assertRaises(RuntimeError) as caught:
                self._plan(root, timestamp, timestamp + 1, known_at)
            self.assertIn("G2B_IMMUTABLE_OBSERVATION_CONFLICT", str(caught.exception))

    def test_g2b_unknown_and_missing_schema_and_wrong_family_fail_closed(self):
        observation = self._actual_successor_observation()
        timestamp = observation["observation_time_ms"]
        known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            path = self._write_successor(root, [observation])
            partition = json.loads((root / path).read_text(encoding="utf-8"))
            partition["schema_version"] = "unknown"
            write_json(root / path, partition)
            with self.assertRaises(RuntimeError) as caught:
                self._plan(root, timestamp, timestamp + 1, known_at)
            self.assertIn("G2B_UNKNOWN_LIQUIDITY_PARTITION_SCHEMA", str(caught.exception))

            unknown = self._copy(observation)
            unknown["schema_version"] = "unknown"
            self._write_successor(root, [unknown])
            with self.assertRaises(RuntimeError) as caught:
                self._plan(root, timestamp, timestamp + 1, known_at)
            self.assertIn("G2B_UNKNOWN_LIQUIDITY_OBSERVATION_SCHEMA", str(caught.exception))

            missing = self._copy(observation)
            missing.pop("schema_version")
            self._write_successor(root, [missing])
            with self.assertRaises(RuntimeError) as caught:
                self._plan(root, timestamp, timestamp + 1, known_at)
            self.assertIn("G2B_UNKNOWN_LIQUIDITY_OBSERVATION_SCHEMA", str(caught.exception))

            wrong_family = self._copy(observation)
            wrong_family["history_family"] = "liquidity.parallel-forbidden"
            self._rehash_durable_record(wrong_family)
            self._write_successor(root, [wrong_family])
            plan = self._plan(root, timestamp, timestamp + 1, known_at)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                self._read(root, plan)
            self.assertEqual(caught.exception.code, "G2B_SCHEMA_POLICY_CONFLICT")

    def test_g2b_legacy_successor_coercion_is_forbidden(self):
        successor = self._actual_successor_observation()
        successor_ts = successor["observation_time_ms"]
        successor_known = history_access_v2._parse_utc_ms(successor["known_at_utc"])
        legacy_ts = successor_ts - 60000
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            self._write_legacy(root, legacy_ts)
            legacy_plan = self._plan(root, legacy_ts, legacy_ts + 1, legacy_ts + 1000)
            forged_legacy = self._copy(legacy_plan)
            forged_legacy["segments"][0]["schema_class"] = resolution_v2.G2B_SUCCESSOR_CLASS
            self._rehash_plan(forged_legacy)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.validate_resolution_plan_v2(forged_legacy)
            self.assertEqual(caught.exception.code, "G2B_SUCCESSOR_AS_LEGACY_COERCION_FORBIDDEN")

            self._write_successor(root, [successor])
            successor_plan = self._plan(root, successor_ts, successor_ts + 1, successor_known)
            forged_successor = self._copy(successor_plan)
            forged_successor["segments"][0]["schema_class"] = resolution_v2.G2B_LEGACY_CLASS
            self._rehash_plan(forged_successor)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.validate_resolution_plan_v2(forged_successor)
            self.assertEqual(caught.exception.code, "G2B_LEGACY_AS_SUCCESSOR_COERCION_FORBIDDEN")

    def test_g2b_temporal_and_integrity_mutations_fail_closed(self):
        original = self._actual_successor_observation()
        cases = []

        bad_time = self._copy(original)
        bad_time["known_at_utc"] = iso(original["observation_time_ms"] - 1)
        self._rehash_durable_record(bad_time)
        cases.append((bad_time, "G2B_SCHEMA_POLICY_CONFLICT"))

        bad_book = self._copy(original)
        bad_book["normalized_book"]["bids"] = []
        cases.append((bad_book, "G2B_SCHEMA_POLICY_CONFLICT"))

        bad_identity = self._copy(original)
        bad_identity["durable_identity_sha256"] = "0" * 64
        cases.append((bad_identity, "G2B_SCHEMA_POLICY_CONFLICT"))

        bad_quantity = self._copy(original)
        bad_quantity["quantity_semantics"]["quantity_sha256"] = "0" * 64
        self._rehash_durable_record(bad_quantity)
        cases.append((bad_quantity, "G2B_SCHEMA_POLICY_CONFLICT"))

        bad_coverage = self._copy(original)
        bad_coverage["coverage"]["achieved_bid_coverage_bps"] = -1
        self._rehash_durable_record(bad_coverage)
        cases.append((bad_coverage, "G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN"))

        bad_truncated = self._copy(original)
        bad_truncated["coverage"]["coverage_complete_bid"] = True
        bad_truncated["coverage"]["coverage_complete_ask"] = True
        bad_truncated["coverage"]["truncated"] = True
        self._rehash_durable_record(bad_truncated)
        cases.append((bad_truncated, "G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN"))

        for observation, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                    history_access_v2._validate_g2b_observation(observation)
                self.assertEqual(caught.exception.code, expected_code)

    def test_g2b_partial_truncated_and_no_extrapolation_fidelity(self):
        observation = self._make_partial(self._actual_successor_observation())
        timestamp = observation["observation_time_ms"]
        known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            self._write_successor(root, [observation])
            plan = self._plan(root, timestamp, timestamp + 1, known_at)
            rows, _ = self._read(root, plan)
        stored = rows[0]["value"]["coverage"]
        self.assertFalse(stored["coverage_complete_bid"])
        self.assertFalse(stored["coverage_complete_ask"])
        self.assertTrue(stored["truncated"])
        self.assertFalse(stored["extrapolation_allowed"])
        self.assertEqual(stored["history_target_bps"], "500")

    def test_g2b_plan_uses_only_declared_durable_resources_no_provider_or_current_fallback(self):
        observation = self._actual_successor_observation()
        timestamp = observation["observation_time_ms"]
        known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._base_root(root)
            self._write_successor(root, [observation])
            plan = self._plan(root, timestamp, timestamp + 1, known_at)
        self.assertTrue(plan["segments"])
        for segment in plan["segments"]:
            self.assertEqual(segment["storage"], "GIT_WARM_RESOURCE")
            self.assertEqual(segment["source_manifest_path"], resolution_v2.G2B_CONTRACT_PATH)
            self.assertNotIn("browser_download_url", segment)
        self.assertEqual(plan["authority"]["d9_activation_status"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual(plan["authority"]["catalog_projection"], "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG")


if __name__ == "__main__":
    unittest.main()
