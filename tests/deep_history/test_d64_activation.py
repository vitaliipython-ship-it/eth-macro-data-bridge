import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class D64ActivationTests(unittest.TestCase):
    def test_bridge_contract_declares_active_capability_route(self):
        contract = read("bridge-contract.json")
        self.assertEqual(contract["contract_version"], "1.4.0")
        self.assertEqual(contract["canonical_paths"]["capability_index"], "history/capability-index.json")
        self.assertEqual(contract["semantic_resolution"]["status"], "ACTIVE")
        self.assertEqual(
            contract["semantic_resolution"]["discovery_route_authority"],
            "canonical_paths.capability_index",
        )
        self.assertEqual(contract["semantic_resolution"]["reader"]["input_authority"], "ResolutionPlan")
        transport = contract["semantic_resolution"]["agent_transport"]
        self.assertEqual(transport["status"], "ACTIVE")
        self.assertEqual(transport["method"], "GITHUB_ISSUE_REQUEST")
        self.assertEqual(transport["authority"], "TRANSPORT_ONLY")
        self.assertTrue(transport["owner_only"])

    def test_legacy_manifest_routes_remain_backward_compatible(self):
        contract = read("bridge-contract.json")
        legacy = contract["semantic_resolution"]["legacy_manifest_route"]
        paths = contract["canonical_paths"]
        self.assertEqual(legacy["status"], "SUPPORTED_BACKWARD_COMPATIBLE")
        self.assertEqual(legacy["spot_history_manifest"], paths["spot_history_manifest"])
        self.assertEqual(legacy["release_history_manifest"], paths["release_history_manifest"])

    def test_capability_index_remains_derived_not_physical_authority(self):
        contract = read("bridge-contract.json")
        index = read(contract["canonical_paths"]["capability_index"])
        self.assertEqual(index["authority"]["route_policy"], "bridge-contract.json")
        self.assertEqual(
            contract["semantic_resolution"]["physical_authority"]["cold_manifest"],
            contract["canonical_paths"]["release_history_manifest"],
        )
        self.assertNotIn("asset_inventory", index)

    def test_public_resolver_plan_uses_declared_authorities(self):
        contract = read("bridge-contract.json")
        result = subprocess.run(
            [
                sys.executable,
                "tools/capability_index.py",
                "resolve",
                "spot.binance-spot.ETHUSDT.ohlcv.1h",
                "--from",
                "2022-06-18T00:00:00Z",
                "--to",
                "2022-06-19T00:00:00Z",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        plan = json.loads(result.stdout)
        self.assertEqual(plan["authority"]["route_policy"], "bridge-contract.json")
        self.assertEqual(plan["authority"]["capability_index"], contract["canonical_paths"]["capability_index"])
        self.assertEqual(plan["authority"]["cold_manifest"], contract["canonical_paths"]["release_history_manifest"])
        self.assertTrue(plan["segments"])


if __name__ == "__main__":
    unittest.main()
