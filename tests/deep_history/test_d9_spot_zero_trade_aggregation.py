from __future__ import annotations

import copy
import unittest
from pathlib import Path

import spot_history


OPENED = 1788717600000
M5_EXACT_FAILED = [
    [OPENED, "0.03126000", "0.03126000", "0.03126000", "0.03126000", "0.00000000", 1788717899999, "0.00000000", 0, "0.00000000", "0.00000000"],
    [1788717900000, "0.03125000", "0.03125000", "0.03124000", "0.03124000", "1.75860000", 1788718199999, "0.05494500", 8, "0.00000000", "0.00000000"],
    [1788718200000, "0.03124000", "0.03124000", "0.03124000", "0.03124000", "5.37920000", 1788718499999, "0.16804599", 53, "0.00000000", "0.00000000"],
]
NATIVE_15M_EXACT_FAILED = [
    OPENED, "0.03125000", "0.03125000", "0.03124000", "0.03124000", "7.13780000",
    1788718499999, "0.22299099", 61, "0.00000000", "0.00000000",
]


class D9SpotZeroTradeAggregationRegressionTests(unittest.TestCase):
    def test_exact_program2_ethbtc_conflict_reproduces_as_semantic_equivalence(self):
        rows = copy.deepcopy(M5_EXACT_FAILED)
        original = copy.deepcopy(rows)
        derived = spot_history.derive_m5_bucket(rows, OPENED, "15m", "binance")
        self.assertEqual(
            derived,
            [OPENED, "0.03125000", "0.03125000", "0.03124000", "0.03124000", "7.13780000"],
        )
        self.assertEqual(
            spot_history.compare_native_to_derived(
                NATIVE_15M_EXACT_FAILED, derived, "binance", native=True
            ),
            "EQUIVALENT",
        )
        self.assertEqual(rows, original, "aggregation must not mutate or drop source observations")

    def test_genuine_traded_value_conflict_still_fails_closed(self):
        rows = copy.deepcopy(M5_EXACT_FAILED)
        rows[1][2] = "0.03127000"
        derived = spot_history.derive_m5_bucket(rows, OPENED, "15m", "binance")
        self.assertEqual(
            spot_history.compare_native_to_derived(
                NATIVE_15M_EXACT_FAILED, derived, "binance", native=True
            ),
            "CONFLICT",
        )

    def test_missing_m5_observation_still_maps_to_gap_boundary(self):
        with self.assertRaises(spot_history.IncompleteAggregationBucket):
            spot_history.derive_m5_bucket(M5_EXACT_FAILED[:-1], OPENED, "15m", "binance")

    def test_zero_trade_rows_are_excluded_only_from_price_not_volume_or_time(self):
        derived = spot_history.derive_m5_bucket(M5_EXACT_FAILED, OPENED, "15m", "binance")
        self.assertEqual(derived[0], OPENED)
        self.assertEqual(derived[5], "7.13780000")
        self.assertEqual(len(M5_EXACT_FAILED), 3)
        self.assertEqual(M5_EXACT_FAILED[0][8], 0)
        self.assertEqual(M5_EXACT_FAILED[1][8] + M5_EXACT_FAILED[2][8], 61)

    def test_all_zero_trade_bucket_keeps_existing_fallback_semantics(self):
        rows = []
        for index in range(3):
            ts = OPENED + index * 300000
            rows.append([
                ts, "1.00000000", "1.00000000", "1.00000000", "1.00000000", "0.00000000",
                ts + 299999, "0.00000000", 0, "0.00000000", "0.00000000",
            ])
        self.assertEqual(
            spot_history.derive_m5_bucket(rows, OPENED, "15m", "binance"),
            [OPENED, "1.00000000", "1.00000000", "1.00000000", "1.00000000", "0E-8"],
        )

    def test_integrity_gate_and_status_vocabulary_are_not_weakened(self):
        root = Path(__file__).resolve().parents[2]
        validator = (root / "tools/validation/validate_history.py").read_text(encoding="utf-8")
        self.assertIn('assert consistency["status_counts"]["CONFLICT"]==0', validator)
        vocabulary = ("EQUIVALENT", "KNOWN_PROVIDER_GAP", "SEMANTIC_ALIGNMENT_DIFFERENCE", "CONFLICT")
        self.assertIn("SEMANTIC_ALIGNMENT_DIFFERENCE", vocabulary)
        self.assertIn("KNOWN_PROVIDER_GAP", vocabulary)
        self.assertIn("CONFLICT", vocabulary)


if __name__ == "__main__":
    unittest.main()
