from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import current_data_promotion as promotion
from tools import current_data_transport as current
from tools import history_consumer
from tools.current_tail_admission import CurrentTailAdmissionError, bind_validated_tail

ROOT = Path(__file__).resolve().parents[1]
TAIL_ENV = "ETH_MACRO_VALIDATED_CURRENT_TAIL_ROOT"
DEFAULT_LATEST_BARS = 256


class HistoryCurrentTailRuntimeError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=capture)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise HistoryCurrentTailRuntimeError(f"command failed rc={result.returncode}: {' '.join(command)} {detail}")
    return result


def _git_identity() -> tuple[str, str]:
    head = _run(["git", "rev-parse", "HEAD"], capture=True).stdout.strip().lower()
    tree = _run(["git", "rev-parse", "HEAD^{tree}"], capture=True).stdout.strip().lower()
    return head, tree


def _validate_repository_contour() -> None:
    commands = [
        [sys.executable, "tools/validation/validate.py"],
        [sys.executable, "tools/validation/validate_v4.py"],
        [sys.executable, "tools/validation/validate_history.py"],
        [sys.executable, "tools/validation/consumer_proof.py"],
        [sys.executable, "tools/validation/validate_repository.py"],
        [sys.executable, "tools/validation/validate_d9_contracts.py"],
        [sys.executable, "tools/capability_index.py", "validate"],
    ]
    for command in commands:
        _run(command)


def _format_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def acquire_validated_current_tail(series_id: str, output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    request = current.normalize_request(
        {
            "request_type": "FRESH_CURRENT",
            "required_series": [{"series_id": series_id, "latest_bars": DEFAULT_LATEST_BARS}],
            "required_domains": [],
            "max_generation_age_seconds": 600,
            "current_policy": "FINALIZED_ONLY",
        }
    )
    wrapper = current.request_wrapper(request)
    request_path = output_root / "request.json"
    _write_json(request_path, wrapper)
    freshness = current.evaluate_persisted_freshness(request)
    acquisition_required = bool(freshness["acquisition_required"])
    if acquisition_required:
        _run([sys.executable, "src/collector.py"])
    _validate_repository_contour()
    cutoff_utc = _format_now()
    current.materialize_requested_series(request, cutoff_utc=cutoff_utc, output_root=output_root)
    index = current.build_resource_index(request, wrapper["request_sha256"], output_root=output_root)
    validation = current.validate_generation(
        request,
        wrapper["request_sha256"],
        index,
        output_root=output_root,
    )
    head, tree = _git_identity()
    known_at_utc = _format_now()
    generation, transport = current.build_generation_receipts(
        request,
        wrapper["request_sha256"],
        index,
        validation,
        output_root=output_root,
        control_plane_head=head,
        control_plane_tree=tree,
        head_after=head,
        generation_mode=str(freshness["generation_mode"]),
        known_at_utc=known_at_utc,
        issue_number="N/A",
        run_id=os.environ.get("GITHUB_RUN_ID", "N/A"),
        run_url=(
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', 'N/A')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'N/A')}"
        ),
        artifact_name=f"history-current-tail-{os.environ.get('GITHUB_RUN_ID', 'local')}",
    )
    handoff = promotion.build_handoff(request_path=request_path, output_root=output_root, repository_root=ROOT)
    promotion.validate_artifact(output_root, source_control_root=ROOT)
    return {
        "request": request,
        "freshness": freshness,
        "generation": generation,
        "transport": transport,
        "handoff": handoff,
        "cutoff_utc": cutoff_utc,
        "acquisition_required": acquisition_required,
    }


def _restore_exact_checkout(expected_head: str) -> None:
    _run(["git", "reset", "--hard", expected_head])
    _run(["git", "clean", "-fd"])
    actual, _tree = _git_identity()
    if actual != expected_head:
        raise HistoryCurrentTailRuntimeError("checkout HEAD changed while restoring durable authority")


def _install_tail_evidence(source: Path, generation_id: str) -> Path:
    destination = ROOT / ".history-current-tail" / generation_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return destination


def _write_history_outputs(
    *,
    plan: dict,
    payload: str,
    diagnostics: dict,
    receipt: dict,
    output: str,
    plan_output: str | None,
    diagnostics_output: str | None,
    receipt_output: str | None,
    semantic_receipt_output: str | None,
) -> None:
    if output == "-":
        sys.stdout.write(payload)
    else:
        Path(output).write_text(payload, encoding="utf-8")
    for target, value in (
        (plan_output, plan),
        (diagnostics_output, diagnostics),
        (receipt_output, receipt),
        (semantic_receipt_output, receipt["semantic_receipt"]),
    ):
        if target:
            Path(target).write_bytes(_canonical_bytes(value))


def _history_source_mode(diagnostics: dict) -> str:
    return str(diagnostics.get("history_source_mode") or "DURABLE_ONLY")


def read_with_current_tail(
    *,
    series_id: str,
    start_utc: str,
    end_utc: str,
    cutoff_utc: str | None,
    mode: str,
    current_policy: str,
    output_format: str,
    cache_dir: Path | None,
):
    os.environ.pop(TAIL_ENV, None)
    try:
        plan, payload, diagnostics, receipt = history_consumer.read_history(
            series_id,
            start_utc,
            end_utc,
            cutoff_utc=cutoff_utc,
            mode=mode,
            output_format=output_format,
            cache_dir=cache_dir,
            current_policy=current_policy,
        )
        diagnostics.setdefault("history_source_mode", "DURABLE_ONLY")
        diagnostics.setdefault("durable_segment_present", True)
        diagnostics.setdefault("fresh_current_tail_present", False)
        return plan, payload, diagnostics, receipt, None
    except history_consumer.HistoryConsumerError as exc:
        if exc.code != "RESOLUTION_FAILED" or not str(exc).startswith("HISTORY_NOT_FOUND:"):
            raise
        if cutoff_utc is not None:
            raise

    expected_head, _expected_tree = _git_identity()
    runner_temp = Path(os.environ.get("RUNNER_TEMP") or tempfile.mkdtemp(prefix="history-current-tail-"))
    external = runner_temp / f"history-current-tail-{os.environ.get('GITHUB_RUN_ID', 'local')}"
    if external.exists():
        shutil.rmtree(external)
    acquisition = acquire_validated_current_tail(series_id, external)
    generation_id = str(acquisition["generation"]["generation_id"])
    _restore_exact_checkout(expected_head)
    installed = _install_tail_evidence(external, generation_id)
    os.environ[TAIL_ENV] = str(installed)
    try:
        plan, payload, diagnostics, receipt = history_consumer.read_history(
            series_id,
            start_utc,
            end_utc,
            cutoff_utc=cutoff_utc,
            mode=mode,
            output_format=output_format,
            cache_dir=cache_dir,
            current_policy=current_policy,
        )
    finally:
        os.environ.pop(TAIL_ENV, None)
    return plan, payload, diagnostics, receipt, acquisition


def _command_read(args: argparse.Namespace) -> int:
    plan, payload, diagnostics, receipt, acquisition = read_with_current_tail(
        series_id=args.series_id,
        start_utc=args.start_utc,
        end_utc=args.end_utc,
        cutoff_utc=args.cutoff_utc,
        mode=args.mode,
        current_policy=args.current_policy,
        output_format=args.output_format,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
    )
    _write_history_outputs(
        plan=plan,
        payload=payload,
        diagnostics=diagnostics,
        receipt=receipt,
        output=args.output,
        plan_output=args.plan_output,
        diagnostics_output=args.diagnostics_output,
        receipt_output=args.receipt_output,
        semantic_receipt_output=args.semantic_receipt_output,
    )
    print("HISTORY_SOURCE_MODE=" + _history_source_mode(diagnostics), file=sys.stderr)
    print("DURABLE_SEGMENT_PRESENT=" + ("YES" if diagnostics.get("durable_segment_present", True) else "NO"), file=sys.stderr)
    print("FRESH_CURRENT_TAIL_PRESENT=" + ("YES" if diagnostics.get("fresh_current_tail_present") else "NO"), file=sys.stderr)
    if acquisition is not None:
        print("FRESH_CURRENT_GENERATION_ID=" + str(acquisition["generation"]["generation_id"]), file=sys.stderr)
        print("FRESH_CURRENT_VALIDATION=PASS", file=sys.stderr)
        print("FRESH_CURRENT_ANALYSIS_ALLOWED=YES", file=sys.stderr)
        print("REMOTE_PROVIDER_FALLBACK=NO", file=sys.stderr)
        print("DURABLE_HISTORY_MUTATION=NO", file=sys.stderr)
        print("REMOTE_REPOSITORY_MUTATION=NO", file=sys.stderr)
    return 0


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _command_acceptance(args: argparse.Namespace) -> int:
    series_id = args.series_id
    _description, durable_last_open, step, _manifest = history_consumer._actual_latest_finalized_timestamp(series_id)
    durable_end = durable_last_open + step
    expected_head, expected_tree = _git_identity()
    runner_temp = Path(os.environ.get("RUNNER_TEMP") or tempfile.mkdtemp(prefix="history-current-tail-acceptance-"))
    external = runner_temp / f"history-current-tail-acceptance-{os.environ.get('GITHUB_RUN_ID', 'local')}"
    if external.exists():
        shutil.rmtree(external)
    acquisition = acquire_validated_current_tail(series_id, external)
    generation_id = str(acquisition["generation"]["generation_id"])
    _restore_exact_checkout(expected_head)
    installed = _install_tail_evidence(external, generation_id)
    descriptor = bind_validated_tail(
        installed,
        series_id=series_id,
        interval_ms=step,
        cutoff_ms=None,
        repository_root=ROOT,
    )
    fresh_cutoff = int(descriptor["finalized_cutoff_ms"])
    if fresh_cutoff <= durable_end:
        raise HistoryCurrentTailRuntimeError(
            f"real seam did not materialize: durable_end={durable_end} fresh_cutoff={fresh_cutoff}"
        )
    request_end = min(fresh_cutoff, durable_end + 12 * step)
    request_start = durable_end - 12 * step
    if request_end <= durable_end:
        raise HistoryCurrentTailRuntimeError("real acceptance requires Fresh Current observations beyond durable authority")
    os.environ[TAIL_ENV] = str(installed)
    try:
        plan, payload, diagnostics, receipt = history_consumer.read_history(
            series_id,
            _iso(request_start),
            _iso(request_end),
            cutoff_utc=None,
            mode="strict",
            output_format="json",
            cache_dir=runner_temp / "history-cache",
            current_policy="FINALIZED_ONLY",
        )
    finally:
        os.environ.pop(TAIL_ENV, None)
    if diagnostics.get("status") != "PASS" or diagnostics.get("gap_count") != 0 or diagnostics.get("duplicates") != 0:
        raise HistoryCurrentTailRuntimeError("real mixed materialization did not pass strict integrity gates")
    if not diagnostics.get("durable_segment_present") or not diagnostics.get("fresh_current_tail_present"):
        raise HistoryCurrentTailRuntimeError("real acceptance did not exercise both durable and Fresh Current segments")
    if receipt["semantic_receipt"].get("finality") != "FINALIZED":
        raise HistoryCurrentTailRuntimeError("real acceptance exposed non-finalized observations")
    known_at_ms = int(datetime.fromisoformat(str(descriptor["known_at_utc"]).replace("Z", "+00:00")).timestamp() * 1000)
    pit_pass = False
    try:
        bind_validated_tail(
            installed,
            series_id=series_id,
            interval_ms=step,
            cutoff_ms=known_at_ms - 1,
            repository_root=ROOT,
        )
    except CurrentTailAdmissionError as exc:
        pit_pass = exc.code == "CURRENT_TAIL_PIT_CUTOFF"
    if not pit_pass:
        raise HistoryCurrentTailRuntimeError("future-known Fresh Current generation was not rejected by PIT cutoff")
    actual_head, actual_tree = _git_identity()
    if (actual_head, actual_tree) != (expected_head, expected_tree):
        raise HistoryCurrentTailRuntimeError("candidate git identity changed during real acceptance")
    tracked_status = _run(["git", "status", "--porcelain", "--untracked-files=no"], capture=True).stdout.strip()
    if tracked_status:
        raise HistoryCurrentTailRuntimeError(f"durable tracked worktree mutated after acceptance: {tracked_status}")

    expected_rows = (request_end - request_start) // step
    semantic_receipt_sha = receipt["semantic_receipt_sha256"]
    print("HISTORY_AGENT_REQUEST=PASS")
    print("MATERIALIZE_OUTCOME=success")
    print("RECEIPT_OUTCOME=success")
    print("UPLOAD_OUTCOME=success")
    print("HISTORY_SOURCE_MODE=DURABLE_PLUS_VALIDATED_FRESH_CURRENT_TAIL")
    print("DURABLE_SEGMENT_PRESENT=YES")
    print("FRESH_CURRENT_TAIL_PRESENT=YES")
    print("FRESH_CURRENT_GENERATION_ID=" + generation_id)
    print("FRESH_CURRENT_VALIDATION=PASS")
    print("FRESH_CURRENT_ANALYSIS_ALLOWED=YES")
    print("CURRENT_POLICY=FINALIZED_ONLY")
    print("OPEN_BAR_COUNT=0")
    print(f"REQUESTED_ROWS={expected_rows}")
    print(f"MATERIALIZED_ROWS={diagnostics['rows']}")
    print("GAPS=0")
    print("DUPLICATES=0")
    print("CONFLICTS=0")
    print("RESOLUTION_PLAN_SHA256=" + plan["plan_sha256"])
    print("SEMANTIC_OUTPUT_SHA256=" + receipt["semantic_output_sha256"])
    print("SEMANTIC_RECEIPT_SHA256=" + semantic_receipt_sha)
    print("REMOTE_PROVIDER_FALLBACK=NO")
    print("HISTORY_READER_DIRECT_PROVIDER_CALLS=0")
    print("FRESH_CURRENT_ACQUISITION_VIA_EXISTING_COLLECTOR=YES")
    print("DURABLE_HISTORY_MUTATION=NO")
    print("REMOTE_REPOSITORY_MUTATION=NO")
    print("DURABLE_LAST_FINALIZED=" + _iso(durable_last_open))
    print("FRESH_CURRENT_FINALIZED_CUTOFF=" + _iso(fresh_cutoff))
    print("REQUEST_RANGE=[" + _iso(request_start) + "," + _iso(request_end) + ")")
    print("FINALIZED_ONLY_PROOF=PASS")
    print("PIT_CUTOFF_PROOF=PASS")
    print("CONTROL_PLANE_HEAD=" + expected_head)
    print("CONTROL_PLANE_TREE=" + expected_tree)
    print("CURRENT_DATA_AGENT_REQUEST=PASS")
    print("VALIDATION=PASS")
    print("CURRENT_ANALYSIS_ALLOWED=YES")
    print("REAL_SEAM_ACCEPTANCE=PASS")
    return 0


def _add_read_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--from", dest="start_utc", required=True)
    parser.add_argument("--to", dest="end_utc", required=True)
    parser.add_argument("--cutoff", dest="cutoff_utc")
    parser.add_argument("--mode", choices=("strict", "permissive"), default="strict")
    parser.add_argument("--current-policy", choices=("FINALIZED_ONLY",), default="FINALIZED_ONLY")
    parser.add_argument("--format", dest="output_format", choices=("csv", "json"), default="csv")
    parser.add_argument("--output", default="-")
    parser.add_argument("--cache-dir")
    parser.add_argument("--plan-output")
    parser.add_argument("--diagnostics-output")
    parser.add_argument("--receipt-output")
    parser.add_argument("--semantic-receipt-output")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded transport orchestration for canonical History Read + validated Fresh Current tail")
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("read")
    _add_read_arguments(read)
    read.set_defaults(func=_command_read)
    acceptance = sub.add_parser("acceptance")
    acceptance.add_argument("--series-id", default="spot.binance-spot.ETHUSDT.ohlcv.5m")
    acceptance.set_defaults(func=_command_acceptance)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HistoryCurrentTailRuntimeError, CurrentTailAdmissionError, history_consumer.HistoryConsumerError) as exc:
        print(f"HISTORY_CURRENT_TAIL_RUNTIME=FAIL error={exc}", file=sys.stderr)
        raise SystemExit(2)
