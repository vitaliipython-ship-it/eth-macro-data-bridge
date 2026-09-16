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
    validate_execution_substrate_governance,
    validate_root_layout,
)


class RepositoryExecutionSubstrateGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    def test_canonical_host_neutral_execution_policy_passes(self) -> None:
        validate_execution_substrate_governance(self.agents)

    def test_host_neutral_fallback_and_mandatory_branch_hygiene_markers_are_required(self) -> None:
        validate_branch_hygiene_policy(self.agents)
        for marker in REQUIRED_BRANCH_HYGIENE_MARKERS:
            self.assertIn(marker, self.agents)
        self.assertIn(
            "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_SELECTED_AUTHORIZED_EXECUTION_HOST_OR_RECONNECT_TRANSPORT",
            self.agents,
        )
        self.assertIn("OWNER_COMMAND_RELAY_AFTER_RESTORABLE_EXECUTION_HOST_OFFLINE=FORBIDDEN", self.agents)

    def test_missing_supported_execution_host_classes_fails_closed(self) -> None:
        weakened = self.agents.replace(
            "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST", "", 1
        )
        with self.assertRaisesRegex(RuntimeError, "AUTHORIZED_EXECUTION_HOST_CLASSES"):
            validate_execution_substrate_governance(weakened)

    def test_missing_one_device_agent_per_execution_host_fails_closed(self) -> None:
        weakened = self.agents.replace("ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_EXECUTION_HOST=true", "", 1)
        with self.assertRaisesRegex(RuntimeError, "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_EXECUTION_HOST"):
            validate_execution_substrate_governance(weakened)

    def test_old_codespace_only_generic_markers_are_rejected(self) -> None:
        stale_pairs = (
            (
                "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_EXECUTION_HOST=true",
                "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_CODESPACE=true",
            ),
            (
                "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_SELECTED_AUTHORIZED_EXECUTION_HOST_OR_RECONNECT_TRANSPORT",
                "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_EXISTING_AUTHORIZED_CODESPACE_OR_RECONNECT_TRANSPORT",
            ),
            (
                "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_EXECUTION_HOST_OFFLINE=FORBIDDEN",
                "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_CODESPACE_OFFLINE=FORBIDDEN",
            ),
        )
        for current, stale in stale_pairs:
            with self.subTest(stale=stale):
                weakened = self.agents.replace(current, stale, 1)
                with self.assertRaises(RuntimeError):
                    validate_execution_substrate_governance(weakened)

    def test_missing_host_neutral_remote_terminal_fallback_fails_closed(self) -> None:
        weakened = self.agents.replace(
            "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_SELECTED_AUTHORIZED_EXECUTION_HOST_OR_RECONNECT_TRANSPORT",
            "",
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK"):
            validate_execution_substrate_governance(weakened)

    def test_missing_host_neutral_command_relay_prohibition_fails_closed(self) -> None:
        weakened = self.agents.replace(
            "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_EXECUTION_HOST_OFFLINE=FORBIDDEN", "", 1
        )
        with self.assertRaisesRegex(RuntimeError, "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_EXECUTION_HOST_OFFLINE"):
            validate_execution_substrate_governance(weakened)

    def test_execution_health_gate_removal_fails_closed(self) -> None:
        weakened = self.agents.replace("REMOTE_EXECUTION_HEALTH_GATE=DEVICE_ONLINE+PING+TRIVIAL_START_PROCESS", "", 1)
        with self.assertRaisesRegex(RuntimeError, "REMOTE_EXECUTION_HEALTH_GATE"):
            validate_execution_substrate_governance(weakened)

    def test_dedicated_worktree_invariant_removal_fails_closed(self) -> None:
        weakened = self.agents.replace("PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE=true", "", 1)
        with self.assertRaisesRegex(RuntimeError, "PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE"):
            validate_execution_substrate_governance(weakened)

    def test_codespace_remains_supported_execution_host(self) -> None:
        self.assertIn("AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST", self.agents)
        weakened = self.agents.replace(
            "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST",
            "AUTHORIZED_EXECUTION_HOST_CLASSES=OWNER_AUTHORIZED_LOCAL_HOST",
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "AUTHORIZED_EXECUTION_HOST_CLASSES"):
            validate_execution_substrate_governance(weakened)

    def test_owner_authorized_local_host_is_supported(self) -> None:
        self.assertIn("AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST", self.agents)
        weakened = self.agents.replace(
            "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST",
            "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE",
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "AUTHORIZED_EXECUTION_HOST_CLASSES"):
            validate_execution_substrate_governance(weakened)

    def test_github_shared_repository_authority_is_required(self) -> None:
        weakened = self.agents.replace("GITHUB_SHARED_REPOSITORY_AUTHORITY=true", "", 1)
        with self.assertRaisesRegex(RuntimeError, "GITHUB_SHARED_REPOSITORY_AUTHORITY"):
            validate_execution_substrate_governance(weakened)

    def test_local_clone_is_not_automatic_github_synchronization(self) -> None:
        for marker in (
            "LOCAL_CLONE_IS_EXECUTION_WORKING_COPY=true",
            "LOCAL_FILESYSTEM_AUTOMATIC_GITHUB_SYNC=NO",
            "GIT_FETCH_AUTOMATICALLY_MOVES_CHECKED_OUT_TASK_COMMIT=NO",
        ):
            with self.subTest(marker=marker):
                weakened = self.agents.replace(marker, "", 1)
                with self.assertRaisesRegex(RuntimeError, marker.split("=")[0]):
                    validate_execution_substrate_governance(weakened)

    def test_optional_cleanup_semantics_are_rejected(self) -> None:
        weakened = self.agents + "SAFE_MERGED_TASK_BRANCH_CLEANUP_ALLOWED=true"
        with self.assertRaises(RuntimeError):
            validate_branch_hygiene_policy(weakened)

    def test_branch_hygiene_critical_semantics_fail_closed_when_removed(self) -> None:
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
                weakened = self.agents.replace(marker, "__REMOVED_REQUIRED_SEMANTIC__", 1)
                with self.assertRaises(RuntimeError):
                    validate_branch_hygiene_policy(weakened)

    def test_aife_f5c_c9_hard_keep_targets_are_machine_required(self) -> None:
        targets = (
            "agent/aife/server-data-foundation-wip",
            "agent/market-data/raw-transfer-physical-route-aife-portability-design-r01",
            "__tmp_noop_should_not_create__",
            "__tmp_noop2__",
            "/tmp/f5c-c9-*",
        )
        for target in targets:
            self.assertIn(target, self.agents)
            weakened = self.agents.replace(target, "__REMOVED_HARD_KEEP_TARGET__", 1)
            with self.assertRaises(RuntimeError):
                validate_branch_hygiene_policy(weakened)

    def test_native_routing_health_and_parallel_worktree_policy(self) -> None:
        required = (
            "NATIVE_TOOL_ROUTING_REQUIRED=true",
            "GITHUB_ONLY_WORK_MAY_CONTINUE_WHEN_REMOTE_TERMINAL_UNAVAILABLE=true",
            "REMOTE_EXECUTION_HEALTH_GATE=DEVICE_ONLINE+PING+TRIVIAL_START_PROCESS",
            "REMOTE_DEVICE_FALSE_HEALTHY_CLASS=ONLINE_PING_PASS_EXECUTION_PROBE_FAIL",
            "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST",
            "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_EXECUTION_HOST=true",
            "PARALLEL_MUTATION_SAME_WORKTREE=FORBIDDEN",
            "PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE=true",
        )
        for marker in required:
            self.assertIn(marker, self.agents)
        validate_execution_substrate_governance(self.agents)

    def test_linked_worktree_gitfile_is_vcs_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            for name in (".gitignore", ".gitmessage.txt", "AGENTS.md", "README.md", "bridge-contract.json"):
                (root / name).write_text("fixture", encoding="utf-8")
            (root / ".git").write_text("gitdir: /tmp/example/.git/worktrees/fixture", encoding="utf-8")
            for name in (
                ".github", "analytics", "archive", "contracts", "data", "derivatives", "docs", "events",
                "history", "liquidity", "options", "schema", "src", "tests", "tools",
            ):
                (root / name).mkdir()
            validate_root_layout(root)

    def test_remote_device_agent_bootstrap_command_is_bounded_and_required(self) -> None:
        required = (
            "REMOTE_DEVICE_AGENT_OFFLINE_OWNER_FALLBACK=RUN_SINGLE_DEVICE_AGENT_START_COMMAND",
            "REMOTE_DEVICE_AGENT_START_COMMAND=npx @wonderwhy-er/desktop-commander@latest remote",
            "OWNER_MANUAL_COMMAND_EXCEPTION_SCOPE=REMOTE_DEVICE_AGENT_BOOTSTRAP_ONLY",
        )
        for marker in required:
            self.assertIn(marker, self.agents)
            weakened = self.agents.replace(marker, "", 1)
            with self.assertRaisesRegex(RuntimeError, marker.split("=")[0]):
                validate_execution_substrate_governance(weakened)
        self.assertIn("После execution probe PASS owner больше не выполняет repository-команды", self.agents)


if __name__ == "__main__":
    unittest.main()
