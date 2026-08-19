from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from d8_runtime import D8Runtime, DeterministicMockAcquisition, RuntimeConfig, fingerprint_payload

ROOT = Path(__file__).resolve().parents[2]


class NonFiniteIdentityBoundaryTests(unittest.TestCase):
    def test_finite_payload_fingerprint_matches_previous_serialization(self):
        payload = {"nested": {"n": 7, "unicode": "Δ"}, "values": [1, None, "x"], "flag": True}
        old_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        expected = hashlib.sha256(old_bytes).hexdigest()
        self.assertEqual(fingerprint_payload(payload), expected)

    def test_non_finite_fingerprint_values_fail_closed(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    fingerprint_payload({"x": value})

    def test_non_finite_payload_fails_before_observation_identity_or_spool(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = D8Runtime(
                RuntimeConfig(state_root=Path(tmp), profile="test", source_revision="nonfinite-test"),
                DeterministicMockAcquisition(),
            )
            capability = {"id": "binance-spot.m5", "provider": "binance-spot"}
            row = {
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m",
                "provider_timestamp_at": "2026-08-19T14:00:00.000Z",
                "value": {"close": float("nan")},
            }
            with patch("d8_runtime.observation_id") as observation_id_mock:
                with self.assertRaises(ValueError):
                    runtime._normalize_observations(
                        capability,
                        [row],
                        "d8c-nonfinite-test",
                        "2026-08-19T14:00:00.000Z",
                        1787148000000,
                    )
                observation_id_mock.assert_not_called()
            with runtime.state.connect() as db:
                spool_rows = int(db.execute("SELECT COUNT(*) FROM spool").fetchone()[0])
            self.assertEqual(spool_rows, 0)

    def test_forwarding_contract_matches_canonical_non_finite_policy(self):
        contract = json.loads((ROOT / "contracts/d8-d9-forwarding-v1.json").read_text(encoding="utf-8"))
        source = contract["source"]
        canonical = contract["publication_batch"]["canonical_serialization"]
        self.assertEqual(source["payload_fingerprint_canonical_primitive"], "src/canonical_json.py::sha256_canonical_json")
        self.assertEqual(source["payload_fingerprint_non_finite_policy"], "REJECT")
        self.assertIn("allow_nan=False", canonical["algorithm"])
        self.assertEqual(canonical["non_finite_numbers"], "REJECT")


if __name__ == "__main__":
    unittest.main()
