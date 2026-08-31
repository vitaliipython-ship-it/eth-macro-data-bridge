"""Bounded F5 implementation acceptance tests for this mapped owner path."""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from server.work.models import (
    AttemptId,
    F5WorkIdentityInputs,
    IdempotencyIdentity,
    InvalidWorkTransition,
    ProvenanceReference,
    WorkExecutionStatus,
    WorkId,
    WorkIdentityReferences,
    WorkRecord,
    WorkState,
    WorkType,
    build_f5_work_id,
    retry_identity,
    retryable_attempt_failure,
    transition_work,
)


def test_f5_work_identity_exact_canonical_json_and_no_runtime_identity():
    """Exercise the mapped F5 acceptance case."""
    values = F5WorkIdentityInputs(
        domain_artifact_identity="artifact:eth:1",
        source_revision="rev-7",
        content_identity="a" * 64,
        policy_revision_identity="policy-3",
    )
    canonical = {
        "CONTENT_IDENTITY": "a" * 64,
        "DOMAIN_ARTIFACT_IDENTITY": "artifact:eth:1",
        "F5_STAGE_ID": "F5",
        "POLICY_REVISION_IDENTITY": "policy-3",
        "SCHEDULING_SLOT_IDENTITY_OR_DIRECT": "DIRECT",
        "SOURCE_REVISION": "rev-7",
        "WORK_KIND": "F5_INCOMING_ARTIFACT_PUBLICATION",
    }
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert build_f5_work_id(values).value == "work:f5:v1:" + expected
    assert values.logical_input_identity == expected
    assert all(x not in values.canonical_mapping() for x in ("NODE_ID", "PROCESS_ID", "WORKER_ID"))


def _record(state=WorkState.PENDING):
    """Exercise the mapped F5 acceptance case."""
    return WorkRecord(
        WorkId("w"),
        WorkType("t"),
        "payload",
        datetime.now(timezone.utc),
        WorkIdentityReferences(IdempotencyIdentity("i"), ProvenanceReference("p")),
        WorkExecutionStatus(state=state),
    )


def test_work_transition_and_terminal_non_reopen():
    """Exercise the mapped F5 acceptance case."""
    r = transition_work(_record(), WorkState.READY)
    r = transition_work(r, WorkState.CLAIMED, attempt_id=AttemptId("a1"), claim_reference="c1")
    r = transition_work(r, WorkState.RUNNING)
    with pytest.raises(InvalidWorkTransition):
        transition_work(transition_work(r, WorkState.CANCELLED), WorkState.READY)


def test_retry_preserves_work_identity_and_new_attempt():
    """Exercise the mapped F5 acceptance case."""
    r = _record(WorkState.READY)
    ri = retry_identity(r, AttemptId("a2"))
    assert ri.work_id == r.work_id
    rr = retryable_attempt_failure(r)
    assert rr.work_id == r.work_id and rr.state is WorkState.READY
