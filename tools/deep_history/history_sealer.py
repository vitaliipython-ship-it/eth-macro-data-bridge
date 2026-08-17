from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _history_sealer_core as _core
from revision_materializer import apply_kraken_revision_evidence

# Public compatibility facade: retain the existing D9.3 sealer interface while
# successor overlays are applied at narrow semantic seams. The core module is the
# byte-preserved predecessor implementation, not a second sealer route.
for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_original_declared_regular_resources = _core.declared_regular_resources
_original_generation_membership_states = _core.generation_membership_states
_original_eligible_snapshot_periods = _core.eligible_snapshot_periods
_original_candidate_fingerprint = _core._candidate_fingerprint


def _record_encoding(payload: dict[str, Any], rows: list[Any], path: Path) -> dict[str, Any]:
    columns = payload.get("columns")
    if isinstance(columns, list) and columns and all(isinstance(name, str) and name for name in columns):
        if any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
            raise RuntimeError(f"WARM positional encoding/row width mismatch: {path.as_posix()}")
        return {"kind": "POSITIONAL_COLUMNS", "columns": columns}
    if rows and all(isinstance(row, list) and len(row) == 2 and isinstance(row[0], int) for row in rows):
        return {"kind": "TIMESTAMP_VALUE"}
    raise RuntimeError(f"WARM record encoding is ambiguous: {path.as_posix()}")


def declared_regular_resources(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    grouped = _original_declared_regular_resources(root)
    for series_id, item in grouped.items():
        encoding = None
        for resource in item.get("resources", []):
            path = root / resource["path"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("records")
            if not isinstance(rows, list) or not rows:
                raise RuntimeError(f"canonical WARM resource lost records: {resource['path']}")
            current = _record_encoding(payload, rows, path)
            if encoding is None:
                encoding = current
            elif encoding != current:
                raise RuntimeError(f"mixed WARM record encoding for semantic series: {series_id}")
        if encoding is None:
            raise RuntimeError(f"record encoding missing for semantic series: {series_id}")
        item["record_encoding"] = encoding
    return grouped


def generation_membership_states(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    states = _original_generation_membership_states(as_of_ms, root)
    authority_by_series = {
        item["series_id"]: item for item in _core.declared_regular_authority(root).values()
    }
    physical_by_series = declared_regular_resources(root)
    for state in states:
        for member in state.get("members", []):
            semantic = authority_by_series.get(member.get("series_id"))
            concrete = physical_by_series.get(member.get("series_id"))
            if semantic is None or concrete is None:
                raise RuntimeError(f"declared sealer authority missing during successor materialization: {member.get('series_id')}")
            rows, resources = apply_kraken_revision_evidence(
                semantic,
                member["rows"],
                member["resources"],
                start_ms=member["start_ms"],
                end_ms=member["end_ms"],
                as_of_ms=as_of_ms,
                root=root,
            )
            gaps = _core._validate_fixed_grid(
                rows,
                member["start_ms"],
                member["end_ms"],
                semantic["step_ms"],
                semantic["coverage_start_ms"],
            )
            if gaps:
                raise RuntimeError(f"PIT revision materialization changed fixed-grid membership: {member['series_id']}")
            member["rows"] = rows
            member["resources"] = resources
            member["record_encoding"] = concrete["record_encoding"]
    return states


def eligible_snapshot_periods(as_of_ms: int, root: Path = ROOT) -> list[dict[str, Any]]:
    candidates = _original_eligible_snapshot_periods(as_of_ms, root)
    for candidate in candidates:
        candidate["record_encoding"] = {"kind": "SNAPSHOT_OBJECT"}
    return candidates


def _asset_payload(candidate: dict[str, Any], generation_id: str) -> dict[str, Any]:
    encoding = candidate.get("record_encoding")
    if not isinstance(encoding, dict) or encoding.get("kind") not in {
        "POSITIONAL_COLUMNS", "TIMESTAMP_VALUE", "SNAPSHOT_OBJECT"
    }:
        raise RuntimeError(f"D9 COLD candidate record encoding missing: {candidate.get('series_id')}")
    return {
        "schema_version": "market-data-cold-asset/1.1.0",
        "generation_id": generation_id,
        "series_id": candidate["series_id"],
        "series_kind": candidate["series_kind"],
        "record_encoding": encoding,
        "coverage_start_ms": candidate["start_ms"],
        "coverage_end_ms": candidate["end_ms"],
        "known_gaps": candidate["known_gaps"],
        "records": candidate["rows"],
    }


def _candidate_fingerprint(members: list[dict[str, Any]]) -> str:
    base = _original_candidate_fingerprint(members)
    encodings = [
        {"series_id": member["series_id"], "record_encoding": member.get("record_encoding")}
        for member in sorted(members, key=lambda item: item["series_id"])
    ]
    return _core.sha256_bytes(_core.compact({
        "predecessor_candidate_fingerprint": base,
        "record_encodings": encodings,
    }))


# Existing core build/detect/publish functions resolve these globals from the core
# module. Patch only the semantic seams; public CLI and imports therefore share one
# implementation and one publication route.
_core.declared_regular_resources = declared_regular_resources
_core.generation_membership_states = generation_membership_states
_core.eligible_snapshot_periods = eligible_snapshot_periods
_core._asset_payload = _asset_payload
_core._candidate_fingerprint = _candidate_fingerprint

globals()["declared_regular_resources"] = declared_regular_resources
globals()["generation_membership_states"] = generation_membership_states
globals()["eligible_snapshot_periods"] = eligible_snapshot_periods
globals()["_asset_payload"] = _asset_payload
globals()["_candidate_fingerprint"] = _candidate_fingerprint


if __name__ == "__main__":
    _core.main()
