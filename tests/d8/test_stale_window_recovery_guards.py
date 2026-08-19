from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from d8_runtime import (
    CAPABILITY_POLICY,
    RUNTIME_CONTRACT_VERSION,
    STALE_SLOT_SECONDS,
    D8Runtime,
    D8State,
    RuntimeConfig,
    cycle_id_for,
    utc_iso,
    validate_request_common,
)

SLOT_MS = int(datetime(2026, 8, 18, 15, 50, tzinfo=timezone.utc).timestamp() * 1000)
OLD_SOURCE = "5a38713098a4632b2ca8ea9a369e869de979205a"
NEW_SOURCE = "successor-repair-source"


def request(slot_ms: int = SLOT_MS) -> dict:
    return {
        "schema_version": "eth-macro-d8-collect-cycle-request/1.0.0",
        "expected_schedule_at": utc_iso(slot_ms),
        "canonical_slot": "M5",
        "trace_id": "stale-window-guards",
    }


class Clock:
    def __init__(self, now_ms: int):
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms


class CountingCore:
    def __init__(self):
        self.calls: dict[str, int] = {}

    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict:
        self.calls[capability_id] = self.calls.get(capability_id, 0) + 1
        if capability_id == "binance-usdm.m5-current":
            observations = [
                {
                    "series_id": f"derivatives.binance-usdm.guard-{idx}",
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
                for idx in range(12)
            ]
            return {"status": "PASS", "observations": observations}
        provider = next(item["provider"] for item in CAPABILITY_POLICY if item["id"] == capability_id)
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


class RecoveryGuardCase(unittest.TestCase):
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
        runtime_revision: str = RUNTIME_CONTRACT_VERSION,
        lease_seconds: int = 60,
    ) -> RuntimeConfig:
        return RuntimeConfig(
            state_root=self.root,
            profile="VPS_SHADOW",
            source_revision=source_revision,
            runtime_revision=runtime_revision,
            lease_seconds=lease_seconds,
            owner_id=owner_id,
        )

    def runtime(
        self,
        *,
        clock: Clock,
        core: CountingCore,
        source_revision: str,
        owner_id: str,
        runtime_revision: str = RUNTIME_CONTRACT_VERSION,
        lease_seconds: int = 60,
    ) -> D8Runtime:
        return D8Runtime(
            self.config(
                source_revision=source_revision,
                owner_id=owner_id,
                runtime_revision=runtime_revision,
                lease_seconds=lease_seconds,
            ),
            core,
            clock_ms=clock,
        )

    def seed_usdm_checkpoint(self, *, initial_now: int) -> tuple[D8Runtime, str, int]:
        clock = Clock(initial_now)
        rt = self.runtime(
            clock=clock,
            core=CountingCore(),
            source_revision=OLD_SOURCE,
            owner_id="old-owner",
        )
        normalized = validate_request_common(request(), now_ms=initial_now)
        cid = cycle_id_for(normalized["expected_schedule_at"])
        outcome, _, attempt, _ = rt.state.acquire(
            slot=normalized["expected_schedule_at"],
            cycle_id=cid,
            now_ms=initial_now,
            new_admission_allowed=True,
        )
        self.assertEqual(outcome, "OWNER")
        cap = next(item for item in CAPABILITY_POLICY if item["id"] == "binance-usdm.m5-current")
        raw = CountingCore().collect(
            cap["id"],
            expected_ms=SLOT_MS,
            cycle_id=cid,
            staging_root=self.root,
        )
        obs = rt._normalize_observations(
            cap,
            raw["observations"],
            cid,
            normalized["expected_schedule_at"],
            initial_now + 1,
        )
        ledger = rt._ledger_row(cap, "PASS", None, obs, initial_now + 1)
        rt.state.checkpoint_capability(
            cycle_id=cid,
            attempt=attempt,
            ledger_row=ledger,
            observations=obs,
            now_ms=initial_now + 1,
        )
        self.assertEqual(len(rt.state.load_checkpoint(cid, cap["id"])[0]), 12)
        return rt, cid, attempt

    def test_startup_retains_expired_lease_as_recovery_anchor(self):
        initial_now = SLOT_MS + 60_000
        old, cid, _ = self.seed_usdm_checkpoint(initial_now=initial_now)
        with old.state.connect() as db:
            lease_until = int(db.execute("SELECT lease_until FROM leases WHERE cycle_id=?", (cid,)).fetchone()[0])

        restart_clock = Clock(lease_until + 1)
        successor = self.runtime(
            clock=restart_clock,
            core=CountingCore(),
            source_revision=NEW_SOURCE,
            owner_id="successor-owner",
        )
        with successor.state.connect() as db:
            lease = db.execute(
                "SELECT owner_id,lease_until FROM leases WHERE cycle_id=?", (cid,)
            ).fetchone()
            cycle = db.execute("SELECT status FROM cycles WHERE cycle_id=?", (cid,)).fetchone()
        self.assertIsNotNone(lease)
        self.assertEqual(int(lease["lease_until"]), lease_until)
        self.assertEqual(cycle["status"], "RECOVERABLE")

    def test_incompatible_runtime_contract_fails_closed_without_rewriting_provenance(self):
        now_ms = SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1
        cid = cycle_id_for(utc_iso(SLOT_MS))
        state = D8State(self.config(source_revision=OLD_SOURCE, owner_id="seed"))
        with state.connect() as db:
            db.execute(
                "INSERT INTO cycles(cycle_id,slot,expected_at,attempt,status,started_at,source_revision,runtime_revision) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    cid,
                    utc_iso(SLOT_MS),
                    utc_iso(SLOT_MS),
                    1,
                    "RECOVERABLE",
                    utc_iso(now_ms - 60_000),
                    OLD_SOURCE,
                    "eth-macro-d8-runtime/999.0.0",
                ),
            )
            db.execute(
                "INSERT INTO leases(slot,cycle_id,owner_id,acquired_at,lease_until) VALUES(?,?,?,?,?)",
                (utc_iso(SLOT_MS), cid, "old-owner", now_ms - 120_000, now_ms - 1),
            )
        successor = self.runtime(
            clock=Clock(now_ms),
            core=CountingCore(),
            source_revision=NEW_SOURCE,
            owner_id="successor",
        )
        code, result = successor.collect_cycle(request())
        self.assertEqual(code, 409)
        self.assertEqual(result["errors"][0]["class"], "LEDGER_CONFLICT")
        with successor.state.connect() as db:
            cycle = db.execute(
                "SELECT source_revision,runtime_revision,attempt FROM cycles WHERE cycle_id=?", (cid,)
            ).fetchone()
        self.assertEqual(cycle["source_revision"], OLD_SOURCE)
        self.assertEqual(cycle["runtime_revision"], "eth-macro-d8-runtime/999.0.0")
        self.assertEqual(cycle["attempt"], 1)

    def _prove_invalid_checkpoint_reacquires_full_capability(self, *, partial: bool) -> None:
        initial_now = SLOT_MS + 60_000
        old, cid, _ = self.seed_usdm_checkpoint(initial_now=initial_now)
        with old.state.connect() as db:
            lease_until = int(db.execute("SELECT lease_until FROM leases WHERE cycle_id=?", (cid,)).fetchone()[0])
            if partial:
                db.execute(
                    "DELETE FROM cycle_checkpoint_observations "
                    "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current' AND position=11",
                    (cid,),
                )
            else:
                db.execute(
                    "UPDATE cycle_checkpoint_observations SET payload_json='{}' "
                    "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current' AND position=0",
                    (cid,),
                )
        self.assertEqual(old.state.load_checkpoint(cid, "binance-usdm.m5-current"), ([], None))

        clock = Clock(lease_until + 1)
        core = CountingCore()
        successor = self.runtime(
            clock=clock,
            core=core,
            source_revision=NEW_SOURCE,
            owner_id="successor",
        )
        code, result = successor.collect_cycle(request())
        self.assertEqual((code, result["overall_status"]), (200, "PASS"))
        self.assertEqual(result["cycle_id"], cid)
        self.assertEqual(core.calls.get("binance-usdm.m5-current"), 1)
        self.assertNotIn(
            "reused_durable_checkpoint",
            result["capability_statuses"]["binance-usdm.m5-current"],
        )
        with successor.state.connect() as db:
            count = db.execute(
                "SELECT COUNT(*) FROM cycle_checkpoint_observations "
                "WHERE cycle_id=? AND capability_id='binance-usdm.m5-current'",
                (cid,),
            ).fetchone()[0]
        self.assertEqual(count, 12)

    def test_tampered_checkpoint_causes_safe_full_capability_reacquisition(self):
        self._prove_invalid_checkpoint_reacquires_full_capability(partial=False)

    def test_partial_checkpoint_causes_safe_full_capability_reacquisition(self):
        self._prove_invalid_checkpoint_reacquires_full_capability(partial=True)

    def test_terminal_pass_stale_request_does_not_reenter_recovery(self):
        initial_now = SLOT_MS + 60_000
        clock = Clock(initial_now)
        rt = self.runtime(
            clock=clock,
            core=CountingCore(),
            source_revision=NEW_SOURCE,
            owner_id="terminal-owner",
        )
        code, first = rt.collect_cycle(request())
        self.assertEqual((code, first["overall_status"]), (200, "PASS"))
        self.assertEqual(first["attempt"], 1)

        clock.now_ms = SLOT_MS + STALE_SLOT_SECONDS * 1000 + 1
        restarted = self.runtime(
            clock=clock,
            core=CountingCore(),
            source_revision=NEW_SOURCE,
            owner_id="terminal-probe",
        )
        code, result = restarted.collect_cycle(request())
        self.assertEqual(code, 400)
        self.assertEqual(result["errors"][0]["class"], "REQUEST_INVALID")
        with restarted.state.connect() as db:
            cycle = db.execute(
                "SELECT status,attempt FROM cycles WHERE cycle_id=?", (first["cycle_id"],)
            ).fetchone()
        self.assertEqual((cycle["status"], cycle["attempt"]), ("PASS", 1))


if __name__ == "__main__":
    unittest.main()
