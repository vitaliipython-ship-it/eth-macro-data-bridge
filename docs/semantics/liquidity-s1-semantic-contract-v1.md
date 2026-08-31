# S1 liquidity semantic contract v1

## Статус и authority

```text
CONTRACT_ID=ETH-LIQUIDITY-S1-SEMANTIC-CONTRACT-V1
MACHINE_AUTHORITY=contracts/liquidity-s1-semantic-contract-v1.json
ARCHITECTURE_PREDECESSOR_PR=295
STATUS=ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE
ARCH_B_CAPABILITY_SELECTIVE_EXTENSION=RETAINED
S1_SOURCE_IMPLEMENTATION=SOURCE_IMPLEMENTED_NOT_ACTIVE
S1_RUNTIME_ACTIVE=NO
S2_PROVIDER_ROLLOUT=NO
S3_REQUEST_AWARE_NETWORK_ACTIVATION=NO
PRODUCTION_NETWORK_CALLS_ADDED=0
PRODUCTION_SCHEDULER_MUTATED=NO
```

Machine contract остаётся единственным S1 semantic owner. Этот документ — implementation-facing projection. Route/provider policy остаётся `bridge-contract.json`; provider/API facts принадлежат `contracts/provider-contracts.json`; capability discovery/resolution остаётся в существующем contour `history/capability-index.json → tools/capability_index.py → ResolutionPlan → tools/history_access.py`.

S1 runtime foundation реализован в `src/liquidity_s1_runtime.py` как pure provider-independent source layer. Он не является collector, resolver, reader, catalog, storage authority, agent API или provider adapter и не выполняет network I/O.

## Single Market Data Foundation

```text
ARCHITECTURE=ARCH_B_CAPABILITY_SELECTIVE_EXTENSION
MARKET_DATA_FOUNDATION_CONTOUR_COUNT=1
SECOND_COLLECTOR=NO
SECOND_CATALOG=NO
SECOND_RESOLVER=NO
SECOND_READER=NO
SECOND_MARKET_DATA_AUTHORITY=NO
```

Canonical existing extension points:

```text
resource index:
tools/current_data_transport.py
schema=fresh-current-resource-index/1.0.0

resolution:
tools/capability_index.py
→ ResolutionPlan
→ tools/history_access.py

current liquidity projection:
src/intelligence.py::depth_metrics
src/intelligence.py::collect_liquidity
```

## Executable S1 flow

Source implementation materializes the already accepted flow:

```text
SEMANTIC_COVERAGE_REQUEST
→ RESOURCE_SATISFACTION_CHECK
→ REUSE existing qualified resource
  OR
  DYNAMIC_DEPTH_ACQUISITION_PLANNER
→ EXACTLY_ONE_PROVIDER_ACQUISITION_PLAN
→ future ONE_COHERENT_PROVIDER_OBSERVATION
→ NORMALIZATION
→ SIDE_SPECIFIC_COVERAGE_PROOF
→ QUALIFIED / TRUNCATED / UNSATISFIED
```

`RESOURCE_SATISFACTION_CHECK` всегда предшествует acquisition planning. Если existing qualified resource dominates request, result:

```text
DECISION=REUSE
NETWORK_REQUIRED=NO
ACQUISITION_PLAN=null
```

S1 planner определяет только semantic evidence requirement. `network_required=true` означает, что существующего evidence недостаточно и будущему S2/S3 contour потребуется acquisition; это **не** означает, что S1 делает provider call.

## Semantic request

Executable request сохраняет semantic-only boundary:

```text
series_id
provider_id
instrument_id
book_kind
representation
target_bps
requested_bid_coverage_bps
requested_ask_coverage_bps
bucket_bps
freshness.max_age_seconds
completeness.required
quantity_semantics
```

Минимально поддерживаются `target_bps=250` и `target_bps=500`.

Запрещённые request inputs:

```text
provider_url
rest_endpoint
websocket_endpoint
filesystem_path
manifest_path
resource_path
provider_level_count
provider_depth_parameter
depth
limit
```

Provider-specific physical knob может появиться только как planner output, когда provider capability authority его квалифицировала.

## Resource satisfaction и dominance

Deterministic `evaluate_resource_satisfaction` возвращает:

```text
SATISFIED
UNSATISFIED
NOT_QUALIFIED
```

Сравниваются как минимум provider/instrument identity, book kind, representation compatibility, observation coherence, freshness, qualification state, bid coverage, ask coverage, completeness/truncation integrity и quantity qualification.

Одна сторона не компенсирует другую:

```text
existing bid=510 / ask=525, request=250/250
→ SATISFIED

existing bid=230 / ask=520, request=250/250
→ UNSATISFIED
```

Ресурс, truncated относительно более глубокого исходного request, может удовлетворить более узкий request только когда **реально доказанная** coverage каждой стороны dominates новый target.

Accepted conservative representation rule сохраняется: exact representation может reuse itself; coherent `RAW` может удовлетворить narrower `PROFILE` внутри physically observed book. `SUMMARY` не masquerade как `RAW`. `PROVIDER_GROUPED_L2` не masquerade как `L2_LEVEL_BOOK`.

## Dynamic-depth AcquisitionPlan

Planner deterministic: одинаковые canonical inputs дают одинаковые canonical plan bytes и digest.

Hard invariants:

```text
ONE_LOGICAL_BOOK_OBSERVATION=ONE_COHERENT_PROVIDER_OBSERVATION
SEQUENTIAL_REST_STITCHING=FORBIDDEN
RETRY_SEMANTICS=NEW_OBSERVATION
S1_EXECUTES_NETWORK=NO
```

S1 не угадывает endpoint, provider limit, level count или instrument substitution.

Kraken Futures сохраняет:

```text
RAW_L2_CAPABILITY=PROVIDER_CAPABILITY_CONFIRMED
SELECTABLE_DEPTH_LIMIT=NOT_NORMATIVELY_DOCUMENTED
NORMATIVE_MAX_DEPTH_INVENTED=false
```

Поэтому planner materializes:

```text
PROVIDER_DEPTH_BOUND_NOT_QUALIFIED
qualified_provider_depth_parameter=null
```

до будущей S2 provider qualification. PI/PF identities не взаимозаменяются.

## Normalization и book kinds

`normalize_order_book_observation` принимает ровно один provider observation и fail closed при:

- non-finite/negative invalid values;
- unsorted levels;
- duplicate prices;
- crossed/locked invalid book;
- missing observation/provider/instrument identity;
- unknown book kind/representation;
- claimed coverage larger than physically observed outermost level.

Normalized evidence сохраняет provider/instrument/observation identity, timestamp, book kind, source representation, ordered bids/asks, price и native quantity.

```text
BOOK_KIND != REPRESENTATION
RAW != NORMALIZED != PROFILE != SUMMARY
L2_LEVEL_BOOK != PROVIDER_GROUPED_L2 != L3_ORDER_BOOK != FUTURES_L2_BOOK
```

Normalized object не становится raw observation; downstream representations остаются derived evidence.

## Coverage semantics

S1 currentization не изобретает новый anchor. Runtime использует canonical anchor уже существующей current liquidity projection `src/intelligence.py::depth_metrics`:

```text
REFERENCE_PRICE_ANCHOR=BEST_BID_ASK_MIDPOINT
mid=(best_bid+best_ask)/2
```

Achieved coverage вычисляется только по outermost physically observed levels относительно midpoint:

```text
achieved_bid_bps=(mid-outer_bid)/mid*10000
achieved_ask_bps=(outer_ask-mid)/mid*10000
```

Result:

```text
requested_bid_coverage_bps
requested_ask_coverage_bps
achieved_bid_coverage_bps
achieved_ask_coverage_bps
coverage_complete_bid
coverage_complete_ask
truncated
extrapolation_allowed=false
```

Для request `500/500` и observed `230/410`:

```text
coverage_complete_bid=false
coverage_complete_ask=false
truncated=true
```

Ни linear/density/symmetry, ни bid→ask/ask→bid extrapolation не допускаются.

## Quantity semantics

Model остаётся `PRODUCT_AWARE_NATIVE_FIRST`.

Provider-native quantity сохраняется всегда. Для derivatives отдельно сохраняются native quantity/unit и contract quantity. `base_equivalent`/`quote_equivalent` materialize только при explicit qualified conversion authority.

Без такой authority:

```text
base_equivalent=null
quote_equivalent=null
consumer_qualified_equivalent=false
```

Никакой guessed contract multiplier или universal provider qty→base mapping не допускается.

## Fail-closed validity

PR #283 semantics сохранены:

```text
SOURCE_CONFLICT != AVAILABLE
NOT_QUALIFIED != AVAILABLE
MISALIGNED != AVAILABLE
UNKNOWN != AVAILABLE
UNAVAILABLE != numeric zero
UNOBSERVED != ZERO
VALID_ZERO requires explicit proof
```

PR #299 semantics сохранены:

```text
GENERATION_INTEGRITY != METRIC_QUALIFICATION != REQUEST_SATISFACTION
```

Resource existence не означает request satisfaction; provider capability existence не означает canonical AIFE resource existence; observed levels не означают requested coverage complete.

## Provider boundaries

Kraken Spot:

```text
PROVIDER_RAW_BOOK_CAPABILITY=AVAILABLE_EXTERNALLY
CURRENT_AIFE_RAW_BOOK_RESOURCE=ABSENT
```

Kraken Futures:

```text
RAW_L2_CAPABILITY=CONFIRMED
NORMATIVE_MAX_DEPTH=NOT_NORMATIVELY_DOCUMENTED
NETWORK_ACTIVATED=NO
```

Existing Binance/Deribit shallow current collection остаётся без изменений и не считается доказательством, что S1 dynamic-depth network acquisition active.

## Runtime / production boundary

```text
S1_SOURCE_IMPLEMENTED=YES
S1_RUNTIME_IMPLEMENTATION=SOURCE_IMPLEMENTED_NOT_ACTIVE
S1_RUNTIME_ACTIVE=NO
S2_PROVIDER_ROLLOUT=NO
S3_NETWORK_ACTIVATION=NO
PRODUCTION_NETWORK_CALLS_ADDED=0
PRODUCTION_SCHEDULER_MUTATED=NO
ACTIVE_DATA_ROUTES_CHANGED=NO
PROVIDER_ACTIVATION_CHANGED=NO
```

Repository CI validates source, network-free boundary, resource dominance, planner determinism, 250/500 bps, one-observation rule, coverage/no-extrapolation and native-first quantity behavior.

D8 PR synthetic integration provenance defect исправлен атомарной currentization active-current authority. Tested bytes authority — exact checked-out GitHub synthetic merge object; `parent1` — actual tested base; `parent2` обязан совпадать с `EVENT_PR_HEAD_SHA`. `EVENT_PR_BASE_SHA` остаётся event metadata only: moving-base mismatch не является failure, тогда как head substitution остаётся fail-closed.

```text
D8_PR_SYNTHETIC_PARENT1_EVENT_BASE_RACE=REPAIRED_ACTUAL_SYNTHETIC_PARENT_AUTHORITY
```

Следующий отдельный gate после owner review/merge этого source PR — S2 provider adapters/capability qualification. Real provider acquisition and S3 activation remain forbidden here.

## DB-F/S3 implementation boundary

S3 does not modify S1 semantics. `src/liquidity_s1_runtime.py` remains the sole
owner of request normalization, representation compatibility, coverage,
freshness and qualified-resource validation. Same-execution discovery is
representation-neutral and delegates the final RAW/PROFILE decision to S1.
