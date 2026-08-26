---
id: STD-ARCH-001
domain: ARCH
version: '1.1.0'
title: "📐 Architecture Standards (STD-ARCH-001)"
status: approved
owner: AIFE Architecture Team
created: 2025-10-14
updated: 2026-08-26
tags: [standards, architecture]
category: standards
doc_type: standard
language: ru
review_cycle_days: 180
next_review_due: 2027-02-22
---

## 📐 Architecture Standards (STD-ARCH-001)

- Title: Стандарт архитектуры AIFE
- Purpose: Консолидация архитектурных принципов, слоёв и требований к структуре
- Owner: AIFE Architecture Team
- Created: 2025-10-14
- Updated: 2026-08-26

## 🧭 Карта смысловых блоков

> Этот owner-side блок фиксирует ограниченный набор `machine-safe carrier`
> для текущего стандарта. Таблица не создаёт второй источник истины: каждый
> смысловой блок читается только через указанный носитель внутри этого файла
> и YAML front matter.

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Каноническая идентичность, статус и владелец стандарта |
| `baseline_scope` | `## 🎯 Область применения` | `block-level` | Граница применения архитектурного baseline |
| `architecture_layers` | `## 🧱 Слои и модули` | `block-level` | Базовая карта слоёв и модулей AIFE |
| `lifecycle_model` | `## 🔄 Жизненный цикл` | `block-level` | Канонический lifecycle baseline |
| `enforcement_map` | `## 🛡️ Enforcement & Compliance` | `block-level` | Пакет контроля и соответствия |
| `adjacent_owner_routes` | `## 🔗 Связанные стандарты` | `block-level` | Возврат к соседним owner-стандартам |

## 🎯 Область применения

Стандарт определяет базовые принципы архитектуры AIFE: модульность, слабая связанность, event-driven подход, асинхронность, централизованное логирование и жизненный цикл.

## 🧱 Слои и модули

- Core, Communication, AI, Blockchain, UI, Initializer, Monitoring, Security, Resources, Server (admitted future top-level family)
- Разделение ответственности и зависимостей между слоями

## 🔄 Жизненный цикл

- Инициализация (Initializer, AppContext)
- Работа (EventRouter, EventBus, LogManager)
- Завершение (graceful shutdown, compliance)

## 📦 Пакетирование

- Кодовые корни: ai/, core/, communication/, blockchain/, ui/, initializer/, security/, monitoring/, server/ (admitted future top-level family; materialization is separate)
- Тестовые корни: tests/unit, tests/integration
- Скрипты: scripts/

### Допуск будущего top-level `server/`

`server/` допускается как отдельное крупное semantic family исходного кода для generic
Server/Data mechanisms. Допуск корня не материализует пакет и не разрешает runtime
implementation сам по себе.

```text
SERVER_ROOT_KIND=TOP_LEVEL_PYTHON_PACKAGE
SERVER_ROOT_ADMITTED=YES
SERVER_ROOT_MATERIALIZED_BY_THIS_STANDARD=NO
SERVER_ROOT_IS_CORE_SUBPACKAGE=NO
SERVER_ROOT_IS_DEPLOY_DIRECTORY=NO
SERVER_ROOT_IS_GENERIC_DUMPING_GROUND=NO
SERVER_DOMAIN_IS_DOMAIN_SEMANTIC_AUTHORITY=NO
```

Граница ответственности сохраняется: `core/data/**` остаётся нижней generic
repository/session/UoW substrate; будущий `server/storage/**` может оркестрировать lifecycle
и adapters поверх этой substrate, но не создаёт параллельный data substrate. Deployment
artifacts остаются в `deploy/**`. Domain-specific identities, finality, normalization,
revision/gap и resolution rules остаются у соответствующего domain owner.

Публичные typed runtime capabilities будущего `server/**` должны публиковаться через
`AppContext` либо явно одобренные transport adapters. `DependencyManager` остаётся internal
bootstrap/lifecycle registry и не становится public service locator. Новый root обязан
входить в canonical packaging, type-check, lint и coverage boundaries без исключений.

## ✅ Требования

- Соблюдать структуру пакетов и зависимостей
- Использовать централизованное логирование (STD-LOG-001)
- Документировать решения в ADR (99-ADR)

## 🛡️ Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
|-------------|------------------|-------------------|-------|-----------------|
| Соблюдать структуру пакетов и зависимостей | Manual | Release Architecture Review Checklist | Architecture Lead | Каждый релиз |
| Использовать централизованное логирование (STD-LOG-001) | Manual | Architecture Review → Logging compliance check | Architecture Lead | Каждый релиз |
| Документировать решения в ADR (99-ADR) | Manual | ADR Gate в Release Checklist | Architecture Lead | При каждом архитектурном изменении |

## 🔗 Связанные стандарты

- STD-DOC-DOCSTRING-001.md (STD-DOC-DOCSTRING-001)
- STD-LOG-001.md (STD-LOG-001)
- STD-DOC-README-001.md (STD-DOC-README-001)
- STD-DOC-INDEX-001.md (STD-DOC-INDEX-001)

## 🔄 Alignment Note (ARCH proposed clarifications)

Этот approved-base стандарт задаёт только базовый архитектурный baseline.

- Уточнение canonical DI/runtime authority (`AppContext` как единственная публичная runtime surface; `DependencyManager` как internal bootstrap/lifecycle registry) задаётся в `STD-ARCH-PATTERNS-001.md`.
- Уточнение async conformance model, seam policy и runtime expectations задаётся в `STD-ARCH-ASYNC-001.md`.

Если между кратким baseline этого документа и более детализированными proposed-standard уточнениями возникает неоднозначность, для соответствующего scope следует использовать детализированные правила из `STD-ARCH-PATTERNS-001.md` и `STD-ARCH-ASYNC-001.md` без переписывания approved-base semantics этого документа.
