# S1 liquidity semantic contract v1

## Статус и authority

```text
CONTRACT_ID=ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1
MACHINE_AUTHORITY=contracts/liquidity-s1-semantic-contract-v1.json
STATUS=ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE
ARCH_B_CAPABILITY_SELECTIVE_EXTENSION=RETAINED
S1_SOURCE_IMPLEMENTATION=NO
S2_PROVIDER_ROLLOUT=NO
S3_REQUEST_AWARE_NETWORK_ACTIVATION=NO
```

Этот документ — human-readable implementation-facing представление machine contract. Он не создаёт второй catalog, resolver, reader, collector, refresh transport, capability authority или provider authority. Route/provider-policy authority остаётся `bridge-contract.json`; provider/API facts принадлежат `contracts/provider-contracts.json`; existing capability discovery/resolution остаётся тем же `history/capability-index.json → tools/capability_index.py → ResolutionPlan → tools/history_access.py` contour.

Standalone correction/review/recovery packages — только historical evidence/carrier. Они не являются canonical SSOT после этой установки.

## Почему создан новый contract owner

До этой currentization repository имел current liquidity runtime и generic capability/current-data semantics, но не имел отдельного canonical owner для будущего S1 semantic depth/coverage/acquisition-plan contract. Поэтому создан ровно один machine owner `contracts/liquidity-s1-semantic-contract-v1.json`. Он является additive extension существующей Market Data Foundation, а не новым data subsystem.

## Canonical mapping accepted corrections → owner

Mutation column описывает **физическую правду текущего PR #295**, а не желаемое намерение. `CURRENTIZE` допустим только для owner path, который реально изменён этим PR.

| Accepted correction | Canonical owner | Section / role | Mutation | Reason |
|---|---|---|---|---|
| Canonical entrypoint discoverability | `AGENTS.md` | Liquidity S1 semantic architecture pointer | CURRENTIZE | Текущий PR добавляет concise canonical pointer, не дублируя contract |
| Route/provider-policy graph discoverability | `bridge-contract.json` | `semantic_contracts.liquidity_s1` | CURRENTIZE | Текущий PR additively связывает S1 owner без изменения active D6 route |
| Dynamic depth, coverage request, AcquisitionPlan | `contracts/liquidity-s1-semantic-contract-v1.json` | `dynamic_depth_acquisition_plan` | ADD | Ранее canonical owner отсутствовал |
| Resource satisfaction / coverage dominance | тот же contract | `resource_satisfaction` | ADD | Нужен единый pre-acquisition semantic rule |
| Coverage/book-kind model | тот же contract | `coverage`, `book_kind` | ADD | Не должен жить в provider adapter |
| Native-first derivatives quantity | тот же contract | `derivatives_quantity` | ADD | Cross-provider semantic invariant |
| Observation coverage != value validity | тот же contract | `observation_value_validity` | ADD | Global consumer-qualification invariant из accepted PR #283 |
| Kraken Futures trade-flow qualification | тот же contract | `kraken_futures_trade_flow` | ADD | Accepted runtime outcome закреплён как architecture semantics без globalizing provider detail |
| Historical/release CVD scope reference | `docs/semantics/kraken-futures-cvd.md` | predecessor CVD/release semantics | HISTORICAL_REFERENCE_ONLY | PR #295 не изменяет этот документ; его исторический scope остаётся совместимым |
| Provider capabilities/boundaries | `contracts/provider-contracts.json` | Kraken Spot / Futures book contracts | CURRENTIZE | Это существующий provider/API contract owner и он физически изменён PR #295 |
| Existing capability/resolver continuity | `docs/semantics/capability-index.md` | additive S1 boundary | CURRENTIZE | PR #295 физически currentizes этот owner и не допускает второй catalog/resolver/reader |
| Fresh-current validity preservation | `docs/semantics/fresh-current-agent-transport-v1.md` | liquidity S1 / projection boundary | CURRENTIZE | PR #295 физически currentizes existing current-data owner |
| D8 fixed depth `limit=100` scope | `docs/semantics/d8-vps-unified-acquisition-runtime-v1.md` | current runtime vs S1 semantic contract | NO_CHANGE_ALREADY_COMPATIBLE | Existing D8 doc уже ограничивает `limit=100` current source/runtime scope; PR #295 его не меняет |
| Current D8 hourly cadence / exact-minute non-authority | `.github/workflows/qualify-d8-runtime.yml` | current accepted cadence qualification | NO_CHANGE_ALREADY_COMPATIBLE | S1 does not mutate scheduler or D8 qualification |
| Current human authority hierarchy | `docs/semantics/d9-operational-status-and-agent-usage-v1.md` | machine SSOT hierarchy | CURRENTIZE | Текущий PR минимально добавляет discoverability pointer без второго route |

## Dynamic depth — first-class contract

Agent-facing depth request выражает semantic coverage, а не provider-specific limit:

```text
series_id
book_kind
representation
target_bps
bucket_bps
freshness
completeness
```

Минимально canonical vocabulary выражает `target_bps=250` и `target_bps=500`.

Нормативный flow:

```text
SEMANTIC_COVERAGE_REQUEST
→ RESOURCE_SATISFACTION_CHECK
→ DYNAMIC_DEPTH_ACQUISITION_PLANNER
→ EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN
→ ONE_COHERENT_PROVIDER_OBSERVATION
```

Agent не обязан знать или угадывать Binance/Kraken provider depth/level knobs. Provider-specific limit/depth — planner output только после capability qualification.

Один logical observation не может быть построен путём stitching отдельных REST responses `100 → 500 → 1000 → 5000`. Retry создаёт новый observation.

`AcquisitionPlan` interface определён в S1, но S1 **не выполняет** request-aware provider network acquisition. Mapping в adapters — S2; runtime selective network activation — S3.

## Resource satisfaction и dominance

До network acquisition system обязан проверить, не существует ли уже fresh coherent resource, который покрывает request. Dominance сравнивает как минимум:

- provider;
- market/instrument identity;
- book kind;
- representation;
- freshness;
- side coverage;
- actual achieved coverage bps;
- completeness;
- integrity.

Более глубокий fresh coherent `RAW` может удовлетворить более узкий downstream `PROFILE`, если semantic identity совместима и requested coverage полностью лежит внутри реально наблюдаемого book. Reacquisition в таком случае не требуется.

## Coverage semantics

Нужно различать три разные величины:

1. requested target coverage;
2. provider acquisition depth/limit;
3. actual achieved coverage.

Observation сохраняет side-specific coverage:

```text
requested_bid_coverage_bps
requested_ask_coverage_bps
achieved_bid_coverage_bps
achieved_ask_coverage_bps
coverage_complete_bid
coverage_complete_ask
truncated
```

Экстраполяция вне observed book запрещена. `TRUNCATED` допустим только как explicit `PARTIAL/INCOMPLETE`. Если request требует mandatory completeness, а target не достигнут, результат fail closed.

## Book kind != representation

Semantic book kinds:

```text
L2_LEVEL_BOOK
PROVIDER_GROUPED_L2
L3_ORDER_BOOK
FUTURES_L2_BOOK
```

Representations:

```text
RAW
NORMALIZED
PROFILE
SUMMARY
```

Kraken provider-native `GroupedBook` не становится AIFE `PROFILE` автоматически. L3 не является обычным L2 RAW. RAW/NORMALIZED/PROFILE/SUMMARY — разные представления evidence, а не независимые аналитические votes.

## Kraken Spot boundary

Provider capability и current AIFE resource — разные факты:

```text
KRAKEN_SPOT_PROVIDER_RAW_BOOK_CAPABILITY=AVAILABLE_EXTERNALLY
KRAKEN_SPOT_RAW_BOOK_IN_CURRENT_BRIDGE=ABSENT
```

Accepted provider surfaces: REST L2 order book, WS v2 L2 with selectable depth, provider-native GroupedBook и authenticated L3 как отдельная forensic surface. Наличие provider endpoint не доказывает наличие canonical AIFE resource. L3 остаётся future forensic successor до отдельной authorization.

## Kraken Futures book boundary

```text
KRAKEN_FUTURES_RAW_L2_BOOK=PROVIDER_CAPABILITY_CONFIRMED
KRAKEN_FUTURES_SELECTABLE_DEPTH_LIMIT=NOT_NORMATIVELY_DOCUMENTED
```

Normative max depth не изобретается. Если provider не документирует request depth knob, будущий adapter обязан использовать explicit message/read/byte/resource bounds и fail closed вместо silent RAW truncation.

Первый raw-book family должен сохранить current analytics product identity `PI_ETHUSD` и `PI_XBTUSD`. PF family не может silently substitute PI.

## Derivatives quantity — native first

Universal mapping `provider qty → base_quantity` запрещён для derivatives. Normalized model поддерживает provider-native quantity/unit, contract type/value/multiplier/currency, instrument spec identity и versioned conversion formula. `base_equivalent` и `quote_notional` nullable.

Если conversion semantics не доказаны, derived equivalent = `null/UNAVAILABLE`; provider-native fields остаются. PI и PF identities не схлопываются.

## Observation coverage != value validity

Global invariant:

```text
OBSERVATION COVERAGE != VALUE VALIDITY
UNOBSERVED DATA MUST NEVER MASQUERADE AS OBSERVED ZERO
```

Canonical consumer states включают минимум:

```text
VALID_ZERO
UNAVAILABLE
NOT_QUALIFIED
SOURCE_CONFLICT
MISALIGNED
UNKNOWN
PARTIAL / INCOMPLETE
```

`OBSERVED_COMPLETE_INTERVAL_NO_EVENTS` может дать `count=0`, `volume=0`, `delta=0` только когда источник реально наблюдался и completeness доказана. Это не равно feed unavailable, not observed, incomplete coverage, parser failure, unsupported metric или unknown conversion.

Для separately produced provider-native numerical series применимая consumer qualification требует сочетания:

```text
SOURCE_OBSERVED
COVERAGE_SUFFICIENT
TEMPORAL_ALIGNMENT_PROVEN
METRIC_SEMANTICS_QUALIFIED
NO_SOURCE_CONFLICT
```

`coverage_complete=true` само по себе не доказывает numerical value отдельной provider-native series.

## Accepted Kraken Futures trade-flow semantics

`trade-count`:

- direct raw execution reconciliation — `QUALIFIED`;
- current Market Analytics interval — 300 seconds;
- accepted current timestamp semantics — `BUCKET_END`;
- raw bucket — `[bucket_start,bucket_end)`;
- same-bucket raw/native `MATCH` обязателен;
- mismatch = `SOURCE_CONFLICT`;
- complete aligned raw/native zero = `VALID_ZERO_NO_TRADES_IN_BUCKET`.

`trade-volume`: provider-native series существует, но raw `/history size` → analytics base-volume equivalence = `NOT_QUALIFIED`.

`aggressor-differential`: taker-side sign semantics understood, PI raw-size quantity-unit equivalence = `NOT_QUALIFIED`.

`CVD`: provider-native state сохраняется; one-bucket raw signed flow не считается равным absolute native CVD; raw-delta/state equivalence = `NOT_QUALIFIED`.

Для этого current raw-value qualification contour запрещены L2-derived executed trades, CVD reconstruction/reset и invented raw quantity conversion.

## Provider-native present != consumer-qualified available

Provider-native observation может оставаться доступным для diagnostics/forensics, но ordinary consumer-facing value fail closed, если qualification не пройдена. Validity envelope не должен теряться по route:

```text
DERIVATIVES
→ ANALYTICS
→ CURRENT_DATA
→ CONSUMER
```

Это runtime-подтверждено accepted PR #283 и закреплено как architecture invariant.

## Current D8 fixed-depth scope

Текущий D8 source-candidate исторически имеет bounded Binance depth request `limit=100`. Это **не** agent-facing S1 request contract и **не** normative provider max depth. Этот existing source behavior сохраняется до отдельной S2/S3 implementation/activation wave; текущая SSOT installation его не переписывает и не активирует dynamic-depth network execution.

## Current hourly scheduler boundary

S1 не владеет exact scheduler minute и не восстанавливает predecessor exact-minute OD-01 mismatch marker. Current D8 authority квалифицирует hourly cadence; `.github/workflows/update-market.yml` и `.github/workflows/qualify-d8-runtime.yml` этим task не изменяются.

```text
S1_CURRENTIZATION_DOES_NOT_REINTRODUCE_STALE_OD01=PASS
SCHEDULER_MUTATION_BY_S1=NO
D8_PR_SYNTHETIC_PARENT1_EVENT_BASE_RACE=RECORDED_NOT_REPAIRED
```

## Currentization after Fresh Current successors

Current `main` successor semantics have priority. S1 preserves accepted PR #283 fail-closed value validity and PR #299 request-scoped qualification:

```text
GENERATION_INTEGRITY != METRIC_QUALIFICATION != REQUEST_SATISFACTION
FAILURE_RELEVANCE=GLOBAL_STRUCTURAL | REQUESTED_RESOURCE | REQUESTED_DOMAIN | UNREQUESTED_RESOURCE
UNRELATED_DEGRADED_METRIC_POISONS_SATISFIED_REQUEST=NO
SOURCE_CONFLICT -> unavailable -> value=null
NOT_QUALIFIED -> unavailable/not-qualified -> value=null
UNOBSERVED != ZERO
VALID_ZERO -> numeric 0 only when explicitly proven
```

Dynamic depth remains semantic-only in S1. Provider/network execution is still S2/S3 work.

## S1 / S2 / S3 terminal boundary

```text
ACQUISITION_PLAN_CONTRACT=DEFINED_IN_S1
REQUEST_AWARE_NETWORK_ACQUISITION=NOT_IMPLEMENTED_BY_S1
S1_SOURCE_IMPLEMENTATION_PERFORMED=NO
PROVIDER_ROLLOUT_PERFORMED=NO
ACTIVE_DATA_ROUTES_CHANGED=NO
```

Следующий допустимый шаг после merge этого SSOT contract — отдельная bounded S1 implementation wave, только после independent owner review/merge. S2/S3 network behavior остаётся вне этой currentization.
