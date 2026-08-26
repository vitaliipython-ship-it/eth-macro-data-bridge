"""Сквозная проверка композиции шести F2-контрактов в чистых F3-моделях."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.access import AccessProvenance, AccessResult, AccessSourceRevision, ResultCompleteness, ResultIdentity
from server.execution import Claim, ClaimId, FencingToken, Lease, LeaseId, validate_terminal_authority
from server.publication import (
    AckEvidence,
    PublicationId,
    PublicationRecord,
    PublicationState,
    SourceRevision,
    StoredObjectIdentity,
    acknowledge,
    transition_publication,
)
from server.scheduling import (
    PolicyRevision,
    ScheduleDefinition,
    ScheduleId,
    ScheduleKind,
    build_due_identity,
    materialize_due,
)
from server.storage import ObjectIdentity
from server.work import (
    AttemptId,
    IdempotencyIdentity,
    ProvenanceReference,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkState,
    WorkType,
    transition_work,
)

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def test_work_to_access_flow_preserves_generic_identity_boundaries() -> None:
    """Проверить сквозную композицию шести generic contract boundaries."""
    work = WorkRecord(
        work_id=WorkId("work-1"),
        work_type=WorkType("generic-capability"),
        payload_reference="payload:opaque",
        created_at=NOW,
        identities=WorkIdentityReferences(IdempotencyIdentity("idem-1"), ProvenanceReference("domain:source-r1")),
    )
    work = transition_work(work, WorkState.READY)

    schedule = ScheduleDefinition(
        schedule_id=ScheduleId("schedule-1"),
        policy_revision=PolicyRevision("policy-r1"),
        kind=ScheduleKind.RECURRING,
        timezone_name="UTC",
    )
    due = build_due_identity(schedule, NOW)
    materialization = materialize_due(due, work.work_id, NOW)
    assert materialization.work_id == work.work_id

    attempt = AttemptId("attempt-1")
    work = transition_work(work, WorkState.CLAIMED, attempt_id=attempt, claim_reference="claim-1")
    lease = Lease(
        claim=Claim(work.work_id, ClaimId("claim-1"), attempt, FencingToken(1)),
        lease_id=LeaseId("lease-1"),
        expires_at=NOW + timedelta(minutes=5),
    )
    validate_terminal_authority(lease, FencingToken(1), NOW)

    publication = PublicationRecord(PublicationId("publication-1"), SourceRevision("source-r1"))
    for state in (PublicationState.INGEST_DURABLE, PublicationState.STAGED, PublicationState.PUBLISHING):
        publication = transition_publication(publication, state)
    stored = ObjectIdentity("object-1")
    publication = transition_publication(
        publication,
        PublicationState.DURABLE_STORED,
        stored_object_identity=StoredObjectIdentity(stored.value),
    )
    publication = transition_publication(publication, PublicationState.INDEPENDENT_READBACK_VERIFIED)
    publication = transition_publication(publication, PublicationState.CANONICALLY_REGISTERED)
    publication = acknowledge(publication, AckEvidence(True, True, True, True))

    result = AccessResult(
        items=(stored.value,),
        result_identity=ResultIdentity("result-1"),
        source_revision=AccessSourceRevision(publication.source_revision.value),
        provenance=AccessProvenance(publication.publication_id.value),
        completeness=ResultCompleteness.COMPLETE,
    )
    assert publication.state is PublicationState.ACKED
    assert result.source_revision.value == "source-r1"
    assert result.provenance.value == "publication-1"


def test_no_eth_or_provider_specific_symbols_in_server_source() -> None:
    """Проверить отсутствие ETH/provider-specific source symbols."""
    server_root = Path(__file__).resolve().parents[3] / "server"
    banned = ("ethusdt", "deribit", "binance", "kraken")
    for path in server_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token in text for token in banned), path
