"""
Claim/lease/fencing models and exact F5 attempt identities.

[Purpose]
    Определить claim/lease/fencing execution models F5.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Attempt authority, lease/fence value objects и validation rules.

[Usage]
    Использовать через typed bounded F5 interfaces и owner-mapped application/runtime composition.

[Architecture]
    Модуль принадлежит generic AIFE Server execution/storage contour; Data Bridge сохраняет
    market-data semantic authority.

[Note]
    Реализация рассчитана на one-server SQLite/WAL + immutable filesystem profile и fail-closed invariants.

[Warning]
    Не переносить domain/provider semantics в Work IDs, SQLite keys, filesystem locators или execution state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256

from server._validation import require_aware, require_non_empty
from server.work.models import AttemptId, WorkId

LEASE_DEFAULT_DURATION_SECONDS = 60
LEASE_RENEWAL_TARGET_SECONDS_BEFORE_EXPIRY = 20


def _digest(v: object) -> str:
    """F5 contract-bound function `_digest`. EN summary: bounded F5 function."""
    return sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_f5_attempt_id(work_id: str, attempt_no: int) -> AttemptId:
    """F5 contract-bound function `build_f5_attempt_id`. EN summary: bounded F5 function."""
    if attempt_no < 1:
        raise ValueError("attempt_no must start at 1")
    return AttemptId(
        "attempt:f5:v1:" + _digest({"ATTEMPT_NO": attempt_no, "WORK_ID": require_non_empty(work_id, "work_id")})
    )


def build_f5_claim_id(attempt_id: AttemptId) -> str:
    """F5 contract-bound function `build_f5_claim_id`. EN summary: bounded F5 function."""
    return "claim:f5:v1:" + attempt_id.value


def build_f5_lease_id(attempt_id: AttemptId) -> str:
    """F5 contract-bound function `build_f5_lease_id`. EN summary: bounded F5 function."""
    return "lease:f5:v1:" + attempt_id.value


@dataclass(frozen=True, slots=True)
class ClaimId:
    """F5 contract-bound class `ClaimId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "claim_id"))


@dataclass(frozen=True, slots=True)
class LeaseId:
    """F5 contract-bound class `LeaseId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "lease_id"))


@dataclass(frozen=True, order=True, slots=True)
class FencingToken:
    """F5 contract-bound class `FencingToken`. EN summary: bounded F5 class."""

    value: int

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        if self.value < 1:
            raise ValueError("fencing token должен быть положительным")


@dataclass(frozen=True, slots=True)
class Claim:
    """F5 contract-bound class `Claim`. EN summary: bounded F5 class."""

    work_id: WorkId
    claim_id: ClaimId
    attempt_id: AttemptId
    fencing_token: FencingToken


@dataclass(frozen=True, slots=True)
class Lease:
    """F5 contract-bound class `Lease`. EN summary: bounded F5 class."""

    claim: Claim
    lease_id: LeaseId
    expires_at: datetime

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        require_aware(self.expires_at, "expires_at")

    def is_expired(self, at: datetime) -> bool:
        """F5 contract-bound function `is_expired`. EN summary: bounded F5 function."""
        return require_aware(at, "at") >= self.expires_at


@dataclass(frozen=True, slots=True)
class RenewalResult:
    """F5 contract-bound class `RenewalResult`. EN summary: bounded F5 class."""

    accepted: bool
    lease: Lease
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReclaimResult:
    """F5 contract-bound class `ReclaimResult`. EN summary: bounded F5 class."""

    previous_lease_id: LeaseId
    replacement: Lease


class StaleFencingAuthorityError(RuntimeError):
    """F5 contract-bound class `StaleFencingAuthorityError`. EN summary: bounded F5 class."""


def validate_terminal_authority(lease: Lease, current_token: FencingToken, at: datetime) -> None:
    """F5 contract-bound function `validate_terminal_authority`. EN summary: bounded F5 function."""
    now = require_aware(at, "at")
    if lease.is_expired(now):
        raise StaleFencingAuthorityError("lease истёк и не разрешает terminal effect")
    if lease.claim.fencing_token != current_token:
        raise StaleFencingAuthorityError("fencing token больше не является текущей authority")


def renew_lease(lease: Lease, *, current_token: FencingToken, now: datetime, new_expiry: datetime) -> RenewalResult:
    """F5 contract-bound function `renew_lease`. EN summary: bounded F5 function."""
    moment = require_aware(now, "now")
    expiry = require_aware(new_expiry, "new_expiry")
    if lease.is_expired(moment):
        return RenewalResult(False, lease, "lease_expired")
    if lease.claim.fencing_token != current_token:
        return RenewalResult(False, lease, "fence_lost")
    if expiry <= moment or expiry <= lease.expires_at:
        return RenewalResult(False, lease, "expiry_not_extended")
    return RenewalResult(True, replace(lease, expires_at=expiry))


def reclaim_lease(expired: Lease, replacement: Lease, *, at: datetime) -> ReclaimResult:
    """F5 contract-bound function `reclaim_lease`. EN summary: bounded F5 function."""
    moment = require_aware(at, "at")
    if not expired.is_expired(moment):
        raise ValueError("reclaim разрешён только после expiry")
    if expired.claim.work_id != replacement.claim.work_id:
        raise ValueError("replacement same WORK_ID required")
    if replacement.claim.fencing_token <= expired.claim.fencing_token:
        raise ValueError("newer fence required")
    if replacement.expires_at <= moment:
        raise ValueError("replacement lease must be active")
    return ReclaimResult(expired.lease_id, replacement)
