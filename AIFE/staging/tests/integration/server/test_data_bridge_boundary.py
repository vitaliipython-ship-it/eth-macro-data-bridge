"""F4 semantic-authority regression plus F5 exact replay identity binding."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.access.models import resolve_exact_generation
from server.application.services import F5BoundedPublicationCoordinator
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
from server.integration.domain import exact_generation_request_for_domain
from server.publication import AckEvidence, PublicationState, acknowledge
from server.storage import DurableWriteEvidence, ReadbackEvidence
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem
from server.work import AttemptId
from server.work.models import F5WorkIdentityInputs


def _accepted_input():
    """Exercise the mapped F5 acceptance case."""
    t = datetime(2026, 8, 26, 13, tzinfo=UTC)
    return DomainArtifactEnvelope(
        DomainArtifactIdentity("accepted-domain-artifact"),
        DomainArtifactType("accepted-domain-type"),
        "source-revision-a",
        "content-identity-a",
        DomainArtifactReferences("payload-ref-a", "provenance-ref-a", "acceptance-ref-a"),
        DomainArtifactTiming(t, t, t),
    )


def _published(e):
    """Exercise the mapped F5 acceptance case."""
    b = bind_domain_publication(e)
    r = mark_publishing(mark_staged(mark_ingest_durable(b.publication)))
    r = mark_durable_stored(r, b, DurableWriteEvidence(b.object_identity, b.durable_request.content_digest))
    rb = ReadbackEvidence(
        b.object_identity,
        b.durable_request.content_digest,
        b.durable_request.source_revision,
        b.durable_request.provenance_reference,
    )
    r = mark_readback_verified(r, b, rb)
    return b, mark_canonically_registered(r, b, b.object_identity)


def test_f4_domain_flow_preserves_payload_identity():
    """Exercise the mapped F5 acceptance case."""
    e = _accepted_input()
    w = bind_domain_work(e, created_at=e.produced_at)
    b, r = _published(e)
    a = acknowledge(r, AckEvidence(True, True, True, True))
    out = access_result_from_domain(e, snapshot_identity="snapshot-a")
    assert (
        w.work.payload_reference == e.payload_reference
        and b.durable_request.payload_reference == e.payload_reference
        and a.state == PublicationState.ACKED
        and out.items[0].content_identity == e.content_identity
    )


def test_stale_execution_fence_blocks_terminal_effect():
    """Exercise the mapped F5 acceptance case."""
    e = _accepted_input()
    w = bind_domain_work(e, created_at=e.produced_at).work
    now = e.produced_at
    lease = Lease(
        Claim(w.work_id, ClaimId("c"), AttemptId("a"), FencingToken(1)),
        LeaseId("l"),
        now + timedelta(minutes=1),
    )
    _, r = _published(e)
    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(lease, FencingToken(2), now)
    assert r.state == PublicationState.CANONICALLY_REGISTERED


def test_domain_builds_exact_generation_request_without_inventing_identity():
    """Exercise the mapped F5 acceptance case."""
    e = _accepted_input()
    q = exact_generation_request_for_domain(e, "gen:f5:v1:historic")
    assert (
        q.generation_scope_identity == e.artifact_identity.value
        and q.generation_identity == "gen:f5:v1:historic"
        and q.expected_source_revision == e.source_revision
        and q.expected_content_checksum == e.content_identity
    )


def test_f20_exact_historical_generation_does_not_fall_back_to_current(  # pylint: disable=too-many-locals
    tmp_path,
):
    """Prove F20 exact historical access never falls back to current."""
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    coordinator = F5BoundedPublicationCoordinator(repo, store)
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    identities = []
    for index, (rev, payload) in enumerate((("rev-old", b"old"), ("rev-new", b"new")), start=1):
        digest = hashlib.sha256(payload).hexdigest()
        inputs = F5WorkIdentityInputs(
            domain_artifact_identity="accepted-domain-artifact",
            source_revision=rev,
            content_identity=digest,
            policy_revision_identity="policy-1",
        )
        work = repo.accept_work(
            inputs,
            payload_reference=f"opaque-{index}",
            provenance_reference="domain-prov",
            created_at=now,
        )
        repo.mark_work_ready(work.work_id, at=now)
        attempt = repo.claim_work(work.work_id, claim_owner=f"worker-{index}", now=now)
        repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
        publication = coordinator.publish(
            work_id=work.work_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            domain_artifact_identity="accepted-domain-artifact",
            source_revision=rev,
            payload=payload,
            content_checksum=digest,
            at=now,
        )
        generation = repo.resolve_generation("accepted-domain-artifact")
        assert publication.state == "ACKED" and generation is not None
        identities.append((generation.generation_identity, rev, digest))
    old_gid, old_rev, old_digest = identities[0]
    current = repo.resolve_generation("accepted-domain-artifact")
    assert current is not None and current.generation_identity == identities[1][0]
    envelope = _accepted_input()
    envelope = DomainArtifactEnvelope(
        envelope.artifact_identity,
        envelope.artifact_type,
        old_rev,
        old_digest,
        envelope.references,
        envelope.timing,
    )
    exact = resolve_exact_generation(repo, exact_generation_request_for_domain(envelope, old_gid))
    assert exact.generation_identity == old_gid and exact.source_revision == old_rev
