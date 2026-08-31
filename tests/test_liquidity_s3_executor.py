from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import current_data_transport
from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import plan_liquidity_acquisition
from liquidity_s2_binance_adapter import build_binance_provider_plan
from liquidity_s2_kraken_spot_adapter import build_kraken_spot_provider_plan, compute_kraken_ws_v2_checksum
from liquidity_s2_kraken_futures_adapter import build_kraken_futures_provider_plan
from liquidity_s3_executor import (
    S3_EXECUTION_POLICY,
    S3_EXECUTION_POLICY_SHA256,
    S3ExecutionError,
    execute_s3,
    validate_execution_receipt,
)
from tools.current_data_request_scope import qualify_request
from tools.current_data_transport import (
    REQUEST_SCHEMA_V10,
    _load_request_wrapper,
    _sha256_json,
    normalize_request,
)

NOW_MS=1_800_000_600_000
NOW=datetime.fromtimestamp(NOW_MS/1000,timezone.utc)
NONCE="11"*32

def req(provider="binance-spot",instrument="ETHUSDT",book_kind="L2_LEVEL_BOOK",representation="RAW",target=500,max_age=600):
    return {
        "series_id":f"liquidity.{provider}.{instrument}.orderbook",
        "provider_id":provider,"instrument_id":instrument,"book_kind":book_kind,
        "representation":representation,"target_bps":target,"bucket_bps":25,
        "freshness":{"max_age_seconds":max_age},"completeness":{"required":True},
        "quantity_semantics":{"mode":"NATIVE_FIRST","consumer_equivalent_required":False},
    }

def s1_plan(request):
    provider=request["provider_id"]
    cap={
        "provider_id":provider,"book_kind":request["book_kind"],
        "raw_book_capability":"AVAILABLE_EXTERNALLY" if provider=="kraken-spot" else "CONFIRMED",
        "selectable_depth_limit":"NOT_NORMATIVELY_DOCUMENTED" if provider=="kraken-futures" else "NOT_QUALIFIED",
        "qualified_provider_depth_parameter":None,
    }
    return plan_liquidity_acquisition(request,cap)

def provider_plan(request,max_bytes=1_000_000):
    plan=s1_plan(request)
    if request["provider_id"] in {"binance-spot","binance-usdm"}:
        return plan,build_binance_provider_plan(plan,request_weight_budget=250 if request["provider_id"]=="binance-spot" else 20,max_raw_resource_bytes=max_bytes)
    if request["provider_id"]=="kraken-spot":
        return plan,build_kraken_spot_provider_plan(plan,max_raw_resource_bytes=max_bytes)
    return plan,build_kraken_futures_provider_plan(plan,max_raw_resource_bytes=max_bytes)

def binance_payload():
    return {
        "lastUpdateId":123,
        "bids":[["99.9","2"],["98","3"],["95","4"]],
        "asks":[["100.1","2"],["102","3"],["105","4"]],
    }

class FakeTransport:
    def __init__(self,mode="success"):
        self.mode=mode; self.calls=0
    def rest(self,plan,*,byte_limit):
        self.calls += 1
        if self.mode=="timeout": raise S3ExecutionError("FAIL_TIMEOUT","fake")
        if self.mode=="oversize": return 200,b"x"*(byte_limit+1)
        payload=binance_payload()
        if plan["provider_id"]=="binance-usdm":
            payload={**payload,"E":1,"T":1}
        return 200,json.dumps(payload,separators=(",",":")).encode()
    def ws(self,plan,*,byte_limit):
        self.calls += 1
        if self.mode=="timeout": raise S3ExecutionError("FAIL_TIMEOUT","fake")
        if plan["provider_id"]=="kraken-spot":
            bids=[{"price":"99.9","qty":"2.0"},{"price":"98","qty":"3.0"},{"price":"95","qty":"4.0"}]
            asks=[{"price":"100.1","qty":"2.0"},{"price":"102","qty":"3.0"},{"price":"105","qty":"4.0"}]
            checksum=compute_kraken_ws_v2_checksum(bids,asks)
            return [
                json.dumps({"method":"subscribe","success":True,"result":{"channel":"book","symbol":plan["provider_symbol"],"depth":plan["provider_requested_level_count"]}}),
                json.dumps({"channel":"heartbeat"}),
                json.dumps({"channel":"book","type":"snapshot","data":[{
                    "symbol":plan["provider_symbol"],"bids":bids,"asks":asks,
                    "checksum":checksum,"timestamp":"2027-01-15T08:10:00.000000Z",
                }]}),
            ]
        return [
            json.dumps({"event":"subscribed","feed":"book","product_ids":[plan["provider_product_id"]]}),
            json.dumps({"feed":"book_snapshot","product_id":plan["provider_product_id"],"timestamp":NOW_MS,
                        "seq":1,"tickSize":None,
                        "bids":[{"price":"99.9","qty":"2"},{"price":"98","qty":"3"},{"price":"95","qty":"4"}],
                        "asks":[{"price":"100.1","qty":"2"},{"price":"102","qty":"3"},{"price":"105","qty":"4"}]}),
        ]

class DBFS3Tests(unittest.TestCase):
    def setUp(self):
        clock=patch.object(current_data_transport,"_utc_now",return_value=NOW)
        clock.start(); self.addCleanup(clock.stop)

    def test_001_policy_digest_exact(self):
        self.assertEqual(sha256_canonical_json(S3_EXECUTION_POLICY),S3_EXECUTION_POLICY_SHA256)

    def test_002_binance_spot_rest_success_and_receipt(self):
        request=req(); s1,plan=provider_plan(request); fake=FakeTransport()
        result=execute_s3(request,s1,plan,transport=fake,execution_nonce=NONCE)
        self.assertEqual(result["status"],"PASS"); self.assertEqual(fake.calls,1)
        receipt=validate_execution_receipt(result["receipt"],provider_plan=plan,s1_planner_result=s1,qualified_resource=result["qualified_resource"])
        self.assertEqual(receipt["network_attempt_count"],1); self.assertEqual(receipt["automatic_retry_count"],0)
        self.assertEqual(receipt["physical_route_kind"],"REST")
        self.assertEqual(plan["canonical_base_host"],"https://api.binance.com")

    def test_003_binance_usdm_policy_block_before_network(self):
        request=req("binance-usdm","ETHUSDT","FUTURES_L2_BOOK"); s1,plan=provider_plan(request); fake=FakeTransport()
        result=execute_s3(request,s1,plan,transport=fake,execution_nonce=NONCE)
        self.assertEqual(result["status"],"POLICY_BLOCKED"); self.assertEqual(fake.calls,0)
        self.assertEqual(result["receipt"]["network_attempt_count"],0)
        self.assertEqual(result["receipt"]["provider_request_or_session_count"],0)

    def test_004_kraken_spot_ws_success(self):
        request=req("kraken-spot","ETHUSD","L2_LEVEL_BOOK"); s1,plan=provider_plan(request); fake=FakeTransport()
        result=execute_s3(request,s1,plan,transport=fake,execution_nonce=NONCE)
        self.assertEqual(result["status"],"PASS"); self.assertEqual(fake.calls,1)
        self.assertTrue(result["receipt"]["ws_subscription_acknowledged"])
        self.assertEqual(result["receipt"]["ws_terminal_snapshot_message_index"],3)

    def test_005_kraken_futures_ws_success(self):
        request=req("kraken-futures","PI_ETHUSD","FUTURES_L2_BOOK"); s1,plan=provider_plan(request); fake=FakeTransport()
        result=execute_s3(request,s1,plan,transport=fake,execution_nonce=NONCE)
        self.assertEqual(result["status"],"PASS"); self.assertEqual(fake.calls,1)
        self.assertEqual(result["receipt"]["ws_terminal_snapshot_message_index"],2)

    def test_006_tampered_plan_fails_before_network(self):
        request=req(); s1,plan=provider_plan(request); forged=copy.deepcopy(plan); forged["canonical_base_host"]="https://evil.invalid"
        fake=FakeTransport(); result=execute_s3(request,s1,forged,transport=fake,execution_nonce=NONCE)
        self.assertEqual(result["receipt"]["terminal_status"],"FAIL_PLAN_INVALID"); self.assertEqual(fake.calls,0)

    def test_007_receipt_self_hash_tamper_fails(self):
        request=req(); s1,plan=provider_plan(request); result=execute_s3(request,s1,plan,transport=FakeTransport(),execution_nonce=NONCE)
        bad=copy.deepcopy(result["receipt"]); bad["raw_message_count"]=0
        with self.assertRaisesRegex(ValueError,"RECEIPT_SHA256"):
            validate_execution_receipt(bad,provider_plan=plan,s1_planner_result=s1)

    def test_008_attempt_count_over_one_rejected_even_with_rehash(self):
        request=req(); s1,plan=provider_plan(request); result=execute_s3(request,s1,plan,transport=FakeTransport(),execution_nonce=NONCE)
        bad=copy.deepcopy(result["receipt"]); bad["network_attempt_count"]=2
        material=dict(bad); material.pop("execution_receipt_sha256"); bad["execution_receipt_sha256"]=sha256_canonical_json(material)
        with self.assertRaisesRegex(ValueError,"CARDINALITY"):
            validate_execution_receipt(bad,provider_plan=plan,s1_planner_result=s1)

    def test_009_retry_count_rejected(self):
        request=req(); s1,plan=provider_plan(request); result=execute_s3(request,s1,plan,transport=FakeTransport(),execution_nonce=NONCE)
        bad=copy.deepcopy(result["receipt"]); bad["automatic_retry_count"]=1
        material=dict(bad); material.pop("execution_receipt_sha256"); bad["execution_receipt_sha256"]=sha256_canonical_json(material)
        with self.assertRaisesRegex(ValueError,"RETRY"):
            validate_execution_receipt(bad,provider_plan=plan,s1_planner_result=s1)

    def test_010_oversize_sentinel(self):
        request=req(); s1,plan=provider_plan(request,max_bytes=128); result=execute_s3(request,s1,plan,transport=FakeTransport("oversize"),execution_nonce=NONCE)
        self.assertEqual(result["receipt"]["terminal_status"],"FAIL_OVERSIZE")
        self.assertEqual(result["receipt"]["raw_observation_bytes"],129)

    def test_011_timeout(self):
        request=req(); s1,plan=provider_plan(request); result=execute_s3(request,s1,plan,transport=FakeTransport("timeout"),execution_nonce=NONCE)
        self.assertEqual(result["receipt"]["terminal_status"],"FAIL_TIMEOUT")
        self.assertIsNone(result["receipt"]["observation_id"])

    def test_012_observation_binding_tamper(self):
        request=req(); s1,plan=provider_plan(request); result=execute_s3(request,s1,plan,transport=FakeTransport(),execution_nonce=NONCE)
        resource=copy.deepcopy(result["qualified_resource"]); resource["observation_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"OBSERVATION"):
            validate_execution_receipt(result["receipt"],provider_plan=plan,s1_planner_result=s1,qualified_resource=resource)

    def test_013_exact_only_request_normalizes_without_outer_freshness_authority(self):
        normalized=normalize_request({
            "request_type":"FRESH_CURRENT","required_series":[],"required_domains":[],
            "required_liquidity":[req(max_age=600)],"max_generation_age_seconds":1,"current_policy":"FINALIZED_ONLY",
        })
        self.assertEqual(normalized["max_generation_age_seconds"],1)
        self.assertEqual(normalized["required_liquidity"][0]["freshness"]["max_age_seconds"],600)

    def test_014_old_1_0_wrapper_dual_read(self):
        old={"request_type":"FRESH_CURRENT","required_series":["spot.binance-spot.ETHUSDT.ohlcv.5m"],
             "required_domains":[],"max_generation_age_seconds":600,"current_policy":"FINALIZED_ONLY"}
        # Use legacy normalizer through public body semantics: current loader verifies old hash before upgrade.
        from tools.current_data_transport import _normalize_request_v10
        old=_normalize_request_v10(old)
        wrapper={"schema_version":REQUEST_SCHEMA_V10,"contract_id":"ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
                 "contract_version":"1.0.0","request":old,"request_sha256":_sha256_json(old)}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"request.json"; path.write_text(json.dumps(wrapper),encoding="utf-8")
            upgraded,_sha=_load_request_wrapper(path)
        self.assertEqual(upgraded["required_liquidity"],[])

    def test_015_raw_to_profile_same_execution_one_network(self):
        fake=FakeTransport()
        payload={
            "request_type":"FRESH_CURRENT","required_series":[],"required_domains":[],
            "required_liquidity":[req(representation="PROFILE",target=250),req(representation="RAW",target=500)],
            "max_generation_age_seconds":1,"current_policy":"FINALIZED_ONLY",
        }
        normalized=normalize_request(payload)
        index={"schema_version":"fresh-current-resource-index/1.1.0",
               "contract_id":"ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1","contract_version":"1.1.0",
               "request_sha256":"x","ephemeral_resource_discovery":"GENERATION_RESOURCE_INDEX",
               "follow_legacy_raw_url_for_ephemeral_data":False,"domains":[],"series":[],"liquidity_resources":[]}
        with tempfile.TemporaryDirectory() as td:
            result=qualify_request(normalized,"x",index,output_root=Path(td),s3_transport=fake,legacy_snapshots=[])
            resource_index=json.loads((Path(td)/"resource-index.json").read_text())
        self.assertEqual(result["status"],"PASS"); self.assertEqual(fake.calls,1)
        rows=resource_index["liquidity_resources"]
        self.assertEqual({row["acquisition_mode"] for row in rows},{"S3_NETWORK_ACQUIRED","SAME_EXECUTION_REUSE"})
        self.assertEqual(len({row["resource_sha256"] for row in rows}),1)
        network=next(row for row in rows if row["acquisition_mode"]=="S3_NETWORK_ACQUIRED")
        reuse=next(row for row in rows if row["acquisition_mode"]=="SAME_EXECUTION_REUSE")
        self.assertIsNotNone(network["s3_execution_receipt_sha256"])
        self.assertIsNone(reuse["s3_execution_receipt_sha256"])

    def test_016_cross_run_registry_not_loaded(self):
        source=Path(__file__).parents[1]/"tools"/"current_data_request_scope.py"
        text=source.read_text(encoding="utf-8")
        self.assertNotIn("actions/artifacts",text.lower())
        self.assertNotIn("download-artifact",text.lower())

if __name__=="__main__":
    unittest.main()
