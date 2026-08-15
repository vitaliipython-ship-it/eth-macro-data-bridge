from __future__ import annotations

import json
import os
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ARCHIVE_VERSION = "3.1.0"
ARCHIVE_ROOT = Path("archive")
BINANCE_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms",
                   "quote_volume", "trade_count", "taker_buy_base_volume", "taker_buy_quote_volume"]
KRAKEN_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "vwap", "volume", "trade_count"]
LEGACY_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume"]
FIVE_MINUTES_MS = 300_000
DEFAULT_BACKFILL_DAYS = 7


def day_for(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def partition_path(provider: str, symbol: str, date_utc: str) -> Path:
    year, month, day = date_utc.split("-")
    return ARCHIVE_ROOT / year / month / day / provider / f"{symbol}-5m.json"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
    temporary = path.with_suffix(".json.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def load_partition(path: Path, provider: str, symbol: str, date_utc: str) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text())
    return {"schema_version": ARCHIVE_VERSION, "provider": provider, "symbol": symbol,
            "interval": "5m", "date_utc": date_utc,
            "columns": BINANCE_COLUMNS if provider == "binance" else KRAKEN_COLUMNS, "candles": []}


def append_closed(provider: str, symbol: str, rows: list[list[Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, list[list[Any]]] = defaultdict(list)
    for row in rows:
        if row[-1] is True:
            by_day[day_for(row[0])].append(row[:-1])
    conflicts: list[dict[str, Any]] = []
    for date_utc, incoming in by_day.items():
        path = partition_path(provider, symbol, date_utc)
        payload = load_partition(path, provider, symbol, date_utc)
        legacy = payload.get("schema_version") == "3.0.0"
        existing = {row[0]: row for row in payload["candles"]}
        changed = False
        for row in incoming:
            old = existing.get(row[0])
            if old is None:
                existing[row[0]] = row; changed = True
            elif len(old) == len(LEGACY_COLUMNS):
                core_new = row[:6] if provider == "binance" else row[:5] + [row[6]]
                if old == core_new:
                    existing[row[0]] = row; changed = True
                else:
                    conflicts.append({"provider": provider, "symbol": symbol, "interval": "5m",
                                      "open_time_ms": row[0], "archive_path": path.as_posix(), "old": old, "new": row,
                                      "reason": "MIGRATION_CORE_MISMATCH"})
            elif old != row:
                conflicts.append({"provider": provider, "symbol": symbol, "interval": "5m",
                                  "open_time_ms": row[0], "archive_path": path.as_posix(), "old": old, "new": row})
        if changed:
            payload["schema_version"] = ARCHIVE_VERSION
            payload["columns"] = BINANCE_COLUMNS if provider == "binance" else KRAKEN_COLUMNS
            payload["candles"] = [existing[key] for key in sorted(existing)]
            atomic_json(path, payload)
    return conflicts


def fetch_binance_backfill(symbol: str, now_ms: int, days: int, get_json, base_urls: tuple[str, ...], start_override: int | None = None) -> list[list[Any]]:
    start = min(now_ms - days * 86_400_000, start_override) if start_override is not None else now_ms - days * 86_400_000
    cursor = start - (start % FIVE_MINUTES_MS)
    output: dict[int, list[Any]] = {}
    while cursor < now_ms:
        query = urllib.parse.urlencode({"symbol": symbol, "interval": "5m", "limit": 1000, "startTime": cursor, "endTime": now_ms})
        error = None
        for base in base_urls:
            try:
                raw = get_json(f"{base}/api/v3/klines?{query}")
                if not isinstance(raw, list): raise ValueError("non-list Binance response")
                break
            except Exception as exc: error = exc; raw = None
        if raw is None: raise RuntimeError(f"Binance backfill failed: {error}")
        if not raw: break
        for row in raw:
            closed = now_ms > int(row[6])
            output[int(row[0])] = map_binance_kline(row, closed)
        next_cursor = int(raw[-1][0]) + FIVE_MINUTES_MS
        if next_cursor <= cursor: raise RuntimeError("Binance pagination did not advance")
        cursor = next_cursor
        if len(raw) < 1000: break
    return [output[key] for key in sorted(output)]


def map_binance_kline(row: list[Any], closed: bool) -> list[Any]:
    return [int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), int(row[6]),
            str(row[7]), int(row[8]), str(row[9]), str(row[10]), closed]


def map_kraken_ohlc(row: list[Any], closed: bool) -> list[Any]:
    return [int(row[0]) * 1000, str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]),
            str(row[6]), int(row[7]), closed]


def fetch_kraken_native(symbol: str, now_ms: int, get_json) -> list[list[Any]]:
    query = urllib.parse.urlencode({"pair": symbol, "interval": 5})
    raw = get_json(f"https://api.kraken.com/0/public/OHLC?{query}")
    if not isinstance(raw, dict) or raw.get("error"): raise ValueError(f"Kraken error: {raw.get('error')}")
    keys = [key for key in raw["result"] if key != "last"]
    if len(keys) != 1: raise ValueError("unexpected Kraken result")
    rows = raw["result"][keys[0]]
    return [map_kraken_ohlc(row, index < len(rows)-1 and now_ms > int(row[0])*1000 + FIVE_MINUTES_MS-1)
            for index, row in enumerate(rows)]


def build_manifest(generated_at: str, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for path in ARCHIVE_ROOT.glob("????/??/??/*/*-5m.json"):
        payload = json.loads(path.read_text())
        rows = payload["candles"]
        key = (payload["provider"], payload["symbol"])
        item = groups.setdefault(key, {"provider": key[0], "symbol": key[1], "total_closed_candles": 0,
                                       "first_candle_time_ms": None, "last_candle_time_ms": None, "date_partitions": []})
        item["total_closed_candles"] += len(rows)
        item["date_partitions"].append({"date_utc": payload["date_utc"], "path": path.as_posix(), "candle_count": len(rows)})
        if rows:
            item["first_candle_time_ms"] = rows[0][0] if item["first_candle_time_ms"] is None else min(item["first_candle_time_ms"], rows[0][0])
            item["last_candle_time_ms"] = rows[-1][0] if item["last_candle_time_ms"] is None else max(item["last_candle_time_ms"], rows[-1][0])
    instruments = sorted(groups.values(), key=lambda x: (x["provider"], x["symbol"]))
    for item in instruments:
        item["date_partitions"].sort(key=lambda x: x["date_utc"])
        item["latest_partition"] = item["date_partitions"][-1]["path"] if item["date_partitions"] else None
    coverage = {}
    for provider in ("binance", "kraken"):
        fields = BINANCE_COLUMNS if provider == "binance" else KRAKEN_COLUMNS
        provider_rows = [json.loads(p.read_text())["candles"] for p in ARCHIVE_ROOT.glob(f"????/??/??/{provider}/*-5m.json")]
        flat = [row for rows in provider_rows for row in rows]
        coverage[provider] = {field: (sum(row[i] is not None for row in flat) / len(flat) if flat else 0)
                              for i, field in enumerate(fields)}
    manifest = {"schema_version": ARCHIVE_VERSION, "generated_at_utc": generated_at,
        "archive_policy": {"canonical_interval": "5m", "closed_only": True, "append_only": True,
                           "backfill_days": int(os.getenv("ARCHIVE_BACKFILL_DAYS", DEFAULT_BACKFILL_DAYS))},
        "available_fields": {"binance": BINANCE_COLUMNS, "kraken": KRAKEN_COLUMNS}, "field_coverage": coverage,
        "migration_status": "CONFLICT" if conflicts else "COMPLETE", "integrity_status": "CONFLICT" if conflicts else "PASS", "archive_conflict": bool(conflicts),
        "conflicts": conflicts, "instruments": instruments,
        "total_closed_candles": sum(x["total_closed_candles"] for x in instruments)}
    atomic_json(ARCHIVE_ROOT / "manifest.json", manifest)
    if conflicts:
        atomic_json(Path("diagnostics/archive-conflicts.json"), {"schema_version": ARCHIVE_VERSION, "generated_at_utc": generated_at, "conflicts": conflicts})
    return manifest


def update_archive(rolling_manifest: dict[str, Any], get_json, base_urls: tuple[str, ...]) -> dict[str, Any]:
    generated = rolling_manifest["generated_at_utc"]; now_ms = rolling_manifest["generated_at_epoch_ms"]
    days = int(os.getenv("ARCHIVE_BACKFILL_DAYS", DEFAULT_BACKFILL_DAYS))
    if not 1 <= days <= 30: raise ValueError("ARCHIVE_BACKFILL_DAYS must be between 1 and 30")
    conflicts: list[dict[str, Any]] = []
    for provider, provider_data in rolling_manifest["providers"].items():
        for symbol, symbol_data in provider_data["symbols"].items():
            path = Path(symbol_data["intervals"]["5m"]["path"])
            hot = json.loads(path.read_text())["candles"]
            existing=load_series(provider,symbol)
            earliest=existing[0][0] if existing else None
            rows = fetch_binance_backfill(symbol, now_ms, days, get_json, base_urls, earliest) if provider == "binance" else fetch_kraken_native(symbol, now_ms, get_json)
            conflicts.extend(append_closed(provider, symbol, rows))
    return build_manifest(generated, conflicts)


def load_series(provider: str, symbol: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for path in ARCHIVE_ROOT.glob(f"????/??/??/{provider}/{symbol}-5m.json"):
        rows.extend(json.loads(path.read_text())["candles"])
    return sorted(rows, key=lambda row: row[0])


def aggregate(rows: list[list[Any]], minutes: int, provider: str = "binance") -> list[list[Any]]:
    width = minutes * 60_000; buckets: dict[int, list[list[Any]]] = defaultdict(list)
    for row in rows: buckets[row[0] - row[0] % width].append(row)
    result = []
    for opened in sorted(buckets):
        group = sorted(buckets[opened], key=lambda row: row[0])
        common=[opened,group[0][1],str(max(Decimal(r[2]) for r in group)),str(min(Decimal(r[3]) for r in group)),group[-1][4]]
        if provider == "binance":
            result.append(common+[str(sum(Decimal(r[5]) for r in group)),group[-1][6],str(sum(Decimal(r[7]) for r in group)),
                                  sum(r[8] for r in group),str(sum(Decimal(r[9]) for r in group)),str(sum(Decimal(r[10]) for r in group))])
        else:
            volume=sum(Decimal(r[6]) for r in group)
            vwap=str(sum(Decimal(r[5])*Decimal(r[6]) for r in group)/volume) if volume else None
            result.append(common+[vwap,str(volume),sum(r[7] for r in group)])
    return result


def binance_analytics(row: list[Any]) -> dict[str, Any]:
    base, quote, trades, buy_base, buy_quote = Decimal(row[5]), Decimal(row[7]), row[8], Decimal(row[9]), Decimal(row[10])
    ratio=lambda a,b: str(a/b) if b else None
    return {"taker_sell_base_volume":str(base-buy_base),"taker_sell_quote_volume":str(quote-buy_quote),
            "taker_buy_base_ratio":ratio(buy_base,base),"taker_buy_quote_ratio":ratio(buy_quote,quote),
            "average_base_per_trade":ratio(base,Decimal(trades)),"average_quote_per_trade":ratio(quote,Decimal(trades)),
            "derived":True,"formula_version":"1.0.0"}
