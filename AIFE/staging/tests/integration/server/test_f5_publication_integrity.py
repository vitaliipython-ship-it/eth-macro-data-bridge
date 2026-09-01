"""
F5 T6/T7 persisted publication-integrity acceptance tests.

[Purpose]
    Доказать f5 T6/T7 persisted publication-integrity acceptance tests.

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
from datetime import datetime, timedelta, timezone

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.publication.models import build_f5_generation_identity
from tests.integration.server.test_f5_publication_recovery import (
    _ack_ready_publication,
    _publication_ack_columns,
    _register_generation,
)


def _retry_generation_registration(repo, publication_id, attempt, at):
    """Retry T6 registration with the current attempt authority."""
    authority = {"attempt_id": attempt.attempt_id, "fencing_token": attempt.fencing_token, "at": at}
    return repo.register_generation(publication_id, **authority)


def _guarded_ack(repo, publication_id, attempt, at):
    """Execute guarded T7 ACK with the current attempt authority."""
    authority = {"attempt_id": attempt.attempt_id, "fencing_token": attempt.fencing_token, "at": at}
    return repo.ack_publication(publication_id, **authority)


def test_t6_rejects_equal_number_conflicting_current_generation_pointer(tmp_path):
    """An equal generation number is idempotent only for the exact registered identity."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "equal-pointer.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
            ("gen:f5:v1:conflicting", generation.generation_scope_identity),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        _retry_generation_registration(repo, publication.publication_id, attempt, now)


def test_t6_rejects_future_bogus_current_generation_pointer(tmp_path):
    """A pointer cannot claim a generation number that has not been durably registered."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "future-pointer.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            (
                "UPDATE publication_current_generation SET generation_identity=?,generation_no=generation_no+10 "
                "WHERE generation_scope_identity=?"
            ),
            ("gen:f5:v1:future-bogus", generation.generation_scope_identity),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        _retry_generation_registration(repo, publication.publication_id, attempt, now)


def test_t6_rejects_stale_lower_current_generation_pointer(tmp_path):
    """The current pointer must equal the maximum registered generation before any T6 retry."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "lower-pointer.sqlite3")
    old_publication, old_attempt, old_generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    _new_publication, _new_attempt, new_generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r2",
        content="b" * 64,
        at=now,
    )
    assert new_generation.generation_no > old_generation.generation_no
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            (
                "UPDATE publication_current_generation SET generation_identity=?,generation_no=? "
                "WHERE generation_scope_identity=?"
            ),
            (
                old_generation.generation_identity,
                old_generation.generation_no,
                old_generation.generation_scope_identity,
            ),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        _retry_generation_registration(repo, old_publication.publication_id, old_attempt, now)


@pytest.mark.parametrize(
    ("field", "value", "coherent_pointer"),
    [
        ("source_revision", "tampered-revision", False),
        ("generation_scope_identity", "tampered-scope", False),
        ("generation_identity", "gen:f5:v1:tampered", True),
        ("content_checksum", "e" * 64, False),
        ("content_size", 999, False),
        ("physical_locator", "objects/sha256/ee/tampered", False),
    ],
)
def test_t6_rejects_existing_generation_publication_identity_corruption(tmp_path, field, value, coherent_pointer):
    """T6 idempotent reconciliation rejects any persisted generation/Publication identity mismatch."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"existing-{field}.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="existing-generation-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            f"UPDATE publication_generation SET {field}=? WHERE publication_id=?",
            (value, publication.publication_id),
        )
        if coherent_pointer:
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                (value, generation.generation_scope_identity),
            )
        con.execute(
            "UPDATE publication SET state='INDEPENDENT_READBACK_VERIFIED',"
            "registration_evidence=NULL,registration_fencing_token=NULL WHERE publication_id=?",
            (publication.publication_id,),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="identity corruption|pointer corruption"):
        _retry_generation_registration(repo, publication.publication_id, attempt, now)
    assert repo.get_publication(publication.publication_id).state == "INDEPENDENT_READBACK_VERIFIED"


def _publication_row(repo, publication_id):
    """Read one persisted Publication row independently of repository projections."""
    con = sqlite3.connect(repo.database_path)
    try:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM publication WHERE publication_id=?", (publication_id,)).fetchone()
        return dict(row)
    finally:
        con.close()


@pytest.mark.parametrize("state", ["STAGED", "PUBLISHING", "INGEST_DURABLE"])
def test_t6_existing_generation_rejects_impossible_early_publication_state(tmp_path, state):
    """R03-001: an existing Generation cannot legitimize a Publication before independent readback."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"r03-001-{state}.sqlite3")
    publication, attempt, _generation = _register_generation(
        repo,
        artifact=f"r03-state-{state}",
        revision="r1",
        content="1" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            "UPDATE publication SET state=?,registration_evidence=NULL,registration_fencing_token=NULL "
            "WHERE publication_id=?",
            (state, publication.publication_id),
        )
        con.commit()
    finally:
        con.close()
    before = _publication_row(repo, publication.publication_id)
    with pytest.raises(RuntimeError, match="lifecycle corruption"):
        _retry_generation_registration(repo, publication.publication_id, attempt, now)
    after = _publication_row(repo, publication.publication_id)
    assert after == before


@pytest.mark.parametrize("state", ["INDEPENDENT_READBACK_VERIFIED", "CANONICALLY_REGISTERED", "ACKED"])
def test_t6_existing_generation_legal_state_matrix(tmp_path, state):
    """T6-A/B/C: exact existing registration is recoverable/idempotent only in legal lifecycle states."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"t6-legal-{state}.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact=f"t6-legal-{state}",
        revision="r1",
        content="2" * 64,
        at=now,
    )
    if state == "INDEPENDENT_READBACK_VERIFIED":
        con = sqlite3.connect(repo.database_path)
        try:
            con.execute(
                "UPDATE publication SET state='INDEPENDENT_READBACK_VERIFIED',registration_evidence=NULL,"
                "registration_fencing_token=NULL WHERE publication_id=?",
                (publication.publication_id,),
            )
            con.commit()
        finally:
            con.close()
        before = _publication_row(repo, publication.publication_id)
        assert before["registration_evidence"] is None
        returned = _retry_generation_registration(repo, publication.publication_id, attempt, now)
        after = _publication_row(repo, publication.publication_id)
        assert returned.generation_identity == generation.generation_identity
        assert after["state"] == "CANONICALLY_REGISTERED"
        assert after["registration_evidence"] == "idempotent-generation:" + generation.generation_identity
        return
    if state == "ACKED":
        _guarded_ack(repo, publication.publication_id, attempt, now)
    before = _publication_row(repo, publication.publication_id)
    returned = repo.register_generation(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(milliseconds=1),
    )
    after = _publication_row(repo, publication.publication_id)
    assert returned.generation_identity == generation.generation_identity
    assert after == before


@pytest.mark.parametrize(
    "variant",
    [
        "missing_owning_publication",
        "scope_mismatch",
        "source_revision_mismatch",
        "generation_identity_mismatch",
        "checksum_mismatch",
        "size_mismatch",
        "locator_mismatch",
        "publication_lifecycle_mismatch",
    ],
)
def test_t6_current_pointer_transitively_validates_generation_publication(
    tmp_path, variant
):  # pylint: disable=too-many-locals
    """R03-002: current pointer trust is transitive through Generation to its owning Publication."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"r03-002-{variant}.sqlite3")
    old_publication, old_attempt, _old_generation = _register_generation(
        repo,
        artifact="r03-current-scope",
        revision="r1",
        content="3" * 64,
        at=now,
    )
    new_publication, _new_attempt, new_generation = _register_generation(
        repo,
        artifact="r03-current-scope",
        revision="r2",
        content="4" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        if variant == "missing_owning_publication":
            con.execute("DELETE FROM publication WHERE publication_id=?", (new_publication.publication_id,))
        elif variant == "scope_mismatch":
            con.execute(
                "UPDATE publication SET domain_artifact_identity=? WHERE publication_id=?",
                ("r03-other-scope", new_publication.publication_id),
            )
        elif variant in {"source_revision_mismatch", "checksum_mismatch"}:
            new_revision = "r2-corrupt" if variant == "source_revision_mismatch" else new_publication.source_revision
            new_checksum = "5" * 64 if variant == "checksum_mismatch" else new_publication.content_checksum
            new_identity = build_f5_generation_identity(
                domain_artifact_identity=new_generation.generation_scope_identity,
                source_revision=new_revision,
                content_identity=new_checksum,
            )
            con.execute(
                "UPDATE publication_generation SET source_revision=?,content_checksum=?,generation_identity=? "
                "WHERE publication_id=?",
                (new_revision, new_checksum, new_identity, new_publication.publication_id),
            )
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                (new_identity, new_generation.generation_scope_identity),
            )
        elif variant == "generation_identity_mismatch":
            con.execute(
                "UPDATE publication_generation SET generation_identity=? WHERE publication_id=?",
                ("gen:f5:v1:corrupt-current", new_publication.publication_id),
            )
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                ("gen:f5:v1:corrupt-current", new_generation.generation_scope_identity),
            )
        elif variant == "size_mismatch":
            con.execute(
                "UPDATE publication_generation SET content_size=content_size+1 WHERE publication_id=?",
                (new_publication.publication_id,),
            )
        elif variant == "locator_mismatch":
            con.execute(
                "UPDATE publication_generation SET physical_locator=? WHERE publication_id=?",
                ("objects/sha256/ff/corrupt", new_publication.publication_id),
            )
        elif variant == "publication_lifecycle_mismatch":
            con.execute(
                "UPDATE publication SET state='STAGED',registration_evidence=NULL WHERE publication_id=?",
                (new_publication.publication_id,),
            )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="pointer corruption|relation corruption"):
        _retry_generation_registration(repo, old_publication.publication_id, old_attempt, now)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generation_scope_identity", "post-ack-scope-corrupt"),
        ("source_revision", "post-ack-revision-corrupt"),
        ("generation_identity", "gen:f5:v1:post-ack-corrupt"),
        ("content_checksum", "6" * 64),
        ("content_size", 999),
        ("physical_locator", "objects/sha256/66/post-ack-corrupt"),
    ],
)
def test_f26_duplicate_ack_revalidates_post_ack_generation_integrity(tmp_path, field, value):
    """R03-003: duplicate ACK rejects every persisted Generation corruption without rewriting ACK evidence."""
    now, repo, _work, attempt, publication = _ack_ready_publication(tmp_path / field, name=f"post-ack-{field}")
    first = _guarded_ack(repo, publication.publication_id, attempt, now)
    assert first.state == "ACKED"
    before = _publication_ack_columns(repo, publication.publication_id)
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute(
            f"UPDATE publication_generation SET {field}=? WHERE publication_id=?",
            (value, publication.publication_id),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(ValueError, match="ILLEGAL_ACK"):
        repo.ack_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(milliseconds=1),
        )
    after = _publication_ack_columns(repo, publication.publication_id)
    assert before[0] == after[0] == "ACKED"
    assert after[1:] == before[1:]
    con = sqlite3.connect(repo.database_path)
    try:
        persisted = con.execute(
            f"SELECT {field} FROM publication_generation WHERE publication_id=?",
            (publication.publication_id,),
        ).fetchone()[0]
    finally:
        con.close()
    assert persisted == value
