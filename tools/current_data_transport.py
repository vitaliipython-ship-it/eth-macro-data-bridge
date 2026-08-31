from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from canonical_json import sha256_canonical_json
from liquidity_s1_runtime import LiquidityS1Error, normalize_liquidity_request, validate_qualified_liquidity_resource
from tools.capability_index import (
    describe_capability,
    list_capabilities,
    describe_requestable_capability,
)
from tools.history_consumer import D6_CURRENT_POLICY, LATEST_BARS_SAFE_MAX, latest_history

CONTRACT_ID = "ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1"
CONTRACT_VERSION = "1.1.0"
ISSUE_PREFIX = "[current-data]"
REQUEST_SCHEMA_V10 = "fresh-current-agent-request/1.0.0"
REQUEST_SCHEMA = "fresh-current-agent-request/1.1.0"
RESOURCE_INDEX_SCHEMA_V10 = "fresh-current-resource-index/1.0.0"
RESOURCE_INDEX_SCHEMA = "fresh-current-resource-index/1.1.0"
GENERATION_SCHEMA_V10 = "fresh-current-generation/1.0.0"
GENERATION_SCHEMA = "fresh-current-generation/1.1.0"
TRANSPORT_RECEIPT_SCHEMA_V10 = "fresh-current-transport-receipt/1.0.0"
TRANSPORT_RECEIPT_SCHEMA = "fresh-current-transport-receipt/1.1.0"
VALIDATION_SCHEMA_V10 = "fresh-current-validation-summary/1.0.0"
VALIDATION_SCHEMA = "fresh-current-validation-summary/1.1.0"
REQUEST_SATISFACTION_SCHEMA = "fresh-current-request-satisfaction/1.1.0"
EXECUTION_TRANSPORT = "GITHUB_ACTIONS_ISSUE_V1"
FUTURE_EXECUTION_TRANSPORT = "AIFE_SERVER_D8_CURRENT_V1"
DEFAULT_LATEST_BARS = 256
DEFAULT_MAX_GENERATION_AGE_SECONDS = 600
MAX_GENERATION_AGE_SECONDS = 86400
ALLOWED_DOMAINS = ("SPOT", "DERIVATIVES", "OPTIONS", "LIQUIDITY", "ANALYTICS", "EVENTS")
DOMAIN_PATH_KEYS = {
    "SPOT": "current_spot_manifest",
    "DERIVATIVES": "derivatives_manifest",
    "OPTIONS": "options_manifest",
    "LIQUIDITY": "liquidity_manifest",
    "ANALYTICS": "analytics_manifest",
    "EVENTS": "events_manifest",
}
ALLOWED_REQUEST_KEYS = {
    "request_type",
    "required_series",
    "required_domains",
    "max_generation_age_seconds",
    "current_policy",
}
FORBIDDEN_PHYSICAL_INPUTS = {
    "provider_url",
    "release_tag",
    "asset_name",
    "asset_id",
    "resource_path",
    "filesystem_path",
    "manifest_path",
    "sha256",
    "vps_path",
    "database_locator",
    "browser_download_url",
    "raw_url",
}
SERIES_OBJECT_KEYS = {"series_id", "latest_bars"}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CurrentDataTransportError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentDataTransportError("INVALID_JSON_RESOURCE", f"cannot read canonical JSON: {path}") from exc


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "\n" in value or "\r" in value:
        raise CurrentDataTransportError("INVALID_UTC", f"{field} must use single-line UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CurrentDataTransportError("INVALID_UTC", f"invalid {field}: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CurrentDataTransportError("INVALID_UTC", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _append_output(path: Path | None, name: str, value: object) -> None:
    if path is None:
        return
    text = str(value)
    if "\n" in text or "\r" in text:
        raise CurrentDataTransportError("UNSAFE_GITHUB_OUTPUT", f"unsafe multiline output: {name}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={text}\n")


def _normalize_series_item(value: object) -> dict[str, object]:
    if isinstance(value, str):
        series_id = value
        latest_bars = DEFAULT_LATEST_BARS
    elif isinstance(value, Mapping):
        unknown = set(value) - SERIES_OBJECT_KEYS
        forbidden = unknown & FORBIDDEN_PHYSICAL_INPUTS
        if forbidden:
            raise CurrentDataTransportError(
                "FORBIDDEN_PHYSICAL_INPUT",
                f"series request contains forbidden physical fields: {sorted(forbidden)}",
            )
        if unknown:
            raise CurrentDataTransportError("UNKNOWN_REQUEST_FIELD", f"unsupported series fields: {sorted(unknown)}")
        series_id = value.get("series_id")
        latest_bars = value.get("latest_bars", DEFAULT_LATEST_BARS)
    else:
        raise CurrentDataTransportError("INVALID_SERIES_REQUEST", "required_series items must be strings or JSON objects")
    if not isinstance(series_id, str) or not series_id or len(series_id) > 256 or any(ch in series_id for ch in "\r\n"):
        raise CurrentDataTransportError("INVALID_SERIES_REQUEST", "series_id must be a non-empty single-line string <= 256 chars")
    if isinstance(latest_bars, bool) or not isinstance(latest_bars, int) or not 1 <= latest_bars <= LATEST_BARS_SAFE_MAX:
        raise CurrentDataTransportError(
            "LATEST_BARS_OUT_OF_RANGE",
            f"latest_bars must be an integer in [1,{LATEST_BARS_SAFE_MAX}]",
        )
    return {"series_id": series_id, "latest_bars": latest_bars}


def _validate_series_discovery(series_items: Sequence[Mapping[str, object]]) -> None:
    catalog = list_capabilities()
    for request in series_items:
        series_id = request["series_id"]
        matches = [row for row in catalog if row.get("series_id") == series_id]
        if not matches:
            raise CurrentDataTransportError("UNKNOWN_SERIES", f"unknown canonical series_id: {series_id}")
        if len(matches) != 1:
            raise CurrentDataTransportError("AMBIGUOUS_SERIES", f"ambiguous canonical series_id: {series_id}")


def _normalize_request_v10(payload: object) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise CurrentDataTransportError("JSON_OBJECT_REQUIRED", "request body must be one JSON object")
    forbidden = set(payload) & FORBIDDEN_PHYSICAL_INPUTS
    if forbidden:
        raise CurrentDataTransportError(
            "FORBIDDEN_PHYSICAL_INPUT",
            f"request contains forbidden physical fields: {sorted(forbidden)}",
        )
    unknown = set(payload) - ALLOWED_REQUEST_KEYS
    if unknown:
        raise CurrentDataTransportError("UNKNOWN_REQUEST_FIELD", f"unsupported request fields: {sorted(unknown)}")
    request_type = payload.get("request_type")
    if request_type != "FRESH_CURRENT":
        raise CurrentDataTransportError("INVALID_REQUEST_TYPE", "request_type must be FRESH_CURRENT")
    current_policy = payload.get("current_policy", D6_CURRENT_POLICY)
    if current_policy != D6_CURRENT_POLICY:
        raise CurrentDataTransportError("CURRENT_POLICY_UNSUPPORTED", "current_policy must be FINALIZED_ONLY")

    raw_series = payload.get("required_series", [])
    if not isinstance(raw_series, list):
        raise CurrentDataTransportError("INVALID_SERIES_REQUEST", "required_series must be a JSON array")
    series_items = [_normalize_series_item(value) for value in raw_series]
    series_ids = [str(row["series_id"]) for row in series_items]
    if len(series_ids) != len(set(series_ids)):
        raise CurrentDataTransportError("DUPLICATE_SERIES", "required_series must be duplicate-free")
    series_items.sort(key=lambda row: str(row["series_id"]))

    raw_domains = payload.get("required_domains", [])
    if not isinstance(raw_domains, list) or not all(isinstance(value, str) for value in raw_domains):
        raise CurrentDataTransportError("INVALID_DOMAIN_REQUEST", "required_domains must be an array of strings")
    domains = list(raw_domains)
    if len(domains) != len(set(domains)):
        raise CurrentDataTransportError("DUPLICATE_DOMAIN", "required_domains must be duplicate-free")
    invalid = sorted(set(domains) - set(ALLOWED_DOMAINS))
    if invalid:
        raise CurrentDataTransportError(
            "INVALID_DOMAIN_REQUEST",
            f"required_domains values must be in {list(ALLOWED_DOMAINS)}; invalid={invalid}",
        )
    domains.sort()
    # Empty ordinary requirements are permitted internally for 1.1 exact-liquidity-only requests.

    max_age = payload.get("max_generation_age_seconds", DEFAULT_MAX_GENERATION_AGE_SECONDS)
    if isinstance(max_age, bool) or not isinstance(max_age, int) or not 1 <= max_age <= MAX_GENERATION_AGE_SECONDS:
        raise CurrentDataTransportError(
            "INVALID_FRESHNESS_THRESHOLD",
            f"max_generation_age_seconds must be an integer in [1,{MAX_GENERATION_AGE_SECONDS}]",
        )
    _validate_series_discovery(series_items)
    return {
        "request_type": "FRESH_CURRENT",
        "required_series": series_items,
        "required_domains": domains,
        "max_generation_age_seconds": max_age,
        "current_policy": D6_CURRENT_POLICY,
    }


def _normalize_required_liquidity(raw: object) -> list[dict[str, object]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CurrentDataTransportError("INVALID_LIQUIDITY_REQUEST", "required_liquidity must be a JSON array")
    normalized: list[tuple[str, dict[str, object]]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise CurrentDataTransportError("INVALID_LIQUIDITY_REQUEST", "required_liquidity items must be JSON objects")
        try:
            request = normalize_liquidity_request(item)
        except LiquidityS1Error as exc:
            raise CurrentDataTransportError("INVALID_LIQUIDITY_REQUEST", str(exc)) from exc
        try:
            capability = describe_requestable_capability(str(request["series_id"]))
        except Exception as exc:
            raise CurrentDataTransportError("UNKNOWN_REQUESTABLE_CAPABILITY", str(request["series_id"])) from exc
        if (
            capability.get("capability_id") != request["series_id"]
            or capability.get("provider_id") != request["provider_id"]
            or capability.get("instrument_id") != request["instrument_id"]
            or capability.get("book_kind") != request["book_kind"]
            or request["representation"] not in capability.get("supported_representations", [])
        ):
            raise CurrentDataTransportError(
                "REQUEST_CAPABILITY_IDENTITY_MISMATCH",
                f"exact liquidity request does not match requestable capability: {request['series_id']}",
            )
        digest = sha256_canonical_json(request)
        if digest in seen:
            raise CurrentDataTransportError("DUPLICATE_LIQUIDITY_REQUEST", f"duplicate exact liquidity request: {request['series_id']}")
        seen.add(digest)
        normalized.append((digest, dict(request)))
    normalized.sort(key=lambda row: (str(row[1]["series_id"]), row[0]))
    return [row[1] for row in normalized]


def normalize_request(payload: object) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise CurrentDataTransportError("JSON_OBJECT_REQUIRED", "request body must be one JSON object")
    allowed = set(ALLOWED_REQUEST_KEYS) | {"required_liquidity"}
    forbidden = set(payload) & FORBIDDEN_PHYSICAL_INPUTS
    if forbidden:
        raise CurrentDataTransportError("FORBIDDEN_PHYSICAL_INPUT", f"request contains forbidden physical fields: {sorted(forbidden)}")
    unknown = set(payload) - allowed
    if unknown:
        raise CurrentDataTransportError("UNKNOWN_REQUEST_FIELD", f"unsupported request fields: {sorted(unknown)}")
    ordinary = _normalize_request_v10({key: value for key, value in payload.items() if key != "required_liquidity"})
    liquidity = _normalize_required_liquidity(payload.get("required_liquidity", []))
    if not ordinary["required_series"] and not ordinary["required_domains"] and not liquidity:
        raise CurrentDataTransportError(
            "EMPTY_SEMANTIC_REQUEST",
            "at least one required_series, required_domains or required_liquidity entry is required",
        )
    return {
        "request_type": ordinary["request_type"],
        "required_series": ordinary["required_series"],
        "required_domains": ordinary["required_domains"],
        "required_liquidity": liquidity,
        "max_generation_age_seconds": ordinary["max_generation_age_seconds"],
        "current_policy": ordinary["current_policy"],
    }


def parse_request_body(body: str) -> dict[str, object]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CurrentDataTransportError("MALFORMED_JSON", "request body must be valid JSON only") from exc
    return normalize_request(payload)


def request_wrapper(request: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(request)
    return {
        "schema_version": REQUEST_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "request": normalized,
        "request_sha256": _sha256_json(normalized),
    }


def parse_issue_event(event: Mapping[str, object]) -> tuple[int, dict[str, object]]:
    issue = event.get("issue")
    repository = event.get("repository")
    if not isinstance(issue, Mapping) or not isinstance(repository, Mapping):
        raise CurrentDataTransportError("INVALID_ISSUE_EVENT", "GitHub event lacks issue/repository objects")
    title = issue.get("title")
    if not isinstance(title, str) or not title.startswith(ISSUE_PREFIX):
        raise CurrentDataTransportError("INVALID_ISSUE_PREFIX", f"issue title must start with {ISSUE_PREFIX}")
    issue_login = ((issue.get("user") or {}) if isinstance(issue.get("user"), Mapping) else {}).get("login")
    owner = repository.get("owner")
    owner_login = (owner if isinstance(owner, Mapping) else {}).get("login")
    if not issue_login or issue_login != owner_login:
        raise CurrentDataTransportError("OWNER_ONLY", "fresh current market-data requests are repository-owner only")
    issue_number = issue.get("number")
    if not isinstance(issue_number, int) or issue_number <= 0:
        raise CurrentDataTransportError("INVALID_ISSUE_EVENT", "issue number is invalid")
    return issue_number, parse_request_body(str(issue.get("body") or ""))


def _load_request_wrapper(path: Path) -> tuple[dict[str, object], str]:
    wrapper = _load_json(path)
    if not isinstance(wrapper, Mapping):
        raise CurrentDataTransportError("INVALID_REQUEST_WRAPPER", "normalized request wrapper must be an object")
    schema = wrapper.get("schema_version")
    request = wrapper.get("request")
    if not isinstance(request, Mapping):
        raise CurrentDataTransportError("INVALID_REQUEST_WRAPPER", "normalized request is missing")
    if schema == REQUEST_SCHEMA_V10:
        old_normalized = _normalize_request_v10(request)
        if not old_normalized["required_series"] and not old_normalized["required_domains"]:
            raise CurrentDataTransportError("EMPTY_SEMANTIC_REQUEST", "1.0 request requires series or domains")
        old_sha = _sha256_json(old_normalized)
        if wrapper.get("request_sha256") != old_sha:
            raise CurrentDataTransportError("REQUEST_SHA_MISMATCH", "1.0 normalized request identity mismatch")
        upgraded = normalize_request({**old_normalized, "required_liquidity": []})
        return upgraded, _sha256_json(upgraded)
    if schema != REQUEST_SCHEMA:
        raise CurrentDataTransportError("INVALID_REQUEST_WRAPPER", "normalized request wrapper has unsupported schema")
    normalized = normalize_request(request)
    request_sha256 = _sha256_json(normalized)
    if wrapper.get("request_sha256") != request_sha256:
        raise CurrentDataTransportError("REQUEST_SHA_MISMATCH", "normalized request identity mismatch")
    return normalized, request_sha256


def _bridge_contract() -> dict[str, object]:
    contract = _load_json(ROOT / "bridge-contract.json")
    if not isinstance(contract, dict):
        raise CurrentDataTransportError("BRIDGE_CONTRACT_INVALID", "bridge-contract.json must be an object")
    return contract


def _domain_manifest_path(domain: str) -> Path:
    contract = _bridge_contract()
    paths = contract.get("canonical_paths")
    if not isinstance(paths, Mapping):
        raise CurrentDataTransportError("BRIDGE_CONTRACT_INVALID", "canonical_paths missing")
    key = DOMAIN_PATH_KEYS[domain]
    value = paths.get(key)
    if not isinstance(value, str) or not value:
        raise CurrentDataTransportError("DOMAIN_RESOURCE_UNAVAILABLE", f"canonical path missing for domain {domain}")
    return ROOT / value


def _generated_at_from_manifest(manifest: Mapping[str, object]) -> str | None:
    for key in ("generated_at_utc", "backfill_as_of_utc"):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _aggregate_status(values: Sequence[object]) -> str:
    normalized = [str(value) for value in values if isinstance(value, str) and value != "DISABLED_BY_POLICY"]
    if not normalized:
        return "PASS"
    if any(value in {"FAIL", "UNAVAILABLE", "NOT_AVAILABLE"} for value in normalized):
        return "FAIL"
    if any(value in {"DEGRADED", "HISTORICAL_CONTEXT"} for value in normalized):
        return "DEGRADED"
    return "PASS"


def _declared_domain_status(domain: str, manifest: Mapping[str, object]) -> tuple[str, object]:
    for key in ("status", "bridge_status", "overall_data_plane_status", "integrity_status"):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            return _aggregate_status([value]), value
    collection = manifest.get("collection")
    if isinstance(collection, Mapping) and isinstance(collection.get("status"), str):
        value = collection["status"]
        return _aggregate_status([value]), value
    provider_status = manifest.get("provider_status")
    if isinstance(provider_status, Mapping):
        declared = {str(key): value for key, value in provider_status.items()}
        return _aggregate_status(list(declared.values())), declared
    providers = manifest.get("providers")
    if isinstance(providers, Mapping):
        declared = {
            str(key): value.get("status")
            for key, value in providers.items()
            if isinstance(value, Mapping) and isinstance(value.get("status"), str)
        }
        if declared:
            return _aggregate_status(list(declared.values())), declared
    if domain == "ANALYTICS" and isinstance(manifest.get("analytics_freshness"), str):
        value = manifest["analytics_freshness"]
        return ("PASS" if value == "LIVE_USABLE" else "DEGRADED"), value
    return "PASS", "VALIDATED_BY_REPOSITORY_CONTOUR"


def _series_manifest_path(series_id: str) -> Path:
    try:
        description = describe_capability(series_id)
    except Exception as exc:
        raise CurrentDataTransportError("UNKNOWN_SERIES", f"cannot describe canonical series: {series_id}") from exc
    profile = description.get("profile")
    if not isinstance(profile, Mapping):
        raise CurrentDataTransportError("UNKNOWN_SERIES", f"canonical series profile missing: {series_id}")
    manifest = profile.get("hot_manifest_path")
    if not isinstance(manifest, str) or not manifest:
        raise CurrentDataTransportError("CURRENT_SERIES_UNAVAILABLE", f"series has no current WARM route: {series_id}")
    return ROOT / manifest


def evaluate_persisted_freshness(request: Mapping[str, object], *, now: datetime | None = None) -> dict[str, object]:
    now = (now or _utc_now()).astimezone(timezone.utc)
    max_age = int(request["max_generation_age_seconds"])
    evidence: list[dict[str, object]] = []
    reasons: list[str] = []
    seen_paths: set[str] = set()

    def inspect(logical_id: str, path: Path, *, domain: str | None = None) -> None:
        key = str(path.resolve())
        if key in seen_paths:
            return
        seen_paths.add(key)
        if not path.exists():
            reasons.append(f"MISSING:{logical_id}")
            evidence.append({"logical_id": logical_id, "status": "MISSING"})
            return
        manifest = _load_json(path)
        if not isinstance(manifest, Mapping):
            reasons.append(f"INVALID:{logical_id}")
            evidence.append({"logical_id": logical_id, "status": "INVALID"})
            return
        generated = _generated_at_from_manifest(manifest)
        if generated is None:
            reasons.append(f"NO_GENERATION_TIME:{logical_id}")
            evidence.append({"logical_id": logical_id, "status": "NO_GENERATION_TIME"})
            return
        generated_dt = _parse_utc(generated, f"{logical_id}.generated_at_utc")
        age = max(0, int((now - generated_dt).total_seconds()))
        status = "PASS"
        declared: object = "N/A"
        if domain is not None:
            status, declared = _declared_domain_status(domain, manifest)
            if status in {"FAIL", "DEGRADED"}:
                reasons.append(f"DECLARED_{status}:{logical_id}")
        if age > max_age:
            reasons.append(f"STALE:{logical_id}:{age}")
        evidence.append(
            {
                "logical_id": logical_id,
                "generated_at_utc": generated,
                "age_seconds": age,
                "max_age_seconds": max_age,
                "status": status,
                "declared_status": declared,
                "freshness": "FRESH" if age <= max_age else "STALE",
            }
        )

    for item in request["required_series"]:
        series_id = str(item["series_id"])
        inspect(f"series-manifest:{series_id}", _series_manifest_path(series_id))
    for domain in request["required_domains"]:
        inspect(f"domain:{domain}", _domain_manifest_path(str(domain)), domain=str(domain))

    persisted_fresh = not reasons
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "evaluated_at_utc": _format_utc(now),
        "max_generation_age_seconds": max_age,
        "persisted_fresh_enough": persisted_fresh,
        "generation_mode": "PERSISTED_REUSE" if persisted_fresh else "FRESH_ACQUISITION",
        "acquisition_required": not persisted_fresh,
        "reasons": reasons,
        "evidence": evidence,
    }


def _safe_series_dir(series_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", series_id)


def materialize_requested_series(request: Mapping[str, object], *, cutoff_utc: str, output_root: Path) -> list[dict[str, object]]:
    cutoff = _format_utc(_parse_utc(cutoff_utc, "cutoff_utc"))
    results: list[dict[str, object]] = []
    for item in request["required_series"]:
        series_id = str(item["series_id"])
        bars = int(item["latest_bars"])
        series_dir = output_root / "series" / _safe_series_dir(series_id)
        series_dir.mkdir(parents=True, exist_ok=True)
        try:
            plan, payload, diagnostics, receipt = latest_history(
                series_id,
                bars,
                cutoff_utc=cutoff,
                mode="strict",
                output_format="json",
                current_policy=D6_CURRENT_POLICY,
            )
        except Exception as exc:
            code = getattr(exc, "code", "SERIES_MATERIALIZATION_FAILED")
            raise CurrentDataTransportError(str(code), f"latest materialization failed for {series_id}: {exc}") from exc
        normalized_path = series_dir / "normalized.json"
        normalized_path.write_text(payload, encoding="utf-8")
        _write_json(series_dir / "resolution-plan.json", plan)
        _write_json(series_dir / "diagnostics.json", diagnostics)
        _write_json(series_dir / "receipt.json", receipt)
        _write_json(series_dir / "semantic-receipt.json", receipt["semantic_receipt"])
        results.append(
            {
                "series_id": series_id,
                "latest_bars": bars,
                "status": receipt.get("status"),
                "rows": receipt.get("rows"),
                "plan_sha256": receipt.get("plan_sha256"),
                "semantic_receipt_sha256": receipt.get("semantic_receipt_sha256"),
                "semantic_output_sha256": receipt.get("semantic_output_sha256"),
                "latest_selection": receipt.get("latest_selection"),
                "artifact_member": normalized_path.relative_to(output_root).as_posix(),
            }
        )
    return results


def _file_identity(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    return _sha256_bytes(raw), len(raw)


def build_resource_index(
    request: Mapping[str, object],
    request_sha256: str,
    *,
    output_root: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    now = (now or _utc_now()).astimezone(timezone.utc)
    max_age = int(request["max_generation_age_seconds"])
    domains_dir = output_root / "domains"
    domains_dir.mkdir(parents=True, exist_ok=True)
    domain_rows: list[dict[str, object]] = []
    for domain_value in request["required_domains"]:
        domain = str(domain_value)
        source = _domain_manifest_path(domain)
        raw = source.read_bytes()
        manifest = json.loads(raw)
        generated = _generated_at_from_manifest(manifest)
        if generated is None:
            raise CurrentDataTransportError("DOMAIN_GENERATION_TIME_MISSING", f"domain {domain} has no generation time")
        generated_dt = _parse_utc(generated, f"{domain}.generated_at_utc")
        age = max(0, int((now - generated_dt).total_seconds()))
        status, declared = _declared_domain_status(domain, manifest)
        target = domains_dir / f"{domain.lower()}.json"
        target.write_bytes(raw)
        digest, size = _file_identity(target)
        domain_rows.append(
            {
                "domain_id": domain,
                "resource_logical_id": f"current-domain:{domain.lower()}",
                "status": status,
                "generated_at_utc": generated,
                "sha256": digest,
                "size_bytes": size,
                "availability": "AVAILABLE" if status == "PASS" else "DECLARED_NON_PASS",
                "freshness": "FRESH" if age <= max_age else "STALE",
                "age_seconds": age,
                "declared_status": declared,
                "durability_class": (
                    "RECONSTRUCTIBLE_SERIES" if domain == "SPOT" else "NON_RECONSTRUCTIBLE_OR_SAMPLE_DEPENDENT_CURRENT"
                ),
                "artifact_member": target.relative_to(output_root).as_posix(),
                "legacy_raw_url_is_authority": False,
                "automatic_research_publication": False,
            }
        )

    series_rows: list[dict[str, object]] = []
    for item in request["required_series"]:
        series_id = str(item["series_id"])
        bars = int(item["latest_bars"])
        series_dir = output_root / "series" / _safe_series_dir(series_id)
        normalized = series_dir / "normalized.json"
        receipt_path = series_dir / "receipt.json"
        semantic_path = series_dir / "semantic-receipt.json"
        diagnostics_path = series_dir / "diagnostics.json"
        if not all(path.exists() for path in (normalized, receipt_path, semantic_path, diagnostics_path)):
            raise CurrentDataTransportError("SERIES_ARTIFACT_MISSING", f"series artifact incomplete: {series_id}")
        receipt = _load_json(receipt_path)
        semantic = _load_json(semantic_path)
        diagnostics = _load_json(diagnostics_path)
        digest, size = _file_identity(normalized)
        if not isinstance(receipt, Mapping) or not isinstance(semantic, Mapping) or not isinstance(diagnostics, Mapping):
            raise CurrentDataTransportError("SERIES_ARTIFACT_INVALID", f"series artifact invalid: {series_id}")
        series_rows.append(
            {
                "domain_id": str(series_id).split(".", 1)[0].upper(),
                "resource_logical_id": f"latest-series:{series_id}:{bars}",
                "series_id": series_id,
                "latest_bars": bars,
                "status": receipt.get("status"),
                "generated_at_utc": _load_json(ROOT / "data" / "manifest.json").get("generated_at_utc"),
                "sha256": digest,
                "size_bytes": size,
                "availability": "AVAILABLE" if receipt.get("status") == "PASS" else "UNAVAILABLE",
                "freshness": "VALIDATED_CURRENT_GENERATION",
                "semantic_receipt_sha256": receipt.get("semantic_receipt_sha256"),
                "semantic_output_sha256": semantic.get("output_sha256"),
                "resolution_plan_sha256": semantic.get("resolution_plan_sha256"),
                "finality": semantic.get("finality"),
                "rows": diagnostics.get("rows"),
                "expected_rows": diagnostics.get("expected_rows"),
                "gap_count": diagnostics.get("gap_count"),
                "duplicates": diagnostics.get("duplicates"),
                "durability_class": "RECONSTRUCTIBLE_SERIES",
                "artifact_member": normalized.relative_to(output_root).as_posix(),
                "legacy_raw_url_is_authority": False,
                "automatic_research_publication": False,
            }
        )
    series_rows.sort(key=lambda row: str(row["series_id"]))
    domain_rows.sort(key=lambda row: str(row["domain_id"]))
    index = {
        "schema_version": RESOURCE_INDEX_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "request_sha256": request_sha256,
        "ephemeral_resource_discovery": "GENERATION_RESOURCE_INDEX",
        "follow_legacy_raw_url_for_ephemeral_data": False,
        "domains": domain_rows,
        "series": series_rows,
        "liquidity_resources": [],
    }
    _write_json(output_root / "resource-index.json", index)
    return index


def validate_generation(
    request: Mapping[str, object],
    request_sha256: str,
    resource_index: Mapping[str, object],
    *,
    output_root: Path,
) -> dict[str, object]:
    if resource_index.get("request_sha256") != request_sha256:
        raise CurrentDataTransportError("RESOURCE_INDEX_REQUEST_MISMATCH", "resource index is bound to a different request")
    if resource_index.get("follow_legacy_raw_url_for_ephemeral_data") is not False:
        raise CurrentDataTransportError("LEGACY_RAW_URL_AUTHORITY_FORBIDDEN", "ephemeral resource index must reject raw_url authority")
    domain_rows = resource_index.get("domains")
    series_rows = resource_index.get("series")
    if not isinstance(domain_rows, list) or not isinstance(series_rows, list):
        raise CurrentDataTransportError("RESOURCE_INDEX_INVALID", "resource index rows are missing")
    domains = {row.get("domain_id"): row for row in domain_rows if isinstance(row, Mapping)}
    for required in request["required_domains"]:
        row = domains.get(required)
        if row is None:
            raise CurrentDataTransportError("REQUIRED_DOMAIN_MISSING", f"required domain missing: {required}")
        if row.get("status") == "DEGRADED":
            raise CurrentDataTransportError("REQUIRED_CAPABILITY_DEGRADED", f"required domain degraded: {required}")
        if row.get("status") != "PASS" or row.get("freshness") != "FRESH":
            raise CurrentDataTransportError("REQUIRED_CAPABILITY_UNAVAILABLE", f"required domain unavailable/stale: {required}")
    series = {row.get("series_id"): row for row in series_rows if isinstance(row, Mapping)}
    for required in request["required_series"]:
        series_id = required["series_id"]
        bars = required["latest_bars"]
        row = series.get(series_id)
        if row is None:
            raise CurrentDataTransportError("REQUIRED_SERIES_MISSING", f"required series missing: {series_id}")
        if (
            row.get("status") != "PASS"
            or row.get("availability") != "AVAILABLE"
            or row.get("finality") != "FINALIZED"
            or row.get("rows") != bars
            or row.get("expected_rows") != bars
            or row.get("gap_count") != 0
            or row.get("duplicates") != 0
        ):
            raise CurrentDataTransportError("REQUIRED_SERIES_INVALID", f"required latest series failed strict validation: {series_id}")
        if not _HEX64.fullmatch(str(row.get("semantic_receipt_sha256") or "")):
            raise CurrentDataTransportError("SEMANTIC_RECEIPT_INVALID", f"semantic receipt identity invalid: {series_id}")
    summary = {
        "schema_version": VALIDATION_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "status": "PASS",
        "request_sha256": request_sha256,
        "repository_existing_validation_contour": [
            "tools/validation/validate.py",
            "tools/validation/validate_v4.py",
            "tools/validation/validate_history.py",
            "tools/validation/consumer_proof.py",
            "tools/validation/validate_repository.py",
            "tools/validation/validate_d9_contracts.py",
            "tools/capability_index.py validate",
        ],
        "normal_test_network_required": False,
        "existing_history_resolver_reused": True,
        "existing_history_reader_reused": True,
        "existing_collector_reused": True,
        "direct_provider_call_by_agent": False,
        "on_demand_ephemeral_data_automatically_durable_research_evidence": False,
        "automatic_research_publication_from_ephemeral_only_evidence": False,
    }
    _write_json(output_root / "validation-summary.json", summary)
    return summary


LIQUIDITY_ROW_FIELDS = {
    "semantic_resource_id","provider_id","instrument_id","book_kind","representation",
    "resource_family_sha256","resource_sha256","resource_qualification_request_sha256",
    "current_semantic_request_sha256","qualification_receipt_sha256","request_satisfaction_status",
    "request_satisfaction_sha256","request_satisfied","observation_id","observation_sha256",
    "acquisition_mode","durability_class","cross_run_cache_eligible","automatic_promotion",
    "automatic_history_append","automatic_research_publication","resource_artifact_member",
    "qualification_receipt_member","request_binding_member","s3_execution_receipt_sha256",
    "s3_execution_receipt_member",
}
LIQUIDITY_ACQUISITION_MODES = {
    "S3_NETWORK_ACQUIRED","SAME_EXECUTION_REUSE","LEGACY_PERSISTED_REQUALIFICATION"
}

def _safe_artifact_member(output_root: Path, member: object, *, allow_none: bool = False) -> Path | None:
    if member is None and allow_none:
        return None
    if not isinstance(member,str) or not member:
        raise CurrentDataTransportError("LIQUIDITY_ARTIFACT_MEMBER_INVALID","exact liquidity artifact member missing")
    rel=Path(member)
    if rel.is_absolute() or ".." in rel.parts:
        raise CurrentDataTransportError("LIQUIDITY_ARTIFACT_MEMBER_INVALID",f"unsafe exact liquidity member: {member}")
    root=output_root.resolve()
    resolved=(output_root/rel).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CurrentDataTransportError("LIQUIDITY_ARTIFACT_MEMBER_INVALID",f"exact liquidity member escapes artifact root: {member}") from exc
    return resolved

def _validate_self_hashed(value: Mapping[str,object], hash_field: str, code: str) -> dict[str,object]:
    material=dict(value)
    supplied=material.pop(hash_field,None)
    if supplied != sha256_canonical_json(material):
        raise CurrentDataTransportError(code,f"{hash_field} mismatch")
    return dict(value)

def validate_liquidity_resource_rows(
    request: Mapping[str,object],
    resource_index: Mapping[str,object],
    *,
    output_root: Path,
) -> list[dict[str,object]]:
    rows=resource_index.get("liquidity_resources")
    if rows is None and resource_index.get("schema_version")==RESOURCE_INDEX_SCHEMA_V10:
        rows=[]
    if not isinstance(rows,list):
        raise CurrentDataTransportError("LIQUIDITY_RESOURCE_INDEX_INVALID","liquidity_resources must be an array")
    expected={sha256_canonical_json(item) for item in request.get("required_liquidity",[])}
    if len(rows)!=len(expected):
        raise CurrentDataTransportError("LIQUIDITY_RESOURCE_BINDING_COUNT_MISMATCH","one liquidity row per current exact requirement is required")
    seen=set()
    for raw_row in rows:
        if not isinstance(raw_row,Mapping) or set(raw_row)!=LIQUIDITY_ROW_FIELDS:
            raise CurrentDataTransportError("LIQUIDITY_RESOURCE_ROW_FIELDS_INVALID","exact liquidity row fields are not canonical")
        row=dict(raw_row)
        current_sha=row["current_semantic_request_sha256"]
        if current_sha not in expected or current_sha in seen:
            raise CurrentDataTransportError("LIQUIDITY_CURRENT_REQUEST_BINDING_INVALID","exact liquidity current request digest mismatch")
        seen.add(current_sha)
        if row["acquisition_mode"] not in LIQUIDITY_ACQUISITION_MODES:
            raise CurrentDataTransportError("LIQUIDITY_ACQUISITION_MODE_INVALID","unknown exact liquidity acquisition mode")
        if row["durability_class"]!="EPHEMERAL_ONLY" or row["cross_run_cache_eligible"] is not False:
            raise CurrentDataTransportError("LIQUIDITY_DURABILITY_INVALID","exact S3 liquidity must remain EPHEMERAL_ONLY")
        if any(row[field] is not False for field in ("automatic_promotion","automatic_history_append","automatic_research_publication")):
            raise CurrentDataTransportError("LIQUIDITY_DURABILITY_INVALID","exact S3 liquidity automatic durability is forbidden")
        bind_path=_safe_artifact_member(output_root,row["request_binding_member"])
        binding=_load_json(bind_path)
        if not isinstance(binding,Mapping):
            raise CurrentDataTransportError("LIQUIDITY_REQUEST_BINDING_INVALID","request binding must be object")
        _validate_self_hashed(binding,"request_binding_sha256","LIQUIDITY_REQUEST_BINDING_SHA_MISMATCH")
        if binding.get("current_semantic_request_sha256")!=current_sha or binding.get("resource_sha256")!=row["resource_sha256"]:
            raise CurrentDataTransportError("LIQUIDITY_REQUEST_BINDING_MISMATCH","request binding differs from index")
        receipt_sha=row["s3_execution_receipt_sha256"]; receipt_member=row["s3_execution_receipt_member"]
        if row["acquisition_mode"]=="S3_NETWORK_ACQUIRED":
            if not _HEX64.fullmatch(str(receipt_sha or "")) or not isinstance(receipt_member,str):
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_REQUIRED","network-acquired row requires S3 receipt")
            receipt_path=_safe_artifact_member(output_root,receipt_member)
            if receipt_path.parent.name != receipt_sha:
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_MEMBER_MISMATCH","receipt digest path component mismatch")
            receipt=_load_json(receipt_path)
            if not isinstance(receipt,Mapping) or receipt.get("execution_receipt_sha256")!=receipt_sha:
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_SHA_MISMATCH","receipt/index digest mismatch")
        else:
            if receipt_sha is not None or receipt_member is not None:
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_FORBIDDEN_ON_REUSE","reuse/requalification row cannot attach S3 receipt")
        if row["resource_sha256"] is None:
            if row["request_satisfied"] is not False or row["request_satisfaction_status"]=="SATISFIED":
                raise CurrentDataTransportError("LIQUIDITY_UNSATISFIED_RESOURCE_INVALID","missing resource cannot satisfy request")
            continue
        resource_path=_safe_artifact_member(output_root,row["resource_artifact_member"])
        resource=_load_json(resource_path)
        try:
            canonical=validate_qualified_liquidity_resource(resource)
        except Exception as exc:
            raise CurrentDataTransportError("LIQUIDITY_QUALIFIED_RESOURCE_INVALID",str(exc)) from exc
        if canonical["resource_sha256"]!=row["resource_sha256"]:
            raise CurrentDataTransportError("LIQUIDITY_RESOURCE_SHA_MISMATCH","resource/index digest mismatch")
        if canonical["observation_id"]!=row["observation_id"] or canonical["observation_sha256"]!=row["observation_sha256"]:
            raise CurrentDataTransportError("LIQUIDITY_OBSERVATION_BINDING_MISMATCH","resource/index observation mismatch")
        qpath=_safe_artifact_member(output_root,row["qualification_receipt_member"])
        qualification=_load_json(qpath)
        if not isinstance(qualification,Mapping):
            raise CurrentDataTransportError("LIQUIDITY_QUALIFICATION_RECEIPT_INVALID","qualification receipt must be object")
        _validate_self_hashed(qualification,"qualification_receipt_sha256","LIQUIDITY_QUALIFICATION_RECEIPT_SHA_MISMATCH")
        if qualification.get("resource_sha256")!=row["resource_sha256"] or qualification.get("qualification_receipt_sha256")!=row["qualification_receipt_sha256"]:
            raise CurrentDataTransportError("LIQUIDITY_QUALIFICATION_RECEIPT_BINDING_MISMATCH","qualification receipt differs from index")
        if row["acquisition_mode"]=="S3_NETWORK_ACQUIRED":
            receipt=_load_json(_safe_artifact_member(output_root,row["s3_execution_receipt_member"]))
            plan=qualification.get("s2_provider_plan")
            s1_plan=qualification.get("s1_planner_result")
            if not isinstance(plan,Mapping) or not isinstance(s1_plan,Mapping):
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_PLAN_EVIDENCE_MISSING","network qualification receipt must retain exact S1/S2 plan evidence")
            try:
                from liquidity_s3_executor import validate_execution_receipt
                validate_execution_receipt(receipt,provider_plan=plan,s1_planner_result=s1_plan,qualified_resource=canonical)
            except Exception as exc:
                raise CurrentDataTransportError("S3_EXECUTION_RECEIPT_INVALID",str(exc)) from exc
    return [dict(row) for row in rows]


def _git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, capture_output=True, text=True)
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, check=False, capture_output=True, text=True)
    if head.returncode or tree.returncode:
        raise CurrentDataTransportError("CONTROL_PLANE_GIT_INVALID", "cannot capture git control-plane identity")
    head_sha = head.stdout.strip().lower()
    tree_sha = tree.stdout.strip().lower()
    if not _HEX40.fullmatch(head_sha) or not _HEX40.fullmatch(tree_sha):
        raise CurrentDataTransportError("CONTROL_PLANE_GIT_INVALID", "invalid git control-plane identity")
    return head_sha, tree_sha


def build_generation_receipts(
    request: Mapping[str, object],
    request_sha256: str,
    resource_index: Mapping[str, object],
    validation_summary: Mapping[str, object],
    *,
    output_root: Path,
    control_plane_head: str,
    control_plane_tree: str,
    head_after: str,
    generation_mode: str,
    known_at_utc: str,
    issue_number: str = "N/A",
    run_id: str = "N/A",
    run_url: str = "N/A",
    artifact_name: str = "N/A",
) -> tuple[dict[str, object], dict[str, object]]:
    if validation_summary.get("status") != "PASS":
        raise CurrentDataTransportError("VALIDATION_NOT_PASS", "generation cannot be exposed before validation PASS")
    for value,label in ((control_plane_head,"CONTROL_PLANE_HEAD"),(control_plane_tree,"CONTROL_PLANE_TREE"),(head_after,"HEAD_AFTER")):
        if not _HEX40.fullmatch(value):
            raise CurrentDataTransportError("CONTROL_PLANE_GIT_INVALID",f"{label} must be an exact 40-char git SHA")
    if head_after != control_plane_head:
        raise CurrentDataTransportError("REMOTE_MUTATION_BOUNDARY_VIOLATION","control-plane HEAD changed during on-demand generation")
    if generation_mode not in {"PERSISTED_REUSE","FRESH_ACQUISITION"}:
        raise CurrentDataTransportError("INVALID_GENERATION_MODE",f"invalid input generation mode: {generation_mode}")
    known_at=_format_utc(_parse_utc(known_at_utc,"known_at_utc"))
    liquidity_rows=validate_liquidity_resource_rows(request,resource_index,output_root=output_root)
    s3_used=any(row["acquisition_mode"]=="S3_NETWORK_ACQUIRED" and row["s3_execution_receipt_sha256"] is not None for row in liquidity_rows)
    effective_mode=(
        "FRESH_ACQUISITION_PLUS_SELECTIVE_S3" if generation_mode=="FRESH_ACQUISITION" and s3_used
        else "SELECTIVE_S3_ACQUISITION" if s3_used
        else generation_mode
    )
    ordinary_required=bool(request.get("required_series") or request.get("required_domains"))
    ordinary_generation=None
    if ordinary_required:
        data_path=ROOT/"data"/"manifest.json"
        data_manifest=_load_json(data_path)
        if not isinstance(data_manifest,Mapping):
            raise CurrentDataTransportError("GENERATION_MANIFEST_INVALID","data manifest is invalid")
        generated_at=data_manifest.get("generated_at_utc"); collector_version=data_manifest.get("collector_version")
        if not isinstance(generated_at,str) or not isinstance(collector_version,str):
            raise CurrentDataTransportError("GENERATION_MANIFEST_INVALID","collector generation identity missing")
        digest,_size=_file_identity(data_path)
        ordinary_generation={
            "data_manifest_generated_at_utc":generated_at,
            "collector_version":collector_version,
            "data_manifest_sha256":digest,
        }
    domain_identities=[{"domain_id":row["domain_id"],"resource_logical_id":row["resource_logical_id"],"sha256":row["sha256"]}
                       for row in resource_index.get("domains",[]) if isinstance(row,Mapping)]
    series_identities=[{"series_id":row["series_id"],"latest_bars":row["latest_bars"],"sha256":row["sha256"],
                       "semantic_receipt_sha256":row["semantic_receipt_sha256"],"semantic_output_sha256":row["semantic_output_sha256"]}
                      for row in resource_index.get("series",[]) if isinstance(row,Mapping)]
    liquidity_identities=[{
        "semantic_resource_id":row["semantic_resource_id"],
        "resource_family_sha256":row["resource_family_sha256"],
        "resource_sha256":row["resource_sha256"],
        "resource_qualification_request_sha256":row["resource_qualification_request_sha256"],
        "current_semantic_request_sha256":row["current_semantic_request_sha256"],
        "qualification_receipt_sha256":row["qualification_receipt_sha256"],
        "request_satisfaction_sha256":row["request_satisfaction_sha256"],
    } for row in liquidity_rows]
    domain_identities.sort(key=lambda row:str(row["domain_id"]))
    series_identities.sort(key=lambda row:str(row["series_id"]))
    liquidity_identities.sort(key=lambda row:(str(row["semantic_resource_id"]),str(row["current_semantic_request_sha256"])))
    requested_liquidity=[dict(item) for item in request.get("required_liquidity",[])]
    identity_basis={
        "contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,"control_plane_head":control_plane_head,
        "requested_semantic_capabilities":{
            "required_domains":list(request["required_domains"]),
            "required_series":list(request["required_series"]),
            "required_liquidity":requested_liquidity,
        },
        "ordinary_generation":ordinary_generation,
        "validated_domain_resources":domain_identities,
        "validated_series_resources":series_identities,
        "validated_exact_liquidity_current_bindings":liquidity_identities,
    }
    generation_id=_sha256_json(identity_basis)
    resource_index_sha256,_=_file_identity(output_root/"resource-index.json")
    validation_sha256,_=_file_identity(output_root/"validation-summary.json")
    semantic_receipts=[row["semantic_receipt_sha256"] for row in series_identities]
    core={
        "schema_version":GENERATION_SCHEMA,"contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,
        "market_data_semantic_authority":"ETH_MACRO_DATA_BRIDGE","execution_plane_is_market_data_authority":False,
        "github_actions_is_market_data_authority":False,"actions_artifact_is_market_data_authority":False,
        "github_issue_is_market_data_authority":False,"control_plane_head":control_plane_head,
        "control_plane_tree":control_plane_tree,"generation_mode":effective_mode,"known_at_utc":known_at,
        "ordinary_generation":ordinary_generation,"request_sha256":request_sha256,"generation_id":generation_id,
        "resource_index_sha256":resource_index_sha256,"validation_summary_sha256":validation_sha256,
        "semantic_receipts":semantic_receipts,"execution_transport":EXECUTION_TRANSPORT,
        "generation_id_excludes":[
            "github_run_id","issue_number","artifact_url","runner_path","hostname","known_at_utc",
            "s3_execution_receipt_sha256","s3_execution_id","s3_execution_nonce",
            "s3_endpoint_binding_sha256","s3_physical_action_sha256","s3_execution_timestamps",
            "s3_execution_receipt_member",
        ],
        "on_demand_current_data_can_be_used_for_live_analysis":True,
        "on_demand_ephemeral_data_automatically_durable_research_evidence":False,
        "automatic_research_publication_from_ephemeral_only_evidence":False,
    }
    generation_manifest_sha256=_sha256_json(core)
    generation={**core,"generation_manifest_sha256":generation_manifest_sha256}
    _write_json(output_root/"current-generation.json",generation)
    exact_results=[{
        "current_semantic_request_sha256":row["current_semantic_request_sha256"],
        "semantic_resource_id":row["semantic_resource_id"],
        "request_satisfaction_status":row["request_satisfaction_status"],
        "resource_sha256":row["resource_sha256"],
        "acquisition_mode":row["acquisition_mode"],
        "s3_execution_receipt_sha256":row["s3_execution_receipt_sha256"],
    } for row in liquidity_rows]
    transport={
        "schema_version":TRANSPORT_RECEIPT_SCHEMA,"contract_id":CONTRACT_ID,"contract_version":CONTRACT_VERSION,
        "authority":"TRANSPORT_ONLY","execution_transport":EXECUTION_TRANSPORT,
        "future_execution_transport":FUTURE_EXECUTION_TRANSPORT,"future_transport_swap_requires_domain_rewrite":False,
        "request_sha256":request_sha256,"generation_id":generation_id,
        "generation_manifest_sha256":generation_manifest_sha256,"control_plane_head":control_plane_head,
        "control_plane_tree":control_plane_tree,"head_after":head_after,"head_before_equals_head_after":True,
        "remote_repository_mutation":False,"git_add":False,"git_commit":False,"git_push":False,
        "release_publication":False,"d8_state_mutation":False,"d9_activation":False,
        "exact_liquidity_results":exact_results,"issue_number":issue_number,"run_id":run_id,
        "run_url":run_url,"artifact_name":artifact_name,
    }
    _write_json(output_root/"transport-receipt.json",transport)
    return generation,transport

def _command_build_request(args: argparse.Namespace) -> int:
    liquidity = []
    for raw in args.liquidity_json:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CurrentDataTransportError("INVALID_LIQUIDITY_REQUEST", "--liquidity-json must contain one JSON object") from exc
        liquidity.append(value)
    payload = {
        "request_type": "FRESH_CURRENT",
        "required_series": list(args.series),
        "required_domains": list(args.domain),
        "required_liquidity": liquidity,
        "max_generation_age_seconds": args.max_generation_age_seconds,
        "current_policy": args.current_policy,
    }
    normalized = normalize_request(payload)
    _write_json(Path(args.output), normalized)
    print(f"CURRENT_DATA_REQUEST_BUILD=PASS output={args.output} request_sha256={_sha256_json(normalized)}")
    return 0


def _command_parse(args: argparse.Namespace) -> int:
    if args.event:
        event = _load_json(Path(args.event))
        if not isinstance(event, Mapping):
            raise CurrentDataTransportError("INVALID_ISSUE_EVENT", "GitHub event must be an object")
        issue_number, request = parse_issue_event(event)
    else:
        raw = Path(args.request_file).read_text(encoding="utf-8")
        request = parse_request_body(raw)
        issue_number = 0
    wrapper = request_wrapper(request)
    _write_json(Path(args.output), wrapper)
    github_output = Path(args.github_output) if args.github_output else None
    _append_output(github_output, "issue_number", issue_number or "N/A")
    _append_output(github_output, "request_sha256", wrapper["request_sha256"])
    _append_output(github_output, "required_series_count", len(request["required_series"]))
    _append_output(github_output, "required_domains", ",".join(request["required_domains"]) or "NONE")
    _append_output(github_output, "required_liquidity_count", len(request["required_liquidity"]))
    print(f"CURRENT_DATA_REQUEST=PASS request_sha256={wrapper['request_sha256']}")
    return 0


def _command_freshness(args: argparse.Namespace) -> int:
    request, _request_sha = _load_request_wrapper(Path(args.request))
    now = _parse_utc(args.now_utc, "now_utc") if args.now_utc else _utc_now()
    result = evaluate_persisted_freshness(request, now=now)
    _write_json(Path(args.output), result)
    github_output = Path(args.github_output) if args.github_output else None
    _append_output(github_output, "generation_mode", result["generation_mode"])
    _append_output(github_output, "acquisition_required", str(result["acquisition_required"]).lower())
    _append_output(github_output, "persisted_fresh_enough", str(result["persisted_fresh_enough"]).lower())
    print(f"CURRENT_DATA_FRESHNESS={'PASS' if result['persisted_fresh_enough'] else 'STALE'} mode={result['generation_mode']}")
    return 0


def _command_materialize(args: argparse.Namespace) -> int:
    request, _request_sha = _load_request_wrapper(Path(args.request))
    output_root = Path(args.output_root)
    results = materialize_requested_series(request, cutoff_utc=args.cutoff, output_root=output_root)
    _write_json(output_root / "series-materialization.json", {"status": "PASS", "series": results})
    print(f"CURRENT_DATA_SERIES_MATERIALIZATION=PASS series={len(results)}")
    return 0


def _command_index(args: argparse.Namespace) -> int:
    request, request_sha = _load_request_wrapper(Path(args.request))
    output_root = Path(args.output_root)
    now = _parse_utc(args.now_utc, "now_utc") if args.now_utc else _utc_now()
    index = build_resource_index(request, request_sha, output_root=output_root, now=now)
    print(f"CURRENT_DATA_RESOURCE_INDEX=PASS domains={len(index['domains'])} series={len(index['series'])}")
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    request, request_sha = _load_request_wrapper(Path(args.request))
    output_root = Path(args.output_root)
    index = _load_json(output_root / "resource-index.json")
    if not isinstance(index, Mapping):
        raise CurrentDataTransportError("RESOURCE_INDEX_INVALID", "resource index must be an object")
    validate_generation(request, request_sha, index, output_root=output_root)
    print("CURRENT_DATA_GENERATION_VALIDATION=PASS")
    return 0


def _command_receipt(args: argparse.Namespace) -> int:
    request, request_sha = _load_request_wrapper(Path(args.request))
    output_root = Path(args.output_root)
    index = _load_json(output_root / "resource-index.json")
    validation = _load_json(output_root / "validation-summary.json")
    if not isinstance(index, Mapping) or not isinstance(validation, Mapping):
        raise CurrentDataTransportError("GENERATION_ARTIFACT_INVALID", "resource/validation artifacts must be objects")
    generation, _transport = build_generation_receipts(
        request,
        request_sha,
        index,
        validation,
        output_root=output_root,
        control_plane_head=args.control_plane_head,
        control_plane_tree=args.control_plane_tree,
        head_after=args.head_after,
        generation_mode=args.generation_mode,
        known_at_utc=args.known_at_utc,
        issue_number=args.issue_number,
        run_id=args.run_id,
        run_url=args.run_url,
        artifact_name=args.artifact_name,
    )
    github_output = Path(args.github_output) if args.github_output else None
    _append_output(github_output, "generation_id", generation["generation_id"])
    ordinary = generation.get("ordinary_generation")
    generated = ordinary.get("data_manifest_generated_at_utc") if isinstance(ordinary, Mapping) else "N/A"
    _append_output(github_output, "generated_at_utc", generated)
    _append_output(github_output, "known_at_utc", generation["known_at_utc"])
    _append_output(github_output, "generation_manifest_sha256", generation["generation_manifest_sha256"])
    print(f"CURRENT_DATA_GENERATION_RECEIPT=PASS generation_id={generation['generation_id']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thin orchestration for canonical fresh/current Data Bridge agent transport")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-request")
    build.add_argument("--series", action="append", default=[])
    build.add_argument("--domain", action="append", default=[])
    build.add_argument("--liquidity-json", action="append", default=[])
    build.add_argument("--max-generation-age-seconds", type=int, default=DEFAULT_MAX_GENERATION_AGE_SECONDS)
    build.add_argument("--current-policy", default=D6_CURRENT_POLICY)
    build.add_argument("--output", required=True)
    build.set_defaults(func=_command_build_request)

    parse = sub.add_parser("parse-request")
    source = parse.add_mutually_exclusive_group(required=True)
    source.add_argument("--event")
    source.add_argument("--request-file")
    parse.add_argument("--output", required=True)
    parse.add_argument("--github-output")
    parse.set_defaults(func=_command_parse)

    freshness = sub.add_parser("evaluate-freshness")
    freshness.add_argument("--request", required=True)
    freshness.add_argument("--output", required=True)
    freshness.add_argument("--now-utc")
    freshness.add_argument("--github-output")
    freshness.set_defaults(func=_command_freshness)

    materialize = sub.add_parser("materialize-series")
    materialize.add_argument("--request", required=True)
    materialize.add_argument("--cutoff", required=True)
    materialize.add_argument("--output-root", required=True)
    materialize.set_defaults(func=_command_materialize)

    index = sub.add_parser("build-resource-index")
    index.add_argument("--request", required=True)
    index.add_argument("--output-root", required=True)
    index.add_argument("--now-utc")
    index.set_defaults(func=_command_index)

    validate = sub.add_parser("validate-generation")
    validate.add_argument("--request", required=True)
    validate.add_argument("--output-root", required=True)
    validate.set_defaults(func=_command_validate)

    receipt = sub.add_parser("build-receipt")
    receipt.add_argument("--request", required=True)
    receipt.add_argument("--output-root", required=True)
    receipt.add_argument("--control-plane-head", required=True)
    receipt.add_argument("--control-plane-tree", required=True)
    receipt.add_argument("--head-after", required=True)
    receipt.add_argument("--generation-mode", required=True)
    receipt.add_argument("--known-at-utc", required=True)
    receipt.add_argument("--issue-number", default="N/A")
    receipt.add_argument("--run-id", default="N/A")
    receipt.add_argument("--run-url", default="N/A")
    receipt.add_argument("--artifact-name", default="N/A")
    receipt.add_argument("--github-output")
    receipt.set_defaults(func=_command_receipt)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CurrentDataTransportError as exc:
        print(f"CURRENT_DATA_TRANSPORT={exc.code} error={exc}", file=sys.stderr)
        raise SystemExit(2)
