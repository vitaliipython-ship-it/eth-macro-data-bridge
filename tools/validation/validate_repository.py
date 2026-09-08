from __future__ import annotations

from pathlib import Path

from validate_liquidity_g1_durability import validate_g1

ALLOWED_ROOT_FILES = {
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
    for marker in (
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
    ):
        if marker not in agents:
            raise RuntimeError(f"AGENTS execution/branch-cleanup governance marker missing: {marker}")
    for marker in (
        "EXECUTION_SUBSTRATE_DISCOVERY_REQUIRED=true",
        "REMOTE_TERMINAL_IS_GITHUB_AUTHORITY=NO",
        "GITHUB_CONNECTOR_IS_SHELL_AUTHORITY=NO",
        "GH_CLI_AUTH_IS_SEPARATE_CAPABILITY=true",
        "GH_AUTH_STATUS_REQUIRED_BEFORE_GH_DEPENDENT_OPERATIONS=true",
        "NONINTERACTIVE_GIT_FETCH_PROOF_REQUIRED_BEFORE_RELYING_ON_REMOTE_GIT_AUTH=true",
        "TRANSIENT_EXECUTION_IDENTIFIERS_ARE_REPOSITORY_AUTHORITY=NO",
        "CREDENTIALS_OR_TOKENS_MUST_NOT_BE_PERSISTED_IN_REPOSITORY=true",
        "OWNER_MANUAL_COMMAND_RELAY_WHEN_EQUIVALENT_REMOTE_TERMINAL_AVAILABLE=FORBIDDEN",
        "LINKED_WORKTREE_GITFILE_IS_VALID_VCS_METADATA=true",
    ):
        if marker not in agents:
            raise RuntimeError(f"AGENTS execution-substrate marker missing: {marker}")
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
    print("REPOSITORY_STRUCTURE_VALIDATION=PASS")


if __name__ == "__main__":
    main()
