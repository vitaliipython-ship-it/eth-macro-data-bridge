from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Iterable

from canonical_json import canonical_json_bytes

SCHEMA_VERSION = "market-data-history-publication-batch/1.0.0"
TARGET_RESIDENCE_ROLE = "WARM"


class PublicationBatchError(RuntimeError):
    """Fail-closed logical PublicationBatch identity/consistency violation."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _effective_timestamp(envelope: dict[str, Any]) -> str:
    value = envelope.get("provider_timestamp_at") or envelope.get("known_at")
    if not isinstance(value, str) or not value:
        raise PublicationBatchError("member lacks canonical effective timestamp")
    return value


def canonical_member_sort_key(envelope: dict[str, Any]) -> tuple[str, str, str]:
    series_id = envelope.get("series_id")
    observation_id = envelope.get("observation_id")
    if not isinstance(series_id, str) or not series_id:
        raise PublicationBatchError("member series_id missing")
    if not isinstance(observation_id, str) or not observation_id:
        raise PublicationBatchError("member observation_id missing")
    return (series_id, _effective_timestamp(envelope), observation_id)


def membership_preimage(member_observation_ids: list[str]) -> list[str]:
    return list(member_observation_ids)


def payload_binding_preimage(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "position": member["position"],
            "observation_id": member["observation_id"],
            "series_id": member["series_id"],
            "provider_timestamp_at": member.get("provider_timestamp_at"),
            "known_at": member["known_at"],
            "payload_fingerprint": member["payload_fingerprint"],
            "payload_sha256": member["payload_sha256"],
        }
        for member in members
    ]


def batch_id_preimage(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": batch["schema_version"],
        "target_residence_role": batch["target_residence_role"],
        "membership_sha256": batch["membership_sha256"],
        "payload_sha256": batch["payload_sha256"],
        "member_observation_ids": list(batch["member_observation_ids"]),
    }


def _member(envelope: dict[str, Any], position: int) -> dict[str, Any]:
    required = ("observation_id", "series_id", "provider", "fingerprint", "known_at", "finality")
    missing = [name for name in required if name not in envelope]
    if missing:
        raise PublicationBatchError(f"D8 envelope missing PublicationBatch fields: {missing}")
    return {
        "position": position,
        "observation_id": envelope["observation_id"],
        "series_id": envelope["series_id"],
        "provider": envelope["provider"],
        "provider_timestamp_at": envelope.get("provider_timestamp_at"),
        "payload_fingerprint": envelope["fingerprint"],
        "payload_sha256": _sha256(canonical_json_bytes(envelope)),
        "known_at": envelope["known_at"],
        "finality": envelope["finality"],
    }


def build_publication_batch(envelopes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(row) for row in envelopes]
    if not rows:
        raise PublicationBatchError("PublicationBatch requires at least one observation")
    rows.sort(key=canonical_member_sort_key)
    members = [_member(row, index) for index, row in enumerate(rows)]
    ids = [member["observation_id"] for member in members]
    if len(ids) != len(set(ids)):
        raise PublicationBatchError("duplicate observation_id in logical PublicationBatch")
    batch: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "target_residence_role": TARGET_RESIDENCE_ROLE,
        "member_count": len(members),
        "member_observation_ids": ids,
        "members": members,
        "membership_sha256": _sha256(canonical_json_bytes(membership_preimage(ids))),
        "payload_sha256": _sha256(canonical_json_bytes(payload_binding_preimage(members))),
    }
    batch["batch_id"] = "pub-" + _sha256(canonical_json_bytes(batch_id_preimage(batch)))
    validate_publication_batch(batch)
    return batch


def validate_publication_batch(batch: dict[str, Any]) -> None:
    if not isinstance(batch, dict):
        raise PublicationBatchError("PublicationBatch must be an object")
    if batch.get("schema_version") != SCHEMA_VERSION:
        raise PublicationBatchError("PublicationBatch schema_version mismatch")
    if batch.get("target_residence_role") != TARGET_RESIDENCE_ROLE:
        raise PublicationBatchError("PublicationBatch target residence role mismatch")
    forbidden = {"publication_attempt_id", "backend_profile", "retry_at", "server_hostname", "filesystem_path", "git_commit"}
    if forbidden & set(batch):
        raise PublicationBatchError("logical PublicationBatch contains transient/backend attempt state")
    ids = batch.get("member_observation_ids")
    members = batch.get("members")
    if not isinstance(ids, list) or not isinstance(members, list) or not ids or not members:
        raise PublicationBatchError("PublicationBatch membership missing")
    if len(ids) != len(members):
        raise PublicationBatchError("member_observation_ids/members length mismatch")
    if batch.get("member_count") != len(members):
        raise PublicationBatchError("member_count mismatch")
    if len(ids) != len(set(ids)):
        raise PublicationBatchError("duplicate observation_id in PublicationBatch")
    for index, member in enumerate(members):
        if not isinstance(member, dict):
            raise PublicationBatchError("PublicationBatch member must be object")
        if member.get("position") != index:
            raise PublicationBatchError("PublicationBatch member position mismatch")
        if member.get("observation_id") != ids[index]:
            raise PublicationBatchError("duplicated membership list mismatch")
        canonical_member_sort_key(member)
    if members != sorted(members, key=canonical_member_sort_key):
        raise PublicationBatchError("PublicationBatch members are not in canonical order")
    expected_membership = _sha256(canonical_json_bytes(membership_preimage(ids)))
    if batch.get("membership_sha256") != expected_membership:
        raise PublicationBatchError("membership_sha256 mismatch")
    expected_payload = _sha256(canonical_json_bytes(payload_binding_preimage(members)))
    if batch.get("payload_sha256") != expected_payload:
        raise PublicationBatchError("payload_sha256 mismatch")
    expected_batch_id = "pub-" + _sha256(canonical_json_bytes(batch_id_preimage(batch)))
    if batch.get("batch_id") != expected_batch_id:
        raise PublicationBatchError("batch_id mismatch")
