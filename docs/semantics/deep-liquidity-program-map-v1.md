# Каноническая программа deep-liquidity: G1/G2

`docs/semantics/deep-liquidity-program-map-v1.md` — единственная repository-owned карта продолжения канонического deep-liquidity контура. Внешний owner-review `ETH_LIQUIDITY_G1_G2_DURABILITY_PROGRAM_MAP_EXPANSION_R01.md` остается `EVIDENCE_ONLY`: он не нужен для восстановления текущего состояния из `AGENTS.md`.

## Текущее состояние

```text
DB-C=CLOSED
DB-D1=CLOSED
DB-D2=CLOSED
DB_F_S3=CLOSED
G1=CLOSED
CURRENT_STAGE=G2-B_IMPLEMENTATION_CANDIDATE
G2A=CLOSED
G2A_IMPLEMENTATION=COMPLETE
G2A_PREIMPLEMENTATION=PASS
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES
G2A_S3_HOST_BINDING_TEST_COUPLED_SCOPE_REVIEW=PASS
G2A_S3_HOST_BINDING_TEST_COUPLED_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_KRAKEN_SPOT_FIRST_ACTUAL_FAILURE_RCA_REVIEW=PASS
G2A_KRAKEN_SPOT_PRODUCTION_JSON_NUMERIC_COMPATIBILITY_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_REAUTHORIZED=YES
READY_FOR_G2A_IMPLEMENTATION=YES
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS_R04_REUSED
SECOND_CONTROLLED_G2A_REQUALIFICATION=NO
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
OWNER_INTEGRATED=YES
G2A_OWNER_INTEGRATION=PASS
G2_A_OWNER_INTEGRATION=PASS
G2B_STARTED=YES
G2B_IMPLEMENTATION=COMPLETE_IN_CANDIDATE
G2_B_READER_IMPLEMENTED=YES_IN_CANDIDATE
G2B_IMPLEMENTATION_QUALIFICATION=PASS
READY_FOR_G2B_OWNER_INTEGRATION=YES
G2B_OWNER_INTEGRATED=NO
G2B_POSTMERGE_QUALIFIED=NO
```

DB-F/S3 даёт request-aware bounded acquisition через один существующий маршрут `S1 → S2 → S3`. G1 contract owner-integrated и закрыт. G2-A preimplementation/governance sequence закрыта, implementation complete, fresh owner review пройден и owner integration currentized в том же exact21 contour. R04 repaired WIP прошёл pre-network qualification, а controlled qualification carrier на **тех же production S1→S2→S3 paths** получил coherent observations для всех шести baseline capabilities и измерил actual successor serializer bytes. Второй controlled provider run не выполняется: доказанный R04 proof переиспользуется, потому что successor/currentization не меняет S1/S2/S3 acquisition semantics, `build_durable_l2_observation` или `serialize_durable_l2_observation`. G2-A закрывает destructive fixed-100 succession, physical namespace collision, Fresh Current observation-level transfer/durability, coupled validation currentization и repository authority. G2-B runtime implementation завершён и qualified в candidate; owner integration и post-merge qualification остаются отдельным следующим контуром.

## G1 closure evidence

```text
G1_OWNER_INTEGRATION=PASS
G1_PR_NUMBER=385
G1_EXACT_HEAD=040fbf33b662b40dcce1c0ba08e8041a09c67c8b
G1_MERGE_COMMIT=60ed320527e6dfbc262de59fda81989a4a22c18b
G1_POSTMERGE_QUALIFICATION=PASS
```

## Реальный риск

```text
RISK=IRRETRIEVABLE_POINT_IN_TIME_L2_HISTORY_LOSS
```

Если реально наблюденный coherent L2 book использован как current evidence, но его underlying market observation не попал в canonical history, такой point-in-time факт обычно нельзя достоверно восстановить позже. Именно этот риск обосновывает G1/G2; задача не является общим проектом «собирать больше данных».

## Owner architecture и reuse

Продолжение обязано использовать:

```text
ONE_ACQUISITION_PATH=S1_TO_S2_TO_S3
HISTORY_FAMILY=liquidity.orderbook-snapshots
DURABLE_PUBLISHER=.github/workflows/update-market.yml
IMMUTABLE_HISTORY_PRIMITIVE=src/history_store.py
RESOLVER=tools/capability_index.py
READER=tools/history_access.py
```

Запрещенное дублирование:

```text
SECOND_COLLECTOR=NO
SECOND_S3_EXECUTOR=NO
SECOND_PROVIDER_PLANNER=NO
SECOND_PROMOTION_WORKFLOW=NO
SECOND_HISTORY_READER=NO
SECOND_CAPABILITY_CATALOG=NO
SECOND_DEDUPE_LEDGER=NO
SECOND_TEMPORAL_AUTHORITY=NO
```

## Request resource и market observation

Exact S3 request resource и исторический market fact — разные сущности.

```text
REQUEST_RESOURCE_DURABILITY=EPHEMERAL_ONLY
UNDERLYING_OBSERVATION_DURABILITY=ELIGIBLE_FOR_CANONICAL_HISTORY
CROSS_RUN_EXACT_RESOURCE_REUSE=NO
ACTIONS_ARTIFACT_AS_CROSS_RUN_CACHE=NO
```

Request resource содержит request-relative satisfaction/freshness/identity. Durable observation содержит market facts и не получает request SHA в semantic identity.

## G1_SCOPE

G1 устанавливает `ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1` и владеет только `DURABLE_L2_OBSERVATION_SEMANTICS`.

G1:
- развивает существующую family `liquidity.orderbook-snapshots`, не создает параллельную deep-history family;
- переиспользует `liquidity-s1-normalized-book/1.0.0`;
- фиксирует observation identity и immutable binding;
- сохраняет actual bid/ask levels/coverage и native quantity semantics через S1 value substrate;
- фиксирует coherent partial/truncated durability и `extrapolation_allowed=false`;
- фиксирует compact provenance option B;
- фиксирует legacy compatibility, cadence/storage independence и no-lookahead vocabulary.

G1 не владеет S1 request satisfaction, S2 provider selection, S3 network execution, hourly scheduling, fresh-current writer, provider activation, history reader activation или server storage backend.

```text
G1_WRITER_ACTIVE=NO
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
G2_A_OWNER_INTEGRATION=PASS
OWNER_INTEGRATED=YES
G2_B_READER_IMPLEMENTED=YES_IN_CANDIDATE
G2B_OWNER_INTEGRATED=NO
PROVIDER_NETWORK_CALLS_PER_CANONICAL_HOURLY_RUN=6
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
```

## G2_A_SCOPE

G2-A — один атомарный writer-side successor:

```text
HOURLY_BASELINE
+ LEGACY_FIXED_100_BINANCE_SUCCESSION
+ FRESH_CURRENT_NEW_OBSERVATION_PROMOTION
+ OBSERVATION_DEDUPE
+ EXISTING_HOURLY_DURABLE_PUBLICATION
```

### Hourly baseline

```text
HOURLY_HISTORY_TARGET_BPS=500
```

SIX_CAPABILITY_BASELINE_SCOPE:

```text
binance-spot ETHUSDT
binance-spot BTCUSDT
kraken-spot ETHUSD
kraken-spot BTCUSD
kraken-futures PI_ETHUSD
kraken-futures PI_XBTUSD
```

Binance USD-M остается `DISABLED_BY_POLICY` в GitHub execution plane:

```text
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
```

500 bps — semantic history target, а provider depth/level count остается S2 physical realization. Если coherent provider observation не достигает 500 bps, реальный наблюденный book не выбрасывается.

### Fresh-current new observation durability

```text
FRESH_CURRENT_NEW_OBSERVATION_DURABILITY=YES
NO_FAKE_HISTORY_ON_REUSE=YES
```

Только новая фактическая S3 acquisition может дать новый historical observation. Reuse уже существующего resource не создаёт новый market timestamp и не дублирует историю.

### Partial / truncated

```text
PERSIST_PARTIAL_COHERENT_OBSERVATION=YES
TRUNCATED_OBSERVATION_HANDOFF_MUST_NOT_DEPEND_ON_REQUEST_PASS=YES
NO_EXTRAPOLATION=YES
```

Target miss не превращает наблюденный coherent book в «не существовавший» market fact. Actual coverage сохраняется честно. Request satisfaction по-прежнему остается отдельным S1 verdict и может быть FAIL/PARTIAL. Durable writer оценивает coherent underlying observation отдельно от request-level PASS.

### Legacy succession

Существующие schema 1.0.0/fixed-100 historical bytes сохраняются:

```text
LEGACY_100_LEVEL_HISTORY_VALID=YES
LEGACY_SNAPSHOT_BYTES_MUTATED=NO
LEGACY_FIXED_100_SUCCESSION=COMPLETE
NO_SYNTHETIC_BACKFILL=YES
```

G2-A atomically убирает два duplicate Binance Spot `limit=100` network calls (ETHUSDT/BTCUSDT) одновременно с canonical S3 hourly baseline. Legacy history не переименовывается в 500-bps complete: доступно только то, что доказывают stored levels; неизвестное остается UNKNOWN.

### Observation dedupe

```text
OBSERVATION_DEDUPE=provider_id+instrument_id+book_kind+observation_id
OBSERVATION_CONTENT_BINDING=observation_sha256
SAME_IDENTITY_SAME_SHA=IDEMPOTENT_DUPLICATE
SAME_IDENTITY_DIFFERENT_SHA=FAIL_CLOSED_IMMUTABLE_OBSERVATION_CONFLICT
```

Request identity, cadence, storage locator, Issue/run/artifact identity не участвуют в semantic observation identity. Используется существующий immutable `src/history_store.py`; второй ledger не создается.

### Compact provenance

```text
PROVENANCE_DECISION=OPTION_B_COMPACT_STABLE_ACQUISITION_PROVENANCE_DIGESTS
```

Durable fact хранит canonical observation плюс минимальные стабильные bindings: provider plan/capability SHA, S3 policy/receipt SHA, route/endpoint/action binding digests, one-observation/one-request-or-session proof и provider-specific coherence/integrity evidence. Полный transient S3 receipt не сохраняется forever по умолчанию.

## G2-A preimplementation owner review R01

Следующий раздел сохраняется как историческая owner-review authority, на которой основан текущий implementation successor.

```text
G2A_PREIMPLEMENTATION_REVIEW=PASS
G2A_IMPLEMENTATION_STARTED=NO
READY_FOR_G2A_IMPLEMENTATION=YES
NEW_PATH_COUNT=0
```

### Exact implementation mutation scope

G2-A implementation обязан оставаться в следующем точном минимальном наборе существующих paths, если implementation не обнаружит доказанный новый coupled invariant. Любое расширение требует нового owner review до mutation.

```text
EXACT_IMPLEMENTATION_PATH_COUNT=21
EXACT_IMPLEMENTATION_PATHS=
.github/workflows/update-market.yml
.github/workflows/current-data-request.yml
src/intelligence.py
src/sampled_history.py
tools/current_data_promotion.py
bridge-contract.json
contracts/liquidity-durable-l2-observation-v1.json
docs/semantics/deep-liquidity-program-map-v1.md
docs/semantics/fresh-current-agent-transport-v1.md
AGENTS.md
tools/validation/validate_liquidity_g1_durability.py
tests/deep_history/test_liquidity_g1_durability.py
tests/deep_history/test_current_data_promotion.py
tests/deep_history/test_d9_sampled_history.py
tests/deep_history/test_d9_liquidity_reproducibility.py
contracts/provider-contracts.json
src/liquidity_s2_binance_adapter.py
tools/validation/validate_liquidity_s2_binance_adapter.py
tests/test_liquidity_s2_binance_adapter.py
tests/test_liquidity_s3_executor.py
src/liquidity_s3_executor.py
```

Новые files/helpers/workflows/services не нужны:

```text
NEW_PATH_COUNT=0
NEW_PATH_JUSTIFICATION=NONE_EXISTING_PATHS_SUFFICIENT
```

### Existing owner paths, которые G2-A обязан переиспользовать

```text
LEGACY_FIXED_100_OWNER_PATHS=
src/intelligence.py

HOURLY_ACQUISITION_OWNER_PATHS=
.github/workflows/update-market.yml
src/collector.py
src/intelligence.py

HOURLY_S3_OWNER_PATHS=
src/liquidity_s1_runtime.py
src/liquidity_s2_binance_adapter.py
src/liquidity_s2_kraken_spot.py
src/liquidity_s2_kraken_futures.py
src/liquidity_s3_executor.py

BINANCE_SPOT_CANONICAL_HOST_OWNER_PATHS=
contracts/provider-contracts.json
src/liquidity_s2_binance_adapter.py

PROMOTION_HANDOFF_OWNER_PATHS=
.github/workflows/current-data-request.yml
tools/current_data_request_scope.py
tools/current_data_promotion.py
.github/workflows/update-market.yml

LIQUIDITY_HISTORY_SERIALIZATION_OWNER_PATHS=
src/sampled_history.py
contracts/liquidity-durable-l2-observation-v1.json

OBSERVATION_DEDUPE_OWNER_PATH=src/history_store.py

CURRENT_DATA_PROMOTION_OWNER_PATHS=
.github/workflows/current-data-request.yml
tools/current_data_promotion.py
.github/workflows/update-market.yml

DEPENDENCY_INSTALLATION_OWNER_PATHS=
.github/workflows/update-market.yml
tools/requirements-s3.txt

VALIDATION_TEST_OWNER_PATHS=
tools/validation/validate_liquidity_g1_durability.py
tests/deep_history/test_liquidity_g1_durability.py
tests/deep_history/test_current_data_promotion.py
tests/deep_history/test_d9_sampled_history.py
tests/deep_history/test_d9_liquidity_reproducibility.py
tools/validation/validate_liquidity_s2_binance_adapter.py
tests/test_liquidity_s2_binance_adapter.py
tests/test_liquidity_s3_executor.py
```

Следующие existing paths являются reuse-only для G2-A и не входят в frozen mutation scope без нового доказанного coupled invariant:

```text
src/collector.py
src/liquidity_s1_runtime.py
src/liquidity_s2_kraken_spot.py
src/liquidity_s2_kraken_futures.py
src/history_store.py
tools/current_data_request_scope.py
tools/requirements-s3.txt
tools/capability_index.py
tools/history_access.py
```

### Truncated handoff decision

```text
TRUNCATED_HANDOFF_DESIGN=RESOLVED
PERSIST_COHERENT_OBSERVATION_INDEPENDENT_OF_REQUEST_PASS=YES
REQUEST_LEVEL_PASS_REMAINS_SEPARATE=YES
```

Coherent partial/truncated observation, полученный новой S3 acquisition, может стать durable market observation даже если request-level target не достигнут. Stored actual coverage и truncation сохраняются; completion не фабрикуется и extrapolation запрещён.

### Reuse и observation dedupe decision

```text
OBSERVATION_DEDUPE_DESIGN=RESOLVED
REUSE_CREATES_HISTORICAL_OBSERVATION=NO
FRESH_S3_ACQUISITION_CAN_CREATE_DURABLE_OBSERVATION=YES
DEDUPE_PRIMITIVE=src/history_store.py
```

Persisted/exact-resource reuse не создаёт новый market timestamp. Новая durable запись допускается только для реально нового coherent market observation. Existing immutable history primitive определяет idempotent duplicate/conflict semantics; второй dedupe ledger запрещён.

### Hourly dependency installation decision

```text
HOURLY_DEPENDENCY_INSTALLATION=RESOLVED
PINNED_S3_REQUIREMENTS=tools/requirements-s3.txt
SECOND_DEPENDENCY_INSTALLER=NO
```

Hourly runtime должен устанавливать existing pinned S3/WebSocket dependency через тот же `update-market.yml`; новый requirements file или отдельный installer не создаётся.

### Cron reconciliation decision

Фактический durable publisher остаётся `.github/workflows/update-market.yml`; его schedule — `17 * * * *`. Историческая декларация `35 * * * *` была stale declaration и в R05 currentized до фактического schedule.

```text
CRON_RECONCILIATION=COMPLETE_IN_IMPLEMENTATION_CANDIDATE
ACTUAL_DURABLE_PUBLISHER_CRON=17 * * * *
DECLARATION_TARGET_CRON=17 * * * *
CRON_MINUTE_IS_SEMANTIC_IDENTITY=NO
CRON_RECONCILIATION_OWNER_PATHS=
bridge-contract.json
docs/semantics/fresh-current-agent-transport-v1.md
```

### Promotion retention gate

```text
PROMOTION_RETENTION_GATE=RESOLVED
DURABLE_PUBLISHER_RECOVERY_SLO_HOURS=24
CURRENT_PROMOTION_ARTIFACT_RETENTION_HOURS=168
RETENTION_GT_RECOVERY_SLO=PASS
```

Existing 7-day current-data artifact retention достаточно для declared 24-hour durable-publisher recovery SLO. Новый retention mechanism не создаётся. Если implementation изменит recovery SLO или retention, gate должен быть пересчитан fail-closed.

### Actual successor byte benchmark plan

```text
SUCCESSOR_BYTE_BENCHMARK_PLAN=RESOLVED
ACTUAL_SUCCESSOR_BYTE_BENCHMARK_REQUIRED=YES
WRITER_ACTIVATION_BEFORE_BENCHMARK_PASS=FORBIDDEN
```

До writer activation implementation должна:

1. получить actual newly acquired coherent observations для всех шести baseline capabilities через существующий S1→S2→S3 route;
2. пропустить их через **тот же actual successor serializer** в `src/sampled_history.py`, который будет использовать durable writer;
3. не выполнять durable publication до benchmark PASS;
4. измерить canonical UTF-8/LF serialized bytes per provider/instrument;
5. измерить six-capability baseline generation bytes;
6. рассчитать hourly 30-day/1-year projections и representative future 5-minute projection;
7. сохранить benchmark evidence в существующем test/qualification evidence flow, без нового storage subsystem.

Этот план был исполнен R04 controlled qualification и в owner currentization повторно не запускается.

## R04 actual six-capability successor proof reused by R05

```text
R04_REPAIRED_WIP_HEAD=d4726243ff0ab719f668d764a858dd7bea8e1f6d
R04_REPAIRED_WIP_TREE=08764f28c8d8802f89a0fb848dfaa35427f28e7d
R04_PRE_NETWORK_CI_RUN=33560282658
R04_QUALIFICATION_CARRIER_HEAD=743bb18cdedb414476a0ccdc191a0f7cea9154f3
R04_QUALIFICATION_CARRIER_TREE=83ee5b0dbf9631866c543ec19f37baa06c0baba6
R04_CONTROLLED_QUALIFICATION_RUN=33560525938
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS
SIX_CAPABILITY_GENERATION_BYTES=547874
HOURLY_30D_BYTES=394469280
HOURLY_1Y_BYTES=4799376240
REPRESENTATIVE_5M_30D_BYTES=4733631360
REPRESENTATIVE_5M_1Y_BYTES=57592514880
SECOND_CONTROLLED_G2A_REQUALIFICATION=NO
```

R04 production serializer proof применим к R05, потому что R05 сохраняет bytes/semantics `build_durable_l2_observation` и `serialize_durable_l2_observation`; R05 изменяет physical partition locator, Fresh Current transfer/invocation layer, destructive legacy succession, declarations/docs/validators/tests. Qualification carrier не является implementation source и его controlled-acquisition trigger не переносится в final candidate.

R04 после six-capability/benchmark proof выявил separate post-proof namespace defect: multi-observation G2-A partition под `liquidity/snapshots/**` попадал в legacy `src/event_window.py::nearest_v4()` single-snapshot reader. R05 исправляет это без mutation `src/event_window.py`: physical G2-A partition перемещён в `history/liquidity-orderbook-snapshots/**`, semantic family остаётся `liquidity.orderbook-snapshots`.

### Атомарность legacy succession

```text
LEGACY_FIXED_100_RETIREMENT=COMPLETE_IN_IMPLEMENTATION_CANDIDATE
FIXED_100_REMOVAL_BEFORE_SUCCESSOR_PASS=NO
```

Два Binance Spot fixed-100 calls в `src/intelligence.py` retire только после доказанного R04 six-capability successor/serializer proof и в той же R05 implementation candidate, где hourly durability integration проходит final qualification.

### Три owner-вопроса

Для каждого proposed change review применил обязательные вопросы:

1. **Какой реальный риск закрывается?** Потеря невосстановимого L2 point-in-time fact, duplicate/fake history, immutable observation conflict, silent loss truncated book, runtime dependency failure, stale schedule authority, handoff expiry до recovery и неизвестный actual payload envelope.
2. **Можно ли закрыть в существующем path?** Да. Все решения имеют existing owner path; новый collector/executor/publisher/history reader/dedupe ledger/helper не нужен.
3. **Уменьшается ли число действий следующего агента/инженера?** Да. Один frozen implementation scope, один hourly acquisition route, один promotion route, один history serializer, один immutable dedupe primitive и один publisher исключают ручную реконструкцию и параллельные механизмы.

## G2-A coupled main drift owner review R01

PR #402 (`af5294e8cdea3faeffab51102bf43d9dfd826c91`) изменил только Fresh Current tail/PIT admission и regression coverage: schema v1.1 проецирует generation timestamp из `ordinary_generation.data_manifest_generated_at_utc`. Этот timestamp является generation provenance/PIT input и не заменяет semantic timestamp отдельной L2 observation. Durable L2 contract, normalized-book semantics, observation identity, immutable dedupe и S1→S2→S3 authority PR #402 не менял.

```text
PR402_COUPLED_DRIFT_REVIEW=PASS
PR402_CLASSIFICATION=COMPATIBLE_COUPLED_DRIFT
PR402_REQUIRES_G2A_ARCHITECTURE_REDESIGN=NO
PR402_REQUIRES_G2A_SCOPE_EXPANSION=NO
G2A_SCOPE_EXPANSION_REQUIRED=NO
G2A_REAUTHORIZED=YES
GOVERNANCE_CANDIDATE_INTEGRATION_STATUS=MERGED_AND_POSTMERGE_QUALIFIED
PR402_REVIEW_PREDECESSOR_LAST_CONFIRMED_GATE=G2A_PREIMPLEMENTATION_OWNER_REVIEW_PASS
```

## G2-A proven DB-C validation coupled scope expansion owner review R01

Fresh-read `main`, implementation WIP и failed retirement attempt подтвердил, что required atomic legacy succession блокируется не successor architecture, а двумя существующими DB-C validation owners. `tools/validation/validate_liquidity_s2_binance_adapter.py` и `tests/test_liquidity_s2_binance_adapter.py` жёстко требуют сохранения Binance Spot `limit=100` / active shallow provider semantics. В failed attempt `df87fd47194a4d4b57edc49bc0915881082ebe71` именно removal этих calls приводит к первому canonical failed gate `Validate liquidity S2 Binance DB-C provider foundation`.

```text
DB_C_VALIDATION_COUPLING_REVIEW=PASS
DB_C_LEGACY_ASSERTIONS=STALE_FOR_G2A_SUCCESSOR
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=CONFIRMED
G2A_LEGACY_RETIREMENT_REQUIRES_DB_C_VALIDATION_CURRENTIZATION=YES
G2A_SCOPE_EXPANSION_REASON=LEGACY_FIXED_100_RETIREMENT_REQUIRES_SUCCESSOR_AWARE_DB_C_VALIDATION
PROVEN_MINIMUM_COUPLED_SCOPE_EXPANSION_PATH_COUNT=2
AUTHORIZED_SCOPE_EXPANSION_PATH_COUNT=2
AUTHORIZED_SCOPE_EXPANSION_PATHS=
tools/validation/validate_liquidity_s2_binance_adapter.py
tests/test_liquidity_s2_binance_adapter.py
PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=15
DB_C_REVIEW_RESULT_EXACT_IMPLEMENTATION_PATH_COUNT=17
DB_C_REVIEW_EXACT_IMPLEMENTATION_PATH_COUNT=17
NEW_PATH_COUNT=0
ARCHITECTURE_REDESIGN_REQUIRED=NO
NEW_RUNTIME_PATH_REQUIRED=NO
NEW_VALIDATION_LAYER_REQUIRED=NO
SECOND_VALIDATOR_REQUIRED=NO
G2A_IMPLEMENTATION_WIP_HEAD=d7261b9e8eb47a23642ebbdf7134959e1c9b8043
G2A_IMPLEMENTATION_WIP_TREE=f43b04129a3029886a7f6b8f2ce5f56ff69ed049
G2A_IMPLEMENTATION_WIP_LAST_GREEN_CI=33509217889
LEGACY_RETIREMENT_ATTEMPT_SHA=df87fd47194a4d4b57edc49bc0915881082ebe71
LEGACY_RETIREMENT_ATTEMPT_RESULT=BLOCKED_BY_STALE_DB_C_VALIDATION
LEGACY_FIXED_100_RETIREMENT=NOT_YET_COMPLETE
LEGACY_FIXED_100_RETIREMENT_CONTINUATION=PENDING_AUTHORIZED_CONTINUATION
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=NO
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PENDING_IMPLEMENTATION_CONTINUATION
DURABLE_PUBLICATION_BEFORE_BENCHMARK_PASS=NO
```

Этот блок сохраняется как историческая owner authorization. В R05 authorized DB-C validator/test currentized до successor-aware semantics: active fixed-100 Spot call отсутствует, canonical G2-A route присутствует, USD-M policy/no-pagination/no-stitching/no-extrapolation сохраняются.

Scope authorization не является доказательством отсутствия любых будущих coupled blockers. Если subsequent full CI докажет необходимость нового path вне current exact scope, implementation обязана остановиться:

```text
STOP_CODE=ADDITIONAL_OUT_OF_SCOPE_COUPLED_INVARIANT_PROVEN
```

Owner self-review scope expansion:

```text
SCOPE_EXPANSION_RISK=VALIDATION_CONTRACT_PREVENTS_REQUIRED_ATOMIC_LEGACY_SUCCESSION
SIMPLER_EXISTING_DB_C_VALIDATOR_AND_TEST_CURRENTIZATION=YES
SECOND_VALIDATOR_OR_COMPATIBILITY_DEAD_CODE_REQUIRED=NO
NEXT_AGENT_ACTION_COUNT_REDUCED=YES
```

## G2-A Binance Spot public market-data endpoint viability owner review R01

Canonical diagnostic `33519578314` на exact head `6aecfc6d06e1986f9426bdddb08a2725f9c9567c` выполнил одну physical attempt для первого baseline capability и fail-closed получил HTTP `451` через текущий Binance Spot general REST plan. S3 classification остаётся coarse execution class и не доказывает более узкую provider-specific причину.

```text
DIAGNOSTIC_HEAD=6aecfc6d06e1986f9426bdddb08a2725f9c9567c
DIAGNOSTIC_TREE=ea6bfbb997b06ef0f868c465107a7d20f9070c65
DIAGNOSTIC_CI_RUN=33519578314
DIAGNOSTIC_FIRST_FAILED_CAPABILITY=liquidity.binance-spot.ETHUSDT.orderbook
DIAGNOSTIC_HTTP_STATUS=451
DIAGNOSTIC_S3_CLASS=PROVIDER_REJECTION_OR_RATE_LIMIT
DIAGNOSTIC_S3_ERROR_CLASS=RATE_LIMIT_OR_PROVIDER_REJECTION
RATE_LIMIT_CAUSE_PROVEN=NO
GEO_BLOCK_CAUSE_PROVEN=NO
GITHUB_IP_CAUSE_PROVEN=NO
HTTP_451_PROVIDER_SPECIFIC_SEMANTICS=NOT_NORMATIVELY_DOCUMENTED
```

First-party Binance Spot documentation сохраняет `https://api.binance.com` как официальный general Spot REST base и отдельно указывает `https://data-api.binance.vision` для API, которые передают только public market data. Market Data Only contract прямо включает `GET /api/v3/depth`; G2-A Binance Spot acquisition не требует account/trading/user-data API.

```text
CURRENT_GENERAL_SPOT_REST_HOST=https://api.binance.com
FIRST_PARTY_GENERAL_SPOT_REST_HOST=https://api.binance.com
FIRST_PARTY_MARKET_DATA_ONLY_HOST=https://data-api.binance.vision
FIRST_PARTY_MARKET_DATA_ONLY_DEPTH_ENDPOINT=/api/v3/depth
FIRST_PARTY_MARKET_DATA_ONLY_DEPTH_SUPPORTED=YES
CURRENT_CANONICAL_ROUTE_ALIGNED_WITH_FIRST_PARTY_MARKET_DATA_ONLY_GUIDANCE=NO
```

Owner decision использует самый узкий механизм: один canonical host для того же provider, того же endpoint path и того же S1→S2→S3 route. `api.binance.com` не объявляется stale/unsupported; для G2-A public-only acquisition авторизуется requalification через официальный market-data-only host. Это authorization на controlled requalification, а не доказательство причины исторического HTTP 451.

```text
OWNER_PROVIDER_EXECUTION_DECISION=AUTHORIZE_SINGLE_CANONICAL_MARKET_DATA_ONLY_HOST_REQUALIFICATION
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES
SINGLE_CANONICAL_HOST_SUCCESSION_AUTHORIZED=YES
AUTHORIZED_BINANCE_SPOT_BASE_HOST=https://data-api.binance.vision
HOST_SUCCESSION_KIND=SINGLE_CANONICAL_PUBLIC_MARKET_DATA_HOST_SUCCESSION
SAME_PROVIDER=YES
SAME_ENDPOINT_PATH=/api/v3/depth
SAME_S1_TO_S2_TO_S3_ROUTE=YES
SECOND_PROVIDER=NO
SECOND_S3=NO
AUTOMATIC_FALLBACK=NO
RETRY_POLICY_CHANGED=NO
VPS_MIGRATION_AUTHORIZED=NO
AIFE_SERVER_EXECUTION_AUTHORIZED=NO
PROXY_AUTHORIZED=NO
ACTUAL_REQUALIFICATION_REQUIRED=YES
HTTP_451_RESOLUTION_PROVEN=NO
```

Exact source ownership показывает, что canonical Spot host принадлежит `contracts/provider-contracts.json`, а `src/liquidity_s2_binance_adapter.py` revalidate'ит этот contract и материализует `canonical_base_host` в provider plan. S3 executor только исполняет validated plan и отдельного Binance Spot host не hard-code'ит.

```text
PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=17
PROVEN_COUPLED_SCOPE_EXPANSION_PATH_COUNT=2
PROVEN_COUPLED_SCOPE_EXPANSION_PATHS=
contracts/provider-contracts.json
src/liquidity_s2_binance_adapter.py
RESULT_EXACT_IMPLEMENTATION_PATH_COUNT=19
NEW_PATH_COUNT=0
S3_EXECUTOR_MUTATION_REQUIRED=NO
CURRENT_DATA_REQUEST_SCOPE_MUTATION_REQUIRED=NO
```

Owner three-question review:

1. **Какой реальный риск закрывается?** Убирается avoidable mismatch между public-only G2-A acquisition и first-party dedicated public market-data route, чтобы не блокировать устранение исходного `IRRETRIEVABLE_POINT_IN_TIME_L2_HISTORY_LOSS`.
2. **Можно ли закрыть проще?** Да: single host succession в двух существующих host-owner paths; proxy/VPS/second provider/host pool/retry loop не нужны.
3. **Уменьшает ли решение число действий следующего агента?** Да: следующий implementation currentizes только два owner-authorized host paths и продолжает прежний G2-A task только после pre-network PASS.

## G2-A S3 host-binding test coupled scope expansion owner review R01

Canonical pre-network run `33532738999` на exact stopped implementation head `4b70dae85a8952911972a4eac8abd6b766b73d15` / tree `38e5cc6c7143cafa3425792b78e1e84e5321ffa9` materialized owner-authorized Binance Spot host succession, но остановился на первом S3 executable regression: test всё ещё требовал predecessor host.

```text
G2A_S3_HOST_BINDING_TEST_COUPLED_SCOPE_REVIEW=PASS
G2A_S3_HOST_BINDING_TEST_COUPLED_DEFECT=CONFIRMED
S3_HOST_BINDING_TEST_ASSERTION=STALE_FOR_OWNER_AUTHORIZED_CANONICAL_HOST_SUCCESSION
PRE_NETWORK_FAILED_CI_RUN=33532738999
PRE_NETWORK_FAILED_HEAD=4b70dae85a8952911972a4eac8abd6b766b73d15
PRE_NETWORK_FAILED_TREE=38e5cc6c7143cafa3425792b78e1e84e5321ffa9
PRE_NETWORK_FAILED_GATE=Validate DB-F S3 bounded execution
PRE_NETWORK_FAILED_TEST=tests.test_liquidity_s3_executor.DBFS3Tests.test_002_binance_spot_rest_success_and_receipt
STALE_EXPECTED_HOST=https://api.binance.com
OWNER_AUTHORIZED_HOST=https://data-api.binance.vision
PROVEN_MINIMUM_COUPLED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH=tests/test_liquidity_s3_executor.py
PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=19
EXACT_IMPLEMENTATION_PATH_COUNT=20
NEW_PATH_COUNT=0
ARCHITECTURE_REDESIGN_REQUIRED=NO
S3_EXECUTOR_MUTATION_REQUIRED=NO
AUTOMATIC_FALLBACK=NO
RETRY_POLICY_CHANGED=NO
SECOND_PROVIDER=NO
SECOND_S3=NO
ACTUAL_REQUALIFICATION_REQUIRED=YES
HTTP_451_RESOLUTION_PROVEN=NO
LEGACY_FIXED_100_RETIREMENT=NOT_YET_COMPLETE
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=NO
```

Этот block — historical evidence. R04/R05 S3 regression уже currentized на `https://data-api.binance.vision`; fallback/retry/provider semantics не расширены.

## G2-A Kraken Spot WS v2 numeric precision malformed-payload RCA / coupled scope owner review R01

Canonical actual qualification `33549822547` на failure carrier `a46de92f265cbdd49667b815ec7c5693a8d048e4` / tree `4bf3d4b7d5c777560bb7778a82c181f9449e1932` прошла две Binance Spot baseline capabilities и fail-closed остановилась на третьей capability — Kraken Spot ETHUSD. Sanitized S3 receipt сохранил route/cardinality/size/digests, но не raw frame и не underlying S2 exception; поэтому exact observed failure не объявляется causally proven, хотя статический production compatibility defect доказан независимо.

```text
G2A_KRAKEN_SPOT_FIRST_ACTUAL_FAILURE_RCA_REVIEW=PASS
G2A_KRAKEN_SPOT_PRODUCTION_JSON_NUMERIC_COMPATIBILITY_DEFECT=CONFIRMED
FAILED_ACQUISITION_RUN=33549822547
FAILED_CARRIER_HEAD=a46de92f265cbdd49667b815ec7c5693a8d048e4
FAILED_CARRIER_TREE=4bf3d4b7d5c777560bb7778a82c181f9449e1932
FAILED_CAPABILITY=liquidity.kraken-spot.ETHUSD.orderbook
FAILED_ROUTE=WEBSOCKET
FAILED_TERMINAL_STATUS=FAIL_MALFORMED_PAYLOAD
NETWORK_ATTEMPT_COUNT=1
PROVIDER_REQUEST_OR_SESSION_COUNT=1
RAW_MESSAGE_COUNT=3
RAW_OBSERVATION_BYTES=71232
PROVIDER_PLAN_SHA256=c3e0f1215d61ff63935df0451113a42c6246a18a526515404fcd592a38f12b34
PROVIDER_ENDPOINT_BINDING_SHA256=41eeec40e274e3f451add435163ff4d9e2d73e8db4751f7f54cc4dd3c6760ef1
PHYSICAL_ACTION_SHA256=ec5f58a7761780cf8bde229f845546d7a2d00b869bc43eb2570f554e3c10e800
BINANCE_SPOT_ETHUSDT_OBSERVED_EXECUTION=PASS_BEFORE_FIRST_FAILURE
BINANCE_SPOT_BTCUSDT_OBSERVED_EXECUTION=PASS_BEFORE_FIRST_FAILURE
HISTORICAL_HTTP_451_REPRODUCED=NO
KRAKEN_FIRST_PARTY_PRICE_QTY_SEMANTICS=JSON_NUMERIC_FLOAT
KRAKEN_FIRST_PARTY_CHECKSUM_PRECISION_REQUIREMENT=DECIMAL_OR_STRING_DECODER
CURRENT_S3_JSON_DECODER=PLAIN_JSON_LOADS
CURRENT_DECODED_JSON_NUMERIC_TYPE=FLOAT
CURRENT_KRAKEN_SPOT_ADAPTER_ACCEPTED_LEVEL_VALUE_TYPES=STR_OR_DECIMAL
UNIT_FIXTURE_MATCHES_POST_PRECISION_PARSE_REPRESENTATION=YES
UNIT_FIXTURE_REPRODUCES_RAW_JSON_DECODER_TYPE_PIPELINE=NO
LIVE_WIRE_NUMERIC_DECODING_COVERAGE_GAP=CONFIRMED
FLOAT_ACCEPTANCE_WITHOUT_PRECISION_PRESERVATION_SAFE=NO
PRODUCTION_COMPATIBILITY_DEFECT=CONFIRMED
EXACT_RUN_ROOT_CAUSE_PROVEN=NO
OBSERVED_FAILURE_CAUSAL_BINDING=HIGH_CONFIDENCE
ROOT_CAUSE_CANDIDATE_CONFIDENCE=HIGH
MINIMAL_CORRECT_REPAIR_PATH=src/liquidity_s3_executor.py
PROVEN_MINIMUM_COUPLED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH=src/liquidity_s3_executor.py
PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=20
EXACT_IMPLEMENTATION_PATH_COUNT=21
NEW_PATH_COUNT=0
ARCHITECTURE_REDESIGN_REQUIRED=NO
ACTUAL_SECOND_PROVIDER_REQUALIFICATION_REQUIRED=YES
SECOND_PROVIDER_NETWORK_RUN_IN_THIS_GOVERNANCE_TASK=NO
RUNTIME_MUTATION_IN_THIS_GOVERNANCE_TASK=NO
PROVIDER_NETWORK_ATTEMPT_IN_THIS_GOVERNANCE_TASK=NO
BENCHMARK_IN_THIS_GOVERNANCE_TASK=NO
LEGACY_RETIREMENT_IN_THIS_GOVERNANCE_TASK=NO
```

Type-pipeline proof:

```text
KRAKEN_SPOT_TYPE_PIPELINE=WEBSOCKET_FRAME_TO_S3_DECODE_TO_S3_CONSUMER_TO_KRAKEN_SPOT_S2_TO_CHECKSUM_TO_NORMALIZED_BOOK
S3_DECODE_BOUNDARY=json.loads(message)
JSON_NUMERIC_TOKEN_WITH_PLAIN_JSON_LOADS=PYTHON_FLOAT
S2_PROVIDER_LEVEL_VALUE_TYPES=STR_OR_DECIMAL
CHECKSUM_PRECISION_MUST_BE_PRESERVED_BEFORE_S2_CHECKSUM_CONSTRUCTION=YES
```

First-party Kraken Spot WebSocket v2 `book` schema объявляет `price` и `qty` numeric/float fields и snapshot CRC32 top-10 checksum. First-party checksum guide требует parse `price`/`qty` через decimal или string decoder для сохранения полной точности при deserialisation и показывает `json.loads(..., parse_float=Decimal)`. Текущий S3 decode boundary использует plain `json.loads(message)`, поэтому numeric JSON tokens становятся binary `float` до вызова Kraken Spot S2. S2 намеренно принимает только `str|Decimal` и строит checksum material из точных decimal representations; просто разрешить `float` в S2 после потери lexical precision противоречило бы checksum authority.

Unit fixture в `tests/test_liquidity_s2_kraken_spot_adapter.py` использует preconstructed `Decimal`, а existing S3 fake-wire fixture передаёт `price`/`qty` как JSON strings. Поэтому оба test уровня обходят реальный numeric-wire decode seam. Новый test path не нужен: уже authorized `tests/test_liquidity_s3_executor.py` способен подать realistic raw JSON numeric tokens и доказать end-to-end precision-preserving decode → S2 normalization → CRC32 PASS.

### Minimal repair location review

A. `src/liquidity_s2_kraken_spot_adapter.py` не является минимальным корректным repair location: принятие binary float после decode не восстанавливает потерянную decimal precision и ослабляет checksum boundary.

B. `src/liquidity_s3_executor.py` является минимальным корректным repair location: precision должна сохраняться именно на JSON decode boundary до provider checksum construction.

C. Новый decoder/helper/file не нужен: существующий S3 executor уже владеет физическим JSON decode seam.

```text
PROVEN_MINIMUM_NEW_COUPLED_PATH_COUNT=1
PROVEN_MINIMUM_NEW_COUPLED_PATH=src/liquidity_s3_executor.py
ARCHITECTURE_REDESIGN_REQUIRED=NO
NEW_DECODER_HELPER_REQUIRED=NO
S2_ADAPTER_MUTATION_REQUIRED=NO
EXISTING_S3_REGRESSION_PATH_SUFFICIENT=YES
```

R04 repaired WIP applied exactly this authorized decode-boundary repair and six-capability proof passed. R05 does not change this repaired path except carrying the exact proven R04 blob into the final candidate.

Exact 21 — current frozen authorization. Если final qualification докажет ещё один out-of-scope coupled invariant:

```text
STOP_CODE=ADDITIONAL_OUT_OF_SCOPE_COUPLED_INVARIANT_PROVEN
```

Owner three-question review:

1. **Какой реальный риск закрывается?** Нормативный Kraken Spot WS v2 numeric payload мог преобразовываться plain JSON decoder в binary float до CRC32; это несовместимо с provider-required precision preservation и блокировало G2-A six-capability durability qualification.
2. **Можно ли проще?** Да — R04 currentized existing S3 decode boundary и existing S3 regression test; provider architecture, S2 semantics, checksum, fallback/retry и новые helpers не потребовались.
3. **Уменьшается ли число действий следующего агента?** Да — R04 proof теперь reusable, второй controlled provider run R05 не нужен.

### Temporal role separation gate

```text
TEMPORAL_ROLE_SEPARATION_GATE=REQUIRED
FRESH_CURRENT_GENERATION_TIME=ordinary_generation.data_manifest_generated_at_utc
FRESH_CURRENT_GENERATION_TIME_ROLE=GENERATION_PROVENANCE_AND_PIT_ADMISSION
DURABLE_L2_OBSERVATION_TIME=normalized_book.timestamp_ms
DURABLE_L2_OBSERVATION_TIME_ROLE=MARKET_OBSERVATION_TIME
KNOWN_AT_TIME=canonical execution knowledge timestamp
KNOWN_AT_ROLE=WHEN_THE_OBSERVATION_BECAME_KNOWN_TO_THE_EXECUTION_PATH
DURABLE_PUBLICATION_TIME=publication/commit time
DURABLE_PUBLICATION_TIME_ROLE=STORAGE_PUBLICATION_PROVENANCE_ONLY
GENERATION_TIME_IS_L2_OBSERVATION_TIME=NO
KNOWN_AT_IS_L2_OBSERVATION_TIME=NO
DURABLE_PUBLICATION_TIME_IS_L2_OBSERVATION_TIME=NO
PUBLICATION_TIME_IS_L2_OBSERVATION_TIME=NO
WORKFLOW_SCHEDULE_TIME_IS_L2_OBSERVATION_TIME=NO
REQUEST_TIME_IS_L2_OBSERVATION_TIME=NO
OBSERVATION_TIME_LE_KNOWN_AT_TIME=REQUIRED
UNKNOWN_REMAINS_UNKNOWN=YES
SECOND_TEMPORAL_AUTHORITY=NO
```

`tools/current_tail_admission.py` остаётся owner Fresh Current tail/PIT admission и не становится owner L2 market observation timestamp. Для newly acquired S3 L2 observation implementation берёт observation time только из `normalized_book.timestamp_ms`; generation/known-at/workflow/request/publication timestamps запрещено использовать как surrogate observation time. Если корректный known-at фактически не доказуем, он не фабрикуется.

Durable L2 identity остаётся неизменной:

```text
DURABLE_L2_IDENTITY=provider_id+instrument_id+book_kind+observation_id
DURABLE_L2_CONTENT_BINDING=observation_sha256
GENERATION_ID_IN_DURABLE_L2_IDENTITY=NO
GENERATED_AT_UTC_IN_DURABLE_L2_IDENTITY=NO
KNOWN_AT_UTC_IN_DURABLE_L2_IDENTITY=NO
REQUEST_IDENTITY_IN_DURABLE_L2_IDENTITY=NO
REQUEST_SHA256_IN_DURABLE_L2_IDENTITY=NO
CURRENT_SEMANTIC_REQUEST_SHA256_IN_DURABLE_L2_IDENTITY=NO
GITHUB_RUN_ID_IN_DURABLE_L2_IDENTITY=NO
ISSUE_NUMBER_IN_DURABLE_L2_IDENTITY=NO
ARTIFACT_PATH_IN_DURABLE_L2_IDENTITY=NO
STORAGE_LOCATOR_IN_DURABLE_L2_IDENTITY=NO
CADENCE_IN_DURABLE_L2_IDENTITY=NO
```

Implementation regression coverage должна доказать temporal role separation внутри уже frozen test paths; `tools/current_tail_admission.py` и `tests/deep_history/test_current_tail_generated_at_utc.py` в G2-A implementation mutation scope не добавляются.

Owner self-review:

```text
CURRENTIZATION_RISK_CLOSED=PREVENT_TEMPORAL_ROLE_CONFUSION_AND_REPEAT_FALSE_STOP
SIMPLER_EXISTING_OWNER_PATH_SOLUTION=YES
NEXT_AGENT_ACTION_COUNT_REDUCED=YES
```

## G2_B_SCOPE

G2-B currentizes/qualifies существующий sampled-history read family для successor observation schema:

```text
liquidity.orderbook-snapshots
→ existing capability/resolution family
→ existing ResolutionPlan
→ existing history_access
```

Новый reader/catalog не создается. Legacy v1 snapshots остаются читаемыми. D9 default authority не активируется этим этапом.

## Durable payload direction

История должна сохранять normalized L2 market fact, достаточный для будущего deterministic recomputation:
- ordered bids/asks;
- best bid/ask через canonical S1 normalized book;
- actual side coverage;
- native quantity semantics;
- observation identity/hash;
- compact stable provenance.

Не сохранять только сегодняшние derived spread/depth/imbalance/slippage features как единственный факт. Полный provider wire payload forever по умолчанию не требуется.

Историческая оценка:

```text
HISTORY_TARGET_BPS=500
HISTORY_TARGET_ROLE=NON_IDENTITY_ASSESSMENT_METADATA
```

Fresh-current observation, физически полученный для меньшего request target, может оставаться действительным historical market observation; его acquisition history не переписывается.

## PIT / NO_LOOKAHEAD

Переиспользуется существующий resolver/reader и collection-run timing evidence.

```text
NO_LOOKAHEAD=YES
observation_time != known_at
request_time != observation_time
durable_publication_time != observation_time
known_at > cutoff => EXCLUDED
```

`retrieved_at` и `durable_publication_time` — provenance, а не market event identity.

## Storage profile и corrected planning estimate

```text
STORAGE_MODEL_CLASS=CONSERVATIVE_REPRESENTATIVE_PLANNING_ESTIMATE_NOT_MEASURED_SUCCESSOR_BYTES
STORAGE_ESTIMATE_STATUS=SUPERSEDED_BY_R04_ACTUAL_SUCCESSOR_BYTE_BENCHMARK_FOR_CURRENT_HOURLY_CANDIDATE
```

Predecessor arithmetic использовала legacy liquidity snapshot как консервативный planning anchor; legacy file содержит не только две Binance Spot книги, но и дополнительные Deribit books. Поэтому эти числа **не являлись измеренным successor bytes-per-level и не являлись capacity commitment**.

Planning-only estimates сохраняются как historical planning evidence:

```text
REPRESENTATIVE_BASELINE_SIZE_MIB≈2.004
REPRESENTATIVE_HOURLY_30D_GIB≈1.409
REPRESENTATIVE_HOURLY_1Y_GIB≈17.14
REPRESENTATIVE_5M_30D_GIB≈16.91
REPRESENTATIVE_5M_1Y_GIB≈205.72
HARD_ENVELOPE_5M_1Y_TIB≈1.776
```

Уточнения:
- representative != capacity commitment;
- Kraken Futures depth не normatively fixed;
- fresh-current NEW observations добавляют bytes сверх baseline;
- reuse добавляет `0` новых historical observation bytes;
- R04 actual successor bytes являются текущим measured proof для six-capability serializer;
- большой estimate сам по себе не разрешает новый storage subsystem.

Текущий GitHub physical profile — approximately-hourly WARM. Future AIFE Server profile ожидается approximately 5-minute, но:

```text
CADENCE_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_BACKEND_IS_NOT_SEMANTIC_IDENTITY=YES
FUTURE_5M_SERVER_SEMANTIC_COMPATIBILITY=REQUIRED
```

Git path, Release asset или будущий server object/file/database locator не меняют observation schema/identity.

## Future server boundary

D8/D9/VPS/provider-authority/AIFE Server — отдельный contour. G1/G2 source semantics не авторизуют:
- D8 provider authority transition;
- D9 activation;
- VPS mutation;
- AIFE Server mutation;
- Binance USD-M GitHub network activation;
- DB-G.

```text
D8_D9_VPS_AIFE_SERVER_SEPARATE_CONTOUR=YES
```

## Поздние этапы

Только после G1 и owner-integrated/qualified G2-A:

```text
G1
→ G2-A
→ G2-B
→ deterministic liquidity profile/summary
→ Research liquidity features
→ point-in-time backtesting
```

Derived metrics должны по возможности детерминированно пересчитываться из canonical historical L2 observations.

## Acceptance gates

```text
IRRETRIEVABLE_L2_HISTORY_RISK_EXPLICIT=YES
S1_S2_S3_ARCHITECTURE_PRESERVED=YES
AGENT_DYNAMIC_DEPTH_REQUEST_PRESERVED=YES
HOURLY_BASELINE_DEFINED=YES
HOURLY_HISTORY_TARGET_BPS=500
SIX_CAPABILITY_BASELINE_SCOPE=DEFINED
FRESH_CURRENT_NEW_OBSERVATION_DURABILITY=IMPLEMENTED_IN_CANDIDATE
NO_FAKE_HISTORY_ON_REUSE=YES
REQUEST_RESOURCE_REMAINS_EPHEMERAL_ONLY=YES
UNDERLYING_OBSERVATION_DURABILITY_CONTRACT=IMPLEMENTED_IN_CANDIDATE
CROSS_RUN_EXACT_RESOURCE_REUSE=NO
EXISTING_LIQUIDITY_SNAPSHOT_FAMILY_REUSED=YES
NEW_PARALLEL_DEEP_HISTORY_FAMILY=NO
PERSIST_PARTIAL_COHERENT_OBSERVATION=YES
TRUNCATED_HANDOFF_DESIGN=RESOLVED
NO_EXTRAPOLATION=YES
LEGACY_100_LEVEL_HISTORY_PRESERVED=YES
LEGACY_FIXED_100_SUCCESSION=COMPLETE
NO_SYNTHETIC_BACKFILL=YES
OBSERVATION_DEDUPE=DEFINED
OBSERVATION_DEDUPE_DESIGN=RESOLVED
OPTION_B_COMPACT_PROVENANCE=YES
HOURLY_DEPENDENCY_INSTALLATION=RESOLVED
CRON_RECONCILIATION=COMPLETE_IN_CANDIDATE
PROMOTION_RETENTION_GATE=RESOLVED
SUCCESSOR_BYTE_BENCHMARK_PLAN=COMPLETED_R04
POINT_IN_TIME_READ_MODEL=EXISTING_FAMILY
NO_LOOKAHEAD=YES
CADENCE_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_BACKEND_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_ESTIMATES_AS_PLANNING_ONLY=YES
G2_ACTUAL_BYTE_BENCHMARK_REQUIRED=YES
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS_R04_REUSED
DURABLE_PUBLICATION_BEFORE_BENCHMARK_PASS=NO
PR402_COUPLED_DRIFT_REVIEW=PASS
PR402_CLASSIFICATION=COMPATIBLE_COUPLED_DRIFT
PR402_REQUIRES_G2A_ARCHITECTURE_REDESIGN=NO
PR402_REQUIRES_G2A_SCOPE_EXPANSION=NO
TEMPORAL_ROLE_SEPARATION_GATE=PASS_IN_CANDIDATE
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
DB_C_VALIDATION_COUPLING_REVIEW=PASS
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_S3_HOST_BINDING_TEST_COUPLED_SCOPE_REVIEW=PASS
G2A_S3_HOST_BINDING_TEST_COUPLED_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_KRAKEN_SPOT_FIRST_ACTUAL_FAILURE_RCA_REVIEW=PASS
G2A_KRAKEN_SPOT_PRODUCTION_JSON_NUMERIC_COMPATIBILITY_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
PRODUCTION_COMPATIBILITY_DEFECT=RESOLVED_R04
EXACT_RUN_ROOT_CAUSE_PROVEN=NO
OBSERVED_FAILURE_CAUSAL_BINDING=HIGH_CONFIDENCE
FLOAT_ACCEPTANCE_WITHOUT_PRECISION_PRESERVATION_SAFE=NO
LIVE_WIRE_NUMERIC_DECODING_COVERAGE_GAP=RESOLVED_R04
MINIMAL_CORRECT_REPAIR_PATH=src/liquidity_s3_executor.py
PROVEN_MINIMUM_COUPLED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH_COUNT=1
AUTHORIZED_SCOPE_EXPANSION_PATH=src/liquidity_s3_executor.py
PREVIOUS_EXACT_IMPLEMENTATION_PATH_COUNT=20
G2A_REAUTHORIZED=YES
EXACT_IMPLEMENTATION_PATH_COUNT=21
NEW_PATH_COUNT=0
SECOND_COLLECTOR=NO
SECOND_S3_EXECUTOR=NO
SECOND_PROVIDER_PLANNER=NO
SECOND_PROMOTION_WORKFLOW=NO
SECOND_HISTORY_READER=NO
SECOND_CAPABILITY_CATALOG=NO
SECOND_DEDUPE_LEDGER=NO
SECOND_TEMPORAL_AUTHORITY=NO
G2A_PREIMPLEMENTATION=PASS
READY_FOR_G2A_IMPLEMENTATION=YES
G2A=CLOSED
G2A_IMPLEMENTATION=COMPLETE
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
OWNER_INTEGRATED=YES
G2_A_OWNER_INTEGRATION=PASS
G2A_OWNER_INTEGRATION=PASS
G2B_STARTED=YES
G2B_IMPLEMENTATION=COMPLETE_IN_CANDIDATE
G2_B_READER_IMPLEMENTED=YES_IN_CANDIDATE
G2B_IMPLEMENTATION_QUALIFICATION=PASS
READY_FOR_G2B_OWNER_INTEGRATION=YES
G2B_OWNER_INTEGRATED=NO
G2B_POSTMERGE_QUALIFIED=NO
LEGACY_FIXED_100_RETIREMENT=COMPLETE_IN_CANDIDATE
BINANCE_FIXED_100_RUNTIME_CHANGED=YES_IN_CANDIDATE
HOURLY_RUNTIME_CHANGED=YES_IN_CANDIDATE
FRESH_CURRENT_RUNTIME_CHANGED=YES_IN_CANDIDATE
PROVIDER_NETWORK_CALLS_PER_CANONICAL_HOURLY_RUN=6
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
SECOND_CONTROLLED_G2A_REQUALIFICATION=NO
D8_PROVIDER_AUTHORITY_TRANSITION=NO
D9_AUTHORITY_ACTIVATION=NO
VPS_MUTATION=NO
AIFE_SERVER_MUTATION=NO
DB_G_STARTED=NO
```

## Resume / continuation

```text
CURRENT_STAGE=G2-A
LAST_CONFIRMED_GATE=G2A_OWNER_REVIEW_PASS_AND_OWNER_CURRENTIZATION
G2A_PREIMPLEMENTATION=PASS
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES
G2A_S3_HOST_BINDING_TEST_COUPLED_SCOPE_REVIEW=PASS
G2A_S3_HOST_BINDING_TEST_COUPLED_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_KRAKEN_SPOT_FIRST_ACTUAL_FAILURE_RCA_REVIEW=PASS
G2A_KRAKEN_SPOT_PRODUCTION_JSON_NUMERIC_COMPATIBILITY_DEFECT=RESOLVED_IN_IMPLEMENTATION_CANDIDATE
G2A_REAUTHORIZED=YES
READY_FOR_G2A_IMPLEMENTATION=YES
R04_REPAIRED_WIP_HEAD=d4726243ff0ab719f668d764a858dd7bea8e1f6d
R04_REPAIRED_WIP_TREE=08764f28c8d8802f89a0fb848dfaa35427f28e7d
R04_PRE_NETWORK_PASS_RUN=33560282658
R04_QUALIFICATION_CARRIER_HEAD=743bb18cdedb414476a0ccdc191a0f7cea9154f3
R04_QUALIFICATION_CARRIER_TREE=83ee5b0dbf9631866c543ec19f37baa06c0baba6
R04_CONTROLLED_QUALIFICATION_RUN=33560525938
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS_R04_REUSED
SECOND_CONTROLLED_G2A_REQUALIFICATION=NO
PHYSICAL_DURABLE_L2_PARTITION=history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json
EVENT_WINDOW_NAMESPACE_COLLISION=RESOLVED
LEGACY_FIXED_100_RETIREMENT=COMPLETE_IN_CANDIDATE
LEGACY_FIXED_100_SUCCESSION=COMPLETE
FRESH_CURRENT_NEW_S3_OBSERVATION_DURABLE_TRANSFER=IMPLEMENTED
G2A=CLOSED
G2A_IMPLEMENTATION=COMPLETE
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
OWNER_INTEGRATED=YES
G2_A_OWNER_INTEGRATION=PASS
G2A_OWNER_INTEGRATION=PASS
G2_B_READER_IMPLEMENTED=NO
G2B_STARTED=NO
NEXT_EXACT_TASK=ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-PREIMPLEMENTATION-OWNER-REVIEW-R01
BLOCKERS=NONE
OUT_OF_SCOPE=G2-B;PROFILE_SUMMARY;RESEARCH_FEATURES;PIT_BACKTEST_IMPLEMENTATION;D8;D9;VPS;AIFE_SERVER;DB-G
```

Owner-currentized G2-A сохраняет R04 production six-capability proof и actual serializer benchmark, не запускает второй controlled provider run и не переносит qualification-carrier trigger в implementation source. Frozen exact21 и `NEW_PATH_COUNT=0` остаются неизменными. Следующий отдельный stage — только G2-B preimplementation owner review; G2-B implementation в этом contour не начат.

## G2-B sampled-history reader successor preimplementation owner review R01 — current successor authority

Этот раздел является **current successor continuation authority** и supersedes только более ранние `CURRENT_STAGE` / `LAST_CONFIRMED_GATE` / `NEXT_EXACT_TASK` continuation markers выше. Все predecessor review sections и исторические доказательства выше сохраняются без переинтерпретации.

### Fresh predecessor и G2-A runtime closeout

```text
G2B_OWNER_REVIEW_TASK=ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-PREIMPLEMENTATION-OWNER-REVIEW-R01
FRESH_SEMANTIC_REBIND_HEAD=0d72449d2f87ee9411526917d3f66d43cc1fad89
FRESH_SEMANTIC_REBIND_TREE=c15838ec8659d32b186a4e19ba625076c3e1c201
FRESH_REBIND_CLASSIFICATION=BENIGN_GENERATED_DATA_ONLY_SUCCESSOR
G2A_REPAIR_PR=448
G2A_REPAIR_MERGE_SHA=80c1c0e6096481d726b3762beeaacf5d0f5dbb44
POST_REPAIR_VALIDATE_RUN=33635550473
POST_REPAIR_VALIDATE=PASS
POST_REPAIR_KRAKEN_OVERLAP_RUN=33635550475
POST_REPAIR_KRAKEN_OVERLAP=PASS
HOURLY_PUBLISHER_RUN=33635872387
HOURLY_PUBLISHER_RESULT=PASS
HOURLY_G2A_WRITER_RUNTIME=PASS
DURABLE_PUBLICATION_READBACK=PASS
EXACT_REPLAY_ISSUE=452
EXACT_REPLAY_RUN=33638011092
EXACT_REPLAY_HEAD=b9c3b42268982e1eac52b0272343e1c429005109
EXACT_REPLAY_RESULT=PASS
UNDECLARED_SAMPLED_CAPABILITY=RESOLVED
COLLECTION_RUN_MISSING=RESOLVED
G2A_RUNTIME_REPAIR=PASS
G2A_RUNTIME_QUALIFICATION=PASS
G2A_RUNTIME_BLOCKERS=NONE
SECOND_ARTIFICIAL_PROVIDER_RUN_FOR_G2A_CLOSEOUT=NO
```

`PROMOTION_PENDING_COUNT` у успешного Fresh Current handoff не является G2-A blocker: canonical durability возникает после существующего hourly harvest/apply/push/read-back, а эта композиция отдельно доказана successful hourly publisher run. Дополнительный artificial provider acquisition для этого review не выполняется.

### Owner verdict и reuse architecture

```text
G2B_PREIMPLEMENTATION_REVIEW=PASS
G2B_ARCHITECTURE=DEFINED
EXISTING_READER_REUSE=YES
HISTORY_FAMILY=liquidity.orderbook-snapshots
SECOND_HISTORY_READER=NO
SECOND_CAPABILITY_CATALOG=NO
SECOND_TEMPORAL_AUTHORITY=NO
SECOND_RESOLVER=NO
SECOND_HISTORY_API=NO
SECOND_OBSERVATION_NORMALIZER=NO
SECOND_LEGACY_COMPATIBILITY_ADAPTER=NO
SECOND_HISTORY_ROOT=NO
DUPLICATE_ARCHITECTURE_COUNT=0
LEGACY_COMPATIBILITY_PLAN=DEFINED
SUCCESSOR_SCHEMA_READ_PLAN=DEFINED
MIXED_SCHEMA_POLICY=DEFINED
POINT_IN_TIME_POLICY=DEFINED
CAPABILITY_RESOLUTION_PLAN=DEFINED
FAIL_CLOSED_POLICY=DEFINED
READY_FOR_G2B_IMPLEMENTATION=YES
G2B_IMPLEMENTATION_STARTED=NO
```

G2-B не создаёт market-data collector, provider route, storage architecture или parallel history API. Он currentizes уже существующий `ResolutionPlan v2` / `history_access` family так, чтобы одна semantic family читала legacy snapshot bytes и G2-A successor durable observations без schema coercion.

### Legacy + successor coexistence

Physical coexistence принимается как намеренная:

```text
LEGACY_PHYSICAL_FAMILY=liquidity/snapshots/**
LEGACY_SCHEMA_VERSION=1.0.0
SUCCESSOR_PHYSICAL_FAMILY=history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json
SUCCESSOR_PARTITION_SCHEMA=liquidity-durable-l2-observation-partition/1.0.0
SUCCESSOR_OBSERVATION_SCHEMA=liquidity-durable-l2-observation/1.0.0
LEGACY_100_LEVEL_HISTORY_VALID=YES
LEGACY_SNAPSHOT_BYTES_MUTATED=NO
NO_SYNTHETIC_BACKFILL=YES
LEGACY_SEMANTIC_UPGRADE=FORBIDDEN
```

Legacy row читается только как legacy snapshot evidence. Successor-only поля, включая 500-bps coverage semantics, observation identity и durable provenance, не фабрикуются для legacy bytes. Successor observation читается как exact durable record с сохранением `provider_id`, `instrument_id`, `book_kind`, `observation_id`, `observation_sha256`, actual bids/asks, actual coverage, `truncated`, `extrapolation_allowed=false`, quantity semantics, acquisition provenance, observation time и known-at.

### Mixed-schema policy

```text
MIXED_SCHEMA_WINDOWS=ALLOWED_EXPLICIT_HETEROGENEOUS_NO_COERCION
SILENT_LEGACY_TO_SUCCESSOR_UPGRADE=NO
SILENT_SUCCESSOR_TO_LEGACY_DOWNGRADE=NO
SILENT_LEGACY_SUBSTITUTION=NO
UNKNOWN_FUTURE_SCHEMA=FAIL_CLOSED
```

Mixed window может содержать обе schema только как явно различимые observations одной semantic family. Reader не объединяет legacy и successor payload в один синтетический snapshot и не скрывает schema boundary. Unknown/missing successor partition или observation schema fail-closed; consumer, требующий coercion в единую successor schema, должен получить explicit failure, а не fabricated completeness.

### PIT / no-lookahead authority

```text
POINT_IN_TIME_AUTHORITY=EXISTING_RESOLUTION_PLAN_HISTORY_AUTHORITY
SECOND_TEMPORAL_MODEL=NO
OBSERVATION_TIME_ROLE=MARKET_OBSERVATION_TIME
KNOWN_AT_ROLE=AVAILABILITY_TO_EXECUTION_PATH
PUBLICATION_TIME_ROLE=STORAGE_PROVENANCE_ONLY
REQUEST_TIME_ROLE=REQUEST_PROVENANCE_ONLY
ARTIFACT_TIME_ROLE=TRANSPORT_PROVENANCE_ONLY
GITHUB_RUN_TIME_ROLE=EXECUTION_PROVENANCE_ONLY
KNOWN_AT_AFTER_CUTOFF=EXCLUDED
NO_LOOKAHEAD=YES
```

Legacy sampled rows сохраняют existing collection-run `known_at <= cutoff` authority. Successor observation использует собственный persisted `known_at_utc <= cutoff`; `observation_time_ms` определяет market timestamp, но не заменяет availability cutoff. Resolver обязан исключить successor observation, которая ещё не была known-at к requested cutoff; reader обязан revalidate temporal/schema binding fail-closed, чтобы forged/stale ResolutionPlan не мог протащить future observation.

### Capability resolution и physical locator

```text
CAPABILITY_ID=liquidity.orderbook-snapshots
CAPABILITY_RESOLVER=tools/capability_index.py
RESOLUTION_IMPLEMENTATION=tools/resolution_v2.py
PUBLIC_READER=tools/history_access.py
READER_IMPLEMENTATION=tools/history_access_v2.py
CAPABILITY_PATH_GUESSING=FORBIDDEN
READER_LOCAL_CAPABILITY_REGISTRY=FORBIDDEN
PROVIDER_FALLBACK=FORBIDDEN
DIRECT_PROVIDER_FROM_G2B=FORBIDDEN
```

`tools/resolution_v2.py` должен использовать существующие `bridge-contract.json` / `contracts/liquidity-durable-l2-observation-v1.json` declarations для canonical successor locator и schema, а не hard-code второй catalog. Existing runtime-projected capability `liquidity.orderbook-snapshots` остаётся единственным semantic ID. ResolutionPlan может составлять legacy ledger-backed segments и successor partition segments в одном ordered window, сохраняя для каждого сегмента достаточную schema/integrity/temporal evidence.

### Immutable identity и dedupe read semantics

```text
OBSERVATION_DEDUPE=provider_id+instrument_id+book_kind+observation_id
OBSERVATION_CONTENT_BINDING=observation_sha256
SAME_IDENTITY_SAME_SHA=IDEMPOTENT_DUPLICATE
SAME_IDENTITY_DIFFERENT_SHA=FAIL_CLOSED_IMMUTABLE_OBSERVATION_CONFLICT
READER_GENERATES_NEW_SEMANTIC_IDENTITY=NO
READER_REWRITES_STORED_OBSERVATION=NO
```

Reader может collapse только exact same-identity/same-SHA duplicate. Same identity + different SHA не скрывается и не merge-ится. Legacy rows не получают synthetic successor identity.

### Partial / truncated / Fresh Current boundary

```text
PARTIAL_TO_COMPLETE_UPGRADE=FORBIDDEN
TRUNCATED_TO_COMPLETE_UPGRADE=FORBIDDEN
UNKNOWN_TO_COMPLETE_UPGRADE=FORBIDDEN
EXTRAPOLATION_ALLOWED=false
FRESH_CURRENT_IS_CANONICAL_HISTORY_READER=NO
CURRENT_DATA_SUBSTITUTION_FOR_MISSING_HISTORY=FORBIDDEN
G2B_PROVIDER_NETWORK_CALLS=0
```

Правильная композиция:

```text
Fresh Current
→ optional G2-A promotion
→ canonical durable history
→ existing G2-B history reader family
```

Запрещённая композиция:

```text
G2-B reader
→ direct provider
```

### Frozen future implementation contract

G2-B runtime implementation в этом review **не выполняется**. Следующая отдельная implementation task обязана использовать только следующий frozen path-set, пока новый coupled invariant не доказан отдельным owner review.

```text
FUTURE_IMPLEMENTATION_TASK=ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-IMPLEMENTATION-R01
EXACT_IMPLEMENTATION_PATH_COUNT=9
EXACT_IMPLEMENTATION_PATHS=
tools/resolution_v2.py
tools/history_access_v2.py
tools/validation/validate_d9_resolution_v2.py
tests/deep_history/test_d9_resolution_v2.py
tests/deep_history/test_d9_public_resolution_v2.py
bridge-contract.json
contracts/liquidity-durable-l2-observation-v1.json
docs/semantics/deep-liquidity-program-map-v1.md
AGENTS.md

MODIFY_PATHS=
tools/resolution_v2.py
tools/history_access_v2.py
tools/validation/validate_d9_resolution_v2.py
tests/deep_history/test_d9_resolution_v2.py
tests/deep_history/test_d9_public_resolution_v2.py
bridge-contract.json
contracts/liquidity-durable-l2-observation-v1.json
docs/semantics/deep-liquidity-program-map-v1.md
AGENTS.md

ADD_PATHS=NONE
NEW_PATH_COUNT=0

REUSE_ONLY_PATHS=
tools/capability_index.py
tools/history_access.py
history/capability-index.json
src/sampled_history.py
src/history_store.py
tests/deep_history/test_d9_sampled_history.py
tests/deep_history/test_d9_liquidity_reproducibility.py
history/liquidity-orderbook-snapshots/**
liquidity/snapshots/**
history/collection-runs/**

FORBIDDEN_PATHS=
.github/workflows/update-market.yml
.github/workflows/current-data-request.yml
src/collector.py
src/liquidity_s1_runtime.py
src/liquidity_s2_binance_adapter.py
src/liquidity_s2_kraken_spot.py
src/liquidity_s2_kraken_futures.py
src/liquidity_s3_executor.py
new history reader/catalog/resolver/backend paths
D8/D9 activation or cutover paths
VPS/AIFE-server paths
```

Governance files в frozen implementation scope разрешены только для truthful post-implementation status/contract currentization после successful runtime qualification; они не разрешают architecture reselection.

### Three-question review proposed mutation paths

1. `tools/resolution_v2.py` — Q1: successor canonical partitions должны стать resolvable внутри existing family с PIT filtering; Q2: этот path уже владеет ResolutionPlan v2 и sampled segments; Q3: без него successor durable bytes остаются невидимыми canonical resolver-у. `PROPOSED_PATH=ACCEPT`.
2. `tools/history_access_v2.py` — Q1: reader должен schema-aware декодировать successor partition и fail-closed на unknown/coercion/conflict; Q2: это existing v2 materializer за public `tools/history_access.py`; Q3: без него partition object будет интерпретирован как legacy sampled payload либо останется недоказанным. `PROPOSED_PATH=ACCEPT`.
3. `tools/validation/validate_d9_resolution_v2.py` — Q1: canonical validator обязан доказать no-second-reader/catalog, successor resolution и no-lookahead guards; Q2: это existing D9 v2 resolution validator; Q3: без него repository gate не доказывает новый reader contract. `PROPOSED_PATH=ACCEPT`.
4. `tests/deep_history/test_d9_resolution_v2.py` — Q1: нужны adversarial schema/PIT/mixed-window/conflict regressions на resolver/materializer seam; Q2: это existing v2 resolution semantic test owner; Q3: без него internal policy не имеет deterministic regression proof. `PROPOSED_PATH=ACCEPT`.
5. `tests/deep_history/test_d9_public_resolution_v2.py` — Q1: public `capability_index.py → ResolutionPlan v2 → history_access.py` route должен доказать successor read без второго entrypoint; Q2: этот test уже владеет public v2 dispatch contract; Q3: без него internal tests не доказывают agent-callable reuse. `PROPOSED_PATH=ACCEPT`.
6. `bridge-contract.json` — Q1: после implementation machine authority должна truthful отметить G2-B reader implemented/qualified, сохранив default D9 activation отдельно; Q2: contract уже владеет route/status machine declarations; Q3: без него runtime и machine authority разойдутся. `PROPOSED_PATH=ACCEPT`.
7. `contracts/liquidity-durable-l2-observation-v1.json` — Q1: durable observation contract должен currentize reader-side successor/legacy/PIT acceptance после implementation; Q2: он владеет durable L2 schema/history bindings; Q3: без него reader semantics останется только кодовой импликацией. `PROPOSED_PATH=ACCEPT`.
8. `docs/semantics/deep-liquidity-program-map-v1.md` — Q1: owner map должен закрыть G2-B implementation gate и установить следующий stage; Q2: это единственная repository-owned continuation map; Q3: без него continuation снова станет stale. `PROPOSED_PATH=ACCEPT`.
9. `AGENTS.md` — Q1: canonical entrypoint должен discoverable отражать implemented G2-B route/status после qualification; Q2: это первая semantic точка входа; Q3: без него следующий агент увидит stale G2-A/G2-B state. `PROPOSED_PATH=ACCEPT`.

### Required implementation invariants and negative tests

```text
INVARIANTS=
ONE_ACQUISITION_PATH=S1_TO_S2_TO_S3
ONE_HISTORY_FAMILY=liquidity.orderbook-snapshots
ONE_PUBLIC_READER=tools/history_access.py
ONE_CAPABILITY_RESOLVER=tools/capability_index.py
LEGACY_BYTES_IMMUTABLE=YES
NO_SYNTHETIC_BACKFILL=YES
NO_LOOKAHEAD=YES
NO_SCHEMA_COERCION=YES
NO_EXTRAPOLATION=YES
NO_PROVIDER_FALLBACK=YES
NO_CURRENT_DATA_SUBSTITUTION=YES
D9_DEFAULT_ACTIVATION_UNCHANGED=YES

NEGATIVE_TESTS=
unknown successor partition schema -> FAIL_CLOSED
unknown successor observation schema -> FAIL_CLOSED
missing successor schema -> FAIL_CLOSED
legacy row treated as successor -> FAIL_CLOSED
successor row treated as legacy -> FAIL_CLOSED
partial/truncated/unknown upgraded to complete -> FAIL_CLOSED
successor known_at > cutoff -> EXCLUDED/FAIL_CLOSED_ON_FORGED_PLAN
same identity + different sha -> FAIL_CLOSED
capability path guessed -> FAIL_CLOSED
provider fallback in reader -> FAIL_CLOSED
mixed window silent coercion -> FAIL_CLOSED
missing successor history replaced by current snapshot -> FAIL_CLOSED
historical result replaced by Fresh Current -> FAIL_CLOSED

TARGETED_TESTS=
python -m unittest tests.deep_history.test_d9_resolution_v2 -v
python -m unittest tests.deep_history.test_d9_public_resolution_v2 -v
python -m unittest tests.deep_history.test_d9_sampled_history -v
python -m unittest tests.deep_history.test_d9_liquidity_reproducibility -v

CANONICAL_VALIDATORS=
PYTHONPATH=src:tools/deep_history python tools/validation/validate_d9_resolution_v2.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

### Implementation stop codes

```text
G2B_IMPLEMENTATION_AUTHORITY_DRIFT_REQUIRES_REBIND
G2B_SCOPE_EXPANSION_REQUIRES_OWNER_REVIEW
G2B_UNKNOWN_LIQUIDITY_PARTITION_SCHEMA
G2B_UNKNOWN_LIQUIDITY_OBSERVATION_SCHEMA
G2B_MISSING_LIQUIDITY_SCHEMA
G2B_LEGACY_AS_SUCCESSOR_COERCION_FORBIDDEN
G2B_SUCCESSOR_AS_LEGACY_COERCION_FORBIDDEN
G2B_SCHEMA_COERCION_FORBIDDEN
G2B_KNOWN_AT_AFTER_CUTOFF
G2B_IMMUTABLE_OBSERVATION_CONFLICT
G2B_GUESSED_PATH_FORBIDDEN
G2B_PROVIDER_FALLBACK_FORBIDDEN
G2B_CURRENT_DATA_SUBSTITUTION_FORBIDDEN
G2B_PARTIAL_COMPLETENESS_UPGRADE_FORBIDDEN
G2B_EXTRAPOLATION_FORBIDDEN
G2B_IMPLEMENTATION_QUALIFICATION_FAILED
```

```text
OWNER_REVIEW_BINDING=ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-PREIMPLEMENTATION-OWNER-REVIEW-R01
PREDECESSOR_AUTHORITY_BINDING=G2A_POSTMERGE_RUNTIME_INTEGRATION_REPAIR_AND_RUNTIME_QUALIFICATION_COMPLETE
```

### Current successor continuation

```text
CURRENT_STAGE=G2-B_IMPLEMENTATION_CANDIDATE
LAST_CONFIRMED_GATE=G2B_IMPLEMENTATION_QUALIFICATION_PASS_IN_CANDIDATE
G2A=CLOSED
G2A_RUNTIME_REPAIR=PASS
G2A_RUNTIME_QUALIFICATION=PASS
UNDECLARED_SAMPLED_CAPABILITY=RESOLVED
COLLECTION_RUN_MISSING=RESOLVED
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
G2A_RUNTIME_BLOCKERS=NONE
G2B_PREIMPLEMENTATION_REVIEW=PASS
G2B_ARCHITECTURE=DEFINED
EXISTING_READER_REUSE=YES
LEGACY_COMPATIBILITY_PLAN=IMPLEMENTED_AND_QUALIFIED
SUCCESSOR_SCHEMA_READ_PLAN=IMPLEMENTED_AND_QUALIFIED
MIXED_SCHEMA_POLICY=IMPLEMENTED_AND_QUALIFIED
POINT_IN_TIME_POLICY=IMPLEMENTED_AND_QUALIFIED
CAPABILITY_RESOLUTION_PLAN=IMPLEMENTED_AND_QUALIFIED
FAIL_CLOSED_POLICY=IMPLEMENTED_AND_QUALIFIED
DUPLICATE_ARCHITECTURE_COUNT=0
EXACT_IMPLEMENTATION_PATH_COUNT=9
NEW_PATH_COUNT=0
G2B_STARTED=YES
G2B_IMPLEMENTATION_STARTED=YES
G2B_IMPLEMENTATION=COMPLETE_IN_CANDIDATE
G2_B_READER_IMPLEMENTED=YES_IN_CANDIDATE
G2B_IMPLEMENTATION_QUALIFICATION=PASS
READY_FOR_G2B_OWNER_INTEGRATION=YES
G2B_OWNER_INTEGRATED=NO
G2B_POSTMERGE_QUALIFIED=NO
D9_AUTHORITY_ACTIVATION=NO
NEXT_EXACT_TASK=ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-OWNER-MERGE-AND-POSTMERGE-QUALIFICATION-R01
BLOCKERS=NONE
OUT_OF_SCOPE=PROFILE_SUMMARY;RESEARCH_FEATURES;PIT_BACKTEST_IMPLEMENTATION;D8;D9_ACTIVATION;VPS;AIFE_SERVER;DB-G
```

G2-B implementation завершён внутри frozen exact9 candidate без provider/network execution и без второго reader/resolver/catalog/temporal authority. Runtime, targeted и full repository qualification прошли; owner integration и post-merge qualification намеренно не выполнялись и остаются отдельным следующим exact task. D9 default authority не активирован.