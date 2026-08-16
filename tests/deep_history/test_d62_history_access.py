import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools import capability_index as ci
from tools.history_access import (
    HistoryAccessError,
    _cache_path,
    compact as history_compact,
    materialize_resolution_plan,
    validate_resolution_plan,
)

STEP = 300000
START = 1640995200000
SERIES_ID = "spot.binance-spot.ETHUSDT.ohlcv.5m"


def record(ts, price):
    return [ts, str(price), str(price + 1), str(price - 1), str(price + 0.5), "10", ts + STEP - 1]


def warm_payload(records):
    return {
        "schema_version": "1.0.0",
        "provider": "binance",
        "symbol": "ETHUSDT",
        "interval": "5m",
        "columns": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms"],
        "records": records,
    }


def cold_payload(records):
    return {
        "schema_version": "1.0.0",
        "provider": "binance",
        "instrument": "ETHUSDT",
        "interval_or_metric": "5m",
        "columns": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms"],
        "records": records,
    }


def encoded(value):
    return (json.dumps(value, separators=(",", ":")) + "\n").encode()


def segment(storage, raw, left, right, *, path=None, url=None, suffix="x"):
    result = {
        "segment_id": f"{storage}:{suffix}",
        "storage": storage,
        "source_manifest_path": "history/release-manifest.json" if storage == "GITHUB_RELEASE_ASSET" else "history/manifest.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "first_timestamp_ms": left,
        "last_timestamp_ms": right - STEP,
        "read_start_ms": left,
        "read_end_ms": right,
        "source_provider": "binance",
        "instrument": "ETHUSDT",
        "source_interval_or_metric": "5m",
    }
    if storage == "GITHUB_RELEASE_ASSET":
        result.update({
            "release_tag": "history-binance-spot-v1",
            "asset_id": 1 if suffix == "x" else 2,
            "asset_name": f"asset-{suffix}.json",
            "browser_download_url": url or f"https://example.invalid/{suffix}.json",
            "immutable": True,
        })
    else:
        result["resource_path"] = path or f"history/warm-{suffix}.json"
    return result


def plan_for(segments, end=START + 4 * STEP):
    plan = {
        "schema_version": "market-data-resolution-plan/1.0.0",
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {
            "route_policy": "bridge-contract.json",
            "capability_index": "history/capability-index.json",
            "cold_manifest": "history/release-manifest.json",
            "hot_manifest": "history/manifest.json",
        },
        "request": {"series_id": SERIES_ID, "start_ms": START, "end_ms": end, "cutoff_ms": None},
        "series": {
            "series_id": SERIES_ID,
            "profile_id": "binance-spot.history.max-available.hot",
            "instrument": "ETHUSDT",
            "series": "ohlcv",
            "interval": "5m",
            "source_interval_or_metric": "5m",
            "provider_id": "binance-spot",
            "source_provider": "binance",
            "history_mode": "MAX_AVAILABLE",
            "availability_status": "PASS",
            "interval_ms": STEP,
        },
        "segments": segments,
    }
    plan["plan_sha256"] = hashlib.sha256(history_compact(plan)).hexdigest()
    return plan


class Response:
    def __init__(self, raw):
        self.stream = io.BytesIO(raw)
    def read(self, amount=-1):
        return self.stream.read(amount)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class CapabilityResolutionFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "history/odd-layout").mkdir(parents=True)
        cold = encoded(cold_payload([record(START, 100), record(START + STEP, 101)]))
        warm = encoded(warm_payload([record(START + 2 * STEP, 102), record(START + 3 * STEP, 103)]))
        self.warm_path = self.root / "history/odd-layout/not-a-date-name.json"
        self.warm_path.write_bytes(warm)
        profile = "binance-spot.history.max-available.hot"
        index = {
            "schema_version": "1.0.0",
            "catalog_id": "eth-macro-data-bridge-capability-index",
            "generation_policy": "DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
            "authority": {
                "route_policy": "bridge-contract.json",
                "provider_contracts": "contracts/provider-contracts.json",
                "cold_history_manifest": "history/release-manifest.json",
                "hot_history_manifests": ["history/manifest.json"],
            },
            "provider_policies": [
                {"provider_id": "binance-spot", "domain": "spot", "status": "ACTIVE", "authority_role": "PRIMARY"},
                {"provider_id": "binance-usdm", "domain": "derivatives", "status": "DISABLED_BY_POLICY", "authority_role": "FROZEN", "network_calls": 0, "signal_vote": "EXCLUDED"},
            ],
            "profiles": {
                profile: {
                    "provider_id": "binance-spot",
                    "source_provider": "binance",
                    "history_mode": "MAX_AVAILABLE",
                    "availability_status": "PASS",
                    "semantics_ref": None,
                    "cold_manifest_path": "history/release-manifest.json",
                    "release_tag": "history-binance-spot-v1",
                    "hot_manifest_path": "history/manifest.json",
                }
            },
            "series": [{
                "series_id": SERIES_ID,
                "profile_id": profile,
                "instrument": "ETHUSDT",
                "series": "ohlcv",
                "interval": "5m",
                "source_interval_or_metric": "5m",
            }],
            "forward_capabilities": [],
        }
        (self.root / "history/capability-index.json").write_text(json.dumps(index))
        (self.root / "history/manifest.json").write_text(json.dumps({
            "schema_version": "1.0.0",
            "generated_at_utc": "2022-01-02T00:00:00Z",
            "series": [{"provider": "binance", "symbol": "ETHUSDT", "interval": "5m"}],
        }))
        self.asset = {
            "provider": "binance",
            "instrument": "ETHUSDT",
            "interval_or_metric": "5m",
            "release_tag": "history-binance-spot-v1",
            "asset_id": 77,
            "asset_name": "physical-from-manifest.json",
            "browser_download_url": "https://example.invalid/exact-manifest-url",
            "sha256": hashlib.sha256(cold).hexdigest(),
            "size_bytes": len(cold),
            "first_timestamp": START,
            "last_timestamp": START + STEP,
            "integrity_status": "PASS",
            "immutable": True,
        }
        (self.root / "history/release-manifest.json").write_text(json.dumps({
            "schema_version": "1.0.0",
            "generated_at_utc": "2022-01-02T00:00:00Z",
            "storage_backend": "GITHUB_RELEASE_ASSET",
            "asset_inventory": [self.asset],
        }))
        self.old = (ci.ROOT, ci.INDEX_PATH, ci.SCHEMA_PATH)
        ci.ROOT = self.root
        ci.INDEX_PATH = self.root / "history/capability-index.json"
        ci.SCHEMA_PATH = self.root / "schema/capability-index.schema.json"

    def tearDown(self):
        ci.ROOT, ci.INDEX_PATH, ci.SCHEMA_PATH = self.old
        self.temp.cleanup()

    def test_list_describe_are_semantic_only(self):
        rows = ci.list_capabilities()
        self.assertEqual([item["series_id"] for item in rows], [SERIES_ID])
        self.assertEqual(ci.describe_capability(SERIES_ID)["profile"]["release_tag"], "history-binance-spot-v1")

    def test_resolve_uses_exact_manifest_asset_and_discovered_warm_path(self):
        plan = ci.resolve_capability(SERIES_ID, "2022-01-01T00:00:00Z", "2022-01-01T00:20:00Z")
        self.assertEqual([item["storage"] for item in plan["segments"]], ["GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE"])
        cold, warm = plan["segments"]
        self.assertEqual(cold["asset_name"], self.asset["asset_name"])
        self.assertEqual(cold["browser_download_url"], self.asset["browser_download_url"])
        self.assertEqual(cold["sha256"], self.asset["sha256"])
        self.assertEqual(warm["resource_path"], "history/odd-layout/not-a-date-name.json")
        self.assertFalse((self.root / "history/history-catalog.json").exists())

    def test_resolution_plan_is_byte_deterministic(self):
        args = (SERIES_ID, "2022-01-01T00:00:00Z", "2022-01-01T00:20:00Z")
        self.assertEqual(ci.compact(ci.resolve_capability(*args)), ci.compact(ci.resolve_capability(*args)))

    def test_point_in_time_cutoff_rejects_future_known_manifests(self):
        with self.assertRaisesRegex(RuntimeError, "HISTORY_NOT_FOUND"):
            ci.resolve_capability(SERIES_ID, "2022-01-01T00:00:00Z", "2022-01-01T00:20:00Z", "2022-01-01T12:00:00Z")

    def test_unknown_series_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "UNKNOWN_SERIES_ID"):
            ci.describe_capability("spot.binance-spot.UNKNOWN.ohlcv.5m")


class HistoryAccessTests(unittest.TestCase):
    def test_mixed_cold_warm_merge_is_deterministic(self):
        cold = encoded(cold_payload([record(START, 100), record(START + STEP, 101)]))
        warm = encoded(warm_payload([record(START + 2 * STEP, 102), record(START + 3 * STEP, 103)]))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "history/warm.json"
            path.parent.mkdir()
            path.write_bytes(warm)
            segments = [
                segment("GITHUB_RELEASE_ASSET", cold, START, START + 2 * STEP, url="https://example.invalid/cold.json"),
                segment("GIT_WARM_RESOURCE", warm, START + 2 * STEP, START + 4 * STEP, path="history/warm.json"),
            ]
            plan = plan_for(segments)
            def opener(url, timeout=0):
                self.assertEqual(url, "https://example.invalid/cold.json")
                return Response(cold)
            rows, diagnostics = materialize_resolution_plan(plan, root=root, cache_dir=root / "cache", opener=opener)
            self.assertEqual([row[0] for row in rows], [START + i * STEP for i in range(4)])
            self.assertEqual((diagnostics["status"], diagnostics["gap_count"], diagnostics["duplicates"]), ("PASS", 0, 0))

    def test_reader_needs_only_resolution_plan_not_catalog_or_manifests(self):
        warm = encoded(warm_payload([record(START, 100)]))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "only/physical.json"
            path.parent.mkdir()
            path.write_bytes(warm)
            plan = plan_for([segment("GIT_WARM_RESOURCE", warm, START, START + STEP, path="only/physical.json")], end=START + STEP)
            rows, diagnostics = materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
            self.assertEqual(len(rows), 1)
            self.assertEqual(diagnostics["status"], "PASS")
            self.assertFalse((root / "history/manifest.json").exists())

    def test_corrupt_cache_is_not_a_cache_hit(self):
        cold = encoded(cold_payload([record(START, 100)]))
        cold_segment = segment("GITHUB_RELEASE_ASSET", cold, START, START + STEP)
        plan = plan_for([cold_segment], end=START + STEP)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = root / "cache"
            cache.mkdir()
            _cache_path(cold_segment, cache).write_bytes(b"corrupt")
            calls = []
            def opener(url, timeout=0):
                calls.append(url)
                return Response(cold)
            _, diagnostics = materialize_resolution_plan(plan, root=root, cache_dir=cache, opener=opener)
            self.assertEqual(len(calls), 1)
            self.assertEqual(diagnostics["status"], "PASS")

    def test_checksum_mismatch_fails_closed(self):
        cold = encoded(cold_payload([record(START, 100)]))
        wrong = encoded(cold_payload([record(START, 999)]))
        plan = plan_for([segment("GITHUB_RELEASE_ASSET", cold, START, START + STEP)], end=START + STEP)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(HistoryAccessError) as ctx:
                materialize_resolution_plan(plan, root=Path(td), cache_dir=Path(td) / "cache", opener=lambda *a, **k: Response(wrong))
            self.assertEqual(ctx.exception.code, "CHECKSUM_MISMATCH")

    def test_gap_strict_fails_and_permissive_degrades(self):
        warm = encoded(warm_payload([record(START, 100), record(START + 2 * STEP, 102)]))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "warm.json"
            path.write_bytes(warm)
            plan = plan_for([segment("GIT_WARM_RESOURCE", warm, START, START + 3 * STEP, path="warm.json")], end=START + 3 * STEP)
            with self.assertRaises(HistoryAccessError) as ctx:
                materialize_resolution_plan(plan, root=root, cache_dir=root / "cache", mode="strict")
            self.assertEqual(ctx.exception.code, "DATA_GAP")
            rows, diagnostics = materialize_resolution_plan(plan, root=root, cache_dir=root / "cache", mode="permissive")
            self.assertEqual(len(rows), 2)
            self.assertEqual((diagnostics["status"], diagnostics["gap_count"]), ("DEGRADED", 1))

    def test_duplicate_strict_fails(self):
        cold = encoded(cold_payload([record(START, 100)]))
        warm = encoded(warm_payload([record(START, 100)]))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "warm.json"
            path.write_bytes(warm)
            segments = [
                segment("GITHUB_RELEASE_ASSET", cold, START, START + STEP, suffix="a"),
                segment("GIT_WARM_RESOURCE", warm, START, START + STEP, path="warm.json", suffix="b"),
            ]
            segments.sort(key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"]))
            plan = plan_for(segments, end=START + STEP)
            with self.assertRaises(HistoryAccessError) as ctx:
                materialize_resolution_plan(plan, root=root, cache_dir=root / "cache", opener=lambda *a, **k: Response(cold))
            self.assertEqual(ctx.exception.code, "DUPLICATE_TIMESTAMP")

    def test_plan_digest_is_authoritative(self):
        warm = encoded(warm_payload([record(START, 100)]))
        plan = plan_for([segment("GIT_WARM_RESOURCE", warm, START, START + STEP, path="warm.json")], end=START + STEP)
        validate_resolution_plan(plan)
        plan["segments"][0]["resource_path"] = "guessed.json"
        with self.assertRaises(HistoryAccessError) as ctx:
            validate_resolution_plan(plan)
        self.assertEqual(ctx.exception.code, "INVALID_RESOLUTION_PLAN")


if __name__ == "__main__":
    unittest.main()
