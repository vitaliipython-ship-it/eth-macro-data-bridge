from __future__ import annotations

import argparse
import sys

try:
    from . import _capability_index_v1 as _v1
    sys.modules.setdefault("_capability_index_v1", _v1)
    from . import resolution_v2 as _v2
except ImportError:
    import _capability_index_v1 as _v1
    import resolution_v2 as _v2

# Preserve every existing D6 import surface. V2 is an explicit successor mode of
# this same canonical entrypoint; it does not create a second resolver route.
for _name, _value in vars(_v1).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


def list_capabilities_v2():
    index = _v2.build_index_v2()
    result = []
    for row in index["series"]:
        profile = index["profiles"][row["profile_id"]]
        result.append({
            **row,
            "provider_id": profile["provider_id"],
            "history_mode": profile["history_mode"],
            "availability_status": profile["availability_status"],
            "series_kind": profile["series_kind"],
            "coverage_semantics": profile["coverage_semantics"],
            "finality_policy": profile["finality_policy"],
            "revision_policy": profile["revision_policy"],
            "warm_manifest_path": profile.get("warm_manifest_path"),
            "cold_manifest_path": profile["cold_manifest_path"],
        })
    return result


def describe_capability_v2(series_id: str):
    index = _v2.build_index_v2()
    row, profile, policy = _v2._series_descriptor(index, series_id)
    return {"series": row, "profile": profile, "provider_policy": policy}


def resolve_capability_v2(
    series_id: str,
    start_utc: str,
    end_utc: str,
    cutoff_utc: str | None = None,
    *,
    current_policy: str = "FINALIZED_ONLY",
    qualification_mode: bool = False,
):
    return _v2.resolve_capability_v2(
        series_id,
        start_utc,
        end_utc,
        cutoff_utc,
        current_policy=current_policy,
        qualification_mode=qualification_mode,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic market-data capability index and canonical semantic resolver"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("validate")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--plan-version", choices=("1", "2"), default="1")

    describe = sub.add_parser("describe")
    describe.add_argument("series_id")
    describe.add_argument("--plan-version", choices=("1", "2"), default="1")

    resolve = sub.add_parser("resolve")
    resolve.add_argument("series_id")
    resolve.add_argument("--from", dest="start_utc", required=True)
    resolve.add_argument("--to", dest="end_utc", required=True)
    resolve.add_argument("--cutoff", dest="cutoff_utc")
    resolve.add_argument("--format", choices=("json",), default="json")
    resolve.add_argument("--plan-version", choices=("1", "2"), default="1")
    resolve.add_argument(
        "--current-policy",
        choices=("FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"),
        default="FINALIZED_ONLY",
    )
    resolve.add_argument("--qualification-mode", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "build":
        _v1.write_index()
    elif args.command == "validate":
        _v1.validate_committed()
    elif args.command == "list":
        _v1._print_json(_v1.list_capabilities() if args.plan_version == "1" else list_capabilities_v2())
    elif args.command == "describe":
        value = _v1.describe_capability(args.series_id) if args.plan_version == "1" else describe_capability_v2(args.series_id)
        _v1._print_json(value)
    elif args.plan_version == "1":
        if args.current_policy != "FINALIZED_ONLY" or args.qualification_mode:
            raise RuntimeError("V2_ONLY_RESOLUTION_OPTION")
        _v1._print_json(_v1.resolve_capability(args.series_id, args.start_utc, args.end_utc, args.cutoff_utc))
    else:
        _v1._print_json(
            resolve_capability_v2(
                args.series_id,
                args.start_utc,
                args.end_utc,
                args.cutoff_utc,
                current_policy=args.current_policy,
                qualification_mode=args.qualification_mode,
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CAPABILITY_INDEX=FAIL error={exc}", file=sys.stderr)
        raise
