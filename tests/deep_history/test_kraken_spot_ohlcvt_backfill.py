import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.deep_history import kraken_spot_ohlcvt_backfill as backfill


FIVE_MINUTE = b"""time,open,high,low,close,volume,trades
1577836800,100,101,99,100.5,10,5
1577837100,100.5,102,100,101,11,6
1577837700,101,103,100.5,102,12,7
1577838000,102,104,101,103,13,8
"""
DAILY = b"""1577836800,100,110,90,105,1000,50
1577923200,105,115,100,110,1100,55
1578009600,110,120,105,115,1200,60
"""
CUTOFF = 1578182400000


def make_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ETHUSD_5.csv", FIVE_MINUTE)
        archive.writestr("ETHUSD_1440.csv", DAILY)


def source() -> dict:
    return {
        "schema_version": backfill.SOURCE_SCHEMA,
        "source_mode": backfill.SOURCE_MODE,
        "authority": "KRAKEN_OFFICIAL_POSTTRADE",
        "endpoint": backfill.posttrade.ENDPOINT,
        "documentation": backfill.posttrade.DOCUMENTATION,
        "symbol": backfill.posttrade.SYMBOL,
        "segmentation": "UTC_CALENDAR_QUARTER",
        "resume_granularity": "COMPLETED_SEGMENT",
        "page_level_checkpointing": False,
        "max_parallel": 1,
        "archive_sha256": "a" * 64,
        "archive_size_bytes": 123,
        "source_lineage_digest": "b" * 64,
        "segment_count": 2,
        "derived_archive_sha256": "c" * 64,
        "acquired_at_utc": "2026-09-04T00:00:00Z",
    }


class KrakenSpotOhlcvtBackfillTests(unittest.TestCase):
    def test_source_selection_identity_is_posttrade_only(self):
        self.assertEqual("KRAKEN_OFFICIAL_POSTTRADE_BULK", backfill.SOURCE_MODE)
        self.assertEqual(backfill.SOURCE_MODE, backfill.posttrade.SOURCE_MODE)
        self.assertEqual("https://api.kraken.com/0/public/PostTrade", backfill.posttrade.ENDPOINT)
        self.assertEqual("history-kraken-spot-v2", backfill.RELEASE_TAG)
        self.assertFalse(hasattr(backfill, "time_sales"))
        self.assertFalse(hasattr(backfill, "rest_trades"))

    def test_qualification_inventory_crosses_real_utc_quarter_boundary(self):
        inventory = backfill.qualification_inventory()
        self.assertEqual(2, len(inventory))
        self.assertEqual("2017-06-29T00:00:00.000000Z", inventory[0]["requested_start_utc"])
        self.assertEqual("2017-07-01T00:00:00.000000Z", inventory[0]["requested_end_utc"])
        self.assertEqual("2017-07-01T00:00:00.000000Z", inventory[1]["requested_start_utc"])
        self.assertEqual("2017-07-03T00:00:00.000000Z", inventory[1]["requested_end_utc"])

    def test_parser_preserves_trade_count_and_provider_gaps(self):
        rows = backfill.parse_ohlcvt(io.BytesIO(FIVE_MINUTE), "5m", CUTOFF)
        self.assertEqual(4, len(rows))
        self.assertEqual(5, rows[0][6])
        summary = backfill.gap_summary(rows, 300000)
        self.assertEqual(backfill.GAP_POLICY, summary["policy"])
        self.assertFalse(summary["synthetic_fill"])
        self.assertEqual(1, summary["gap_events"])
        self.assertEqual(1, summary["missing_intervals"])
        self.assertNotIn(1577837400000, {row[0] for row in rows})

    def test_cutoff_is_closed_only(self):
        rows = backfill.parse_ohlcvt(io.BytesIO(FIVE_MINUTE), "5m", 1577837100000)
        self.assertEqual(1, len(rows))
        self.assertTrue(all(row[7] < 1577837100000 for row in rows))

    def test_build_is_deterministic_and_posttrade_semantics_are_emitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            make_archive(archive)
            left = backfill.build_assets(archive, root / "a", CUTOFF, source())
            right = backfill.build_assets(archive, root / "b", CUTOFF, source())
            backfill.compare_builds(left, right)
            self.assertEqual({"5m", "1d"}, {item["interval_or_metric"] for item in left})
            asset = next(item for item in left if item["interval_or_metric"] == "5m")
            payload = json.loads(Path(asset["local_path"]).read_text())
            self.assertEqual("KRAKEN_POSTTRADE_DERIVED_OHLCVT", payload["source_semantics"])
            self.assertEqual(backfill.GAP_POLICY, payload["gap_semantics"]["policy"])
            self.assertFalse(payload["gap_semantics"]["synthetic_fill"])
            self.assertIn("trade_count", payload["columns"])
            self.assertEqual(backfill.SOURCE_MODE, asset["boundary_proof"]["source_mode"])
            self.assertEqual(backfill.posttrade.ENDPOINT, asset["boundary_proof"]["source_route"])

    def test_overlap_compares_compatibility_projection_and_native_trade_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            make_archive(archive)
            assets = backfill.build_assets(archive, root / "build", CUTOFF, source())
            for interval in ("5m", "1d"):
                asset = next(item for item in assets if item["interval_or_metric"] == interval)
                payload = json.loads(Path(asset["local_path"]).read_text())
                rows = payload["records"][:3]
                compat = [[r[0], r[1], r[2], r[3], r[4], r[5], r[7]] for r in rows]
                native = [[r[0], r[1], r[2], r[3], r[4], r[4], r[5], r[6], r[7]] for r in rows]
                path = root / "history" / "kraken" / "ETHUSD" / interval / "2020" / "01" / "01.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"records": compat, "provider_native_records": native}))
            result = backfill.verify_warm_overlap(assets, root, coverage_end_ms=CUTOFF)
            self.assertEqual("PASS", result["status"])
            self.assertEqual(0, result["conflicts"])
            self.assertGreaterEqual(result["overlaps"]["5m"], 3)
            self.assertGreaterEqual(result["overlaps"]["1d"], 3)

    def test_manifest_merge_replaces_only_ethusd_5m_and_1d(self):
        current = {
            "schema_version": "1.0.0",
            "storage_schema_version": "1.0.0",
            "generated_at_utc": "old",
            "backfill_as_of_utc": "2026-08-15T11:00:00Z",
            "backfill_as_of_ms": CUTOFF,
            "storage_backend": "GITHUB_RELEASE_ASSET",
            "frozen_source": {"manifest_sha256": "x", "request_count": 1, "requests": []},
            "release_inventory": [{"release_tag": "history-kraken-spot-v1", "release_id": 1, "release_url": "u1", "immutable": True, "asset_count": 3}],
            "series_inventory": [
                {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "5m", "first_timestamp": 9, "last_timestamp": 10, "row_count": 2, "asset_count": 1, "release_tag": "history-kraken-spot-v1", "boundary_status": "PROVIDER_HISTORY_LIMIT"},
                {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "1d", "first_timestamp": 9, "last_timestamp": 10, "row_count": 2, "asset_count": 1, "release_tag": "history-kraken-spot-v1", "boundary_status": "PROVIDER_HISTORY_LIMIT"},
                {"provider": "kraken", "instrument": "BTCUSD", "interval_or_metric": "5m", "first_timestamp": 9, "last_timestamp": 10, "row_count": 2, "asset_count": 1, "release_tag": "history-kraken-spot-v1", "boundary_status": "PROVIDER_HISTORY_LIMIT"},
            ],
            "asset_inventory": [
                {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "5m", "asset_name": "old5", "first_timestamp": 9},
                {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "1d", "asset_name": "old1d", "first_timestamp": 9},
                {"provider": "kraken", "instrument": "BTCUSD", "interval_or_metric": "5m", "asset_name": "keep", "first_timestamp": 9},
            ],
            "integrity_summary": {},
        }
        assets = [
            {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "5m", "asset_name": "new5", "first_timestamp": 1, "last_timestamp": 5, "row_count": 5, "local_path": "ignored"},
            {"provider": "kraken", "instrument": "ETHUSD", "interval_or_metric": "1d", "asset_name": "new1d", "first_timestamp": 1, "last_timestamp": 5, "row_count": 5, "local_path": "ignored"},
        ]
        result = backfill.merge_release_manifest(current, assets, source(), {"id": 2, "html_url": "u2"})
        self.assertEqual({"keep", "new5", "new1d"}, {item["asset_name"] for item in result["asset_inventory"]})
        series = {(item["instrument"], item["interval_or_metric"]): item for item in result["series_inventory"]}
        self.assertEqual("MAX_AVAILABLE", series[("ETHUSD", "5m")]["boundary_status"])
        self.assertEqual(backfill.RELEASE_TAG, series[("ETHUSD", "1d")]["release_tag"])
        self.assertEqual("PROVIDER_HISTORY_LIMIT", series[("BTCUSD", "5m")]["boundary_status"])
        self.assertEqual(backfill.SOURCE_MODE, result["integrity_summary"]["kraken_spot_deep_history_source_mode"])

    def test_series_id_stability_and_single_route(self):
        index = Path("history/capability-index.json").read_text()
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.5m", index)
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.1d", index)
        self.assertFalse(Path("tools/kraken_second_resolver.py").exists())
        self.assertFalse(Path("tools/kraken_posttrade_history_consumer.py").exists())
        self.assertTrue(Path("tools/history_access.py").is_file())
        self.assertTrue(Path("tools/history_consumer.py").is_file())


if __name__ == "__main__":
    unittest.main()
