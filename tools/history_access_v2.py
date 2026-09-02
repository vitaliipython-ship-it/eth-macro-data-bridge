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
from canonical_json import canonical_json_bytes

PLAN_SCHEMA = "market-data-resolution-plan/2.0.0"
DIAGNOSTICS_SCHEMA = "history-access-diagnostics/2.0.0"
RECEIPT_SCHEMA = "history-access-receipt/2.0.0"
COLD_ASSET_SCHEMA = "market-data-cold-asset/1.1.0"
LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
REVISION_SCHEMA = "market-data-provider-revision/1.0.0"
REVISION_SOURCE_SCHEMA = "kraken-revision-source-observation/1.0.0"
REVISABLE_CLASS = "PROVIDER_REVISABLE_SNAPSHOT"
G2B_FAMILY = "liquidity.orderbook-snapshots"
G2B_CONTRACT_PATH = "contracts/liquidity-durable-l2-observation-v1.json"
G2B_CONTRACT_ID = "ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1"
G2B_CONTRACT_SCHEMA = "eth-liquidity-durable-l2-observation-contract/1.0.0"
G2B_PARTITION_SCHEMA = "liquidity-durable-l2-observation-partition/1.0.0"
G2B_OBSERVATION_SCHEMA = "liquidity-durable-l2-observation/1.0.0"
G2B_LEGACY_SCHEMA = "1.0.0"
G2B_LOCATOR_PATTERN = "history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json"
G2B_LEGACY_CLASS = "LEGACY_LIQUIDITY_SNAPSHOT"
G2B_SUCCESSOR_CLASS = "SUCCESSOR_DURABLE_L2"


class HistoryAccessV2Error(v1.HistoryAccessError):
    pass


def compact(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _canonical(value: Any) -> bytes:
    return canonical_json_bytes(value)


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


def _validate_g2b_binding(binding: Any) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "G2-B schema binding missing")
    required = {
        "contract_id": G2B_CONTRACT_ID,
        "contract_path": G2B_CONTRACT_PATH,
        "history_family": G2B_FAMILY,
        "legacy_schema": G2B_LEGACY_SCHEMA,
        "partition_schema": G2B_PARTITION_SCHEMA,
        "observation_schema": G2B_OBSERVATION_SCHEMA,
        "locator_pattern": G2B_LOCATOR_PATTERN,
    }
    if any(binding.get(key) != value for key, value in required.items()):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "G2-B schema authority binding mismatch")
    resource = binding.get("contract_resource")
    if not isinstance(resource, dict) or resource.get("resource_path") != G2B_CONTRACT_PATH:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "G2-B contract resource binding missing")
    if not isinstance(resource.get("sha256"), str) or len(resource["sha256"]) != 64 or not isinstance(resource.get("size_bytes"), int):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "G2-B contract resource integrity binding invalid")
    return binding


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
    cutoff = request.get("cutoff_ms")
    if cutoff is not None and (not isinstance(cutoff, int) or end > cutoff):
        raise HistoryAccessV2Error("INVALID_RESOLUTION_PLAN", "point-in-time cutoff does not cover request")
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

    g2b_binding = None
    if series.get("series_id") == G2B_FAMILY:
        g2b_binding = _validate_g2b_binding(plan.get("authority", {}).get("liquidity_durable_l2_contract"))

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
        if g2b_binding is not None:
            schema_class = segment.get("schema_class")
            if schema_class not in {G2B_LEGACY_CLASS, G2B_SUCCESSOR_CLASS}:
                raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "liquidity segment lacks explicit legacy/successor schema class")
            if segment.get("schema_binding") != g2b_binding:
                raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "liquidity segment schema binding diverges from plan authority")
            if schema_class == G2B_LEGACY_CLASS:
                if not isinstance(segment.get("collection_run"), dict) or not isinstance(segment.get("sampled_observation_at_ms"), int):
                    raise HistoryAccessV2Error("G2B_LEGACY_AS_SUCCESSOR_COERCION_FORBIDDEN", "legacy liquidity evidence binding missing")
            else:
                if segment.get("source_manifest_path") != G2B_CONTRACT_PATH or segment.get("collection_run") is not None:
                    raise HistoryAccessV2Error("G2B_SUCCESSOR_AS_LEGACY_COERCION_FORBIDDEN", "successor segment authority shape invalid")
                bindings = segment.get("successor_observations")
                if not isinstance(bindings, list) or not bindings:
                    raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "successor observation bindings missing")
                for row in bindings:
                    if not isinstance(row, dict):
                        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "successor observation binding invalid")
                    for key in ("durable_identity_sha256", "observation_sha256", "durable_record_sha256"):
                        if not isinstance(row.get(key), str) or len(row[key]) != 64:
                            raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", f"successor {key} invalid")
                    if not isinstance(row.get("observation_time_ms"), int) or not isinstance(row.get("known_at_ms"), int):
                        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "successor temporal binding missing")
                    if not (segment["read_start_ms"] <= row["observation_time_ms"] < segment["read_end_ms"]):
                        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor observation escapes segment range")
                    if cutoff is not None and row["known_at_ms"] > cutoff:
                        raise HistoryAccessV2Error("G2B_KNOWN_AT_AFTER_CUTOFF", "successor observation was not known by requested cutoff")
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
    cutoff = plan["request"].get("cutoff_ms")
    known_at_ms = _parse_utc_ms(str(run.get("known_at")))
    if cutoff is not None and known_at_ms > cutoff:
        raise HistoryAccessV2Error("G2B_KNOWN_AT_AFTER_CUTOFF", "legacy collection run was not known by requested cutoff")
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


def _verify_g2b_contract(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    binding = _validate_g2b_binding(binding)
    raw = _verified_repo_descriptor(root, binding["contract_resource"], "G2B_SCHEMA_POLICY_CONFLICT")
    try:
        contract = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "durable L2 contract is not valid JSON") from exc
    if (
        contract.get("schema_version") != G2B_CONTRACT_SCHEMA
        or contract.get("contract_id") != G2B_CONTRACT_ID
        or contract.get("family", {}).get("family_id") != G2B_FAMILY
        or contract.get("storage_independence", {}).get("durable_l2_physical_locator") != G2B_LOCATOR_PATTERN
        or contract.get("legacy_compatibility", {}).get("legacy_snapshot_schema_version") != G2B_LEGACY_SCHEMA
        or contract.get("market_time", {}).get("known_at_after_cutoff_excluded") is not True
    ):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "durable L2 contract semantic binding mismatch")
    reuse = contract.get("authority_reuse", {})
    if any(reuse.get(key) is not False for key in ("second_history_reader", "second_capability_catalog", "second_temporal_authority")):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "durable L2 contract permits duplicate reader/catalog/temporal authority")
    return contract


def _g2b_expected_path(binding: dict[str, Any], timestamp_ms: int) -> str:
    day = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
    return (
        binding["locator_pattern"]
        .replace("YYYY", f"{day.year:04d}")
        .replace("MM", f"{day.month:02d}")
        .replace("DD", f"{day.day:02d}")
    )


def _validate_g2b_observation(observation: Any) -> dict[str, Any]:
    if not isinstance(observation, dict) or observation.get("schema_version") != G2B_OBSERVATION_SCHEMA:
        raise HistoryAccessV2Error("G2B_UNKNOWN_LIQUIDITY_OBSERVATION_SCHEMA", "unknown or missing successor observation schema")
    if observation.get("history_family") != G2B_FAMILY:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor history family mismatch")
    for key in ("provider_id", "instrument_id", "book_kind", "observation_id"):
        if not isinstance(observation.get(key), str) or not observation[key]:
            raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", f"successor identity field missing: {key}")
    for key in ("observation_sha256", "durable_identity_sha256", "durable_record_sha256"):
        if not isinstance(observation.get(key), str) or len(observation[key]) != 64:
            raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", f"successor integrity field missing: {key}")
    timestamp = observation.get("observation_time_ms")
    if not isinstance(timestamp, int):
        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "successor observation_time_ms missing")
    if not isinstance(observation.get("observation_time_utc"), str) or _parse_utc_ms(observation["observation_time_utc"]) != timestamp:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor observation time binding mismatch")
    known_at = observation.get("known_at_utc")
    if not isinstance(known_at, str):
        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "successor known_at_utc missing")
    known_at_ms = _parse_utc_ms(known_at)
    if known_at_ms < timestamp:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor known-at precedes market observation")
    if observation.get("observation_time_role") != "MARKET_OBSERVATION_TIME" or observation.get("known_at_role") != "WHEN_THE_OBSERVATION_BECAME_KNOWN_TO_THE_EXECUTION_PATH":
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor temporal roles mismatch")
    for key in ("generation_time_is_observation_time", "publication_time_is_observation_time", "request_time_is_observation_time"):
        if observation.get(key) is not False:
            raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", f"successor temporal authority widened: {key}")
    book = observation.get("normalized_book")
    if not isinstance(book, dict) or book.get("schema_version") != "liquidity-s1-normalized-book/1.0.0":
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor normalized book schema mismatch")
    identity_fields = ("provider_id", "instrument_id", "book_kind", "observation_id", "observation_sha256")
    if any(book.get(key) != observation.get(key) for key in identity_fields):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor outer/normalized observation identity mismatch")
    if book.get("timestamp_ms") != timestamp:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor normalized book timestamp mismatch")
    book_body = dict(book)
    book_sha = book_body.pop("observation_sha256", None)
    if book_sha != _fingerprint(book_body):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor normalized book hash mismatch")
    identity_body = {key: observation[key] for key in ("provider_id", "instrument_id", "book_kind", "observation_id")}
    if observation["durable_identity_sha256"] != _fingerprint(identity_body):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor durable identity hash mismatch")
    body = dict(observation)
    body.pop("durable_record_sha256", None)
    if observation["durable_record_sha256"] != _fingerprint(body):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor durable record hash mismatch")
    coverage = observation.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("extrapolation_allowed") is not False:
        raise HistoryAccessV2Error("G2B_EXTRAPOLATION_FORBIDDEN", "successor coverage permits extrapolation or is missing")
    if coverage.get("history_target_bps") != 500:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor history target binding mismatch")
    if coverage.get("achieved_bid_coverage_bps") != book.get("achieved_bid_coverage_bps") or coverage.get("achieved_ask_coverage_bps") != book.get("achieved_ask_coverage_bps"):
        raise HistoryAccessV2Error("G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN", "successor achieved coverage differs from stored normalized book")
    for key in ("coverage_complete_bid", "coverage_complete_ask", "truncated"):
        if not isinstance(coverage.get(key), bool):
            raise HistoryAccessV2Error("G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN", f"successor completeness field invalid: {key}")
    if coverage["truncated"] is not (not (coverage["coverage_complete_bid"] and coverage["coverage_complete_ask"])):
        raise HistoryAccessV2Error("G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN", "successor truncated/completeness relation inconsistent")
    quantity = observation.get("quantity_semantics")
    if not isinstance(quantity, dict) or quantity.get("schema_version") != "liquidity-s1-quantity-semantics/1.0.0":
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor quantity semantics schema mismatch")
    quantity_body = dict(quantity)
    quantity_sha = quantity_body.pop("quantity_sha256", None)
    if quantity_sha != _fingerprint(quantity_body):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor quantity semantics hash mismatch")
    provenance = observation.get("provenance")
    stable = (
        "provider_plan_sha256", "provider_capability_sha256", "s3_execution_policy_sha256",
        "s3_execution_receipt_sha256", "provider_endpoint_binding_sha256", "physical_action_sha256",
        "one_observation_proof", "one_request_or_session_proof", "provider_specific_integrity_or_coherence_evidence_sha256",
    )
    if not isinstance(provenance, dict) or any(key not in provenance for key in stable):
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor stable provenance incomplete")
    for key in stable[:6] + stable[-1:]:
        if not isinstance(provenance.get(key), str) or len(provenance[key]) != 64:
            raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", f"successor provenance hash invalid: {key}")
    if provenance.get("one_observation_proof") is not True or provenance.get("one_request_or_session_proof") is not True:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor one-observation/request proof invalid")
    return {**observation, "_known_at_ms": known_at_ms}


def _g2b_binding_row(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "durable_identity_sha256": observation["durable_identity_sha256"],
        "observation_sha256": observation["observation_sha256"],
        "durable_record_sha256": observation["durable_record_sha256"],
        "observation_time_ms": observation["observation_time_ms"],
        "known_at_ms": observation["_known_at_ms"],
        "provider_id": observation["provider_id"],
        "instrument_id": observation["instrument_id"],
        "book_kind": observation["book_kind"],
        "observation_id": observation["observation_id"],
    }


def _normalize_g2b_successor(payload: dict[str, Any], segment: dict[str, Any], plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    binding = _validate_g2b_binding(segment.get("schema_binding"))
    _verify_g2b_contract(root, binding)
    expected_path = segment.get("resource_path") or segment.get("physical_descriptor", {}).get("resource_path")
    if (
        payload.get("schema_version") != G2B_PARTITION_SCHEMA
        or payload.get("history_family") != G2B_FAMILY
        or not isinstance(payload.get("date_utc"), str)
        or not isinstance(payload.get("observations"), list)
    ):
        raise HistoryAccessV2Error("G2B_UNKNOWN_LIQUIDITY_PARTITION_SCHEMA", "unknown or missing successor partition schema")
    cutoff = plan["request"].get("cutoff_ms")
    selected: dict[str, dict[str, Any]] = {}
    seen: dict[str, str] = {}
    for raw_observation in payload["observations"]:
        observation = _validate_g2b_observation(raw_observation)
        identity = observation["durable_identity_sha256"]
        previous_sha = seen.get(identity)
        if previous_sha is not None and previous_sha != observation["observation_sha256"]:
            raise HistoryAccessV2Error("G2B_IMMUTABLE_OBSERVATION_CONFLICT", "same durable identity has different observation sha")
        seen[identity] = observation["observation_sha256"]
        if _g2b_expected_path(binding, observation["observation_time_ms"]) != expected_path:
            raise HistoryAccessV2Error("G2B_GUESSED_PATH_FORBIDDEN", "successor observation is not in contract-derived daily partition")
        timestamp = observation["observation_time_ms"]
        if not (segment["read_start_ms"] <= timestamp < segment["read_end_ms"]):
            continue
        if cutoff is not None and observation["_known_at_ms"] > cutoff:
            continue
        if identity not in selected:
            selected[identity] = observation
    actual_bindings = sorted((_g2b_binding_row(row) for row in selected.values()), key=lambda row: (row["observation_time_ms"], row["durable_identity_sha256"]))
    planned = segment.get("successor_observations")
    if actual_bindings != planned:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "successor ResolutionPlan membership does not match physical PIT/schema authority")
    result = []
    for observation in sorted(selected.values(), key=lambda row: (row["observation_time_ms"], row["durable_identity_sha256"])):
        clean_observation = {key: value for key, value in observation.items() if key != "_known_at_ms"}
        result.append({
            "timestamp_ms": observation["observation_time_ms"],
            "schema_class": G2B_SUCCESSOR_CLASS,
            "schema_version": G2B_OBSERVATION_SCHEMA,
            "durable_identity_sha256": observation["durable_identity_sha256"],
            "observation_sha256": observation["observation_sha256"],
            "known_at_ms": observation["_known_at_ms"],
            "value": clean_observation,
            "_source_record": clean_observation,
        })
    return result


def _normalize_g2b_legacy(payload: dict[str, Any], segment: dict[str, Any], plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    binding = _validate_g2b_binding(segment.get("schema_binding"))
    _verify_g2b_contract(root, binding)
    if payload.get("schema_version") != G2B_LEGACY_SCHEMA or payload.get("history_family") == G2B_FAMILY:
        raise HistoryAccessV2Error("G2B_LEGACY_AS_SUCCESSOR_COERCION_FORBIDDEN", "legacy liquidity payload schema mismatch")
    run = _validate_collection_run(segment, plan, root)
    sampled_at = segment.get("sampled_observation_at_ms")
    if not isinstance(sampled_at, int) or payload.get("timestamp_ms") != sampled_at:
        raise HistoryAccessV2Error("G2B_SCHEMA_POLICY_CONFLICT", "legacy liquidity timestamp binding mismatch")
    known_at_ms = _parse_utc_ms(str(run.get("known_at"))) if isinstance(run, dict) else None
    return [{
        "timestamp_ms": sampled_at,
        "schema_class": G2B_LEGACY_CLASS,
        "schema_version": G2B_LEGACY_SCHEMA,
        "known_at_ms": known_at_ms,
        "legacy_run_id": run.get("run_id") if isinstance(run, dict) else None,
        "value": payload,
        "_source_record": payload,
    }]


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
    return [{"timestamp_ms": sampled_at, "value": payload, "_source_record": payload}]


def _normalize_records(raw: bytes, segment: dict[str, Any], plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryAccessV2Error("ARCHIVE_INVALID", "physical segment is not valid JSON") from exc
    series = plan["series"]
    if series["series_id"] == G2B_FAMILY:
        schema_class = segment.get("schema_class")
        if schema_class == G2B_SUCCESSOR_CLASS:
            return _normalize_g2b_successor(payload, segment, plan, root)
        if schema_class == G2B_LEGACY_CLASS:
            if payload.get("schema_version") == G2B_PARTITION_SCHEMA:
                raise HistoryAccessV2Error("G2B_SUCCESSOR_AS_LEGACY_COERCION_FORBIDDEN", "successor partition presented as legacy")
            return _normalize_g2b_legacy(payload, segment, plan, root)
        raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "liquidity segment schema class missing")
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


def _merge_key(item: dict[str, Any], series_id: str) -> tuple[Any, ...]:
    if series_id != G2B_FAMILY:
        return ("timestamp", item["timestamp_ms"])
    if item.get("schema_class") == G2B_SUCCESSOR_CLASS:
        return (G2B_SUCCESSOR_CLASS, item.get("durable_identity_sha256"))
    if item.get("schema_class") == G2B_LEGACY_CLASS:
        return (G2B_LEGACY_CLASS, item["timestamp_ms"], item.get("legacy_run_id"))
    raise HistoryAccessV2Error("G2B_MISSING_LIQUIDITY_SCHEMA", "liquidity observation schema class missing at merge")


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
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
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
            key = _merge_key(item, plan["series"]["series_id"])
            previous = merged.get(key)
            if previous is None:
                merged[key] = item
            elif plan["series"]["series_id"] == G2B_FAMILY and item.get("schema_class") == G2B_SUCCESSOR_CLASS:
                if previous.get("observation_sha256") != item.get("observation_sha256") or previous.get("value") != item.get("value"):
                    raise HistoryAccessV2Error("G2B_IMMUTABLE_OBSERVATION_CONFLICT", "same durable identity has conflicting materialization")
                overlaps.append(item["timestamp_ms"])
            elif previous.get("value") == item.get("value"):
                overlaps.append(item["timestamp_ms"])
                if previous.get("finality") == "PROVISIONAL" and item.get("finality") == "FINALIZED":
                    merged[key] = item
            else:
                raise HistoryAccessV2Error("DUPLICATE_CONFLICT", f"cross-tier semantic mismatch at {item['timestamp_ms']}")
        known_segment_gaps.extend(segment.get("known_gaps", []))
        sources.append({
            "segment_id": segment["segment_id"],
            "storage": segment["storage"],
            "generation_id": segment.get("generation_id"),
            "sha256": segment["sha256"],
            "rows": len(observations),
            "schema_class": segment.get("schema_class"),
            "revision_evidence": len(segment.get("revision_evidence", [])),
            "collection_run_id": segment.get("collection_run", {}).get("run_id") if isinstance(segment.get("collection_run"), dict) else None,
        })

    observations = sorted(
        merged.values(),
        key=lambda item: (
            item["timestamp_ms"],
            item.get("schema_class", ""),
            item.get("durable_identity_sha256", ""),
            item.get("legacy_run_id", ""),
        ),
    )
    request = plan["request"]
    series = plan["series"]
    effective_start = request.get("effective_start_ms", request["start_ms"])
    missing: list[int] = []
    if series["coverage_semantics"] == "FIXED_GRID":
        interval = series["interval_ms"]
        expected = list(range(effective_start, request["end_ms"], interval))
        actual = {item["timestamp_ms"] for item in observations}
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
    schema_counts: dict[str, int] = {}
    for item in public_observations:
        schema_class = item.get("schema_class")
        if isinstance(schema_class, str):
            schema_counts[schema_class] = schema_counts.get(schema_class, 0) + 1
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
        "schema_class_counts": schema_counts,
        "mixed_schema_policy": "EXPLICIT_SCHEMA_BOUNDARY" if series["series_id"] == G2B_FAMILY else None,
        "status": "DEGRADED" if degraded else "PASS",
        "sources": sources,
        "receipt": receipt,
    }
    return public_observations, diagnostics
