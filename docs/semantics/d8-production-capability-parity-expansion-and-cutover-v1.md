# D8 production capability parity, expansion and cutover master specification v1

```text
SPEC_ID=ETH-MARKET-DATA-PRODUCTION-READINESS-MASTER-SPEC-V1
TASK_FAMILY=MARKET_DATA_FOUNDATION
STATUS=PLANNING_AUTHORITY_NOT_ACTIVATION
IMPLEMENTATION_AUTHORITY=vitaliipython-ship-it/eth-macro-data-bridge
PLANNING_AUTHORITY=vitaliipython-ship-it/eth-macro-research/docs/programs/market-data-foundation.md
CURRENT_PROFILE=GITHUB_FIRST_V1
PRODUCTION_ACTIVATION_FORBIDDEN=true
VPS_ACTIVE_FORBIDDEN=true
PROVIDER_AUTHORITY_TRANSITION_FORBIDDEN=true
LEGACY_GITHUB_ACQUISITION_DISABLE_FORBIDDEN=true
PRODUCTION_WARM_FORWARDER_SCHEDULING_FORBIDDEN=true
PRODUCTION_CUTOVER_FORBIDDEN=true
BUILD_AND_TEST_THE_COMPLETE_COMPACT_CONTOUR_FIRST=true
PRODUCTION_LAUNCH_ONLY_AFTER_COMPLETE_READINESS=true
D8_WARM_PRODUCTION_BLOCKED_ON_MONTHLY_COLD=NO
D9_COLD_REMAINS_SEPARATE_LIFECYCLE_STAGE=YES
```

## 1. Назначение и authority

Этот документ — единая implementation-facing master specification целевого production market-data contour перед дальнейшим D8/D9 production activation. Он фиксирует capability parity, compact expansion, ownership, scaling, qualification, cutover и rollback semantics. Он **не** активирует D8/D9, не меняет provider authority, не запускает provider acquisition, не выбирает permanent high-cardinality backend и не разворачивает server/database runtime.

Machine authority текущего состояния остаётся:

- `bridge-contract.json`;
- `contracts/d8-runtime-candidate.json`;
- `contracts/d8-d9-forwarding-v1.json`;
- `contracts/d8-a2-physical-qualification-status-v1.json`;
- referenced schemas/contracts.

Этот документ задаёт обязательный target/readiness contract для будущих implementation tasks. Если current machine state и target state различаются, target здесь не считается активным до отдельной owner-authorized transition.

## 2. Accepted baseline, который нельзя потерять

Owner-accepted A1/A2 evidence уже доказывает:

```text
D8_A1_PHYSICAL_QUALIFICATION=PASS
D8_TO_D9_PUBLICATION_PORT_A2=PASS
CANONICAL_PUBLICATION=QUALIFIED
REMOTE_DURABILITY_READBACK=PASS
RESOLVER_VISIBILITY=PASS
READER_MATERIALIZATION=PASS
CANONICAL_ACK=PASS
PENDING_TO_FORWARDED=PASS
IDEMPOTENT_REPLAY=PASS
```

Но текущая production authority остаётся неизменной:

```text
D8_ACTIVE=false
D9_ACTIVE=false
PRODUCTION_WARM_FORWARDER_DEPLOYED=false
PRODUCTION_CUTOVER=false
PROVIDER_AUTHORITY_TRANSITION=false
LEGACY_GITHUB_PRODUCTION_ACQUISITION_ACTIVE=true
D9_COLD_V2_AUTHORITY=NOT_ACTIVE
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
```

A1/A2 — proof publication mechanics, а не proof полной capability parity и не production activation authorization.

## 3. Binance USD-M: scope correction без текущей activation

`DISABLED_BY_POLICY` относится к текущему GitHub-hosted acquisition runtime, а не к глобальному target provider status.

```text
BINANCE_USDM_GITHUB_ACQUISITION=DISABLED_BY_POLICY
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
BINANCE_USDM_D8_VPS_TARGET=REQUIRED
BINANCE_USDM_D8_VPS_PRODUCTION_TARGET=ACTIVE
BINANCE_USDM_PROVIDER_AUTHORITY_TRANSITION=SEPARATE_VERSIONED_PRODUCTION_CUTOVER
```

До отдельного cutover current machine state остаётся `NOT_ACTIVE`. GitHub runtime не должен делать Binance USD-M network calls. После полного R0–R7 readiness и отдельной R8 authorization qualified D8 VPS target обязан включать Binance USD-M production acquisition.

## 4. Master information model

Четыре логических слоя:

```text
L0_PROVIDER_EVIDENCE
L1_NORMALIZED_MARKET_FACTS
L2_DETERMINISTIC_MARKET_DERIVED_METRICS
L3_ANALYTICAL_DOMAINS
```

Ownership:

```text
DATA_BRIDGE_OWNS=L0+L1+L2
RESEARCH_OWNS=L3
```

### L0 — provider evidence

Provider-native rows/snapshots/events, exact provider timestamps, raw fields required for reproduction, source route identity, retrieval/known-at evidence, provider revisions and immutable/raw evidence where required.

### L1 — normalized market facts

Canonical `series_id`/`observation_id`, normalized timestamps/units/finality/freshness, provider identity, lifecycle classification and provenance. Normalization may change representation, not semantic source identity.

### L2 — deterministic market-derived metrics

Deterministic market-structure derivations from canonical L0/L1 evidence. Formula/version/provenance are mandatory. They remain market facts/measurements and must not contain interpretation, scenario or trade direction.

```text
DERIVED_METRIC_IS_NOT_SOURCE_AUTHORITY=true
PROVIDER_NATIVE_AND_DERIVED_EQUIVALENT_MAY_COEXIST=true
PROVIDER_NATIVE_AND_DERIVED_EQUIVALENT_SHARE_IDENTITY=false
```

Example:

```text
KRAKEN_PROVIDER_NATIVE_CVD != DATA_BRIDGE_DERIVED_CVD
```

Distinct identity/provenance is required even if numeric values temporarily match.

### L3 — analytical domains

Research owns interpretation and epistemic synthesis: patterns, waves, regimes, hypotheses, scenarios, domain states, probabilities and modeling. Provider acquisition must not emit scenario/interpretation logic.

## 5. Technical Indicators — separate Research domain

Traditional technical indicators are **not** Data Bridge L2 market-derived ownership by default:

```text
RSI MACD ATR SMA EMA ADX STOCHASTIC CCI BOLLINGER_BANDS ICHIMOKU MFI OBV
```

and future comparable indicator methods belong to Research `TECHNICAL_INDICATORS`.

Canonical route:

```text
canonical market observations
→ TECHNICAL_INDICATORS
→ versioned indicator observations/features
→ higher analytical domains
```

Planning-level future identity must preserve at least:

```text
indicator_id
indicator_version
input_series_id
input_resolution
parameters
effective_at
known_at
calculation_fingerprint
source_observation_range
```

Research already has `docs/programs/technical-indicators.md`; no second indicator program is created here. Successor roadmap task remains `ETH-TECHNICAL-INDICATORS-DOMAIN-V1` against that existing owner program.

Where a name overlaps, identity decides ownership. For example Data Bridge may define a canonical tape/book/candle-derived `VWAP` or standardized realized-volatility market metric as L2, while Research may define a technical-indicator method using similar mathematics. They must have distinct IDs, versions and provenance and may not be silently aliased.

## 6. Allowed Data Bridge L2 metric families

Subject to explicit versioned formula/input contracts, Data Bridge may own deterministic market-derived measurements including:

- CVD, buy/sell delta, aggressive buy/sell volume, taker imbalance;
- VWAP / buy VWAP / sell VWAP as market/tape derivations;
- basis, annualized basis, basis curve / term structure;
- OI delta / OI percentage change and price × OI mechanical quadrant;
- funding normalization/z-score and basis normalization/z-score when their statistical window contract is explicit;
- spot/perp divergence;
- liquidation impulse / imbalance;
- spread, order-book imbalance, depth slope, liquidity concentration, slippage and price-impact proxy;
- standardized realized volatility as a market-derived series with explicit identity distinct from Research indicator methods;
- option IV term structure, risk reversal, butterfly;
- OI by expiry/strike;
- gamma/vega concentration proxy with explicit formula/provenance;
- ETH/BTC volatility differential;
- large-trade statistics and compact microstructure aggregates.

These outputs are evidence, not bullish/bearish scenarios.

## 7. P0 — exact GitHub → D8 capability parity closure

Production authority transition is forbidden until:

```text
CURRENT_GITHUB_INFORMATION_SET SUBSET_OF D8_VPS_INFORMATION_SET
```

For provider-native higher timeframes, D8 must preserve native observations. Synthetic M5 aggregation may be a consistency check or separate derived series; it may not become the sole authority when provider-native data is currently preserved.

### 7.1 Confirmed information-loss gap registry

The following gaps are grounded in current repository behavior and are mandatory P0 closure items.

| ID | Provider | Confirmed current gap | Required closure |
|---|---|---|---|
| P0-01 | Binance Spot | D8 `_ohlcv` promotes O/H/L/C/volume only and drops rich native M5 fields | Preserve `base_volume`, `quote_volume`, `trade_count`, `taker_buy_base_volume`, `taker_buy_quote_volume`, `close_time` plus OHLC |
| P0-02 | Binance Spot | D8 capability is M5-only while GitHub preserves native 15m/1h/4h/1d/1w | Canonical D8 native 5m/15m/1h/4h/1d/1w |
| P0-03 | Kraken Spot | D8 `_ohlcv` drops native VWAP/trade_count richness | Preserve OHLC, VWAP, volume, trade_count and provider timestamp/finality |
| P0-04 | Kraken Spot | D8 capability is M5-only while GitHub preserves native 15m/1h/4h/1d/1w | Canonical D8 native 5m/15m/1h/4h/1d/1w |
| P0-05 | Binance USD-M | `openInterestHist` rows are fetched/written in temporary acquisition tree but D8 promotes no OI-history observations | Durable canonical OI history 5m including provider-native `sumOpenInterestValue`/notional where returned |
| P0-06 | Binance USD-M | funding history is fetched/written but D8 promotes only current composite funding | Durable canonical funding history plus current funding identity |
| P0-07 | Kraken Futures | acquisition appends all eligible analytics rows, D8 facade emits only each metric `latest` | Promote every eligible row for all 13 current metric families |
| P0-08 | Kraken Futures | provider revision/PIT evidence exists in GitHub lifecycle but is not emitted by D8 acquisition observation path | Preserve revision evidence: effective timestamp, known_at, previous fingerprint, observed value, revision_of, source snapshot provenance |
| P0-09 | Deribit Perpetual | GitHub durable funding H1 exists; D8 perpetual capability is current ticker only | Preserve funding H1 history through D8 |
| P0-10 | Deribit Perpetual | GitHub durable perpetual OHLCV H1 exists; D8 current capability does not promote it | Preserve perpetual OHLCV H1 history through D8 |
| P0-11 | Deribit Options | GitHub writes full ETH DVOL H1 history; D8 emits only latest DVOL observation | Preserve every newly eligible DVOL H1 row, not latest-only |
| P0-12 | Deribit Liquidity | GitHub passes selected option names to book collection; D8 calls liquidity with `selected_options=[]` | Preserve selected option order-book snapshots and selection provenance; no silent loss |

```text
P0_CONFIRMED_INFORMATION_LOSS_GAP_COUNT=12
```

### 7.2 Production-required existing D8 capabilities that must not regress

Current D8 already has source support for some Binance USD-M evidence. P0 must retain it while closing the gaps:

- rich provider-native 5m perp kline row;
- provider-native 1h/4h/1d perp klines;
- current mark/index/basis/premium/funding/OI composite;
- bounded depth snapshot.

P0 must make all fetched valuable rows canonical before staging is removed. Temporary acquisition files are never the only durable location for production-required evidence.

### 7.3 Kraken Futures current metric universe

Every eligible row must be preserved for:

```text
open-interest
aggressor-differential
trade-volume
trade-count
liquidation-volume
rolling-volatility
long-short-ratio
cvd
spreads
liquidity
slippage
future-basis
funding
```

Current semantic classes are retained:

```text
STRICT_OVERLAP_REQUIRED
WINDOW_ANCHORED_CUMULATIVE
PROVIDER_REVISABLE_SNAPSHOT
```

Current provider-revisable set includes `spreads`, `liquidity`, `slippage`, `future-basis`, `funding`. Cutover that keeps only latest value and loses earlier-known revisions is forbidden.

### 7.4 Deribit options/liquidity P0 preservation

Preserve current GitHub information set:

- full active ETH option surface;
- selected ATM/25-delta Greeks and selection evidence;
- full forward ETH DVOL H1 observations;
- selected option books used by liquidity analytics;
- current perpetual book where collected.

No historical option/book evidence may be fabricated when it was never collected.

## 8. Legacy `update-market.yml` responsibility decomposition

Disabling overlapping provider acquisition in a future cutover does **not** mean deleting the whole legacy workflow. Every responsibility must remain or be migrated explicitly.

| Responsibility | Current workflow duties | Cutover rule |
|---|---|---|
| `PROVIDER_ACQUISITION` | `python src/collector.py` invokes rolling spot plus intelligence/provider collection | Disable only overlapping acquisition authority after cutover proof |
| `VALIDATION` | snapshot increment checks; `validate.py`; `validate_v4.py`; `validate_history.py`; `consumer_proof.py`; dispatch qualification; final validation; compileall | Retain or migrate with equivalent/exceeding proof |
| `COMPATIBILITY_PROJECTION` | rolling `data/*`, manifests and compatibility outputs produced by collector/history pipeline | Preserve while any consumer/validator still requires them; migrate explicitly |
| `HISTORY/LIFECYCLE` | archive append, native history, Deribit history, Kraken revision observer, sampled-history ledger and consistency generation | Migrate responsibility to D8→D9 lifecycle only after parity/continuity proof; never silently drop |
| `PUBLICATION` | remote-main concurrency guard, generated data commit, push of declared data domains | Remove/replace only after canonical D8 PublicationBatch/WARM publication is production-authoritative |
| `DIAGNOSTICS` | provider status/error reporting, overall plane status, archive/history counts/sizes and publish latency | Preserve operational visibility in successor route |

```text
LEGACY_WORKFLOW_BLIND_DELETE_FORBIDDEN=true
ONLY_OVERLAPPING_PROVIDER_ACQUISITION_AUTHORITY_DISABLE_ALLOWED_AFTER_CUTOVER=true
```

## 9. P1 — compact high-value data expansion

P1 follows P0 source parity and precedes final production cutover. Each candidate requires fresh verification against official provider documentation and real current rate-limit budget immediately before implementation.

```text
P1_ENDPOINT_FIELD_GUESSING=FORBIDDEN
P1_OFFICIAL_DOCUMENTATION_REVERIFY_REQUIRED=true
P1_RATE_BUDGET_REVERIFY_REQUIRED=true
```

A candidate that is unavailable, not historical, too expensive or semantically unstable must be explicitly classified instead of fabricated.

### 9.1 Candidate registry

| ID | Provider | Candidate family | Planning classification |
|---|---|---|---|
| P1-01 | Binance USD-M | global long/short account ratio | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-02 | Binance USD-M | top-trader long/short accounts | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-03 | Binance USD-M | top-trader long/short positions | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-04 | Binance USD-M | taker buy/sell volume | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-05 | Binance USD-M | mark-price klines | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-06 | Binance USD-M | index-price klines | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-07 | Binance USD-M | premium-index klines | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-08 | Binance USD-M | funding interval/cap/floor configuration where exposed | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-09 | Binance USD-M | liquidation events or deterministic M5 liquidation aggregate | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-10 | Binance USD-M | enhanced order-book/depth evidence | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-11 | Binance Spot | aggTrades/trade evidence | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-12 | Binance Spot | aggressive buy/sell flow aggregate | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-13 | Binance Spot | trade-count distribution | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-14 | Binance Spot | large-trade notional statistics | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-15 | Binance Spot | trade-side VWAP / deterministic M5 trade-flow aggregates | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-16 | Kraken Futures | `long-short-info` candidate | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-17 | Kraken Futures | `top-traders` candidate | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-18 | Kraken Futures | `orderbook` candidate | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-19 | Kraken Futures | provider-native trade candles | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-20 | Kraken Futures | provider-native mark candles | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-21 | Kraken Futures | provider-native spot-reference candles | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-22 | Kraken Futures | trade classifications for normal/liquidation/block/etc compact aggregates | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-23 | Kraken Spot | book order-count evidence by level where officially supported | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-24 | Deribit | BTC option surface | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-25 | Deribit | BTC DVOL | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-26 | Deribit | ETH/BTC historical volatility | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-27 | Deribit | dated futures curve | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-28 | Deribit | OI by maturity | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-29 | Deribit | future basis / annualized basis term structure | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-30 | Deribit | fuller option Greeks coverage | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-31 | Deribit | public trade flow | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-32 | Deribit | option IV attached to trades | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-33 | Deribit | liquidations | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-34 | Deribit | block trades | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-35 | Deribit | combo/multi-leg trade identity | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |
| P1-36 | Deribit | Block RFQ evidence | VERIFY_OFFICIAL_DOCS_AND_RATE_BUDGET |

```text
P1_EXPANSION_FAMILY_COUNT=36
```

Institutional multi-leg identifiers supplied by a provider must be preserved. Combo/block/RFQ legs may not be silently misclassified as independent directional trades.

Raw trade/book/event streams whose cardinality exceeds compact backend policy are escalated to P2 rather than forced into Git WARM.

## 10. P2 — high-cardinality contour

Dedicated successor decision:

```text
ETH-MARKET-DATA-HIGH-CARDINALITY-WARM-BACKEND-DECISION-V1
```

Candidate source classes:

- raw trades / aggTrades;
- liquidation streams;
- L2 depth deltas;
- L3 order events/public order events;
- Deribit high-frequency ticker/book;
- institutional trade-flow evidence.

Hard boundary:

```text
D8_SQLITE_WAL=OPERATIONAL_RUNTIME_STATE
D8_SQLITE_WAL!=PERMANENT_HIGH_CARDINALITY_HISTORY_WAREHOUSE
HIGH_CARDINALITY_BACKEND_SELECTED_BY_THIS_SPEC=false
POSTGRES_DEPLOYED_BY_THIS_SPEC=false
OBJECT_STORAGE_DEPLOYED_BY_THIS_SPEC=false
```

Future backend requirements:

- append/idempotent ingestion;
- partitioning, retention and compression;
- point-in-time / `known_at` semantics;
- provider revision support;
- immutable/raw preservation where required;
- horizontal write scaling;
- bounded replay/recovery;
- canonical resolver compatibility;
- backend-independent `series_id`;
- backend-independent `observation_id`.

## 11. Current storage strategy and future portability

```text
CURRENT_PROFILE=GITHUB_FIRST_V1
BACKEND_MIGRATION_IS_ADAPTER_TRANSITION=true
BACKEND_MIGRATION_IS_SEMANTIC_REWRITE=false
```

GitHub is intentionally the current implementation profile while identity, provenance, acquisition, normalization, publication, lifecycle and semantic consumption are stabilized. Future `GitHub WARM → database/object-store WARM` may change adapter/profile, physical descriptors, migration tooling and durability evidence only.

It must not change:

- `series_id`;
- `observation_id`;
- semantic request shape;
- canonical resolver family;
- ResolutionPlan family;
- canonical reader family;
- semantic receipt meaning.

No database is selected here. Existing server PostgreSQL is not an implicit reuse decision.

## 12. Horizontal scaling invariants

### 12.1 Data expansion

Adding provider/instrument/pair/timeframe/metric/series/depth cardinality must not by default require:

```text
NEW_RESOLVER=NO
NEW_READER=NO
NEW_HISTORY_SUBSYSTEM=NO
NEW_STORAGE_PROTOCOL=NO
NEW_MARKET_DATA_AUTHORITY=NO
```

A new provider can require its own network/auth/normalization adapter and qualification, while still using the same semantic history architecture.

### 12.2 Execution expansion

Target model:

```text
canonical M5 slot
→ due-policy resolution
→ independent capability work units
→ provider/capability workers
→ deterministic checkpoints
→ SPOOL
→ PublicationBatch
```

Future sharding may be by provider, capability or instrument group without changing observation identity or semantic authority.

### 12.3 Shared rate-budget ownership

Workers do not receive independent imaginary provider budgets.

```text
PROVIDER → RATE_BUDGET → CAPABILITIES → WORKERS
```

The shared logical contract must support:

- provider weight accounting;
- backoff and 429 handling;
- provider-specific concurrency caps;
- bounded retry budget;
- circuit-breaker/degradation semantics;
- rate-budget observability.

No generic distributed infrastructure is required until a measured bottleneck proves it necessary.

### 12.4 Idempotency under concurrency

Horizontal concurrency must preserve:

```text
cycle_id
capability_id
series_id
observation_id
provider_timestamp
known_at
checkpoint_identity
PublicationBatch_membership
ACK_state
```

Parallel workers must never create duplicate semantic authority.

## 13. Pre-production freeze policy

Until the complete compact production contour passes R0–R7:

```text
PRODUCTION_ACTIVATION_FORBIDDEN=true
VPS_ACTIVE_FORBIDDEN=true
PROVIDER_AUTHORITY_TRANSITION_FORBIDDEN=true
LEGACY_GITHUB_ACQUISITION_DISABLE_FORBIDDEN=true
PRODUCTION_WARM_FORWARDER_SCHEDULING_FORBIDDEN=true
PRODUCTION_CUTOVER_FORBIDDEN=true
```

Allowed pre-production work:

- source implementation;
- local deterministic/unit/integration tests;
- repository-hosted CI qualification;
- disposable/container qualification;
- explicitly owner-authorized `VPS_SHADOW` deployments/provider connectivity;
- bounded shadow multi-cycle and Publication Port qualification;
- restart/recovery/idempotency/rate-limit/failure-injection/rollback rehearsal.

All remain non-authoritative.

## 14. Ordered readiness ladder R0–R8

| Phase | Required state | Exit gate |
|---|---|---|
| R0 — MASTER SPEC | This versioned authority + Research program reconciliation | master spec/repository navigation PASS; no activation |
| R1 — P0 PARITY SOURCE IMPLEMENTATION | All current GitHub information preserved/promoted by D8 | all P0 gaps closed; current GitHub information set subset proof |
| R2 — P1 COMPACT EXPANSION SOURCE IMPLEMENTATION | Approved/reverified compact high-value families | official-doc/rate-budget evidence + source coverage; rejected candidates explicitly classified |
| R3 — LOCAL / SOURCE CONVERGENCE | deterministic complete source | targeted tests, full D8 tests, deep-history regressions, validators, compile, determinism, identity/provenance PASS; no silent substitution/synthetic fill |
| R4 — HOSTED QUALIFICATION | repository-native exact-SHA qualification | hosted CI exact SHA PASS; local-only evidence insufficient |
| R5 — CONTAINER / DISPOSABLE RUNTIME | production-like process/image semantics | startup/shutdown/state/restart/network configuration tests PASS without authority change |
| R6 — REAL VPS_SHADOW FULL-MATRIX | real providers/network and production-like publication seam | fresh server readback first; multiple natural M5 slots; M5/hourly/daily/other cadence boundaries; complete capability/provider/publication/recovery/rate-limit matrix PASS |
| R7 — SHADOW SOAK / CONTINUITY | bounded preproduction continuity | duration chosen from actual risk at implementation time; no unresolved loss/duplicates/SPOOL/rate/memory/state/publication/provider-drift defects |
| R8 — FINAL CUTOVER AUTHORIZATION | separate owner decision | only after R0–R7 PASS; atomic temporal cutover task |

R6 must prove at least:

- all target providers reachable and all production-required capabilities collectable;
- no hidden `NOT_DUE` defects across due-boundary classes;
- expected observations complete; duplicates=0;
- provider timestamps and `known_at` truthful;
- checkpoint-v2 complete;
- SPOOL durable;
- PublicationBatch deterministic;
- canonical WARM publication/readback/control-plane/resolver/reader/ACK/PENDING→FORWARDED PASS;
- restart recovery, same-slot retry, lease/ownership recovery PASS;
- rate-limit compliance and bounded runtime-state growth;
- provider revision evidence preserved;
- no direct-agent provider bypass.

Higher-TF cadence need not wait literal weeks when exact latest-closed provider observations plus cadence logic can prove the boundary. Natural M5 slots and relevant hourly/daily boundaries still require real execution evidence.

## 15. No partial production launch

```text
BUILD_AND_TEST_THE_COMPLETE_COMPACT_CONTOUR_FIRST=true
PRODUCTION_LAUNCH_ONLY_AFTER_COMPLETE_READINESS=true
PARTIAL_PRODUCTION_LAUNCH=FORBIDDEN_BY_DEFAULT
```

Do not activate an easy subset while architecture-critical parity/compact responsibilities are knowingly unfinished if this creates temporary dual authority, lost information or ad-hoc route exceptions. Any exception requires a separate owner-approved architecture decision; an executor may not infer one.

## 16. Atomic future production cutover

Future authority transition must define one explicit temporal boundary:

```text
CUTOVER_EFFECTIVE_AT=T
```

For overlapping provider series:

```text
provider_timestamp < T  → LEGACY_GITHUB_ACQUISITION
provider_timestamp >= T → D8_VPS_ACQUISITION
```

A cutover plan must bind exact source revisions, capability set, provider set, scheduler state, publication state and rollback point. Overlap at T must be explicitly resolved so one semantic observation interval has one authority.

Target state after successful transition:

```text
D8_VPS_ACTIVE=true
BINANCE_SPOT_VPS_ACTIVE=true
KRAKEN_SPOT_VPS_ACTIVE=true
BINANCE_USDM_VPS_ACTIVE=true
KRAKEN_FUTURES_VPS_ACTIVE=true
DERIBIT_PERPETUAL_VPS_ACTIVE=true
DERIBIT_OPTIONS_VPS_ACTIVE=true
LIQUIDITY_VPS_ACTIVE=true
PRODUCTION_WARM_FORWARDER_DEPLOYED=true
CONTINUOUS_D8_TO_D9_WARM=true
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
```

These are target states only. They are not current states and are not authorized by this document.

Legacy overlapping GitHub acquisition is disabled only after authoritative cutover proof. Non-acquisition workflow duties remain or are migrated explicitly according to §8.

## 17. Temporal rollback contract

A future rollback uses a new boundary:

```text
ROLLBACK_EFFECTIVE_AT=R
```

Observations successfully canonical-ACKed from D8 before R remain canonical. Rollback must not:

- delete accepted D8 WARM;
- rewrite accepted observation values;
- reacquire already ACKed identities merely to impersonate legacy provenance;
- erase D8 provenance;
- pretend a successful publication never occurred.

If legacy acquisition resumes, it becomes authority only for timestamps at/after R according to the explicit rollback transition contract. The interval split must preserve exactly one acquisition authority per semantic observation interval.

## 18. D8/WARM production readiness is not monthly D9 COLD eligibility

The production readiness graph has two distinct axes:

```text
D8 acquisition + continuous D9 WARM production readiness
!=
D9 WARM→COLD completed-partition lifecycle
```

The `COMPLETED_MONTH_ONLY` eligibility gate remains a prerequisite for a real D9 COLD generation/activation. It is **not** a prerequisite for D8 + continuous WARM production once the complete R0–R7 readiness ladder passes.

```text
D8_WARM_PRODUCTION_BLOCKED_ON_MONTHLY_COLD=NO
D9_COLD_REMAINS_SEPARATE_LIFECYCLE_STAGE=YES
```

This document still authorizes neither D8/WARM production nor D9 COLD activation.

## 19. Successor task graph

Ordered roadmap minimum:

| Order | Task | Purpose |
|---:|---|---|
| 1 | `ETH-D8-PRODUCTION-CAPABILITY-PARITY-CLOSURE-V1` | R1: close P0 exact GitHub→D8 information parity |
| 2 | `ETH-MARKET-DATA-COMPACT-HIGH-VALUE-EXPANSION-V1` | R2: official-doc/rate-budget-qualified P1 compact evidence |
| 3 | `ETH-MARKET-DATA-HIGH-CARDINALITY-WARM-BACKEND-DECISION-V1` | Separate P2 backend decision; not prerequisite for compact source unless approved P1 crosses cardinality boundary |
| 4 | `ETH-TECHNICAL-INDICATORS-DOMAIN-V1` | Separate Research-domain indicator implementation/reconciliation; not Data Bridge acquisition logic |
| 5 | `ETH-D8-FULL-MATRIX-LOCAL-HOSTED-QUALIFICATION-V1` | R3–R4 qualification |
| 6 | `ETH-D8-VPS-SHADOW-FULL-MATRIX-QUALIFICATION-V1` | R5–R6 container + real shadow matrix |
| 7 | `ETH-D8-VPS-SHADOW-PREPRODUCTION-SOAK-V1` | R7 bounded continuity/soak |
| 8 | `ETH-D8-PRODUCTION-AUTHORITY-CUTOVER-V1` | R8 owner-authorized atomic cutover only |

Dependencies may be split further by semantic owner, but no listed stage may silently disappear.

## 20. Provider/capability traceability matrix

Status values describe current source contour at this specification version. `PARTIAL` means some evidence exists but P0 canonical parity is incomplete.

| PROVIDER | CAPABILITY | SOURCE_API_FAMILY | CURRENT_GITHUB_STATUS | CURRENT_D8_STATUS | P0_PARITY_REQUIRED | P1_EXPANSION | CADENCE | DATA_CLASS | LIFECYCLE_CLASS | FINALITY | REVISION_POLICY | CURRENT_STORAGE | TARGET_STORAGE_SEMANTICS | HIGH_CARDINALITY | PRODUCTION_REQUIRED | QUALIFICATION_REQUIRED | CUTOVER_OVERLAP | NOTES |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| binance-spot | rich OHLCV 5m | spot klines | YES | PARTIAL | YES/P0-01 | P1-11..15 | 5m | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | IMMUTABLE_NATIVE | Git WARM/archive | same series identity behind WARM adapter | NO | YES | R1,R3-R7 | YES | preserve quote/trades/taker-buy/close-time |
| binance-spot | native 15m/1h/4h/1d/1w | spot klines | YES | NO | YES/P0-02 | NO | native TF | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | IMMUTABLE_NATIVE | Git WARM/history | provider-native WARM, derived TF separate | NO | YES | R1,R3-R7 | YES | native authority must survive |
| kraken-spot | rich OHLCV 5m incl VWAP/trades | public OHLC | YES | PARTIAL | YES/P0-03 | P1-23 book separate | 5m | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | PROVIDER_LIMITED | Git WARM/archive | same semantic series behind WARM adapter | NO | YES | R1,R3-R7 | YES | retention-limited evidence |
| kraken-spot | native 15m/1h/4h/1d/1w | public OHLC | YES | NO | YES/P0-04 | NO | native TF | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | PROVIDER_LIMITED | Git WARM/history | provider-native WARM | NO | YES | R1,R3-R7 | YES | not replaceable by derived-only |
| binance-usdm | perp OHLCV 5m rich | futures klines | NO_CURRENT_GITHUB_NETWORK / legacy archive preserved | YES | PRESERVE | P1-04,09 | 5m | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | FORWARD_ONLY_TARGET | D8 shadow staging/spool candidate | canonical WARM via PublicationBatch | NO | YES | R1-R7 | YES_AFTER_T | GitHub policy disabled; VPS target required |
| binance-usdm | native perp 1h/4h/1d | futures klines | NO_CURRENT_GITHUB_NETWORK | YES | PRESERVE | NO | native TF | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | FORWARD_ONLY_TARGET | D8 shadow staging/spool candidate | canonical WARM | NO | YES | R1-R7 | YES_AFTER_T | retain provider-native TF |
| binance-usdm | mark/index/premium/current funding/OI | premiumIndex/openInterest | NO_CURRENT_GITHUB_NETWORK | YES | PRESERVE | P1-05..08 | 5m sampled | NORMALIZED_FACT | SAMPLED_SCHEDULE | OBSERVED_STATE | POINT_IN_TIME | D8 shadow state | canonical WARM sampled | NO | YES | R1-R7 | YES_AFTER_T | current composite already promoted |
| binance-usdm | OI history 5m + notional | openInterestHist | LEGACY_FETCH_PATH_WHEN_ENABLED | NO | YES/P0-05 | NO | 5m | PROVIDER_EVIDENCE | FIXED_GRID | PROVIDER_NATIVE | PROVIDER_HISTORY | temporary acquisition archive | canonical WARM | NO | YES | R1,R3-R7 | YES_AFTER_T | no staging-only loss |
| binance-usdm | funding history | fundingRate | LEGACY_FETCH_PATH_WHEN_ENABLED | NO | YES/P0-06 | NO | provider timestamps | PROVIDER_EVIDENCE | FIXED_GRID_OR_SAMPLED_DECLARED | PROVIDER_NATIVE | PROVIDER_HISTORY | temporary acquisition archive | canonical WARM | NO | YES | R1,R3-R7 | YES_AFTER_T | current + history distinct |
| binance-usdm | depth snapshot | futures depth | NO_CURRENT_GITHUB_NETWORK | YES | PRESERVE | P1-10 | 5m sampled | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | D8 shadow state | canonical WARM sampled / P2 if cardinality expands | CURRENT_COMPACT_NO | YES | R1-R7 | YES_AFTER_T | bounded depth currently 100 |
| kraken-futures | 13 analytics metric families full rows | charts analytics | YES | PARTIAL | YES/P0-07 | P1-16..22 | 300s provider rows / hourly acquisition | PROVIDER_EVIDENCE | FIXED_GRID_OR_SEMANTIC_CLASS | PROVIDER_NATIVE | DECLARED_PER_METRIC | Git WARM/archive | every eligible row canonical WARM | NO | YES | R1-R7 | YES | D8 latest-only is insufficient |
| kraken-futures | revision evidence | charts analytics overlap | YES | NO | YES/P0-08 | NO | overlap observer | PROVIDER_EVIDENCE | REVISION_EVIDENCE | PIT | PROVIDER_REVISABLE_SNAPSHOT | Git revisions | backend-independent revision store/refs | NO | YES | R1-R7 | YES | preserve earlier-known values |
| deribit-perpetual | current ticker snapshot | public ticker | YES | YES | PRESERVE | P1-27..29 related | 5m | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | Git current/sampled + D8 state | canonical WARM sampled | NO | YES | R1-R7 | YES | ETH+BTC current |
| deribit-perpetual | funding H1 | funding history | YES | NO | YES/P0-09 | NO | 1h | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | FORWARD_CONTINUATION | Git WARM | canonical WARM | NO | YES | R1,R3-R7 | YES | durable legacy history |
| deribit-perpetual | OHLCV H1 | tradingview chart data | YES | NO | YES/P0-10 | NO | 1h | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | FORWARD_CONTINUATION | Git WARM candidate | canonical WARM | NO | YES | R1,R3-R7 | YES | durable legacy history |
| deribit-options | full ETH option surface | instruments + book summaries | YES | YES | PRESERVE | P1-24,30 | hourly sampled | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | Git snapshots + D8 spool candidate | canonical WARM sampled / P2 if expanded | MEDIUM | YES | R1-R7 | YES | full chain compact snapshot |
| deribit-options | selected ATM/25d Greeks | ticker selections | YES | YES_IN_SURFACE_PAYLOAD | PRESERVE | P1-30 | hourly sampled | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | Git option snapshot | canonical WARM with selection provenance | NO | YES | R1-R7 | YES | selected evidence used by analytics |
| deribit-options | ETH DVOL H1 full rows | volatility index data | YES | PARTIAL | YES/P0-11 | P1-25 BTC_DVOL | 1h | PROVIDER_EVIDENCE | FIXED_GRID | FINALIZED | PROVIDER_HISTORY | Git option archive | canonical WARM all eligible rows | NO | YES | R1-R7 | YES | D8 latest-only today |
| deribit/liquidity | selected option books | public get_order_book | YES | NO | YES/P0-12 | P1-31..36 flow separate | hourly sampled | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | Git liquidity snapshots | canonical WARM sampled / P2 if HF | MEDIUM | YES | R1-R7 | YES | D8 empty selection bug/gap |
| binance-spot/liquidity | bounded spot depth | spot depth | YES | YES_VIA_MULTI_PROVIDER | PRESERVE | P1-10/23 analogues where relevant | 5m/hourly depending route | PROVIDER_EVIDENCE | SAMPLED_SCHEDULE | OBSERVED_STATE | FORWARD_ONLY | Git liquidity + D8 | canonical WARM sampled | MEDIUM | YES | R1-R7 | YES | raw levels required for reproducibility |
| data-bridge-derived | deterministic market-derived metrics | canonical L0/L1 inputs | YES_PARTIAL | PARTIAL | FORMULA_IDENTITY | all approved P1 aggregates | declared | MARKET_DERIVED | DERIVED_SERIES | INPUT_BOUND | VERSIONED_FORMULA | Git analytics/current profile | rebuildable/materialized behind semantic route | DEPENDS | AS_APPROVED | R3-R7 | NO_SOURCE_AUTHORITY | never aliases provider-native identity |

Technical indicator outputs are intentionally excluded from this Data Bridge traceability matrix.

## 21. Qualification invariants

Every production-required capability must prove:

```text
NO_DUPLICATE_IDENTITIES=true
NO_SILENT_PROVIDER_SUBSTITUTION=true
NO_SYNTHETIC_FILL=true
PROVIDER_TIMESTAMP_TRUTHFUL=true
KNOWN_AT_TRUTHFUL=true
FINALITY_TRUTHFUL=true
PROVENANCE_COMPLETE=true
DETERMINISTIC_REPLAY=true
CANONICAL_ACK_REQUIRED=true
```

Repository-hosted qualification must bind exact source SHA. Local-only PASS cannot authorize R8. Real VPS_SHADOW qualification always starts with fresh live server readback and never treats repository status snapshots as continuous server truth.

## 22. Acceptance checklist for this specification

```text
MASTER_SPEC_CREATED_OR_RECONCILED=PASS
CURRENT_GITHUB_TO_D8_PARITY_MATRIX=PASS
P0_GAPS_CAPTURED=PASS
P1_EXPANSION_CAPTURED=PASS
HIGH_CARDINALITY_BOUNDARY_CAPTURED=PASS
TECHNICAL_INDICATOR_BOUNDARY_CAPTURED=PASS
HORIZONTAL_SCALING_INVARIANTS_CAPTURED=PASS
GITHUB_TO_FUTURE_DB_PORTABILITY_CAPTURED=PASS
LOCAL_HOSTED_SERVER_READINESS_LADDER_CAPTURED=PASS
NO_PARTIAL_PRODUCTION_LAUNCH_POLICY_CAPTURED=PASS
ATOMIC_CUTOVER_CONTRACT_CAPTURED=PASS
ROLLBACK_CONTRACT_CAPTURED=PASS
BINANCE_USDM_SCOPE_SEMANTICS_CAPTURED=PASS
D8_WARM_VS_D9_COLD_STAGE_SEPARATION_CAPTURED=PASS
SUCCESSOR_TASK_GRAPH_CAPTURED=PASS
NO_EXECUTABLE_SOURCE_MUTATION=REQUIRED
NO_RUNTIME_MUTATION=REQUIRED
NO_SERVER_MUTATION=REQUIRED
NO_PROVIDER_AUTHORITY_CHANGE=REQUIRED
```

## 23. Recovery route for future executors

```text
AGENTS.md
→ this master specification
→ bridge-contract.json + D8/D9 machine contracts
→ current Research docs/programs/market-data-foundation.md
→ exact successor task
→ fresh main + live server readback when physical work is authorized
```

Do not reconstruct this production-readiness architecture from chat history. Any later change to the readiness ladder, ownership boundary, parity set, cutover semantics or permanent high-cardinality backend requires a versioned repository decision.

## 24. R0 exhaustive provider market-data surface hardening

This section is the current R0 completeness authority inside this same master specification. It **amends**, and where counts or classification differ **supersedes**, the parent-task snapshot in §§9, 10 and 20. The 12 confirmed P0 gaps remain unchanged; the old `P1_EXPANSION_FAMILY_COUNT=36` was a known-candidate snapshot, not exhaustive-surface proof.

```text
R0_EXHAUSTIVE_AUDIT_SECTION_AUTHORITY=CURRENT
EVERY_RELEVANT_PROVIDER_MARKET_DATA_CAPABILITY_MUST_HAVE_EXPLICIT_DISPOSITION=true
UNKNOWN_OR_UNCLASSIFIED_PROVIDER_CAPABILITY=FAIL_CLOSED
PROVIDER_NATIVE_INFORMATION_LOSS_WITHOUT_EXPLICIT_DISPOSITION=FORBIDDEN
PROVIDER_API_SURFACE_SNAPSHOT_AS_OF_UTC=2026-08-22T21:16:21Z
P1_REGISTRY_IS_NOT_FIXED_TO_36=true
P2_REGISTRY_IS_NOT_FIXED_TO_CURRENT_LIST=true
R0_EXHAUSTIVE_PROVIDER_SURFACE_AUDIT_REQUIRED_BEFORE_R1_COMPLETE=true
PROVIDER_API_CHANGE_REAUDIT_REQUIRED_BEFORE_R8=true
UNCLASSIFIED_RELEVANT_PROVIDER_CAPABILITY_COUNT=0
```

### 24.1 Official documentation evidence set

Only provider-owned current documentation was used for this audit. Repository source remains evidence for current implementation status, not proof of provider API completeness.

```text
BINANCE_DOCUMENTATION_SOURCE_SET=
  https://developers.binance.com/en/docs/catalog
  https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market
  https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
  https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/market-data
  https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/market-data
BINANCE_DOCUMENTATION_REVIEW_STATUS=PASS

KRAKEN_DOCUMENTATION_SOURCE_SET=
  https://docs.kraken.com/llms.txt
  https://docs.kraken.com/api-reference/market-data/get-order-book
  https://docs.kraken.com/api-reference/market-data/query-l3-order-book
  https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/level3
  https://docs.kraken.com/exchange/guides/futures/introduction
  https://docs.kraken.com/exchange/api-reference/futures-websocket/ticker
  https://docs.kraken.com/exchange/api-reference/futures-websocket/trade
  https://docs.kraken.com/exchange/api-reference/futures-websocket/book
  https://futures.kraken.com/api/charts/v1/analytics/liquidity-pool
KRAKEN_DOCUMENTATION_REVIEW_STATUS=PASS

DERIBIT_DOCUMENTATION_SOURCE_SET=
  https://docs.deribit.com/
  https://docs.deribit.com/llms.txt
  https://docs.deribit.com/articles/options-data-collection-best-practices
  https://docs.deribit.com/articles/block-trading-api
  https://docs.deribit.com/articles/block-rfq-api-walkthrough
  https://docs.deribit.com/articles/accessing-historical-trades-orders
DERIBIT_DOCUMENTATION_REVIEW_STATUS=PASS
```

Binance’s current catalog explicitly exposes separate Spot, USDⓈ-M Futures, COIN-M Futures and Options REST/stream product surfaces. The audit therefore treats COIN-M and Binance Options as first-class product families requiring disposition, not as absent because current repository source does not collect them.

### 24.2 Disposition, auth, cardinality, recoverability and cadence vocabulary

Every row in the exhaustive matrix below has exactly one planning disposition:

```text
P0_PARITY
P1_COMPACT
P2_HIGH_CARDINALITY
DERIVE_FROM_CANONICAL_SOURCE
PROVIDER_METADATA
REDUNDANT_DO_NOT_STORE
AUTH_REQUIRED_REVIEW
NOT_ANALYTICALLY_USEFUL
UNAVAILABLE_BY_PROVIDER
SUPERSEDED
OUT_OF_PROJECT_SCOPE
```

Authentication scope:

```text
PUBLIC_NO_AUTH
PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT
AUTHENTICATED_MARKET_DATA
ACCOUNT_PRIVATE
TRADING_PRIVATE
```

Cardinality:

```text
LOW
MEDIUM
HIGH
VERY_HIGH
```

Recoverability:

```text
DEEP_BACKFILL_AVAILABLE
BOUNDED_BACKFILL
SHORT_PROVIDER_RETENTION
FORWARD_ONLY
UNKNOWN_REVERIFY
```

Cadence:

```text
M5
M15
H1
H4
D1
W1
EVENT_STREAM
METADATA_LOW_FREQUENCY
EXPIRY_DRIVEN
OTHER_DECLARED
```

`rate/budget` values below are planning classes only. Exact current request weights, subscription limits and shared provider budget MUST be re-read and proven in R2 before implementation; the exhaustive inventory does not mean “call everything every five minutes.”

### 24.3 Provider metadata and data-driven discovery plane

Provider metadata is an explicit L0 plane, not incidental setup code:

```text
PROVIDER_PRODUCT_DISCOVERY
→ VERSIONED_INSTRUMENT_METADATA
→ SCOPE / ADMISSION POLICY
→ CAPABILITY WORK UNITS
```

Required target invariants:

```text
PROVIDER_DISCOVERY_IS_DATA_DRIVEN=true
INSTRUMENT_ADMISSION_IS_POLICY_DRIVEN=true
HARD_CODED_SYMBOL_LIST_IS_NOT_TARGET_ARCHITECTURE=true
ADDING_NEW_INSTRUMENT_MUST_NOT_REQUIRE_RUNTIME_REDESIGN=true
NEW_SYMBOL_REQUIRES_NEW_AUTHORITY=false
NEW_SYMBOL_REQUIRES_NEW_RESOLVER=false
NEW_SYMBOL_REQUIRES_NEW_STORAGE_PROTOCOL=false
```

Metadata families include exchange/instrument catalogs, base/quote/underlying, contract type, expiry/delivery, tick/lot size, precision, trading state, settlement semantics and rate-limit metadata. Current ETH/BTC-heavy scope may remain the initial admission policy; adding SOL/XRP/new expiry/new option underlying/new venue must be data/config/admission expansion, not architecture replacement.

### 24.4 Authentication corrections

Kraken Spot L3 is not `PUBLIC_NO_AUTH`. Current official REST `Level3` requires API key/signature and permission `Orders and trades - Query open orders & trades`; current WebSocket `level3` requires an API token. Therefore:

```text
KRAKEN_L3_AUTH_SCOPE=AUTHENTICATED_MARKET_DATA
KRAKEN_L3_DISPOSITION=AUTH_REQUIRED_REVIEW
P1_23_CANDIDATE_IDENTITY=PRESERVED
P1_23_CURRENT_DISPOSITION=AUTH_REQUIRED_REVIEW
```

Unauthenticated L2/grouped/PreTrade does not provide a proven per-level individual-order count source. `ORDER_COUNT_IMBALANCE`, `MEAN_ORDER_SIZE_BY_LEVEL` and `WALL_FRAGMENTATION` may be derived only after an approved canonical individual-order source exists.

Binance Spot `Historical Block Trades (MARKET_DATA)` requires `X-MBX-APIKEY`; it is therefore `PUBLIC_ENDPOINT_WITH_KEY_REQUIREMENT → AUTH_REQUIRED_REVIEW`. Futures old-trade lookup families carrying `MARKET_DATA` credential requirements receive the same review boundary. Account-private and trading-private data is not imported merely because the provider exposes an API.

Deribit public executed block/RFQ trade evidence is distinct from private execution/request/quote state: public trade evidence may be collected, while private RFQ/block workflow state remains `OUT_OF_PROJECT_SCOPE` unless a separate security/credential authority changes that scope.

### 24.5 Field-level preservation and identity rules

```text
PROVIDER_NATIVE_INFORMATION_LOSS_WITHOUT_EXPLICIT_DISPOSITION=FORBIDDEN
PROVIDER_NATIVE_BASIS_IDENTITY_DISTINCT=true
PROVIDER_NATIVE_CVD_IDENTITY_DISTINCT=true
PROVIDER_NATIVE_VOLATILITY_IDENTITY_DISTINCT=true
PROVIDER_NATIVE_POSITIONING_IDENTITY_DISTINCT=true
PROVIDER_NATIVE_LIQUIDITY_ANALYTICS_IDENTITY_DISTINCT=true
```

Provider-native fields that are analytically meaningful must be preserved, normalized, explicitly derived/redundant, or explicitly rejected. They may not disappear merely because a compact D8 envelope omitted them.

Known examples remain binding: Binance quote volume/trade count/taker-buy volumes; Binance OI-history `sumOpenInterestValue`; Kraken VWAP/trade count/revision evidence; provider-native basis; option trade IV where supplied; combo/block/RFQ multi-leg identity.

Provider-native basis is not an alias for local mark-minus-index basis. Provider-native CVD is not an alias for locally derived CVD. Provider-native historical/realized volatility is not an alias for a Data Bridge-derived realized-vol series. Provider-native positioning/liquidity analytics remain distinct from downstream mechanical states.

### 24.6 Derived L2 registry hardening

The existing L2 families remain. Explicitly add, when canonical source evidence supports them:

```text
SPOT_CVD_VS_PERP_CVD
ORDER_COUNT_IMBALANCE
MEAN_ORDER_SIZE_BY_LEVEL
WALL_FRAGMENTATION
```

All require versioned formula, exact inputs and provenance. `ORDER_COUNT_IMBALANCE`, `MEAN_ORDER_SIZE_BY_LEVEL` and `WALL_FRAGMENTATION` require an approved individual-order source; Kraken authenticated L3 is not silently assumed available.

Technical Indicators remain outside Data Bridge L2. RSI/MACD/ATR/SMA/EMA/ADX/Stochastic/CCI/Bollinger/Ichimoku/MFI/OBV and comparable methods remain Research `TECHNICAL_INDICATORS` even though deterministic.

### 24.7 Exhaustive audited surface matrix

Legend for compact fields:

- `auth`: `PUB` = `PUBLIC_NO_AUTH`; `KEY` = public endpoint with key; `AUTH` = authenticated market data; `PRIVATE` = account/trading-private.
- `hist`: recoverability class; exact provider retention is not invented where official docs do not state it.
- `rate`: current endpoint weights/subscription constraints must be reverified in R2; documented hard bounds are kept where materially relevant.
- `GH/D8`: current repository/source support, not future target.
- `storage`: current physical role only; target remains backend-neutral WARM/P2 adapter semantics.
- `qual`: minimum successor qualification; every production-required P1 still needs official-doc/rate-budget proof plus R3–R7.

| ID | Provider / product | Capability family; endpoint/channel | Transport / auth | Instrument scope / discovery | Native fields / timestamp-finality-revision | History / pagination / recoverability | Rate / cadence / cardinality | GH / D8 / storage | Target lifecycle / analytical value / production | Disposition / reason | Qual / cutover | Doc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BS-01 | Binance Spot | admitted native OHLCV 5m/15m/1h/4h/1d/1w; `/api/v3/klines` | REST PUB | ETHUSDT/BTCUSDT/ETHBTC initially; `exchangeInfo` discovery | open/high/low/close/base+quote volume/close time/trade count/taker-buy base+quote; open/close timestamps; closed bars | DB range query; bounded pages; `BOUNDED_BACKFILL` | weight per docs; M5/native TF; LOW | GH YES rich/native; D8 PARTIAL M5-only/lossy; Git WARM | FIXED_GRID FINALIZED; canonical source; required | `P0_PARITY` P0-01/P0-02 | R1,R3-R7; overlap YES | BIN-SPOT-MARKET |
| BS-02 | Binance Spot | other provider-native kline/UIKline intervals | REST PUB | discovered symbols | same kline fields | DB; `BOUNDED_BACKFILL` | native intervals; MEDIUM | GH/D8 NO | no current admitted semantic series | `REDUNDANT_DO_NOT_STORE`; current compact timeframe policy, future admission requires explicit policy | re-audit if admitted | BIN-SPOT-MARKET |
| BS-03 | Binance Spot | aggTrades/recent/historical trades + trade/aggTrade streams | REST/WS PUB | discovered symbols | trade ids, price, qty, quote/taker/maker semantics, provider time | DB/recent + stream; retention varies; `BOUNDED_BACKFILL`/`FORWARD_ONLY` stream | EVENT_STREAM; HIGH | GH/D8 no canonical raw tape | EVENT evidence; high analytical value | `P2_HIGH_CARDINALITY`; raw tape not forced into Git | P2 backend + rate/replay | BIN-SPOT-MARKET/CATALOG |
| BS-04 | Binance Spot | compact trade-flow/CVD/large-trade/VWAP aggregates P1-11..15 | derived from canonical trades | admitted symbols | versioned aggregates + source range | rebuildable if raw source retained | M5; LOW | not complete | DERIVED_SERIES; flow evidence | `P1_COMPACT` | R2-R7; cutover with source | master L2 |
| BS-05 | Binance Spot | historical block trades `/api/v3/historicalBlockTrades` | REST KEY | symbols | block trade id, price, qty, quoteQty, time, maker side | DB, id pagination, max 1000; `BOUNDED_BACKFILL` | low/medium; MEDIUM | no | institutional trade evidence | `AUTH_REQUIRED_REVIEW`; API key required | credential/security review | BIN-SPOT-MARKET |
| BS-06 | Binance Spot | bounded L2 order-book snapshots | REST PUB | symbols | bid/ask price+qty, update identity | snapshot; `FORWARD_ONLY` for historical state | M5/OTHER; MEDIUM | GH liquidity YES; D8 via liquidity/depth | SAMPLED_SCHEDULE; reproducible liquidity | `P1_COMPACT`/preserve existing compact source | R2-R7 | BIN-SPOT-MARKET |
| BS-07 | Binance Spot | incremental/diff depth streams | WS PUB | symbols | level deltas/update ids/event time | stream only; `FORWARD_ONLY` | EVENT_STREAM; VERY_HIGH | no permanent history | raw microstructure | `P2_HIGH_CARDINALITY` | P2 backend | BIN-CATALOG |
| BS-08 | Binance Spot | avgPrice + 24h/rolling/trading-day/price/book ticker families | REST/WS PUB | symbols | provider summary statistics/current quotes | current/window summaries | M5/OTHER; LOW | partial current facts already derivable | convenience summaries | `REDUNDANT_DO_NOT_STORE`; canonical trades/candles/book are preferred source | compatibility-only if used | BIN-SPOT-MARKET |
| BS-09 | Binance Spot | reference price + calculation | REST PUB | symbols | provider reference value/calculation metadata/time | provider current/reference; `UNKNOWN_REVERIFY` | M5/OTHER; LOW | absent | independent reference evidence | `P1_COMPACT` P1-43 | R2-R7 | BIN-SPOT-MARKET |
| BS-10 | Binance Spot | exchangeInfo/filters/status/precision/rate-limit metadata | REST PUB | all products | base/quote/status/tick/lot/precision/filter/rate metadata | current metadata; version snapshots forward | METADATA_LOW_FREQUENCY; LOW | hard-coded source tuples today | L0 discovery/admission | `PROVIDER_METADATA` | metadata versioning/changes | BIN-CATALOG |
| BU-01 | Binance USD-M | rich perp 5m + native 1h/4h/1d klines | REST PUB | ETHUSDT/BTCUSDT current; exchangeInfo target | rich kline fields, close time, quote/trade/taker fields | API history; `BOUNDED_BACKFILL` | M5/H1/H4/D1; LOW | GitHub network disabled; D8 supports source | FIXED_GRID source; required VPS target | `P0_PARITY` preserve existing D8 target semantics | R1-R7; overlap after T | BIN-USDM |
| BU-02 | Binance USD-M | OI history `/futures/data/openInterestHist` | REST PUB | symbols | timestamp, `sumOpenInterest`, `sumOpenInterestValue` | official recent-window API; latest-30d families documented; `BOUNDED_BACKFILL` | M5+; LOW | legacy fetch writes staging/archive; D8 loses rows | FIXED_GRID; leverage evidence | `P0_PARITY` P0-05 | R1,R3-R7 | BIN-USDM |
| BU-03 | Binance USD-M | funding history `/fapi/v1/fundingRate` | REST PUB | symbols | fundingRate/time, markPrice, rateType where supplied | start/end, max 1000; `BOUNDED_BACKFILL` | funding schedule; LOW | legacy fetch writes; D8 current-only | provider-native funding history | `P0_PARITY` P0-06 | R1,R3-R7 | BIN-USDM |
| BU-04 | Binance USD-M | current mark/index/premium/funding/OI composite | REST PUB | symbols | mark/index/last funding/current OI/provider time | current; `FORWARD_ONLY` snapshot | M5; LOW | D8 YES | SAMPLED_SCHEDULE current evidence | `P0_PARITY` preserve | R1-R7 | BIN-USDM |
| BU-05 | Binance USD-M | global/top-trader long-short ratios | REST PUB | symbols | ratios/count/long/short accounts or positions/time | latest-30d family; `BOUNDED_BACKFILL` | M5-H1; LOW | absent D8 | positioning evidence | `P1_COMPACT` P1-01..03 | R2-R7 | BIN-USDM |
| BU-06 | Binance USD-M | taker buy/sell volume | REST PUB | symbols | buy/sell volumes/time | latest-30d family; `BOUNDED_BACKFILL` | M5-H1; LOW | absent | flow evidence | `P1_COMPACT` P1-04 | R2-R7 | BIN-USDM |
| BU-07 | Binance USD-M | index/mark/premium-index klines | REST PUB | symbols/pairs | provider-native OHLC reference series | range API; `BOUNDED_BACKFILL` | H1/declared; LOW | partly source support | reference/funding basis evidence | `P1_COMPACT` P1-05..07 | R2-R7 | BIN-USDM |
| BU-08 | Binance USD-M | funding config/cap/floor/interval | REST PUB | contracts | funding interval/cap/floor/config metadata | current metadata; `FORWARD_ONLY` snapshots | METADATA_LOW_FREQUENCY; LOW | absent | funding semantics | `P1_COMPACT` P1-08 | R2 + metadata change proof | BIN-USDM |
| BU-09 | Binance USD-M | compact liquidation impulse | derived from force-order evidence | symbols | classified liquidation qty/notional/side/time | depends on raw stream | M5; LOW | absent | deleveraging evidence | `P1_COMPACT` P1-09 | R2-R7 after source | master L2 |
| BU-10 | Binance USD-M | bounded depth | REST PUB | symbols | bid/ask price+qty | snapshot forward | M5; MEDIUM | D8 YES limit 100 | liquidity evidence | `P1_COMPACT` P1-10 preserve/extend | R2-R7 | BIN-USDM |
| BU-11 | Binance USD-M | provider-native basis `/futures/data/basis` | REST PUB | pair+contract type | indexPrice,futuresPrice,basis,basisRate,annualizedBasisRate,pair,timestamp | period/range API; `BOUNDED_BACKFILL` | H1/declared; LOW | absent | provider-native curve/basis evidence | `P1_COMPACT` P1-37; distinct from derived mark-index basis | R2-R7 | BIN-USDM |
| BU-12 | Binance USD-M | RPI order book `/fapi/v1/rpiDepth` | REST PUB | symbols | update/output/transaction time, bid/ask price+qty; RPI-aware semantics | snapshot; `FORWARD_ONLY` | M5/OTHER; MEDIUM | absent | alternative liquidity evidence | `P1_COMPACT` P1-38 | R2-R7 | BIN-USDM |
| BU-13 | Binance USD-M | ADL risk `/fapi/v1/symbolAdlRisk` | REST PUB | symbols/all | risk rating + updateTime | current 30m-like state; `FORWARD_ONLY` | OTHER_DECLARED; LOW | absent | systemic risk/deleveraging evidence | `P1_COMPACT` P1-39 | R2-R7 | BIN-USDM |
| BU-14 | Binance USD-M | insurance fund balance | REST PUB | symbol/all | asset/balance/update semantics | snapshots; `FORWARD_ONLY` unless endpoint history says otherwise | H1/D1; LOW | absent | risk-capacity context | `P1_COMPACT` P1-40 | R2-R7 | BIN-USDM |
| BU-15 | Binance USD-M | quarterly settlement/delivery price | REST PUB | pair | deliveryTime,deliveryPrice | historical pages; `BOUNDED_BACKFILL` | EXPIRY_DRIVEN; LOW | absent | curve/settlement evidence | `P1_COMPACT` P1-41 | R2-R7 | BIN-USDM |
| BU-16 | Binance USD-M | continuous-contract klines | REST PUB | pair+contract type | OHLCV/reference timing | API range; `BOUNDED_BACKFILL` | native TF; LOW | absent | curve continuity | `P1_COMPACT` P1-42 | R2-R7 | BIN-USDM |
| BU-17 | Binance USD-M | raw recent/aggregate/history trades + streams | REST/WS PUB or KEY for MARKET_DATA old-trade variant | symbols | trade ids/price/qty/time/maker classification | bounded DB + streams | EVENT_STREAM; HIGH | no canonical raw tape | raw execution evidence | `P2_HIGH_CARDINALITY`; key-gated old-trade variant separately auth-reviewed | P2 backend | BIN-USDM |
| BU-18 | Binance USD-M | raw force-order/liquidation event stream | WS PUB | symbols/all | force-order side/qty/price/time/status | `FORWARD_ONLY` | EVENT_STREAM; HIGH | absent | raw liquidation evidence | `P2_HIGH_CARDINALITY` | P2 backend | BIN-CATALOG |
| BU-19 | Binance USD-M | old trades MARKET_DATA credential variant | REST KEY | symbols | historical trade fields | provider DB; bounded | OTHER_DECLARED; HIGH | absent | optional backfill | `AUTH_REQUIRED_REVIEW` | credentials + P2 backend | BIN-USDM |
| BU-20 | Binance USD-M | exchangeInfo/trading schedule/composite-index/index constituents/asset-index metadata | REST PUB | all contracts/pairs | product, contract type, expiry/delivery, components/weights, precision/status/rate limits | metadata snapshots | METADATA_LOW_FREQUENCY; LOW | hard-coded admission today | discovery/reference metadata | `PROVIDER_METADATA` | metadata versioning | BIN-USDM |
| BU-21 | Binance USD-M | ticker summaries | REST/WS PUB | symbols | 24h/current ticker stats | current windows | M5/OTHER; LOW | current facts overlap | convenience | `REDUNDANT_DO_NOT_STORE` | compatibility only | BIN-USDM |
| BC-01 | Binance COIN-M | perp/delivery native OHLCV | REST PUB | initial BTC/ETH pairs/contracts via exchangeInfo | provider-native OHLCV/close/trade/volume fields | API range; `BOUNDED_BACKFILL` | M5/H1/H4/D1; LOW | GH/D8 absent | inverse-contract source evidence | `P1_COMPACT` P1-44 | R2-R7; new cutover scope | BIN-COINM |
| BC-02 | Binance COIN-M | continuous-contract klines | REST PUB | pair+contract type | continuous OHLCV | API range; `BOUNDED_BACKFILL` | native TF; LOW | absent | curve continuity | `P1_COMPACT` P1-45 | R2-R7 | BIN-COINM |
| BC-03 | Binance COIN-M | mark/index/premium current + klines | REST PUB | contracts | reference prices/premium and OHLC series | API ranges; `BOUNDED_BACKFILL` | M5-H1; LOW | absent | inverse-contract reference evidence | `P1_COMPACT` P1-46 | R2-R7 | BIN-COINM |
| BC-04 | Binance COIN-M | funding current/history/info | REST PUB | perpetuals | funding rate/time/config | start/end max 1000; `BOUNDED_BACKFILL` | funding/H1; LOW | absent | leverage-cost evidence | `P1_COMPACT` P1-47 | R2-R7 | BIN-COINM |
| BC-05 | Binance COIN-M | OI current/history + base-value semantics | REST PUB | pair+contract type | sumOpenInterest/sumOpenInterestValue/time | official latest-30d stats; `BOUNDED_BACKFILL` | M5-H1; LOW | absent | inverse leverage evidence | `P1_COMPACT` P1-48 | R2-R7 | BIN-COINM |
| BC-06 | Binance COIN-M | provider-native basis | REST PUB | pair+contract type | index/futures price,basis/rate,annualized rate,time | range API; `BOUNDED_BACKFILL` | H1; LOW | absent | cross-contract curve evidence | `P1_COMPACT` P1-49 | R2-R7 | BIN-COINM |
| BC-07 | Binance COIN-M | global/top-trader positioning ratios | REST PUB | pair | long/short ratios/time | latest-window API; `BOUNDED_BACKFILL` | M5-H1; LOW | absent | inverse positioning | `P1_COMPACT` P1-50 | R2-R7 | BIN-COINM |
| BC-08 | Binance COIN-M | taker buy/sell flow | REST PUB | pair | buy/sell volume/time | bounded provider window | M5-H1; LOW | absent | flow confirmation | `P1_COMPACT` P1-51 | R2-R7 | BIN-COINM |
| BC-09 | Binance COIN-M | bounded depth snapshots | REST PUB | contracts | bid/ask price+qty | snapshot forward | M5; MEDIUM | absent | liquidity corroboration | `P1_COMPACT` P1-52 | R2-R7 | BIN-COINM |
| BC-10 | Binance COIN-M | compact liquidation aggregates | derived from public force-order/trade classes where verified | contracts | side/qty/notional/time aggregates | forward if stream-only | M5; LOW | absent | deleveraging divergence | `P1_COMPACT` P1-53 | R2-R7 after source | BIN-COINM/master L2 |
| BC-11 | Binance COIN-M | raw trades/depth/liquidation streams | REST/WS PUB | contracts | trade/order/event fields | bounded DB + forward streams | EVENT_STREAM; HIGH/VERY_HIGH | absent | raw inverse-contract microstructure | `P2_HIGH_CARDINALITY` | P2 backend | BIN-COINM/CATALOG |
| BC-12 | Binance COIN-M | old trades MARKET_DATA credential variant | REST KEY | contracts | historical trade fields | provider DB | OTHER_DECLARED; HIGH | absent | optional raw backfill | `AUTH_REQUIRED_REVIEW` | credentials + P2 | BIN-COINM |
| BC-13 | Binance COIN-M | exchangeInfo/contract lifecycle/expiry/index constituents/rate metadata | REST PUB | all | contract type, expiry/delivery, precision/status/index composition | metadata snapshots | METADATA_LOW_FREQUENCY; LOW | absent | discovery/admission | `PROVIDER_METADATA` | metadata versioning | BIN-COINM |
| BC-14 | Binance COIN-M | ticker summaries | REST/WS PUB | contracts | current/24h stats | current windows | OTHER_DECLARED; LOW | absent | low incremental value | `REDUNDANT_DO_NOT_STORE` | none unless consumer requires | BIN-COINM |
| BO-01 | Binance Options | option contracts/chain/exchangeInfo/filters/expiry metadata | REST PUB | dynamic BTC/ETH options initially; exchangeInfo | underlying/base/quote/settle, symbol, expiry, strike, filters, precision, status, rate metadata | metadata snapshots | METADATA_LOW_FREQUENCY; LOW | absent | dynamic option discovery | `PROVIDER_METADATA` | metadata versioning | BIN-OPTIONS |
| BO-02 | Binance Options | index/reference price | REST PUB | underlying | provider reference price/time | current/history as endpoint supports; `UNKNOWN_REVERIFY` | M5; LOW | absent | independent venue reference | `P1_COMPACT` P1-54 | R2-R7 | BIN-OPTIONS |
| BO-03 | Binance Options | mark price + bid/ask/mark IV + Greeks | REST/streams PUB | option chain | markPrice,bidIV,askIV,markIV,delta/theta/gamma/vega plus provider time | snapshots/streams; `FORWARD_ONLY` unless retained | M5/OTHER; MEDIUM | absent | cross-venue option valuation | `P1_COMPACT` P1-55 | R2-R7 | BIN-OPTIONS |
| BO-04 | Binance Options | option OHLCV | REST PUB | symbols | OHLCV, close time, quote volume/trades/taker fields where returned | start/end, max 1500; `BOUNDED_BACKFILL` | M5/H1; MEDIUM | absent | venue-native option price history | `P1_COMPACT` P1-56 | R2-R7 | BIN-OPTIONS |
| BO-05 | Binance Options | OI by underlying/expiration | REST PUB | chain | symbol,sumOpenInterest,sumOpenInterestUsd,timestamp | snapshot/history endpoint semantics; `UNKNOWN_REVERIFY` | H1/EXPIRY; MEDIUM | absent | cross-venue positioning | `P1_COMPACT` P1-57 | R2-R7 | BIN-OPTIONS |
| BO-06 | Binance Options | 24h ticker/book summary | REST/streams PUB | chain | price/volume/OI/IV summary fields | window snapshot | H1; MEDIUM | absent | compact chain activity | `P1_COMPACT` P1-58 | R2-R7 | BIN-OPTIONS |
| BO-07 | Binance Options | bounded order-book snapshot | REST PUB | selected liquid options | bid/ask levels/time | snapshot; `FORWARD_ONLY` | H1/M5 selected; MEDIUM | absent | liquidity/skew execution evidence | `P1_COMPACT` P1-59 | R2-R7 | BIN-OPTIONS |
| BO-08 | Binance Options | recent block trades | REST PUB | option symbols | trade/block id, price, qty, quoteQty, side,time | recent bounded max 500; `SHORT_PROVIDER_RETENTION` | EVENT/OTHER; LOW | absent | institutional cross-venue flow | `P1_COMPACT` P1-60 | R2-R7 | BIN-OPTIONS |
| BO-09 | Binance Options | exercise/expiry-settlement evidence | REST PUB | chain | exercise/settlement identity/time/value fields | provider historical records; `BOUNDED_BACKFILL` | EXPIRY_DRIVEN; LOW | absent | expiry/settlement context | `P1_COMPACT` P1-61 | R2-R7 | BIN-OPTIONS |
| BO-10 | Binance Options | raw trade/depth streams | REST/streams PUB | chain | trade prints/level events | recent/forward; `SHORT_PROVIDER_RETENTION`/`FORWARD_ONLY` | EVENT_STREAM; HIGH | absent | raw option microstructure | `P2_HIGH_CARDINALITY` | P2 backend | BIN-OPTIONS/CATALOG |
| BO-11 | Binance Options | stream mirrors of compact REST chain state | streams PUB | chain | same semantic values at higher update cadence | forward | EVENT_STREAM; MEDIUM | absent | acquisition transport, not second identity | `DERIVE_FROM_CANONICAL_SOURCE` | exact equivalence/identity test | BIN-CATALOG |
| KS-01 | Kraken Spot | admitted native OHLC including VWAP/trade count P0-03/P0-04 | REST PUB | ETHUSD/BTCUSD initially; AssetPairs target | OHLC,VWAP,volume,trade count,provider time | provider-limited OHLC; `SHORT_PROVIDER_RETENTION` | M5/native TF; LOW | GH YES; D8 PARTIAL/lossy M5 | FIXED_GRID source; required | `P0_PARITY` | R1,R3-R7 | KRAKEN-SPOT |
| KS-02 | Kraken Spot | extra OHLC intervals outside current admitted set | REST PUB | pairs | same provider fields | provider-limited | native TF; LOW | absent | no current admitted semantic series | `REDUNDANT_DO_NOT_STORE` | future admission only | KRAKEN-SPOT |
| KS-03 | Kraken Spot | public L2 REST/WS book | REST/WS PUB | pairs | aggregated price levels+qty, timestamps/checksum/update semantics | snapshot+stream; no reconstructable old book by default | M5/stream; MEDIUM | GH liquidity current; D8 via liquidity | SAMPLED_SCHEDULE evidence | `P1_COMPACT` preserve/extend bounded snapshot | R2-R7 | KRAKEN-SPOT |
| KS-04 | Kraken Spot | grouped book + PreTrade aggregate view | REST PUB | pairs | top aggregated price levels | current snapshots | OTHER; MEDIUM | absent | duplicates L2 aggregate semantics | `REDUNDANT_DO_NOT_STORE` | no second canonical identity | KRAKEN-SPOT |
| KS-05 | Kraken Spot | public trades/PostTrade/WS trade tape | REST/WS PUB | pairs | price,qty,side/type,time/trade identifiers per route | recent provider pages + stream; `SHORT_PROVIDER_RETENTION` | EVENT_STREAM; HIGH | absent | raw tape | `P2_HIGH_CARDINALITY` | P2 backend | KRAKEN-SPOT |
| KS-06 | Kraken Spot | provider-native recent spread history | REST PUB | pairs | bid,ask,time | recent history; `SHORT_PROVIDER_RETENTION` | M5/OTHER; LOW | absent | native corroboration distinct from derived spread | `P1_COMPACT` P1-62 | R2-R7 | KRAKEN-SPOT |
| KS-07 | Kraken Spot | Level3 individual orders REST/WS | REST/WS AUTH | pairs; authenticated token/key | order_id,price,qty,timestamp per order; snapshot/delta | current/stream; `FORWARD_ONLY` unless approved retention | EVENT_STREAM; VERY_HIGH | absent | individual-order microstructure | `AUTH_REQUIRED_REVIEW`; security/credential approval required | auth architecture + P2 backend | KRAKEN-L3 |
| KS-08 | Kraken Spot | P1-23 per-level order-count evidence | derives only from approved individual-order source | pairs | order count/size distribution | depends on L3 | M5; HIGH source | absent | basis for order-count analytics | `AUTH_REQUIRED_REVIEW`; candidate ID retained but not active compact source | auth + formula proof | KRAKEN-L3 |
| KS-09 | Kraken Spot | order-count imbalance / mean order size / wall fragmentation | derived | pairs | versioned formulas + exact L3 source fingerprint | rebuildable after source retained | M5; LOW output | absent | L2 deterministic metrics | `DERIVE_FROM_CANONICAL_SOURCE` | formula + source qualification | master L2 |
| KS-10 | Kraken Spot | Assets/AssetPairs/status/instrument metadata | REST/WS PUB | all | base/quote, tick/order min/cost min/status/precision and identifiers | metadata snapshots | METADATA_LOW_FREQUENCY; LOW | hard-coded pair list today | discovery/admission | `PROVIDER_METADATA` | metadata versioning | KRAKEN-SPOT |
| KS-11 | Kraken Spot | ticker summary | REST/WS PUB | pairs | current/24h stats | current | OTHER; LOW | not needed as source | convenience | `REDUNDANT_DO_NOT_STORE` | none unless consumer requires | KRAKEN-SPOT |
| KF-01 | Kraken Futures | current 13 analytics metric families, every eligible row | REST PUB charts analytics | PI_ETHUSD/PI_XBTUSD current; instruments target | provider-native metric rows/time | paginated history; current revision classes | 300s/provider intervals; LOW | GH all rows; D8 latest-only | provider-native history | `P0_PARITY` P0-07 | R1-R7 | KRAKEN-FUTURES |
| KF-02 | Kraken Futures | revision/PIT evidence | REST PUB overlap observation | current revisable metrics | effective timestamp, known_at, previous fingerprint, observed value, revision_of, source snapshot | overlap re-observation | H1/observer; LOW | GH revisions YES; D8 NO | REVISION_EVIDENCE | `P0_PARITY` P0-08 | R1-R7 | repo semantics + official analytics |
| KF-03 | Kraken Futures | long-short-info/top-traders/orderbook analytics | REST PUB charts analytics | instruments | provider-native analytics fields/time | charts pagination; `BOUNDED_BACKFILL`/provider history | 300s/declared; LOW | absent D8 | compact positioning/book analytics | `P1_COMPACT` P1-16..18 | R2-R7 | KRAKEN-FUTURES |
| KF-04 | Kraken Futures | liquidity-pool analytics | REST PUB `/api/charts/v1/analytics/liquidity-pool` | derivatives pool | pool value/time fields | interval query; provider history | H1/D1; LOW | absent | systemic risk/liquidation-capacity context | `P1_COMPACT` P1-63; `KRAKEN_DERIVATIVES_LIQUIDITY_POOL_METRICS=COLLECT` | R2-R7 | KRAKEN-FUTURES |
| KF-05 | Kraken Futures | trade/mark/spot-reference candles | REST PUB charts | tradeable symbols/reference | OHLC candle values/time; tick type identity | chart pagination | M5/H1/...; LOW | absent | independent native reference series | `P1_COMPACT` P1-19..21 | R2-R7 | KRAKEN-FUTURES |
| KF-06 | Kraken Futures | public ticker/reference/funding/OI/premium/maturity snapshot | WS PUB | tradeable products | funding/prediction,bid/ask,size,volume,index,mark,OI,premium,maturity/tag,time | live snapshot/delta; `FORWARD_ONLY` | M5/stream; LOW | current collector does not canonically persist full ticker family | compact state/curve input | `P1_COMPACT` P1-64 | R2-R7 | KRAKEN-FUTURES |
| KF-07 | Kraken Futures | dated-futures curve/basis compact evidence | REST/WS PUB + analytics | dated futures from instruments | maturity,mark/index/trade/future-basis | provider charts/current | H1/EXPIRY; LOW | absent | term-structure corroboration | `P1_COMPACT` P1-65 | R2-R7 | KRAKEN-FUTURES |
| KF-08 | Kraken Futures | raw trades/history with fill/liquidation/termination/block classification | REST/WS PUB | tradeable products | side,type,seq,time,qty,price,uid | recent/history bounded; `SHORT_PROVIDER_RETENTION` where endpoint says recent | EVENT_STREAM; HIGH | absent | raw execution/deleveraging evidence | `P2_HIGH_CARDINALITY` | P2 backend | KRAKEN-FUTURES |
| KF-09 | Kraken Futures | compact normal/liquidation/termination/block aggregates | derived from KF-08 | products | counts/qty/notional/side/time buckets | rebuildable if raw retained | M5; LOW | absent | deleveraging/institutional evidence | `P1_COMPACT` P1-22 | R2-R7 | master L2 |
| KF-10 | Kraken Futures | public L2 book snapshots/deltas | WS PUB | tradeable products | seq,timestamp,bid/ask price+qty | stream `FORWARD_ONLY` | EVENT_STREAM; VERY_HIGH | absent | raw microstructure | `P2_HIGH_CARDINALITY` | P2 backend | KRAKEN-FUTURES |
| KF-11 | Kraken Futures | public historical market order events | REST PUB current history interface where exposed | products | add/change/cancel/order-event identities/times | continuation/history semantics; `UNKNOWN_REVERIFY` exact retention | EVENT/OTHER; VERY_HIGH | absent | raw order-flow history | `P2_HIGH_CARDINALITY` | official endpoint reverify + P2 | KRAKEN-FUTURES |
| KF-12 | Kraken Futures | instrument catalog/maturity/index/reference metadata | REST PUB | all tradeable products | symbol,type,underlying,maturity/tradeable/reference identifiers | metadata snapshots | METADATA_LOW_FREQUENCY; LOW | collector discovers but admits hard-coded two | discovery/admission | `PROVIDER_METADATA` | metadata versioning | KRAKEN-FUTURES |
| KF-13 | Kraken Futures | ticker_lite/duplicate summary transports | WS PUB | products | subset of ticker | current | OTHER; LOW | absent | duplicate transport | `REDUNDANT_DO_NOT_STORE` | no second identity | KRAKEN-FUTURES |
| DF-01 | Deribit Futures | ETH/BTC perpetual current ticker/book summary | REST/WS PUB | ETH/BTC instruments | mark/index,last,bid/ask,OI/funding where supplied,time | current; `FORWARD_ONLY` | M5; LOW | GH/D8 current YES | sampled current evidence | `P0_PARITY` preserve | R1-R7 | DERIBIT |
| DF-02 | Deribit Futures | perpetual funding H1 | REST PUB | ETH/BTC perpetuals | timestamp,index price,8h/1h interest,previous index | historical API; `BOUNDED_BACKFILL`/forward continuation | H1; LOW | GH YES; D8 NO | fixed history | `P0_PARITY` P0-09 | R1-R7 | DERIBIT |
| DF-03 | Deribit Futures | perpetual OHLCV H1 | REST PUB TradingView | ETH/BTC perpetuals | OHLCV ticks/time | chart range; `DEEP_BACKFILL_AVAILABLE` where public chart supports range | H1; LOW | GH YES; D8 NO | fixed history | `P0_PARITY` P0-10 | R1-R7 | DERIBIT |
| DF-04 | Deribit Futures | dated futures ticker/OHLCV/book summaries | REST/WS PUB | dynamic dated instruments | price/OHLCV/OI/mark/index/maturity/book summary fields | public range/current | H1/EXPIRY; LOW | absent | futures curve source | `P1_COMPACT` P1-27 | R2-R7 | DERIBIT |
| DF-05 | Deribit Futures | future curve/basis/annualized basis | derived from canonical dated/perp/index source | ETH/BTC maturities | versioned term-structure output | rebuildable | H1; LOW | absent | deterministic curve metric | `DERIVE_FROM_CANONICAL_SOURCE` P1-29 identity remains analytical candidate | formula + source proof | master L2 |
| DF-06 | Deribit Futures | delivery prices + settlements/delivery/bankruptcy history | REST PUB | currencies/instruments | settlement type,value,time,instrument/delivery identifiers | historical pagination; `DEEP_BACKFILL_AVAILABLE` public settlement history | EXPIRY_DRIVEN; LOW | absent | expiry/default/risk evidence | `P1_COMPACT` P1-66 | R2-R7 | DERIBIT |
| DF-07 | Deribit Futures | mark-price history 5m | REST PUB | instrument | 5m mark values/time | historical API; `DEEP_BACKFILL_AVAILABLE`/range | M5; LOW | absent | provider-native mark history | `P1_COMPACT` P1-67 | R2-R7 | DERIBIT |
| DF-08 | Deribit Futures | index current/chart/reference | REST/WS PUB | index names | index values/time/composition identity where exposed | current + chart history | M5/H1; LOW | partial current | reference evidence | `P1_COMPACT` P1-68 | R2-R7 | DERIBIT |
| DF-09 | Deribit Futures | aggregated trade-volume families | REST PUB | currencies/kinds | 24h executed volume aggregates | rolling summary | H1/D1; LOW | absent | market activity context | `P1_COMPACT` P1-69 | R2-R7 | DERIBIT |
| DF-10 | Deribit Futures | instruments/expirations/contract-size/currencies/index-name metadata | REST/WS PUB | all | instrument kind,state,expiry,strike/contract size,currency/index identifiers | metadata snapshots; recently expired supported | METADATA_LOW_FREQUENCY; LOW | collector uses explicit instruments today | discovery/admission | `PROVIDER_METADATA` | metadata versioning | DERIBIT |
| DO-01 | Deribit Options | full ETH surface + selected Greeks | REST/WS PUB | dynamic ETH chain | mark/IV/OI/volume/ticker Greeks/definition fields | snapshot+public streams; backfill varies | H1; MEDIUM | GH/D8 surface YES | sampled chain evidence | `P0_PARITY` preserve current information | R1-R7 | DERIBIT-OPTIONS |
| DO-02 | Deribit Options | selected option books | REST PUB | selected ETH options | raw bid/ask levels, mark/index, timestamp | snapshots forward | H1; MEDIUM | GH YES; D8 loses selection | sampled liquidity evidence | `P0_PARITY` P0-12 | R1-R7 | DERIBIT-OPTIONS |
| DO-03 | Deribit Options | full BTC surface | REST/WS PUB | dynamic BTC chain | same chain valuation fields | snapshots/streams | H1; MEDIUM | absent | cross-underlying/cross-venue volatility | `P1_COMPACT` P1-24 | R2-R7 | DERIBIT-OPTIONS |
| DO-04 | Deribit Options | fuller mark/bid/ask IV + Greeks + OI | REST/WS PUB | ETH/BTC chain | mark price/IV,bid/ask IV,delta/gamma/theta/vega/rho where supplied,OI,volume | live/snapshots; public history where endpoint supports | H1; MEDIUM | partial selected | option valuation/risk evidence | `P1_COMPACT` P1-30 | R2-R7 | DERIBIT-OPTIONS |
| DO-05 | Deribit Options | option OHLCV/TradingView charts | REST/WS PUB | option instruments | OHLCV/trade chart time | public range backfill; `DEEP_BACKFILL_AVAILABLE` where chart endpoint serves range | H1/OTHER; MEDIUM | absent | option price history | `P1_COMPACT` P1-70 | R2-R7 | DERIBIT-OPTIONS |
| DO-06 | Deribit Options | public raw trades live + REST history | REST/WS PUB | instrument or whole kind/currency chain | price,amount,direction,time,trade id/seq,index/mark/IV/block ids where supplied | time/sequence pagination; max 1000/call; official guide supports gapless full-history paging | EVENT_STREAM; HIGH | absent | raw option/institutional flow | `P2_HIGH_CARDINALITY` | P2 backend | DERIBIT-OPTIONS |
| DO-07 | Deribit Options | compact trade/IV/liquidation aggregates | derived/public trade fields | ETH/BTC chain | versioned M5/H1 counts/qty/notional/IV/liq classes | rebuildable if raw retained | M5; LOW | absent | flow/deleveraging evidence | `P1_COMPACT` P1-31..33 | R2-R7 after source | master L2 |
| DO-08 | Deribit Options | public block trade identity | public trade history/streams | option/futures | `block_trade_id`, leg/trade fields/time | same public trade backfill | EVENT/OTHER; LOW | absent | institutional flow | `P1_COMPACT` P1-34 | R2-R7 | DERIBIT-BLOCK |
| DO-09 | Deribit Options | combo definitions/leg metadata | REST PUB combo methods | separate combo namespace | combo id/state/full leg structure | current metadata; snapshots | METADATA_LOW_FREQUENCY; LOW | absent | multi-leg instrument discovery | `PROVIDER_METADATA` | namespace/versioning | DERIBIT-OPTIONS |
| DO-10 | Deribit Options | combo/multi-leg trade identity | public trade evidence where provider emits combo/block identity; private user combo channels excluded | mixed | multi-leg identifiers/leg mapping/time | public evidence varies; `UNKNOWN_REVERIFY` exact retention | EVENT/OTHER; LOW | absent | institutional strategy evidence | `P1_COMPACT` P1-35 | R2-R7 | DERIBIT-OPTIONS |
| DO-11 | Deribit Options | executed Block RFQ trades | REST/WS PUB `get_block_rfq_trades` / `block_rfq.trades.{currency}` | currencies | RFQ trade/leg identifiers,time,price/amount | recent + continuation where provided; `BOUNDED_BACKFILL` | EVENT/OTHER; LOW | absent | institutional RFQ execution evidence | `P1_COMPACT` P1-36 | R2-R7 | DERIBIT-RFQ |
| DO-12 | Deribit Options | private RFQ request/quote/acceptance and private block execution state | REST/WS PRIVATE | accounts | counterparty/account/RFQ quote state | private | EVENT; MEDIUM | absent | account/trading state, not public market fact | `OUT_OF_PROJECT_SCOPE` | separate owner/security decision only | DERIBIT-RFQ/BLOCK |
| DO-13 | Deribit Options | high-frequency public books/trades | WS PUB (100ms/agg where allowed) | many chain instruments | book/trade deltas | forward streams | EVENT_STREAM; VERY_HIGH | absent | raw microstructure | `P2_HIGH_CARDINALITY` | P2 backend | DERIBIT-OPTIONS |
| DO-14 | Deribit Options | authenticated raw order-book interval | WS AUTH | instruments | raw book events | forward | EVENT_STREAM; VERY_HIGH | absent | potentially richer microstructure | `AUTH_REQUIRED_REVIEW` | security + P2 backend | DERIBIT-OPTIONS |
| DV-01 | Deribit Volatility | ETH DVOL full H1 rows | REST/WS PUB | ETH DVOL index | candle-formatted volatility index/time | public REST backfill | H1; LOW | GH full history; D8 latest-only | provider-native vol index | `P0_PARITY` P0-11 | R1-R7 | DERIBIT-OPTIONS |
| DV-02 | Deribit Volatility | BTC DVOL | REST/WS PUB | BTC DVOL index | DVOL candles/time | public backfill | H1; LOW | absent | cross-underlying implied-vol context | `P1_COMPACT` P1-25 | R2-R7 | DERIBIT-OPTIONS |
| DV-03 | Deribit Volatility | ETH/BTC historical volatility | REST PUB | currencies | provider historical-vol series/time | historical endpoint | H1/D1; LOW | absent | provider-native realized/historical vol | `P1_COMPACT` P1-26 | R2-R7 | DERIBIT-OPTIONS |
| DV-04 | Deribit Volatility | locally derived realized vol vs provider historical vol | derived | canonical price series | formula/version/source fingerprint | rebuildable | H1/D1; LOW | partial analytics | deterministic corroboration | `DERIVE_FROM_CANONICAL_SOURCE`; identity distinct from provider vol | formula proof | master L2 |
| DR-01 | Deribit Reference | public market trade backfill by time/sequence across futures/options | REST PUB | instrument/currency/kind | public trade fields incl ids/seq/time/price/amount | official time/sequence paging, count max 1000; guide describes gapless full history | OTHER/EVENT; HIGH | absent | recoverable raw market tape | `P2_HIGH_CARDINALITY` | P2 backend | DERIBIT-OPTIONS |
| DR-02 | Deribit Reference | private user historical trades/orders with `historical:true` | REST PRIVATE | user accounts | account order/user-trade fields | official recent 30m orders/24h trades; historical records persist indefinitely | OTHER; HIGH | absent | account-private, not public market source | `OUT_OF_PROJECT_SCOPE` | separate security/account domain only | DERIBIT-PRIVATE-HISTORY |
| DR-03 | Deribit Reference | yield-token/APR families | REST PUB | yield products | APR/yield product data | provider-specific | D1; LOW | absent | outside current ETH/BTC market-evidence target | `OUT_OF_PROJECT_SCOPE` | separate project-scope decision | DERIBIT |

### 24.8 P0/P1/P2 current registries and counts

The 12 source-code-confirmed P0 information-loss gaps remain exactly P0-01..P0-12.

```text
PREVIOUS_P0_GAP_COUNT=12
FINAL_P0_GAP_COUNT=12
```

All previous candidate IDs P1-01..P1-36 are retained as identities. Official auth review changes only P1-23’s disposition; it does not erase the candidate history. New compact candidates discovered by the exhaustive audit:

```text
P1-37  Binance USD-M provider-native basis
P1-38  Binance USD-M RPI order book
P1-39  Binance USD-M ADL risk
P1-40  Binance USD-M insurance-fund balance
P1-41  Binance USD-M quarterly settlement/delivery price
P1-42  Binance USD-M continuous-contract klines
P1-43  Binance Spot reference price/calculation
P1-44  Binance COIN-M native perp/delivery OHLCV
P1-45  Binance COIN-M continuous-contract klines
P1-46  Binance COIN-M mark/index/premium current+klines
P1-47  Binance COIN-M funding current/history/config
P1-48  Binance COIN-M OI current/history
P1-49  Binance COIN-M provider-native basis
P1-50  Binance COIN-M positioning ratios
P1-51  Binance COIN-M taker flow
P1-52  Binance COIN-M bounded depth
P1-53  Binance COIN-M compact liquidation aggregates
P1-54  Binance Options index/reference price
P1-55  Binance Options mark/IV/Greeks
P1-56  Binance Options OHLCV
P1-57  Binance Options OI by underlying/expiration
P1-58  Binance Options compact chain summary
P1-59  Binance Options bounded book
P1-60  Binance Options public block trades
P1-61  Binance Options exercise/settlement evidence
P1-62  Kraken Spot native recent-spread history
P1-63  Kraken Futures liquidity-pool analytics
P1-64  Kraken Futures ticker/reference/maturity compact state
P1-65  Kraken Futures dated-futures curve compact evidence
P1-66  Deribit settlement/delivery/bankruptcy history
P1-67  Deribit mark-price history
P1-68  Deribit index current/chart/reference
P1-69  Deribit aggregated trade volumes
P1-70  Deribit option OHLCV
```

Current registry accounting:

```text
P1_REGISTRY_ENTRY_COUNT=70
P1_AUTH_REQUIRED_REVIEW_ENTRY_COUNT=1
FINAL_P1_COMPACT_FAMILY_COUNT=69
FINAL_P2_FAMILY_COUNT=13
PROVIDER_METADATA_FAMILY_COUNT=8
AUTH_REQUIRED_REVIEW_COUNT=5
REDUNDANT_OR_REJECTED_COUNT=11
```

P2 current logical families are: Binance Spot raw trade tape; Binance Spot depth deltas; USD-M raw trade tape; USD-M force orders; COIN-M raw trade/depth/liquidation stream family; Binance Options raw trade/depth; Kraken Spot raw trade tape; Kraken Futures raw trades; Kraken Futures L2 deltas; Kraken Futures public historical order events; Deribit raw option trade history/live; Deribit high-frequency books/trades; Deribit cross-product full public raw trade backfill. The P2 list is explicitly extensible when later official API changes reveal additional high-cardinality market evidence.

### 24.9 Product-family disposition summary and exhaustive proof

```text
BINANCE_SPOT_RELEVANT_SURFACE_CLASSIFIED=PASS
BINANCE_USDM_RELEVANT_SURFACE_CLASSIFIED=PASS
BINANCE_COINM_RELEVANT_SURFACE_CLASSIFIED=PASS
BINANCE_OPTIONS_RELEVANT_SURFACE_CLASSIFIED=PASS
KRAKEN_SPOT_RELEVANT_SURFACE_CLASSIFIED=PASS
KRAKEN_FUTURES_RELEVANT_SURFACE_CLASSIFIED=PASS
DERIBIT_FUTURES_RELEVANT_SURFACE_CLASSIFIED=PASS
DERIBIT_OPTIONS_RELEVANT_SURFACE_CLASSIFIED=PASS
DERIBIT_VOLATILITY_RELEVANT_SURFACE_CLASSIFIED=PASS
UNCLASSIFIED_RELEVANT_PROVIDER_CAPABILITY_COUNT=0
R0_MASTER_SPEC=PASS_COMPLETE_FOR_DOCUMENTED_PROVIDER_SURFACE_SNAPSHOT
```

Explicit new-family disposition:

```text
BINANCE_COINM_EXPLICIT_DISPOSITION=P1_COMPACT_FOR_SELECTED_BTC_ETH_INVERSE_CONTRACT_REFERENCE_POSITIONING_CURVE_AND_LIQUIDITY;P2_HIGH_CARDINALITY_FOR_RAW_TAPE_BOOK_LIQUIDATION;PROVIDER_METADATA_FOR_DISCOVERY
BINANCE_OPTIONS_EXPLICIT_DISPOSITION=P1_COMPACT_FOR_INDEPENDENT_CROSS_VENUE_CHAIN_REFERENCE_IV_GREEKS_OI_OHLCV_BOOK_BLOCK_EXERCISE;P2_HIGH_CARDINALITY_FOR_RAW_TRADE_DEPTH
KRAKEN_DERIVATIVES_LIQUIDITY_POOL_METRICS=COLLECT
KRAKEN_L3_AUTH_SCOPE=AUTHENTICATED_MARKET_DATA
```

### 24.10 Deribit historical backfill result

A blanket `FORWARD_ONLY` assumption is rejected. Current official Deribit documentation exposes public market-trade backfill by time range and sequence range, TradingView OHLC backfill, mark-price history, index/history families, funding/history, DVOL backfill, delivery prices and historical settlement/delivery/bankruptcy records. The options best-practices guide explicitly describes paging public trade history to full history without gaps/duplicates and recommends sequence pagination when gaplessness matters.

Private **user** order/trade history is a different API family: current official documentation says recent user orders are available for 30 minutes, recent user trades for 24 hours, and authenticated historical records persist indefinitely with `historical:true`. That is account-private evidence and remains out of project scope.

```text
DERIBIT_HISTORICAL_BACKFILL_CAPABILITY=PUBLIC_MARKET_TRADES_AND_MULTIPLE_PUBLIC_MARKET_HISTORY_SERIES_AVAILABLE
DERIBIT_HISTORICAL_BACKFILL_SCOPE=PUBLIC_TRADES_BY_TIME_OR_SEQUENCE;OHLCV_CHARTS;MARK_PRICE_5M;INDEX_HISTORY;FUNDING;DVOL;DELIVERY_AND_SETTLEMENT_BANKRUPTCY
DERIBIT_HISTORICAL_BACKFILL_AUTH_REQUIREMENT=PUBLIC_NO_AUTH_FOR_PUBLIC_MARKET_SERIES;ACCOUNT_AUTH_REQUIRED_FOR_PRIVATE_USER_HISTORY
DERIBIT_HISTORICAL_BACKFILL_PLANNING_DISPOSITION=P1_COMPACT_FOR_BOUNDED_COMPACT_PUBLIC_SERIES;P2_HIGH_CARDINALITY_FOR_FULL_RAW_PUBLIC_TRADE_HISTORY;OUT_OF_PROJECT_SCOPE_FOR_PRIVATE_USER_HISTORY
```

Exact retention/history depth remains `UNKNOWN_REVERIFY` where the provider documentation does not state a hard bound; no retention number is invented from memory.

### 24.11 Recoverability priority

Forward-only and short-retention sources are elevated because they cannot be recreated later. Priority ordering is not equivalent to polling frequency:

```text
FORWARD_ONLY_OR_SHORT_RETENTION_RAW_EVENTS
→ preserve acquisition requirement now (P2 if necessary)
→ choose durable backend before production capture

DEEP_OR_BOUNDED_BACKFILL
→ can be backfilled/verified according to provider limits
```

Books, provider revisions, liquidation/force-order events, recent trade tapes and high-frequency market events must not disappear from roadmap merely because GITHUB_FIRST_V1 cannot safely store their raw cardinality.

### 24.12 Rate-budget and scheduler model after expansion

The canonical scheduler tick may remain M5, but due policy is capability-specific:

```text
M5_TICK
→ capability due policy
→ M5 | M15 | H1 | H4 | D1 | W1 | EVENT_STREAM | METADATA_LOW_FREQUENCY | EXPIRY_DRIVEN | OTHER_DECLARED
```

Shared budget ownership remains:

```text
PROVIDER
→ RATE_BUDGET
→ CAPABILITIES
→ WORKERS
```

R2 must prove real current weights, concurrency/subscription caps, 429/backoff and intended cadence before accepting final production P1. The R0 matrix is coverage/disposition authority, not execution-rate authorization.

### 24.13 Provider API drift policy

```text
R0_PROVIDER_API_SURFACE_SNAPSHOT=FROZEN_AT_2026-08-22T21:16:21Z
R2_REAUDIT_REQUIRED_IF_IMPLEMENTATION_SPANS_MATERIAL_PROVIDER_API_CHANGE=true
R8_FINAL_PROVIDER_API_AND_CHANGELOG_REAUDIT_REQUIRED=true
PROVIDER_API_CHANGE_REAUDIT_REQUIRED_BEFORE_R8=true
```

No R8 production cutover may use an obsolete provider surface inventory. Removed/deprecated endpoints must become `SUPERSEDED` or `UNAVAILABLE_BY_PROVIDER` with replacement/impact recorded rather than silently vanishing.

### 24.14 Whole-product / cross-venue analytical intent

Maximum-source collection is not endpoint collection for its own sake. The admitted evidence surface is intended to enable future, separately owned Research analysis such as:

- spot vs perp flow;
- Binance vs Kraken positioning/OI/funding/basis confirmation;
- USD-M vs COIN-M leverage divergence;
- ETH vs BTC options volatility;
- Deribit vs Binance Options cross-venue IV/skew/OI;
- perp vs dated-future curve;
- spot-led vs leverage-led price impulse;
- liquidation/deleveraging regimes;
- institutional block/combo/RFQ flow;
- order-book liquidity fragmentation;
- provider disagreement / market dislocation.

These are planning motivations only. No analytical model, regime, signal, probability or scenario is implemented or owned by Data Bridge.

### 24.15 R0 acceptance after exhaustive audit

```text
OFFICIAL_PROVIDER_DOCUMENTATION_REVIEW=PASS
FIELD_LEVEL_INFORMATION_PRESERVATION=PASS
PROVIDER_METADATA_DISCOVERY_PLANE=CAPTURED
INSTRUMENT_ADMISSION_POLICY=CAPTURED
PROVIDER_NATIVE_BASIS_IDENTITY_DISTINCT=PASS
PROVIDER_NATIVE_CVD_IDENTITY_DISTINCT=PASS
PROVIDER_NATIVE_VOLATILITY_IDENTITY_DISTINCT=PASS
SPOT_CVD_VS_PERP_CVD=CAPTURED
ORDER_COUNT_IMBALANCE=CAPTURED_CONDITIONAL_ON_APPROVED_INDIVIDUAL_ORDER_SOURCE
MEAN_ORDER_SIZE_BY_LEVEL=CAPTURED_CONDITIONAL_ON_APPROVED_INDIVIDUAL_ORDER_SOURCE
WALL_FRAGMENTATION=CAPTURED_CONDITIONAL_ON_APPROVED_INDIVIDUAL_ORDER_SOURCE
TECHNICAL_INDICATORS_SEPARATED=PASS
HIGH_CARDINALITY_BOUNDARY=PASS
RECOVERABILITY_CLASSIFICATION=PASS
CARDINALITY_CLASSIFICATION=PASS
RATE_BUDGET_REVIEW_REQUIRED_BEFORE_IMPLEMENTATION=YES
PROVIDER_API_CHANGE_REAUDIT_REQUIRED_BEFORE_R8=YES
HORIZONTAL_INSTRUMENT_DISCOVERY=CAPTURED
R0_EXHAUSTIVE_PROVIDER_SURFACE_AUDIT=PASS
NO_EXECUTABLE_SOURCE_MUTATION=REQUIRED
NO_RUNTIME_MUTATION=REQUIRED
NO_SERVER_MUTATION=REQUIRED
NO_PROVIDER_AUTHORITY_CHANGE=REQUIRED
```

R1 source implementation may start only after owner integration of this repaired R0 planning authority. R0 PASS does not authorize R1 merge, R2 endpoints, server deployment, D8/D9 activation, provider-authority transition, production scheduler, WARM forwarder or legacy-acquisition disablement.