"""Storage capability types; F5 adds a bounded immutable opaque-object profile."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from server._validation import require_non_empty


@dataclass(frozen=True, slots=True)
class ObjectIdentity:
    """Bounded F5 class `ObjectIdentity` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "object_identity"))


@dataclass(frozen=True, slots=True)
class DurableWriteRequest:
    """Bounded F5 class `DurableWriteRequest` preserving the frozen contract."""

    object_identity: ObjectIdentity
    source_revision: str
    provenance_reference: str
    content_digest: str
    payload_reference: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        for n in (
            "source_revision",
            "provenance_reference",
            "content_digest",
            "payload_reference",
        ):
            object.__setattr__(self, n, require_non_empty(getattr(self, n), n))


@dataclass(frozen=True, slots=True)
class DurableWriteEvidence:
    """Bounded F5 class `DurableWriteEvidence` preserving the frozen contract."""

    object_identity: ObjectIdentity
    content_digest: str


@dataclass(frozen=True, slots=True)
class ReadbackEvidence:
    """Bounded F5 class `ReadbackEvidence` preserving the frozen contract."""

    object_identity: ObjectIdentity
    content_digest: str
    source_revision: str
    provenance_reference: str


@dataclass(frozen=True, slots=True)
class InventoryCursor:
    """Bounded F5 class `InventoryCursor` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "inventory_cursor"))


@dataclass(frozen=True, slots=True)
class InventoryPage:
    """Bounded F5 class `InventoryPage` preserving the frozen contract."""

    items: tuple[ObjectIdentity, ...]
    next_cursor: InventoryCursor | None
    complete: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MigrationBatch:
    """Bounded F5 class `MigrationBatch` preserving the frozen contract."""

    identities: tuple[ObjectIdentity, ...]
    source_revision: str
    provenance_reference: str


@dataclass(frozen=True, slots=True)
class RetentionState:
    """Bounded F5 class `RetentionState` preserving the frozen contract."""

    object_identity: ObjectIdentity
    state: str


@dataclass(frozen=True, slots=True)
class BackupReference:
    """Bounded F5 class `BackupReference` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "backup_reference"))


@dataclass(frozen=True, slots=True)
class RestoreReference:
    """Bounded F5 class `RestoreReference` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "restore_reference"))


class IngestDurableWritePort(Protocol):
    """Bounded F5 class `IngestDurableWritePort` preserving the frozen contract."""

    async def write_ingest(self, request: DurableWriteRequest) -> DurableWriteEvidence:
        """Protocol operation `write_ingest` for the frozen F5 boundary."""
        raise NotImplementedError


class DurableObjectWritePort(Protocol):
    """Bounded F5 class `DurableObjectWritePort` preserving the frozen contract."""

    async def write_object(self, request: DurableWriteRequest) -> DurableWriteEvidence:
        """Protocol operation `write_object` for the frozen F5 boundary."""
        raise NotImplementedError


class ReadbackPort(Protocol):
    """Bounded F5 class `ReadbackPort` preserving the frozen contract."""

    async def readback(self, identity: ObjectIdentity) -> ReadbackEvidence:
        """Protocol operation `readback` for the frozen F5 boundary."""
        raise NotImplementedError


class IdentityLookupPort(Protocol):
    """Bounded F5 class `IdentityLookupPort` preserving the frozen contract."""

    async def lookup(self, identity: ObjectIdentity) -> ObjectIdentity | None:
        """Protocol operation `lookup` for the frozen F5 boundary."""
        raise NotImplementedError


class InventoryPort(Protocol):
    """Bounded F5 class `InventoryPort` preserving the frozen contract."""

    async def list_inventory(self, cursor: InventoryCursor | None = None) -> InventoryPage:
        """Protocol operation `list_inventory` for the frozen F5 boundary."""
        raise NotImplementedError


class MigrationSourcePort(Protocol):
    """Bounded F5 class `MigrationSourcePort` preserving the frozen contract."""

    async def read_migration_batch(self, cursor: InventoryCursor | None = None) -> MigrationBatch:
        """Protocol operation `read_migration_batch` for the frozen F5 boundary."""
        raise NotImplementedError


class MigrationTargetPort(Protocol):
    """Bounded F5 class `MigrationTargetPort` preserving the frozen contract."""

    async def write_migration_batch(self, batch: MigrationBatch) -> tuple[DurableWriteEvidence, ...]:
        """Protocol operation `write_migration_batch` for the frozen F5 boundary."""
        raise NotImplementedError


class RetentionStatePort(Protocol):
    """Bounded F5 class `RetentionStatePort` preserving the frozen contract."""

    async def get_retention_state(self, identity: ObjectIdentity) -> RetentionState:
        """Protocol operation `get_retention_state` for the frozen F5 boundary."""
        raise NotImplementedError


class BackupPort(Protocol):
    """Bounded F5 class `BackupPort` preserving the frozen contract."""

    async def create_backup(self, identities: tuple[ObjectIdentity, ...]) -> BackupReference:
        """Protocol operation `create_backup` for the frozen F5 boundary."""
        raise NotImplementedError


class RestorePort(Protocol):
    """Bounded F5 class `RestorePort` preserving the frozen contract."""

    async def restore(self, backup: BackupReference) -> RestoreReference:
        """Protocol operation `restore` for the frozen F5 boundary."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StorageWriteCapabilities:
    """Bounded F5 class `StorageWriteCapabilities` preserving the frozen contract."""

    ingest: IngestDurableWritePort
    object_write: DurableObjectWritePort


@dataclass(frozen=True, slots=True)
class StorageReadCapabilities:
    """Bounded F5 class `StorageReadCapabilities` preserving the frozen contract."""

    readback: ReadbackPort
    identity_lookup: IdentityLookupPort
    inventory: InventoryPort


@dataclass(frozen=True, slots=True)
class StorageMigrationCapabilities:
    """Bounded F5 class `StorageMigrationCapabilities` preserving the frozen contract."""

    source: MigrationSourcePort
    target: MigrationTargetPort


@dataclass(frozen=True, slots=True)
class StorageLifecycleCapabilities:
    """Bounded F5 class `StorageLifecycleCapabilities` preserving the frozen contract."""

    retention: RetentionStatePort
    backup: BackupPort
    restore: RestorePort


@dataclass(frozen=True, slots=True)
class StorageCapabilities:
    """Bounded F5 class `StorageCapabilities` preserving the frozen contract."""

    writes: StorageWriteCapabilities
    reads: StorageReadCapabilities
    migration: StorageMigrationCapabilities
    lifecycle: StorageLifecycleCapabilities


@dataclass(frozen=True, slots=True)
class ImmutableObjectEvidence:
    """Bounded F5 class `ImmutableObjectEvidence` preserving the frozen contract."""

    content_digest: str
    size: int
    physical_locator: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(
            self,
            "content_digest",
            require_non_empty(self.content_digest, "content_digest"),
        )
        object.__setattr__(
            self,
            "physical_locator",
            require_non_empty(self.physical_locator, "physical_locator"),
        )
        if self.size < 0:
            raise ValueError("size cannot be negative")


class ImmutableObjectConflict(RuntimeError):
    """Bounded F5 class `ImmutableObjectConflict` preserving the frozen contract."""


class ImmutableObjectStore(Protocol):
    """Bounded F5 class `ImmutableObjectStore` preserving the frozen contract."""

    def write_immutable(self, payload: bytes, *, expected_digest: str | None = None) -> ImmutableObjectEvidence:
        """Protocol operation `write_immutable` for the frozen F5 boundary."""
        raise NotImplementedError

    def read_exact(self, content_digest: str) -> bytes:
        """Protocol operation `read_exact` for the frozen F5 boundary."""
        raise NotImplementedError

    def readback_verify(self, content_digest: str, *, expected_size: int) -> ImmutableObjectEvidence:
        """Protocol operation `readback_verify` for the frozen F5 boundary."""
        raise NotImplementedError
