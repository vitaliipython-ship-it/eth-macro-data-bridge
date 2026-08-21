from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class D8ShadowPostResetStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = read("contracts/d8-shadow-post-reset-status-v1.json")
        self.forwarding = read("contracts/d8-d9-forwarding-v1.json")

    def test_snapshot_provenance_and_live_readback_boundary(self) -> None:
        self.assertEqual(
            self.status["status_semantics"],
            "RECONCILED_PHYSICAL_SNAPSHOT_NOT_LIVE_PROBE",
        )
        self.assertEqual(
            self.status["snapshot_time_semantics"],
            "EXTERNAL_EXECUTION_TIMESTAMP_NOT_REPOSITORY_AUTHORITY",
        )
        self.assertFalse(self.status["live_runtime_status_continuously_verified"])
        self.assertTrue(self.status["live_server_readback_required_before_physical_mutation"])
        self.assertTrue(self.status["live_server_readback_required_before_physical_qualification"])

        model = self.status["authority_model"]
        self.assertEqual(
            model["data_bridge_repository_authority"],
            "PROGRAM_CONTRACT_AND_RECONCILED_STATUS",
        )
        self.assertEqual(model["server_execution_authority"], "LIVE_PHYSICAL_STATE_READBACK")
        self.assertFalse(model["reconciled_status_snapshot_is_live_probe"])
        self.assertFalse(
            model["repository_status_can_authorize_physical_mutation_without_live_readback"]
        )
        self.assertFalse(model["live_vps_path_or_filesystem_is_semantic_market_data_authority"])
        self.assertFalse(model["reconciled_status_snapshot_is_semantic_market_data_authority"])

        provenance = self.status["snapshot_external_evidence"]
        self.assertEqual(
            provenance["server_ssot_closure_head"],
            "81522acededc94d52b4c73b8d6c254bd012a3034",
        )
        self.assertEqual(
            provenance["server_ssot_closure_tree"],
            "19f6edfcd7bf745ed099d1509782cf87ea857b29",
        )
        self.assertEqual(
            provenance["execution_evidence_sha256"],
            "f4ab6d04d59e41db05cef476502b9be405d9b36d89654f44c439bc74646b60e9",
        )
        self.assertEqual(
            provenance["forensic_db_sha256"],
            "8be1971e2a5f20ac2c00f57e3a1fc18cc973acca85f8cd06dfa14623351a9769",
        )
        self.assertEqual(
            provenance["pending_state_fingerprint_sha256"],
            "d80197463db61ea2b3acce11094a4a3b7b0556a029711fb65a3994cbd1958177",
        )
        self.assertEqual(
            provenance["evidence_role"],
            "PROVENANCE_BINDING_NOT_SEMANTIC_MARKET_DATA_AUTHORITY",
        )
        self.assertFalse(provenance["semantic_market_data_authority"])

    def test_accepted_post_reset_state_is_exact_and_non_authoritative(self) -> None:
        self.assertEqual(self.status["schema_version"], "eth-macro-d8-shadow-post-reset-status/1.0.0")
        self.assertEqual(
            self.status["status"],
            "POST_RESET_CLEAN_VPS_SHADOW_READY_FOR_FRESH_CHECKPOINT_V2_COLLECTION",
        )
        evidence = self.status["accepted_external_physical_evidence"]
        self.assertEqual(
            evidence["dynamic_runtime_and_count_fields_semantics"],
            "RECONCILED_SNAPSHOT_VALUES_NOT_CONTINUOUS_LIVE_STATE",
        )
        self.assertEqual(evidence["old_pending_total"], 261)
        self.assertEqual(evidence["old_checkpoint_v2_eligible"], 62)
        self.assertEqual(evidence["old_legacy_pre_checkpoint_v2"], 199)
        self.assertTrue(evidence["old_pending_forensically_preserved"])
        self.assertFalse(evidence["old_pending_restore_authorized"])
        self.assertEqual(evidence["controlled_shadow_reset"], "PASS")
        self.assertEqual(evidence["current_d8_source"], "9336f75b4e6c49dcbc82252bc37a4bc45075f04f")
        self.assertEqual(evidence["current_d8_profile"], "VPS_SHADOW")
        self.assertEqual(evidence["current_d8_runtime"], "RUNNING_HEALTHY_NON_AUTHORITATIVE")
        self.assertEqual(evidence["current_state_schema_version"], 2)
        self.assertEqual(evidence["current_spool_total"], 0)
        self.assertEqual(evidence["current_pending_total"], 0)
        self.assertEqual(evidence["current_forwarded_total"], 0)
        self.assertEqual(evidence["normal_provider_acquisition_after_reset"], "NOT_RUN")
        self.assertFalse(evidence["physical_publication_port_e2e_qualified"])

    def test_program_frontier_requires_fresh_checkpoint_v2_before_publication(self) -> None:
        actual = [(row["stage"], row["status"]) for row in self.status["program_frontier"]]
        self.assertEqual(
            actual,
            [
                ("OLD_PRE_PRODUCTION_SHADOW", "HISTORICAL"),
                ("FORENSIC_PRESERVATION", "COMPLETE"),
                ("CONTROLLED_SHADOW_RESET", "COMPLETE"),
                ("CURRENT_D8_DEPLOYMENT", "COMPLETE"),
                ("CLEAN_VPS_SHADOW", "COMPLETE"),
                ("NEW_REAL_CHECKPOINT_V2_DATA", "NEXT"),
                ("PHYSICAL_PUBLICATION_PORT", "PENDING"),
                ("ACTIVATION", "NOT_AUTHORIZED"),
            ],
        )
        step = self.status["next_physical_step"]
        self.assertEqual(
            step["route"],
            [
                "CURRENT_D8_VPS_SHADOW",
                "EXPLICIT_REAL_PROVIDER_COLLECTION",
                "NEW_CURRENT_GENERATION_CHECKPOINT_V2_EVIDENCE",
                "NON_ZERO_ELIGIBLE_PENDING",
                "STOP",
            ],
        )
        self.assertFalse(step["pre_reset_live_spool_is_qualification_input"])
        self.assertFalse(step["old_forensic_pending_restore_authorized"])
        self.assertFalse(step["provider_acquisition_performed_by_reconciliation_task"])

    def test_authority_and_credential_boundaries_remain_closed(self) -> None:
        authority = self.status["authority"]
        self.assertFalse(authority["d8_active"])
        self.assertFalse(authority["d9_active"])
        self.assertEqual(authority["active_default_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertFalse(authority["vps_is_market_data_authority"])
        self.assertTrue(authority["legacy_github_production_acquisition_active"])
        self.assertFalse(authority["production_warm_forwarder_deployed"])
        self.assertFalse(authority["physical_vps_d8_to_d9_qualified"])
        self.assertFalse(authority["cross_tier_semantic_read_qualified"])
        self.assertFalse(authority["production_cutover"])
        self.assertFalse(authority["provider_authority_transition"])
        self.assertFalse(authority["postgres_implemented"])
        self.assertFalse(authority["public_d8_ingress_required"])

        credentials = self.status["credential_boundary"]
        self.assertEqual(credentials["d8_runtime_authentication"], "D8_RUNTIME_TOKEN")
        self.assertFalse(credentials["github_token_required_inside_d8_runtime"])
        self.assertEqual(
            credentials["publication_credentials_owner"],
            "SEPARATELY_AUTHORIZED_PUBLICATION_EXECUTOR_OR_ADAPTER",
        )
        self.assertFalse(credentials["public_d8_ingress_required"])

    def test_forwarding_acceptance_no_longer_consumes_pre_reset_live_spool_first(self) -> None:
        acceptance = self.forwarding["future_physical_acceptance"]
        self.assertEqual(
            acceptance["current_shadow_status_contract"],
            "contracts/d8-shadow-post-reset-status-v1.json",
        )
        self.assertTrue(acceptance["preserve_real_d8_spool_for_later"])
        self.assertEqual(
            acceptance["preserve_real_d8_spool_for_later_semantics"],
            "PRE_RESET_FORENSIC_EVIDENCE_ONLY_NOT_LIVE_QUALIFICATION_INPUT",
        )
        self.assertFalse(acceptance["pre_reset_live_spool_is_qualification_input"])
        self.assertEqual(acceptance["current_spool_total"], 0)
        self.assertEqual(acceptance["current_pending_total"], 0)
        self.assertEqual(acceptance["current_forwarded_total"], 0)
        self.assertTrue(acceptance["new_real_checkpoint_v2_data_required_before_publication_test"])
        self.assertEqual(
            acceptance["later_test_a"],
            "FRESH_REAL_PROVIDER_COLLECTION_TO_NONZERO_ELIGIBLE_CHECKPOINT_V2_PENDING_THEN_STOP",
        )
        self.assertEqual(
            acceptance["later_test_b"],
            "SEPARATELY_AUTHORIZED_FRESH_PENDING_TO_CANONICAL_BACKEND_REMOTE_VERIFICATION_RESOLVER_VISIBILITY_ACK_FORWARDED",
        )
        self.assertTrue(acceptance["publication_test_requires_separate_owner_authorization"])
        self.assertFalse(acceptance["github_token_required_inside_d8_runtime"])


if __name__ == "__main__":
    unittest.main()
