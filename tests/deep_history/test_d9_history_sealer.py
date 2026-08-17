from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from history_sealer import build_ab, detect, month_bounds, write_index


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


class D9HistorySealerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "history/binance/ETHUSDT/1h/2026").mkdir(parents=True)
        (self.root / "history").mkdir(exist_ok=True)
        legacy = {
            "series_inventory":[
                {
                    "provider":"binance",
                    "instrument":"ETHUSDT",
                    "interval_or_metric":"1h",
                    "last_timestamp":datetime(2026, 1, 31, 23, tzinfo=timezone.utc).timestamp().__int__()*1000,
                }
            ]
        }
        (self.root / "history/release-manifest.json").write_text(compact(legacy))

    def tearDown(self):
        self.temp.cleanup()

    def write_month(self, year: int, month: int, *, complete: bool = True):
        start, end = month_bounds(year, month)
        rows = []
        cursor = start
        while cursor < end:
            rows.append([cursor,"1","2","0.5","1.5","10",cursor+3599999])
            cursor += 3600000
        if not complete:
            rows.pop(len(rows)//2)
        payload = {
            "schema_version":"1.0.0",
            "provider":"binance",
            "symbol":"ETHUSDT",
            "interval":"1h",
            "columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms"],
            "closed_only":True,
            "records":rows,
        }
        path = self.root / f"history/binance/ETHUSDT/1h/{year}/{month:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(compact(payload))
        return path

    def test_completed_month_after_legacy_cold_is_eligible(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        found = detect(as_of, self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["generation_id"], "history-grid-v1-2026-02")
        self.assertEqual(found[0]["series_id"], "spot.binance-spot.ETHUSDT.ohlcv.1h")

    def test_incomplete_month_fails_closed_as_not_eligible(self):
        self.write_month(2026, 2, complete=False)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(detect(as_of, self.root), [])

    def test_active_month_is_never_sealed(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 2, 20, tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(detect(as_of, self.root), [])

    def test_legacy_cold_overlap_is_not_republished(self):
        self.write_month(2026, 1)
        as_of = int(datetime(2026, 2, 2, tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(detect(as_of, self.root), [])

    def test_build_ab_is_byte_deterministic_and_does_not_cleanup_warm(self):
        warm = self.write_month(2026, 2)
        before = warm.read_bytes()
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        manifests = build_ab(as_of, self.root / "work", self.root)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(warm.read_bytes(), before)
        manifest = manifests[0]
        self.assertEqual(manifest["state"], "CANDIDATE")
        self.assertEqual(manifest["publication"]["activation_status"], "NOT_ACTIVE")
        self.assertEqual(manifest["publication"]["cross_boundary_semantic_read"], "NOT_RUN")
        self.assertEqual(manifest["publication"]["publish_status"], "NOT_RUN")

    def test_candidate_index_never_claims_active_authority(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        manifests = build_ab(as_of, self.root / "work", self.root)
        manifests[0]["publication"]["publish_status"] = "PASS"
        index = write_index(manifests, self.root / "candidate-index.json")
        self.assertEqual(index["status"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual(index["legacy_cold_manifest"], "history/release-manifest.json")
        self.assertEqual(index["generations"][0]["authority_status"], "CANDIDATE_NOT_ACTIVE")


if __name__ == "__main__":
    unittest.main()
