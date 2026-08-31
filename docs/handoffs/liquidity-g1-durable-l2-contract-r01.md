# Handoff G1 durable L2 contract — R01

## Назначение

Этот файл — repository resume для `ETH-LIQUIDITY-G1-DURABLE-L2-OBSERVATION-CONTRACT-AND-LEGACY-COMPATIBILITY-IMPLEMENTATION-R01`. Каноническая программа продолжения находится в `docs/semantics/deep-liquidity-program-map-v1.md`; этот handoff не заменяет program map.

## Machine identity

```text
TASK_FAMILY=ETH-LIQUIDITY-DEEP-BOOK-CANONICAL-MARKET-DATA-FOUNDATION
TASK_ID=ETH-LIQUIDITY-G1-DURABLE-L2-OBSERVATION-CONTRACT-AND-LEGACY-COMPATIBILITY-IMPLEMENTATION-R01
RUN_ID=G1-R01-STRICT-RESUME-CURRENTIZATION-AND-SAME-PR-REQUALIFICATION-R02
```

## Fresh base

```text
FRESH_BASE_HEAD=39ebb6b0aa45c75e05df9505c5754c93556396f4
FRESH_BASE_TREE=519559577cfd4ec69e19caf5195e69fd8b30cc5c
DRIFT_FROM_PREDECESSOR_FREEZE=GENERATED_DATA_ONLY
```

`FRESH_BASE_HEAD`/`FRESH_BASE_TREE` фиксируют qualified G1 base, на котором сформирован 9-path candidate. Текущий `main` перед owner integration всегда перечитывается из remote; generated-data-only advance сам по себе не требует переписывания G1 candidate.

## Feature branch / publication

```text
FEATURE_BRANCH=agent/g1-deep-l2-durability-contract-r01
QUALIFIED_CANDIDATE_HEAD_BEFORE_PR=b3f3f28d7d7b4d16b54d76048f57b1cc36388d61
QUALIFIED_CANDIDATE_TREE_BEFORE_PR=f4526460009f0f38b9d1937cee52896b89f50be8
CURRENT_BRANCH_HEAD_AUTHORITY=READ_FEATURE_BRANCH_REF
CURRENT_BRANCH_TREE_AUTHORITY=READ_CURRENT_BRANCH_HEAD_TREE
CURRENT_PR_CI_AUTHORITY=READ_EXACT_CURRENT_PR_HEAD_CHECKS
PR_NUMBER=385
PR_URL=https://github.com/vitaliipython-ship-it/eth-macro-data-bridge/pull/385
PR_HEAD_AT_CREATION=b3f3f28d7d7b4d16b54d76048f57b1cc36388d61
PR_HEAD_TREE_AT_CREATION=f4526460009f0f38b9d1937cee52896b89f50be8
PR_CHANGED_FILES_AT_CREATION=9
PR_MERGED=NO
```

Authoritative current head/tree не записываются самоссылочным SHA в commit, который включает этот handoff. Текущие feature-branch head/tree и CI читаются по machine authority выше. Exact квалифицированный predecessor head/tree и PR head-at-creation остаются фиксированным evidence.

## Pre-repair PR evidence

```text
PRE_REPAIR_PR_HEAD=dc0f65719b0fd864f9c0c93c615b39f8fe3c749e
PRE_REPAIR_PR_HEAD_TREE=2b23b5cb8dab45a9d19d28f15cea878a4ef0180e
PRE_REPAIR_SYNTHETIC_INTEGRATION_SHA=c53f87fc0bbae72824a447778718e65b88a36b0d

PRE_REPAIR_VALIDATE_RUN_ID=33396037433
PRE_REPAIR_VALIDATE_CONCLUSION=SUCCESS

PRE_REPAIR_D8_RUN_ID=33396037397
PRE_REPAIR_D8_CONCLUSION=SUCCESS

PRE_REPAIR_FRESH_CURRENT_RUN_ID=33396037440
PRE_REPAIR_FRESH_CURRENT_CONCLUSION=SKIPPED_EXPECTED
```

Это predecessor evidence, а не вечная current authority. После любого successor commit exact PR head, synthetic integration и checks перечитываются из GitHub remote.

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

Base→candidate compare и PR read-back подтверждают ровно 9 changed files. Writer/runtime/provider/reader/workflow paths в candidate отсутствуют.

## G1 authority

```text
G1_CONTRACT_ID=ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1
G1_CONTRACT_PATH=contracts/liquidity-durable-l2-observation-v1.json
CANONICAL_PROGRAM_MAP=docs/semantics/deep-liquidity-program-map-v1.md
BRIDGE_DISCOVERY=semantic_contracts.liquidity_durable_l2
HISTORY_FAMILY=liquidity.orderbook-snapshots
REQUEST_RESOURCE_DURABILITY=EPHEMERAL_ONLY
UNDERLYING_MARKET_OBSERVATION_DURABILITY=ELIGIBLE_FOR_CANONICAL_HISTORY
HOURLY_HISTORY_TARGET_BPS=500
PROVIDER_NETWORK_CALLS=0
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
G2_WRITER_IMPLEMENTED=NO
G2_READER_IMPLEMENTED=NO
```

## Qualification

Перед созданием PR exact head `b3f3f28d7d7b4d16b54d76048f57b1cc36388d61` прошёл canonical branch qualification:

```text
VALIDATE_REPOSITORY_RUN_ID=33395351415
VALIDATE_REPOSITORY_CONCLUSION=SUCCESS
PREVIOUS_FULL_9_PATH_VALIDATE_RUN_ID=33395106216
PREVIOUS_FULL_9_PATH_VALIDATE_CONCLUSION=SUCCESS
D8_QUALIFICATION_RUN_ID=33395106151
D8_QUALIFICATION_CONCLUSION=SUCCESS
TARGETED_G1_VALIDATOR=PASS_VIA_VALIDATE_REPOSITORY
DEEP_HISTORY_G1_TESTS=PASS_VIA_EXISTING_TEST_DISCOVERY
CANONICAL_BRANCH_VALIDATION=PASS
PROVIDER_NETWORK_PROBES=0
```

Pre-repair exact PR head `dc0f65719b0fd864f9c0c93c615b39f8fe3c749e` также прошёл фактический PR CI, зафиксированный в `Pre-repair PR evidence`. После resume-currentization terminal gate остаётся actual GitHub checks для текущего exact PR head: predecessor green не подменяет fresh read-back.

## Scope proof

G1 не меняет physical writer/runtime semantics. `src/collector.py`, `src/intelligence.py`, S1/S2/S3 runtime, current-data transport/promotion, `resolution_v2`, `history_access_v2`, hourly/current-data workflows остаются byte-identical base. Legacy Binance Spot fixed `limit=100` не retired в G1; это G2-A. Exact S3 request resource остаётся `EPHEMERAL_ONLY`; G1 только определяет durability underlying coherent market observation.

## Resume

```text
CURRENT_STAGE=G1
LAST_CONFIRMED_GATE=G1_PR_385_PRE_REPAIR_EXACT_HEAD_CI_PASS
NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK
NEXT_PROGRAM_TASK_AFTER_OWNER_INTEGRATION=G2_A_HOURLY_BASELINE_AND_LEGACY_FIXED_DEPTH_SUCCESSION
BLOCKERS=NONE
OWNER_INTEGRATION_PRECONDITION=FRESH_PR_HEAD_AND_CURRENT_PR_CI_PASS
OUT_OF_SCOPE=G2-A;G2-B;G2-C;D8;D9;VPS;AIFE_SERVER;DB-G;PROFILE_FEATURES;BACKTEST_IMPLEMENTATION
```

После owner merge/read-back canonical program map должен быть currentized прежде, чем G2-A начнет writer implementation. До merge owner agent обязан fresh-read current PR head, synthetic integration и exact-head CI; этот handoff не должен возвращаться в self-referential `PR_CI_PENDING` state.
