"""Typed generic access boundary plus exact F5 generation lookup semantics."""

from __future__ import annotations

# Exact access mirrors persisted generation fields without importing the persistence owner.
# pylint: disable=duplicate-code

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, Protocol, TypeAlias, TypeVar

from server._validation import require_non_empty

Scalar: TypeAlias = str | int | float | bool | None
T = TypeVar("T")


class FilterOperator(StrEnum):
    """Bounded F5 class `FilterOperator` preserving the frozen contract."""

    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"


@dataclass(frozen=True, slots=True)
class QueryFilter:
    """Bounded F5 class `QueryFilter` preserving the frozen contract."""

    field: str
    operator: FilterOperator
    value: Scalar

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "field", require_non_empty(self.field, "filter.field"))


@dataclass(frozen=True, slots=True)
class PaginationCursor:
    """Bounded F5 class `PaginationCursor` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "pagination_cursor"))


@dataclass(frozen=True, slots=True)
class SnapshotIdentity:
    """Bounded F5 class `SnapshotIdentity` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "snapshot_identity"))


@dataclass(frozen=True, slots=True)
class AccessRequest:
    """Bounded F5 class `AccessRequest` preserving the frozen contract."""

    filters: tuple[QueryFilter, ...] = ()
    cursor: PaginationCursor | None = None
    snapshot_identity: SnapshotIdentity | None = None


@dataclass(frozen=True, slots=True)
class ResultIdentity:
    """Bounded F5 class `ResultIdentity` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "result_identity"))


@dataclass(frozen=True, slots=True)
class AccessSourceRevision:
    """Bounded F5 class `AccessSourceRevision` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "source_revision"))


@dataclass(frozen=True, slots=True)
class AccessProvenance:
    """Bounded F5 class `AccessProvenance` preserving the frozen contract."""

    value: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "value", require_non_empty(self.value, "provenance"))


@dataclass(frozen=True, slots=True)
class AccessError:
    """Bounded F5 class `AccessError` preserving the frozen contract."""

    code: str
    message: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        object.__setattr__(self, "code", require_non_empty(self.code, "error.code"))
        object.__setattr__(self, "message", require_non_empty(self.message, "error.message"))


class ResultCompleteness(StrEnum):
    """Bounded F5 class `ResultCompleteness` preserving the frozen contract."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class AccessResultPage:
    """Bounded F5 class `AccessResultPage` preserving the frozen contract."""

    next_cursor: PaginationCursor | None = None
    errors: tuple[AccessError, ...] = ()
    unavailable_partitions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AccessResult(Generic[T]):
    """Bounded F5 class `AccessResult` preserving the frozen contract."""

    items: tuple[T, ...]
    result_identity: ResultIdentity
    source_revision: AccessSourceRevision
    provenance: AccessProvenance
    completeness: ResultCompleteness
    snapshot_identity: SnapshotIdentity | None = None
    page: AccessResultPage = AccessResultPage()

    @property
    def next_cursor(self) -> PaginationCursor | None:
        """Bounded F5 function `next_cursor` preserving the frozen contract."""
        return self.page.next_cursor

    @property
    def errors(self) -> tuple[AccessError, ...]:
        """Bounded F5 function `errors` preserving the frozen contract."""
        return self.page.errors

    @property
    def unavailable_partitions(self) -> tuple[str, ...]:
        """Bounded F5 function `unavailable_partitions` preserving the frozen contract."""
        return self.page.unavailable_partitions

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        if self.completeness == ResultCompleteness.COMPLETE and (self.errors or self.unavailable_partitions):
            raise ValueError("COMPLETE result не может содержать ошибки или недоступные partitions")
        if self.completeness == ResultCompleteness.PARTIAL and not self.errors and not self.unavailable_partitions:
            raise ValueError("PARTIAL result должен явно объяснять неполноту")
        if self.completeness == ResultCompleteness.FAILED:
            if not self.errors:
                raise ValueError("FAILED result должен содержать explicit error")
            if self.items:
                raise ValueError("FAILED result не должен маскировать items как полезный результат")


@dataclass(frozen=True, slots=True)
class ExactGenerationRequest:
    """Exact registered generation lookup; never falls back to current."""

    generation_scope_identity: str
    generation_identity: str
    expected_source_revision: str
    expected_content_checksum: str

    def __post_init__(self) -> None:
        """Bounded F5 function `__post_init__` preserving the frozen contract."""
        for name in (
            "generation_scope_identity",
            "generation_identity",
            "expected_source_revision",
            "expected_content_checksum",
        ):
            object.__setattr__(self, name, require_non_empty(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class ExactGenerationResult:  # pylint: disable=too-many-instance-attributes
    """Bounded F5 class `ExactGenerationResult` preserving the frozen contract."""

    generation_scope_identity: str
    generation_identity: str
    generation_no: int
    publication_id: str
    source_revision: str
    content_checksum: str
    content_size: int
    physical_locator: str


class ExactGenerationNotFound(LookupError):
    """Bounded F5 class `ExactGenerationNotFound` preserving the frozen contract."""


class ExactGenerationIdentityMismatch(RuntimeError):
    """Bounded F5 class `ExactGenerationIdentityMismatch` preserving the frozen contract."""


class ExactGenerationRow(Protocol):  # pylint: disable=too-few-public-methods
    """Bounded F5 class `ExactGenerationRow` preserving the frozen contract."""

    generation_scope_identity: str
    generation_identity: str
    generation_no: int
    publication_id: str
    source_revision: str
    content_checksum: str
    content_size: int
    physical_locator: str


class ExactGenerationRepository(Protocol):
    """Bounded F5 class `ExactGenerationRepository` preserving the frozen contract."""

    def resolve_generation(self, scope: str, generation_identity: str | None = None) -> ExactGenerationRow | None:
        """Protocol operation `resolve_generation` for the frozen F5 boundary."""
        raise NotImplementedError


def resolve_exact_generation(
    repository: ExactGenerationRepository, request: ExactGenerationRequest
) -> ExactGenerationResult:
    """Resolve one exact generation and fail closed on absence or identity mismatch."""
    row = repository.resolve_generation(request.generation_scope_identity, request.generation_identity)
    if row is None:
        raise ExactGenerationNotFound(request.generation_identity)
    if row.generation_identity != request.generation_identity:
        raise ExactGenerationIdentityMismatch("generation identity mismatch")
    if row.source_revision != request.expected_source_revision:
        raise ExactGenerationIdentityMismatch("source revision mismatch")
    if row.content_checksum != request.expected_content_checksum:
        raise ExactGenerationIdentityMismatch("content checksum mismatch")
    return ExactGenerationResult(
        row.generation_scope_identity,
        row.generation_identity,
        row.generation_no,
        row.publication_id,
        row.source_revision,
        row.content_checksum,
        row.content_size,
        row.physical_locator,
    )
