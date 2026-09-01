"""
Bounded F5 implementation acceptance tests for this mapped owner path.

[Purpose]
    Доказать bounded F5 implementation acceptance tests for this mapped owner path.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Pytest cases и fixtures, проверяющие mapped F5 invariants этого owner path.

[Usage]
    Запускать через canonical pytest/toolchain gates; тесты не являются production runtime.

[Architecture]
    Test surface проверяет generic AIFE Server contour на disposable future-AIFE tree; Data Bridge
    остаётся authority domain semantics.

[Note]
    Physical SQLite/filesystem и Docker qualification имеют отдельные evidence gates поверх этих тестов.

[Warning]
    Не ослаблять assertions и не принимать unit/integration PASS за production или Docker activation.
"""

import hashlib
from datetime import datetime, timezone

from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.application.services import F5BoundedPublicationCoordinator
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem
from server.work.models import F5WorkIdentityInputs


def test_f5_publication_contract_flow(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    now = datetime.now(timezone.utc)
    repo = SQLiteServerControlRepository(tmp_path / "c.sqlite3")
    payload = b"validated-domain-artifact"
    digest = hashlib.sha256(payload).hexdigest()
    inp = F5WorkIdentityInputs(
        domain_artifact_identity="artifact",
        source_revision="r1",
        content_identity=digest,
        policy_revision_identity="p",
    )
    w = repo.accept_work(inp, payload_reference="opaque", provenance_reference="prov", created_at=now)
    repo.mark_work_ready(w.work_id, at=now)
    a = repo.claim_work(w.work_id, claim_owner="worker", now=now)
    repo.mark_attempt_running(a.attempt_id, fencing_token=a.fencing_token, at=now)
    service = F5BoundedPublicationCoordinator(repo, QualifiedDataRootImmutableFilesystem(tmp_path / "data"))
    p = service.publish(
        work_id=w.work_id,
        attempt_id=a.attempt_id,
        fencing_token=a.fencing_token,
        domain_artifact_identity="artifact",
        source_revision="r1",
        payload=payload,
        content_checksum=digest,
        at=now,
    )
    assert p.state == "ACKED"
    assert repo.resolve_generation("artifact") is not None
