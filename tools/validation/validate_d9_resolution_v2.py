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


def _actual_g2a_successor_observation() -> dict:
    base = ROOT / "history/liquidity-orderbook-snapshots"
    for path in sorted(base.rglob("observations.json"), reverse=True):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != resolution_v2.G2B_PARTITION_SCHEMA:
            continue
        for observation in payload.get("observations", []):
            if not isinstance(observation, dict):
                continue
            try:
                history_access_v2._validate_g2b_observation(observation)
            except history_access_v2.HistoryAccessV2Error:
                continue
            return observation
    fail("no valid owner-integrated G2-A successor observation is readable")


def _validate_g2b_candidate() -> None:
    bridge = read_json("bridge-contract.json")
    binding = resolution_v2._g2b_contract_binding(ROOT)
    contract = read_json(resolution_v2.G2B_CONTRACT_PATH)

    if contract.get("family", {}).get("family_id") != resolution_v2.G2B_FAMILY:
        fail("G2-B canonical history family changed")
    if contract.get("family", {}).get("new_parallel_deep_history_family") is not False:
        fail("G2-B parallel history family permitted")
    reuse = contract.get("authority_reuse", {})
    if reuse.get("second_history_reader") is not False:
        fail("G2-B second history reader permitted")
    if reuse.get("second_capability_catalog") is not False:
        fail("G2-B second capability catalog permitted")
    if reuse.get("second_temporal_authority") is not False:
        fail("G2-B second temporal authority permitted")
    if bridge.get("semantic_resolution", {}).get("reader", {}).get("interface") != "tools/history_access.py":
        fail("G2-B public reader reuse lost")
    if bridge.get("semantic_resolution", {}).get("resolver", {}).get("interface") != "tools/capability_index.py":
        fail("G2-B public capability resolver reuse lost")
    if (ROOT / "history/capability-index-v2.json").exists():
        fail("G2-B second committed capability catalog detected")
    print("G2B_ONE_HISTORY_FAMILY=PASS")
    print("G2B_PUBLIC_READER_REUSE=PASS")
    print("G2B_CAPABILITY_RESOLVER_REUSE=PASS")
    print("G2B_SECOND_READER_ABSENT=PASS")
    print("G2B_SECOND_CATALOG_ABSENT=PASS")
    print("G2B_SECOND_TEMPORAL_AUTHORITY_ABSENT=PASS")

    observation = _actual_g2a_successor_observation()
    timestamp = observation["observation_time_ms"]
    known_at = history_access_v2._parse_utc_ms(observation["known_at_utc"])
    plan = resolution_v2.resolve_capability_v2(
        resolution_v2.G2B_FAMILY,
        iso(timestamp),
        iso(timestamp + 1),
        cutoff_utc=iso(known_at),
        root=ROOT,
    )
    successor_segments = [
        segment for segment in plan["segments"]
        if segment.get("schema_class") == resolution_v2.G2B_SUCCESSOR_CLASS
    ]
    if not successor_segments:
        fail("owner-integrated G2-A successor did not resolve through G2-B")
    if any(segment.get("schema_binding") != binding for segment in successor_segments):
        fail("G2-B successor segment lost durable contract binding")
    if any(segment.get("storage") != "GIT_WARM_RESOURCE" for segment in successor_segments):
        fail("G2-B successor escaped declared durable repository resources")
    if any(segment.get("storage") == "HOT_CURRENT_RESOURCE" for segment in plan["segments"]):
        fail("G2-B substituted current data into durable history")
    print("G2B_SUCCESSOR_SCHEMA_BINDING=PASS")
    print("G2B_NO_PROVIDER_FALLBACK=PASS")
    print("G2B_NO_CURRENT_DATA_SUBSTITUTION=PASS")

    excluded, _ = resolution_v2._g2b_successor_segments(
        ROOT,
        timestamp,
        timestamp + 1,
        known_at - 1,
    )
    if excluded:
        fail("G2-B PIT resolver exposed observation after cutoff")
    forged = json.loads(json.dumps(plan))
    successor = next(
        segment for segment in forged["segments"]
        if segment.get("schema_class") == resolution_v2.G2B_SUCCESSOR_CLASS
    )
    successor["successor_observations"][0]["known_at_ms"] = known_at + 1
    forged["plan_sha256"] = history_access_v2._plan_digest(forged)
    try:
        history_access_v2.validate_resolution_plan_v2(forged)
    except history_access_v2.HistoryAccessV2Error as exc:
        if exc.code != "G2B_KNOWN_AT_AFTER_CUTOFF":
            raise
    else:
        fail("G2-B forged future observation did not fail closed")
    print("G2B_PIT_POLICY=PASS")
    print("G2B_NO_LOOKAHEAD=PASS")

    if len(resolution_v2._g2b_day_paths(binding, 1704067200000, 1704067200000 + 371 * 86400000)) != 371:
        fail("G2-B arbitrary history horizon still present")

    suite = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.deep_history.test_d9_public_resolution_v2.G2BReaderSuccessorTests",
            "-v",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if suite.returncode != 0:
        sys.stderr.write(suite.stdout)
        sys.stderr.write(suite.stderr)
        fail("G2-B executable regression matrix failed")
    print("G2B_LEGACY_COMPATIBILITY=PASS")
    print("G2B_MIXED_SCHEMA_POLICY=PASS")
    print("G2B_IDEMPOTENT_DEDUPE=PASS")
    print("G2B_IMMUTABLE_CONFLICT_FAIL_CLOSED=PASS")
    print("G2B_FAIL_CLOSED_POLICY=PASS")


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
    print("G2B_D9_DEFAULT_ACTIVATION_UNCHANGED=PASS")

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

    _validate_g2b_candidate()
    print("D9_4_VALIDATION=PASS")
    print("G2B_VALIDATION=PASS")


if __name__ == "__main__":
    main()
