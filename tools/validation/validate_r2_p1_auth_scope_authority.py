from __future__ import annotations

import json
import re
from pathlib import Path

MASTER = Path("docs/semantics/d8-production-capability-parity-expansion-and-cutover-v1.md")
BRIDGE = Path("bridge-contract.json")
RUNTIME = Path("contracts/d8-runtime-candidate.json")
FORWARDING = Path("contracts/d8-d9-forwarding-v1.json")

MARKER_RE = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*)$", re.MULTILINE)
P1_REF_RE = re.compile(r"P1-(\d{2})(?:\.\.(\d{2}))?")

EXPECTED_MARKERS = {
    "R2_P1_AUTH_SCOPE_REVERIFY_AS_OF_UTC": "2026-08-24T08:35:54Z",
    "P1_01_IDENTITY_PRESERVED": "true",
    "P1_01_ENDPOINT": "/futures/data/globalLongShortAccountRatio",
    "P1_01_AUTH_SCOPE": "PUBLIC_NO_AUTH",
    "P1_01_AUTH_HEADER_REQUIRED": "false",
    "P1_01_REQUEST_WEIGHT": "IP_WEIGHT_0",
    "P1_01_CURRENT_DISPOSITION": "P1_COMPACT",
    "P1_02_IDENTITY_PRESERVED": "true",
    "P1_02_ENDPOINT": "/futures/data/topLongShortAccountRatio",
    "P1_02_PROVIDER_SECURITY_CLASS": "MARKET_DATA",
    "P1_02_AUTH_SCOPE": "PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT",
    "P1_02_AUTH_HEADER_REQUIRED": "true",
    "P1_02_REQUIRED_HEADER": "X-MBX-APIKEY",
    "P1_02_REQUEST_WEIGHT": "NOT_EXPLICITLY_STATED_IN_CURRENT_OFFICIAL_PAGE",
    "P1_02_CURRENT_DISPOSITION": "AUTH_REQUIRED_REVIEW",
    "P1_03_IDENTITY_PRESERVED": "true",
    "P1_03_ENDPOINT": "/futures/data/topLongShortPositionRatio",
    "P1_03_PROVIDER_SECURITY_CLASS": "MARKET_DATA",
    "P1_03_AUTH_SCOPE": "PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT",
    "P1_03_AUTH_HEADER_REQUIRED": "true",
    "P1_03_REQUIRED_HEADER": "X-MBX-APIKEY",
    "P1_03_REQUEST_WEIGHT": "IP_WEIGHT_0",
    "P1_03_CURRENT_DISPOSITION": "AUTH_REQUIRED_REVIEW",
    "COINM_TOP_TRADER_COMPARATOR_AUTH_SCOPE": "PUBLIC_NO_AUTH",
    "COINM_TOP_TRADER_COMPARATOR_REQUEST_WEIGHT": "IP_WEIGHT_1",
    "P1_23_IDENTITY_PRESERVED": "true",
    "P1_23_CURRENT_DISPOSITION": "AUTH_REQUIRED_REVIEW",
    "KRAKEN_L3_AUTH_SCOPE": "AUTHENTICATED_MARKET_DATA",
    "COUNT_RECOMPUTATION_METHOD": "SECTION_24_7_P1_IDENTITY_DISPOSITION_RECOUNT_WITH_AUTH_SOURCE_ALIAS",
    "AUTH_REQUIRED_REVIEW_MATRIX_ALIAS_KS_08": "KS_07",
    "P1_REGISTRY_ENTRY_COUNT": "70",
    "P1_AUTH_REQUIRED_REVIEW_ENTRY_COUNT": "3",
    "FINAL_P1_COMPACT_FAMILY_COUNT": "67",
    "FINAL_P2_FAMILY_COUNT": "13",
    "PROVIDER_METADATA_FAMILY_COUNT": "8",
    "AUTH_REQUIRED_REVIEW_COUNT": "7",
    "REDUNDANT_OR_REJECTED_COUNT": "11",
    "UNCLASSIFIED_RELEVANT_PROVIDER_CAPABILITY_COUNT": "0",
    "COUNT_MATRIX_CONSISTENCY": "PASS",
    "R2_P2_DEPENDENCY_REVIEW_REQUIRED_BEFORE_COMPLETE_COMPACT_PASS": "true",
    "R2_P2_DEPENDENCY_REVIEW_IDS": "P1-09,P1-11,P1-12,P1-13,P1-14,P1-15,P1-22,P1-31,P1-32,P1-33,P1-53",
    "P2_BACKEND_SELECTED_BY_THIS_RECONCILIATION": "false",
    "R2_RUNTIME_SOURCE_IMPLEMENTATION_RESUMED": "false",
    "R1_DATA_BRIDGE_OWNER_MERGE": "00c362791be305313de2d115cbe1d85d6834bf30",
    "R1_P0_PARITY_STATUS": "OWNER_INTEGRATED",
    "P0_GAP_COUNT_AFTER": "0",
    "CURRENT_GITHUB_INFORMATION_SET_SUBSET_OF_D8_VPS_INFORMATION_SET": "PASS",
    "OLD_D8_INFORMATION_SET_SUBSET_OF_NEW_D8_INFORMATION_SET": "PASS",
    "D8_ACTIVE": "false",
    "D9_ACTIVE": "false",
    "PRODUCTION_CUTOVER": "false",
    "PROVIDER_AUTHORITY_TRANSITION": "false",
    "LEGACY_GITHUB_PRODUCTION_ACQUISITION_ACTIVE": "true",
    "D9_COLD_V2_AUTHORITY": "NOT_ACTIVE",
    "ACTIVE_DEFAULT_ROUTE": "D6_RESOLUTION_PLAN_V1",
}

FORBIDDEN_STALE_FRAGMENTS = {
    "| BU-05 | Binance USD-M | global/top-trader long-short ratios | REST PUB |",
    "`P1_COMPACT` P1-01..03",
    "P1_AUTH_REQUIRED_REVIEW_ENTRY_COUNT=1",
    "FINAL_P1_COMPACT_FAMILY_COUNT=69",
    "AUTH_REQUIRED_REVIEW_COUNT=5",
}

REQUIRED_ROW_FRAGMENTS = {
    "| BU-05A | Binance USD-M | global long/short account ratio P1-01; `/futures/data/globalLongShortAccountRatio` | REST PUB |",
    "| BU-05B | Binance USD-M | top-trader long/short account ratio P1-02; `/futures/data/topLongShortAccountRatio` | REST KEY (`MARKET_DATA`, `X-MBX-APIKEY`) |",
    "| BU-05C | Binance USD-M | top-trader long/short position ratio P1-03; `/futures/data/topLongShortPositionRatio` | REST KEY (`MARKET_DATA`, `X-MBX-APIKEY`) |",
    "| DF-04 | Deribit Futures | dated futures ticker/OHLCV/book summaries including OI-by-maturity source evidence |",
}


def marker_values(text: str) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for match in MARKER_RE.finditer(text):
        values.setdefault(match.group("key"), set()).add(match.group("value").strip())
    return values


def expand_p1_refs(text: str) -> set[int]:
    result: set[int] = set()
    for match in P1_REF_RE.finditer(text):
        start = int(match.group(1))
        end_text = match.group(2)
        end = int(end_text) if end_text is not None else start
        if end < start:
            raise RuntimeError(f"invalid P1 range: {match.group(0)}")
        result.update(range(start, end + 1))
    return result


def matrix_rows(text: str) -> list[tuple[str, list[str], str]]:
    start = text.index("### 24.7 Exhaustive audited surface matrix")
    end = text.index("### 24.8 P0/P1/P2 current registries and counts")
    section = text[start:end]
    rows: list[tuple[str, list[str], str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 13 or parts[0] in {"ID", "---"} or set(parts[0]) == {"-"}:
            continue
        rows.append((parts[0], parts, line))
    return rows


def validate_matrix(text: str) -> tuple[int, int, int, int]:
    rows = matrix_rows(text)
    p1_dispositions: dict[int, set[str]] = {}
    auth_rows: set[str] = set()

    for row_id, parts, raw in rows:
        disposition = parts[10]
        refs = expand_p1_refs(raw)
        if "AUTH_REQUIRED_REVIEW" in disposition:
            auth_rows.add(row_id)
        for p1_id in refs:
            if "AUTH_REQUIRED_REVIEW" in disposition:
                cls = "AUTH_REQUIRED_REVIEW"
            elif "P1_COMPACT" in disposition or "DERIVE_FROM_CANONICAL_SOURCE" in disposition:
                cls = "COMPACT_OR_DERIVED"
            else:
                continue
            p1_dispositions.setdefault(p1_id, set()).add(cls)

    expected_ids = set(range(1, 71))
    actual_ids = set(p1_dispositions)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise RuntimeError(f"P1 matrix identity coverage mismatch: missing={missing} extra={extra}")

    conflicts = {key: sorted(value) for key, value in p1_dispositions.items() if len(value) != 1}
    if conflicts:
        raise RuntimeError(f"P1 matrix disposition conflicts: {conflicts}")

    auth_p1 = {key for key, value in p1_dispositions.items() if value == {"AUTH_REQUIRED_REVIEW"}}
    compact_p1 = {key for key, value in p1_dispositions.items() if value == {"COMPACT_OR_DERIVED"}}
    if auth_p1 != {2, 3, 23}:
        raise RuntimeError(f"unexpected P1 auth-review set: {sorted(auth_p1)}")
    if compact_p1 != expected_ids - auth_p1:
        raise RuntimeError("compact P1 set is not exact registry minus auth-review set")

    aliases = {"KS-08": "KS-07"}
    normalized_auth_rows = {aliases.get(row_id, row_id) for row_id in auth_rows}
    if len(normalized_auth_rows) != 7:
        raise RuntimeError(
            f"overall auth-review surface count mismatch: rows={sorted(auth_rows)} normalized={sorted(normalized_auth_rows)}"
        )

    return len(expected_ids), len(auth_p1), len(compact_p1), len(normalized_auth_rows)


def validate_machine_freeze() -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    forwarding = json.loads(FORWARDING.read_text(encoding="utf-8"))

    usdm = bridge["disabled_providers"]["binance-usdm"]
    assert usdm["status"] == "DISABLED_BY_POLICY"
    assert usdm["network_calls"] == 0
    assert usdm["vps_runtime_status"] == "NOT_ACTIVE"
    assert bridge["semantic_resolution"]["resolver"]["resolution_plan_schema"] == "market-data-resolution-plan/1.0.0"
    assert bridge["d9_candidate"]["authority_activation_status"] == "NOT_ACTIVE"

    authority = runtime["authority"]
    assert runtime["status"] == "SOURCE_CANDIDATE_NOT_DEPLOYED"
    assert authority["d8_runtime_active"] is False
    assert authority["d9_active"] is False
    assert authority["active_default_route"] == "D6_RESOLUTION_PLAN_V1"
    assert authority["vps_is_market_data_authority"] is False
    assert authority["provider_authority_transition_allowed"] is False
    assert authority["production_cutover_allowed"] is False

    fwd = forwarding["authority"]
    assert fwd["d8_active"] is False
    assert fwd["d9_active"] is False
    assert fwd["vps_is_market_data_authority"] is False
    assert fwd["production_cutover"] is False
    assert fwd["provider_authority_transition"] is False
    assert fwd["legacy_github_production_acquisition_active"] is True
    assert fwd["production_warm_forwarder_deployed"] is False
    assert forwarding["source"]["state_schema_version"] == 2


def validate() -> None:
    text = MASTER.read_text(encoding="utf-8")
    values = marker_values(text)
    problems: list[str] = []

    for key, expected in EXPECTED_MARKERS.items():
        actual = values.get(key, set())
        if actual != {expected}:
            problems.append(f"{key}: expected only {expected!r}, got {sorted(actual)!r}")

    for fragment in sorted(FORBIDDEN_STALE_FRAGMENTS):
        if fragment in text:
            problems.append(f"stale authority fragment remains: {fragment}")

    for fragment in sorted(REQUIRED_ROW_FRAGMENTS):
        if fragment not in text:
            problems.append(f"required matrix row missing: {fragment}")

    if problems:
        raise RuntimeError("R2_P1_AUTH_SCOPE_AUTHORITY_INVALID: " + " | ".join(problems))

    registry_count, p1_auth_count, compact_count, auth_surface_count = validate_matrix(text)
    if registry_count != int(next(iter(values["P1_REGISTRY_ENTRY_COUNT"]))):
        raise RuntimeError("declared P1 registry count does not match matrix")
    if p1_auth_count != int(next(iter(values["P1_AUTH_REQUIRED_REVIEW_ENTRY_COUNT"]))):
        raise RuntimeError("declared P1 auth-review count does not match matrix")
    if compact_count != int(next(iter(values["FINAL_P1_COMPACT_FAMILY_COUNT"]))):
        raise RuntimeError("declared compact P1 count does not match matrix")
    if auth_surface_count != int(next(iter(values["AUTH_REQUIRED_REVIEW_COUNT"]))):
        raise RuntimeError("declared overall auth-review count does not match matrix")

    validate_machine_freeze()

    print("R2_P1_AUTH_SCOPE_AUTHORITY=PASS")
    print(f"P1_REGISTRY_ENTRY_COUNT={registry_count}")
    print(f"P1_AUTH_REQUIRED_REVIEW_ENTRY_COUNT={p1_auth_count}")
    print(f"FINAL_P1_COMPACT_FAMILY_COUNT={compact_count}")
    print(f"AUTH_REQUIRED_REVIEW_COUNT={auth_surface_count}")
    print("P1_AUTH_REQUIRED_REVIEW_IDS=P1-02,P1-03,P1-23")
    print("P1_02_AUTH_SCOPE=PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT")
    print("P1_03_AUTH_SCOPE=PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT")
    print("P1_23_CURRENT_DISPOSITION=AUTH_REQUIRED_REVIEW")
    print("R2_P2_DEPENDENCY_REVIEW_REQUIRED_BEFORE_COMPLETE_COMPACT_PASS=true")
    print("P0_GAP_COUNT_AFTER=0")
    print("STATE_SCHEMA_VERSION=2")
    print("PRODUCTION_WARM_FORWARDER_DEPLOYED=false")
    print("PRODUCTION_ACTIVATION=NO")


if __name__ == "__main__":
    validate()
