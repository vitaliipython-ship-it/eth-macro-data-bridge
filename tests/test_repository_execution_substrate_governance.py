from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

from validate_repository import validate_root_layout


class RepositoryExecutionSubstrateGovernanceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
