from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from kraken_revision import append_metric_with_revision_evidence, revision_overlap_cursor


class D9KrakenRevisionTests(unittest.TestCase):
    def test_revisable_overlap_preserves_base_and_creates_pit_evidence(self):
        timestamp = 1786960000000
        known = 1786968000000
        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                path = Path("derivatives/archive/2026/08/17/kraken-futures/PI_ETHUSD-spreads.json")
                metadata = {
                    "schema_version": "1.0.0",
                    "provider": "kraken-futures",
                    "instrument": "PI_ETHUSD",
                    "metric": "spreads",
                    "resolution_seconds": 300,
                }
                append_metric_with_revision_evidence(
                    path,
                    metadata,
                    [[timestamp, {"bid.best_price": "2000", "ask.best_price": "2001"}]],
                    instrument="PI_ETHUSD",
                    metric="spreads",
                    known_at_ms=known - 1000,
                    source_routes=["fixture:first"],
                    revisable={"spreads"},
                )
                result, evidence = append_metric_with_revision_evidence(
                    path,
                    metadata,
                    [[timestamp, {"bid.best_price": "1999", "ask.best_price": "2000"}]],
                    instrument="PI_ETHUSD",
                    metric="spreads",
                    known_at_ms=known,
                    source_routes=["fixture:revision"],
                    revisable={"spreads"},
                )
                base = json.loads(path.read_text())["records"]
                self.assertEqual(base, [[timestamp, {"bid.best_price": "2000", "ask.best_price": "2001"}]])
                self.assertEqual(len(result.revisions), 1)
                self.assertEqual(len(evidence), 1)
                proof = json.loads(Path(evidence[0]).read_text())
                self.assertEqual(proof["classification"], "PROVIDER_REVISABLE_SNAPSHOT")
                self.assertEqual(proof["observed_value"][1]["bid.best_price"], "1999")
                self.assertTrue(Path(proof["source_snapshot_ref"]).is_file())
                _result, repeated = append_metric_with_revision_evidence(
                    path,
                    metadata,
                    [[timestamp, {"bid.best_price": "1999", "ask.best_price": "2000"}]],
                    instrument="PI_ETHUSD",
                    metric="spreads",
                    known_at_ms=known + 1000,
                    source_routes=["fixture:repeat"],
                    revisable={"spreads"},
                )
                self.assertEqual(repeated, [])
            finally:
                os.chdir(previous)

    def test_strict_metric_conflict_fails_closed(self):
        timestamp = 1786960000000
        with tempfile.TemporaryDirectory() as temp:
            previous = os.getcwd()
            os.chdir(temp)
            try:
                path = Path("strict.json")
                metadata = {"provider": "kraken-futures", "instrument": "PI_ETHUSD", "metric": "open-interest"}
                append_metric_with_revision_evidence(
                    path,
                    metadata,
                    [[timestamp, "1"]],
                    instrument="PI_ETHUSD",
                    metric="open-interest",
                    known_at_ms=timestamp,
                    source_routes=["fixture"],
                    revisable=set(),
                )
                with self.assertRaises(ValueError):
                    append_metric_with_revision_evidence(
                        path,
                        metadata,
                        [[timestamp, "2"]],
                        instrument="PI_ETHUSD",
                        metric="open-interest",
                        known_at_ms=timestamp + 1,
                        source_routes=["fixture"],
                        revisable=set(),
                    )
            finally:
                os.chdir(previous)

    def test_only_revisable_metric_moves_cursor_backward(self):
        tail = 1786960000000
        default = 1786900000
        revisable = {"spreads"}
        self.assertLess(revision_overlap_cursor(tail, default, "spreads", revisable), tail // 1000)
        self.assertEqual(revision_overlap_cursor(tail, default, "open-interest", revisable), tail // 1000 + 1)


if __name__ == "__main__":
    unittest.main()
