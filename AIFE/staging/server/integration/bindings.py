"""
Pure F4 bindings retained while F5 adds physical lifecycle underneath them.

[Purpose]
    Связать neutral F4 domain envelope с generic Server F5 lifecycle без переноса domain semantics.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Typed bindings между domain envelope, Work identity и application/runtime seams.

[Usage]
    Использовать через typed bounded F5 interfaces и owner-mapped application/runtime composition.

[Architecture]
    Модуль принадлежит generic AIFE Server execution/storage contour; Data Bridge сохраняет
    market-data semantic authority.

[Note]
    Реализация рассчитана на one-server SQLite/WAL + immutable filesystem profile и fail-closed invariants.

[Warning]
    Не переносить domain/provider semantics в Work IDs, SQLite keys, filesystem locators или execution state.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.data.repositories.server_control import ServerControlRepository, StoredAttempt, StoredWork
from server._validation import stable_identity
from server.access import (
    AccessProvenance,
    AccessResult,
    AccessSourceRevision,
    ResultCompleteness,
    ResultIdentity,
    SnapshotIdentity,
)
from server.access.models import (
    ExactGenerationIdentityMismatch,
    ExactGenerationNotFound,
    resolve_exact_generation,
)
from server.application.services import F5BoundedPublicationCoordinator
from server.integration.domain import DomainArtifactEnvelope, exact_generation_request_for_domain
from server.publication import (
    PublicationId,
    PublicationRecord,
    PublicationState,
    SourceRevision,
    StoredObjectIdentity,
    transition_publication,
)
from server.publication.models import build_f5_generation_identity, build_f5_publication_id
from server.storage import (
    DurableWriteEvidence,
    DurableWriteRequest,
    ObjectIdentity,
    ReadbackEvidence,
)
from server.storage.ports import ImmutableObjectConflict, ImmutableObjectEvidence
from server.work import (
    IdempotencyIdentity,
    ProvenanceReference,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkType,
)
from server.work.models import F5WorkIdentityInputs


class DomainWriteMismatch(RuntimeError):
    """F5 contract-bound class `DomainWriteMismatch`. EN summary: bounded F5 class."""


class DomainReadbackMismatch(RuntimeError):
    """F5 contract-bound class `DomainReadbackMismatch`. EN summary: bounded F5 class."""


class DomainRegistrationMismatch(RuntimeError):
    """F5 contract-bound class `DomainRegistrationMismatch`. EN summary: bounded F5 class."""


@dataclass(frozen=True, slots=True)
class DomainWorkBinding:
    """F5 contract-bound class `DomainWorkBinding`. EN summary: bounded F5 class."""

    input_identity: str
    work: WorkRecord


@dataclass(frozen=True, slots=True)
class DomainPublicationBinding:
    """F5 contract-bound class `DomainPublicationBinding`. EN summary: bounded F5 class."""

    input_identity: str
    publication: PublicationRecord
    durable_request: DurableWriteRequest
    object_identity: ObjectIdentity


@dataclass(frozen=True, slots=True)
class DomainAccessItem:
    """F5 contract-bound class `DomainAccessItem`. EN summary: bounded F5 class."""

    artifact_identity: str
    artifact_type: str
    content_identity: str
    payload_reference: str


def domain_input_identity(envelope: DomainArtifactEnvelope) -> str:
    """F5 contract-bound function `domain_input_identity`. EN summary: bounded F5 function."""
    return stable_identity(
        "domain-input-v1",
        envelope.artifact_identity.value,
        envelope.source_revision,
        envelope.content_identity,
    )


def bind_domain_work(envelope: DomainArtifactEnvelope, *, created_at: datetime) -> DomainWorkBinding:
    """F5 contract-bound function `bind_domain_work`. EN summary: bounded F5 function."""
    i = domain_input_identity(envelope)
    w = WorkRecord(
        WorkId("work-" + stable_identity("domain-work-v1", i)),
        WorkType("domain-artifact:" + envelope.artifact_type.value),
        envelope.payload_reference,
        created_at,
        WorkIdentityReferences(
            IdempotencyIdentity("idem-" + stable_identity("domain-idempotency-v1", i)),
            ProvenanceReference(envelope.provenance_reference),
        ),
    )
    return DomainWorkBinding(i, w)


def accept_domain_work_from_durable_object(
    repository: ServerControlRepository,
    envelope: DomainArtifactEnvelope,
    object_evidence: ImmutableObjectEvidence,
    *,
    policy_revision_identity: str,
    created_at: datetime,
    scheduling_slot_identity: str = "DIRECT",
) -> StoredWork:
    """Persist Work only after a verified immutable object has supplied its exact reference."""
    if object_evidence.content_digest != envelope.content_identity:
        raise DomainWriteMismatch("durable object digest differs from domain content identity")
    inputs = F5WorkIdentityInputs(
        domain_artifact_identity=envelope.artifact_identity.value,
        source_revision=envelope.source_revision,
        content_identity=envelope.content_identity,
        policy_revision_identity=policy_revision_identity,
        scheduling_slot_identity=scheduling_slot_identity,
    )
    work = repository.accept_work(
        inputs,
        payload_reference=object_evidence.physical_locator,
        provenance_reference=envelope.provenance_reference,
        created_at=created_at,
    )
    if work.payload_reference != object_evidence.physical_locator:
        raise DomainWriteMismatch("persisted Work does not reference the verified immutable object")
    return work


def bind_domain_publication(
    envelope: DomainArtifactEnvelope,
) -> DomainPublicationBinding:
    """F5 contract-bound function `bind_domain_publication`. EN summary: bounded F5 function."""
    i = domain_input_identity(envelope)
    pid = PublicationId("publication-" + stable_identity("domain-publication-v1", i))
    oid = ObjectIdentity("object-" + stable_identity("domain-object-v1", i))
    p = PublicationRecord(pid, SourceRevision(envelope.source_revision))
    req = DurableWriteRequest(
        oid,
        envelope.source_revision,
        envelope.provenance_reference,
        envelope.content_identity,
        envelope.payload_reference,
    )
    return DomainPublicationBinding(i, p, req, oid)


def mark_ingest_durable(r: PublicationRecord) -> PublicationRecord:
    """F5 contract-bound function `mark_ingest_durable`. EN summary: bounded F5 function."""
    return transition_publication(r, PublicationState.INGEST_DURABLE)


def mark_staged(r: PublicationRecord) -> PublicationRecord:
    """F5 contract-bound function `mark_staged`. EN summary: bounded F5 function."""
    return transition_publication(r, PublicationState.STAGED)


def mark_publishing(r: PublicationRecord) -> PublicationRecord:
    """F5 contract-bound function `mark_publishing`. EN summary: bounded F5 function."""
    return transition_publication(r, PublicationState.PUBLISHING)


def mark_durable_stored(
    r: PublicationRecord, b: DomainPublicationBinding, e: DurableWriteEvidence
) -> PublicationRecord:
    """F5 contract-bound function `mark_durable_stored`. EN summary: bounded F5 function."""
    if e.object_identity != b.object_identity or e.content_digest != b.durable_request.content_digest:
        raise DomainWriteMismatch()
    return transition_publication(
        r,
        PublicationState.DURABLE_STORED,
        stored_object_identity=StoredObjectIdentity(b.object_identity.value),
    )


def mark_readback_verified(r: PublicationRecord, b: DomainPublicationBinding, e: ReadbackEvidence) -> PublicationRecord:
    """F5 contract-bound function `mark_readback_verified`. EN summary: bounded F5 function."""
    x = b.durable_request
    if (
        e.object_identity != b.object_identity
        or e.content_digest != x.content_digest
        or e.source_revision != x.source_revision
        or e.provenance_reference != x.provenance_reference
    ):
        raise DomainReadbackMismatch()
    return transition_publication(r, PublicationState.INDEPENDENT_READBACK_VERIFIED)


def mark_canonically_registered(
    r: PublicationRecord, b: DomainPublicationBinding, registered_identity: ObjectIdentity
) -> PublicationRecord:
    """F5 contract-bound function `mark_canonically_registered`. EN summary: bounded F5 function."""
    if registered_identity != b.object_identity:
        raise DomainRegistrationMismatch()
    return transition_publication(r, PublicationState.CANONICALLY_REGISTERED)


def access_result_from_domain(
    envelope: DomainArtifactEnvelope, *, snapshot_identity: str | None = None
) -> AccessResult[DomainAccessItem]:
    """F5 contract-bound function `access_result_from_domain`. EN summary: bounded F5 function."""
    item = DomainAccessItem(
        envelope.artifact_identity.value,
        envelope.artifact_type.value,
        envelope.content_identity,
        envelope.payload_reference,
    )
    snap = SnapshotIdentity(snapshot_identity) if snapshot_identity else None
    return AccessResult(
        (item,),
        ResultIdentity(envelope.artifact_identity.value),
        AccessSourceRevision(envelope.source_revision),
        AccessProvenance(envelope.provenance_reference),
        ResultCompleteness.COMPLETE,
        snap,
    )


@dataclass(frozen=True, slots=True)
class F5VerticalSliceResult:
    """F5 contract-bound class `F5VerticalSliceResult`. EN summary: bounded F5 class."""

    work_id: str
    attempt_id: str | None
    publication_id: str
    generation_identity: str
    physical_locator: str
    payload: bytes
    duplicate_collapsed: bool = False


class F5IncomingArtifactLifecycle:
    """Bounded F5 one-server orchestration; domain identities are inputs, never derived from storage."""

    def __init__(self, repository: Any, object_store: Any) -> None:
        """F5 contract-bound function `__init__`. EN summary: bounded F5 function."""
        self.repository = repository
        self.object_store = object_store

    def accept_and_claim(  # pylint: disable=too-many-arguments
        self,
        envelope: DomainArtifactEnvelope,
        *,
        policy_revision_identity: str,
        claim_owner: str,
        at: datetime,
        scheduling_slot_identity: str = "DIRECT",
    ) -> tuple[StoredWork, StoredAttempt | None]:
        """F5 contract-bound function `accept_and_claim`. EN summary: bounded F5 function."""
        inputs = F5WorkIdentityInputs(
            domain_artifact_identity=envelope.artifact_identity.value,
            source_revision=envelope.source_revision,
            content_identity=envelope.content_identity,
            policy_revision_identity=policy_revision_identity,
            scheduling_slot_identity=scheduling_slot_identity,
        )
        work = self.repository.accept_work(
            inputs,
            payload_reference=envelope.payload_reference,
            provenance_reference=envelope.provenance_reference,
            created_at=at,
        )
        if work.state == "PENDING":
            work = self.repository.mark_work_ready(work.work_id, at=at)
        if work.state != "READY":
            return work, None
        attempt = self.repository.claim_work(work.work_id, claim_owner=claim_owner, now=at)
        attempt = self.repository.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=at)
        return self.repository.get_work(work.work_id), attempt

    def complete_attempt(  # pylint: disable=too-many-arguments
        self,
        envelope: DomainArtifactEnvelope,
        payload: bytes,
        *,
        work_id: str,
        attempt: StoredAttempt,
        at: datetime,
    ) -> F5VerticalSliceResult:
        """F5 contract-bound function `complete_attempt`. EN summary: bounded F5 function."""
        try:
            digest = hashlib.sha256(payload).hexdigest()
            if digest != envelope.content_identity:
                raise DomainWriteMismatch("payload bytes do not match domain content identity")
            publication = F5BoundedPublicationCoordinator(self.repository, self.object_store).publish(
                work_id=work_id,
                attempt_id=attempt.attempt_id,
                fencing_token=attempt.fencing_token,
                domain_artifact_identity=envelope.artifact_identity.value,
                source_revision=envelope.source_revision,
                payload=payload,
                content_checksum=digest,
                at=at,
            )
            generation = self.repository.resolve_generation(envelope.artifact_identity.value)
            if generation is None:
                raise DomainRegistrationMismatch("registered generation missing")
            exact = resolve_exact_generation(
                self.repository,
                exact_generation_request_for_domain(envelope, generation.generation_identity),
            )
            observed = self.object_store.read_exact(exact.content_checksum)
            if observed != payload:
                raise DomainReadbackMismatch("exact access bytes differ from accepted payload")
        except (
            DomainWriteMismatch,
            DomainReadbackMismatch,
            DomainRegistrationMismatch,
            ExactGenerationIdentityMismatch,
            ExactGenerationNotFound,
            ImmutableObjectConflict,
        ) as exc:
            self.repository.terminal_attempt(
                attempt.attempt_id,
                fencing_token=attempt.fencing_token,
                at=at,
                success=False,
                retryable=False,
                reason=type(exc).__name__.upper(),
            )
            raise
        self.repository.terminal_attempt(attempt.attempt_id, fencing_token=attempt.fencing_token, at=at, success=True)
        return F5VerticalSliceResult(
            work_id,
            attempt.attempt_id,
            publication.publication_id,
            exact.generation_identity,
            exact.physical_locator,
            observed,
        )

    def process(  # pylint: disable=too-many-arguments
        self,
        envelope: DomainArtifactEnvelope,
        payload: bytes,
        *,
        policy_revision_identity: str,
        claim_owner: str,
        at: datetime,
        scheduling_slot_identity: str = "DIRECT",
    ) -> F5VerticalSliceResult:
        """F5 contract-bound function `process`. EN summary: bounded F5 function."""
        work, attempt = self.accept_and_claim(
            envelope,
            policy_revision_identity=policy_revision_identity,
            claim_owner=claim_owner,
            at=at,
            scheduling_slot_identity=scheduling_slot_identity,
        )
        if attempt is not None:
            return self.complete_attempt(envelope, payload, work_id=work.work_id, attempt=attempt, at=at)
        if work.state != "SUCCEEDED":
            raise RuntimeError(f"work not processable while state={work.state}")
        gid = build_f5_generation_identity(
            domain_artifact_identity=envelope.artifact_identity.value,
            source_revision=envelope.source_revision,
            content_identity=envelope.content_identity,
        )
        exact = resolve_exact_generation(self.repository, exact_generation_request_for_domain(envelope, gid))
        observed = self.object_store.read_exact(exact.content_checksum)
        if observed != payload:
            raise DomainReadbackMismatch("duplicate delivery bytes differ from registered object")
        pid = build_f5_publication_id(
            work_id=work.work_id,
            domain_artifact_identity=envelope.artifact_identity.value,
            source_revision=envelope.source_revision,
            content_identity=envelope.content_identity,
        )
        return F5VerticalSliceResult(
            work.work_id,
            None,
            pid,
            exact.generation_identity,
            exact.physical_locator,
            observed,
            True,
        )
