"""Проверки STORAGE capability boundary F3."""

import inspect
from pathlib import Path

from server.storage import (
    BackupPort,
    DurableObjectWritePort,
    IdentityLookupPort,
    IngestDurableWritePort,
    InventoryPort,
    MigrationSourcePort,
    MigrationTargetPort,
    ReadbackPort,
    RestorePort,
    RetentionStatePort,
)


def test_storage_protocols_are_capability_bounded() -> None:
    """Проверить узость storage capability protocols."""
    protocols = (
        IngestDurableWritePort,
        DurableObjectWritePort,
        ReadbackPort,
        IdentityLookupPort,
        InventoryPort,
        MigrationSourcePort,
        MigrationTargetPort,
        RetentionStatePort,
        BackupPort,
        RestorePort,
    )
    for protocol in protocols:
        public_methods = [
            name for name, value in vars(protocol).items() if callable(value) and not name.startswith("_")
        ]
        assert len(public_methods) == 1, (protocol.__name__, public_methods)


def test_storage_public_model_has_no_backend_assumptions() -> None:
    """Проверить отсутствие backend assumptions в storage API."""
    source = Path(inspect.getsourcefile(IngestDurableWritePort) or "").read_text(encoding="utf-8").lower()
    banned = ("postgresql", "sqlite", "mongodb", "redis", "s3", "parquet")
    assert not any(token in source for token in banned)
