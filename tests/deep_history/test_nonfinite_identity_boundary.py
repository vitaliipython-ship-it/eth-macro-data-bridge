from __future__ import annotations

import hashlib
import json
import unittest

import tools.history_consumer  # establish canonical history-access import compatibility
from tools.history_access_v2 import _plan_digest, build_semantic_receipt, compact


class SemanticIdentityNonFiniteBoundaryTests(unittest.TestCase):
    def test_finite_compact_bytes_preserve_previous_identity(self):
        value = [{"timestamp_ms": 1, "value": {"close": "1900", "unicode": "Δ"}, "finality": "FINALIZED"}]
        old_bytes = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
        )
        self.assertEqual(compact(value), old_bytes)
        self.assertEqual(hashlib.sha256(compact(value)).hexdigest(), hashlib.sha256(old_bytes).hexdigest())

    def test_semantic_receipt_rejects_non_finite_output_identity(self):
        observations = [{"timestamp_ms": 1, "value": {"x": float("nan")}, "finality": "FINALIZED"}]
        with self.assertRaises(ValueError):
            build_semantic_receipt(
                series_id="spot.binance-spot.ETHUSDT.ohlcv.5m",
                start_ms=0,
                end_ms=300000,
                cutoff_ms=None,
                mode="strict",
                current_policy="FINALIZED_ONLY",
                resolution_plan_sha256="a" * 64,
                observations=observations,
                finality="FINALIZED",
                revision_context=None,
            )

    def test_resolution_plan_digest_rejects_non_finite_identity_input(self):
        plan = {
            "schema_version": "market-data-resolution-plan/2.0.0",
            "plan_sha256": "ignored",
            "authority": {"nonfinite": float("inf")},
        }
        with self.assertRaises(ValueError):
            _plan_digest(plan)


if __name__ == "__main__":
    unittest.main()
