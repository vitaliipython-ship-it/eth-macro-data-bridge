from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from raw_chain_transfer_core import CanonicalBlockReferencePort
from raw_chain_transfer_range import RawChainTransferBoundedRangeExecutor, RawTransferRangeError
from raw_chain_transfer_route import RawTransferPhysicalRoute

ROOT = Path(__file__).resolve().parents[2]
KNOWN_AT = "2026-09-14T12:00:00Z"


def block_hash(height: int) -> str:
    return "0x" + f"{height:064x}"


class RecordingBlockReference:
    def __init__(self, events: list[tuple[Any, ...]], *, fail_height: int | None = None) -> None:
        self.events = events
        self.fail_height = fail_height
        self.calls: list[int] = []

    def resolve_block_hash(self, *, chain_id: str, block_height: int) -> str:
        self.calls.append(block_height)
        self.events.append(("resolve", block_height))
        if block_height == self.fail_height:
            raise RuntimeError("DISCOVERY_FAILURE")
        return block_hash(block_height)


class RecordingRoute:
    def __init__(
        self,
        events: list[tuple[Any, ...]],
        *,
        fail_height: int | None = None,
        mismatch_height: int | None = None,
        mismatch_hash: int | None = None,
        zero_height: int | None = None,
        ack_fail_height: int | None = None,
    ) -> None:
        self.events = events
        self.fail_height = fail_height
        self.mismatch_height = mismatch_height
        self.mismatch_hash = mismatch_hash
        self.zero_height = zero_height
        self.ack_fail_height = ack_fail_height
        self.calls: list[tuple[str, str, str, Mapping[str, Any] | None]] = []

    def execute_block(
        self,
        chain_id: str,
        block_ref: str,
        *,
        observation_known_at: str,
        prior_canonical_block: Mapping[str, Any] | None = None,
    ):
        height = int(block_ref, 16)
        self.calls.append((chain_id, block_ref, observation_known_at, prior_canonical_block))
        self.events.append(("route", height, block_ref, prior_canonical_block))
        if height == self.fail_height:
            raise RuntimeError("ROUTE_OR_ACK_FAILURE")
        return SimpleNamespace(
            block_height=height + 1 if height == self.mismatch_height else height,
            block_hash=block_hash(height + 1000) if height == self.mismatch_hash else block_ref,
            ack_state="FAIL" if height == self.ack_fail_height else "PASS",
            observation_count=0 if height == self.zero_height else 1,
            zero_event_classification=(
                "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE" if height == self.zero_height else None
            ),
        )


class RawTransferBoundedRangeTests(unittest.TestCase):
    def executor(self, **route_kwargs):
        events: list[tuple[Any, ...]] = []
        reference = RecordingBlockReference(events)
        route = RecordingRoute(events, **route_kwargs)
        return RawChainTransferBoundedRangeExecutor(reference, route), reference, route, events

    def test_T01_reuses_existing_ports_and_route(self) -> None:
        self.assertIn("resolve_block_hash", CanonicalBlockReferencePort.__dict__)
        self.assertTrue(hasattr(RawTransferPhysicalRoute, "execute_block"))
        source = (ROOT / "src/raw_chain_transfer_range.py").read_text(encoding="utf-8")
        self.assertIn("from raw_chain_transfer_core import CanonicalBlockReferencePort", source)
        self.assertIn("from raw_chain_transfer_route import RawTransferPhysicalRoute", source)

    def test_T02_half_open_range_executes_ascending_once_each(self) -> None:
        executor, reference, route, events = self.executor()
        result = executor.execute_range(
            chain_id="1", block_height_start=10, block_height_end=13, observation_known_at=KNOWN_AT
        )
        self.assertEqual(reference.calls, [10, 11, 12])
        self.assertEqual([int(call[1], 16) for call in route.calls], [10, 11, 12])
        self.assertEqual([item.block_height for item in result.results], [10, 11, 12])
        self.assertEqual([event[:2] for event in events], [("resolve", 10), ("route", 10), ("resolve", 11), ("route", 11), ("resolve", 12), ("route", 12)])

    def test_T03_single_height_range_executes_exactly_one_height(self) -> None:
        executor, reference, route, _ = self.executor()
        executor.execute_range(chain_id="1", block_height_start=42, block_height_end=43, observation_known_at=KNOWN_AT)
        self.assertEqual(reference.calls, [42])
        self.assertEqual(len(route.calls), 1)
        self.assertEqual(route.calls[0][1], block_hash(42))

    def test_T04_invalid_ranges_fail_before_side_effect(self) -> None:
        invalid = ((True, 2), (1, False), ("1", 2), (1, 2.0), (-1, 2), (1, -2), (2, 2), (3, 2))
        for start, end in invalid:
            with self.subTest(start=start, end=end):
                executor, reference, route, events = self.executor()
                with self.assertRaises(RawTransferRangeError):
                    executor.execute_range(
                        chain_id="1", block_height_start=start, block_height_end=end, observation_known_at=KNOWN_AT
                    )
                self.assertEqual(reference.calls, [])
                self.assertEqual(route.calls, [])
                self.assertEqual(events, [])

    def test_T05_resolved_hash_is_exact_route_block_ref(self) -> None:
        executor, _, route, _ = self.executor()
        executor.execute_range(chain_id="1", block_height_start=7, block_height_end=8, observation_known_at=KNOWN_AT)
        self.assertEqual(route.calls[0][1], block_hash(7))

    def test_T06_route_result_height_and_hash_must_bind_exactly(self) -> None:
        for kwargs, code in (({"mismatch_height": 7}, "ROUTE_BLOCK_HEIGHT_MISMATCH"), ({"mismatch_hash": 7}, "ROUTE_BLOCK_HASH_MISMATCH")):
            with self.subTest(code=code):
                executor, _, _, _ = self.executor(**kwargs)
                with self.assertRaisesRegex(RawTransferRangeError, code):
                    executor.execute_range(chain_id="1", block_height_start=7, block_height_end=8, observation_known_at=KNOWN_AT)

    def test_T07_next_height_starts_only_after_prior_route_success(self) -> None:
        executor, _, _, events = self.executor()
        executor.execute_range(chain_id="1", block_height_start=3, block_height_end=6, observation_known_at=KNOWN_AT)
        self.assertEqual([event[0] for event in events], ["resolve", "route", "resolve", "route", "resolve", "route"])

    def test_T08_discovery_failure_stops_current_route_and_later_heights(self) -> None:
        events: list[tuple[Any, ...]] = []
        reference = RecordingBlockReference(events, fail_height=5)
        route = RecordingRoute(events)
        executor = RawChainTransferBoundedRangeExecutor(reference, route)
        with self.assertRaisesRegex(RuntimeError, "DISCOVERY_FAILURE"):
            executor.execute_range(chain_id="1", block_height_start=4, block_height_end=8, observation_known_at=KNOWN_AT)
        self.assertEqual(reference.calls, [4, 5])
        self.assertEqual([int(call[1], 16) for call in route.calls], [4])

    def test_T09_route_or_ack_failure_stops_every_later_height(self) -> None:
        executor, reference, route, _ = self.executor(fail_height=5)
        with self.assertRaisesRegex(RuntimeError, "ROUTE_OR_ACK_FAILURE"):
            executor.execute_range(chain_id="1", block_height_start=4, block_height_end=8, observation_known_at=KNOWN_AT)
        self.assertEqual(reference.calls, [4, 5])
        self.assertEqual([int(call[1], 16) for call in route.calls], [4, 5])

        executor, reference, route, _ = self.executor(ack_fail_height=5)
        with self.assertRaisesRegex(RawTransferRangeError, "ROUTE_ACK_NOT_PASS"):
            executor.execute_range(chain_id="1", block_height_start=4, block_height_end=8, observation_known_at=KNOWN_AT)
        self.assertEqual(reference.calls, [4, 5])
        self.assertEqual([int(call[1], 16) for call in route.calls], [4, 5])

    def test_T10_prior_successes_are_not_rolled_back_after_later_failure(self) -> None:
        executor, _, route, events = self.executor(fail_height=6)
        with self.assertRaises(RuntimeError):
            executor.execute_range(chain_id="1", block_height_start=4, block_height_end=8, observation_known_at=KNOWN_AT)
        self.assertEqual([event[1] for event in events if event[0] == "route"], [4, 5, 6])
        self.assertEqual([int(call[1], 16) for call in route.calls[:2]], [4, 5])

    def test_T11_covered_zero_is_successful_height_and_not_skipped(self) -> None:
        executor, reference, route, _ = self.executor(zero_height=5)
        result = executor.execute_range(chain_id="1", block_height_start=4, block_height_end=7, observation_known_at=KNOWN_AT)
        self.assertEqual(reference.calls, [4, 5, 6])
        self.assertEqual(len(route.calls), 3)
        zero = result.results[1]
        self.assertEqual(zero.observation_count, 0)
        self.assertEqual(zero.zero_event_classification, "NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE")

    def test_T12_prior_canonical_evidence_passes_exactly_and_is_never_invented(self) -> None:
        prior = {"chain_id": "1", "block_height": 5, "block_hash": block_hash(99)}
        executor, _, route, _ = self.executor()
        executor.execute_range(
            chain_id="1", block_height_start=4, block_height_end=7, observation_known_at=KNOWN_AT, prior_canonical_blocks={5: prior}
        )
        self.assertIsNone(route.calls[0][3])
        self.assertIs(route.calls[1][3], prior)
        self.assertIsNone(route.calls[2][3])

    def test_T13_no_checkpoint_vendor_storage_scheduler_or_network_framework(self) -> None:
        source = (ROOT / "src/raw_chain_transfer_range.py").read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in (
            "sqlite", "checkpoint", "cursor", "resume_file", "alchemy", "quicknode", "infura", "ankr",
            "api_key", "endpoint", "database", "filesystem", "scheduler", "threadpool", "threading", "asyncio",
            "requests", "urllib", "socket", "aiohttp", "http://", "https://",
        ):
            self.assertNotIn(forbidden, lowered)
        tree = ast.parse(source)
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
        imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
        self.assertTrue(imports.isdisjoint({"os", "sqlite3", "requests", "urllib", "socket", "aiohttp", "asyncio", "threading"}))

    def test_T14_bridge_predicates_truthful_higher_activation_remains_false(self) -> None:
        bridge = json.loads((ROOT / "bridge-contract.json").read_text(encoding="utf-8"))
        selective = bridge["semantic_resolution"]["selective_v2_event_series"]
        raw = bridge["semantic_contracts"]["raw_chain_transfer_fact"]
        self.assertTrue(selective["raw_transfer_bounded_range_execution_source_implemented"])
        self.assertEqual(selective["raw_transfer_bounded_range_execution_network_inactive_qualification"], "PASS")
        self.assertFalse(selective["raw_transfer_bounded_range_execution_runtime_active"])
        self.assertFalse(selective["raw_transfer_capability_implemented"])
        self.assertEqual(selective["raw_transfer_live_provider_qualification"], "NOT_STARTED")
        self.assertFalse(selective["provider_selected"])
        self.assertFalse(selective["storage_selected"])
        self.assertFalse(selective["production_activated"])
        self.assertFalse(selective["resolution_plan_v2_global_active"])
        self.assertFalse(selective["d9_global_active"])
        self.assertFalse(raw["runtime_active"])
        self.assertEqual(raw["status"], "CONTRACT_BOUND_RUNTIME_ROUTE_NOT_IMPLEMENTED")


if __name__ == "__main__":
    unittest.main()
