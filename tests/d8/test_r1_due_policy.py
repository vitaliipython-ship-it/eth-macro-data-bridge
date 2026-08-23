from __future__ import annotations

import unittest
from datetime import datetime, timezone

from d8_runtime import CAPABILITY_POLICY, due_state


def ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp() * 1000)


def cap(capability_id: str):
    return next(row for row in CAPABILITY_POLICY if row["id"] == capability_id)


class AbsoluteDuePolicyCase(unittest.TestCase):
    def assert_boundary(self, capability_id: str, positive: int, *negative: int) -> None:
        capability = cap(capability_id)
        self.assertEqual(due_state(capability, positive, "development"), "DUE")
        for timestamp in negative:
            self.assertEqual(due_state(capability, timestamp, "development"), "NOT_DUE")

    def test_15m_positive_and_negative_boundary(self):
        self.assert_boundary("binance-spot.15m", ms(2026, 8, 24, 12, 15), ms(2026, 8, 24, 12, 10), ms(2026, 8, 24, 12, 20))

    def test_1h_positive_and_negative_boundary(self):
        self.assert_boundary("binance-spot.1h", ms(2026, 8, 24, 13, 0), ms(2026, 8, 24, 12, 55), ms(2026, 8, 24, 13, 5))

    def test_4h_positive_and_negative_boundary(self):
        self.assert_boundary("binance-spot.4h", ms(2026, 8, 24, 12, 0), ms(2026, 8, 24, 11, 55), ms(2026, 8, 24, 13, 0))

    def test_1d_positive_and_negative_boundary(self):
        self.assert_boundary("binance-spot.1d", ms(2026, 8, 25, 0, 0), ms(2026, 8, 24, 23, 55), ms(2026, 8, 25, 0, 5))

    def test_1w_monday_utc_transition(self):
        self.assertEqual(datetime(2026, 8, 24, tzinfo=timezone.utc).weekday(), 0)
        self.assert_boundary("binance-spot.1w", ms(2026, 8, 24, 0, 0), ms(2026, 8, 23, 23, 55), ms(2026, 8, 24, 0, 5), ms(2026, 8, 17, 0, 5))
        self.assertEqual(due_state(cap("binance-spot.1w"), ms(2026, 8, 17, 0, 0), "development"), "DUE")

    def test_provider_equivalent_capabilities_share_absolute_schedule(self):
        for suffix in ("15m", "1h", "4h", "1d", "1w"):
            b = cap(f"binance-spot.{suffix}")
            k = cap(f"kraken-spot.{suffix}")
            self.assertEqual((b["every_minutes"], b["schedule_anchor_ms"]), (k["every_minutes"], k["schedule_anchor_ms"]))

    def test_schedule_is_epoch_arithmetic_not_local_time(self):
        weekly = cap("binance-spot.1w")
        self.assertEqual(weekly["schedule_anchor_utc"], "1970-01-05T00:00:00Z")
        self.assertEqual(due_state(weekly, ms(2026, 3, 30, 0, 0), "development"), "DUE")
        self.assertEqual(due_state(weekly, ms(2026, 10, 26, 0, 0), "development"), "DUE")


if __name__ == "__main__":
    unittest.main()
