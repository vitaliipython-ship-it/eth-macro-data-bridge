from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> None:
    bridge = read("bridge-contract.json")
    sealing = read("contracts/d9-sealing-candidate.json")
    require(bridge["contract_version"] == "1.2.0", "active D6 bridge contract version changed")
    require(bridge["semantic_resolution"]["status"] == "ACTIVE", "active D6 semantic route changed")
    require(
        bridge["semantic_resolution"]["physical_authority"]["cold_manifest"] == "history/release-manifest.json",
        "legacy COLD authority changed before D9.4",
    )
    require(sealing["status"] == "CANDIDATE_NOT_ACTIVE", "D9.3 sealing advertised active")
    require(sealing["legacy_cold_authority"] == "history/release-manifest.json", "legacy COLD authority mismatch")
    require(sealing["publication"]["backend"] == "GITHUB_RELEASE", "new COLD backend introduced")
    require(sealing["publication"]["reuse_existing_release_primitives"] is True, "existing Release primitives not reused")
    require(sealing["publication"]["candidate_only"] is True, "D9.3 publication must remain candidate-only")
    require(sealing["publication"]["install_legacy_manifest"] is False, "D9.3 must not replace legacy manifest")
    require(sealing["publication"]["warm_cleanup"] is False, "WARM cleanup is forbidden before D9.4")
    require(sealing["period_policy"]["active_period_sealing"] is False, "active period sealing is forbidden")
    require(sealing["activation_gate"]["requires_d9_4_cross_boundary_semantic_read"] is True, "D9.4 dependency lost")
    require(sealing["activation_gate"]["legacy_cold_remains_active_until_pass"] is True, "legacy COLD protection lost")

    warm = sealing["high_cardinality_warm"]
    require(warm["qualified_repository_result"] == "PUBLISHED_PRERELEASE_IMMUTABLE", "WARM Release probe result mismatch")
    require(warm["mutable_in_place"] is False, "repository must not claim mutable published prerelease")
    require(warm["probe_run_id"] == 32025981841 and warm["probe_job_id"] == 95375375158, "WARM Release proof identity mismatch")
    require(warm["status"].startswith("BLOCKED_"), "high-cardinality WARM blocker must remain explicit")

    generation = read(sealing["generation_schema"])
    require(generation["properties"]["state"]["enum"] == ["CANDIDATE", "ACTIVE", "SUPERSEDED"], "generation state semantics mismatch")
    publication = generation["properties"]["publication"]["properties"]
    require("cross_boundary_semantic_read" in publication, "cross-boundary publication gate missing")
    require("release_immutable" in publication, "remote immutable proof missing")
    require(publication["activation_status"]["enum"] == ["NOT_ACTIVE", "ACTIVE"], "activation status semantics mismatch")

    index = read(sealing["generation_index_schema"])
    require(index["properties"]["status"]["enum"] == ["CANDIDATE_NOT_ACTIVE", "ACTIVE"], "generation index state mismatch")
    require(index["properties"]["legacy_cold_manifest"]["const"] == "history/release-manifest.json", "generation index legacy authority mismatch")

    source = (ROOT / sealing["sealer"]).read_text(encoding="utf-8")
    require("history-grid-v1-" in source and "history-snapshots-v1-" in source, "generation naming policy missing")
    require("D9_3_WARM_CLEANUP=NOT_RUN" in source, "no-cleanup proof missing")
    require("cross_boundary_semantic_read\":\"NOT_RUN" in source, "candidate cross-boundary block missing")

    print("D9_3_SEALING_CONTRACT=PASS")
    print("D9_3_LEGACY_COLD_AUTHORITY_UNCHANGED=PASS")
    print("D9_3_ACTIVE_PERIOD_SEALING=false")
    print("D9_3_WARM_CLEANUP=NOT_RUN")
    print("D9_3_D9_4_ACTIVATION_DEPENDENCY=PASS")
    print("WARM_RELEASE_PUBLISHED_IMMUTABLE=true")
    print("WARM_RELEASE_MUTABLE_IN_PLACE=NO")
    print("D9_2_HIGH_CARDINALITY_WARM_RELEASE=BLOCKED")
    print("D9_3_SEALING_VALIDATION=PASS")


if __name__ == "__main__":
    main()
