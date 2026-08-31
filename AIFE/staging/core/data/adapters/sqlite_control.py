"""SQLite/WAL implementation of the bounded F5 control repository."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Iterator, cast

from core.data.adapters.sqlite_schema import (
    CONTROL_SCHEMA_ID,
    CONTROL_SCHEMA_INITIAL_VERSION,
    initialize_or_validate,
)
from core.data.repositories.server_control import (
    ControlBackupEvidence,
    ControlStateConflict,
    ControlRestoreEvidence,
    StoredAttempt,
    StoredGeneration,
    StoredPublication,
    StoredWork,
    WorkIdentityConflict,
    WorkNotClaimable,
)
from server._validation import require_aware, require_non_empty
from server.publication.models import (
    build_f5_generation_identity,
    build_f5_logical_target_identity,
    build_f5_publication_id,
)
from server.work.models import F5WorkIdentityInputs, MAX_AUTOMATIC_ATTEMPTS_PER_WORK


def _utc(value: datetime) -> datetime:
    """F5 contract-bound function `_utc`. EN summary: bounded F5 function."""
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
    """F5 contract-bound function `_iso`. EN summary: bounded F5 function."""
    return _utc(value).isoformat()


def _parse(value: str) -> datetime:
    """F5 contract-bound function `_parse`. EN summary: bounded F5 function."""
    return datetime.fromisoformat(value)


def _canonical_digest(value: object) -> str:
    """F5 contract-bound function `_canonical_digest`. EN summary: bounded F5 function."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def _attempt_id(work_id: str, attempt_no: int) -> str:
    """F5 contract-bound function `_attempt_id`. EN summary: bounded F5 function."""
    return "attempt:f5:v1:" + _canonical_digest({"ATTEMPT_NO": attempt_no, "WORK_ID": work_id})


class SQLiteServerControlRepository:
    """One-server transactional control adapter; every operation owns one connection."""

    def __init__(self, database_path: str | Path) -> None:
        """F5 contract-bound function `__init__`. EN summary: bounded F5 function."""
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as con:
            initialize_or_validate(con)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """F5 contract-bound function `_connection`. EN summary: bounded F5 function."""
        con = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
        con.row_factory = sqlite3.Row
        initialize_or_validate(con)
        try:
            yield con
        finally:
            con.close()

    @staticmethod
    def _stored_work(row: sqlite3.Row) -> StoredWork:
        """F5 contract-bound function `_stored_work`. EN summary: bounded F5 function."""
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

    @staticmethod
    def _stored_attempt(row: sqlite3.Row) -> StoredAttempt:
        """F5 contract-bound function `_stored_attempt`. EN summary: bounded F5 function."""
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

    def accept_work(  # pylint: disable=too-many-locals
        self,
        inputs: F5WorkIdentityInputs,
        *,
        payload_reference: str,
        provenance_reference: str,
        created_at: datetime,
    ) -> StoredWork:
        """F5 contract-bound function `accept_work`. EN summary: bounded F5 function."""
        payload = require_non_empty(payload_reference, "payload_reference")
        provenance = require_non_empty(provenance_reference, "provenance_reference")
        created = _utc(created_at)
        work_id = inputs.work_id.value
        immutable = {
            **inputs.canonical_mapping(),
            "PAYLOAD_REFERENCE": payload,
            "PROVENANCE_REFERENCE": provenance,
        }
        immutable_digest = _canonical_digest(immutable)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                existing = con.execute(
                    "SELECT * FROM work WHERE logical_input_identity=?",
                    (inputs.logical_input_identity,),
                ).fetchone()
                if existing is not None:
                    same = (
                        existing["work_id"] == work_id
                        and existing["work_kind"] == inputs.work_kind
                        and existing["scheduling_slot_identity"] == inputs.scheduling_slot_identity
                        and existing["payload_reference"] == payload
                        and existing["provenance_reference"] == provenance
                        and existing["policy_revision_identity"] == inputs.policy_revision_identity
                        and existing["immutable_input_digest"] == immutable_digest
                    )
                    if not same:
                        self._fail_work(
                            con,
                            existing["work_id"],
                            at=created,
                            failure_state="WORK_IDENTITY_CONFLICT",
                        )
                        con.commit()
                        raise WorkIdentityConflict("same logical input has different immutable tuple")
                    con.commit()
                    return self._stored_work(existing)
                stamp = _iso(created)
                con.execute(
                    """INSERT INTO work(
                    work_id,work_kind,logical_input_identity,scheduling_slot_identity,payload_reference,
                    provenance_reference,policy_revision_identity,immutable_input_digest,
                    created_at,updated_at,state,record_version
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (
                        work_id,
                        inputs.work_kind,
                        inputs.logical_input_identity,
                        inputs.scheduling_slot_identity,
                        payload,
                        provenance,
                        inputs.policy_revision_identity,
                        immutable_digest,
                        stamp,
                        stamp,
                        "PENDING",
                    ),
                )
                row = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
                con.commit()
                assert row is not None
                return self._stored_work(row)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def get_work(self, work_id: str) -> StoredWork | None:
        """F5 contract-bound function `get_work`. EN summary: bounded F5 function."""
        with self._connection() as con:
            row = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
            return None if row is None else self._stored_work(row)

    def mark_work_ready(self, work_id: str, *, at: datetime) -> StoredWork:
        """F5 contract-bound function `mark_work_ready`. EN summary: bounded F5 function."""
        stamp = _iso(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                row = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
                if row is None:
                    raise KeyError(work_id)
                if row["state"] == "READY":
                    con.commit()
                    return self._stored_work(row)
                if row["state"] != "PENDING":
                    raise WorkNotClaimable(f"cannot ready state={row['state']}")
                con.execute(
                    "UPDATE work SET state='READY',updated_at=?,record_version=record_version+1 WHERE work_id=?",
                    (stamp, work_id),
                )
                out = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
                con.commit()
                assert out is not None
                return self._stored_work(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def claim_work(  # pylint: disable=too-many-locals
        self,
        work_id: str,
        *,
        claim_owner: str,
        now: datetime,
        lease_duration_seconds: int = 60,
    ) -> StoredAttempt:
        """F5 contract-bound function `claim_work`. EN summary: bounded F5 function."""
        owner = require_non_empty(claim_owner, "claim_owner")
        moment = _utc(now)
        if lease_duration_seconds <= 0:
            raise ValueError("lease duration must be positive")
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                work = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
                if work is None:
                    raise KeyError(work_id)
                if work["state"] != "READY":
                    raise WorkNotClaimable(f"work state={work['state']}")
                maxrow = con.execute(
                    "SELECT COALESCE(MAX(attempt_no),0),COALESCE(MAX(fencing_token),0) FROM attempt WHERE work_id=?",
                    (work_id,),
                ).fetchone()
                attempt_no = int(maxrow[0]) + 1
                fence = int(maxrow[1]) + 1
                if attempt_no > MAX_AUTOMATIC_ATTEMPTS_PER_WORK:
                    self._fail_work(
                        con,
                        work_id,
                        at=moment,
                        failure_state="RETRY_BUDGET_EXHAUSTED",
                    )
                    con.commit()
                    raise WorkNotClaimable("automatic retry budget exhausted")
                aid = _attempt_id(work_id, attempt_no)
                claim_id = "claim:f5:v1:" + aid
                lease_id = "lease:f5:v1:" + aid
                expiry = moment + timedelta(seconds=lease_duration_seconds)
                con.execute(
                    """INSERT INTO attempt(attempt_id,work_id,attempt_no,claim_id,claim_owner,lease_id,
                    lease_acquired_at,lease_expires_at,fencing_token,state) VALUES(?,?,?,?,?,?,?,?,?,'CLAIMED')""",
                    (
                        aid,
                        work_id,
                        attempt_no,
                        claim_id,
                        owner,
                        lease_id,
                        _iso(moment),
                        _iso(expiry),
                        fence,
                    ),
                )
                con.execute(
                    "UPDATE work SET state='CLAIMED',updated_at=?,record_version=record_version+1 WHERE work_id=?",
                    (_iso(moment), work_id),
                )
                row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (aid,)).fetchone()
                con.commit()
                assert row is not None
                return self._stored_attempt(row)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    @staticmethod
    def _fail_work(con: sqlite3.Connection, work_id: str, *, at: datetime, failure_state: str) -> None:
        """Persist one fail-closed non-retryable Work terminal state."""
        stamp = _iso(at)
        con.execute(
            (
                "UPDATE work SET state='FAILED',terminal_state='FAILED',failure_state=?,"
                "terminal_at=COALESCE(terminal_at,?),updated_at=?,record_version=record_version+1 "
                "WHERE work_id=? AND state NOT IN('SUCCEEDED','FAILED','CANCELLED')"
            ),
            (failure_state, stamp, stamp, work_id),
        )

    @classmethod
    def _fail_attempt_and_work(
        cls,
        con: sqlite3.Connection,
        attempt_id: str,
        *,
        at: datetime,
        failure_state: str,
    ) -> None:
        """Fail one Attempt and its bound Work atomically for a non-retryable violation."""
        attempt = con.execute("SELECT work_id FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
        if attempt is None:
            raise KeyError(attempt_id)
        stamp = _iso(at)
        con.execute(
            (
                "UPDATE attempt SET state='FAILED',terminated_at=COALESCE(terminated_at,?),"
                "terminal_reason=COALESCE(terminal_reason,?) WHERE attempt_id=? "
                "AND state NOT IN('SUCCEEDED','FAILED','ABANDONED')"
            ),
            (stamp, failure_state, attempt_id),
        )
        cls._fail_work(con, attempt["work_id"], at=at, failure_state=failure_state)

    def get_attempt(self, attempt_id: str) -> StoredAttempt | None:
        """F5 contract-bound function `get_attempt`. EN summary: bounded F5 function."""
        with self._connection() as con:
            row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
            return None if row is None else self._stored_attempt(row)

    def _current_attempt_row(self, con: sqlite3.Connection, work_id: str) -> sqlite3.Row | None:
        """F5 contract-bound function `_current_attempt_row`. EN summary: bounded F5 function."""
        return cast(
            sqlite3.Row | None,
            con.execute(
                "SELECT * FROM attempt WHERE work_id=? ORDER BY fencing_token DESC LIMIT 1",
                (work_id,),
            ).fetchone(),
        )

    def renew_attempt_lease(
        self,
        attempt_id: str,
        *,
        fencing_token: int,
        now: datetime,
        new_expiry: datetime,
    ) -> StoredAttempt:
        """F5 contract-bound function `renew_attempt_lease`. EN summary: bounded F5 function."""
        moment = _utc(now)
        expiry = _utc(new_expiry)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
                if row is None:
                    raise KeyError(attempt_id)
                current = self._current_attempt_row(con, row["work_id"])
                work = con.execute("SELECT * FROM work WHERE work_id=?", (row["work_id"],)).fetchone()
                if current is None or current["attempt_id"] != attempt_id or int(row["fencing_token"]) != fencing_token:
                    raise WorkNotClaimable("stale fence")
                if work is None or work["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    raise WorkNotClaimable("terminal Work cannot renew authority")
                if row["state"] not in ("CLAIMED", "RUNNING"):
                    raise WorkNotClaimable("terminal Attempt cannot renew authority")
                if _parse(row["lease_expires_at"]) <= moment:
                    raise WorkNotClaimable("lease expired")
                if expiry <= moment or expiry <= _parse(row["lease_expires_at"]):
                    raise ValueError("lease expiry must extend")
                con.execute(
                    "UPDATE attempt SET lease_expires_at=? WHERE attempt_id=?",
                    (_iso(expiry), attempt_id),
                )
                out = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
                con.commit()
                return self._stored_attempt(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def reclaim_work(  # pylint: disable=too-many-locals
        self,
        work_id: str,
        *,
        claim_owner: str,
        now: datetime,
        lease_duration_seconds: int = 60,
    ) -> StoredAttempt:
        """F5 contract-bound function `reclaim_work`. EN summary: bounded F5 function."""
        owner = require_non_empty(claim_owner, "claim_owner")
        moment = _utc(now)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                work = con.execute("SELECT * FROM work WHERE work_id=?", (work_id,)).fetchone()
                if work is None:
                    raise KeyError(work_id)
                if work["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    raise WorkNotClaimable("terminal Work cannot be reclaimed")
                current = self._current_attempt_row(con, work_id)
                if current is None:
                    raise WorkNotClaimable("no attempt to reclaim")
                if _parse(current["lease_expires_at"]) > moment and current["state"] != "ABANDONED":
                    raise WorkNotClaimable("current lease remains authoritative")
                if current["state"] not in ("FAILED", "SUCCEEDED", "ABANDONED"):
                    con.execute(
                        (
                            "UPDATE attempt SET state='ABANDONED',terminated_at=?,"
                            "terminal_reason=COALESCE(terminal_reason,'lease_reclaimed') "
                            "WHERE attempt_id=?"
                        ),
                        (_iso(moment), current["attempt_id"]),
                    )
                maxrow = con.execute(
                    "SELECT MAX(attempt_no),MAX(fencing_token) FROM attempt WHERE work_id=?",
                    (work_id,),
                ).fetchone()
                attempt_no = int(maxrow[0]) + 1
                fence = int(maxrow[1]) + 1
                if attempt_no > MAX_AUTOMATIC_ATTEMPTS_PER_WORK:
                    self._fail_work(
                        con,
                        work_id,
                        at=moment,
                        failure_state="RETRY_BUDGET_EXHAUSTED",
                    )
                    con.commit()
                    raise WorkNotClaimable("automatic retry budget exhausted")
                aid = _attempt_id(work_id, attempt_no)
                cid = "claim:f5:v1:" + aid
                lid = "lease:f5:v1:" + aid
                expiry = moment + timedelta(seconds=lease_duration_seconds)
                con.execute(
                    (
                        "INSERT INTO attempt(attempt_id,work_id,attempt_no,claim_id,claim_owner,lease_id,"
                        "lease_acquired_at,lease_expires_at,fencing_token,state) "
                        "VALUES(?,?,?,?,?,?,?,?,?,'CLAIMED')"
                    ),
                    (
                        aid,
                        work_id,
                        attempt_no,
                        cid,
                        owner,
                        lid,
                        _iso(moment),
                        _iso(expiry),
                        fence,
                    ),
                )
                con.execute(
                    "UPDATE work SET state='CLAIMED',updated_at=?,record_version=record_version+1 WHERE work_id=?",
                    (_iso(moment), work_id),
                )
                out = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (aid,)).fetchone()
                con.commit()
                return self._stored_attempt(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def mark_attempt_running(self, attempt_id: str, *, fencing_token: int, at: datetime) -> StoredAttempt:
        """F5 contract-bound function `mark_attempt_running`. EN summary: bounded F5 function."""
        moment = _utc(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
                if row is None:
                    raise KeyError(attempt_id)
                current = self._current_attempt_row(con, row["work_id"])
                work = con.execute("SELECT * FROM work WHERE work_id=?", (row["work_id"],)).fetchone()
                if (
                    current is None
                    or current["attempt_id"] != attempt_id
                    or int(row["fencing_token"]) != fencing_token
                    or _parse(row["lease_expires_at"]) <= moment
                ):
                    raise WorkNotClaimable("stale or expired authority")
                if work is None or work["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    raise WorkNotClaimable("terminal Work cannot return to RUNNING")
                if row["state"] == "RUNNING" and work["state"] == "RUNNING":
                    con.commit()
                    return self._stored_attempt(row)
                if row["state"] != "CLAIMED" or work["state"] != "CLAIMED":
                    raise WorkNotClaimable("illegal persisted transition to RUNNING")
                con.execute(
                    "UPDATE attempt SET state='RUNNING',started_at=COALESCE(started_at,?) WHERE attempt_id=?",
                    (_iso(moment), attempt_id),
                )
                con.execute(
                    "UPDATE work SET state='RUNNING',updated_at=?,record_version=record_version+1 WHERE work_id=?",
                    (_iso(moment), row["work_id"]),
                )
                out = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
                con.commit()
                return self._stored_attempt(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def terminal_attempt(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        attempt_id: str,
        *,
        fencing_token: int,
        at: datetime,
        success: bool,
        retryable: bool = False,
        reason: str | None = None,
    ) -> StoredWork:
        """F5 contract-bound function `terminal_attempt`. EN summary: bounded F5 function."""
        moment = _utc(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
                if row is None:
                    raise KeyError(attempt_id)
                current = self._current_attempt_row(con, row["work_id"])
                if (
                    current is None
                    or current["attempt_id"] != attempt_id
                    or int(row["fencing_token"]) != fencing_token
                    or _parse(row["lease_expires_at"]) <= moment
                ):
                    raise WorkNotClaimable("stale or expired authority")
                work = con.execute("SELECT * FROM work WHERE work_id=?", (row["work_id"],)).fetchone()
                if work is None or work["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
                    raise WorkNotClaimable("terminal Work cannot transition again")
                if row["state"] not in ("CLAIMED", "RUNNING"):
                    raise WorkNotClaimable("terminal Attempt cannot transition again")
                con.execute(
                    "UPDATE attempt SET state=?,terminated_at=?,terminal_reason=? WHERE attempt_id=?",
                    (
                        "SUCCEEDED" if success else "FAILED",
                        _iso(moment),
                        reason,
                        attempt_id,
                    ),
                )
                if success:
                    wstate, terminal, failure = "SUCCEEDED", "SUCCEEDED", None
                elif retryable and int(row["attempt_no"]) < MAX_AUTOMATIC_ATTEMPTS_PER_WORK:
                    wstate, terminal, failure = (
                        "READY",
                        None,
                        reason or "RETRYABLE_ATTEMPT_FAILURE",
                    )
                elif retryable:
                    wstate, terminal, failure = (
                        "FAILED",
                        "FAILED",
                        "RETRY_BUDGET_EXHAUSTED",
                    )
                else:
                    wstate, terminal, failure = (
                        "FAILED",
                        "FAILED",
                        reason or "NON_RETRYABLE_FAILURE",
                    )
                con.execute(
                    (
                        "UPDATE work SET state=?,terminal_state=?,failure_state=?,terminal_at=?,updated_at=?,"
                        "record_version=record_version+1 WHERE work_id=?"
                    ),
                    (
                        wstate,
                        terminal,
                        failure,
                        _iso(moment) if terminal else None,
                        _iso(moment),
                        row["work_id"],
                    ),
                )
                out = con.execute("SELECT * FROM work WHERE work_id=?", (row["work_id"],)).fetchone()
                con.commit()
                return self._stored_work(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    @staticmethod
    def _stored_publication(row: sqlite3.Row) -> StoredPublication:
        """F5 contract-bound function `_stored_publication`. EN summary: bounded F5 function."""
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

    @staticmethod
    def _stored_generation(row: sqlite3.Row) -> StoredGeneration:
        """F5 contract-bound function `_stored_generation`. EN summary: bounded F5 function."""
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

    def _require_current_fence(
        self, con: sqlite3.Connection, attempt_id: str, fencing_token: int, at: datetime
    ) -> sqlite3.Row:
        """F5 contract-bound function `_require_current_fence`. EN summary: bounded F5 function."""
        row = con.execute("SELECT * FROM attempt WHERE attempt_id=?", (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(attempt_id)
        current = self._current_attempt_row(con, row["work_id"])
        if (
            current is None
            or current["attempt_id"] != attempt_id
            or int(row["fencing_token"]) != fencing_token
            or _parse(row["lease_expires_at"]) <= _utc(at)
        ):
            raise WorkNotClaimable("current fencing authority required")
        work = con.execute("SELECT * FROM work WHERE work_id=?", (row["work_id"],)).fetchone()
        if work is None or work["state"] in ("SUCCEEDED", "FAILED", "CANCELLED"):
            raise WorkNotClaimable("terminal Work has no execution authority")
        if row["state"] not in ("CLAIMED", "RUNNING"):
            raise WorkNotClaimable("terminal Attempt has no execution authority")
        return cast(sqlite3.Row, row)

    def ensure_publication(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        work_id: str,
        attempt_id: str,
        fencing_token: int,
        domain_artifact_identity: str,
        source_revision: str,
        content_checksum: str,
        content_size: int,
        at: datetime,
    ) -> StoredPublication:
        """F5 contract-bound function `ensure_publication`. EN summary: bounded F5 function."""
        pid = build_f5_publication_id(
            work_id=work_id,
            domain_artifact_identity=domain_artifact_identity,
            source_revision=source_revision,
            content_identity=content_checksum,
        )
        target = build_f5_logical_target_identity(
            domain_artifact_identity=domain_artifact_identity,
            source_revision=source_revision,
        )
        stamp = _iso(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                a = self._require_current_fence(con, attempt_id, fencing_token, at)
                if a["work_id"] != work_id:
                    raise WorkNotClaimable("attempt/work mismatch")
                existing = con.execute(
                    "SELECT * FROM publication WHERE logical_target_identity=?",
                    (target,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["publication_id"] == pid
                        and existing["content_checksum"] == content_checksum
                        and int(existing["content_size"]) == content_size
                    ):
                        con.commit()
                        return self._stored_publication(existing)
                    self._fail_attempt_and_work(
                        con,
                        attempt_id,
                        at=at,
                        failure_state="PUBLICATION_CONFLICT",
                    )
                    con.commit()
                    raise ControlStateConflict("PUBLICATION_CONFLICT: same target different bytes")
                con.execute(
                    (
                        "INSERT INTO publication(publication_id,work_id,attempt_id,domain_artifact_identity,"
                        "source_revision,content_checksum,content_size,logical_target_identity,"
                        "state,created_at,updated_at) "
                        "VALUES(?,?,?,?,?,?,?,?,'INGEST_DURABLE',?,?)"
                    ),
                    (
                        pid,
                        work_id,
                        attempt_id,
                        domain_artifact_identity,
                        source_revision,
                        content_checksum,
                        content_size,
                        target,
                        stamp,
                        stamp,
                    ),
                )
                out = con.execute("SELECT * FROM publication WHERE publication_id=?", (pid,)).fetchone()
                con.commit()
                return self._stored_publication(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def get_publication(self, publication_id: str) -> StoredPublication | None:
        """F5 contract-bound function `get_publication`. EN summary: bounded F5 function."""
        with self._connection() as con:
            r = con.execute("SELECT * FROM publication WHERE publication_id=?", (publication_id,)).fetchone()
            return None if r is None else self._stored_publication(r)

    def advance_publication(  # pylint: disable=too-many-arguments
        self,
        publication_id: str,
        *,
        attempt_id: str,
        fencing_token: int,
        target_state: str,
        at: datetime,
        physical_locator: str | None = None,
        evidence: str | None = None,
    ) -> StoredPublication:
        """F5 contract-bound function `advance_publication`. EN summary: bounded F5 function."""
        stamp = _iso(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                authority = self._require_current_fence(con, attempt_id, fencing_token, at)
                r = con.execute(
                    "SELECT * FROM publication WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                if r is None:
                    raise KeyError(publication_id)
                if r["work_id"] != authority["work_id"]:
                    raise WorkNotClaimable("publication/work authority mismatch")
                if target_state in ("CANONICALLY_REGISTERED", "ACKED"):
                    raise ValueError("privileged publication state requires dedicated repository operation")
                if (
                    target_state not in _PUBLICATION_SEQUENCE
                    or _PUBLICATION_SEQUENCE.index(target_state) != _PUBLICATION_SEQUENCE.index(r["state"]) + 1
                ):
                    raise ValueError(f'illegal publication transition {r["state"]}->{target_state}')
                fields = ["state=?", "updated_at=?"]
                vals = [target_state, stamp]
                if target_state == "DURABLE_STORED":
                    if not physical_locator or not evidence:
                        raise ValueError("durable evidence and locator required")
                    fields += ["physical_locator=?", "durable_write_evidence=?"]
                    vals += [physical_locator, evidence]
                elif target_state == "INDEPENDENT_READBACK_VERIFIED":
                    if not evidence or not r["physical_locator"] or not r["durable_write_evidence"]:
                        raise ValueError("readback requires durable evidence")
                    fields += ["readback_evidence=?"]
                    vals += [evidence]
                vals.append(publication_id)
                con.execute(
                    "UPDATE publication SET " + ",".join(fields) + " WHERE publication_id=?",
                    vals,
                )
                out = con.execute(
                    "SELECT * FROM publication WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                con.commit()
                return self._stored_publication(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    @staticmethod
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

    @staticmethod
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

    @classmethod
    def _validated_current_generation_pointer(
        cls, con: sqlite3.Connection, generation_scope_identity: str
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
            or not cls._generation_matches_publication(target, publication)
            or not cls._publication_state_compatible_with_registered_generation(publication)
        ):
            raise RuntimeError("current generation/publication relation corruption")
        return cast(sqlite3.Row, current)

    def register_generation(  # pylint: disable=too-many-locals,too-many-branches
        self, publication_id: str, *, attempt_id: str, fencing_token: int, at: datetime
    ) -> StoredGeneration:
        """F5 contract-bound function `register_generation`. EN summary: bounded F5 function."""
        stamp = _iso(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                authority = self._require_current_fence(con, attempt_id, fencing_token, at)
                p = con.execute(
                    "SELECT * FROM publication WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                if p is None:
                    raise KeyError(publication_id)
                if p["work_id"] != authority["work_id"]:
                    raise WorkNotClaimable("publication/work authority mismatch")
                existing = con.execute(
                    "SELECT * FROM publication_generation WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                if existing is not None:
                    if not self._generation_matches_publication(existing, p):
                        raise RuntimeError("existing generation/publication identity corruption")
                    if not self._publication_state_compatible_with_registered_generation(p):
                        raise RuntimeError("existing generation/publication lifecycle corruption")
                    current = self._validated_current_generation_pointer(con, existing["generation_scope_identity"])
                    if current is None or int(current["generation_no"]) < int(existing["generation_no"]):
                        raise RuntimeError("current generation pointer corruption")
                    if (
                        int(current["generation_no"]) == int(existing["generation_no"])
                        and current["generation_identity"] != existing["generation_identity"]
                    ):
                        raise RuntimeError("current generation pointer conflict")
                    if p["state"] == "INDEPENDENT_READBACK_VERIFIED":
                        con.execute(
                            (
                                "UPDATE publication SET state='CANONICALLY_REGISTERED',registration_evidence=?,"
                                "registration_fencing_token=?,updated_at=? WHERE publication_id=?"
                            ),
                            (
                                "idempotent-generation:" + existing["generation_identity"],
                                fencing_token,
                                stamp,
                                publication_id,
                            ),
                        )
                    out = con.execute(
                        "SELECT * FROM publication_generation WHERE publication_id=?",
                        (publication_id,),
                    ).fetchone()
                    con.commit()
                    return self._stored_generation(out)
                if (
                    p["state"] != "INDEPENDENT_READBACK_VERIFIED"
                    or not p["readback_evidence"]
                    or not p["physical_locator"]
                ):
                    raise ValueError("registration requires independent readback")
                scope = p["domain_artifact_identity"]
                gid = build_f5_generation_identity(
                    domain_artifact_identity=scope,
                    source_revision=p["source_revision"],
                    content_identity=p["content_checksum"],
                )
                current = self._validated_current_generation_pointer(con, scope)
                no = 1 if current is None else int(current["generation_no"]) + 1
                con.execute(
                    (
                        "INSERT INTO publication_generation("
                        "generation_scope_identity,generation_identity,generation_no,"
                        "publication_id,source_revision,content_checksum,content_size,physical_locator,registered_at,"
                        "registration_fencing_token) VALUES(?,?,?,?,?,?,?,?,?,?)"
                    ),
                    (
                        scope,
                        gid,
                        no,
                        publication_id,
                        p["source_revision"],
                        p["content_checksum"],
                        p["content_size"],
                        p["physical_locator"],
                        stamp,
                        fencing_token,
                    ),
                )
                if current is None:
                    con.execute(
                        "INSERT INTO publication_current_generation VALUES(?,?,?,?,?)",
                        (scope, gid, no, stamp, fencing_token),
                    )
                else:
                    con.execute(
                        (
                            "UPDATE publication_current_generation SET generation_identity=?,generation_no=?,"
                            "updated_at=?,"
                            "registration_fencing_token=? WHERE generation_scope_identity=?"
                        ),
                        (gid, no, stamp, fencing_token, scope),
                    )
                con.execute(
                    (
                        "UPDATE publication SET state='CANONICALLY_REGISTERED',registration_evidence=?,"
                        "registration_fencing_token=?,updated_at=? WHERE publication_id=?"
                    ),
                    ("generation:" + gid, fencing_token, stamp, publication_id),
                )
                out = con.execute(
                    "SELECT * FROM publication_generation WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                con.commit()
                return self._stored_generation(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def ack_publication(
        self, publication_id: str, *, attempt_id: str, fencing_token: int, at: datetime
    ) -> StoredPublication:
        """F5 contract-bound function `ack_publication`. EN summary: bounded F5 function."""
        stamp = _iso(at)
        with self._connection() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                authority = self._require_current_fence(con, attempt_id, fencing_token, at)
                p = con.execute(
                    "SELECT * FROM publication WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                if p is None:
                    raise KeyError(publication_id)
                if p["work_id"] != authority["work_id"]:
                    raise WorkNotClaimable("publication/work authority mismatch")
                gen = con.execute(
                    "SELECT * FROM publication_generation WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                pointer_ok = False
                if gen is not None:
                    try:
                        self._validated_current_generation_pointer(con, gen["generation_scope_identity"])
                        pointer_ok = True
                    except RuntimeError:
                        pointer_ok = False
                predecessor_ok = bool(
                    p["state"] in {"CANONICALLY_REGISTERED", "ACKED"}
                    and p["durable_write_evidence"]
                    and p["readback_evidence"]
                    and p["registration_evidence"]
                    and gen is not None
                    and self._generation_matches_publication(gen, p)
                    and pointer_ok
                )
                duplicate_ack_ok = bool(
                    p["state"] == "ACKED" and p["ack_evidence"] == "ack:" + publication_id and p["acked_at"]
                )
                if not predecessor_ok or (p["state"] == "ACKED" and not duplicate_ack_ok):
                    self._fail_attempt_and_work(
                        con,
                        attempt_id,
                        at=at,
                        failure_state="ILLEGAL_ACK",
                    )
                    con.commit()
                    raise ValueError("ILLEGAL_ACK: durable+readback+registration+identity+fence required")
                if p["state"] == "ACKED":
                    con.commit()
                    return self._stored_publication(p)
                con.execute(
                    (
                        "UPDATE publication SET state='ACKED',ack_evidence=?,acked_at=?,updated_at=? "
                        "WHERE publication_id=?"
                    ),
                    ("ack:" + publication_id, stamp, stamp, publication_id),
                )
                out = con.execute(
                    "SELECT * FROM publication WHERE publication_id=?",
                    (publication_id,),
                ).fetchone()
                con.commit()
                return self._stored_publication(out)
            except Exception:
                if con.in_transaction:
                    con.rollback()
                raise

    def resolve_generation(self, scope: str, generation_identity: str | None = None) -> StoredGeneration | None:
        """F5 contract-bound function `resolve_generation`. EN summary: bounded F5 function."""
        with self._connection() as con:
            if generation_identity is None:
                c = con.execute(
                    "SELECT * FROM publication_current_generation WHERE generation_scope_identity=?",
                    (scope,),
                ).fetchone()
                if c is None:
                    return None
                generation_identity = c["generation_identity"]
                r = con.execute(
                    "SELECT * FROM publication_generation WHERE generation_scope_identity=? AND generation_identity=?",
                    (scope, generation_identity),
                ).fetchone()
                if r is None or int(r["generation_no"]) != int(c["generation_no"]):
                    raise RuntimeError("current generation pointer reconciliation mismatch")
                return self._stored_generation(r)
            r = con.execute(
                "SELECT * FROM publication_generation WHERE generation_scope_identity=? AND generation_identity=?",
                (scope, generation_identity),
            ).fetchone()
            return None if r is None else self._stored_generation(r)

    def list_generations(self) -> tuple[StoredGeneration, ...]:
        """F5 contract-bound function `list_generations`. EN summary: bounded F5 function."""
        with self._connection() as con:
            rows = con.execute(
                "SELECT * FROM publication_generation ORDER BY generation_scope_identity,generation_no"
            ).fetchall()
            return tuple(self._stored_generation(row) for row in rows)

    def backup_to(self, destination: str | Path) -> ControlBackupEvidence:
        """F5 contract-bound function `backup_to`. EN summary: bounded F5 function."""
        dest = Path(destination)
        if dest.exists():
            raise FileExistsError(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.database_path, timeout=5.0)
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


def restore_sqlite_backup(
    backup_path: str | Path,
    destination: str | Path,
    *,
    expected_backup_sha256: str | None = None,
    expected_backup_size: int | None = None,
) -> tuple[SQLiteServerControlRepository, ControlRestoreEvidence]:
    """Restore one exact backup identity into an isolated destination."""
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
    repo = SQLiteServerControlRepository(dest)
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
        count = int(verification.execute("SELECT COUNT(*) FROM publication_generation").fetchone()[0])
    finally:
        verification.close()
    return repo, ControlRestoreEvidence(
        str(dest),
        backup_identity[0],
        backup_identity[1],
        integrity,
        CONTROL_SCHEMA_ID,
        version,
        count,
    )
