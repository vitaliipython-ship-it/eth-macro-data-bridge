"""Data Bridge-owned adapter into the generic AIFE Server/Data domain envelope.

This module is intentionally the only F4 source that knows Data Bridge observation
fields. It trusts Data Bridge validation/finality authority and does not ask Server
to reinterpret provider or market semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, cast

from canonical_json import sha256_canonical_json

from server.integration import (
    DomainArtifactEnvelope,
    DomainArtifactIdentity,
    DomainArtifactReferences,
    DomainArtifactTiming,
    DomainArtifactType,
)


class DataBridgeAdapterError(ValueError):
    """Accepted-artifact boundary is incomplete or not domain-accepted."""


@dataclass(frozen=True, slots=True)
class AcceptedArtifactReferences:
    """Data Bridge-owned references exported to the neutral Server boundary."""

    payload: str
    provenance: str
    acceptance_evidence: str


@dataclass(frozen=True, slots=True)
class AcceptedArtifactTiming:
    """Data Bridge-owned authoritative times exported without reinterpretation."""

    validated_at: str
    produced_at: str
    observed_at: str | None = None


@dataclass(frozen=True, slots=True)
class DataBridgeAcceptedArtifact:
    """Already accepted repository/domain artifact prepared by Data Bridge authority."""

    artifact_identity: str
    artifact_type: str
    source_revision: str
    content_identity: str
    references: AcceptedArtifactReferences
    timing: AcceptedArtifactTiming


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DataBridgeAdapterError("Data Bridge timestamp must be UTC RFC3339 with Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DataBridgeAdapterError("invalid Data Bridge UTC timestamp") from exc
    return parsed.astimezone(timezone.utc)


def adapt_accepted_artifact(
    artifact: DataBridgeAcceptedArtifact,
) -> DomainArtifactEnvelope:
    """Map already accepted Data Bridge metadata into the neutral Server envelope."""
    return DomainArtifactEnvelope(
        artifact_identity=DomainArtifactIdentity(artifact.artifact_identity),
        artifact_type=DomainArtifactType(artifact.artifact_type),
        source_revision=artifact.source_revision,
        content_identity=artifact.content_identity,
        references=DomainArtifactReferences(
            payload=artifact.references.payload,
            provenance=artifact.references.provenance,
            acceptance_evidence=artifact.references.acceptance_evidence,
        ),
        timing=DomainArtifactTiming(
            validated_at=_utc(artifact.timing.validated_at),
            produced_at=_utc(artifact.timing.produced_at),
            observed_at=(
                _utc(artifact.timing.observed_at)
                if artifact.timing.observed_at
                else None
            ),
        ),
    )


def adapt_d8_observation(observation: Mapping[str, object]) -> DomainArtifactEnvelope:
    """Adapt a Data Bridge-validated D8 observation without revalidating its semantics."""
    if observation.get("validation_status") != "PASS":
        raise DataBridgeAdapterError(
            "only Data Bridge validation_status=PASS input is accepted"
        )

    provenance = observation.get("provenance")
    if not isinstance(provenance, Mapping):
        raise DataBridgeAdapterError("Data Bridge observation provenance is missing")

    required = (
        "observation_id",
        "series_id",
        "capability_id",
        "canonical_cycle_id",
        "known_at",
        "collected_at",
    )
    missing = [
        name
        for name in required
        if not isinstance(observation.get(name), str) or not observation[name]
    ]
    if missing:
        raise DataBridgeAdapterError(
            f"accepted Data Bridge observation is missing fields: {missing}"
        )

    source_revision = provenance.get("source_revision")
    if not isinstance(source_revision, str) or not source_revision:
        raise DataBridgeAdapterError(
            "Data Bridge source_revision provenance is missing"
        )

    observation_id = cast(str, observation["observation_id"])
    series_id = cast(str, observation["series_id"])
    capability_id = cast(str, observation["capability_id"])
    cycle_id = cast(str, observation["canonical_cycle_id"])
    known_at = cast(str, observation["known_at"])
    collected_at = cast(str, observation["collected_at"])
    provider_timestamp = observation.get("provider_timestamp_at")
    if provider_timestamp is not None and not isinstance(provider_timestamp, str):
        raise DataBridgeAdapterError("provider_timestamp_at must be a string or null")

    content_identity = sha256_canonical_json(dict(observation))
    return adapt_accepted_artifact(
        DataBridgeAcceptedArtifact(
            artifact_identity=observation_id,
            artifact_type=series_id,
            source_revision=source_revision,
            content_identity=content_identity,
            references=AcceptedArtifactReferences(
                payload=f"d8-observation:{observation_id}",
                provenance=f"d8-cycle:{cycle_id}:{capability_id}:{observation_id}",
                acceptance_evidence=f"d8-checkpoint:{cycle_id}:{observation_id}",
            ),
            timing=AcceptedArtifactTiming(
                validated_at=collected_at,
                produced_at=collected_at,
                observed_at=cast(str | None, provider_timestamp) or known_at,
            ),
        )
    )
