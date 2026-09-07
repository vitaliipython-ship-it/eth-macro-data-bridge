"""F5C C1 provider-neutral acquisition boundary acceptance tests."""

import asyncio
import hashlib
from dataclasses import fields
from datetime import UTC, datetime

import pytest

from server.acquisition import (
    AcquiredArtifact,
    AcquisitionResultInvariantError,
    GenericAcquisitionService,
)
from server.integration.domain import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)
from server.runtime.composition import ServerRuntimeDependencies


def _envelope(source_revision: str, payload: bytes) -> DomainArtifactEnvelope:
    now = datetime(2026, 9, 6, 16, tzinfo=UTC)
    return DomainArtifactEnvelope(
        DomainArtifactIdentity(f"artifact-{source_revision}"),
        DomainArtifactType("opaque-immutable"),
        source_revision,
        hashlib.sha256(payload).hexdigest(),
        DomainArtifactReferences(
            f"payload-{source_revision}",
            f"provenance-{source_revision}",
            f"accepted-{source_revision}",
        ),
        DomainArtifactTiming(now, now, now),
    )


class _FakeAdapterA:
    async def acquire(self) -> AcquiredArtifact:
        payload = b"source-a"
        return AcquiredArtifact(_envelope("source-a-r1", payload), payload)


class _FakeAdapterB:
    async def acquire(self) -> AcquiredArtifact:
        payload = b"source-b"
        return AcquiredArtifact(_envelope("source-b-r9", payload), payload)


class _MismatchedAdapter:
    async def acquire(self) -> AcquiredArtifact:
        return AcquiredArtifact(_envelope("source-c", b"different"), b"payload")


def test_two_adapters_use_same_generic_acquisition_boundary():
    """Two source identities use the same Server boundary without core branching."""
    first = asyncio.run(GenericAcquisitionService(_FakeAdapterA()).acquire())
    second = asyncio.run(GenericAcquisitionService(_FakeAdapterB()).acquire())

    assert first.payload == b"source-a"
    assert second.payload == b"source-b"
    assert first.envelope.source_revision != second.envelope.source_revision
    assert type(GenericAcquisitionService(_FakeAdapterA())) is type(
        GenericAcquisitionService(_FakeAdapterB())
    )


def test_generic_boundary_rejects_payload_identity_mismatch():
    """The neutral boundary fails closed when envelope and exact bytes disagree."""
    with pytest.raises(AcquisitionResultInvariantError):
        asyncio.run(GenericAcquisitionService(_MismatchedAdapter()).acquire())


def test_runtime_composition_adds_only_optional_acquisition_seam():
    """Existing five-field composition remains valid and gains one optional seam."""
    runtime_fields = fields(ServerRuntimeDependencies)
    assert tuple(field.name for field in runtime_fields) == (
        "role",
        "services",
        "storage",
        "lease_timing",
        "retry_timing",
        "acquisition",
    )
    assert runtime_fields[-1].default is None

    legacy = ServerRuntimeDependencies(object(), object(), object(), object(), object())
    assert legacy.acquisition is None

    service = GenericAcquisitionService(_FakeAdapterA())
    composed = ServerRuntimeDependencies(
        object(), object(), object(), object(), object(), service
    )
    assert composed.acquisition is service


def test_c5_two_sources_share_same_durable_restart_replay_path(tmp_path):
    """Two source adapters reuse one generic durable/reopen/replay mechanism."""
    import sqlite3

    from core.data.adapters.sqlite_control import SQLiteServerControlRepository
    from server.acquisition.service import DurableAcquisitionAcceptance
    from server.storage.filesystem import QualifiedDataRootImmutableFilesystem

    now = datetime(2026, 9, 6, 18, tzinfo=UTC)
    database_path = tmp_path / "c5-ext-control.sqlite3"
    data_root = tmp_path / "c5-ext-data"
    repo = SQLiteServerControlRepository(database_path)
    store = QualifiedDataRootImmutableFilesystem(data_root)

    first_a = asyncio.run(
        GenericAcquisitionService(
            _FakeAdapterA(),
            DurableAcquisitionAcceptance(
                store,
                repo,
                policy_revision_identity="policy-c5-ext",
            ),
        ).acquire_durable(at=now)
    )
    first_b = asyncio.run(
        GenericAcquisitionService(
            _FakeAdapterB(),
            DurableAcquisitionAcceptance(
                store,
                repo,
                policy_revision_identity="policy-c5-ext",
            ),
        ).acquire_durable(at=now)
    )

    del repo, store
    reopened_repo = SQLiteServerControlRepository(database_path)
    reopened_store = QualifiedDataRootImmutableFilesystem(data_root)
    replay_a = asyncio.run(
        GenericAcquisitionService(
            _FakeAdapterA(),
            DurableAcquisitionAcceptance(
                reopened_store,
                reopened_repo,
                policy_revision_identity="policy-c5-ext",
            ),
        ).acquire_durable(at=now)
    )
    replay_b = asyncio.run(
        GenericAcquisitionService(
            _FakeAdapterB(),
            DurableAcquisitionAcceptance(
                reopened_store,
                reopened_repo,
                policy_revision_identity="policy-c5-ext",
            ),
        ).acquire_durable(at=now)
    )

    assert replay_a.work.work_id == first_a.work.work_id
    assert replay_b.work.work_id == first_b.work.work_id
    assert replay_a.object_evidence == first_a.object_evidence
    assert replay_b.object_evidence == first_b.object_evidence
    assert replay_a.work.payload_reference == first_a.work.payload_reference
    assert replay_b.work.payload_reference == first_b.work.payload_reference
    assert reopened_store.read_exact(replay_a.object_evidence.content_digest) == b"source-a"
    assert reopened_store.read_exact(replay_b.object_evidence.content_digest) == b"source-b"

    con = sqlite3.connect(database_path)
    try:
        assert int(con.execute("SELECT COUNT(*) FROM work").fetchone()[0]) == 2
    finally:
        con.close()
    assert len(list((data_root / "objects" / "sha256").glob("*/*"))) == 2
