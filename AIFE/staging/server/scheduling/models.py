"""Чистые модели планирования по `CONTRACT-SERVER-SCHEDULING-001`.

Вычисление наступившей работы отделено от создания логической работы и от её исполнения.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from server._validation import require_aware, require_non_empty, stable_identity
from server.work import AttemptId, WorkId


@dataclass(frozen=True, slots=True)
class ScheduleId:
    """Идентификатор определения расписания. EN summary: schedule definition identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "schedule_id"))


@dataclass(frozen=True, slots=True)
class PolicyRevision:
    """Ревизия политики расписания. EN summary: schedule policy revision."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "policy_revision"))


class ScheduleKind(StrEnum):
    """Общий класс расписания. EN summary: generic schedule kind."""

    ONE_SHOT = "ONE_SHOT"
    RECURRING = "RECURRING"
    CONDITION = "CONDITION"
    RETRY = "RETRY"


@dataclass(frozen=True, slots=True)
class ScheduleDefinition:
    """Определение расписания без движка cron. EN summary: backend-neutral schedule definition."""

    schedule_id: ScheduleId
    policy_revision: PolicyRevision
    kind: ScheduleKind
    timezone_name: str

    def __post_init__(self) -> None:
        name = require_non_empty(self.timezone_name, "timezone_name")
        try:
            ZoneInfo(name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"неизвестная timezone: {name}") from exc
        object.__setattr__(self, "timezone_name", name)


@dataclass(frozen=True, slots=True)
class DueIdentity:
    """Детерминированная идентичность наступившего слота. EN summary: deterministic due identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "due_identity"))


@dataclass(frozen=True, slots=True)
class DueMaterialization:
    """Связь due-слота с логической работой. EN summary: due-to-work materialization boundary."""

    due_identity: DueIdentity
    work_id: WorkId
    due_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.due_at, "due_at")


@dataclass(frozen=True, slots=True)
class RetryBackoffDecision:
    """Решение о времени повтора. EN summary: retry eligibility decision without new work identity."""

    work_id: WorkId
    next_attempt_id: AttemptId
    eligible_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.eligible_at, "eligible_at")


def build_due_identity(definition: ScheduleDefinition, due_at: datetime) -> DueIdentity:
    """Построить стабильный due-id. EN summary: build a deterministic timezone-aware due identity."""
    aware = require_aware(due_at, "due_at")
    canonical = aware.astimezone(ZoneInfo(definition.timezone_name))
    digest = stable_identity(
        definition.schedule_id.value,
        definition.policy_revision.value,
        definition.kind.value,
        definition.timezone_name,
        canonical.isoformat(timespec="microseconds"),
    )
    return DueIdentity(digest)


def materialize_due(due_identity: DueIdentity, work_id: WorkId, due_at: datetime) -> DueMaterialization:
    """Связать due с уже выбранным `WORK_ID`. EN summary: materialize a due-to-work reference only."""
    return DueMaterialization(due_identity=due_identity, work_id=work_id, due_at=require_aware(due_at, "due_at"))
