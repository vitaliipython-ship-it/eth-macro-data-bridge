"""Проверки SCHEDULING-контракта F3."""

from datetime import datetime, timezone

import pytest

from server.scheduling import (
    PolicyRevision,
    RetryBackoffDecision,
    ScheduleDefinition,
    ScheduleId,
    ScheduleKind,
    build_due_identity,
    materialize_due,
)
from server.work import AttemptId, WorkId


def _schedule() -> ScheduleDefinition:
    return ScheduleDefinition(
        schedule_id=ScheduleId("schedule-1"),
        policy_revision=PolicyRevision("policy-r1"),
        kind=ScheduleKind.RECURRING,
        timezone_name="Europe/Kyiv",
    )


def test_due_identity_is_deterministic_and_timezone_aware() -> None:
    """Проверить deterministic timezone-aware due identity."""
    due_utc = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    first = build_due_identity(_schedule(), due_utc)
    second = build_due_identity(_schedule(), due_utc)
    assert first == second
    with pytest.raises(ValueError):
        build_due_identity(_schedule(), datetime(2026, 8, 26, 12, 0))


def test_due_computation_is_separate_from_work_materialization() -> None:
    """Проверить разделение due computation и materialization."""
    due_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    due = build_due_identity(_schedule(), due_at)
    work_id = WorkId("work-1")
    materialization = materialize_due(due, work_id, due_at)
    assert materialization.due_identity == due
    assert materialization.work_id == work_id


def test_retry_backoff_keeps_logical_work_identity() -> None:
    """Проверить сохранение WorkId в retry/backoff boundary."""
    decision = RetryBackoffDecision(
        work_id=WorkId("work-1"),
        next_attempt_id=AttemptId("attempt-2"),
        eligible_at=datetime(2026, 8, 26, 12, 5, tzinfo=timezone.utc),
    )
    assert decision.work_id == WorkId("work-1")
