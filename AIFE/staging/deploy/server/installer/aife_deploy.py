#!/usr/bin/python3 -I
"""Narrow root-owned AIFE host deployment executor.

The executor is a privileged filesystem adapter, never owner/domain authority.  It
accepts only fixed-schema deployment identities, copies unprivileged staging bytes
into root-private storage before verification, and delegates release/map/receipt/
activation semantics to the root-owned trusted copy of server.runtime.deployment.
Candidate release code is never imported or executed as root.
"""
from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import importlib.util
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Mapping, Sequence

EXECUTOR_VERSION = "aife-privileged-deployment-executor/1.0.0"
REQUEST_SCHEMA = "aife-privileged-deployment-request/1.0.0"
VALIDATION_SCHEMA = "aife-pre-activation-validation/1.0.0"
REQUIRED_PRE_ACTIVATION_CHECKS = (
    "exact_release_readback",
    "config_identity",
    "control_backend_compatibility",
    "control_schema_compatibility",
    "persistent_root_backing_binding",
    "mount_space_permission_preflight",
    "pre_activation_health_readiness",
    "applicable_write_readback",
)
POLICY_SCHEMA = "aife-deployment-executor-policy/1.0.0"
TRUSTED_CORE_SHA256 = "9f90586d99ed22891b1d48152e9eccbdb18fba88452289ac8c872b99c639c007"

EXECUTOR_PATH = Path("/usr/local/sbin/aife-deploy")
TRUSTED_CORE_PATH = Path("/usr/local/lib/aife-deploy/deployment.py")
POLICY_PATH = Path("/etc/aife/deployment-executor-policy.json")
SUDOERS_PATH = Path("/etc/sudoers.d/aife-deploy")
STAGING_ROOT = Path("/var/tmp/aife-deploy")
LOCK_PATH = Path("/run/lock/aife-deploy.lock")

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PATH_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ExecutorError(RuntimeError):
    """Fail-closed privileged executor error."""


@dataclass(frozen=True, slots=True)
class HostLayout:
    install_root: Path
    release_root: Path
    current_pointer: Path
    previous_pointer: Path
    config_root: Path
    deployment_map: Path
    state_root: Path
    data_root: Path
    control_root: Path
    control_db: Path
    deployments_root: Path
    receipt_root: Path
    staging_root: Path
    lock_path: Path


CANONICAL_LAYOUT = HostLayout(
    install_root=Path("/opt/aife"),
    release_root=Path("/opt/aife/releases"),
    current_pointer=Path("/opt/aife/current"),
    previous_pointer=Path("/opt/aife/previous"),
    config_root=Path("/etc/aife"),
    deployment_map=Path("/etc/aife/deployment-map.json"),
    state_root=Path("/var/lib/aife"),
    data_root=Path("/var/lib/aife/data"),
    control_root=Path("/var/lib/aife/control"),
    control_db=Path("/var/lib/aife/control/aife-control.sqlite3"),
    deployments_root=Path("/var/lib/aife/deployments"),
    receipt_root=Path("/var/lib/aife/deployments/receipts"),
    staging_root=STAGING_ROOT,
    lock_path=LOCK_PATH,
)


@dataclass(frozen=True, slots=True)
class ExecutorPolicy:
    deployment_caller: str
    service_account: str
    service_group: str
    service_uid: int
    service_gid: int


@dataclass(frozen=True, slots=True)
class DeploymentRequest:
    intent: str
    deployment_id: str
    receipt_id: str
    release_id: str
    source_head: str
    source_tree: str
    bundle_sha256: str | None
    release_digest: str
    release_manifest_id: str
    config_identity: str
    control_backend_identity: str
    control_schema_identity: str
    backing_identity: str


@dataclass(frozen=True, slots=True)
class ValidationEvidence:
    deployment_id: str
    release_id: str
    source_head: str
    source_tree: str
    checks: Mapping[str, str]


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_path_token(value: object, field: str) -> str:
    if not isinstance(value, str) or not _PATH_TOKEN.fullmatch(value) or ".." in value:
        raise ExecutorError(f"invalid {field}")
    return value


def _safe_token(value: object, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ExecutorError(f"invalid {field}")
    return value


def _hex(value: object, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ExecutorError(f"invalid {field}")
    return value


def parse_request(raw: Mapping[str, object]) -> DeploymentRequest:
    allowed = {
        "schema_version",
        "intent",
        "deployment_id",
        "receipt_id",
        "release_id",
        "source_head",
        "source_tree",
        "bundle_sha256",
        "release_digest",
        "release_manifest_id",
        "config_identity",
        "control_backend_identity",
        "control_schema_identity",
        "backing_identity",
    }
    if set(raw) != allowed:
        raise ExecutorError("request fields")
    if raw.get("schema_version") != REQUEST_SCHEMA:
        raise ExecutorError("request schema")
    intent = raw.get("intent")
    if intent not in {"install", "upgrade", "rollback"}:
        raise ExecutorError("intent")
    bundle = raw.get("bundle_sha256")
    if intent in {"install", "upgrade"}:
        bundle_sha256: str | None = _hex(bundle, "bundle_sha256", _HEX64)
    elif bundle is not None:
        raise ExecutorError("rollback bundle forbidden")
    else:
        bundle_sha256 = None
    return DeploymentRequest(
        intent=str(intent),
        deployment_id=_safe_path_token(raw.get("deployment_id"), "deployment_id"),
        receipt_id=_safe_path_token(raw.get("receipt_id"), "receipt_id"),
        release_id=_safe_path_token(raw.get("release_id"), "release_id"),
        source_head=_hex(raw.get("source_head"), "source_head", _HEX40),
        source_tree=_hex(raw.get("source_tree"), "source_tree", _HEX40),
        bundle_sha256=bundle_sha256,
        release_digest=_hex(raw.get("release_digest"), "release_digest", _HEX64),
        release_manifest_id=_hex(raw.get("release_manifest_id"), "release_manifest_id", _HEX64),
        config_identity=_safe_token(raw.get("config_identity"), "config_identity"),
        control_backend_identity=_safe_token(raw.get("control_backend_identity"), "control_backend_identity"),
        control_schema_identity=_safe_token(raw.get("control_schema_identity"), "control_schema_identity"),
        backing_identity=_safe_token(raw.get("backing_identity"), "backing_identity"),
    )


def parse_validation(raw: Mapping[str, object]) -> ValidationEvidence:
    allowed = {"schema_version", "deployment_id", "release_id", "source_head", "source_tree", "status", "checks"}
    if set(raw) != allowed or raw.get("schema_version") != VALIDATION_SCHEMA or raw.get("status") != "PASS":
        raise ExecutorError("validation schema/status")
    checks = raw.get("checks")
    if not isinstance(checks, dict) or not checks:
        raise ExecutorError("validation checks")
    normalized: dict[str, str] = {}
    for key, value in checks.items():
        normalized[_safe_token(key, "validation check")] = _safe_token(value, "validation result")
    missing = set(REQUIRED_PRE_ACTIVATION_CHECKS).difference(normalized)
    if missing:
        raise ExecutorError("validation required checks missing")
    if any(value != "PASS" for value in normalized.values()):
        raise ExecutorError("validation not pass")
    return ValidationEvidence(
        deployment_id=_safe_path_token(raw.get("deployment_id"), "deployment_id"),
        release_id=_safe_path_token(raw.get("release_id"), "release_id"),
        source_head=_hex(raw.get("source_head"), "source_head", _HEX40),
        source_tree=_hex(raw.get("source_tree"), "source_tree", _HEX40),
        checks=normalized,
    )


def parse_policy(raw: Mapping[str, object]) -> ExecutorPolicy:
    allowed = {"schema_version", "deployment_caller", "service_account", "service_group", "service_uid", "service_gid"}
    if set(raw) != allowed or raw.get("schema_version") != POLICY_SCHEMA:
        raise ExecutorError("policy schema")
    caller = _safe_token(raw.get("deployment_caller"), "deployment_caller")
    account = _safe_token(raw.get("service_account"), "service_account")
    group = _safe_token(raw.get("service_group"), "service_group")
    uid = raw.get("service_uid")
    gid = raw.get("service_gid")
    if not isinstance(uid, int) or not isinstance(gid, int) or uid <= 0 or gid <= 0:
        raise ExecutorError("service uid/gid")
    return ExecutorPolicy(caller, account, group, uid, gid)


def _trusted_regular_file(path: Path, *, expected_uid: int = 0) -> os.stat_result:
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or path.is_symlink():
        raise ExecutorError(f"trusted file type: {path}")
    if st.st_uid != expected_uid or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ExecutorError(f"trusted file ownership/mode: {path}")
    return st


def load_policy(path: Path = POLICY_PATH, *, enforce_root_trust: bool = True) -> ExecutorPolicy:
    if enforce_root_trust:
        _trusted_regular_file(path)
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError("policy unreadable") from exc
    if not isinstance(raw, dict):
        raise ExecutorError("policy object")
    return parse_policy(raw)


def load_deployment_core(
    path: Path = TRUSTED_CORE_PATH,
    *,
    expected_sha256: str = TRUSTED_CORE_SHA256,
    enforce_root_trust: bool = True,
) -> ModuleType:
    if enforce_root_trust:
        _trusted_regular_file(path)
    if _sha256_path(path) != expected_sha256:
        raise ExecutorError("trusted deployment core digest")
    spec = importlib.util.spec_from_file_location("aife_trusted_deployment_core", path)
    if spec is None or spec.loader is None:
        raise ExecutorError("trusted deployment core loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _open_staged_fd(staging_root: Path, request_id: str, filename: str) -> int:
    request_id = _safe_path_token(request_id, "request_id")
    root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open(staging_root, root_flags)
    try:
        request_fd = os.open(request_id, root_flags, dir_fd=root_fd)
    finally:
        os.close(root_fd)
    try:
        fd = os.open(filename, file_flags, dir_fd=request_fd)
    finally:
        os.close(request_fd)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        os.close(fd)
        raise ExecutorError("staging file type/link count")
    return fd


def _copy_verified_staged_file(
    staging_root: Path,
    request_id: str,
    filename: str,
    expected_sha256: str,
    private_root: Path,
) -> Path:
    _hex(expected_sha256, f"{filename} sha256", _HEX64)
    fd = _open_staged_fd(staging_root, request_id, filename)
    target = private_root / filename
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, "rb", closefd=True) as source, target.open("xb") as destination:
            os.chmod(target, 0o600)
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                h.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if h.hexdigest() != expected_sha256:
        target.unlink(missing_ok=True)
        raise ExecutorError(f"{filename} digest mismatch")
    return target


def _load_request_private(path: Path) -> DeploymentRequest:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError("request unreadable") from exc
    if not isinstance(raw, dict):
        raise ExecutorError("request object")
    return parse_request(raw)


def _load_validation_private(path: Path, request: DeploymentRequest) -> ValidationEvidence:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError("validation unreadable") from exc
    if not isinstance(raw, dict):
        raise ExecutorError("validation object")
    evidence = parse_validation(raw)
    expected = (request.deployment_id, request.release_id, request.source_head, request.source_tree)
    observed = (evidence.deployment_id, evidence.release_id, evidence.source_head, evidence.source_tree)
    if observed != expected:
        raise ExecutorError("validation identity mismatch")
    return evidence


def _sanitize_environment() -> None:
    for name in tuple(os.environ):
        if name.startswith(("GIT_", "PYTHON")) and name not in {"GIT_TERMINAL_PROMPT"}:
            os.environ.pop(name, None)
    os.environ.update(
        {
            "PATH": "/usr/bin:/bin",
            "HOME": "/nonexistent",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if completed.returncode:
        raise ExecutorError("git operation failed")
    return completed.stdout.strip()


def _private_git_repo(bundle: Path, expected_head: str, expected_tree: str, private_root: Path) -> Path:
    repo = private_root / "source.git"
    completed = subprocess.run(
        ["git", "clone", "--bare", "--no-local", os.fspath(bundle), os.fspath(repo)],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    if completed.returncode:
        raise ExecutorError("git bundle clone failed")
    _git(repo, "update-ref", "refs/heads/aife-deploy", expected_head)
    _git(repo, "symbolic-ref", "HEAD", "refs/heads/aife-deploy")
    if _git(repo, "rev-parse", "HEAD") != expected_head or _git(repo, "rev-parse", "HEAD^{tree}") != expected_tree:
        raise ExecutorError("git source identity mismatch")
    return repo


def _service_identity(policy: ExecutorPolicy) -> tuple[pwd.struct_passwd, grp.struct_group]:
    try:
        account = pwd.getpwnam(policy.service_account)
        group = grp.getgrnam(policy.service_group)
    except KeyError as exc:
        raise ExecutorError("service identity missing") from exc
    if account.pw_uid != policy.service_uid or account.pw_gid != policy.service_gid or group.gr_gid != policy.service_gid:
        raise ExecutorError("service identity mismatch")
    if not account.pw_shell.endswith("nologin") or account.pw_dir not in {"/nonexistent", "/var/empty"}:
        raise ExecutorError("service account must be non-login without interactive home")
    return account, group


def _expect_dir(path: Path, uid: int, gid: int, mode: int) -> None:
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or path.is_symlink():
        raise ExecutorError(f"directory type: {path}")
    if (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) != (uid, gid, mode):
        raise ExecutorError(f"directory ownership/mode: {path}")


def preflight(
    layout: HostLayout,
    policy: ExecutorPolicy,
    *,
    executor_path: Path = EXECUTOR_PATH,
    core_path: Path = TRUSTED_CORE_PATH,
    enforce_root_trust: bool = True,
) -> Mapping[str, object]:
    if enforce_root_trust:
        if os.geteuid() != 0:
            raise ExecutorError("executor must run as root")
        _trusted_regular_file(executor_path)
        _trusted_regular_file(core_path)
        if _sha256_path(core_path) != TRUSTED_CORE_SHA256:
            raise ExecutorError("trusted deployment core digest")
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user != policy.deployment_caller:
            raise ExecutorError("deployment caller mismatch")
    account, group = _service_identity(policy)
    _expect_dir(layout.install_root, 0, 0, 0o755)
    _expect_dir(layout.release_root, 0, 0, 0o755)
    _expect_dir(layout.config_root, 0, group.gr_gid, 0o750)
    _expect_dir(layout.state_root, 0, group.gr_gid, 0o750)
    _expect_dir(layout.deployments_root, 0, group.gr_gid, 0o750)
    _expect_dir(layout.receipt_root, 0, group.gr_gid, 0o750)
    _expect_dir(layout.control_root, account.pw_uid, group.gr_gid, 0o750)
    _expect_dir(layout.data_root, account.pw_uid, group.gr_gid, 0o750)
    return {
        "status": "PASS",
        "executor_version": EXECUTOR_VERSION,
        "deployment_caller": policy.deployment_caller,
        "runtime_service_account": policy.service_account,
        "runtime_service_uid": policy.service_uid,
        "runtime_service_gid": policy.service_gid,
        "canonical_install_root": os.fspath(layout.install_root),
        "canonical_data_root": os.fspath(layout.data_root),
        "canonical_control_db": os.fspath(layout.control_db),
        "general_root_shell": "NO",
        "semantic_authority": False,
    }


def _lock(layout: HostLayout) -> int:
    fd = os.open(layout.lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise ExecutorError("concurrent deployment") from exc
    return fd


def _persistent_roots(layout: HostLayout, request: DeploymentRequest) -> dict[str, str]:
    return {
        "backing_identity": request.backing_identity,
        "control_db_path": os.fspath(layout.control_db),
        "data_root": os.fspath(layout.data_root),
        "state_root": os.fspath(layout.state_root),
        "deployment_receipt_root": os.fspath(layout.receipt_root),
    }


def install_release(
    layout: HostLayout,
    policy: ExecutorPolicy,
    request_id: str,
    request_sha256: str,
    *,
    core: ModuleType,
) -> Mapping[str, object]:
    if os.geteuid() != 0:
        raise ExecutorError("root required")
    _service_identity(policy)
    lock_fd = _lock(layout)
    try:
        with tempfile.TemporaryDirectory(prefix="aife-deploy-root-") as tmp:
            private = Path(tmp)
            request_path = _copy_verified_staged_file(layout.staging_root, request_id, "request.json", request_sha256, private)
            request = _load_request_private(request_path)
            if request.intent == "rollback" or request.bundle_sha256 is None:
                raise ExecutorError("rollback cannot install")
            bundle = _copy_verified_staged_file(layout.staging_root, request_id, "source.bundle", request.bundle_sha256, private)
            repo = _private_git_repo(bundle, request.source_head, request.source_tree, private)
            verify_root = private / "verified-releases"
            verify_root.mkdir()
            verify_identity, verify_plan, verify_path = core.materialize_immutable_release(
                repo,
                expected_head=request.source_head,
                expected_tree=request.source_tree,
                release_root=verify_root,
                release_id=request.release_id,
            )
            if verify_plan.release_digest != request.release_digest or verify_plan.release_manifest_id != request.release_manifest_id:
                raise ExecutorError("release identity mismatch")
            core.verify_installed_release(verify_path, verify_plan.manifest)
            identity, plan, release_path = core.materialize_immutable_release(
                repo,
                expected_head=request.source_head,
                expected_tree=request.source_tree,
                release_root=layout.release_root,
                release_id=request.release_id,
            )
            if (plan.release_digest, plan.release_manifest_id) != (verify_plan.release_digest, verify_plan.release_manifest_id):
                raise ExecutorError("canonical release differs from verified plan")
            if (identity.head, identity.tree) != (verify_identity.head, verify_identity.tree):
                raise ExecutorError("materialized source identity mismatch")
            core.verify_installed_release(release_path, plan.manifest)
            return {
                "status": "PASS",
                "operation": "install",
                "release_id": plan.release_id,
                "release_path": os.fspath(release_path),
                "source_head": plan.source_head,
                "source_tree": plan.source_tree,
                "release_digest": plan.release_digest,
                "release_manifest_id": plan.release_manifest_id,
                "exact_byte_verification": "PASS",
                "immutable_release": "PASS",
                "release_controlled_root_execution": "NO",
            }
    finally:
        os.close(lock_fd)


def _plan_from_installed(core: ModuleType, release_path: Path, request: DeploymentRequest) -> object:
    try:
        manifest = json.loads((release_path / core.MANIFEST).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError("installed release manifest unavailable") from exc
    if not isinstance(manifest, dict):
        raise ExecutorError("installed release manifest object")
    core.verify_installed_release(release_path, manifest)
    expected = {
        "source_head": request.source_head,
        "source_tree": request.source_tree,
        "release_id": request.release_id,
        "release_digest": request.release_digest,
        "release_manifest_id": request.release_manifest_id,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ExecutorError("installed release/request mismatch")
    return core.ReleasePlan(
        request.source_head,
        request.source_tree,
        request.release_id,
        request.release_digest,
        request.release_manifest_id,
        tuple(),
        manifest,
    )


def _set_operator_readable(path: Path, policy: ExecutorPolicy, mode: int) -> None:
    os.chown(path, 0, policy.service_gid)
    os.chmod(path, mode)


def activate_release(
    layout: HostLayout,
    policy: ExecutorPolicy,
    request_id: str,
    request_sha256: str,
    validation_sha256: str,
    *,
    core: ModuleType,
) -> Mapping[str, object]:
    if os.geteuid() != 0:
        raise ExecutorError("root required")
    _service_identity(policy)
    lock_fd = _lock(layout)
    try:
        with tempfile.TemporaryDirectory(prefix="aife-deploy-root-") as tmp:
            private = Path(tmp)
            request_path = _copy_verified_staged_file(layout.staging_root, request_id, "request.json", request_sha256, private)
            validation_path = _copy_verified_staged_file(layout.staging_root, request_id, "validation.json", validation_sha256, private)
            request = _load_request_private(request_path)
            _load_validation_private(validation_path, request)
            release_path = layout.release_root / request.release_id
            if release_path.is_symlink() or not release_path.is_dir() or release_path.parent != layout.release_root:
                raise ExecutorError("candidate release path")
            plan = _plan_from_installed(core, release_path, request)
            receipt_path = layout.receipt_root / f"{request.deployment_id}.json"
            if layout.current_pointer.is_symlink() and layout.current_pointer.resolve() == release_path.resolve() and receipt_path.exists():
                receipt = core.readback_deployment_receipt(
                    receipt_path,
                    expected_deployment_id=request.deployment_id,
                    expected_receipt_id=request.receipt_id,
                )
                if receipt.get("release_manifest_id") != request.release_manifest_id or receipt.get("terminal_outcome") != "PASS":
                    raise ExecutorError("idempotent activation receipt mismatch")
                return {
                    "status": "PASS",
                    "operation": "activate",
                    "release_id": request.release_id,
                    "reconciled": True,
                    "current_release": request.release_id,
                    "receipt_path": os.fspath(receipt_path),
                }
            mapping, receipt, predecessor = core.execute_release_activation(
                plan=plan,
                release_path=release_path,
                deployment_map_path=layout.deployment_map,
                receipt_path=receipt_path,
                current_pointer=layout.current_pointer,
                previous_pointer=layout.previous_pointer,
                deployment_id=request.deployment_id,
                deployment_receipt_id=request.receipt_id,
                config_identity=request.config_identity,
                control_backend_identity=request.control_backend_identity,
                control_schema_identity=request.control_schema_identity,
                persistent_roots=_persistent_roots(layout, request),
                pre_activation_check=lambda observed: observed.get("release_manifest_id") == request.release_manifest_id,
                backing_default=request.backing_identity,
            )
            _set_operator_readable(layout.deployment_map, policy, 0o640)
            _set_operator_readable(receipt_path, policy, 0o640)
            if mapping.get("release_manifest_id") != request.release_manifest_id or receipt.get("terminal_outcome") != "PASS":
                raise ExecutorError("activation readback")
            return {
                "status": "PASS",
                "operation": "activate",
                "intent": request.intent,
                "release_id": request.release_id,
                "predecessor_release_id": predecessor,
                "current_release": request.release_id,
                "deployment_map": os.fspath(layout.deployment_map),
                "receipt_path": os.fspath(receipt_path),
                "validation_evidence_sha256": validation_sha256,
                "atomic_activation": "PASS",
                "receipt_readback": "PASS",
            }
    finally:
        os.close(lock_fd)


def _emit(value: Mapping[str, object]) -> None:
    sys.stdout.buffer.write(_json_bytes(value))


def _require_root() -> None:
    if os.geteuid() != 0:
        raise ExecutorError("root required")


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aife-deploy", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    install = sub.add_parser("install")
    install.add_argument("--request-id", required=True)
    install.add_argument("--request-sha256", required=True)
    activate = sub.add_parser("activate")
    activate.add_argument("--request-id", required=True)
    activate.add_argument("--request-sha256", required=True)
    activate.add_argument("--validation-sha256", required=True)
    args = parser.parse_args(argv)
    _sanitize_environment()
    _require_root()
    policy = load_policy()
    core = load_deployment_core()
    preflight(CANONICAL_LAYOUT, policy)
    if args.command == "preflight":
        _emit(preflight(CANONICAL_LAYOUT, policy))
    elif args.command == "install":
        _emit(install_release(CANONICAL_LAYOUT, policy, args.request_id, args.request_sha256, core=core))
    else:
        _emit(
            activate_release(
                CANONICAL_LAYOUT,
                policy,
                args.request_id,
                args.request_sha256,
                args.validation_sha256,
                core=core,
            )
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_cli())
    except ExecutorError as exc:
        sys.stderr.write(f"AIFE_DEPLOY_FAIL={exc}\n")
        raise SystemExit(2) from None
