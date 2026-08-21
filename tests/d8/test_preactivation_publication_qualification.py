"""D8-side regression for qualification-only publication admission."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import publication_control_v2

ROOT = Path(__file__).resolve().parents[2]
SERIES_ID = "derivatives.binance-usdm.BTCUSDT.current"
TIMESTAMP_MS = 1787310900000


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


class PreActivationPublicationQualificationD8Tests(unittest.TestCase):
    def test_binance_usdm_provider_authority_remains_disabled(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        policy = bridge["disabled_providers"]["binance-usdm"]
        self.assertNotIn("binance-usdm", bridge["active_providers"])
        self.assertEqual(policy["status"], "DISABLED_BY_POLICY")
        self.assertEqual(policy["current_collection"], "DISABLED_BY_POLICY")
        self.assertEqual(policy["network_calls"], 0)
        self.assertEqual(policy["vps_runtime_status"], "NOT_ACTIVE")

    def test_normal_mode_rejects_preactivation_binance_usdm(self):
        with self.assertRaisesRegex(
            publication_control_v2.PublicationControlError,
            "PREACTIVATION_PROVIDER_REQUIRES_QUALIFICATION_MODE",
        ):
            publication_control_v2.resolve_capability_v2(
                SERIES_ID,
                _iso(TIMESTAMP_MS),
                _iso(TIMESTAMP_MS + 1),
                qualification_mode=False,
                root=ROOT,
            )

    def test_qualification_projection_keeps_disabled_provider_policy_truthful(self):
        index = publication_control_v2.build_index_v2(ROOT, qualification_mode=True)
        policy = next(
            row for row in index["provider_policies"]
            if row["provider_id"] == "binance-usdm"
        )
        descriptor = next(row for row in index["series"] if row["series_id"] == SERIES_ID)
        profile = index["profiles"][descriptor["profile_id"]]
        self.assertEqual(policy["status"], "DISABLED_BY_POLICY")
        self.assertEqual(
            profile["d8_origin_provider_admission"],
            publication_control_v2.PREACTIVATION_QUALIFICATION_ONLY,
        )


if __name__ == "__main__":
    unittest.main()
