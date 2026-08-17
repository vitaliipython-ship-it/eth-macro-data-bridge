from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import history_sealer as sealer


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def fingerprint(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class D9RevisionSealingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for rel in ("history", "derivatives/archive", "derivatives/revisions/evidence", "derivatives/revisions/source", "options", "contracts"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        self.start, self.end = sealer.month_bounds(2026, 2)
        self.target_ts = self.end - 300000
        (self.root / "history/release-manifest.json").write_text(compact({"series_inventory": []}), encoding="utf-8")
        (self.root / "history/manifest.json").write_text(compact({"schema_version":"1.0.0","series":[]}), encoding="utf-8")
        (self.root / "derivatives/history-manifest.json").write_text(
            compact({
                "schema_version":"1.0.0",
                "series":[{
                    "provider":"kraken-futures",
                    "instrument":"PI_ETHUSD",
                    "metric":"spreads",
                    "first_timestamp":self.start,
                    "last_timestamp":self.target_ts,
                    "historical_backfill":"PASS",
                }],
            }),
            encoding="utf-8",
        )
        (self.root / "derivatives/deribit-history-manifest.json").write_text(compact({"schema_version":"1.0.0","series":[],"d9_candidate_series":[]}), encoding="utf-8")
        (self.root / "options/history-manifest.json").write_text(compact({"schema_version":"1.0.0","deribit_dvol":{"historical_backfill":"UNAVAILABLE_BY_PROVIDER"}}), encoding="utf-8")
        (self.root / "derivatives/metric-semantics.json").write_text(
            compact({
                "schema_version":"1.0.0",
                "provider":"kraken-futures",
                "resolution_seconds":300,
                "archive_ingestion":{"stabilization_seconds":1800},
                "metrics":{"spreads":{"classification":"PROVIDER_REVISABLE_SNAPSHOT"}},
            }),
            encoding="utf-8",
        )
        (self.root / "contracts/d9-sealing-candidate.json").write_text(
            compact({
                "generation_membership":{"policy_version":"d9-generation-membership/1.0.0","authority":"CANONICAL_WARM_MANIFESTS"},
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
                "high_cardinality_warm":{"status":"BLOCKED_TEST","cold_sealing_enabled":False},
            }),
            encoding="utf-8",
        )
        rows = [[ts,"1"] for ts in range(self.start, self.end, 300000)]
        archive = self.root / "derivatives/archive/2026/02/28/kraken-futures/PI_ETHUSD-spreads.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(compact({
            "schema_version":"1.0.0",
            "provider":"kraken-futures",
            "instrument":"PI_ETHUSD",
            "metric":"spreads",
            "resolution_seconds":300,
            "records":rows,
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def add_revision(self, *, known_at_ms: int, value: str = "2") -> tuple[Path, Path]:
        source = self.root / f"derivatives/revisions/source/2026/03/01/kraken-futures/PI_ETHUSD-spreads-{known_at_ms}.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(compact({
            "schema_version":"kraken-revision-source-observation/1.0.0",
            "provider":"kraken-futures",
            "instrument":"PI_ETHUSD",
            "metric":"spreads",
            "retrieved_at":iso(known_at_ms),
            "source_routes":["fixture:revision"],
            "observed_rows":[[self.target_ts,value]],
        }), encoding="utf-8")
        evidence = self.root / f"derivatives/revisions/evidence/2026/02/28/kraken-futures/PI_ETHUSD-spreads-rev-{known_at_ms}.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(compact({
            "schema_version":"market-data-provider-revision/1.0.0",
            "revision_id":f"rev-{known_at_ms}",
            "classification":"PROVIDER_REVISABLE_SNAPSHOT",
            "effective_timestamp":self.target_ts,
            "known_at_utc":iso(known_at_ms),
            "provider":"kraken-futures",
            "instrument":"PI_ETHUSD",
            "metric":"spreads",
            "previous_value_fingerprint":fingerprint([self.target_ts,"1"]),
            "observed_value":[self.target_ts,value],
            "source_snapshot_ref":source.relative_to(self.root).as_posix(),
            "revision_of":f"kraken-futures/PI_ETHUSD/spreads/{self.target_ts}",
        }), encoding="utf-8")
        return evidence, source

    def test_qualified_revision_evidence_before_freeze_materializes_into_cold(self):
        evidence, source = self.add_revision(known_at_ms=self.end + 7200*1000)
        manifests = sealer.build(self.end + 14400*1000, self.root / "out", self.root)
        self.assertEqual(len(manifests), 1)
        manifest = manifests[0]
        asset = Path(manifest["_asset_paths"][manifest["assets"][0]["asset_name"]])
        payload = json.loads(asset.read_text(encoding="utf-8"))
        by_ts = {int(row[0]): row for row in payload["records"]}
        self.assertEqual(by_ts[self.target_ts], [self.target_ts,"2"])
        provenance = {row["path"] for row in manifest["assets"][0]["source_warm_resources"]}
        self.assertIn(evidence.relative_to(self.root).as_posix(), provenance)
        self.assertIn(source.relative_to(self.root).as_posix(), provenance)

    def test_revision_discovered_after_immutable_candidate_requires_successor(self):
        baseline = sealer.build(self.end + 14400*1000, self.root / "baseline", self.root)
        self.assertEqual(len(baseline), 1)
        original_id = baseline[0]["generation_id"]
        baseline[0]["publication"]["publish_status"] = "PASS"
        sealer.install_candidate_control_plane(baseline, self.root)
        original_path = self.root / f"history/generations/{original_id}.json"
        original_bytes = original_path.read_bytes()
        self.add_revision(known_at_ms=self.end + 20000*1000)
        revised = sealer.build(self.end + 25000*1000, self.root / "revised", self.root)
        self.assertEqual(len(revised), 1)
        self.assertNotEqual(revised[0]["generation_id"], original_id)
        self.assertEqual(revised[0]["supersedes"], original_id)
        self.assertEqual(original_path.read_bytes(), original_bytes)

    def test_revision_evidence_tamper_fails_closed(self):
        evidence, _source = self.add_revision(known_at_ms=self.end + 7200*1000)
        payload = json.loads(evidence.read_text(encoding="utf-8"))
        payload["previous_value_fingerprint"] = "0" * 64
        evidence.write_text(compact(payload), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            sealer.build(self.end + 14400*1000, self.root / "tampered", self.root)


if __name__ == "__main__":
    unittest.main()
