from __future__ import annotations

import inspect
import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

from canonical_json import sha256_canonical_json
from ethereum_raw_transfer_rpc_adapter import EthereumJsonRpcProviderAdapter, EthereumRawTransferRpcError
from raw_chain_transfer_core import (
    BUNDLE_SCHEMA_VERSION,
    CAPABILITY_ID,
    CHAIN_REORG_MODEL,
    ERC1155_BATCH_TOPIC,
    ERC1155_SINGLE_TOPIC,
    PARSER_POLICY_REVISION,
    TRANSFER_TOPIC,
    ProviderPort,
    RawTransferCollectionCore,
    RawTransferFoundationError,
    build_physical_block_bundle,
    derive_transfer_identity,
    serialize_physical_block_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
KNOWN_AT = "2026-09-10T12:00:00Z"
BLOCK_HASH = "0x" + "11" * 32
OTHER_BLOCK_HASH = "0x" + "22" * 32
TX1 = "0x" + "31" * 32
TX2 = "0x" + "32" * 32
A1 = "0x" + "aa" * 20
A2 = "0x" + "bb" * 20
A3 = "0x" + "cc" * 20
TOKEN = "0x" + "dd" * 20

FORBIDDEN = {
    "source_entity",
    "destination_entity",
    "entity_label",
    "exchange_label",
    "whale_label",
    "smart_money_label",
    "owner_name",
    "custodian_classification",
    "whale_classification",
    "whale_threshold",
    "accumulation_signal",
    "distribution_signal",
    "exchange_inflow_classification",
    "exchange_outflow_classification",
    "entity_position",
    "entity_position_change",
    "directional_interpretation",
    "forensic_score",
    "usd_value",
}


def word(value: int) -> str:
    return value.to_bytes(32, "big").hex()


def topic_address(address: str) -> str:
    return "0x" + "0" * 24 + address[2:]


def batch_data(ids: list[int], values: list[int]) -> str:
    first_offset = 64
    second_offset = first_offset + 32 * (1 + len(ids))
    parts = [word(first_offset), word(second_offset), word(len(ids))]
    parts.extend(word(value) for value in ids)
    parts.append(word(len(values)))
    parts.extend(word(value) for value in values)
    return "0x" + "".join(parts)


def base_trace(*, value: int = 0, frame_type: str = "CALL", calls: list[dict[str, Any]] | None = None, error: str | None = None) -> dict[str, Any]:
    frame: dict[str, Any] = {
        "type": frame_type,
        "from": A1,
        "to": A2,
        "value": hex(value),
        "calls": calls or [],
    }
    if error is not None:
        frame["error"] = error
    return frame


def make_log(
    topic0: str,
    *,
    tx_hash: str = TX1,
    block_hash: str = BLOCK_HASH,
    log_index: int = 0,
    topics: list[str] | None = None,
    data: str = "0x",
    address: str = TOKEN,
) -> dict[str, Any]:
    return {
        "address": address,
        "topics": [topic0] + (topics or []),
        "data": data,
        "blockHash": block_hash,
        "transactionHash": tx_hash,
        "logIndex": hex(log_index),
        "removed": False,
    }


def make_receipt(tx_hash: str, logs: list[dict[str, Any]] | None = None, *, block_hash: str = BLOCK_HASH, status: str = "0x1") -> dict[str, Any]:
    return {
        "transactionHash": tx_hash,
        "blockHash": block_hash,
        "blockNumber": "0x64",
        "status": status,
        "logs": logs or [],
    }


class FakeTransport:
    def __init__(
        self,
        *,
        chain_id: str = "0x1",
        block_hash: str = BLOCK_HASH,
        transactions: list[str] | None = None,
        receipts: list[dict[str, Any]] | None = None,
        traces: list[dict[str, Any]] | None = None,
        finalized: dict[str, Any] | None = None,
        failures: dict[str, Any] | None = None,
        provider_label: str | None = None,
    ) -> None:
        txs = [] if transactions is None else transactions
        self.block = {
            "hash": block_hash,
            "number": "0x64",
            "timestamp": "0x68c2cb00",
            "transactions": [{"hash": tx_hash, "from": A1, "to": A2} for tx_hash in txs],
        }
        self.chain_id = chain_id
        self.receipts = [] if receipts is None else receipts
        self.traces = [] if traces is None else traces
        self.finalized = finalized if finalized is not None else {"number": "0x63", "hash": "0x" + "09" * 32}
        self.failures = failures or {}
        self.provider_label = provider_label
        self.calls: list[tuple[str, list[Any]]] = []

    def request(self, method: str, params: list[Any]) -> dict[str, Any]:
        self.calls.append((method, deepcopy(params)))
        failure = self.failures.get(method)
        if isinstance(failure, BaseException):
            raise failure
        if failure is not None:
            return {"jsonrpc": "2.0", "id": 1, "error": deepcopy(failure)}
        values = {
            "eth_chainId": self.chain_id,
            "eth_getBlockByHash": self.block,
            "eth_getBlockReceipts": self.receipts,
            "debug_traceBlockByHash": self.traces,
            "eth_getBlockByNumber": self.finalized,
        }
        return {"jsonrpc": "2.0", "id": 1, "result": deepcopy(values[method])}


def one_tx_transport(
    *,
    trace: dict[str, Any] | None = None,
    logs: list[dict[str, Any]] | None = None,
    status: str = "0x1",
    **kwargs: Any,
) -> FakeTransport:
    trace = base_trace() if trace is None else trace
    return FakeTransport(
        transactions=[TX1],
        receipts=[make_receipt(TX1, logs, status=status)],
        traces=[{"txHash": TX1, "result": trace}],
        **kwargs,
    )


def build_bundle(transport: FakeTransport, *, known_at: str = KNOWN_AT, chain_id: str = "1", block_ref: str = BLOCK_HASH, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    provider = EthereumJsonRpcProviderAdapter(transport)
    return RawTransferCollectionCore(provider).collect_block(
        chain_id,
        block_ref,
        observation_known_at=known_at,
        prior_canonical_block=prior,
    )


def transfer_log_erc20(*, value: int = 7, source: str = A1, destination: str = A2, log_index: int = 0) -> dict[str, Any]:
    return make_log(
        TRANSFER_TOPIC,
        topics=[topic_address(source), topic_address(destination)],
        data="0x" + word(value),
        log_index=log_index,
    )


def transfer_log_erc721(*, token_id: int = 9, log_index: int = 0) -> dict[str, Any]:
    return make_log(
        TRANSFER_TOPIC,
        topics=[topic_address(A1), topic_address(A2), "0x" + word(token_id)],
        data="0x",
        log_index=log_index,
    )


def transfer_log_erc1155_single(*, token_id: int = 12, value: int = 3, log_index: int = 0) -> dict[str, Any]:
    return make_log(
        ERC1155_SINGLE_TOPIC,
        topics=[topic_address(A3), topic_address(A1), topic_address(A2)],
        data="0x" + word(token_id) + word(value),
        log_index=log_index,
    )


def transfer_log_erc1155_batch(*, ids: list[int] | None = None, values: list[int] | None = None, log_index: int = 0) -> dict[str, Any]:
    ids = [12, 13] if ids is None else ids
    values = [3, 4] if values is None else values
    return make_log(
        ERC1155_BATCH_TOPIC,
        topics=[topic_address(A3), topic_address(A1), topic_address(A2)],
        data=batch_data(ids, values),
        log_index=log_index,
    )


def collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(collect_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(collect_keys(child))
    return keys


class RawTransferPhysicalRouteTests(unittest.TestCase):
    def test_T01_capability_id_remains_stable(self) -> None:
        bundle = build_bundle(FakeTransport())
        self.assertEqual(CAPABILITY_ID, "blockchain.raw-transfer-facts")
        self.assertEqual(bundle["capability_id"], CAPABILITY_ID)

    def test_T02_required_l0_fields_emitted(self) -> None:
        bundle = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        row = bundle["observations"][0]
        required = {
            "observation_id", "chain_id", "transaction_hash", "transfer_identity", "block_height", "block_hash",
            "event_time", "observation_known_at", "source_address", "destination_address", "asset_identity",
            "native_quantity", "native_quantity_unit", "finality", "source_provenance",
        }
        self.assertTrue(required.issubset(row))

    def test_T03_forbidden_analytical_fields_absent(self) -> None:
        bundle = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        self.assertFalse(FORBIDDEN.intersection(collect_keys(bundle)))

    def test_T04_transfer_identity_deterministic_on_replay(self) -> None:
        a = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        b = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        self.assertEqual(a["observations"][0]["transfer_identity"], b["observations"][0]["transfer_identity"])

    def test_T05_observation_id_deterministic_on_replay(self) -> None:
        a = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        b = build_bundle(one_tx_transport(trace=base_trace(value=5)))
        self.assertEqual(a["observations"][0]["observation_id"], b["observations"][0]["observation_id"])

    def test_T06_native_eth_call_value_transfer_normalizes(self) -> None:
        row = build_bundle(one_tx_transport(trace=base_trace(value=123)))["observations"][0]
        self.assertEqual(row["asset_identity"], {"kind": "NATIVE_ASSET", "chain_id": "1", "asset": "ETH"})
        self.assertEqual((row["source_address"], row["destination_address"], row["native_quantity"], row["native_quantity_unit"]), (A1, A2, "123", "wei"))
        self.assertEqual(row["trace_index"], "0")

    def test_T07_create_and_create2_value_transfers_normalize(self) -> None:
        calls = [
            {"type": "CREATE", "from": A1, "to": A2, "value": "0x2", "calls": []},
            {"type": "CREATE2", "from": A1, "to": A3, "value": "0x3", "calls": []},
        ]
        rows = build_bundle(one_tx_transport(trace=base_trace(calls=calls)))["observations"]
        self.assertEqual({row["trace_index"] for row in rows}, {"0.0", "0.1"})
        self.assertEqual({row["native_quantity"] for row in rows}, {"2", "3"})

    def test_T08_selfdestruct_value_transfer_normalizes(self) -> None:
        trace = {"type": "SELFDESTRUCT", "from": A1, "to": A2, "value": "0x7", "calls": []}
        row = build_bundle(one_tx_transport(trace=trace))["observations"][0]
        self.assertEqual(row["native_quantity"], "7")
        self.assertEqual(row["trace_index"], "0")

    def test_T09_failed_value_effect_is_not_emitted(self) -> None:
        trace = base_trace(value=10, error="execution reverted")
        bundle = build_bundle(one_tx_transport(trace=trace, status="0x0"))
        self.assertEqual(bundle["observations"], [])
        self.assertEqual(bundle["coverage"]["zero_event_classification"], "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")

    def test_T10_erc20_transfer_normalizes(self) -> None:
        row = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=17)]))["observations"][0]
        self.assertEqual(row["asset_identity"]["standard"], "ERC20")
        self.assertEqual(row["native_quantity"], "17")
        self.assertEqual(row["log_index"], 0)

    def test_T11_erc721_transfer_normalizes(self) -> None:
        row = build_bundle(one_tx_transport(logs=[transfer_log_erc721(token_id=77)]))["observations"][0]
        self.assertEqual(row["asset_identity"]["standard"], "ERC721")
        self.assertEqual(row["asset_identity"]["token_id"], "77")
        self.assertEqual(row["native_quantity"], "1")

    def test_T12_erc1155_transfer_single_normalizes(self) -> None:
        row = build_bundle(one_tx_transport(logs=[transfer_log_erc1155_single(token_id=21, value=8)]))["observations"][0]
        self.assertEqual(row["asset_identity"]["standard"], "ERC1155")
        self.assertEqual(row["asset_identity"]["token_id"], "21")
        self.assertEqual(row["native_quantity"], "8")

    def test_T13_erc1155_batch_creates_deterministic_multiple_transfers(self) -> None:
        first = build_bundle(one_tx_transport(logs=[transfer_log_erc1155_batch(ids=[2, 3], values=[11, 12])]))
        second = build_bundle(one_tx_transport(logs=[transfer_log_erc1155_batch(ids=[2, 3], values=[11, 12])]))
        rows = first["observations"]
        self.assertEqual([row["transfer_index"] for row in rows], [0, 1])
        self.assertEqual([row["transfer_identity"] for row in rows], [row["transfer_identity"] for row in second["observations"]])

    def test_T14_quantities_are_lossless_strings_never_float(self) -> None:
        huge = 2**255 + 123456789
        row = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=huge)]))["observations"][0]
        self.assertEqual(row["native_quantity"], str(huge))
        self.assertIsInstance(row["native_quantity"], str)
        self.assertNotIsInstance(row["native_quantity"], float)

    def test_T15_equivalent_address_casing_normalizes_identity(self) -> None:
        lower = build_bundle(one_tx_transport(logs=[transfer_log_erc20(source=A1, destination=A2)]))["observations"][0]
        upper = build_bundle(one_tx_transport(logs=[transfer_log_erc20(source=A1.upper().replace("0X", "0x"), destination=A2.upper().replace("0X", "0x"))]))["observations"][0]
        self.assertEqual(lower["source_address"], upper["source_address"])
        self.assertEqual(lower["destination_address"], upper["destination_address"])
        self.assertEqual(lower["transfer_identity"], upper["transfer_identity"])

    def test_T16_complete_zero_transfer_block_is_valid(self) -> None:
        bundle = build_bundle(FakeTransport())
        self.assertEqual(bundle["observations"], [])
        self.assertTrue(bundle["coverage"]["complete"])
        self.assertEqual(bundle["coverage"]["zero_event_classification"], "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")
        self.assertTrue(serialize_physical_block_bundle(bundle))

    def test_T17_zero_transfer_block_carries_all_coverage_components(self) -> None:
        coverage = build_bundle(FakeTransport())["coverage"]
        self.assertEqual(
            set(coverage["components"]),
            {"BLOCK_BODY", "ALL_TRANSACTION_RECEIPTS", "ALL_TRANSACTION_TRACES", "DECLARED_TOKEN_EVENT_PARSERS"},
        )
        self.assertTrue(all(member["verified"] for member in coverage["components"].values()))
        self.assertFalse(coverage["absence_without_coverage_proof_is_zero"])

    def test_T18_provisional_finality_supported(self) -> None:
        bundle = build_bundle(FakeTransport())
        self.assertEqual(bundle["finality"], "PROVISIONAL")

    def test_T19_finalized_requires_exact_finalized_block_evidence(self) -> None:
        finalized = {"number": "0x64", "hash": BLOCK_HASH}
        bundle = build_bundle(FakeTransport(finalized=finalized))
        self.assertEqual(bundle["finality"], "FINALIZED")

    def test_T20_source_provenance_survives_bundle_serialization(self) -> None:
        bundle = build_bundle(one_tx_transport(trace=base_trace(value=1)))
        encoded = serialize_physical_block_bundle(bundle)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["source_provenance"], bundle["source_provenance"])
        self.assertEqual(decoded["observations"][0]["source_provenance"], bundle["source_provenance"])

    def test_T21_bundle_serialization_is_deterministic_canonical_json(self) -> None:
        bundle = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=3)]))
        first = serialize_physical_block_bundle(bundle)
        second = serialize_physical_block_bundle(deepcopy(bundle))
        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8"))
        self.assertFalse(first.endswith(b"\n"))

    def test_T22_retry_produces_semantically_identical_bundle(self) -> None:
        first = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=3)]))
        second = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=3)]))
        self.assertEqual(serialize_physical_block_bundle(first), serialize_physical_block_bundle(second))

    def test_T23_reorg_hash_change_creates_append_only_revision(self) -> None:
        prior = {"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH}
        bundle = build_bundle(FakeTransport(), prior=prior)
        self.assertEqual(CHAIN_REORG_MODEL, "APPEND_ONLY_VERSIONED_CANONICALITY_STATE_WITH_PIT_CUTOFF")
        revision = bundle["canonicality_revisions"][0]
        self.assertEqual(revision["previous_canonical_block_hash"], OTHER_BLOCK_HASH)
        self.assertEqual(revision["canonical_block_hash"], BLOCK_HASH)

    def test_T24_reorg_does_not_mutate_prior_observation_evidence(self) -> None:
        prior = {"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH, "observation_id": "old-observation"}
        original = deepcopy(prior)
        bundle = build_bundle(FakeTransport(), prior=prior)
        self.assertEqual(prior, original)
        self.assertEqual(len(bundle["canonicality_revisions"]), 1)
        self.assertNotIn("deleted_observation", bundle)
        self.assertNotIn("overwritten_observation", bundle)

    def test_T25_adapter_uses_exact_provider_neutral_rpc_request_shape(self) -> None:
        transport = FakeTransport()
        build_bundle(transport)
        self.assertEqual(
            transport.calls,
            [
                ("eth_chainId", []),
                ("eth_getBlockByHash", [BLOCK_HASH, True]),
                ("eth_getBlockReceipts", [BLOCK_HASH]),
                ("debug_traceBlockByHash", [BLOCK_HASH, {"tracer": "callTracer"}]),
                ("eth_getBlockByNumber", ["finalized", False]),
            ],
        )

    def test_T26_schema_is_versioned_zero_capable_and_complete_only(self) -> None:
        schema = json.loads((ROOT / "schema/raw-chain-transfer-physical-block-bundle-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], BUNDLE_SCHEMA_VERSION)
        self.assertEqual(schema["properties"]["capability_id"]["const"], CAPABILITY_ID)
        self.assertEqual(schema["properties"]["observations"]["minItems"], 0)
        self.assertTrue(schema["$defs"]["coverage"]["properties"]["complete"]["const"])
        self.assertEqual(schema["properties"]["parser_policy_revision"]["const"], PARSER_POLICY_REVISION)

    def test_N01_wrong_chain_id_rejected(self) -> None:
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(FakeTransport(chain_id="0x2"))
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("INVALID_SOURCE_EVIDENCE", "CHAIN_ID_MISMATCH"))

    def test_N02_block_hash_mismatch_rejected_as_coverage_gap(self) -> None:
        transport = FakeTransport(block_hash=OTHER_BLOCK_HASH)
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport, block_ref=BLOCK_HASH)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "BLOCK_BODY_HASH_MISMATCH"))

    def test_N03_missing_receipt_is_coverage_gap(self) -> None:
        transport = FakeTransport(transactions=[TX1], receipts=[], traces=[{"txHash": TX1, "result": base_trace()}])
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual(ctx.exception.classification, "COVERAGE_GAP")
        self.assertEqual(ctx.exception.code, "RECEIPT_TRANSACTION_SET_MISMATCH")

    def test_N04_extra_receipt_is_coverage_gap(self) -> None:
        transport = FakeTransport(
            transactions=[TX1],
            receipts=[make_receipt(TX1), make_receipt(TX2)],
            traces=[{"txHash": TX1, "result": base_trace()}],
        )
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual(ctx.exception.classification, "COVERAGE_GAP")
        self.assertEqual(ctx.exception.code, "RECEIPT_TRANSACTION_SET_MISMATCH")

    def test_N05_receipt_block_hash_mismatch_is_coverage_gap(self) -> None:
        transport = FakeTransport(
            transactions=[TX1],
            receipts=[make_receipt(TX1, block_hash=OTHER_BLOCK_HASH)],
            traces=[{"txHash": TX1, "result": base_trace()}],
        )
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "RECEIPT_BLOCK_HASH_MISMATCH"))

    def test_N06_missing_trace_is_coverage_gap(self) -> None:
        transport = FakeTransport(transactions=[TX1], receipts=[make_receipt(TX1)], traces=[])
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "TRACE_TRANSACTION_COUNT_MISMATCH"))

    def test_N07_malformed_trace_is_coverage_gap(self) -> None:
        malformed = {"type": "CALL", "from": A1, "to": A2, "value": "0x0", "calls": {}}
        transport = one_tx_transport(trace=malformed)
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "TRACE_CALL_TREE_INVALID"))

    def test_N08_transport_timeout_is_provider_unavailable(self) -> None:
        transport = FakeTransport(failures={"eth_chainId": TimeoutError("fixture timeout")})
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual(ctx.exception.classification, "PROVIDER_UNAVAILABLE")

    def test_N09_rate_limit_rpc_error_is_provider_unavailable(self) -> None:
        transport = FakeTransport(failures={"eth_chainId": {"code": -32005, "message": "rate limit exceeded"}})
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("PROVIDER_UNAVAILABLE", "RPC_PROVIDER_UNAVAILABLE"))

    def test_N10_incomplete_components_with_no_transfers_is_not_proven_zero(self) -> None:
        transport = FakeTransport(transactions=[TX1], receipts=[make_receipt(TX1)], traces=[])
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual(ctx.exception.classification, "COVERAGE_GAP")
        self.assertNotEqual(ctx.exception.code, "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")

    def test_N11_unsupported_transfer_shaped_log_is_not_zero_evidence(self) -> None:
        malformed = make_log(TRANSFER_TOPIC, topics=[topic_address(A1)], data="0x" + word(1))
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_bundle(one_tx_transport(logs=[malformed]))
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "NOT_COVERED_NOT_ZERO"))

    def test_N12_duplicate_logical_identity_with_conflicting_bytes_rejected(self) -> None:
        first = transfer_log_erc20(value=1, log_index=0)
        second = transfer_log_erc20(value=2, log_index=0)
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_bundle(one_tx_transport(logs=[first, second]))
        self.assertEqual(ctx.exception.code, "DUPLICATE_LOGICAL_IDENTITY_CONFLICT")

    def test_N13_provider_label_cannot_alter_transfer_identity(self) -> None:
        a = build_bundle(one_tx_transport(trace=base_trace(value=4), provider_label="provider-a"))
        b = build_bundle(one_tx_transport(trace=base_trace(value=4), provider_label="provider-b"))
        self.assertEqual(a["observations"][0]["transfer_identity"], b["observations"][0]["transfer_identity"])
        self.assertNotIn("provider-a", json.dumps(a))
        self.assertNotIn("provider-b", json.dumps(b))

    def test_N14_observation_known_at_cannot_alter_transfer_identity(self) -> None:
        a = build_bundle(one_tx_transport(trace=base_trace(value=4)), known_at="2026-09-10T12:00:00Z")
        b = build_bundle(one_tx_transport(trace=base_trace(value=4)), known_at="2026-09-10T13:00:00Z")
        self.assertEqual(a["observations"][0]["transfer_identity"], b["observations"][0]["transfer_identity"])
        self.assertEqual(a["observations"][0]["observation_id"], b["observations"][0]["observation_id"])

    def test_N15_storage_execution_metadata_cannot_enter_identity_api(self) -> None:
        parameters = set(inspect.signature(derive_transfer_identity).parameters)
        forbidden_parameter_fragments = ("provider", "storage", "bucket", "filesystem", "github", "workflow", "run_id", "queue", "scheduler")
        self.assertFalse(any(fragment in name for name in parameters for fragment in forbidden_parameter_fragments))
        with self.assertRaises(TypeError):
            derive_transfer_identity(
                chain_id="1",
                transaction_hash=TX1,
                identity_kind="NATIVE_ETH_CALL",
                trace_index="0",
                storage_backend="not-allowed",  # type: ignore[call-arg]
            )

    def test_N16_entity_whale_exchange_usd_output_is_absent_everywhere(self) -> None:
        bundle = build_bundle(one_tx_transport(logs=[transfer_log_erc20(value=3)]))
        schema = json.loads((ROOT / "schema/raw-chain-transfer-physical-block-bundle-v1.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(FORBIDDEN.intersection(collect_keys(bundle)))
        self.assertFalse(FORBIDDEN.intersection(collect_keys(schema)))
        serialized = json.dumps(bundle, sort_keys=True).lower()
        self.assertNotIn("alchemy", serialized)
        self.assertNotIn("quicknode", serialized)
        self.assertNotIn("github", serialized)
        self.assertNotIn("bucket", serialized)
        self.assertNotIn("filesystem", serialized)
        self.assertNotIn("database", serialized)

    def test_T27_staticcall_and_delegatecall_are_not_independent_value_transfers(self) -> None:
        calls = [
            {"type": "STATICCALL", "from": A1, "to": A2, "value": "0x5", "calls": []},
            {"type": "DELEGATECALL", "from": A1, "to": A3, "value": "0x6", "calls": []},
        ]
        bundle = build_bundle(one_tx_transport(trace=base_trace(calls=calls)))
        self.assertEqual(bundle["observations"], [])
        self.assertEqual(bundle["coverage"]["zero_event_classification"], "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")

    def test_T28_zero_address_semantics_are_preserved(self) -> None:
        zero = "0x" + "00" * 20
        row = build_bundle(one_tx_transport(logs=[transfer_log_erc20(source=zero, destination=A2)]))["observations"][0]
        self.assertEqual(row["source_address"], zero)

    def test_T29_parser_policy_revision_is_in_coverage_key(self) -> None:
        bundle = build_bundle(FakeTransport())
        self.assertEqual(bundle["parser_policy_revision"], PARSER_POLICY_REVISION)
        self.assertEqual(bundle["coverage"]["key"]["parser_policy_revision"], PARSER_POLICY_REVISION)

    def test_N17_trace_transaction_position_mismatch_is_coverage_gap(self) -> None:
        transport = FakeTransport(
            transactions=[TX1],
            receipts=[make_receipt(TX1)],
            traces=[{"txHash": TX2, "result": base_trace()}],
        )
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "TRACE_TRANSACTION_POSITION_MISMATCH"))

    def test_N18_receipt_trace_success_mismatch_is_coverage_gap(self) -> None:
        transport = one_tx_transport(trace=base_trace(error="execution reverted"), status="0x1")
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "RECEIPT_TRACE_SUCCESS_MISMATCH"))

    def test_N19_unknown_value_bearing_trace_frame_is_not_zero(self) -> None:
        trace = {"type": "UNKNOWN_CALL", "from": A1, "to": A2, "value": "0x1", "calls": []}
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_bundle(one_tx_transport(trace=trace))
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "UNSUPPORTED_VALUE_BEARING_TRACE_FRAME"))

    def test_N20_finalized_same_height_wrong_hash_rejected(self) -> None:
        transport = FakeTransport(finalized={"number": "0x64", "hash": OTHER_BLOCK_HASH})
        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(transport)
        self.assertEqual(ctx.exception.code, "FINALIZED_BLOCK_HASH_MISMATCH")

    def test_N21_malformed_rpc_response_rejected_without_bundle(self) -> None:
        class BadTransport(FakeTransport):
            def request(self, method: str, params: list[Any]) -> dict[str, Any]:
                self.calls.append((method, deepcopy(params)))
                if method == "eth_chainId":
                    return {"jsonrpc": "2.0", "id": 1}
                return super().request(method, params)

        with self.assertRaises(EthereumRawTransferRpcError) as ctx:
            build_bundle(BadTransport())
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("INVALID_SOURCE_EVIDENCE", "RPC_RESULT_MISSING"))


    def test_T30_provider_port_returns_source_components_and_core_builds_bundle(self) -> None:
        transport = one_tx_transport(trace=base_trace(value=3))
        source = EthereumJsonRpcProviderAdapter(transport).fetch_block_bundle(
            "1", BLOCK_HASH, observation_known_at=KNOWN_AT
        )
        self.assertIn("block_body", source)
        self.assertIn("receipts", source)
        self.assertIn("traces", source)
        self.assertIn("component_evidence", source)
        self.assertNotIn("observations", source)
        bundle = RawTransferCollectionCore(EthereumJsonRpcProviderAdapter(one_tx_transport(trace=base_trace(value=3)))).collect_block(
            "1", BLOCK_HASH, observation_known_at=KNOWN_AT
        )
        self.assertEqual(len(bundle["observations"]), 1)

    def test_T31_core_derives_finality_and_source_provenance_from_factual_source(self) -> None:
        transport = FakeTransport(finalized={"number": "0x64", "hash": BLOCK_HASH})
        source = EthereumJsonRpcProviderAdapter(transport).fetch_block_bundle("1", BLOCK_HASH, observation_known_at=KNOWN_AT)
        self.assertNotIn("finality", source)
        self.assertNotIn("source_provenance", source)
        bundle = build_physical_block_bundle(source)
        self.assertEqual(bundle["finality"], "FINALIZED")
        self.assertEqual(bundle["source_provenance"]["authority"], "ETHEREUM_JSON_RPC")
        self.assertTrue(bundle["source_provenance"]["evidence_id"].startswith("src-"))

    def test_T32_provider_port_signature_matches_primary_adapter_and_core_owns_reorg_context(self) -> None:
        port = inspect.signature(ProviderPort.fetch_block_bundle)
        adapter = inspect.signature(EthereumJsonRpcProviderAdapter.fetch_block_bundle)
        core = inspect.signature(RawTransferCollectionCore.collect_block)
        self.assertEqual(
            [(name, parameter.kind) for name, parameter in port.parameters.items()],
            [(name, parameter.kind) for name, parameter in adapter.parameters.items()],
        )
        self.assertEqual(list(port.parameters), ["self", "chain_id", "block_ref", "observation_known_at"])
        self.assertNotIn("prior_canonical_block", port.parameters)
        self.assertNotIn("prior_canonical_block", adapter.parameters)
        self.assertIn("prior_canonical_block", core.parameters)
        prior = {"chain_id": "1", "block_height": 100, "block_hash": OTHER_BLOCK_HASH}
        bundle = RawTransferCollectionCore(EthereumJsonRpcProviderAdapter(FakeTransport())).collect_block(
            "1", BLOCK_HASH, observation_known_at=KNOWN_AT, prior_canonical_block=prior
        )
        self.assertEqual(bundle["canonicality_revisions"][0]["previous_canonical_block_hash"], OTHER_BLOCK_HASH)
        self.assertEqual(bundle["canonicality_revisions"][0]["canonical_block_hash"], BLOCK_HASH)

    def test_N22_direct_core_receipt_set_mismatch_cannot_claim_zero(self) -> None:
        provider = EthereumJsonRpcProviderAdapter(one_tx_transport())
        source = dict(provider.fetch_block_bundle("1", BLOCK_HASH, observation_known_at=KNOWN_AT))
        source["receipts"] = [make_receipt(TX2)]
        source["component_evidence"] = deepcopy(source["component_evidence"])
        source["component_evidence"]["ALL_TRANSACTION_RECEIPTS"]["evidence_sha256"] = sha256_canonical_json(source["receipts"])
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_physical_block_bundle(source)
        self.assertEqual(ctx.exception.classification, "COVERAGE_GAP")

    def test_N23_direct_core_trace_binding_mismatch_cannot_claim_zero(self) -> None:
        provider = EthereumJsonRpcProviderAdapter(one_tx_transport())
        source = dict(provider.fetch_block_bundle("1", BLOCK_HASH, observation_known_at=KNOWN_AT))
        source["traces"] = [{"transaction_hash": TX2, "transaction_position": 0, "result": base_trace()}]
        source["component_evidence"] = deepcopy(source["component_evidence"])
        source["component_evidence"]["ALL_TRANSACTION_TRACES"]["evidence_sha256"] = sha256_canonical_json(source["traces"])
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_physical_block_bundle(source)
        self.assertEqual(ctx.exception.classification, "COVERAGE_GAP")

    def test_N25_direct_core_block_body_mismatch_cannot_claim_zero(self) -> None:
        provider = EthereumJsonRpcProviderAdapter(one_tx_transport())
        source = dict(provider.fetch_block_bundle("1", BLOCK_HASH, observation_known_at=KNOWN_AT))
        source["block_body"] = deepcopy(source["block_body"])
        source["block_body"]["hash"] = OTHER_BLOCK_HASH
        source["component_evidence"] = deepcopy(source["component_evidence"])
        source["component_evidence"]["BLOCK_BODY"]["evidence_sha256"] = sha256_canonical_json(source["block_body"])
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_physical_block_bundle(source)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "BLOCK_BODY_HASH_MISMATCH"))

    def test_N24_direct_core_component_digest_mismatch_cannot_claim_zero(self) -> None:
        provider = EthereumJsonRpcProviderAdapter(one_tx_transport())
        source = dict(provider.fetch_block_bundle("1", BLOCK_HASH, observation_known_at=KNOWN_AT))
        source["component_evidence"] = deepcopy(source["component_evidence"])
        source["component_evidence"]["ALL_TRANSACTION_RECEIPTS"]["evidence_sha256"] = "0" * 64
        with self.assertRaises(RawTransferFoundationError) as ctx:
            build_physical_block_bundle(source)
        self.assertEqual((ctx.exception.classification, ctx.exception.code), ("COVERAGE_GAP", "ALL_TRANSACTION_RECEIPTS_EVIDENCE_DIGEST_MISMATCH"))


if __name__ == "__main__":
    unittest.main()
