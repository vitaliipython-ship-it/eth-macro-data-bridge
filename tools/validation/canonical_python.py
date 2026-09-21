from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PATHS = (
    ROOT,
    ROOT / "src",
    ROOT / "tools",
    ROOT / "tools" / "deep_history",
)


def configure() -> None:
    canonical = [str(path) for path in CANONICAL_PATHS]
    remainder = [entry for entry in sys.path if entry not in canonical]
    sys.path[:] = canonical + remainder
    os.environ["PYTHONPATH"] = os.pathsep.join(canonical)


def repository_script(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit("canonical runner only executes repository-local scripts") from exc
    if not path.is_file():
        raise SystemExit(f"repository script does not exist: {path}")
    return path


def main() -> None:
    configure()
    args = sys.argv[1:]
    if not args:
        raise SystemExit("usage: canonical_python.py [-m module|-c code|script] [args...]")
    if args[0] == "-m":
        if len(args) < 2:
            raise SystemExit("-m requires a module name")
        module = args[1]
        sys.argv = [module, *args[2:]]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return
    if args[0] == "-c":
        if len(args) < 2:
            raise SystemExit("-c requires code")
        sys.argv = ["-c", *args[2:]]
        namespace = {"__name__": "__main__", "__file__": "<canonical-python>"}
        exec(compile(args[1], "<canonical-python>", "exec"), namespace, namespace)
        return
    script = repository_script(args[0])
    sys.argv = [str(script), *args[1:]]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
