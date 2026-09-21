from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from options_derivation import derive_options_analytics
from tools.history_access import _v1
from tools.history_consumer import (
    HistoryConsumerError,
    _classify_derivation_policy_comparability,
    classify_sampled_history_comparability,
    sampled_history,
)
from tools.sampled_history import (
    OPTIONS_SURFACE_CAPABILITY_ID,
    build_observation_index,
)

DAY_MS = 86_400_000


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _direct_current(index: dict) -> tuple[dict, dict]:
    observation = index["observations"][-1]
    descriptor = observation["resource_descriptor"]
    raw = _v1._warm_bytes(descriptor, Path.cwd())
    snapshot = json.loads(raw)
    return snapshot, derive_options_analytics(snapshot)


def _print_read(label: str, target_ms: int, result: tuple[dict, str, dict, dict]) -> dict:
    _plan, payload, diagnostics, receipt = result
    rendered = json.loads(payload)
    identity = rendered.get("derivation_policy_identity") or {}
    print(f"{label}_TARGET_UTC={_utc(target_ms)}")
    print(f"{label}_SELECTED_OBSERVATION_UTC={rendered.get('selected_observation_timestamp_utc')}")
    print(f"{label}_DISTANCE_TO_TARGET_MS={rendered.get('distance_to_target_ms')}")
    print(f"{label}_AVAILABILITY_STATE={rendered.get('availability_state')}")
    print(f"{label}_RESOURCE_IDENTITY={rendered.get('resource_identity')}")
    print(f"{label}_DERIVATION_POLICY_ID={identity.get('derivation_policy_id')}")
    print(f"{label}_DERIVATION_POLICY_VERSION={identity.get('derivation_policy_version')}")
    print(f"{label}_DERIVATION_POLICY_SHA256={identity.get('derivation_policy_sha256')}")
    if diagnostics.get("direct_provider_history_fallback") is not False:
        raise RuntimeError(f"{label}: direct provider fallback detected")
    if receipt.get("availability_state") != "HISTORY_AVAILABLE":
        raise RuntimeError(f"{label}: history unavailable: {receipt.get('availability_state')}")
    return rendered


def _metric_row(label: str, rendered: dict) -> None:
    analytics = rendered["analytics"]
    mapping = {
        "CALL_OI": "total_call_oi",
        "PUT_OI": "total_put_oi",
        "P_C_OI": "put_call_oi_ratio",
        "CALL_VOLUME": "total_call_volume",
        "PUT_VOLUME": "total_put_volume",
        "P_C_VOLUME": "put_call_volume_ratio",
        "ATM_IV_7D": "atm_iv_7d",
        "ATM_IV_30D": "atm_iv_30d",
        "ATM_IV_90D": "atm_iv_90d",
    }
    for output, key in mapping.items():
        print(f"{label}_{output}={analytics.get(key)}")
    for days in (7, 30, 90):
        skew = analytics.get(f"25d_{days}d") or {}
        print(f"{label}_CALL_IV_{days}D={skew.get('call_iv')}")
        print(f"{label}_PUT_IV_{days}D={skew.get('put_iv')}")
        print(f"{label}_RR_{days}D={skew.get('risk_reversal')}")
        print(f"{label}_BUTTERFLY_{days}D={skew.get('butterfly')}")


def _mechanical_delta(current: dict, historical: dict, historical_label: str) -> None:
    keys = (
        "total_call_oi", "total_put_oi", "put_call_oi_ratio",
        "total_call_volume", "total_put_volume", "put_call_volume_ratio",
        "atm_iv_7d", "atm_iv_30d", "atm_iv_90d",
    )
    for key in keys:
        try:
            current_value = Decimal(str(current["analytics"].get(key)))
            historical_value = Decimal(str(historical["analytics"].get(key)))
        except (InvalidOperation, TypeError, ValueError):
            continue
        delta = current_value - historical_value
        pct = (delta / historical_value * Decimal(100)) if historical_value else None
        direction = "INCREASE" if delta > 0 else ("DECREASE" if delta < 0 else "UNCHANGED")
        print(f"DELTA_CURRENT_VS_{historical_label}_{key.upper()}={delta}")
        print(f"PCT_CURRENT_VS_{historical_label}_{key.upper()}={pct}")
        print(f"DIRECTION_CURRENT_VS_{historical_label}_{key.upper()}={direction}")


def main() -> int:
    index = build_observation_index(OPTIONS_SURFACE_CAPABILITY_ID)
    if index["observation_count"] < 1:
        raise RuntimeError("no canonical option surface observations")
    capability = index["capability"]
    if capability.get("history_mode") != "FORWARD_ONLY" or capability.get("availability_status") != "PASS":
        raise RuntimeError("forward sampled capability discovery failed")

    current_ms = int(index["last_observation_timestamp_ms"])
    snapshot, current_direct_analytics = _direct_current(index)
    if snapshot.get("timestamp_ms") != current_ms:
        raise RuntimeError("current canonical snapshot anchor mismatch")

    current_evidence = sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(current_ms))
    current = _print_read("CURRENT", current_ms, current_evidence)
    if current.get("analytics") != current_direct_analytics:
        raise RuntimeError("CURRENT_HISTORICAL_DERIVATION_PARITY_FAILED")

    reads = {"CURRENT": current}
    evidence = {"CURRENT": current_evidence}
    for label, delta_ms in (("H24", DAY_MS), ("H72", 3 * DAY_MS), ("D7", 7 * DAY_MS)):
        target_ms = current_ms - delta_ms
        sampled = sampled_history(OPTIONS_SURFACE_CAPABILITY_ID, _utc(target_ms))
        evidence[label] = sampled
        reads[label] = _print_read(label, target_ms, sampled)

    comparability = classify_sampled_history_comparability(list(evidence.values()))
    if comparability["terminal_classification"] != "PASS":
        raise RuntimeError("matching sampled derivation policies were not classified PASS")
    if comparability.get("provenance_boundary") != "VERIFIED_CANONICAL_SAMPLED_HISTORY_ENVELOPE":
        raise RuntimeError("PROGRAM-3 comparability provenance boundary was not verified")
    identity = comparability["derivation_policy_identity"]

    mismatch = json.loads(json.dumps(current))
    mismatch["analytics"]["derivation_policy_version"] = (
        str(mismatch["analytics"]["derivation_policy_version"]) + "-mismatch"
    )
    mismatch_classification = _classify_derivation_policy_comparability([current, mismatch])
    if mismatch_classification["comparability_classification"] != "NOT_COMPARABLE":
        raise RuntimeError("derivation-policy mismatch was not classified NOT_COMPARABLE")
    if mismatch_classification["source_error_code"] != "DERIVATION_VERSION_MISMATCH":
        raise RuntimeError("underlying derivation mismatch error code was not preserved")
    if mismatch_classification["source_availability_state"] != "DERIVATION_VERSION_MISMATCH":
        raise RuntimeError("underlying derivation mismatch availability state was not preserved")
    if "physical_integrity_valid" in mismatch_classification or "read_route_executable" in mismatch_classification:
        raise RuntimeError("pure semantic comparator self-asserted physical/read evidence")

    fabricated = {
        "availability_state": "HISTORY_AVAILABLE",
        "resource_identity": "sha256:" + "a" * 64,
        "analytics": json.loads(json.dumps(current["analytics"])),
    }
    fabricated_peer = json.loads(json.dumps(fabricated))
    fabricated_peer["resource_identity"] = "sha256:" + "b" * 64
    fabricated_peer["analytics"]["derivation_policy_version"] = (
        str(fabricated_peer["analytics"]["derivation_policy_version"]) + "-fabricated"
    )
    try:
        classify_sampled_history_comparability([fabricated, fabricated_peer])
    except HistoryConsumerError as exc:
        if exc.code != "SAMPLED_COMPARABILITY_PRECONDITION_FAILED":
            raise RuntimeError("fabricated sampled input failed with unexpected code") from exc
    else:
        raise RuntimeError("fabricated sampled input reached trusted PROGRAM-3 terminal classification")

    for label, rendered in reads.items():
        _metric_row(label, rendered)
    for label in ("H24", "H72", "D7"):
        _mechanical_delta(current, reads[label], label)

    print("CAPABILITY_DISCOVERY=PASS")
    print("FORWARD_SAMPLED_HISTORY_RESOLUTION=PASS")
    print("AT_OR_BEFORE_SELECTION=PASS")
    print("CANONICAL_SNAPSHOT_READER=PASS")
    print("SHARED_OPTIONS_DERIVATION=PASS")
    print("CURRENT_HISTORICAL_DERIVATION_PARITY=PASS")
    print("OPTIONS_24H_READ=PASS")
    print("OPTIONS_72H_READ=PASS")
    print("OPTIONS_7D_READ=PASS")
    print("DERIVATION_POLICY_MATCH=YES")
    print("DERIVATION_POLICY_ID=" + identity["derivation_policy_id"])
    print("DERIVATION_POLICY_VERSION=" + identity["derivation_policy_version"])
    print("DERIVATION_POLICY_SHA256=" + identity["derivation_policy_sha256"])
    print("PROGRAM3_SAMPLED_COMPARABILITY_MATCH=PASS")
    print("PROGRAM3_SAMPLED_TERMINAL_CLASSIFICATION=PASS")
    print("UNDERLYING_MISMATCH=" + mismatch_classification["source_availability_state"])
    print("PROGRAM3_MISMATCH_TERMINAL_CLASSIFICATION=NOT_COMPARABLE")
    print("PROGRAM3_NOT_COMPARABLE_MAPPING=PASS")
    print("PROGRAM3_COMPARABILITY_PROVENANCE_BOUNDARY=PASS")
    print("PROGRAM3_FABRICATED_INPUT_REJECTED=PASS")
    print("PROGRAM3_PHYSICAL_INTEGRITY_SELF_ASSERTION=NO")
    print("PROGRAM3_READ_EXECUTABILITY_SELF_ASSERTION=NO")
    print("NO_DIRECT_PROVIDER_HISTORY_SUBSTITUTION=PASS")
    print("SECOND_MARKET_DATA_AUTHORITY=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
