from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.current_data_transport import CurrentDataTransportError, main, normalize_request, request_wrapper


ROOT = Path(__file__).resolve().parents[2]


class CurrentDataInvocationContractTests(unittest.TestCase):
    def test_machine_template_is_complete_and_parser_accepts_it(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        request = bridge["semantic_resolution"]["current_data"]["request"]
        required = request["required_fields"]
        self.assertEqual(
            required,
            [
                "request_type",
                "required_series",
                "required_domains",
                "required_liquidity",
                "max_generation_age_seconds",
                "current_policy",
            ],
        )
        self.assertTrue(request["request_type_required"])
        self.assertEqual(request["request_type_const"], "FRESH_CURRENT")
        template = dict(request["canonical_template"])
        template["required_domains"] = ["SPOT"]
        normalized = normalize_request(template)
        self.assertEqual(normalized["request_type"], "FRESH_CURRENT")

    def test_missing_request_type_remains_fail_closed(self) -> None:
        with self.assertRaises(CurrentDataTransportError) as ctx:
            normalize_request(
                {
                    "required_series": [],
                    "required_domains": ["SPOT"],
                    "max_generation_age_seconds": 600,
                    "current_policy": "FINALIZED_ONLY",
                }
            )
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST_TYPE")

    def test_repository_builder_materializes_required_discriminator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "request.json"
            rc = main(
                [
                    "build-request",
                    "--domain",
                    "SPOT",
                    "--max-generation-age-seconds",
                    "600",
                    "--current-policy",
                    "FINALIZED_ONLY",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["request_type"], "FRESH_CURRENT")
            self.assertEqual(payload["required_domains"], ["SPOT"])
            self.assertEqual(normalize_request(payload), payload)

    def test_entrypoint_and_semantics_require_preflight_and_remote_readback(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        semantics = (ROOT / "docs/semantics/fresh-current-agent-transport-v1.md").read_text(encoding="utf-8")
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        current_data = bridge["semantic_resolution"]["current_data"]
        request = current_data["request"]
        transport = current_data["agent_transport"]
        self.assertIn('"request_type": "FRESH_CURRENT"', agents)
        self.assertIn("build-request", agents)
        self.assertIn("parse-request --request-file", agents)
        self.assertIn("MUTATION_OUTCOME_UNKNOWN", semantics)
        self.assertTrue(request["preflight"]["required_before_issue_mutation_when_checkout_available"])
        self.assertTrue(request["preflight"]["parser_remains_fail_closed"])
        self.assertTrue(transport["mutation_outcome_readback"]["tool_error_or_unknown_does_not_prove_remote_mutation_absent"])
        self.assertTrue(transport["mutation_outcome_readback"]["retry_only_if_remote_issue_absence_proven"])
        self.assertEqual(
            transport["mutation_outcome_readback"]["duplicate_issue_creation_on_unknown_outcome"],
            "FORBIDDEN",
        )

    def test_program2_d9_postrepair_request_identity_is_exact_issue_824_semantics(self) -> None:
        request = {
            "request_type": "FRESH_CURRENT",
            "required_series": [
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.5m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.15m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.1h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.4h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.1d", "latest_bars": 256},
                {"series_id": "spot.binance-spot.BTCUSDT.ohlcv.1w", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.5m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.15m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.1h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.4h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.1d", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHBTC.ohlcv.1w", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.15m", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.4h", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1d", "latest_bars": 256},
                {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1w", "latest_bars": 256},
            ],
            "required_domains": [],
            "max_generation_age_seconds": 600,
            "current_policy": "FINALIZED_ONLY",
        }
        normalized = normalize_request(request)
        wrapper = request_wrapper(normalized)
        self.assertEqual(len(normalized["required_series"]), 18)
        self.assertTrue(all(row["latest_bars"] == 256 for row in normalized["required_series"]))
        self.assertEqual(
            wrapper["request_sha256"],
            "dab41685db181b3df7e366492c7d8a212ad352891c363717b6347c9f571e4aaf",
        )

    def test_program2_d9_terminal_proof_requires_request_aware_network_acquisition_true(self) -> None:
        workflow = (ROOT / ".github/workflows/current-data-request.yml").read_text(encoding="utf-8")
        start = workflow.index("      - name: Print request-scope real acceptance terminal proof\n")
        end = workflow.index("      - name: Upload exact candidate real acceptance evidence\n", start)
        terminal_block = workflow[start:end]
        self.assertIn("satisfaction['request_aware_network_acquisition_implemented'] is True", terminal_block)
        self.assertNotIn("satisfaction['request_aware_network_acquisition_implemented'] is False", terminal_block)
        self.assertIn("REQUEST_AWARE_NETWORK_ACQUISITION_IMPLEMENTED=YES", terminal_block)
        self.assertNotIn("REQUEST_AWARE_NETWORK_ACQUISITION_IMPLEMENTED=NO", terminal_block)


if __name__ == "__main__":
    unittest.main()

# DB-F/S3 R01: required_liquidity additive invocation contract currentized
