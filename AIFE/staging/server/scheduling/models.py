"""Scheduling models plus deterministic F5 slot identity."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from server._validation import require_aware, require_non_empty, stable_identity
from server.work.models import AttemptId, WorkId

F5_SLOT_PREFIX = "slot:f5:v1:"


def _canon(v: object) -> bytes:
    """F5 contract-bound function `_canon`. EN summary: bounded F5 function."""
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True, slots=True)
class ScheduleId:
    """F5 contract-bound class `ScheduleId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "schedule_id"))


@dataclass(frozen=True, slots=True)
class PolicyRevision:
    """F5 contract-bound class `PolicyRevision`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "policy_revision"))


class ScheduleKind(StrEnum):
    """F5 contract-bound class `ScheduleKind`. EN summary: bounded F5 class."""

    ONE_SHOT = "ONE_SHOT"
    RECURRING = "RECURRING"
    CONDITION = "CONDITION"
    RETRY = "RETRY"


@dataclass(frozen=True, slots=True)
class ScheduleDefinition:
    """F5 contract-bound class `ScheduleDefinition`. EN summary: bounded F5 class."""

    schedule_id: ScheduleId
    policy_revision: PolicyRevision
    kind: ScheduleKind
    timezone_name: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        name = require_non_empty(self.timezone_name, "timezone_name")
        try:
            ZoneInfo(name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"неизвестная timezone: {name}") from exc
        object.__setattr__(self, "timezone_name", name)


@dataclass(frozen=True, slots=True)
class DueIdentity:
    """F5 contract-bound class `DueIdentity`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "due_identity"))


@dataclass(frozen=True, slots=True)
class DueMaterialization:
    """F5 contract-bound class `DueMaterialization`. EN summary: bounded F5 class."""

    due_identity: DueIdentity
    work_id: WorkId
    due_at: datetime

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        require_aware(self.due_at, "due_at")


@dataclass(frozen=True, slots=True)
class RetryBackoffDecision:
    """F5 contract-bound class `RetryBackoffDecision`. EN summary: bounded F5 class."""

    work_id: WorkId
    next_attempt_id: AttemptId
    eligible_at: datetime

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        require_aware(self.eligible_at, "eligible_at")


def build_due_identity(definition: ScheduleDefinition, due_at: datetime) -> DueIdentity:
    """F5 contract-bound function `build_due_identity`. EN summary: bounded F5 function."""
    aware = require_aware(due_at, "due_at")
    canonical = aware.astimezone(ZoneInfo(definition.timezone_name))
    return DueIdentity(
        stable_identity(
            definition.schedule_id.value,
            definition.policy_revision.value,
            definition.kind.value,
            definition.timezone_name,
            canonical.isoformat(timespec="microseconds"),
        )
    )


def materialize_due(due_identity: DueIdentity, work_id: WorkId, due_at: datetime) -> DueMaterialization:
    """F5 contract-bound function `materialize_due`. EN summary: bounded F5 function."""
    return DueMaterialization(due_identity, work_id, require_aware(due_at, "due_at"))


def build_f5_slot_identity(
    *,
    schedule_definition_identity: str,
    nominal_due_at: datetime,
    timezone_identity: str,
    policy_revision_identity: str,
) -> str:
    """F5 contract-bound function `build_f5_slot_identity`. EN summary: bounded F5 function."""
    due = require_aware(nominal_due_at, "nominal_due_at").astimezone(timezone.utc).isoformat()
    mapping = {
        "NOMINAL_DUE_AT_UTC": due,
        "POLICY_REVISION_IDENTITY": require_non_empty(policy_revision_identity, "policy_revision_identity"),
        "SCHEDULE_DEFINITION_IDENTITY": require_non_empty(schedule_definition_identity, "schedule_definition_identity"),
        "TIMEZONE_IDENTITY": require_non_empty(timezone_identity, "timezone_identity"),
    }
    return F5_SLOT_PREFIX + sha256(_canon(mapping)).hexdigest()
