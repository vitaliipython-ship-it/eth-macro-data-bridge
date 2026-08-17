from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import _history_access_v1 as v1

PLAN_SCHEMA = "market-data-resolution-plan/2.0.0"
DIAGNOSTICS_SCHEMA = "history-access-diagnostics/2.0.0"
RECEIPT_SCHEMA = "history-access-receipt/2.0.0"
COLD_ASSET_SCHEMA = "market-data-cold-asset/1.1.0"
REVISION_SCHEMA = "market-data-provider-revision/1.0.0"


class HistoryAccessV2Error(v1.HistoryAccessError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(compact(body)).hexdigest()


def _iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def validate_resolution_plan_v2(plan: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "plan_kind", "authority", "request", "series", "segments", "plan_sha256"}
    if not isinstance(plan, dict) or set(plan) != required:
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "ResolutionPlan v2 top-level shape mismatch")
    if plan.get("schema_version") != PLAN_SCHEMA or plan.get("plan_kind") != "MARKET_DATA_RESOLUTION_PLAN":
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "ResolutionPlan v2 identity mismatch")
    if plan.get("plan_sha256") != _plan_digest(plan):
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "ResolutionPlan v2 digest mismatch")
    request = plan.get("request", {})
    series = plan.get("series", {})
    if request.get("series_id") != series.get("series_id"):
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "request/series identity mismatch")
    start, end = request.get("start_ms"), request.get("end_ms")
    effective = request.get("effective_start_ms", start)
    if not all(isinstance(value, int) for value in (start, end, effective)) or not start <= effective < end:
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "invalid v2 request range")
    if request.get("current_policy", "FINALIZED_ONLY") not in {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}:
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "invalid current policy")
    if series.get("coverage_semantics") not in {"FIXED_GRID", "SAMPLED_SCHEDULE", "EVENT_DRIVEN"}:
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "coverage semantics missing")
    if series.get("series_kind") not in {"OHLCV", "SCALAR_TIME_SERIES", "STRUCTURED_TIME_SERIES", "SNAPSHOT_SERIES", "OPTION_SURFACE", "ORDER_BOOK_SNAPSHOT"}:
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "series kind missing")
    if series.get("coverage_semantics") == "FIXED_GRID" and not isinstance(series.get("interval_ms"), int):
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "fixed-grid interval missing")

    previous = None
    for segment in plan.get("segments", []):
        if not isinstance(segment, dict):
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "segment must be object")
        for key in ("segment_id", "storage", "sha256", "size_bytes", "read_start_ms", "read_end_ms", "physical_descriptor"):
            if key not in segment:
                raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", f"segment field missing: {key}")
        if segment["storage"] not in {"GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE", "GITHUB_RELEASE_WARM_ASSET", "HOT_CURRENT_RESOURCE"}:
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "unsupported v2 storage")
        if not isinstance(segment["sha256"], str) or len(segment["sha256"]) != 64:
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "segment sha256 missing")
        if not isinstance(segment["size_bytes"], int) or segment["size_bytes"] < 0:
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "segment size invalid")
        if not (effective <= segment["read_start_ms"] < segment["read_end_ms"] <= end):
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "segment range escapes effective request")
        if segment["storage"] in {"GITHUB_RELEASE_ASSET", "GITHUB_RELEASE_WARM_ASSET"}:
            if not all(segment.get(key) is not None for key in ("asset_id", "asset_name", "browser_download_url")):
                raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "release segment descriptor incomplete")
            if not str(segment["browser_download_url"]).startswith("https://"):
                raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "release segment URL must be HTTPS")
        else:
            resource_path = segment.get("resource_path") or segment.get("physical_descriptor", {}).get("resource_path")
            if not isinstance(resource_path, str) or not resource_path or Path(resource_path).is_absolute() or ".." in Path(resource_path).parts:
                raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "repository resource path invalid")
            if segment["storage"] == "HOT_CURRENT_RESOURCE" and request.get("current_policy") != "INCLUDE_CURRENT_PROVISIONAL":
                raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "HOT segment requires explicit provisional policy")
        order = (segment["read_start_ms"], segment["read_end_ms"], segment["storage"], segment["segment_id"])
        if previous is not None and order < previous:
            raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "segments are not deterministically ordered")
        previous = order
    if not plan.get("segments"):
        raise HistoryAccessV2Error("HISTORY_NOT_FOUND", "ResolutionPlan v2 contains no physical segments")
    return plan


def _verified_bytes(segment: dict[str, Any], *, root: Path, cache_dir: Path, opener) -> bytes:
    if segment["storage"] in {"GITHUB_RELEASE_ASSET", "GITHUB_RELEASE_WARM_ASSET"}:
        return v1._download_verified(segment, cache_dir, opener=opener)
    materialized = dict(segment)
    materialized["resource_path"] = segment.get("resource_path") or segment["physical_descriptor"]["resource_path"]
    return v1._warm_bytes(materialized, root)


def _payload_identity_ok(payload: dict[str, Any], segment: dict[str, Any], series_id: str) -> bool:
    if payload.get("schema_version") == COLD_ASSET_SCHEMA:
        return payload.get("series_id") == series_id and payload.get("generation_id") == segment.get("generation_id")
    expected = (segment.get("source_provider"), segment.get("instrument"), segment.get("source_interval_or_metric"))
    actual = (
        payload.get("provider"),
        payload.get("symbol") or payload.get("instrument"),
        payload.get("interval") or payload.get("metric") or payload.get("interval_or_metric"),
    )
    return actual == expected


def _record_encoding(payload: dict[str, Any], series_kind: str) -> dict[str, Any]:
    if payload.get("schema_version") == COLD_ASSET_SCHEMA:
        encoding = payload.get("record_encoding")
        if not isinstance(encoding, dict) or encoding.get("kind") not in {"POSITIONAL_COLUMNS", "TIMESTAMP_VALUE", "SNAPSHOT_OBJECT"}:
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "D9 COLD asset is not self-describing")
        return encoding
    columns = payload.get("columns")
    if isinstance(columns, list) and columns:
        return {"kind": "POSITIONAL_COLUMNS", "columns": columns}
    records = payload.get("records")
    if isinstance(records, list) and all(isinstance(row, list) and len(row) == 2 for row in records):
        return {"kind": "TIMESTAMP_VALUE"}
    if series_kind in {"SNAPSHOT_SERIES", "OPTION_SURFACE", "ORDER_BOOK_SNAPSHOT"}:
        return {"kind": "SNAPSHOT_OBJECT"}
    raise HistoryAccessV2Error("ARCHIVE_INVALID", "physical resource record encoding ambiguous")


def _decimal(value: Any, field: str, ts: int) -> str:
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError) as exc:
        raise HistoryAccessV2Error("INVALID_OBSERVATION", f"non-numeric {field} at {ts}") from exc
    return format(number, "f")


def _normalize_records(raw: bytes, segment: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "physical segment is not valid JSON") from exc
    series = plan["series"]
    if not _payload_identity_ok(payload, segment, series["series_id"]):
        raise HistoryAccessV2Error("MEMBER_NOT_FOUND", "segment payload semantic identity mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        if series["series_kind"] in {"SNAPSHOT_SERIES", "OPTION_SURFACE", "ORDER_BOOK_SNAPSHOT"} and isinstance(payload.get("snapshot"), dict):
            snapshot = payload["snapshot"]
            timestamp = snapshot.get("timestamp_ms") or snapshot.get("expected_schedule_at_ms")
            records = [[timestamp, snapshot]] if isinstance(timestamp, int) else []
        else:
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "records missing")
    encoding = _record_encoding(payload, series["series_kind"])
    normalized: list[dict[str, Any]] = []
    if encoding["kind"] == "POSITIONAL_COLUMNS":
        columns = encoding.get("columns")
        if not isinstance(columns, list):
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "positional columns missing")
        timestamp_aliases = ("open_time_ms", "timestamp_ms", "effective_timestamp_ms", "expected_schedule_at_ms")
        ts_pos = next((columns.index(name) for name in timestamp_aliases if name in columns), None)
        if ts_pos is None:
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "timestamp column missing")
        if series["series_kind"] == "OHLCV":
            aliases = {
                "open": ("open",), "high": ("high",), "low": ("low",), "close": ("close",), "volume": ("base_volume", "volume")
            }
            positions = {}
            for field, names in aliases.items():
                position = next((columns.index(name) for name in names if name in columns), None)
                if position is None:
                    raise HistoryAccessV2Error("ARCHIVE_INVALID", f"OHLCV column missing: {field}")
                positions[field] = position
            for row in records:
                if not isinstance(row, list) or max([ts_pos, *positions.values()]) >= len(row):
                    raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid positional OHLCV row")
                ts = row[ts_pos]
                if not isinstance(ts, int):
                    raise HistoryAccessV2Error("INVALID_OBSERVATION", "timestamp must be integer milliseconds")
                if not (segment["read_start_ms"] <= ts < segment["read_end_ms"]):
                    continue
                values = {field: _decimal(row[position], field, ts) for field, position in positions.items()}
                o, h, l, c, volume = (Decimal(values[field]) for field in ("open", "high", "low", "close", "volume"))
                if h < max(o, l, c) or l > min(o, h, c) or volume < 0:
                    raise HistoryAccessV2Error("INVALID_OBSERVATION", f"invalid OHLCV candle at {ts}")
                normalized.append({"timestamp_ms": ts, "value": values})
        else:
            for row in records:
                if not isinstance(row, list) or ts_pos >= len(row):
                    raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid positional row")
                ts = row[ts_pos]
                if isinstance(ts, int) and segment["read_start_ms"] <= ts < segment["read_end_ms"]:
                    normalized.append({"timestamp_ms": ts, "value": {name: row[index] for index, name in enumerate(columns) if index != ts_pos and index < len(row)}})
    elif encoding["kind"] == "TIMESTAMP_VALUE":
        for row in records:
            if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], int):
                raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid timestamp/value row")
            if segment["read_start_ms"] <= row[0] < segment["read_end_ms"]:
                normalized.append({"timestamp_ms": row[0], "value": row[1]})
    else:
        for row in records:
            if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], int):
                raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid sampled snapshot row")
            if segment["read_start_ms"] <= row[0] < segment["read_end_ms"]:
                normalized.append({"timestamp_ms": row[0], "value": row[1]})
    return normalized


def _revision_payload(root: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    path = (root / descriptor["resource_path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision evidence escaped repository root") from exc
    if not path.is_file():
        raise HistoryAccessV2Error("REVISION_INVALID", f"revision evidence missing: {descriptor['resource_path']}")
    raw = path.read_bytes()
    if len(raw) != descriptor["size_bytes"] or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise HistoryAccessV2Error("CHECKSUM_MISMATCH", f"revision evidence integrity mismatch: {descriptor['resource_path']}")
    payload = json.loads(raw)
    if payload.get("schema_version") != REVISION_SCHEMA:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision evidence schema mismatch")
    return payload


def _apply_revisions(
    observations: list[dict[str, Any]],
    segment: dict[str, Any],
    plan: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    descriptors = segment.get("revision_evidence", [])
    if not descriptors:
        return observations, []
    cutoff = plan["request"].get("cutoff_ms")
    by_timestamp = {item["timestamp_ms"]: item for item in observations}
    chosen: dict[int, tuple[int, str, dict[str, Any]]] = {}
    for descriptor in descriptors:
        evidence = _revision_payload(root, descriptor)
        known_at_ms = descriptor.get("known_at_ms")
        timestamp = evidence.get("effective_timestamp")
        revision_id = evidence.get("revision_id")
        if not isinstance(known_at_ms, int) or not isinstance(timestamp, int) or not isinstance(revision_id, str):
            raise HistoryAccessV2Error("REVISION_INVALID", "revision descriptor incomplete")
        if cutoff is not None and known_at_ms > cutoff:
            continue
        if timestamp not in by_timestamp:
            raise HistoryAccessV2Error("REVISION_INVALID", f"revision has no base observation: {timestamp}")
        observed = evidence.get("observed_value")
        if not isinstance(observed, list) or len(observed) < 2 or observed[0] != timestamp:
            raise HistoryAccessV2Error("REVISION_INVALID", "revision observed value mismatch")
        current = chosen.get(timestamp)
        if current is not None and known_at_ms == current[0] and observed != current[2].get("observed_value"):
            raise HistoryAccessV2Error("REVISION_INVALID", f"ambiguous revision ordering: {timestamp}")
        if current is None or (known_at_ms, revision_id) > (current[0], current[1]):
            chosen[timestamp] = (known_at_ms, revision_id, evidence)
    applied = []
    for timestamp, (known_at_ms, revision_id, evidence) in chosen.items():
        by_timestamp[timestamp] = {"timestamp_ms": timestamp, "value": evidence["observed_value"][1], "revision_id": revision_id, "known_at_ms": known_at_ms}
        applied.append({"timestamp_ms": timestamp, "revision_id": revision_id, "known_at_ms": known_at_ms, "evidence_path": next(item["resource_path"] for item in descriptors if item.get("revision_id") == revision_id)})
    return [by_timestamp[key] for key in sorted(by_timestamp)], sorted(applied, key=lambda item: (item["timestamp_ms"], item["known_at_ms"], item["revision_id"]))


def materialize_resolution_plan_v2(
    plan: dict[str, Any],
    *,
    root: Path,
    cache_dir: Path | None = None,
    mode: str = "strict",
    opener=urllib.request.urlopen,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_resolution_plan_v2(plan)
    if mode not in {"strict", "permissive"}:
        raise ValueError("mode must be strict or permissive")
    cache = Path(cache_dir or os.environ.get("ETH_MACRO_HISTORY_CACHE", Path.home() / ".cache" / "eth-macro-data-bridge" / "history-access"))
    merged: dict[int, dict[str, Any]] = {}
    sources = []
    overlaps = []
    revisions = []
    provisional = False
    known_collection_gaps = []
    for segment in plan["segments"]:
        raw = _verified_bytes(segment, root=root, cache_dir=cache, opener=opener)
        observations = _normalize_records(raw, segment, plan)
        observations, applied = _apply_revisions(observations, segment, plan, root)
        revisions.extend(applied)
        if segment["storage"] == "HOT_CURRENT_RESOURCE":
            provisional = True
            for item in observations:
                item["finality"] = "PROVISIONAL"
        else:
            for item in observations:
                item.setdefault("finality", "FINALIZED")
        for item in observations:
            timestamp = item["timestamp_ms"]
            previous = merged.get(timestamp)
            if previous is None:
                merged[timestamp] = item
            elif previous.get("value") == item.get("value"):
                overlaps.append(timestamp)
                if previous.get("finality") == "PROVISIONAL" and item.get("finality") == "FINALIZED":
                    merged[timestamp] = item
            else:
                raise HistoryAccessV2Error("DUPLICATE_CONFLICT", f"cross-tier semantic mismatch at {timestamp}")
        known_collection_gaps.extend(segment.get("known_gaps", []))
        sources.append({
            "segment_id": segment["segment_id"],
            "storage": segment["storage"],
            "generation_id": segment.get("generation_id"),
            "sha256": segment["sha256"],
            "rows": len(observations),
            "revision_evidence": len(segment.get("revision_evidence", [])),
        })

    observations = [merged[key] for key in sorted(merged)]
    request = plan["request"]
    series = plan["series"]
    effective_start = request.get("effective_start_ms", request["start_ms"])
    missing: list[int] = []
    if series["coverage_semantics"] == "FIXED_GRID":
        interval = series["interval_ms"]
        expected = list(range(effective_start, request["end_ms"], interval))
        actual = set(merged)
        missing = [timestamp for timestamp in expected if timestamp not in actual]
        extras = [timestamp for timestamp in actual if timestamp < effective_start or timestamp >= request["end_ms"] or (timestamp - effective_start) % interval]
        if extras:
            raise HistoryAccessV2Error("INVALID_OBSERVATION", f"rows outside fixed grid: {extras[:5]}")
        if missing and mode == "strict":
            raise HistoryAccessV2Error("DATA_GAP", f"missing fixed-grid timestamps: {missing[:5]}")
    else:
        # Sampled/event history is evidence of observations, never a reconstructed fixed grid.
        missing = []

    boundary = series.get("coverage_boundary_evidence", {})
    boundary_unavailable = max(0, int(boundary.get("effective_start_ms", effective_start)) - int(boundary.get("requested_start_ms", request["start_ms"])))
    degraded = bool(missing or known_collection_gaps or boundary_unavailable)
    output_sha = hashlib.sha256(compact(observations)).hexdigest()
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "resolution_plan_sha256": plan["plan_sha256"],
        "output_sha256": output_sha,
        "observation_count": len(observations),
        "finality": "PROVISIONAL_INCLUDED" if provisional else "FINALIZED",
    }
    diagnostics = {
        "schema_version": DIAGNOSTICS_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "series_id": series["series_id"],
        "series_kind": series["series_kind"],
        "coverage_semantics": series["coverage_semantics"],
        "requested_start": _iso(request["start_ms"]),
        "effective_start": _iso(effective_start),
        "requested_end": _iso(request["end_ms"]),
        "rows": len(observations),
        "internal_gap_count": len(missing),
        "missing_intervals_ms": missing,
        "collection_gap_count": len(known_collection_gaps),
        "collection_gaps": known_collection_gaps,
        "provider_boundary": boundary if boundary_unavailable else None,
        "overlap_deduped_timestamps_ms": sorted(set(overlaps)),
        "revisions_applied": revisions,
        "provisional_included": provisional,
        "status": "DEGRADED" if degraded else "PASS",
        "sources": sources,
        "receipt": receipt,
    }
    return observations, diagnostics
