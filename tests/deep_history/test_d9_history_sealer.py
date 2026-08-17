from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from history_sealer import (
    build_ab,
    declared_regular_resources,
    detect,
    high_cardinality_warm_ready,
    install_candidate_control_plane,
    month_bounds,
    write_index,
)


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


class D9HistorySealerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "history/binance/ETHUSDT/1h/2026").mkdir(parents=True)
        (self.root / "derivatives").mkdir(exist_ok=True)
        (self.root / "options").mkdir(exist_ok=True)
        (self.root / "contracts").mkdir(exist_ok=True)
        jan_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
        jan_last = int(datetime(2026, 1, 31, 23, tzinfo=timezone.utc).timestamp()*1000)
        legacy = {
            "series_inventory":[
                {
                    "provider":"binance",
                    "instrument":"ETHUSDT",
                    "interval_or_metric":"1h",
                    "last_timestamp":jan_last,
                }
            ]
        }
        (self.root / "history/release-manifest.json").write_text(compact(legacy))
        (self.root / "history/manifest.json").write_text(
            compact(
                {
                    "schema_version":"1.0.0",
                    "series":[
                        {
                            "provider":"binance",
                            "symbol":"ETHUSDT",
                            "interval":"1h",
                            "first_timestamp":jan_start,
                            "last_timestamp":jan_last,
                            "historical_backfill":"PASS",
                            "provider_history_limit":False,
                        }
                    ],
                }
            )
        )
        (self.root / "derivatives/history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[]}))
        (self.root / "derivatives/deribit-history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[],"d9_candidate_series":[]}))
        (self.root / "options/history-manifest.json").write_text(
            compact(
                {
                    "schema_version":"1.0.0",
                    "deribit_dvol":{"historical_backfill":"UNAVAILABLE_BY_PROVIDER"},
                }
            )
        )
        self.write_policy(status="BLOCKED_TEST", enabled=False)

    def tearDown(self):
        self.temp.cleanup()

    def write_policy(self, *, status: str, enabled: bool):
        (self.root / "contracts/d9-sealing-candidate.json").write_text(
            compact(
                {
                    "generation_membership":{
                        "policy_version":"d9-generation-membership/1.0.0",
                        "authority":"CANONICAL_WARM_MANIFESTS",
                    },
                    "finalization_policy":{
                        "policy_version":"d9-cold-finalization/1.0.0",
                        "regular_grid_default_finalization_lag_seconds":3600,
                        "provider_overrides":{"kraken-futures":{"ingestion_stabilization_source":"derivatives/metric-semantics.json"}},
                        "metric_overrides":{},
                        "revision_class_lag_seconds":{
                            "STRICT_OVERLAP_REQUIRED":0,
                            "WINDOW_ANCHORED_CUMULATIVE":0,
                            "PROVIDER_REVISABLE_SNAPSHOT":10800,
                        },
                        "missing_required_revision_policy":"FAIL_CLOSED",
                    },
                    "high_cardinality_warm":{
                        "status":status,
                        "cold_sealing_enabled":enabled,
                    },
                }
            )
        )

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
        self.assertEqual(manifest["schema_version"], "market-data-history-generation/1.1.0")
        self.assertEqual(manifest["state"], "CANDIDATE")
        self.assertEqual(manifest["membership"]["expected_series_set"], manifest["membership"]["actual_complete_series_set"])
        self.assertEqual(manifest["membership"]["blocked_series_set"], [])
        self.assertEqual(manifest["membership"]["missing_series_set"], [])
        self.assertTrue(manifest["finalization"]["period_closed"])
        self.assertEqual(manifest["publication"]["activation_status"], "NOT_ACTIVE")
        self.assertEqual(manifest["publication"]["cross_boundary_semantic_read"], "NOT_RUN")
        self.assertEqual(manifest["publication"]["publish_status"], "NOT_RUN")

    def test_candidate_index_never_claims_active_authority(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        manifests = build_ab(as_of, self.root / "work", self.root)
        manifests[0]["publication"]["publish_status"] = "PASS"
        index = write_index(manifests, self.root / "candidate-index.json")
        self.assertEqual(index["schema_version"], "market-data-history-generation-index/1.1.0")
        self.assertEqual(index["status"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual(index["legacy_cold_manifest"], "history/release-manifest.json")
        self.assertEqual(index["generations"][0]["authority_status"], "CANDIDATE_NOT_ACTIVE")

    def test_verified_candidate_control_plane_does_not_replace_legacy_manifest(self):
        warm = self.write_month(2026, 2)
        legacy_before = (self.root / "history/release-manifest.json").read_bytes()
        warm_before = warm.read_bytes()
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        manifests = build_ab(as_of, self.root / "work", self.root)
        manifests[0]["publication"].update({
            "publish_status":"PASS","readback_status":"PASS","size_match":"PASS","sha256_match":"PASS","release_immutable":True,
        })
        index = install_candidate_control_plane(manifests, self.root)
        candidate = self.root / "history/generations/history-grid-v1-2026-02.json"
        self.assertTrue(candidate.is_file())
        self.assertTrue((self.root / "history/generation-index.json").is_file())
        self.assertEqual(index["status"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual((self.root / "history/release-manifest.json").read_bytes(), legacy_before)
        self.assertEqual(warm.read_bytes(), warm_before)

    def test_candidate_index_preserves_previous_generations(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        first = build_ab(as_of, self.root / "work-a", self.root)
        first[0]["publication"]["publish_status"] = "PASS"
        install_candidate_control_plane(first, self.root)
        old_index = json.loads((self.root / "history/generation-index.json").read_text())
        self.assertEqual(len(old_index["generations"]), 1)
        self.write_month(2026, 3)
        april_as_of = int(datetime(2026, 4, 2, tzinfo=timezone.utc).timestamp()*1000)
        both = build_ab(april_as_of, self.root / "work-b", self.root)
        march_manifest = next(item for item in both if item["period"] == "2026-03")
        march_manifest["publication"]["publish_status"] = "PASS"
        merged = install_candidate_control_plane([march_manifest], self.root)
        self.assertEqual({row["period"] for row in merged["generations"]}, {"2026-02","2026-03"})

    def test_retry_same_generation_preserves_installed_manifest(self):
        self.write_month(2026, 2)
        as_of = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp()*1000)
        first = build_ab(as_of, self.root / "work-a", self.root)
        first[0]["publication"]["publish_status"] = "PASS"
        install_candidate_control_plane(first, self.root)
        path = self.root / "history/generations/history-grid-v1-2026-02.json"
        before = path.read_bytes()
        second = build_ab(as_of, self.root / "work-b", self.root)
        self.assertEqual(second[0]["generation_id"], "history-grid-v1-2026-02")
        second[0]["publication"]["publish_status"] = "PASS"
        install_candidate_control_plane(second, self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_high_cardinality_sealing_requires_explicit_ready_policy(self):
        self.assertFalse(high_cardinality_warm_ready(self.root))
        self.write_policy(status="READY", enabled=True)
        self.assertTrue(high_cardinality_warm_ready(self.root))
        self.write_policy(status="READY", enabled=False)
        self.assertFalse(high_cardinality_warm_ready(self.root))

    def test_manifest_not_rglob_defines_dvol_authority(self):
        options_dir = self.root / "options/archive/2026/08/14/deribit"
        options_dir.mkdir(parents=True)
        timestamp = 1786676400000
        canonical = {
            "schema_version":"1.0.0","provider":"deribit","metric":"ETH-DVOL","resolution_seconds":3600,
            "columns":["timestamp_ms","open","high","low","close"],
            "records":[[timestamp,48.49,48.52,48.4,48.5]],
        }
        legacy = {"schema_version":"1.0.0","provider":"deribit","metric":"ETH-DVOL","resolution_minutes":60,"records":[[timestamp,48.49,48.5,48.49,48.5]]}
        canonical_path = options_dir / "ETH-volatility-index-1h.json"
        legacy_path = options_dir / "ETH-volatility-index.json"
        canonical_path.write_text(compact(canonical))
        legacy_path.write_text(compact(legacy))
        (self.root / "options/history-manifest.json").write_text(
            compact({"schema_version":"1.0.0","deribit_dvol":{"historical_backfill":"PASS","first_timestamp":timestamp,"last_timestamp":timestamp}})
        )
        resources = declared_regular_resources(self.root)
        dvol = resources["options.deribit-options.ETH.dvol.1h"]
        self.assertEqual(dvol["rows"][timestamp], canonical["records"][0])
        paths = {row["path"] for row in dvol["resources"]}
        self.assertIn(canonical_path.relative_to(self.root).as_posix(), paths)
        self.assertNotIn(legacy_path.relative_to(self.root).as_posix(), paths)
        self.assertTrue(legacy_path.exists())

    def test_undeclared_physical_series_never_creates_authority(self):
        rogue = self.root / "history/binance/ROGUE/1h/2026/02.json"
        rogue.parent.mkdir(parents=True)
        rogue.write_text(compact({"provider":"binance","symbol":"ROGUE","interval":"1h","records":[[1769904000000,"1","1","1","1","1",1769907599999]]}))
        resources = declared_regular_resources(self.root)
        self.assertNotIn("spot.binance-spot.ROGUE.ohlcv.1h", resources)
        self.assertTrue(rogue.exists())


if __name__ == "__main__":
    unittest.main()
