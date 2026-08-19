from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from d8_capability_routing import declarations_from_contract, route_capability_series, runtime_due_policy
from history_publication_batch import build_publication_batch

ROOT = Path(__file__).resolve().parents[2]


def load_contract() -> dict:
    return json.loads((ROOT / "contracts/d8-runtime-candidate.json").read_text(encoding="utf-8"))


class HorizontalCapabilityExtensibilityTests(unittest.TestCase):
    def test_new_instrument_reuses_existing_family_declaration(self):
        route = route_capability_series(
            "binance-spot.m5",
            "binance-spot",
            "spot.binance-spot.SOLUSDT.ohlcv.5m",
        )
        self.assertEqual(route["lifecycle_class"], "FIXED_GRID")
        self.assertEqual(route["normalization_family"], "OHLCV")
        self.assertEqual(route["target_residence_role"], "WARM")

    def test_new_metric_requires_declaration_not_forwarder_code(self):
        contract = load_contract()
        caps = contract["due_policy"]["capabilities"]
        target = next(row for row in caps if row["id"] == "binance-spot.m5")
        target["forwarding"]["series_rules"].append(
            {
                "series_id_regex": r"^spot\.binance-spot\.[A-Z0-9_-]+\.mark-price\.5m$",
                "lifecycle_class": "FIXED_GRID",
                "normalization_family": "SCALAR_TIME_SERIES",
                "finality_policy": "FINALIZED_ONLY",
                "allowed_finality": ["FINALIZED"],
                "publication_eligibility": "VALIDATED_TERMINAL_CHECKPOINT_V2",
            }
        )
        declarations = declarations_from_contract(contract)
        route = route_capability_series(
            "binance-spot.m5",
            "binance-spot",
            "spot.binance-spot.SOLUSDT.mark-price.5m",
            declarations=declarations,
        )
        self.assertEqual(route["normalization_family"], "SCALAR_TIME_SERIES")
        self.assertEqual(route["lifecycle_class"], "FIXED_GRID")

    def test_due_policy_is_derived_from_same_contract(self):
        contract = load_contract()
        declarations = declarations_from_contract(contract)
        derived = {row["id"]: row for row in runtime_due_policy(declarations)}
        for capability in contract["due_policy"]["capabilities"]:
            self.assertEqual(derived[capability["id"]]["provider"], capability["provider"])
            self.assertEqual(derived[capability["id"]]["every_minutes"], capability["cadence_minutes"])

    def test_horizontal_expansion_is_independent_of_backend_profile(self):
        value = {"close": "200.0"}
        fingerprint = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        env = {
            "observation_id": "obs-" + "1" * 64,
            "series_id": "spot.binance-spot.SOLUSDT.ohlcv.5m",
            "provider": "binance-spot",
            "provider_timestamp_at": "2026-08-19T12:00:00.000Z",
            "known_at": "2026-08-19T12:00:01.000Z",
            "fingerprint": fingerprint,
            "finality": "FINALIZED",
            "value": value,
        }
        batch = build_publication_batch([env])
        self.assertNotIn("backend_profile", batch)
        self.assertNotIn("publication_attempt_id", batch)
        self.assertEqual(batch["target_residence_role"], "WARM")
