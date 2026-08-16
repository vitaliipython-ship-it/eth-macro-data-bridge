# Semantic contract: Market Data Capability Index v1

## Статус

`D6.1 IMPLEMENTATION CANDIDATE / NOT YET PUBLIC ROUTE`

Этот документ описывает implementation contract `history/capability-index.json`.

До D6.4 capability index **не объявлен** в `bridge-contract.json` и поэтому не является публичным consumer entrypoint. Канонический production-маршрут остаётся `bridge-contract.json → declared manifests`.

## Назначение

Capability index — компактная machine-readable плоскость semantic discovery. Он позволяет агенту/инженеру узнать:

- какие исторические series опубликованы;
- какой provider/domain/instrument/metric они представляют;
- какая роль authority у provider;
- является история `MAX_AVAILABLE` или `PROVIDER_LIMITED`;
- существует ли совместимый HOT/WARM tail;
- через какой manifest должна выполняться дальнейшая physical resolution;
- какие capability существуют только как forward snapshots;
- какие provider policies запрещают current collection/signal use.

Index **не хранит market-data rows, asset inventory, точные first/last timestamps или текущие цены**.

## Architecture gate

### 1. Какой реальный риск закрывает механизм?

Без компактной semantic discovery плоскости следующий агент вынужден заново читать большие manifests/Release inventory, выводить provider roles и вручную связывать COLD history с HOT tail. Это создаёт path guessing, повторную работу и риск silent provider substitution.

### 2. Можно ли закрыть проще?

Документация `AGENTS.md` + `bridge-contract.json` уже объясняет правильный маршрут, но не даёт дешёвого machine-readable inventory. Новый DB/API/service не нужен. Минимальный достаточный механизм — один derived JSON index + один deterministic offline builder/validator.

### 3. Уменьшает ли решение число действий?

Да. Discovery становится одним чтением compact index. Точная physical resolution выполняется только когда реально нужен конкретный time range. Consumers не сканируют GitHub Releases и не строят provider paths самостоятельно.

## Authority hierarchy

```text
bridge-contract.json
  │
  ├── provider/policy authority
  │
  └── declared manifests
          │
          ├── history/release-manifest.json   ← COLD physical inventory
          ├── domain history manifests        ← HOT/WARM state
          │
          └── immutable Release/Git bytes
```

D6.1 candidate:

```text
canonical manifests
      │
      ▼
tools/capability_index.py build
      │
      ▼
history/capability-index.json
```

Capability index — **derived materialized index**, а не новый source of truth.

## Stable `series_id`

Grammar v1:

```text
<domain>.<provider_id>.<instrument>.<series>[.<interval>]
```

Примеры:

```text
spot.binance-spot.ETHUSDT.ohlcv.1h
spot.kraken-spot.ETHUSD.ohlcv.1d
derivatives.kraken-futures.PI_ETHUSD.funding
derivatives.kraken-futures.PI_ETHUSD.cvd
derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h
options.deribit-options.ETH.dvol.1h
```

`provider_id` берётся из `contracts/provider-contracts.json`. Physical provider name из Release manifest сохраняется отдельно как `source_provider`.

`series_id` не выводится потребителем из filename и не содержит year partition, asset URL или Release asset name.

## Compact profiles

Повторяющиеся provider/history/HOT-route semantics вынесены в `profiles`, а `series` хранит только stable identity и ссылку `profile_id`. Это сокращает index и не дублирует один и тот же route десятки раз.

## Discovery vs resolution

```text
DISCOVERY != RESOLUTION != CONSUMPTION
```

### Discovery

Читается `history/capability-index.json`.

Index хранит `history_mode`:

- `MAX_AVAILABLE`;
- `PROVIDER_LIMITED`;
- `FORWARD_ONLY`;
- `FROZEN_REFERENCE`;
- `UNAVAILABLE`.

Точные временные границы намеренно не копируются.

### Resolution

Точный диапазон, Release asset и SHA-256 разрешаются через profile `cold_manifest_path` + Release `source_provider` и series `source_interval_or_metric`.

В D6.1 resolver ещё не реализован. `list/describe/resolve` относятся к D6.2.

### Consumption

Consumer читает только resolved physical resources. Research сохраняет exact bridge commit + manifest/release/asset/SHA provenance по своему contract.

## HOT tail semantics

`hot_manifest_path != null` означает только наличие declared compatible manifest route для той же semantic family.

Это **не** означает, что COLD и HOT имеют одинаковую retention/depth.

Например, immutable Deribit perpetual `OHLCV-1h` существует в COLD history, но текущий repository не имеет эквивалентного versioned OHLCV-1h hot-history product. Поэтому его profile имеет `hot_manifest_path=null`. Не подменять этот gap текущим ticker state.

## Forward-only capability

Исторические options surface и historical order book не фабрикуются.

Index отдельно фиксирует:

- `options.deribit-options.ETH.surface-snapshots` → `FORWARD_ONLY`;
- `liquidity.orderbook-snapshots` → `FORWARD_ONLY`.

Их точное текущее состояние разрешается через соответствующий manifest.

## Binance USDⓈ-M

`binance-usdm` остаётся provider policy:

```text
STATUS=DISABLED_BY_POLICY
CURRENT_COLLECTION=DISABLED_BY_POLICY
NETWORK_CALLS=0
SIGNAL_VOTE=EXCLUDED
```

Frozen historical reference не превращается в active series и не получает signal eligibility через capability index.

## Determinism

`tools/capability_index.py build`:

- делает только local file reads;
- не вызывает provider API;
- не скачивает Release assets;
- игнорирует hourly `generated_at`, current price и rolling timestamps;
- выводит stable identities/routes/policies;
- одинаковые canonical inputs → byte-identical `history/capability-index.json`.

`validate` пересобирает index in-memory и требует byte-equivalent canonical JSON.

## Команды D6.1

```bash
python tools/capability_index.py build
python tools/capability_index.py validate
python -m unittest tests.deep_history.test_capability_index -v
```

Обычный hourly collector не запускает `build`.

## Что D6.1 не меняет

- `.github/workflows/update-market.yml`;
- `.github/workflows/publish-deep-history.yml`;
- provider acquisition;
- immutable Releases;
- `bridge-contract.json`;
- Research consumer policy;
- market-data rows.

## Activation gates

D6.1 считается qualified только после:

1. deterministic build regression PASS;
2. schema/shape validation PASS;
3. provider-policy inheritance PASS;
4. disabled-provider leakage = 0;
5. forward-only semantics PASS;
6. existing Data Bridge repository/data/history/consumer tests PASS.

После D6.1:

- D6.2 — `list/describe/resolve`;
- D6.3 — extended consumer qualification;
- D6.4 — только после qualification объявить capability path в `bridge-contract.json`;
- D6.5 — затем перевести Research routing contract на новый semantic route.

До D6.4 consumer продолжает начинать с текущего `bridge-contract.json`.
