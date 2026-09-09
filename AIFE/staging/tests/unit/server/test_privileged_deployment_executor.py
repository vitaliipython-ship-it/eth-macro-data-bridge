from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from deploy.server.installer import aife_deploy as executor


def request(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": executor.REQUEST_SCHEMA,
        "intent": "install",
        "deployment_id": "deploy-1",
        "receipt_id": "receipt-1",
        "release_id": "release-1",
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
        "bundle_sha256": "c" * 64,
        "release_digest": "d" * 64,
        "release_manifest_id": "e" * 64,
        "config_identity": "config:v1",
        "control_backend_identity": "sqlite:v1",
        "control_schema_identity": "aife-server-control",
        "backing_identity": "disk:v1",
    }
    value.update(changes)
    return value


def validation(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": executor.VALIDATION_SCHEMA,
        "deployment_id": "deploy-1",
        "release_id": "release-1",
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
        "status": "PASS",
        "checks": {"release_readback": "PASS", "runtime_precheck": "PASS"},
    }
    value.update(changes)
    return value


def test_valid_request_is_canonical_and_has_no_paths_or_privilege_fields() -> None:
    parsed = executor.parse_request(request())
    assert parsed.release_id == "release-1"
    assert parsed.intent == "install"
    assert not hasattr(parsed, "destination")
    assert not hasattr(parsed, "uid")
    assert not hasattr(parsed, "mode")


@pytest.mark.parametrize(
    "extra",
    [
        {"destination": "/etc/passwd"},
        {"root": "/"},
        {"command": "bash"},
        {"hook": "post-install"},
        {"uid": 0},
        {"gid": 0},
        {"mode": "0777"},
        {"secret": "do-not-log"},
    ],
)
def test_arbitrary_privilege_and_command_fields_are_rejected(extra: dict[str, object]) -> None:
    with pytest.raises(executor.ExecutorError, match="request fields"):
        executor.parse_request(request(**extra))


@pytest.mark.parametrize("field", ["deployment_id", "receipt_id", "release_id"])
def test_path_traversal_rejected(field: str) -> None:
    with pytest.raises(executor.ExecutorError):
        executor.parse_request(request(**{field: "../escape"}))


def test_rollback_forbids_bundle_input() -> None:
    with pytest.raises(executor.ExecutorError, match="rollback bundle"):
        executor.parse_request(request(intent="rollback"))
    parsed = executor.parse_request(request(intent="rollback", bundle_sha256=None))
    assert parsed.intent == "rollback"


def test_validation_requires_exact_pass_only_schema() -> None:
    parsed = executor.parse_validation(validation())
    assert set(parsed.checks.values()) == {"PASS"}
    with pytest.raises(executor.ExecutorError):
        executor.parse_validation(validation(status="FAIL"))
    with pytest.raises(executor.ExecutorError):
        executor.parse_validation(validation(checks={"release_readback": "FAIL"}))
    with pytest.raises(executor.ExecutorError):
        executor.parse_validation({**validation(), "detail": "secret-ish free text"})


def test_symlink_staging_file_rejected(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    request_dir = staging / "deploy-1"
    request_dir.mkdir(parents=True)
    target = tmp_path / "target"
    target.write_text("payload")
    (request_dir / "request.json").symlink_to(target)
    with pytest.raises(OSError):
        executor._open_staged_fd(staging, "deploy-1", "request.json")


def test_hardlink_staging_file_rejected(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    request_dir = staging / "deploy-1"
    request_dir.mkdir(parents=True)
    source = request_dir / "request.json"
    source.write_text("payload")
    os.link(source, request_dir / "second-link")
    with pytest.raises(executor.ExecutorError, match="link count"):
        executor._open_staged_fd(staging, "deploy-1", "request.json")


def test_root_private_copy_verifies_digest_and_rejects_mismatch(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    request_dir = staging / "deploy-1"
    request_dir.mkdir(parents=True)
    source = request_dir / "request.json"
    source.write_bytes(b"exact bytes\n")
    private = tmp_path / "private"
    private.mkdir()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    copied = executor._copy_verified_staged_file(staging, "deploy-1", "request.json", digest, private)
    assert copied.read_bytes() == source.read_bytes()
    copied.unlink()
    with pytest.raises(executor.ExecutorError, match="digest mismatch"):
        executor._copy_verified_staged_file(staging, "deploy-1", "request.json", "0" * 64, private)


def test_policy_rejects_arbitrary_fields_and_zero_uid_gid() -> None:
    good = {
        "schema_version": executor.POLICY_SCHEMA,
        "deployment_caller": "labadmin",
        "service_account": "aife",
        "service_group": "aife",
        "service_uid": 10001,
        "service_gid": 10001,
    }
    assert executor.parse_policy(good).service_uid == 10001
    with pytest.raises(executor.ExecutorError):
        executor.parse_policy({**good, "root": "/"})
    with pytest.raises(executor.ExecutorError):
        executor.parse_policy({**good, "service_uid": 0})


def test_sudoers_template_is_exact_executor_only() -> None:
    template = Path("deploy/server/installer/sudoers.aife-deploy.template").read_text()
    assert "/usr/local/sbin/aife-deploy" in template
    assert "sha256:@EXECUTOR_SHA256@" in template
    assert "NOPASSWD: ALL" not in template
    assert "/bin/bash" not in template
    assert "/bin/sh" not in template
    assert "/usr/bin/python" not in template


def test_executor_has_no_shell_execution_or_release_hook_surface() -> None:
    source = Path("deploy/server/installer/aife_deploy.py").read_text()
    assert "shell=True" not in source
    assert "post-install" not in source
    assert "source release" not in source.lower()
    assert "exec(" not in source
    assert "eval(" not in source
    assert "subprocess.run(" in source


def test_validation_json_has_no_freeform_secret_field() -> None:
    raw = validation()
    encoded = json.dumps(raw, sort_keys=True)
    assert "password" not in encoded.lower()
    assert "token" not in encoded.lower()
    assert "secret" not in encoded.lower()


def test_executor_pins_exact_reusable_deployment_core_bytes() -> None:
    core = Path("server/runtime/deployment.py")
    assert hashlib.sha256(core.read_bytes()).hexdigest() == executor.TRUSTED_CORE_SHA256
