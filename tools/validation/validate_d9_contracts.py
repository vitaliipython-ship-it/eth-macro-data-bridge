from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    contract = read("bridge-contract.json")
    require(contract["contract_version"] == "1.3.0", "unexpected bridge contract version")
    semantic = contract["semantic_resolution"]
    require(semantic["status"] == "ACTIVE", "active D6 semantic route is not ACTIVE")
    require(
        semantic["resolver"]["resolution_plan_schema"] == "market-data-resolution-plan/1.0.0",
        "D9 must not activate ResolutionPlan v2 before its activation gate",
    )
    require(semantic["reader"]["input_authority"] == "ResolutionPlan", "reader authority changed")

    disabled = contract["disabled_providers"]["binance-usdm"]
    require(disabled["status"] == "DISABLED_BY_POLICY", "Binance USD-M GitHub runtime policy changed")
    require(disabled["network_calls"] == 0, "Binance USD-M GitHub runtime network policy weakened")
    require(disabled["signal_vote"] == "EXCLUDED", "Binance USD-M GitHub runtime signal policy weakened")
    require(
        disabled["runtime_scope"] == "CURRENT_GITHUB_HOSTED_ACQUISITION_ONLY",
        "Binance USD-M disablement must be scoped to current GitHub-hosted acquisition runtime",
    )
    require(
        disabled["target_state"] == "REQUIRED_FUTURE_ACTIVE_PROVIDER_VIA_QUALIFIED_D8_VPS_RUNTIME",
        "Binance USD-M future VPS target missing",
    )
    require(disabled["vps_runtime_status"] == "NOT_ACTIVE", "D9 must not activate Binance USD-M VPS runtime")
    require(disabled["historical_archive_preserved"] is True, "historical Binance USD-M evidence must remain preserved")
    require(
        disabled["provider_policy_transition"] == "SEPARATE_VERSIONED_CONTROL_PLANE_TRANSITION_AFTER_D8_QUALIFICATION",
        "Binance USD-M activation must remain a separate versioned transition",
    )

    d9 = contract.get("d9_candidate")
    require(isinstance(d9, dict), "D9 candidate contract missing")
    require(
        d9["status"] == "SOURCE_CANDIDATE_NOT_ACTIVE_WITH_PUBLICATION_PORTABILITY_GAP_IDENTIFIED",
        "unexpected D9 candidate status",
    )
    require(d9["target_contract_status"] == "ACCEPTED", "D9 target contract status mismatch")
    require(
        d9["source_implementation_status"] == "COMPLETE_WITH_PUBLICATION_PORTABILITY_GAP_IDENTIFIED",
        "D9 source status must expose publication portability gap",
    )
    require(d9["physical_canonical_d8_publication_status"] == "NOT_QUALIFIED", "D8 canonical publication status changed")
    require(d9["authority_activation_status"] == "NOT_ACTIVE", "D9 authority activated unexpectedly")
    require(d9["source_authority"] == "EXACT_GITHUB_REPOSITORY_COMMIT", "source authority weakened")
    require(d9["single_spot_warm_root"] == "history", "Spot WARM root must remain history for current profile")
    require(d9["lifecycle"]["residence_roles_are_backend_neutral"] is True, "lifecycle roles leaked backend semantics")
    require(d9["successor_route"]["second_resolver"] is False, "second resolver forbidden")
    require(d9["successor_route"]["second_reader_family"] is False, "second reader family forbidden")
    require(d9["successor_route"]["physical_backend_selected_internally"] is True, "consumer must not select backend")
    require(
        d9["qualification_environment"]["canonical_repository_physical_qualification"]
        == "GITHUB_ACTIONS_ACTIONS_CHECKOUT",
        "canonical physical qualification environment mismatch",
    )
    require(d9["activation_gate"]["d9_3_cold_activation_requires_d9_4"] is True, "D9.3/D9.4 dependency lost")
    require(d9["activation_gate"]["canonical_d8_publication_required_before_d8_origin_authority"] is True, "canonical D8 publication gate missing")

    d8 = d9["d8_dependency"]
    require(d8["status"] == "CAPTURED_REQUIRED", "D8 VPS dependency not captured")
    require(d8["task"] == "ETH-D8", "unexpected D8 task identity")
    require(d8["role"] == "VPS_NEAR_REAL_TIME_ACQUISITION_RUNTIME", "D8 runtime responsibility mismatch")
    require(d8["target_collection_cadence"] == "APPROX_5_MINUTES", "D8 target cadence mismatch")
    require(d8["github_actions_is_primary_5m_acquisition_scheduler"] is False, "GitHub Actions must not be the primary 5m acquisition scheduler")
    require(d8["vps_is_market_data_authority"] is False, "VPS runtime must not become market-data authority")
    target = d8["binance_usdm"]
    require(target["github_runtime"] == "DISABLED_BY_POLICY", "Binance USD-M GitHub runtime state mismatch")
    require(target["vps_target"] == "REQUIRED", "Binance USD-M VPS target must be required")
    require(target["vps_runtime"] == "NOT_ACTIVE", "Binance USD-M VPS route activated inside D9")
    require(target["active_provider"] is False, "Binance USD-M active provider transition occurred before D8 qualification")
    require(target["historical_evidence"] == "PRESERVED", "Binance USD-M historical evidence policy weakened")
    required_d8_proofs = {
        "VPS_PROVIDER_CONNECTIVITY",
        "BINANCE_USDM_5M_COLLECTION",
        "RUNTIME_RESTART_RECOVERY",
        "FRESHNESS_SEMANTICS",
        "COLLECTION_GAP_SEMANTICS",
        "HOT_TRANSPORT_INTEGRITY",
        "NO_DIRECT_AGENT_PROVIDER_ACCESS",
        "NO_SECOND_DATA_AUTHORITY",
    }
    require(set(target["activation_requires"]) == required_d8_proofs, "D8 activation proof set mismatch")

    hot = d9["hot_source_seam"]
    require(hot["status"] == "CONTRACT_READY_NOT_ACTIVE", "VPS HOT seam status mismatch")
    require(hot["physical_location"] == "CANONICAL_AUTHORITY_RESOLVED", "HOT location must remain authority-resolved")
    require(hot["transport"] == "CANONICAL_AUTHORITY_RESOLVED", "HOT transport must remain authority-resolved")
    require(hot["qualified_runtime_hot_allowed"] is True, "qualified runtime HOT source not supported")
    require(hot["hardcode_vps_hostname"] is False and hot["hardcode_vps_filesystem_path"] is False, "VPS details must not be hard-coded")
    require(hot["agent_direct_provider_access"] is False, "agent direct provider access forbidden")
    require(hot["git_commit_per_observation_hot_transport"] is False, "Git commits must not be the online HOT transport")

    portability = contract["storage_portability"]
    require(portability["contract_id"] == "ETH-MARKET-DATA-STORAGE-PORTABILITY-V2", "portability contract id mismatch")
    require(portability["market_data_semantic_authority"] == "ETH_MACRO_DATA_BRIDGE", "semantic authority mismatch")
    require(portability["current_physical_backend_profile"] == "GITHUB_FIRST_V1", "current backend profile mismatch")
    require(portability["physical_backend_is_semantic_contract"] is False, "physical backend became semantic contract")
    require(portability["execution_plane_is_semantic_authority"] is False, "execution plane became semantic authority")
    require(portability["vps_is_market_data_authority"] is False, "VPS became semantic authority")
    require(portability["storage_migration_changes_semantic_interface"] is False, "storage migration changes agent interface")
    require(portability["storage_migration_changes_observation_id"] is False, "storage migration changes observation id")
    require(portability["storage_migration_changes_series_id"] is False, "storage migration changes series id")
    require(portability["d8_runtime_state_backend"] == "SQLITE_WAL", "D8 runtime state backend changed")
    require(portability["d8_runtime_state_role"] == "OPERATIONAL_RUNTIME_STATE", "D8 SQLite role mismatch")
    require(portability["d8_runtime_state_is_history_authority"] is False, "D8 SQLite became history authority")
    require(portability["local_filesystem_write_sufficient_for_production_ack"] is False, "local write incorrectly sufficient for production ACK")
    require(portability["canonical_publication_ack_required"] is True, "canonical publication ACK gate missing")
    require(portability["high_cardinality_warm_backend"] == "BLOCKED_VERSIONED_DECISION", "high-cardinality backend prematurely selected")
    require(portability["postgres_implemented"] is False, "PostgreSQL implemented prematurely")
    require(portability["postgres_migration_path_defined"] is True, "PostgreSQL migration path missing")
    require(portability["existing_server_postgres_reuse_decision"] == "NOT_MADE", "server PostgreSQL reuse decided prematurely")
    require(portability["git_commit_per_observation"] is False, "per-observation Git publication forbidden")
    require(portability["second_resolver"] is False and portability["second_reader"] is False, "second consumer family forbidden")
    require(portability["second_history_authority"] is False, "second market-data authority forbidden")
    require(portability["permanent_vps_d9_warm_required"] is False, "permanent VPS D9 WARM incorrectly required")

    families = {row["family"]: row["history_mode"] for row in d9["binance_usdm_target_families"]}
    minimum_families = {
        "OHLCV_5M",
        "OHLCV_PROVIDER_NATIVE_HIGHER_TF",
        "MARK_PRICE",
        "INDEX_PRICE",
        "PREMIUM_BASIS",
        "OPEN_INTEREST",
        "FUNDING",
        "ORDER_BOOK_DEPTH_SNAPSHOT",
    }
    require(minimum_families <= set(families), "Binance USD-M target capability families incomplete")
    require(families["ORDER_BOOK_DEPTH_SNAPSHOT"] == "FORWARD_ONLY", "order-book history must not invent backfill")

    contracts = d9["successor_contracts"]
    expected = {
        "capability_index_schema": ("schema/capability-index-v2.schema.json", "2.0.0"),
        "resolution_plan_schema": ("schema/market-data-resolution-plan-v2.schema.json", "market-data-resolution-plan/2.0.0"),
        "collection_run_ledger_schema": ("schema/collection-run-ledger.schema.json", "market-data-collection-run-ledger/1.0.0"),
        "provider_revision_schema": ("schema/provider-revision.schema.json", "market-data-provider-revision/1.0.0"),
        "history_generation_schema": ("schema/history-generation.schema.json", "market-data-history-generation/1.1.0"),
        "publication_batch_schema": ("schema/history-publication-batch-v1.schema.json", "market-data-history-publication-batch/1.0.0"),
    }
    for key, (path, version) in expected.items():
        require(contracts.get(key) == path, f"D9 contract path mismatch: {key}")
        schema = read(path)
        require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"schema draft mismatch: {path}")
        require(schema.get("$id", "").endswith(path), f"schema id mismatch: {path}")
        schema_version = schema.get("properties", {}).get("schema_version", {}).get("const")
        require(schema_version == version, f"schema version mismatch: {path}")

    ledger = read("schema/collection-run-ledger.schema.json")
    run_required = set(ledger["properties"]["runs"]["items"]["required"])
    require(
        {"expected_schedule_at", "collection_started_at", "collection_completed_at", "provider_timestamp_at", "known_at", "retrieved_at", "freshness"}
        <= run_required,
        "collection timing/freshness provenance incomplete",
    )
    statuses = set(ledger["properties"]["runs"]["items"]["properties"]["status"]["enum"])
    require("COLLECTION_GAP" in statuses, "collection gap semantics missing")

    plan = read("schema/market-data-resolution-plan-v2.schema.json")
    segment = plan["$defs"]["segment"]["properties"]
    storages = set(segment["storage"]["enum"])
    require(
        storages == {"GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE", "GITHUB_RELEASE_WARM_ASSET", "HOT_CURRENT_RESOURCE"},
        "ResolutionPlan v2 compatibility storage aliases incomplete",
    )
    require(segment["storage"].get("deprecated") is True, "technology-specific storage must be a deprecated compatibility alias")
    for field in ("residence_role", "adapter_profile", "resource_ref", "integrity_evidence"):
        require(field in segment, f"storage-neutral ResolutionPlan field missing: {field}")
    require(plan["$defs"]["residenceRole"]["enum"] == ["HOT", "WARM", "COLD"], "residence roles mismatch")
    hot_descriptor = plan["$defs"]["hotPhysicalDescriptor"]
    require(hot_descriptor["properties"]["locator_authority"]["const"] == "CANONICAL_CONTROL_PLANE", "HOT locator authority weakened")
    require(hot_descriptor["properties"]["transport_authority"]["const"] == "CANONICAL_CONTROL_PLANE", "HOT transport authority weakened")
    series_kinds = set(plan["$defs"]["seriesKind"]["enum"])
    require("OPTION_SURFACE" in series_kinds and "ORDER_BOOK_SNAPSHOT" in series_kinds, "sampled series kinds missing")

    publication = read("schema/history-publication-batch-v1.schema.json")
    publication_required = set(publication["required"])
    require(
        {"batch_id", "target_residence_role", "member_count", "member_observation_ids", "members", "membership_sha256", "payload_sha256"}
        <= publication_required,
        "PublicationBatch identity incomplete",
    )
    require(publication["properties"]["target_residence_role"]["const"] == "WARM", "PublicationBatch target role mismatch")
    require("backend_profile" not in publication["properties"], "logical PublicationBatch must exclude backend profile")
    require("publication_attempt_id" not in publication["properties"], "logical PublicationBatch must exclude attempt identity")
    require(portability["resolution_plan_v2_runtime_migration"] == "PENDING_PRE_ACTIVATION", "ResolutionPlan v2 runtime migration overstated")
    require(portability["capability_routing_single_source"] is True, "capability routing is not single-source")
    require(portability["d8_origin_canonical_warm_representation"] == "NEXT_TASK_DECISION_GATE_DEFINED", "canonical WARM representation gate missing")
    require(portability["github_publication_concurrency_contract"] == "DEFINED_AS_NEXT_TASK_GATE", "GitHub CAS gate missing")

    forwarding = read("contracts/d8-d9-forwarding-v1.json")
    require(forwarding["contract_id"] == "ETH-MARKET-DATA-STORAGE-PORTABILITY-V2", "forwarding portability identity mismatch")
    require(forwarding["publication_batch"]["partial_ack"] is False, "partial batch ACK forbidden")
    require(forwarding["publication_batch"]["git_commit_per_observation"] is False, "per-observation Git publication forbidden")
    require(forwarding["canonical_publication_ack"]["required_before_pending_to_forwarded"] is True, "canonical ACK binding missing")
    require(forwarding["resolver_visibility"]["resolver_scans_arbitrary_vps_filesystem"] is False, "resolver must not scan arbitrary VPS filesystem")
    require(forwarding["future_physical_acceptance"]["local_warm_root_physical_test_next"] is False, "qualification-only local WARM root must not be next production proof")

    capability = read("schema/capability-index-v2.schema.json")
    profile_schema = capability["properties"]["profiles"]["additionalProperties"]
    required_profile = set(profile_schema["required"])
    require("warm_manifest_path" in required_profile, "warm_manifest_path successor semantic missing")
    require("plan_schema" in required_profile, "plan schema discriminator missing")
    require("hot_source_policy" in required_profile, "HOT source policy missing from capability v2")
    hot_policy = profile_schema["properties"]["hot_source_policy"]["properties"]
    require("QUALIFIED_VPS" in hot_policy["runtime_class"]["enum"], "qualified VPS runtime class missing")
    require("QUALIFIED_RUNTIME_REQUIRED" in hot_policy["status"]["enum"], "qualified runtime activation state missing")

    print("D9_1_CONTRACTS=PASS")
    print("D9_1_SCHEMA_REGRESSION=PASS")
    print("D6_V1_COMPATIBILITY=PASS")
    print("ACTIVE_ROUTE_UNCHANGED=PASS")
    print("STORAGE_PORTABILITY_CONTRACT=PASS")
    print("SEMANTIC_AUTHORITY_SEPARATED_FROM_BACKEND=PASS")
    print("D8_SQLITE_OPERATIONAL_ONLY=PASS")
    print("PUBLICATION_BATCH_MODEL_DEFINED=PASS")
    print("CANONICAL_PUBLICATION_ACK=PASS")
    print("RESOLUTIONPLAN_V2_ROLE_ADAPTER_SEPARATION=PASS")
    print("D8_ORIGIN_RESOLVER_GAP_RECONCILED=PASS")
    print("POSTGRES_IMPLEMENTED=false")
    print("POSTGRES_MIGRATION_PATH_DEFINED=true")
    print("D9_1_CONTRACT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
