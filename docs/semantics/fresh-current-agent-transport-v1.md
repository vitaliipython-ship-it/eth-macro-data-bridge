# Fresh/current agent transport v1

## Назначение

Этот документ фиксирует implementation-facing semantics общего request-time freshness transport внутри существующей `MARKET_DATA_FOUNDATION` authority.

```text
CONTRACT_ID=ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1
CONTRACT_VERSION=1.0.0
ISSUE_PREFIX=[current-data]
ROLE=INTERIM_PRE_AIFE_SERVER_EXECUTION_TRANSPORT
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
EXECUTION_PLANE_IS_MARKET_DATA_AUTHORITY=NO
GITHUB_ACTIONS_IS_MARKET_DATA_AUTHORITY=NO
ACTIONS_ARTIFACT_IS_MARKET_DATA_AUTHORITY=NO
GITHUB_ISSUE_IS_MARKET_DATA_AUTHORITY=NO
```

Механизм общий для Technical Indicators, Wave Analysis, Price Structures, Relative Strength, derivatives/OI/funding/CVD, options/IV/DVOL, liquidity, analytics, events и будущих consumers. Он не содержит domain formulas, scoring, Wave logic или provider-specific secondary acquisition.

## Нормативный decision route

```text
REQUEST_REQUIRES_MARKET_DATA
→ determine semantic requirements
→ REQUEST_REQUIRES_CURRENT_DATA?
→ evaluate persisted freshness
→ persisted fresh: existing semantic read route
→ persisted stale/missing: FRESH_CURRENT_AGENT_TRANSPORT
→ validated current generation
→ semantic outputs / receipts
→ downstream analysis
```

Если task не требует current data, используется обычный semantic history/current route. Если current data нужны, agent сначала определяет canonical `series_id`/domains и freshness threshold, а не physical storage.

Нельзя:

- обращаться к provider API напрямую из Research/аналитического domain;
- угадывать `series_id`;
- задавать Release/asset/path/SHA/VPS/database locator;
- ослаблять freshness threshold для принятия stale state как current;
- создавать domain-specific refresh workflow;
- считать Actions/Issue/artifact новой market-data authority.

## Semantic request

Owner-only Issue request имеет title prefix `[current-data]`, а body — только JSON object.

Минимальная форма:

```json
{
  "request_type": "FRESH_CURRENT",
  "required_series": [],
  "required_domains": [],
  "max_generation_age_seconds": 600,
  "current_policy": "FINALIZED_ONLY"
}
```

`required_series` принимает canonical `series_id` string или bounded object:

```json
{
  "series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m",
  "latest_bars": 256
}
```

`latest_bars` bounded: `1..4096` в v1. Plain string shorthand означает default `256`.

Allowed domains:

```text
SPOT
DERIVATIVES
OPTIONS
LIQUIDITY
ANALYTICS
EVENTS
```

Хотя бы один series/domain обязателен. Every requested `series_id` проверяется через `tools/capability_index.py`; unknown/ambiguous series fail closed.

Forbidden semantic request fields include:

```text
provider_url
release_tag
asset_name
asset_id
resource_path
filesystem_path
manifest_path
sha256
vps_path
database_locator
browser_download_url
raw_url
```

## Freshness router

Transport checkout captures exact request-time `main`:

```text
CONTROL_PLANE_HEAD
CONTROL_PLANE_TREE
```

Freshness оценивается по persisted canonical generation timestamps/status, а не по возрасту Git commit. Consumer-supplied `max_generation_age_seconds` является request requirement.

```text
PERSISTED_FRESH_ENOUGH=REUSE_ALLOWED
STALE_PERSISTED_STATE=FRESH_ACQUISITION_REQUIRED
```

При reuse provider acquisition не запускается. При stale/missing state workflow вызывает ровно существующий producer:

```text
CURRENT_ACQUISITION=src/collector.py
SECOND_COLLECTOR=NO
```

Provider policies collector-а сохраняются. В частности, Binance USD-M не активируется этой задачей.

## Cron и on-demand — разные durability roles

Existing hourly workflow сохраняет schedule:

```text
CRON_SCHEDULE=35 * * * *
CRON_ROLE=PERIODIC_DURABLE_PUBLICATION
CRON_GIT_PUBLICATION=YES
```

Fresh transport:

```text
ON_DEMAND_ROLE=INTERACTIVE_FRESHNESS_AVAILABILITY
ON_DEMAND_GIT_PUBLICATION=NO
THEY_ARE_COMPLEMENTARY=YES
```

Hourly cron остаётся важен, потому что регулярно сохраняет samples, которые для options/liquidity/order-book/current intelligence могут быть не полностью reconstructible позже. On-demand transport не заменяет эту durability function.

Scheduled и on-demand provider acquisition используют одну repository-wide concurrency:

```text
concurrency.group=market-bridge-update
cancel-in-progress=false
CRON_AND_ON_DEMAND_PARALLEL_PROVIDER_ACQUISITION=NO
CRON_AND_ON_DEMAND_SERIALIZED=YES
```

Если два запуска приходят одновременно, один ждёт; ни один не отменяет другой.

## On-demand mutation boundary

Workflow permissions:

```text
contents: read
issues: write
```

Generated state меняет только disposable Actions checkout.

```text
REMOTE_REPOSITORY_MUTATION=NO
GIT_ADD=NO
GIT_COMMIT=NO
GIT_PUSH=NO
RELEASE_PUBLICATION=NO
D8_STATE_MUTATION=NO
D9_ACTIVATION=NO
SEALING=NO
COLD_PUBLICATION=NO
```

Перед receipt:

```text
git rev-parse HEAD == CONTROL_PLANE_HEAD
```

Dirty generated files внутри disposable checkout ожидаемы и не являются repository publication.

## Validation before exposure

После fresh acquisition выполняется approved validation contour до любого output exposure:

```text
python tools/validation/validate.py
python tools/validation/validate_v4.py
python tools/validation/validate_history.py
python tools/validation/consumer_proof.py
python tools/validation/validate_repository.py
python tools/validation/validate_d9_contracts.py
python tools/capability_index.py validate
```

Pre-merge real acceptance также включает compileall, D9 resolution v2 non-regression и deep-history tests.

Required capability с explicit `DEGRADED`/`FAIL`/unavailable state не заменяется silent substitute. Request fail closed с deterministic public category.

## Latest finalized series

`tools/history_consumer.py latest` — additive operation внутри **существующего** consumer family. Она не является вторым resolver/reader.

```text
tools/capability_index.py describe/resolve
→ declared WARM manifest
→ actual canonical finalized last_timestamp
→ canonical interval semantics
→ bounded exact range
→ existing resolve_capability
→ ResolutionPlan v1
→ tools/history_access.py
→ strict normalized output
→ canonical semantic receipt
```

Actual returned/declared canonical finalized observation anchors range. Local guessed time grid не является semantic authority. `FINALIZED_ONLY` обязателен; forward/open bar не допускается.

## Generation identity

Git commit — control-plane identity, но не единственная market-data generation identity.

Generation manifest separates:

```text
CONTROL_PLANE_HEAD
CONTROL_PLANE_TREE
GENERATION_ID
GENERATED_AT_UTC
KNOWN_AT_UTC
REQUEST_SHA256
GENERATION_MANIFEST_SHA256
SEMANTIC_RECEIPTS
EXECUTION_TRANSPORT=GITHUB_ACTIONS_ISSUE_V1
```

`GENERATION_ID` = SHA256 canonical sorted serialization over:

- contract id/version;
- control-plane HEAD;
- collector version;
- `generated_at_utc`;
- requested semantic capability identities;
- canonical SHA256 identities of validated domain/series resources;
- semantic receipt identities.

Generation identity **не** включает:

```text
GitHub run id
issue number
artifact URL
runner filesystem path
hostname
```

Эти значения принадлежат только transport receipt.

## Generation resource index

Agent обнаруживает ephemeral generation resources через `resource-index.json`, а не через repository paths.

Domain entry minimum:

```text
domain_id
resource_logical_id
status
generated_at_utc
sha256
size_bytes
availability
freshness
```

Series entry дополнительно связывает `series_id`, `latest_bars`, ResolutionPlan/semantic receipt identity, finality и strict diagnostics.

```text
EPHEMERAL_RESOURCE_DISCOVERY=GENERATION_RESOURCE_INDEX
FOLLOW_LEGACY_RAW_URL_FOR_EPHEMERAL_DATA=FORBIDDEN
```

Legacy `raw_url` внутри source payload может сохраняться как payload field, но никогда не становится authoritative ephemeral locator.

## Artifact и Issue receipt

Один ephemeral artifact retention `7 days` содержит только requested current-generation evidence:

```text
current-generation.json
transport-receipt.json
resource-index.json
validation-summary.json
series/<semantic-id>/normalized.json
series/<semantic-id>/resolution-plan.json
series/<semantic-id>/diagnostics.json
series/<semantic-id>/receipt.json
series/<semantic-id>/semantic-receipt.json
domains/<requested-domain>.json
```

Не загружаются `.git`, whole repository, credentials, secrets или unrequested deep archives.

PASS Issue receipt публикует:

```text
CURRENT_DATA_AGENT_REQUEST=PASS
REQUEST_SHA256
CONTROL_PLANE_HEAD
GENERATION_MODE=PERSISTED_REUSE|FRESH_ACQUISITION
GENERATION_ID
GENERATED_AT_UTC
KNOWN_AT_UTC
REQUIRED_SERIES_COUNT
REQUIRED_DOMAINS
VALIDATION=PASS
ARTIFACT_URL
RUN_ID
RUN_URL
```

FAIL receipt публикует step/failure category; Issue затем закрывается. Issue receipt — transport evidence, не semantic market-data authority.

## Durability classes

### A. RECONSTRUCTIBLE_SERIES

Closed OHLCV и иные provider-history-backed series могут использовать ephemeral current tail, потому что canonical durable history может впоследствии накопить те же observations.

### B. NON_RECONSTRUCTIBLE_OR_SAMPLE_DEPENDENT_CURRENT

Options/liquidity/order-book/current intelligence и иные sampled facts могут зависеть от point-in-time collection semantics. On-demand generation пригодна для current analysis, но сама по себе не получает automatic Research durability.

```text
ON_DEMAND_CURRENT_DATA_CAN_BE_USED_FOR_LIVE_ANALYSIS=YES
ON_DEMAND_EPHEMERAL_DATA_AUTOMATICALLY_DURABLE_RESEARCH_EVIDENCE=NO
AUTOMATIC_RESEARCH_PUBLICATION_FROM_EPHEMERAL_ONLY_EVIDENCE=FORBIDDEN
```

Durability promotion не является частью v1.

## AIFE Server future compatibility

Сегодня execution transport:

```text
GITHUB_ACTIONS_ISSUE_V1
```

Future target:

```text
AIFE_SERVER_D8_CURRENT_V1
```

Stable consumer semantics остаются:

- semantic capability requirements;
- freshness requirement;
- generation identity;
- semantic receipts;
- resource logical identities.

Consumer не должен зависеть от Issue number, workflow filename, Git commit-per-generation или Actions artifact encoding.

```text
FUTURE_TRANSPORT_SWAP_REQUIRES_DOMAIN_REWRITE=NO
```

## Non-goals

Fresh/current transport v1 не:

- меняет hourly cron frequency;
- активирует AIFE Server/D8/D9;
- активирует Binance USD-M;
- создаёт second market-data API/collector/resolver/reader;
- создаёт PostgreSQL;
- выполняет production cutover;
- публикует Research objects;
- выполняет Wave/indicator/model/probability logic;
- превращает каждую M5 generation в Git commit.
