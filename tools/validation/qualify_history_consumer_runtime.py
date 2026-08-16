from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools.history_consumer import read_history
from tools.validation.qualify_d63_history_access import (
    DERIBIT_PERP_H1,
    H1,
    KRAKEN_SPOT_H1,
    first_asset_range,
)

CACHE = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "history-consumer-runtime-cache"


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _qualify(name: str, series_id: str, start: str, end: str) -> dict:
    plan, payload, diagnostics, receipt = read_history(
        series_id,
        start,
        end,
        mode="strict",
        output_format="csv",
        cache_dir=CACHE,
    )
    assert diagnostics["status"] == "PASS"
    assert diagnostics["rows"] == diagnostics["expected_rows"]
    assert diagnostics["gap_count"] == 0
    assert diagnostics["duplicates"] == 0
    assert receipt["plan_sha256"] == plan["plan_sha256"]
    assert receipt["output_bytes"] == len(payload.encode("utf-8"))
    assert receipt["sources"]
    print(
        "HISTORY_CONSUMER_RUNTIME_CASE=PASS"
        f" name={name} series_id={series_id} rows={diagnostics['rows']}"
        f" expected={diagnostics['expected_rows']} plan_sha256={plan['plan_sha256']}"
        f" output_sha256={receipt['output_sha256']}"
    )
    for source in receipt["sources"]:
        print(
            "HISTORY_CONSUMER_RUNTIME_SOURCE=VERIFIED"
            f" name={name} storage={source['storage']} locator={source['locator']}"
            f" sha256={source['sha256']} rows={source['rows']}"
        )
    return receipt


def main() -> None:
    receipts = []
    receipts.append(
        _qualify(
            "wave-h4-leg",
            "spot.binance-spot.ETHUSDT.ohlcv.4h",
            "2023-10-13T00:00:00Z",
            "2024-03-13T00:00:00Z",
        )
    )
    receipts.append(
        _qualify(
            "wave-h1-leg",
            "spot.binance-spot.ETHUSDT.ohlcv.1h",
            "2023-10-13T00:00:00Z",
            "2024-03-13T00:00:00Z",
        )
    )
    receipts.append(
        _qualify(
            "pivot-m5",
            "spot.binance-spot.ETHUSDT.ohlcv.5m",
            "2024-03-11T00:00:00Z",
            "2024-03-13T00:00:00Z",
        )
    )
    cold = _qualify(
        "cold-2022-m5",
        "spot.binance-spot.ETHUSDT.ohlcv.5m",
        "2022-06-18T00:00:00Z",
        "2022-11-10T00:00:00Z",
    )
    assert cold["rows"] == 41760
    assert any(source["storage"] == "GITHUB_RELEASE_ASSET" for source in cold["sources"])
    receipts.append(cold)

    for name, series_id in (
        ("kraken-spot", KRAKEN_SPOT_H1),
        ("deribit-perpetual", DERIBIT_PERP_H1),
    ):
        start, end = first_asset_range(series_id, H1)
        receipts.append(_qualify(name, series_id, start, end))

    provider_sources = {
        source["locator"]
        for receipt in receipts
        for source in receipt["sources"]
    }
    assert provider_sources
    summary = {
        "schema_version": "history-consumer-runtime-qualification/1.0.0",
        "status": "PASS",
        "cases": len(receipts),
        "all_gap_free": all(receipt["gap_count"] == 0 for receipt in receipts),
        "all_duplicate_free": all(receipt["duplicates"] == 0 for receipt in receipts),
        "source_count": len(provider_sources),
    }
    print("HISTORY_CONSUMER_RUNTIME_QUALIFICATION=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    print("HISTORY_CONSUMER_ROUTE=PASS")
    print("COLD_BINARY_TRANSPORT=PASS")
    print("HISTORY_MATERIALIZER=PASS")


if __name__ == "__main__":
    main()
