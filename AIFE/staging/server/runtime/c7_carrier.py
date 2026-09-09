"""Thin provider-neutral executable carrier for F5C C7 Docker qualification only."""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import hashlib
import json
import signal
import sqlite3
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.acquisition.ports import AcquiredArtifact
from server.acquisition.service import (
    DurableAcquisitionAcceptance,
    GenericAcquisitionService,
)
from server.integration.domain import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem

DEFAULT_DATA_ROOT = Path("/var/lib/aife/data")
DEFAULT_CONTROL_DB = Path("/var/lib/aife/control/aife-control.sqlite3")
INPUT_SCHEMA = "aife-f5c-c7-input/1.0.0"


class C7CarrierError(RuntimeError):
    """Qualification carrier input or durable-readback invariant failed."""


@dataclass(frozen=True, slots=True)
class _StaticQualificationAdapter:
    """Return one already supplied neutral qualification artifact."""

    artifact: AcquiredArtifact

    async def acquire(self) -> AcquiredArtifact:
        return self.artifact


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _emit(value: dict[str, Any]) -> None:
    sys.stdout.write(_canonical_json(value) + "\n")
    sys.stdout.flush()


def _parse_time(value: str, field: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise C7CarrierError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise C7CarrierError(f"{field} must be timezone-aware")
    return parsed


def _require_text(raw: dict[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise C7CarrierError(f"{field} must be a non-empty string")
    return value


def _load_input(path: Path) -> AcquiredArtifact:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise C7CarrierError("qualification input is unreadable") from exc
    if not isinstance(raw, dict):
        raise C7CarrierError("qualification input must be a JSON object")

    allowed = {
        "schema_version",
        "artifact_identity",
        "artifact_type",
        "source_revision",
        "payload_base64",
        "content_identity_sha256",
        "payload_reference",
        "provenance_reference",
        "acceptance_evidence_reference",
        "validated_at",
        "produced_at",
        "observed_at",
    }
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise C7CarrierError(f"unexpected qualification input fields: {unexpected}")

    if raw.get("schema_version") != INPUT_SCHEMA:
        raise C7CarrierError("unsupported qualification input schema")

    try:
        payload = base64.b64decode(
            _require_text(raw, "payload_base64"),
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise C7CarrierError("payload_base64 is invalid") from exc

    declared_digest = _require_text(raw, "content_identity_sha256").lower()
    observed_digest = hashlib.sha256(payload).hexdigest()
    if declared_digest != observed_digest:
        raise C7CarrierError(
            "decoded payload SHA-256 differs from declared content identity"
        )

    observed_at_raw = raw.get("observed_at")
    if observed_at_raw is not None and not isinstance(observed_at_raw, str):
        raise C7CarrierError("observed_at must be a string or null")

    envelope = DomainArtifactEnvelope(
        DomainArtifactIdentity(_require_text(raw, "artifact_identity")),
        DomainArtifactType(_require_text(raw, "artifact_type")),
        _require_text(raw, "source_revision"),
        declared_digest,
        DomainArtifactReferences(
            _require_text(raw, "payload_reference"),
            _require_text(raw, "provenance_reference"),
            _require_text(raw, "acceptance_evidence_reference"),
        ),
        DomainArtifactTiming(
            _parse_time(_require_text(raw, "validated_at"), "validated_at"),
            _parse_time(_require_text(raw, "produced_at"), "produced_at"),
            None
            if observed_at_raw is None
            else _parse_time(observed_at_raw, "observed_at"),
        ),
    )
    return AcquiredArtifact(envelope, payload)


def _open_runtime(
    data_root: Path,
    control_db: Path,
) -> tuple[QualifiedDataRootImmutableFilesystem, SQLiteServerControlRepository]:
    data_root.mkdir(parents=True, exist_ok=True)
    control_db.parent.mkdir(parents=True, exist_ok=True)
    if not data_root.is_dir():
        raise C7CarrierError("data root is not a directory")
    if not control_db.parent.is_dir():
        raise C7CarrierError("control DB parent is not a directory")
    store = QualifiedDataRootImmutableFilesystem(data_root)
    repository = SQLiteServerControlRepository(control_db)
    return store, repository


def _work_json(work: Any) -> dict[str, Any]:
    return {
        "work_id": work.work_id,
        "work_kind": work.work_kind,
        "logical_input_identity": work.logical_input_identity,
        "scheduling_slot_identity": work.scheduling_slot_identity,
        "payload_reference": work.payload_reference,
        "work_payload_reference": work.payload_reference,
        "provenance_reference": work.provenance_reference,
        "policy_revision_identity": work.policy_revision_identity,
        "immutable_input_digest": work.immutable_input_digest,
        "state": work.state,
        "record_version": work.record_version,
    }


def _cmd_serve(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root)
    control_db = Path(args.control_db)
    _open_runtime(data_root, control_db)

    stop = threading.Event()

    def _handle_signal(_signum: int, _frame: Any) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    startup = {
        "command": "serve",
        "control_db": control_db.as_posix(),
        "data_root": data_root.as_posix(),
        "network_listener": False,
        "production_activation": False,
        "qualification_profile": "C7",
        "scheduler": False,
        "status": "PASS",
    }
    _emit(startup)
    stop.wait()
    return {}


def _cmd_readiness(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root)
    control_db = Path(args.control_db)
    _, repository = _open_runtime(data_root, control_db)
    del repository

    probe_identity = f"readiness:f5:v1:c7:{uuid4().hex}"
    probe_payload = ("aife-f5c-c7-readiness:" + probe_identity).encode("utf-8")
    digest = hashlib.sha256(probe_payload).hexdigest()
    probe = QualifiedDataRootImmutableFilesystem.for_readiness_probe(
        data_root,
        probe_identity,
    )
    written = probe.write_immutable(probe_payload, expected_digest=digest)
    verified = probe.readback_verify(digest, expected_size=len(probe_payload))
    observed = probe.read_exact(digest)
    if written != verified or observed != probe_payload:
        raise C7CarrierError("immutable readiness probe readback mismatch")
    probe.cleanup_readiness_probe(digest)

    # A fresh SQLite connection verifies that the durable file can be reopened.
    with sqlite3.connect(control_db) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if integrity.lower() != "ok" or version != 1:
        raise C7CarrierError("control DB readiness validation failed")

    return {
        "command": "readiness",
        "control_db": control_db.as_posix(),
        "control_schema_version": version,
        "data_root": data_root.as_posix(),
        "immutable_storage_probe": "PASS",
        "qualification_readiness": "PASS",
        "status": "PASS",
    }


def _cmd_run_once(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root)
    control_db = Path(args.control_db)
    artifact = _load_input(Path(args.input))
    store, repository = _open_runtime(data_root, control_db)
    acceptance = DurableAcquisitionAcceptance(
        store,
        repository,
        policy_revision_identity=args.policy_revision,
        scheduling_slot_identity=args.scheduling_slot,
    )
    service = GenericAcquisitionService(
        _StaticQualificationAdapter(artifact),
        acceptance,
    )
    accepted = asyncio.run(
        service.acquire_durable(at=_parse_time(args.at, "at"))
    )

    observed = store.read_exact(accepted.object_evidence.content_digest)
    observed_digest = hashlib.sha256(observed).hexdigest()
    if observed_digest != artifact.envelope.content_identity:
        raise C7CarrierError("post-acceptance exact-byte readback mismatch")

    return {
        "artifact_identity": artifact.envelope.artifact_identity.value,
        "artifact_type": artifact.envelope.artifact_type.value,
        "command": "run-once",
        "content_identity": artifact.envelope.content_identity,
        "object_digest": accepted.object_evidence.content_digest,
        "object_locator": accepted.object_evidence.physical_locator,
        "object_size": accepted.object_evidence.size,
        "payload_base64": base64.b64encode(observed).decode("ascii"),
        "source_revision": artifact.envelope.source_revision,
        "status": "PASS",
        **_work_json(accepted.work),
    }


def _cmd_readback(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root)
    control_db = Path(args.control_db)
    expected = args.expected_content_identity.lower()
    store, repository = _open_runtime(data_root, control_db)
    work = repository.get_work(args.work_id)
    if work is None:
        raise C7CarrierError("requested Work does not exist")

    expected_locator = store.locator(expected).relative_to(data_root).as_posix()
    if work.payload_reference != expected_locator:
        raise C7CarrierError(
            "Work payload_reference does not match expected immutable object locator"
        )

    payload = store.read_exact(expected)
    observed = hashlib.sha256(payload).hexdigest()
    if observed != expected:
        raise C7CarrierError("independent object SHA-256 mismatch")
    evidence = store.readback_verify(expected, expected_size=len(payload))
    if evidence.physical_locator != work.payload_reference:
        raise C7CarrierError("independent object locator differs from Work reference")

    return {
        "command": "readback",
        "content_identity": expected,
        "object_digest": evidence.content_digest,
        "object_locator": evidence.physical_locator,
        "object_size": evidence.size,
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "status": "PASS",
        **_work_json(work),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bounded F5C C7 qualification carrier"
    )
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT.as_posix())
    parser.add_argument("--control-db", default=DEFAULT_CONTROL_DB.as_posix())
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("serve")
    subparsers.add_parser("readiness")

    run_once = subparsers.add_parser("run-once")
    run_once.add_argument("--input", required=True)
    run_once.add_argument("--policy-revision", required=True)
    run_once.add_argument("--scheduling-slot", required=True)
    run_once.add_argument("--at", required=True)

    readback = subparsers.add_parser("readback")
    readback.add_argument("--work-id", required=True)
    readback.add_argument("--expected-content-identity", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "serve":
            _cmd_serve(args)
            return 0
        if args.command == "readiness":
            result = _cmd_readiness(args)
        elif args.command == "run-once":
            result = _cmd_run_once(args)
        elif args.command == "readback":
            result = _cmd_readback(args)
        else:
            raise C7CarrierError(f"unsupported command: {args.command}")
        _emit(result)
        return 0
    except Exception as exc:  # fail closed at the executable qualification boundary
        _emit(
            {
                "command": args.command,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "status": "FAIL",
            }
        )
        print(
            f"C7_CARRIER_FAILURE={type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
