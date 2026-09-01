"""
Bounded control backup/isolated restore orchestration for F5 tests.

[Purpose]
    Оркестрировать bounded backup/isolated restore для F5 control state.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Backup creation, isolated restore и post-restore reconciliation helpers.

[Usage]
    Использовать через typed bounded F5 interfaces и owner-mapped application/runtime composition.

[Architecture]
    Модуль принадлежит generic AIFE Server execution/storage contour; Data Bridge сохраняет
    market-data semantic authority.

[Note]
    Реализация рассчитана на one-server SQLite/WAL + immutable filesystem profile и fail-closed invariants.

[Warning]
    Не переносить domain/provider semantics в Work IDs, SQLite keys, filesystem locators или execution state.
"""

from pathlib import Path
from typing import Any, cast

from core.data.adapters.sqlite_control import SQLiteServerControlRepository, restore_sqlite_backup
from core.data.repositories.server_control import ControlBackupEvidence, ControlRestoreEvidence
from server.storage.ports import ImmutableObjectStore


def create_control_backup(repository: Any, destination: str | Path) -> ControlBackupEvidence:
    """F5 contract-bound function `create_control_backup`. EN summary: bounded F5 function."""
    return cast(ControlBackupEvidence, repository.backup_to(destination))


def restore_control_backup(
    backup: ControlBackupEvidence, destination: str | Path
) -> tuple[SQLiteServerControlRepository, ControlRestoreEvidence]:
    """Restore only the exact backup identity frozen by `create_control_backup`."""
    return restore_sqlite_backup(
        backup.backup_path,
        destination,
        expected_backup_sha256=backup.sha256,
        expected_backup_size=backup.size,
    )


def reconcile_registered_objects(
    repository: Any, object_store: ImmutableObjectStore
) -> tuple[tuple[str, str, int], ...]:
    """F5 contract-bound function `reconcile_registered_objects`. EN summary: bounded F5 function."""
    evidence: list[tuple[str, str, int]] = []
    generations = tuple(repository.list_generations())
    by_scope: dict[str, list[Any]] = {}
    for generation in generations:
        by_scope.setdefault(generation.generation_scope_identity, []).append(generation)
        rb = object_store.readback_verify(generation.content_checksum, expected_size=generation.content_size)
        if rb.physical_locator != generation.physical_locator:
            raise RuntimeError("registered generation physical locator mismatch")
        evidence.append((generation.generation_identity, rb.content_digest, rb.size))
    for scope, rows in by_scope.items():
        expected_current = max(rows, key=lambda row: row.generation_no)
        current = repository.resolve_generation(scope)
        if (
            current is None
            or current.generation_identity != expected_current.generation_identity
            or current.generation_no != expected_current.generation_no
        ):
            raise RuntimeError("current generation pointer reconciliation mismatch")
    return tuple(evidence)
