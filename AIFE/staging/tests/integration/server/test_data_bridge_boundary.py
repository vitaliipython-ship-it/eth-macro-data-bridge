"""Cross-mechanism F4 proofs without embedding market/provider semantics in Server source."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from server.execution import (
    Claim,
    ClaimId,
    FencingToken,
    Lease,
    LeaseId,
    StaleFencingAuthorityError,
    validate_terminal_authority,
)
from server.integration import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
    access_result_from_domain,
    bind_domain_publication,
    bind_domain_work,
    mark_canonically_registered,
    mark_durable_stored,
    mark_ingest_durable,
    mark_publishing,
    mark_readback_verified,
    mark_staged,
)
from server.publication import AckEvidence, PublicationState, acknowledge
from server.storage import DurableWriteEvidence, ReadbackEvidence
from server.work import AttemptId


def _accepted_input() -> DomainArtifactEnvelope:
    moment = datetime(2026, 8, 26, 13, 0, tzinfo=UTC)
    return DomainArtifactEnvelope(
        DomainArtifactIdentity("accepted-domain-artifact"),
        DomainArtifactType("accepted-domain-type"),
        "source-revision-a",
        "content-identity-a",
        DomainArtifactReferences(
            "payload-ref-a", "provenance-ref-a", "acceptance-ref-a"
        ),
        DomainArtifactTiming(moment, moment, moment),
    )


def _published(envelope: DomainArtifactEnvelope):
    binding = bind_domain_publication(envelope)
    record = mark_ingest_durable(binding.publication)
    record = mark_staged(record)
    record = mark_publishing(record)
    record = mark_durable_stored(
        record,
        binding,
        DurableWriteEvidence(
            binding.object_identity, binding.durable_request.content_digest
        ),
    )
    readback = ReadbackEvidence(
        binding.object_identity,
        binding.durable_request.content_digest,
        binding.durable_request.source_revision,
        binding.durable_request.provenance_reference,
    )
    record = mark_readback_verified(record, binding, readback)
    record = mark_canonically_registered(record, binding, binding.object_identity)
    return binding, record


def test_accepted_domain_input_flows_to_work_publication_and_access_without_payload_reinterpretation() -> (
    None
):
    envelope = _accepted_input()
    work = bind_domain_work(envelope, created_at=envelope.produced_at)
    publication, registered = _published(envelope)
    acked = acknowledge(registered, AckEvidence(True, True, True, True))
    result = access_result_from_domain(envelope, snapshot_identity="snapshot-a")

    assert work.work.payload_reference == envelope.payload_reference
    assert publication.durable_request.payload_reference == envelope.payload_reference
    assert acked.state == PublicationState.ACKED
    assert result.items[0].payload_reference == envelope.payload_reference
    assert result.items[0].content_identity == envelope.content_identity


def test_duplicate_delivery_reuses_work_and_publication_identities() -> None:
    envelope = _accepted_input()
    first_work = bind_domain_work(envelope, created_at=envelope.produced_at)
    duplicate_work = bind_domain_work(envelope, created_at=envelope.produced_at)
    first_pub = bind_domain_publication(envelope)
    duplicate_pub = bind_domain_publication(envelope)

    assert first_work == duplicate_work
    assert first_pub == duplicate_pub


def test_stale_execution_fence_blocks_terminal_effect_before_ack() -> None:
    envelope = _accepted_input()
    work = bind_domain_work(envelope, created_at=envelope.produced_at).work
    now = envelope.produced_at
    claim = Claim(
        work.work_id, ClaimId("claim-a"), AttemptId("attempt-a"), FencingToken(1)
    )
    lease = Lease(claim, LeaseId("lease-a"), now + timedelta(minutes=1))
    _, registered = _published(envelope)

    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(lease, FencingToken(2), now)
    assert registered.state == PublicationState.CANONICALLY_REGISTERED


def test_current_fence_then_ack_preserves_same_publication_identity() -> None:
    envelope = _accepted_input()
    work = bind_domain_work(envelope, created_at=envelope.produced_at).work
    now = envelope.produced_at
    claim = Claim(
        work.work_id, ClaimId("claim-b"), AttemptId("attempt-b"), FencingToken(2)
    )
    lease = Lease(claim, LeaseId("lease-b"), now + timedelta(minutes=1))
    binding, registered = _published(envelope)

    validate_terminal_authority(lease, FencingToken(2), now)
    acked = acknowledge(registered, AckEvidence(True, True, True, True))
    assert acked.publication_id == binding.publication.publication_id
