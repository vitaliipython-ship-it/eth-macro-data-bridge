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
        self.assertEqual(contract["contract_version"], "1.2.0")
        self.assertEqual(contract["semantic_resolution"]["status"], "ACTIVE")
        self.assertEqual(
            contract["semantic_resolution"]["resolver"]["resolution_plan_schema"],
            "market-data-resolution-plan/1.0.0",
        )
        self.assertEqual(contract["schema_versions"]["capability_index"], "1.0.0")
        self.assertEqual(contract["schema_versions"]["resolution_plan"], "1.0.0")

    def test_d9_candidate_is_explicitly_not_active(self):
        d9 = read("bridge-contract.json")["d9_candidate"]
        self.assertEqual(d9["status"], "D9_1_IMPLEMENTATION_CANDIDATE_NOT_ACTIVE")
        self.assertEqual(d9["single_spot_warm_root"], "history")
        self.assertFalse(d9["successor_route"]["second_resolver"])
        self.assertFalse(d9["successor_route"]["second_reader_family"])
        self.assertTrue(d9["activation_gate"]["d9_3_cold_activation_requires_d9_4"])
        self.assertTrue(d9["activation_gate"]["combined_d9_3_d9_4_qualification_required"])

    def test_successor_schemas_are_additive(self):
        d9 = read("bridge-contract.json")["d9_candidate"]
        for path in d9["successor_contracts"].values():
            schema = read(path)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith(path))
        self.assertEqual(read("history/capability-index.json")["schema_version"], "1.0.0")

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
