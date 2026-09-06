"""F5C C2 composite durable-acceptance behavioral proofs."""

import asyncio
import hashlib
import sqlite3
from datetime import UTC, datetime
import pytest

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.acquisition import AcquiredArtifact, AcquisitionResultInvariantError
from server.acquisition.service import DurableAcquisitionAcceptance, GenericAcquisitionService
from server.integration.domain import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem


NOW = datetime(2026, 9, 6, 17, tzinfo=UTC)


def _envelope(payload: bytes, *, revision: str = "source-r1", digest: str | None = None) -> DomainArtifactEnvelope:
    content_identity = digest or hashlib.sha256(payload).hexdigest()
    return DomainArtifactEnvelope(
        DomainArtifactIdentity("artifact-c2"),
        DomainArtifactType("opaque-immutable"),
        revision,
        content_identity,
        DomainArtifactReferences("provider-result", "domain-provenance", "domain-accepted"),
        DomainArtifactTiming(NOW, NOW, NOW),
    )


class _Adapter:
    def __init__(self, envelope: DomainArtifactEnvelope, payload: bytes) -> None:
        self.envelope = envelope
        self.payload = payload

    async def acquire(self) -> AcquiredArtifact:
        return AcquiredArtifact(self.envelope, self.payload)


class _RecordingStore:
    def __init__(self, inner: QualifiedDataRootImmutableFilesystem, events: list[str]) -> None:
        self.inner = inner
        self.events = events
        self.fail_before_write = False
        self.fail_during_write = False
        self.fail_readback = False

    def write_immutable(self, payload: bytes, *, expected_digest: str | None = None):
        self.events.append("object.write")
        if self.fail_before_write:
            raise OSError("injected failure before object write")
        if self.fail_during_write:
            partial = self.inner.data_root / ".injected-partial"
            partial.parent.mkdir(parents=True, exist_ok=True)
            partial.write_bytes(payload[: max(1, len(payload) // 2)])
            raise OSError("injected failure during object write")
        return self.inner.write_immutable(payload, expected_digest=expected_digest)

    def readback_verify(self, content_digest: str, *, expected_size: int):
        self.events.append("object.readback")
        if self.fail_readback:
            raise OSError("injected independent readback failure")
        return self.inner.readback_verify(content_digest, expected_size=expected_size)

    def read_exact(self, content_digest: str) -> bytes:
        return self.inner.read_exact(content_digest)


class _RecordingRepository:
    def __init__(self, inner: SQLiteServerControlRepository, events: list[str], *, fail_accept: bool = False) -> None:
        self.inner = inner
        self.events = events
        self.fail_accept = fail_accept

    def accept_work(self, *args, **kwargs):
        self.events.append("work.accept")
        if self.fail_accept:
            raise RuntimeError("injected failure before Work commit")
        return self.inner.accept_work(*args, **kwargs)

    def get_work(self, work_id: str):
        return self.inner.get_work(work_id)


def _work_count(repo: SQLiteServerControlRepository) -> int:
    con = sqlite3.connect(repo.database_path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM work").fetchone()[0])
    finally:
        con.close()


def _row_count(repo: SQLiteServerControlRepository, table: str) -> int:
    con = sqlite3.connect(repo.database_path)
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        con.close()


def _service(adapter, store, repository) -> GenericAcquisitionService:
    return GenericAcquisitionService(
        adapter,
        DurableAcquisitionAcceptance(
            store,
            repository,
            policy_revision_identity="policy-c2",
        ),
    )


def test_c2_orders_object_write_readback_before_work_commit_and_survives_restart(tmp_path):
    payload = b"c2-durable-payload"
    envelope = _envelope(payload)
    events: list[str] = []
    base_store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    base_repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    result = asyncio.run(
        _service(
            _Adapter(envelope, payload),
            _RecordingStore(base_store, events),
            _RecordingRepository(base_repo, events),
        ).acquire_durable(at=NOW)
    )

    assert events == ["object.write", "object.readback", "work.accept"]
    digest = hashlib.sha256(payload).hexdigest()
    assert result.object_evidence.content_digest == digest
    assert result.object_evidence.size == len(payload)
    assert result.object_evidence.physical_locator == f"objects/sha256/{digest[:2]}/{digest}"
    assert result.work.payload_reference == result.object_evidence.physical_locator
    assert result.work.state == "PENDING"
    assert base_store.read_exact(digest) == payload
    assert _row_count(base_repo, "attempt") == 0
    assert _row_count(base_repo, "publication") == 0

    reopened_repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    reopened_store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    persisted = reopened_repo.get_work(result.work.work_id)
    assert persisted is not None and persisted.payload_reference == result.object_evidence.physical_locator
    assert reopened_store.read_exact(digest) == payload


def test_c2_payload_digest_mismatch_fails_before_any_durable_effect(tmp_path):
    payload = b"actual"
    envelope = _envelope(b"expected")
    events: list[str] = []
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = _RecordingStore(QualifiedDataRootImmutableFilesystem(tmp_path / "data"), events)

    with pytest.raises(AcquisitionResultInvariantError):
        asyncio.run(_service(_Adapter(envelope, payload), store, _RecordingRepository(repo, events)).acquire_durable(at=NOW))

    assert events == []
    assert _work_count(repo) == 0
    assert not (tmp_path / "data" / "objects").exists()


def test_c2_failure_before_object_write_accepts_nothing(tmp_path):
    payload = b"before-write"
    envelope = _envelope(payload)
    events: list[str] = []
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = _RecordingStore(QualifiedDataRootImmutableFilesystem(tmp_path / "data"), events)
    store.fail_before_write = True

    with pytest.raises(OSError, match="before object write"):
        asyncio.run(_service(_Adapter(envelope, payload), store, _RecordingRepository(repo, events)).acquire_durable(at=NOW))

    assert events == ["object.write"]
    assert _work_count(repo) == 0


def test_c2_failure_during_object_write_does_not_accept_partial_data(tmp_path):
    payload = b"during-write"
    envelope = _envelope(payload)
    digest = envelope.content_identity
    events: list[str] = []
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    inner = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    store = _RecordingStore(inner, events)
    store.fail_during_write = True

    with pytest.raises(OSError, match="during object write"):
        asyncio.run(_service(_Adapter(envelope, payload), store, _RecordingRepository(repo, events)).acquire_durable(at=NOW))

    assert events == ["object.write"]
    assert _work_count(repo) == 0
    assert not inner.locator(digest).exists()
    assert (tmp_path / "data" / ".injected-partial").exists()


def test_c2_object_persisted_but_readback_failure_creates_no_work(tmp_path):
    payload = b"readback-failure"
    envelope = _envelope(payload)
    events: list[str] = []
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    inner = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    store = _RecordingStore(inner, events)
    store.fail_readback = True

    with pytest.raises(OSError, match="readback failure"):
        asyncio.run(_service(_Adapter(envelope, payload), store, _RecordingRepository(repo, events)).acquire_durable(at=NOW))

    assert events == ["object.write", "object.readback"]
    assert inner.read_exact(envelope.content_identity) == payload
    assert _work_count(repo) == 0


def test_c2_orphan_object_before_work_commit_is_safe_to_retry(tmp_path):
    payload = b"orphan-then-retry"
    envelope = _envelope(payload)
    events: list[str] = []
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    recording_store = _RecordingStore(store, events)
    failing_repo = _RecordingRepository(repo, events, fail_accept=True)

    with pytest.raises(RuntimeError, match="before Work commit"):
        asyncio.run(_service(_Adapter(envelope, payload), recording_store, failing_repo).acquire_durable(at=NOW))

    assert events == ["object.write", "object.readback", "work.accept"]
    assert store.read_exact(envelope.content_identity) == payload
    assert _work_count(repo) == 0

    retry = asyncio.run(
        _service(
            _Adapter(envelope, payload),
            _RecordingStore(store, []),
            _RecordingRepository(repo, []),
        ).acquire_durable(at=NOW)
    )
    assert retry.work.payload_reference == retry.object_evidence.physical_locator
    assert _work_count(repo) == 1
    assert len(list((tmp_path / "data" / "objects" / "sha256").glob("*/*"))) == 1


def test_c2_sqlite_work_transaction_failure_accepts_nothing_and_retry_is_safe(tmp_path):
    payload = b"sqlite-rollback"
    envelope = _envelope(payload)
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")

    con = sqlite3.connect(repo.database_path)
    try:
        con.execute(
            "CREATE TRIGGER inject_work_failure BEFORE INSERT ON work "
            "BEGIN SELECT RAISE(ABORT, 'injected work transaction failure'); END"
        )
        con.commit()
    finally:
        con.close()

    with pytest.raises(sqlite3.IntegrityError, match="injected work transaction failure"):
        asyncio.run(_service(_Adapter(envelope, payload), store, repo).acquire_durable(at=NOW))

    assert store.read_exact(envelope.content_identity) == payload
    assert _work_count(repo) == 0

    con = sqlite3.connect(repo.database_path)
    try:
        con.execute("DROP TRIGGER inject_work_failure")
        con.commit()
    finally:
        con.close()

    retry = asyncio.run(_service(_Adapter(envelope, payload), store, repo).acquire_durable(at=NOW))
    assert retry.work.payload_reference == retry.object_evidence.physical_locator
    assert _work_count(repo) == 1


def test_c2_replay_same_logical_acquisition_is_object_and_work_idempotent(tmp_path):
    payload = b"idempotent-c2"
    envelope = _envelope(payload)
    repo = SQLiteServerControlRepository(tmp_path / "control.sqlite3")
    store = QualifiedDataRootImmutableFilesystem(tmp_path / "data")
    service = _service(_Adapter(envelope, payload), store, repo)

    first = asyncio.run(service.acquire_durable(at=NOW))
    second = asyncio.run(service.acquire_durable(at=NOW))

    assert second.object_evidence == first.object_evidence
    assert second.work.work_id == first.work.work_id
    assert second.work.payload_reference == first.work.payload_reference
    assert _work_count(repo) == 1
    assert len(list((tmp_path / "data" / "objects" / "sha256").glob("*/*"))) == 1
