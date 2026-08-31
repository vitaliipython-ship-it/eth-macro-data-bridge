from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from tools.current_data_promotion import PromotionError, validate_artifact

ROOT = Path(__file__).resolve().parents[1]
TAIL_SCHEMA = "validated-fresh-current-tail/1.0.0"
REQUEST_SCHEMAS = {"fresh-current-agent-request/1.0.0","fresh-current-agent-request/1.1.0"}
RESOURCE_INDEX_SCHEMAS = {"fresh-current-resource-index/1.0.0","fresh-current-resource-index/1.1.0"}
GENERATION_SCHEMAS = {"fresh-current-generation/1.0.0","fresh-current-generation/1.1.0"}
VALIDATION_SCHEMAS = {"fresh-current-validation-summary/1.0.0","fresh-current-validation-summary/1.1.0"}
TRANSPORT_SCHEMAS = {"fresh-current-transport-receipt/1.0.0","fresh-current-transport-receipt/1.1.0"}
CONTRACT_ID = "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1"
CONTRACT_VERSIONS = {"1.0.0","1.1.0"}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CurrentTailAdmissionError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _load_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentTailAdmissionError(code, f"cannot read validated current-tail evidence: {path}") from exc


def _parse_utc_ms(value: object, field: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z") or "\n" in value or "\r" in value:
        raise CurrentTailAdmissionError("CURRENT_TAIL_TIME_INVALID", f"{field} must use UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CurrentTailAdmissionError("CURRENT_TAIL_TIME_INVALID", f"invalid {field}: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CurrentTailAdmissionError("CURRENT_TAIL_TIME_INVALID", f"{field} must be UTC")
    return int(parsed.timestamp() * 1000)


def _safe_member(root: Path, member: object) -> Path:
    if not isinstance(member, str) or not member:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "artifact member missing")
    relative = Path(member)
    if relative.is_absolute() or ".." in relative.parts:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "artifact member escaped generation root")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "artifact member escaped generation root")
    return resolved


def _relative_to_repository(path: Path, repository_root: Path) -> str:
    try:
        return path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError as exc:
        raise CurrentTailAdmissionError(
            "CURRENT_TAIL_RESOURCE_INVALID",
            "validated Fresh Current generation must be installed inside repository checkout before resolution",
        ) from exc


def _validate_generation_manifest(generation: Mapping[str, Any]) -> None:
    if generation.get("schema_version") not in GENERATION_SCHEMAS:
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_INVALID", "generation schema mismatch")
    digest = str(generation.get("generation_manifest_sha256") or "")
    if not _HEX64.fullmatch(digest):
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_INVALID", "generation manifest digest invalid")
    core = dict(generation)
    core.pop("generation_manifest_sha256", None)
    if _sha256_json(core) != digest:
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_FORGED", "generation manifest digest mismatch")


def _generated_at_utc(generation: Mapping[str, Any]) -> tuple[str, int]:
    schema = generation.get("schema_version")
    if schema == "fresh-current-generation/1.0.0":
        value = generation.get("generated_at_utc")
        field = "generated_at_utc"
    elif schema == "fresh-current-generation/1.1.0":
        ordinary = generation.get("ordinary_generation")
        if not isinstance(ordinary, Mapping):
            raise CurrentTailAdmissionError(
                "CURRENT_TAIL_GENERATION_INVALID",
                "historical series tail requires ordinary_generation",
            )
        value = ordinary.get("data_manifest_generated_at_utc")
        field = "ordinary_generation.data_manifest_generated_at_utc"
    else:
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_INVALID", "generation schema mismatch")
    generated_ms = _parse_utc_ms(value, field)
    assert isinstance(value, str)
    return value, generated_ms


def _generation_id(wrapper: Mapping[str, Any], index: Mapping[str, Any], generation: Mapping[str, Any]) -> str:
    request=wrapper.get("request")
    if not isinstance(request,Mapping):
        raise CurrentTailAdmissionError("CURRENT_TAIL_REQUEST_INVALID","normalized Fresh Current request missing")
    request_sha=_sha256_json(request)
    if wrapper.get("schema_version") not in REQUEST_SCHEMAS or wrapper.get("contract_id")!=CONTRACT_ID or wrapper.get("contract_version") not in CONTRACT_VERSIONS:
        raise CurrentTailAdmissionError("CURRENT_TAIL_REQUEST_INVALID","Fresh Current request contract mismatch")
    if wrapper.get("request_sha256")!=request_sha:
        raise CurrentTailAdmissionError("CURRENT_TAIL_REQUEST_FORGED","Fresh Current request digest mismatch")
    if index.get("request_sha256")!=request_sha or generation.get("request_sha256")!=request_sha:
        raise CurrentTailAdmissionError("CURRENT_TAIL_REQUEST_MISMATCH","generation/index request binding mismatch")
    domains=[{"domain_id":row["domain_id"],"resource_logical_id":row["resource_logical_id"],"sha256":row["sha256"]}
             for row in index.get("domains",[]) if isinstance(row,Mapping)]
    series=[{"series_id":row["series_id"],"latest_bars":row["latest_bars"],"sha256":row["sha256"],
             "semantic_receipt_sha256":row["semantic_receipt_sha256"],"semantic_output_sha256":row["semantic_output_sha256"]}
            for row in index.get("series",[]) if isinstance(row,Mapping)]
    domains.sort(key=lambda row:str(row["domain_id"])); series.sort(key=lambda row:str(row["series_id"]))
    if generation.get("schema_version")=="fresh-current-generation/1.0.0":
        basis={
            "contract_id":CONTRACT_ID,"contract_version":"1.0.0","control_plane_head":generation.get("control_plane_head"),
            "collector_version":generation.get("collector_version"),"generated_at_utc":generation.get("generated_at_utc"),
            "requested_semantic_capabilities":{"required_domains":list(request.get("required_domains",[])),"required_series":list(request.get("required_series",[]))},
            "validated_domain_resources":domains,"validated_series_resources":series,
        }
    else:
        liquidity=[{
            "semantic_resource_id":row.get("semantic_resource_id"),"resource_family_sha256":row.get("resource_family_sha256"),
            "resource_sha256":row.get("resource_sha256"),"resource_qualification_request_sha256":row.get("resource_qualification_request_sha256"),
            "current_semantic_request_sha256":row.get("current_semantic_request_sha256"),
            "qualification_receipt_sha256":row.get("qualification_receipt_sha256"),
            "request_satisfaction_sha256":row.get("request_satisfaction_sha256"),
        } for row in index.get("liquidity_resources",[]) if isinstance(row,Mapping)]
        liquidity.sort(key=lambda row:(str(row["semantic_resource_id"]),str(row["current_semantic_request_sha256"])))
        basis={
            "contract_id":CONTRACT_ID,"contract_version":"1.1.0","control_plane_head":generation.get("control_plane_head"),
            "requested_semantic_capabilities":{
                "required_domains":list(request.get("required_domains",[])),
                "required_series":list(request.get("required_series",[])),
                "required_liquidity":list(request.get("required_liquidity",[])),
            },
            "ordinary_generation":generation.get("ordinary_generation"),
            "validated_domain_resources":domains,"validated_series_resources":series,
            "validated_exact_liquidity_current_bindings":liquidity,
        }
    return _sha256_json(basis)

def _normalized_rows(raw: bytes, *, interval_ms: int) -> tuple[list[tuple[int, str, str, str, str, str]], str]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "normalized current series is not JSON") from exc
    if not isinstance(payload, list) or not payload:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "normalized current series must contain observations")
    rows: list[tuple[int, str, str, str, str, str]] = []
    semantic: list[dict[str, Any]] = []
    previous: int | None = None
    for item in payload:
        if not isinstance(item, Mapping):
            raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "normalized observation must be an object")
        ts = _parse_utc_ms(item.get("open_time"), "current_tail.open_time")
        if previous is not None and ts != previous + interval_ms:
            raise CurrentTailAdmissionError("CURRENT_TAIL_GAP", f"validated current tail is not contiguous at {ts}")
        previous = ts
        values: list[str] = []
        try:
            numbers = [Decimal(str(item[field])) for field in ("open", "high", "low", "close", "volume")]
            if any(not value.is_finite() for value in numbers):
                raise InvalidOperation
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", f"invalid OHLCV observation at {ts}") from exc
        o, h, l, c, v = numbers
        if h < max(o, l, c) or l > min(o, h, c) or v < 0:
            raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", f"invalid OHLCV bounds at {ts}")
        values = [format(value, "f") for value in numbers]
        row = (ts, *values)
        rows.append(row)
        semantic.append(
            {
                "timestamp_ms": ts,
                "value": {"open": values[0], "high": values[1], "low": values[2], "close": values[3], "volume": values[4]},
                "finality": "FINALIZED",
            }
        )
    return rows, _sha256_json(semantic)


def bind_validated_tail(
    artifact_root: Path,
    *,
    series_id: str,
    interval_ms: int,
    cutoff_ms: int | None,
    repository_root: Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(series_id, str) or not series_id or not isinstance(interval_ms, int) or interval_ms <= 0:
        raise CurrentTailAdmissionError("CURRENT_TAIL_SERIES_INVALID", "series identity/interval invalid")
    artifact_root = Path(artifact_root)
    repository_root = Path(repository_root)
    try:
        _handoff, promotion_generation = validate_artifact(
            artifact_root,
            source_control_root=repository_root,
        )
    except PromotionError as exc:
        raise CurrentTailAdmissionError("CURRENT_TAIL_PROMOTION_EVIDENCE_INVALID", str(exc)) from exc

    generation = _load_json(artifact_root / "current-generation.json", "CURRENT_TAIL_GENERATION_INVALID")
    wrapper = _load_json(artifact_root / "request.json", "CURRENT_TAIL_REQUEST_INVALID")
    index = _load_json(artifact_root / "resource-index.json", "CURRENT_TAIL_RESOURCE_INDEX_INVALID")
    validation = _load_json(artifact_root / "validation-summary.json", "CURRENT_TAIL_VALIDATION_MISSING")
    transport = _load_json(artifact_root / "transport-receipt.json", "CURRENT_TAIL_TRANSPORT_INVALID")
    if not all(isinstance(value, Mapping) for value in (generation, wrapper, index, validation, transport)):
        raise CurrentTailAdmissionError("CURRENT_TAIL_EVIDENCE_INVALID", "Fresh Current evidence must be JSON objects")
    _validate_generation_manifest(generation)
    if dict(generation) != promotion_generation:
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_MISMATCH", "promotion/generation readback mismatch")
    if index.get("schema_version") not in RESOURCE_INDEX_SCHEMAS or index.get("contract_id") != CONTRACT_ID or index.get("contract_version") not in CONTRACT_VERSIONS:
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INDEX_INVALID", "resource index contract mismatch")
    if validation.get("schema_version") not in VALIDATION_SCHEMAS or validation.get("status") != "PASS":
        raise CurrentTailAdmissionError("CURRENT_TAIL_VALIDATION_MISSING", "Fresh Current validation is not PASS")
    if transport.get("schema_version") not in TRANSPORT_SCHEMAS or transport.get("authority") != "TRANSPORT_ONLY":
        raise CurrentTailAdmissionError("CURRENT_TAIL_TRANSPORT_INVALID", "Fresh Current transport receipt invalid")
    if transport.get("remote_repository_mutation") is not False or transport.get("git_commit") is not False or transport.get("git_push") is not False:
        raise CurrentTailAdmissionError("CURRENT_TAIL_MUTATION_BOUNDARY", "Fresh Current transport mutated repository authority")
    for field in ("generation_id", "generation_manifest_sha256", "control_plane_head", "control_plane_tree"):
        if transport.get(field) != generation.get(field):
            raise CurrentTailAdmissionError("CURRENT_TAIL_TRANSPORT_INVALID", f"transport/generation binding mismatch: {field}")
    if transport.get("head_after") != generation.get("control_plane_head"):
        raise CurrentTailAdmissionError("CURRENT_TAIL_MUTATION_BOUNDARY", "Fresh Current HEAD changed during generation")

    index_raw = (artifact_root / "resource-index.json").read_bytes()
    validation_raw = (artifact_root / "validation-summary.json").read_bytes()
    if _sha256_bytes(index_raw) != generation.get("resource_index_sha256"):
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INDEX_FORGED", "resource index digest mismatch")
    if _sha256_bytes(validation_raw) != generation.get("validation_summary_sha256"):
        raise CurrentTailAdmissionError("CURRENT_TAIL_VALIDATION_FORGED", "validation summary digest mismatch")
    expected_generation_id = _generation_id(wrapper, index, generation)
    if generation.get("generation_id") != expected_generation_id:
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_ID_MISMATCH", "Fresh Current generation_id is forged or mismatched")
    if generation.get("on_demand_current_data_can_be_used_for_live_analysis") is not True:
        raise CurrentTailAdmissionError("CURRENT_TAIL_ANALYSIS_NOT_ALLOWED", "CURRENT_ANALYSIS_ALLOWED is not YES")
    if generation.get("market_data_semantic_authority") != "ETH_MACRO_DATA_BRIDGE":
        raise CurrentTailAdmissionError("CURRENT_TAIL_AUTHORITY_INVALID", "Fresh Current semantic authority mismatch")
    if generation.get("actions_artifact_is_market_data_authority") is not False:
        raise CurrentTailAdmissionError("CURRENT_TAIL_AUTHORITY_INVALID", "Actions artifact cannot become market-data authority")

    generated_at_utc, generated_ms = _generated_at_utc(generation)
    known_at_ms=_parse_utc_ms(generation.get("known_at_utc"),"known_at_utc")
    if cutoff_ms is not None and (generated_ms > cutoff_ms or known_at_ms > cutoff_ms):
        raise CurrentTailAdmissionError("CURRENT_TAIL_PIT_CUTOFF", "Fresh Current generation is future-known under requested cutoff")
    head = str(generation.get("control_plane_head") or "")
    tree = str(generation.get("control_plane_tree") or "")
    generation_id = str(generation.get("generation_id") or "")
    if not _HEX40.fullmatch(head) or not _HEX40.fullmatch(tree) or not _HEX64.fullmatch(generation_id):
        raise CurrentTailAdmissionError("CURRENT_TAIL_GENERATION_INVALID", "generation provenance identity invalid")

    request = wrapper["request"]
    requested = [row for row in request.get("required_series", []) if isinstance(row, Mapping) and row.get("series_id") == series_id]
    if len(requested) != 1 or request.get("current_policy") != "FINALIZED_ONLY":
        raise CurrentTailAdmissionError("CURRENT_TAIL_WRONG_SERIES", "generation was not requested for exact series under FINALIZED_ONLY")
    matches = [row for row in index.get("series", []) if isinstance(row, Mapping) and row.get("series_id") == series_id]
    if len(matches) != 1:
        raise CurrentTailAdmissionError("CURRENT_TAIL_WRONG_SERIES", "validated resource index does not contain exact requested series")
    row = matches[0]
    if (
        row.get("status") != "PASS"
        or row.get("availability") != "AVAILABLE"
        or row.get("finality") != "FINALIZED"
        or row.get("freshness") != "VALIDATED_CURRENT_GENERATION"
        or row.get("gap_count") != 0
        or row.get("duplicates") != 0
        or row.get("rows") != row.get("expected_rows")
        or row.get("latest_bars") != requested[0].get("latest_bars")
    ):
        raise CurrentTailAdmissionError("CURRENT_TAIL_SERIES_NOT_VALIDATED", "Fresh Current series validation gates are not PASS")
    for field in ("sha256", "semantic_receipt_sha256", "semantic_output_sha256", "resolution_plan_sha256"):
        if not _HEX64.fullmatch(str(row.get(field) or "")):
            raise CurrentTailAdmissionError("CURRENT_TAIL_SERIES_NOT_VALIDATED", f"series identity missing: {field}")

    resource_path = _safe_member(artifact_root, row.get("artifact_member"))
    if not resource_path.is_file():
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_INVALID", "validated normalized series member missing")
    raw = resource_path.read_bytes()
    if len(raw) != row.get("size_bytes") or _sha256_bytes(raw) != row.get("sha256"):
        raise CurrentTailAdmissionError("CURRENT_TAIL_RESOURCE_FORGED", "validated normalized series bytes mismatch")
    rows, semantic_output = _normalized_rows(raw, interval_ms=interval_ms)
    if len(rows) != row.get("rows") or semantic_output != row.get("semantic_output_sha256"):
        raise CurrentTailAdmissionError("CURRENT_TAIL_SEMANTIC_OUTPUT_MISMATCH", "normalized series semantic identity mismatch")
    first_ms = rows[0][0]
    last_ms = rows[-1][0]
    finalized_cutoff_ms = last_ms + interval_ms
    if finalized_cutoff_ms > known_at_ms:
        raise CurrentTailAdmissionError("CURRENT_TAIL_OPEN_BAR_FORBIDDEN", "validated tail contains an observation not finalized by generation known-at")
    if cutoff_ms is not None and finalized_cutoff_ms > cutoff_ms:
        raise CurrentTailAdmissionError("CURRENT_TAIL_PIT_CUTOFF", "tail finalization lies beyond requested cutoff")

    descriptor: dict[str, Any] = {
        "schema_version": TAIL_SCHEMA,
        "authority_class": "VALIDATED_EPHEMERAL_CURRENT_TAIL",
        "durable_history_authority": False,
        "actions_artifact_is_durable_history_authority": False,
        "current_data_agent_request": "PASS",
        "validation": "PASS",
        "current_analysis_allowed": True,
        "current_policy": "FINALIZED_ONLY",
        "series_id": series_id,
        "interval_ms": interval_ms,
        "first_timestamp_ms": first_ms,
        "last_timestamp_ms": last_ms,
        "finalized_cutoff_ms": finalized_cutoff_ms,
        "generation_id": generation_id,
        "generated_at_utc": generated_at_utc,
        "known_at_utc": generation["known_at_utc"],
        "control_plane_head": head,
        "control_plane_tree": tree,
        "generation_manifest_sha256": generation["generation_manifest_sha256"],
        "resource_index_sha256": generation["resource_index_sha256"],
        "validation_summary_sha256": generation["validation_summary_sha256"],
        "request_sha256": generation["request_sha256"],
        "semantic_receipt_sha256": row["semantic_receipt_sha256"],
        "semantic_output_sha256": row["semantic_output_sha256"],
        "resolution_plan_sha256": row["resolution_plan_sha256"],
        "resource_path": _relative_to_repository(resource_path, repository_root),
        "sha256": row["sha256"],
        "size_bytes": row["size_bytes"],
    }
    descriptor["descriptor_sha256"] = _sha256_json(descriptor)
    return descriptor


def validate_descriptor(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    if descriptor.get("schema_version") != TAIL_SCHEMA or descriptor.get("authority_class") != "VALIDATED_EPHEMERAL_CURRENT_TAIL":
        raise CurrentTailAdmissionError("CURRENT_TAIL_DESCRIPTOR_INVALID", "validated current-tail descriptor identity mismatch")
    digest = str(descriptor.get("descriptor_sha256") or "")
    if not _HEX64.fullmatch(digest):
        raise CurrentTailAdmissionError("CURRENT_TAIL_DESCRIPTOR_INVALID", "validated current-tail descriptor digest missing")
    body = dict(descriptor)
    body.pop("descriptor_sha256", None)
    if _sha256_json(body) != digest:
        raise CurrentTailAdmissionError("CURRENT_TAIL_DESCRIPTOR_FORGED", "validated current-tail descriptor digest mismatch")
    if descriptor.get("durable_history_authority") is not False or descriptor.get("actions_artifact_is_durable_history_authority") is not False:
        raise CurrentTailAdmissionError("CURRENT_TAIL_AUTHORITY_INVALID", "ephemeral current tail cannot be relabeled durable")
    if descriptor.get("current_data_agent_request") != "PASS" or descriptor.get("validation") != "PASS" or descriptor.get("current_analysis_allowed") is not True:
        raise CurrentTailAdmissionError("CURRENT_TAIL_VALIDATION_MISSING", "current-tail admission gates are not PASS")
    if descriptor.get("current_policy") != "FINALIZED_ONLY":
        raise CurrentTailAdmissionError("CURRENT_TAIL_OPEN_BAR_FORBIDDEN", "current-tail descriptor is not FINALIZED_ONLY")
    return dict(descriptor)
