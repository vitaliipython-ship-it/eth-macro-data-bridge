from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from d8_runtime import (
    CAPABILITY_POLICY,
    CANONICAL_SLOT,
    EXISTING_CYCLE_RECOVERY_SECONDS,
    FUTURE_SKEW_SECONDS,
    MAX_ATTEMPTS,
    RUNTIME_CONTRACT_VERSION,
    STALE_SLOT_SECONDS,
    D8Runtime,
    D8State,
    RuntimeConfig,
    StateError,
    cycle_id_for,
    new_admission_is_stale,
    utc_iso,
    validate_request,
    validate_request_common,
)

PHYSICAL_REPRO_SOURCE = "5a38713098a4632b2ca8ea9a369e869de979205a"
SUCCESSOR_SOURCE = "successor-repair-source"
SLOT_MS = int(datetime(2026, 8, 18, 15, 50, tzinfo=timezone.utc).timestamp() * 1000)
PHYSICAL_CYCLE_B = "d8c-c4063f22f5d9ceef61fcde2568051d26"
LEASE_SECONDS = 240


def request(slot_ms: int = SLOT_MS, trace_id: str = "stale-window-recovery") -> dict:
    return {
        "schema_version": "eth-macro-d8-collect-cycle-request/1.0.0",
        "expected_schedule_at": utc_iso(slot_ms),
        "canonical_slot": CANONICAL_SLOT,
        "trace_id": trace_id,
    }


class MutableClock:
    def __init__(self, now_ms: int):
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms


class CountingCore:
    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.calls: dict[str, int] = {}
        self._lock = threading.Lock()

    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict:
        with self._lock:
            self.calls[capability_id] = self.calls.get(capability_id, 0) + 1
        if self.delay:
            time.sleep(self.delay)
        if capability_id == "binance-usdm.m5-current":
            rows = []
            for idx in range(12):
                rows.append(
                    {
                        "series_id": f"derivatives.binance-usdm.recovery-fixture-{idx}",
                        "provider_timestamp_at": utc_iso(expected_ms),
                        "finality": "OBSERVED_STATE",
                        "freshness": {
                            "status": "LIVE_USABLE",
                            "age_seconds": 0,
                            "target_cadence_seconds": 300,
                        },
                        "value": {"slot_ms": expected_ms, "idx": idx},
                        "d9_target": "SAMPLED_SCHEDULE",
                    }
                )
            return {"status": "PASS", "observations": rows}
        provider = next(c["provider"] for c in CAPABILITY_POLICY if c["id"] == capability_id)
        return {
            "status": "PASS",
            "observations": [
                {
                    "series_id": f"fixture.{provider}.{capability_id}",
                    "provider_timestamp_at": utc_iso(expected_ms),
                    "finality": "FINALIZED",
                    "freshness": {
                        "status": "LIVE_USABLE",
                        "age_seconds": 0,
                        "target_cadence_seconds": 300,
                    },
                    "value": {"slot_ms": expected_ms, "capability": capability_id},
                    "d9_target": "FIXED_GRID",
                }
            ],
        }


class RecoveryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def config(
        self,
        *,
        source_revision: str,
        owner_id: str,
        profile: str = "VPS_SHADOW",
        lease_seconds: int = LEASE_SECONDS,
    ) -> RuntimeConfig:
        return RuntimeConfig(
            state_root=self.root,
            profile=profile,
            source_revision=source_revision,
            runtime_revision=RUNTIME_CONTRACT_VERSION,
            lease_seconds=lease_seconds,
            owner_id=owner_id,
        )

    def runtime(
        self,
        clock: MutableClock,
        core: CountingCore,
        *,
        source_revision: str,
        owner_id: str,
        profile: str = "VPS_SHADOW",
        lease_seconds: int = LEASE_SECONDS,
    ) -> D8Runtime:
        return D8Runtime(
            self.config(
                source_revision=source_revision,
                owner_id=owner_id,
                profile=profile,
                lease_seconds=lease_seconds,
            ),
            core,
            clock_ms=clock,
        )

    def seed_owned_cycle(
        self,
        rt: D8Runtime,
        *,
        slot_ms: int,
        now_ms: int,
        checkpoint_capabilities: tuple[str, ...] = (),
    ) -> tuple[str, int]:
        req = validate_request_common(request(slot_ms), now_ms=now_ms)
        self.assertFalse(new_admission_is_stale(req, now_ms=now_ms))
        cid = cycle_id_for(req["expected_schedule_at"])
        state, _, attempt, _ = rt.state.acquire(
            slot=req["expected_schedule_at"],
            cycle_id=cid,
            now_ms=now_ms,
            new_admission_allowed=True,
        )
        self.assertEqual(state, "OWNER")
        for capability_id in checkpoint_capabilities:
            cap = next(c for c in CAPABILITY_POLICY if c["id"] == capability_id)
            raw = CountingCore().collect(
                capability_id,
                expected_ms=slot_ms,
                cycle_id=cid,
                staging_root=self.root,
            )
            obs = rt._normalize_observations(
                cap,
                raw["observations"],
                cid,
                req["expected_schedule_at"],
                now_ms + 1,
            )
            ledger = rt._ledger_row(cap, "PASS", None, obs, now_ms + 1)
            rt.state.checkpoint_capability(
                cycle_id=cid,
                attempt=attempt,
                ledger_row=ledger,
                observations=obs,
                now_ms=now_ms + 1,
            )
        return cid, attempt


class PrimaryStaleWindowLeaseOverlapCase(RecoveryFixture):
    def test_preserved_cycle_b_recovers_after_new_admission_deadline_and_reuses_12_of_12(self):
        self.assertEqual(cycle_id_for(utc_iso(SLOT_MS)), PHYSICAL_CYCLE_B)
        initial_now = SLOT_MS + 989_000
        clock = MutableClock(initial_now)
        initial_core = CountingCore()
        initial = self.runtime(
            clock,
            initial_core,
            source_revision=PHYSICAL_REPRO_SOURCE,
            owner_id="physical-owner",
        )
        cid, attempt = self.seed_owned_cycle(
            initial,
            slot_ms=SLOT_MS,
            now_ms=initial_now,
            checkpoint_capabilities=("binance-usdm.m5-current",),
        )
        self.assertEqual((cid, attempt), (PHYSICAL_CYCLE_B, 1))
        checkpoint, _ = initial.state.load_checkpoint(cid, "binance-usdm.m5-current")
        self.assertEqual((len(checkpoint), len({o["observation_id"] for o in checkpoint})), (12, 12))
        original_ids = [o["observation_id"] for o in checkpoint]
        self.assertTrue(all(o["provenance"]["source_revision"] == PHYSICAL_REPRO_SOURCE for o in checkpoint))

        with initial.state.connect() as db:
            lease_until = int(
                db.execute("SELECT lease_until FROM leases WHERE cycle_id=?", (cid,)).fetchone()[0]
            )
            cycle_source = db.execute(
                "SELECT source_revision FROM cycles WHERE cycle_id=?", (cid,)
            ).fetchone()[0]
        self.assertEqual(cycle_source, PHYSICAL_REPRO_SOURCE)
        self.assertGreater(lease_until, SLOT_MS + STALE_SLOT_SECONDS * 1000)

        clock.now_ms = SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1
        live_retry = self.runtime(
            clock,
            CountingCore(),
            source_revision=SUCCESSOR_SOURCE,
            owner_id="successor-live-probe",
        )
        code, busy = live_retry.collect_cycle(request())
        self.assertEqual(code, 409)
        self.assertEqual(busy["errors"][0]["class"], "LOCK_BUSY")

        clock.now_ms = lease_until + 1
        recovery_core = CountingCore()
        recovered = self.runtime(
            clock,
            recovery_core,
            source_revision=SUCCESSOR_SOURCE,
            owner_id="successor-owner",
        )
        code, result = recovered.collect_cycle(request())
        self.assertEqual((code, result["overall_status"]), (200, "PASS"))
        self.assertEqual(result["cycle_id"], PHYSICAL_CYCLE_B)
        self.assertEqual(result["attempt"], 2)
        self.assertTrue(result["stale_lock_recovered"])
        self.assertTrue(
            result["capability_statuses"]["binance-usdm.m5-current"]["reused_durable_checkpoint"]
        )
        self.assertEqual(recovery_core.calls.get("binance-usdm.m5-current", 0), 0)

        with recovered.state.connect() as db:
            cycle = db.execute(
                "SELECT cycle_id,attempt,status,source_revision FROM cycles WHERE cycle_id=?", (cid,)
            ).fetchone()
            member_ids = [
                r[0]
                for r in db.execute(
                    "SELECT observation_id FROM cycle_checkpoint_observations "
                    "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current' ORDER BY position",
                    (cid,),
                ).fetchall()
            ]
        self.assertEqual((cycle["cycle_id"], cycle["attempt"], cycle["status"]), (cid, 2, "PASS"))
        self.assertEqual(cycle["source_revision"], PHYSICAL_REPRO_SOURCE)
        self.assertEqual(member_ids, original_ids)

    def test_heartbeat_renewal_beyond_slot_deadline_stays_busy_then_recovers(self):
        initial_now = SLOT_MS + (STALE_SLOT_SECONDS * 1000 - 20_000)
        clock = MutableClock(initial_now)
        rt = self.runtime(
            clock,
            CountingCore(),
            source_revision=PHYSICAL_REPRO_SOURCE,
            owner_id="heartbeat-owner",
        )
        cid, attempt = self.seed_owned_cycle(rt, slot_ms=SLOT_MS, now_ms=initial_now)
        self.assertEqual(attempt, 1)

        heartbeat_now = SLOT_MS + STALE_SLOT_SECONDS * 1000 + 60_000
        self.assertTrue(rt.state.renew_lease(slot=utc_iso(SLOT_MS), cycle_id=cid, now_ms=heartbeat_now))
        with rt.state.connect() as db:
            renewed_until = int(
                db.execute("SELECT lease_until FROM leases WHERE cycle_id=?", (cid,)).fetchone()[0]
            )
        self.assertGreater(renewed_until, SLOT_MS + STALE_SLOT_SECONDS * 1000)

        clock.now_ms = heartbeat_now + 1
        probe = self.runtime(
            clock,
            CountingCore(),
            source_revision=SUCCESSOR_SOURCE,
            owner_id="heartbeat-probe",
        )
        code, result = probe.collect_cycle(request())
        self.assertEqual(code, 409)
        self.assertEqual(result["errors"][0]["class"], "LOCK_BUSY")

        equally_old_missing_slot = SLOT_MS - 5 * 60_000
        code, invalid = probe.collect_cycle(request(equally_old_missing_slot))
        self.assertEqual(code, 400)
        self.assertEqual(invalid["errors"][0]["class"], "REQUEST_INVALID")

        clock.now_ms = renewed_until + 1
        successor = self.runtime(
            clock,
            CountingCore(),
            source_revision=SUCCESSOR_SOURCE,
            owner_id="heartbeat-successor",
        )
        code, recovered = successor.collect_cycle(request())
        self.assertEqual((code, recovered["overall_status"]), (200, "PASS"))
        self.assertEqual(recovered["cycle_id"], cid)
        self.assertEqual(recovered["attempt"], 2)
        self.assertTrue(recovered["stale_lock_recovered"])


class RequestAndBoundaryCase(RecoveryFixture):
    def test_new_admission_stale_boundary_is_inclusive_at_1200_seconds(self):
        validate_request(request(), now_ms=SLOT_MS + STALE_SLOT_SECONDS * 1000 - 1)
        validate_request(request(), now_ms=SLOT_MS + STALE_SLOT_SECONDS * 1000)
        with self.assertRaisesRegex(ValueError, "stale slot"):
            validate_request(request(), now_ms=SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1)

    def test_future_skew_boundary_is_inclusive_at_120_seconds(self):
        future_slot = SLOT_MS + 5 * 60_000
        validate_request_common(
            request(future_slot),
            now_ms=future_slot - FUTURE_SKEW_SECONDS * 1000,
        )
        with self.assertRaisesRegex(ValueError, "future slot"):
            validate_request_common(
                request(future_slot),
                now_ms=future_slot - FUTURE_SKEW_SECONDS * 1000 - 1,
            )

    def _seed_prior_with_lease(self, *, lease_until: int, attempt: int = 1, status: str = "STARTED"):
        cfg = self.config(source_revision=PHYSICAL_REPRO_SOURCE, owner_id="old-owner")
        state = D8State(cfg)
        cid = cycle_id_for(utc_iso(SLOT_MS))
        with state.connect() as db:
            db.execute(
                "INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,started_at,source_revision,runtime_revision) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    cid,
                    utc_iso(SLOT_MS),
                    utc_iso(SLOT_MS),
                    attempt,
                    status,
                    utc_iso(lease_until - 60_000),
                    PHYSICAL_REPRO_SOURCE,
                    RUNTIME_CONTRACT_VERSION,
                ),
            )
            db.execute(
                "INSERT INTO leases(slot,cycle_id,owner_id,acquired_at,lease_until) VALUES(?,?,?,?,?)",
                (utc_iso(SLOT_MS), cid, "old-owner", lease_until - 60_000, lease_until),
            )
        return state, cid

    def test_lease_boundary_minus_one_expired_equal_and_plus_one_live(self):
        for offset, expected in ((-1, "OWNER"), (0, "BUSY"), (1, "BUSY")):
            with self.subTest(offset=offset):
                with tempfile.TemporaryDirectory() as td:
                    self.root = Path(td)
                    now_ms = SLOT_MS + 30 * 60_000
                    state, cid = self._seed_prior_with_lease(lease_until=now_ms + offset)
                    state.config = self.config(source_revision=SUCCESSOR_SOURCE, owner_id="new-owner")
                    outcome, _, _, _ = state.acquire(
                        slot=utc_iso(SLOT_MS),
                        cycle_id=cid,
                        now_ms=now_ms,
                        new_admission_allowed=False,
                    )
                    self.assertEqual(outcome, expected)

    def test_recovery_bound_minus_one_equal_and_plus_one(self):
        recovery_ms = EXISTING_CYCLE_RECOVERY_SECONDS * 1000
        for offset, expected in ((-1, "OWNER"), (0, "OWNER"), (1, "RECOVERY_EXPIRED")):
            with self.subTest(offset=offset):
                with tempfile.TemporaryDirectory() as td:
                    self.root = Path(td)
                    anchor = SLOT_MS + 10 * 60_000
                    state, cid = self._seed_prior_with_lease(lease_until=anchor)
                    state.config = self.config(source_revision=SUCCESSOR_SOURCE, owner_id="new-owner")
                    outcome, _, _, _ = state.acquire(
                        slot=utc_iso(SLOT_MS),
                        cycle_id=cid,
                        now_ms=anchor + recovery_ms + offset,
                        new_admission_allowed=False,
                    )
                    self.assertEqual(outcome, expected)

    def test_stale_slot_without_exact_cycle_is_request_invalid(self):
        clock = MutableClock(SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1)
        rt = self.runtime(
            clock,
            CountingCore(),
            source_revision=SUCCESSOR_SOURCE,
            owner_id="missing-cycle",
        )
        code, result = rt.collect_cycle(request())
        self.assertEqual(code, 400)
        self.assertEqual(result["errors"][0]["class"], "REQUEST_INVALID")

    def test_malformed_and_different_slot_fail_closed(self):
        clock = MutableClock(SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1)
        rt = self.runtime(clock, CountingCore(), source_revision=SUCCESSOR_SOURCE, owner_id="guard")
        malformed = request()
        malformed["expected_schedule_at"] = "2026-08-18T15:51:00Z"
        code, result = rt.collect_cycle(malformed)
        self.assertEqual((code, result["errors"][0]["class"]), (400, "REQUEST_INVALID"))

        different = SLOT_MS - 5 * 60_000
        code, result = rt.collect_cycle(request(different))
        self.assertEqual((code, result["errors"][0]["class"]), (400, "REQUEST_INVALID"))

    def test_corrupt_cycle_identity_fails_closed(self):
        clock = MutableClock(SLOT_MS + 30_000)
        rt = self.runtime(clock, CountingCore(), source_revision=SUCCESSOR_SOURCE, owner_id="guard")
        with rt.state.connect() as db:
            db.execute(
                "INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,started_at,source_revision,runtime_revision) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    "d8c-corrupt",
                    utc_iso(SLOT_MS),
                    utc_iso(SLOT_MS),
                    1,
                    "STARTED",
                    utc_iso(clock.now_ms),
                    PHYSICAL_REPRO_SOURCE,
                    RUNTIME_CONTRACT_VERSION,
                ),
            )
        code, result = rt.collect_cycle(request())
        self.assertEqual(code, 409)
        self.assertEqual(result["errors"][0]["class"], "LEDGER_CONFLICT")

    def test_max_attempts_remains_authoritative(self):
        now_ms = SLOT_MS + 30 * 60_000
        state, cid = self._seed_prior_with_lease(lease_until=now_ms - 1, attempt=MAX_ATTEMPTS)
        state.config = self.config(source_revision=SUCCESSOR_SOURCE, owner_id="new-owner")
        outcome, _, attempt, _ = state.acquire(
            slot=utc_iso(SLOT_MS),
            cycle_id=cid,
            now_ms=now_ms,
            new_admission_allowed=False,
        )
        self.assertEqual((outcome, attempt), ("EXHAUSTED", MAX_ATTEMPTS))


class OwnershipAndConcurrencyCase(RecoveryFixture):
    def test_stale_owner_cannot_renew_release_checkpoint_or_terminalize_after_takeover(self):
        initial_now = SLOT_MS + 60_000
        old_clock = MutableClock(initial_now)
        old = self.runtime(
            old_clock,
            CountingCore(),
            source_revision=PHYSICAL_REPRO_SOURCE,
            owner_id="old-owner",
            lease_seconds=60,
        )
        cid, attempt = self.seed_owned_cycle(old, slot_ms=SLOT_MS, now_ms=initial_now)
        takeover_now = initial_now + 60_001
        new_cfg = self.config(
            source_revision=SUCCESSOR_SOURCE,
            owner_id="new-owner",
            lease_seconds=60,
        )
        new_state = D8State(new_cfg)
        outcome, _, new_attempt, _ = new_state.acquire(
            slot=utc_iso(SLOT_MS),
            cycle_id=cid,
            now_ms=takeover_now,
            new_admission_allowed=True,
        )
        self.assertEqual((outcome, new_attempt), ("OWNER", 2))
        self.assertFalse(old.state.renew_lease(slot=utc_iso(SLOT_MS), cycle_id=cid, now_ms=takeover_now + 1))
        self.assertFalse(
            old.state.release_recoverable(
                utc_iso(SLOT_MS), cid, attempt=attempt, now_ms=takeover_now + 1
            )
        )

        cap = next(c for c in CAPABILITY_POLICY if c["id"] == "binance-spot.m5")
        raw = CountingCore().collect(cap["id"], expected_ms=SLOT_MS, cycle_id=cid, staging_root=self.root)
        obs = old._normalize_observations(cap, raw["observations"], cid, utc_iso(SLOT_MS), takeover_now + 1)
        ledger = old._ledger_row(cap, "PASS", None, obs, takeover_now + 1)
        with self.assertRaisesRegex(StateError, "lease ownership lost"):
            old.state.checkpoint_capability(
                cycle_id=cid,
                attempt=attempt,
                ledger_row=ledger,
                observations=obs,
                now_ms=takeover_now + 1,
            )

        response = {
            "overall_status": "PASS",
            "completed_at": utc_iso(takeover_now + 1),
        }
        with self.assertRaisesRegex(StateError, "lease ownership lost"):
            old.state.terminalize(
                cycle_id=cid,
                slot=utc_iso(SLOT_MS),
                attempt=attempt,
                response=response,
                observations=[],
                ledger_rows=[],
                promote=False,
                now_ms=takeover_now + 1,
            )

    def test_two_simultaneous_expired_lease_retries_have_one_owner_and_no_duplicate_collection(self):
        initial_now = SLOT_MS + 60_000
        seed_clock = MutableClock(initial_now)
        seed = self.runtime(
            seed_clock,
            CountingCore(),
            source_revision=PHYSICAL_REPRO_SOURCE,
            owner_id="dead-owner",
            lease_seconds=60,
        )
        cid, _ = self.seed_owned_cycle(seed, slot_ms=SLOT_MS, now_ms=initial_now)
        retry_now = initial_now + 60_001
        shared_core = CountingCore(delay=0.08)
        clock = MutableClock(retry_now)
        rt1 = self.runtime(
            clock,
            shared_core,
            source_revision=SUCCESSOR_SOURCE,
            owner_id="retry-owner-1",
            lease_seconds=60,
        )
        rt2 = self.runtime(
            clock,
            shared_core,
            source_revision=SUCCESSOR_SOURCE,
            owner_id="retry-owner-2",
            lease_seconds=60,
        )
        barrier = threading.Barrier(3)
        results: list[tuple[int, dict]] = []
        lock = threading.Lock()

        def invoke(rt: D8Runtime) -> None:
            barrier.wait()
            result = rt.collect_cycle(request())
            with lock:
                results.append(result)

        t1 = threading.Thread(target=invoke, args=(rt1,))
        t2 = threading.Thread(target=invoke, args=(rt2,))
        t1.start()
        t2.start()
        barrier.wait()
        t1.join()
        t2.join()

        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        busy = next(body for code, body in results if code == 409)
        self.assertEqual(busy["errors"][0]["class"], "LOCK_BUSY")
        with rt1.state.connect() as db:
            cycle = db.execute(
                "SELECT attempt,status FROM cycles WHERE cycle_id=?", (cid,)
            ).fetchone()
        self.assertEqual((cycle["attempt"], cycle["status"]), (2, "PASS"))
        for cap in CAPABILITY_POLICY:
            if cap.get("profiles") and "VPS_SHADOW" not in cap["profiles"]:
                continue
            minute = datetime.fromtimestamp(SLOT_MS / 1000, timezone.utc).minute
            if minute % int(cap["every_minutes"]) == 0:
                self.assertLessEqual(shared_core.calls.get(cap["id"], 0), 1)


class CrashPointMatrixCase(RecoveryFixture):
    def _run_phase(self, checkpoint_capabilities: tuple[str, ...]) -> tuple[dict, CountingCore]:
        initial_now = SLOT_MS + 60_000
        clock = MutableClock(initial_now)
        seed = self.runtime(
            clock,
            CountingCore(),
            source_revision=PHYSICAL_REPRO_SOURCE,
            owner_id="matrix-old",
            lease_seconds=60,
        )
        cid, _ = self.seed_owned_cycle(
            seed,
            slot_ms=SLOT_MS,
            now_ms=initial_now,
            checkpoint_capabilities=checkpoint_capabilities,
        )
        clock.now_ms = initial_now + 60_001
        core = CountingCore()
        successor = self.runtime(
            clock,
            core,
            source_revision=SUCCESSOR_SOURCE,
            owner_id="matrix-new",
            lease_seconds=60,
        )
        code, result = successor.collect_cycle(request())
        self.assertEqual((code, result["overall_status"], result["cycle_id"]), (200, "PASS", cid))
        return result, core

    def test_crash_matrix_cycle_insert_partial_checkpoint_all_due_checkpoints(self):
        result_a, core_a = self._run_phase(())
        self.assertGreater(sum(core_a.calls.values()), 0)

        result_b, core_b = self._run_phase(("binance-spot.m5",))
        self.assertTrue(result_b["capability_statuses"]["binance-spot.m5"]["reused_durable_checkpoint"])
        self.assertEqual(core_b.calls.get("binance-spot.m5", 0), 0)

        due_m5 = (
            "binance-spot.m5",
            "kraken-spot.m5",
            "binance-usdm.m5-current",
            "deribit-perpetual.current",
            "liquidity.current",
        )
        result_d, core_d = self._run_phase(due_m5)
        self.assertTrue(all(result_d["capability_statuses"][cap]["reused_durable_checkpoint"] for cap in due_m5))
        self.assertEqual(sum(core_d.calls.get(cap, 0) for cap in due_m5), 0)


if __name__ == "__main__":
    unittest.main()
