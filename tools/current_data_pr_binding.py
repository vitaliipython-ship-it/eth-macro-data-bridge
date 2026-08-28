#!/usr/bin/env python3
"""Fail-closed identity proof for Fresh Current pull-request synthetic merges."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Sequence


class BindingError(RuntimeError):
    """Raised when the synthetic PR identity cannot be proven."""


def _git(repo: Path | str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise BindingError(f"git {' '.join(args)} failed: {detail}")
    return result


def _parents(repo: Path | str, commit_sha: str) -> list[str]:
    line = _git(repo, "show", "-s", "--format=%P", commit_sha).stdout.strip()
    return line.split() if line else []


def _is_ancestor(repo: Path | str, older: str, newer: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def _is_on_first_parent_lineage(repo: Path | str, candidate: str, current_main: str) -> bool:
    if candidate == current_main:
        return True
    rows = _git(repo, "rev-list", "--first-parent", current_main).stdout.splitlines()
    return candidate in rows


def verify_binding(
    *,
    repo: Path | str,
    event_base_sha: str,
    expected_pr_head_sha: str,
    synthetic_sha: str,
    current_main_sha: str,
    current_pr_head_sha: str,
) -> dict[str, str]:
    """Prove a two-parent synthetic merge while allowing monotonic main drift."""
    parents = _parents(repo, synthetic_sha)
    if len(parents) != 2:
        raise BindingError(f"synthetic parent count must be 2, got {len(parents)}")

    effective_base_sha, synthetic_pr_head_sha = parents
    if synthetic_pr_head_sha != expected_pr_head_sha:
        raise BindingError("synthetic parent2 does not match exact expected PR head")
    if current_pr_head_sha != expected_pr_head_sha:
        raise BindingError("remote PR branch head changed during qualification")
    if not _is_ancestor(repo, event_base_sha, effective_base_sha):
        raise BindingError("event base is not ancestor-or-equal of effective synthetic base")
    if not _is_ancestor(repo, effective_base_sha, current_main_sha):
        raise BindingError("effective synthetic base is not ancestor-or-equal of current main")
    if not _is_on_first_parent_lineage(repo, effective_base_sha, current_main_sha):
        raise BindingError("effective synthetic base is not on canonical main first-parent lineage")

    synthetic_tree = _git(repo, "rev-parse", f"{synthetic_sha}^{{tree}}").stdout.strip()
    return {
        "EVENT_BASE_SHA": event_base_sha,
        "EFFECTIVE_SYNTHETIC_BASE_SHA": effective_base_sha,
        "CURRENT_MAIN_SHA": current_main_sha,
        "PR_HEAD_SHA": expected_pr_head_sha,
        "SYNTHETIC_SHA": synthetic_sha,
        "SYNTHETIC_TREE": synthetic_tree,
        "SYNTHETIC_PARENT_1": effective_base_sha,
        "SYNTHETIC_PARENT_2": synthetic_pr_head_sha,
        "EVENT_BASE_IS_ANCESTOR_OF_EFFECTIVE_BASE": "YES",
        "EFFECTIVE_BASE_ON_CANONICAL_MAIN_LINEAGE": "YES",
        "PR_HEAD_PARENT_BINDING": "PASS",
        "PR_EFFECTIVE_INTEGRATION_BINDING": "PASS",
        "PHYSICAL_IDENTITY_PROOF": "PASS",
    }


def require_no_final_main_drift(*, qualified_main_sha: str, final_main_sha: str) -> None:
    """Fail owner-readiness if canonical main moved after qualification."""
    if qualified_main_sha != final_main_sha:
        raise BindingError(
            f"canonical main drifted after qualification: {qualified_main_sha} -> {final_main_sha}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--repo", default=".")
    verify.add_argument("--event-base", required=True)
    verify.add_argument("--expected-pr-head", required=True)
    verify.add_argument("--synthetic-sha", required=True)
    verify.add_argument("--current-main-sha", required=True)
    verify.add_argument("--current-pr-head", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify":
        proof = verify_binding(
            repo=args.repo,
            event_base_sha=args.event_base,
            expected_pr_head_sha=args.expected_pr_head,
            synthetic_sha=args.synthetic_sha,
            current_main_sha=args.current_main_sha,
            current_pr_head_sha=args.current_pr_head,
        )
        for key, value in proof.items():
            print(f"{key}={value}")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
