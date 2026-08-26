"""Pure bindings between accepted domain input and generic Server/Data mechanisms."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from server._validation import stable_identity
from server.access import (
    AccessProvenance,
    AccessResult,
    AccessSourceRevision,
    ResultCompleteness,
    ResultIdentity,
    SnapshotIdentity,
)
from server.integration.domain import DomainArtifactEnvelope
from server.publication import (
    PublicationId,
    PublicationRecord,
    PublicationState,
    SourceRevision,
    StoredObjectIdentity,
    transition_publication,
)
from server.storage import (
    DurableWriteEvidence,
    DurableWriteRequest,
    ObjectIdentity,
    ReadbackEvidence,
)
from server.work import (
    IdempotencyIdentity,
    ProvenanceReference,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkType,
)


class DomainWriteMismatch(RuntimeError):
    """Durable write evidence differs from the accepted domain binding."""


class DomainReadbackMismatch(RuntimeError):
    """Independent read-back differs from the accepted domain binding."""


class DomainRegistrationMismatch(RuntimeError):
    """Canonical registration does not bind the same stored object."""


@dataclass(frozen=True, slots=True)
class DomainWorkBinding:
    """Deterministic domain-input to logical-work binding."""

    input_identity: str
    work: WorkRecord


@dataclass(frozen=True, slots=True)
class DomainPublicationBinding:
    """Stable publication/object identities derived from the accepted domain input."""

    input_identity: str
    publication: PublicationRecord
    durable_request: DurableWriteRequest
    object_identity: ObjectIdentity


@dataclass(frozen=True, slots=True)
class DomainAccessItem:
    """Identity-only item exposed through generic ACCESS without payload reinterpretation."""

    artifact_identity: str
    artifact_type: str
    content_identity: str
    payload_reference: str


def domain_input_identity(envelope: DomainArtifactEnvelope) -> str:
    """Bind identity+revision+content without inspecting the domain payload."""
    return stable_identity(
        "domain-input-v1",
        envelope.artifact_identity.value,
        envelope.source_revision,
        envelope.content_identity,
    )


def bind_domain_work(
    envelope: DomainArtifactEnvelope, *, created_at: datetime
) -> DomainWorkBinding:
    """Map one accepted input revision to stable WORK and idempotency identities."""
    input_id = domain_input_identity(envelope)
    work = WorkRecord(
        work_id=WorkId("work-" + stable_identity("domain-work-v1", input_id)),
        work_type=WorkType("domain-artifact:" + envelope.artifact_type.value),
        payload_reference=envelope.payload_reference,
        created_at=created_at,
        identities=WorkIdentityReferences(
            idempotency=IdempotencyIdentity(
                "idem-" + stable_identity("domain-idempotency-v1", input_id)
            ),
            provenance=ProvenanceReference(envelope.provenance_reference),
        ),
    )
    return DomainWorkBinding(input_identity=input_id, work=work)


def bind_domain_publication(
    envelope: DomainArtifactEnvelope,
) -> DomainPublicationBinding:
    """Build stable generic publication and durable-write identities from accepted input."""
    input_id = domain_input_identity(envelope)
    publication_id = PublicationId(
        "publication-" + stable_identity("domain-publication-v1", input_id)
    )
    object_identity = ObjectIdentity(
        "object-" + stable_identity("domain-object-v1", input_id)
    )
    publication = PublicationRecord(
        publication_id=publication_id,
        source_revision=SourceRevision(envelope.source_revision),
    )
    request = DurableWriteRequest(
        object_identity=object_identity,
        source_revision=envelope.source_revision,
        provenance_reference=envelope.provenance_reference,
        content_digest=envelope.content_identity,
        payload_reference=envelope.payload_reference,
    )
    return DomainPublicationBinding(input_id, publication, request, object_identity)


def mark_ingest_durable(record: PublicationRecord) -> PublicationRecord:
    """Advance only the generic publication state after durable ingest evidence exists."""
    return transition_publication(record, PublicationState.INGEST_DURABLE)


def mark_staged(record: PublicationRecord) -> PublicationRecord:
    """Advance to STAGED without changing domain identity."""
    return transition_publication(record, PublicationState.STAGED)


def mark_publishing(record: PublicationRecord) -> PublicationRecord:
    """Advance to PUBLISHING without implying durability or ACK."""
    return transition_publication(record, PublicationState.PUBLISHING)


def mark_durable_stored(
    record: PublicationRecord,
    binding: DomainPublicationBinding,
    evidence: DurableWriteEvidence,
) -> PublicationRecord:
    """Accept durable storage only when exact object/content identities match."""
    if (
        evidence.object_identity != binding.object_identity
        or evidence.content_digest != binding.durable_request.content_digest
    ):
        raise DomainWriteMismatch(
            "durable write identity/content does not match accepted domain input"
        )
    return transition_publication(
        record,
        PublicationState.DURABLE_STORED,
        stored_object_identity=StoredObjectIdentity(binding.object_identity.value),
    )


def mark_readback_verified(
    record: PublicationRecord,
    binding: DomainPublicationBinding,
    evidence: ReadbackEvidence,
) -> PublicationRecord:
    """Require independent exact identity/revision/content/provenance read-back."""
    expected = binding.durable_request
    if (
        evidence.object_identity != binding.object_identity
        or evidence.content_digest != expected.content_digest
        or evidence.source_revision != expected.source_revision
        or evidence.provenance_reference != expected.provenance_reference
    ):
        raise DomainReadbackMismatch(
            "independent read-back does not match accepted domain binding"
        )
    return transition_publication(
        record, PublicationState.INDEPENDENT_READBACK_VERIFIED
    )


def mark_canonically_registered(
    record: PublicationRecord,
    binding: DomainPublicationBinding,
    registered_identity: ObjectIdentity,
) -> PublicationRecord:
    """Register only the same durable object; registration itself stays outside storage write."""
    if registered_identity != binding.object_identity:
        raise DomainRegistrationMismatch(
            "canonical registration points at a different object identity"
        )
    return transition_publication(record, PublicationState.CANONICALLY_REGISTERED)


def access_result_from_domain(
    envelope: DomainArtifactEnvelope,
    *,
    snapshot_identity: str | None = None,
) -> AccessResult[DomainAccessItem]:
    """Project identities into ACCESS without reading or normalizing the domain payload."""
    item = DomainAccessItem(
        artifact_identity=envelope.artifact_identity.value,
        artifact_type=envelope.artifact_type.value,
        content_identity=envelope.content_identity,
        payload_reference=envelope.payload_reference,
    )
    snapshot = (
        SnapshotIdentity(snapshot_identity) if snapshot_identity is not None else None
    )
    return AccessResult(
        items=(item,),
        result_identity=ResultIdentity(envelope.artifact_identity.value),
        source_revision=AccessSourceRevision(envelope.source_revision),
        provenance=AccessProvenance(envelope.provenance_reference),
        completeness=ResultCompleteness.COMPLETE,
        snapshot_identity=snapshot,
    )
