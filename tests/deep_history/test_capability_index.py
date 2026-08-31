import json
import unittest
from pathlib import Path

from tools.capability_index import build_index, compact, validate_committed, validate_shape

ROOT = Path(__file__).resolve().parents[2]


class CapabilityIndexTests(unittest.TestCase):
    def setUp(self):
        self.index = build_index()
        validate_shape(self.index)
        self.by_id = {row["series_id"]: row for row in self.index["series"]}

    def profile(self, series_id):
        return self.index["profiles"][self.by_id[series_id]["profile_id"]]

    def test_deterministic_build_matches_committed_artifact(self):
        committed = json.loads((ROOT / "history" / "capability-index.json").read_text(encoding="utf-8"))
        self.assertEqual(compact(self.index), compact(committed))
        self.assertEqual(compact(build_index()), compact(build_index()))

    def test_committed_validator_passes(self):
        validate_committed()

    def test_compact_catalog_has_expected_cold_series(self):
        self.assertEqual(len(self.index["series"]), 61)
        self.assertEqual(len(self.index["profiles"]), 6)
        required = {
            "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "spot.binance-spot.ETHBTC.ohlcv.1d",
            "derivatives.kraken-futures.PI_ETHUSD.funding",
            "derivatives.kraken-futures.PI_ETHUSD.cvd",
            "derivatives.deribit-perpetual.ETH-PERPETUAL.funding",
            "derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h",
            "options.deribit-options.ETH.dvol.1h",
        }
        self.assertTrue(required <= set(self.by_id))

    def test_depth_class_is_semantic_not_physical_inventory_copy(self):
        self.assertEqual(self.profile("spot.binance-spot.ETHUSDT.ohlcv.1h")["history_mode"], "MAX_AVAILABLE")
        self.assertEqual(self.profile("spot.kraken-spot.ETHUSD.ohlcv.1h")["history_mode"], "PROVIDER_LIMITED")
        self.assertEqual(
            self.profile("derivatives.kraken-futures.PI_ETHUSD.funding")["history_mode"],
            "PROVIDER_LIMITED",
        )
        self.assertEqual(self.profile("options.deribit-options.ETH.dvol.1h")["history_mode"], "MAX_AVAILABLE")
        forbidden = {"first_timestamp", "last_timestamp", "row_count", "asset_count", "asset_inventory"}
        self.assertFalse(forbidden & set(self.index))
        for profile in self.index["profiles"].values():
            self.assertFalse(forbidden & set(profile))
        for row in self.index["series"]:
            self.assertFalse(forbidden & set(row))

    def test_hot_tail_routes_are_declared_without_path_guessing(self):
        self.assertEqual(
            self.profile("spot.binance-spot.ETHUSDT.ohlcv.1h")["hot_manifest_path"],
            "history/manifest.json",
        )
        self.assertEqual(
            self.profile("derivatives.kraken-futures.PI_ETHUSD.funding")["hot_manifest_path"],
            "derivatives/history-manifest.json",
        )
        self.assertIsNone(
            self.profile("derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h")[
                "hot_manifest_path"
            ]
        )

    def test_provider_policy_preserves_binance_usdm_exclusion(self):
        policies = {row["provider_id"]: row for row in self.index["provider_policies"]}
        disabled = policies["binance-usdm"]
        self.assertEqual(disabled["status"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["current_collection"], "DISABLED_BY_POLICY")
        self.assertEqual(disabled["network_calls"], 0)
        self.assertEqual(disabled["signal_vote"], "EXCLUDED")
        self.assertFalse(disabled["affects_health"])
        self.assertFalse(
            any(
                self.index["profiles"][row["profile_id"]]["provider_id"] == "binance-usdm"
                for row in self.index["series"]
            )
        )

    def test_forward_only_capabilities_are_explicit(self):
        forward = {row["capability_id"]: row for row in self.index["forward_capabilities"]}
        self.assertEqual(forward["liquidity.orderbook-snapshots"]["history_mode"], "FORWARD_ONLY")
        self.assertEqual(
            forward["liquidity.orderbook-snapshots"]["historical_backfill_status"],
            "UNAVAILABLE_BY_PROVIDER",
        )
        self.assertEqual(
            forward["options.deribit-options.ETH.surface-snapshots"]["historical_backfill_status"],
            "UNAVAILABLE_BY_PROVIDER",
        )

    def test_d64_activation_is_explicit_in_bridge_contract(self):
        contract = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        self.assertNotIn("market_capability_index", contract["canonical_paths"])
        self.assertEqual(contract["canonical_paths"]["capability_index"], "history/capability-index.json")
        self.assertEqual(contract["semantic_resolution"]["status"], "ACTIVE")
        self.assertEqual(contract["semantic_resolution"]["reader"]["input_authority"], "ResolutionPlan")


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: capability index 1.1 requestable surface qualified by tests/test_liquidity_s3_executor.py
