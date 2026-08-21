from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import resolution_v2 as base_v2
from d8_capability_routing import (
    CapabilityRoutingError,
    declarations_from_contract,
    route_capability_series,
)
from history_publication_batch import PublicationBatchError, build_publication_batch

CONTROL_SCHEMA = "market-data-d8-origin-publication-manifest/1.0.0"
DATA_SCHEMA = "market-data-d8-origin-github-warm/1.0.0"
CONTROL_PATH = "history/d8-origin/manifest.json"
BACKEND_PROFILE = "GITHUB_FIRST_V1"
REPRESENTATION = "EXACT_D8_ENVELOPE"
RUNTIME_CONTRACT_PATH = "contracts/d8-runtime-candidate.json"
BRIDGE_CONTRACT_PATH = "bridge-contract.json"
QUALIFICATION_ADMISSION_PATH = "contracts/d8-publication-qualification-admission-v1.json"
QUALIFICATION_ADMISSION_SCHEMA = "d8-publication-qualification-admission/1.0.0"
ELIGIBLE_PUBLICATION_POLICY = "VALIDATED_TERMINAL_CHECKPOINT_V2"
ACTIVE_PROVIDER_AUTHORITY = "ACTIVE_PROVIDER_AUTHORITY"
PREACTIVATION_QUALIFICATION_ONLY = "PREACTIVATION_D8_PUBLICATION_QUALIFICATION"
PREACTIVATION_REQUIRES_QUALIFICATION_MODE = "PREACTIVATION_PROVIDER_REQUIRES_QUALIFICATION_MODE"
REJECT_PROVIDER = "REJECT"
NORMALIZATION_KINDS = {
    "OHLCV": "OHLCV",
    "DERIVATIVES_CURRENT": "SNAPSHOT_SERIES",
    "DERIVATIVES_METRIC": "STRUCTURED_TIME_SERIES",
    "ORDER_BOOK_SNAPSHOT": "ORDER_BOOK_SNAPSHOT",
    "OPTIONS_OR_VOLATILITY": "OPTION_SURFACE",
}


class PublicationControlError(RuntimeError):
    """Fail-closed canonical D8 publication control-plane violation."""


def _plan_digest(plan: dict[str, Any]) -> str:
    body = dict(plan)
    body.pop("plan_sha256", None)
    return hashlib.sha256(base_v2.compact(body)).hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise PublicationControlError(f"D8 publication resource path invalid: {relative}")
    resolved_root = root.resolve()
    resolved = (root / path).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise PublicationControlError(f"D8 publication resource escaped repository root: {relative}")
    return resolved


def _read_contract(root: Path, relative: str, label: str) -> dict[str, Any]:
    target = _safe_path(root, relative)
    if not target.is_file():
        raise PublicationControlError(f"{label} missing: {relative}")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationControlError(f"{label} unreadable: {relative}") from exc
    if not isinstance(value, dict):
        raise PublicationControlError(f"{label} must be an object: {relative}")
    return value


def _d8_declarations(root: Path) -> dict[str, dict[str, Any]]:
    contract = _read_contract(root, RUNTIME_CONTRACT_PATH, "D8 capability declaration contract")
    try:
        return declarations_from_contract(contract)
    except CapabilityRoutingError as exc:
        raise PublicationControlError("D8 capability declaration authority invalid") from exc


def _route_bound_series(root: Path, series: dict[str, Any]) -> dict[str, Any]:
    try:
        return route_capability_series(
            series["capability_id"],
            series["provider"],
            series["series_id"],
            declarations=_d8_declarations(root),
        )
    except (KeyError, CapabilityRoutingError) as exc:
        raise PublicationControlError("D8 publication series is not current declaration authority") from exc


def _qualification_admission_contract(root: Path) -> dict[str, Any]:
    contract = _read_contract(root, QUALIFICATION_ADMISSION_PATH, "D8 qualification admission contract")
    if (
        contract.get("schema_version") != QUALIFICATION_ADMISSION_SCHEMA
        or contract.get("authority_role") != "QUALIFICATION_ADMISSION_ONLY_NOT_PROVIDER_POLICY"
        or contract.get("provider_policy_authority") != "bridge-contract.json#disabled_providers"
        or contract.get("capability_declaration_authority")
        != "contracts/d8-runtime-candidate.json#due_policy.capabilities"
        or contract.get("publication_control_authority") != CONTROL_PATH
        or contract.get("normal_resolution_requires_active_provider_authority") is not True
        or not isinstance(contract.get("admissions"), list)
    ):
        raise PublicationControlError("D8 qualification admission contract identity mismatch")
    provider_ids = [
        row.get("provider_id") for row in contract["admissions"] if isinstance(row, dict)
    ]
    if len(provider_ids) != len(contract["admissions"]) or len(provider_ids) != len(set(provider_ids)):
        raise PublicationControlError("D8 qualification admission provider set invalid")
    return contract


def _preactivation_admission_allowed(
    root: Path,
    series: dict[str, Any],
    routing: dict[str, Any],
) -> bool:
    contract = _qualification_admission_contract(root)
    provider_id = series["provider"]
    matches = [
        row for row in contract["admissions"]
        if isinstance(row, dict) and row.get("provider_id") == provider_id
    ]
    if not matches:
        return False
    if len(matches) != 1:
        raise PublicationControlError(f"duplicate preactivation admission: {provider_id}")
    admission = matches[0]
    required_admission = {
        "status": "ALLOWED",
        "scope": "QUALIFICATION_MODE_ONLY",
        "requires_canonical_d8_publication_control": True,
        "requires_validated_terminal_checkpoint_v2": True,
        "target_residence_role": "WARM",
        "does_not_activate_provider": True,
        "does_not_enable_github_acquisition": True,
        "provider_authority_transition_required_later": True,
        "required_bridge_provider_status": "DISABLED_BY_POLICY",
        "required_bridge_current_collection": "DISABLED_BY_POLICY",
        "required_bridge_runtime_scope": "CURRENT_GITHUB_HOSTED_ACQUISITION_ONLY",
        "required_bridge_target_state": "REQUIRED_FUTURE_ACTIVE_PROVIDER_VIA_QUALIFIED_D8_VPS_RUNTIME",
        "required_bridge_vps_runtime_status": "NOT_ACTIVE",
        "required_bridge_provider_policy_transition": "SEPARATE_VERSIONED_CONTROL_PLANE_TRANSITION_AFTER_D8_QUALIFICATION",
        "required_bridge_network_calls": 0,
    }
    if any(admission.get(key) != value for key, value in required_admission.items()):
        raise PublicationControlError(f"preactivation qualification admission is not fail-closed: {provider_id}")

    bridge = _read_contract(root, BRIDGE_CONTRACT_PATH, "bridge provider policy")
    if provider_id in bridge.get("active_providers", {}):
        raise PublicationControlError(f"preactivation provider unexpectedly active: {provider_id}")
    disabled = bridge.get("disabled_providers", {}).get(provider_id)
    if not isinstance(disabled, dict):
        raise PublicationControlError(f"preactivation provider lacks disabled policy: {provider_id}")
    bridge_requirements = {
        "status": admission["required_bridge_provider_status"],
        "current_collection": admission["required_bridge_current_collection"],
        "runtime_scope": admission["required_bridge_runtime_scope"],
        "target_state": admission["required_bridge_target_state"],
        "vps_runtime_status": admission["required_bridge_vps_runtime_status"],
        "provider_policy_transition": admission["required_bridge_provider_policy_transition"],
        "network_calls": admission["required_bridge_network_calls"],
    }
    if any(disabled.get(key) != value for key, value in bridge_requirements.items()):
        raise PublicationControlError(f"preactivation provider bridge policy mismatch: {provider_id}")

    declarations = _d8_declarations(root)
    capability = declarations.get(series["capability_id"])
    if not isinstance(capability, dict) or capability.get("provider") != provider_id:
        raise PublicationControlError("preactivation capability/provider identity mismatch")
    if routing.get("provider") != provider_id or routing.get("series_id") != series["series_id"]:
        raise PublicationControlError("preactivation routing identity mismatch")
    if routing.get("target_residence_role") != "WARM":
        raise PublicationControlError("preactivation publication target must be WARM")
    if routing.get("publication_eligibility") != ELIGIBLE_PUBLICATION_POLICY:
        raise PublicationControlError("preactivation publication eligibility is not checkpoint-v2 terminal")
    return True


def _provider_policy(index: dict[str, Any], provider_id: str) -> dict[str, Any] | None:
    policy = next(
        (row for row in index["provider_policies"] if row.get("provider_id") == provider_id),
        None,
    )
    return policy if isinstance(policy, dict) else None


def _provider_admission_kind(
    index: dict[str, Any],
    root: Path,
    series: dict[str, Any],
    routing: dict[str, Any],
    *,
    qualification_mode: bool,
) -> str:
    policy = _provider_policy(index, series["provider"])
    if isinstance(policy, dict) and policy.get("status") == "ACTIVE":
        return ACTIVE_PROVIDER_AUTHORITY
    if _preactivation_admission_allowed(root, series, routing):
        return PREACTIVATION_QUALIFICATION_ONLY if qualification_mode else PREACTIVATION_REQUIRES_QUALIFICATION_MODE
    return REJECT_PROVIDER


def _load_manifest(root: Path) -> dict[str, Any] | None:
    path = root / CONTROL_PATH
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationControlError("D8 publication control manifest is unreadable") from exc
    if (
        payload.get("schema_version") != CONTROL_SCHEMA
        or payload.get("backend_profile") != BACKEND_PROFILE
        or payload.get("representation") != REPRESENTATION
        or not isinstance(payload.get("publications"), list)
    ):
        raise PublicationControlError("D8 publication control manifest identity mismatch")
    return payload


def _validate_publication(root: Path, publication: dict[str, Any]) -> dict[str, Any]:
    required = {
        "batch_id", "residence_role", "adapter_profile", "resource_ref", "resource_path",
        "sha256", "size_bytes", "data_commit_sha", "member_count", "member_observation_ids",
        "membership_sha256", "payload_sha256", "series",
    }
    if not isinstance(publication, dict) or not required <= set(publication):
        raise PublicationControlError("D8 publication control entry incomplete")
    if publication["residence_role"] != "WARM" or publication["adapter_profile"] != BACKEND_PROFILE:
        raise PublicationControlError("D8 publication backend/residence binding mismatch")
    if not isinstance(publication["batch_id"], str) or not publication["batch_id"].startswith("pub-"):
        raise PublicationControlError("D8 publication batch identity invalid")
    if publication["resource_ref"] != f"d8-publication:{publication['batch_id']}":
        raise PublicationControlError("D8 publication resource_ref identity mismatch")
    expected_path = f"history/d8-origin/resources/{publication['batch_id']}.json"
    if publication["resource_path"] != expected_path:
        raise PublicationControlError("D8 publication resource path is not canonical")
    target = _safe_path(root, publication["resource_path"])
    if not target.is_file():
        raise PublicationControlError(f"D8 publication resource missing: {publication['resource_path']}")
    raw = target.read_bytes()
    if publication["size_bytes"] != len(raw) or publication["sha256"] != hashlib.sha256(raw).hexdigest():
        raise PublicationControlError("D8 publication resource integrity mismatch")
    try:
        resource = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationControlError("D8 publication resource is not valid JSON") from exc
    if (
        resource.get("schema_version") != DATA_SCHEMA
        or resource.get("representation") != REPRESENTATION
        or resource.get("batch_id") != publication["batch_id"]
        or resource.get("target_residence_role") != "WARM"
        or resource.get("member_count") != publication["member_count"]
        or resource.get("member_observation_ids") != publication["member_observation_ids"]
        or resource.get("membership_sha256") != publication["membership_sha256"]
        or resource.get("payload_sha256") != publication["payload_sha256"]
    ):
        raise PublicationControlError("D8 publication logical batch/resource binding mismatch")
    observations = resource.get("observations")
    if not isinstance(observations, list) or len(observations) != publication["member_count"]:
        raise PublicationControlError("D8 publication observation membership invalid")
    resource_ids = [row.get("observation_id") for row in observations if isinstance(row, dict)]
    if resource_ids != publication["member_observation_ids"] or len(resource_ids) != len(set(resource_ids)):
        raise PublicationControlError("D8 publication resource member order/identity mismatch")

    try:
        rebuilt_batch = build_publication_batch(observations)
    except PublicationBatchError as exc:
        raise PublicationControlError("D8 publication remote envelopes do not form a valid PublicationBatch") from exc
    for key in ("batch_id", "member_count", "member_observation_ids", "membership_sha256", "payload_sha256"):
        if rebuilt_batch.get(key) != publication.get(key) or rebuilt_batch.get(key) != resource.get(key):
            raise PublicationControlError(f"D8 publication remote PublicationBatch {key} mismatch")

    controlled_ids: list[str] = []
    for series in publication["series"]:
        if not isinstance(series, dict):
            raise PublicationControlError("D8 publication series binding must be object")
        routing = _route_bound_series(root, series)
        if routing.get("target_residence_role") != "WARM":
            raise PublicationControlError("D8 publication series target residence is not WARM")
        if routing.get("publication_eligibility") != ELIGIBLE_PUBLICATION_POLICY:
            raise PublicationControlError("D8 publication series is not checkpoint-v2 terminal eligible")
        for field in ("lifecycle_class", "normalization_family", "finality_policy"):
            if series.get(field) != routing[field]:
                raise PublicationControlError(f"D8 publication series routing mismatch: {series.get('series_id')}:{field}")
        if series.get("allowed_finality") != list(routing["allowed_finality"]):
            raise PublicationControlError("D8 publication finality policy binding mismatch")
        if series.get("interval_ms") is not None and (
            not isinstance(series["interval_ms"], int) or series["interval_ms"] <= 0
        ):
            raise PublicationControlError("D8 publication fixed-grid interval invalid")
        if routing["lifecycle_class"] == "FIXED_GRID" and series.get("interval_ms") is None:
            raise PublicationControlError("D8 publication fixed-grid interval missing")
        rows = series.get("observations")
        if not isinstance(rows, list) or not rows:
            raise PublicationControlError("D8 publication series observation binding missing")
        for row in rows:
            oid = row.get("observation_id") if isinstance(row, dict) else None
            if not isinstance(oid, str) or oid not in publication["member_observation_ids"]:
                raise PublicationControlError("D8 publication series observation identity mismatch")
            if row.get("finality") not in routing["allowed_finality"]:
                raise PublicationControlError("D8 publication series finality mismatch")
            if not isinstance(row.get("effective_timestamp_ms"), int):
                raise PublicationControlError("D8 publication effective timestamp missing")
            if not isinstance(row.get("known_at"), str):
                raise PublicationControlError("D8 publication known_at missing")
            controlled_ids.append(oid)
    if sorted(controlled_ids) != sorted(publication["member_observation_ids"]):
        raise PublicationControlError("D8 publication control membership is not exact")
    return publication


def publications(root: Path) -> list[dict[str, Any]]:
    manifest = _load_manifest(root)
    if manifest is None:
        return []
    validated = [_validate_publication(root, row) for row in manifest["publications"]]
    ids = [row["batch_id"] for row in validated]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise PublicationControlError("D8 publication manifest batch order/uniqueness failure")
    return validated


def _series_bindings(root: Path) -> dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    result: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for publication in publications(root):
        for series in publication["series"]:
            result.setdefault(series["series_id"], []).append((publication, series))
    for rows in result.values():
        rows.sort(key=lambda pair: (pair[0]["batch_id"], pair[1]["series_id"]))
    return result


def _kind(normalization_family: str) -> str:
    try:
        return NORMALIZATION_KINDS[normalization_family]
    except KeyError as exc:
        raise PublicationControlError(f"unmapped D8 normalization family: {normalization_family}") from exc


def _new_series_descriptor(series_id: str, bindings: list[tuple[dict[str, Any], dict[str, Any]]]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    first = bindings[0][1]
    if any(
        row["provider"] != first["provider"]
        or row["capability_id"] != first["capability_id"]
        or row["lifecycle_class"] != first["lifecycle_class"]
        or row["normalization_family"] != first["normalization_family"]
        or row["finality_policy"] != first["finality_policy"]
        or row.get("interval_ms") != first.get("interval_ms")
        for _, row in bindings
    ):
        raise PublicationControlError(f"D8 publication series control bindings conflict: {series_id}")
    profile_id = "d8-origin.v2." + hashlib.sha256(series_id.encode("utf-8")).hexdigest()[:24]
    coverage = min(
        observation["effective_timestamp_ms"]
        for _, row in bindings
        for observation in row["observations"]
    )
    lifecycle = first["lifecycle_class"]
    profile = {
        "provider_id": first["provider"],
        "source_provider": first["provider"],
        "history_mode": "FORWARD_ONLY",
        "availability_status": "PASS",
        "cold_manifest_path": "history/release-manifest.json",
        "warm_manifest_path": CONTROL_PATH,
        "hot_manifest_path": None,
        "plan_schema": base_v2.PLAN_SCHEMA,
        "series_kind": _kind(first["normalization_family"]),
        "coverage_semantics": lifecycle,
        "finality_policy": first["finality_policy"],
        "revision_policy": "IMMUTABLE",
        "hot_source_policy": base_v2._hot_source_policy(),
        "publication_control_path": CONTROL_PATH,
        "adapter_profile": BACKEND_PROFILE,
    }
    tokens = series_id.split(".")
    interval = series_id.rsplit(".", 1)[-1] if lifecycle == "FIXED_GRID" else None
    physical_series = interval if first["normalization_family"] == "OHLCV" else series_id
    descriptor = {
        "series_id": series_id,
        "profile_id": profile_id,
        "instrument": tokens[2] if len(tokens) > 2 else None,
        "series": "ohlcv" if first["normalization_family"] == "OHLCV" else "snapshot",
        "interval": interval,
        "source_interval_or_metric": physical_series,
        "coverage_start_ms": coverage,
        "coverage_boundary": "FORWARD_ONLY_START",
    }
    return profile_id, profile, descriptor


def build_index_v2(
    root: Path = base_v2.ROOT,
    *,
    qualification_mode: bool = False,
) -> dict[str, Any]:
    index = base_v2.build_index_v2(root)
    bindings = _series_bindings(root)
    existing = {row["series_id"] for row in index["series"]}
    preactivation_included = False
    for series_id, rows in sorted(bindings.items()):
        if series_id in existing:
            continue
        first = rows[0][1]
        routing = _route_bound_series(root, first)
        admission = _provider_admission_kind(
            index,
            root,
            first,
            routing,
            qualification_mode=qualification_mode,
        )
        if admission == PREACTIVATION_REQUIRES_QUALIFICATION_MODE:
            continue
        if admission == REJECT_PROVIDER:
            raise PublicationControlError(f"published D8 series provider is not admitted: {series_id}")
        profile_id, profile, descriptor = _new_series_descriptor(series_id, rows)
        profile["d8_origin_provider_admission"] = admission
        if admission == PREACTIVATION_QUALIFICATION_ONLY:
            preactivation_included = True
        index["profiles"][profile_id] = profile
        index["series"].append(descriptor)
    index["profiles"] = {key: index["profiles"][key] for key in sorted(index["profiles"])}
    index["series"].sort(key=lambda row: row["series_id"])
    index["authority"]["d8_origin_publication_control"] = CONTROL_PATH if bindings else None
    index["authority"]["d8_origin_adapter_profile"] = BACKEND_PROFILE if bindings else None
    index["authority"]["d8_origin_preactivation_qualification_admission"] = (
        QUALIFICATION_ADMISSION_PATH if preactivation_included else None
    )
    return index


def _publication_series_descriptor(
    index: dict[str, Any],
    series_id: str,
    *,
    admission: str,
    qualification_mode: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    row = next((item for item in index["series"] if item["series_id"] == series_id), None)
    if row is None:
        raise PublicationControlError(f"D8 publication series absent from projection: {series_id}")
    profile = index["profiles"][row["profile_id"]]
    policy = _provider_policy(index, profile["provider_id"])
    if isinstance(policy, dict) and policy.get("status") == "ACTIVE":
        return row, profile, policy
    if (
        qualification_mode
        and admission == PREACTIVATION_QUALIFICATION_ONLY
        and profile.get("d8_origin_provider_admission") == PREACTIVATION_QUALIFICATION_ONLY
        and isinstance(policy, dict)
        and policy.get("status") == "DISABLED_BY_POLICY"
    ):
        return row, profile, policy
    raise PublicationControlError(f"published D8 series provider admission rejected: {series_id}")


def _d8_raw_segments(
    root: Path,
    row: dict[str, Any],
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    series_id = row["series_id"]
    for publication, series in _series_bindings(root).get(series_id, []):
        for observation in series["observations"]:
            known_at_ms = base_v2.parse_utc_ms(observation["known_at"])
            if cutoff_ms is not None and known_at_ms > cutoff_ms:
                continue
            timestamp = observation["effective_timestamp_ms"]
            step = series.get("interval_ms") if series["lifecycle_class"] == "FIXED_GRID" else 1
            physical_end = timestamp + int(step or 1)
            if physical_end <= start_ms or timestamp >= end_ms:
                continue
            result.append(
                {
                    "segment_id": f"d8-warm:{publication['batch_id']}:{observation['observation_id']}",
                    "residence_role": "WARM",
                    "adapter_profile": BACKEND_PROFILE,
                    "resource_ref": publication["resource_ref"],
                    "integrity_evidence": {
                        "batch_id": publication["batch_id"],
                        "data_commit_sha": publication["data_commit_sha"],
                        "membership_sha256": publication["membership_sha256"],
                        "payload_sha256": publication["payload_sha256"],
                        "observation_id": observation["observation_id"],
                    },
                    "storage": "GIT_WARM_RESOURCE",
                    "source_manifest_path": CONTROL_PATH,
                    "resource_path": publication["resource_path"],
                    "sha256": publication["sha256"],
                    "size_bytes": publication["size_bytes"],
                    "generation_id": None,
                    "first_timestamp_ms": timestamp,
                    "last_timestamp_ms": timestamp,
                    "physical_start_ms": timestamp,
                    "physical_end_ms": physical_end,
                    "physical_descriptor": {
                        "resource_path": publication["resource_path"],
                        "representation": REPRESENTATION,
                        "batch_id": publication["batch_id"],
                    },
                    "authority_priority": 50,
                    "source_provider": series["provider"],
                    "instrument": row.get("instrument"),
                    "source_interval_or_metric": row["source_interval_or_metric"],
                    "known_gaps": [],
                    "normalization_family": series["normalization_family"],
                    "d8_observation_ids": [observation["observation_id"]],
                    "d8_effective_timestamp_ms": timestamp,
                }
            )
    return result


def _neutralize(segment: dict[str, Any]) -> dict[str, Any]:
    if all(key in segment for key in ("residence_role", "adapter_profile", "resource_ref", "integrity_evidence")):
        return segment
    storage = segment.get("storage")
    residence = "COLD" if storage in {"GITHUB_RELEASE_ASSET", "GITHUB_RELEASE_WARM_ASSET"} else "HOT" if storage == "HOT_CURRENT_RESOURCE" else "WARM"
    resource_ref = "resource:" + hashlib.sha256(
        f"{storage}|{segment.get('resource_path')}|{segment.get('asset_id')}|{segment.get('sha256')}".encode("utf-8")
    ).hexdigest()
    return {
        **segment,
        "residence_role": residence,
        "adapter_profile": BACKEND_PROFILE,
        "resource_ref": resource_ref,
        "integrity_evidence": {"sha256": segment.get("sha256"), "size_bytes": segment.get("size_bytes")},
    }


def _select_non_overlapping(raw: list[dict[str, Any]], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    """Use v2 priority semantics but never merge distinct D8 observation identities."""
    points = {start_ms, end_ms}
    for item in raw:
        points.add(max(start_ms, item["physical_start_ms"]))
        points.add(min(end_ms, item["physical_end_ms"]))
    ordered = sorted(point for point in points if start_ms <= point <= end_ms)
    selected: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:]):
        if left >= right:
            continue
        covering = [item for item in raw if item["physical_start_ms"] <= left and item["physical_end_ms"] >= right]
        if not covering:
            raise RuntimeError(f"UNRESOLVED_SEGMENT_GAP: {left}->{right}")
        best_priority = max(item["authority_priority"] for item in covering)
        best = [item for item in covering if item["authority_priority"] == best_priority]
        identities = {(item["segment_id"], item["sha256"]) for item in best}
        if len(identities) != 1:
            raise RuntimeError(f"AMBIGUOUS_PHYSICAL_AUTHORITY: {left}->{right}")
        chosen = dict(best[0])
        chosen["read_start_ms"] = left
        chosen["read_end_ms"] = right
        chosen["segment_id"] = f"{chosen['segment_id']}:{left}:{right}"
        for key in ("physical_start_ms", "physical_end_ms", "authority_priority"):
            chosen.pop(key, None)
        merge_fields = ("storage", "sha256", "resource_path", "asset_id", "generation_id", "d8_observation_ids")
        if selected and all(selected[-1].get(key) == chosen.get(key) for key in merge_fields) and selected[-1]["read_end_ms"] == left:
            selected[-1]["read_end_ms"] = right
        else:
            selected.append(chosen)
    return selected


def _build_plan(
    index: dict[str, Any],
    row: dict[str, Any],
    profile: dict[str, Any],
    *,
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
    current_policy: str,
    qualification_mode: bool,
    root: Path,
) -> dict[str, Any]:
    step = base_v2._step_ms(row, profile)
    if profile.get("adapter_profile") == BACKEND_PROFILE and profile["coverage_semantics"] == "FIXED_GRID":
        step = profile.get("interval_ms") or row.get("interval") and base_v2.v1.INTERVAL_MS.get(row["interval"])
    if profile["coverage_semantics"] == "FIXED_GRID" and not isinstance(step, int):
        raise RuntimeError(f"FIXED_GRID_INTERVAL_MISSING: {row['series_id']}")
    coverage_start = row.get("coverage_start_ms")
    collection_gaps: list[dict[str, Any]] = []
    boundary = row.get("coverage_boundary", "FORWARD_ONLY_START")
    effective_start = start_ms
    if isinstance(coverage_start, int) and start_ms < coverage_start:
        if boundary not in {"PROVIDER_HISTORY_LIMIT", "FORWARD_ONLY_START"}:
            raise RuntimeError(f"HISTORY_NOT_FOUND: requested before declared availability {coverage_start}")
        effective_start = coverage_start
    if effective_start >= end_ms:
        raise RuntimeError(f"HISTORY_NOT_FOUND: availability starts at {coverage_start}")

    policy = _provider_policy(index, profile["provider_id"])
    active_provider = isinstance(policy, dict) and policy.get("status") == "ACTIVE"
    d8_raw = (
        _d8_raw_segments(root, row, effective_start, end_ms, cutoff_ms)
        if qualification_mode or active_provider
        else []
    )
    if profile["coverage_semantics"] == "FIXED_GRID":
        native_index = base_v2.build_index_v2(root)
        native_ids = {item["series_id"] for item in native_index["series"]}
        native_raw = base_v2._regular_raw_segments(
            root, row, profile, effective_start, end_ms, cutoff_ms, qualification_mode
        ) if row["series_id"] in native_ids else []
        segments = _select_non_overlapping(native_raw + d8_raw, effective_start, end_ms)
    else:
        native_segments: list[dict[str, Any]] = []
        if row["series_id"] in base_v2.SAMPLED_CAPABILITIES:
            native_segments, collection_gaps, declared = base_v2._sampled_segments_and_gaps(
                root, row["series_id"], effective_start, end_ms, cutoff_ms
            )
            if coverage_start is None:
                coverage_start = declared
        d8_by_time = {item["physical_start_ms"]: item for item in d8_raw}
        native_segments = [item for item in native_segments if item["read_start_ms"] not in d8_by_time]
        segments = native_segments
        for item in d8_raw:
            chosen = dict(item)
            physical_start = chosen.pop("physical_start_ms")
            physical_end = chosen.pop("physical_end_ms")
            chosen["read_start_ms"] = max(effective_start, physical_start)
            chosen["read_end_ms"] = min(end_ms, physical_end)
            chosen.pop("authority_priority", None)
            segments.append(chosen)
        segments.sort(key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"]))
        if not segments and not collection_gaps:
            raise RuntimeError(f"HISTORY_NOT_FOUND: no sampled evidence for {row['series_id']}")

    segments = [_neutralize(item) for item in segments]
    authority = {
        "route_policy": index["authority"]["route_policy"],
        "active_capability_index": "history/capability-index.json",
        "catalog_projection": "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG",
        "legacy_cold_manifest": profile["cold_manifest_path"],
        "warm_manifest": profile.get("warm_manifest_path"),
        "collection_ledger_root": "history/collection-runs" if profile["coverage_semantics"] != "FIXED_GRID" else None,
        "candidate_generation_index": "history/generation-index.json" if (root / "history/generation-index.json").is_file() else None,
        "d8_origin_publication_control": CONTROL_PATH if _series_bindings(root).get(row["series_id"]) else None,
        "d8_origin_provider_admission": profile.get("d8_origin_provider_admission"),
        "qualification_mode": qualification_mode,
        "d9_activation_status": "CANDIDATE_NOT_ACTIVE",
    }
    plan = {
        "schema_version": base_v2.PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": authority,
        "request": {
            "series_id": row["series_id"],
            "start_ms": start_ms,
            "end_ms": end_ms,
            "cutoff_ms": cutoff_ms,
            "current_policy": current_policy,
            "effective_start_ms": effective_start,
        },
        "series": {
            **row,
            "provider_id": profile["provider_id"],
            "source_provider": profile["source_provider"],
            "source_interval_or_metric": row["source_interval_or_metric"],
            "series_kind": profile["series_kind"],
            "coverage_semantics": profile["coverage_semantics"],
            "finality_policy": profile["finality_policy"],
            "revision_policy": profile["revision_policy"],
            "history_mode": profile["history_mode"],
            "availability_status": profile["availability_status"],
            "interval_ms": step,
            "coverage_boundary_evidence": {
                "kind": boundary,
                "declared_start_ms": coverage_start,
                "requested_start_ms": start_ms,
                "effective_start_ms": effective_start,
            },
            "collection_gaps": collection_gaps,
        },
        "segments": segments,
    }
    plan["plan_sha256"] = _plan_digest(plan)
    return plan


def resolve_capability_v2(
    series_id: str,
    start_utc: str,
    end_utc: str,
    cutoff_utc: str | None = None,
    *,
    current_policy: str = "FINALIZED_ONLY",
    qualification_mode: bool = False,
    root: Path = base_v2.ROOT,
) -> dict[str, Any]:
    bindings = _series_bindings(root)
    if series_id not in bindings:
        plan = base_v2.resolve_capability_v2(
            series_id,
            start_utc,
            end_utc,
            cutoff_utc,
            current_policy=current_policy,
            qualification_mode=qualification_mode,
            root=root,
        )
        plan["segments"] = [_neutralize(item) for item in plan["segments"]]
        plan["plan_sha256"] = _plan_digest(plan)
        return plan
    if current_policy not in {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}:
        raise RuntimeError("INVALID_CURRENT_POLICY")

    first = bindings[series_id][0][1]
    routing = _route_bound_series(root, first)
    base_index = base_v2.build_index_v2(root)
    admission = _provider_admission_kind(
        base_index,
        root,
        first,
        routing,
        qualification_mode=qualification_mode,
    )
    if admission == PREACTIVATION_REQUIRES_QUALIFICATION_MODE:
        raise PublicationControlError(f"{PREACTIVATION_REQUIRES_QUALIFICATION_MODE}: {series_id}")
    if admission == REJECT_PROVIDER:
        raise PublicationControlError(f"published D8 series provider is not admitted: {series_id}")

    index = build_index_v2(root, qualification_mode=qualification_mode)
    row, profile, _policy = _publication_series_descriptor(
        index,
        series_id,
        admission=admission,
        qualification_mode=qualification_mode,
    )
    start_ms = base_v2.parse_utc_ms(start_utc)
    end_ms = base_v2.parse_utc_ms(end_utc)
    cutoff_ms = base_v2.parse_utc_ms(cutoff_utc) if cutoff_utc else None
    if start_ms >= end_ms:
        raise RuntimeError("INVALID_TIME_RANGE")
    if cutoff_ms is not None and end_ms > cutoff_ms:
        raise RuntimeError("POINT_IN_TIME_RANGE_EXCEEDS_CUTOFF")
    return _build_plan(
        index,
        row,
        profile,
        start_ms=start_ms,
        end_ms=end_ms,
        cutoff_ms=cutoff_ms,
        current_policy=current_policy,
        qualification_mode=qualification_mode,
        root=root,
    )
