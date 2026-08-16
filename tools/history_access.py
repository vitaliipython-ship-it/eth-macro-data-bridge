from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_SCHEMA = "market-data-resolution-plan/1.0.0"
DIAGNOSTICS_SCHEMA = "history-access-diagnostics/1.0.0"


class HistoryAccessError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _plan_digest(plan: dict) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(compact(body)).hexdigest()


def validate_resolution_plan(plan: dict) -> dict:
    required = {"schema_version", "plan_kind", "authority", "request", "series", "segments", "plan_sha256"}
    if not isinstance(plan, dict) or set(plan) != required:
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan top-level shape mismatch")
    if plan["schema_version"] != PLAN_SCHEMA or plan["plan_kind"] != "MARKET_DATA_RESOLUTION_PLAN":
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan identity mismatch")
    if plan["plan_sha256"] != _plan_digest(plan):
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan digest mismatch")

    request = plan["request"]
    series = plan["series"]
    if request.get("series_id") != series.get("series_id"):
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "request/series identity mismatch")
    start = request.get("start_ms")
    end = request.get("end_ms")
    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "invalid request range")
    if series.get("series") != "ohlcv" or not isinstance(series.get("interval_ms"), int):
        raise HistoryAccessError("UNSUPPORTED_INTERVAL", "D6.2B v1 materializes OHLCV series only")

    previous = None
    for segment in plan["segments"]:
        common = {
            "segment_id", "storage", "source_manifest_path", "sha256", "size_bytes",
            "first_timestamp_ms", "last_timestamp_ms", "read_start_ms", "read_end_ms",
            "source_provider", "instrument", "source_interval_or_metric",
        }
        if not isinstance(segment, dict) or not common <= set(segment):
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "segment shape mismatch")
        if segment["storage"] not in {"GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE"}:
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "unsupported segment storage")
        if not isinstance(segment["sha256"], str) or len(segment["sha256"]) != 64:
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "segment sha256 missing")
        if not isinstance(segment["size_bytes"], int) or segment["size_bytes"] < 0:
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "segment size invalid")
        if not (start <= segment["read_start_ms"] < segment["read_end_ms"] <= end):
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "segment range escapes request")
        if segment["storage"] == "GITHUB_RELEASE_ASSET":
            required_cold = {"release_tag", "asset_id", "asset_name", "browser_download_url", "immutable"}
            if not required_cold <= set(segment) or segment.get("immutable") is not True:
                raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "cold segment authority incomplete")
            url = segment["browser_download_url"]
            if not isinstance(url, str) or not url.startswith("https://"):
                raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "cold segment URL must be HTTPS")
        else:
            path = segment.get("resource_path")
            if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
                raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "warm resource path invalid")
        order = (segment["read_start_ms"], segment["read_end_ms"], segment["storage"], segment["segment_id"])
        if previous is not None and order < previous:
            raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "segments are not deterministically ordered")
        previous = order
    if not plan["segments"]:
        raise HistoryAccessError("HISTORY_NOT_FOUND", "resolution plan contains no physical segments")
    return plan


def read_resolution_plan(path: str) -> dict:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    try:
        return validate_resolution_plan(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise HistoryAccessError("INVALID_RESOLUTION_PLAN", "resolution plan is not valid JSON") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cache_path(segment: dict, cache_dir: Path) -> Path:
    identity = f"{segment['browser_download_url']}\0{segment['sha256']}".encode("utf-8")
    return cache_dir / (hashlib.sha256(identity).hexdigest() + ".json")


def _verified_cached_bytes(segment: dict, cache_dir: Path) -> bytes | None:
    path = _cache_path(segment, cache_dir)
    if not path.exists():
        return None
    raw = path.read_bytes()
    if len(raw) == segment["size_bytes"] and _sha256(raw) == segment["sha256"]:
        return raw
    path.unlink(missing_ok=True)
    return None


def _download_verified(segment: dict, cache_dir: Path, opener=urllib.request.urlopen) -> bytes:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = _verified_cached_bytes(segment, cache_dir)
    if cached is not None:
        return cached

    fd, temp_name = tempfile.mkstemp(prefix="history-access-", suffix=".partial", dir=cache_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    digest = hashlib.sha256()
    size = 0
    try:
        try:
            with opener(segment["browser_download_url"], timeout=120) as response, temp_path.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
                    out.write(chunk)
        except Exception as exc:
            raise HistoryAccessError("DOWNLOAD_FAILED", f"failed to download {segment['asset_name']}") from exc
        if size != segment["size_bytes"] or digest.hexdigest() != segment["sha256"]:
            raise HistoryAccessError("CHECKSUM_MISMATCH", f"cold asset integrity mismatch: {segment['asset_name']}")
        target = _cache_path(segment, cache_dir)
        os.replace(temp_path, target)
        return target.read_bytes()
    finally:
        temp_path.unlink(missing_ok=True)


def _warm_bytes(segment: dict, root: Path) -> bytes:
    path = (root / segment["resource_path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise HistoryAccessError("PARTITION_NOT_FOUND", "warm resource escaped repository root") from exc
    if not path.is_file():
        raise HistoryAccessError("PARTITION_NOT_FOUND", f"warm resource missing: {segment['resource_path']}")
    raw = path.read_bytes()
    if len(raw) != segment["size_bytes"] or _sha256(raw) != segment["sha256"]:
        raise HistoryAccessError("CHECKSUM_MISMATCH", f"warm resource integrity mismatch: {segment['resource_path']}")
    return raw


def _payload_identity(payload: dict) -> tuple[str | None, str | None, str | None]:
    return (
        payload.get("provider"),
        payload.get("symbol") or payload.get("instrument"),
        payload.get("interval") or payload.get("metric") or payload.get("interval_or_metric"),
    )


def _normalize_payload(raw: bytes, segment: dict) -> list[tuple[int, str, str, str, str, str]]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        code = "ARCHIVE_INVALID" if segment["storage"] == "GITHUB_RELEASE_ASSET" else "PARTITION_NOT_FOUND"
        raise HistoryAccessError(code, "physical segment is not valid JSON") from exc
    expected = (segment["source_provider"], segment["instrument"], segment["source_interval_or_metric"])
    if _payload_identity(payload) != expected:
        raise HistoryAccessError("MEMBER_NOT_FOUND", f"segment payload identity mismatch: expected={expected!r}")
    columns = payload.get("columns")
    records = payload.get("records")
    if not isinstance(columns, list) or not isinstance(records, list):
        raise HistoryAccessError("ARCHIVE_INVALID", "segment payload columns/records missing")
    aliases = {
        "open_time": ("open_time_ms",),
        "open": ("open",),
        "high": ("high",),
        "low": ("low",),
        "close": ("close",),
        "volume": ("base_volume", "volume"),
    }
    positions = {}
    for name, candidates in aliases.items():
        found = next((columns.index(candidate) for candidate in candidates if candidate in columns), None)
        if found is None:
            raise HistoryAccessError("ARCHIVE_INVALID", f"required OHLCV column missing: {name}")
        positions[name] = found

    normalized = []
    for row in records:
        if not isinstance(row, list) or max(positions.values()) >= len(row):
            raise HistoryAccessError("ARCHIVE_INVALID", "invalid candle row shape")
        ts = row[positions["open_time"]]
        if not isinstance(ts, int):
            raise HistoryAccessError("INVALID_CANDLE", "open_time_ms must be integer")
        if not (segment["read_start_ms"] <= ts < segment["read_end_ms"]):
            continue
        values = []
        try:
            for field in ("open", "high", "low", "close", "volume"):
                value = Decimal(str(row[positions[field]]))
                if not value.is_finite():
                    raise InvalidOperation
                values.append(value)
        except (InvalidOperation, ValueError) as exc:
            raise HistoryAccessError("INVALID_CANDLE", f"non-numeric candle at {ts}") from exc
        o, h, l, c, v = values
        if h < max(o, l, c) or l > min(o, h, c) or v < 0:
            raise HistoryAccessError("INVALID_CANDLE", f"invalid OHLCV candle at {ts}")
        normalized.append((ts, *(format(value, "f") for value in values)))
    return normalized


def _iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def materialize_resolution_plan(
    plan: dict,
    *,
    root: Path = ROOT,
    cache_dir: Path | None = None,
    mode: str = "strict",
    opener=urllib.request.urlopen,
) -> tuple[list[tuple[int, str, str, str, str, str]], dict]:
    validate_resolution_plan(plan)
    if mode not in {"strict", "permissive"}:
        raise ValueError("mode must be strict or permissive")
    cache_dir = Path(cache_dir or os.environ.get(
        "ETH_MACRO_HISTORY_CACHE",
        Path.home() / ".cache" / "eth-macro-data-bridge" / "history-access",
    ))

    merged: dict[int, tuple[int, str, str, str, str, str]] = {}
    duplicate_timestamps = []
    sources = []
    for segment in plan["segments"]:
        if segment["storage"] == "GITHUB_RELEASE_ASSET":
            raw = _download_verified(segment, cache_dir, opener=opener)
            locator = segment["asset_name"]
        else:
            raw = _warm_bytes(segment, Path(root))
            locator = segment["resource_path"]
        rows = _normalize_payload(raw, segment)
        for row in rows:
            if row[0] in merged:
                duplicate_timestamps.append(row[0])
                continue
            merged[row[0]] = row
        sources.append({
            "segment_id": segment["segment_id"],
            "storage": segment["storage"],
            "locator": locator,
            "sha256": segment["sha256"],
            "rows": len(rows),
        })

    rows = [merged[key] for key in sorted(merged)]
    request = plan["request"]
    interval_ms = plan["series"]["interval_ms"]
    expected = list(range(request["start_ms"], request["end_ms"], interval_ms))
    actual = set(merged)
    expected_set = set(expected)
    missing = [timestamp for timestamp in expected if timestamp not in actual]
    extras = [timestamp for timestamp in actual if timestamp not in expected_set]
    if extras:
        raise HistoryAccessError("INVALID_CANDLE", f"rows outside expected candle grid: {extras[:5]}")

    if duplicate_timestamps and mode == "strict":
        raise HistoryAccessError("DUPLICATE_TIMESTAMP", f"duplicate timestamps: {duplicate_timestamps[:5]}")
    if missing and mode == "strict":
        raise HistoryAccessError("DATA_GAP", f"missing candle timestamps: {missing[:5]}")

    degraded = bool(duplicate_timestamps or missing)
    diagnostics = {
        "schema_version": DIAGNOSTICS_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "series_id": request["series_id"],
        "requested_start": _iso(request["start_ms"]),
        "requested_end": _iso(request["end_ms"]),
        "actual_start": _iso(rows[0][0]) if rows else None,
        "actual_end": _iso(rows[-1][0] + interval_ms) if rows else None,
        "rows": len(rows),
        "expected_rows": len(expected),
        "duplicates": len(duplicate_timestamps),
        "duplicate_timestamps_ms": sorted(set(duplicate_timestamps)),
        "gap_count": len(missing),
        "missing_intervals_ms": missing,
        "status": "DEGRADED" if degraded else "PASS",
        "sources": sources,
    }
    return rows, diagnostics


def rows_to_csv(rows: list[tuple[int, str, str, str, str, str]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("open_time", "open", "high", "low", "close", "volume"))
    for ts, o, h, l, c, v in rows:
        writer.writerow((_iso(ts), o, h, l, c, v))
    return stream.getvalue()


def rows_to_json(rows: list[tuple[int, str, str, str, str, str]]) -> str:
    payload = [
        {"open_time": _iso(ts), "open": o, "high": h, "low": l, "close": c, "volume": v}
        for ts, o, h, l, c, v in rows
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="D6.2B read-only historical materialization from a ResolutionPlan")
    sub = parser.add_subparsers(dest="command", required=True)
    slice_cmd = sub.add_parser("slice")
    slice_cmd.add_argument("--plan", required=True, help="ResolutionPlan JSON file, or - for stdin")
    slice_cmd.add_argument("--format", choices=("csv", "json"), default="csv")
    slice_cmd.add_argument("--output", default="-")
    slice_cmd.add_argument("--mode", choices=("strict", "permissive"), default="strict")
    slice_cmd.add_argument("--cache-dir")
    args = parser.parse_args(argv)

    plan = read_resolution_plan(args.plan)
    rows, diagnostics = materialize_resolution_plan(
        plan,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        mode=args.mode,
    )
    body = rows_to_csv(rows) if args.format == "csv" else rows_to_json(rows)
    if args.output == "-":
        sys.stdout.write(body)
    else:
        Path(args.output).write_text(body, encoding="utf-8")
    print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True, separators=(",", ":")), file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except HistoryAccessError as exc:
        print(json.dumps({"status": "FAIL", "code": exc.code, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
