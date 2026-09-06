"""Generic F5C C1 acquisition orchestration without durable acceptance.

The service owns only generic adapter invocation and protocol-level result
checks. Storage, Work acceptance, publication, attempts and ACK semantics are
explicitly outside C1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .ports import AcquiredArtifact, AcquisitionAdapter


class AcquisitionResultInvariantError(ValueError):
    """Raised when an adapter result violates the generic C1 boundary contract."""


@dataclass(frozen=True, slots=True)
class GenericAcquisitionService:
    """Invoke one injected adapter and return one validated neutral artifact result."""

    adapter: AcquisitionAdapter

    async def acquire(self) -> AcquiredArtifact:
        """Acquire and validate envelope/payload identity without persisting it."""
        result = await self.adapter.acquire()
        if not isinstance(result, AcquiredArtifact):
            raise AcquisitionResultInvariantError("adapter must return AcquiredArtifact")
        digest = hashlib.sha256(result.payload).hexdigest()
        if digest != result.envelope.content_identity:
            raise AcquisitionResultInvariantError(
                "payload digest does not match envelope content_identity"
            )
        return result
