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
        archive.writestr("Kraken_OHLCVT/XETHZUSD_5.csv", FIVE_MINUTE)
        archive.writestr("Kraken_OHLCVT/ETHUSD_1440.csv", DAILY)


def source() -> dict:
    return {
        "schema_version": backfill.SOURCE_SCHEMA,
        "source_mode": backfill.SOURCE_MODE,
        "authority": "KRAKEN_OFFICIAL_TIME_SALES_PLUS_REST_TRADES",
        "support_url": backfill.SUPPORT_URL,
        "file_ids": [backfill.FILE_ID],
        "acquired_at_utc": "2026-08-17T00:00:00Z",
        "archive_sha256": "a" * 64,
        "archive_component_sha256": "c" * 64,
        "archive_size_bytes": 123,
        "rest_tail_source_sha256": "d" * 64,
        "rest_tail_page_count": 9,
        "source_seam_overlap": {
            "status": "PASS", "matches": {"5m": 3, "1d": 1}, "conflicts": 0
        },
        "derived_archive_sha256": "b" * 64,
    }


class KrakenSpotOhlcvtBackfillTests(unittest.TestCase):
    def test_source_selection_identity(self):
        self.assertEqual(
            "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL",
            backfill.SOURCE_MODE,
        )
        self.assertIn("time-and-sales", backfill.SUPPORT_URL)
        self.assertEqual("history-kraken-spot-v2", backfill.RELEASE_TAG)

    def test_rest_tail_is_selected_for_missing_quarter_seam(self):
        self.assertEqual(
            "KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE_PLUS_REST_TRADES_TAIL",
            backfill.SOURCE_MODE,
        )
        self.assertEqual("https://api.kraken.com/0/public/Trades", backfill.rest_trades.ENDPOINT)
        self.assertGreater(backfill.rest_trades.OVERLAP_NS, 0)

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
        cutoff = 1577837100000
        rows = backfill.parse_ohlcvt(io.BytesIO(FIVE_MINUTE), "5m", cutoff)
        self.assertEqual([], [row for row in rows if row[7] >= cutoff])
        self.assertEqual(1, len(rows))

    def test_build_is_deterministic_and_accepts_legacy_pair_alias(self):
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
            self.assertEqual(backfill.GAP_POLICY, payload["gap_semantics"]["policy"])
            self.assertFalse(payload["gap_semantics"]["synthetic_fill"])
            self.assertEqual(
                "KRAKEN_TIME_SALES_PLUS_REST_TRADES_DERIVED_OHLCVT",
                payload["source_semantics"],
            )
            self.assertIn("trade_count", payload["columns"])
            self.assertEqual(backfill.SOURCE_MODE, asset["boundary_proof"]["source_mode"])

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
            result = backfill.verify_warm_overlap(assets, root)
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
            "release_inventory": [
                {
                    "release_tag": "history-kraken-spot-v1",
                    "release_id": 1,
                    "release_url": "u1",
                    "immutable": True,
                    "asset_count": 3,
                }
            ],
            "series_inventory": [
                {
                    "provider": "kraken",
                    "instrument": "ETHUSD",
                    "interval_or_metric": "5m",
                    "first_timestamp": 9,
                    "last_timestamp": 10,
                    "row_count": 2,
                    "asset_count": 1,
                    "release_tag": "history-kraken-spot-v1",
                    "boundary_status": "PROVIDER_HISTORY_LIMIT",
                },
                {
                    "provider": "kraken",
                    "instrument": "ETHUSD",
                    "interval_or_metric": "1d",
                    "first_timestamp": 9,
                    "last_timestamp": 10,
                    "row_count": 2,
                    "asset_count": 1,
                    "release_tag": "history-kraken-spot-v1",
                    "boundary_status": "PROVIDER_HISTORY_LIMIT",
                },
                {
                    "provider": "kraken",
                    "instrument": "BTCUSD",
                    "interval_or_metric": "5m",
                    "first_timestamp": 9,
                    "last_timestamp": 10,
                    "row_count": 2,
                    "asset_count": 1,
                    "release_tag": "history-kraken-spot-v1",
                    "boundary_status": "PROVIDER_HISTORY_LIMIT",
                },
            ],
            "asset_inventory": [
                {
                    "provider": "kraken",
                    "instrument": "ETHUSD",
                    "interval_or_metric": "5m",
                    "asset_name": "old5",
                    "first_timestamp": 9,
                },
                {
                    "provider": "kraken",
                    "instrument": "ETHUSD",
                    "interval_or_metric": "1d",
                    "asset_name": "old1d",
                    "first_timestamp": 9,
                },
                {
                    "provider": "kraken",
                    "instrument": "BTCUSD",
                    "interval_or_metric": "5m",
                    "asset_name": "keep",
                    "first_timestamp": 9,
                },
            ],
            "integrity_summary": {},
        }
        assets = [
            {
                "provider": "kraken",
                "instrument": "ETHUSD",
                "interval_or_metric": "5m",
                "asset_name": "new5",
                "first_timestamp": 1,
                "last_timestamp": 5,
                "row_count": 5,
                "local_path": "ignored",
            },
            {
                "provider": "kraken",
                "instrument": "ETHUSD",
                "interval_or_metric": "1d",
                "asset_name": "new1d",
                "first_timestamp": 1,
                "last_timestamp": 5,
                "row_count": 5,
                "local_path": "ignored",
            },
        ]
        published = {"id": 2, "html_url": "u2"}
        result = backfill.merge_release_manifest(current, assets, source(), published)
        names = {item["asset_name"] for item in result["asset_inventory"]}
        self.assertEqual({"keep", "new5", "new1d"}, names)
        series = {
            (item["instrument"], item["interval_or_metric"]): item
            for item in result["series_inventory"]
        }
        self.assertEqual("MAX_AVAILABLE", series[("ETHUSD", "5m")]["boundary_status"])
        self.assertEqual(backfill.RELEASE_TAG, series[("ETHUSD", "1d")]["release_tag"])
        self.assertEqual("PROVIDER_HISTORY_LIMIT", series[("BTCUSD", "5m")]["boundary_status"])
        self.assertEqual("PASS", result["integrity_summary"]["kraken_spot_ohlcvt_gap_policy"])
        self.assertEqual(
            backfill.SOURCE_MODE,
            result["integrity_summary"]["kraken_spot_deep_history_source_mode"],
        )

    def test_series_id_stability_and_single_route(self):
        index = Path("history/capability-index.json").read_text()
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.5m", index)
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.1d", index)
        self.assertIn("history-kraken-spot-v1", index)
        self.assertFalse(Path("tools/kraken_second_resolver.py").exists())
        self.assertFalse(Path("tools/kraken_trades_history_consumer.py").exists())
        self.assertTrue(Path("tools/history_access.py").is_file())
        self.assertTrue(Path("tools/history_consumer.py").is_file())


    def test_rest_tail_end_is_bounded_to_warm_overlap(self):
        warm = 1_800_000_000_000
        far_cutoff = warm + 30 * 86_400_000
        self.assertEqual(
            warm + backfill.REST_WARM_OVERLAP_MS,
            backfill._rest_tail_end_ms(far_cutoff, warm),
        )
        near_cutoff = warm + 2 * 86_400_000
        self.assertEqual(near_cutoff, backfill._rest_tail_end_ms(near_cutoff, warm))


if __name__ == "__main__":
    unittest.main()
