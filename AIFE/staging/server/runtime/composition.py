"""
Typed F3 runtime composition plus an injected F5 readiness seam; no activation.

[Purpose]
    Typed F3 runtime composition plus an injected F5 readiness seam; no activation.

[Description]
    Модуль ограничен текущим F5/C-144 contour и сохраняет существующие owner boundaries.
    Он не создаёт вторую semantic authority и не выполняет production activation.

[Components]
    - Типизированные компоненты bounded F5 contour, определённые этим модулем.

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

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from server.application import ServerApplicationServices
from server.configuration import LeaseTimingConfig, ProcessRole, RetryTimingConfig
from server.storage import StorageCapabilities

if TYPE_CHECKING:
    from server.acquisition import GenericAcquisitionService


class LifecycleComponent(Protocol):
    """Bounded F5 class `LifecycleComponent` preserving the frozen contract."""

    async def start(self) -> None:
        """Protocol operation `start` for the frozen F5 boundary."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Protocol operation `stop` for the frozen F5 boundary."""
        raise NotImplementedError


class ReadinessEvaluator(Protocol):
    """Bounded F5 class `ReadinessEvaluator` preserving the frozen contract."""

    def __call__(self) -> object:
        """Protocol operation `__call__` for the frozen F5 boundary."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ServerRuntimeDependencies:
    """Bounded F5 class `ServerRuntimeDependencies` preserving the frozen contract."""

    role: ProcessRole
    services: ServerApplicationServices
    storage: StorageCapabilities
    lease_timing: LeaseTimingConfig
    retry_timing: RetryTimingConfig
    acquisition: GenericAcquisitionService | None = None
