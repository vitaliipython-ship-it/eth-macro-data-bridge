from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STAGED_AIFE_ROOT = REPOSITORY_ROOT / "AIFE" / "staging"
if str(STAGED_AIFE_ROOT) not in sys.path:
    sys.path.insert(0, str(STAGED_AIFE_ROOT))

# isort: off
from aife_server_adapter import (
    AcceptedArtifactReferences,
    AcceptedArtifactTiming,
    DataBridgeAcceptedArtifact,
    DataBridgeAdapterError,
    adapt_accepted_artifact,
    adapt_d8_observation,
)
from canonical_json import sha256_canonical_json

# isort: on

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "aife_server_f4"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / f"{name}.json").read_text(encoding="utf-8"))


def _accepted_from_fixture(payload: dict[str, object]) -> DataBridgeAcceptedArtifact:
    return DataBridgeAcceptedArtifact(
        artifact_identity=str(payload["artifact_identity"]),
        artifact_type=str(payload["artifact_type"]),
        source_revision=str(payload["source_revision"]),
        content_identity=str(payload["content_identity"]),
        references=AcceptedArtifactReferences(
            payload=str(payload["payload_reference"]),
            provenance=str(payload["provenance_reference"]),
            acceptance_evidence=str(payload["acceptance_evidence_reference"]),
        ),
        timing=AcceptedArtifactTiming(
            validated_at=str(payload["validated_at"]),
            produced_at=str(payload["produced_at"]),
            observed_at=str(payload["observed_at"]),
        ),
    )


class AIFEServerAdapterTests(unittest.TestCase):
    """Repository-native F4 proof using actual Data Bridge metadata fixtures."""

    def _assert_real_repository_artifact(self, fixture_name: str) -> None:
        source = _fixture(fixture_name)
        envelope = adapt_accepted_artifact(_accepted_from_fixture(source))

        self.assertEqual(envelope.artifact_identity.value, source["artifact_identity"])
        self.assertEqual(envelope.artifact_type.value, source["artifact_type"])
        self.assertEqual(envelope.source_revision, source["source_revision"])
        self.assertEqual(envelope.content_identity, source["content_identity"])
        self.assertEqual(envelope.payload_reference, source["payload_reference"])
        self.assertEqual(envelope.provenance_reference, source["provenance_reference"])
        self.assertEqual(
            envelope.acceptance_evidence_reference,
            source["acceptance_evidence_reference"],
        )
        self.assertEqual(
            envelope.validated_at,
            datetime.fromisoformat(str(source["validated_at"]).replace("Z", "+00:00")),
        )
        self.assertEqual(
            envelope.produced_at,
            datetime.fromisoformat(str(source["produced_at"]).replace("Z", "+00:00")),
        )

        self.assertIn("domain_excerpt", source)
        for domain_field in (
            "domain_excerpt",
            "provider",
            "instrument",
            "finality",
            "value",
        ):
            self.assertFalse(hasattr(envelope, domain_field))

    def test_real_spot_history_metadata_crosses_neutral_boundary(self) -> None:
        self._assert_real_repository_artifact("spot-history")

    def test_real_derivatives_metadata_crosses_neutral_boundary(self) -> None:
        self._assert_real_repository_artifact("derivatives")

    def test_real_options_metadata_crosses_neutral_boundary(self) -> None:
        self._assert_real_repository_artifact("options")

    def test_real_liquidity_metadata_crosses_neutral_boundary(self) -> None:
        self._assert_real_repository_artifact("liquidity")

    def test_real_a2_publication_identity_and_replay_evidence(self) -> None:
        publication = _fixture("publication")

        self.assertEqual(
            publication["batch_id"],
            "pub-0e3a0d13c5ea7d46c50a13285a1c0372190123be620b92a7a2a062bf70ca5b42",
        )
        self.assertEqual(publication["member_count"], 20)
        self.assertEqual(publication["canonical_ack"], "PASS")
        self.assertIs(publication["partial_ack"], False)
        self.assertEqual(publication["remote_byte_preservation"], "PASS")
        self.assertEqual(publication["accepted_observation_id_set_match"], "PASS")
        self.assertEqual(publication["idempotent_replay_result"], "IDEMPOTENT_NOOP")

    def test_accepted_d8_observation_preserves_existing_domain_identity(self) -> None:
        observation: dict[str, object] = {
            "schema_version": "market-data-d8-runtime-observation/1.0.0",
            "observation_id": "obs-" + "1" * 64,
            "fingerprint": "2" * 64,
            "provider": "repository-owned-provider",
            "capability_id": "repository-owned-capability",
            "series_id": "repository-owned-series",
            "provider_timestamp_at": "2026-08-21T11:15:00.000Z",
            "retrieved_at": "2026-08-21T11:15:01.000Z",
            "known_at": "2026-08-21T11:15:02.000Z",
            "collected_at": "2026-08-21T11:15:03.000Z",
            "canonical_cycle_id": "d8c-repository-cycle",
            "canonical_slot": "2026-08-21T11:15:00.000Z",
            "finality": "REPOSITORY_OWNED_FINALITY_TOKEN",
            "validation_status": "PASS",
            "provenance": {
                "runtime_contract": "eth-macro-d8-runtime/1.0.0",
                "source_revision": "source-revision-a",
            },
            "d9_forward_seam": {"target": "REPOSITORY_OWNED_LIFECYCLE_TOKEN"},
            "value": {"already_normalized_by_domain": "opaque"},
        }

        envelope = adapt_d8_observation(observation)

        self.assertEqual(
            envelope.artifact_identity.value, observation["observation_id"]
        )
        self.assertEqual(envelope.artifact_type.value, observation["series_id"])
        self.assertEqual(envelope.source_revision, "source-revision-a")
        self.assertEqual(envelope.content_identity, sha256_canonical_json(observation))
        self.assertEqual(
            envelope.payload_reference,
            f"d8-observation:{observation['observation_id']}",
        )
        self.assertTrue(
            envelope.provenance_reference.endswith(str(observation["observation_id"]))
        )
        for domain_field in ("provider", "finality", "value"):
            self.assertFalse(hasattr(envelope, domain_field))

    def test_unaccepted_d8_observation_is_rejected_before_server_boundary(self) -> None:
        observation: dict[str, object] = {
            "validation_status": "FAIL",
            "provenance": {"source_revision": "source-revision-a"},
        }

        with self.assertRaisesRegex(DataBridgeAdapterError, "validation_status=PASS"):
            adapt_d8_observation(observation)


if __name__ == "__main__":
    unittest.main()
