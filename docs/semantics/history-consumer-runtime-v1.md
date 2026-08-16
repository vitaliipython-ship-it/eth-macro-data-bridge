# Runtime consumer для historical market data v1

## Статус

`CANDIDATE / D6.5 CONSUMER-READINESS HARDENING`

Этот слой не создаёт новый market-data route, catalog, resolver, cache authority или storage backend. Он уменьшает число действий аналитического агента и даёт штатный read-only transport для сессий, которые могут работать с GitHub Actions/artifacts, но не могут напрямую получить binary body GitHub Release asset.

## Authority chain

Единственная допустимая цепочка:

```text
AGENTS.md
→ bridge-contract.json
→ history/capability-index.json
→ tools/capability_index.py / resolve_capability()
→ market-data-resolution-plan/1.0.0
→ tools/history_access.py / materialize_resolution_plan()
→ verified Git WARM или immutable GitHub Release bytes
→ candles + diagnostics + receipt
```

`tools/history_consumer.py` — только execution adapter над этой цепочкой. Он не строит physical paths/URLs и не повторяет resolver.

## Локальный/agent runtime

Один semantic request:

```bash
python tools/history_consumer.py read \
  --series-id spot.binance-spot.ETHUSDT.ohlcv.4h \
  --from 2023-10-13T00:00:00Z \
  --to 2024-03-13T00:00:00Z \
  --mode strict \
  --format csv \
  --output candles.csv \
  --plan-output resolution-plan.json \
  --diagnostics-output diagnostics.json \
  --receipt-output receipt.json
```

Caller задаёт только semantic `series_id`, `[from,to)`, optional replay cutoff и integrity mode. Storage placement остаётся прозрачным.

## Hosted read-only transport

Workflow `.github/workflows/history-consumer-read.yml` предоставляет `workflow_dispatch` с теми же semantic inputs и публикует краткоживущий Actions artifact:

- normalized candles;
- exact `ResolutionPlan`;
- integrity diagnostics;
- consumer receipt.

Artifact является **transport output**, а не evidence/byte authority. Каноническая provenance внутри receipt остаётся привязана к exact physical source segment SHA/locator из validated `ResolutionPlan`.

## Failure semantics

```text
RESOLUTION_FAILED       semantic range/series не разрешён canonical resolver-ом
DATA_TRANSPORT_BLOCKED  reader получил DOWNLOAD_FAILED при physical COLD fetch
READER_FAILED           integrity/schema/gap/duplicate/other reader failure
PASS                    canonical bytes реально materialized и проверены
DEGRADED                только explicit permissive mode с diagnostics
```

`DATA_TRANSPORT_BLOCKED` не разрешает direct provider fallback. Официальный provider API может использоваться только как отдельная corroboration, но не как silent replacement canonical history.

## Qualification contract

Push qualification на dedicated implementation branch обязан реально materialize:

1. Binance Spot ETHUSDT H4 `2023-10-13 → 2024-03-13`, strict;
2. Binance Spot ETHUSDT H1 тот же диапазон, strict;
3. Binance Spot ETHUSDT M5 `2024-03-11 → 2024-03-13`, strict;
4. Binance Spot ETHUSDT M5 `2022-06-18 → 2022-11-10`, strict, `41760` rows, immutable COLD;
5. один фактический H1 asset Kraken Spot ETHUSD;
6. один фактический H1 asset Deribit ETH-PERPETUAL.

Для каждого case обязательны `status=PASS`, `gap_count=0`, `duplicates=0`, `rows=expected_rows`, `plan_sha256`, source locator/SHA и output SHA-256.

## Guardrails

1. `ResolutionPlan` остаётся input authority reader-а.
2. Capability index остаётся derived discovery projection.
3. Никаких guessed/hardcoded Release routes.
4. WARM/COLD integrity и merge остаются deterministic и SHA-pinned.
5. Workflow artifact не копируется в Research и не становится новым SSOT.
6. Collector/cadence/provider acquisition не изменяются.
