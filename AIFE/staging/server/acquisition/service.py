"""Generic F5C acquisition orchestration with bounded composite durable acceptance.

C1 remains the provider-neutral adapter/result boundary. C2 adds one optional
composite durability dependency that reuses the existing immutable object store
and durable Work repository; no spool, queue, ledger or publication route is
created here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from core.data.repositories.server_control import ServerControlRepository, StoredWork
from server.integration.bindings import accept_domain_work_from_durable_object
from server.storage.ports import ImmutableObjectEvidence, ImmutableObjectStore

from .ports import AcquiredArtifact, AcquisitionAdapter


class AcquisitionResultInvariantError(ValueError):
    """Raised when an adapter/result violates the generic acquisition contract."""


class DurableAcceptanceNotConfigured(RuntimeError):
    """Raised when a caller requests C2 semantics without the C2 dependencies."""


@dataclass(frozen=True, slots=True)
class DurablyAcceptedArtifact:
    """Composite C2 success: exact bytes are verified and Work is durably bound."""

    acquired: AcquiredArtifact
    object_evidence: ImmutableObjectEvidence
    work: StoredWork


@dataclass(frozen=True, slots=True)
class DurableAcquisitionAcceptance:
    """Compose existing immutable storage and Work persistence in the frozen C2 order."""

    object_store: ImmutableObjectStore
    repository: ServerControlRepository
    policy_revision_identity: str
    scheduling_slot_identity: str = "DIRECT"

    def accept(self, acquired: AcquiredArtifact, *, at: datetime) -> DurablyAcceptedArtifact:
        """Return success only after object write/readback and the durable Work commit."""
        written = self.object_store.write_immutable(
            acquired.payload,
            expected_digest=acquired.envelope.content_identity,
        )
        if written.content_digest != acquired.envelope.content_identity or written.size != len(acquired.payload):
            raise AcquisitionResultInvariantError("immutable write evidence does not match acquired payload")

        verified = self.object_store.readback_verify(
            written.content_digest,
            expected_size=len(acquired.payload),
        )
        if verified != written:
            raise AcquisitionResultInvariantError("independent readback differs from immutable write evidence")

        work = accept_domain_work_from_durable_object(
            self.repository,
            acquired.envelope,
            verified,
            policy_revision_identity=self.policy_revision_identity,
            created_at=at,
            scheduling_slot_identity=self.scheduling_slot_identity,
        )
        if work.payload_reference != verified.physical_locator:
            raise AcquisitionResultInvariantError("durable Work does not reference the verified immutable object")
        return DurablyAcceptedArtifact(acquired, verified, work)


@dataclass(frozen=True, slots=True)
class GenericAcquisitionService:
    """Invoke one adapter; optionally cross the C2 durable-acceptance boundary."""

    adapter: AcquisitionAdapter
    durable_acceptance: DurableAcquisitionAcceptance | None = None

    async def acquire(self) -> AcquiredArtifact:
        """Acquire and validate envelope/payload identity without claiming durability."""
        result = await self.adapter.acquire()
        if not isinstance(result, AcquiredArtifact):
            raise AcquisitionResultInvariantError("adapter must return AcquiredArtifact")
        digest = hashlib.sha256(result.payload).hexdigest()
        if digest != result.envelope.content_identity:
            raise AcquisitionResultInvariantError(
                "payload digest does not match envelope content_identity"
            )
        return result

    async def acquire_durable(self, *, at: datetime) -> DurablyAcceptedArtifact:
        """Acquire one artifact and return only after composite C2 durability succeeds."""
        acquired = await self.acquire()
        if self.durable_acceptance is None:
            raise DurableAcceptanceNotConfigured("C2 durable acceptance dependency is not configured")
        return self.durable_acceptance.accept(acquired, at=at)
