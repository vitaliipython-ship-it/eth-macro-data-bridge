from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.capability_index import resolve_capability
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
    args = parser.parse_args(argv)

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
