import binascii
import json
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from tools.deep_history import kraken_spot_time_sales as source


def frozen_member(root: Path, name: str, raw: bytes, *, year=None, quarter=None) -> dict:
    compressor = zlib.compressobj(level=6, wbits=-15)
    compressed = compressor.compress(raw) + compressor.flush()
    path = root / f"{name}.deflate"
    path.write_bytes(compressed)
    item = {
        "file_id": f"id-{name}",
        "filename": name,
        "archive_size_bytes": len(compressed) + 100,
        "member_name": "ETHUSD.csv",
        "compression_method": 8,
        "crc32": binascii.crc32(raw) & 0xFFFFFFFF,
        "compressed_size": len(compressed),
        "uncompressed_size": len(raw),
        "compressed_sha256": source._sha256_file(path),
        "frozen_path": str(path),
    }
    if year is not None:
        item["year"] = year
        item["quarter"] = quarter
    return item


def frozen_set(root: Path) -> dict:
    complete = b"""1438956205,3.00000,1.00000000\n1438956205,4.00000,2.00000000\n1438956290,2.00000,3.00000000\n1767225594,2971.39000,0.05849597\n"""
    q1 = b"""Timestamp,Price,Volume\n1767225601,2972.00000,0.10000000\n1767225660,2973.00000,0.20000000\n1774997999,2000.00000,0.30000000\n"""
    return {
        "metadata": {"source_mode": source.SOURCE_MODE},
        "sources": [
            frozen_member(root, "complete", complete),
            frozen_member(root, "Kraken_Trading_History_Q1_2026.zip", q1, year=2026, quarter=1),
        ],
    }


class FakeResponse:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.status = 200
        self.headers = {"Content-Type": "text/html"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *_args):
        return self.raw


class FakeOpener:
    def __init__(self, raw: bytes):
        self.raw = raw

    def open(self, *_args, **_kwargs):
        return FakeResponse(self.raw)


class KrakenSpotTimeSalesTests(unittest.TestCase):
    def test_01_official_source_identity(self):
        self.assertEqual("KRAKEN_OFFICIAL_TIME_SALES_ARCHIVE", source.SOURCE_MODE)
        self.assertIn("kraken.com", source.SUPPORT_URL)
        self.assertEqual("https://api.kraken.com/0/public/Trades", source.TRADES_ENDPOINT)

    def test_02_provider_pair_normalization(self):
        self.assertEqual({"ETHUSD.CSV", "XETHZUSD.CSV"}, source.TARGET_MEMBERS)

    def test_03_old_history_market_inception_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = source.derive_ohlcvt_archive(
                frozen_set(Path(temporary)), Path(temporary) / "derived.zip", 1_900_000_000_000
            )
            self.assertEqual(1438956205000, result["first_trade_ms"])

    def test_04_same_timestamp_order_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual("3.00000", first[1])
            self.assertEqual("2.00000", first[4])

    def test_05_utc_five_minute_bucket_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual(str((1438956205 // 300) * 300), first[0])

    def test_06_ohlc_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual(["3.00000", "4.00000", "2.00000", "2.00000"], first[1:5])

    def test_07_volume_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual("6.00000000", first[5])

    def test_08_trade_count_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual("3", first[6])

    def test_09_no_synthetic_fill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with zipfile.ZipFile(root / "derived.zip") as archive:
                lines = archive.read("ETHUSD_5.csv").decode().splitlines()
            starts = [int(line.split(",", 1)[0]) for line in lines]
            self.assertGreater(starts[1] - starts[0], 300)
            self.assertNotIn(starts[0] + 300, starts)

    def test_10_header_normalization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            self.assertGreater(result["latest_trade_ms"], 1767225600000)

    def test_11_timestamp_regression_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = b"100,1,1\n99,1,1\n"
            frozen = {"metadata": {}, "sources": [frozen_member(root, "complete", raw)]}
            with self.assertRaisesRegex(RuntimeError, "timestamp regression"):
                source.derive_ohlcvt_archive(frozen, root / "derived.zip", 1_000_000_000)

    def test_12_acquisition_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = frozen_set(root)
            path = Path(frozen["sources"][0]["frozen_path"])
            path.write_bytes(path.read_bytes() + b"x")
            with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
                source.derive_ohlcvt_archive(frozen, root / "derived.zip", 1_900_000_000_000)

    def test_13_quarter_row_outside_partition_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            complete = frozen_member(root, "complete", b"1767225594,1,1\n")
            wrong = frozen_member(root, "q1", b"1775001601,1,1\n", year=2026, quarter=1)
            with self.assertRaisesRegex(RuntimeError, "outside declared quarter"):
                source.derive_ohlcvt_archive(
                    {"metadata": {}, "sources": [complete, wrong]}, root / "derived.zip", 1_900_000_000_000
                )

    def test_14_complete_quarter_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            complete = frozen_member(root, "complete", b"1767225602,1,1\n")
            q1 = frozen_member(root, "q1", b"1767225601,1,1\n", year=2026, quarter=1)
            with self.assertRaises(RuntimeError):
                source.derive_ohlcvt_archive(
                    {"metadata": {}, "sources": [complete, q1]}, root / "derived.zip", 1_900_000_000_000
                )

    def test_15_frozen_replay_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = frozen_set(root)
            left = root / "a.zip"
            right = root / "b.zip"
            source.derive_ohlcvt_archive(frozen, left, 1_900_000_000_000)
            source.derive_ohlcvt_archive(frozen, right, 1_900_000_000_000)
            source.compare_derived_archives(left, right)
            self.assertEqual(source._sha256_file(left), source._sha256_file(right))

    def test_16_declared_quarter_coverage_can_reach_warm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            source.assert_source_covers_warm(result, 1770000000000)

    def test_17_missing_quarter_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = source.derive_ohlcvt_archive(frozen_set(root), root / "derived.zip", 1_900_000_000_000)
            with self.assertRaises(source.SourceInventoryIncomplete):
                source.assert_source_covers_warm(result, 1786516200000)

    def test_18_quarter_folder_identity_is_single_official_inventory(self):
        html = b'''<div data-id="abc123" data-tooltip="Kraken_Trading_History_Q1_2026.zip"></div>'''
        opener = FakeOpener(html)
        inventory = source.discover_quarterly_archives(opener)
        self.assertEqual([{"file_id": "abc123", "filename": "Kraken_Trading_History_Q1_2026.zip", "quarter": 1, "year": 2026}], inventory)

    def test_19_source_set_digest_changes_with_raw_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = frozen_set(root)
            before = source.frozen_source_set_digest(frozen)
            frozen["sources"][0]["compressed_sha256"] = "f" * 64
            self.assertNotEqual(before, source.frozen_source_set_digest(frozen))

    def test_20_source_mode_not_consumer_field(self):
        contract = json.loads(Path("bridge-contract.json").read_text())
        request = contract["semantic_resolution"]["agent_transport"]["request"]
        canonical = set(request.get("fields") or request.get("required_fields") or [])
        serialized = json.dumps(request, sort_keys=True)
        self.assertNotIn("source_mode", serialized)
        self.assertNotIn("provider_url", serialized)
        self.assertNotIn("release_tag", serialized)
        self.assertTrue(canonical or "series_id" in serialized)

    def test_21_series_id_stability(self):
        index = json.loads(Path("history/capability-index.json").read_text())
        text = json.dumps(index)
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.5m", text)
        self.assertIn("spot.kraken-spot.ETHUSD.ohlcv.1d", text)

    def test_22_no_second_resolver_or_reader_is_created(self):
        self.assertFalse(Path("tools/kraken_second_resolver.py").exists())
        self.assertFalse(Path("tools/kraken_trades_history_consumer.py").exists())
        self.assertTrue(Path("tools/history_access.py").is_file())
        self.assertTrue(Path("tools/history_consumer.py").is_file())

    def test_23_existing_v1_release_identity_is_preserved_in_control_plane(self):
        text = Path("history/capability-index.json").read_text()
        self.assertIn("history-kraken-spot-v1", text)

    def test_24_canonical_outputs_remain_only_5m_and_1d(self):
        self.assertEqual({"5m", "1d"}, set(source.DERIVED_MEMBERS))


if __name__ == "__main__":
    unittest.main()
