from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import history_access_v2
import resolution_v2

EXPECTED_SAMPLED = {
    "options.deribit-options.ETH.surface-snapshots",
    "liquidity.orderbook-snapshots",
    "derivatives.deribit-perpetual.current-snapshot",
}


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def iso(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    bridge = read_json("bridge-contract.json")
    semantic = bridge.get("semantic_resolution", {})
    if semantic.get("status") != "ACTIVE":
        fail("active semantic route missing")
    if semantic.get("resolver", {}).get("interface") != "tools/capability_index.py":
        fail("canonical resolver interface changed")
    if semantic.get("reader", {}).get("interface") != "tools/history_access.py":
        fail("canonical reader interface changed")
    if semantic.get("resolver", {}).get("resolution_plan_schema") != "market-data-resolution-plan/1.0.0":
        fail("D6 active ResolutionPlan version changed")
    if bridge.get("d9_candidate", {}).get("successor_route", {}).get("second_resolver") is not False:
        fail("second resolver contract weakened")
    if bridge.get("d9_candidate", {}).get("successor_route", {}).get("second_reader_family") is not False:
        fail("second reader family contract weakened")
    print("D9_4_ACTIVE_ROUTE_UNCHANGED=PASS")

    if (ROOT / "history/capability-index-v2.json").exists():
        fail("second committed capability catalog detected")
    base = read_json("history/capability-index.json")
    first = resolution_v2.build_index_v2(ROOT)
    second = resolution_v2.build_index_v2(ROOT)
    if resolution_v2.compact(first) != resolution_v2.compact(second):
        fail("v2 runtime projection is not deterministic")
    base_ids = {row["series_id"] for row in base["series"]}
    v2_ids = {row["series_id"] for row in first["series"]}
    if not base_ids <= v2_ids:
        fail("v2 projection lost active v1 series")
    if not EXPECTED_SAMPLED <= v2_ids:
        fail(f"v2 sampled capability set incomplete: {sorted(EXPECTED_SAMPLED - v2_ids)}")
    print("D9_4_RUNTIME_PROJECTION=PASS")
    print("D9_4_NO_SECOND_CATALOG=PASS")
    print(f"D9_4_V1_SERIES_PRESERVED={len(base_ids)}")
    print(f"D9_4_V2_SERIES={len(v2_ids)}")

    by_id = {row["series_id"]: row for row in first["series"]}
    spreads = by_id["derivatives.kraken-futures.PI_ETHUSD.spreads"]
    oi = by_id["derivatives.kraken-futures.PI_ETHUSD.open-interest"]
    spreads_profile = first["profiles"][spreads["profile_id"]]
    oi_profile = first["profiles"][oi["profile_id"]]
    if spreads["profile_id"] == oi["profile_id"]:
        fail("Kraken metric-specific v2 profiles collapsed")
    if spreads_profile.get("revision_policy") != "PROVIDER_REVISABLE_SNAPSHOT":
        fail("Kraken revisable policy lost")
    if oi_profile.get("revision_policy") != "STRICT_OVERLAP_REQUIRED":
        fail("Kraken strict overlap policy lost")
    print("D9_4_KRAKEN_REVISION_POLICY=PASS")

    sealing = read_json("contracts/d9-sealing-candidate.json")
    high_card = sealing.get("high_cardinality_warm", {})
    if high_card.get("cold_sealing_enabled") is not False:
        fail("high-cardinality COLD sealing unexpectedly active")
    if not str(high_card.get("status", "")).startswith("BLOCKED_"):
        fail("high-cardinality Release-WARM blocker disappeared without qualification")
    if high_card.get("mutable_in_place") is not False:
        fail("unqualified mutable prerelease authority was claimed")
    print("D9_4_HIGH_CARD_RELEASE_WARM_NOT_ACTIVE=PASS")

    v1_result = subprocess.run(
        [
            sys.executable,
            "tools/capability_index.py",
            "resolve",
            "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "--from", "2022-06-18T00:00:00Z",
            "--to", "2022-06-19T00:00:00Z",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if json.loads(v1_result.stdout).get("schema_version") != "market-data-resolution-plan/1.0.0":
        fail("canonical resolver default stopped producing v1")
    print("D9_4_V1_DEFAULT_COMPATIBILITY=PASS")

    ledger = resolution_v2._ledger_rows(ROOT)
    sampled = next(
        row for row in reversed(ledger)
        if row["series_or_capability"] == "options.deribit-options.ETH.surface-snapshots"
        and row["status"] == "OBSERVED_STATE"
    )
    start = sampled["expected_schedule_at_ms"]
    v2_result = subprocess.run(
        [
            sys.executable,
            "tools/capability_index.py",
            "resolve",
            "options.deribit-options.ETH.surface-snapshots",
            "--from", iso(start),
            "--to", iso(start + 1000),
            "--plan-version", "2",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(v2_result.stdout)
    if plan.get("schema_version") != "market-data-resolution-plan/2.0.0":
        fail("explicit v2 resolver did not produce v2 plan")
    if plan.get("authority", {}).get("d9_activation_status") != "CANDIDATE_NOT_ACTIVE":
        fail("v2 plan claimed D9 activation")
    if plan.get("series", {}).get("coverage_semantics") != "SAMPLED_SCHEDULE":
        fail("sampled series lost sampled coverage semantics")
    with tempfile.TemporaryDirectory() as td:
        rows, diagnostics = history_access_v2.materialize_resolution_plan_v2(
            plan,
            root=ROOT,
            cache_dir=Path(td) / "cache",
        )
    if len(rows) != 1 or diagnostics.get("status") != "PASS":
        fail("real sampled ledger resolution/read failed")
    if diagnostics.get("receipt", {}).get("observation_count") != 1:
        fail("v2 receipt observation count mismatch")
    print("D9_4_PUBLIC_V2_ROUTE=PASS")
    print("D9_4_SAMPLED_LEDGER_RESOLUTION=PASS")
    print("D9_4_RECEIPT=PASS")

    if any(segment.get("storage") == "HOT_CURRENT_RESOURCE" for segment in plan["segments"]):
        fail("default finalized sampled plan unexpectedly used HOT")
    print("D9_4_NO_PROVIDER_FALLBACK=PASS")
    print("D9_4_VALIDATION=PASS")


if __name__ == "__main__":
    main()
