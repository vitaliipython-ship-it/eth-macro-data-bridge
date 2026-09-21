from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.history_access import (
    HistoryAccessError,
    compact,
    materialize_resolution_plan,
    rows_to_csv,
    rows_to_json,
)
from tools.history_consumer import read_history

STEP = 300_000
START = 1_789_491_600_000
OI = "derivatives.kraken-futures.PI_ETHUSD.open-interest"
VOLUME = "derivatives.kraken-futures.PI_ETHUSD.trade-volume"
FROM = "2026-09-15T17:00:00Z"
TO = "2026-09-15T17:45:00Z"
CUTOFF = "2026-09-15T18:15:00Z"


def encoded(value):
    return (json.dumps(value, separators=(",", ":")) + "\n").encode()
def generic_plan(raw: bytes, *, metric="trade-volume", records_end=START + 3 * STEP):
    plan = {
        "schema_version": "market-data-resolution-plan/1.0.0",
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {"route_policy": "bridge-contract.json"},
        "request": {"series_id": f"derivatives.kraken-futures.PI_ETHUSD.{metric}", "start_ms": START, "end_ms": records_end, "cutoff_ms": records_end},
        "series": {
            "series_id": f"derivatives.kraken-futures.PI_ETHUSD.{metric}",
            "profile_id": "kraken-futures.history.provider-limited.hot",
            "instrument": "PI_ETHUSD", "series": metric, "interval": None,
            "source_interval_or_metric": metric, "provider_id": "kraken-futures",
            "source_provider": "kraken-futures", "history_mode": "PROVIDER_LIMITED",
            "availability_status": "PROVIDER_HISTORY_LIMIT", "interval_ms": STEP,
        },
        "segments": [{
            "segment_id": "warm:test", "storage": "GIT_WARM_RESOURCE",
            "source_manifest_path": "derivatives/history-manifest.json",
            "resource_path": "metric.json", "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "first_timestamp_ms": START,
            "last_timestamp_ms": records_end - STEP, "read_start_ms": START,
            "read_end_ms": records_end, "source_provider": "kraken-futures",
            "instrument": "PI_ETHUSD", "source_interval_or_metric": metric,
        }],
    }
    plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
    return plan
def metric_payload(records, *, metric="trade-volume", provider="kraken-futures", instrument="PI_ETHUSD"):
    return {
        "schema_version": "1.0.0", "provider": provider, "instrument": instrument,
        "metric": metric, "resolution_seconds": 300, "records": records,
    }


class NonOhlcvReaderTests(unittest.TestCase):
    def test_kraken_oi_zero_gap_plan_materializes_losslessly(self):
        plan, payload, diagnostics, receipt = read_history(
            OI, FROM, TO, cutoff_utc=CUTOFF, output_format="json"
        )
        repeated_plan, repeated_payload, repeated_diagnostics, repeated_receipt = read_history(
            OI, FROM, TO, cutoff_utc=CUTOFF, output_format="json"
        )
        observations = json.loads(payload)
        # Historical predecessor evidence only: plan SHA
        # 9ae92836665d924be778c7a49b61016a8d4ea8b890e6e953a6f30a5a896270b3
        # belonged to the prior generated-resource snapshot and is intentionally not asserted.
        self.assertEqual(plan, repeated_plan)
        self.assertEqual(compact(plan), compact(repeated_plan))
        self.assertEqual(payload, repeated_payload)
        self.assertEqual(diagnostics, repeated_diagnostics)
        self.assertEqual(receipt["plan_sha256"], repeated_receipt["plan_sha256"])
        self.assertEqual(plan["schema_version"], "market-data-resolution-plan/1.0.0")
        self.assertEqual(plan["request"]["series_id"], OI)
        self.assertEqual(plan["series"]["series_id"], OI)
        self.assertEqual(plan["series"]["interval_ms"], STEP)
        self.assertEqual(len(plan["segments"]), 1)
        body = dict(plan)
        plan_sha256 = body.pop("plan_sha256")
        self.assertEqual(plan_sha256, hashlib.sha256(compact(body)).hexdigest())
        segment = plan["segments"][0]
        resource = Path(__file__).resolve().parents[2] / segment["resource_path"]
        resource_bytes = resource.read_bytes()
        self.assertEqual(segment["sha256"], hashlib.sha256(resource_bytes).hexdigest())
        self.assertEqual(segment["size_bytes"], len(resource_bytes))
        self.assertEqual(segment["source_provider"], "kraken-futures")
        self.assertEqual(receipt["current_policy"], "FINALIZED_ONLY")
        self.assertEqual(receipt["route"]["resolver"], "tools/capability_index.py")
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(diagnostics["gap_count"], 0)
        self.assertEqual(diagnostics["duplicates"], 0)
        self.assertEqual(len(observations), 9)
        self.assertGreater(len(observations[0]["value"]), 1)
        self.assertEqual(receipt["semantic_receipt"]["receipt_schema_version"], "history-access-receipt/2.0.0")

    def test_second_regular_metric_uses_same_generic_path(self):
        _plan, payload, diagnostics, _receipt = read_history(
            VOLUME, FROM, TO, cutoff_utc=CUTOFF, output_format="json"
        )
        observations = json.loads(payload)
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["gap_count"], 0)
        self.assertEqual(set(observations[0]), {"timestamp_ms", "value"})

    def test_generated_resource_refresh_rebinds_plan_without_weakening_integrity(self):
        records_a = [[START + i * STEP, str(i)] for i in range(3)]
        records_b = [[START + i * STEP, str(i + 10)] for i in range(3)]
        raw_a = encoded(metric_payload(records_a))
        raw_b = encoded(metric_payload(records_b))
        plan_a = generic_plan(raw_a)
        plan_b = generic_plan(raw_b)
        self.assertNotEqual(plan_a["segments"][0]["sha256"], plan_b["segments"][0]["sha256"])
        self.assertNotEqual(plan_a["plan_sha256"], plan_b["plan_sha256"])
        for raw, plan in ((raw_a, plan_a), (raw_b, plan_b)):
            with tempfile.TemporaryDirectory() as temp:
                Path(temp, "metric.json").write_bytes(raw)
                rows, diagnostics = materialize_resolution_plan(plan, root=Path(temp), mode="strict")
            self.assertEqual(len(rows), 3)
            self.assertEqual(diagnostics["gap_count"], 0)
            self.assertEqual(diagnostics["status"], "PASS")
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "metric.json").write_bytes(raw_b)
            with self.assertRaises(HistoryAccessError) as caught:
                materialize_resolution_plan(plan_a, root=Path(temp), mode="strict")
        self.assertEqual(caught.exception.code, "CHECKSUM_MISMATCH")

    def test_true_missing_observation_is_data_gap(self):
        records = [[START, "1"], [START + 2 * STEP, "3"]]
        raw = encoded(metric_payload(records))
        plan = generic_plan(raw)
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "metric.json").write_bytes(raw)
            with self.assertRaises(HistoryAccessError) as caught:
                materialize_resolution_plan(plan, root=Path(temp), mode="strict")
        self.assertEqual(caught.exception.code, "DATA_GAP")

    def test_identity_mismatch_fails_closed(self):
        records = [[START + i * STEP, str(i)] for i in range(3)]
        raw = encoded(metric_payload(records, metric="trade-count"))
        plan = generic_plan(raw, metric="trade-volume")
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "metric.json").write_bytes(raw)
            with self.assertRaises(HistoryAccessError) as caught:
                materialize_resolution_plan(plan, root=Path(temp), mode="strict")
        self.assertEqual(caught.exception.code, "MEMBER_NOT_FOUND")

    def test_payload_interval_mismatch_fails_closed(self):
        records = [[START + i * STEP, str(i)] for i in range(3)]
        payload = metric_payload(records)
        payload["resolution_seconds"] = 60
        raw = encoded(payload)
        plan = generic_plan(raw)
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "metric.json").write_bytes(raw)
            with self.assertRaises(HistoryAccessError) as caught:
                materialize_resolution_plan(plan, root=Path(temp), mode="strict")
        self.assertEqual(caught.exception.code, "ARCHIVE_INVALID")
    def test_consumer_receipt_digest_matches_generic_observations(self):
        _plan, payload, diagnostics, receipt = read_history(
            OI, FROM, TO, cutoff_utc=CUTOFF, output_format="json"
        )
        observations = json.loads(payload)
        semantic = receipt["semantic_receipt"]
        canonical = json.dumps(observations, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        self.assertEqual(semantic["observation_count"], diagnostics["rows"])
        self.assertEqual(semantic["output_sha256"], hashlib.sha256(canonical).hexdigest())

    def test_ohlcv_renderer_bytes_stay_legacy(self):
        rows = [(START, "1", "2", "0", "1.5", "10")]
        csv_payload = rows_to_csv(rows)
        json_payload = rows_to_json(rows)
        self.assertTrue(csv_payload.startswith("open_time,open,high,low,close,volume\n"))
        self.assertEqual(set(json.loads(json_payload)[0]), {"open_time", "open", "high", "low", "close", "volume"})

    def test_empty_generic_output_keeps_generic_schema(self):
        series = {"series": "trade-volume"}
        self.assertEqual(rows_to_csv([], series=series), "timestamp_ms,value_json\n")
        self.assertEqual(rows_to_json([], series=series), "[]\n")


if __name__ == "__main__":
    unittest.main()
