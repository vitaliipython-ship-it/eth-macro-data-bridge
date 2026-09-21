from __future__ import annotations

from pathlib import Path

from validate_liquidity_g1_durability import validate_g1

ALLOWED_ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    ".gitmessage.txt",
    "AGENTS.md",
    "README.md",
    "bridge-contract.json",
}

REQUIRED_ROOT_DIRS = {
    ".github",
    "analytics",
    "archive",
    "contracts",
    "data",
    "derivatives",
    "docs",
    "events",
    "history",
    "liquidity",
    "options",
    "schema",
    "src",
    "tests",
    "tools",
}

STALE_COMMANDS = (
    "python collector.py",
    "python validate.py",
    "python validate_v4.py",
    "python validate_history.py",
    "python consumer_proof.py",
    "python publish_deep_history.py",
    "python qualify_kraken_overlap_policy.py",
)


REQUIRED_BRANCH_HYGIENE_MARKERS = (
    "POSTMERGE_BRANCH_HYGIENE_TERMINAL_GATE=REQUIRED",
    "MERGED_TASK_BRANCH_LIFECYCLE=ENDED",
    "POSTMERGE_BRANCH_HYGIENE_CLASSIFICATION_REQUIRED=true",
    "SAFE_MERGED_TASK_BRANCH_DELETE_REQUIRED=true",
    "SAFE_MERGED_TASK_BRANCH_DELETE_ONLY_IF_ALL_PREDICATES_PASS=true",
    "DELETE_REMOTE_BRANCH_ONLY_IF_PR_STATE=MERGED",
    "DELETE_REMOTE_BRANCH_REQUIRES_EXACT_HEAD_IDENTITY=true",
    "DELETE_REMOTE_BRANCH_REQUIRES_NO_OPEN_DEPENDENT_PR=true",
    "DELETE_REMOTE_BRANCH_REQUIRES_NON_DEFAULT_NON_PROTECTED_NON_AUTHORITY_BRANCH=true",
    "DELETE_REMOTE_BRANCH_REQUIRES_NO_ACTIVE_WORKFLOW_OR_TASK=true",
    "DELETE_REMOTE_BRANCH_REQUIRES_NO_ACTIVE_WORKTREE_DEPENDENCY=true",
    "DELETE_REMOTE_BRANCH_REQUIRES_REMOTE_READBACK=true",
    "KEEP_REMOTE_BRANCH_REQUIRES_EXPLICIT_REASON=true",
    "UNMERGED_OR_AMBIGUOUS_BRANCH_DELETE=FORBIDDEN",
    "LOCAL_TASK_WORKTREE_AND_REF_CLASSIFICATION_REQUIRED=true",
    "LOCAL_TASK_STATE_CLEANUP_REQUIRED_WHEN_SAFE=true",
    "TASK_TERMINAL_COMPLETE_REQUIRES_POSTMERGE_BRANCH_HYGIENE_RESOLUTION=true",
    "GITHUB_DELETE_BRANCH_ON_MERGE_IS_NOT_CANONICAL_HYGIENE_ENFORCEMENT=true",
    "POSTMERGE_BRANCH_HYGIENE_KEEP_REASONS=OPEN_PR_DEPENDENCY|ACTIVE_DOWNSTREAM_DEPENDENCY|DEFAULT_BRANCH|PROTECTED_BRANCH|DURABLE_AUTHORITY_BRANCH|ACTIVE_WORKFLOW|ACTIVE_WORKTREE_OR_TASK|DIRTY_LOCAL_WORKTREE|UNMERGED_OR_AMBIGUOUS_STATE|BRANCH_MOVED_AFTER_MERGE|EXPLICIT_REPOSITORY_HARD_KEEP|TRANSPORT_UNAVAILABLE_FAIL_CLOSED",
    "AIFE_F5C_C9_GENERIC_HYGIENE_CLASSIFICATION=KEEP_REQUIRED_WITH_REASON",
    "AIFE_F5C_C9_GENERIC_HYGIENE_KEEP_REASON=EXPLICIT_REPOSITORY_HARD_KEEP",
    "EXPLICIT_REPOSITORY_HARD_KEEP_BRANCHES=agent/aife/server-data-foundation-wip|agent/market-data/raw-transfer-physical-route-aife-portability-design-r01|__tmp_noop_should_not_create__|__tmp_noop2__",
    "EXPLICIT_REPOSITORY_HARD_KEEP_WORKTREE_GLOB=/tmp/f5c-c9-*",
    "PROVEN_AIFE_F5C_C9_PROVENANCE_REQUIRES_HARD_KEEP=true",
    "REMOTE_BRANCH_HYGIENE_RESOLVED=BRANCH_DELETED_AND_ABSENCE_PROVEN|BRANCH_KEPT_WITH_PHYSICALLY_PROVEN_REASON",
    "TASK_TERMINAL_COMPLETE_FORMULA=POST_MERGE_QUALIFICATION_PASS+REMOTE_BRANCH_HYGIENE_RESOLVED+LOCAL_TASK_STATE_CLASSIFIED+REQUIRED_READBACK_COMPLETE",
)

FORBIDDEN_BRANCH_HYGIENE_MARKERS = (
    "SAFE_MERGED_TASK_BRANCH_CLEANUP_ALLOWED=true",
    "POSTMERGE_BRANCH_HYGIENE_TERMINAL_GATE=OPTIONAL",
)

REQUIRED_EXECUTION_GOVERNANCE_MARKERS = (
    "EXECUTION_SUBSTRATE_DISCOVERY_REQUIRED=true",
    "REMOTE_TERMINAL_IS_GITHUB_AUTHORITY=NO",
    "GITHUB_CONNECTOR_IS_SHELL_AUTHORITY=NO",
    "NATIVE_TOOL_ROUTING_REQUIRED=true",
    "GITHUB_CONNECTOR_PREFERRED_FOR_SUPPORTED_GITHUB_API_OPERATIONS=true",
    "DO_NOT_USE_REMOTE_TERMINAL_WHEN_EQUIVALENT_GITHUB_CONNECTOR_ACTION_IS_AVAILABLE=true",
    "GITHUB_ONLY_WORK_MAY_CONTINUE_WHEN_REMOTE_TERMINAL_UNAVAILABLE=true",
    "REMOTE_EXECUTION_HEALTH_GATE=DEVICE_ONLINE+PING+TRIVIAL_START_PROCESS",
    "REMOTE_DEVICE_ONLINE_ALONE_IS_EXECUTION_PROOF=NO",
    "REMOTE_DEVICE_PING_ALONE_IS_EXECUTION_PROOF=NO",
    "REMOTE_DEVICE_FALSE_HEALTHY_CLASS=ONLINE_PING_PASS_EXECUTION_PROBE_FAIL",
    "REMOTE_EXECUTION_SUBSTRATE_AVAILABLE_ONLY_AFTER_EXECUTION_PROBE_PASS=true",
    "AUTHORIZED_EXECUTION_HOST_CLASSES=CODESPACE,OWNER_AUTHORIZED_LOCAL_HOST",
    "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_EXECUTION_HOST=true",
    "PARALLEL_CHAT_AGENTS_SAME_DEVICE_ALLOWED=true",
    "OWNER_TERMINAL_PER_AGENT_REQUIRED=NO",
    "PARALLEL_MUTATION_SAME_WORKTREE=FORBIDDEN",
    "PARALLEL_MUTATION_TASK_REQUIRES_DEDICATED_WORKTREE=true",
    "GITHUB_SHARED_REPOSITORY_AUTHORITY=true",
    "LOCAL_CLONE_IS_EXECUTION_WORKING_COPY=true",
    "LOCAL_FILESYSTEM_AUTOMATIC_GITHUB_SYNC=NO",
    "FRESH_ORIGIN_MAIN_REQUIRED_BEFORE_NEW_TASK_WORKTREE=true",
    "GIT_FETCH_UPDATES_REMOTE_TRACKING_REFS_ONLY=true",
    "GIT_FETCH_AUTOMATICALLY_MOVES_CHECKED_OUT_TASK_COMMIT=NO",
    "TASK_BRANCH_PUSH_IS_OWNER_INTEGRATION=NO",
    "PR_CREATION_IS_OWNER_INTEGRATION=NO",
    "OWNER_MERGE_AUTOMATICALLY_MOVES_LOCAL_CHECKOUT=NO",
    "GH_CLI_AUTH_IS_SEPARATE_CAPABILITY=true",
    "GH_AUTH_STATUS_REQUIRED_BEFORE_GH_DEPENDENT_OPERATIONS=true",
    "NONINTERACTIVE_GIT_FETCH_PROOF_REQUIRED_BEFORE_RELYING_ON_REMOTE_GIT_AUTH=true",
    "TRANSIENT_EXECUTION_IDENTIFIERS_ARE_REPOSITORY_AUTHORITY=NO",
    "CREDENTIALS_OR_TOKENS_MUST_NOT_BE_PERSISTED_IN_REPOSITORY=true",
    "OWNER_MANUAL_COMMAND_RELAY_WHEN_EQUIVALENT_REMOTE_TERMINAL_AVAILABLE=FORBIDDEN",
    "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_SELECTED_AUTHORIZED_EXECUTION_HOST_OR_RECONNECT_TRANSPORT",
    "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_EXECUTION_HOST_OFFLINE=FORBIDDEN",
    "REMOTE_DEVICE_AGENT_OFFLINE_OWNER_FALLBACK=RUN_SINGLE_DEVICE_AGENT_START_COMMAND",
    "REMOTE_DEVICE_AGENT_START_COMMAND=npx @wonderwhy-er/desktop-commander@latest remote",
    "OWNER_MANUAL_COMMAND_EXCEPTION_SCOPE=REMOTE_DEVICE_AGENT_BOOTSTRAP_ONLY",
    "LINKED_WORKTREE_GITFILE_IS_VALID_VCS_METADATA=true",
)

FORBIDDEN_EXECUTION_GOVERNANCE_MARKERS = (
    "ONE_REMOTE_DEVICE_AGENT_PROCESS_PER_" + "CODESPACE=true",
    "REMOTE_TERMINAL_OFFLINE_OWNER_FALLBACK=START_OR_RESUME_EXISTING_AUTHORIZED_" + "CODESPACE_OR_RECONNECT_TRANSPORT",
    "OWNER_COMMAND_RELAY_AFTER_RESTORABLE_" + "CODESPACE_OFFLINE=FORBIDDEN",
    "CODESPACE_IS_ONLY_GENERIC_EXECUTION_HOST=true",
)


def validate_execution_substrate_governance(agents: str) -> None:
    missing = [marker for marker in REQUIRED_EXECUTION_GOVERNANCE_MARKERS if marker not in agents]
    if missing:
        raise RuntimeError(f"AGENTS execution governance marker missing: {missing}")
    forbidden = [marker for marker in FORBIDDEN_EXECUTION_GOVERNANCE_MARKERS if marker in agents]
    if forbidden:
        raise RuntimeError(f"AGENTS stale/unsafe execution governance marker present: {forbidden}")



def validate_branch_hygiene_policy(agents: str) -> None:
    missing = [marker for marker in REQUIRED_BRANCH_HYGIENE_MARKERS if marker not in agents]
    if missing:
        raise RuntimeError(f"AGENTS mandatory branch-hygiene marker missing: {missing}")

    forbidden = [marker for marker in FORBIDDEN_BRANCH_HYGIENE_MARKERS if marker in agents]
    if forbidden:
        raise RuntimeError(f"AGENTS optional/unsafe branch-hygiene marker present: {forbidden}")


def validate_root_layout(root: Path) -> None:
    root_files = {path.name for path in root.iterdir() if path.is_file() and path.name != ".git"}
    unexpected = sorted(root_files - ALLOWED_ROOT_FILES)
    missing_files = sorted(ALLOWED_ROOT_FILES - root_files)
    if unexpected or missing_files:
        raise RuntimeError(f"root file policy mismatch unexpected={unexpected} missing={missing_files}")

    root_dirs = {path.name for path in root.iterdir() if path.is_dir() and path.name != ".git"}
    missing_dirs = sorted(REQUIRED_ROOT_DIRS - root_dirs)
    if missing_dirs:
        raise RuntimeError(f"required repository directories missing: {missing_dirs}")

    if list(root.glob("*.py")):
        raise RuntimeError("Python files are forbidden in repository root")


def main() -> None:
    root = Path(".")
    validate_root_layout(root)

    readme = Path("README.md").read_text()
    agents = Path("AGENTS.md").read_text()
    template = Path(".gitmessage.txt").read_text()

    if "Канонический язык" not in readme or "русский" not in readme.lower():
        raise RuntimeError("README does not declare Russian documentation policy")
    if "Канонический язык" not in agents or "русский" not in agents.lower():
        raise RuntimeError("AGENTS does not declare Russian repository language")
    validate_branch_hygiene_policy(agents)
    validate_execution_substrate_governance(agents)
    for marker in ("RU:", "EN:", "Validation / Проверка:"):
        if marker not in template:
            raise RuntimeError(f"commit template marker missing: {marker}")

    if Path("provider-contracts.json").exists() or not Path("contracts/provider-contracts.json").exists():
        raise RuntimeError("provider contracts are not in canonical contracts/ location")
    if Path("KRAKEN_CVD_SEMANTICS.md").exists() or not Path("docs/semantics/kraken-futures-cvd.md").exists():
        raise RuntimeError("Kraken CVD semantics are not in canonical docs/semantics location")

    workflows = "\n".join(path.read_text() for path in Path(".github/workflows").glob("*.yml"))
    stale = [command for command in STALE_COMMANDS if command in workflows]
    if stale:
        raise RuntimeError(f"workflow still references removed root entrypoints: {stale}")

    validate_g1(root)

    print("ROOT_LAYOUT=PASS")
    print("ROOT_PYTHON_FILE_COUNT=0")
    print("REPOSITORY_LANGUAGE_POLICY=RUSSIAN")
    print("COMMIT_TEMPLATE_BILINGUAL=PASS")
    print("PROVIDER_CONTRACT_LOCATION=PASS")
    print("SEMANTICS_DOC_LOCATION=PASS")
    print("STALE_ROOT_ENTRYPOINTS=0")
    print("G1_DURABILITY_VALIDATION=PASS")
    print("POSTMERGE_BRANCH_HYGIENE_POLICY_VALIDATION=PASS")
    print("REPOSITORY_STRUCTURE_VALIDATION=PASS")


if __name__ == "__main__":
    main()
