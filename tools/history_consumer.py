from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.capability_index import INTERVAL_MS, describe_capability, resolve_capability
from tools.history_access import (
    HistoryAccessError,
    materialize_resolution_plan,
    rows_to_csv,
    rows_to_json,
)
from tools.history_access_v2 import build_semantic_receipt

LEGACY_RECEIPT_SCHEMA = "history-consumer-receipt/1.0.0"
SEMANTIC_RECEIPT_SCHEMA = "history-access-receipt/2.0.0"
D6_CURRENT_POLICY = "FINALIZED_ONLY"
LATEST_BARS_SAFE_MAX = 4096


class HistoryConsumerError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _write_text(path: str | None, payload: str) -> None:
    if not path:
        return
    Path(path).write_text(payload, encoding="utf-8")


def _compact(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _d6_semantic_observations(rows: list[tuple[int, str, str, str, str, str]]) -> list[dict]:
    return [
        {
            "timestamp_ms": ts,
            "value": {"open": o, "high": h, "low": l, "close": c, "volume": v},
            "finality": "FINALIZED",
        }
        for ts, o, h, l, c, v in rows
    ]


def _parse_utc_ms(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise HistoryConsumerError("INVALID_CUTOFF", "cutoff must use UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise HistoryConsumerError("INVALID_CUTOFF", f"invalid cutoff: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise HistoryConsumerError("INVALID_CUTOFF", "cutoff must be UTC")
    return int(parsed.timestamp() * 1000)


def _format_utc_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _manifest_item_key(item: dict) -> tuple[object, object, object]:
    return (
        item.get("provider"),
        item.get("symbol") or item.get("instrument"),
        item.get("interval") or item.get("metric") or item.get("interval_or_metric"),
    )


def _actual_latest_finalized_timestamp(series_id: str) -> tuple[dict, int, int, str]:
    """Return the actual canonical finalized tail declared by the capability's WARM manifest.

    The manifest path and interval semantics come from the existing capability resolver family;
    this function does not infer storage paths or construct a local schedule.
    """
    try:
        description = describe_capability(series_id)
    except Exception as exc:
        raise HistoryConsumerError("RESOLUTION_FAILED", str(exc)) from exc
    row = description["series"]
    profile = description["profile"]
    manifest_path = profile.get("hot_manifest_path")
    if not manifest_path:
        raise HistoryConsumerError(
            "CURRENT_TAIL_UNAVAILABLE",
            f"series has no declared current WARM manifest: {series_id}",
        )
    interval = row.get("interval")
    step_ms = INTERVAL_MS.get(interval)
    if step_ms is None:
        raise HistoryConsumerError(
            "LATEST_UNSUPPORTED_SERIES",
            f"latest finalized bounded read requires a canonical regular interval: {series_id}",
        )
    path = ROOT / manifest_path
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoryConsumerError("CURRENT_TAIL_UNAVAILABLE", f"cannot read declared manifest: {manifest_path}") from exc

    source_provider = profile["source_provider"]
    instrument = row["instrument"]
    physical_series = row["source_interval_or_metric"]
    latest = None
    for item in manifest.get("series", []):
        if not isinstance(item, dict):
            continue
        if _manifest_item_key(item) == (source_provider, instrument, physical_series):
            candidate = item.get("last_timestamp")
            if isinstance(candidate, int):
                latest = candidate
                break
    if latest is None and source_provider == "deribit-options" and physical_series == "DVOL-1h":
        candidate = (manifest.get("deribit_dvol") or {}).get("last_timestamp")
        if isinstance(candidate, int):
            latest = candidate
    if latest is None:
        raise HistoryConsumerError(
            "CURRENT_TAIL_UNAVAILABLE",
            f"declared manifest does not expose an actual finalized tail for {series_id}",
        )
    return description, latest, step_ms, manifest_path


def read_history(
    series_id: str,
    start_utc: str,
    end_utc: str,
    *,
    cutoff_utc: str | None = None,
    mode: str = "strict",
    output_format: str = "csv",
    cache_dir: Path | None = None,
    current_policy: str = D6_CURRENT_POLICY,
) -> tuple[dict, str, dict, dict]:
    """Resolve one semantic request, then materialize only through the canonical ResolutionPlan reader."""
    if current_policy != D6_CURRENT_POLICY:
        raise HistoryConsumerError(
            "CURRENT_POLICY_UNSUPPORTED",
            "active D6 ResolutionPlan v1 route is FINALIZED_ONLY; provisional current data requires an explicit D9 v2 route",
        )
    try:
        plan = resolve_capability(series_id, start_utc, end_utc, cutoff_utc)
    except Exception as exc:
        raise HistoryConsumerError("RESOLUTION_FAILED", str(exc)) from exc

    rows, diagnostics = materialize_resolution_plan(
        plan,
        cache_dir=cache_dir,
        mode=mode,
    )
    if output_format == "csv":
        payload = rows_to_csv(rows)
    elif output_format == "json":
        payload = rows_to_json(rows)
    else:
        raise HistoryConsumerError("UNSUPPORTED_FORMAT", f"unsupported output format: {output_format}")

    request = plan["request"]
    semantic_observations = _d6_semantic_observations(rows)
    semantic_receipt = build_semantic_receipt(
        series_id=series_id,
        start_ms=request["start_ms"],
        end_ms=request["end_ms"],
        cutoff_ms=request.get("cutoff_ms"),
        mode=mode,
        current_policy=D6_CURRENT_POLICY,
        resolution_plan_sha256=plan["plan_sha256"],
        observations=semantic_observations,
        finality="FINALIZED",
        revision_context=None,
    )

    encoded = payload.encode("utf-8")
    transport_sha256 = hashlib.sha256(encoded).hexdigest()
    semantic_receipt_bytes = _compact(semantic_receipt).encode("utf-8")
    receipt = {
        "schema_version": LEGACY_RECEIPT_SCHEMA,
        "receipt_role": "LEGACY_TRANSPORT_WRAPPER",
        "route": {
            "route_authority": "bridge-contract.json",
            "discovery": "history/capability-index.json",
            "resolver": "tools/capability_index.py",
            "reader": "tools/history_access.py",
            "reader_input_authority": "ResolutionPlan",
            "execution_adapter": "tools/history_consumer.py",
        },
        "series_id": series_id,
        "requested_start": diagnostics["requested_start"],
        "requested_end": diagnostics["requested_end"],
        "cutoff_utc": cutoff_utc,
        "mode": mode,
        "current_policy": D6_CURRENT_POLICY,
        "plan_sha256": plan["plan_sha256"],
        "status": diagnostics["status"],
        "rows": diagnostics["rows"],
        "expected_rows": diagnostics["expected_rows"],
        "gap_count": diagnostics["gap_count"],
        "duplicates": diagnostics["duplicates"],
        "sources": diagnostics["sources"],
        "output_format": output_format,
        "output_bytes": len(encoded),
        "output_sha256": transport_sha256,
        "output_sha256_semantics": "LEGACY_ALIAS_RENDERED_CONSUMER_ARTIFACT_BYTES",
        "transport_output_sha256": transport_sha256,
        "semantic_output_sha256": semantic_receipt["output_sha256"],
        "semantic_receipt_sha256": hashlib.sha256(semantic_receipt_bytes).hexdigest(),
        "semantic_receipt": semantic_receipt,
    }
    return plan, payload, diagnostics, receipt


def latest_history(
    series_id: str,
    bars: int,
    *,
    cutoff_utc: str,
    mode: str = "strict",
    output_format: str = "json",
    cache_dir: Path | None = None,
    current_policy: str = D6_CURRENT_POLICY,
) -> tuple[dict, str, dict, dict]:
    """Materialize a bounded latest finalized window through the existing canonical read route."""
    if isinstance(bars, bool) or not isinstance(bars, int) or not 1 <= bars <= LATEST_BARS_SAFE_MAX:
        raise HistoryConsumerError(
            "LATEST_BARS_OUT_OF_RANGE",
            f"bars must be an integer in [1,{LATEST_BARS_SAFE_MAX}]",
        )
    if current_policy != D6_CURRENT_POLICY:
        raise HistoryConsumerError(
            "CURRENT_POLICY_UNSUPPORTED",
            "latest operation supports current_policy=FINALIZED_ONLY only",
        )
    _description, latest_open_ms, step_ms, manifest_path = _actual_latest_finalized_timestamp(series_id)
    latest_close_ms = latest_open_ms + step_ms
    cutoff_ms = _parse_utc_ms(cutoff_utc)
    if latest_close_ms > cutoff_ms:
        raise HistoryConsumerError(
            "LATEST_FINALIZED_AFTER_CUTOFF",
            "declared latest finalized observation closes after the requested cutoff",
        )
    start_ms = latest_close_ms - bars * step_ms
    start_utc = _format_utc_ms(start_ms)
    end_utc = _format_utc_ms(latest_close_ms)
    plan, payload, diagnostics, receipt = read_history(
        series_id,
        start_utc,
        end_utc,
        cutoff_utc=cutoff_utc,
        mode=mode,
        output_format=output_format,
        cache_dir=cache_dir,
        current_policy=current_policy,
    )
    if mode == "strict" and (
        diagnostics.get("status") != "PASS"
        or diagnostics.get("rows") != bars
        or diagnostics.get("expected_rows") != bars
        or diagnostics.get("gap_count") != 0
        or diagnostics.get("duplicates") != 0
    ):
        raise HistoryConsumerError(
            "LATEST_WINDOW_INCOMPLETE",
            f"latest strict window must contain exactly {bars} gap-free unique observations",
        )
    if output_format == "json":
        try:
            observations = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HistoryConsumerError("LATEST_OUTPUT_INVALID", "latest JSON output is invalid") from exc
        if not observations or observations[-1].get("timestamp_ms") != latest_open_ms:
            raise HistoryConsumerError(
                "LATEST_ANCHOR_MISMATCH",
                "materialized latest window does not terminate at the actual declared finalized observation",
            )
        if any(row.get("finality") != "FINALIZED" for row in observations):
            raise HistoryConsumerError("LATEST_OPEN_BAR_FORBIDDEN", "latest operation exposed non-finalized data")
    receipt["latest_selection"] = {
        "anchor_authority": "ACTUAL_DECLARED_CANONICAL_FINALIZED_OBSERVATION",
        "declared_manifest": manifest_path,
        "latest_open_timestamp_ms": latest_open_ms,
        "latest_close_timestamp_ms": latest_close_ms,
        "bars": bars,
        "local_guessed_schedule_is_authority": False,
    }
    return plan, payload, diagnostics, receipt


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="One-step read-only adapter over the canonical D6 resolver -> ResolutionPlan -> reader route"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("read")
    read.add_argument("--series-id", required=True)
    read.add_argument("--from", dest="start_utc", required=True)
    read.add_argument("--to", dest="end_utc", required=True)
    read.add_argument("--cutoff", dest="cutoff_utc")
    read.add_argument("--mode", choices=("strict", "permissive"), default="strict")
    read.add_argument("--current-policy", choices=("FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"), default=D6_CURRENT_POLICY)
    read.add_argument("--format", dest="output_format", choices=("csv", "json"), default="csv")
    read.add_argument("--output", default="-")
    read.add_argument("--cache-dir")
    read.add_argument("--plan-output")
    read.add_argument("--diagnostics-output")
    read.add_argument("--receipt-output")
    read.add_argument("--semantic-receipt-output")

    latest = sub.add_parser("latest")
    latest.add_argument("--series-id", required=True)
    latest.add_argument("--bars", type=int, required=True)
    latest.add_argument("--cutoff", dest="cutoff_utc", required=True)
    latest.add_argument("--mode", choices=("strict", "permissive"), default="strict")
    latest.add_argument("--current-policy", choices=("FINALIZED_ONLY",), default=D6_CURRENT_POLICY)
    latest.add_argument("--format", dest="output_format", choices=("csv", "json"), default="json")
    latest.add_argument("--output", default="-")
    latest.add_argument("--cache-dir")
    latest.add_argument("--plan-output")
    latest.add_argument("--diagnostics-output")
    latest.add_argument("--receipt-output")
    latest.add_argument("--semantic-receipt-output")

    args = parser.parse_args(argv)
    if args.command == "read":
        plan, payload, diagnostics, receipt = read_history(
            args.series_id,
            args.start_utc,
            args.end_utc,
            cutoff_utc=args.cutoff_utc,
            mode=args.mode,
            output_format=args.output_format,
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            current_policy=args.current_policy,
        )
    else:
        plan, payload, diagnostics, receipt = latest_history(
            args.series_id,
            args.bars,
            cutoff_utc=args.cutoff_utc,
            mode=args.mode,
            output_format=args.output_format,
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            current_policy=args.current_policy,
        )

    if args.output == "-":
        sys.stdout.write(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    _write_text(args.plan_output, _compact(plan))
    _write_text(args.diagnostics_output, _compact(diagnostics))
    _write_text(args.receipt_output, _compact(receipt))
    _write_text(args.semantic_receipt_output, _compact(receipt["semantic_receipt"]))
    if not args.receipt_output:
        sys.stderr.write(_compact(receipt))


if __name__ == "__main__":
    try:
        main()
    except HistoryAccessError as exc:
        status = "DATA_TRANSPORT_BLOCKED" if exc.code == "DOWNLOAD_FAILED" else "READER_FAILED"
        print(f"HISTORY_CONSUMER={status} reader_code={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
    except HistoryConsumerError as exc:
        print(f"HISTORY_CONSUMER={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
