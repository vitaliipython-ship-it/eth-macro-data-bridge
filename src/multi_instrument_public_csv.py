from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from multi_instrument_substrate import (
    AcquisitionWindow,
    InstrumentConfig,
    ProviderBatch,
    load_repository_config,
    run_acquisition,
    utc_iso,
)


class CsvHttpAdapter:
    adapter_id = "CSV_HTTP"

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        clock: Callable[[], datetime] | None = None,
    ):
        self._opener = opener
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def acquire(self, config: InstrumentConfig, window: AcquisitionWindow) -> ProviderBatch:
        config.validate()
        window.validate()
        if config.adapter != self.adapter_id:
            raise ValueError(f"adapter mismatch: {config.adapter}")
        if not config.endpoint:
            raise ValueError("CSV_HTTP endpoint missing")
        request = urllib.request.Request(
            self._bounded_url(config, window),
            headers={
                "Accept": "text/csv",
                "User-Agent": "eth-macro-data-bridge-internal-substrate/1.0",
            },
            method="GET",
        )
        with self._opener(request, timeout=20) as response:
            raw = response.read()
            content_type = str(response.headers.get("Content-Type", "text/csv"))
        if not raw:
            raise ValueError("provider returned empty bounded response")
        return ProviderBatch(
            raw_bytes=raw,
            retrieved_at_utc=utc_iso(self._clock()),
            retrieval_method=config.acquisition_method,
            source_provenance=config.source_provenance,
            content_type=content_type,
        )

    @staticmethod
    def _bounded_url(config: InstrumentConfig, window: AcquisitionWindow) -> str:
        start = datetime.fromisoformat(window.start_utc.replace("Z", "+00:00")).date().isoformat()
        end = (
            datetime.fromisoformat(window.end_utc.replace("Z", "+00:00"))
            - timedelta(microseconds=1)
        ).date().isoformat()
        if config.provider_id == "ecb":
            params = {"startPeriod": start, "endPeriod": end, "format": "csvdata"}
        elif config.provider_id == "fred":
            params = {"id": config.provider_instrument_id, "cosd": start, "coed": end}
        else:
            raise ValueError("CSV_HTTP live acquisition provider not explicitly admitted")
        separator = "&" if "?" in str(config.endpoint) else "?"
        return str(config.endpoint) + separator + urllib.parse.urlencode(params)

    def parse(self, config: InstrumentConfig, batch: ProviderBatch) -> list[dict[str, Any]]:
        if config.series_kind != "SCALAR_TIME_SERIES":
            raise ValueError("CSV_HTTP adapter currently supports scalar series only")
        reader = csv.DictReader(io.StringIO(batch.raw_bytes.decode("utf-8-sig")))
        if not reader.fieldnames:
            raise ValueError("CSV response has no header")
        date_candidates = [config.date_column, "TIME_PERIOD", "DATE", "observation_date"]
        value_candidates = [config.value_column, "OBS_VALUE", config.provider_instrument_id]
        date_column = next((name for name in date_candidates if name and name in reader.fieldnames), None)
        value_column = next((name for name in value_candidates if name and name in reader.fieldnames), None)
        if date_column is None or value_column is None:
            raise ValueError(f"CSV columns do not match configured semantics: {reader.fieldnames}")
        rows = []
        for row in reader:
            raw_date = str(row.get(date_column, "")).strip()
            raw_value = str(row.get(value_column, "")).strip()
            if not raw_date or raw_value in {"", ".", "NA", "N/A"}:
                continue
            rows.append({"source_time": raw_date, "value": raw_value})
        if not rows:
            raise ValueError("CSV response has no usable bounded observations")
        return rows


def live_probe(
    config_path: Path,
    staging_root: Path,
    window: AcquisitionWindow,
) -> dict[str, Any]:
    configs = load_repository_config(config_path)
    adapter = CsvHttpAdapter()
    samples = []
    failures = []
    for config in configs.values():
        if not config.enabled_for_live_probe:
            continue
        if config.adapter != adapter.adapter_id:
            failures.append(
                {
                    "provider_id": config.provider_id,
                    "series_id": config.series_id,
                    "status": "BLOCKED_ADAPTER_OR_CREDENTIAL_RUNTIME_REQUIRED",
                }
            )
            continue
        try:
            result = run_acquisition(config, window, adapter, staging_root=staging_root)
            receipt = result["receipt"]
            samples.append(
                {
                    "provider_id": config.provider_id,
                    "series_id": config.series_id,
                    "record_count": receipt["record_count"],
                    "raw_fingerprint": receipt["raw_fingerprint"],
                    "normalized_fingerprint": receipt["normalized_fingerprint"],
                    "quality": receipt["quality"],
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "provider_id": config.provider_id,
                    "series_id": config.series_id,
                    "status": "PHYSICAL_ACQUISITION_FAILED",
                    "error": str(exc),
                }
            )
    providers = sorted({sample["provider_id"] for sample in samples})
    return {
        "schema_version": "free-multi-instrument-live-probe/1.0.0",
        "sample_class": "NON_PRODUCTION_INTEGRATION_SAMPLE",
        "requested_window": {"start_utc": window.start_utc, "end_utc": window.end_utc},
        "successful_provider_count": len(providers),
        "successful_providers": providers,
        "samples": samples,
        "failures": failures,
        "multi_provider_physical_acquisition": (
            "PASS" if len(providers) >= 2 else ("PARTIAL" if providers else "FAIL")
        ),
        "vendor_raw_bytes_committed_to_git": False,
        "production_provider_activation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--staging-root", required=True)
    parser.add_argument("--start-utc", required=True)
    parser.add_argument("--end-utc", required=True)
    args = parser.parse_args()
    summary = live_probe(
        Path(args.config),
        Path(args.staging_root),
        AcquisitionWindow(args.start_utc, args.end_utc),
    )
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
