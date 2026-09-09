#!/usr/bin/env python3
"""Read-only late-bound effective-integration qualification orchestration."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Mapping, Sequence

from current_data_pr_binding import BindingError, require_no_final_main_drift, verify_binding

ROUTE_SCHEMA = "pr-effective-integration-requalification/1.0.0"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class RequalificationError(RuntimeError):
    """Raised when late-bound PR requalification cannot proceed safely."""


def _require_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise RequalificationError(f"{field} must be exact lowercase 40-hex SHA")
    return value


def validate_dispatch_inputs(pr_number: object, expected_pr_head_sha: object) -> tuple[int, str]:
    try:
        number = int(pr_number)
    except (TypeError, ValueError) as exc:
        raise RequalificationError("pr_number must be a positive integer") from exc
    if number <= 0:
        raise RequalificationError("pr_number must be a positive integer")
    return number, _require_sha(expected_pr_head_sha, "expected_pr_head_sha")


def validate_pr_metadata(
    metadata: Mapping[str, object], *, repository: str, expected_pr_head_sha: str
) -> dict[str, str | int | bool]:
    head = metadata.get("head")
    base = metadata.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise RequalificationError("PR metadata lacks head/base objects")
    head_repo = head.get("repo")
    base_repo = base.get("repo")
    if not isinstance(head_repo, Mapping) or not isinstance(base_repo, Mapping):
        raise RequalificationError("PR metadata lacks head/base repository objects")
    if metadata.get("state") != "open":
        raise RequalificationError("target PR must be open")
    if metadata.get("merged") is not False:
        raise RequalificationError("target PR merged state must be exact false")
    if base.get("ref") != "main":
        raise RequalificationError("target PR base ref must be main")
    if head_repo.get("full_name") != repository or base_repo.get("full_name") != repository:
        raise RequalificationError("target PR must be same-repository")
    head_sha = _require_sha(head.get("sha"), "target_pr_head_sha")
    expected = _require_sha(expected_pr_head_sha, "expected_pr_head_sha")
    if head_sha != expected:
        raise RequalificationError("target PR head differs from expected exact head")
    event_base_sha = _require_sha(base.get("sha"), "pr_event_base_sha")
    head_ref = head.get("ref")
    if not isinstance(head_ref, str) or not head_ref:
        raise RequalificationError("target PR head ref is missing")
    number = metadata.get("number")
    if not isinstance(number, int) or number <= 0:
        raise RequalificationError("target PR number is invalid")
    return {
        "number": number,
        "state": "open",
        "merged": False,
        "base_ref": "main",
        "event_base_sha": event_base_sha,
        "head_repository": repository,
        "head_ref": head_ref,
        "head_sha": head_sha,
    }


def fetch_pr_metadata(repository: str, pr_number: int, token: str) -> dict[str, object]:
    if not token:
        raise RequalificationError("GitHub token is required for PR readback")
    url = f"https://api.github.com/repos/{repository}/pulls/{pr_number}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr-effective-integration-requalification",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RequalificationError("GitHub PR response is not an object")
    return payload


def _git(repo: Path | str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RequalificationError(f"git {' '.join(args)} failed: {detail}")
    return result


def _rev_parse(repo: Path | str, value: str) -> str:
    return _git(repo, "rev-parse", value).stdout.strip()


def read_remote_branch_head(repo: Path | str, branch: str) -> str:
    result = _git(repo, "ls-remote", "origin", f"refs/heads/{branch}")
    rows = result.stdout.splitlines()
    if len(rows) != 1:
        raise RequalificationError("target PR remote branch head cannot be proven exactly")
    return _require_sha(rows[0].split()[0], "current_pr_head_sha")


def fetch_effective_base(repo: Path | str) -> tuple[str, str]:
    _git(repo, "fetch", "--no-tags", "--prune", "origin", "+refs/heads/main:refs/remotes/origin/main")
    sha = _require_sha(_rev_parse(repo, "refs/remotes/origin/main"), "effective_base_sha")
    return sha, _require_sha(_rev_parse(repo, f"{sha}^{{tree}}"), "effective_base_tree")


def fetch_exact_head(repo: Path | str, head_sha: str) -> str:
    head_sha = _require_sha(head_sha, "target_pr_head_sha")
    _git(repo, "fetch", "--no-tags", "origin", head_sha)
    resolved = _require_sha(_rev_parse(repo, head_sha), "resolved_pr_head_sha")
    if resolved != head_sha:
        raise RequalificationError("fetched PR head does not resolve to expected SHA")
    return _require_sha(_rev_parse(repo, f"{head_sha}^{{tree}}"), "target_pr_head_tree")


def build_local_synthetic(repo: Path | str, *, effective_base_sha: str, pr_head_sha: str) -> dict[str, str]:
    base = _require_sha(effective_base_sha, "effective_base_sha")
    head = _require_sha(pr_head_sha, "pr_head_sha")
    merge = _git(repo, "merge-tree", "--write-tree", base, head, check=False)
    if merge.returncode != 0:
        detail = (merge.stderr or merge.stdout).strip()
        raise RequalificationError(f"LATE_BOUND_PR_EFFECTIVE_INTEGRATION_CONFLICT: {detail}")
    lines = [line.strip() for line in merge.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RequalificationError("synthetic integration tree output is not exact")
    tree = _require_sha(lines[0], "synthetic_tree")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "late-bound-pr-qualification",
            "GIT_AUTHOR_EMAIL": "qualification@example.invalid",
            "GIT_COMMITTER_NAME": "late-bound-pr-qualification",
            "GIT_COMMITTER_EMAIL": "qualification@example.invalid",
        }
    )
    commit = subprocess.run(
        [
            "git", "-C", str(repo), "commit-tree", tree,
            "-p", base, "-p", head,
            "-m", "ci(qualification): local late-bound PR effective integration",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if commit.returncode != 0:
        raise RequalificationError(f"git commit-tree failed: {(commit.stderr or commit.stdout).strip()}")
    synthetic = _require_sha(commit.stdout.strip(), "synthetic_sha")
    parents = _git(repo, "show", "-s", "--format=%P", synthetic).stdout.strip().split()
    if parents != [base, head]:
        raise RequalificationError("synthetic parent ordering does not match base + PR head")
    if _rev_parse(repo, f"{synthetic}^{{tree}}") != tree:
        raise RequalificationError("synthetic commit tree mismatch")
    return {
        "PR_EFFECTIVE_INTEGRATION_SHA": synthetic,
        "PR_EFFECTIVE_INTEGRATION_TREE": tree,
        "SYNTHETIC_PARENT_1_SHA": base,
        "SYNTHETIC_PARENT_2_SHA": head,
    }


def checkout_synthetic(repo: Path | str, synthetic_sha: str, expected_tree: str) -> dict[str, str]:
    synthetic = _require_sha(synthetic_sha, "synthetic_sha")
    tree = _require_sha(expected_tree, "expected_tree")
    _git(repo, "checkout", "--detach", synthetic)
    actual_sha = _require_sha(_rev_parse(repo, "HEAD"), "qualification_checkout_sha")
    actual_tree = _require_sha(_rev_parse(repo, "HEAD^{tree}"), "qualification_checkout_tree")
    if actual_sha != synthetic or actual_tree != tree:
        raise RequalificationError("qualification checkout identity mismatch")
    return {
        "QUALIFICATION_CHECKOUT_SHA": actual_sha,
        "QUALIFICATION_CHECKOUT_TREE": actual_tree,
        "ACTUAL_CHECKOUT_SHA_MATCH": "PASS",
        "ACTUAL_CHECKOUT_TREE_MATCH": "PASS",
    }


def verify_existing_binding(
    *, repo: Path | str, event_base_sha: str, expected_pr_head_sha: str,
    synthetic_sha: str, current_main_sha: str, current_pr_head_sha: str,
) -> dict[str, str]:
    try:
        return verify_binding(
            repo=repo,
            event_base_sha=event_base_sha,
            expected_pr_head_sha=expected_pr_head_sha,
            synthetic_sha=synthetic_sha,
            current_main_sha=current_main_sha,
            current_pr_head_sha=current_pr_head_sha,
        )
    except BindingError as exc:
        raise RequalificationError(f"existing PR binding rejected synthetic integration: {exc}") from exc


def require_final_main_unchanged(*, qualified_base_sha: str, final_main_sha: str) -> None:
    try:
        require_no_final_main_drift(
            qualified_main_sha=qualified_base_sha, final_main_sha=final_main_sha
        )
    except BindingError as exc:
        raise RequalificationError(str(exc)) from exc


def _write_evidence(path: Path, evidence: Mapping[str, object]) -> None:
    path.write_text(json.dumps(dict(evidence), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_evidence(evidence: Mapping[str, object]) -> None:
    for key in sorted(evidence):
        value = evidence[key]
        if isinstance(value, (str, int, bool)):
            print(f"{key}={value}")


def prepare(args: argparse.Namespace) -> int:
    number, expected_head = validate_dispatch_inputs(args.pr_number, args.expected_pr_head_sha)
    metadata = fetch_pr_metadata(args.repository, number, args.token)
    pr = validate_pr_metadata(metadata, repository=args.repository, expected_pr_head_sha=expected_head)
    remote_head = read_remote_branch_head(args.repo, str(pr["head_ref"]))
    if remote_head != expected_head:
        raise RequalificationError("remote PR branch head changed after metadata readback")
    effective_base, effective_base_tree = fetch_effective_base(args.repo)
    head_tree = fetch_exact_head(args.repo, expected_head)
    synthetic = build_local_synthetic(
        args.repo, effective_base_sha=effective_base, pr_head_sha=expected_head
    )
    binding = verify_existing_binding(
        repo=args.repo,
        event_base_sha=str(pr["event_base_sha"]),
        expected_pr_head_sha=expected_head,
        synthetic_sha=synthetic["PR_EFFECTIVE_INTEGRATION_SHA"],
        current_main_sha=effective_base,
        current_pr_head_sha=remote_head,
    )
    checkout = checkout_synthetic(
        args.repo,
        synthetic["PR_EFFECTIVE_INTEGRATION_SHA"],
        synthetic["PR_EFFECTIVE_INTEGRATION_TREE"],
    )
    evidence: dict[str, object] = {
        "QUALIFICATION_ROUTE_SCHEMA": ROUTE_SCHEMA,
        "TARGET_PR_NUMBER": number,
        "TARGET_PR_STATE": pr["state"],
        "TARGET_PR_MERGED": pr["merged"],
        "TARGET_PR_BASE_REF": pr["base_ref"],
        "TARGET_PR_EVENT_BASE_SHA": pr["event_base_sha"],
        "TARGET_PR_HEAD_REPOSITORY": pr["head_repository"],
        "TARGET_PR_HEAD_SHA": expected_head,
        "TARGET_PR_HEAD_TREE": head_tree,
        "PR_EVENT_BASE_SHA": pr["event_base_sha"],
        "PR_EFFECTIVE_BASE_SHA": effective_base,
        "PR_EFFECTIVE_BASE_TREE": effective_base_tree,
        **synthetic,
        "PR_EFFECTIVE_INTEGRATION_BINDING": binding["PR_EFFECTIVE_INTEGRATION_BINDING"],
        "PR_HEAD_IDENTITY_BINDING": binding["PR_HEAD_PARENT_BINDING"],
        "PR_EFFECTIVE_BASE_BINDING": binding["EFFECTIVE_BASE_ON_CANONICAL_MAIN_LINEAGE"],
        "PR_EVENT_BASE_ANCESTRY": binding["EVENT_BASE_IS_ANCESTOR_OF_EFFECTIVE_BASE"],
        **checkout,
        "REMOTE_REF_MUTATION_COUNT": 0,
        "TARGET_PR_MUTATION_COUNT": 0,
    }
    _write_evidence(Path(args.evidence_path), evidence)
    _print_evidence(evidence)
    return 0


def finalize(args: argparse.Namespace) -> int:
    path = Path(args.evidence_path)
    evidence = json.loads(path.read_text(encoding="utf-8"))
    qualified_base = _require_sha(evidence.get("PR_EFFECTIVE_BASE_SHA"), "qualified_base_sha")
    final_main, final_tree = fetch_effective_base(args.repo)
    evidence["POSTQUAL_FINAL_MAIN_SHA"] = final_main
    evidence["POSTQUAL_FINAL_MAIN_TREE"] = final_tree
    try:
        require_final_main_unchanged(qualified_base_sha=qualified_base, final_main_sha=final_main)
    except RequalificationError:
        evidence["OWNER_READINESS_FINAL_MAIN_DRIFT"] = "FAIL"
        _write_evidence(path, evidence)
        _print_evidence(evidence)
        raise
    evidence["OWNER_READINESS_FINAL_MAIN_DRIFT"] = "PASS"
    _write_evidence(path, evidence)
    _print_evidence(evidence)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--repo", default=".")
    prep.add_argument("--repository", required=True)
    prep.add_argument("--pr-number", required=True)
    prep.add_argument("--expected-pr-head-sha", required=True)
    prep.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    prep.add_argument("--evidence-path", default="pr-effective-integration-qualification.json")
    final = sub.add_parser("finalize")
    final.add_argument("--repo", default=".")
    final.add_argument("--evidence-path", default="pr-effective-integration-qualification.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        return prepare(args)
    if args.command == "finalize":
        return finalize(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
