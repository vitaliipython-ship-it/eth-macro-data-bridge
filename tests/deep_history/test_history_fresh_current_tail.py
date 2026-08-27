from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import history_access
from tools.current_tail_admission import CurrentTailAdmissionError, bind_validated_tail, validate_descriptor
from tools.history_access_v2 import build_semantic_receipt

STEP = 300000
START = 1787823000000
SERIES_ID = "spot.binance-spot.ETHUSDT.ohlcv.5m"


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha_json(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def iso(ms):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalized_rows(start, count, price=100):
    return [
        {
            "open_time": iso(start + i * STEP),
            "open": str(price + i),
            "high": str(price + i + 1),
            "low": str(price + i - 1),
            "close": str(price + i) + ".5",
            "volume": "10",
        }
        for i in range(count)
    ]


def semantic_hash(rows):
    observations = []
    for row in rows:
        observations.append(
            {
                "timestamp_ms": int(__import__("datetime").datetime.fromisoformat(row["open_time"].replace("Z", "+00:00")).timestamp() * 1000),
                "value": {key: row[key] for key in ("open", "high", "low", "close", "volume")},
                "finality": "FINALIZED",
            }
        )
    return sha_json(observations)


def descriptor(resource_path, raw, first, last, *, finalized_cutoff=None, series_id=SERIES_ID):
    value = {
        "schema_version": "validated-fresh-current-tail/1.0.0",
        "authority_class": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "durable_history_authority": False,
        "actions_artifact_is_durable_history_authority": False,
        "current_data_agent_request": "PASS",
        "validation": "PASS",
        "current_analysis_allowed": True,
        "current_policy": "FINALIZED_ONLY",
        "series_id": series_id,
        "interval_ms": STEP,
        "first_timestamp_ms": first,
        "last_timestamp_ms": last,
        "finalized_cutoff_ms": finalized_cutoff if finalized_cutoff is not None else last + STEP,
        "generation_id": "1" * 64,
        "generated_at_utc": "2026-08-27T14:00:00Z",
        "known_at_utc": "2026-08-27T14:01:00Z",
        "control_plane_head": "a" * 40,
        "control_plane_tree": "b" * 40,
        "generation_manifest_sha256": "2" * 64,
        "resource_index_sha256": "3" * 64,
        "validation_summary_sha256": "4" * 64,
        "request_sha256": "5" * 64,
        "semantic_receipt_sha256": "6" * 64,
        "semantic_output_sha256": "7" * 64,
        "resolution_plan_sha256": "8" * 64,
        "resource_path": resource_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }
    value["descriptor_sha256"] = sha_json(value)
    return value


def warm_payload(rows):
    records = []
    for i, row in enumerate(rows):
        ts = START + i * STEP
        records.append([ts, row["open"], row["high"], row["low"], row["close"], row["volume"], ts + STEP - 1])
    return {
        "schema_version": "1.0.0",
        "provider": "binance",
        "symbol": "ETHUSDT",
        "interval": "5m",
        "columns": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms"],
        "records": records,
    }


def warm_segment(path, raw, left, right):
    return {
        "segment_id": "warm:test",
        "storage": "GIT_WARM_RESOURCE",
        "source_manifest_path": "history/manifest.json",
        "resource_path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "first_timestamp_ms": left,
        "last_timestamp_ms": right - STEP,
        "read_start_ms": left,
        "read_end_ms": right,
        "source_provider": "binance",
        "instrument": "ETHUSDT",
        "source_interval_or_metric": "5m",
    }


def mixed_plan(segments, start, end):
    plan = {
        "schema_version": "market-data-resolution-plan/1.0.0",
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {
            "route_policy": "bridge-contract.json",
            "capability_index": "history/capability-index.json",
            "cold_manifest": "history/release-manifest.json",
            "hot_manifest": "history/manifest.json",
            "validated_current_tail": "fresh-current-generation/1.0.0",
        },
        "request": {"series_id": SERIES_ID, "start_ms": start, "end_ms": end, "cutoff_ms": None},
        "series": {
            "series_id": SERIES_ID,
            "profile_id": "binance-spot.history.max-available.hot",
            "instrument": "ETHUSDT",
            "series": "ohlcv",
            "interval": "5m",
            "source_interval_or_metric": "5m",
            "provider_id": "binance-spot",
            "source_provider": "binance",
            "history_mode": "MAX_AVAILABLE",
            "availability_status": "PASS",
            "interval_ms": STEP,
        },
        "segments": sorted(segments, key=lambda row: (row["read_start_ms"], row["read_end_ms"], row["storage"], row["segment_id"])),
    }
    plan["plan_sha256"] = hashlib.sha256(history_access.compact(plan)).hexdigest()
    return plan


def current_segment(desc, left, right):
    return {
        "segment_id": "current:test",
        "storage": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "source_manifest_path": "fresh-current-generation/1.0.0",
        "resource_path": desc["resource_path"],
        "sha256": desc["sha256"],
        "size_bytes": desc["size_bytes"],
        "first_timestamp_ms": desc["first_timestamp_ms"],
        "last_timestamp_ms": desc["last_timestamp_ms"],
        "read_start_ms": left,
        "read_end_ms": right,
        "source_provider": "binance",
        "instrument": "ETHUSDT",
        "source_interval_or_metric": "5m",
        "authority_class": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "current_tail": desc,
    }


class CurrentTailAdmissionTests(unittest.TestCase):
    def _artifact(self, root: Path, *, analysis_allowed=True, series_id=SERIES_ID):
        artifact = root / "artifact"
        member = Path("series/exact/normalized.json")
        target = artifact / member
        target.parent.mkdir(parents=True)
        rows = normalized_rows(START, 4)
        raw = canonical(rows)
        target.write_bytes(raw)
        request = {
            "request_type": "FRESH_CURRENT",
            "required_series": [{"series_id": series_id, "latest_bars": 4}],
            "required_domains": [],
            "max_generation_age_seconds": 600,
            "current_policy": "FINALIZED_ONLY",
        }
        request_sha = sha_json(request)
        wrapper = {
            "schema_version": "fresh-current-agent-request/1.0.0",
            "contract_id": "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
            "contract_version": "1.0.0",
            "request": request,
            "request_sha256": request_sha,
        }
        row = {
            "domain_id": "SPOT",
            "resource_logical_id": f"latest-series:{series_id}:4",
            "series_id": series_id,
            "latest_bars": 4,
            "status": "PASS",
            "generated_at_utc": "2026-08-27T13:58:00Z",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "availability": "AVAILABLE",
            "freshness": "VALIDATED_CURRENT_GENERATION",
            "semantic_receipt_sha256": "6" * 64,
            "semantic_output_sha256": semantic_hash(rows),
            "resolution_plan_sha256": "8" * 64,
            "finality": "FINALIZED",
            "rows": 4,
            "expected_rows": 4,
            "gap_count": 0,
            "duplicates": 0,
            "artifact_member": member.as_posix(),
        }
        index = {
            "schema_version": "fresh-current-resource-index/1.0.0",
            "contract_id": "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
            "contract_version": "1.0.0",
            "request_sha256": request_sha,
            "follow_legacy_raw_url_for_ephemeral_data": False,
            "domains": [],
            "series": [row],
        }
        validation = {
            "schema_version": "fresh-current-validation-summary/1.0.0",
            "contract_id": "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
            "contract_version": "1.0.0",
            "status": "PASS",
            "request_sha256": request_sha,
        }
        identity_basis = {
            "contract_id": "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
            "contract_version": "1.0.0",
            "control_plane_head": "a" * 40,
            "collector_version": "0.4.0",
            "generated_at_utc": "2026-08-27T13:58:00Z",
            "requested_semantic_capabilities": {"required_domains": [], "required_series": request["required_series"]},
            "validated_domain_resources": [],
            "validated_series_resources": [{
                "series_id": series_id,
                "latest_bars": 4,
                "sha256": row["sha256"],
                "semantic_receipt_sha256": row["semantic_receipt_sha256"],
                "semantic_output_sha256": row["semantic_output_sha256"],
            }],
        }
        generation = {
            "schema_version": "fresh-current-generation/1.0.0",
            "contract_id": "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1",
            "contract_version": "1.0.0",
            "market_data_semantic_authority": "ETH_MACRO_DATA_BRIDGE",
            "actions_artifact_is_market_data_authority": False,
            "control_plane_head": "a" * 40,
            "control_plane_tree": "b" * 40,
            "collector_version": "0.4.0",
            "generation_mode": "FRESH_ACQUISITION",
            "generated_at_utc": "2026-08-27T13:58:00Z",
            "known_at_utc": "2026-08-27T14:01:00Z",
            "request_sha256": request_sha,
            "generation_id": sha_json(identity_basis),
            "resource_index_sha256": hashlib.sha256(canonical(index)).hexdigest(),
            "validation_summary_sha256": hashlib.sha256(canonical(validation)).hexdigest(),
            "on_demand_current_data_can_be_used_for_live_analysis": analysis_allowed,
        }
        generation["generation_manifest_sha256"] = sha_json(generation)
        transport = {
            "schema_version": "fresh-current-transport-receipt/1.0.0",
            "authority": "TRANSPORT_ONLY",
            "generation_id": generation["generation_id"],
            "generation_manifest_sha256": generation["generation_manifest_sha256"],
            "control_plane_head": generation["control_plane_head"],
            "control_plane_tree": generation["control_plane_tree"],
            "head_after": generation["control_plane_head"],
            "remote_repository_mutation": False,
            "git_commit": False,
            "git_push": False,
        }
        for path, value in (
            (artifact / "request.json", wrapper),
            (artifact / "resource-index.json", index),
            (artifact / "validation-summary.json", validation),
            (artifact / "current-generation.json", generation),
            (artifact / "transport-receipt.json", transport),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical(value))
        return artifact, generation

    def test_missing_generation_validation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); artifact, generation = self._artifact(root)
            (artifact / "validation-summary.json").unlink()
            with mock.patch("tools.current_tail_admission.validate_artifact", return_value=({}, generation)), self.assertRaises(CurrentTailAdmissionError):
                bind_validated_tail(artifact, series_id=SERIES_ID, interval_ms=STEP, cutoff_ms=None, repository_root=root)

    def test_current_analysis_allowed_no_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); artifact, generation = self._artifact(root, analysis_allowed=False)
            with mock.patch("tools.current_tail_admission.validate_artifact", return_value=({}, generation)), self.assertRaises(CurrentTailAdmissionError) as caught:
                bind_validated_tail(artifact, series_id=SERIES_ID, interval_ms=STEP, cutoff_ms=None, repository_root=root)
            self.assertEqual(caught.exception.code, "CURRENT_TAIL_ANALYSIS_NOT_ALLOWED")

    def test_wrong_series_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); artifact, generation = self._artifact(root, series_id="spot.binance-spot.BTCUSDT.ohlcv.5m")
            with mock.patch("tools.current_tail_admission.validate_artifact", return_value=({}, generation)), self.assertRaises(CurrentTailAdmissionError) as caught:
                bind_validated_tail(artifact, series_id=SERIES_ID, interval_ms=STEP, cutoff_ms=None, repository_root=root)
            self.assertEqual(caught.exception.code, "CURRENT_TAIL_WRONG_SERIES")

    def test_future_generation_point_in_time_leak_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); artifact, generation = self._artifact(root)
            cutoff = int(__import__("datetime").datetime.fromisoformat("2026-08-27T14:00:00+00:00").timestamp() * 1000)
            with mock.patch("tools.current_tail_admission.validate_artifact", return_value=({}, generation)), self.assertRaises(CurrentTailAdmissionError) as caught:
                bind_validated_tail(artifact, series_id=SERIES_ID, interval_ms=STEP, cutoff_ms=cutoff, repository_root=root)
            self.assertEqual(caught.exception.code, "CURRENT_TAIL_PIT_CUTOFF")

    def test_forged_generation_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); artifact, generation = self._artifact(root)
            generation["generation_id"] = "f" * 64
            generation["generation_manifest_sha256"] = sha_json({k:v for k,v in generation.items() if k != "generation_manifest_sha256"})
            transport = json.loads((artifact / "transport-receipt.json").read_text())
            transport["generation_id"] = generation["generation_id"]
            transport["generation_manifest_sha256"] = generation["generation_manifest_sha256"]
            (artifact / "current-generation.json").write_bytes(canonical(generation))
            (artifact / "transport-receipt.json").write_bytes(canonical(transport))
            with mock.patch("tools.current_tail_admission.validate_artifact", return_value=({}, generation)), self.assertRaises(CurrentTailAdmissionError) as caught:
                bind_validated_tail(artifact, series_id=SERIES_ID, interval_ms=STEP, cutoff_ms=None, repository_root=root)
            self.assertEqual(caught.exception.code, "CURRENT_TAIL_GENERATION_ID_MISMATCH")


class MixedReaderTests(unittest.TestCase):
    def _current_file(self, root: Path, rows):
        path = root / ".tail/current.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical(rows)
        path.write_bytes(raw)
        return path, raw

    def test_durable_only_preserves_existing_behavior(self):
        rows = normalized_rows(START, 2)
        raw = canonical(warm_payload(rows))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / "history/warm.json"; path.parent.mkdir(); path.write_bytes(raw)
            segment = warm_segment("history/warm.json", raw, START, START + 2 * STEP)
            plan = mixed_plan([segment], START, START + 2 * STEP)
            plan["authority"].pop("validated_current_tail")
            plan["plan_sha256"] = hashlib.sha256(history_access.compact({k:v for k,v in plan.items() if k != "plan_sha256"})).hexdigest()
            result, diagnostics = history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
        self.assertEqual(len(result), 2)
        self.assertNotIn("history_source_mode", diagnostics)

    def test_durable_plus_fresh_tail_and_mixed_prefix_pass(self):
        durable_rows = normalized_rows(START, 2)
        durable_raw = canonical(warm_payload(durable_rows))
        current_rows = normalized_rows(START + STEP, 4, price=101)
        current_rows[0] = durable_rows[1]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            warm = root / "history/warm.json"; warm.parent.mkdir(); warm.write_bytes(durable_raw)
            current, current_raw = self._current_file(root, current_rows)
            desc = descriptor(".tail/current.json", current_raw, START + STEP, START + 4 * STEP)
            segments = [
                warm_segment("history/warm.json", durable_raw, START, START + 2 * STEP),
                current_segment(desc, START + STEP, START + 5 * STEP),
            ]
            plan = mixed_plan(segments, START, START + 5 * STEP)
            result, diagnostics = history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
        self.assertEqual(len(result), 5)
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["gap_count"], 0)
        self.assertEqual(diagnostics["duplicates"], 0)
        self.assertEqual(diagnostics["deduplicated_identical_overlaps"], 1)
        self.assertTrue(diagnostics["durable_segment_present"])
        self.assertTrue(diagnostics["fresh_current_tail_present"])

    def test_tail_only_current_range_passes(self):
        rows = normalized_rows(START, 4)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _path, raw = self._current_file(root, rows)
            desc = descriptor(".tail/current.json", raw, START, START + 3 * STEP)
            plan = mixed_plan([current_segment(desc, START, START + 4 * STEP)], START, START + 4 * STEP)
            result, diagnostics = history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
        self.assertEqual(len(result), 4)
        self.assertFalse(diagnostics["durable_segment_present"])
        self.assertTrue(diagnostics["fresh_current_tail_present"])

    def test_open_bar_is_excluded_fail_closed(self):
        rows = normalized_rows(START, 3)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _path, raw = self._current_file(root, rows)
            desc = descriptor(".tail/current.json", raw, START, START + 2 * STEP, finalized_cutoff=START + 2 * STEP)
            plan = mixed_plan([current_segment(desc, START, START + 3 * STEP)], START, START + 3 * STEP)
            with self.assertRaises(history_access.HistoryAccessError) as caught:
                history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
            self.assertEqual(caught.exception.code, "INVALID_RESOLUTION_PLAN")

    def test_gap_inside_tail_strict_fails(self):
        rows = normalized_rows(START, 3)
        rows.pop(1)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _path, raw = self._current_file(root, rows)
            desc = descriptor(".tail/current.json", raw, START, START + 2 * STEP, finalized_cutoff=START + 3 * STEP)
            plan = mixed_plan([current_segment(desc, START, START + 3 * STEP)], START, START + 3 * STEP)
            with self.assertRaises(history_access.HistoryAccessError) as caught:
                history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
            self.assertEqual(caught.exception.code, "DATA_GAP")

    def test_overlap_conflict_fails_closed(self):
        durable_rows = normalized_rows(START, 2)
        durable_raw = canonical(warm_payload(durable_rows))
        current_rows = normalized_rows(START + STEP, 2, price=999)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); warm = root / "history/warm.json"; warm.parent.mkdir(); warm.write_bytes(durable_raw)
            _path, current_raw = self._current_file(root, current_rows)
            desc = descriptor(".tail/current.json", current_raw, START + STEP, START + 2 * STEP)
            plan = mixed_plan([
                warm_segment("history/warm.json", durable_raw, START, START + 2 * STEP),
                current_segment(desc, START + STEP, START + 3 * STEP),
            ], START, START + 3 * STEP)
            with self.assertRaises(history_access.HistoryAccessError) as caught:
                history_access.materialize_resolution_plan(plan, root=root, cache_dir=root / "cache")
            self.assertEqual(caught.exception.code, "OVERLAP_CONFLICT")

    def test_forged_descriptor_fails_closed(self):
        rows = normalized_rows(START, 1)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _path, raw = self._current_file(root, rows)
            desc = descriptor(".tail/current.json", raw, START, START)
            desc["generation_id"] = "f" * 64
            with self.assertRaises(CurrentTailAdmissionError):
                validate_descriptor(desc)

    def test_no_provider_fallback_in_history_resolver_or_reader(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "tools/history_access.py").read_text(encoding="utf-8") + (root / "tools/capability_index.py").read_text(encoding="utf-8")
        for forbidden in ("api.binance.com", "api.kraken.com", "deribit.com/api", "urllib.request.Request"):
            self.assertNotIn(forbidden, source)

    def test_exact_authorities_are_deterministic(self):
        rows = normalized_rows(START, 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _path, raw = self._current_file(root, rows)
            desc = descriptor(".tail/current.json", raw, START, START + STEP)
            first = mixed_plan([current_segment(desc, START, START + 2 * STEP)], START, START + 2 * STEP)
            second = mixed_plan([current_segment(desc, START, START + 2 * STEP)], START, START + 2 * STEP)
            rows1, _diag1 = history_access.materialize_resolution_plan(first, root=root, cache_dir=root / "cache")
            rows2, _diag2 = history_access.materialize_resolution_plan(second, root=root, cache_dir=root / "cache")
            observations = history_consumer_semantic(rows1)
            receipt1 = build_semantic_receipt(
                series_id=SERIES_ID, start_ms=START, end_ms=START + 2 * STEP, cutoff_ms=None,
                mode="strict", current_policy="FINALIZED_ONLY", resolution_plan_sha256=first["plan_sha256"],
                observations=observations, finality="FINALIZED", revision_context=None,
            )
            receipt2 = build_semantic_receipt(
                series_id=SERIES_ID, start_ms=START, end_ms=START + 2 * STEP, cutoff_ms=None,
                mode="strict", current_policy="FINALIZED_ONLY", resolution_plan_sha256=second["plan_sha256"],
                observations=history_consumer_semantic(rows2), finality="FINALIZED", revision_context=None,
            )
        self.assertEqual(first["plan_sha256"], second["plan_sha256"])
        self.assertEqual(rows1, rows2)
        self.assertEqual(sha_json(receipt1), sha_json(receipt2))


def history_consumer_semantic(rows):
    return [
        {
            "timestamp_ms": row[0],
            "value": {"open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5]},
            "finality": "FINALIZED",
        }
        for row in rows
    ]


if __name__ == "__main__":
    unittest.main()
