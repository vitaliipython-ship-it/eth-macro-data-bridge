# Free multi-instrument integration substrate v1

## Статус

```text
CONTRACT_ID=ETH-MARKET-DATA-FREE-MULTI-INSTRUMENT-INTEGRATION-SUBSTRATE-V1
STATUS=NON_PRODUCTION_INTEGRATION_SUBSTRATE
USE_CASE=PRIVATE_INTERNAL_AIFE_RESEARCH
FREE_DATA_ONLY=YES
PRODUCTION_PROVIDER_ACTIVATION=NO
I7_EXECUTION=NO
```

Machine configuration authority этой реализации:

`contracts/free-multi-instrument-integration-substrate-v1.json`.

Это отдельный generic server-substrate contour. Он не является продолжением I7 P1 и не превращает GOLD/WTI test samples в Wave evidence.

## Зачем нужен этот контур

Существующий consumer-facing route сохраняется:

```text
CAPABILITY_INDEX
→ CANONICAL_RESOLVER
→ RESOLUTION_PLAN
→ CANONICAL_READER
```

Новый код решает только bounded integration seam перед этим route:

```text
provider-specific acquisition
→ non-production staging
→ generic validation
→ generic normalization
→ provenance receipt
→ non-production ResolutionPlan compatibility proof
→ existing reader
```

Ни второй resolver, ни второй reader, ни второй market-data authority не создаются.

## Главная граница

```text
RAW_OR_STAGING != CANONICAL_HISTORY
INTEGRATION_SAMPLE_QUALIFICATION != PROVIDER_CANONICAL_QUALIFICATION
READER_COMPATIBILITY_PASS != CAPABILITY_ADVERTISEMENT_AUTHORIZATION
```

Новый external-provider sample имеет класс:

`NON_PRODUCTION_INTEGRATION_SAMPLE`.

Он не регистрируется в production `history/capability-index.json`.

## Provider / instrument separation

Generic configuration обязана разделять:

- `provider_id`;
- `provider_instrument_id`;
- `economic_subject_id`;
- `market_type`;
- `price_semantics`;
- granularity;
- timezone/time semantics;
- session semantics;
- acquisition method;
- provenance.

Hard invariant:

```text
ECONOMIC_SUBJECT != PROVIDER_SYMBOL
```

Один provider adapter может обслуживать несколько instruments через configuration. Отдельный pipeline на каждый symbol не создаётся.

## Поддерживаемые construction classes

Минимальный generic carrier допускает:

```text
SPOT
CFD
REFERENCE_SERIES
FUTURES_SINGLE
FUTURES_CONTINUOUS
INDEX
OTHER
```

Наличие `FUTURES_CONTINUOUS` в carrier не означает наличие WTI roll engine.

```text
SYNTHETIC_WTI_ROLL_RECONSTRUCTION=NO
I7_WTI_CONTINUOUS_CONSTRUCTION_IMPLEMENTED=NO
```

Для будущего расширения могут передаваться conditional fields:

`contract_id`, `expiry`, `roll_event`, `adjustment_event`, `construction_generation_id`.

## Raw/staging

Runtime root приходит извне:

```text
AIFE_MULTI_INSTRUMENT_CONFIG
AIFE_MULTI_INSTRUMENT_STAGING_ROOT
```

Никаких owner-machine, WSL или Docker Desktop paths в domain logic нет.

Generation path определяется детерминированно из:

- provider/instrument/subject;
- requested window;
- normalized configuration fingerprint;
- raw fingerprint.

Одинаковый input + config повторно попадает в ту же generation identity.

Если upstream bytes меняются, меняется `generation_id`; старое поколение не переписывается.

## Vendor bytes

Third-party vendor payload разрешён только во внутреннем runtime staging/cache.

```text
THIRD_PARTY_VENDOR_RAW_BYTES_COMMITTED_TO_GIT=NO
DATA_REDISTRIBUTION_VIA_REPOSITORY=NO
```

В Git находятся только code/config/docs/tests и synthetic test rows.

Live qualification не upload-ит raw response как artifact.

## Provenance receipt

Каждый successful bounded acquisition создаёт receipt:

```text
provider_id
provider_instrument
economic_subject
market_type
retrieval_method
retrieved_at_utc
requested_window
actual_window
granularity
price_semantics
source_timezone
record_count
raw_fingerprint
normalized_fingerprint
configuration_fingerprint
acquisition_identity
generation_id
quality
sample_class
```

Receipt не содержит provider raw payload.

## Session model

Carrier различает:

```text
24X7
DECLARED_SESSION
DAILY_BREAK
WEEKEND_CLOSE
HOLIDAY_OR_SPECIAL_CLOSE
UNKNOWN_SESSION
```

`weekday` не является универсальной calendar authority.

Gap carrier позволяет позже различать:

```text
REAL_PRICE_MOVE
SESSION_REOPEN_GAP
MARKET_CLOSED_INTERVAL
MISSING_DATA
PROVIDER_OUTAGE
ROLL_GAP
ADJUSTMENT_ARTIFACT
UNKNOWN_GAP
```

Текущая реализация не заявляет полный session/gap inference engine. Если gap не квалифицирован, он остаётся `UNKNOWN_GAP`.

## Time normalization

Provider config обязан объявить `source_timezone` и `source_time_kind`.

Поддерживаются:

- `ISO8601`;
- `EPOCH_MS`;
- `DATE_PERIOD`.

`DATE_PERIOD` нормализуется в start-of-period в явно заданной timezone. Это period anchor, а не утверждение о точном времени публикации provider-а.

Unknown timezone/time semantics не допускаются как positive normalization proof.

## Data quality

Generic normalization fail-closed проверяет:

- пустой sample;
- duplicate timestamps;
- non-finite values;
- OHLC bounds;
- negative volume;
- out-of-window records.

Дополнительно receipt фиксирует:

- input out-of-order count;
- raw/normalized gap count;
- max gap;
- current generic gap class.

Synthetic fill отсутствует.

## Aggregation

`aggregate_ohlcv` агрегирует fixed-grid rows только при полном bucket membership.

Если bucket неполный:

```text
SYNTHETIC_FILL=NO
RESULT=FAIL_CLOSED
```

Этим одним primitive можно доказать M1→M5, M1→H1 и M1→H4 при явном bucket/session anchor.

## Existing reader compatibility

`build_nonproduction_resolution_plan()` создаёт только isolated non-production `ResolutionPlan v2`.

Он:

- использует существующую schema `market-data-resolution-plan/2.0.0`;
- использует `GIT_WARM_RESOURCE` только как compatibility storage label текущего reader;
- указывает temporary staging resource relative to supplied test/runtime root;
- содержит `capability_advertisement=false`;
- содержит `second_resolver=false`.

Plan передаётся существующему `tools/history_access_v2.py`.

Этот proof не меняет production capability index и не создаёт test resolver.

## Public free physical probe

Для bounded live qualification выбраны два distinct public providers, потому что они проверяют разные provider identities через один и тот же generic CSV acquisition substrate:

1. ECB Data Portal:
   - `D.USD.EUR.SP00.A`;
   - economic subject `FX:EURUSD`;
   - daily official reference series.

2. FRED:
   - `DCOILWTICO`;
   - economic subject `COMMODITY:WTI_CRUDE_OIL`;
   - daily WTI Cushing reference series, source identified by FRED as EIA Spot Prices.

FRED WTI здесь:

```text
REFERENCE_SERIES
!=
CANONICAL_I7_WTI_CONTINUOUS_CL
```

Live probe ограничен fixed historical window и пишет bytes только в runner temp.

## Dukascopy

Dukascopy остаётся configuration-level candidate:

```text
ROLE=FREE_INTERNAL_RESEARCH_INTRADAY_INTEGRATION_PROOF_PROVIDER_CANDIDATE
PREFERRED_METHOD=OFFICIAL_JFOREX_API
PRODUCTION_CANONICAL_AUTHORITY=NO
STORAGE_MODE=BOUNDED_INTERNAL_TEST_CACHE_OR_STAGING
```

Текущий Python contour не пытается обходить JForex runtime/login boundary и не использует website scraper.

Если free account/runtime credentials недоступны:

```text
DUKASCOPY_PHYSICAL_ACQUISITION=
BLOCKED_ADAPTER_OR_CREDENTIAL_RUNTIME_REQUIRED
```

Это не превращается в paid-data failure и не разрешает альтернативный unauthorized scraper.

## WTI boundary

Dukascopy `LIGHT.CMD/USD`, если будет добавлен в отдельный bounded execution proof, остаётся:

`NONCANONICAL_MULTI_INSTRUMENT_PIPELINE_TEST_SERIES`.

Он не доказывает I7 WTI.

## Server readiness

Новый instrument в уже поддерживаемом adapter class задаётся конфигурацией, а не source-code branch.

Deployment-specific storage root также задаётся environment/config.

Server-ready здесь означает готовность bounded ingestion/staging/normalization contour, а не production deployment и не public data service.

## Что квалифицируется

Targeted tests обязаны доказать:

- config-driven multi-provider model;
- multi-instrument reuse одного pipeline;
- raw/staging separation;
- deterministic fingerprints;
- idempotent reingestion;
- versioned generation при changed raw bytes;
- UTC normalization;
- invalid/duplicate fail-closed;
- deterministic aggregation without fill;
- non-production ResolutionPlan v2;
- existing canonical reader compatibility.

Repository full qualification отдельно доказывает отсутствие regressions существующего crypto/history route.

## Что не квалифицируется

```text
GOLD_CANONICAL_HISTORY=NO
WTI_CANONICAL_HISTORY=NO
DUKASCOPY_CANONICAL_PROVIDER=NO
FULL_VENDOR_ARCHIVE=NO
FULL_DUKASCOPY_ARCHIVE_RIGHT=NOT_CLAIMED
PRODUCTION_PROVIDER_ACTIVATION=NO
I7_READINESS_STARTED=NO
I7_EXECUTION_STARTED=NO
```

После owner merge допустима отдельная internal-server materialization задача с bounded providers. Bulk history и canonical provider activation остаются отдельными gates.
