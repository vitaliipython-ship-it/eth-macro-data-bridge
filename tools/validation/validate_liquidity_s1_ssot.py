from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
S1 = "contracts/liquidity-s1-semantic-contract-v1.json"
HUMAN = "docs/semantics/liquidity-s1-semantic-contract-v1.md"
PROVIDERS = "contracts/provider-contracts.json"
CURRENT = "docs/semantics/fresh-current-agent-transport-v1.md"
CAPABILITY = "docs/semantics/capability-index.md"
D9 = "docs/semantics/d9-operational-status-and-agent-usage-v1.md"
D8_WORKFLOW = ".github/workflows/qualify-d8-runtime.yml"
UPDATE_WORKFLOW = ".github/workflows/update-market.yml"
CURRENT_WORKFLOW = ".github/workflows/current-data-request.yml"
REQUEST_SCOPE = "tools/current_data_request_scope.py"
VALIDATE_V4 = "tools/validation/validate_v4.py"
KRAKEN_FLOW = "src/kraken_trade_flow.py"
ACTIVE = {"AGENTS.md", "bridge-contract.json", S1, PROVIDERS, HUMAN, CURRENT, CAPABILITY, D9,
          D8_WORKFLOW, UPDATE_WORKFLOW, CURRENT_WORKFLOW, REQUEST_SCOPE, VALIDATE_V4, KRAKEN_FLOW}
HIST_DIRS = ("docs/handoffs", "AIFE/evidence", "AIFE/staging")
CURRENTIZED = {"AGENTS.md", "bridge-contract.json", PROVIDERS, CAPABILITY, CURRENT, D9}


def _text(path: str, root: Path, overrides: Mapping[str, str] | None) -> str:
    if overrides and path in overrides:
        return overrides[path]
    return (root / path).read_text(encoding="utf-8")


def _json(path: str, root: Path, overrides: Mapping[str, str] | None):
    return json.loads(_text(path, root, overrides))


def classify_path(path: str) -> str:
    if path in ACTIVE:
        return "ACTIVE_CURRENT"
    if any(path.startswith(prefix + "/") for prefix in HIST_DIRS):
        return "HISTORICAL_EXCLUDED"
    return "OUT_OF_SCOPE"


def discover_audit_corpus(root: Path = ROOT) -> list[str]:
    found = {p for p in ACTIVE if (root / p).is_file()}
    for dirname in HIST_DIRS:
        base = root / dirname
        if base.exists():
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in {".md", ".json", ".py", ".txt", ".yml", ".yaml"}:
                    found.add(p.relative_to(root).as_posix())
    return sorted(found)


def _mapping(human: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for line in human.splitlines():
        if not line.startswith("|") or "`" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        for owner in re.findall(r"`([^`]+)`", cells[1]):
            out.setdefault(owner, set()).add(cells[3])
    return out


def audit_active_current_semantics(root: Path = ROOT, overrides: Mapping[str, str] | None = None):
    corpus = discover_audit_corpus(root)
    active = [p for p in corpus if classify_path(p) == "ACTIVE_CURRENT"]
    historical = [p for p in corpus if classify_path(p) == "HISTORICAL_EXCLUDED"]
    findings: list[dict[str, str]] = []

    def check(ok: bool, path: str, invariant: str, detail: object) -> None:
        if not ok:
            findings.append({"path": path, "classification": classify_path(path),
                             "invariant": invariant, "detail": repr(detail)})

    c = _json(S1, root, overrides)
    bridge = _json("bridge-contract.json", root, overrides)
    providers = _json(PROVIDERS, root, overrides)
    agents = _text("AGENTS.md", root, overrides)
    human = _text(HUMAN, root, overrides)
    current = _text(CURRENT, root, overrides)
    capability = _text(CAPABILITY, root, overrides)
    d9 = _text(D9, root, overrides)
    d8wf = _text(D8_WORKFLOW, root, overrides)
    update = _text(UPDATE_WORKFLOW, root, overrides)
    curwf = _text(CURRENT_WORKFLOW, root, overrides)
    scope = _text(REQUEST_SCOPE, root, overrides)
    v4 = _text(VALIDATE_V4, root, overrides)
    kflow = _text(KRAKEN_FLOW, root, overrides)

    check(c.get("contract_id") == "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1", S1, "machine_owner_id", c.get("contract_id"))
    check(c.get("status") == "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE" and c.get("runtime_active") is False,
          S1, "runtime_inactive", {"status": c.get("status"), "runtime_active": c.get("runtime_active")})
    ptr = bridge.get("semantic_contracts", {}).get("liquidity_s1")
    check(ptr == {"contract_id": "ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1", "path": S1,
                  "status": "ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE", "runtime_active": False},
          "bridge-contract.json", "bridge_s1_discoverability", ptr)
    chain = "AGENTS.md\n→ bridge-contract.json\n→ semantic_contracts.liquidity_s1\n→ contracts/liquidity-s1-semantic-contract-v1.json"
    check(chain in agents and "runtime_active=false" in agents, "AGENTS.md", "canonical_entrypoint_binding", chain in agents)

    arch = c.get("architecture", {})
    check(arch.get("model") == "ARCH_B_CAPABILITY_SELECTIVE_EXTENSION" and arch.get("market_data_foundation_contour_count") == 1,
          S1, "arch_b_single_contour", arch)
    for key in ("second_catalog", "second_resolver", "second_reader", "second_collector", "second_refresh_transport",
                "second_capability_authority", "second_provider_authority", "second_market_data_authority"):
        check(arch.get(key) is False, S1, "no_" + key, arch.get(key))

    stages = c.get("stage_boundaries", {})
    check(stages.get("request_aware_network_acquisition") == "NOT_IMPLEMENTED_BY_S1" and
          stages.get("S1", {}).get("provider_network_rollout") is False and
          stages.get("S2", {}).get("active_in_this_contract_installation") is False and
          stages.get("S3", {}).get("active_in_this_contract_installation") is False,
          S1, "s1_s2_s3_boundary", stages)
    dynamic = c.get("dynamic_depth_acquisition_plan", {})
    check(dynamic.get("flow") == ["SEMANTIC_COVERAGE_REQUEST", "RESOURCE_SATISFACTION_CHECK",
                                  "DYNAMIC_DEPTH_ACQUISITION_PLANNER", "EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN",
                                  "ONE_COHERENT_PROVIDER_OBSERVATION"], S1, "resource_satisfaction_before_network", dynamic.get("flow"))
    req = dynamic.get("semantic_request", {})
    planner = dynamic.get("planner", {})
    check({250, 500} <= set(req.get("minimum_required_target_bps_examples", [])) and
          req.get("provider_specific_depth_or_level_limit_is_agent_knowledge") is False,
          S1, "dynamic_depth_250_500", req)
    check(planner.get("exactly_one_provider_acquisition_plan_per_observation") is True and
          planner.get("sequential_rest_depth_escalation_stitched_as_one_observation") == "FORBIDDEN" and
          planner.get("s1_executes_network") is False, S1, "one_coherent_provider_observation", planner)
    reuse = c.get("resource_satisfaction", {})
    check(reuse.get("check_before_network_acquisition") is True and reuse.get("reacquire_when_dominating_resource_exists") is False,
          S1, "resource_dominance_reuse", reuse)

    cov = c.get("coverage", {})
    required_cov = {"requested_bid_coverage_bps", "requested_ask_coverage_bps", "achieved_bid_coverage_bps",
                    "achieved_ask_coverage_bps", "coverage_complete_bid", "coverage_complete_ask", "truncated"}
    ex = cov.get("incomplete_example", {})
    check(required_cov <= set(cov.get("side_specific_fields", [])) and cov.get("no_extrapolation_outside_observed_book") is True and
          ex.get("requested_bid_coverage_bps") == 500 and ex.get("requested_ask_coverage_bps") == 500 and
          ex.get("achieved_bid_coverage_bps") == 230 and ex.get("achieved_ask_coverage_bps") == 410 and
          ex.get("coverage_complete_bid") is False and ex.get("coverage_complete_ask") is False and
          ex.get("truncated") is True and ex.get("extrapolation_allowed") is False,
          S1, "side_specific_coverage_no_extrapolation", {"fields": cov.get("side_specific_fields"), "example": ex})

    books = c.get("book_kind", {})
    check(books.get("kraken_grouped_book_equals_aife_profile") is False and books.get("l3_equals_ordinary_l2_raw") is False and
          set(books.get("representations", [])) == {"RAW", "NORMALIZED", "PROFILE", "SUMMARY"},
          S1, "book_kind_vs_representation", books)
    qty = c.get("derivatives_quantity", {})
    check(qty.get("model") == "PRODUCT_AWARE_NATIVE_FIRST" and qty.get("universal_provider_qty_to_base_quantity_mapping") == "FORBIDDEN" and
          qty.get("base_equivalent_nullable") is True and qty.get("quote_equivalent_nullable") is True and
          qty.get("consumer_qualified_equivalent_when_conversion_unproven") is False,
          S1, "native_first_derivatives_quantity", qty)

    bounds = c.get("provider_boundaries", {})
    check(bounds.get("kraken_spot", {}).get("raw_book_in_current_bridge") == "ABSENT", S1, "kraken_spot_raw_not_active", bounds.get("kraken_spot"))
    fut = bounds.get("kraken_futures", {})
    check(fut.get("raw_l2_book") == "PROVIDER_CAPABILITY_CONFIRMED" and fut.get("selectable_depth_limit") == "NOT_NORMATIVELY_DOCUMENTED" and
          fut.get("pf_may_substitute_for_pi") is False, S1, "kraken_futures_depth_identity", fut)

    validity = c.get("observation_value_validity", {})
    flow = c.get("kraken_futures_trade_flow", {})
    check({"VALID_ZERO", "UNAVAILABLE", "NOT_QUALIFIED", "SOURCE_CONFLICT", "MISALIGNED", "UNKNOWN", "PARTIAL", "INCOMPLETE"} <= set(validity.get("states", [])) and
          validity.get("unobserved_data_may_masquerade_as_observed_zero") is False and
          flow.get("trade_count", {}).get("mismatch") == "SOURCE_CONFLICT" and
          flow.get("cvd", {}).get("raw_delta_state_equivalence") == "NOT_QUALIFIED" and
          flow.get("l2_derived_executed_trades") is False and flow.get("cvd_reconstruction_or_reset_for_current_raw_value_qualification") is False,
          S1, "pr283_fail_closed_semantics", {"validity": validity, "flow": flow})
    check("VALID_ZERO" in kflow and "SOURCE_CONFLICT" in kflow and "NOT_QUALIFIED" in kflow, KRAKEN_FLOW, "pr283_runtime_markers", "markers")

    cur = c.get("currentization", {})
    rel = set(cur.get("pr299_request_scope_semantics", {}).get("failure_relevance_classes", []))
    check(cur.get("current_main_successors_preserved") is True and cur.get("pr283_fail_closed_semantics_preserved") is True and
          rel == {"GLOBAL_STRUCTURAL", "REQUESTED_RESOURCE", "REQUESTED_DOMAIN", "UNREQUESTED_RESOURCE"} and
          cur.get("pr299_request_scope_semantics", {}).get("unrelated_degraded_metric_poisoning_forbidden") is True,
          S1, "pr299_request_scope_preserved", cur)
    for marker in ("GLOBAL_STRUCTURAL", "REQUESTED_RESOURCE", "REQUESTED_DOMAIN", "UNREQUESTED_RESOURCE"):
        check(marker in scope, REQUEST_SCOPE, "request_scope_relevance_" + marker.lower(), marker)
    check("generation_integrity" in curwf and "request_satisfaction" in curwf and
          "GENERATION_INTEGRITY_VS_REQUEST_SATISFACTION=SEPARATED" in v4,
          CURRENT_WORKFLOW, "generation_integrity_request_satisfaction_separated", "markers")
    check("request_type" in current and "build-request" in current and "parse-request" in current and "remote Issue read-back" in current,
          CURRENT, "canonical_invocation_preserved", "markers")

    check(c.get("od01") is None and cur.get("stale_od01_reintroduced") is False and
          "OD01_STATUS=" not in human and "OD01_OPEN_SCHEDULE_MISMATCH" not in human and
          "OD01_STATUS=" not in current and "OD01_OPEN_SCHEDULE_MISMATCH" not in current,
          S1, "stale_od01_not_reintroduced", {"contract_od01": c.get("od01"), "flag": cur.get("stale_od01_reintroduced")})
    check(re.search(r'cron:\s*"[0-5]?\d \* \* \* \*"', update) is not None,
          UPDATE_WORKFLOW, "current_hourly_cadence_preserved", "hourly")

    repaired_state = "REPAIRED_ACTUAL_SYNTHETIC_PARENT_AUTHORITY"
    check(
        'QUALIFIED_CHECKOUT_SHA="$(git rev-parse HEAD)"' in d8wf and
        'test "$QUALIFIED_CHECKOUT_SHA" = "$GITHUB_SHA"' in d8wf and
        'ACTUAL_TESTED_BASE_SHA="${parents[0]}"' in d8wf and
        'ACTUAL_TESTED_PR_HEAD_SHA="${parents[1]}"' in d8wf and
        'test "$ACTUAL_TESTED_PR_HEAD_SHA" = "$EVENT_PR_HEAD_SHA"' in d8wf and
        'test "$ACTUAL_TESTED_BASE_SHA" = "$EVENT_PR_BASE_SHA"' not in d8wf and
        'test "${parents[0]}" = "$PR_BASE_SHA_FROM_EVENT"' not in d8wf and
        "EVENT_BASE_DIFFERS_FROM_ACTUAL_TESTED_BASE=YES" in d8wf and
        "PR_EFFECTIVE_INTEGRATION_BINDING=PASS" in d8wf and
        "PHYSICAL_IDENTITY_PROOF=PASS" in d8wf and
        cur.get("d8_residual_synthetic_parent1_event_base_race") == repaired_state and
        f"D8_PR_SYNTHETIC_PARENT1_EVENT_BASE_RACE={repaired_state}" in human and
        "D8_PR_SYNTHETIC_PARENT1_EVENT_BASE_RACE=RECORDED_NOT_REPAIRED" not in human,
        D8_WORKFLOW, "d8_provenance_repaired_actual_synthetic_parent_authority", repaired_state,
    )

    rows = {(r.get("provider"), r.get("product")): r for r in providers.get("contracts", [])}
    spot = rows.get(("kraken", "Spot Order Book"), {})
    frow = rows.get(("kraken", "Futures Raw L2 Order Book"), {})
    check(spot.get("current_aife_raw_book_resource") == "ABSENT" and spot.get("grouped_book_equals_aife_profile") is False,
          PROVIDERS, "provider_spot_boundary", spot)
    check(frow.get("selectable_depth_limit") == "NOT_NORMATIVELY_DOCUMENTED" and frow.get("pf_substitution_for_pi") is False,
          PROVIDERS, "provider_futures_boundary", frow)

    check("S1 liquidity — additive semantic extension" in capability, CAPABILITY, "single_capability_contour", "section")
    check("contracts/liquidity-s1-semantic-contract-v1.json" in d9 and "runtime_active=false" in d9, D9, "d9_s1_discoverability", "section")
    mapping = _mapping(human)
    for owner, statuses in mapping.items():
        if "CURRENTIZE" in statuses:
            check(owner in CURRENTIZED, HUMAN, "mapping_currentize_physical_truth", {owner: sorted(statuses)})

    positive = re.compile(r'(?im)^\s*(SECOND_(?:COLLECTOR|RESOLVER|READER|MARKET_DATA_AUTHORITY)|LIQUIDITY_RUNTIME_ACTIVE|S2_PROVIDER_ROLLOUT|S3_NETWORK_ACTIVATION)\s*=\s*(YES|TRUE|ACTIVE)\s*$')
    for path in active:
        text = _text(path, root, overrides)
        m = positive.search(text)
        if m:
            check(False, path, "active_positive_forbidden_control", m.group(0))

    return findings, {"audited_path_count": len(corpus), "active_current_path_count": len(active),
                      "historical_excluded_count": len(historical)}


def main() -> int:
    findings, stats = audit_active_current_semantics(ROOT)
    print(f"SSOT_AUDITED_PATH_COUNT={stats['audited_path_count']}")
    print(f"SSOT_ACTIVE_CURRENT_PATH_COUNT={stats['active_current_path_count']}")
    print(f"SSOT_HISTORICAL_EXCLUDED_COUNT={stats['historical_excluded_count']}")
    print(f"ACTIVE_SSOT_CONTRADICTION_COUNT={len(findings)}")
    print("CONTRADICTION_COUNT_IS_COMPUTED=YES")
    if findings:
        for item in findings:
            print("CONTRADICTION=" + json.dumps(item, ensure_ascii=False, sort_keys=True))
        return 1
    for marker in ("LIQUIDITY_S1_SSOT_CONTRACT=PASS", "CANONICAL_ENTRYPOINT_BINDING=PASS",
                   "BRIDGE_CONTRACT_S1_DISCOVERABILITY=PASS", "MAPPING_TRACEABILITY=PASS",
                   "ARCH_B_STATUS=RETAINED", "ACTIVE_ROUTE_UNCHANGED=PASS", "NO_PROVIDER_ROLLOUT=PASS",
                   "DYNAMIC_DEPTH_SEMANTICS=PASS", "RESOURCE_SATISFACTION_BEFORE_NETWORK=PASS",
                   "ONE_COHERENT_PROVIDER_OBSERVATION=PASS", "SIDE_SPECIFIC_COVERAGE=PASS",
                   "NO_BOOK_EXTRAPOLATION=PASS", "BOOK_KIND_VS_REPRESENTATION=SEPARATED",
                   "DERIVATIVES_QUANTITY_NATIVE_FIRST=PASS", "PR283_FAIL_CLOSED_SEMANTICS=PRESERVED",
                   "PR299_REQUEST_SCOPE_SEMANTICS=PRESERVED", "S1_CURRENTIZATION_DOES_NOT_REINTRODUCE_STALE_OD01=PASS",
                   "D8_PROVENANCE_SYNTHETIC_PARENT_AUTHORITY=REPAIRED"):
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# DB-F/S3 R01: DB-F/S3 candidate preserves S1 semantic ownership and adds no S1 network I/O
