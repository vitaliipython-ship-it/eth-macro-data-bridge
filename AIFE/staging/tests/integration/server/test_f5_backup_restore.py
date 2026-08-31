"""Bounded F5 implementation acceptance tests for this mapped owner path."""

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from core.data.adapters.sqlite_control import (
    SQLiteServerControlRepository,
    restore_sqlite_backup,
)
from server.application.services import F5BoundedPublicationCoordinator
from server.runtime.recovery import (
    create_control_backup,
    reconcile_registered_objects,
    restore_control_backup,
)
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem
from server.work.models import F5WorkIdentityInputs


def published(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now = datetime(2026, 8, 30, 12, tzinfo=UTC)
    payload = b"backup-object"
    digest = hashlib.sha256(payload).hexdigest()
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    inputs = F5WorkIdentityInputs(
        domain_artifact_identity="artifact-backup",
        source_revision="r1",
        content_identity=digest,
        policy_revision_identity="p",
    )
    w = repo.accept_work(inputs, payload_reference="opaque", provenance_reference="prov", created_at=now)
    repo.mark_work_ready(w.work_id, at=now)
    a = repo.claim_work(w.work_id, claim_owner="w", now=now)
    repo.mark_attempt_running(a.attempt_id, fencing_token=a.fencing_token, at=now)
    F5BoundedPublicationCoordinator(repo, store).publish(
        work_id=w.work_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        domain_artifact_identity="artifact-backup",
        source_revision="r1",
        payload=payload,
        content_checksum=digest,
        at=now,
    )
    return repo, store


def test_f21_f22_backup_restore_reconciliation_and_readback(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    repo, store = published(tmp_path)
    e = create_control_backup(repo, tmp_path / "backup.sqlite3")
    assert e.size > 0 and len(e.sha256) == 64
    restored, proof = restore_control_backup(e, tmp_path / "restore/control.sqlite3")
    assert (
        proof.source_backup_sha256 == e.sha256
        and proof.source_backup_size == e.size
        and proof.integrity_check == "ok"
        and proof.schema_version == 1
        and proof.generation_count == 1
        and len(reconcile_registered_objects(restored, store)) == 1
    )


def test_f23_incompatible_schema_downgrade_rejected(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    bad = tmp_path / "bad.sqlite3"
    con = sqlite3.connect(bad)
    con.execute("PRAGMA user_version=2")
    con.commit()
    con.close()
    with pytest.raises(RuntimeError):
        restore_sqlite_backup(bad, tmp_path / "restored.sqlite3")


def test_restore_reconciliation_rejects_stale_current_generation_pointer(tmp_path):
    """Restore reconciliation proves the current pointer equals the maximum registered generation."""
    repo, store = published(tmp_path)
    evidence = create_control_backup(repo, tmp_path / "pointer-backup.sqlite3")
    restored, _proof = restore_control_backup(evidence, tmp_path / "pointer-restore/control.sqlite3")
    con = sqlite3.connect(tmp_path / "pointer-restore/control.sqlite3")
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("UPDATE publication_current_generation SET generation_no=generation_no+1")
    con.commit()
    con.close()
    with pytest.raises(RuntimeError, match="current generation pointer reconciliation mismatch"):
        reconcile_registered_objects(restored, store)


def test_restore_rejects_backup_bytes_that_do_not_match_frozen_identity(tmp_path):
    """F21 restore refuses a backup artifact changed after identity freeze."""
    repo, _store = published(tmp_path)
    evidence = create_control_backup(repo, tmp_path / "identity-backup.sqlite3")
    with (tmp_path / "identity-backup.sqlite3").open("ab") as handle:
        handle.write(b"tamper-after-freeze")
    with pytest.raises(RuntimeError, match="backup identity mismatch"):
        restore_control_backup(evidence, tmp_path / "identity-restore/control.sqlite3")


def test_f16_corrupt_active_control_db_requires_isolated_restore_before_authority_resumes(tmp_path):
    """F16 proves corrupt active control state fails closed and only an isolated exact restore is usable."""
    repo, store = published(tmp_path)
    backup = create_control_backup(repo, tmp_path / "f16-backup.sqlite3")
    active_path = Path(repo.database_path)
    active_path.write_bytes(b"not-a-sqlite-database")
    with pytest.raises(sqlite3.DatabaseError):
        repo.get_work("missing-work")

    restored, proof = restore_control_backup(backup, tmp_path / "f16-restore/control.sqlite3")
    assert proof.integrity_check == "ok"
    assert len(reconcile_registered_objects(restored, store)) == 1
