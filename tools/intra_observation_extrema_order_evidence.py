from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

PARENT_CONTRACT_ID = "ETH-MARKET-DATA-INTRA-OBSERVATION-EXTREMA-ORDER-EVIDENCE-V1"
COMPANION_CONTRACT_ID = "ETH-MARKET-DATA-INTRA-OBSERVATION-EXTREMA-ORDER-EVIDENCE-FINGERPRINT-CANONICALIZATION-V1"
CAPABILITY_ID = "market-data.intra-observation-extrema-order-evidence"
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

LOWER_TF_RESULTS = {
    "HIGH_BEFORE_LOW",
    "LOW_BEFORE_HIGH",
    "UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE",
}
FLAT_RESULT = "ORDER_NOT_MATERIALLY_DISTINCT"
LOWER_TF_BINDING_FIELDS = (
    "child_series_id",
    "child_interval",
    "supporting_child_observation_refs",
    "child_window_fingerprint",
    "earliest_parent_high_occurrence",
    "earliest_parent_low_occurrence",
)
LOWER_TF_PROVENANCE_FIELDS = (
    "parent_semantic_receipt_sha256",
    "parent_resolution_plan_sha256",
    "parent_semantic_output_sha256",
    "child_semantic_receipt_sha256",
    "child_resolution_plan_sha256",
    "child_semantic_output_sha256",
    "parent_observation_fingerprint",
    "child_window_fingerprint",
)
FLAT_PROVENANCE_FIELDS = (
    "parent_semantic_receipt_sha256",
    "parent_resolution_plan_sha256",
    "parent_semantic_output_sha256",
    "parent_observation_fingerprint",
)
EVIDENCE_BASE_FIELDS = (
    "contract_id",
    "capability_id",
    "provider_id",
    "instrument_id",
    "parent_series_id",
    "parent_observation_ref",
    "parent_high",
    "parent_low",
)
PIT_FIELDS = ("event_effective_at", "evidence_available_at_utc", "known_at_utc")
EVENT_LEVEL_MARKERS = ("source_event_refs", "event_ordering_rule")


class FingerprintCanonicalizationError(ValueError):
    def __init__(self, reason_code: str, detail: str = "") -> None:
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)
        self.reason_code = reason_code
        self.detail = detail


def _reject_nonfinite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "non-finite number")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "object key must be text")
            _reject_nonfinite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_nonfinite(child)


def canonical_json_bytes(payload: Any) -> bytes:
    """Return contract-authoritative canonical JSON bytes for a JSON-safe payload."""
    _reject_nonfinite(payload)
    try:
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", str(exc)) from exc
    return text.encode("utf-8")


def strict_json_loads(text: str) -> Any:
    """Parse JSON while rejecting duplicate object keys and non-finite constants."""
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", f"duplicate key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", f"non-finite constant: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    except FingerprintCanonicalizationError:
        raise
    except json.JSONDecodeError as exc:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", str(exc)) from exc


def _fingerprint(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _require_mapping(carrier: Any) -> Mapping[str, Any]:
    if not isinstance(carrier, Mapping):
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "carrier must be an object")
    return carrier


def _require_text(carrier: Mapping[str, Any], field: str) -> str:
    value = carrier.get(field)
    if not isinstance(value, str) or not value:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", f"missing/invalid {field}")
    return value


def _require_provenance(carrier: Mapping[str, Any], fields: Sequence[str]) -> dict[str, str]:
    provenance = carrier.get("provenance")
    if not isinstance(provenance, Mapping):
        raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", "provenance object required")
    result: dict[str, str] = {}
    for field in fields:
        value = provenance.get(field)
        if not isinstance(value, str) or not value:
            raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", field)
        if field.endswith("_sha256") and HEX_SHA256_RE.fullmatch(value) is None:
            raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", field)
        if field.endswith("_fingerprint") and FINGERPRINT_RE.fullmatch(value) is None:
            raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", field)
        result[field] = value
    return result


def _proof_profile(carrier: Mapping[str, Any]) -> str:
    if any(marker in carrier for marker in EVENT_LEVEL_MARKERS):
        raise FingerprintCanonicalizationError(
            "UNSUPPORTED_PROOF_PROFILE",
            "EVENT_LEVEL_FINGERPRINT_PROFILE_NOT_AUTHORIZED",
        )
    result = _require_text(carrier, "derived_result")
    if result == FLAT_RESULT:
        if _require_text(carrier, "parent_high") != _require_text(carrier, "parent_low"):
            raise FingerprintCanonicalizationError("FLAT_RESULT_INVALID_FOR_NON_FLAT_PARENT")
        return "FLAT_PARENT_ONLY"
    if result not in LOWER_TF_RESULTS:
        raise FingerprintCanonicalizationError("UNSUPPORTED_PROOF_PROFILE", result)
    missing = [field for field in LOWER_TF_BINDING_FIELDS if field not in carrier]
    if missing:
        raise FingerprintCanonicalizationError("UNSUPPORTED_PROOF_PROFILE", f"lower-TF fields missing: {missing}")
    return "LOWER_TIMEFRAME"


def _validate_common_identity(carrier: Mapping[str, Any]) -> None:
    if _require_text(carrier, "contract_id") != PARENT_CONTRACT_ID:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "contract_id")
    if _require_text(carrier, "capability_id") != CAPABILITY_ID:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "capability_id")
    for field in EVIDENCE_BASE_FIELDS[2:]:
        _require_text(carrier, field)
    if _require_text(carrier, "finality") != "FINALIZED":
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "finality")
    for field in ("value_semantics", "unit", "ordering_evidence_source", "proof_granularity"):
        _require_text(carrier, field)
    for field in ("parent_observation_fingerprint",):
        value = carrier.get("provenance", {}).get(field) if isinstance(carrier.get("provenance"), Mapping) else None
        if not isinstance(value, str) or FINGERPRINT_RE.fullmatch(value) is None:
            raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", field)


def build_evidence_fingerprint_payload(carrier: Mapping[str, Any]) -> dict[str, Any]:
    carrier = _require_mapping(carrier)
    _validate_common_identity(carrier)
    profile = _proof_profile(carrier)
    payload: dict[str, Any] = {field: _require_text(carrier, field) for field in EVIDENCE_BASE_FIELDS}
    if profile == "LOWER_TIMEFRAME":
        refs = carrier.get("supporting_child_observation_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
            raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "supporting_child_observation_refs")
        child_bindings = {field: carrier[field] for field in LOWER_TF_BINDING_FIELDS}
        child_bindings["supporting_child_observation_refs"] = list(refs)
        provenance = _require_provenance(carrier, LOWER_TF_PROVENANCE_FIELDS)
        if provenance["child_window_fingerprint"] != _require_text(carrier, "child_window_fingerprint"):
            raise FingerprintCanonicalizationError("PROVENANCE_IDENTITY_INCOMPLETE", "child_window_fingerprint mismatch")
    else:
        child_bindings = {}
        provenance = _require_provenance(carrier, FLAT_PROVENANCE_FIELDS)
    payload["child_or_event_evidence_bindings"] = child_bindings
    payload["derived_result"] = _require_text(carrier, "derived_result")
    payload["provenance_receipt_identity"] = provenance
    return payload


def compute_evidence_fingerprint(carrier: Mapping[str, Any]) -> str:
    return _fingerprint(build_evidence_fingerprint_payload(carrier))


def build_carrier_fingerprint_payload(carrier: Mapping[str, Any]) -> dict[str, Any]:
    carrier = _require_mapping(carrier)
    recomputed = compute_evidence_fingerprint(carrier)
    pit = {field: _require_text(carrier, field) for field in PIT_FIELDS}
    return {"evidence_fingerprint": recomputed, "pit_envelope": pit}


def compute_carrier_fingerprint(carrier: Mapping[str, Any]) -> str:
    return _fingerprint(build_carrier_fingerprint_payload(carrier))


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "UTC timestamp invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise FingerprintCanonicalizationError("INVALID_CANONICAL_PAYLOAD", "UTC timestamp required")
    return parsed.astimezone(timezone.utc)


def validate_carrier_fingerprints(
    carrier: Mapping[str, Any],
    optional_query_cutoff: str | None = None,
) -> dict[str, Any]:
    """Validate exact fingerprints and PIT eligibility without producing market facts."""
    try:
        carrier = _require_mapping(carrier)
        evidence = compute_evidence_fingerprint(carrier)
        if carrier.get("evidence_fingerprint") != evidence:
            return {"status": "INVALID", "reason_code": "EVIDENCE_FINGERPRINT_MISMATCH"}
        carrier_fp = compute_carrier_fingerprint(carrier)
        if carrier.get("carrier_fingerprint") != carrier_fp:
            return {"status": "INVALID", "reason_code": "CARRIER_FINGERPRINT_MISMATCH"}
        effective = _parse_utc(_require_text(carrier, "event_effective_at"))
        available = _parse_utc(_require_text(carrier, "evidence_available_at_utc"))
        known = _parse_utc(_require_text(carrier, "known_at_utc"))
        if known < available:
            return {"status": "INVALID", "reason_code": "PIT_BACKDATED"}
        eligible = True
        if optional_query_cutoff is not None:
            cutoff = _parse_utc(optional_query_cutoff)
            if known > cutoff:
                eligible = False
        return {
            "status": "VALID" if eligible else "PIT_INELIGIBLE",
            "reason_code": None if eligible else "PIT_INELIGIBLE",
            "evidence_fingerprint": evidence,
            "carrier_fingerprint": carrier_fp,
            "pit_eligible": eligible,
            "event_effective_at": effective.isoformat().replace("+00:00", "Z"),
        }
    except FingerprintCanonicalizationError as exc:
        return {"status": "INVALID", "reason_code": exc.reason_code, "detail": exc.detail}
