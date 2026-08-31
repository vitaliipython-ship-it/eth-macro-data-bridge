# G1: durable L2 observation contract

## Зачем нужен G1

DB-F/S3 уже умеет по semantic request получить один bounded coherent L2 observation. До G1 оставалась другая проблема: **сам факт рынка мог быть использован для current analysis и затем исчезнуть как историческая точка**. Для order book это принципиально: точное состояние в прошлом обычно нельзя надежно восстановить позднее простым повторным provider request.

G1 закрывает только неоднозначность durable semantics. Writer, promotion и reader behavior этим этапом не активируются.

Machine authority:

```text
CONTRACT_ID=ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1
CONTRACT_PATH=contracts/liquidity-durable-l2-observation-v1.json
FAMILY=liquidity.orderbook-snapshots
```

## Market observation не равен request resource

Exact S3 request resource отвечает на вопрос конкретного consumer: хватило ли freshness, coverage и completeness для его request. Поэтому он остается:

```text
REQUEST_SPECIFIC_EXACT_RESOURCE_DURABILITY=EPHEMERAL_ONLY
CROSS_RUN_EXACT_RESOURCE_REUSE=NO
ACTIONS_ARTIFACT_AS_CROSS_RUN_CACHE=NO
```

Underlying market observation отвечает на другой вопрос: **какой coherent book реально наблюдал provider в конкретный момент**. Этот факт может стать canonical history независимо от того, удовлетворил ли он исходный request.

Request SHA, Issue/run identity, artifact path, cadence и storage locator не входят в market observation identity.

## Что именно сохраняется

G1 не вводит второй order-book representation. Value substrate остается:

```text
liquidity-s1-normalized-book/1.0.0
```

Он уже фиксирует provider/instrument/book kind, observation identity/hash, timestamp, best bid/ask, ordered bid/ask levels и фактически достигнутую coverage по обеим сторонам. Native quantity semantics остаются `NATIVE_FIRST`; непроверенная conversion не превращается в известное значение.

Durable wrapper добавляет только history-owned bindings: actual level counts, history-target assessment и compact provenance.

## 500 bps — assessment, а не identity

```text
history_target_bps=500
identity_role=NON_IDENTITY_ASSESSMENT_METADATA
```

500 bps нужен как единая целевая оценка будущего hourly history. Он не переписывает физическую историю acquisition. Observation, полученный fresh-current запросом для меньшего target, остается тем же market observation.

## Partial / truncated observation

Coherent book не становится «несуществующим», если provider limit/full snapshot не достиг 500 bps.

```text
PERSIST_COHERENT_PARTIAL_OBSERVATION=YES
TARGET_MISS_DOES_NOT_INVALIDATE_OBSERVED_MARKET_FACT=YES
REQUEST_SATISFACTION_REMAINS_SEPARATE=YES
extrapolation_allowed=false
```

Сохраняется фактически достигнутая bid/ask coverage. Нельзя экстраполировать глубину за внешний наблюденный уровень. S1 consumer verdict может оставаться FAIL/PARTIAL.

## Identity, dedupe и immutable conflict

Semantic observation identity:

```text
provider_id
+ instrument_id
+ book_kind
+ observation_id
```

Content binding:

```text
observation_sha256
```

Правила:

```text
same identity + same observation_sha256
→ IDEMPOTENT_DUPLICATE

same identity + different observation_sha256
→ FAIL_CLOSED_IMMUTABLE_OBSERVATION_CONFLICT
```

Для этого достаточно существующего `src/history_store.py`; отдельный dedupe ledger не нужен.

## Compact provenance — option B

Мы не сохраняем полный transient S3 execution receipt forever только потому, что он существует.

Durable observation должен иметь минимальную стабильную trust chain:
- `provider_plan_sha256`;
- `provider_capability_sha256`;
- `s3_execution_policy_sha256`;
- `s3_execution_receipt_sha256`;
- endpoint/route/action binding digests;
- proof одного observation и одного physical request/session;
- provider-specific integrity/coherence evidence, нужное для выбранного route.

Это позволяет проверить origin/coherence, но не делает request-relative transport fields частью рыночного факта.

## Legacy fixed-100 history

Существующие `liquidity` schema 1.0.0 bytes не переписываются.

```text
LEGACY_SNAPSHOT_BYTES_MUTATED=NO
LEGACY_100_LEVEL_HISTORY_VALID=YES
LEGACY_100_LEVEL_HISTORY_IS_NOT_RELABELED_AS_500_BPS_COMPLETE=YES
SYNTHETIC_DEEP_BACKFILL=NO
```

Legacy book можно проецировать только в пределах сохраненных levels. Если coverage/provenance/depth metadata не доказаны stored bytes, они остаются UNKNOWN. G2-A позже заменит два duplicate Binance Spot fixed-100 network calls одновременно с включением canonical S3 hourly baseline, но исторические файлы останутся валидными.

## Время и no-lookahead

Четыре понятия намеренно различаются:

- `observation_time` — момент market observation;
- `known_at` — когда система получила знание;
- `retrieved_at` — transport/retrieval provenance;
- `durable_publication_time` — когда durable publication завершена.

```text
observation_time != known_at
request_time != observation_time
durable_publication_time != observation_time
known_at > cutoff => EXCLUDED
```

Cutoff semantics уже принадлежат существующему history resolver/reader. G1 не создает второй temporal authority.

## Cadence и storage independence

Hourly GitHub и будущий approximately-5-minute AIFE Server profile используют одну semantic observation identity.

```text
CADENCE_IS_NOT_SEMANTIC_IDENTITY=YES
STORAGE_BACKEND_IS_NOT_SEMANTIC_IDENTITY=YES
```

Git path, Release asset, server file/object locator или database locator — physical concerns. Они не входят в observation identity.

Storage estimates в program map — только conservative representative planning estimates, а не измеренный successor payload. До G2-A writer activation обязателен фактический byte benchmark.

## Что G1 НЕ реализует

G1 не:
- меняет `src/collector.py` или legacy `limit=100`;
- запускает hourly 500-bps acquisition;
- меняет fresh-current handoff/promotion ordering;
- меняет S1/S2/S3 runtime;
- меняет `tools/resolution_v2.py` или `tools/history_access_v2.py`;
- активирует D8/D9/VPS/AIFE Server;
- включает Binance USD-M GitHub network;
- создает storage/database/compression subsystem;
- запускает G2-A/G2-B, profile/features/backtest implementation.

Текущая и следующая стадия всегда определяются canonical `docs/semantics/deep-liquidity-program-map-v1.md`.
