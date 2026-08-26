"""Application-facing service protocols для будущей композиции через `AppContext`.

Protocols не создают второй DI-container и не являются concrete runtime services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from server.access import AccessRequest, AccessResult
from server.execution import Lease
from server.publication import PublicationRecord
from server.scheduling import DueMaterialization, ScheduleDefinition
from server.work import WorkRecord

T = TypeVar("T")


class WorkService(Protocol):
    """Сервис работы. EN summary: application-facing work service protocol."""

    async def submit(self, record: WorkRecord) -> WorkRecord:
        """Принять логическую работу. EN summary: submit logical work."""
        raise NotImplementedError


class SchedulingService(Protocol):
    """Сервис планирования. EN summary: application-facing scheduling service protocol."""

    async def materialize(self, definition: ScheduleDefinition) -> DueMaterialization | None:
        """Получить due-materialization. EN summary: materialize a due reference."""
        raise NotImplementedError


class ExecutionService(Protocol):
    """Сервис execution. EN summary: application-facing execution service protocol."""

    async def claim(self, record: WorkRecord) -> Lease:
        """Получить lease. EN summary: claim execution authority."""
        raise NotImplementedError


class PublicationService(Protocol):
    """Сервис публикации. EN summary: application-facing publication service protocol."""

    async def reconcile(self, record: PublicationRecord) -> PublicationRecord:
        """Согласовать durable state. EN summary: reconcile publication state."""
        raise NotImplementedError


class AccessService(Protocol[T]):
    """Сервис чтения. EN summary: application-facing access service protocol."""

    async def query(self, request: AccessRequest) -> AccessResult[T]:
        """Выполнить generic query. EN summary: execute a generic access query."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ServerApplicationServices:
    """Набор application services. EN summary: typed server application service bundle."""

    work: WorkService
    scheduling: SchedulingService
    execution: ExecutionService
    publication: PublicationService
    access: AccessService[object]
