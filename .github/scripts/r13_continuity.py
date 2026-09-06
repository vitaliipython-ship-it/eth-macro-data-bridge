from datetime import timedelta
from decimal import Decimal
from tools.deep_history import kraken_spot_posttrade as p

GAP="PROVIDER_NO_TRADE_OMISSION"
S23="1fce3a71369382b3a6717baab50c6b0e94b52b8245baaa91c1c3c661b5ddf026"

def initial_cursor(start):
    return p.iso_utc(p.parse_utc(start)-timedelta(seconds=1))

def verify_segment(e):
    required={"schema_version":p.SOURCE_SCHEMA,"source_mode":p.SOURCE_MODE,"symbol":p.SYMBOL,
              "completion_status":"COMPLETE","cursor_monotonic":True,"trade_id_conflict_count":0,
              "gap_policy":GAP,"synthetic_fill":False}
    for key,value in required.items():
        if e.get(key)!=value:
            raise RuntimeError(f"source invariant {key}: {e.get(key)!r} != {value!r}")
    start,end=e["requested_start_utc"],e["requested_end_utc"]
    if e["segment_id"]!=p.segment_id(start,end):
        raise RuntimeError("segment identity mismatch")
    first,last=e.get("initial_cursor"),e.get("final_cursor")
    if not first or not last or not e.get("page_transcript_digest"):
        raise RuntimeError("cursor/pagination evidence missing")
    if first!=initial_cursor(start):
        raise RuntimeError("independent segment initial cursor mismatch")
    if p.timestamp_decimal(last)<=p.timestamp_decimal(first):
        raise RuntimeError("cursor did not advance")
    ft,lt=e.get("first_provider_trade_ts"),e.get("last_provider_trade_ts")
    if (ft is None)!=(lt is None):
        raise RuntimeError("partial trade boundary evidence")
    if ft:
        if not(p.timestamp_decimal(start)<=p.timestamp_decimal(ft)<=p.timestamp_decimal(lt)<p.timestamp_decimal(end)):
            raise RuntimeError("provider trade range/order failed")
        if p.timestamp_decimal(last)<p.timestamp_decimal(lt):
            raise RuntimeError("final cursor precedes last provider trade")
    return True

def verify_seam(left,right):
    if left["requested_end_utc"]!=right["requested_start_utc"]:
        raise RuntimeError("logical time-range seam gap/overlap")
    a,b=left.get("last_provider_trade_ts"),right.get("first_provider_trade_ts")
    if a and b and p.timestamp_decimal(a)>=p.timestamp_decimal(b):
        raise RuntimeError("provider execution ordering failed across logical seam")
    return True

def verify_segment_023(e):
    if e["segment_id"]!=S23 or e.get("execution_mode")!="RECOVERED_QUARTER_HIERARCHY" or e.get("recovery_mode")!="QUARTER_TO_MONTH_TO_FIXED_7D":
        raise RuntimeError("segment023 hierarchy lineage mismatch")
    if e.get("recovered_parent_build_a_b")!="PASS" or e.get("recovered_parent_assembly_determinism")!="PASS" or int(e.get("cross_month_provider_trade_id_conflicts",-1))!=0:
        raise RuntimeError("segment023 parent assembly failed")
    months=e.get("months",[])
    expected=[
        ("2021-04-01T00:00:00.000000Z","2021-05-01T00:00:00.000000Z"),
        ("2021-05-01T00:00:00.000000Z","2021-06-01T00:00:00.000000Z"),
        ("2021-06-01T00:00:00.000000Z","2021-07-01T00:00:00.000000Z"),
    ]
    if len(months)!=3: raise RuntimeError("segment023 month count")
    for i,(m,bound) in enumerate(zip(months,expected)):
        if (m.get("requested_start_utc"),m.get("requested_end_utc"))!=bound or m.get("status")!="PASS" or m.get("cursor_monotonic") is not True or int(m.get("trade_id_conflict_count",-1))!=0 or m.get("gap_policy")!=GAP or m.get("synthetic_fill") is not False:
            raise RuntimeError(f"segment023 month {i} invalid")
    if months[0].get("execution_mode")!="PRESERVED_R08_CALENDAR_MONTH" or months[0].get("provider_reacquisition")!="NO" or int(months[0].get("source_artifact_id",-1))!=9971292963:
        raise RuntimeError("segment023 April reuse invalid")
    may=months[1]; children=may.get("children",[])
    bounds=[
        ("2021-05-01T00:00:00.000000Z","2021-05-08T00:00:00.000000Z"),
        ("2021-05-08T00:00:00.000000Z","2021-05-15T00:00:00.000000Z"),
        ("2021-05-15T00:00:00.000000Z","2021-05-22T00:00:00.000000Z"),
        ("2021-05-22T00:00:00.000000Z","2021-05-29T00:00:00.000000Z"),
        ("2021-05-29T00:00:00.000000Z","2021-06-01T00:00:00.000000Z"),
    ]
    if may.get("execution_mode")!="FIXED_UTC_7D_SUBMONTH_FALLBACK" or len(children)!=5:
        raise RuntimeError("segment023 May hierarchy invalid")
    for i,(child,bound) in enumerate(zip(children,bounds)):
        if (child.get("requested_start_utc"),child.get("requested_end_utc"))!=bound or child.get("status")!="PASS" or child.get("cursor_monotonic") is not True or int(child.get("trade_id_conflict_count",-1))!=0 or child.get("gap_policy")!=GAP or child.get("synthetic_fill") is not False:
            raise RuntimeError(f"segment023 May child {i} invalid")
        if int(child.get("page_count",999999))>2164 or Decimal(str(child.get("elapsed_seconds")))>Decimal("3080.819716"):
            raise RuntimeError(f"segment023 May child {i} qualified boundary violation")
    if months[2].get("execution_mode")!="DIRECT_CALENDAR_MONTH":
        raise RuntimeError("segment023 June lineage invalid")
    return True
