# AGENTS.md

## Назначение

Это **первая и каноническая semantic точка входа** для любого человека или агента, который читает, анализирует или изменяет `eth-macro-data-bridge`. Не начинать с guessed provider path, Release asset или отдельного domain-файла без прохождения route authority.

Репозиторий — публичный read-only Data Bridge для ETH Macro Watch. Он собирает, нормализует, архивирует и публикует рыночные факты. Интерпретация рынка, гипотезы, сценарии и модели принадлежат `eth-macro-research` и не должны переноситься сюда.

## Язык репозитория

**Канонический язык документации, архитектурных комментариев, PR/issue-описаний и сообщений для человека — русский.** Machine identifiers, API endpoints, schema/status/metric names, пути и команды не переводятся.

## Канонический semantic route после D6.4

Для discovery/consumption не сканировать repository tree и не угадывать storage layout.

```text
AGENTS.md
  → bridge-contract.json
  → canonical_paths.capability_index
  → history/capability-index.json
  → tools/capability_index.py list|describe|resolve
  → ResolutionPlan
  → canonical physical manifest/resource
  → tools/history_access.py slice
  → verified Git WARM / immutable Release bytes
```

Правила:

1. `bridge-contract.json` — единственная route/provider-policy authority.
2. `history/capability-index.json` — public **derived discovery index**, но не byte authority.
3. Exact physical depth/assets/URL/SHA принадлежат manifests/Releases.
4. Resolver не строит provider paths или Release URLs самостоятельно.
5. D6.2B reader принимает только validated `ResolutionPlan` и не повторяет resolution.
6. Legacy manifest route после D6.4 остаётся `SUPPORTED_BACKWARD_COMPATIBLE`; удалять его без отдельной migration policy запрещено.
7. Для task из `eth-macro-research` сначала соблюдать Research `AGENTS.md`, затем при переходе сюда начинать с этого файла и `bridge-contract.json`.

## Каноничная структура

```text
README.md                    — русскоязычное описание и навигация
AGENTS.md                    — правила работы с репозиторием
.gitmessage.txt              — обязательный двуязычный шаблон коммита
bridge-contract.json         — публичный route/provider-policy entrypoint
contracts/                   — provider/semantic contracts
src/                         — production collectors/builders
tools/
  capability_index.py        — semantic discovery + read-only resolver
  history_access.py          — ResolutionPlan-only historical materializer
  deep_history/              — cold-history publisher, overlap policy, probes
  qualification/             — repeated-run/idempotence qualification
  validation/                — validators и consumer proof
tests/
  deep_history/              — deep-history/capability/history-access tests
docs/
  semantics/                 — человекочитаемые semantic contracts
```

Data/control entrypoints (`data/`, `archive/`, `history/`, `derivatives/`, `options/`, `liquidity/`, `analytics/`, `events/`) остаются на верхнем уровне намеренно как часть публичного data contract.

## Authority и invariants

1. Не угадывать canonical paths; получать их из `bridge-contract.json`/declared manifests.
2. Raw/provider-native facts не заменяются derived analytics.
3. Providers не усредняются и не подменяются молча.
4. Binance USDⓈ-M остаётся `DISABLED_BY_POLICY`, пока policy явно не изменён.
5. Closed historical records и live/open preview имеют разные semantics.
6. Git — HOT/WARM/control plane; max-available deep history — immutable GitHub Release assets.
7. Deep-history publisher использует `ACQUIRE_REMOTE_ONCE_THEN_FROZEN_REPLAY`.
8. Release/Git overlap fail-closed; semantic exceptions только через versioned metric contract + regression evidence.
9. Нельзя silently rewrite append-only historical evidence.
10. Любое изменение публичных routes требует explicit consumer proof.
11. Capability discovery не становится вторым source of truth.
12. Никаких synthetic gap fills или silent provider fallback.

## D6 semantic capability/history-access contour

```text
schema/capability-index.schema.json
        ↓
tools/capability_index.py build|validate|list|describe|resolve
        ↓
history/capability-index.json
        ↓
market-data-resolution-plan/1.0.0
        ↓
tools/history_access.py slice
        ↓
verified COLD/WARM bytes
```

Ключевые правила:

- stable `series_id` не зависит от filename/year/URL/storage backend;
- точные first/last timestamps и asset inventory не копируются в capability index;
- provider roles/status берутся из `bridge-contract.json`;
- COLD physical inventory остаётся в `history/release-manifest.json`;
- WARM/HOT state остаётся в declared domain manifests;
- catalog runtime-derived, persistent competing catalog запрещён;
- Release locator/SHA только manifest-driven;
- WARM/COLD bytes SHA-pinned, merge deterministic, gap/duplicate явные;
- canonical OHLCV timestamp normalization поддерживает `open_time_ms` и `timestamp_ms` без изменения provider identity;
- обычный hourly collector не перестраивает capability index.

Lifecycle/planning authority: `eth-macro-research/docs/integrations/market-data-capability-resolution-v1.md` и `history-access-layer-v1.md`.

## D6 status

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=QUALIFIED/PASS
D6.5=PENDING/NEXT
```

D6.3 source qualification:

```text
SOURCE_HEAD=76a09841dad36800525e599446ec93f91fa1524c
LIVE_RUN=31957353588 SUCCESS
LIVE_JOB=95189884017 SUCCESS
REPOSITORY_CI_RUN=31957353590 SUCCESS
TARGETED_TESTS=13/13 PASS
M5_TO_H1=PASS
M5_TO_H4=PASS
CAPABILITY_COLD_HOT_SEAM=PASS
CAPABILITY_CONSUMER_PROOF=PASS
```

D6.4 activation qualification:

```text
QUALIFIED_SOURCE_HEAD=f90215c6581b2157a219f55d7aba9ecef5bf10b2
QUALIFICATION_RUN=31962611123 SUCCESS
QUALIFICATION_JOB=95202800848 SUCCESS
BRIDGE_CONTRACT_VERSION=1.1.0
CAPABILITY_ROUTE_DECLARED=PASS
CAPABILITY_INDEX_READ=PASS
LEGACY_MANIFEST_ROUTE=PASS
CAPABILITY_RESOLUTION=PASS
RESOLUTION_PLAN_AUTHORITY=PASS
CAPABILITY_NO_GUESSED_PATHS=PASS
RELEASE_ASSET_DOWNLOAD=PASS
RELEASE_ASSET_SHA256=PASS
RELEASE_TO_HOT_TAIL_SEAM=PASS
NO_PROVIDER_SUBSTITUTION=PASS
CAPABILITY_CONSUMER_PROOF=PASS
CONSUMER_PROOF=PASS
DEEP_HISTORY_TESTS=PASS
```

Первый D6.4 run `31962567844` прошёл весь network-backed consumer proof, но корректно упал на stale test, который ещё требовал pre-activation state. Assertion обновлён на active-route regression; resolver/reader/provider-policy criteria не ослаблялись.

## Четыре hard guardrails

1. `ResolutionPlan` — input authority reader-а; второго `HistoryResolver` внутри D6.2B быть не должно.
2. Catalog — только derived projection, не новый SSOT.
3. Никаких guessed/hardcoded Release routes; exact locator/SHA идут из canonical physical authority.
4. WARM/COLD merge и integrity должны оставаться доказуемыми и deterministic.

## Provider/history semantics

`history_mode`:

```text
MAX_AVAILABLE
PROVIDER_LIMITED
FORWARD_ONLY
FROZEN_REFERENCE
UNAVAILABLE
```

Historical options surface/order book не фабрикуются. Binance USDM frozen reference не становится active/signal-eligible.

Binance H1 `2023-03-24T13:00:00Z` — доказанный provider-native no-trading gap: strict reader fail-closed; synthetic candle запрещён.

## D6.4 activation boundary

D6.4 активировал только Data Bridge route:

- `bridge-contract.json` теперь объявляет `canonical_paths.capability_index`;
- `semantic_resolution.status=ACTIVE`;
- legacy manifests явно backward-compatible;
- existing `consumer_proof.py` проходит bridge → capability → resolver → physical manifest → Release verification;
- `bridge-contract.json` включён в repository-validation path trigger.

D6.4 **не менял** Research routing, collector/cadence, provider acquisition, immutable Releases, COLD packaging, market-data rows, server/runtime или Macro Watch.

Следующий gate — **D6.5 Research migration**. Не изменять Research routing в этом репозитории и не считать D6.5 выполненным автоматически.

## Выполнение Python

Linux/macOS validation environment:

```bash
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python tools/capability_index.py list
python tools/capability_index.py describe spot.binance-spot.ETHUSDT.ohlcv.5m
```

Resolution:

```bash
python tools/capability_index.py resolve \
  spot.binance-spot.ETHUSDT.ohlcv.5m \
  --from 2022-06-18T00:00:00Z \
  --to 2022-11-10T00:00:00Z \
  --format json > resolution-plan.json
```

Reader принимает сохранённый plan:

```bash
python tools/history_access.py slice \
  --plan resolution-plan.json \
  --format csv \
  --output - \
  --mode strict
```

PowerShell:

```powershell
$env:PYTHONPATH = 'src;tools/deep_history'
python tools/capability_index.py validate
```

## Deep-history contour

Перед новым full acquisition:

1. unit/adversarial tests;
2. targeted provider probe при неизвестном overlap conflict;
3. live overlap policy qualification;
4. только затем full `Publish deep history`.

D6 route changes сами по себе не являются причиной повторять D5/full acquisition.

## Architecture gate

Перед новым механизмом ответить:

1. Какой реальный риск он закрывает?
2. Можно ли закрыть его проще?
3. Уменьшает ли решение число действий для следующего агента/инженера?

Если риск не доказан, проще уже достаточно или ручная работа растёт — механизм по умолчанию не добавляется.

## Коммиты

Использовать корневой `.gitmessage.txt`:

- короткий Conventional Commit-style Subject на английском;
- эквивалентные секции `RU:` и `EN:`;
- для code/data-contract изменений `Validation / Проверка:`;
- не писать process-noise (`rework`, `again`, revision labels и т. п.) в Subject.

## Перед завершением изменения

Минимум:

```bash
python -m compileall -q src tools tests
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Network-backed D6.3 historical materialization qualification остаётся отдельным workflow; D6.4 route changes проверяются обычным repository validation, включая existing network-backed consumer proof.
