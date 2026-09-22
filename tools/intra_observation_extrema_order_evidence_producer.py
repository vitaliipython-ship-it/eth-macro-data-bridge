from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from tools.history_consumer import read_history as _canonical_read_history
from tools.intra_observation_extrema_order_evidence import (
    CAPABILITY_ID,
    PARENT_CONTRACT_ID,
    canonical_json_bytes,
    compute_carrier_fingerprint,
    compute_evidence_fingerprint,
    validate_carrier_fingerprints,
)

VALUE_SEMANTICS = "PRICE"
UNIT = "QUOTE_ASSET"
ORDERING_SOURCE = "CANONICAL_LOWER_TIMEFRAME_OBSERVATIONS"
LOWER_TF_GRANULARITY = "LOWER_TIMEFRAME"
FLAT_SOURCE = "PARENT_FLAT_VALUE"
FLAT_GRANULARITY = "PARENT_ONLY_FLAT"
UNRESOLVED_OCCURRENCE = "UNRESOLVED_NOT_PHYSICALLY_PROVEN"

_CANONICAL_ROUTE = {
    "route_authority": "bridge-contract.json",
    "discovery": "history/capability-index.json",
    "resolver": "tools/capability_index.py",
    "reader": "tools/history_access.py",
    "reader_input_authority": "ResolutionPlan",
    "execution_adapter": "tools/history_consumer.py",
}


class ExtremaOrderEvidenceProducerError(ValueError):
    """Fail-closed producer error with a stable reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)
        self.reason_code = reason_code
        self.detail = detail


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _parse_utc_ms(value: str, *, field: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExtremaOrderEvidenceProducerError("INVALID_TIME", field)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExtremaOrderEvidenceProducerError("INVALID_TIME", field) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExtremaOrderEvidenceProducerError("INVALID_TIME", field)
    return int(parsed.timestamp() * 1000)


def _format_utc_ms(value: int) -> str:
    parsed = datetime.fromtimestamp(value / 1000, timezone.utc)
    timespec = "seconds" if value % 1000 == 0 else "milliseconds"
    return parsed.isoformat(timespec=timespec).replace("+00:00", "Z")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_ref(payload: Any) -> str:
    return "sha256:" + _sha256_hex(canonical_json_bytes(payload))


def _canonical_line_bytes(payload: Any) -> bytes:
    return canonical_json_bytes(payload) + b"\n"


def observation_fingerprint(observation: dict[str, Any]) -> str:
    """Fingerprint one exact canonical rendered history observation."""

    return _sha256_ref(observation)


def child_window_fingerprint(observations: list[dict[str, Any]]) -> str:
    """Fingerprint a complete child window in physical semantic chronology."""

    return _sha256_ref(observations)


def _observation_ref(series_id: str, observation: dict[str, Any]) -> str:
    return (
        f"obs:{series_id}:{observation['open_time']}:"
        f"{observation_fingerprint(observation)}"
    )


def _semantic_observations(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for row in observations:
        result.append(
            {
                "timestamp_ms": _parse_utc_ms(
                    row["open_time"], field="observation.open_time"
                ),
                "value": {
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                },
                "finality": "FINALIZED",
            }
        )
    return result


def _validate_decimal_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExtremaOrderEvidenceProducerError("INVALID_OBSERVATION", field)
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ExtremaOrderEvidenceProducerError("INVALID_OBSERVATION", field) from exc
    if not parsed.is_finite():
        raise ExtremaOrderEvidenceProducerError("INVALID_OBSERVATION", field)
    return value


def _validate_ohlcv_row(row: Any, *, role: str) -> dict[str, Any]:
    expected = {"open_time", "open", "high", "low", "close", "volume"}
    if not isinstance(row, dict) or set(row) != expected:
        raise ExtremaOrderEvidenceProducerError(
            "INVALID_OBSERVATION", f"{role}:shape"
        )
    _parse_utc_ms(row["open_time"], field=f"{role}.open_time")
    values = {
        name: Decimal(_validate_decimal_text(row[name], f"{role}.{name}"))
        for name in ("open", "high", "low", "close", "volume")
    }
    if (
        values["high"] < max(values["open"], values["low"], values["close"])
        or values["low"] > min(values["open"], values["high"], values["close"])
        or values["volume"] < 0
    ):
        raise ExtremaOrderEvidenceProducerError(
            "INVALID_OBSERVATION", f"{role}:ohlcv_bounds"
        )
    return row


def _validate_grid(
    observations: list[dict[str, Any]],
    *,
    role: str,
    start_ms: int,
    end_ms: int,
    interval_ms: int,
) -> None:
    if interval_ms <= 0 or (end_ms - start_ms) % interval_ms:
        raise ExtremaOrderEvidenceProducerError(
            "INVALID_RESOLUTION", f"{role}:unaligned_range"
        )
    expected_timestamps = list(range(start_ms, end_ms, interval_ms))
    if len(observations) != len(expected_timestamps):
        raise ExtremaOrderEvidenceProducerError(
            "INCOMPLETE_WINDOW", f"{role}:observation_count"
        )
    actual = []
    for row in observations:
        _validate_ohlcv_row(row, role=role)
        actual.append(_parse_utc_ms(row["open_time"], field=f"{role}.open_time"))
    if len(set(actual)) != len(actual):
        raise ExtremaOrderEvidenceProducerError(
            "CHRONOLOGY_CONFLICT", f"{role}:duplicate_timestamp"
        )
    if actual != expected_timestamps:
        raise ExtremaOrderEvidenceProducerError(
            "INCOMPLETE_WINDOW", f"{role}:gap_or_noncanonical_order"
        )


def _validate_semantic_read(
    *,
    role: str,
    series_id: str,
    start_ms: int,
    end_ms: int,
    plan: dict[str, Any],
    payload: str,
    diagnostics: dict[str, Any],
    receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(plan, dict) or not isinstance(receipt, dict):
        raise ExtremaOrderEvidenceProducerError("CANONICAL_ROUTE_INVALID", role)
    request = plan.get("request")
    series = plan.get("series")
    if not isinstance(request, dict) or not isinstance(series, dict):
        raise ExtremaOrderEvidenceProducerError("CANONICAL_ROUTE_INVALID", role)
    if request.get("series_id") != series_id or series.get("series_id") != series_id:
        raise ExtremaOrderEvidenceProducerError("SERIES_IDENTITY_MISMATCH", role)
    if request.get("start_ms") != start_ms or request.get("end_ms") != end_ms:
        raise ExtremaOrderEvidenceProducerError("RANGE_IDENTITY_MISMATCH", role)
    if series.get("series") != "ohlcv":
        raise ExtremaOrderEvidenceProducerError("UNSUPPORTED_SERIES_KIND", role)
    interval_ms = series.get("interval_ms")
    if not isinstance(interval_ms, int) or interval_ms <= 0:
        raise ExtremaOrderEvidenceProducerError("INVALID_RESOLUTION", role)
    if not isinstance(series.get("provider_id"), str) or not series["provider_id"]:
        raise ExtremaOrderEvidenceProducerError("PROVIDER_IDENTITY_MISSING", role)
    if not isinstance(series.get("instrument"), str) or not series["instrument"]:
        raise ExtremaOrderEvidenceProducerError("INSTRUMENT_IDENTITY_MISSING", role)

    if not isinstance(diagnostics, dict):
        raise ExtremaOrderEvidenceProducerError("CANONICAL_ROUTE_INVALID", role)
    if diagnostics.get("status") != "PASS" or diagnostics.get("gap_count") != 0:
        raise ExtremaOrderEvidenceProducerError(
            "INCOMPLETE_WINDOW", f"{role}:reader_diagnostics"
        )

    route = receipt.get("route")
    if not isinstance(route, dict) or any(
        route.get(key) != value for key, value in _CANONICAL_ROUTE.items()
    ):
        raise ExtremaOrderEvidenceProducerError(
            "CANONICAL_ROUTE_INVALID", f"{role}:receipt_route"
        )
    if receipt.get("series_id") != series_id:
        raise ExtremaOrderEvidenceProducerError(
            "SERIES_IDENTITY_MISMATCH", f"{role}:receipt"
        )
    if receipt.get("plan_sha256") != plan.get("plan_sha256"):
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:plan_sha256"
        )
    semantic_receipt = receipt.get("semantic_receipt")
    if not isinstance(semantic_receipt, dict):
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:semantic_receipt"
        )
    if semantic_receipt.get("series_id") != series_id:
        raise ExtremaOrderEvidenceProducerError(
            "SERIES_IDENTITY_MISMATCH", f"{role}:semantic_receipt"
        )
    if semantic_receipt.get("resolution_plan_sha256") != plan.get("plan_sha256"):
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:semantic_plan_sha256"
        )
    if semantic_receipt.get("finality") != "FINALIZED":
        raise ExtremaOrderEvidenceProducerError(
            "FINALITY_MISMATCH", f"{role}:semantic_receipt"
        )

    try:
        observations = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExtremaOrderEvidenceProducerError(
            "CANONICAL_OUTPUT_INVALID", role
        ) from exc
    if not isinstance(observations, list):
        raise ExtremaOrderEvidenceProducerError("CANONICAL_OUTPUT_INVALID", role)

    _validate_grid(
        observations,
        role=role,
        start_ms=start_ms,
        end_ms=end_ms,
        interval_ms=interval_ms,
    )
    semantic_observations = _semantic_observations(observations)
    expected_semantic_output = _sha256_hex(
        _canonical_line_bytes(semantic_observations)
    )
    if (
        semantic_receipt.get("output_sha256") != expected_semantic_output
        or receipt.get("semantic_output_sha256") != expected_semantic_output
    ):
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:semantic_output_sha256"
        )
    expected_semantic_receipt = _sha256_hex(
        _canonical_line_bytes(semantic_receipt)
    )
    if receipt.get("semantic_receipt_sha256") != expected_semantic_receipt:
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:semantic_receipt_sha256"
        )
    expected_transport = _sha256_hex(payload.encode("utf-8"))
    if receipt.get("transport_output_sha256") != expected_transport:
        raise ExtremaOrderEvidenceProducerError(
            "PROVENANCE_MISMATCH", f"{role}:transport_output_sha256"
        )
    return observations


def _series_semantics(series: dict[str, Any]) -> tuple[str, str]:
    value_semantics = series.get("value_semantics", VALUE_SEMANTICS)
    unit = series.get("unit", UNIT)
    if not isinstance(value_semantics, str) or not value_semantics:
        raise ExtremaOrderEvidenceProducerError(
            "VALUE_SEMANTICS_MISMATCH", "invalid value semantics"
        )
    if not isinstance(unit, str) or not unit:
        raise ExtremaOrderEvidenceProducerError("UNIT_MISMATCH", "invalid unit")
    return value_semantics, unit


def _base_carrier(
    *,
    provider_id: str,
    instrument_id: str,
    parent_series_id: str,
    parent_row: dict[str, Any],
    parent_interval_ms: int,
    value_semantics: str,
    unit: str,
    known_at_utc: str,
    parent_receipt: dict[str, Any],
    parent_plan: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    parent_fp = observation_fingerprint(parent_row)
    start_ms = _parse_utc_ms(
        parent_row["open_time"], field="parent.open_time"
    )
    end_utc = _format_utc_ms(start_ms + parent_interval_ms)
    carrier = {
        "contract_id": PARENT_CONTRACT_ID,
        "capability_id": CAPABILITY_ID,
        "provider_id": provider_id,
        "instrument_id": instrument_id,
        "parent_series_id": parent_series_id,
        "parent_observation_ref": _observation_ref(parent_series_id, parent_row),
        "parent_interval_start_utc": parent_row["open_time"],
        "parent_interval_end_utc": end_utc,
        "parent_high": parent_row["high"],
        "parent_low": parent_row["low"],
        "value_semantics": value_semantics,
        "unit": unit,
        "finality": "FINALIZED",
        "event_effective_at": end_utc,
        "evidence_available_at_utc": known_at_utc,
        "known_at_utc": known_at_utc,
        "provenance": {
            "parent_semantic_receipt_sha256": parent_receipt[
                "semantic_receipt_sha256"
            ],
            "parent_resolution_plan_sha256": parent_plan["plan_sha256"],
            "parent_semantic_output_sha256": parent_receipt[
                "semantic_output_sha256"
            ],
            "parent_observation_fingerprint": parent_fp,
        },
    }
    return carrier, parent_fp


def _lower_tf_carrier(
    *,
    base: dict[str, Any],
    parent_row: dict[str, Any],
    child_series_id: str,
    child_interval: str,
    child_rows: list[dict[str, Any]],
    child_receipt: dict[str, Any],
    child_plan: dict[str, Any],
) -> dict[str, Any]:
    window_fp = child_window_fingerprint(child_rows)
    child_refs = [_observation_ref(child_series_id, row) for row in child_rows]
    highs = [row for row in child_rows if row["high"] == parent_row["high"]]
    lows = [row for row in child_rows if row["low"] == parent_row["low"]]
    earliest_high = highs[0]["open_time"] if highs else UNRESOLVED_OCCURRENCE
    earliest_low = lows[0]["open_time"] if lows else UNRESOLVED_OCCURRENCE

    if not highs or not lows:
        result = "UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE"
    elif earliest_high == earliest_low:
        result = "UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE"
    elif _parse_utc_ms(earliest_high, field="earliest_parent_high_occurrence") < (
        _parse_utc_ms(earliest_low, field="earliest_parent_low_occurrence")
    ):
        result = "HIGH_BEFORE_LOW"
    else:
        result = "LOW_BEFORE_HIGH"

    carrier = dict(base)
    carrier["provenance"] = dict(base["provenance"])
    carrier.update(
        {
            "ordering_evidence_source": ORDERING_SOURCE,
            "proof_granularity": LOWER_TF_GRANULARITY,
            "derived_result": result,
            "child_series_id": child_series_id,
            "child_interval": child_interval,
            "supporting_child_observation_refs": child_refs,
            "child_window_fingerprint": window_fp,
            "earliest_parent_high_occurrence": earliest_high,
            "earliest_parent_low_occurrence": earliest_low,
        }
    )
    carrier["provenance"].update(
        {
            "child_semantic_receipt_sha256": child_receipt[
                "semantic_receipt_sha256"
            ],
            "child_resolution_plan_sha256": child_plan["plan_sha256"],
            "child_semantic_output_sha256": child_receipt[
                "semantic_output_sha256"
            ],
            "child_window_fingerprint": window_fp,
        }
    )
    return carrier


def _finalize_carrier(
    carrier: dict[str, Any], query_cutoff_utc: str | None
) -> dict[str, Any]:
    carrier["evidence_fingerprint"] = compute_evidence_fingerprint(carrier)
    carrier["carrier_fingerprint"] = compute_carrier_fingerprint(carrier)
    validation = validate_carrier_fingerprints(
        carrier, optional_query_cutoff=query_cutoff_utc
    )
    if validation.get("status") not in {"VALID", "PIT_INELIGIBLE"}:
        raise ExtremaOrderEvidenceProducerError(
            "REFERENCE_VALIDATION_FAILED",
            str(validation.get("reason_code") or "UNKNOWN"),
        )
    return carrier


def produce_extrema_order_evidence(
    parent_series_id: str,
    child_series_id: str,
    range_start: str,
    range_end: str,
    *,
    query_cutoff_utc: str | None = None,
) -> list[dict[str, Any]]:
    """Produce source-bound V1 extrema-order carriers via the canonical history route."""

    start_ms = _parse_utc_ms(range_start, field="range_start")
    end_ms = _parse_utc_ms(range_end, field="range_end")
    if start_ms >= end_ms:
        raise ExtremaOrderEvidenceProducerError("INVALID_TIME_RANGE")

    try:
        parent_plan, parent_payload, parent_diag, parent_receipt = (
            _canonical_read_history(
                parent_series_id,
                range_start,
                range_end,
                cutoff_utc=query_cutoff_utc,
                mode="strict",
                output_format="json",
            )
        )
        child_plan, child_payload, child_diag, child_receipt = (
            _canonical_read_history(
                child_series_id,
                range_start,
                range_end,
                cutoff_utc=query_cutoff_utc,
                mode="strict",
                output_format="json",
            )
        )
    except ExtremaOrderEvidenceProducerError:
        raise
    except Exception as exc:
        raise ExtremaOrderEvidenceProducerError(
            "CANONICAL_HISTORY_READ_FAILED", str(exc)
        ) from exc

    parent_series = parent_plan.get("series") if isinstance(parent_plan, dict) else None
    child_series = child_plan.get("series") if isinstance(child_plan, dict) else None
    if not isinstance(parent_series, dict) or not isinstance(child_series, dict):
        raise ExtremaOrderEvidenceProducerError("CANONICAL_ROUTE_INVALID", "series")
    parent_interval_ms = parent_series.get("interval_ms")
    child_interval_ms = child_series.get("interval_ms")
    if (
        not isinstance(parent_interval_ms, int)
        or parent_interval_ms <= 0
        or not isinstance(child_interval_ms, int)
        or child_interval_ms <= 0
    ):
        raise ExtremaOrderEvidenceProducerError("INVALID_RESOLUTION")
    if child_interval_ms >= parent_interval_ms:
        raise ExtremaOrderEvidenceProducerError(
            "CHILD_RESOLUTION_NOT_STRICTLY_FINER"
        )
    if parent_interval_ms % child_interval_ms:
        raise ExtremaOrderEvidenceProducerError(
            "CHILD_RESOLUTION_NOT_DIVISOR_OF_PARENT"
        )

    parent_rows = _validate_semantic_read(
        role="parent",
        series_id=parent_series_id,
        start_ms=start_ms,
        end_ms=end_ms,
        plan=parent_plan,
        payload=parent_payload,
        diagnostics=parent_diag,
        receipt=parent_receipt,
    )
    child_rows = _validate_semantic_read(
        role="child",
        series_id=child_series_id,
        start_ms=start_ms,
        end_ms=end_ms,
        plan=child_plan,
        payload=child_payload,
        diagnostics=child_diag,
        receipt=child_receipt,
    )

    if parent_series["provider_id"] != child_series["provider_id"]:
        raise ExtremaOrderEvidenceProducerError("PROVIDER_MISMATCH")
    if parent_series["instrument"] != child_series["instrument"]:
        raise ExtremaOrderEvidenceProducerError("INSTRUMENT_MISMATCH")
    parent_semantics, parent_unit = _series_semantics(parent_series)
    child_semantics, child_unit = _series_semantics(child_series)
    if parent_semantics != child_semantics:
        raise ExtremaOrderEvidenceProducerError("VALUE_SEMANTICS_MISMATCH")
    if parent_unit != child_unit:
        raise ExtremaOrderEvidenceProducerError("UNIT_MISMATCH")

    child_by_time = {
        _parse_utc_ms(row["open_time"], field="child.open_time"): row
        for row in child_rows
    }
    children_per_parent = parent_interval_ms // child_interval_ms
    known_at_utc = _utc_now()
    carriers = []

    for parent_row in parent_rows:
        parent_start_ms = _parse_utc_ms(
            parent_row["open_time"], field="parent.open_time"
        )
        base, _parent_fp = _base_carrier(
            provider_id=parent_series["provider_id"],
            instrument_id=parent_series["instrument"],
            parent_series_id=parent_series_id,
            parent_row=parent_row,
            parent_interval_ms=parent_interval_ms,
            value_semantics=parent_semantics,
            unit=parent_unit,
            known_at_utc=known_at_utc,
            parent_receipt=parent_receipt,
            parent_plan=parent_plan,
        )
        if parent_row["high"] == parent_row["low"]:
            carrier = dict(base)
            carrier.update(
                {
                    "ordering_evidence_source": FLAT_SOURCE,
                    "proof_granularity": FLAT_GRANULARITY,
                    "derived_result": "ORDER_NOT_MATERIALLY_DISTINCT",
                }
            )
        else:
            expected_times = [
                parent_start_ms + index * child_interval_ms
                for index in range(children_per_parent)
            ]
            try:
                window = [child_by_time[timestamp] for timestamp in expected_times]
            except KeyError as exc:
                raise ExtremaOrderEvidenceProducerError(
                    "INCOMPLETE_CHILD_WINDOW", parent_row["open_time"]
                ) from exc
            if (
                _parse_utc_ms(window[0]["open_time"], field="child_window_start")
                != parent_start_ms
                or _parse_utc_ms(
                    window[-1]["open_time"], field="child_window_end"
                )
                + child_interval_ms
                != parent_start_ms + parent_interval_ms
            ):
                raise ExtremaOrderEvidenceProducerError(
                    "INCOMPLETE_CHILD_WINDOW", parent_row["open_time"]
                )
            carrier = _lower_tf_carrier(
                base=base,
                parent_row=parent_row,
                child_series_id=child_series_id,
                child_interval=child_series["interval"],
                child_rows=window,
                child_receipt=child_receipt,
                child_plan=child_plan,
            )
        carriers.append(_finalize_carrier(carrier, query_cutoff_utc))

    return carriers
