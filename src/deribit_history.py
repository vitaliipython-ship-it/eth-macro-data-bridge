from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from history_store import append_partition, atomic_json

BASE = "https://www.deribit.com/api/v2/public/"
INSTRUMENTS = ("ETH-PERPETUAL", "BTC-PERPETUAL")
FUNDING_COLUMNS = ["timestamp_ms", "index_price", "interest_8h", "interest_1h", "prev_index_price"]
OHLCV_COLUMNS = ["timestamp_ms", "open", "high", "low", "close", "volume"]
HOUR_MS = 3_600_000


def _request(get: Callable[[str], Any], method: str, params: dict[str, Any]) -> Any:
    payload = get(BASE + method + "?" + urllib.parse.urlencode(params))
    if not isinstance(payload, dict) or payload.get("error"):
        raise RuntimeError(f"Deribit {method} error: {payload.get('error') if isinstance(payload, dict) else 'invalid response'}")
    return payload["result"]


def _path(instrument: str, metric: str) -> Path:
    suffix = "funding-1h" if metric == "funding" else "ohlcv-1h"
    return Path("derivatives/archive/deribit-perpetual") / f"{instrument}-{suffix}.json"


def _existing_tail(path: Path) -> int | None:
    if not path.exists():
        return None
    rows = json.loads(path.read_text()).get("records", [])
    return int(rows[-1][0]) if rows else None


def _canonicalize_metadata(path: Path, metadata: dict[str, Any]) -> None:
    payload = json.loads(path.read_text())
    for stale in ("interval", "interval_or_metric"):
        payload.pop(stale, None)
    payload.update(metadata)
    atomic_json(path, payload)


def _append_funding(get: Callable[[str], Any], instrument: str, now_ms: int) -> dict[str, Any]:
    path = _path(instrument, "funding")
    tail = _existing_tail(path)
    start = max(0, (tail + 1) if tail is not None else now_ms - 30 * 86_400_000)
    result = _request(
        get,
        "get_funding_rate_history",
        {"instrument_name": instrument, "start_timestamp": start, "end_timestamp": now_ms},
    )
    rows = [
        [int(item["timestamp"]), str(item["index_price"]), str(item["interest_8h"]), str(item["interest_1h"]), str(item["prev_index_price"])]
        for item in result
        if int(item["timestamp"]) <= now_ms
    ]
    metadata = {
        "schema_version": "1.0.0",
        "provider": "deribit-perpetual",
        "instrument": instrument,
        "metric": "funding",
        "resolution_seconds": 3600,
        "columns": FUNDING_COLUMNS,
        "closed_only": True,
        "partitioning": "bounded-30d-forward-continuation",
        "d9_role": "CANONICAL_DERIBIT_WARM",
    }
    merge = append_partition(path, metadata, rows)
    _canonicalize_metadata(path, metadata)
    return {"path": path.as_posix(), "incoming": len(rows), "changed": merge.changed}


def _append_ohlcv(get: Callable[[str], Any], instrument: str, now_ms: int) -> dict[str, Any]:
    path = _path(instrument, "OHLCV-1h")
    tail = _existing_tail(path)
    start = max(0, (tail + HOUR_MS) if tail is not None else now_ms - 14 * 86_400_000)
    result = _request(
        get,
        "get_tradingview_chart_data",
        {
            "instrument_name": instrument,
            "start_timestamp": start,
            "end_timestamp": now_ms,
            "resolution": "60",
        },
    )
    ticks = result.get("ticks", []) if isinstance(result, dict) else []
    rows = []
    for index, timestamp in enumerate(ticks):
        timestamp = int(timestamp)
        if timestamp + HOUR_MS > now_ms:
            continue
        rows.append(
            [
                timestamp,
                str(result["open"][index]),
                str(result["high"][index]),
                str(result["low"][index]),
                str(result["close"][index]),
                str(result["volume"][index]),
            ]
        )
    metadata = {
        "schema_version": "1.0.0",
        "provider": "deribit-perpetual",
        "instrument": instrument,
        "metric": "OHLCV-1h",
        "resolution_seconds": 3600,
        "columns": OHLCV_COLUMNS,
        "closed_only": True,
        "partitioning": "forward-continuation",
        "d9_role": "CANONICAL_DERIBIT_WARM_CANDIDATE_NOT_ACTIVE",
    }
    merge = append_partition(path, metadata, rows)
    _canonicalize_metadata(path, metadata)
    return {"path": path.as_posix(), "incoming": len(rows), "changed": merge.changed}


def _descriptor(instrument: str, metric: str) -> dict[str, Any] | None:
    path = _path(instrument, metric)
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    rows = payload.get("records", [])
    if not rows:
        return None
    timestamps = [int(row[0]) for row in rows]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise RuntimeError(f"Deribit history ordering/duplicate failure: {instrument}/{metric}")
    return {
        "provider": "deribit-perpetual",
        "instrument": instrument,
        "metric": metric,
        "first_timestamp": timestamps[0],
        "last_timestamp": timestamps[-1],
        "row_count": len(rows),
        "historical_backfill": "PASS" if metric == "funding" else "FORWARD_CONTINUATION",
        "warm_resource_path": path.as_posix(),
    }


def refresh_manifest(now_ms: int) -> dict[str, Any]:
    active_series = []
    candidate_series = []
    for instrument in INSTRUMENTS:
        funding = _descriptor(instrument, "funding")
        if funding:
            active_series.append(funding)
            candidate_series.append({**funding, "d9_warm_status": "EXISTING_ACTIVE_WARM_CONTINUED"})
        ohlcv = _descriptor(instrument, "OHLCV-1h")
        if ohlcv:
            candidate_series.append({**ohlcv, "d9_warm_status": "DUAL_WRITE_CANDIDATE_NOT_ACTIVE"})
    active_series.sort(key=lambda row: (row["instrument"], row["metric"]))
    candidate_series.sort(key=lambda row: (row["instrument"], row["metric"]))
    manifest = {
        "schema_version": "1.0.0",
        "as_of_ms": now_ms,
        "series": active_series,
        "d9_candidate_series": candidate_series,
        "d9_candidate_status": "DERIBIT_H1_WARM_NOT_ACTIVE",
    }
    atomic_json(Path("derivatives/deribit-history-manifest.json"), manifest)
    return manifest


def collect_deribit_history(get: Callable[[str], Any], now_ms: int) -> dict[str, Any]:
    results = []
    for instrument in INSTRUMENTS:
        results.append(_append_funding(get, instrument, now_ms))
        results.append(_append_ohlcv(get, instrument, now_ms))
    manifest = refresh_manifest(now_ms)
    candidate_count = len(manifest["d9_candidate_series"])
    return {
        "status": "PASS",
        "resources": results,
        "active_series": len(manifest["series"]),
        "candidate_series": candidate_count,
        "series": candidate_count,
    }
