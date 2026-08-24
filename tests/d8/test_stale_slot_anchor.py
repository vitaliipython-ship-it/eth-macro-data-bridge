from __future__ import annotations

import tempfile
import unittest
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import acquisition_core as ac
import collector

SLOT_MS = int(datetime(2026, 8, 17, 23, 0, tzinfo=timezone.utc).timestamp() * 1000)
M5_MS = 5 * 60 * 1000
NEAR_MS = SLOT_MS + 10_000
DELAYED_MS = SLOT_MS + 19 * 60 * 1000 + 30_000
FUTURE_GUARD_NOW_MS = SLOT_MS - 60_000


def compact_row(open_ms: int, actual_ms: int) -> list[object]:
    closed = actual_ms > open_ms + M5_MS - 1
    return [open_ms, "1900", "1910", "1890", "1905", "12.5", closed]


def binance_native_row(open_ms: int) -> list[object]:
    close_ms = open_ms + M5_MS - 1
    return [open_ms, "1900", "1910", "1890", "1905", "12.5", close_ms, "100", 42, "50", "60"]


def kraken_native_row(open_ms: int) -> list[object]:
    close_ms = open_ms + M5_MS - 1
    return [open_ms, "1900", "1910", "1890", "1905", "1902", "12.5", 42, close_ms]


def binance_api_row(open_ms: int) -> list[object]:
    close_ms = open_ms + M5_MS - 1
    return [open_ms, "1900", "1910", "1890", "1905", "12.5", close_ms, "100", 42, "50", "60", "0"]


def kraken_api_row(open_ms: int) -> list[object]:
    return [open_ms // 1000, "1900", "1910", "1890", "1905", "1902", "12.5", 42]


def wall_clock_window(actual_ms: int) -> list[int]:
    boundary = (actual_ms // M5_MS) * M5_MS
    return [boundary - 2 * M5_MS, boundary - M5_MS, boundary]


def anchored_window(anchor_ms: int) -> list[int]:
    return [anchor_ms - 3 * M5_MS, anchor_ms - 2 * M5_MS, anchor_ms - M5_MS]


class StaleSlotAcquisitionRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.core = ac.CanonicalAcquisitionCore()
        self.actual_ms = NEAR_MS

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _fake_spot(self, symbol, _interval, _limit, physical_now_ms, *, anchor_ms=None):
        self.assertEqual(physical_now_ms, self.actual_ms)
        opens = anchored_window(anchor_ms) if anchor_ms is not None else wall_clock_window(self.actual_ms)
        rows = [compact_row(open_ms, self.actual_ms) for open_ms in opens]
        native = []
        for open_ms in opens:
            close_ms = open_ms + M5_MS - 1
            if self.actual_ms <= close_ms:
                continue
            if symbol.endswith("USDT") or symbol == "ETHBTC":
                native.append(binance_native_row(open_ms))
            else:
                native.append(kraken_native_row(open_ms))
        return "fixture-route", rows, native

    def _collect(self, capability: str, actual_ms: int) -> dict:
        self.actual_ms = actual_ms
        target = "acquisition_core.binance" if capability == "binance-spot.m5" else "acquisition_core.kraken"
        with patch(target, side_effect=self._fake_spot), patch("acquisition_core.time.time", return_value=actual_ms / 1000):
            return self.core.collect(capability, expected_ms=SLOT_MS, cycle_id="fixture-cycle", staging_root=self.root)

    def test_binance_temporal_selection_is_anchored_to_requested_slot(self):
        result = self._collect("binance-spot.m5", DELAYED_MS)
        self.assertEqual({o["value"]["open_time_ms"] for o in result["observations"]}, {SLOT_MS - M5_MS})
        self.assertTrue(all(o["value"]["open_time_ms"] + M5_MS <= SLOT_MS for o in result["observations"]))

    def test_kraken_temporal_selection_is_anchored_to_requested_slot(self):
        result = self._collect("kraken-spot.m5", DELAYED_MS)
        self.assertEqual({o["value"]["open_time_ms"] for o in result["observations"]}, {SLOT_MS - M5_MS})
        self.assertTrue(all(o["value"]["open_time_ms"] + M5_MS <= SLOT_MS for o in result["observations"]))

    def test_delayed_same_slot_keeps_same_temporal_identity(self):
        for capability in ("binance-spot.m5", "kraken-spot.m5"):
            near = self._collect(capability, NEAR_MS)
            delayed = self._collect(capability, DELAYED_MS)
            near_identity = [(o["series_id"], o["provider_timestamp_at"], o["value"]["open_time_ms"]) for o in near["observations"]]
            delayed_identity = [(o["series_id"], o["provider_timestamp_at"], o["value"]["open_time_ms"]) for o in delayed["observations"]]
            self.assertEqual(delayed_identity, near_identity)

    def test_future_skew_does_not_finalize_physically_open_candle(self):
        result = self._collect("binance-spot.m5", FUTURE_GUARD_NOW_MS)
        opens = {o["value"]["open_time_ms"] for o in result["observations"]}
        self.assertNotIn(SLOT_MS - M5_MS, opens)
        self.assertTrue(all(open_ms + M5_MS <= FUTURE_GUARD_NOW_MS for open_ms in opens))

    def test_temporal_unavailability_is_explicit_validation_failure(self):
        self.actual_ms = FUTURE_GUARD_NOW_MS

        def only_not_yet_final(_symbol, _interval, _limit, physical_now_ms, *, anchor_ms=None):
            self.assertEqual(physical_now_ms, FUTURE_GUARD_NOW_MS)
            self.assertEqual(anchor_ms, SLOT_MS)
            return "fixture-route", [compact_row(SLOT_MS - M5_MS, FUTURE_GUARD_NOW_MS)], []

        with patch("acquisition_core.binance", side_effect=only_not_yet_final), patch("acquisition_core.time.time", return_value=FUTURE_GUARD_NOW_MS / 1000):
            result = self.core.collect("binance-spot.m5", expected_ms=SLOT_MS, cycle_id="fixture-cycle", staging_root=self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failure_class"], "VALIDATION_FAILED")
        self.assertIn("requested slot", result["error"])


class ProviderQueryAnchorRegression(unittest.TestCase):
    def test_binance_provider_query_uses_requested_slot_end_boundary(self):
        urls: list[str] = []

        def fake_get(url: str, retries: int = 3):
            urls.append(url)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "endTime" in qs:
                self.assertEqual(int(qs["endTime"][0]), SLOT_MS - 1)
                opens = anchored_window(SLOT_MS)
            else:
                opens = wall_clock_window(DELAYED_MS)
            return [binance_api_row(open_ms) for open_ms in opens]

        with patch.object(collector, "get", side_effect=fake_get):
            _route, candles, _native = collector.binance(
                "ETHUSDT", "5m", 3, DELAYED_MS, anchor_ms=SLOT_MS
            )
        self.assertTrue(urls)
        self.assertEqual(candles[-1][0], SLOT_MS - M5_MS)
        self.assertTrue(candles[-1][-1])

    def test_kraken_provider_query_uses_requested_slot_since_window(self):
        urls: list[str] = []

        def fake_get(url: str, retries: int = 3):
            urls.append(url)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "since" in qs:
                since_ms = int(qs["since"][0]) * 1000
                self.assertLessEqual(since_ms, SLOT_MS - 4 * M5_MS)
                opens = [
                    SLOT_MS - 4 * M5_MS,
                    SLOT_MS - 3 * M5_MS,
                    SLOT_MS - 2 * M5_MS,
                    SLOT_MS - M5_MS,
                    SLOT_MS,
                    SLOT_MS + M5_MS,
                    SLOT_MS + 2 * M5_MS,
                    SLOT_MS + 3 * M5_MS,
                ]
            else:
                opens = [SLOT_MS + M5_MS, SLOT_MS + 2 * M5_MS, SLOT_MS + 3 * M5_MS]
            return {"error": [], "result": {"XETHZUSD": [kraken_api_row(open_ms) for open_ms in opens], "last": 0}}

        with patch.object(collector, "get", side_effect=fake_get):
            _route, candles, _native = collector.kraken(
                "ETHUSD", "5m", 3, DELAYED_MS, anchor_ms=SLOT_MS
            )
        self.assertTrue(urls)
        self.assertIn("since", urllib.parse.parse_qs(urllib.parse.urlparse(urls[0]).query))
        self.assertEqual(candles[-1][0], SLOT_MS - M5_MS)
        self.assertTrue(candles[-1][-1])


if __name__ == "__main__":
    unittest.main()
