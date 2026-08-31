"""Модели durable Work и bounded F5 identity по CONTRACT-SERVER-WORK-001."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json

from server._validation import require_aware, require_non_empty

F5_STAGE_ID = "F5"
F5_WORK_KIND = "F5_INCOMING_ARTIFACT_PUBLICATION"
F5_DIRECT_SLOT = "DIRECT"
F5_WORK_ID_PREFIX = "work:f5:v1:"
MAX_AUTOMATIC_ATTEMPTS_PER_WORK = 3


def _canonical_json(value: object) -> bytes:
    """F5 contract-bound function `_canonical_json`. EN summary: bounded F5 function."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True, slots=True)
class WorkId:
    """F5 contract-bound class `WorkId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "work_id"))


@dataclass(frozen=True, slots=True)
class WorkType:
    """F5 contract-bound class `WorkType`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "work_type"))


@dataclass(frozen=True, slots=True)
class AttemptId:
    """F5 contract-bound class `AttemptId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "attempt_id"))


@dataclass(frozen=True, slots=True)
class IdempotencyIdentity:
    """F5 contract-bound class `IdempotencyIdentity`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "idempotency_identity"))


@dataclass(frozen=True, slots=True)
class ProvenanceReference:
    """F5 contract-bound class `ProvenanceReference`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "provenance_reference"))


@dataclass(frozen=True, slots=True)
class TerminalResultReference:
    """F5 contract-bound class `TerminalResultReference`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "terminal_result_reference"))


class WorkState(StrEnum):
    """F5 contract-bound class `WorkState`. EN summary: bounded F5 class."""

    PENDING = "PENDING"
    READY = "READY"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_WORK_STATES = frozenset({WorkState.SUCCEEDED, WorkState.FAILED, WorkState.CANCELLED})


@dataclass(frozen=True, slots=True)
class WorkIdentityReferences:
    """F5 contract-bound class `WorkIdentityReferences`. EN summary: bounded F5 class."""

    idempotency: IdempotencyIdentity
    provenance: ProvenanceReference


@dataclass(frozen=True, slots=True)
class WorkExecutionStatus:
    """F5 contract-bound class `WorkExecutionStatus`. EN summary: bounded F5 class."""

    state: WorkState = WorkState.PENDING
    attempt_id: AttemptId | None = None
    owner_claim_reference: str | None = None
    terminal_result_reference: TerminalResultReference | None = None

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        if self.owner_claim_reference is not None:
            object.__setattr__(
                self,
                "owner_claim_reference",
                require_non_empty(self.owner_claim_reference, "owner_claim_reference"),
            )


@dataclass(frozen=True, slots=True)
class WorkRecord:
    """F5 contract-bound class `WorkRecord`. EN summary: bounded F5 class."""

    work_id: WorkId
    work_type: WorkType
    payload_reference: str
    created_at: datetime
    identities: WorkIdentityReferences
    execution: WorkExecutionStatus = WorkExecutionStatus()

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(
            self,
            "payload_reference",
            require_non_empty(self.payload_reference, "payload_reference"),
        )
        require_aware(self.created_at, "created_at")

    @property
    def idempotency_identity(self) -> IdempotencyIdentity:
        """F5 contract-bound function `idempotency_identity`. EN summary: bounded F5 function."""
        return self.identities.idempotency

    @property
    def provenance_reference(self) -> ProvenanceReference:
        """F5 contract-bound function `provenance_reference`. EN summary: bounded F5 function."""
        return self.identities.provenance

    @property
    def state(self) -> WorkState:
        """F5 contract-bound function `state`. EN summary: bounded F5 function."""
        return self.execution.state

    @property
    def attempt_id(self) -> AttemptId | None:
        """F5 contract-bound function `attempt_id`. EN summary: bounded F5 function."""
        return self.execution.attempt_id

    @property
    def owner_claim_reference(self) -> str | None:
        """F5 contract-bound function `owner_claim_reference`. EN summary: bounded F5 function."""
        return self.execution.owner_claim_reference

    @property
    def terminal_result_reference(self) -> TerminalResultReference | None:
        """F5 contract-bound function `terminal_result_reference`. EN summary: bounded F5 function."""
        return self.execution.terminal_result_reference


@dataclass(frozen=True, slots=True)
class WorkRetryIdentity:
    """F5 contract-bound class `WorkRetryIdentity`. EN summary: bounded F5 class."""

    work_id: WorkId
    idempotency_identity: IdempotencyIdentity
    next_attempt_id: AttemptId


@dataclass(frozen=True, slots=True)
class F5WorkIdentityInputs:
    """F5 contract-bound class `F5WorkIdentityInputs`. EN summary: bounded F5 class."""

    domain_artifact_identity: str
    source_revision: str
    content_identity: str
    policy_revision_identity: str
    scheduling_slot_identity: str = F5_DIRECT_SLOT
    stage_id: str = F5_STAGE_ID
    work_kind: str = F5_WORK_KIND

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        for field_name in (
            "domain_artifact_identity",
            "source_revision",
            "content_identity",
            "policy_revision_identity",
            "scheduling_slot_identity",
            "stage_id",
            "work_kind",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty(getattr(self, field_name), field_name),
            )
        if self.stage_id != F5_STAGE_ID:
            raise ValueError("F5 Work identity требует stage_id=F5")
        if self.work_kind != F5_WORK_KIND:
            raise ValueError("F5 Work identity требует canonical work kind")

    def canonical_mapping(self) -> dict[str, str]:
        """F5 contract-bound function `canonical_mapping`. EN summary: bounded F5 function."""
        return {
            "CONTENT_IDENTITY": self.content_identity,
            "DOMAIN_ARTIFACT_IDENTITY": self.domain_artifact_identity,
            "F5_STAGE_ID": self.stage_id,
            "POLICY_REVISION_IDENTITY": self.policy_revision_identity,
            "SCHEDULING_SLOT_IDENTITY_OR_DIRECT": self.scheduling_slot_identity,
            "SOURCE_REVISION": self.source_revision,
            "WORK_KIND": self.work_kind,
        }

    @property
    def logical_input_identity(self) -> str:
        """F5 contract-bound function `logical_input_identity`. EN summary: bounded F5 function."""
        return sha256(_canonical_json(self.canonical_mapping())).hexdigest()

    @property
    def work_id(self) -> WorkId:
        """F5 contract-bound function `work_id`. EN summary: bounded F5 function."""
        return WorkId(F5_WORK_ID_PREFIX + self.logical_input_identity)


def build_f5_work_id(inputs: F5WorkIdentityInputs) -> WorkId:
    """F5 contract-bound function `build_f5_work_id`. EN summary: bounded F5 function."""
    return inputs.work_id


class InvalidWorkTransition(ValueError):
    """F5 contract-bound class `InvalidWorkTransition`. EN summary: bounded F5 class."""


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
    """F5 contract-bound function `transition_work`. EN summary: bounded F5 function."""
    if target not in _ALLOWED_TRANSITIONS[record.state]:
        raise InvalidWorkTransition(f"переход {record.state} -> {target} запрещён")
    next_attempt = attempt_id if attempt_id is not None else record.attempt_id
    next_claim = claim_reference if claim_reference is not None else record.owner_claim_reference
    if target in {WorkState.CLAIMED, WorkState.RUNNING, WorkState.SUCCEEDED, WorkState.FAILED} and next_attempt is None:
        raise InvalidWorkTransition(f"состояние {target} требует attempt_id")
    if target in {WorkState.CLAIMED, WorkState.RUNNING, WorkState.SUCCEEDED, WorkState.FAILED} and next_claim is None:
        raise InvalidWorkTransition(f"состояние {target} требует owner_claim_reference")
    if target in {WorkState.SUCCEEDED, WorkState.FAILED} and terminal_result_reference is None:
        raise InvalidWorkTransition(f"состояние {target} требует terminal_result_reference")
    return replace(
        record,
        execution=WorkExecutionStatus(
            state=target,
            attempt_id=next_attempt,
            owner_claim_reference=next_claim,
            terminal_result_reference=terminal_result_reference or record.terminal_result_reference,
        ),
    )


def retry_identity(record: WorkRecord, next_attempt_id: AttemptId) -> WorkRetryIdentity:
    """F5 contract-bound function `retry_identity`. EN summary: bounded F5 function."""
    if record.attempt_id == next_attempt_id:
        raise ValueError("next_attempt_id должен отличаться от текущей попытки")
    return WorkRetryIdentity(record.work_id, record.idempotency_identity, next_attempt_id)


def retryable_attempt_failure(record: WorkRecord) -> WorkRecord:
    """Return the same logical Work to READY; terminal Work is never reopened."""
    if record.state in TERMINAL_WORK_STATES:
        raise InvalidWorkTransition("terminal Work cannot become retryable")
    return replace(record, execution=WorkExecutionStatus(state=WorkState.READY))
