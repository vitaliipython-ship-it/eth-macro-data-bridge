# Handoff G1 durable L2 contract — R01

## Назначение

Этот файл — repository resume для `ETH-LIQUIDITY-G1-DURABLE-L2-OBSERVATION-CONTRACT-AND-LEGACY-COMPATIBILITY-IMPLEMENTATION-R01`. Каноническая программа продолжения находится в `docs/semantics/deep-liquidity-program-map-v1.md`; этот handoff не заменяет program map.

## Fresh base

```text
FRESH_BASE_HEAD=39ebb6b0aa45c75e05df9505c5754c93556396f4
FRESH_BASE_TREE=519559577cfd4ec69e19caf5195e69fd8b30cc5c
DRIFT_FROM_PREDECESSOR_FREEZE=GENERATED_DATA_ONLY
```

## Feature branch / publication

```text
FEATURE_BRANCH=agent/g1-deep-l2-durability-contract-r01
BRANCH_HEAD=PENDING_PUBLICATION
BRANCH_TREE=PENDING_PUBLICATION
PR_NUMBER=PENDING
PR_HEAD_SHA=PENDING
PR_CI=PENDING
PR_MERGED=NO
```

## Exact path map

```text
PATH_COUNT=9

MODIFY AGENTS.md
MODIFY bridge-contract.json
MODIFY tools/validation/validate_repository.py

ADD docs/semantics/deep-liquidity-program-map-v1.md
ADD contracts/liquidity-durable-l2-observation-v1.json
ADD docs/semantics/liquidity-durable-l2-observation-v1.md
ADD tools/validation/validate_liquidity_g1_durability.py
ADD tests/deep_history/test_liquidity_g1_durability.py
ADD docs/handoffs/liquidity-g1-durable-l2-contract-r01.md
```

## G1 authority

```text
G1_CONTRACT_ID=ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1
G1_CONTRACT_PATH=contracts/liquidity-durable-l2-observation-v1.json
CANONICAL_PROGRAM_MAP=docs/semantics/deep-liquidity-program-map-v1.md
HISTORY_FAMILY=liquidity.orderbook-snapshots
REQUEST_RESOURCE_DURABILITY=EPHEMERAL_ONLY
PROVIDER_NETWORK_CALLS=0
```

## Qualification

```text
TARGETED_TESTS=PENDING
CANONICAL_VALIDATION=PENDING
```

## Scope proof

Writer/runtime/provider/reader/workflow semantics не изменяются этим G1 candidate. `src/collector.py`, `src/intelligence.py`, S2 adapters, S3 executor, current-data transport/promotion, `resolution_v2`, `history_access_v2`, hourly/current-data workflows остаются byte-identical base.

## Resume

```text
CURRENT_STAGE=G1
LAST_CONFIRMED_GATE=G1_SOURCE_CANDIDATE_PREPUBLICATION
NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK
BLOCKERS=PENDING_BRANCH_AND_PR_QUALIFICATION
OUT_OF_SCOPE=G2-A;G2-B;D8;D9;VPS;AIFE_SERVER;DB-G;PROFILE_FEATURES;BACKTEST_IMPLEMENTATION
```
