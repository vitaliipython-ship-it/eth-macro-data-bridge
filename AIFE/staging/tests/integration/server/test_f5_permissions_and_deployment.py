"""
Bounded F5 implementation acceptance tests for this mapped owner path.

[Purpose]
    Доказать bounded F5 implementation acceptance tests for this mapped owner path.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Pytest cases и fixtures, проверяющие mapped F5 invariants этого owner path.

[Usage]
    Запускать через canonical pytest/toolchain gates; тесты не являются production runtime.

[Architecture]
    Test surface проверяет generic AIFE Server contour на disposable future-AIFE tree; Data Bridge
    остаётся authority domain semantics.

[Note]
    Physical SQLite/filesystem и Docker qualification имеют отдельные evidence gates поверх этих тестов.

[Warning]
    Не ослаблять assertions и не принимать unit/integration PASS за production или Docker activation.
"""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from server.configuration.models import F5ReadinessConfig
from server.runtime.deployment import (
    ActivationError,
    DeploymentReceiptMismatch,
    GitIdentityMismatch,
    MaterializedByteMismatch,
    ProjectedPathCollision,
    ReleaseIdentityMismatch,
    execute_disposable_deployment,
    materialize_immutable_release,
    readback_deployment_receipt,
    verify_exact_git_identity,
    verify_installed_release,
)
from server.runtime.readiness import evaluate_f5_readiness


def cfg(tmp_path, *, mapping=None, minimum_free_bytes=1):
    """Exercise the mapped F5 acceptance case."""
    root = tmp_path / "data"
    root.mkdir(exist_ok=True)
    mp = tmp_path / "deployment.json"
    d = {
        "control_schema_version": 1,
        "backing_identity": "disk-test",
        "data_root": str(root),
        "control_schema_id": "aife-server-control",
        "config_identity": "config-1",
        "active_release_identity": "release-1",
    }
    d.update(mapping or {})
    mp.write_text(json.dumps(d))
    return F5ReadinessConfig(
        deployment_map_path=mp,
        expected_release_identity="release-1",
        expected_config_identity="config-1",
        expected_backing_identity="disk-test",
        minimum_free_bytes=minimum_free_bytes,
    )


def test_f11_missing_data_root(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    assert not evaluate_f5_readiness(
        cfg(tmp_path, mapping={"data_root": str(tmp_path / "missing")}),
        control_schema_check=lambda: None,
    ).ready


def test_f12_unwritable_data_root(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    c = cfg(tmp_path)
    root = tmp_path / "data"
    os.chmod(root, 0o555)
    try:
        assert not evaluate_f5_readiness(c, control_schema_check=lambda: None).ready
    finally:
        os.chmod(root, 0o755)


def test_f13_insufficient_space(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    assert not evaluate_f5_readiness(cfg(tmp_path, minimum_free_bytes=10**30), control_schema_check=lambda: None).ready


def test_f17_f18_deployment_release_config_schema_mismatch(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    for m in (
        {"active_release_identity": "wrong"},
        {"config_identity": "wrong"},
        {"control_schema_id": "wrong"},
        {"control_schema_version": 2},
        {"backing_identity": "wrong"},
    ):
        assert not evaluate_f5_readiness(cfg(tmp_path, mapping=m), control_schema_check=lambda: None).ready


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _fixture_checkout(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "c6@example.invalid")
    _git(repo, "config", "user.name", "C6 Fixture")
    source = repo / "AIFE" / "staging" / "server" / "fixture.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 'c6-v1'\n", encoding="utf-8")
    executable = repo / "AIFE" / "staging" / "bin" / "fixture-tool"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\necho c6\n", encoding="utf-8")
    os.chmod(executable, 0o755)
    _git(repo, "add", "AIFE/staging")
    _git(repo, "commit", "-q", "-m", "c6 fixture")
    return repo, _git(repo, "rev-parse", "HEAD"), _git(repo, "rev-parse", "HEAD^{tree}")


def _persistent_roots(tmp_path: Path) -> dict[str, str]:
    data_root = tmp_path / "data-root"
    data_root.mkdir(exist_ok=True)
    return {
        "data_root": str(data_root),
        "state_root": str(tmp_path / "state"),
        "spool_root": str(tmp_path / "spool"),
        "log_root": str(tmp_path / "log"),
        "backing_identity": "disk-c6",
    }


def _accepted_predecessor(install_root: Path) -> Path:
    predecessor = install_root / "releases" / "release-predecessor"
    predecessor.mkdir(parents=True)
    marker = predecessor / "accepted.txt"
    marker.write_text("accepted predecessor\n", encoding="utf-8")
    os.chmod(marker, 0o444)
    os.chmod(predecessor, 0o555)
    current = install_root / "current"
    current.symlink_to(predecessor.resolve())
    return predecessor


def test_c6_exact_git_projection_release_receipt_and_atomic_activation(tmp_path):
    """Exact Git bytes become a distinct immutable release with durable activation evidence."""
    repo, head, tree = _fixture_checkout(tmp_path)
    install_root = tmp_path / "install"
    install_root.mkdir()
    predecessor = _accepted_predecessor(install_root)
    roots = _persistent_roots(tmp_path)

    def readiness(mapping):
        assert mapping["source_head"] == head
        assert mapping["source_tree"] == tree
        config = F5ReadinessConfig(
            deployment_map_path=install_root / "config" / "deployment-map.json",
            expected_release_identity="release-opaque-c6",
            expected_config_identity="config-c6",
            expected_backing_identity="disk-c6",
            minimum_free_bytes=1,
        )
        return evaluate_f5_readiness(config, control_schema_check=lambda: None).ready

    result = execute_disposable_deployment(
        repo,
        expected_head=head,
        expected_tree=tree,
        install_root=install_root,
        release_id="release-opaque-c6",
        deployment_id="deployment-c6",
        deployment_receipt_id="receipt-c6",
        config_identity="config-c6",
        control_backend_identity="sqlite-c6",
        control_schema_identity="aife-server-control",
        persistent_roots=roots,
        pre_activation_check=readiness,
    )

    assert result.release.release_id == "release-opaque-c6"
    assert result.release.release_id not in {head, tree}
    assert len(result.release.entries) == 2
    assert all(entry.byte_identity_match for entry in result.release.entries)
    assert all(len(value) == 64 for value in (result.release.release_digest, result.release.release_manifest_id))
    assert (install_root / "current").resolve() == result.release_path.resolve()
    assert (install_root / "previous").resolve() == predecessor.resolve()
    assert result.receipt["source_head"] == head
    assert result.receipt["source_tree"] == tree
    assert result.receipt["release_id"] == "release-opaque-c6"
    assert result.receipt["release_digest"] == result.release.release_digest
    assert result.receipt["release_manifest_id"] == result.release.release_manifest_id
    assert result.receipt["terminal_outcome"] == "PASS"
    assert stat.S_IMODE(result.release_path.stat().st_mode) & 0o222 == 0
    for entry in result.release.entries:
        assert stat.S_IMODE((result.release_path / entry.projected_path).stat().st_mode) & 0o222 == 0


def test_c6_wrong_expected_git_head_fails_closed(tmp_path):
    repo, _head, tree = _fixture_checkout(tmp_path)
    with pytest.raises(GitIdentityMismatch):
        verify_exact_git_identity(repo, "0" * 40, tree)


def test_c6_wrong_expected_git_tree_fails_closed(tmp_path):
    repo, head, _tree = _fixture_checkout(tmp_path)
    with pytest.raises(GitIdentityMismatch):
        verify_exact_git_identity(repo, head, "0" * 40)


def test_c6_materialized_source_byte_mismatch_fails_closed(tmp_path):
    repo, head, tree = _fixture_checkout(tmp_path)
    _identity, plan, release_path = materialize_immutable_release(
        repo,
        expected_head=head,
        expected_tree=tree,
        release_root=tmp_path / "releases",
        release_id="release-byte-check",
    )
    target = release_path / plan.entries[0].projected_path
    os.chmod(release_path, 0o755)
    os.chmod(target, 0o644)
    target.write_bytes(target.read_bytes() + b"tampered")
    with pytest.raises(MaterializedByteMismatch):
        verify_installed_release(release_path, plan.manifest)


def test_c6_preexisting_release_identity_with_different_digest_fails_closed(tmp_path):
    repo, head, tree = _fixture_checkout(tmp_path)
    release_root = tmp_path / "releases"
    materialize_immutable_release(
        repo,
        expected_head=head,
        expected_tree=tree,
        release_root=release_root,
        release_id="stable-release-id",
    )
    source = repo / "AIFE" / "staging" / "server" / "fixture.py"
    source.write_text("VALUE = 'c6-v2'\n", encoding="utf-8")
    _git(repo, "add", str(source.relative_to(repo)))
    _git(repo, "commit", "-q", "-m", "change bytes")
    new_head = _git(repo, "rev-parse", "HEAD")
    new_tree = _git(repo, "rev-parse", "HEAD^{tree}")
    with pytest.raises(ReleaseIdentityMismatch):
        materialize_immutable_release(
            repo,
            expected_head=new_head,
            expected_tree=new_tree,
            release_root=release_root,
            release_id="stable-release-id",
        )


def test_c6_release_manifest_identity_mismatch_fails_closed(tmp_path):
    repo, head, tree = _fixture_checkout(tmp_path)
    _identity, plan, release_path = materialize_immutable_release(
        repo,
        expected_head=head,
        expected_tree=tree,
        release_root=tmp_path / "releases",
        release_id="manifest-check",
    )
    manifest_path = release_path / ".aife-release-manifest.json"
    os.chmod(release_path, 0o755)
    os.chmod(manifest_path, 0o644)
    observed = json.loads(manifest_path.read_text(encoding="utf-8"))
    observed["release_digest"] = "f" * 64
    manifest_path.write_text(json.dumps(observed), encoding="utf-8")
    with pytest.raises(ReleaseIdentityMismatch):
        verify_installed_release(release_path, plan.manifest)


def test_c6_deployment_receipt_identity_mismatch_fails_closed(tmp_path):
    repo, head, tree = _fixture_checkout(tmp_path)
    install_root = tmp_path / "install"
    install_root.mkdir()
    _accepted_predecessor(install_root)
    result = execute_disposable_deployment(
        repo,
        expected_head=head,
        expected_tree=tree,
        install_root=install_root,
        release_id="receipt-release",
        deployment_id="deployment-c6",
        deployment_receipt_id="receipt-c6",
        config_identity="config-c6",
        control_backend_identity="sqlite-c6",
        control_schema_identity="aife-server-control",
        persistent_roots=_persistent_roots(tmp_path),
        pre_activation_check=lambda _mapping: True,
    )
    with pytest.raises(DeploymentReceiptMismatch):
        readback_deployment_receipt(
            result.receipt_path,
            expected_deployment_id="deployment-c6",
            expected_receipt_id="wrong-receipt",
        )


def test_c6_activation_precondition_failure_preserves_predecessor_and_emits_receipt(tmp_path):
    repo, head, tree = _fixture_checkout(tmp_path)
    install_root = tmp_path / "install"
    install_root.mkdir()
    predecessor = _accepted_predecessor(install_root)
    with pytest.raises(ActivationError):
        execute_disposable_deployment(
            repo,
            expected_head=head,
            expected_tree=tree,
            install_root=install_root,
            release_id="blocked-candidate",
            deployment_id="failed-deployment-c6",
            deployment_receipt_id="failed-receipt-c6",
            config_identity="config-c6",
            control_backend_identity="sqlite-c6",
            control_schema_identity="aife-server-control",
            persistent_roots=_persistent_roots(tmp_path),
            pre_activation_check=lambda _mapping: False,
        )
    assert (install_root / "current").resolve() == predecessor.resolve()
    assert not (install_root / "previous").exists()
    receipt_path = install_root / "state" / "deployments" / "receipts" / "failed-deployment-c6.json"
    receipt = readback_deployment_receipt(
        receipt_path,
        expected_deployment_id="failed-deployment-c6",
        expected_receipt_id="failed-receipt-c6",
    )
    assert receipt["activation_result"] == "PRECONDITION_FAILED"
    assert receipt["terminal_outcome"] == "FAIL"

def test_privileged_executor_required_pre_activation_checks_cover_deployment_contract():
    from deploy.server.installer.aife_deploy import REQUIRED_PRE_ACTIVATION_CHECKS

    assert set(REQUIRED_PRE_ACTIVATION_CHECKS) == {
        "exact_release_readback",
        "config_identity",
        "control_backend_compatibility",
        "control_schema_compatibility",
        "persistent_root_backing_binding",
        "mount_space_permission_preflight",
        "pre_activation_health_readiness",
        "applicable_write_readback",
    }



def test_c9_release_projects_canonical_src_exact_git_bytes_and_manifest(tmp_path):
    repo, _head, _tree = _fixture_checkout(tmp_path)
    canonical = repo / "src" / "canonical-provider.py"
    canonical.parent.mkdir()
    canonical.write_bytes(b"CANONICAL_PROVIDER_BYTES = b'c9-exact-git-bytes'\n")
    _git(repo, "add", "src/canonical-provider.py")
    _git(repo, "commit", "-q", "-m", "add canonical provider fixture")
    head = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")

    _identity, plan, release = materialize_immutable_release(
        repo,
        expected_head=head,
        expected_tree=tree,
        release_root=tmp_path / "c9-releases",
        release_id="c9-projection",
    )
    entries = {entry.projected_path: entry for entry in plan.entries}
    assert "server/fixture.py" in entries
    assert "canonical-provider.py" in entries
    projected = release / "canonical-provider.py"
    git_blob = subprocess.run(
        ["git", "-C", str(repo), "show", f"{head}:src/canonical-provider.py"],
        check=True,
        capture_output=True,
    ).stdout
    assert projected.read_bytes() == git_blob
    assert entries["canonical-provider.py"].source_path == "src/canonical-provider.py"
    assert entries["canonical-provider.py"].byte_identity_match
    manifest = json.loads((release / ".aife-release-manifest.json").read_text())
    manifest_entry = next(row for row in manifest["entries"] if row["projected_path"] == "canonical-provider.py")
    assert manifest_entry["source_path"] == "src/canonical-provider.py"
    assert manifest_entry["source_byte_sha256"] == entries["canonical-provider.py"].source_sha256
    assert stat.S_IMODE(projected.stat().st_mode) & 0o222 == 0
    verify_installed_release(release, plan.manifest)


def test_c9_projected_path_collision_fails_before_release_materialization(tmp_path):
    repo, _head, _tree = _fixture_checkout(tmp_path)
    staged = repo / "AIFE" / "staging" / "collision.py"
    canonical = repo / "src" / "collision.py"
    staged.write_text("ORIGIN = 'staging'\n", encoding="utf-8")
    canonical.parent.mkdir()
    canonical.write_text("ORIGIN = 'src'\n", encoding="utf-8")
    _git(repo, "add", "AIFE/staging/collision.py", "src/collision.py")
    _git(repo, "commit", "-q", "-m", "collision fixture")
    head = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    release_root = tmp_path / "collision-releases"

    with pytest.raises(ProjectedPathCollision, match="collision.py"):
        materialize_immutable_release(
            repo,
            expected_head=head,
            expected_tree=tree,
            release_root=release_root,
            release_id="must-not-exist",
        )
    assert not release_root.exists()
