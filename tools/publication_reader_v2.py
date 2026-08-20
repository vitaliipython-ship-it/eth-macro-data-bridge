from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import history_access_v2 as base_v2
from canonical_json import canonical_json_bytes

DATA_SCHEMA = "market-data-d8-origin-github-warm/1.0.0"
BACKEND_PROFILE = "GITHUB_FIRST_V1"
REPRESENTATION = "EXACT_D8_ENVELOPE"


class PublicationReaderError(base_v2.HistoryAccessV2Error):
    """Fail-closed D8 publication adapter error inside the existing v2 reader family."""


def _is_d8_segment(segment: dict[str, Any]) -> bool:
    descriptor = segment.get("physical_descriptor")
    return (
        segment.get("residence_role") == "WARM"
        and segment.get("adapter_profile") == BACKEND_PROFILE
        and isinstance(descriptor, dict)
        and descriptor.get("representation") == REPRESENTATION
    )


def _effective_timestamp_ms(envelope: dict[str, Any]) -> int:
    if envelope.get("d9_forward_seam", {}).get("target") == "FIXED_GRID":
        value = envelope.get("value")
        if isinstance(value, dict) and isinstance(value.get("open_time_ms"), int):
            return int(value["open_time_ms"])
        source = envelope.get("provider_timestamp_at") or envelope.get("canonical_slot")
    else:
        source = envelope.get("canonical_slot") or envelope.get("known_at")
    if not isinstance(source, str):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 envelope effective timestamp missing")
    return base_v2._parse_utc_ms(source)


def _load_resource(segment: dict[str, Any], root: Path) -> dict[str, Any]:
    path = segment.get("resource_path") or segment.get("physical_descriptor", {}).get("resource_path")
    if not isinstance(path, str):
        raise PublicationReaderError("ARCHIVE_INVALID", "D8 publication resource path missing")
    raw = base_v2._verified_repo_descriptor(
        root,
        {"resource_path": path, "sha256": segment.get("sha256"), "size_bytes": segment.get("size_bytes")},
        "ARCHIVE_INVALID",
    )
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationReaderError("ARCHIVE_INVALID", "D8 publication resource is invalid JSON") from exc
    integrity = segment.get("integrity_evidence")
    if not isinstance(integrity, dict):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 publication integrity evidence missing")
    batch_id = integrity.get("batch_id")
    if (
        payload.get("schema_version") != DATA_SCHEMA
        or payload.get("representation") != REPRESENTATION
        or payload.get("batch_id") != batch_id
        or payload.get("target_residence_role") != "WARM"
        or payload.get("membership_sha256") != integrity.get("membership_sha256")
        or payload.get("payload_sha256") != integrity.get("payload_sha256")
    ):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 publication resource/batch integrity mismatch")
    observations = payload.get("observations")
    member_ids = payload.get("member_observation_ids")
    if not isinstance(observations, list) or not isinstance(member_ids, list):
        raise PublicationReaderError("ARCHIVE_INVALID", "D8 publication observations missing")
    ids = [row.get("observation_id") for row in observations if isinstance(row, dict)]
    if ids != member_ids or len(ids) != len(set(ids)):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 publication resource membership mismatch")
    return payload


def _envelope_for_segment(segment: dict[str, Any], root: Path, expected_series_id: str) -> dict[str, Any]:
    payload = _load_resource(segment, root)
    wanted = segment.get("d8_observation_ids")
    if not isinstance(wanted, list) or len(wanted) != 1 or not isinstance(wanted[0], str):
        raise PublicationReaderError("INVALID_RESOLUTION_PLAN", "D8 segment must bind exactly one observation identity")
    envelope = next((row for row in payload["observations"] if row.get("observation_id") == wanted[0]), None)
    if not isinstance(envelope, dict):
        raise PublicationReaderError("MEMBER_NOT_FOUND", f"D8 observation not found: {wanted[0]}")
    if envelope.get("series_id") != expected_series_id:
        raise PublicationReaderError("MEMBER_NOT_FOUND", "D8 observation series binding mismatch")
    fingerprint = envelope.get("fingerprint")
    if not isinstance(fingerprint, str) or fingerprint != hashlib.sha256(canonical_json_bytes(envelope.get("value"))).hexdigest():
        raise PublicationReaderError("CHECKSUM_MISMATCH", "D8 observation payload fingerprint mismatch")
    if envelope.get("observation_id") != segment.get("integrity_evidence", {}).get("observation_id"):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 observation identity/integrity binding mismatch")
    if _effective_timestamp_ms(envelope) != segment.get("d8_effective_timestamp_ms"):
        raise PublicationReaderError("INVALID_PROVENANCE", "D8 observation effective timestamp binding mismatch")
    return envelope


def _virtual_payload(envelope: dict[str, Any], segment: dict[str, Any], series_kind: str) -> bytes:
    timestamp = _effective_timestamp_ms(envelope)
    value = envelope.get("value")
    if series_kind == "OHLCV":
        if not isinstance(value, dict):
            raise PublicationReaderError("INVALID_OBSERVATION", "D8 OHLCV value must be object")
        required = ("open", "high", "low", "close", "volume")
        if any(name not in value for name in required):
            raise PublicationReaderError("INVALID_OBSERVATION", "D8 OHLCV value incomplete")
        payload = {
            "provider": segment.get("source_provider"),
            "instrument": segment.get("instrument"),
            "interval_or_metric": segment.get("source_interval_or_metric"),
            "columns": ["open_time_ms", "open", "high", "low", "close", "volume"],
            "records": [[timestamp, value["open"], value["high"], value["low"], value["close"], value["volume"]]],
        }
    else:
        payload = {"value": value} if not isinstance(value, dict) else value
    return canonical_json_bytes(payload) + b"\n"


def _copy_descriptor_file(root: Path, virtual_root: Path, descriptor: dict[str, Any]) -> None:
    relative = descriptor.get("resource_path") or descriptor.get("path")
    if not isinstance(relative, str):
        return
    source = base_v2._safe_path(root, relative, "ARCHIVE_INVALID")
    target = virtual_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def _copy_native_dependencies(segment: dict[str, Any], root: Path, virtual_root: Path) -> None:
    relative = segment.get("resource_path") or segment.get("physical_descriptor", {}).get("resource_path")
    if isinstance(relative, str):
        source = base_v2._safe_path(root, relative, "ARCHIVE_INVALID")
        target = virtual_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    collection = segment.get("collection_run")
    if isinstance(collection, dict) and isinstance(collection.get("ledger_resource"), dict):
        _copy_descriptor_file(root, virtual_root, collection["ledger_resource"])
    for revision in segment.get("revision_evidence", []):
        if isinstance(revision, dict):
            _copy_descriptor_file(root, virtual_root, revision)
            source = revision.get("source_snapshot")
            if isinstance(source, dict):
                _copy_descriptor_file(root, virtual_root, source)


def _copy_gap_dependencies(plan: dict[str, Any], root: Path, virtual_root: Path) -> None:
    for gap in plan.get("series", {}).get("collection_gaps", []):
        if isinstance(gap, dict) and isinstance(gap.get("ledger_resource"), dict):
            _copy_descriptor_file(root, virtual_root, gap["ledger_resource"])


def _transform_plan(plan: dict[str, Any], root: Path, virtual_root: Path) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    transformed = copy.deepcopy(plan)
    d8_by_timestamp: dict[int, dict[str, Any]] = {}
    expected_series_id = plan["series"]["series_id"]
    for index, (source_segment, target_segment) in enumerate(zip(plan["segments"], transformed["segments"])):
        if not _is_d8_segment(source_segment):
            _copy_native_dependencies(source_segment, root, virtual_root)
            continue
        envelope = _envelope_for_segment(source_segment, root, expected_series_id)
        timestamp = _effective_timestamp_ms(envelope)
        if timestamp in d8_by_timestamp and d8_by_timestamp[timestamp]["observation_id"] != envelope["observation_id"]:
            raise PublicationReaderError("DUPLICATE_CONFLICT", f"multiple D8 identities at timestamp {timestamp}")
        d8_by_timestamp[timestamp] = envelope
        virtual_path = f"__publication_reader/{index:06d}-{envelope['observation_id']}.json"
        raw = _virtual_payload(envelope, source_segment, plan["series"]["series_kind"])
        target = virtual_root / virtual_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target_segment["resource_path"] = virtual_path
        target_segment["physical_descriptor"] = {"resource_path": virtual_path}
        target_segment["sha256"] = hashlib.sha256(raw).hexdigest()
        target_segment["size_bytes"] = len(raw)
        target_segment["storage"] = "GIT_WARM_RESOURCE"
    _copy_gap_dependencies(plan, root, virtual_root)
    transformed["plan_sha256"] = base_v2._plan_digest(transformed)
    return transformed, d8_by_timestamp


def _attach_d8_semantics(rows: list[dict[str, Any]], d8_by_timestamp: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen: set[int] = set()
    for row in rows:
        item = dict(row)
        envelope = d8_by_timestamp.get(item.get("timestamp_ms"))
        if envelope is not None:
            item["observation_id"] = envelope["observation_id"]
            item["known_at"] = envelope["known_at"]
            item["finality"] = envelope["finality"]
            item["provenance"] = envelope["provenance"]
            item["payload_fingerprint"] = envelope["fingerprint"]
            item["canonical_cycle_id"] = envelope.get("canonical_cycle_id")
            item["capability_id"] = envelope.get("capability_id")
            seen.add(item["timestamp_ms"])
        result.append(item)
    missing = sorted(set(d8_by_timestamp) - seen)
    if missing:
        raise PublicationReaderError("MEMBER_NOT_FOUND", f"D8 published observations were not materialized: {missing[:5]}")
    return result


def materialize_resolution_plan_v2(
    plan: dict[str, Any],
    *,
    root: Path,
    cache_dir: Path | None = None,
    mode: str = "strict",
    opener: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_v2.validate_resolution_plan_v2(plan)
    if not any(_is_d8_segment(segment) for segment in plan["segments"]):
        kwargs = {"root": root, "cache_dir": cache_dir, "mode": mode}
        if opener is not None:
            kwargs["opener"] = opener
        return base_v2.materialize_resolution_plan_v2(plan, **kwargs)

    with tempfile.TemporaryDirectory(prefix="eth-macro-publication-reader-") as temporary:
        virtual_root = Path(temporary)
        transformed, d8_by_timestamp = _transform_plan(plan, root, virtual_root)
        kwargs = {"root": virtual_root, "cache_dir": cache_dir, "mode": mode}
        if opener is not None:
            kwargs["opener"] = opener
        rows, diagnostics = base_v2.materialize_resolution_plan_v2(transformed, **kwargs)
    rows = _attach_d8_semantics(rows, d8_by_timestamp)
    request = plan["request"]
    provisional = any(row.get("finality") == "PROVISIONAL" for row in rows)
    receipt = base_v2.build_semantic_receipt(
        series_id=plan["series"]["series_id"],
        start_ms=request["start_ms"],
        end_ms=request["end_ms"],
        cutoff_ms=request.get("cutoff_ms"),
        mode=mode,
        current_policy=request.get("current_policy", "FINALIZED_ONLY"),
        resolution_plan_sha256=plan["plan_sha256"],
        observations=rows,
        finality="PROVISIONAL_INCLUDED" if provisional else "FINALIZED",
        revision_context=diagnostics.get("receipt", {}).get("revision_context"),
    )
    diagnostics = dict(diagnostics)
    diagnostics["plan_sha256"] = plan["plan_sha256"]
    diagnostics["sources"] = [
        {
            **source,
            "adapter_profile": next(
                (
                    segment.get("adapter_profile")
                    for segment in plan["segments"]
                    if segment.get("segment_id") == source.get("segment_id")
                ),
                None,
            ),
        }
        for source in diagnostics.get("sources", [])
    ]
    diagnostics["receipt"] = receipt
    return rows, diagnostics
