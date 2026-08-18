from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.history_consumer import HistoryConsumerError, read_history
from tools.history_access_v2 import build_semantic_receipt, compact


SERIES = "spot.binance-spot.ETHUSDT.ohlcv.5m"
PLAN_SHA = "a" * 64
ROWS = [
    (1786975200000, "1900", "1910", "1890", "1905", "12.5"),
    (1786975500000, "1905", "1912", "1901", "1910", "13.0"),
]
DIAGNOSTICS = {
    "requested_start": "2026-08-17T14:00:00Z",
    "requested_end": "2026-08-17T14:10:00Z",
    "status": "PASS",
    "rows": 2,
    "expected_rows": 2,
    "gap_count": 0,
    "duplicates": 0,
    "sources": [],
}
PLAN = {
    "plan_sha256": PLAN_SHA,
    "request": {
        "series_id": SERIES,
        "start_ms": 1786975200000,
        "end_ms": 1786975800000,
        "cutoff_ms": None,
    },
}


class SemanticReceiptV2Tests(unittest.TestCase):
    def test_d6_receipt_is_canonical_and_transport_hash_is_separate(self):
        with tempfile.TemporaryDirectory() as cache, patch(
            "tools.history_consumer.resolve_capability", return_value=PLAN
        ), patch(
            "tools.history_consumer.materialize_resolution_plan", return_value=(ROWS, DIAGNOSTICS)
        ):
            _, csv_payload, _, csv_receipt = read_history(
                SERIES,
                "caller-string-not-used-as-receipt-authority",
                "caller-string-not-used-as-receipt-authority",
                cache_dir=Path(cache),
                output_format="csv",
            )
            _, json_payload, _, json_receipt = read_history(
                SERIES,
                "caller-string-not-used-as-receipt-authority",
                "caller-string-not-used-as-receipt-authority",
                cache_dir=Path(cache),
                output_format="json",
            )

        semantic = csv_receipt["semantic_receipt"]
        self.assertEqual(csv_receipt["schema_version"], "history-consumer-receipt/1.0.0")
        self.assertEqual(csv_receipt["receipt_role"], "LEGACY_TRANSPORT_WRAPPER")
        self.assertEqual(semantic["receipt_schema_version"], "history-access-receipt/2.0.0")
        self.assertEqual(semantic["series_id"], SERIES)
        self.assertEqual(semantic["request"], {
            "from_utc": "2026-08-17T14:00:00Z",
            "to_utc": "2026-08-17T14:10:00Z",
            "cutoff_utc": None,
            "mode": "strict",
            "current_policy": "FINALIZED_ONLY",
        })
        self.assertEqual(semantic["resolution_plan_sha256"], PLAN_SHA)
        self.assertEqual(semantic["observation_count"], 2)
        self.assertEqual(semantic["finality"], "FINALIZED")
        self.assertIsNone(semantic["revision_context"])
        self.assertEqual(csv_receipt["output_sha256"], hashlib.sha256(csv_payload.encode()).hexdigest())
        self.assertEqual(csv_receipt["transport_output_sha256"], csv_receipt["output_sha256"])
        self.assertEqual(json_receipt["output_sha256"], hashlib.sha256(json_payload.encode()).hexdigest())
        self.assertNotEqual(csv_receipt["transport_output_sha256"], json_receipt["transport_output_sha256"])
        self.assertEqual(csv_receipt["semantic_output_sha256"], json_receipt["semantic_output_sha256"])
        self.assertEqual(csv_receipt["semantic_receipt"], json_receipt["semantic_receipt"])

    def test_d6_provisional_current_policy_fails_closed(self):
        with self.assertRaises(HistoryConsumerError) as caught:
            read_history(
                SERIES,
                "2026-08-17T14:00:00Z",
                "2026-08-17T14:10:00Z",
                current_policy="INCLUDE_CURRENT_PROVISIONAL",
            )
        self.assertEqual(caught.exception.code, "CURRENT_POLICY_UNSUPPORTED")

    def test_canonical_builder_hashes_normalized_semantic_materialization(self):
        observations = [{"timestamp_ms": 1, "value": {"close": "1900"}, "finality": "FINALIZED"}]
        receipt = build_semantic_receipt(
            series_id=SERIES,
            start_ms=0,
            end_ms=300000,
            cutoff_ms=None,
            mode="strict",
            current_policy="FINALIZED_ONLY",
            resolution_plan_sha256=PLAN_SHA,
            observations=observations,
            finality="FINALIZED",
            revision_context=None,
        )
        self.assertEqual(receipt["output_sha256"], hashlib.sha256(compact(observations)).hexdigest())
        self.assertEqual(set(receipt), {
            "receipt_schema_version", "series_id", "request", "resolution_plan_sha256",
            "output_sha256", "observation_count", "finality", "revision_context",
        })
        self.assertFalse(any("path" in key or "storage" in key for key in receipt))


if __name__ == "__main__":
    unittest.main()
