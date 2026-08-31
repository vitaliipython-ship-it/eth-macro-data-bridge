"""Bounded F5 implementation acceptance tests for this mapped owner path."""

import sqlite3
from datetime import datetime, timezone

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from core.data.adapters.sqlite_schema import (
    CONTROL_SCHEMA_ID,
    initialize_or_validate,
    validate_schema_identity,
)
from core.data.repositories.server_control import WorkIdentityConflict
from server.work.models import F5WorkIdentityInputs


def test_schema_v1_initialize_and_cross_check(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    db = tmp_path / "control.sqlite3"
    con = sqlite3.connect(db)
    initialize_or_validate(con)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1
    assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert con.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert con.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert con.execute("SELECT schema_name FROM schema_metadata").fetchone()[0] == CONTROL_SCHEMA_ID
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "schema_metadata",
        "work",
        "attempt",
        "publication",
        "publication_generation",
        "publication_current_generation",
    } <= tables
    validate_schema_identity(con)


def test_schema_mismatch_and_downgrade_fail_closed(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    con = sqlite3.connect(tmp_path / "bad.sqlite3")
    initialize_or_validate(con)
    con.execute("PRAGMA user_version=2")
    con.commit()
    with pytest.raises(RuntimeError):
        initialize_or_validate(con)


def _inputs():
    """Exercise the mapped F5 acceptance case."""
    return F5WorkIdentityInputs(
        domain_artifact_identity="eth:a",
        source_revision="r1",
        content_identity="b" * 64,
        policy_revision_identity="p1",
    )


def test_t1_exact_duplicate_reconcile_and_conflict(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    repo = SQLiteServerControlRepository(tmp_path / "repo.sqlite3")
    now = datetime.now(timezone.utc)
    first = repo.accept_work(
        _inputs(),
        payload_reference="payload",
        provenance_reference="prov",
        created_at=now,
    )
    again = repo.accept_work(
        _inputs(),
        payload_reference="payload",
        provenance_reference="prov",
        created_at=now,
    )
    assert first.work_id == again.work_id and again.state == "PENDING"
    with pytest.raises(WorkIdentityConflict):
        repo.accept_work(
            _inputs(),
            payload_reference="different",
            provenance_reference="prov",
            created_at=now,
        )
    conflicted = repo.get_work(first.work_id)
    assert conflicted is not None
    assert conflicted.state == "FAILED"
    assert conflicted.terminal_state == "FAILED"
    assert conflicted.failure_state == "WORK_IDENTITY_CONFLICT"
    assert conflicted.terminal_at is not None


def test_t2_claim_persists_across_repository_restart(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    path = tmp_path / "repo.sqlite3"
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(path)
    work = repo.accept_work(
        _inputs(),
        payload_reference="payload",
        provenance_reference="prov",
        created_at=now,
    )
    repo.mark_work_ready(work.work_id, at=now)
    attempt = repo.claim_work(work.work_id, claim_owner="worker-1", now=now)
    assert attempt.attempt_no == 1 and attempt.fencing_token == 1 and attempt.state == "CLAIMED"
    reopened = SQLiteServerControlRepository(path)
    assert reopened.get_work(work.work_id).state == "CLAIMED"
    assert reopened.get_attempt(attempt.attempt_id).claim_owner == "worker-1"
