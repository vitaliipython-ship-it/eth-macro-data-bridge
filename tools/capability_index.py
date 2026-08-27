from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from . import _capability_index_v1 as _v1
    sys.modules.setdefault("_capability_index_v1", _v1)
    from . import resolution_v2 as _v2
    sys.modules.setdefault("resolution_v2", _v2)
    from . import publication_control_v2 as _publication_v2
    from .current_tail_admission import bind_validated_tail
except ImportError:
    import _capability_index_v1 as _v1
    import resolution_v2 as _v2
    import publication_control_v2 as _publication_v2
    from current_tail_admission import bind_validated_tail

CURRENT_TAIL_ROOT_ENV = "ETH_MACRO_VALIDATED_CURRENT_TAIL_ROOT"

# Preserve the existing module-level names, including mutable ROOT/INDEX_PATH/
# SCHEMA_PATH used by the D6 deterministic fixture harness.
for _name, _value in vars(_v1).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


def _sync_v1_context() -> None:
    _v1.ROOT = globals()["ROOT"]
    _v1.INDEX_PATH = globals()["INDEX_PATH"]
    _v1.SCHEMA_PATH = globals()["SCHEMA_PATH"]


def build_index():
    _sync_v1_context()
    return _v1.build_index()


def validate_shape(index):
    _sync_v1_context()
    return _v1.validate_shape(index)


def validate_committed():
    _sync_v1_context()
    return _v1.validate_committed()


def write_index():
    _sync_v1_context()
    return _v1.write_index()


def list_capabilities():
    _sync_v1_context()
    return _v1.list_capabilities()


def describe_capability(series_id: str):
    _sync_v1_context()
    return _v1.describe_capability(series_id)


def _format_utc_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _durable_latest_end(profile: dict, row: dict, cutoff_ms: int | None, step: int) -> int | None:
    cold_assets, _release = _v1._cold_catalog(profile, row, cutoff_ms)
    warm_resources = _v1._derived_warm_catalog(profile, row, cutoff_ms)
    ends = [int(item["last_timestamp"]) + step for item in cold_assets]
    ends.extend(int(item["last_timestamp"]) + step for item in warm_resources)
    return max(ends) if ends else None


def _mixed_plan_from_validated_tail(
    series_id: str,
    start_utc: str,
    end_utc: str,
    cutoff_utc: str | None,
    *,
    artifact_root: Path,
):
    index = _v1._committed_index()
    row, profile, _policy = _v1._series_descriptor(index, series_id)
    start_ms = _v1._parse_utc_ms(start_utc)
    end_ms = _v1._parse_utc_ms(end_utc)
    cutoff_ms = _v1._parse_utc_ms(cutoff_utc) if cutoff_utc else None
    if start_ms >= end_ms:
        raise RuntimeError("INVALID_TIME_RANGE")
    if cutoff_ms is not None and end_ms > cutoff_ms:
        raise RuntimeError("POINT_IN_TIME_RANGE_EXCEEDS_CUTOFF")
    step = _v1._interval_ms(row, profile)
    if row["series"] != "ohlcv" or not isinstance(step, int):
        raise RuntimeError(f"CURRENT_TAIL_UNSUPPORTED_SERIES: {series_id}")
    alignment = min(step, 86400000)
    if start_ms % alignment or end_ms % alignment:
        raise RuntimeError("UNALIGNED_OHLCV_RANGE")

    descriptor = bind_validated_tail(
        Path(artifact_root),
        series_id=series_id,
        interval_ms=step,
        cutoff_ms=cutoff_ms,
        repository_root=Path(globals()["ROOT"]),
    )
    durable_end = _durable_latest_end(profile, row, cutoff_ms, step)
    prefix_end = min(end_ms, durable_end) if durable_end is not None else start_ms
    prefix_end = max(start_ms, prefix_end)
    durable_segments: list[dict] = []
    if prefix_end > start_ms:
        prefix = _v1.resolve_capability(
            series_id,
            start_utc,
            _format_utc_ms(prefix_end),
            cutoff_utc,
        )
        durable_segments = list(prefix["segments"])
        authority = dict(prefix["authority"])
        series = dict(prefix["series"])
    else:
        authority = {
            "route_policy": index["authority"]["route_policy"],
            "capability_index": "history/capability-index.json",
            "cold_manifest": profile["cold_manifest_path"],
            "hot_manifest": profile["hot_manifest_path"],
        }
        series = {
            **row,
            "provider_id": profile["provider_id"],
            "source_provider": profile["source_provider"],
            "history_mode": profile["history_mode"],
            "availability_status": profile["availability_status"],
            "interval_ms": step,
        }

    suffix_start = prefix_end
    tail_left = max(start_ms, int(descriptor["first_timestamp_ms"]))
    tail_right = min(end_ms, int(descriptor["finalized_cutoff_ms"]))
    if tail_left > suffix_start or tail_right < end_ms:
        raise RuntimeError(
            f"HISTORY_NOT_FOUND: validated current tail cannot cover suffix {suffix_start}->{end_ms}"
        )
    tail_segment = {
        "segment_id": f"current:{descriptor['generation_id'][:16]}:{descriptor['sha256'][:16]}",
        "storage": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "source_manifest_path": "fresh-current-generation/1.0.0",
        "resource_path": descriptor["resource_path"],
        "sha256": descriptor["sha256"],
        "size_bytes": descriptor["size_bytes"],
        "first_timestamp_ms": descriptor["first_timestamp_ms"],
        "last_timestamp_ms": descriptor["last_timestamp_ms"],
        "read_start_ms": tail_left,
        "read_end_ms": tail_right,
        "source_provider": profile["source_provider"],
        "instrument": row["instrument"],
        "source_interval_or_metric": row["source_interval_or_metric"],
        "authority_class": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "current_tail": descriptor,
    }
    segments = sorted(
        durable_segments + [tail_segment],
        key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"]),
    )
    _v1._coverage_check(segments, start_ms, end_ms)
    authority["validated_current_tail"] = "fresh-current-generation/1.0.0"
    plan = {
        "schema_version": _v1.PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": authority,
        "request": {
            "series_id": series_id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "cutoff_ms": cutoff_ms,
        },
        "series": series,
        "segments": segments,
    }
    plan["plan_sha256"] = hashlib.sha256(_v1.compact(plan)).hexdigest()
    return plan


def resolve_capability(series_id: str, start_utc: str, end_utc: str, cutoff_utc: str | None = None):
    _sync_v1_context()
    try:
        return _v1.resolve_capability(series_id, start_utc, end_utc, cutoff_utc)
    except RuntimeError as exc:
        if not str(exc).startswith("HISTORY_NOT_FOUND:"):
            raise
        artifact_root = os.environ.get(CURRENT_TAIL_ROOT_ENV)
        if not artifact_root:
            raise
        return _mixed_plan_from_validated_tail(
            series_id,
            start_utc,
            end_utc,
            cutoff_utc,
            artifact_root=Path(artifact_root),
        )


def list_capabilities_v2():
    index = _publication_v2.build_index_v2()
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
    index = _publication_v2.build_index_v2()
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
    return _publication_v2.resolve_capability_v2(
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
        write_index()
    elif args.command == "validate":
        validate_committed()
    elif args.command == "list":
        _v1._print_json(list_capabilities() if args.plan_version == "1" else list_capabilities_v2())
    elif args.command == "describe":
        value = describe_capability(args.series_id) if args.plan_version == "1" else describe_capability_v2(args.series_id)
        _v1._print_json(value)
    elif args.plan_version == "1":
        if args.current_policy != "FINALIZED_ONLY" or args.qualification_mode:
            raise RuntimeError("V2_ONLY_RESOLUTION_OPTION")
        _v1._print_json(resolve_capability(args.series_id, args.start_utc, args.end_utc, args.cutoff_utc))
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
