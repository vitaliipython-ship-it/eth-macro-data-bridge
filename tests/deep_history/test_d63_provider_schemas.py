import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.history_access import compact, materialize_resolution_plan

START = 1700000000000
H1 = 3600000
SERIES_ID = "derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h"


class Response:
    def __init__(self, raw: bytes):
        self.stream = io.BytesIO(raw)

    def read(self, amount=-1):
        return self.stream.read(amount)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def payload_bytes() -> bytes:
    payload = {
        "schema_version": "1.0.0",
        "provider": "deribit-perpetual",
        "instrument": "ETH-PERPETUAL",
        "interval_or_metric": "OHLCV-1h",
        "columns": ["timestamp_ms", "open", "high", "low", "close", "volume"],
        "records": [[START, "2000", "2010", "1990", "2005", "123.45"]],
    }
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode()


def plan_for(raw: bytes) -> dict:
    plan = {
        "schema_version": "market-data-resolution-plan/1.0.0",
        "plan_kind": "MARKET_DATA_RESOLUTION_PLAN",
        "authority": {
            "route_policy": "bridge-contract.json",
            "capability_index": "history/capability-index.json",
            "cold_manifest": "history/release-manifest.json",
            "hot_manifest": None,
        },
        "request": {
            "series_id": SERIES_ID,
            "start_ms": START,
            "end_ms": START + H1,
            "cutoff_ms": None,
        },
        "series": {
            "series_id": SERIES_ID,
            "profile_id": "deribit-perpetual.ohlcv.max-available.cold-only",
            "instrument": "ETH-PERPETUAL",
            "series": "ohlcv",
            "interval": "1h",
            "source_interval_or_metric": "OHLCV-1h",
            "provider_id": "deribit-perpetual",
            "source_provider": "deribit-perpetual",
            "history_mode": "MAX_AVAILABLE",
            "availability_status": "PASS",
            "interval_ms": H1,
        },
        "segments": [{
            "segment_id": "cold:history-deribit-v1:1",
            "storage": "GITHUB_RELEASE_ASSET",
            "source_manifest_path": "history/release-manifest.json",
            "release_tag": "history-deribit-v1",
            "asset_id": 1,
            "asset_name": "deribit-perpetual--ETH-PERPETUAL--OHLCV-1h--2023.json",
            "browser_download_url": "https://example.invalid/deribit-ohlcv.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "immutable": True,
            "first_timestamp_ms": START,
            "last_timestamp_ms": START,
            "read_start_ms": START,
            "read_end_ms": START + H1,
            "source_provider": "deribit-perpetual",
            "instrument": "ETH-PERPETUAL",
            "source_interval_or_metric": "OHLCV-1h",
        }],
    }
    plan["plan_sha256"] = hashlib.sha256(compact(plan)).hexdigest()
    return plan


class DeribitProviderSchemaTests(unittest.TestCase):
    def test_timestamp_ms_ohlcv_is_normalized(self):
        raw = payload_bytes()
        plan = plan_for(raw)
        with tempfile.TemporaryDirectory() as temp:
            rows, diagnostics = materialize_resolution_plan(
                plan,
                cache_dir=Path(temp) / "cache",
                opener=lambda *_args, **_kwargs: Response(raw),
            )
        self.assertEqual(rows, [(START, "2000", "2010", "1990", "2005", "123.45")])
        self.assertEqual(diagnostics["status"], "PASS")
        self.assertEqual(diagnostics["gap_count"], 0)
        self.assertEqual(diagnostics["duplicates"], 0)


if __name__ == "__main__":
    unittest.main()
