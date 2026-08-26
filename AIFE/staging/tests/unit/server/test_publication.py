"""Проверки PUBLICATION-контракта F3."""

import pytest

from server.publication import (
    AckEvidence,
    InvalidPublicationTransition,
    PublicationAckError,
    PublicationId,
    PublicationRecord,
    PublicationState,
    SourceRevision,
    StoredObjectIdentity,
    acknowledge,
    transition_publication,
)


def _registered() -> PublicationRecord:
    record = PublicationRecord(PublicationId("pub-1"), SourceRevision("source-r1"))
    for state in (
        PublicationState.INGEST_DURABLE,
        PublicationState.STAGED,
        PublicationState.PUBLISHING,
    ):
        record = transition_publication(record, state)
    record = transition_publication(
        record,
        PublicationState.DURABLE_STORED,
        stored_object_identity=StoredObjectIdentity("object-1"),
    )
    record = transition_publication(record, PublicationState.INDEPENDENT_READBACK_VERIFIED)
    return transition_publication(record, PublicationState.CANONICALLY_REGISTERED)


def test_lifecycle_order_is_strict() -> None:
    """Проверить строгий порядок publication lifecycle."""
    record = PublicationRecord(PublicationId("pub-1"), SourceRevision("source-r1"))
    with pytest.raises(InvalidPublicationTransition):
        transition_publication(record, PublicationState.STAGED)


def test_ack_requires_all_four_conditions() -> None:
    """Проверить четыре обязательных условия ACK."""
    record = _registered()
    good = AckEvidence(True, True, True, True)
    assert acknowledge(record, good).state is PublicationState.ACKED
    for bad in (
        AckEvidence(False, True, True, True),
        AckEvidence(True, False, True, True),
        AckEvidence(True, True, False, True),
        AckEvidence(True, True, True, False),
    ):
        with pytest.raises(PublicationAckError):
            acknowledge(record, bad)


def test_readback_mismatch_blocks_ack_and_retry_remains_idempotent() -> None:
    """Проверить блокировку ACK при read-back mismatch и idempotent retry."""
    record = _registered()
    with pytest.raises(PublicationAckError):
        acknowledge(record, AckEvidence(True, True, True, False))
    retried = acknowledge(record, AckEvidence(True, True, True, True))
    assert retried.publication_id == record.publication_id
    assert retried.source_revision == record.source_revision
