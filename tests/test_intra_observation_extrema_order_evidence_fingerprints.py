from __future__ import annotations

import copy
import hashlib
import json
import math
import unittest
from pathlib import Path

from tools.intra_observation_extrema_order_evidence import (
    COMPANION_CONTRACT_ID,
    FingerprintCanonicalizationError,
    build_carrier_fingerprint_payload,
    build_evidence_fingerprint_payload,
    canonical_json_bytes,
    compute_carrier_fingerprint,
    compute_evidence_fingerprint,
    strict_json_loads,
    validate_carrier_fingerprints,
)

ROOT = Path(__file__).resolve().parents[1]
COMPANION_PATH = ROOT / "contracts/intra-observation-extrema-order-evidence-fingerprint-canonicalization-v1.json"
PARENT_PATH = ROOT / "contracts/intra-observation-extrema-order-evidence-v1.json"
BRIDGE_PATH = ROOT / "bridge-contract.json"
PARENT_BLOB = "2ad4ca7f54f15468c3f6f39f725ed0625f62e18e"
PARENT_SHA256 = "2b84f071eb265e902565cddaab8ecb9eb16ac7c05b7793f446aeea7db842ff04"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class ExtremaOrderFingerprintVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.companion = read_json(COMPANION_PATH)
        cls.vectors = {row["vector_id"]: row for row in cls.companion["test_vectors"]}

    def _carrier(self, vector_id: str = "LOWER_TF_HIGH_BEFORE_LOW") -> dict:
        return copy.deepcopy(self.vectors[vector_id]["input_carrier_subset"])

    def test_vector_1_lower_tf_high_before_low(self):
        self._assert_vector("LOWER_TF_HIGH_BEFORE_LOW")

    def test_vector_2_lower_tf_low_before_high(self):
        self._assert_vector("LOWER_TF_LOW_BEFORE_HIGH")

    def test_vector_3_lower_tf_unresolved_same_child(self):
        self._assert_vector("LOWER_TF_UNRESOLVED_SAME_CHILD")

    def test_vector_4_flat_order_not_materially_distinct(self):
        self._assert_vector("FLAT_ORDER_NOT_MATERIALLY_DISTINCT")

    def _assert_vector(self, vector_id: str) -> None:
        row = self.vectors[vector_id]
        carrier = row["input_carrier_subset"]
        evidence_payload = build_evidence_fingerprint_payload(carrier)
        carrier_payload = build_carrier_fingerprint_payload(carrier)
        self.assertEqual(row["exact_evidence_payload"], evidence_payload)
        self.assertEqual(row["canonical_evidence_json_utf8"], canonical_json_bytes(evidence_payload).decode("utf-8"))
        self.assertEqual(row["expected_evidence_fingerprint"], compute_evidence_fingerprint(carrier))
        self.assertEqual(row["exact_carrier_payload"], carrier_payload)
        self.assertEqual(row["canonical_carrier_json_utf8"], canonical_json_bytes(carrier_payload).decode("utf-8"))
        self.assertEqual(row["expected_carrier_fingerprint"], compute_carrier_fingerprint(carrier))
        self.assertEqual("VALID", validate_carrier_fingerprints(carrier, "2026-09-14T10:00:00Z")["status"])

    def test_a_object_key_insertion_order_does_not_change_fingerprint(self):
        payload = self.vectors["LOWER_TF_HIGH_BEFORE_LOW"]["exact_evidence_payload"]
        reversed_payload = dict(reversed(list(payload.items())))
        self.assertEqual(canonical_json_bytes(payload), canonical_json_bytes(reversed_payload))
        self.assertEqual(hashlib.sha256(canonical_json_bytes(payload)).digest(), hashlib.sha256(canonical_json_bytes(reversed_payload)).digest())

    def test_b_supporting_child_chronology_permutation_changes_evidence_fingerprint(self):
        carrier = self._carrier()
        baseline = compute_evidence_fingerprint(carrier)
        carrier["supporting_child_observation_refs"] = list(reversed(carrier["supporting_child_observation_refs"]))
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_c_provider_id_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["provider_id"] = "SYNTHETIC_PROVIDER_OTHER"
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_d_instrument_id_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["instrument_id"] = "SYNTHETIC:OTHER"
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_e_parent_observation_ref_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["parent_observation_ref"] += ":other"
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_f_parent_high_low_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["parent_high"] = "111"
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_g_derived_result_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["derived_result"] = "LOW_BEFORE_HIGH"
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_h_provenance_receipt_mutation_changes_evidence_fingerprint(self):
        carrier = self._carrier(); baseline = compute_evidence_fingerprint(carrier)
        carrier["provenance"]["child_semantic_receipt_sha256"] = "9" * 64
        self.assertNotEqual(baseline, compute_evidence_fingerprint(carrier))

    def test_i_event_effective_at_changes_only_carrier_fingerprint(self):
        carrier = self._carrier(); evidence = compute_evidence_fingerprint(carrier); carrier_fp = compute_carrier_fingerprint(carrier)
        carrier["event_effective_at"] = "2026-09-14T01:01:00Z"
        self.assertEqual(evidence, compute_evidence_fingerprint(carrier))
        self.assertNotEqual(carrier_fp, compute_carrier_fingerprint(carrier))

    def test_j_evidence_available_at_changes_only_carrier_fingerprint(self):
        carrier = self._carrier(); evidence = compute_evidence_fingerprint(carrier); carrier_fp = compute_carrier_fingerprint(carrier)
        carrier["evidence_available_at_utc"] = "2026-09-14T01:04:00Z"
        self.assertEqual(evidence, compute_evidence_fingerprint(carrier))
        self.assertNotEqual(carrier_fp, compute_carrier_fingerprint(carrier))

    def test_k_known_at_changes_only_carrier_fingerprint(self):
        carrier = self._carrier(); evidence = compute_evidence_fingerprint(carrier); carrier_fp = compute_carrier_fingerprint(carrier)
        carrier["known_at_utc"] = "2026-09-14T01:06:00Z"
        self.assertEqual(evidence, compute_evidence_fingerprint(carrier))
        self.assertNotEqual(carrier_fp, compute_carrier_fingerprint(carrier))

    def test_l_query_cutoff_is_eligibility_only_and_not_fingerprint_identity(self):
        carrier = self._carrier()
        evidence = compute_evidence_fingerprint(carrier); carrier_fp = compute_carrier_fingerprint(carrier)
        early = validate_carrier_fingerprints(carrier, "2026-09-14T01:04:59Z")
        late = validate_carrier_fingerprints(carrier, "2026-09-14T01:05:00Z")
        self.assertEqual("PIT_INELIGIBLE", early["status"])
        self.assertEqual("VALID", late["status"])
        self.assertEqual(evidence, compute_evidence_fingerprint(carrier))
        self.assertEqual(carrier_fp, compute_carrier_fingerprint(carrier))

    def test_m_wrong_caller_evidence_fingerprint_detected(self):
        carrier = self._carrier(); carrier["evidence_fingerprint"] = "sha256:" + "0" * 64
        result = validate_carrier_fingerprints(carrier)
        self.assertEqual(("INVALID", "EVIDENCE_FINGERPRINT_MISMATCH"), (result["status"], result["reason_code"]))

    def test_n_wrong_caller_carrier_fingerprint_detected(self):
        carrier = self._carrier(); carrier["carrier_fingerprint"] = "sha256:" + "0" * 64
        result = validate_carrier_fingerprints(carrier)
        self.assertEqual(("INVALID", "CARRIER_FINGERPRINT_MISMATCH"), (result["status"], result["reason_code"]))

    def test_o_nan_and_infinity_canonical_payload_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(FingerprintCanonicalizationError) as ctx:
                canonical_json_bytes({"value": value})
            self.assertEqual("INVALID_CANONICAL_PAYLOAD", ctx.exception.reason_code)

    def test_p_flat_result_on_non_flat_parent_rejected(self):
        carrier = self._carrier("FLAT_ORDER_NOT_MATERIALLY_DISTINCT")
        carrier["parent_low"] = "99"
        with self.assertRaises(FingerprintCanonicalizationError) as ctx:
            compute_evidence_fingerprint(carrier)
        self.assertEqual("FLAT_RESULT_INVALID_FOR_NON_FLAT_PARENT", ctx.exception.reason_code)

    def test_q_flat_exact_carrier_is_deterministic(self):
        carrier = self._carrier("FLAT_ORDER_NOT_MATERIALLY_DISTINCT")
        first = (build_evidence_fingerprint_payload(carrier), compute_evidence_fingerprint(carrier), compute_carrier_fingerprint(carrier))
        second = (build_evidence_fingerprint_payload(copy.deepcopy(carrier)), compute_evidence_fingerprint(copy.deepcopy(carrier)), compute_carrier_fingerprint(copy.deepcopy(carrier)))
        self.assertEqual(first, second)
        self.assertEqual({}, first[0]["child_or_event_evidence_bindings"])
        self.assertEqual(4, len(first[0]["provenance_receipt_identity"]))

    def test_r_event_level_profile_without_authority_fails_closed(self):
        carrier = self._carrier()
        carrier["source_event_refs"] = ["event:1", "event:2"]
        carrier["event_ordering_rule"] = "SOURCE_SEQUENCE"
        result = validate_carrier_fingerprints(carrier)
        self.assertEqual("INVALID", result["status"])
        self.assertEqual("UNSUPPORTED_PROOF_PROFILE", result["reason_code"])
        self.assertEqual("EVENT_LEVEL_FINGERPRINT_PROFILE_NOT_AUTHORIZED", result["detail"])

    def test_s_transport_and_local_metadata_cannot_affect_preimages(self):
        carrier = self._carrier(); evidence = compute_evidence_fingerprint(carrier); carrier_fp = compute_carrier_fingerprint(carrier)
        carrier.update({
            "local_path": "/tmp/a", "hostname": "host-a", "github_run_id": "123", "issue_number": "77",
            "transport_url": "https://example.invalid", "caller_list_position": 9, "local_ingestion_arrival_order": 42,
        })
        self.assertEqual(evidence, compute_evidence_fingerprint(carrier))
        self.assertEqual(carrier_fp, compute_carrier_fingerprint(carrier))


class ExtremaOrderFingerprintAuthorityTests(unittest.TestCase):
    def test_parent_contract_bytes_and_git_blob_remain_immutable(self):
        data = PARENT_PATH.read_bytes()
        self.assertEqual(PARENT_SHA256, hashlib.sha256(data).hexdigest())
        self.assertEqual(PARENT_BLOB, git_blob_sha1(data))

    def test_companion_identity_and_runtime_boundaries(self):
        companion = read_json(COMPANION_PATH)
        self.assertEqual(COMPANION_CONTRACT_ID, companion["contract_id"])
        self.assertFalse(companion["runtime_active"])
        self.assertFalse(companion["provider_activation_changed"])
        self.assertFalse(companion["storage_authority_changed"])
        self.assertFalse(companion["authority"]["wave_specific_semantics"])
        self.assertTrue(companion["boundaries"]["machine_companion_contract_is_semantic_authority"])
        self.assertFalse(companion["boundaries"]["python_helper_is_semantic_authority"])

    def test_bridge_discovery_preserves_parent_and_adds_companion(self):
        bridge = read_json(BRIDGE_PATH)
        ptr = bridge["semantic_contracts"]["intra_observation_extrema_order_evidence"]
        self.assertEqual("ETH-MARKET-DATA-INTRA-OBSERVATION-EXTREMA-ORDER-EVIDENCE-V1", ptr["contract_id"])
        self.assertEqual("contracts/intra-observation-extrema-order-evidence-v1.json", ptr["path"])
        self.assertFalse(ptr["runtime_active"])
        self.assertEqual(COMPANION_CONTRACT_ID, ptr["fingerprint_canonicalization_contract_id"])
        self.assertEqual("contracts/intra-observation-extrema-order-evidence-fingerprint-canonicalization-v1.json", ptr["fingerprint_canonicalization_path"])
        self.assertEqual("tools/intra_observation_extrema_order_evidence.py:validate_carrier_fingerprints", ptr["fingerprint_validator_entrypoint"])
        self.assertEqual("ACCEPTED_EXACT_FINGERPRINT_PREIMAGE_AND_VALIDATION_COMPANION_NOT_RUNTIME_ACTIVE", ptr["fingerprint_canonicalization_status"])

    def test_strict_json_parser_rejects_duplicate_keys_and_nonfinite_constants(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(FingerprintCanonicalizationError) as ctx:
                strict_json_loads(text)
            self.assertEqual("INVALID_CANONICAL_PAYLOAD", ctx.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
