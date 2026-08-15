from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import kraken_overlap_probe as probe
import release_publisher as publisher
from release_overlap_policy import verify_git_overlap


def main():
    assets = []
    requests = 0
    source_route = "https://futures.kraken.com/api/charts/v1/analytics/:symbol/:analytics_type"
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for instrument in probe.DEFAULT_INSTRUMENTS:
            for metric in probe.DEFAULT_METRICS:
                git_rows, _ = probe.all_archive_rows(instrument, metric, publisher.AS_OF_MS)
                if not git_rows:
                    raise RuntimeError(f"missing Git overlap series: {instrument}/{metric}")
                provider_rows, pages = probe.fetch_range(instrument, metric, git_rows[0][0], publisher.AS_OF_MS)
                requests += pages
                metric_semantics = None
                if metric == "cvd":
                    provider_rows, metric_semantics = publisher.canonicalize_kraken_cvd(provider_rows, git_rows[0][0] // 1000)
                path = temp_root / f"{instrument}--{metric}.json"
                payload = {
                    "schema_version": publisher.SCHEMA,
                    "provider": "kraken-futures",
                    "instrument": instrument,
                    "interval_or_metric": metric,
                    "records": provider_rows,
                }
                if metric_semantics:
                    payload["metric_semantics"] = metric_semantics
                path.write_text(json.dumps(payload, separators=(",", ":")))
                assets.append({
                    "provider": "kraken-futures",
                    "instrument": instrument,
                    "interval_or_metric": metric,
                    "local_path": str(path),
                    "boundary_proof": {
                        "requested_cutoff_ms": publisher.AS_OF_MS,
                        "source_route": source_route,
                    },
                    "source_route": source_route,
                    "retrieved_at_utc": "LIVE_POLICY_QUALIFICATION",
                })

        original_source = publisher.SOURCE
        try:
            publisher.SOURCE = SimpleNamespace(replay=True)
            result = verify_git_overlap(assets, publisher=publisher, root=Path("."), diagnostics_limit=20)
        finally:
            publisher.SOURCE = original_source

    if result["unresolved_conflicts"] != 0:
        raise RuntimeError("live overlap policy qualification left unresolved conflicts")
    print(f"LIVE_POLICY_QUALIFICATION_REQUESTS={requests}")
    print(f"LIVE_POLICY_QUALIFICATION_MATCHED={result['matched']}")
    print(f"LIVE_POLICY_QUALIFICATION_EXACT={result['exact']}")
    print(f"LIVE_POLICY_QUALIFICATION_CVD_SEMANTIC={result['cvd_semantic']}")
    print(f"LIVE_POLICY_QUALIFICATION_PROVIDER_RESTATEMENTS={result['provider_restatements']}")
    print("LIVE_POLICY_QUALIFICATION_UNRESOLVED_CONFLICTS=0")
    print("LIVE_POLICY_QUALIFICATION=PASS")


if __name__ == "__main__":
    main()
