from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import _history_access_v1 as v1

PLAN_SCHEMA = "market-data-resolution-plan/2.0.0"
DIAGNOSTICS_SCHEMA = "history-access-diagnostics/2.0.0"
RECEIPT_SCHEMA = "history-access-receipt/2.0.0"
COLD_ASSET_SCHEMA = "market-data-cold-asset/1.1.0"
LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
REVISION_SCHEMA = "market-data-provider-revision/1.0.0"
REVISION_SOURCE_SCHEMA = "kraken-revision-source-observation/1.0.0"
REVISABLE_CLASS = "PROVIDER_REVISABLE_SNAPSHOT"


class HistoryAccessV2Error(v1.HistoryAccessError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(compact(body)).hexdigest()


def _iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def build_semantic_receipt(
    *,
    series_id: str,
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
    mode: str,
    current_policy: str,
    resolution_plan_sha256: str,
    observations: list[dict[str, Any]],
    finality: str,
    revision_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Canonical semantic receipt authority shared by D6 adapter and D9 v2 reader."""
    if not isinstance(series_id, str) or not series_id:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt series_id missing")
    if not isinstance(start_ms, int) or not isinstance(end_ms, int) or start_ms >= end_ms:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt request range invalid")
    if cutoff_ms is not None and (not isinstance(cutoff_ms, int) or end_ms > cutoff_ms):
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt cutoff does not cover request")
    if mode not in {"strict", "permissive"}:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt mode invalid")
    if current_policy not in {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt current_policy invalid")
    if finality not in {"FINALIZED", "PROVISIONAL_INCLUDED"}:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt finality invalid")
    if finality == "PROVISIONAL_INCLUDED" and current_policy != "INCLUDE_CURRENT_PROVISIONAL":
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "provisional finality requires explicit provisional policy")
    if not isinstance(resolution_plan_sha256, str) or len(resolution_plan_sha256) != 64:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", "semantic receipt resolution plan digest invalid")
    return {
        "receipt_schema_version": RECEIPT_SCHEMA,
        "series_id": series_id,
        "request": {
            "from_utc": _iso(start_ms),
            "to_utc": _iso(end_ms),
            "cutoff_utc": _iso(cutoff_ms),
            "mode": mode,
            "current_policy": current_policy,
        },
        "resolution_plan_sha256": resolution_plan_sha256,
        "output_sha256": hashlib.sha256(compact(observations)).hexdigest(),
        "observation_count": len(observations),
        "finality": finality,
        "revision_context": revision_context,
    }


def _receipt_revision_context(revisions: list[dict[str, Any]], cutoff_ms: int | None) -> dict[str, Any] | None:
    # One Research receipt has room for one exact revision identity only. Never
    # collapse unrelated revisions into a synthetic aggregate context.
    if cutoff_ms is None or len(revisions) != 1:
        return None
    row = revisions[0]
    evidence_sha256 = row.get("evidence_sha256")
    if not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64:
        return None
    return {
        "observation_time_utc": _iso(row["timestamp_ms"]),
        "effective_time_utc": _iso(row["timestamp_ms"]),
        "revision_known_at_utc": _iso(row["known_at_ms"]),
        "evidence_sha256": evidence_sha256,
    }


def _parse_utc_ms(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryAccessV2Error("INVALID_PROVENANCE", f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise HistoryAccessV2Error("INVALID_PROVENANCE", f"timestamp must be UTC: {value}")
    return int(parsed.timestamp() * 1000)


def _safe_path(root: Path, relative: str, code: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise HistoryAccessV2Error(code, f"resource path escaped repository root: {relative}")
    root_resolved = root.resolve()
    resolved = (root / path).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise HistoryAccessV2Error(code, f"resource path escaped repository root: {relative}")
    return resolved


def _verified_repo_descriptor(root: Path, descriptor: dict[str, Any], code: str) -> bytes:
    relative = descriptor.get("resource_path") or descriptor.get("path")
    if not isinstance(relative, str):
        raise HistoryAccessV2Error(code, "resource descriptor path missing")
    path = _safe_path(root, relative, code)
    if not path.is_file():
        raise HistoryAccessV2Error(code, f"resource missing: {relative}")
    raw = path.read_bytes()
    if descriptor.get("size_bytes") != len(raw) or descriptor.get("sha256") != hashlib.sha256(raw).hexdigest():
        raise HistoryAccessV2Error("CHECKSUM_MISMATCH", f"resource integrity mismatch: {relative}")
    return raw


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
    collection_gaps = series.get("collection_gaps", [])
    if not isinstance(collection_gaps, list):
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "collection gaps must be an array")

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
        if series.get("coverage_semantics") == "FIXED_GRID" or not collection_gaps:
            raise HistoryAccessV2Error("HISTORY_NOT_FOUND", "ResolutionPlan v2 contains no physical segments or explicit sampled gaps")
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


def _validate_collection_run(segment: dict[str, Any], plan: dict[str, Any], root: Path) -> dict[str, Any] | None:
    evidence = segment.get("collection_run")
    if evidence is None:
        return None
    if not isinstance(evidence, dict) or not isinstance(evidence.get("ledger_resource"), dict):
        raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection run descriptor incomplete")
    raw = _verified_repo_descriptor(root, evidence["ledger_resource"], "COLLECTION_EVIDENCE_INVALID")
    ledger = json.loads(raw)
    if ledger.get("schema_version") != LEDGER_SCHEMA or not isinstance(ledger.get("runs"), list):
        raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection ledger schema mismatch")
    run = next((row for row in ledger["runs"] if row.get("run_id") == evidence.get("run_id")), None)
    if not isinstance(run, dict):
        raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection run missing from bound ledger")
    expected_ms = _parse_utc_ms(str(run.get("expected_schedule_at")))
    if (
        run.get("series_or_capability") != plan["series"]["series_id"]
        or run.get("status") != "OBSERVED_STATE"
        or run.get("snapshot_ref") != segment.get("resource_path")
        or expected_ms != segment.get("sampled_observation_at_ms")
        or run.get("known_at") != evidence.get("known_at")
        or run.get("retrieved_at") != evidence.get("retrieved_at")
    ):
        raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", f"collection run binding mismatch: {evidence.get('run_id')}")
    return run


def _validate_collection_gaps(plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for gap in plan["series"].get("collection_gaps", []):
        if not isinstance(gap, dict) or not isinstance(gap.get("ledger_resource"), dict):
            raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection gap descriptor incomplete")
        raw = _verified_repo_descriptor(root, gap["ledger_resource"], "COLLECTION_EVIDENCE_INVALID")
        ledger = json.loads(raw)
        if ledger.get("schema_version") != LEDGER_SCHEMA:
            raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection gap ledger schema mismatch")
        run = next((row for row in ledger.get("runs", []) if row.get("run_id") == gap.get("run_id")), None)
        if not isinstance(run, dict) or run.get("series_or_capability") != plan["series"]["series_id"]:
            raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", f"collection gap run binding mismatch: {gap.get('run_id')}")
        expected_ms = _parse_utc_ms(str(run.get("expected_schedule_at")))
        if expected_ms != gap.get("expected_schedule_at_ms"):
            raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection gap timestamp mismatch")
        if gap.get("error_class") == "SNAPSHOT_REF_MISSING":
            if run.get("status") != "OBSERVED_STATE":
                raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "missing snapshot gap must originate from observed ledger state")
        elif run.get("status") != gap.get("status") or run.get("status") == "OBSERVED_STATE":
            raise HistoryAccessV2Error("COLLECTION_EVIDENCE_INVALID", "collection gap status mismatch")
        verified.append({
            "run_id": gap["run_id"],
            "expected_schedule_at_ms": expected_ms,
            "status": gap.get("status"),
            "error_class": gap.get("error_class"),
        })
    return verified


def _normalize_sampled(payload: dict[str, Any], segment: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    kind = plan["series"]["series_kind"]
    if payload.get("schema_version") == COLD_ASSET_SCHEMA:
        if not _payload_identity_ok(payload, segment, plan["series"]["series_id"]):
            raise HistoryAccessV2Error("MEMBER_NOT_FOUND", "sampled COLD asset semantic identity mismatch")
        encoding = _record_encoding(payload, kind)
        if encoding.get("kind") != "SNAPSHOT_OBJECT":
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled COLD asset encoding mismatch")
        records = payload.get("records")
        if not isinstance(records, list):
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled COLD records missing")
        normalized = []
        for row in records:
            if isinstance(row, dict):
                ts = row.get("expected_schedule_at_ms")
                value = row.get("payload")
                if not isinstance(ts, int) or value is None:
                    raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled COLD row is not self-describing")
            elif isinstance(row, list) and len(row) == 2 and isinstance(row[0], int):
                ts, value = row
            else:
                raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid sampled COLD row")
            if segment["read_start_ms"] <= ts < segment["read_end_ms"]:
                normalized.append({"timestamp_ms": ts, "value": value, "_source_record": row})
        return normalized

    sampled_at = segment.get("sampled_observation_at_ms")
    if not isinstance(sampled_at, int):
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled WARM observation timestamp missing")
    if not (segment["read_start_ms"] <= sampled_at < segment["read_end_ms"]):
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled observation escapes segment")
    _validate_collection_run(segment, plan, Path(plan.get("_root", ".")))
    return [{"timestamp_ms": sampled_at, "value": payload, "_source_record": payload}]


def _normalize_records(raw: bytes, segment: dict[str, Any], plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "physical segment is not valid JSON") from exc
    series = plan["series"]
    if series["coverage_semantics"] != "FIXED_GRID":
        if payload.get("schema_version") == COLD_ASSET_SCHEMA:
            return _normalize_sampled(payload, segment, plan)
        _validate_collection_run(segment, plan, root)
        sampled_at = segment.get("sampled_observation_at_ms")
        if not isinstance(sampled_at, int):
            raise HistoryAccessV2Error("ARCHIVE_INVALID", "sampled observation timestamp missing")
        return [{"timestamp_ms": sampled_at, "value": payload, "_source_record": payload}]

    if not _payload_identity_ok(payload, segment, series["series_id"]):
        raise HistoryAccessV2Error("MEMBER_NOT_FOUND", "segment payload semantic identity mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
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
                normalized.append({"timestamp_ms": ts, "value": values, "_source_record": row})
        else:
            for row in records:
                if not isinstance(row, list) or ts_pos >= len(row):
                    raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid positional row")
                ts = row[ts_pos]
                if isinstance(ts, int) and segment["read_start_ms"] <= ts < segment["read_end_ms"]:
                    normalized.append({"timestamp_ms": ts, "value": {name: row[index] for index, name in enumerate(columns) if index != ts_pos and index < len(row)}, "_source_record": row})
    elif encoding["kind"] == "TIMESTAMP_VALUE":
        for row in records:
            if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], int):
                raise HistoryAccessV2Error("ARCHIVE_INVALID", "invalid timestamp/value row")
            if segment["read_start_ms"] <= row[0] < segment["read_end_ms"]:
                normalized.append({"timestamp_ms": row[0], "value": row[1], "_source_record": row})
    else:
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "snapshot encoding used for fixed-grid series")
    return normalized


def _revision_payload(root: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    raw = _verified_repo_descriptor(root, descriptor, "REVISION_INVALID")
    payload = json.loads(raw)
    if payload.get("schema_version") != REVISION_SCHEMA:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision evidence schema mismatch")
    return payload


def _verify_revision_source(root: Path, descriptor: dict[str, Any], evidence: dict[str, Any], plan: dict[str, Any]) -> None:
    source_descriptor = descriptor.get("source_snapshot")
    if not isinstance(source_descriptor, dict):
        raise HistoryAccessV2Error("REVISION_INVALID", "revision source snapshot descriptor missing")
    source_ref = evidence.get("source_snapshot_ref")
    descriptor_ref = source_descriptor.get("resource_path") or source_descriptor.get("path")
    if not isinstance(source_ref, str) or source_ref != descriptor_ref:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision source snapshot ref mismatch")
    raw = _verified_repo_descriptor(root, source_descriptor, "REVISION_INVALID")
    source = json.loads(raw)
    if (
        source.get("schema_version") != REVISION_SOURCE_SCHEMA
        or source.get("provider") != "kraken-futures"
        or source.get("instrument") != plan["series"].get("instrument")
        or source.get("metric") != plan["series"].get("source_interval_or_metric")
        or source.get("retrieved_at") != evidence.get("known_at_utc")
    ):
        raise HistoryAccessV2Error("REVISION_INVALID", "revision source snapshot identity mismatch")
    rows = source.get("observed_rows")
    if not isinstance(rows, list) or evidence.get("observed_value") not in rows:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision observed value not bound to source snapshot")


def _apply_revisions(
    observations: list[dict[str, Any]],
    segment: dict[str, Any],
    plan: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    descriptors = segment.get("revision_evidence", [])
    if not descriptors:
        return observations, []
    if plan["series"].get("revision_policy") != REVISABLE_CLASS:
        raise HistoryAccessV2Error("REVISION_INVALID", "revision evidence attached to non-revisable series")
    cutoff = plan["request"].get("cutoff_ms")
    by_timestamp = {item["timestamp_ms"]: item for item in observations}
    chosen: dict[int, tuple[int, str, dict[str, Any], dict[str, Any]]] = {}
    for descriptor in descriptors:
        evidence = _revision_payload(root, descriptor)
        known_at_ms = descriptor.get("known_at_ms")
        timestamp = evidence.get("effective_timestamp")
        revision_id = evidence.get("revision_id")
        expected_revision_of = f"kraken-futures/{plan['series'].get('instrument')}/{plan['series'].get('source_interval_or_metric')}/{timestamp}"
        if (
            evidence.get("classification") != REVISABLE_CLASS
            or evidence.get("provider") != "kraken-futures"
            or evidence.get("instrument") != plan["series"].get("instrument")
            or evidence.get("metric") != plan["series"].get("source_interval_or_metric")
            or evidence.get("revision_of") != expected_revision_of
            or not isinstance(known_at_ms, int)
            or not isinstance(timestamp, int)
            or not isinstance(revision_id, str)
            or descriptor.get("revision_id") != revision_id
            or descriptor.get("effective_timestamp_ms") != timestamp
        ):
            raise HistoryAccessV2Error("REVISION_INVALID", "revision descriptor/evidence identity mismatch")
        evidence_known_at = evidence.get("known_at_utc")
        if not isinstance(evidence_known_at, str) or _parse_utc_ms(evidence_known_at) != known_at_ms:
            raise HistoryAccessV2Error("REVISION_INVALID", "revision known-at binding mismatch")
        if cutoff is not None and known_at_ms > cutoff:
            continue
        base = by_timestamp.get(timestamp)
        if base is None:
            raise HistoryAccessV2Error("REVISION_INVALID", f"revision has no base observation: {timestamp}")
        source_record = base.get("_source_record")
        if evidence.get("previous_value_fingerprint") != _fingerprint(source_record):
            raise HistoryAccessV2Error("REVISION_INVALID", f"revision previous fingerprint mismatch: {timestamp}")
        observed = evidence.get("observed_value")
        if not isinstance(observed, list) or len(observed) < 2 or observed[0] != timestamp:
            raise HistoryAccessV2Error("REVISION_INVALID", "revision observed value mismatch")
        _verify_revision_source(root, descriptor, evidence, plan)
        current = chosen.get(timestamp)
        if current is not None and known_at_ms == current[0] and observed != current[2].get("observed_value"):
            raise HistoryAccessV2Error("REVISION_INVALID", f"ambiguous revision ordering: {timestamp}")
        if current is None or (known_at_ms, revision_id) > (current[0], current[1]):
            chosen[timestamp] = (known_at_ms, revision_id, evidence, descriptor)
    applied = []
    for timestamp, (known_at_ms, revision_id, evidence, descriptor) in chosen.items():
        by_timestamp[timestamp] = {
            "timestamp_ms": timestamp,
            "value": evidence["observed_value"][1],
            "revision_id": revision_id,
            "known_at_ms": known_at_ms,
            "_source_record": evidence["observed_value"],
        }
        applied.append({
            "timestamp_ms": timestamp,
            "revision_id": revision_id,
            "known_at_ms": known_at_ms,
            "evidence_path": descriptor.get("resource_path") or descriptor.get("path"),
            "source_snapshot_path": evidence["source_snapshot_ref"],
            "evidence_sha256": descriptor.get("sha256"),
        })
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
    collection_gaps = _validate_collection_gaps(plan, root)
    known_segment_gaps = []
    for segment in plan["segments"]:
        raw = _verified_bytes(segment, root=root, cache_dir=cache, opener=opener)
        observations = _normalize_records(raw, segment, plan, root)
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
        known_segment_gaps.extend(segment.get("known_gaps", []))
        sources.append({
            "segment_id": segment["segment_id"],
            "storage": segment["storage"],
            "generation_id": segment.get("generation_id"),
            "sha256": segment["sha256"],
            "rows": len(observations),
            "revision_evidence": len(segment.get("revision_evidence", [])),
            "collection_run_id": segment.get("collection_run", {}).get("run_id") if isinstance(segment.get("collection_run"), dict) else None,
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

    boundary = series.get("coverage_boundary_evidence", {})
    boundary_unavailable = max(0, int(boundary.get("effective_start_ms", effective_start)) - int(boundary.get("requested_start_ms", request["start_ms"])))
    degraded = bool(missing or collection_gaps or known_segment_gaps or boundary_unavailable)

    public_observations = []
    for item in observations:
        clean = {key: value for key, value in item.items() if key != "_source_record"}
        public_observations.append(clean)
    receipt = build_semantic_receipt(
        series_id=series["series_id"],
        start_ms=request["start_ms"],
        end_ms=request["end_ms"],
        cutoff_ms=request.get("cutoff_ms"),
        mode=mode,
        current_policy=request.get("current_policy", "FINALIZED_ONLY"),
        resolution_plan_sha256=plan["plan_sha256"],
        observations=public_observations,
        finality="PROVISIONAL_INCLUDED" if provisional else "FINALIZED",
        revision_context=_receipt_revision_context(revisions, request.get("cutoff_ms")),
    )
    diagnostics = {
        "schema_version": DIAGNOSTICS_SCHEMA,
        "plan_sha256": plan["plan_sha256"],
        "series_id": series["series_id"],
        "series_kind": series["series_kind"],
        "coverage_semantics": series["coverage_semantics"],
        "requested_start": _iso(request["start_ms"]),
        "effective_start": _iso(effective_start),
        "requested_end": _iso(request["end_ms"]),
        "rows": len(public_observations),
        "internal_gap_count": len(missing),
        "missing_intervals_ms": missing,
        "collection_gap_count": len(collection_gaps),
        "collection_gaps": collection_gaps,
        "known_segment_gaps": known_segment_gaps,
        "provider_boundary": boundary if boundary_unavailable else None,
        "overlap_deduped_timestamps_ms": sorted(set(overlaps)),
        "revisions_applied": revisions,
        "provisional_included": provisional,
        "status": "DEGRADED" if degraded else "PASS",
        "sources": sources,
        "receipt": receipt,
    }
    return public_observations, diagnostics
