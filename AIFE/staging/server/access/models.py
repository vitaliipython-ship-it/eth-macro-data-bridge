"""Типизированная read/query boundary по `CONTRACT-SERVER-ACCESS-001`.

Модуль не реализует HTTP API и не переопределяет доменную нормализацию или финальность.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeAlias, TypeVar

from server._validation import require_non_empty

Scalar: TypeAlias = str | int | float | bool | None
T = TypeVar("T")


class FilterOperator(StrEnum):
    """Общий оператор фильтра. EN summary: generic query filter operator."""

    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"


@dataclass(frozen=True, slots=True)
class QueryFilter:
    """Типизированный фильтр запроса. EN summary: typed generic query filter."""

    field: str
    operator: FilterOperator
    value: Scalar

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", require_non_empty(self.field, "filter.field"))


@dataclass(frozen=True, slots=True)
class PaginationCursor:
    """Opaque pagination cursor. EN summary: pagination cursor bound to query semantics."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "pagination_cursor"))


@dataclass(frozen=True, slots=True)
class SnapshotIdentity:
    """Идентичность snapshot/freshness. EN summary: snapshot or freshness identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "snapshot_identity"))


@dataclass(frozen=True, slots=True)
class AccessRequest:
    """Общий запрос чтения. EN summary: generic typed access request."""

    filters: tuple[QueryFilter, ...] = ()
    cursor: PaginationCursor | None = None
    snapshot_identity: SnapshotIdentity | None = None


@dataclass(frozen=True, slots=True)
class ResultIdentity:
    """Идентичность результата. EN summary: stable access result identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "result_identity"))


@dataclass(frozen=True, slots=True)
class AccessSourceRevision:
    """Ревизия источника результата. EN summary: access source revision."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "source_revision"))


@dataclass(frozen=True, slots=True)
class AccessProvenance:
    """Происхождение результата. EN summary: access result provenance."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "provenance"))


@dataclass(frozen=True, slots=True)
class AccessError:
    """Явная ошибка части запроса. EN summary: explicit access error."""

    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_non_empty(self.code, "error.code"))
        object.__setattr__(self, "message", require_non_empty(self.message, "error.message"))


class ResultCompleteness(StrEnum):
    """Полнота результата. EN summary: access result completeness state."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class AccessResultPage:
    """Pagination и evidence неполноты. EN summary: result page and partial evidence."""

    next_cursor: PaginationCursor | None = None
    errors: tuple[AccessError, ...] = ()
    unavailable_partitions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AccessResult(Generic[T]):
    """Результат с identity/provenance/error. EN summary: typed access result envelope."""

    items: tuple[T, ...]
    result_identity: ResultIdentity
    source_revision: AccessSourceRevision
    provenance: AccessProvenance
    completeness: ResultCompleteness
    snapshot_identity: SnapshotIdentity | None = None
    page: AccessResultPage = AccessResultPage()

    @property
    def next_cursor(self) -> PaginationCursor | None:
        """Вернуть cursor. EN summary: expose next pagination cursor."""
        return self.page.next_cursor

    @property
    def errors(self) -> tuple[AccessError, ...]:
        """Вернуть ошибки. EN summary: expose explicit result errors."""
        return self.page.errors

    @property
    def unavailable_partitions(self) -> tuple[str, ...]:
        """Вернуть недоступные части. EN summary: expose unavailable partitions."""
        return self.page.unavailable_partitions

    def __post_init__(self) -> None:
        if self.completeness == ResultCompleteness.COMPLETE:
            if self.errors or self.unavailable_partitions:
                raise ValueError("COMPLETE result не может содержать ошибки или недоступные partitions")
        elif self.completeness == ResultCompleteness.PARTIAL:
            if not self.errors and not self.unavailable_partitions:
                raise ValueError("PARTIAL result должен явно объяснять неполноту")
        elif self.completeness == ResultCompleteness.FAILED:
            if not self.errors:
                raise ValueError("FAILED result должен содержать explicit error")
            if self.items:
                raise ValueError("FAILED result не должен маскировать items как полезный результат")
