from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import history_access_v2

from multi_instrument_substrate import (
    AcquisitionWindow,
    InstrumentConfig,
    StaticRowsAdapter,
    aggregate_ohlcv,
    build_nonproduction_resolution_plan,
    load_repository_config,
    run_acquisition,
    server_config_from_environment,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "contracts" / "free-multi-instrument-integration-substrate-v1.json"


def config(
    *,
    provider="synthetic-fx",
    instrument="EURUSD",
    subject="FX:EURUSD",
    market_type="SPOT",
    series_kind="OHLCV",
    coverage="FIXED_GRID",
    granularity="1m",
    interval_ms=60_000,
    source_timezone="UTC",
    source_time_kind="ISO8601",
    session_kind="WEEKEND_CLOSE",
    series_id="nonprod.synthetic.EURUSD.ohlcv.1m",
):
    return InstrumentConfig(
        provider_id=provider,
        provider_instrument_id=instrument,
        economic_subject_id=subject,
        market_type=market_type,
        price_semantics="TEST_PRICE",
        granularity=granularity,
        interval_ms=interval_ms,
        series_kind=series_kind,
        coverage_semantics=coverage,
        source_timezone=source_timezone,
        source_time_kind=source_time_kind,
        session_calendar_ref=f"{provider.upper()}_TEST_SESSION",
        session_kind=session_kind,
        acquisition_method="STATIC_TEST",
        source_provenance="NON_VENDOR_TEST_FIXTURE",
        adapter="STATIC_ROWS",
        series_id=series_id,
        enabled_for_live_probe=False,
    )


def candles(count, *, start="2026-09-01T00:00:00Z", step_seconds=60):
    from datetime import datetime, timedelta, timezone

    base = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(timezone.utc)
    rows = []
    for index in range(count):
        ts = base + timedelta(seconds=index * step_seconds)
        price = 100 + index
        rows.append(
            {
                "source_time": ts.isoformat().replace("+00:00", "Z"),
                "open": str(price),
                "high": str(price + 2),
                "low": str(price - 1),
                "close": str(price + 1),
                "volume": "1.5",
            }
        )
    return rows


class MultiInstrumentSubstrateTests(unittest.TestCase):
    def test_01_repository_config_is_nonproduction_and_multi_provider(self):
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "NON_PRODUCTION_INTEGRATION_SUBSTRATE")
        self.assertFalse(payload["activation"]["new_production_provider_active"])
        self.assertFalse(payload["activation"]["production_capability_advertisement"])
        loaded = load_repository_config(CONFIG_PATH)
        self.assertGreaterEqual(len({row.provider_id for row in loaded.values()}), 3)
        self.assertGreaterEqual(len(loaded), 4)
        self.assertIn("FX:EURUSD", {row.economic_subject_id for row in loaded.values()})
        self.assertIn("COMMODITY:WTI_CRUDE_OIL", {row.economic_subject_id for row in loaded.values()})
        self.assertIn("COMMODITY:GOLD", {row.economic_subject_id for row in loaded.values()})
        for item in loaded.values():
            self.assertNotEqual(item.economic_subject_id, item.provider_instrument_id)

    def test_02_one_generic_pipeline_handles_multiple_instruments(self):
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:03:00Z")
        fx = config()
        gold = config(
            provider="synthetic-metal",
            instrument="XAUUSD",
            subject="COMMODITY:GOLD",
            market_type="CFD",
            series_id="nonprod.synthetic.XAUUSD.ohlcv.1m",
            session_kind="DAILY_BREAK",
        )
        with tempfile.TemporaryDirectory() as temp:
            first = run_acquisition(fx, window, StaticRowsAdapter(candles(3)), staging_root=Path(temp))
            second = run_acquisition(gold, window, StaticRowsAdapter(candles(3)), staging_root=Path(temp))
        self.assertEqual(first["receipt"]["record_count"], 3)
        self.assertEqual(second["receipt"]["record_count"], 3)
        self.assertNotEqual(first["receipt"]["configuration_fingerprint"], second["receipt"]["configuration_fingerprint"])

    def test_03_timezone_normalization_is_explicit_and_utc(self):
        cfg = config(source_timezone="Europe/Kyiv", source_time_kind="ISO8601")
        rows = [
            {
                "source_time": "2026-09-01T03:00:00",
                "open": "100",
                "high": "102",
                "low": "99",
                "close": "101",
                "volume": "1",
            }
        ]
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:01:00Z")
        with tempfile.TemporaryDirectory() as temp:
            result = run_acquisition(cfg, window, StaticRowsAdapter(rows), staging_root=Path(temp))
        record = result["normalized_payload"]["records"][0]
        self.assertEqual(record[0], 1788220800000)
        self.assertEqual(result["receipt"]["source_timezone"], "Europe/Kyiv")

    def test_04_idempotent_reingestion_and_changed_raw_generation(self):
        cfg = config()
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:03:00Z")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = run_acquisition(cfg, window, StaticRowsAdapter(candles(3)), staging_root=root)
            b = run_acquisition(cfg, window, StaticRowsAdapter(candles(3)), staging_root=root)
            changed_rows = candles(3)
            changed_rows[1]["close"] = "150"
            changed_rows[1]["high"] = "151"
            c = run_acquisition(cfg, window, StaticRowsAdapter(changed_rows), staging_root=root)
            self.assertEqual(a["receipt"]["generation_id"], b["receipt"]["generation_id"])
            self.assertEqual(a["receipt"]["normalized_fingerprint"], b["receipt"]["normalized_fingerprint"])
            self.assertNotEqual(a["receipt"]["generation_id"], c["receipt"]["generation_id"])
            self.assertTrue(Path(a["normalized_path"]).exists())
            self.assertTrue(Path(c["normalized_path"]).exists())

    def test_05_duplicate_nonfinite_and_invalid_ohlc_fail_closed(self):
        cfg = config()
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:02:00Z")
        duplicate = candles(1) + candles(1)
        nonfinite = candles(1)
        nonfinite[0]["open"] = "NaN"
        invalid = candles(1)
        invalid[0]["high"] = "50"
        for rows in (duplicate, nonfinite, invalid):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    run_acquisition(cfg, window, StaticRowsAdapter(rows), staging_root=Path(temp))

    def test_06_gap_is_observed_not_synthetically_filled(self):
        cfg = config()
        rows = candles(3)
        del rows[1]
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:03:00Z")
        with tempfile.TemporaryDirectory() as temp:
            result = run_acquisition(cfg, window, StaticRowsAdapter(rows), staging_root=Path(temp))
        self.assertEqual(result["receipt"]["quality"]["raw_gaps"], 1)
        self.assertEqual(result["receipt"]["quality"]["normalized_gaps"], 1)
        self.assertEqual(result["receipt"]["quality"]["gap_classes"], ["UNKNOWN_GAP"])
        self.assertEqual(result["receipt"]["record_count"], 2)

    def test_07_m1_to_m5_h1_h4_are_deterministic_without_fill(self):
        source = []
        for index, row in enumerate(candles(240)):
            source.append(
                {
                    "timestamp_ms": 1788220800000 + index * 60_000,
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                }
            )
        m5_a = aggregate_ohlcv(source, source_interval_ms=60_000, target_interval_ms=300_000, bucket_anchor_ms=1788220800000)
        m5_b = aggregate_ohlcv(list(reversed(source)), source_interval_ms=60_000, target_interval_ms=300_000, bucket_anchor_ms=1788220800000)
        h1 = aggregate_ohlcv(source, source_interval_ms=60_000, target_interval_ms=3_600_000, bucket_anchor_ms=1788220800000)
        h4 = aggregate_ohlcv(source, source_interval_ms=60_000, target_interval_ms=14_400_000, bucket_anchor_ms=1788220800000)
        self.assertEqual(m5_a, m5_b)
        self.assertEqual(len(m5_a), 48)
        self.assertEqual(len(h1), 4)
        self.assertEqual(len(h4), 1)
        with self.assertRaises(ValueError):
            aggregate_ohlcv(source[:-1], source_interval_ms=60_000, target_interval_ms=14_400_000, bucket_anchor_ms=1788220800000)

    def test_08_existing_resolution_plan_v2_reader_materializes_nonproduction_ohlcv(self):
        cfg = config()
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-01T00:03:00Z")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_acquisition(cfg, window, StaticRowsAdapter(candles(3)), staging_root=root)
            plan = build_nonproduction_resolution_plan(cfg, result)
            observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
        self.assertEqual(len(observations), 3)
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["receipt"]["observation_count"], 3)
        self.assertFalse(plan["authority"]["capability_advertisement"])
        self.assertFalse(plan["authority"]["second_resolver"])

    def test_09_existing_reader_materializes_second_asset_class_scalar(self):
        cfg = config(
            provider="synthetic-reference",
            instrument="WTI-REF",
            subject="COMMODITY:WTI_CRUDE_OIL",
            market_type="REFERENCE_SERIES",
            series_kind="SCALAR_TIME_SERIES",
            granularity="1d",
            interval_ms=86_400_000,
            series_id="nonprod.synthetic.WTI.reference.1d",
            session_kind="DECLARED_SESSION",
        )
        rows = [
            {"source_time": "2026-09-01T00:00:00Z", "value": "80.1"},
            {"source_time": "2026-09-02T00:00:00Z", "value": "80.2"},
            {"source_time": "2026-09-03T00:00:00Z", "value": "80.3"},
        ]
        window = AcquisitionWindow("2026-09-01T00:00:00Z", "2026-09-04T00:00:00Z")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_acquisition(cfg, window, StaticRowsAdapter(rows), staging_root=root)
            plan = build_nonproduction_resolution_plan(cfg, result)
            observations, diagnostics = history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
        self.assertEqual([row["value"]["value"] for row in observations], ["80.1", "80.2", "80.3"])
        self.assertEqual(diagnostics["receipt"]["observation_count"], 3)

    def test_10_server_configuration_is_environment_driven(self):
        with patch.dict(
            os.environ,
            {
                "AIFE_MULTI_INSTRUMENT_CONFIG": str(CONFIG_PATH),
                "AIFE_MULTI_INSTRUMENT_STAGING_ROOT": "/tmp/aife-market-staging",
            },
            clear=False,
        ):
            config_path, staging_root = server_config_from_environment()
        self.assertEqual(config_path, CONFIG_PATH)
        self.assertEqual(staging_root, Path("/tmp/aife-market-staging"))

    def test_11_production_capability_index_has_no_nonprod_series(self):
        index = json.loads((ROOT / "history" / "capability-index.json").read_text(encoding="utf-8"))
        serialized = json.dumps(index, sort_keys=True)
        self.assertNotIn("nonprod.", serialized)
        self.assertNotIn("DCOILWTICO", serialized)
        self.assertNotIn("XAUUSD", serialized)

    def test_12_dukascopy_is_candidate_not_live_or_canonical(self):
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        dukascopy = payload["providers"]["dukascopy"]
        self.assertFalse(dukascopy["production_canonical_authority"])
        self.assertFalse(dukascopy["physical_live_probe_enabled"])
        self.assertEqual(dukascopy["preferred_acquisition_method"], "OFFICIAL_JFOREX_API")
        configured = [row for row in payload["instruments"] if row["provider_id"] == "dukascopy"]
        self.assertTrue(configured)
        self.assertTrue(all(not row["enabled_for_live_probe"] for row in configured))


if __name__ == "__main__":
    unittest.main()
