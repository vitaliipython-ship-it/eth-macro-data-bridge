from __future__ import annotations

import unittest

from tools.current_data_transport import CurrentDataTransportError
from tools.current_data_request_scope import (
    evaluate_request_satisfaction,
    validate_flow_metric_envelope,
    validate_kraken_generation_integrity,
)


def flow_metric(metric_name, *, availability, reconciliation, consumer_qualified, latest=None, native_latest=None, reason, freshness="LIVE_USABLE", age=10):
    semantics = {
        "trade-count": "QUALIFIED_DIRECT_EXECUTION_COUNT",
        "trade-volume": "INSUFFICIENT_FOR_RAW_COMPARISON",
        "aggressor-differential": "TAKER_SIDE_QUALIFIED_QUANTITY_UNIT_NOT_QUALIFIED",
        "cvd": "PROVIDER_NATIVE_STATEFUL_DELTA_CONTRACT_NOT_QUALIFIED",
    }[metric_name]
    metric = {
        "more": False,
        "data_age_seconds": age,
        "freshness_status": freshness,
        "latest": latest,
        "native_latest": native_latest,
        "availability_status": availability,
        "availability_reason": reason,
        "value_reconciliation_status": reconciliation,
        "temporal_alignment_status": "ALIGNED",
        "metric_semantics_status": semantics,
        "feed_observed": True,
        "coverage_complete": True,
        "raw_observed_value": None,
        "native_observed_value": None if native_latest is None else native_latest[1],
    }
    projection = {
        "value": latest if consumer_qualified else None,
        "native_latest": native_latest,
        "availability_status": availability,
        "availability_reason": reason,
        "metric_semantics_status": semantics,
        "value_reconciliation_status": reconciliation,
        "temporal_alignment_status": "ALIGNED",
        "consumer_qualified": consumer_qualified,
    }
    return metric, projection


def valid_zero_trade_count():
    metric, projection = flow_metric(
        "trade-count", availability="AVAILABLE", reconciliation="MATCH", consumer_qualified=True,
        latest=[1000, 0], native_latest=[1000, 0], reason="VALID_ZERO_NO_TRADES_IN_BUCKET",
    )
    metric["raw_observed_value"] = 0
    metric["native_observed_value"] = 0
    return metric, projection


def source_conflict_trade_count():
    return flow_metric(
        "trade-count", availability="UNAVAILABLE", reconciliation="SOURCE_CONFLICT", consumer_qualified=False,
        latest=None, native_latest=[1000, 7], reason="RAW_NATIVE_TRADE_COUNT_SOURCE_CONFLICT",
        freshness="UNAVAILABLE", age=10,
    )


def not_qualified(metric_name):
    native_value = {"cvd": "10"} if metric_name == "cvd" else "3"
    return flow_metric(
        metric_name, availability="NOT_QUALIFIED", reconciliation="NOT_QUALIFIED", consumer_qualified=False,
        latest=[1000, native_value], native_latest=[1000, native_value],
        reason={
            "trade-volume": "RAW_SIZE_TO_ANALYTICS_BASE_VOLUME_UNIT_NOT_QUALIFIED",
            "aggressor-differential": "AGGRESSOR_SIGN_QUALIFIED_RAW_SIZE_UNIT_NOT_QUALIFIED",
            "cvd": "PROVIDER_NATIVE_CVD_NOT_RAW_VALUE_VERIFIED",
        }[metric_name],
    )


def current_fixture(*, conflict=False, stale_regular=False):
    tc_metric, tc_projection = source_conflict_trade_count() if conflict else valid_zero_trade_count()
    tv_metric, tv_projection = not_qualified("trade-volume")
    ag_metric, ag_projection = not_qualified("aggressor-differential")
    cvd_metric, cvd_projection = not_qualified("cvd")
    open_interest = {
        "more": False,
        "data_age_seconds": 1900 if stale_regular else 10,
        "freshness_status": "STALE_FOR_CURRENT" if stale_regular else "LIVE_USABLE",
        "latest": [1000, "100"],
    }
    derivatives = {"providers": {"kraken-futures": {"status": "PASS", "instruments": {"PI_XBTUSD": {"metrics": {
        "trade-count": tc_metric,
        "trade-volume": tv_metric,
        "aggressor-differential": ag_metric,
        "cvd": cvd_metric,
        "open-interest": open_interest,
    }}}}}}
    analytics = {"latest": {"kraken-futures": {"instruments": {"PI_XBTUSD": {"flow_metric_validity": {
        "trade-count": tc_projection,
        "trade-volume": tv_projection,
        "aggressor-differential": ag_projection,
        "cvd": cvd_projection,
    }}}}}}
    return derivatives, analytics


def spot_request():
    return {
        "required_series": [
            {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m", "latest_bars": 512},
            {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.15m", "latest_bars": 256},
            {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h", "latest_bars": 256},
            {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.4h", "latest_bars": 128},
        ],
        "required_domains": [],
    }


def index_for(request, domains=None):
    series = [{
        "series_id": item["series_id"],
        "status": "PASS",
        "availability": "AVAILABLE",
        "finality": "FINALIZED",
        "rows": item["latest_bars"],
        "expected_rows": item["latest_bars"],
        "gap_count": 0,
        "duplicates": 0,
    } for item in request["required_series"]]
    return {"domains": list(domains or []), "series": series}


class FreshCurrentRequestScopeQualificationTests(unittest.TestCase):
    def _integrity(self, derivatives, analytics):
        return validate_kraken_generation_integrity(derivatives["providers"]["kraken-futures"], analytics)

    def test_A_spot_only_unrelated_source_conflict_passes(self):
        derivatives, analytics = current_fixture(conflict=True)
        integrity = self._integrity(derivatives, analytics)
        request = spot_request()
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(integrity["generation_integrity_status"], "PASS")
        self.assertEqual(result["request_satisfaction_status"], "PASS")
        self.assertGreaterEqual(result["unrequested_degraded_resource_count"], 1)
        projection = analytics["latest"]["kraken-futures"]["instruments"]["PI_XBTUSD"]["flow_metric_validity"]["trade-count"]
        self.assertFalse(projection["consumer_qualified"])
        self.assertIsNone(projection["value"])

    def test_B_requested_source_conflict_fails_request_not_integrity(self):
        derivatives, analytics = current_fixture(conflict=True)
        integrity = self._integrity(derivatives, analytics)
        request = {"required_series": [{"series_id": "derivatives.kraken-futures.PI_XBTUSD.trade-count", "latest_bars": 1}], "required_domains": []}
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(integrity["generation_integrity_status"], "PASS")
        self.assertEqual(result["request_satisfaction_status"], "FAIL")
        self.assertEqual(result["unsatisfied_required_resource_count"], 1)
        self.assertFalse(result["requested_current_qualification"][request["required_series"][0]["series_id"]]["consumer_qualified"])

    def test_C_unrelated_not_qualified_cvd_does_not_poison_spot(self):
        derivatives, analytics = current_fixture()
        integrity = self._integrity(derivatives, analytics)
        request = spot_request()
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(result["status"], "PASS")
        degraded_ids = {row["resource_id"] for row in result["unrequested_degraded_resources"]}
        self.assertIn("derivatives.kraken-futures.PI_XBTUSD.cvd", degraded_ids)

    def test_D_explicit_not_qualified_cvd_fails_request(self):
        derivatives, analytics = current_fixture()
        integrity = self._integrity(derivatives, analytics)
        request = {"required_series": [{"series_id": "derivatives.kraken-futures.PI_XBTUSD.cvd", "latest_bars": 1}], "required_domains": []}
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(result["request_satisfaction_status"], "FAIL")

    def test_E_valid_zero_remains_numeric_zero_and_passes(self):
        metric, projection = valid_zero_trade_count()
        result = validate_flow_metric_envelope("trade-count", metric, projection)
        self.assertTrue(result["consumer_qualified"])
        self.assertEqual(metric["latest"][1], 0)
        self.assertEqual(projection["value"][1], 0)

    def test_F_malformed_fail_closed_projection_fails_global_integrity(self):
        derivatives, analytics = current_fixture(conflict=True)
        projection = analytics["latest"]["kraken-futures"]["instruments"]["PI_XBTUSD"]["flow_metric_validity"]["trade-count"]
        projection["value"] = [1000, 7]
        with self.assertRaises(CurrentDataTransportError) as caught:
            self._integrity(derivatives, analytics)
        self.assertEqual(caught.exception.code, "FLOW_FAIL_CLOSED_PUBLIC_VALUE_PRESENT")

    def test_G_requested_stale_resource_fails_request(self):
        derivatives, analytics = current_fixture(stale_regular=True)
        integrity = self._integrity(derivatives, analytics)
        request = {"required_series": [{"series_id": "derivatives.kraken-futures.PI_XBTUSD.open-interest", "latest_bars": 1}], "required_domains": []}
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(result["request_satisfaction_status"], "FAIL")

    def test_H_unrequested_stale_resource_does_not_poison_spot(self):
        derivatives, analytics = current_fixture(stale_regular=True)
        integrity = self._integrity(derivatives, analytics)
        request = spot_request()
        result = evaluate_request_satisfaction(request, index_for(request), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(result["request_satisfaction_status"], "PASS")
        self.assertEqual(integrity["metric_qualification_status"], "DEGRADED")

    def test_I_global_structural_corruption_blocks_before_request_scope(self):
        derivatives, analytics = current_fixture()
        derivatives["providers"]["kraken-futures"]["instruments"]["PI_XBTUSD"]["metrics"]["trade-volume"]["more"] = True
        with self.assertRaises(CurrentDataTransportError) as caught:
            self._integrity(derivatives, analytics)
        self.assertEqual(caught.exception.code, "KRAKEN_MORE_INCOMPLETE")

    def test_J_broad_required_domain_does_not_make_all_metrics_hard_required(self):
        derivatives, analytics = current_fixture()
        integrity = self._integrity(derivatives, analytics)
        request = {"required_series": [], "required_domains": ["DERIVATIVES", "ANALYTICS"]}
        domains = [
            {"domain_id": "DERIVATIVES", "status": "PASS", "freshness": "FRESH"},
            {"domain_id": "ANALYTICS", "status": "PASS", "freshness": "FRESH"},
        ]
        result = evaluate_request_satisfaction(request, index_for(request, domains), derivatives_manifest=derivatives, analytics_manifest=analytics, global_integrity=integrity)
        self.assertEqual(result["request_satisfaction_status"], "PASS")
        self.assertGreater(result["unrequested_degraded_resource_count"], 0)
        self.assertFalse(result["broad_physical_acquisition_implies_broad_qualification"])
        self.assertFalse(result["request_aware_network_acquisition_implemented"])


if __name__ == "__main__":
    unittest.main()
