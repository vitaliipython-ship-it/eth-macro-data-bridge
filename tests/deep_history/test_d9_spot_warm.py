from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import spot_history
from history_store import ImmutableHistoryConflict


class D92SpotWarmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_history = spot_history.ROOT
        self.old_archive = spot_history.ARCHIVE_ROOT
        spot_history.ROOT = self.root / "history"
        spot_history.ARCHIVE_ROOT = self.root / "archive"
        spot_history.ROOT.mkdir(parents=True)

    def tearDown(self):
        spot_history.ROOT = self.old_history
        spot_history.ARCHIVE_ROOT = self.old_archive
        self.tmp.cleanup()

    def test_binance_native_append_is_idempotent(self):
        row = [1786752000000, "1", "2", "0.5", "1.5", "10", 1786752299999, "15", 3, "6", "9"]
        first = spot_history.append_native_history("binance", "ETHUSDT", "5m", [row], availability_status="PASS")
        path = spot_history.partition_path("binance", "ETHUSDT", "5m", row[0])
        raw = path.read_bytes()
        second = spot_history.append_native_history("binance", "ETHUSDT", "5m", [row], availability_status="PASS")
        self.assertEqual(path.read_bytes(), raw)
        self.assertGreaterEqual(first["compatibility_rows_observed"], 1)
        self.assertEqual(second["compatibility_rows_observed"], 0)

    def test_kraken_preserves_d6_records_and_adds_native_evidence(self):
        row = [1786752000000, "1", "2", "0.5", "1.5", "1.4", "10", 7, 1786752299999]
        spot_history.append_native_history("kraken", "ETHUSD", "5m", [row], availability_status="PROVIDER_HISTORY_LIMIT")
        path = spot_history.partition_path("kraken", "ETHUSD", "5m", row[0])
        payload = json.loads(path.read_text())
        self.assertEqual(payload["columns"], spot_history.KRAKEN_COMPAT_COLUMNS)
        self.assertEqual(payload["records"], [[row[0], "1", "2", "0.5", "1.5", "10", 1786752299999]])
        self.assertEqual(payload["provider_native_columns"], spot_history.KRAKEN_NATIVE_COLUMNS)
        self.assertEqual(payload["provider_native_records"], [row])

    def test_archive_migration_rejects_market_value_conflict(self):
        ts = 1786752000000
        spot_history.append_native_history(
            "binance", "ETHUSDT", "5m",
            [[ts, "1", "2", "0.5", "1.5", "10", ts + 299999, "15", 3, "6", "9"]],
            availability_status="PASS",
        )
        path = spot_history.ARCHIVE_ROOT / "2026/08/15/binance/ETHUSDT-5m.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "provider":"binance","symbol":"ETHUSDT",
            "candles":[[ts, "1", "2", "0.5", "1.6", "10", ts + 299999, "16", 3, "6", "10"]],
        }))
        with self.assertRaises(ImmutableHistoryConflict):
            spot_history.migrate_archive_m5()

    def test_kraken_archive_migration_enriches_overlap_without_rewriting_projection(self):
        ts = 1786752000000
        history_path = spot_history.partition_path("kraken", "ETHUSD", "5m", ts)
        history_path.parent.mkdir(parents=True)
        history_path.write_text(json.dumps({
            "schema_version":"1.0.0","provider":"kraken","symbol":"ETHUSD","interval":"5m",
            "columns":spot_history.KRAKEN_COMPAT_COLUMNS,"closed_only":True,"partitioning":"daily",
            "availability_status":"PROVIDER_HISTORY_LIMIT",
            "records":[[ts,"1","2","0.5","1.5","10",ts+299999]],
        }))
        archive_path = spot_history.ARCHIVE_ROOT / "2026/08/15/kraken/ETHUSD-5m.json"
        archive_path.parent.mkdir(parents=True)
        archive_path.write_text(json.dumps({
            "provider":"kraken","symbol":"ETHUSD",
            "candles":[[ts,"1","2","0.5","1.5","1.4","10",7]],
        }))
        result = spot_history.migrate_archive_m5()
        payload = json.loads(history_path.read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(payload["records"], [[ts,"1","2","0.5","1.5","10",ts+299999]])
        self.assertEqual(payload["provider_native_records"][0][5], "1.4")
        self.assertEqual(payload["provider_native_records"][0][7], 7)

    def test_complete_m5_bucket_matches_native_and_partial_bucket_rejects(self):
        opened = 1786752000000
        m5 = []
        for index in range(3):
            ts = opened + index * 300000
            m5.append([ts, str(1+index), str(2+index), str(0.5+index), str(1.5+index), "10", ts+299999, "15", 3, "6", "9"])
        derived = spot_history.derive_m5_bucket(m5, opened, "15m", "binance")
        native = [opened, "1", "4", "0.5", "3.5", "30", opened+899999, "45", 9, "18", "27"]
        self.assertEqual(spot_history.compare_native_to_derived(native, derived, "binance", native=True), "EQUIVALENT")
        with self.assertRaises(spot_history.IncompleteAggregationBucket):
            spot_history.derive_m5_bucket(m5[:-1], opened, "15m", "binance")


if __name__ == "__main__":
    unittest.main()
