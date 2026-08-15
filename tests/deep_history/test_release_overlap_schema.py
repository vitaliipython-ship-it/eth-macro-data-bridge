from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from release_overlap_policy import REVISABLE_SCHEMA, verify_git_overlap


class RevisableSchemaGuardTests(unittest.TestCase):
    def test_value_revision_cannot_hide_schema_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "derivatives" / "archive" / "2026" / "08" / "14" / "kraken-futures"
            archive.mkdir(parents=True)
            (root / "derivatives" / "metric-semantics.json").write_text(json.dumps({
                "schema_version": "1.0.0",
                "provider": "kraken-futures",
                "metrics": {"spreads": {"classification": "PROVIDER_REVISABLE_SNAPSHOT", "schema_version": REVISABLE_SCHEMA}},
            }))
            timestamp = 1786738500000
            (archive / "PI_ETHUSD-spreads.json").write_text(json.dumps({
                "provider": "kraken-futures",
                "instrument": "PI_ETHUSD",
                "metric": "spreads",
                "records": [[timestamp, {"bid.best_price": "1877.3", "ask.best_price": "1879.2"}]],
            }))
            asset_path = root / "asset.json"
            asset_path.write_text(json.dumps({
                "records": [[timestamp, {"bid.best_price": "1877.2", "ask.best_price": "1879.1", "unexpected": "schema-drift"}]],
            }))
            publisher = SimpleNamespace(
                AS_OF_MS=1786791600000,
                AS_OF_UTC="2026-08-15T11:00:00Z",
                KRAKEN_METRICS=("spreads",),
                CVD_SEMANTICS_SCHEMA="kraken-futures-cvd/2.0.0",
                SOURCE=SimpleNamespace(replay=True),
                cvd_overlap_equal=lambda *args: False,
            )
            asset = {
                "provider": "kraken-futures",
                "instrument": "PI_ETHUSD",
                "interval_or_metric": "spreads",
                "local_path": str(asset_path),
                "boundary_proof": {
                    "requested_cutoff_ms": publisher.AS_OF_MS,
                    "source_route": "https://futures.kraken.com/api/charts/v1/analytics/:symbol/:analytics_type",
                },
                "source_route": "https://futures.kraken.com/api/charts/v1/analytics/:symbol/:analytics_type",
                "retrieved_at_utc": "2026-08-15T18:00:00Z",
            }
            with self.assertRaisesRegex(RuntimeError, "revisable overlap schema drift"):
                verify_git_overlap([asset], publisher=publisher, root=root)


if __name__ == "__main__":
    unittest.main()
