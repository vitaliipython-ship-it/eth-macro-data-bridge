"""Bounded C9 real-provider composition over existing AIFE durable lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from acquisition_core import CanonicalAcquisitionCore
from aife_f5c_acquisition_adapter import (
    C3_DEFAULT_SERIES_ID,
    DataBridgeF5CAcquisitionAdapter,
)
from server.acquisition.service import DurableAcquisitionAcceptance, GenericAcquisitionService
from server.integration.bindings import F5IncomingArtifactLifecycle, F5VerticalSliceResult
from server.storage.ports import ImmutableObjectStore
from core.data.repositories.server_control import ServerControlRepository


class C9ForwardInvariantError(RuntimeError):
    """Raised when the bounded C9 composition would cross an unqualified boundary."""


@dataclass(frozen=True, slots=True)
class C9ForwardRequest:
    """Inputs for one canonical binance-spot.m5 forward collection attempt."""

    expected_ms: int
    cycle_id: str
    canonical_slot: str
    staging_root: Path
    source_revision: str
    at: datetime
    claim_owner: str
    policy_revision_identity: str
    series_id: str = C3_DEFAULT_SERIES_ID
    scheduling_slot_identity: str = "DIRECT"


async def forward_once(
    request: C9ForwardRequest,
    *,
    repository: ServerControlRepository,
    object_store: ImmutableObjectStore,
    acquisition: CanonicalAcquisitionCore | None = None,
    clock_ms: Callable[[], int] | None = None,
) -> F5VerticalSliceResult:
    """Acquire via Data Bridge and reuse one accepted Work through Publication/Access."""
    adapter = DataBridgeF5CAcquisitionAdapter(
        expected_ms=request.expected_ms,
        cycle_id=request.cycle_id,
        canonical_slot=request.canonical_slot,
        staging_root=request.staging_root,
        source_revision=request.source_revision,
        series_id=request.series_id,
        acquisition=acquisition,
        clock_ms=clock_ms,
    )
    service = GenericAcquisitionService(
        adapter,
        DurableAcquisitionAcceptance(
            object_store,
            repository,
            policy_revision_identity=request.policy_revision_identity,
            scheduling_slot_identity=request.scheduling_slot_identity,
        ),
    )
    durable = await service.acquire_durable(at=request.at)
    lifecycle = F5IncomingArtifactLifecycle(repository, object_store)
    claimed_work, attempt = lifecycle.claim_accepted_work(
        durable.work.work_id,
        claim_owner=request.claim_owner,
        at=request.at,
    )
    if claimed_work.work_id != durable.work.work_id:
        raise C9ForwardInvariantError("claim did not preserve the durably accepted Work identity")
    if attempt is None:
        raise C9ForwardInvariantError("durably accepted Work was not claimable for this forward attempt")
    result = lifecycle.complete_attempt(
        durable.acquired.envelope,
        durable.acquired.payload,
        work_id=durable.work.work_id,
        attempt=attempt,
        at=request.at,
    )
    if result.work_id != durable.work.work_id or result.payload != durable.acquired.payload:
        raise C9ForwardInvariantError("publication/access result diverged from durable acceptance")
    return result
