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

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.integration.bindings import DomainWriteMismatch, F5IncomingArtifactLifecycle
from server.integration.domain import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem


def envelope(payload: bytes, rev="r1"):
    """Exercise the mapped F5 acceptance case."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    return DomainArtifactEnvelope(
        DomainArtifactIdentity("domain-artifact-vslice"),
        DomainArtifactType("opaque-immutable"),
        rev,
        hashlib.sha256(payload).hexdigest(),
        DomainArtifactReferences("payload-ref", "domain-prov", "accepted"),
        DomainArtifactTiming(now, now, now),
    )


def test_i8_bounded_vertical_slice_and_duplicate_collapse(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    payload = b"bounded-f5-payload"
    e = envelope(payload)
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    flow = F5IncomingArtifactLifecycle(repo, store)
    first = flow.process(e, payload, policy_revision_identity="policy-1", claim_owner="worker-a", at=now)
    assert repo.get_work(first.work_id).state == "SUCCEEDED" and first.payload == payload
    duplicate = flow.process(
        e,
        payload,
        policy_revision_identity="policy-1",
        claim_owner="worker-b",
        at=now + timedelta(seconds=1),
    )
    assert (
        duplicate.duplicate_collapsed
        and duplicate.work_id == first.work_id
        and duplicate.generation_identity == first.generation_identity
    )
    assert len(repo.list_generations()) == 1


def test_f01_crash_before_durable_write_restarts_same_work_new_attempt(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    payload = b"crash-before-write"
    e = envelope(payload)
    path = tmp_path / "control.sqlite3"
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    repo = SQLiteServerControlRepository(path)
    flow = F5IncomingArtifactLifecycle(repo, store)
    work, first = flow.accept_and_claim(e, policy_revision_identity="policy-1", claim_owner="worker-a", at=now)
    assert first is not None and repo.get_publication("missing") is None
    # process crash: reopen durable control DB after lease expiry; no object was written.
    repo = SQLiteServerControlRepository(path)
    later = now + timedelta(seconds=61)
    second = repo.reclaim_work(work.work_id, claim_owner="worker-b", now=later)
    repo.mark_attempt_running(second.attempt_id, fencing_token=second.fencing_token, at=later)
    assert (
        second.attempt_no == 2
        and second.fencing_token > first.fencing_token
        and repo.get_work(work.work_id).work_id == work.work_id
    )
    result = F5IncomingArtifactLifecycle(repo, store).complete_attempt(
        e, payload, work_id=work.work_id, attempt=second, at=later
    )
    assert result.payload == payload and repo.get_work(work.work_id).state == "SUCCEEDED"


def test_nonretryable_domain_content_mismatch_terminalizes_same_work(tmp_path):
    """A domain/content identity violation cannot leave a retryable RUNNING Work."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    accepted_payload = b"accepted"
    wrong_payload = b"different"
    e = envelope(accepted_payload)
    repo = SQLiteServerControlRepository(tmp_path / "identity-conflict.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    flow = F5IncomingArtifactLifecycle(repo, store)
    work, attempt = flow.accept_and_claim(e, policy_revision_identity="policy-1", claim_owner="worker-a", at=now)
    assert attempt is not None
    with pytest.raises(DomainWriteMismatch):
        flow.complete_attempt(e, wrong_payload, work_id=work.work_id, attempt=attempt, at=now)
    failed = repo.get_work(work.work_id)
    assert failed is not None and failed.state == "FAILED"
    assert failed.terminal_state == "FAILED"
    assert failed.failure_state == "DOMAINWRITEMISMATCH"
    assert repo.get_attempt(attempt.attempt_id).state == "FAILED"
    assert not (tmp_path / "data" / "objects").exists()


def test_f09_restart_preserves_ready_work_and_resumes_same_identity(tmp_path):
    """F09 closes and reopens durable READY Work before any Attempt exists, then resumes it."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    payload = b"restart-ready-work"
    accepted = envelope(payload)
    path = tmp_path / "f09-control.sqlite3"
    repo = SQLiteServerControlRepository(path)
    flow = F5IncomingArtifactLifecycle(repo, QualifiedDataRootImmutableFilesystem(tmp_path / "f09-data"))
    work, attempt = flow.accept_and_claim(accepted, policy_revision_identity="policy-1", claim_owner="worker-a", at=now)
    assert attempt is not None
    # Return the same logical Work to READY through the bounded retry transition, then restart.
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    ready = repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(seconds=1),
        success=False,
        retryable=True,
        reason="transient",
    )
    assert ready.state == "READY" and ready.work_id == work.work_id

    reopened = SQLiteServerControlRepository(path)
    persisted = reopened.get_work(work.work_id)
    assert persisted is not None and persisted.state == "READY" and persisted.work_id == work.work_id
    resumed = reopened.claim_work(work.work_id, claim_owner="worker-b", now=now + timedelta(seconds=2))
    assert resumed.work_id == work.work_id and resumed.attempt_no == 2
