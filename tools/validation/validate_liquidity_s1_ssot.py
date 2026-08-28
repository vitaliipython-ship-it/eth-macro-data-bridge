from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]

ACTIVE_CURRENT_AUTHORITY = "ACTIVE_CURRENT_AUTHORITY"
CURRENT_COMPATIBLE_CONTEXT = "CURRENT_COMPATIBLE_CONTEXT"
HISTORICAL_EVIDENCE = "HISTORICAL_EVIDENCE"
SUPERSEDED_HISTORICAL = "SUPERSEDED_HISTORICAL"
OUT_OF_SCOPE = "OUT_OF_SCOPE"

S1 = "contracts/liquidity-s1-semantic-contract-v1.json"
PROVIDERS = "contracts/provider-contracts.json"
HUMAN = "docs/semantics/liquidity-s1-semantic-contract-v1.md"
CAPABILITY = "docs/semantics/capability-index.md"
CURRENT = "docs/semantics/fresh-current-agent-transport-v1.md"
D8 = "docs/semantics/d8-vps-unified-acquisition-runtime-v1.md"
D9 = "docs/semantics/d9-operational-status-and-agent-usage-v1.md"
CVD = "docs/semantics/kraken-futures-cvd.md"
UPDATE_WORKFLOW = ".github/workflows/update-market.yml"
VALIDATE_WORKFLOW = ".github/workflows/validate-repository.yml"

ACTIVE_AUTHORITY_PATHS = {"AGENTS.md", "bridge-contract.json", S1, PROVIDERS}
CURRENT_CONTEXT_PATHS = {
    HUMAN, CAPABILITY, CURRENT, D8, D9, CVD,
    UPDATE_WORKFLOW, VALIDATE_WORKFLOW,
    "src/collector.py", "src/kraken_trade_flow.py",
}
CURRENT_TASK_CURRENTIZE_PATHS = {
    "AGENTS.md", "bridge-contract.json", PROVIDERS, CAPABILITY, CURRENT, D9,
}
TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml", ".toml", ".txt"}

CONTROL_CONTRADICTIONS = (
    ("second_catalog", re.compile(r'(?im)(?:^\s*SECOND_CATALOG\s*=\s*(?:YES|TRUE|ACTIVE)\s*$|"second_catalog"\s*:\s*true)')),
    ("second_resolver", re.compile(r'(?im)(?:^\s*SECOND_RESOLVER\s*=\s*(?:YES|TRUE|ACTIVE)\s*$|"second_resolver"\s*:\s*true)')),
    ("second_reader", re.compile(r'(?im)(?:^\s*SECOND_READER\s*=\s*(?:YES|TRUE|ACTIVE)\s*$|"second_reader"\s*:\s*true)')),
    ("second_collector", re.compile(r'(?im)(?:^\s*SECOND_COLLECTOR\s*=\s*(?:YES|TRUE|ACTIVE)\s*$|"second_collector"\s*:\s*true)')),
    ("second_refresh_transport", re.compile(r'(?im)(?:^\s*SECOND_REFRESH_TRANSPORT\s*=\s*(?:YES|TRUE|ACTIVE)\s*$|"second_refresh_transport"\s*:\s*true)')),
    ("s1_network_execution", re.compile(r'(?im)^\s*REQUEST_AWARE_NETWORK_ACQUISITION\s*=\s*(?:ACTIVE|IMPLEMENTED|YES|TRUE)\s*$')),
    ("s2_active", re.compile(r'(?im)^\s*S2_ACTIVE\s*=\s*(?:YES|TRUE|ACTIVE)\s*$')),
    ("s3_active", re.compile(r'(?im)^\s*S3_ACTIVE\s*=\s*(?:YES|TRUE|ACTIVE)\s*$')),
    ("od01_silently_resolved", re.compile(r'(?im)^\s*OD01_STATUS\s*=\s*(?:RESOLVED|CLOSED)\s*$')),
)


def classify_path(path: str) -> str:
    if path in ACTIVE_AUTHORITY_PATHS:
        return ACTIVE_CURRENT_AUTHORITY
    if path in CURRENT_CONTEXT_PATHS:
        return CURRENT_COMPATIBLE_CONTEXT
    if path.startswith("docs/handoffs/") or path.startswith("AIFE/evidence/"):
        return HISTORICAL_EVIDENCE
    if path.startswith("AIFE/staging/"):
        return SUPERSEDED_HISTORICAL
    return OUT_OF_SCOPE


def discover_audit_corpus(root: Path = ROOT) -> list[str]:
    found = set(ACTIVE_AUTHORITY_PATHS | CURRENT_CONTEXT_PATHS)
    found = {p for p in found if (root / p).is_file()}
    for dirname in ("docs/handoffs", "AIFE/evidence", "AIFE/staging"):
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


def _text(path: str, root: Path, overrides: Mapping[str, str] | None) -> str:
    if overrides and path in overrides:
        return overrides[path]
    return (root / path).read_text(encoding="utf-8")


def _json(path: str, root: Path, overrides: Mapping[str, str] | None):
    return json.loads(_text(path, root, overrides))


def _mapping(human: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for line in human.splitlines():
        if not line.startswith("|") or "`" not in line:
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        for owner in re.findall(r"`([^`]+)`", cells[1]):
            result.setdefault(owner, set()).add(cells[3])
    return result


def audit_active_current_semantics(
    root: Path = ROOT,
    overrides: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    corpus = discover_audit_corpus(root)
    classes = {p: classify_path(p) for p in corpus}
    active = [p for p in corpus if classes[p] in {ACTIVE_CURRENT_AUTHORITY, CURRENT_COMPATIBLE_CONTEXT}]
    historical = [p for p in corpus if classes[p] in {HISTORICAL_EVIDENCE, SUPERSEDED_HISTORICAL}]
    findings: list[dict[str, str]] = []

    def bad(path: str, invariant: str, matched, reason: str) -> None:
        findings.append({
            "path": path,
            "classification": classify_path(path),
            "invariant": invariant,
            "matched_current_semantic": repr(matched),
            "reason": reason,
        })

    def check(ok: bool, path: str, invariant: str, matched, reason: str) -> None:
        if not ok:
            bad(path, invariant, matched, reason)

    c = _json(S1, root, overrides)
    providers = _json(PROVIDERS, root, overrides)
    bridge = _json("bridge-contract.json", root, overrides)
    agents = _text("AGENTS.md", root, overrides)
    human = _text(HUMAN, root, overrides)
    capability = _text(CAPABILITY, root, overrides)
    current = _text(CURRENT, root, overrides)
    d8 = _text(D8, root, overrides)
    d9 = _text(D9, root, overrides)
    update = _text(UPDATE_WORKFLOW, root, overrides)

    check(c.get("contract_id") == "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1", S1,
          "machine_owner_id", c.get("contract_id"), "exact S1 contract id required")
    check(c.get("status") == "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE", S1,
          "s1_non_runtime_status", c.get("status"), "S1 contract must remain non-runtime-active")
    auth = c.get("authority", {})
    check(auth.get("canonical_owner") == S1 and auth.get("route_provider_policy_authority") == "bridge-contract.json", S1,
          "authority_graph", auth, "S1 owner must stay inside bridge-contract authority graph")
    check(auth.get("standalone_correction_artifacts_role") == "HISTORICAL_EVIDENCE_ONLY_NOT_CANONICAL_SSOT", S1,
          "standalone_artifact_not_ssot", auth.get("standalone_correction_artifacts_role"),
          "standalone correction carriers are historical evidence only")

    pointer = bridge.get("semantic_contracts", {}).get("liquidity_s1", {})
    expected_pointer = {
        "contract_id": "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1",
        "path": S1,
        "status": "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE",
        "runtime_active": False,
    }
    check(pointer == expected_pointer, "bridge-contract.json", "bridge_s1_discoverability", pointer,
          "bridge-contract must resolve exact non-active S1 owner")
    chain = "AGENTS.md\n→ bridge-contract.json\n→ semantic_contracts.liquidity_s1\n→ contracts/liquidity-s1-semantic-contract-v1.json"
    check(chain in agents and "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE" in agents
          and "`runtime_active=false`" in agents, "AGENTS.md", "canonical_entrypoint_binding",
          "present" if "semantic_contracts.liquidity_s1" in agents else "missing",
          "AGENTS must expose non-active S1 owner from canonical entrypoint")
    check("semantic_contracts.liquidity_s1" in d9 and S1 in d9 and "runtime_active=false" in d9, D9,
          "d9_hierarchy_discoverability", "present" if S1 in d9 else "missing",
          "D9 machine-SSOT hierarchy must expose the non-active S1 owner")

    arch = c.get("architecture", {})
    check(arch.get("model") == "ARCH_B_CAPABILITY_SELECTIVE_EXTENSION"
          and arch.get("market_data_foundation_contour_count") == 1, S1,
          "arch_b_single_contour", arch, "ARCH_B and one Market Data Foundation contour required")
    for key in ("second_catalog", "second_resolver", "second_reader", "second_collector",
                "second_refresh_transport", "second_capability_authority", "second_provider_authority"):
        check(arch.get(key) is False, S1, f"no_{key}", arch.get(key), f"{key} must remain false")

    stages = c.get("stage_boundaries", {})
    check(stages.get("acquisition_plan_contract") == "DEFINED_IN_S1"
          and stages.get("request_aware_network_acquisition") == "NOT_IMPLEMENTED_BY_S1", S1,
          "s1_contract_not_execution", stages, "S1 defines AcquisitionPlan but not request-aware network execution")
    check(stages.get("S1", {}).get("provider_network_rollout") is False
          and stages.get("S2", {}).get("active_in_this_contract_installation") is False
          and stages.get("S3", {}).get("active_in_this_contract_installation") is False, S1,
          "s1_s2_s3_non_activation", stages, "S1 rollout and S2/S3 activation must remain false")

    dynamic = c.get("dynamic_depth_acquisition_plan", {})
    expected_flow = ["SEMANTIC_COVERAGE_REQUEST", "RESOURCE_SATISFACTION_CHECK",
                     "DYNAMIC_DEPTH_ACQUISITION_PLANNER", "EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN",
                     "ONE_COHERENT_PROVIDER_OBSERVATION"]
    check(dynamic.get("flow") == expected_flow, S1, "resource_satisfaction_before_acquisition",
          dynamic.get("flow"), "resource satisfaction must precede planner/acquisition")
    req = dynamic.get("semantic_request", {})
    check({"representation", "target_bps", "bucket_bps", "freshness", "completeness"} <= set(req.get("required_fields", []))
          and {250, 500} <= set(req.get("minimum_required_target_bps_examples", [])), S1,
          "semantic_depth_250_500", req, "250/500 bps must be expressible semantically")
    check(req.get("provider_specific_depth_or_level_limit_is_agent_knowledge") is False, S1,
          "no_agent_provider_depth_guessing", req.get("provider_specific_depth_or_level_limit_is_agent_knowledge"),
          "agent must not know provider max_levels/depth")
    planner = dynamic.get("planner", {})
    check(planner.get("exactly_one_provider_acquisition_plan_per_observation") is True
          and planner.get("sequential_rest_depth_escalation_stitched_as_one_observation") == "FORBIDDEN"
          and planner.get("retry_semantics") == "NEW_OBSERVATION"
          and planner.get("s1_executes_network") is False, S1,
          "one_coherent_observation", planner, "REST stitching is forbidden and S1 does not execute network")

    reuse = c.get("resource_satisfaction", {})
    check(reuse.get("check_before_network_acquisition") is True
          and reuse.get("deeper_fresh_coherent_raw_may_satisfy_narrower_profile") is True
          and reuse.get("reacquire_when_dominating_resource_exists") is False, S1,
          "resource_satisfaction_reuse", reuse, "dominating fresh resource must be reused before acquisition")
    coverage = c.get("coverage", {})
    check(coverage.get("requested_target_coverage_is_distinct_from_provider_acquisition_depth") is True
          and coverage.get("provider_acquisition_depth_is_distinct_from_actual_achieved_coverage") is True
          and set(coverage.get("side_specific_fields", [])) == {"bid_coverage", "ask_coverage", "common_complete_bps"}
          and coverage.get("target_bps_500_expressible") is True
          and coverage.get("no_extrapolation_outside_observed_book") is True
          and coverage.get("mandatory_completeness_target_missed") == "FAIL_CLOSED", S1,
          "coverage_semantics", coverage, "side-specific achieved coverage/no extrapolation must remain explicit")

    books = c.get("book_kind", {})
    check({"L2_LEVEL_BOOK", "PROVIDER_GROUPED_L2", "L3_ORDER_BOOK", "FUTURES_L2_BOOK"}
          <= set(books.get("semantic_book_kinds", []))
          and set(books.get("representations", [])) == {"RAW", "NORMALIZED", "PROFILE", "SUMMARY"}
          and books.get("kraken_grouped_book_equals_aife_profile") is False
          and books.get("l3_equals_ordinary_l2_raw") is False, S1,
          "book_kind_not_representation", books, "GroupedBook != PROFILE and L3 != ordinary L2 RAW")
    spot = c.get("provider_boundaries", {}).get("kraken_spot", {})
    check(spot.get("provider_raw_book_capability") == "AVAILABLE_EXTERNALLY"
          and spot.get("raw_book_in_current_bridge") == "ABSENT", S1,
          "kraken_spot_capability_not_current_raw", spot, "external capability is not current AIFE RAW")
    fut = c.get("provider_boundaries", {}).get("kraken_futures", {})
    check(fut.get("raw_l2_book") == "PROVIDER_CAPABILITY_CONFIRMED"
          and fut.get("selectable_depth_limit") == "NOT_NORMATIVELY_DOCUMENTED"
          and fut.get("normative_max_depth_invented") is False, S1,
          "kraken_futures_max_not_invented", fut, "normative selectable Futures max depth must not be invented")
    check(fut.get("first_raw_book_instruments") == ["PI_ETHUSD", "PI_XBTUSD"]
          and fut.get("pf_may_substitute_for_pi") is False, S1,
          "pi_pf_identity", fut, "PF must not silently substitute PI")
    qty = c.get("derivatives_quantity", {})
    check(qty.get("model") == "PRODUCT_AWARE_NATIVE_FIRST"
          and qty.get("universal_provider_qty_to_base_quantity_mapping") == "FORBIDDEN"
          and qty.get("base_equivalent_nullable") is True and qty.get("quote_notional_nullable") is True
          and qty.get("unproven_conversion_result") == "UNAVAILABLE_OR_NULL"
          and qty.get("pi_pf_identity_distinct") is True and qty.get("pi_pf_silent_substitution") is False, S1,
          "native_first_quantity", qty, "derivatives quantity must stay product-aware/native-first")

    validity = c.get("observation_value_validity", {})
    required_states = {"VALID_ZERO", "UNAVAILABLE", "NOT_QUALIFIED", "SOURCE_CONFLICT",
                       "MISALIGNED", "UNKNOWN", "PARTIAL", "INCOMPLETE"}
    check(validity.get("global_invariant") == "OBSERVATION_COVERAGE_NE_VALUE_VALIDITY"
          and required_states <= set(validity.get("states", []))
          and validity.get("unobserved_data_may_masquerade_as_observed_zero") is False
          and validity.get("coverage_complete_alone_proves_separate_provider_native_numeric_value") is False
          and validity.get("provider_native_present_equals_consumer_qualified_available") is False, S1,
          "observation_vs_value_validity", validity, "unobserved/invalid data must not become ordinary zero/value")
    down = c.get("downstream_projection", {})
    check(down.get("route") == ["DERIVATIVES", "ANALYTICS", "CURRENT_DATA", "CONSUMER"]
          and down.get("validity_envelope_must_be_preserved") is True
          and down.get("not_qualified_cvd_may_appear_as_ordinary_consumer_zero") is False
          and down.get("source_conflict_may_become_available") is False, S1,
          "downstream_validity", down, "NOT_QUALIFIED/SOURCE_CONFLICT must remain controlling downstream")
    flow = c.get("kraken_futures_trade_flow", {})
    check(flow.get("trade_count", {}).get("raw_execution_reconciliation") == "QUALIFIED"
          and flow.get("trade_count", {}).get("analytics_interval_seconds") == 300
          and flow.get("trade_count", {}).get("accepted_current_timestamp_semantics") == "BUCKET_END"
          and flow.get("trade_count", {}).get("raw_bucket_semantics") == "[bucket_start,bucket_end)"
          and flow.get("trade_count", {}).get("mismatch") == "SOURCE_CONFLICT"
          and flow.get("trade_volume", {}).get("raw_history_size_to_analytics_base_volume_equivalence") == "NOT_QUALIFIED"
          and flow.get("aggressor_differential", {}).get("pi_raw_size_quantity_unit_equivalence") == "NOT_QUALIFIED"
          and flow.get("cvd", {}).get("raw_delta_state_equivalence") == "NOT_QUALIFIED"
          and flow.get("l2_derived_executed_trades") is False
          and flow.get("invented_raw_quantity_conversion") is False, S1,
          "kraken_trade_flow_boundaries", flow, "accepted raw/native qualification boundaries must remain fail-closed")

    od01 = c.get("od01", {})
    check(od01.get("status") == "OPEN_TRACKED_INTEGRATION_GATE"
          and od01.get("workflow_observed_schedule") == "17 * * * *"
          and od01.get("contract_declared_schedule") == "35 * * * *"
          and od01.get("resolved_by_this_installation") is False
          and od01.get("scheduler_behavior_changed_by_this_installation") is False
          and 'cron: "17 * * * *"' in update, UPDATE_WORKFLOW,
          "od01_open", {"contract": od01, "workflow17": 'cron: "17 * * * *"' in update},
          "OD-01 must remain explicit 17-vs-35 open gate")
    check("limit=100" in d8 and "limit=100" in human
          and "agent-facing S1 request contract" in human and "normative provider max depth" in human, D8,
          "d8_limit_100_runtime_specific", "limit=100",
          "current D8 limit=100 must be scoped as runtime-specific, not agent/provider max semantics")

    rows = {(r.get("provider"), r.get("product")): r for r in providers.get("contracts", [])}
    srow = rows.get(("kraken", "Spot Order Book"), {})
    frow = rows.get(("kraken", "Futures Raw L2 Order Book"), {})
    check(srow.get("current_aife_raw_book_resource") == "ABSENT"
          and srow.get("grouped_book_equals_aife_profile") is False, PROVIDERS,
          "provider_kraken_spot_boundary", srow, "provider contract must keep Spot RAW absent and GroupedBook != PROFILE")
    check(frow.get("selectable_depth_limit") == "NOT_NORMATIVELY_DOCUMENTED"
          and frow.get("pf_substitution_for_pi") is False, PROVIDERS,
          "provider_kraken_futures_boundary", frow, "provider contract must not invent max depth or allow PF->PI")

    sem = bridge.get("semantic_resolution", {})
    check(sem.get("status") == "ACTIVE"
          and sem.get("discovery_route_authority") == "canonical_paths.capability_index"
          and sem.get("resolver", {}).get("interface") == "tools/capability_index.py"
          and sem.get("resolver", {}).get("resolution_plan_schema") == "market-data-resolution-plan/1.0.0"
          and sem.get("reader", {}).get("interface") == "tools/history_access.py"
          and sem.get("reader", {}).get("input_authority") == "ResolutionPlan"
          and sem.get("consumer", {}).get("interface") == "tools/history_consumer.py"
          and sem.get("current_data", {}).get("acquisition", {}).get("producer") == "src/collector.py"
          and sem.get("current_data", {}).get("acquisition", {}).get("second_collector") is False
          and sem.get("current_data", {}).get("series_output", {}).get("resolver") == "tools/capability_index.py"
          and sem.get("current_data", {}).get("series_output", {}).get("reader") == "tools/history_access.py"
          and sem.get("current_data", {}).get("series_output", {}).get("resolution_plan") == "market-data-resolution-plan/1.0.0"
          and sem.get("current_data", {}).get("series_output", {}).get("second_resolver") is False
          and sem.get("current_data", {}).get("series_output", {}).get("second_reader") is False
          and bridge.get("no_silent_provider_substitution") is True, "bridge-contract.json",
          "active_d6_route_unchanged", sem, "additive S1 pointer must not alter resolver/reader/collector/default plan")

    check("MACHINE_AUTHORITY=contracts/liquidity-s1-semantic-contract-v1.json" in human, HUMAN,
          "human_machine_owner", "present", "human S1 doc must point to machine owner")
    check("S1 liquidity — additive semantic extension" in capability, CAPABILITY,
          "single_capability_contour", "present", "capability doc must preserve additive one-contour semantics")
    check("OD01_STATUS=OPEN_TRACKED_INTEGRATION_GATE" in current, CURRENT,
          "current_data_od01", "present", "fresh-current owner must keep OD-01 visible")
    mutations = _mapping(human)
    for owner, statuses in mutations.items():
        if "CURRENTIZE" in statuses:
            check(owner in CURRENT_TASK_CURRENTIZE_PATHS, HUMAN,
                  "mapping_currentize_physical_truth", {"owner": owner, "statuses": sorted(statuses)},
                  "CURRENTIZE may only name a path physically mutated by current PR #295 task")
    check("NO_CHANGE_ALREADY_COMPATIBLE" in mutations.get(D8, set())
          and "CURRENTIZE" not in mutations.get(D8, set()), HUMAN,
          "mapping_d8_truth", mutations.get(D8, set()), "D8 is compatible and not physically currentized")
    check("HISTORICAL_REFERENCE_ONLY" in mutations.get(CVD, set())
          and "CURRENTIZE" not in mutations.get(CVD, set()), HUMAN,
          "mapping_cvd_truth", mutations.get(CVD, set()), "CVD doc is reference-only for this task")
    check("CURRENTIZE" in mutations.get(D9, set()), HUMAN,
          "mapping_d9_truth", mutations.get(D9, set()), "D9 hierarchy is physically currentized")

    for key, value in c.get("installation_boundaries", {}).items():
        check(value is False, S1, f"installation_boundary_{key}", value,
              "governance/SSOT repair cannot activate runtime/provider behavior")

    for path in active:
        text = _text(path, root, overrides)
        for invariant, pattern in CONTROL_CONTRADICTIONS:
            match = pattern.search(text)
            if match:
                bad(path, invariant, match.group(0), "active/current artifact contains contradictory control declaration")

    stats = {
        "audited_path_count": len(corpus),
        "active_current_path_count": len(active),
        "historical_excluded_count": len(historical),
    }
    return findings, stats


def main() -> None:
    findings, stats = audit_active_current_semantics()
    for item in findings:
        print("SSOT_CONTRADICTION "
              f"path={item['path']} classification={item['classification']} "
              f"invariant={item['invariant']} "
              f"matched_current_semantic={json.dumps(item['matched_current_semantic'], ensure_ascii=False)} "
              f"reason={json.dumps(item['reason'], ensure_ascii=False)}")
    print(f"SSOT_AUDITED_PATH_COUNT={stats['audited_path_count']}")
    print(f"SSOT_ACTIVE_CURRENT_PATH_COUNT={stats['active_current_path_count']}")
    print(f"SSOT_HISTORICAL_EXCLUDED_COUNT={stats['historical_excluded_count']}")
    print(f"ACTIVE_SSOT_CONTRADICTION_COUNT={len(findings)}")
    print("CONTRADICTION_COUNT_IS_COMPUTED=YES")
    if findings:
        raise RuntimeError(f"active S1 SSOT contradictions detected: {len(findings)}")
    for line in (
        "LIQUIDITY_S1_SSOT_CONTRACT=PASS",
        "CANONICAL_ENTRYPOINT_BINDING=PASS",
        "BRIDGE_CONTRACT_S1_DISCOVERABILITY=PASS",
        "MAPPING_TRACEABILITY=PASS",
        "ARCH_B_STATUS=RETAINED",
        "DYNAMIC_DEPTH_SEMANTICS=PASS",
        "RESOURCE_SATISFACTION=PASS",
        "ONE_COHERENT_OBSERVATION=PASS",
        "PROFILE_500_BPS_EXPRESSIBLE=YES",
        "SIDE_SPECIFIC_COVERAGE=PASS",
        "BOOK_KIND_MODEL=PASS",
        "KRAKEN_BOUNDARIES=PASS",
        "NATIVE_FIRST_QUANTITY=PASS",
        "OBSERVATION_VALUE_VALIDITY=PASS",
        "PROVIDER_NATIVE_VS_CONSUMER_QUALIFIED=PASS",
        "DOWNSTREAM_VALIDITY=PASS",
        "S1_S2_S3_BOUNDARY=PASS",
        "OD01_OPEN_GATE=PASS",
        "ACTIVE_ROUTE_UNCHANGED=PASS",
        "NO_PROVIDER_ROLLOUT=PASS",
        "LIQUIDITY_S1_SSOT_VALIDATION=PASS",
    ):
        print(line)


if __name__ == "__main__":
    main()
