"""Adversarial remote-integrity and semantic-gap qualification for canonical publication."""

from __future__ import annotations

import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from canonical_json import canonical_json_bytes
from github_history_publication import (
    CONTROL_PATH,
    RemoteSnapshotSemanticVerifier,
    materialize_data_resource,
    publication_control_entry,
)
from history_publication_batch import build_publication_batch
import publication_control_v2
from tests.deep_history.test_canonical_publication_port import ROOT, envelope


class PublicationRemoteIntegrityTests(unittest.TestCase):
    def test_control_plane_recomputes_publication_batch_from_remote_envelopes(self):
        envs = [envelope(minute=0), envelope(minute=5, close="1807")]
        batch = build_publication_batch(envs)
        resource_path, raw = materialize_data_resource(batch, envs)
        resource = json.loads(raw)

        # Simulate a remote/control-plane attacker or corruption that changes exact
        # envelope content while also updating the outer resource sha/size. The
        # copied logical batch hashes are intentionally left untouched. A validator
        # that only compares manifest fields would accept this; canonical validation
        # must rebuild the existing PublicationBatch from the exact remote envelopes.
        resource["observations"][0]["value"]["close"] = "9999"
        tampered = canonical_json_bytes(resource) + b"\n"

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / resource_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tampered)
            entry = publication_control_entry(
                batch,
                envs,
                data_commit_sha="a" * 40,
                resource_path=resource_path,
                resource_bytes=tampered,
            )
            with self.assertRaisesRegex(
                publication_control_v2.PublicationControlError,
                "PublicationBatch|payload|logical",
            ):
                publication_control_v2._validate_publication(root, entry)

    def test_noncontiguous_fixed_grid_batch_proves_each_member_without_synthetic_fill(self):
        envs = [envelope(minute=0), envelope(minute=10, close="1809")]
        batch = build_publication_batch(envs)
        resource_path, raw = materialize_data_resource(batch, envs)
        entry = publication_control_entry(
            batch,
            envs,
            data_commit_sha="a" * 40,
            resource_path=resource_path,
            resource_bytes=raw,
        )
        manifest = {
            "schema_version": "market-data-d8-origin-publication-manifest/1.0.0",
            "backend_profile": "GITHUB_FIRST_V1",
            "representation": "EXACT_D8_ENVELOPE",
            "publications": [entry],
        }

        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            shutil.copytree(
                ROOT,
                fixture,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            target = fixture / resource_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            control = fixture / CONTROL_PATH
            control.parent.mkdir(parents=True, exist_ok=True)
            control.write_bytes(canonical_json_bytes(manifest) + b"\n")
            archive_bytes = io.BytesIO()
            with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
                archive.add(fixture, arcname="snapshot")

        class ArchiveTransport:
            def download_archive(self, ref):
                return archive_bytes.getvalue()

        proof = RemoteSnapshotSemanticVerifier(ArchiveTransport()).verify("a" * 40, envs)
        self.assertEqual(proof["status"], "PASS")
        self.assertEqual(len(proof["proofs"]), 1)
        self.assertEqual(len(proof["proofs"][0]["receipts"]), 2)
        self.assertEqual(len(proof["proofs"][0]["plan_sha256s"]), 2)


if __name__ == "__main__":
    unittest.main()
