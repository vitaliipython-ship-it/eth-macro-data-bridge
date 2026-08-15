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
  deep_history/              — cold-history publisher, overlap policy, probes
  qualification/             — repeated-run/idempotence qualification
  validation/                — validators и consumer proof
tests/
  deep_history/              — tests для deep-history/release contour
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

## Выполнение Python

Из корня репозитория для validation/qualification использовать `PYTHONPATH=src:tools/deep_history` на Linux/macOS.

Примеры:

```bash
PYTHONPATH=src:tools/deep_history python src/collector.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
```

PowerShell:

```powershell
$env:PYTHONPATH = 'src;tools/deep_history'
python src/collector.py
```

GitHub Actions обязан задавать эквивалентный `PYTHONPATH` явно.

## Deep-history contour

Перед полным acquisition:

1. unit/adversarial tests;
2. targeted provider probe, если есть неизвестный overlap conflict;
3. live overlap policy qualification;
4. только затем полный `Publish deep history`.

Не запускать дорогой full acquisition вслепую после неизвестного conflict.

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

Если изменение затрагивает deep history — дополнительно соответствующие `tests/deep_history/` и targeted qualification.
