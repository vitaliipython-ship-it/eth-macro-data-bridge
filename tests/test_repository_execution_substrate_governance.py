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
        )
        for marker in required:
            self.assertIn(marker, agents)

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
        self.assertIn("После device `online` owner больше не выполняет repository-команды", agents)

if __name__ == "__main__":
    unittest.main()
