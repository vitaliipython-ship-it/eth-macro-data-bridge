from __future__ import annotations

import os
from pathlib import Path

from tools.capability_index import resolve_capability
from tools.history_access import materialize_resolution_plan

SERIES_ID = "spot.binance-spot.ETHUSDT.ohlcv.5m"
START_UTC = "2022-06-18T00:00:00Z"
END_UTC = "2022-11-10T00:00:00Z"
INTERVAL_MS = 300000
EXPECTED_ROWS = 41760


def no_network(*_args, **_kwargs):
    raise RuntimeError("network access attempted after verified cache warm-up")


def main() -> None:
    cache = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / "d62-history-access-live-cache"
    plan = resolve_capability(SERIES_ID, START_UTC, END_UTC)

    assert plan["request"]["series_id"] == SERIES_ID
    assert plan["series"]["source_provider"] == "binance"
    assert plan["series"]["instrument"] == "ETHUSDT"
    assert plan["series"]["source_interval_or_metric"] == "5m"
    assert plan["segments"]
    assert all(item["storage"] == "GITHUB_RELEASE_ASSET" for item in plan["segments"])
    assert all(item["source_manifest_path"] == "history/release-manifest.json" for item in plan["segments"])
    assert all(item["release_tag"] == "history-binance-spot-v1" for item in plan["segments"])
    assert all(item["browser_download_url"].startswith("https://") for item in plan["segments"])
    assert all(len(item["sha256"]) == 64 for item in plan["segments"])

    rows, diagnostics = materialize_resolution_plan(plan, cache_dir=cache, mode="strict")
    assert diagnostics["status"] == "PASS"
    assert diagnostics["gap_count"] == 0
    assert diagnostics["duplicates"] == 0
    assert diagnostics["rows"] == EXPECTED_ROWS
    assert diagnostics["expected_rows"] == EXPECTED_ROWS
    assert len(rows) == EXPECTED_ROWS
    assert rows[0][0] == plan["request"]["start_ms"]
    assert rows[-1][0] + INTERVAL_MS == plan["request"]["end_ms"]

    # A second materialization must be physically identical and require no network:
    # the immutable COLD bytes are reused only after size/SHA verification.
    rows_cached, diagnostics_cached = materialize_resolution_plan(
        plan,
        cache_dir=cache,
        mode="strict",
        opener=no_network,
    )
    assert rows_cached == rows
    assert diagnostics_cached["status"] == "PASS"
    assert diagnostics_cached["rows"] == EXPECTED_ROWS

    sources = diagnostics["sources"]
    print("D62_LIVE_SERIES_ID=" + SERIES_ID)
    print("D62_LIVE_RANGE=" + START_UTC + ".." + END_UTC)
    print("D62_RESOLUTION_PLAN_SHA256=" + plan["plan_sha256"])
    print("D62_RESOLUTION_PLAN_AUTHORITY=PASS")
    print("D62_NO_GUESSED_RELEASE_ROUTE=PASS")
    print("D62_COLD_SEGMENT_COUNT=" + str(len(plan["segments"])))
    print("D62_SOURCE_ASSET=" + ",".join(item["locator"] for item in sources))
    print("D62_SOURCE_SHA256=" + ",".join(item["sha256"] for item in sources))
    print("D62_ROWS=" + str(len(rows)))
    print("D62_EXPECTED_ROWS=" + str(EXPECTED_ROWS))
    print("D62_GAP_COUNT=0")
    print("D62_DUPLICATES=0")
    print("D62_STRICT_INTEGRITY=PASS")
    print("D62_VERIFIED_CACHE_REPLAY=PASS")
    print("D62_REAL_2022_SLICE=PASS")


if __name__ == "__main__":
    main()
