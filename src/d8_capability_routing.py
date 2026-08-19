from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "d8-runtime-candidate.json"


class CapabilityRoutingError(RuntimeError):
    """Fail-closed capability declaration/routing violation."""


def declarations_from_contract(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        capabilities = contract["due_policy"]["capabilities"]
    except (KeyError, TypeError) as exc:
        raise CapabilityRoutingError("D8 capability declaration authority missing") from exc
    if not isinstance(capabilities, list) or not capabilities:
        raise CapabilityRoutingError("D8 capability declaration set must be non-empty")
    out: dict[str, dict[str, Any]] = {}
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise CapabilityRoutingError("capability declaration must be an object")
        capability_id = capability.get("id")
        provider = capability.get("provider")
        cadence = capability.get("cadence_minutes")
        forwarding = capability.get("forwarding")
        if not isinstance(capability_id, str) or not capability_id or capability_id in out:
            raise CapabilityRoutingError("capability id missing or duplicated")
        if not isinstance(provider, str) or not provider:
            raise CapabilityRoutingError(f"capability provider missing: {capability_id}")
        if not isinstance(cadence, int) or cadence <= 0:
            raise CapabilityRoutingError(f"capability cadence invalid: {capability_id}")
        if not isinstance(forwarding, dict):
            raise CapabilityRoutingError(f"forwarding declaration missing: {capability_id}")
        if forwarding.get("target_residence_role") != "WARM":
            raise CapabilityRoutingError(f"unsupported target residence role: {capability_id}")
        rules = forwarding.get("series_rules")
        if not isinstance(rules, list) or not rules:
            raise CapabilityRoutingError(f"series routing rules missing: {capability_id}")
        for rule in rules:
            if not isinstance(rule, dict):
                raise CapabilityRoutingError(f"series rule must be object: {capability_id}")
            for field in (
                "series_id_regex",
                "lifecycle_class",
                "normalization_family",
                "finality_policy",
                "publication_eligibility",
            ):
                if not isinstance(rule.get(field), str) or not rule[field]:
                    raise CapabilityRoutingError(f"series rule field missing: {capability_id}:{field}")
            allowed = rule.get("allowed_finality")
            if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed):
                raise CapabilityRoutingError(f"allowed_finality missing: {capability_id}")
            try:
                re.compile(rule["series_id_regex"])
            except re.error as exc:
                raise CapabilityRoutingError(f"invalid series regex: {capability_id}") from exc
        out[capability_id] = capability
    return out


@lru_cache(maxsize=1)
def load_default_declarations() -> dict[str, dict[str, Any]]:
    if not CONTRACT_PATH.is_file():
        raise CapabilityRoutingError(f"D8 capability declaration contract missing: {CONTRACT_PATH}")
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityRoutingError("D8 capability declaration contract unreadable") from exc
    return declarations_from_contract(contract)


def capability_provider(capability_id: str, declarations: dict[str, dict[str, Any]] | None = None) -> str:
    declarations = declarations or load_default_declarations()
    try:
        return str(declarations[capability_id]["provider"])
    except KeyError as exc:
        raise CapabilityRoutingError(f"unsupported D8 capability: {capability_id}") from exc


def runtime_due_policy(declarations: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, Any], ...]:
    declarations = declarations or load_default_declarations()
    rows: list[dict[str, Any]] = []
    for capability in declarations.values():
        row = {
            "id": capability["id"],
            "provider": capability["provider"],
            "every_minutes": capability["cadence_minutes"],
            "required": bool(capability.get("required", False)),
        }
        if "profiles" in capability:
            row["profiles"] = list(capability["profiles"])
        if capability.get("disabled") is True:
            row["disabled"] = True
        rows.append(row)
    return tuple(rows)


def route_capability_series(
    capability_id: str,
    provider: str,
    series_id: str,
    *,
    declarations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    declarations = declarations or load_default_declarations()
    try:
        capability = declarations[capability_id]
    except KeyError as exc:
        raise CapabilityRoutingError(f"unsupported D8 capability: {capability_id}") from exc
    if provider != capability["provider"]:
        raise CapabilityRoutingError("capability/provider identity mismatch")
    if not isinstance(series_id, str) or not series_id:
        raise CapabilityRoutingError("series_id missing")
    matches = [
        rule
        for rule in capability["forwarding"]["series_rules"]
        if re.fullmatch(rule["series_id_regex"], series_id)
    ]
    if len(matches) != 1:
        raise CapabilityRoutingError(
            f"capability/series mapping must match exactly one declaration: {capability_id}:{series_id}"
        )
    rule = matches[0]
    return {
        "capability_id": capability_id,
        "provider": provider,
        "series_id": series_id,
        "lifecycle_class": rule["lifecycle_class"],
        "normalization_family": rule["normalization_family"],
        "finality_policy": rule["finality_policy"],
        "allowed_finality": tuple(rule["allowed_finality"]),
        "publication_eligibility": rule["publication_eligibility"],
        "target_residence_role": capability["forwarding"]["target_residence_role"],
    }
