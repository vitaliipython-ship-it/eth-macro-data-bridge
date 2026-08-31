"""Bounded F5 implementation acceptance tests for this mapped owner path."""

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from core.data.repositories.server_control import ControlStateConflict, WorkNotClaimable
from server.publication.models import build_f5_generation_identity
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem
from server.work.models import F5WorkIdentityInputs


def setup(tmp_path, artifact="a", rev="r1", payload=b"x"):
    """Exercise the mapped F5 acceptance case."""
    now = datetime.now(timezone.utc)
    d = hashlib.sha256(payload).hexdigest()
    repo = SQLiteServerControlRepository(tmp_path / "c.sqlite3")
    w = repo.accept_work(
        F5WorkIdentityInputs(
            domain_artifact_identity=artifact,
            source_revision=rev,
            content_identity=d,
            policy_revision_identity="p",
        ),
        payload_reference="opaque",
        provenance_reference="prov",
        created_at=now,
    )
    repo.mark_work_ready(w.work_id, at=now)
    a = repo.claim_work(w.work_id, claim_owner="w", now=now)
    repo.mark_attempt_running(a.attempt_id, fencing_token=a.fencing_token, at=now)
    p = repo.ensure_publication(
        work_id=w.work_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        domain_artifact_identity=artifact,
        source_revision=rev,
        content_checksum=d,
        content_size=len(payload),
        at=now,
    )
    return (
        now,
        repo,
        w,
        a,
        p,
        d,
        QualifiedDataRootImmutableFilesystem(tmp_path / "data"),
    )


def advance_to_publishing(repo, p, a, now):
    """Exercise the mapped F5 acceptance case."""
    p = repo.advance_publication(
        p.publication_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        target_state="STAGED",
        at=now,
    )
    return repo.advance_publication(
        p.publication_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        target_state="PUBLISHING",
        at=now,
    )


def test_f02_f03_f04_restart_windows(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now, repo, _work, a, p, d, store = setup(tmp_path, payload=b"abc")
    p = advance_to_publishing(repo, p, a, now)
    e = store.write_immutable(b"abc", expected_digest=d)
    # F02 crash after write, before DB durable evidence: reopen control state, then exact write collapses.
    repo = SQLiteServerControlRepository(tmp_path / "c.sqlite3")
    assert repo.get_publication(p.publication_id).state == "PUBLISHING"
    assert store.write_immutable(b"abc", expected_digest=d) == e
    p = repo.advance_publication(
        p.publication_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        target_state="DURABLE_STORED",
        at=now,
        physical_locator=e.physical_locator,
        evidence="dw",
    )
    rb = store.readback_verify(d, expected_size=3)
    p = repo.advance_publication(
        p.publication_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        target_state="INDEPENDENT_READBACK_VERIFIED",
        at=now,
        evidence="rb:" + rb.content_digest,
    )
    # F03 restart before registration
    repo = SQLiteServerControlRepository(tmp_path / "c.sqlite3")
    g = repo.register_generation(p.publication_id, attempt_id=a.attempt_id, fencing_token=a.fencing_token, at=now)
    # F04 restart before ACK
    repo = SQLiteServerControlRepository(tmp_path / "c.sqlite3")
    assert (
        repo.ack_publication(
            p.publication_id,
            attempt_id=a.attempt_id,
            fencing_token=a.fencing_token,
            at=now,
        ).state
        == "ACKED"
    )
    assert (
        repo.register_generation(
            p.publication_id,
            attempt_id=a.attempt_id,
            fencing_token=a.fencing_token,
            at=now,
        ).generation_identity
        == g.generation_identity
    )


def test_f05_same_target_same_bytes_and_f06_conflict(tmp_path):
    """Same bytes collapse; conflicting logical target fails Work and never overwrites accepted bytes."""
    now, repo, w, a, p, d, store = setup(tmp_path, payload=b"abc")
    accepted = store.write_immutable(b"abc", expected_digest=d)
    same = repo.ensure_publication(
        work_id=w.work_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        domain_artifact_identity="a",
        source_revision="r1",
        content_checksum=d,
        content_size=3,
        at=now,
    )
    assert same.publication_id == p.publication_id
    with pytest.raises(ControlStateConflict):
        repo.ensure_publication(
            work_id=w.work_id,
            attempt_id=a.attempt_id,
            fencing_token=a.fencing_token,
            domain_artifact_identity="a",
            source_revision="r1",
            content_checksum="f" * 64,
            content_size=3,
            at=now,
        )
    assert store.read_exact(d) == b"abc"
    assert store.readback_verify(d, expected_size=3) == accepted
    failed = repo.get_work(w.work_id)
    assert failed is not None and failed.state == "FAILED"
    assert failed.failure_state == "PUBLICATION_CONFLICT"
    assert repo.get_publication(p.publication_id).state == "INGEST_DURABLE"


def test_f26_illegal_ack_terminalizes_work_without_advancing_publication(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now, repo, _work, a, p, _digest, _store = setup(tmp_path, payload=b"one")
    with pytest.raises(ValueError):
        repo.ack_publication(
            p.publication_id,
            attempt_id=a.attempt_id,
            fencing_token=a.fencing_token,
            at=now,
        )
    assert repo.get_publication(p.publication_id).state == "INGEST_DURABLE"
    failed = repo.get_work(p.work_id)
    assert failed is not None and failed.state == "FAILED"
    assert failed.failure_state == "ILLEGAL_ACK"
    assert repo.get_attempt(a.attempt_id).state == "FAILED"


def _register_generation(repo, *, artifact, revision, content, at):
    """Create one independently-readback-ready registered generation without filesystem I/O."""
    work_inputs = F5WorkIdentityInputs(
        domain_artifact_identity=artifact,
        source_revision=revision,
        content_identity=content,
        policy_revision_identity="p",
    )
    work = repo.accept_work(work_inputs, payload_reference="x", provenance_reference="p", created_at=at)
    repo.mark_work_ready(work.work_id, at=at)
    attempt = repo.claim_work(work.work_id, claim_owner=revision, now=at)
    repo.mark_attempt_running(attempt.attempt_id, fencing_token=attempt.fencing_token, at=at)
    publication = repo.ensure_publication(
        work_id=work.work_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        domain_artifact_identity=artifact,
        source_revision=revision,
        content_checksum=content,
        content_size=3,
        at=at,
    )
    for state, kwargs in (
        ("STAGED", {}),
        ("PUBLISHING", {}),
        ("DURABLE_STORED", {"physical_locator": f"objects/sha256/{content[:2]}/{content}", "evidence": "dw"}),
        ("INDEPENDENT_READBACK_VERIFIED", {"evidence": "rb"}),
    ):
        publication = repo.advance_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            target_state=state,
            at=at,
            **kwargs,
        )
    generation = repo.register_generation(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=at,
    )
    return publication, attempt, generation


def test_f19_retry_after_newer_generation_never_rewinds_current(tmp_path):
    """Retrying an older registered publication preserves the newer current pointer."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "generation.sqlite3")
    old_pub, old_attempt, old_gen = _register_generation(
        repo, artifact="scope-a", revision="r1", content="a" * 64, at=now
    )
    _new_pub, _new_attempt, new_gen = _register_generation(
        repo, artifact="scope-a", revision="r2", content="b" * 64, at=now
    )
    assert new_gen.generation_no > old_gen.generation_no
    assert repo.resolve_generation("scope-a").generation_identity == new_gen.generation_identity

    retried = repo.register_generation(
        old_pub.publication_id,
        attempt_id=old_attempt.attempt_id,
        fencing_token=old_attempt.fencing_token,
        at=now,
    )
    assert retried.generation_identity == old_gen.generation_identity
    assert repo.resolve_generation("scope-a").generation_identity == new_gen.generation_identity


def _reclaim(repo, work, attempt, now):
    """Expire one Attempt and return the strictly newer durable authority."""
    later = now + timedelta(seconds=61)
    newer = repo.reclaim_work(work.work_id, claim_owner="reclaimer", now=later)
    assert newer.attempt_id != attempt.attempt_id
    assert newer.fencing_token > attempt.fencing_token
    assert newer.work_id == work.work_id
    return later, newer


def _publication_ack_columns(repo, publication_id):
    """Read persisted ACK-only columns independently of the repository projection."""
    con = sqlite3.connect(repo.database_path)
    try:
        return con.execute(
            "SELECT state,ack_evidence,acked_at FROM publication WHERE publication_id=?",
            (publication_id,),
        ).fetchone()
    finally:
        con.close()


def test_f10_partial_publication_reclaim_hands_authority_to_new_attempt(tmp_path):
    """Stable Publication provenance survives reclaim while current authority moves to Attempt-2."""
    now, repo, work, first, publication, _digest, _store = setup(tmp_path, payload=b"abc")
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=first.attempt_id,
        fencing_token=first.fencing_token,
        target_state="STAGED",
        at=now,
    )
    later, second = _reclaim(repo, work, first, now)
    resumed = repo.advance_publication(
        publication.publication_id,
        attempt_id=second.attempt_id,
        fencing_token=second.fencing_token,
        target_state="PUBLISHING",
        at=later,
    )
    assert resumed.publication_id == publication.publication_id
    assert resumed.attempt_id == first.attempt_id  # immutable creation provenance
    assert resumed.state == "PUBLISHING"
    assert repo.get_attempt(first.attempt_id).state == "ABANDONED"
    with pytest.raises(WorkNotClaimable):
        repo.advance_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            target_state="DURABLE_STORED",
            at=later,
            physical_locator="objects/sha256/aa/" + "a" * 64,
            evidence="old-write",
        )


@pytest.mark.parametrize("window", ["before_write", "after_write", "after_readback", "after_registration"])
def test_f10_cross_attempt_recovery_matrix(tmp_path, window):  # pylint: disable=too-many-locals
    """Each persisted crash window resumes with one stable Publication and newer authority."""
    payload = b"matrix"
    now, repo, work, first, publication, digest, store = setup(
        tmp_path / window,
        payload=payload,
    )
    publication = advance_to_publishing(repo, publication, first, now)
    durable = None
    if window in {"after_write", "after_readback", "after_registration"}:
        durable = store.write_immutable(payload, expected_digest=digest)
        publication = repo.advance_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            target_state="DURABLE_STORED",
            at=now,
            physical_locator=durable.physical_locator,
            evidence="dw:" + durable.content_digest,
        )
    if window in {"after_readback", "after_registration"}:
        readback = store.readback_verify(digest, expected_size=len(payload))
        publication = repo.advance_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            target_state="INDEPENDENT_READBACK_VERIFIED",
            at=now,
            evidence="rb:" + readback.content_digest,
        )
    old_generation = None
    if window == "after_registration":
        old_generation = repo.register_generation(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            at=now,
        )
        publication = repo.get_publication(publication.publication_id)

    later, second = _reclaim(repo, work, first, now)
    stable_id = publication.publication_id
    if window == "before_write":
        durable = store.write_immutable(payload, expected_digest=digest)
        publication = repo.advance_publication(
            stable_id,
            attempt_id=second.attempt_id,
            fencing_token=second.fencing_token,
            target_state="DURABLE_STORED",
            at=later,
            physical_locator=durable.physical_locator,
            evidence="dw:" + durable.content_digest,
        )
    elif window == "after_write":
        assert store.write_immutable(payload, expected_digest=digest) == durable
        readback = store.readback_verify(digest, expected_size=len(payload))
        publication = repo.advance_publication(
            stable_id,
            attempt_id=second.attempt_id,
            fencing_token=second.fencing_token,
            target_state="INDEPENDENT_READBACK_VERIFIED",
            at=later,
            evidence="rb:" + readback.content_digest,
        )
    elif window == "after_readback":
        generation = repo.register_generation(
            stable_id,
            attempt_id=second.attempt_id,
            fencing_token=second.fencing_token,
            at=later,
        )
        assert (
            repo.resolve_generation(publication.domain_artifact_identity).generation_identity
            == generation.generation_identity
        )
    else:
        generation = repo.register_generation(
            stable_id,
            attempt_id=second.attempt_id,
            fencing_token=second.fencing_token,
            at=later,
        )
        assert generation.generation_identity == old_generation.generation_identity
        assert (
            repo.ack_publication(
                stable_id,
                attempt_id=second.attempt_id,
                fencing_token=second.fencing_token,
                at=later,
            ).state
            == "ACKED"
        )
    assert repo.get_publication(stable_id).publication_id == stable_id


def test_old_attempt_cannot_mutate_any_publication_authority_after_reclaim(tmp_path):
    """Attempt-1 stays permanently stale after Attempt-2 takes durable authority."""
    now, repo, work, first, publication, _digest, _store = setup(tmp_path, payload=b"abc")
    publication = advance_to_publishing(repo, publication, first, now)
    later, second = _reclaim(repo, work, first, now)
    locator = "objects/sha256/aa/" + "a" * 64
    with pytest.raises(WorkNotClaimable):
        repo.advance_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            target_state="DURABLE_STORED",
            at=later,
            physical_locator=locator,
            evidence="old-write",
        )
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=second.attempt_id,
        fencing_token=second.fencing_token,
        target_state="DURABLE_STORED",
        at=later,
        physical_locator=locator,
        evidence="new-write",
    )
    with pytest.raises(WorkNotClaimable):
        repo.advance_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            target_state="INDEPENDENT_READBACK_VERIFIED",
            at=later,
            evidence="old-readback",
        )
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=second.attempt_id,
        fencing_token=second.fencing_token,
        target_state="INDEPENDENT_READBACK_VERIFIED",
        at=later,
        evidence="new-readback",
    )
    with pytest.raises(WorkNotClaimable):
        repo.register_generation(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            at=later,
        )
    repo.register_generation(
        publication.publication_id,
        attempt_id=second.attempt_id,
        fencing_token=second.fencing_token,
        at=later,
    )
    with pytest.raises(WorkNotClaimable):
        repo.ack_publication(
            publication.publication_id,
            attempt_id=first.attempt_id,
            fencing_token=first.fencing_token,
            at=later,
        )
    with pytest.raises(WorkNotClaimable):
        repo.terminal_attempt(
            first.attempt_id,
            fencing_token=first.fencing_token,
            at=later,
            success=True,
        )
    assert repo.get_publication(publication.publication_id).state == "CANONICALLY_REGISTERED"
    assert repo.get_attempt(second.attempt_id).fencing_token > first.fencing_token


def test_generic_advance_cannot_enter_canonical_registration(tmp_path):
    """T6 is the only durable entrypoint into CANONICALLY_REGISTERED."""
    now, repo, _work, attempt, publication, digest, _store = setup(tmp_path, payload=b"reg")
    publication = advance_to_publishing(repo, publication, attempt, now)
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        target_state="DURABLE_STORED",
        at=now,
        physical_locator=f"objects/sha256/{digest[:2]}/{digest}",
        evidence="dw",
    )
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        target_state="INDEPENDENT_READBACK_VERIFIED",
        at=now,
        evidence="rb",
    )
    before = repo.get_publication(publication.publication_id)
    with pytest.raises(ValueError, match="privileged publication state"):
        repo.advance_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            target_state="CANONICALLY_REGISTERED",
            at=now,
        )
    after = repo.get_publication(publication.publication_id)
    assert after == before
    assert repo.resolve_generation(publication.domain_artifact_identity) is None


def _ack_ready_publication(tmp_path, name="ack"):
    """Build one registered Publication for guarded ACK negative tests."""
    now, repo, work, attempt, publication, digest, _store = setup(tmp_path, artifact=name, payload=b"ack")
    publication = advance_to_publishing(repo, publication, attempt, now)
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        target_state="DURABLE_STORED",
        at=now,
        physical_locator=f"objects/sha256/{digest[:2]}/{digest}",
        evidence="dw",
    )
    publication = repo.advance_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        target_state="INDEPENDENT_READBACK_VERIFIED",
        at=now,
        evidence="rb",
    )
    repo.register_generation(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now,
    )
    return now, repo, work, attempt, repo.get_publication(publication.publication_id)


@pytest.mark.parametrize(
    "variant",
    [
        "no_durable_write",
        "no_readback",
        "no_registration",
        "identity_mismatch",
        "source_revision_mismatch",
        "generation_scope_mismatch",
        "generation_identity_mismatch",
        "stale_fence",
        "wrong_work",
        "wrong_attempt",
        "generic_advance",
    ],
)
def test_f26_ack_negative_gate_matrix(tmp_path, variant):  # pylint: disable=too-many-locals
    """Every required ACK predecessor/authority gate rejects independently."""
    case_root = tmp_path / variant
    now, repo, work, attempt, publication, digest, _store = setup(case_root, artifact="ack-main", payload=b"ack")
    if variant != "no_durable_write":
        publication = advance_to_publishing(repo, publication, attempt, now)
        publication = repo.advance_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            target_state="DURABLE_STORED",
            at=now,
            physical_locator=f"objects/sha256/{digest[:2]}/{digest}",
            evidence="dw",
        )
    if variant not in {"no_durable_write", "no_readback"}:
        publication = repo.advance_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            target_state="INDEPENDENT_READBACK_VERIFIED",
            at=now,
            evidence="rb",
        )
    if variant not in {"no_durable_write", "no_readback", "no_registration"}:
        repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )
        publication = repo.get_publication(publication.publication_id)

    call_attempt = attempt
    call_fence = attempt.fencing_token
    call_time = now
    if variant in {
        "identity_mismatch",
        "source_revision_mismatch",
        "generation_scope_mismatch",
        "generation_identity_mismatch",
    }:
        tamper = {
            "identity_mismatch": ("content_checksum", "f" * 64),
            "source_revision_mismatch": ("source_revision", "tampered-revision"),
            "generation_scope_mismatch": ("generation_scope_identity", "tampered-scope"),
            "generation_identity_mismatch": ("generation_identity", "gen:f5:v1:tampered"),
        }[variant]
        con = sqlite3.connect(repo.database_path)
        try:
            con.execute(
                f"UPDATE publication_generation SET {tamper[0]}=? WHERE publication_id=?",
                (tamper[1], publication.publication_id),
            )
            con.commit()
        finally:
            con.close()
    elif variant == "stale_fence":
        later, newer = _reclaim(repo, work, attempt, now)
        call_time = later
        assert newer.fencing_token > attempt.fencing_token
    elif variant == "wrong_work":
        other_now, other_repo, _other_work, other_attempt, _pub, _d, _s = setup(
            case_root / "other",
            artifact="ack-other",
            payload=b"other",
        )
        # Use another Work's valid Attempt by copying it into this repository is intentionally impossible;
        # instead create the second Work in the same control DB below.
        del other_now, other_repo, other_attempt
        inputs = F5WorkIdentityInputs(
            domain_artifact_identity="ack-other",
            source_revision="r1",
            content_identity="b" * 64,
            policy_revision_identity="p",
        )
        other_work = repo.accept_work(inputs, payload_reference="x", provenance_reference="p", created_at=now)
        repo.mark_work_ready(other_work.work_id, at=now)
        call_attempt = repo.claim_work(other_work.work_id, claim_owner="other", now=now)
        repo.mark_attempt_running(call_attempt.attempt_id, fencing_token=call_attempt.fencing_token, at=now)
        call_fence = call_attempt.fencing_token
    elif variant == "wrong_attempt":
        later, newer = _reclaim(repo, work, attempt, now)
        call_time = later
        call_fence = newer.fencing_token  # old identity paired with new fence must still fail
    elif variant == "generic_advance":
        before = _publication_ack_columns(repo, publication.publication_id)
        with pytest.raises(ValueError, match="privileged publication state"):
            repo.advance_publication(
                publication.publication_id,
                attempt_id=attempt.attempt_id,
                fencing_token=attempt.fencing_token,
                target_state="ACKED",
                at=now,
            )
        assert _publication_ack_columns(repo, publication.publication_id) == before
        return

    before = _publication_ack_columns(repo, publication.publication_id)
    with pytest.raises((ValueError, WorkNotClaimable)):
        repo.ack_publication(
            publication.publication_id,
            attempt_id=call_attempt.attempt_id,
            fencing_token=call_fence,
            at=call_time,
        )
    after = _publication_ack_columns(repo, publication.publication_id)
    assert after[0] != "ACKED"
    assert after[1] is None and after[2] is None
    assert before[1] is None and before[2] is None


def test_duplicate_guarded_ack_is_idempotent(tmp_path):
    """Repeated guarded T7 ACK preserves the same evidence and timestamp."""
    now, repo, _work, attempt, publication = _ack_ready_publication(tmp_path)
    first = repo.ack_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now,
    )
    persisted_first = _publication_ack_columns(repo, publication.publication_id)
    second = repo.ack_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(milliseconds=100),
    )
    persisted_second = _publication_ack_columns(repo, publication.publication_id)
    assert first.state == second.state == "ACKED"
    assert persisted_second == persisted_first


def test_t6_rejects_equal_number_conflicting_current_generation_pointer(tmp_path):
    """An equal generation number is idempotent only for the exact registered identity."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "equal-pointer.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
            ("gen:f5:v1:conflicting", generation.generation_scope_identity),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )


def test_t6_rejects_future_bogus_current_generation_pointer(tmp_path):
    """A pointer cannot claim a generation number that has not been durably registered."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "future-pointer.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            (
                "UPDATE publication_current_generation SET generation_identity=?,generation_no=generation_no+10 "
                "WHERE generation_scope_identity=?"
            ),
            ("gen:f5:v1:future-bogus", generation.generation_scope_identity),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )


def test_t6_rejects_stale_lower_current_generation_pointer(tmp_path):
    """The current pointer must equal the maximum registered generation before any T6 retry."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "lower-pointer.sqlite3")
    old_publication, old_attempt, old_generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    _new_publication, _new_attempt, new_generation = _register_generation(
        repo,
        artifact="pointer-scope",
        revision="r2",
        content="b" * 64,
        at=now,
    )
    assert new_generation.generation_no > old_generation.generation_no
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            (
                "UPDATE publication_current_generation SET generation_identity=?,generation_no=? "
                "WHERE generation_scope_identity=?"
            ),
            (
                old_generation.generation_identity,
                old_generation.generation_no,
                old_generation.generation_scope_identity,
            ),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="current generation pointer corruption"):
        repo.register_generation(
            old_publication.publication_id,
            attempt_id=old_attempt.attempt_id,
            fencing_token=old_attempt.fencing_token,
            at=now,
        )


@pytest.mark.parametrize(
    ("field", "value", "coherent_pointer"),
    [
        ("source_revision", "tampered-revision", False),
        ("generation_scope_identity", "tampered-scope", False),
        ("generation_identity", "gen:f5:v1:tampered", True),
        ("content_checksum", "e" * 64, False),
        ("content_size", 999, False),
        ("physical_locator", "objects/sha256/ee/tampered", False),
    ],
)
def test_t6_rejects_existing_generation_publication_identity_corruption(tmp_path, field, value, coherent_pointer):
    """T6 idempotent reconciliation rejects any persisted generation/Publication identity mismatch."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"existing-{field}.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact="existing-generation-scope",
        revision="r1",
        content="a" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            f"UPDATE publication_generation SET {field}=? WHERE publication_id=?",
            (value, publication.publication_id),
        )
        if coherent_pointer:
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                (value, generation.generation_scope_identity),
            )
        con.execute(
            "UPDATE publication SET state='INDEPENDENT_READBACK_VERIFIED',"
            "registration_evidence=NULL,registration_fencing_token=NULL WHERE publication_id=?",
            (publication.publication_id,),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="identity corruption|pointer corruption"):
        repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )
    assert repo.get_publication(publication.publication_id).state == "INDEPENDENT_READBACK_VERIFIED"


def _publication_row(repo, publication_id):
    """Read one persisted Publication row independently of repository projections."""
    con = sqlite3.connect(repo.database_path)
    try:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM publication WHERE publication_id=?", (publication_id,)).fetchone()
        return dict(row)
    finally:
        con.close()


@pytest.mark.parametrize("state", ["STAGED", "PUBLISHING", "INGEST_DURABLE"])
def test_t6_existing_generation_rejects_impossible_early_publication_state(tmp_path, state):
    """R03-001: an existing Generation cannot legitimize a Publication before independent readback."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"r03-001-{state}.sqlite3")
    publication, attempt, _generation = _register_generation(
        repo,
        artifact=f"r03-state-{state}",
        revision="r1",
        content="1" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            "UPDATE publication SET state=?,registration_evidence=NULL,registration_fencing_token=NULL "
            "WHERE publication_id=?",
            (state, publication.publication_id),
        )
        con.commit()
    finally:
        con.close()
    before = _publication_row(repo, publication.publication_id)
    with pytest.raises(RuntimeError, match="lifecycle corruption"):
        repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )
    after = _publication_row(repo, publication.publication_id)
    assert after == before


@pytest.mark.parametrize("state", ["INDEPENDENT_READBACK_VERIFIED", "CANONICALLY_REGISTERED", "ACKED"])
def test_t6_existing_generation_legal_state_matrix(tmp_path, state):
    """T6-A/B/C: exact existing registration is recoverable/idempotent only in legal lifecycle states."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"t6-legal-{state}.sqlite3")
    publication, attempt, generation = _register_generation(
        repo,
        artifact=f"t6-legal-{state}",
        revision="r1",
        content="2" * 64,
        at=now,
    )
    if state == "INDEPENDENT_READBACK_VERIFIED":
        con = sqlite3.connect(repo.database_path)
        try:
            con.execute(
                "UPDATE publication SET state='INDEPENDENT_READBACK_VERIFIED',registration_evidence=NULL,"
                "registration_fencing_token=NULL WHERE publication_id=?",
                (publication.publication_id,),
            )
            con.commit()
        finally:
            con.close()
        before = _publication_row(repo, publication.publication_id)
        assert before["registration_evidence"] is None
        returned = repo.register_generation(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )
        after = _publication_row(repo, publication.publication_id)
        assert returned.generation_identity == generation.generation_identity
        assert after["state"] == "CANONICALLY_REGISTERED"
        assert after["registration_evidence"] == "idempotent-generation:" + generation.generation_identity
        return
    if state == "ACKED":
        repo.ack_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now,
        )
    before = _publication_row(repo, publication.publication_id)
    returned = repo.register_generation(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now + timedelta(milliseconds=1),
    )
    after = _publication_row(repo, publication.publication_id)
    assert returned.generation_identity == generation.generation_identity
    assert after == before


@pytest.mark.parametrize(
    "variant",
    [
        "missing_owning_publication",
        "scope_mismatch",
        "source_revision_mismatch",
        "generation_identity_mismatch",
        "checksum_mismatch",
        "size_mismatch",
        "locator_mismatch",
        "publication_lifecycle_mismatch",
    ],
)
def test_t6_current_pointer_transitively_validates_generation_publication(
    tmp_path, variant
):  # pylint: disable=too-many-locals
    """R03-002: current pointer trust is transitive through Generation to its owning Publication."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / f"r03-002-{variant}.sqlite3")
    old_publication, old_attempt, _old_generation = _register_generation(
        repo,
        artifact="r03-current-scope",
        revision="r1",
        content="3" * 64,
        at=now,
    )
    new_publication, _new_attempt, new_generation = _register_generation(
        repo,
        artifact="r03-current-scope",
        revision="r2",
        content="4" * 64,
        at=now,
    )
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        if variant == "missing_owning_publication":
            con.execute("DELETE FROM publication WHERE publication_id=?", (new_publication.publication_id,))
        elif variant == "scope_mismatch":
            con.execute(
                "UPDATE publication SET domain_artifact_identity=? WHERE publication_id=?",
                ("r03-other-scope", new_publication.publication_id),
            )
        elif variant in {"source_revision_mismatch", "checksum_mismatch"}:
            new_revision = "r2-corrupt" if variant == "source_revision_mismatch" else new_publication.source_revision
            new_checksum = "5" * 64 if variant == "checksum_mismatch" else new_publication.content_checksum
            new_identity = build_f5_generation_identity(
                domain_artifact_identity=new_generation.generation_scope_identity,
                source_revision=new_revision,
                content_identity=new_checksum,
            )
            con.execute(
                "UPDATE publication_generation SET source_revision=?,content_checksum=?,generation_identity=? "
                "WHERE publication_id=?",
                (new_revision, new_checksum, new_identity, new_publication.publication_id),
            )
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                (new_identity, new_generation.generation_scope_identity),
            )
        elif variant == "generation_identity_mismatch":
            con.execute(
                "UPDATE publication_generation SET generation_identity=? WHERE publication_id=?",
                ("gen:f5:v1:corrupt-current", new_publication.publication_id),
            )
            con.execute(
                "UPDATE publication_current_generation SET generation_identity=? WHERE generation_scope_identity=?",
                ("gen:f5:v1:corrupt-current", new_generation.generation_scope_identity),
            )
        elif variant == "size_mismatch":
            con.execute(
                "UPDATE publication_generation SET content_size=content_size+1 WHERE publication_id=?",
                (new_publication.publication_id,),
            )
        elif variant == "locator_mismatch":
            con.execute(
                "UPDATE publication_generation SET physical_locator=? WHERE publication_id=?",
                ("objects/sha256/ff/corrupt", new_publication.publication_id),
            )
        elif variant == "publication_lifecycle_mismatch":
            con.execute(
                "UPDATE publication SET state='STAGED',registration_evidence=NULL WHERE publication_id=?",
                (new_publication.publication_id,),
            )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="pointer corruption|relation corruption"):
        repo.register_generation(
            old_publication.publication_id,
            attempt_id=old_attempt.attempt_id,
            fencing_token=old_attempt.fencing_token,
            at=now,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generation_scope_identity", "post-ack-scope-corrupt"),
        ("source_revision", "post-ack-revision-corrupt"),
        ("generation_identity", "gen:f5:v1:post-ack-corrupt"),
        ("content_checksum", "6" * 64),
        ("content_size", 999),
        ("physical_locator", "objects/sha256/66/post-ack-corrupt"),
    ],
)
def test_f26_duplicate_ack_revalidates_post_ack_generation_integrity(tmp_path, field, value):
    """R03-003: duplicate ACK rejects every persisted Generation corruption without rewriting ACK evidence."""
    now, repo, _work, attempt, publication = _ack_ready_publication(tmp_path / field, name=f"post-ack-{field}")
    first = repo.ack_publication(
        publication.publication_id,
        attempt_id=attempt.attempt_id,
        fencing_token=attempt.fencing_token,
        at=now,
    )
    assert first.state == "ACKED"
    before = _publication_ack_columns(repo, publication.publication_id)
    con = sqlite3.connect(repo.database_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute(
            f"UPDATE publication_generation SET {field}=? WHERE publication_id=?",
            (value, publication.publication_id),
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(ValueError, match="ILLEGAL_ACK"):
        repo.ack_publication(
            publication.publication_id,
            attempt_id=attempt.attempt_id,
            fencing_token=attempt.fencing_token,
            at=now + timedelta(milliseconds=1),
        )
    after = _publication_ack_columns(repo, publication.publication_id)
    assert before[0] == after[0] == "ACKED"
    assert after[1:] == before[1:]
    con = sqlite3.connect(repo.database_path)
    try:
        persisted = con.execute(
            f"SELECT {field} FROM publication_generation WHERE publication_id=?",
            (publication.publication_id,),
        ).fetchone()[0]
    finally:
        con.close()
    assert persisted == value
