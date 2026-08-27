from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.current_data_transport import (  # noqa: E402
    ALLOWED_DOMAINS,
    evaluate_persisted_freshness,
    normalize_request,
)
from tools.history_consumer import D6_CURRENT_POLICY  # noqa: E402

CHECK_INTERVAL_SECONDS = 180
STALE_THRESHOLD_SECONDS = 3900
RECOVERY_DISPATCH_COOLDOWN_SECONDS = 1200
WATCHDOG_GENERATION_RUNTIME_SECONDS = 17100  # 4h45m; bounded away from GitHub-hosted 6h limit.
UPDATE_WORKFLOW_FILE = "update-market.yml"
UPDATE_WORKFLOW_PATH = ".github/workflows/update-market.yml"
WATCHDOG_WORKFLOW_FILE = "internal-market-watchdog.yml"
WATCHDOG_WORKFLOW_PATH = ".github/workflows/internal-market-watchdog.yml"
WATCHDOG_CONCURRENCY_GROUP = "internal-market-watchdog"
DEFAULT_REF = "main"
API_VERSION = "2026-03-10"
ACTIVE_UPDATE_STATUSES = ("queued", "in_progress")

TEMPORARY_FAILOVER = True
TARGET_REPLACEMENT = "D8/VPS production scheduler/runtime once owner-authorized and active"
WATCHDOG_IS_MARKET_DATA_AUTHORITY = False
WATCHDOG_IS_STORAGE_AUTHORITY = False
WATCHDOG_IS_PROVIDER_AUTHORITY = False
WATCHDOG_IS_FRESHNESS_AUTHORITY = False
WATCHDOG_ROLE = "TEMPORARY_EXECUTION_ORCHESTRATOR"


class WatchdogError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class FreshnessSnapshot:
    check_time_utc: str
    canonical_generation_time_utc: str
    canonical_age_seconds: int
    stale_threshold_seconds: int
    freshness_verdict: str
    evidence: tuple[Mapping[str, object], ...]


@dataclass
class WatchdogState:
    last_recovery_dispatch_monotonic: float | None = None


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", f"invalid canonical generation timestamp: {value!r}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", f"invalid canonical generation timestamp: {value!r}") from exc
    return parsed.astimezone(timezone.utc)


def _run_git(*args: str) -> None:
    try:
        subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", f"cannot refresh canonical origin/main: {detail.strip()}") from exc


def refresh_canonical_checkout() -> None:
    """Refresh local read-only working bytes to the latest canonical default branch."""
    _run_git("fetch", "--quiet", "--no-tags", "origin", DEFAULT_REF)
    _run_git("reset", "--hard", "--quiet", f"origin/{DEFAULT_REF}")


def _freshness_request(stale_threshold_seconds: int) -> dict[str, object]:
    return normalize_request(
        {
            "request_type": "FRESH_CURRENT",
            "required_series": [],
            "required_domains": list(ALLOWED_DOMAINS),
            "max_generation_age_seconds": stale_threshold_seconds,
            "current_policy": D6_CURRENT_POLICY,
        }
    )


def evaluate_canonical_durable_freshness(
    stale_threshold_seconds: int,
    *,
    now: datetime | None = None,
    refresh_checkout: Callable[[], None] = refresh_canonical_checkout,
    evaluator: Callable[..., Mapping[str, object]] = evaluate_persisted_freshness,
) -> FreshnessSnapshot:
    try:
        refresh_checkout()
        result = evaluator(_freshness_request(stale_threshold_seconds), now=now)
    except WatchdogError:
        raise
    except Exception as exc:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", f"canonical freshness evaluation failed: {exc}") from exc

    evidence_obj = result.get("evidence")
    reasons_obj = result.get("reasons")
    if not isinstance(evidence_obj, list) or not evidence_obj:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness evidence is missing")
    if not isinstance(reasons_obj, list) or not all(isinstance(reason, str) for reason in reasons_obj):
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness reasons are invalid")

    non_stale_reasons = [reason for reason in reasons_obj if not reason.startswith("STALE:")]
    if non_stale_reasons:
        raise WatchdogError(
            "FRESHNESS_AUTHORITY_UNAVAILABLE",
            f"canonical freshness authority is non-usable: {non_stale_reasons}",
        )

    evidence: list[Mapping[str, object]] = []
    generation_times: list[datetime] = []
    ages: list[int] = []
    for row in evidence_obj:
        if not isinstance(row, Mapping):
            raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness evidence row is invalid")
        generated = row.get("generated_at_utc")
        age = row.get("age_seconds")
        if not isinstance(generated, str) or isinstance(age, bool) or not isinstance(age, int) or age < 0:
            raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness evidence lacks generation age")
        generation_times.append(_parse_utc(generated))
        ages.append(age)
        evidence.append(row)

    persisted_fresh = result.get("persisted_fresh_enough")
    if persisted_fresh is True and reasons_obj:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness result is internally inconsistent")
    if persisted_fresh not in {True, False}:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical freshness verdict is missing")
    if persisted_fresh is False and not reasons_obj:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "canonical stale verdict lacks reasons")

    return FreshnessSnapshot(
        check_time_utc=str(result.get("evaluated_at_utc") or _format_utc(now or datetime.now(timezone.utc))),
        canonical_generation_time_utc=_format_utc(min(generation_times)),
        canonical_age_seconds=max(ages),
        stale_threshold_seconds=stale_threshold_seconds,
        freshness_verdict="FRESH" if persisted_fresh else "STALE",
        evidence=tuple(evidence),
    )


def emit_freshness(snapshot: FreshnessSnapshot) -> None:
    print(f"CHECK_TIME_UTC={snapshot.check_time_utc}")
    print(f"CANONICAL_GENERATION_TIME_UTC={snapshot.canonical_generation_time_utc}")
    print(f"CANONICAL_AGE_SECONDS={snapshot.canonical_age_seconds}")
    print(f"STALE_THRESHOLD_SECONDS={snapshot.stale_threshold_seconds}")
    print(f"FRESHNESS_VERDICT={snapshot.freshness_verdict}")


def emit_watchdog_error(exc: WatchdogError) -> None:
    print(f"WATCHDOG_REASON={exc.code}", file=sys.stderr)
    print(f"WATCHDOG_ERROR={exc}", file=sys.stderr)


class GitHubActionsClient:
    def __init__(self, repository: str, token: str, *, api_url: str = "https://api.github.com"):
        if "/" not in repository:
            raise WatchdogError("GITHUB_RUN_STATE_UNAVAILABLE", "GITHUB_REPOSITORY must be owner/name")
        if not token:
            raise WatchdogError("GITHUB_RUN_STATE_UNAVAILABLE", "GITHUB_TOKEN is unavailable")
        self.repository = repository
        self.token = token
        self.api_url = api_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Mapping[str, object] | None = None) -> tuple[int, object | None]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "eth-macro-data-bridge-internal-watchdog",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API HTTP {exc.code}: {body[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("GitHub API returned invalid JSON") from exc

    def active_update_runs(self) -> list[Mapping[str, object]]:
        workflow = urllib.parse.quote(UPDATE_WORKFLOW_FILE, safe="")
        active: list[Mapping[str, object]] = []
        try:
            for run_status in ACTIVE_UPDATE_STATUSES:
                query = urllib.parse.urlencode(
                    {"branch": DEFAULT_REF, "status": run_status, "per_page": 100}
                )
                status, payload = self._request(
                    "GET",
                    f"/repos/{self.repository}/actions/workflows/{workflow}/runs?{query}",
                )
                if status != 200 or not isinstance(payload, Mapping):
                    raise RuntimeError(f"unexpected workflow-runs response status={status}")
                runs = payload.get("workflow_runs")
                if not isinstance(runs, list):
                    raise RuntimeError("workflow-runs response has no workflow_runs array")
                for run in runs:
                    if isinstance(run, Mapping) and run.get("status") == run_status:
                        active.append(run)
        except RuntimeError as exc:
            raise WatchdogError("GITHUB_RUN_STATE_UNAVAILABLE", str(exc)) from exc
        return active

    def dispatch_workflow(self, workflow_file: str, *, ref: str = DEFAULT_REF) -> int | None:
        workflow = urllib.parse.quote(workflow_file, safe="")
        status, payload = self._request(
            "POST",
            f"/repos/{self.repository}/actions/workflows/{workflow}/dispatches",
            {"ref": ref},
        )
        if status not in {200, 201, 202, 204}:
            raise RuntimeError(f"unexpected workflow-dispatch response status={status}")
        if isinstance(payload, Mapping):
            run_id = payload.get("workflow_run_id")
            if isinstance(run_id, int) and run_id > 0:
                return run_id
        return None

    def _recent_watchdog_runs(self) -> list[Mapping[str, object]]:
        workflow = urllib.parse.quote(WATCHDOG_WORKFLOW_FILE, safe="")
        query = urllib.parse.urlencode({"branch": DEFAULT_REF, "event": "workflow_dispatch", "per_page": 20})
        status, payload = self._request(
            "GET",
            f"/repos/{self.repository}/actions/workflows/{workflow}/runs?{query}",
        )
        if status != 200 or not isinstance(payload, Mapping) or not isinstance(payload.get("workflow_runs"), list):
            raise RuntimeError(f"unexpected watchdog-runs response status={status}")
        return [run for run in payload["workflow_runs"] if isinstance(run, Mapping)]

    def dispatch_successor(
        self,
        current_run_id: int,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        proof_timeout_seconds: int = 60,
    ) -> int:
        print("SELF_DISPATCH_ATTEMPTED=YES")
        dispatch_started = datetime.now(timezone.utc)
        try:
            returned_id = self.dispatch_workflow(WATCHDOG_WORKFLOW_FILE)
            if returned_id is not None and returned_id != current_run_id:
                print("SUCCESSOR_RUN_CREATED=YES")
                print(f"SUCCESSOR_RUN_ID={returned_id}")
                return returned_id

            deadline = monotonic() + proof_timeout_seconds
            while monotonic() < deadline:
                for run in self._recent_watchdog_runs():
                    run_id = run.get("id")
                    created_at = run.get("created_at")
                    if not isinstance(run_id, int) or run_id == current_run_id or not isinstance(created_at, str):
                        continue
                    try:
                        created = _parse_utc(created_at)
                    except WatchdogError:
                        continue
                    if created >= dispatch_started.replace(microsecond=0):
                        print("SUCCESSOR_RUN_CREATED=YES")
                        print(f"SUCCESSOR_RUN_ID={run_id}")
                        return run_id
                sleep(3)
        except (RuntimeError, WatchdogError) as exc:
            raise WatchdogError("SELF_DISPATCH_FAILED", str(exc)) from exc
        raise WatchdogError("SELF_DISPATCH_FAILED", "successor workflow run could not be proven")


def perform_watchdog_check(
    snapshot: FreshnessSnapshot,
    client: GitHubActionsClient,
    state: WatchdogState,
    *,
    monotonic_now: float,
    recovery_cooldown_seconds: int = RECOVERY_DISPATCH_COOLDOWN_SECONDS,
) -> str:
    emit_freshness(snapshot)
    if snapshot.freshness_verdict == "FRESH":
        reason = "FRESH_NO_ACTION"
        print(f"WATCHDOG_REASON={reason}")
        return reason
    if snapshot.freshness_verdict != "STALE":
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", f"unknown freshness verdict: {snapshot.freshness_verdict}")

    last = state.last_recovery_dispatch_monotonic
    if last is not None and monotonic_now - last < recovery_cooldown_seconds:
        reason = "RECOVERY_COOLDOWN_ACTIVE"
        print(f"WATCHDOG_REASON={reason}")
        print(f"RECOVERY_COOLDOWN_REMAINING_SECONDS={max(0, int(recovery_cooldown_seconds - (monotonic_now - last)))}")
        return reason

    active = client.active_update_runs()
    if active:
        reason = "STALE_EXISTING_UPDATE_RUN"
        print(f"WATCHDOG_REASON={reason}")
        print("RECOVERY_DISPATCH=SKIPPED_EXISTING_RUN")
        print("EXISTING_UPDATE_RUN_IDS=" + ",".join(str(run.get("id")) for run in active))
        return reason

    # Arm the cooldown before the API call: a network failure after server-side
    # acceptance is ambiguous and must not cause a retry storm every 3 minutes.
    state.last_recovery_dispatch_monotonic = monotonic_now
    try:
        run_id = client.dispatch_workflow(UPDATE_WORKFLOW_FILE)
    except RuntimeError as exc:
        raise WatchdogError("RECOVERY_DISPATCH_FAILED", str(exc)) from exc
    reason = "STALE_RECOVERY_DISPATCHED"
    print(f"WATCHDOG_REASON={reason}")
    print("RECOVERY_DISPATCH=DISPATCHED")
    if run_id is not None:
        print(f"RECOVERY_RUN_ID={run_id}")
    return reason


def run_generation(
    repository: str,
    current_run_id: int,
    *,
    check_interval_seconds: int = CHECK_INTERVAL_SECONDS,
    stale_threshold_seconds: int = STALE_THRESHOLD_SECONDS,
    recovery_cooldown_seconds: int = RECOVERY_DISPATCH_COOLDOWN_SECONDS,
    generation_runtime_seconds: int = WATCHDOG_GENERATION_RUNTIME_SECONDS,
    token: str | None = None,
) -> int:
    if generation_runtime_seconds <= 0 or generation_runtime_seconds >= 6 * 60 * 60:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "watchdog runtime must be positive and below 6 hours")
    if check_interval_seconds <= 0 or recovery_cooldown_seconds < check_interval_seconds:
        raise WatchdogError("FRESHNESS_AUTHORITY_UNAVAILABLE", "watchdog timing configuration is invalid")

    client = GitHubActionsClient(repository, token or os.environ.get("GITHUB_TOKEN", ""))
    state = WatchdogState()
    started = time.monotonic()
    deadline = started + generation_runtime_seconds
    iteration_failures = 0

    print(f"TEMPORARY_FAILOVER={'true' if TEMPORARY_FAILOVER else 'false'}")
    print(f"TARGET_REPLACEMENT={TARGET_REPLACEMENT}")
    print(f"WATCHDOG_ROLE={WATCHDOG_ROLE}")
    print(f"WATCHDOG_IS_MARKET_DATA_AUTHORITY={str(WATCHDOG_IS_MARKET_DATA_AUTHORITY).lower()}")
    print(f"WATCHDOG_IS_STORAGE_AUTHORITY={str(WATCHDOG_IS_STORAGE_AUTHORITY).lower()}")
    print(f"WATCHDOG_IS_PROVIDER_AUTHORITY={str(WATCHDOG_IS_PROVIDER_AUTHORITY).lower()}")
    print(f"WATCHDOG_IS_FRESHNESS_AUTHORITY={str(WATCHDOG_IS_FRESHNESS_AUTHORITY).lower()}")
    print(f"CHECK_INTERVAL_SECONDS={check_interval_seconds}")
    print(f"STALE_THRESHOLD_SECONDS={stale_threshold_seconds}")
    print(f"RECOVERY_DISPATCH_COOLDOWN_SECONDS={recovery_cooldown_seconds}")
    print(f"WATCHDOG_GENERATION_RUNTIME_SECONDS={generation_runtime_seconds}")

    while True:
        now_mono = time.monotonic()
        if now_mono >= deadline:
            break
        try:
            snapshot = evaluate_canonical_durable_freshness(stale_threshold_seconds)
            perform_watchdog_check(
                snapshot,
                client,
                state,
                monotonic_now=now_mono,
                recovery_cooldown_seconds=recovery_cooldown_seconds,
            )
        except WatchdogError as exc:
            # Fail closed for this iteration: no alternate collector/provider path
            # is attempted. Preserve the bounded chain so a transient control-plane
            # failure does not permanently remove the only temporary watchdog.
            iteration_failures += 1
            emit_watchdog_error(exc)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(check_interval_seconds, remaining))

    successor_id = client.dispatch_successor(current_run_id)
    print(f"SUCCESSOR_RUN_ID={successor_id}")
    print("CURRENT_GENERATION_EXITS_AFTER_SUCCESSOR_ACCEPTED=YES")
    print(f"WATCHDOG_ITERATION_FAILURE_COUNT={iteration_failures}")
    if iteration_failures:
        print("WATCHDOG_REASON=WATCHDOG_COMPLETED_WITH_ERRORS_SUCCESSOR_CREATED")
        return 1
    print("WATCHDOG_REASON=WATCHDOG_COMPLETED_SUCCESSOR_CREATED")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Temporary internal durable market-data refresh watchdog")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run-generation")
    run.add_argument("--repository", required=True)
    run.add_argument("--current-run-id", required=True, type=int)
    run.add_argument("--check-interval-seconds", type=int, default=CHECK_INTERVAL_SECONDS)
    run.add_argument("--stale-threshold-seconds", type=int, default=STALE_THRESHOLD_SECONDS)
    run.add_argument("--recovery-dispatch-cooldown-seconds", type=int, default=RECOVERY_DISPATCH_COOLDOWN_SECONDS)
    run.add_argument("--generation-runtime-seconds", type=int, default=WATCHDOG_GENERATION_RUNTIME_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run-generation":
            return run_generation(
                args.repository,
                args.current_run_id,
                check_interval_seconds=args.check_interval_seconds,
                stale_threshold_seconds=args.stale_threshold_seconds,
                recovery_cooldown_seconds=args.recovery_dispatch_cooldown_seconds,
                generation_runtime_seconds=args.generation_runtime_seconds,
            )
    except WatchdogError as exc:
        emit_watchdog_error(exc)
        return 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
