from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import _history_sealer_core as sealer_core
import history_access_v2


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


class D9CrossBoundaryEncodingTests(unittest.TestCase):
    def test_d9_cold_ohlcv_is_resolution_plan_self_describing(self):
        start = 1782864000000
        end = start + 3600000
        generation_id = "history-grid-v1-2026-07"
        candidate = {
            "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "series_kind": "REGULAR_GRID",
            "start_ms": start,
            "end_ms": end,
            "rows": [[start, "1800", "1810", "1790", "1805", "120", end - 1]],
            "known_gaps": [],
        }
        payload = sealer_core._asset_payload(candidate, generation_id)
        raw = history_access_v2.compact(payload)
        segment = {
            "segment_id": "generation-cold:fixture:1",
            "storage": "GITHUB_RELEASE_ASSET",
            "source_manifest_path": "history/generations/history-grid-v1-2026-07.json",
            "release_tag": generation_id,
            "asset_id": 1,
            "asset_name": "spot.binance-spot.ETHUSDT.ohlcv.1h.json",
            "browser_download_url": "https://example.invalid/d9-cold.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "immutable": True,
            "generation_id": generation_id,
            "first_timestamp_ms": start,
            "last_timestamp_ms": start,
            "read_start_ms": start,
            "read_end_ms": end,
            "source_provider": "binance",
            "instrument": "ETHUSDT",
            "source_interval_or_metric": "1h",
            "known_gaps": [],
            "physical_descriptor": {
                "release_tag": generation_id,
                "asset_id": 1,
                "asset_name": "spot.binance-spot.ETHUSDT.ohlcv.1h.json",
                "browser_download_url": "https://example.invalid/d9-cold.json",
                "immutable": True,
            },
        }
        plan = {
            "schema_version": "market-data-resolution-plan/2.0.0",
            "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
            "authority": {
                "active_capability_index": "history/capability-index.json",
                "catalog_projection": "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG",
                "d9_activation_status": "CANDIDATE_NOT_ACTIVE",
                "qualification_mode": True,
            },
            "request": {
                "series_id": candidate["series_id"],
                "start_ms": start,
                "end_ms": end,
                "effective_start_ms": start,
                "cutoff_ms": None,
                "current_policy": "FINALIZED_ONLY",
            },
            "series": {
                "series_id": candidate["series_id"],
                "series_kind": "OHLCV",
                "coverage_semantics": "FIXED_GRID",
                "finality_policy": "FINALIZED_ONLY",
                "revision_policy": "IMMUTABLE",
                "interval_ms": 3600000,
                "coverage_boundary_evidence": {
                    "kind": "AVAILABLE_START",
                    "declared_start_ms": start,
                    "requested_start_ms": start,
                    "effective_start_ms": start,
                },
            },
            "segments": [segment],
        }
        plan["plan_sha256"] = hashlib.sha256(history_access_v2.compact(plan)).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                plan,
                root=Path(temp),
                cache_dir=Path(temp) / "cache",
                opener=lambda *_args, **_kwargs: _Response(raw),
            )
        self.assertEqual(observations[0]["value"]["close"], "1805")
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["receipt"]["observation_count"], 1)


if __name__ == "__main__":
    unittest.main()
