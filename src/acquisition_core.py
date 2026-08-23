from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# D8 deliberately imports the repository's existing provider implementations.
# It does not define a second collector family.
from collector import binance, get, kraken
from deribit_history import FUNDING_COLUMNS, OHLCV_COLUMNS, collect_deribit_history
from intelligence import (
    BINANCE_USDM_BASES,
    collect_binance,
    collect_deribit_perpetual,
    collect_kraken,
    collect_liquidity,
    collect_options,
    depth_metrics,
)

SPOT_CAPABILITY_INTERVALS = {
    "m5": ("5m", 5 * 60_000),
    "15m": ("15m", 15 * 60_000),
    "1h": ("1h", 60 * 60_000),
    "4h": ("4h", 4 * 60 * 60_000),
    "1d": ("1d", 24 * 60 * 60_000),
    "1w": ("1w", 7 * 24 * 60 * 60_000),
}
KRAKEN_REVISABLE_METRICS = {"spreads", "liquidity", "slippage", "future-basis", "funding"}
BINANCE_OI_OVERLAP_MS = 6 * 60 * 60_000
BINANCE_FUNDING_OVERLAP_MS = 24 * 60 * 60_000


@contextmanager
def _working_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    before = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


def _latest_eligible_native(rows: list[list[Any]], expected_ms: int, interval_ms: int) -> list[Any]:
    eligible = [row for row in rows if isinstance(row, list) and row and int(row[0]) + interval_ms <= expected_ms]
    if not eligible:
        raise ValueError("no eligible finalized observation for requested slot")
    return max(eligible, key=lambda row: int(row[0]))


def _freshness(expected_ms: int, provider_ms: int | None, cadence: int = 300) -> dict[str, Any]:
    if provider_ms is None:
        return {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": cadence}
    age = max(0, (expected_ms - provider_ms) // 1000)
    return {"status": "LIVE_USABLE" if age <= cadence * 2 else ("RECENT_CONTEXT" if age <= cadence * 6 else "STALE_FOR_CURRENT"), "age_seconds": age, "target_cadence_seconds": cadence}


def _row_dict(columns: list[str], row: list[Any]) -> dict[str, Any]:
    if len(row) != len(columns):
        raise ValueError("history row width does not match canonical columns")
    return dict(zip(columns, row))


class CanonicalAcquisitionCore:
    """VPS facade over the current collector/intelligence provider family."""

    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict[str, Any]:
        with _working_directory(staging_root / capability_id.replace("/", "_")):
            if capability_id.startswith("binance-spot."):
                return self._spot("binance-spot", capability_id, expected_ms)
            if capability_id.startswith("kraken-spot."):
                return self._spot("kraken-spot", capability_id, expected_ms)
            if capability_id == "binance-usdm.m5-current":
                result = collect_binance(get, expected_ms)
                observations = self._binance_usdm(result, expected_ms)
                observations.extend(self._binance_usdm_supplemental(expected_ms))
                observations.sort(key=lambda row: (row["series_id"], row.get("provider_timestamp_at") or ""))
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "kraken-futures.analytics":
                result = collect_kraken(get, expected_ms)
                observations = []
                route = "https://futures.kraken.com/api/charts/v1/analytics"
                for instrument in sorted(result.get("instruments", {})):
                    instrument_data = result["instruments"][instrument]
                    for metric in sorted(instrument_data.get("metrics", {})):
                        metric_data = instrument_data["metrics"][metric]
                        for row in metric_data.get("eligible_rows", []):
                            if not isinstance(row, list) or len(row) < 2:
                                raise ValueError(f"malformed Kraken eligible row: {instrument}/{metric}")
                            ts = int(row[0])
                            item = self._sample(
                                "kraken-futures",
                                f"derivatives.kraken-futures.{instrument}.{metric}",
                                ts,
                                {"timestamp_ms": ts, "metric": metric, "value": row[1]},
                                expected_ms,
                                route,
                            )
                            if metric in KRAKEN_REVISABLE_METRICS:
                                item["revision_classification"] = "PROVIDER_REVISABLE_SNAPSHOT"
                                item["source_snapshot_ref"] = route
                                item["provenance"] = {
                                    "metric_policy_schema": "kraken-futures-provider-revision/1.0.0",
                                    "revision_evidence_schema": "market-data-provider-revision/1.0.0",
                                }
                            observations.append(item)
                observations.sort(key=lambda row: (row["series_id"], row["provider_timestamp_at"]))
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "deribit-perpetual.current":
                result = collect_deribit_perpetual(get, expected_ms)
                observations = [
                    self._sample(
                        "deribit-perpetual",
                        f"derivatives.deribit-perpetual.{name}.current",
                        int(value.get("timestamp_ms", expected_ms)),
                        value,
                        expected_ms,
                        "https://www.deribit.com/api/v2/public",
                    )
                    for name, value in sorted(result.get("instruments", {}).items())
                ]
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "deribit-perpetual.h1-history":
                result = collect_deribit_history(get, expected_ms)
                observations = []
                for resource in sorted(result.get("resources", []), key=lambda row: (row.get("instrument", ""), row.get("metric", ""))):
                    instrument = resource.get("instrument")
                    metric = resource.get("metric")
                    columns = resource.get("columns")
                    if not isinstance(instrument, str) or not isinstance(metric, str) or not isinstance(columns, list):
                        raise ValueError("malformed Deribit history resource descriptor")
                    for row in resource.get("projection_rows", []):
                        value = _row_dict(columns, row)
                        ts = int(value["timestamp_ms"])
                        suffix = "funding.1h" if metric == "funding" else "ohlcv.1h"
                        observations.append({
                            "series_id": f"derivatives.deribit-perpetual.{instrument}.{suffix}",
                            "provider_timestamp_at": _iso(ts),
                            "provider_route": "https://www.deribit.com/api/v2/public",
                            "finality": "FINALIZED",
                            "freshness": _freshness(expected_ms, ts, 3600),
                            "value": value,
                            "d9_target": "FIXED_GRID",
                            "provenance": {"shared_history_resource": resource.get("path"), "projection_overlap_ms": resource.get("projection_overlap_ms")},
                        })
                observations.sort(key=lambda row: (row["series_id"], row["provider_timestamp_at"]))
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "deribit-options.surface-dvol":
                return self._options_surface_dvol(expected_ms)
            if capability_id == "liquidity.current":
                result = collect_liquidity(get, expected_ms, [], "PASS")
                path = result.get("latest_path")
                value = json.loads(Path(path).read_text()) if path and Path(path).is_file() else result
                observations = [self._sample("multi-provider", "liquidity.orderbook-snapshots", expected_ms, value, expected_ms, "repository-owned canonical liquidity collector")] if result.get("status") in {"PASS", "DEGRADED"} else []
                return {"status": result.get("status", "FAIL"), "observations": observations}
            raise ValueError(f"unsupported capability: {capability_id}")

    def _spot(self, provider: str, capability_id: str, expected_ms: int) -> dict[str, Any]:
        suffix = capability_id.rsplit(".", 1)[-1]
        try:
            interval, interval_ms = SPOT_CAPABILITY_INTERVALS[suffix]
        except KeyError as exc:
            raise ValueError(f"unsupported native spot timeframe: {capability_id}") from exc
        physical_now_ms = int(time.time() * 1000)
        observations = []
        symbols = ("ETHUSDT", "BTCUSDT", "ETHBTC") if provider == "binance-spot" else ("ETHUSD", "BTCUSD")
        collector = binance if provider == "binance-spot" else kraken
        for symbol in symbols:
            route, _compact, native = collector(symbol, interval, 3, physical_now_ms, anchor_ms=expected_ms)
            try:
                row = _latest_eligible_native(native, expected_ms, interval_ms)
            except ValueError as exc:
                if "no eligible finalized observation" in str(exc):
                    return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": str(exc), "observations": []}
                raise
            observations.append(self._rich_spot(provider, symbol, interval, route, row, expected_ms, interval_ms))
        observations.sort(key=lambda row: row["series_id"])
        return {"status": "PASS", "observations": observations}

    @staticmethod
    def _rich_spot(provider: str, symbol: str, interval: str, route: str, row: list[Any], expected_ms: int, interval_ms: int) -> dict[str, Any]:
        ts = int(row[0])
        if provider == "binance-spot":
            if len(row) < 11:
                raise ValueError("malformed Binance native rich OHLCV row")
            value = {
                "open_time_ms": ts,
                "open": row[1], "high": row[2], "low": row[3], "close": row[4],
                "base_volume": row[5],
                "close_time_ms": int(row[6]), "close_time": int(row[6]),
                "quote_volume": row[7], "trade_count": int(row[8]),
                "taker_buy_base_volume": row[9], "taker_buy_quote_volume": row[10],
                "closed": True,
            }
        else:
            if len(row) < 9:
                raise ValueError("malformed Kraken native rich OHLCV row")
            value = {
                "open_time_ms": ts,
                "open": row[1], "high": row[2], "low": row[3], "close": row[4],
                "vwap": row[5], "volume": row[6], "trade_count": int(row[7]),
                "close_time_ms": int(row[8]), "close_time": int(row[8]),
                "closed": True,
            }
        return {
            "series_id": f"spot.{provider}.{symbol}.ohlcv.{interval}",
            "provider_timestamp_at": _iso(ts),
            "provider_route": route,
            "finality": "FINALIZED",
            "freshness": _freshness(expected_ms, ts, max(300, interval_ms // 1000)),
            "value": value,
            "d9_target": "FIXED_GRID",
            "provenance": {"provider_native_timeframe": interval, "provider_native_rich_row": True},
        }

    def _binance_usdm(self, result: dict[str, Any], expected_ms: int) -> list[dict[str, Any]]:
        out = []
        for symbol in sorted(result.get("instruments", {})):
            data = result["instruments"][symbol]
            latest = data.get("latest", {})
            ts = int(latest.get("timestamp_ms", expected_ms))
            out.append(self._sample("binance-usdm", f"derivatives.binance-usdm.{symbol}.current", ts, latest, expected_ms, result.get("route")))
            path = data.get("latest_kline_path")
            if path and Path(path).is_file():
                records = json.loads(Path(path).read_text()).get("records", [])
                eligible = [row for row in records if int(row[6]) < expected_ms]
                if eligible:
                    row = eligible[-1]
                    out.append({"series_id": f"derivatives.binance-usdm.{symbol}.perp-ohlcv.5m", "provider_timestamp_at": _iso(int(row[0])), "provider_route": result.get("route"), "finality": "FINALIZED", "freshness": _freshness(expected_ms, int(row[0])), "value": row, "d9_target": "FIXED_GRID"})
            for row in data.get("open_interest_history_rows", []):
                row_ts = int(row["timestamp"])
                if expected_ms - BINANCE_OI_OVERLAP_MS <= row_ts <= expected_ms:
                    out.append({
                        "series_id": f"derivatives.binance-usdm.{symbol}.open-interest-history.5m",
                        "provider_timestamp_at": _iso(row_ts), "provider_route": result.get("route"), "known_at": row.get("known_at"),
                        "finality": "FINALIZED", "freshness": _freshness(expected_ms, row_ts), "value": row,
                        "d9_target": "FIXED_GRID", "provenance": row.get("provenance", {}),
                    })
            for row in data.get("funding_history_rows", []):
                row_ts = int(row["fundingTime"])
                if expected_ms - BINANCE_FUNDING_OVERLAP_MS <= row_ts <= expected_ms:
                    out.append({
                        "series_id": f"derivatives.binance-usdm.{symbol}.funding-history",
                        "provider_timestamp_at": _iso(row_ts), "provider_route": result.get("route"), "known_at": row.get("known_at"),
                        "finality": "FINALIZED", "freshness": _freshness(expected_ms, row_ts, 8 * 3600), "value": row,
                        "d9_target": "SAMPLED_SCHEDULE", "provenance": row.get("provenance", {}),
                    })
        return out

    def _binance_usdm_supplemental(self, expected_ms: int) -> list[dict[str, Any]]:
        base = BINANCE_USDM_BASES[0]
        out = []
        for symbol in ("ETHUSDT", "BTCUSDT"):
            for interval in ("1h", "4h", "1d"):
                raw = get(f"{base}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=3")
                closed = [r for r in raw if expected_ms > int(r[6])]
                if not closed: raise ValueError(f"no closed {symbol} {interval}")
                row = closed[-1]
                out.append({"series_id": f"derivatives.binance-usdm.{symbol}.perp-ohlcv.{interval}", "provider_timestamp_at": _iso(int(row[0])), "provider_route": base, "finality": "FINALIZED", "freshness": _freshness(expected_ms, int(row[0]), 3600), "value": [int(row[0]), *[str(x) for x in row[1:6]], int(row[6])], "d9_target": "FIXED_GRID"})
            book = get(f"{base}/fapi/v1/depth?symbol={symbol}&limit=100")
            metric = depth_metrics(book, expected_ms, "binance-usdm", symbol)
            out.append(self._sample("binance-usdm", f"liquidity.binance-usdm.{symbol}.depth", expected_ms, metric, expected_ms, base))
        return out

    def _options_surface_dvol(self, expected_ms: int) -> dict[str, Any]:
        result = collect_options(get, expected_ms)
        surface_path = result.get("latest_surface")
        if not surface_path or not Path(surface_path).is_file():
            return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "missing Deribit option surface", "observations": []}
        selected_names = list(result.get("selected_option_names") or [])
        if not selected_names:
            return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "canonical Deribit option selection is empty", "observations": []}
        dvol_rows = result.get("dvol_rows")
        if not isinstance(dvol_rows, list) or not dvol_rows:
            return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "empty bounded Deribit DVOL history", "observations": []}
        surface = json.loads(Path(surface_path).read_text())
        surface_series = "options.deribit-options.ETH.surface-snapshots"
        observations = [self._sample("deribit-options", surface_series, expected_ms, surface, expected_ms, "https://www.deribit.com/api/v2/public")]
        for row in sorted(dvol_rows, key=lambda item: int(item[0])):
            if not isinstance(row, list) or len(row) < 5:
                raise ValueError("malformed Deribit DVOL row")
            ts = int(row[0])
            observations.append({
                "series_id": "options.deribit-options.ETH.dvol.1h",
                "provider_timestamp_at": _iso(ts), "provider_route": "https://www.deribit.com/api/v2/public/get_volatility_index_data",
                "finality": "FINALIZED", "freshness": _freshness(expected_ms, ts, 3600),
                "value": {"timestamp_ms": ts, "open": row[1], "high": row[2], "low": row[3], "close": row[4]},
                "d9_target": "FIXED_GRID", "provenance": {"bounded_overlap_ms": result.get("dvol_overlap_ms")},
            })
        liquidity = collect_liquidity(get, expected_ms, selected_names, "PASS")
        selected_set = set(selected_names[:8])
        for book in sorted(liquidity.get("snapshots", []), key=lambda item: str(item.get("instrument", ""))):
            name = book.get("instrument")
            if book.get("provider") != "deribit" or name not in selected_set:
                continue
            observations.append({
                "series_id": f"liquidity.deribit-options.{name}.selected-book",
                "provider_timestamp_at": _iso(int(book.get("timestamp_ms", expected_ms))),
                "provider_route": "https://www.deribit.com/api/v2/public",
                "source_identity": "deribit",
                "finality": "OBSERVED_STATE", "freshness": _freshness(expected_ms, int(book.get("timestamp_ms", expected_ms))),
                "value": book, "d9_target": "SAMPLED_SCHEDULE",
                "provenance": {
                    "selection_source": "collect_options.selected_option_names",
                    "selected_option": name,
                    "selection_surface_series_id": surface_series,
                    "selection_surface_timestamp_ms": expected_ms,
                },
            })
        observations.sort(key=lambda row: (row["series_id"], row.get("provider_timestamp_at") or ""))
        return {"status": result.get("status", "FAIL"), "observations": observations}

    @staticmethod
    def _sample(provider: str, series: str, provider_ms: int, value: Any, expected_ms: int, route: str | None) -> dict[str, Any]:
        return {"series_id": series, "provider_timestamp_at": _iso(provider_ms), "provider_route": route, "finality": "OBSERVED_STATE", "freshness": _freshness(expected_ms, provider_ms), "value": value, "d9_target": "SAMPLED_SCHEDULE"}


def _iso(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
