"""Preactivation D8-origin publication admission and actual A2 semantic proof."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import publication_control_v2
from history_access import materialize_resolution_plan_any

ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "pub-0e3a0d13c5ea7d46c50a13285a1c0372190123be620b92a7a2a062bf70ca5b42"
DATA_COMMIT = "789d24c26af5cfd36b3be62a89093fd8becbc684"
CONTROL_COMMIT = "f05a33df6bc661ed14941cb47487439f28f92d58"
RESOURCE_PATH = f"history/d8-origin/resources/{BATCH_ID}.json"
CONTROL_PATH = "history/d8-origin/manifest.json"
MEMBERSHIP_SHA256 = "2f97f71630e8f42704e563c872356ef4212ae7a324286303506e0677ac796a3d"
PAYLOAD_SHA256 = "a2856c0ccc0610d87f796949c8dfa4046286e93cc164f95588438e9a402054b5"


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _semantic_value(envelope: dict) -> object:
    value = envelope.get("value")
    if envelope.get("d9_forward_seam", {}).get("target") == "FIXED_GRID" and isinstance(value, dict):
        fields = ("open", "high", "low", "close", "volume")
        if all(field in value for field in fields):
            return {field: value[field] for field in fields}
    return value


def _a2_publication() -> tuple[dict, dict, dict[str, dict]]:
    manifest = json.loads((ROOT / CONTROL_PATH).read_text(encoding="utf-8"))
    matches = [row for row in manifest["publications"] if row.get("batch_id") == BATCH_ID]
    if len(matches) != 1:
        raise AssertionError("actual A2 PublicationBatch control entry must exist exactly once")
    publication = matches[0]
    resource = json.loads((ROOT / RESOURCE_PATH).read_text(encoding="utf-8"))
    envelopes = {row["observation_id"]: row for row in resource["observations"]}
    return publication, resource, envelopes


def _minimal_validation_fixture(root: Path, *, include_resource: bool = True) -> None:
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "contracts/d8-runtime-candidate.json", root / "contracts/d8-runtime-candidate.json")
    if include_resource:
        target = root / RESOURCE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / RESOURCE_PATH, target)


class PreActivationD8PublicationQualificationTests(unittest.TestCase):
    def test_actual_a2_batch_identity_is_exact_and_unchanged(self):
        publication, resource, envelopes = _a2_publication()
        self.assertEqual(publication["batch_id"], BATCH_ID)
        self.assertEqual(publication["data_commit_sha"], DATA_COMMIT)
        self.assertEqual(publication["member_count"], 20)
        self.assertEqual(publication["membership_sha256"], MEMBERSHIP_SHA256)
        self.assertEqual(publication["payload_sha256"], PAYLOAD_SHA256)
        self.assertEqual(publication["resource_path"], RESOURCE_PATH)
        self.assertEqual(resource["batch_id"], BATCH_ID)
        self.assertEqual(resource["member_count"], 20)
        self.assertEqual(len(envelopes), 20)

    def test_machine_policy_is_qualification_only_and_does_not_activate_provider(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        admission = json.loads(
            (ROOT / publication_control_v2.QUALIFICATION_ADMISSION_PATH).read_text(encoding="utf-8")
        )
        disabled = bridge["disabled_providers"]["binance-usdm"]
        self.assertNotIn("binance-usdm", bridge["active_providers"])
        self.assertEqual(disabled["status"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["current_collection"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["network_calls"], 0)
        self.assertEqual(disabled["vps_runtime_status"], "NOT_ACTIVE")
        self.assertEqual(admission["authority_role"], "QUALIFICATION_ADMISSION_ONLY_NOT_PROVIDER_POLICY")
        self.assertTrue(admission["normal_resolution_requires_active_provider_authority"])
        row = admission["admissions"][0]
        self.assertEqual(row["provider_id"], "binance-usdm")
        self.assertEqual(row["scope"], "QUALIFICATION_MODE_ONLY")
        self.assertTrue(row["does_not_activate_provider"])
        self.assertTrue(row["does_not_enable_github_acquisition"])
        self.assertTrue(row["provider_authority_transition_required_later"])

    def test_binance_usdm_is_qualification_only_and_provider_policy_stays_disabled(self):
        series_id = "derivatives.binance-usdm.BTCUSDT.current"
        normal = publication_control_v2.build_index_v2(ROOT, qualification_mode=False)
        self.assertNotIn(series_id, {row["series_id"] for row in normal["series"]})
        with self.assertRaisesRegex(
            publication_control_v2.PublicationControlError,
            "PREACTIVATION_PROVIDER_REQUIRES_QUALIFICATION_MODE",
        ):
            publication_control_v2.resolve_capability_v2(
                series_id,
                _iso(1787310900000),
                _iso(1787310900001),
                qualification_mode=False,
                root=ROOT,
            )

        qualified = publication_control_v2.build_index_v2(ROOT, qualification_mode=True)
        policy = next(row for row in qualified["provider_policies"] if row["provider_id"] == "binance-usdm")
        profile = qualified["profiles"][
            next(row for row in qualified["series"] if row["series_id"] == series_id)["profile_id"]
        ]
        self.assertEqual(policy["status"], "DISABLED_BY_POLICY")
        self.assertEqual(
            profile["d8_origin_provider_admission"],
            publication_control_v2.PREACTIVATION_QUALIFICATION_ONLY,
        )

    def test_active_provider_d8_origin_series_resolves_in_normal_mode(self):
        publication, _resource, envelopes = _a2_publication()
        series = next(
            row for row in publication["series"]
            if row["series_id"] == "derivatives.deribit-perpetual.BTC-PERPETUAL.current"
        )
        observation = series["observations"][0]
        timestamp = observation["effective_timestamp_ms"]
        plan = publication_control_v2.resolve_capability_v2(
            series["series_id"],
            _iso(timestamp),
            _iso(timestamp + 1),
            current_policy="INCLUDE_CURRENT_PROVISIONAL",
            qualification_mode=False,
            root=ROOT,
        )
        rows, diagnostics = materialize_resolution_plan_any(plan, mode="strict")
        match = [row for row in rows if row.get("observation_id") == observation["observation_id"]]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["value"], _semantic_value(envelopes[observation["observation_id"]]))
        self.assertEqual(diagnostics["status"], "PASS")

    def test_unrelated_disabled_provider_without_explicit_admission_is_rejected(self):
        index = {
            "provider_policies": [
                {"provider_id": "unrelated-disabled", "status": "DISABLED_BY_POLICY"}
            ]
        }
        series = {
            "provider": "unrelated-disabled",
            "capability_id": "unrelated.capability",
            "series_id": "derivatives.unrelated-disabled.TEST.current",
        }
        routing = {
            "provider": "unrelated-disabled",
            "series_id": series["series_id"],
            "target_residence_role": "WARM",
            "publication_eligibility": "VALIDATED_TERMINAL_CHECKPOINT_V2",
        }
        self.assertEqual(
            publication_control_v2._provider_admission_kind(
                index,
                ROOT,
                series,
                routing,
                qualification_mode=True,
            ),
            publication_control_v2.REJECT_PROVIDER,
        )

    def test_missing_or_corrupt_publication_evidence_fails_closed(self):
        publication, _resource, _envelopes = _a2_publication()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _minimal_validation_fixture(root, include_resource=False)
            with self.assertRaisesRegex(
                publication_control_v2.PublicationControlError,
                "resource missing",
            ):
                publication_control_v2._validate_publication(root, publication)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = root / CONTROL_PATH
            control.parent.mkdir(parents=True, exist_ok=True)
            control.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                publication_control_v2.PublicationControlError,
                "manifest identity mismatch",
            ):
                publication_control_v2.publications(root)

    def test_wrong_capability_provider_series_binding_fails_closed(self):
        publication, _resource, _envelopes = _a2_publication()
        tampered = copy.deepcopy(publication)
        target = next(row for row in tampered["series"] if row["provider"] == "binance-usdm")
        target["provider"] = "kraken-futures"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _minimal_validation_fixture(root)
            with self.assertRaisesRegex(
                publication_control_v2.PublicationControlError,
                "current declaration authority",
            ):
                publication_control_v2._validate_publication(root, tampered)

    def test_wrong_publication_eligibility_fails_closed(self):
        publication, _resource, _envelopes = _a2_publication()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _minimal_validation_fixture(root)
            contract_path = root / "contracts/d8-runtime-candidate.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            capability = next(
                row for row in contract["due_policy"]["capabilities"]
                if row["id"] == "binance-usdm.m5-current"
            )
            for rule in capability["forwarding"]["series_rules"]:
                rule["publication_eligibility"] = "NOT_ELIGIBLE"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(
                publication_control_v2.PublicationControlError,
                "checkpoint-v2 terminal eligible",
            ):
                publication_control_v2._validate_publication(root, publication)

    def test_actual_a2_all_20_materialize_in_qualification_mode_without_network(self):
        publication, resource, envelopes = _a2_publication()
        self.assertEqual(publication["member_count"], 20)
        self.assertEqual(resource["member_count"], 20)
        materialized = 0
        with mock.patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("provider/network access forbidden in semantic qualification"),
        ) as network:
            for series in publication["series"]:
                for observation in series["observations"]:
                    timestamp = observation["effective_timestamp_ms"]
                    step = int(series.get("interval_ms") or 1)
                    plan = publication_control_v2.resolve_capability_v2(
                        series["series_id"],
                        _iso(timestamp),
                        _iso(timestamp + step),
                        qualification_mode=True,
                        root=ROOT,
                    )
                    rows, diagnostics = materialize_resolution_plan_any(plan, mode="strict")
                    matches = [
                        row for row in rows
                        if row.get("observation_id") == observation["observation_id"]
                    ]
                    self.assertEqual(len(matches), 1, observation["observation_id"])
                    row = matches[0]
                    envelope = envelopes[observation["observation_id"]]
                    self.assertEqual(row.get("known_at"), envelope["known_at"])
                    self.assertEqual(row.get("finality"), envelope["finality"])
                    self.assertEqual(row.get("provenance"), envelope["provenance"])
                    self.assertEqual(row.get("payload_fingerprint"), envelope["fingerprint"])
                    self.assertEqual(row.get("value"), _semantic_value(envelope))
                    self.assertEqual(diagnostics.get("status"), "PASS")
                    self.assertEqual(diagnostics.get("receipt", {}).get("series_id"), series["series_id"])
                    if series["provider"] == "binance-usdm":
                        self.assertEqual(
                            plan["authority"]["d8_origin_provider_admission"],
                            publication_control_v2.PREACTIVATION_QUALIFICATION_ONLY,
                        )
                    materialized += 1
        network.assert_not_called()
        self.assertEqual(materialized, 20)

    def test_active_v1_route_and_activation_boundaries_remain_unchanged(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        runtime = json.loads((ROOT / "contracts/d8-runtime-candidate.json").read_text(encoding="utf-8"))
        self.assertEqual(
            bridge["semantic_resolution"]["resolver"]["resolution_plan_schema"],
            "market-data-resolution-plan/1.0.0",
        )
        self.assertEqual(runtime["authority"]["active_default_route"], "D6_RESOLUTION_PLAN_V1")
        self.assertFalse(runtime["authority"]["d8_runtime_active"])
        self.assertFalse(runtime["authority"]["d9_active"])
        self.assertFalse(runtime["authority"]["provider_authority_transition_allowed"])
        self.assertFalse(runtime["authority"]["production_cutover_allowed"])


if __name__ == "__main__":
    unittest.main()
