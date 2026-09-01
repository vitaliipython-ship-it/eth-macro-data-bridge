"""Bounded F5 implementation acceptance tests for this mapped owner path.

[Purpose]
    Доказать mapped F5/C-144 behavior для `tests/unit/server/test_scheduling.py`.
[Description]
    Pytest surface проверяет bounded generic Server contour без production activation.
[Components]
    - Test cases и fixtures для соответствующих F5 invariants.
[Usage]
    Запускать через targeted/canonical qualification gates на disposable future-AIFE.
[Architecture]
    Tests проверяют AIFE execution/storage boundary; Data Bridge остаётся domain semantic authority.
[Note]
    Physical Linux/Docker evidence имеет отдельные qualification gates.
[Warning]
    Test PASS не означает production activation или real local AIFE integration.
"""

from datetime import datetime, timezone

from server.scheduling.models import build_f5_slot_identity
from server.work.models import F5WorkIdentityInputs, build_f5_work_id


def test_f5_slot_deterministic_and_timezone_aware():
    """Exercise the mapped F5 acceptance case."""
    due = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    a = build_f5_slot_identity(
        schedule_definition_identity="sched",
        nominal_due_at=due,
        timezone_identity="UTC",
        policy_revision_identity="p1",
    )
    assert a == build_f5_slot_identity(
        schedule_definition_identity="sched",
        nominal_due_at=due,
        timezone_identity="UTC",
        policy_revision_identity="p1",
    ) and a.startswith("slot:f5:v1:")


def test_f24_duplicate_slot_derives_same_logical_work_identity():
    """F24 binds duplicate deterministic slot observations to the same logical Work identity."""
    due = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    slot = build_f5_slot_identity(
        schedule_definition_identity="sched",
        nominal_due_at=due,
        timezone_identity="UTC",
        policy_revision_identity="p1",
    )
    inputs = {
        "domain_artifact_identity": "artifact-slot",
        "source_revision": "rev-slot",
        "content_identity": "a" * 64,
        "policy_revision_identity": "p1",
        "scheduling_slot_identity": slot,
    }
    assert build_f5_work_id(F5WorkIdentityInputs(**inputs)) == build_f5_work_id(F5WorkIdentityInputs(**inputs))
