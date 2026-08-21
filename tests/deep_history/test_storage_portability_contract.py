from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class StoragePortabilityContractTests(unittest.TestCase):
    def test_bridge_contract_separates_semantic_authority_and_backend(self):
        bridge = load_json("bridge-contract.json")
        portability = bridge["storage_portability"]
        self.assertEqual(portability["contract_id"], "ETH-MARKET-DATA-STORAGE-PORTABILITY-V2")
        self.assertEqual(portability["market_data_semantic_authority"], "ETH_MACRO_DATA_BRIDGE")
        self.assertEqual(portability["current_physical_backend_profile"], "GITHUB_FIRST_V1")
        self.assertFalse(portability["physical_backend_is_semantic_contract"])
        self.assertFalse(portability["execution_plane_is_semantic_authority"])
        self.assertFalse(portability["vps_is_market_data_authority"])
        self.assertFalse(portability["storage_migration_changes_semantic_interface"])
        self.assertFalse(portability["storage_migration_changes_observation_id"])
        self.assertFalse(portability["storage_migration_changes_series_id"])
        self.assertEqual(portability["d8_runtime_state_backend"], "SQLITE_WAL")
        self.assertEqual(portability["d8_runtime_state_role"], "OPERATIONAL_RUNTIME_STATE")
        self.assertFalse(portability["d8_runtime_state_is_history_authority"])
        self.assertFalse(portability["local_filesystem_write_sufficient_for_production_ack"])
        self.assertTrue(portability["canonical_publication_ack_required"])
        self.assertEqual(portability["canonical_publication_port_status"], "SOURCE_IMPLEMENTED_QUALIFIED_MERGED")
        self.assertEqual(portability["next_source_task"], "NONE_SOURCE_IMPLEMENTATION_COMPLETE")
        self.assertEqual(
            portability["d8_origin_canonical_publication"],
            "SOURCE_IMPLEMENTED_QUALIFIED_MERGED_PHYSICAL_RUNTIME_QUALIFIED",
        )
        self.assertEqual(
            portability["d8_origin_resolver_authority"],
            "RECONCILED_CONTRACT_PHYSICALLY_QUALIFIED_NOT_ACTIVE",
        )
        self.assertEqual(portability["d8_origin_canonical_warm_representation"], "IMPLEMENTED_QUALIFIED")
        self.assertEqual(portability["github_publication_concurrency_contract"], "IMPLEMENTED_QUALIFIED_CAS")
        self.assertEqual(portability["high_cardinality_warm_backend"], "BLOCKED_VERSIONED_DECISION")
        self.assertFalse(portability["postgres_implemented"])
        self.assertTrue(portability["postgres_migration_path_defined"])
        self.assertEqual(portability["existing_server_postgres_reuse_decision"], "NOT_MADE")
        self.assertFalse(portability["git_commit_per_observation"])
        self.assertFalse(portability["second_resolver"])
        self.assertFalse(portability["second_reader"])
        self.assertFalse(portability["second_history_authority"])
        self.assertFalse(portability["permanent_vps_d9_warm_required"])
        self.assertFalse(portability["resolution_plan_v2_active"])
        self.assertTrue(portability["d6_resolution_plan_v1_active"])

    def test_d9_status_axes_are_not_collapsed(self):
        bridge = load_json("bridge-contract.json")
        d9 = bridge["d9_candidate"]
        forwarding = bridge["d8_d9_forwarding_source"]
        self.assertEqual(d9["target_contract_status"], "ACCEPTED")
        self.assertEqual(
            d9["source_implementation_status"],
            "COMPLETE_WITH_PUBLICATION_PORT_IMPLEMENTED_QUALIFIED_MERGED",
        )
        self.assertEqual(d9["canonical_d8_publication_implementation_status"], "SOURCE_IMPLEMENTED_QUALIFIED_MERGED")
        self.assertEqual(d9["physical_canonical_d8_publication_status"], "QUALIFIED")
        self.assertEqual(d9["authority_activation_status"], "NOT_ACTIVE")
        self.assertTrue(forwarding["canonical_publication_qualified"])
        self.assertTrue(forwarding["physical_vps_d8_to_d9_qualified"])
        self.assertTrue(forwarding["cross_tier_semantic_read_qualified"])
        self.assertFalse(forwarding["production_warm_forwarder_deployed"])
        self.assertFalse(forwarding["d8_active"])
        self.assertFalse(forwarding["d9_active"])
        self.assertFalse(forwarding["production_cutover"])
        self.assertFalse(forwarding["provider_authority_transition"])
        self.assertTrue(forwarding["legacy_github_production_acquisition_active"])
        self.assertTrue(d9["activation_gate"]["active_d6_route_must_remain_unchanged"])

    def test_forwarding_contract_requires_canonical_publication_ack(self):
        contract = load_json("contracts/d8-d9-forwarding-v1.json")
        self.assertEqual(contract["contract_id"], "ETH-MARKET-DATA-STORAGE-PORTABILITY-V2")
        self.assertEqual(
            contract["local_forwarder_primitive"]["classification"],
            "CURRENT_PHYSICAL_PRIMITIVE_NOT_PRODUCTION_PUBLICATION_AUTHORITY",
        )
        self.assertFalse(contract["local_forwarder_primitive"]["local_filesystem_write_sufficient_for_production_ack"])
        self.assertFalse(contract["publication_batch"]["partial_ack"])
        self.assertFalse(contract["publication_batch"]["git_commit_per_observation"])
        self.assertEqual(contract["canonical_publication_ack"]["name"], "CANONICAL_PUBLICATION_ACK")
        self.assertTrue(contract["canonical_publication_ack"]["required_before_pending_to_forwarded"])
        self.assertIn("control_plane_visibility_evidence", contract["canonical_publication_ack"]["ack_binding"])
        self.assertEqual(contract["history_publication_port"]["status"], "SOURCE_IMPLEMENTED_QUALIFIED_MERGED")
        self.assertEqual(contract["history_publication_port"]["next_source_task"], "NONE_SOURCE_IMPLEMENTATION_COMPLETE")
        self.assertFalse(contract["history_publication_port"]["generic_plugin_framework"])
        self.assertTrue(contract["authority"]["canonical_publication_qualified"])
        self.assertTrue(contract["authority"]["physical_vps_d8_to_d9_qualified"])
        self.assertTrue(contract["authority"]["cross_tier_semantic_read_qualified"])
        self.assertFalse(contract["authority"]["d8_active"])
        self.assertFalse(contract["authority"]["d9_active"])
        self.assertFalse(contract["authority"]["production_cutover"])
        self.assertFalse(contract["authority"]["provider_authority_transition"])
        self.assertFalse(contract["future_physical_acceptance"]["local_warm_root_physical_test_next"])
        self.assertTrue(contract["future_physical_acceptance"]["preserve_real_d8_spool_for_later"])
        self.assertEqual(
            contract["future_physical_acceptance"]["status"],
            "A1_A2_PHYSICAL_QUALIFICATION_COMPLETE",
        )
        self.assertEqual(
            contract["future_physical_acceptance"]["current_status_contract"],
            "contracts/d8-a2-physical-qualification-status-v1.json",
        )
        self.assertTrue(contract["future_physical_acceptance"]["physical_publication_port_e2e_qualified"])
        self.assertEqual(
            contract["future_physical_acceptance"]["prerequisite_source_task"],
            "COMPLETED_ETH-D8-D9-CANONICAL-PUBLICATION-PORT-V1",
        )
        self.assertEqual(
            contract["future_physical_acceptance"]["next_stage"],
            "FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION",
        )

    def test_d8_origin_resolver_gap_has_control_plane_transition_not_filesystem_scan(self):
        contract = load_json("contracts/d8-d9-forwarding-v1.json")
        visibility = contract["resolver_visibility"]
        self.assertEqual(
            visibility["confirmed_gap"],
            "LOCAL_D8_ORIGIN_PARTITIONS_ARE_NOT_AUTOMATIC_CANONICAL_RESOLVER_AUTHORITY",
        )
        self.assertEqual(visibility["local_materialization_source"], "IMPLEMENTED")
        self.assertEqual(visibility["canonical_publication"], "SOURCE_IMPLEMENTED_QUALIFIED_MERGED")
        self.assertEqual(
            visibility["canonical_resolver_authority"],
            "RECONCILED_CONTRACT_PHYSICALLY_QUALIFIED_NOT_ACTIVE",
        )
        self.assertIn("existing capability/resolver visibility", visibility["required_transition"])
        self.assertFalse(visibility["resolver_scans_arbitrary_vps_filesystem"])
        self.assertFalse(visibility["manual_d8_origin_path_stitching"])
        self.assertFalse(visibility["second_resolver"])
        self.assertFalse(visibility["second_reader"])
        self.assertFalse(visibility["agent_visible_filesystem_path"])
        self.assertEqual(contract["canonical_warm_representation_gate"]["status"], "IMPLEMENTED_QUALIFIED")
        self.assertEqual(contract["github_publication_concurrency_gate"]["status"], "IMPLEMENTED_QUALIFIED_CAS")

    def test_resolution_plan_v2_defines_storage_neutral_vocabulary_with_compatibility_alias(self):
        schema = load_json("schema/market-data-resolution-plan-v2.schema.json")
        segment = schema["$defs"]["segment"]
        properties = segment["properties"]
        for field in ("residence_role", "adapter_profile", "resource_ref", "integrity_evidence"):
            self.assertIn(field, properties)
        self.assertTrue(properties["storage"]["deprecated"])
        self.assertIn("compatibility alias", properties["storage"]["description"].lower())
        self.assertEqual(schema["$defs"]["residenceRole"]["enum"], ["HOT", "WARM", "COLD"])

    def test_publication_batch_schema_binds_exact_membership_and_integrity(self):
        schema = load_json("schema/history-publication-batch-v1.schema.json")
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "market-data-history-publication-batch/1.0.0",
        )
        required = set(schema["required"])
        self.assertTrue(
            {
                "batch_id",
                "target_residence_role",
                "member_count",
                "member_observation_ids",
                "members",
                "membership_sha256",
                "payload_sha256",
            }.issubset(required)
        )
        self.assertEqual(schema["properties"]["target_residence_role"]["const"], "WARM")
        self.assertTrue(schema["properties"]["member_observation_ids"]["uniqueItems"])
        self.assertNotIn("backend_profile", schema["properties"])
        self.assertNotIn("publication_attempt_id", schema["properties"])
        bridge = load_json("bridge-contract.json")
        portability = bridge["storage_portability"]
        self.assertEqual(portability["resolution_plan_v2_runtime_migration"], "PENDING_PRE_ACTIVATION")
        self.assertFalse(portability["resolution_plan_v2_active"])
        self.assertTrue(portability["d6_resolution_plan_v1_active"])
        self.assertEqual(portability["capability_declaration_authority"], "contracts/d8-runtime-candidate.json#due_policy.capabilities")
        self.assertTrue(portability["capability_routing_single_source"])
        member_required = set(schema["$defs"]["member"]["required"])
        self.assertTrue(
            {
                "position",
                "observation_id",
                "series_id",
                "provider",
                "payload_fingerprint",
                "payload_sha256",
                "known_at",
                "finality",
            }.issubset(member_required)
        )


if __name__ == "__main__":
    unittest.main()
