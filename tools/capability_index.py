from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "history" / "capability-index.json"
SCHEMA_PATH = ROOT / "schema" / "capability-index.schema.json"

SCHEMA_VERSION = "1.0.0"
CATALOG_ID = "eth-macro-data-bridge-capability-index"
PLAN_SCHEMA = "market-data-resolution-plan/1.0.0"
RELEASE_PROVIDER_MAP = {
    "binance": "binance-spot",
    "kraken": "kraken-spot",
    "kraken-futures": "kraken-futures",
    "deribit-perpetual": "deribit-perpetual",
    "deribit-options": "deribit-options",
}
PROVIDER_DOMAIN = {
    "binance-spot": "spot",
    "kraken-spot": "spot",
    "kraken-futures": "derivatives",
    "deribit-perpetual": "derivatives",
    "deribit-options": "options",
    "binance-usdm": "derivatives",
}
DEPTH_MODE_BY_BOUNDARY = {
    "MAX_AVAILABLE": "MAX_AVAILABLE",
    "PROVIDER_HISTORY_LIMIT": "PROVIDER_LIMITED",
}
AVAILABILITY_BY_BOUNDARY = {
    "MAX_AVAILABLE": "PASS",
    "PROVIDER_HISTORY_LIMIT": "PROVIDER_HISTORY_LIMIT",
}
SPOT_INTERVALS = {"5m", "15m", "1h", "4h", "1d", "1w"}
INTERVAL_MS = {"5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000, "1d": 86400000, "1w": 604800000}
CONTROL_FILENAMES = {"manifest.json", "release-manifest.json", "capability-index.json"}


def read_json(path: str | Path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def compact(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _status(value):
    return value.get("status") if isinstance(value, dict) else value


def _series_parts(source_provider: str, physical_series: str):
    if source_provider in {"binance", "kraken"} and physical_series in SPOT_INTERVALS:
        return "ohlcv", physical_series
    if physical_series.startswith("OHLCV-"):
        return "ohlcv", physical_series.split("-", 1)[1]
    if physical_series.startswith("DVOL-"):
        return "dvol", physical_series.split("-", 1)[1]
    return physical_series.lower(), None


def _series_id(domain: str, provider_id: str, instrument: str, series_name: str, interval: str | None):
    parts = [domain, provider_id, instrument, series_name]
    if interval:
        parts.append(interval)
    return ".".join(parts)


def _provider_policies():
    bridge = read_json("bridge-contract.json")
    source_contracts = read_json("contracts/provider-contracts.json")
    if source_contracts.get("schema_version") != "1.0.0" or not isinstance(source_contracts.get("contracts"), list):
        raise RuntimeError("provider endpoint contract shape mismatch")
    documented = {row.get("provider") for row in source_contracts["contracts"] if isinstance(row, dict)}
    if not {"binance", "kraken", "deribit"} <= documented:
        raise RuntimeError("provider endpoint contracts incomplete")

    policies = {}
    for provider_id, authority_role in bridge["active_providers"].items():
        domain = PROVIDER_DOMAIN.get(provider_id)
        if domain is None:
            raise RuntimeError(f"unclassified active provider: {provider_id}")
        policies[provider_id] = {
            "provider_id": provider_id,
            "domain": domain,
            "status": "ACTIVE",
            "authority_role": authority_role,
        }

    for provider_id, policy in bridge["disabled_providers"].items():
        domain = PROVIDER_DOMAIN.get(provider_id)
        if domain is None:
            raise RuntimeError(f"unclassified disabled provider: {provider_id}")
        row = {
            "provider_id": provider_id,
            "domain": domain,
            "status": policy["status"],
            "authority_role": policy["existing_archive"],
        }
        for key in (
            "current_collection",
            "network_calls",
            "signal_vote",
            "affects_health",
            "archive_continuously_accumulated",
            "archive_currently_updated",
            "historical_archive_preserved",
        ):
            if key in policy:
                row[key] = policy[key]
        policies[provider_id] = row

    if set(policies) != set(PROVIDER_DOMAIN):
        raise RuntimeError(
            "provider policy/domain registry mismatch: "
            f"missing={sorted(set(PROVIDER_DOMAIN) - set(policies))} "
            f"extra={sorted(set(policies) - set(PROVIDER_DOMAIN))}"
        )
    return policies


def _hot_routes():
    spot = read_json("history/manifest.json")
    kraken_futures = read_json("derivatives/history-manifest.json")
    deribit = read_json("derivatives/deribit-history-manifest.json")
    options = read_json("options/history-manifest.json")

    spot_keys = {(row["provider"], row["symbol"], row["interval"]) for row in spot.get("series", [])}
    kraken_keys = {
        (row["provider"], row["instrument"], row["metric"])
        for row in kraken_futures.get("series", [])
    }
    deribit_keys = {
        (row["provider"], row["instrument"], row["metric"])
        for row in deribit.get("series", [])
    }
    dvol_available = _status(options.get("deribit_dvol", {}).get("historical_backfill")) == "PASS"

    def resolve(source_provider: str, instrument: str, physical_series: str):
        if source_provider in {"binance", "kraken"}:
            return "history/manifest.json" if (source_provider, instrument, physical_series) in spot_keys else None
        if source_provider == "kraken-futures":
            return (
                "derivatives/history-manifest.json"
                if (source_provider, instrument, physical_series) in kraken_keys
                else None
            )
        if source_provider == "deribit-perpetual":
            return (
                "derivatives/deribit-history-manifest.json"
                if (source_provider, instrument, physical_series) in deribit_keys
                else None
            )
        if source_provider == "deribit-options" and physical_series == "DVOL-1h" and dvol_available:
            return "options/history-manifest.json"
        return None

    return resolve


def _profile_id(provider_id: str, series_name: str, history_mode: str, hot_manifest_path: str | None):
    semantic = series_name if provider_id.startswith("deribit") else "history"
    mode = history_mode.lower().replace("_", "-")
    tail = "hot" if hot_manifest_path else "cold-only"
    return f"{provider_id}.{semantic}.{mode}.{tail}"


def build_index():
    providers = _provider_policies()
    release = read_json("history/release-manifest.json")
    history = read_json("history/manifest.json")
    options_history = read_json("options/history-manifest.json")
    hot_route = _hot_routes()

    provider_policies = [providers[provider_id] for provider_id in sorted(providers)]

    profiles = {}
    series = []
    for item in release["series_inventory"]:
        source_provider = item["provider"]
        provider_id = RELEASE_PROVIDER_MAP.get(source_provider)
        if provider_id is None or provider_id not in providers:
            raise RuntimeError(f"unmapped release provider: {source_provider}")
        contract = providers[provider_id]
        if contract["status"] == "DISABLED_BY_POLICY":
            raise RuntimeError(f"disabled provider leaked into release inventory: {source_provider}")
        boundary = item["boundary_status"]
        if boundary not in DEPTH_MODE_BY_BOUNDARY:
            raise RuntimeError(f"unsupported release boundary: {boundary}")
        history_mode = DEPTH_MODE_BY_BOUNDARY[boundary]
        availability = AVAILABILITY_BY_BOUNDARY[boundary]
        series_name, interval = _series_parts(source_provider, item["interval_or_metric"])
        hot_manifest = hot_route(source_provider, item["instrument"], item["interval_or_metric"])
        profile_id = _profile_id(provider_id, series_name, history_mode, hot_manifest)
        profile = {
            "provider_id": provider_id,
            "source_provider": source_provider,
            "history_mode": history_mode,
            "availability_status": availability,
            "semantics_ref": "derivatives/metric-semantics.json" if source_provider == "kraken-futures" else None,
            "cold_manifest_path": "history/release-manifest.json",
            "release_tag": item["release_tag"],
            "hot_manifest_path": hot_manifest,
        }
        previous = profiles.get(profile_id)
        if previous is not None and previous != profile:
            raise RuntimeError(f"profile collision: {profile_id}")
        profiles[profile_id] = profile
        series.append(
            {
                "series_id": _series_id(
                    contract["domain"], provider_id, item["instrument"], series_name, interval
                ),
                "profile_id": profile_id,
                "instrument": item["instrument"],
                "series": series_name,
                "interval": interval,
                "source_interval_or_metric": item["interval_or_metric"],
            }
        )
    series.sort(key=lambda row: row["series_id"])
    profiles = {key: profiles[key] for key in sorted(profiles)}

    historical_availability = history.get("historical_availability")
    if not isinstance(historical_availability, dict):
        raise RuntimeError("history manifest historical_availability missing")
    forward_capabilities = [
        {
            "capability_id": "liquidity.orderbook-snapshots",
            "domain": "liquidity",
            "history_mode": "FORWARD_ONLY",
            "availability_status": _status(historical_availability.get("liquidity_forward_snapshot_archive")),
            "historical_backfill_status": _status(historical_availability.get("historical_orderbook")),
            "manifest_path": "liquidity/manifest.json",
        },
        {
            "capability_id": "options.deribit-options.ETH.surface-snapshots",
            "domain": "options",
            "history_mode": "FORWARD_ONLY",
            "availability_status": _status(options_history.get("options_forward_snapshot_archive")),
            "historical_backfill_status": _status(options_history.get("historical_option_surface")),
            "manifest_path": "options/manifest.json",
        },
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "catalog_id": CATALOG_ID,
        "generation_policy": "DETERMINISTIC_FROM_CANONICAL_MANIFESTS",
        "authority": {
            "route_policy": "bridge-contract.json",
            "provider_contracts": "contracts/provider-contracts.json",
            "cold_history_manifest": "history/release-manifest.json",
            "hot_history_manifests": [
                "history/manifest.json",
                "derivatives/history-manifest.json",
                "derivatives/deribit-history-manifest.json",
                "options/history-manifest.json",
            ],
        },
        "provider_policies": provider_policies,
        "profiles": profiles,
        "series": series,
        "forward_capabilities": forward_capabilities,
    }


def validate_shape(index):
    required_top = {
        "schema_version",
        "catalog_id",
        "generation_policy",
        "authority",
        "provider_policies",
        "profiles",
        "series",
        "forward_capabilities",
    }
    if set(index) != required_top:
        raise RuntimeError(f"capability index top-level mismatch: {sorted(set(index) ^ required_top)}")
    if index["schema_version"] != SCHEMA_VERSION or index["catalog_id"] != CATALOG_ID:
        raise RuntimeError("capability index identity mismatch")
    if index["generation_policy"] != "DETERMINISTIC_FROM_CANONICAL_MANIFESTS":
        raise RuntimeError("capability index generation policy mismatch")

    ids = [row["series_id"] for row in index["series"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise RuntimeError("series_id order/uniqueness failure")
    for row in index["series"]:
        if row["profile_id"] not in index["profiles"]:
            raise RuntimeError(f"missing profile: {row['series_id']}")

    allowed_modes = {"MAX_AVAILABLE", "PROVIDER_LIMITED", "FORWARD_ONLY", "FROZEN_REFERENCE", "UNAVAILABLE"}
    for profile_id, profile in index["profiles"].items():
        if profile["history_mode"] not in allowed_modes:
            raise RuntimeError(f"invalid history_mode: {profile_id}")
        if profile["cold_manifest_path"] != "history/release-manifest.json":
            raise RuntimeError(f"unexpected cold route: {profile_id}")
        if (
            profile["source_provider"] == "kraken-futures"
            and profile["semantics_ref"] != "derivatives/metric-semantics.json"
        ):
            raise RuntimeError(f"missing Kraken Futures semantics: {profile_id}")

    policies = {row["provider_id"]: row for row in index["provider_policies"]}
    disabled = policies.get("binance-usdm")
    if not disabled or disabled["status"] != "DISABLED_BY_POLICY":
        raise RuntimeError("Binance USDM disabled policy missing")
    if disabled.get("network_calls") != 0 or disabled.get("signal_vote") != "EXCLUDED":
        raise RuntimeError("Binance USDM disabled policy weakened")
    if any(index["profiles"][row["profile_id"]]["provider_id"] == "binance-usdm" for row in index["series"]):
        raise RuntimeError("disabled provider leaked into active series")

    forward_ids = [row["capability_id"] for row in index["forward_capabilities"]]
    if forward_ids != sorted(forward_ids):
        raise RuntimeError("forward capability order failure")


def validate_committed():
    expected = build_index()
    validate_shape(expected)
    committed = read_json("history/capability-index.json")
    validate_shape(committed)
    if compact(expected) != compact(committed):
        expected_ids = {row["series_id"] for row in expected["series"]}
        committed_ids = {row["series_id"] for row in committed["series"]}
        raise RuntimeError(
            "capability index is stale: "
            f"missing={sorted(expected_ids - committed_ids)[:10]} "
            f"extra={sorted(committed_ids - expected_ids)[:10]}"
        )

    schema = read_json("schema/capability-index.schema.json")
    expected_id = (
        "https://raw.githubusercontent.com/vitaliipython-ship-it/"
        "eth-macro-data-bridge/main/schema/capability-index.schema.json"
    )
    if schema.get("$id") != expected_id:
        raise RuntimeError("capability schema identity mismatch")
    if schema.get("properties", {}).get("schema_version", {}).get("const") != SCHEMA_VERSION:
        raise RuntimeError("capability schema version mismatch")

    print("CAPABILITY_INDEX_SCHEMA=PASS")
    print("CAPABILITY_INDEX_DETERMINISM=PASS")
    print(f"CAPABILITY_INDEX_SERIES={len(committed['series'])}")
    print(f"CAPABILITY_INDEX_PROFILES={len(committed['profiles'])}")
    print("CAPABILITY_INDEX_PROVIDER_POLICY=PASS")
    print("CAPABILITY_INDEX_NO_DISABLED_PROVIDER_SERIES=PASS")
    print("CAPABILITY_INDEX_VALIDATION=PASS")


def write_index():
    value = build_index()
    validate_shape(value)
    INDEX_PATH.write_bytes(compact(value))
    print(
        "CAPABILITY_INDEX_BUILD=PASS "
        f"path={INDEX_PATH.relative_to(ROOT).as_posix()} "
        f"series={len(value['series'])} profiles={len(value['profiles'])}"
    )


# D6.2A: discovery remains derived; physical resolution is manifest-driven and read-only.
def _committed_index():
    index = read_json("history/capability-index.json")
    validate_shape(index)
    return index


def _series_descriptor(index: dict, series_id: str):
    row = next((item for item in index["series"] if item["series_id"] == series_id), None)
    if row is None:
        raise RuntimeError(f"UNKNOWN_SERIES_ID: {series_id}")
    profile = index["profiles"][row["profile_id"]]
    policy = next(item for item in index["provider_policies"] if item["provider_id"] == profile["provider_id"])
    if policy["status"] != "ACTIVE":
        raise RuntimeError(f"PROVIDER_POLICY_CONFLICT: {profile['provider_id']}")
    return row, profile, policy


def list_capabilities():
    index = _committed_index()
    result = []
    for row in index["series"]:
        profile = index["profiles"][row["profile_id"]]
        result.append({
            **row,
            "provider_id": profile["provider_id"],
            "history_mode": profile["history_mode"],
            "availability_status": profile["availability_status"],
            "hot_manifest_path": profile["hot_manifest_path"],
            "cold_manifest_path": profile["cold_manifest_path"],
        })
    return result


def describe_capability(series_id: str):
    index = _committed_index()
    row, profile, policy = _series_descriptor(index, series_id)
    return {"series": row, "profile": profile, "provider_policy": policy}


def _parse_utc_ms(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"INVALID_UTC_TIMESTAMP: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeError(f"INVALID_UTC_TIMESTAMP: {value}")
    return int(parsed.timestamp() * 1000)


def _generated_at_ms(manifest: dict) -> int | None:
    value = manifest.get("generated_at_utc") or manifest.get("backfill_as_of_utc")
    return _parse_utc_ms(value) if value else None


def _payload_key(payload: dict):
    return (
        payload.get("provider"),
        payload.get("symbol") or payload.get("instrument"),
        payload.get("interval") or payload.get("metric") or payload.get("interval_or_metric"),
    )


def _manifest_declares(manifest: dict, source_provider: str, instrument: str, physical_series: str) -> bool:
    for item in manifest.get("series", []):
        key = (
            item.get("provider"),
            item.get("symbol") or item.get("instrument"),
            item.get("interval") or item.get("metric") or item.get("interval_or_metric"),
        )
        if key == (source_provider, instrument, physical_series):
            return True
    if source_provider == "deribit-options" and physical_series == "DVOL-1h":
        return _status(manifest.get("deribit_dvol", {}).get("historical_backfill")) == "PASS"
    return False


def _derived_warm_catalog(profile: dict, row: dict, cutoff_ms: int | None):
    manifest_path = profile.get("hot_manifest_path")
    if not manifest_path:
        return []
    manifest = read_json(manifest_path)
    if cutoff_ms is not None:
        generated = _generated_at_ms(manifest)
        if generated is None or generated > cutoff_ms:
            return []
    source_provider = profile["source_provider"]
    instrument = row["instrument"]
    physical_series = row["source_interval_or_metric"]
    if not _manifest_declares(manifest, source_provider, instrument, physical_series):
        raise RuntimeError(f"HOT_MANIFEST_SERIES_MISMATCH: {row['series_id']}")

    # Catalog is a runtime projection over physically present declared resources. Paths are discovered,
    # never synthesized from year/month/day naming conventions.
    base = (ROOT / manifest_path).parent
    catalog = []
    for path in sorted(base.rglob("*.json")):
        if path.name in CONTROL_FILENAMES or path == ROOT / manifest_path:
            continue
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            continue
        if _payload_key(payload) != (source_provider, instrument, physical_series):
            continue
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            continue
        timestamps = [item[0] for item in records if isinstance(item, list) and item and isinstance(item[0], int)]
        if len(timestamps) != len(records) or timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise RuntimeError(f"WARM_RESOURCE_INTEGRITY: {path.relative_to(ROOT).as_posix()}")
        catalog.append({
            "resource_path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "first_timestamp": timestamps[0],
            "last_timestamp": timestamps[-1],
        })
    return catalog


def _cold_catalog(profile: dict, row: dict, cutoff_ms: int | None):
    release = read_json(profile["cold_manifest_path"])
    if release.get("storage_backend") != "GITHUB_RELEASE_ASSET":
        raise RuntimeError("COLD_STORAGE_BACKEND_MISMATCH")
    if cutoff_ms is not None:
        generated = _generated_at_ms(release)
        if generated is None or generated > cutoff_ms:
            return [], release
    wanted = (profile["source_provider"], row["instrument"], row["source_interval_or_metric"])
    assets = []
    for asset in release.get("asset_inventory", []):
        if (asset.get("provider"), asset.get("instrument"), asset.get("interval_or_metric")) != wanted:
            continue
        if asset.get("release_tag") != profile["release_tag"]:
            raise RuntimeError(f"RELEASE_TAG_MISMATCH: {asset.get('asset_name')}")
        required = ("asset_id", "asset_name", "browser_download_url", "sha256", "size_bytes", "first_timestamp", "last_timestamp")
        if any(asset.get(key) is None for key in required):
            raise RuntimeError(f"ASSET_AUTHORITY_INCOMPLETE: {asset.get('asset_name')}")
        if asset.get("integrity_status") != "PASS" or asset.get("immutable") is not True:
            raise RuntimeError(f"ASSET_NOT_IMMUTABLE_VERIFIED: {asset.get('asset_name')}")
        assets.append(asset)
    assets.sort(key=lambda item: (item["first_timestamp"], item["last_timestamp"], item["asset_name"]))
    return assets, release


def _interval_ms(row: dict, profile: dict) -> int | None:
    if row["interval"] in INTERVAL_MS:
        return INTERVAL_MS[row["interval"]]
    if profile["source_provider"] == "kraken-futures":
        return 300000
    return None


def _coverage_check(segments: list[dict], start_ms: int, end_ms: int):
    ranges = sorted((item["read_start_ms"], item["read_end_ms"]) for item in segments)
    cursor = start_ms
    for left, right in ranges:
        if right <= cursor:
            continue
        if left > cursor:
            raise RuntimeError(f"UNRESOLVED_SEGMENT_GAP: {cursor}->{left}")
        cursor = max(cursor, right)
        if cursor >= end_ms:
            return
    if cursor < end_ms:
        raise RuntimeError(f"HISTORY_NOT_FOUND: uncovered {cursor}->{end_ms}")


def resolve_capability(series_id: str, start_utc: str, end_utc: str, cutoff_utc: str | None = None):
    index = _committed_index()
    row, profile, policy = _series_descriptor(index, series_id)
    start_ms = _parse_utc_ms(start_utc)
    end_ms = _parse_utc_ms(end_utc)
    cutoff_ms = _parse_utc_ms(cutoff_utc) if cutoff_utc else None
    if start_ms >= end_ms:
        raise RuntimeError("INVALID_TIME_RANGE")
    if cutoff_ms is not None and end_ms > cutoff_ms:
        raise RuntimeError("POINT_IN_TIME_RANGE_EXCEEDS_CUTOFF")

    step = _interval_ms(row, profile)
    if row["series"] == "ohlcv":
        if step is None:
            raise RuntimeError(f"UNSUPPORTED_INTERVAL: {row['interval']}")
        alignment = min(step, 86400000)
        if start_ms % alignment or end_ms % alignment:
            raise RuntimeError("UNALIGNED_OHLCV_RANGE")

    cold_assets, release = _cold_catalog(profile, row, cutoff_ms)
    cold_segments = []
    cold_last = None
    for asset in cold_assets:
        physical_end = asset["last_timestamp"] + (step or 1)
        left = max(start_ms, asset["first_timestamp"])
        right = min(end_ms, physical_end)
        if left >= right:
            continue
        cold_last = max(cold_last or asset["last_timestamp"], asset["last_timestamp"])
        cold_segments.append({
            "segment_id": f"cold:{asset['release_tag']}:{asset['asset_id']}",
            "storage": "GITHUB_RELEASE_ASSET",
            "source_manifest_path": profile["cold_manifest_path"],
            "release_tag": asset["release_tag"],
            "asset_id": asset["asset_id"],
            "asset_name": asset["asset_name"],
            "browser_download_url": asset["browser_download_url"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
            "immutable": True,
            "first_timestamp_ms": asset["first_timestamp"],
            "last_timestamp_ms": asset["last_timestamp"],
            "read_start_ms": left,
            "read_end_ms": right,
            "source_provider": profile["source_provider"],
            "instrument": row["instrument"],
            "source_interval_or_metric": row["source_interval_or_metric"],
        })

    cold_coverage_end = min(end_ms, (cold_last + (step or 1))) if cold_last is not None else start_ms
    warm_segments = []
    for resource in _derived_warm_catalog(profile, row, cutoff_ms):
        physical_end = resource["last_timestamp"] + (step or 1)
        left = max(start_ms, cold_coverage_end, resource["first_timestamp"])
        right = min(end_ms, physical_end)
        if left >= right:
            continue
        warm_segments.append({
            "segment_id": f"warm:{resource['sha256'][:16]}:{resource['resource_path']}",
            "storage": "GIT_WARM_RESOURCE",
            "source_manifest_path": profile["hot_manifest_path"],
            "resource_path": resource["resource_path"],
            "sha256": resource["sha256"],
            "size_bytes": resource["size_bytes"],
            "first_timestamp_ms": resource["first_timestamp"],
            "last_timestamp_ms": resource["last_timestamp"],
            "read_start_ms": left,
            "read_end_ms": right,
            "source_provider": profile["source_provider"],
            "instrument": row["instrument"],
            "source_interval_or_metric": row["source_interval_or_metric"],
        })

    segments = sorted(
        cold_segments + warm_segments,
        key=lambda item: (item["read_start_ms"], item["read_end_ms"], item["storage"], item["segment_id"]),
    )
    _coverage_check(segments, start_ms, end_ms)

    authority = {
        "route_policy": index["authority"]["route_policy"],
        "capability_index": "history/capability-index.json",
        "cold_manifest": profile["cold_manifest_path"],
        "hot_manifest": profile["hot_manifest_path"],
    }
    plan = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": authority,
        "request": {
            "series_id": series_id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "cutoff_ms": cutoff_ms,
        },
        "series": {
            **row,
            "provider_id": profile["provider_id"],
            "source_provider": profile["source_provider"],
            "history_mode": profile["history_mode"],
            "availability_status": profile["availability_status"],
            "interval_ms": step,
        },
        "segments": segments,
    }
    plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
    return plan


def _print_json(value):
    sys.stdout.buffer.write(compact(value))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic market-data capability index and D6.2A resolver")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("validate")
    sub.add_parser("list")
    describe = sub.add_parser("describe")
    describe.add_argument("series_id")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("series_id")
    resolve.add_argument("--from", dest="start_utc", required=True)
    resolve.add_argument("--to", dest="end_utc", required=True)
    resolve.add_argument("--cutoff", dest="cutoff_utc")
    resolve.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args(argv)
    if args.command == "build":
        write_index()
    elif args.command == "validate":
        validate_committed()
    elif args.command == "list":
        _print_json(list_capabilities())
    elif args.command == "describe":
        _print_json(describe_capability(args.series_id))
    else:
        _print_json(resolve_capability(args.series_id, args.start_utc, args.end_utc, args.cutoff_utc))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CAPABILITY_INDEX=FAIL error={exc}", file=sys.stderr)
        raise
