#!/usr/bin/env python3
"""Deterministically render the one-time AIFE privileged-executor bootstrap package."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA = "aife-bootstrap-package-manifest/1.0.0"
POLICY_SCHEMA = "aife-deployment-executor-policy/1.0.0"
EXECUTOR_SOURCE = Path("AIFE/staging/deploy/server/installer/aife_deploy.py")
SUDOERS_TEMPLATE = Path("AIFE/staging/deploy/server/installer/sudoers.aife-deploy.template")
TRUSTED_CORE_SOURCE = Path("AIFE/staging/server/runtime/deployment.py")
CANONICAL_EXECUTOR_PATH = "/usr/local/sbin/aife-deploy"
CANONICAL_CORE_PATH = "/usr/local/lib/aife-deploy/deployment.py"
CANONICAL_POLICY_PATH = "/etc/aife/deployment-executor-policy.json"
CANONICAL_SUDOERS_PATH = "/etc/sudoers.d/aife-deploy"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _token(value: str, field: str) -> str:
    if not _TOKEN.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def _head(value: str, field: str) -> str:
    if not _HEX40.fullmatch(value):
        raise ValueError(f"invalid {field}")
    return value


def render_package(
    *, repo_root: Path, output_dir: Path, source_head: str, source_tree: str,
    deployment_caller: str, service_account: str, service_group: str,
    service_uid: int, service_gid: int,
) -> Mapping[str, str]:
    source_head = _head(source_head, "source_head")
    source_tree = _head(source_tree, "source_tree")
    deployment_caller = _token(deployment_caller, "deployment_caller")
    service_account = _token(service_account, "service_account")
    service_group = _token(service_group, "service_group")
    if service_uid <= 0 or service_gid <= 0:
        raise ValueError("service uid/gid")
    repo_root = repo_root.resolve()
    executor = (repo_root / EXECUTOR_SOURCE).read_bytes()
    core = (repo_root / TRUSTED_CORE_SOURCE).read_bytes()
    template = (repo_root / SUDOERS_TEMPLATE).read_text(encoding="utf-8")
    executor_sha = _sha(executor)
    core_sha = _sha(core)
    if "@CALLER@" not in template or "@EXECUTOR_SHA256@" not in template:
        raise ValueError("sudoers template placeholders")
    rendered_sudoers = template.replace("@CALLER@", deployment_caller).replace("@EXECUTOR_SHA256@", executor_sha)
    if "@CALLER@" in rendered_sudoers or "@EXECUTOR_SHA256@" in rendered_sudoers:
        raise ValueError("sudoers template rendering")
    sudoers = rendered_sudoers.encode()
    policy = _json_bytes({
        "schema_version": POLICY_SCHEMA,
        "deployment_caller": deployment_caller,
        "service_account": service_account,
        "service_group": service_group,
        "service_uid": service_uid,
        "service_gid": service_gid,
    })
    policy_sha = _sha(policy)
    sudoers_sha = _sha(sudoers)
    manifest = _json_bytes({
        "schema_version": SCHEMA,
        "source_head": source_head,
        "source_tree": source_tree,
        "executor_sha256": executor_sha,
        "trusted_core_sha256": core_sha,
        "policy_sha256": policy_sha,
        "sudoers_sha256": sudoers_sha,
        "deployment_caller": deployment_caller,
        "service_account": service_account,
        "service_group": service_group,
        "service_uid": service_uid,
        "service_gid": service_gid,
        "canonical_executor_path": CANONICAL_EXECUTOR_PATH,
        "canonical_trusted_core_path": CANONICAL_CORE_PATH,
        "canonical_policy_path": CANONICAL_POLICY_PATH,
        "canonical_sudoers_path": CANONICAL_SUDOERS_PATH,
    })
    files = {
        "aife-deploy": executor,
        "deployment.py": core,
        "deployment-executor-policy.json": policy,
        "aife-deploy.sudoers": sudoers,
        "bootstrap-package-manifest.json": manifest,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    for name, data in files.items():
        (output_dir / name).write_bytes(data)
    sums = "".join(f"{_sha(files[name])}  {name}\n" for name in sorted(files)).encode()
    (output_dir / "SHA256SUMS.txt").write_bytes(sums)
    return {
        "executor_sha256": executor_sha,
        "trusted_core_sha256": core_sha,
        "policy_sha256": policy_sha,
        "sudoers_sha256": sudoers_sha,
        "bootstrap_package_manifest_sha256": _sha(manifest),
        "bootstrap_sha256sums_sha256": _sha(sums),
    }


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--deployment-caller", required=True)
    parser.add_argument("--service-account", default="aife")
    parser.add_argument("--service-group", default="aife")
    parser.add_argument("--service-uid", type=int, default=10001)
    parser.add_argument("--service-gid", type=int, default=10001)
    args = parser.parse_args(argv)
    result = render_package(**vars(args))
    for key, value in sorted(result.items()):
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
