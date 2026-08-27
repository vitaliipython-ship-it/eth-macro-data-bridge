from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import internal_market_watchdog as watchdog


class FakeClient:
    def __init__(self, *, active=None, recovery_id=9001, active_error=None, dispatch_error=None):
        self.active = list(active or [])
        self.recovery_id = recovery_id
        self.active_error = active_error
        self.dispatch_error = dispatch_error
        self.dispatches: list[str] = []

    def active_update_runs(self):
        if self.active_error:
            raise watchdog.WatchdogError("GITHUB_RUN_STATE_UNAVAILABLE", self.active_error)
        return list(self.active)

    def dispatch_workflow(self, workflow_file, *, ref=watchdog.DEFAULT_REF):
        if self.dispatch_error:
            raise RuntimeError(self.dispatch_error)
        self.dispatches.append(workflow_file)
        return self.recovery_id


def snapshot(verdict: str, age: int = 4000) -> watchdog.FreshnessSnapshot:
    return watchdog.FreshnessSnapshot(
        check_time_utc="2026-08-27T09:00:00Z",
        canonical_generation_time_utc="2026-08-27T07:53:20Z",
        canonical_age_seconds=age,
        stale_threshold_seconds=3900,
        freshness_verdict=verdict,
        evidence=({},),
    )


class WatchdogDecisionTests(unittest.TestCase):
    def test_fresh_generation_no_dispatch(self):
        client = FakeClient()
        reason = watchdog.perform_watchdog_check(snapshot("FRESH", 100), client, watchdog.WatchdogState(), monotonic_now=10)
        self.assertEqual(reason, "FRESH_NO_ACTION")
        self.assertEqual(client.dispatches, [])

    def test_stale_generation_dispatches_existing_update_workflow(self):
        client = FakeClient(recovery_id=101)
        state = watchdog.WatchdogState()
        reason = watchdog.perform_watchdog_check(snapshot("STALE"), client, state, monotonic_now=100)
        self.assertEqual(reason, "STALE_RECOVERY_DISPATCHED")
        self.assertEqual(client.dispatches, [watchdog.UPDATE_WORKFLOW_FILE])
        self.assertEqual(state.last_recovery_dispatch_monotonic, 100)

    def test_stale_queued_update_run_skips_duplicate(self):
        client = FakeClient(active=[{"id": 11, "status": "queued"}])
        reason = watchdog.perform_watchdog_check(snapshot("STALE"), client, watchdog.WatchdogState(), monotonic_now=100)
        self.assertEqual(reason, "STALE_EXISTING_UPDATE_RUN")
        self.assertEqual(client.dispatches, [])

    def test_stale_in_progress_update_run_skips_duplicate(self):
        client = FakeClient(active=[{"id": 12, "status": "in_progress"}])
        reason = watchdog.perform_watchdog_check(snapshot("STALE"), client, watchdog.WatchdogState(), monotonic_now=100)
        self.assertEqual(reason, "STALE_EXISTING_UPDATE_RUN")
        self.assertEqual(client.dispatches, [])

    def test_stale_cooldown_skips_repeated_dispatch(self):
        client = FakeClient()
        state = watchdog.WatchdogState(last_recovery_dispatch_monotonic=100)
        reason = watchdog.perform_watchdog_check(snapshot("STALE"), client, state, monotonic_now=500, recovery_cooldown_seconds=1200)
        self.assertEqual(reason, "RECOVERY_COOLDOWN_ACTIVE")
        self.assertEqual(client.dispatches, [])

    def test_run_state_failure_fails_closed(self):
        client = FakeClient(active_error="boom")
        with self.assertRaisesRegex(watchdog.WatchdogError, "boom") as ctx:
            watchdog.perform_watchdog_check(snapshot("STALE"), client, watchdog.WatchdogState(), monotonic_now=100)
        self.assertEqual(ctx.exception.code, "GITHUB_RUN_STATE_UNAVAILABLE")

    def test_recovery_dispatch_failure_fails_closed(self):
        client = FakeClient(dispatch_error="dispatch rejected")
        with self.assertRaises(watchdog.WatchdogError) as ctx:
            watchdog.perform_watchdog_check(snapshot("STALE"), client, watchdog.WatchdogState(), monotonic_now=100)
        self.assertEqual(ctx.exception.code, "RECOVERY_DISPATCH_FAILED")


class CanonicalFreshnessReuseTests(unittest.TestCase):
    def test_reuses_existing_canonical_freshness_evaluator(self):
        captured = {}

        def evaluator(request, *, now=None):
            captured.update(request)
            return {
                "evaluated_at_utc": "2026-08-27T09:00:00Z",
                "persisted_fresh_enough": True,
                "reasons": [],
                "evidence": [
                    {
                        "logical_id": f"domain:{domain}",
                        "generated_at_utc": "2026-08-27T08:30:00Z",
                        "age_seconds": 1800,
                    }
                    for domain in watchdog.ALLOWED_DOMAINS
                ],
            }

        result = watchdog.evaluate_canonical_durable_freshness(
            3900,
            now=datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc),
            refresh_checkout=lambda: None,
            evaluator=evaluator,
        )
        self.assertEqual(result.freshness_verdict, "FRESH")
        self.assertEqual(captured["required_domains"], sorted(watchdog.ALLOWED_DOMAINS))
        self.assertEqual(captured["required_series"], [])
        self.assertEqual(captured["max_generation_age_seconds"], 3900)

    def test_only_canonical_staleness_is_recoverable(self):
        def evaluator(request, *, now=None):
            return {
                "evaluated_at_utc": "2026-08-27T09:00:00Z",
                "persisted_fresh_enough": False,
                "reasons": ["STALE:domain:SPOT:4000"],
                "evidence": [
                    {
                        "logical_id": "domain:SPOT",
                        "generated_at_utc": "2026-08-27T07:53:20Z",
                        "age_seconds": 4000,
                    }
                ],
            }

        result = watchdog.evaluate_canonical_durable_freshness(
            3900,
            refresh_checkout=lambda: None,
            evaluator=evaluator,
        )
        self.assertEqual(result.freshness_verdict, "STALE")
        self.assertEqual(result.canonical_age_seconds, 4000)

    def test_freshness_authority_unavailable_fails_closed(self):
        def evaluator(request, *, now=None):
            return {
                "evaluated_at_utc": "2026-08-27T09:00:00Z",
                "persisted_fresh_enough": False,
                "reasons": ["MISSING:domain:OPTIONS"],
                "evidence": [{"logical_id": "domain:OPTIONS", "status": "MISSING"}],
            }

        with self.assertRaises(watchdog.WatchdogError) as ctx:
            watchdog.evaluate_canonical_durable_freshness(3900, refresh_checkout=lambda: None, evaluator=evaluator)
        self.assertEqual(ctx.exception.code, "FRESHNESS_AUTHORITY_UNAVAILABLE")

    def test_checkout_refresh_failure_fails_closed(self):
        def refresh():
            raise RuntimeError("fetch failed")

        with self.assertRaises(watchdog.WatchdogError) as ctx:
            watchdog.evaluate_canonical_durable_freshness(3900, refresh_checkout=refresh)
        self.assertEqual(ctx.exception.code, "FRESHNESS_AUTHORITY_UNAVAILABLE")


class SelfDispatchTests(unittest.TestCase):
    def test_self_dispatch_success_accepts_returned_successor_id(self):
        client = watchdog.GitHubActionsClient("owner/repo", "token")
        client.dispatch_workflow = Mock(return_value=77)
        successor = client.dispatch_successor(66, proof_timeout_seconds=1)
        self.assertEqual(successor, 77)
        client.dispatch_workflow.assert_called_once_with(watchdog.WATCHDOG_WORKFLOW_FILE)

    def test_self_dispatch_failure_is_explicit(self):
        client = watchdog.GitHubActionsClient("owner/repo", "token")
        client.dispatch_workflow = Mock(side_effect=RuntimeError("nope"))
        with self.assertRaises(watchdog.WatchdogError) as ctx:
            client.dispatch_successor(66, proof_timeout_seconds=1)
        self.assertEqual(ctx.exception.code, "SELF_DISPATCH_FAILED")


class StaticWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.watchdog_workflow = (ROOT / ".github" / "workflows" / "internal-market-watchdog.yml").read_text(encoding="utf-8")
        cls.update_workflow = (ROOT / ".github" / "workflows" / "update-market.yml").read_text(encoding="utf-8")
        cls.helper = (ROOT / "tools" / "internal_market_watchdog.py").read_text(encoding="utf-8")

    def test_watchdog_has_workflow_dispatch_only_and_no_schedule(self):
        trigger_block = self.watchdog_workflow.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger_block)
        self.assertNotIn("schedule:", trigger_block)
        self.assertNotIn("push:", trigger_block)
        self.assertNotIn("pull_request:", trigger_block)

    def test_native_update_cron_is_unchanged(self):
        self.assertIn('cron: "17 * * * *"', self.update_workflow)

    def test_watchdog_does_not_call_collector_or_providers_directly(self):
        combined = self.watchdog_workflow + "\n" + self.helper
        self.assertNotIn("src/collector.py", combined)
        self.assertNotIn("deribit.com", combined)
        self.assertNotIn("api.binance", combined)
        self.assertNotIn("api.kraken", combined)

    def test_watchdog_concurrency_prevents_active_overlap(self):
        self.assertIn("group: internal-market-watchdog", self.watchdog_workflow)
        self.assertIn("cancel-in-progress: false", self.watchdog_workflow)

    def test_minimum_token_permissions(self):
        permission_block = self.watchdog_workflow.split("permissions:", 1)[1].split("concurrency:", 1)[0]
        lines = {line.strip() for line in permission_block.splitlines() if line.strip()}
        self.assertEqual(lines, {"contents: read", "actions: write"})
        self.assertNotIn("secrets.", self.watchdog_workflow)

    def test_bounded_runtime_and_timing(self):
        self.assertEqual(watchdog.CHECK_INTERVAL_SECONDS, 180)
        self.assertEqual(watchdog.STALE_THRESHOLD_SECONDS, 3900)
        self.assertEqual(watchdog.RECOVERY_DISPATCH_COOLDOWN_SECONDS, 1200)
        self.assertEqual(watchdog.WATCHDOG_GENERATION_RUNTIME_SECONDS, 17100)
        self.assertLess(watchdog.WATCHDOG_GENERATION_RUNTIME_SECONDS, 6 * 60 * 60)

    def test_watchdog_is_only_execution_orchestrator(self):
        self.assertFalse(watchdog.WATCHDOG_IS_MARKET_DATA_AUTHORITY)
        self.assertFalse(watchdog.WATCHDOG_IS_STORAGE_AUTHORITY)
        self.assertFalse(watchdog.WATCHDOG_IS_PROVIDER_AUTHORITY)
        self.assertFalse(watchdog.WATCHDOG_IS_FRESHNESS_AUTHORITY)
        self.assertEqual(watchdog.WATCHDOG_ROLE, "TEMPORARY_EXECUTION_ORCHESTRATOR")
        self.assertTrue(watchdog.TEMPORARY_FAILOVER)


if __name__ == "__main__":
    unittest.main()
