"""
Pure SQLite control row/identity and backup helpers for the bounded F5 adapter.

[Purpose]
    Содержать чистые row/identity/backup helpers bounded F5 SQLite adapter.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Детерминированные identity helpers, row projections, integrity checks и backup/restore helpers.

[Usage]
    Использовать через typed bounded F5 interfaces и owner-mapped application/runtime composition.

[Architecture]
    Модуль принадлежит generic AIFE Server execution/storage contour; Data Bridge сохраняет
    market-data semantic authority.

[Note]
    Реализация рассчитана на one-server SQLite/WAL + immutable filesystem profile и fail-closed invariants.

[Warning]
    Не переносить domain/provider semantics в Work IDs, SQLite keys, filesystem locators или execution state.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import cast

from core.data.adapters.sqlite_schema import (
    CONTROL_SCHEMA_ID,
    CONTROL_SCHEMA_INITIAL_VERSION,
    initialize_or_validate,
)
from core.data.repositories.server_control import (
    ControlBackupEvidence,
    ControlRestoreEvidence,
    StoredAttempt,
    StoredGeneration,
    StoredPublication,
    StoredWork,
)
from server._validation import require_aware
from server.publication.models import build_f5_generation_identity


def _utc(value: datetime) -> datetime:
    """Normalize one aware timestamp to UTC."""
    return require_aware(value, "timestamp").astimezone(timezone.utc)


_PUBLICATION_SEQUENCE = (
    "INGEST_DURABLE",
    "STAGED",
    "PUBLISHING",
    "DURABLE_STORED",
    "INDEPENDENT_READBACK_VERIFIED",
    "CANONICALLY_REGISTERED",
    "ACKED",
)


def _iso(value: datetime) -> str:
    """Serialize one aware timestamp using the bounded UTC representation."""
    return _utc(value).isoformat()


def _parse(value: str) -> datetime:
    """Parse one persisted ISO timestamp."""
    return datetime.fromisoformat(value)


def _canonical_digest(value: object) -> str:
    """Hash one deterministic canonical JSON value."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _attempt_id(work_id: str, attempt_no: int) -> str:
    """Derive the deterministic F5 Attempt identity."""
    return "attempt:f5:v1:" + _canonical_digest({"ATTEMPT_NO": attempt_no, "WORK_ID": work_id})


def _row_to_stored_work(row: sqlite3.Row) -> StoredWork:
    """Project one persisted Work row into the repository DTO."""
    return StoredWork(
        work_id=row["work_id"],
        work_kind=row["work_kind"],
        logical_input_identity=row["logical_input_identity"],
        scheduling_slot_identity=row["scheduling_slot_identity"],
        payload_reference=row["payload_reference"],
        provenance_reference=row["provenance_reference"],
        policy_revision_identity=row["policy_revision_identity"],
        immutable_input_digest=row["immutable_input_digest"],
        created_at=_parse(row["created_at"]),
        updated_at=_parse(row["updated_at"]),
        state=row["state"],
        terminal_state=row["terminal_state"],
        failure_state=row["failure_state"],
        terminal_at=None if row["terminal_at"] is None else _parse(row["terminal_at"]),
        record_version=int(row["record_version"]),
    )


def _row_to_stored_attempt(row: sqlite3.Row) -> StoredAttempt:
    """Project one persisted Attempt row into the repository DTO."""
    return StoredAttempt(
        attempt_id=row["attempt_id"],
        work_id=row["work_id"],
        attempt_no=int(row["attempt_no"]),
        claim_id=row["claim_id"],
        claim_owner=row["claim_owner"],
        lease_id=row["lease_id"],
        lease_acquired_at=_parse(row["lease_acquired_at"]),
        lease_expires_at=_parse(row["lease_expires_at"]),
        fencing_token=int(row["fencing_token"]),
        state=row["state"],
        started_at=None if row["started_at"] is None else _parse(row["started_at"]),
        terminated_at=None if row["terminated_at"] is None else _parse(row["terminated_at"]),
        terminal_reason=row["terminal_reason"],
    )


def _row_to_stored_publication(row: sqlite3.Row) -> StoredPublication:
    """Project one persisted Publication row into the repository DTO."""
    return StoredPublication(
        row["publication_id"],
        row["work_id"],
        row["attempt_id"],
        row["domain_artifact_identity"],
        row["source_revision"],
        row["content_checksum"],
        int(row["content_size"]),
        row["logical_target_identity"],
        row["state"],
        row["physical_locator"],
        row["durable_write_evidence"],
        row["readback_evidence"],
        row["registration_evidence"],
        row["ack_evidence"],
        (None if row["registration_fencing_token"] is None else int(row["registration_fencing_token"])),
    )


def _row_to_stored_generation(row: sqlite3.Row) -> StoredGeneration:
    """Project one persisted Generation row into the repository DTO."""
    return StoredGeneration(
        row["generation_scope_identity"],
        row["generation_identity"],
        int(row["generation_no"]),
        row["publication_id"],
        row["source_revision"],
        row["content_checksum"],
        int(row["content_size"]),
        row["physical_locator"],
        int(row["registration_fencing_token"]),
    )


def _generation_matches_publication(generation: sqlite3.Row, publication: sqlite3.Row) -> bool:
    """Require one Generation to match the exact immutable Publication identity tuple."""
    expected_identity = build_f5_generation_identity(
        domain_artifact_identity=publication["domain_artifact_identity"],
        source_revision=publication["source_revision"],
        content_identity=publication["content_checksum"],
    )
    return bool(
        generation["publication_id"] == publication["publication_id"]
        and generation["generation_scope_identity"] == publication["domain_artifact_identity"]
        and generation["generation_identity"] == expected_identity
        and generation["source_revision"] == publication["source_revision"]
        and generation["content_checksum"] == publication["content_checksum"]
        and int(generation["content_size"]) == int(publication["content_size"])
        and generation["physical_locator"] == publication["physical_locator"]
    )


def _publication_state_compatible_with_registered_generation(publication: sqlite3.Row) -> bool:
    """Accept only lifecycle states that can coherently coexist with a persisted Generation."""
    state = publication["state"]
    if state not in {"INDEPENDENT_READBACK_VERIFIED", "CANONICALLY_REGISTERED", "ACKED"}:
        return False
    if not publication["durable_write_evidence"] or not publication["readback_evidence"]:
        return False
    if not publication["physical_locator"]:
        return False
    if state in {"CANONICALLY_REGISTERED", "ACKED"} and not publication["registration_evidence"]:
        return False
    if state == "ACKED" and (not publication["ack_evidence"] or not publication["acked_at"]):
        return False
    return True


def _validated_current_generation_pointer(
    con: sqlite3.Connection, generation_scope_identity: str
) -> sqlite3.Row | None:
    """Transitively validate Pointer -> maximum Generation -> owning Publication."""
    maxrow = con.execute(
        "SELECT COALESCE(MAX(generation_no),0) FROM publication_generation WHERE generation_scope_identity=?",
        (generation_scope_identity,),
    ).fetchone()
    max_generation_no = int(maxrow[0])
    current = con.execute(
        "SELECT * FROM publication_current_generation WHERE generation_scope_identity=?",
        (generation_scope_identity,),
    ).fetchone()
    if max_generation_no == 0:
        if current is not None:
            raise RuntimeError("current generation pointer corruption")
        return None
    if current is None or int(current["generation_no"]) != max_generation_no:
        raise RuntimeError("current generation pointer corruption")
    target = con.execute(
        "SELECT * FROM publication_generation WHERE generation_scope_identity=? AND generation_identity=?",
        (generation_scope_identity, current["generation_identity"]),
    ).fetchone()
    if target is None or int(target["generation_no"]) != int(current["generation_no"]):
        raise RuntimeError("current generation pointer corruption")
    expected_identity = build_f5_generation_identity(
        domain_artifact_identity=target["generation_scope_identity"],
        source_revision=target["source_revision"],
        content_identity=target["content_checksum"],
    )
    if target["generation_identity"] != expected_identity:
        raise RuntimeError("current generation pointer corruption")
    if int(current["registration_fencing_token"]) != int(target["registration_fencing_token"]):
        raise RuntimeError("current generation pointer corruption")
    publication = con.execute(
        "SELECT * FROM publication WHERE publication_id=?",
        (target["publication_id"],),
    ).fetchone()
    if (
        publication is None
        or not _generation_matches_publication(target, publication)
        or not _publication_state_compatible_with_registered_generation(publication)
    ):
        raise RuntimeError("current generation/publication relation corruption")
    return cast(sqlite3.Row, current)


def _resolve_generation_row(
    con: sqlite3.Connection, scope: str, generation_identity: str | None = None
) -> sqlite3.Row | None:
    """Resolve an exact or current Generation row without changing repository state."""
    if generation_identity is None:
        current = con.execute(
            "SELECT * FROM publication_current_generation WHERE generation_scope_identity=?",
            (scope,),
        ).fetchone()
        if current is None:
            return None
        generation_identity = current["generation_identity"]
        row = con.execute(
            "SELECT * FROM publication_generation WHERE generation_scope_identity=? AND generation_identity=?",
            (scope, generation_identity),
        ).fetchone()
        if row is None or int(row["generation_no"]) != int(current["generation_no"]):
            raise RuntimeError("current generation pointer reconciliation mismatch")
        return cast(sqlite3.Row, row)
    return con.execute(
        "SELECT * FROM publication_generation WHERE generation_scope_identity=? AND generation_identity=?",
        (scope, generation_identity),
    ).fetchone()


def _backup_sqlite_database(database_path: Path, destination: str | Path) -> ControlBackupEvidence:
    """Create one exact bounded SQLite backup artifact."""
    dest = Path(destination)
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(database_path, timeout=5.0)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
        target.commit()
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("backup integrity_check failed")
        version = int(target.execute("PRAGMA user_version").fetchone()[0])
        row = target.execute("SELECT schema_name,schema_version FROM schema_metadata").fetchone()
        if row != (CONTROL_SCHEMA_ID, CONTROL_SCHEMA_INITIAL_VERSION) or version != CONTROL_SCHEMA_INITIAL_VERSION:
            raise RuntimeError("backup schema identity mismatch")
    finally:
        target.close()
        source.close()
    digest = sha256(dest.read_bytes()).hexdigest()
    return ControlBackupEvidence(
        str(dest),
        digest,
        dest.stat().st_size,
        CONTROL_SCHEMA_ID,
        CONTROL_SCHEMA_INITIAL_VERSION,
    )


def _verify_backup_identity(
    source_path: Path, expected_sha256: str | None, expected_size: int | None
) -> tuple[str, int]:
    """Read and verify the exact frozen backup artifact before restore materialization."""
    actual_size = source_path.stat().st_size
    actual_sha256 = sha256(source_path.read_bytes()).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise RuntimeError("backup identity mismatch: sha256")
    if expected_size is not None and actual_size != expected_size:
        raise RuntimeError("backup identity mismatch: size")
    return actual_sha256, actual_size


def _restore_sqlite_backup_artifact(
    backup_path: str | Path,
    destination: str | Path,
    *,
    expected_backup_sha256: str | None = None,
    expected_backup_size: int | None = None,
) -> ControlRestoreEvidence:
    """Restore and independently verify one exact SQLite backup artifact."""
    source_path = Path(backup_path)
    backup_identity = _verify_backup_identity(source_path, expected_backup_sha256, expected_backup_size)
    dest = Path(destination)
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(dest)
    try:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("backup corrupt or unusable")
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()
    verification = sqlite3.connect(dest, timeout=5.0)
    try:
        initialize_or_validate(verification)
        integrity = verification.execute("PRAGMA integrity_check").fetchone()[0]
        version = int(verification.execute("PRAGMA user_version").fetchone()[0])
        row = verification.execute("SELECT schema_name,schema_version FROM schema_metadata").fetchone()
        if (
            integrity != "ok"
            or tuple(row) != (CONTROL_SCHEMA_ID, CONTROL_SCHEMA_INITIAL_VERSION)
            or version != CONTROL_SCHEMA_INITIAL_VERSION
        ):
            raise RuntimeError("restored schema identity mismatch")
        generation_count = int(verification.execute("SELECT COUNT(*) FROM publication_generation").fetchone()[0])
    finally:
        verification.close()
    return ControlRestoreEvidence(
        str(dest),
        backup_identity[0],
        backup_identity[1],
        integrity,
        CONTROL_SCHEMA_ID,
        version,
        generation_count,
    )
