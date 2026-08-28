import subprocess
import tempfile
import unittest
from pathlib import Path

from current_data_pr_binding import BindingError, require_no_final_main_drift, verify_binding


class SyntheticPrBindingTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _commit(self, repo: Path, message: str, parent: str | None = None) -> str:
        tree = self._git(repo, "write-tree")
        args = ["commit-tree", tree, "-m", message]
        if parent:
            args.extend(["-p", parent])
        return self._git(repo, *args)

    def _merge_commit(self, repo: Path, first: str, second: str, message: str = "synthetic") -> str:
        tree = self._git(repo, "rev-parse", f"{first}^{{tree}}")
        return self._git(repo, "commit-tree", tree, "-p", first, "-p", second, "-m", message)

    def _repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.name", "qualification")
        self._git(repo, "config", "user.email", "qualification@example.invalid")
        (repo / "seed").write_text("seed\n", encoding="utf-8")
        self._git(repo, "add", "seed")
        base = self._commit(repo, "base")
        return temp, repo, base

    def test_01_no_drift_passes(self):
        temp, repo, base = self._repo()
        with temp:
            pr_head = self._commit(repo, "pr", base)
            synthetic = self._merge_commit(repo, base, pr_head)
            proof = verify_binding(
                repo=repo,
                event_base_sha=base,
                expected_pr_head_sha=pr_head,
                synthetic_sha=synthetic,
                current_main_sha=base,
                current_pr_head_sha=pr_head,
            )
            self.assertEqual(proof["EFFECTIVE_SYNTHETIC_BASE_SHA"], base)
            self.assertEqual(proof["PR_HEAD_PARENT_BINDING"], "PASS")

    def test_02_monotonic_main_drift_passes(self):
        temp, repo, base = self._repo()
        with temp:
            newer_main = self._commit(repo, "newer-main", base)
            pr_head = self._commit(repo, "pr", base)
            synthetic = self._merge_commit(repo, newer_main, pr_head)
            proof = verify_binding(
                repo=repo,
                event_base_sha=base,
                expected_pr_head_sha=pr_head,
                synthetic_sha=synthetic,
                current_main_sha=newer_main,
                current_pr_head_sha=pr_head,
            )
            self.assertEqual(proof["EVENT_BASE_IS_ANCESTOR_OF_EFFECTIVE_BASE"], "YES")
            self.assertEqual(proof["EFFECTIVE_SYNTHETIC_BASE_SHA"], newer_main)

    def test_03_unrelated_base_lineage_fails_closed(self):
        temp, repo, base = self._repo()
        with temp:
            unrelated = self._commit(repo, "unrelated")
            pr_head = self._commit(repo, "pr", base)
            synthetic = self._merge_commit(repo, unrelated, pr_head)
            with self.assertRaises(BindingError):
                verify_binding(
                    repo=repo,
                    event_base_sha=base,
                    expected_pr_head_sha=pr_head,
                    synthetic_sha=synthetic,
                    current_main_sha=unrelated,
                    current_pr_head_sha=pr_head,
                )

    def test_04_wrong_pr_head_parent_fails_closed(self):
        temp, repo, base = self._repo()
        with temp:
            expected_pr_head = self._commit(repo, "expected-pr", base)
            wrong_pr_head = self._commit(repo, "wrong-pr", base)
            synthetic = self._merge_commit(repo, base, wrong_pr_head)
            with self.assertRaises(BindingError):
                verify_binding(
                    repo=repo,
                    event_base_sha=base,
                    expected_pr_head_sha=expected_pr_head,
                    synthetic_sha=synthetic,
                    current_main_sha=base,
                    current_pr_head_sha=expected_pr_head,
                )

    def test_05_invalid_parent_count_fails_closed(self):
        temp, repo, base = self._repo()
        with temp:
            pr_head = self._commit(repo, "pr", base)
            with self.assertRaises(BindingError):
                verify_binding(
                    repo=repo,
                    event_base_sha=base,
                    expected_pr_head_sha=pr_head,
                    synthetic_sha=pr_head,
                    current_main_sha=base,
                    current_pr_head_sha=pr_head,
                )

    def test_06_final_main_drift_blocks_owner_readiness(self):
        require_no_final_main_drift(qualified_main_sha="same", final_main_sha="same")
        with self.assertRaises(BindingError):
            require_no_final_main_drift(qualified_main_sha="before", final_main_sha="after")

    def test_07_remote_pr_head_change_fails_closed(self):
        temp, repo, base = self._repo()
        with temp:
            expected_pr_head = self._commit(repo, "expected-pr", base)
            rebound_pr_head = self._commit(repo, "rebound-pr", expected_pr_head)
            synthetic = self._merge_commit(repo, base, expected_pr_head)
            with self.assertRaises(BindingError):
                verify_binding(
                    repo=repo,
                    event_base_sha=base,
                    expected_pr_head_sha=expected_pr_head,
                    synthetic_sha=synthetic,
                    current_main_sha=base,
                    current_pr_head_sha=rebound_pr_head,
                )


if __name__ == "__main__":
    unittest.main()
