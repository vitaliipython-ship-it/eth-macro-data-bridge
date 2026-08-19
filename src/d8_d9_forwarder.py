from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from history_store import ImmutableHistoryConflict, append_partition, partition_descriptor

FORWARD_CONTRACT_VERSION = "d8-d9-forward-batch/1.0.0"
D8_OBSERVATION_SCHEMA = "market-data-d8-runtime-observation/1.0.0"
D9_WARM_PARTITION_SCHEMA = "market-data-d8-origin-warm-partition/1.0.0"
D9_COLLECTION_LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
D8_STATE_SCHEMA_VERSION = "2"
D8_RUNTIME_CONTRACT_VERSION = "eth-macro-d8-runtime/1.0.0"
FORWARDED_RETENTION_SECONDS = 7 * 86400
ALLOWED_FINALITY = frozenset({"FINALIZED", "OBSERVED_STATE", "PROVISIONAL"})
ALLOWED_TARGETS = frozenset({"FIXED_GRID", "SAMPLED_SCHEDULE"})

CAPABILITY_PROVIDER = {
    "binance-spot.m5": "binance-spot",
    "kraken-spot.m5": "kraken-spot",
    "binance-usdm.m5-current": "binance-usdm",
    "deribit-perpetual.current": "deribit-perpetual",
    "liquidity.current": "multi-provider",
    "kraken-futures.analytics": "kraken-futures",
    "deribit-options.surface-dvol": "deribit-options",
}
CAPABILITY_TARGETS = {
    "binance-spot.m5": {"FIXED_GRID"},
    "kraken-spot.m5": {"FIXED_GRID"},
    "binance-usdm.m5-current": {"FIXED_GRID", "SAMPLED_SCHEDULE"},
    "deribit-perpetual.current": {"SAMPLED_SCHEDULE"},
    "liquidity.current": {"SAMPLED_SCHEDULE"},
    "kraken-futures.analytics": {"SAMPLED_SCHEDULE"},
    "deribit-options.surface-dvol": {"SAMPLED_SCHEDULE"},
}
CAPABILITY_SERIES_PREFIXES = {
    "binance-spot.m5": ("spot.binance-spot.",),
    "kraken-spot.m5": ("spot.kraken-spot.",),
    "binance-usdm.m5-current": ("derivatives.binance-usdm.", "liquidity.binance-usdm."),
    "deribit-perpetual.current": ("derivatives.deribit-perpetual.",),
    "liquidity.current": ("liquidity.",),
    "kraken-futures.analytics": ("derivatives.kraken-futures.",),
    "deribit-options.surface-dvol": ("options.deribit-options.",),
}


class ClosingConnection(sqlite3.Connection):
    """sqlite transaction context that also closes the descriptor."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class ForwardContractError(RuntimeError):
    """Fail-closed D8→D9 contract violation."""


class InjectedForwardCrash(RuntimeError):
    """Test-only simulated process crash at a durable seam boundary."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _fingerprint(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _observation_id(provider: str, series_id: str, provider_timestamp_at: str | None, fingerprint: str) -> str:
    raw = f"{provider}|{series_id}|{provider_timestamp_at or 'NONE'}|{fingerprint}"
    return "obs-" + _sha256_text(raw)


def _parse_utc_ms(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ForwardContractError("timestamp must be UTC RFC3339 with Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ForwardContractError("invalid UTC timestamp") from exc
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _day_path(timestamp_at: str) -> str:
    dt = datetime.fromtimestamp(_parse_utc_ms(timestamp_at) / 1000, timezone.utc)
    return dt.strftime("%Y/%m/%d")


def _date_text(timestamp_at: str) -> str:
    dt = datetime.fromtimestamp(_parse_utc_ms(timestamp_at) / 1000, timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _series_token(series_id: str) -> str:
    return hashlib.sha256(series_id.encode()).hexdigest()[:24]


def _observation_key(row: Any) -> str:
    if not isinstance(row, dict) or not isinstance(row.get("observation_id"), str):
        raise ValueError("D8-origin WARM record lacks observation_id")
    return row["observation_id"]


def _run_key(row: Any) -> str:
    if not isinstance(row, dict) or not isinstance(row.get("run_id"), str):
        raise ValueError("collection run lacks run_id")
    return row["run_id"]


class D8ToD9Forwarder:
    """Internal repository-owned D8 spool → existing D9 WARM adapter.

    This class intentionally imports no provider acquisition modules and exposes no
    agent-facing market-data API. It materializes exact validated D8 envelopes via
    the existing D9 ``history_store.append_partition`` primitive.
    """

    def __init__(
        self,
        state_root: Path,
        warm_root: Path,
        *,
        forwarded_retention_seconds: int = FORWARDED_RETENTION_SECONDS,
    ):
        self.state_root = Path(state_root)
        self.warm_root = Path(warm_root)
        self.db_path = self.state_root / "d8-runtime.sqlite3"
        self.forwarded_retention_seconds = int(forwarded_retention_seconds)
        if self.forwarded_retention_seconds <= 0:
            raise ValueError("forwarded_retention_seconds must be positive")

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.is_file():
            raise ForwardContractError(f"D8 state database not found: {self.db_path}")
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def validate_source(self) -> None:
        with self._connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key='state_schema_version'").fetchone()
            if row is None or row[0] != D8_STATE_SCHEMA_VERSION:
                raise ForwardContractError("STATE_SCHEMA_INCOMPATIBLE")
            required = {"spool", "cycles", "capability_ledger", "hot"}
            existing = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            missing = sorted(required - existing)
            if missing:
                raise ForwardContractError(f"D8 state tables missing: {missing}")

    @staticmethod
    def _validate_envelope_shape(envelope: dict[str, Any]) -> tuple[str, str]:
        if envelope.get("schema_version") != D8_OBSERVATION_SCHEMA:
            raise ForwardContractError("D8 observation schema mismatch")
        required = {
            "observation_id", "fingerprint", "provider", "capability_id", "series_id",
            "retrieved_at", "known_at", "collected_at", "canonical_cycle_id",
            "canonical_slot", "finality", "validation_status", "provenance", "d9_forward_seam", "value",
        }
        missing = sorted(required - set(envelope))
        if missing:
            raise ForwardContractError(f"D8 observation envelope missing fields: {missing}")
        if envelope["validation_status"] != "PASS":
            raise ForwardContractError("only validation_status=PASS observations may be forwarded")
        provider = envelope["provider"]
        capability = envelope["capability_id"]
        if CAPABILITY_PROVIDER.get(capability) != provider:
            raise ForwardContractError("capability/provider identity mismatch")
        series_id = envelope["series_id"]
        if not isinstance(series_id, str) or not any(series_id.startswith(prefix) for prefix in CAPABILITY_SERIES_PREFIXES[capability]):
            raise ForwardContractError("capability/series identity mismatch")
        target = envelope["d9_forward_seam"].get("target")
        if target not in ALLOWED_TARGETS or target not in CAPABILITY_TARGETS[capability]:
            raise ForwardContractError("unsupported D9 lifecycle mapping")
        finality = envelope["finality"]
        if finality not in ALLOWED_FINALITY:
            raise ForwardContractError("unsupported finality")
        for name in ("retrieved_at", "known_at", "collected_at", "canonical_slot"):
            _parse_utc_ms(envelope[name])
        provider_timestamp = envelope.get("provider_timestamp_at")
        if provider_timestamp is not None:
            _parse_utc_ms(provider_timestamp)
        fingerprint = envelope["fingerprint"]
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or _fingerprint(envelope["value"]) != fingerprint:
            raise ForwardContractError("payload fingerprint mismatch")
        expected_oid = _observation_id(provider, series_id, provider_timestamp, fingerprint)
        if envelope["observation_id"] != expected_oid:
            raise ForwardContractError("observation_id identity mismatch")
        provenance = envelope["provenance"]
        if not isinstance(provenance, dict):
            raise ForwardContractError("provenance must be an object")
        if provenance.get("runtime_contract") != D8_RUNTIME_CONTRACT_VERSION:
            raise ForwardContractError("runtime contract mismatch")
        if not isinstance(provenance.get("source_revision"), str) or not provenance["source_revision"]:
            raise ForwardContractError("source revision provenance missing")
        return target, series_id

    def _validate_spool_binding(self, db: sqlite3.Connection, row: sqlite3.Row, envelope: dict[str, Any]) -> tuple[str, str]:
        target, series_id = self._validate_envelope_shape(envelope)
        if row["observation_id"] != envelope["observation_id"]:
            raise ForwardContractError("spool observation_id binding mismatch")
        if row["cycle_id"] != envelope["canonical_cycle_id"]:
            raise ForwardContractError("spool cycle binding mismatch")
        if row["capability_id"] != envelope["capability_id"]:
            raise ForwardContractError("spool capability binding mismatch")
        cycle = db.execute("SELECT * FROM cycles WHERE cycle_id=?", (row["cycle_id"],)).fetchone()
        if cycle is None:
            raise ForwardContractError("spool observation missing cycle provenance")
        ledger = db.execute(
            "SELECT * FROM capability_ledger WHERE cycle_id=? AND capability_id=? AND status='OBSERVED_STATE' "
            "ORDER BY attempt DESC LIMIT 1",
            (row["cycle_id"], row["capability_id"]),
        ).fetchone()
        if cycle["status"] not in {"PASS", "DEGRADED", "FAIL"} or not cycle["response_json"]:
            raise ForwardContractError("spool observation lacks terminal cycle evidence")
        if ledger is None:
            raise ForwardContractError("spool observation lacks qualified OBSERVED_STATE ledger evidence")
        return target, series_id

    def _pending(self, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.validate_source()
        with self._connect() as db:
            rows = db.execute(
                "SELECT observation_id,cycle_id,capability_id,payload_json,created_at "
                "FROM spool WHERE state='PENDING' ORDER BY created_at,observation_id LIMIT ?",
                (limit,),
            ).fetchall()
            pending: list[dict[str, Any]] = []
            for row in rows:
                try:
                    envelope = json.loads(row["payload_json"])
                except json.JSONDecodeError as exc:
                    raise ForwardContractError("corrupt D8 spool payload_json") from exc
                target, series_id = self._validate_spool_binding(db, row, envelope)
                pending.append(
                    {
                        "observation_id": row["observation_id"],
                        "cycle_id": row["cycle_id"],
                        "capability_id": row["capability_id"],
                        "created_at": int(row["created_at"]),
                        "target": target,
                        "series_id": series_id,
                        "envelope": envelope,
                    }
                )
            return pending

    def _warm_path(self, item: dict[str, Any]) -> Path:
        envelope = item["envelope"]
        anchor = envelope.get("provider_timestamp_at") or envelope["known_at"]
        return (
            self.warm_root
            / "d8-origin"
            / item["target"].lower().replace("_", "-")
            / _series_token(item["series_id"])
            / f"{_day_path(anchor)}.json"
        )

    @staticmethod
    def _warm_metadata(item: dict[str, Any]) -> dict[str, Any]:
        envelope = item["envelope"]
        return {
            "schema_version": D9_WARM_PARTITION_SCHEMA,
            "d9_role": "CANONICAL_D8_ORIGIN_WARM",
            "source_plane": "D8",
            "history_backend": "history_store.append_partition",
            "series_id": item["series_id"],
            "provider": envelope["provider"],
            "capability_id": item["capability_id"],
            "lifecycle_class": item["target"],
            "identity": "observation_id",
            "native_provider_row_claimed": False,
            "synthetic_fill": False,
        }

    def _preflight_warm(self, pending: list[dict[str, Any]]) -> tuple[set[str], dict[Path, list[dict[str, Any]]]]:
        already: set[str] = set()
        grouped: dict[Path, list[dict[str, Any]]] = defaultdict(list)
        for item in pending:
            path = self._warm_path(item)
            grouped[path].append(item["envelope"])
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ForwardContractError(f"invalid existing WARM partition: {path}") from exc
            expected = self._warm_metadata(item)
            for name in ("schema_version", "series_id", "provider", "capability_id", "lifecycle_class", "identity"):
                if payload.get(name) != expected[name]:
                    raise ForwardContractError(f"WARM partition metadata conflict: {path}:{name}")
            records = payload.get("observations")
            if not isinstance(records, list):
                raise ForwardContractError(f"WARM observations field invalid: {path}")
            index = {record.get("observation_id"): record for record in records if isinstance(record, dict)}
            oid = item["observation_id"]
            if oid in index:
                if index[oid] != item["envelope"]:
                    raise ForwardContractError(f"immutable WARM observation identity conflict: {oid}")
                already.add(oid)
        return already, grouped

    def _write_warm(self, pending: list[dict[str, Any]], grouped: dict[Path, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        item_by_path = {self._warm_path(item): item for item in pending}
        evidence: list[dict[str, Any]] = []
        for path in sorted(grouped, key=lambda p: p.as_posix()):
            item = item_by_path[path]
            metadata = self._warm_metadata(item)
            try:
                append_partition(path, metadata, grouped[path], records_field="observations", key=_observation_key)
            except ImmutableHistoryConflict as exc:
                raise ForwardContractError(str(exc)) from exc
            payload = json.loads(path.read_text())
            by_id = {row["observation_id"]: row for row in payload["observations"]}
            for envelope in grouped[path]:
                if by_id.get(envelope["observation_id"]) != envelope:
                    raise ForwardContractError(f"WARM read-back mismatch: {envelope['observation_id']}")
            desc = partition_descriptor(path, records_field="observations", key=_observation_key)
            desc["series_id"] = item["series_id"]
            desc["lifecycle_class"] = item["target"]
            desc["observation_ids"] = sorted(row["observation_id"] for row in grouped[path])
            evidence.append(desc)
        return evidence

    def _warm_destinations_by_cycle_capability(self, evidence: list[dict[str, Any]], pending: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
        oid_to_path: dict[str, str] = {}
        for entry in evidence:
            for oid in entry["observation_ids"]:
                oid_to_path[oid] = entry["path"]
        result: dict[tuple[str, str], set[str]] = defaultdict(set)
        for item in pending:
            path = oid_to_path.get(item["observation_id"])
            if path:
                result[(item["cycle_id"], item["capability_id"])].add(path)
        return {key: sorted(paths) for key, paths in result.items()}

    def _materialize_collection_runs(self, pending: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        destinations = self._warm_destinations_by_cycle_capability(evidence, pending)
        with self._connect() as db:
            cycles = {row["cycle_id"]: row for row in db.execute("SELECT * FROM cycles").fetchall()}
            ledger_rows = db.execute("SELECT * FROM capability_ledger ORDER BY cycle_id,attempt,capability_id").fetchall()
            materialized: list[dict[str, Any]] = []
            seen: set[tuple[str, str, int]] = set()
            for row in ledger_rows:
                cycle = cycles.get(row["cycle_id"])
                if cycle is None:
                    raise ForwardContractError("capability ledger missing cycle")
                if cycle["status"] not in {"PASS", "DEGRADED", "FAIL"} or not cycle["response_json"]:
                    continue
                attempt = int(row["attempt"])
                seen.add((row["cycle_id"], row["capability_id"], attempt))
                failure_class = row["failure_class"]
                status = row["status"]
                if status == "PROVIDER_FAILURE" and failure_class == "VALIDATION_FAILED":
                    semantic_status = "VALIDATION_FAILURE"
                else:
                    semantic_status = status
                refs = destinations.get((row["cycle_id"], row["capability_id"]), [])
                materialized.append(
                    {
                        "run_id": f"d8:{row['cycle_id']}:{row['capability_id']}:{attempt}",
                        "expected_schedule_at": cycle["expected_at"],
                        "collection_started_at": cycle["started_at"],
                        "collection_completed_at": row["collected_at"],
                        "provider": row["provider"],
                        "series_or_capability": row["capability_id"],
                        "status": semantic_status,
                        "snapshot_ref": refs[0] if len(refs) == 1 else None,
                        "warm_destination_refs": refs,
                        "error_class": failure_class,
                        "provider_timestamp_at": row["provider_timestamp_at"],
                        "known_at": row["known_at"],
                        "retrieved_at": row["retrieved_at"],
                        "freshness": json.loads(row["freshness_json"]),
                        "gap_semantics": row["gap_semantics"],
                        "d8_cycle_id": row["cycle_id"],
                        "d8_attempt": attempt,
                        "d8_source_revision": row["source_revision"],
                        "d8_runtime_revision": row["runtime_revision"],
                        "synthetic_fill": False,
                    }
                )
            for cycle in cycles.values():
                if not cycle["response_json"]:
                    continue
                try:
                    response = json.loads(cycle["response_json"])
                except json.JSONDecodeError as exc:
                    raise ForwardContractError("corrupt cycle response_json") from exc
                attempt = int(cycle["attempt"])
                for capability_id, cap_status in response.get("capability_statuses", {}).items():
                    key = (cycle["cycle_id"], capability_id, attempt)
                    if key in seen:
                        continue
                    status = cap_status.get("status")
                    if status not in {"NOT_DUE", "DISABLED_BY_POLICY"}:
                        continue
                    provider = cap_status.get("provider") or CAPABILITY_PROVIDER.get(capability_id)
                    completed = cycle["completed_at"] or response.get("completed_at") or cycle["started_at"]
                    materialized.append(
                        {
                            "run_id": f"d8:{cycle['cycle_id']}:{capability_id}:{attempt}",
                            "expected_schedule_at": cycle["expected_at"],
                            "collection_started_at": cycle["started_at"],
                            "collection_completed_at": completed,
                            "provider": provider,
                            "series_or_capability": capability_id,
                            "status": status,
                            "snapshot_ref": None,
                            "warm_destination_refs": [],
                            "error_class": None,
                            "provider_timestamp_at": None,
                            "known_at": completed,
                            "retrieved_at": completed,
                            "freshness": {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": None},
                            "gap_semantics": status,
                            "d8_cycle_id": cycle["cycle_id"],
                            "d8_attempt": attempt,
                            "d8_source_revision": cycle["source_revision"],
                            "d8_runtime_revision": cycle["runtime_revision"],
                            "synthetic_fill": False,
                        }
                    )

        grouped: dict[Path, list[dict[str, Any]]] = defaultdict(list)
        for run in materialized:
            anchor = run["expected_schedule_at"]
            path = self.warm_root / "collection-runs" / _day_path(anchor) / "runs.json"
            grouped[path].append(run)

        run_evidence: list[dict[str, Any]] = []
        for path in sorted(grouped, key=lambda p: p.as_posix()):
            rows = grouped[path]
            metadata = {
                "schema_version": D9_COLLECTION_LEDGER_SCHEMA,
                "date_utc": _date_text(rows[0]["expected_schedule_at"]),
                "d9_role": "D8_TO_D9_COLLECTION_RUN_EVIDENCE",
            }
            try:
                append_partition(path, metadata, rows, records_field="runs", key=_run_key)
            except ImmutableHistoryConflict as exc:
                raise ForwardContractError(str(exc)) from exc
            desc = partition_descriptor(path, records_field="runs", key=_run_key)
            run_evidence.append(desc)
        return run_evidence

    def _mark_forwarded(self, observation_ids: list[str], now_ms: int) -> None:
        if not observation_ids:
            return
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            placeholders = ",".join("?" for _ in observation_ids)
            rows = db.execute(
                f"SELECT observation_id,state FROM spool WHERE observation_id IN ({placeholders})",
                observation_ids,
            ).fetchall()
            states = {row["observation_id"]: row["state"] for row in rows}
            if set(states) != set(observation_ids) or any(states[oid] != "PENDING" for oid in observation_ids):
                db.execute("ROLLBACK")
                raise ForwardContractError("D8 ACK state changed concurrently")
            expires_at = now_ms + self.forwarded_retention_seconds * 1000
            cur = db.execute(
                f"UPDATE spool SET state='FORWARDED', expires_at=? "
                f"WHERE observation_id IN ({placeholders}) AND state='PENDING'",
                [expires_at, *observation_ids],
            )
            if int(cur.rowcount) != len(observation_ids):
                db.execute("ROLLBACK")
                raise ForwardContractError("D8 ACK update was partial")
            db.execute("COMMIT")

    def _source_cursor(self, pending: list[dict[str, Any]]) -> dict[str, Any]:
        ids = [item["observation_id"] for item in pending]
        with self._connect() as db:
            completed = db.execute("SELECT MAX(completed_at) FROM cycles").fetchone()[0]
        return {
            "spool_first_created_at": min(item["created_at"] for item in pending) if pending else None,
            "spool_max_created_at": max(item["created_at"] for item in pending) if pending else None,
            "observation_ids_sha256": _sha256_text(_canonical_json(ids)),
            "cycle_max_completed_at": completed,
        }

    def forward_pending(
        self,
        *,
        limit: int = 500,
        now_ms: int | None = None,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        pending = self._pending(limit)
        if not pending:
            return {
                "schema_version": FORWARD_CONTRACT_VERSION,
                "batch_id": None,
                "accepted_observation_ids": [],
                "already_present_observation_ids": [],
                "rejected_observations": [],
                "warm_destination_evidence": [],
                "collection_run_evidence": [],
                "durable_commit_status": "NOOP",
                "read_back_integrity": "PASS",
                "ack_state": "NOOP",
                "source_cursor": None,
                "provider_reacquisition_count": 0,
            }
        ids = [item["observation_id"] for item in pending]
        batch_id = "d8f-" + _sha256_text(
            _canonical_json({"contract": FORWARD_CONTRACT_VERSION, "observation_ids": ids})
        )[:32]
        already, grouped = self._preflight_warm(pending)
        if failpoint:
            failpoint("before_warm_commit")
        warm_evidence = self._write_warm(pending, grouped)
        run_evidence = self._materialize_collection_runs(pending, warm_evidence)
        if failpoint:
            failpoint("after_warm_commit_before_ack")
        self._mark_forwarded(ids, now_ms)
        return {
            "schema_version": FORWARD_CONTRACT_VERSION,
            "batch_id": batch_id,
            "accepted_observation_ids": [oid for oid in ids if oid not in already],
            "already_present_observation_ids": [oid for oid in ids if oid in already],
            "rejected_observations": [],
            "warm_destination_evidence": warm_evidence,
            "collection_run_evidence": run_evidence,
            "durable_commit_status": "COMMITTED",
            "read_back_integrity": "PASS",
            "ack_state": "ACKED",
            "source_cursor": self._source_cursor(pending),
            "provider_reacquisition_count": 0,
        }

    def read_hot_snapshot(self) -> dict[str, Any] | None:
        """Internal local physical source seam for a future resolver-owned HOT reader.

        This is deliberately not an HTTP or agent-facing API.
        """
        self.validate_source()
        with self._connect() as db:
            row = db.execute("SELECT cycle_id,promoted_at,payload_json FROM hot WHERE singleton=1").fetchone()
            if row is None:
                return None
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError as exc:
                raise ForwardContractError("corrupt D8 HOT payload") from exc
            if payload.get("schema_version") != "eth-macro-d8-hot/1.0.0":
                raise ForwardContractError("D8 HOT schema mismatch")
            if payload.get("cycle_id") != row["cycle_id"]:
                raise ForwardContractError("D8 HOT cycle binding mismatch")
            observations = payload.get("observations")
            if not isinstance(observations, list):
                raise ForwardContractError("D8 HOT observations field invalid")
            for envelope in observations:
                self._validate_envelope_shape(envelope)
            return {
                "transport_contract": "d8-hot-internal-physical-source/1.0.0",
                "agent_facing": False,
                "read_only": True,
                "cycle_id": row["cycle_id"],
                "promoted_at": row["promoted_at"],
                "payload": payload,
            }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Internal D8 spool → D9 WARM one-shot forwarder")
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--warm-root", required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args(argv)
    forwarder = D8ToD9Forwarder(Path(args.state_root), Path(args.warm_root))
    result = forwarder.forward_pending(limit=args.limit, now_ms=args.now_ms)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
