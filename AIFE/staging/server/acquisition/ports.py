"""Provider-neutral acquisition port for the bounded F5C C1 Server boundary.

C1 carries a domain-produced neutral envelope together with the exact accepted
payload bytes. It intentionally does not persist, publish, schedule or mark
those bytes durable; those semantics begin at later F5C checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from server.integration.domain import DomainArtifactEnvelope


@dataclass(frozen=True, slots=True)
class AcquiredArtifact:
    """Neutral adapter result containing an accepted envelope and exact bytes."""

    envelope: DomainArtifactEnvelope
    payload: bytes

    def __post_init__(self) -> None:
        """Reject mutable or non-byte payload representations at the C1 boundary."""
        if not isinstance(self.payload, bytes):
            raise TypeError("payload must be exact bytes")


class AcquisitionAdapter(Protocol):
    """Provider-neutral adapter contract consumed by the generic Server boundary."""

    async def acquire(self) -> AcquiredArtifact:
        """Acquire one domain-accepted artifact without generic-core provider branching."""
        raise NotImplementedError
