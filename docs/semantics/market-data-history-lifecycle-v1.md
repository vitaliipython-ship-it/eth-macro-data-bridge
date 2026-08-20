# Market Data History Lifecycle v1

## Статус

`D9 TARGET CONTRACT / SOURCE_IMPLEMENTED / PUBLICATION_PORT_SOURCE_QUALIFIED / PHYSICAL_QUALIFICATION_PENDING / NOT_ACTIVE`

Planning authority:
`vitaliipython-ship-it/eth-macro-research/docs/integrations/market-data-history-lifecycle-v1.md`.

Canonical implementation plan review:
`vitaliipython-ship-it/eth-macro-research/docs/integrations/market-data-history-lifecycle-plan-review-v1.md`.

Plan review verdict:

```text
PLAN_REVIEW=PASS
PLAN_READY_FOR_IMPLEMENTATION=YES_WITH_ORDERED_GATES
UNRESOLVED_ARCHITECTURE_BLOCKERS=0
```

Publication Port source implementation и repository/Actions qualification уже merged. До отдельной real D8 runtime physical qualification и activation transition **действующим остаётся текущий D6 semantic route** из `AGENTS.md` и `bridge-contract.json`.

Этот документ сохраняет target mechanism и planning history; он не утверждает, что HOT→WARM→COLD lifecycle уже active authority для всех series.

---

## 1. Ментальная модель

Для агента существуют только две логические области:

```text
CURRENT
HISTORY
```

Физически:

```text
CURRENT = HOT
HISTORY = WARM + COLD
```

`FORWARD ARCHIVING` — не отдельный tier. Это переход:

```text
HOT finalized/history-worthy observation
→ WARM durable history
```

`SEALING` — переход:

```text
WARM completed partition
→ verified immutable COLD
```

---

## 2. Почему механизм нужен

Он закрывает реальные риски:

1. rolling observation может исчезнуть;
2. option surface/order-book snapshot нельзя гарантированно восстановить позже;
3. provider может restate historical value;
4. WARM/COLD boundary может получить скрытый gap;
5. Git может бесконечно расти без sealing;
6. agent может ошибиться, вручную выбирая storage/path/Release.

Ручной periodic backfill не является достаточной заменой, потому что не восстанавливает forward-only observations и увеличивает число ручных действий.

---

## 3. Обязательный design gate

Перед любым D9 механизмом ответить:

1. **Какой реальный риск закрывает этот механизм?**
2. **Можно ли закрыть его более простым способом?**
3. **Уменьшает ли решение число действий для следующего агента и инженера?**

Предпочитать расширение существующего resolver/ResolutionPlan/reader новым параллельным системам.

---

## 4. Canonical semantic route

Agent не выбирает physical storage.

```text
AGENTS.md
→ bridge-contract.json
→ capability index
→ semantic request
→ canonical resolver
→ ResolutionPlan
→ canonical reader
→ verified COLD/WARM/(explicit HOT) observations
→ diagnostics + receipt + provenance
```

Запрещено передавать агентом:

- Release tag;
- asset id/name;
- browser URL;
- filesystem path;
- storage tier;
- direct provider fallback.

Research default:

```text
current_policy = FINALIZED_ONLY
```

HOT/current preview допускается только explicit policy и маркируется `PROVISIONAL`.

---

## 5. Storage roles

### HOT / CURRENT

- live/current context;
- rolling windows;
- open candle может существовать;
- не long-term authority.

### WARM / ACTIVE HISTORY

- durable recent history;
- append/idempotent;
- active partitions;
- bounded repair до sealing;
- no silent overwrite.

### COLD / SEALED HISTORY

- immutable;
- SHA/size verified;
- long-term authority;
- backend hidden behind ResolutionPlan.

WARM и COLD — одна logical HISTORY.

---

## 6. Что обязано архивироваться

### Unrecoverable observations

Всегда durable capture:

- full option surface;
- order-book snapshot;
- current OI/ticker state, если later history не гарантирована;
- selected Greeks, реально использованные historical analytics.

### Provider-native series

Сохранять, если series research-relevant, provider-limited, revisable или нужна independent corroboration.

### Deterministic derived

Не обязаны быть отдельной source authority:

- higher TF from M5;
- indicators;
- option ratios/RR/BF;
- IV term structure;
- depth/imbalance/slippage при полном raw book.

Derived output может быть materialized, но authority остаётся у inputs + algorithm version.

---

## 7. Spot authority v1

### Binance

Provider-native source authority сохраняется для:

```text
M5 M15 H1 H4 D1 W1
```

M5 одновременно служит base aggregation series.

Из M5 строятся derived M15/H1/H4/D1/W1 для automatic equivalence checks.

D9 v1 не переводит higher TF authority на derived series.

### Kraken Spot

M5 durable accumulation обязательна из-за provider retention limits.

Provider-native higher TF сохраняются как corroboration evidence.

---

## 8. Kraken Futures

Для `PI_ETHUSD` и `PI_XBTUSD` сохраняются provider-native canonical metrics:

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

Сохранить existing semantic classes:

```text
STRICT_OVERLAP_REQUIRED
WINDOW_ANCHORED_CUMULATIVE
PROVIDER_REVISABLE_SNAPSHOT
```

Revisable series требуют point-in-time revision provenance; later restatement не уничтожает earlier-observed value.

---

## 9. Deribit

### Perpetual

Target durable continuation:

- H1 OHLCV;
- funding;
- scheduled mark/index/OI/current_funding/funding_8h/24h-volume snapshots.

### Options

Full active ETH option surface — forward-only historical evidence и должна durable сохраняться.

Derived ratios/RR/BF/term structure не являются source authority.

ETH DVOL H1 остаётся provider-native historical series.

---

## 10. Liquidity / order book

Каждый selected snapshot сохраняется как historical observation.

Если calculation использует 100 Binance levels, historical raw input должен сохранять все фактически использованные 100 levels. Derived depth/slippage без полного input недостаточно воспроизводимы.

Missing scheduled snapshot фиксируется как `COLLECTION_GAP`, а не synthetic copy соседнего состояния.

---

## 11. Partition / retention target

Initial policy:

```text
regular grid:
  daily WARM → monthly COLD

high-cardinality snapshots:
  daily WARM grouping → weekly COLD
```

WARM cleanup только после:

```text
publish PASS
+ read-back PASS
+ SHA/size PASS
+ coverage PASS
+ overlap PASS
+ cross-boundary semantic read PASS
+ retention overlap gate
```

COLD logical retention — indefinite для v1.

---

## 12. Continuity

### Fixed grid

Expected timestamp отсутствует:

- strict = FAIL;
- permissive = explicit diagnostic;
- synthetic fill forbidden.

### Sampled series

Нужен collection-run ledger:

```text
expected_schedule_at
collection_started_at
collection_completed_at
provider
series_or_capability
status
snapshot_ref
error_class
```

Так отличаем `COLLECTION_GAP` от реально наблюдавшегося unchanged state.

---

## 13. WARM → COLD sealing

Fail-closed transaction:

1. exact seal range;
2. finalization/revision lag check;
3. freeze WARM inputs;
4. allowed repair/backfill;
5. schema/grid/duplicate/gap/revision validation;
6. deterministic build;
7. input fingerprint + SHA/size/count;
8. optional A/B deterministic build for critical assets;
9. immutable publication;
10. download/read-back;
11. SHA/size verify;
12. overlap proof;
13. atomic manifest update;
14. capability-index rebuild;
15. semantic cross-boundary read;
16. only then WARM cleanup.

Failure не удаляет WARM и не инвалидирует previous COLD.

---

## 14. Unified reader target

Backward-compatible successor должен поддерживать минимум:

```text
OHLCV
SCALAR_TIME_SERIES
STRUCTURED_TIME_SERIES
SNAPSHOT_SERIES
OPTION_SURFACE
ORDER_BOOK_SNAPSHOT
```

Один ResolutionPlan family, один semantic route.

---

## 15. Wave / Research provenance

Future canonical workflow:

```text
semantic market read
→ verified finalized observations
→ PIVOT
→ WAVE_COUNT
→ CURRENT_STATE
```

Research object не должен использовать rolling/latest physical path как долговременную price authority.

Evidence ref должен сохранять semantic identity и receipt/plan fingerprints; physical placement остаётся внутри Data Bridge provenance.

---

## 16. D9 decomposition

```text
D9.1 contracts/schemas/documentation
D9.2 HOT→WARM integration
D9.3 WARM→COLD sealing
D9.4 unified non-OHLCV/current reader
D9.5 Research/Wave provenance integration
```

Ни один подпункт не становится active contract без qualification/activation.

Plan review дополнительно фиксирует dependency: D9.3 sealing implementation может быть разработан до D9.4, но новая COLD generation не активируется как authority до combined D9.3+D9.4 cross-boundary semantic qualification.

---

## 17. Agent invariant

Следующему агенту должно быть достаточно:

```text
series_id + time range + integrity/current policy
```

Data Bridge сам решает:

- COLD/WARM/HOT placement;
- integrity;
- coverage;
- revisions;
- provenance.

Если storage backend меняется, semantic interface агента не меняется.
