"""Neutral accepted-domain envelope; F5 adds only exact registered-generation binding.

[Purpose]
    Поддержать bounded F5/C-144 generic Server contract этого owner layer.
[Description]
    Модуль сохраняет typed boundary без второго scheduler/repository/semantic resolver.
[Components]
    - Typed models/services/ports текущего bounded Server contour.
[Usage]
    Использовать через existing application/runtime composition и explicit interfaces.
[Architecture]
    AIFE владеет generic execution/storage mechanics; Data Bridge владеет market-data semantics.
[Note]
    Модуль не активирует Docker, F5M, production или real canonical AIFE integration.
[Warning]
    Не переносить provider/domain semantics в execution state, storage locator или Work identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from server._validation import require_aware, require_non_empty
from server.access.models import ExactGenerationRequest


@dataclass(frozen=True, slots=True)
class DomainArtifactIdentity:
    """F5 contract-bound class `DomainArtifactIdentity`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "domain_artifact_identity"))


@dataclass(frozen=True, slots=True)
class DomainArtifactType:
    """F5 contract-bound class `DomainArtifactType`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "domain_artifact_type"))


@dataclass(frozen=True, slots=True)
class DomainArtifactReferences:
    """F5 contract-bound class `DomainArtifactReferences`. EN summary: bounded F5 class."""

    payload: str
    provenance: str
    acceptance_evidence: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        for n in ("payload", "provenance", "acceptance_evidence"):
            object.__setattr__(self, n, require_non_empty(getattr(self, n), n))


@dataclass(frozen=True, slots=True)
class DomainArtifactTiming:
    """F5 contract-bound class `DomainArtifactTiming`. EN summary: bounded F5 class."""

    validated_at: datetime
    produced_at: datetime
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        require_aware(self.validated_at, "validated_at")
        require_aware(self.produced_at, "produced_at")
        if self.observed_at is not None:
            require_aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class DomainArtifactEnvelope:
    """F5 contract-bound class `DomainArtifactEnvelope`. EN summary: bounded F5 class."""

    artifact_identity: DomainArtifactIdentity
    artifact_type: DomainArtifactType
    source_revision: str
    content_identity: str
    references: DomainArtifactReferences
    timing: DomainArtifactTiming

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
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
        """F5 contract-bound function `payload_reference`. EN summary: bounded F5 function."""
        return self.references.payload

    @property
    def provenance_reference(self) -> str:
        """F5 contract-bound function `provenance_reference`. EN summary: bounded F5 function."""
        return self.references.provenance

    @property
    def acceptance_evidence_reference(self) -> str:
        """F5 contract-bound function `acceptance_evidence_reference`. EN summary: bounded F5 function."""
        return self.references.acceptance_evidence

    @property
    def validated_at(self) -> datetime:
        """F5 contract-bound function `validated_at`. EN summary: bounded F5 function."""
        return self.timing.validated_at

    @property
    def produced_at(self) -> datetime:
        """F5 contract-bound function `produced_at`. EN summary: bounded F5 function."""
        return self.timing.produced_at

    @property
    def observed_at(self) -> datetime | None:
        """F5 contract-bound function `observed_at`. EN summary: bounded F5 function."""
        return self.timing.observed_at


def exact_generation_request_for_domain(
    envelope: DomainArtifactEnvelope, generation_identity: str
) -> "ExactGenerationRequest":
    """Carry domain-owned identity into generic exact-generation resolution without inventing it."""

    return ExactGenerationRequest(
        generation_scope_identity=envelope.artifact_identity.value,
        generation_identity=require_non_empty(generation_identity, "generation_identity"),
        expected_source_revision=envelope.source_revision,
        expected_content_checksum=envelope.content_identity,
    )
