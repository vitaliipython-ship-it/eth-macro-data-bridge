"""Pure isolated F5 readiness predicates; never runs real-server readiness."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import shutil
import sqlite3
import stat
from pathlib import Path
from typing import Callable
from uuid import uuid4

from server.configuration.models import F5ReadinessConfig
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem


class ControlBackendUnavailable(RuntimeError):
    """Control backend cannot be opened for the bounded readiness predicate."""


class ControlSchemaIncompatible(RuntimeError):
    """Control schema does not match the implementation-bound identity."""


class ControlBackendCorrupt(RuntimeError):
    """Control backend integrity evidence is unusable."""


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """One explicit readiness predicate result."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Bounded conjunction of readiness predicates; not qualification evidence."""

    checks: tuple[ReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        """Return true only when every bounded predicate passes."""
        return all(check.passed for check in self.checks)


def _write_mode_present(path: Path) -> bool:
    """Check declared Unix write mode bits without attempting a real deployment mutation."""
    return bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def _run_storage_probe(root: Path) -> tuple[bool, str, bool]:
    """Use the F5 immutable storage seam for a dedicated non-domain readiness probe."""
    probe_identity = "readiness:f5:v1:" + uuid4().hex
    payload = ("aife-f5-readiness-probe-v1:" + probe_identity).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    store = QualifiedDataRootImmutableFilesystem.for_readiness_probe(root, probe_identity)
    passed = False
    detail = "probe_not_executed"
    cleanup_passed = False
    try:
        write_evidence = store.write_immutable(payload, expected_digest=digest)
        readback_evidence = store.readback_verify(digest, expected_size=len(payload))
        observed = store.read_exact(digest)
        passed = (
            write_evidence.content_digest == digest
            and readback_evidence.content_digest == digest
            and readback_evidence.size == len(payload)
            and hashlib.sha256(observed).hexdigest() == digest
            and observed == payload
        )
        detail = "same-f5-storage-port+independent-readback+sha256"
    except (OSError, RuntimeError, ValueError) as exc:
        detail = type(exc).__name__
    finally:
        try:
            store.cleanup_readiness_probe(digest)
            cleanup_passed = not (root / ".aife-readiness").exists()
        except (OSError, RuntimeError, ValueError):
            cleanup_passed = False
    return passed, detail, cleanup_passed


def evaluate_f5_readiness(config: F5ReadinessConfig, *, control_schema_check: Callable[[], None]) -> ReadinessReport:
    """Evaluate future F5 readiness predicates only against the supplied isolated fixture."""
    checks: list[ReadinessCheck] = []
    try:
        mapping = json.loads(config.deployment_map_path.read_text(encoding="utf-8"))
        checks.append(ReadinessCheck("deployment_map_readable", True, "ok"))
    except (OSError, json.JSONDecodeError) as exc:
        return ReadinessReport((ReadinessCheck("deployment_map_readable", False, type(exc).__name__),))

    for name, key, expected in (
        ("active_release_identity", "active_release_identity", config.expected_release_identity),
        ("config_identity", "config_identity", config.expected_config_identity),
        ("control_schema_id", "control_schema_id", config.expected_control_schema_id),
        (
            "control_schema_version",
            "control_schema_version",
            config.expected_control_schema_version,
        ),
    ):
        checks.append(ReadinessCheck(name, mapping.get(key) == expected, f"actual={mapping.get(key)!r}"))
    if config.expected_backing_identity is not None:
        checks.append(
            ReadinessCheck(
                "backing_identity",
                mapping.get("backing_identity") == config.expected_backing_identity,
                f"actual={mapping.get('backing_identity')!r}",
            )
        )

    try:
        control_schema_check()
        checks.append(ReadinessCheck("control_backend_openable_and_compatible", True, "ok"))
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        checks.append(ReadinessCheck("control_backend_openable_and_compatible", False, type(exc).__name__))

    root = Path(mapping.get("data_root", ""))
    if not root.is_dir():
        checks.append(ReadinessCheck("data_root_present", False, str(root)))
        return ReadinessReport(tuple(checks))
    checks.append(ReadinessCheck("data_root_present", True, str(root)))

    writable = _write_mode_present(root)
    checks.append(ReadinessCheck("data_root_writable", writable, "mode-bits"))
    free = shutil.disk_usage(root).free
    space_ok = free >= config.minimum_free_bytes
    checks.append(ReadinessCheck("free_space_preflight", space_ok, f"free={free}"))

    if writable and space_ok:
        probe_ok, probe_detail, cleanup_ok = _run_storage_probe(root)
        checks.append(ReadinessCheck("durable_write_readback_probe", probe_ok, probe_detail))
        checks.append(ReadinessCheck("readiness_probe_cleanup_bounded", cleanup_ok, "non-domain-only"))
    return ReadinessReport(tuple(checks))
