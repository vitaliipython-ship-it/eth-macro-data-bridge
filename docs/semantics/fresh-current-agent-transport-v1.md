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
PROMOTION_HANDOFF_IS_MARKET_DATA_AUTHORITY=NO
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
→ durability classification
→ immediate downstream analysis allowed
→ optional bounded promotion handoff for eligible fresh observations
```

Если task не требует current data, используется обычный semantic history/current route. Если current data нужны, agent сначала определяет canonical `series_id`/domains и freshness threshold, а не physical storage.

Нельзя:

- обращаться к provider API напрямую из Research/аналитического domain;
- угадывать `series_id`;
- задавать Release/asset/path/SHA/VPS/database locator;
- ослаблять freshness threshold для принятия stale state как current;
- создавать domain-specific refresh workflow;
- считать Actions/Issue/artifact/promotion handoff новой market-data authority.

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


### Canonical invocation / pre-mutation preflight

`request_type` — обязательный wire-level discriminator, а не необязательная подсказка агенту:

```text
REQUEST_SCHEMA=fresh-current-agent-request/1.0.0
REQUEST_TYPE_REQUIRED=YES
REQUEST_TYPE_CONST=FRESH_CURRENT
MISSING_REQUEST_TYPE=INVALID_REQUEST_TYPE
```

Canonical invocation state machine:

```text
semantic intent
→ canonical request builder/template
→ local parse/normalize preflight when checkout is available
→ exact validated JSON bytes
→ create owner-only [current-data] Issue
→ remote Issue read-back
→ GitHub workflow independently parses the same body again
```

Repository-owned builder для обычной wire-формы:

```bash
python tools/current_data_transport.py build-request \
  --series spot.binance-spot.ETHUSDT.ohlcv.5m \
  --domain SPOT \
  --domain DERIVATIVES \
  --max-generation-age-seconds 600 \
  --current-policy FINALIZED_ONLY \
  --output request.json

python tools/current_data_transport.py parse-request \
  --request-file request.json \
  --output normalized-request.json
```

Parser остаётся fail-closed и НЕ подставляет `FRESH_CURRENT` за отсутствующий `request_type`. В connector-only среде canonical template берётся из `bridge-contract.json.semantic_resolution.current_data.request.canonical_template`; агент меняет semantic lists/threshold, но не удаляет required protocol fields.

Mutation acknowledgement не является remote authority. Если `create_issue` вернул error/unknown, это означает `MUTATION_OUTCOME_UNKNOWN`, а не доказанное отсутствие side effect:

```text
create_issue error/unknown
→ read back expected [current-data] issue identity
→ issue exists: REMOTE_COMMIT_SUCCEEDED_LOCAL_ACK_UNKNOWN; continue from remote truth
→ issue absent: retry may be attempted idempotently
```

Повторное создание Issue до read-back запрещено.

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

Provider policies collector-а сохраняются. Binance USD-M не активируется этой задачей.

## Cron и on-demand — разные durability roles

Existing hourly workflow сохраняет schedule:

```text
CRON_SCHEDULE=35 * * * *
CRON_ROLE=PERIODIC_DURABLE_PUBLICATION
CRON_GIT_PUBLICATION=YES
MAX_GENERATED_DATA_COMMITS_PER_UPDATE_RUN=1
```

Fresh transport:

```text
ON_DEMAND_ROLE=INTERACTIVE_FRESHNESS_AVAILABILITY
ON_DEMAND_GIT_PUBLICATION=NO
PER_REQUEST_GIT_COMMIT=NO
PER_REQUEST_GIT_PUSH=NO
THEY_ARE_COMPLEMENTARY=YES
```

Scheduled и on-demand provider acquisition используют одну repository-wide concurrency:

```text
concurrency.group=market-bridge-update
cancel-in-progress=false
CRON_AND_ON_DEMAND_PARALLEL_PROVIDER_ACQUISITION=NO
CRON_AND_ON_DEMAND_SERIALIZED=YES
```

Running/queued on-demand execution никогда не блокируется synchronous wait из hourly publisher. Hourly harvest рассматривает только уже completed/successful artifacts. Если request завершился позже начала текущего hourly run, handoff остаётся доступным следующему run.

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

`GENERATION_ID` = SHA256 canonical sorted serialization over contract identity, control-plane HEAD, collector version, generation time, requested semantic capability identities, validated resource SHA256 identities и semantic receipt identities.

Generation identity **не** включает GitHub run id, Issue number, artifact URL, runner filesystem path или hostname. Эти значения принадлежат только transport receipt.

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

## Durability classification

Machine durability SSOT для request-time generation — `promotion-handoff.json` по schema:

```text
fresh-current-promotion-handoff/1.0.0
```

Каждый relevant resource получает ровно один класс:

```text
RECONSTRUCTIBLE
PROMOTION_ELIGIBLE
EPHEMERAL_ONLY
NOT_APPLICABLE
```

Unknown class forbidden/fail-closed.

State semantics:

```text
RECONSTRUCTIBLE
= observation может быть canonically recovered через declared provider-history mechanism;
  promotion payload не создаётся.

PROMOTION_PENDING
= fresh acquisition создала point-in-time observation в существующей approved sampled family;
  current analysis allowed immediately, hourly durable promotion pending.

CANONICAL_DURABLE
= persisted reuse / existing durable authority уже содержит exact evidence.

EPHEMERAL_ONLY
= current-use evidence допустим, но approved durable observation contract отсутствует;
  automatic promotion forbidden.

NOT_APPLICABLE
= wrapper/non-observation; durability promotion не применяется.
```

Current approved `PROMOTION_ELIGIBLE` families ровно три:

```text
derivatives.deribit-perpetual.current-snapshot
options.deribit-options.ETH.surface-snapshots
liquidity.orderbook-snapshots
```

Они уже имеют repository-owned sampled/forward-only durable representations. Новая database/archive/history family не создаётся.

RECONSTRUCTIBLE включает closed canonical OHLCV, Kraken Futures declared provider-history metrics, Deribit DVOL и другие exact declared history-backed series. `RECONSTRUCTIBLE_OHLCV_IN_PROMOTION_PAYLOAD=NO`.

`ANALYTICS` current domain и `EVENTS` без approved exact durable observation contract — `EPHEMERAL_ONLY`. Manifest wrapper сам по себе не превращается в durable observation.

## Promotion handoff

Handoff является только:

```text
TEMPORARY_TRANSFER_EVIDENCE
```

Он не является market-data authority, WARM tier, history SSOT, archive или database.

Minimum binding включает contract/schema, `control_plane_head/tree`, `generation_id`, generation-manifest SHA, `generated_at_utc`, `known_at_utc`, `request_sha256` и resources. Для каждого eligible candidate сохраняются semantic identity, source/provider semantics, payload SHA/size, exact existing target family, policy id и validation status.

Observation identity не может использовать artifact name, run id, issue id, filename, filesystem path или URL. Deduplication опирается на существующую semantic observation identity target family.

Для `FRESH_ACQUISITION` bounded payload включает только promotion-eligible fragments. Reconstructible OHLCV windows в payload не копируются. Для `PERSISTED_REUSE` pending promotion не создаётся: evidence уже canonical durable.

Если handoff не содержит pending resources:

```text
PROMOTION_PENDING_COUNT=0
NO_PROMOTION_CONSUMPTION_ENTRY=YES
```

## Artifact и Issue receipt

Один ephemeral artifact retention `7 days` содержит requested current-generation evidence и, когда classification построена:

```text
current-generation.json
transport-receipt.json
resource-index.json
validation-summary.json
promotion-handoff.json
promotion-payload/*     # только bounded eligible fresh fragments
series/<semantic-id>/...
domains/<requested-domain>.json
```

Не загружаются `.git`, whole repository, credentials, secrets или unrequested deep archives.

PASS Issue receipt дополнительно публикует:

```text
DURABILITY_CLASSIFICATION=PASS
PROMOTION_PENDING_COUNT=N
PROMOTION_HANDOFF=PRESENT
CURRENT_ANALYSIS_ALLOWED=YES
CANONICAL_DURABILITY=PENDING_HOURLY_PROMOTION   # только если N > 0
```

До successful hourly durable publication `CANONICAL_DURABILITY=PASS` запрещён.

## Hourly durable promotion state machine

Existing `.github/workflows/update-market.yml` выполняет normal scheduled collector ровно один раз, затем harvest-ит completed/successful production `[current-data]` artifacts и применяет только exact approved target families.

Normative lifecycle:

```text
checkout main with ancestry
→ capture publisher start HEAD/tree
→ normal src/collector.py exactly once
→ harvest completed successful production handoffs
→ validate handoff schema/provenance/hash/identity/policy
→ apply pending eligible observations into EXISTING families
→ append existing collection-run evidence
→ stage promotion consumption state
→ existing full validation
→ CAS origin/main guard
→ ONE generated-data commit max
→ push
→ fetch origin/main
→ exact pushed-head read-back
→ consumption becomes effective
```

Processing order не определяет semantic winner. Existing timestamp/observation identity определяет target. Older promotion добавляет свою старую observation path и не может overwrite newer scheduled snapshot. Same exact identity + same bytes = dedup/no second copy. Same immutable identity + materially different bytes = `IMMUTABLE_OBSERVATION_CONFLICT`; last-writer-wins запрещён.

Promotion использует существующий `market-data-collection-run-ledger/1.0.0` и shared `append_partition`; parallel collection history не создаётся.

`history/current-promotion-consumption.json` имеет роль только:

```text
PROMOTION_CONSUMPTION_STATE_ONLY
```

Он хранит handoff/generation result/observation identities/target families/processing timestamp и **не является market-data observation authority**.

Consumption entry может быть staged в disposable checkout, но становится effective только после:

```text
full validation PASS
→ same generated-data commit
→ successful push
→ origin/main == PUSHED_HEAD
```

```text
ACK_BEFORE_DURABLE_PUSH=FORBIDDEN
SECOND_LEDGER_COMMIT_AFTER_PUSH=FORBIDDEN
ONE_ATOMIC_DURABLE_PUBLICATION=YES
```

Если workflow падает до push/read-back, local state исчезает, artifact остаётся доступен >=7 days, а следующий hourly run применяет тот же handoff снова. Это `PENDING_RETRY`, а не ACK.

Malformed/forged eligible handoff fail-closed; он не считается silently consumed. Harvest не ждёт running/queued request и не harvest-ит candidate-real-acceptance artifacts.

## Existing manifest/index consistency

Promotion не переписывает current domain manifest на старую observation и не делает processing order semantic winner. Approved sampled target families уже discoverable через existing capability/sample semantics и collection-run ledger; snapshot filenames являются physical target implementation, а handoff identity остаётся semantic. Existing validators после apply доказывают, что normal data-plane/history/capability contracts остались consistent.

## Current analysis versus durable research

```text
CURRENT_ANALYSIS_BEFORE_PROMOTION=ALLOWED
CURRENT_ANALYSIS_DOES_NOT_WAIT_FOR_PROMOTION=YES
EVIDENCE_DURABILITY_BEFORE_PROMOTION=EPHEMERAL_VALIDATED
EVIDENCE_DURABILITY_AFTER_SUCCESSFUL_PROMOTION=CANONICAL_DURABLE
```

Durable Research publication может требовать `CANONICAL_DURABLE` evidence по собственному Research policy. Этот contract не изобретает разрешение публиковать Research object из ephemeral evidence.

## Pre-merge qualification boundary

Candidate marker `CURRENT_DATA_REAL_ACCEPTANCE=RUN` проверяет actual provider acquisition через существующий collector, three canonical spot M5 series и requested current domains, строит actual handoff и rehearses durable apply в disposable candidate-aligned copies.

`candidate-real-acceptance` является qualification-only: workflow checkout-ит exact pushed candidate SHA (`github.sha`), не выполняет remote market-data Git publication и не устанавливает canonical durable production promotion. Production durability доказывается только отдельным post-merge gate ниже.

Pre-merge rehearsal обязана доказать promotion >=1 actual eligible resource (если providers позволяют), idempotent replay, exact duplicate dedup, immutable conflict rejection, failed-publication retry и at-most-one generated-data commit candidate. Production main pre-merge не мутируется.

Actual default-branch Issue → hourly durable Git publication проверяется только после owner integration отдельным gate:

```text
POST_MERGE_FRESH_CURRENT_TRANSPORT_LIVE_ACCEPTANCE
```

## Liquidity S1 request-scoped boundary

S1 adds semantic liquidity coverage architecture without replacing Fresh Current transport. Accepted successor semantics remain:

```text
GENERATION_INTEGRITY != METRIC_QUALIFICATION != REQUEST_SATISFACTION
GLOBAL_STRUCTURAL
REQUESTED_RESOURCE
REQUESTED_DOMAIN
UNREQUESTED_RESOURCE
UNRELATED_DEGRADED_RESOURCE_DOES_NOT_POISON_SATISFIED_REQUEST=YES
BROAD_REQUIRED_DOMAIN_DOES_NOT_AUTOMATICALLY_REQUIRE_EVERY_KNOWN_METRIC=YES
```

Canonical `request_type=FRESH_CURRENT`, repository-owned builder/preflight and remote mutation read-back remain unchanged. PR #283 fail-closed value semantics (`SOURCE_CONFLICT`, `NOT_QUALIFIED`, unobserved != zero, proven `VALID_ZERO`) remain intact. S1 owner is `contracts/liquidity-s1-semantic-contract-v1.json`, `runtime_active=false`; S1 does not activate request-aware network depth acquisition.

## AIFE Server future compatibility

Сегодня execution transport:

```text
GITHUB_ACTIONS_ISSUE_V1
```

Future target:

```text
AIFE_SERVER_D8_CURRENT_V1
```

Stable consumer semantics остаются: semantic capability requirements, freshness requirement, generation identity, semantic receipts, resource logical identities, durability classes и promotion handoff semantics. Consumer не зависит от Issue number, workflow filename, Git commit-per-generation или Actions artifact encoding.

```text
FUTURE_TRANSPORT_SWAP_REQUIRES_DOMAIN_REWRITE=NO
```

## Non-goals

Fresh/current transport v1 не:

- меняет hourly cron frequency;
- активирует AIFE Server/D8/D9;
- активирует Binance USD-M;
- создаёт second market-data API/collector/resolver/reader;
- создаёт новую database/archive/history family;
- создаёт PostgreSQL;
- выполняет production cutover;
- публикует Research objects;
- выполняет Wave/indicator/model/probability logic;
- превращает каждую M5 generation в Git commit;
- создаёт per-handoff/per-resource Git commit.

## 1.1 additive exact-liquidity transition — DB-F/S3

`fresh-current-agent-request/1.1.0` adds optional `required_liquidity[]` while
1.0 request wrappers remain version-specifically readable. Single-write output
is 1.1. Outer `max_generation_age_seconds` remains ordinary series/domain
freshness only; each exact liquidity requirement uses canonical S1
`freshness.max_age_seconds`.

Exact resources are request-scoped `EPHEMERAL_ONLY`; execution-local receipt
identity is excluded from semantic `generation_id` but is transitively bound by
`generation_manifest_sha256 → resource_index_sha256 → liquidity_resources[]`.
Cross-run Actions artifact rehydration as an exact-resource cache is forbidden.
