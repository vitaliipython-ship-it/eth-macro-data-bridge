from __future__ import annotations

import ast
import inspect
import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

from ethereum_raw_transfer_rpc_adapter import EthereumJsonRpcProviderAdapter, EthereumRawTransferRpcError
from raw_chain_transfer_core import CanonicalBlockReferencePort, ProviderPort, RawTransferFoundationError
from test_raw_chain_transfer_physical_route import BLOCK_HASH, FakeTransport

ROOT = Path(__file__).resolve().parents[2]
OTHER_HASH = "0x" + "ab" * 32


class DiscoveryTransport:
    def __init__(self, *, chain_id: Any = "0x1", block: Any = None, failure: Any = None) -> None:
        self.chain_id = chain_id
        self.block = {"number": "0x10", "hash": "0x" + "AB" * 32} if block is None else block
        self.failure = failure
        self.calls: list[tuple[str, list[Any]]] = []

    def request(self, method: str, params: list[Any]) -> dict[str, Any]:
        self.calls.append((method, deepcopy(params)))
        if self.failure is not None and method == "eth_getBlockByNumber":
            if isinstance(self.failure, BaseException):
                raise self.failure
            return {"jsonrpc": "2.0", "id": 1, "error": deepcopy(self.failure)}
        result = self.chain_id if method == "eth_chainId" else self.block
        return {"jsonrpc": "2.0", "id": 1, "result": deepcopy(result)}


class RawTransferBlockReferenceTests(unittest.TestCase):
    def test_T01_separate_protocol_provider_port_stable(self) -> None:
        self.assertTrue(inspect.isclass(CanonicalBlockReferencePort))
        self.assertIn("resolve_block_hash", CanonicalBlockReferencePort.__dict__)
        self.assertNotIn("resolve_block_hash", ProviderPort.__dict__)
        self.assertEqual(list(inspect.signature(ProviderPort.fetch_block_bundle).parameters), ["self", "chain_id", "block_ref", "observation_known_at"])

    def test_T02_exact_rpc_sequence(self) -> None:
        transport = DiscoveryTransport()
        result = EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual(result, "0x" + "ab" * 32)
        self.assertEqual(transport.calls, [("eth_chainId", []), ("eth_getBlockByNumber", ["0x10", False])])

    def test_T03_height_encoding_is_canonical_hex_quantity(self) -> None:
        for height, encoded in ((0, "0x0"), (1, "0x1"), (16, "0x10")):
            transport = DiscoveryTransport(block={"number": encoded, "hash": BLOCK_HASH})
            EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=height)
            self.assertEqual(transport.calls[-1], ("eth_getBlockByNumber", [encoded, False]))
        for invalid in (-1, True, "16"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(EthereumRawTransferRpcError, "BLOCK_REFERENCE_HEIGHT_INVALID"):
                EthereumJsonRpcProviderAdapter(DiscoveryTransport()).resolve_block_hash(chain_id="1", block_height=invalid)  # type: ignore[arg-type]

    def test_T04_hash_is_exact_32_byte_and_normalized_lowercase(self) -> None:
        result = EthereumJsonRpcProviderAdapter(DiscoveryTransport()).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual(result, "0x" + "ab" * 32)

    def test_T05_chain_mismatch_fails_closed_before_block_lookup(self) -> None:
        transport = DiscoveryTransport(chain_id="0x2")
        with self.assertRaisesRegex(EthereumRawTransferRpcError, "CHAIN_ID_MISMATCH"):
            EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual(transport.calls, [("eth_chainId", [])])

    def test_T06_missing_block_fails_closed_without_fallback(self) -> None:
        transport = DiscoveryTransport(block=None)
        transport.block = None
        with self.assertRaisesRegex(EthereumRawTransferRpcError, "BLOCK_REFERENCE_MISSING"):
            EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual([m for m, _ in transport.calls], ["eth_chainId", "eth_getBlockByNumber"])

    def test_T07_returned_height_mismatch_fails_closed(self) -> None:
        transport = DiscoveryTransport(block={"number": "0x11", "hash": BLOCK_HASH})
        with self.assertRaisesRegex(EthereumRawTransferRpcError, "BLOCK_REFERENCE_NUMBER_MISMATCH"):
            EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)

    def test_T08_missing_or_malformed_hash_fails_closed(self) -> None:
        for block in ({"number": "0x10"}, {"number": "0x10", "hash": "0x1234"}, {"number": "0x10", "hash": "0x" + "zz" * 32}):
            with self.subTest(block=block), self.assertRaises((EthereumRawTransferRpcError, RawTransferFoundationError)):
                EthereumJsonRpcProviderAdapter(DiscoveryTransport(block=block)).resolve_block_hash(chain_id="1", block_height=16)

    def test_T09_missing_or_malformed_returned_number_fails_closed(self) -> None:
        for block in ({"hash": BLOCK_HASH}, {"number": True, "hash": BLOCK_HASH}, {"number": "bad", "hash": BLOCK_HASH}):
            with self.subTest(block=block), self.assertRaises(EthereumRawTransferRpcError):
                EthereumJsonRpcProviderAdapter(DiscoveryTransport(block=block)).resolve_block_hash(chain_id="1", block_height=16)

    def test_T10_rpc_error_uses_existing_taxonomy(self) -> None:
        transport = DiscoveryTransport(failure={"code": 429, "message": "rate limit"})
        with self.assertRaises(EthereumRawTransferRpcError) as caught:
            EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual(caught.exception.classification, "PROVIDER_UNAVAILABLE")
        self.assertEqual(caught.exception.code, "RPC_PROVIDER_UNAVAILABLE")

    def test_T11_existing_fetch_bundle_stays_exact_hash_route(self) -> None:
        transport = FakeTransport()
        EthereumJsonRpcProviderAdapter(transport).fetch_block_bundle("1", BLOCK_HASH, observation_known_at="2026-09-10T12:00:00Z")
        methods = [method for method, _ in transport.calls]
        self.assertIn("eth_getBlockByHash", methods)
        self.assertEqual(transport.calls[1], ("eth_getBlockByHash", [BLOCK_HASH, True]))

    def test_T12_finalized_tag_semantics_unchanged(self) -> None:
        transport = FakeTransport()
        EthereumJsonRpcProviderAdapter(transport).fetch_block_bundle("1", BLOCK_HASH, observation_known_at="2026-09-10T12:00:00Z")
        self.assertEqual(transport.calls[-1], ("eth_getBlockByNumber", ["finalized", False]))

    def test_T13_fake_transport_only_live_network_zero(self) -> None:
        transport = DiscoveryTransport()
        EthereumJsonRpcProviderAdapter(transport).resolve_block_hash(chain_id="1", block_height=16)
        self.assertEqual(len(transport.calls), 2)
        self.assertFalse(any(hasattr(transport, key) for key in ("url", "endpoint", "token", "credential")))

    def test_T14_source_has_no_vendor_endpoint_credential_storage_or_server_binding(self) -> None:
        for rel in ("src/raw_chain_transfer_core.py", "src/ethereum_raw_transfer_rpc_adapter.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            lowered = source.lower()
            for forbidden in ("alchemy", "quicknode", "infura", "ankr", "api_key", "database_locator", "aife", "http://", "https://"):
                self.assertNotIn(forbidden, lowered)
            self.assertNotIn("os.getenv", lowered)
        adapter_ast = ast.parse((ROOT / "src/ethereum_raw_transfer_rpc_adapter.py").read_text(encoding="utf-8"))
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(adapter_ast) if isinstance(node, ast.Import)}
        imports.update(node.module.split(".")[0] for node in ast.walk(adapter_ast) if isinstance(node, ast.ImportFrom) and node.module)
        self.assertTrue(imports.isdisjoint({"urllib", "requests", "http", "socket", "aiohttp"}))

    def test_T15_bridge_contract_discovery_predicates_truthful(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        self.assertTrue(selective["raw_transfer_block_reference_discovery_source_implemented"])
        self.assertEqual(selective["raw_transfer_block_reference_discovery_network_inactive_qualification"], "PASS")
        self.assertFalse(selective["raw_transfer_block_reference_discovery_runtime_active"])

    def test_T16_higher_activation_boundaries_unchanged(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        raw = bridge["semantic_contracts"]["raw_chain_transfer_fact"]
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        self.assertEqual(selective["raw_transfer_live_provider_qualification"], "NOT_STARTED")
        self.assertFalse(selective["provider_selected"])
        self.assertFalse(selective["storage_selected"])
        self.assertFalse(selective["production_activated"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(selective["d9_global_active"])
        self.assertFalse(raw["runtime_active"])
        self.assertEqual(raw["status"], "CONTRACT_BOUND_RUNTIME_ROUTE_NOT_IMPLEMENTED")


if __name__ == "__main__":
    unittest.main()
