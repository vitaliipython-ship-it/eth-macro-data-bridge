# AGENTS.md

## Назначение

Это **первая и каноническая semantic точка входа** для любого человека или агента, который читает, анализирует или изменяет `eth-macro-data-bridge`. Не начинать с guessed provider path, Release asset или отдельного domain-файла без прохождения route authority.

Репозиторий — публичный read-only Data Bridge для ETH Macro Watch. Он собирает, нормализует, архивирует и публикует рыночные факты. Интерпретация рынка, гипотезы, сценарии и модели принадлежат `eth-macro-research` и не должны переноситься сюда.

## Язык репозитория

**Канонический язык документации, комментариев к архитектурным решениям, PR/issue-описаний и сообщений для человека — русский.**

Допускаются и не переводятся, когда это часть машинного контракта или общепринятого технического интерфейса:

- имена Python/JSON/YAML полей;
- API endpoints и provider-native названия;
- schema/status/metric identifiers (`PASS`, `DEGRADED`, `DISABLED_BY_POLICY`, `open-interest` и т. п.);
- имена файлов/каталогов и shell/Python команды;
- CI evidence markers;
- английская зеркальная часть commit message по обязательному двуязычному шаблону.

Новые narrative-документы на другом естественном языке без явной причины не добавлять. Существующая пользовательская документация при изменении переводится на русский.

## Минимальный semantic route агента

Для discovery/consumption не сканировать весь repository tree и не угадывать storage layout.

Текущий production route до D6.4:

```text
AGENTS.md
  → bridge-contract.json
  → canonical path / manifest, объявленный contract
  → конкретный provider / instrument / interval-or-metric
  → Git resource ИЛИ immutable Release asset
```

Правила:

1. `AGENTS.md` задаёт semantic boundaries и читается один раз при входе в репозиторий/новую задачу.
2. `bridge-contract.json` — единственная route/provider-policy authority для consumer discovery. Старые research refs, README-примеры и знание layout не являются route authority.
3. Manifest разрешает physical resource. Не строить provider path/Release URL самостоятельно.
4. `history/capability-index.json` в D6.1 — staged derived discovery index. До D6.4 не hard-code-ить его как public entrypoint.
5. После D6.4 activation маршрут должен оставаться `AGENTS.md → bridge-contract.json → capability discovery/resolver → physical manifest/resource`; `bridge-contract.json` не обходится.
6. Exact physical depth/assets/SHA принадлежат manifests/Releases, а не semantic index.
7. Для agent task, который пришёл из `eth-macro-research`, сначала соблюсти его `AGENTS.md`, затем при переходе сюда начать с этого файла и route authority выше.

## Каноничная структура

```text
README.md                    — русскоязычное описание и навигация
AGENTS.md                    — правила работы с репозиторием
.gitmessage.txt              — обязательный двуязычный шаблон коммита
bridge-contract.json         — стабильный публичный consumer entrypoint
contracts/                   — provider/semantic contracts
src/                         — production collectors/builders
  archive.py
  backfill.py
  collector.py
  event_burst.py
  event_window.py
  intelligence.py
tools/
  capability_index.py        — D6 capability discovery + read-only semantic resolver
  history_access.py          — D6.2B plan-only historical materializer
  deep_history/              — cold-history publisher, overlap policy, probes
  qualification/             — repeated-run/idempotence qualification
  validation/                — validators и consumer proof
tests/
  deep_history/              — tests для deep-history/release/capability/history-access contour
docs/
  semantics/                 — человекочитаемые semantic contracts
```

Data/control entrypoints (`data/`, `archive/`, `history/`, `derivatives/`, `options/`, `liquidity/`, `analytics/`, `events/`) остаются на верхнем уровне намеренно. Это часть публичного data contract, а не source clutter.

Не возвращать Python scripts, tests или отдельные semantic notes в корень.

## Authority и invariants

1. `bridge-contract.json` разрешает canonical consumer paths. Не угадывать пути.
2. Raw/provider-native facts не заменяются derived analytics.
3. Providers не усредняются и не подменяются молча.
4. Binance USDⓈ-M остаётся `DISABLED_BY_POLICY`, пока policy явно не изменён в bridge contract.
5. Closed historical records и live/open preview имеют разные semantics.
6. Git — hot/control plane. Max-available deep history публикуется immutable GitHub Release assets.
7. Deep-history publisher использует `ACQUIRE_REMOTE_ONCE_THEN_FROZEN_REPLAY`; две независимые live acquisitions не являются доказательством determinism.
8. Release/Git overlap остаётся fail-closed. Semantic exceptions разрешены только versioned metric contract + regression evidence.
9. Нельзя silently rewrite append-only historical evidence.
10. Любое изменение публичных путей требует явной migration/consumer proof.
11. Semantic discovery не становится вторым source of truth: exact physical depth/assets/SHA принадлежат manifests/Releases.

## D6 semantic capability contour

D6 развивает self-describing маршрут Data Bridge без нового warehouse/service.

Qualified D6.1 contract:

```text
schema/capability-index.schema.json
        ↓
tools/capability_index.py build|validate
        ↓
history/capability-index.json
        ↓
docs/semantics/capability-index.md
```

D6.2 bounded-qualified extension:

```text
tools/capability_index.py list|describe|resolve
        ↓
market-data-resolution-plan/1.0.0
        ↓
tools/history_access.py slice
        ↓
verified COLD/WARM bytes
        ↓
normalized [start,end) OHLCV + integrity diagnostics
```

Ключевые правила:

- `history/capability-index.json` — derived materialized discovery index, не market-data authority;
- provider roles/status берутся из `bridge-contract.json`;
- `contracts/provider-contracts.json` документирует provider/API endpoints и не подменяет bridge policy;
- COLD physical inventory остаётся в `history/release-manifest.json`;
- HOT/WARM current state остаётся в объявленных domain manifests;
- stable `series_id` не зависит от filename, year partition, Release asset URL или storage backend;
- точные `first_timestamp`/`last_timestamp`/asset inventory намеренно не копируются в capability index;
- `binance-usdm` не может попасть в active series;
- historical options surface/order book не фабрикуются и отражаются как forward-only capability;
- обычный hourly collector не перестраивает capability index;
- D6.2B принимает только validated `ResolutionPlan` и не повторяет semantic/physical resolution;
- history catalog остаётся runtime-derived projection, persistent competing catalog запрещён;
- Release asset locator/SHA берутся только из canonical release manifest, guessed/hardcoded route запрещён;
- WARM/COLD bytes SHA-pinned, merge deterministic, gap/duplicate не скрываются и не синтезируются.

**До D6.4 capability index/resolver не является публичным consumer route.** Consumer продолжает начинать только с `bridge-contract.json`. Не добавлять capability path в `bridge-contract.json` и не менять Research routing раньше соответствующего qualification gate.

Lifecycle и cross-repository planning authority находятся в `eth-macro-research/docs/integrations/market-data-capability-resolution-v1.md` и `history-access-layer-v1.md`.

## Historical Data Access Layer — D6.2 bounded qualified, not public

Source/storage audit подтвердил, что существующих canonical primitives достаточно: COLD `asset_inventory` уже содержит exact immutable GitHub Release locator/SHA, а WARM resource paths можно получать derived scan-ом фактически присутствующих resources внутри объявленной semantic family. Новый DB/catalog service/storage plugin framework не нужен.

Канонический Data Bridge contract: `docs/semantics/history-access-v1.md`.

Текущий bounded status:

```text
D6.1=QUALIFIED/PASS
D6.2A=BOUNDED_QUALIFIED/PASS
D6.2B=BOUNDED_QUALIFIED/PASS
D6.3=PENDING
D6.4=PENDING
D6.5=PENDING
```

Qualification evidence:

```text
SOURCE_HEAD=a9a07a5e887a619c084ca487915bcd397ae4e590
REPOSITORY_CI_RUN=31956573531 SUCCESS
LIVE_RUN=31956573550 SUCCESS
LIVE_JOB=95188010147 SUCCESS
ADVERSARIAL_TESTS=12/12 PASS
SERIES=spot.binance-spot.ETHUSDT.ohlcv.5m
RANGE=2022-06-18T00:00:00Z..2022-11-10T00:00:00Z
RESOLUTION_PLAN_SHA256=cdb2f905c63b936c907ef4613bb6f65eae23bf655ad0dac6de019a6cc5b49dc8
SOURCE_ASSET=binance--ETHUSDT--5m--2022.json
SOURCE_SHA256=6808c66e764028901c2eeda151f3d3706e616ff043d92022a0999436deb3e310
ROWS=41760/41760
GAP_COUNT=0
DUPLICATES=0
STRICT_INTEGRITY=PASS
VERIFIED_CACHE_REPLAY=PASS
```

Четыре hard guardrails обязательны для любого successor:

1. `ResolutionPlan` — input authority reader-а; не создавать второй `HistoryResolver` внутри D6.2B.
2. Catalog — только derived consumer projection, не новый SSOT.
3. Никаких guessed/hardcoded Release routes; exact locator/SHA идут из canonical physical authority.
4. WARM/COLD merge и integrity должны оставаться доказуемыми и deterministic.

Следующий gate — D6.3: representative multi-provider resolver+reader qualification и M5→H1/H4 reconciliation. До его PASS не активировать D6.4 и не мигрировать Research routing.

Запрещено обходить эти gates через direct provider fallback, silent provider substitution, synthetic gap fill, collector/cadence rewrite, COLD repack, DB/API/service/server runtime или перенос Elliott/NEoWave logic в Data Bridge.

## Выполнение Python

Из корня репозитория для validation/qualification использовать `PYTHONPATH=src:tools/deep_history` на Linux/macOS.

Примеры:

```bash
PYTHONPATH=src:tools/deep_history python src/collector.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python tools/capability_index.py list
python tools/capability_index.py describe spot.binance-spot.ETHUSDT.ohlcv.5m
```

D6.2A resolution example:

```bash
python tools/capability_index.py resolve \
  spot.binance-spot.ETHUSDT.ohlcv.5m \
  --from 2022-06-18T00:00:00Z \
  --to 2022-11-10T00:00:00Z \
  --format json > resolution-plan.json
```

D6.2B принимает только сохранённый plan:

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
python src/collector.py
python tools/capability_index.py validate
```

GitHub Actions обязан задавать эквивалентный `PYTHONPATH` явно.

## Deep-history contour

Перед полным acquisition:

1. unit/adversarial tests;
2. targeted provider probe, если есть неизвестный overlap conflict;
3. live overlap policy qualification;
4. только затем полный `Publish deep history`.

Не запускать дорогой full acquisition вслепую после неизвестного conflict. D6 изменения сами по себе не являются причиной повторного D5/full acquisition.

## Architecture gate

Перед новым механизмом внутри Data Bridge обязательно ответить:

1. Какой реальный риск он закрывает?
2. Можно ли закрыть его более простым способом?
3. Уменьшает ли решение число действий для следующего агента и инженера?

Если механизм не закрывает конкретный риск, более простой путь достаточен или количество последующих действий растёт — механизм по умолчанию не добавляется.

## Коммиты

Для каждого осмысленного коммита использовать корневой `.gitmessage.txt`.

Правила:

- Subject — один короткий Conventional Commit-style заголовок на английском (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`, `data:`).
- В теле обязательны две смыслово эквивалентные секции: `RU:` и `EN:`.
- Для code/data-contract изменений обязательна секция `Validation / Проверка:` с фактически выполненными проверками.
- Не писать в Subject номера попыток, внутренние revision labels, «rework», «again», «final fix» и другие process-noise формулировки.
- Один коммит должен описывать завершённый semantic change.

Настройка локально:

```bash
git config commit.template .gitmessage.txt
```

## Перед завершением изменения

Минимум:

```bash
python -m compileall -q src tools tests
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
```

Если изменение затрагивает D6 capability/history-access contract, дополнительно:

```bash
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Network-backed historical materialization qualification запускается отдельно через `Qualify D6.2 history access`; она не входит в ordinary offline suite.
