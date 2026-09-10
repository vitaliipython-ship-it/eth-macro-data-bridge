from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy.server.installer import aife_deploy as executor
from server.runtime import deployment


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _fixture_repo(tmp_path: Path, value: str = "v1") -> tuple[Path, str, str]:
    repo = tmp_path / f"repo-{value}"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "executor@example.invalid")
    _git(repo, "config", "user.name", "Executor Fixture")
    source = repo / "AIFE" / "staging" / "server" / "fixture.py"
    source.parent.mkdir(parents=True)
    source.write_text(f"VALUE = {value!r}\n")
    hook = repo / "AIFE" / "staging" / "deploy" / "server" / "installer" / "post-install"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\nexit 99\n")
    os.chmod(hook, 0o755)
    _git(repo, "add", "AIFE/staging")
    _git(repo, "commit", "-q", "-m", f"fixture {value}")
    return repo, _git(repo, "rev-parse", "HEAD"), _git(repo, "rev-parse", "HEAD^{tree}")


def _layout(tmp_path: Path) -> executor.HostLayout:
    install = tmp_path / "opt" / "aife"
    config = tmp_path / "etc" / "aife"
    state = tmp_path / "var" / "lib" / "aife"
    layout = executor.HostLayout(
        install_root=install,
        release_root=install / "releases",
        current_pointer=install / "current",
        previous_pointer=install / "previous",
        config_root=config,
        deployment_map=config / "deployment-map.json",
        state_root=state,
        data_root=state / "data",
        control_root=state / "control",
        control_db=state / "control" / "aife-control.sqlite3",
        deployments_root=state / "deployments",
        receipt_root=state / "deployments" / "receipts",
        staging_root=tmp_path / "staging",
        lock_path=tmp_path / "aife-deploy.lock",
    )
    for path in (
        layout.release_root,
        layout.config_root,
        layout.data_root,
        layout.control_root,
        layout.receipt_root,
        layout.staging_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return layout


def _policy() -> executor.ExecutorPolicy:
    return executor.ExecutorPolicy("labadmin", "aife", "aife", 10001, 10001)


def _patch_unprivileged_test_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executor.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        executor,
        "_service_identity",
        lambda _policy: (
            SimpleNamespace(pw_uid=10001, pw_gid=10001, pw_shell="/usr/sbin/nologin", pw_dir="/nonexistent"),
            SimpleNamespace(gr_gid=10001),
        ),
    )
    monkeypatch.setattr(executor, "_set_operator_readable", lambda *_args, **_kwargs: None)


def _plan(repo: Path, head: str, tree: str, tmp_path: Path, release_id: str) -> deployment.ReleasePlan:
    _, plan, _ = deployment.materialize_immutable_release(
        repo,
        expected_head=head,
        expected_tree=tree,
        release_root=tmp_path / "plan-root",
        release_id=release_id,
    )
    return plan


def _stage_request(
    layout: executor.HostLayout,
    repo: Path,
    head: str,
    tree: str,
    plan: deployment.ReleasePlan,
    request_id: str,
    *,
    intent: str = "install",
    make_bundle: bool = True,
) -> tuple[dict[str, object], str]:
    request_dir = layout.staging_root / request_id
    request_dir.mkdir()
    bundle_sha: str | None = None
    if make_bundle:
        bundle = request_dir / "source.bundle"
        _git(repo, "bundle", "create", str(bundle), "--all")
        bundle_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
    request: dict[str, object] = {
        "schema_version": executor.REQUEST_SCHEMA,
        "intent": intent,
        "deployment_id": request_id,
        "receipt_id": f"receipt-{request_id}",
        "release_id": plan.release_id,
        "source_head": head,
        "source_tree": tree,
        "bundle_sha256": bundle_sha,
        "release_digest": plan.release_digest,
        "release_manifest_id": plan.release_manifest_id,
        "config_identity": "config:v1",
        "control_backend_identity": "sqlite:v1",
        "control_schema_identity": "aife-server-control",
        "backing_identity": "disk:v1",
    }
    data = (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (request_dir / "request.json").write_bytes(data)
    return request, hashlib.sha256(data).hexdigest()


def _stage_validation(layout: executor.HostLayout, request_id: str, request: dict[str, object]) -> str:
    validation = {
        "schema_version": executor.VALIDATION_SCHEMA,
        "deployment_id": request["deployment_id"],
        "release_id": request["release_id"],
        "source_head": request["source_head"],
        "source_tree": request["source_tree"],
        "status": "PASS",
        "checks": {key: "PASS" for key in executor.REQUIRED_PRE_ACTIVATION_CHECKS},
    }
    data = (json.dumps(validation, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (layout.staging_root / request_id / "validation.json").write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_valid_install_activation_and_idempotent_reconcile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "release-1")
    request, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-1")

    installed = executor.install_release(layout, _policy(), "deploy-1", request_sha, core=deployment)
    assert installed["status"] == "PASS"
    assert installed["exact_byte_verification"] == "PASS"
    assert installed["release_controlled_root_execution"] == "NO"
    release_path = layout.release_root / "release-1"
    assert release_path.is_dir() and not release_path.is_symlink()
    deployment.verify_installed_release(release_path, plan.manifest)
    assert not (release_path.stat().st_mode & 0o222)
    assert (release_path / "deploy/server/installer/post-install").is_file()

    validation_sha = _stage_validation(layout, "deploy-1", request)
    activated = executor.activate_release(
        layout, _policy(), "deploy-1", request_sha, validation_sha, core=deployment
    )
    assert activated["atomic_activation"] == "PASS"
    assert layout.current_pointer.resolve() == release_path.resolve()
    mapping = json.loads(layout.deployment_map.read_text())
    assert mapping["release_root"] == str(layout.release_root)
    assert mapping["data_root"] == str(layout.data_root)
    receipt = deployment.readback_deployment_receipt(
        layout.receipt_root / "deploy-1.json",
        expected_deployment_id="deploy-1",
        expected_receipt_id="receipt-deploy-1",
    )
    assert receipt["terminal_outcome"] == "PASS"

    reconciled = executor.activate_release(
        layout, _policy(), "deploy-1", request_sha, validation_sha, core=deployment
    )
    assert reconciled["reconciled"] is True
    assert not layout.previous_pointer.exists()


def test_digest_mismatch_rejected_before_canonical_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "release-bad")
    request, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-bad")
    request["release_digest"] = "0" * 64
    data = (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (layout.staging_root / "deploy-bad" / "request.json").write_bytes(data)
    request_sha = hashlib.sha256(data).hexdigest()
    with pytest.raises(executor.ExecutorError, match="release identity mismatch"):
        executor.install_release(layout, _policy(), "deploy-bad", request_sha, core=deployment)
    assert not (layout.release_root / "release-bad").exists()


def test_existing_release_overwrite_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "stable-release")
    _, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-stable")
    existing = layout.release_root / "stable-release"
    existing.mkdir()
    (existing / "unexpected").write_text("different\n")
    with pytest.raises(deployment.ReleaseIdentityMismatch):
        executor.install_release(layout, _policy(), "deploy-stable", request_sha, core=deployment)
    assert (existing / "unexpected").read_text() == "different\n"


def test_activation_before_validation_rejected_without_pointer_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "release-1")
    request, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-1")
    executor.install_release(layout, _policy(), "deploy-1", request_sha, core=deployment)
    validation_sha = _stage_validation(layout, "deploy-1", request)
    path = layout.staging_root / "deploy-1" / "validation.json"
    raw = json.loads(path.read_text())
    raw["status"] = "FAIL"
    data = (json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    validation_sha = hashlib.sha256(data).hexdigest()
    with pytest.raises(executor.ExecutorError, match="validation schema/status"):
        executor.activate_release(layout, _policy(), "deploy-1", request_sha, validation_sha, core=deployment)
    assert not layout.current_pointer.exists()
    assert not layout.deployment_map.exists()


def test_validation_identity_mismatch_rejected_without_pointer_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "release-1")
    request, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-1")
    executor.install_release(layout, _policy(), "deploy-1", request_sha, core=deployment)
    _stage_validation(layout, "deploy-1", request)
    path = layout.staging_root / "deploy-1" / "validation.json"
    raw = json.loads(path.read_text())
    raw["source_tree"] = "f" * 40
    data = (json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    validation_sha = hashlib.sha256(data).hexdigest()
    with pytest.raises(executor.ExecutorError, match="validation identity mismatch"):
        executor.activate_release(layout, _policy(), "deploy-1", request_sha, validation_sha, core=deployment)
    assert not layout.current_pointer.exists()
    assert not layout.deployment_map.exists()


def test_repeated_install_is_reconcilable_and_does_not_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)
    repo, head, tree = _fixture_repo(tmp_path)
    plan = _plan(repo, head, tree, tmp_path, "release-repeat")
    _, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-repeat")
    first = executor.install_release(layout, _policy(), "deploy-repeat", request_sha, core=deployment)
    manifest_before = (layout.release_root / "release-repeat" / deployment.MANIFEST).read_bytes()
    second = executor.install_release(layout, _policy(), "deploy-repeat", request_sha, core=deployment)
    assert first["release_manifest_id"] == second["release_manifest_id"]
    assert (layout.release_root / "release-repeat" / deployment.MANIFEST).read_bytes() == manifest_before


def test_upgrade_and_explicit_rollback_preserve_current_previous_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    layout = _layout(tmp_path)

    repo1, head1, tree1 = _fixture_repo(tmp_path, "v1")
    plan1 = _plan(repo1, head1, tree1, tmp_path / "p1", "release-v1")
    req1, sha1 = _stage_request(layout, repo1, head1, tree1, plan1, "deploy-v1")
    executor.install_release(layout, _policy(), "deploy-v1", sha1, core=deployment)
    val1 = _stage_validation(layout, "deploy-v1", req1)
    executor.activate_release(layout, _policy(), "deploy-v1", sha1, val1, core=deployment)

    repo2, head2, tree2 = _fixture_repo(tmp_path, "v2")
    plan2 = _plan(repo2, head2, tree2, tmp_path / "p2", "release-v2")
    req2, sha2 = _stage_request(layout, repo2, head2, tree2, plan2, "deploy-v2", intent="upgrade")
    executor.install_release(layout, _policy(), "deploy-v2", sha2, core=deployment)
    val2 = _stage_validation(layout, "deploy-v2", req2)
    executor.activate_release(layout, _policy(), "deploy-v2", sha2, val2, core=deployment)
    assert layout.current_pointer.resolve() == (layout.release_root / "release-v2").resolve()
    assert layout.previous_pointer.resolve() == (layout.release_root / "release-v1").resolve()

    rollback_dir = layout.staging_root / "rollback-v1"
    rollback_dir.mkdir()
    rollback_req = dict(req1)
    rollback_req.update(
        {
            "intent": "rollback",
            "deployment_id": "rollback-v1",
            "receipt_id": "receipt-rollback-v1",
            "bundle_sha256": None,
        }
    )
    rollback_data = (json.dumps(rollback_req, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (rollback_dir / "request.json").write_bytes(rollback_data)
    rollback_sha = hashlib.sha256(rollback_data).hexdigest()
    rollback_val = _stage_validation(layout, "rollback-v1", rollback_req)
    executor.activate_release(layout, _policy(), "rollback-v1", rollback_sha, rollback_val, core=deployment)
    assert layout.current_pointer.resolve() == (layout.release_root / "release-v1").resolve()
    assert layout.previous_pointer.resolve() == (layout.release_root / "release-v2").resolve()


def test_concurrent_deployment_lock_fails_closed(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    first = executor._lock(layout)
    try:
        with pytest.raises(executor.ExecutorError, match="concurrent deployment"):
            executor._lock(layout)
    finally:
        os.close(first)



def test_c9_trusted_core_binding_and_databridge_projection_survive_verified_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_unprivileged_test_host(monkeypatch)
    executor._sanitize_environment()
    core_path = Path(deployment.__file__)
    assert hashlib.sha256(core_path.read_bytes()).hexdigest() == executor.TRUSTED_CORE_SHA256
    loaded = executor.load_deployment_core(
        core_path,
        expected_sha256=executor.TRUSTED_CORE_SHA256,
        enforce_root_trust=False,
    )
    assert Path(loaded.__file__).resolve() == core_path.resolve()

    layout = _layout(tmp_path)
    repo, _head, _tree = _fixture_repo(tmp_path, "c9")
    provider = repo / "src" / "canonical-provider.py"
    provider.parent.mkdir()
    provider.write_bytes(b"C9_PROVIDER = b'exact-git-byte-fixture'\n")
    _git(repo, "add", "src/canonical-provider.py")
    _git(repo, "commit", "-q", "-m", "add c9 provider fixture")
    head = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    plan = _plan(repo, head, tree, tmp_path, "release-c9")
    _request, request_sha = _stage_request(layout, repo, head, tree, plan, "deploy-c9")

    installed = executor.install_release(layout, _policy(), "deploy-c9", request_sha, core=deployment)
    release = layout.release_root / "release-c9"
    expected = subprocess.run(
        ["git", "-C", str(repo), "show", f"{head}:src/canonical-provider.py"],
        check=True,
        capture_output=True,
    ).stdout
    assert installed["status"] == "PASS"
    assert installed["exact_byte_verification"] == "PASS"
    assert installed["release_controlled_root_execution"] == "NO"
    assert (release / "canonical-provider.py").read_bytes() == expected
    deployment.verify_installed_release(release, plan.manifest)
