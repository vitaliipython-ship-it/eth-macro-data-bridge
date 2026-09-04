from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from canonical_json import canonical_json_bytes

OPTIONS_SNAPSHOT_SCHEMA_VERSION = "1.0.0"
OPTIONS_PROVIDER = "deribit"
OPTIONS_SCOPE = "FULL_ACTIVE_CHAIN_COMPACT"
OPTIONS_TARGET_DAYS = (7, 30, 90)
OPTIONS_DERIVATION_POLICY_ID = "deribit-options-surface-analytics"
OPTIONS_DERIVATION_POLICY_VERSION = "1.0.0"
OPTIONS_COLUMNS = (
    "expiration_timestamp",
    "strike",
    "option_type",
    "open_interest",
    "volume_24h",
    "best_bid",
    "best_ask",
    "mid",
    "mark",
    "mark_iv",
    "underlying_price",
    "underlying_index",
    "interest_rate",
    "volume_usd",
)


class OptionsDerivationError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise OptionsDerivationError(code)


def _decimal(value: Any, field: str, *, nonnegative: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise OptionsDerivationError(f"{field}_INVALID")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise OptionsDerivationError(f"{field}_INVALID") from exc
    if not result.is_finite():
        raise OptionsDerivationError(f"{field}_NON_FINITE")
    if nonnegative and result < 0:
        raise OptionsDerivationError(f"{field}_NEGATIVE")
    return result


def options_derivation_policy_descriptor() -> dict[str, Any]:
    return {
        "policy_id": OPTIONS_DERIVATION_POLICY_ID,
        "policy_version": OPTIONS_DERIVATION_POLICY_VERSION,
        "snapshot_schema_version": OPTIONS_SNAPSHOT_SCHEMA_VERSION,
        "provider": OPTIONS_PROVIDER,
        "scope": OPTIONS_SCOPE,
        "target_days": list(OPTIONS_TARGET_DAYS),
        "input_semantics": "PERSISTED_CANONICAL_DERIBIT_OPTION_SURFACE_SNAPSHOT",
        "historical_as_of": "SNAPSHOT_TIMESTAMP_MS",
        "expiry_selection": "PERSISTED_SELECTED_GREEKS_TARGET_DAYS",
        "current_chain_substitution_allowed": False,
        "interpolation_allowed": False,
        "put_call_open_interest": "total_put_oi/total_call_oi",
        "put_call_volume": "total_put_volume/total_call_volume",
        "risk_reversal": "call_iv-put_iv",
        "butterfly": "(call_iv+put_iv)/2-atm_iv",
        "atm_iv": "ARITHMETIC_MEAN_OF_PERSISTED_ATM_CALL_AND_PUT_MARK_IV_WHEN_PRESENT",
        "numeric_domain": "DECIMAL_FOR_FINANCIAL_FORMULAS",
        "canonical_json": "UTF8_SORTED_KEYS_COMPACT_NONFINITE_FORBIDDEN",
    }


def options_derivation_policy_identity() -> dict[str, str]:
    descriptor = options_derivation_policy_descriptor()
    return {
        "derivation_policy_id": OPTIONS_DERIVATION_POLICY_ID,
        "derivation_policy_version": OPTIONS_DERIVATION_POLICY_VERSION,
        "derivation_policy_sha256": hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest(),
    }


def validate_options_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(snapshot, Mapping), "OPTIONS_SNAPSHOT_REQUIRED")
    value = dict(snapshot)
    _require(value.get("schema_version") == OPTIONS_SNAPSHOT_SCHEMA_VERSION, "OPTIONS_SNAPSHOT_SCHEMA_INVALID")
    _require(value.get("provider") == OPTIONS_PROVIDER, "OPTIONS_SNAPSHOT_PROVIDER_INVALID")
    _require(value.get("scope") == OPTIONS_SCOPE, "OPTIONS_SNAPSHOT_SCOPE_INVALID")
    timestamp_ms = value.get("timestamp_ms")
    _require(isinstance(timestamp_ms, int) and not isinstance(timestamp_ms, bool) and timestamp_ms > 0, "OPTIONS_SNAPSHOT_TIMESTAMP_INVALID")
    columns = value.get("columns")
    _require(isinstance(columns, list) and tuple(columns) == OPTIONS_COLUMNS, "OPTIONS_SNAPSHOT_COLUMNS_INVALID")
    options = value.get("options")
    _require(isinstance(options, list), "OPTIONS_SNAPSHOT_OPTIONS_INVALID")
    for index, row in enumerate(options):
        _require(isinstance(row, list) and len(row) == len(OPTIONS_COLUMNS), f"OPTIONS_SNAPSHOT_ROW_INVALID:{index}")
        expiry = row[0]
        _require(isinstance(expiry, int) and not isinstance(expiry, bool) and expiry > 0, f"OPTIONS_SNAPSHOT_EXPIRY_INVALID:{index}")
        _decimal(row[1], f"OPTIONS_SNAPSHOT_STRIKE:{index}", nonnegative=True)
        _require(row[2] in {"call", "put"}, f"OPTIONS_SNAPSHOT_OPTION_TYPE_INVALID:{index}")
        _decimal(row[3], f"OPTIONS_SNAPSHOT_OPEN_INTEREST:{index}", nonnegative=True)
        _decimal(row[4], f"OPTIONS_SNAPSHOT_VOLUME:{index}", nonnegative=True)
    selected = value.get("selected_greeks")
    _require(isinstance(selected, list), "OPTIONS_SNAPSHOT_SELECTED_GREEKS_INVALID")
    for index, item in enumerate(selected):
        _require(isinstance(item, Mapping), f"OPTIONS_SELECTED_GREEK_INVALID:{index}")
        _require(item.get("selection") in {"atm", "25d"}, f"OPTIONS_SELECTED_SELECTION_INVALID:{index}")
        _require(item.get("target_days") in OPTIONS_TARGET_DAYS, f"OPTIONS_SELECTED_TARGET_DAYS_INVALID:{index}")
        _require(item.get("option_type") in {"call", "put"}, f"OPTIONS_SELECTED_OPTION_TYPE_INVALID:{index}")
        expiry = item.get("expiry")
        _require(isinstance(expiry, int) and not isinstance(expiry, bool) and expiry > 0, f"OPTIONS_SELECTED_EXPIRY_INVALID:{index}")
        mark_iv = item.get("mark_iv")
        if mark_iv is not None:
            _decimal(mark_iv, f"OPTIONS_SELECTED_MARK_IV:{index}", nonnegative=True)
        if item.get("selection") == "25d":
            greeks = item.get("greeks")
            _require(isinstance(greeks, Mapping), f"OPTIONS_SELECTED_GREEKS_REQUIRED:{index}")
            _decimal(greeks.get("delta"), f"OPTIONS_SELECTED_DELTA:{index}")
    return value


def derive_options_analytics(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_options_snapshot(snapshot)
    timestamp_ms = int(value["timestamp_ms"])
    surface = value["options"]
    selected = value["selected_greeks"]

    calls = [row for row in surface if row[2] == "call"]
    puts = [row for row in surface if row[2] == "put"]
    call_oi = sum((_decimal(row[3], "CALL_OI", nonnegative=True) for row in calls), Decimal(0))
    put_oi = sum((_decimal(row[3], "PUT_OI", nonnegative=True) for row in puts), Decimal(0))
    call_vol = sum((_decimal(row[4], "CALL_VOLUME", nonnegative=True) for row in calls), Decimal(0))
    put_vol = sum((_decimal(row[4], "PUT_VOLUME", nonnegative=True) for row in puts), Decimal(0))
    analytics: dict[str, Any] = {
        "total_call_oi": str(call_oi),
        "total_put_oi": str(put_oi),
        "put_call_oi_ratio": str(put_oi / call_oi) if call_oi else None,
        "total_call_volume": str(call_vol),
        "total_put_volume": str(put_vol),
        "put_call_volume_ratio": str(put_vol / call_vol) if call_vol else None,
    }

    for days in OPTIONS_TARGET_DAYS:
        chosen = [item for item in selected if item.get("target_days") == days]
        atm = [item for item in chosen if item.get("selection") == "atm" and item.get("mark_iv") is not None]
        analytics[f"atm_iv_{days}d"] = (
            str(sum((_decimal(item["mark_iv"], f"ATM_IV_{days}D") for item in atm), Decimal(0)) / len(atm))
            if atm
            else None
        )
        expiries = {int(item["expiry"]) for item in chosen}
        analytics[f"actual_dte_{days}d"] = ((min(expiries) - timestamp_ms) / 86400000 if expiries else None)
        call_25d = next((item for item in chosen if item.get("selection") == "25d" and item.get("option_type") == "call" and item.get("mark_iv") is not None), None)
        put_25d = next((item for item in chosen if item.get("selection") == "25d" and item.get("option_type") == "put" and item.get("mark_iv") is not None), None)
        if call_25d and put_25d and analytics[f"atm_iv_{days}d"] is not None:
            call_iv = _decimal(call_25d["mark_iv"], f"CALL_IV_{days}D")
            put_iv = _decimal(put_25d["mark_iv"], f"PUT_IV_{days}D")
            atm_iv = _decimal(analytics[f"atm_iv_{days}d"], f"ATM_IV_{days}D")
            call_delta = _decimal(call_25d["greeks"]["delta"], f"CALL_DELTA_{days}D")
            put_delta = _decimal(put_25d["greeks"]["delta"], f"PUT_DELTA_{days}D")
            analytics[f"25d_{days}d"] = {
                "call_iv": str(call_iv),
                "put_iv": str(put_iv),
                "call_actual_delta": str(call_delta),
                "put_actual_delta": str(put_delta),
                "call_delta_error": str(abs(call_delta - Decimal("0.25"))),
                "put_delta_error": str(abs(put_delta + Decimal("0.25"))),
                "risk_reversal": str(call_iv - put_iv),
                "butterfly": str((call_iv + put_iv) / 2 - atm_iv),
            }

    analytics["iv_term_structure"] = {str(days): analytics.get(f"atm_iv_{days}d") for days in OPTIONS_TARGET_DAYS}
    if analytics.get("25d_30d"):
        selected_25d = analytics["25d_30d"]
        analytics.update({
            "25d_call_iv": selected_25d["call_iv"],
            "25d_put_iv": selected_25d["put_iv"],
            "25d_call_actual_delta": selected_25d["call_actual_delta"],
            "25d_put_actual_delta": selected_25d["put_actual_delta"],
            "25d_risk_reversal": selected_25d["risk_reversal"],
            "25d_butterfly": selected_25d["butterfly"],
        })
    analytics.update(options_derivation_policy_identity())
    return analytics
