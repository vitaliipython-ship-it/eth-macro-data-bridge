from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    from . import _history_access_v1 as _v1
    sys.modules.setdefault("_history_access_v1", _v1)
    from . import history_access_v2 as _v2
    sys.modules.setdefault("history_access_v2", _v2)
    from . import publication_reader_v2 as _publication_v2
    from .current_tail_admission import validate_descriptor
except ImportError:
    import _history_access_v1 as _v1
    import history_access_v2 as _v2
    import publication_reader_v2 as _publication_v2
    from current_tail_admission import validate_descriptor

CURRENT_TAIL_STORAGE = "VALIDATED_EPHEMERAL_CURRENT_TAIL"

# Preserve the complete D6 import surface for existing consumers. V2 is parsed and
# materialized only when the ResolutionPlan itself carries the v2 discriminator.
for _name, _value in vars(_v1).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


def _has_current_tail(plan: dict) -> bool:
    return any(isinstance(row, dict) and row.get("storage") == CURRENT_TAIL_STORAGE for row in plan.get("segments", []))


def _validate_durable_segment_in_mixed_plan(plan: dict, segment: dict) -> None:
    single = dict(plan)
    single["segments"] = [segment]
    single["plan_sha256"] = _v1._plan_digest(single)
    _v1.validate_resolution_plan(single)


def validate_resolution_plan(plan: dict) -> dict:
    if not _has_current_tail(plan):
        return _v1.validate_resolution_plan(plan)
    required = {"schema_version", "plan_kind", "authority", "request", "series", "segments", "plan_sha256"}
    if not isinstance(plan, dict) or set(plan) != required:
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan top-level shape mismatch")
    if plan.get("schema_version") != _v1.PLAN_SCHEMA or plan.get("plan_kind") != "MARKET_DATA_RESOLUTION_PLAN":
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan identity mismatch")
    if plan.get("plan_sha256") != _v1._plan_digest(plan):
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan digest mismatch")
    request = plan.get("request", {})
    series = plan.get("series", {})
    if request.get("series_id") != series.get("series_id"):
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "request/series identity mismatch")
    start, end = request.get("start_ms"), request.get("end_ms")
    interval = series.get("interval_ms")
    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "invalid request range")
    if series.get("series") != "ohlcv" or not isinstance(interval, int) or interval <= 0:
        raise _v1.HistoryAccessError("UNSUPPORTED_INTERVAL", "validated current tail supports canonical OHLCV grids only")

    previous = None
    current_count = 0
    for segment in plan.get("segments", []):
        if not isinstance(segment, dict):
            raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "segment must be object")
        if segment.get("storage") != CURRENT_TAIL_STORAGE:
            _validate_durable_segment_in_mixed_plan(plan, segment)
        else:
            current_count += 1
            descriptor = segment.get("current_tail")
            try:
                descriptor = validate_descriptor(descriptor)
            except Exception as exc:
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", f"validated current-tail descriptor invalid: {exc}") from exc
            required_tail = {
                "segment_id", "storage", "source_manifest_path", "resource_path", "sha256", "size_bytes",
                "first_timestamp_ms", "last_timestamp_ms", "read_start_ms", "read_end_ms",
                "source_provider", "instrument", "source_interval_or_metric", "authority_class", "current_tail",
            }
            if not required_tail <= set(segment):
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "validated current-tail segment incomplete")
            if segment.get("authority_class") != "VALIDATED_EPHEMERAL_CURRENT_TAIL":
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "validated current-tail authority class mismatch")
            if descriptor.get("series_id") != request.get("series_id") or descriptor.get("interval_ms") != interval:
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "validated current-tail series binding mismatch")
            for key in ("resource_path", "sha256", "size_bytes", "first_timestamp_ms", "last_timestamp_ms"):
                if segment.get(key) != descriptor.get(key):
                    raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", f"validated current-tail segment differs from descriptor: {key}")
            if not (start <= segment.get("read_start_ms", -1) < segment.get("read_end_ms", -1) <= end):
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "validated current-tail range escapes request")
            if segment["read_end_ms"] > descriptor.get("finalized_cutoff_ms", -1):
                raise _v1.HistoryAccessError("OPEN_BAR_FORBIDDEN", "validated current-tail read exceeds finalized cutoff")
            path = segment.get("resource_path")
            if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
                raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "validated current-tail resource path invalid")
        order = (segment["read_start_ms"], segment["read_end_ms"], segment["storage"], segment["segment_id"])
        if previous is not None and order < previous:
            raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "segments are not deterministically ordered")
        previous = order
    if current_count != 1:
        raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", "mixed ResolutionPlan must bind exactly one validated current tail")
    return plan


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
    return validate_resolution_plan(plan)


def _parse_open_ms(value: object) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", "current-tail open_time must be UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", f"invalid current-tail open_time: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", "current-tail open_time must be UTC")
    return int(parsed.timestamp() * 1000)


def _normalize_current_tail(raw: bytes, segment: dict, interval_ms: int):
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", "validated current-tail payload is not JSON") from exc
    if not isinstance(payload, list):
        raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", "validated current-tail payload must be observation array")
    rows = []
    for item in payload:
        if not isinstance(item, dict):
            raise _v1.HistoryAccessError("CURRENT_TAIL_INVALID", "validated current-tail observation must be object")
        ts = _parse_open_ms(item.get("open_time"))
        if not (segment["read_start_ms"] <= ts < segment["read_end_ms"]):
            continue
        if ts + interval_ms > segment["current_tail"]["finalized_cutoff_ms"]:
            raise _v1.HistoryAccessError("OPEN_BAR_FORBIDDEN", f"current-tail observation is not finalized: {ts}")
        try:
            values = [Decimal(str(item[field])) for field in ("open", "high", "low", "close", "volume")]
            if any(not value.is_finite() for value in values):
                raise InvalidOperation
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise _v1.HistoryAccessError("INVALID_CANDLE", f"invalid current-tail candle at {ts}") from exc
        o, h, l, c, v = values
        if h < max(o, l, c) or l > min(o, h, c) or v < 0:
            raise _v1.HistoryAccessError("INVALID_CANDLE", f"invalid current-tail OHLCV bounds at {ts}")
        rows.append((ts, *(format(value, "f") for value in values)))
    return rows


def materialize_resolution_plan(
    plan: dict,
    *,
    root: Path = _v1.ROOT,
    cache_dir: Path | None = None,
    mode: str = "strict",
    opener=None,
):
    if not _has_current_tail(plan):
        kwargs = {"root": root, "cache_dir": cache_dir, "mode": mode}
        if opener is not None:
            kwargs["opener"] = opener
        return _v1.materialize_resolution_plan(plan, **kwargs)
    validate_resolution_plan(plan)
    if mode not in {"strict", "permissive"}:
        raise ValueError("mode must be strict or permissive")
    opener = opener or _v1.urllib.request.urlopen
    cache_dir = Path(cache_dir or os.environ.get(
        "ETH_MACRO_HISTORY_CACHE",
        Path.home() / ".cache" / "eth-macro-data-bridge" / "history-access",
    ))
    root = Path(root)
    interval_ms = plan["series"]["interval_ms"]
    merged = {}
    identical_overlaps = []
    sources = []
    durable_present = False
    current_present = False
    for segment in plan["segments"]:
        storage = segment["storage"]
        if storage == "GITHUB_RELEASE_ASSET":
            raw = _v1._download_verified(segment, cache_dir, opener=opener)
            rows = _v1._normalize_payload(raw, segment)
            locator = segment["asset_name"]
            authority_class = "DURABLE_HISTORY_AUTHORITY"
            durable_present = True
        elif storage == "GIT_WARM_RESOURCE":
            raw = _v1._warm_bytes(segment, root)
            rows = _v1._normalize_payload(raw, segment)
            locator = segment["resource_path"]
            authority_class = "DURABLE_HISTORY_AUTHORITY"
            durable_present = True
        elif storage == CURRENT_TAIL_STORAGE:
            raw = _v1._warm_bytes(segment, root)
            rows = _normalize_current_tail(raw, segment, interval_ms)
            locator = segment["resource_path"]
            authority_class = "VALIDATED_EPHEMERAL_CURRENT_TAIL"
            current_present = True
        else:
            raise _v1.HistoryAccessError("INVALID_RESOLUTION_PLAN", f"unsupported segment storage: {storage}")
        for row in rows:
            previous = merged.get(row[0])
            if previous is None:
                merged[row[0]] = row
            elif previous == row:
                identical_overlaps.append(row[0])
            else:
                raise _v1.HistoryAccessError("OVERLAP_CONFLICT", f"conflicting observation at timestamp {row[0]}")
        source = {
            "segment_id": segment["segment_id"],
            "storage": storage,
            "authority_class": authority_class,
            "locator": locator,
            "sha256": segment["sha256"],
            "rows": len(rows),
        }
        if storage == CURRENT_TAIL_STORAGE:
            descriptor = segment["current_tail"]
            source.update({
                "generation_id": descriptor["generation_id"],
                "generated_at_utc": descriptor["generated_at_utc"],
                "known_at_utc": descriptor["known_at_utc"],
                "control_plane_head": descriptor["control_plane_head"],
                "validation": descriptor["validation"],
                "current_analysis_allowed": descriptor["current_analysis_allowed"],
                "current_policy": descriptor["current_policy"],
                "finalized_cutoff_ms": descriptor["finalized_cutoff_ms"],
                "durable_history_authority": False,
            })
        sources.append(source)

    rows = [merged[key] for key in sorted(merged)]
    request = plan["request"]
    expected = list(range(request["start_ms"], request["end_ms"], interval_ms))
    actual = set(merged)
    expected_set = set(expected)
    missing = [timestamp for timestamp in expected if timestamp not in actual]
    extras = [timestamp for timestamp in actual if timestamp not in expected_set]
    if extras:
        raise _v1.HistoryAccessError("INVALID_CANDLE", f"rows outside expected candle grid: {extras[:5]}")
    if missing and mode == "strict":
        raise _v1.HistoryAccessError("DATA_GAP", f"missing candle timestamps: {missing[:5]}")
    degraded = bool(missing)
    diagnostics = {
        "schema_version": _v1.DIAGNOSTICS_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "series_id": request["series_id"],
        "requested_start": _v1._iso(request["start_ms"]),
        "requested_end": _v1._iso(request["end_ms"]),
        "actual_start": _v1._iso(rows[0][0]) if rows else None,
        "actual_end": _v1._iso(rows[-1][0] + interval_ms) if rows else None,
        "rows": len(rows),
        "expected_rows": len(expected),
        "duplicates": 0,
        "duplicate_timestamps_ms": [],
        "deduplicated_identical_overlaps": len(set(identical_overlaps)),
        "deduplicated_identical_overlap_timestamps_ms": sorted(set(identical_overlaps)),
        "gap_count": len(missing),
        "missing_intervals_ms": missing,
        "conflicts": 0,
        "status": "DEGRADED" if degraded else "PASS",
        "history_source_mode": "DURABLE_PLUS_VALIDATED_FRESH_CURRENT_TAIL",
        "durable_segment_present": durable_present,
        "fresh_current_tail_present": current_present,
        "sources": sources,
    }
    return rows, diagnostics


def materialize_resolution_plan_any(
    plan: dict,
    *,
    cache_dir: Path | None = None,
    mode: str = "strict",
):
    if plan.get("schema_version") == _v2.PLAN_SCHEMA:
        return _publication_v2.materialize_resolution_plan_v2(
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
