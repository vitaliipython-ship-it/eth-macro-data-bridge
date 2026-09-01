# Каноническая программа deep-liquidity: G1/G2

`docs/semantics/deep-liquidity-program-map-v1.md` — единственная repository-owned карта продолжения канонического deep-liquidity контура. Внешний owner-review `ETH_LIQUIDITY_G1_G2_DURABILITY_PROGRAM_MAP_EXPANSION_R01.md` остается `EVIDENCE_ONLY`: он не нужен для восстановления текущего состояния из `AGENTS.md`.

## Текущее состояние

```text
DB-C=CLOSED
DB-D1=CLOSED
DB-D2=CLOSED
DB_F_S3=CLOSED
G1=CLOSED
CURRENT_STAGE=G2-A
G2A_PREIMPLEMENTATION=PASS
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=CONFIRMED
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES
G2A_REAUTHORIZED=YES
READY_FOR_G2A_IMPLEMENTATION=YES
```

DB-F/S3 уже дает request-aware bounded acquisition через один существующий маршрут `S1 → S2 → S3`. G1 contract установлен и owner-integrated; writer в repository authority остаётся неактивным. G2-A preimplementation owner review завершён. PR #402 owner-reviewed как compatible coupled drift. Последующий implementation WIP доказал stale coupling DB-C validation к legacy Binance Spot fixed-100 runtime; после его owner currentization canonical diagnostic доказал `HTTP 451` на текущем Binance Spot general REST host. First-party Binance documentation подтверждает отдельный market-data-only host для public market data, поэтому owner review авторизует single canonical host requalification без изменения S1→S2→S3 architecture и без runtime mutation в этой governance задаче.

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
G2_A_WRITER_IMPLEMENTED=NO
G2_B_READER_IMPLEMENTED=NO
PROVIDER_NETWORK_CALLS=0
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

Только новая фактическая S3 acquisition может дать новый historical observation. Reuse уже существующего resource не создает новый market timestamp и не дублирует историю.

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
LEGACY_FIXED_100_SUCCESSION=G2_A_REQUIRED
NO_SYNTHETIC_BACKFILL=YES
```

G2-A обязан атомарно убрать два duplicate Binance Spot `limit=100` network calls (ETHUSDT/BTCUSDT) только одновременно с активацией canonical S3 hourly baseline. Legacy history не переименовывается в 500-bps complete: доступно только то, что доказывают stored levels; неизвестное остается UNKNOWN.

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

```text
G2A_PREIMPLEMENTATION_REVIEW=PASS
G2A_IMPLEMENTATION_STARTED=NO
READY_FOR_G2A_IMPLEMENTATION=YES
NEW_PATH_COUNT=0
```

### Exact implementation mutation scope

G2-A implementation обязан оставаться в следующем точном минимальном наборе существующих paths, если implementation не обнаружит доказанный новый coupled invariant. Любое расширение требует нового owner review до mutation.

```text
EXACT_IMPLEMENTATION_PATH_COUNT=19
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
```

Следующие existing paths являются reuse-only для G2-A и не входят в frozen mutation scope без нового доказанного coupled invariant:

```text
src/collector.py
src/liquidity_s1_runtime.py
src/liquidity_s2_kraken_spot.py
src/liquidity_s2_kraken_futures.py
src/liquidity_s3_executor.py
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

Фактический durable publisher остаётся `.github/workflows/update-market.yml`; его текущий schedule — `17 * * * *`. Историческая декларация `35 * * * *` в current-data semantics/bridge metadata является stale declaration и не является cadence authority.

```text
CRON_RECONCILIATION=RESOLVED
ACTUAL_DURABLE_PUBLISHER_CRON=17 * * * *
DECLARATION_TARGET_CRON=17 * * * *
CRON_MINUTE_IS_SEMANTIC_IDENTITY=NO
CRON_RECONCILIATION_OWNER_PATHS=
bridge-contract.json
docs/semantics/fresh-current-agent-transport-v1.md
```

G2-A implementation обязана currentize stale declarations до фактического `17 * * * *` до writer activation. Сам cadence в этой preimplementation currentization не меняется.

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

Preimplementation review provider calls/probes не выполняет; benchmark является pre-activation gate будущей implementation задачи.

### Атомарность legacy succession

```text
LEGACY_FIXED_100_RETIREMENT=ATOMIC_WITH_WORKING_HOURLY_SUCCESSOR
FIXED_100_REMOVAL_BEFORE_SUCCESSOR_PASS=FORBIDDEN
```

Два Binance Spot fixed-100 calls в `src/intelligence.py` retire только в той же implementation candidate, где six-capability hourly successor, durability serialization, dependency installation, dedupe и publisher integration проходят acceptance gates.

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

Два newly-authorized paths должны быть **currentized, а не ослаблены** будущей implementation. Existing DB-C validator обязан перейти от obsolete shallow-preservation invariant к successor-aware proof: legacy Binance Spot fixed-100 calls отсутствуют; canonical Spot hourly owner — существующий G2-A `S1→S2→S3` durable successor; Binance USD-M остаётся `DISABLED_BY_POLICY`; DB-C provider qualification, no-pagination, no sequential REST stitching, no extrapolation и S2 ownership сохраняются. Executable DB-C regression должен защищать те же границы и не смешивать S2 adapter с S3/writer ownership.

Scope authorization не является доказательством отсутствия любых будущих coupled blockers. Если subsequent full CI докажет необходимость нового path вне current exact 19, implementation обязана остановиться:

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

Actual six-capability provider benchmark в owner-governance task не выполнялся. Historical WIP ordering может быть использован только как implementation substrate; он не заменяет actual network benchmark и не является accepted implementation candidate после governance merge.

## G2-A Binance Spot public market-data endpoint viability owner review R01

Canonical diagnostic `33519578314` на exact head `6aecfc6d06e1986f9426bdddb08a2725f9c9567c` выполнил одну physical attempt для первого baseline capability и fail-closed получил HTTP `451` через текущий Binance Spot REST plan. S3 classification остаётся coarse execution class и не доказывает более узкую provider-specific причину.

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

Owner decision использует самый узкий механизм: один canonical host для того же provider, того же endpoint path и того же S1→S2→S3 route. `api.binance.com` не объявляется stale/unsupported; для G2-A public-only acquisition авторизуется requalification через официальный market-data-only host. Это authorization на controlled requalification, а не доказательство, что HTTP `451` уже устранён.

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

Exact source ownership показывает, что canonical Spot host принадлежит `contracts/provider-contracts.json`, а `src/liquidity_s2_binance_adapter.py` revalidate'ит этот contract и материализует `canonical_base_host` в provider plan. S3 executor только исполняет validated plan и отдельного Binance Spot host не hard-code'ит. Поэтому required implementation expansion ограничивается двумя existing paths; новых файлов, второго executor или fallback mechanism не требуется.

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
3. **Уменьшает ли решение число действий следующего агента?** Да: следующий implementation currentizes только два owner-authorized host paths, выполняет одну canonical six-capability qualification и продолжает прежний G2-A task только после PASS.

Новый provider network attempt в этой governance задаче не выполняется. Actual viability `data-api.binance.vision` должна быть доказана в следующей implementation qualification; любой capability FAIL требует STOP с exact S3 receipt.

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

`tools/current_tail_admission.py` остаётся owner Fresh Current tail/PIT admission и не становится owner L2 market observation timestamp. Для newly acquired S3 L2 observation implementation обязана брать observation time только из `normalized_book.timestamp_ms`; generation/known-at/workflow/request/publication timestamps запрещено использовать как surrogate observation time. Если корректный known-at фактически не доказуем, он не фабрикуется.

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
STORAGE_ESTIMATE_STATUS=REPRESENTATIVE_PLANNING_ESTIMATE_NOT_MEASURED_SUCCESSOR_BYTES
```

Predecessor arithmetic использовала legacy liquidity snapshot как консервативный planning anchor; legacy file содержит не только две Binance Spot книги, но и дополнительные Deribit books. Поэтому эти числа **не являются измеренным successor bytes-per-level и не являются capacity commitment**.

Planning-only estimates:

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
- actual successor payload должен быть измерен в G2-A до writer activation;
- большой estimate сам по себе не разрешает новый storage subsystem.

Текущий GitHub physical profile — временный approximately-hourly WARM. Future AIFE Server profile ожидается approximately 5-minute, но:

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

Только после G1 и G2:

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
FRESH_CURRENT_NEW_OBSERVATION_DURABILITY=DEFINED
NO_FAKE_HISTORY_ON_REUSE=YES
REQUEST_RESOURCE_REMAINS_EPHEMERAL_ONLY=YES
UNDERLYING_OBSERVATION_DURABILITY_CONTRACT=DEFINED
CROSS_RUN_EXACT_RESOURCE_REUSE=NO
EXISTING_LIQUIDITY_SNAPSHOT_FAMILY_REUSED=YES
NEW_PARALLEL_DEEP_HISTORY_FAMILY=NO
PERSIST_PARTIAL_COHERENT_OBSERVATION=YES
TRUNCATED_HANDOFF_DESIGN=RESOLVED
NO_EXTRAPOLATION=YES
LEGACY_100_LEVEL_HISTORY_PRESERVED=YES
LEGACY_FIXED_100_SUCCESSION=G2_A
NO_SYNTHETIC_BACKFILL=YES
OBSERVATION_DEDUPE=DEFINED
OBSERVATION_DEDUPE_DESIGN=RESOLVED
OPTION_B_COMPACT_PROVENANCE=YES
HOURLY_DEPENDENCY_INSTALLATION=RESOLVED
CRON_RECONCILIATION=RESOLVED
PROMOTION_RETENTION_GATE=RESOLVED
SUCCESSOR_BYTE_BENCHMARK_PLAN=RESOLVED
POINT_IN_TIME_READ_MODEL=EXISTING_FAMILY
NO_LOOKAHEAD=YES
CADENCE_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_BACKEND_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_ESTIMATES_AS_PLANNING_ONLY=YES
G2_ACTUAL_BYTE_BENCHMARK_REQUIRED=YES
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=NO
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PENDING_IMPLEMENTATION_CONTINUATION
DURABLE_PUBLICATION_BEFORE_BENCHMARK_PASS=NO
PR402_COUPLED_DRIFT_REVIEW=PASS
PR402_CLASSIFICATION=COMPATIBLE_COUPLED_DRIFT
PR402_REQUIRES_G2A_ARCHITECTURE_REDESIGN=NO
PR402_REQUIRES_G2A_SCOPE_EXPANSION=NO
TEMPORAL_ROLE_SEPARATION_GATE=REQUIRED
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=CONFIRMED
DB_C_VALIDATION_COUPLING_REVIEW=PASS
PROVEN_MINIMUM_COUPLED_SCOPE_EXPANSION_PATH_COUNT=2
AUTHORIZED_SCOPE_EXPANSION_PATH_COUNT=2
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
DIAGNOSTIC_HTTP_STATUS=451
DIAGNOSTIC_S3_CLASS=PROVIDER_REJECTION_OR_RATE_LIMIT
RATE_LIMIT_CAUSE_PROVEN=NO
GEO_BLOCK_CAUSE_PROVEN=NO
GITHUB_IP_CAUSE_PROVEN=NO
HTTP_451_PROVIDER_SPECIFIC_SEMANTICS=NOT_NORMATIVELY_DOCUMENTED
CURRENT_CANONICAL_ROUTE_ALIGNED_WITH_FIRST_PARTY_MARKET_DATA_ONLY_GUIDANCE=NO
SINGLE_CANONICAL_HOST_SUCCESSION_AUTHORIZED=YES
AUTHORIZED_BINANCE_SPOT_BASE_HOST=https://data-api.binance.vision
ACTUAL_REQUALIFICATION_REQUIRED=YES
HTTP_451_RESOLUTION_PROVEN=NO
PROVEN_COUPLED_SCOPE_EXPANSION_PATH_COUNT=2
G2A_REAUTHORIZED=YES
EXACT_IMPLEMENTATION_PATH_COUNT=19
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
G2_A_WRITER_IMPLEMENTED=NO
G2_B_READER_IMPLEMENTED=NO
LEGACY_FIXED_100_RETIREMENT=NOT_YET_COMPLETE
BINANCE_FIXED_100_RUNTIME_CHANGED=NO
HOURLY_RUNTIME_CHANGED=NO
FRESH_CURRENT_RUNTIME_CHANGED=NO
PROVIDER_NETWORK_CALLS=0
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
D8_PROVIDER_AUTHORITY_TRANSITION=NO
D9_AUTHORITY_ACTIVATION=NO
VPS_MUTATION=NO
AIFE_SERVER_MUTATION=NO
DB_G_STARTED=NO
```

## Resume / continuation

```text
CURRENT_STAGE=G2-A
LAST_CONFIRMED_GATE=G2A_BINANCE_SPOT_PUBLIC_MARKET_DATA_ENDPOINT_VIABILITY_OWNER_REVIEW_AND_GOVERNANCE_REAUTHORIZATION_PASS
G2A_PREIMPLEMENTATION=PASS
G2A_COUPLED_DB_C_VALIDATION_SCOPE_REVIEW=PASS
G2A_COUPLED_DB_C_VALIDATION_DEFECT=CONFIRMED
G2A_BINANCE_SPOT_PROVIDER_EXECUTION_VIABILITY_REVIEW=PASS
G2A_BINANCE_SPOT_HOST_REAUTHORIZED=YES
G2A_REAUTHORIZED=YES
READY_FOR_G2A_IMPLEMENTATION=YES
DIAGNOSTIC_WIP_HEAD=6aecfc6d06e1986f9426bdddb08a2725f9c9567c
DIAGNOSTIC_WIP_TREE=ea6bfbb997b06ef0f868c465107a7d20f9070c65
DIAGNOSTIC_CI_RUN=33519578314
NEXT_EXACT_TASK=ETH-LIQUIDITY-G2A-HOURLY-BASELINE-FRESH-CURRENT-DURABLE-ACCUMULATION-AND-LEGACY-FIXED-DEPTH-SUCCESSION-IMPLEMENTATION-R01
CONTINUATION_MODE=RESUME_DIAGNOSTIC_G2A_WIP_ON_FRESH_POST_GOVERNANCE_AUTHORITY_WITH_OWNER_AUTHORIZED_SINGLE_BINANCE_SPOT_MARKET_DATA_ONLY_HOST_SUCCESSION
BLOCKERS=NONE
OUT_OF_SCOPE=G2-B;PROFILE_SUMMARY;RESEARCH_FEATURES;PIT_BACKTEST_IMPLEMENTATION;D8;D9;VPS;AIFE_SERVER;DB-G
```

G2-A Binance Spot provider execution viability owner review завершён: frozen implementation scope расширен с 17 до 19 существующих paths только за счёт canonical host owner contract и Binance Spot S2 adapter. Runtime host в этой governance задаче не переключался, actual six-capability benchmark не выполнялся, legacy fixed-100 retirement не предпринимался. Следующий агент обязан fresh-read post-governance `main`, materialize diagnostic WIP `6aecfc6d06e1986f9426bdddb08a2725f9c9567c` поверх новой authority корректным Git способом, currentize только owner-authorized Binance Spot host owner paths и выполнить одну canonical six-capability qualification. При первом FAIL — STOP с exact S3 receipt; только после all-six PASS выполнять actual successor serializer byte benchmark и затем продолжать atomic legacy fixed-100 retirement в том же G2-A implementation Task-ID.