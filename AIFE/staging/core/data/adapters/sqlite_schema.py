"""Bounded SQLite/WAL schema for F5 control state; no generic migration framework."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

CONTROL_SCHEMA_ID = "aife-server-control"
CONTROL_SCHEMA_INITIAL_VERSION = 1
CONTROL_SCHEMA_COMPATIBILITY = "F5_V1"
CONTROL_SCHEMA_MIGRATION_ID = "f5-control-0-to-1"
SQLITE_BUSY_TIMEOUT_MS = 5000

DDL = (
    """CREATE TABLE schema_metadata (
 schema_name TEXT PRIMARY KEY,
 schema_version INTEGER NOT NULL CHECK(schema_version>=1),
 compatibility_class TEXT NOT NULL CHECK(compatibility_class IN('F5_V1')),
 migration_id TEXT NOT NULL,
 applied_at TEXT NOT NULL
)""",
    """CREATE TABLE work (
 work_id TEXT PRIMARY KEY,
 work_kind TEXT NOT NULL,
 logical_input_identity TEXT NOT NULL UNIQUE,
 scheduling_slot_identity TEXT,
 payload_reference TEXT NOT NULL,
 provenance_reference TEXT NOT NULL,
 policy_revision_identity TEXT NOT NULL,
 immutable_input_digest TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 terminal_at TEXT,
 state TEXT NOT NULL CHECK(state IN('PENDING','READY','CLAIMED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
 terminal_state TEXT,
 failure_state TEXT,
 record_version INTEGER NOT NULL DEFAULT 1 CHECK(record_version>=1)
)""",
    "CREATE INDEX idx_work_state_created_at ON work(state,created_at)",
    """CREATE TABLE attempt (
 attempt_id TEXT PRIMARY KEY,
 work_id TEXT NOT NULL REFERENCES work(work_id) ON DELETE RESTRICT,
 attempt_no INTEGER NOT NULL CHECK(attempt_no>=1),
 claim_id TEXT NOT NULL UNIQUE,
 claim_owner TEXT NOT NULL,
 lease_id TEXT NOT NULL UNIQUE,
 lease_acquired_at TEXT NOT NULL,
 lease_expires_at TEXT NOT NULL,
 fencing_token INTEGER NOT NULL CHECK(fencing_token>=1),
 state TEXT NOT NULL CHECK(state IN('CLAIMED','RUNNING','SUCCEEDED','FAILED','ABANDONED')),
 started_at TEXT,
 terminated_at TEXT,
 terminal_reason TEXT,
 UNIQUE(work_id,attempt_no),
 UNIQUE(work_id,fencing_token),
 CHECK(lease_expires_at>lease_acquired_at)
)""",
    "CREATE INDEX idx_attempt_work_state ON attempt(work_id,state)",
    "CREATE INDEX idx_attempt_lease_expiry ON attempt(state,lease_expires_at)",
    """CREATE TABLE publication (
 publication_id TEXT PRIMARY KEY,
 work_id TEXT NOT NULL REFERENCES work(work_id) ON DELETE RESTRICT,
 attempt_id TEXT NOT NULL REFERENCES attempt(attempt_id) ON DELETE RESTRICT,
 domain_artifact_identity TEXT NOT NULL,
 source_revision TEXT NOT NULL,
 content_checksum TEXT NOT NULL,
 content_size INTEGER NOT NULL CHECK(content_size>=0),
 logical_target_identity TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL CHECK(state IN(
 'INGEST_DURABLE','STAGED','PUBLISHING','DURABLE_STORED','INDEPENDENT_READBACK_VERIFIED',
 'CANONICALLY_REGISTERED','ACKED','FAILED','CONFLICTED'
 )),
 physical_locator TEXT,
 durable_write_evidence TEXT,
 readback_evidence TEXT,
 registration_evidence TEXT,
 ack_evidence TEXT,
 registration_fencing_token INTEGER,
 failure_reason TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 acked_at TEXT
)""",
    "CREATE INDEX idx_publication_work ON publication(work_id)",
    "CREATE INDEX idx_publication_state ON publication(state)",
    "CREATE INDEX idx_publication_target ON publication(logical_target_identity)",
    """CREATE TABLE publication_generation (
 generation_scope_identity TEXT NOT NULL,
 generation_identity TEXT NOT NULL,
 generation_no INTEGER NOT NULL CHECK(generation_no>=1),
 publication_id TEXT NOT NULL UNIQUE REFERENCES publication(publication_id) ON DELETE RESTRICT,
 source_revision TEXT NOT NULL,
 content_checksum TEXT NOT NULL,
 content_size INTEGER NOT NULL CHECK(content_size>=0),
 physical_locator TEXT NOT NULL,
 registered_at TEXT NOT NULL,
 registration_fencing_token INTEGER NOT NULL CHECK(registration_fencing_token>=1),
 PRIMARY KEY(generation_scope_identity,generation_identity),
 UNIQUE(generation_scope_identity,generation_no)
)""",
    "CREATE INDEX idx_generation_publication ON publication_generation(publication_id)",
    """CREATE TABLE publication_current_generation (
 generation_scope_identity TEXT PRIMARY KEY,
 generation_identity TEXT NOT NULL,
 generation_no INTEGER NOT NULL CHECK(generation_no>=1),
 updated_at TEXT NOT NULL,
 registration_fencing_token INTEGER NOT NULL CHECK(registration_fencing_token>=1),
 FOREIGN KEY(generation_scope_identity,generation_identity)
   REFERENCES publication_generation(generation_scope_identity,generation_identity)
)""",
)


def configure_connection(connection: sqlite3.Connection) -> None:
    """F5 contract-bound function `configure_connection`. EN summary: bounded F5 function."""
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    mode = str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
    if mode != "wal" and connection.execute("PRAGMA database_list").fetchone()[2] != "":
        raise RuntimeError(f"SQLite WAL unavailable: {mode}")


def migrate_0_to_1(connection: sqlite3.Connection) -> None:
    """F5 contract-bound function `migrate_0_to_1`. EN summary: bounded F5 function."""
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != 0:
        raise RuntimeError(f"0->1 migration requires user_version=0, got {version}")
    try:
        connection.execute("BEGIN IMMEDIATE")
        for statement in DDL:
            connection.execute(statement)
        applied_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            (
                "INSERT INTO schema_metadata(schema_name,schema_version,compatibility_class,migration_id,applied_at) "
                "VALUES(?,?,?,?,?)"
            ),
            (
                CONTROL_SCHEMA_ID,
                1,
                CONTROL_SCHEMA_COMPATIBILITY,
                CONTROL_SCHEMA_MIGRATION_ID,
                applied_at,
            ),
        )
        connection.execute("PRAGMA user_version=1")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def validate_schema_identity(connection: sqlite3.Connection) -> None:
    """F5 contract-bound function `validate_schema_identity`. EN summary: bounded F5 function."""
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != CONTROL_SCHEMA_INITIAL_VERSION:
        raise RuntimeError(f"incompatible control schema user_version={version}")
    row = connection.execute(
        "SELECT schema_version,compatibility_class,migration_id FROM schema_metadata WHERE schema_name=?",
        (CONTROL_SCHEMA_ID,),
    ).fetchone()
    if row is None or tuple(row) != (
        1,
        CONTROL_SCHEMA_COMPATIBILITY,
        CONTROL_SCHEMA_MIGRATION_ID,
    ):
        raise RuntimeError("schema_metadata/user_version identity mismatch")
    if int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) != 1:
        raise RuntimeError("foreign_keys must be ON")


def initialize_or_validate(connection: sqlite3.Connection) -> None:
    """F5 contract-bound function `initialize_or_validate`. EN summary: bounded F5 function."""
    configure_connection(connection)
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version == 0:
        migrate_0_to_1(connection)
    elif version == 1:
        validate_schema_identity(connection)
    else:
        raise RuntimeError(f"unsupported control schema version {version}; downgrade forbidden")
    validate_schema_identity(connection)
