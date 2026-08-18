from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TITLE_PREFIX = "[history-read]"
ALLOWED_KEYS = {"series_id", "from_utc", "to_utc", "cutoff_utc", "mode", "current_policy", "output_format"}
REQUIRED_KEYS = {"series_id", "from_utc", "to_utc"}
ALLOWED_MODES = {"strict", "permissive"}
ALLOWED_FORMATS = {"csv", "json"}
ALLOWED_CURRENT_POLICIES = {"FINALIZED_ONLY", "INCLUDE_CURRENT_PROVISIONAL"}


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
    missing = REQUIRED_KEYS - set(payload)
    if missing:
        raise HistoryIssueRequestError(f"missing request fields: {sorted(missing)}")

    series_id = payload["series_id"]
    if not isinstance(series_id, str) or not series_id or len(series_id) > 256 or any(ch in series_id for ch in "\r\n"):
        raise HistoryIssueRequestError("series_id must be a non-empty single-line string <= 256 chars")

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
    _append_output(output, "issue_number", issue_number)
    _append_output(output, "series_id", request["series_id"])
    _append_output(output, "from_utc", request["from_utc"])
    _append_output(output, "to_utc", request["to_utc"])
    _append_output(output, "cutoff_utc", request["cutoff_utc"])
    _append_output(output, "mode", request["mode"])
    _append_output(output, "current_policy", request["current_policy"])
    _append_output(output, "output_format", request["output_format"])
    _append_output(output, "request_sha256", request_sha256)
    print(f"HISTORY_ISSUE_REQUEST=PASS issue={issue_number} request_sha256={request_sha256}")
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
