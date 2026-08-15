# eth-macro-data-bridge

Публичный read-only мост рыночных данных для ETH Macro Watch, воспроизводимых event studies и последующего point-in-time research.

Канонический язык пользовательской и архитектурной документации репозитория — **русский**. Машинные идентификаторы, API/JSON fields, schema/status names и CI markers сохраняют исходные технические имена. Правила работы находятся в [`AGENTS.md`](AGENTS.md).

## Канонические точки входа

- **Контракт для consumers:** `bridge-contract.json`
- **LIVE:** `data/manifest.json`
- **CLOSED M5 ARCHIVE:** `archive/manifest.json`
- **DEEP/HISTORY:** `history/manifest.json`
- **EVENTS:** `events/manifest.json`
- **DERIVATIVES:** `derivatives/manifest.json`
- **OPTIONS:** `options/manifest.json`
- **LIQUIDITY:** `liquidity/manifest.json`
- **DERIVED ANALYTICS:** `analytics/manifest.json`

Consumer сначала читает `bridge-contract.json` и только затем разрешает объявленные canonical paths. Угадывать provider paths запрещено.

## Архитектура данных

Иерархия authority:

`SPOT → DERIVATIVES → OPTIONS → LIQUIDITY → DERIVED ANALYTICS`

Provider files сохраняют raw/native facts. `analytics/` содержит детерминированную производную интерпретацию. Raw не заменяется derived output, а разные providers не усредняются и не подменяются молча.

### HOT / rolling

Backward-compatible rolling слой находится в:

```text
data/{provider}/{symbol}/{interval}.json
```

Он содержит компактные 5m/15m/1h/4h/1d окна. Текущая candle может иметь `closed=false`. Rolling value старше consumer freshness threshold не используется как свежий live факт.

Для Binance сейчас поддерживаются расширенные окна:

- 5m — 3000 candles;
- 15m — 3000;
- 1h — 2000;
- 4h — 1000;
- 1d — 730.

### CLOSED append-only M5 archive

Canonical archive v3.1 хранит только CLOSED M5 candles, partitioned по UTC:

```text
archive/YYYY/MM/DD/{provider}/{symbol}-5m.json
```

Existing `(provider, symbol, interval, open_time_ms)` record не переписывается молча. Conflict создаёт reconciliation evidence и должен остановить validation.

Binance сохраняет OHLC плюс `base_volume`, `close_time_ms`, `quote_volume`, `trade_count`, `taker_buy_base_volume`, `taker_buy_quote_volume`. Эти taker поля — spot aggressive-flow proxy, а не liquidation или futures CVD.

Kraken Spot сохраняет OHLC, VWAP, volume и trade count; provider-current/uncommitted OHLC row не архивируется как closed history.

Higher timeframes строятся детерминированно из canonical closed M5 с UTC-aligned buckets там, где это объявлено контрактом.

### WARM / historical products

`history/` и domain history manifests индексируют bounded/reproducible historical products. Git не должен превращаться в бесконечную market-data database.

### COLD / max-available deep history

Максимально доступная история публикуется как deterministic immutable GitHub Release assets:

```text
bridge-contract.json
  → history/manifest.json
  → history/release-manifest.json
  → immutable GitHub Release asset
```

Git tree остаётся hot/control plane. Deep-history workflow manual-only и не входит в hourly collector.

Publication contour использует:

`acquire remote once → freeze source → Build A → frozen replay Build B → asset integrity → Git overlap policy → immutable Release → remote SHA readback → control-plane manifests → consumer proof`.

## Market-intelligence domains

- `derivatives/` — Kraken Futures historical/native analytics + Deribit perpetual current state. Binance USDⓈ-M live collection остаётся `DISABLED_BY_POLICY`.
- `options/` — Deribit ETH option surface, Greeks/IV/skew/term structure и DVOL там, где provider history реально доступна.
- `liquidity/` — provenance-labelled order-book snapshots, spread/depth/imbalance/slippage.
- `analytics/` — deterministic derived state с явными provider labels.
- `events/` — explicit event definitions/reconstruction; система не придумывает события автоматически.

Binance USDⓈ-M canonical policy:

```text
CURRENT_COLLECTION=DISABLED_BY_POLICY
EXISTING_ARCHIVE=FROZEN_HISTORICAL_REFERENCE
ARCHIVE_CONTINUOUSLY_ACCUMULATED=false
ARCHIVE_CURRENTLY_UPDATED=false
SIGNAL_VOTE=EXCLUDED
NETWORK_CALLS=0
```

Его нельзя silently активировать через другой runtime/VPS без явного изменения `bridge-contract.json`.

## Event snapshots и burst

`src/event_window.py` регистрирует explicit machine-readable event definition и восстанавливает PRE/release/post checkpoints только из уже архивированных данных. Missing points не интерполируются.

Manual-only `Event market-data burst` может временно собирать bounded snapshots вокруг явного события. Он не меняет baseline hourly policy.

## Расписание и freshness

Baseline workflow объявлен hourly на `:35`, однако GitHub Actions scheduler может запускать его с jitter. Поэтому downstream consumer не должен быть связан с фиксированным «через N минут после :35».

Правильный downstream gate:

`new bridge revision → manifest generated_at → provider health/freshness → qualified state → analysis → notification only on material change`.

Collection cadence, analysis cadence и notification cadence — разные вещи.

## Структура репозитория

```text
AGENTS.md
README.md
.gitmessage.txt
bridge-contract.json
contracts/
docs/
src/
tools/
tests/
.github/workflows/

# public data/control planes
data/
archive/
history/
derivatives/
options/
liquidity/
analytics/
events/
```

Python scripts, tests и отдельные semantic notes не должны возвращаться в root.

### Source

```text
src/archive.py
src/backfill.py
src/collector.py
src/event_burst.py
src/event_window.py
src/intelligence.py
```

### Tools

```text
tools/deep_history/
tools/qualification/
tools/validation/
```

### Contracts и semantics

- `bridge-contract.json` — стабильный внешний contract entrypoint;
- `contracts/provider-contracts.json` — machine-readable provider/API contracts;
- `derivatives/metric-semantics.json` — versioned semantics Kraken Futures metrics;
- `docs/semantics/kraken-futures-cvd.md` — человекочитаемый CVD contract.

## Локальный запуск

Linux/macOS:

```bash
export PYTHONPATH="src:tools/deep_history"
python src/collector.py
python tools/validation/validate.py
python tools/validation/validate_v4.py
python tools/validation/validate_history.py
python tools/validation/consumer_proof.py
```

PowerShell:

```powershell
$env:PYTHONPATH = 'src;tools/deep_history'
python src/collector.py
python tools/validation/validate.py
```

Repeated-run qualification запускается отдельно и не должна добавлять второй production collection в scheduled run.

## Deep-history diagnostics

Если Release/Git overlap обнаруживает unknown mismatch, сначала выполняется targeted probe/qualification; полный max-history acquisition повторяется только после классификации причины и regression guard.

Текущий Kraken contour различает:

- strict immutable overlap metrics;
- versioned window-anchored CVD semantics;
- provider-revisable snapshot families, если это отдельно доказано и закреплено contract/evidence;
- unknown mismatch → fail closed.

## Коммиты

В корне находится каноничный двуязычный шаблон `.gitmessage.txt`.

```bash
git config commit.template .gitmessage.txt
```

Subject — короткий Conventional Commit-style английский заголовок. Тело обязательно содержит смысловые секции `RU:` и `EN:` плюс фактическую `Validation / Проверка:` для code/data-contract изменений.

Полные правила — в `AGENTS.md`.
