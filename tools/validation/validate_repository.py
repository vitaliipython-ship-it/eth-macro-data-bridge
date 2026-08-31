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


def main() -> None:
    root = Path(".")
    root_files = {path.name for path in root.iterdir() if path.is_file()}
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

    readme = Path("README.md").read_text()
    agents = Path("AGENTS.md").read_text()
    template = Path(".gitmessage.txt").read_text()

    if "Канонический язык" not in readme or "русский" not in readme.lower():
        raise RuntimeError("README does not declare Russian documentation policy")
    if "Канонический язык" not in agents or "русский" not in agents.lower():
        raise RuntimeError("AGENTS does not declare Russian repository language")
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
