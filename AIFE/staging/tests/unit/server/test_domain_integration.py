"""
Unit proofs for the neutral F4 domain-to-Server binding.

[Purpose]
    Доказать unit proofs for the neutral F4 domain-to-Server binding.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Pytest cases и fixtures, проверяющие mapped F5 invariants этого owner path.

[Usage]
    Запускать через canonical pytest/toolchain gates; тесты не являются production runtime.

[Architecture]
    Test surface проверяет generic AIFE Server contour на disposable future-AIFE tree; Data Bridge
    остаётся authority domain semantics.

[Note]
    Physical SQLite/filesystem и Docker qualification имеют отдельные evidence gates поверх этих тестов.

[Warning]
    Не ослаблять assertions и не принимать unit/integration PASS за production или Docker activation.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from server.integration import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
    DomainReadbackMismatch,
    DomainRegistrationMismatch,
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
from server.publication import (
    AckEvidence,
    PublicationAckError,
    PublicationState,
    acknowledge,
)
from server.storage import DurableWriteEvidence, ObjectIdentity, ReadbackEvidence


def _envelope(*, revision: str = "domain-revision-1", content: str = "content-sha-1") -> DomainArtifactEnvelope:
    moment = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    return DomainArtifactEnvelope(
        artifact_identity=DomainArtifactIdentity("domain-artifact-1"),
        artifact_type=DomainArtifactType("domain-artifact-type"),
        source_revision=revision,
        content_identity=content,
        references=DomainArtifactReferences(
            payload="domain-payload-ref",
            provenance="domain-provenance-ref",
            acceptance_evidence="domain-acceptance-ref",
        ),
        timing=DomainArtifactTiming(validated_at=moment, produced_at=moment, observed_at=moment),
    )


def _durable_state(envelope: DomainArtifactEnvelope):
    binding = bind_domain_publication(envelope)
    record = mark_ingest_durable(binding.publication)
    record = mark_staged(record)
    record = mark_publishing(record)
    record = mark_durable_stored(
        record,
        binding,
        DurableWriteEvidence(binding.object_identity, binding.durable_request.content_digest),
    )
    return binding, record


def test_same_artifact_replay_preserves_work_and_idempotency_identity() -> None:
    """Replay the same accepted artifact without changing work/idempotency identity."""
    envelope = _envelope()
    created = datetime(2026, 8, 26, 12, 1, tzinfo=UTC)

    first = bind_domain_work(envelope, created_at=created)
    replay = bind_domain_work(envelope, created_at=created)

    assert first.input_identity == replay.input_identity
    assert first.work.work_id == replay.work.work_id
    assert first.work.idempotency_identity == replay.work.idempotency_identity


def test_domain_revision_changes_server_input_identity_without_changing_domain_artifact_identity() -> None:
    """Keep domain identity stable while a source revision creates a new server input identity."""
    first = _envelope(revision="domain-revision-1")
    successor = replace(first, source_revision="domain-revision-2")
    created = datetime(2026, 8, 26, 12, 1, tzinfo=UTC)

    first_work = bind_domain_work(first, created_at=created)
    successor_work = bind_domain_work(successor, created_at=created)

    assert first.artifact_identity == successor.artifact_identity
    assert first_work.input_identity != successor_work.input_identity
    assert first_work.work.work_id != successor_work.work.work_id


def test_durable_write_success_is_not_ack() -> None:
    """Require the full publication proof chain after durable storage before ACK."""
    _, record = _durable_state(_envelope())

    assert record.state == PublicationState.DURABLE_STORED
    with pytest.raises(PublicationAckError):
        acknowledge(record, AckEvidence(True, True, True, True))


def test_independent_readback_mismatch_blocks_progress() -> None:
    """Reject a readback whose durable content evidence does not match the publication binding."""
    binding, record = _durable_state(_envelope())
    wrong = ReadbackEvidence(
        object_identity=binding.object_identity,
        content_digest="different-content",
        source_revision=binding.durable_request.source_revision,
        provenance_reference=binding.durable_request.provenance_reference,
    )

    with pytest.raises(DomainReadbackMismatch):
        mark_readback_verified(record, binding, wrong)
    assert record.state == PublicationState.DURABLE_STORED


def test_registration_failure_after_storage_is_recoverable_with_same_publication_identity() -> None:
    """Recover registration after storage without creating a second publication identity."""
    binding, record = _durable_state(_envelope())
    readback = ReadbackEvidence(
        object_identity=binding.object_identity,
        content_digest=binding.durable_request.content_digest,
        source_revision=binding.durable_request.source_revision,
        provenance_reference=binding.durable_request.provenance_reference,
    )
    verified = mark_readback_verified(record, binding, readback)

    with pytest.raises(DomainRegistrationMismatch):
        mark_canonically_registered(verified, binding, ObjectIdentity("wrong-object"))

    registered = mark_canonically_registered(verified, binding, binding.object_identity)
    assert registered.publication_id == binding.publication.publication_id
    assert registered.state == PublicationState.CANONICALLY_REGISTERED


def test_ack_failure_and_retry_do_not_create_duplicate_publication_identity() -> None:
    """Retry a failed ACK against the same registered publication identity."""
    binding, record = _durable_state(_envelope())
    readback = ReadbackEvidence(
        binding.object_identity,
        binding.durable_request.content_digest,
        binding.durable_request.source_revision,
        binding.durable_request.provenance_reference,
    )
    verified = mark_readback_verified(record, binding, readback)
    registered = mark_canonically_registered(verified, binding, binding.object_identity)

    with pytest.raises(PublicationAckError):
        acknowledge(registered, AckEvidence(True, True, True, False))

    acked = acknowledge(registered, AckEvidence(True, True, True, True))
    replay = acknowledge(registered, AckEvidence(True, True, True, True))
    assert acked.publication_id == replay.publication_id == binding.publication.publication_id
    assert acked == replay


def test_access_result_preserves_domain_identity_revision_content_and_provenance() -> None:
    """Preserve domain identity, revision, content, and provenance across the access boundary."""
    envelope = _envelope()
    result = access_result_from_domain(envelope, snapshot_identity="domain-snapshot-1")

    assert result.result_identity.value == envelope.artifact_identity.value
    assert result.source_revision.value == envelope.source_revision
    assert result.provenance.value == envelope.provenance_reference
    assert result.snapshot_identity is not None
    assert result.snapshot_identity.value == "domain-snapshot-1"
    assert result.items[0].artifact_identity == envelope.artifact_identity.value
    assert result.items[0].content_identity == envelope.content_identity
    assert result.items[0].payload_reference == envelope.payload_reference
