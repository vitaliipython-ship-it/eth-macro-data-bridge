from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from history_store import append_partition, atomic_json

ROOT = Path("history")
ARCHIVE_ROOT = Path("archive")
INTERVAL_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000}
BINANCE_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms",
                   "quote_volume", "trade_count", "taker_buy_base_volume", "taker_buy_quote_volume"]
KRAKEN_COMPAT_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume", "close_time_ms"]
KRAKEN_NATIVE_COLUMNS = ["open_time_ms", "open", "high", "low", "close", "vwap", "volume", "trade_count", "close_time_ms"]


class IncompleteAggregationBucket(ValueError):
    def __init__(self, interval: str, opened: int, missing: list[int]):
        self.interval = interval
        self.opened = opened
        self.missing = missing
        super().__init__(f"incomplete M5 bucket {interval} {opened}: missing={missing[:5]}")


def partition(interval: str, timestamp_ms: int) -> tuple[str, str]:
    dt = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
    if interval == "5m":
        return f"{dt:%Y/%m/%d}.json", "daily"
    if interval in ("15m", "1h", "4h"):
        return f"{dt:%Y/%m}.json", "monthly"
    return f"{dt:%Y}.json", "yearly"


def partition_path(provider: str, symbol: str, interval: str, timestamp_ms: int) -> Path:
    return ROOT / provider / symbol / interval / partition(interval, timestamp_ms)[0]


def _kraken_compat(row: list[Any]) -> list[Any]:
    if len(row) != len(KRAKEN_NATIVE_COLUMNS):
        raise ValueError(f"unexpected Kraken native history row length: {len(row)}")
    return [row[0], row[1], row[2], row[3], row[4], row[6], row[8]]


def append_native_history(
    provider: str,
    symbol: str,
    interval: str,
    native_rows: list[list[Any]],
    *,
    availability_status: str,
) -> dict[str, int]:
    if provider not in {"binance", "kraken"}:
        raise ValueError(f"unsupported Spot history provider: {provider}")
    if interval not in INTERVAL_MS:
        raise ValueError(f"unsupported Spot history interval: {interval}")
    grouped: dict[Path, list[list[Any]]] = defaultdict(list)
    for row in native_rows:
        grouped[partition_path(provider, symbol, interval, int(row[0]))].append(row)

    added = 0
    native_added = 0
    for path, rows in sorted(grouped.items(), key=lambda item: item[0].as_posix()):
        mode = partition(interval, int(rows[0][0]))[1]
        if provider == "binance":
            metadata = {
                "schema_version": "1.0.0",
                "provider": provider,
                "symbol": symbol,
                "interval": interval,
                "columns": BINANCE_COLUMNS,
                "closed_only": True,
                "partitioning": mode,
                "availability_status": availability_status,
                "d9_role": "CANONICAL_SPOT_WARM_PROVIDER_NATIVE",
            }
            result = append_partition(path, metadata, rows)
            added += sum(1 for row in rows if row in result.records) if result.changed else 0
        else:
            compatibility = [_kraken_compat(row) for row in rows]
            metadata = {
                "schema_version": "1.0.0",
                "provider": provider,
                "symbol": symbol,
                "interval": interval,
                "columns": KRAKEN_COMPAT_COLUMNS,
                "closed_only": True,
                "partitioning": mode,
                "availability_status": availability_status,
                "d9_role": "CANONICAL_SPOT_WARM_WITH_D6_COMPATIBILITY_PROJECTION",
                "provider_native_schema_version": "kraken-spot-history-native/1.0.0",
                "provider_native_columns": KRAKEN_NATIVE_COLUMNS,
            }
            compat_result = append_partition(path, metadata, compatibility)
            native_result = append_partition(path, metadata, rows, records_field="provider_native_records")
            if compat_result.changed:
                added += len(compatibility)
            if native_result.changed:
                native_added += len(rows)
    return {"compatibility_rows_observed": added, "provider_native_rows_observed": native_added}


def _archive_native(provider: str, row: list[Any]) -> list[Any]:
    if provider == "binance":
        if len(row) != len(BINANCE_COLUMNS):
            raise ValueError(f"unexpected Binance archive row length: {len(row)}")
        return row
    if provider == "kraken":
        if len(row) != 8:
            raise ValueError(f"unexpected Kraken archive row length: {len(row)}")
        return [row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], int(row[0]) + INTERVAL_MS["5m"] - 1]
    raise ValueError(f"unsupported archive provider: {provider}")


def migrate_archive_m5() -> dict[str, Any]:
    summary = {"partitions": 0, "rows": 0, "providers": {"binance": 0, "kraken": 0}}
    for path in sorted(ARCHIVE_ROOT.glob("????/??/??/*/*-5m.json")):
        payload = json.loads(path.read_text())
        provider = payload.get("provider")
        symbol = payload.get("symbol")
        if provider not in {"binance", "kraken"} or not symbol:
            continue
        native = [_archive_native(provider, row) for row in payload.get("candles", [])]
        if not native:
            continue
        append_native_history(
            provider,
            symbol,
            "5m",
            native,
            availability_status="PASS" if provider == "binance" else "PROVIDER_HISTORY_LIMIT",
        )
        summary["partitions"] += 1
        summary["rows"] += len(native)
        summary["providers"][provider] += len(native)
    summary["status"] = "PASS"
    return summary


def _spot_payloads(provider: str, symbol: str, interval: str):
    base = ROOT / provider / symbol / interval
    for path in sorted(base.rglob("*.json")) if base.exists() else []:
        payload = json.loads(path.read_text())
        if payload.get("provider") == provider and payload.get("symbol") == symbol and payload.get("interval") == interval:
            yield path, payload


def load_series(provider: str, symbol: str, interval: str, *, provider_native: bool = False) -> list[list[Any]]:
    field = "provider_native_records" if provider_native and provider == "kraken" else "records"
    rows: list[list[Any]] = []
    for _, payload in _spot_payloads(provider, symbol, interval):
        rows.extend(payload.get(field, []))
    rows.sort(key=lambda row: row[0])
    timestamps = [row[0] for row in rows]
    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError(f"duplicate Spot WARM timestamp {provider}/{symbol}/{interval}/{field}")
    return rows


def build_manifest(as_of_ms: int) -> dict[str, Any]:
    existing = json.loads((ROOT / "manifest.json").read_text()) if (ROOT / "manifest.json").exists() else {}
    old_series = {
        (row["provider"], row["symbol"], row["interval"]): row
        for row in existing.get("series", [])
        if isinstance(row, dict)
    }
    items = []
    for provider_dir in (ROOT / "binance", ROOT / "kraken"):
        if not provider_dir.exists():
            continue
        provider = provider_dir.name
        for symbol_dir in sorted(path for path in provider_dir.iterdir() if path.is_dir()):
            for interval_dir in sorted(path for path in symbol_dir.iterdir() if path.is_dir()):
                interval = interval_dir.name
                if interval not in INTERVAL_MS:
                    continue
                parts = []
                for path in sorted(interval_dir.rglob("*.json")):
                    payload = json.loads(path.read_text())
                    records = payload.get("records", [])
                    if records:
                        parts.append((path, payload, records))
                if not parts:
                    continue
                rows = [row for _, _, records in parts for row in records]
                rows.sort(key=lambda row: row[0])
                timestamps = [row[0] for row in rows]
                if len(timestamps) != len(set(timestamps)):
                    raise RuntimeError(f"duplicate history manifest timestamp {provider}/{symbol_dir.name}/{interval}")
                key = (provider, symbol_dir.name, interval)
                prior = old_series.get(key, {})
                native_count = sum(len(payload.get("provider_native_records", [])) for _, payload, _ in parts)
                items.append({
                    "provider": provider,
                    "symbol": symbol_dir.name,
                    "interval": interval,
                    "schema_version": "1.0.0",
                    "first_timestamp": timestamps[0],
                    "last_timestamp": timestamps[-1],
                    "closed_only": True,
                    "row_count": len(rows),
                    "partition_count": len(parts),
                    "partitioning": parts[0][1]["partitioning"],
                    "known_gaps": prior.get("known_gaps", []),
                    "provider_history_limit": provider == "kraken",
                    "integrity_status": "PASS",
                    "latest_partition_path": parts[-1][0].as_posix(),
                    "provider_native_enrichment_rows": native_count,
                })
    items.sort(key=lambda row: (row["provider"], row["symbol"], row["interval"]))
    manifest = dict(existing)
    manifest.update({
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.fromtimestamp(as_of_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
        "as_of_ms": as_of_ms,
        "series": items,
        "d9_warm_status": "DUAL_WRITE_CANDIDATE_NOT_ACTIVE",
        "canonical_spot_warm_root": "history",
    })
    atomic_json(ROOT / "manifest.json", manifest)
    return manifest


def _volume(row: list[Any], provider: str, native: bool) -> Decimal:
    if provider == "binance":
        return Decimal(str(row[5]))
    return Decimal(str(row[6] if native else row[5]))


def derive_m5_bucket(m5_rows: list[list[Any]], opened: int, interval: str, provider: str) -> list[Any]:
    width = INTERVAL_MS[interval]
    index = {int(row[0]): row for row in m5_rows}
    expected = list(range(opened, opened + width, INTERVAL_MS["5m"]))
    missing = [timestamp for timestamp in expected if timestamp not in index]
    if missing:
        raise IncompleteAggregationBucket(interval, opened, missing)
    group = [index[timestamp] for timestamp in expected]
    return [
        opened,
        group[0][1],
        str(max(Decimal(str(row[2])) for row in group)),
        str(min(Decimal(str(row[3])) for row in group)),
        group[-1][4],
        str(sum(_volume(row, provider, provider == "kraken" and len(row) == len(KRAKEN_NATIVE_COLUMNS)) for row in group)),
    ]


def native_core(row: list[Any], provider: str, *, native: bool) -> list[Any]:
    if provider == "binance":
        return [row[0], row[1], row[2], row[3], row[4], row[5]]
    return [row[0], row[1], row[2], row[3], row[4], row[6] if native else row[5]]


def _numeric_equal(left: Any, right: Any) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except Exception:
        return left == right


def compare_native_to_derived(native_row: list[Any], derived_row: list[Any], provider: str, *, native: bool) -> str:
    source = native_core(native_row, provider, native=native)
    return "EQUIVALENT" if all(_numeric_equal(left, right) for left, right in zip(source, derived_row)) else "CONFLICT"


def build_consistency_report(as_of_ms: int) -> dict[str, Any]:
    results = []
    for provider, symbols in (("binance", ("ETHUSDT", "BTCUSDT", "ETHBTC")), ("kraken", ("ETHUSD", "BTCUSD"))):
        for symbol in symbols:
            m5 = load_series(provider, symbol, "5m", provider_native=provider == "kraken")
            if not m5 and provider == "kraken":
                m5 = load_series(provider, symbol, "5m")
            for interval in ("15m", "1h", "4h", "1d", "1w"):
                native_rows = load_series(provider, symbol, interval, provider_native=provider == "kraken")
                using_native = bool(native_rows)
                if not native_rows:
                    native_rows = load_series(provider, symbol, interval)
                    using_native = False
                if not native_rows:
                    continue
                source = native_rows[-1]
                try:
                    derived = derive_m5_bucket(m5, int(source[0]), interval, provider)
                    status = compare_native_to_derived(source, derived, provider, native=using_native)
                    missing = 0
                except IncompleteAggregationBucket as exc:
                    derived = None
                    status = "KNOWN_PROVIDER_GAP"
                    missing = len(exc.missing)
                results.append({
                    "provider": provider,
                    "symbol": symbol,
                    "interval": interval,
                    "native_open_time_ms": int(source[0]),
                    "status": status,
                    "missing_m5_count": missing,
                    "derived": derived,
                })
    report = {
        "schema_version": "spot-history-consistency/1.0.0",
        "generated_at_utc": datetime.fromtimestamp(as_of_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
        "status_counts": {status: sum(row["status"] == status for row in results) for status in ("EQUIVALENT", "KNOWN_PROVIDER_GAP", "SEMANTIC_ALIGNMENT_DIFFERENCE", "CONFLICT")},
    }
    atomic_json(ROOT / "consistency-latest.json", report)
    return report
