from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from history_store import MergeResult, append_partition, atomic_json

SEMANTICS_PATH = Path("derivatives/metric-semantics.json")
REVISION_SCHEMA = "market-data-provider-revision/1.0.0"
SOURCE_SCHEMA = "kraken-revision-source-observation/1.0.0"
REVISION_OVERLAP_SECONDS = 6 * 3600
INSTRUMENTS = ("PI_ETHUSD", "PI_XBTUSD")
BASE = "https://futures.kraken.com/api/charts/v1/analytics"


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y/%m/%d")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def revisable_metrics(path: Path = SEMANTICS_PATH) -> set[str]:
    contract = json.loads(path.read_text())
    if contract.get("provider") != "kraken-futures":
        raise RuntimeError("Kraken revision semantics provider mismatch")
    return {
        metric
        for metric, policy in contract.get("metrics", {}).items()
        if policy.get("classification") == "PROVIDER_REVISABLE_SNAPSHOT"
    }


def revision_overlap_cursor(existing_tail_ms: int | None, default_since_seconds: int, metric: str, revisable: set[str]) -> int:
    if existing_tail_ms is None or metric not in revisable:
        return default_since_seconds if existing_tail_ms is None else max(default_since_seconds, existing_tail_ms // 1000 + 1)
    return max(default_since_seconds, existing_tail_ms // 1000 - REVISION_OVERLAP_SECONDS)


def _revision_id(instrument: str, metric: str, timestamp_ms: int, observed: Any) -> str:
    identity = f"kraken-futures\0{instrument}\0{metric}\0{timestamp_ms}\0{fingerprint(observed)}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


def _evidence_path(instrument: str, metric: str, timestamp_ms: int, revision_id: str) -> Path:
    return Path("derivatives/revisions/evidence") / day(timestamp_ms) / "kraken-futures" / f"{instrument}-{metric}-{revision_id}.json"


def append_metric_with_revision_evidence(
    path: Path,
    metadata: dict[str, Any],
    records: Iterable[Any],
    *,
    instrument: str,
    metric: str,
    known_at_ms: int,
    source_routes: list[str],
    revisable: set[str] | None = None,
) -> tuple[MergeResult, list[str]]:
    policies = revisable if revisable is not None else revisable_metrics()
    classifier = (lambda _old, _new, _identity: "PROVIDER_REVISABLE_SNAPSHOT") if metric in policies else None
    result = append_partition(path, metadata, records, revision_classifier=classifier)
    if not result.revisions:
        return result, []

    novel = []
    for revision in result.revisions:
        timestamp_ms = int(revision["identity"])
        revision_id = _revision_id(instrument, metric, timestamp_ms, revision["observed"])
        evidence_path = _evidence_path(instrument, metric, timestamp_ms, revision_id)
        if evidence_path.exists():
            continue
        novel.append((revision, revision_id, evidence_path))
    if not novel:
        return result, []

    source_path = (
        Path("derivatives/revisions/source")
        / day(known_at_ms)
        / "kraken-futures"
        / f"{instrument}-{metric}-{known_at_ms}.json"
    )
    atomic_json(
        source_path,
        {
            "schema_version": SOURCE_SCHEMA,
            "provider": "kraken-futures",
            "instrument": instrument,
            "metric": metric,
            "retrieved_at": iso(known_at_ms),
            "source_routes": source_routes,
            "observed_rows": [item[0]["observed"] for item in novel],
        },
    )

    paths = []
    for revision, revision_id, evidence_path in novel:
        timestamp_ms = int(revision["identity"])
        revision_of = f"kraken-futures/{instrument}/{metric}/{timestamp_ms}"
        atomic_json(
            evidence_path,
            {
                "schema_version": REVISION_SCHEMA,
                "revision_id": revision_id,
                "classification": "PROVIDER_REVISABLE_SNAPSHOT",
                "effective_timestamp": timestamp_ms,
                "known_at_utc": iso(known_at_ms),
                "provider": "kraken-futures",
                "instrument": instrument,
                "metric": metric,
                "previous_value_fingerprint": fingerprint(revision["previous"]),
                "observed_value": revision["observed"],
                "source_snapshot_ref": source_path.as_posix(),
                "revision_of": revision_of,
            },
        )
        paths.append(evidence_path.as_posix())
    return result, paths


def revision_evidence_count(instrument: str, metric: str) -> int:
    count = 0
    for path in Path("derivatives/revisions/evidence").rglob(f"{instrument}-{metric}-*.json") if Path("derivatives/revisions/evidence").exists() else []:
        payload = json.loads(path.read_text())
        if payload.get("provider") == "kraken-futures" and payload.get("instrument") == instrument and payload.get("metric") == metric:
            count += 1
    return count


def _flatten(result: dict[str, Any]) -> list[list[Any]]:
    timestamps = result.get("timestamp", [])
    data = result.get("data", [])
    normalize = lambda value: int(value) * 1000 if int(value) < 10**12 else int(value)
    if isinstance(data, list):
        return [[normalize(timestamp), data[index]] for index, timestamp in enumerate(timestamps)]
    fields: list[tuple[str, list[Any]]] = []

    def walk(prefix: list[str], value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(prefix + [key], child)
        elif isinstance(value, list):
            fields.append((".".join(prefix), value))

    walk([], data)
    return [[normalize(timestamp), {key: values[index] for key, values in fields}] for index, timestamp in enumerate(timestamps)]


def observe_kraken_revisions(get: Callable[[str], Any], now_ms: int) -> dict[str, Any]:
    policies = revisable_metrics()
    since_seconds = now_ms // 1000 - 7 * 86_400
    total_revisions = 0
    observed_series = 0
    evidence_paths: list[str] = []
    for instrument in INSTRUMENTS:
        for metric in sorted(policies):
            existing_paths = sorted(Path("derivatives/archive").rglob(f"{instrument}-{metric}.json"))
            existing_tail = None
            for path in existing_paths:
                rows = json.loads(path.read_text()).get("records", [])
                if rows and (existing_tail is None or int(rows[-1][0]) > existing_tail):
                    existing_tail = int(rows[-1][0])
            if existing_tail is None:
                continue
            cursor = revision_overlap_cursor(existing_tail, since_seconds, metric, policies)
            unique: dict[int, list[Any]] = {}
            routes = []
            pages = 0
            more = True
            while more and pages < 6:
                url = f"{BASE}/{instrument}/{metric}?since={cursor}&interval=300"
                response = get(url)
                routes.append(url)
                pages += 1
                if response.get("errors"):
                    raise RuntimeError(f"Kraken revision observer error {instrument}/{metric}: {response['errors']}")
                result = response["result"]
                page = _flatten(result)
                for row in page:
                    timestamp = int(row[0])
                    old = unique.get(timestamp)
                    if old is not None and old != row:
                        raise RuntimeError(f"Kraken revision observer conflicting duplicate {instrument}/{metric}/{timestamp}")
                    unique[timestamp] = row
                more = bool(result.get("more"))
                if more:
                    if not page:
                        raise RuntimeError(f"Kraken revision observer empty pagination {instrument}/{metric}")
                    next_cursor = int(page[-1][0]) // 1000 + 1
                    if next_cursor <= cursor:
                        raise RuntimeError(f"Kraken revision observer pagination stalled {instrument}/{metric}")
                    cursor = next_cursor
            if more:
                raise RuntimeError(f"Kraken revision observer pagination exceeded bound {instrument}/{metric}")
            finalized = [unique[key] for key in sorted(unique) if key <= now_ms - 1_800_000]
            if not finalized:
                continue
            grouped: dict[str, list[list[Any]]] = {}
            for row in finalized:
                grouped.setdefault(day(int(row[0])), []).append(row)
            observed_series += 1
            for date, rows in grouped.items():
                path = Path("derivatives/archive") / date / "kraken-futures" / f"{instrument}-{metric}.json"
                _result, created = append_metric_with_revision_evidence(
                    path,
                    {
                        "schema_version": "1.0.0",
                        "provider": "kraken-futures",
                        "instrument": instrument,
                        "metric": metric,
                        "resolution_seconds": 300,
                    },
                    rows,
                    instrument=instrument,
                    metric=metric,
                    known_at_ms=now_ms,
                    source_routes=routes,
                    revisable=policies,
                )
                evidence_paths.extend(created)
                total_revisions += len(created)
    return {
        "status": "PASS",
        "observed_series": observed_series,
        "new_revision_evidence": total_revisions,
        "evidence_paths": evidence_paths,
    }
