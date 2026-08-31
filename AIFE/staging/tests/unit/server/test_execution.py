"""Bounded F5 implementation acceptance tests for this mapped owner path."""

from datetime import datetime, timedelta, timezone

import pytest

from server.execution.models import (
    Claim,
    ClaimId,
    FencingToken,
    Lease,
    LeaseId,
    StaleFencingAuthorityError,
    build_f5_attempt_id,
    build_f5_claim_id,
    build_f5_lease_id,
    renew_lease,
    validate_terminal_authority,
)
from server.work.models import WorkId


def _lease(fence=1, seconds=60):
    """Exercise the mapped F5 acceptance case."""
    now = datetime.now(timezone.utc)
    aid = build_f5_attempt_id("w", fence)
    claim = Claim(WorkId("w"), ClaimId(build_f5_claim_id(aid)), aid, FencingToken(fence))
    return now, Lease(claim, LeaseId(build_f5_lease_id(aid)), now + timedelta(seconds=seconds))


def test_attempt_identity_and_renewal():
    """Exercise the mapped F5 acceptance case."""
    assert build_f5_attempt_id("w", 1) == build_f5_attempt_id("w", 1)
    now, lease = _lease()
    assert renew_lease(
        lease,
        current_token=FencingToken(1),
        now=now,
        new_expiry=lease.expires_at + timedelta(seconds=1),
    ).accepted
    assert not renew_lease(
        lease,
        current_token=FencingToken(2),
        now=now,
        new_expiry=lease.expires_at + timedelta(seconds=1),
    ).accepted


def test_expired_lease_cannot_renew_or_terminalize():
    """Exercise the mapped F5 acceptance case."""
    now, lease = _lease(seconds=1)
    later = now + timedelta(seconds=2)
    assert not renew_lease(
        lease,
        current_token=FencingToken(1),
        now=later,
        new_expiry=later + timedelta(seconds=10),
    ).accepted
    with pytest.raises(StaleFencingAuthorityError):
        validate_terminal_authority(lease, FencingToken(1), later)
