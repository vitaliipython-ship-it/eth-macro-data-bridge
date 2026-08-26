"""Проверки EXECUTION-контракта F3."""

from datetime import datetime, timedelta, timezone

import pytest

from server.execution import (
    Claim,
    ClaimId,
    FencingToken,
    Lease,
    LeaseId,
    StaleFencingAuthorityError,
    reclaim_lease,
    renew_lease,
    validate_terminal_authority,
)
from server.work import AttemptId, WorkId

NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def _lease(token: int = 1, *, expires_delta: timedelta = timedelta(minutes=5), suffix: str = "1") -> Lease:
    return Lease(
        claim=Claim(
            work_id=WorkId("work-1"),
            claim_id=ClaimId(f"claim-{suffix}"),
            attempt_id=AttemptId(f"attempt-{suffix}"),
            fencing_token=FencingToken(token),
        ),
        lease_id=LeaseId(f"lease-{suffix}"),
        expires_at=NOW + expires_delta,
    )


def test_current_fence_can_authorize_terminal_effect() -> None:
    """Проверить разрешение terminal effect текущим fence."""
    lease = _lease()
    validate_terminal_authority(lease, FencingToken(1), NOW)


def test_stale_or_expired_fence_is_rejected() -> None:
    """Проверить отклонение устаревшего или истёкшего fence."""
    lease = _lease()
    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(lease, FencingToken(2), NOW)
    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(lease, FencingToken(1), NOW + timedelta(minutes=6))


def test_reclaim_changes_authority_generation() -> None:
    """Проверить смену поколения authority при reclaim."""
    expired = _lease(expires_delta=timedelta(minutes=-1))
    replacement = _lease(token=2, suffix="2")
    result = reclaim_lease(expired, replacement, at=NOW)
    assert result.replacement.claim.fencing_token > expired.claim.fencing_token
    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(expired, FencingToken(1), NOW)
    validate_terminal_authority(result.replacement, FencingToken(2), NOW)


def test_renewal_rejects_lost_fence() -> None:
    """Проверить отклонение renewal после потери fence."""
    result = renew_lease(
        _lease(),
        current_token=FencingToken(2),
        now=NOW,
        new_expiry=NOW + timedelta(minutes=10),
    )
    assert result.accepted is False
    assert result.reason == "fence_lost"
