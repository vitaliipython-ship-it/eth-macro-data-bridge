# AGENTS.md

## Назначение

Это каноническая точка входа для любого человека или агента, который изменяет `eth-macro-data-bridge`.

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
  capability_index.py        — staged D6 semantic discovery builder/validator
  deep_history/              — cold-history publisher, overlap policy, probes
  qualification/             — repeated-run/idempotence qualification
  validation/                — validators и consumer proof
tests/
  deep_history/              — tests для deep-history/release/capability contour
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

Текущий staged D6.1 contract:

```text
schema/capability-index.schema.json
        ↓
tools/capability_index.py build|validate
        ↓
history/capability-index.json
        ↓
docs/semantics/capability-index.md
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
- обычный hourly collector не перестраивает capability index.

**До D6.4 capability index не является публичным consumer route.** Consumer продолжает начинать только с `bridge-contract.json`. Не добавлять capability path в `bridge-contract.json`, не менять Research routing и не реализовывать обход manifests раньше соответствующего qualification gate.

Lifecycle и три architecture-вопроса подробно зафиксированы в `docs/semantics/capability-index.md`; cross-repository planning authority находится в `eth-macro-research/docs/integrations/market-data-capability-resolution-v1.md`.

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

Не запускать дорогой full acquisition вслепую после неизвестного conflict. D6.1 не является причиной повторного D5/full acquisition.

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

Если изменение затрагивает D6 capability contract, дополнительно:

```bash
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Если изменение затрагивает deep history — дополнительно соответствующие `tests/deep_history/` и targeted qualification.
