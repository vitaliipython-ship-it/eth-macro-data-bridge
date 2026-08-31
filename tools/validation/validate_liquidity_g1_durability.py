from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = "contracts/liquidity-durable-l2-observation-v1.json"
PROGRAM_MAP_PATH = "docs/semantics/deep-liquidity-program-map-v1.md"
HUMAN_PATH = "docs/semantics/liquidity-durable-l2-observation-v1.md"
IDENTITY_FIELDS = ("provider_id", "instrument_id", "book_kind", "observation_id")
TOP_LEVEL_FIELDS = {
    "schema_version", "contract_id", "status", "ownership", "family", "value_substrate",
    "observation_identity", "market_time", "durable_observation", "history_target_assessment",
    "partial_observation", "deduplication", "provenance", "request_resource_separation",
    "legacy_compatibility", "storage_independence", "cadence_independence", "stage_boundaries",
    "authority_reuse",
}
FROZEN_G2A_IMPLEMENTATION_PATHS = (
    ".github/workflows/update-market.yml",
    ".github/workflows/current-data-request.yml",
    "src/intelligence.py",
    "src/sampled_history.py",
    "tools/current_data_promotion.py",
    "bridge-contract.json",
    "contracts/liquidity-durable-l2-observation-v1.json",
    "docs/semantics/deep-liquidity-program-map-v1.md",
    "docs/semantics/fresh-current-agent-transport-v1.md",
    "AGENTS.md",
    "tools/validation/validate_liquidity_g1_durability.py",
    "tests/deep_history/test_liquidity_g1_durability.py",
    "tests/deep_history/test_current_data_promotion.py",
    "tests/deep_history/test_d9_sampled_history.py",
    "tests/deep_history/test_d9_liquidity_reproducibility.py",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"G1_JSON_OBJECT_REQUIRED:{path}")
    return value


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    return _json(root / CONTRACT_PATH)


def parse_frozen_g2a_implementation_scope(program: str) -> tuple[int, tuple[str, ...]]:
    lines = program.splitlines()
    marker = "EXACT_IMPLEMENTATION_PATHS="
    marker_positions = [index for index, line in enumerate(lines) if line.strip() == marker]
    if len(marker_positions) != 1:
        raise ValueError(f"G2A_IMPLEMENTATION_SCOPE_MARKER_COUNT:{len(marker_positions)}")
    marker_index = marker_positions[0]
    if marker_index == 0:
        raise ValueError("G2A_IMPLEMENTATION_SCOPE_DECLARED_COUNT_MISSING")
    count_match = re.fullmatch(
        r"EXACT_IMPLEMENTATION_PATH_COUNT=(\d+)",
        lines[marker_index - 1].strip(),
    )
    if count_match is None:
        raise ValueError("G2A_IMPLEMENTATION_SCOPE_DECLARED_COUNT_MISSING")
    declared_count = int(count_match.group(1))

    parsed_paths: list[str] = []
    for line in lines[marker_index + 1 :]:
        stripped = line.strip()
        if stripped == "```":
            break
        if not stripped or stripped != line or "=" in stripped:
            raise ValueError("G2A_IMPLEMENTATION_SCOPE_MALFORMED_BLOCK")
        parsed_paths.append(stripped)
    else:
        raise ValueError("G2A_IMPLEMENTATION_SCOPE_UNTERMINATED_BLOCK")

    if not parsed_paths:
        raise ValueError("G2A_IMPLEMENTATION_SCOPE_EMPTY")
    duplicate_count = len(parsed_paths) - len(set(parsed_paths))
    if duplicate_count:
        raise ValueError(f"G2A_IMPLEMENTATION_SCOPE_DUPLICATE_PATHS:{duplicate_count}")
    return declared_count, tuple(parsed_paths)


def validate_frozen_g2a_implementation_scope(program: str) -> tuple[int, tuple[str, ...]]:
    declared_count, parsed_paths = parse_frozen_g2a_implementation_scope(program)
    expected_paths = FROZEN_G2A_IMPLEMENTATION_PATHS
    expected_count = len(expected_paths)
    if declared_count != expected_count:
        raise ValueError(
            f"G2A_IMPLEMENTATION_SCOPE_DECLARED_COUNT:{declared_count}:EXPECTED:{expected_count}"
        )
    if len(parsed_paths) != expected_count:
        raise ValueError(
            f"G2A_IMPLEMENTATION_SCOPE_PARSED_COUNT:{len(parsed_paths)}:EXPECTED:{expected_count}"
        )
    if parsed_paths != expected_paths:
        missing = tuple(path for path in expected_paths if path not in parsed_paths)
        extra = tuple(path for path in parsed_paths if path not in expected_paths)
        raise ValueError(
            "G2A_IMPLEMENTATION_SCOPE_EXACT_SET_MISMATCH:"
            f"MISSING={missing}:EXTRA={extra}"
        )
    return declared_count, parsed_paths


def observation_identity_material(observation: Mapping[str, Any]) -> tuple[str, str, str, str]:
    values: list[str] = []
    for field in IDENTITY_FIELDS:
        value = observation.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"OBSERVATION_IDENTITY_FIELD_INVALID:{field}")
        values.append(value)
    return tuple(values)  # type: ignore[return-value]


def dedupe_verdict(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> str:
    if observation_identity_material(existing) != observation_identity_material(incoming):
        return "DISTINCT_OBSERVATION"
    old_sha, new_sha = existing.get("observation_sha256"), incoming.get("observation_sha256")
    if not all(isinstance(value, str) and len(value) == 64 for value in (old_sha, new_sha)):
        raise ValueError("OBSERVATION_SHA256_INVALID")
    if old_sha == new_sha:
        return "IDEMPOTENT_DUPLICATE"
    raise ValueError("IMMUTABLE_OBSERVATION_CONFLICT")


def history_target_assessment(achieved_bid_bps: float, achieved_ask_bps: float, target_bps: int = 500) -> dict[str, Any]:
    if target_bps != 500 or achieved_bid_bps < 0 or achieved_ask_bps < 0:
        raise ValueError("HISTORY_TARGET_ASSESSMENT_INVALID")
    bid, ask = achieved_bid_bps >= target_bps, achieved_ask_bps >= target_bps
    return {
        "history_target_bps": target_bps,
        "actual_bid_coverage_bps": achieved_bid_bps,
        "actual_ask_coverage_bps": achieved_ask_bps,
        "history_target_complete_bid": bid,
        "history_target_complete_ask": ask,
        "history_target_truncated": not (bid and ask),
        "extrapolation_allowed": False,
        "durable_observation_allowed": True,
    }


def validate_g1(root: Path = ROOT) -> None:
    failures: list[str] = []

    def need(ok: bool, code: str) -> None:
        if not ok:
            failures.append(code)

    c = load_contract(root)
    need(set(c) == TOP_LEVEL_FIELDS, "CONTRACT_SHAPE")
    need(c.get("contract_id") == "ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1", "CONTRACT_ID")
    need(c.get("status") == "G1_CONTRACT_INSTALLED_WRITER_INACTIVE", "CONTRACT_STATUS")
    need(c.get("family") == {
        "evolve_existing_family": True,
        "family_id": "liquidity.orderbook-snapshots",
        "new_parallel_deep_history_family": False,
    }, "EXISTING_HISTORY_FAMILY")

    substrate = c.get("value_substrate", {})
    need(substrate.get("normalized_book_schema") == "liquidity-s1-normalized-book/1.0.0", "S1_VALUE_SUBSTRATE")
    need(substrate.get("reuse_required") is True and substrate.get("second_normalized_order_book_representation") is False,
         "SECOND_VALUE_SHAPE")
    need('BOOK_SCHEMA = "liquidity-s1-normalized-book/1.0.0"' in (root / "src/liquidity_s1_runtime.py").read_text(),
         "S1_RUNTIME_BINDING")

    identity = c.get("observation_identity", {})
    need(identity.get("semantic_identity_fields") == list(IDENTITY_FIELDS), "OBSERVATION_IDENTITY")
    need(identity.get("immutable_content_binding") == "observation_sha256", "OBSERVATION_SHA_BINDING")
    excluded = set(identity.get("excluded_from_semantic_identity", []))
    need(identity.get("request_identity_excluded") is True and
         {"request_sha256", "current_semantic_request_sha256", "storage_backend", "cadence", "known_at"} <= excluded,
         "REQUEST_PHYSICAL_IDENTITY_EXCLUSION")

    target, partial = c.get("history_target_assessment", {}), c.get("partial_observation", {})
    need(target.get("history_target_bps") == 500 and target.get("identity_role") == "NON_IDENTITY_ASSESSMENT_METADATA",
         "HISTORY_TARGET")
    need(target.get("extrapolation_allowed") is False, "NO_EXTRAPOLATION")
    need(partial.get("persist_coherent_partial_observation") is True and
         partial.get("target_miss_does_not_invalidate_observed_market_fact") is True and
         partial.get("request_satisfaction_remains_separate") is True, "PARTIAL_OBSERVATION")

    dedupe = c.get("deduplication", {})
    need(dedupe.get("same_identity_same_observation_sha256") == "IDEMPOTENT_DUPLICATE" and
         dedupe.get("same_identity_different_observation_sha256") == "FAIL_CLOSED_IMMUTABLE_OBSERVATION_CONFLICT" and
         dedupe.get("existing_immutable_primitive") == "src/history_store.py::merge_records" and
         dedupe.get("second_dedupe_ledger") is False, "DEDUPE_SEMANTICS")
    history_store = (root / "src/history_store.py").read_text()
    need("IMMUTABLE_IDENTITY_CONFLICT" in history_store and "ImmutableHistoryConflict" in history_store, "HISTORY_STORE_REUSE")

    provenance = c.get("provenance", {})
    need(provenance.get("decision") == "OPTION_B_COMPACT_STABLE_ACQUISITION_PROVENANCE_DIGESTS" and
         provenance.get("full_s3_execution_receipt_forever") is False, "PROVENANCE_OPTION_B")

    separation = c.get("request_resource_separation", {})
    need(separation.get("request_specific_exact_resource_durability") == "EPHEMERAL_ONLY" and
         separation.get("underlying_market_observation_durability") == "ELIGIBLE_FOR_CANONICAL_HISTORY" and
         separation.get("cross_run_exact_resource_reuse") is False and
         separation.get("actions_artifact_as_cross_run_cache") is False and
         separation.get("reuse_creates_new_historical_observation") is False, "REQUEST_OBSERVATION_SEPARATION")

    legacy = c.get("legacy_compatibility", {})
    need(legacy.get("legacy_snapshot_bytes_mutated") is False and legacy.get("legacy_100_level_history_valid") is True and
         legacy.get("legacy_100_level_history_relabelled_as_500_bps_complete") is False and
         legacy.get("synthetic_deep_backfill") is False, "LEGACY_COMPATIBILITY")

    need(c.get("cadence_independence", {}).get("cadence_is_semantic_identity") is False, "CADENCE_IDENTITY")
    storage = c.get("storage_independence", {})
    need(storage.get("storage_backend_is_semantic_identity") is False and storage.get("physical_locator_is_semantic_identity") is False,
         "STORAGE_IDENTITY")

    times = c.get("market_time", {})
    need(set(times.get("vocabulary", [])) == {"observation_time", "known_at", "retrieved_at", "durable_publication_time"} and
         times.get("observation_time_semantically_distinct_from_known_at") is True and
         times.get("known_at_after_cutoff_excluded") is True, "NO_LOOKAHEAD_VOCABULARY")
    resolution = (root / "tools/resolution_v2.py").read_text()
    need("known_at_ms > cutoff_ms" in resolution and '"liquidity.orderbook-snapshots"' in resolution, "EXISTING_PIT_ROUTE")

    bridge = _json(root / "bridge-contract.json")
    need(bridge.get("semantic_contracts", {}).get("liquidity_durable_l2") == {
        "contract_id": "ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1",
        "g2_implemented": False,
        "path": CONTRACT_PATH,
        "status": "G1_CONTRACT_INSTALLED_WRITER_INACTIVE",
        "writer_active": False,
    }, "BRIDGE_DISCOVERY")
    req = bridge.get("semantic_resolution", {}).get("current_data", {}).get("requestable_liquidity", {})
    need(req.get("exact_resource_durability") == "EPHEMERAL_ONLY" and req.get("cross_run_cache_eligible") is False and
         req.get("binance_usdm_github_network_calls") == 0, "CURRENT_DATA_BOUNDARY")

    stages = c.get("stage_boundaries", {})
    need(stages.get("g1_writer_active") is False and stages.get("g2_a_writer_implemented") is False and
         stages.get("g2_b_reader_implemented") is False and stages.get("provider_network_calls") == 0 and
         stages.get("binance_usdm_github_network_calls") == 0 and stages.get("db_g_started") is False, "G1_BOUNDARY")
    intelligence = (root / "src/intelligence.py").read_text()
    need("limit=100" in intelligence and '"binance-usdm"]={"status":"DISABLED_BY_POLICY"' in intelligence, "G2_RUNTIME_INACTIVE")

    reuse = c.get("authority_reuse", {})
    need(all(value is False for value in reuse.values()), "SECOND_AUTHORITY")

    maps = list((root / "docs/semantics").glob("*deep*liquidity*program*map*.md"))
    need(len(maps) == 1 and maps[0].name == "deep-liquidity-program-map-v1.md", "PROGRAM_MAP_SINGLETON")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    program = (root / PROGRAM_MAP_PATH).read_text(encoding="utf-8")
    human = (root / HUMAN_PATH).read_text(encoding="utf-8")
    need(PROGRAM_MAP_PATH in agents and "semantic_contracts.liquidity_durable_l2" in agents, "AGENTS_ROUTE")
    need(re.search(r"[А-Яа-яЁё]", program) is not None and re.search(r"[А-Яа-яЁё]", human) is not None, "RUSSIAN_DOCS")
    for marker in (
        "DB_F_S3=CLOSED", "G1=CLOSED", "CURRENT_STAGE=G2-A",
        "G1_OWNER_INTEGRATION=PASS", "G1_PR_NUMBER=385",
        "G1_MERGE_COMMIT=60ed320527e6dfbc262de59fda81989a4a22c18b",
        "G1_POSTMERGE_QUALIFICATION=PASS",
        "G1_SCOPE", "G2_A_SCOPE", "G2_B_SCOPE",
        "HOURLY_HISTORY_TARGET_BPS=500", "SIX_CAPABILITY_BASELINE_SCOPE",
        "FRESH_CURRENT_NEW_OBSERVATION_DURABILITY", "NO_FAKE_HISTORY_ON_REUSE",
        "PERSIST_PARTIAL_COHERENT_OBSERVATION", "LEGACY_FIXED_100_SUCCESSION", "NO_SYNTHETIC_BACKFILL",
        "OBSERVATION_DEDUPE", "OPTION_B_COMPACT", "NO_LOOKAHEAD",
        "REPRESENTATIVE_PLANNING_ESTIMATE_NOT_MEASURED_SUCCESSOR_BYTES", "FUTURE_5M_SERVER_SEMANTIC_COMPATIBILITY",
        "D8_D9_VPS_AIFE_SERVER_SEPARATE_CONTOUR",
        "G2A_PREIMPLEMENTATION=PASS", "READY_FOR_G2A_IMPLEMENTATION=YES",
        "EXACT_IMPLEMENTATION_PATH_COUNT=15", "NEW_PATH_COUNT=0",
        "TRUNCATED_HANDOFF_DESIGN=RESOLVED", "OBSERVATION_DEDUPE_DESIGN=RESOLVED",
        "HOURLY_DEPENDENCY_INSTALLATION=RESOLVED", "CRON_RECONCILIATION=RESOLVED",
        "PROMOTION_RETENTION_GATE=RESOLVED", "SUCCESSOR_BYTE_BENCHMARK_PLAN=RESOLVED",
        "LAST_CONFIRMED_GATE=G2A_PREIMPLEMENTATION_OWNER_REVIEW_PASS",
        "NEXT_EXACT_TASK=ETH-LIQUIDITY-G2A-HOURLY-BASELINE-FRESH-CURRENT-DURABLE-ACCUMULATION-AND-LEGACY-FIXED-DEPTH-SUCCESSION-IMPLEMENTATION-R01",
        "BLOCKERS=NONE",
    ):
        need(marker in program, f"PROGRAM_MAP_MARKER:{marker}")
    try:
        declared_scope_count, parsed_scope_paths = validate_frozen_g2a_implementation_scope(program)
    except ValueError as exc:
        failures.append(str(exc))
    else:
        need(declared_scope_count == 15, "G2A_FROZEN_SCOPE_DECLARED_COUNT")
        need(len(parsed_scope_paths) == 15, "G2A_FROZEN_SCOPE_PARSED_COUNT")
        need(len(set(parsed_scope_paths)) == 15, "G2A_FROZEN_SCOPE_DUPLICATE_PATH_COUNT")
        need(parsed_scope_paths == FROZEN_G2A_IMPLEMENTATION_PATHS, "G2A_FROZEN_SCOPE_EXACT_SET")
    for stale_marker in (
        "CURRENT_STAGE=G1",
        "G1_CONTRACT_IMPLEMENTATION_CANDIDATE_QUALIFIED_PENDING_OWNER_INTEGRATION",
        "NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK",
        "LAST_CONFIRMED_GATE=G1_OWNER_INTEGRATION_AND_POSTMERGE_READBACK_PASS",
        "NEXT_EXACT_TASK=ETH-LIQUIDITY-G2A-HOURLY-BASELINE-FRESH-CURRENT-DURABLE-ACCUMULATION-AND-LEGACY-FIXED-DEPTH-SUCCESSION-PREIMPLEMENTATION-R01",
    ):
        need(stale_marker not in program, f"PROGRAM_MAP_ACTIVE_STALE:{stale_marker}")
    need("EVIDENCE_ONLY" in program and "внешний" in program.lower(), "EXTERNAL_ARTIFACT_EVIDENCE_ONLY")

    if failures:
        raise RuntimeError("G1_DURABILITY_VALIDATION_FAILED:" + ",".join(failures))


def main() -> int:
    validate_g1(ROOT)
    print("G1_DURABILITY_CONTRACT=PASS")
    print("CANONICAL_DEEP_LIQUIDITY_PROGRAM_MAP_COUNT=1")
    print("G1_PROGRAM_STAGE=CLOSED")
    print("CURRENT_DEEP_LIQUIDITY_STAGE=G2-A")
    print("G2A_PREIMPLEMENTATION=PASS")
    print("READY_FOR_G2A_IMPLEMENTATION=YES")
    print("G2A_EXACT_IMPLEMENTATION_PATH_COUNT=15")
    print("G2A_PARSED_IMPLEMENTATION_PATH_COUNT=15")
    print("G2A_IMPLEMENTATION_PATHS_EXACT_MATCH=PASS")
    print("G2A_DUPLICATE_IMPLEMENTATION_PATH_COUNT=0")
    print("G2A_CRON_DECLARATION_OWNER_PATH_INCLUDED=PASS")
    print("REQUEST_RESOURCE_DURABILITY=EPHEMERAL_ONLY")
    print("UNDERLYING_OBSERVATION_DURABILITY_CONTRACT=DEFINED")
    print("LEGACY_100_LEVEL_COMPATIBILITY=PASS")
    print("NO_LOOKAHEAD=PASS")
    print("SECOND_AUTHORITY_COUNT=0")
    print("G2_WRITER_IMPLEMENTED=NO")
    print("G2_READER_IMPLEMENTED=NO")
    print("PROVIDER_NETWORK_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
