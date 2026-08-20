from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from canonical_json import canonical_json_bytes
from history_publication_batch import build_publication_batch, validate_publication_batch

ACK_SCHEMA = "market-data-canonical-publication-ack/1.0.0"
PORT_EVIDENCE_SCHEMA = "market-data-history-publication-evidence/1.0.0"
GITHUB_FIRST_V1 = "GITHUB_FIRST_V1"
ACK_GATES = (
    "REMOTE_DURABILITY",
    "REMOTE_READBACK",
    "EXACT_BATCH_MEMBERSHIP",
    "EXACT_PAYLOAD_BINDING",
    "INTEGRITY_BINDING",
    "CONTROL_PLANE_VISIBILITY",
    "RESOLVER_VISIBILITY",
    "READER_MATERIALIZATION",
)


class PublicationPortError(RuntimeError):
    """Fail-closed canonical history publication violation."""


class HistoryPublicationBackend(Protocol):
    """Minimal backend boundary; this is deliberately not a plugin framework."""

    profile: str

    def publish_canonical(
        self,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        *,
        expected_remote_base: str,
        failpoint: Any | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class BoundedPublicationBatchPolicy:
    """Bound one publication attempt without coupling acquisition and publication cadence."""

    max_observations: int = 500
    max_serialized_bytes: int = 4 * 1024 * 1024
    max_oldest_age_seconds: int = 300
    spool_pressure_count: int = 1000

    def __post_init__(self) -> None:
        if min(
            self.max_observations,
            self.max_serialized_bytes,
            self.max_oldest_age_seconds,
            self.spool_pressure_count,
        ) <= 0:
            raise ValueError("publication batch policy limits must be positive")

    def select(
        self,
        pending: list[dict[str, Any]],
        *,
        now_ms: int,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        if not pending:
            return []
        ordered = sorted(pending, key=lambda item: (int(item["created_at"]), item["observation_id"]))
        encoded_sizes = [len(canonical_json_bytes(item["envelope"])) for item in ordered]
        if encoded_sizes[0] > self.max_serialized_bytes:
            raise PublicationPortError("single D8 observation exceeds publication byte bound")
        oldest_age_ms = max(0, now_ms - int(ordered[0]["created_at"]))
        due = (
            force
            or len(ordered) >= self.max_observations
            or len(ordered) >= self.spool_pressure_count
            or oldest_age_ms >= self.max_oldest_age_seconds * 1000
            or sum(encoded_sizes) >= self.max_serialized_bytes
        )
        if not due:
            return []
        selected: list[dict[str, Any]] = []
        used = 0
        for item, size in zip(ordered, encoded_sizes):
            if len(selected) >= self.max_observations or used + size > self.max_serialized_bytes:
                break
            selected.append(item)
            used += size
        if not selected:
            raise PublicationPortError("bounded publication policy selected no observations")
        return selected


def build_batch_from_pending(pending: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    envelopes = [item["envelope"] for item in pending]
    return build_publication_batch(envelopes), envelopes


def validate_batch_envelopes(batch: dict[str, Any], envelopes: list[dict[str, Any]]) -> None:
    """Bind caller-supplied exact D8 envelopes to the canonical logical PublicationBatch."""
    validate_publication_batch(batch)
    rebuilt = build_publication_batch(envelopes)
    if rebuilt != batch:
        raise PublicationPortError("PublicationBatch does not exactly bind supplied D8 envelopes")
    ids = [member["observation_id"] for member in batch["members"]]
    envelope_ids = [envelope.get("observation_id") for envelope in envelopes]
    if len(envelope_ids) != len(set(envelope_ids)) or set(envelope_ids) != set(ids):
        raise PublicationPortError("PublicationBatch envelope membership mismatch")


def canonical_publication_ack(batch: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Create ACK only when every remote/control/resolver/reader gate is PASS."""
    if evidence.get("schema_version") != PORT_EVIDENCE_SCHEMA:
        raise PublicationPortError("publication evidence schema mismatch")
    if evidence.get("batch_id") != batch["batch_id"]:
        raise PublicationPortError("publication evidence batch identity mismatch")
    if evidence.get("partial_ack") is not False:
        raise PublicationPortError("partial publication ACK is forbidden")
    gates = evidence.get("gates")
    if not isinstance(gates, dict) or any(gates.get(name) != "PASS" for name in ACK_GATES):
        raise PublicationPortError("canonical publication ACK gates are incomplete")
    expected_ids = batch["member_observation_ids"]
    if evidence.get("accepted_observation_ids") != expected_ids:
        raise PublicationPortError("canonical publication ACK membership mismatch")
    if evidence.get("membership_sha256") != batch["membership_sha256"]:
        raise PublicationPortError("canonical publication membership hash mismatch")
    if evidence.get("payload_sha256") != batch["payload_sha256"]:
        raise PublicationPortError("canonical publication payload hash mismatch")
    attempt_id = evidence.get("publication_attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise PublicationPortError("publication attempt identity missing")
    return {
        "schema_version": ACK_SCHEMA,
        "ack_state": "PASS",
        "batch_id": batch["batch_id"],
        "publication_attempt_id": attempt_id,
        "backend_profile": evidence.get("backend_profile"),
        "accepted_observation_ids": list(expected_ids),
        "membership_sha256": batch["membership_sha256"],
        "payload_sha256": batch["payload_sha256"],
        "partial_ack": False,
        "gates": {name: "PASS" for name in ACK_GATES},
        "durability_evidence": evidence.get("durability_evidence"),
        "control_plane_visibility_evidence": evidence.get("control_plane_visibility_evidence"),
        "semantic_materialization_evidence": evidence.get("semantic_materialization_evidence"),
    }


class HistoryPublicationPort:
    """Canonical write port with one currently-qualified physical profile."""

    def __init__(self, backend: HistoryPublicationBackend, *, backend_profile: str = GITHUB_FIRST_V1):
        if backend_profile != GITHUB_FIRST_V1:
            raise PublicationPortError(f"unsupported history publication backend profile: {backend_profile}")
        if getattr(backend, "profile", None) != backend_profile:
            raise PublicationPortError("history publication backend/profile mismatch")
        self.backend = backend
        self.backend_profile = backend_profile

    def publish(
        self,
        batch: dict[str, Any],
        envelopes: list[dict[str, Any]],
        *,
        expected_remote_base: str,
        failpoint: Any | None = None,
    ) -> dict[str, Any]:
        if not isinstance(expected_remote_base, str) or len(expected_remote_base) != 40:
            raise PublicationPortError("expected remote base SHA is required for canonical publication")
        validate_batch_envelopes(batch, envelopes)
        evidence = self.backend.publish_canonical(
            batch,
            envelopes,
            expected_remote_base=expected_remote_base,
            failpoint=failpoint,
        )
        return canonical_publication_ack(batch, evidence)
