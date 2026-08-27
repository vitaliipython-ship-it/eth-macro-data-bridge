from __future__ import annotations

import copy
import io
import json
import subprocess
import tempfile
import unittest
import urllib.error
import zipfile
from email.message import Message
from pathlib import Path
from unittest import mock

import current_data_promotion as promotion

ROOT = Path(__file__).resolve().parents[2]
CURRENT_WORKFLOW = ROOT / ".github/workflows/current-data-request.yml"
UPDATE_WORKFLOW = ROOT / ".github/workflows/update-market.yml"
SEMANTICS = ROOT / "docs/semantics/fresh-current-agent-transport-v1.md"
AGENTS = ROOT / "AGENTS.md"
BRIDGE_CONTRACT = ROOT / "bridge-contract.json"


class _BytesResponse:
    def __init__(self, value: bytes):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.value


class CurrentDataPromotionTests(unittest.TestCase):
    timestamp_ms = 1787766300000
    generated_at = "2026-08-26T18:25:00Z"
    known_at = "2026-08-26T18:25:30Z"

    @classmethod
    def git(cls, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def generation(self, mode: str = "FRESH_ACQUISITION") -> dict[str, object]:
        generation: dict[str, object] = {
            "schema_version": "fresh-current-generation/1.0.0",
            "contract_id": promotion.CONTRACT_ID,
            "contract_version": promotion.CONTRACT_VERSION,
            "control_plane_head": self.git("rev-parse", "HEAD"),
            "control_plane_tree": self.git("rev-parse", "HEAD^{tree}"),
            "generation_id": "a" * 64,
            "generated_at_utc": self.generated_at,
            "known_at_utc": self.known_at,
            "request_sha256": "b" * 64,
            "generation_mode": mode,
        }
        generation["generation_manifest_sha256"] = promotion._sha256_json(generation)
        return generation

    def options_payload(self, marker: str = "base") -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "provider": "deribit",
            "timestamp_ms": self.timestamp_ms,
            "scope": "FULL_ACTIVE_CHAIN_COMPACT",
            "instrument_key": "ETH-{expiration_timestamp}-{strike}-{C|P}",
            "options": [[self.timestamp_ms + 86_400_000, "2500", "call", marker]],
            "selected_greeks": [],
        }

    def reconstructible_resource(self) -> dict[str, object]:
        return {
            "logical_resource_id": "series:spot.binance-spot.ETHUSDT.ohlcv.5m",
            "semantic_series_id_or_domain_identity": "spot.binance-spot.ETHUSDT.ohlcv.5m",
            "durability_class": "RECONSTRUCTIBLE",
            "durability_state": "RECONSTRUCTIBLE",
            "observation_identity": {
                "series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m",
                "latest_open_timestamp_ms": self.timestamp_ms,
                "latest_bars": 256,
                "semantic_output_sha256": "c" * 64,
            },
            "observation_time_utc": self.generated_at,
            "known_at_utc": self.known_at,
            "source_provider": "binance-spot",
            "source_semantics": "CANONICAL_SERIES_WINDOW_VIA_SEMANTIC_RECEIPT",
            "payload_member": None,
            "payload_sha256": None,
            "payload_size_bytes": 0,
            "existing_target_family": "DECLARED_PROVIDER_HISTORY",
            "promotion_policy_id": "RECONSTRUCTIBLE_PROVIDER_HISTORY_V1",
            "promotion_required": False,
            "validation_status": "PASS",
        }

    def ephemeral_resource(self) -> dict[str, object]:
        return {
            "logical_resource_id": "domain:ANALYTICS",
            "semantic_series_id_or_domain_identity": "ANALYTICS",
            "durability_class": "EPHEMERAL_ONLY",
            "durability_state": "EPHEMERAL_ONLY",
            "observation_identity": {"domain_id": "ANALYTICS", "generation_resource_sha256": "d" * 64},
            "observation_time_utc": self.generated_at,
            "known_at_utc": self.known_at,
            "source_provider": "MULTI_PROVIDER_OR_DERIVED",
            "source_semantics": "CURRENT_DOMAIN_MANIFEST_RESOURCE",
            "payload_member": None,
            "payload_sha256": None,
            "payload_size_bytes": 0,
            "existing_target_family": None,
            "promotion_policy_id": "NO_APPROVED_DURABLE_CURRENT_DOMAIN_SAMPLE_V1",
            "promotion_required": False,
            "validation_status": "PASS",
            "promotion_not_authorized_for_resource": True,
        }

    def eligible_resource(self, artifact_root: Path, marker: str = "base") -> dict[str, object]:
        family = "options.deribit-options.ETH.surface-snapshots"
        payload = self.options_payload(marker)
        raw = promotion._canonical_bytes(payload)
        member = f"promotion-payload/{family}.json"
        path = artifact_root / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        target = promotion._target_path(family, self.timestamp_ms).as_posix()
        return {
            "logical_resource_id": f"promotion-candidate:{family}:{self.timestamp_ms}",
            "semantic_series_id_or_domain_identity": family,
            "durability_class": "PROMOTION_ELIGIBLE",
            "durability_state": "PROMOTION_PENDING",
            "observation_identity": {
                "provider": "deribit-options",
                "series_or_capability": family,
                "timestamp_ms": self.timestamp_ms,
                "scope": "FULL_ACTIVE_CHAIN_COMPACT",
            },
            "observation_time_utc": self.generated_at,
            "known_at_utc": self.known_at,
            "source_provider": "deribit-options",
            "source_semantics": family,
            "payload_member": member,
            "payload_sha256": promotion._sha256_bytes(raw),
            "payload_size_bytes": len(raw),
            "existing_target_family": family,
            "promotion_policy_id": "EXISTING_FORWARD_OPTIONS_SURFACE_V1",
            "promotion_required": True,
            "validation_status": "PASS",
            "collection_run": {
                "run_id": f"deribit-options-surface:{self.timestamp_ms}",
                "expected_schedule_at": self.generated_at,
                "collection_started_at": self.generated_at,
                "collection_completed_at": self.known_at,
                "provider": "deribit-options",
                "series_or_capability": family,
                "status": "OBSERVED_STATE",
                "snapshot_ref": target,
                "error_class": None,
                "provider_timestamp_at": self.generated_at,
                "known_at": self.known_at,
                "retrieved_at": self.known_at,
                "freshness": {"status": "LIVE_USABLE", "age_seconds": 30, "target_cadence_seconds": 3600},
            },
            "collection_run_identity": f"deribit-options-surface:{self.timestamp_ms}",
            "generated_at_utc": self.generated_at,
        }

    def artifact(
        self,
        root: Path,
        resources: list[dict[str, object]],
        *,
        mode: str = "FRESH_ACQUISITION",
        transport_noise: dict[str, object] | None = None,
    ) -> dict[str, object]:
        generation = self.generation(mode)
        promotion._write_json(root / "current-generation.json", generation)
        handoff: dict[str, object] = {
            "schema_version": promotion.HANDOFF_SCHEMA,
            "contract_id": promotion.CONTRACT_ID,
            "contract_version": promotion.CONTRACT_VERSION,
            "authority": "TEMPORARY_TRANSFER_EVIDENCE",
            "promotion_handoff_is_market_data_authority": False,
            "actions_artifact_is_durable_history_authority": False,
            "canonical_durability_occurs_only_after_existing_durable_publication": True,
            "control_plane_head": generation["control_plane_head"],
            "control_plane_tree": generation["control_plane_tree"],
            "generation_id": generation["generation_id"],
            "generation_manifest_sha256": generation["generation_manifest_sha256"],
            "generated_at_utc": generation["generated_at_utc"],
            "known_at_utc": generation["known_at_utc"],
            "request_sha256": generation["request_sha256"],
            "generation_mode": generation["generation_mode"],
            "durability_classes": list(promotion.DURABILITY_CLASSES),
            "resources": resources,
            "promotion_required": any(row.get("promotion_required") is True for row in resources),
            "promotion_pending_count": sum(row.get("promotion_required") is True for row in resources),
            "reconstructible_payload_included": False,
            "per_request_remote_git_mutation": False,
            "per_request_git_commit": False,
            "per_request_git_push": False,
            "durable_publisher": ".github/workflows/update-market.yml",
            "publication_mode": "HOURLY_BATCHED",
        }
        if transport_noise:
            handoff.update(transport_noise)
        handoff["handoff_id"] = promotion._sha256_json(promotion._handoff_identity_basis(handoff))
        promotion._write_json(root / "promotion-handoff.json", handoff)
        return handoff

    def test_29_reconstructible_observation_has_no_promotion_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            handoff = self.artifact(root, [self.reconstructible_resource()])
            promotion.validate_artifact(root, source_control_root=ROOT)
            self.assertEqual(handoff["promotion_pending_count"], 0)
            self.assertFalse((root / "promotion-payload").exists())

    def test_30_promotion_eligible_snapshot_creates_bounded_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            eligible = self.eligible_resource(root)
            handoff = self.artifact(root, [eligible])
            promotion.validate_artifact(root, source_control_root=ROOT)
            self.assertEqual(handoff["promotion_pending_count"], 1)
            payloads = list((root / "promotion-payload").glob("*.json"))
            self.assertEqual(len(payloads), 1)
            self.assertNotIn("ohlcv", payloads[0].name.lower())

    def test_31_ephemeral_only_never_claims_durable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resource = self.ephemeral_resource()
            self.artifact(root, [resource])
            promotion.validate_artifact(root, source_control_root=ROOT)
            self.assertEqual(resource["durability_state"], "EPHEMERAL_ONLY")
            self.assertFalse(resource["promotion_required"])
            self.assertTrue(resource["promotion_not_authorized_for_resource"])

    def test_32_handoff_hash_generation_and_git_provenance_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.artifact(root, [self.eligible_resource(root)])
            handoff, generation = promotion.validate_artifact(root, source_control_root=ROOT)
            self.assertEqual(handoff["generation_manifest_sha256"], generation["generation_manifest_sha256"])
            self.assertEqual(handoff["control_plane_head"], self.git("rev-parse", "HEAD"))

    def test_33_transport_identifiers_are_excluded_from_semantic_handoff_identity(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            left_root, right_root = Path(left), Path(right)
            left_handoff = self.artifact(
                left_root,
                [self.reconstructible_resource()],
                transport_noise={"github_run_id": 111, "issue_number": 7, "artifact_url": "https://example.invalid/a"},
            )
            right_handoff = self.artifact(
                right_root,
                [self.reconstructible_resource()],
                transport_noise={"github_run_id": 999, "issue_number": 88, "artifact_url": "https://example.invalid/b"},
            )
            self.assertEqual(left_handoff["handoff_id"], right_handoff["handoff_id"])
            forged = json.loads((left_root / "promotion-handoff.json").read_text())
            forged["resources"][0]["observation_identity"]["filesystem_path"] = "/tmp/not-semantic"
            forged["handoff_id"] = promotion._sha256_json(promotion._handoff_identity_basis(forged))
            promotion._write_json(left_root / "promotion-handoff.json", forged)
            with self.assertRaisesRegex(promotion.PromotionError, "physical field forbidden"):
                promotion.validate_artifact(left_root)

    def test_34_same_handoff_second_apply_is_already_consumed(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            self.artifact(artifact_root, [self.eligible_resource(artifact_root)])
            first = promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            second = promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            self.assertEqual(first["status"], "PROMOTED")
            self.assertEqual(second["status"], "ALREADY_CONSUMED")
            self.assertFalse(second["changed"])

    def test_35_on_demand_plus_existing_same_observation_deduplicates(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            resource = self.eligible_resource(artifact_root)
            self.artifact(artifact_root, [resource])
            target = repo_root / promotion._target_path(str(resource["existing_target_family"]), self.timestamp_ms)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((artifact_root / str(resource["payload_member"])).read_bytes())
            result = promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            self.assertEqual(result["status"], "DEDUPLICATED")
            self.assertEqual(len(list(target.parent.glob(f"{self.timestamp_ms}.json"))), 1)

    def test_36_older_promotion_cannot_overwrite_newer_snapshot(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            resource = self.eligible_resource(artifact_root)
            self.artifact(artifact_root, [resource])
            newer_ms = self.timestamp_ms + 3_600_000
            family = str(resource["existing_target_family"])
            newer = repo_root / promotion._target_path(family, newer_ms)
            newer.parent.mkdir(parents=True, exist_ok=True)
            newer_bytes = promotion._canonical_bytes({"provider": "deribit", "timestamp_ms": newer_ms, "scope": "FULL_ACTIVE_CHAIN_COMPACT", "options": [["newer"]]})
            newer.write_bytes(newer_bytes)
            promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            self.assertEqual(newer.read_bytes(), newer_bytes)
            self.assertTrue((repo_root / promotion._target_path(family, self.timestamp_ms)).is_file())

    def test_37_same_identity_materially_different_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            resource = self.eligible_resource(artifact_root)
            self.artifact(artifact_root, [resource])
            target = repo_root / promotion._target_path(str(resource["existing_target_family"]), self.timestamp_ms)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(promotion._canonical_bytes(self.options_payload("conflict")))
            with self.assertRaises(promotion.PromotionError) as caught:
                promotion.apply_artifact(
                    artifact_root,
                    repository_root=repo_root,
                    source_control_root=ROOT,
                    processed_at_utc=self.known_at,
                )
            self.assertEqual(caught.exception.code, "IMMUTABLE_OBSERVATION_CONFLICT")

    def test_38_failed_publication_model_leaves_handoff_retryable(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as retry_temp:
            artifact_root = Path(artifact_temp)
            self.artifact(artifact_root, [self.eligible_resource(artifact_root)])
            first = promotion.apply_artifact(
                artifact_root,
                repository_root=Path(first_temp),
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            retry = promotion.apply_artifact(
                artifact_root,
                repository_root=Path(retry_temp),
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            self.assertEqual(first["status"], "PROMOTED")
            self.assertEqual(retry["status"], "PROMOTED")

    def test_39_consumption_ack_contract_is_after_successful_push_and_readback(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            self.artifact(artifact_root, [self.eligible_resource(artifact_root)])
            promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            ledger = json.loads((repo_root / promotion.PROMOTION_LEDGER_PATH).read_text())
            self.assertFalse(ledger["market_data_authority"])
            self.assertTrue(ledger["entry_effective_only_after_successful_durable_publication_readback"])
            workflow = UPDATE_WORKFLOW.read_text()
            self.assertIn("DURABLE_PUBLICATION_READBACK=PASS", workflow)
            self.assertIn("PROMOTION_CONSUMPTION_EFFECTIVE=", workflow)

    def test_40_artifact_retention_is_at_least_seven_days(self):
        workflow = CURRENT_WORKFLOW.read_text()
        values = []
        for line in workflow.splitlines():
            if "retention-days:" in line:
                values.append(int(line.split(":", 1)[1].strip()))
        self.assertTrue(values)
        self.assertTrue(all(value >= 7 for value in values))

    def test_41_malformed_or_forged_handoff_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resource = self.eligible_resource(root)
            self.artifact(root, [resource])
            payload = root / str(resource["payload_member"])
            payload.write_text('{"tampered":true}\n')
            with self.assertRaises(promotion.PromotionError) as caught:
                promotion.validate_artifact(root, source_control_root=ROOT)
            self.assertEqual(caught.exception.code, "PROMOTION_PAYLOAD_HASH_MISMATCH")

    def test_42_on_demand_has_no_git_publication_or_contents_write(self):
        workflow = CURRENT_WORKFLOW.read_text()
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("git add ", workflow)
        self.assertNotIn("git commit ", workflow)
        self.assertNotIn("git push", workflow)

    def test_43_hourly_has_at_most_one_batched_generated_commit(self):
        workflow = UPDATE_WORKFLOW.read_text()
        self.assertEqual(workflow.count("git commit -m"), 1)
        self.assertNotIn("PER_HANDOFF_COMMIT", workflow)
        self.assertNotIn("PER_PROMOTED_RESOURCE_COMMIT", workflow)

    def test_44_normal_hourly_collector_and_schedule_are_preserved(self):
        workflow = UPDATE_WORKFLOW.read_text()
        self.assertRegex(workflow, r'cron: "[0-5]?\d \* \* \* \*"')
        self.assertEqual(workflow.count("python src/collector.py"), 1)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("SCHEDULED_COLLECTION_COUNT=1", workflow)

    def test_45_current_agent_use_does_not_wait_for_promotion(self):
        agents = AGENTS.read_text()
        semantics = SEMANTICS.read_text()
        self.assertIn("CURRENT_ANALYSIS_DOES_NOT_WAIT_FOR_PROMOTION=YES", agents)
        self.assertIn("CURRENT_ANALYSIS_BEFORE_PROMOTION=ALLOWED", semantics)
        self.assertNotIn("wait for hourly promotion before live analysis", CURRENT_WORKFLOW.read_text().lower())

    def test_46_current_workflow_builds_and_validates_handoff_before_upload(self):
        workflow = CURRENT_WORKFLOW.read_text()
        build = workflow.index("build-handoff")
        validate = workflow.index("validate-artifact")
        upload = workflow.index("Upload validated ephemeral generation")
        self.assertLess(build, validate)
        self.assertLess(validate, upload)

    def test_47_candidate_path_filters_include_promotion_source_and_test(self):
        workflow = CURRENT_WORKFLOW.read_text()
        self.assertIn("tools/current_data_promotion.py", workflow)
        self.assertIn("tests/deep_history/test_current_data_promotion.py", workflow)
        self.assertIn(".github/workflows/update-market.yml", workflow)

    def test_48_hourly_permission_harvest_apply_and_validation_order(self):
        workflow = UPDATE_WORKFLOW.read_text()
        self.assertIn("actions: read", workflow)
        harvest = workflow.index("harvest-actions")
        apply = workflow.index("apply-inbox")
        final_validation = workflow.index("Validate rolling archive and event components")
        publication = workflow.index("Commit refreshed bridge data")
        self.assertLess(harvest, apply)
        self.assertLess(apply, final_validation)
        self.assertLess(final_validation, publication)

    def test_49_hourly_harvest_contract_accepts_only_completed_successful_issue_main_artifacts(self):
        source = (ROOT / "tools/current_data_promotion.py").read_text()
        for literal in (
            'run.get("status") != "completed"',
            'run.get("conclusion") != "success"',
            'run.get("event") != "issues"',
            'run.get("name") != "Fresh current agent transport"',
            'workflow_run.get("head_branch") != "main"',
        ):
            self.assertIn(literal, source)

    def test_50_shared_concurrency_never_cancels_running_acquisition(self):
        current = CURRENT_WORKFLOW.read_text()
        hourly = UPDATE_WORKFLOW.read_text()
        for workflow in (current, hourly):
            self.assertIn("group: market-bridge-update", workflow)
            self.assertIn("cancel-in-progress: false", workflow)

    def test_51_zero_pending_handoff_creates_no_consumption_ledger_churn(self):
        with tempfile.TemporaryDirectory() as artifact_temp, tempfile.TemporaryDirectory() as repo_temp:
            artifact_root, repo_root = Path(artifact_temp), Path(repo_temp)
            self.artifact(artifact_root, [self.reconstructible_resource()])
            result = promotion.apply_artifact(
                artifact_root,
                repository_root=repo_root,
                source_control_root=ROOT,
                processed_at_utc=self.known_at,
            )
            self.assertEqual(result["status"], "NO_PROMOTION_REQUIRED")
            self.assertFalse((repo_root / promotion.PROMOTION_LEDGER_PATH).exists())

    def test_52_consumption_ledger_is_not_market_data_authority(self):
        source = (ROOT / "tools/current_data_promotion.py").read_text()
        self.assertIn('"authority": "PROMOTION_CONSUMPTION_STATE_ONLY"', source)
        self.assertIn('"market_data_authority": False', source)
        contract = json.loads(BRIDGE_CONTRACT.read_text())
        durability = contract["semantic_resolution"]["current_data"]["durability"]
        self.assertEqual(durability["consumption_ledger"], "history/current-promotion-consumption.json")
        self.assertFalse(durability["promotion_handoff_is_authority"])
        self.assertFalse(durability["actions_artifact_is_durable_authority"])

    def test_53_both_current_data_uploads_include_hidden_output_root(self):
        workflow = CURRENT_WORKFLOW.read_text()
        issue_section, candidate_section = workflow.split("\n  candidate-real-acceptance:\n", 1)
        self.assertIn("  issue-current-data:\n", issue_section)
        self.assertIn("Upload validated ephemeral generation", issue_section)
        self.assertIn("path: .current-data-output/**", issue_section)
        self.assertIn("include-hidden-files: true", issue_section)
        candidate_section = "\n  candidate-real-acceptance:\n" + candidate_section
        self.assertIn("Upload exact candidate real acceptance evidence", candidate_section)
        self.assertIn("path: .current-data-output/**", candidate_section)
        self.assertIn("include-hidden-files: true", candidate_section)
        self.assertEqual(workflow.count("include-hidden-files: true"), 2)

    def test_54_artifact_download_auth_is_initial_only_and_redirect_bytes_return(self):
        token = "ghs_UNIT_TEST_SECRET"
        observed: dict[str, object] = {}

        class FakeOpener:
            def open(self, request, timeout=0):
                observed["initial_auth"] = request.get_header("Authorization")
                observed["initial_host"] = request.host
                handler = promotion._ArtifactRedirectHandler()
                redirected = handler.redirect_request(
                    request,
                    None,
                    302,
                    "Found",
                    Message(),
                    "https://signed-artifact.example.test/blob?sig=temporary",
                )
                self_outer.assertIsNotNone(redirected)
                assert redirected is not None
                observed["redirect_auth"] = redirected.get_header("Authorization")
                observed["redirect_unredirected_auth"] = redirected.unredirected_hdrs.get("Authorization")
                observed["redirect_host"] = redirected.host
                return _BytesResponse(b"artifact-bytes")

        self_outer = self
        with mock.patch.object(promotion.urllib.request, "build_opener", return_value=FakeOpener()):
            raw = promotion._github_bytes(
                "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
                token,
            )
        self.assertEqual(raw, b"artifact-bytes")
        self.assertEqual(observed["initial_auth"], f"Bearer {token}")
        self.assertEqual(observed["initial_host"], "api.github.com")
        self.assertIsNone(observed["redirect_auth"])
        self.assertIsNone(observed["redirect_unredirected_auth"])
        self.assertEqual(observed["redirect_host"], "signed-artifact.example.test")

    def test_55_signed_artifact_bytes_can_be_safely_extracted(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("promotion-handoff.json", "{}\n")
            archive.writestr("current-generation.json", "{}\n")
        raw = stream.getvalue()
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            promotion._safe_extract_zip(raw, destination)
            self.assertEqual((destination / "promotion-handoff.json").read_text(), "{}\n")
            self.assertEqual((destination / "current-generation.json").read_text(), "{}\n")

    def test_56_initial_github_api_403_fails_closed_without_token_leak(self):
        token = "ghs_NEVER_LOG_ME"
        initial = "https://api.github.com/repos/o/r/actions/artifacts/1/zip"

        class FakeOpener:
            def open(self, request, timeout=0):
                raise urllib.error.HTTPError(initial, 403, "Forbidden", Message(), None)

        with mock.patch.object(promotion.urllib.request, "build_opener", return_value=FakeOpener()):
            with self.assertRaises(promotion.PromotionError) as caught:
                promotion._github_bytes(initial, token)
        self.assertEqual(caught.exception.code, "ACTIONS_ARTIFACT_DOWNLOAD_FAILED")
        text = str(caught.exception)
        self.assertIn("status=403", text)
        self.assertIn("source_host=api.github.com", text)
        self.assertNotIn(token, text)
        self.assertNotIn("Authorization", text)

    def test_57_redirect_target_failure_redacts_signed_url_and_token(self):
        token = "ghs_NEVER_LOG_ME"
        signed = "https://signed-artifact.example.test/blob?sig=DO_NOT_LOG"

        class FakeOpener:
            def open(self, request, timeout=0):
                raise urllib.error.HTTPError(signed, 502, "Bad Gateway", Message(), None)

        with mock.patch.object(promotion.urllib.request, "build_opener", return_value=FakeOpener()):
            with self.assertRaises(promotion.PromotionError) as caught:
                promotion._github_bytes(
                    "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
                    token,
                )
        text = str(caught.exception)
        self.assertEqual(caught.exception.code, "ACTIONS_ARTIFACT_DOWNLOAD_FAILED")
        self.assertIn("target_host=signed-artifact.example.test", text)
        self.assertNotIn("DO_NOT_LOG", text)
        self.assertNotIn(token, text)
        self.assertNotIn(signed, text)

    def test_58_non_https_redirect_is_rejected_without_credential_forwarding(self):
        token = "ghs_NEVER_FORWARD"
        request = promotion._artifact_api_request(
            "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
            token,
        )
        handler = promotion._ArtifactRedirectHandler()
        with self.assertRaises(urllib.error.URLError) as caught:
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                Message(),
                "http://signed-artifact.example.test/blob",
            )
        self.assertNotIn(token, str(caught.exception))

    def test_59_redirect_with_embedded_credentials_is_rejected(self):
        token = "ghs_NEVER_FORWARD"
        request = promotion._artifact_api_request(
            "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
            token,
        )
        handler = promotion._ArtifactRedirectHandler()
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                Message(),
                "https://user:password@signed-artifact.example.test/blob",
            )

    def test_60_no_redirect_mocked_download_remains_compatible(self):
        token = "ghs_COMPAT"
        observed: dict[str, object] = {}

        class FakeOpener:
            def open(self, request, timeout=0):
                observed["auth"] = request.get_header("Authorization")
                return _BytesResponse(b"direct-artifact")

        with mock.patch.object(promotion.urllib.request, "build_opener", return_value=FakeOpener()):
            raw = promotion._github_bytes(
                "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
                token,
            )
        self.assertEqual(raw, b"direct-artifact")
        self.assertEqual(observed["auth"], f"Bearer {token}")

    def test_61_download_urLError_is_sanitized(self):
        token = "ghs_SUPER_SECRET"

        class FakeOpener:
            def open(self, request, timeout=0):
                raise urllib.error.URLError(f"network failure token={token}")

        with mock.patch.object(promotion.urllib.request, "build_opener", return_value=FakeOpener()):
            with self.assertRaises(promotion.PromotionError) as caught:
                promotion._github_bytes(
                    "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
                    token,
                )
        text = str(caught.exception)
        self.assertEqual(caught.exception.code, "ACTIONS_ARTIFACT_DOWNLOAD_FAILED")
        self.assertIn("reason_class=str", text)
        self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
