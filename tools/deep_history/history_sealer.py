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
GEN_SCHEMA = "market-data-history-generation/1.0.0"
INDEX_SCHEMA = "market-data-history-generation-index/1.0.0"
LEGACY_MANIFEST = Path("history/release-manifest.json")
CANDIDATE_INDEX = Path("history/generation-index.json")
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
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
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


def declared_regular_authority(root: Path = ROOT) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Build the only admissible regular-series set from canonical WARM manifests.

    Physical tree discovery may locate bytes, but it never creates authority. A physical
    resource is sealable only when its semantic identity is declared here.
    """
    authority: dict[tuple[str, str, str], dict[str, Any]] = {}

    spot = _read_manifest(root, "history/manifest.json")
    for row in spot.get("series", []):
        provider, symbol, interval = row.get("provider"), row.get("symbol"), row.get("interval")
        if provider not in {"binance", "kraken"} or not symbol or interval not in INTERVAL_MS:
            continue
        provider_id = "binance-spot" if provider == "binance" else "kraken-spot"
        key = (provider, symbol, interval)
        authority[key] = {
            "series_id": f"spot.{provider_id}.{symbol}.ohlcv.{interval}",
            "legacy_key": key,
            "step_ms": INTERVAL_MS[interval],
        }

    kraken = _read_manifest(root, "derivatives/history-manifest.json")
    for row in kraken.get("series", []):
        if row.get("provider") != "kraken-futures":
            continue
        instrument, metric = row.get("instrument"), row.get("metric")
        if not instrument or not metric:
            continue
        key = ("kraken-futures", instrument, metric)
        authority[key] = {
            "series_id": f"derivatives.kraken-futures.{instrument}.{metric}",
            "legacy_key": key,
            "step_ms": 300000,
        }

    deribit = _read_manifest(root, "derivatives/deribit-history-manifest.json")
    declared_deribit = list(deribit.get("series", [])) + list(deribit.get("d9_candidate_series", []))
    for row in declared_deribit:
        if row.get("provider") != "deribit-perpetual":
            continue
        instrument, metric = row.get("instrument"), row.get("metric")
        if not instrument or not metric:
            continue
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
        }

    options = _read_manifest(root, "options/history-manifest.json")
    dvol = options.get("deribit_dvol")
    if isinstance(dvol, dict) and dvol.get("historical_backfill") == "PASS":
        key = ("deribit-options", "ETH", "DVOL-1h")
        authority[key] = {
            "series_id": "options.deribit-options.ETH.dvol.1h",
            "legacy_key": key,
            "step_ms": 3600000,
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
        # D9 canonical DVOL authority is the explicit 1h resource produced from
        # get_volatility_index_data(...resolution=3600). Preserve legacy files but do
        # not silently coerce their different physical sampling into the 1h series.
        resolution_seconds = payload.get("resolution_seconds")
        if path.name != "ETH-volatility-index-1h.json" or resolution_seconds != 3600:
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
                    "series_id": series_id,
                    "legacy_key": policy["legacy_key"],
                    "step_ms": policy["step_ms"],
                    "resources": [],
                    "rows": {},
                    "anchor_ms": None,
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
            first = min(timestamps)
            item["anchor_ms"] = first if item["anchor_ms"] is None else min(item["anchor_ms"], first)
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


def eligible_grid_periods(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    cold = legacy_cold_last(root)
    candidates = []
    for series_id, series in sorted(declared_regular_resources(root).items()):
        rows_by_ts = series["rows"]
        months = sorted({datetime.fromtimestamp(ts/1000, timezone.utc).strftime("%Y-%m") for ts in rows_by_ts})
        last_cold = cold.get(series["legacy_key"], -1)
        for period in months:
            year, month = map(int, period.split("-"))
            start_ms, end_ms = month_bounds(year, month)
            if end_ms > as_of_ms or start_ms <= last_cold:
                continue
            rows = [rows_by_ts[ts] for ts in sorted(rows_by_ts) if start_ms <= ts < end_ms]
            if not rows:
                continue
            missing = _validate_fixed_grid(rows, start_ms, end_ms, series["step_ms"], series["anchor_ms"])
            if missing:
                continue
            resources = _period_resources(series, start_ms, end_ms)
            if not resources:
                raise RuntimeError(f"eligible period has no authoritative WARM resource: {series_id}/{period}")
            candidates.append({
                "period": period,
                "generation_id": f"history-grid-v1-{period}",
                "series_kind": "REGULAR_GRID",
                "series_id": series_id,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "rows": rows,
                "resources": resources,
                "known_gaps": [],
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


def _asset_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "market-data-cold-asset/1.0.0",
        "generation_id": candidate["generation_id"],
        "series_id": candidate["series_id"],
        "series_kind": candidate["series_kind"],
        "coverage_start_ms": candidate["start_ms"],
        "coverage_end_ms": candidate["end_ms"],
        "known_gaps": candidate["known_gaps"],
        "records": candidate["rows"],
    }


def build(as_of_ms: int, output_root: Path, root: Path = ROOT) -> list[dict[str, Any]]:
    candidates = detect(as_of_ms, root)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["generation_id"]].append(candidate)
    manifests = []
    for generation_id, members in sorted(grouped.items()):
        generation_dir = output_root / generation_id
        generation_dir.mkdir(parents=True, exist_ok=True)
        assets = []
        all_gaps = []
        for member in sorted(members, key=lambda item:item["series_id"]):
            name = f"{safe_slug(member['series_id'])}--{member['period']}.json"
            path = generation_dir / name
            raw = compact(_asset_payload(member))
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
        manifest = {
            "schema_version": GEN_SCHEMA,
            "generation_id": generation_id,
            "storage_role": "COLD",
            "state": "CANDIDATE",
            "series_kind": members[0]["series_kind"],
            "coverage_start_ms": start_ms,
            "coverage_end_ms": end_ms,
            "assets": [{k:v for k,v in asset.items() if not k.startswith("_")} for asset in assets],
            "known_gaps": all_gaps,
            "supersedes": None,
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
    for asset in manifest["assets"]:
        remote = remote_assets.get(asset["asset_name"])
        if remote is None or remote["size"] != asset["size_bytes"]:
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


def write_index(manifests: Iterable[dict[str, Any]], destination: Path) -> dict[str, Any]:
    rows = []
    for manifest in manifests:
        if manifest["publication"]["publish_status"] != "PASS":
            continue
        rows.append({
            "generation_id": manifest["generation_id"],
            "generation_manifest_path": Path(manifest["_manifest_path"]).as_posix(),
            "series_ids": sorted(asset["series_id"] for asset in manifest["assets"]),
            "seal_start_ms": manifest["coverage_start_ms"],
            "seal_end_ms": manifest["coverage_end_ms"],
            "authority_status": "CANDIDATE_NOT_ACTIVE",
            "supersedes": manifest["supersedes"],
        })
    value = {
        "schema_version": INDEX_SCHEMA,
        "status": "CANDIDATE_NOT_ACTIVE",
        "legacy_cold_manifest": LEGACY_MANIFEST.as_posix(),
        "generations": rows,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(compact(value))
    return value


def command_detect(args) -> None:
    as_of = parse_utc(args.as_of) if args.as_of else utc_now_ms()
    found = detect(as_of, ROOT)
    grid = sum(item["series_kind"] == "REGULAR_GRID" for item in found)
    snapshots = sum(item["series_kind"] == "HIGH_CARDINALITY_SNAPSHOT" for item in found)
    print(f"D9_3_ELIGIBLE_SERIES_PERIODS={len(found)}")
    print(f"D9_3_ELIGIBLE_GRID_SERIES_PERIODS={grid}")
    print(f"D9_3_ELIGIBLE_SNAPSHOT_SERIES_PERIODS={snapshots}")
    print("D9_3_AUTHORITY_SELECTION=CANONICAL_WARM_MANIFESTS")
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
    index_path = work / "generation-index.generated.json"
    write_index(manifests, index_path)
    print(f"D9_3_GENERATION_INDEX={index_path}")
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
