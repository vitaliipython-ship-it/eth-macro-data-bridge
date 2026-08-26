"""Узкие storage capability protocols по `CONTRACT-SERVER-STORAGE-001`.

Интерфейсы описывают capabilities и evidence, но не выбирают database/object-store backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server._validation import require_non_empty


@dataclass(frozen=True, slots=True)
class ObjectIdentity:
    """Opaque identity физического объекта. EN summary: backend-neutral stored object identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "object_identity"))


@dataclass(frozen=True, slots=True)
class DurableWriteRequest:
    """Запрос durable write через ссылку. EN summary: backend-neutral durable write request."""

    object_identity: ObjectIdentity
    source_revision: str
    provenance_reference: str
    content_digest: str
    payload_reference: str

    def __post_init__(self) -> None:
        for field_name in ("source_revision", "provenance_reference", "content_digest", "payload_reference"):
            object.__setattr__(self, field_name, require_non_empty(getattr(self, field_name), field_name))


@dataclass(frozen=True, slots=True)
class DurableWriteEvidence:
    """Доказательство durable write. EN summary: durable write evidence."""

    object_identity: ObjectIdentity
    content_digest: str


@dataclass(frozen=True, slots=True)
class ReadbackEvidence:
    """Результат независимого чтения. EN summary: independent readback evidence."""

    object_identity: ObjectIdentity
    content_digest: str
    source_revision: str
    provenance_reference: str


@dataclass(frozen=True, slots=True)
class InventoryCursor:
    """Opaque inventory cursor. EN summary: backend-neutral inventory cursor."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "inventory_cursor"))


@dataclass(frozen=True, slots=True)
class InventoryPage:
    """Страница inventory с явной полнотой. EN summary: explicit inventory page."""

    items: tuple[ObjectIdentity, ...]
    next_cursor: InventoryCursor | None
    complete: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MigrationBatch:
    """Пакет миграции с сохранением identity. EN summary: identity-preserving migration batch."""

    identities: tuple[ObjectIdentity, ...]
    source_revision: str
    provenance_reference: str


@dataclass(frozen=True, slots=True)
class RetentionState:
    """Общее состояние retention. EN summary: generic retention lifecycle state."""

    object_identity: ObjectIdentity
    state: str


@dataclass(frozen=True, slots=True)
class BackupReference:
    """Ссылка на backup. EN summary: backend-neutral backup reference."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "backup_reference"))


@dataclass(frozen=True, slots=True)
class RestoreReference:
    """Ссылка на restore. EN summary: backend-neutral restore reference."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "restore_reference"))


class IngestDurableWritePort(Protocol):
    """Порт durable ingest. EN summary: durable ingest write capability."""

    async def write_ingest(self, request: DurableWriteRequest) -> DurableWriteEvidence:
        """Записать ingest. EN summary: write durable ingest data."""
        raise NotImplementedError


class DurableObjectWritePort(Protocol):
    """Порт durable object write. EN summary: durable object write capability."""

    async def write_object(self, request: DurableWriteRequest) -> DurableWriteEvidence:
        """Записать объект. EN summary: write a durable object."""
        raise NotImplementedError


class ReadbackPort(Protocol):
    """Порт независимого чтения. EN summary: independent readback capability."""

    async def readback(self, identity: ObjectIdentity) -> ReadbackEvidence:
        """Прочитать evidence. EN summary: read object evidence independently."""
        raise NotImplementedError


class IdentityLookupPort(Protocol):
    """Порт поиска по identity. EN summary: identity lookup capability."""

    async def lookup(self, identity: ObjectIdentity) -> ObjectIdentity | None:
        """Найти object identity. EN summary: look up a stored identity."""
        raise NotImplementedError


class InventoryPort(Protocol):
    """Порт inventory/list. EN summary: inventory listing capability."""

    async def list_inventory(self, cursor: InventoryCursor | None = None) -> InventoryPage:
        """Получить страницу inventory. EN summary: list inventory page."""
        raise NotImplementedError


class MigrationSourcePort(Protocol):
    """Источник миграции. EN summary: migration source capability."""

    async def read_migration_batch(self, cursor: InventoryCursor | None = None) -> MigrationBatch:
        """Прочитать batch. EN summary: read an identity-preserving migration batch."""
        raise NotImplementedError


class MigrationTargetPort(Protocol):
    """Цель миграции. EN summary: migration target capability."""

    async def write_migration_batch(self, batch: MigrationBatch) -> tuple[DurableWriteEvidence, ...]:
        """Записать batch. EN summary: write an identity-preserving migration batch."""
        raise NotImplementedError


class RetentionStatePort(Protocol):
    """Порт retention state. EN summary: retention state capability."""

    async def get_retention_state(self, identity: ObjectIdentity) -> RetentionState:
        """Прочитать retention state. EN summary: read generic retention state."""
        raise NotImplementedError


class BackupPort(Protocol):
    """Порт backup reference. EN summary: backup capability."""

    async def create_backup(self, identities: tuple[ObjectIdentity, ...]) -> BackupReference:
        """Создать backup reference. EN summary: create a backup reference."""
        raise NotImplementedError


class RestorePort(Protocol):
    """Порт restore reference. EN summary: restore capability."""

    async def restore(self, backup: BackupReference) -> RestoreReference:
        """Выполнить restore boundary. EN summary: restore from a backup reference."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StorageWriteCapabilities:
    """Порты записи. EN summary: narrow storage write capabilities."""

    ingest: IngestDurableWritePort
    object_write: DurableObjectWritePort


@dataclass(frozen=True, slots=True)
class StorageReadCapabilities:
    """Порты чтения. EN summary: narrow storage read capabilities."""

    readback: ReadbackPort
    identity_lookup: IdentityLookupPort
    inventory: InventoryPort


@dataclass(frozen=True, slots=True)
class StorageMigrationCapabilities:
    """Порты миграции. EN summary: narrow storage migration capabilities."""

    source: MigrationSourcePort
    target: MigrationTargetPort


@dataclass(frozen=True, slots=True)
class StorageLifecycleCapabilities:
    """Порты lifecycle. EN summary: narrow storage lifecycle capabilities."""

    retention: RetentionStatePort
    backup: BackupPort
    restore: RestorePort


@dataclass(frozen=True, slots=True)
class StorageCapabilities:
    """Композиция узких портов. EN summary: typed composition of storage capabilities."""

    writes: StorageWriteCapabilities
    reads: StorageReadCapabilities
    migration: StorageMigrationCapabilities
    lifecycle: StorageLifecycleCapabilities
