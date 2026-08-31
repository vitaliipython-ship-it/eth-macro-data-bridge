"""Application services; F5 orchestration keeps filesystem I/O outside SQLite transactions."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from server.access.models import AccessRequest, AccessResult
from server.execution.models import Lease
from server.publication.models import PublicationRecord
from server.scheduling.models import DueMaterialization, ScheduleDefinition
from server.work.models import WorkRecord


class WorkService(Protocol):
    """Bounded F5 class `WorkService` preserving the frozen contract."""

    async def submit(self, record: WorkRecord) -> WorkRecord:
        """Protocol operation `submit` for the frozen F5 boundary."""
        raise NotImplementedError


class SchedulingService(Protocol):
    """Bounded F5 class `SchedulingService` preserving the frozen contract."""

    async def materialize(self, definition: ScheduleDefinition) -> DueMaterialization | None:
        """Protocol operation `materialize` for the frozen F5 boundary."""
        raise NotImplementedError


class ExecutionService(Protocol):
    """Bounded F5 class `ExecutionService` preserving the frozen contract."""

    async def claim(self, record: WorkRecord) -> Lease:
        """Protocol operation `claim` for the frozen F5 boundary."""
        raise NotImplementedError


class PublicationService(Protocol):
    """Bounded F5 class `PublicationService` preserving the frozen contract."""

    async def reconcile(self, record: PublicationRecord) -> PublicationRecord:
        """Protocol operation `reconcile` for the frozen F5 boundary."""
        raise NotImplementedError


class AccessService(Protocol):
    """Bounded F5 class `AccessService` preserving the frozen contract."""

    async def query(self, request: AccessRequest) -> AccessResult[object]:
        """Protocol operation `query` for the frozen F5 boundary."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ServerApplicationServices:
    """Bounded F5 class `ServerApplicationServices` preserving the frozen contract."""

    work: WorkService
    scheduling: SchedulingService
    execution: ExecutionService
    publication: PublicationService
    access: AccessService


class F5BoundedPublicationCoordinator:
    """Bounded F5 class `F5BoundedPublicationCoordinator` preserving the frozen contract."""

    def __init__(self, repository: Any, object_store: Any) -> None:
        """Bounded F5 function `__init__` preserving the frozen contract."""
        self.repository = repository
        self.object_store = object_store

    def publish(  # pylint: disable=too-many-arguments
        self,
        *,
        work_id: str,
        attempt_id: str,
        fencing_token: int,
        domain_artifact_identity: str,
        source_revision: str,
        payload: bytes,
        content_checksum: str,
        at: datetime,
    ) -> Any:
        """Bounded F5 function `publish` preserving the frozen contract."""
        p = self.repository.ensure_publication(
            work_id=work_id,
            attempt_id=attempt_id,
            fencing_token=fencing_token,
            domain_artifact_identity=domain_artifact_identity,
            source_revision=source_revision,
            content_checksum=content_checksum,
            content_size=len(payload),
            at=at,
        )
        if p.state == "INGEST_DURABLE":
            p = self.repository.advance_publication(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                target_state="STAGED",
                at=at,
            )
        if p.state == "STAGED":
            p = self.repository.advance_publication(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                target_state="PUBLISHING",
                at=at,
            )
        if p.state == "PUBLISHING":
            e = self.object_store.write_immutable(payload, expected_digest=content_checksum)
            p = self.repository.advance_publication(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                target_state="DURABLE_STORED",
                at=at,
                physical_locator=e.physical_locator,
                evidence="sha256:" + e.content_digest,
            )
        if p.state == "DURABLE_STORED":
            e = self.object_store.readback_verify(content_checksum, expected_size=len(payload))
            p = self.repository.advance_publication(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                target_state="INDEPENDENT_READBACK_VERIFIED",
                at=at,
                evidence="readback:" + e.content_digest,
            )
        if p.state == "INDEPENDENT_READBACK_VERIFIED":
            self.repository.register_generation(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                at=at,
            )
            p = self.repository.get_publication(p.publication_id)
        if p.state == "CANONICALLY_REGISTERED":
            p = self.repository.ack_publication(
                p.publication_id,
                attempt_id=attempt_id,
                fencing_token=fencing_token,
                at=at,
            )
        return p
