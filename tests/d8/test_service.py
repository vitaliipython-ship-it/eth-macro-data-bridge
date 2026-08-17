from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from d8_runtime import D8Runtime, DeterministicMockAcquisition, RuntimeConfig, utc_iso
from d8_service import Handler, Server

BASE_MS = int(datetime(2026,8,17,19,0,tzinfo=timezone.utc).timestamp()*1000)

class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        cfg=RuntimeConfig(state_root=root,profile="test",source_revision="fixture")
        self.rt=D8Runtime(cfg,DeterministicMockAcquisition(),clock_ms=lambda:BASE_MS+30_000)
        self.server=Server(("127.0.0.1",0),Handler,self.rt); self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2); self.tmp.cleanup(); os.environ.pop("D8_RUNTIME_TOKEN",None)
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection("127.0.0.1",self.port,timeout=3); c.request(method,path,body=body,headers=headers or {}); r=c.getresponse(); data=r.read(); c.close(); return r.status,json.loads(data)
    def test_health_readiness(self):
        self.assertEqual(self.request("GET","/v1/health")[0],200); self.assertEqual(self.request("GET","/v1/readiness")[0],200)
    def test_auth_fail_closed_when_configured(self):
        os.environ["D8_RUNTIME_TOKEN"]="secret"
        code,body=self.request("GET","/v1/health"); self.assertEqual(code,401); self.assertEqual(body["error_class"],"AUTH_FAILED")
        code,_=self.request("GET","/v1/health",headers={"Authorization":"Bearer secret"}); self.assertEqual(code,200)
    def test_vps_shadow_requires_token_configuration(self):
        self.rt.config = RuntimeConfig(state_root=self.rt.config.state_root,profile="VPS_SHADOW",source_revision="fixture")
        os.environ.pop("D8_RUNTIME_TOKEN",None)
        code,body=self.request("GET","/v1/readiness"); self.assertEqual(code,503); self.assertEqual(body["error_class"],"AUTH_FAILED")
    def test_bounded_request_body(self):
        os.environ["D8_RUNTIME_TOKEN"]="secret"
        body="x"*(65536+1)
        code,result=self.request("POST","/v1/collect-cycle",body,headers={"Authorization":"Bearer secret","Content-Type":"application/json","Content-Length":str(len(body))})
        self.assertEqual(code,413); self.assertEqual(result["error_class"],"REQUEST_INVALID")
    def test_collect_http(self):
        req={"schema_version":"eth-macro-d8-collect-cycle-request/1.0.0","expected_schedule_at":utc_iso(BASE_MS),"canonical_slot":"M5"}; raw=json.dumps(req)
        code,res=self.request("POST","/v1/collect-cycle",raw,headers={"Content-Type":"application/json","Content-Length":str(len(raw))}); self.assertEqual(code,200); self.assertEqual(res["overall_status"],"PASS")
    def test_strict_methods_paths(self):
        self.assertEqual(self.request("GET","/unknown")[0],404); self.assertEqual(self.request("PUT","/v1/collect-cycle")[0],405)

if __name__=="__main__": unittest.main()
