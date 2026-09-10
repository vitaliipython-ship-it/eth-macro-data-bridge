from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from canonical_json import canonical_json_bytes, sha256_canonical_json

CAPABILITY_ID = "blockchain.raw-transfer-facts"
PARSER_POLICY_REVISION = "ethereum-raw-transfer-parser/1.0.0"
BUNDLE_SCHEMA_VERSION = "raw-chain-transfer-physical-block-bundle/1.0.0"
CHAIN_REVISION_SCHEMA_VERSION = "chain-canonicality-revision/1.0.0"
CHAIN_REORG_MODEL = "APPEND_ONLY_VERSIONED_CANONICALITY_STATE_WITH_PIT_CUTOFF"
COVERAGE_COMPONENTS = (
    "BLOCK_BODY",
    "ALL_TRANSACTION_RECEIPTS",
    "ALL_TRANSACTION_TRACES",
    "DECLARED_TOKEN_EVENT_PARSERS",
)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ERC1155_SINGLE_TOPIC = "0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62"
ERC1155_BATCH_TOPIC = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"


class RawTransferFoundationError(ValueError):
    """Small fail-closed domain error with a stable failure classification."""

    def __init__(self, code: str, classification: str = "INVALID_SOURCE_EVIDENCE") -> None:
        self.code = code
        self.classification = classification
        super().__init__(f"{classification}:{code}")


class ProviderPort(Protocol):
    def fetch_block_bundle(
        self,
        chain_id: str,
        block_ref: str,
        *,
        observation_known_at: str,
        prior_canonical_block: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...


class PublicationPort(Protocol):
    def publish(
        self,
        bundle_bytes: bytes,
        content_identity: str,
        provenance: Mapping[str, str],
    ) -> Mapping[str, Any]: ...


def _require(condition: bool, code: str, classification: str = "INVALID_SOURCE_EVIDENCE") -> None:
    if not condition:
        raise RawTransferFoundationError(code, classification)


def normalize_chain_id(value: Any) -> str:
    if isinstance(value, bool):
        raise RawTransferFoundationError("CHAIN_ID_INVALID")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value, 16) if value.startswith(("0x", "0X")) else int(value, 10)
        except ValueError:
            raise RawTransferFoundationError("CHAIN_ID_INVALID") from None
    else:
        raise RawTransferFoundationError("CHAIN_ID_INVALID")
    _require(parsed >= 0, "CHAIN_ID_INVALID")
    return str(parsed)


def normalize_hash(value: Any, *, code: str = "HASH_INVALID") -> str:
    _require(isinstance(value, str), code)
    raw = value[2:] if value.startswith(("0x", "0X")) else value
    _require(len(raw) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in raw), code)
    return "0x" + raw.lower()


def normalize_address(value: Any) -> str:
    _require(isinstance(value, str), "ADDRESS_INVALID")
    raw = value[2:] if value.startswith(("0x", "0X")) else value
    _require(len(raw) == 40 and all(ch in "0123456789abcdefABCDEF" for ch in raw), "ADDRESS_INVALID")
    return "0x" + raw.lower()


def _normalize_utc(value: Any, *, code: str) -> str:
    _require(isinstance(value, str) and value, code)
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise RawTransferFoundationError(code) from None
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, code)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ethereum_timestamp_to_utc(value: Any) -> str:
    seconds = _uint(value, code="BLOCK_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise RawTransferFoundationError("BLOCK_TIMESTAMP_INVALID") from None
    return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _uint(value: Any, *, code: str) -> int:
    if isinstance(value, bool) or isinstance(value, float):
        raise RawTransferFoundationError(code)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.startswith(("0x", "0X")):
        try:
            parsed = int(value, 16)
        except ValueError:
            raise RawTransferFoundationError(code) from None
    elif isinstance(value, str) and value.isdigit():
        parsed = int(value, 10)
    else:
        raise RawTransferFoundationError(code)
    _require(parsed >= 0, code)
    return parsed


def _hex_bytes(value: Any, *, code: str) -> bytes:
    _require(isinstance(value, str) and value.startswith(("0x", "0X")), code)
    raw = value[2:]
    _require(len(raw) % 2 == 0 and all(ch in "0123456789abcdefABCDEF" for ch in raw), code)
    return bytes.fromhex(raw)


def _topic_address(value: Any) -> str:
    raw = _hex_bytes(value, code="LOG_TOPIC_ADDRESS_INVALID")
    _require(len(raw) == 32 and raw[:12] == b"\x00" * 12, "LOG_TOPIC_ADDRESS_INVALID")
    return normalize_address(raw[-20:].hex())


def _word_uint(value: bytes, offset: int, *, code: str) -> int:
    _require(offset >= 0 and offset + 32 <= len(value), code)
    return int.from_bytes(value[offset : offset + 32], "big")


def _abi_uint_arrays(data: Any) -> tuple[list[int], list[int]]:
    raw = _hex_bytes(data, code="ERC1155_BATCH_DATA_INVALID")
    _require(len(raw) >= 64 and len(raw) % 32 == 0, "ERC1155_BATCH_DATA_INVALID")
    first_offset = _word_uint(raw, 0, code="ERC1155_BATCH_DATA_INVALID")
    second_offset = _word_uint(raw, 32, code="ERC1155_BATCH_DATA_INVALID")
    _require(first_offset % 32 == 0 and second_offset % 32 == 0, "ERC1155_BATCH_DATA_INVALID")

    def decode(offset: int) -> list[int]:
        count = _word_uint(raw, offset, code="ERC1155_BATCH_DATA_INVALID")
        start = offset + 32
        end = start + count * 32
        _require(end <= len(raw), "ERC1155_BATCH_DATA_INVALID")
        return [int.from_bytes(raw[pos : pos + 32], "big") for pos in range(start, end, 32)]

    ids = decode(first_offset)
    values = decode(second_offset)
    _require(len(ids) == len(values), "ERC1155_BATCH_LENGTH_MISMATCH")
    return ids, values


def derive_transfer_identity(
    *,
    chain_id: Any,
    transaction_hash: Any,
    identity_kind: str,
    trace_index: str | None = None,
    log_index: int | None = None,
    transfer_index: int | None = None,
) -> str:
    chain = normalize_chain_id(chain_id)
    tx_hash = normalize_hash(transaction_hash, code="TRANSACTION_HASH_INVALID")
    _require(isinstance(identity_kind, str) and identity_kind, "TRANSFER_IDENTITY_KIND_INVALID")
    position_count = int(trace_index is not None) + int(log_index is not None)
    _require(position_count == 1, "TRANSFER_POSITION_IDENTITY_INVALID")
    if trace_index is not None:
        _require(isinstance(trace_index, str) and trace_index, "TRACE_INDEX_INVALID")
    if log_index is not None:
        _require(isinstance(log_index, int) and not isinstance(log_index, bool) and log_index >= 0, "LOG_INDEX_INVALID")
    if transfer_index is not None:
        _require(isinstance(transfer_index, int) and not isinstance(transfer_index, bool) and transfer_index >= 0, "TRANSFER_INDEX_INVALID")
    material = {
        "capability_id": CAPABILITY_ID,
        "chain_id": chain,
        "identity_kind": identity_kind,
        "transaction_hash": tx_hash,
        "trace_index": trace_index,
        "log_index": log_index,
        "transfer_index": transfer_index,
    }
    return "rawtx-" + sha256_canonical_json(material)


def derive_observation_id(
    *,
    chain_id: Any,
    block_height: int,
    block_hash: Any,
    transfer_identity: str,
) -> str:
    _require(isinstance(block_height, int) and not isinstance(block_height, bool) and block_height >= 0, "BLOCK_HEIGHT_INVALID")
    _require(isinstance(transfer_identity, str) and transfer_identity.startswith("rawtx-"), "TRANSFER_IDENTITY_INVALID")
    material = {
        "capability_id": CAPABILITY_ID,
        "chain_id": normalize_chain_id(chain_id),
        "block_height": block_height,
        "block_hash": normalize_hash(block_hash, code="BLOCK_HASH_INVALID"),
        "transfer_identity": transfer_identity,
    }
    return "rawobs-" + sha256_canonical_json(material)


def _native_asset(chain_id: str) -> dict[str, Any]:
    return {"kind": "NATIVE_ASSET", "chain_id": chain_id, "asset": "ETH"}


def _token_asset(chain_id: str, contract_address: str, standard: str, token_id: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": "TOKEN_ASSET",
        "chain_id": chain_id,
        "contract_address": normalize_address(contract_address),
        "standard": standard,
    }
    if token_id is not None:
        result["token_id"] = str(token_id)
    return result


def _observation(
    source: Mapping[str, Any],
    *,
    identity_kind: str,
    transaction_hash: str,
    source_address: str,
    destination_address: str,
    asset_identity: Mapping[str, Any],
    quantity: int,
    quantity_unit: str,
    trace_index: str | None = None,
    log_index: int | None = None,
    transfer_index: int | None = None,
) -> dict[str, Any]:
    transfer_identity = derive_transfer_identity(
        chain_id=source["chain_id"],
        transaction_hash=transaction_hash,
        identity_kind=identity_kind,
        trace_index=trace_index,
        log_index=log_index,
        transfer_index=transfer_index,
    )
    observation_id = derive_observation_id(
        chain_id=source["chain_id"],
        block_height=source["block_height"],
        block_hash=source["block_hash"],
        transfer_identity=transfer_identity,
    )
    row: dict[str, Any] = {
        "observation_id": observation_id,
        "chain_id": source["chain_id"],
        "transaction_hash": normalize_hash(transaction_hash, code="TRANSACTION_HASH_INVALID"),
        "transfer_identity": transfer_identity,
        "block_height": source["block_height"],
        "block_hash": source["block_hash"],
        "event_time": source["event_time"],
        "observation_known_at": source["observation_known_at"],
        "source_address": normalize_address(source_address),
        "destination_address": normalize_address(destination_address),
        "asset_identity": deepcopy(dict(asset_identity)),
        "native_quantity": str(quantity),
        "native_quantity_unit": quantity_unit,
        "finality": source["finality"],
        "source_provenance": deepcopy(dict(source["source_provenance"])),
    }
    if trace_index is not None:
        row["trace_index"] = trace_index
    if log_index is not None:
        row["log_index"] = log_index
    if transfer_index is not None:
        row["transfer_index"] = transfer_index
    return row


def _walk_trace_frame(
    source: Mapping[str, Any],
    transaction_hash: str,
    frame: Any,
    trace_index: str,
    output: list[dict[str, Any]],
) -> None:
    _require(isinstance(frame, Mapping), "TRACE_FRAME_INVALID", "COVERAGE_GAP")
    frame_type = frame.get("type")
    _require(isinstance(frame_type, str) and frame_type, "TRACE_FRAME_TYPE_INVALID", "COVERAGE_GAP")
    calls = frame.get("calls", [])
    _require(isinstance(calls, list), "TRACE_CALL_TREE_INVALID", "COVERAGE_GAP")
    error = frame.get("error")
    if error not in (None, ""):
        return
    value = _uint(frame.get("value", "0x0"), code="TRACE_VALUE_INVALID")
    transfer_types = {"CALL", "CREATE", "CREATE2", "SELFDESTRUCT"}
    no_independent_transfer_types = {"STATICCALL", "DELEGATECALL"}
    if value > 0:
        if frame_type in transfer_types:
            _require("from" in frame and "to" in frame, "TRACE_VALUE_ENDPOINTS_MISSING", "COVERAGE_GAP")
            output.append(
                _observation(
                    source,
                    identity_kind=f"NATIVE_ETH_{frame_type}",
                    transaction_hash=transaction_hash,
                    source_address=frame["from"],
                    destination_address=frame["to"],
                    asset_identity=_native_asset(source["chain_id"]),
                    quantity=value,
                    quantity_unit="wei",
                    trace_index=trace_index,
                )
            )
        elif frame_type not in no_independent_transfer_types:
            raise RawTransferFoundationError("UNSUPPORTED_VALUE_BEARING_TRACE_FRAME", "COVERAGE_GAP")
    for index, child in enumerate(calls):
        _walk_trace_frame(source, transaction_hash, child, f"{trace_index}.{index}", output)


def normalize_native_trace_transfers(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    traces = source.get("traces")
    _require(isinstance(traces, list), "TRACE_SET_INVALID", "COVERAGE_GAP")
    output: list[dict[str, Any]] = []
    for item in traces:
        _require(isinstance(item, Mapping), "TRACE_ENTRY_INVALID", "COVERAGE_GAP")
        tx_hash = normalize_hash(item.get("transaction_hash"), code="TRACE_TRANSACTION_HASH_INVALID")
        _walk_trace_frame(source, tx_hash, item.get("result"), "0", output)
    return output


def _receipt_success(receipt: Mapping[str, Any]) -> bool:
    if "status" in receipt:
        return _uint(receipt["status"], code="RECEIPT_STATUS_INVALID") == 1
    root = receipt.get("root")
    _require(root is not None, "RECEIPT_SUCCESS_EVIDENCE_MISSING", "COVERAGE_GAP")
    normalize_hash(root, code="RECEIPT_ROOT_INVALID")
    return True


def _token_log_observations(source: Mapping[str, Any], receipt: Mapping[str, Any], log: Any) -> list[dict[str, Any]]:
    _require(isinstance(log, Mapping), "LOG_INVALID", "COVERAGE_GAP")
    _require(log.get("removed") in (None, False), "REMOVED_LOG_IN_EXACT_BLOCK", "COVERAGE_GAP")
    tx_hash = normalize_hash(log.get("transactionHash"), code="LOG_TRANSACTION_HASH_INVALID")
    _require(tx_hash == normalize_hash(receipt.get("transactionHash"), code="RECEIPT_TRANSACTION_HASH_INVALID"), "LOG_RECEIPT_TRANSACTION_MISMATCH", "COVERAGE_GAP")
    _require(normalize_hash(log.get("blockHash"), code="LOG_BLOCK_HASH_INVALID") == source["block_hash"], "LOG_BLOCK_HASH_MISMATCH", "COVERAGE_GAP")
    log_index = _uint(log.get("logIndex"), code="LOG_INDEX_INVALID")
    contract_address = normalize_address(log.get("address"))
    topics = log.get("topics")
    _require(isinstance(topics, list) and topics, "LOG_TOPICS_INVALID", "COVERAGE_GAP")
    topic0 = normalize_hash(topics[0], code="LOG_TOPIC0_INVALID")

    if topic0 == TRANSFER_TOPIC:
        if len(topics) == 3:
            raw = _hex_bytes(log.get("data"), code="ERC20_TRANSFER_DATA_INVALID")
            _require(len(raw) == 32, "NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")
            return [
                _observation(
                    source,
                    identity_kind="ERC20_TRANSFER",
                    transaction_hash=tx_hash,
                    source_address=_topic_address(topics[1]),
                    destination_address=_topic_address(topics[2]),
                    asset_identity=_token_asset(source["chain_id"], contract_address, "ERC20"),
                    quantity=int.from_bytes(raw, "big"),
                    quantity_unit="token_native_integer",
                    log_index=log_index,
                )
            ]
        if len(topics) == 4:
            raw = _hex_bytes(log.get("data", "0x"), code="ERC721_TRANSFER_DATA_INVALID")
            _require(len(raw) == 0, "NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")
            token_id = _uint(topics[3], code="ERC721_TOKEN_ID_INVALID")
            return [
                _observation(
                    source,
                    identity_kind="ERC721_TRANSFER",
                    transaction_hash=tx_hash,
                    source_address=_topic_address(topics[1]),
                    destination_address=_topic_address(topics[2]),
                    asset_identity=_token_asset(source["chain_id"], contract_address, "ERC721", token_id),
                    quantity=1,
                    quantity_unit="token_native_integer",
                    log_index=log_index,
                )
            ]
        raise RawTransferFoundationError("NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")

    if topic0 == ERC1155_SINGLE_TOPIC:
        _require(len(topics) == 4, "NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")
        raw = _hex_bytes(log.get("data"), code="ERC1155_SINGLE_DATA_INVALID")
        _require(len(raw) == 64, "NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")
        token_id = int.from_bytes(raw[:32], "big")
        value = int.from_bytes(raw[32:], "big")
        return [
            _observation(
                source,
                identity_kind="ERC1155_TRANSFER_SINGLE",
                transaction_hash=tx_hash,
                source_address=_topic_address(topics[2]),
                destination_address=_topic_address(topics[3]),
                asset_identity=_token_asset(source["chain_id"], contract_address, "ERC1155", token_id),
                quantity=value,
                quantity_unit="token_native_integer",
                log_index=log_index,
            )
        ]

    if topic0 == ERC1155_BATCH_TOPIC:
        _require(len(topics) == 4, "NOT_COVERED_NOT_ZERO", "COVERAGE_GAP")
        ids, values = _abi_uint_arrays(log.get("data"))
        result: list[dict[str, Any]] = []
        for transfer_index, (token_id, value) in enumerate(zip(ids, values, strict=True)):
            result.append(
                _observation(
                    source,
                    identity_kind="ERC1155_TRANSFER_BATCH",
                    transaction_hash=tx_hash,
                    source_address=_topic_address(topics[2]),
                    destination_address=_topic_address(topics[3]),
                    asset_identity=_token_asset(source["chain_id"], contract_address, "ERC1155", token_id),
                    quantity=value,
                    quantity_unit="token_native_integer",
                    log_index=log_index,
                    transfer_index=transfer_index,
                )
            )
        return result

    return []


def normalize_token_transfers(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    receipts = source.get("receipts")
    _require(isinstance(receipts, list), "RECEIPT_SET_INVALID", "COVERAGE_GAP")
    output: list[dict[str, Any]] = []
    for receipt in receipts:
        _require(isinstance(receipt, Mapping), "RECEIPT_INVALID", "COVERAGE_GAP")
        logs = receipt.get("logs")
        _require(isinstance(logs, list), "RECEIPT_LOGS_INVALID", "COVERAGE_GAP")
        if not _receipt_success(receipt):
            continue
        for log in logs:
            output.extend(_token_log_observations(source, receipt, log))
    return output


def _deduplicate_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[str, dict[str, Any]] = {}
    for raw in observations:
        row = deepcopy(dict(raw))
        identity = row["transfer_identity"]
        previous = by_identity.get(identity)
        if previous is None:
            by_identity[identity] = row
        elif canonical_json_bytes(previous) != canonical_json_bytes(row):
            raise RawTransferFoundationError("DUPLICATE_LOGICAL_IDENTITY_CONFLICT")
    return sorted(
        by_identity.values(),
        key=lambda row: (
            row["transaction_hash"],
            row.get("log_index", -1),
            row.get("trace_index", ""),
            row.get("transfer_index", -1),
            row["transfer_identity"],
        ),
    )


def classify_finality(
    *,
    block_height: int,
    block_hash: Any,
    finalized_block_evidence: Mapping[str, Any] | None,
) -> str:
    normalize_hash(block_hash, code="BLOCK_HASH_INVALID")
    _require(isinstance(block_height, int) and not isinstance(block_height, bool) and block_height >= 0, "BLOCK_HEIGHT_INVALID")
    if finalized_block_evidence is None:
        return "PROVISIONAL"
    _require(isinstance(finalized_block_evidence, Mapping), "FINALIZED_EVIDENCE_INVALID")
    evidence_height = finalized_block_evidence.get("block_height")
    evidence_hash = finalized_block_evidence.get("block_hash")
    _require(isinstance(evidence_height, int) and not isinstance(evidence_height, bool) and evidence_height >= 0, "FINALIZED_EVIDENCE_HEIGHT_INVALID")
    evidence_hash = normalize_hash(evidence_hash, code="FINALIZED_EVIDENCE_HASH_INVALID")
    if evidence_height == block_height:
        _require(evidence_hash == normalize_hash(block_hash, code="BLOCK_HASH_INVALID"), "FINALIZED_EVIDENCE_HASH_MISMATCH")
        return "FINALIZED"
    return "PROVISIONAL"


def build_canonicality_revision(
    *,
    chain_id: str,
    block_height: int,
    previous_canonical_block_hash: str,
    canonical_block_hash: str,
    revision_known_at: str,
    source_provenance: Mapping[str, str],
) -> dict[str, Any] | None:
    previous_hash = normalize_hash(previous_canonical_block_hash, code="PREVIOUS_CANONICAL_BLOCK_HASH_INVALID")
    current_hash = normalize_hash(canonical_block_hash, code="CANONICAL_BLOCK_HASH_INVALID")
    if previous_hash == current_hash:
        return None
    known_at = _normalize_utc(revision_known_at, code="REVISION_KNOWN_AT_INVALID")
    provenance = _normalize_provenance(source_provenance)
    material = {
        "schema_version": CHAIN_REVISION_SCHEMA_VERSION,
        "chain_id": normalize_chain_id(chain_id),
        "block_height": block_height,
        "previous_canonical_block_hash": previous_hash,
        "canonical_block_hash": current_hash,
        "revision_known_at": known_at,
        "source_provenance": provenance,
    }
    revision = deepcopy(material)
    revision["revision_id"] = "chainrev-" + sha256_canonical_json(material)
    return revision


def _normalize_provenance(value: Mapping[str, Any]) -> dict[str, str]:
    _require(isinstance(value, Mapping), "SOURCE_PROVENANCE_INVALID")
    _require(set(value) == {"authority", "evidence_id"}, "SOURCE_PROVENANCE_SHAPE_INVALID")
    authority = value.get("authority")
    evidence_id = value.get("evidence_id")
    _require(isinstance(authority, str) and authority, "SOURCE_PROVENANCE_AUTHORITY_INVALID")
    _require(isinstance(evidence_id, str) and evidence_id, "SOURCE_PROVENANCE_EVIDENCE_ID_INVALID")
    return {"authority": authority, "evidence_id": evidence_id}


def _normalize_complete_source(source: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(source, Mapping), "SOURCE_BUNDLE_INVALID")
    chain_id = normalize_chain_id(source.get("chain_id"))
    block_height = source.get("block_height")
    _require(isinstance(block_height, int) and not isinstance(block_height, bool) and block_height >= 0, "BLOCK_HEIGHT_INVALID")
    block_hash = normalize_hash(source.get("block_hash"), code="BLOCK_HASH_INVALID")
    event_time = _normalize_utc(source.get("event_time"), code="EVENT_TIME_INVALID")
    known_at = _normalize_utc(source.get("observation_known_at"), code="OBSERVATION_KNOWN_AT_INVALID")
    finality = source.get("finality")
    _require(finality in {"PROVISIONAL", "FINALIZED"}, "FINALITY_INVALID")
    provenance = _normalize_provenance(source.get("source_provenance"))
    tx_hashes = source.get("transaction_hashes")
    _require(isinstance(tx_hashes, list), "TRANSACTION_SET_INVALID", "COVERAGE_GAP")
    tx_hashes = [normalize_hash(item, code="TRANSACTION_HASH_INVALID") for item in tx_hashes]
    _require(len(tx_hashes) == len(set(tx_hashes)), "TRANSACTION_SET_DUPLICATE", "COVERAGE_GAP")
    receipts = source.get("receipts")
    traces = source.get("traces")
    evidence = source.get("component_evidence")
    _require(isinstance(receipts, list), "RECEIPT_SET_INVALID", "COVERAGE_GAP")
    _require(isinstance(traces, list), "TRACE_SET_INVALID", "COVERAGE_GAP")
    _require(isinstance(evidence, Mapping), "SOURCE_COMPONENT_EVIDENCE_INVALID", "COVERAGE_GAP")
    for component in ("BLOCK_BODY", "ALL_TRANSACTION_RECEIPTS", "ALL_TRANSACTION_TRACES"):
        member = evidence.get(component)
        _require(isinstance(member, Mapping) and member.get("verified") is True, f"{component}_NOT_VERIFIED", "COVERAGE_GAP")
        digest = member.get("evidence_sha256")
        _require(isinstance(digest, str) and len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest), f"{component}_EVIDENCE_SHA_INVALID", "COVERAGE_GAP")
    return {
        "chain_id": chain_id,
        "block_height": block_height,
        "block_hash": block_hash,
        "event_time": event_time,
        "observation_known_at": known_at,
        "finality": finality,
        "source_provenance": provenance,
        "transaction_hashes": tx_hashes,
        "receipts": deepcopy(receipts),
        "traces": deepcopy(traces),
        "component_evidence": deepcopy(dict(evidence)),
    }


def build_physical_block_bundle(
    source: Mapping[str, Any],
    *,
    prior_canonical_block: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_complete_source(source)
    observations = normalize_native_trace_transfers(normalized) + normalize_token_transfers(normalized)
    observations = _deduplicate_observations(observations)

    parser_evidence = {
        "policy_revision": PARSER_POLICY_REVISION,
        "supported_event_classes": [
            "NATIVE_ETH_CALLTRACER",
            "ERC20_TRANSFER",
            "ERC721_TRANSFER",
            "ERC1155_TRANSFER_SINGLE",
            "ERC1155_TRANSFER_BATCH",
        ],
    }
    components: dict[str, Any] = {}
    for name in ("BLOCK_BODY", "ALL_TRANSACTION_RECEIPTS", "ALL_TRANSACTION_TRACES"):
        member = normalized["component_evidence"][name]
        components[name] = {"verified": True, "evidence_sha256": member["evidence_sha256"]}
    components["DECLARED_TOKEN_EVENT_PARSERS"] = {
        "verified": True,
        "evidence_sha256": sha256_canonical_json(parser_evidence),
    }

    revisions: list[dict[str, Any]] = []
    if prior_canonical_block is not None:
        _require(isinstance(prior_canonical_block, Mapping), "PRIOR_CANONICAL_BLOCK_INVALID")
        _require(normalize_chain_id(prior_canonical_block.get("chain_id")) == normalized["chain_id"], "PRIOR_CANONICAL_CHAIN_MISMATCH")
        _require(prior_canonical_block.get("block_height") == normalized["block_height"], "PRIOR_CANONICAL_HEIGHT_MISMATCH")
        revision = build_canonicality_revision(
            chain_id=normalized["chain_id"],
            block_height=normalized["block_height"],
            previous_canonical_block_hash=prior_canonical_block.get("block_hash"),
            canonical_block_hash=normalized["block_hash"],
            revision_known_at=normalized["observation_known_at"],
            source_provenance=normalized["source_provenance"],
        )
        if revision is not None:
            revisions.append(revision)

    zero_classification = "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE" if not observations else None
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "capability_id": CAPABILITY_ID,
        "chain_id": normalized["chain_id"],
        "block_height": normalized["block_height"],
        "block_hash": normalized["block_hash"],
        "parser_policy_revision": PARSER_POLICY_REVISION,
        "observation_known_at": normalized["observation_known_at"],
        "finality": normalized["finality"],
        "source_provenance": normalized["source_provenance"],
        "coverage": {
            "key": {
                "chain_id": normalized["chain_id"],
                "block_height": normalized["block_height"],
                "block_hash": normalized["block_hash"],
                "parser_policy_revision": PARSER_POLICY_REVISION,
            },
            "complete": True,
            "absence_without_coverage_proof_is_zero": False,
            "zero_event_classification": zero_classification,
            "components": components,
        },
        "observations": observations,
        "canonicality_revisions": revisions,
    }
    return bundle


def serialize_physical_block_bundle(bundle: Mapping[str, Any]) -> bytes:
    _require(isinstance(bundle, Mapping), "PHYSICAL_BLOCK_BUNDLE_INVALID")
    _require(bundle.get("schema_version") == BUNDLE_SCHEMA_VERSION, "PHYSICAL_BLOCK_BUNDLE_SCHEMA_INVALID")
    _require(bundle.get("capability_id") == CAPABILITY_ID, "PHYSICAL_BLOCK_BUNDLE_CAPABILITY_INVALID")
    coverage = bundle.get("coverage")
    _require(isinstance(coverage, Mapping) and coverage.get("complete") is True, "INCOMPLETE_CANONICAL_BLOCK_BUNDLE_FORBIDDEN")
    observations = bundle.get("observations")
    _require(isinstance(observations, list), "PHYSICAL_BLOCK_BUNDLE_OBSERVATIONS_INVALID")
    zero_classification = coverage.get("zero_event_classification")
    if observations:
        _require(zero_classification is None, "NONZERO_BUNDLE_ZERO_CLASSIFICATION_INVALID")
    else:
        _require(zero_classification == "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE", "ZERO_EVENT_COVERAGE_PROOF_MISSING")
    return canonical_json_bytes(bundle)


def physical_block_bundle_sha256(bundle: Mapping[str, Any]) -> str:
    return sha256_canonical_json(bundle)
