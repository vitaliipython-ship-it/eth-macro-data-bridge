import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.deep_history import kraken_spot_ohlcvt_backfill as backfill


def m5(ts, o, h, low, c, volume, trades):
    return [ts, str(o), str(h), str(low), str(c), str(volume), trades, ts + 300_000 - 1]


def payload(interval, period, records, gap=None):
    return {
        "schema_version": "1.0.0", "provider": "kraken", "instrument": "ETHUSD",
        "interval_or_metric": interval, "columns": backfill.COLUMNS, "partitioning": "yearly",
        "period": period, "closed_only": True,
        "gap_semantics": gap or {"policy": backfill.GAP_POLICY, "synthetic_fill": False, "gap_events": 0, "missing_intervals": 0},
        "records": records,
    }


class KrakenDerivedH1H4Tests(unittest.TestCase):
    def test_policy_is_versioned_distinct_identity(self):
        policy, digest = backfill._derivation_policy()
        self.assertEqual(policy["policy_id"], "KRAKEN_SPOT_M5_TO_H1_H4_DERIVATION")
        self.assertEqual(policy["policy_version"], "1.0.0")
        self.assertFalse(policy["identity"]["provider_native_and_derived_share_identity"])
        self.assertEqual(len(digest), 64)

    def test_sparse_no_trade_source_aggregates_without_synthetic_fill(self):
        hour = 3_600_000
        rows = [
            m5(0, "100", "101", "99", "100.5", "2", 2),
            m5(600_000, "100.5", "103", "100", "102", "3", 4),
            m5(hour, "102", "104", "101", "103", "5", 1),
        ]
        derived = backfill._derive_rows(rows, hour, 0, 2 * hour)
        self.assertEqual(derived, [
            [0, "100", "103", "99", "102", "5", 6, hour - 1],
            [hour, "102", "104", "101", "103", "5", 1, 2 * hour - 1],
        ])
        summary = backfill._qualified_gap_summary(derived, hour, 0, 2 * hour)
        self.assertEqual(summary, {"policy": backfill.GAP_POLICY, "synthetic_fill": False, "gap_events": 0, "missing_intervals": 0})

    def test_empty_target_bucket_is_qualified_omission_not_synthetic_candle(self):
        hour = 3_600_000
        rows = [m5(0, "100", "101", "99", "100", "1", 1), m5(2 * hour, "102", "103", "101", "102", "1", 1)]
        derived = backfill._derive_rows(rows, hour, 0, 3 * hour)
        self.assertEqual([row[0] for row in derived], [0, 2 * hour])
        summary = backfill._qualified_gap_summary(derived, hour, 0, 3 * hour)
        self.assertEqual((summary["gap_events"], summary["missing_intervals"], summary["synthetic_fill"]), (1, 1, False))

    def test_distinct_identity_reference_overlap_allows_volume_divergence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assets = []
            for physical, interval, step in (("derived-1h", "1h", 3_600_000), ("derived-4h", "4h", 14_400_000)):
                target = root / f"kraken--ETHUSD--{physical}--2026.json"
                row = [0, "100", "103", "99", "102", "5", 6, step - 1]
                target.write_text(json.dumps({"records": [row]}))
                assets.append({"interval_or_metric": physical, "local_path": str(target)})
                native_dir = root / "history" / "kraken" / "ETHUSD" / interval / "2026"
                native_dir.mkdir(parents=True, exist_ok=True)
                native_volume = "9" if interval == "4h" else "5"
                (native_dir / "01.json").write_text(json.dumps({
                    "provider": "kraken", "symbol": "ETHUSD", "interval": interval,
                    "records": [[0, "100", "103", "99", "102", native_volume, step - 1]],
                }))
            result = backfill.verify_native_reference_overlap(assets, root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["series"]["1h"]["volume_divergences"], 0)
        self.assertEqual(result["series"]["4h"]["volume_divergences"], 1)
        self.assertEqual(result["unresolved_conflicts"], 0)

    def test_distinct_identity_reference_overlap_still_fails_on_price_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assets = []
            for physical, interval, step in (("derived-1h", "1h", 3_600_000), ("derived-4h", "4h", 14_400_000)):
                target = root / f"kraken--ETHUSD--{physical}--2026.json"
                target.write_text(json.dumps({"records": [[0, "100", "103", "99", "102", "5", 6, step - 1]]}))
                assets.append({"interval_or_metric": physical, "local_path": str(target)})
                native_dir = root / "history" / "kraken" / "ETHUSD" / interval / "2026"
                native_dir.mkdir(parents=True, exist_ok=True)
                close = "101" if interval == "4h" else "102"
                (native_dir / "01.json").write_text(json.dumps({
                    "provider": "kraken", "symbol": "ETHUSD", "interval": interval,
                    "records": [[0, "100", "103", "99", close, "5", step - 1]],
                }))
            with self.assertRaisesRegex(RuntimeError, "KRAKEN_DERIVED_REFERENCE_OVERLAP_CONFLICT"):
                backfill.verify_native_reference_overlap(assets, root)

    def test_successor_build_is_deterministic_and_excludes_partial_h4_tail(self):
        base = int(backfill.datetime(2015, 1, 1, tzinfo=backfill.timezone.utc).timestamp() * 1000)
        rows = [m5(base + i * 300_000, "100", "101", "99", "100", "1", 1) for i in range(60)]
        cutoff = base + 5 * 3_600_000
        rows = [row for row in rows if row[0] < cutoff]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m5_path = root / "kraken--ETHUSD--5m--2015.json"
            d1_path = root / "kraken--ETHUSD--1d--2015.json"
            m5_path.write_bytes(backfill.compact(payload("5m", "2015", rows)))
            d1_path.write_bytes(backfill.compact(payload("1d", "2015", [[base, "100", "101", "99", "100", "5", 5, base + 86_400_000 - 1]])))
            common = {
                "provider": "kraken", "instrument": "ETHUSD", "release_tag": "history-kraken-spot-v2",
                "release_id": 1, "asset_id": 1, "browser_download_url": "https://example.invalid/a",
                "integrity_status": "PASS", "immutable": True, "historical_availability": "MAX_AVAILABLE",
                "provider_history_limit": False, "known_gaps": [], "retrieved_at_utc": "2026-01-01T00:00:00Z",
                "boundary_proof": {"requested_start": "2015-01-01T00:00:00Z", "provider_more_exhausted": True},
            }
            assets = []
            for idx, (path, interval, records_) in enumerate(((m5_path, "5m", rows), (d1_path, "1d", [[base, "100", "101", "99", "100", "5", 5, base + 86_400_000 - 1]])), 1):
                raw = path.read_bytes(); item = dict(common); item.update({
                    "asset_id": idx, "asset_name": path.name, "interval_or_metric": interval, "local_path": str(path),
                    "first_timestamp": records_[0][0], "last_timestamp": records_[-1][0], "row_count": len(records_),
                    "partitioning": "yearly", "closed_only": True, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                    "gap_semantics": {"policy": backfill.GAP_POLICY, "synthetic_fill": False, "gap_events": 0, "missing_intervals": 0},
                }); assets.append(item)
            current = {
                "generated_at_utc": "2026-01-01T00:00:00Z", "backfill_as_of_ms": cutoff,
                "series_inventory": [
                    {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "5m", "release_tag": "history-kraken-spot-v2", "boundary_status": "MAX_AVAILABLE"},
                    {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "1d", "release_tag": "history-kraken-spot-v2", "boundary_status": "MAX_AVAILABLE"},
                ],
            }
            left = backfill.build_derived_successor_assets(assets, root / "a", current)
            right = backfill.build_derived_successor_assets(assets, root / "b", current)
            lhash = {x["asset_name"]: x["sha256"] for x in left}; rhash = {x["asset_name"]: x["sha256"] for x in right}
            self.assertEqual(lhash, rhash)
            h1 = next(x for x in left if x["interval_or_metric"] == "derived-1h")
            h4 = next(x for x in left if x["interval_or_metric"] == "derived-4h")
            self.assertEqual(h1["coverage_end_ms"], cutoff)
            self.assertEqual(h4["coverage_end_ms"], base + 4 * 3_600_000)
            self.assertFalse(json.loads(Path(h4["local_path"]).read_text())["gap_semantics"]["synthetic_fill"])


if __name__ == "__main__":
    unittest.main()
