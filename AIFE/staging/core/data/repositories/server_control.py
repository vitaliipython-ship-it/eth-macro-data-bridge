"""Narrow control-state repository abstraction for the F5 bounded slice.

[Purpose]
    Определить typed durable-control contract F5/C-144 независимо от SQLite adapter.
[Description]
    Protocol и DTO фиксируют Work/Attempt/Publication/Generation authority transitions.
[Components]
    - ServerControlRepository, StoredWork, StoredAttempt, StoredPublication и StoredGeneration.
[Usage]
    Реализации должны соблюдать fail-closed identity, lease, fencing и publication invariants.
[Architecture]
    Generic AIFE Server control boundary; physical adapter реализуется отдельно в core/data/adapters.
[Note]
    Контракт не владеет market-data/provider semantics и не создаёт второй repository framework.
[Warning]
    Не расширять protocol domain-specific identities или backend-specific semantic authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from server.work.models import F5WorkIdentityInputs


class ControlStateConflict(RuntimeError):
    """Persisted identity/state disagrees with the requested durable effect."""


class WorkIdentityConflict(ControlStateConflict):
    """Bounded F5 class `WorkIdentityConflict` preserving the frozen contract."""


class WorkNotClaimable(ControlStateConflict):
    """Bounded F5 class `WorkNotClaimable` preserving the frozen contract."""


class StaleControlAuthority(ControlStateConflict):
    """Bounded F5 class `StaleControlAuthority` preserving the frozen contract."""


@dataclass(frozen=True, slots=True)
class StoredWork:  # pylint: disable=too-many-instance-attributes
    """Bounded F5 class `StoredWork` preserving the frozen contract."""

    work_id: str
    work_kind: str
    logical_input_identity: str
    scheduling_slot_identity: str | None
    payload_reference: str
    provenance_reference: str
    policy_revision_identity: str
    immutable_input_digest: str
    created_at: datetime
    updated_at: datetime
    state: str
    terminal_state: str | None
    failure_state: str | None
    terminal_at: datetime | None
    record_version: int


@dataclass(frozen=True, slots=True)
class StoredAttempt:  # pylint: disable=too-many-instance-attributes
    """Bounded F5 class `StoredAttempt` preserving the frozen contract."""

    attempt_id: str
    work_id: str
    attempt_no: int
    claim_id: str
    claim_owner: str
    lease_id: str
    lease_acquired_at: datetime
    lease_expires_at: datetime
    fencing_token: int
    state: str
    started_at: datetime | None
    terminated_at: datetime | None
    terminal_reason: str | None


class ServerControlRepository(Protocol):
    """Only the transactional control operations needed by F5."""

    def accept_work(
        self,
        inputs: F5WorkIdentityInputs,
        *,
        payload_reference: str,
        provenance_reference: str,
        created_at: datetime,
    ) -> StoredWork:
        """Protocol operation `accept_work` for the frozen F5 boundary."""
        raise NotImplementedError

    def get_work(self, work_id: str) -> StoredWork | None:
        """Protocol operation `get_work` for the frozen F5 boundary."""
        raise NotImplementedError

    def mark_work_ready(self, work_id: str, *, at: datetime) -> StoredWork:
        """Protocol operation `mark_work_ready` for the frozen F5 boundary."""
        raise NotImplementedError

    def claim_work(
        self,
        work_id: str,
        *,
        claim_owner: str,
        now: datetime,
        lease_duration_seconds: int = 60,
    ) -> StoredAttempt:
        """Protocol operation `claim_work` for the frozen F5 boundary."""
        raise NotImplementedError

    def get_attempt(self, attempt_id: str) -> StoredAttempt | None:
        """Protocol operation `get_attempt` for the frozen F5 boundary."""
        raise NotImplementedError

    def renew_attempt_lease(
        self,
        attempt_id: str,
        *,
        fencing_token: int,
        now: datetime,
        new_expiry: datetime,
    ) -> StoredAttempt:
        """Protocol operation `renew_attempt_lease` for the frozen F5 boundary."""
        raise NotImplementedError

    def reclaim_work(
        self,
        work_id: str,
        *,
        claim_owner: str,
        now: datetime,
        lease_duration_seconds: int = 60,
    ) -> StoredAttempt:
        """Protocol operation `reclaim_work` for the frozen F5 boundary."""
        raise NotImplementedError

    def mark_attempt_running(self, attempt_id: str, *, fencing_token: int, at: datetime) -> StoredAttempt:
        """Protocol operation `mark_attempt_running` for the frozen F5 boundary."""
        raise NotImplementedError

    def terminal_attempt(  # pylint: disable=too-many-arguments
        self,
        attempt_id: str,
        *,
        fencing_token: int,
        at: datetime,
        success: bool,
        retryable: bool = False,
        reason: str | None = None,
    ) -> StoredWork:
        """Protocol operation `terminal_attempt` for the frozen F5 boundary."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StoredPublication:  # pylint: disable=too-many-instance-attributes
    """Bounded F5 class `StoredPublication` preserving the frozen contract."""

    publication_id: str
    work_id: str
    attempt_id: str
    domain_artifact_identity: str
    source_revision: str
    content_checksum: str
    content_size: int
    logical_target_identity: str
    state: str
    physical_locator: str | None
    durable_write_evidence: str | None
    readback_evidence: str | None
    registration_evidence: str | None
    ack_evidence: str | None
    registration_fencing_token: int | None


@dataclass(frozen=True, slots=True)
class StoredGeneration:  # pylint: disable=too-many-instance-attributes
    """Bounded F5 class `StoredGeneration` preserving the frozen contract."""

    generation_scope_identity: str
    generation_identity: str
    generation_no: int
    publication_id: str
    source_revision: str
    content_checksum: str
    content_size: int
    physical_locator: str
    registration_fencing_token: int


@dataclass(frozen=True, slots=True)
class ControlBackupEvidence:
    """Bounded F5 class `ControlBackupEvidence` preserving the frozen contract."""

    backup_path: str
    sha256: str
    size: int
    schema_id: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class ControlRestoreEvidence:
    """Bounded F5 class `ControlRestoreEvidence` preserving the frozen contract."""

    restore_path: str
    source_backup_sha256: str
    source_backup_size: int
    integrity_check: str
    schema_id: str
    schema_version: int
    generation_count: int
