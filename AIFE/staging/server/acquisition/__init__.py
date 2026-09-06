"""Public provider-neutral acquisition boundary for F5C C1."""

from .ports import AcquiredArtifact, AcquisitionAdapter
from .service import AcquisitionResultInvariantError, GenericAcquisitionService

__all__ = [
    "AcquiredArtifact",
    "AcquisitionAdapter",
    "AcquisitionResultInvariantError",
    "GenericAcquisitionService",
]
