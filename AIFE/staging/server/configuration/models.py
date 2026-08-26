"""Минимальные конфигурационные типы Server/Data.

Здесь нет production configuration system; только значения, необходимые чистым F3-механизмам.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum


class ProcessRole(StrEnum):
    """Роль процесса Server/Data. EN summary: server process role identity."""

    CONTROL = "CONTROL"
    WORKER = "WORKER"
    COMBINED_INITIAL_NODE = "COMBINED_INITIAL_NODE"


@dataclass(frozen=True, slots=True)
class LeaseTimingConfig:
    """Параметры lease timing. EN summary: generic lease timing configuration."""

    default_lease: timedelta
    renewal_margin: timedelta

    def __post_init__(self) -> None:
        if self.default_lease <= timedelta(0):
            raise ValueError("default_lease должен быть положительным")
        if self.renewal_margin <= timedelta(0) or self.renewal_margin >= self.default_lease:
            raise ValueError("renewal_margin должен быть внутри default_lease")


@dataclass(frozen=True, slots=True)
class RetryTimingConfig:
    """Параметры generic backoff. EN summary: deterministic retry timing configuration."""

    base_delay: timedelta
    max_delay: timedelta
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.base_delay <= timedelta(0):
            raise ValueError("base_delay должен быть положительным")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay не может быть меньше base_delay")
        if self.multiplier < 1.0:
            raise ValueError("multiplier должен быть не меньше 1.0")

    def delay_for(self, retry_index: int) -> timedelta:
        """Вычислить backoff. EN summary: compute deterministic bounded retry delay."""
        if retry_index < 0:
            raise ValueError("retry_index не может быть отрицательным")
        seconds = self.base_delay.total_seconds() * (self.multiplier**retry_index)
        return min(timedelta(seconds=seconds), self.max_delay)
