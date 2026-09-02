# AGENTS.md

## Назначение

Это первая и каноническая semantic точка входа для любого агента, который читает или изменяет `eth-macro-data-bridge`. Репозиторий является authority рыночных фактов; Elliott/NEoWave, гипотезы, сценарии и интерпретация принадлежат `eth-macro-research`.

Канонический язык документации — **русский**. Machine identifiers, provider names, schema fields, paths и commands сохраняются на английском.

## Канонический market-data route

Главный принцип: **AGENT REQUESTS SEMANTICS, NOT STORAGE**.

Не начинать с provider path, Release tag, asset filename, URL или Git tree scan.

Текущий active/default route:

```text
AGENTS.md
→ bridge-contract.json
→ canonical_paths.capability_index
→ semantic capability discovery
→ tools/capability_index.py
→ ResolutionPlan v1
→ tools/history_access.py
→ canonical manifests/resources
→ verified WARM / legacy COLD
→ normalized output
→ diagnostics
→ receipt
```

`bridge-contract.json` — route/provider-policy/storage-portability machine authority. Capability index — derived discovery layer, не byte authority. `ResolutionPlan` — единственный input authority reader-а. Physical locator/size/SHA приходит только из canonical control plane после semantic resolution.

Агент задаёт `series_id`, range/observation identity, cutoff когда применимо, mode/policy и output format. Агент не задаёт Release tag, asset/path/URL/SHA locator, WARM/COLD/generation path, VPS filesystem path, database locator или provider URL.

## Liquidity S1 semantic architecture

Canonical discoverability chain для принятой S1 liquidity architecture:

```text
AGENTS.md
→ bridge-contract.json
→ semantic_contracts.liquidity_s1
→ contracts/liquidity-s1-semantic-contract-v1.json
```

`contracts/liquidity-s1-semantic-contract-v1.json` — additive machine owner S1 semantic architecture внутри существующего Market Data Foundation. Status `ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE`, `runtime_active=false`. Он не меняет active D6/ResolutionPlan v1 route, не создаёт второй collector/catalog/resolver/reader/market-data authority и не активирует S2/S3 provider/network execution.

## Fresh/current market-data requests

Для любой задачи сначала определить, действительно ли нужен **current** market state. Один и тот же mechanism используется Technical Indicators, Wave Analysis, Price Structures, Relative Strength, OI/funding/CVD, options/IV/DVOL, liquidity, analytics, events и будущими consumers.

Normative decision tree:

```text
IF task does not require current data:
    use normal semantic history/current route.

IF task requires current data:
    discover required semantic capabilities via canonical capability index.
    evaluate persisted canonical generation against consumer freshness requirement.

    IF persisted generation is fresh enough:
        reuse it through the existing semantic read route.
    ELSE:
        invoke bridge-contract.json semantic_resolution.current_data agent transport
        via owner-only GitHub Issue [current-data].

After response:
    consume only validated generation resources and semantic receipts.
```

Canonical current-data contract:

```text
CONTRACT_ID=ETH-MARKET-DATA-FRESH-CURRENT-TRANSPORT-V1
CONTRACT_VERSION=1.1.0
SEMANTICS=docs/semantics/fresh-current-agent-transport-v1.md
ISSUE_PREFIX=[current-data]
EXECUTION_TRANSPORT=GITHUB_ACTIONS_ISSUE_V1
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
```

Request body — canonical JSON object контракта `fresh-current-agent-request/1.1.0`. Поле `request_type` ОБЯЗАТЕЛЬНО и имеет единственное допустимое значение `FRESH_CURRENT`; отсутствие этого поля является `INVALID_REQUEST_TYPE` и fail-closed. Минимальная wire-форма:

```json
{
  "request_type": "FRESH_CURRENT",
  "required_series": [],
  "required_domains": [],
  "required_liquidity": [],
  "max_generation_age_seconds": 600,
  "current_policy": "FINALIZED_ONLY"
}
```

Агент не должен вручную импровизировать wire protocol. При наличии checkout request сначала строится через `python tools/current_data_transport.py build-request ...`, затем обязательно preflight-ится через `python tools/current_data_transport.py parse-request --request-file <request.json> --output <normalized.json>` и только после PASS exact validated JSON используется как body `[current-data]` Issue. В connector-only среде, где локальный preflight недоступен, использовать exact `bridge-contract.json.semantic_resolution.current_data.request.canonical_template`, меняя только semantic requirements. После любой ошибки/unknown результата `create_issue` запрещено считать remote mutation отсутствующей без read-back по ожидаемому `[current-data]` title/request identity; retry допускается только после доказанного отсутствия Issue. `series_id` должен быть найден/проверен через `tools/capability_index.py`; не синтезировать его из provider/instrument strings.

Примеры одной и той же freshness route:

```text
Wave M5 current context
→ [current-data]
→ required_series=[spot.binance-spot.ETHUSDT.ohlcv.5m]

Technical Indicators 3×6 current snapshot
→ [current-data]
→ semantic series requirements for ETHUSDT/BTCUSDT/ETHBTC
→ same validated generation + semantic receipts

OI / funding / CVD
→ [current-data]
→ required_domains=[DERIVATIVES,ANALYTICS]

options / IV / DVOL
→ [current-data]
→ required_domains=[OPTIONS,ANALYTICS]
→ canonical series_id additionally when a historical/current series is required

liquidity
→ [current-data]
→ required_domains=[LIQUIDITY]
```

Never:

- call provider directly from Research/analytical domain;
- guess storage, Release, path, URL, SHA, VPS/database locator;
- relax freshness and label stale values as current;
- follow legacy `raw_url` as ephemeral generation authority;
- create a Technical-Indicators/Wave/options-specific refresh transport.

If persisted state is stale/missing, `[current-data]` may run the **existing** `src/collector.py` inside a disposable Actions checkout, validates the generation, materializes requested semantic outputs through the existing resolver/ResolutionPlan/reader family, uploads one ephemeral artifact and closes the Issue with a compact receipt. It has `contents: read`; it does not commit/push generated data.

Hourly `.github/workflows/update-market.yml` remains the durable periodic collector/publication path. On-demand freshness and hourly durability are complementary, use the same `market-bridge-update` concurrency group, and never acquire providers concurrently through this collector.

Issue/workflow/artifact are transport/evidence only. On-demand sample-dependent current data may be used for live analysis but is **not** automatically durable Research evidence. Future replacement by `AIFE_SERVER_D8_CURRENT_V1` must preserve the same semantic request/freshness/generation/receipt contract without domain rewrites.

Fresh/current artifact additionally содержит `promotion-handoff.json`, который является `TEMPORARY_TRANSFER_EVIDENCE`, а не market-data/history authority. Для fresh acquisition machine evidence классифицирует каждый relevant resource:

```text
RECONSTRUCTIBLE
→ promotion не нужен; canonical provider-history path сохраняет/восстанавливает observation.

PROMOTION_PENDING
→ current analysis разрешён немедленно;
→ bounded handoff ждёт следующего successful hourly durable publisher.

CANONICAL_DURABLE
→ evidence уже находится в существующей canonical durable authority.

EPHEMERAL_ONLY
→ current-use evidence only; automatic durable promotion запрещён до отдельного approved storage contract.

NOT_APPLICABLE
→ wrapper/non-observation; durability promotion не применяется.
```

Hourly publisher harvest-ит только completed/successful owner `[current-data]` artifacts, validates provenance/hash/semantic observation identity, deduplicates и appends только в три уже существующие approved sample families: `derivatives.deribit-perpetual.current-snapshot`, `options.deribit-options.ETH.surface-snapshots`, `liquidity.orderbook-snapshots`. Promotion consumption state входит в тот же единственный generated-data commit и становится effective только после successful push + exact `origin/main` read-back.

```text
CURRENT_ANALYSIS_DOES_NOT_WAIT_FOR_PROMOTION=YES
PER_REQUEST_GIT_COMMIT=NO
PER_REQUEST_GIT_PUSH=NO
PROMOTION_HANDOFF_IS_MARKET_DATA_AUTHORITY=NO
CONSUMPTION_ACK_BEFORE_DURABLE_PUSH=NO
```

Agent не должен вручную persist/promote current evidence, создавать Git commit для request, вызывать provider напрямую, ждать hourly promotion перед live analysis или изобретать второй refresh/promotion mechanism.

## Storage portability boundary

Canonical contract identity:

```text
ETH-MARKET-DATA-STORAGE-PORTABILITY-V2
```

Implementation-facing semantics: `docs/semantics/market-data-storage-portability-v2.md`.

Hard invariant:

```text
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
PHYSICAL_STORAGE_BACKEND_IS_SEMANTIC_AUTHORITY=false
EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false
```

`HOT/WARM/COLD` — logical residence roles. Current physical profile `GITHUB_FIRST_V1` не является eternal semantic ontology. Backend migration не должна менять `series_id`, `observation_id`, D8 envelope, resolver/reader public family или semantic receipt meaning.

D8 SQLite WAL — `OPERATIONAL_RUNTIME_STATE`, не D9 history authority.

Current reconciled A1/A2 physical-qualification program/status snapshot authority:

- machine current status snapshot: `contracts/d8-a2-physical-qualification-status-v1.json`;
- historical predecessor snapshot: `contracts/d8-shadow-post-reset-status-v1.json`;
- historical predecessor semantics: `docs/semantics/d8-shadow-post-reset-authority-v1.md`.

Current snapshot records owner-accepted A1 fresh checkpoint-v2 and A2 canonical publication/ACK/PENDING→FORWARDED/idempotent replay evidence. It is a committed reconciliation snapshot, **not** a continuously refreshed live VPS probe. Its `CURRENT_*` values are accepted observation-point values; before any future physical mutation or qualification the executor must fresh-read server execution authority again.

The predecessor preserves the earlier post-reset `0/0/0`, `NEW_REAL_CHECKPOINT_V2_DATA=NEXT` and `PHYSICAL_PUBLICATION_PORT=PENDING` observation point as historical evidence and must not be interpreted as current program status after accepted A2 qualification.

Source/runtime behavior authority remains `contracts/d8-runtime-candidate.json`; historical exact-source handoff remains `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md` and is not current deployment-status SSOT.

## Production readiness master freeze

До любой D8/D9 production activation, provider-authority transition, legacy-acquisition disablement или production cutover обязательна implementation-facing authority:

`docs/semantics/d8-production-capability-parity-expansion-and-cutover-v1.md`.

```text
PRODUCTION_ACTIVATION_BEFORE_FULL_READINESS=FORBIDDEN
VPS_ACTIVE_BEFORE_R0_R7_PASS=FORBIDDEN
PROVIDER_AUTHORITY_TRANSITION_BEFORE_R0_R7_PASS=FORBIDDEN
LEGACY_GITHUB_ACQUISITION_DISABLE_BEFORE_R0_R7_PASS=FORBIDDEN
PRODUCTION_WARM_FORWARDER_SCHEDULING_BEFORE_R0_R7_PASS=FORBIDDEN
PARTIAL_PRODUCTION_LAUNCH=FORBIDDEN_BY_DEFAULT
D8_WARM_PRODUCTION_BLOCKED_ON_MONTHLY_COLD=NO
```

Current D9 completed-month eligibility/COLD frontier ниже остаётся authority для **D9 WARM→COLD lifecycle**, но не является prerequisite будущего D8 + continuous D9 WARM production launch после полного R0–R7 readiness. Binance USDⓈ-M GitHub `DISABLED_BY_POLICY` / `network_calls=0` означает current GitHub-runtime policy; target D8 VPS production provider remains required и может стать active только через отдельный versioned owner-authorized provider-authority cutover.

## Agent-callable historical read

Preferred local adapter текущего D6/v1 route:

```bash
python tools/history_consumer.py read \
  --series-id spot.binance-spot.ETHUSDT.ohlcv.1h \
  --from 2025-04-09T00:00:00Z \
  --to 2025-08-25T00:00:00Z \
  --mode strict \
  --format csv \
  --output candles.csv \
  --plan-output resolution-plan.json \
  --diagnostics-output diagnostics.json \
  --receipt-output receipt.json
```

`tools/history_consumer.py` не второй resolver: он вызывает canonical resolver и передаёт полученный `ResolutionPlan` canonical reader-у. Additive `latest` operation использует actual finalized tail из declared canonical WARM manifest и затем проходит через тот же resolver/ResolutionPlan/reader route; local guessed schedule не является authority.

### Hosted connector transport

Если local reader недоступен, использовать `bridge-contract.json.semantic_resolution.agent_transport`:

```text
GitHub Issue: [history-read]
→ .github/workflows/history-consumer-read.yml
→ tools/history_consumer.py
→ resolver → ResolutionPlan → reader
→ receipt + diagnostics + ephemeral artifact
```

Issue/workflow/artifact — transport/evidence, не market-data authority. В request допустимы только semantic fields; asset/release/path/URL/SHA запрещены.

Если canonical transports недоступны:

```text
DATA_TRANSPORT_BLOCKED
```

Не заменять canonical history прямым provider API. Provider API может быть только отдельной corroboration, не replacement authority.

## Hard guardrails

1. `bridge-contract.json` — текущая machine route/provider/storage-portability authority.
2. `ResolutionPlan` — reader input authority.
3. Capability catalog/index — derived projection, не второй SSOT.
4. Не угадывать и не hard-code-ить Release/storage routes.
5. Никаких synthetic gap fills и silent provider substitution.
6. Runtime/Actions/VPS transport не становится market-data authority.
7. Raw market history не копируется в Research.
8. Binance USDⓈ-M остаётся `DISABLED_BY_POLICY`, пока contract явно не изменён после отдельной provider-authority transition.
9. Historical options/order-book backfill не фабрикуется.
10. Immutable Release не переписывается in-place.
11. D9 source completeness или physical A2 qualification не означает D9 activation.
12. Human docs не переопределяют machine contracts/schemas/runtime.
13. `HOT/WARM/COLD` не означают Git/VPS/PostgreSQL/Release.
14. Local filesystem write/read-back сам по себе не даёт production D8→D9 ACK.
15. `one M5 observation → one git commit` запрещён.
16. Не создавать второй resolver/reader/catalog/API/market-data authority ради backend portability.
17. Repository reconciled physical status snapshot не является live VPS probe и не авторизует physical mutation без fresh server readback.
18. Physical qualification != activation: A1/A2 PASS не активирует D8, D9, Binance USD-M provider authority или ResolutionPlan v2.
19. Current-data Issue/workflow/artifact являются transport/evidence only; semantic authority остаётся Data Bridge.
20. Ephemeral on-demand generation не получает automatic durable Research status.
21. Promotion handoff/Actions artifact не являются durable history authority; canonical durability возникает только после existing hourly generated-data publication/read-back.
22. Не создавать consumption ACK до durable push и не создавать второй ACK commit после push.

## D6 / D9 status

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=QUALIFIED/PASS/ACTIVE
D6.5=QUALIFIED/PASS/MERGED
D6.6=NEXT/PENDING/CLOSURE_COMPATIBILITY
AGENT_RUNTIME_HISTORY_TRANSPORT=ACTIVE

D9_1=PASS
D9_2=PASS
D9_3_SOURCE=PASS
D9_4_SOURCE=PASS
D9_5_SOURCE=PASS
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
D9_REAL_D8_RUNTIME_TO_CANONICAL_WARM=PHYSICAL_QUALIFICATION_PASS
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVE=NO
D9_ACTIVATION=PENDING

D8_STATUS_SEMANTICS=RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE
D8_LIVE_RUNTIME_STATUS_CONTINUOUSLY_VERIFIED=false
D8_LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_ACTION=true
D8_AUTHORITY_ACTIVE=false
D8_VPS_SHADOW_RUNTIME=NON_AUTHORITATIVE
CURRENT_D8_STATE_SCHEMA_VERSION=2
CURRENT_D8_SPOOL_TOTAL=20
CURRENT_D8_PENDING_TOTAL=0
CURRENT_D8_FORWARDED_TOTAL=20
A1_FRESH_CHECKPOINT_V2=PASS
A2_CANONICAL_PUBLICATION=PASS
A2_CANONICAL_ACK=PASS
A2_PENDING_TO_FORWARDED=PASS
A2_IDEMPOTENT_REPLAY=PASS
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=true

ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
ACTIVE_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
D9_V2=SOURCE_CANDIDATE_NOT_ACTIVE
```

D9 v2 реализован как candidate в той же `tools/capability_index.py` / `tools/history_access.py` family, но default `--plan-version` остаётся v1. Не создавать второй resolver/catalog/reader и не считать v2 active без отдельной activation transition.

Storage-neutral v2 target разделяет `residence_role`, `adapter_profile`, opaque `resource_ref`, adapter-owned `physical_descriptor` и `integrity_evidence`. Technology-specific `storage` пока остаётся deprecated compatibility alias до pre-activation implementation migration; ResolutionPlan v3 ради этого не создаётся.

Полный operational status, agent examples, machine SSOT hierarchy, remaining physical gates и D9.5 provenance rules:

`docs/semantics/d9-operational-status-and-agent-usage-v1.md`.

Implementation-facing lifecycle background:

`docs/semantics/market-data-history-lifecycle-v1.md`.

Storage/publication reconciliation:

`docs/semantics/market-data-storage-portability-v2.md`.

## Почему D9 ещё не active

Source-level canonical Publication Port gap закрыт, а owner-accepted physical A1/A2 contour теперь тоже PASS: fresh checkpoint-v2 generation produced exact 20 eligible observations, current canonical `GITHUB_FIRST_V1` WARM publication passed durability/read-back/control-plane/resolver/reader checks, exact whole-batch ACK passed, the same 20 observations transitioned `PENDING→FORWARDED`, and replay was an idempotent no-op.

Это physical qualification, **не** authority activation. Binance USDⓈ-M remains `DISABLED_BY_POLICY`, D8/D9 remain inactive, production warm-forwarder scheduling is not deployed, and default route stays D6 / ResolutionPlan v1.

Accepted A1/A2 frontier:

```text
OLD_PRE_PRODUCTION_SHADOW
→ FORENSIC_PRESERVATION                 COMPLETE
→ CONTROLLED_SHADOW_RESET               COMPLETE
→ CURRENT_D8_DEPLOYMENT                 COMPLETE
→ CLEAN_VPS_SHADOW                      COMPLETE
→ NEW_REAL_CHECKPOINT_V2_DATA           COMPLETE
→ PHYSICAL_PUBLICATION_PORT             QUALIFIED
→ FIRST_PRODUCTION_ELIGIBLE_GENERATION  NEXT
→ REAL_D9_COLD_PHYSICAL_QUALIFICATION   BLOCKED_UNTIL_ELIGIBLE_GENERATION
→ ACTIVATION                            NOT_AUTHORIZED
```

Current regular-grid sealing policy remains `COMPLETED_MONTH_ONLY`; active-period sealing is disabled. Therefore the next real program predecessor is availability of the first production-eligible completed generation. Only after eligibility may a separately owner-authorized task execute the existing D9 COLD publication/read-back route and real D9.3+D9.4 cross-boundary semantic proof.

Existing production sealer remains:

```text
.github/workflows/seal-history.yml
→ tools/deep_history/history_sealer.py detect
→ tools/deep_history/history_sealer.py publish
→ immutable candidate publication/read-back
```

Do not run it for an active/ineligible period and do not create a second sealer/publisher. After a qualified real D9 COLD generation and cross-boundary PASS, a separate minimal activation transition is still required.

Before any future physical action, fresh server-side live readback remains mandatory. Repository status snapshots are evidence/coordination authority, not continuous VPS truth and not physical-mutation authorization by themselves.

`GITHUB_FIRST_V1` does not require `GITHUB_TOKEN` inside D8 runtime. Publication credentials remain owned by the separately authorized publication executor/adapter. Public D8 ingress is not required.

## D8 / high-cardinality boundary

```text
D8_STATUS_SEMANTICS=RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE
D8_AUTHORITY_ACTIVE=false
D8_RUNTIME_STATE_BACKEND=SQLITE_WAL
D8_RUNTIME_STATE_ROLE=OPERATIONAL_RUNTIME_STATE
D8_RUNTIME_STATE_IS_HISTORY_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_VPS_TARGET=REQUIRED
BINANCE_USDM_VPS_RUNTIME=NOT_ACTIVE
BINANCE_USDM_ACTIVE_PROVIDER=false

HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_VERSIONED_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

Published GitHub prerelease оказался immutable; mutable-in-place Release assumption — `HISTORICAL_PLAN_DECISION_SUPERSEDED` и не используется как current backend decision.

PostgreSQL сейчас не разворачивается. Future migration path допустим только behind same semantic interface; наличие existing server PostgreSQL не означает reuse decision.

## Provider/history semantics

`history_mode` values:

```text
MAX_AVAILABLE
PROVIDER_LIMITED
FORWARD_ONLY
FROZEN_REFERENCE
UNAVAILABLE
```

Known Binance H1 `2023-03-24T13:00:00Z` provider-native no-trading gap остаётся fail-closed в strict mode; synthetic candle запрещён.

## Выполнение и validation

```bash
python -m compileall -q src tools tests
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Network-backed historical materialization and production sealing qualification remain separate repository-owned workflows. Fresh/current provider acceptance is likewise a separate marker-gated candidate proof; normal unit/repository tests remain network-free.

## Ownership boundaries

Без отдельной authority-changing task не изменять:

- collector/cadence/provider acquisition;
- `bridge-contract.json` activation/default route;
- immutable COLD assets;
- raw/generated market rows;
- server/VPS acquisition plane;
- D8/Binance USD-M provider policy;
- Research wave/hypothesis/current objects;
- WARM retention/cleanup.

Новый mechanism допускается только если закрывает доказанный operational risk, проще существующих вариантов и уменьшает ручную работу следующего агента/инженера.

Не строить `StoragePluginManager`, generic persistence framework, Kafka/Redis/new warehouse или backend deployment без отдельного доказанного риска и versioned decision.

## D8 VPS unified acquisition runtime source candidate

- Canonical source contract: `contracts/d8-runtime-candidate.json`.
- Operational source semantics: `docs/semantics/d8-vps-unified-acquisition-runtime-v1.md`.
- Current reconciled physical/program status snapshot contract: `contracts/d8-a2-physical-qualification-status-v1.json`.
- Historical post-reset status predecessor: `contracts/d8-shadow-post-reset-status-v1.json`.
- Historical post-reset semantics: `docs/semantics/d8-shadow-post-reset-authority-v1.md`.
- Storage/publication boundary: `docs/semantics/market-data-storage-portability-v2.md`.
- Historical server handoff: `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md`.
- Entrypoint: `python -m d8_service`; container: `tools/d8/Dockerfile`.
- Source contract remains a source candidate and `VPS_ACTIVE` remains forbidden without a separate transition; its historical `NOT_DEPLOYED` labels do not override the separate reconciled physical/status snapshot contract.
- Current reconciled snapshot records accepted A1/A2 physical evidence and `SPOOL/PENDING/FORWARDED=20/0/20` at the accepted evidence point; live state must be re-read from server execution authority before any future physical action.
- D8 does not change `D9_ACTIVE=NO`, `ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1`, the hourly GitHub production acquisition schedule, or Binance USD-M GitHub `DISABLED_BY_POLICY` / `network_calls=0`.

## DB-F / S3 bounded exact-liquidity current requests

Current-data 1.1 adds optional `required_liquidity[]`. Each item is the existing
`liquidity-s1-semantic-request/1.0.0` object and is correlated with the single
capability index `requestable_capabilities[]`; agents still request semantics,
never provider URLs, hosts, paths, depth or transport knobs.

Exact-liquidity flow is:

```text
required_liquidity
→ requestable capability correlation
→ canonical S1 existing-resource satisfaction
→ canonical S1 acquisition plan
→ canonical S2 provider plan
→ bounded src/liquidity_s3_executor.py
→ one coherent provider observation
→ existing S2 parser
→ existing S1 qualification
→ current request binding
```

`src/liquidity_s1_runtime.py` remains the sole representation-compatibility
authority, including RAW → PROFILE dominance. Discovery groups candidates with a
representation-neutral family hash and MUST call S1 before reuse. Exact S3
resources are `EPHEMERAL_ONLY`, have no cross-run Actions-artifact cache. G2-A
не делает request-specific resource исторической authority: durable eligible
только underlying coherent `S3_NETWORK_ACQUIRED` observation, построенное через
тот же S1-normalized book и canonical durable serializer.

S3 initial execution is zero-retry / one provider observation / one physical
request or WebSocket session. Binance USDⓈ-M remains discoverable and
source-supported while GitHub runtime execution remains `DISABLED_BY_POLICY`
with zero network attempts. D8/VPS/provider-authority activation remains a
separate owner transition.

## Deep-liquidity durability G1/G2

Каноническая repository-owned карта продолжения после DB-F/S3:

```text
AGENTS.md
→ docs/semantics/deep-liquidity-program-map-v1.md
→ contracts/liquidity-durable-l2-observation-v1.json
```

Machine discoverability:

```text
AGENTS.md
→ bridge-contract.json
→ semantic_contracts.liquidity_durable_l2
→ contracts/liquidity-durable-l2-observation-v1.json
```

Human implementation semantics:

`docs/semantics/liquidity-durable-l2-observation-v1.md`.

Текущий owner-integrated program/contract stage:

```text
G1_PROGRAM_STAGE=CLOSED
G1_CONTRACT_INSTALLED=YES
G1_CONTRACT=ETH-LIQUIDITY-DURABLE-L2-OBSERVATION-V1
G1_WRITER_ACTIVE=NO
CURRENT_DEEP_LIQUIDITY_STAGE=G2-A
G2A=CLOSED
G2A_IMPLEMENTATION=COMPLETE
G2_A_WRITER_IMPLEMENTED=YES
G2_A_WRITER_ACTIVE=YES
G2_A_OWNER_INTEGRATION=PASS
G2A_OWNER_INTEGRATION=PASS
OWNER_INTEGRATED=YES
G2_B_READER_IMPLEMENTED=NO
G2B_STARTED=NO
ACTUAL_SIX_CAPABILITY_BENCHMARK_COMPLETE=YES
ACTUAL_SUCCESSOR_BYTE_BENCHMARK=PASS_R04_REUSED
SECOND_CONTROLLED_G2A_REQUALIFICATION=NO
R04_SIX_CAPABILITY_PROOF=REUSED_NO_SECOND_CONTROLLED_REQUALIFICATION
HOURLY_HISTORY_TARGET_BPS=500
PHYSICAL_DURABLE_L2_PARTITION=history/liquidity-orderbook-snapshots/YYYY/MM/DD/observations.json
SEMANTIC_HISTORY_FAMILY=liquidity.orderbook-snapshots
LEGACY_FIXED_100_SUCCESSION=COMPLETE
LEGACY_HISTORY_BYTES_MUTATED=NO
SYNTHETIC_BACKFILL=NO
REQUEST_RESOURCE_DURABILITY=EPHEMERAL_ONLY
FRESH_CURRENT_NEW_S3_OBSERVATION_DURABILITY=ELIGIBLE_FOR_CANONICAL_HISTORY
SAME_EXECUTION_REUSE_CREATES_HISTORY=NO
PERSISTED_REUSE_CREATES_HISTORY=NO
COHERENT_PARTIAL_OBSERVATION_DURABLE=YES
SECOND_DEDUPE_LEDGER=NO
SECOND_READER=NO
SECOND_RESOLVER=NO
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
D8_PROVIDER_AUTHORITY_TRANSITION=NO
D9_AUTHORITY_ACTIVATION=NO
VPS_MUTATION=NO
AIFE_SERVER_MUTATION=NO
DB_G_STARTED=NO
```

G2-A развивает только существующую `liquidity.orderbook-snapshots` family и переиспользует `liquidity-s1-normalized-book/1.0.0`, S1→S2→S3 execution, canonical durable builder/serializer и существующий immutable-history dedupe/conflict primitive. Новый multi-observation partition физически вынесен из legacy `liquidity/snapshots/**`, поэтому существующий event-window reader не получает несовместимый JSON shape. Семантическая family не меняется.

Legacy fixed-100 Binance Spot acquisition в hourly intelligence context destructively succeeded canonical G2-A route: активного `provider("binance-spot", spot)` больше нет, исторические legacy bytes не переписываются и не переименовываются в 500 bps complete. Binance USDⓈ-M GitHub policy остаётся `DISABLED_BY_POLICY` / zero network calls.

Fresh Current сохраняет request/observation separation: exact request resource остаётся `EPHEMERAL_ONLY`; только новое coherent `S3_NETWORK_ACQUIRED` underlying observation получает transfer evidence для того же hourly durable publisher. `SAME_EXECUTION_REUSE` и persisted reuse не создают fake history. Target miss не уничтожает observed market fact: coherent partial/truncated observation может быть durable с фактической coverage и `extrapolation_allowed=false`, тогда как consumer request satisfaction остаётся отдельным fail-closed verdict.

G2-A owner integration завершена: `G2_A_OWNER_INTEGRATION=PASS`, writer active, R04 six-capability/byte proof reused, второй controlled G2-A provider requalification не запускался. G2-B, DB-G, D8/D9 activation, server/VPS mutation и provider-authority transition этим контуром не начаты.

Следующий отдельный exact task: `ETH-LIQUIDITY-G2B-SAMPLED-HISTORY-READER-SUCCESSOR-PREIMPLEMENTATION-OWNER-REVIEW-R01`. До отдельной owner authorization G2-B implementation запрещён.
