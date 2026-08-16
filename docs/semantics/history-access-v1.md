# D6.2 Historical Data Access v1 — bounded qualification

## Статус

`D6.2A + D6.2B BOUNDED QUALIFIED / PASS / NOT YET PUBLIC ROUTE`

Эта реализация продолжает qualified D6.1 и **не активирует** capability path в `bridge-contract.json`. Полная D6.3 multi-provider/cross-timeframe qualification, D6.4 activation и D6.5 Research migration остаются отдельными последующими gates.

Planning authority: `eth-macro-research/docs/integrations/history-access-layer-v1.md` и `market-data-capability-resolution-v1.md`.

Bounded qualification authority:

```text
QUALIFICATION_SOURCE_HEAD=a9a07a5e887a619c084ca487915bcd397ae4e590
REPOSITORY_CI_RUN=31956573531
REPOSITORY_CI_STATUS=SUCCESS
LIVE_2022_RUN=31956573550
LIVE_2022_JOB=95188010147
LIVE_2022_STATUS=SUCCESS
D62_ADVERSARIAL_TESTS=12/12 PASS
D62_REAL_2022_SLICE=PASS
```

## Source/storage audit

Текущий physical storage уже даёт достаточные authority primitives без нового catalog service или storage abstraction framework:

- `history/release-manifest.json` содержит exact COLD `asset_inventory`: `release_tag`, `asset_id`, `asset_name`, `browser_download_url`, `sha256`, size и timestamp boundaries;
- immutable COLD objects фактически являются самостоятельными compact-JSON GitHub Release assets, поэтому v1 не repack-ит и не изобретает archive/member layout;
- WARM manifests объявляют semantic series, но не полный список partition paths;
- поэтому WARM physical catalog строится только как runtime derived scan фактически присутствующих JSON resources и проверяется по payload identity; filename/year/month/day не синтезируются;
- существующие release publisher и consumer proof уже подтверждают SHA-256/immutability/overlap contracts; D6.2 использует те же manifest facts, но не импортирует write-oriented publisher path.

## Четыре hard guardrails

1. **`ResolutionPlan` является входной authority D6.2B.** `tools/history_access.py` не читает capability index или manifests и не выполняет повторный resolve.
2. **Catalog только derived.** Никакой `history-catalog.json`, новой БД или второго SSOT не создаётся.
3. **No guessed/hardcoded Release routes.** D6.2A копирует exact locator/asset/SHA только из canonical release manifest; WARM path берётся из physically discovered resource, объявленной semantic family.
4. **WARM/COLD merge и integrity детерминированы.** Plan pin-ит SHA каждого segment, COLD cache доверяется только после SHA/size verification, WARM bytes также SHA-pinned, merge сортируется по `open_time`, duplicate/gap не скрываются.

## D6.2A

`tools/capability_index.py` сохраняет D6.1 `build|validate` и добавляет:

```text
list
describe <series_id>
resolve <series_id> --from <UTC> --to <UTC> [--cutoff <UTC>] --format json
```

`resolve` выполняет только local reads. Provider API/Release download отсутствуют.

Выход — deterministic `market-data-resolution-plan/1.0.0` с SHA-256 самого plan и exact physical segments.

COLD precedence на уже опубликованном диапазоне устраняет intentional Release↔WARM overlap; WARM используется только после COLD covered boundary. Metadata coverage gap остаётся fail-closed.

Point-in-time cutoff консервативен: manifest, который с текущего checkout известен только после cutoff, не разрешается как future-known physical evidence.

## D6.2B

`tools/history_access.py slice` принимает **только ResolutionPlan**:

```bash
python tools/history_access.py slice \
  --plan resolution-plan.json \
  --format csv \
  --output - \
  --mode strict
```

V1 materialization ограничена OHLCV series. Это соответствует первому blocking consumer — historical lower-TF wave analysis. D6.2A semantic discovery/resolution остаётся шире.

Reader:

```text
ResolutionPlan
→ verify plan digest
→ verified COLD read-through cache OR SHA-pinned WARM file
→ verify physical payload identity
→ normalize OHLCV
→ deterministic chronological merge
→ [start,end) slice
→ gap/duplicate/candle integrity diagnostics
```

CSV payload идёт в stdout/output file; machine diagnostics — отдельно в stderr.

### Strict/permissive

- `strict`: checksum mismatch, duplicate, gap, invalid candle → typed failure;
- `permissive`: gap/duplicate дают `STATUS=DEGRADED`, при этом diagnostics сохраняют exact timestamps/counts.

Никакого synthetic gap fill или silent provider substitution.

## Cache

Cache read-through only и не authority.

Identity:

```text
SHA256(browser_download_url + NUL + expected_asset_sha256)
```

Corrupt/partial cache entry не считается hit. Download сначала пишется во временный файл, проверяется по expected size/SHA-256 и только затем atomically rename-ится.

## Adversarial qualification

Targeted D6.2 suite доказал `12/12 PASS`:

- semantic `list/describe`;
- exact manifest-driven COLD resolution;
- WARM path discovery на намеренно нестандартном filename, чтобы исключить path templating;
- byte-identical repeated ResolutionPlan;
- point-in-time future-known rejection;
- reader работает без capability/manifests, имея только plan + physical resource;
- mixed COLD→WARM deterministic merge;
- corrupt cache re-fetch;
- checksum mismatch fail-closed;
- strict gap failure / permissive degradation;
- duplicate failure;
- plan tampering invalidates plan digest.

## Реальный COLD proof — priority use-case C

Bounded live workflow физически разрешил и прочитал immutable Binance Spot history:

```text
SERIES_ID=spot.binance-spot.ETHUSDT.ohlcv.5m
RANGE=2022-06-18T00:00:00Z..2022-11-10T00:00:00Z
RESOLUTION_PLAN_SHA256=cdb2f905c63b936c907ef4613bb6f65eae23bf655ad0dac6de019a6cc5b49dc8
COLD_SEGMENT_COUNT=1
SOURCE_ASSET=binance--ETHUSDT--5m--2022.json
SOURCE_SHA256=6808c66e764028901c2eeda151f3d3706e616ff043d92022a0999436deb3e310
ROWS=41760
EXPECTED_ROWS=41760
GAP_COUNT=0
DUPLICATES=0
STRICT_INTEGRITY=PASS
VERIFIED_CACHE_REPLAY=PASS
REAL_2022_SLICE=PASS
```

Второй materialization того же plan выполнялся с network opener, который намеренно всегда падает; success доказывает, что immutable asset повторно использован только через verified cache path.

## Что остаётся после bounded D6.2 qualification

Это **не полный D6.3 PASS**. До D6.4 activation ещё требуются:

- representative M5→H1 и M5→H4 reconciliation;
- representative positive resolution/consumption для других semantic provider families, где это применимо;
- combined resolver+reader consumer proof и adversarial seam qualification в объёме D6.3;
- только после этого — отдельное решение об объявлении capability route в `bridge-contract.json`.

Не изменяются:

- `bridge-contract.json`;
- hourly collector/cadence;
- provider acquisition;
- immutable Releases;
- COLD packaging;
- Research production routing;
- Macro Watch;
- server/runtime.
