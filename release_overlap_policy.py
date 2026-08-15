from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

SEMANTICS_PATH = Path("derivatives/metric-semantics.json")
REVISABLE_SCHEMA = "kraken-futures-provider-revision/1.0.0"


def load_contract(path=SEMANTICS_PATH):
    contract = json.loads(Path(path).read_text())
    if contract.get("schema_version") != "1.0.0" or contract.get("provider") != "kraken-futures":
        raise RuntimeError("invalid Kraken metric-semantics contract")
    metrics = contract.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise RuntimeError("missing Kraken metric classifications")
    return contract


def revisable_metrics(contract):
    return {
        metric
        for metric, policy in contract["metrics"].items()
        if policy.get("classification") == "PROVIDER_REVISABLE_SNAPSHOT"
    }


def release_semantics(contract, metric, publisher):
    policy = contract["metrics"][metric]
    if policy.get("classification") != "PROVIDER_REVISABLE_SNAPSHOT" or policy.get("schema_version") != REVISABLE_SCHEMA:
        raise RuntimeError(f"metric is not qualified as provider-revisable: {metric}")
    return {
        "schema_version": REVISABLE_SCHEMA,
        "classification": "PROVIDER_REVISABLE_SNAPSHOT",
        "provider": "kraken-futures",
        "metric": metric,
        "comparison_policy": "EXACT_IF_UNCHANGED_ELSE_RECORD_PROVIDER_RESTATEMENT",
        "release_authority": "IMMUTABLE_PROVIDER_SNAPSHOT_AT_PUBLICATION_CUTOFF",
        "git_overlap_role": "EARLIER_OBSERVED_PROVIDER_SNAPSHOT",
        "publication_cutoff_ms": publisher.AS_OF_MS,
        "publication_cutoff_utc": publisher.AS_OF_UTC,
        "frozen_source_required": True,
    }


def _qualify_restatement(asset, metric, contract, publisher):
    policy = contract["metrics"].get(metric)
    if not policy or policy.get("classification") != "PROVIDER_REVISABLE_SNAPSHOT" or policy.get("schema_version") != REVISABLE_SCHEMA:
        return False
    proof = asset.get("boundary_proof") or {}
    if proof.get("requested_cutoff_ms") != publisher.AS_OF_MS:
        raise RuntimeError(f"revisable overlap missing fixed cutoff proof: {metric}")
    if not asset.get("retrieved_at_utc"):
        raise RuntimeError(f"revisable overlap missing retrieval provenance: {metric}")
    source_route = asset.get("source_route") or proof.get("source_route") or ""
    if "futures.kraken.com/api/charts/v1/analytics" not in source_route:
        raise RuntimeError(f"revisable overlap has unexpected source route: {metric} {source_route}")
    if publisher.SOURCE is None or not getattr(publisher.SOURCE, "replay", False):
        raise RuntimeError(f"revisable overlap requires frozen replay source: {metric}")
    return True


def verify_git_overlap(assets, publisher=None, root=Path("."), diagnostics_limit=20):
    if publisher is None:
        import release_publisher as publisher

    contract = load_contract(Path(root) / SEMANTICS_PATH)
    declared = set(contract["metrics"])
    if declared != set(publisher.KRAKEN_METRICS):
        missing = sorted(set(publisher.KRAKEN_METRICS) - declared)
        extra = sorted(declared - set(publisher.KRAKEN_METRICS))
        raise RuntimeError(f"Kraken metric-semantics coverage mismatch missing={missing} extra={extra}")

    existing = defaultdict(dict)
    existing_semantics = {}

    def ingest(key, payload, path):
        semantics = payload.get("metric_semantics")
        if semantics:
            existing_semantics[key] = semantics
        for row in payload.get("records", []):
            old = existing[key].get(row[0])
            if old is not None:
                raise RuntimeError(f"duplicate Git archive timestamp: {key} {row[0]} {path}")
            existing[key][row[0]] = row

    for path in Path(root, "history").rglob("*.json"):
        if path.name in ("manifest.json", "release-manifest.json"):
            continue
        payload = json.loads(path.read_text())
        key = (payload.get("provider"), payload.get("symbol"), payload.get("interval"))
        ingest(key, payload, path)
    for path in Path(root, "derivatives/archive").rglob("*.json"):
        payload = json.loads(path.read_text())
        key = (payload.get("provider"), payload.get("instrument"), payload.get("metric"))
        ingest(key, payload, path)
    for path in Path(root, "options/archive").rglob("ETH-volatility-index-1h.json"):
        payload = json.loads(path.read_text())
        ingest(("deribit-options", "ETH", "DVOL-1h"), payload, path)

    matched = 0
    exact = 0
    cvd_semantic = 0
    restatements = 0
    restatements_by_series = defaultdict(int)
    diagnostics = []

    for asset in assets:
        key = (asset["provider"], asset["instrument"], asset["interval_or_metric"])
        expected = existing.get(key)
        if not expected:
            continue
        payload = json.loads(Path(asset["local_path"]).read_text())
        semantics = payload.get("metric_semantics")
        asset_restatements = 0
        for row in payload["records"]:
            old = expected.get(row[0])
            if old is None:
                continue
            matched += 1
            if old == row:
                exact += 1
                continue
            if key[0] == "kraken-futures" and key[2] == "cvd" and semantics and semantics.get("schema_version") == publisher.CVD_SEMANTICS_SCHEMA:
                if publisher.cvd_overlap_equal(old, row, existing_semantics.get(key), semantics):
                    cvd_semantic += 1
                    continue
            if key[0] == "kraken-futures" and key[2] in revisable_metrics(contract):
                if _qualify_restatement(asset, key[2], contract, publisher):
                    restatements += 1
                    asset_restatements += 1
                    restatements_by_series["/".join(key)] += 1
                    if len(diagnostics) < diagnostics_limit:
                        diagnostics.append((key, row[0], old, row))
                    continue
            raise RuntimeError(f"release/Git overlap conflict {key} {row[0]}")
        if key[0] == "kraken-futures" and key[2] in revisable_metrics(contract):
            asset["metric_semantics"] = release_semantics(contract, key[2], publisher)
            asset["overlap_reconciliation"] = {
                "provider_restatement_count": asset_restatements,
                "policy": "EXACT_IF_UNCHANGED_ELSE_RECORD_PROVIDER_RESTATEMENT",
                "unresolved_conflicts": 0,
            }

    if not matched:
        raise RuntimeError("release/Git overlap proof found no common rows")

    for key, timestamp, old, new in diagnostics:
        print(
            "PROVIDER_RESTATEMENT="
            + "/".join(key)
            + f" TS={timestamp} GIT={json.dumps(old,separators=(',',':'),ensure_ascii=False)}"
            + f" RELEASE={json.dumps(new,separators=(',',':'),ensure_ascii=False)}"
        )
    print(f"RELEASE_TO_GIT_OVERLAP=PASS matched={matched}")
    print(f"EXACT_MATCH_COUNT={exact}")
    print(f"CVD_SEMANTIC_MATCH_COUNT={cvd_semantic}")
    print(f"PROVIDER_RESTATEMENT_COUNT={restatements}")
    print(f"PROVIDER_RESTATEMENT_SERIES={json.dumps(dict(sorted(restatements_by_series.items())),separators=(',',':'))}")
    print("UNRESOLVED_CONFLICT_COUNT=0")
    print("DUPLICATE_EXPANSION=0")
    return {
        "matched": matched,
        "exact": exact,
        "cvd_semantic": cvd_semantic,
        "provider_restatements": restatements,
        "provider_restatements_by_series": dict(restatements_by_series),
        "unresolved_conflicts": 0,
    }
