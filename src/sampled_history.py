from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from canonical_json import canonical_json_bytes, sha256_canonical_json
from capability_index import describe_requestable_capability
from current_data_request_scope import _build_s2_plan, _s1_provider_capability
from history_store import ImmutableHistoryConflict, append_partition, atomic_json
from liquidity_s1_runtime import (
    normalize_liquidity_request,
    plan_liquidity_acquisition,
    validate_qualified_liquidity_resource,
)
from liquidity_s3_executor import execute_s3

LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
SAMPLED_SCHEMA = "market-data-sampled-observation/1.0.0"
G2A_OBSERVATION_SCHEMA = "liquidity-durable-l2-observation/1.0.0"
G2A_PARTITION_SCHEMA = "liquidity-durable-l2-observation-partition/1.0.0"
G2A_BENCHMARK_SCHEMA = "liquidity-g2a-successor-byte-benchmark/1.0.0"
G2A_FRESH_CURRENT_TRANSFER_SCHEMA = "liquidity-g2a-fresh-current-transfer/1.0.0"
G2A_FRESH_CURRENT_TRANSFER_PATH = Path("g2a-durable-observations/index.json")
G2A_HISTORY_TARGET_BPS = "500"
G2A_BUCKET_BPS = "50"
G2A_BASELINE_CAPABILITIES = (
    ("liquidity.binance-spot.ETHUSDT.orderbook", "binance-spot", "ETHUSDT", "L2_LEVEL_BOOK"),
    ("liquidity.binance-spot.BTCUSDT.orderbook", "binance-spot", "BTCUSDT", "L2_LEVEL_BOOK"),
    ("liquidity.kraken-spot.ETHUSD.orderbook", "kraken-spot", "ETHUSD", "L2_LEVEL_BOOK"),
    ("liquidity.kraken-spot.BTCUSD.orderbook", "kraken-spot", "BTCUSD", "L2_LEVEL_BOOK"),
    ("liquidity.kraken-futures.PI_ETHUSD.orderbook", "kraken-futures", "PI_ETHUSD", "FUTURES_L2_BOOK"),
    ("liquidity.kraken-futures.PI_XBTUSD.orderbook", "kraken-futures", "PI_XBTUSD", "FUTURES_L2_BOOK"),
)


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y/%m/%d")


def date_text(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def freshness(provider_timestamp_ms: int | None, completed_ms: int, target_cadence_seconds: int) -> dict[str, Any]:
    if provider_timestamp_ms is None:
        return {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": target_cadence_seconds}
    age = max(0, (completed_ms - provider_timestamp_ms) // 1000)
    if age <= target_cadence_seconds * 2:
        status = "LIVE_USABLE"
    elif age <= target_cadence_seconds * 6:
        status = "RECENT_CONTEXT"
    else:
        status = "STALE_FOR_CURRENT"
    return {"status": status, "age_seconds": age, "target_cadence_seconds": target_cadence_seconds}


def g2a_semantic_requests() -> list[dict[str, Any]]:
    requests = []
    for series_id, provider_id, instrument_id, book_kind in G2A_BASELINE_CAPABILITIES:
        requests.append(
            normalize_liquidity_request(
                {
                    "series_id": series_id,
                    "provider_id": provider_id,
                    "instrument_id": instrument_id,
                    "book_kind": book_kind,
                    "representation": "RAW",
                    "target_bps": G2A_HISTORY_TARGET_BPS,
                    "requested_bid_coverage_bps": G2A_HISTORY_TARGET_BPS,
                    "requested_ask_coverage_bps": G2A_HISTORY_TARGET_BPS,
                    "bucket_bps": G2A_BUCKET_BPS,
                    "freshness": {"max_age_seconds": 600},
                    "completeness": {"required": False},
                }
            )
        )
    return requests


def acquire_g2a_baseline(*, transport: Any | None = None) -> list[dict[str, Any]]:
    acquisitions: list[dict[str, Any]] = []
    for semantic_request in g2a_semantic_requests():
        capability = describe_requestable_capability(str(semantic_request["series_id"]))
        if capability["provider_id"] == "binance-usdm":
            raise RuntimeError("BINANCE_USDM_GITHUB_NETWORK_CALL_FORBIDDEN")
        provider_capability = _s1_provider_capability(capability)
        s1_planner_result = plan_liquidity_acquisition(semantic_request, provider_capability)
        if s1_planner_result["decision"] != "ACQUISITION_REQUIRED" or s1_planner_result["network_required"] is not True:
            raise RuntimeError("G2A_S1_ACQUISITION_PLAN_INVALID")
        s2_provider_plan = _build_s2_plan(str(semantic_request["provider_id"]), s1_planner_result)
        execution = execute_s3(
            semantic_request,
            s1_planner_result,
            s2_provider_plan,
            transport=transport,
            execution_plane="GITHUB_ACTIONS",
        )
        if execution.get("status") != "PASS" or not isinstance(execution.get("qualified_resource"), Mapping):
            receipt = execution.get("receipt")
            safe_receipt = receipt if isinstance(receipt, Mapping) else {}
            diagnostic = {
                "series_id": semantic_request["series_id"],
                "provider_id": semantic_request["provider_id"],
                "instrument_id": semantic_request["instrument_id"],
                "status": execution.get("status"),
                "terminal_status": safe_receipt.get("terminal_status"),
                "error_class": safe_receipt.get("error_class"),
                "http_status_code": safe_receipt.get("http_status_code"),
                "network_attempt_count": safe_receipt.get("network_attempt_count"),
                "provider_request_or_session_count": safe_receipt.get("provider_request_or_session_count"),
                "raw_message_count": safe_receipt.get("raw_message_count"),
                "raw_observation_bytes": safe_receipt.get("raw_observation_bytes"),
                "physical_route_kind": safe_receipt.get("physical_route_kind"),
                "provider_plan_sha256": safe_receipt.get("provider_plan_sha256"),
                "provider_endpoint_binding_sha256": safe_receipt.get("provider_endpoint_binding_sha256"),
                "physical_action_sha256": safe_receipt.get("physical_action_sha256"),
            }
            print(
                "G2A_S3_FAILURE_DIAGNOSTIC_JSON="
                + json.dumps(diagnostic, sort_keys=True, separators=(",", ":"))
            )
            raise RuntimeError(
                "SIX_CAPABILITY_COHERENT_ACQUISITION_FAILED:"
                + str(semantic_request["series_id"])
            )
        resource = validate_qualified_liquidity_resource(execution["qualified_resource"])
        if resource["coherent_observation"] is not True:
            raise RuntimeError(
                "SIX_CAPABILITY_COHERENT_ACQUISITION_FAILED:"
                + str(semantic_request["series_id"])
            )
        acquisitions.append(
            {
                "semantic_request": semantic_request,
                "s1_planner_result": s1_planner_result,
                "s2_provider_plan": s2_provider_plan,
                "execution_receipt": execution["receipt"],
                "qualified_resource": resource,
            }
        )
    expected = {row[0] for row in G2A_BASELINE_CAPABILITIES}
    actual = {row["semantic_request"]["series_id"] for row in acquisitions}
    if len(acquisitions) != 6 or actual != expected:
        raise RuntimeError("G2A_SIX_CAPABILITY_BASELINE_MISMATCH")
    return acquisitions


def build_durable_l2_observation(acquisition: Mapping[str, Any]) -> dict[str, Any]:
    resource = validate_qualified_liquidity_resource(acquisition["qualified_resource"])
    book = resource["normalized_book"]
    s2_provider_plan = acquisition.get("s2_provider_plan")
    execution_receipt = acquisition.get("execution_receipt")
    if not isinstance(s2_provider_plan, Mapping) or not isinstance(execution_receipt, Mapping):
        raise ValueError("G2A_ACQUISITION_PROVENANCE_MISSING")
    required_receipt_fields = (
        "execution_policy_sha256",
        "provider_plan_sha256",
        "provider_endpoint_binding_sha256",
        "physical_action_sha256",
        "execution_receipt_sha256",
    )
    if any(not isinstance(execution_receipt.get(field), str) for field in required_receipt_fields):
        raise ValueError("G2A_S3_PROVENANCE_INCOMPLETE")
    provider_capability_sha = s2_provider_plan.get("provider_capability_sha256")
    if not isinstance(provider_capability_sha, str):
        raise ValueError("G2A_PROVIDER_CAPABILITY_PROVENANCE_MISSING")
    if execution_receipt.get("terminal_status") != "SUCCESS_OBSERVATION_CAPTURED":
        raise ValueError("G2A_S3_TERMINAL_STATUS_INVALID")
    if execution_receipt.get("terminal_observation_count") != 1:
        raise ValueError("G2A_ONE_OBSERVATION_PROOF_INVALID")
    if execution_receipt.get("provider_request_or_session_count") != 1:
        raise ValueError("G2A_ONE_REQUEST_OR_SESSION_PROOF_INVALID")
    if execution_receipt.get("network_attempt_count") != 1:
        raise ValueError("G2A_ONE_REQUEST_OR_SESSION_PROOF_INVALID")
    temporal = resource["temporal_provenance"]
    identity_material = {
        "provider_id": resource["provider_id"],
        "instrument_id": resource["instrument_id"],
        "book_kind": resource["book_kind"],
        "observation_id": resource["observation_id"],
    }
    provider_integrity_evidence = {
        "provider_id": resource["provider_id"],
        "instrument_id": resource["instrument_id"],
        "book_kind": resource["book_kind"],
        "provider_capability_sha256": provider_capability_sha,
        "physical_route_kind": execution_receipt.get("physical_route_kind"),
        "terminal_status": execution_receipt.get("terminal_status"),
        "ws_subscription_acknowledged": execution_receipt.get("ws_subscription_acknowledged"),
        "coherent_observation": resource["coherent_observation"],
        "observation_sha256": resource["observation_sha256"],
    }
    record = {
        "schema_version": G2A_OBSERVATION_SCHEMA,
        "history_family": "liquidity.orderbook-snapshots",
        "provider_id": resource["provider_id"],
        "instrument_id": resource["instrument_id"],
        "book_kind": resource["book_kind"],
        "observation_id": resource["observation_id"],
        "observation_sha256": resource["observation_sha256"],
        "durable_identity_sha256": sha256_canonical_json(identity_material),
        "observation_time_ms": int(book["timestamp_ms"]),
        "observation_time_utc": iso(int(book["timestamp_ms"])),
        "known_at_utc": temporal["evaluated_at_utc"],
        "observation_time_role": "MARKET_OBSERVATION_TIME",
        "known_at_role": "WHEN_THE_OBSERVATION_BECAME_KNOWN_TO_THE_EXECUTION_PATH",
        "generation_time_is_observation_time": False,
        "publication_time_is_observation_time": False,
        "request_time_is_observation_time": False,
        "coverage": {
            "history_target_bps": G2A_HISTORY_TARGET_BPS,
            "achieved_bid_coverage_bps": resource["achieved_bid_coverage_bps"],
            "achieved_ask_coverage_bps": resource["achieved_ask_coverage_bps"],
            "coverage_complete_bid": resource["coverage_complete_bid"],
            "coverage_complete_ask": resource["coverage_complete_ask"],
            "truncated": resource["truncated"],
            "extrapolation_allowed": False,
        },
        "quantity_semantics": resource["quantity_semantics"],
        "normalized_book": book,
        "provenance": {
            "capability_series_id": resource["series_id"],
            "provider_plan_sha256": execution_receipt["provider_plan_sha256"],
            "provider_capability_sha256": provider_capability_sha,
            "s3_execution_policy_sha256": execution_receipt["execution_policy_sha256"],
            "s3_execution_receipt_sha256": execution_receipt["execution_receipt_sha256"],
            "provider_endpoint_binding_sha256": execution_receipt["provider_endpoint_binding_sha256"],
            "physical_action_sha256": execution_receipt["physical_action_sha256"],
            "one_observation_proof": True,
            "one_request_or_session_proof": True,
            "provider_specific_integrity_or_coherence_evidence_sha256": sha256_canonical_json(provider_integrity_evidence),
        },
    }
    record["durable_record_sha256"] = sha256_canonical_json(record)
    return record


def serialize_durable_l2_observation(record: Mapping[str, Any]) -> bytes:
    if record.get("schema_version") != G2A_OBSERVATION_SCHEMA:
        raise ValueError("G2A_DURABLE_OBSERVATION_SCHEMA_INVALID")
    if record.get("observation_sha256") != record.get("normalized_book", {}).get("observation_sha256"):
        raise ValueError("G2A_OBSERVATION_CONTENT_BINDING_INVALID")
    if record.get("coverage", {}).get("extrapolation_allowed") is not False:
        raise ValueError("G2A_EXTRAPOLATION_FORBIDDEN")
    if record.get("generation_time_is_observation_time") is not False:
        raise ValueError("SECOND_TEMPORAL_AUTHORITY_INTRODUCED")
    if record.get("publication_time_is_observation_time") is not False:
        raise ValueError("SECOND_TEMPORAL_AUTHORITY_INTRODUCED")
    if record.get("request_time_is_observation_time") is not False:
        raise ValueError("SECOND_TEMPORAL_AUTHORITY_INTRODUCED")
    provenance = record.get("provenance")
    required_provenance = {
        "provider_plan_sha256",
        "provider_capability_sha256",
        "s3_execution_policy_sha256",
        "s3_execution_receipt_sha256",
        "provider_endpoint_binding_sha256",
        "physical_action_sha256",
        "one_observation_proof",
        "one_request_or_session_proof",
        "provider_specific_integrity_or_coherence_evidence_sha256",
    }
    if not isinstance(provenance, Mapping) or not required_provenance.issubset(provenance):
        raise ValueError("G2A_COMPACT_PROVENANCE_INCOMPLETE")
    if provenance.get("one_observation_proof") is not True or provenance.get("one_request_or_session_proof") is not True:
        raise ValueError("G2A_COMPACT_PROVENANCE_PROOF_INVALID")
    material = dict(record)
    supplied = material.pop("durable_record_sha256", None)
    if supplied != sha256_canonical_json(material):
        raise ValueError("G2A_DURABLE_RECORD_SHA256_INVALID")
    return canonical_json_bytes(record) + b"\n"


def benchmark_g2a_acquisitions(acquisitions: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {row[0] for row in G2A_BASELINE_CAPABILITIES}
    actual = {row["semantic_request"]["series_id"] for row in acquisitions}
    if len(acquisitions) != 6 or actual != expected:
        raise RuntimeError("ACTUAL_SUCCESSOR_BYTE_BENCHMARK_FAILED:BASELINE_SET")
    records = []
    measurements = []
    for acquisition in acquisitions:
        record = build_durable_l2_observation(acquisition)
        serialized = serialize_durable_l2_observation(record)
        if not serialized or not serialized.endswith(b"\n"):
            raise RuntimeError("ACTUAL_SUCCESSOR_BYTE_BENCHMARK_FAILED:SERIALIZER")
        records.append(record)
        measurements.append(
            {
                "series_id": acquisition["semantic_request"]["series_id"],
                "provider_id": record["provider_id"],
                "instrument_id": record["instrument_id"],
                "serialized_bytes": len(serialized),
                "truncated": record["coverage"]["truncated"],
                "achieved_bid_coverage_bps": record["coverage"]["achieved_bid_coverage_bps"],
                "achieved_ask_coverage_bps": record["coverage"]["achieved_ask_coverage_bps"],
            }
        )
    generation_bytes = sum(row["serialized_bytes"] for row in measurements)
    projections = {
        "hourly_30d_bytes": generation_bytes * 24 * 30,
        "hourly_1y_bytes": generation_bytes * 24 * 365,
        "representative_5m_30d_bytes": generation_bytes * 12 * 24 * 30,
        "representative_5m_1y_bytes": generation_bytes * 12 * 24 * 365,
    }
    return {
        "schema_version": G2A_BENCHMARK_SCHEMA,
        "status": "PASS",
        "capability_count": 6,
        "history_target_bps": G2A_HISTORY_TARGET_BPS,
        "serializer": "src/sampled_history.py::serialize_durable_l2_observation",
        "measurements": measurements,
        "six_capability_generation_bytes": generation_bytes,
        "projections": projections,
        "records": records,
    }


def durable_partition_path(observation_time_ms: int, *, root: Path = Path(".")) -> Path:
    return root / "history" / "liquidity-orderbook-snapshots" / day(observation_time_ms) / "observations.json"


def persist_durable_l2_observation(record: Mapping[str, Any], *, root: Path = Path(".")) -> dict[str, Any]:
    serialize_durable_l2_observation(record)
    path = durable_partition_path(int(record["observation_time_ms"]), root=root)
    identity = str(record["durable_identity_sha256"])
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        for current in existing.get("observations", []):
            if current.get("durable_identity_sha256") != identity:
                continue
            if current.get("observation_sha256") == record.get("observation_sha256"):
                return {"status": "DEDUPLICATED", "changed": False, "path": path.as_posix()}
            raise ImmutableHistoryConflict("IMMUTABLE_OBSERVATION_CONFLICT")
    metadata = {
        "schema_version": G2A_PARTITION_SCHEMA,
        "date_utc": date_text(int(record["observation_time_ms"])),
        "history_family": "liquidity.orderbook-snapshots",
    }
    append_partition(
        path,
        metadata,
        [dict(record)],
        records_field="observations",
        key=lambda row: row["durable_identity_sha256"],
    )
    return {"status": "APPENDED", "changed": True, "path": path.as_posix()}


def _artifact_member(root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_MISSING")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_UNSAFE")
    path = root / relative
    if not path.is_file():
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_MISSING")
    return path


def _json_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(code) from exc
    if not isinstance(value, dict):
        raise ValueError(code)
    return value


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_INVALID")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_INVALID") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"G2A_FRESH_CURRENT_{field}_INVALID")
    return parsed.astimezone(timezone.utc)


def _fresh_current_network_records(output_root: Path) -> list[dict[str, Any]]:
    index = _json_object(output_root / "resource-index.json", "G2A_FRESH_CURRENT_RESOURCE_INDEX_INVALID")
    rows = index.get("liquidity_resources")
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("G2A_FRESH_CURRENT_RESOURCE_INDEX_INVALID")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("G2A_FRESH_CURRENT_RESOURCE_ROW_INVALID")
        mode = row.get("acquisition_mode")
        if mode in {"SAME_EXECUTION_REUSE", "LEGACY_PERSISTED_REQUALIFICATION"}:
            continue
        if mode != "S3_NETWORK_ACQUIRED":
            raise ValueError("G2A_FRESH_CURRENT_ACQUISITION_MODE_INVALID")
        resource = _json_object(
            _artifact_member(output_root, row.get("resource_artifact_member"), "RESOURCE_ARTIFACT_MEMBER"),
            "G2A_FRESH_CURRENT_RESOURCE_INVALID",
        )
        qualified = validate_qualified_liquidity_resource(resource)
        qualification = _json_object(
            _artifact_member(output_root, row.get("qualification_receipt_member"), "QUALIFICATION_RECEIPT_MEMBER"),
            "G2A_FRESH_CURRENT_QUALIFICATION_RECEIPT_INVALID",
        )
        execution = _json_object(
            _artifact_member(output_root, row.get("s3_execution_receipt_member"), "S3_EXECUTION_RECEIPT_MEMBER"),
            "G2A_FRESH_CURRENT_EXECUTION_RECEIPT_INVALID",
        )
        qualification_material = dict(qualification)
        qualification_sha = qualification_material.pop("qualification_receipt_sha256", None)
        if (
            qualification_sha != row.get("qualification_receipt_sha256")
            or qualification_sha != sha256_canonical_json(qualification_material)
        ):
            raise ValueError("G2A_FRESH_CURRENT_QUALIFICATION_RECEIPT_BINDING_INVALID")
        if execution.get("execution_receipt_sha256") != row.get("s3_execution_receipt_sha256"):
            raise ValueError("G2A_FRESH_CURRENT_EXECUTION_RECEIPT_BINDING_INVALID")
        if (
            qualified.get("observation_id") != row.get("observation_id")
            or qualified.get("observation_sha256") != row.get("observation_sha256")
            or qualification.get("observation_id") != row.get("observation_id")
            or qualification.get("observation_sha256") != row.get("observation_sha256")
        ):
            raise ValueError("G2A_FRESH_CURRENT_OBSERVATION_BINDING_INVALID")
        s1_plan = qualification.get("s1_planner_result")
        s2_plan = qualification.get("s2_provider_plan")
        if not isinstance(s1_plan, Mapping) or not isinstance(s2_plan, Mapping):
            raise ValueError("G2A_FRESH_CURRENT_ACQUISITION_PROVENANCE_MISSING")
        record = build_durable_l2_observation(
            {
                "qualified_resource": qualified,
                "s2_provider_plan": s2_plan,
                "execution_receipt": execution,
            }
        )
        if record["history_family"] != "liquidity.orderbook-snapshots":
            raise ValueError("G2A_FRESH_CURRENT_HISTORY_FAMILY_CHANGED")
        if record["observation_id"] != row.get("observation_id") or record["observation_sha256"] != row.get("observation_sha256"):
            raise ValueError("G2A_FRESH_CURRENT_OBSERVATION_BINDING_INVALID")
        if _utc(record["observation_time_utc"], "OBSERVATION_TIME") > _utc(record["known_at_utc"], "KNOWN_AT"):
            raise ValueError("G2A_OBSERVATION_TIME_AFTER_KNOWN_AT")
        identity = str(record["durable_identity_sha256"])
        if identity in seen:
            continue
        seen.add(identity)
        records.append(record)
    records.sort(key=lambda record: (int(record["observation_time_ms"]), str(record["durable_identity_sha256"])))
    return records


def build_fresh_current_durable_observation_artifact(output_root: Path) -> dict[str, Any]:
    records = _fresh_current_network_records(output_root)
    rows: list[dict[str, Any]] = []
    for record in records:
        serialized = serialize_durable_l2_observation(record)
        digest = hashlib.sha256(serialized).hexdigest()
        member = Path("g2a-durable-observations") / f"{record['durable_identity_sha256']}.json"
        path = output_root / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(serialized)
        rows.append(
            {
                "acquisition_mode": "S3_NETWORK_ACQUIRED",
                "history_family": "liquidity.orderbook-snapshots",
                "provider_id": record["provider_id"],
                "instrument_id": record["instrument_id"],
                "book_kind": record["book_kind"],
                "observation_id": record["observation_id"],
                "observation_sha256": record["observation_sha256"],
                "durable_identity_sha256": record["durable_identity_sha256"],
                "observation_time_utc": record["observation_time_utc"],
                "known_at_utc": record["known_at_utc"],
                "request_satisfaction_separate": True,
                "exact_request_resource_durability": "EPHEMERAL_ONLY",
                "payload_member": member.as_posix(),
                "payload_sha256": digest,
                "payload_size_bytes": len(serialized),
            }
        )
    transfer = {
        "schema_version": G2A_FRESH_CURRENT_TRANSFER_SCHEMA,
        "authority": "TEMPORARY_TRANSFER_EVIDENCE",
        "history_family": "liquidity.orderbook-snapshots",
        "exact_request_resource_durability": "EPHEMERAL_ONLY",
        "underlying_network_observation_durability": "ELIGIBLE_FOR_CANONICAL_HISTORY",
        "same_execution_reuse_creates_history": False,
        "persisted_reuse_creates_history": False,
        "request_satisfaction_separate": True,
        "second_dedupe_ledger": False,
        "observation_count": len(rows),
        "observations": rows,
    }
    atomic_json(output_root / G2A_FRESH_CURRENT_TRANSFER_PATH, transfer)
    return transfer


def apply_fresh_current_durable_observation_artifact(
    artifact_root: Path,
    *,
    root: Path = Path("."),
) -> dict[str, Any]:
    expected_records = _fresh_current_network_records(artifact_root)
    transfer_path = artifact_root / G2A_FRESH_CURRENT_TRANSFER_PATH
    if not transfer_path.is_file():
        if expected_records:
            raise ValueError("G2A_FRESH_CURRENT_TRANSFER_MISSING")
        return {"status": "NOT_APPLICABLE", "appended": 0, "deduplicated": 0, "paths": []}
    transfer = _json_object(transfer_path, "G2A_FRESH_CURRENT_TRANSFER_INVALID")
    if (
        transfer.get("schema_version") != G2A_FRESH_CURRENT_TRANSFER_SCHEMA
        or transfer.get("authority") != "TEMPORARY_TRANSFER_EVIDENCE"
        or transfer.get("history_family") != "liquidity.orderbook-snapshots"
        or transfer.get("exact_request_resource_durability") != "EPHEMERAL_ONLY"
        or transfer.get("same_execution_reuse_creates_history") is not False
        or transfer.get("persisted_reuse_creates_history") is not False
        or transfer.get("second_dedupe_ledger") is not False
    ):
        raise ValueError("G2A_FRESH_CURRENT_TRANSFER_INVALID")
    rows = transfer.get("observations")
    if not isinstance(rows, list) or transfer.get("observation_count") != len(rows) or len(rows) != len(expected_records):
        raise ValueError("G2A_FRESH_CURRENT_TRANSFER_COUNT_MISMATCH")
    by_identity = {str(record["durable_identity_sha256"]): record for record in expected_records}
    if len(by_identity) != len(expected_records):
        raise ValueError("G2A_FRESH_CURRENT_TRANSFER_DUPLICATE_IDENTITY")
    appended = 0
    deduplicated = 0
    paths: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("acquisition_mode") != "S3_NETWORK_ACQUIRED":
            raise ValueError("G2A_FRESH_CURRENT_TRANSFER_ROW_INVALID")
        identity = str(row.get("durable_identity_sha256") or "")
        record = by_identity.pop(identity, None)
        if record is None:
            raise ValueError("G2A_FRESH_CURRENT_TRANSFER_IDENTITY_MISMATCH")
        if (
            row.get("history_family") != record["history_family"]
            or row.get("provider_id") != record["provider_id"]
            or row.get("instrument_id") != record["instrument_id"]
            or row.get("book_kind") != record["book_kind"]
            or row.get("observation_id") != record["observation_id"]
            or row.get("observation_sha256") != record["observation_sha256"]
            or row.get("observation_time_utc") != record["observation_time_utc"]
            or row.get("known_at_utc") != record["known_at_utc"]
            or row.get("request_satisfaction_separate") is not True
            or row.get("exact_request_resource_durability") != "EPHEMERAL_ONLY"
        ):
            raise ValueError("G2A_FRESH_CURRENT_TRANSFER_BINDING_INVALID")
        payload = _artifact_member(artifact_root, row.get("payload_member"), "PAYLOAD_MEMBER")
        raw = payload.read_bytes()
        expected = serialize_durable_l2_observation(record)
        if raw != expected or hashlib.sha256(raw).hexdigest() != row.get("payload_sha256") or len(raw) != row.get("payload_size_bytes"):
            raise ValueError("G2A_FRESH_CURRENT_TRANSFER_PAYLOAD_INVALID")
        try:
            result = persist_durable_l2_observation(record, root=root)
        except ImmutableHistoryConflict as exc:
            raise ImmutableHistoryConflict("IMMUTABLE_OBSERVATION_CONFLICT") from exc
        if result["status"] == "APPENDED":
            appended += 1
        elif result["status"] == "DEDUPLICATED":
            deduplicated += 1
        else:
            raise ValueError("G2A_FRESH_CURRENT_PERSISTENCE_STATUS_INVALID")
        paths.append(str(result["path"]))
    if by_identity:
        raise ValueError("G2A_FRESH_CURRENT_TRANSFER_RECORD_MISSING")
    return {
        "status": "PASS",
        "appended": appended,
        "deduplicated": deduplicated,
        "paths": sorted(paths),
    }


def persist_g2a_baseline(
    *,
    root: Path = Path("."),
    transport: Any | None = None,
    benchmark_output: Path | None = None,
) -> dict[str, Any]:
    acquisitions = acquire_g2a_baseline(transport=transport)
    benchmark = benchmark_g2a_acquisitions(acquisitions)
    if benchmark["status"] != "PASS" or benchmark["capability_count"] != 6:
        raise RuntimeError("ACTUAL_SUCCESSOR_BYTE_BENCHMARK_FAILED")
    public_benchmark = {key: value for key, value in benchmark.items() if key != "records"}
    if benchmark_output is not None:
        atomic_json(benchmark_output, public_benchmark)
    persistence = [persist_durable_l2_observation(record, root=root) for record in benchmark["records"]]
    return {
        "status": "PASS",
        "acquisition_route": "S1_TO_S2_TO_S3",
        "capability_count": 6,
        "benchmark": public_benchmark,
        "persistence": persistence,
        "records": benchmark["records"],
    }


def run_row(
    *,
    run_id: str,
    expected_ms: int,
    started_ms: int,
    completed_ms: int,
    provider: str,
    series_or_capability: str,
    status: str,
    snapshot_ref: str | None,
    error_class: str | None,
    provider_timestamp_ms: int | None,
    target_cadence_seconds: int,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "expected_schedule_at": iso(expected_ms),
        "collection_started_at": iso(started_ms),
        "collection_completed_at": iso(completed_ms),
        "provider": provider,
        "series_or_capability": series_or_capability,
        "status": status,
        "snapshot_ref": snapshot_ref,
        "error_class": error_class,
        "provider_timestamp_at": iso(provider_timestamp_ms) if provider_timestamp_ms is not None else None,
        "known_at": iso(completed_ms),
        "retrieved_at": iso(completed_ms),
        "freshness": freshness(provider_timestamp_ms, completed_ms, target_cadence_seconds)
        if status == "OBSERVED_STATE"
        else {"status": "COLLECTION_GAP" if status == "COLLECTION_GAP" else "UNKNOWN", "age_seconds": None, "target_cadence_seconds": target_cadence_seconds},
    }


def persist_sampled_intelligence(
    intelligence: dict[str, Any],
    *,
    expected_ms: int,
    started_ms: int,
    completed_ms: int,
    target_cadence_seconds: int = 3600,
    enable_g2a: bool | None = None,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []

    derivatives = intelligence.get("derivatives", {})
    deribit = derivatives.get("providers", {}).get("deribit-perpetual", {})
    instruments = deribit.get("instruments") if isinstance(deribit, dict) else None
    if deribit.get("status") == "PASS" and isinstance(instruments, dict) and instruments:
        snapshot_path = Path("derivatives/snapshots") / day(expected_ms) / f"{expected_ms}.json"
        provider_timestamps = [int(row["timestamp_ms"]) for row in instruments.values() if row.get("timestamp_ms") is not None]
        provider_timestamp = max(provider_timestamps) if provider_timestamps else None
        atomic_json(
            snapshot_path,
            {
                "schema_version": SAMPLED_SCHEMA,
                "provider": "deribit-perpetual",
                "timestamp_ms": expected_ms,
                "collection_started_at": iso(started_ms),
                "collection_completed_at": iso(completed_ms),
                "instruments": instruments,
            },
        )
        runs.append(
            run_row(
                run_id=f"deribit-perpetual-current:{expected_ms}",
                expected_ms=expected_ms,
                started_ms=started_ms,
                completed_ms=completed_ms,
                provider="deribit-perpetual",
                series_or_capability="derivatives.deribit-perpetual.current-snapshot",
                status="OBSERVED_STATE",
                snapshot_ref=snapshot_path.as_posix(),
                error_class=None,
                provider_timestamp_ms=provider_timestamp,
                target_cadence_seconds=target_cadence_seconds,
            )
        )
    else:
        runs.append(
            run_row(
                run_id=f"deribit-perpetual-current:{expected_ms}",
                expected_ms=expected_ms,
                started_ms=started_ms,
                completed_ms=completed_ms,
                provider="deribit-perpetual",
                series_or_capability="derivatives.deribit-perpetual.current-snapshot",
                status="PROVIDER_FAILURE",
                snapshot_ref=None,
                error_class="DERIBIT_PERPETUAL_COLLECTION_FAILED",
                provider_timestamp_ms=None,
                target_cadence_seconds=target_cadence_seconds,
            )
        )

    options = intelligence.get("options", {}).get("providers", {}).get("deribit", {})
    option_path = options.get("latest_surface") if isinstance(options, dict) else None
    option_ok = options.get("status") == "PASS" and isinstance(option_path, str) and Path(option_path).is_file()
    runs.append(
        run_row(
            run_id=f"deribit-options-surface:{expected_ms}",
            expected_ms=expected_ms,
            started_ms=started_ms,
            completed_ms=completed_ms,
            provider="deribit-options",
            series_or_capability="options.deribit-options.ETH.surface-snapshots",
            status="OBSERVED_STATE" if option_ok else "PROVIDER_FAILURE",
            snapshot_ref=option_path if option_ok else None,
            error_class=None if option_ok else "DERIBIT_OPTION_SURFACE_COLLECTION_FAILED",
            provider_timestamp_ms=expected_ms if option_ok else None,
            target_cadence_seconds=target_cadence_seconds,
        )
    )

    if enable_g2a is None:
        enable_g2a = os.environ.get("G2A_HOURLY_WRITER_ACTIVE") == "1"
    g2a = None
    if enable_g2a:
        benchmark_output_value = os.environ.get("G2A_BENCHMARK_OUTPUT")
        benchmark_output = Path(benchmark_output_value) if benchmark_output_value else None
        g2a = persist_g2a_baseline(benchmark_output=benchmark_output)
        for record, result in zip(g2a["records"], g2a["persistence"]):
            runs.append(
                run_row(
                    run_id="liquidity-g2a:" + str(record["durable_identity_sha256"]),
                    expected_ms=expected_ms,
                    started_ms=started_ms,
                    completed_ms=completed_ms,
                    provider=str(record["provider_id"]),
                    series_or_capability=str(record["provenance"]["capability_series_id"]),
                    status="OBSERVED_STATE",
                    snapshot_ref=str(result["path"]),
                    error_class=None,
                    provider_timestamp_ms=int(record["observation_time_ms"]),
                    target_cadence_seconds=target_cadence_seconds,
                )
            )

    liquidity = intelligence.get("liquidity", {}).get("collection", {})
    liquidity_path = liquidity.get("latest_path") if isinstance(liquidity, dict) else None
    liquidity_ok = liquidity.get("status") in {"PASS", "DEGRADED"} and isinstance(liquidity_path, str) and Path(liquidity_path).is_file()
    runs.append(
        run_row(
            run_id=f"liquidity-orderbook-legacy-context:{expected_ms}",
            expected_ms=expected_ms,
            started_ms=started_ms,
            completed_ms=completed_ms,
            provider="multi-provider-legacy-context",
            series_or_capability="liquidity.orderbook-snapshots.legacy-context",
            status="OBSERVED_STATE" if liquidity_ok else "PROVIDER_FAILURE",
            snapshot_ref=liquidity_path if liquidity_ok else None,
            error_class=None if liquidity_ok else "LEGACY_LIQUIDITY_CONTEXT_COLLECTION_FAILED",
            provider_timestamp_ms=expected_ms if liquidity_ok else None,
            target_cadence_seconds=target_cadence_seconds,
        )
    )

    ledger_path = Path("history/collection-runs") / day(expected_ms) / "runs.json"
    metadata = {"schema_version": LEDGER_SCHEMA, "date_utc": date_text(expected_ms)}
    append_partition(ledger_path, metadata, runs, records_field="runs", key=lambda row: row["run_id"])
    return {
        "ledger_path": ledger_path.as_posix(),
        "run_count": len(runs),
        "runs": runs,
        "g2a": g2a,
    }


def _append_github_output(path: Path | None, name: str, value: object) -> None:
    if path is None:
        return
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValueError("G2A_UNSAFE_GITHUB_OUTPUT")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={text}\n")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="G2-A durable L2 writer and Fresh Current transfer")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-current-transfer")
    build.add_argument("--resource-index", required=True)
    build.add_argument("--output-root", required=True)
    build.add_argument("--github-output")

    apply = sub.add_parser("apply-current-transfer")
    apply.add_argument("--artifact-root", required=True)
    apply.add_argument("--repository-root", required=True)

    args = parser.parse_args(argv)
    if args.command == "build-current-transfer":
        output_root = Path(args.output_root)
        resource_index = Path(args.resource_index)
        if resource_index.resolve() != (output_root / "resource-index.json").resolve():
            raise ValueError("G2A_FRESH_CURRENT_RESOURCE_INDEX_PATH_MISMATCH")
        transfer = build_fresh_current_durable_observation_artifact(output_root)
        github_output = Path(args.github_output) if args.github_output else None
        _append_github_output(github_output, "observation_count", transfer["observation_count"])
        _append_github_output(github_output, "transfer_schema", transfer["schema_version"])
        print(f"G2A_FRESH_CURRENT_TRANSFER_BUILD=PASS observations={transfer['observation_count']}")
        return 0
    result = apply_fresh_current_durable_observation_artifact(
        Path(args.artifact_root), root=Path(args.repository_root)
    )
    print(
        "G2A_FRESH_CURRENT_TRANSFER_APPLY=PASS "
        f"status={result['status']} appended={result['appended']} deduplicated={result['deduplicated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
