from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import _capability_index_v1 as v1

ROOT = Path(__file__).resolve().parents[1]
PLAN_SCHEMA = "market-data-resolution-plan/2.0.0"
INDEX_SCHEMA = "2.0.0"
GENERATION_INDEX_SCHEMA = "market-data-history-generation-index/1.1.0"
GENERATION_SCHEMA = "market-data-history-generation/1.1.0"
LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
REVISION_SCHEMA = "market-data-provider-revision/1.0.0"
REVISABLE_CLASS = "PROVIDER_REVISABLE_SNAPSHOT"
CONTROL_FILENAMES = {"manifest.json", "release-manifest.json", "capability-index.json", "generation-index.json"}
STRUCTURED_KRAKEN_METRICS = {"aggressor-differential", "cvd", "spreads", "liquidity", "slippage"}
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
SAMPLED_CAPABILITIES: dict[str, dict[str, Any]] = {
    "options.deribit-options.ETH.surface-snapshots": {
        "provider_id": "deribit-options",
        "source_provider": "deribit-options",
        "domain": "options",
        "series_kind": "OPTION_SURFACE",
        "manifest_path": "options/manifest.json",
    },
    G2B_FAMILY: {
        "provider_id": "multi-provider",
        "source_provider": "multi-provider",
        "domain": "liquidity",
        "series_kind": "ORDER_BOOK_SNAPSHOT",
        "manifest_path": "liquidity/manifest.json",
    },
    "derivatives.deribit-perpetual.current-snapshot": {
        "provider_id": "deribit-perpetual",
        "source_provider": "deribit-perpetual",
        "domain": "derivatives",
        "series_kind": "SNAPSHOT_SERIES",
        "manifest_path": "derivatives/manifest.json",
    },
}


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def read_json(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    if not target.is_file():
        raise RuntimeError(f"CANONICAL_RESOURCE_MISSING: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"CANONICAL_RESOURCE_INVALID: {path}")
    return value


def parse_utc_ms(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"INVALID_UTC_TIMESTAMP: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise RuntimeError(f"INVALID_UTC_TIMESTAMP: {value}")
    return int(parsed.timestamp() * 1000)


def _status(value: Any) -> Any:
    return value.get("status") if isinstance(value, dict) else value


def _metric_revision_policy(root: Path, source_provider: str, metric: str) -> str:
    if source_provider != "kraken-futures":
        return "IMMUTABLE"
    semantics = read_json(root, "derivatives/metric-semantics.json")
    policy = semantics.get("metrics", {}).get(metric)
    classification = policy.get("classification") if isinstance(policy, dict) else None
    if classification not in {"STRICT_OVERLAP_REQUIRED", "WINDOW_ANCHORED_CUMULATIVE", REVISABLE_CLASS}:
        raise RuntimeError(f"REVISION_POLICY_MISSING: {metric}")
    return classification


def _series_kind(row: dict[str, Any], profile: dict[str, Any]) -> str:
    if row.get("series") == "ohlcv":
        return "OHLCV"
    if profile.get("source_provider") == "kraken-futures":
        return "STRUCTURED_TIME_SERIES" if row.get("source_interval_or_metric") in STRUCTURED_KRAKEN_METRICS else "SCALAR_TIME_SERIES"
    if row.get("series") == "dvol":
        return "SCALAR_TIME_SERIES"
    return "STRUCTURED_TIME_SERIES"


def _v2_profile_id(old_profile_id: str, series_kind: str, revision_policy: str) -> str:
    return f"{old_profile_id}.v2.{series_kind.lower()}.{revision_policy.lower()}"


def _manifest_series_row(manifest: dict[str, Any], source_provider: str, instrument: str, physical_series: str) -> dict[str, Any] | None:
    for item in manifest.get("series", []):
        if not isinstance(item, dict):
            continue
        identity = (
            item.get("provider"),
            item.get("symbol") or item.get("instrument"),
            item.get("interval") or item.get("metric") or item.get("interval_or_metric"),
        )
        if identity == (source_provider, instrument, physical_series):
            return item
    if source_provider == "deribit-options" and physical_series == "DVOL-1h":
        dvol = manifest.get("deribit_dvol")
        return dvol if isinstance(dvol, dict) else None
    return None


def _coverage_descriptor(root: Path, row: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    manifest_path = profile.get("hot_manifest_path")
    declared = None
    if manifest_path:
        declared = _manifest_series_row(
            read_json(root, manifest_path),
            profile["source_provider"],
            row["instrument"],
            row["source_interval_or_metric"],
        )
    if declared is None:
        release = read_json(root, profile["cold_manifest_path"])
        matches = [
            item for item in release.get("series_inventory", [])
            if (
                item.get("provider"), item.get("instrument"), item.get("interval_or_metric")
            ) == (profile["source_provider"], row["instrument"], row["source_interval_or_metric"])
        ]
        starts = [item.get("first_timestamp") for item in matches if isinstance(item.get("first_timestamp"), int)]
        if not starts:
            raise RuntimeError(f"DECLARED_COVERAGE_MISSING: {row['series_id']}")
        start_ms = min(starts)
    else:
        start_ms = declared.get("first_timestamp")
        if not isinstance(start_ms, int):
            raise RuntimeError(f"DECLARED_COVERAGE_MISSING: {row['series_id']}")
    mode = profile["history_mode"]
    if mode == "PROVIDER_LIMITED":
        boundary = "PROVIDER_HISTORY_LIMIT"
    elif mode == "FORWARD_ONLY":
        boundary = "FORWARD_ONLY_START"
    else:
        boundary = "AVAILABLE_START"
    return {"start_ms": start_ms, "boundary": boundary}


def _hot_source_policy() -> dict[str, Any]:
    return {
        "status": "NOT_ACTIVE",
        "locator_authority": "NONE",
        "transport_authority": "NONE",
        "runtime_class": "NONE",
        "provider_policy_transition_required": False,
        "runtime_task": None,
    }


def _safe_resource_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"CANONICAL_RESOURCE_PATH_INVALID: {relative}")
    root_resolved = root.resolve()
    resolved = (root / path).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise RuntimeError(f"CANONICAL_RESOURCE_PATH_INVALID: {relative}")
    return resolved


def _resource_descriptor(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "resource_path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _ledger_rows(root: Path, cutoff_ms: int | None = None) -> list[dict[str, Any]]:
    base = root / "history/collection-runs"
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.rglob("runs.json")):
        ledger = json.loads(path.read_text(encoding="utf-8"))
        if ledger.get("schema_version") != LEDGER_SCHEMA or not isinstance(ledger.get("runs"), list):
            raise RuntimeError(f"COLLECTION_LEDGER_SCHEMA_MISMATCH: {path.relative_to(root).as_posix()}")
        descriptor = _resource_descriptor(path, root)
        for run in ledger["runs"]:
            if not isinstance(run, dict):
                raise RuntimeError(f"COLLECTION_LEDGER_RUN_INVALID: {path.relative_to(root).as_posix()}")
            series_id = run.get("series_or_capability")
            if series_id not in SAMPLED_CAPABILITIES:
                raise RuntimeError(f"UNDECLARED_SAMPLED_CAPABILITY: {series_id}")
            expected_at = run.get("expected_schedule_at")
            known_at = run.get("known_at")
            retrieved_at = run.get("retrieved_at")
            if not all(isinstance(value, str) for value in (expected_at, known_at, retrieved_at)):
                raise RuntimeError(f"COLLECTION_LEDGER_TIMING_INVALID: {run.get('run_id')}")
            expected_ms = parse_utc_ms(expected_at)
            known_at_ms = parse_utc_ms(known_at)
            retrieved_at_ms = parse_utc_ms(retrieved_at)
            if cutoff_ms is not None and known_at_ms > cutoff_ms:
                continue
            rows.append({
                **run,
                "expected_schedule_at_ms": expected_ms,
                "known_at_ms": known_at_ms,
                "retrieved_at_ms": retrieved_at_ms,
                "ledger_resource": descriptor,
            })
    rows.sort(key=lambda item: (item["expected_schedule_at_ms"], item["series_or_capability"], item["run_id"]))
    return rows


def _sampled_profile(series_id: str, meta: dict[str, Any], base: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    forward = next((row for row in base.get("forward_capabilities", []) if row.get("capability_id") == series_id), None)
    availability = forward.get("availability_status") if isinstance(forward, dict) else "PASS"
    profile_id = f"sampled.v2.{series_id}"
    profile = {
        "provider_id": meta["provider_id"],
        "source_provider": meta["source_provider"],
        "history_mode": "FORWARD_ONLY",
        "availability_status": availability,
        "cold_manifest_path": "history/release-manifest.json",
        "warm_manifest_path": None,
        "hot_manifest_path": None,
        "plan_schema": PLAN_SCHEMA,
        "series_kind": meta["series_kind"],
        "coverage_semantics": "SAMPLED_SCHEDULE",
        "finality_policy": "OBSERVED_SNAPSHOT",
        "revision_policy": "IMMUTABLE",
        "hot_source_policy": _hot_source_policy(),
        "collection_ledger_root": "history/collection-runs",
        "domain_manifest_path": meta["manifest_path"],
    }
    return profile_id, profile


def _g2b_contract_binding(root: Path) -> dict[str, Any]:
    bridge = read_json(root, "bridge-contract.json")
    semantic = bridge.get("semantic_contracts", {}).get("liquidity_durable_l2")
    if not isinstance(semantic, dict):
        raise RuntimeError("G2B_DURABLE_L2_AUTHORITY_MISSING")
    if semantic.get("contract_id") != G2B_CONTRACT_ID or semantic.get("path") != G2B_CONTRACT_PATH:
        raise RuntimeError("G2B_DURABLE_L2_AUTHORITY_MISMATCH")
    contract = read_json(root, G2B_CONTRACT_PATH)
    if contract.get("schema_version") != G2B_CONTRACT_SCHEMA or contract.get("contract_id") != G2B_CONTRACT_ID:
        raise RuntimeError("G2B_DURABLE_L2_CONTRACT_IDENTITY_MISMATCH")
    if contract.get("family", {}).get("family_id") != G2B_FAMILY or contract.get("family", {}).get("new_parallel_deep_history_family") is not False:
        raise RuntimeError("G2B_HISTORY_FAMILY_CONFLICT")
    if contract.get("storage_independence", {}).get("durable_l2_physical_locator") != G2B_LOCATOR_PATTERN:
        raise RuntimeError("G2B_SUCCESSOR_LOCATOR_AUTHORITY_MISMATCH")
    if contract.get("legacy_compatibility", {}).get("legacy_snapshot_schema_version") != G2B_LEGACY_SCHEMA:
        raise RuntimeError("G2B_LEGACY_SCHEMA_AUTHORITY_MISMATCH")
    if contract.get("market_time", {}).get("known_at_after_cutoff_excluded") is not True:
        raise RuntimeError("G2B_PIT_AUTHORITY_MISSING")
    reuse = contract.get("authority_reuse", {})
    if any(reuse.get(key) is not False for key in ("second_history_reader", "second_capability_catalog", "second_temporal_authority")):
        raise RuntimeError("G2B_DUPLICATE_ARCHITECTURE_CONFLICT")
    contract_path = _safe_resource_path(root, G2B_CONTRACT_PATH)
    return {
        "contract_id": G2B_CONTRACT_ID,
        "contract_path": G2B_CONTRACT_PATH,
        "contract_resource": _resource_descriptor(contract_path, root),
        "history_family": G2B_FAMILY,
        "legacy_schema": G2B_LEGACY_SCHEMA,
        "partition_schema": G2B_PARTITION_SCHEMA,
        "observation_schema": G2B_OBSERVATION_SCHEMA,
        "locator_pattern": G2B_LOCATOR_PATTERN,
    }


def _g2b_day_paths(binding: dict[str, Any], start_ms: int, end_ms: int) -> list[tuple[str, str]]:
    start_day = datetime.fromtimestamp(start_ms / 1000, timezone.utc).date()
    end_day = datetime.fromtimestamp((end_ms - 1) / 1000, timezone.utc).date()
    current = start_day
    result: list[tuple[str, str]] = []
    while current <= end_day:
        relative = (
            binding["locator_pattern"]
            .replace("YYYY", f"{current.year:04d}")
            .replace("MM", f"{current.month:02d}")
            .replace("DD", f"{current.day:02d}")
        )
        result.append((current.isoformat(), relative))
        current += timedelta(days=1)
    return result


def _g2b_successor_segments(
    root: Path,
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
) -> tuple[list[dict[str, Any]], int | None]:
    binding = _g2b_contract_binding(root)
    result: list[dict[str, Any]] = []
    first_declared: int | None = None
    for date_utc, relative in _g2b_day_paths(binding, start_ms, end_ms):
        path = _safe_resource_path(root, relative)
        if not path.is_file():
            continue
        raw = path.read_bytes()
        try:
            partition = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"G2B_SUCCESSOR_PARTITION_INVALID_JSON: {relative}") from exc
        if (
            not isinstance(partition, dict)
            or partition.get("schema_version") != G2B_PARTITION_SCHEMA
            or partition.get("date_utc") != date_utc
            or partition.get("history_family") != G2B_FAMILY
            or not isinstance(partition.get("observations"), list)
        ):
            raise RuntimeError(f"G2B_UNKNOWN_LIQUIDITY_PARTITION_SCHEMA: {relative}")
        selected: list[dict[str, Any]] = []
        seen: dict[str, str] = {}
        for observation in partition["observations"]:
            if not isinstance(observation, dict) or observation.get("schema_version") != G2B_OBSERVATION_SCHEMA:
                raise RuntimeError(f"G2B_UNKNOWN_LIQUIDITY_OBSERVATION_SCHEMA: {relative}")
            timestamp = observation.get("observation_time_ms")
            known_at = observation.get("known_at_utc")
            identity = observation.get("durable_identity_sha256")
            observation_sha = observation.get("observation_sha256")
            durable_sha = observation.get("durable_record_sha256")
            if (
                not isinstance(timestamp, int)
                or not isinstance(known_at, str)
                or not isinstance(identity, str) or len(identity) != 64
                or not isinstance(observation_sha, str) or len(observation_sha) != 64
                or not isinstance(durable_sha, str) or len(durable_sha) != 64
            ):
                raise RuntimeError(f"G2B_MISSING_LIQUIDITY_SCHEMA: {relative}")
            previous = seen.get(identity)
            if previous is not None and previous != observation_sha:
                raise RuntimeError("G2B_IMMUTABLE_OBSERVATION_CONFLICT")
            seen[identity] = observation_sha
            if first_declared is None or timestamp < first_declared:
                first_declared = timestamp
            if not (start_ms <= timestamp < end_ms):
                continue
            known_at_ms = parse_utc_ms(known_at)
            if cutoff_ms is not None and known_at_ms > cutoff_ms:
                continue
            selected.append({
                "durable_identity_sha256": identity,
                "observation_sha256": observation_sha,
                "durable_record_sha256": durable_sha,
                "observation_time_ms": timestamp,
                "known_at_ms": known_at_ms,
                "provider_id": observation.get("provider_id"),
                "instrument_id": observation.get("instrument_id"),
                "book_kind": observation.get("book_kind"),
                "observation_id": observation.get("observation_id"),
            })
        if not selected:
            continue
        selected.sort(key=lambda item: (item["observation_time_ms"], item["durable_identity_sha256"]))
        descriptor = _resource_descriptor(path, root)
        result.append({
            "segment_id": f"g2b-successor:{date_utc}:{descriptor['sha256'][:16]}",
            "storage": "GIT_WARM_RESOURCE",
            "source_manifest_path": G2B_CONTRACT_PATH,
            "resource_path": descriptor["resource_path"],
            "sha256": descriptor["sha256"],
            "size_bytes": descriptor["size_bytes"],
            "generation_id": None,
            "first_timestamp_ms": selected[0]["observation_time_ms"],
            "last_timestamp_ms": selected[-1]["observation_time_ms"],
            "read_start_ms": max(start_ms, selected[0]["observation_time_ms"]),
            "read_end_ms": min(end_ms, selected[-1]["observation_time_ms"] + 1),
            "source_provider": "multi-provider",
            "instrument": None,
            "source_interval_or_metric": G2B_FAMILY,
            "known_gaps": [],
            "physical_descriptor": {"resource_path": descriptor["resource_path"]},
            "schema_class": G2B_SUCCESSOR_CLASS,
            "schema_binding": binding,
            "successor_observations": selected,
        })
    return result, first_declared


def build_index_v2(root: Path = ROOT) -> dict[str, Any]:
    base = read_json(root, "history/capability-index.json")
    if base.get("schema_version") != "1.1.0":
        raise RuntimeError("ACTIVE_CAPABILITY_INDEX_1_1_REQUIRED")
    bridge = read_json(root, "bridge-contract.json")
    provider_policies = json.loads(json.dumps(base["provider_policies"]))
    disabled_contract = bridge.get("disabled_providers", {})
    for policy in provider_policies:
        extra = disabled_contract.get(policy.get("provider_id"))
        if isinstance(extra, dict):
            for key in ("runtime_scope", "target_state", "provider_policy_transition"):
                if key in extra:
                    policy[key] = extra[key]
    if not any(item.get("provider_id") == "multi-provider" for item in provider_policies):
        provider_policies.append({
            "provider_id": "multi-provider",
            "domain": "liquidity",
            "status": "ACTIVE",
            "authority_role": "DECLARED_COMPOSITE_SAMPLED_CAPABILITY",
            "runtime_scope": "COLLECTION_LEDGER_BOUND",
        })
    provider_policies.sort(key=lambda item: item["provider_id"])

    profiles: dict[str, dict[str, Any]] = {}
    series: list[dict[str, Any]] = []
    for row in base["series"]:
        old_profile = base["profiles"][row["profile_id"]]
        kind = _series_kind(row, old_profile)
        revision = _metric_revision_policy(root, old_profile["source_provider"], row["source_interval_or_metric"])
        profile_id = _v2_profile_id(row["profile_id"], kind, revision)
        candidate = {
            **old_profile,
            "warm_manifest_path": old_profile.get("hot_manifest_path"),
            "plan_schema": PLAN_SCHEMA,
            "series_kind": kind,
            "coverage_semantics": "FIXED_GRID",
            "finality_policy": "FINALIZED_ONLY",
            "revision_policy": revision,
            "hot_source_policy": _hot_source_policy(),
        }
        previous = profiles.get(profile_id)
        if previous is not None and previous != candidate:
            raise RuntimeError(f"V2_PROFILE_COLLISION: {profile_id}")
        profiles[profile_id] = candidate
        coverage = _coverage_descriptor(root, row, old_profile)
        series.append({
            **row,
            "profile_id": profile_id,
            "coverage_start_ms": coverage["start_ms"],
            "coverage_boundary": coverage["boundary"],
        })

    ledger = _ledger_rows(root)
    by_sampled: dict[str, list[dict[str, Any]]] = {key: [] for key in SAMPLED_CAPABILITIES}
    for run in ledger:
        by_sampled[run["series_or_capability"]].append(run)
    for series_id, meta in sorted(SAMPLED_CAPABILITIES.items()):
        profile_id, profile = _sampled_profile(series_id, meta, base)
        profiles[profile_id] = profile
        runs = by_sampled[series_id]
        coverage_start = min((row["expected_schedule_at_ms"] for row in runs), default=None)
        if series_id == G2B_FAMILY:
            try:
                _segments, successor_start = _g2b_successor_segments(root, 0, 253402300799999, None)
            except (OverflowError, OSError, ValueError):
                successor_start = None
            starts = [value for value in (coverage_start, successor_start) if isinstance(value, int)]
            coverage_start = min(starts) if starts else None
        series.append({
            "series_id": series_id,
            "profile_id": profile_id,
            "instrument": None,
            "series": "snapshot",
            "interval": None,
            "source_interval_or_metric": series_id,
            "coverage_start_ms": coverage_start,
            "coverage_boundary": "FORWARD_ONLY_START",
        })

    return {
        "schema_version": INDEX_SCHEMA,
        "catalog_id": base["catalog_id"],
        "generation_policy": "DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
        "authority": {
            **base["authority"],
            "active_v1_catalog": "history/capability-index.json",
            "candidate_generation_index": "history/generation-index.json",
            "collection_ledger_root": "history/collection-runs",
            "projection": "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG",
        },
        "provider_policies": provider_policies,
        "profiles": {key: profiles[key] for key in sorted(profiles)},
        "series": sorted(series, key=lambda item: item["series_id"]),
    }


def _series_descriptor(index: dict[str, Any], series_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    row = next((item for item in index["series"] if item["series_id"] == series_id), None)
    if row is None:
        raise RuntimeError(f"UNKNOWN_SERIES_ID: {series_id}")
    profile = index["profiles"][row["profile_id"]]
    policy = next((item for item in index["provider_policies"] if item["provider_id"] == profile["provider_id"]), None)
    if not isinstance(policy, dict) or policy.get("status") != "ACTIVE":
        raise RuntimeError(f"PROVIDER_POLICY_CONFLICT: {profile['provider_id']}")
    return row, profile, policy


def _payload_key(payload: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        payload.get("provider"),
        payload.get("symbol") or payload.get("instrument"),
        payload.get("interval") or payload.get("metric") or payload.get("interval_or_metric"),
    )


def _manifest_generated_ms(manifest: dict[str, Any]) -> int | None:
    value = manifest.get("generated_at_utc") or manifest.get("backfill_as_of_utc")
    return parse_utc_ms(value) if isinstance(value, str) else None


def _warm_catalog(root: Path, profile: dict[str, Any], row: dict[str, Any], cutoff_ms: int | None) -> list[dict[str, Any]]:
    manifest_path = profile.get("warm_manifest_path")
    if not manifest_path:
        return []
    manifest = read_json(root, manifest_path)
    generated = _manifest_generated_ms(manifest)
    if cutoff_ms is not None and generated is not None and generated > cutoff_ms:
        return []
    declared = _manifest_series_row(manifest, profile["source_provider"], row["instrument"], row["source_interval_or_metric"])
    if declared is None:
        raise RuntimeError(f"WARM_MANIFEST_SERIES_MISMATCH: {row['series_id']}")
    base = (root / manifest_path).parent
    result = []
    for path in sorted(base.rglob("*.json")):
        if path.name in CONTROL_FILENAMES or "collection-runs" in path.parts or "revisions" in path.parts:
            continue
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if _payload_key(payload) != (profile["source_provider"], row["instrument"], row["source_interval_or_metric"]):
            continue
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            continue
        timestamps = [item[0] for item in records if isinstance(item, list) and item and isinstance(item[0], int)]
        if len(timestamps) != len(records) or timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise RuntimeError(f"WARM_RESOURCE_INTEGRITY: {path.relative_to(root).as_posix()}")
        result.append({
            **_resource_descriptor(path, root),
            "first_timestamp": timestamps[0],
            "last_timestamp": timestamps[-1],
        })
    return result


def _legacy_cold_catalog(root: Path, profile: dict[str, Any], row: dict[str, Any], cutoff_ms: int | None) -> list[dict[str, Any]]:
    release = read_json(root, profile["cold_manifest_path"])
    if release.get("storage_backend") != "GITHUB_RELEASE_ASSET":
        raise RuntimeError("COLD_STORAGE_BACKEND_MISMATCH")
    generated = _manifest_generated_ms(release)
    if cutoff_ms is not None and (generated is None or generated > cutoff_ms):
        return []
    wanted = (profile["source_provider"], row["instrument"], row["source_interval_or_metric"])
    assets = []
    for asset in release.get("asset_inventory", []):
        if (asset.get("provider"), asset.get("instrument"), asset.get("interval_or_metric")) != wanted:
            continue
        if asset.get("release_tag") != profile.get("release_tag"):
            raise RuntimeError(f"RELEASE_TAG_MISMATCH: {asset.get('asset_name')}")
        required = ("asset_id", "asset_name", "browser_download_url", "sha256", "size_bytes", "first_timestamp", "last_timestamp")
        if any(asset.get(key) is None for key in required):
            raise RuntimeError(f"ASSET_AUTHORITY_INCOMPLETE: {asset.get('asset_name')}")
        if asset.get("integrity_status") != "PASS" or asset.get("immutable") is not True:
            raise RuntimeError(f"ASSET_NOT_IMMUTABLE_VERIFIED: {asset.get('asset_name')}")
        assets.append(asset)
    return sorted(assets, key=lambda item: (item["first_timestamp"], item["last_timestamp"], item["asset_name"]))


def _generation_catalog(root: Path, series_id: str, *, qualification_mode: bool) -> list[dict[str, Any]]:
    index_path = root / "history/generation-index.json"
    if not index_path.is_file():
        return []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema_version") != GENERATION_INDEX_SCHEMA:
        raise RuntimeError("GENERATION_INDEX_SCHEMA_MISMATCH")
    if index.get("legacy_cold_manifest") != "history/release-manifest.json":
        raise RuntimeError("GENERATION_INDEX_LEGACY_AUTHORITY_MISMATCH")
    allowed = {"ACTIVE"}
    if qualification_mode:
        allowed.add("CANDIDATE_NOT_ACTIVE")
    entries = [
        entry for entry in index.get("generations", [])
        if isinstance(entry, dict)
        and entry.get("authority_status") in allowed
        and series_id in entry.get("series_ids", [])
    ]
    superseded_ids = {entry.get("supersedes") for entry in entries if isinstance(entry.get("supersedes"), str)}
    entries = [entry for entry in entries if entry.get("generation_id") not in superseded_ids]
    result = []
    for entry in entries:
        manifest_path = entry.get("generation_manifest_path")
        if not isinstance(manifest_path, str):
            raise RuntimeError("GENERATION_MANIFEST_PATH_MISSING")
        manifest = read_json(root, manifest_path)
        if manifest.get("schema_version") != GENERATION_SCHEMA or manifest.get("generation_id") != entry.get("generation_id"):
            raise RuntimeError("GENERATION_MANIFEST_IDENTITY_MISMATCH")
        publication = manifest.get("publication", {})
        required_pass = ("publish_status", "readback_status", "size_match", "sha256_match", "overlap_proof")
        if any(publication.get(key) != "PASS" for key in required_pass) or publication.get("release_immutable") is not True:
            raise RuntimeError(f"GENERATION_PUBLICATION_NOT_QUALIFIED: {manifest.get('generation_id')}")
        if entry.get("authority_status") == "ACTIVE":
            if publication.get("cross_boundary_semantic_read") != "PASS" or publication.get("activation_status") != "ACTIVE":
                raise RuntimeError(f"ACTIVE_GENERATION_GATE_INCOMPLETE: {manifest.get('generation_id')}")
        elif not qualification_mode:
            continue
        for asset in manifest.get("assets", []):
            if asset.get("series_id") != series_id:
                continue
            required = ("asset_name", "sha256", "size_bytes", "first_timestamp_ms", "last_timestamp_ms", "remote_asset_id", "browser_download_url")
            if any(asset.get(key) is None for key in required):
                raise RuntimeError(f"GENERATION_ASSET_AUTHORITY_INCOMPLETE: {asset.get('asset_name')}")
            result.append({
                **asset,
                "generation_id": manifest["generation_id"],
                "generation_manifest_path": manifest_path,
                "release_tag": publication.get("release_tag") or manifest["generation_id"],
                "authority_status": entry["authority_status"],
                "supersedes": entry.get("supersedes"),
                "known_gaps": manifest.get("known_gaps", []),
            })
    result.sort(key=lambda item: (item["first_timestamp_ms"], item["last_timestamp_ms"], item["generation_id"], item["asset_name"]))
    return result


def _revision_resources(
    root: Path,
    profile: dict[str, Any],
    row: dict[str, Any],
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
) -> list[dict[str, Any]]:
    if profile.get("revision_policy") != REVISABLE_CLASS or profile.get("source_provider") != "kraken-futures":
        return []
    evidence_root = root / "derivatives/revisions/evidence"
    if not evidence_root.exists():
        return []
    instrument = row["instrument"]
    metric = row["source_interval_or_metric"]
    result = []
    for path in sorted(evidence_root.rglob(f"{instrument}-{metric}-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != REVISION_SCHEMA:
            raise RuntimeError(f"REVISION_SCHEMA_MISMATCH: {path.relative_to(root).as_posix()}")
        if (
            payload.get("classification") != REVISABLE_CLASS
            or payload.get("provider") != "kraken-futures"
            or payload.get("instrument") != instrument
            or payload.get("metric") != metric
        ):
            raise RuntimeError(f"REVISION_IDENTITY_MISMATCH: {path.relative_to(root).as_posix()}")
        timestamp = payload.get("effective_timestamp")
        known_at = payload.get("known_at_utc")
        if not isinstance(timestamp, int) or not isinstance(known_at, str) or not (start_ms <= timestamp < end_ms):
            continue
        known_at_ms = parse_utc_ms(known_at)
        if cutoff_ms is not None and known_at_ms > cutoff_ms:
            continue
        descriptor = _resource_descriptor(path, root)
        source_ref = payload.get("source_snapshot_ref")
        if not isinstance(source_ref, str):
            raise RuntimeError(f"REVISION_SOURCE_REF_INVALID: {path.relative_to(root).as_posix()}")
        source_path = _safe_resource_path(root, source_ref)
        if not source_path.is_file():
            raise RuntimeError(f"REVISION_SOURCE_MISSING: {source_ref}")
        result.append({
            **descriptor,
            "known_at_ms": known_at_ms,
            "effective_timestamp_ms": timestamp,
            "revision_id": payload.get("revision_id"),
            "source_snapshot": _resource_descriptor(source_path, root),
        })
    return result


def _step_ms(row: dict[str, Any], profile: dict[str, Any]) -> int | None:
    interval = row.get("interval")
    if interval in v1.INTERVAL_MS:
        return v1.INTERVAL_MS[interval]
    if profile.get("source_provider") == "kraken-futures":
        return 300000
    if row.get("series") == "dvol":
        return 3600000
    return None


def _segment_common(profile: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_provider": profile["source_provider"],
        "instrument": row.get("instrument"),
        "source_interval_or_metric": row["source_interval_or_metric"],
        "known_gaps": [],
    }


def _regular_raw_segments(
    root: Path,
    row: dict[str, Any],
    profile: dict[str, Any],
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
    qualification_mode: bool,
) -> list[dict[str, Any]]:
    step = _step_ms(row, profile) or 1
    segments: list[dict[str, Any]] = []
    for asset in _legacy_cold_catalog(root, profile, row, cutoff_ms):
        segments.append({
            "segment_id": f"legacy-cold:{asset['release_tag']}:{asset['asset_id']}",
            "storage": "GITHUB_RELEASE_ASSET",
            "source_manifest_path": profile["cold_manifest_path"],
            "release_tag": asset["release_tag"],
            "asset_id": asset["asset_id"],
            "asset_name": asset["asset_name"],
            "browser_download_url": asset["browser_download_url"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
            "immutable": True,
            "generation_id": None,
            "first_timestamp_ms": asset["first_timestamp"],
            "last_timestamp_ms": asset["last_timestamp"],
            "physical_start_ms": asset["first_timestamp"],
            "physical_end_ms": asset["last_timestamp"] + step,
            "physical_descriptor": {"release_tag": asset["release_tag"], "asset_id": asset["asset_id"], "asset_name": asset["asset_name"], "browser_download_url": asset["browser_download_url"], "immutable": True},
            "authority_priority": 20,
            **_segment_common(profile, row),
        })
    for asset in _generation_catalog(root, row["series_id"], qualification_mode=qualification_mode):
        priority = 40 if asset["authority_status"] == "CANDIDATE_NOT_ACTIVE" else 30
        segments.append({
            "segment_id": f"generation-cold:{asset['generation_id']}:{asset['remote_asset_id']}",
            "storage": "GITHUB_RELEASE_ASSET",
            "source_manifest_path": asset["generation_manifest_path"],
            "release_tag": asset["release_tag"],
            "asset_id": asset["remote_asset_id"],
            "asset_name": asset["asset_name"],
            "browser_download_url": asset["browser_download_url"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
            "immutable": True,
            "generation_id": asset["generation_id"],
            "candidate_authority_status": asset["authority_status"],
            "first_timestamp_ms": asset["first_timestamp_ms"],
            "last_timestamp_ms": asset["last_timestamp_ms"],
            "physical_start_ms": asset["first_timestamp_ms"],
            "physical_end_ms": asset["last_timestamp_ms"] + step,
            "physical_descriptor": {"release_tag": asset["release_tag"], "asset_id": asset["remote_asset_id"], "asset_name": asset["asset_name"], "browser_download_url": asset["browser_download_url"], "immutable": True},
            "authority_priority": priority,
            "known_gaps": asset.get("known_gaps", []),
            **{key: value for key, value in _segment_common(profile, row).items() if key != "known_gaps"},
        })
    for resource in _warm_catalog(root, profile, row, cutoff_ms):
        revisions = _revision_resources(root, profile, row, resource["first_timestamp"], resource["last_timestamp"] + step, cutoff_ms)
        segments.append({
            "segment_id": f"warm:{resource['sha256'][:16]}:{resource['resource_path']}",
            "storage": "GIT_WARM_RESOURCE",
            "source_manifest_path": profile.get("warm_manifest_path"),
            "resource_path": resource["resource_path"],
            "sha256": resource["sha256"],
            "size_bytes": resource["size_bytes"],
            "generation_id": None,
            "first_timestamp_ms": resource["first_timestamp"],
            "last_timestamp_ms": resource["last_timestamp"],
            "physical_start_ms": resource["first_timestamp"],
            "physical_end_ms": resource["last_timestamp"] + step,
            "physical_descriptor": {"resource_path": resource["resource_path"]},
            "revision_evidence": revisions,
            "authority_priority": 10,
            **_segment_common(profile, row),
        })
    return [segment for segment in segments if segment["physical_end_ms"] > start_ms and segment["physical_start_ms"] < end_ms]


def _select_non_overlapping(raw: list[dict[str, Any]], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
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
        if selected and all(
            selected[-1].get(key) == chosen.get(key)
            for key in ("storage", "sha256", "resource_path", "asset_id", "generation_id")
        ) and selected[-1]["read_end_ms"] == left:
            selected[-1]["read_end_ms"] = right
        else:
            selected.append(chosen)
    return selected


def _sampled_segments_and_gaps(
    root: Path,
    series_id: str,
    start_ms: int,
    end_ms: int,
    cutoff_ms: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int | None]:
    all_ledger = _ledger_rows(root, cutoff_ms)
    runs = [
        row for row in all_ledger
        if row["series_or_capability"] == series_id and start_ms <= row["expected_schedule_at_ms"] < end_ms
    ]
    segments: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    first_declared = min((row["expected_schedule_at_ms"] for row in all_ledger if row["series_or_capability"] == series_id), default=None)
    binding = _g2b_contract_binding(root) if series_id == G2B_FAMILY else None
    for row in runs:
        ledger = row["ledger_resource"]
        expected_ms = row["expected_schedule_at_ms"]
        evidence = {
            "run_id": row["run_id"],
            "expected_schedule_at": row["expected_schedule_at"],
            "expected_schedule_at_ms": expected_ms,
            "known_at": row["known_at"],
            "known_at_ms": row["known_at_ms"],
            "retrieved_at": row["retrieved_at"],
            "retrieved_at_ms": row["retrieved_at_ms"],
            "provider": row["provider"],
            "status": row["status"],
            "snapshot_ref": row.get("snapshot_ref"),
            "error_class": row.get("error_class"),
            "provider_timestamp_at": row.get("provider_timestamp_at"),
            "freshness": row.get("freshness"),
            "ledger_resource": ledger,
        }
        if row.get("status") != "OBSERVED_STATE" or not isinstance(row.get("snapshot_ref"), str):
            gaps.append(evidence)
            continue
        snapshot_path = _safe_resource_path(root, row["snapshot_ref"])
        if not snapshot_path.is_file():
            gaps.append({**evidence, "status": "COLLECTION_GAP", "error_class": "SNAPSHOT_REF_MISSING"})
            continue
        descriptor = _resource_descriptor(snapshot_path, root)
        segment = {
            "segment_id": f"sampled-warm:{row['run_id']}:{descriptor['sha256'][:16]}",
            "storage": "GIT_WARM_RESOURCE",
            "source_manifest_path": None,
            "resource_path": descriptor["resource_path"],
            "sha256": descriptor["sha256"],
            "size_bytes": descriptor["size_bytes"],
            "generation_id": None,
            "first_timestamp_ms": expected_ms,
            "last_timestamp_ms": expected_ms,
            "read_start_ms": expected_ms,
            "read_end_ms": expected_ms + 1,
            "source_provider": SAMPLED_CAPABILITIES[series_id]["source_provider"],
            "instrument": None,
            "source_interval_or_metric": series_id,
            "known_gaps": [],
            "sampled_observation_at_ms": expected_ms,
            "collection_run": evidence,
            "physical_descriptor": {"resource_path": descriptor["resource_path"]},
        }
        if binding is not None:
            segment["schema_class"] = G2B_LEGACY_CLASS
            segment["schema_binding"] = binding
        segments.append(segment)
    if series_id == G2B_FAMILY:
        successor, successor_start = _g2b_successor_segments(root, start_ms, end_ms, cutoff_ms)
        segments.extend(successor)
        starts = [value for value in (first_declared, successor_start) if isinstance(value, int)]
        first_declared = min(starts) if starts else None
    segments.sort(key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"]))
    gaps.sort(key=lambda item: (item["expected_schedule_at_ms"], item["run_id"]))
    return segments, gaps, first_declared


def resolve_capability_v2(
    series_id: str,
    start_utc: str,
    end_utc: str,
    cutoff_utc: str | None = None,
    *,
    current_policy: str = "FINALIZED_ONLY",
    qualification_mode: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    if current_policy not in {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}:
        raise RuntimeError("INVALID_CURRENT_POLICY")
    index = build_index_v2(root)
    row, profile, _policy = _series_descriptor(index, series_id)
    start_ms = parse_utc_ms(start_utc)
    end_ms = parse_utc_ms(end_utc)
    cutoff_ms = parse_utc_ms(cutoff_utc) if cutoff_utc else None
    if start_ms >= end_ms:
        raise RuntimeError("INVALID_TIME_RANGE")
    if cutoff_ms is not None and end_ms > cutoff_ms:
        raise RuntimeError("POINT_IN_TIME_RANGE_EXCEEDS_CUTOFF")

    step = _step_ms(row, profile)
    if profile["coverage_semantics"] == "FIXED_GRID" and step is None:
        raise RuntimeError(f"FIXED_GRID_INTERVAL_MISSING: {series_id}")
    if row.get("series") == "ohlcv" and step:
        alignment = min(step, 86400000)
        if start_ms % alignment or end_ms % alignment:
            raise RuntimeError("UNALIGNED_OHLCV_RANGE")

    collection_gaps: list[dict[str, Any]] = []
    if profile["coverage_semantics"] == "FIXED_GRID":
        coverage_start = row.get("coverage_start_ms")
        if not isinstance(coverage_start, int):
            raise RuntimeError(f"DECLARED_COVERAGE_MISSING: {series_id}")
        boundary = row["coverage_boundary"]
        if start_ms < coverage_start:
            if boundary not in {"PROVIDER_HISTORY_LIMIT", "FORWARD_ONLY_START"}:
                raise RuntimeError(f"HISTORY_NOT_FOUND: requested before declared availability {coverage_start}")
            effective_start = coverage_start
        else:
            effective_start = start_ms
        if effective_start >= end_ms:
            raise RuntimeError(f"HISTORY_NOT_FOUND: availability starts at {coverage_start}")
        raw = _regular_raw_segments(root, row, profile, effective_start, end_ms, cutoff_ms, qualification_mode)
        segments = _select_non_overlapping(raw, effective_start, end_ms)
    else:
        segments, collection_gaps, declared_start = _sampled_segments_and_gaps(root, series_id, start_ms, end_ms, cutoff_ms)
        coverage_start = row.get("coverage_start_ms")
        starts = [value for value in (coverage_start, declared_start) if isinstance(value, int)]
        coverage_start = min(starts) if starts else None
        boundary = "FORWARD_ONLY_START"
        if not isinstance(coverage_start, int):
            raise RuntimeError(f"HISTORY_NOT_FOUND: no sampled evidence for {series_id}")
        effective_start = max(start_ms, coverage_start)
        segments = [item for item in segments if item["read_end_ms"] > effective_start]
        collection_gaps = [item for item in collection_gaps if item["expected_schedule_at_ms"] >= effective_start]
        if not segments and not collection_gaps:
            raise RuntimeError(f"HISTORY_NOT_FOUND: no sampled evidence for {series_id}")

    authority = {
        "route_policy": index["authority"]["route_policy"],
        "active_capability_index": "history/capability-index.json",
        "catalog_projection": "RUNTIME_SUCCESSOR_NO_SECOND_COMMITTED_CATALOG",
        "legacy_cold_manifest": profile["cold_manifest_path"],
        "warm_manifest": profile.get("warm_manifest_path"),
        "collection_ledger_root": "history/collection-runs" if profile["coverage_semantics"] != "FIXED_GRID" else None,
        "candidate_generation_index": "history/generation-index.json" if (root / "history/generation-index.json").is_file() else None,
        "qualification_mode": qualification_mode,
        "d9_activation_status": "CANDIDATE_NOT_ACTIVE",
    }
    if series_id == G2B_FAMILY:
        authority["liquidity_durable_l2_contract"] = _g2b_contract_binding(root)
    plan = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": authority,
        "request": {
            "series_id": series_id,
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
        "segments": sorted(segments, key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"])),
    }
    plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
    return plan
