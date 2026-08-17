from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

Identity = Any
IdentityKey = Callable[[Any], Identity]
RevisionClassifier = Callable[[Any, Any, Identity], str | None]


def first_field_identity(row: Any) -> Identity:
    if not isinstance(row, (list, tuple)) or not row:
        raise ValueError("history observation must have a non-empty sequence identity")
    return row[0]


def canonical_observation_identity(row: Any, key: IdentityKey = first_field_identity) -> Identity:
    identity = key(row)
    if identity is None:
        raise ValueError("history observation identity must not be null")
    return identity


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    """Write repository JSON atomically using the existing compact-byte convention."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
    temporary = path.with_suffix(".json.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


class ImmutableHistoryConflict(ValueError):
    def __init__(self, conflicts: list[dict[str, Any]]):
        self.conflicts = conflicts
        first = conflicts[0] if conflicts else {}
        super().__init__(f"historical conflict identity={first.get('identity')!r}")


@dataclass(frozen=True)
class MergeResult:
    records: list[Any]
    changed: bool
    conflicts: list[dict[str, Any]]
    revisions: list[dict[str, Any]]


def merge_records(
    existing: Iterable[Any],
    incoming: Iterable[Any],
    *,
    key: IdentityKey = first_field_identity,
    revision_classifier: RevisionClassifier | None = None,
    fail_on_conflict: bool = True,
) -> MergeResult:
    """Merge observations deterministically without silently overwriting an identity.

    A qualified revision is evidence only: the previously stored base observation is
    intentionally preserved here. D9.2 owns the provider-specific PIT revision ledger.
    """
    index: dict[Identity, Any] = {}
    for row in existing:
        identity = canonical_observation_identity(row, key)
        if identity in index and index[identity] != row:
            raise ImmutableHistoryConflict(
                [{"identity": identity, "old": index[identity], "new": row, "reason": "EXISTING_DUPLICATE_CONFLICT"}]
            )
        index[identity] = row

    changed = False
    conflicts: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    for row in incoming:
        identity = canonical_observation_identity(row, key)
        old = index.get(identity)
        if old is None:
            index[identity] = row
            changed = True
            continue
        if old == row:
            continue
        classification = revision_classifier(old, row, identity) if revision_classifier else None
        if classification:
            revisions.append(
                {
                    "identity": identity,
                    "classification": classification,
                    "previous": old,
                    "observed": row,
                }
            )
            continue
        conflicts.append({"identity": identity, "old": old, "new": row, "reason": "IMMUTABLE_IDENTITY_CONFLICT"})

    if conflicts and fail_on_conflict:
        raise ImmutableHistoryConflict(conflicts)
    return MergeResult(
        records=[index[identity] for identity in sorted(index)],
        changed=changed,
        conflicts=conflicts,
        revisions=revisions,
    )


def append_partition(
    path: Path,
    metadata: dict[str, Any],
    records: Iterable[Any],
    *,
    records_field: str = "records",
    key: IdentityKey = first_field_identity,
    revision_classifier: RevisionClassifier | None = None,
) -> MergeResult:
    """Idempotently append one physical partition through the shared primitive."""
    existed = path.exists()
    payload = json.loads(path.read_text()) if existed else {**metadata, records_field: []}
    old_records = payload.get(records_field, [])
    if not isinstance(old_records, list):
        raise ValueError(f"history partition {path} field {records_field!r} is not a list")
    result = merge_records(
        old_records,
        records,
        key=key,
        revision_classifier=revision_classifier,
        fail_on_conflict=True,
    )
    metadata_changed = any(payload.get(name) != value for name, value in metadata.items())
    field_missing = records_field not in payload
    payload.update(metadata)
    payload[records_field] = result.records
    if not existed or result.changed or metadata_changed or field_missing:
        atomic_json(path, payload)
    return result


def partition_descriptor(
    path: Path,
    *,
    records_field: str = "records",
    key: IdentityKey = first_field_identity,
) -> dict[str, Any]:
    """Return deterministic physical evidence for a repository-owned partition."""
    raw = path.read_bytes()
    payload = json.loads(raw)
    records = payload.get(records_field)
    if not isinstance(records, list):
        raise ValueError(f"history partition {path} has no list field {records_field!r}")
    identities = [canonical_observation_identity(row, key) for row in records]
    if identities != sorted(identities) or len(identities) != len(set(identities)):
        raise ValueError(f"history partition identity ordering/uniqueness failure: {path}")
    return {
        "path": path.as_posix(),
        "records_field": records_field,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "record_count": len(records),
        "first_identity": identities[0] if identities else None,
        "last_identity": identities[-1] if identities else None,
    }
