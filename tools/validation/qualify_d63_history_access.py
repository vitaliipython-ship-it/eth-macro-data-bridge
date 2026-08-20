from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from tools.capability_index import describe_capability, resolve_capability
from tools.history_access import materialize_resolution_plan

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "d63-history-access-live-cache"
RELEASE_PATH = ROOT / "history" / "release-manifest.json"
INDEX_PATH = ROOT / "history" / "capability-index.json"
HISTORY_MANIFEST_PATH = ROOT / "history" / "manifest.json"

BINANCE_M5 = "spot.binance-spot.ETHUSDT.ohlcv.5m"
BINANCE_H1 = "spot.binance-spot.ETHUSDT.ohlcv.1h"
BINANCE_H4 = "spot.binance-spot.ETHUSDT.ohlcv.4h"
KRAKEN_SPOT_H1 = "spot.kraken-spot.ETHUSD.ohlcv.1h"
DERIBIT_PERP_H1 = "derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h"
KRAKEN_FUNDING = "derivatives.kraken-futures.PI_ETHUSD.funding"
KRAKEN_OI = "derivatives.kraken-futures.PI_ETHUSD.open-interest"
DERIBIT_DVOL = "options.deribit-options.ETH.dvol.1h"

M5 = 300000
H1 = 3600000
H4 = 14400000
KNOWN_BINANCE_SPOT_H1_HALT_GAPS = {1679662800000}  # 2023-03-24T13:00:00Z


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def release_assets(series_id: str) -> list[dict]:
    descriptor = describe_capability(series_id)
    row = descriptor["series"]
    profile = descriptor["profile"]
    wanted = (profile["source_provider"], row["instrument"], row["source_interval_or_metric"])
    release = read_json(RELEASE_PATH)
    assets = [
        item
        for item in release["asset_inventory"]
        if (item.get("provider"), item.get("instrument"), item.get("interval_or_metric")) == wanted
    ]
    assert assets, f"no release assets for {series_id}"
    return sorted(assets, key=lambda item: (item["first_timestamp"], item["last_timestamp"], item["asset_name"]))


def assert_manifest_driven(plan: dict) -> None:
    release = read_json(RELEASE_PATH)
    by_id = {item["asset_id"]: item for item in release["asset_inventory"]}
    for segment in plan["segments"]:
        if segment["storage"] == "GITHUB_RELEASE_ASSET":
            authority = by_id[segment["asset_id"]]
            assert segment["source_manifest_path"] == "history/release-manifest.json"
            assert segment["asset_name"] == authority["asset_name"]
            assert segment["release_tag"] == authority["release_tag"]
            assert segment["browser_download_url"] == authority["browser_download_url"]
            assert segment["sha256"] == authority["sha256"]
            assert segment["size_bytes"] == authority["size_bytes"]
        else:
            path = ROOT / segment["resource_path"]
            assert path.is_file()
            raw = path.read_bytes()
            import hashlib
            assert hashlib.sha256(raw).hexdigest() == segment["sha256"]
            assert len(raw) == segment["size_bytes"]


def qualify_slice(series_id: str, start: str, end: str, *, mode: str = "strict") -> tuple[list, dict, dict]:
    plan = resolve_capability(series_id, start, end)
    assert_manifest_driven(plan)
    rows, diagnostics = materialize_resolution_plan(plan, cache_dir=CACHE, mode=mode)
    assert diagnostics["duplicates"] == 0
    assert diagnostics["rows"] == len(rows)
    if mode == "strict":
        assert diagnostics["status"] == "PASS"
        assert diagnostics["gap_count"] == 0
        assert diagnostics["rows"] == diagnostics["expected_rows"]
    else:
        assert diagnostics["rows"] + diagnostics["gap_count"] == diagnostics["expected_rows"]
        expected_status = "DEGRADED" if diagnostics["gap_count"] else "PASS"
        assert diagnostics["status"] == expected_status
    return rows, diagnostics, plan


def first_asset_range(series_id: str, step_ms: int) -> tuple[str, str]:
    asset = release_assets(series_id)[0]
    start = asset["first_timestamp"]
    end = min(asset["last_timestamp"] + step_ms, start + step_ms)
    assert end > start
    return iso(start), iso(end)


def qualify_resolver_only(series_id: str, step_ms: int = M5) -> dict:
    start, end = first_asset_range(series_id, step_ms)
    plan = resolve_capability(series_id, start, end)
    assert plan["segments"]
    assert_manifest_driven(plan)
    return plan


def aggregate(rows: list[tuple], target_ms: int) -> dict[int, tuple[Decimal, Decimal, Decimal, Decimal, Decimal]]:
    groups: dict[int, list[tuple]] = defaultdict(list)
    for row in rows:
        groups[(row[0] // target_ms) * target_ms].append(row)
    result = {}
    expected_members = target_ms // M5
    for bucket, members in sorted(groups.items()):
        members.sort(key=lambda row: row[0])
        assert len(members) == expected_members
        values = [(Decimal(row[1]), Decimal(row[2]), Decimal(row[3]), Decimal(row[4]), Decimal(row[5])) for row in members]
        result[bucket] = (
            values[0][0],
            max(value[1] for value in values),
            min(value[2] for value in values),
            values[-1][3],
            sum((value[4] for value in values), Decimal(0)),
        )
    return result


def native(rows: list[tuple]) -> dict[int, tuple[Decimal, Decimal, Decimal, Decimal, Decimal]]:
    return {
        row[0]: tuple(Decimal(value) for value in row[1:6])
        for row in rows
    }


def qualify_cross_timeframe() -> None:
    start = "2024-03-11T00:00:00Z"
    end = "2024-03-13T00:00:00Z"
    m5, _, _ = qualify_slice(BINANCE_M5, start, end)
    h1, _, _ = qualify_slice(BINANCE_H1, start, end)
    h4, _, _ = qualify_slice(BINANCE_H4, start, end)
    assert aggregate(m5, H1) == native(h1)
    assert aggregate(m5, H4) == native(h4)
    print("D63_M5_TO_H1=PASS")
    print("D63_M5_TO_H4=PASS")
    print("D63_CROSS_TIMEFRAME_WINDOW=" + start + ".." + end)


def qualify_physical_seam() -> None:
    release = read_json(RELEASE_PATH)
    cold = [
        item for item in release["asset_inventory"]
        if (item.get("provider"), item.get("instrument"), item.get("interval_or_metric")) == ("binance", "ETHUSDT", "5m")
    ]
    assert cold
    cold_last = max(item["last_timestamp"] for item in cold)

    history = read_json(HISTORY_MANIFEST_PATH)
    series = next(
        item for item in history["series"]
        if (item["provider"], item["symbol"], item["interval"]) == ("binance", "ETHUSDT", "5m")
    )
    warm_root = ROOT / "history" / series["provider"] / series["symbol"] / series["interval"]
    assert warm_root.is_dir()

    candidates = []
    for warm_path in sorted(warm_root.rglob("*.json")):
        warm = read_json(warm_path)
        columns = warm.get("columns")
        records = warm.get("records")
        if not isinstance(columns, list) or not isinstance(records, list) or not records:
            continue
        required = ("open_time_ms", "open", "high", "low", "close", "base_volume")
        if any(name not in columns for name in required):
            continue
        p = {name: columns.index(name) for name in required}
        warm_rows = {
            row[p["open_time_ms"]]: (
                str(row[p["open"]]), str(row[p["high"]]), str(row[p["low"]]), str(row[p["close"]]), str(row[p["base_volume"]])
            )
            for row in records
            if isinstance(row, list) and len(row) > max(p.values()) and isinstance(row[p["open_time_ms"]], int)
        }
        if not warm_rows:
            continue
        overlap_end = min(cold_last + M5, max(warm_rows) + M5)
        overlap_start = max(min(warm_rows), overlap_end - 12 * M5)
        if overlap_start < overlap_end:
            candidates.append((max(warm_rows), warm_path.as_posix(), warm_rows, overlap_start, overlap_end))

    assert candidates, "no committed WARM partition overlaps immutable COLD seam"
    _, selected_path, warm_rows, overlap_start, overlap_end = max(candidates, key=lambda item: (item[0], item[1]))

    rows, diagnostics, plan = qualify_slice(BINANCE_M5, iso(overlap_start), iso(overlap_end))
    assert all(segment["storage"] == "GITHUB_RELEASE_ASSET" for segment in plan["segments"])
    matched = 0
    for row in rows:
        candidate = warm_rows.get(row[0])
        if candidate is not None:
            assert tuple(row[1:6]) == candidate
            matched += 1
    assert matched > 0
    assert diagnostics["duplicates"] == 0 and diagnostics["gap_count"] == 0
    print("D63_PHYSICAL_SEAM_MODE=COLD_PRECEDENCE_OVER_VERIFIED_OVERLAP")
    print("D63_PHYSICAL_SEAM_WARM_PARTITION=" + selected_path)
    print("D63_PHYSICAL_SEAM_MATCHED_ROWS=" + str(matched))
    print("CAPABILITY_COLD_HOT_SEAM=PASS")

def qualify_priority_acceptance() -> None:
    start = "2022-06-01T00:00:00Z"
    end = "2025-09-15T00:00:00Z"

    # A: native 4h is complete across the requested multi-year range.
    rows, diagnostics, _ = qualify_slice(BINANCE_H4, start, end)
    assert rows and diagnostics["status"] == "PASS"
    print("D63_PRIORITY_FULL_RANGE=PASS series_id=" + BINANCE_H4 + " rows=" + str(len(rows)))

    # B: strict mode intentionally fails on a real no-trading interval from the 2023-03-24 Binance Spot outage.
    # D6.3 therefore qualifies the same full range in permissive mode and allows only that evidenced provider-native gap.
    rows, diagnostics, _ = qualify_slice(BINANCE_H1, start, end, mode="permissive")
    missing = set(diagnostics["missing_intervals_ms"])
    assert missing == KNOWN_BINANCE_SPOT_H1_HALT_GAPS
    assert diagnostics["status"] == "DEGRADED" and diagnostics["gap_count"] == 1
    print("D63_PRIORITY_FULL_RANGE=DEGRADED_EXPECTED_PROVIDER_HALT series_id=" + BINANCE_H1 + " rows=" + str(len(rows)))
    print("D63_PROVIDER_NATIVE_HALT_DIAGNOSTIC=PASS missing=" + ",".join(iso(item) for item in sorted(missing)))

    # C was already independently qualified in D6.2; repeat under the final D6.3 contour.
    rows, _, _ = qualify_slice(BINANCE_M5, "2022-06-18T00:00:00Z", "2022-11-10T00:00:00Z")
    assert len(rows) == 41760
    print("D63_PRIORITY_C_2022_M5=PASS rows=41760")

    # D: all four key pivot windows, two UTC days each.
    windows = (
        ("2024-03-11T00:00:00Z", "2024-03-13T00:00:00Z"),
        ("2024-12-15T00:00:00Z", "2024-12-17T00:00:00Z"),
        ("2025-04-08T00:00:00Z", "2025-04-10T00:00:00Z"),
        ("2025-08-23T00:00:00Z", "2025-08-25T00:00:00Z"),
    )
    for pivot_start, pivot_end in windows:
        rows, pivot_diagnostics, _ = qualify_slice(BINANCE_M5, pivot_start, pivot_end)
        assert len(rows) == 576 and pivot_diagnostics["status"] == "PASS"
        print("D63_PRIORITY_PIVOT_WINDOW=PASS range=" + pivot_start + ".." + pivot_end + " rows=576")


def qualify_capability_contract() -> None:
    index = read_json(INDEX_PATH)
    release = read_json(RELEASE_PATH)
    ids = [item["series_id"] for item in index["series"]]
    assert len(ids) == len(set(ids)) and ids == sorted(ids)

    index_keys = {
        (
            index["profiles"][item["profile_id"]]["source_provider"],
            item["instrument"],
            item["source_interval_or_metric"],
        )
        for item in index["series"]
    }
    release_keys = {
        (item["provider"], item["instrument"], item["interval_or_metric"])
        for item in release["series_inventory"]
    }
    assert index_keys == release_keys

    policies = {item["provider_id"]: item for item in index["provider_policies"]}
    disabled = policies["binance-usdm"]
    assert disabled["status"] == "DISABLED_BY_POLICY"
    assert disabled["network_calls"] == 0 and disabled["signal_vote"] == "EXCLUDED"
    assert all(index["profiles"][item["profile_id"]]["provider_id"] != "binance-usdm" for item in index["series"])

    forward = {item["capability_id"]: item for item in index["forward_capabilities"]}
    assert forward["liquidity.orderbook-snapshots"]["history_mode"] == "FORWARD_ONLY"
    assert forward["options.deribit-options.ETH.surface-snapshots"]["history_mode"] == "FORWARD_ONLY"
    assert not any("surface-snapshots" in item["series_id"] or "orderbook-snapshots" in item["series_id"] for item in index["series"])

    for profile_id, profile in index["profiles"].items():
        if profile["source_provider"] in {"kraken", "kraken-futures"}:
            assert profile["history_mode"] == "PROVIDER_LIMITED", profile_id

    update_workflow = (ROOT / ".github" / "workflows" / "update-market.yml").read_text(encoding="utf-8")
    assert "capability_index.py" not in update_workflow

    plan = qualify_resolver_only(KRAKEN_FUNDING)
    assert plan["series"]["history_mode"] == "PROVIDER_LIMITED"
    qualify_resolver_only(KRAKEN_OI)
    qualify_resolver_only(DERIBIT_DVOL, H1)

    try:
        resolve_capability(BINANCE_M5, "2022-06-18T00:00:00Z", "2022-06-18T01:00:00Z", "2026-08-15T10:59:59Z")
    except RuntimeError as exc:
        assert "HISTORY_NOT_FOUND" in str(exc) or "UNRESOLVED_SEGMENT_GAP" in str(exc)
    else:
        raise AssertionError("point-in-time resolver admitted future-known COLD evidence")

    print("CAPABILITY_SERIES_ID_UNIQUE=PASS")
    print("CAPABILITY_SOURCE_COVERAGE=PASS")
    print("CAPABILITY_NO_ORPHANS=PASS")
    print("CAPABILITY_PHYSICAL_RESOLUTION=PASS")
    print("CAPABILITY_NO_GUESSED_PATHS=PASS")
    print("CAPABILITY_POINT_IN_TIME_CUTOFF=PASS")
    print("D63_FORWARD_ONLY_SEMANTICS=PASS")
    print("D63_BINANCE_USDM_DISABLED_SEMANTICS=PASS")
    print("D63_PROVIDER_LIMITED_SEMANTICS=PASS")
    print("D63_HOURLY_INDEX_REGENERATION_REQUIRED=false")
    print("D63_REPRESENTATIVE_RESOLUTION=PASS providers=binance-spot,kraken-futures,deribit-options")


def qualify_multi_provider_reader() -> None:
    for series_id, step in ((KRAKEN_SPOT_H1, H1), (DERIBIT_PERP_H1, H1)):
        start, end = first_asset_range(series_id, step)
        rows, diagnostics, _ = qualify_slice(series_id, start, end)
        assert len(rows) == 1 and diagnostics["status"] == "PASS"
        print("D63_MULTI_PROVIDER_READER=PASS series_id=" + series_id)


def main() -> None:
    qualify_capability_contract()
    qualify_priority_acceptance()
    qualify_cross_timeframe()
    qualify_physical_seam()
    qualify_multi_provider_reader()
    print("CAPABILITY_CONSUMER_PROOF=PASS")
    print("D63_RESOLVER_CONSUMER_QUALIFICATION=PASS")


if __name__ == "__main__":
    main()
