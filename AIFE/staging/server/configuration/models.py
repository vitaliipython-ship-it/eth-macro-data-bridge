"""
F3 configuration types plus bounded F5 readiness input identities.

[Purpose]
    F3 configuration types plus bounded F5 readiness input identities.

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
from datetime import timedelta
from enum import StrEnum
from pathlib import Path


class ProcessRole(StrEnum):
    """F5 contract-bound class `ProcessRole`. EN summary: bounded F5 class."""

    CONTROL = "CONTROL"
    WORKER = "WORKER"
    COMBINED_INITIAL_NODE = "COMBINED_INITIAL_NODE"


@dataclass(frozen=True, slots=True)
class LeaseTimingConfig:
    """F5 contract-bound class `LeaseTimingConfig`. EN summary: bounded F5 class."""

    default_lease: timedelta
    renewal_margin: timedelta

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        if self.default_lease <= timedelta(0):
            raise ValueError("default_lease должен быть положительным")
        if self.renewal_margin <= timedelta(0) or self.renewal_margin >= self.default_lease:
            raise ValueError("renewal_margin должен быть внутри default_lease")


@dataclass(frozen=True, slots=True)
class RetryTimingConfig:
    """F5 contract-bound class `RetryTimingConfig`. EN summary: bounded F5 class."""

    base_delay: timedelta
    max_delay: timedelta
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        if self.base_delay <= timedelta(0):
            raise ValueError("base_delay должен быть положительным")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay не может быть меньше base_delay")
        if self.multiplier < 1.0:
            raise ValueError("multiplier должен быть не меньше 1.0")

    def delay_for(self, retry_index: int) -> timedelta:
        """F5 contract-bound function `delay_for`. EN summary: bounded F5 function."""
        if retry_index < 0:
            raise ValueError("retry_index не может быть отрицательным")
        return min(
            timedelta(seconds=self.base_delay.total_seconds() * (self.multiplier**retry_index)),
            self.max_delay,
        )


@dataclass(frozen=True, slots=True)
class F5ReadinessConfig:
    """F5 contract-bound class `F5ReadinessConfig`. EN summary: bounded F5 class."""

    deployment_map_path: Path
    expected_release_identity: str
    expected_config_identity: str
    expected_control_schema_id: str = "aife-server-control"
    expected_control_schema_version: int = 1
    minimum_free_bytes: int = 1
    expected_backing_identity: str | None = None
