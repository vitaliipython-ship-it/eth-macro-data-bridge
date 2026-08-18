from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D8 = json.loads((ROOT / "contracts/d8-runtime-candidate.json").read_text())
BRIDGE = json.loads((ROOT / "bridge-contract.json").read_text())


class UnifiedConsumerContinuityContractCase(unittest.TestCase):
    def test_cutover_gate_is_required_and_not_qualified(self):
        continuity = D8["consumer_continuity"]
        gate = continuity["production_cutover_gate"]
        self.assertEqual(
            continuity["decision_id"],
            "ETH-UNIFIED-MARKET-DATA-CONSUMER-CONTINUITY-V1",
        )
        self.assertEqual(
            continuity["status"],
            "PENDING_REQUIRED_BEFORE_PRODUCTION_CONSUMER_CUTOVER",
        )
        self.assertTrue(gate["required"])
        self.assertEqual(gate["status"], "NOT_QUALIFIED")
        self.assertEqual(gate["qualification_kind"], "CROSS_TIER_SEMANTIC_READ")

    def test_single_semantic_consumer_family_is_machine_required(self):
        continuity = D8["consumer_continuity"]
        route = continuity["semantic_route"]
        gate = continuity["production_cutover_gate"]
        self.assertEqual(continuity["planes"]["d8"], "NEAR_REAL_TIME_ACQUISITION_PLANE")
        self.assertEqual(continuity["planes"]["d9"], "DURABLE_HISTORY_LIFECYCLE_PLANE")
        self.assertEqual(route["physical_composition"], "AUTOMATIC_RESOLVER_OWNED")
        self.assertEqual(route["active_d6_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertEqual(route["active_d6_current_policy"], "FINALIZED_ONLY")
        self.assertEqual(route["active_d6_provisional_current"], "FAIL_CLOSED")
        for key in (
            "one_semantic_request",
            "one_resolver_family",
            "one_resolution_plan",
            "one_reader_family",
            "one_normalized_result",
            "one_diagnostics_set",
            "one_provenance_receipt",
        ):
            self.assertTrue(gate[key], key)
        for key in (
            "no_manual_stitching",
            "no_second_resolver",
            "no_second_reader_family",
            "no_second_agent_read_api",
            "no_provider_reacquisition_by_reader",
            "no_direct_provider_fallback",
            "no_hidden_gap",
            "no_silent_provider_substitution",
            "no_storage_knowledge_required_by_agent",
            "no_vps_filesystem_knowledge_required_by_agent",
            "fail_closed",
        ):
            self.assertTrue(gate[key], key)

    def test_required_physical_roles_and_integrity_are_explicit(self):
        gate = D8["consumer_continuity"]["production_cutover_gate"]
        self.assertEqual(gate["required_physical_roles"], ["COLD", "WARM", "D8_HOT"])
        self.assertEqual(gate["duplicates_allowed"], 0)
        self.assertEqual(gate["undeclared_gaps_allowed"], 0)
        self.assertEqual(gate["ordering_required"], "PASS")
        self.assertEqual(gate["coverage_required"], "PASS")
        for key in (
            "finality_preserved",
            "known_at_preserved",
            "provenance_preserved",
            "series_identity_preserved",
            "pit_revision_semantics_preserved",
        ):
            self.assertTrue(gate[key], key)
        self.assertEqual(
            set(gate["missing_hot_replacement_forbidden"]),
            {
                "PREVIOUS_WARM_VALUE",
                "SYNTHETIC_CANDLE",
                "PROVIDER_API_CALL",
                "EXTERNAL_QUOTE",
                "ANOTHER_PROVIDER",
            },
        )

    def test_checkpoint_v2_and_global_vs_cycle_identity_are_preserved(self):
        self.assertEqual(D8["state"]["state_schema_version"], 2)
        checkpoint = D8["state"]["checkpoint"]
        self.assertEqual(checkpoint["cycle_checkpoint_identity"], "cycle_id+capability_id")
        self.assertTrue(checkpoint["global_observation_identity_and_cycle_checkpoint_are_distinct"])
        self.assertTrue(checkpoint["global_observation_may_belong_to_multiple_cycle_checkpoints"])
        self.assertTrue(checkpoint["complete_checkpoint_required_for_reuse"])
        self.assertFalse(checkpoint["partial_reuse"])
        self.assertFalse(checkpoint["partial_provider_reacquire_merge"])
        self.assertEqual(
            checkpoint["reuse_condition"],
            "LEDGER_SUCCESS_AND_CHECKPOINT_IDENTITY_MATCH_AND_CHECKPOINT_COMPLETE_AND_CHECKPOINT_INTEGRITY_PASS",
        )
        self.assertEqual(checkpoint["legacy_v1_nonterminal_checkpoint"], "SAFE_REACQUIRE")
        self.assertEqual(
            checkpoint["migration"],
            "ADDITIVE_IDEMPOTENT_V1_TO_V2_NO_VOLUME_RESET",
        )
        self.assertEqual(
            D8["idempotency"]["observation_identity"],
            "sha256(provider|series_id|provider_timestamp_at|payload_fingerprint)",
        )

    def test_semantic_receipt_v2_and_hash_roles_are_preserved(self):
        receipt = D8["consumer_continuity"]["receipt_contract"]
        self.assertEqual(receipt["canonical_semantic_receipt"], "history-access-receipt/2.0.0")
        self.assertEqual(receipt["legacy_transport_receipt"], "history-consumer-receipt/1.0.0")
        self.assertEqual(receipt["legacy_transport_role"], "LEGACY_TRANSPORT_WRAPPER")
        self.assertEqual(receipt["semantic_output_hash"], "HASH_NORMALIZED_SEMANTIC_OBSERVATIONS")
        self.assertEqual(receipt["transport_output_hash"], "HASH_RENDERED_CSV_JSON_ARTIFACT_BYTES")
        self.assertFalse(receipt["hashes_interchangeable"])

        consumer = BRIDGE["semantic_resolution"]["consumer"]
        self.assertEqual(consumer["canonical_semantic_receipt"], "history-access-receipt/2.0.0")
        self.assertEqual(consumer["legacy_transport_receipt"], "history-consumer-receipt/1.0.0")
        self.assertEqual(
            consumer["canonical_output_sha_semantics"],
            "SHA256_CANONICAL_NORMALIZED_SEMANTIC_OBSERVATIONS_JSON_LF",
        )

    def test_current_authority_is_unchanged(self):
        authority = D8["authority"]
        self.assertFalse(authority["d8_runtime_active"])
        self.assertFalse(authority["d9_active"])
        self.assertFalse(authority["vps_is_market_data_authority"])
        self.assertFalse(authority["provider_authority_transition_allowed"])
        self.assertFalse(authority["production_cutover_allowed"])
        self.assertEqual(authority["active_default_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertFalse(D8["d9_seam"]["production_warm_forwarder_deployed"])
        self.assertFalse(D8["binance_usdm"]["active_provider"])
        self.assertEqual(D8["github_legacy_policy"]["production_acquisition"], "CURRENTLY_ACTIVE_LEGACY")
        self.assertFalse(D8["github_legacy_policy"]["existing_schedule_disabled"])

        resolver = BRIDGE["semantic_resolution"]["resolver"]
        self.assertEqual(resolver["resolution_plan_schema"], "market-data-resolution-plan/1.0.0")
        self.assertEqual(BRIDGE["disabled_providers"]["binance-usdm"]["status"], "DISABLED_BY_POLICY")
        self.assertEqual(BRIDGE["disabled_providers"]["binance-usdm"]["network_calls"], 0)
        self.assertEqual(BRIDGE["disabled_providers"]["binance-usdm"]["vps_runtime_status"], "NOT_ACTIVE")

    def test_no_parallel_agent_read_interface_was_added(self):
        self.assertEqual(set(D8["interfaces"]), {"health", "readiness", "collect", "internal_port"})
        continuity = D8["consumer_continuity"]
        self.assertFalse(continuity["provider_reacquire"])
        self.assertFalse(continuity["second_resolver"])
        self.assertFalse(continuity["second_reader"])
        self.assertFalse(continuity["second_agent_read_api"])
        self.assertFalse(continuity["manual_storage_knowledge"])


if __name__ == "__main__":
    unittest.main()
