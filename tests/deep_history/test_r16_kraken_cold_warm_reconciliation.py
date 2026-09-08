from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import spot_history
from history_store import ImmutableHistoryConflict, merge_records

DAY = 86_400_000
R13_TS = 1_782_172_800_000


def native_row(ts: int, close: str) -> list[object]:
    return [
        ts,
        "1726.12",
        "1734.46",
        "1633.10",
        close,
        "1671.12",
        "26130.92616972",
        16902,
        ts + DAY - 1,
    ]


class KrakenColdWarmReconciliationTest(unittest.TestCase):
    def test_fully_cold_bucket_is_not_reappended_and_newer_warm_row_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_root = Path(tmp) / "history"
            with patch.object(spot_history, "ROOT", history_root):
                corrected = native_row(R13_TS, "1665.12")
                result = spot_history.append_native_history(
                    "kraken",
                    "ETHUSD",
                    "1d",
                    [corrected],
                    availability_status="PROVIDER_HISTORY_LIMIT",
                )
                self.assertEqual(result["provider_native_rows_observed"], 1)

                release = {
                    "asset_inventory": [
                        {
                            "provider": "kraken",
                            "instrument": "ETHUSD",
                            "interval_or_metric": "1d",
                            "release_tag": "history-kraken-spot-v2",
                            "asset_id": 1,
                            "asset_name": "fixture.json",
                            "sha256": "0" * 64,
                            "size_bytes": 1,
                            "first_timestamp": R13_TS,
                            "last_timestamp": R13_TS,
                            "immutable": True,
                            "integrity_status": "PASS",
                        }
                    ]
                }
                history_root.mkdir(parents=True, exist_ok=True)
                (history_root / "release-manifest.json").write_text(
                    json.dumps(release), encoding="utf-8"
                )

                stale = native_row(R13_TS, "1600.00")
                newer = native_row(R13_TS + DAY, "1700.00")
                result = spot_history.append_native_history(
                    "kraken",
                    "ETHUSD",
                    "1d",
                    [stale, newer],
                    availability_status="PROVIDER_HISTORY_LIMIT",
                )
                self.assertEqual(result["compatibility_rows_observed"], 1)
                self.assertEqual(result["provider_native_rows_observed"], 1)

                path = spot_history.partition_path("kraken", "ETHUSD", "1d", R13_TS)
                payload = json.loads(path.read_text(encoding="utf-8"))
                native = {int(row[0]): row for row in payload["provider_native_records"]}
                self.assertEqual(native[R13_TS][4], "1665.12")
                self.assertEqual(native[R13_TS + DAY][4], "1700.00")
                self.assertNotEqual(native[R13_TS][4], stale[4])

    def test_frontier_is_derived_from_asset_interval_and_not_hard_coded(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_root = Path(tmp) / "history"
            history_root.mkdir(parents=True, exist_ok=True)
            release = {
                "asset_inventory": [
                    {
                        "provider": "kraken",
                        "instrument": "ETHUSD",
                        "interval_or_metric": "1d",
                        "asset_id": 1,
                        "asset_name": "fixture.json",
                        "sha256": "0" * 64,
                        "size_bytes": 1,
                        "first_timestamp": 10 * DAY,
                        "last_timestamp": 12 * DAY,
                        "immutable": True,
                        "integrity_status": "PASS",
                    }
                ]
            }
            (history_root / "release-manifest.json").write_text(
                json.dumps(release), encoding="utf-8"
            )
            with patch.object(spot_history, "ROOT", history_root):
                rows = [native_row(12 * DAY, "1"), native_row(13 * DAY, "2")]
                admitted = spot_history._kraken_warm_eligible_rows("ETHUSD", "1d", rows)
                self.assertEqual([int(row[0]) for row in admitted], [13 * DAY])

    def test_immutable_conflict_semantics_are_not_weakened(self):
        with self.assertRaises(ImmutableHistoryConflict):
            merge_records([[R13_TS, "old"]], [[R13_TS, "different"]])

    def test_incomplete_matching_cold_authority_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_root = Path(tmp) / "history"
            history_root.mkdir(parents=True, exist_ok=True)
            (history_root / "release-manifest.json").write_text(
                json.dumps(
                    {
                        "asset_inventory": [
                            {
                                "provider": "kraken",
                                "instrument": "ETHUSD",
                                "interval_or_metric": "1d",
                                "asset_name": "broken.json",
                                "first_timestamp": R13_TS,
                                "last_timestamp": R13_TS,
                                "immutable": True,
                                "integrity_status": "PASS",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(spot_history, "ROOT", history_root):
                with self.assertRaisesRegex(RuntimeError, "KRAKEN_COLD_ASSET_AUTHORITY_INCOMPLETE"):
                    spot_history._kraken_warm_eligible_rows(
                        "ETHUSD", "1d", [native_row(R13_TS, "1665.12")]
                    )


if __name__ == "__main__":
    unittest.main()
