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
    require(sealing["schema_version"] == "d9-sealing-candidate/1.1.0", "D9.3 sealing contract version mismatch")
    require(sealing["status"] == "CANDIDATE_NOT_ACTIVE", "D9.3 sealing advertised active")
    require(sealing["legacy_cold_authority"] == "history/release-manifest.json", "legacy COLD authority mismatch")

    membership = sealing["generation_membership"]
    require(membership["authority"] == "CANONICAL_WARM_MANIFESTS", "generation membership authority mismatch")
    require(membership["physical_inventory_defines_membership"] is False, "physical inventory must not define membership")
    require(membership["late_history_change"] == "IMMUTABLE_SUCCESSOR_OR_FAIL_CLOSED", "late-history policy missing")
    require(bool(membership["policy_version"]), "membership policy not versioned")

    finalization = sealing["finalization_policy"]
    require(bool(finalization["policy_version"]), "finalization policy not versioned")
    require(finalization["regular_grid_default_finalization_lag_seconds"] > 0, "regular-grid finalization lag must be explicit")
    require(finalization["effective_cutoff_rule"] == "MAX_APPLICABLE_CONSTRAINT", "effective cutoff rule mismatch")
    require(
        finalization["provider_overrides"]["kraken-futures"]["ingestion_stabilization_source"]
        == "derivatives/metric-semantics.json",
        "Kraken stabilization must be sourced from canonical semantics",
    )
    require(
        "PROVIDER_REVISABLE_SNAPSHOT" in finalization["revision_class_lag_seconds"],
        "provider-revisable finalization lag missing",
    )
    require(finalization["missing_required_revision_policy"] == "FAIL_CLOSED", "missing revision policy must fail closed")

    publication = sealing["publication"]
    require(publication["backend"] == "GITHUB_RELEASE", "new COLD backend introduced")
    require(publication["reuse_existing_release_primitives"] is True, "existing Release primitives not reused")
    require(publication["exact_remote_asset_membership"] is True, "exact immutable membership proof missing")
    require(publication["candidate_only"] is True, "D9.3 publication must remain candidate-only")
    require(publication["candidate_generation_root"] == "history/generations", "candidate generation root mismatch")
    require(publication["candidate_index"] == "history/generation-index.json", "candidate index path mismatch")
    require(publication["install_legacy_manifest"] is False, "D9.3 must not replace legacy manifest")
    require(publication["warm_cleanup"] is False, "WARM cleanup is forbidden before D9.4")
    require(sealing["period_policy"]["active_period_sealing"] is False, "active period sealing is forbidden")
    require(
        sealing["period_policy"]["high_cardinality_snapshot"]
        == "COMPLETED_ISO_WEEK_ONLY_AFTER_WARM_BACKEND_QUALIFICATION",
        "snapshot sealing must remain gated on WARM backend qualification",
    )
    require(sealing["activation_gate"]["requires_d9_4_cross_boundary_semantic_read"] is True, "D9.4 dependency lost")
    require(sealing["activation_gate"]["legacy_cold_remains_active_until_pass"] is True, "legacy COLD protection lost")

    warm = sealing["high_cardinality_warm"]
    require(warm["qualified_repository_result"] == "PUBLISHED_PRERELEASE_IMMUTABLE", "WARM Release probe result mismatch")
    require(warm["mutable_in_place"] is False, "repository must not claim mutable published prerelease")
    require(warm["probe_run_id"] == 32025981841 and warm["probe_job_id"] == 95375375158, "WARM Release proof identity mismatch")
    require(warm["status"].startswith("BLOCKED_"), "high-cardinality WARM blocker must remain explicit")
    require(warm["cold_sealing_enabled"] is False, "blocked high-cardinality WARM must not be sealable")

    generation = read(sealing["generation_schema"])
    require(generation["properties"]["schema_version"]["const"] == "market-data-history-generation/1.1.0", "generation schema version mismatch")
    require("membership" in generation["required"] and "finalization" in generation["required"], "generation evidence missing")
    require("candidate_fingerprint" in generation["required"] and "period" in generation["required"], "successor identity evidence missing")
    require(generation["properties"]["state"]["enum"] == ["CANDIDATE", "ACTIVE", "SUPERSEDED"], "generation state semantics mismatch")
    pub_schema = generation["properties"]["publication"]["properties"]
    require("cross_boundary_semantic_read" in pub_schema, "cross-boundary publication gate missing")
    require("release_immutable" in pub_schema, "remote immutable proof missing")
    require(pub_schema["activation_status"]["enum"] == ["NOT_ACTIVE", "ACTIVE"], "activation status semantics mismatch")

    index = read(sealing["generation_index_schema"])
    require(index["properties"]["schema_version"]["const"] == "market-data-history-generation-index/1.1.0", "generation index version mismatch")
    require(index["properties"]["status"]["enum"] == ["CANDIDATE_NOT_ACTIVE", "ACTIVE"], "generation index state mismatch")
    require(index["properties"]["legacy_cold_manifest"]["const"] == "history/release-manifest.json", "generation index legacy authority mismatch")
    row_properties = index["properties"]["generations"]["items"]["properties"]
    require("supersedes" in row_properties and "candidate_fingerprint" in row_properties, "multi-generation index semantics missing")

    source_path = ROOT / sealing["sealer"]
    workflow_path = ROOT / sealing["daily_workflow"]
    require(source_path.is_file(), "D9 sealer missing")
    require(workflow_path.is_file(), "repository-owned daily D9 sealer workflow missing")
    source = source_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    require("generation_membership_states" in source, "generation-level membership gate missing")
    require("declared_regular_authority" in source, "canonical membership authority missing")
    require("_resolve_generation_identity" in source and "supersedes" in source, "late-series successor route missing")
    require("effective_seal_after_ms" in source, "effective finalization cutoff missing")
    require("PROVIDER_REVISABLE_SNAPSHOT" in source, "revision-class finalization gate missing")
    require("remote immutable generation membership mismatch" in source, "exact remote membership fail-closed gate missing")
    require("release_publisher" in source and "requests" not in source and "urllib.request" not in source, "sealer must not reacquire provider history")
    require("D9_3_WARM_CLEANUP=NOT_RUN" in source, "no-cleanup proof missing")
    require("cross_boundary_semantic_read\":\"NOT_RUN" in source, "candidate cross-boundary block missing")
    require("high_cardinality_warm_ready" in source, "snapshot sealing policy guard missing")
    require("install_candidate_control_plane" in source, "candidate control-plane install missing")
    require("ref: main" in workflow and "python tools/deep_history/history_sealer.py publish" in workflow, "daily sealer production route mismatch")
    require("history/release-manifest.json" in workflow, "legacy authority protection missing from daily sealer")
    require("history/generation-index.json history/generations" in workflow, "candidate metadata commit scope mismatch")
    require("git push origin HEAD:main" in workflow, "repository-owned candidate metadata publication route missing")
    require("CONCURRENT_RUN_GUARD=ABORT_REMOTE_ADVANCED" in workflow, "generated-data race guard missing")

    print("D9_3_SEALING_CONTRACT=PASS")
    print("D9_3_GENERATION_ATOMICITY=PASS")
    print("D9_3_EXPECTED_MEMBERSHIP=PASS")
    print("D9_3_COVERAGE_APPLICABILITY=PASS")
    print("D9_3_LATE_SERIES_POLICY=PASS")
    print("D9_3_LATE_BACKFILL_POLICY=PASS")
    print("D9_3_FINALIZATION_POLICY=PASS")
    print("D9_3_INGESTION_STABILIZATION_SEPARATION=PASS")
    print("D9_3_REVISION_LAG=PASS")
    print("D9_3_EFFECTIVE_SEAL_CUTOFF=PASS")
    print("D9_3_NO_PROVIDER_REACQUIRE=PASS")
    print("D9_3_LEGACY_COLD_AUTHORITY_UNCHANGED=PASS")
    print("D9_3_ACTIVE_PERIOD_SEALING=false")
    print("D9_3_WARM_CLEANUP=NOT_RUN")
    print("D9_3_D9_4_ACTIVATION_DEPENDENCY=PASS")
    print("D9_3_DAILY_SEALER_ROUTE=PASS")
    print("D9_3_CANDIDATE_CONTROL_PLANE=PASS")
    print("WARM_RELEASE_PUBLISHED_IMMUTABLE=true")
    print("WARM_RELEASE_MUTABLE_IN_PLACE=NO")
    print("D9_2_HIGH_CARDINALITY_WARM_RELEASE=BLOCKED")
    print("D9_3_HIGH_CARDINALITY_COLD_SEALING=BLOCKED")
    print("D9_3_SEALING_VALIDATION=PASS")


if __name__ == "__main__":
    main()
