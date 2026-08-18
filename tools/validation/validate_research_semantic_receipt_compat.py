from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RESEARCH_COMMIT = "6cfd98bda974f2280f3dba57b70e270e50cbf565"
RESEARCH_SCHEMA_GIT_BLOB_SHA1 = "02c90f8fed8b9ca58fe22695fcc50ac09b428143"
SCHEMA_PATH = Path("tests/fixtures/research-d9-5/market-data-ref.schema.json")
SERIES_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_SOURCE_RE = re.compile(
    r"^market-data:bridge:([0-9a-f]{40}):history-read:([^:]+):"
    r"plan=([0-9a-f]{64}):output=([0-9a-f]{64})$"
)


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode()
    return hashlib.sha1(header + raw).hexdigest()


def validate_receipt_schema(receipt: Any, schema: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    if not isinstance(receipt, dict):
        return {"SCHEMA_TYPE"}
    sem = schema["properties"]["semantic_receipt"]
    required = set(sem["required"])
    allowed = set(sem["properties"])
    if not required.issubset(receipt):
        codes.add("SCHEMA_REQUIRED")
    if set(receipt) - allowed:
        codes.add("SCHEMA_ADDITIONAL_PROPERTY")
    if receipt.get("receipt_schema_version") not in sem["properties"]["receipt_schema_version"]["enum"]:
        codes.add("SCHEMA_RECEIPT_VERSION")
    series_id = receipt.get("series_id")
    if not isinstance(series_id, str) or SERIES_ID_RE.fullmatch(series_id) is None:
        codes.add("SEMANTIC_SERIES_ID")
    for field in ("resolution_plan_sha256", "output_sha256"):
        value = receipt.get(field)
        if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
            codes.add("SCHEMA_SHA256")
    count = receipt.get("observation_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        codes.add("SCHEMA_OBSERVATION_COUNT")
    if receipt.get("finality") not in sem["properties"]["finality"]["enum"]:
        codes.add("SCHEMA_FINALITY")

    request = receipt.get("request")
    request_schema = sem["properties"]["request"]
    if not isinstance(request, dict):
        codes.add("SCHEMA_REQUEST")
    else:
        if set(request) - set(request_schema["properties"]):
            codes.add("SCHEMA_ADDITIONAL_PROPERTY")
        policy = request.get("current_policy")
        if policy is not None and policy not in request_schema["properties"]["current_policy"]["enum"]:
            codes.add("SCHEMA_CURRENT_POLICY")
        for field in ("from_utc", "to_utc", "observation_time_utc"):
            if field in request:
                try:
                    parse_utc(request[field])
                except Exception:
                    codes.add("SCHEMA_DATETIME")
        if request.get("cutoff_utc") is not None:
            try:
                parse_utc(request["cutoff_utc"])
            except Exception:
                codes.add("SCHEMA_DATETIME")

    revision = receipt.get("revision_context")
    revision_schema = sem["properties"]["revision_context"]
    if revision is not None:
        if not isinstance(revision, dict):
            codes.add("SCHEMA_REVISION")
        else:
            if not set(revision_schema["required"]).issubset(revision):
                codes.add("SCHEMA_REQUIRED")
            if set(revision) - set(revision_schema["properties"]):
                codes.add("SCHEMA_ADDITIONAL_PROPERTY")
            evidence = revision.get("evidence_sha256")
            if evidence is not None and (not isinstance(evidence, str) or HEX64_RE.fullmatch(evidence) is None):
                codes.add("SCHEMA_SHA256")
            for field in ("observation_time_utc", "effective_time_utc", "revision_known_at_utc"):
                if revision.get(field) is not None:
                    try:
                        parse_utc(revision[field])
                    except Exception:
                        codes.add("SCHEMA_DATETIME")
    return codes


def validate_research_semantics(
    receipt: dict[str, Any], *, ref_as_of: datetime, obj_known: datetime
) -> set[str]:
    """Mirror the exact D9.5 semantic checks at Research commit RESEARCH_COMMIT."""
    codes: set[str] = set()
    series_id = receipt.get("series_id")
    if not isinstance(series_id, str) or SERIES_ID_RE.fullmatch(series_id) is None:
        codes.add("SEMANTIC_SERIES_ID")

    request = receipt.get("request")
    if not isinstance(request, dict):
        return codes
    has_from = isinstance(request.get("from_utc"), str)
    has_to = isinstance(request.get("to_utc"), str)
    has_range = has_from and has_to
    has_observation = isinstance(request.get("observation_time_utc"), str)
    request_start = request_end = observation_time = None
    if has_from != has_to or has_range == has_observation:
        codes.add("SEMANTIC_REQUEST_IDENTITY")
    elif has_range:
        try:
            request_start = parse_utc(request["from_utc"])
            request_end = parse_utc(request["to_utc"])
        except Exception:
            pass
        else:
            if request_start >= request_end:
                codes.add("SEMANTIC_REQUEST_RANGE")
    else:
        try:
            observation_time = parse_utc(request["observation_time_utc"])
            request_end = observation_time
        except Exception:
            pass

    if request_end is not None and request_end > ref_as_of:
        codes.add("SEMANTIC_REQUEST_TIME")

    cutoff = None
    cutoff_raw = request.get("cutoff_utc")
    if cutoff_raw is not None:
        try:
            cutoff = parse_utc(cutoff_raw)
        except Exception:
            pass
        else:
            if request_end is not None and request_end > cutoff:
                codes.add("SEMANTIC_REQUEST_CUTOFF")
            if cutoff > obj_known:
                codes.add("SEMANTIC_REQUEST_CUTOFF")

    finality = receipt.get("finality")
    current_policy = request.get("current_policy", "FINALIZED_ONLY")
    if finality == "PROVISIONAL_INCLUDED" and current_policy != "INCLUDE_CURRENT_PROVISIONAL":
        codes.add("SEMANTIC_FINALITY")

    revision = receipt.get("revision_context")
    if not isinstance(revision, dict):
        return codes
    if cutoff is None:
        codes.add("SEMANTIC_REVISION_CUTOFF")
        return codes
    try:
        revision_observation = parse_utc(revision.get("observation_time_utc"))
        revision_known = parse_utc(revision.get("revision_known_at_utc"))
    except Exception:
        return codes
    if revision_known < revision_observation:
        codes.add("SEMANTIC_REVISION_TEMPORAL_ORDER")
    if revision_known > cutoff or revision_known > obj_known:
        codes.add("SEMANTIC_REVISION_CUTOFF")
    effective_raw = revision.get("effective_time_utc")
    if effective_raw is not None:
        try:
            effective = parse_utc(effective_raw)
        except Exception:
            effective = None
        if effective is not None:
            if revision_known < effective:
                codes.add("SEMANTIC_REVISION_TEMPORAL_ORDER")
            if effective > cutoff:
                codes.add("SEMANTIC_REVISION_CUTOFF")
    if request_start is not None and request_end is not None:
        if not request_start <= revision_observation < request_end:
            codes.add("SEMANTIC_REVISION_IDENTITY")
    elif observation_time is not None and revision_observation != observation_time:
        codes.add("SEMANTIC_REVISION_IDENTITY")
    return codes


def validate_binding(receipt: dict[str, Any], bridge_head: str, source_ref: str) -> set[str]:
    codes: set[str] = set()
    if HEX40_RE.fullmatch(bridge_head) is None:
        codes.add("MARKET_HEAD")
        return codes
    match = RECEIPT_SOURCE_RE.fullmatch(source_ref)
    if match is None:
        return {"BRIDGE_SOURCE_REF"}
    source_head, _, source_plan, source_output = match.groups()
    if source_head != bridge_head:
        codes.add("MARKET_HEAD_MISMATCH")
    if source_plan != receipt.get("resolution_plan_sha256"):
        codes.add("MARKET_PLAN_MISMATCH")
    if source_output != receipt.get("output_sha256"):
        codes.add("MARKET_OUTPUT_MISMATCH")
    return codes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--bridge-head", required=True)
    args = parser.parse_args()

    raw_schema = SCHEMA_PATH.read_bytes()
    actual_blob = git_blob_sha1(raw_schema)
    if actual_blob != RESEARCH_SCHEMA_GIT_BLOB_SHA1:
        raise RuntimeError(
            f"Research schema snapshot drift: expected {RESEARCH_SCHEMA_GIT_BLOB_SHA1}, got {actual_blob}"
        )
    schema = json.loads(raw_schema)
    if schema["properties"]["semantic_receipt"]["properties"]["receipt_schema_version"]["enum"] != [
        "history-access-receipt/2.0.0"
    ]:
        raise RuntimeError("unexpected Research semantic receipt schema authority")

    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    end = receipt["request"]["to_utc"]
    end_dt = parse_utc(end)
    ref_as_of = end_dt
    obj_known = end_dt + timedelta(minutes=10)
    source_ref = (
        f"market-data:bridge:{args.bridge_head}:history-read:qualification:"
        f"plan={receipt['resolution_plan_sha256']}:output={receipt['output_sha256']}"
    )

    positive = (
        validate_receipt_schema(receipt, schema)
        | validate_research_semantics(receipt, ref_as_of=ref_as_of, obj_known=obj_known)
        | validate_binding(receipt, args.bridge_head, source_ref)
    )
    if positive:
        raise RuntimeError(f"Research positive compatibility failed: {sorted(positive)}")

    cases: list[tuple[str, dict[str, Any], str, set[str]]] = []
    cases.append(("head_mismatch", copy.deepcopy(receipt), source_ref.replace(args.bridge_head, "1" * 40), {"MARKET_HEAD_MISMATCH"}))
    cases.append(("plan_mismatch", copy.deepcopy(receipt), source_ref.replace(receipt["resolution_plan_sha256"], "2" * 64), {"MARKET_PLAN_MISMATCH"}))
    cases.append(("output_mismatch", copy.deepcopy(receipt), source_ref.replace(receipt["output_sha256"], "3" * 64), {"MARKET_OUTPUT_MISMATCH"}))

    obj = copy.deepcopy(receipt)
    obj["request"].pop("from_utc", None); obj["request"].pop("to_utc", None)
    cases.append(("missing_request_identity", obj, source_ref, {"SEMANTIC_REQUEST_IDENTITY"}))

    obj = copy.deepcopy(receipt); obj["series_id"] = "bad series id"
    cases.append(("malformed_series_id", obj, source_ref, {"SEMANTIC_SERIES_ID"}))

    obj = copy.deepcopy(receipt); obj["finality"] = "INVALID"
    cases.append(("invalid_finality", obj, source_ref, {"SCHEMA_FINALITY"}))

    obj = copy.deepcopy(receipt); obj["storage_path"] = "history/forbidden"
    cases.append(("unsupported_storage_field", obj, source_ref, {"SCHEMA_ADDITIONAL_PROPERTY"}))

    obj = copy.deepcopy(receipt)
    cutoff = end_dt + timedelta(minutes=1)
    obj["request"]["cutoff_utc"] = iso(cutoff)
    obj["revision_context"] = {
        "observation_time_utc": obj["request"]["from_utc"],
        "effective_time_utc": obj["request"]["from_utc"],
        "revision_known_at_utc": iso(cutoff + timedelta(minutes=1)),
        "evidence_sha256": "e" * 64,
    }
    cases.append(("revision_known_after_cutoff", obj, source_ref, {"SEMANTIC_REVISION_CUTOFF"}))

    for name, candidate, candidate_source_ref, expected in cases:
        got = (
            validate_receipt_schema(candidate, schema)
            | validate_research_semantics(candidate, ref_as_of=ref_as_of, obj_known=obj_known)
            | validate_binding(candidate, args.bridge_head, candidate_source_ref)
        )
        if not got or not (got & expected):
            raise RuntimeError(
                f"Research negative case {name} did not fail closed as expected; "
                f"expected={sorted(expected)} got={sorted(got)}"
            )
        print(f"RESEARCH_NEGATIVE_{name.upper()}=PASS codes={','.join(sorted(got))}")

    print("RESEARCH_CONTRACT_SOURCE_COMMIT=" + RESEARCH_COMMIT)
    print("RESEARCH_SCHEMA_GIT_BLOB_SHA1=" + actual_blob)
    print("RESEARCH_SCHEMA_SNAPSHOT_ROLE=TEST_SNAPSHOT_ONLY")
    print("DATA_BRIDGE_V2_RECEIPT_TO_RESEARCH_SCHEMA=PASS")
    print("SEMANTIC_RECEIPT_SCHEMA=" + receipt["receipt_schema_version"])
    print("SEMANTIC_RECEIPT_PLAN_SHA256=" + receipt["resolution_plan_sha256"])
    print("SEMANTIC_RECEIPT_OUTPUT_SHA256=" + receipt["output_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
