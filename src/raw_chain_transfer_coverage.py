from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical_json import sha256_canonical_json

SNAPSHOT_SCHEMA_VERSION = "raw-chain-transfer-acked-coverage-snapshot/1.0.0"
_COVERED_STATES = {"COVERED_ZERO_EVENT_BLOCK", "COVERED_NONZERO_BLOCK"}
_FINALITY_STATES = {"PROVISIONAL", "FINALIZED"}


class RawTransferCoverageSnapshotError(ValueError):
    """Fail-closed error for invalid canonical coverage evidence."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RawTransferCoverageSnapshotError(code)


def _validate_request(chain_id: str, start: int, end: int) -> None:
    _require(isinstance(chain_id, str) and bool(chain_id), "CHAIN_ID_INVALID")
    for value, code in ((start, "BLOCK_HEIGHT_START_INVALID"), (end, "BLOCK_HEIGHT_END_INVALID")):
        _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, code)
    _require(start < end, "BLOCK_HEIGHT_RANGE_INVALID")


def _normalize_evidence_row(
    row: Mapping[str, Any], *, chain_id: str, start: int, end: int
) -> dict[str, Any]:
    _require(isinstance(row, Mapping), "COVERAGE_EVIDENCE_ROW_INVALID")
    state = row.get("state")
    _require(state in _COVERED_STATES, "COVERAGE_EVIDENCE_STATE_INVALID")
    _require(row.get("coverage_complete") is True, "COVERAGE_EVIDENCE_INCOMPLETE")
    key = row.get("coverage_key")
    _require(isinstance(key, Mapping), "COVERAGE_KEY_INVALID")
    _require(key.get("chain_id") == chain_id, "COVERAGE_CHAIN_MISMATCH")
    height = key.get("block_height")
    _require(isinstance(height, int) and not isinstance(height, bool), "COVERAGE_HEIGHT_INVALID")
    _require(start <= height < end, "COVERAGE_HEIGHT_OUTSIDE_RANGE")
    block_hash = key.get("block_hash")
    parser_policy = key.get("parser_policy_revision")
    _require(isinstance(block_hash, str) and bool(block_hash), "COVERAGE_BLOCK_HASH_INVALID")
    _require(isinstance(parser_policy, str) and bool(parser_policy), "COVERAGE_PARSER_POLICY_INVALID")
    resource_ref = row.get("resource_ref")
    content_identity = row.get("content_identity")
    _require(isinstance(resource_ref, str) and bool(resource_ref), "COVERAGE_RESOURCE_REF_INVALID")
    _require(isinstance(content_identity, str) and len(content_identity) == 64, "COVERAGE_CONTENT_IDENTITY_INVALID")
    try:
        int(content_identity, 16)
    except ValueError as exc:
        raise RawTransferCoverageSnapshotError("COVERAGE_CONTENT_IDENTITY_INVALID") from exc
    finality = row.get("finality")
    known_at = row.get("observation_known_at")
    _require(finality in _FINALITY_STATES, "COVERAGE_FINALITY_INVALID")
    _require(isinstance(known_at, str) and bool(known_at), "COVERAGE_KNOWN_AT_INVALID")
    zero = row.get("zero_event_classification")
    if state == "COVERED_ZERO_EVENT_BLOCK":
        _require(zero == "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE", "COVERED_ZERO_PROOF_INVALID")
    else:
        _require(zero is None, "COVERED_NONZERO_ZERO_CLASSIFICATION_INVALID")
    return {
        "state": state,
        "resource_ref": resource_ref,
        "content_identity": content_identity,
        "coverage_complete": True,
        "coverage_key": {
            "chain_id": chain_id,
            "block_height": height,
            "block_hash": block_hash,
            "parser_policy_revision": parser_policy,
        },
        "zero_event_classification": zero,
        "finality": finality,
        "observation_known_at": known_at,
    }


def build_acked_coverage_snapshot(
    *,
    chain_id: str,
    block_height_start: int,
    block_height_end: int,
    coverage_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project canonical PIT-visible durable block coverage into one contiguous frontier."""
    _validate_request(chain_id, block_height_start, block_height_end)
    _require(
        isinstance(coverage_evidence, Sequence)
        and not isinstance(coverage_evidence, (str, bytes, bytearray)),
        "COVERAGE_EVIDENCE_INVALID",
    )
    normalized = [
        _normalize_evidence_row(row, chain_id=chain_id, start=block_height_start, end=block_height_end)
        for row in coverage_evidence
    ]
    normalized.sort(
        key=lambda row: (
            row["coverage_key"]["block_height"],
            row["coverage_key"]["block_hash"],
            row["resource_ref"],
        )
    )
    heights = [row["coverage_key"]["block_height"] for row in normalized]
    _require(len(heights) == len(set(heights)), "COVERAGE_DUPLICATE_HEIGHT")
    covered = sorted(heights)
    covered_set = set(covered)
    expected = list(range(block_height_start, block_height_end))
    missing = [height for height in expected if height not in covered_set]
    next_uncovered = missing[0] if missing else None
    contiguous_end = next_uncovered if next_uncovered is not None else block_height_end
    highest = contiguous_end - 1 if contiguous_end > block_height_start else None
    snapshot: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "chain_id": chain_id,
        "block_height_start": block_height_start,
        "block_height_end": block_height_end,
        "requested_height_count": len(expected),
        "covered_height_count": len(covered),
        "covered_heights": covered,
        "missing_height_count": len(missing),
        "missing_block_heights": missing,
        "contiguous_start_height": block_height_start,
        "contiguous_end_exclusive": contiguous_end,
        "highest_contiguous_acked_height": highest,
        "next_uncovered_block_height": next_uncovered,
        "complete": not missing,
        "coverage_evidence_sha256": sha256_canonical_json(normalized),
    }
    snapshot["snapshot_sha256"] = sha256_canonical_json(snapshot)
    return snapshot
