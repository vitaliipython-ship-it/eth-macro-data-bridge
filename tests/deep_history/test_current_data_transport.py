from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tools import current_data_transport as transport
from tools import history_consumer


class CurrentDataTransportTests(unittest.TestCase):
    def _domain_request(self, **overrides):
        value = {
            "request_type": "FRESH_CURRENT",
            "required_series": [],
            "required_domains": ["ANALYTICS"],
            "max_generation_age_seconds": 600,
            "current_policy": "FINALIZED_ONLY",
        }
        value.update(overrides)
        return value

    def _issue_event(self, body, *, issue_user="owner", repo_owner="owner", title="[current-data] request"):
        return {
            "issue": {"number": 7, "title": title, "body": json.dumps(body), "user": {"login": issue_user}},
            "repository": {"owner": {"login": repo_owner}},
        }

    def test_01_exact_contract_identity(self):
        self.assertEqual(transport.CONTRACT_ID, "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1")
        self.assertEqual(transport.CONTRACT_VERSION, "1.1.0")
        self.assertEqual(transport.REQUEST_SCHEMA_V10, "fresh-current-agent-request/1.0.0")
        self.assertEqual(transport.ISSUE_PREFIX, "[current-data]")
        self.assertEqual(transport.EXECUTION_TRANSPORT, "GITHUB_ACTIONS_ISSUE_V1")

    def test_02_owner_only_issue_request(self):
        number, request = transport.parse_issue_event(self._issue_event(self._domain_request()))
        self.assertEqual(number, 7)
        self.assertEqual(request["required_domains"], ["ANALYTICS"])
        with self.assertRaises(transport.CurrentDataTransportError) as caught:
            transport.parse_issue_event(self._issue_event(self._domain_request(), issue_user="other"))
        self.assertEqual(caught.exception.code, "OWNER_ONLY")

    def test_03_json_only_request(self):
        with self.assertRaises(transport.CurrentDataTransportError) as caught:
            transport.parse_request_body("request_type=FRESH_CURRENT")
        self.assertEqual(caught.exception.code, "MALFORMED_JSON")
        normalized = transport.parse_request_body(json.dumps(self._domain_request()))
        self.assertEqual(normalized["request_type"], "FRESH_CURRENT")

    def test_04_forbidden_physical_inputs_rejected(self):
        for field in transport.FORBIDDEN_PHYSICAL_INPUTS:
            payload = self._domain_request()
            payload[field] = "forbidden"
            with self.subTest(field=field), self.assertRaises(transport.CurrentDataTransportError) as caught:
                transport.normalize_request(payload)
            self.assertEqual(caught.exception.code, "FORBIDDEN_PHYSICAL_INPUT")

    def test_05_unknown_series_rejected_by_capability_discovery(self):
        payload = self._domain_request(required_domains=[], required_series=["spot.invalid.X.ohlcv.5m"])
        with mock.patch.object(transport, "list_capabilities", return_value=[]), self.assertRaises(
            transport.CurrentDataTransportError
        ) as caught:
            transport.normalize_request(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_SERIES")

    def test_06_required_domain_enum_validation(self):
        with self.assertRaises(transport.CurrentDataTransportError) as caught:
            transport.normalize_request(self._domain_request(required_domains=["NOPE"]))
        self.assertEqual(caught.exception.code, "INVALID_DOMAIN_REQUEST")
        for value in transport.ALLOWED_DOMAINS:
            normalized = transport.normalize_request(self._domain_request(required_domains=[value]))
            self.assertEqual(normalized["required_domains"], [value])

    def test_07_persisted_fresh_state_skips_acquisition(self):
        request = transport.normalize_request(self._domain_request())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "analytics.json"
            path.write_text(json.dumps({"generated_at_utc": "2026-08-26T16:00:00Z", "analytics_freshness": "LIVE_USABLE"}))
            with mock.patch.object(transport, "_domain_manifest_path", return_value=path):
                result = transport.evaluate_persisted_freshness(
                    request, now=datetime(2026, 8, 26, 16, 5, tzinfo=timezone.utc)
                )
        self.assertTrue(result["persisted_fresh_enough"])
        self.assertFalse(result["acquisition_required"])
        self.assertEqual(result["generation_mode"], "PERSISTED_REUSE")

    def test_08_stale_state_triggers_acquisition(self):
        request = transport.normalize_request(self._domain_request())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "analytics.json"
            path.write_text(json.dumps({"generated_at_utc": "2026-08-26T15:00:00Z", "analytics_freshness": "LIVE_USABLE"}))
            with mock.patch.object(transport, "_domain_manifest_path", return_value=path):
                result = transport.evaluate_persisted_freshness(
                    request, now=datetime(2026, 8, 26, 16, 5, tzinfo=timezone.utc)
                )
        self.assertFalse(result["persisted_fresh_enough"])
        self.assertTrue(result["acquisition_required"])
        self.assertEqual(result["generation_mode"], "FRESH_ACQUISITION")

    def test_09_existing_collector_invoked_no_duplicate_acquisition_code(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        source = (transport.ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8")
        self.assertIn("python src/collector.py", workflow)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("requests.get", source)
        self.assertNotIn("api.binance.com", source)

    def test_10_contents_permission_is_read_only(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertNotIn("contents: write", workflow)

    def test_11_no_git_add_commit_push(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        for command in ("git add", "git commit", "git push"):
            self.assertNotIn(command, workflow)

    def test_12_same_concurrency_group_as_scheduled_acquisition(self):
        current = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        scheduled = (transport.ROOT / ".github/workflows/update-market.yml").read_text(encoding="utf-8")
        self.assertIn("group: market-bridge-update", current)
        self.assertIn("group: market-bridge-update", scheduled)

    def test_13_no_cancel_in_progress(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        self.assertIn("cancel-in-progress: false", workflow)

    def test_14_control_plane_head_and_tree_are_captured(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        self.assertIn("git rev-parse HEAD", workflow)
        self.assertIn("git rev-parse 'HEAD^{tree}'", workflow)
        self.assertIn("HEAD_BEFORE_EQUALS_HEAD_AFTER=YES", workflow)

    def _generation_fixture(self, root: Path):
        (root / "data").mkdir(parents=True)
        (root / "data/manifest.json").write_text(
            json.dumps({"generated_at_utc": "2026-08-26T16:00:00Z", "collector_version": "0.4.0"}),
            encoding="utf-8",
        )
        output = root / "out"
        output.mkdir()
        request = transport.normalize_request(self._domain_request())
        wrapper = transport.request_wrapper(request)
        resource_index = {
            "schema_version": transport.RESOURCE_INDEX_SCHEMA,
            "request_sha256": wrapper["request_sha256"],
            "follow_legacy_raw_url_for_ephemeral_data": False,
            "domains": [
                {"domain_id": "ANALYTICS", "resource_logical_id": "current-domain:analytics", "sha256": "1" * 64}
            ],
            "series": [],
            "liquidity_resources": [],
        }
        validation = {"status": "PASS"}
        transport._write_json(output / "resource-index.json", resource_index)
        transport._write_json(output / "validation-summary.json", validation)
        return request, wrapper["request_sha256"], resource_index, validation, output

    def test_15_generation_id_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, sha, index, validation, output = self._generation_fixture(root)
            with mock.patch.object(transport, "ROOT", root):
                first, _ = transport.build_generation_receipts(
                    request, sha, index, validation, output_root=output,
                    control_plane_head="a" * 40, control_plane_tree="b" * 40, head_after="a" * 40,
                    generation_mode="FRESH_ACQUISITION", known_at_utc="2026-08-26T16:01:00Z",
                    issue_number="7", run_id="100", run_url="https://example/run/100", artifact_name="a"
                )
                second, _ = transport.build_generation_receipts(
                    request, sha, index, validation, output_root=output,
                    control_plane_head="a" * 40, control_plane_tree="b" * 40, head_after="a" * 40,
                    generation_mode="FRESH_ACQUISITION", known_at_utc="2026-08-26T16:02:00Z",
                    issue_number="8", run_id="200", run_url="https://example/run/200", artifact_name="b"
                )
        self.assertEqual(first["generation_id"], second["generation_id"])

    def test_16_run_id_excluded_from_generation_id(self):
        source = (transport.ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8")
        identity = source[source.index("identity_basis={"):source.index("generation_id=_sha256_json(identity_basis)")]
        self.assertNotIn("run_id", identity)
        self.assertNotIn("issue_number", identity)
        self.assertNotIn("artifact_name", identity)

    def test_17_artifact_transport_identity_is_separated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, sha, index, validation, output = self._generation_fixture(root)
            with mock.patch.object(transport, "ROOT", root):
                generation, receipt = transport.build_generation_receipts(
                    request, sha, index, validation, output_root=output,
                    control_plane_head="a" * 40, control_plane_tree="b" * 40, head_after="a" * 40,
                    generation_mode="PERSISTED_REUSE", known_at_utc="2026-08-26T16:01:00Z",
                    issue_number="7", run_id="99", run_url="run-url", artifact_name="artifact"
                )
        self.assertNotIn("run_id", generation)
        self.assertEqual(receipt["run_id"], "99")
        self.assertEqual(receipt["authority"], "TRANSPORT_ONLY")

    def test_18_domain_resource_index_is_semantic(self):
        request = transport.normalize_request(self._domain_request())
        wrapper = transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "analytics-manifest.json"
            source.write_text(json.dumps({"generated_at_utc":"2026-08-26T16:00:00Z","analytics_freshness":"LIVE_USABLE"}))
            output = root / "out"
            output.mkdir()
            with mock.patch.object(transport, "_domain_manifest_path", return_value=source):
                index = transport.build_resource_index(
                    request, wrapper["request_sha256"], output_root=output,
                    now=datetime(2026,8,26,16,1,tzinfo=timezone.utc)
                )
        row = index["domains"][0]
        for key in ("domain_id","resource_logical_id","status","generated_at_utc","sha256","size_bytes","availability","freshness"):
            self.assertIn(key, row)
        self.assertNotIn("manifest_path", row)

    def test_19_legacy_raw_url_not_ephemeral_authority(self):
        request = transport.normalize_request(self._domain_request())
        wrapper = transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "analytics.json"
            source.write_text(json.dumps({"generated_at_utc":"2026-08-26T16:00:00Z","analytics_freshness":"LIVE_USABLE","raw_url":"https://legacy"}))
            output = root / "out"; output.mkdir()
            with mock.patch.object(transport, "_domain_manifest_path", return_value=source):
                index = transport.build_resource_index(request, wrapper["request_sha256"], output_root=output,
                    now=datetime(2026,8,26,16,1,tzinfo=timezone.utc))
        self.assertFalse(index["follow_legacy_raw_url_for_ephemeral_data"])
        self.assertFalse(index["domains"][0]["legacy_raw_url_is_authority"])

    def test_20_existing_history_resolver_and_reader_are_reused(self):
        source = (transport.ROOT / "tools/history_consumer.py").read_text(encoding="utf-8")
        self.assertIn("resolve_capability", source)
        self.assertIn("materialize_resolution_plan", source)
        self.assertNotIn("class SecondResolver", source)
        self.assertNotIn("class SecondReader", source)

    def test_21_latest_finalized_selection_contains_no_open_bar(self):
        latest_open = 1787751000000
        step = 300000
        payload = json.dumps([{"open_time": history_consumer._format_utc_ms(latest_open), "open":"1","high":"2","low":"1","close":"2","volume":"3"}]) + "\n"
        diagnostics = {"status":"PASS","rows":1,"expected_rows":1,"gap_count":0,"duplicates":0}
        receipt = {"semantic_receipt":{"finality":"FINALIZED"}}
        with mock.patch.object(history_consumer, "_actual_latest_finalized_timestamp", return_value=({}, latest_open, step, "history/manifest.json")), mock.patch.object(
            history_consumer, "read_history", return_value=({"plan_sha256":"a"*64}, payload, diagnostics, receipt)
        ):
            _plan, _payload, _diagnostics, result = history_consumer.latest_history(
                "spot.binance-spot.ETHUSDT.ohlcv.5m", 1, cutoff_utc="2026-08-26T14:00:00Z"
            )
        self.assertEqual(result["semantic_receipt"]["finality"], "FINALIZED")
        self.assertEqual(result["latest_selection"]["latest_open_timestamp_ms"], latest_open)

    def test_22_no_guessed_schedule_is_semantic_authority(self):
        source = (transport.ROOT / "tools/history_consumer.py").read_text(encoding="utf-8")
        self.assertIn("ACTUAL_DECLARED_CANONICAL_FINALIZED_OBSERVATION", source)
        self.assertIn('"local_guessed_schedule_is_authority": False', source)
        self.assertNotIn("floor_to_interval", source)

    def test_23_malformed_provider_result_fails_resource_build(self):
        request = transport.normalize_request(self._domain_request())
        wrapper = transport.request_wrapper(request)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "bad.json"; source.write_text("not-json")
            output = root / "out"; output.mkdir()
            with mock.patch.object(transport, "_domain_manifest_path", return_value=source), self.assertRaises(Exception):
                transport.build_resource_index(request, wrapper["request_sha256"], output_root=output)

    def test_24_required_degraded_capability_fails_explicitly(self):
        request = transport.normalize_request(self._domain_request())
        wrapper = transport.request_wrapper(request)
        index = {
            "request_sha256": wrapper["request_sha256"],
            "follow_legacy_raw_url_for_ephemeral_data": False,
            "domains": [{"domain_id":"ANALYTICS","status":"DEGRADED","freshness":"FRESH"}],
            "series": [],
        }
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(transport.CurrentDataTransportError) as caught:
            transport.validate_generation(request, wrapper["request_sha256"], index, output_root=Path(temp))
        self.assertEqual(caught.exception.code, "REQUIRED_CAPABILITY_DEGRADED")

    def test_25_durability_classes_are_explicit(self):
        source = (transport.ROOT / "tools/current_data_transport.py").read_text(encoding="utf-8")
        self.assertIn("RECONSTRUCTIBLE_SERIES", source)
        self.assertIn("NON_RECONSTRUCTIBLE_OR_SAMPLE_DEPENDENT_CURRENT", source)

    def test_26_ephemeral_current_evidence_cannot_auto_publish_research(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, sha, index, validation, output = self._generation_fixture(root)
            with mock.patch.object(transport, "ROOT", root):
                generation, _ = transport.build_generation_receipts(
                    request, sha, index, validation, output_root=output,
                    control_plane_head="a"*40, control_plane_tree="b"*40, head_after="a"*40,
                    generation_mode="FRESH_ACQUISITION", known_at_utc="2026-08-26T16:01:00Z"
                )
        self.assertFalse(generation["on_demand_ephemeral_data_automatically_durable_research_evidence"])
        self.assertFalse(generation["automatic_research_publication_from_ephemeral_only_evidence"])

    def test_27_normal_tests_are_network_free(self):
        source = (transport.ROOT / "tests/deep_history/test_current_data_transport.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        subprocess_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                    subprocess_calls.append(node.func.attr)
        self.assertFalse(any(name == "requests" or name.startswith("urllib") for name in imported))
        self.assertEqual(subprocess_calls, [])

    def test_28_future_aife_transport_does_not_change_semantic_contract(self):
        self.assertEqual(transport.FUTURE_EXECUTION_TRANSPORT, "AIFE_SERVER_D8_CURRENT_V1")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request, sha, index, validation, output = self._generation_fixture(root)
            with mock.patch.object(transport, "ROOT", root):
                generation, receipt = transport.build_generation_receipts(
                    request, sha, index, validation, output_root=output,
                    control_plane_head="a"*40, control_plane_tree="b"*40, head_after="a"*40,
                    generation_mode="FRESH_ACQUISITION", known_at_utc="2026-08-26T16:01:00Z"
                )
        self.assertEqual(generation["contract_id"], transport.CONTRACT_ID)
        self.assertFalse(receipt["future_transport_swap_requires_domain_rewrite"])

    def test_29_request_sha_is_canonical_and_order_stable(self):
        a = transport.normalize_request(self._domain_request(required_domains=["OPTIONS","ANALYTICS"]))
        b = transport.normalize_request(self._domain_request(required_domains=["ANALYTICS","OPTIONS"]))
        self.assertEqual(transport.request_wrapper(a)["request_sha256"], transport.request_wrapper(b)["request_sha256"])

    def test_30_issue_workflow_closes_request_and_keeps_transport_only(self):
        workflow = (transport.ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        self.assertIn("startsWith(github.event.issue.title, '[current-data]')", workflow)
        self.assertIn("github.actor == github.repository_owner", workflow)
        self.assertIn("state: 'closed'", workflow)
        self.assertIn("REMOTE_REPOSITORY_MUTATION=NO", workflow)


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: current-data 1.1 dual-read and exact-only semantics qualified by DB-F/S3 suite
