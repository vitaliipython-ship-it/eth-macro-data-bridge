---
title: "Backlog — AIFE Solo Tracker"
id: DOC-95-REPORTS-RECOMMENDATIONS-BACKLOG
version: '1.2'
status: active
owner: Architecture Lead
created: 2025-10-15
updated: 2026-08-29
next_review_due: 2026-08-04
category: reports
doc_type: report
tags: [backlog, tracking, solo]
review_cycle_days: 30

---

# Backlog — AIFE Solo Tracker

> Единый бэклог всех задач. Источники: аудиты кода, документации, инфраструктуры.

## Статусы

| Статус | Описание |
|--------|----------|
| Backlog | Статус ожидания в очереди |
| In Progress | Статус активной работы |
| Done | Статус завершённой задачи |
| Cancelled | Статус отменённой задачи (с причиной) |

## Формат импорта из Unified TZ (D-016)

Используйте один унифицированный формат для переноса задач из `Unified TZ`:

```markdown
| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-0XX | <действие> | [Audit TZ](<path/to/TZ_file.md>) §<section> | Backlog |
```

Правила импорта:

1. `ID` использует только префиксы backlog: `B-`, `C-`, `D-`, `S-`, `I-`, `L-`.
2. `Статус` для новой задачи всегда `Backlog`.
3. `Источник`: ссылка на конкретный audit/TZ раздел с подписью `Audit TZ` и указанием `§N`.
4. Задача добавляется в секцию своего приоритета (`P0/P1/P2/P3`), без дублирования существующего `ID`.
5. При повторном аудите сначала обновляйте существующую строку по `ID`, а не создавайте новую.

## Классификация ID (анти-путаница для агентов)

`Backlog Task IDs` (разрешены только в этом файле):

- `B-xxx` — критические баги/runtime-defects.
- `C-xxx` — feature/runtime implementation (в основном код и интеграции).
- `D-xxx` — documentation/architecture/process/tooling quality tasks.
- `S-xxx` — security-domain tasks.
- `I-xxx` — infrastructure/CI/ops/tooling tasks.
- `L-xxx` — long-horizon/legacy/landscape tasks.

`Analysis IDs` (запрещены как backlog-задачи):

- `DEV-xxx`, `DEVCONS-xxx` — research findings.
- `AUD-xxx` — audit findings.

### Legacy / historical noncanonical IDs

Ниже перечислены historical строки backlog, которые уже существуют в этом
файле как след ранее закрытых контуров, review-only волн или bounded cleanup.
Они не расширяют allowlist backlog ID и не дают агенту права создавать новые
task-card с теми же префиксами или шаблонами.

| ID pattern | Disposition | New usage allowed |
|---|---|---:|
| `A10-*` | legacy architecture contour IDs; retained as historical accepted rows | no |
| `A10-SD-*` | legacy closed structure-disposition contour IDs; retained as historical accepted rows | no |
| `A10-AUTHORITY-REFERENCE-CLEANUP-001` | bounded cleanup label retained as historical row | no |
| `RP-*` | historical review-process cleanup IDs | no |
| `R-*` | historical README audit IDs | no |
| `QG-*` | historical quality-gate audit IDs | no |
| `STD-*` | historical standards-review task rows; not owner artifact IDs | no |
| `ATS-*` | invalid draft IDs in current tree-sync contour; must be canonicalized before plan-review/execution | no |

Правила интерпретации:

1. Historical noncanonical IDs сохраняются только для traceability и не
   становятся разрешённым namespace новых backlog task-card.
2. Если новый `DEV_TZ` или investigation создаёт task-card, он обязан
   использовать только backlog-префиксы `B-`, `C-`, `D-`, `S-`, `I-`, `L-`.
3. Contour-local labels, findings IDs, review labels и scope slugs допустимы
   только вне backlog task-card namespace. Примеры: `TREE-SYNC-F01`,
   `A10-SD-5-RF-*`, `architecture-tree-sync-governance-and-validation`.
4. Такие labels нельзя импортировать в canonical backlog как новые task ID,
   если они не проходят через разрешённый backlog namespace.
5. Для контура `architecture-tree-sync-governance-and-validation`
   `ATS-001..ATS-005` считаются invalid draft task IDs; перед
   `plan-review`/execution они должны быть заменены на canonical `D-*`.

Правило выдачи номеров:

1. В `RESEARCH_*`, `RESEARCH_CONSOLIDATED_*`, `AUDIT_*`, `AUDIT_CONSOLIDATED_*` нельзя создавать backlog task-ID (`B-/C-/D-/S-/I-/L-`).
2. Нумерация backlog task-ID создаётся только на этапе формирования `TZ_*`/`DEV_TZ_*` из consolidated-отчёта.
3. После генерации TZ задачи импортируются в этот backlog с проверкой уникальности ID.

---

### BCH-READINESS — предварительная проверка перед первой blockchain implementation

Этот блок фиксирует future-readiness findings для будущего pre-implementation
контура. Метки `BCH-READINESS-*` не являются backlog task-card ID, не создают
`DEV_TZ`, не создают Task-ID и не разрешают runtime implementation.

- `BCH-READINESS-001` — добавить прямые unit-тесты для
  `BlockchainCommunicationAdapter.emit()` и
  `BlockchainCommunicationAdapter.route_event()`.
  Смысл: подтвердить передачу события в `SignalCommunication.emit(...)`,
  отсутствие mutation payload и отсутствие business logic в adapter.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-002` — усилить тесты `BlockchainManager`.
  Смысл: проверить lazy creation adapter, реальный путь
  `process_blockchain_event -> BlockchainCommunicationAdapter ->
  SignalCommunication`, payload shutdown `final_status="event_shell_shutdown"`,
  `state_persistence="not_implemented"` и отсутствие `saved_state=True`.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-003` — принять решение по package surface
  `from blockchain import BlockchainCommunicationAdapter`.
  Смысл: либо добавить package surface test, либо в будущем убрать root export,
  если он не является публичной поверхностью.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-004` — зафиксировать UI placeholder guard.
  Смысл: проверить, что blockchain menu/toolbar остаются unavailable routes,
  пока нет backend action, а toolbar fallback не вызывает `BlockchainManager`.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-005` — выполнить отдельный dead-path / vestigial-path audit
  перед первой реализацией.
  Смысл: отличить intentional placeholders от dead code, найти synthetic-only
  paths, проверить action ids, которые существуют только в UI, проверить future
  event names, которые существуют только в документации, и не превращать future
  companion docs в runtime API.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-006` — оставить `security/blockchain` как policy-level
  validators.
  Смысл: при будущей transaction subsystem не считать эти helpers достаточной
  transaction-security subsystem; они не заменяют signing, wallet lifecycle,
  transaction lifecycle и on-chain validation.
  `status: future-readiness`; `not-a-task: true`;
  `requires-separate-decision: true`;
  `runtime-implementation-authorized: false`.

- `BCH-READINESS-007` — закрытое polishing-наблюдение по лог-сообщениям
  `BlockchainManager`.
  `status: completed-polishing`; `not-a-task: true`;
  `requires-separate-decision: false`;
  `runtime-implementation-authorized: false`.
  Смысл: лог-сообщения уже уточнены с `блокчейн система` на
  `блокчейн-обвязка`, чтобы соответствовать текущему runtime как
  lifecycle/event shell.

## P1 — Синхронизация раздела docs/01-Overview (2026-06-01)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-O01-1 | Синхронизировать README-first route, inventory и index раздела `docs/01-Overview` | [DEV_TZ overview-01-sync](../98-Reviews/execution/2026-06/overview-01-sync/DEV_TZ_overview-01-sync_2026-06-01.md) §Task-card `D-O01-1` | Done |
| D-O01-2 | Снять дубли и shadow-routes overview-документов | [DEV_TZ overview-01-sync](../98-Reviews/execution/2026-06/overview-01-sync/DEV_TZ_overview-01-sync_2026-06-01.md) §Task-card `D-O01-2` | Done |
| D-O01-3 | Синхронизировать stale roadmap/config/developer/archive disposition | [DEV_TZ overview-01-sync](../98-Reviews/execution/2026-06/overview-01-sync/DEV_TZ_overview-01-sync_2026-06-01.md) §Task-card `D-O01-3` | Done |
| D-O01-4 | Оформить terminal proof и Artifact Necessity closure для `docs/01-Overview` | [DEV_TZ overview-01-sync](../98-Reviews/execution/2026-06/overview-01-sync/DEV_TZ_overview-01-sync_2026-06-01.md) §Task-card `D-O01-4` | Done |

## P1 — Investigation беклог для docs/10-Architecture (2026-06-02)

> `A10-1`, `A10-2` и `A10-3` приняты как корректно закрытые.
> `A10-4` принят отдельным closure-review: diagram-layer подтверждён как
> companion/derived слой с runtime parity и archive route.
> `A10-5` закрыт как terminal proof; execution-контур `architecture-10-sync`
> завершён без автоматического открытия downstream execution.
> Возможная будущая структурная перегруппировка в `docs/10-Architecture/runtime/`
> и `docs/10-Architecture/planning/` пока существует только как downstream
> candidate и не открывает новый execution в этом контуре.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| A10-1 | Синхронизировать входы, индексы и закон маршрута чтения для `docs/10-Architecture` без подмены источника архитектурной истины (`done`) | [DEV_TZ architecture-10-sync](../98-Reviews/execution/2026-06/architecture-10-sync/DEV_TZ_architecture-10-sync_2026-06-02.md) §Task card `A10-1` | Done |
| A10-2 | Синхронизировать поверхности текущей исполняемой архитектуры (`architecture.md`, `app_context_architecture.md`, `system_control_integration.md`) с текущим runtime-контекстом AIFE (`done`) | [DEV_TZ architecture-10-sync](../98-Reviews/execution/2026-06/architecture-10-sync/DEV_TZ_architecture-10-sync_2026-06-02.md) §Task card `A10-2` | Done |
| A10-3 | Классифицировать `Project_Modules_Documentation.md` как `draft/autogen/planned module map candidate` либо отдельно подтвердить иную роль (`done`) | [DEV_TZ architecture-10-sync](../98-Reviews/execution/2026-06/architecture-10-sync/DEV_TZ_architecture-10-sync_2026-06-02.md) §Task card `A10-3` | Done |
| A10-4 | Классифицировать `diagrams/**` как сопроводительный/производный слой, довести ownership-model до runtime parity и разобрать residual carriers без дрейфа источника истины (`done`) | [DEV_TZ architecture-10-sync](../98-Reviews/execution/2026-06/architecture-10-sync/DEV_TZ_architecture-10-sync_2026-06-02.md) §Task card `A10-4` | Done |
| A10-5 | Закрыть terminal proof и контур закрытия для `architecture-10-sync` без ложного downstream execution (`done`) | [DEV_TZ architecture-10-sync](../98-Reviews/execution/2026-06/architecture-10-sync/DEV_TZ_architecture-10-sync_2026-06-02.md) §Task card `A10-5` | Done |

## P1 — Structure-disposition backlog для docs/10-Architecture (2026-06-03)

> `A10-SD-1` закрыт через PRR, `A10-SD-2` выполнен как bounded runtime-layer
> migration и принят отдельным closure-review.
> `A10-SD-3` принят отдельным closure-review.
> `A10-SD-4` принят отдельным closure-review как bounded split overview/tree
> result; required-fix `A10-SD-4-TREE-IDENTITY-REQUIRED-FIX` восстановил
> идентичность дерева до принятия review.
> Для `A10-SD-5` интегрирован PRR, принят bounded policy-sync и выполнен
> bounded execution по materialization модульных архитектурных деревьев:
> состояние = `implementation_completed_pending_closure_review`.
> `RF-A10-SD-5-02` закрыт через package policy для `BSP/`,
> `external/everything-claude-code/` и `patches/`; `RF-A10-SD-5-03`
> переведён в `accepted_with_bounded_validation_scope`.
> `A10-SD-6` остаётся dependency-gated.
> Required-fix `A10-SD-5-RF-TREE-COVERAGE-SEMANTIC-COMMENTS` дополнительно
> довёл полноту и комментарии tree-surfaces: `current_architecture_tree.md`
> закреплён как активный индекс, `current_architecture_tree_index.md`
> сохранён только как redirect, а `docs/`, `scripts/` и `tests/` получили
> усиленное покрытие перед closure-review.
> Required-fix `A10-SD-5-RF-ROUTE-INDEX-AND-COMMENT-QUALITY-SYNC` завершён: верхние README и JSON-индексы ведут на `current_architecture_tree.md`, `docs/`-счётчики пересчитаны, а слабые комментарии root/runtime tree-surfaces заменены на тематические.
> Required-fix `A10-SD-5-RF-FINAL-TREE-SYNC` завершён: `architecture.md` закрепляет активный индекс раньше redirect-ссылки, `module-directories.md` удерживает согласованный счётчик `docs/ = 907`, а остатки шаблона `Python-модуль:` удалены из малых runtime tree-surfaces перед closure-review.
> Closure-review `A10-SD-5` принят: модульные архитектурные деревья закрыты как bounded navigation surface без дрейфа источника истины; `A10-SD-6` переведён только в `next_gated_candidate_pending_plan_review`.
> File-system-first PRR `A10-SD-6` интегрирован: `A10-SD-6` переведён в `ready_for_execution` только для terminal closure execution; в самом execution обязателен terminal recount `docs/` после добавления terminal artifacts.
> Terminal closure `A10-SD-6` завершён: контур `architecture-10-structure-disposition` закрыт, package-facing recount `docs/` доведён до `910`, review package остаётся чистым, а downstream-направления удержаны в состоянии `locked until explicit separate decision`.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| A10-SD-1 | Провести plan-review `A10-STRUCTURE-DISPOSITION`, синхронизировать admission-state и разрешить execution только для `A10-SD-2` (`done`) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-1` | Done |
| A10-SD-2 | Создать `docs/10-Architecture/runtime/`, перенести `app_context_architecture.md` и `system_control_integration.md`, синхронизировать route-back и ссылки (`done`) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-2` | Done |
| A10-SD-3 | Создать `docs/10-Architecture/planning/`, перенести `architecture-roadmap.md` и `Project_Modules_Documentation.md`, закрепить planning-only роль (`done`) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-3` | Done |
| A10-SD-4 | Принять bounded решение по декомпозиции `general/architecture.md` или его сохранению как thin overview / route hub (`accepted_closed`) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-4` | Done |
| A10-SD-5 | Синхронизировать индексы, metadata, route-back и prompt-sensitive surfaces после фактических переносов; materialize модульную tree-модель с root/runtime/governance/measurement/tooling/disposition поверхностями (`accepted_closed`) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-5` | Done / accepted_closed |
| A10-SD-6 | Закрыть structure-disposition contour: final proof, no-owner-drift validation и terminal closure (`accepted_closed`, terminal recount `docs/ = 910` выполнен) | [DEV_TZ architecture-10-structure-disposition](../98-Reviews/execution/2026-06/architecture-10-structure-disposition/DEV_TZ_architecture-10-structure-disposition_2026-06-03.md) §Task card `A10-SD-6` | Done / accepted_closed |

## P1 — Authority reference cleanup для docs/10-Architecture (2026-06-05)

> `A10-AUTHORITY-REFERENCE-CLEANUP-001` выполнен как отдельный bounded cleanup:
> исправлены только missing `authority_reference target` в
> `docs/10-Architecture/diagrams/**` и `docs/10-Architecture/runtime/README.md`
> без подмены источников полномочий convenience-поверхностями.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| A10-AUTHORITY-REFERENCE-CLEANUP-001 | Исправить missing `authority_reference target` в `docs/10-Architecture/diagrams/**` и `docs/10-Architecture/runtime/README.md` через реальные owner targets из standards/ADR/owner-route | [Closure A10 authority reference cleanup](../98-Reviews/execution/2026-06/architecture-authority-reference-cleanup/CLOSURE_A10_authority-reference-cleanup_2026-06-05.md) §Матрица old/new | Done |

## P1 — Investigation backlog для постоянной синхронизации архитектурных деревьев (2026-06-05)

> Контур `architecture-tree-sync-governance-and-validation` интегрирован как
> исследовательский и подготовительный: investigation и `DEV_TZ` уже
> опубликованы, а прежние неканонические draft-ID заменены на диапазон
> `D-359..D-363`.
> Текущее состояние:
> `TREE_SYNC_GOVERNANCE_D359_D360_D361_D362_D363_ACCEPTED_CLOSED`,
> `architecture-tree-sync-governance-and-validation = closed`,
> `D-359 = accepted_closed`,
> `D-360 = accepted_closed`,
> `D-361 = accepted_closed`,
> `D-362 = accepted_closed`,
> `D-363 = accepted_closed`,
> `RF-COVERAGE-ENFORCEMENT = accepted`,
> `Execution allowed = false`.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-359 | Проверить naming/registry decision для будущих owner-артефактов tree-sync без создания `STD/ADR/CONTRACT` по смыслу | [DEV_TZ architecture-tree-sync-governance-and-validation](../98-Reviews/research/2026-06/architecture-tree-sync-governance-and-validation/DEV_TZ_architecture-tree-sync-governance-and-validation_2026-06-05.md) §D-359 | Done |
| D-360 | Создать машинный носитель правил синхронизации архитектурных деревьев и schema к нему; зависит от `D-359`; closure-review принят, шаг закрыт только как substrate/materialization step без validator и без открытия downstream execution | [DEV_TZ architecture-tree-sync-governance-and-validation](../98-Reviews/research/2026-06/architecture-tree-sync-governance-and-validation/DEV_TZ_architecture-tree-sync-governance-and-validation_2026-06-05.md) §D-360 | Done |
| D-361 | Реализовать мягкий валидатор синхронизации архитектурных деревьев и выполнить `dry-run` на текущем состоянии; зависит от `D-360`; closure-review принят, шаг закрыт только как soft validator + dry-run step без gate integration и без owner-artifact publication | [DEV_TZ architecture-tree-sync-governance-and-validation](../98-Reviews/research/2026-06/architecture-tree-sync-governance-and-validation/DEV_TZ_architecture-tree-sync-governance-and-validation_2026-06-05.md) §D-361 | Done |
| D-362 | Принят bounded decision-only step: подтверждено, что новые `STD/ADR/CONTRACT` сейчас не нужны, final owner-artifact IDs не назначаются, а warning `comment-policy.weak-patterns` остаётся входом для `D-363` | [DEV_TZ architecture-tree-sync-governance-and-validation](../98-Reviews/research/2026-06/architecture-tree-sync-governance-and-validation/DEV_TZ_architecture-tree-sync-governance-and-validation_2026-06-05.md) §D-362 | Done |
| D-363 | Финальная operational integration завершена: remediation `comment-policy.weak-patterns`, blocking weak-comment policy, hook `architecture-tree-sync`, prompt/instruction sync и terminal closure всего контура выполнены без создания `STD/ADR/CONTRACT` и без downstream unlock; required-fix `RF-COVERAGE-ENFORCEMENT` / `RF-COVERAGE-ENFORCEMENT-FINAL` дополнительно принял двусторонний runtime/scripts coverage gate, stale tree entry blocking и blocking `tests/**` per-directory policy | [DEV_TZ architecture-tree-sync-governance-and-validation](../98-Reviews/research/2026-06/architecture-tree-sync-governance-and-validation/DEV_TZ_architecture-tree-sync-governance-and-validation_2026-06-05.md) §D-363 | Done |

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| B-001 | Двойная/тройная доставка событий: `EventBus.subscribe()` регистрирует callback и в `SignalCommunication`, и в `EventRouter` напрямую (дубль); `SignalCommunication.emit()` вызывает callback из `_subscribers` + отправляет в `EventRouter` — итого до 3× вызовов | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.1 + [Deep Audit 2026-02-19] | Done |
| B-002 | Два экземпляра LogManager: глобальный синглтон при `import` (`log_manager.py` L826) + DependencyManager — гонка данных, побочные эффекты в тестах | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.1 + [Deep Audit 2026-02-19] | Done |
| B-003 | Отсутствует `unsubscribe()` в EventRouter и SignalCommunication — утечка памяти | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 | Done |
| B-004 | CI workflows (`python-version: '3.10'`) не соответствуют проекту (Python 3.11, pyenv `aife-3119`, mypy, pyrightconfig) — тесты на неправильной версии | [Deep Audit 2026-02-19] | Done |
| B-005 | ~~`pytest-asyncio==1.2.0` — ложное срабатывание: версия 1.2.0 актуальна (1.x серия), тесты проходят (162/162), `asyncio_mode=strict` работает~~ | [Deep Audit 2026-02-19] | Cancelled |
| B-006 | CHANGELOG.md: нет секции `[Unreleased]`, последняя запись 2025-10-19 — 4 месяца изменений (20+ коммитов) не задокументированы | [Deep Audit 2026-02-19] | Done |
| B-007 | Гейт метаданных не блокирует ошибки: `validate_markdown_metadata.py --json` без `--strict` — возвращает exit 0 при 36 ошибках | [Quality Gate Audit 2026-02-19] | Done |
| B-008 | `check_coverage_thresholds.py` падает на Windows cp1251 из-за emoji в print (✅) — UnicodeEncodeError даже при пройденных порогах | [Quality Gate Audit 2026-02-19] | Done |
| B-009 | Owner-валидатор проверяет только staged файлы — при `--all-files` (CI) staged=0 → skip, валидатор никогда не срабатывает в CI | [Quality Gate Audit 2026-02-19] | Done |

## P0 — UI Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-019 | Реализовать полноценный UIManager lifecycle: setup_ui error propagation, initialize timeout, shutdown cascade, shutdown_callback try/finally | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-019 | Done |
| C-020 | Исправить setStyleSheet в ChartTabManager — заменить docstring на валидный CSS | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-020 | Done |
| C-021 | Создать базовый набор unit-тестов для UI (tests/unit/ui/) — target покрытие ≥ 30% | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-021 | Done |

## P0 — Стандарты (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| STD-001 | Синхронизировать STANDARDS_REGISTRY.md: 17 статусов draft→approved, 4 версии, 15 владельцев, счётчик 44→45 | [Standards Review](standards_review_2025-01.md) §2.1, §16 | Done |
| STD-002 | Исправить status STD-GOVERNANCE-AUTHORING-001: `active` → `approved` (нелегитимный статус для стандартов) | [Standards Review](standards_review_2025-01.md) §3 | Done |

## P0 — Review Process Deprecation (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| RP-001 | Deprecate review-process suite (7 файлов): FM `status: deprecated`, `deprecated_by: AGENTS_PATCH_GUIDE`, notice после заголовка | [Review Audit 2026-02-19] | Done |
| RP-002 | Убрать 8-фазные противоречия: секция Compliance Audit / Release Bundle / Production Deployment в PATCH_WORKFLOW, Patch Request section в 98-Reviews/README | [Review Audit 2026-02-19] | Done |
| RP-003 | Удалить устаревшие YAML: `PATCH_REQUEST_TEMPLATE.yaml`, `patch_request.LogManagers.yaml` (антипаттерн #6 AGENTS_PATCH_GUIDE) | [Review Audit 2026-02-19] | Done |
| RP-004 | Исправить Phase 2 именование: «Patch Implementation» → «Individual Analysis» в review-process/README.md | [Review Audit 2026-02-19] | Done |

## P1 — Review Process Cleanup (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| RP-005 | Унифицировать команды `python -m pytest` / `python -m pre_commit` (19 вхождений, 5 файлов deprecated suite) | [Review Audit 2026-02-19] | Done |
| RP-006 | Заменить хардкод покрытия (80/85/90%) на ссылку `coverage_thresholds.json` (3 вхождения) | [Review Audit 2026-02-19] | Done |
| RP-007 | Очистить устаревшие пути: `Activate.ps1` → pyenv, `UNIVERSAL_AGENT_INSTRUCTION` → `MAIN_GUIDE`, PR/merge → коммит, `feature/` → `fix/` | [Review Audit 2026-02-19] | Done |
| RP-008 | Обновить GUIDELINES_REGISTRY и review/README.md — suite status → ⛔ Deprecated | [Review Audit 2026-02-19] | Done |

## P0 — Audit Framework v2 (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-012 | Обновить `.github/prompts/audit.prompt.md` до v2: Contract, C1-C8, Consolidation, Unified TZ | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |
| D-013 | Стандартизовать хранение артефактов в `docs/98-Reviews/audits/` и зафиксировать структуру/naming | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |
| D-014 | Зафиксировать anti-clutter policy для audit-потока | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |

## P0 — Genome Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-019 | Унифицировать порядок EN/RU в docstring-правилах | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-019 | Done |
| D-020 | Удалить фантомные ID из STD-DATA-MGMT-001 | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-020 | Done |
| D-021 | Устранить конфликт versioning policy (MAJOR.MINOR vs X.Y.Z) | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-021 | Done |
| D-042 | Унифицировать related path convention и закрыть missing related links во всех STD-* | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P0 — Immediate | Done |
| D-043 | Нормализовать version до MAJOR.MINOR.PATCH для всех STD-* и синхронизировать с реестром | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P0 — Immediate | Done |
| D-044 | Подготовить и провести closure-review для всех non-approved стандартов | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P0 — Immediate | Done |

## P0 — Genome Standards ARCH Research (2026-03-18)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-068 | Зафиксировать ownership contract manager/service/repository + canonical DI resolve path | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-068 | Done |
| D-069 | Определить `core/data/` topology и disposition historical flat-file claims | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-069 | Done |
| D-075 | Реализовать DI resolve unification + AppContext extension по ownership contract (Phase B; downstream после closure Phase A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-075 | Done |
| D-076 | Создать `core/data/` package structure + base abstractions по topology (Phase B; downstream после closure Phase A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-076 | Done |

## P0 — UI Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-042 | Реализовать Data Integration: historical_data_loader + data_stream_manager для chart data feed | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-042 | Done |
| C-043 | Реализовать Theme Manager: theme_manager + theme_loader + style_settings (dark/light, QSS) | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-043 | Done |
| C-044 | Реализовать Market Overview: symbol_list + symbol_search + chart_integration | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-044 | Done |
| C-040 | Реализовать ChartWidget + Main Canvas: production OHLCV renderer (pyqtgraph), 9 слоёв main_canvas | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-040 | Done |
| C-041 | Реализовать Chart Header: InstrumentLabel + TimeframeLabel + ActionButtons | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-041 | Done |
| C-045 | Реализовать Chart Footer: status_bar + interaction_hint + notification_area | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-045 | Done |
| C-046 | Реализовать Indicator Windows: BaseIndicatorWindow + FACT + ADX windows | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-046 | Done |
| D-053 | IconProvider — централизованный runtime service для theme-aware загрузки иконок | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-053 | Done |
| D-054 | Каноническая структура `resources/icons` + стабильные пути + EXT intake `_incoming` (анализ SVG/PNG и сортировка ассетов) | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-054 | Done |

## P0 — UI MainWindow + Chart Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-070 | Реализовать incremental rendering pipeline: append_candle, update_last_candle, viewport culling, dirty-region tracking | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-070 | Done |
| C-071 | Реализовать layout mode contract: ChartLayoutMode enum (MINIMAL/EXTENDED/FULLSCREEN), set_layout_mode API | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-071 | Done |
| C-072 | Реализовать unified ActionDescriptor + расширить ActionRegistry + ActionDispatcher + ShortcutConflictScanner | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-072 | Done |
| C-073 | Реализовать chart context menu (ПКМ на canvas): категории Trading/Chart/Drawing/View через ActionRegistry | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-073 | Done |
| C-074 | Исправить оси графика: price axis → right, DateAxisItem для bottom axis, убрать emoji title | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-074 | Done |
| C-075 | Реализовать ChartContextSnapshot DTO: frozen dataclass, atomic set_context(), signal context_changed | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-075 | Done |
| C-092 | Создать package skeleton `ui/layout/workspace/` и зафиксировать public API boundaries без альтернативного production namespace | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-092 | Done |
| C-093 | Реализовать `WorkspaceGraph` и `node_types` как authoritative model для panels/toolbars/content_host с schema-ready `floating_zone` и без native authority | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-093 | Done |
| C-094 | Реализовать `ZoneTree` и unified topology model через canonical `ui/layout/workspace/topology` public entrypoint для fixed/nested/tabbed/pinned/band/content_host zones без обязательного runtime floating в v1 | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-094 | Done |
| C-095 | Реализовать `ZoneRegistry` и `WorkspaceEvents` как отдельный runtime registry/event boundary поверх `graph`/`topology` для workspace framework | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-095 | Done |

## P1 — Owner Corpus Semantic Block Normalization Rollout

> `D-324` закрыт bounded execution'ом и переведён в canonical status `Done`.
> Historical blocker-review `PRR-D-324-20260516-blocked` не переписывается;
> после bounded `D-324-BLOCKER-SYNC`, повторного review-event
> `PRR-D-324-20260516-approved` и самого execution materialized `14`
> file-local carriers в active `ADR` owner files, а deprecated
> `ADR-INITIALIZER-SYSTEM-002` сохранён как честный `no-change`. Historical
> review-event `PRR-D-325-20260516-blocked` затем подтвердил, что task-card
> `D-325` не выражала весь residual subset post-`D-323` / `D-324` и не
> фиксировала однозначный execution mode. После bounded task-contract sync
> `D-325-BLOCKER-SYNC` live task-card уже route-back-ит residual authorizing
> boundary `D-322 -> D-323 -> D-324`, общий contour `49` owner artifacts и
> canonical mode `residual-disposition-only / no-owner-edit`. Затем bounded
> execution `D-325` зафиксировал матрицу `16 blocked + 4 deferred + 29
> no-change` без owner edits и без новых carrier blocks. Затем
> `I-1044-BLOCKER-SYNC` сузил compare до changed `D-323` / `D-324` slices, а
> повторный review-event `PRR-I-1044-20260518-blocked-r2` подтвердил
> historical compare-carrier gap и route-back в bounded
> `I-1044-COMPARE-CARRIER-SYNC`.
>
> `I-1044-COMPARE-CARRIER-SYNC` уже закрыл этот ограниченный разрыв в
> measurement-substrate: live schema, current scenario catalog, family
> descriptor и `family_taxonomy.json` теперь разрешают `I-1044` только как
> changed-slice `t1_result_task` / `t1_result_path` / `compare_path` для уже
> изменённого подмножества `D-323` / `D-324`. `D-325` сохранён только как
> context / guard contour, residual `49` остаётся в downstream-контуре
> `D-328..D-331`, а отдельным ограниченным исполнением `I-1044` уже созданы
> пакет результата `.benchmarks/results/owner-corpus-semantic-block-normalization-rollout-post-d323-d324-slices/normalized_result.json`
> и пакет сравнения `.benchmarks/compare/owner-corpus-semantic-block-normalization-rollout-changed-d323-d324-first-compare/compare_package.json`.
> Compare verdict = `bounded-improvement-confirmed`, semantic result =
> `6 true / 3 retained false`, publication package не создан,
> dashboard/runtime не открывались, owner `.md` не менялись. После этого
> bounded execution `D-328` уже закрыт как `Done`: exact blocked subset `16`
> получил explicit per-artifact verdicts (`15 carrier-needed-but-not-authorized-in-D-328 + 1 excluded-by-owner-law-with-named-reason`) без owner edits и без новых carrier blocks. Поверх этого bounded execution `D-329` уже закрыт как `Done`: точная deferred-четвёрка `STD-DOC-INDEX-001`, `STD-GOVERNANCE-METRICS-001`, `STD-GOVERNANCE-ROUTING-001`, `STD-GOVERNANCE-STRUCTURAL-001` получила explicit per-artifact verdicts (`2 deferred-retained-with-named-condition + 2 delegated-to-separate-approved-contour`) без правок owner `.md`, без новых carrier blocks и без выхода в blocked `16` или no-change `29`. Поверх этого bounded execution `D-330` уже закрыт как `Done`: exact no-change subset `29`
> (`7` retained rows из `D-322` + `21` conservative no-change rows из
> `D-323` + `1` deprecated `ADR` из `D-324`) получил explicit per-artifact
> verdicts `accepted-no-change-with-proof` без правок owner `.md`, без новых
> carrier blocks и без forbidden-root drift. Historical review-event
> `PRR-D-331-20260520-approved` теперь сохраняется только как evidence того,
> что residual contour `49 / 49` уже покрыт class-wise verdict-ами. Этого
> больше недостаточно для live terminal closure: пакет теперь требует
> `77 / 77` terminal operational status, `77 / 77` physical owner-side
> machine-safe carrier, `0` terminal `draft / proposed / deferred / blocked /
> ambiguous no-change` и explicit `active/archive` disposition для каждого
> owner artifact. После closure bounded verification gate `D-332` control-plane
> теперь честно фиксирует, что duplicate policy rewrite не произошло, current
> physical owner-side machine-safe carrier coverage по-прежнему = `28 / 77`
> (`D-323 = 14` + `D-324 = 14`), residual-only evidence `49 / 49` не
> authorizes `D-331`, а separate strict review `PRR-D-333-20260520-blocked`
> уже удержан как historical evidence, а bounded sync `D-333-BLOCKER-SYNC`
> синхронизировал live task-card `D-333`: точный входной контур `49 + 28`,
> terminal law только для `active/live` / `archived/deprecated`,
> per-artifact matrix и явный запрет на правки owner `.md`, новые carrier
> blocks и выход в контуры `result/compare/publication` теперь закреплены
> прямо в task-contract. Отдельный bounded `D-333-MATRIX-GRAMMAR-SYNC`
> уже закрыл последний grammar-разрыв: в per-artifact matrix теперь прямо
> перечислены допустимые значения `source cohort` и
> `required carrier disposition`, без запуска самого `D-333`. Повторный
> strict review `PRR-D-333-20260521-approved` подтвердил readiness, а само
> execution `D-333` уже закрыто как `Done`: в live control-plane
> зафиксирована матрица `77 / 77`, разделение по `proposed terminal status` `54 active/live + 23
> archived/deprecated`, а разбиение по `required carrier disposition`
> `28 already-present-carrier + 26 needs-active-carrier-in-D-334 + 22
> needs-archive/deprecated-carrier-in-D-335 + 1
> contract-single-entry-carrier-with-lock-retained`, без owner `.md` edits и
> без новых carrier blocks. Отдельный строгий предварительный обзор
> `PRR-D-334-20260521-blocked` показал, что prerequisites уже зелёные, а
> blocker находился только в слишком широкой pre-sync task-card `D-334`.
> Текущий bounded `#prompt:change-workflow` уже сузил live task-card до
> точного подмножества `26`, допустимого размещения по owner
> `.md`-носителям, forbidden roots и retained lock boundary с нужной
> жёсткостью. Повторный strict review `PRR-D-334-20260521-approved`
> подтвердил, что live task-card теперь прямо удерживает exact subset `26`,
> boundary `active/live`, допустимое host placement только в owner `.md`,
> forbidden roots, generated-as-owner prohibition и retained `CONTRACT`
> lock. После этого bounded execution `D-334` уже закрыто как `Done`:
> physical owner-side machine-safe carriers materialized ровно для exact
> subset `26`, вне подмножества owner `.md` edits не было, forbidden roots
> и generated companions не затронуты, а current physical carrier coverage
> теперь = `54 / 77` (`28 already-present-carrier + 26 from D-334`).
> После этого отдельный строгий review `PRR-D-335-20260521-blocked`
> подтвердил, что exact archive/deprecated subset `22` уже route-back-ится к
> матрице `D-333`, а retained `CONTRACT-DOC-PRR-001` row остаётся отдельным
> `contract-single-entry-carrier-with-lock-retained`. Отдельный bounded
> `D-335-BLOCKER-REMOVAL-SYNC` уже перевёл blocker в live task-contract, а
> повторный strict review `PRR-D-335-20260521-approved` подтвердил exact
> subset `22`, допустимое host placement только внутри owner `.md` этого
> подмножества, forbidden roots, generated-as-owner boundary, retained
> `CONTRACT` lock и downstream lock. После этого bounded execution `D-335`
> уже закрыто как `Done`: archive/deprecated owner-side machine-safe carriers
> materialized ровно для exact subset `22`, вне подмножества owner `.md`
> edits не было, forbidden roots и generated companions не затронуты, а full
> physical carrier coverage подтверждено как `77 / 77`. После отдельного
> repeat review-event `PRR-D-331-20260521-approved` bounded execution
> `D-331` уже закрыто как `Done`: terminal status coverage = `77 / 77`,
> physical carrier coverage = `77 / 77`, unresolved terminal statuses = `0`,
> carrier gaps = `0`, retained `CONTRACT-DOC-PRR-001` single-entry lock
> сохранён, owner `.md` carriers не менялись, forbidden roots и generated
> surfaces не тронуты. Поверх этого materialized repeat review-event
> `PRR-D-326-20260521-approved`, а затем bounded execution `D-326` уже
> закрыто как `Done`: route-back evidence, `no-change` / archive /
> follow-up evidence и rollback evidence синхронизированы только к уже
> закрытым owner и measurement facts, full-coverage gate `77 / 77` /
> `77 / 77` отражён без новых owner-side facts, retained row
> `CONTRACT-DOC-PRR-001` и её lock сохранены, owner `.md`, forbidden roots и
> generated companion surfaces не тронуты. После отдельного strict approved
> review-event `PRR-D-327-20260521-approved` подтверждало, что `D-327` можно
> честно допустить только к bounded execution как final terminal package
> closure; publication lane, dashboard/runtime, новый owner rollout и
> status-vocabulary cleanup автоматически не открываются. Теперь bounded
> execution `D-327` уже закрыт как `Done`: terminal law остаётся подтверждён
> как `77 / 77` terminal operational status и `77 / 77` physical carrier при
> `0` unresolved terminal statuses и `0` carrier gaps, retained
> `CONTRACT-DOC-PRR-001` lock сохранён, а внутри текущего rollout package
> автоматического следующего шага больше нет. Итоговая цепочка текущего
> package теперь = `D-332 -> D-333 -> approved review D-334 -> D-334 Done -> blocked review D-335 -> D-335 blocker-removal sync -> approved review D-335 -> D-335 Done -> approved review D-331 -> D-331 Done -> approved review D-326 -> D-326 Done -> approved review D-327 -> D-327 Done`.
>
> Архивный итог контура `owner-corpus-semantic-block-normalization-rollout`:
> корневые `README.md`, `PROGRAM_MAP_*`, `INVESTIGATION_QUEUE_*`, terminal
> `RESEARCH_*`, sibling `DEV_TZ_*` и sibling `PRR_*` переведены в архивную
> семантику как управляющий и доказательный след уже закрытого контура.
> Живые owner artifacts, owner-side carriers, validators,
> `.aife/measurement/**` и `.benchmarks/**` остаются активными и не
> архивируются; любой новый шаг допустим только как новый именованный контур
> вне текущего архива.
| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-311 | Оформить identity, storage contract и contamination policy для measurement `T0` wrapper | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §D-311 | Done |
| D-312 | Оформить scenario catalog, dimensions и family-specific probes для `STD / ADR / CONTRACT` | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §D-312 | Done |
| I-1041 | Снять `semantic-T0` baseline до любых owner `.md` правок | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §I-1041 | Done |
| I-1042 | Снять `navigation-T0` baseline и route-cost evidence до owner `.md` правок | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §I-1042 | Done |
| D-313 | Зафиксировать baseline immutability и compare admissibility manifest | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §D-313 | Done |
| I-1043 | Проверить `T0` package на contamination, route-back и family lock | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §I-1043 | Done |
| D-314 | Закрыть measurement `T0` gate и передать разрешение только в host-selection / rollout prerequisites | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_measurement-t0-wrapper-gate_2026-05-13.md) §D-314 | Done |
| D-315 | Составить host-selection matrix и карту unresolved owner-law вопросов | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-315 | Done |
| D-316 | Зафиксировать placement rules для существующих owner standards без нового workflow | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-316 | Done |
| D-317 | Оформить carrier grammar для machine-safe named semantic blocks и levels of route-back | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-317 | Done |
| D-318 | Зафиксировать generated-as-owner prohibition и companion-layer границы | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-318 | Done |
| D-319 | Зафиксировать `ADR` wrong-surface guard и `CONTRACT` family lock | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-319 | Done |
| D-320 | Закрыть bounded host review с patch/no-patch disposition и named blockers | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_bounded-owner-law-host-selection_2026-05-13.md) §D-320 | Done |
| D-321 | Проверить upstream gates и зафиксировать go/no-go для owner rollout | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-321 | Done |
| D-322 | Составить readiness-class inventory и per-file candidate map для `77` owner artifacts | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-322 | Done |
| D-323 | Оформить early active low-leakage `STD` rollout slice без cosmetic heading-only normalization | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-323 | Done |
| D-324 | Оформить conditional `ADR` slice только после wrong-surface containment | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-324 | Done |
| D-325 | Зафиксировать blocked/deferred/no-change classes для draft, deferred и `CONTRACT` corpus | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-325 | Done |
| I-1044 | Собрать post-change `T1` / compare package только для changed `D-323` / `D-324` slices (`D-325` = context only) | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §I-1044 | Done |
| D-328 | Разрешить `blocked` residual class через explicit blocker/follow-up verdict | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-328 | Done |
| D-329 | Разрешить `deferred` residual class через named deferred route | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-329 | Done |
| D-330 | Подтвердить `no-change` residual class как explicit no-change verdict | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-330 | Done |
| D-332 | Подтвердить закрепление full-coverage terminal law как verification gate перед `D-333` | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-332 | Done |
| D-333 | Зафиксировать terminal status grammar и explicit `active/archive` disposition для `77` owner artifacts | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-333 | Done |
| D-334 | Materialize physical owner-side machine-safe carriers только для точного active subset `26` с `needs-active-carrier-in-D-334` | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-334 | Done |
| D-335 | Свести `CONTRACT` / archive carrier contour и проверить full `77 / 77` closure | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-335 | Done |
| D-331 | Свести terminal admissibility verdict после полного `77 / 77` status/carrier proof | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-331 | Done |
| D-326 | Синхронизировать route-back / no-change / rollback evidence после full-coverage gate | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-326 | Done |
| D-327 | Закрыть rollout package без `CONTRACT` family generalization и без dashboard/runtime unlock | [Research TZ](../98-Reviews/research/2026-05/owner-corpus-semantic-block-normalization-rollout/DEV_TZ_owner-corpus-semantic-block-normalization-rollout_owner-corpus-normalization-rollout_2026-05-13.md) §D-327 | Done |

## P1 — Audit Framework v2

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-015 | Синхронизировать review-domain гайды с audit v2 | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |
| D-016 | Ввести единый формат импорта задач Unified TZ -> backlog | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |
| D-017 | Обновить навигационный контекст prompts/instructions под `#prompt:audit` | [TZ Audit Framework v2](TZ_AUDIT_FRAMEWORK_V2_2026-02-19.md) §5 | Done |

## P1 — Genome Standards ARCH Research (2026-03-18)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-070 | Построить карту доказательств соответствия async для `STD-ARCH-ASYNC-001` (`closed/partial/open`) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-070 | Done |
| D-071 | Собрать единую инвентаризацию блокирующих hotspot'ов и классификацию швов | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-071 | Done |
| D-072 | Зафиксировать таксономию тестов `repository/service` и контракт доказательства | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-072 | Done |
| D-077 | Закрыть действительно открытые async-пункты из карты доказательств (этап B; последующий шаг после закрытия этапа A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-077 | Done |
| D-078 | Мигрировать пять главных блокирующих hotspot'ов по классификации из инвентаризации (этап B; последующий шаг после закрытия этапа A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-078 | Done |
| D-079 | Создать набор тестов `repository/service` по таксономии (этап B; последующий шаг после закрытия этапа A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-079 | Done |

## P1 — Код

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-001 | `ManagerProtocol` дублирован в 7 файлах (communication, core, ui, security, monitoring, patterns, resources) → вынести в `initializer/protocols.py` | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 + [Deep Audit 2026-02-19] | Done |
| C-002 | `DependencyManager.shutdown()` неполный — не завершает SignalCommunication, TaskManager, LogManager | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 | Done |
| C-003 | `MainLogic` зависит от PySide6 — UI в логическом слое, нарушение SRP | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §3.11 | Done |
| C-005 | 7 модулей с нулевым тестовым покрытием: ai/, blockchain/, ui/, monitoring/, patterns/, resources/, security/ | [Deep Audit 2026-02-19] | Done |
| C-006 | Удалить/сверить dead code: `EventInterface` (оставлен как используемый контракт), неиспользуемые параметры SystemInitializer, `_cancel_pending_tasks()` | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.2 | Done |
| C-012 | Неправильная сигнатура `log_error` в SignalCommunication — 8 вызовов с 3 позиционными аргументами → исправлено на format string с контекстом | [Quality Gate Audit 2026-02-19] | Done |
| C-013 | `EventRouter._drain_pending_events()` отбрасывает события без логирования → добавлен log_warning для каждого дропнутого события | [Quality Gate Audit 2026-02-19] | Done |
| C-014 | `AIManager.process_ai_event()` мутирует входной dict (`data["timestamp"] = ...`) — side effect у вызывающей стороны | [Deep Audit 2026-02-19] | Done |
| C-015 | Менеджеры (Blockchain/Monitoring/Patterns) отправляют события в собственном `shutdown()` при уже остановленном CommunicationManager — расширить устойчивость к transport-level исключениям в финальной отправке | [Deep Audit 2026-02-19] | Done |
| C-016 | Конфликтующие пути shutdown: `main.py._graceful_shutdown()` + `MainLogic.shutdown()` (отменяет все asyncio tasks) + `SystemInitializer.shutdown()` — унифицировать MainLogic до soft-stop через `exit_event` | [Deep Audit 2026-02-19] | Done |

## P1 — UI Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-022 | Подключить MenuBar.exit_application() к shutdown path | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-022 | Done |
| C-023 | Исправить опечатки init_setings→init_settings и некорректные docstrings в UI | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-023 | Done |
| C-024 | Консолидировать UI event-систему (ActionRegistry + EventDispatcher) | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-024 | Done |
| C-025 | Исправить SettingsLoader: абсолютный путь CONFIG_PATH + обработка I/O ошибок | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-025 | Done |
| C-026 | Рефакторить UIComponents dataclass — Optional поля вместо type: ignore | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-026 | Done |
| C-027 | Централизовать CSS-стили через UISettings/theme-систему | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-027 | Done |
| C-028 | Удалить мёртвый код UI: init.py legacy, MainWindowSettings, пустые подпакеты | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-028 | Done |
| C-029 | Исправить DockPanelsManager: unreachable resize + unused _register_dock_signals | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-029 | Done |
| C-030 | Вывести obsolete drag-and-drop prototype из production и убрать legacy archive path | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-030 | Done |
| C-066 | Исправить partial theme switch (menu/chart/tab/dock/splitter/pyqtgraph): синхронизация theme tokens + runtime restyle + regression tests | [Bug Hunt Report](../98-Reviews/audits/2026-02/ui/BUG_HUNT_ui_2026-02-27_theme-switch.md) §Required Fixes | Done |
| C-067 | Исправить visual/interaction несоответствия MenuBar/ToolBars/Window Controls: parity фона, hover/pressed states, toolbar text behavior, docking/redocking/reorder regression coverage | [Bug Hunt Report](../98-Reviews/audits/2026-02/ui/BUG_HUNT_ui_2026-02-27_menu-toolbar-window-controls.md) §Required Fixes | Done |
| C-068 | Привести MenuBar/QMenu к целевому visual-style (VS Code-like), устранить submenu overlap и артефакты rounded corners через runtime filter + mask | [Bug Hunt Report](../98-Reviews/audits/2026-02/ui/BUG_HUNT_ui_2026-02-28_menubar-qmenu-visual-style.md) §Required Fixes | Done |
| C-069 | Реализовать стильную и консистентную систему рамок (MainWindow, Dock Panels, Splitters) с дизайн-анализом и parity dark/light; расширено (EXT): dock title border-top + _TopBorderOverlay, menubar separator,_SeparatorDragOverlay rubber-band; расширено (MENU): context-aware createPopupMenu | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_borders_2026-02-28.md) §C-069 | Done |

## P1 — Документация

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-001 | Исправить 5 синтаксических ошибок (ai.md, blockchain.md, docs/README.md, ADR-004, INDEX_ANALYSIS) | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.1 | Done |
| D-002 | Добавить YAML FM к 7 файлам без front-matter | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.2 | Done |
| D-003 | Обновить 10+ ссылок на `94-Standards/` → `genome/standards/` | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.6 | Done |
| D-004 | Синхронизировать FM status с реальностью — 15+ файлов где draft != Implemented | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.3 | Done |
| D-005 | Исправить ссылку `00-Overview/` → `01-Overview/` в docs/README.md | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.6 | Done |

## P1 — Prompt Library Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-062 | Синхронизировать canonical inventory и navigation layer prompt library | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-062 | Done |
| D-063 | Выстроить include-layer как canonical owner shared governance rules | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-063 | Done |
| D-064 | Истончить `execute-tz-task` до task-aware adapter поверх `change-workflow` | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-064 | Done |

## P1 — README (вымышленное содержание)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| R-001 | `patterns/README.md`: полностью вымышленная структура (factory/, adapter/, observer/, singleton/, di/ — не существуют; реальные patterns_manager.py, pattern_templates/ не упомянуты) | [README Audit 2026-02-19] | Done |
| R-002 | `resources/README.md`: полностью вымышленная структура (assets/, locales/, themes/, schemas/ — не существуют; реальные resources_manager.py, storage/, communication/ не упомянуты) | [README Audit 2026-02-19] | Done |
| R-003 | `security/README.md`: полностью вымышленная архитектура (CryptoService, KeyManager, crypto/, auth/ — не существуют; реальный security_manager.py, communication/ не упомянуты) | [README Audit 2026-02-19] | Done |
| R-004 | `docs/50-Security/README.md`: все 7 ссылок на стандарты битые — пути `genome/standards/security/...` не существуют (правильно: `genome/standards/sec/`), ID не совпадают с реальными | [README Audit 2026-02-19] | Done |
| R-005 | `docs/90-Testing/README.md`: все ссылки на стандарты битые — путь `genome/standards/testing/...` не существует (правильно: `genome/standards/test/`), STD-TEST-UNIT-001 не существует | [README Audit 2026-02-19] | Done |
| R-006 | `docs/README.md`: ссылка `00-Overview/` не существует (→`01-Overview/`), путь к STANDARDS_REGISTRY неверен, `genome/standards/logging/`→`log/`, счётчик 27→45 стандартов | [README Audit 2026-02-19] | Done |

## P1 — Инфраструктура

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-006 | Конфликт Pyright: `typeCheckingMode = "standard"` (pyproject.toml) vs `"basic"` (pyrightconfig.json); `extraPaths` расходятся | [Deep Audit 2026-02-19] | Done |
| I-007 | `coverage.run.source` (pyproject.toml) не включает monitoring, patterns, resources, security — 4 модуля полностью исключены из покрытия | [Deep Audit 2026-02-19] | Done |
| I-008 | isort mirror `v5.10.1` (pre-commit) конфликтует с pip `isort==7.0.0` — разные версии форматируют по-разному | [Deep Audit 2026-02-19] | Done |
| I-009 | mypy hook: `--cache-dir=/dev/null` — Unix-path, не работает на Windows | [Deep Audit 2026-02-19] | Done |
| I-010 | CI: нет workflow для unit-тестов при `push`; только `pull_request` trigger — при прямых пушах CI не запускается | [Deep Audit 2026-02-19] | Done |

## P1 — Укрепление Black и ограничителя Bandit (2026-07-05)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-374 | Сквозным контуром укрепить нормализацию Black и нулевой шлюз Bandit | [Audit TZ](../98-Reviews/execution/2026-07/black-pre-freeze-and-bandit-ratchet-hardening/DEV_TZ_black-pre-freeze-and-bandit-ratchet-hardening_2026-07-05.md) §Task Contract D-374 | Done |
| I-1054 | Укрепить controlled pre-freeze normalization Black с immutable tool/config binding, exact staging, idempotence, cache/process evidence | [Audit TZ](../98-Reviews/execution/2026-07/black-pre-freeze-and-bandit-ratchet-hardening/DEV_TZ_black-pre-freeze-and-bandit-ratchet-hardening_2026-07-05.md) §I-1054 | Done |
| I-1055 | Атомарно внедрить нулевой шлюз Bandit, устранить все находки и удалить базовую линию, счётчиковый ограничитель и `nosec` | [Audit TZ](../98-Reviews/execution/2026-07/black-pre-freeze-and-bandit-ratchet-hardening/DEV_TZ_black-pre-freeze-and-bandit-ratchet-hardening_2026-07-05.md) §I-1055 | Done |
| D-375 | Независимо принять D-374, погасить авторизацию и удалить временные debt/repair/cache артефакты | [Audit TZ](../98-Reviews/execution/2026-07/black-pre-freeze-and-bandit-ratchet-hardening/DEV_TZ_black-pre-freeze-and-bandit-ratchet-hardening_2026-07-05.md) §D-375 | Done |

## P1 — Связь агента с системой передачи патчей и матрица решений (2026-07-07)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-376 | Открыть контур укрепления связи агента с системой передачи патчей, матрицей решений и предварительной проверкой пакетов | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §Контракт задачи D-376 | Done |
| I-1056 | Описать единую карту возможностей `direct_patch` и `verified_handoff` без второй политики маршрутизации | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1056 | Done |
| I-1057 | Добавить предварительную проверку `direct_patch` по `route_profile`, обязательным полям и ссылкам решений | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1057 | Done |
| I-1058 | Улучшить классификацию отказов `direct_patch` и вывод причины отказа без добавления `repair/resume` | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1058 | Done |
| I-1059 | Ввести жизненный цикл ошибок до создания носителя `verified_handoff` с безопасным журналом исправлений | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1059 | Done |
| I-1060 | Сохранить безопасность `source_patch_sha256` через проверяемую цепочку происхождения исправленного кандидата | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1060 | Done |
| I-1061 | Развести проверку, синхронизацию и изменение дерева в планах доказательства и шлюзах коммита | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1061 | Done |
| I-1062 | Закрепить требования к артефактам проверки и закрытия, включая `Physical Integration Proof` и `physical-use class` | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1062 | Done |
| I-1063 | Добавить проверочные сценарии измерения для навигации агента по системе передачи патчей | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1063 | Done |
| I-1064 | Добавить видимую индикацию выполнения штатных patch-маршрутов без внешних wrapper | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1064 | Done |
| I-1065 | Добавить узкий маршрут ремонта активного pre-carrier authorization profile без повторной авторизации | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1065 | Done |
| I-1066 | Закрепить дисциплину канонической выдачи patch package и команд | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §I-1066 | Done |
| D-377 | Терминально принять D-376 после внедрения, проверки и удаления временных следов исправлений | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-agent-navigation-and-preflight-hardening/DEV_TZ_patch-system-agent-navigation-and-preflight-hardening_2026-07-07.md) §D-377 | Done |

## P1 — Доверие, конкуренция, вывод и публикация системы передачи патчей (2026-07-10)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-378 | Открыть контур укрепления trust, concurrency, process-output и review-publication boundaries для `direct_patch` и `verified_handoff` без третьего маршрута; bounded local self-bootstrap addendum разрешает частичный substrate I-1068/I-1069/I-1071 | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §D-378 | In Progress |
| I-1067 | Связать direct approval с operation-aware digest и новой canonicalization semantics без нарушения verified v3 digest | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1067 | Done / Accepted |
| I-1068 | Ввести общий repository mutation lock и доказуемое stale recovery для direct и verified mutating modes | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1068 | Done / Accepted / Finalized |
| I-1069 | Закрыть принятую волну I-1069; дальнейший scope ограничен отдельным `VPHWINPATH-001` | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1069 | Done / Accepted / Consumed |
| I-1070 | Перевести finalizer на receipt-bound review discovery, подтвердить rolling parity и отсутствие нового terminal route | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1070 | Wave A implementation candidate under exact review |
| I-1071 | Выполнить Wave B: output/executable/path-safety и полный отрицательный corpus с proof-routing migration | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1071 | Pending / Wave B |
| I-1072 | Сохранить `TERMREPAIR-001` как no-new-route; полный отрицательный proof перенесён в I-1071 | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §I-1072 | Decision accepted / full negative proof deferred to I-1071 |
| D-379 | Терминально принять D-378 после независимой проверки, terminal proof и удаления временных следов | [Audit TZ](../98-Reviews/execution/2026-07/patch-system-runtime-trust-concurrency-output-publication-hardening/DEV_TZ_patch-system-runtime-trust-concurrency-output-publication-hardening_2026-07-10.md) §D-379 | Blocked |

## P1 — BSP

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-001 | BSP README описывает несуществующие файлы — привести в соответствие | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §6.2 | Done |
| S-002 | BSP `pytest.ini` — копия AIFE (`--cov=main`) → исправить на `--cov=bsp` | [BSP Audit](audits/AUDIT_AIFE_BSP_2026-02-19.md) §3 | Done |
| S-003 | BSP: нет тестов и каталога tests/ — создать минимальный smoke test | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §6.2 | Done |
| S-004 | BSP AGENTS.md пуст (0 байт) — заполнить или удалить | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §6.2 | Done |

## P1 — Security Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-005 | Рефакторинг `security/` в подпакеты (auth, crypto, data, api, blockchain, secrets, review) — L4 | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-001 | Done |
| S-006 | Переименовать тесты с batch B1–B9 на доменные имена (test_auth_session_jwt, test_mfa_authz и т.п.) | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-002 | Done |
| S-007 | Создать `tests/unit/security/conftest.py`, вынести fixture `security_app_context` из 9 файлов | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-003 | Done |
| S-008 | Полностью переписать `security/README.md`: все 20 файлов, event routing, policy boundaries, logging arch | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-004 | Done |
| S-009 | Переписать `docs/50-Security/security.md`: убрать несуществующие файлы, актуализировать архитектуру | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-005 | Done |

## P1 — Качество гейтов / Schema / Инструкции (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| QG-001 | Schema `category` enum без `monitoring`/`performance` — 9 стандартов MON/PERF не проходят валидацию. Добавлен `redirect` в `doc_type` enum | [Quality Gate Audit 2026-02-19] | Done |
| QG-002 | `STANDARDS_REGISTRY_REDIRECT.md`: `superseded_by` → `deprecated_by`, удалена устаревшая авто-таблица (90 строк) | [Quality Gate Audit 2026-02-19] | Done |
| QG-003 | `STANDARDS_REGISTRY.md` FM: нет `title`, `created`, `category`, `doc_type` — не соответствует schema | [Quality Gate Audit 2026-02-19] | Done |
| QG-004 | Порядок EN/RU в docstring: AGENTS.md (EN первым) vs copilot-instructions.md (RU первым) → унифицировано: RU первым | [Quality Gate Audit 2026-02-19] | Done |
| QG-005 | `asyncio_mode` конфликт: `pytest.ini` = `strict`, доки рекомендуют `--asyncio-mode=auto` (5 мест в 3 файлах) → убрано из доков | [Quality Gate Audit 2026-02-19] | Done |
| QG-006 | Покрытие “≥80%” в доках vs реальные пороги 40/45/24% — заменено на ссылку `.aife/coverage_thresholds.json` | [Quality Gate Audit 2026-02-19] | Done |
| QG-007 | Валидаторы структуры/индексов дают низкий сигнал: 66 warnings, `file_placement_rules.json` устарел, индексов нет | [Quality Gate Audit 2026-02-19] | Done |

## P1 — Стандарты (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| STD-003 | Исправить 11 битых кросс-ссылок в стандартах (STD-TEST-UNIT-001, STD-DB-SCHEMA-002, и др.) | [Standards Review](standards_review_2025-01.md) §4, §16 | Done |
| STD-004 | Стандартизировать формат версий: добавить правило 3-part semver в NAMING-001, привести все файлы | [Standards Review](standards_review_2025-01.md) §2.2 | Done |
| STD-005 | Исправить `category: logging` → `monitoring` во всех 5 MON + `quality` → `performance` в 4 PERF | [Standards Review](standards_review_2025-01.md) §2.6 | Done |
| STD-006 | Утвердить STD-DOC-METADATA-001 (proposed → approved) — мета-стандарт для всех остальных | [Standards Review](standards_review_2025-01.md) §8 | Done |
| STD-007 | Добавить навигацию к стандартам в copilot-instructions.md и промпт-файлы (42 из 45 не упомянуты в агентских инструкциях) | [Standards Review](standards_review_2025-01.md) §6.3 | Done |

## P1 — Genome Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-022 | Дополнить доменные индексы arch и governance | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-022 | Done |
| D-023 | Синхронизировать версии README-индексов с реестром | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-023 | Done |
| D-024 | Исправить lifecycle-status конфликт STD-DOC-METADATA-001 | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-024 | Done |
| D-025 | Заменить фантомные cross-reference STD-* ID | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-025 | Done |
| D-026 | Исправить несуществующие файлы в related paths | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-026 | Done |
| D-027 | Устранить PostgreSQL vs SQLite конфликт в PERF | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-027 | Done |
| D-028 | Развести зоны ответственности TEST-PERF и PERF-BENCHMARK | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-028 | Done |
| D-029 | Добавить next_review_due в 5 API стандартов | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-029 | Done |
| D-030 | Убрать placeholder из sec/README.md | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-030 | Done |
| D-045 | Добавить/согласовать next_review_due в стандартах без даты ревью | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P1 — Next Sprint | Done |
| D-046 | Разобрать открытые implementation чекбоксы: закрыть или вынести в отдельные rollout-TZ | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P1 — Next Sprint | Done |
| D-047 | Провести доменный rollout-wave для ARCH/DATA/MON/PERF/DOC-INDEX/GOV-IMPROVEMENT | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P1 — Next Sprint | Done |

## P1 — UI Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-047 | Реализовать NavigatorPanel: api_connection + indicator_selection + advisor_selection | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-047 | Done |
| C-048 | Реализовать ToolsPanel: QTabWidget с вкладками Trade Info, Events, Settings и др. | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-048 | Done |
| C-049 | Реализовать StrategyTesterPanel: strategy_selection + backtest_controls + results | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-049 | Done |
| C-050 | Реализовать DataPanel: QTableWidget с OHLCV, bid/ask, volume | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-050 | Done |
| C-051 | Реализовать Menu Sections: 8 разделов меню (file, edit, view, ai, blockchain, patterns, tools, help) | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-051 | Done |
| C-052 | Реализовать Toolbar Sections: FileToolbar, GraphsToolbar, AIToolbar и др. через @register_toolbar | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-052 | Done |
| C-053 | Реализовать UI Communication Layer: event_listener + state_updater + log_consumer + connection_tracker | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-053 | Done |
| C-054 | Реализовать Notification Center: notification_center + notifications_widget + alert_viewer | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-054 | Done |
| C-055 | Реализовать Localization: localization.py + en.json + ru.json | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-055 | Done |
| C-056 | Реализовать User Telemetry: user_interaction + user_action_logger | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-056 | Done |
| D-055 | PNG-ассеты: минимальный rollout иконок для MenuBar/ToolBar | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-055 | Done |
| D-056 | Автообновление иконок при смене темы (theme-driven refresh) | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-056 | Done |
| D-057 | Интеграция иконок в ToolBar actions через базовый icon API | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-057 | Done |
| D-058 | Интеграция иконок в MenuBar sections через helper базовой секции | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-058 | Done |
| D-061 | Разделить Monitoring в MenuBar: отдельный системный раздел + rename AI Monitoring | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-061 | Done |

## P0 — Test Cost Unification Audit (2026-03-25)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-111 | Провести поконтурную validation для `pytest-xdist` до любых заявлений о rollout | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-111 | Done |
| D-112 | Собрать базовые wall-clock-замеры и cost buckets для ordinary test contours | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-112 | Done |
| D-113 | Проверить реализуемость pooled harness для selected Qt-heavy families | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-113 | Done |
| D-114 | Утвердить валидационную базовую линию для severity marker / validator по expensive-pattern family | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-114 | Done |
| D-115 | Выпустить канонический cheap-by-default governance-пакет для ordinary tests | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-115 | Done |
| D-116 | Унифицировать Qt bootstrap authority и bounded heavy-runtime harness seams | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-116 | Done |
| D-117 | Материализовать внедрение в prompt/include для regression-first и cost-aware verification loop | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-117 | Done |
| D-118 | Синхронизировать truth-layers в docs, taxonomy wording и устаревшие `e2e`-утверждения после remediation wave | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-118 | Done |
| D-119 | Выпустить validator / marker enforcement для expensive-pattern family | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-119 | Done |
| D-120 | Выполнить optional staged rollout `pytest-xdist` как wall-time-only mitigation | [Research TZ](../98-Reviews/research/2026-03/test-cost-unification-audit/DEV_TZ_test-cost-unification-audit_2026-03-25.md) §D-120 | Done |

## P0 — Test Package Operating Model (2026-03-26)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-121 | Канонический артефакт test-package operating model (companion standard) | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-121 | Done |
| D-122 | Уточнение taxonomy для edge-families и exceptional paths | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-122 | Done |
| D-123 | Governance baseline model, evidence schema и drift detection | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-123 | Done |
| D-124 | Enforcement split, exception ladder, review triggers, onboarding | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-124 | Done |
| D-125 | Leakage observability probes + reset-complete contract | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-125 | Done |
| D-126 | Random-order / repeated-run validation contour | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-126 | Done |
| D-127 | Offscreen/display parity explicit proof boundary | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-127 | Done |
| D-128 | Explicit `expensive_runtime` marking на confirmed hot families | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-128 | Done |
| D-129 | Session-bounded MainWindow validation prototype | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-129 | Done |
| D-130 | Condition-based settle API prototype | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-130 | Done |
| D-131 | Repeated-sequence collapse candidates | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-131 | Done |
| D-132 | Prompt/include + architecture.md downstream sync | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-132 | Done |
| D-133 | xdist wider rollout criteria (optional) | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-133 | Done |
| D-134 | MainWindow pooled-reuse: terminal debt closure (DF-6) | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-134 | Done |
| D-135 | Settle API: terminal debt closure (DF-7) | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-135 | Done |
| D-136 | Canonical storage contract for test-run outputs / execution-output artifacts | [Research TZ](../98-Reviews/research/2026-03/test-package-operating-model/DEV_TZ_test-package-operating-model_2026-03-26.md) §D-136 | Done |

## P1 — UI MainWindow + Chart Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-076 | Создать chart/utilities/ каноническую директорию: shortcut_manager, layout_manager, theme_switcher, error_logger, feedback_collector | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-076 | Done |
| C-077 | Реализовать chart_tools.py: HorizontalLine, TrendLine, FibonacciRetracement, ChartToolManager, serialization | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-077 | Done |
| C-078 | Реализовать scoped event routing для multi-chart isolation: topic convention chart.<id>.*, per-chart data feed | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-078 | Done |
| C-079 | Реализовать BottomTabZone orchestration: state machine (hidden/collapsed/expanded/pinned), persistence, drag-resize | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-079 | Done |
| C-080 | Реализовать RenderBudgetManager: frame budget 16ms, coalesce policy, degrade policy, DataThrottlePolicy | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-080 | Done |
| C-081 | Создать perf/scalability test harness: benchmark suite для 1k-20k свечей, multi-chart scaling, NFR assertions | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-081 | Done |
| C-082 | Реализовать shortcut governance + conflict scanner: duplicate detection, chart-specific shortcuts | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-082 | Done |
| C-083 | Заменить placeholder handlers в ai/blockchain/patterns/tools/monitoring menu и domain toolbar на ActionRegistry dispatch | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-083 | Done |
| C-084 | Подключить indicator windows к production data contract: set_indicator_data API, lifecycle sync, убрать demo | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-084 | Done |
| C-096 | Обобщить splitter foundation и внедрить `dock_panels_adapter` без big-bang rewrite `dock_panels`, сохранив zero-collapse и restore semantics | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-096 | Done |
| C-097 | Реализовать `WorkspaceShell` и unified `content_host` protocol; сохранить `ChartTabManager` как `content_host` в v1 | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-097 | Done |
| C-098 | Реализовать `DragSession` и `DropTargetResolver` как graph/registry-driven drag-drop runtime без reuse obsolete experimental singleton-flow | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-098 | Done |
| C-099 | Реализовать `WorkspaceSnapshot`, canonical store в `UISettings` и versioned migrator для unified persistence path `MainWindow` | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-099 | Done |
| C-100 | Реализовать graph-authoritative toolbar bridge с native `QMainWindow` toolbar runtime только как subordinate apply/fallback layer, без full cutover в первой wave | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-100 | Done |
| C-101 | Перевести `MainWindow` popup/reset/default capture wiring на единый workspace facade без превращения `MainWindow` в layout monolith | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-101 | Done |
| C-102 | Зафиксировать test matrix, quarantine experimental drag-drop и final closure gate для workspace framework, включая canonicalization `architecture.md` только по факту runtime files | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-102 | Done |
| C-104 | Реализовать owner-side apply path для фактического panel drag/drop, чтобы accepted `REPARENT_ZONE` intent приводил к реальному перемещению managed panels без возврата ownership в `drag_drop`, с rollback-safe owner apply и mirror sync | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-104 | Done |
| C-105 | Реализовать end-to-end gesture path для фактического panel drag/drop, чтобы managed panels реально перетаскивались мышью через `DragSession -> WorkspaceFacade -> DockPanelsManager.apply_panel_drop_intent(...)` без возврата ownership в `drag_drop` | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-105 | Done |
| C-106 | Реализовать visual drag presentation layer для фактического panel drag/drop, чтобы source panel визуально отделялась, target-zone подсвечивалась и drag/drop воспринимался пользователем как реальное перетаскивание без возврата ownership в `drag_drop` | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-106 | Done |
| C-107 | Реализовать bounded floating panel window mode, повторный захват/reinsertion и global perimeter drop behavior вокруг `MainWindow` для panel drag/drop без возврата ownership в `drag_drop`; target selection оформить через явные insertion controls (perimeter arrows + local insertion cross), а не через хрупкие hit-zones | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-107 | Done |
| C-108 | Реализовать "Свободу Всем Панелям": standalone panel freedom + deterministic release handoff, включая rollback-safe release failure path и финальный floating owner contract без bounded-only surrogate semantics | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-108 | Backlog |
| C-109 | Удалить дублированный status block в DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md:1294-1305 с устаревшими статусами C-098/C-106/C-107 | [Dead-Path Audit TZ](../98-Reviews/audits/2026-03/ui-dead-path/DEV_TZ_ui-dead-path_2026-03-15.md) §C-109 | Done |
| C-110 | Обновить vestigial package contracts в workspace/__init__.py и animation/__init__.py — убрать C-092 skeleton claims, отразить live C-093…C-107 state | [Dead-Path Audit TZ](../98-Reviews/audits/2026-03/ui-dead-path/DEV_TZ_ui-dead-path_2026-03-15.md) §C-110 | Done |
| C-111 | Принять решение по 5 synthetic-only constraint helpers в zone_constraints.py: wire в ZoneTree mutation API (A) или remove from __all__ + internalize (B) | [Dead-Path Audit TZ](../98-Reviews/audits/2026-03/ui-dead-path/DEV_TZ_ui-dead-path_2026-03-15.md) §C-111 | Done |

### C-079 — post-closure stabilization (2026-03-03)

- Статус: выполнено как дополнительные действия в рамках уже закрытого `C-079` (без открытия нового research-ID).
- Что зафиксировано после closure:
  - BottomTabZone принудительно скрыт в UX-flow (single-tab strip), кнопка `+` удалена из интерфейса (оставлен backward-compatible API без создания вкладок).
  - Выбор символа из Market Overview переведён на explicit intent: открытие графика по ПКМ (`Открыть график`) и создание новой вкладки.
  - Заголовки вкладок унифицированы в формате `SYMBOL,TIMEFRAME`, добавлено контекстное закрытие вкладки.
  - Устранён theme desync контекстного меню Market Overview (резолв `ui_settings` через parent/base_widget chain), синхронизирован единый popup-menu стиль для dark/light.
  - Добавлены/обновлены регрессионные unit-тесты в `tests/unit/ui/test_chart_tab_manager.py` и `tests/unit/ui/test_market_overview.py`.

## P2 — Код

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-007 | Copy-paste менеджеры (7 модулей, ~4000 строк docstring при ~400 строк кода, ratio 10:1) — оценить необходимость | [Deep Audit 2026-02-19] + [C-007 Assessment](implementations/docstring-analysis/C-007_manager_docstring_necessity_assessment_2026-02-22.md) | Done |
| C-008 | `AppContext.get_manager()` — хрупкий string matching (`"core" in name`) → типизированный реестр | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 + [Deep Audit 2026-02-19] | Done |
| C-009 | Смешение f-string и %-formatting в логировании → стандартизировать (f-string форматируется всегда, даже если уровень отключён) | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 | Done |
| C-010 | Непоследовательный error handling в process_event → стандартизировать | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.3 | Done |
| C-011 | `pytest.ini addopts --cov=main` не покрывает ai, blockchain, initializer, monitoring, patterns, resources, security | [Deep Audit 2026-02-19] | Done |
| C-017 | `BaseManager.initialize()` содержит базовое логирование, но ни один подкласс не вызывает `await super().initialize()` — логирование теряется | [Deep Audit 2026-02-19] | Done |
| C-018 | `AppContext` свойства (log_manager, signal_communication и др.) аннотированы как `Any` → потеря типовой безопасности по всей кодовой базе | [Deep Audit 2026-02-19] | Done |
| C-112 | Удалить dead DragPayload.source / .binding property accessors + private descriptor classes (mutation probe confirmed safe) | [Dead-Path Audit TZ](../98-Reviews/audits/2026-03/ui-dead-path/DEV_TZ_ui-dead-path_2026-03-15.md) §C-112 | Done |
| C-113 | Удалить или формализовать ghost package dock_panels/components/ (пустой, zero callers, zero tests) | [Dead-Path Audit TZ](../98-Reviews/audits/2026-03/ui-dead-path/DEV_TZ_ui-dead-path_2026-03-15.md) §C-113 | Done |

## P2 — Genome Standards ARCH Research (2026-03-18)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-073 | Выпустить disposition matrix `architecture.md` vs runtime vs standards | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-073 | Done |
| D-074 | Зафиксировать internal typing boundary для `DependencyManager` без второго public runtime path | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-074 | Done |
| D-080 | Обновить `architecture.md` по disposition matrix и implementation state (Phase B; downstream после closure Phase A) | [Research TZ](../98-Reviews/research/2026-03/genome-standards-arch/DEV_TZ_genome-standards-arch_2026-03-18.md) §D-080 | Done |

## P2 — Документация

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-006 | Заполнить или удалить 16 stub-документов (docs/20-AI, 25-Blockchain, 40-Monitoring, 44-Patterns, 45-Resources — по 1-2 файла) | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.4 + [Deep Audit 2026-02-19] | Done |
| D-007 | Устранить 4 дублирования контента (overview↔architecture и др.) | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.5 | Done |
| D-008 | Стандартизировать FM — добавить id, version во все файлы | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §5.3 | Done |
| D-009 | Удалить .bak файлы из git (security_manager.py.bak, 95-Reports/, 98-Reviews/) | [Deep Audit 2026-02-19] | Done |
| D-010 | Убрать обёртки ` ```markdown ` из 20+ стандартов (sec×3, governance×3, api×2, test×1, perf×1, mon×2) — мешает рендерингу | [Deep Audit 2026-02-19] | Done |
| D-011 | Дополнить README-индексы: 30-Communication, 44-Patterns | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §4.6 | Done |

## P2 — Prompt Library Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-065 | Истончить `audit-session` и `research-session` до guided launchers | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-065 | Done |
| D-066 | Зафиксировать governance loop для context-layer prompt library | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-066 | Done |

## P2 — UI Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-031 | Убрать silent exception handling вокруг logging (22+ мест try/except pass) | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-031 | Done |
| C-032 | Исправить corrupted UTF-8 в логах CentralWidget | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-032 | Done |
| C-033 | Интегрировать ToolbarRegistry в ToolBarFactory | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-033 | Done |
| C-034 | Ревизия мёртвого кода UI: GlobalEventController, set_ui_adapter, ActionRegistry без LogManager | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-034 | Done |
| C-035 | Переименовать UIComponents/ → ui_components/ (PEP 8) | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-035 | Done |
| C-036 | Добавить persist в UISettings.update_setting() | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-036 | Done |
| C-037 | Заполнить __all__ в UI layout пакетах | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-037 | Done |
| C-038 | Перенести ENABLE_TRACEBACK в config/env | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-038 | Done |
| C-039 | Упростить container_type в DockPanelsManager | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §C-039 | Done |
| D-018 | Расширить ui/README.md по шаблону STD-DOC-README-001 | [Audit TZ](../98-Reviews/audits/2026-02/ui/TZ_ui_2026-02-20.md) §D-018 | Done |

## P2 — README (неполное содержание)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| R-007 | Корневой `README.md`: 12+ фантомных стандартов Phase 0/1 (STD-VCS-*, STD-CODE-*, STD-OPS-* — не существуют), устаревшие счётчики (134 тестов, 47 стандартов) | [README Audit 2026-02-19] | Done |
| R-008 | 8 модульных README неполные — не упоминают `communication/` подкаталоги: core (+ api/, management/), ai, blockchain, monitoring (+ metrics/, alerting/), ui (+ base_components/, dashboard/, localization/) | [README Audit 2026-02-19] | Done |
| R-009 | `initializer/README.md`: упомянуты 2 из 11 файлов — пропущены base_manager, context, context_builder, context_factory, dependency_manager, main_logic, main_runner, system_initializer_builder, task_manager | [README Audit 2026-02-19] | Done |
| R-010 | `tests/README.md`: неверные имена файлов (test_main_unit→test_main), пропущены каталоги smoke/, smoke_tests/, unit/core/, unit/validators/. Команда `venv\Scripts\python` — проект использует pyenv | [README Audit 2026-02-19] | Done |
| R-011 | `tests/performance/README.md`: 3 из 5 benchmark-файлов не существуют (test_ai/blockchain/ui_performance.py) | [README Audit 2026-02-19] | Done |
| R-012 | `genome/standards/arch/README.md`: 2 из 3 стандартов (ASYNC-001, PATTERNS-001) не упомянуты | [README Audit 2026-02-19] | Done |
| R-013 | `genome/standards/README.md`: устаревший заголовок «Раздел 94», пропущены домены async/events/ops, счётчики устарели | [README Audit 2026-02-19] | Done |

## P2 — Инфраструктура

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-001 | 8 уязвимостей pip-audit (filelock, urllib3, virtualenv, werkzeug) | [BSP Audit](audits/AUDIT_AIFE_BSP_2026-02-19.md) §2 | Done |
| I-002 | 24 ошибки metadata + 122 предупреждения (validate_markdown_metadata) | [BSP Audit](audits/AUDIT_AIFE_BSP_2026-02-19.md) §2 | Done |
| I-003 | BSP: добавить базовый CI (lint + pytest + links + pip-audit) — отложено до этапа фактической интеграции BSP (`blocked by BSP integration readiness`) | [BSP Audit](audits/AUDIT_AIFE_BSP_2026-02-19.md) §3 | Backlog |
| I-004 | Создать mermaid Decision Tree для STD-CHANGE-001 | Бывший REC-001 | Done |
| I-005 | Автоматизировать STANDARDS_REGISTRY.md (auto-таблица) | Бывший REC-018 | Done |
| I-011 | `pre-commit` в production `requirements.in` → перенести в `requirements-dev.in` (раздувает production deps: cfgv, nodeenv, virtualenv) | [Deep Audit 2026-02-19] | Done |
| I-012 | `example.env` неполный: нет AI env vars (OPENAI_API_KEY, MODEL_PATH), нет BSP_PATH/PYTHONPATH | [Deep Audit 2026-02-19] | Done |
| I-013 | Дублирование тестовых каталогов: `tests/smoke/` и `tests/smoke_tests/` — объединить | [Deep Audit 2026-02-19] | Done |
| I-014 | `docs/26-Configuration/config_reference-1.md` — дубликат `config_reference.md`, удалить | [Deep Audit 2026-02-19] | Done |
| I-015 | STANDARDS_REGISTRY.md `updated: 2025-11-06` — дата в front-matter не обновлена после правок 2026-02-19 | [Deep Audit 2026-02-19] | Done |
| I-016 | CI workflows: `actions/setup-python@v4` → `v5` (устаревший action) → исправлено в B-004 | [Deep Audit 2026-02-19] | Done |
| I-017 | Версии pre-commit hooks рассинхронизированы с pip: black 25.1.0 vs 25.9.0, isort mirror 5.x vs pip 7.x | [Deep Audit 2026-02-19] | Done |

## P2 — Стандарты (Done)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| STD-008 | Добавить `next_review_due` во все стандарты с `review_cycle_days` (SEC×7, GOVERNANCE-GENOME) | [Standards Review](standards_review_2025-01.md) §2.8 | Done |
| STD-009 | Исправить путь related в STD-API-DOCS-001: `doc/STD-DOC-METADATA-001.md` → `doc/metadata/...` | [Standards Review](standards_review_2025-01.md) §4 | Done |
| STD-010 | Разрешить дублирование `async/`: redirect в README на STD-ARCH-ASYNC-001 или перемещение | [Standards Review](standards_review_2025-01.md) §14 | Done |
| STD-011 | Исправить противоречие STD-DOC-INSTRUCTIONS-001: «Статус: ACTIVE» в теле vs `approved` в FM | [Standards Review](standards_review_2025-01.md) §8 | Done |
| STD-012 | Создать `scripts/validate_registry.py` — автоматическая сверка FM файлов с Registry | [Standards Review](standards_review_2025-01.md) §17 | Done |

## P2 — Genome Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-031 | Зафиксировать правило размещения ASYNC vs ARCH | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-031 | Done |
| D-032 | Добавить поле domain в front-matter стандартов | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-032 | Done |
| D-033 | Синхронизировать OWNERS_ALIASES и owner-policy | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-033 | Done |
| D-034 | Нормализовать next_review_due в README-индексах | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-034 | Done |
| D-035 | Закрыть просроченные reviews стандартов | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-035 | Done |
| I-019 | Восстановить полноту registry слоя (JSON + markdown) | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §I-019 | Done |
| I-018 | Реализовать STD-* validator + pre-commit gate | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §I-018 | Done |
| D-036 | Исправить self-link и нумерацию секций (DOC/CHANGE) | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-036 | Done |
| D-037 | Унифицировать related path conventions | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-037 | Done |
| D-038 | Нормализовать значения category | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-038 | Done |
| D-039 | Стандартизировать review_cycle_days в SEC домене | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-039 | Done |
| D-040 | Обновить governance/change lifecycle metadata | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-040 | Done |
| D-041 | Добавить examples и planned-маркировку future standards | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_2026-02-22.md) §D-041 | Done |
| D-048 | Добавить автоматический closure-readiness отчёт (скрипт + CI артефакт) | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P2 — Backlog | Done |
| D-049 | Добавить gate: approved стандарт не может иметь missing related и non-semver version | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P2 — Backlog | Done |
| D-050 | Обновить guidance по standard lifecycle (когда чекбоксы допустимы в approved) | [Audit TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_closure_2026-02-23.md) §P2 — Backlog | Done |

## P0 — Security Logging Audit (2026-02-25)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-030 | Создать `sanitize_security_payload` + per-category whitelist + recursive redaction | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-030 | Done |
| S-031 | Применить sanitizer в `SecurityCommunicationAdapter.emit()/route_event()` + emoji fix | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-031 | Done |
| S-032 | Применить sanitizer в `SecurityEventDispatcher.dispatch()` + fallback ветки | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-032 | Done |

## P1 — Security Logging Audit (2026-02-25)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-033 | Реализовать auto-escalation reject events до WARNING/ERROR в dispatch | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-033 | Done |
| S-035 | Реализовать `SecurityLogger` по STD-SEC-LOG-001 (MASK_PATTERNS + structured JSON) | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-035 | Done |
| S-036 | Добавить event taxonomy (dot-notation) в `extra` dict | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-036 | Done |
| S-037 | Реализовать `AuditLogger` с SHA-256 hash chain | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-037 | Done |

## P2 — Security Logging Audit (2026-02-25)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-034 | Исправить component prefix на `[SecurityEventDispatcher]` + emoji consistency | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-034 | Done |
| S-038 | Внести clarification amendment в STD-LOG-001 §1 (pure functions exemption) | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-038 | Done |
| S-039 | Реализовать PII masking utilities | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-039 | Done |
| S-040 | Реализовать SIEM integration (`ElasticsearchHandler`) | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-040 | Done |
| S-041 | Реализовать alerting rules (`BruteForceDetector` и escalation) | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-041 | Done |
| S-042 | Реализовать log retention policy enforcement | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-042 | Done |
| S-043 | Добавить masking `session_id` при logout (hash/partial) | [Audit TZ](../98-Reviews/audits/2026-02/security-logging/TZ_security-logging_2026-02-25.md) §S-043 | Done |

## P2 — Security Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| S-010 | Ревью `docs/50-Security/SECURITY_ENFORCEMENT.md`: обновить `next_review_due`, статусы planned стандартов | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-006 | Done |
| S-011 | Сократить docstring `initialize()`/`shutdown()` до фактической реализации, вынести TODO в backlog | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-007 | Done |
| S-012 | Зафиксировать `threat`/`compliance` event categories как planned-capability в docs/ADR | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-008 | Done |
| S-013 | Нормализация public API docstrings по STD-DOC-DOCSTRING-001 (RU+EN start lines) во всех `security/*.py` | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-009 | Done |
| S-014 | Документировать «logging только в SecurityManager, policy = pure functions» в README и docs | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-010 | Done |
| S-015 | Добавить `log_manager` в Args docstring `SecurityCommunicationAdapter.__init__` | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-011 | Done |
| S-016 | Создать пустой `tests/unit/security/__init__.py` | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-012 | Done |
| S-017 | Декомпозиция SecurityManager (~600 строк): извлечь event handlers или применить Registry-паттерн | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-013 | Done |
| S-018 | Унифицировать именование B1 integration-теста с B2–B9 (решается при S-006) | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-014 | Done |
| S-019 | Сократить `security/__init__.py` до фасадного минимума после рефакторинга S-005 | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-015 | Done |
| S-020 | Добавить TTL/max_entries eviction для in-memory storages (sessions, rate limiters, refresh tokens) | [Audit TZ](../98-Reviews/audits/2026-02/security/TZ_security_2026-02-23.md) §UF-016 | Done |

## P2 — UI Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-057 | Реализовать Chart Utilities: theme_switcher, layout_manager, shortcut_manager | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-057 | Backlog |
| C-058 | Реализовать Chart Tools: drawing tools (линия, горизонталь, Фибоначчи) | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-058 | Backlog |
| C-059 | Реализовать Market Overview Extended: exchange connector + real-time price updates | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-059 | Backlog |
| C-060 | Реализовать Toolbar UI Components: ToolButton, ToolMenu, ToolSeparator | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-060 | Backlog |
| C-061 | Реализовать Toolbar Management: toolbar_controller + toolbar_customization | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-061 | Backlog |
| C-062 | Подключить Toolbar Slots: connect QAction'ов в Default/ExtraToolbar | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-062 | Backlog |
| C-063 | Реализовать GlobalEventController: реальные обработчики theme_changed, ui_updated | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-063 | Backlog |
| C-064 | Создать Integration Tests: 3+ end-to-end тестов UI flow (menu→chart→layout) | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-064 | Backlog |
| C-065 | Исправить runtime theme switch: ViewMenu -> MainWindow -> ChartWidget (обновление palette) | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §C-065 | Done |
| D-051 | Исправить Path/Case Drift: UIComponents→ui_components, обновить architecture.md | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §D-051 | Backlog |
| D-052 | Консолидировать UI документацию: ui/charts vs ui/layout/chart, TODO-статусы | [Research TZ](../98-Reviews/research/2026-02/ui/DEV_TZ_ui_2026-02-25.md) §D-052 | Backlog |
| D-059 | Канонизация `resources/icons` и `ui/theme/icon_provider.py` в `architecture.md` | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-059 | Done |
| D-060 | Unit-тесты icon pipeline (`IconProvider` + menu/toolbar refresh) | [Research TZ](../98-Reviews/research/2026-03/ui/DEV_TZ_ui_icons_2026-03-01.md) §D-060 | Done |

## P2 — UI MainWindow + Chart Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-085 | Исправить documentation drift: ui/charts/ → ui/layout/chart/, TODO-статусы, monitoring_menu/, NFR section | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-085 | Done |
| C-086 | Создать ADR для chart backend selection: pyqtgraph (realtime) + matplotlib (offline export) + IChartBackend interface | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-086 | Done |
| C-087 | Расширить MultiChartManager: linked crosshair sync, optional linked time scroll, configuration API | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-087 | Done |
| C-088 | Реализовать tab context menu: Rename, Close, Close Others, Duplicate, закрытие через context menu/API (без close-крестика) | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-088 | Done |
| C-089 | Реализовать workspace state persistence: ChartWorkspaceState dataclass, save/restore tabs/context/layout/bottom-zone/drawings через UISettings | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-089 | Done |
| C-090 | Реализовать UX visibility presets (Compact/Standard/Full/Analysis): apply_preset API + UISettings persistence | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-090 | Done |
| C-091 | Execution stabilization backlog: emergent defects during execution без нового research, обязательные regression-tests и strict closure-proof без skip (Batch-001: chart overlay overflow, restore remap на double-click Y-axis, indicator sync grid/theme/right-axis; EXE-004 follow-up: indicator context-menu de-dup, chart/UI theme decoupling, workspace indicator persistence, typing hardening + regression tests; EXE-006: dock panels viewport/host unification, compact-shell hardening, shutdown/runtime safety, regression stabilization; EXE-007: dedicated TimeAxisStrip, 3px indicator floor, adjacent splitter resize, tab/separator chrome cleanup; EXE-008: dock lifecycle hardening for maximize/minimize transitions and stale post-restore compact resync; EXE-009 v2: closed follow-up for manager-first dock interaction ownership rebinding, explicit `expanded/clipped/collapsed` compact phase model, native-only title-bar policy, manager-side zone recovery and removal of global style override from dock contract; EXE-010: physical decomposition of dock interaction helpers into dedicated modules, extraction of `_SeparatorDragOverlay` from `MainWindow` and final regression sync to the boundary contract; EXE-011: behavior-preserving migration managed dock runtime на workspace-only splitter substrate с snapshot-only restore/recovery, shell-based phase semantics и удалением obsolete separator drag helpers) | Execution Finding → [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-091 | Done |
| C-103 | Реализовать `WorkspaceAnimationHooks` как optional reactive layer для preview/highlight/collapse transitions без ownership над authoritative state | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-workspace-framework/DEV_TZ_ui-main-window-workspace-framework_2026-03-09.md) §C-103 | Done |
| C-091-EXE-010 | Завершить physical decomposition dock interaction слоя: вынести drag/compact/recovery helpers в dedicated modules, перенести `_SeparatorDragOverlay` из `MainWindow` и синхронизировать финальный regression/closure contract | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-091-EXE-010 | Done |
| C-091-EXE-011 | Завершить behavior-preserving migration managed dock panels на workspace-only splitter runtime: перенести useful UX/runtime contract из native dock-модели в `ManagedPanelShell`/`PanelSplitterWorkspace`, нормализовать snapshot restore/recovery, удалить legacy separator drag substrate и переписать regression tests на workspace truth; native `QToolBar` persistence остаётся вне scope как отдельная подсистема | [Research TZ](../98-Reviews/research/2026-03/ui-main-window-chart/DEV_TZ_ui-main-window-chart_2026-03-02.md) §C-091-EXE-011 | Done |

## P0 — Tests Standards And Test Tree Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-081 | Зафиксировать canonical test taxonomy contract для `tests/` | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-081 | Done |
| D-082 | Зафиксировать controlled decomposition plan для `tests/unit/ui/` и `tests/integration/ui/` | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-082 | Done |
| D-083 | Зафиксировать fixture ownership contract и shared-helper hierarchy | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-083 | Done |
| D-084 | Выпустить disposition matrix для `architecture.md` / `Project_Modules_Documentation.md` / test tree truth-layers | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-084 | Done |
| D-085 | Зафиксировать protected proof inventory и package-surface expansion policy | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-085 | Done |
| D-086 | Зафиксировать canonical performance test substrate contract | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-086 | Done |

## P1 — Tests Standards And Test Tree Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-087 | Реализовать taxonomy alignment: naming / placement / markers | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-087 | Done |
| D-088 | Декомпозировать `tests/unit/ui/` и oversized `tests/integration/ui/` в semantic subpackages | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-088 | Done |
| D-089 | Реализовать fixture cleanup и удалить legacy residues в test tree | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-089 | Done |
| D-090 | Расширить package-surface guards и protected proof coverage по top-level пакетам | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-090 | Done |
| D-091 | Закрыть implementation gap в `tests/performance/` | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-091 | Done |
| D-093 | Стабилизировать protected-core root suites в `tests/unit/` | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-093 | Done |
| D-094 | Стабилизировать subtree `tests/unit/security/` | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-094 | Done |
| D-095 | Нормализовать residual structural pressure в `tests/` после primary stabilization | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-095 | Done |
| D-096 | Довести `tests/` до полного structural closure после residual normalization | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-096 | Done |

## P1 — Test Performance Audit (2026-03-28)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-114 | Снизить drain defaults в drag_drop pilot contour | [Performance Audit TZ](../98-Reviews/audits/2026-03/drag_drop/DEV_TZ_drag_drop_2026-03-28.md) §C-114 | Done |
| C-115 | Ввести module-scoped shared MainWindow для main_local кластера | [Performance Audit TZ](../98-Reviews/audits/2026-03/drag_drop/DEV_TZ_drag_drop_2026-03-28.md) §C-115 | In Progress |
| C-116 | Реализовать validation seed gating для CI-режима | [Performance Audit TZ](../98-Reviews/audits/2026-03/drag_drop/DEV_TZ_drag_drop_2026-03-28.md) §C-116 | Done |

## P2 — Tests Standards And Test Tree Audit

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-092 | Синхронизировать docs truth-layers, artifact README и backlog-ready import block после remediation | [Research TZ](../98-Reviews/research/2026-03/tests-standards-and-test-tree-audit/DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md) §D-092 | Done |

## P3 — Долгосрочное

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| L-001 | Sphinx: настроить source/conf.py или удалить make.bat/Makefile | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §8 | Done |
| L-002 | Перевести autogen-документы из draft в active после ручной проверки | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §8 | Done |
| L-003 | Обновить устаревшие метрики в 98-Analysis/ (149 тестов→162, покрытие) | [Docs Audit](audits/AUDIT_DOCS_DEEP_ANALYSIS_2026-02-19.md) §8 | Done |
| L-004 | Неверный docstring в `SecurityManager.process_security_event()` — скопирован от shutdown() | [Code Audit](audits/AUDIT_COPILOT_DEEP_ANALYSIS_2026-02-19.md) §4.1 | Done |
| L-005 | Унифицировать owner для draft-стандартов: `Documentation Team` → профильные команды | [Standards Review](standards_review_2025-01.md) §2.5 | Done |
| L-006 | Удалить дублирование metadata-секций из тел стандартов (front-matter vs body) | [Standards Review](standards_review_2025-01.md) §2.7 | Done |
| L-007 | f-strings в log-вызовах (resources_manager, main_logic, task_manager и др.) — строка форматируется всегда, даже если уровень выключен → %-подстановка | [Deep Audit 2026-02-19] | Done |
| L-008 | CamelCase в именах тестовых файлов: `test_system_Initializer.py`, `test_systemInitializer_integration.py` → snake_case | [Deep Audit 2026-02-19] | Done |
| L-009 | `.vscode/README.md`: устаревший путь `C:\Project\AIFE` → `E:\AIFE_Ecosystem\AIFE` | [README Audit 2026-02-19] | Done |
| L-010 | CHANGELOG записи чрезмерно детализированы (100+ строк каждая) — формат версий не SemVer при декларированном SemVer | [Deep Audit 2026-02-19] | Done |
| L-011 | `docs/01-Overview/README.md`: заголовок `00-Overview` вместо `01-Overview` | [README Audit 2026-02-19] | Done |
| L-012 | `pyproject.toml`: нет секции `[build-system]`/`[project]` — невозможен `pip install -e .` | [Deep Audit 2026-02-19] | Done |
| L-013 | `isort known_third_party` содержит только `["requests", "flask"]` — не включает PySide6, qasync, numpy | [Deep Audit 2026-02-19] | Done |
| L-014 | `tests/e2e/` — пустая директория (только `__init__.py`), удалить или заполнить | [Deep Audit 2026-02-19] | Done |

## P3 — Prompt Library Research

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-067 | Опционально убрать tolerable duplication prompt-map между `session-start` и `README` | [Research TZ](../98-Reviews/research/2026-03/prompt-library/DEV_TZ_prompt-library-unification_2026-03-17.md) §D-067 | Done |

---

## P1 — SEC I-900 Decomposition (MANUAL)

> ⚠️ __ОТМЕНЕНО (2026-02-24):__ Все батчи I-960..I-968 отменены. Чекбоксы STD-SEC-REVIEW-001 являются
> переиспользуемым review-шаблоном (тип D), их нельзя «закрывать» в файле стандарта.
> Runtime-код `security/` и тесты сохранены как самостоятельная реализация.
> См. policy v1.3.0 в STD-GOVERNANCE-IMPROVEMENT-001.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-960 | [STD-SEC-REVIEW-001] Batch B1: закрыть IDX-001..IDX-013 (13 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B1) | Cancelled |
| I-961 | [STD-SEC-REVIEW-001] Batch B2: закрыть IDX-014..IDX-026 (13 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B2) | Cancelled |
| I-962 | [STD-SEC-REVIEW-001] Batch B3: закрыть IDX-027..IDX-039 (13 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B3) | Cancelled |
| I-963 | [STD-SEC-REVIEW-001] Batch B4: закрыть IDX-040..IDX-052 (13 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B4) | Cancelled |
| I-964 | [STD-SEC-REVIEW-001] Batch B5: закрыть IDX-053..IDX-065 (13 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B5) | Cancelled |
| I-965 | [STD-SEC-REVIEW-001] Batch B6: закрыть IDX-066..IDX-077 (12 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B6) | Cancelled |
| I-966 | [STD-SEC-REVIEW-001] Batch B7: закрыть IDX-078..IDX-089 (12 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B7) | Cancelled |
| I-967 | [STD-SEC-REVIEW-001] Batch B8: закрыть IDX-090..IDX-101 (12 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B8) | Cancelled |
| I-968 | [STD-SEC-REVIEW-001] Batch B9: закрыть IDX-102..IDX-113 (12 чекбоксов) (reverted: чекбоксы типа D — review template, нельзя закрывать) | [SEC Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_sec_review_I-900_batches_2026-02-23.md) §Batch plan (B9) | Cancelled |

## P1 — Ownership Model Unification (2026-03-23)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-097 | Удалить `SystemInitializerBuilder` file + exports | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-097 | Done |
| D-098 | Удалить `ErrorHandlingMixin` dead class | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-098 | Done |
| D-099 | Удалить native reset residue (proof-gated) | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-099 | Done |
| D-107 | Создать 5 обязательных диаграмм → canonical architecture docs | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-107 | Done |
| D-108 | Full documentation canonicalization (builder + runtime authority + workspace ownership + restore boundaries) | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-108 | Done |
| D-109 | Final canonicalization verification package | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-109 | Done |

## P2 — Ownership Model Unification (2026-03-23)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-100 | Удалить legacy LogManager startup path | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-100 | Done |
| D-101 | Заменить `MainLogic.run()` resurrection → `RuntimeError` | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-101 | Done |
| D-102 | CommunicationManager AppContext cleanup в shutdown | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-102 | Done |
| D-104 | Align `authority` → `capture_source` vocabulary | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-104 | Done |
| D-110 | ADR / registry sync: parent cross-links, addendum visibility | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-110 | Done |

## P3 — Ownership Model Unification (2026-03-23)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-105 | Добавить lifecycle ownership rule в `STD-ARCH-PATTERNS-001` (proposed) | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-105 | Done |
| D-106 | Добавить dual-registration cleanup contract в `STD-ARCH-PATTERNS-001` (proposed) | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-106 | Done |

## P4 — Ownership Model Unification (2026-03-23)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-103 | Optional: удалить DM conditional `EventRouter` shutdown | [Research TZ](../98-Reviews/research/2026-03/ownership-model/DEV_TZ_ownership-model-unification_2026-03-23.md) §D-103 | Done |

## P2 — ARCH Patterns Ownership Remediation (2026-03-29)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-137 | Извлечь educational примеры из STD-ARCH-PATTERNS-001 в `examples/arch/` | [Audit](../98-Reviews/audits/2026-03/arch-patterns-ownership-remediation/AUDIT_arch-patterns-ownership-remediation_general_2026-03-29_copilot-claude.md) §FIND-002, §FIND-003 | Done |
| D-138 | Targeted review и approval STD-ARCH-PATTERNS-001 (proposed → approved v1.0.0) | [DEV_TZ](../98-Reviews/audits/2026-03/arch-patterns-ownership-remediation/DEV_TZ_arch-patterns-ownership-remediation_2026-03-29.md) §D-138 | Done |
| D-139 | Синхронизировать STANDARDS_REGISTRY после approval STD-ARCH-PATTERNS-001 | [DEV_TZ](../98-Reviews/audits/2026-03/arch-patterns-ownership-remediation/DEV_TZ_arch-patterns-ownership-remediation_2026-03-29.md) §D-139 | Done |

## P1 — Governance Routing Accessibility (2026-03-29)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-140 | Опубликовать authority model и decision tree в AGENTS.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-001 | Done |
| D-141 | Добавить ownership routing и «Правило для архитектурных решений» в AGENTS.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-002 | Done |
| D-142 | Пометить phantom CONTRACT-ARCH-MODULE-OWNERSHIP-001 как illustrative-only | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-003 | Done |
| D-143 | Добавить третью ветку (STD) в routing rule copilot-instructions.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-005 | Done |

## P2 — Governance Routing Refinement (2026-03-29)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-144 | Добавить sibling-link на STD-ARCH-PATTERNS-001 в architecture.md truth-layer | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-004 | Done |
| D-145 | Добавить ownership label в entry-point таблицы стандартов | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-006 | Done |
| D-146 | Добавить ссылку на canonical-context.md или inline baseline в AGENTS.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-007 | Done |
| D-147 | Добавить scope guard note в CONTRACTS_REGISTRY для ARCH domain | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-009 | Done |
| D-148 | Добавить governance routing cross-ref в AGENTS_PATCH_GUIDE.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-011 | Done |
| D-149 | Нормализовать routing definitions между entry points | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-014 | Done |
| D-150 | Усилить routing к CONTRACTS_REGISTRY в docs/99-ADR/README.md | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-016 | Done |
| D-151 | Добавить enforcement checklist в STD-ARCH-PATTERNS-001 | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-010 | Done |
| D-152 | Добавить explicit Scope & Authority declaration в STD-ARCH-PATTERNS-001 | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-012 | Done |
| D-153 | Добавить reverse-routing links в STD-ARCH-PATTERNS-001 | [AUDIT CONSOLIDATED](../98-Reviews/audits/2026-03/governance-routing-accessibility/AUDIT_CONSOLIDATED_governance-routing-accessibility_2026-03-29.md) §CF-013 | Done |

## P1 — Architectural Drift Validator Calibration (2026-03-30)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-969 | Drift model types + entity classifier + import graph | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-969 | Done |
| I-970 | Pattern engine + signal types + evaluator | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-970 | Done |
| I-971 | CLI entry point + advisory mode integration | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-971 | Done |
| I-972 | Shared signal taxonomy module | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-972 | Done |
| I-973 | Advisory/blocking rule family config | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-973 | Done |
| I-974 | Entity extraction + calibration run на ui/layout/ | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-974 | Done |
| I-975 | Ground truth comparison + precision/recall metrics | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-975 | Done |
| I-976 | Synthetic fixture corpus (DPT-001, DPT-004) | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-976 | Done |
| I-977 | Exception mechanism (drift_exceptions.yml) | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-977 | Done |
| I-978 | Blocking promotion gate для calibrated patterns | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-978 | Done |
| I-979 | Validator README + unified signal taxonomy docs | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-979 | Done |
| I-980 | Governance trigger assessment | [DEV_TZ](../98-Reviews/audits/2026-03/architectural-drift-validator-calibration/DEV_TZ_architectural-drift-validator-calibration_2026-03-30.md) §I-980 | Done |

## P1 — Phase 5B UI Package End-to-End Runtime Remediation (2026-03-31)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-117 | Устранить carrier-seam drift WorkspaceFacade → DockPanelsManager (CF-001+CF-002) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-117 | Done |
| I-981 | Validator rerun contract Wave 1 (runtime-only scope) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §I-981 | Done |
| C-126 | Реализовать unified unavailable-action routing mechanism через EventBus/EventRouter (CF-004+CF-005) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-126 | Done |
| C-118 | File→Save — подключить к persistence consumer или canonical unavailable route (CF-004) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-118 | Done |
| C-119 | Перевести 37 menu stub actions на unified connection model (CF-005) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-119 | Done |
| C-120 | Декомпозиция 6 файлов >1000 строк в dock_panels (CF-006) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-120 | Done |

## P2 — Phase 5B UI Package End-to-End Runtime Remediation (2026-03-31)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-121 | Waiver или декомпозиция 5+ файлов 700–1000 строк (CF-007) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-121 | Done |
| C-127 | Снять residual warning-zone pressure в `chart_widget.py` после adjacent remeasure C-121 (CF-007) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-127 | Done |
| C-122 | Public method count DockPanelsManager — контроль порога (CF-013) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-122 | Done |
| C-128 | Снизить effective public surface DockPanelsManager ниже hard ceiling после inventory C-122 (CF-013) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-128 | Done |
| C-123 | Переподтвердить или удалить WORKAROUND C-108 (CF-008) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-123 | Done |
| C-124 | Материализовать stale-access warning / freshness guard поверх generation tracking в DockPanelsAdapter (CF-009) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-124 | Done |
| C-125 | Injection seam для DockPanelsAdapter (CF-010) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-125 | Done |
| C-129 | Устранить residual private fallback seam WorkspaceFacade → DockPanelsManager после closure Phase 5B | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §C-129 | Done |
| I-982 | Unit-тесты для validate_lint_suppressions.py (CF-011) | [DEV_TZ](../98-Reviews/audits/2026-03/phase-5b-ui-runtime-remediation/DEV_TZ_phase-5b-ui-runtime-remediation_2026-03-31.md) §I-982 | Done |

## P0 — Phase 5C Test Contour Remediation (2026-04-01)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-130 | Tiered drain policy + inter-module GC (CF-001, CF-003) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-130 | Done |
| C-131 | Validation/report fixture settle optimization (CF-002) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-131 | Done |
| C-133 | D-129 → D-126 composition refactoring (CF-005) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-133 | Done |

## P1 — Phase 5C Test Contour Remediation (2026-04-01)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-132 | Module-scoped MainWindow reuse expansion (CF-004) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-132 | Done |
| C-134 | Ordinary family delegation + redundant test removal (CF-006, CF-007) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-134 | Done |
| C-135 | Surface/stability merge + perimeter parametrize (CF-008, CF-009) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-135 | Done |
| C-136 | Public properties for top _internal_attr usages (CF-010) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-136 | Done |
| D-154 | Validate prompt/routing sync correctness (CF-011..CF-014, CF-017, CF-019) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §D-154 | Done |
| D-155 | Final DoD measurement and Phase 5C closure (§20) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §D-155 | Done |

## P2 — Phase 5C Test Contour Remediation (2026-04-01)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-137 | Consolidate reset/metadata assertions + case-id constants (CF-016) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-137 | Done |
| C-138 | Decompose _common_runtime_helpers by semantic families (CF-015) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-138 | Done |
| C-139 | Reduce waypoint grid in churn stability tests (CF-018) | [DEV_TZ](../98-Reviews/audits/2026-04/phase-5c-test-contour/DEV_TZ_phase-5c-test-contour_2026-04-01.md) §C-139 | Done |

## P0 — Hook Ecosystem Core Foundation (2026-04-02)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-156 | Создать `STD-GOVERNANCE-HOOKS-001` и канонизировать `4+1` contour model | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §D-156 | Done |
| I-983 | Материализовать `HOOK_REGISTRY` и начальный inventory живых hook IDs | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-983 | Done |
| I-984 | Согласовать `.pre-commit-config.yaml` с contour contract и вынести heavy hooks из primary commit contour | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-984 | Done |
| I-985 | Сделать authority traceability обязательной для каждого live hook | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-985 | Done |

## P1 — Hook Ecosystem Contracts and Closure (2026-04-02)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-986 | Ввести default-inclusive coverage map и authorized exclusions governance | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-986 | Done |
| I-987 | Зафиксировать output / observability contract для hook diagnostics и durable evidence | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-987 | Done |
| I-988 | Материализовать repeat-failure routing и advisory hook health report | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-988 | Done |
| D-157 | Синхронизировать docs / prompts / instructions с новым hook-core contract | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §D-157 | Done |
| D-158 | Зафиксировать runtime overlay compatibility contract и external borrowing policy | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §D-158 | Done |
| D-159 | Выполнить финальную проверку, closure verdict и archive readiness для hook core | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §D-159 | Done |

## P2 — Hook Ecosystem Reuse and Dev-Loop Overlay (2026-04-02)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-989 | Извлечь только узкие helper seams по низкоуровневым семьям и не создавать umbrella dispatcher | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-989 | Done |
| I-990 | Материализовать быстрый `quality-gate` как AIFE-owned `dev-loop` helper | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-02.md) §I-990 | Done |

## P2 — Hook Ecosystem Post-Closure Maintainability (2026-04-06)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-160 | Выполнить post-closure maintainability hardening hook ecosystem без reopening hook-core authority | [DEV_TZ](../98-Reviews/audits/2026-04/hook-ecosystem/DEV_TZ_hook-ecosystem_2026-04-06.md) §D-160 | Done |

## P0 — Phase 5D Validator Calibration (2026-04-03)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-991 | Scope isolation: post-evaluation seed filtering для validate_architectural_drift | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-991 | Done |

## P1 — Phase 5D Validator Calibration (2026-04-03)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-992 | DPT-004: same-package companion import filter (blocking FP fix) | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-992 | Done |
| I-993 | DPT-001: single-caller getattr detection (FN-1 fix) | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-993 | Done |

## P2 — Phase 5D Validator Calibration (2026-04-03)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-994 | Фильтрация _-prefixed классов из visible-surface role | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-994 | Done |
| I-995 | Class method count threshold >25 (DPT-009, anti-monolith signal) | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-995 | Done |
| I-996 | DPT-002: дифференциация shell vs active runtime widget | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-996 | Done |
| I-997 | DPT-007: дедупликация derivative-сигналов (DPT-004+DPT-007 overlap) | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-997 | Done |
| I-998 | DPT-006: подавление advisory для __init__.py re-export | [DEV_TZ](../98-Reviews/audits/2026-04/validator-truth-calibration/DEV_TZ_validator-truth-calibration_2026-04-03.md) §I-998 | Done |

## P1 — Architectural Drift Framework Finalization (2026-04-04)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-999 | Decision substrate: materialize signal → action contract | [DEV_TZ](../98-Reviews/research/2026-04/architectural-drift-validator-framework-finalization/DEV_TZ_architectural-drift-validator-framework-finalization_2026-04-04.md) §I-999 | Done |
| I-1000 | Blind spot closure: закрыть BSR-001 / BSR-002 / BSR-006 / BSR-007 / BSR-008 | [DEV_TZ](../98-Reviews/research/2026-04/architectural-drift-validator-framework-finalization/DEV_TZ_architectural-drift-validator-framework-finalization_2026-04-04.md) §I-1000 | Done |
| I-1001 | Adapter boundary: materialize explicit project-specific seam | [DEV_TZ](../98-Reviews/research/2026-04/architectural-drift-validator-framework-finalization/DEV_TZ_architectural-drift-validator-framework-finalization_2026-04-04.md) §I-1001 | Done |
| I-1002 | Cross-package calibration: recalibrate DPT-002 / DPT-003 / DPT-006 outside UI | [DEV_TZ](../98-Reviews/research/2026-04/architectural-drift-validator-framework-finalization/DEV_TZ_architectural-drift-validator-framework-finalization_2026-04-04.md) §I-1002 | Done |
| I-1003 | Operating model: materialize modes / hooks / evidence / triage contract | [DEV_TZ](../98-Reviews/research/2026-04/architectural-drift-validator-framework-finalization/DEV_TZ_architectural-drift-validator-framework-finalization_2026-04-04.md) §I-1003 | Done |

## P0 — Genome-Driven Knowledge Navigation Foundation (2026-04-08)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-161 | Канонизировать `STD-GOVERNANCE-GENOME-001` как `OU-1` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-1-governance-core-and-bounded-vocabulary-base_2026-04-08.md) §D-161 | Done |
| D-162 | Синхронизировать `STANDARDS_REGISTRY.md` с `OU-1` и ограниченным `CU-1` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-1-governance-core-and-bounded-vocabulary-base_2026-04-08.md) §D-162 | Done |
| D-164 | Канонизировать `genome/adr/**` как живой маршрут владельца для семейства ADR | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-2-adr-migration-and-redirect-continuity_2026-04-08.md) §D-164 | Done |
| D-165 | Выполнить downstream migration ADR family к уже закреплённой общей grammar без переоткрытия naming rule | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-2-adr-migration-and-redirect-continuity_2026-04-08.md) §D-165 | Done |
| D-166 | Закрыть текущий переход addenda без постоянной ветки `ADDENDUM` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-2-adr-migration-and-redirect-continuity_2026-04-08.md) §D-166 | Done |
| D-169 | Канонизировать question-class и first-open discipline в `AGENTS.md` как живой owner route `OU-5` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-3-routing-owner-refresh-and-companion-route-layer_2026-04-08.md) §D-169 | Done |
| D-170 | Синхронизировать `AGENTS_PATCH_GUIDE.md` и `AGENTS_ARTIFACTS.md` с owner route `TZ-3` и каноническим ADR маршрутом `TZ-2` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-3-routing-owner-refresh-and-companion-route-layer_2026-04-08.md) §D-170 | Done |
| D-171 | Материализовать shared companion route layer в `.github/prompts/README.md` и `includes/canonical-context.md` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-3-routing-owner-refresh-and-companion-route-layer_2026-04-08.md) §D-171 | Done |
| D-174 | Канонизировать межсемейный relation vocabulary и границу owner/mirror в `STD-DOC-METADATA-001` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-4-cross-family-lineage-and-relation-vocabulary_2026-04-08.md) §D-174 | Done |
| D-175 | Материализовать schema и validator support для canonical relation model | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-4-cross-family-lineage-and-relation-vocabulary_2026-04-08.md) §D-175 | Done |
| D-176 | Материализовать bounded cross-family seed corpus для relation model | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-4-cross-family-lineage-and-relation-vocabulary_2026-04-08.md) §D-176 | Done |
| D-179 | Зафиксировать ограниченный вводный контракт `semantic_id` / `node-key` и границы `code/diagram/BSP` для `TZ-5` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md) §D-179 | Done |
| D-180 | Материализовать ограниченную производную графовую поверхность чтения без дрейфа владения | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md) §D-180 | Done |
| D-184 | Канонизировать `OU-6` как контракт владельца для принудительных требований и синхронизационных барьеров финального контура knowledge-navigation | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md) §D-184 | Done |
| D-186 | Материализовать `CU-5` как переиспользуемый сопроводительный контур проверки с маршрутом захвата доказательства | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md) §D-186 | Done |

## P1 — Genome-Driven Knowledge Navigation Foundation (2026-04-08)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-163 | Выполнить финальную проверку `TZ-1` и подтвердить границы несхлопывания | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-1-governance-core-and-bounded-vocabulary-base_2026-04-08.md) §D-163 | Done |
| D-167 | Материализовать ограниченное перенаправление и трассируемость для миграции ADR | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-2-adr-migration-and-redirect-continuity_2026-04-08.md) §D-167 | Done |
| D-168 | Выполнить финальную проверку `TZ-2` и подтвердить непрерывность ADR без утечки границ | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-2-adr-migration-and-redirect-continuity_2026-04-08.md) §D-168 | Done |
| D-172 | Нормализовать routing-carrying prompt surfaces без теневых полномочий | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-3-routing-owner-refresh-and-companion-route-layer_2026-04-08.md) §D-172 | Done |
| D-173 | Выполнить финальную проверку `TZ-3` и подтвердить first-open discipline без shadow authority | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-3-routing-owner-refresh-and-companion-route-layer_2026-04-08.md) §D-173 | Done |
| D-177 | Синхронизировать registries и selected entry surfaces как mirror-only consumers relation model | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-4-cross-family-lineage-and-relation-vocabulary_2026-04-08.md) §D-177 | Done |
| D-178 | Выполнить финальную проверку `TZ-4` и подтвердить boundary law `lineage-before-graph-consumers` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-4-cross-family-lineage-and-relation-vocabulary_2026-04-08.md) §D-178 | Done |
| D-181 | Материализовать `CU-3` как отдельный сопроводительный слой диаграмм с дисциплиной визуальных якорей | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md) §D-181 | Done |
| D-182 | Материализовать `CU-4` как безопасный по происхождению сопроводительный слой terminal-help | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md) §D-182 | Done |
| D-183 | Выполнить финальную проверку `TZ-5` и подтвердить готовый для `TZ-6` строго производный контур | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md) §D-183 | Done |
| D-185 | Материализовать `CU-7` как ограниченный операторский сопроводительный слой для валидаторов, `CI` и синхронизационных барьеров без теневых полномочий | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md) §D-185 | Done |
| D-187 | Синхронизировать корневой управляющий контур и дисциплину закрытия пакета `D` без седьмого `DEV_TZ` | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md) §D-187 | Done |
| D-188 | Выполнить финальную проверку `TZ-6` и подтвердить носитель закрытия для всей шестиконтурной последовательности | [Research TZ](../98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/wave-7-drift-reconciliation-and-final-closure/DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md) §D-188 | Done |

## P1 — Post-Closure Enforcement And Runtime Resolution (2026-04-11)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-189 | Очистить active routing surfaces от ссылок на deleted `GEN/CHR` surfaces | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-189 | Done |
| D-190 | Синхронизировать `genome_registry.json` с фактическим perimeter `genome/registries/` | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-190 | Done |
| D-191 | Перевести `registry_generator.py` на live JSON-контракт без deleted registries | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-191 | Done |
| D-195 | Выполнить финальную проверку и подтвердить closure без alternative owner-route | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-195 | Done |

## P0 — Публикация у владельца для второй волны программы `post-closure-enforcement-and-runtime-resolution` (2026-04-13)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-201 | Оформить повторяемый закон маршрутизации и публикации для второй волны как `STD` у владельца и синхронизировать реестр, индекс и трассируемость | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-std-routing-law-materialization_2026-04-13.md) §D-201 | Done |
| D-202 | Исправить route-sensitive ссылки change-слоя и вернуть их к canonical ADR route | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-change-routing-publication-fix_2026-04-13.md) §D-202 | Done |
| D-203 | Опубликовать owner-side решение по substrate seams, classes и boundaries без выбора concrete technology | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-substrate-owner-decision-publication_2026-04-13.md) §D-203 | Done |

## P1 — Execution package для второй волны программы `post-closure-enforcement-and-runtime-resolution` (2026-04-13)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-204 | Опубликовать owner-readable contracts для freshness, benchmark и promotion без repo-wide recalibration | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-freshness-benchmark-and-promotion-contracts_2026-04-13.md) §D-204 | Done |
| D-205 | Синхронизировать control-plane и route-sensitive consumer surfaces после materialization package Волны 2 | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-control-plane-and-consumer-sync_2026-04-13.md) §D-205 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology (2026-04-20)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-221 | Снять блокеры `BR-1` и `BR-2` через единое обновление корневого управляющего слоя и правила допуска | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_readiness-blocker-removal_2026-04-20.md) §D-221 | Done |
| D-222 | Материализовать bounded owner-readable lookup / route-back carrier для active consumer surfaces без shadow authority | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_lookup-publication-authority_2026-04-20.md) §D-222 | Done |
| D-223 | Синхронизировать publication / discoverability consumers и route-to-owner consistency для DOC execution-layer | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_lookup-publication-authority_2026-04-20.md) §D-223 | Done |
| D-224 | Закрыть `TZ-1` через bounded control-plane sync, backlog import и proof без открытия `TZ-2..TZ-4` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_lookup-publication-authority_2026-04-20.md) §D-224 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-2 Status Provenance Materialization (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-225 | Материализовать provenance-first и reference-only границу для glossary / abbreviation carriers | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_status-provenance-materialization_2026-04-21.md) §D-225 | Done |
| D-226 | Синхронизировать root/section index seeds под bounded status/provenance и route-back law | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_status-provenance-materialization_2026-04-21.md) §D-226 | Done |
| D-227 | Закрыть `TZ-2` через bounded control-plane sync и передать следующий шаг только в `TZ-3` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_status-provenance-materialization_2026-04-21.md) §D-227 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-3 Legacy Sphinx Residue Application (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-228 | Применить классификацию по подсемействам к живому `Sphinx`-пакету и дубликатам инструкций | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_legacy-sphinx-residue-application_2026-04-21.md) §D-228 | Done |
| D-229 | Убрать фантомный маршрут `docs/source` и синхронизировать ближайшие навигационные и управляющие носители | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_legacy-sphinx-residue-application_2026-04-21.md) §D-229 | Done |
| D-230 | Закрыть `TZ-3` через синхронизацию управляющего слоя, backlog и доказательств и передать следующий шаг только в `TZ-4` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_legacy-sphinx-residue-application_2026-04-21.md) §D-230 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-4 Freshness Validator Enforcement (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-1007 | Оформить отдельный скрипт для узкой проверки свежести и явных ссылок возврата в `scripts/metadata/` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_freshness-validator-enforcement_2026-04-21.md) §I-1007 | Done |
| I-1008 | Добавить узкий hook-runtime и сопроводительный след для `validate-doc-freshness` без расширения блокирующей области | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_freshness-validator-enforcement_2026-04-21.md) §I-1008 | Done |
| D-231 | Закрыть `TZ-4` через синхронизацию управляющих документов, backlog и `CHANGELOG.md` и зафиксировать исчерпание точного порядка | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_freshness-validator-enforcement_2026-04-21.md) §D-231 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-5 Standards Publication Packet (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-232 | Перевести 7 обязательных STD (SUBSTRATE, PLACEMENT, LEGACY, TERMINOLOGY, DIAGRAMS, HELP, FRESHNESS) из `draft` в `approved` и синхронизировать STANDARDS_REGISTRY | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_standards-publication-packet_2026-04-21.md) §D-232 | Done |
| D-233 | Создать тонкий pointer-layer носитель `lookup / publication / status` с обязательными полями для owner-backed surfaces | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_standards-publication-packet_2026-04-21.md) §D-233 | Done |
| D-234 | Синхронизировать root control-plane (README области, PROGRAM_MAP, INVESTIGATION_QUEUE, LOGICAL_DRIFT_REGISTER) с фактом publication milestone | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_standards-publication-packet_2026-04-21.md) §D-234 | Done |
| D-235 | Закрыть TZ-5 через bounded proof, синхронизировать backlog и CHANGELOG, передать следующий шаг только в TZ-6 | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_standards-publication-packet_2026-04-21.md) §D-235 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-6 ADR Substrate Materialization (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-236 | Создать `ADR-DOC-SUBSTRATE-001` в `genome/adr/doc/` и зарегистрировать в `ADR_REGISTRY.md` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_adr-substrate-materialization_2026-04-21.md) §D-236 | Done |
| D-237 | Проверить нужность `ADR-DOC-HELP-001` и `ADR-DOC-DELIVERY-001` после публикации STD; зафиксировать вывод явно | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_adr-substrate-materialization_2026-04-21.md) §D-237 | Done |
| D-238 | Закрыть TZ-6 через регистрацию ADR в ADR_REGISTRY и proof; синхронизировать backlog и CHANGELOG | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_adr-substrate-materialization_2026-04-21.md) §D-238 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-7 Diagram Law Application (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-239 | Выполнить аудит диаграмм в `docs/` по критериям STD-DOC-DIAGRAMS-001; составить список несоответствий | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_diagram-law-application_2026-04-21.md) §D-239 | Done |
| D-240 | Устранить найденные несоответствия visual grammar и source/export law по списку из D-239 | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_diagram-law-application_2026-04-21.md) §D-240 | Done |
| D-241 | Закрыть TZ-7: обновить LOGICAL_DRIFT_REGISTER, синхронизировать backlog и CHANGELOG | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_diagram-law-application_2026-04-21.md) §D-241 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / TZ-8 Metadata Alias Governance Application (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-242 | Синхронизировать `.aife/owners.yml` и metadata schema с опубликованным STD-DOC-METADATA-001; применить controlled expansion law | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_metadata-alias-governance-application_2026-04-21.md) §D-242 | Done |
| D-243 | Устранить alias drift в `.aife/owners.yml` согласно STD-DOC-TERMINOLOGY-001; зафиксировать retained alias с обоснованием | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_metadata-alias-governance-application_2026-04-21.md) §D-243 | Done |
| D-244 | Закрыть TZ-8: обновить LOGICAL_DRIFT_REGISTER, синхронизировать backlog и CHANGELOG | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_metadata-alias-governance-application_2026-04-21.md) §D-244 | Done |

## P1 — Documentation Substrate Help / Diagrams / Terminology / Terminal Closure and Archive Sync (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-245 | Перевести все закрытые DEV_TZ (TZ-2..TZ-8) и все root PRR-носители в архивную семантику без массовой архивации research corpus | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_terminal-closure-and-archive-sync_2026-04-21.md) §D-245 | Done |
| D-246 | Оформить `TASK_RANGE_CLOSURE_*` по диапазону D-221..D-247, синхронизировать backlog и `CHANGELOG.md`, закрыть текущий terminal `DEV_TZ` | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_terminal-closure-and-archive-sync_2026-04-21.md) §D-246 | Done |
| D-247 | Перевести корневой control-plane и monthly index в `archived / completed` semantics без публикации нового contour | [Research TZ](../98-Reviews/research/2026-04/documentation-substrate-help-diagrams-terminology/DEV_TZ_documentation-substrate-help-diagrams-terminology_terminal-closure-and-archive-sync_2026-04-21.md) §D-247 | Done |

## P1 — Встроенная справка приложения из меню (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| C-140 | Оформить производный пакет встроенной справки поверх указательного DOC-слоя | [Research TZ](../98-Reviews/research/2026-04/runtime-in-app-help-architecture/DEV_TZ_runtime-in-app-help-architecture_2026-04-21.md) §C-140 | Done |
| C-141 | Реализовать `BaseAIFEDialog`-носитель встроенной справки и открыть его из меню `Справка` | [Research TZ](../98-Reviews/research/2026-04/runtime-in-app-help-architecture/DEV_TZ_runtime-in-app-help-architecture_2026-04-21.md) §C-141 | Done |
| C-142 | Добавить честный `route-back`, режим честной недоступности и передачу для `API Reference` | [Research TZ](../98-Reviews/research/2026-04/runtime-in-app-help-architecture/DEV_TZ_runtime-in-app-help-architecture_2026-04-21.md) §C-142 | Done |
| C-143 | Добавить unit/smoke-доказательство для встроенной справки и обновить ожидания help-menu | [Research TZ](../98-Reviews/research/2026-04/runtime-in-app-help-architecture/DEV_TZ_runtime-in-app-help-architecture_2026-04-21.md) §C-143 | Done |
| C-144 | `F5_NEW_INCOMING_PHYSICAL_LIFECYCLE_QUALIFICATION`; `IMPLEMENTATION_STARTED=NO`; `OWNER_EXECUTION_AUTHORITY_GRANTED=NO` | [Execution DEV_TZ](../98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_f5_2026-08-29.md) §C-144; [Owner Review](../98-Reviews/execution/2026-08/aife-server-data-foundation/PRR_aife-server-data-foundation_f5_2026-08-29.md) §Owner verdict | Backlog |
| D-248 | Финализировать контур встроенной справки: синхронизировать `DEV_TZ`, список задач и доказательства закрытия | [Research TZ](../98-Reviews/research/2026-04/runtime-in-app-help-architecture/DEV_TZ_runtime-in-app-help-architecture_2026-04-21.md) §D-248 | Done |

## P1 — Порог обязательности семейств и раскатка диаграммных исходников (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-259 | Материализовать три новых обязательных family-local Markdown-контура `event-flow`, `workspace-topology`, `gesture-session` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-1-diagram-family-rollout-threshold-application_2026-04-22.md) §D-259 | Done |
| D-260 | Расширить обязательные живые якоря `workspace-ownership-hierarchy.md` и `restore-scheme.md` до текущего runtime scope | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-1-diagram-family-rollout-threshold-application_2026-04-22.md) §D-260 | Done |
| D-261 | Повторно зафиксировать матрицу обязательности для живых runtime-якорей и lookup-якоря `file-role-lookup`, синхронизировать diagram-index после rollout `TZ-1` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-1-diagram-family-rollout-threshold-application_2026-04-22.md) §D-261 | Done |
| D-262 | Финализировать пакет `TZ-1`, синхронизировать task-ID / backlog и оформить честный downstream unlock только к `TZ-2` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-1-diagram-family-rollout-threshold-application_2026-04-22.md) §D-262 | Done |

## P1 — Генератор, SVG и пакеты происхождения диаграмм (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-263 | Нормализовать шестисемейный Markdown source corpus под exact `Wave 3` contract после closure `TZ-1` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md) §D-263 | Done |
| D-264 | Принять и materialize-ить bounded generator substrate decision для multi-family export contour | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md) §D-264 | Done |
| D-265 | Materialize-ить sibling `SVG` и family manifests для новых family carriers из `TZ-1` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md) §D-265 | Done |
| D-266 | Синхронизировать root/family index layer и повторно зафиксировать ontology `Markdown -> SVG + manifest` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md) §D-266 | Done |
| D-267 | Финализировать `TZ-2`, синхронизировать backlog и оформить downstream boundary только к `TZ-3` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md) §D-267 | Done |

## P1 — Корневой JSON-пакет диаграмм и обратная ссылка на слой владельца (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-268 | Зафиксировать и материализовать канонический корневой пакет `diagram JSON` в `docs/10-Architecture/diagrams/` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-3-diagram-json-owner-integration_2026-04-22.md) §D-268 | Done |
| D-269 | Материализовать `family_registry` для шести семейств и semantic-first `nodes` / `edges` для post-`TZ-2` corpus | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-3-diagram-json-owner-integration_2026-04-22.md) §D-269 | Done |
| D-270 | Встроить reference-first `provenance` и структурированный `owner_bridge` без захвата owner truth | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-3-diagram-json-owner-integration_2026-04-22.md) §D-270 | Done |
| D-271 | Синхронизировать корневой индекс диаграмм и явно развести `diagram JSON`, `SVG` и family manifests | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-3-diagram-json-owner-integration_2026-04-22.md) §D-271 | Done |
| D-272 | Финализировать `TZ-3`, синхронизировать backlog и оформить разрешение перехода только к `TZ-4` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-3-diagram-json-owner-integration_2026-04-22.md) §D-272 | Done |

## P1 — Свежесть, валидатор и ограниченная раскатка диаграмм (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-273 | Зафиксировать матрицу сигналов и три инварианта детерминизма для `V1`-проверки диаграмм | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md) §D-273 | Done |
| D-274 | Расширить `V1`-проверку `Markdown -> SVG + manifest` на все шесть семейств | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md) §D-274 | Done |
| D-275 | Материализовать `V2`-проверку свежести `diagram JSON` по ссылкам на source, manifest и owner | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md) §D-275 | Done |
| D-276 | Оформить ограниченный режим запуска `local-strict` / `advisory` без перехода к blocking-раскатке | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md) §D-276 | Done |
| D-277 | Финализировать `TZ-4`, синхронизировать backlog и передать следующий шаг только в `TZ-5` | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md) §D-277 | Done |

## P1 — Публикация у владельца и интеграция в prompt/workflow для диаграмм (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-278 | Переоценить owner-level вопросы по closure note `TZ-4` и materialize-ить только доказанный owner publication packet | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-5-owner-publication-and-prompt-workflow-integration_2026-04-22.md) §D-278 | Done |
| D-279 | Встроить порог обязательности диаграмм в bounded prompt/workflow consumer layer | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-5-owner-publication-and-prompt-workflow-integration_2026-04-22.md) §D-279 | Done |
| D-280 | Синхронизировать границу `owner publication -> prompt consumers -> execution automation` без blocking rollout | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-5-owner-publication-and-prompt-workflow-integration_2026-04-22.md) §D-280 | Done |
| D-281 | Финализировать `TZ-5`, синхронизировать backlog и явно удержать `TZ-4` как единственный upstream gate | [Research TZ](../98-Reviews/research/2026-04/runtime-diagram-substrate-and-agent-readable-exports/DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-5-owner-publication-and-prompt-workflow-integration_2026-04-22.md) §D-281 | Done |

## P1 — Первая публикация owner-артефакта и закон маршрута владельца (2026-04-24)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-282 | Опубликовать owner-side закон первой публикации и route-back границу через `STD` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md) §D-282 | Done |
| D-283 | Materialize-ить companion workflow-doc и нормализовать `docs/85-Operations/**` без повышения ops-layer до owner truth | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md) §D-283 | Done |
| I-1009 | Добавить узкий validator полноты первой публикации и hook-trace без расширения blocking области | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md) §I-1009 | Done |
| D-284 | Закрыть `DEV_TZ-1`, синхронизировать backlog/control-plane и удержать единственный следующий contour = `DEV_TZ-2` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md) §D-284 | Done |

## P1 — Паритет и происхождение SVG-экспорта диаграмм (2026-04-21)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-249 | Оформить локальный индекс `ownership-model/` и соседнее размещение source/SVG | [Research TZ](../98-Reviews/research/2026-04/diagram-svg-export-parity-provenance/DEV_TZ_diagram-svg-export-parity-provenance_2026-04-21.md) §D-249 | Done |
| D-250 | Расширить `export-diagrams.ps1` пакетом происхождения `diagram-export-manifest.json` | [Research TZ](../98-Reviews/research/2026-04/diagram-svg-export-parity-provenance/DEV_TZ_diagram-svg-export-parity-provenance_2026-04-21.md) §D-250 | Done |
| D-251 | Добавить узкий валидатор паритета Markdown/SVG и целевые тесты | [Research TZ](../98-Reviews/research/2026-04/diagram-svg-export-parity-provenance/DEV_TZ_diagram-svg-export-parity-provenance_2026-04-21.md) §D-251 | Done |
| D-252 | Закрыть пакет: синхронизировать `README`, backlog, `CHANGELOG.md` и статус `DEV_TZ` | [Research TZ](../98-Reviews/research/2026-04/diagram-svg-export-parity-provenance/DEV_TZ_diagram-svg-export-parity-provenance_2026-04-21.md) §D-252 | Done |

## P2 — Контракт Markdown-источника и пути генератора диаграмм (2026-04-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-253 | Материализовать локальный контракт вокруг уже доказанного пути генератора текущего семейства | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-253 | Done |
| D-254 | Материализовать локальный структурный контракт для `ownership-model/*.md` | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-254 | Done |
| D-255 | Синхронизировать локальный шов `manifest` / доказательства и профиль `first-mermaid-block-to-sibling-svg` | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-255 | Done |
| D-256 | Синхронизировать локальные несущие поверхности текущего контура | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-256 | Done |
| D-257 | Зафиксировать остаточный вердикт после материализации для `STD-DOC-DIAGRAMS-001` | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-257 | Done |
| D-258 | Финализировать пакет и синхронизировать `DEV_TZ`, backlog и контур доказательства | [Research TZ](../98-Reviews/research/2026-04/diagram-markdown-generator-contract/DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md) §D-258 | Done |

## P2 — Нормализация внешних потребителей устаревших ADR-ссылок Wave 4 (2026-04-15)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-206 | Нормализовать голые устаревшие ADR-ID в architecture.md и Project_Modules_Documentation.md | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-4-external-consumer-sweep_2026-04-15.md) §D-206 | Done |
| D-207 | Обновить устаревшие ADR-токены в drift_patterns.yml, migrate_meta_blocks_to_yaml.py и validators/README.md | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-4-external-consumer-sweep_2026-04-15.md) §D-207 | Done |
| D-208 | Финализировать контур нормализации внешних потребителей Wave 4 | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-4-external-consumer-sweep_2026-04-15.md) §D-208 | Done |

## P0 — Шлюз допустимости playbook производного слоя Wave 3 (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-209 | Опубликовать шлюз допустимости и граничный закон производного слоя в `knowledge_navigation_graph.md` | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-209 | Done |

## P1 — Исполнительный пакет Wave 3 derived layer (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-210 | Опубликовать модель ролей, классификацию G1..G4, набор обязательных предпосылок и четырёхслойный контур доказательств | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-210 | Done |
| D-211 | Опубликовать каноническую безопасную последовательность раскатки и матрицу остановки/перенаправления | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-211 | Done |
| D-212 | Нормализовать границу дозаполнения companion-слоёв и обновить четыре companion surfaces (diagrams/README, prompts/README, scripts/README, genome_registry.json) | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-212 | Done |
| D-214 | Финализировать Wave 3 derived layer: синхронизировать PROGRAM_MAP, INVESTIGATION_QUEUE, backlog и CHANGELOG | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-214 | Done |

## P2 — Каталог анти-паттернов и инвентаризация Wave 3 derived layer (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-213 | Перенести каталог анти-паттернов и baseline-инвентаризацию живых производных семейств в owner layer | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-graph-rollout-derived-layer_2026-04-14.md) §D-213 | Done |

## P0 — Шлюз допустимости тяжёлой раскатки Wave 3 enforcement (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-215 | Опубликовать шлюз допустимости тяжёлого rollout и граничный закон классов C1/C2/C3 в STD-GOVERNANCE-HOOKS-001.md | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-215 | Done |

## P1 — Исполнительный пакет Wave 3 enforcement heavy rollout (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-216 | Создать enforcement_heavy_rollout_playbook.md: модель ролей, таксономия E1..E5, prerequisites, 5-layer proof contour | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-216 | Done |
| D-217 | Опубликовать безопасную последовательность раскатки и закон generator/export/freshness | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-217 | Done |
| D-218 | Опубликовать семантику сбоёв и матрицу остановки/перенаправления | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-218 | Done |

## P2 — Каталог анти-паттернов и инвентаризация Wave 3 enforcement heavy rollout (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-219 | Перенести каталог анти-паттернов и baseline-инвентаризацию кандидатов E1..E5 в enforcement_heavy_rollout_playbook.md | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-219 | Done |

## P3 — Закрытие Wave 3 enforcement heavy rollout (2026-04-14)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-220 | Финализировать Wave 3 enforcement heavy rollout: синхронизировать управляющий слой | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-3-enforcement-heavy-rollout_2026-04-14.md) §D-220 | Done |

## P2 — Post-Closure Enforcement And Runtime Resolution (2026-04-11)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-192 | Убрать docs/scripts shadow-entry к удалённому subtree | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-192 | Done |
| D-193 | Обновить active research artifacts под truth «слой удалён» | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-193 | Done |

## P3 — Post-Closure Enforcement And Runtime Resolution (2026-04-11)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-194 | Нормализовать residual vocabulary в active architecture narrative | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/genome-layer-removal-consistency-fix/DEV_TZ_post-closure-enforcement-and-runtime-resolution_tz-1-genome-layer-removal-consistency-fix_2026-04-11.md) §D-194 | Done |

## P1 — Post-Closure Enforcement And Runtime Resolution / Wave 1 Owner Route (2026-04-12)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-196 | Стабилизировать активные поверхности маршрута владельца и убрать конкурирующие формулировки первого чтения | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §D-196 | Done |
| D-198 | Понизить исторический корпус преемственности `ADR` до безопасного переходного состояния | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §D-198 | Done |
| I-1004 | Оформить ограниченные шлюзы синхронизации и ссылок `ADR` для корпуса маршрута владельца | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §I-1004 | Done |
| I-1005 | Оформить правдивый экспорт реестра и покрытие целостности ссылок для управляющих поверхностей маршрута владельца | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §I-1005 | Done |
| D-199 | Выполнить доказательство закрытия Волны 1 и опубликовать ограничённую передачу для следующих волн без корневого финального вердикта | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §D-199 | Done |
| D-200 | Оформить ограничённый downstream execution contract `Wave 1 -> Waves 2-3` как обязательную базовую линию | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §D-200 | Done |

## P2 — Post-Closure Enforcement And Runtime Resolution / Wave 1 Owner Route (2026-04-12)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-197 | Нормализовать вспомогательный слой `prompt/include` и hook-trail до чисто зеркальной семантики | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §D-197 | Done |
| I-1006 | Зафиксировать ограничённое решение по `CONTRACT partial parity` и шуму на поверхности реестра без конкурирующей семантики владельца | [Research TZ](../98-Reviews/research/2026-04/post-closure-enforcement-and-runtime-resolution/DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md) §I-1006 | Done |

## P1 — Подложка измерений и слой запуска эффективности рабочего пространства (2026-04-30)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-285 | Оформить инженерное руководство по измерению эффективности рабочего пространства | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §D-285 | Done |
| I-1010 | Опубликовать словарь измерений, схемы и описатели семейств | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §I-1010 | Done |
| I-1011 | Оформить адаптер, нормализатор и слой запуска из исходного пакета в нормализованный | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §I-1011 | Done |
| I-1012 | Оформить хранилище нормализованных доказательств, снимки базовой линии и границу сравнения | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §I-1012 | Done |
| I-1013 | Собрать шлюзы проверки синхронизации документации, схем, слоя запуска и доказательств | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §I-1013 | Done |
| D-286 | Закрыть пакет подложки и слоя запуска; подготовить честное разрешение перехода к `DEV_TZ #2` | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-substrate-and-run-harness_2026-04-30.md) §D-286 | Done |

## P1 — Корпус semantic-navigation и регрессионная раскатка (2026-04-30)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-1014 | Оформить описатель корпуса `semantic-navigation` и каталог сценариев | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1014 | Done |
| I-1015 | Подготовить сценарии первого чтения `AGENTS` и проверки загрязнения маршрута | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1015 | Done |
| I-1016 | Подготовить сценарии маршрута стандартов и проверки возврата к владельцу | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1016 | Done |
| I-1017 | Подготовить сценарии маршрута `ADR` и восстановления истории перенаправлений | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1017 | Done |
| I-1018 | Подготовить сценарии классификации типов контракта и маршрута `Artifact Contract` | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1018 | Done |
| I-1019 | Подготовить сценарии маршрутов слоёв `prompt`, `consumer` и `companion` | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1019 | Done |
| I-1020 | Оформить нормализованный регрессионный пакет и состояния базовой линии | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1020 | Done |
| I-1021 | Оформить сравнение регрессий, пороги и правила итогового вывода | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1021 | Done |
| I-1022 | Собрать публикационный пакет, след владельца и локальное доказательство корпуса | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §I-1022 | Done |
| D-287 | Закрыть пакет корпуса `semantic-navigation` и подтвердить честную передачу дальше | [Research TZ](../98-Reviews/research/2026-04/semantic-navigation-benchmark-and-workspace-effectiveness/wave-7-dashboard-storage-regression-and-closure/DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md) §D-287 | Done |

## P2 — Измерительный wrapper DEV_TZ #1: baseline публикации owner-артефакта (2026-05-02)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-288 | Зарегистрировать `family_id = owner-artifact-publication` и оформить каталог сценариев для измерения DEV_TZ #1 | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-pilot-owner-artifact-publication_2026-05-02.md) §D-288 | Done |
| I-1023 | Снять T0 baseline до начала D-282: структурный снимок текущей полноты owner-artifact publication | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-pilot-owner-artifact-publication_2026-05-02.md) §I-1023 | Done |
| I-1025 | Снять navigation-effectiveness T0 baseline до начала D-282: нормализованные метрики маршрута и эффективности навигации агента | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-pilot-owner-artifact-publication_2026-05-02.md) §I-1025 | Done |
| I-1024 | После закрытия D-284 собрать нормализованный результат, снимок базовой линии и пакет сравнения для `owner-artifact-publication` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-pilot-owner-artifact-publication_2026-05-02.md) §I-1024 | Done |
| D-289 | Оформить publication trace и закрыть measurement-pilot с вердиктом | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-pilot-owner-artifact-publication_2026-05-02.md) §D-289 | Done |

## P1 — Нормализация существующего owner-корпуса и миграция (2026-05-03)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-290 | Зафиксировать инвентарь существующего owner-корпуса и карту нормализации `STD / ADR / CONTRACT` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §D-290 | Done |
| D-291 | Классифицировать разрывы, waivers и допустимую область миграции без синтетического добора данных | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §D-291 | Done |
| D-292 | Нормализовать `semantic_id`, lineage, alias/redirect continuity и legacy lookup в owner-корпусе | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §D-292 | Done |
| D-293 | Синхронизировать реестры, `genome_registry.json` и companion route-back после owner-нормализации | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §D-293 | Done |
| I-1026 | При доказанной необходимости добавить узкий validator или шлюз синхронизации для полноты и выявления сломанных маршрутов | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §I-1026 | Cancelled |
| D-294 | Закрыть `DEV_TZ #2`, синхронизировать backlog/control-plane и передать ход дальше без открытия пятого owner `DEV_TZ` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md) §D-294 | Done |

## P1 — Measurement wrapper для DEV_TZ #2: T0 semantic/navigation baseline и compare closure (2026-05-03)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-295 | Зарегистрировать measurement family и каталог сценариев для wrapper вокруг `DEV_TZ #2` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md) §D-295 | Done |
| I-1027 | Снять T0 semantic baseline до начала `D-290` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md) §I-1027 | Done |
| I-1028 | Снять T0 navigation baseline до начала `D-290` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md) §I-1028 | Done |
| I-1029 | После closure `D-294` собрать T1 normalized result и compare package для `DEV_TZ #2` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md) §I-1029 | Done |
| D-296 | Оформить publication trace, закрыть measurement wrapper и синхронизировать control-plane | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md) §D-296 | Done |

## P1 — Производный JSON-слой и непрерывность owner/generated contour (2026-05-05)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-297 | Зафиксировать exact generated artifact set, aggregate-first contract и bounded generation seam | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §D-297 | Done |
| D-298 | Materialize-ить owner-first source-of-truth mapping и sync path `owner -> registries -> generated json` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §D-298 | Done |
| D-299 | Materialize-ить continuity families, owner/generated mismatch handling и drift barriers для generated layer | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §D-299 | Done |
| I-1030 | Добавить узкий validator owner-generated sync и hook-trace без расширения blocking области | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §I-1030 | Done |
| I-1031 | Добавить validator полноты/continuity generated layer и manual-closure ambiguity contour | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §I-1031 | Done |
| D-300 | Закрыть `DEV_TZ #3`, синхронизировать backlog/control-plane и передать ход только в `DEV_TZ #4` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md) §D-300 | Done |

## P1 — Measurement wrapper для DEV_TZ #3: T0 semantic/navigation baseline и compare closure (2026-05-05)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-301 | Зарегистрировать measurement family, каталог сценариев и трёхфазный navigation benchmark для wrapper вокруг `DEV_TZ #3` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md) §D-301 | Done |
| I-1032 | Снять T0 semantic baseline до начала `D-297` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md) §I-1032 | Done |
| I-1033 | Снять T0 navigation baseline до начала `D-297` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md) §I-1033 | Done |
| I-1034 | После closure `D-300` собрать T1 normalized result и compare package для `DEV_TZ #3` | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md) §I-1034 | Done |
| D-302 | Оформить publication trace, закрыть measurement wrapper и синхронизировать control-plane | [Research TZ](../98-Reviews/research/2026-04/owner-artifact-semantic-normalization/DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md) §D-302 | Done |

## P1 — Модель смыслового каталога владельца (2026-05-09)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-303 | Опубликовать owner-side semantic catalog contract и owner Markdown normalization gates | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §D-303 | Done |
| D-304 | Оформить domain-bucket local catalog envelope, route-back grammar и `projection_state` contract | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §D-304 | Done |
| I-1035 | Materialize-ить generator substrate и lightweight transformation `genome_registry.json` | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §I-1035 | Done |
| I-1036 | Добавить validator contour и hook-trace для coverage, route-back, state и forbidden shapes | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §I-1036 | Done |
| D-305 | Синхронизировать операторскую документацию, границу доказательств и передачу к соседнему измерительному пакету | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §D-305 | Done |
| D-306 | Закрыть owner-lane пакет, синхронизировать backlog/control-plane и удержать execution gate до sibling measurement-wrapper review | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md) §D-306 | Done |
| D-307 | Зарегистрировать measurement family, wrapper identity и storage contract для semantic catalog corpus | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §D-307 | Done |
| D-308 | Оформить scenario catalog, 14 scenario classes, measurement dimensions и route-cost contract | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §D-308 | Done |
| I-1037 | Снять T0 semantic baseline до первого owner-change `D-303` | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §I-1037 | Done |
| I-1038 | Снять T0 navigation baseline до первого owner-change `D-303` и git-зафиксировать T0 gate | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §I-1038 | Done |
| I-1039 | После closure `D-306` собрать T1 normalized result для semantic и navigation contour | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §I-1039 | Done |
| I-1040 | Собрать compare package `T1 vs T0` и route-cost delta без dashboard unlock | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §I-1040 | Done |
| D-309 | Оформить publication trace, publication index sync и companion-only summary для wrapper-а | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §D-309 | Done |
| D-310 | Закрыть measurement wrapper, синхронизировать backlog/control-plane и удержать dashboard/runtime lock | [Research TZ](../98-Reviews/research/2026-05/owner-semantic-catalog-model/DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md) §D-310 | Done |

## P1 — Смысловой JSON-слой каталога владельца (2026-05-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-1045 | Зафиксировать schema / contract / admissibility границу для block-level companion projection | [Research TZ](../98-Reviews/research/2026-05/owner-catalog-semantic-json-layer/DEV_TZ_owner-catalog-semantic-json-layer_owner-catalog-semantic-json-layer-dev-tz-synthesis_2026-05-22.md) §I-1045 | Done |
| I-1046 | Расширить generator и повторную генерацию local catalogs без выхода за границы companion-only слоя | [Research TZ](../98-Reviews/research/2026-05/owner-catalog-semantic-json-layer/DEV_TZ_owner-catalog-semantic-json-layer_owner-catalog-semantic-json-layer-dev-tz-synthesis_2026-05-22.md) §I-1046 | Done |
| I-1047 | Расширить validator и доказательный контур под enriched states и запрещённые формы дрейфа | [Research TZ](../98-Reviews/research/2026-05/owner-catalog-semantic-json-layer/DEV_TZ_owner-catalog-semantic-json-layer_owner-catalog-semantic-json-layer-dev-tz-synthesis_2026-05-22.md) §I-1047 | Done |
| D-336 | Синхронизировать операторский сценарий, backlog и scope control-plane и закрыть ограничённый пакет без broad unlock | [Research TZ](../98-Reviews/research/2026-05/owner-catalog-semantic-json-layer/DEV_TZ_owner-catalog-semantic-json-layer_owner-catalog-semantic-json-layer-dev-tz-synthesis_2026-05-22.md) §D-336 | Done |

## P1 — Agentic Workspace Effectiveness MVP (2026-05-25)

> Канонический backlog уже зафиксировал фактическое post-execution состояние:
> `D-337..D-342` синхронизированы в `Done`.
> `STATUS_ENUM_LIMITATION`: отдельного terminal/admission-token здесь нет,
> поэтому отсутствие automatic next step фиксируется narrative-слоем, а не
> новым enum-значением.
> Соседний `PRR_agentic-workspace-effectiveness-mvp_2026-05-25.md`
> остаётся историей plan-review и не открывает новый execution-cycle.
> Wave 6 закрыта как `materialized`, runtime overlay не открывается.

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-337 | `DEV_TZ v0.3`: опубликовать и сшить `Agent Launch Packet v1` (исполнено как локальный пилотный носитель программы; broad unlock не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.1 | Done |
| D-338 | `DEV_TZ v0.3`: опубликовать и сшить `Project State Snapshot v1` (исполнено как локальный производный обзор состояния проекта; broad unlock не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.2 | Done |
| D-339 | `DEV_TZ v0.3`: опубликовать и сшить `Capability / Mutation Matrix v1` (исполнено как локальная пилотная матрица границ, запретов и возврата по маршруту владельца; broad unlock не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.3 | Done |
| D-340 | `DEV_TZ v0.3`: опубликовать и сшить `Work Unit Envelope v1` (исполнено как локальный пилотный конверт рабочей единицы; broad unlock не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.4 | Done |
| D-341 | `DEV_TZ v0.3`: зафиксировать measurement protocol и провести ограниченный effectiveness pilot (исполнено как локальный ручной pilot report с verdict `improvement-confirmed` / `PARTIAL_EFFECTIVENESS_WITH_FIXES`; runtime overlay не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.5 | Done |
| D-342 | `DEV_TZ v1.0`: выполнить terminal Wave 6 closure и control-plane sync (исполнено как closure carrier, sync mirrors/backlog и package verdict `MVP_ACCEPTED_FOR_LOCAL_PILOT_ONLY`; runtime overlay не открыт) | [Research TZ](../98-Reviews/research/2026-05/agentic-workspace-effectiveness-mvp/DEV_TZ_agentic-workspace-effectiveness-mvp_2026-05-25.md) §5.6 | Done |

## P1 — Agentic Workspace Effectiveness Adoption (2026-05-27)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-343 | Материализовать рабочую поверхность Agentic Workspace Launch Kit | [Execution DEV_TZ](../98-Reviews/execution/2026-05/agentic-workspace-effectiveness-adoption/DEV_TZ_agentic-workspace-effectiveness-adoption_2026-05-27.md) §D-343 | Done |
| D-344 | Материализовать мост запуска сессии для Agentic Workspace | [Execution DEV_TZ](../98-Reviews/execution/2026-05/agentic-workspace-effectiveness-adoption/DEV_TZ_agentic-workspace-effectiveness-adoption_2026-05-27.md) §D-344 | Done |
| D-345 | Доказать использование операционного набора Agentic Workspace агентом | [Execution DEV_TZ](../98-Reviews/execution/2026-05/agentic-workspace-effectiveness-adoption/DEV_TZ_agentic-workspace-effectiveness-adoption_2026-05-27.md) §D-345 | Done |
| D-346 | Закрыть adoption-контур Agentic Workspace с Physical Integration Proof | [Execution DEV_TZ](../98-Reviews/execution/2026-05/agentic-workspace-effectiveness-adoption/DEV_TZ_agentic-workspace-effectiveness-adoption_2026-05-27.md) §D-346 | Done |

## P1 — Documentation Operating Model and Code-Doc Parity (2026-05-28)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-347 | Создать рабочую карту владельцев документационной модели AIFE | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-347 | Done |
| D-348 | Встроить проверку влияния `.py`-изменений на docstrings/docs/help в prompt-layer | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-348 | Done |
| D-349 | Определить границу валидатора и checklist для code-doc parity | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-349 | Done |
| D-350 | Исправить только активные stale/duplicate документы по audit inventory | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-350 | Done |

## P2 — Documentation Operating Model and Code-Doc Parity (2026-05-28)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-351 | Опубликовать карту route-back для user/in-app/runtime/developer help | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-351 | Done |
| D-352 | Создать безопасный disposition index для evidence/history corpus | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-352 | Done |
| D-353 | Проверить package/module README coverage по code-doc inventory | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-operating-model-and-code-doc-parity/DEV_TZ_documentation-operating-model-and-code-doc-parity_2026-05-28.md) §D-353 | Done |

## P1 — Documentation Implementation Truth Alignment (2026-05-30)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-354 | Разделить текущую и плановую архитектурную документацию AIFE | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-implementation-truth-alignment/DEV_TZ_documentation-implementation-truth-alignment_2026-05-30.md) §D-354 | Done |
| D-355 | Закрыть минимальное покрытие package README и route-back prompt/instruction system | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-implementation-truth-alignment/DEV_TZ_documentation-implementation-truth-alignment_2026-05-30.md) §D-355 | Done |
| D-356 | Синхронизировать семантический статус диаграмм и активные stale/index claims | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-implementation-truth-alignment/DEV_TZ_documentation-implementation-truth-alignment_2026-05-30.md) §D-356 | Done |
| D-357 | Ограничить и закрыть code-doc parity hotspots по public API/docstrings/comments | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-implementation-truth-alignment/DEV_TZ_documentation-implementation-truth-alignment_2026-05-30.md) §D-357 | Done |
| D-358 | Проверить физический эффект контура и оформить terminal closure proof | [Execution DEV_TZ](../98-Reviews/execution/2026-05/documentation-implementation-truth-alignment/DEV_TZ_documentation-implementation-truth-alignment_2026-05-30.md) §D-358 | Done |

## P1 — Синхронизация раздела docs/00-Guidelines (2026-05-31)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-G00-1 | Синхронизировать реестр и фактические файлы раздела `docs/00-Guidelines` | [Execution DEV_TZ](../98-Reviews/execution/2026-05/guidelines-00-sync/DEV_TZ_guidelines-00-sync_2026-05-31.md) §D-G00-1 | Done |
| D-G00-2 | Убрать устаревший prompt-id и выровнять язык активных гайдов | [Execution DEV_TZ](../98-Reviews/execution/2026-05/guidelines-00-sync/DEV_TZ_guidelines-00-sync_2026-05-31.md) §D-G00-2 (depends on D-G00-1) | Done |
| D-G00-3 | Чётко обозначить GitHub Issues и VCS как опциональные guidance-носители | [Execution DEV_TZ](../98-Reviews/execution/2026-05/guidelines-00-sync/DEV_TZ_guidelines-00-sync_2026-05-31.md) §D-G00-3 (depends on D-G00-1, D-G00-2) | Done |
| D-G00-4 | Довести тестовый индекс и доказательный контур до согласованного состояния | [Execution DEV_TZ](../98-Reviews/execution/2026-05/guidelines-00-sync/DEV_TZ_guidelines-00-sync_2026-05-31.md) §D-G00-4 (depends on D-G00-1, D-G00-2) | Done |

Постзакрывающий архивный итог: `PHASE_TRACKER.md` и `QUALITY_AUDIT.md`
оставлены как `historical traceability`; новый follow-up не открыт
(`no_open_followup`).

## P2 — Контроль терминального состояния семантической документации (2026-06-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-364 | Провести audit-first исследование междокументной проверки маркеров терминального состояния жизненного цикла для семантических документационных папок, определить границу промпта, контрольного списка и валидатора; владелец решения — `Architecture Lead`, потребитель — `Documentation Team`, автоматический запуск запрещён | [Execution DEV_TZ](../98-Reviews/execution/2026-06/docs-44-patterns-runtime-sync/DEV_TZ_docs-44-patterns-runtime-sync_2026-06-19.md) §Маршрут системного долга `D-364` | Backlog |

## P1 — Вывод старого контура патчей и проверяемая передача Git-патча (2026-06-22)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-365 | Переработать `STD-CHANGE-001` и живые правила управления изменениями без требований старого `patches/**` | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_legacy-retirement_2026-06-22.md) §D-365 | Done |
| I-1048 | Удалить устаревший валидатор артефактов изменений, его хук и специальные исключения качества для `patches/**` | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_legacy-retirement_2026-06-22.md) §I-1048 | Done |
| L-015 | Удалить корневой `patches/**` и синхронизировать живую архитектурную навигацию без зеркального архива | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_legacy-retirement_2026-06-22.md) §L-015 | Done |
| D-366 | Выполнить терминальное закрытие вывода старого контура патчей и подтвердить безопасный прямой процесс исполнения | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_legacy-retirement_2026-06-22.md) §D-366 | Done |
| D-367 | Опубликовать стандарт и ADR проверяемой передачи Git-патча авторизованному исполнителю | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §D-367 | Done |
| I-1049 | Реализовать схемы, валидатор предварительной проверки командной строки и модульные тесты проверяемой передачи | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §I-1049 | Done |
| D-368 | Встроить нейтральный к исполнителю маршрут передачи в инструкции и промпты | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §D-368 | Done |
| I-1050 | Связать происхождение входной передачи с итоговым пакетом проверки | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §I-1050 | Done |
| I-1051 | Провести пилотные испытания ручного и агентского применения, включая отказные сценарии | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §I-1051 | Done |
| D-369 | Выполнить терминальное принятие механизма с необязательным статусом `optional` | [Execution DEV_TZ](../98-Reviews/execution/2026-06/legacy-root-patches-and-verified-patch-handoff/DEV_TZ_legacy-root-patches-and-verified-patch-handoff_verified-handoff_2026-06-22.md) §D-369 | Done |
| D-370 | В восьми миграционных волнах удалить `review_cycle_days` и `next_review_due` из 360 исторических файлов со `status: archived`, затем волной очистки вывести базовую линию, схему и переходный API без ослабления валидатора | [Execution DEV_TZ](../98-Reviews/execution/2026-06/archived-review-schedule-debt-retirement/DEV_TZ_archived-review-schedule-debt-retirement_2026-06-27.md) §Task Contract D-370 | Done |

## P1 — Усиление verified patch handoff v3 (2026-06-27)

| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| D-371 | Опубликовать owner-модель v3 verified patch handoff с обязательной binding-связью через `CONTRACT-CHANGE-HANDOFF-001` | [Execution DEV_TZ](../98-Reviews/execution/2026-06/verified-patch-handoff-contract-and-execution-hardening/DEV_TZ_verified-patch-handoff-contract-and-execution-hardening_2026-06-27.md) §Task Contract D-371 | Done |
| I-1052 | Реализовать manifest schema `3.0`, per-task authorization, trusted enforcement, candidate validation и closure package binding | [Execution DEV_TZ](../98-Reviews/execution/2026-06/verified-patch-handoff-contract-and-execution-hardening/DEV_TZ_verified-patch-handoff-contract-and-execution-hardening_2026-06-27.md) §Task Contract I-1052 | Done |
| B-010 | Исправить index-safe повторный exact stage уже staged-удалений во всех repair/execute маршрутах | [Execution DEV_TZ](../98-Reviews/execution/2026-06/verified-patch-handoff-contract-and-execution-hardening/DEV_TZ_verified-patch-handoff-contract-and-execution-hardening_2026-06-27.md) §Task Contract B-010 | Done |
| D-372 | Финализировать bootstrap и весь verified patch handoff v3 через промежуточный и итоговый closure-контур | [Execution DEV_TZ](../98-Reviews/execution/2026-06/verified-patch-handoff-contract-and-execution-hardening/DEV_TZ_verified-patch-handoff-contract-and-execution-hardening_2026-06-27.md) §Task Contract D-372 | Done |
| I-1053 | Синхронизировать потребительские семантические проекции verified patch handoff v3 и исправить архивные формулировки закрытия | [Execution DEV_TZ](../98-Reviews/execution/2026-06/verified-patch-handoff-contract-and-execution-hardening/DEV_TZ_verified-patch-handoff-contract-and-execution-hardening_2026-06-27.md) §Архивная поправка I-1053 | Done |
| D-373 | Развести прямой Git-патч и проверяемую передачу без создания второй патч-системы | [Execution DEV_TZ](../98-Reviews/execution/2026-06/direct-patch-and-verified-handoff-routing/DEV_TZ_direct-patch-and-verified-handoff-routing_2026-06-30.md) §Task Contract D-373 | Done |

## P1 — Standards Open Checklists (AUTO)

> Авто-секция: синхронизируется из closure-readiness snapshot при запуске `check_backlog.py`; правило приоритета: approved + wave W1 (если применимо).

<!-- BEGIN: AUTO-STD-OPEN-CHECKLISTS-P1 -->
| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-921 | [STD-ARCH-PATTERNS-001] Закрыть 10 открытых roadmap-чекбоксов (type B) (status=proposed, domain=ARCH, rule=rollout-W1) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W1 | Backlog |
| I-903 | [STD-DOC-INSTRUCTIONS-001] Закрыть 7 открытых roadmap-чекбоксов (type B) (status=approved, domain=DOC, rule=approved-actionable-rollout) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W1 | Backlog |
| I-929 | [STD-ARCH-ASYNC-001] Закрыть 2 открытых roadmap-чекбоксов (type B) (status=proposed, domain=ARCH, rule=rollout-W1) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W1 | Backlog |
| I-920 | [STD-SEC-VULN-001] Закрыть 2 открытых roadmap-чекбоксов (type B) (status=approved, domain=SEC, rule=approved-actionable-rollout) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W1 | Backlog |
<!-- END: AUTO-STD-OPEN-CHECKLISTS-P1 -->

## P2 — Standards Open Checklists (AUTO)

> Авто-секция: синхронизируется из closure-readiness snapshot при запуске `check_backlog.py`; правило приоритета: wave W2 + proposed fallback.

<!-- BEGIN: AUTO-STD-OPEN-CHECKLISTS-P2 -->
| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-902 | [STD-DATA-SCHEMA-001] Закрыть 8 открытых roadmap-чекбоксов (type B) (status=draft, domain=DATA, rule=rollout-W2) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W2 | Backlog |
| I-901 | [STD-GOVERNANCE-IMPROVEMENT-001] Закрыть 1 открытых roadmap-чекбоксов (type B) (status=proposed, domain=GOVERNANCE, rule=rollout-W2) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W2 | Backlog |
<!-- END: AUTO-STD-OPEN-CHECKLISTS-P2 -->

## P3 — Standards Open Checklists (AUTO)

> Авто-секция: синхронизируется из closure-readiness snapshot при запуске `check_backlog.py`; правило приоритета: wave W3 + draft fallback.

<!-- BEGIN: AUTO-STD-OPEN-CHECKLISTS-P3 -->
| ID | Задача | Источник | Статус |
|----|--------|----------|--------|
| I-910 | [STD-MON-DASHBOARD-001] Закрыть 16 открытых roadmap-чекбоксов (type B) (status=draft, domain=MON, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-916 | [STD-MON-METRICS-001] Закрыть 13 открытых roadmap-чекбоксов (type B) (status=draft, domain=MON, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-917 | [STD-MON-ALERTING-001] Закрыть 12 открытых roadmap-чекбоксов (type B) (status=draft, domain=MON, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-918 | [STD-PERF-BENCHMARK-001] Закрыть 12 открытых roadmap-чекбоксов (type B) (status=draft, domain=PERF, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-923 | [STD-MON-HEALTH-001] Закрыть 11 открытых roadmap-чекбоксов (type B) (status=draft, domain=MON, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-926 | [STD-PERF-CACHING-001] Закрыть 10 открытых roadmap-чекбоксов (type B) (status=draft, domain=PERF, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-908 | [STD-PERF-OPTIMIZATION-001] Закрыть 10 открытых roadmap-чекбоксов (type B) (status=draft, domain=PERF, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-930 | [STD-MON-BASE-001] Закрыть 9 открытых roadmap-чекбоксов (type B) (status=draft, domain=MON, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
| I-931 | [STD-PERF-PROFILING-001] Закрыть 9 открытых roadmap-чекбоксов (type B) (status=draft, domain=PERF, rule=rollout-W3) | [Closure Readiness](../98-Reviews/audits/2026-02/genome/closure_readiness_report_latest.md) §Open checklist tracker; [Rollout TZ](../98-Reviews/audits/2026-02/genome/TZ_genome_standards_rollout_planned_2026-02-23.md) §W3 | Backlog |
<!-- END: AUTO-STD-OPEN-CHECKLISTS-P3 -->

## Статистика

| Приоритет | Всего | Backlog | In Progress | Done | Cancelled |
|-----------|:-----:|:-------:|:-----------:|:----:|:---------:|
| P0 | 104 | 0 | 0 | 104 | 0 |
| P1 | 454 | 6 | 2 | 435 | 11 |
| P2 | 176 | 14 | 0 | 162 | 0 |
| P3 | 29 | 9 | 0 | 20 | 0 |
| __Итого__ | __763__ | __29__ | __2__ | __721__ | __11__ |

*Последнее обновление: 2026-05-11 (выполнен `D-310` из `DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md`: measurement wrapper `owner-semantic-catalog-layer-measurement` переведён в terminal closure state `archived`, `DEV_TZ`, canonical backlog, scope `README.md`, `PROGRAM_MAP_*`, `INVESTIGATION_QUEUE_*`, scope `CHANGELOG.md` и root `CHANGELOG.md` синхронизированы до `D-310 = Done`, а автоматический следующий шаг внутри текущего wrapper-а снят. Dashboard/runtime contour по-прежнему остаётся locked; новый owner route и rollout локальных смысловых каталогов этим closure-change-set не открывались. Proof: `python scripts/check_backlog.py` — backlog valid and parseable, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `pytest --no-cov tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d307.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d308.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1037.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1038.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1039.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1040.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d309.py -q` — `34 passed`; follow-up repo-wide terminal cleanup снял устаревший blocker-report по `validate-structure`: `python -m pre_commit run --all-files` теперь проходит зелёно, а stale truth-expectations в `D-291`, `D-292`, `D-293`, `D-301` синхронизированы без переписывания immutable measurement evidence.)*

*Последнее обновление: 2026-05-09 (выполнен `I-1036` из `DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md`: materialize-ён bounded validator package `scripts/validators/semantic_catalog/**` с проверками coverage, route-back, state separation, forbidden shapes и purity глобального индекса; `scripts/standards/registry_generator.py` дополнительно получил family-qualified/path-stable `required_generated_artifact_set.id`, а `.pre-commit-config.yaml` и `.aife/hook_registry.yml` расширены bounded advisory hook trace `validate-semantic-catalog-boundaries`. Синхронизированы owner `DEV_TZ`, scope `README.md`, `PROGRAM_MAP_*`, sibling `PRR`, scope `CHANGELOG.md`, root `CHANGELOG.md` и canonical backlog; следующий честный owner-step теперь = только `D-305`, а `T1` / compare / publication package и dashboard/runtime по-прежнему не materialize-ились. Proof: `pytest tests/unit/standards/test_registry_generator_json.py tests/unit/validators/semantic_catalog/test_validate_semantic_catalog_boundaries.py tests/unit/validators/generated_layer/test_validate_owner_generated_sync.py tests/unit/validators/generated_layer/test_validate_generated_completeness.py tests/unit/validators/generated_layer/test_validate_generated_continuity.py -q` — passed, `python scripts/standards/registry_generator.py --apply` — passed, `python scripts/standards/registry_generator.py --check` — passed, `python scripts/validators/generated_layer/validate_owner_generated_sync.py --check` — passed, `python scripts/validators/semantic_catalog/validate_semantic_catalog_boundaries.py --check` — passed.)*

*Последнее обновление: 2026-05-09 (выполнен `I-1035` из `DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md`: generation substrate расширен helper-модулем `scripts/standards/_semantic_catalog_generation.py`, а `scripts/standards/registry_generator.py` теперь materialize-ит только разрешённые domain-bucket catalogs в `genome/standards/<domain>/<domain>.json`, `genome/adr/<domain>/<domain>.json` и `genome/contracts/<domain>/<domain>.json`; `genome_registry.json` удержан в роли lightweight route/status/coverage index с `semantic_catalog_ref`, `semantic_catalog_state`, `coverage_summary`, `family_counts` и `semantic_catalog_state_counts` без semantic bodies. Синхронизированы owner `DEV_TZ`, measurement `DEV_TZ`, scope `CHANGELOG.md`, root `CHANGELOG.md` и canonical backlog; следующий честный owner-step теперь = только `I-1036`, а validator contour, `T1` / compare / publication package и dashboard/runtime по-прежнему не materialize-ились. Proof: `pytest tests/unit/standards/test_registry_generator_json.py -q` — passed, `python scripts/standards/registry_generator.py --apply` — passed, `python scripts/standards/registry_generator.py --check` — passed.)*

*Последнее обновление: 2026-05-09 (выполнен `D-304` из `DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md`: materialized owner-readable companion carrier `ARCHITECTURE_owner-semantic-catalog-model_local-semantic-catalog-envelope_2026-05-09.md`, который фиксирует domain-bucket envelope для `STD` / `ADR` / `CONTRACT`, grammar `artifact_route_back_ref`, vocabulary `projection_state` / `semantic_catalog_state` и запрет root-level semantic catalogs / per-artifact fleet. Синхронизированы owner `DEV_TZ`, оба sibling `PRR`, scope `README.md`, `PROGRAM_MAP_*`, `INVESTIGATION_QUEUE_*`, `CHANGELOG.md`, canonical backlog и support-anchor в `docs/10-Architecture/general/architecture.md`; generator substrate, validator contour, `T1` / compare / publication package и dashboard/runtime не materialize-ились. Proof: `python scripts/check_backlog.py` — backlog valid and parseable, `python scripts/validators/validate_tz_backlog_sync.py` — OK.)*

*Последнее обновление: 2026-05-09 (выполнен `D-303` из `DEV_TZ_owner-semantic-catalog-model_owner-semantic-catalog-layer_2026-05-09.md`: в `STD-GOVERNANCE-ROUTING-001` опубликован owner-law boundary для generated semantic catalog layer с различением `artifact-level` и `block-level` route-back, а в `STD-DOC-METADATA-001` опубликован owner-side normalization contract с named semantic blocks для `STD` / `ADR` / `CONTRACT` и Markdown normalization gates. `STANDARDS_REGISTRY.md` и `genome_registry.json` синхронизированы через `registry_generator.py`, canonical backlog и owner `DEV_TZ` переведены на `D-303 = Done`; следующий честный owner-step теперь = только `#prompt:execute-task` для `D-304`, а post-owner measurement branch `I-1039 -> I-1040 -> D-309 -> D-310` по-прежнему заблокирован до `D-306`. Proof: `python scripts/standards/registry_generator.py --check` — passed, `python scripts/validators/generated_layer/validate_owner_generated_sync.py --check` — passed.)*

*Последнее обновление: 2026-05-09 (выполнен `I-1037` из `DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md`: создан immutable semantic T0 baseline `.benchmarks/baselines/owner-semantic-catalog-layer-measurement-semantic-t0-baseline/baseline_snapshot.json` с truthful pre-owner git/timestamp state, carrier-контрактами и 14 scenario values = `false`, а также добавлен family-local proof `tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1037.py`. Синхронизированы measurement `DEV_TZ`, owner `DEV_TZ`, оба sibling `PRR`, scope `README.md`, `PROGRAM_MAP_*`, `INVESTIGATION_QUEUE_*` и canonical backlog до `I-1037 = Done`; следующий честный measurement step теперь = только `#prompt:execute-task` для `I-1038`, owner execution по-прежнему заблокирован до git-фиксации `I-1038`. Proof: `python -m pytest tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d307.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d308.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_i1037.py -q` — `14/14` PASSED, `python scripts/check_backlog.py` — backlog valid and parseable, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m scripts.benchmarks.sync_gates` — `6/6` PASSED.)*

*Последнее обновление: 2026-05-09 (выполнен `D-308` из `DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md`: registration-only carrier stub заменён на shared `planned_scenarios_only` catalog `.aife/measurement/catalog/owner_semantic_catalog_layer_measurement.scenario_catalog.json` с 14 обязательными scenario classes, mandatory measurement dimensions, route-cost grammar, baseline state model и contamination policy для `T0-MD`, `T1-MD`, `T1-JSON`; синхронизированы `.aife/measurement/families/owner_semantic_catalog_layer_measurement/corpus_descriptor.json` и `.aife/measurement/families/family_taxonomy.json`, targeted proof `tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d307.py` переведён на устойчивые registration invariants и добавлен `tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d308.py`. Proof: `python -m pytest tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d307.py tests/unit/scripts/benchmarks/owner_semantic_catalog_layer_measurement/test_d308.py -q` — `8/8` PASSED, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m scripts.benchmarks.sync_gates` — `6/6` PASSED; поэтому `D-308 = Done`, а следующий честный measurement step теперь = только `#prompt:execute-task` для `I-1037`, owner execution по-прежнему заблокирован до git-фиксации `I-1037 -> I-1038`.)*

*Последнее обновление: 2026-05-09 (выполнен `D-307` из `DEV_TZ_owner-semantic-catalog-model_measurement-owner-semantic-catalog-layer_2026-05-09.md`: создан новый measurement wrapper `owner-semantic-catalog-layer-measurement` в `.aife/measurement/**`, materialized `.aife/measurement/families/owner_semantic_catalog_layer_measurement/corpus_descriptor.json` и registration-only carrier stub `.aife/measurement/catalog/owner_semantic_catalog_layer_measurement.scenario_catalog.json`, а `.aife/measurement/families/family_taxonomy.json`, `.aife/measurement/publication/index.json` и live measurement schemas синхронизированы под новый family без преждевременного открытия `D-308`. Route-back удержан к owner-lane `DEV_TZ` и scope control-plane, storage contract ограничен `.benchmarks/**` + `.aife/measurement/**`, dashboard/runtime consumer остаётся locked, а owner execution по-прежнему заблокирован до git-фиксации measurement T0 gate `D-307 -> D-308 -> I-1037 -> I-1038`. Следующий честный шаг — только `#prompt:execute-task` для `D-308`.)*

*Последнее обновление: 2026-05-07 (выполнен `D-302` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md`: создан `.aife/measurement/publication/owner-artifact-derived-json-generation-and-continuity-pilot-package.json` как companion-only publication trace для registry-level generated substrate вокруг `DEV_TZ #3`, `.aife/measurement/publication/index.json` обновлён новой записью пакета и marker-constraint, а targeted proof `tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_d302.py` подтвердил возврат к `D-301`, `I-1032`, `I-1033`, `I-1034` и owner closure `D-300`. Publication verdict опирается только на route-count, artifact-count, route-back, contamination contract и `generated-as-owner-violation-count`; сравнение по секундам честно зафиксировано как `unavailable` и в вывод не включается. Semantic catalog JSON layer не materialized, `PROGRAM_MAP_AMENDMENT` не выполнялся, `DEV_TZ #4` execution не открывался, dashboard/runtime и examples-validation-and-consumer-rollout не materialize-ились. Proof: `python -m pytest tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_d302.py -q` — `4/4` PASSED, `python -m pytest tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1032.py tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1033.py tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1034.py -q` — `18/18` PASSED, `python -m scripts.benchmarks.sync_gates` — `6/6` PASSED, `python scripts/check_backlog.py` — backlog valid and parseable, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m pre_commit run --all-files` — Passed; поэтому `D-302 = Done`, measurement-lane для wrapper-а закрыта, старый контур удерживается как `paused` / `closed-at-registry-level`, а любой последующий semantic catalog / examples / consumer rollout шаг допустим только через внешний контур `owner-semantic-catalog-model`.)*

*Последнее обновление: 2026-05-06 (выполнен `I-1034` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md`: после обязательного preflight-подтверждения полноты live repo post-`D-300` собраны `.benchmarks/results/owner-artifact-derived-json-generation-and-continuity-post-tz3/normalized_result.json` и `.benchmarks/compare/owner-artifact-derived-json-generation-and-continuity-first-compare/compare_package.json`, а также targeted proof `tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1034.py`; T1 semantic packet честно подтверждает `11/11` scenario values = `true`, `owner_generated_sync_parity_pct = 100.0`, `continuity_family_coverage_pct = 100.0`, `generated_as_owner_violation_count = 0`, `manual_ambiguity_case_count = 2`, `contamination_events = 0`, а navigation compare сохраняет route-back law и clean contamination contract: `T1-MD` удерживает `.md-only` маршрут (`33` шага, `33` opened Markdown artifacts), `T1-JSON` снижает стоимость маршрута до `29` шагов и `20` opened Markdown artifacts при `opened_json_count = 9`, `route_back_confirmed = true` и без подмены owner truth generated JSON-слоем. Required sync-fix после независимого повтора proof выполнен только на стороне `tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1034.py`: live contract выровнен на `t1_result_path`, а compare navigation totals больше не требуют stale `scenario_count`; сами result/compare артефакты не переписывались. Proof: `python -m pytest tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1032.py tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1033.py tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1034.py -q` — `12/12` PASSED, `python -m scripts.benchmarks.sync_gates` — `6/6` PASSED, `python scripts/check_backlog.py` — backlog valid and parseable; поэтому `I-1034 = Done`, а ближайший допустимый следующий шаг в measurement-lane теперь = только `#prompt:execute-task` для `D-302`, который по-прежнему остаётся downstream closure-шагом и не выполнялся в этом change-set.)*

*Последнее обновление: 2026-05-06 (выполнен `D-300` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md`: `DEV_TZ #3` переведён в terminal state `archived`, scope `README.md`, canonical backlog и `CHANGELOG.md` синхронизированы до `D-300 = Done`, а honest handoff разведен без расширения scope: owner-lane теперь допускает только `#prompt:plan-review` для `DEV_TZ #4`, measurement-lane — только `#prompt:execute-task` для `I-1034`, тогда как `D-302` остаётся downstream closure-шагом после `I-1034`. Отдельный closure-артефакт не создавался, потому что task-card `D-300` закрывает пакет через terminal state текущего `DEV_TZ`; `DEV_TZ #4`, `I-1034`, `D-302`, compare/publication package, dashboard/runtime и per-artifact JSON fleet не materialize-ились. Proof: preflight `python scripts/standards/registry_generator.py --check` — PASSED и `python -m pytest tests/unit/standards/test_registry_generator_json.py -q` — `10/10` PASSED; затем `python -m pytest tests/unit/validators/generated_layer/ -q` — `10/10` PASSED, повторный `python -m pytest tests/unit/standards/test_registry_generator_json.py -q` — `10/10` PASSED, `python scripts/standards/registry_generator.py --check` — PASSED, `python scripts/validators/generated_layer/validate_owner_generated_sync.py --check` — PASSED, `python scripts/validators/generated_layer/validate_generated_completeness.py --mode closure` — PASSED, `python scripts/validators/generated_layer/validate_generated_continuity.py --mode manual` и `--mode closure` — PASSED, `python scripts/check_backlog.py` — backlog valid and parseable, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m pre_commit run --all-files` — Passed; поэтому `D-300 = Done`, owner `DEV_TZ #3` закрыт, а ближайший допустимый следующий шаг по соседнему measurement contour теперь = только `I-1034`.)*

*Последнее обновление: 2026-05-06 (выполнен `I-1031` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md`: добавлены `scripts/validators/generated_layer/validate_generated_completeness.py` и `scripts/validators/generated_layer/validate_generated_continuity.py`, которые закрепляют packet-4 split для generated layer без broad blocking rollout: completeness closure не даёт derived payload закрываться при отсутствии required families или named blocker families, continuity contour удерживает truthful blocker/advisory/manual semantics и явный manual ambiguity route для `alias_history` / `redirect_history_trace`. Обновлены package surface `scripts/validators/generated_layer/__init__.py`, targeted proof-модули `tests/unit/validators/generated_layer/test_validate_generated_completeness.py` и `tests/unit/validators/generated_layer/test_validate_generated_continuity.py`, а также узкий operator/control-plane слой: `.pre-commit-config.yaml` получил только `manual` hook `validate-generated-continuity-manual`, `.aife/hook_registry.yml` синхронизирован до `live_hook_count = 52`, `scripts/validators/README.md` фиксирует split `pre-commit / manual / closure / advisory` без расширения в `examples-validation-and-consumer-rollout`, dashboard/runtime, `DEV_TZ #4`, measurement baselines и per-artifact JSON fleet. Proof: `python -m pytest tests/unit/validators/generated_layer/ -q` + `python -m pytest tests/unit/standards/test_registry_generator_json.py -q` — `20/20` PASSED, `python scripts/standards/registry_generator.py --check` — PASSED, `python scripts/validators/generated_layer/validate_owner_generated_sync.py --check` — PASSED, `python scripts/validators/generated_layer/validate_generated_completeness.py --mode closure` — PASSED, `python scripts/validators/generated_layer/validate_generated_continuity.py --mode manual` и `--mode closure` — PASSED, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m pre_commit run --all-files` — Passed; поэтому `I-1031 = Done`, а ближайший допустимый owner-step теперь = только `#prompt:execute-task` для `D-300`.)*

*Последнее обновление: 2026-05-06 (выполнен `I-1030` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md`: создано узкое семейство `scripts/validators/generated_layer/` с `validate_owner_generated_sync.py`, которое пересобирает expected payload через `registry_generator.py`, сравнивает только aggregate carrier `genome/registries/genome_registry.json` и ограниченные sync-секции generated layer, а по умолчанию остаётся advisory и переходит в blocking только по `--check`; direct-script bootstrap укреплён, поэтому validator честно запускается как модуль и как файл. В `.pre-commit-config.yaml` добавлен только один узкий hook `validate-owner-generated-sync`, `.aife/hook_registry.yml` синхронизирован до `live_hook_count = 51`, `scripts/validators/README.md` обновлён под новый contour, а `.pre-commit-config.yaml` сохранён единственным runtime-dispatch owner без расширения hook coverage на `examples-validation-and-consumer-rollout`, dashboard/runtime, `DEV_TZ #4`, per-artifact JSON fleet и соседние measurement/closure contour-ы. Proof: `tests/unit/validators/generated_layer/test_validate_owner_generated_sync.py` + `tests/unit/standards/test_registry_generator_json.py` — `14/14` PASSED, `python scripts/validators/generated_layer/validate_owner_generated_sync.py --check` — PASSED, `python scripts/validators/validate_tz_backlog_sync.py` — OK, `python -m pre_commit run --all-files` — Passed; поэтому `I-1030 = Done`, а ближайший допустимый owner-step теперь = только `#prompt:execute-task` для `I-1031`.)*

*Последнее обновление: 2026-05-06 (выполнен `D-299` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md`: в `scripts/standards/_registry_continuity_projection.py` materialized helper seam для truthful generated continuity, а `scripts/standards/registry_generator.py` теперь публикует top-level блок `generated_continuity_projection`, per-entry families `owner_artifact_path`, `artifact_family`, `lineage`, `owner_route_status`, `generated_from` и named blockers для `alias_history` / `redirect_history_trace` без synthetic filler; через `registry_generator.py --apply` регенерирован live `genome_registry.json`, где owner-backed lineage сохраняется только по живым carriers `replaces` / `deprecated_by`, mismatch matrix явным образом фиксирует `rebuild / blocker / advisory / manual_escalation`, а drift barriers не расширяются до `examples-validation-and-consumer-rollout`; bounded preflight-sync fix обновил scope `README.md` и module docstring в `tests/unit/standards/test_registry_generator_json.py`, targeted proof `tests/unit/standards/test_registry_generator_json.py` — `10/10` PASSED. `I-1030`, `I-1031`, `D-300`, `I-1034/D-302`, dashboard/runtime и пятый owner `DEV_TZ` не открывались, поэтому ближайший допустимый owner-step теперь = только `#prompt:execute-task` для `I-1030`.)*

*Последнее обновление: 2026-05-06 (выполнен `I-1033` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md`: создан immutable navigation T0 baseline `.benchmarks/baselines/owner-artifact-derived-json-generation-and-continuity-navigation-t0-baseline/baseline_snapshot.json` с `baseline_state = pristine`, `snapshot_taken_before = D-297`, `status = captured-i1033`, девятью compare-ready route traces и `.md-only` contract (`total_opened_json_count = 0`, `total_generated_as_owner_violation_count = 0`, `owner_route_completion_ratio = 1.0`, `route_back_confirmed_count = 9`, `total_contamination_events = 0`); добавлен family-local proof `tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1033.py` (`6/6` PASSED); baseline gate `D-301 -> I-1032 -> I-1033` закрыт, поэтому ближайший допустимый owner-step теперь = только `#prompt:execute-task` для `D-297`, а measurement-lane ждёт external closure `D-300` перед `I-1034`.)*

*Последнее обновление: 2026-05-05 (выполнен `I-1032` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md`: создан immutable semantic T0 baseline `.benchmarks/baselines/owner-artifact-derived-json-generation-and-continuity-semantic-t0-baseline/baseline_snapshot.json` с `baseline_state = pristine`, `snapshot_taken_before = D-297`, eleven-scenario T0 packet и explicit primary metrics для generated contour (`generated_artifact_inventory_count = 1`, `aggregate_first_contract_compliance_pct = 100.0`, `truthful_missing_family_count = 2`, `manual_ambiguity_case_count = 2`, `contamination_events = 0`); добавлен family-local proof `tests/unit/scripts/benchmarks/owner_artifact_derived_json_generation_and_continuity/test_i1032.py` (`6/6` PASSED); owner execution `D-297` по-прежнему не authorizes direct start и остаётся заблокированным до git-фиксации `I-1033`, а ближайший честный measurement-step теперь = только `#prompt:execute-task` для `I-1033`.)*

*Последнее обновление: 2026-05-05 (для planning-only пакета `D-297..D-300 + I-1030..I-1031` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md` выполнен строгий pre-execution `plan-review` и materialized sibling `PRR`: owner `DEV_TZ #3` подтверждён как exact third owner contour для generated-layer materialization без scope drift, без подмены owner truth и без открытия `DEV_TZ #4/#5`, но execution verdict удержан как `APPROVED_PENDING_MEASUREMENT_GATE`; direct start `D-297` по-прежнему запрещён до выполнения и git-фиксации `D-301 -> I-1032 -> I-1033`, а так как `D-301` уже выполнен и закоммичен, ближайший честный ход остаётся на measurement-lane как `#prompt:execute-task` для `I-1032`, затем `I-1033`, а не как прямой owner execution.)*

*Последнее обновление: 2026-05-05 (выполнен `D-301` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md`: зарегистрированы `.aife/measurement/families/owner_artifact_derived_json_generation_and_continuity/corpus_descriptor.json` и `.aife/measurement/catalog/owner_artifact_derived_json_generation_and_continuity.scenario_catalog.json` с одиннадцатью scenario groups и tri-phase grammar `T0-MD / T1-MD / T1-JSON`, обновлены `.aife/measurement/families/family_taxonomy.json` и `.aife/measurement/publication/index.json`, а stale status wrapper-а `DEV_TZ #2` честно переведён в `pilot-closed`; owner `DEV_TZ #3` по-прежнему не authorizes direct execution, поэтому `D-297` остаётся заблокированным до git-фиксации `I-1032 -> I-1033`, а ближайший честный measurement-step теперь = только `#prompt:execute-task` для `I-1032`.)*

*Последнее обновление: 2026-05-05 (для planning-only пакета `D-301..D-302 + I-1032..I-1034` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-owner-derived-json-generation-and-continuity_2026-05-05.md` выполнен строгий `plan-review` и materialized sibling `PRR`: measurement-side wrapper вокруг `DEV_TZ #3` подтверждён как approved side-lane contour с жёстким gate `D-301 -> I-1032 -> I-1033` до старта `D-297`; embedding measurement внутрь owner `DEV_TZ #3` отклонён, reuse baseline wrapper-а `DEV_TZ #2` отклонён, а post-factum-only measurement заранее понижен до `diagnostic-only`. Так как `D-301` уже закрыт и закоммичен, immediate measurement-lane step теперь ограничен только `#prompt:execute-task` для `I-1032`, тогда как owner-lane после отдельного owner-review уже удержан в состоянии `APPROVED_PENDING_MEASUREMENT_GATE`.)*

*Последнее обновление: 2026-05-05 (импортирован planning-only пакет `D-297..D-300 + I-1030..I-1031` из `DEV_TZ_owner-artifact-semantic-normalization_owner-derived-json-generation-and-continuity_2026-05-05.md`: materialized `DEV_TZ #3` строго для generated-layer contour — `generated JSON`, generator seam, `owner -> registries -> generated` sync, continuity mapping, owner/generated mismatch handling, drift barriers и sector validators/gates; `examples-validation-and-consumer-rollout`, dashboard/runtime, optional migration, per-artifact JSON fleet и пятый owner `DEV_TZ` сознательно оставлены вне области. Owner `DEV_TZ #3` уже прошёл `plan-review`, но owner execution `D-297` остаётся заблокированным до завершения и git-фиксации measurement gate: `D-301 -> I-1032 -> I-1033`.)*

*Последнее обновление: 2026-05-05 (выполнен `D-296` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md`: создан companion publication package `.aife/measurement/publication/owner-artifact-existing-corpus-normalization-pilot-package.json`, обновлён `.aife/measurement/publication/index.json`, текущий measurement wrapper переведён в archived/closure semantics, а scope `README.md` и canonical backlog синхронизированы без переписывания T0 baselines `I-1027/I-1028`, T1 result и compare package `I-1029`; dashboard/runtime, `DEV_TZ #3/#4` execution и пятый owner `DEV_TZ` не открывались, а owner `DEV_TZ #3` теперь уже прошёл `plan-review`, но owner execution `D-297` остаётся заблокированным до `D-301 -> I-1032 -> I-1033`.)*

*Последнее обновление: 2026-05-04 (выполнен `D-293` из `DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md`: создан execution-артефакт `docs/98-Reviews/research/2026-04/owner-artifact-semantic-normalization/OWNER_CORPUS_NORMALIZATION_REGISTRY_SYNC_D293_2026-05-04.md`, который фиксирует bounded follower-side sync по `12` поверхностям из матрицы `D-291`, исправляет только drift в агрегатной статистике `genome/registries/STANDARDS_REGISTRY.md` и three-file companion layer (`genome/standards/README.md`, `genome/standards/doc/README.md`, `genome/standards/async/README.md`), подтверждает truthful no-change для `ADR_REGISTRY.md`, `CONTRACTS_REGISTRY.md`, `genome_registry.json`, `genome/adr/README.md`, `docs/99-ADR/README.md`, `genome/standards/governance/README.md` и guard-only owner cases `D-A1`, не меняет `genome/standards/**`, `genome/adr/**`, `genome/contracts/**`, `.aife/measurement/**` и `.benchmarks/**`; дефицит для `I-1026` не доказан, а следующий честный шаг — `#prompt:execute-task` для `D-294`.)*

*Последнее обновление: 2026-05-04 (выполнен `D-292` из `DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md`: создан execution-артефакт `docs/98-Reviews/research/2026-04/owner-artifact-semantic-normalization/OWNER_CORPUS_NORMALIZATION_EXECUTION_D292_2026-05-04.md`, который фиксирует ограниченную перепроверку `74` прямых owner-носителей из матрицы `D-291`, подтверждает `71` случая `D-B1` на owner-backed `id`, сохраняет `3` живых continuity-carrier случая `D-C1`, не добавляет synthetic `semantic_id` / `alias_history` / `redirect_history_trace` и не вносит допустимых правок в `genome/standards/**`, `genome/adr/**`, `genome/contracts/**`; `D-A1` guard-поля оставлены без правок до `D-293`, owner-корпус, `genome/registries/**`, `genome_registry.json`, `.aife/measurement/**` и `.benchmarks/**` не менялись; следующий честный шаг — `#prompt:execute-task` для `D-293`.)*

*Последнее обновление: 2026-05-04 (выполнен `D-291` из `DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md`: создан execution-артефакт `docs/98-Reviews/research/2026-04/owner-artifact-semantic-normalization/OWNER_CORPUS_NORMALIZATION_DISPOSITION_D291_2026-05-04.md`, который переводит inventory `D-290` в bounded matrix (`74` прямых owner-носителя -> `D-292`, `12` registry / companion / mirror-followers -> `D-293`), materialize-ит `named-exclusion` для `NR-4` / `NR-5`, не открывает downstream handoff к `DEV_TZ #3/#4` и оставляет `I-1026 = not-needed-yet`; owner-корпус, `genome/registries/**`, `genome_registry.json`, `.aife/measurement/**` и `.benchmarks/**` не менялись; следующий честный шаг — `#prompt:execute-task` для `D-292`.)*

*Последнее обновление: 2026-05-04 (выполнен `I-1028` из `DEV_TZ_owner-artifact-semantic-normalization_measurement-existing-owner-corpus-normalization_2026-05-03.md`: materialized navigation T0 baseline `.benchmarks/baselines/owner-artifact-existing-corpus-normalization-navigation-t0-baseline/baseline_snapshot.json` и family-local proof `tests/unit/scripts/benchmarks/owner_artifact_existing_corpus_normalization/test_i1028.py`; gate перед `D-290` собран полностью (`D-295`, `I-1027`, `I-1028`), historical pilot evidence `owner-artifact-publication` не тронуто, `I-1029/D-296` и owner execution `D-290..D-294` ещё не выполнялись; следующий честный шаг — `#prompt:execute-task` для `D-290`.)*

*Последнее обновление: 2026-05-04 (импортирован пакет только для планирования `D-290..D-294 + I-1026` из `DEV_TZ_owner-artifact-semantic-normalization_existing-owner-corpus-normalization-and-migration_2026-05-03.md`: оформлен `DEV_TZ #2` для нормализации существующего owner-корпуса под уже опубликованный закон первой публикации; следующий честный шаг — `#prompt:plan-review` для `DEV_TZ #2` и отдельного measurement `DEV_TZ` с T0 baseline; owner-корпус, `.aife/measurement/**`, `.benchmarks/**`, `DEV_TZ #3/#4` и пятый owner `DEV_TZ` не запускались.)*

*Последнее обновление: 2026-05-03 (D-289 Done: materialized `.aife/measurement/publication/owner-artifact-publication-pilot-package.json`; обновлён `.aife/measurement/publication/index.json` с pilot package entry; measurement-pilot DEV_TZ переведён в closure-state без открытия `DEV_TZ #2..#4`, dashboard input/runtime, optional migration и runtime/performance corpus; backlog-связка `D-288/I-1023/I-1025/I-1024/D-289` синхронизирована в `Done`.)*

*Последнее обновление: 2026-05-03 (выполнен `D-284` из `DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md`: `DEV_TZ #1` закрыт терминально, строки `D-282/D-283/I-1009/D-284` синхронизированы в `Done`, scope control-plane и measurement-wrapper обновлены без открытия `DEV_TZ #3/#4`; следующий ход разделён по двум дорожкам: owner-lane — `#prompt:plan-review` для `DEV_TZ #2`, measurement-lane — `#prompt:execute-task` для `I-1024`.)*

*Последнее обновление: 2026-05-03 (I-1024 Done: после D-284 commit `daf77bfb` создан T1 normalized result `.benchmarks/results/owner-artifact-publication-post-tz1/normalized_result.json` и compare package `.benchmarks/compare/owner-artifact-publication-first-compare/compare_package.json`; structural compare показывает T0 `0/4` -> T1 `4/4`, `completeness_pct_delta = +100.0`, contamination clean; navigation compare использует I-1025 route traces, остаётся `compare-ready` при том же GPT-5 Codex / route-step method v1 профиле; structural baseline I-1023 и navigation baseline I-1025 не изменялись; D-289/publication/dashboard/DEV_TZ #2 не выполнялись. Следующий measurement-lane шаг после git-фиксации I-1024 — `#prompt:execute-task` для `D-289`.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1020` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: materialized first normalized evidence layer в `.benchmarks/**` для корпуса `semantic-navigation` — `result_package.json`, `baseline_snapshot.json` и movable indexes `latest.json` / `current-baseline.json`; bounded proof-контур `test_semantic_navigation_regression_package_i1020.py` подтвердил owner-route refs, catalog-only scenario refs, canonical `contamination_packet` и baseline vocabulary (`6 passed`), при этом compare package, dashboard input/runtime, publication contour и `I-1021..I-1022` / `D-287` не выполнялись.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1018` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: materialized Topics 8–9 в `semantic_navigation.scenario_catalog.json` с explicit triage `Artifact Contract -> CONTRACTS_REGISTRY`, `Task Contract -> DEV_TZ/task-card`, `Runtime Contract -> owner-family filtering -> runtime surface`, добавлена contamination matrix (`DEV_TZ-first`, `runtime-first`, `ADR-only`, `README-first`, `graph-first`, `prompt-first`, `unclassified generic contract`), `corpus_descriptor.json` синхронизирован, добавлен узкий proof-контур `test_semantic_navigation_scenarios_i1018.py` (`4 passed`), без запуска measurement runs, без `.benchmarks/**` result artifacts, без baseline snapshots, regression compare, dashboard input/runtime и optional migration; `I-1019..I-1022` и `D-287` не выполнялись.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1017` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: materialized Topics 6–7 в `semantic_navigation.scenario_catalog.json` с ADR registry-first route `AGENTS.md -> ADR_REGISTRY.md -> genome/adr/**`, bounded history redirect recovery (`docs/99-ADR` только как lookup layer) и contamination matrix (`docs99-direct-first`, `README-first`, `graph-first`, `diagram-first`, `prompt-first`, `stale-history-first`); `corpus_descriptor.json` синхронизирован, добавлен узкий proof-контур `test_semantic_navigation_scenarios_i1017.py` (`4 passed`), без запуска measurement runs, без `.benchmarks/**` result artifacts, без baseline snapshots, regression compare, dashboard input/runtime и optional migration; `I-1018..I-1022` и `D-287` не выполнялись.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1016` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: materialized Topics 4–5 в `semantic_navigation.scenario_catalog.json` с AGENTS->STANDARDS_REGISTRY->STD route, route-back к owner standards route и обязательной contamination matrix (`README-first`, `graph-first`, `diagram-first`, `prompt-first`, `direct-file-first`); `corpus_descriptor.json` синхронизирован, добавлен узкий proof-контур `test_semantic_navigation_scenarios_i1016.py` (`4 passed`), без запуска measurement runs, без `.benchmarks/**` result artifacts, без baseline snapshots, regression compare, dashboard input/runtime и optional migration; `I-1017..I-1022` и `D-287` не выполнялись.)*

*Последнее обновление: 2026-05-03 (measurement-pilot-addendum: добавлена I-1025 — navigation-effectiveness T0 baseline между I-1023 и D-282; создан placeholder `.benchmarks/baselines/owner-artifact-publication-navigation-t0-baseline/baseline_snapshot.json`; primary metrics зафиксированы в DEV_TZ (`route_steps_to_owner_truth`, `opened_artifact_count`, `wrong_surface_hits`, `backtrack_count`, `first_route_correct`, `owner_route_completion`, `contamination_events`); wall-clock time помечен advisory-only; structural T0 baseline I-1023 не перезаписан; D-282 запрещён до git-фиксации I-1025; следующий честный шаг — `#prompt:execute-task` для `I-1025`.)*

*Последнее обновление: 2026-05-03 (I-1023 Done: снят T0 baseline для `owner-artifact-publication` до D-282; создан `.benchmarks/baselines/owner-artifact-publication-t0-baseline/baseline_snapshot.json` с `baseline_state = pristine`, `contamination_packet.blocks_regression_interpretation = false`, commit/state до D-282 `0d6d943a2494f7f416dc2d64dc3405cc037df70f`; добавлен целевой proof в существующий `tests/unit/scripts/benchmarks/test_benchmark_storage_boundary.py` (`40 passed`). Следующий шаг после I-1023 — `#prompt:execute-task` для `I-1025` (navigation-effectiveness T0 baseline); D-282 запрещён до git-фиксации I-1025; I-1024 и D-289 остаются `Backlog`, compare/publication/dashboard не создавались.)*

*Последнее обновление: 2026-05-02 (D-288 Done: зарегистрировано семейство `owner-artifact-publication` в `family_taxonomy.json`; materialized companion corpus descriptor и scenario catalog с четырьмя группами для измерения DEV_TZ #1; route-back к DEV_TZ #1 зафиксирован явно; publication/index.json обновлён. Следующий честный шаг — `#prompt:execute-task` для `I-1023` (T0 baseline до D-282); contamination gate сохраняется: D-282 запрещён до git-фиксации I-1023; dashboard, migration, runtime/performance corpus и DEV_TZ #2..#4 не разблокированы.)*

*Последнее обновление: 2026-05-02 (выполнен `D-287` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: проверены статусы I-1014..I-1022 (Done), цепочка descriptor → catalog → normalized result → baseline → compare → publication подтверждена полностью, итог регрессии — `regression-pass` / `stable`; dashboard UI/runtime, optional migration и runtime/performance corpus не разблокированы автоматически.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1015` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: в `semantic_navigation.scenario_catalog.json` materialized Topics 1–2 как AGENTS-first сценарии (7 классов вопросов) и contamination matrix (`README-first`, `graph-first`, `diagram-first`, `prompt-first`, `history-first`, `derived layer as fake owner truth`) с route-back к `AGENTS.md`; `corpus_descriptor.json` синхронизирован, добавлен узкий proof-контур `test_semantic_navigation_scenarios_i1015.py` (`4 passed`) без запуска измерений, без `.benchmarks/**`, без dashboard/result packages, regression compare и optional migration; `I-1016..I-1022` и `D-287` не выполнялись.)*

*Последнее обновление: 2026-05-01 (выполнен `I-1014` из `DEV_TZ_semantic-navigation-benchmark-and-workspace-effectiveness_wave-7-semantic-navigation-corpus-and-regression-rollout_2026-04-30.md`: материализованы первый corpus descriptor `semantic-navigation`, каталог planned scenario identity, schema/publication extension и узкий proof-контур без запуска измерений, без `.benchmarks/**`, без dashboard/result packages, без optional migration и без изменения `I-1015..I-1022` или `D-287`.)*

*Последнее обновление: 2026-04-24 (импортирован пакет планирования `D-282..D-284 + I-1009` из `DEV_TZ_owner-artifact-semantic-normalization_owner-canon-publication-and-first-publication-law_2026-04-24.md`: первый `DEV_TZ` программы `owner-artifact-semantic-normalization` оформлен как отдельный ограниченный пакет для закона обязательной первой публикации owner-артефакта, companion workflow-документа и правдивой нормализации `docs/85-Operations/**`, узкого validator-контура и терминального закрытия самого пакета; все четыре задачи добавлены в backlog со статусом `Backlog`, а следующий честный шаг удержан только как `#prompt:plan-review` для этого пакета, без запуска исполнения и без преждевременного перехода к `DEV_TZ-2..4`.)*

*Последнее обновление: 2026-04-22 (закрыт пакет исполнения `TZ-2` / `svg-json-manifest-generator-substrate`: задачи `D-263..D-267` переведены в `Done`, текущий `DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-2-svg-json-manifest-generator-substrate_2026-04-22.md` архивирован, canonical backlog и внутренний backlog-block синхронизированы, proof contour подтверждён через real multi-family export run, `check_backlog.py`, `validate_tz_backlog_sync.py`, targeted `pytest` и `pre_commit`; root-sync residue по `README.md` / `PROGRAM_MAP_*` честно сохранён как неблокирующий остаток, а следующий допустимый шаг явно ограничен только `TZ-3`.)*

*Последнее обновление: 2026-04-23 (закрыт пакет исполнения `TZ-5` / `owner-publication-and-prompt-workflow-integration`: задачи `D-278..D-281` переведены в `Done`, `STD-DOC-DIAGRAMS-001` получил ограниченный owner-side порог обязательности диаграммы для live contour и правило consumer-layer `raise requirement + route-back`, prompt/workflow surfaces синхронизированы под owner-backed corpus, `.github/prompts/README.md` и `scripts/validators/README.md` теперь явно различают `owner publication -> prompt consumers -> execution automation`, `TZ-4` удержан как единственный upstream gate, labels `TZ-4/V1` и `TZ-4/V2` закреплены как stale residue, а repo-wide `blocking` / `staged` rollout, новые `ADR` / `CONTRACT` и любые дальнейшие owner-level шаги честно оставлены вне области.)*

*Последнее обновление: 2026-04-22 (импортирован planning-only пакет `D-273..D-277` из `DEV_TZ_runtime-diagram-substrate-and-agent-readable-exports_tz-4-freshness-validator-and-rollout_2026-04-22.md`: `TZ-4` оформлен как один bounded `DEV_TZ` для точной матрицы сигналов, расширения `V1` на шесть семейств, materialization `V2` для корневого `diagram JSON` и фиксации честного режима `local-strict / advisory`; repo-wide `blocking` или `staged` rollout, prompt/workflow automation и owner-level publication сознательно оставлены вне области, а следующий bounded пакет после `TZ-4` зафиксирован только как `TZ-5`.)*

*Последнее обновление: 2026-04-22 (импортированы planning-only пакеты `D-259..D-272` из трёх bounded `DEV_TZ` программы `runtime-diagram-substrate-and-agent-readable-exports`: `TZ-1` оформляет порог обязательности и раскатку диаграммных исходников, `TZ-2` — генераторный слой `SVG + manifest`, `TZ-3` — корневой `diagram JSON` с `owner_bridge`; все задачи добавлены в backlog со статусом `Backlog`, а исполнение пакетов ещё не запускалось. Точный downstream-порядок удержан как `TZ-1 -> TZ-2 -> TZ-3 -> TZ-4 -> TZ-5`, без раннего unlock `TZ-4/V2` или `TZ-5`.)*

*Последнее обновление: 2026-04-22 (импортирован planning-only пакет `D-253..D-258` из `DEV_TZ_diagram-markdown-generator-contract_2026-04-22.md`: новый ограниченный контур оформляет локальный контракт вокруг уже доказанного пути генератора для `ownership-model/`, локальный структурный контракт `.md`-диаграмм, шов `diagram-export-manifest.json` / валидатора и финальный остаточный вердикт по `STD-DOC-DIAGRAMS-001`; sibling `SVG` placement, общая раскатка `hook` / `CI`, новый `ADR` и общее правило генератора сознательно оставлены вне области, а исполнение пакета ещё не запускалось.)*

*Последнее обновление: 2026-04-21 (закрыт пакет исполнения `TZ-4` / `freshness-validator-enforcement`: задачи `I-1007`, `I-1008` и `D-231` переведены в `Done`; materialized отдельный validator `validate_doc_freshness.py`, узкий hook-runtime `validate-doc-freshness` и control-plane sync, а точный порядок `TZ-1 -> TZ-2 -> TZ-3 -> TZ-4` зафиксирован как исчерпанный без автоматического открытия `TZ-5` или скрытого следующего пакета.)*

*Последнее обновление: 2026-04-21 (для `documentation-substrate-help-diagrams-terminology` точный порядок исполнения по-прежнему удерживается как `TZ-1 -> TZ-2 -> TZ-3 -> TZ-4`, при этом `TZ-1` / `lookup-publication-authority`, `TZ-2` / `status-provenance-materialization` и `TZ-3` / `legacy-sphinx-residue-application` уже закрыты как пакеты `D-222..D-224`, `D-225..D-227` и `D-228..D-230`; следующий допустимый шаг по-прежнему только `TZ-4`, а широкое или преждевременное усиление слоя проверок свежести вне нового пакета не разрешено.)*

*Последнее обновление: 2026-04-21 (импортирован пакет планирования `I-1007..I-1008 + D-231` из `DEV_TZ_documentation-substrate-help-diagrams-terminology_freshness-validator-enforcement_2026-04-21.md`: `TZ-4` оформлен как отдельный узкий пакет для metadata-слоя, который различает предупреждения о старении и блокирующие противоречия только по явным таблицам и секциям возврата; owner-side corpus, широкая проверка prose-части документации и автоматическое расширение escalation сознательно оставлены вне области, а все три задачи добавлены в backlog со статусом `Backlog`.)*

*Последнее обновление: 2026-04-21 (импортирован пакет планирования `D-228..D-230` из `DEV_TZ_documentation-substrate-help-diagrams-terminology_legacy-sphinx-residue-application_2026-04-21.md`: `TZ-3` материализован как отдельный ограниченный контур для применения уже опубликованного закона к `Sphinx`-остаткам, фантомному маршруту `docs/source` и ближайшему навигационному/управляющему слою; `scripts/metadata/**`, широкое усиление слоя валидаторов и ранний переход к `TZ-4` сознательно оставлены вне области, а все три задачи добавлены в backlog со статусом `Backlog`.)*

*Последнее обновление: 2026-04-14 (закрыт `D-200` — опубликован downstream execution contract Wave 1 -> Waves 2-3; материализован terminal closure для диапазона `D-196..D-220 + I-1004..I-1006`; root control-plane программы переведён в `archived/completed` semantics.)*

*Последнее обновление: 2026-04-14 (закрыт `D-199` — выполнено доказательство закрытия Wave 1: все 6 поверхностей верифицированы (чисто), класс shadow-authority подтверждён устранённым по всем поверхностям, управляющий слой программы (четыре файла) синхронизирован с execution closure; downstream-остатки Topics 8/10/11 явно именованы; representative scenario proof удержан как downstream readiness issue (D-202); разблокирован D-200.)*

*Последнее обновление: 2026-04-14 (закрыт `I-1006` — зафиксирован терминальный вердикт Wave 1 по CONTRACT partial parity: именованный удержанный остаток (вариант 2 из 3); в `CONTRACTS_REGISTRY.md` добавлен явный раздел «Вердикт Wave 1»; шумовые случаи confirmed not-present; разблокирован `D-199`.)*

*Последнее обновление: 2026-04-14 (закрыт `I-1005` — DRY-функция `_parse_registry_table_rows()` добавлена в `registry_generator.py`; `build_genome_registry_payload()` расширена ключами `adrs`/`contracts`; `genome_registry.json` регенерирован (14 ADR + 1 CONTRACT + 52 STD); `check_markdown_links.py --roots` расширен на `genome/registries` и `docs/99-ADR`; `.pre-commit-config.yaml` + `.aife/hook_registry.yml` files pattern обновлен; 5 unit-тестов PASSED; `pre-commit run --all-files: PASSED` (37 хуков); разблокирован `I-1006`.)*

*Последнее обновление: 2026-04-14 (закрыт `I-1004` — создан subpackage `scripts/validators/adr/` с `validate_adr_registry.py` и `validate_adr_continuity.py`; 8 unit-тестов PASSED; 2 hook admission записи в `.pre-commit-config.yaml` + `.aife/hook_registry.yml`; `pre-commit run --all-files: PASSED`; разблокирован `I-1005`.)*

*Последнее обновление: 2026-04-14 (закрыт `D-198` — понижены все 12 основных legacy ADR-файлов `docs/99-ADR/ADR-001..ADR-012` и 2 addendum-файла до `doc_type: redirect` с `canonical_target`; тело основных файлов сведено к banner + §Роль файла + §Историческое резюме + §Куда читать дальше; emoji убраны; `README.md` и canonical `genome/adr/**` не изменялись; `pre-commit run --all-files: PASSED`; разблокирован `I-1004`.)*

*Последнее обновление: 2026-04-14 (закрыт `D-197` — верификация-прохождение: все 9 целевых поверхностей `prompt/include` и hook-trail проверены на чисто зеркальную семантику везде через grep — ни одна не публикует конкурирующего закона маршрута и не присваивает себе полномочие первого чтения поверх `AGENTS.md`; правок исходников не потребовалось; разблокирован `D-198`.)*

*Последнее обновление: 2026-04-14 (закрыт `D-196` — удалена прямая гиперссылка `[genome/adr/README.md]` из навигационного bullet в `AGENTS.md`; семейство `ADR` теперь имеет единственный маршрут первого чтения через `ADR_REGISTRY.md` во всех полномочных носителях маршрута владельца; разблокирован `D-197`.)*

*Последнее обновление: 2026-04-14 (закрыт `D-205` — синхронизированы control-plane surfaces программы `post-closure-enforcement-and-runtime-resolution`: PROGRAM_MAP обновлён (D-202..D-204 явно Done), INVESTIGATION_QUEUE содержит честный execution status, LOGICAL_DRIFT_REGISTER пополнен записью `wave-2-execution-package-d202-d204-closure-sync`; все 5 consumer surfaces проверены — stale wording отсутствует, редактирование не потребовалось; пакет Wave 2 `D-201..D-205` полностью закрыт.)*

*Последнее обновление: 2026-04-13 (закрыт `D-203` — опубликован `ADR-GRAPH-SUBSTRATE-001` как canonical owner-backed carrier для knowledge-navigation substrate: 3 класса A/B/C, 5-ступенчатая gate-модель, 6 швов → 4 routing-семейства; derived-only / owner-first law закреплены как обязательные ограничения; concrete technology оставлен downstream; разблокированы D-204.)*

*Последнее обновление: 2026-04-15 (импортированы задачи `D-206..D-208` волны 4 external-consumer-sweep из `DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-4-external-consumer-sweep_2026-04-15.md`: нормализация голых числовых ADR-ID в пяти внешних потребителях после закрытия D-202; пакет добавлен в backlog со статусом `Backlog`, исполнение не запускалось.)*

*Последнее обновление: 2026-04-13 (материализован planning-only execution package `D-202..D-205` для второй волны `post-closure-enforcement-and-runtime-resolution`: после уже закрытого owner-publication contour `D-201` создан отдельный bounded `DEV_TZ` для route-sensitive change-layer fix `D-202`, отдельный owner-side substrate contour `D-203`, policy-basis contour `D-204` для freshness / benchmark / promotion и final control-plane / consumer sync contour `D-205`; пакет зафиксирован как готовый к `plan-review`, но исполнение ещё не запускалось.)*

*Последнее обновление: 2026-04-13 (импортирован и сразу закрыт ограничённый контур публикации у владельца `D-201` из `DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-2-std-routing-law-materialization_2026-04-13.md`: опубликован `STD-GOVERNANCE-ROUTING-001` как основной носитель повторяемого закона маршрутизации и публикации, синхронизированы `STANDARDS_REGISTRY.md`, `genome_registry.json` и индекс набора governance-стандартов, а вопрос о последующей топологии `DEV_TZ` сознательно оставлен в состоянии ожидания без открытия общего плана исполнения второй волны.)*

*Последнее обновление: 2026-04-12 (импортирован wave-блок `D-196..D-200` + `I-1004..I-1006` из `DEV_TZ_post-closure-enforcement-and-runtime-resolution_wave-1-owner-route-enforcement-and-shadow-authority-control_2026-04-12.md`: оформлен один корневой `DEV_TZ` строго для Wave 1, область ограничена исправлением `owner-route` / `shadow-authority`, включает понижение корпуса `legacy ADR continuity`, инфраструктурный контур валидаторов/экспорта/покрытия ссылок, ограничённое решение для `CONTRACT partial parity` и отдельный downstream execution contract; Wave 3 используется только как порядок `Topic 9 -> Topic 8 -> Topic 10 -> Topic 11`, а решения Wave 2 по runtime/substrate и корневое финальное закрытие программы сознательно оставлены вне области.)*

*Последнее обновление: 2026-04-11 (remediation contour `D-189..D-195` полностью закрыт: `D-189..D-194` остались `Done` как route/JSON/generator/docs/research/narrative cleanup, а `D-195` завершён после повторного `registry_generator.py --check`, verification-only reread/grep по `.github/prompts/**`, `.pre-commit-config.yaml`, `.aife/hook_registry.yml`, успешных `python scripts/check_backlog.py`, `python scripts/validators/validate_tz_backlog_sync.py` и repo-wide `python -m pre_commit run --all-files`; scope по-прежнему жёстко ограничен active routing/docs/scripts/research surfaces после удаления `GEN/CHR` layer, без reopening wave-модели и без historical repo-wide rewrite.)*

*Последнее обновление: 2026-04-10 (задача `D-188` закрыта как финальный `closure-proof` для `TZ-6`: активный `DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md` переведён в `status: archived`, строка `D-188` и mirror import block синхронизированы под `Done`, а финальный пакет `D = TZ-6` теперь читается как уже полностью закрытая шестиконтурная база без седьмого `DEV_TZ`; корневой управляющий контур подтверждён без нового status-drift, снаружи basis честно остаются только `RL-1..RL-4`, а машиночитаемый final proof materialized через D-136 capture route `.aife/test-outputs/pre-commit/closure-proof/d-188/tz6-final-closure-proof/` для repo-wide `pre-push` gate.)*

*Последнее обновление: 2026-04-10 (задача `D-187` закрыта как ограниченная синхронизация корневого управляющего контура для пакета `D`: `docs/98-Reviews/research/2026-04/genome-driven-knowledge-navigation-foundation/README.md`, `PROGRAM_MAP_*`, `INVESTIGATION_QUEUE_*` и `LOGICAL_DRIFT_REGISTER_*` теперь явно фиксируют, что `Пакет D = TZ-6` остаётся единым финальным пакетом, уже внутренне поглощает материализованные `OU-6`, `CU-7`, `CU-5` и ограниченную синхронизацию корневого управляющего контура, не создаёт седьмой `DEV_TZ`, оставляет downstream только `D-188`, а честный остаточный набор ограничен `RL-1..RL-4`; исторические drift/evidence записи не переписывались задним числом, а синхронизированы через ограниченные статусные уточнения, после чего активный `DEV_TZ` и канонический backlog выровнены под `D-187 = Done`.)*

*Последнее обновление: 2026-04-10 (задача `D-186` закрыта как переиспользуемый сопроводительный контур проверки `CU-5` для `TZ-6`: новый include `.github/prompts/includes/reusable-verification-companion.md` материализует mixed model `локальный Контур проверки + общий companion`, `.github/prompts/includes/closure-gates.md` и `tz-readiness-map.md` теперь явно возвращают reusable verification reading к этому include, `.github/prompts/README.md`, `.github/prompts/quality/README.md`, `.github/prompts/quality/pre-commit-check.prompt.md` и `scripts/ci/README.md` синхронизированы как производные consumer surfaces, а D-136 capture route назван обязательным только для устойчивых machine-readable proof claims; операторский contour `CU-7` не переоткрывался, bounded root control-plane sync и final closure `TZ-6` сознательно оставлены downstream `D-187..D-188` / `RL-1..RL-2`, а активный `DEV_TZ` и канонический backlog синхронизированы под `D-186 = Done`.)*

*Последнее обновление: 2026-04-10 (задача `D-185` закрыта как ограниченный операторский сопроводительный слой `CU-7` для `TZ-6`: `scripts/validators/README.md` и `scripts/ci/README.md` теперь прямо возвращают operator/support чтение validator/CI/sync barriers к `STD-GOVERNANCE-HOOKS-001` appendix `OU-6`, различают `commit-proof`, `closure-proof`, `manual/audit` и `review-only` без owner drift, удерживают `.pre-commit-config.yaml` как единственный runtime-dispatch owner и называют D-136 capture route обязательным только для устойчивых machine-readable validation/closure claims; `CU-5`, bounded root control-plane sync, threshold calibration / promotion и runtime graph backend / storage / query сознательно оставлены downstream `D-186..D-188` / `RL-1..RL-2`, а активный `DEV_TZ` и канонический backlog синхронизированы под `D-185 = Done`.)*

*Последнее обновление: 2026-04-10 (задача `D-184` закрыта как ограничённый контракт enforcement/sync на стороне владельца для `TZ-6`: `STD-GOVERNANCE-HOOKS-001` теперь публикует приложение `OU-6` как единственный смысловой носитель для разведения вердиктов `blocking-ready now / advisory-first / review-only`, разведения контуров доказательства и ограниченной дисциплины синхронизации финального пакета `D`, при этом `.pre-commit-config.yaml` сохранён как единственный runtime-dispatch owner, `.aife/hook_registry.yml` удержан как companion record, а validators / README / prompt / metrics layers не получили owner authority; активный `DEV_TZ` и канонический backlog синхронизированы под `D-184 = Done`, тогда как `CU-7`, `CU-5`, bounded root control-plane sync, threshold calibration / promotion и runtime graph backend / storage / query сознательно оставлены downstream `D-185..D-188` / `RL-1..RL-2`.)*

*Последнее обновление: 2026-04-10 (задача `D-183` закрыта как truthful final closure-proof `TZ-5`: `docs/10-Architecture/general/knowledge_navigation_graph.md` больше не держит `D-183` как следующий шаг и явно подтверждает owner-backed graph contract как единственный смысловой центр, а `CU-3` / `CU-4` — как раздельные строго производные companion layers; `DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md` переведён в `status: archived`, mirror import block и канонический backlog синхронизированы под `D-183 = Done`, а `TZ-6` теперь читается только как downstream contour после полного closure `TZ-5` без переоткрытия diagram/help surfaces, README mirror layer или runtime graph decisions.)*

*Последнее обновление: 2026-04-10 (задача `D-182` закрыта как bounded provenance-safe слой terminal-help для `TZ-5`: `scripts/README.md` и `.github/prompts/README.md` теперь вместе публикуют `CU-4` как раздельный от `CU-3` производный слой доставки и помощи с явными режимами `lookup / query / read / trace`, уровнями чтения `summary / deep`, offline-first правилом и возвратом к owner surfaces, а `docs/10-Architecture/general/knowledge_navigation_graph.md` получил только минимальную route-back синхронизацию статуса materialized terminal-help без переопределения graph contract и без поглощения `D-183`, enforcement/verification или runtime CLI design.)*

*Последнее обновление: 2026-04-10 (задача `D-181` закрыта как bounded companion-only слой диаграмм для `TZ-5`: `docs/10-Architecture/diagrams/README.md` теперь явно публикует роль каталога как ограниченного семейного индекса, порядок чтения после `knowledge_navigation_graph.md`, набор живых поверхностей `ownership-model/**`, дисциплину визуальных якорей и сознательно удерживает вне области terminal-help, enforcement и решения по `renderer` / `storage` / `substrate`; пять активных диаграмм получили явные `authority_reference` / `companion`, секции возврата к владельцу и больше не читаются как теневой источник полномочий, а `docs/10-Architecture/README.md`, `docs/10-Architecture/general/README.md`, `docs/10-Architecture/general/architecture.md`, `DEV_TZ` и канонический backlog синхронизированы под `D-181 = Done` без поглощения `D-182`, `D-183` или repo-wide cleanup инвентаря диаграмм.)*

*Последнее обновление: 2026-04-09 (задача `D-180` закрыта как первая ограниченная производная графовая поверхность чтения для `TZ-5`: `docs/10-Architecture/general/knowledge_navigation_graph.md` теперь поверх уже опубликованного контракта владельца явно публикует входные законы из `TZ-3` и `TZ-4`, ограниченный протокол чтения, разрешённые классы отношений и обязательный возврат к живому артефакту владельца, а `docs/10-Architecture/general/README.md`, `docs/10-Architecture/README.md`, `docs/10-Architecture/general/architecture.md`, `DEV_TZ` и канонический backlog синхронизированы как зеркальные или обзорные потребители без дрейфа владения; слои diagram/help, обязательный корпус `GEN-*`, контур принудительных проверок и решения по `backend` / `storage` / `query` / `serialization` сознательно оставлены вне области.)*

*Последнее обновление: 2026-04-09 (задача `D-179` закрыта как вводный контракт владельца для `TZ-5`: новый `docs/10-Architecture/general/knowledge_navigation_graph.md` теперь публикует единый контракт `semantic_id` / `node-key`, базу идентичности, подтверждённую живым артефактом владельца, отдельные границы `code`, `diagram`, help/runtime и `BSP`, а `docs/10-Architecture/general/README.md`, `docs/10-Architecture/README.md`, `DEV_TZ` и канонический backlog синхронизированы под `D-179 = Done`; производная графовая поверхность чтения, слои diagram/help, `GEN-*`, решения по `backend` / `storage` / `query` / `serialization` и downstream-контуры `D-180..D-183` сознательно оставлены вне области.)*

*Последнее обновление: 2026-04-09 (задача `D-177` закрыта как bounded mirror-only consumer sync для `TZ-4`: `genome/registries/STANDARDS_REGISTRY.md`, `ADR_REGISTRY.md` и `CONTRACTS_REGISTRY.md` теперь явно возвращают чтение relation semantics к `STD-DOC-METADATA-001.md` и метаданным владеющих артефактов, сохраняя за собой только route/status/index authority, а `docs/99-ADR/README.md` прямо фиксирует legacy mapping rows как lookup/redirect continuity layer без самостоятельной `lineage`-семантики; backlog и mirror-block синхронизированы под `D-177 = Done`, при этом vocabulary owner standard, schema/validator substrate, bounded seed corpus, graph/help rollout и финальный closure `D-178` сознательно оставлены вне области.)*

*Последнее обновление: 2026-04-09 (задача `D-176` закрыта как bounded cross-family seed corpus для `TZ-4`: `INDEX-GENOME-STANDARDS-ASYNC -> STD-ARCH-ASYNC-001` материализует живой non-ADR lineage-case, `ADR-INITIALIZER-CORE-002 -> ADR-011-ADD-001` закрепляет canonical ADR lineage-case, `CONTRACT-DOC-PRR-001` получил `authority_reference` к `STD-GOVERNANCE-CONTRACT-001`, а `docs/10-Architecture/general/architecture.md` вместе с `docs/10-Architecture/diagrams/ownership-model/file-to-role-map.md` материализуют ограниченный `authority_reference` / `companion`-контур без превращения документа и диаграммы в owner-layer; targeted unit-proof для `tests/unit/validators/test_validate_markdown_metadata.py`, строгая проверка markdown metadata, backlog и mirror-block синхронизированы под `D-176 = Done`, при этом registry mirror sync, финальный closure `TZ-4` и задачи `D-177..D-178` сознательно оставлены downstream.)*

*Последнее обновление: 2026-04-09 (задача `D-175` закрыта как bounded machine-support contour для `TZ-4`: `.aife/schemas/markdown_metadata.schema.json` и `scripts/metadata/validate_markdown_metadata.py` теперь поддерживают canonical relation carriers `parent`, `authority_reference`, `companion`, `alias_history`, `redirect_history_trace`, а также `path/id` resolution для relation targets; `related` больше не может маскировать structured semantics, unit-proof добавлен в `tests/unit/validators/test_validate_markdown_metadata.py`, backlog и mirror-block синхронизированы под `D-175 = Done`, при этом seed corpus, registry mirror sync, graph/help rollout и задачи `D-176..D-178` сознательно оставлены downstream.)*

*Последнее обновление: 2026-04-09 (задача `D-168` закрыта как truthful whole-contour closure-proof `TZ-2`: последний in-scope active legacy first-open residue в `security/security_manager.py` переведён на canonical route `ADR_REGISTRY.md -> genome/adr/security/ADR-SECURITY-CAPABILITIES-001.md`, repo-wide gates `validate_structural_pressure.py --strict`, `python scripts/check_backlog.py`, `python scripts/validators/validate_tz_backlog_sync.py`, `python -m pre_commit run --all-files` и staged `python -m pre_commit run` завершились зелёно, `D-168` синхронизирован как `Done` в canonical backlog и mirror-block, `TZ-2` переведён в `status: archived`, а downstream unlock `TZ-3` / `TZ-4` теперь честно опирается на полное closure всего ADR continuity contour.)*

*Последнее обновление: 2026-04-09 (задача `D-167` закрыта как bounded consumer-side redirect / traceability contour для ADR migration: `AGENTS.md`, `.github/prompts/change-workflow.prompt.md`, root/docs overview surfaces, selected architecture/security/UI docs и `scripts/ci/validate_change_artifacts.py` теперь ведут активные потребительские поверхности к `ADR_REGISTRY.md` и canonical `genome/adr/**`, а `docs/99-ADR/README.md` и все 12 retained standalone legacy ADR получили явные history/lookup/redirect markers и canonical targets; `docs/99-ADR/**` остаётся retrievable continuity layer, но больше не читается как normal owner destination.)*

*Последнее обновление: 2026-04-09 (задача `D-166` закрыта как truthful contour завершения текущего addenda transition: `ADR-010-ADD-001` поглощён в `ADR-UI-WORKSPACE-002`, бывший `ADR-011-ADD-001` повышен до самостоятельного canonical ADR `ADR-INITIALIZER-CORE-002`, owner-side addendum files удалены из `genome/adr/**`, `ADR_REGISTRY.md` / `STD-ARCH-PATTERNS-001` / `STD-TEST-PACKAGE-001` перепривязаны к окончательным owner targets, а `docs/99-ADR/**` нормализован до deprecated lookup/redirect continuity слоя без постоянной canonical ветки `ADDENDUM`.)*

*Последнее обновление: 2026-04-09 (задача `D-165` закрыта как truthful standalone ADR naming/placement migration contour: по audit/mapping matrix все 12 standalone ADR переведены на shared canonical grammar и domain-only placement `genome/adr/<domain-lowercase>/ADR-<DOMAIN>-<QUALIFIER>-<NNN>.md`, legacy owner filenames удалены из `genome/adr/**`, `ADR_REGISTRY.md` / `genome/adr/README.md` / `docs/99-ADR/README.md` синхронизированы под новый owner corpus, а composite buckets `ui-workspace/` и `initializer-core/` retained only for addenda continuity до downstream `D-166`; addenda intentionally не трогались.)*

*Последнее обновление: 2026-04-08 (импортирован backlog-контур `D-184..D-188` из `DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-6-enforcement-sync-gates-and-reusable-verification-contour_2026-04-08.md`: `TZ-6` материализован как финальный пакет `D` строго после `TZ-5`; scope сознательно ограничен owner-side enforcement/sync-gates `OU-6`, bounded operator companion `CU-7`, reusable verification companion `CU-5`, D-136 capture-route discipline и bounded root control-plane sync без седьмого `DEV_TZ`; runtime graph backend / storage / query, threshold calibration / promotion, generic observability redesign и прочие residual directions честно оставлены вне области, чтобы six-contour execution basis закрывалась без reopening `TZ-1..TZ-5`.)*

*Последнее обновление: 2026-04-08 (импортирован backlog-контур `D-179..D-183` из `DEV_TZ_genome-driven-knowledge-navigation-foundation_tz-5-derived-navigation-rollout-and-graph-consumer-layer_2026-04-08.md`: `TZ-5` материализован как ограниченный пакет `C` строго после `TZ-3` и `TZ-4`, с обязательным вводным контрактом темы `9` для `semantic_id` / `node-key` и границ `code/diagram/BSP`, затем — с ограниченной производной графовой поверхностью чтения и раздельными сопроводительными контурами `CU-3` и `CU-4`; решения по runtime backend / storage / query, усиление проверок, закрытие сопроводительного слоя верификации и синхронизация управляющего контура сознательно оставлены вне области, чтобы `TZ-6` стартовал уже на стабильных строго производных границах без повторного пересогласования семантики графового центра.)*

*Последнее обновление: 2026-04-03 (задача `I-996` закрыта как bounded Wave 2 calibration contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_patterns/_evaluator.py` теперь комбинирует bounded Qt source hints (`connect`, `installEventFilter`, parent-child widget init) с уже извлечёнными structural signals и suppress-ит `DPT-002` только для active runtime surfaces, сохраняя advisory-valid shell stub inventory; synthetic/live proof в `tests/unit/validators/drift_patterns/test_evaluator.py` и `test_evaluator_live_calibration.py` подтверждает split `ChartWidget -> no DPT-002`, `SymbolListWidget -> advisory DPT-002`, targeted contour завершился `24 passed`, `0 failed`, расширенный validator contour — `133 passed`, `0 failed`, полный `python -m pytest -q` — `1747 passed`, `0 failed`, а live CLI summary для `--scope ui/layout` подтвердил `SignalCount 21`, `Dpt002Count 12` и residual ровно из 12 advisory-valid shell entities; updated live baseline той же сессии был `Dpt002Count 39`, поэтому фактический delta составил `39 -> 12`, без reopening `I-991..I-995`, `I-997`, `I-998`, runtime UI code или `pyproject.toml`.)*

*Последнее обновление: 2026-04-03 (задача `I-998` закрыта как literal Wave 2 guard contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_patterns/_evaluator.py` теперь распознаёт explicit package `__init__.py` convenience re-export через `_package_init_reexports(...)` и `_is_init_convenience_import_route(...)`, поэтому package-level re-export import больше не считается отдельным duplicate route для `DPT-006`; synthetic proof в `tests/unit/validators/drift_patterns/test_evaluator.py` подтверждает suppression `__init__.py` route и сохранение direct module duplicate route, а live regression в `test_evaluator_live_calibration.py` подтверждает, что `ChartTabManager` остаётся видимым как non-init `DPT-006`; targeted contour завершился `24 passed`, `0 failed`, полный `python -m pytest -q` завершился `1743 passed`, `0 failed`, а live summaries для `--scope ui/layout/workspace` и `--scope ui` остались без delta (`3/1` и `50/4`), что честно фиксирует: обновлённый baseline уже не содержит активных package-level `__init__` imports для этих сигналов, поэтому `I-998` закрылся как preventive guard, не переоткрывая `I-991..I-997`, runtime UI code или `pyproject.toml`.)*

*Последнее обновление: 2026-04-03 (задача `I-997` закрыта как bounded Wave 2 dedup contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_patterns/_evaluator.py` теперь вычищает из `fallback_seam_map` derivative `import-private` crossings, уже принадлежащие import-private drift family `DPT-004`, а targeted/live proof в `tests/unit/validators/drift_patterns/test_evaluator.py` и `test_evaluator_live_calibration.py` подтверждает, что `DockPanelsAdapter` больше не публикует residual `DPT-007`, тогда как независимый `WorkspaceFacade -> _mdi_area` fallback seam сохраняется; targeted contour завершился `21 passed`, `0 failed`, live summary для `--scope ui/layout/workspace` изменился `SignalCount 4 -> 3`, `Dpt007Count 2 -> 1`, `DockPanelsAdapterDpt007 1 -> 0`, а полный `python -m pytest -q` завершился `1740 passed`, `13 skipped`; `I-991..I-996`, `I-998`, runtime UI code и `pyproject.toml` не менялись.)*

*Последнее обновление: 2026-04-03 (задача `I-991` закрыта как bounded scope-isolation contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_model/_extractor.py` сохраняет полный transitive model, но публикует direct seed inventory через `collect_seed_modules(...)`, `scripts/validators/_drift_patterns/_evaluator.py` post-filter'ит готовые сигналы по seed-ownership через owner entity/evidence source, а `scripts/validators/validate_architectural_drift.py` делает `--scope` optional и вводит truthful `scope_semantics` для scoped/full-repo mode; targeted validator contour `tests/unit/validators/drift_model/test_drift_model_types.py + tests/unit/validators/drift_model/test_drift_extractor.py + tests/unit/validators/drift_patterns/test_evaluator.py + tests/unit/validators/drift_patterns/test_evaluator_live_calibration.py + tests/unit/validators/drift_exceptions/test_drift_exceptions.py + tests/unit/validators/drift_cli/test_validate_architectural_drift.py` завершился `37 passed`, `0 failed`, а live CLI summaries подтвердили `ui/layout/dock_panels -> SignalCount 23, OffScopeCount 0`, `core/api -> SignalCount 0, OffScopeCount 0`, `full-repo -> SignalCount 60`, `SetsDistinct=True`; downstream зависимости на прежнее leakage behavior не подтвердились, `I-992..I-995` не переоткрывались, `I-996..I-998`, runtime UI code и `pyproject.toml` не менялись.)*

*Последнее обновление: 2026-04-03 (задача `I-995` закрыта как узкий advisory contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_model/_import_graph.py` отделяет callable public method descriptors от broad public member inventory, `scripts/validators/_drift_model/_entity_classifier.py` materialize-ит effective public method surface по локально разрешимому base chain, а `scripts/validators/_drift_patterns/_config/drift_patterns.yml`, `_pattern_registry.py` и `_evaluator.py` добавляют advisory pattern `DPT-009` с threshold `25`; targeted validator contour `tests/unit/validators/drift_model/test_import_graph.py + tests/unit/validators/drift_model/test_entity_classifier.py + tests/unit/validators/drift_model/test_drift_extractor.py + tests/unit/validators/drift_patterns/test_evaluator.py + tests/unit/validators/drift_patterns/test_evaluator_live_calibration.py + tests/unit/validators/drift_cli/test_validate_architectural_drift.py + tests/unit/validators/drift_fixtures/test_fixture_corpus.py` завершился `31 passed`, `0 failed`, а live CLI summary для `--scope ui/layout/workspace` подтвердил `SignalCount 37 -> 40`, `Dpt009Count 0 -> 3`, новый `DockPanelsManager -> DPT-009` при `effective public method count = 26`, а также truthful hits для `ChartTabManager = 32` и `PanelSplitterWorkspace = 61`; `I-991..I-994`, `I-996..I-998`, runtime UI code и `pyproject.toml` не менялись.)*

*Последнее обновление: 2026-04-03 (задача `I-993` закрыта как узкий live-calibration contour для `Phase 5D Validator Calibration`: `scripts/validators/_drift_model/_import_graph.py` теперь materialize-ит `getattr-private` для annotated method parameters и local collaborator vars, а `scripts/validators/_drift_patterns/_config/drift_patterns.yml` расширяет `DPT-001` на target-group `surface` alongside `authority`, поэтому `WorkspaceFacade -> ChartTabManager._mdi_area` снова попадает в advisory summary как `DPT-001`; targeted validator contour `tests/unit/validators/drift_model/test_import_graph.py + tests/unit/validators/drift_model/test_drift_extractor.py + tests/unit/validators/drift_patterns/test_evaluator.py + tests/unit/validators/drift_patterns/test_evaluator_live_calibration.py + tests/unit/validators/drift_cli/test_validate_architectural_drift.py + tests/unit/validators/drift_fixtures/test_fixture_corpus.py` завершился `27 passed`, `0 failed`, а live CLI summary для `--scope ui/layout/workspace` подтвердил `SignalCount 34 -> 37`, `Dpt001Count 0 -> 1`, `WorkspaceFacadeDpt001 0 -> 1` и advisory `_mdi_area` hit с `blocking=no`; `I-991`, `I-994..I-998` не выполнялись, `evaluator.py` и `pyproject.toml` не менялись.)*

*Последнее обновление: 2026-04-03 (задача `I-994` закрыта как узкий контур проверки корректности классификации для `Phase 5D Validator Calibration`: `scripts/validators/_drift_model/_entity_classifier.py` больше не классифицирует `_`-prefixed Qt classes как `visible-surface`, targeted validator contour `tests/unit/validators/drift_model/test_entity_classifier.py + tests/unit/validators/drift_model/test_drift_extractor.py + tests/unit/validators/drift_patterns/test_evaluator_live_calibration.py` завершился `8 passed`, `0 failed`, а живой замер на scope `ui/layout/workspace + ui/layout/dock_panels` подтвердил `SignalCount 41 -> 34`, `Dpt002Count 37 -> 30`, `_`-prefixed `visible-surface 7 -> 0` и сохранение `BaseDockPanel` как `visible-surface`; `I-991` и `I-993..I-998` не выполнялись, `role_heuristics.yml`, runtime UI code и `pyproject.toml` не менялись.)*

*Последнее обновление: 2026-04-02 (импортирован backlog-контур `D-156..D-159, I-983..I-990` из `DEV_TZ_hook-ecosystem_2026-04-02.md`: сформирован один authoritative execution/governance contract для `hook-ecosystem` строго по consolidated findings, scope ограничен `repo-authoritative hook core`, а runtime overlay / session-state / external state-store / external dispatcher authority явно оставлены вне live owner-layer; волны импорта покрывают foundation/governance, contour/config migration, coverage/output contracts, drift routing + consumer sync, narrow helper reuse и fast `dev-loop` overlay без blanket weakening hooks и без umbrella dispatcher.)*

*Последнее обновление: 2026-04-02 (задача `D-155` закрыта как governance-adjusted final DoD measurement/verdict contour для `Phase 5C Test Contour Remediation`: `DoD-01` теперь зафиксирован как двухметричный proof-contract, где authoritative runtime rerun `python -m pytest tests/integration/ui/workspace/drag_drop -q --no-cov` дал `112 passed, 5 skipped in 139.23s` и проходит threshold `<= 180s`, а coverage-observability rerun `python -m pytest tests/integration/ui/workspace/drag_drop -q` дал `112 passed, 5 skipped in 229.75s` и остаётся informational, non-blocking note из-за `pytest.ini addopts`; итоговый phase verdict = `PASS`. Verification-only audit подтвердил `0` parallel D-129 route bodies, `0` ordinary full-route copies, `0` settle/full-drain calls вне validation, current-tree deltas `hover 20 -> 6`, `L96 4 -> 1`, `perimeter 12 -> 4`, CF-007 `9 -> 4` (`-5`), helper bound `_common_runtime_helpers.py = 241`, governance ratio `1/20 = 0.05`; task status остаётся `Done`, новых governance artifacts не создано.)*

*Последнее обновление: 2026-04-01 (задача `C-129` закрыта как узкий residual follow-up к Phase 5B closure: `ui/layout/workspace/workspace_facade.py` больше не использует private fallback `getattr(..., "_capture_default_layout_state", ...)`, а `DockPanelsManager` получил public owner-authorized seam `capture_default_layout_state()` через `ui/layout/dock_panels/manager/runtime/_dock_snapshot_io.py`; targeted contour `tests/unit/ui/workspace/adapters/test_workspace_facade.py + tests/unit/ui/layout/dock_panels/manager/runtime/lifecycle/test_window_lifecycle_startup.py` завершился `13 passed`, `0 failed`, а advisory rerun `python scripts/validators/validate_architectural_drift.py --scope ui --mode advisory --json` больше не materialize-ит `WorkspaceFacade` / `DPT-007`, оставляя только отдельные `DPT-002`/`DPT-006` signal families вне scope этого residual fix.)*

*Последнее обновление: 2026-04-01 (задача `I-982` закрыта как bounded validator coverage contour: добавлен `tests/unit/validators/test_validate_lint_suppressions.py`, который через monkeypatched staged diff проверяет три canonical verdict-сценария `validate_lint_suppressions.py` — clean path без suppressions, allowed suppression с adjacent `LINT-WAIVER` и blocking suppression без waiver; targeted proof завершился `3 passed`, `0 failed`, production validator не менялся, а blocking folder saturation `tests/unit/validators` честно materialized как explicit waiver `source_task=I-982` вместо broad validator regrouping.)*

*Последнее обновление: 2026-04-01 (задача `C-123` закрыта как bounded stale-workaround removal contour: historical marker `WORKAROUND C-108` удалён из live companion `ui/layout/dock_panels/workspace/runtime/panel_splitter_workspace_panel_ops_mixin.py` после fresh reproduction attempt по former zero-geometry failure mode, regression-proof `test_apply_panel_drop_intent_panel_local_split_survives_zero_live_target_width` materialized в owner-apply suite, targeted contour `test_drop_intents_owner_apply.py + test_main_surface_repeated_inserts.py + test_main_local_regression_runtime.py` завершился `20 passed`, `0 failed`, а `python scripts/validators/validate_tz_backlog_sync.py`, `python scripts/check_backlog.py` и `python -m pre_commit run --all-files` подтвердили truthful closure без marker-only refresh.)*

*Последнее обновление: 2026-04-01 (задача `C-122` закрыта как inventory-only preventive guard после `C-117` без runtime-code churn: reproducible static inventory для `DockPanelsManager` по `__dict__` / `__mro__` зафиксировал `direct public methods = 4` (`attach_central_widget`, `eventFilter`, `initialize`, `initialize_all`) и `effective public methods = 35`, при этом public `property` / `Signal` / Qt meta attrs документированы отдельно как supplemental surface и не входят в class method metric; truthful decision note привязал preventive verdict к effective public surface финального класса, а не к isolated root file, и из-за превышения hard ceiling `25` materialized explicit follow-up `C-128` вместо cosmetic API masking. `python scripts/validators/validate_tz_backlog_sync.py` и `python scripts/check_backlog.py` подтвердили truthful artifact sync.)*

*Последнее обновление: 2026-03-31 (задача `C-127` закрыта как bounded chart-only structural follow-up после honest residual materialization из `C-121`: layout/preset/persistence family вынесена из `ui/layout/chart/chart_widget.py` в существующий `ui/layout/chart/utilities/layout_manager.py`, корневой widget доведён до `593` строк без waiver и без public/runtime drift, chart-root folder saturation не ухудшен, а targeted chart contour `test_chart_widget.py + test_chart_main_canvas_contract.py + test_chart_visibility_axes.py + test_chart_utilities.py + test_chart_layout_mode_integration.py` завершился `41 passed`, `0 failed`; `python scripts/validators/validate_structural_pressure.py --strict` подтвердил снятие giant-file residue для `chart_widget.py`, при этом existing folder-saturation warning `ui/layout/chart | py_files=8 | warn>=8` честно оставлен как отдельный, неисполнявшийся в `C-127` structural debt.)*

*Последнее обновление: 2026-03-31 (задача `C-121` повторно синхронизирована по live repo truth после decomposition-first rerun: warning-zone root modules `ui/layout/main_window.py`, `ui/layout/workspace/drag_drop/drag_payload.py`, `ui/layout/workspace/adapters/dock_panels_adapter.py`, `ui/layout/workspace/graph/workspace_graph.py`, `ui/layout/workspace/persistence/_snapshot_parts.py`, `ui/layout/dock_panels/workspace/panel_splitter_workspace.py` и `ui/layout/dock_panels/workspace/sizing/_splitter_main_surface_layout.py` доведены до `679 / 330 / 685 / 517 / 256 / 511 / 639` строк через bounded companion extraction; adjacent remeasure подтвердил `ui/layout/workspace/topology/zone_tree.py = 626`, а residual warning-level pressure `ui/layout/chart/chart_widget.py = 731` честно вынесен в новый backlog task `C-127`; stale giant-file entries `C-121` удалены из `.aife/structural_pressure_waivers.yml`, closure proof подтверждён через expanded targeted pytest contours (`91 passed` unit + `7 passed` integration) и strict structural validators/backlog sync.)*

*Последнее обновление: 2026-03-31 (задача `C-120` повторно синхронизирована после проверки фактического состояния закрытия: из `ui/layout/dock_panels/panel_drag_gesture_coordinator.py` вынесен приватный вспомогательный модуль `gesture/_drag_runtime_support.py`, размер координатора снижен до `599` строк, итоговые размеры шестифайлового контура заново зафиксированы по актуальным путям (`presentation/controls/...`, `workspace/sizing/...`, `manager/transfer/...`), устаревшие записи kind=`giant_file` для уже закрытого контура удалены из `.aife/structural_pressure_waivers.yml`, а доказательство закрытия подтверждено через `python scripts/validators/validate_structural_pressure.py --strict` и целевой drag/drop контур `30 passed`, `0 failed`.)*

*Последнее обновление: 2026-03-31 (задача `C-119` закрыта как bounded downstream migration contour для Phase 5B UI runtime remediation: `ui/layout/menubar/tools_menu/tools_menu_section.py` удаляет последний section-local wrapper `_bind_action(...)`, systematic proof `tests/unit/ui/layout/menubar/test_menu_bar_unavailable_routing.py` фиксирует triage `0 live-manager connected / 37 unavailable-ready` и zero-residue source markers для target sections `AI/Monitoring/Blockchain/Patterns/Tools`, а targeted contour `action_registry + menubar` завершился `28 passed` без реализации live domain managers и без reopening unified unavailable substrate.)*

*Последнее обновление: 2026-03-30 (задача `I-975` закрыта как ограниченный контур метрик и отчёта для `architectural-drift-validator-calibration`: выполнен один воспроизводимый report-mode capture на approved scope `ui/layout/workspace/` + `ui/layout/dock_panels/`, материализован semantic proof package `tests/unit/validators/drift_calibration/`, опубликован доступный отчёт `EVIDENCE_I-975_ground-truth-metrics_2026-03-30.md` с поэлементной TP/FP/FN-таблицей по corpus `1-10`, high-confidence precision `1.00` и medium-confidence recall `0.33`; threshold miss честно зафиксирован как measured shortfall без heuristic tuning, fixture corpus, exception mechanism, blocking promotion, governance assessment и без поглощения downstream задач `I-976..I-980`.)*

*Последнее обновление: 2026-03-30 (задача `I-974` закрыта как bounded advisory-first calibration contour для `architectural-drift-validator-calibration`: existing CLI `validate_architectural_drift.py` прогнан только на `ui/layout/workspace/` + `ui/layout/dock_panels/`, выполнен один узкий evaluator refinement для module-level `import-private` evidence, после чего rerun подтвердил detectability live corpus items `1-4`, advisory-only disposition `blocking_enabled=False` / `advisory_only=True` и publication retrievable report `EVIDENCE_I-974_advisory-calibration_2026-03-30.md`; runtime remediation, blocking promotion, exception mechanism, fixture corpus и formal precision/recall intentionally untouched.)*

*Последнее обновление: 2026-03-29 (волна `D-151..D-153` закрыта как bounded W3 standard maturity contour для `governance-routing-accessibility`: `STD-ARCH-PATTERNS-001` получил verifiable `Enforcement Checklist (manual)`, explicit `Scope & Authority` declaration и reverse-routing links к `AGENTS.md`, `.github/copilot-instructions.md`, `CLAUDE.md`, `.github/prompts/includes/canonical-context.md`; после закрытия всех `D-140..D-153` consolidated audit и `DEV_TZ_governance-routing-accessibility_2026-03-29.md` переведены в `status: archived`, а `python -m pre_commit run --all-files` служит final Phase 4 closure proof.)*

*Последнее обновление: 2026-03-29 (волна `D-144..D-150` закрыта как bounded W2 routing refinement для `governance-routing-accessibility`: `architecture.md` получил paired truth-layer routing `ADR-011 + STD-ARCH-PATTERNS-001`, entry-point surfaces `AGENTS.md`, `.github/copilot-instructions.md` и `CLAUDE.md` нормализованы под `Архитектура / Ownership` и explicit source-of-truth policy, `AGENTS.md` materialize-ит baseline через `.github/prompts/includes/canonical-context.md`, `CONTRACTS_REGISTRY.md` объясняет intentional empty `ARCH` lane, `AGENTS_PATCH_GUIDE.md` получил governance routing preflight, `docs/99-ADR/README.md` усилил route к `CONTRACTS_REGISTRY.md`, а `python -m pre_commit run --all-files` служит wave proof; W3 intentionally untouched.)*

*Последнее обновление: 2026-03-29 (волна `D-140..D-143` закрыта как bounded W1 blocking remediation для `governance-routing-accessibility`: в `AGENTS.md` опубликованы explicit authority model, compact decision tree и ownership routing rule с маршрутом `ADR_REGISTRY.md (ADR-011) -> STD-ARCH-PATTERNS-001`, `.github/copilot-instructions.md` синхронизирован до трёх routing branches `STD / ADR / CONTRACT`, а `STD-GOVERNANCE-CONTRACT-001.md` помечает `CONTRACT-ARCH-MODULE-OWNERSHIP-001` как illustrative-only phantom reference; `python -m pre_commit run --all-files` служит wave proof, W2/W3 intentionally untouched.)*

*Последнее обновление: 2026-03-29 (задача `D-139` закрыта как bounded registry-sync contour для `STD-ARCH-PATTERNS-001`: `genome/registries/STANDARDS_REGISTRY.md` синхронизирован под `version 1.0.0` и `status approved`, frontmatter `updated` переведён на `2026-03-29`, статистика пересчитана до `Approved 30 / Proposed 2 / Draft 17`, а `genome/registries/genome_registry.json` выровнен по тому же standard record, чтобы снять downstream failure `validate-standards-registry-autotable` после `D-138`; другие standard rows и `I-921` не менялись.)*

*Последнее обновление: 2026-03-29 (задача `D-138` закрыта как bounded targeted review и approval contour для `STD-ARCH-PATTERNS-001`: после завершённого `D-137` подтверждена полнота и неизменность ownership sections (`Authoritative ownership seam`, `Canonical runtime resolution`, `Lifecycle ownership rule`, `Dual-registration cleanup rule`), стандарт переведён `proposed -> approved` с `version 0.1.2 -> 1.0.0`, rollout-block синхронизирован под `draft -> proposed -> approved`, а `I-921` сознательно не закрывался; registry sync (`D-139`) оставлен отдельным downstream backlog item.)*

*Последнее обновление: 2026-03-29 (задача `D-137` закрыта как bounded structural cleanup для `STD-ARCH-PATTERNS-001`: educational code examples вынесены из стандарта в `examples/arch/` как 7 self-contained `.py` files с верхними explanatory docstring, `examples/arch/README.md` материализует их индекс, а сам стандарт сокращён до `233` строк и сохраняет inline только нормативные ownership/DI rules, diagram и roadmap section; structural proof подтверждён через `python scripts/validators/validate_structural_pressure.py --strict` со статусом `Structural pressure validation OK`, а approval / registry sync (`D-138`, `D-139`) сознательно оставлены вне scope.)*

*Последнее обновление: 2026-03-28 (задача `D-135` закрыта как bounded rollout closure для `test-package-operating-model`: authoritative `D-130 = ready-for-rollout` verdict потреблён как binding input без reopening validation contour, helper-owned default route materialized только для validated seeded pilot case bundle `root.reject_release_cleanup`, `root.valid_release_global_state`, `root.signal_cleanup`, `main_local.repeated_ring_stability` внутри named contour `tests/integration/ui/workspace/drag_drop/**`, retrievable evidence report `EVIDENCE_D-135_condition-based-settle-rollout_2026-03-28.md` подтвердил terminal state `materially-remediated`, cost improvement `42.72%`, flakiness delta `0` и retained cleanup-stage fallback (`12` calls, `probe-error:AttributeError`) как legacy safety-net после substrate teardown; captured proof materialized в `.aife/test-outputs/pytest/closure-proof/d-135/`, targeted suite дал `34 passed`, `0 failed`, full `drag_drop` regression дал `132 passed`, `0 failed`, а wider rollout/default switch beyond validated bundle и fallback removal остались вне scope.)*

*Последнее обновление: 2026-03-27 (задача `D-129` закрыта как bounded validation-only contour для `test-package-operating-model`: materialized opt-in session-bounded reusable `MainWindow` prototype внутри `tests/integration/ui/workspace/drag_drop/validation/` и retrievable evidence report `EVIDENCE_D-129_mainwindow-validation_2026-03-27.md`, который сравнивает fresh-window baseline и shared-window prototype на одном и том же named pilot contour `tests/integration/ui/workspace/drag_drop/**`; targeted proof дал `2 passed`, `0 failed`, но итоговый verdict = `rejected`, потому что case `root.signal_cleanup` воспроизводимо оставляет signal residue `drag_drop.window.visibility 0->1` на seeds `12601/12602/12603`, а measured cost improvement `10.89%` не достигает required `20.0%` threshold. Routing к `D-134 rejection closure` materialized явно; default switch, native fallback removal и broader rollout не authorizes-ились.)*

*Последнее обновление: 2026-03-27 (задача `D-128` закрыта как visibility-only marker contour для `test-package-operating-model`: на 16 collector-visible runtime файлах подтверждённого drag/drop hot contour across `local_anchor`, `main_local`, `interaction`, `root` добавлены parseable module-level `pytest.mark.expensive_runtime(reason=..., owner=..., proof=...)` markers, что materialize-ит governance visibility для hotspot score `1527.1` без runtime behavior changes, taxonomy rewrite, validator expansion, remediation drift или broadened rollout claims; targeted proof подтвердил parseability и pickup existing validator contract.)*

*Последнее обновление: 2026-03-27 (задача `D-127` закрыта как bounded proof-boundary contour для `test-package-operating-model`: owner standard `STD-TEST-PACKAGE-001` теперь явно фиксирует negative boundary `offscreen/minimal -> display-sensitive parity = rejected-with-current-proof`, ограничивает offscreen proof declared `persistence/store/bridge` slices, перечисляет display-sensitive exclusions (`geometry`, `focus`, `event delivery`, `rendering timing`, `popup/widgetAt`, `hit-test`, `overlay`, `drag-drop`) и задаёт allowed/forbidden closure wording; derived `tests/README.md` синхронизирован как annotation layer без parity overclaim, runtime remediation, environment rollout или broader validation drift.)*

*Последнее обновление: 2026-03-27 (задача `D-126` закрыта как bounded random-order / repeated-run validation contour для `test-package-operating-model`: materialized semantic subpackage `tests/integration/ui/workspace/drag_drop/validation/` с helper-layer runner `_random_order_validation_runtime.py` и targeted proof `test_random_order_validation_runtime.py`, seeded iterations `12601/12602/12603` дали retrievable evidence report `EVIDENCE_D-126_random-order-validation_2026-03-27.md` без contamination на named pilot contour `tests/integration/ui/workspace/drag_drop/**`, а downstream finding для `D-129` зафиксировал только blocking validation substrate без pooled/MainWindow rollout, settle API semantics или repo-wide random-order default.)*

*Последнее обновление: 2026-03-27 (задача `D-125` закрыта как approved validation-substrate contour для `test-package-operating-model`: materialized bounded helper-layer `tests/helpers/leakage_observability.py` и pilot helper `tests/integration/ui/workspace/drag_drop/helpers/_observability_runtime_helpers.py` с явным contour `tests/integration/ui/workspace/drag_drop/**`, companion standard `STD-TEST-PACKAGE-001` получил section про leakage observability и 6-dimensional reset-complete contract, targeted proof дал `11 passed`, `0 failed`, а adjacent drag/drop regression slice `test_session_recovery_runtime.py` подтвердил `7 passed`, `0 failed`; production code, `tests/conftest.py`, random-order rollout `D-126`, MainWindow pooling `D-129` и settle/remediation `D-130` не трогались.)*

*Последнее обновление: 2026-03-27 (hardening DEV_TZ test-package-operating-model: semantics переведены из "bounded remediation" в "full known debt closure"; добавлены D-134 (MainWindow terminal debt closure DF-6) и D-135 (Settle API terminal debt closure DF-7) как mandatory verdict-gated task-cards Phase F; Debt Closure Contract section с 10 debt-families; D-128 blocked by D-121+D-123; execution-economics baseline: implementation-bearing 12/15 = 0.80, support-bearing 3/12 = 0.25.)*

*Последнее обновление: 2026-03-26 (импортирован backlog-контур `D-121 .. D-133` из `DEV_TZ_test-package-operating-model_2026-03-26.md`: 13 task-cards в 5 фазах (foundation design, validation substrate, bounded runtime remediation, downstream enforcement, optional acceleration); все task-cards в статусе `Backlog`; execution-economics baseline: implementation-bearing 10/13 ≈ 0.77, support-bearing 3/10 = 0.30; PRR entry создаётся lazy per CONTRACT-DOC-PRR-001 при первом plan-review event.)*

*Последнее обновление: 2026-03-25 (задача `D-120` закрыта как approved limited rollout contour для `test-cost-unification-audit`: materialized bounded helper `scripts/ci/run_validated_xdist_contours.py` с serial / compare recipes для validated-safe first-wave contours и factual xdist fast-path только для `unit-safe` и `unit-ui`; local proof на Windows показал near-neutral `smoke`, slower `integration-safe`, stable repeated green xdist runs для adopted contours и сохранил explicit exclusions `tests/integration/ui/**`, `drag_drop/**`, `tests/performance/**` без repo-wide default, `pytest.ini` addopts или `-n auto`.)*

*Последнее обновление: 2026-03-25 (задача `D-115` закрыта как approved governance-only contour для `test-cost-unification-audit`: materialized canonical AIFE-owned standard-owner `genome/standards/test/STD-TEST-COST-001.md`, который фиксирует authoritative cheap-by-default vocabulary, guardrails для deferred `tests/e2e/`, reference-only `external/`, retained comparison anchor `tests/performance/**` и `xdist` только как validation-gated wall-time-only mitigation; derived consumer sync ограничен `STD-TEST-STRATEGY-001`, `genome/standards/test/README.md`, `tests/README.md`, prompt/include layer и contour artifacts без runtime refactor, pooled harness rollout, threshold enforcement или live validator activation.)*

*Последнее обновление: 2026-03-25 (после отдельного подтверждения инженера весь backlog-контур `D-111 .. D-120` materialized в canonical backlog для `test-cost-unification-audit` без разрыва между уже закрытыми и downstream-задачами: `D-111` закрыт как validation-only contour с retrievable `PRR`, bounded contour matrix и candidate-only handoff в `D-120`, `D-112` закрыт как bounded measurement-only contour с named wall-clock ledger, reproducibility schema, separate heavy-family / helper timing-tax buckets и split `per-test cost` / `suite-wide cost` / `wall-time only mitigation` без threshold enforcement, pooled harness adoption, validator rollout или `xdist` rollout claims, `D-113` закрыт как bounded pooled-vs-fresh feasibility matrix с раздельным evidence по `fresh process`, `pooled QApplication` и `pooled MainWindow`, а `D-114 .. D-120` оставлены в canonical backlog как downstream `Backlog`-контур для baseline enforcement, governance adoption, prompt/docs sync и optional rollout.)*

*Последнее обновление: 2026-03-23 (задача `D-108` закрыта как approved package-closure documentation canonicalization ownership-model contour: `docs/10-Architecture/general/architecture.md`, `docs/15-Initialization/initializer_components.md`, `docs/15-Initialization/README.md`, `initializer/README.md` и `docs/10-Architecture/general/Project_Modules_Documentation.md` выровнены под единый runtime authority contract; targeted canonical-doc grep по builder-residue дал `0 matches`, repo-wide и staged `python -m pre_commit run` завершились `PASSED`, а `D-109` сохранён как отдельный final verification gate.)*

*Последнее обновление: 2026-03-23 (задача `D-101` закрыта как approved local-contour fail-fast cleanup ownership-model: в `initializer/main_logic.py::run()` удалены resurrection-ветки silent `DependencyManager` reattach/initialize, сохранён sanctioned `_read_bootstrap_dependency_manager(...)` read seam и введён explicit `RuntimeError("DependencyManager must be pre-attached and initialized")`; focused regression `tests/unit/bootstrap/test_main_logic.py` подтверждает оба required failure cases (`2 passed`), production startup smoke `python main.py` остаётся зелёным по AppContext path, полный `pytest -q` дал `1624 passed`, `0 failed`, а `python -m pre_commit run --all-files` завершился `PASSED`.)*

*Последнее обновление: 2026-03-23 (задача `D-099` закрыта как proof-gated local-contour cleanup ownership-model: обязательный regression gate `§9.1` пройден до удаления residue, в `ui/layout/mixins/main_window_popup_layout_mixin.py` удалены dead native reset helpers `_reset_layout()` / `_restore_default_toolbar_layout()` и vestigial `saveState()` capture, public reset path `MainWindow.reset_layout() -> workspace_facade.reset_layout()` сохранён как единственный live route, focused reset/snapshot/startup proof повторно зелёный (`29 passed`), а полный `pytest -q` подтвердил `1622 passed`, `0 failed`.)*

*Последнее обновление: 2026-03-23 (ownership-model planning package импортирован в backlog из `DEV_TZ_ownership-model-unification_2026-03-23.md`: добавлены `D-097..D-110`, включая closure-critical runtime/doc canonicalization задачи, governance follow-ups и optional `D-103`. Импорт выполнен в каноническом backlog-формате без дублирования существующих ID; `P4` добавлен как отдельный приоритет для optional hygiene-card, а статистика backlog пересчитана.)*

*Последнее обновление: 2026-03-22 (задача `D-094` закрыта как bounded subtree stabilization для `tests/unit/security/` по `Plan-Review-Ref: PRR-D-094-20260322-approved`: retained-root anchors `__init__.py`, `conftest.py`, `test_security_package_surface.py` сохранены, а subtree декомпозирован в semantic packages `communication/`, `controls/` и `integration/` без helper promotion и без ослабления owner seam `security_app_context`; вся `SecurityManager` integration-family перенесена единым bounded contour, package-surface guard сохранён на root, focused subtree proof подтверждён: `138 passed`, `0 failed`.)*

*Последнее обновление: 2026-03-22 (задача `D-093` закрыта как plan-governed protected-core decomposition строго по preserve-list `D-085`: `tests/unit/test_main.py` и `tests/unit/test_system_initializer.py` сохранены как retained-root anchors, а тематические proof families вынесены в bounded semantic packages `tests/unit/main_entrypoint/` и `tests/unit/system_initializer/`; explicit equivalent-or-stronger proof mapping и closure-proof materialized в `DEV_TZ_tests-standards-and-test-tree-audit_2026-03-20.md`, helper extraction остался bounded (`tests/helpers/main_helpers.py`), а runtime boundary `ADR-011` не ослаблен. Focused proof подтверждён: targeted unit contour `40 passed` + `37 passed`, adjacent integration anchors `15 passed`, `python scripts/validators/validate_structural_pressure.py --strict` — OK, `python -m pre_commit run --all-files` — PASSED, staged gate `python -m pre_commit run` — PASSED.)*

## Отменённые задачи из старого бэклога

Следующие задачи (REC-004..REC-019) отменены как неактуальные для solo-разработки:

- ~~REC-004~~ Уточнить границу Enhancement vs Patch → решено в change-workflow (L1-L5)
- ~~REC-005~~ Процедура апелляции → не нужна для solo
- ~~REC-006~~ Метрики успеха стандарта → не нужна для solo
- ~~REC-007..REC-009~~ Создать STD-SEC/TEST/PERF-001 → 68 стандартов при 20K LOC, ratio 1:5 — преждевременно
- ~~REC-010..REC-017~~ Создать STD-API/ERR/DB/MON/DOC/LOG/CHANGE/ARCH → аналогично
- ~~REC-019~~ Standards Enforcement Gate в CI → pre-commit уже выполняет эту роль

---

*Последнее обновление: 2026-03-20 (`DEV_TZ_genome-standards-arch_2026-03-18.md` доведён до полного closure как execution artifact: все task-cards `D-068..D-080` и `Wave 1..Wave 9` закрыты, `status` DEV_TZ переведён в `closed`, а status drift по Phase B нормализован до factual closure state. При этом parent backlog items `I-921` и `I-929` сознательно не закрываются: после честной синхронизации roadmap-checklists в `STD-ARCH-PATTERNS-001` и `STD-ARCH-ASYNC-001` они остаются открытыми как residual standards debt (`10` и `2` open type-B соответственно), без ложного claim о полном closure самих стандартов.)*

*Последнее обновление: 2026-03-18 (Wave 1 / Phase A по ARCH research частично закрыта: `D-068` и `D-070` переведены в `Done` как design-only / evidence-only deliverables по `Plan-Review-Ref: PRR-D-068-D-070-20260318-approved`. В `DEV_TZ_genome-standards-arch_2026-03-18.md` материализованы authoritative ownership contract и async conformance map без runtime implementation; execution discipline не меняется — Phase B (`D-075..D-080`) остаётся dependency-gated downstream scope, а следующими active design candidates остаются `D-069` и `D-071`.)*

*Последнее обновление: 2026-03-19 (задача `D-077` закрыта в узком approved runtime contour по `Plan-Review-Ref: PRR-D-077-20260319-approved`: `monitoring/monitoring_manager.py` получил owner-managed event-loop lag detection через существующий `TaskManager` substrate и opt-in profiling activation/restore path, `.env/.env.example/example.env` синхронизированы по новым observability flags, а focused regression proof materialized в `tests/unit/monitoring/test_monitoring_manager.py`; repo-wide gates подтверждены: `python -m pre_commit run --all-files` — PASSED, `python -m pytest -q --cov` — `1587 passed`, `0 failed`. При этом `Async middleware for API requests` сознательно оставлен `open`, потому что live request owner path так и не materialize-ился, и synthetic closure нарушила бы boundary `D-077` vs `D-078`.)*

*Последнее обновление: 2026-03-19 (задача `D-078` закрыта в узком approved hotspot contour по `Plan-Review-Ref: PRR-D-078-20260319-approved`: `communication/logging/elk_handler.py` получил dedicated worker boundary для bulk POST/retry/backoff без блокировки caller logging path, `monitoring/security_alerts.py` перевёл webhook delivery в local executor при сохранении sync `process_event(...) -> list[SecurityAlert]`, а `core/management/system_control_manager.py` materialize-ит explicit manager-owned seam `run_client_call(...)` как единственный async-facing bridge над sync `SysControlClient`; focused regression proof materialized в `tests/unit/communication/test_elk_handler.py`, `tests/unit/monitoring/test_security_alerts.py`, `tests/unit/core/management/test_system_control_manager.py`, repo-wide gates подтверждены: `python -m pre_commit run --all-files` — PASSED, `python -m pytest -q --cov` — `1602 passed`, `0 failed`. `native-async-rewrite`, `safe_call` async variant и broad async framework expansion сознательно оставлены вне scope.)*

*Последнее обновление: 2026-03-20 (задача `D-079` закрыта в узком approved runtime-test contour по `Plan-Review-Ref: PRR-D-079-20260320-approved`: materialized только repository-unit slice через новый `tests/unit/core/data/test_data_repository_taxonomy.py` поверх live contracts `BaseRepository` / `BaseUnitOfWork` / `DataSessionAdapter`, тогда как existing `tests/unit/core/data/test_data_package_surface.py` и AppContext-based unit/integration tests (`test_app_context_get_manager.py`, `test_dependency_manager.py`, `test_event_bus.py`, `test_system_initializer_integration.py`) reused как authoritative composition-root/lifecycle evidence; service slice честно зафиксирован как `N/A in current contour`, потому что owner-approved service layer не materialized, а отдельный smoke не создавался как duplicate-only signal. Focused taxonomy proof составил `66 passed`, `0 failed`, repo-wide gates подтверждены: `python -m pre_commit run --all-files` — PASSED, `python -m pytest -q --cov` — PASSED.)*

*Последнее обновление: 2026-03-20 (задача `D-080` закрыта как docs-only synchronization contour по `Task-ID: D-080`: `docs/10-Architecture/general/architecture.md` синхронизирован с authoritative disposition/closure state из `D-073` и `D-075`..`D-079`, получил явный truth-layer notice, корректные AppContext/DependencyManager ownership markers, package-first `core/data/` runtime narrative и честные historical/superseded markers для stale `real_time*`, `test_data_fetcher.py` и `oridginal_docs/` references; runtime/code/test scope не расширялся, а документ сохранён как subordinate overview artifact, а не новый source of truth.)*

*Последнее обновление: 2026-03-20 (для уже закрытой `D-078` зафиксирован post-closure hardening без reopen scope: follow-up commit `4d90f59be723004875e20eae4e5d812a6a700e31` materialized два non-blocking closure-review findings — bounded ELK retry backoff через `ElasticsearchHandlerConfig.max_backoff_seconds` и debug-level success observability для webhook delivery в `SecurityAlertEngine`; focused regression proof для addendum составил `11 passed`, `0 failed`, а repo-wide/staged quality gates были повторно подтверждены. Статус backlog не меняется: `D-078` остаётся `Done`, addendum нужен только для traceability, чтобы fix не оставался chat-only комментарием.)*

*Последнее обновление: 2026-03-18 (волна `C-109..C-113` формально закрыта как завершённый dead-path cleanup для `ui/layout/`: `C-109` убрал документарный status drift в workspace DEV_TZ, `C-110` синхронизировал vestigial package contracts, `C-111` закрепил Variant A для topology constraint helpers, `C-112` удалил remaining DragPayload descriptor residue, `C-113` удалил ghost package `dock_panels/components/`. Дополнительно `I-921` пересверен против самих ARCH-стандартов: `W1/ARCH closure` подтверждает только переход `draft -> proposed` и sign-off ready, но не закрытие Phase 2/3 roadmap-checklists; поэтому active type-B AUTO-строки диапазона `I-900..I-938`, которые всё ещё присутствуют в `closure_readiness_report_latest.md`, возвращены в `Backlog` и не могут быть скрыты ручным `Cancelled` до изменения snapshot/source-of-truth. Единственный follow-up вне scope ui-wave остаётся `C-DPA-009 -> C-108`.)*

*Последнее обновление: 2026-03-18 (задача `C-112` закрыта: dead-path cleanup для `DragPayload` доведён до фактического production scope — публичные accessors `.source` / `.binding` уже отсутствовали в live API, а remaining private descriptor classes `_PayloadSourceDescriptor` / `_PayloadBindingDescriptor` удалены; `DragPayload` переведён на immutable tuple-backed fields без изменения production-alive property surface (`source_zone_id`, `source_zone_type`, `source_parent_zone_id`, `element_id`, `element_type`, `binding_id`, `subject_kind`, `operation`). Точечный regression-proof подтверждён: `tests/unit/ui/test_workspace_drag_drop.py`, `tests/unit/ui/test_panel_drag_presentation_spec.py`, `tests/integration/ui/test_workspace_drag_drop_integration.py` — PASSED.)*

*Последнее обновление: 2026-03-17 (задача `D-067` закрыта: low-priority duplication между `session-start` и `.github/prompts/README.md` снижено без потери discoverability — `session-start` теперь сохраняет только компактный `Goal -> next prompt` router, а полный human-readable prompt map остаётся канонически закреплён за README; тем самым optional residue cleanup prompt-library wave завершён без broad rewrite router semantics. Ранее зафиксированное закрытие `D-066` остаётся в силе: для context-layer prompt library зафиксирован governance loop без раздувания scope — `ui-context` и `main-entrypoint` получили явные review cadence / boundary markers, а локальные index-layer README в `modules/` и `architecture/` теперь отдельно поясняют границу между context prompts и execution prompts, запрещая append-only drift и synthetic freshness без path validation. Ранее зафиксированное закрытие `D-065` остаётся в силе: `audit-session` и `research-session` истончены до guided launchers — canonical owner execution semantics теперь явно закреплены за `audit` и `research`, тогда как session-prompts сохраняют only structured input fields, launch-path selection и dispatch rules. Ранее зафиксированное закрытие `C-091` как execution batch после завершения EXE-011 остаётся в силе: managed dock runtime переведён на workspace-only splitter substrate без native dock dual-mode и без separator drag overlay path; `DockPanelsManager`, `PanelResizeController`, `PanelSplitterWorkspace`, `BaseDockPanel` и `MainWindow` синхронизированы с shell/state-model contract, удалены obsolete helper-модули `separator_drag_controller.py`, `dock_geometry_recovery.py`, `separator_drag_overlay.py`; полный quality gate был подтверждён: `python -m pytest -q`, `python -m pre_commit run --all-files`, `python scripts/check_backlog.py`, `python scripts/validators/validate_batch_done_evidence.py` — PASSED. Уточнение границы scope сохраняется: `EXE-011` закрывает migration только для managed dock panels; native toolbar persistence (`addToolBar/removeToolBar/saveState/restoreState`) остаётся допустимым отдельным subsystem contract и не трактуется как незавершённость dock-panel migration. Дальнейшая работа, включая возможную toolbar migration или общий drag-drop workspace framework, должна открываться отдельной карточкой и отдельным research/TZ.)*

*Последнее обновление: 2026-04-01 (задача `C-132` закрыта как bounded bootstrap-reuse contour для `tests/integration/ui/workspace/drag_drop/**`: reusable controller `helpers/_shared_main_window_runtime.py` и bounded router в `tests/conftest.py` перевели на module-scoped reuse `72` tests across root-level families (`foundation/leakage/legacy_tail/perimeter`), `local_anchor` и `interaction`, при этом `validation` и `main_local` owner contours не менялись; destructive opt-out materialized для `test_shutdown_runtime.py`, `test_session_recovery_runtime.py` и одного deterministic geometry-sensitive case `test_local_anchor_slot_solver_runtime.py::test_small_edge_panel_local_cluster_chooses_free_slot_and_stays_grouped`, поэтому remaining function-scoped contour = `12` tests с explicit `# REASON: destructive`. Three consecutive family reruns остались зелёными (`local_anchor = 32 passed in 36.59s / 36.76s / 36.30s`, `interaction = 16 passed in 15.59s / 15.43s / 15.41s`, migrated root contour = `25 passed in 22.85s / 22.90s / 23.23s`), destructive sanity rerun дал `11 passed in 7.37s`, а full drag/drop contour ускорился с `133 passed in 263.23s`, wall-time `278.003s` до `133 passed in 187.76s`, wall-time `193.988s` (delta `-75.47s` pytest / `-84.015s` wall). Production `ui/`, validation fixtures и drain/settle substrate не менялись; `C-134..C-139`, `D-154`, `D-155` остаются downstream scope.)*

*Последнее обновление: 2026-04-01 (задача `C-131` закрыта как контур подтверждения validation/report после prerequisite `C-130`: проверка `tests/integration/ui/workspace/drag_drop/validation/**` показала, что дополнительный патч для прогрева фикстур не требуется, потому что текущее evidence уже проходит task thresholds — isolated `D-130 = 10.07s`, isolated `D-135 = 10.13s`, внутри validation-кластера `D-130 = 9.72s`, внутри validation-кластера `D-135 = 9.87s`, inflation ≈ `0.97× / 0.97×`, validation cluster = `13 passed in 36.87s`, three consecutive plain reruns = `38.01s / 37.51s / 36.51s`, full drag/drop regression = `133 passed in 281.37s`; settle controller, condition-based logic и production `ui/` не менялись, поэтому truthful closure = подтвердить и зафиксировать без лишней оптимизации. Остальные task-cards wave `C-132..C-139, D-154..D-155` остаются downstream scope.)*

*Последнее обновление: 2026-04-01 (задача `C-130` повторно закрыта после честного уточнения контракта по strict closure-review: latest live rerun `python -m pytest tests/integration/ui/workspace/drag_drop -q --no-cov` (`133 passed in 272.99s`, wall-time `287.093s`) подтвердил не отсутствие улучшений, а то, что isolated wall-time не принадлежит `C-130`; поэтому task contract переведён в truthful lifecycle/drain normalization closure (`drain_light` / `drain_full`, root drag/drop GC flush, marker-routed full-settle override, `needs_full_settle`, inflation control, 3× stability), а aggregate performance proof явно перенесён downstream в `C-131`, `C-132`, `C-134` и финальный `D-155`. Остальные task-cards wave `C-132..C-139, D-154..D-155` остаются `Backlog`, Phase 5B и persistence optimization не reopening.)*

*Последнее обновление: 2026-04-01 (импортирован backlog-контур `C-130..C-139, D-154..D-155` из `DEV_TZ_phase-5c-test-contour_2026-04-01.md`: 12 task-cards в 6 волнах (drain/lifecycle, bootstrap/fixture, duplication/route composition, structural/helper, config/prompt validation, final DoD closure); на момент импорта все task-cards были в статусе `Backlog`; evidence base = consolidated audit 66 findings → 20 CF → 12 tasks; dependency order: W1→W2→W3→W4→W5→W6; binding constraints: no Phase 5B reopen, no new governance, no persistence optimization.)*

*Последнее обновление: 2026-03-27 (задача `D-136` закрыта как bounded test-operations storage contour: materialized canonical machine-readable root `.aife/test-outputs/` с reusable helper/wrapper seam для `closure-proof` / `validation` / `machine-readable` runs, ordinary direct/IDE/button `pytest` loop сохранён `ephemeral`, owner/consumer docs синхронизированы, а evidence artifacts `D-126` и `D-129` теперь явно маршрутизируют к captured `manifest.json`, `command.log` и `pytest.junit.xml` без смешения с `resources`, runtime logs или blanket persistence.)*

- RF-COVERAGE-ENFORCEMENT-FINAL-CLEANUP: accepted — package clean-state cleanup для D-363; stale entries устранены, execution remains closed.
