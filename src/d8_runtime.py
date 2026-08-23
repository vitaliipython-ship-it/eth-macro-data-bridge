from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from canonical_json import canonical_json, sha256_canonical_json

RUNTIME_CONTRACT_VERSION = "eth-macro-d8-runtime/1.0.0"
STATE_SCHEMA_VERSION = 2
OBSERVATION_ENVELOPE_VERSION = "market-data-d8-runtime-observation/1.0.0"
CANONICAL_SLOT = "M5"
DEFAULT_SPOOL_MAX_BYTES = 128 * 1024 * 1024
DEFAULT_SPOOL_RETENTION_SECONDS = 7 * 86400
DEFAULT_LEASE_SECONDS = 240
MAX_ATTEMPTS = 3
MAX_BODY_BYTES = 64 * 1024
STALE_SLOT_SECONDS = 20 * 60
FUTURE_SKEW_SECONDS = 120
EXISTING_CYCLE_RECOVERY_SECONDS = 24 * 60 * 60
RECOVERABLE_CYCLE_STATUSES = frozenset({"STARTED", "COLLECTED", "QUALIFIED", "RECOVERABLE"})

FAILURE_CLASSES = {
    "PROVIDER_CONNECTIVITY", "PROVIDER_RATE_LIMIT", "PROVIDER_SCHEMA", "PROVIDER_TIMEOUT",
    "VALIDATION_FAILED", "STATE_IO", "STATE_SCHEMA_INCOMPATIBLE", "LEDGER_CONFLICT",
    "LOCK_BUSY", "STALE_LOCK_RECOVERED", "HOT_PROMOTION_FAILED", "SPOOL_FULL", "AUTH_FAILED",
    "REQUEST_INVALID", "RUNTIME_INTERNAL",
}

DUE_POLICY_VERSION = "d8-provider-due-policy/2.0.0"
from d8_capability_routing import runtime_due_policy
CAPABILITY_POLICY: tuple[dict[str, Any], ...] = runtime_due_policy()


def utc_iso(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC RFC3339 with Z")
    dt = datetime.fromisoformat(value[:-1] + "+00:00")
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _utc_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(parse_utc(value).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def canonical_slot_text(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:00Z")


def cycle_id_for(slot_text: str) -> str:
    raw = f"{RUNTIME_CONTRACT_VERSION}|{CANONICAL_SLOT}|{slot_text}".encode()
    return "d8c-" + hashlib.sha256(raw).hexdigest()[:32]


def observation_id(provider: str, series_id: str, provider_timestamp: str | None, fingerprint: str) -> str:
    raw = f"{provider}|{series_id}|{provider_timestamp or 'NONE'}|{fingerprint}".encode()
    return "obs-" + hashlib.sha256(raw).hexdigest()


def fingerprint_payload(value: Any) -> str:
    return sha256_canonical_json(value)


def _canonical_json(value: Any) -> str:
    return canonical_json(value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _checkpoint_hashes(observations: list[dict[str, Any]]) -> tuple[str, str]:
    observation_ids = [row["observation_id"] for row in observations]
    return (
        _sha256_text(_canonical_json(observation_ids)),
        _sha256_text(_canonical_json(observations)),
    )


def _ledger_binding(row: dict[str, Any]) -> str:
    bound = {
        "capability_id": row["capability_id"],
        "provider": row["provider"],
        "status": row["status"],
        "failure_class": row.get("failure_class"),
        "provider_timestamp_at": row.get("provider_timestamp_at"),
        "retrieved_at": row["retrieved_at"],
        "known_at": row["known_at"],
        "collected_at": row["collected_at"],
        "fingerprint": row.get("fingerprint"),
        "spool_ref": row.get("spool_ref"),
        "freshness": row["freshness"],
        "gap_semantics": row.get("gap_semantics"),
    }
    return _sha256_text(_canonical_json(bound))


def validate_request_common(body: Any, *, now_ms: int) -> dict[str, Any]:
    """Validate request structure/identity without applying new-cycle staleness."""
    if not isinstance(body, dict):
        raise ValueError("request must be an object")
    allowed = {"schema_version", "expected_schedule_at", "canonical_slot", "trace_id"}
    if set(body) - allowed:
        raise ValueError("request contains forbidden fields")
    if body.get("schema_version") != "eth-macro-d8-collect-cycle-request/1.0.0":
        raise ValueError("unsupported schema_version")
    if body.get("canonical_slot") != CANONICAL_SLOT:
        raise ValueError("canonical_slot must be M5")
    dt = parse_utc(body.get("expected_schedule_at"))
    if dt.second or dt.microsecond or dt.minute % 5:
        raise ValueError("expected_schedule_at must be an exact M5 UTC boundary")
    expected_ms = int(dt.timestamp() * 1000)
    if expected_ms - now_ms > FUTURE_SKEW_SECONDS * 1000:
        raise ValueError("future slot outside clock-skew policy")
    trace_id = body.get("trace_id")
    if trace_id is not None and (not isinstance(trace_id, str) or not (1 <= len(trace_id) <= 128)):
        raise ValueError("trace_id must be 1..128 characters")
    return {
        "expected_schedule_at": utc_iso(expected_ms),
        "expected_ms": expected_ms,
        "canonical_slot": CANONICAL_SLOT,
        "trace_id": trace_id,
    }


def new_admission_is_stale(req: dict[str, Any], *, now_ms: int) -> bool:
    """STALE_SLOT_SECONDS is exclusively the NEW cycle admission bound."""
    return now_ms - int(req["expected_ms"]) > STALE_SLOT_SECONDS * 1000


def validate_request(body: Any, *, now_ms: int) -> dict[str, Any]:
    """Backward-compatible validator for callers performing NEW admission."""
    req = validate_request_common(body, now_ms=now_ms)
    if new_admission_is_stale(req, now_ms=now_ms):
        raise ValueError("stale slot outside new-cycle admission window")
    return req


def due_state(capability: dict[str, Any], expected_ms: int, profile: str) -> str:
    if capability.get("disabled"):
        return "DISABLED_BY_POLICY"
    profiles = capability.get("profiles")
    if profiles and profile not in profiles:
        return "DISABLED_BY_POLICY"
    period_ms = int(capability["every_minutes"]) * 60_000
    anchor_ms = int(capability["schedule_anchor_ms"])
    if period_ms <= 0:
        raise ValueError("capability cadence must be positive")
    return "DUE" if (int(expected_ms) - anchor_ms) % period_ms == 0 else "NOT_DUE"


class AcquisitionCore(Protocol):
    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RuntimeConfig:
    state_root: Path
    profile: str = "development"
    source_revision: str = "UNBOUND_SOURCE_REVISION"
    runtime_revision: str = RUNTIME_CONTRACT_VERSION
    spool_max_bytes: int = DEFAULT_SPOOL_MAX_BYTES
    spool_retention_seconds: int = DEFAULT_SPOOL_RETENTION_SECONDS
    lease_seconds: int = DEFAULT_LEASE_SECONDS
    owner_id: str = "d8-runtime"

    def validate(self) -> None:
        if self.profile not in {"development", "test", "VPS_SHADOW"}:
            raise ValueError("VPS_ACTIVE is not allowed by the D8 source candidate")
        if self.spool_max_bytes < 1024 * 1024:
            raise ValueError("spool_max_bytes is unreasonably small")
        if self.lease_seconds < 30 or self.lease_seconds > 600:
            raise ValueError("lease_seconds outside bounded policy")


class StateError(RuntimeError):
    pass


class ClosingConnection(sqlite3.Connection):
    """sqlite transaction context that also releases the file descriptor."""
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class D8State:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        config.validate()
        config.state_root.mkdir(parents=True, exist_ok=True)
        self.db_path = config.state_root / "d8-runtime.sqlite3"
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, isolation_level=None, check_same_thread=False, factory=ClosingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @staticmethod
    def _create_v1_tables(db: sqlite3.Connection) -> None:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cycles(
          cycle_id TEXT PRIMARY KEY, slot TEXT UNIQUE NOT NULL, expected_at TEXT NOT NULL,
          attempt INTEGER NOT NULL, status TEXT NOT NULL, started_at TEXT, completed_at TEXT,
          response_json TEXT, source_revision TEXT NOT NULL, runtime_revision TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS leases(
          slot TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, owner_id TEXT NOT NULL,
          acquired_at INTEGER NOT NULL, lease_until INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS spool(
          observation_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL,
          payload_json TEXT NOT NULL, payload_bytes INTEGER NOT NULL, created_at INTEGER NOT NULL,
          expires_at INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING');
        CREATE TABLE IF NOT EXISTS capability_ledger(
          cycle_id TEXT NOT NULL, capability_id TEXT NOT NULL, attempt INTEGER NOT NULL,
          provider TEXT NOT NULL, status TEXT NOT NULL, failure_class TEXT,
          provider_timestamp_at TEXT, retrieved_at TEXT NOT NULL, known_at TEXT NOT NULL,
          collected_at TEXT NOT NULL, fingerprint TEXT, spool_ref TEXT,
          promotion_result TEXT NOT NULL, freshness_json TEXT NOT NULL, gap_semantics TEXT,
          source_revision TEXT NOT NULL, runtime_revision TEXT NOT NULL,
          PRIMARY KEY(cycle_id, capability_id, attempt));
        CREATE TABLE IF NOT EXISTS hot(
          singleton INTEGER PRIMARY KEY CHECK(singleton=1), cycle_id TEXT NOT NULL,
          promoted_at TEXT NOT NULL, payload_json TEXT NOT NULL);
        """)

    @staticmethod
    def _create_v2_checkpoint_tables(db: sqlite3.Connection) -> None:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cycle_checkpoints(
          cycle_id TEXT NOT NULL,
          capability_id TEXT NOT NULL,
          checkpoint_attempt INTEGER NOT NULL,
          expected_count INTEGER NOT NULL,
          membership_sha256 TEXT NOT NULL,
          payload_sha256 TEXT NOT NULL,
          ledger_sha256 TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          PRIMARY KEY(cycle_id, capability_id));
        CREATE TABLE IF NOT EXISTS cycle_checkpoint_observations(
          cycle_id TEXT NOT NULL,
          capability_id TEXT NOT NULL,
          position INTEGER NOT NULL,
          observation_id TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          payload_sha256 TEXT NOT NULL,
          PRIMARY KEY(cycle_id, capability_id, position),
          UNIQUE(cycle_id, capability_id, observation_id),
          FOREIGN KEY(cycle_id, capability_id)
            REFERENCES cycle_checkpoints(cycle_id, capability_id)
            ON DELETE CASCADE);
        """)

    def _init_db(self) -> None:
        try:
            with self.connect() as db:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                row = db.execute("SELECT value FROM meta WHERE key='state_schema_version'").fetchone()
                version = row[0] if row is not None else None
                if version not in {None, "1", str(STATE_SCHEMA_VERSION)}:
                    raise StateError("STATE_SCHEMA_INCOMPATIBLE")
                self._create_v1_tables(db)
                self._create_v2_checkpoint_tables(db)
                if version is None:
                    db.execute("INSERT INTO meta(key,value) VALUES('state_schema_version',?)", (str(STATE_SCHEMA_VERSION),))
                elif version == "1":
                    db.execute("UPDATE meta SET value=? WHERE key='state_schema_version'", (str(STATE_SCHEMA_VERSION),))
        except StateError:
            raise
        except sqlite3.DatabaseError as exc:
            raise StateError(f"STATE_IO:{exc}") from exc

    def compatibility_check(self) -> None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key='state_schema_version'").fetchone()
            if row is None or row[0] != str(STATE_SCHEMA_VERSION):
                raise StateError("STATE_SCHEMA_INCOMPATIBLE")
            db.execute("SELECT COUNT(*) FROM cycles").fetchone()
            db.execute("SELECT COUNT(*) FROM spool").fetchone()
            db.execute("SELECT COUNT(*) FROM cycle_checkpoints").fetchone()
            db.execute("SELECT COUNT(*) FROM cycle_checkpoint_observations").fetchone()

    @staticmethod
    def _identity_is_exact(prior: sqlite3.Row, slot: str, cycle_id: str) -> bool:
        return prior["slot"] == slot and prior["expected_at"] == slot and prior["cycle_id"] == cycle_id and cycle_id_for(prior["expected_at"]) == prior["cycle_id"]

    def _runtime_contract_compatible(self, prior: sqlite3.Row) -> bool:
        stored = str(prior["runtime_revision"])
        return stored in {RUNTIME_CONTRACT_VERSION, self.config.runtime_revision}

    @staticmethod
    def _recovery_anchor_ms(db: sqlite3.Connection, prior: sqlite3.Row, lease: sqlite3.Row | None) -> int | None:
        anchors = [_utc_ms(prior["started_at"]), _utc_ms(prior["completed_at"])]
        if lease is not None:
            anchors.extend([int(lease["acquired_at"]), int(lease["lease_until"])])
        checkpoint = db.execute("SELECT MAX(created_at) FROM cycle_checkpoints WHERE cycle_id=?", (prior["cycle_id"],)).fetchone()[0]
        if checkpoint is not None:
            anchors.append(int(checkpoint))
        ledger_rows = db.execute("SELECT collected_at FROM capability_ledger WHERE cycle_id=?", (prior["cycle_id"],)).fetchall()
        anchors.extend(_utc_ms(row[0]) for row in ledger_rows)
        valid = [value for value in anchors if value is not None]
        return max(valid) if valid else None

    def recover_nonterminal(self, now_ms: int) -> int:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            stale = int(db.execute("SELECT COUNT(*) FROM leases WHERE lease_until < ?", (now_ms,)).fetchone()[0])
            db.execute("UPDATE cycles SET status='RECOVERABLE' WHERE status IN ('STARTED','COLLECTED','QUALIFIED') AND NOT EXISTS (SELECT 1 FROM leases WHERE leases.cycle_id=cycles.cycle_id AND leases.lease_until >= ?)", (now_ms,))
            db.execute("COMMIT")
            return stale

    def acquire(self, *, slot: str, cycle_id: str, now_ms: int, new_admission_allowed: bool = True) -> tuple[str, dict[str, Any] | None, int, bool]:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM cycles WHERE slot=?", (slot,)).fetchone()
            lease = db.execute("SELECT * FROM leases WHERE slot=?", (slot,)).fetchone()
            if prior and not self._identity_is_exact(prior, slot, cycle_id):
                db.execute("COMMIT"); return "CONFLICT", None, int(prior["attempt"]), False
            if lease and (not prior or lease["cycle_id"] != cycle_id):
                db.execute("COMMIT"); return "CONFLICT", None, int(prior["attempt"] if prior else 0), False
            if prior and prior["status"] == "PASS" and prior["response_json"]:
                if not new_admission_allowed:
                    db.execute("COMMIT"); return "STALE_TERMINAL", None, int(prior["attempt"]), False
                db.execute("COMMIT"); return "REPLAY", json.loads(prior["response_json"]), int(prior["attempt"]), False
            if lease and int(lease["lease_until"]) >= now_ms:
                db.execute("COMMIT"); return "BUSY", None, int(prior["attempt"] if prior else 0), False
            stale_recovered = bool(lease and int(lease["lease_until"]) < now_ms)
            if prior is None:
                if not new_admission_allowed:
                    db.execute("COMMIT"); return "STALE_NEW", None, 0, False
            elif not new_admission_allowed:
                if prior["status"] not in RECOVERABLE_CYCLE_STATUSES:
                    db.execute("COMMIT"); return "STALE_TERMINAL", None, int(prior["attempt"]), stale_recovered
                if not self._runtime_contract_compatible(prior):
                    db.execute("COMMIT"); return "CONFLICT", None, int(prior["attempt"]), stale_recovered
                anchor = self._recovery_anchor_ms(db, prior, lease)
                if anchor is None or now_ms > anchor + EXISTING_CYCLE_RECOVERY_SECONDS * 1000:
                    db.execute("COMMIT"); return "RECOVERY_EXPIRED", None, int(prior["attempt"]), stale_recovered
            attempt = int(prior["attempt"] if prior else 0) + 1
            if attempt > MAX_ATTEMPTS:
                db.execute("COMMIT"); return "EXHAUSTED", json.loads(prior["response_json"]) if prior and prior["response_json"] else None, attempt - 1, stale_recovered
            now_iso = utc_iso(now_ms)
            if prior:
                db.execute("UPDATE cycles SET attempt=?, status='STARTED', started_at=?, completed_at=NULL WHERE cycle_id=?", (attempt, now_iso, cycle_id))
            else:
                db.execute("INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,started_at,source_revision,runtime_revision) VALUES(?,?,?,?,?,?,?,?)", (cycle_id, slot, slot, attempt, "STARTED", now_iso, self.config.source_revision, self.config.runtime_revision))
            db.execute("INSERT OR REPLACE INTO leases(slot,cycle_id,owner_id,acquired_at,lease_until) VALUES(?,?,?,?,?)", (slot, cycle_id, self.config.owner_id, now_ms, now_ms + self.config.lease_seconds * 1000))
            db.execute("COMMIT")
            return "OWNER", None, attempt, stale_recovered

    def _assert_owner(self, db: sqlite3.Connection, *, cycle_id: str, attempt: int, now_ms: int) -> sqlite3.Row:
        cycle = db.execute("SELECT attempt,slot FROM cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
        if cycle is None or int(cycle["attempt"]) != attempt:
            raise StateError("LEDGER_CONFLICT: lease ownership lost: cycle attempt changed")
        lease = db.execute("SELECT * FROM leases WHERE slot=?", (cycle["slot"],)).fetchone()
        if lease is None or lease["cycle_id"] != cycle_id or lease["owner_id"] != self.config.owner_id or int(lease["lease_until"]) < now_ms:
            raise StateError("LEDGER_CONFLICT: lease ownership lost")
        return lease

    def renew_lease(self, *, slot: str, cycle_id: str, now_ms: int) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("UPDATE leases SET lease_until=? WHERE slot=? AND cycle_id=? AND owner_id=? AND lease_until>=?", (now_ms + self.config.lease_seconds * 1000, slot, cycle_id, self.config.owner_id, now_ms))
            db.execute("COMMIT")
            return cur.rowcount == 1

    def spool_bytes(self, db: sqlite3.Connection | None = None) -> int:
        own = db is None
        conn = db or self.connect()
        try:
            return int(conn.execute("SELECT COALESCE(SUM(payload_bytes),0) FROM spool").fetchone()[0])
        finally:
            if own:
                conn.close()

    def semantic_predecessor(self, capability_id: str, provider: str, series_id: str, provider_timestamp_at: str | None, fingerprint: str) -> dict[str, Any] | None:
        """Find bounded retained predecessor evidence without changing schema v2."""
        if not provider_timestamp_at:
            return None
        with self.connect() as db:
            rows = db.execute("SELECT payload_json FROM spool WHERE capability_id=? ORDER BY created_at DESC LIMIT 2048", (capability_id,)).fetchall()
        for stored in rows:
            try:
                payload = json.loads(stored["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("provider") == provider and payload.get("series_id") == series_id and payload.get("provider_timestamp_at") == provider_timestamp_at and payload.get("fingerprint") != fingerprint:
                return payload
        return None

    def checkpoint_capability(self, *, cycle_id: str, attempt: int, ledger_row: dict[str, Any], observations: list[dict[str, Any]], now_ms: int) -> None:
        encoded = [(o["observation_id"], _canonical_json(o)) for o in observations]
        ids = [oid for oid, _ in encoded]
        if len(ids) != len(set(ids)):
            raise StateError("LEDGER_CONFLICT: duplicate observation_id inside checkpoint")
        membership_sha256, payload_sha256 = _checkpoint_hashes(observations)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._assert_owner(db, cycle_id=cycle_id, attempt=attempt, now_ms=now_ms)
                existing_ids = set()
                if encoded:
                    placeholders = ",".join("?" for _ in encoded)
                    existing_ids = {r[0] for r in db.execute(f"SELECT observation_id FROM spool WHERE observation_id IN ({placeholders})", [x[0] for x in encoded]).fetchall()}
                incremental = sum(len(payload.encode()) for oid, payload in encoded if oid not in existing_ids)
                if self.spool_bytes(db) + incremental > self.config.spool_max_bytes:
                    raise StateError("SPOOL_FULL")
                expires_at = now_ms + self.config.spool_retention_seconds * 1000
                for oid, payload in encoded:
                    cap = ledger_row["capability_id"]
                    db.execute("INSERT OR IGNORE INTO spool(observation_id,cycle_id,capability_id,payload_json,payload_bytes,created_at,expires_at,state) VALUES(?,?,?,?,?,?,?,'PENDING')", (oid, cycle_id, cap, payload, len(payload.encode()), now_ms, expires_at))
                self._upsert_ledger(db, cycle_id=cycle_id, attempt=attempt, row=ledger_row, promotion_result="PENDING")
                if ledger_row["status"] == "OBSERVED_STATE" and observations:
                    cap = ledger_row["capability_id"]
                    db.execute("DELETE FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=?", (cycle_id, cap))
                    db.execute("DELETE FROM cycle_checkpoints WHERE cycle_id=? AND capability_id=?", (cycle_id, cap))
                    db.execute("INSERT INTO cycle_checkpoints(cycle_id,capability_id,checkpoint_attempt,expected_count,membership_sha256,payload_sha256,ledger_sha256,created_at) VALUES(?,?,?,?,?,?,?,?)", (cycle_id, cap, attempt, len(observations), membership_sha256, payload_sha256, _ledger_binding(ledger_row), now_ms))
                    for position, (oid, payload) in enumerate(encoded):
                        db.execute("INSERT INTO cycle_checkpoint_observations(cycle_id,capability_id,position,observation_id,payload_json,payload_sha256) VALUES(?,?,?,?,?,?)", (cycle_id, cap, position, oid, payload, _sha256_text(payload)))
                db.execute("UPDATE cycles SET status='COLLECTED' WHERE cycle_id=? AND status IN ('STARTED','RECOVERABLE','COLLECTED')", (cycle_id,))
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise

    def load_checkpoint(self, cycle_id: str, capability_id: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        with self.connect() as db:
            checkpoint = db.execute("SELECT * FROM cycle_checkpoints WHERE cycle_id=? AND capability_id=?", (cycle_id, capability_id)).fetchone()
            if checkpoint is None:
                return [], None
            ledger = db.execute("SELECT * FROM capability_ledger WHERE cycle_id=? AND capability_id=? AND attempt=?", (cycle_id, capability_id, int(checkpoint["checkpoint_attempt"]))).fetchone()
            if ledger is None or ledger["status"] != "OBSERVED_STATE":
                return [], None
            try:
                ledger_view = {"capability_id": capability_id, "provider": ledger["provider"], "status": ledger["status"], "failure_class": ledger["failure_class"], "provider_timestamp_at": ledger["provider_timestamp_at"], "retrieved_at": ledger["retrieved_at"], "known_at": ledger["known_at"], "collected_at": ledger["collected_at"], "fingerprint": ledger["fingerprint"], "spool_ref": ledger["spool_ref"], "freshness": json.loads(ledger["freshness_json"]), "gap_semantics": ledger["gap_semantics"]}
            except (TypeError, ValueError, json.JSONDecodeError):
                return [], None
            if _ledger_binding(ledger_view) != checkpoint["ledger_sha256"]:
                return [], None
            rows = db.execute("SELECT position,observation_id,payload_json,payload_sha256 FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=? ORDER BY position", (cycle_id, capability_id)).fetchall()
            expected_count = int(checkpoint["expected_count"])
            if expected_count <= 0 or len(rows) != expected_count:
                return [], None
            if [int(row["position"]) for row in rows] != list(range(expected_count)):
                return [], None
            observation_ids = [row["observation_id"] for row in rows]
            if len(observation_ids) != len(set(observation_ids)):
                return [], None
            if _sha256_text(_canonical_json(observation_ids)) != checkpoint["membership_sha256"]:
                return [], None
            payloads = []
            try:
                for row in rows:
                    payload_json = row["payload_json"]
                    if _sha256_text(payload_json) != row["payload_sha256"]:
                        return [], None
                    payload = json.loads(payload_json)
                    if payload.get("observation_id") != row["observation_id"] or payload.get("capability_id") != capability_id or payload.get("canonical_cycle_id") != cycle_id:
                        return [], None
                    payloads.append(payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                return [], None
            if _sha256_text(_canonical_json(payloads)) != checkpoint["payload_sha256"]:
                return [], None
            return payloads, ledger_view

    def _upsert_ledger(self, db: sqlite3.Connection, *, cycle_id: str, attempt: int, row: dict[str, Any], promotion_result: str) -> None:
        db.execute("INSERT OR REPLACE INTO capability_ledger(cycle_id,capability_id,attempt,provider,status,failure_class,provider_timestamp_at,retrieved_at,known_at,collected_at,fingerprint,spool_ref,promotion_result,freshness_json,gap_semantics,source_revision,runtime_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (cycle_id, row["capability_id"], attempt, row["provider"], row["status"], row.get("failure_class"), row.get("provider_timestamp_at"), row["retrieved_at"], row["known_at"], row["collected_at"], row.get("fingerprint"), row.get("spool_ref"), promotion_result, json.dumps(row["freshness"], sort_keys=True), row.get("gap_semantics"), self.config.source_revision, self.config.runtime_revision))

    def mark_forwarded(self, observation_ids: list[str], now_ms: int) -> int:
        if not observation_ids:
            return 0
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            placeholders = ",".join("?" for _ in observation_ids)
            params = [now_ms + self.config.spool_retention_seconds * 1000, *observation_ids]
            cur = db.execute(f"UPDATE spool SET state='FORWARDED', expires_at=? WHERE observation_id IN ({placeholders}) AND state='PENDING'", params)
            db.execute("COMMIT")
            return int(cur.rowcount)

    def sweep_forwarded(self, now_ms: int) -> int:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("DELETE FROM spool WHERE state='FORWARDED' AND expires_at < ?", (now_ms,))
            db.execute("COMMIT")
            return int(cur.rowcount)

    def terminalize(self, *, cycle_id: str, slot: str, attempt: int, response: dict[str, Any], observations: list[dict[str, Any]], ledger_rows: list[dict[str, Any]], promote: bool, now_ms: int) -> None:
        encoded_obs = [(o["observation_id"], json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)) for o in observations]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._assert_owner(db, cycle_id=cycle_id, attempt=attempt, now_ms=now_ms)
            existing_ids = {r[0] for r in db.execute("SELECT observation_id FROM spool WHERE observation_id IN (%s)" % ",".join("?" * len(encoded_obs)), [x[0] for x in encoded_obs]).fetchall()} if encoded_obs else set()
            incremental = sum(len(payload.encode()) for oid, payload in encoded_obs if oid not in existing_ids)
            if self.spool_bytes(db) + incremental > self.config.spool_max_bytes:
                db.execute("ROLLBACK")
                raise StateError("SPOOL_FULL")
            expires_at = now_ms + self.config.spool_retention_seconds * 1000
            for oid, payload in encoded_obs:
                cap = next(o["capability_id"] for o in observations if o["observation_id"] == oid)
                db.execute("INSERT OR IGNORE INTO spool(observation_id,cycle_id,capability_id,payload_json,payload_bytes,created_at,expires_at) VALUES(?,?,?,?,?,?,?)", (oid, cycle_id, cap, payload, len(payload.encode()), now_ms, expires_at))
            for row in ledger_rows:
                self._upsert_ledger(db, cycle_id=cycle_id, attempt=attempt, row=row, promotion_result="PROMOTED" if promote else "NOT_PROMOTED")
            if promote:
                hot_payload = json.dumps({"schema_version": "eth-macro-d8-hot/1.0.0", "cycle_id": cycle_id, "slot": slot, "observations": observations}, sort_keys=True, separators=(",", ":"))
                try:
                    db.execute("INSERT INTO hot(singleton,cycle_id,promoted_at,payload_json) VALUES(1,?,?,?) ON CONFLICT(singleton) DO UPDATE SET cycle_id=excluded.cycle_id,promoted_at=excluded.promoted_at,payload_json=excluded.payload_json", (cycle_id, utc_iso(now_ms), hot_payload))
                except sqlite3.DatabaseError as exc:
                    db.execute("ROLLBACK")
                    raise StateError(f"HOT_PROMOTION_FAILED:{exc}") from exc
            response_json = json.dumps(response, sort_keys=True, separators=(",", ":"))
            db.execute("UPDATE cycles SET status=?, completed_at=?, response_json=? WHERE cycle_id=?", (response["overall_status"], response["completed_at"], response_json, cycle_id))
            db.execute("DELETE FROM leases WHERE slot=? AND cycle_id=? AND owner_id=?", (slot, cycle_id, self.config.owner_id))
            db.execute("COMMIT")

    def release_recoverable(self, slot: str, cycle_id: str, *, attempt: int, now_ms: int) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._assert_owner(db, cycle_id=cycle_id, attempt=attempt, now_ms=now_ms)
            except StateError:
                db.execute("COMMIT")
                return False
            db.execute("UPDATE leases SET lease_until=? WHERE slot=? AND cycle_id=? AND owner_id=?", (now_ms - 1, slot, cycle_id, self.config.owner_id))
            db.execute("UPDATE cycles SET status='RECOVERABLE' WHERE cycle_id=? AND attempt=? AND status IN ('STARTED','COLLECTED','QUALIFIED')", (cycle_id, attempt))
            db.execute("COMMIT")
            return True

    def diagnostics(self, now_ms: int | None = None) -> dict[str, Any]:
        self.compatibility_check()
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        with self.connect() as db:
            hot = db.execute("SELECT cycle_id,promoted_at FROM hot WHERE singleton=1").fetchone()
            return {"state_schema_version": STATE_SCHEMA_VERSION, "spool_bytes": self.spool_bytes(db), "spool_rows": int(db.execute("SELECT COUNT(*) FROM spool WHERE state='PENDING'").fetchone()[0]), "ledger_rows": int(db.execute("SELECT COUNT(*) FROM capability_ledger").fetchone()[0]), "active_leases": int(db.execute("SELECT COUNT(*) FROM leases WHERE lease_until>=?", (now_ms,)).fetchone()[0]), "hot_cycle_id": hot["cycle_id"] if hot else None, "hot_promoted_at": hot["promoted_at"] if hot else None}


class D8Runtime:
    def __init__(self, config: RuntimeConfig, acquisition: AcquisitionCore, clock_ms: Callable[[], int] | None = None):
        self.config = config
        self.acquisition = acquisition
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.state = D8State(config)
        self.accepting = True
        self._cwd_guard = threading.Lock()
        self._sweep_staging()
        self.state.sweep_forwarded(self.clock_ms())
        self.state.recover_nonterminal(self.clock_ms())

    def _sweep_staging(self) -> None:
        import shutil
        staging = self.config.state_root / "staging"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _cleanup_attempt_staging(path: Path) -> None:
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    def health(self) -> dict[str, Any]:
        try:
            with self.state.connect() as db:
                db.execute("SELECT 1").fetchone()
            state = "PASS"
        except Exception:
            state = "FAIL"
        return {"schema_version": "eth-macro-d8-health/1.0.0", "status": "PASS" if self.accepting and state == "PASS" else "FAIL", "accepting": self.accepting, "state_access": state, "runtime_revision": self.config.runtime_revision}

    def readiness(self) -> tuple[int, dict[str, Any]]:
        try:
            self.config.validate()
            now_ms = self.clock_ms()
            info = self.state.diagnostics(now_ms)
            probe = self.config.state_root / ".readiness-probe"
            probe.write_text(str(now_ms)); probe.unlink()
            return 200, {"schema_version": "eth-macro-d8-readiness/1.0.0", "status": "PASS", "profile": self.config.profile, **info}
        except Exception as exc:
            return 503, {"schema_version": "eth-macro-d8-readiness/1.0.0", "status": "FAIL", "error_class": "STATE_SCHEMA_INCOMPATIBLE" if "STATE_SCHEMA_INCOMPATIBLE" in str(exc) else "STATE_IO"}

    def collect_cycle(self, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        now_ms = self.clock_ms()
        if not self.accepting:
            return 503, {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "overall_status": "FAIL", "errors": [{"class": "RUNTIME_INTERNAL", "message": "runtime is shutting down"}]}
        try:
            req = validate_request_common(request, now_ms=now_ms)
        except Exception as exc:
            return 400, self._request_invalid_response(str(exc))
        slot = req["expected_schedule_at"]
        cid = cycle_id_for(slot)
        owner_state, prior, attempt, stale = self.state.acquire(slot=slot, cycle_id=cid, now_ms=now_ms, new_admission_allowed=not new_admission_is_stale(req, now_ms=now_ms))
        if owner_state == "REPLAY":
            replay = dict(prior or {}); replay["replayed"] = True; return 200, replay
        if owner_state == "BUSY": return 409, self._busy_response(cid, slot, "LOCK_BUSY")
        if owner_state == "EXHAUSTED":
            if prior:
                exhausted = dict(prior); exhausted["retry_exhausted"] = True; return 409, exhausted
            return 409, self._error_response(cid, slot, "LEDGER_CONFLICT", "cycle attempt limit exhausted")
        if owner_state == "CONFLICT": return 409, self._error_response(cid, slot, "LEDGER_CONFLICT", "stored cycle identity/runtime contract is incompatible")
        if owner_state in {"STALE_NEW", "STALE_TERMINAL"}: return 400, self._request_invalid_response("stale slot outside new-cycle admission window")
        if owner_state == "RECOVERY_EXPIRED": return 400, self._request_invalid_response("existing cycle recovery bound expired")

        heartbeat_stop = threading.Event(); heartbeat_lost = threading.Event()
        def heartbeat() -> None:
            interval = max(1.0, self.config.lease_seconds / 3)
            while not heartbeat_stop.wait(interval):
                try:
                    if not self.state.renew_lease(slot=slot, cycle_id=cid, now_ms=self.clock_ms()):
                        heartbeat_lost.set(); return
                except Exception:
                    heartbeat_lost.set(); return
        heartbeat_thread = threading.Thread(target=heartbeat, name=f"d8-lease-{cid[-8:]}", daemon=True); heartbeat_thread.start()

        started_ms = now_ms; capability_statuses: dict[str, Any] = {}; observations: list[dict[str, Any]] = []; ledger_rows: list[dict[str, Any]] = []; errors: list[dict[str, Any]] = []
        staging = self.config.state_root / "staging" / cid / f"attempt-{attempt}"; staging.mkdir(parents=True, exist_ok=True)
        try:
            for cap in CAPABILITY_POLICY:
                due = due_state(cap, req["expected_ms"], self.config.profile)
                if due != "DUE":
                    capability_statuses[cap["id"]] = {"status": due, "provider": cap["provider"]}; continue
                checkpointed, checkpoint_ledger = self.state.load_checkpoint(cid, cap["id"])
                if checkpointed and checkpoint_ledger is not None:
                    observations.extend(checkpointed)
                    capability_statuses[cap["id"]] = {"status": "PASS", "provider": cap["provider"], "observation_count": len(checkpointed), "reused_durable_checkpoint": True}
                    ledger_rows.append(checkpoint_ledger); continue
                try:
                    with self._cwd_guard:
                        result = self.acquisition.collect(cap["id"], expected_ms=req["expected_ms"], cycle_id=cid, staging_root=staging)
                    status = result.get("status", "FAIL")
                    if status not in {"PASS", "FAIL", "DEGRADED"}: raise ValueError("invalid acquisition status")
                    produced = self._normalize_observations(cap, result.get("observations", []), cid, req["expected_schedule_at"], self.clock_ms())
                    observations.extend(produced)
                    failure_class = result.get("failure_class")
                    if failure_class and failure_class not in FAILURE_CLASSES: failure_class = "RUNTIME_INTERNAL"
                    capability_statuses[cap["id"]] = {"status": status if produced or status != "PASS" else "FAIL", "provider": cap["provider"], "observation_count": len(produced)}
                    if status == "PASS" and not produced:
                        status = "FAIL"; failure_class = "VALIDATION_FAILED"; capability_statuses[cap["id"]]["status"] = status
                    if status != "PASS": errors.append({"class": failure_class or "PROVIDER_CONNECTIVITY", "capability": cap["id"], "message": result.get("error", status)})
                    ledger = self._ledger_row(cap, status, failure_class, produced, self.clock_ms()); ledger_rows.append(ledger)
                    self.state.checkpoint_capability(cycle_id=cid, attempt=attempt, ledger_row=ledger, observations=produced, now_ms=self.clock_ms())
                except StateError:
                    raise
                except Exception as exc:
                    failure = self._classify_exception(exc)
                    capability_statuses[cap["id"]] = {"status": "FAIL", "provider": cap["provider"], "observation_count": 0}
                    errors.append({"class": failure, "capability": cap["id"], "message": str(exc)[:256]})
                    ledger = self._ledger_row(cap, "FAIL", failure, [], self.clock_ms()); ledger_rows.append(ledger)
                    self.state.checkpoint_capability(cycle_id=cid, attempt=attempt, ledger_row=ledger, observations=[], now_ms=self.clock_ms())
            self._cleanup_attempt_staging(staging)
            if heartbeat_lost.is_set(): raise StateError("LEDGER_CONFLICT: lease ownership lost during cycle")
            due_rows = [(cap, capability_statuses[cap["id"]]["status"]) for cap in CAPABILITY_POLICY if capability_statuses.get(cap["id"], {}).get("status") not in {"NOT_DUE", "DISABLED_BY_POLICY"}]
            required_fail = any(cap.get("required") and status != "PASS" for cap, status in due_rows); any_fail = any(status != "PASS" for _, status in due_rows)
            overall = "FAIL" if required_fail else ("DEGRADED" if any_fail else "PASS"); promote = overall == "PASS"; completed_ms = self.clock_ms()
            response = self._response(cid, req, started_ms, completed_ms, overall, capability_statuses, observations, errors, stale, attempt, promote)
            try:
                self.state.terminalize(cycle_id=cid, slot=slot, attempt=attempt, response=response, observations=observations, ledger_rows=ledger_rows, promote=promote, now_ms=completed_ms)
            except StateError as exc:
                if "SPOOL_FULL" in str(exc):
                    response = self._response(cid, req, started_ms, self.clock_ms(), "FAIL", capability_statuses, [], errors + [{"class": "SPOOL_FULL", "message": "durable spool capacity exceeded"}], stale, attempt, False)
                    self.state.terminalize(cycle_id=cid, slot=slot, attempt=attempt, response=response, observations=[], ledger_rows=ledger_rows, promote=False, now_ms=self.clock_ms())
                else: raise
            heartbeat_stop.set(); heartbeat_thread.join(timeout=1)
            return (200 if response["overall_status"] in {"PASS", "DEGRADED"} else 503), response
        except Exception as exc:
            heartbeat_stop.set(); heartbeat_thread.join(timeout=1); self._cleanup_attempt_staging(staging)
            try: self.state.release_recoverable(slot, cid, attempt=attempt, now_ms=self.clock_ms())
            except Exception: pass
            failure = self._classify_exception(exc); completed_ms = self.clock_ms()
            return 503, {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "cycle_id": cid, "canonical_slot": CANONICAL_SLOT, "expected_schedule_at": slot, "started_at": utc_iso(started_ms), "completed_at": utc_iso(completed_ms), "runtime_revision": self.config.runtime_revision, "source_revision": self.config.source_revision, "overall_status": "FAIL", "provider_statuses": {}, "capability_statuses": capability_statuses, "freshness_summary": {"statuses": [], "observation_count": len(observations)}, "collection_gap_summary": {"gap_count": sum(1 for x in capability_statuses.values() if x.get("status") == "FAIL"), "synthetic_fill": False}, "spool_status": "ERROR" if failure in {"SPOOL_FULL", "STATE_IO"} else "DURABLE_CHECKPOINTS_PRESERVED", "ledger_status": "RECOVERABLE", "hot_promotion": "PREVIOUS_HOT_PRESERVED", "attempt": attempt, "stale_lock_recovered": stale, "errors": errors + [{"class": failure, "message": str(exc)[:256]}]}

    def _normalize_observations(self, cap: dict[str, Any], rows: list[dict[str, Any]], cid: str, slot: str, now_ms: int) -> list[dict[str, Any]]:
        out = []
        for row in rows:
            if not isinstance(row, dict) or "series_id" not in row or "value" not in row:
                raise ValueError("malformed provider observation")
            provider_ts = row.get("provider_timestamp_at")
            fp = fingerprint_payload(row["value"])
            oid = observation_id(cap["provider"], row["series_id"], provider_ts, fp)
            known_at = row.get("known_at") or utc_iso(now_ms)
            parse_utc(known_at)
            provenance = {"runtime_contract": RUNTIME_CONTRACT_VERSION, "source_revision": self.config.source_revision, "provider_route": row.get("provider_route")}
            extra_provenance = row.get("provenance")
            if extra_provenance is not None:
                if not isinstance(extra_provenance, dict): raise ValueError("malformed provider provenance")
                provenance.update(extra_provenance)
            envelope = {
                "schema_version": OBSERVATION_ENVELOPE_VERSION, "observation_id": oid, "fingerprint": fp,
                "provider": cap["provider"], "source_identity": row.get("source_identity", cap["provider"]), "capability_id": cap["id"], "series_id": row["series_id"],
                "provider_timestamp_at": provider_ts, "retrieved_at": utc_iso(now_ms), "known_at": known_at, "collected_at": utc_iso(now_ms),
                "canonical_cycle_id": cid, "canonical_slot": slot, "finality": row.get("finality", "OBSERVED_STATE"),
                "freshness": row.get("freshness", {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": 300}), "validation_status": "PASS",
                "provenance": provenance,
                "d9_forward_seam": {"identity_preserved": True, "known_at_preserved": True, "finality_preserved": True, "collection_gap_compatible": True, "target": row.get("d9_target", "WARM_FORWARD_OBSERVATION")},
                "value": row["value"],
            }
            if row.get("revision_classification") == "PROVIDER_REVISABLE_SNAPSHOT":
                predecessor = self.state.semantic_predecessor(cap["id"], cap["provider"], row["series_id"], provider_ts, fp)
                if predecessor is not None:
                    envelope["provider_revision"] = {
                        "schema_version": "market-data-provider-revision/1.0.0",
                        "metric_policy_schema": "kraken-futures-provider-revision/1.0.0",
                        "classification": "PROVIDER_REVISABLE_SNAPSHOT",
                        "effective_timestamp": provider_ts,
                        "known_at_utc": known_at,
                        "previous_value_fingerprint": predecessor["fingerprint"],
                        "observed_value": row["value"],
                        "revision_of": predecessor["observation_id"],
                        "predecessor_observation_id": predecessor["observation_id"],
                        "source_snapshot_ref": row.get("source_snapshot_ref") or row.get("provider_route"),
                    }
            out.append(envelope)
        return out

    def _ledger_row(self, cap: dict[str, Any], status: str, failure_class: str | None, obs: list[dict[str, Any]], now_ms: int) -> dict[str, Any]:
        ts = obs[-1].get("provider_timestamp_at") if obs else None
        freshness = obs[-1]["freshness"] if obs else {"status": "COLLECTION_GAP" if status == "FAIL" else "UNKNOWN", "age_seconds": None, "target_cadence_seconds": cap.get("every_minutes", 5) * 60}
        return {"capability_id": cap["id"], "provider": cap["provider"], "status": "OBSERVED_STATE" if status == "PASS" else "PROVIDER_FAILURE", "failure_class": failure_class, "provider_timestamp_at": ts, "retrieved_at": utc_iso(now_ms), "known_at": utc_iso(now_ms), "collected_at": utc_iso(now_ms), "fingerprint": fingerprint_payload([o["fingerprint"] for o in obs]) if obs else None, "spool_ref": obs[-1]["observation_id"] if obs else None, "freshness": freshness, "gap_semantics": None if obs else "COLLECTION_GAP_NO_SYNTHETIC_FILL"}

    def _response(self, cid: str, req: dict[str, Any], started_ms: int, completed_ms: int, overall: str, statuses: dict[str, Any], observations: list[dict[str, Any]], errors: list[dict[str, Any]], stale: bool, attempt: int, promote: bool) -> dict[str, Any]:
        providers: dict[str, str] = {}
        for item in statuses.values():
            p = item["provider"]; s = item["status"]
            if p not in providers or providers[p] in {"NOT_DUE", "DISABLED_BY_POLICY", "PASS"}: providers[p] = s
        fresh = [o["freshness"].get("status") for o in observations]; gap_count = sum(1 for s in statuses.values() if s["status"] == "FAIL")
        return {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "cycle_id": cid, "canonical_slot": CANONICAL_SLOT, "expected_schedule_at": req["expected_schedule_at"], "started_at": utc_iso(started_ms), "completed_at": utc_iso(completed_ms), "runtime_revision": self.config.runtime_revision, "source_revision": self.config.source_revision, "overall_status": overall, "provider_statuses": providers, "capability_statuses": statuses, "freshness_summary": {"statuses": sorted(set(fresh)), "observation_count": len(observations)}, "collection_gap_summary": {"gap_count": gap_count, "synthetic_fill": False}, "spool_status": "DURABLE" if observations else "NO_NEW_OBSERVATIONS", "ledger_status": "TERMINAL", "hot_promotion": "PROMOTED" if promote else "PREVIOUS_HOT_PRESERVED", "attempt": attempt, "stale_lock_recovered": stale, "errors": errors}

    def _request_invalid_response(self, message: str) -> dict[str, Any]:
        return {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "overall_status": "FAIL", "errors": [{"class": "REQUEST_INVALID", "message": message}]}

    def _error_response(self, cid: str, slot: str, failure: str, message: str) -> dict[str, Any]:
        return {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "cycle_id": cid, "canonical_slot": CANONICAL_SLOT, "expected_schedule_at": slot, "overall_status": "FAIL", "provider_statuses": {}, "capability_statuses": {}, "freshness_summary": {"statuses": [], "observation_count": 0}, "collection_gap_summary": {"gap_count": 0, "synthetic_fill": False}, "spool_status": "UNCHANGED", "ledger_status": "UNCHANGED", "errors": [{"class": failure, "message": message}]}

    def _busy_response(self, cid: str, slot: str, failure: str) -> dict[str, Any]:
        return {"schema_version": "eth-macro-d8-collect-cycle-response/1.0.0", "cycle_id": cid, "canonical_slot": CANONICAL_SLOT, "expected_schedule_at": slot, "overall_status": "FAIL", "provider_statuses": {}, "capability_statuses": {}, "freshness_summary": {"statuses": [], "observation_count": 0}, "collection_gap_summary": {"gap_count": 0, "synthetic_fill": False}, "spool_status": "UNCHANGED", "ledger_status": "ALREADY_RUNNING", "errors": [{"class": failure, "message": "slot already has a live owner lease"}]}

    @staticmethod
    def _classify_exception(exc: Exception) -> str:
        text = str(exc).lower()
        if "429" in text or "rate" in text and "limit" in text: return "PROVIDER_RATE_LIMIT"
        if "timeout" in text: return "PROVIDER_TIMEOUT"
        if "schema" in text or "malformed" in text: return "PROVIDER_SCHEMA"
        if "spool_full" in text: return "SPOOL_FULL"
        if "state_schema" in text: return "STATE_SCHEMA_INCOMPATIBLE"
        if "hot_promotion" in text: return "HOT_PROMOTION_FAILED"
        if "ledger_conflict" in text or "lease ownership lost" in text: return "LEDGER_CONFLICT"
        if "state_io" in text: return "STATE_IO"
        if isinstance(exc, (sqlite3.DatabaseError, OSError)): return "STATE_IO"
        return "PROVIDER_CONNECTIVITY"

    def begin_shutdown(self) -> None:
        self.accepting = False


class DeterministicMockAcquisition:
    """Allowed only for development/test qualification; never selected by VPS_SHADOW."""
    def __init__(self, fail: set[str] | None = None, delay: float = 0.0):
        self.fail = fail or set(); self.delay = delay; self.calls: dict[str, int] = {}

    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict[str, Any]:
        self.calls[capability_id] = self.calls.get(capability_id, 0) + 1
        if self.delay: time.sleep(self.delay)
        if capability_id in self.fail: return {"status": "FAIL", "failure_class": "PROVIDER_TIMEOUT", "error": "deterministic injected timeout", "observations": []}
        provider = next(c["provider"] for c in CAPABILITY_POLICY if c["id"] == capability_id)
        value = {"mock": True, "capability": capability_id, "slot_ms": expected_ms}
        finality = "FINALIZED" if any(token in capability_id for token in ("m5", "15m", "1h", "4h", "1d", "1w", "h1-history")) else "OBSERVED_STATE"
        return {"status": "PASS", "observations": [{"series_id": f"runtime.{provider}.{capability_id}", "provider_timestamp_at": utc_iso(expected_ms), "finality": finality, "freshness": {"status": "LIVE_USABLE", "age_seconds": 0, "target_cadence_seconds": 300}, "value": value, "d9_target": "FIXED_GRID" if finality == "FINALIZED" else "SAMPLED_SCHEDULE"}]}


def config_from_env() -> RuntimeConfig:
    profile = os.environ.get("D8_RUNTIME_PROFILE", "development")
    root = Path(os.environ.get("RUNTIME_STATE_ROOT", "/var/lib/eth-macro-data-bridge"))
    return RuntimeConfig(state_root=root, profile=profile, source_revision=os.environ.get("D8_SOURCE_REVISION", "UNBOUND_SOURCE_REVISION"), runtime_revision=os.environ.get("D8_RUNTIME_REVISION", RUNTIME_CONTRACT_VERSION), spool_max_bytes=int(os.environ.get("D8_SPOOL_MAX_BYTES", DEFAULT_SPOOL_MAX_BYTES)), spool_retention_seconds=int(os.environ.get("D8_SPOOL_RETENTION_SECONDS", DEFAULT_SPOOL_RETENTION_SECONDS),), lease_seconds=int(os.environ.get("D8_LEASE_SECONDS", DEFAULT_LEASE_SECONDS)), owner_id=os.environ.get("D8_OWNER_ID", f"pid-{os.getpid()}"))
