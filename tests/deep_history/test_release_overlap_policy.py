from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from release_overlap_policy import REVISABLE_SCHEMA, load_contract, revisable_metrics, verify_git_overlap


class ReleaseOverlapPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "derivatives" / "archive" / "2026" / "08" / "14" / "kraken-futures").mkdir(parents=True)
        contract = {
            "schema_version": "1.0.0",
            "provider": "kraken-futures",
            "resolution_seconds": 300,
            "archive_ingestion": {"stabilization_seconds": 1800},
            "metrics": {
                "open-interest": {"classification": "STRICT_OVERLAP_REQUIRED"},
                "cvd": {"classification": "WINDOW_ANCHORED_CUMULATIVE", "schema_version": "kraken-futures-cvd/2.0.0"},
                "spreads": {"classification": "PROVIDER_REVISABLE_SNAPSHOT", "schema_version": REVISABLE_SCHEMA},
            },
        }
        semantics = self.root / "derivatives" / "metric-semantics.json"
        semantics.parent.mkdir(parents=True, exist_ok=True)
        semantics.write_text(json.dumps(contract))
        self.publisher = SimpleNamespace(
            AS_OF_MS=1786791600000,
            AS_OF_UTC="2026-08-15T11:00:00Z",
            KRAKEN_METRICS=("open-interest", "cvd", "spreads"),
            CVD_SEMANTICS_SCHEMA="kraken-futures-cvd/2.0.0",
            SOURCE=SimpleNamespace(replay=True),
            cvd_overlap_equal=lambda old, new, old_semantics, new_semantics: old[1]["buy_volume"] == new[1]["buy_volume"] and old[1]["sell_volume"] == new[1]["sell_volume"],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def write_git(self, metric, row, metric_semantics=None):
        path = self.root / "derivatives" / "archive" / "2026" / "08" / "14" / "kraken-futures" / f"PI_ETHUSD-{metric}.json"
        payload = {
            "schema_version": "1.0.0",
            "provider": "kraken-futures",
            "instrument": "PI_ETHUSD",
            "metric": metric,
            "resolution_seconds": 300,
            "records": [row],
        }
        if metric_semantics:
            payload["metric_semantics"] = metric_semantics
        path.write_text(json.dumps(payload))

    def asset(self, metric, row, *, cutoff=True, frozen_provenance=True, metric_semantics=None):
        path = self.root / f"asset-{metric}.json"
        payload = {
            "provider": "kraken-futures",
            "instrument": "PI_ETHUSD",
            "interval_or_metric": metric,
            "records": [row],
        }
        if metric_semantics:
            payload["metric_semantics"] = metric_semantics
        path.write_text(json.dumps(payload))
        proof = {
            "requested_cutoff_ms": self.publisher.AS_OF_MS if cutoff else self.publisher.AS_OF_MS - 1,
            "source_route": "https://futures.kraken.com/api/charts/v1/analytics/:symbol/:analytics_type",
        }
        return {
            "provider": "kraken-futures",
            "instrument": "PI_ETHUSD",
            "interval_or_metric": metric,
            "local_path": str(path),
            "boundary_proof": proof,
            "source_route": proof["source_route"],
            "retrieved_at_utc": "2026-08-15T18:00:00Z" if frozen_provenance else None,
        }

    def test_contract_identifies_only_declared_revisable_metric(self):
        contract = load_contract(self.root / "derivatives" / "metric-semantics.json")
        self.assertEqual(revisable_metrics(contract), {"spreads"})

    def test_exact_strict_overlap_passes(self):
        row = [1786738500000, ["1", "2"]]
        self.write_git("open-interest", row)
        result = verify_git_overlap([self.asset("open-interest", row)], publisher=self.publisher, root=self.root)
        self.assertEqual(result["exact"], 1)
        self.assertEqual(result["provider_restatements"], 0)

    def test_strict_overlap_mismatch_fails_closed(self):
        self.write_git("open-interest", [1786738500000, ["1", "2"]])
        with self.assertRaisesRegex(RuntimeError, "release/Git overlap conflict"):
            verify_git_overlap([self.asset("open-interest", [1786738500000, ["1", "3"]])], publisher=self.publisher, root=self.root)

    def test_revisable_overlap_records_provider_restatement(self):
        self.write_git("spreads", [1786738500000, {"bid.best_price": "1877.3", "ask.best_price": "1879.2"}])
        asset = self.asset("spreads", [1786738500000, {"bid.best_price": "1877.2", "ask.best_price": "1879.1"}])
        result = verify_git_overlap([asset], publisher=self.publisher, root=self.root)
        self.assertEqual(result["provider_restatements"], 1)
        self.assertEqual(asset["metric_semantics"]["schema_version"], REVISABLE_SCHEMA)
        self.assertEqual(asset["metric_semantics"]["classification"], "PROVIDER_REVISABLE_SNAPSHOT")
        self.assertEqual(asset["overlap_reconciliation"]["provider_restatement_count"], 1)
        self.assertEqual(asset["overlap_reconciliation"]["unresolved_conflicts"], 0)

    def test_revisable_overlap_requires_fixed_cutoff(self):
        self.write_git("spreads", [1786738500000, {"bid.best_price": "1", "ask.best_price": "2"}])
        asset = self.asset("spreads", [1786738500000, {"bid.best_price": "1.1", "ask.best_price": "2.1"}], cutoff=False)
        with self.assertRaisesRegex(RuntimeError, "missing fixed cutoff proof"):
            verify_git_overlap([asset], publisher=self.publisher, root=self.root)

    def test_revisable_overlap_requires_frozen_replay(self):
        self.write_git("spreads", [1786738500000, {"bid.best_price": "1", "ask.best_price": "2"}])
        asset = self.asset("spreads", [1786738500000, {"bid.best_price": "1.1", "ask.best_price": "2.1"}])
        self.publisher.SOURCE = SimpleNamespace(replay=False)
        with self.assertRaisesRegex(RuntimeError, "requires frozen replay source"):
            verify_git_overlap([asset], publisher=self.publisher, root=self.root)

    def test_revisable_overlap_requires_retrieval_provenance(self):
        self.write_git("spreads", [1786738500000, {"bid.best_price": "1", "ask.best_price": "2"}])
        asset = self.asset("spreads", [1786738500000, {"bid.best_price": "1.1", "ask.best_price": "2.1"}], frozen_provenance=False)
        with self.assertRaisesRegex(RuntimeError, "missing retrieval provenance"):
            verify_git_overlap([asset], publisher=self.publisher, root=self.root)

    def test_cvd_semantic_overlap_remains_separate(self):
        old_semantics = {"schema_version": "kraken-futures-cvd/2.0.0", "canonical_anchor": {"identity": "old"}}
        new_semantics = {"schema_version": "kraken-futures-cvd/2.0.0", "canonical_anchor": {"identity": "new"}}
        self.write_git("cvd", [1786738500000, {"buy_volume": "10", "sell_volume": "4", "cvd": "99"}], old_semantics)
        asset = self.asset("cvd", [1786738500000, {"buy_volume": "10", "sell_volume": "4", "cvd": "5"}], metric_semantics=new_semantics)
        result = verify_git_overlap([asset], publisher=self.publisher, root=self.root)
        self.assertEqual(result["cvd_semantic"], 1)
        self.assertEqual(result["provider_restatements"], 0)

    def test_repository_contract_covers_all_current_kraken_metrics(self):
        import release_publisher

        contract = load_contract(Path("derivatives/metric-semantics.json"))
        self.assertEqual(set(contract["metrics"]), set(release_publisher.KRAKEN_METRICS))
        self.assertEqual(contract["archive_ingestion"]["stabilization_seconds"], 1800)
        self.assertEqual(
            revisable_metrics(contract),
            {"spreads", "liquidity", "slippage", "future-basis", "funding"},
        )

    def test_current_hourly_collector_keeps_stabilization_gate(self):
        source = Path("src/intelligence.py").read_text()
        self.assertIn("r[0]<=now-1800000", source.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
