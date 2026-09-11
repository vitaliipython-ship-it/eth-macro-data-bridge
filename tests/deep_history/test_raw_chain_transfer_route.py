from __future__ import annotations

import ast
import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from ethereum_raw_transfer_rpc_adapter import EthereumJsonRpcProviderAdapter
from raw_chain_transfer_core import RawTransferFoundationError
from raw_chain_transfer_route import REQUIRED_ACK_GATES, RawTransferPhysicalRoute, RawTransferRouteError
from test_raw_chain_transfer_physical_route import (
    BLOCK_HASH,
    KNOWN_AT,
    OTHER_BLOCK_HASH,
    FakeTransport,
    base_trace,
    one_tx_transport,
)

ROOT = Path(__file__).resolve().parents[2]


class RecordingPublication:
    def __init__(self, mutate_ack=None) -> None:
        self.calls: list[tuple[bytes, str, dict[str, str]]] = []
        self.mutate_ack = mutate_ack

    def publish(self, bundle_bytes: bytes, content_identity: str, provenance: Mapping[str, str]) -> dict[str, Any]:
        captured = (bytes(bundle_bytes), content_identity, dict(provenance))
        self.calls.append(captured)
        ack: dict[str, Any] = {
            "ack_state": "PASS",
            "partial_ack": False,
            "content_identity": content_identity,
            "provenance": dict(provenance),
            "resource_id": "rawblk-test",
            "gates": {name: "PASS" for name in REQUIRED_ACK_GATES},
            "durability_evidence": {"sha256": content_identity, "size_bytes": len(bundle_bytes)},
            "control_plane_visibility_evidence": {"visible": True},
            "semantic_materialization_evidence": {"status": "PASS"},
        }
        if self.mutate_ack is not None:
            self.mutate_ack(ack)
        return ack


class FailingProvider:
    def fetch_block_bundle(self, chain_id: str, block_ref: str, *, observation_known_at: str):
        raise RawTransferFoundationError("INJECTED_COLLECTION_FAILURE", "COVERAGE_GAP")


def route_for(transport: FakeTransport, publication: RecordingPublication | None = None):
    publication = publication or RecordingPublication()
    return RawTransferPhysicalRoute(EthereumJsonRpcProviderAdapter(transport), publication), publication


class RawTransferRouteCompositionTests(unittest.TestCase):
    def test_T01_collect_to_serialize_publish_ack_pass(self) -> None:
        route, publication = route_for(one_tx_transport(trace=base_trace(value=5)))
        result = route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(result.ack_state, "PASS")
        self.assertEqual(result.observation_count, 1)
        self.assertEqual(len(publication.calls), 1)

    def test_T02_exact_canonical_bytes_are_published(self) -> None:
        route, publication = route_for(one_tx_transport(trace=base_trace(value=5)))
        route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        raw = publication.calls[0][0]
        decoded = json.loads(raw)
        self.assertEqual(raw, json.dumps(decoded, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode())
        self.assertFalse(raw.endswith(b"\n"))

    def test_T03_content_identity_is_sha256_of_exact_bytes_and_changes_with_bytes(self) -> None:
        first_route, first_pub = route_for(one_tx_transport(trace=base_trace(value=5)))
        first = first_route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(first.content_identity, hashlib.sha256(first_pub.calls[0][0]).hexdigest())
        second_route, second_pub = route_for(one_tx_transport(trace=base_trace(value=6)))
        second = second_route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(second.content_identity, hashlib.sha256(second_pub.calls[0][0]).hexdigest())
        self.assertNotEqual(first.content_identity, second.content_identity)

    def test_T04_publication_provenance_matches_canonical_bundle(self) -> None:
        route, publication = route_for(one_tx_transport(trace=base_trace(value=5)))
        result = route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        raw, _, provenance = publication.calls[0]
        bundle = json.loads(raw)
        self.assertEqual(provenance, bundle["source_provenance"])
        self.assertEqual(result.provenance_authority, provenance["authority"])
        self.assertEqual(result.provenance_evidence_id, provenance["evidence_id"])

    def test_T05_collection_failure_causes_no_publication(self) -> None:
        publication = RecordingPublication()
        route = RawTransferPhysicalRoute(FailingProvider(), publication)
        with self.assertRaises(RawTransferFoundationError):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(publication.calls, [])

    def test_T06_ack_state_not_pass_fails_closed(self) -> None:
        publication = RecordingPublication(lambda ack: ack.__setitem__("ack_state", "FAIL"))
        route, _ = route_for(FakeTransport(), publication)
        with self.assertRaisesRegex(RawTransferRouteError, "PUBLICATION_ACK_NOT_PASS"):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)

    def test_T07_partial_ack_true_fails_closed(self) -> None:
        publication = RecordingPublication(lambda ack: ack.__setitem__("partial_ack", True))
        route, _ = route_for(FakeTransport(), publication)
        with self.assertRaisesRegex(RawTransferRouteError, "PUBLICATION_ACK_PARTIAL"):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)

    def test_T08_ack_content_identity_mismatch_fails_closed(self) -> None:
        publication = RecordingPublication(lambda ack: ack.__setitem__("content_identity", "0" * 64))
        route, _ = route_for(FakeTransport(), publication)
        with self.assertRaisesRegex(RawTransferRouteError, "PUBLICATION_ACK_CONTENT_IDENTITY_MISMATCH"):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)

    def test_T09_ack_provenance_mismatch_fails_closed(self) -> None:
        publication = RecordingPublication(lambda ack: ack.__setitem__("provenance", {"authority": "tampered", "evidence_id": "tampered"}))
        route, _ = route_for(FakeTransport(), publication)
        with self.assertRaisesRegex(RawTransferRouteError, "PUBLICATION_ACK_PROVENANCE_MISMATCH"):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)

    def test_T10_covered_zero_publishes_nonempty_bundle_with_empty_observations(self) -> None:
        route, publication = route_for(FakeTransport())
        result = route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        raw = publication.calls[0][0]
        bundle = json.loads(raw)
        self.assertTrue(raw)
        self.assertEqual(bundle["observations"], [])
        self.assertTrue(bundle["coverage"]["complete"])
        self.assertEqual(bundle["coverage"]["zero_event_classification"], "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")
        self.assertEqual(result.zero_event_classification, "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")

    def test_T11_covered_zero_requires_durable_ack(self) -> None:
        def break_durability(ack):
            ack["gates"]["REMOTE_DURABILITY"] = "FAIL"
        route, _ = route_for(FakeTransport(), RecordingPublication(break_durability))
        with self.assertRaisesRegex(RawTransferRouteError, "PUBLICATION_ACK_GATE_FAILED"):
            route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)

    def test_T12_prior_canonical_block_passes_through_without_semantic_rewrite(self) -> None:
        prior = {"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH}
        original = deepcopy(prior)
        route, publication = route_for(FakeTransport())
        route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT, prior_canonical_block=prior)
        bundle = json.loads(publication.calls[0][0])
        self.assertEqual(prior, original)
        self.assertEqual(len(bundle["canonicality_revisions"]), 1)
        revision = bundle["canonicality_revisions"][0]
        self.assertEqual(revision["previous_canonical_block_hash"], OTHER_BLOCK_HASH)
        self.assertEqual(revision["canonical_block_hash"], BLOCK_HASH)
        self.assertEqual(revision["revision_known_at"], bundle["observation_known_at"])

    def test_T13_replay_same_evidence_yields_same_bytes_and_identity(self) -> None:
        first_route, first_pub = route_for(one_tx_transport(trace=base_trace(value=5)))
        second_route, second_pub = route_for(one_tx_transport(trace=base_trace(value=5)))
        first = first_route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        second = second_route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(first_pub.calls[0][0], second_pub.calls[0][0])
        self.assertEqual(first.content_identity, second.content_identity)

    def test_T14_route_has_no_vendor_storage_server_or_network_binding(self) -> None:
        path = ROOT / "src/raw_chain_transfer_route.py"
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in ("alchemy", "quicknode", "github", "vps", "hostname", "api_key", "filesystem", "database_locator"):
            self.assertNotIn(forbidden, lowered)
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Import)}
        imports.update(node.module.split(".")[0] for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom) and node.module)
        self.assertTrue(imports.isdisjoint({"urllib", "requests", "http", "socket", "aiohttp"}))

    def test_T15_live_network_request_count_zero(self) -> None:
        route, publication = route_for(FakeTransport())
        route.execute_block("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertEqual(len(publication.calls), 1)
        self.assertNotIn("network", publication.__dict__)

    def test_T16_bridge_contract_currentization_truthful_capability_remains_false(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertTrue(selective["raw_transfer_route_composition_source_implemented"])
        self.assertEqual(selective["raw_transfer_route_composition_network_inactive_qualification"], "PASS")
        self.assertFalse(selective["raw_transfer_route_composition_runtime_active"])
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        self.assertEqual(selective["raw_transfer_live_provider_qualification"], "NOT_STARTED")
        self.assertFalse(selective["provider_selected"])
        self.assertFalse(selective["storage_selected"])
        self.assertFalse(selective["production_activated"])

    def test_T17_runtime_d8_and_global_activation_state_unchanged(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        raw = bridge["semantic_contracts"]["raw_chain_transfer_fact"]
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertEqual(raw["status"], "CONTRACT_BOUND_RUNTIME_ROUTE_NOT_IMPLEMENTED")
        self.assertFalse(raw["runtime_active"])
        self.assertFalse(selective["raw_transfer_route_composition_runtime_active"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(selective["d9_global_active"])
        self.assertFalse(bridge["storage_portability"]["resolution_plan_v2_active"])


if __name__ == "__main__":
    unittest.main()
