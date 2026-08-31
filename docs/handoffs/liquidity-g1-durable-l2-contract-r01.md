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
QUALIFIED_CANDIDATE_HEAD_BEFORE_HANDOFF_CURRENTIZATION=8587a4b6789cbb12e876e75e085519d4df59972f
QUALIFIED_CANDIDATE_TREE_BEFORE_HANDOFF_CURRENTIZATION=1da72bdb54af31da116eb91af240d610beb8f1aa
CURRENT_BRANCH_HEAD=READ_FEATURE_BRANCH_REF
CURRENT_BRANCH_TREE=READ_CURRENT_BRANCH_HEAD_TREE
PR_NUMBER=PENDING_CREATION_AFTER_CURRENT_HANDOFF_CI
PR_HEAD_SHA=PENDING_CREATION_AFTER_CURRENT_HANDOFF_CI
PR_MERGED=NO
```

`CURRENT_BRANCH_HEAD` намеренно не самоссылочный SHA внутри commit, который содержит этот handoff: authoritative exact current head всегда читается из Git ref. Предшествующий полностью квалифицированный candidate SHA и tree зафиксированы выше.

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

Base→candidate compare подтвердил ровно эти 9 путей. Writer/runtime/provider/reader/workflow paths в candidate отсутствуют.

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

Полностью квалифицированный predecessor candidate `8587a4b6789cbb12e876e75e085519d4df59972f` прошёл оба автоматически затронутых GitHub Actions workflow:

```text
VALIDATE_REPOSITORY_RUN_ID=33395106216
VALIDATE_REPOSITORY_CONCLUSION=SUCCESS
D8_QUALIFICATION_RUN_ID=33395106151
D8_QUALIFICATION_CONCLUSION=SUCCESS
TARGETED_G1_VALIDATOR=PASS_VIA_VALIDATE_REPOSITORY
DEEP_HISTORY_G1_TESTS=PASS_VIA_EXISTING_TEST_DISCOVERY
CANONICAL_BRANCH_VALIDATION=PASS
PROVIDER_NETWORK_PROBES=0
```

`tools/validation/validate_repository.py` вызывает `validate_g1(root)`, а существующий `tests/deep_history/test_*.py` discovery включает G1 regressions; отдельный validator framework или отдельный CI workflow не создан.

## Scope proof

G1 не меняет physical writer/runtime semantics. `src/collector.py`, `src/intelligence.py`, S1/S2/S3 runtime, current-data transport/promotion, `resolution_v2`, `history_access_v2`, hourly/current-data workflows остаются byte-identical base. Legacy Binance Spot fixed `limit=100` не retired в G1; это G2-A. Exact S3 request resource остаётся `EPHEMERAL_ONLY`; G1 только определяет durability underlying coherent market observation.

## Resume

```text
CURRENT_STAGE=G1
LAST_CONFIRMED_GATE=G1_9_PATH_CANDIDATE_BRANCH_QUALIFICATION_PASS
NEXT_EXACT_TASK=QUALIFY_CURRENT_HANDOFF_COMMIT_THEN_CREATE_ONE_OWNER_REVIEW_PR
NEXT_PROGRAM_TASK_AFTER_OWNER_INTEGRATION=G2_A_HOURLY_BASELINE_AND_LEGACY_FIXED_DEPTH_SUCCESSION
BLOCKERS=NONE_G1_SOURCE;OWNER_PR_REVIEW_REQUIRED
OUT_OF_SCOPE=G2-A;G2-B;G2-C;D8;D9;VPS;AIFE_SERVER;DB-G;PROFILE_FEATURES;BACKTEST_IMPLEMENTATION
```
