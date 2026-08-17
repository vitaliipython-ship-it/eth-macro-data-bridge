from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from d8_runtime import (
    CAPABILITY_POLICY, D8Runtime, DeterministicMockAcquisition, RuntimeConfig, StateError,
    cycle_id_for, due_state, validate_request, utc_iso,
)

BASE_MS = int(datetime(2026, 8, 17, 19, 0, tzinfo=timezone.utc).timestamp() * 1000)
REQ = {"schema_version":"eth-macro-d8-collect-cycle-request/1.0.0","expected_schedule_at":utc_iso(BASE_MS),"canonical_slot":"M5","trace_id":"test"}

class RuntimeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def runtime(self, core=None, **kwargs):
        cfg = RuntimeConfig(state_root=self.root, profile=kwargs.pop("profile", "test"), spool_max_bytes=kwargs.pop("spool_max_bytes", 128*1024*1024), lease_seconds=kwargs.pop("lease_seconds", 60), source_revision="fixture", **kwargs)
        return D8Runtime(cfg, core or DeterministicMockAcquisition(), clock_ms=lambda: BASE_MS+30_000)

    def test_slot_identity_deterministic(self): self.assertEqual(cycle_id_for(REQ["expected_schedule_at"]), cycle_id_for(REQ["expected_schedule_at"]))
    def test_invalid_non_m5(self):
        body=dict(REQ); body["expected_schedule_at"]="2026-08-17T19:02:00Z"
        with self.assertRaises(ValueError): validate_request(body, now_ms=BASE_MS)
    def test_future_slot_policy(self):
        body=dict(REQ); body["expected_schedule_at"]="2026-08-17T19:10:00Z"
        with self.assertRaises(ValueError): validate_request(body, now_ms=BASE_MS)
    def test_stale_slot_policy(self):
        with self.assertRaises(ValueError): validate_request(REQ, now_ms=BASE_MS+21*60_000)
    def test_forbidden_provider_field(self):
        body=dict(REQ); body["provider"]="binance"
        with self.assertRaises(ValueError): validate_request(body, now_ms=BASE_MS)
    def test_due_not_due(self):
        cap=next(c for c in CAPABILITY_POLICY if c["id"]=="kraken-futures.analytics")
        self.assertEqual(due_state(cap, BASE_MS, "test"), "DUE")
        self.assertEqual(due_state(cap, BASE_MS+5*60_000, "test"), "NOT_DUE")
    def test_vps_shadow_binance_usdm_due(self):
        cap=next(c for c in CAPABILITY_POLICY if c["id"]=="binance-usdm.m5-current")
        self.assertEqual(due_state(cap, BASE_MS, "VPS_SHADOW"), "DUE")
        self.assertEqual(due_state(cap, BASE_MS, "test"), "DISABLED_BY_POLICY")
    def test_vps_active_forbidden(self):
        with self.assertRaises(ValueError): RuntimeConfig(state_root=self.root, profile="VPS_ACTIVE").validate()

    def test_pass_promotes_hot_and_spool(self):
        rt=self.runtime(); code,res=rt.collect_cycle(REQ); self.assertEqual((code,res["overall_status"]),(200,"PASS"))
        info=rt.state.diagnostics(); self.assertEqual(info["hot_cycle_id"],res["cycle_id"]); self.assertGreater(info["spool_rows"],0)
    def test_same_slot_replay_no_reacquire(self):
        core=DeterministicMockAcquisition(); rt=self.runtime(core); rt.collect_cycle(REQ); calls=dict(core.calls)
        code,res=rt.collect_cycle(REQ); self.assertEqual(code,200); self.assertTrue(res["replayed"]); self.assertEqual(core.calls,calls)
    def test_same_slot_concurrency_lock_busy(self):
        core=DeterministicMockAcquisition(delay=.25); rt=self.runtime(core); out=[]
        t=threading.Thread(target=lambda: out.append(rt.collect_cycle(REQ))); t.start(); time.sleep(.05)
        code,res=rt.collect_cycle(REQ); t.join(); self.assertEqual(code,409); self.assertEqual(res["errors"][0]["class"],"LOCK_BUSY")
    def test_stale_lease_recovery(self):
        rt=self.runtime(); cid=cycle_id_for(REQ["expected_schedule_at"])
        with rt.state.connect() as db:
            db.execute("INSERT OR REPLACE INTO cycles(cycle_id,slot,expected_at,attempt,status,source_revision,runtime_revision) VALUES(?,?,?,?,?,?,?)",(cid,REQ["expected_schedule_at"],REQ["expected_schedule_at"],1,"STARTED","x","x"))
            db.execute("INSERT OR REPLACE INTO leases(slot,cycle_id,owner_id,acquired_at,lease_until) VALUES(?,?,?,?,?)",(REQ["expected_schedule_at"],cid,"dead",BASE_MS-10000,BASE_MS-1))
        code,res=rt.collect_cycle(REQ); self.assertEqual(code,200); self.assertTrue(res["stale_lock_recovered"])
    def test_restart_hot_spool_ledger_persist(self):
        rt=self.runtime(); _,res=rt.collect_cycle(REQ); first=rt.state.diagnostics()
        rt2=self.runtime(); second=rt2.state.diagnostics(); self.assertEqual(first,second)
        code,replay=rt2.collect_cycle(REQ); self.assertEqual(code,200); self.assertTrue(replay["replayed"]); self.assertEqual(replay["cycle_id"],res["cycle_id"])
    def test_restart_nonterminal_recoverable(self):
        rt=self.runtime(); cid=cycle_id_for(REQ["expected_schedule_at"])
        with rt.state.connect() as db:
            db.execute("INSERT OR REPLACE INTO cycles(cycle_id,slot,expected_at,attempt,status,source_revision,runtime_revision) VALUES(?,?,?,?,?,?,?)",(cid,REQ["expected_schedule_at"],REQ["expected_schedule_at"],1,"STARTED","x","x"))
        rt2=self.runtime();
        with rt2.state.connect() as db: status=db.execute("SELECT status FROM cycles WHERE cycle_id=?",(cid,)).fetchone()[0]
        self.assertEqual(status,"RECOVERABLE")
    def test_crash_after_durable_checkpoint_reuses_provider_evidence(self):
        class InterruptOnce:
            def __init__(self):
                self.delegate=DeterministicMockAcquisition(); self.interrupted=False
            def collect(self, capability_id, **kwargs):
                if capability_id=="kraken-spot.m5" and not self.interrupted:
                    self.interrupted=True
                    raise StateError("STATE_IO: injected crash boundary")
                return self.delegate.collect(capability_id, **kwargs)
        core=InterruptOnce(); rt=self.runtime(core)
        code,_=rt.collect_cycle(REQ); self.assertEqual(code,503)
        self.assertEqual(core.delegate.calls.get("binance-spot.m5"),1)
        self.assertGreater(rt.state.diagnostics()["spool_rows"],0)
        self.assertIsNone(rt.state.diagnostics()["hot_cycle_id"])
        code,res=rt.collect_cycle(REQ); self.assertEqual((code,res["overall_status"]),(200,"PASS"))
        self.assertEqual(core.delegate.calls.get("binance-spot.m5"),1, "durable success must not be reacquired")
        self.assertTrue(res["capability_statuses"]["binance-spot.m5"].get("reused_durable_checkpoint"))
        self.assertEqual(rt.state.diagnostics()["hot_cycle_id"],res["cycle_id"])

    def test_restart_sweeps_non_authoritative_staging(self):
        rt=self.runtime(); leftover=self.root/"staging"/"dead-cycle"/"attempt-1"/"raw.json"
        leftover.parent.mkdir(parents=True,exist_ok=True); leftover.write_text("partial")
        self.assertTrue(leftover.exists())
        rt2=self.runtime(); self.assertFalse(leftover.exists()); self.assertTrue((self.root/"staging").is_dir())
    def test_optional_failure_degraded_preserves_old_hot(self):
        rt=self.runtime(); rt.collect_cycle(REQ); old=rt.state.diagnostics()["hot_cycle_id"]
        later=BASE_MS+5*60_000; req=dict(REQ,expected_schedule_at=utc_iso(later)); rt.clock_ms=lambda: later+30000
        rt.acquisition=DeterministicMockAcquisition(fail={"kraken-spot.m5"}); code,res=rt.collect_cycle(req)
        self.assertEqual((code,res["overall_status"]),(200,"DEGRADED")); self.assertEqual(rt.state.diagnostics()["hot_cycle_id"],old); self.assertEqual(res["hot_promotion"],"PREVIOUS_HOT_PRESERVED")
    def test_required_failure_fail_preserves_old_hot(self):
        rt=self.runtime(); rt.collect_cycle(REQ); old=rt.state.diagnostics()["hot_cycle_id"]
        later=BASE_MS+5*60_000; req=dict(REQ,expected_schedule_at=utc_iso(later)); rt.clock_ms=lambda: later+30000; rt.acquisition=DeterministicMockAcquisition(fail={"binance-spot.m5"})
        code,res=rt.collect_cycle(req); self.assertEqual((code,res["overall_status"]),(503,"FAIL")); self.assertEqual(rt.state.diagnostics()["hot_cycle_id"],old)
    def test_no_synthetic_fill_gap(self):
        rt=self.runtime(DeterministicMockAcquisition(fail={"binance-spot.m5"})); _,res=rt.collect_cycle(REQ)
        self.assertFalse(res["collection_gap_summary"]["synthetic_fill"]); self.assertGreater(res["collection_gap_summary"]["gap_count"],0)
    def test_spool_deduplicates_observation_identity(self):
        rt=self.runtime(); rt.collect_cycle(REQ); rows=rt.state.diagnostics()["spool_rows"]
        # Force a retry state while preserving spool; deterministic observation IDs remain unique.
        cid=cycle_id_for(REQ["expected_schedule_at"])
        with rt.state.connect() as db: db.execute("UPDATE cycles SET status='FAIL' WHERE cycle_id=?",(cid,))
        rt.collect_cycle(REQ); self.assertEqual(rt.state.diagnostics()["spool_rows"],rows)
    def test_spool_full_explicit(self):
        rt=self.runtime(spool_max_bytes=1024*1024)
        # Fill pending spool nearly to cap with a valid row.
        payload="x"*(1024*1024-500)
        with rt.state.connect() as db: db.execute("INSERT INTO spool(observation_id,cycle_id,capability_id,payload_json,payload_bytes,created_at,expires_at) VALUES(?,?,?,?,?,?,?)",("fill","old","x",payload,len(payload),BASE_MS,BASE_MS+9999999))
        code,res=rt.collect_cycle(REQ); self.assertEqual(code,503); self.assertTrue(any(e["class"]=="SPOOL_FULL" for e in res["errors"]))
    def test_state_version_incompatibility_fail_closed(self):
        rt=self.runtime()
        with rt.state.connect() as db: db.execute("UPDATE meta SET value='999' WHERE key='state_schema_version'")
        with self.assertRaises(StateError): rt.state.compatibility_check()
        code,res=rt.readiness(); self.assertEqual(code,503); self.assertEqual(res["error_class"],"STATE_SCHEMA_INCOMPATIBLE")
    def test_readiness_and_health(self):
        rt=self.runtime(); self.assertEqual(rt.health()["status"],"PASS"); self.assertEqual(rt.readiness()[0],200)
    def test_graceful_shutdown_rejects_new_cycle(self):
        rt=self.runtime(); rt.begin_shutdown(); code,res=rt.collect_cycle(REQ); self.assertEqual(code,503); self.assertEqual(rt.health()["status"],"FAIL")
    def test_provider_timeout_classification(self): self.assertEqual(D8Runtime._classify_exception(TimeoutError("timeout")),"PROVIDER_TIMEOUT")
    def test_rate_limit_classification(self): self.assertEqual(D8Runtime._classify_exception(RuntimeError("HTTP 429 rate limit")),"PROVIDER_RATE_LIMIT")
    def test_malformed_provider_payload(self):
        class Bad:
            def collect(self,*a,**k): return {"status":"PASS","observations":[{"bad":1}]}
        rt=self.runtime(Bad()); code,res=rt.collect_cycle(REQ); self.assertIn(res["overall_status"],{"FAIL","DEGRADED"}); self.assertTrue(any(e["class"]=="PROVIDER_SCHEMA" for e in res["errors"]))
    def test_ledger_lifecycle_terminal(self):
        rt=self.runtime(); _,res=rt.collect_cycle(REQ)
        with rt.state.connect() as db:
            cycle=db.execute("SELECT status,response_json FROM cycles WHERE cycle_id=?",(res["cycle_id"],)).fetchone(); ledger=db.execute("SELECT COUNT(*) FROM capability_ledger WHERE cycle_id=?",(res["cycle_id"],)).fetchone()[0]
        self.assertEqual(cycle[0],"PASS"); self.assertGreater(ledger,0); self.assertEqual(json.loads(cycle[1])["ledger_status"],"TERMINAL")
    def test_lease_heartbeat_renewal_primitive(self):
        rt=self.runtime(); cid=cycle_id_for(REQ["expected_schedule_at"])
        state,_,_,_=rt.state.acquire(slot=REQ["expected_schedule_at"],cycle_id=cid,now_ms=BASE_MS)
        self.assertEqual(state,"OWNER")
        with rt.state.connect() as db: before=db.execute("SELECT lease_until FROM leases WHERE slot=?",(REQ["expected_schedule_at"],)).fetchone()[0]
        self.assertTrue(rt.state.renew_lease(slot=REQ["expected_schedule_at"],cycle_id=cid,now_ms=BASE_MS+10_000))
        with rt.state.connect() as db: after=db.execute("SELECT lease_until FROM leases WHERE slot=?",(REQ["expected_schedule_at"],)).fetchone()[0]
        self.assertGreater(after,before)

    def test_forward_ack_and_post_ack_retention(self):
        rt=self.runtime(); _,res=rt.collect_cycle(REQ)
        with rt.state.connect() as db: ids=[r[0] for r in db.execute("SELECT observation_id FROM spool WHERE cycle_id=?",(res["cycle_id"],)).fetchall()]
        self.assertGreater(len(ids),0); self.assertEqual(rt.state.mark_forwarded(ids,BASE_MS+60_000),len(ids))
        with rt.state.connect() as db: self.assertEqual(db.execute("SELECT COUNT(*) FROM spool WHERE state='FORWARDED'").fetchone()[0],len(ids))
        self.assertEqual(rt.state.sweep_forwarded(BASE_MS+60_000+rt.config.spool_retention_seconds*1000+1),len(ids))

    def test_failed_hot_promotion_preserves_old_hot_and_is_explicit(self):
        rt=self.runtime(); rt.collect_cycle(REQ); old=rt.state.diagnostics()["hot_cycle_id"]
        later=BASE_MS+5*60_000; req=dict(REQ,expected_schedule_at=utc_iso(later)); rt.clock_ms=lambda: later+30_000
        real=rt.state.terminalize
        def fail_promotion(**kwargs):
            if kwargs.get("promote"): raise StateError("HOT_PROMOTION_FAILED: injected")
            return real(**kwargs)
        rt.state.terminalize=fail_promotion
        code,res=rt.collect_cycle(req)
        self.assertEqual(code,503); self.assertTrue(any(e["class"]=="HOT_PROMOTION_FAILED" for e in res["errors"])); self.assertEqual(rt.state.diagnostics()["hot_cycle_id"],old)

    def test_state_io_failure_is_explicit(self):
        rt=self.runtime(); real=rt.state.checkpoint_capability
        def fail_once(**kwargs): raise StateError("STATE_IO: injected")
        rt.state.checkpoint_capability=fail_once
        code,res=rt.collect_cycle(REQ)
        self.assertEqual(code,503); self.assertTrue(any(e["class"]=="STATE_IO" for e in res["errors"])); self.assertEqual(res["hot_promotion"],"PREVIOUS_HOT_PRESERVED")

if __name__ == "__main__": unittest.main()
