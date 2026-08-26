"""Модели claim/lease/fencing по `CONTRACT-SERVER-EXECUTION-001`.

Модуль не создаёт распределённый lock backend; он только фиксирует проверяемую authority-модель.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from server._validation import require_aware, require_non_empty
from server.work import AttemptId, WorkId


@dataclass(frozen=True, slots=True)
class ClaimId:
    """Идентификатор claim. EN summary: claim identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "claim_id"))


@dataclass(frozen=True, slots=True)
class LeaseId:
    """Идентификатор lease. EN summary: lease identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "lease_id"))


@dataclass(frozen=True, order=True, slots=True)
class FencingToken:
    """Монотонный fencing token. EN summary: monotonic fencing authority token."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError("fencing token должен быть положительным")


@dataclass(frozen=True, slots=True)
class Claim:
    """Authority claim для одной попытки. EN summary: work execution claim."""

    work_id: WorkId
    claim_id: ClaimId
    attempt_id: AttemptId
    fencing_token: FencingToken


@dataclass(frozen=True, slots=True)
class Lease:
    """Ограниченное временем владение. EN summary: time-bounded execution lease."""

    claim: Claim
    lease_id: LeaseId
    expires_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.expires_at, "expires_at")

    def is_expired(self, at: datetime) -> bool:
        """Проверить истечение lease. EN summary: test whether the lease is expired."""
        return require_aware(at, "at") >= self.expires_at


@dataclass(frozen=True, slots=True)
class RenewalResult:
    """Результат renewal без скрытой мутации. EN summary: explicit lease renewal result."""

    accepted: bool
    lease: Lease
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReclaimResult:
    """Результат смены authority generation. EN summary: explicit lease reclaim result."""

    previous_lease_id: LeaseId
    replacement: Lease


class StaleFencingAuthorityError(RuntimeError):
    """Ошибка устаревшей authority. EN summary: stale fencing authority error."""


def validate_terminal_authority(lease: Lease, current_token: FencingToken, at: datetime) -> None:
    """Проверить право terminal commit. EN summary: require current non-expired fencing authority."""
    now = require_aware(at, "at")
    if lease.is_expired(now):
        raise StaleFencingAuthorityError("lease истёк и не разрешает terminal effect")
    if lease.claim.fencing_token != current_token:
        raise StaleFencingAuthorityError("fencing token больше не является текущей authority")


def renew_lease(
    lease: Lease,
    *,
    current_token: FencingToken,
    now: datetime,
    new_expiry: datetime,
) -> RenewalResult:
    """Обновить lease только при текущей authority. EN summary: renew only current lease authority."""
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
    """Сменить authority после expiry. EN summary: reclaim an expired lease with a newer fence."""
    moment = require_aware(at, "at")
    if not expired.is_expired(moment):
        raise ValueError("reclaim разрешён только после expiry")
    if expired.claim.work_id != replacement.claim.work_id:
        raise ValueError("replacement должен относиться к тому же WORK_ID")
    if replacement.claim.fencing_token <= expired.claim.fencing_token:
        raise ValueError("replacement fencing token должен быть монотонно больше")
    if replacement.expires_at <= moment:
        raise ValueError("replacement lease должен быть действующим")
    return ReclaimResult(expired.lease_id, replacement)
