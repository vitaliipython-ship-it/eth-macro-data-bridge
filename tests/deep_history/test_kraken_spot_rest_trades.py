import json
import tempfile
import unittest
import urllib.parse
import zipfile
from pathlib import Path

from tools.deep_history import kraken_spot_rest_trades as rest


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload, separators=(",", ":")).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.raw


class FakeOpener:
    def __init__(self, pages):
        self.pages = pages
        self.cursors = []

    def open(self, request, timeout=30):
        cursor = int(urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)["since"][0])
        self.cursors.append(cursor)
        return FakeResponse(self.pages[cursor])


def payload(rows, last):
    return {"error": [], "result": {rest.RESULT_ID: rows, "last": str(last)}}


def derived(path: Path, rows5, rows1):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(
            rest.DERIVED_MEMBERS["5m"],
            "".join(",".join(map(str, row)) + "\n" for row in rows5),
        )
        archive.writestr(
            rest.DERIVED_MEMBERS["1d"],
            "".join(",".join(map(str, row)) + "\n" for row in rows1),
        )


class KrakenSpotRestTradesTests(unittest.TestCase):
    def test_01_official_identity(self):
        self.assertEqual("KRAKEN_OFFICIAL_REST_TRADES_TAIL", rest.SOURCE_MODE)
        self.assertEqual("https://api.kraken.com/0/public/Trades", rest.ENDPOINT)
        self.assertEqual("ETHUSD", rest.PAIR)
        self.assertEqual("XETHZUSD", rest.RESULT_ID)

    def test_02_cursor_pagination_freezes_bounded_rows(self):
        pages = {
            100_000_000_000: payload(
                [["10", "1", 100.1, "b", "l", ""], ["11", "2", 100.2, "s", "l", ""]],
                101_000_000_000,
            ),
            101_000_000_000: payload(
                [["12", "3", 101.1, "b", "l", ""], ["13", "4", 102.1, "s", "l", ""]],
                103_000_000_000,
            ),
        }
        opener = FakeOpener(pages)
        with tempfile.TemporaryDirectory() as temporary:
            frozen = rest.acquire_frozen_tail(
                Path(temporary),
                start_ns=100_000_000_000,
                end_ns=102_000_000_000,
                opener=opener,
                sleep_fn=lambda _x: None,
                delay_seconds=0,
            )
            self.assertEqual([100_000_000_000, 101_000_000_000], opener.cursors)
            self.assertEqual(2, frozen["metadata"]["page_count"])
            self.assertEqual(3, frozen["metadata"]["row_count"])
            self.assertEqual(102_000_000_000, frozen["metadata"]["coverage_end_ns"])
            self.assertTrue(frozen["metadata"]["cursor_monotonic"])

    def test_03_non_advancing_cursor_fails_closed(self):
        pages = {
            100_000_000_000: payload(
                [["10", "1", 100.1, "b", "l", ""]],
                100_000_000_000,
            )
        }
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(rest.RestTailIncomplete):
                rest.acquire_frozen_tail(
                    Path(temporary),
                    start_ns=100_000_000_000,
                    end_ns=102_000_000_000,
                    opener=FakeOpener(pages),
                    sleep_fn=lambda _x: None,
                    delay_seconds=0,
                )

    def test_04_frozen_replay_is_deterministic_and_tail_filter_is_exact(self):
        pages = {
            100_000_000_000: payload(
                [
                    ["10", "1", 100.1, "b", "l", ""],
                    ["11", "2", 100.2, "s", "l", ""],
                    ["12", "3", 101.1, "b", "l", ""],
                    ["13", "4", 102.1, "s", "l", ""],
                ],
                103_000_000_000,
            )
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = rest.acquire_frozen_tail(
                root / "frozen",
                start_ns=100_000_000_000,
                end_ns=102_000_000_000,
                opener=FakeOpener(pages),
                sleep_fn=lambda _x: None,
                delay_seconds=0,
            )
            a = root / "a.zip"
            b = root / "b.zip"
            rest.derive_ohlcvt_archive(frozen, a, 200_000, min_exclusive_ns=100_150_000_000)
            rest.derive_ohlcvt_archive(frozen, b, 200_000, min_exclusive_ns=100_150_000_000)
            self.assertEqual(rest._sha256_file(a), rest._sha256_file(b))
            with zipfile.ZipFile(a) as archive:
                first = archive.read("ETHUSD_5.csv").decode().splitlines()[0].split(",")
            self.assertEqual("11", first[1])
            self.assertEqual("12", first[4])
            self.assertEqual("5", first[5])
            self.assertEqual("2", first[6])

    def test_05_archive_rest_overlap_and_seam_merge(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "archive.zip"
            overlap = root / "overlap.zip"
            tail = root / "tail.zip"
            merged = root / "merged.zip"
            rows5 = [
                [0, "1", "2", "1", "2", "3", 2],
                [300, "2", "3", "2", "3", "4", 2],
                [600, "3", "4", "3", "4", "5", 2],
                [900, "4", "5", "4", "5", "6", 2],
            ]
            rows1 = [[0, "1", "5", "1", "5", "18", 8]]
            derived(archive, rows5, rows1)
            derived(overlap, rows5, rows1)
            proof = rest.verify_archive_overlap(archive, overlap, 86_400_000_000_000)
            self.assertEqual("PASS", proof["status"])
            derived(
                tail,
                [[900, "5", "6", "5", "6", "7", 3], [1200, "6", "7", "6", "7", "8", 3]],
                [[0, "5", "7", "5", "7", "15", 6]],
            )
            result = rest.merge_derived_archives(archive, tail, merged)
            self.assertEqual(1, result["seam_buckets"]["5m"])
            self.assertEqual(1, result["seam_buckets"]["1d"])
            with zipfile.ZipFile(merged) as output:
                five = output.read("ETHUSD_5.csv").decode().splitlines()
                day = output.read("ETHUSD_1440.csv").decode().splitlines()[0].split(",")
            self.assertEqual(5, len(five))
            seam = five[3].split(",")
            self.assertEqual("4", seam[1])
            self.assertEqual("6", seam[4])
            self.assertEqual("13", seam[5])
            self.assertEqual("5", seam[6])
            self.assertEqual("33", day[5])
            self.assertEqual("14", day[6])


if __name__ == "__main__":
    unittest.main()
