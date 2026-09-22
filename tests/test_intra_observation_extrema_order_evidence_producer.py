from __future__ import annotations

import hashlib
import inspect
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools.history_access_v2 import build_semantic_receipt, compact
from tools.intra_observation_extrema_order_evidence import (
    canonical_json_bytes,
    compute_carrier_fingerprint,
    compute_evidence_fingerprint,
    validate_carrier_fingerprints,
)
from tools import intra_observation_extrema_order_evidence_producer as producer


PARENT_ID = "synthetic.exchange.XYZQUOTE.ohlcv.1h"
CHILD_ID = "synthetic.exchange.XYZQUOTE.ohlcv.5m"
START = "2026-01-01T00:00:00Z"
END = "2026-01-01T01:00:00Z"
FIXED_KNOWN = "2026-01-02T00:00:00Z"


def _ms(value: str) -> int:
    return int(
        datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
    )


def _iso(ms: int) -> str:
    return (
        datetime.fromtimestamp(ms / 1000, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _row(
    open_time: str,
    *,
    open_value: str = "95",
    high: str = "99",
    low: str = "91",
    close: str = "96",
    volume: str = "1",
) -> dict[str, str]:
    return {
        "open_time": open_time,
        "open": open_value,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def _child_rows(
    *,
    high_indices: tuple[int, ...] = (2,),
    low_indices: tuple[int, ...] = (8,),
    exact_high: str = "100",
    exact_low: str = "90",
) -> list[dict[str, str]]:
    start = _ms(START)
    rows = []
    for index in range(12):
        high = exact_high if index in high_indices else "99"
        low = exact_low if index in low_indices else "91"
        rows.append(
            _row(
                _iso(start + index * 300_000),
                high=high,
                low=low,
            )
        )
    return rows


def _parent_row(
    *, high: str = "100", low: str = "90"
) -> dict[str, str]:
    return _row(START, high=high, low=low)


def _semantic_observations(rows: list[dict[str, str]]) -> list[dict]:
    return [
        {
            "timestamp_ms": _ms(row["open_time"]),
            "value": {
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            },
            "finality": "FINALIZED",
        }
        for row in rows
    ]


def _bundle(
    series_id: str,
    interval: str,
    interval_ms: int,
    rows: list[dict[str, str]],
    *,
    provider_id: str = "synthetic-provider",
    instrument: str = "XYZQUOTE",
    value_semantics: str | None = None,
    unit: str | None = None,
) -> tuple[dict, str, dict, dict]:
    start_ms, end_ms = _ms(START), _ms(END)
    series = {
        "series_id": series_id,
        "series": "ohlcv",
        "instrument": instrument,
        "interval": interval,
        "interval_ms": interval_ms,
        "provider_id": provider_id,
        "source_provider": "synthetic",
        "source_interval_or_metric": interval,
        "profile_id": "synthetic.history",
        "history_mode": "MAX_AVAILABLE",
        "availability_status": "PASS",
    }
    if value_semantics is not None:
        series["value_semantics"] = value_semantics
    if unit is not None:
        series["unit"] = unit
    plan_sha = hashlib.sha256(
        f"{series_id}:{interval}:{provider_id}:{instrument}".encode()
    ).hexdigest()
    plan = {
        "schema_version": "market-data-resolution-plan/1.0.0",
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {},
        "request": {
            "series_id": series_id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "cutoff_ms": None,
        },
        "series": series,
        "segments": [],
        "plan_sha256": plan_sha,
    }
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    semantic = build_semantic_receipt(
        series_id=series_id,
        start_ms=start_ms,
        end_ms=end_ms,
        cutoff_ms=None,
        mode="strict",
        current_policy="FINALIZED_ONLY",
        resolution_plan_sha256=plan_sha,
        observations=_semantic_observations(rows),
        finality="FINALIZED",
        revision_context=None,
    )
    receipt = {
        "schema_version": "history-consumer-receipt/1.0.0",
        "receipt_role": "LEGACY_TRANSPORT_WRAPPER",
        "route": dict(producer._CANONICAL_ROUTE),
        "series_id": series_id,
        "plan_sha256": plan_sha,
        "semantic_output_sha256": semantic["output_sha256"],
        "semantic_receipt_sha256": hashlib.sha256(compact(semantic)).hexdigest(),
        "transport_output_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "semantic_receipt": semantic,
    }
    diagnostics = {
        "status": "PASS",
        "gap_count": 0,
        "rows": len(rows),
        "expected_rows": len(rows),
    }
    return plan, payload, diagnostics, receipt


def _reader(
    parent_rows: list[dict[str, str]],
    child_rows: list[dict[str, str]],
    *,
    parent_kwargs: dict | None = None,
    child_kwargs: dict | None = None,
):
    parent = _bundle(
        PARENT_ID, "1h", 3_600_000, parent_rows, **(parent_kwargs or {})
    )
    child = _bundle(
        CHILD_ID, "5m", 300_000, child_rows, **(child_kwargs or {})
    )

    def read(series_id, *_args, **_kwargs):
        if series_id == PARENT_ID:
            return parent
        if series_id == CHILD_ID:
            return child
        raise AssertionError(series_id)

    return read


def _produce(
    parent_rows: list[dict[str, str]] | None = None,
    child_rows: list[dict[str, str]] | None = None,
    *,
    reader=None,
    cutoff: str | None = None,
    known_at: str = FIXED_KNOWN,
) -> list[dict]:
    parent_rows = parent_rows or [_parent_row()]
    child_rows = child_rows or _child_rows()
    reader = reader or _reader(parent_rows, child_rows)
    with (
        patch.object(producer, "_canonical_read_history", side_effect=reader),
        patch.object(producer, "_utc_now", return_value=known_at),
    ):
        return producer.produce_extrema_order_evidence(
            PARENT_ID,
            CHILD_ID,
            START,
            END,
            query_cutoff_utc=cutoff,
        )


class ProducerDerivationTests(unittest.TestCase):
    def test_01_high_before_low(self):
        carrier = _produce()[0]
        self.assertEqual(carrier["derived_result"], "HIGH_BEFORE_LOW")
        self.assertEqual(carrier["earliest_parent_high_occurrence"], "2026-01-01T00:10:00Z")
        self.assertEqual(carrier["earliest_parent_low_occurrence"], "2026-01-01T00:40:00Z")

    def test_02_low_before_high(self):
        carrier = _produce(child_rows=_child_rows(high_indices=(8,), low_indices=(2,)))[0]
        self.assertEqual(carrier["derived_result"], "LOW_BEFORE_HIGH")

    def test_03_same_child_is_unresolved(self):
        carrier = _produce(child_rows=_child_rows(high_indices=(2,), low_indices=(2,)))[0]
        self.assertEqual(
            carrier["derived_result"],
            "UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE",
        )
        self.assertEqual(
            carrier["earliest_parent_high_occurrence"],
            carrier["earliest_parent_low_occurrence"],
        )

    def test_04_flat_parent_is_not_materially_distinct(self):
        flat = _row(
            START,
            open_value="100",
            high="100",
            low="100",
            close="100",
        )
        carrier = _produce(parent_rows=[flat])[0]
        self.assertEqual(carrier["derived_result"], "ORDER_NOT_MATERIALLY_DISTINCT")
        self.assertNotIn("child_series_id", carrier)
        self.assertEqual(carrier["proof_granularity"], "PARENT_ONLY_FLAT")

    def test_05_repeated_high_selects_earliest(self):
        carrier = _produce(child_rows=_child_rows(high_indices=(2, 3), low_indices=(8,)))[0]
        self.assertEqual(carrier["earliest_parent_high_occurrence"], "2026-01-01T00:10:00Z")

    def test_06_repeated_low_selects_earliest(self):
        carrier = _produce(child_rows=_child_rows(high_indices=(8,), low_indices=(2, 3)))[0]
        self.assertEqual(carrier["earliest_parent_low_occurrence"], "2026-01-01T00:10:00Z")

    def test_07_public_api_has_no_occurrence_selector(self):
        params = inspect.signature(producer.produce_extrema_order_evidence).parameters
        self.assertNotIn("selected_extremum_occurrence", params)
        self.assertNotIn("occurrence", params)

    def test_08_public_api_has_no_winner_or_order_assertion(self):
        params = inspect.signature(producer.produce_extrema_order_evidence).parameters
        for forbidden in ("winner", "caller_order_assertion", "high_before_low", "low_before_high"):
            self.assertNotIn(forbidden, params)

    def test_09_provider_mismatch_fails_closed(self):
        reader = _reader(
            [_parent_row()],
            _child_rows(),
            child_kwargs={"provider_id": "other-provider"},
        )
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "PROVIDER_MISMATCH"):
            _produce(reader=reader)

    def test_10_instrument_mismatch_fails_closed(self):
        reader = _reader(
            [_parent_row()],
            _child_rows(),
            child_kwargs={"instrument": "OTHER"},
        )
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "INSTRUMENT_MISMATCH"):
            _produce(reader=reader)

    def test_11_unit_mismatch_fails_closed(self):
        reader = _reader(
            [_parent_row()],
            _child_rows(),
            parent_kwargs={"unit": "QUOTE_ASSET"},
            child_kwargs={"unit": "USD"},
        )
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "UNIT_MISMATCH"):
            _produce(reader=reader)

    def test_12_value_semantics_mismatch_fails_closed(self):
        reader = _reader(
            [_parent_row()],
            _child_rows(),
            parent_kwargs={"value_semantics": "PRICE"},
            child_kwargs={"value_semantics": "INDEX"},
        )
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "VALUE_SEMANTICS_MISMATCH"):
            _produce(reader=reader)

    def test_13_equal_child_resolution_rejected(self):
        child = _bundle(CHILD_ID, "1h", 3_600_000, [_parent_row()])
        parent = _bundle(PARENT_ID, "1h", 3_600_000, [_parent_row()])
        def read(series_id, *_a, **_k):
            return parent if series_id == PARENT_ID else child
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "CHILD_RESOLUTION_NOT_STRICTLY_FINER"):
            _produce(reader=read)

    def test_14_coarser_child_resolution_rejected(self):
        child = _bundle(CHILD_ID, "2h", 7_200_000, [_parent_row()])
        parent = _bundle(PARENT_ID, "1h", 3_600_000, [_parent_row()])
        def read(series_id, *_a, **_k):
            return parent if series_id == PARENT_ID else child
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "CHILD_RESOLUTION_NOT_STRICTLY_FINER"):
            _produce(reader=read)

    def test_15_child_coverage_gap_fails_closed(self):
        rows = _child_rows()
        rows.pop(4)
        reader = _reader([_parent_row()], rows)
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "INCOMPLETE_WINDOW"):
            _produce(reader=reader)

    def test_16_conflicting_child_overlap_fails_closed(self):
        rows = _child_rows()
        conflicting = dict(rows[3])
        conflicting["high"] = "100"
        rows.insert(4, conflicting)
        reader = _reader([_parent_row()], rows)
        with self.assertRaisesRegex(producer.ExtremaOrderEvidenceProducerError, "INCOMPLETE_WINDOW|CHRONOLOGY_CONFLICT"):
            _produce(reader=reader)

    def test_17_cross_provider_substitution_is_not_attempted(self):
        calls = []
        exact = _reader([_parent_row()], _child_rows())
        def read(series_id, *args, **kwargs):
            calls.append(series_id)
            return exact(series_id, *args, **kwargs)
        _produce(reader=read)
        self.assertEqual(calls, [PARENT_ID, CHILD_ID])

    def test_18_supporting_refs_preserve_physical_chronology(self):
        refs = _produce()[0]["supporting_child_observation_refs"]
        times = [ref.split(":")[3] for ref in refs]
        self.assertEqual(refs, list(refs))
        self.assertEqual(len(refs), 12)
        self.assertEqual(times, sorted(times))

    def test_19_reordering_refs_changes_evidence_fingerprint(self):
        carrier = _produce()[0]
        original = carrier["evidence_fingerprint"]
        changed = dict(carrier)
        changed["supporting_child_observation_refs"] = list(
            reversed(carrier["supporting_child_observation_refs"])
        )
        self.assertNotEqual(original, compute_evidence_fingerprint(changed))

    def test_20_query_cutoff_is_not_immutable_identity(self):
        later = "2026-01-03T00:00:00Z"
        first = _produce(cutoff=None)[0]
        second = _produce(cutoff=later)[0]
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertEqual(first["carrier_fingerprint"], second["carrier_fingerprint"])

    def test_21_backdated_known_at_fails_reference_validation(self):
        carrier = _produce()[0]
        carrier["evidence_available_at_utc"] = "2026-01-02T00:00:01Z"
        carrier["known_at_utc"] = "2026-01-02T00:00:00Z"
        carrier["carrier_fingerprint"] = compute_carrier_fingerprint(carrier)
        result = validate_carrier_fingerprints(carrier)
        self.assertEqual(result["reason_code"], "PIT_BACKDATED")

    def test_22_future_known_evidence_is_pit_ineligible(self):
        cutoff = "2026-01-01T12:00:00Z"
        carrier = _produce(cutoff=cutoff)[0]
        result = validate_carrier_fingerprints(carrier, cutoff)
        self.assertEqual(result["status"], "PIT_INELIGIBLE")

    def test_23_event_effective_after_known_at_not_rejected(self):
        carrier = _produce(known_at="2025-12-31T23:59:00Z")[0]
        result = validate_carrier_fingerprints(carrier)
        self.assertEqual(result["status"], "VALID")
        self.assertGreater(carrier["event_effective_at"], carrier["known_at_utc"])

    def test_24_produced_carrier_passes_reference_validator(self):
        result = validate_carrier_fingerprints(_produce()[0])
        self.assertEqual(result["status"], "VALID")

    def test_25_exact_decimal_text_never_roundtrips_through_float(self):
        parent = [
            _row(
                START,
                open_value="0.09500000000000001",
                high="0.10000000000000001",
                low="0.09000000000000001",
                close="0.09600000000000001",
            )
        ]
        child = _child_rows(
            high_indices=(2,),
            low_indices=(8,),
            exact_high="0.10000000000000001",
            exact_low="0.09000000000000001",
        )
        for row in child:
            if row["high"] == "99":
                row["high"] = "0.09900000000000001"
            if row["low"] == "91":
                row["low"] = "0.09100000000000001"
            row["open"] = "0.09500000000000001"
            row["close"] = "0.09600000000000001"
        carrier = _produce(parent_rows=parent, child_rows=child)[0]
        self.assertEqual(carrier["parent_high"], "0.10000000000000001")
        self.assertEqual(carrier["parent_low"], "0.09000000000000001")

    def test_26_source_contains_no_wave_semantics(self):
        text = Path(producer.__file__).read_text(encoding="utf-8").lower()
        for forbidden in ("neowave", "monowave", "termination", "elliott"):
            self.assertNotIn(forbidden, text)

    def test_27_source_contains_no_direct_provider_acquisition(self):
        text = Path(producer.__file__).read_text(encoding="utf-8").lower()
        for forbidden in ("requests.", "urllib.", "binance", "kraken", "urlopen"):
            self.assertNotIn(forbidden, text)

    def test_28_same_child_does_not_attempt_event_fallback(self):
        carrier = _produce(child_rows=_child_rows(high_indices=(2,), low_indices=(2,)))[0]
        self.assertEqual(
            carrier["derived_result"],
            "UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE",
        )
        self.assertNotIn("source_event_refs", carrier)
        self.assertNotIn("event_ordering_rule", carrier)

    def test_29_observation_fingerprint_is_canonical_row_hash(self):
        row = _parent_row()
        expected = "sha256:" + hashlib.sha256(canonical_json_bytes(row)).hexdigest()
        self.assertEqual(producer.observation_fingerprint(row), expected)

    def test_30_child_window_fingerprint_is_complete_ordered_rows_hash(self):
        rows = _child_rows()
        expected = "sha256:" + hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        self.assertEqual(producer.child_window_fingerprint(rows), expected)


if __name__ == "__main__":
    unittest.main()
