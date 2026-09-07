"""Bounded Data Bridge provider/domain adapter for the F5C C3 acquisition seam."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from acquisition_core import CanonicalAcquisitionCore
from aife_server_adapter import adapt_d8_observation_with_payload
from d8_capability_routing import route_capability_series, runtime_due_policy
from d8_observation_normalizer import normalize_observations
from server.acquisition.ports import AcquiredArtifact

C3_CAPABILITY_ID = "binance-spot.m5"
C3_PROVIDER = "binance-spot"
C3_DEFAULT_SERIES_ID = "spot.binance-spot.ETHUSDT.ohlcv.5m"


class DataBridgeF5CAcquisitionError(ValueError):
    """The bounded C3 Data Bridge acquisition result is not uniquely admissible."""


class DataBridgeF5CAcquisitionAdapter:
    """Adapt one existing Binance Spot M5 domain member into the generic C1 result."""

    def __init__(
        self,
        *,
        expected_ms: int,
        cycle_id: str,
        canonical_slot: str,
        staging_root: Path,
        source_revision: str,
        series_id: str = C3_DEFAULT_SERIES_ID,
        acquisition: CanonicalAcquisitionCore | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        if not isinstance(source_revision, str) or not source_revision:
            raise DataBridgeF5CAcquisitionError("source_revision is required")
        if not isinstance(series_id, str) or not series_id:
            raise DataBridgeF5CAcquisitionError("series_id is required")
        self.expected_ms = int(expected_ms)
        self.cycle_id = cycle_id
        self.canonical_slot = canonical_slot
        self.staging_root = Path(staging_root)
        self.source_revision = source_revision
        self.series_id = series_id
        self.acquisition = acquisition or CanonicalAcquisitionCore()
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    @staticmethod
    def _capability() -> dict[str, object]:
        matches = [row for row in runtime_due_policy() if row["id"] == C3_CAPABILITY_ID]
        if len(matches) != 1 or matches[0].get("provider") != C3_PROVIDER:
            raise DataBridgeF5CAcquisitionError(
                "binance-spot.m5 capability declaration is missing or ambiguous"
            )
        return matches[0]

    async def acquire(self) -> AcquiredArtifact:
        """Reuse Data Bridge acquisition + normalization and return exact canonical bytes."""
        result = self.acquisition.collect(
            C3_CAPABILITY_ID,
            expected_ms=self.expected_ms,
            cycle_id=self.cycle_id,
            staging_root=self.staging_root,
        )
        if not isinstance(result, dict) or result.get("status") != "PASS":
            raise DataBridgeF5CAcquisitionError("Data Bridge capability acquisition did not PASS")
        rows = result.get("observations")
        if not isinstance(rows, list):
            raise DataBridgeF5CAcquisitionError("Data Bridge observations must be a list")

        cap = self._capability()
        normalized = normalize_observations(
            cap,
            rows,
            self.cycle_id,
            self.canonical_slot,
            self.clock_ms(),
            source_revision=self.source_revision,
        )
        selected = [row for row in normalized if row.get("series_id") == self.series_id]
        if len(selected) != 1:
            raise DataBridgeF5CAcquisitionError(
                "bounded binance-spot.m5 series selection must resolve exactly one observation"
            )

        observation = selected[0]
        route_capability_series(
            C3_CAPABILITY_ID,
            C3_PROVIDER,
            self.series_id,
        )
        envelope, payload = adapt_d8_observation_with_payload(observation)
        return AcquiredArtifact(envelope=envelope, payload=payload)
