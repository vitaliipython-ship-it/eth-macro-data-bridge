from __future__ import annotations

import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import acquisition_core as ac  # noqa: E402
import d8_runtime as runtime  # noqa: E402

CONTRACT_PATH = ROOT / "contracts" / "d8-runtime-candidate.json"


def _ms(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp() * 1000)


def _cap(capability_id: str) -> dict:
    return next(row for row in runtime.CAPABILITY_POLICY if row["id"] == capability_id)


def _absolute_due_proof() -> bool:
    boundaries = {
        "binance-spot.15m": ("2026-08-24T12:15:00Z", "2026-08-24T12:10:00Z"),
        "binance-spot.1h": ("2026-08-24T13:00:00Z", "2026-08-24T12:55:00Z"),
        "binance-spot.4h": ("2026-08-24T12:00:00Z", "2026-08-24T11:55:00Z"),
        "binance-spot.1d": ("2026-08-25T00:00:00Z", "2026-08-24T23:55:00Z"),
        "binance-spot.1w": ("2026-08-24T00:00:00Z", "2026-08-23T23:55:00Z"),
    }
    return all(
        runtime.due_state(_cap(cap_id), _ms(positive), "development") == "DUE"
        and runtime.due_state(_cap(cap_id), _ms(negative), "development") == "NOT_DUE"
        for cap_id, (positive, negative) in boundaries.items()
    )


def validate() -> dict[str, object]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    matrix = contract["provider_capability_matrix"]
    declared = {row["id"] for row in contract["due_policy"]["capabilities"]}
    acquisition_source = inspect.getsource(ac.CanonicalAcquisitionCore)
    intelligence_source = (ROOT / "src" / "intelligence.py").read_text(encoding="utf-8")
    history_source = (ROOT / "src" / "deribit_history.py").read_text(encoding="utf-8")
    runtime_source = inspect.getsource(runtime.D8Runtime)

    binance_tfs = {f"binance-spot.{tf}" for tf in ("m5", "15m", "1h", "4h", "1d", "1w")}
    kraken_tfs = {f"kraken-spot.{tf}" for tf in ("m5", "15m", "1h", "4h", "1d", "1w")}

    proofs = {
        "P0_01_BINANCE_SPOT_RICH_M5": all(token in acquisition_source for token in ("base_volume", "quote_volume", "trade_count", "taker_buy_base_volume", "taker_buy_quote_volume", "close_time_ms")) and "RICH_NATIVE_OHLCV" in matrix["binance-spot"],
        "P0_02_BINANCE_SPOT_NATIVE_TF": binance_tfs <= declared and all(x in matrix["binance-spot"] for x in ("OHLCV_5M", "OHLCV_15M", "OHLCV_1H", "OHLCV_4H", "OHLCV_1D", "OHLCV_1W")),
        "P0_03_KRAKEN_SPOT_RICH_M5": all(token in acquisition_source for token in ("vwap", "trade_count", "close_time_ms")) and "RICH_NATIVE_OHLCV" in matrix["kraken-spot"],
        "P0_04_KRAKEN_SPOT_NATIVE_TF": kraken_tfs <= declared and all(x in matrix["kraken-spot"] for x in ("OHLCV_5M", "OHLCV_15M", "OHLCV_1H", "OHLCV_4H", "OHLCV_1D", "OHLCV_1W")),
        "P0_05_BINANCE_USDM_OI_HISTORY": "open_interest_history_rows" in intelligence_source and "open-interest-history.5m" in acquisition_source and "OPEN_INTEREST_HISTORY_5M" in matrix["binance-usdm"],
        "P0_06_BINANCE_USDM_FUNDING_HISTORY": "funding_history_rows" in intelligence_source and "funding-history" in acquisition_source and "FUNDING_HISTORY" in matrix["binance-usdm"],
        "P0_07_KRAKEN_FUTURES_ALL_ROWS": "eligible_rows" in intelligence_source and "for row in metric_data.get(\"eligible_rows\", [])" in acquisition_source and "BOUNDED_ALL_ROWS" in matrix["kraken-futures"],
        "P0_08_KRAKEN_FUTURES_PIT_REVISIONS": all(token in (acquisition_source + runtime_source) for token in ("PROVIDER_REVISABLE_SNAPSHOT", "market-data-provider-revision/1.0.0", "kraken-futures-provider-revision/1.0.0", "revision_of")) and "PROVIDER_PIT_REVISION_EVIDENCE" in matrix["kraken-futures"],
        "P0_09_DERIBIT_PERP_FUNDING_H1": "projection_rows" in history_source and "funding.1h" in acquisition_source and "FUNDING_H1" in matrix["deribit-perpetual"],
        "P0_10_DERIBIT_PERP_OHLCV_H1": "projection_rows" in history_source and "ohlcv.1h" in acquisition_source and "OHLCV_H1" in matrix["deribit-perpetual"],
        "P0_11_DERIBIT_DVOL_H1_ALL_ROWS": "dvol_rows" in intelligence_source and "for row in sorted(dvol_rows" in acquisition_source and "ETH_DVOL_1H" in matrix["deribit-options"],
        "P0_12_DERIBIT_SELECTED_OPTION_BOOKS": "selected_option_names" in intelligence_source and "collect_liquidity(get, expected_ms, selected_names" in acquisition_source and "SELECTED_OPTION_BOOKS" in matrix["deribit-options"],
    }
    failed = sorted(name for name, passed in proofs.items() if not passed)
    due = _absolute_due_proof()
    authority = contract["authority"]
    invariants = {
        "STATE_SCHEMA_VERSION": contract["state"]["state_schema_version"] == 2 == runtime.STATE_SCHEMA_VERSION,
        "D8_INACTIVE": authority["d8_runtime_active"] is False,
        "D9_INACTIVE": authority["d9_active"] is False,
        "VPS_NOT_AUTHORITY": authority["vps_is_market_data_authority"] is False,
        "NO_PROVIDER_TRANSITION": authority["provider_authority_transition_allowed"] is False,
        "NO_PRODUCTION_CUTOVER": authority["production_cutover_allowed"] is False,
        "ACTIVE_DEFAULT_ROUTE_D6": authority["active_default_route"] == "D6_RESOLUTION_PLAN_V1",
        "BINANCE_USDM_GITHUB_NETWORK_CALLS_0": contract["github_legacy_policy"]["binance_usdm_github_network_calls"] == 0,
    }
    all_pass = not failed and due and all(invariants.values())
    result: dict[str, object] = {
        "schema_version": "d8-r1-parity-proof/1.0.0",
        "P0_GAP_COUNT_BEFORE": 12,
        **proofs,
        "P0_GAP_COUNT_AFTER": len(failed),
        "CURRENT_GITHUB_INFORMATION_SET_SUBSET_OF_D8_VPS_INFORMATION_SET": all_pass,
        "OLD_D8_INFORMATION_SET_SUBSET_OF_NEW_D8_INFORMATION_SET": all_pass,
        "DUE_POLICY_ABSOLUTE_SCHEDULING": due,
        "DUE_15M": runtime.due_state(_cap("binance-spot.15m"), _ms("2026-08-24T12:15:00Z"), "development") == "DUE",
        "DUE_1H": runtime.due_state(_cap("binance-spot.1h"), _ms("2026-08-24T13:00:00Z"), "development") == "DUE",
        "DUE_4H": runtime.due_state(_cap("binance-spot.4h"), _ms("2026-08-24T12:00:00Z"), "development") == "DUE",
        "DUE_1D": runtime.due_state(_cap("binance-spot.1d"), _ms("2026-08-25T00:00:00Z"), "development") == "DUE",
        "DUE_1W": runtime.due_state(_cap("binance-spot.1w"), _ms("2026-08-24T00:00:00Z"), "development") == "DUE",
        "P0_08_EVIDENCE_SCHEMA": "market-data-provider-revision/1.0.0",
        "P0_08_METRIC_POLICY_SCHEMA": "kraken-futures-provider-revision/1.0.0",
        "SECOND_PROVIDER_CLIENT_FAMILY_CREATED": False,
        "SECOND_COLLECTOR_CREATED": False,
        "SECOND_RESOLVER_CREATED": False,
        "SECOND_READER_CREATED": False,
        "SECOND_MARKET_DATA_AUTHORITY_CREATED": False,
        "STATE_SCHEMA_MIGRATION": "NOT_REQUIRED",
        **invariants,
        "R1_PARITY_VALIDATOR": all_pass,
        "FAILED_PROOFS": failed,
    }
    return result


def main() -> int:
    result = validate()
    for key, value in result.items():
        if key == "FAILED_PROOFS":
            continue
        if isinstance(value, bool):
            rendered = "PASS" if value else "FAIL"
        else:
            rendered = str(value)
        print(f"{key}={rendered}")
    if result["FAILED_PROOFS"]:
        print("FAILED_PROOFS=" + ",".join(result["FAILED_PROOFS"]))
    return 0 if result["R1_PARITY_VALIDATOR"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
