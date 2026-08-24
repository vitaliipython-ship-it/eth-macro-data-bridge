from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from d8_capability_routing import route_capability_series
from d8_runtime import D8Runtime, DeterministicMockAcquisition, RuntimeConfig
from history_publication_batch import build_publication_batch, validate_publication_batch

NOW_MS = int(datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
SLOT = "2026-08-24T12:00:00.000Z"
EFFECTIVE = "2026-08-24T11:55:00.000Z"


class R1RevisionAndPublicationCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = D8Runtime(
            RuntimeConfig(state_root=Path(self.tmp.name), profile="test", source_revision="r1-fixture"),
            DeterministicMockAcquisition(),
            clock_ms=lambda: NOW_MS,
        )
        self.kraken_cap = {
            "id": "kraken-futures.analytics",
            "provider": "kraken-futures",
            "every_minutes": 60,
        }
        self.options_cap = {
            "id": "deribit-options.surface-dvol",
            "provider": "deribit-options",
            "every_minutes": 60,
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def revisable_row(value: dict[str, object]) -> dict[str, object]:
        return {
            "series_id": "derivatives.kraken-futures.PI_ETHUSD.spreads",
            "provider_timestamp_at": EFFECTIVE,
            "known_at": SLOT,
            "provider_route": "https://futures.kraken.com/api/charts/v1/analytics",
            "finality": "OBSERVED_STATE",
            "freshness": {"status": "LIVE_USABLE", "age_seconds": 300, "target_cadence_seconds": 3600},
            "value": value,
            "revision_classification": "PROVIDER_REVISABLE_SNAPSHOT",
            "source_snapshot_ref": "kraken-fixture",
            "provenance": {
                "metric_policy_schema": "kraken-futures-provider-revision/1.0.0",
                "revision_evidence_schema": "market-data-provider-revision/1.0.0",
            },
        }

    def test_changed_revisable_payload_creates_distinct_bound_revision_evidence(self):
        first = self.runtime._normalize_observations(
            self.kraken_cap,
            [self.revisable_row({"bid": "1900", "ask": "1901"})],
            "cycle-a",
            SLOT,
            NOW_MS,
        )[0]
        payload = json.dumps(first, sort_keys=True, separators=(",", ":"))
        with self.runtime.state.connect() as db:
            db.execute(
                "INSERT INTO spool(observation_id,cycle_id,capability_id,payload_json,payload_bytes,created_at,expires_at,state) VALUES(?,?,?,?,?,?,?,'PENDING')",
                (first["observation_id"], "cycle-a", self.kraken_cap["id"], payload, len(payload.encode()), NOW_MS, NOW_MS + 86_400_000),
            )

        second = self.runtime._normalize_observations(
            self.kraken_cap,
            [self.revisable_row({"bid": "1900.5", "ask": "1901.5"})],
            "cycle-b",
            SLOT,
            NOW_MS + 60_000,
        )[0]

        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(first["observation_id"], second["observation_id"])
        revision = second["provider_revision"]
        self.assertEqual(revision["schema_version"], "market-data-provider-revision/1.0.0")
        self.assertEqual(revision["metric_policy_schema"], "kraken-futures-provider-revision/1.0.0")
        self.assertEqual(revision["revision_of"], first["observation_id"])
        self.assertEqual(revision["predecessor_observation_id"], first["observation_id"])
        self.assertEqual(revision["previous_value_fingerprint"], first["fingerprint"])
        self.assertEqual(revision["observed_value"], {"bid": "1900.5", "ask": "1901.5"})
        self.assertEqual(revision["known_at_utc"], SLOT)

    def test_strict_kraken_family_does_not_synthesize_revision_evidence(self):
        row = {
            "series_id": "derivatives.kraken-futures.PI_ETHUSD.open-interest",
            "provider_timestamp_at": EFFECTIVE,
            "known_at": SLOT,
            "provider_route": "kraken-fixture",
            "finality": "OBSERVED_STATE",
            "freshness": {"status": "LIVE_USABLE", "age_seconds": 300, "target_cadence_seconds": 3600},
            "value": {"value": "100"},
        }
        envelope = self.runtime._normalize_observations(self.kraken_cap, [row], "cycle-a", SLOT, NOW_MS)[0]
        self.assertNotIn("provider_revision", envelope)

    def test_multirow_dvol_has_stable_unique_identity_and_publication_batch(self):
        rows = [
            {
                "series_id": "options.deribit-options.ETH.dvol.1h",
                "provider_timestamp_at": "2026-08-24T10:00:00.000Z",
                "known_at": SLOT,
                "provider_route": "deribit-fixture",
                "finality": "FINALIZED",
                "freshness": {"status": "RECENT_CONTEXT", "age_seconds": 7200, "target_cadence_seconds": 3600},
                "value": {"timestamp_ms": NOW_MS - 7_200_000, "open": "60", "high": "62", "low": "59", "close": "61"},
            },
            {
                "series_id": "options.deribit-options.ETH.dvol.1h",
                "provider_timestamp_at": "2026-08-24T11:00:00.000Z",
                "known_at": SLOT,
                "provider_route": "deribit-fixture",
                "finality": "FINALIZED",
                "freshness": {"status": "LIVE_USABLE", "age_seconds": 3600, "target_cadence_seconds": 3600},
                "value": {"timestamp_ms": NOW_MS - 3_600_000, "open": "61", "high": "63", "low": "60", "close": "62"},
            },
        ]
        first = self.runtime._normalize_observations(self.options_cap, rows, "cycle-dvol", SLOT, NOW_MS)
        replay = self.runtime._normalize_observations(self.options_cap, rows, "cycle-dvol", SLOT, NOW_MS)
        first_ids = [row["observation_id"] for row in first]
        replay_ids = [row["observation_id"] for row in replay]
        self.assertEqual(len(first_ids), 2)
        self.assertEqual(len(set(first_ids)), 2)
        self.assertEqual(first_ids, replay_ids)
        self.assertEqual([row["provider_timestamp_at"] for row in first], sorted(row["provider_timestamp_at"] for row in first))
        route = route_capability_series(
            "deribit-options.surface-dvol",
            "deribit-options",
            "options.deribit-options.ETH.dvol.1h",
        )
        self.assertEqual(route["lifecycle_class"], "FIXED_GRID")
        self.assertIn("FINALIZED", route["allowed_finality"])
        batch = build_publication_batch(first)
        validate_publication_batch(batch)
        self.assertEqual(batch["member_count"], 2)
        self.assertEqual(len(set(batch["member_observation_ids"])), 2)

    def test_every_new_r1_series_family_is_routable_by_existing_router(self):
        cases = [
            ("binance-spot.15m", "binance-spot", "spot.binance-spot.ETHUSDT.ohlcv.15m", "FIXED_GRID"),
            ("binance-spot.4h", "binance-spot", "spot.binance-spot.ETHUSDT.ohlcv.4h", "FIXED_GRID"),
            ("binance-spot.1d", "binance-spot", "spot.binance-spot.ETHUSDT.ohlcv.1d", "FIXED_GRID"),
            ("binance-spot.1w", "binance-spot", "spot.binance-spot.ETHUSDT.ohlcv.1w", "FIXED_GRID"),
            ("kraken-spot.15m", "kraken-spot", "spot.kraken-spot.ETHUSD.ohlcv.15m", "FIXED_GRID"),
            ("kraken-spot.1h", "kraken-spot", "spot.kraken-spot.ETHUSD.ohlcv.1h", "FIXED_GRID"),
            ("binance-usdm.m5-current", "binance-usdm", "derivatives.binance-usdm.ETHUSDT.open-interest-history.5m", "FIXED_GRID"),
            ("binance-usdm.m5-current", "binance-usdm", "derivatives.binance-usdm.ETHUSDT.funding-history", "SAMPLED_SCHEDULE"),
            ("deribit-perpetual.h1-history", "deribit-perpetual", "derivatives.deribit-perpetual.ETH-PERPETUAL.funding.1h", "FIXED_GRID"),
            ("deribit-perpetual.h1-history", "deribit-perpetual", "derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h", "FIXED_GRID"),
            ("deribit-options.surface-dvol", "deribit-options", "options.deribit-options.ETH.dvol.1h", "FIXED_GRID"),
            ("deribit-options.surface-dvol", "deribit-options", "liquidity.deribit-options.ETH-28AUG26-2000-C.selected-book", "SAMPLED_SCHEDULE"),
        ]
        for capability_id, provider, series_id, lifecycle in cases:
            with self.subTest(series_id=series_id):
                route = route_capability_series(capability_id, provider, series_id)
                self.assertEqual(route["target_residence_role"], "WARM")
                self.assertEqual(route["lifecycle_class"], lifecycle)


if __name__ == "__main__":
    unittest.main()
