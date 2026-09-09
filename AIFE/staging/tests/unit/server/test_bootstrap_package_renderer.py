from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from deploy.server.installer import render_bootstrap_package as renderer


def _render(repo_root: Path, output: Path) -> dict[str, str]:
    return dict(
        renderer.render_package(
            repo_root=repo_root,
            output_dir=output,
            source_head="a" * 40,
            source_tree="b" * 40,
            deployment_caller="labadmin",
            service_account="aife",
            service_group="aife",
            service_uid=10001,
            service_gid=10001,
        )
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(root.iterdir()) if path.is_file()}


def test_two_render_runs_are_byte_identical(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    result_a = _render(repo_root, run_a)
    result_b = _render(repo_root, run_b)
    assert result_a == result_b
    assert _tree_bytes(run_a) == _tree_bytes(run_b)


def test_manifest_binds_source_identities_digests_profile_and_canonical_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    output = tmp_path / "package"
    result = _render(repo_root, output)
    manifest_bytes = (output / "bootstrap-package-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    assert hashlib.sha256(manifest_bytes).hexdigest() == result["bootstrap_package_manifest_sha256"]
    assert manifest["source_head"] == "a" * 40
    assert manifest["source_tree"] == "b" * 40
    assert manifest["executor_sha256"] == hashlib.sha256((output / "aife-deploy").read_bytes()).hexdigest()
    assert manifest["trusted_core_sha256"] == hashlib.sha256((output / "deployment.py").read_bytes()).hexdigest()
    assert manifest["policy_sha256"] == hashlib.sha256((output / "deployment-executor-policy.json").read_bytes()).hexdigest()
    assert manifest["sudoers_sha256"] == hashlib.sha256((output / "aife-deploy.sudoers").read_bytes()).hexdigest()
    assert manifest["deployment_caller"] == "labadmin"
    assert manifest["service_account"] == "aife"
    assert manifest["service_group"] == "aife"
    assert manifest["service_uid"] == 10001
    assert manifest["service_gid"] == 10001
    assert manifest["canonical_executor_path"] == "/usr/local/sbin/aife-deploy"
    assert manifest["canonical_trusted_core_path"] == "/usr/local/lib/aife-deploy/deployment.py"
    assert manifest["canonical_policy_path"] == "/etc/aife/deployment-executor-policy.json"
    assert manifest["canonical_sudoers_path"] == "/etc/sudoers.d/aife-deploy"


def test_sudoers_is_exact_template_projection_and_sha256sums_verify(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    output = tmp_path / "package"
    result = _render(repo_root, output)
    executor_sha = hashlib.sha256((repo_root / renderer.EXECUTOR_SOURCE).read_bytes()).hexdigest()
    expected = (repo_root / renderer.SUDOERS_TEMPLATE).read_text().replace("@CALLER@", "labadmin").replace(
        "@EXECUTOR_SHA256@", executor_sha
    ).encode()
    assert (output / "aife-deploy.sudoers").read_bytes() == expected
    sums = (output / "SHA256SUMS.txt").read_bytes()
    assert hashlib.sha256(sums).hexdigest() == result["bootstrap_sha256sums_sha256"]
    for line in sums.decode().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


def test_renderer_rejects_nonempty_output_and_invalid_identity(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    output = tmp_path / "package"
    output.mkdir()
    (output / "stale").write_text("x")
    with pytest.raises(ValueError, match="output directory must be empty"):
        _render(repo_root, output)
    with pytest.raises(ValueError, match="source_head"):
        renderer.render_package(
            repo_root=repo_root,
            output_dir=tmp_path / "invalid",
            source_head="not-a-head",
            source_tree="b" * 40,
            deployment_caller="labadmin",
            service_account="aife",
            service_group="aife",
            service_uid=10001,
            service_gid=10001,
        )
