import copy
from tools.deep_history import kraken_spot_posttrade as p
from r10_continuity import GAP,verify_segment,verify_seam

def fixture(start="2020-01-01T00:00:00.000000Z",end="2020-04-01T00:00:00.000000Z"):
    e={"schema_version":p.SOURCE_SCHEMA,"source_mode":p.SOURCE_MODE,"symbol":p.SYMBOL,
       "requested_start_utc":start,"requested_end_utc":end,"initial_cursor":"2019-12-31T23:59:59.000000Z",
       "final_cursor":"2020-03-31T20:00:00.000000000Z","first_provider_trade_ts":"2020-01-01T00:00:03.000000000Z",
       "last_provider_trade_ts":"2020-03-31T20:00:00.000000000Z","page_transcript_digest":"x",
       "completion_status":"COMPLETE","cursor_monotonic":True,"trade_id_conflict_count":0,"gap_policy":GAP,"synthetic_fill":False}
    e["segment_id"]=p.segment_id(start,end); return e

left=fixture(); verify_segment(left)
right=fixture("2020-04-01T00:00:00.000000Z","2020-07-01T00:00:00.000000Z")
right.update(initial_cursor="2020-03-31T23:59:59.000000Z",final_cursor="2020-06-30T22:00:00.000000000Z",
             first_provider_trade_ts="2020-04-01T00:00:04.000000000Z",last_provider_trade_ts="2020-06-30T22:00:00.000000000Z")
verify_segment(right); verify_seam(left,right)
assert left["final_cursor"]!=right["initial_cursor"]
for key,value in (("cursor_monotonic",False),("synthetic_fill",True)):
    broken=copy.deepcopy(left); broken[key]=value
    try: verify_segment(broken)
    except RuntimeError: pass
    else: raise AssertionError(f"malformed {key} evidence accepted")
broken=copy.deepcopy(right); broken["requested_start_utc"]="2020-04-02T00:00:00.000000Z"
try: verify_seam(left,broken)
except RuntimeError: pass
else: raise AssertionError("logical seam gap accepted")
print("REGRESSION_ORDINARY_QUARTER_SEAM=PASS")
print("REGRESSION_PROVIDER_NO_TRADE_TAIL=PASS")
print("REGRESSION_INDEPENDENT_CROSS_SEGMENT_CURSOR=PASS")
print("REGRESSION_MALFORMED_EVIDENCE_FAIL_CLOSED=PASS")
