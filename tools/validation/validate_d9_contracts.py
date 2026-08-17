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
    require(contract["contract_version"] == "1.2.0", "D6 bridge contract version changed during D9.1")
    semantic = contract["semantic_resolution"]
    require(semantic["status"] == "ACTIVE", "active D6 semantic route is not ACTIVE")
    require(
        semantic["resolver"]["resolution_plan_schema"] == "market-data-resolution-plan/1.0.0",
        "D9.1 must not activate ResolutionPlan v2",
    )
    require(semantic["reader"]["input_authority"] == "ResolutionPlan", "reader authority changed")

    disabled = contract["disabled_providers"]["binance-usdm"]
    require(disabled["status"] == "DISABLED_BY_POLICY", "Binance USD-M policy changed")
    require(disabled["network_calls"] == 0, "Binance USD-M network policy weakened")
    require(disabled["signal_vote"] == "EXCLUDED", "Binance USD-M signal policy weakened")

    d9 = contract.get("d9_candidate")
    require(isinstance(d9, dict), "D9 candidate contract missing")
    require(d9["status"] == "D9_1_IMPLEMENTATION_CANDIDATE_NOT_ACTIVE", "unexpected D9.1 status")
    require(d9["source_authority"] == "EXACT_GITHUB_REPOSITORY_COMMIT", "source authority weakened")
    require(d9["single_spot_warm_root"] == "history", "Spot WARM root must remain history")
    require(d9["successor_route"]["second_resolver"] is False, "second resolver forbidden")
    require(d9["successor_route"]["second_reader_family"] is False, "second reader family forbidden")
    require(
        d9["qualification_environment"]["canonical_repository_physical_qualification"]
        == "GITHUB_ACTIONS_ACTIONS_CHECKOUT",
        "canonical physical qualification environment mismatch",
    )
    require(d9["activation_gate"]["d9_3_cold_activation_requires_d9_4"] is True, "D9.3/D9.4 dependency lost")

    contracts = d9["successor_contracts"]
    expected = {
        "capability_index_schema": ("schema/capability-index-v2.schema.json", "2.0.0"),
        "resolution_plan_schema": ("schema/market-data-resolution-plan-v2.schema.json", "market-data-resolution-plan/2.0.0"),
        "collection_run_ledger_schema": ("schema/collection-run-ledger.schema.json", "market-data-collection-run-ledger/1.0.0"),
        "provider_revision_schema": ("schema/provider-revision.schema.json", "market-data-provider-revision/1.0.0"),
        "history_generation_schema": ("schema/history-generation.schema.json", "market-data-history-generation/1.0.0"),
    }
    for key, (path, version) in expected.items():
        require(contracts.get(key) == path, f"D9 contract path mismatch: {key}")
        schema = read(path)
        require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"schema draft mismatch: {path}")
        require(schema.get("$id", "").endswith(path), f"schema id mismatch: {path}")
        schema_version = schema.get("properties", {}).get("schema_version", {}).get("const")
        require(schema_version == version, f"schema version mismatch: {path}")

    plan = read("schema/market-data-resolution-plan-v2.schema.json")
    storages = set(plan["$defs"]["segment"]["properties"]["storage"]["enum"])
    require(
        storages == {"GITHUB_RELEASE_ASSET", "GIT_WARM_RESOURCE", "GITHUB_RELEASE_WARM_ASSET", "HOT_CURRENT_RESOURCE"},
        "ResolutionPlan v2 storage semantics incomplete",
    )
    series_kinds = set(plan["$defs"]["seriesKind"]["enum"])
    require("OPTION_SURFACE" in series_kinds and "ORDER_BOOK_SNAPSHOT" in series_kinds, "sampled series kinds missing")

    capability = read("schema/capability-index-v2.schema.json")
    required_profile = set(capability["properties"]["profiles"]["additionalProperties"]["required"])
    require("warm_manifest_path" in required_profile, "warm_manifest_path successor semantic missing")
    require("plan_schema" in required_profile, "plan schema discriminator missing")

    print("D9_1_CONTRACTS=PASS")
    print("D9_1_SCHEMA_REGRESSION=PASS")
    print("D6_V1_COMPATIBILITY=PASS")
    print("ACTIVE_ROUTE_UNCHANGED=PASS")
    print("D9_1_CONTRACT_VALIDATION=PASS")


if __name__ == "__main__":
    main()
