from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

from validate_repository import (
    REQUIRED_BRANCH_HYGIENE_MARKERS,
    validate_branch_hygiene_policy,
    validate_root_layout,
)


class RepositoryExecutionSubstrateGovernanceTests(unittest.TestCase):

    def test_codespace_fallback_and_mandatory_branch_hygiene_markers_are_required(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        validate_branch_hygiene_policy(agents)
        for marker in REQUIRED_BRANCH_HYGIENE_MARKERS:
            self.assertIn(marker, agents)
        self.assertIn(
            "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_EXISTING_AUTHORIZED_CODESPACE_OR_RECONNECT_TRANSPORT",
            agents,
        )
        self.assertIn("OWNER_COMMAND_RELAY_AFTER_RESTORABLE_CODESPACE_OFFLINE=FORBIDDEN", agents)

    def test_optional_cleanup_semantics_are_rejected(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        weakened = agents + "\nSAFE_MERGED_TASK_BRANCH_CLEANUP_ALLOWED=true\n"
        with self.assertRaises(RuntimeError):
            validate_branch_hygiene_policy(weakened)

    def test_branch_hygiene_critical_semantics_fail_closed_when_removed(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        critical = (
            "POSTMERGE_BRANCH_HYGIENE_TERMINAL_GATE=REQUIRED",
            "SAFE_MERGED_TASK_BRANCH_DELETE_REQUIRED=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_EXACT_HEAD_IDENTITY=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_NO_OPEN_DEPENDENT_PR=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_NO_ACTIVE_WORKTREE_DEPENDENCY=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_REMOTE_READBACK=true",
            "KEEP_REMOTE_BRANCH_REQUIRES_EXPLICIT_REASON=true",
            "UNMERGED_OR_AMBIGUOUS_BRANCH_DELETE=FORBIDDEN",
            "LOCAL_TASK_WORKTREE_AND_REF_CLASSIFICATION_REQUIRED=true",
            "TASK_TERMINAL_COMPLETE_REQUIRES_POSTMERGE_BRANCH_HYGIENE_RESOLUTION=true",
            "AIFE_F5C_C9_GENERIC_HYGIENE_KEEP_REASON=EXPLICIT_REPOSITORY_HARD_KEEP",
        )
        for marker in critical:
            with self.subTest(marker=marker):
                weakened = agents.replace(marker, "__REMOVED_REQUIRED_SEMANTIC__", 1)
                with self.assertRaises(RuntimeError):
                    validate_branch_hygiene_policy(weakened)

    def test_aife_f5c_c9_hard_keep_targets_are_machine_required(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        targets = (
            "agent/aife/server-data-foundation-wip",
            "agent/market-data/raw-transfer-physical-route-aife-portability-design-r01",
            "__tmp_noop_should_not_create__",
            "__tmp_noop2__",
            "/tmp/f5c-c9-*",
        )
        for target in targets:
            self.assertIn(target, agents)
            weakened = agents.replace(target, "__REMOVED_HARD_KEEP_TARGET__", 1)
            with self.assertRaises(RuntimeError):
                validate_branch_hygiene_policy(weakened)

    def test_native_routing_health_and_parallel_worktree_policy(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("NATIVE_TOOL_ROUTING_REQUIRED=true", agents)
        self.assertIn("GITHUB_ONLY_WORK_MAY_CONTINUE_WHEN_REMOTE_TERMINAL_UNAVAILABLE=true", agents)
        self.assertIn("REMOTE_EXECUTION_HEALTH_GATE=DEVICE_ONLINE+PING+TRIVIAL_START_PROCESS", agents)
        self.assertIn("REMOTE_DEVICE_FALSE_HEALTHY_CLASS=ONLINE_PING_PASS_EXECUTION_PROBE_FAIL", agents)
        self.assertIn("ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_CODESPACE=true", agents)
        self.assertIn("PARALLEL_MUTATION_SAME_WORKTREE=FORBIDDEN", agents)
        self.assertIn("PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE=true", agents)

    def test_linked_worktree_gitfile_is_vcs_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            for name in (".gitignore", ".gitmessage.txt", "AGENTS.md", "README.md", "bridge-contract.json"):
                (root / name).write_text("fixture\n", encoding="utf-8")
            (root / ".git").write_text("gitdir: /tmp/example/.git/worktrees/fixture\n", encoding="utf-8")
            for name in (
                ".github", "analytics", "archive", "contracts", "data", "derivatives", "docs", "events",
                "history", "liquidity", "options", "schema", "src", "tests", "tools",
            ):
                (root / name).mkdir()

            validate_root_layout(root)


    def test_remote_device_agent_bootstrap_command_is_bounded(self):
        agents = (ROOT / "AGENTS.md").read_text()
        self.assertIn("REMOTE_DEVICE_AGENT_OFFLINE_OWNER_FALLBACK=RUN_SINGLE_DEVICE_AGENT_START_COMMAND", agents)
        self.assertIn("REMOTE_DEVICE_AGENT_START_COMMAND=npx @wonderwhy-er/desktop-commander@latest remote", agents)
        self.assertIn("OWNER_MANUAL_COMMAND_EXCEPTION_SCOPE=REMOTE_DEVICE_AGENT_BOOTSTRAP_ONLY", agents)
        self.assertIn("После execution probe PASS owner больше не выполняет repository-команды", agents)

if __name__ == "__main__":
    unittest.main()
