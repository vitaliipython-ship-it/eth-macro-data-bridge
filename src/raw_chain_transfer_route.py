from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from raw_chain_transfer_core import (
    CAPABILITY_ID,
    ProviderPort,
    PublicationPort,
    RawTransferCollectionCore,
    serialize_physical_block_bundle,
)

ROUTE_RESULT_SCHEMA_VERSION = "raw-chain-transfer-physical-route-result/1.0.0"
REQUIRED_ACK_GATES = (
    "REMOTE_DURABILITY",
    "REMOTE_READBACK",
    "EXACT_PAYLOAD_BINDING",
    "INTEGRITY_BINDING",
    "CONTROL_PLANE_VISIBILITY",
    "RESOLVER_VISIBILITY",
    "READER_MATERIALIZATION",
)


class RawTransferRouteError(RuntimeError):
    """Fail-closed composition error outside raw-transfer domain semantics."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class RawTransferRouteResult:
    schema_version: str
    capability_id: str
    chain_id: str
    block_height: int
    block_hash: str
    content_identity: str
    observation_count: int
    zero_event_classification: str | None
    ack_state: str
    publication_resource_id: str | None
    provenance_authority: str
    provenance_evidence_id: str


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RawTransferRouteError(code)


def _validate_ack(
    ack: Mapping[str, Any],
    *,
    expected_content_identity: str,
    expected_provenance: Mapping[str, str],
    expected_size_bytes: int,
) -> None:
    _require(isinstance(ack, Mapping), "PUBLICATION_ACK_INVALID")
    _require(ack.get("ack_state") == "PASS", "PUBLICATION_ACK_NOT_PASS")
    _require(ack.get("partial_ack") is False, "PUBLICATION_ACK_PARTIAL")
    _require(ack.get("content_identity") == expected_content_identity, "PUBLICATION_ACK_CONTENT_IDENTITY_MISMATCH")

    if "provenance" in ack:
        _require(ack.get("provenance") == expected_provenance, "PUBLICATION_ACK_PROVENANCE_MISMATCH")

    gates = ack.get("gates")
    _require(isinstance(gates, Mapping), "PUBLICATION_ACK_GATES_MISSING")
    _require(all(gates.get(name) == "PASS" for name in REQUIRED_ACK_GATES), "PUBLICATION_ACK_GATE_FAILED")

    durability = ack.get("durability_evidence")
    _require(isinstance(durability, Mapping) and bool(durability), "PUBLICATION_ACK_DURABILITY_EVIDENCE_MISSING")
    if "sha256" in durability:
        _require(durability.get("sha256") == expected_content_identity, "PUBLICATION_ACK_DURABILITY_IDENTITY_MISMATCH")
    if "size_bytes" in durability:
        _require(durability.get("size_bytes") == expected_size_bytes, "PUBLICATION_ACK_DURABILITY_SIZE_MISMATCH")

    control = ack.get("control_plane_visibility_evidence")
    _require(isinstance(control, Mapping) and bool(control), "PUBLICATION_ACK_CONTROL_EVIDENCE_MISSING")
    semantic = ack.get("semantic_materialization_evidence")
    _require(isinstance(semantic, Mapping) and semantic.get("status") == "PASS", "PUBLICATION_ACK_SEMANTIC_EVIDENCE_INVALID")

    # The existing canonical raw-transfer publication ACK represents provenance
    # binding through INTEGRITY_BINDING after the port validates the exact
    # provenance argument against canonical bundle bytes. If a backend also
    # returns explicit provenance, it must match exactly (checked above).
    _require(gates.get("INTEGRITY_BINDING") == "PASS", "PUBLICATION_ACK_PROVENANCE_BINDING_MISSING")


class RawTransferPhysicalRoute:
    """Provider-neutral collect -> canonical bytes -> durable publication composition."""

    def __init__(self, provider: ProviderPort, publication: PublicationPort) -> None:
        self._core = RawTransferCollectionCore(provider)
        self._publication = publication

    def execute_block(
        self,
        chain_id: str,
        block_ref: str,
        *,
        observation_known_at: str,
        prior_canonical_block: Mapping[str, Any] | None = None,
    ) -> RawTransferRouteResult:
        bundle = self._core.collect_block(
            chain_id,
            block_ref,
            observation_known_at=observation_known_at,
            prior_canonical_block=prior_canonical_block,
        )
        bundle_bytes = serialize_physical_block_bundle(bundle)
        content_identity = hashlib.sha256(bundle_bytes).hexdigest()
        provenance = bundle.get("source_provenance")
        _require(isinstance(provenance, Mapping), "BUNDLE_PROVENANCE_MISSING")
        provenance = dict(provenance)
        _require(
            set(provenance) == {"authority", "evidence_id"}
            and all(isinstance(value, str) and value for value in provenance.values()),
            "BUNDLE_PROVENANCE_INVALID",
        )

        ack = self._publication.publish(bundle_bytes, content_identity, provenance)
        _validate_ack(
            ack,
            expected_content_identity=content_identity,
            expected_provenance=provenance,
            expected_size_bytes=len(bundle_bytes),
        )

        coverage = bundle["coverage"]
        observations = bundle["observations"]
        return RawTransferRouteResult(
            schema_version=ROUTE_RESULT_SCHEMA_VERSION,
            capability_id=CAPABILITY_ID,
            chain_id=bundle["chain_id"],
            block_height=bundle["block_height"],
            block_hash=bundle["block_hash"],
            content_identity=content_identity,
            observation_count=len(observations),
            zero_event_classification=coverage.get("zero_event_classification"),
            ack_state="PASS",
            publication_resource_id=ack.get("resource_id") if isinstance(ack.get("resource_id"), str) else None,
            provenance_authority=provenance["authority"],
            provenance_evidence_id=provenance["evidence_id"],
        )
