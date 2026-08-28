from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from kraken_trade_flow import apply_trade_flow_evidence
from tools import current_data_transport


NOW = 1_800_000_000_000
END = (NOW // 300_000) * 300_000
START = END - 300_000
FLOW_METRICS = ("trade-count", "trade-volume", "aggressor-differential", "cvd")


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def trade(offset_ms: int, *, trade_id: int) -> dict[str, object]:
    return {
        "time": iso(START + offset_ms),
        "price": "2500",
        "size": "1",
        "side": "buy",
        "trade_id": trade_id,
        "type": "fill",
    }


def getter(history: list[dict[str, object]]):
    def get(_url: str) -> dict[str, object]:
        return {
            "result": "success",
            "serverTime": iso(END + 1_000),
            "history": list(history),
        }

    return get


def intelligence(
    *,
    trade_count: object = 0,
    trade_count_timestamp: int = END,
    trade_count_semantics: str | None = None,
) -> dict[str, object]:
    metrics: dict[str, dict[str, object]] = {
        "trade-count": {"latest": [trade_count_timestamp, trade_count], "freshness_status": "LIVE_USABLE"},
        "trade-volume": {"latest": [END, 0], "freshness_status": "LIVE_USABLE"},
        "aggressor-differential": {"latest": [END, 0], "freshness_status": "LIVE_USABLE"},
        "cvd": {"latest": [END, {"cvd": "0"}], "freshness_status": "LIVE_USABLE"},
    }
    if trade_count_semantics is not None:
        metrics["trade-count"]["native_timestamp_semantics"] = trade_count_semantics
    native_available = ["funding", *FLOW_METRICS]
    analytics_symbol = {name: value["latest"] for name, value in metrics.items()}
    analytics_symbol["funding"] = [END, "0.0001"]
    return {
        "derivatives": {
            "providers": {
                "kraken-futures": {
                    "status": "PASS",
                    "instruments": {"PI_ETHUSD": {"metrics": metrics}},
                }
            }
        },
        "analytics": {
            "schema_version": "1.0.0",
            "generated_at_utc": iso(NOW),
            "overall_data_plane_status": "PASS",
            "analytics_available_metrics": list(native_available),
            "latest": {
                "kraken-futures": {
                    "analytics_provider": "KRAKEN_FUTURES_NATIVE",
                    "analytics_freshness": "LIVE_USABLE",
                    "analytics_available_metrics": list(native_available),
                    "instruments": {"PI_ETHUSD": analytics_symbol},
                }
            },
        },
    }


def apply_case(payload: dict[str, object], history: list[dict[str, object]]):
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            result = apply_trade_flow_evidence(payload, getter(history), NOW)
            persisted = json.loads(Path("analytics/manifest.json").read_text(encoding="utf-8"))
        finally:
            os.chdir(previous)
    return result, persisted


def projected_metric(analytics: dict[str, object], metric: str) -> tuple[object, dict[str, object]]:
    symbol = analytics["latest"]["kraken-futures"]["instruments"]["PI_ETHUSD"]
    return symbol[metric], symbol["flow_metric_validity"][metric]


class KrakenTradeFlowProjectionTests(unittest.TestCase):
    def test_22_trade_volume_not_qualified_zero_is_not_public_zero(self):
        result, persisted = apply_case(intelligence(), [trade(-1_000, trade_id=9)])
        for analytics in (result["analytics"], persisted):
            value, validity = projected_metric(analytics, "trade-volume")
            self.assertIsNone(value)
            self.assertIsNone(validity["value"])
            self.assertEqual(validity["native_latest"], [END, 0])
            self.assertEqual(validity["availability_status"], "NOT_QUALIFIED")
            self.assertEqual(validity["value_reconciliation_status"], "NOT_QUALIFIED")
            self.assertEqual(validity["metric_semantics_status"], "INSUFFICIENT_FOR_RAW_COMPARISON")

    def test_23_aggressor_not_qualified_zero_is_fail_closed_downstream(self):
        result, _ = apply_case(intelligence(), [trade(-1_000, trade_id=9)])
        value, validity = projected_metric(result["analytics"], "aggressor-differential")
        self.assertIsNone(value)
        self.assertEqual(validity["native_latest"], [END, 0])
        self.assertEqual(validity["availability_status"], "NOT_QUALIFIED")
        self.assertEqual(
            validity["metric_semantics_status"],
            "TAKER_SIDE_QUALIFIED_QUANTITY_UNIT_NOT_QUALIFIED",
        )

    def test_24_cvd_native_zero_state_stays_explicit_not_value_verified(self):
        result, _ = apply_case(intelligence(), [trade(-1_000, trade_id=9)])
        value, validity = projected_metric(result["analytics"], "cvd")
        self.assertIsNone(value)
        self.assertEqual(validity["native_latest"], [END, {"cvd": "0"}])
        self.assertEqual(validity["availability_status"], "NOT_QUALIFIED")
        self.assertEqual(validity["availability_reason"], "PROVIDER_NATIVE_CVD_NOT_RAW_VALUE_VERIFIED")
        self.assertEqual(
            validity["metric_semantics_status"],
            "PROVIDER_NATIVE_STATEFUL_DELTA_CONTRACT_NOT_QUALIFIED",
        )

    def test_25_trade_count_source_conflict_cannot_project_numeric_available(self):
        result, _ = apply_case(
            intelligence(trade_count=0),
            [trade(1_000, trade_id=1), trade(-1_000, trade_id=2)],
        )
        value, validity = projected_metric(result["analytics"], "trade-count")
        self.assertIsNone(value)
        self.assertFalse(validity["consumer_qualified"])
        self.assertEqual(validity["value_reconciliation_status"], "SOURCE_CONFLICT")
        self.assertEqual(validity["availability_status"], "UNAVAILABLE")
        self.assertEqual(validity["native_latest"], [END, 0])

    def test_26_valid_zero_trade_count_remains_available_zero(self):
        result, _ = apply_case(intelligence(trade_count=0), [trade(-1_000, trade_id=9)])
        value, validity = projected_metric(result["analytics"], "trade-count")
        self.assertEqual(value, [END, 0])
        self.assertEqual(validity["value"], [END, 0])
        self.assertTrue(validity["consumer_qualified"])
        self.assertEqual(validity["availability_status"], "AVAILABLE")
        self.assertEqual(validity["availability_reason"], "VALID_ZERO_NO_TRADES_IN_BUCKET")
        self.assertEqual(validity["value_reconciliation_status"], "MATCH")

    def test_27_nonzero_trade_count_match_remains_available(self):
        result, _ = apply_case(
            intelligence(trade_count=1),
            [trade(1_000, trade_id=1), trade(-1_000, trade_id=2)],
        )
        value, validity = projected_metric(result["analytics"], "trade-count")
        self.assertEqual(value, [END, 1])
        self.assertTrue(validity["consumer_qualified"])
        self.assertEqual(validity["value_reconciliation_status"], "MATCH")

    def test_28_misaligned_and_unknown_trade_count_fail_closed_with_classification(self):
        cases = (
            (intelligence(trade_count_timestamp=START), "MISALIGNED"),
            (intelligence(trade_count_semantics="UNKNOWN"), "UNKNOWN"),
        )
        for payload, expected_alignment in cases:
            with self.subTest(expected_alignment=expected_alignment):
                result, _ = apply_case(payload, [trade(-1_000, trade_id=9)])
                value, validity = projected_metric(result["analytics"], "trade-count")
                self.assertIsNone(value)
                self.assertFalse(validity["consumer_qualified"])
                self.assertEqual(validity["temporal_alignment_status"], expected_alignment)
                self.assertEqual(validity["value_reconciliation_status"], "NOT_QUALIFIED")

    def test_29_available_metric_metadata_separates_native_presence_from_qualified(self):
        result, _ = apply_case(intelligence(), [trade(-1_000, trade_id=9)])
        analytics = result["analytics"]
        provider = analytics["latest"]["kraken-futures"]
        native = provider["analytics_provider_native_metrics"]
        qualified = provider["analytics_consumer_qualified_metrics"]
        self.assertEqual(provider["analytics_available_metrics"], qualified)
        for metric in ("trade-volume", "aggressor-differential", "cvd"):
            self.assertIn(metric, native)
            self.assertNotIn(metric, qualified)
            self.assertNotIn(metric, analytics["analytics_available_metrics"])
        self.assertIn("trade-count", qualified)
        self.assertIn("trade-count", analytics["analytics_available_metrics"])

    def test_30_current_data_domain_resource_preserves_validity_envelope(self):
        _, persisted = apply_case(intelligence(), [trade(-1_000, trade_id=9)])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "analytics-source.json"
            source.write_text(json.dumps(persisted) + "\n", encoding="utf-8")
            output = root / "artifact"
            request = {
                "required_domains": ["ANALYTICS"],
                "required_series": [],
                "max_generation_age_seconds": 600,
                "current_policy": "FINALIZED_ONLY",
            }
            now = datetime.fromtimestamp((NOW + 1_000) / 1000, timezone.utc)
            with mock.patch.object(current_data_transport, "_domain_manifest_path", return_value=source):
                index = current_data_transport.build_resource_index(
                    request,
                    "a" * 64,
                    output_root=output,
                    now=now,
                )
            self.assertEqual(index["domains"][0]["status"], "PASS")
            copied = json.loads((output / "domains" / "analytics.json").read_text(encoding="utf-8"))
            value, validity = projected_metric(copied, "cvd")
            self.assertIsNone(value)
            self.assertEqual(validity["availability_status"], "NOT_QUALIFIED")
            self.assertEqual(validity["availability_reason"], "PROVIDER_NATIVE_CVD_NOT_RAW_VALUE_VERIFIED")
            self.assertEqual(validity["native_latest"], [END, {"cvd": "0"}])


if __name__ == "__main__":
    unittest.main()
