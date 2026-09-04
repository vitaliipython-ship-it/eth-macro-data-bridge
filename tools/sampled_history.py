from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for value in (ROOT, SRC):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from options_derivation import OptionsDerivationError, derive_options_analytics, options_derivation_policy_identity, validate_options_snapshot
from tools import capability_index, history_access

SAMPLED_INDEX_SCHEMA = "market-data-sampled-observation-index/1.0.0"
SAMPLED_PLAN_SCHEMA = "market-data-sampled-resolution-plan/1.0.0"
SAMPLED_RECEIPT_SCHEMA = "market-data-sampled-history-receipt/1.0.0"
OPTIONS_SURFACE_CAPABILITY_ID = "options.deribit-options.ETH.surface-snapshots"
SELECTION_AT_OR_BEFORE = "AT_OR_BEFORE"
OPTIONS_HISTORY_MANIFEST = Path("options/history-manifest.json")
OPTIONS_CURRENT_MANIFEST = Path("options/manifest.json")
FORWARD_FIRST_TIMESTAMP_KEY = "options_forward_snapshot_first_timestamp_ms"
AVAILABILITY_STATES = {"HISTORY_AVAILABLE", "TARGET_PRECEDES_FORWARD_ARCHIVE", "DATA_GAP", "HISTORY_EXECUTION_GAP", "SEMANTIC_VALIDATION_FAILED", "DERIVATION_VERSION_MISMATCH"}


class SampledHistoryError(RuntimeError):
    def __init__(self, code: str, availability_state: str, message: str):
        self.code = code
        self.availability_state = availability_state
        super().__init__(message)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _digest(value: Mapping[str, Any], self_field: str) -> str:
    body = dict(value); body.pop(self_field, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _parse_target_utc(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z") or "\n" in value or "\r" in value:
        raise SampledHistoryError("INVALID_TARGET_UTC", "SEMANTIC_VALIDATION_FAILED", "target_utc must use UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise SampledHistoryError("INVALID_TARGET_UTC", "SEMANTIC_VALIDATION_FAILED", f"invalid target_utc: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise SampledHistoryError("INVALID_TARGET_UTC", "SEMANTIC_VALIDATION_FAILED", "target_utc must be UTC")
    return int(parsed.timestamp() * 1000)


def _format_utc_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _read_control_json(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SampledHistoryError("SAMPLED_CONTROL_RESOURCE_READ_FAILED", "HISTORY_EXECUTION_GAP", relative.as_posix()) from exc
    except json.JSONDecodeError as exc:
        raise SampledHistoryError("SAMPLED_CONTROL_RESOURCE_JSON_INVALID", "SEMANTIC_VALIDATION_FAILED", relative.as_posix()) from exc
    if not isinstance(value, dict):
        raise SampledHistoryError("SAMPLED_CONTROL_RESOURCE_SHAPE_INVALID", "SEMANTIC_VALIDATION_FAILED", relative.as_posix())
    return value


def discover_forward_capability(capability_id: str) -> dict[str, Any]:
    try:
        index = capability_index._committed_index()
    except Exception as exc:
        raise SampledHistoryError("CAPABILITY_INDEX_UNAVAILABLE", "HISTORY_EXECUTION_GAP", str(exc)) from exc
    matches = [row for row in index.get("forward_capabilities", []) if isinstance(row, Mapping) and row.get("capability_id") == capability_id]
    if len(matches) != 1:
        raise SampledHistoryError("UNKNOWN_SAMPLED_CAPABILITY", "SEMANTIC_VALIDATION_FAILED", f"unknown sampled capability: {capability_id}")
    row = dict(matches[0])
    if row.get("history_mode") != "FORWARD_ONLY":
        raise SampledHistoryError("SAMPLED_CAPABILITY_MODE_INVALID", "SEMANTIC_VALIDATION_FAILED", f"capability is not FORWARD_ONLY: {capability_id}")
    if row.get("availability_status") != "PASS":
        raise SampledHistoryError("SAMPLED_CAPABILITY_UNAVAILABLE", "DATA_GAP", f"forward archive is not available: {capability_id}")
    return row


def _archive_bounds(root: Path, capability_id: str) -> tuple[int, int, str]:
    if capability_id != OPTIONS_SURFACE_CAPABILITY_ID:
        raise SampledHistoryError("UNSUPPORTED_SAMPLED_CAPABILITY", "SEMANTIC_VALIDATION_FAILED", capability_id)
    history_manifest = _read_control_json(root, OPTIONS_HISTORY_MANIFEST)
    first_ms = history_manifest.get(FORWARD_FIRST_TIMESTAMP_KEY)
    if not isinstance(first_ms, int) or isinstance(first_ms, bool) or first_ms <= 0:
        raise SampledHistoryError("SAMPLED_ARCHIVE_FIRST_BOUNDARY_MISSING", "SEMANTIC_VALIDATION_FAILED", OPTIONS_HISTORY_MANIFEST.as_posix())
    current_manifest = _read_control_json(root, OPTIONS_CURRENT_MANIFEST)
    latest_surface = (((current_manifest.get("providers") or {}).get("deribit") or {}).get("latest_surface"))
    if not isinstance(latest_surface, str) or not latest_surface.startswith("options/snapshots/") or not latest_surface.endswith(".json"):
        raise SampledHistoryError("SAMPLED_ARCHIVE_LATEST_BOUNDARY_MISSING", "SEMANTIC_VALIDATION_FAILED", OPTIONS_CURRENT_MANIFEST.as_posix())
    try:
        latest_ms = int(Path(latest_surface).stem)
    except ValueError as exc:
        raise SampledHistoryError("SAMPLED_ARCHIVE_LATEST_BOUNDARY_INVALID", "SEMANTIC_VALIDATION_FAILED", latest_surface) from exc
    if latest_ms < first_ms:
        raise SampledHistoryError("SAMPLED_ARCHIVE_BOUNDARY_ORDER_INVALID", "SEMANTIC_VALIDATION_FAILED", latest_surface)
    return first_ms, latest_ms, latest_surface


def _day_relative(ms: int) -> Path:
    return Path("options/snapshots") / datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y/%m/%d")


def _candidate_days(target_ms: int, first_ms: int):
    current = datetime.fromtimestamp(target_ms / 1000, timezone.utc).date()
    first = datetime.fromtimestamp(first_ms / 1000, timezone.utc).date()
    while current >= first:
        yield Path("options/snapshots") / current.strftime("%Y/%m/%d")
        current -= timedelta(days=1)


def _bounded_selected_observation(root: Path, capability_id: str, target_ms: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    first_ms, latest_ms, latest_surface = _archive_bounds(root, capability_id)
    bounds = {"archive_first_timestamp_ms": first_ms, "archive_last_timestamp_ms": latest_ms, "latest_surface": latest_surface}
    if target_ms < first_ms:
        return None, bounds
    effective_target = min(target_ms, latest_ms)
    selected_path: Path | None = None
    selected_ms: int | None = None
    scanned_days = 0
    for relative_day in _candidate_days(effective_target, first_ms):
        scanned_days += 1
        directory = root / relative_day
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise SampledHistoryError("SAMPLED_DAY_RESOURCE_INVALID", "HISTORY_EXECUTION_GAP", relative_day.as_posix())
        try:
            candidates = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix == ".json")
        except OSError as exc:
            raise SampledHistoryError("SAMPLED_DAY_ENUMERATION_FAILED", "HISTORY_EXECUTION_GAP", relative_day.as_posix()) from exc
        eligible: list[tuple[int, Path]] = []
        for path in candidates:
            try:
                timestamp_ms = int(path.stem)
            except ValueError as exc:
                raise SampledHistoryError("SAMPLED_RESOURCE_NAME_INVALID", "SEMANTIC_VALIDATION_FAILED", path.as_posix()) from exc
            if first_ms <= timestamp_ms <= effective_target:
                eligible.append((timestamp_ms, path))
        if eligible:
            selected_ms, selected_path = max(eligible, key=lambda item: item[0])
            break
    bounds["candidate_day_count"] = scanned_days
    bounds["candidate_derivation"] = "TARGET_DAY_BACKWARD_TO_CANONICAL_FIRST_BOUNDARY_STOP_ON_FIRST_ELIGIBLE_DAY"
    if selected_path is None or selected_ms is None:
        return None, bounds
    try:
        raw = selected_path.read_bytes()
    except OSError as exc:
        raise SampledHistoryError("SAMPLED_RESOURCE_READ_FAILED", "HISTORY_EXECUTION_GAP", selected_path.as_posix()) from exc
    relative = selected_path.relative_to(root).as_posix()
    digest = hashlib.sha256(raw).hexdigest()
    observation = {
        "capability_id": capability_id,
        "observation_timestamp_ms": selected_ms,
        "observation_timestamp_utc": _format_utc_ms(selected_ms),
        "resource_identity": f"sha256:{digest}",
        "integrity_identity": {"sha256": digest, "size_bytes": len(raw)},
        "resource_descriptor": {"storage": "GIT_WARM_RESOURCE", "resource_path": relative, "sha256": digest, "size_bytes": len(raw)},
    }
    return observation, bounds


def build_observation_index(capability_id: str, target_utc: str | None = None, *, repo_root: Path | None = None) -> dict[str, Any]:
    capability = discover_forward_capability(capability_id)
    root = Path(repo_root or capability_index.ROOT)
    first_ms, latest_ms, _latest_surface = _archive_bounds(root, capability_id)
    target_ms = latest_ms if target_utc is None else _parse_target_utc(target_utc)
    selected, bounds = _bounded_selected_observation(root, capability_id, target_ms)
    observations = [selected] if selected is not None else []
    index: dict[str, Any] = {
        "schema_version": SAMPLED_INDEX_SCHEMA,
        "index_role": "BOUNDED_DETERMINISTIC_DERIVED_PROJECTION_NOT_AUTHORITY",
        "derived_index_is_second_ssot": False,
        "capability": capability,
        "canonical_authority": {"capability_index": "history/capability-index.json", "capability_manifest_path": capability.get("manifest_path"), "history_boundary_manifest": OPTIONS_HISTORY_MANIFEST.as_posix(), "durable_resource_family": "options/snapshots"},
        "request_target_ms": target_ms,
        "archive_first_timestamp_ms": first_ms,
        "archive_last_timestamp_ms": latest_ms,
        "candidate_derivation": bounds["candidate_derivation"],
        "candidate_day_count": bounds["candidate_day_count"],
        "observation_count": len(observations),
        "first_observation_timestamp_ms": selected["observation_timestamp_ms"] if selected else None,
        "last_observation_timestamp_ms": selected["observation_timestamp_ms"] if selected else None,
        "observations": observations,
    }
    index["index_sha256"] = _digest(index, "index_sha256")
    return index


def resolve_sampled_history(capability_id: str, target_utc: str, *, selection_policy: str = SELECTION_AT_OR_BEFORE, repo_root: Path | None = None) -> dict[str, Any]:
    if selection_policy != SELECTION_AT_OR_BEFORE:
        raise SampledHistoryError("UNSUPPORTED_SELECTION_POLICY", "SEMANTIC_VALIDATION_FAILED", selection_policy)
    target_ms = _parse_target_utc(target_utc)
    index = build_observation_index(capability_id, target_utc, repo_root=repo_root)
    first_ms = index["archive_first_timestamp_ms"]
    if target_ms < first_ms:
        state = "TARGET_PRECEDES_FORWARD_ARCHIVE"; selected = None
    elif index["observations"]:
        state = "HISTORY_AVAILABLE"; selected = index["observations"][0]
    else:
        state = "DATA_GAP"; selected = None
    selection: dict[str, Any] = {"availability_state": state, "selected_observation_timestamp_ms": None, "selected_observation_timestamp_utc": None, "distance_to_target_ms": None, "resource_identity": None, "integrity_identity": None, "resource_descriptor": None}
    if selected is not None:
        selected_ms = int(selected["observation_timestamp_ms"])
        if selected_ms > target_ms:
            raise SampledHistoryError("AT_OR_BEFORE_INVARIANT_BROKEN", "SEMANTIC_VALIDATION_FAILED", capability_id)
        selection.update({"selected_observation_timestamp_ms": selected_ms, "selected_observation_timestamp_utc": selected["observation_timestamp_utc"], "distance_to_target_ms": target_ms - selected_ms, "resource_identity": selected["resource_identity"], "integrity_identity": selected["integrity_identity"], "resource_descriptor": selected["resource_descriptor"]})
    resolution_material = {"capability_id": capability_id, "target_ms": target_ms, "selection_policy": selection_policy, "availability_state": state, "selected_observation_timestamp_ms": selection["selected_observation_timestamp_ms"], "resource_identity": selection["resource_identity"], "index_sha256": index["index_sha256"]}
    selection["resolution_identity"] = "sha256:" + hashlib.sha256(_canonical_bytes(resolution_material)).hexdigest()
    plan: dict[str, Any] = {
        "schema_version": SAMPLED_PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_SAMPLED_RESOLUTION_PLAN",
        "authority": {"route_policy": "bridge-contract.json", "capability_index": "history/capability-index.json", "observation_inventory": "BOUNDED_DETERMINISTIC_DERIVED_FROM_CANONICAL_DURABLE_OBSERVATIONS", "direct_provider_history_fallback": False, "consumer_supplied_physical_locator": False, "raw_unbounded_directory_scan": False},
        "request": {"capability_id": capability_id, "target_utc": target_utc, "target_ms": target_ms, "selection_policy": selection_policy},
        "inventory": {"schema_version": index["schema_version"], "index_sha256": index["index_sha256"], "observation_count": index["observation_count"], "archive_first_timestamp_ms": index["archive_first_timestamp_ms"], "archive_last_timestamp_ms": index["archive_last_timestamp_ms"], "candidate_derivation": index["candidate_derivation"], "candidate_day_count": index["candidate_day_count"]},
        "selection": selection,
    }
    plan["plan_sha256"] = _digest(plan, "plan_sha256")
    return plan


def validate_sampled_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "sampled plan must be object")
    value = dict(plan)
    required = {"schema_version", "plan_kind", "authority", "request", "inventory", "selection", "plan_sha256"}
    if set(value) != required or value.get("schema_version") != SAMPLED_PLAN_SCHEMA or value.get("plan_kind") != "MARKET_DATA_SAMPLED_RESOLUTION_PLAN":
        raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "sampled plan identity mismatch")
    if value.get("plan_sha256") != _digest(value, "plan_sha256"):
        raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "sampled plan digest mismatch")
    request = value.get("request") or {}; selection = value.get("selection") or {}; authority = value.get("authority") or {}
    if request.get("selection_policy") != SELECTION_AT_OR_BEFORE or authority.get("raw_unbounded_directory_scan") is not False:
        raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "selection/authority policy mismatch")
    state = selection.get("availability_state")
    if state not in AVAILABILITY_STATES:
        raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "availability state invalid")
    selected_ms = selection.get("selected_observation_timestamp_ms"); target_ms = request.get("target_ms")
    if state == "HISTORY_AVAILABLE":
        if not isinstance(selected_ms, int) or not isinstance(target_ms, int) or selected_ms > target_ms:
            raise SampledHistoryError("AT_OR_BEFORE_INVARIANT_BROKEN", "SEMANTIC_VALIDATION_FAILED", "selected observation is after target")
        descriptor = selection.get("resource_descriptor")
        if not isinstance(descriptor, Mapping):
            raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "resource descriptor missing")
        path = descriptor.get("resource_path")
        if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts or not path.startswith("options/snapshots/"):
            raise SampledHistoryError("INVALID_SAMPLED_PLAN", "SEMANTIC_VALIDATION_FAILED", "sampled resource escaped canonical family")
    return value


def materialize_sampled_history(plan: Mapping[str, Any], *, repo_root: Path | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    value = validate_sampled_plan(plan); selection = value["selection"]; state = selection["availability_state"]
    diagnostics = {"schema_version": "market-data-sampled-history-diagnostics/1.0.0", "availability_state": state, "selected_observation_timestamp_ms": selection.get("selected_observation_timestamp_ms"), "selected_observation_timestamp_utc": selection.get("selected_observation_timestamp_utc"), "distance_to_target_ms": selection.get("distance_to_target_ms"), "resource_identity": selection.get("resource_identity"), "resolution_identity": selection.get("resolution_identity"), "direct_provider_history_fallback": False, "raw_unbounded_directory_scan": False}
    if state != "HISTORY_AVAILABLE":
        return None, None, diagnostics
    descriptor = dict(selection["resource_descriptor"]); root = Path(repo_root or capability_index.ROOT)
    try:
        raw = history_access._v1._warm_bytes(descriptor, root)
    except history_access.HistoryAccessError as exc:
        mapped_state = "SEMANTIC_VALIDATION_FAILED" if exc.code == "CHECKSUM_MISMATCH" else "HISTORY_EXECUTION_GAP"
        raise SampledHistoryError(f"SAMPLED_READER_{exc.code}", mapped_state, str(exc)) from exc
    try:
        payload = json.loads(raw); snapshot = validate_options_snapshot(payload); analytics = derive_options_analytics(snapshot)
    except (UnicodeDecodeError, json.JSONDecodeError, OptionsDerivationError) as exc:
        raise SampledHistoryError("CANONICAL_SNAPSHOT_VALIDATION_FAILED", "SEMANTIC_VALIDATION_FAILED", str(exc)) from exc
    selected_ms = selection["selected_observation_timestamp_ms"]
    if snapshot.get("timestamp_ms") != selected_ms or selected_ms > value["request"]["target_ms"]:
        raise SampledHistoryError("SAMPLED_OBSERVATION_BINDING_INVALID", "SEMANTIC_VALIDATION_FAILED", "snapshot/plan timestamp binding invalid")
    diagnostics["snapshot_validation"] = "PASS"; diagnostics["derivation_policy_identity"] = options_derivation_policy_identity()
    return snapshot, analytics, diagnostics


def sampled_semantic_receipt(plan: Mapping[str, Any], analytics: Mapping[str, Any] | None, diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_sampled_plan(plan); selection = value["selection"]
    identity = None
    if analytics is not None:
        identity = {key: analytics[key] for key in ("derivation_policy_id", "derivation_policy_version", "derivation_policy_sha256")}
    receipt: dict[str, Any] = {"receipt_schema_version": SAMPLED_RECEIPT_SCHEMA, "capability_id": value["request"]["capability_id"], "target_utc": value["request"]["target_utc"], "target_ms": value["request"]["target_ms"], "selection_policy": value["request"]["selection_policy"], "availability_state": diagnostics["availability_state"], "selected_observation_timestamp_utc": selection.get("selected_observation_timestamp_utc"), "selected_observation_timestamp_ms": selection.get("selected_observation_timestamp_ms"), "distance_to_target_ms": selection.get("distance_to_target_ms"), "resource_identity": selection.get("resource_identity"), "resolution_identity": selection.get("resolution_identity"), "plan_sha256": value["plan_sha256"], "derivation_policy_identity": identity, "direct_provider_history_fallback": False, "consumer_supplied_physical_locator": False, "raw_unbounded_directory_scan": False}
    receipt["semantic_receipt_sha256"] = _digest(receipt, "semantic_receipt_sha256")
    return receipt


def assert_derivation_policy_match(results: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    identities = []
    for result in results:
        analytics = result.get("analytics") if isinstance(result, Mapping) else None
        if not isinstance(analytics, Mapping):
            raise SampledHistoryError("DERIVATION_VERSION_MISMATCH", "DERIVATION_VERSION_MISMATCH", "missing analytics derivation identity")
        identities.append(tuple(analytics.get(key) for key in ("derivation_policy_id", "derivation_policy_version", "derivation_policy_sha256")))
    if not identities or len(set(identities)) != 1 or any(not isinstance(part, str) or not part for part in identities[0]):
        raise SampledHistoryError("DERIVATION_VERSION_MISMATCH", "DERIVATION_VERSION_MISMATCH", "derivation policies do not match")
    policy_id, version, digest = identities[0]
    return {"derivation_policy_id": policy_id, "derivation_policy_version": version, "derivation_policy_sha256": digest}
