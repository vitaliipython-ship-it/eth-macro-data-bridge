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
        self.current = read("contracts/d8-a2-physical-qualification-status-v1.json")
        self.forwarding = read("contracts/d8-d9-forwarding-v1.json")
        self.bridge = read("bridge-contract.json")
        self.admission = read("contracts/d8-publication-qualification-admission-v1.json")
        self.sealing = read("contracts/d9-sealing-candidate.json")

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

    def test_accepted_post_reset_state_is_exact_historical_predecessor(self) -> None:
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

    def test_historical_program_frontier_remains_byte_truthful(self) -> None:
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

    def test_current_a2_successor_binds_exact_accepted_evidence(self) -> None:
        self.assertEqual(
            self.current["schema_version"],
            "eth-macro-d8-a2-physical-qualification-status/1.0.0",
        )
        self.assertEqual(
            self.current["status"],
            "A2_PHYSICAL_PUBLICATION_QUALIFICATION_ACCEPTED_NOT_ACTIVE",
        )
        self.assertEqual(
            self.current["status_semantics"],
            "RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE",
        )
        self.assertEqual(
            self.current["predecessor_status_contract"],
            "contracts/d8-shadow-post-reset-status-v1.json",
        )
        self.assertFalse(self.current["live_runtime_status_continuously_verified"])
        self.assertTrue(self.current["live_server_readback_required_before_physical_mutation"])
        self.assertTrue(self.current["live_server_readback_required_before_physical_qualification"])

        evidence = self.current["accepted_external_physical_evidence"]
        self.assertEqual(
            evidence["dynamic_runtime_and_count_fields_semantics"],
            "RECONCILED_SNAPSHOT_VALUES_NOT_CONTINUOUS_LIVE_STATE",
        )
        self.assertEqual(evidence["a1_fresh_checkpoint_v2_generation"], "PASS")
        self.assertEqual(evidence["a2_canonical_publication"], "PASS")
        self.assertEqual(evidence["a2_canonical_ack"], "PASS")
        self.assertEqual(evidence["a2_pending_to_forwarded"], "PASS")
        self.assertEqual(evidence["a2_idempotent_replay"], "PASS")
        self.assertEqual(evidence["independent_server_evidence_sha_recompute"], "PASS")
        self.assertTrue(evidence["physical_publication_port_e2e_qualified"])
        self.assertEqual(evidence["current_sqlite_integrity"], "ok")
        self.assertEqual(
            (evidence["current_spool_total"], evidence["current_pending_total"], evidence["current_forwarded_total"]),
            (20, 0, 20),
        )

        anchors = self.current["evidence_anchors"]
        self.assertEqual(
            anchors["execution_evidence_sha256"],
            "4ebc80433c1f09992304c3f9db9b9a063747d0999b35ec2de6c8615aa7068ebe",
        )
        self.assertEqual(
            anchors["pre_db_backup_sha256"],
            "1a7e678626fb40bea96ac98d9e16b4f480c7944a375ba15c7bf5be1a609845de",
        )
        self.assertEqual(
            anchors["post_db_backup_sha256"],
            "8169e5d16b61f48557fcd28c4328de1bc921c950983ffdeb0947e816a31981c3",
        )
        self.assertEqual(anchors["replay_post_db_backup_sha256"], anchors["post_db_backup_sha256"])
        self.assertFalse(anchors["semantic_market_data_authority"])

        a1 = self.current["a1"]
        self.assertEqual(a1["status"], "QUALIFIED_PASS")
        self.assertEqual(a1["cycle_id"], "d8c-397e11d26b0f55ba891ef16bf2a19447")
        self.assertEqual(a1["canonical_slot"], "2026-08-21T11:15:00.000Z")
        self.assertEqual(a1["observation_count"], 20)
        self.assertEqual(
            a1["pending_membership_sha256"],
            "f29cbc1fe566983ceda79d70cff20e3284b4ba71d9ba6c3f03c48215a02b0fbc",
        )
        self.assertEqual(
            a1["payload_fingerprint_set_sha256"],
            "0c308680084a9d79ff1a35452d4397b38b58202a32333531168c5fb0027bdd5b",
        )
        self.assertEqual(
            a1["pending_state_fingerprint_sha256"],
            "bcab6548dbb3dc5d7eef631efd5d4acdde6371bc8501727e8c831b05980cfaeb",
        )
        self.assertEqual(
            a1["inventory_sha256"],
            "626534f028fa9d8408d72f47b269652b7d403b1c51eb468d7447bc3ac2c2480f",
        )

        a2 = self.current["a2"]
        self.assertEqual(a2["status"], "QUALIFIED_PASS")
        self.assertEqual(
            a2["batch_id"],
            "pub-0e3a0d13c5ea7d46c50a13285a1c0372190123be620b92a7a2a062bf70ca5b42",
        )
        self.assertEqual(a2["data_commit"], "789d24c26af5cfd36b3be62a89093fd8becbc684")
        self.assertEqual(a2["control_commit"], "f05a33df6bc661ed14941cb47487439f28f92d58")
        self.assertEqual(a2["member_count"], 20)
        self.assertEqual(
            a2["membership_sha256"],
            "2f97f71630e8f42704e563c872356ef4212ae7a324286303506e0677ac796a3d",
        )
        self.assertEqual(
            a2["payload_sha256"],
            "a2856c0ccc0610d87f796949c8dfa4046286e93cc164f95588438e9a402054b5",
        )
        self.assertEqual(a2["control_blob"], "2cf28f2b4594eed0150cc79c31088ba2341e94d7")
        self.assertEqual(a2["resource_blob"], "80e54eaec28c78019839d67167917d520c68abc9")
        self.assertEqual(a2["remote_byte_preservation"], "PASS")
        self.assertFalse(a2["second_logical_batch"])
        self.assertEqual(a2["canonical_ack"], "PASS")
        self.assertFalse(a2["partial_ack"])
        self.assertEqual(a2["accepted_observation_count"], 20)
        self.assertEqual(a2["accepted_observation_id_set_match"], "PASS")

        transition = self.current["state_transition"]
        self.assertEqual(transition["pre"], {"spool": 20, "pending": 20, "forwarded": 0})
        self.assertEqual(transition["post"], {"spool": 20, "pending": 0, "forwarded": 20})
        self.assertEqual(transition["pre_pending_id_set_equals_post_forwarded_id_set"], "PASS")
        self.assertEqual(transition["payload_fingerprint_set_unchanged"], "PASS")
        self.assertEqual(transition["observation_content_unchanged"], "PASS")
        self.assertEqual(transition["cycle_id_unchanged"], "PASS")
        self.assertEqual(transition["checkpoint_binding_unchanged"], "PASS")

        replay = self.current["idempotency"]
        self.assertTrue(replay["already_present_retry"])
        self.assertFalse(replay["new_logical_batch_created"])
        self.assertFalse(replay["new_data_resource_created"])
        self.assertFalse(replay["new_data_commit_created"])
        self.assertFalse(replay["new_control_entry_created"])
        self.assertFalse(replay["a2_resource_rewritten"])
        self.assertFalse(replay["a2_control_rewritten"])
        self.assertTrue(replay["replay_executed"])
        self.assertEqual(replay["replay_result"], "IDEMPOTENT_NOOP")
        self.assertEqual(replay["replay_provider_reacquisition"], 0)
        self.assertEqual(replay["replay_github_mutation"], "NO_BY_CANONICAL_NOOP_ROUTE")
        self.assertFalse(replay["replay_state_mutation"])

    def test_current_authority_boundaries_preserve_inactive_default_route(self) -> None:
        authority = self.current["authority"]
        self.assertFalse(authority["d8_active"])
        self.assertFalse(authority["d9_active"])
        self.assertEqual(authority["active_default_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertEqual(authority["active_resolution_plan"], "market-data-resolution-plan/1.0.0")
        self.assertFalse(authority["d9_v2_active"])
        self.assertFalse(authority["vps_is_market_data_authority"])
        self.assertFalse(authority["binance_usdm_provider_authority_active"])
        self.assertEqual(authority["binance_usdm_normal_mode_status"], "DISABLED_BY_POLICY")
        self.assertTrue(authority["legacy_github_production_acquisition_active"])
        self.assertFalse(authority["production_warm_forwarder_deployed"])
        self.assertTrue(authority["physical_vps_d8_to_d9_qualified"])
        self.assertTrue(authority["canonical_publication_qualified"])
        self.assertTrue(authority["cross_tier_semantic_read_qualified"])
        self.assertFalse(authority["production_cutover"])
        self.assertFalse(authority["provider_authority_transition"])

        disabled = self.bridge["disabled_providers"]["binance-usdm"]
        self.assertEqual(disabled["status"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["current_collection"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["network_calls"], 0)
        self.assertEqual(disabled["vps_runtime_status"], "NOT_ACTIVE")

        self.assertEqual(self.admission["authority_role"], "QUALIFICATION_ADMISSION_ONLY_NOT_PROVIDER_POLICY")
        admission = self.admission["admissions"][0]
        self.assertTrue(admission["does_not_activate_provider"])
        self.assertTrue(admission["does_not_enable_github_acquisition"])
        self.assertTrue(admission["provider_authority_transition_required_later"])
        self.assertEqual(admission["required_bridge_provider_status"], "DISABLED_BY_POLICY")
        self.assertEqual(admission["required_bridge_network_calls"], 0)

    def test_forwarding_contract_reconciles_completed_a1_a2_without_activation(self) -> None:
        self.assertEqual(
            self.forwarding["status"],
            "SOURCE_IMPLEMENTED_CANONICAL_PUBLICATION_MERGED_PHYSICAL_QUALIFICATION_PASS",
        )
        authority = self.forwarding["authority"]
        self.assertTrue(authority["canonical_publication_qualified"])
        self.assertTrue(authority["physical_vps_d8_to_d9_qualified"])
        self.assertTrue(authority["cross_tier_semantic_read_qualified"])
        self.assertFalse(authority["d8_active"])
        self.assertFalse(authority["d9_active"])
        self.assertFalse(authority["vps_is_market_data_authority"])
        self.assertFalse(authority["production_cutover"])
        self.assertFalse(authority["provider_authority_transition"])
        self.assertTrue(authority["legacy_github_production_acquisition_active"])
        self.assertFalse(authority["production_warm_forwarder_deployed"])

        self.assertEqual(
            self.forwarding["resolver_visibility"]["canonical_resolver_authority"],
            "RECONCILED_CONTRACT_PHYSICALLY_QUALIFIED_NOT_ACTIVE",
        )
        self.assertTrue(self.forwarding["hot_internal_source"]["cross_tier_semantic_read_qualified"])

        acceptance = self.forwarding["future_physical_acceptance"]
        self.assertEqual(acceptance["status"], "A1_A2_PHYSICAL_QUALIFICATION_COMPLETE")
        self.assertEqual(
            acceptance["current_status_contract"],
            "contracts/d8-a2-physical-qualification-status-v1.json",
        )
        self.assertEqual(
            acceptance["current_shadow_status_contract"],
            "contracts/d8-shadow-post-reset-status-v1.json",
        )
        self.assertEqual(acceptance["current_shadow_status_contract_role"], "HISTORICAL_PREDECESSOR_SNAPSHOT")
        self.assertTrue(acceptance["pre_reset_pending_forensic_preserved"])
        self.assertFalse(acceptance["pre_reset_pending_restore_authorized"])
        self.assertFalse(acceptance["pre_reset_live_spool_is_qualification_input"])
        self.assertEqual(
            acceptance["dynamic_runtime_and_count_fields_semantics"],
            "RECONCILED_SNAPSHOT_VALUES_NOT_CONTINUOUS_LIVE_STATE",
        )
        self.assertEqual(
            (acceptance["current_spool_total"], acceptance["current_pending_total"], acceptance["current_forwarded_total"]),
            (20, 0, 20),
        )
        self.assertFalse(acceptance["new_real_checkpoint_v2_data_required_before_publication_test"])
        self.assertEqual(acceptance["a1_fresh_checkpoint_v2_generation"], "PASS")
        self.assertEqual(acceptance["a2_canonical_publication"], "PASS")
        self.assertEqual(acceptance["a2_canonical_ack"], "PASS")
        self.assertEqual(acceptance["a2_pending_to_forwarded"], "PASS")
        self.assertEqual(acceptance["a2_idempotent_replay"], "PASS")
        self.assertTrue(acceptance["physical_publication_port_e2e_qualified"])
        self.assertEqual(
            acceptance["execution_evidence_sha256"],
            "4ebc80433c1f09992304c3f9db9b9a063747d0999b35ec2de6c8615aa7068ebe",
        )
        self.assertEqual(acceptance["next_stage"], "FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION")
        self.assertEqual(
            acceptance["next_physical_qualification"],
            "REAL_D9_COLD_PHYSICAL_QUALIFICATION_AFTER_ELIGIBILITY",
        )
        self.assertFalse(acceptance["github_token_required_inside_d8_runtime"])
        self.assertFalse(acceptance["public_d8_ingress_required"])

    def test_current_frontier_defers_cold_until_eligible_completed_generation(self) -> None:
        actual = [(row["stage"], row["status"]) for row in self.current["program_frontier"]]
        self.assertIn(("NEW_REAL_CHECKPOINT_V2_DATA", "COMPLETE"), actual)
        self.assertIn(("PHYSICAL_PUBLICATION_PORT", "QUALIFIED"), actual)
        self.assertIn(("FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION", "NEXT"), actual)
        self.assertIn(
            ("REAL_D9_COLD_PHYSICAL_QUALIFICATION", "BLOCKED_UNTIL_ELIGIBLE_GENERATION"),
            actual,
        )
        self.assertIn(("ACTIVATION", "NOT_AUTHORIZED"), actual)

        next_stage = self.current["next_stage"]
        self.assertEqual(next_stage["stage"], "FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION")
        self.assertEqual(next_stage["regular_grid_policy"], "COMPLETED_MONTH_ONLY")
        self.assertFalse(next_stage["active_period_sealing"])
        self.assertFalse(next_stage["activation_authorized"])

        self.assertEqual(self.sealing["status"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual(self.sealing["period_policy"]["regular_grid"], "COMPLETED_MONTH_ONLY")
        self.assertFalse(self.sealing["period_policy"]["active_period_sealing"])
        self.assertTrue(self.sealing["activation_gate"]["requires_d9_4_cross_boundary_semantic_read"])
        self.assertTrue(self.sealing["activation_gate"]["legacy_cold_remains_active_until_pass"])


if __name__ == "__main__":
    unittest.main()
