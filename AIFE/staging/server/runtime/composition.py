"""Typed composition boundary для будущей публикации через `AppContext`.

Модуль не содержит singleton, service locator, startup registry или multiprocess orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.application import ServerApplicationServices
from server.configuration import LeaseTimingConfig, ProcessRole, RetryTimingConfig
from server.storage import StorageCapabilities


class LifecycleComponent(Protocol):
    """Минимальный async lifecycle seam. EN summary: minimal asynchronous lifecycle protocol."""

    async def start(self) -> None:
        """Запустить компонент. EN summary: start a lifecycle component."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Остановить компонент. EN summary: stop a lifecycle component."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ServerRuntimeDependencies:
    """Typed зависимости Server/Data. EN summary: typed server runtime dependency container."""

    role: ProcessRole
    services: ServerApplicationServices
    storage: StorageCapabilities
    lease_timing: LeaseTimingConfig
    retry_timing: RetryTimingConfig
