from __future__ import annotations

import hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path.cwd(); OLD="adab4813cf7b5c8144097c3840b8eff8d93bcd97"
S1="contracts/liquidity-s1-semantic-contract-v1.json"; HUMAN="docs/semantics/liquidity-s1-semantic-contract-v1.md"
TEST="tests/test_liquidity_s1_ssot.py"; VALIDATOR="tools/validation/validate_liquidity_s1_ssot.py"

def old(path): return subprocess.check_output(["git","show",f"{OLD}:{path}"],text=True)
def write(path,text):
 p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
def dump(v): return json.dumps(v,ensure_ascii=False,separators=(",",":"))+"\n"
def pretty(v): return json.dumps(v,ensure_ascii=False,indent=2)+"\n"

# Current main bytes are base authority. Add bounded S1 discoverability only.
p=ROOT/"AGENTS.md"; t=p.read_text(encoding="utf-8")
if "→ semantic_contracts.liquidity_s1" not in t:
 block='''## Liquidity S1 semantic architecture\n\nCanonical discoverability chain для принятой S1 liquidity architecture:\n\n```text\nAGENTS.md\n→ bridge-contract.json\n→ semantic_contracts.liquidity_s1\n→ contracts/liquidity-s1-semantic-contract-v1.json\n```\n\n`contracts/liquidity-s1-semantic-contract-v1.json` — additive machine owner S1 semantic architecture внутри существующего Market Data Foundation. Status `ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE`, `runtime_active=false`. Он не меняет active D6/ResolutionPlan v1 route, не создаёт второй collector/catalog/resolver/reader/market-data authority и не активирует S2/S3 provider/network execution.\n\n'''
 marker="## Fresh/current market-data requests\n"; assert marker in t; p.write_text(t.replace(marker,block+marker,1),encoding="utf-8")

p=ROOT/"bridge-contract.json"; b=json.loads(p.read_text(encoding="utf-8")); b.setdefault("semantic_contracts",{})["liquidity_s1"]={"contract_id":"ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1","path":S1,"status":"ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE","runtime_active":False}; p.write_text(dump(b),encoding="utf-8")

# Preserve current provider rows; add only S1 provider/API facts and accepted PR283 value-qualification envelope.
p=ROOT/"contracts/provider-contracts.json"; obj=json.loads(p.read_text(encoding="utf-8")); rows=obj["contracts"]
for r in rows:
 if r.get("provider")=="kraken" and r.get("product")=="Futures Market Analytics":
  r["current_trade_flow_value_qualification"]={"trade_count":"RAW_EXECUTION_RECONCILIATION_QUALIFIED_BUCKET_END_MATCH_REQUIRED","trade_volume":"PROVIDER_NATIVE_PRESENT_RAW_HISTORY_SIZE_TO_ANALYTICS_BASE_VOLUME_EQUIVALENCE_NOT_QUALIFIED","aggressor_differential":"TAKER_SIDE_SIGN_UNDERSTOOD_PI_RAW_SIZE_QUANTITY_UNIT_EQUIVALENCE_NOT_QUALIFIED","cvd":"PROVIDER_NATIVE_STATE_RAW_DELTA_STATE_EQUIVALENCE_NOT_QUALIFIED"}
rows[:]=[r for r in rows if r.get("product") not in {"Spot Order Book","Futures Raw L2 Order Book"}]
spot={"provider":"kraken","product":"Spot Order Book","endpoint":"REST_L2; WS_V2_L2_SELECTABLE_DEPTH; PROVIDER_NATIVE_GROUPED_L2; AUTHENTICATED_L3","purpose":"spot order-book capability boundary for future S1/S2/S3 liquidity extension","authentication_required":"L2_NO; L3_YES","historical_support":"NOT_CLAIMED_BY_S1_CONTRACT","native_resolution":"POINT_IN_TIME_BOOK_STATE","field_mapping":"L2 level book, provider grouped L2 and authenticated L3 remain distinct semantic book kinds/surfaces","rate_limit":"PROVIDER_ROUTE_SPECIFIC_TO_BE_QUALIFIED_BY_S2_ADAPTER","source_documentation":"KRAKEN_FIRST_PARTY_SPOT_API_ACCEPTED_RESEARCH_EVIDENCE","provider_raw_book_capability":"AVAILABLE_EXTERNALLY","current_aife_raw_book_resource":"ABSENT","grouped_book_equals_aife_profile":False,"l3_status":"FUTURE_FORENSIC_SUCCESSOR_REQUIRES_SEPARATE_AUTHORIZATION"}
fut={"provider":"kraken","product":"Futures Raw L2 Order Book","endpoint":"PROVIDER_RAW_L2_CAPABILITY_CONFIRMED_EXACT_ADAPTER_ROUTE_TO_BE_QUALIFIED_IN_S2","purpose":"future raw futures order-book acquisition for PI_ETHUSD and PI_XBTUSD","authentication_required":"PROVIDER_ROUTE_SPECIFIC_TO_BE_QUALIFIED_IN_S2","historical_support":"NOT_CLAIMED_BY_S1_CONTRACT","native_resolution":"POINT_IN_TIME_BOOK_STATE","field_mapping":"provider-native levels preserved; product-aware native quantity semantics required","rate_limit":"PROVIDER_ROUTE_SPECIFIC_TO_BE_QUALIFIED_IN_S2","source_documentation":"KRAKEN_FIRST_PARTY_FUTURES_API_ACCEPTED_RESEARCH_EVIDENCE","provider_raw_l2_capability":"CONFIRMED","selectable_depth_limit":"NOT_NORMATIVELY_DOCUMENTED","normative_max_depth":"NOT_INVENTED","required_initial_product_identities":["PI_ETHUSD","PI_XBTUSD"],"pf_substitution_for_pi":False}
i=next((i for i,r in enumerate(rows) if r.get("provider")=="deribit"),len(rows)); rows[i:i]=[spot,fut]; p.write_text(pretty(obj),encoding="utf-8")

# Machine S1 owner from predecessor semantic delta, but remove stale OD-01 exact-minute state and strengthen current coverage/request semantics.
c=json.loads(old(S1)); c.pop("od01",None); c["runtime_active"]=False; c["architecture"]["second_market_data_authority"]=False
c["coverage"]["side_specific_fields"]=["requested_bid_coverage_bps","requested_ask_coverage_bps","achieved_bid_coverage_bps","achieved_ask_coverage_bps","coverage_complete_bid","coverage_complete_ask","truncated"]
c["coverage"]["coverage_complete_rule"]="BOTH_SIDES_MEET_REQUESTED_COVERAGE"; c["coverage"]["incomplete_example"]={"requested_bid_coverage_bps":500,"requested_ask_coverage_bps":500,"achieved_bid_coverage_bps":230,"achieved_ask_coverage_bps":410,"coverage_complete_bid":False,"coverage_complete_ask":False,"truncated":True,"extrapolation_allowed":False}
q=c["derivatives_quantity"]
for x in ("contract_quantity","quote_equivalent","consumer_qualified_equivalent"):
 if x not in q["normalized_fields"]: q["normalized_fields"].append(x)
q["quote_equivalent_nullable"]=True; q["consumer_qualified_equivalent_when_conversion_unproven"]=False
c["currentization"]={"current_main_successors_preserved":True,"pr283_fail_closed_semantics_preserved":True,"pr299_request_scope_semantics":{"generation_integrity_distinct_from_metric_qualification":True,"metric_qualification_distinct_from_request_satisfaction":True,"failure_relevance_classes":["GLOBAL_STRUCTURAL","REQUESTED_RESOURCE","REQUESTED_DOMAIN","UNREQUESTED_RESOURCE"],"unrelated_degraded_metric_poisoning_forbidden":True,"broad_required_domain_does_not_make_every_known_metric_hard_requirement":True},"stale_od01_reintroduced":False,"current_d8_hourly_cadence_semantics_preserved":True,"exact_scheduler_minute_is_not_s1_authority":True,"d8_residual_synthetic_parent1_event_base_race":"RECORDED_NOT_REPAIRED"}
write(S1,pretty(c))

# Human S1 owner: preserve architecture text, remove predecessor OD-01 mismatch, currentize coverage and successor semantics.
h=old(HUMAN)
h=re.sub(r'\| OD-01 schedule mismatch .*?\n','| Current D8 hourly cadence / exact-minute non-authority | `.github/workflows/qualify-d8-runtime.yml` | current accepted cadence qualification | NO_CHANGE_ALREADY_COMPATIBLE | S1 does not mutate scheduler or D8 qualification |\n',h)
h=re.sub(r'\n## OD-01 — open integration gate\n.*?(?=\n## S1 / S2 / S3 terminal boundary)','\n## Current hourly scheduler boundary\n\nS1 не владеет exact scheduler minute и не восстанавливает predecessor `OD01_OPEN_SCHEDULE_MISMATCH`. Current D8 authority квалифицирует hourly cadence; `.github/workflows/update-market.yml` и `.github/workflows/qualify-d8-runtime.yml` этим task не изменяются.\n\n```text\nS1_CURRENTIZATION_DOES_NOT_REINTRODUCE_STALE_OD01=PASS\nSCHEDULER_MUTATION_BY_S1=NO\nD8_PR_SYNTHETIC_PARENT1_EVENT_BASE_RACE=RECORDED_NOT_REPAIRED\n```\n',h,flags=re.S)
h=h.replace('bid_coverage\nask_coverage\ncommon_complete_bps','requested_bid_coverage_bps\nrequested_ask_coverage_bps\nachieved_bid_coverage_bps\nachieved_ask_coverage_bps\ncoverage_complete_bid\ncoverage_complete_ask\ntruncated')
extra='''\n## Currentization after Fresh Current successors\n\nCurrent `main` successor semantics have priority. S1 preserves accepted PR #283 fail-closed value validity and PR #299 request-scoped qualification:\n\n```text\nGENERATION_INTEGRITY != METRIC_QUALIFICATION != REQUEST_SATISFACTION\nFAILURE_RELEVANCE=GLOBAL_STRUCTURAL | REQUESTED_RESOURCE | REQUESTED_DOMAIN | UNREQUESTED_RESOURCE\nUNRELATED_DEGRADED_METRIC_POISONS_SATISFIED_REQUEST=NO\nSOURCE_CONFLICT -> unavailable -> value=null\nNOT_QUALIFIED -> unavailable/not-qualified -> value=null\nUNOBSERVED != ZERO\nVALID_ZERO -> numeric 0 only when explicitly proven\n```\n\nDynamic depth remains semantic-only in S1. Provider/network execution is still S2/S3 work.\n'''
marker='\n## S1 / S2 / S3 terminal boundary'; assert marker in h; h=h.replace(marker,extra+marker,1); write(HUMAN,h)

# Additive current-main docs, never replay predecessor whole-file bytes.
p=ROOT/"docs/semantics/capability-index.md"; t=p.read_text(encoding="utf-8"); marker="## History/depth semantics\n"
if "## S1 liquidity — additive semantic extension" not in t:
 block='''## S1 liquidity — additive semantic extension\n\n`contracts/liquidity-s1-semantic-contract-v1.json` defines accepted non-runtime S1 semantics inside the same Market Data Foundation contour. It does not create a second catalog/resolver/reader/collector. Semantic depth requests (`target_bps=250/500`) are checked against existing canonical resource coverage before any future provider acquisition; provider-specific depth knobs are not agent request fields.\n\n'''; assert marker in t; p.write_text(t.replace(marker,block+marker,1),encoding="utf-8")

p=ROOT/"docs/semantics/d9-operational-status-and-agent-usage-v1.md"; t=p.read_text(encoding="utf-8"); marker='- route/provider policy authority: `bridge-contract.json`;\n'
if S1 not in t:
 add=marker+'- liquidity S1 architecture machine owner: `contracts/liquidity-s1-semantic-contract-v1.json` (`runtime_active=false`, additive, no D6/D9 activation);\n'; assert marker in t; p.write_text(t.replace(marker,add,1),encoding="utf-8")

p=ROOT/"docs/semantics/fresh-current-agent-transport-v1.md"; t=p.read_text(encoding="utf-8")
if "## Liquidity S1 request-scoped boundary" not in t:
 marker="## AIFE Server future compatibility\n"; block='''## Liquidity S1 request-scoped boundary\n\nS1 adds semantic liquidity coverage architecture without replacing Fresh Current transport. Accepted successor semantics remain:\n\n```text\nGENERATION_INTEGRITY != METRIC_QUALIFICATION != REQUEST_SATISFACTION\nGLOBAL_STRUCTURAL\nREQUESTED_RESOURCE\nREQUESTED_DOMAIN\nUNREQUESTED_RESOURCE\nUNRELATED_DEGRADED_RESOURCE_DOES_NOT_POISON_SATISFIED_REQUEST=YES\nBROAD_REQUIRED_DOMAIN_DOES_NOT_AUTOMATICALLY_REQUIRE_EVERY_KNOWN_METRIC=YES\n```\n\nCanonical `request_type=FRESH_CURRENT`, repository-owned builder/preflight and remote mutation read-back remain unchanged. PR #283 fail-closed value semantics (`SOURCE_CONFLICT`, `NOT_QUALIFIED`, unobserved != zero, proven `VALID_ZERO`) remain intact. S1 owner is `contracts/liquidity-s1-semantic-contract-v1.json`, `runtime_active=false`; S1 does not activate request-aware network depth acquisition.\n\n'''; assert marker in t; p.write_text(t.replace(marker,block+marker,1),encoding="utf-8")

# Existing canonical repository workflow gets S1 gate; no D8 workflow change.
p=ROOT/".github/workflows/validate-repository.yml"; t=p.read_text(encoding="utf-8")
if "Validate liquidity S1 canonical SSOT" not in t:
 marker='      - name: Compile source and tooling\n'; block='''      - name: Validate liquidity S1 canonical SSOT\n        run: |\n          python tools/validation/validate_liquidity_s1_ssot.py\n          python -m unittest discover -s tests -p 'test_liquidity_s1_ssot.py' -v\n'''; assert marker in t; p.write_text(t.replace(marker,block+marker,1),encoding="utf-8")

# Templates are temp carrier inputs, copied into candidate paths.
write(VALIDATOR,(ROOT/".tmp/s1_validator_template.py").read_text(encoding="utf-8")); write(TEST,(ROOT/".tmp/s1_test_template.py").read_text(encoding="utf-8"))

changed=[".github/workflows/validate-repository.yml","AGENTS.md","bridge-contract.json",S1,"contracts/provider-contracts.json","docs/semantics/capability-index.md","docs/semantics/d9-operational-status-and-agent-usage-v1.md","docs/semantics/fresh-current-agent-transport-v1.md",HUMAN,TEST,VALIDATOR]
m={"schema":"liquidity-s1-currentization-candidate/1.0.0","old_pr_head":OLD,"changed_paths":changed,"files":{}}
for path in changed:
 data=(ROOT/path).read_bytes(); m["files"][path]={"sha256":hashlib.sha256(data).hexdigest(),"size":len(data)}
write(".liquidity-s1-candidate-manifest.json",pretty(m)); print("LIQUIDITY_S1_CURRENTIZATION_BUILD=PASS"); print("CHANGED_PATH_COUNT=11")
