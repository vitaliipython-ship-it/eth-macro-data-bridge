import json
import unittest
from pathlib import Path

from tools.capability_index import (
    build_index,
    compact,
    list_requestable_capabilities,
    resolve_capability,
    validate_committed,
    validate_shape,
    _warm_resource_interval_ms,
)

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

    def test_profile_summary_discovery_is_runtime_projection_without_catalog_rewrite(self):
        committed = json.loads((ROOT / "history" / "capability-index.json").read_text(encoding="utf-8"))
        committed_by_id = {
            row["capability_id"]: row for row in committed["requestable_capabilities"]
        }
        projected = list_requestable_capabilities()
        self.assertEqual(len(projected), len(committed_by_id))
        self.assertEqual(
            {row["capability_id"] for row in projected},
            set(committed_by_id),
        )
        for row in projected:
            self.assertEqual(row["supported_representations"], ["RAW", "PROFILE", "SUMMARY"])
            self.assertNotIn("SUMMARY", committed_by_id[row["capability_id"]]["supported_representations"])
        self.assertEqual(compact(build_index()), compact(committed))

    def test_compact_catalog_has_expected_cold_series(self):
        self.assertEqual(len(self.index["series"]), 63)
        self.assertEqual(len(self.index["profiles"]), 8)
        required = {
            "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "spot.binance-spot.ETHBTC.ohlcv.1d",
            "spot.kraken-spot.ETHUSD.ohlcv.5m",
            "spot.kraken-spot.ETHUSD.ohlcv.1d",
            "spot.kraken-spot.ETHUSD.derived-ohlcv.1h",
            "spot.kraken-spot.ETHUSD.derived-ohlcv.4h",
            "derivatives.kraken-futures.PI_ETHUSD.funding",
            "derivatives.kraken-futures.PI_ETHUSD.cvd",
            "derivatives.deribit-perpetual.ETH-PERPETUAL.funding",
            "derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h",
            "options.deribit-options.ETH.dvol.1h",
        }
        self.assertTrue(required <= set(self.by_id))
        for series_id in (
            "spot.kraken-spot.ETHUSD.derived-ohlcv.1h",
            "spot.kraken-spot.ETHUSD.derived-ohlcv.4h",
        ):
            profile = self.profile(series_id)
            self.assertEqual(profile["history_mode"], "MAX_AVAILABLE")
            self.assertIsNone(profile["hot_manifest_path"])
            self.assertEqual(profile["semantics_ref"], "contracts/kraken-spot-derived-ohlcv-v1.json")

    def test_deribit_funding_interval_is_derived_from_canonical_resource(self):
        series_id = "derivatives.deribit-perpetual.ETH-PERPETUAL.funding"
        args = (
            series_id,
            "2026-09-20T19:00:00Z",
            "2026-09-20T20:00:00Z",
            "2026-09-21T21:18:08.789Z",
        )
        plan = resolve_capability(*args)
        repeated = resolve_capability(*args)
        self.assertEqual(plan, repeated)
        self.assertEqual(plan["schema_version"], "market-data-resolution-plan/1.0.0")
        self.assertEqual(plan["series"]["interval_ms"], 3_600_000)
        self.assertEqual(
            plan["series"]["interval_source"],
            "CANONICAL_RESOURCE_RESOLUTION_SECONDS",
        )
        self.assertEqual(len(plan["segments"]), 1)
        segment = plan["segments"][0]
        self.assertEqual(segment["storage"], "GIT_WARM_RESOURCE")
        self.assertEqual(
            segment["resource_path"],
            "derivatives/archive/deribit-perpetual/ETH-PERPETUAL-funding-1h.json",
        )
        raw = (ROOT / segment["resource_path"]).read_bytes()
        resource = json.loads(raw)
        self.assertEqual(resource["resolution_seconds"] * 1000, plan["series"]["interval_ms"])
        import hashlib
        self.assertEqual(segment["sha256"], hashlib.sha256(raw).hexdigest())
        body = dict(plan)
        plan_sha256 = body.pop("plan_sha256")
        self.assertEqual(plan_sha256, hashlib.sha256(compact(body)).hexdigest())

    def test_warm_resource_interval_derivation_fails_closed_on_invalid_metadata(self):
        for value in (None, True, 0, -1):
            with self.subTest(resolution_seconds=value):
                with self.assertRaisesRegex(RuntimeError, "WARM_RESOURCE_RESOLUTION_INVALID"):
                    _warm_resource_interval_ms([
                        {"resource_path": "canonical.json", "resolution_seconds": value}
                    ])

    def test_warm_resource_interval_derivation_requires_consistent_grid(self):
        with self.assertRaisesRegex(RuntimeError, "WARM_RESOURCE_RESOLUTION_MISMATCH"):
            _warm_resource_interval_ms([
                {"resource_path": "a.json", "resolution_seconds": 3600},
                {"resource_path": "b.json", "resolution_seconds": 300},
            ])

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
