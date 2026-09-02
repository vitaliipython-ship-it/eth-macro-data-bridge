from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from event_window import nearest_v4
from intelligence import depth_metrics
from sampled_history import durable_partition_path, persist_sampled_intelligence


class D9LiquidityReproducibilityTests(unittest.TestCase):
    def test_order_book_snapshot_preserves_every_level_used_by_calculation(self):
        bids = [[str(2000 - index), str(1 + index / 100)] for index in range(100)]
        asks = [[str(2001 + index), str(1 + index / 100)] for index in range(100)]
        result = depth_metrics({"bids": bids, "asks": asks}, 1786965000000, "binance-spot", "ETHUSDT")
        self.assertEqual(result["raw_level_count"], {"bids": 100, "asks": 100})
        self.assertEqual(len(result["raw"]["bids"]), 100)
        self.assertEqual(len(result["raw"]["asks"]), 100)
        self.assertEqual(result["raw"]["bids"][-1], bids[-1])
        self.assertEqual(result["raw"]["asks"][-1], asks[-1])

    def test_snapshot_does_not_invent_binance_usdm_collection(self):
        result = depth_metrics(
            {"bids": [["2000", "1"]], "asks": [["2001", "1"]]},
            1786965000000,
            "binance-spot",
            "ETHUSDT",
        )
        self.assertEqual(result["provider"], "binance-spot")
        self.assertNotEqual(result["provider"], "binance-usdm")

    def test_g2a_successor_partition_is_invisible_to_legacy_nearest_v4_snapshot_decoder(self):
        timestamp_ms = 1786965000000
        event_ms = timestamp_ms + 1_000
        legacy_payload = {
            "timestamp_ms": timestamp_ms,
            "snapshots": [{"provider": "binance-spot", "instrument": "ETHUSDT"}],
        }
        successor_payload = {
            "schema_version": "liquidity-durable-l2-observation-partition/1.0.0",
            "date_utc": "2026-08-17",
            "history_family": "liquidity.orderbook-snapshots",
            "observations": [
                {
                    "provider_id": "binance-spot",
                    "instrument_id": "ETHUSDT",
                    "book_kind": "L2_LEVEL_BOOK",
                    "observation_time_ms": timestamp_ms,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "liquidity/snapshots/2026/08/17" / f"{timestamp_ms}.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(json.dumps(legacy_payload) + "\n", encoding="utf-8")
            successor = durable_partition_path(timestamp_ms, root=root)
            successor.parent.mkdir(parents=True, exist_ok=True)
            successor.write_text(json.dumps(successor_payload) + "\n", encoding="utf-8")
            self.assertTrue(successor.as_posix().endswith("history/liquidity-orderbook-snapshots/2026/08/17/observations.json"))
            self.assertNotIn("/liquidity/snapshots/", successor.as_posix())

            previous = Path.cwd()
            try:
                os.chdir(root)
                package = nearest_v4(event_ms)
            finally:
                os.chdir(previous)

            self.assertIsNotNone(package["liquidity"])
            assert package["liquidity"] is not None
            self.assertEqual(package["liquidity"]["source_timestamp"], timestamp_ms)
            self.assertEqual(package["liquidity"]["data"], legacy_payload)
            self.assertEqual(package["liquidity"]["source_path"], legacy.relative_to(root).as_posix())

    def test_g2a_writer_keeps_durable_records_out_of_d9_sampled_ledger_until_g2b(self):
        now = 1786965000000
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            option_path = root / "options/snapshots/2026/08/17" / f"{now}.json"
            liquidity_path = root / "liquidity/snapshots/2026/08/17" / f"{now}.json"
            option_path.parent.mkdir(parents=True, exist_ok=True)
            liquidity_path.parent.mkdir(parents=True, exist_ok=True)
            option_path.write_text("{}\n", encoding="utf-8")
            liquidity_path.write_text("{}\n", encoding="utf-8")
            intelligence = {
                "derivatives": {
                    "providers": {
                        "deribit-perpetual": {
                            "status": "PASS",
                            "instruments": {
                                "ETH-PERPETUAL": {
                                    "timestamp_ms": now - 1000,
                                    "mark_price": 2000,
                                    "index_price": 1999,
                                    "open_interest": 10,
                                    "current_funding": 0.0,
                                    "funding_8h": 0.0,
                                    "volume_24h": 100,
                                    "volume_usd_24h": 200000,
                                }
                            },
                        }
                    }
                },
                "options": {"providers": {"deribit": {"status": "PASS", "latest_surface": option_path.as_posix()}}},
                "liquidity": {"collection": {"status": "PASS", "latest_path": liquidity_path.as_posix()}},
            }
            fake_g2a = {
                "status": "PASS",
                "acquisition_route": "S1_TO_S2_TO_S3",
                "capability_count": 6,
                "records": [],
                "persistence": [],
            }
            previous = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch("sampled_history.persist_g2a_baseline", return_value=fake_g2a):
                    result = persist_sampled_intelligence(
                        intelligence,
                        expected_ms=now,
                        started_ms=now,
                        completed_ms=now + 2000,
                        target_cadence_seconds=3600,
                        enable_g2a=True,
                    )
            finally:
                os.chdir(previous)

            self.assertEqual(result["g2a"], fake_g2a)
            self.assertEqual(result["run_count"], 3)
            ledger = json.loads((root / result["ledger_path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(ledger["runs"]), 3)
            self.assertEqual(
                {row["series_or_capability"] for row in ledger["runs"]},
                {
                    "derivatives.deribit-perpetual.current-snapshot",
                    "options.deribit-options.ETH.surface-snapshots",
                    "liquidity.orderbook-snapshots",
                },
            )
            liquidity_row = next(
                row for row in ledger["runs"]
                if row["series_or_capability"] == "liquidity.orderbook-snapshots"
            )
            self.assertEqual(liquidity_row["run_id"], f"liquidity-orderbook:{now}")
            self.assertEqual(liquidity_row["provider"], "multi-provider")
            self.assertFalse(any(str(row["run_id"]).startswith("liquidity-g2a:") for row in ledger["runs"]))


if __name__ == "__main__":
    unittest.main()
