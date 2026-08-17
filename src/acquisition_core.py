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
from intelligence import BINANCE_USDM_BASES, collect_binance, collect_deribit_perpetual, collect_kraken, collect_liquidity, collect_options, depth_metrics


@contextmanager
def _working_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    before = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


def _latest_eligible_closed(candles: list[list[Any]], expected_ms: int, interval_ms: int) -> list[Any]:
    eligible = [
        row
        for row in candles
        if bool(row[-1]) and int(row[0]) + interval_ms <= expected_ms
    ]
    if not eligible:
        raise ValueError("no eligible finalized observation for requested slot")
    return eligible[-1]


def _freshness(expected_ms: int, provider_ms: int | None, cadence: int = 300) -> dict[str, Any]:
    if provider_ms is None:
        return {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": cadence}
    age = max(0, (expected_ms - provider_ms) // 1000)
    return {"status": "LIVE_USABLE" if age <= cadence * 2 else ("RECENT_CONTEXT" if age <= cadence * 6 else "STALE_FOR_CURRENT"), "age_seconds": age, "target_cadence_seconds": cadence}


class CanonicalAcquisitionCore:
    """VPS facade over the current collector/intelligence provider family."""

    def collect(self, capability_id: str, *, expected_ms: int, cycle_id: str, staging_root: Path) -> dict[str, Any]:
        with _working_directory(staging_root / capability_id.replace("/", "_")):
            if capability_id == "binance-spot.m5":
                observations = []
                physical_now_ms = int(time.time() * 1000)
                for symbol in ("ETHUSDT", "BTCUSDT", "ETHBTC"):
                    route, candles, _native = binance(symbol, "5m", 3, physical_now_ms, anchor_ms=expected_ms)
                    try:
                        row = _latest_eligible_closed(candles, expected_ms, 5 * 60_000)
                    except ValueError as exc:
                        if "no eligible finalized observation" in str(exc):
                            return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": str(exc), "observations": []}
                        raise
                    observations.append(self._ohlcv("binance-spot", symbol, "5m", route, row, expected_ms))
                return {"status": "PASS", "observations": observations}
            if capability_id == "kraken-spot.m5":
                observations = []
                physical_now_ms = int(time.time() * 1000)
                for symbol in ("ETHUSD", "BTCUSD"):
                    route, candles, _native = kraken(symbol, "5m", 3, physical_now_ms, anchor_ms=expected_ms)
                    try:
                        row = _latest_eligible_closed(candles, expected_ms, 5 * 60_000)
                    except ValueError as exc:
                        if "no eligible finalized observation" in str(exc):
                            return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": str(exc), "observations": []}
                        raise
                    observations.append(self._ohlcv("kraken-spot", symbol, "5m", route, row, expected_ms))
                return {"status": "PASS", "observations": observations}
            if capability_id == "binance-usdm.m5-current":
                result = collect_binance(get, expected_ms)
                observations = self._binance_usdm(result, expected_ms)
                observations.extend(self._binance_usdm_supplemental(expected_ms))
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "kraken-futures.analytics":
                result = collect_kraken(get, expected_ms)
                observations = []
                for instrument, instrument_data in result.get("instruments", {}).items():
                    for metric, metric_data in instrument_data.get("metrics", {}).items():
                        latest = metric_data.get("latest")
                        if latest is None: continue
                        ts = int(latest[0]) if isinstance(latest, list) else metric_data.get("last_timestamp")
                        observations.append(self._sample("kraken-futures", f"derivatives.kraken-futures.{instrument}.{metric}", ts, metric_data, expected_ms, "https://futures.kraken.com/api/charts/v1/analytics"))
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "deribit-perpetual.current":
                result = collect_deribit_perpetual(get, expected_ms)
                observations = [self._sample("deribit-perpetual", f"derivatives.deribit-perpetual.{name}.current", int(value.get("timestamp_ms", expected_ms)), value, expected_ms, "https://www.deribit.com/api/v2/public") for name, value in result.get("instruments", {}).items()]
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "deribit-options.surface-dvol":
                result = collect_options(get, expected_ms)
                surface_path = result.get("latest_surface")
                dvol_path = result.get("dvol_latest_path")
                if not surface_path or not Path(surface_path).is_file():
                    return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "missing Deribit option surface", "observations": []}
                if not dvol_path or not Path(dvol_path).is_file():
                    return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "missing Deribit DVOL history", "observations": []}
                surface = json.loads(Path(surface_path).read_text())
                dvol_records = json.loads(Path(dvol_path).read_text()).get("records", [])
                if not dvol_records:
                    return {"status": "FAIL", "failure_class": "VALIDATION_FAILED", "error": "empty Deribit DVOL history", "observations": []}
                dvol = dvol_records[-1]
                observations = [
                    self._sample("deribit-options", "options.deribit-options.ETH.surface-snapshots", expected_ms, surface, expected_ms, "https://www.deribit.com/api/v2/public"),
                    self._sample("deribit-options", "options.deribit-options.ETH.dvol.1h", int(dvol[0]), dvol, expected_ms, "https://www.deribit.com/api/v2/public/get_volatility_index_data"),
                ]
                return {"status": result.get("status", "FAIL"), "observations": observations}
            if capability_id == "liquidity.current":
                result = collect_liquidity(get, expected_ms, [], "PASS")
                path = result.get("latest_path")
                value = json.loads(Path(path).read_text()) if path and Path(path).is_file() else result
                return {"status": result.get("status", "FAIL"), "observations": [self._sample("multi-provider", "liquidity.orderbook-snapshots", expected_ms, value, expected_ms, "repository-owned canonical liquidity collector")] if result.get("status") in {"PASS", "DEGRADED"} else []}
            raise ValueError(f"unsupported capability: {capability_id}")

    @staticmethod
    def _ohlcv(provider: str, symbol: str, interval: str, route: str, row: list[Any], expected_ms: int) -> dict[str, Any]:
        ts = int(row[0])
        return {"series_id": f"spot.{provider}.{symbol}.ohlcv.{interval}", "provider_timestamp_at": _iso(ts), "provider_route": route, "finality": "FINALIZED" if row[-1] else "PROVISIONAL", "freshness": _freshness(expected_ms, ts), "value": {"open_time_ms": ts, "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5], "closed": bool(row[-1])}, "d9_target": "FIXED_GRID"}

    def _binance_usdm(self, result: dict[str, Any], expected_ms: int) -> list[dict[str, Any]]:
        out = []
        for symbol, data in result.get("instruments", {}).items():
            latest = data.get("latest", {})
            ts = int(latest.get("timestamp_ms", expected_ms))
            out.append(self._sample("binance-usdm", f"derivatives.binance-usdm.{symbol}.current", ts, latest, expected_ms, result.get("route")))
            path = data.get("latest_kline_path")
            if path and Path(path).is_file():
                records = json.loads(Path(path).read_text()).get("records", [])
                if records:
                    row = records[-1]
                    out.append({"series_id": f"derivatives.binance-usdm.{symbol}.perp-ohlcv.5m", "provider_timestamp_at": _iso(int(row[0])), "provider_route": result.get("route"), "finality": "FINALIZED", "freshness": _freshness(expected_ms, int(row[0])), "value": row, "d9_target": "FIXED_GRID"})
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

    @staticmethod
    def _sample(provider: str, series: str, provider_ms: int, value: Any, expected_ms: int, route: str | None) -> dict[str, Any]:
        return {"series_id": series, "provider_timestamp_at": _iso(provider_ms), "provider_route": route, "finality": "OBSERVED_STATE", "freshness": _freshness(expected_ms, provider_ms), "value": value, "d9_target": "SAMPLED_SCHEDULE"}


def _iso(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
