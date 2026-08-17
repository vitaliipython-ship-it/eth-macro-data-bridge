from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import release_publisher as release

ROOT = Path(__file__).resolve().parents[2]
GEN_SCHEMA = "market-data-history-generation/1.1.0"
INDEX_SCHEMA = "market-data-history-generation-index/1.1.0"
LEGACY_MANIFEST = Path("history/release-manifest.json")
CANDIDATE_INDEX = Path("history/generation-index.json")
SEALING_CONTRACT = Path("contracts/d9-sealing-candidate.json")
KRAKEN_SEMANTICS = Path("derivatives/metric-semantics.json")
CONTROL_NAMES = {
    "manifest.json",
    "release-manifest.json",
    "capability-index.json",
    "consistency-latest.json",
    "generation-index.json",
}
INTERVAL_MS = {"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000,"1w":604800000}


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_utc(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return int(parsed.timestamp() * 1000)


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def month_bounds(year: int, month: int) -> tuple[int, int]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def week_bounds(year: int, week: int) -> tuple[int, int]:
    start = datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def resource_descriptor(path: Path, root: Path = ROOT) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return {"path": rel, "sha256": sha256_bytes(raw), "size_bytes": len(raw)}


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def _read_manifest(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    if not target.is_file():
        raise RuntimeError(f"canonical WARM manifest missing: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"canonical WARM manifest invalid: {path}")
    return value


def _read_sealing_contract(root: Path) -> dict[str, Any]:
    value = _read_manifest(root, SEALING_CONTRACT.as_posix())
    policy = value.get("finalization_policy")
    membership = value.get("generation_membership")
    if not isinstance(policy, dict) or not isinstance(membership, dict):
        raise RuntimeError("D9 sealing membership/finalization policy missing")
    if not policy.get("policy_version") or not membership.get("policy_version"):
        raise RuntimeError("D9 sealing policy version missing")
    return value


def high_cardinality_warm_ready(root: Path = ROOT) -> bool:
    contract_path = root / SEALING_CONTRACT
    if not contract_path.is_file():
        return False
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    policy = contract.get("high_cardinality_warm")
    return bool(
        isinstance(policy, dict)
        and policy.get("status") == "READY"
        and policy.get("cold_sealing_enabled") is True
    )


def _coverage(row: dict[str, Any], mode: str) -> tuple[int, str]:
    start = row.get("first_timestamp")
    if not isinstance(start, int):
        raise RuntimeError("canonical WARM series missing declared coverage start")
    return start, mode


def declared_regular_authority(root: Path = ROOT) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Build semantic regular-series authority only from canonical WARM manifests."""
    authority: dict[tuple[str, str, str], dict[str, Any]] = {}

    spot = _read_manifest(root, "history/manifest.json")
    for row in spot.get("series", []):
        provider, symbol, interval = row.get("provider"), row.get("symbol"), row.get("interval")
        if provider not in {"binance", "kraken"} or not symbol or interval not in INTERVAL_MS:
            continue
        provider_id = "binance-spot" if provider == "binance" else "kraken-spot"
        coverage_start, coverage_mode = _coverage(
            row,
            "PROVIDER_LIMITED" if row.get("provider_history_limit") is True else "DECLARED_BACKFILL",
        )
        key = (provider, symbol, interval)
        authority[key] = {
            "series_id": f"spot.{provider_id}.{symbol}.ohlcv.{interval}",
            "legacy_key": key,
            "step_ms": INTERVAL_MS[interval],
            "coverage_start_ms": coverage_start,
            "coverage_mode": coverage_mode,
            "provider": provider,
            "metric": None,
        }

    kraken = _read_manifest(root, "derivatives/history-manifest.json")
    for row in kraken.get("series", []):
        if row.get("provider") != "kraken-futures":
            continue
        instrument, metric = row.get("instrument"), row.get("metric")
        if not instrument or not metric:
            continue
        history_mode = row.get("historical_backfill")
        coverage_start, coverage_mode = _coverage(
            row,
            "FORWARD_ONLY" if history_mode == "FORWARD_CONTINUATION" else "DECLARED_BACKFILL",
        )
        key = ("kraken-futures", instrument, metric)
        authority[key] = {
            "series_id": f"derivatives.kraken-futures.{instrument}.{metric}",
            "legacy_key": key,
            "step_ms": 300000,
            "coverage_start_ms": coverage_start,
            "coverage_mode": coverage_mode,
            "provider": "kraken-futures",
            "metric": metric,
        }

    deribit = _read_manifest(root, "derivatives/deribit-history-manifest.json")
    declared_deribit = list(deribit.get("series", [])) + list(deribit.get("d9_candidate_series", []))
    for row in declared_deribit:
        if row.get("provider") != "deribit-perpetual":
            continue
        instrument, metric = row.get("instrument"), row.get("metric")
        if not instrument or not metric:
            continue
        coverage_start, coverage_mode = _coverage(
            row,
            "FORWARD_ONLY" if row.get("historical_backfill") == "FORWARD_CONTINUATION" else "DECLARED_BACKFILL",
        )
        key = ("deribit-perpetual", instrument, metric)
        series_id = (
            f"derivatives.deribit-perpetual.{instrument}.ohlcv.1h"
            if metric == "OHLCV-1h"
            else f"derivatives.deribit-perpetual.{instrument}.{metric}"
        )
        authority[key] = {
            "series_id": series_id,
            "legacy_key": key,
            "step_ms": 3600000,
            "coverage_start_ms": coverage_start,
            "coverage_mode": coverage_mode,
            "provider": "deribit-perpetual",
            "metric": metric,
        }

    options = _read_manifest(root, "options/history-manifest.json")
    dvol = options.get("deribit_dvol")
    if isinstance(dvol, dict) and dvol.get("historical_backfill") == "PASS":
        coverage_start, coverage_mode = _coverage(dvol, "DECLARED_BACKFILL")
        key = ("deribit-options", "ETH", "DVOL-1h")
        authority[key] = {
            "series_id": "options.deribit-options.ETH.dvol.1h",
            "legacy_key": key,
            "step_ms": 3600000,
            "coverage_start_ms": coverage_start,
            "coverage_mode": coverage_mode,
            "provider": "deribit-options",
            "metric": "DVOL-1h",
        }
    return authority


def _payload_rows(path: Path) -> tuple[dict[str, Any], list[Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError(f"WARM resource has no records list: {path}")
    return payload, rows


def _physical_identity(path: Path, payload: dict[str, Any]) -> tuple[str, str, str] | None:
    provider = payload.get("provider")
    if provider in {"binance", "kraken"}:
        symbol, interval = payload.get("symbol"), payload.get("interval")
        return (provider, symbol, interval) if symbol and interval else None
    if provider == "kraken-futures":
        instrument, metric = payload.get("instrument"), payload.get("metric")
        return (provider, instrument, metric) if instrument and metric else None
    if provider == "deribit-perpetual":
        instrument, metric = payload.get("instrument"), payload.get("metric")
        return (provider, instrument, metric) if instrument and metric else None
    if provider in {"deribit", "deribit-options"} and payload.get("metric") in {"ETH-DVOL", "DVOL-1h"}:
        if path.name != "ETH-volatility-index-1h.json" or payload.get("resolution_seconds") != 3600:
            return None
        return ("deribit-options", "ETH", "DVOL-1h")
    return None


def declared_regular_resources(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    authority = declared_regular_authority(root)
    grouped: dict[str, dict[str, Any]] = {}
    roots = [root / "history", root / "derivatives" / "archive", root / "options" / "archive"]
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            if path.name in CONTROL_NAMES or "collection-runs" in path.parts or "revisions" in path.parts:
                continue
            try:
                payload, rows = _payload_rows(path)
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            identity = _physical_identity(path, payload)
            if identity is None or identity not in authority or not rows:
                continue
            policy = authority[identity]
            series_id = policy["series_id"]
            item = grouped.setdefault(
                series_id,
                {
                    **policy,
                    "resources": [],
                    "rows": {},
                    "anchor_ms": policy["coverage_start_ms"],
                },
            )
            timestamps = []
            for row in rows:
                if not isinstance(row, list) or not row or not isinstance(row[0], int):
                    raise RuntimeError(f"invalid WARM row: {path}")
                timestamp = int(row[0])
                timestamps.append(timestamp)
                old = item["rows"].get(timestamp)
                if old is not None and old != row:
                    raise RuntimeError(f"WARM identity conflict: {series_id}/{timestamp}")
                item["rows"][timestamp] = row
            descriptor = resource_descriptor(path, root)
            descriptor["_first_timestamp_ms"] = min(timestamps)
            descriptor["_last_timestamp_ms"] = max(timestamps)
            item["resources"].append(descriptor)
    return grouped


def legacy_cold_last(root: Path = ROOT) -> dict[tuple[str, str, str], int]:
    manifest = json.loads((root / LEGACY_MANIFEST).read_text(encoding="utf-8"))
    result = {}
    for row in manifest.get("series_inventory", []):
        key = (row.get("provider"), row.get("instrument"), row.get("interval_or_metric"))
        if all(key) and isinstance(row.get("last_timestamp"), int):
            result[key] = int(row["last_timestamp"])
    return result


def _grid_start(start_ms: int, step_ms: int, anchor_ms: int) -> int:
    return start_ms + ((anchor_ms - start_ms) % step_ms)


def _validate_fixed_grid(
    rows: list[Any],
    start_ms: int,
    end_ms: int,
    step_ms: int | None,
    anchor_ms: int | None,
) -> list[int]:
    timestamps = [int(row[0]) for row in rows]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise RuntimeError("candidate timestamp order/duplicate failure")
    if step_ms is None or anchor_ms is None:
        return []
    expected_start = _grid_start(start_ms, step_ms, anchor_ms)
    expected = list(range(expected_start, end_ms, step_ms))
    actual = set(timestamps)
    return [timestamp for timestamp in expected if timestamp not in actual]


def _period_resources(series: dict[str, Any], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    selected = []
    for resource in series["resources"]:
        if resource["_last_timestamp_ms"] < start_ms or resource["_first_timestamp_ms"] >= end_ms:
            continue
        selected.append({key: resource[key] for key in ("path", "sha256", "size_bytes")})
    return selected


def _month_keys(start_ms: int, as_of_ms: int) -> list[str]:
    cursor = datetime.fromtimestamp(start_ms / 1000, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    limit = datetime.fromtimestamp(as_of_ms / 1000, timezone.utc)
    result = []
    while cursor <= limit:
        result.append(cursor.strftime("%Y-%m"))
        cursor = datetime(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1, tzinfo=timezone.utc)
    return result


def _kraken_semantics(root: Path) -> dict[str, Any]:
    return _read_manifest(root, KRAKEN_SEMANTICS.as_posix())


def _finalization_constraint(
    policy: dict[str, Any],
    series: dict[str, Any],
    period_end_ms: int,
    root: Path,
) -> dict[str, Any]:
    finalization = policy["finalization_policy"]
    generic = finalization.get("regular_grid_default_finalization_lag_seconds")
    if not isinstance(generic, int) or generic < 0:
        raise RuntimeError("regular-grid finalization lag missing")
    provider_stabilization = 0
    revision_class = None
    revision_lag = 0
    metric_override = 0
    provider_overrides = finalization.get("provider_overrides", {})
    provider_policy = provider_overrides.get(series["provider"], {})
    if isinstance(provider_policy, dict):
        override = provider_policy.get("finalization_lag_seconds")
        if override is not None:
            if not isinstance(override, int) or override < 0:
                raise RuntimeError("invalid provider finalization lag")
            generic = max(generic, override)
        source = provider_policy.get("ingestion_stabilization_source")
        if source:
            semantics = _read_manifest(root, source)
            value = semantics.get("archive_ingestion", {}).get("stabilization_seconds")
            if not isinstance(value, int) or value < 0:
                raise RuntimeError("provider ingestion stabilization policy missing")
            provider_stabilization = value
    if series["provider"] == "kraken-futures":
        semantics = _kraken_semantics(root)
        metric_policy = semantics.get("metrics", {}).get(series["metric"])
        if not isinstance(metric_policy, dict) or not metric_policy.get("classification"):
            raise RuntimeError(f"Kraken semantic class missing: {series['metric']}")
        revision_class = metric_policy["classification"]
        class_lags = finalization.get("revision_class_lag_seconds", {})
        if revision_class == "PROVIDER_REVISABLE_SNAPSHOT" and revision_class not in class_lags:
            if finalization.get("missing_required_revision_policy") == "FAIL_CLOSED":
                raise RuntimeError("required revisable-class finalization policy missing")
            raise RuntimeError("revisable-class policy ambiguous")
        value = class_lags.get(revision_class, 0)
        if not isinstance(value, int) or value < 0:
            raise RuntimeError("invalid revision-class lag")
        revision_lag = value
        metric_key = f"{series['provider']}.{series['metric']}"
        override = finalization.get("metric_overrides", {}).get(metric_key, 0)
        if not isinstance(override, int) or override < 0:
            raise RuntimeError("invalid metric finalization lag")
        metric_override = override
    effective = max(generic, provider_stabilization, revision_lag, metric_override)
    return {
        "series_id": series["series_id"],
        "generic_finalization_lag_seconds": generic,
        "provider_ingestion_stabilization_seconds": provider_stabilization,
        "revision_class": revision_class,
        "revision_lag_seconds": revision_lag,
        "metric_override_lag_seconds": metric_override,
        "effective_lag_seconds": effective,
        "effective_seal_after_ms": period_end_ms + effective * 1000,
    }


def generation_membership_states(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    policy = _read_sealing_contract(root)
    authority = declared_regular_authority(root)
    physical = declared_regular_resources(root)
    cold = legacy_cold_last(root)
    periods: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for semantic in authority.values():
        after_legacy = cold.get(semantic["legacy_key"], -1) + semantic["step_ms"]
        semantic_start = max(semantic["coverage_start_ms"], after_legacy)
        for period in _month_keys(semantic_start, as_of_ms):
            year, month = map(int, period.split("-"))
            period_start, period_end = month_bounds(year, month)
            expected_start = max(period_start, semantic_start)
            if expected_start >= period_end:
                continue
            periods[period].append({
                **semantic,
                "period": period,
                "period_start_ms": period_start,
                "period_end_ms": period_end,
                "expected_start_ms": expected_start,
                "expected_end_ms": period_end,
            })

    states = []
    membership_version = policy["generation_membership"]["policy_version"]
    finalization_version = policy["finalization_policy"]["policy_version"]
    for period, expected in sorted(periods.items()):
        period_start = expected[0]["period_start_ms"]
        period_end = expected[0]["period_end_ms"]
        expected_ids = sorted(item["series_id"] for item in expected)
        complete: list[str] = []
        blocked: list[str] = []
        missing: list[str] = []
        members: list[dict[str, Any]] = []
        applicability = []
        constraints = []
        for semantic in sorted(expected, key=lambda item: item["series_id"]):
            series_id = semantic["series_id"]
            applicability.append({
                "declared_series_id": series_id,
                "declared_coverage_start_ms": semantic["coverage_start_ms"],
                "declared_coverage_mode": semantic["coverage_mode"],
                "period_start_ms": period_start,
                "period_end_ms": period_end,
                "expected_start_within_period_ms": semantic["expected_start_ms"],
                "expected_end_within_period_ms": semantic["expected_end_ms"],
                "series_required_for_generation": True,
            })
            constraint = _finalization_constraint(policy, semantic, period_end, root)
            constraints.append(constraint)
            concrete = physical.get(series_id)
            if concrete is None:
                missing.append(series_id)
                continue
            rows = [
                concrete["rows"][ts]
                for ts in sorted(concrete["rows"])
                if semantic["expected_start_ms"] <= ts < semantic["expected_end_ms"]
            ]
            if not rows:
                missing.append(series_id)
                continue
            gaps = _validate_fixed_grid(
                rows,
                semantic["expected_start_ms"],
                semantic["expected_end_ms"],
                semantic["step_ms"],
                semantic["coverage_start_ms"],
            )
            resources = _period_resources(concrete, semantic["expected_start_ms"], semantic["expected_end_ms"])
            if gaps or not resources:
                blocked.append(series_id)
                continue
            complete.append(series_id)
            if as_of_ms < constraint["effective_seal_after_ms"]:
                blocked.append(series_id)
            members.append({
                "period": period,
                "base_generation_id": f"history-grid-v1-{period}",
                "series_kind": "REGULAR_GRID",
                "series_id": series_id,
                "start_ms": semantic["expected_start_ms"],
                "end_ms": semantic["expected_end_ms"],
                "rows": rows,
                "resources": resources,
                "known_gaps": [],
            })
        period_closed = as_of_ms >= period_end
        if not period_closed:
            blocked = sorted(set(blocked) | set(expected_ids))
        membership = {
            "policy_version": membership_version,
            "expected_series_set": expected_ids,
            "actual_complete_series_set": sorted(complete),
            "blocked_series_set": sorted(set(blocked)),
            "missing_series_set": sorted(set(missing)),
            "applicability": applicability,
        }
        effective_after = max((row["effective_seal_after_ms"] for row in constraints), default=period_end)
        finalization = {
            "policy_version": finalization_version,
            "period_closed": period_closed,
            "effective_seal_after_ms": effective_after,
            "constraints": constraints,
        }
        ready = (
            period_closed
            and as_of_ms >= effective_after
            and membership["expected_series_set"] == membership["actual_complete_series_set"]
            and not membership["blocked_series_set"]
            and not membership["missing_series_set"]
        )
        states.append({
            "period": period,
            "base_generation_id": f"history-grid-v1-{period}",
            "series_kind": "REGULAR_GRID",
            "period_start_ms": period_start,
            "period_end_ms": period_end,
            "membership": membership,
            "finalization": finalization,
            "members": members,
            "ready": ready,
        })
    return states


def eligible_grid_periods(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    candidates = []
    for state in generation_membership_states(as_of_ms, root):
        if not state["ready"]:
            continue
        for member in state["members"]:
            candidates.append({
                **member,
                "generation_id": state["base_generation_id"],
                "membership": state["membership"],
                "finalization": state["finalization"],
            })
    return candidates


def _ledger_runs(root: Path) -> list[dict[str, Any]]:
    result = []
    base = root / "history" / "collection-runs"
    if not base.exists():
        return result
    for path in sorted(base.rglob("runs.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("runs", []):
            result.append({**row, "_ledger": resource_descriptor(path, root)})
    return result


def eligible_snapshot_periods(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    if not high_cardinality_warm_ready(root):
        return []
    runs = _ledger_runs(root)
    if not runs:
        return []
    grouped: dict[tuple[int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        expected = parse_utc(run["expected_schedule_at"])
        dt = datetime.fromtimestamp(expected/1000, timezone.utc)
        iso_year, iso_week, _ = dt.isocalendar()
        grouped[(iso_year, iso_week, run["series_or_capability"])].append(run)
    output = []
    for (year, week, capability), items in sorted(grouped.items()):
        start_ms, end_ms = week_bounds(year, week)
        if end_ms > as_of_ms:
            continue
        first_expected = min(parse_utc(item["expected_schedule_at"]) for item in items)
        expected_slots = list(range(max(start_ms, first_expected), end_ms, 3600000))
        by_slot = {parse_utc(item["expected_schedule_at"]): item for item in items}
        known_gaps = []
        observed = []
        resources = {}
        for slot in expected_slots:
            row = by_slot.get(slot)
            if row is None:
                known_gaps.append({"expected_schedule_at_ms":slot,"status":"COLLECTION_GAP","reason":"NO_LEDGER_RUN"})
                continue
            if row.get("status") != "OBSERVED_STATE" or not row.get("snapshot_ref"):
                known_gaps.append({"expected_schedule_at_ms":slot,"status":row.get("status"),"reason":row.get("error_class")})
                continue
            path = root / row["snapshot_ref"]
            if not path.is_file():
                known_gaps.append({"expected_schedule_at_ms":slot,"status":"COLLECTION_GAP","reason":"SNAPSHOT_REF_MISSING"})
                continue
            raw = path.read_bytes()
            observed.append({
                "expected_schedule_at_ms": slot,
                "known_at": row.get("known_at"),
                "retrieved_at": row.get("retrieved_at"),
                "snapshot_ref": row["snapshot_ref"],
                "snapshot_sha256": sha256_bytes(raw),
                "snapshot_size_bytes": len(raw),
                "payload": json.loads(raw),
            })
            resources[row["snapshot_ref"]] = resource_descriptor(path, root)
            ledger_desc = row["_ledger"]
            resources[ledger_desc["path"]] = ledger_desc
        if not observed:
            continue
        output.append({
            "period": f"{year}-W{week:02d}",
            "generation_id": f"history-snapshots-v1-{year}-W{week:02d}",
            "series_kind": "HIGH_CARDINALITY_SNAPSHOT",
            "series_id": capability,
            "start_ms": max(start_ms, first_expected),
            "end_ms": end_ms,
            "rows": observed,
            "resources": [resources[key] for key in sorted(resources)],
            "known_gaps": known_gaps,
        })
    return output


def detect(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    return eligible_grid_periods(as_of_ms, root) + eligible_snapshot_periods(as_of_ms, root)


def _asset_payload(candidate: dict[str, Any], generation_id: str) -> dict[str, Any]:
    return {
        "schema_version": "market-data-cold-asset/1.0.0",
        "generation_id": generation_id,
        "series_id": candidate["series_id"],
        "series_kind": candidate["series_kind"],
        "coverage_start_ms": candidate["start_ms"],
        "coverage_end_ms": candidate["end_ms"],
        "known_gaps": candidate["known_gaps"],
        "records": candidate["rows"],
    }


def _candidate_fingerprint(members: list[dict[str, Any]]) -> str:
    membership = members[0].get("membership")
    finalization = members[0].get("finalization")
    evidence = []
    for member in sorted(members, key=lambda item: item["series_id"]):
        evidence.append({
            "series_id": member["series_id"],
            "start_ms": member["start_ms"],
            "end_ms": member["end_ms"],
            "rows_sha256": sha256_bytes(compact(member["rows"])),
            "resource_paths": sorted(resource["path"] for resource in member["resources"]),
        })
    return sha256_bytes(compact({
        "period": members[0]["period"],
        "series_kind": members[0]["series_kind"],
        "membership": membership,
        "finalization": finalization,
        "evidence": evidence,
    }))


def _candidate_index_value(root: Path) -> dict[str, Any] | None:
    path = root / CANDIDATE_INDEX
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("generations"), list):
        raise RuntimeError("candidate generation index invalid")
    return value


def _period_for_index_row(row: dict[str, Any]) -> str | None:
    if isinstance(row.get("period"), str):
        return row["period"]
    match = re.match(r"^history-grid-v1-(\d{4}-\d{2})(?:-s[0-9a-f]+)?$", str(row.get("generation_id", "")))
    return match.group(1) if match else None


def _existing_generation_chain(root: Path, period: str) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    index = _candidate_index_value(root)
    if index is None:
        return []
    result = []
    for row in index["generations"]:
        if _period_for_index_row(row) != period:
            continue
        manifest = None
        manifest_path = row.get("generation_manifest_path")
        if isinstance(manifest_path, str) and (root / manifest_path).is_file():
            manifest = json.loads((root / manifest_path).read_text(encoding="utf-8"))
        result.append((row, manifest))
    return result


def _resolve_generation_identity(
    root: Path,
    period: str,
    base_generation_id: str,
    fingerprint: str,
) -> tuple[str, str | None]:
    chain = _existing_generation_chain(root, period)
    if not chain:
        return base_generation_id, None
    latest_row, latest_manifest = chain[-1]
    latest_id = latest_row["generation_id"]
    latest_fingerprint = None if latest_manifest is None else latest_manifest.get("candidate_fingerprint")
    if latest_fingerprint == fingerprint:
        return latest_id, latest_row.get("supersedes")
    successor = f"{base_generation_id}-s{fingerprint[:12]}"
    for row, manifest in chain:
        if row["generation_id"] != successor:
            continue
        if manifest is not None and manifest.get("candidate_fingerprint") == fingerprint:
            return successor, row.get("supersedes")
        raise RuntimeError("generation successor identity collision")
    return successor, latest_id


def build(as_of_ms: int, output_root: Path, root: Path = ROOT) -> list[dict[str, Any]]:
    candidates = detect(as_of_ms, root)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["generation_id"]].append(candidate)
    manifests = []
    for base_generation_id, members in sorted(grouped.items()):
        fingerprint = _candidate_fingerprint(members)
        period = members[0]["period"]
        generation_id, supersedes = _resolve_generation_identity(root, period, base_generation_id, fingerprint)
        generation_dir = output_root / generation_id
        generation_dir.mkdir(parents=True, exist_ok=True)
        assets = []
        all_gaps = []
        for member in sorted(members, key=lambda item:item["series_id"]):
            name = f"{safe_slug(member['series_id'])}--{member['period']}.json"
            path = generation_dir / name
            raw = compact(_asset_payload(member, generation_id))
            path.write_bytes(raw)
            timestamps = [int(row[0]) if isinstance(row, list) else int(row["expected_schedule_at_ms"]) for row in member["rows"]]
            assets.append({
                "asset_name": name,
                "series_id": member["series_id"],
                "sha256": sha256_bytes(raw),
                "size_bytes": len(raw),
                "record_count": len(member["rows"]),
                "first_timestamp_ms": min(timestamps),
                "last_timestamp_ms": max(timestamps),
                "source_warm_resources": member["resources"],
                "remote_asset_id": None,
                "browser_download_url": None,
                "_local_path": str(path),
            })
            all_gaps.extend({"series_id":member["series_id"], **gap} for gap in member["known_gaps"])
        start_ms = min(item["start_ms"] for item in members)
        end_ms = max(item["end_ms"] for item in members)
        membership = members[0].get("membership")
        finalization = members[0].get("finalization")
        if membership is None:
            membership = {
                "policy_version":"d9-snapshot-membership/1.0.0",
                "expected_series_set":sorted(item["series_id"] for item in members),
                "actual_complete_series_set":sorted(item["series_id"] for item in members),
                "blocked_series_set":[],
                "missing_series_set":[],
                "applicability":[],
            }
        if finalization is None:
            finalization = {
                "policy_version":"d9-snapshot-finalization/1.0.0",
                "period_closed":True,
                "effective_seal_after_ms":end_ms,
                "constraints":[],
            }
        manifest = {
            "schema_version": GEN_SCHEMA,
            "generation_id": generation_id,
            "candidate_fingerprint": fingerprint,
            "period": period,
            "storage_role": "COLD",
            "state": "CANDIDATE",
            "series_kind": members[0]["series_kind"],
            "coverage_start_ms": start_ms,
            "coverage_end_ms": end_ms,
            "membership": membership,
            "finalization": finalization,
            "assets": [{k:v for k,v in asset.items() if not k.startswith("_")} for asset in assets],
            "known_gaps": all_gaps,
            "supersedes": supersedes,
            "publication": {
                "publish_status":"NOT_RUN","readback_status":"NOT_RUN","size_match":"NOT_RUN","sha256_match":"NOT_RUN",
                "overlap_proof":"PASS","cross_boundary_semantic_read":"NOT_RUN","activation_status":"NOT_ACTIVE",
                "release_tag":None,"release_id":None,"release_immutable":None,
            },
            "_asset_paths": {asset["asset_name"]:asset["_local_path"] for asset in assets},
        }
        public = {k:v for k,v in manifest.items() if not k.startswith("_")}
        manifest_path = generation_dir / "generation.json"
        manifest_path.write_bytes(compact(public))
        manifest["_manifest_path"] = str(manifest_path)
        manifests.append(manifest)
    return manifests


def _build_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            digest.update(file.relative_to(path).as_posix().encode("utf-8") + b"\0")
            digest.update(file.read_bytes())
    return digest.hexdigest()


def build_ab(as_of_ms: int, work_root: Path, root: Path = ROOT) -> list[dict[str, Any]]:
    a_root, b_root = work_root / "build-a", work_root / "build-b"
    for path in (a_root, b_root):
        if path.exists():
            shutil.rmtree(path)
    a = build(as_of_ms, a_root, root)
    build(as_of_ms, b_root, root)
    digest_a = _build_digest(a_root)
    digest_b = _build_digest(b_root)
    if digest_a != digest_b:
        raise RuntimeError("D9 COLD deterministic A/B mismatch")
    print(f"D9_3_BUILD_A_SHA256={digest_a}")
    print(f"D9_3_BUILD_B_SHA256={digest_b}")
    print("D9_3_DETERMINISM=PASS")
    return a


def _release_for_generation(generation_id: str):
    existing = release.release_by_tag(generation_id)
    if existing:
        if existing.get("draft") or not existing.get("immutable"):
            raise RuntimeError(f"existing COLD generation is not immutable published authority: {generation_id}")
        return existing
    return release.gh(
        "/releases",
        method="POST",
        payload={
            "tag_name": generation_id,
            "target_commitish": "main",
            "name": generation_id,
            "body": "D9 immutable COLD generation candidate. NOT ACTIVE until combined D9.3+D9.4 semantic qualification.",
            "draft": True,
            "prerelease": False,
        },
    )


def publish_generation(manifest: dict[str, Any]) -> dict[str, Any]:
    generation_id = manifest["generation_id"]
    remote_release = _release_for_generation(generation_id)
    if remote_release.get("draft"):
        for asset in manifest["assets"]:
            local_path = manifest["_asset_paths"][asset["asset_name"]]
            release.upload_verified(
                remote_release,
                {"asset_name":asset["asset_name"],"local_path":local_path,"size_bytes":asset["size_bytes"],"sha256":asset["sha256"]},
            )
        remote_release = release.gh(
            f"/releases/{remote_release['id']}", method="PATCH", payload={"draft":False,"prerelease":False}
        )
    remote_release = release.gh(f"/releases/{remote_release['id']}")
    if not remote_release.get("immutable"):
        raise RuntimeError("published D9 COLD generation is not immutable")
    remote_assets = {item["name"]:item for item in release.list_assets(remote_release["id"])}
    expected_names = {asset["asset_name"] for asset in manifest["assets"]}
    if set(remote_assets) != expected_names:
        raise RuntimeError(f"remote immutable generation membership mismatch: {generation_id}")
    for asset in manifest["assets"]:
        remote = remote_assets[asset["asset_name"]]
        if remote["size"] != asset["size_bytes"]:
            raise RuntimeError(f"remote COLD size mismatch: {asset['asset_name']}")
        raw = release.download_release_asset(remote["id"])
        if sha256_bytes(raw) != asset["sha256"]:
            raise RuntimeError(f"remote COLD sha mismatch: {asset['asset_name']}")
        asset["remote_asset_id"] = remote["id"]
        asset["browser_download_url"] = remote["browser_download_url"]
    manifest["publication"] = {
        "publish_status":"PASS","readback_status":"PASS","size_match":"PASS","sha256_match":"PASS",
        "overlap_proof":"PASS","cross_boundary_semantic_read":"NOT_RUN","activation_status":"NOT_ACTIVE",
        "release_tag":remote_release["tag_name"],"release_id":remote_release["id"],"release_immutable":True,
    }
    Path(manifest["_manifest_path"]).write_bytes(compact({k:v for k,v in manifest.items() if not k.startswith("_")}))
    print(f"CANDIDATE_PUBLICATION=PASS generation={generation_id}")
    print("REMOTE_BINARY_READBACK=PASS")
    print("REMOTE_SIZE_MATCH=PASS")
    print("REMOTE_SHA256_MATCH=PASS")
    print("OVERLAP_PROOF=PASS")
    print("CROSS_BOUNDARY_SEMANTIC_READ=NOT_RUN")
    print("D9_3_COLD_AUTHORITY_ACTIVATED=false")
    return manifest


def _index_row(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "generation_id": manifest["generation_id"],
        "generation_manifest_path": Path(manifest["_manifest_path"]).as_posix(),
        "period": manifest["period"],
        "candidate_fingerprint": manifest["candidate_fingerprint"],
        "series_ids": sorted(asset["series_id"] for asset in manifest["assets"]),
        "seal_start_ms": manifest["coverage_start_ms"],
        "seal_end_ms": manifest["coverage_end_ms"],
        "authority_status": "CANDIDATE_NOT_ACTIVE",
        "supersedes": manifest["supersedes"],
    }


def write_index(manifests: Iterable[dict[str, Any]], destination: Path) -> dict[str, Any]:
    existing_rows: list[dict[str, Any]] = []
    if destination.is_file():
        old = json.loads(destination.read_text(encoding="utf-8"))
        existing_rows = list(old.get("generations", []))
    by_id = {row["generation_id"]: row for row in existing_rows if isinstance(row, dict) and row.get("generation_id")}
    for manifest in manifests:
        if manifest["publication"]["publish_status"] != "PASS":
            continue
        row = _index_row(manifest)
        old = by_id.get(row["generation_id"])
        if old is not None:
            comparable_old = {key: old.get(key) for key in row}
            if comparable_old != row:
                raise RuntimeError(f"candidate index immutable generation mismatch: {row['generation_id']}")
        by_id[row["generation_id"]] = row
        if row["supersedes"] in by_id:
            by_id[row["supersedes"]] = {**by_id[row["supersedes"]], "authority_status":"SUPERSEDED"}
    rows = sorted(by_id.values(), key=lambda row: (row.get("period") or _period_for_index_row(row) or "", row["generation_id"]))
    value = {
        "schema_version": INDEX_SCHEMA,
        "status": "CANDIDATE_NOT_ACTIVE",
        "legacy_cold_manifest": LEGACY_MANIFEST.as_posix(),
        "generations": rows,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(compact(value))
    return value


def _install_generation_manifest(path: Path, manifest: dict[str, Any]) -> None:
    raw = compact({k:v for k,v in manifest.items() if not k.startswith("_")})
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("candidate_fingerprint") != manifest["candidate_fingerprint"]:
            raise RuntimeError(f"immutable candidate control-plane mismatch: {path.as_posix()}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def install_candidate_control_plane(manifests: Iterable[dict[str, Any]], root: Path = ROOT) -> dict[str, Any]:
    verified = [manifest for manifest in manifests if manifest["publication"]["publish_status"] == "PASS"]
    generation_root = root / "history" / "generations"
    generation_root.mkdir(parents=True, exist_ok=True)
    for manifest in verified:
        relative = Path("history/generations") / f"{manifest['generation_id']}.json"
        destination = root / relative
        _install_generation_manifest(destination, manifest)
        manifest["_manifest_path"] = relative.as_posix()
    index = write_index(verified, root / CANDIDATE_INDEX)
    print(f"D9_3_CANDIDATE_CONTROL_PLANE_INSTALL=PASS generations={len(verified)}")
    print("D9_3_LEGACY_COLD_MANIFEST_INSTALL=NOT_RUN")
    return index


def command_detect(args) -> None:
    as_of = parse_utc(args.as_of) if args.as_of else utc_now_ms()
    found = detect(as_of, ROOT)
    grid = sum(item["series_kind"] == "REGULAR_GRID" for item in found)
    snapshots = sum(item["series_kind"] == "HIGH_CARDINALITY_SNAPSHOT" for item in found)
    ready_generations = len({item["generation_id"] for item in found})
    print(f"D9_3_ELIGIBLE_SERIES_PERIODS={len(found)}")
    print(f"D9_3_ELIGIBLE_GRID_SERIES_PERIODS={grid}")
    print(f"D9_3_ELIGIBLE_SNAPSHOT_SERIES_PERIODS={snapshots}")
    print(f"D9_3_ELIGIBLE_GENERATIONS={ready_generations}")
    print("D9_3_AUTHORITY_SELECTION=CANONICAL_WARM_MANIFESTS")
    print(f"D9_3_HIGH_CARDINALITY_WARM={'READY' if high_cardinality_warm_ready(ROOT) else 'BLOCKED'}")
    print("D9_3_ACTIVE_PERIOD_SEALED=false")


def command_build(args) -> None:
    as_of = parse_utc(args.as_of) if args.as_of else utc_now_ms()
    work = Path(args.output or os.environ.get("RUNNER_TEMP", ".tmp")) / "d9-history-sealer"
    manifests = build_ab(as_of, work, ROOT)
    print(f"D9_3_GENERATION_CANDIDATES={len(manifests)}")
    print("D9_3_WARM_CLEANUP=NOT_RUN")


def command_publish(args) -> None:
    as_of = parse_utc(args.as_of) if args.as_of else utc_now_ms()
    work = Path(args.output or os.environ.get("RUNNER_TEMP", ".tmp")) / "d9-history-sealer"
    manifests = build_ab(as_of, work, ROOT)
    if not manifests:
        print("D9_3_CANDIDATE_PUBLICATION=NO_ELIGIBLE_COMPLETED_PERIOD")
        print("D9_3_WARM_CLEANUP=NOT_RUN")
        return
    for manifest in manifests:
        publish_generation(manifest)
    index = install_candidate_control_plane(manifests, ROOT)
    print(f"D9_3_GENERATION_INDEX={CANDIDATE_INDEX.as_posix()}")
    print(f"D9_3_GENERATION_INDEX_ENTRIES={len(index['generations'])}")
    print("D9_3_WARM_CLEANUP=NOT_RUN")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="D9 continuous WARM to immutable COLD candidate sealer")
    parser.add_argument("command", choices=("detect", "build", "publish"))
    parser.add_argument("--as-of")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    {"detect":command_detect,"build":command_build,"publish":command_publish}[args.command](args)


if __name__ == "__main__":
    main()
