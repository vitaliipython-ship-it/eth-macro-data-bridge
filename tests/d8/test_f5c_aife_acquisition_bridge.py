from __future__ import annotations

import asyncio
import hashlib
import inspect
import sqlite3
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STAGED_AIFE_ROOT = REPOSITORY_ROOT / "AIFE" / "staging"
if str(STAGED_AIFE_ROOT) not in sys.path:
    sys.path.insert(0, str(STAGED_AIFE_ROOT))

# isort: off
import aife_f5c_acquisition_adapter as f5c_adapter
from acquisition_core import CanonicalAcquisitionCore
from aife_f5c_acquisition_adapter import (
    DataBridgeF5CAcquisitionAdapter,
    DataBridgeF5CAcquisitionError,
)
from canonical_json import canonical_json_bytes
from d8_capability_routing import runtime_due_policy
from d8_observation_normalizer import canonical_observation_bytes, normalize_observations
from d8_runtime import D8Runtime, DeterministicMockAcquisition, RuntimeConfig
from server.acquisition.ports import AcquiredArtifact
from server.acquisition.service import (
    AcquisitionResultInvariantError,
    DurableAcquisitionAcceptance,
    GenericAcquisitionService,
)
from core.data.adapters.sqlite_control import SQLiteServerControlRepository
from server.storage.filesystem import QualifiedDataRootImmutableFilesystem

# isort: on

SLOT = "2026-09-07T11:15:00.000Z"
EXPECTED_MS = 1788779700000
NOW_MS = 1788779701000
SOURCE_REVISION = "c3-source-revision"
CYCLE_ID = "d8c-f5c-c3-test"
NOW = datetime(2026, 9, 7, 11, 15, 1, tzinfo=UTC)


def _capability() -> dict[str, object]:
    return next(row for row in runtime_due_policy() if row["id"] == "binance-spot.m5")


def _row(symbol: str = "ETHUSDT") -> dict[str, object]:
    return {
        "series_id": f"spot.binance-spot.{symbol}.ohlcv.5m",
        "provider_timestamp_at": SLOT,
        "provider_route": "https://provider.test/binance-spot",
        "finality": "FINALIZED",
        "freshness": {
            "status": "LIVE_USABLE",
            "age_seconds": 0,
            "target_cadence_seconds": 300,
        },
        "value": {
            "open_time_ms": EXPECTED_MS - 300000,
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "101",
            "base_volume": "10",
            "close_time_ms": EXPECTED_MS - 1,
            "close_time": EXPECTED_MS - 1,
            "quote_volume": "1000",
            "trade_count": 7,
            "taker_buy_base_volume": "5",
            "taker_buy_quote_volume": "500",
            "closed": True,
        },
        "d9_target": "FIXED_GRID",
        "provenance": {
            "provider_native_timeframe": "5m",
            "provider_native_rich_row": True,
        },
    }


def _provider_result() -> dict[str, object]:
    return {"status": "PASS", "observations": [_row("ETHUSDT"), _row("BTCUSDT")]}


def _row_count(repo: SQLiteServerControlRepository, table: str) -> int:
    con = sqlite3.connect(repo.database_path)
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        con.close()


class F5CAIFEAcquisitionBridgeTests(unittest.TestCase):
    def test_runtime_delegates_to_single_shared_normalizer_and_preserves_behavior(self) -> None:
        cap = _capability()
        rows = [_row()]
        direct_a = normalize_observations(
            cap,
            rows,
            CYCLE_ID,
            SLOT,
            NOW_MS,
            source_revision=SOURCE_REVISION,
        )
        direct_b = normalize_observations(
            cap,
            rows,
            CYCLE_ID,
            SLOT,
            NOW_MS,
            source_revision=SOURCE_REVISION,
        )
        self.assertEqual(direct_a, direct_b)

        with tempfile.TemporaryDirectory() as td:
            runtime = D8Runtime(
                RuntimeConfig(
                    state_root=Path(td) / "runtime",
                    profile="test",
                    source_revision=SOURCE_REVISION,
                ),
                DeterministicMockAcquisition(),
                clock_ms=lambda: NOW_MS,
            )
            with patch(
                "d8_runtime.normalize_observations",
                wraps=normalize_observations,
            ) as shared:
                legacy = runtime._normalize_observations(
                    cap,
                    rows,
                    CYCLE_ID,
                    SLOT,
                    NOW_MS,
                )
            self.assertEqual(shared.call_count, 1)
            self.assertEqual(legacy, direct_a)

        method_source = inspect.getsource(D8Runtime._normalize_observations)
        self.assertIn("normalize_observations(", method_source)
        self.assertNotIn("provider_revision", method_source)
        self.assertNotIn("observation_id(", method_source)

    def test_f5c_adapter_reuses_canonical_core_and_returns_exact_canonical_bytes(self) -> None:
        cap = _capability()
        result = _provider_result()
        expected_rows = normalize_observations(
            cap,
            result["observations"],
            CYCLE_ID,
            SLOT,
            NOW_MS,
            source_revision=SOURCE_REVISION,
        )
        expected = next(
            row
            for row in expected_rows
            if row["series_id"] == "spot.binance-spot.ETHUSDT.ohlcv.5m"
        )
        core = CanonicalAcquisitionCore()
        with tempfile.TemporaryDirectory() as td, patch.object(
            core, "_spot", return_value=result
        ) as spot:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                acquisition=core,
                clock_ms=lambda: NOW_MS,
            )
            acquired = asyncio.run(adapter.acquire())

        spot.assert_called_once_with("binance-spot", "binance-spot.m5", EXPECTED_MS)
        self.assertIsInstance(acquired, AcquiredArtifact)
        self.assertEqual(acquired.payload, canonical_observation_bytes(expected))
        self.assertEqual(acquired.payload, canonical_json_bytes(expected))
        self.assertEqual(
            hashlib.sha256(acquired.payload).hexdigest(),
            acquired.envelope.content_identity,
        )
        self.assertEqual(acquired.envelope.artifact_identity.value, expected["observation_id"])
        self.assertEqual(acquired.envelope.artifact_type.value, expected["series_id"])
        self.assertEqual(acquired.envelope.source_revision, SOURCE_REVISION)
        self.assertEqual(
            acquired.envelope.payload_reference,
            f"d8-observation:{expected['observation_id']}",
        )
        for domain_field in ("provider", "finality", "value", "capability_id"):
            self.assertFalse(hasattr(acquired.envelope, domain_field))

    def test_generic_acquisition_reuses_c2_durable_acceptance_and_survives_restart(self) -> None:
        result = _provider_result()
        core = CanonicalAcquisitionCore()
        with tempfile.TemporaryDirectory() as td, patch.object(
            core, "_spot", return_value=result
        ):
            root = Path(td)
            repo = SQLiteServerControlRepository(root / "control.sqlite3")
            store = QualifiedDataRootImmutableFilesystem(root / "data")
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=root / "provider",
                source_revision=SOURCE_REVISION,
                acquisition=core,
                clock_ms=lambda: NOW_MS,
            )
            service = GenericAcquisitionService(
                adapter,
                DurableAcquisitionAcceptance(
                    store,
                    repo,
                    policy_revision_identity="policy-c3",
                ),
            )
            durable = asyncio.run(service.acquire_durable(at=NOW))

            digest = hashlib.sha256(durable.acquired.payload).hexdigest()
            self.assertEqual(digest, durable.acquired.envelope.content_identity)
            self.assertEqual(durable.object_evidence.content_digest, digest)
            self.assertEqual(
                durable.work.payload_reference,
                durable.object_evidence.physical_locator,
            )
            self.assertEqual(durable.work.state, "PENDING")
            self.assertEqual(store.read_exact(digest), durable.acquired.payload)
            self.assertEqual(_row_count(repo, "work"), 1)
            self.assertEqual(_row_count(repo, "attempt"), 0)
            self.assertEqual(_row_count(repo, "publication"), 0)

            reopened_repo = SQLiteServerControlRepository(root / "control.sqlite3")
            reopened_store = QualifiedDataRootImmutableFilesystem(root / "data")
            persisted = reopened_repo.get_work(durable.work.work_id)
            self.assertIsNotNone(persisted)
            self.assertEqual(
                persisted.payload_reference,
                durable.object_evidence.physical_locator,
            )
            self.assertEqual(reopened_store.read_exact(digest), durable.acquired.payload)

            replay = asyncio.run(service.acquire_durable(at=NOW))
            self.assertEqual(replay.work.work_id, durable.work.work_id)
            self.assertEqual(replay.object_evidence, durable.object_evidence)
            self.assertEqual(_row_count(repo, "work"), 1)
            self.assertEqual(_row_count(repo, "attempt"), 0)
            self.assertEqual(_row_count(repo, "publication"), 0)

    def test_invalid_provider_result_and_payload_mismatch_fail_closed(self) -> None:
        core = CanonicalAcquisitionCore()
        with tempfile.TemporaryDirectory() as td, patch.object(
            core,
            "_spot",
            return_value={"status": "FAIL", "observations": []},
        ):
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                acquisition=core,
                clock_ms=lambda: NOW_MS,
            )
            with self.assertRaisesRegex(
                DataBridgeF5CAcquisitionError,
                "did not PASS",
            ):
                asyncio.run(adapter.acquire())

        cap = _capability()
        observation = normalize_observations(
            cap,
            [_row()],
            CYCLE_ID,
            SLOT,
            NOW_MS,
            source_revision=SOURCE_REVISION,
        )[0]
        from aife_server_adapter import adapt_d8_observation_with_payload

        envelope, payload = adapt_d8_observation_with_payload(observation)

        class _MismatchedAdapter:
            async def acquire(self) -> AcquiredArtifact:
                return AcquiredArtifact(envelope=envelope, payload=payload + b"tamper")

        with self.assertRaisesRegex(
            AcquisitionResultInvariantError,
            "payload digest",
        ):
            asyncio.run(GenericAcquisitionService(_MismatchedAdapter()).acquire())

    def test_c3_adapter_does_not_own_new_durability_or_state_mechanism(self) -> None:
        source = Path(f5c_adapter.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "sqlite3",
            "write_immutable",
            "accept_work",
            "mark_work_ready",
            "claim_work",
            "publication",
            "spool",
            "queue",
            "ledger",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
