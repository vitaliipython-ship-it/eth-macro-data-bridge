from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REVISION_SCHEMA = "market-data-provider-revision/1.0.0"
SOURCE_SCHEMA = "kraken-revision-source-observation/1.0.0"
REVISION_CLASS = "PROVIDER_REVISABLE_SNAPSHOT"
SEMANTICS_PATH = Path("derivatives/metric-semantics.json")
EVIDENCE_ROOT = Path("derivatives/revisions/evidence")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return _sha256(_canonical(value))


def _descriptor(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256(raw),
        "size_bytes": len(raw),
    }


def _parse_utc(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise RuntimeError("revision known_at_utc must be UTC")
    return int(parsed.timestamp() * 1000)


def _revision_class(root: Path, metric: str) -> str:
    path = root / SEMANTICS_PATH
    if not path.is_file():
        raise RuntimeError("Kraken metric semantics missing during revision materialization")
    semantics = json.loads(path.read_text(encoding="utf-8"))
    if semantics.get("provider") != "kraken-futures":
        raise RuntimeError("Kraken metric semantics provider mismatch")
    policy = semantics.get("metrics", {}).get(metric)
    if not isinstance(policy, dict) or not policy.get("classification"):
        raise RuntimeError(f"Kraken metric classification missing: {metric}")
    return str(policy["classification"])


def _safe_source_path(root: Path, source_ref: str) -> Path:
    relative = Path(source_ref)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Kraken revision source snapshot path escapes authority root: {source_ref}")
    root_resolved = root.resolve()
    source_path = (root / relative).resolve()
    if source_path != root_resolved and root_resolved not in source_path.parents:
        raise RuntimeError(f"Kraken revision source snapshot path escapes authority root: {source_ref}")
    return source_path


def apply_kraken_revision_evidence(
    series: dict[str, Any],
    rows: list[Any],
    resources: list[dict[str, Any]],
    *,
    start_ms: int,
    end_ms: int,
    as_of_ms: int,
    root: Path,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Materialize qualified D9.2 PIT restatements without mutating base WARM bytes."""
    if series.get("provider") != "kraken-futures":
        return rows, resources
    metric = str(series.get("metric") or "")
    if _revision_class(root, metric) != REVISION_CLASS:
        return rows, resources
    legacy_key = series.get("legacy_key")
    if not isinstance(legacy_key, tuple) or len(legacy_key) != 3:
        raise RuntimeError("Kraken revision series identity missing")
    instrument = str(legacy_key[1])
    evidence_root = root / EVIDENCE_ROOT
    if not evidence_root.exists():
        return rows, resources

    base_by_timestamp = {int(row[0]): row for row in rows}
    chosen: dict[int, tuple[int, str, Any]] = {}
    provenance: dict[str, dict[str, Any]] = {item["path"]: item for item in resources}

    for path in sorted(evidence_root.rglob(f"{instrument}-{metric}-*.json")):
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if evidence.get("schema_version") != REVISION_SCHEMA:
            raise RuntimeError(f"unknown Kraken revision schema: {path.as_posix()}")
        if evidence.get("classification") != REVISION_CLASS:
            raise RuntimeError(f"Kraken revision classification mismatch: {path.as_posix()}")
        if (
            evidence.get("provider") != "kraken-futures"
            or evidence.get("instrument") != instrument
            or evidence.get("metric") != metric
        ):
            raise RuntimeError(f"Kraken revision identity mismatch: {path.as_posix()}")
        timestamp = evidence.get("effective_timestamp")
        if not isinstance(timestamp, int) or not (start_ms <= timestamp < end_ms):
            continue
        known_at = evidence.get("known_at_utc")
        if not isinstance(known_at, str):
            raise RuntimeError(f"Kraken revision known_at missing: {path.as_posix()}")
        known_at_ms = _parse_utc(known_at)
        if known_at_ms > as_of_ms:
            continue
        observed = evidence.get("observed_value")
        if not isinstance(observed, list) or not observed or int(observed[0]) != timestamp:
            raise RuntimeError(f"Kraken revision observed row mismatch: {path.as_posix()}")
        base = base_by_timestamp.get(timestamp)
        if base is None:
            raise RuntimeError(f"Kraken revision has no base WARM observation: {instrument}/{metric}/{timestamp}")
        previous_fingerprint = evidence.get("previous_value_fingerprint")
        if previous_fingerprint != _fingerprint(base):
            raise RuntimeError(f"Kraken revision previous fingerprint mismatch: {instrument}/{metric}/{timestamp}")
        expected_revision_of = f"kraken-futures/{instrument}/{metric}/{timestamp}"
        if evidence.get("revision_of") != expected_revision_of:
            raise RuntimeError(f"Kraken revision_of mismatch: {path.as_posix()}")
        revision_id = evidence.get("revision_id")
        if not isinstance(revision_id, str) or not revision_id:
            raise RuntimeError(f"Kraken revision id missing: {path.as_posix()}")

        source_ref = evidence.get("source_snapshot_ref")
        if not isinstance(source_ref, str) or not source_ref:
            raise RuntimeError(f"Kraken revision source snapshot missing: {path.as_posix()}")
        source_path = _safe_source_path(root, source_ref)
        if not source_path.is_file():
            raise RuntimeError(f"Kraken revision source snapshot unavailable: {source_ref}")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if (
            source.get("schema_version") != SOURCE_SCHEMA
            or source.get("provider") != "kraken-futures"
            or source.get("instrument") != instrument
            or source.get("metric") != metric
            or source.get("retrieved_at") != known_at
        ):
            raise RuntimeError(f"Kraken revision source snapshot identity mismatch: {source_ref}")
        source_rows = source.get("observed_rows")
        if not isinstance(source_rows, list) or observed not in source_rows:
            raise RuntimeError(f"Kraken revision observed row not bound to source snapshot: {source_ref}")

        current = chosen.get(timestamp)
        if current is not None and known_at_ms == current[0] and observed != current[2]:
            raise RuntimeError(f"ambiguous Kraken revision PIT ordering: {instrument}/{metric}/{timestamp}/{known_at}")
        if current is None or known_at_ms > current[0] or (known_at_ms == current[0] and revision_id > current[1]):
            chosen[timestamp] = (known_at_ms, revision_id, observed)

        provenance[path.relative_to(root).as_posix()] = _descriptor(path, root)
        provenance[source_ref] = _descriptor(source_path, root)

    if not chosen:
        return rows, [provenance[key] for key in sorted(provenance)]

    materialized = dict(base_by_timestamp)
    for timestamp, (_known_at_ms, _revision_id, observed) in chosen.items():
        materialized[timestamp] = observed
    return [materialized[key] for key in sorted(materialized)], [provenance[key] for key in sorted(provenance)]
