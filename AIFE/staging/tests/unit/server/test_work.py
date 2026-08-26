"""Проверки WORK-контракта F3."""

from datetime import datetime, timezone

import pytest

from server.work import (
    AttemptId,
    IdempotencyIdentity,
    InvalidWorkTransition,
    ProvenanceReference,
    TerminalResultReference,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkState,
    WorkType,
    retry_identity,
    transition_work,
)


def _work() -> WorkRecord:
    return WorkRecord(
        work_id=WorkId("work-1"),
        work_type=WorkType("collect"),
        payload_reference="payload:1",
        created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        identities=WorkIdentityReferences(IdempotencyIdentity("idem-1"), ProvenanceReference("source:1")),
    )


def test_valid_work_lifecycle() -> None:
    """Проверить допустимый жизненный цикл работы."""
    record = transition_work(_work(), WorkState.READY)
    record = transition_work(
        record,
        WorkState.CLAIMED,
        attempt_id=AttemptId("attempt-1"),
        claim_reference="claim-1",
    )
    record = transition_work(record, WorkState.RUNNING)
    record = transition_work(
        record,
        WorkState.SUCCEEDED,
        terminal_result_reference=TerminalResultReference("result-1"),
    )
    assert record.state is WorkState.SUCCEEDED


def test_invalid_transition_is_rejected() -> None:
    """Проверить отклонение недопустимого перехода работы."""
    with pytest.raises(InvalidWorkTransition):
        transition_work(_work(), WorkState.RUNNING)


def test_retry_retains_logical_identity() -> None:
    """Проверить сохранение логической идентичности при повторе."""
    claimed = transition_work(
        transition_work(_work(), WorkState.READY),
        WorkState.CLAIMED,
        attempt_id=AttemptId("attempt-1"),
        claim_reference="claim-1",
    )
    plan = retry_identity(claimed, AttemptId("attempt-2"))
    assert plan.work_id == claimed.work_id
    assert plan.idempotency_identity == claimed.idempotency_identity
    assert plan.next_attempt_id != claimed.attempt_id
