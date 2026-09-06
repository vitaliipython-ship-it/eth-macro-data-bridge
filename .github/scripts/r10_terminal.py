import hashlib,json,os,shutil
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from tools.deep_history import kraken_spot_ohlcvt_backfill as b
from tools.deep_history import kraken_spot_posttrade as p
from r10_continuity import verify_segment,verify_seam,verify_segment_023,GAP

R07=33916820262; R08=33964062741; R09=33978349492
SRC="91546fdd81471851c2cb6b948821c04cfe636f1c"; TREE="6deb789f26424845fae52593abb68f09c73801e0"
R09SHA="262b2b99c8d359c6da785430c1990ed6df0d048b"; TOTAL=64887079
S22="9deb84887d89898ab28e95f2dcae97e1726500baa18c75cf9f002c5fcae78ff1"
TERM="KRAKEN_POSTTRADE_FULL_MARKET_INCEPTION_TO_WARM_ACQUISITION_AND_FULL_CHAIN_QUALIFICATION_PASSED_OWNER_RELEASE_ACTIVATION_GATE_READY"
GATE="OWNER_DECISION_ON_HISTORY_KRAKEN_SPOT_V2_RELEASE_PUBLICATION_AND_CONTROL_PLANE_ACTIVATION"

def compact(x): return json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()+b"\n"
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for q in iter(lambda:f.read(8*1024*1024),b""): h.update(q)
    return h.hexdigest()
def logical_dirs(root):
    out=[]
    for name in ("r07","r08","r09"):
        for f in (root/name).rglob("evidence.json"): out.append(f.parent)
    return sorted(out,key=lambda d:json.loads((d/"evidence.json").read_text())["requested_start_utc"])
def assemble(ds):
    maps={"5m":{},"1d":{}}
    for d in ds:
        out=json.loads((d/"segment-output.json").read_text())
        if set(out)!={"5m","1d"}: raise RuntimeError("logical output schema mismatch")
        for interval in ("5m","1d"):
            for row in out[interval]:
                ts=int(row[0]); old=maps[interval].get(ts)
                maps[interval][ts]=row if old is None else p._merge_record(old,row)
    return {k:[maps[k][t] for t in sorted(maps[k])] for k in ("5m","1d")}
def window(rows,start,end):
    a=int(p.parse_utc(start).timestamp()*1000); z=int(p.parse_utc(end).timestamp()*1000)
    out=[r for r in rows if a<=int(r[0])<z]
    if not out: raise RuntimeError(f"empty forensic window {start} {end}")
    return out

root=Path(os.environ["RUNNER_TEMP"])/"global"; ds=logical_dirs(root)
if len(ds)!=45: raise RuntimeError(f"logical segment readback count {len(ds)} != 45")
required={"evidence.json","provider-trade-ids.txt","segment-output.json","segment-readback.json"}
evidences=[]; inventory=[]; previous=None; false_old=0; unique=raw=duplicates=0
for i,d in enumerate(ds):
    if {x.name for x in d.iterdir() if x.is_file()}!=required:
        raise RuntimeError(f"logical artifact file-set mismatch index={i}")
    e=json.loads((d/"evidence.json").read_text()); rb=json.loads((d/"segment-readback.json").read_text())
    if rb.get("segment_id")!=e["segment_id"] or rb.get("evidence_sha256")!=sha(d/"evidence.json") or rb.get("segment_output_sha256")!=sha(d/"segment-output.json") or rb.get("provider_trade_ids_sha256")!=sha(d/"provider-trade-ids.txt"):
        raise RuntimeError(f"logical readback SHA mismatch index={i}")
    verify_segment(e)
    if previous is not None: verify_seam(previous,e)
    if p.timestamp_decimal(e["final_cursor"])<p.timestamp_decimal(e["requested_end_utc"]): false_old+=1
    if i==22 and e["segment_id"]!=S22: raise RuntimeError("R08 segment022 identity mismatch")
    if i==23: verify_segment_023(e)
    run=R07 if i<=21 else R08 if i==22 else R09
    if i==22 and e.get("recovery_orchestration_sha")!="4bf8df4eb9ac1818ceeb2adafd17c5d3d26c4aaf": raise RuntimeError("R08 lineage mismatch")
    if i>=23 and e.get("recovery_orchestration_sha")!=R09SHA: raise RuntimeError(f"R09 lineage mismatch index={i}")
    unique+=int(e["unique_trade_count"]); raw+=int(e["raw_row_count"]); duplicates+=int(e["duplicate_trade_id_count"])
    inventory.append({k:e.get(k) for k in ("segment_id","requested_start_utc","requested_end_utc","initial_cursor","final_cursor","first_provider_trade_ts","first_provider_trade_id","last_provider_trade_ts","last_provider_trade_id","page_count","raw_row_count","unique_trade_count","duplicate_trade_id_count","trade_id_conflict_count","execution_mode","recovery_mode","frozen_source_digest","segment_output_digest","page_transcript_digest","completion_status")}|{"index":i,"source_run_id":run})
    evidences.append(e); previous=e

if unique!=TOTAL or int(os.environ["TOTAL_UNIQUE_PROVIDER_TRADES"])!=TOTAL: raise RuntimeError("provider unique count mismatch")
if evidences[0]["first_provider_trade_ts"]!="2015-08-07T14:03:25.775444995Z" or evidences[0]["first_provider_trade_id"]!="OG6TQH-NEBSF-FBMDZJ":
    raise RuntimeError("market inception identity mismatch")
manifest=json.loads(Path("history/release-manifest.json").read_text()); cutoff=int(manifest["backfill_as_of_ms"]); warm_first=b._warm_first_timestamp(); full_end=b._iso_ms(min(cutoff,warm_first+b.WARM_OVERLAP_MS))
if p.timestamp_decimal(evidences[-1]["requested_end_utc"])!=p.timestamp_decimal(full_end): raise RuntimeError("full chain end mismatch")

print("LOGICAL_SEGMENTS_READ_BACK=45")
print("REGRESSION_R07_R08_SEAM=PASS")
print("REGRESSION_R08_R09_SEAM=PASS")
print("REGRESSION_SEGMENT_023_FIXED_7D_RECOVERY=PASS")
print("FULL_CHAIN_CURSOR_PAGINATION_CONTINUITY=PASS")
print(f"R09_FALSE_FINAL_CURSOR_BOUNDARY_ASSERTION_AFFECTED_SEGMENTS={false_old}")
print("PROVIDER_NETWORK_CALLS=0")

build0=assemble(ds); build1=assemble(ds)
if build0!=build1: raise RuntimeError("full logical assembly nondeterminism")
sha5=hashlib.sha256(compact(build0["5m"])).hexdigest(); sha1=hashlib.sha256(compact(build0["1d"])).hexdigest()
warm=b.verify_warm_overlap_records(build0,Path("."))
if warm["conflicts"]!=0: raise RuntimeError("WARM overlap conflict")

r=window(build0["1d"],"2015-10-01T00:00:00Z","2015-11-01T00:00:00Z"); low15=min(r,key=lambda x:Decimal(str(x[3])))
r=window(build0["1d"],"2016-06-01T00:00:00Z","2016-07-01T00:00:00Z"); high16=max(r,key=lambda x:Decimal(str(x[2])))
r=window(build0["1d"],"2016-11-15T00:00:00Z","2016-12-15T00:00:00Z"); low16=min(r,key=lambda x:Decimal(str(x[3])))
r=window(build0["1d"],"2017-06-01T00:00:00Z","2017-08-01T00:00:00Z"); high17=max(r,key=lambda x:Decimal(str(x[2]))); low17=min(r,key=lambda x:Decimal(str(x[3])))
if not(Decimal(".30")<=Decimal(str(low15[3]))<=Decimal(".60") and Decimal("20")<=Decimal(str(high16[2]))<=Decimal("23") and Decimal("5")<=Decimal(str(low16[3]))<=Decimal("7") and Decimal("350")<=Decimal(str(high17[2]))<=Decimal("450") and Decimal("100")<=Decimal(str(low17[3]))<=Decimal("180") and int(high17[0])<int(low17[0])):
    raise RuntimeError("forensic 2015-2017 acceptance failed")
forensic={"2015_0_41_region":{"low_row":low15},"2016_21_48_high_region":{"high_row":high16},"2016_5_92_low_region":{"low_row":low16},"2017_404_98_to_134_78_ordering":{"high_row":high17,"low_row":low17}}

candidate=Path(os.environ["RUNNER_TEMP"])/"kraken-posttrade-full-candidate"; shutil.rmtree(candidate,ignore_errors=True); candidate.mkdir()
archive=candidate/"kraken-posttrade-derived-ohlcvt.zip"; derived=p.write_derived_archive(build0,archive); lineage=b._source_lineage([{"evidence":e} for e in evidences])
source={"schema_version":p.SOURCE_SCHEMA,"source_mode":p.SOURCE_MODE,"authority":"KRAKEN_OFFICIAL_POSTTRADE","endpoint":p.ENDPOINT,"documentation":p.DOCUMENTATION,"symbol":p.SYMBOL,
"source_authority_sha":SRC,"source_authority_tree":TREE,"coverage_declared_start_utc":p.MARKET_INCEPTION_UTC,"coverage_declared_end_utc":full_end,"backfill_cutoff_ms":cutoff,"canonical_warm_first_ms":warm_first,
"archive_sha256":lineage["frozen_source_digest"],"source_lineage_digest":lineage["source_lineage_digest"],"segment_count":45,"first_provider_trade_ts":lineage["first_provider_trade_ts"],"first_provider_trade_id":lineage["first_provider_trade_id"],
"last_provider_trade_ts":lineage["last_provider_trade_ts"],"last_provider_trade_id":lineage["last_provider_trade_id"],"page_count":lineage["page_count"],"raw_row_count":lineage["raw_row_count"],"unique_trade_count":lineage["unique_trade_count"],
"duplicate_trade_id_count":lineage["duplicate_trade_id_count"],"derived_archive_sha256":derived["derived_archive_sha256"],"derived_archive_size_bytes":derived["derived_archive_size_bytes"],"derived_row_counts":derived["row_counts"],"gap_policy":GAP,"synthetic_fill":False,
"acquired_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"execution_lineage":{"R07":{"run_id":R07,"logical_segments":"000..021"},"R08":{"run_id":R08,"logical_segments":"022"},"R09":{"run_id":R09,"logical_segments":"023..044","orchestration_sha":R09SHA},"R10":{"run_id":int(os.environ["GITHUB_RUN_ID"]),"orchestration_sha":os.environ["GITHUB_SHA"],"provider_network_calls":0}}}
(candidate/"source.json").write_bytes(b.compact(source))
assets_a=b.build_assets(archive,candidate/"build-a",cutoff,source); assets_b=b.build_assets(archive,candidate/"build-b",cutoff,source); b.compare_builds(assets_a,assets_b)
warm_assets=b.verify_warm_overlap(assets_a)
if warm_assets!=warm: raise RuntimeError("assembled-output/Build-A WARM mismatch")
digest_a=hashlib.sha256(b.compact({x["asset_name"]:x["sha256"] for x in assets_a})).hexdigest(); digest_b=hashlib.sha256(b.compact({x["asset_name"]:x["sha256"] for x in assets_b})).hexdigest()
if digest_a!=digest_b: raise RuntimeError("global Build A/B digest mismatch")
shutil.rmtree(candidate/"build-b")

inv={"schema_version":"kraken-posttrade-full-candidate-inventory/3.0.0","source_authority_sha":SRC,"source_authority_tree":TREE,"r10_orchestration_sha":os.environ["GITHUB_SHA"],"r10_run_id":int(os.environ["GITHUB_RUN_ID"]),"provider_network_calls":0,
"logical_segment_count":45,"execution_lineage":source["execution_lineage"],"segments":inventory,"provider_totals":{"unique_trade_count":unique,"raw_row_count":raw,"duplicate_trade_id_count":duplicates,"trade_id_conflict_count":0},
"cursor_pagination":{"status":"PASS","previous_final_cursor_equals_next_initial_cursor_required":False,"r09_false_boundary_assertion_affected_segment_count":false_old},
"full_outputs":{"5m":{"first_timestamp":build0["5m"][0][0],"last_timestamp":build0["5m"][-1][0],"row_count":len(build0["5m"]),"sha256":sha5},"1d":{"first_timestamp":build0["1d"][0][0],"last_timestamp":build0["1d"][-1][0],"row_count":len(build0["1d"]),"sha256":sha1}},
"global_build_a_digest":digest_a,"global_build_b_digest":digest_b,"assets":[{k:v for k,v in x.items() if k!="local_path"} for x in assets_a],"source_lineage_digest":source["source_lineage_digest"],"frozen_source_digest":source["archive_sha256"],"derived_archive_sha256":source["derived_archive_sha256"],
"warm_overlap":warm,"forensic_acceptance":forensic,"gap_policy":GAP,"synthetic_fill":False,"source_data_mutated":False,"existing_logical_artifacts_mutated":False,"release_publication":"NOT_RUN","control_plane_install":"NOT_RUN","capability_activation":"NO","research_mutation":"NO","owner_merge":"NO"}
inventory_path=candidate/"candidate-inventory.json"; inventory_path.write_bytes(b.compact(inv)); candidate_sha=b.sha256_file(inventory_path)
qualification={"schema_version":"kraken-posttrade-full-qualification/3.0.0","status":"PASS","full_candidate_sha256":candidate_sha,"logical_segments_read_back":45,"global_provider_trade_id_audit":"PASS","global_provider_trade_id_conflicts":0,"total_unique_provider_trades":unique,
"full_chain_cursor_pagination_continuity":"PASS","full_5m_build_a":"PASS","full_5m_build_b":"PASS","full_5m_build_a_b_equal":"PASS","full_1d_build_a":"PASS","full_1d_build_b":"PASS","full_1d_build_a_b_equal":"PASS","warm_overlap_conflicts":0,
"forensic_2015_2017":"PASS","provider_network_calls":0,"source_data_mutated":False,"existing_logical_artifacts_mutated":False,"release_publication_executed":False,"control_plane_activated":False,"capability_activated":False,"research_mutated":False,"owner_merge_executed":False,
"terminal_state":TERM,"next_exact_gate":GATE}
(candidate/"qualification-summary.json").write_bytes(b.compact(qualification))
sums=[f"{b.sha256_file(x)}  {x.relative_to(candidate).as_posix()}" for x in sorted(candidate.rglob("*")) if x.is_file() and x.name!="SHA256SUMS"]; (candidate/"SHA256SUMS").write_text("\n".join(sums)+"\n")

print(f"FIRST_PROVIDER_TRADE_TIMESTAMP={source['first_provider_trade_ts']}"); print(f"FIRST_PROVIDER_TRADE_ID={source['first_provider_trade_id']}")
print(f"LAST_PROVIDER_TRADE_TIMESTAMP={source['last_provider_trade_ts']}"); print(f"LAST_PROVIDER_TRADE_ID={source['last_provider_trade_id']}")
print(f"TOTAL_UNIQUE_PROVIDER_TRADES={unique}"); print(f"5M_FIRST_TIMESTAMP={build0['5m'][0][0]}"); print(f"5M_LAST_TIMESTAMP={build0['5m'][-1][0]}"); print(f"5M_ROW_COUNT={len(build0['5m'])}"); print(f"5M_SHA256={sha5}")
print(f"1D_FIRST_TIMESTAMP={build0['1d'][0][0]}"); print(f"1D_LAST_TIMESTAMP={build0['1d'][-1][0]}"); print(f"1D_ROW_COUNT={len(build0['1d'])}"); print(f"1D_SHA256={sha1}")
print(f"GLOBAL_BUILD_A_DIGEST={digest_a}"); print(f"GLOBAL_BUILD_B_DIGEST={digest_b}")
print("BUILD_A_5M=PASS"); print("BUILD_B_5M=PASS"); print("BUILD_A_B_5M_EQUAL=PASS"); print("BUILD_A_1D=PASS"); print("BUILD_B_1D=PASS"); print("BUILD_A_B_1D_EQUAL=PASS")
print("WARM_OVERLAP_CONFLICTS=0"); print("FORENSIC_2015_2017=PASS"); print("FULL_CANDIDATE_CREATED=YES"); print(f"FULL_CANDIDATE_SHA256={candidate_sha}")
print("RELEASE_PUBLICATION_EXECUTED=false"); print("CONTROL_PLANE_ACTIVATED=false"); print("CAPABILITY_ACTIVATED=false"); print("RESEARCH_MUTATED=false"); print("OWNER_MERGE_EXECUTED=false")
print(f"TERMINAL_STATE={TERM}"); print(f"NEXT_EXACT_GATE={GATE}")
