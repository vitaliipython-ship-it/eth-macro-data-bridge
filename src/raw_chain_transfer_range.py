from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from raw_chain_transfer_core import CanonicalBlockReferencePort
from raw_chain_transfer_route import RawTransferPhysicalRoute, RawTransferRouteResult

RANGE_RESULT_SCHEMA_VERSION = "raw-chain-transfer-bounded-range-result/1.0.0"


class RawTransferRangeError(RuntimeError):
    """Fail-closed bounded-range composition error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class RawTransferRangeResult:
    schema_version: str
    chain_id: str
    block_height_start: int
    block_height_end: int
    results: tuple[RawTransferRouteResult, ...]


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RawTransferRangeError(code)


def _validate_range(start: int, end: int) -> None:
    _require(isinstance(start, int) and not isinstance(start, bool), "RANGE_START_INVALID")
    _require(isinstance(end, int) and not isinstance(end, bool), "RANGE_END_INVALID")
    _require(start >= 0, "RANGE_START_NEGATIVE")
    _require(end >= 0, "RANGE_END_NEGATIVE")
    _require(start < end, "RANGE_EMPTY_OR_REVERSED")


class RawChainTransferBoundedRangeExecutor:
    """Execute one explicit half-open block range through existing qualified seams."""

    def __init__(
        self,
        block_reference: CanonicalBlockReferencePort,
        route: RawTransferPhysicalRoute,
    ) -> None:
        self._block_reference = block_reference
        self._route = route

    def execute_range(
        self,
        *,
        chain_id: str,
        block_height_start: int,
        block_height_end: int,
        observation_known_at: str,
        prior_canonical_blocks: Mapping[int, Mapping[str, Any]] | None = None,
    ) -> RawTransferRangeResult:
        _validate_range(block_height_start, block_height_end)
        prior = {} if prior_canonical_blocks is None else prior_canonical_blocks
        _require(isinstance(prior, Mapping), "PRIOR_CANONICAL_BLOCKS_INVALID")

        completed: list[RawTransferRouteResult] = []
        for height in range(block_height_start, block_height_end):
            block_hash = self._block_reference.resolve_block_hash(
                chain_id=chain_id,
                block_height=height,
            )
            result = self._route.execute_block(
                chain_id,
                block_hash,
                observation_known_at=observation_known_at,
                prior_canonical_block=prior.get(height),
            )
            _require(result.ack_state == "PASS", "ROUTE_ACK_NOT_PASS")
            _require(result.block_height == height, "ROUTE_BLOCK_HEIGHT_MISMATCH")
            _require(result.block_hash == block_hash, "ROUTE_BLOCK_HASH_MISMATCH")
            completed.append(result)

        return RawTransferRangeResult(
            schema_version=RANGE_RESULT_SCHEMA_VERSION,
            chain_id=chain_id,
            block_height_start=block_height_start,
            block_height_end=block_height_end,
            results=tuple(completed),
        )
