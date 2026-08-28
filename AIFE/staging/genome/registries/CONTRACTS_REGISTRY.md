---
id: CONTRACTS-REGISTRY-GENOME-AIFE
title: AIFE Contracts Registry
owner: AIFE Architecture Team
status: active
version: "1.0"
created: 2026-03-24
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2026-10-18
category: standards
doc_type: index
language: ru
---

# AIFE Contracts Registry

Полный реестр контрактов AIFE. Это канонический источник истины по
`CONTRACT-ID`, статусам, версиям, владельцам и ссылкам на связывающие соглашения.

## Навигация

- **Реестр стандартов:** [STANDARDS_REGISTRY.md](./STANDARDS_REGISTRY.md)
- **Реестр ADR:** [ADR_REGISTRY.md](./ADR_REGISTRY.md)
- **Стандарт метаданных со связями:** [STD-DOC-METADATA-001](../standards/doc/metadata/STD-DOC-METADATA-001.md)
- **Стандарт формы контракта:** [STD-GOVERNANCE-CONTRACT-001](../standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md)
- **Стандарт именования артефактов:** [STD-GOVERNANCE-NAMING-001](../standards/governance/STD-GOVERNANCE-NAMING-001.md)
- **ADR о введении контрактов:** [ADR-GOVERNANCE-CONTRACT-001](../adr/governance/ADR-GOVERNANCE-CONTRACT-001.md)

## Примечание о производном JSON-слое

- Текущий обязательный производный JSON-носитель для периметра реестров = `genome/registries/genome_registry.json`.
- Он строится только через `scripts/standards/registry_generator.py`.
- Этот реестр участвует в генерации как owner-backed input и route/mirror carrier в явной цепочке `owner artifact -> registry row -> generated entry`.
- Если строка реестра расходится с owner-контрактом, generated JSON не должен маскировать этот drift: сначала чинится owner/registry sync, а потом пересобирается export.
- Отдельные JSON-носители по одной записи на контракт (`per-artifact`) текущим контуром не разрешены.

## Примечание о семантике связей

- Этот реестр остаётся авторитетным только для `CONTRACT-ID`, `status`,
  `version`, `owner`, `domain` и канонического `link`.
- Смысл `lineage`, `authority-reference`, `companion`, `alias/history`,
  `redirect/history-trace` и поясняющего `related` читается через
  `STD-DOC-METADATA-001.md` и метаданные самого контрактного артефакта, а не из
  поясняющего текста или строки таблицы этого реестра.
- Показательный случай `authority-reference` на стороне контрактов читается во
  владеющем артефакте в
  `genome/contracts/doc/CONTRACT-DOC-PRR-001.md`, где живёт
  `authority_reference` к `STD-GOVERNANCE-CONTRACT-001`; строка реестра только
  возвращает читателя к контракту и не создаёт собственную семантику связей.

## Правила использования

- Начинать навигацию по контрактам нужно отсюда, а не с прямого просмотра `genome/contracts/`.
- При расхождениях между ссылками в других документах и фактическими статусами контрактов доверять этому реестру.
- При создании нового контракта агент обязан зарегистрировать его здесь в том же change-set.
- Формат контрактов и обязательные секции определены в
  `STD-GOVERNANCE-CONTRACT-001`.
- Общая canonical grammar ID stem для family `CONTRACT` определяется
  `STD-GOVERNANCE-NAMING-001`.

### Scope guard для ARCH domain

На текущем слое governance отсутствие `ARCH`-контрактов в таблице ниже является
осознанным состоянием, а не missing deployment. Для reusable ownership / boundary /
lifecycle rules маршрут идёт через `STANDARDS_REGISTRY.md`, начиная с
`STD-ARCH-PATTERNS-001`, а decision-history для owner seam — через `ADR_REGISTRY.md`
(`ADR-011`). Contract-track для ARCH открывается только если появится named binding
agreement между конкретными артефактами, а не ещё одна universal ownership rule.

### Вердикт Wave 1 по частичному паритету семейства CONTRACT

**Терминальный вердикт (I-1006):** именованный удержанный остаток — вариант 2 из 3
разрешённых по `Task Contract`.

- Семейство `CONTRACT` в Wave 1 представлено одной записью
  (`CONTRACT-DOC-PRR-001`, `approved`, домен `DOC`). Это намеренное
  ограниченное состояние, а не структурный дефект.
- После `I-1005` производный экспорт `genome_registry.json` честно отражает
  этот корпус: ключ `contracts` содержит 1 запись — skip-эффект устранён.
- Шумовые случаи (`redirect` remnants, generated leftovers, stale companion
  placements) в активном корпусе маршрута владельца **отсутствуют**
  (`not-present`). Семейство CONTRACT не имело legacy-redirect слоя — это
  ADR-специфичная история; ни orphan-файлов в `genome/contracts/`, ни
  stale companion placements не обнаружено.
- Конкурирующей семантики владельца или параллельной точки первого чтения
  нет: `AGENTS.md` → `CONTRACTS_REGISTRY.md` — единственный маршрут.
- Расширение корпуса контрактов (новые `CONTRACT-*`) — downstream задача за
  пределами контура Wave 1.

**Источник:** `I-1006` / Wave 1 / post-closure-enforcement-and-runtime-resolution

**Дополнение I-1067:** действующий `CONTRACT-CHANGE-HANDOFF-001` также связывает стандартный `direct_patch` с точным blob подтверждения и каноническим digest операций.

## Реестр контрактов

<!-- BEGIN: AUTO-CONTRACTS-TABLE -->
<!-- Эта таблица обновляется вручную при создании/изменении контрактов. -->

| ID | Name | Version | Status | Owner | Domain | Link |
|----|------|---------|--------|-------|--------|------|
| CONTRACT-CHANGE-HANDOFF-001 | CONTRACT-CHANGE-HANDOFF-001: Привязка авторизации к контракту задачи | 1.8.0 | approved | Architecture Lead | CHANGE | [genome/contracts/change/CONTRACT-CHANGE-HANDOFF-001.md](../contracts/change/CONTRACT-CHANGE-HANDOFF-001.md) |
| CONTRACT-DOC-PRR-001 | CONTRACT-DOC-PRR-001: PRR Integration Contract | 1.0.0 | approved | Architecture Lead | DOC | [genome/contracts/doc/CONTRACT-DOC-PRR-001.md](../contracts/doc/CONTRACT-DOC-PRR-001.md) |
| CONTRACT-SERVER-ACCESS-001 | CONTRACT-SERVER-ACCESS-001: Generic Semantic Access Boundary Contract | 0.2.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md](../contracts/server/CONTRACT-SERVER-ACCESS-001.md) |
| CONTRACT-SERVER-EXECUTION-001 | CONTRACT-SERVER-EXECUTION-001: Distributed Execution Ownership Contract | 0.2.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md](../contracts/server/CONTRACT-SERVER-EXECUTION-001.md) |
| CONTRACT-SERVER-PUBLICATION-001 | CONTRACT-SERVER-PUBLICATION-001: Durable Publication and ACK Contract | 0.3.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md](../contracts/server/CONTRACT-SERVER-PUBLICATION-001.md) |
| CONTRACT-SERVER-SCHEDULING-001 | CONTRACT-SERVER-SCHEDULING-001: Generic Scheduling and Due Materialization Contract | 0.1.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md](../contracts/server/CONTRACT-SERVER-SCHEDULING-001.md) |
| CONTRACT-SERVER-STORAGE-001 | CONTRACT-SERVER-STORAGE-001: Generic Storage Lifecycle Port Contract | 0.3.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md](../contracts/server/CONTRACT-SERVER-STORAGE-001.md) |
| CONTRACT-SERVER-WORK-001 | CONTRACT-SERVER-WORK-001: Generic Durable Work Contract | 0.1.0 | draft | Architecture Lead | SERVER | [genome/contracts/server/CONTRACT-SERVER-WORK-001.md](../contracts/server/CONTRACT-SERVER-WORK-001.md) |

**Total Contracts:** 8

<!-- END: AUTO-CONTRACTS-TABLE -->

## Статистика

- **Всего контрактов:** 8
- **Approved:** 2
- **Draft:** 6

## Протокол маршрутизации

Вход в контракты должен идти так:

`AGENTS.md` → `genome/registries/CONTRACTS_REGISTRY.md` → нужный контракт

Для combined governance work:

`AGENTS.md` → `STANDARDS_REGISTRY.md` + `ADR_REGISTRY.md` + `CONTRACTS_REGISTRY.md` → релевантные артефакты
