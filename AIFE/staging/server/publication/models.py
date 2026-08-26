"""Модель публикации по `CONTRACT-SERVER-PUBLICATION-001`.

ACK является отдельным проверяемым шлюзом и не приравнивается к physical write.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from server._validation import require_non_empty


@dataclass(frozen=True, slots=True)
class PublicationId:
    """Стабильная идентичность публикации. EN summary: stable publication identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "publication_id"))


@dataclass(frozen=True, slots=True)
class StoredObjectIdentity:
    """Идентичность сохранённого объекта. EN summary: durable stored object identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "stored_object_identity"))


@dataclass(frozen=True, slots=True)
class SourceRevision:
    """Ревизия исходных данных. EN summary: source revision identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_non_empty(self.value, "source_revision"))


class PublicationState(StrEnum):
    """Состояние публикации. EN summary: durable publication lifecycle state."""

    VALIDATED_DOMAIN_INPUT = "VALIDATED_DOMAIN_INPUT"
    INGEST_DURABLE = "INGEST_DURABLE"
    STAGED = "STAGED"
    PUBLISHING = "PUBLISHING"
    DURABLE_STORED = "DURABLE_STORED"
    INDEPENDENT_READBACK_VERIFIED = "INDEPENDENT_READBACK_VERIFIED"
    CANONICALLY_REGISTERED = "CANONICALLY_REGISTERED"
    ACKED = "ACKED"


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    """Неизменяемая запись публикации. EN summary: immutable publication record."""

    publication_id: PublicationId
    source_revision: SourceRevision
    state: PublicationState = PublicationState.VALIDATED_DOMAIN_INPUT
    stored_object_identity: StoredObjectIdentity | None = None


@dataclass(frozen=True, slots=True)
class AckEvidence:
    """Четыре условия ACK. EN summary: explicit ACK conjunction evidence."""

    durable_stored: bool
    independent_readback_verified: bool
    canonically_registered: bool
    identity_match: bool

    @property
    def complete(self) -> bool:
        """Проверить conjunction. EN summary: test whether all ACK conditions hold."""
        return (
            self.durable_stored
            and self.independent_readback_verified
            and self.canonically_registered
            and self.identity_match
        )


class InvalidPublicationTransition(ValueError):
    """Ошибка порядка публикации. EN summary: invalid publication transition error."""


class PublicationAckError(RuntimeError):
    """Ошибка ACK-шлюза. EN summary: publication acknowledgement gate error."""


_SEQUENCE = (
    PublicationState.VALIDATED_DOMAIN_INPUT,
    PublicationState.INGEST_DURABLE,
    PublicationState.STAGED,
    PublicationState.PUBLISHING,
    PublicationState.DURABLE_STORED,
    PublicationState.INDEPENDENT_READBACK_VERIFIED,
    PublicationState.CANONICALLY_REGISTERED,
)
_NEXT = dict(zip(_SEQUENCE, _SEQUENCE[1:]))


def transition_publication(
    record: PublicationRecord,
    target: PublicationState,
    *,
    stored_object_identity: StoredObjectIdentity | None = None,
) -> PublicationRecord:
    """Продвинуть публикацию на один шаг. EN summary: advance publication by one validated state."""
    expected = _NEXT.get(record.state)
    if target != expected:
        raise InvalidPublicationTransition(f"переход {record.state} -> {target} запрещён")
    next_identity = stored_object_identity or record.stored_object_identity
    if target == PublicationState.DURABLE_STORED and next_identity is None:
        raise InvalidPublicationTransition("DURABLE_STORED требует stored_object_identity")
    return replace(record, state=target, stored_object_identity=next_identity)


def acknowledge(record: PublicationRecord, evidence: AckEvidence) -> PublicationRecord:
    """Разрешить ACK только при полном conjunction. EN summary: acknowledge only with all four proofs."""
    if record.state != PublicationState.CANONICALLY_REGISTERED:
        raise PublicationAckError("ACK допустим только после CANONICALLY_REGISTERED")
    if record.stored_object_identity is None:
        raise PublicationAckError("ACK требует stored object identity")
    if not evidence.complete:
        raise PublicationAckError("ACK требует durable+readback+registration+identity_match")
    return replace(record, state=PublicationState.ACKED)
