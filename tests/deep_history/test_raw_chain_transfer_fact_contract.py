from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RawChainTransferFactContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = read("bridge-contract.json")
        cls.raw = read("contracts/raw-chain-transfer-fact-semantic-contract-v1.json")
        cls.ptr = cls.bridge["semantic_contracts"]["raw_chain_transfer_fact"]

    def test_t01_t05_machine_discovery_owner_layer(self):
        self.assertEqual(self.ptr["path"], "contracts/raw-chain-transfer-fact-semantic-contract-v1.json")
        self.assertEqual(self.ptr["capability_id"], "blockchain.raw-transfer-facts")
        self.assertEqual(self.ptr["owner_domain"], "MARKET_DATA_FOUNDATION")
        self.assertEqual(self.ptr["layer"], "L0_FACTUAL")
        self.assertFalse(self.ptr["analytical_state"])

    def test_t06_t10_selective_v2_semantics_without_global_activation(self):
        plan = self.raw["resolution_plan"]
        self.assertEqual(plan["plan_schema"], "market-data-resolution-plan/2.0.0")
        self.assertEqual(plan["series_kind"], "STRUCTURED_TIME_SERIES")
        self.assertEqual(plan["coverage_semantics"], "EVENT_DRIVEN")
        self.assertEqual(plan["revision_policy"], "CHAIN_CANONICALITY_REVISION")
        self.assertFalse(plan["d9_global_activation"])
        self.assertFalse(plan["v2_global_activation"])

    def test_t11_t14_factual_identity_and_no_attribution(self):
        obs = self.raw["observation"]
        required = {"observation_id","chain_id","transaction_hash","transfer_identity","block_height","block_hash","event_time","observation_known_at","source_address","destination_address","asset_identity","native_quantity","native_quantity_unit","finality","source_provenance"}
        self.assertTrue(required.issubset(obs["required_fields"]))
        self.assertEqual(obs["transfer_identity_rule"], "DETERMINISTIC_FROM_CHAIN_NATIVE_FACTUAL_IDENTITY_COMPONENTS")
        self.assertEqual(set(obs["conditional_identity_fields"]), {"log_index","trace_index","transfer_index"})
        self.assertFalse(obs["address_semantics"]["address_is_entity"])
        self.assertFalse(obs["address_semantics"]["address_is_exchange"])
        self.assertFalse(obs["address_semantics"]["address_is_whale"])
        forbidden = set(self.raw["forbidden_analytical_fields"])
        self.assertTrue({"entity_label","exchange_label","whale_label","accumulation_signal","distribution_signal","directional_interpretation"}.issubset(forbidden))

    def test_t15_t16_coverage_absence_is_not_zero(self):
        cov = self.raw["coverage"]
        self.assertFalse(cov["absence_without_coverage_proof_is_zero"])
        self.assertEqual(cov["states"], ["NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE","SOURCE_NOT_OBSERVED","COVERAGE_GAP","PROVIDER_UNAVAILABLE","UNKNOWN"])

    def test_t17_t18_provider_network_storage_deferred(self):
        b = self.raw["boundaries"]
        self.assertEqual(self.raw["capability"]["provider_selection"], "DEFERRED")
        self.assertFalse(self.raw["capability"]["runtime_active"])
        self.assertEqual(self.raw["capability"]["route_status"], "NOT_IMPLEMENTED")
        for key in ("provider_selected","rpc_selected","indexer_selected","storage_selected","api_key_contract_created"):
            self.assertFalse(b[key])
        self.assertEqual(b["network_calls_added"], 0)

    def test_t19_t20_no_runtime_capability_row(self):
        idx = read("history/capability-index.json")
        self.assertNotIn("blockchain.raw-transfer-facts", json.dumps(idx, sort_keys=True))
        self.assertFalse(self.raw["boundaries"]["history_capability_index_runtime_row_created"])
        self.assertFalse(self.raw["boundaries"]["fake_availability_status_created"])
        self.assertFalse(self.raw["boundaries"]["fake_provider_profile_created"])

    def test_t21_zero_job_recovery_semantics_preserved(self):
        z = self.bridge["semantic_resolution"]["current_data"]["zero_job_recovery"]
        canonical = json.dumps(z, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), "f4611f4b301834f8d07be7448e2ae6b85616b3a5aa56e7657678531146e0e01c")

    def test_t22_d6_v1_default_route_preserved(self):
        self.assertEqual(self.bridge["semantic_resolution"]["resolver"]["resolution_plan_schema"], "market-data-resolution-plan/1.0.0")
        self.assertTrue(self.bridge["storage_portability"]["d6_resolution_plan_v1_active"])
        self.assertFalse(self.bridge["storage_portability"]["resolution_plan_v2_active"])

    def test_t23_selective_v2_event_reorg_substrate_preserved(self):
        s = self.bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertTrue(s["source_implemented"])
        self.assertFalse(s["production_activated"])
        self.assertEqual(s["revision_policy"], "CHAIN_CANONICALITY_REVISION")
        self.assertEqual(s["chain_reorg_model"], "APPEND_ONLY_VERSIONED_CANONICALITY_STATE_WITH_PIT_CUTOFF")
        self.assertTrue(s["canonicality_evidence_policy"]["superseded_observation_remains_addressable"])


if __name__ == "__main__":
    unittest.main()
