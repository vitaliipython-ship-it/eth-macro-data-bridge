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

import pytest

from server.storage.filesystem import QualifiedDataRootImmutableFilesystem
from server.storage.ports import ImmutableObjectConflict


def test_immutable_write_readback_and_same_digest_collapse(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    store = QualifiedDataRootImmutableFilesystem(tmp_path)
    payload = b"opaque-domain-artifact"
    d = hashlib.sha256(payload).hexdigest()
    first = store.write_immutable(payload, expected_digest=d)
    second = store.write_immutable(payload, expected_digest=d)
    assert (
        first == second and first.physical_locator == f"objects/sha256/{d[:2]}/{d}" and store.read_exact(d) == payload
    )


def test_wrong_content_identity_never_overwrites(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    store = QualifiedDataRootImmutableFilesystem(tmp_path)
    d = hashlib.sha256(b"first").hexdigest()
    store.write_immutable(b"first", expected_digest=d)
    with pytest.raises(ImmutableObjectConflict):
        store.write_immutable(b"second", expected_digest=d)
    assert store.read_exact(d) == b"first"


def test_independent_readback_detects_corruption(tmp_path):
    """Exercise the mapped F5 acceptance case."""
    store = QualifiedDataRootImmutableFilesystem(tmp_path)
    payload = b"x"
    e = store.write_immutable(payload)
    store.locator(e.content_digest).write_bytes(b"y")
    with pytest.raises(ImmutableObjectConflict):
        store.readback_verify(e.content_digest, expected_size=1)
