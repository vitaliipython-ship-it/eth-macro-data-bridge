from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import history_access_v2
import resolution_v2
from raw_chain_transfer_coverage import (
    SNAPSHOT_SCHEMA_VERSION,
    RawTransferCoverageSnapshotError,
    build_acked_coverage_snapshot,
)
from tests.deep_history import test_d9_resolution_v2 as d9test
from tests.deep_history.test_raw_chain_transfer_physical_route import FakeTransport, build_bundle

ROOT = Path(__file__).resolve().parents[2]
CHAIN_ID = "1"
START_UTC = "2025-09-11T13:00:00Z"
END_UTC = "2025-09-11T14:00:00Z"
CUTOFF_UTC = "2026-09-10T12:30:00Z"
PARSER_POLICY = "ethereum-raw-transfer-parser/1.0.0"
ZERO_CLASS = "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE"


def _block_hash(height: int, salt: int = 0) -> str:
    return "0x" + f"{height + salt:064x}"


def _coverage_row(height: int, *, state: str = "COVERED_ZERO_EVENT_BLOCK", chain_id: str = CHAIN_ID) -> dict:
    zero = ZERO_CLASS if state == "COVERED_ZERO_EVENT_BLOCK" else None
    return {
        "state": state,
        "resource_ref": f"raw-transfer-bundle:rawblk-{'a' * 64}-{height}",
        "content_identity": f"{height + 1:064x}"[-64:],
        "coverage_complete": True,
        "coverage_key": {
            "chain_id": chain_id,
            "block_height": height,
            "block_hash": _block_hash(height),
            "parser_policy_revision": PARSER_POLICY,
        },
        "zero_event_classification": zero,
        "finality": "FINALIZED",
        "observation_known_at": "2026-09-10T12:00:00Z",
    }


def _bundle(
    height: int, *, block_hash: str | None = None, known_at: str = "2026-09-10T12:00:00Z",
    prior=None, finalized_height: int | None = None,
):
    block_hash = block_hash or _block_hash(height)
    finalized_height = height if finalized_height is None else finalized_height
    finalized_hash = block_hash if finalized_height == height else _block_hash(finalized_height)
    transport = FakeTransport(
        block_hash=block_hash, finalized={"number": hex(finalized_height), "hash": finalized_hash}
    )
    transport.block["number"] = hex(height)
    return build_bundle(transport, known_at=known_at, block_ref=block_hash, prior=prior)


def _write_root(root: Path, bundles: list[dict]) -> list[dict]:
    return d9test.RawTransferDurableV2WiringTests._write_root(root, bundles)


def _plan(root: Path, start: int, end: int, *, cutoff: str = CUTOFF_UTC, current_policy: str = "FINALIZED_ONLY"):
    return resolution_v2.resolve_event_series_v2(
        "blockchain.raw-transfer-facts",
        START_UTC,
        END_UTC,
        observations=None,
        canonicality_revisions=None,
        cutoff_utc=cutoff,
        current_policy=current_policy,
        root=root,
        chain_id=CHAIN_ID,
        block_height_start=start,
        block_height_end=end,
    )


class RawTransferAckedCoverageFrontierTests(unittest.TestCase):
    def test_T01_empty_coverage_starts_gap_at_first_requested_height(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID, block_height_start=100, block_height_end=103, coverage_evidence=[]
        )
        self.assertEqual(snap["schema_version"], SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(snap["covered_heights"], [])
        self.assertEqual(snap["missing_block_heights"], [100, 101, 102])
        self.assertIsNone(snap["highest_contiguous_acked_height"])
        self.assertEqual(snap["contiguous_end_exclusive"], 100)
        self.assertEqual(snap["next_uncovered_block_height"], 100)
        self.assertFalse(snap["complete"])

    def test_T02_fully_covered_range_is_complete(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID,
            block_height_start=100,
            block_height_end=103,
            coverage_evidence=[_coverage_row(h) for h in (100, 101, 102)],
        )
        self.assertTrue(snap["complete"])
        self.assertEqual(snap["highest_contiguous_acked_height"], 102)
        self.assertEqual(snap["contiguous_end_exclusive"], 103)
        self.assertIsNone(snap["next_uncovered_block_height"])

    def test_T03_covered_zero_counts_as_covered(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID, block_height_start=100, block_height_end=101, coverage_evidence=[_coverage_row(100)]
        )
        self.assertEqual(snap["covered_heights"], [100])
        self.assertTrue(snap["complete"])

    def test_T04_first_height_gap_prevents_frontier_advance(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID,
            block_height_start=100,
            block_height_end=103,
            coverage_evidence=[_coverage_row(101), _coverage_row(102)],
        )
        self.assertIsNone(snap["highest_contiguous_acked_height"])
        self.assertEqual(snap["next_uncovered_block_height"], 100)

    def test_T05_middle_gap_stops_frontier_exactly(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID,
            block_height_start=100,
            block_height_end=106,
            coverage_evidence=[_coverage_row(h) for h in (100, 101, 102, 104, 105)],
        )
        self.assertEqual(snap["highest_contiguous_acked_height"], 102)
        self.assertEqual(snap["contiguous_end_exclusive"], 103)
        self.assertEqual(snap["next_uncovered_block_height"], 103)

    def test_T06_later_coverage_never_jumps_first_gap(self):
        snap = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID,
            block_height_start=200,
            block_height_end=205,
            coverage_evidence=[_coverage_row(h) for h in (200, 202, 203, 204)],
        )
        self.assertEqual(snap["covered_heights"], [200, 202, 203, 204])
        self.assertEqual(snap["highest_contiguous_acked_height"], 200)
        self.assertEqual(snap["next_uncovered_block_height"], 201)

    def test_T07_duplicate_height_fails_closed(self):
        duplicate = deepcopy(_coverage_row(100))
        duplicate["resource_ref"] += "-duplicate"
        with self.assertRaisesRegex(RawTransferCoverageSnapshotError, "COVERAGE_DUPLICATE_HEIGHT"):
            build_acked_coverage_snapshot(
                chain_id=CHAIN_ID, block_height_start=100, block_height_end=101,
                coverage_evidence=[_coverage_row(100), duplicate],
            )

    def test_T08_wrong_chain_evidence_fails_closed(self):
        with self.assertRaisesRegex(RawTransferCoverageSnapshotError, "COVERAGE_CHAIN_MISMATCH"):
            build_acked_coverage_snapshot(
                chain_id=CHAIN_ID, block_height_start=100, block_height_end=101,
                coverage_evidence=[_coverage_row(100, chain_id="8453")],
            )

    def test_T09_out_of_range_evidence_fails_closed(self):
        with self.assertRaisesRegex(RawTransferCoverageSnapshotError, "COVERAGE_HEIGHT_OUTSIDE_RANGE"):
            build_acked_coverage_snapshot(
                chain_id=CHAIN_ID, block_height_start=100, block_height_end=101,
                coverage_evidence=[_coverage_row(101)],
            )

    def test_T10_malformed_or_incomplete_evidence_fails_closed(self):
        mutations = (
            (lambda row: row.__setitem__("coverage_complete", False), "COVERAGE_EVIDENCE_INCOMPLETE"),
            (lambda row: row.__setitem__("resource_ref", ""), "COVERAGE_RESOURCE_REF_INVALID"),
            (lambda row: row["coverage_key"].__setitem__("block_hash", ""), "COVERAGE_BLOCK_HASH_INVALID"),
        )
        for mutate, code in mutations:
            with self.subTest(code=code):
                row = _coverage_row(100)
                mutate(row)
                with self.assertRaisesRegex(RawTransferCoverageSnapshotError, code):
                    build_acked_coverage_snapshot(
                        chain_id=CHAIN_ID, block_height_start=100, block_height_end=101, coverage_evidence=[row]
                    )

    def test_T11_snapshot_identity_is_deterministic_for_semantic_evidence(self):
        rows = [_coverage_row(100), _coverage_row(101), _coverage_row(102)]
        first = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID, block_height_start=100, block_height_end=103, coverage_evidence=rows
        )
        second = build_acked_coverage_snapshot(
            chain_id=CHAIN_ID, block_height_start=100, block_height_end=103, coverage_evidence=list(reversed(rows))
        )
        self.assertEqual(first["coverage_evidence_sha256"], second["coverage_evidence_sha256"])
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])

    def test_T12_reader_snapshot_is_after_pit_canonical_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_hash, new_hash = _block_hash(100), _block_hash(100, 1000)
            old = _bundle(100, block_hash=old_hash, known_at="2026-09-10T12:00:00Z")
            prior = {"chain_id": CHAIN_ID, "block_height": 100, "block_hash": old_hash}
            new = _bundle(100, block_hash=new_hash, known_at="2026-09-10T12:10:00Z", prior=prior)
            _write_root(root, [old, new])
            pre_rows, pre = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 101, cutoff="2026-09-10T12:05:00Z"), root=root, mode="strict"
            )
            post_rows, post = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 101, cutoff="2026-09-10T12:20:00Z"), root=root, mode="strict"
            )
            self.assertEqual(pre_rows, post_rows, [])
            self.assertEqual(pre["coverage_evidence"][0]["coverage_key"]["block_hash"], old_hash)
            self.assertEqual(post["coverage_evidence"][0]["coverage_key"]["block_hash"], new_hash)
            self.assertTrue(pre["acked_coverage_snapshot"]["complete"])
            self.assertTrue(post["acked_coverage_snapshot"]["complete"])

    def test_T13_reorg_canonical_selection_yields_one_covered_height(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_hash, new_hash = _block_hash(100), _block_hash(100, 2000)
            old = _bundle(100, block_hash=old_hash, known_at="2026-09-10T12:00:00Z")
            prior = {"chain_id": CHAIN_ID, "block_height": 100, "block_hash": old_hash}
            new = _bundle(100, block_hash=new_hash, known_at="2026-09-10T12:10:00Z", prior=prior)
            _write_root(root, [old, new])
            _, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 101, cutoff="2026-09-10T12:20:00Z"), root=root, mode="strict"
            )
            self.assertEqual(len(diagnostics["coverage_evidence"]), 1)
            self.assertEqual(diagnostics["acked_coverage_snapshot"]["covered_heights"], [100])
            self.assertEqual(diagnostics["superseded_resource_count"], 1)

    def test_T14_future_revision_beyond_cutoff_does_not_change_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_hash, new_hash = _block_hash(100), _block_hash(100, 3000)
            old = _bundle(100, block_hash=old_hash, known_at="2026-09-10T12:00:00Z")
            prior = {"chain_id": CHAIN_ID, "block_height": 100, "block_hash": old_hash}
            new = _bundle(100, block_hash=new_hash, known_at="2026-09-10T12:40:00Z", prior=prior)
            _write_root(root, [old, new])
            _, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 101, cutoff="2026-09-10T12:30:00Z"), root=root, mode="strict"
            )
            self.assertEqual(diagnostics["coverage_evidence"][0]["coverage_key"]["block_hash"], old_hash)
            self.assertEqual(diagnostics["canonicality_revisions_applied"], [])
            self.assertEqual(diagnostics["acked_coverage_snapshot"]["highest_contiguous_acked_height"], 100)

    def test_T15_strict_reader_fails_data_gap_on_incomplete_explicit_range(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_root(root, [_bundle(100), _bundle(102)])
            plan = _plan(root, 100, 103)
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as ctx:
                history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
            self.assertEqual(ctx.exception.code, "DATA_GAP")
            self.assertIn("101", str(ctx.exception))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_root(root, [_bundle(100, finalized_height=99)])
            plan = _plan(root, 100, 101, current_policy="FINALIZED_ONLY")
            with self.assertRaises(history_access_v2.HistoryAccessV2Error) as ctx:
                history_access_v2.materialize_resolution_plan_v2(plan, root=root, mode="strict")
            self.assertEqual(ctx.exception.code, "DATA_GAP")
            self.assertIn("100", str(ctx.exception))

    def test_T16_permissive_reader_returns_degraded_with_exact_first_gap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_root(root, [_bundle(100), _bundle(102)])
            _, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 103), root=root, mode="permissive"
            )
            self.assertEqual(diagnostics["status"], "DEGRADED")
            snapshot = diagnostics["acked_coverage_snapshot"]
            self.assertFalse(snapshot["complete"])
            self.assertEqual(snapshot["next_uncovered_block_height"], 101)
            self.assertEqual(snapshot["highest_contiguous_acked_height"], 100)

    def test_T17_fully_covered_explicit_range_remains_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_root(root, [_bundle(100), _bundle(101), _bundle(102)])
            _, diagnostics = history_access_v2.materialize_resolution_plan_v2(
                _plan(root, 100, 103), root=root, mode="strict"
            )
            self.assertEqual(diagnostics["status"], "PASS")
            snapshot = diagnostics["acked_coverage_snapshot"]
            self.assertTrue(snapshot["complete"])
            self.assertEqual(snapshot["covered_heights"], [100, 101, 102])
            self.assertIsNone(snapshot["next_uncovered_block_height"])

    def test_T18_bridge_predicates_are_truthful_and_activation_stays_off(self):
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        raw = bridge["semantic_contracts"]["raw_chain_transfer_fact"]
        self.assertTrue(selective["raw_transfer_acked_coverage_frontier_source_implemented"])
        self.assertEqual(selective["raw_transfer_acked_coverage_frontier_network_inactive_qualification"], "PASS")
        self.assertFalse(selective["raw_transfer_acked_coverage_frontier_runtime_active"])
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        self.assertEqual(selective["raw_transfer_live_provider_qualification"], "NOT_STARTED")
        self.assertFalse(selective["provider_selected"])
        self.assertFalse(selective["storage_selected"])
        self.assertFalse(selective["production_activated"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(selective["d9_global_active"])
        self.assertEqual(raw["status"], "CONTRACT_BOUND_RUNTIME_ROUTE_NOT_IMPLEMENTED")
        self.assertFalse(raw["runtime_active"])


if __name__ == "__main__":
    unittest.main()
