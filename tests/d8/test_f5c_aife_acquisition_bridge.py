from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
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
import d8_capability_routing as capability_routing
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
from server.runtime import c9_forward as c9_forward_module
from server.runtime.c9_forward import C9ForwardRequest, forward_once

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


def _generic_row(
    series_id: str,
    *,
    provider: str,
    finality: str,
    value: object,
    revision_classification: str | None = None,
    provider_timestamp_at: str | None = SLOT,
) -> dict[str, object]:
    row: dict[str, object] = {
        "series_id": series_id,
        "provider_timestamp_at": provider_timestamp_at,
        "provider_route": f"https://provider.test/{provider}",
        "finality": finality,
        "value": value,
        "d9_target": "FIXED_GRID",
    }
    if revision_classification is not None:
        row["revision_classification"] = revision_classification
        row["source_snapshot_ref"] = row["provider_route"]
        row["provenance"] = {
            "metric_policy_schema": "kraken-futures-provider-revision/1.0.0",
            "revision_evidence_schema": "market-data-provider-revision/1.0.0",
        }
    return row


class _CountingAcquisition:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def collect(self, capability_id: str, **kwargs: object) -> dict[str, object]:
        self.calls.append((capability_id, kwargs))
        return self.result


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

    def test_binance_spot_defaults_remain_backward_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
            )
            request = C9ForwardRequest(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                at=NOW,
                claim_owner="worker-defaults",
                policy_revision_identity="policy-defaults",
            )
        self.assertEqual(adapter.capability_id, "binance-spot.m5")
        self.assertEqual(adapter.provider, "binance-spot")
        self.assertEqual(adapter.series_id, "spot.binance-spot.ETHUSDT.ohlcv.5m")
        self.assertEqual(request.capability_id, "binance-spot.m5")
        self.assertEqual(request.provider, "binance-spot")
        self.assertEqual(request.series_id, "spot.binance-spot.ETHUSDT.ohlcv.5m")

    def test_kraken_spot_generic_adapter_returns_exact_canonical_bytes(self) -> None:
        capability_id = "kraken-spot.m5"
        provider = "kraken-spot"
        series_id = "spot.kraken-spot.ETHUSD.ohlcv.5m"
        row = _generic_row(
            series_id,
            provider=provider,
            finality="FINALIZED",
            value={"open": "100", "high": "101", "low": "99", "close": "100.5"},
        )
        acquisition = _CountingAcquisition({"status": "PASS", "observations": [row]})
        cap = next(row for row in runtime_due_policy() if row["id"] == capability_id)
        expected = normalize_observations(
            cap, [row], CYCLE_ID, SLOT, NOW_MS, source_revision=SOURCE_REVISION
        )[0]
        with tempfile.TemporaryDirectory() as td:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
                acquisition=acquisition,
                clock_ms=lambda: NOW_MS,
            )
            acquired = asyncio.run(adapter.acquire())

        self.assertEqual(acquisition.calls[0][0], capability_id)
        self.assertEqual(acquired.payload, canonical_observation_bytes(expected))
        self.assertEqual(
            hashlib.sha256(acquired.payload).hexdigest(),
            acquired.envelope.content_identity,
        )
        self.assertEqual(acquired.envelope.artifact_type.value, series_id)

    def test_binance_usdm_representative_routing_classes(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        cases = (
            ("derivatives.binance-usdm.ETHUSDT.perp-ohlcv.5m", "FINALIZED"),
            ("derivatives.binance-usdm.ETHUSDT.open-interest-history.5m", "FINALIZED"),
            ("derivatives.binance-usdm.ETHUSDT.funding-history", "FINALIZED"),
            ("derivatives.binance-usdm.ETHUSDT.current", "OBSERVED_STATE"),
            ("liquidity.binance-usdm.ETHUSDT.depth", "OBSERVED_STATE"),
        )
        cap = next(row for row in runtime_due_policy() if row["id"] == capability_id)
        with tempfile.TemporaryDirectory() as td:
            for index, (series_id, finality) in enumerate(cases):
                with self.subTest(series_id=series_id):
                    row = _generic_row(
                        series_id,
                        provider=provider,
                        finality=finality,
                        value={"case": index, "series_id": series_id},
                    )
                    acquisition = _CountingAcquisition(
                        {"status": "PASS", "observations": [row]}
                    )
                    expected = normalize_observations(
                        cap,
                        [row],
                        CYCLE_ID,
                        SLOT,
                        NOW_MS,
                        source_revision=SOURCE_REVISION,
                    )[0]
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / f"provider-{index}",
                        source_revision=SOURCE_REVISION,
                        capability_id=capability_id,
                        provider=provider,
                        series_id=series_id,
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                    )
                    acquired = asyncio.run(adapter.acquire())
                    self.assertEqual(acquisition.calls[0][0], capability_id)
                    self.assertEqual(acquired.payload, canonical_observation_bytes(expected))
                    self.assertEqual(acquired.envelope.artifact_type.value, series_id)

    def test_multi_row_requested_series_selects_unique_latest_independent_of_input_order(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        series_id = "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m"
        earlier = _generic_row(
            series_id,
            provider=provider,
            finality="FINALIZED",
            value={"marker": "earlier"},
            provider_timestamp_at="2026-09-07T11:10:00.000Z",
        )
        latest = _generic_row(
            series_id,
            provider=provider,
            finality="FINALIZED",
            value={"marker": "latest"},
            provider_timestamp_at=SLOT,
        )
        cap = next(row for row in runtime_due_policy() if row["id"] == capability_id)
        expected = normalize_observations(
            cap, [latest], CYCLE_ID, SLOT, NOW_MS, source_revision=SOURCE_REVISION
        )[0]
        payloads = []
        with tempfile.TemporaryDirectory() as td:
            for index, rows in enumerate(([earlier, latest], [latest, earlier])):
                acquisition = _CountingAcquisition(
                    {"status": "PASS", "observations": list(rows)}
                )
                adapter = DataBridgeF5CAcquisitionAdapter(
                    expected_ms=EXPECTED_MS,
                    cycle_id=CYCLE_ID,
                    canonical_slot=SLOT,
                    staging_root=Path(td) / f"provider-{index}",
                    source_revision=SOURCE_REVISION,
                    capability_id=capability_id,
                    provider=provider,
                    series_id=series_id,
                    acquisition=acquisition,
                    clock_ms=lambda: NOW_MS,
                )
                payloads.append(asyncio.run(adapter.acquire()).payload)

        self.assertEqual(payloads[0], canonical_observation_bytes(expected))
        self.assertEqual(payloads[1], canonical_observation_bytes(expected))

    def test_multi_row_duplicate_latest_timestamp_fails_closed(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        series_id = "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m"
        rows = [
            _generic_row(
                series_id,
                provider=provider,
                finality="FINALIZED",
                value={"marker": "left"},
                provider_timestamp_at=SLOT,
            ),
            _generic_row(
                series_id,
                provider=provider,
                finality="FINALIZED",
                value={"marker": "right"},
                provider_timestamp_at=SLOT,
            ),
        ]
        acquisition = _CountingAcquisition({"status": "PASS", "observations": rows})
        with tempfile.TemporaryDirectory() as td:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
                acquisition=acquisition,
                clock_ms=lambda: NOW_MS,
            )
            with self.assertRaisesRegex(
                DataBridgeF5CAcquisitionError,
                "unique latest provider timestamp",
            ):
                asyncio.run(adapter.acquire())

    def test_multi_row_missing_or_invalid_provider_timestamp_fails_closed(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        series_id = "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m"
        for invalid_timestamp in (None, "not-a-timestamp"):
            with self.subTest(provider_timestamp_at=invalid_timestamp):
                rows = [
                    _generic_row(
                        series_id,
                        provider=provider,
                        finality="FINALIZED",
                        value={"marker": "invalid"},
                        provider_timestamp_at=invalid_timestamp,
                    ),
                    _generic_row(
                        series_id,
                        provider=provider,
                        finality="FINALIZED",
                        value={"marker": "latest"},
                        provider_timestamp_at=SLOT,
                    ),
                ]
                acquisition = _CountingAcquisition(
                    {"status": "PASS", "observations": rows}
                )
                with tempfile.TemporaryDirectory() as td:
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / "provider",
                        source_revision=SOURCE_REVISION,
                        capability_id=capability_id,
                        provider=provider,
                        series_id=series_id,
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                    )
                    with self.assertRaisesRegex(
                        DataBridgeF5CAcquisitionError,
                        "requires valid provider_timestamp_at",
                    ):
                        asyncio.run(adapter.acquire())

    def test_binance_usdm_history_representatives_select_unique_latest(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        cases = (
            "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m",
            "derivatives.binance-usdm.ETHUSDT.funding-history",
        )
        with tempfile.TemporaryDirectory() as td:
            for index, series_id in enumerate(cases):
                with self.subTest(series_id=series_id):
                    rows = [
                        _generic_row(
                            series_id,
                            provider=provider,
                            finality="FINALIZED",
                            value={"marker": "older"},
                            provider_timestamp_at="2026-09-07T11:00:00.000Z",
                        ),
                        _generic_row(
                            series_id,
                            provider=provider,
                            finality="FINALIZED",
                            value={"marker": "latest"},
                            provider_timestamp_at=SLOT,
                        ),
                    ]
                    acquisition = _CountingAcquisition(
                        {"status": "PASS", "observations": rows}
                    )
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / f"provider-{index}",
                        source_revision=SOURCE_REVISION,
                        capability_id=capability_id,
                        provider=provider,
                        series_id=series_id,
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                    )
                    payload = json.loads(asyncio.run(adapter.acquire()).payload)
                    self.assertEqual(payload["provider_timestamp_at"], SLOT)
                    self.assertEqual(payload["value"]["marker"], "latest")

    def test_kraken_futures_multi_row_representative_selects_unique_latest(self) -> None:
        capability_id = "kraken-futures.analytics"
        provider = "kraken-futures"
        series_id = "derivatives.kraken-futures.PI_ETHUSD.open-interest"
        rows = [
            _generic_row(
                series_id,
                provider=provider,
                finality="OBSERVED_STATE",
                value={"metric": "open-interest", "value": "1.0"},
                provider_timestamp_at="2026-09-07T11:10:00.000Z",
            ),
            _generic_row(
                series_id,
                provider=provider,
                finality="OBSERVED_STATE",
                value={"metric": "open-interest", "value": "1.25"},
                provider_timestamp_at=SLOT,
            ),
        ]
        acquisition = _CountingAcquisition({"status": "PASS", "observations": rows})
        with tempfile.TemporaryDirectory() as td:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
                acquisition=acquisition,
                clock_ms=lambda: NOW_MS,
            )
            payload = json.loads(asyncio.run(adapter.acquire()).payload)
        self.assertEqual(payload["provider_timestamp_at"], SLOT)
        self.assertEqual(payload["value"]["value"], "1.25")

    def test_kraken_futures_revisable_funding_multi_row_preserves_revision_provenance(self) -> None:
        capability_id = "kraken-futures.analytics"
        provider = "kraken-futures"
        series_id = "derivatives.kraken-futures.PI_ETHUSD.funding"
        rows = [
            _generic_row(
                series_id,
                provider=provider,
                finality="OBSERVED_STATE",
                value={"metric": "funding", "value": "0.001"},
                revision_classification="PROVIDER_REVISABLE_SNAPSHOT",
                provider_timestamp_at="2026-09-07T11:10:00.000Z",
            ),
            _generic_row(
                series_id,
                provider=provider,
                finality="OBSERVED_STATE",
                value={"metric": "funding", "value": "0.002"},
                revision_classification="PROVIDER_REVISABLE_SNAPSHOT",
                provider_timestamp_at=SLOT,
            ),
        ]

        def predecessor(*_args):
            return {
                "fingerprint": "previous-fingerprint",
                "observation_id": "obs-previous",
            }

        acquisition = _CountingAcquisition({"status": "PASS", "observations": rows})
        with tempfile.TemporaryDirectory() as td:
            adapter = DataBridgeF5CAcquisitionAdapter(
                expected_ms=EXPECTED_MS,
                cycle_id=CYCLE_ID,
                canonical_slot=SLOT,
                staging_root=Path(td) / "provider",
                source_revision=SOURCE_REVISION,
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
                acquisition=acquisition,
                clock_ms=lambda: NOW_MS,
                semantic_predecessor=predecessor,
            )
            payload = json.loads(asyncio.run(adapter.acquire()).payload)

        self.assertEqual(payload["provider_timestamp_at"], SLOT)
        self.assertEqual(
            payload["provider_revision"]["classification"],
            "PROVIDER_REVISABLE_SNAPSHOT",
        )
        self.assertEqual(payload["provider_revision"]["revision_of"], "obs-previous")
        self.assertEqual(
            payload["provider_revision"]["predecessor_observation_id"],
            "obs-previous",
        )
        self.assertEqual(
            payload["provider_revision"]["source_snapshot_ref"],
            f"https://provider.test/{provider}",
        )

    def test_kraken_futures_route_generalization_preserves_supported_revision_semantics(self) -> None:
        capability_id = "kraken-futures.analytics"
        provider = "kraken-futures"
        cap = next(row for row in runtime_due_policy() if row["id"] == capability_id)
        cases = (
            (
                "derivatives.kraken-futures.PI_ETHUSD.open-interest",
                None,
                None,
            ),
            (
                "derivatives.kraken-futures.PI_ETHUSD.funding",
                "PROVIDER_REVISABLE_SNAPSHOT",
                lambda *_args: {
                    "fingerprint": "previous-fingerprint",
                    "observation_id": "obs-previous",
                },
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            for index, (series_id, revision_classification, predecessor) in enumerate(cases):
                with self.subTest(series_id=series_id):
                    row = _generic_row(
                        series_id,
                        provider=provider,
                        finality="OBSERVED_STATE",
                        value={"metric": series_id.rsplit(".", 1)[-1], "value": "1.25"},
                        revision_classification=revision_classification,
                    )
                    acquisition = _CountingAcquisition(
                        {"status": "PASS", "observations": [row]}
                    )
                    expected = normalize_observations(
                        cap,
                        [row],
                        CYCLE_ID,
                        SLOT,
                        NOW_MS,
                        source_revision=SOURCE_REVISION,
                        semantic_predecessor=predecessor,
                    )[0]
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / f"provider-{index}",
                        source_revision=SOURCE_REVISION,
                        capability_id=capability_id,
                        provider=provider,
                        series_id=series_id,
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                        semantic_predecessor=predecessor,
                    )
                    acquired = asyncio.run(adapter.acquire())
                    self.assertEqual(acquisition.calls[0][0], capability_id)
                    self.assertEqual(acquired.payload, canonical_observation_bytes(expected))
                    payload = json.loads(acquired.payload)
                    if revision_classification is None:
                        self.assertNotIn("provider_revision", payload)
                    else:
                        self.assertEqual(
                            payload["provider_revision"]["classification"],
                            "PROVIDER_REVISABLE_SNAPSHOT",
                        )
                        self.assertEqual(
                            payload["provider_revision"]["revision_of"],
                            "obs-previous",
                        )

    def test_multi_row_forward_once_still_accepts_exactly_one_artifact_lifecycle(self) -> None:
        capability_id = "binance-usdm.m5-current"
        provider = "binance-usdm"
        series_id = "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m"
        rows = [
            _generic_row(
                series_id,
                provider=provider,
                finality="FINALIZED",
                value={"marker": "older"},
                provider_timestamp_at="2026-09-07T11:10:00.000Z",
            ),
            _generic_row(
                series_id,
                provider=provider,
                finality="FINALIZED",
                value={"marker": "latest"},
                provider_timestamp_at=SLOT,
            ),
        ]
        acquisition = _CountingAcquisition({"status": "PASS", "observations": rows})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = SQLiteServerControlRepository(root / "control.sqlite3")
            store = QualifiedDataRootImmutableFilesystem(root / "data")
            request = C9ForwardRequest(
                expected_ms=EXPECTED_MS,
                cycle_id="f5c-cardinality-single-artifact-test",
                canonical_slot=SLOT,
                staging_root=root / "provider",
                source_revision=SOURCE_REVISION,
                at=NOW,
                claim_owner="worker-cardinality",
                policy_revision_identity="policy-cardinality",
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
            )
            result = asyncio.run(
                forward_once(
                    request,
                    repository=repo,
                    object_store=store,
                    acquisition=acquisition,
                    clock_ms=lambda: NOW_MS,
                )
            )

            payload = json.loads(result.payload)
            self.assertEqual(payload["provider_timestamp_at"], SLOT)
            self.assertEqual(_row_count(repo, "work"), 1)
            self.assertEqual(_row_count(repo, "attempt"), 1)
            self.assertEqual(_row_count(repo, "publication"), 1)
            self.assertEqual(len(repo.list_generations()), 1)

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


    def test_c9_forward_reuses_canonical_adapter_same_work_and_existing_publication_access(self) -> None:
        core = CanonicalAcquisitionCore()
        provider_result = _provider_result()
        with tempfile.TemporaryDirectory() as td, patch.object(
            core, "_spot", return_value=provider_result
        ) as fake_provider:
            root = Path(td)
            repo = SQLiteServerControlRepository(root / "control.sqlite3")
            store = QualifiedDataRootImmutableFilesystem(root / "data")
            request = C9ForwardRequest(
                expected_ms=EXPECTED_MS,
                cycle_id="f5c-c9-forward-test",
                canonical_slot=SLOT,
                staging_root=root / "provider",
                source_revision=SOURCE_REVISION,
                at=NOW,
                claim_owner="worker-c9",
                policy_revision_identity="policy-c9",
            )
            result = asyncio.run(
                forward_once(
                    request,
                    repository=repo,
                    object_store=store,
                    acquisition=core,
                    clock_ms=lambda: NOW_MS,
                )
            )

            fake_provider.assert_called_once_with("binance-spot", "binance-spot.m5", EXPECTED_MS)
            work = repo.get_work(result.work_id)
            publication = repo.get_publication(result.publication_id)
            generation = repo.resolve_generation(publication.domain_artifact_identity)
            self.assertIsNotNone(work)
            self.assertIsNotNone(publication)
            self.assertIsNotNone(generation)
            self.assertEqual(work.state, "SUCCEEDED")
            self.assertEqual(_row_count(repo, "work"), 1)
            self.assertEqual(_row_count(repo, "attempt"), 1)
            self.assertEqual(_row_count(repo, "publication"), 1)
            self.assertEqual(len(repo.list_generations()), 1)
            self.assertEqual(store.read_exact(hashlib.sha256(result.payload).hexdigest()), result.payload)
            self.assertIn("DataBridgeF5CAcquisitionAdapter", inspect.getsource(c9_forward_module))
            self.assertNotIn("accept_and_claim(", inspect.getsource(c9_forward_module.forward_once))
            self.assertNotIn("accept_work(", inspect.getsource(c9_forward_module.forward_once))


    def test_generic_provider_forward_reuses_existing_durable_lifecycle(self) -> None:
        capability_id = "kraken-spot.m5"
        provider = "kraken-spot"
        series_id = "spot.kraken-spot.ETHUSD.ohlcv.5m"
        row = _generic_row(
            series_id,
            provider=provider,
            finality="FINALIZED",
            value={"open": "100", "high": "101", "low": "99", "close": "100.5"},
        )
        acquisition = _CountingAcquisition({"status": "PASS", "observations": [row]})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = SQLiteServerControlRepository(root / "control.sqlite3")
            store = QualifiedDataRootImmutableFilesystem(root / "data")
            request = C9ForwardRequest(
                expected_ms=EXPECTED_MS,
                cycle_id="f5c-generic-provider-forward-test",
                canonical_slot=SLOT,
                staging_root=root / "provider",
                source_revision=SOURCE_REVISION,
                at=NOW,
                claim_owner="worker-generic-provider",
                policy_revision_identity="policy-generic-provider",
                capability_id=capability_id,
                provider=provider,
                series_id=series_id,
            )
            result = asyncio.run(
                forward_once(
                    request,
                    repository=repo,
                    object_store=store,
                    acquisition=acquisition,
                    clock_ms=lambda: NOW_MS,
                )
            )

            self.assertEqual(acquisition.calls[0][0], capability_id)
            work = repo.get_work(result.work_id)
            publication = repo.get_publication(result.publication_id)
            generation = repo.resolve_generation(publication.domain_artifact_identity)
            self.assertIsNotNone(work)
            self.assertIsNotNone(publication)
            self.assertIsNotNone(generation)
            self.assertEqual(work.state, "SUCCEEDED")
            self.assertEqual(_row_count(repo, "work"), 1)
            self.assertEqual(_row_count(repo, "attempt"), 1)
            self.assertEqual(_row_count(repo, "publication"), 1)
            self.assertEqual(len(repo.list_generations()), 1)
            digest = hashlib.sha256(result.payload).hexdigest()
            self.assertEqual(store.read_exact(digest), result.payload)

    def test_invalid_generic_routes_fail_before_provider_callback(self) -> None:
        cases = (
            {
                "name": "unknown-capability",
                "capability_id": "missing-capability",
                "provider": "kraken-spot",
                "series_id": "spot.kraken-spot.ETHUSD.ohlcv.5m",
            },
            {
                "name": "provider-mismatch",
                "capability_id": "kraken-spot.m5",
                "provider": "binance-spot",
                "series_id": "spot.kraken-spot.ETHUSD.ohlcv.5m",
            },
            {
                "name": "undeclared-series",
                "capability_id": "kraken-spot.m5",
                "provider": "kraken-spot",
                "series_id": "spot.kraken-spot.ETHUSD.ohlcv.1m",
            },
        )
        with tempfile.TemporaryDirectory() as td:
            for index, case in enumerate(cases):
                with self.subTest(case=case["name"]):
                    acquisition = _CountingAcquisition(
                        {"status": "PASS", "observations": []}
                    )
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / f"provider-{index}",
                        source_revision=SOURCE_REVISION,
                        capability_id=case["capability_id"],
                        provider=case["provider"],
                        series_id=case["series_id"],
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                    )
                    with self.assertRaises(
                        (
                            DataBridgeF5CAcquisitionError,
                            capability_routing.CapabilityRoutingError,
                        )
                    ):
                        asyncio.run(adapter.acquire())
                    self.assertEqual(acquisition.calls, [])

    def test_ambiguous_series_routing_fails_before_provider_callback(self) -> None:
        acquisition = _CountingAcquisition({"status": "PASS", "observations": []})
        rule = {
            "series_id_regex": "^spot\\.kraken-spot\\.[A-Z0-9_-]+\\.ohlcv\\.5m$",
            "lifecycle_class": "FIXED_GRID",
            "normalization_family": "OHLCV",
            "finality_policy": "FINALIZED_ONLY",
            "allowed_finality": ["FINALIZED"],
            "publication_eligibility": "VALIDATED_TERMINAL_CHECKPOINT_V2",
        }
        contract = {
            "due_policy": {
                "capabilities": [
                    {
                        "id": "kraken-spot.m5",
                        "provider": "kraken-spot",
                        "cadence_minutes": 5,
                        "schedule_anchor_utc": "1970-01-01T00:00:00Z",
                        "required": False,
                        "forwarding": {
                            "target_residence_role": "WARM",
                            "series_rules": [rule, dict(rule)],
                        },
                    }
                ]
            }
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ambiguous-routing-contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            capability_routing.load_default_declarations.cache_clear()
            try:
                with patch.object(capability_routing, "CONTRACT_PATH", path):
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS,
                        cycle_id=CYCLE_ID,
                        canonical_slot=SLOT,
                        staging_root=Path(td) / "provider",
                        source_revision=SOURCE_REVISION,
                        capability_id="kraken-spot.m5",
                        provider="kraken-spot",
                        series_id="spot.kraken-spot.ETHUSD.ohlcv.5m",
                        acquisition=acquisition,
                        clock_ms=lambda: NOW_MS,
                    )
                    with self.assertRaisesRegex(
                        capability_routing.CapabilityRoutingError,
                        "must match exactly one declaration",
                    ):
                        asyncio.run(adapter.acquire())
            finally:
                capability_routing.load_default_declarations.cache_clear()
        self.assertEqual(acquisition.calls, [])

    def test_missing_routing_contract_fails_before_provider_callback(self) -> None:
        class CountingAcquisition:
            def __init__(self) -> None:
                self.calls = 0

            def collect(self, *_args, **_kwargs):
                self.calls += 1
                return _provider_result()

        acquisition = CountingAcquisition()
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing-routing-contract.json"
            capability_routing.load_default_declarations.cache_clear()
            try:
                with patch.object(capability_routing, "CONTRACT_PATH", missing):
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS, cycle_id=CYCLE_ID, canonical_slot=SLOT,
                        staging_root=Path(td) / "provider", source_revision=SOURCE_REVISION,
                        acquisition=acquisition, clock_ms=lambda: NOW_MS,
                    )
                    with self.assertRaisesRegex(capability_routing.CapabilityRoutingError, "missing"):
                        asyncio.run(adapter.acquire())
            finally:
                capability_routing.load_default_declarations.cache_clear()
        self.assertEqual(acquisition.calls, 0)

    def test_invalid_routing_contract_fails_before_provider_callback(self) -> None:
        class CountingAcquisition:
            def __init__(self) -> None:
                self.calls = 0

            def collect(self, *_args, **_kwargs):
                self.calls += 1
                return _provider_result()

        acquisition = CountingAcquisition()
        with tempfile.TemporaryDirectory() as td:
            invalid = Path(td) / "invalid-routing-contract.json"
            invalid.write_text("{not-json", encoding="utf-8")
            capability_routing.load_default_declarations.cache_clear()
            try:
                with patch.object(capability_routing, "CONTRACT_PATH", invalid):
                    adapter = DataBridgeF5CAcquisitionAdapter(
                        expected_ms=EXPECTED_MS, cycle_id=CYCLE_ID, canonical_slot=SLOT,
                        staging_root=Path(td) / "provider", source_revision=SOURCE_REVISION,
                        acquisition=acquisition, clock_ms=lambda: NOW_MS,
                    )
                    with self.assertRaisesRegex(capability_routing.CapabilityRoutingError, "unreadable"):
                        asyncio.run(adapter.acquire())
            finally:
                capability_routing.load_default_declarations.cache_clear()
        self.assertEqual(acquisition.calls, 0)

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
