from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from . import _history_access_v1 as _v1
    sys.modules.setdefault("_history_access_v1", _v1)
    from . import history_access_v2 as _v2
except ImportError:
    import _history_access_v1 as _v1
    import history_access_v2 as _v2

# Preserve the complete D6 import surface for existing consumers. V2 is parsed and
# materialized only when the ResolutionPlan itself carries the v2 discriminator.
for _name, _value in vars(_v1).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


def materialize_resolution_plan(
    plan: dict,
    *,
    root: Path = _v1.ROOT,
    cache_dir: Path | None = None,
    mode: str = "strict",
    opener=_v1.urllib.request.urlopen,
):
    coverage = plan.get("series", {}).get("coverage_semantics", "FIXED_GRID")
    if coverage != "TRADES_ONLY_SPARSE":
        return _v1.materialize_resolution_plan(
            plan,
            root=root,
            cache_dir=cache_dir,
            mode=mode,
            opener=opener,
        )

    rows, diagnostics = _v1.materialize_resolution_plan(
        plan,
        root=root,
        cache_dir=cache_dir,
        mode="permissive",
        opener=opener,
    )
    duplicates = diagnostics["duplicates"]
    if duplicates and mode == "strict":
        raise _v1.HistoryAccessError(
            "DUPLICATE_TIMESTAMP",
            f"duplicate timestamps: {diagnostics['duplicate_timestamps_ms'][:5]}",
        )
    provider_no_trade = list(diagnostics["missing_intervals_ms"])
    diagnostics["coverage_semantics"] = coverage
    diagnostics["provider_no_trade_intervals_count"] = len(provider_no_trade)
    diagnostics["provider_no_trade_intervals_preview_ms"] = provider_no_trade[:20]
    diagnostics["missing_intervals_ms"] = []
    diagnostics["gap_count"] = 0
    diagnostics["status"] = "DEGRADED" if duplicates else "PASS"
    return rows, diagnostics


def read_resolution_plan_any(path: str) -> dict:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan is not valid JSON") from exc
    if plan.get("schema_version") == _v2.PLAN_SCHEMA:
        return _v2.validate_resolution_plan_v2(plan)
    return _v1.validate_resolution_plan(plan)


def materialize_resolution_plan_any(
    plan: dict,
    *,
    cache_dir: Path | None = None,
    mode: str = "strict",
):
    if plan.get("schema_version") == _v2.PLAN_SCHEMA:
        return _v2.materialize_resolution_plan_v2(
            plan,
            root=_v1.ROOT,
            cache_dir=cache_dir,
            mode=mode,
        )
    return materialize_resolution_plan(plan, cache_dir=cache_dir, mode=mode)


def _v2_json_rows(rows: list[dict]) -> str:
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only historical materialization from the canonical ResolutionPlan family"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    slice_cmd = sub.add_parser("slice")
    slice_cmd.add_argument("--plan", required=True, help="ResolutionPlan JSON file, or - for stdin")
    slice_cmd.add_argument("--format", choices=("csv", "json"), default="csv")
    slice_cmd.add_argument("--output", default="-")
    slice_cmd.add_argument("--mode", choices=("strict", "permissive"), default="strict")
    slice_cmd.add_argument("--cache-dir")
    args = parser.parse_args(argv)

    plan = read_resolution_plan_any(args.plan)
    rows, diagnostics = materialize_resolution_plan_any(
        plan,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        mode=args.mode,
    )
    if plan.get("schema_version") == _v2.PLAN_SCHEMA:
        if args.format != "json":
            raise _v2.HistoryAccessV2Error(
                "UNSUPPORTED_FORMAT",
                "ResolutionPlan v2 heterogeneous observations require JSON output in D9.4 candidate mode",
            )
        payload = _v2_json_rows(rows)
    else:
        payload = _v1.rows_to_csv(rows) if args.format == "csv" else _v1.rows_to_json(rows)
    if args.output == "-":
        sys.stdout.write(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    sys.stderr.write(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    try:
        main()
    except _v1.HistoryAccessError as exc:
        print(f"HISTORY_ACCESS={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
