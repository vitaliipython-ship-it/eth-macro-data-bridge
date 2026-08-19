from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from d8_capability_routing import capability_provider
from d8_d9_forwarder import (
    D8ToD9Forwarder as BaseD8ToD9Forwarder,
    D9_COLLECTION_LEDGER_SCHEMA,
    FORWARD_CONTRACT_VERSION,
    ForwardContractError,
    _canonical_json,
    _date_text,
    _day_path,
    _run_key,
    _sha256_text,
)
from history_store import ImmutableHistoryConflict, append_partition, partition_descriptor


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



class D8ToD9Forwarder(BaseD8ToD9Forwarder):
    """Integrity-bound successor policy over the qualified D8→D9 adapter.

    The base module owns physical append/ACK mechanics. This policy layer binds every
    forwarded spool row to complete checkpoint-v2 evidence, enforces canonical
    lifecycle mapping from series semantics, and exports gap-only terminal lifecycle
    evidence even when a cycle produced no market observation.
    """

    def validate_source(self) -> None:
        super().validate_source()
        with self._connect() as db:
            required = {"cycle_checkpoints", "cycle_checkpoint_observations"}
            existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = sorted(required - existing)
            if missing:
                raise ForwardContractError(f"checkpoint-v2 state tables missing: {missing}")

    @staticmethod
    def _validate_envelope_shape(envelope: dict[str, Any]) -> tuple[str, str]:
        # Base validation is declaration-bound; integrity layer adds checkpoint-v2 evidence only.
        return BaseD8ToD9Forwarder._validate_envelope_shape(envelope)

    @staticmethod
    def _validated_checkpoint_payloads(
        db: sqlite3.Connection, cycle_id: str, capability_id: str
    ) -> dict[str, dict[str, Any]]:
        checkpoint = db.execute(
            "SELECT * FROM cycle_checkpoints WHERE cycle_id=? AND capability_id=?",
            (cycle_id, capability_id),
        ).fetchone()
        if checkpoint is None:
            raise ForwardContractError("qualified spool observation lacks checkpoint-v2 evidence")
        ledger = db.execute(
            "SELECT * FROM capability_ledger WHERE cycle_id=? AND capability_id=? AND attempt=?",
            (cycle_id, capability_id, int(checkpoint["checkpoint_attempt"])),
        ).fetchone()
        if ledger is None or ledger["status"] != "OBSERVED_STATE":
            raise ForwardContractError("checkpoint-v2 ledger binding missing or non-observed")
        try:
            ledger_view = {
                "capability_id": capability_id,
                "provider": ledger["provider"],
                "status": ledger["status"],
                "failure_class": ledger["failure_class"],
                "provider_timestamp_at": ledger["provider_timestamp_at"],
                "retrieved_at": ledger["retrieved_at"],
                "known_at": ledger["known_at"],
                "collected_at": ledger["collected_at"],
                "fingerprint": ledger["fingerprint"],
                "spool_ref": ledger["spool_ref"],
                "freshness": json.loads(ledger["freshness_json"]),
                "gap_semantics": ledger["gap_semantics"],
            }
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ForwardContractError("checkpoint-v2 ledger binding is corrupt") from exc
        if _ledger_binding(ledger_view) != checkpoint["ledger_sha256"]:
            raise ForwardContractError("checkpoint-v2 ledger hash mismatch")
        rows = db.execute(
            "SELECT position,observation_id,payload_json,payload_sha256 "
            "FROM cycle_checkpoint_observations WHERE cycle_id=? AND capability_id=? ORDER BY position",
            (cycle_id, capability_id),
        ).fetchall()
        expected_count = int(checkpoint["expected_count"])
        if expected_count <= 0 or len(rows) != expected_count:
            raise ForwardContractError("checkpoint-v2 expected_count mismatch")
        if [int(row["position"]) for row in rows] != list(range(expected_count)):
            raise ForwardContractError("checkpoint-v2 position sequence mismatch")
        observation_ids = [row["observation_id"] for row in rows]
        if len(observation_ids) != len(set(observation_ids)):
            raise ForwardContractError("checkpoint-v2 duplicate membership")
        if _sha256_text(_canonical_json(observation_ids)) != checkpoint["membership_sha256"]:
            raise ForwardContractError("checkpoint-v2 membership hash mismatch")
        payloads: list[dict[str, Any]] = []
        by_id: dict[str, dict[str, Any]] = {}
        try:
            for row in rows:
                payload_json = row["payload_json"]
                if _sha256_text(payload_json) != row["payload_sha256"]:
                    raise ForwardContractError("checkpoint-v2 member payload hash mismatch")
                payload = json.loads(payload_json)
                if payload.get("observation_id") != row["observation_id"]:
                    raise ForwardContractError("checkpoint-v2 member observation_id mismatch")
                if payload.get("capability_id") != capability_id:
                    raise ForwardContractError("checkpoint-v2 member capability mismatch")
                if payload.get("canonical_cycle_id") != cycle_id:
                    raise ForwardContractError("checkpoint-v2 member cycle mismatch")
                payloads.append(payload)
                by_id[row["observation_id"]] = payload
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ForwardContractError("checkpoint-v2 member payload is corrupt") from exc
        if _sha256_text(_canonical_json(payloads)) != checkpoint["payload_sha256"]:
            raise ForwardContractError("checkpoint-v2 aggregate payload hash mismatch")
        return by_id

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
            checkpoint_cache: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
            for row in rows:
                try:
                    envelope = json.loads(row["payload_json"])
                except json.JSONDecodeError as exc:
                    raise ForwardContractError("corrupt D8 spool payload_json") from exc
                target, series_id = self._validate_envelope_shape(envelope)
                if row["observation_id"] != envelope["observation_id"]:
                    raise ForwardContractError("spool observation_id binding mismatch")
                if row["cycle_id"] != envelope["canonical_cycle_id"]:
                    raise ForwardContractError("spool cycle binding mismatch")
                if row["capability_id"] != envelope["capability_id"]:
                    raise ForwardContractError("spool capability binding mismatch")
                cycle = db.execute("SELECT * FROM cycles WHERE cycle_id=?", (row["cycle_id"],)).fetchone()
                if cycle is None or cycle["status"] not in {"PASS", "DEGRADED", "FAIL"} or not cycle["response_json"]:
                    raise ForwardContractError("spool observation lacks terminal cycle evidence")
                key = (row["cycle_id"], row["capability_id"])
                checkpoint_payloads = checkpoint_cache.get(key)
                if checkpoint_payloads is None:
                    checkpoint_payloads = self._validated_checkpoint_payloads(db, *key)
                    checkpoint_cache[key] = checkpoint_payloads
                checkpoint_payload = checkpoint_payloads.get(row["observation_id"])
                if checkpoint_payload is None:
                    raise ForwardContractError("spool observation is not a member of complete checkpoint-v2 evidence")
                if checkpoint_payload != envelope:
                    raise ForwardContractError("spool payload differs from checkpoint-v2 cycle-local payload")
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

    def _existing_gap_run_ids(self) -> set[str]:
        base = self.warm_root / "collection-runs"
        run_ids: set[str] = set()
        if not base.exists():
            return run_ids
        for path in sorted(base.rglob("runs.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ForwardContractError(f"invalid existing D9 collection-run ledger: {path}") from exc
            if payload.get("schema_version") != D9_COLLECTION_LEDGER_SCHEMA:
                raise ForwardContractError(f"collection-run ledger schema conflict: {path}")
            rows = payload.get("runs")
            if not isinstance(rows, list):
                raise ForwardContractError(f"collection-run ledger rows invalid: {path}")
            for row in rows:
                run_ids.add(_run_key(row))
        return run_ids

    def _materialize_gap_only_runs(self) -> list[dict[str, Any]]:
        existing = self._existing_gap_run_ids()
        materialized: list[dict[str, Any]] = []
        with self._connect() as db:
            cycles = {row["cycle_id"]: row for row in db.execute("SELECT * FROM cycles").fetchall()}
            seen: set[tuple[str, str, int]] = set()
            for row in db.execute("SELECT * FROM capability_ledger ORDER BY cycle_id,attempt,capability_id").fetchall():
                cycle = cycles.get(row["cycle_id"])
                if cycle is None or cycle["status"] not in {"PASS", "DEGRADED", "FAIL"} or not cycle["response_json"]:
                    continue
                attempt = int(row["attempt"])
                seen.add((row["cycle_id"], row["capability_id"], attempt))
                if row["status"] == "OBSERVED_STATE":
                    continue
                failure_class = row["failure_class"]
                status = "VALIDATION_FAILURE" if row["status"] == "PROVIDER_FAILURE" and failure_class == "VALIDATION_FAILED" else row["status"]
                run_id = f"d8:{row['cycle_id']}:{row['capability_id']}:{attempt}"
                if run_id in existing:
                    continue
                materialized.append(
                    {
                        "run_id": run_id,
                        "expected_schedule_at": cycle["expected_at"],
                        "collection_started_at": cycle["started_at"],
                        "collection_completed_at": row["collected_at"],
                        "provider": row["provider"],
                        "series_or_capability": row["capability_id"],
                        "status": status,
                        "snapshot_ref": None,
                        "warm_destination_refs": [],
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
                response = json.loads(cycle["response_json"])
                attempt = int(cycle["attempt"])
                for capability_id, cap_status in response.get("capability_statuses", {}).items():
                    key = (cycle["cycle_id"], capability_id, attempt)
                    if key in seen or cap_status.get("status") not in {"NOT_DUE", "DISABLED_BY_POLICY"}:
                        continue
                    run_id = f"d8:{cycle['cycle_id']}:{capability_id}:{attempt}"
                    if run_id in existing:
                        continue
                    completed = cycle["completed_at"] or response.get("completed_at") or cycle["started_at"]
                    materialized.append(
                        {
                            "run_id": run_id,
                            "expected_schedule_at": cycle["expected_at"],
                            "collection_started_at": cycle["started_at"],
                            "collection_completed_at": completed,
                            "provider": cap_status.get("provider") or capability_provider(capability_id),
                            "series_or_capability": capability_id,
                            "status": cap_status["status"],
                            "snapshot_ref": None,
                            "warm_destination_refs": [],
                            "error_class": None,
                            "provider_timestamp_at": None,
                            "known_at": completed,
                            "retrieved_at": completed,
                            "freshness": {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": None},
                            "gap_semantics": cap_status["status"],
                            "d8_cycle_id": cycle["cycle_id"],
                            "d8_attempt": attempt,
                            "d8_source_revision": cycle["source_revision"],
                            "d8_runtime_revision": cycle["runtime_revision"],
                            "synthetic_fill": False,
                        }
                    )
        grouped: dict[Path, list[dict[str, Any]]] = defaultdict(list)
        for run in materialized:
            path = self.warm_root / "collection-runs" / _day_path(run["expected_schedule_at"]) / "runs.json"
            grouped[path].append(run)
        evidence: list[dict[str, Any]] = []
        for path in sorted(grouped, key=lambda value: value.as_posix()):
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
            evidence.append(partition_descriptor(path, records_field="runs", key=_run_key))
        return evidence

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
        if pending:
            return super().forward_pending(limit=limit, now_ms=now_ms, failpoint=failpoint)
        run_evidence = self._materialize_gap_only_runs()
        return {
            "schema_version": FORWARD_CONTRACT_VERSION,
            "batch_id": None,
            "accepted_observation_ids": [],
            "already_present_observation_ids": [],
            "rejected_observations": [],
            "warm_destination_evidence": [],
            "collection_run_evidence": run_evidence,
            "durable_commit_status": "COMMITTED" if run_evidence else "NOOP",
            "read_back_integrity": "PASS",
            "ack_state": "NOOP",
            "source_cursor": self._source_cursor([]),
            "provider_reacquisition_count": 0,
        }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Integrity-bound internal D8 spool → D9 WARM one-shot forwarder")
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
