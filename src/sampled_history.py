from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from history_store import append_partition, atomic_json

LEDGER_SCHEMA = "market-data-collection-run-ledger/1.0.0"
SAMPLED_SCHEMA = "market-data-sampled-observation/1.0.0"


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y/%m/%d")


def date_text(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def freshness(provider_timestamp_ms: int | None, completed_ms: int, target_cadence_seconds: int) -> dict[str, Any]:
    if provider_timestamp_ms is None:
        return {"status": "UNKNOWN", "age_seconds": None, "target_cadence_seconds": target_cadence_seconds}
    age = max(0, (completed_ms - provider_timestamp_ms) // 1000)
    if age <= target_cadence_seconds * 2:
        status = "LIVE_USABLE"
    elif age <= target_cadence_seconds * 6:
        status = "RECENT_CONTEXT"
    else:
        status = "STALE_FOR_CURRENT"
    return {"status": status, "age_seconds": age, "target_cadence_seconds": target_cadence_seconds}


def run_row(
    *,
    run_id: str,
    expected_ms: int,
    started_ms: int,
    completed_ms: int,
    provider: str,
    series_or_capability: str,
    status: str,
    snapshot_ref: str | None,
    error_class: str | None,
    provider_timestamp_ms: int | None,
    target_cadence_seconds: int,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "expected_schedule_at": iso(expected_ms),
        "collection_started_at": iso(started_ms),
        "collection_completed_at": iso(completed_ms),
        "provider": provider,
        "series_or_capability": series_or_capability,
        "status": status,
        "snapshot_ref": snapshot_ref,
        "error_class": error_class,
        "provider_timestamp_at": iso(provider_timestamp_ms) if provider_timestamp_ms is not None else None,
        "known_at": iso(completed_ms),
        "retrieved_at": iso(completed_ms),
        "freshness": freshness(provider_timestamp_ms, completed_ms, target_cadence_seconds)
        if status == "OBSERVED_STATE"
        else {"status": "COLLECTION_GAP" if status == "COLLECTION_GAP" else "UNKNOWN", "age_seconds": None, "target_cadence_seconds": target_cadence_seconds},
    }


def persist_sampled_intelligence(
    intelligence: dict[str, Any],
    *,
    expected_ms: int,
    started_ms: int,
    completed_ms: int,
    target_cadence_seconds: int = 3600,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []

    derivatives = intelligence.get("derivatives", {})
    deribit = derivatives.get("providers", {}).get("deribit-perpetual", {})
    instruments = deribit.get("instruments") if isinstance(deribit, dict) else None
    if deribit.get("status") == "PASS" and isinstance(instruments, dict) and instruments:
        snapshot_path = Path("derivatives/snapshots") / day(expected_ms) / f"{expected_ms}.json"
        provider_timestamps = [int(row["timestamp_ms"]) for row in instruments.values() if row.get("timestamp_ms") is not None]
        provider_timestamp = max(provider_timestamps) if provider_timestamps else None
        atomic_json(
            snapshot_path,
            {
                "schema_version": SAMPLED_SCHEMA,
                "provider": "deribit-perpetual",
                "timestamp_ms": expected_ms,
                "collection_started_at": iso(started_ms),
                "collection_completed_at": iso(completed_ms),
                "instruments": instruments,
            },
        )
        runs.append(
            run_row(
                run_id=f"deribit-perpetual-current:{expected_ms}",
                expected_ms=expected_ms,
                started_ms=started_ms,
                completed_ms=completed_ms,
                provider="deribit-perpetual",
                series_or_capability="derivatives.deribit-perpetual.current-snapshot",
                status="OBSERVED_STATE",
                snapshot_ref=snapshot_path.as_posix(),
                error_class=None,
                provider_timestamp_ms=provider_timestamp,
                target_cadence_seconds=target_cadence_seconds,
            )
        )
    else:
        runs.append(
            run_row(
                run_id=f"deribit-perpetual-current:{expected_ms}",
                expected_ms=expected_ms,
                started_ms=started_ms,
                completed_ms=completed_ms,
                provider="deribit-perpetual",
                series_or_capability="derivatives.deribit-perpetual.current-snapshot",
                status="PROVIDER_FAILURE",
                snapshot_ref=None,
                error_class="DERIBIT_PERPETUAL_COLLECTION_FAILED",
                provider_timestamp_ms=None,
                target_cadence_seconds=target_cadence_seconds,
            )
        )

    options = intelligence.get("options", {}).get("providers", {}).get("deribit", {})
    option_path = options.get("latest_surface") if isinstance(options, dict) else None
    option_ok = options.get("status") == "PASS" and isinstance(option_path, str) and Path(option_path).is_file()
    runs.append(
        run_row(
            run_id=f"deribit-options-surface:{expected_ms}",
            expected_ms=expected_ms,
            started_ms=started_ms,
            completed_ms=completed_ms,
            provider="deribit-options",
            series_or_capability="options.deribit-options.ETH.surface-snapshots",
            status="OBSERVED_STATE" if option_ok else "PROVIDER_FAILURE",
            snapshot_ref=option_path if option_ok else None,
            error_class=None if option_ok else "DERIBIT_OPTION_SURFACE_COLLECTION_FAILED",
            provider_timestamp_ms=expected_ms if option_ok else None,
            target_cadence_seconds=target_cadence_seconds,
        )
    )

    liquidity = intelligence.get("liquidity", {}).get("collection", {})
    liquidity_path = liquidity.get("latest_path") if isinstance(liquidity, dict) else None
    liquidity_ok = liquidity.get("status") in {"PASS", "DEGRADED"} and isinstance(liquidity_path, str) and Path(liquidity_path).is_file()
    runs.append(
        run_row(
            run_id=f"liquidity-orderbook:{expected_ms}",
            expected_ms=expected_ms,
            started_ms=started_ms,
            completed_ms=completed_ms,
            provider="multi-provider",
            series_or_capability="liquidity.orderbook-snapshots",
            status="OBSERVED_STATE" if liquidity_ok else "PROVIDER_FAILURE",
            snapshot_ref=liquidity_path if liquidity_ok else None,
            error_class=None if liquidity_ok else "LIQUIDITY_COLLECTION_FAILED",
            provider_timestamp_ms=expected_ms if liquidity_ok else None,
            target_cadence_seconds=target_cadence_seconds,
        )
    )

    ledger_path = Path("history/collection-runs") / day(expected_ms) / "runs.json"
    metadata = {"schema_version": LEDGER_SCHEMA, "date_utc": date_text(expected_ms)}
    append_partition(ledger_path, metadata, runs, records_field="runs", key=lambda row: row["run_id"])
    return {"ledger_path": ledger_path.as_posix(), "run_count": len(runs), "runs": runs}
