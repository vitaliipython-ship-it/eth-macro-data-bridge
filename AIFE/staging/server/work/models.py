"""Модели логической работы по `CONTRACT-SERVER-WORK-001`.

Модуль фиксирует стабильную идентичность работы и допустимые переходы состояния,
не выбирая persistence backend и не интерпретируя доменный payload.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from server._validation import require_aware, require_non_empty


@dataclass(frozen=True, slots=True)
class WorkId:
    """Идентификатор логической работы. EN summary: stable logical work identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "work_id"))


@dataclass(frozen=True, slots=True)
class WorkType:
    """Общий тип работы. EN summary: generic work type identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "work_type"))


@dataclass(frozen=True, slots=True)
class AttemptId:
    """Идентификатор попытки исполнения. EN summary: execution attempt identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "attempt_id"))


@dataclass(frozen=True, slots=True)
class IdempotencyIdentity:
    """Идентичность дедупликации. EN summary: idempotency identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "idempotency_identity"))


@dataclass(frozen=True, slots=True)
class ProvenanceReference:
    """Ссылка на происхождение работы. EN summary: work provenance reference."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "provenance_reference"))


@dataclass(frozen=True, slots=True)
class TerminalResultReference:
    """Ссылка на конечный результат. EN summary: terminal result reference."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "terminal_result_reference"))


class WorkState(StrEnum):
    """Состояние логической работы. EN summary: logical work lifecycle state."""

    PENDING = "PENDING"
    READY = "READY"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class WorkIdentityReferences:
    """Стабильные ссылки работы. EN summary: stable work identity references."""

    idempotency: IdempotencyIdentity
    provenance: ProvenanceReference


@dataclass(frozen=True, slots=True)
class WorkExecutionStatus:
    """Изменяемая логикой часть записи. EN summary: work execution status value."""

    state: WorkState = WorkState.PENDING
    attempt_id: AttemptId | None = None
    owner_claim_reference: str | None = None
    terminal_result_reference: TerminalResultReference | None = None

    def __post_init__(self) -> None:
        if self.owner_claim_reference is not None:
            object.__setattr__(
                self,
                "owner_claim_reference",
                require_non_empty(self.owner_claim_reference, "owner_claim_reference"),
            )


@dataclass(frozen=True, slots=True)
class WorkRecord:
    """Неизменяемая запись работы. EN summary: immutable logical work record."""

    work_id: WorkId
    work_type: WorkType
    payload_reference: str
    created_at: datetime
    identities: WorkIdentityReferences
    execution: WorkExecutionStatus = WorkExecutionStatus()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "payload_reference",
            require_non_empty(self.payload_reference, "payload_reference"),
        )
        require_aware(self.created_at, "created_at")

    @property
    def idempotency_identity(self) -> IdempotencyIdentity:
        """Вернуть idempotency identity. EN summary: expose idempotency identity."""
        return self.identities.idempotency

    @property
    def provenance_reference(self) -> ProvenanceReference:
        """Вернуть provenance reference. EN summary: expose provenance reference."""
        return self.identities.provenance

    @property
    def state(self) -> WorkState:
        """Вернуть состояние. EN summary: expose work state."""
        return self.execution.state

    @property
    def attempt_id(self) -> AttemptId | None:
        """Вернуть attempt identity. EN summary: expose execution attempt."""
        return self.execution.attempt_id

    @property
    def owner_claim_reference(self) -> str | None:
        """Вернуть claim reference. EN summary: expose claim reference."""
        return self.execution.owner_claim_reference

    @property
    def terminal_result_reference(self) -> TerminalResultReference | None:
        """Вернуть terminal result. EN summary: expose terminal result reference."""
        return self.execution.terminal_result_reference


@dataclass(frozen=True, slots=True)
class WorkRetryIdentity:
    """Связь повтора с исходной работой. EN summary: retry identity preserving logical work."""

    work_id: WorkId
    idempotency_identity: IdempotencyIdentity
    next_attempt_id: AttemptId


class InvalidWorkTransition(ValueError):
    """Ошибка недопустимого перехода. EN summary: invalid work transition error."""


_ALLOWED_TRANSITIONS: dict[WorkState, frozenset[WorkState]] = {
    WorkState.PENDING: frozenset({WorkState.READY, WorkState.CANCELLED}),
    WorkState.READY: frozenset({WorkState.CLAIMED, WorkState.CANCELLED}),
    WorkState.CLAIMED: frozenset({WorkState.RUNNING, WorkState.CANCELLED}),
    WorkState.RUNNING: frozenset({WorkState.SUCCEEDED, WorkState.FAILED, WorkState.CANCELLED}),
    WorkState.SUCCEEDED: frozenset(),
    WorkState.FAILED: frozenset(),
    WorkState.CANCELLED: frozenset(),
}


def transition_work(
    record: WorkRecord,
    target: WorkState,
    *,
    attempt_id: AttemptId | None = None,
    claim_reference: str | None = None,
    terminal_result_reference: TerminalResultReference | None = None,
) -> WorkRecord:
    """Проверить и применить переход. EN summary: validate and apply a work transition."""
    if target not in _ALLOWED_TRANSITIONS[record.state]:
        raise InvalidWorkTransition(f"переход {record.state} -> {target} запрещён")

    next_attempt = attempt_id if attempt_id is not None else record.attempt_id
    next_claim = claim_reference if claim_reference is not None else record.owner_claim_reference
    if target in {WorkState.CLAIMED, WorkState.RUNNING, WorkState.SUCCEEDED, WorkState.FAILED}:
        if next_attempt is None:
            raise InvalidWorkTransition(f"состояние {target} требует attempt_id")
    if target in {WorkState.CLAIMED, WorkState.RUNNING, WorkState.SUCCEEDED, WorkState.FAILED}:
        if next_claim is None:
            raise InvalidWorkTransition(f"состояние {target} требует owner_claim_reference")
    if target in {WorkState.SUCCEEDED, WorkState.FAILED} and terminal_result_reference is None:
        raise InvalidWorkTransition(f"состояние {target} требует terminal_result_reference")

    return replace(
        record,
        execution=WorkExecutionStatus(
            state=target,
            attempt_id=next_attempt,
            owner_claim_reference=next_claim,
            terminal_result_reference=(terminal_result_reference or record.terminal_result_reference),
        ),
    )


def retry_identity(record: WorkRecord, next_attempt_id: AttemptId) -> WorkRetryIdentity:
    """Сохранить `WORK_ID` при повторе. EN summary: preserve work identity for a retry."""
    if record.attempt_id == next_attempt_id:
        raise ValueError("next_attempt_id должен отличаться от текущей попытки")
    return WorkRetryIdentity(record.work_id, record.idempotency_identity, next_attempt_id)
