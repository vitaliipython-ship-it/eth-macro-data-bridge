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