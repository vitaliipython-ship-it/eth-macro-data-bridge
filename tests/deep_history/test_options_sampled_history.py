from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from options_derivation import OPTIONS_COLUMNS, derive_options_analytics, options_derivation_policy_identity, validate_options_snapshot
from tools.history_access import HistoryAccessError
from tools.history_consumer import read_history, sampled_history
from tools.history_issue_request import HistoryIssueRequestError, parse_request_body
from tools.sampled_history import OPTIONS_SURFACE_CAPABILITY_ID, SampledHistoryError, assert_derivation_policy_match, discover_forward_capability, materialize_sampled_history, resolve_sampled_history

DAY_MS = 86_400_000


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _snapshot(ts: int, *, call_oi: str = "100", put_oi: str = "80", call_volume: str = "20", put_volume: str = "30") -> dict:
    rows = [
        [ts + 7 * DAY_MS, "100", "call", call_oi, call_volume, None, None, None, None, "60", "100", "ETH_USD", "0", "2000"],
        [ts + 7 * DAY_MS, "100", "put", put_oi, put_volume, None, None, None, None, "62", "100", "ETH_USD", "0", "1800"],
    ]
    selected = []
    for days, atm_call, atm_put, call_iv, put_iv in ((7, "60", "62", "64", "61"), (30, "55", "57", "59", "54"), (90, "50", "52", "53", "49")):
        expiry = ts + days * DAY_MS
        selected.extend([
            {"instrument_name": f"ETH-{days}-ATM-C", "expiry": expiry, "target_days": days, "selection": "atm", "target_delta": None, "actual_dte": float(days), "strike": 100, "option_type": "call", "greeks": {"delta": 0.5}, "mark_iv": atm_call, "underlying_price": 100, "underlying_index": "ETH_USD", "interest_rate": 0},
            {"instrument_name": f"ETH-{days}-ATM-P", "expiry": expiry, "target_days": days, "selection": "atm", "target_delta": None, "actual_dte": float(days), "strike": 100, "option_type": "put", "greeks": {"delta": -0.5}, "mark_iv": atm_put, "underlying_price": 100, "underlying_index": "ETH_USD", "interest_rate": 0},
            {"instrument_name": f"ETH-{days}-25D-C", "expiry": expiry, "target_days": days, "selection": "25d", "target_delta": "0.25", "actual_dte": float(days), "strike": 110, "option_type": "call", "greeks": {"delta": 0.25}, "mark_iv": call_iv, "underlying_price": 100, "underlying_index": "ETH_USD", "interest_rate": 0},
            {"instrument_name": f"ETH-{days}-25D-P", "expiry": expiry, "target_days": days, "selection": "25d", "target_delta": "-0.25", "actual_dte": float(days), "strike": 90, "option_type": "put", "greeks": {"delta": -0.25}, "mark_iv": put_iv, "underlying_price": 100, "underlying_index": "ETH_USD", "interest_rate": 0},
        ])
    return {"schema_version": "1.0.0", "provider": "deribit", "timestamp_ms": ts, "scope": "FULL_ACTIVE_CHAIN_COMPACT", "instrument_key": "ETH-{expiration_timestamp}-{strike}-{C|P}", "discovered_option_count": len(rows), "columns": list(OPTIONS_COLUMNS), "options": rows, "selected_greeks": selected}


def _write(root: Path, payload: dict) -> Path:
    ts = payload["timestamp_ms"]
    day = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y/%m/%d")
    path = root / "options" / "snapshots" / day / f"{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    history_path = root / "options" / "history-manifest.json"
    current_path = root / "options" / "manifest.json"
    existing_first = ts
    if history_path.exists():
        existing_first = min(existing_first, int(json.loads(history_path.read_text())["options_forward_snapshot_first_timestamp_ms"]))
    history_path.write_text(json.dumps({"schema_version": "1.0.0", "options_forward_snapshot_archive": "PASS", "options_forward_snapshot_first_timestamp_ms": existing_first}, separators=(",", ":")) + "\n", encoding="utf-8")
    latest_ts = ts
    if current_path.exists():
        current = json.loads(current_path.read_text())
        previous = (((current.get("providers") or {}).get("deribit") or {}).get("latest_surface"))
        if previous:
            latest_ts = max(latest_ts, int(Path(previous).stem))
    latest_day = datetime.fromtimestamp(latest_ts / 1000, timezone.utc).strftime("%Y/%m/%d")
    current_path.write_text(json.dumps({"schema_version": "1.0.0", "providers": {"deribit": {"latest_surface": f"options/snapshots/{latest_day}/{latest_ts}.json"}}}, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


def _capability() -> dict:
    return {"capability_id": OPTIONS_SURFACE_CAPABILITY_ID, "domain": "options", "history_mode": "FORWARD_ONLY", "availability_status": "PASS", "historical_backfill_status": "UNAVAILABLE_BY_PROVIDER", "manifest_path": "options/manifest.json"}


class OptionsSampledHistoryContractTests(unittest.TestCase):
    def test_t01_capability_discovery(self):
        row = discover_forward_capability(OPTIONS_SURFACE_CAPABILITY_ID)
        self.assertEqual(row["capability_id"], OPTIONS_SURFACE_CAPABILITY_ID)
        self.assertEqual(row["history_mode"], "FORWARD_ONLY")
        self.assertEqual(row["availability_status"], "PASS")

    def test_t02_at_or_before_selection(self):
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp)
            for ts in (1_780_000_000_000, 1_780_003_600_000, 1_780_007_200_000): _write(root, _snapshot(ts))
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(1_780_005_400_000), repo_root=root)
            self.assertEqual(plan["selection"]["selected_observation_timestamp_ms"], 1_780_003_600_000)
            self.assertLessEqual(plan["selection"]["selected_observation_timestamp_ms"], plan["request"]["target_ms"])
            self.assertFalse(plan["authority"]["raw_unbounded_directory_scan"])

    def test_t03_exact_target_hit(self):
        ts = 1_780_003_600_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, _snapshot(ts))
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts), repo_root=root)
            self.assertEqual(plan["selection"]["selected_observation_timestamp_ms"], ts)
            self.assertEqual(plan["selection"]["distance_to_target_ms"], 0)

    def test_t04_target_precedes_forward_archive(self):
        ts = 1_780_003_600_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, _snapshot(ts))
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts - 1), repo_root=root)
            self.assertEqual(plan["selection"]["availability_state"], "TARGET_PRECEDES_FORWARD_ARCHIVE")
            self.assertIsNone(plan["selection"]["resource_descriptor"])

    def test_t05_no_interpolation_or_future_selection(self):
        left, right = 1_780_000_000_000, 1_780_007_200_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, _snapshot(left)); _write(root, _snapshot(right))
            target = left + 6_000_000
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(target), repo_root=root)
            self.assertEqual(plan["selection"]["selected_observation_timestamp_ms"], left)
            self.assertNotEqual(plan["selection"]["selected_observation_timestamp_ms"], right)

    def test_t06_canonical_snapshot_validation_and_integrity(self):
        ts = 1_780_003_600_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); path = _write(root, _snapshot(ts))
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts), repo_root=root)
            tampered = _snapshot(ts); tampered["provider"] = "other"
            path.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
            with self.assertRaises(SampledHistoryError) as caught: materialize_sampled_history(plan, repo_root=root)
            self.assertEqual(caught.exception.availability_state, "SEMANTIC_VALIDATION_FAILED")

    def test_t07_current_historical_derivation_parity_and_source_binding(self):
        payload = _snapshot(1_780_003_600_000); current = derive_options_analytics(payload)
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, payload)
            plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(payload["timestamp_ms"]), repo_root=root)
            _snap, historical, _diag = materialize_sampled_history(plan, repo_root=root)
        self.assertEqual(current, historical)
        source = Path("src/intelligence.py").read_text(encoding="utf-8")
        collect_options_source = source.split("def collect_options", 1)[1].split("def collect_deribit_perpetual", 1)[0]
        self.assertIn("analytics=derive_options_analytics(snapshot_payload)", collect_options_source)
        self.assertNotIn('analytics={"total_call_oi"', collect_options_source)
        self.assertEqual(current["derivation_policy_sha256"], options_derivation_policy_identity()["derivation_policy_sha256"])

    def test_t08_options_7d_30d_90d_metrics(self):
        analytics = derive_options_analytics(_snapshot(1_780_003_600_000))
        for days in (7, 30, 90):
            self.assertIsNotNone(analytics[f"atm_iv_{days}d"]); self.assertIsNotNone(analytics[f"actual_dte_{days}d"])
            self.assertIn(f"25d_{days}d", analytics); self.assertIn("risk_reversal", analytics[f"25d_{days}d"]); self.assertIn("butterfly", analytics[f"25d_{days}d"])

    def test_t09_oi_volume_aggregates(self):
        analytics = derive_options_analytics(_snapshot(1_780_003_600_000, call_oi="100", put_oi="80", call_volume="20", put_volume="30"))
        self.assertEqual(analytics["total_call_oi"], "100"); self.assertEqual(analytics["total_put_oi"], "80")
        self.assertEqual(analytics["put_call_oi_ratio"], "0.8"); self.assertEqual(analytics["put_call_volume_ratio"], "1.5")

    def test_t10_historical_as_of_uses_snapshot_timestamp_and_persisted_expiries(self):
        ts = 1_780_003_600_000; payload = _snapshot(ts)
        analytics = derive_options_analytics(payload)
        self.assertEqual(analytics["actual_dte_7d"], 7.0)
        self.assertEqual(validate_options_snapshot(payload)["timestamp_ms"], ts)

    def test_t11_deterministic_repeat_read(self):
        ts = 1_780_003_600_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, _snapshot(ts))
            first = sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts), repo_root=root); second = sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts), repo_root=root)
        self.assertEqual(first[0]["plan_sha256"], second[0]["plan_sha256"]); self.assertEqual(first[1], second[1]); self.assertEqual(first[3]["semantic_receipt_sha256"], second[3]["semantic_receipt_sha256"])

    def test_t12_existing_series_history_regression(self):
        plan = {"plan_sha256": "a" * 64, "request": {"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h", "start_ms": 1_704_067_200_000, "end_ms": 1_704_070_800_000, "cutoff_ms": None}}
        rows = [(1_704_067_200_000, "1", "2", "0.5", "1.5", "10")]
        diagnostics = {"requested_start": "2024-01-01T00:00:00Z", "requested_end": "2024-01-01T01:00:00Z", "status": "PASS", "rows": 1, "expected_rows": 1, "gap_count": 0, "duplicates": 0, "sources": []}
        with patch("tools.history_consumer.resolve_capability", return_value=plan), patch("tools.history_consumer.materialize_resolution_plan", return_value=(rows, diagnostics)):
            returned_plan, payload, returned_diagnostics, receipt = read_history("spot.binance-spot.ETHUSDT.ohlcv.1h", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z")
        self.assertIs(returned_plan, plan); self.assertIs(returned_diagnostics, diagnostics); self.assertIn("2024-01-01T00:00:00Z", payload); self.assertEqual(receipt["status"], "PASS")

    def test_t13_hosted_transport_xor_sampled_form(self):
        sampled = parse_request_body(json.dumps({"capability_id": OPTIONS_SURFACE_CAPABILITY_ID, "target_utc": "2026-09-03T12:00:00Z", "selection_policy": "AT_OR_BEFORE", "output_format": "json"}))
        self.assertEqual(sampled["selection_policy"], "AT_OR_BEFORE")
        series = parse_request_body(json.dumps({"series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h", "from_utc": "2026-09-01T00:00:00Z", "to_utc": "2026-09-02T00:00:00Z"}))
        self.assertEqual(series["mode"], "strict")
        with self.assertRaises(HistoryIssueRequestError): parse_request_body(json.dumps({"series_id": "x", "from_utc": "2026-09-01T00:00:00Z", "to_utc": "2026-09-02T00:00:00Z", "capability_id": OPTIONS_SURFACE_CAPABILITY_ID, "target_utc": "2026-09-03T12:00:00Z"}))
        workflow = Path(".github/workflows/history-consumer-read.yml").read_text(encoding="utf-8")
        self.assertIn("request_kind == 'SAMPLED'", workflow); self.assertIn("tools/history_consumer.py sampled", workflow)

    def test_t14_physical_input_rejection(self):
        for key, value in (("resource_path", "options/snapshots/x.json"), ("asset_name", "x.json"), ("url", "https://example.invalid"), ("sha", "a" * 64)):
            with self.subTest(key=key), self.assertRaises(HistoryIssueRequestError): parse_request_body(json.dumps({"capability_id": OPTIONS_SURFACE_CAPABILITY_ID, "target_utc": "2026-09-03T12:00:00Z", key: value}))

    def test_t15_transport_failure_not_data_gap(self):
        ts = 1_780_003_600_000
        with tempfile.TemporaryDirectory() as temp, patch("tools.sampled_history.discover_forward_capability", return_value=_capability()):
            root = Path(temp); _write(root, _snapshot(ts)); plan = resolve_sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(ts), repo_root=root)
            with patch("tools.sampled_history.history_access._v1._warm_bytes", side_effect=HistoryAccessError("PARTITION_NOT_FOUND", "simulated transport failure")):
                with self.assertRaises(SampledHistoryError) as caught: materialize_sampled_history(plan, repo_root=root)
        self.assertEqual(caught.exception.availability_state, "HISTORY_EXECUTION_GAP"); self.assertNotEqual(caught.exception.availability_state, "DATA_GAP")

    def test_derivation_policy_match_gate(self):
        analytics = derive_options_analytics(_snapshot(1_780_003_600_000)); identity = assert_derivation_policy_match([{"analytics": analytics}, {"analytics": dict(analytics)}])
        self.assertEqual(identity["derivation_policy_sha256"], analytics["derivation_policy_sha256"])
        mismatch = dict(analytics); mismatch["derivation_policy_version"] = "9.9.9"
        with self.assertRaises(SampledHistoryError) as caught: assert_derivation_policy_match([{"analytics": analytics}, {"analytics": mismatch}])
        self.assertEqual(caught.exception.availability_state, "DERIVATION_VERSION_MISMATCH")


if __name__ == "__main__": unittest.main()
