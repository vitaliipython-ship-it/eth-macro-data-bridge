"""
Bounded F5 implementation acceptance tests for this mapped owner path.

[Purpose]
    Доказать bounded F5 implementation acceptance tests for this mapped owner path.

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

import pytest

from server.publication.models import (
    AckEvidence,
    PublicationAckError,
    PublicationId,
    PublicationRecord,
    PublicationState,
    SourceRevision,
    StoredObjectIdentity,
    acknowledge,
    build_f5_publication_id,
    transition_publication,
)


def test_publication_identity_and_state_machine():
    """Exercise the mapped F5 acceptance case."""
    pid = build_f5_publication_id(
        work_id="w",
        domain_artifact_identity="a",
        source_revision="r",
        content_identity="c",
    )
    assert pid == build_f5_publication_id(
        work_id="w",
        domain_artifact_identity="a",
        source_revision="r",
        content_identity="c",
    )
    r = PublicationRecord(PublicationId(pid), SourceRevision("r"))
    r = transition_publication(r, PublicationState.INGEST_DURABLE)
    r = transition_publication(r, PublicationState.STAGED)
    r = transition_publication(r, PublicationState.PUBLISHING)
    r = transition_publication(
        r,
        PublicationState.DURABLE_STORED,
        stored_object_identity=StoredObjectIdentity("o"),
    )
    r = transition_publication(r, PublicationState.INDEPENDENT_READBACK_VERIFIED)
    r = transition_publication(r, PublicationState.CANONICALLY_REGISTERED)
    assert acknowledge(r, AckEvidence(True, True, True, True, True)).state == PublicationState.ACKED


def test_illegal_ack_fails_closed():
    """Exercise the mapped F5 acceptance case."""
    with pytest.raises(PublicationAckError):
        acknowledge(
            PublicationRecord(PublicationId("p"), SourceRevision("r")),
            AckEvidence(True, True, True, True, True),
        )
