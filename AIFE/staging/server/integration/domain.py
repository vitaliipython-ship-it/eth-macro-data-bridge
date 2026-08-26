"""Нейтральный вход доменного артефакта в Server/Data.

Server принимает только уже принятые доменом identity/evidence references и не
переопределяет доменную нормализацию, finality, provider rules или payload semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from server._validation import require_aware, require_non_empty


@dataclass(frozen=True, slots=True)
class DomainArtifactIdentity:
    """Opaque domain-owned artifact identity. EN summary: domain-owned artifact identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", require_non_empty(self.value, "domain_artifact_identity")
        )


@dataclass(frozen=True, slots=True)
class DomainArtifactType:
    """Opaque domain artifact class. EN summary: domain-owned artifact type."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", require_non_empty(self.value, "domain_artifact_type")
        )


@dataclass(frozen=True, slots=True)
class DomainArtifactReferences:
    """Opaque domain references. EN summary: payload, provenance and acceptance references."""

    payload: str
    provenance: str
    acceptance_evidence: str

    def __post_init__(self) -> None:
        for field_name in ("payload", "provenance", "acceptance_evidence"):
            object.__setattr__(
                self,
                field_name,
                require_non_empty(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class DomainArtifactTiming:
    """Authoritative domain timestamps. EN summary: validated/produced/observed timing."""

    validated_at: datetime
    produced_at: datetime
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_aware(self.validated_at, "validated_at")
        require_aware(self.produced_at, "produced_at")
        if self.observed_at is not None:
            require_aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class DomainArtifactEnvelope:
    """Минимальный neutral envelope уже принятого доменного артефакта."""

    artifact_identity: DomainArtifactIdentity
    artifact_type: DomainArtifactType
    source_revision: str
    content_identity: str
    references: DomainArtifactReferences
    timing: DomainArtifactTiming

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_revision",
            require_non_empty(self.source_revision, "source_revision"),
        )
        object.__setattr__(
            self,
            "content_identity",
            require_non_empty(self.content_identity, "content_identity"),
        )

    @property
    def payload_reference(self) -> str:
        """Вернуть opaque payload ref. EN summary: expose domain-owned payload reference."""
        return self.references.payload

    @property
    def provenance_reference(self) -> str:
        """Вернуть provenance ref. EN summary: expose domain-owned provenance reference."""
        return self.references.provenance

    @property
    def acceptance_evidence_reference(self) -> str:
        """Вернуть acceptance evidence. EN summary: expose domain acceptance evidence reference."""
        return self.references.acceptance_evidence

    @property
    def validated_at(self) -> datetime:
        """Вернуть validation time. EN summary: expose authoritative validated time."""
        return self.timing.validated_at

    @property
    def produced_at(self) -> datetime:
        """Вернуть produced time. EN summary: expose authoritative produced time."""
        return self.timing.produced_at

    @property
    def observed_at(self) -> datetime | None:
        """Вернуть observed time. EN summary: expose optional authoritative observation time."""
        return self.timing.observed_at
