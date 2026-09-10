from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Protocol, Sequence

from canonical_json import sha256_canonical_json
from raw_chain_transfer_core import (
    ethereum_timestamp_to_utc,
    normalize_address,
    normalize_chain_id,
    normalize_hash,
)


class JsonRpcTransport(Protocol):
    def request(self, method: str, params: Sequence[Any]) -> Mapping[str, Any]: ...


class EthereumRawTransferRpcError(ValueError):
    """Small adapter boundary error with a stable domain-facing classification."""

    def __init__(self, code: str, classification: str) -> None:
        self.code = code
        self.classification = classification
        super().__init__(f"{classification}:{code}")


def _fail(code: str, classification: str = "INVALID_SOURCE_EVIDENCE") -> None:
    raise EthereumRawTransferRpcError(code, classification)


def _require(condition: bool, code: str, classification: str = "INVALID_SOURCE_EVIDENCE") -> None:
    if not condition:
        _fail(code, classification)


def _quantity(value: Any, *, code: str) -> int:
    if isinstance(value, bool) or isinstance(value, float):
        _fail(code)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.startswith(("0x", "0X")):
        try:
            parsed = int(value, 16)
        except ValueError:
            _fail(code)
    elif isinstance(value, str) and value.isdigit():
        parsed = int(value, 10)
    else:
        _fail(code)
    _require(parsed >= 0, code)
    return parsed


def _rpc_error_is_unavailable(error: Mapping[str, Any]) -> bool:
    code = error.get("code")
    message = str(error.get("message", "")).lower()
    return code in {429, -32005, -32016} or "rate" in message or "limit" in message or "unavailable" in message


class EthereumJsonRpcProviderAdapter:
    """Ethereum-specific source adapter over an injected JSON-RPC transport.

    The adapter owns Ethereum request/response validation only. It has no HTTP
    client, endpoint, credential, storage, scheduler, or provider-vendor model.
    """

    def __init__(self, transport: JsonRpcTransport) -> None:
        self._transport = transport

    def _rpc(self, method: str, params: Sequence[Any]) -> Any:
        try:
            response = self._transport.request(method, list(params))
        except (TimeoutError, ConnectionError, OSError) as exc:
            raise EthereumRawTransferRpcError("RPC_TRANSPORT_UNAVAILABLE", "PROVIDER_UNAVAILABLE") from exc
        except EthereumRawTransferRpcError:
            raise
        except Exception as exc:
            raise EthereumRawTransferRpcError("RPC_TRANSPORT_FAILURE", "PROVIDER_UNAVAILABLE") from exc
        _require(isinstance(response, Mapping), "RPC_RESPONSE_NOT_OBJECT")
        if "error" in response and response.get("error") is not None:
            error = response.get("error")
            _require(isinstance(error, Mapping), "RPC_ERROR_SHAPE_INVALID")
            if _rpc_error_is_unavailable(error):
                _fail("RPC_PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE")
            _fail("RPC_ERROR", "PROVIDER_UNAVAILABLE")
        _require("result" in response, "RPC_RESULT_MISSING")
        return response.get("result")

    def _validate_block(self, requested_hash: str, block: Any) -> tuple[dict[str, Any], int, list[str]]:
        _require(isinstance(block, Mapping), "BLOCK_BODY_MISSING", "COVERAGE_GAP")
        normalized_hash = normalize_hash(block.get("hash"), code="BLOCK_HASH_INVALID")
        _require(normalized_hash == requested_hash, "BLOCK_BODY_HASH_MISMATCH", "COVERAGE_GAP")
        block_height = _quantity(block.get("number"), code="BLOCK_NUMBER_INVALID")
        ethereum_timestamp_to_utc(block.get("timestamp"))
        transactions = block.get("transactions")
        _require(isinstance(transactions, list), "BLOCK_TRANSACTIONS_INVALID", "COVERAGE_GAP")
        transaction_hashes: list[str] = []
        for transaction in transactions:
            _require(isinstance(transaction, Mapping), "FULL_TRANSACTION_OBJECT_REQUIRED", "COVERAGE_GAP")
            transaction_hashes.append(normalize_hash(transaction.get("hash"), code="TRANSACTION_HASH_INVALID"))
        _require(len(transaction_hashes) == len(set(transaction_hashes)), "BLOCK_TRANSACTION_DUPLICATE", "COVERAGE_GAP")
        return deepcopy(dict(block)), block_height, transaction_hashes

    def _validate_receipts(
        self,
        receipts: Any,
        *,
        block_hash: str,
        block_height: int,
        transaction_hashes: Sequence[str],
    ) -> list[dict[str, Any]]:
        _require(isinstance(receipts, list), "RECEIPT_SET_MISSING", "COVERAGE_GAP")
        normalized: list[dict[str, Any]] = []
        seen: list[str] = []
        for receipt in receipts:
            _require(isinstance(receipt, Mapping), "RECEIPT_INVALID", "COVERAGE_GAP")
            tx_hash = normalize_hash(receipt.get("transactionHash"), code="RECEIPT_TRANSACTION_HASH_INVALID")
            _require(normalize_hash(receipt.get("blockHash"), code="RECEIPT_BLOCK_HASH_INVALID") == block_hash, "RECEIPT_BLOCK_HASH_MISMATCH", "COVERAGE_GAP")
            _require(_quantity(receipt.get("blockNumber"), code="RECEIPT_BLOCK_NUMBER_INVALID") == block_height, "RECEIPT_BLOCK_NUMBER_MISMATCH", "COVERAGE_GAP")
            logs = receipt.get("logs")
            _require(isinstance(logs, list), "RECEIPT_LOGS_INVALID", "COVERAGE_GAP")
            if "status" in receipt:
                status = _quantity(receipt.get("status"), code="RECEIPT_STATUS_INVALID")
                _require(status in {0, 1}, "RECEIPT_STATUS_INVALID", "COVERAGE_GAP")
                _require(not (status == 0 and logs), "FAILED_RECEIPT_LOGS_PRESENT", "COVERAGE_GAP")
            for log in logs:
                _require(isinstance(log, Mapping), "RECEIPT_LOG_INVALID", "COVERAGE_GAP")
                if log.get("blockHash") is not None:
                    _require(normalize_hash(log.get("blockHash"), code="LOG_BLOCK_HASH_INVALID") == block_hash, "LOG_BLOCK_HASH_MISMATCH", "COVERAGE_GAP")
                if log.get("transactionHash") is not None:
                    _require(normalize_hash(log.get("transactionHash"), code="LOG_TRANSACTION_HASH_INVALID") == tx_hash, "LOG_TRANSACTION_HASH_MISMATCH", "COVERAGE_GAP")
                if log.get("address") is not None:
                    normalize_address(log.get("address"))
            seen.append(tx_hash)
            normalized.append(deepcopy(dict(receipt)))
        _require(len(seen) == len(set(seen)), "RECEIPT_TRANSACTION_DUPLICATE", "COVERAGE_GAP")
        _require(set(seen) == set(transaction_hashes), "RECEIPT_TRANSACTION_SET_MISMATCH", "COVERAGE_GAP")
        return normalized

    def _validate_trace_frame(self, frame: Any) -> None:
        _require(isinstance(frame, Mapping), "TRACE_FRAME_INVALID", "COVERAGE_GAP")
        frame_type = frame.get("type")
        _require(isinstance(frame_type, str) and frame_type, "TRACE_FRAME_TYPE_INVALID", "COVERAGE_GAP")
        calls = frame.get("calls", [])
        _require(isinstance(calls, list), "TRACE_CALL_TREE_INVALID", "COVERAGE_GAP")
        value = frame.get("value", "0x0")
        _quantity(value, code="TRACE_VALUE_INVALID")
        for child in calls:
            self._validate_trace_frame(child)

    def _validate_traces(
        self,
        traces: Any,
        transaction_hashes: Sequence[str],
        receipts: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        _require(isinstance(traces, list), "TRACE_SET_MISSING", "COVERAGE_GAP")
        _require(len(traces) == len(transaction_hashes), "TRACE_TRANSACTION_COUNT_MISMATCH", "COVERAGE_GAP")
        normalized: list[dict[str, Any]] = []
        seen: list[str] = []
        receipt_by_hash = {
            normalize_hash(receipt.get("transactionHash"), code="RECEIPT_TRANSACTION_HASH_INVALID"): receipt
            for receipt in receipts
        }
        for position, (trace, expected_tx_hash) in enumerate(zip(traces, transaction_hashes, strict=True)):
            _require(isinstance(trace, Mapping), "TRACE_ENTRY_INVALID", "COVERAGE_GAP")
            supplied_tx_hash = trace.get("txHash")
            if supplied_tx_hash is None:
                tx_hash = expected_tx_hash
            else:
                tx_hash = normalize_hash(supplied_tx_hash, code="TRACE_TRANSACTION_HASH_INVALID")
                _require(tx_hash == expected_tx_hash, "TRACE_TRANSACTION_POSITION_MISMATCH", "COVERAGE_GAP")
            result = trace.get("result")
            self._validate_trace_frame(result)
            receipt = receipt_by_hash[tx_hash]
            if "status" in receipt:
                receipt_success = _quantity(receipt.get("status"), code="RECEIPT_STATUS_INVALID") == 1
                trace_success = result.get("error") in (None, "")
                _require(receipt_success == trace_success, "RECEIPT_TRACE_SUCCESS_MISMATCH", "COVERAGE_GAP")
            seen.append(tx_hash)
            normalized.append({"transaction_hash": tx_hash, "transaction_position": position, "result": deepcopy(result)})
        _require(len(seen) == len(set(seen)), "TRACE_TRANSACTION_DUPLICATE", "COVERAGE_GAP")
        _require(list(seen) == list(transaction_hashes), "TRACE_TRANSACTION_SET_MISMATCH", "COVERAGE_GAP")
        return normalized

    def _finalized_evidence(self, result: Any, *, block_height: int, block_hash: str) -> Mapping[str, Any] | None:
        if result is None:
            return None
        _require(isinstance(result, Mapping), "FINALIZED_BLOCK_RESPONSE_INVALID")
        finalized_height = _quantity(result.get("number"), code="FINALIZED_BLOCK_NUMBER_INVALID")
        finalized_hash = normalize_hash(result.get("hash"), code="FINALIZED_BLOCK_HASH_INVALID")
        if finalized_height == block_height:
            _require(finalized_hash == block_hash, "FINALIZED_BLOCK_HASH_MISMATCH")
            return {"block_height": block_height, "block_hash": block_hash}
        return {"block_height": finalized_height, "block_hash": finalized_hash}

    def fetch_block_bundle(
        self,
        chain_id: str,
        block_ref: str,
        *,
        observation_known_at: str,
    ) -> Mapping[str, Any]:
        expected_chain_id = normalize_chain_id(chain_id)
        requested_hash = normalize_hash(block_ref, code="REQUESTED_BLOCK_HASH_INVALID")

        observed_chain_id = normalize_chain_id(self._rpc("eth_chainId", []))
        _require(observed_chain_id == expected_chain_id, "CHAIN_ID_MISMATCH")

        block_raw = self._rpc("eth_getBlockByHash", [requested_hash, True])
        block, block_height, transaction_hashes = self._validate_block(requested_hash, block_raw)

        receipts_raw = self._rpc("eth_getBlockReceipts", [requested_hash])
        receipts = self._validate_receipts(
            receipts_raw,
            block_hash=requested_hash,
            block_height=block_height,
            transaction_hashes=transaction_hashes,
        )

        traces_raw = self._rpc("debug_traceBlockByHash", [requested_hash, {"tracer": "callTracer"}])
        traces = self._validate_traces(traces_raw, transaction_hashes, receipts)

        finalized_raw = self._rpc("eth_getBlockByNumber", ["finalized", False])
        finalized_evidence = self._finalized_evidence(
            finalized_raw,
            block_height=block_height,
            block_hash=requested_hash,
        )
        block_digest = sha256_canonical_json(block)
        receipts_digest = sha256_canonical_json(receipts)
        traces_digest = sha256_canonical_json(traces)
        source = {
            "chain_id": expected_chain_id,
            "block_height": block_height,
            "block_hash": requested_hash,
            "event_time": ethereum_timestamp_to_utc(block.get("timestamp")),
            "observation_known_at": observation_known_at,
            "source_authority": "ETHEREUM_JSON_RPC",
            "finalized_block_evidence": deepcopy(finalized_evidence),
            "block_body": deepcopy(block),
            "transaction_hashes": list(transaction_hashes),
            "receipts": receipts,
            "traces": traces,
            "component_evidence": {
                "BLOCK_BODY": {"verified": True, "evidence_sha256": block_digest},
                "ALL_TRANSACTION_RECEIPTS": {"verified": True, "evidence_sha256": receipts_digest},
                "ALL_TRANSACTION_TRACES": {"verified": True, "evidence_sha256": traces_digest},
            },
        }
        return source
