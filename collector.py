from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
COLLECTOR_VERSION = "0.1.0"
OUTPUT_PATH = Path("data/market.json")

# Prefer Binance's market-data-only host; fall back to the primary public host.
BINANCE_BASE_URLS = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
)
BINANCE_SYMBOLS = ("ETHUSDT", "BTCUSDT", "ETHBTC")

KRAKEN_BASE_URL = "https://api.kraken.com"
KRAKEN_PAIRS = ("ETHUSD", "BTCUSD")

# Event-study windows. An hourly refresh can reconstruct intrahour events because
# the exchange endpoints return historical candles, not merely the latest quote.
INTERVAL_LIMITS = {
    "5m": 288,   # 24h
    "15m": 96,   # 24h
    "1h": 72,    # 3d
    "4h": 42,    # 7d
    "1d": 90,    # 90d
}
KRAKEN_INTERVAL_MINUTES = {
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

USER_AGENT = (
    "eth-macro-data-bridge/0.1 "
    "(+https://github.com/vitaliipython-ship-it/eth-macro-data-bridge)"
)


def utc_iso_from_ms(value_ms: int) -> str:
    return (
        datetime.fromtimestamp(value_ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def http_json(url: str, *, retries: int = 3, timeout: int = 20) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(attempt * 1.5)
    raise RuntimeError(f"HTTP JSON fetch failed for {url}: {last_error}")


def normalize_binance_row(row: list[Any], now_ms: int) -> dict[str, Any]:
    open_ms = int(row[0])
    close_ms = int(row[6])
    return {
        "open_time_ms": open_ms,
        "open_time_utc": utc_iso_from_ms(open_ms),
        "close_time_ms": close_ms,
        "close_time_utc": utc_iso_from_ms(close_ms),
        "open": str(row[1]),
        "high": str(row[2]),
        "low": str(row[3]),
        "close": str(row[4]),
        "volume": str(row[5]),
        "quote_volume": str(row[7]),
        "trade_count": int(row[8]),
        "closed": now_ms > close_ms,
    }


def fetch_binance_dataset(
    symbol: str, interval: str, limit: int, now_ms: int
) -> tuple[str, list[dict[str, Any]]]:
    params = urllib.parse.urlencode(
        {"symbol": symbol, "interval": interval, "limit": limit}
    )
    errors: list[str] = []
    for base_url in BINANCE_BASE_URLS:
        url = f"{base_url}/api/v3/klines?{params}"
        try:
            raw = http_json(url)
            if not isinstance(raw, list) or not raw:
                raise RuntimeError("unexpected empty/non-list Binance response")
            return base_url, [normalize_binance_row(row, now_ms) for row in raw]
        except Exception as exc:
            errors.append(f"{base_url}: {exc}")
    raise RuntimeError("; ".join(errors))


def normalize_kraken_rows(
    rows: list[Any], interval_minutes: int, now_ms: int
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        open_ms = int(row[0]) * 1000
        close_ms = open_ms + interval_minutes * 60_000 - 1

        # Kraken documents the final OHLC row as current/not-yet-committed.
        closed = index < len(rows) - 1 and now_ms > close_ms

        normalized.append(
            {
                "open_time_ms": open_ms,
                "open_time_utc": utc_iso_from_ms(open_ms),
                "close_time_ms": close_ms,
                "close_time_utc": utc_iso_from_ms(close_ms),
                "open": str(row[1]),
                "high": str(row[2]),
                "low": str(row[3]),
                "close": str(row[4]),
                "vwap": str(row[5]),
                "volume": str(row[6]),
                "trade_count": int(row[7]),
                "closed": closed,
            }
        )
    return normalized


def fetch_kraken_dataset(
    pair: str, interval_name: str, limit: int, now_ms: int
) -> tuple[str, list[dict[str, Any]]]:
    interval_minutes = KRAKEN_INTERVAL_MINUTES[interval_name]
    params = urllib.parse.urlencode(
        {"pair": pair, "interval": interval_minutes}
    )
    url = f"{KRAKEN_BASE_URL}/0/public/OHLC?{params}"
    raw = http_json(url)

    if not isinstance(raw, dict):
        raise RuntimeError("unexpected non-object Kraken response")
    if raw.get("error"):
        raise RuntimeError(f"Kraken API error: {raw['error']}")

    result = raw.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken response missing result object")

    pair_keys = [key for key in result if key != "last"]
    if len(pair_keys) != 1:
        raise RuntimeError(f"unexpected Kraken pair keys: {pair_keys}")

    response_pair = pair_keys[0]
    rows = result[response_pair]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("unexpected empty/non-list Kraken OHLC response")

    rows = rows[-limit:]
    return response_pair, normalize_kraken_rows(rows, interval_minutes, now_ms)


def dataset_record(
    interval: str, requested_limit: int, candles: list[dict[str, Any]]
) -> dict[str, Any]:
    closed = [candle for candle in candles if candle["closed"]]
    return {
        "interval": interval,
        "requested_limit": requested_limit,
        "count": len(candles),
        "closed_count": len(closed),
        "latest_open_time_utc": candles[-1]["open_time_utc"] if candles else None,
        "latest_closed_open_time_utc": (
            closed[-1]["open_time_utc"] if closed else None
        ),
        "candles": candles,
    }


def validate_ohlc(candle: dict[str, Any]) -> None:
    o = float(candle["open"])
    h = float(candle["high"])
    l = float(candle["low"])
    c = float(candle["close"])

    if h < max(o, c):
        raise ValueError(f"invalid OHLC high: {candle}")
    if l > min(o, c):
        raise ValueError(f"invalid OHLC low: {candle}")
    if int(candle["close_time_ms"]) <= int(candle["open_time_ms"]):
        raise ValueError(f"invalid candle timestamps: {candle}")


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected schema version")

    binance = payload["providers"]["binance"]
    for symbol in BINANCE_SYMBOLS:
        symbol_data = binance["symbols"].get(symbol)
        if not symbol_data:
            raise ValueError(f"missing Binance symbol {symbol}")

        for interval in INTERVAL_LIMITS:
            dataset = symbol_data["intervals"].get(interval)
            if not dataset or dataset["count"] < 2:
                raise ValueError(
                    f"missing/short Binance dataset {symbol} {interval}"
                )
            validate_ohlc(dataset["candles"][-1])
            validate_ohlc(dataset["candles"][-2])

    # Kraken is corroboration, not a hard availability dependency. If data is
    # present, it must still be structurally valid.
    kraken = payload["providers"]["kraken"]
    for pair_data in kraken["pairs"].values():
        for dataset in pair_data["intervals"].values():
            if dataset["count"] < 2:
                raise ValueError("short Kraken dataset")
            validate_ohlc(dataset["candles"][-1])
            validate_ohlc(dataset["candles"][-2])


def collect() -> dict[str, Any]:
    now_ms = int(time.time() * 1000)
    generated_at = utc_iso_from_ms(now_ms)

    binance_provider: dict[str, Any] = {
        "role": "PRIMARY_CRYPTO_OHLC",
        "status": "PASS",
        "base_urls": list(BINANCE_BASE_URLS),
        "symbols": {},
        "errors": [],
    }
    binance_failed = False

    for symbol in BINANCE_SYMBOLS:
        symbol_record: dict[str, Any] = {"intervals": {}}
        for interval, limit in INTERVAL_LIMITS.items():
            try:
                base_url, candles = fetch_binance_dataset(
                    symbol, interval, limit, now_ms
                )
                symbol_record["intervals"][interval] = {
                    **dataset_record(interval, limit, candles),
                    "source_base_url": base_url,
                }
            except Exception as exc:
                binance_failed = True
                binance_provider["errors"].append(
                    f"{symbol} {interval}: {exc}"
                )
        binance_provider["symbols"][symbol] = symbol_record

    if binance_failed:
        binance_provider["status"] = "FAIL"

    kraken_provider: dict[str, Any] = {
        "role": "CORROBORATION_SPOT_OHLC",
        "status": "PASS",
        "base_url": KRAKEN_BASE_URL,
        "pairs": {},
        "errors": [],
    }
    kraken_failed = False

    for pair in KRAKEN_PAIRS:
        pair_record: dict[str, Any] = {"intervals": {}}
        for interval, limit in INTERVAL_LIMITS.items():
            try:
                response_pair, candles = fetch_kraken_dataset(
                    pair, interval, limit, now_ms
                )
                pair_record["response_pair"] = response_pair
                pair_record["intervals"][interval] = dataset_record(
                    interval, limit, candles
                )
            except Exception as exc:
                kraken_failed = True
                kraken_provider["errors"].append(
                    f"{pair} {interval}: {exc}"
                )
        kraken_provider["pairs"][pair] = pair_record

    if kraken_failed:
        kraken_provider["status"] = "DEGRADED"

    if binance_failed:
        bridge_status = "FAIL"
    elif kraken_failed:
        bridge_status = "DEGRADED"
    else:
        bridge_status = "PASS"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "generated_at_utc": generated_at,
        "generated_at_epoch_ms": now_ms,
        "bridge_status": bridge_status,
        "policy": {
            "authentication": "NONE",
            "api_keys_required": False,
            "purpose": "ETH Macro Watch event-window reconstruction",
            "timezone": "UTC",
            "interval_windows": INTERVAL_LIMITS,
        },
        "providers": {
            "binance": binance_provider,
            "kraken": kraken_provider,
        },
    }

    if bridge_status == "FAIL":
        raise RuntimeError(
            "Primary Binance collection incomplete: "
            + " | ".join(binance_provider["errors"])
        )

    validate_payload(payload)
    return payload


def main() -> None:
    payload = collect()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(OUTPUT_PATH)

    print(f"BRIDGE_STATUS={payload['bridge_status']}")
    print(f"GENERATED_AT_UTC={payload['generated_at_utc']}")
    print(f"BINANCE_STATUS={payload['providers']['binance']['status']}")
    print(f"KRAKEN_STATUS={payload['providers']['kraken']['status']}")
    print(f"OUTPUT={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
