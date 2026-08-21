from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from history_store import ImmutableHistoryConflict, append_partition, merge_records, partition_descriptor

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class D91ContractFoundationTests(unittest.TestCase):
    def test_d6_route_remains_active_v1(self):
        contract = read("bridge-contract.json")
        self.assertEqual(contract["contract_version"], "1.3.0")
        self.assertEqual(contract["semantic_resolution"]["status"], "ACTIVE")
        self.assertEqual(
            contract["semantic_resolution"]["resolver"]["resolution_plan_schema"],
            "market-data-resolution-plan/1.0.0",
        )
        self.assertEqual(contract["schema_versions"]["capability_index"], "1.0.0")
        self.assertEqual(contract["schema_versions"]["resolution_plan"], "1.0.0")

    def test_d9_candidate_is_explicitly_not_active(self):
        d9 = read("bridge-contract.json")["d9_candidate"]
        self.assertEqual(
            d9["status"],
            "SOURCE_CANDIDATE_NOT_ACTIVE_PUBLICATION_PORT_PHYSICALLY_QUALIFIED",
        )
        self.assertEqual(d9["target_contract_status"], "ACCEPTED")
        self.assertEqual(
            d9["source_implementation_status"],
            "COMPLETE_WITH_PUBLICATION_PORT_IMPLEMENTED_QUALIFIED_MERGED",
        )
        self.assertEqual(d9["canonical_d8_publication_implementation_status"], "SOURCE_IMPLEMENTED_QUALIFIED_MERGED")
        self.assertEqual(d9["physical_canonical_d8_publication_status"], "QUALIFIED")
        self.assertEqual(d9["authority_activation_status"], "NOT_ACTIVE")
        self.assertEqual(d9["single_spot_warm_root"], "history")
        self.assertFalse(d9["successor_route"]["second_resolver"])
        self.assertFalse(d9["successor_route"]["second_reader_family"])
        self.assertTrue(d9["activation_gate"]["d9_3_cold_activation_requires_d9_4"])
        self.assertTrue(d9["activation_gate"]["combined_d9_3_d9_4_qualification_required"])
        self.assertTrue(d9["activation_gate"]["canonical_d8_publication_required_before_d8_origin_authority"])

    def test_binance_usdm_disablement_is_runtime_scoped_not_permanent(self):
        contract = read("bridge-contract.json")
        current = contract["disabled_providers"]["binance-usdm"]
        self.assertEqual(current["status"], "DISABLED_BY_POLICY")
        self.assertEqual(current["network_calls"], 0)
        self.assertEqual(current["runtime_scope"], "CURRENT_GITHUB_HOSTED_ACQUISITION_ONLY")
        self.assertEqual(current["vps_runtime_status"], "NOT_ACTIVE")
        self.assertTrue(current["historical_archive_preserved"])
        self.assertEqual(
            current["target_state"],
            "REQUIRED_FUTURE_ACTIVE_PROVIDER_VIA_QUALIFIED_D8_VPS_RUNTIME",
        )

    def test_d8_dependency_and_vps_hot_seam_are_explicit(self):
        d9 = read("bridge-contract.json")["d9_candidate"]
        d8 = d9["d8_dependency"]
        self.assertEqual(d8["status"], "CAPTURED_REQUIRED")
        self.assertEqual(d8["target_collection_cadence"], "APPROX_5_MINUTES")
        self.assertFalse(d8["github_actions_is_primary_5m_acquisition_scheduler"])
        self.assertFalse(d8["vps_is_market_data_authority"])
        target = d8["binance_usdm"]
        self.assertEqual(target["vps_target"], "REQUIRED")
        self.assertEqual(target["vps_runtime"], "NOT_ACTIVE")
        self.assertFalse(target["active_provider"])
        seam = d9["hot_source_seam"]
        self.assertEqual(seam["status"], "CONTRACT_READY_NOT_ACTIVE")
        self.assertEqual(seam["physical_location"], "CANONICAL_AUTHORITY_RESOLVED")
        self.assertEqual(seam["transport"], "CANONICAL_AUTHORITY_RESOLVED")
        self.assertFalse(seam["hardcode_vps_hostname"])
        self.assertFalse(seam["hardcode_vps_filesystem_path"])
        self.assertFalse(seam["agent_direct_provider_access"])
        self.assertFalse(seam["git_commit_per_observation_hot_transport"])

    def test_binance_usdm_target_families_are_forward_compatible(self):
        families = {row["family"]: row["history_mode"] for row in read("bridge-contract.json")["d9_candidate"]["binance_usdm_target_families"]}
        expected = {
            "OHLCV_5M",
            "OHLCV_PROVIDER_NATIVE_HIGHER_TF",
            "MARK_PRICE",
            "INDEX_PRICE",
            "PREMIUM_BASIS",
            "OPEN_INTEREST",
            "FUNDING",
            "ORDER_BOOK_DEPTH_SNAPSHOT",
        }
        self.assertTrue(expected <= set(families))
        self.assertEqual(families["ORDER_BOOK_DEPTH_SNAPSHOT"], "FORWARD_ONLY")

    def test_successor_schemas_are_additive(self):
        d9 = read("bridge-contract.json")["d9_candidate"]
        for path in d9["successor_contracts"].values():
            schema = read(path)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith(path))
        self.assertEqual(read("history/capability-index.json")["schema_version"], "1.0.0")

    def test_collection_ledger_has_vps_timing_and_gap_semantics(self):
        ledger = read("schema/collection-run-ledger.schema.json")
        run = ledger["properties"]["runs"]["items"]
        required = set(run["required"])
        self.assertTrue(
            {
                "expected_schedule_at",
                "collection_started_at",
                "collection_completed_at",
                "provider_timestamp_at",
                "known_at",
                "retrieved_at",
                "freshness",
            }
            <= required
        )
        self.assertIn("COLLECTION_GAP", run["properties"]["status"]["enum"])

    def test_resolution_plan_hot_resource_is_authority_resolved(self):
        plan = read("schema/market-data-resolution-plan-v2.schema.json")
        descriptor = plan["$defs"]["hotPhysicalDescriptor"]
        self.assertEqual(descriptor["properties"]["locator_authority"]["const"], "CANONICAL_CONTROL_PLANE")
        self.assertEqual(descriptor["properties"]["transport_authority"]["const"], "CANONICAL_CONTROL_PLANE")
        segment = plan["$defs"]["segment"]["properties"]
        self.assertIn("HOT_CURRENT_RESOURCE", segment["storage"]["enum"])
        self.assertTrue(segment["storage"]["deprecated"])
        self.assertIn("residence_role", segment)
        self.assertIn("adapter_profile", segment)
        self.assertIn("resource_ref", segment)
        self.assertIn("integrity_evidence", segment)

    def test_capability_v2_supports_qualified_vps_hot_source(self):
        capability = read("schema/capability-index-v2.schema.json")
        profile = capability["properties"]["profiles"]["additionalProperties"]
        self.assertIn("hot_source_policy", profile["required"])
        hot = profile["properties"]["hot_source_policy"]["properties"]
        self.assertIn("QUALIFIED_VPS", hot["runtime_class"]["enum"])
        self.assertIn("QUALIFIED_RUNTIME_REQUIRED", hot["status"]["enum"])

    def test_history_store_append_is_idempotent_and_sorted(self):
        result = merge_records([[20, "b"], [10, "a"]], [[20, "b"], [30, "c"]])
        self.assertTrue(result.changed)
        self.assertEqual(result.records, [[10, "a"], [20, "b"], [30, "c"]])
        self.assertEqual(result.conflicts, [])
        again = merge_records(result.records, [[10, "a"], [30, "c"]])
        self.assertFalse(again.changed)
        self.assertEqual(again.records, result.records)

    def test_history_store_conflict_fails_closed(self):
        with self.assertRaises(ImmutableHistoryConflict) as ctx:
            merge_records([[10, "old"]], [[10, "new"]])
        self.assertEqual(ctx.exception.conflicts[0]["reason"], "IMMUTABLE_IDENTITY_CONFLICT")

    def test_qualified_revision_does_not_overwrite_base_observation(self):
        classifier = lambda old, new, identity: "PROVIDER_REVISABLE_SNAPSHOT"
        result = merge_records([[10, "old"]], [[10, "new"]], revision_classifier=classifier)
        self.assertFalse(result.changed)
        self.assertEqual(result.records, [[10, "old"]])
        self.assertEqual(result.revisions[0]["observed"], [10, "new"])
        self.assertEqual(result.revisions[0]["previous"], [10, "old"])

    def test_partition_write_and_descriptor_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "part.json"
            metadata = {"schema_version": "test/1.0.0", "provider": "fixture"}
            append_partition(path, metadata, [[20, "b"], [10, "a"]])
            first = path.read_bytes()
            descriptor = partition_descriptor(path)
            append_partition(path, metadata, [[10, "a"], [20, "b"]])
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(descriptor["record_count"], 2)
            self.assertEqual(descriptor["first_identity"], 10)
            self.assertEqual(descriptor["last_identity"], 20)
            self.assertEqual(len(descriptor["sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
