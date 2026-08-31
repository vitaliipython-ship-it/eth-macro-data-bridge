# Каноническая программа deep-liquidity: G1/G2

`docs/semantics/deep-liquidity-program-map-v1.md` — единственная repository-owned карта продолжения канонического deep-liquidity контура. Внешний owner-review `ETH_LIQUIDITY_G1_G2_DURABILITY_PROGRAM_MAP_EXPANSION_R01.md` остается `EVIDENCE_ONLY`: он не нужен для восстановления текущего состояния из `AGENTS.md`.

## Текущее состояние

```text
DB-C=CLOSED
DB-D1=CLOSED
DB-D2=CLOSED
DB_F_S3=CLOSED
CURRENT_STAGE=G1
```

DB-F/S3 уже дает request-aware bounded acquisition через один существующий маршрут `S1 → S2 → S3`. G1 не переопределяет этот маршрут и не активирует writer.

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
NO_EXTRAPOLATION=YES
```

Target miss не превращает наблюденный coherent book в «не существовавший» market fact. Actual coverage сохраняется честно. Request satisfaction по-прежнему остается отдельным S1 verdict и может быть FAIL/PARTIAL.

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
```

`observation_sha256` — immutable content binding.

```text
SAME_IDENTITY_SAME_SHA=IDEMPOTENT_DUPLICATE
SAME_IDENTITY_DIFFERENT_SHA=FAIL_CLOSED_IMMUTABLE_OBSERVATION_CONFLICT
```

Request identity, cadence, storage locator, Issue/run/artifact identity не участвуют в semantic observation identity. Используется существующий immutable `history_store`, второй ledger не создается.

### Compact provenance

```text
PROVENANCE_DECISION=OPTION_B_COMPACT_STABLE_ACQUISITION_PROVENANCE_DIGESTS
```

Durable fact хранит canonical observation плюс минимальные стабильные bindings: provider plan/capability SHA, S3 policy/receipt SHA, route/endpoint/action binding digests, one-observation/one-request-or-session proof и provider-specific coherence/integrity evidence. Полный transient S3 receipt не сохраняется forever по умолчанию.

### G2-A обязательства перед активацией

1. `TRUNCATED_OBSERVATION_HANDOFF_MUST_NOT_DEPEND_ON_REQUEST_PASS=YES`.
2. Hourly runtime устанавливает уже существующую pinned WebSocket dependency.
3. Promotion artifact retention должен быть больше declared durable-publisher recovery SLO.
4. Stale cron declaration (`bridge` vs фактический workflow) должен быть reconciled, при этом exact minute не становится semantic identity.
5. Два Binance Spot fixed-100 calls retire атомарно с successor activation.
6. `ACTUAL_SUCCESSOR_BYTE_BENCHMARK_REQUIRED=YES`.

До writer activation G2-A обязан измерить фактически produced successor observations per provider/instrument и опубликовать: observation size, baseline generation size, hourly 30-day/1-year projections и representative future 5-minute projection.

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
NO_EXTRAPOLATION=YES
LEGACY_100_LEVEL_HISTORY_PRESERVED=YES
LEGACY_FIXED_100_SUCCESSION=G2_A
NO_SYNTHETIC_BACKFILL=YES
OBSERVATION_DEDUPE=DEFINED
OPTION_B_COMPACT_PROVENANCE=YES
POINT_IN_TIME_READ_MODEL=EXISTING_FAMILY
NO_LOOKAHEAD=YES
CADENCE_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_BACKEND_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_ESTIMATES_AS_PLANNING_ONLY=YES
G2_ACTUAL_BYTE_BENCHMARK_REQUIRED=YES
SECOND_COLLECTOR=NO
SECOND_S3_EXECUTOR=NO
SECOND_PROVIDER_PLANNER=NO
SECOND_PROMOTION_WORKFLOW=NO
SECOND_HISTORY_READER=NO
SECOND_CAPABILITY_CATALOG=NO
SECOND_DEDUPE_LEDGER=NO
SECOND_TEMPORAL_AUTHORITY=NO
G2_WRITER_IMPLEMENTED=NO
G2_READER_IMPLEMENTED=NO
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
CURRENT_STAGE=G1
LAST_CONFIRMED_GATE=G1_CONTRACT_IMPLEMENTATION_CANDIDATE_QUALIFIED_PENDING_OWNER_INTEGRATION
NEXT_EXACT_TASK=G1_OWNER_PR_INTEGRATION_AND_POSTMERGE_READBACK
BLOCKERS=NONE
OUT_OF_SCOPE=G2-A;G2-B;PROFILE_SUMMARY;RESEARCH_FEATURES;PIT_BACKTEST_IMPLEMENTATION;D8;D9;VPS;AIFE_SERVER;DB-G
```

После owner merge/read-back program map должен быть currentized прежде, чем G2-A начнет writer implementation.
