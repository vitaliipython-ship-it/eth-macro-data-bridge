from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from canonical_json import canonical_json_bytes, sha256_canonical_json

RUNTIME_CONTRACT_VERSION = "eth-macro-d8-runtime/1.0.0"
OBSERVATION_ENVELOPE_VERSION = "market-data-d8-runtime-observation/1.0.0"

SemanticPredecessor = Callable[
    [str, str, str, str | None, str], Mapping[str, Any] | None
]


def utc_iso(epoch_ms: int) -> str:
    """Return the canonical millisecond UTC representation used by D8 observations."""
    return (
        datetime.fromtimestamp(epoch_ms / 1000, timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def parse_utc(value: str) -> datetime:
    """Validate the existing D8 UTC RFC3339-with-Z timestamp contract."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC RFC3339 with Z")
    dt = datetime.fromisoformat(value[:-1] + "+00:00")
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def observation_id(
    provider: str,
    series_id: str,
    provider_timestamp: str | None,
    fingerprint: str,
) -> str:
    """Preserve the established D8 observation identity derivation."""
    raw = f"{provider}|{series_id}|{provider_timestamp or 'NONE'}|{fingerprint}".encode()
    return "obs-" + hashlib.sha256(raw).hexdigest()


def fingerprint_payload(value: Any) -> str:
    """Preserve the established D8 canonical value fingerprint."""
    return sha256_canonical_json(value)


def canonical_observation_bytes(observation: Mapping[str, object]) -> bytes:
    """Return the exact canonical bytes persisted by the F5C acquisition route."""
    return canonical_json_bytes(dict(observation))


def normalize_observations(
    cap: Mapping[str, Any],
    rows: list[dict[str, Any]],
    cid: str,
    slot: str,
    now_ms: int,
    *,
    source_revision: str,
    semantic_predecessor: SemanticPredecessor | None = None,
) -> list[dict[str, Any]]:
    """Normalize provider rows using the single Data Bridge-owned D8 semantics seam."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or "series_id" not in row or "value" not in row:
            raise ValueError("malformed provider observation")
        provider_ts = row.get("provider_timestamp_at")
        fp = fingerprint_payload(row["value"])
        oid = observation_id(cap["provider"], row["series_id"], provider_ts, fp)
        known_at = row.get("known_at") or utc_iso(now_ms)
        parse_utc(known_at)
        provenance = {
            "runtime_contract": RUNTIME_CONTRACT_VERSION,
            "source_revision": source_revision,
            "provider_route": row.get("provider_route"),
        }
        extra_provenance = row.get("provenance")
        if extra_provenance is not None:
            if not isinstance(extra_provenance, dict):
                raise ValueError("malformed provider provenance")
            provenance.update(extra_provenance)
        envelope: dict[str, Any] = {
            "schema_version": OBSERVATION_ENVELOPE_VERSION,
            "observation_id": oid,
            "fingerprint": fp,
            "provider": cap["provider"],
            "source_identity": row.get("source_identity", cap["provider"]),
            "capability_id": cap["id"],
            "series_id": row["series_id"],
            "provider_timestamp_at": provider_ts,
            "retrieved_at": utc_iso(now_ms),
            "known_at": known_at,
            "collected_at": utc_iso(now_ms),
            "canonical_cycle_id": cid,
            "canonical_slot": slot,
            "finality": row.get("finality", "OBSERVED_STATE"),
            "freshness": row.get(
                "freshness",
                {
                    "status": "UNKNOWN",
                    "age_seconds": None,
                    "target_cadence_seconds": 300,
                },
            ),
            "validation_status": "PASS",
            "provenance": provenance,
            "d9_forward_seam": {
                "identity_preserved": True,
                "known_at_preserved": True,
                "finality_preserved": True,
                "collection_gap_compatible": True,
                "target": row.get("d9_target", "WARM_FORWARD_OBSERVATION"),
            },
            "value": row["value"],
        }
        if row.get("revision_classification") == "PROVIDER_REVISABLE_SNAPSHOT":
            predecessor = (
                semantic_predecessor(
                    cap["id"], cap["provider"], row["series_id"], provider_ts, fp
                )
                if semantic_predecessor is not None
                else None
            )
            if predecessor is not None:
                envelope["provider_revision"] = {
                    "schema_version": "market-data-provider-revision/1.0.0",
                    "metric_policy_schema": "kraken-futures-provider-revision/1.0.0",
                    "classification": "PROVIDER_REVISABLE_SNAPSHOT",
                    "effective_timestamp": provider_ts,
                    "known_at_utc": known_at,
                    "previous_value_fingerprint": predecessor["fingerprint"],
                    "observed_value": row["value"],
                    "revision_of": predecessor["observation_id"],
                    "predecessor_observation_id": predecessor["observation_id"],
                    "source_snapshot_ref": row.get("source_snapshot_ref")
                    or row.get("provider_route"),
                }
        out.append(envelope)
    return out
