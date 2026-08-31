"""Publication lifecycle and stable F5 publication/generation identities."""

from __future__ import annotations
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json
from server._validation import require_non_empty


def _digest(mapping: dict[str, object]) -> str:
    """F5 contract-bound function `_digest`. EN summary: bounded F5 function."""
    return sha256(json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PublicationId:
    """F5 contract-bound class `PublicationId`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "publication_id"))


@dataclass(frozen=True, slots=True)
class StoredObjectIdentity:
    """F5 contract-bound class `StoredObjectIdentity`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "stored_object_identity"))


@dataclass(frozen=True, slots=True)
class SourceRevision:
    """F5 contract-bound class `SourceRevision`. EN summary: bounded F5 class."""

    value: str

    def __post_init__(self) -> None:
        """F5 contract-bound function `__post_init__`. EN summary: bounded F5 function."""
        object.__setattr__(self, "value", require_non_empty(self.value, "source_revision"))


class PublicationState(StrEnum):
    """F5 contract-bound class `PublicationState`. EN summary: bounded F5 class."""

    VALIDATED_DOMAIN_INPUT = "VALIDATED_DOMAIN_INPUT"
    INGEST_DURABLE = "INGEST_DURABLE"
    STAGED = "STAGED"
    PUBLISHING = "PUBLISHING"
    DURABLE_STORED = "DURABLE_STORED"
    INDEPENDENT_READBACK_VERIFIED = "INDEPENDENT_READBACK_VERIFIED"
    CANONICALLY_REGISTERED = "CANONICALLY_REGISTERED"
    ACKED = "ACKED"
    FAILED = "FAILED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    """F5 contract-bound class `PublicationRecord`. EN summary: bounded F5 class."""

    publication_id: PublicationId
    source_revision: SourceRevision
    state: PublicationState = PublicationState.VALIDATED_DOMAIN_INPUT
    stored_object_identity: StoredObjectIdentity | None = None


@dataclass(frozen=True, slots=True)
class AckEvidence:
    """F5 contract-bound class `AckEvidence`. EN summary: bounded F5 class."""

    durable_stored: bool
    independent_readback_verified: bool
    canonically_registered: bool
    identity_match: bool
    current_fencing_authority: bool = True

    @property
    def complete(self) -> bool:
        """F5 contract-bound function `complete`. EN summary: bounded F5 function."""
        return (
            self.durable_stored
            and self.independent_readback_verified
            and self.canonically_registered
            and self.identity_match
            and self.current_fencing_authority
        )


class InvalidPublicationTransition(ValueError):
    """F5 contract-bound class `InvalidPublicationTransition`. EN summary: bounded F5 class."""


class PublicationAckError(RuntimeError):
    """F5 contract-bound class `PublicationAckError`. EN summary: bounded F5 class."""


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
    """F5 contract-bound function `transition_publication`. EN summary: bounded F5 function."""
    if target != _NEXT.get(record.state):
        raise InvalidPublicationTransition(f"переход {record.state} -> {target} запрещён")
    nxt = stored_object_identity or record.stored_object_identity
    if target == PublicationState.DURABLE_STORED and nxt is None:
        raise InvalidPublicationTransition("DURABLE_STORED requires identity")
    return replace(record, state=target, stored_object_identity=nxt)


def acknowledge(record: PublicationRecord, evidence: AckEvidence) -> PublicationRecord:
    """F5 contract-bound function `acknowledge`. EN summary: bounded F5 function."""
    if (
        record.state != PublicationState.CANONICALLY_REGISTERED
        or record.stored_object_identity is None
        or not evidence.complete
    ):
        raise PublicationAckError("ACK gate incomplete")
    return replace(record, state=PublicationState.ACKED)


def build_f5_publication_id(
    *,
    work_id: str,
    domain_artifact_identity: str,
    source_revision: str,
    content_identity: str,
) -> str:
    """F5 contract-bound function `build_f5_publication_id`. EN summary: bounded F5 function."""
    return "pub:f5:v1:" + _digest(
        {
            "CONTENT_IDENTITY": content_identity,
            "DOMAIN_ARTIFACT_IDENTITY": domain_artifact_identity,
            "SOURCE_REVISION": source_revision,
            "WORK_ID": work_id,
        }
    )


def build_f5_logical_target_identity(*, domain_artifact_identity: str, source_revision: str) -> str:
    """F5 contract-bound function `build_f5_logical_target_identity`. EN summary: bounded F5 function."""
    return "target:f5:v1:" + _digest(
        {
            "DOMAIN_ARTIFACT_IDENTITY": domain_artifact_identity,
            "SOURCE_REVISION": source_revision,
        }
    )


def build_f5_generation_identity(*, domain_artifact_identity: str, source_revision: str, content_identity: str) -> str:
    """F5 contract-bound function `build_f5_generation_identity`. EN summary: bounded F5 function."""
    return "gen:f5:v1:" + _digest(
        {
            "CONTENT_IDENTITY": content_identity,
            "DOMAIN_ARTIFACT_IDENTITY": domain_artifact_identity,
            "SOURCE_REVISION": source_revision,
        }
    )
