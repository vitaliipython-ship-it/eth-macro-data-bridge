from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import _history_access_v1 as history_access_v1
import history_access_v2

SERIES_ID = "spot.binance-spot.ETHUSDT.ohlcv.1h"
START = 1785542400000
STEP = 3_600_000


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def write_json(path: Path, value) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = compact(value)
    path.write_bytes(raw)
    return raw


def ohlcv_payload(timestamp: int, close: str = "1.5") -> dict:
    return {
        "schema_version": "1.0.0",
        "provider": "binance",
        "symbol": "ETHUSDT",
        "interval": "1h",
        "columns": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms"],
        "records": [[timestamp, "1", "2", "0.5", close, "10", timestamp + STEP - 1]],
    }


def cold_payload(timestamp: int) -> dict:
    return {
        "schema_version": "market-data-cold-asset/1.1.0",
        "generation_id": "fixture-cold-generation",
        "series_id": SERIES_ID,
        "series_kind": "OHLCV",
        "record_encoding": {
            "kind": "POSITIONAL_COLUMNS",
            "columns": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms"],
        },
        "coverage_start_ms": timestamp,
        "coverage_end_ms": timestamp + STEP,
        "known_gaps": [],
        "records": [[timestamp, "1", "2", "0.5", "1.5", "10", timestamp + STEP - 1]],
    }


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


def digest_plan(plan: dict) -> dict:
    body = dict(plan)
    body.pop("plan_sha256", None)
    plan["plan_sha256"] = hashlib.sha256(compact(body)).hexdigest()
    return plan


def segment(
    *,
    segment_id: str,
    storage: str,
    raw: bytes,
    start: int,
    end: int,
    resource_path: str | None = None,
    generation_id: str | None = None,
) -> dict:
    result = {
        "segment_id": segment_id,
        "storage": storage,
        "source_manifest_path": None,
        "resource_path": resource_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "generation_id": generation_id,
        "first_timestamp_ms": start,
        "last_timestamp_ms": start,
        "read_start_ms": start,
        "read_end_ms": end,
        "source_provider": "binance",
        "instrument": "ETHUSDT",
        "source_interval_or_metric": "1h",
        "known_gaps": [],
        "physical_descriptor": {"resource_path": resource_path} if resource_path else {},
    }
    if storage == "GITHUB_RELEASE_ASSET":
        result.update(
            {
                "release_tag": "fixture-cold",
                "asset_id": 1,
                "asset_name": "fixture-cold.json",
                "browser_download_url": "https://example.invalid/fixture-cold.json",
                "immutable": True,
            }
        )
    if storage == "HOT_CURRENT_RESOURCE":
        result["physical_descriptor"] = {
            "resource_path": resource_path,
            "authority_ref": "fixture-d8-hot",
            "resource_id": "fixture-hot-resource",
            "locator_authority": "CANONICAL_CONTROL_PLANE",
            "transport_authority": "CANONICAL_CONTROL_PLANE",
            "known_at": "2026-08-01T02:00:01Z",
            "retrieved_at": "2026-08-01T02:00:01Z",
            "provider_timestamp_at": "2026-08-01T02:00:00Z",
            "freshness_status": "LIVE_USABLE",
        }
    return result


def base_plan(segments: list[dict], *, current_policy: str = "INCLUDE_CURRENT_PROVISIONAL") -> dict:
    return digest_plan(
        {
            "schema_version": "market-data-resolution-plan/2.0.0",
            "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
            "authority": {
                "qualification_mode": True,
                "d9_activation_status": "CANDIDATE_NOT_ACTIVE",
            },
            "request": {
                "series_id": SERIES_ID,
                "start_ms": START,
                "end_ms": START + 3 * STEP,
                "effective_start_ms": START,
                "cutoff_ms": None,
                "current_policy": current_policy,
            },
            "series": {
                "series_id": SERIES_ID,
                "instrument": "ETHUSDT",
                "source_interval_or_metric": "1h",
                "series_kind": "OHLCV",
                "coverage_semantics": "FIXED_GRID",
                "finality_policy": "PROVISIONAL_ALLOWED_EXPLICITLY",
                "revision_policy": "IMMUTABLE",
                "interval_ms": STEP,
                "collection_gaps": [],
            },
            "segments": segments,
            "plan_sha256": "",
        }
    )


class D8D9UnifiedConsumerContinuityReaderPrimitive(unittest.TestCase):
    def fixture(self, root: Path):
        cold_raw = compact(cold_payload(START))
        warm_raw = write_json(root / "history/warm.json", ohlcv_payload(START + STEP))
        hot_raw = write_json(root / "runtime/hot.json", ohlcv_payload(START + 2 * STEP))
        segments = [
            segment(
                segment_id="cold:fixture",
                storage="GITHUB_RELEASE_ASSET",
                raw=cold_raw,
                start=START,
                end=START + STEP,
                generation_id="fixture-cold-generation",
            ),
            segment(
                segment_id="warm:fixture",
                storage="GIT_WARM_RESOURCE",
                raw=warm_raw,
                start=START + STEP,
                end=START + 2 * STEP,
                resource_path="history/warm.json",
            ),
            segment(
                segment_id="hot:fixture",
                storage="HOT_CURRENT_RESOURCE",
                raw=hot_raw,
                start=START + 2 * STEP,
                end=START + 3 * STEP,
                resource_path="runtime/hot.json",
            ),
        ]
        return cold_raw, segments

    def test_one_resolution_plan_materializes_cold_warm_hot_as_one_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cold_raw, segments = self.fixture(root)
            plan = base_plan(segments)
            rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                plan,
                root=root,
                cache_dir=root / "cache",
                opener=lambda *_args, **_kwargs: _Response(cold_raw),
            )

        self.assertEqual([row["timestamp_ms"] for row in rows], [START, START + STEP, START + 2 * STEP])
        self.assertEqual(len(rows), 3)
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["internal_gap_count"], 0)
        self.assertEqual(diagnostics["overlap_deduped_timestamps_ms"], [])
        self.assertEqual(
            [source["storage"] for source in diagnostics["sources"]],
            ["GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE", "HOT_CURRENT_RESOURCE"],
        )
        self.assertEqual(diagnostics["receipt"]["observation_count"], 3)
        self.assertEqual(diagnostics["receipt"]["resolution_plan_sha256"], plan["plan_sha256"])
        self.assertEqual(rows[-1]["finality"], "PROVISIONAL")
        self.assertTrue(all("storage" not in row and "segment_id" not in row for row in rows))

    def test_missing_hot_fixed_grid_interval_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cold_raw, segments = self.fixture(root)
            plan = base_plan(segments[:2])
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.materialize_resolution_plan_v2(
                    plan,
                    root=root,
                    cache_dir=root / "cache",
                    opener=lambda *_args, **_kwargs: _Response(cold_raw),
                )
        self.assertEqual(caught.exception.code, "DATA_GAP")

    def test_cross_tier_payload_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cold_raw = compact(cold_payload(START))
            conflict_raw = write_json(root / "history/conflict.json", ohlcv_payload(START, close="1.75"))
            segments = [
                segment(
                    segment_id="cold:fixture",
                    storage="GITHUB_RELEASE_ASSET",
                    raw=cold_raw,
                    start=START,
                    end=START + STEP,
                    generation_id="fixture-cold-generation",
                ),
                segment(
                    segment_id="warm:conflict",
                    storage="GIT_WARM_RESOURCE",
                    raw=conflict_raw,
                    start=START,
                    end=START + STEP,
                    resource_path="history/conflict.json",
                ),
            ]
            plan = base_plan(segments)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.materialize_resolution_plan_v2(
                    plan,
                    root=root,
                    cache_dir=root / "cache",
                    opener=lambda *_args, **_kwargs: _Response(cold_raw),
                )
        self.assertEqual(caught.exception.code, "DUPLICATE_CONFLICT")

    def test_finalized_only_rejects_hot_segment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _cold_raw, segments = self.fixture(root)
            plan = base_plan(segments, current_policy="FINALIZED_ONLY")
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as caught:
                history_access_v2.validate_resolution_plan_v2(plan)
        self.assertEqual(caught.exception.code, "INVALID_RESOLUTION_PLAN")

    def test_missing_hot_resource_does_not_fallback_to_network(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = compact(ohlcv_payload(START + 2 * STEP))
            hot = segment(
                segment_id="hot:missing",
                storage="HOT_CURRENT_RESOURCE",
                raw=raw,
                start=START + 2 * STEP,
                end=START + 3 * STEP,
                resource_path="runtime/missing-hot.json",
            )
            plan = base_plan([hot])
            network_calls = []

            def forbidden_opener(*args, **kwargs):
                network_calls.append((args, kwargs))
                raise AssertionError("reader attempted network fallback")

            with self.assertRaises(history_access_v1.HistoryAccessError) as caught:
                history_access_v2.materialize_resolution_plan_v2(
                    plan,
                    root=root,
                    cache_dir=root / "cache",
                    opener=forbidden_opener,
                )
        self.assertEqual(caught.exception.code, "PARTITION_NOT_FOUND")
        self.assertEqual(network_calls, [])


if __name__ == "__main__":
    unittest.main()
