from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

from validate_repository import validate_root_layout


class RepositoryExecutionSubstrateGovernanceTests(unittest.TestCase):

    def test_codespace_fallback_and_safe_branch_cleanup_markers_are_required(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required = (
            "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_EXISTING_AUTHORIZED_CODESPACE_OR_RECONNECT_TRANSPORT",
            "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_CODESPACE_OFFLINE=FORBIDDEN",
            "SAFE_MERGED_TASK_BRANCH_CLEANUP_ALLOWED=true",
            "DELETE_REMOTE_BRANCH_ONLY_IF_PR_STATE=MERGED",
            "DELETE_REMOTE_BRANCH_REQUIRES_EXACT_HEAD_IDENTITY=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_NO_OPEN_DEPENDENT_PR=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_NON_DEFAULT_NON_PROTECTED_NON_AUTHORITY_BRANCH=true",
            "DELETE_REMOTE_BRANCH_REQUIRES_REMOTE_READBACK=true",
            "UNMERGED_OR_AMBIGUOUS_BRANCH_DELETE=FORBIDDEN",
            "NATIVE_TOOL_ROUTING_REQUIRED=true",
            "GITHUB_CONNECTOR_PREFERRED_FOR_SUPPORTED_GITHUB_API_OPERATIONS=true",
            "DO_NOT_USE_REMOTE_TERMINAL_WHEN_EQUIVALENT_GITHUB_CONNECTOR_ACTION_IS_AVAILABLE=true",
            "GITHUB_ONLY_WORK_MAY_CONTINUE_WHEN_REMOTE_TERMINAL_UNAVAILABLE=true",
            "REMOTE_EXECUTION_HEALTH_GATE=DEVICE_ONLINE+PING+TRIVIAL_START_PROCESS",
            "REMOTE_DEVICE_ONLINE_ALONE_IS_EXECUTION_PROOF=NO",
            "REMOTE_DEVICE_PING_ALONE_IS_EXECUTION_PROOF=NO",
            "REMOTE_DEVICE_FALSE_HEALTHY_CLASS=ONLINE_PING_PASS_EXECUTION_PROBE_FAIL",
            "REMOTE_EXECUTION_SUBSTRATE_AVAILABLE_ONLY_AFTER_EXECUTION_PROBE_PASS=true",
            "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_CODESPACE=true",
            "PARALLEL_CHAT_AGENTS_SAME_DEVICE_ALLOWED=true",
            "OWNER_TERMINAL_PER_AGENT_REQUIRED=NO",
            "PARALLEL_MUTATION_SAME_WORKTREE=FORBIDDEN",
            "PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE=true",
        )
        for marker in required:
            self.assertIn(marker, agents)

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
