from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical_json import canonical_json_bytes
from d8_d9_canonical_forwarder import CanonicalD8ToD9Forwarder
from github_history_publication import (
    CONTROL_PATH,
    GitHubCASConflict,
    GitHubFirstV1Adapter,
    GitHubPublicationError,
    materialize_data_resource,
    publication_control_entry,
)
from history_publication_batch import build_publication_batch
from history_publication_port import (
    BoundedPublicationBatchPolicy,
    HistoryPublicationPort,
    PORT_EVIDENCE_SCHEMA,
    PublicationPortError,
    canonical_publication_ack,
)
import publication_control_v2
import publication_reader_v2

ROOT = Path(__file__).resolve().parents[2]


def fingerprint(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def observation_id(provider, series_id, provider_timestamp_at, fp):
    raw = f"{provider}|{series_id}|{provider_timestamp_at or 'NONE'}|{fp}".encode()
    return "obs-" + hashlib.sha256(raw).hexdigest()


def envelope(*, series="spot.binance-spot.TESTUSDT.ohlcv.5m", minute=0, close="1805"):
    open_ms = 1787072400000 + minute * 60000
    provider_at = "2026-08-18T17:00:00.000Z" if minute == 0 else "2026-08-18T17:05:00.000Z"
    slot = provider_at
    value = {
        "open_time_ms": open_ms,
        "open": "1800",
        "high": "1810",
        "low": "1795",
        "close": close,
        "volume": "12.5",
        "closed": True,
    }
    fp = fingerprint(value)
    return {
        "schema_version": "market-data-d8-runtime-observation/1.0.0",
        "observation_id": observation_id("binance-spot", series, provider_at, fp),
        "fingerprint": fp,
        "provider": "binance-spot",
        "source_identity": "binance-spot",
        "capability_id": "binance-spot.m5",
        "series_id": series,
        "provider_timestamp_at": provider_at,
        "retrieved_at": provider_at,
        "known_at": provider_at,
        "collected_at": provider_at,
        "canonical_cycle_id": f"cycle-{minute}",
        "canonical_slot": slot,
        "finality": "FINALIZED",
        "freshness": {"status": "LIVE_USABLE", "age_seconds": 0, "target_cadence_seconds": 300},
        "validation_status": "PASS",
        "provenance": {
            "runtime_contract": "eth-macro-d8-runtime/1.0.0",
            "source_revision": "qualification-source",
            "provider_route": "test-only",
        },
        "d9_forward_seam": {
            "identity_preserved": True,
            "known_at_preserved": True,
            "finality_preserved": True,
            "collection_gap_compatible": True,
            "target": "FIXED_GRID",
        },
        "value": value,
    }


class PassingSemanticVerifier:
    def verify(self, control_commit, envelopes):
        return {"status": "PASS", "control_commit": control_commit, "observations": len(envelopes)}


class FailingSemanticVerifier:
    def verify(self, control_commit, envelopes):
        return {"status": "FAIL"}


class MemoryGitHub:
    repository = "vitaliipython-ship-it/eth-macro-data-bridge"
    branch = "qualification/canonical-publication-port"

    def __init__(self):
        self.head = "0" * 40
        self.snapshots = {self.head: {}}
        self.changed = {}
        self.counter = 1
        self.inject_generated_cas_once = False

    def read_head(self):
        return self.head

    def read_file(self, path, ref):
        value = self.snapshots.get(ref)
        if value is None:
            raise AssertionError(f"unknown fake ref {ref}")
        return value.get(path)

    def _advance(self, files):
        previous = self.head
        new = f"{self.counter:040x}"
        self.counter += 1
        snapshot = dict(self.snapshots[previous])
        snapshot.update(files)
        self.snapshots[new] = snapshot
        self.changed[(previous, new)] = sorted(files)
        self.head = new
        return new

    def commit_files(self, expected_head, files, message):
        if self.head != expected_head:
            raise GitHubCASConflict(expected_head, self.head)
        if self.inject_generated_cas_once:
            self.inject_generated_cas_once = False
            actual = self._advance({"data/qualification-refresh.json": b"{}\n"})
            raise GitHubCASConflict(expected_head, actual)
        return self._advance(files)

    def compare_paths(self, base, head):
        if base == head:
            return []
        if (base, head) in self.changed:
            return self.changed[(base, head)]
        base_files = self.snapshots[base]
        head_files = self.snapshots[head]
        return sorted(path for path in set(base_files) | set(head_files) if base_files.get(path) != head_files.get(path))

    def download_archive(self, ref):
        raise AssertionError("stub semantic verifier must avoid archive download")


class CanonicalPublicationPortTests(unittest.TestCase):
    def _publish(self, transport=None, verifier=None):
        transport = transport or MemoryGitHub()
        envs = [envelope(minute=0), envelope(minute=5, close="1807")]
        batch = build_publication_batch(envs)
        backend = GitHubFirstV1Adapter(transport, semantic_verifier=verifier or PassingSemanticVerifier())
        port = HistoryPublicationPort(backend)
        ack = port.publish(batch, envs, expected_remote_base="0" * 40)
        return transport, envs, batch, ack

    def test_publication_port_ack_requires_all_remote_semantic_gates(self):
        transport, envs, batch, ack = self._publish()
        self.assertEqual(ack["ack_state"], "PASS")
        self.assertFalse(ack["partial_ack"])
        self.assertEqual(ack["accepted_observation_ids"], batch["member_observation_ids"])
        self.assertIsNotNone(transport.read_file(CONTROL_PATH, transport.head))
        self.assertTrue(all(value == "PASS" for value in ack["gates"].values()))

    def test_crash_after_remote_before_control_leaves_durable_data_and_retry_is_exact(self):
        transport = MemoryGitHub()
        envs = [envelope(minute=0)]
        batch = build_publication_batch(envs)
        port = HistoryPublicationPort(GitHubFirstV1Adapter(transport, semantic_verifier=PassingSemanticVerifier()))

        def failpoint(point):
            if point == "after_remote_data_before_control":
                raise RuntimeError(point)

        with self.assertRaisesRegex(RuntimeError, "after_remote_data_before_control"):
            port.publish(batch, envs, expected_remote_base="0" * 40, failpoint=failpoint)
        path, raw = materialize_data_resource(batch, envs)
        self.assertEqual(transport.read_file(path, transport.head), raw)
        self.assertIsNone(transport.read_file(CONTROL_PATH, transport.head))

        ack = port.publish(batch, envs, expected_remote_base="0" * 40)
        self.assertEqual(ack["ack_state"], "PASS")
        self.assertTrue(ack["durability_evidence"]["already_present_retry"])

    def test_fully_published_retry_is_idempotent(self):
        transport, envs, batch, first = self._publish()
        head = transport.head
        backend = GitHubFirstV1Adapter(transport, semantic_verifier=PassingSemanticVerifier())
        second = HistoryPublicationPort(backend).publish(batch, envs, expected_remote_base="0" * 40)
        self.assertEqual(second["ack_state"], "PASS")
        self.assertEqual(transport.head, head)
        self.assertEqual(second["accepted_observation_ids"], first["accepted_observation_ids"])

    def test_same_batch_id_conflicting_remote_resource_fails_closed_without_overwrite(self):
        transport = MemoryGitHub()
        envs = [envelope(minute=0)]
        batch = build_publication_batch(envs)
        path, raw = materialize_data_resource(batch, envs)
        transport._advance({path: raw + b"conflict"})
        head = transport.head
        port = HistoryPublicationPort(GitHubFirstV1Adapter(transport, semantic_verifier=PassingSemanticVerifier()))
        with self.assertRaises(GitHubPublicationError):
            port.publish(batch, envs, expected_remote_base="0" * 40)
        self.assertEqual(transport.head, head)
        self.assertEqual(transport.read_file(path, head), raw + b"conflict")

    def test_generated_remote_advance_retries_with_cas_and_never_forces(self):
        transport = MemoryGitHub()
        transport.inject_generated_cas_once = True
        _, _, _, ack = self._publish(transport=transport)
        self.assertEqual(ack["ack_state"], "PASS")
        self.assertIsNotNone(transport.read_file("data/qualification-refresh.json", transport.head))

    def test_control_visibility_without_reader_materialization_cannot_ack(self):
        transport = MemoryGitHub()
        envs = [envelope(minute=0)]
        batch = build_publication_batch(envs)
        port = HistoryPublicationPort(GitHubFirstV1Adapter(transport, semantic_verifier=FailingSemanticVerifier()))
        with self.assertRaises(GitHubPublicationError):
            port.publish(batch, envs, expected_remote_base="0" * 40)
        self.assertIsNotNone(transport.read_file(CONTROL_PATH, transport.head))

    def test_partial_ack_is_rejected(self):
        envs = [envelope(minute=0), envelope(minute=5)]
        batch = build_publication_batch(envs)
        evidence = {
            "schema_version": PORT_EVIDENCE_SCHEMA,
            "batch_id": batch["batch_id"],
            "publication_attempt_id": "attempt",
            "backend_profile": "GITHUB_FIRST_V1",
            "accepted_observation_ids": batch["member_observation_ids"][:1],
            "membership_sha256": batch["membership_sha256"],
            "payload_sha256": batch["payload_sha256"],
            "partial_ack": False,
            "gates": {name: "PASS" for name in (
                "REMOTE_DURABILITY", "REMOTE_READBACK", "EXACT_BATCH_MEMBERSHIP", "EXACT_PAYLOAD_BINDING",
                "INTEGRITY_BINDING", "CONTROL_PLANE_VISIBILITY", "RESOLVER_VISIBILITY", "READER_MATERIALIZATION",
            )},
        }
        with self.assertRaises(PublicationPortError):
            canonical_publication_ack(batch, evidence)

    def test_bounded_batch_policy_uses_count_bytes_age_and_spool_pressure_without_identity_attempt_fields(self):
        envs = [envelope(minute=0), envelope(minute=5)]
        pending = [
            {"observation_id": row["observation_id"], "created_at": 1000 + index, "envelope": row}
            for index, row in enumerate(reversed(envs))
        ]
        policy = BoundedPublicationBatchPolicy(
            max_observations=1,
            max_serialized_bytes=100000,
            max_oldest_age_seconds=300,
            spool_pressure_count=10,
        )
        selected = policy.select(pending, now_ms=2000, force=True)
        self.assertEqual(len(selected), 1)
        batch = build_publication_batch([selected[0]["envelope"]])
        self.assertNotIn("backend_profile", batch)
        self.assertNotIn("publication_attempt_id", batch)

    def test_pending_to_forwarded_transition_occurs_only_after_canonical_ack(self):
        env = envelope(minute=0)
        pending = [{"observation_id": env["observation_id"], "created_at": 1, "envelope": env}]

        class FakeSource:
            def __init__(self):
                self.marked = []
            def _pending(self, limit):
                return pending
            def _mark_forwarded(self, ids, now_ms):
                self.marked.append(list(ids))

        class Backend:
            profile = "GITHUB_FIRST_V1"
            def __init__(self, pass_ack):
                self.pass_ack = pass_ack
            def publish_canonical(self, batch, envelopes, *, expected_remote_base, failpoint=None):
                if not self.pass_ack:
                    raise PublicationPortError("no canonical ack")
                return {
                    "schema_version": PORT_EVIDENCE_SCHEMA,
                    "batch_id": batch["batch_id"],
                    "publication_attempt_id": "attempt",
                    "backend_profile": self.profile,
                    "accepted_observation_ids": batch["member_observation_ids"],
                    "membership_sha256": batch["membership_sha256"],
                    "payload_sha256": batch["payload_sha256"],
                    "partial_ack": False,
                    "gates": {name: "PASS" for name in (
                        "REMOTE_DURABILITY", "REMOTE_READBACK", "EXACT_BATCH_MEMBERSHIP", "EXACT_PAYLOAD_BINDING",
                        "INTEGRITY_BINDING", "CONTROL_PLANE_VISIBILITY", "RESOLVER_VISIBILITY", "READER_MATERIALIZATION",
                    )},
                }

        failing_source = FakeSource()
        with mock.patch("d8_d9_canonical_forwarder.IntegrityBoundD8Source", return_value=failing_source):
            forwarder = CanonicalD8ToD9Forwarder(
                Path("unused"), HistoryPublicationPort(Backend(False)),
                batch_policy=BoundedPublicationBatchPolicy(max_observations=10, max_serialized_bytes=100000, max_oldest_age_seconds=1, spool_pressure_count=10),
            )
            with self.assertRaises(PublicationPortError):
                forwarder.forward_pending(expected_remote_base="0" * 40, now_ms=5000, force_batch=True)
        self.assertEqual(failing_source.marked, [])

        passing_source = FakeSource()
        with mock.patch("d8_d9_canonical_forwarder.IntegrityBoundD8Source", return_value=passing_source):
            forwarder = CanonicalD8ToD9Forwarder(
                Path("unused"), HistoryPublicationPort(Backend(True)),
                batch_policy=BoundedPublicationBatchPolicy(max_observations=10, max_serialized_bytes=100000, max_oldest_age_seconds=1, spool_pressure_count=10),
            )
            result = forwarder.forward_pending(expected_remote_base="0" * 40, now_ms=5000, force_batch=True)
        self.assertEqual(result["canonical_publication_ack"], "PASS")
        self.assertEqual(passing_source.marked, [[env["observation_id"]]])


class NewSeriesHorizontalE2ETests(unittest.TestCase):
    def test_test_only_new_series_uses_same_index_resolver_reader_and_receipt(self):
        envs = [envelope(minute=0), envelope(minute=5, close="1807")]
        batch = build_publication_batch(envs)
        path, raw = materialize_data_resource(batch, envs)
        entry = publication_control_entry(
            batch,
            envs,
            data_commit_sha="a" * 40,
            resource_path=path,
            resource_bytes=raw,
        )
        manifest = {
            "schema_version": "market-data-d8-origin-publication-manifest/1.0.0",
            "backend_profile": "GITHUB_FIRST_V1",
            "representation": "EXACT_D8_ENVELOPE",
            "publications": [entry],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            control = root / CONTROL_PATH
            control.parent.mkdir(parents=True, exist_ok=True)
            control.write_bytes(canonical_json_bytes(manifest) + b"\n")

            index = publication_control_v2.build_index_v2(root)
            series_id = envs[0]["series_id"]
            self.assertEqual(sum(row["series_id"] == series_id for row in index["series"]), 1)
            plan = publication_control_v2.resolve_capability_v2(
                series_id,
                "2026-08-18T17:00:00Z",
                "2026-08-18T17:10:00Z",
                qualification_mode=True,
                root=root,
            )
            self.assertTrue(plan["segments"])
            self.assertTrue(all(segment["residence_role"] == "WARM" for segment in plan["segments"]))
            self.assertTrue(all(segment["adapter_profile"] == "GITHUB_FIRST_V1" for segment in plan["segments"]))
            rows, diagnostics = publication_reader_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
            self.assertEqual([row["observation_id"] for row in rows], [env["observation_id"] for env in envs])
            self.assertEqual([row["known_at"] for row in rows], [env["known_at"] for env in envs])
            self.assertEqual([row["finality"] for row in rows], ["FINALIZED", "FINALIZED"])
            self.assertEqual([row["payload_fingerprint"] for row in rows], [env["fingerprint"] for env in envs])
            self.assertEqual([row["provenance"] for row in rows], [env["provenance"] for env in envs])
            self.assertEqual(diagnostics["status"], "PASS")
            self.assertEqual(diagnostics["receipt"]["series_id"], series_id)
            self.assertEqual(diagnostics["receipt"]["observation_count"], 2)


if __name__ == "__main__":
    unittest.main()
