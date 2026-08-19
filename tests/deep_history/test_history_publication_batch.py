from __future__ import annotations

import copy
import hashlib
import json
import math
import unittest

from canonical_json import canonical_json_bytes
from history_publication_batch import (
    PublicationBatchError,
    batch_id_preimage,
    build_publication_batch,
    membership_preimage,
    payload_binding_preimage,
    validate_publication_batch,
)


def envelope(series: str, ts: str, suffix: str) -> dict:
    value = {"price": suffix, "nested": {"unicode": "Δ"}}
    fingerprint = hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "market-data-d8-runtime-observation/1.0.0",
        "observation_id": "obs-" + hashlib.sha256(f"{series}|{ts}|{suffix}".encode()).hexdigest(),
        "fingerprint": fingerprint,
        "provider": "binance-spot",
        "capability_id": "binance-spot.m5",
        "series_id": series,
        "provider_timestamp_at": ts,
        "known_at": ts,
        "retrieved_at": ts,
        "collected_at": ts,
        "canonical_cycle_id": "d8c-test",
        "canonical_slot": ts,
        "finality": "FINALIZED",
        "validation_status": "PASS",
        "provenance": {"runtime_contract": "eth-macro-d8-runtime/1.0.0", "source_revision": "test"},
        "d9_forward_seam": {"target": "FIXED_GRID"},
        "value": value,
    }


class PublicationBatchDeterminismTests(unittest.TestCase):
    def setUp(self):
        self.a = envelope("spot.binance-spot.SOLUSDT.ohlcv.5m", "2026-08-19T12:00:00.000Z", "a")
        self.b = envelope("spot.binance-spot.BTCUSDT.ohlcv.5m", "2026-08-19T12:05:00.000Z", "b")

    def test_same_input_different_process_order_same_batch(self):
        first = build_publication_batch([self.a, self.b])
        second = build_publication_batch([copy.deepcopy(self.b), copy.deepcopy(self.a)])
        self.assertEqual(first, second)
        self.assertEqual(
            canonical_json_bytes({"z": "Δ", "a": None, "n": 7}),
            b'{"a":null,"n":7,"z":"\xce\x94"}',
        )
        reference_membership = hashlib.sha256(
            json.dumps(
                membership_preimage(first["member_observation_ids"]),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        reference_payload = hashlib.sha256(
            json.dumps(
                payload_binding_preimage(first["members"]),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        reference_batch = "pub-" + hashlib.sha256(
            json.dumps(
                batch_id_preimage(first),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(first["membership_sha256"], reference_membership)
        self.assertEqual(first["payload_sha256"], reference_payload)
        self.assertEqual(first["batch_id"], reference_batch)
        self.assertNotIn("backend_profile", first)
        self.assertNotIn("publication_attempt_id", first)

    def test_non_finite_payload_cannot_create_batch_identity(self):
        candidate = copy.deepcopy(self.a)
        candidate["value"]["nonfinite"] = math.nan
        with self.assertRaises(ValueError):
            build_publication_batch([candidate])

    def test_negative_cross_field_consistency_matrix(self):
        valid = build_publication_batch([self.a, self.b])
        cases = {}
        mutated = copy.deepcopy(valid); mutated["members"] = list(reversed(mutated["members"])); cases["reordered"] = mutated
        mutated = copy.deepcopy(valid); mutated["members"][1]["observation_id"] = mutated["members"][0]["observation_id"]; mutated["member_observation_ids"][1] = mutated["member_observation_ids"][0]; cases["duplicate"] = mutated
        mutated = copy.deepcopy(valid); mutated["member_observation_ids"][0] = "obs-" + "f" * 64; cases["membership-list"] = mutated
        mutated = copy.deepcopy(valid); mutated["members"].pop(); cases["missing-member"] = mutated
        mutated = copy.deepcopy(valid); mutated["members"][0]["position"] = 7; cases["position"] = mutated
        mutated = copy.deepcopy(valid); mutated["membership_sha256"] = "0" * 64; cases["membership-hash"] = mutated
        mutated = copy.deepcopy(valid); mutated["payload_sha256"] = "0" * 64; cases["payload-hash"] = mutated
        mutated = copy.deepcopy(valid); mutated["batch_id"] = "pub-" + "0" * 64; cases["batch-id"] = mutated
        mutated = copy.deepcopy(valid); mutated["backend_profile"] = "GITHUB_FIRST_V1"; cases["backend-leak"] = mutated
        for name, candidate in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(PublicationBatchError):
                    validate_publication_batch(candidate)
