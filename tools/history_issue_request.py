from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TITLE_PREFIX = "[history-read]"
SERIES_KEYS = {"series_id", "from_utc", "to_utc", "cutoff_utc", "mode", "current_policy"}
SAMPLED_KEYS = {"capability_id", "target_utc", "selection_policy"}
COMMON_KEYS = {"output_format"}
ALLOWED_KEYS = SERIES_KEYS | SAMPLED_KEYS | COMMON_KEYS
REQUIRED_SERIES_KEYS = {"series_id", "from_utc", "to_utc"}
REQUIRED_SAMPLED_KEYS = {"capability_id", "target_utc"}
ALLOWED_MODES = {"strict", "permissive"}
ALLOWED_FORMATS = {"csv", "json"}
ALLOWED_CURRENT_POLICIES = {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}
SAMPLED_SELECTION_POLICY = "AT_OR_BEFORE"


class HistoryIssueRequestError(ValueError):
    """Raised when an issue is not a valid semantic history request."""


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise HistoryIssueRequestError(f"{field} must be a single-line UTC timestamp")
    if not value.endswith("Z"):
        raise HistoryIssueRequestError(f"{field} must use UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise HistoryIssueRequestError(f"invalid {field}: {value!r}") from exc
    if parsed.tzinfo != timezone.utc:
        raise HistoryIssueRequestError(f"{field} must be UTC")
    return parsed


def _single_line_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or any(ch in value for ch in "\r\n"):
        raise HistoryIssueRequestError(f"{field} must be a non-empty single-line string <= 256 chars")
    return value


def _parse_series_request(payload: dict[str, Any]) -> dict[str, str]:
    missing = REQUIRED_SERIES_KEYS - set(payload)
    if missing:
        raise HistoryIssueRequestError(f"missing request fields: {sorted(missing)}")

    series_id = _single_line_identifier(payload["series_id"], "series_id")
    start = _utc(payload["from_utc"], "from_utc")
    end = _utc(payload["to_utc"], "to_utc")
    if start >= end:
        raise HistoryIssueRequestError("from_utc must be earlier than to_utc")

    cutoff = payload.get("cutoff_utc") or ""
    if cutoff:
        _utc(cutoff, "cutoff_utc")

    mode = payload.get("mode", "strict")
    if mode not in ALLOWED_MODES:
        raise HistoryIssueRequestError(f"mode must be one of {sorted(ALLOWED_MODES)}")
    current_policy = payload.get("current_policy", "FINALIZED_ONLY")
    if current_policy not in ALLOWED_CURRENT_POLICIES:
        raise HistoryIssueRequestError(f"current_policy must be one of {sorted(ALLOWED_CURRENT_POLICIES)}")
    if current_policy != "FINALIZED_ONLY":
        raise HistoryIssueRequestError("active D6 history route supports current_policy=FINALIZED_ONLY only")

    output_format = payload.get("output_format", "csv")
    if output_format not in ALLOWED_FORMATS:
        raise HistoryIssueRequestError(f"output_format must be one of {sorted(ALLOWED_FORMATS)}")

    return {
        "series_id": series_id,
        "from_utc": payload["from_utc"],
        "to_utc": payload["to_utc"],
        "cutoff_utc": cutoff,
        "mode": mode,
        "current_policy": current_policy,
        "output_format": output_format,
    }


def _parse_sampled_request(payload: dict[str, Any]) -> dict[str, str]:
    missing = REQUIRED_SAMPLED_KEYS - set(payload)
    if missing:
        raise HistoryIssueRequestError(f"missing sampled request fields: {sorted(missing)}")
    capability_id = _single_line_identifier(payload["capability_id"], "capability_id")
    _utc(payload["target_utc"], "target_utc")
    selection_policy = payload.get("selection_policy", SAMPLED_SELECTION_POLICY)
    if selection_policy != SAMPLED_SELECTION_POLICY:
        raise HistoryIssueRequestError("sampled selection_policy must be AT_OR_BEFORE")
    output_format = payload.get("output_format", "json")
    if output_format != "json":
        raise HistoryIssueRequestError("sampled history output_format must be json")
    return {
        "capability_id": capability_id,
        "target_utc": payload["target_utc"],
        "selection_policy": selection_policy,
        "output_format": output_format,
    }


def parse_request_body(body: str) -> dict[str, str]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HistoryIssueRequestError("issue body must be a single JSON object") from exc
    if not isinstance(payload, dict):
        raise HistoryIssueRequestError("issue body must be a JSON object")
    unknown = set(payload) - ALLOWED_KEYS
    if unknown:
        raise HistoryIssueRequestError(f"unsupported request fields: {sorted(unknown)}")

    has_series = bool(set(payload) & SERIES_KEYS)
    has_sampled = bool(set(payload) & SAMPLED_KEYS)
    if has_series == has_sampled:
        raise HistoryIssueRequestError("request must contain exactly one of SERIES_REQUEST or SAMPLED_CAPABILITY_REQUEST")
    return _parse_series_request(payload) if has_series else _parse_sampled_request(payload)


def parse_issue_event(event: dict[str, Any]) -> tuple[int, dict[str, str], str]:
    issue = event.get("issue")
    repository = event.get("repository")
    if not isinstance(issue, dict) or not isinstance(repository, dict):
        raise HistoryIssueRequestError("GitHub event does not contain issue/repository objects")
    title = issue.get("title")
    if not isinstance(title, str) or not title.startswith(TITLE_PREFIX):
        raise HistoryIssueRequestError(f"issue title must start with {TITLE_PREFIX}")
    issue_login = ((issue.get("user") or {}).get("login"))
    owner_login = ((repository.get("owner") or {}).get("login"))
    if not issue_login or issue_login != owner_login:
        raise HistoryIssueRequestError("history requests are owner-only")
    number = issue.get("number")
    if not isinstance(number, int) or number <= 0:
        raise HistoryIssueRequestError("invalid issue number")
    request = parse_request_body(issue.get("body") or "")
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return number, request, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _append_output(path: Path, name: str, value: str | int) -> None:
    text = str(value)
    if "\n" in text or "\r" in text:
        raise HistoryIssueRequestError(f"unsafe multiline output: {name}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={text}\n")


def command_parse(args: argparse.Namespace) -> int:
    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    issue_number, request, request_sha256 = parse_issue_event(event)
    output = Path(args.github_output)
    request_kind = "SERIES" if "series_id" in request else "SAMPLED"
    values = {
        "issue_number": issue_number,
        "request_kind": request_kind,
        "series_id": request.get("series_id", ""),
        "from_utc": request.get("from_utc", ""),
        "to_utc": request.get("to_utc", ""),
        "cutoff_utc": request.get("cutoff_utc", ""),
        "mode": request.get("mode", ""),
        "current_policy": request.get("current_policy", ""),
        "capability_id": request.get("capability_id", ""),
        "target_utc": request.get("target_utc", ""),
        "selection_policy": request.get("selection_policy", ""),
        "output_format": request["output_format"],
        "request_sha256": request_sha256,
    }
    for name, value in values.items():
        _append_output(output, name, value)
    print(f"HISTORY_ISSUE_REQUEST=PASS issue={issue_number} request_kind={request_kind} request_sha256={request_sha256}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate owner-only semantic history requests from GitHub Issues")
    sub = parser.add_subparsers(dest="command", required=True)
    parse = sub.add_parser("parse")
    parse.add_argument("--event", required=True)
    parse.add_argument("--github-output", required=True)
    parse.set_defaults(func=command_parse)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
