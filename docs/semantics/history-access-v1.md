# D6 Historical Data Access v1 — D6.3 qualified

## Статус

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=PENDING
D6.5=PENDING
```

`D6.2A + D6.2B + D6.3 QUALIFIED / PASS / NOT YET PUBLIC ROUTE`.

Эта реализация продолжает qualified D6.1 и **не активирует** capability path в `bridge-contract.json`. D6.4 activation и D6.5 Research migration остаются отдельными последующими gates.

Planning authority: `eth-macro-research/docs/integrations/history-access-layer-v1.md` и `market-data-capability-resolution-v1.md`.

Qualification authority:

```text
D63_SOURCE_HEAD=76a09841dad36800525e599446ec93f91fa1524c
D63_LIVE_RUN=31957353588
D63_LIVE_JOB=95189884017
D63_LIVE_STATUS=SUCCESS
D63_SOURCE_REPOSITORY_CI_RUN=31957353590
D63_SOURCE_REPOSITORY_CI_STATUS=SUCCESS
D62_D63_TARGETED_TESTS=13/13 PASS
D63_RESOLVER_CONSUMER_QUALIFICATION=PASS
```

Branch-level CI является merge evidence в PR и не изменяет source-qualified identity выше.

## Source/storage audit

Текущий physical storage уже даёт достаточные authority primitives без нового catalog service или storage abstraction framework:

- `history/release-manifest.json` содержит exact COLD `asset_inventory`: `release_tag`, `asset_id`, `asset_name`, `browser_download_url`, `sha256`, size и timestamp boundaries;
- immutable COLD objects являются самостоятельными compact-JSON GitHub Release assets; v1 не repack-ит и не изобретает archive/member layout;
- WARM manifests объявляют semantic series, но не полный список partition paths;
- WARM physical catalog поэтому строится только как runtime derived scan фактически присутствующих JSON resources и проверяется по payload identity; filename/year/month/day не синтезируются;
- существующие release publisher и consumer proof остаются authority для publication/SHA/immutability contracts; D6 reader не импортирует write-oriented publisher path.

## Четыре hard guardrails

1. **`ResolutionPlan` является входной authority D6.2B.** `tools/history_access.py` не читает capability index или manifests и не выполняет повторный resolve.
2. **Catalog только derived.** Никакой `history-catalog.json`, новой БД или второго SSOT не создаётся.
3. **No guessed/hardcoded Release routes.** D6.2A копирует exact locator/asset/SHA только из canonical release manifest; WARM path берётся из physically discovered resource объявленной semantic family.
4. **WARM/COLD merge и integrity детерминированы.** Plan pin-ит SHA каждого segment, COLD cache доверяется только после SHA/size verification, WARM bytes также SHA-pinned, merge сортируется по timestamp, duplicate/gap не скрываются.

## D6.2A — semantic resolver

`tools/capability_index.py` сохраняет D6.1 `build|validate` и предоставляет:

```text
list
describe <series_id>
resolve <series_id> --from <UTC> --to <UTC> [--cutoff <UTC>] --format json
```

`resolve` выполняет только local reads. Provider API/Release download отсутствуют.

Выход — deterministic `market-data-resolution-plan/1.0.0` с SHA-256 самого plan и exact physical segments.

COLD precedence на уже опубликованном диапазоне устраняет intentional Release↔WARM overlap; WARM используется только после COLD covered boundary. Metadata coverage gap остаётся fail-closed.

Point-in-time cutoff консервативен: manifest, который с текущего checkout известен только после cutoff, не разрешается как future-known physical evidence.

## D6.2B — plan-only reader

`tools/history_access.py slice` принимает **только ResolutionPlan**:

```bash
python tools/history_access.py slice \
  --plan resolution-plan.json \
  --format csv \
  --output - \
  --mode strict
```

V1 materialization ограничена OHLCV series. D6.2A semantic discovery/resolution остаётся шире.

Reader:

```text
ResolutionPlan
→ verify plan digest
→ verified COLD read-through cache OR SHA-pinned WARM file
→ verify physical payload identity
→ normalize canonical OHLCV schemas
→ deterministic chronological merge
→ [start,end) slice
→ gap/duplicate/candle integrity diagnostics
```

Для canonical OHLCV timestamp reader поддерживает `open_time_ms` (spot) и `timestamp_ms` (Deribit perpetual). Это schema normalization, а не provider substitution.

### Strict/permissive

- `strict`: checksum mismatch, duplicate, gap, invalid candle → typed failure;
- `permissive`: gap/duplicate дают `STATUS=DEGRADED`, diagnostics сохраняют exact timestamps/counts.

Никакого synthetic gap fill или silent provider substitution.

## Cache

Cache — read-through only и не authority.

Identity:

```text
SHA256(browser_download_url + NUL + expected_asset_sha256)
```

Corrupt/partial cache entry не считается hit. Download сначала пишется во временный файл, проверяется по expected size/SHA-256 и только затем atomically rename-ится.

## D6.2 real COLD proof

Реальный immutable Binance Spot proof сохраняется как regression authority:

```text
SERIES_ID=spot.binance-spot.ETHUSDT.ohlcv.5m
RANGE=2022-06-18T00:00:00Z..2022-11-10T00:00:00Z
RESOLUTION_PLAN_SHA256=cdb2f905c63b936c907ef4613bb6f65eae23bf655ad0dac6de019a6cc5b49dc8
SOURCE_ASSET=binance--ETHUSDT--5m--2022.json
SOURCE_SHA256=6808c66e764028901c2eeda151f3d3706e616ff043d92022a0999436deb3e310
ROWS=41760/41760
GAP_COUNT=0
DUPLICATES=0
STRICT_INTEGRITY=PASS
VERIFIED_CACHE_REPLAY=PASS
REAL_2022_SLICE=PASS
```

Verified cache replay выполняется с network opener, который намеренно всегда падает.

## D6.3 qualification

### Capability contract

```text
CAPABILITY_SERIES_ID_UNIQUE=PASS
CAPABILITY_SOURCE_COVERAGE=PASS
CAPABILITY_NO_ORPHANS=PASS
CAPABILITY_PHYSICAL_RESOLUTION=PASS
CAPABILITY_NO_GUESSED_PATHS=PASS
CAPABILITY_POINT_IN_TIME_CUTOFF=PASS
CAPABILITY_COLD_HOT_SEAM=PASS
CAPABILITY_CONSUMER_PROOF=PASS
D63_FORWARD_ONLY_SEMANTICS=PASS
D63_BINANCE_USDM_DISABLED_SEMANTICS=PASS
D63_PROVIDER_LIMITED_SEMANTICS=PASS
D63_HOURLY_INDEX_REGENERATION_REQUIRED=false
```

Representative semantic resolver proof включает Binance Spot, Kraken Futures `PI_ETHUSD` funding/OI и Deribit DVOL. Forward-only options/liquidity не фабрикуются как historical backfill; `binance-usdm` не появляется в active series.

### Priority A/B/C/D acceptance

A — Binance Spot ETHUSDT 4h, `2022-06-01 → 2025-09-15`:

```text
D63_PRIORITY_FULL_RANGE=PASS
ROWS=7212
```

B — Binance Spot ETHUSDT 1h, тот же диапазон:

```text
D63_PRIORITY_FULL_RANGE=DEGRADED_EXPECTED_PROVIDER_HALT
ROWS=28847
GAP_COUNT=1
MISSING=2023-03-24T13:00:00Z
D63_PROVIDER_NATIVE_HALT_DIAGNOSTIC=PASS
```

Strict reader на этом gap по-прежнему fail-closed. D6.3 использует permissive mode только для full-range acceptance и принимает только exact единственный provider-native no-trading interval; данные не синтезируются.

C — Binance Spot ETHUSDT 5m, `2022-06-18 → 2022-11-10`:

```text
D63_PRIORITY_C_2022_M5=PASS
ROWS=41760
```

D — M5 pivot windows:

```text
2024-03-11T00:00:00Z..2024-03-13T00:00:00Z  576 rows  PASS
2024-12-15T00:00:00Z..2024-12-17T00:00:00Z  576 rows  PASS
2025-04-08T00:00:00Z..2025-04-10T00:00:00Z  576 rows  PASS
2025-08-23T00:00:00Z..2025-08-25T00:00:00Z  576 rows  PASS
```

### Cross-timeframe reconciliation

На `2024-03-11T00:00:00Z..2024-03-13T00:00:00Z` M5 агрегируется детерминированно и exact сравнивается с native higher timeframe по open/high/low/close/volume:

```text
D63_M5_TO_H1=PASS
D63_M5_TO_H4=PASS
```

### Physical COLD/WARM seam

Текущий checkout имеет intentional overlap, в котором immutable COLD новее WARM tail. Resolver применяет COLD precedence и qualification сравнивает overlap rows с WARM bytes:

```text
D63_PHYSICAL_SEAM_MODE=COLD_PRECEDENCE_OVER_VERIFIED_OVERLAP
D63_PHYSICAL_SEAM_MATCHED_ROWS=12
CAPABILITY_COLD_HOT_SEAM=PASS
```

Synthetic mixed COLD→WARM continuation отдельно покрыт adversarial test и остаётся deterministic.

### Multi-provider reader

```text
D63_MULTI_PROVIDER_READER=PASS series_id=spot.kraken-spot.ETHUSD.ohlcv.1h
D63_MULTI_PROVIDER_READER=PASS series_id=derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h
```

Deribit qualification обнаружил и закрыл source defect: canonical perpetual OHLCV uses `timestamp_ms`; regression test фиксирует эту форму.

## Что остаётся после D6.3

Следующий gate — **D6.4 activation**. До отдельного activation change capability index/resolver всё ещё не является public production route.

Не изменены D6.3:

- `bridge-contract.json`;
- hourly collector/cadence;
- provider acquisition;
- immutable Releases;
- COLD packaging;
- Research production routing;
- Macro Watch;
- server/runtime.

D6.5 Research migration выполняется только после отдельного D6.4 activation/consumer proof.