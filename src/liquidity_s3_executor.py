from __future__ import annotations

import http.client
import json
import re
import secrets
import ssl
import time
from typing import Any, Mapping
from urllib.parse import urlencode, urlsplit

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s2_binance_adapter import (
    BinanceS2Error,
    S2_PLAN_SCHEMA as BINANCE_PLAN_SCHEMA,
    build_binance_liquidity_resource,
    validate_binance_provider_plan,
)
from liquidity_s2_kraken_spot_adapter import (
    KrakenSpotS2Error,
    S2_PLAN_SCHEMA as KRAKEN_SPOT_PLAN_SCHEMA,
    build_kraken_spot_liquidity_resource,
    validate_kraken_spot_provider_plan,
)
from liquidity_s2_kraken_futures_adapter import (
    KrakenFuturesS2Error,
    S2_PLAN_SCHEMA as KRAKEN_FUTURES_PLAN_SCHEMA,
    build_kraken_futures_liquidity_resource,
    validate_kraken_futures_provider_plan,
)

S3_EXECUTION_RECEIPT_SCHEMA = "liquidity-s3-execution-receipt/1.0.0"
S3_EXECUTION_POLICY = {
    "automatic_retry_count": 0,
    "best_effort_close_timeout_ms": 2000,
    "connect_timeout_ms": 5000,
    "max_provider_observations_per_semantic_request": 1,
    "max_provider_requests_or_sessions_per_observation": 1,
    "max_raw_observation_bytes": 8388608,
    "max_ws_messages_before_terminal": 32,
    "rest_response_deadline_ms": 10000,
    "ws_initial_snapshot_deadline_ms": 10000,
}
S3_EXECUTION_POLICY_SHA256 = "2bfbfbbb389bdc5f7a2ac3f564dbcdebc64d07f2af991e80d39d6ac3cd2adbe2"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_FIELDS = {
    "schema_version","execution_id","execution_nonce","execution_policy_sha256",
    "provider_plan_sha256","provider_id","instrument_id","book_kind","physical_route_kind",
    "provider_endpoint_binding_sha256","physical_action_sha256","started_at_utc","terminal_at_utc",
    "network_attempt_count","provider_request_or_session_count","automatic_retry_count",
    "raw_message_count","terminal_observation_count","raw_observation_bytes","http_status_code",
    "ws_subscription_acknowledged","ws_terminal_snapshot_message_index","terminal_status","error_class",
    "observation_id","observation_sha256","execution_receipt_sha256",
}
TERMINAL_ERROR = {
    "SUCCESS_OBSERVATION_CAPTURED": None,
    "FAIL_POLICY_BLOCKED": "POLICY_BLOCKED",
    "FAIL_PLAN_INVALID": "PLAN_INVALID",
    "FAIL_CONNECT": "CONNECT",
    "FAIL_TIMEOUT": "TIMEOUT",
    "FAIL_RATE_LIMIT_OR_PROVIDER_REJECTION": "RATE_LIMIT_OR_PROVIDER_REJECTION",
    "FAIL_OVERSIZE": "OVERSIZE",
    "FAIL_MALFORMED_PAYLOAD": "MALFORMED_PAYLOAD",
    "FAIL_PROVIDER_IDENTITY": "PROVIDER_IDENTITY",
    "FAIL_INCOMPLETE_OBSERVATION": "INCOMPLETE_OBSERVATION",
    "FAIL_INTERNAL_BOUNDED_EXECUTION": "INTERNAL_BOUNDED_EXECUTION",
}

class S3ExecutionError(RuntimeError):
    def __init__(self, terminal_status: str, message: str):
        self.terminal_status = terminal_status
        super().__init__(message)

def _now_utc() -> str:
    current = current_data_transport._utc_now()
    offset = current.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise S3ExecutionError("FAIL_INTERNAL_BOUNDED_EXECUTION","CURRENT_DATA_CLOCK_NOT_UTC")
    return current_data_transport._format_utc(current)

def _execution_id(nonce: str, provider_plan_sha256: str | None) -> str:
    return sha256_canonical_json({"execution_nonce": nonce, "provider_plan_sha256": provider_plan_sha256})

def _validate_nonce(value: str) -> str:
    if not isinstance(value,str) or not _HEX64.fullmatch(value):
        raise ValueError("S3_EXECUTION_NONCE_INVALID")
    return value

def _validate_plan(provider_plan: Mapping[str,Any], s1_planner_result: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(provider_plan,Mapping):
        raise ValueError("S3_PROVIDER_PLAN_REQUIRED")
    schema=provider_plan.get("schema_version")
    if schema == BINANCE_PLAN_SCHEMA:
        return validate_binance_provider_plan(provider_plan,s1_planner_result)
    if schema == KRAKEN_SPOT_PLAN_SCHEMA:
        return validate_kraken_spot_provider_plan(provider_plan,s1_planner_result)
    if schema == KRAKEN_FUTURES_PLAN_SCHEMA:
        return validate_kraken_futures_provider_plan(provider_plan,s1_planner_result)
    raise ValueError("S3_PROVIDER_PLAN_SCHEMA_UNKNOWN")

def _endpoint_and_action(plan: Mapping[str,Any]) -> tuple[dict[str,Any],dict[str,Any]]:
    provider=str(plan["provider_id"])
    if plan.get("http_method") is not None:
        route_kind="REST"
        base=plan.get("canonical_base_host"); path=plan.get("endpoint_path")
        if not isinstance(base,str) or not isinstance(path,str):
            raise ValueError("S3_BINANCE_ENDPOINT_BINDING_INVALID")
        absolute=base.rstrip("/")+"/"+path.lstrip("/")
        route_id=None; instrument=plan["instrument_id"]; channel=None; method=plan["http_method"]
        depth_name=plan.get("provider_depth_parameter_name"); depth_value=plan.get("provider_requested_level_count")
    else:
        route_kind="WEBSOCKET"; absolute=plan.get("endpoint")
        if not isinstance(absolute,str):
            raise ValueError("S3_WS_ENDPOINT_BINDING_INVALID")
        route_id=plan.get("route_id"); instrument=plan.get("provider_symbol",plan.get("provider_product_id"))
        channel=plan.get("channel",plan.get("feed")); method=None
        depth_name=plan.get("provider_depth_parameter_name"); depth_value=plan.get("provider_requested_level_count")
    binding={
        "absolute_endpoint":absolute,"physical_route_kind":route_kind,
        "provider_capability_sha256":plan["provider_capability_sha256"],
        "provider_id":provider,"route_id":route_id,
    }
    binding_sha=sha256_canonical_json(binding)
    action={
        "channel_or_feed":channel,"http_method":method,"physical_route_kind":route_kind,
        "provider_depth_parameter_name":depth_name,"provider_depth_parameter_value":depth_value,
        "provider_endpoint_binding_sha256":binding_sha,"provider_id":provider,
        "provider_instrument_id":instrument,"snapshot_required":True,
    }
    return binding,action

class BoundedTransport:
    # One-request/one-session physical transport. No retry and no fallback.
    def rest(self, plan: Mapping[str,Any], *, byte_limit: int) -> tuple[int,bytes]:
        endpoint=str(plan["canonical_base_host"]).rstrip("/")+str(plan["endpoint_path"])
        query=urlencode({"symbol":str(plan["instrument_id"]),str(plan["provider_depth_parameter_name"]):int(plan["provider_requested_level_count"])})
        parsed=urlsplit(endpoint)
        if parsed.scheme!="https" or not parsed.hostname or parsed.query or parsed.fragment:
            raise S3ExecutionError("FAIL_PLAN_INVALID","REST_ENDPOINT_NOT_CANONICAL_HTTPS")
        connect_deadline=time.monotonic()+S3_EXECUTION_POLICY["connect_timeout_ms"]/1000
        conn=http.client.HTTPSConnection(parsed.hostname,parsed.port or 443,timeout=max(0.001,connect_deadline-time.monotonic()),context=ssl.create_default_context())
        try:
            conn.connect()
        except TimeoutError as exc:
            conn.close(); raise S3ExecutionError("FAIL_CONNECT","REST_CONNECT_TIMEOUT") from exc
        except OSError as exc:
            conn.close(); raise S3ExecutionError("FAIL_CONNECT","REST_CONNECT_FAILED") from exc
        response_deadline=time.monotonic()+S3_EXECUTION_POLICY["rest_response_deadline_ms"]/1000
        try:
            if conn.sock is not None: conn.sock.settimeout(max(0.001,response_deadline-time.monotonic()))
            conn.request("GET",parsed.path+"?"+query,headers={"Accept":"application/json","Accept-Encoding":"identity","User-Agent":"eth-macro-data-bridge-s3/1.0"})
            if conn.sock is not None: conn.sock.settimeout(max(0.001,response_deadline-time.monotonic()))
            response=conn.getresponse()
            if response.getheader("Location"):
                raise S3ExecutionError("FAIL_RATE_LIMIT_OR_PROVIDER_REJECTION","REST_REDIRECT_FORBIDDEN")
            if (response.getheader("Content-Encoding") or "identity").lower() not in {"identity",""}:
                raise S3ExecutionError("FAIL_MALFORMED_PAYLOAD","REST_CONTENT_ENCODING_FORBIDDEN")
            if conn.sock is not None: conn.sock.settimeout(max(0.001,response_deadline-time.monotonic()))
            return int(response.status),response.read(byte_limit+1)
        except TimeoutError as exc:
            raise S3ExecutionError("FAIL_TIMEOUT","REST_RESPONSE_TIMEOUT") from exc
        finally:
            conn.close()

    def ws(self, plan: Mapping[str,Any], *, byte_limit: int) -> list[str|bytes]:
        try:
            from websockets.sync.client import connect
        except Exception as exc:
            raise S3ExecutionError("FAIL_INTERNAL_BOUNDED_EXECUTION","WEBSOCKETS_DEPENDENCY_UNAVAILABLE") from exc
        endpoint=str(plan["endpoint"]); provider=str(plan["provider_id"])
        if provider=="kraken-spot":
            subscription={"method":"subscribe","params":{"channel":str(plan["channel"]),"symbol":[str(plan["provider_symbol"])],"depth":int(plan["provider_requested_level_count"]),"snapshot":True}}
        elif provider=="kraken-futures":
            subscription={"event":"subscribe","feed":str(plan["feed"]),"product_ids":[str(plan["provider_product_id"])]}
        else:
            raise S3ExecutionError("FAIL_PLAN_INVALID","WS_PROVIDER_UNSUPPORTED")
        try:
            with connect(endpoint,open_timeout=S3_EXECUTION_POLICY["connect_timeout_ms"]/1000,
                         close_timeout=S3_EXECUTION_POLICY["best_effort_close_timeout_ms"]/1000,
                         max_size=byte_limit+1,max_queue=4,compression=None,ping_interval=None,proxy=None,legacy=True) as websocket:
                websocket.send(json.dumps(subscription,separators=(",",":"),ensure_ascii=False))
                deadline=time.monotonic()+S3_EXECUTION_POLICY["ws_initial_snapshot_deadline_ms"]/1000
                messages=[]
                for _ in range(S3_EXECUTION_POLICY["max_ws_messages_before_terminal"]):
                    remaining=deadline-time.monotonic()
                    if remaining<=0: raise S3ExecutionError("FAIL_TIMEOUT","WS_INITIAL_SNAPSHOT_TIMEOUT")
                    messages.append(websocket.recv(timeout=remaining))
                    if _looks_terminal_ws_snapshot(provider,messages[-1]): return messages
                raise S3ExecutionError("FAIL_INCOMPLETE_OBSERVATION","WS_MESSAGE_LIMIT_BEFORE_SNAPSHOT")
        except S3ExecutionError: raise
        except TimeoutError as exc: raise S3ExecutionError("FAIL_TIMEOUT","WS_TIMEOUT") from exc
        except OSError as exc: raise S3ExecutionError("FAIL_CONNECT","WS_CONNECT_FAILED") from exc
        except Exception as exc: raise S3ExecutionError("FAIL_CONNECT","WS_CONNECTION_FAILED") from exc

def _message_bytes(message: str|bytes) -> bytes:
    return message if isinstance(message,bytes) else message.encode("utf-8")

def _decode_json(message: str|bytes) -> Mapping[str,Any]:
    try: value=json.loads(message)
    except Exception as exc: raise S3ExecutionError("FAIL_MALFORMED_PAYLOAD","S3_MESSAGE_JSON_INVALID") from exc
    if not isinstance(value,Mapping): raise S3ExecutionError("FAIL_MALFORMED_PAYLOAD","S3_MESSAGE_OBJECT_REQUIRED")
    return value

def _looks_terminal_ws_snapshot(provider: str, message: str|bytes) -> bool:
    try: value=json.loads(message)
    except Exception: return False
    if not isinstance(value,Mapping): return False
    if provider=="kraken-spot": return value.get("channel")=="book" and value.get("type")=="snapshot"
    if provider=="kraken-futures": return value.get("feed")=="book_snapshot"
    return False

def _spot_ack(message: Mapping[str,Any], plan: Mapping[str,Any]) -> bool:
    if message.get("method")!="subscribe" or message.get("success") is not True: return False
    result=message.get("result")
    if result is None: return True
    if not isinstance(result,Mapping): raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_SPOT_ACK_RESULT_INVALID")
    if result.get("channel") not in (None,plan["channel"]): raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_SPOT_ACK_CHANNEL_MISMATCH")
    if result.get("symbol") not in (None,plan["provider_symbol"]): raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_SPOT_ACK_SYMBOL_MISMATCH")
    if result.get("depth") not in (None,plan["provider_requested_level_count"]): raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_SPOT_ACK_DEPTH_MISMATCH")
    return True

def _futures_ack(message: Mapping[str,Any], plan: Mapping[str,Any]) -> bool:
    if message.get("event")!="subscribed" or message.get("feed")!="book": return False
    product_ids=message.get("product_ids"); product_id=message.get("product_id")
    if product_ids is not None and plan["provider_product_id"] not in product_ids: raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_FUTURES_ACK_PRODUCT_MISMATCH")
    if product_id is not None and product_id!=plan["provider_product_id"]: raise S3ExecutionError("FAIL_PROVIDER_IDENTITY","KRAKEN_FUTURES_ACK_PRODUCT_MISMATCH")
    return True

def _consume_ws(messages: list[str|bytes], plan: Mapping[str,Any], byte_limit: int):
    provider=str(plan["provider_id"]); total=0; ack=False; snapshot=None; terminal_index=None
    for index,message in enumerate(messages,1):
        total += len(_message_bytes(message))
        if total>byte_limit: raise S3ExecutionError("FAIL_OVERSIZE",f"OVERSIZE:{byte_limit+1}")
        parsed=_decode_json(message)
        if provider=="kraken-spot":
            if parsed.get("channel")=="book" and parsed.get("type")=="snapshot":
                ack=True; snapshot=parsed; terminal_index=index; break
            if parsed.get("channel")=="book" and parsed.get("type")=="update":
                raise S3ExecutionError("FAIL_INCOMPLETE_OBSERVATION","KRAKEN_SPOT_DELTA_BEFORE_INITIAL_SNAPSHOT")
            if parsed.get("channel") in {"heartbeat","status"} or parsed.get("method")=="pong": continue
            if _spot_ack(parsed,plan): ack=True; continue
            if parsed.get("success") is False: raise S3ExecutionError("FAIL_RATE_LIMIT_OR_PROVIDER_REJECTION","KRAKEN_SPOT_SUBSCRIPTION_REJECTED")
        else:
            if parsed.get("feed")=="book_snapshot":
                ack=True; snapshot=parsed; terminal_index=index; break
            if _futures_ack(parsed,plan): ack=True; continue
            if parsed.get("feed")=="book": raise S3ExecutionError("FAIL_INCOMPLETE_OBSERVATION","KRAKEN_FUTURES_DELTA_BEFORE_INITIAL_SNAPSHOT")
            if parsed.get("event") in {"alert","error"}: raise S3ExecutionError("FAIL_RATE_LIMIT_OR_PROVIDER_REJECTION","KRAKEN_FUTURES_SUBSCRIPTION_REJECTED")
    if snapshot is None: raise S3ExecutionError("FAIL_INCOMPLETE_OBSERVATION","INITIAL_SNAPSHOT_NOT_OBSERVED")
    return snapshot,ack,terminal_index,total

def _receipt(*,nonce,started,terminal,terminal_status,plan,endpoint_sha,action_sha,network_attempt_count,session_count,
             raw_message_count,raw_observation_bytes,http_status_code,ws_ack,ws_index,observation_id,observation_sha256):
    plan_sha=plan.get("provider_plan_sha256") if plan is not None else None
    result={
        "schema_version":S3_EXECUTION_RECEIPT_SCHEMA,"execution_id":_execution_id(nonce,plan_sha),"execution_nonce":nonce,
        "execution_policy_sha256":S3_EXECUTION_POLICY_SHA256,"provider_plan_sha256":plan_sha,
        "provider_id":plan.get("provider_id") if plan is not None else None,
        "instrument_id":plan.get("instrument_id") if plan is not None else None,
        "book_kind":plan.get("book_kind") if plan is not None else None,
        "physical_route_kind":"REST" if plan is not None and plan.get("http_method") is not None else ("WEBSOCKET" if plan is not None else None),
        "provider_endpoint_binding_sha256":endpoint_sha,"physical_action_sha256":action_sha,
        "started_at_utc":started,"terminal_at_utc":terminal,"network_attempt_count":network_attempt_count,
        "provider_request_or_session_count":session_count,"automatic_retry_count":0,"raw_message_count":raw_message_count,
        "terminal_observation_count":1 if terminal_status=="SUCCESS_OBSERVATION_CAPTURED" else 0,
        "raw_observation_bytes":raw_observation_bytes,"http_status_code":http_status_code,
        "ws_subscription_acknowledged":ws_ack,"ws_terminal_snapshot_message_index":ws_index,
        "terminal_status":terminal_status,"error_class":TERMINAL_ERROR[terminal_status],
        "observation_id":observation_id if terminal_status=="SUCCESS_OBSERVATION_CAPTURED" else None,
        "observation_sha256":observation_sha256 if terminal_status=="SUCCESS_OBSERVATION_CAPTURED" else None,
    }
    result["execution_receipt_sha256"]=sha256_canonical_json(result)
    return result

def validate_execution_receipt(receipt: Mapping[str,Any],*,provider_plan=None,s1_planner_result=None,qualified_resource=None):
    if not isinstance(receipt,Mapping) or set(receipt)!=RECEIPT_FIELDS: raise ValueError("S3_EXECUTION_RECEIPT_FIELDS_INVALID")
    if receipt.get("schema_version")!=S3_EXECUTION_RECEIPT_SCHEMA: raise ValueError("S3_EXECUTION_RECEIPT_SCHEMA_INVALID")
    if receipt.get("execution_policy_sha256")!=S3_EXECUTION_POLICY_SHA256: raise ValueError("S3_EXECUTION_POLICY_SHA256_MISMATCH")
    nonce=_validate_nonce(receipt.get("execution_nonce")); status=receipt.get("terminal_status")
    if status not in TERMINAL_ERROR or receipt.get("error_class")!=TERMINAL_ERROR[status]: raise ValueError("S3_TERMINAL_STATUS_ERROR_CLASS_MISMATCH")
    material=dict(receipt); supplied=material.pop("execution_receipt_sha256",None)
    if supplied!=sha256_canonical_json(material): raise ValueError("S3_EXECUTION_RECEIPT_SHA256_MISMATCH")
    plan_sha=receipt.get("provider_plan_sha256")
    if receipt.get("execution_id")!=_execution_id(nonce,plan_sha): raise ValueError("S3_EXECUTION_ID_MISMATCH")
    for field in ("network_attempt_count","provider_request_or_session_count","automatic_retry_count","raw_message_count","terminal_observation_count","raw_observation_bytes"):
        value=receipt.get(field)
        if isinstance(value,bool) or not isinstance(value,int) or value<0: raise ValueError(f"S3_RECEIPT_{field.upper()}_INVALID")
    if receipt["automatic_retry_count"]!=0: raise ValueError("S3_AUTOMATIC_RETRY_FORBIDDEN")
    if receipt["network_attempt_count"]>1 or receipt["provider_request_or_session_count"]>1: raise ValueError("S3_NETWORK_CARDINALITY_EXCEEDED")
    if receipt["terminal_observation_count"] not in {0,1}: raise ValueError("S3_OBSERVATION_CARDINALITY_INVALID")
    if status=="SUCCESS_OBSERVATION_CAPTURED":
        if receipt["terminal_observation_count"]!=1 or not _HEX64.fullmatch(str(receipt.get("observation_sha256") or "")): raise ValueError("S3_SUCCESS_OBSERVATION_BINDING_INVALID")
        if not isinstance(receipt.get("observation_id"),str) or not receipt["observation_id"]: raise ValueError("S3_SUCCESS_OBSERVATION_ID_INVALID")
    elif receipt["terminal_observation_count"]!=0 or receipt.get("observation_id") is not None or receipt.get("observation_sha256") is not None:
        raise ValueError("S3_FAILURE_OBSERVATION_MUST_BE_NULL")
    start=current_data_transport._parse_utc(str(receipt["started_at_utc"]),"s3.started_at_utc")
    end=current_data_transport._parse_utc(str(receipt["terminal_at_utc"]),"s3.terminal_at_utc")
    if current_data_transport._format_utc(start)!=receipt["started_at_utc"] or current_data_transport._format_utc(end)!=receipt["terminal_at_utc"] or end<start:
        raise ValueError("S3_EXECUTION_TIME_INVALID")
    if status=="FAIL_PLAN_INVALID":
        for field in ("provider_plan_sha256","provider_id","instrument_id","book_kind","physical_route_kind","provider_endpoint_binding_sha256","physical_action_sha256"):
            if receipt.get(field) is not None: raise ValueError("S3_INVALID_PLAN_TRUSTED_IDENTITY_LEAK")
        if receipt["network_attempt_count"] or receipt["provider_request_or_session_count"]: raise ValueError("S3_INVALID_PLAN_NETWORK_ATTEMPTED")
        return dict(receipt)
    if provider_plan is None or s1_planner_result is None: raise ValueError("S3_RECEIPT_PLAN_REVALIDATION_REQUIRED")
    plan=_validate_plan(provider_plan,s1_planner_result)
    if receipt["provider_plan_sha256"]!=plan["provider_plan_sha256"]: raise ValueError("S3_RECEIPT_PROVIDER_PLAN_SHA_MISMATCH")
    if receipt["provider_id"]!=plan["provider_id"] or receipt["instrument_id"]!=plan["instrument_id"] or receipt["book_kind"]!=plan["book_kind"]:
        raise ValueError("S3_RECEIPT_PLAN_IDENTITY_MISMATCH")
    binding,action=_endpoint_and_action(plan)
    if receipt["provider_endpoint_binding_sha256"]!=sha256_canonical_json(binding): raise ValueError("S3_ENDPOINT_BINDING_SHA_MISMATCH")
    if receipt["physical_action_sha256"]!=sha256_canonical_json(action): raise ValueError("S3_PHYSICAL_ACTION_SHA_MISMATCH")
    limit=min(int(plan["max_raw_resource_bytes"]),S3_EXECUTION_POLICY["max_raw_observation_bytes"])
    if status=="FAIL_OVERSIZE":
        if receipt["raw_observation_bytes"]!=limit+1: raise ValueError("S3_OVERSIZE_SENTINEL_INVALID")
    elif receipt["raw_observation_bytes"]>limit: raise ValueError("S3_RAW_OBSERVATION_BYTES_EXCEEDED")
    if plan.get("http_method") is not None:
        if receipt["physical_route_kind"]!="REST" or receipt.get("ws_subscription_acknowledged") is not None or receipt.get("ws_terminal_snapshot_message_index") is not None:
            raise ValueError("S3_REST_RECEIPT_ROUTE_FIELDS_INVALID")
        if receipt["raw_message_count"]>1: raise ValueError("S3_REST_MESSAGE_COUNT_INVALID")
    else:
        if receipt["physical_route_kind"]!="WEBSOCKET" or receipt.get("http_status_code") is not None: raise ValueError("S3_WS_RECEIPT_ROUTE_FIELDS_INVALID")
        if receipt["raw_message_count"]>S3_EXECUTION_POLICY["max_ws_messages_before_terminal"]: raise ValueError("S3_WS_MESSAGE_COUNT_EXCEEDED")
        if status=="SUCCESS_OBSERVATION_CAPTURED":
            idx=receipt.get("ws_terminal_snapshot_message_index")
            if receipt.get("ws_subscription_acknowledged") is not True or not isinstance(idx,int) or not 1<=idx<=receipt["raw_message_count"]:
                raise ValueError("S3_WS_SUCCESS_LIFECYCLE_INVALID")
    if status=="FAIL_POLICY_BLOCKED" and (receipt["network_attempt_count"] or receipt["provider_request_or_session_count"]):
        raise ValueError("S3_POLICY_BLOCKED_NETWORK_ATTEMPTED")
    if qualified_resource is not None and status=="SUCCESS_OBSERVATION_CAPTURED":
        if receipt["observation_id"]!=qualified_resource.get("observation_id") or receipt["observation_sha256"]!=qualified_resource.get("observation_sha256"):
            raise ValueError("S3_RECEIPT_RESOURCE_OBSERVATION_MISMATCH")
        book=qualified_resource.get("normalized_book")
        if not isinstance(book,Mapping) or book.get("observation_id")!=receipt["observation_id"] or book.get("observation_sha256")!=receipt["observation_sha256"]:
            raise ValueError("S3_RECEIPT_NORMALIZED_BOOK_OBSERVATION_MISMATCH")
    return dict(receipt)

def execute_s3(semantic_request,s1_planner_result,provider_plan,*,transport=None,execution_nonce=None,execution_plane="GITHUB_ACTIONS"):
    if sha256_canonical_json(S3_EXECUTION_POLICY)!=S3_EXECUTION_POLICY_SHA256: raise RuntimeError("S3_EXECUTION_POLICY_DIGEST_INTERNAL_MISMATCH")
    nonce=_validate_nonce(execution_nonce) if execution_nonce is not None else secrets.token_hex(32); started=_now_utc()
    try: plan=_validate_plan(provider_plan,s1_planner_result)
    except Exception:
        receipt=_receipt(nonce=nonce,started=started,terminal=_now_utc(),terminal_status="FAIL_PLAN_INVALID",plan=None,endpoint_sha=None,action_sha=None,
            network_attempt_count=0,session_count=0,raw_message_count=0,raw_observation_bytes=0,http_status_code=None,ws_ack=None,ws_index=None,
            observation_id=None,observation_sha256=None)
        return {"status":"FAIL","receipt":receipt,"provider_plan":None,"s2_result":None,"qualified_resource":None}
    binding,action=_endpoint_and_action(plan); endpoint_sha=sha256_canonical_json(binding); action_sha=sha256_canonical_json(action)
    if plan["provider_id"]=="binance-usdm" and execution_plane=="GITHUB_ACTIONS":
        receipt=_receipt(nonce=nonce,started=started,terminal=_now_utc(),terminal_status="FAIL_POLICY_BLOCKED",plan=plan,endpoint_sha=endpoint_sha,action_sha=action_sha,
            network_attempt_count=0,session_count=0,raw_message_count=0,raw_observation_bytes=0,http_status_code=None,ws_ack=None,ws_index=None,
            observation_id=None,observation_sha256=None)
        validate_execution_receipt(receipt,provider_plan=plan,s1_planner_result=s1_planner_result)
        return {"status":"POLICY_BLOCKED","receipt":receipt,"provider_plan":plan,"s2_result":None,"qualified_resource":None}
    transport=transport or BoundedTransport(); limit=min(int(plan["max_raw_resource_bytes"]),S3_EXECUTION_POLICY["max_raw_observation_bytes"])
    status_code=None; message_count=0; raw_bytes=0; ws_ack=None; ws_index=None
    observation_id="s3:"+_execution_id(nonce,plan["provider_plan_sha256"])
    try:
        if plan.get("http_method") is not None:
            status_code,raw=transport.rest(plan,byte_limit=limit); message_count=1
            if len(raw)>limit: raise S3ExecutionError("FAIL_OVERSIZE",f"OVERSIZE:{limit+1}")
            raw_bytes=len(raw)
            if status_code in {418,429} or status_code>=500 or status_code!=200: raise S3ExecutionError("FAIL_RATE_LIMIT_OR_PROVIDER_REJECTION",f"HTTP_STATUS:{status_code}")
            try: payload=json.loads(raw)
            except Exception as exc: raise S3ExecutionError("FAIL_MALFORMED_PAYLOAD","BINANCE_JSON_INVALID") from exc
            if not isinstance(payload,Mapping): raise S3ExecutionError("FAIL_MALFORMED_PAYLOAD","BINANCE_RESPONSE_OBJECT_REQUIRED")
            try: s2_result=build_binance_liquidity_resource(plan,s1_planner_result,semantic_request,payload,observation_id=observation_id)
            except BinanceS2Error as exc:
                terminal="FAIL_PROVIDER_IDENTITY" if any(k in str(exc) for k in ("INSTRUMENT","SYMBOL","PROVIDER")) else "FAIL_MALFORMED_PAYLOAD"
                raise S3ExecutionError(terminal,str(exc)) from exc
        else:
            messages=transport.ws(plan,byte_limit=limit)
            if not isinstance(messages,list): raise S3ExecutionError("FAIL_INTERNAL_BOUNDED_EXECUTION","WS_TRANSPORT_RESULT_INVALID")
            if len(messages)>S3_EXECUTION_POLICY["max_ws_messages_before_terminal"]: raise S3ExecutionError("FAIL_INCOMPLETE_OBSERVATION","WS_MESSAGE_LIMIT_EXCEEDED")
            snapshot,ws_ack,ws_index,raw_bytes=_consume_ws(messages,plan,limit); message_count=ws_index or len(messages)
            try:
                s2_result=(build_kraken_spot_liquidity_resource(plan,s1_planner_result,semantic_request,snapshot,observation_id=observation_id)
                           if plan["provider_id"]=="kraken-spot"
                           else build_kraken_futures_liquidity_resource(plan,s1_planner_result,semantic_request,snapshot,observation_id=observation_id))
            except (KrakenSpotS2Error,KrakenFuturesS2Error) as exc:
                terminal="FAIL_PROVIDER_IDENTITY" if any(k in str(exc) for k in ("INSTRUMENT","SYMBOL","PRODUCT")) else "FAIL_MALFORMED_PAYLOAD"
                raise S3ExecutionError(terminal,str(exc)) from exc
        resource=s2_result["qualified_resource"]
        receipt=_receipt(nonce=nonce,started=started,terminal=_now_utc(),terminal_status="SUCCESS_OBSERVATION_CAPTURED",plan=plan,endpoint_sha=endpoint_sha,action_sha=action_sha,
            network_attempt_count=1,session_count=1,raw_message_count=message_count,raw_observation_bytes=raw_bytes,http_status_code=status_code,
            ws_ack=ws_ack,ws_index=ws_index,observation_id=resource["observation_id"],observation_sha256=resource["observation_sha256"])
        validate_execution_receipt(receipt,provider_plan=plan,s1_planner_result=s1_planner_result,qualified_resource=resource)
        return {"status":"PASS","receipt":receipt,"provider_plan":plan,"s2_result":s2_result,"qualified_resource":resource}
    except S3ExecutionError as exc:
        terminal=exc.terminal_status
        if terminal=="FAIL_OVERSIZE": raw_bytes=limit+1
        receipt=_receipt(nonce=nonce,started=started,terminal=_now_utc(),terminal_status=terminal,plan=plan,endpoint_sha=endpoint_sha,action_sha=action_sha,
            network_attempt_count=1,session_count=1,raw_message_count=message_count,raw_observation_bytes=raw_bytes,http_status_code=status_code,
            ws_ack=ws_ack if plan.get("http_method") is None else None,ws_index=None,observation_id=None,observation_sha256=None)
        validate_execution_receipt(receipt,provider_plan=plan,s1_planner_result=s1_planner_result)
        return {"status":"FAIL","receipt":receipt,"provider_plan":plan,"s2_result":None,"qualified_resource":None}
