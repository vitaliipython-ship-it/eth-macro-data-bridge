"""Typed F3 runtime composition plus an injected F5 readiness seam; no activation."""

from dataclasses import dataclass
from typing import Protocol
from server.application import ServerApplicationServices
from server.configuration import LeaseTimingConfig, ProcessRole, RetryTimingConfig
from server.storage import StorageCapabilities


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
