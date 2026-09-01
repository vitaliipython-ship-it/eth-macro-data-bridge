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

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from core.data.repositories.server_control import WorkNotClaimable
from server.work.models import F5WorkIdentityInputs


def test_f5_sqlite_accept_ready_claim_restart(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    path = tmp_path / "control.sqlite3"
    now = datetime.now(timezone.utc)
    inputs = F5WorkIdentityInputs(
        domain_artifact_identity="artifact-1",
        source_revision="rev-1",
        content_identity="c" * 64,
        policy_revision_identity="policy-1",
    )
    repo = SQLiteServerControlRepository(path)
    work = repo.accept_work(
        inputs,
        payload_reference="opaque-ref",
        provenance_reference="domain-prov",
        created_at=now,
    )
    assert repo.mark_work_ready(work.work_id, at=now).state == "READY"
    claim = repo.claim_work(work.work_id, claim_owner="worker-A", now=now)
    assert claim.work_id == work.work_id
    repo2 = SQLiteServerControlRepository(path)
    assert repo2.get_attempt(claim.attempt_id) == claim
    con = sqlite3.connect(path)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def _new_ready_repo(tmp_path, name="race.sqlite3"):
    """Exercise the mapped F5 acceptance case."""
    path = tmp_path / name
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(path)
    inputs = F5WorkIdentityInputs(
        domain_artifact_identity=name,
        source_revision="rev",
        content_identity="d" * 64,
        policy_revision_identity="p",
    )
    work = repo.accept_work(inputs, payload_reference="x", provenance_reference="p", created_at=now)
    repo.mark_work_ready(work.work_id, at=now)
    return repo, work, now


def test_concurrent_claim_one_winner(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    repo, work, now = _new_ready_repo(tmp_path)

    def claim(owner):
        """Exercise the mapped F5 acceptance case."""
        try:
            return repo.claim_work(work.work_id, claim_owner=owner, now=now).claim_owner
        except WorkNotClaimable:
            return None

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(claim, ["a", "b"]))
    assert sum(x is not None for x in results) == 1
    con = sqlite3.connect(repo.database_path)
    try:
        assert con.execute("SELECT COUNT(*) FROM attempt WHERE work_id=?", (work.work_id,)).fetchone()[0] == 1
    finally:
        con.close()


def test_expiry_reclaim_new_attempt_and_fence_and_stale_rejected(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    repo, work, now = _new_ready_repo(tmp_path, "reclaim.sqlite3")
    first = repo.claim_work(work.work_id, claim_owner="a", now=now, lease_duration_seconds=1)
    later = now + timedelta(seconds=2)
    second = repo.reclaim_work(work.work_id, claim_owner="b", now=later)
    assert second.attempt_no == 2 and second.fencing_token > first.fencing_token
    with pytest.raises(WorkNotClaimable):
        repo.mark_attempt_running(first.attempt_id, fencing_token=first.fencing_token, at=later)
    assert repo.mark_attempt_running(second.attempt_id, fencing_token=second.fencing_token, at=later).state == "RUNNING"


def test_retry_same_work_new_attempt(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    repo, work, now = _new_ready_repo(tmp_path, "retry.sqlite3")
    first = repo.claim_work(work.work_id, claim_owner="a", now=now)
    repo.mark_attempt_running(first.attempt_id, fencing_token=first.fencing_token, at=now)
    ready = repo.terminal_attempt(
        first.attempt_id,
        fencing_token=first.fencing_token,
        at=now + timedelta(seconds=1),
        success=False,
        retryable=True,
        reason="io",
    )
    assert ready.work_id == work.work_id and ready.state == "READY"
    second = repo.claim_work(work.work_id, claim_owner="b", now=now + timedelta(seconds=2))
    assert second.attempt_no == 2


def test_retry_budget_exhaustion_terminalizes_work(tmp_path):
    """A third retryable Attempt exhausts the bounded budget and terminalizes the same Work."""
    repo, work, now = _new_ready_repo(tmp_path, "retry-budget.sqlite3")
    for attempt_no in (1, 2, 3):
        attempt = repo.claim_work(
            work.work_id,
            claim_owner=f"worker-{attempt_no}",
            now=now + timedelta(seconds=attempt_no * 2),
        )
        repo.mark_attempt_running(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(seconds=attempt_no * 2),
        )
        state = repo.terminal_attempt(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(seconds=attempt_no * 2 + 1),
            success=False,
            retryable=True,
            reason="transient_io",
        )
        if attempt_no < 3:
            assert state.state == "READY" and state.work_id == work.work_id
        else:
            assert state.state == "FAILED"
            assert state.terminal_state == "FAILED"
            assert state.failure_state == "RETRY_BUDGET_EXHAUSTED"
            assert state.terminal_at is not None


def test_cross_work_current_fence_cannot_register_or_ack_other_publication(tmp_path):
    """A valid current fence is authority only for its own Work/Publication relation."""
    repo = SQLiteServerControlRepository(tmp_path / "cross-work.sqlite3")
    now = datetime.now(timezone.utc)

    def running(artifact: str):
        inputs = F5WorkIdentityInputs(
            domain_artifact_identity=artifact,
            source_revision="rev",
            content_identity=("a" if artifact == "one" else "b") * 64,
            policy_revision_identity="p",
        )
        work = repo.accept_work(inputs, payload_reference="x", provenance_reference="p", created_at=now)
        repo.mark_work_ready(work.work_id, at=now)
        attempt = repo.claim_work(work.work_id, claim_owner=artifact, now=now)
        repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
        return work, attempt

    work_one, attempt_one = running("one")
    _work_two, attempt_two = running("two")
    pub = repo.ensure_publication(
        work_id=work_one.work_id,
        attempt_id=attempt_one.attempt_id,
        fencing_token=attempt_one.fencing_token,
        domain_artifact_identity="one",
        source_revision="rev",
        content_checksum="a" * 64,
        content_size=1,
        at=now,
    )
    for target, kwargs in (
        ("STAGED", {}),
        ("PUBLISHING", {}),
        ("DURABLE_STORED", {"physical_locator": "objects/sha256/aa/" + "a" * 64, "evidence": "dw"}),
        ("INDEPENDENT_READBACK_VERIFIED", {"evidence": "rb"}),
    ):
        pub = repo.advance_publication(
            pub.publication_id,
            attempt_id=attempt_one.attempt_id,
            fencing_token=attempt_one.fencing_token,
            target_state=target,
            at=now,
            **kwargs,
        )

    with pytest.raises(WorkNotClaimable):
        repo.register_generation(
            pub.publication_id,
            attempt_id=attempt_two.attempt_id,
            fencing_token=attempt_two.fencing_token,
            at=now,
        )
    assert repo.resolve_generation("one") is None

    repo.register_generation(
        pub.publication_id,
        attempt_id=attempt_one.attempt_id,
        fencing_token=attempt_one.fencing_token,
        at=now,
    )
    with pytest.raises(WorkNotClaimable):
        repo.ack_publication(
            pub.publication_id,
            attempt_id=attempt_two.attempt_id,
            fencing_token=attempt_two.fencing_token,
            at=now,
        )
    assert repo.get_publication(pub.publication_id).state == "CANONICALLY_REGISTERED"


def test_f14_control_database_unavailable_blocks_control_operation(tmp_path):
    """F14 reaches an actual sqlite open failure; no control operation can proceed."""
    path = tmp_path / "unavailable.sqlite3"
    repo = SQLiteServerControlRepository(path)
    path.unlink()
    path.mkdir()
    with pytest.raises(sqlite3.OperationalError):
        repo.get_work("missing-work")


def test_f15_incompatible_schema_blocks_control_operation(tmp_path):
    """F15 mutates persisted user_version and proves the next real control read fails closed."""
    path = tmp_path / "schema-incompatible.sqlite3"
    repo = SQLiteServerControlRepository(path)
    con = sqlite3.connect(path)
    con.execute("PRAGMA user_version=2")
    con.commit()
    con.close()
    with pytest.raises(RuntimeError, match="unsupported control schema version 2"):
        repo.get_work("missing-work")


def test_terminal_success_cannot_return_to_running(tmp_path):
    """A succeeded Work/Attempt cannot be resurrected through repository SQL."""
    repo, work, now = _new_ready_repo(tmp_path, "terminal-success.sqlite3")
    attempt = repo.claim_work(work.work_id, claim_owner="a", now=now)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    terminal = repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(seconds=1),
        success=True,
        reason="complete",
    )
    assert terminal.state == "SUCCEEDED"
    with pytest.raises(WorkNotClaimable):
        repo.mark_attempt_running(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(seconds=2),
        )
    assert repo.get_work(work.work_id).state == "SUCCEEDED"
    assert repo.get_attempt(attempt.attempt_id).state == "SUCCEEDED"


def test_terminal_failed_work_cannot_return_to_running(tmp_path):
    """A non-retryable failed Work/Attempt stays terminal."""
    repo, work, now = _new_ready_repo(tmp_path, "terminal-failed.sqlite3")
    attempt = repo.claim_work(work.work_id, claim_owner="a", now=now)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(seconds=1),
        success=False,
        retryable=False,
        reason="fatal",
    )
    with pytest.raises(WorkNotClaimable):
        repo.mark_attempt_running(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(seconds=2),
        )
    assert repo.get_work(work.work_id).state == "FAILED"
    assert repo.get_attempt(attempt.attempt_id).state == "FAILED"


def test_terminal_attempt_cannot_renew_lease(tmp_path):
    """Terminal Attempt cannot regain authority through lease renewal."""
    repo, work, now = _new_ready_repo(tmp_path, "terminal-renew.sqlite3")
    attempt = repo.claim_work(work.work_id, claim_owner="a", now=now)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(seconds=1),
        success=True,
    )
    before = repo.get_attempt(attempt.attempt_id)
    with pytest.raises(WorkNotClaimable):
        repo.renew_attempt_lease(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            now=now + timedelta(seconds=2),
            new_expiry=now + timedelta(seconds=120),
        )
    after = repo.get_attempt(attempt.attempt_id)
    assert after == before


def test_terminal_work_cannot_be_reclaimed_after_lease_expiry(tmp_path):
    """Lease expiry never makes a terminal Work reclaimable."""
    repo, work, now = _new_ready_repo(tmp_path, "terminal-reclaim.sqlite3")
    attempt = repo.claim_work(work.work_id, claim_owner="a", now=now, lease_duration_seconds=1)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(milliseconds=500),
        success=True,
    )
    with pytest.raises(WorkNotClaimable):
        repo.reclaim_work(work.work_id, claim_owner="b", now=now + timedelta(seconds=2))
    con = sqlite3.connect(repo.database_path)
    try:
        assert con.execute("SELECT COUNT(*) FROM attempt WHERE work_id=?", (work.work_id,)).fetchone()[0] == 1
    finally:
        con.close()


def test_conflicting_repeat_terminal_transition_is_rejected(tmp_path):
    """A terminal result cannot be replaced by a later conflicting result."""
    repo, work, now = _new_ready_repo(tmp_path, "terminal-repeat.sqlite3")
    attempt = repo.claim_work(work.work_id, claim_owner="a", now=now)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=now)
    repo.terminal_attempt(
        attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(seconds=1),
        success=True,
        reason="first",
    )
    with pytest.raises(WorkNotClaimable):
        repo.terminal_attempt(
            attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(seconds=2),
            success=False,
            reason="conflict",
        )
    persisted = repo.get_attempt(attempt.attempt_id)
    assert persisted.state == "SUCCEEDED"
    assert persisted.terminal_reason == "first"
