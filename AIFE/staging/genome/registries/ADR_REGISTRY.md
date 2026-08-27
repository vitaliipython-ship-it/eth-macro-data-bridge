---
id: ADR-REGISTRY-GENOME-AIFE
title: AIFE ADR Registry
owner: AIFE Architecture Team
status: active
version: "1.0"
created: 2026-03-20
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2026-10-18
category: architecture
doc_type: index
language: ru
---

# AIFE ADR Registry

Полный реестр архитектурных решений AIFE. Это канонический источник истины по
текущим опубликованным ADR-строкам: ID, статусам, версиям, владельцам и
ссылкам на связывающие архитектурные решения. Контракт артефактов для семейства `ADR`
публикуется в `STD-GOVERNANCE-ADR-001`, а общая грамматика канонического
именования ADR — в `STD-GOVERNANCE-NAMING-001`.

## Навигация

- **Реестр стандартов:** [STANDARDS_REGISTRY.md](./STANDARDS_REGISTRY.md)
- **Стандарт метаданных со связями:** [STD-DOC-METADATA-001.md](../standards/doc/metadata/STD-DOC-METADATA-001.md)
- **Стандарт артефактов ADR:** [STD-GOVERNANCE-ADR-001.md](../standards/governance/adr/STD-GOVERNANCE-ADR-001.md)
- **Стандарт именования:** [STD-GOVERNANCE-NAMING-001.md](../standards/governance/STD-GOVERNANCE-NAMING-001.md)
- **Канонический корень ADR:** [genome/adr/README.md](../adr/README.md)
- **Устаревший слой поиска:** [docs/99-ADR/README.md](../../docs/99-ADR/README.md)

## Примечание о производном JSON-слое

- Текущий обязательный производный JSON-носитель для периметра реестров = `genome/registries/genome_registry.json`.
- Он строится только через `scripts/standards/registry_generator.py`.
- Этот реестр участвует в генерации как owner-backed input и route/mirror carrier в явной цепочке `owner artifact -> registry row -> generated entry`.
- Если строка ADR-реестра расходится с owner-артефактом, generated JSON не должен скрывать этот drift: сначала нужно синхронизировать owner-файл и строку реестра.
- Отдельные JSON-носители по одной записи на ADR (`per-artifact`) текущим контуром не разрешены.

## Примечание о семантике связей

- Этот реестр остаётся авторитетным только для опубликованного списка ADR:
  `ID`, `status`, `version`, `owner`, `Area` и канонического `Link`.
- Смысл `lineage`, `authority-reference`, `companion`, `alias/history`,
  `redirect/history-trace` и поясняющего `related` читается через
  `STD-DOC-METADATA-001.md` и метаданные самих владеющих артефактов, а не
  из поясняющего текста, строк таблицы или примечаний о непрерывности этого реестра.
- Показательный случай `lineage` на стороне ADR нужно читать во владеющем
  артефакте в
  `genome/adr/initializer/ADR-INITIALIZER-CORE-002.md`, где живёт
  `replaces: ADR-011-ADD-001`; реестр и `docs/99-ADR/**` остаются только
  поверхностями маршрута и поиска и не создают отдельную грамматику для
  `lineage`.

## Правила использования

- Начинать навигацию по архитектурным решениям нужно отсюда, а не с прямого просмотра `genome/adr/` или `docs/99-ADR/`.
- Канонический owner-first маршрут для семейства ADR = `AGENTS.md` → `ADR_REGISTRY.md` → `genome/adr/**`.
- `docs/99-ADR/**` остаётся только ограниченной legacy lookup / continuity surface и не является owner-layer.
- При расхождениях между `genome/adr/**`, `docs/99-ADR/README.md`, ссылками в других документах и фактическими статусами ADR доверять этому реестру.
- Перед созданием нового ADR агент обязан проверить, нет ли уже binding ADR source для текущего architectural seam.
- При изменении статуса, версии, owner или появлении нового ADR реестр обязан обновляться в том же change-set.

## Placement note

- Колонка `Link` несёт канонический placement route для ADR family.
- Колонка `Area` сохраняется как semantic metadata и не подменяет owner-side filesystem authority.
- Маршрут артефактов, граница размещения и разделение `owner corpus vs legacy continuity` читаются через `STD-GOVERNANCE-ADR-001`.
- Shared canonical naming grammar для `ADR` family читается через `STD-GOVERNANCE-NAMING-001`.
- Standalone naming/placement migration `D-165` уже материализована: canonical registry rows и canonical owner corpus используют shared grammar и domain-only placement.
- После `D-166` legacy continuity остаётся только в `docs/99-ADR/**`; active registry rows больше не публикуют addenda как canonical targets.

## Naming note

- Общая owner-side naming grammar для `ADR` family читается через
  `STD-GOVERNANCE-NAMING-001`, а правила маршрута и размещения артефактов — через
  `STD-GOVERNANCE-ADR-001`.
- Нормализованная shared grammar = `ADR-<DOMAIN>-<QUALIFIER>-<NNN>`.
- `QUALIFIER` обязателен, а `NNN` ведётся локально от `001` внутри canonical
  bucket `ADR + DOMAIN + QUALIFIER`.
- Колонка `Area` остаётся semantic metadata only и не создаёт дополнительных
  ID slots.
- Canonical placement route читается как `genome/adr/<domain-lowercase>/...`;
  `QUALIFIER` уточняет stem файла, но не создаёт отдельную папку.
- Standalone ADR уже нормализованы literal по owner-published mapping из
  `genome/adr/README.md`; composite standalone buckets `ui-chart`,
  `ui-workspace`, `initializer-core` больше не используются как canonical
  placement matrix.
- Текущие sequence-only legacy IDs, date/slug continuity filenames и lineage
  tokens `ADD` / `ADDENDUM` сохраняются только как legacy continuity layer в
  `docs/99-ADR/**`; этот реестр не трактует их как вторую canonical grammar и не публикует их как active owner rows после `D-166`.

## Реестр ADR

<!-- BEGIN: AUTO-ADR-TABLE -->
<!-- Контракт таблицы унифицирован с реестром стандартов. -->

| ID | Name | Version | Status | Owner Team | Area | Link |
|----|------|---------|--------|------------|------|------|
| ADR-INITIALIZER-CONTEXT-001 | ADR-INITIALIZER-CONTEXT-001: Шаблон AppContext для устранения R0913 | 1.0 | active | Architecture Lead | INITIALIZER | [genome/adr/initializer/ADR-INITIALIZER-CONTEXT-001.md](../adr/initializer/ADR-INITIALIZER-CONTEXT-001.md) |
| ADR-COMM-ROUTER-001 | ADR-COMM-ROUTER-001: Централизация жизненного цикла EventRouter | 1.0 | active | Architecture Lead | COMM | [genome/adr/comm/ADR-COMM-ROUTER-001.md](../adr/comm/ADR-COMM-ROUTER-001.md) |
| ADR-INITIALIZER-SYSTEM-001 | ADR-INITIALIZER-SYSTEM-001: Архитектура инициализационной системы v2B | 1.0 | active | Architecture Lead | INITIALIZER | [genome/adr/initializer/ADR-INITIALIZER-SYSTEM-001.md](../adr/initializer/ADR-INITIALIZER-SYSTEM-001.md) |
| ADR-INITIALIZER-SYSTEM-002 | ADR-INITIALIZER-SYSTEM-002: Устаревшая реализация инициализационной системы | 1.0 | deprecated | Architecture Lead | INITIALIZER | [genome/adr/initializer/ADR-INITIALIZER-SYSTEM-002.md](../adr/initializer/ADR-INITIALIZER-SYSTEM-002.md) |
| ADR-COMM-BUS-001 | ADR-COMM-BUS-001: Выравнивание EventBus | 1.0 | active | Architecture Lead | COMM | [genome/adr/comm/ADR-COMM-BUS-001.md](../adr/comm/ADR-COMM-BUS-001.md) |
| ADR-LOG-INJECTION-001 | ADR-LOG-INJECTION-001: Выравнивание логирования через внедрение зависимостей | 1.0 | active | Architecture Lead | LOG | [genome/adr/log/ADR-LOG-INJECTION-001.md](../adr/log/ADR-LOG-INJECTION-001.md) |
| ADR-SECURITY-CAPABILITIES-001 | ADR-SECURITY-CAPABILITIES-001: Запланированные возможности контура безопасности — категории событий `threat` и `compliance` | 1.1 | active | Architecture Lead | SECURITY | [genome/adr/security/ADR-SECURITY-CAPABILITIES-001.md](../adr/security/ADR-SECURITY-CAPABILITIES-001.md) |
| ADR-UI-CHART-001 | ADR-UI-CHART-001: Выбор backend'а графиков — `pyqtgraph` (`realtime`) + `matplotlib` (`offline export`) | 1.0 | active | Architecture Lead | UI | [genome/adr/ui/ADR-UI-CHART-001.md](../adr/ui/ADR-UI-CHART-001.md) |
| ADR-UI-WORKSPACE-001 | ADR-UI-WORKSPACE-001: Перераспределение владения взаимодействием с dock-панелями | 1.0 | active | Architecture Lead | UI | [genome/adr/ui/ADR-UI-WORKSPACE-001.md](../adr/ui/ADR-UI-WORKSPACE-001.md) |
| ADR-UI-WORKSPACE-002 | ADR-UI-WORKSPACE-002: Архитектурный фундамент каркаса рабочего пространства для MainWindow и границы объёма | 1.0 | active | Architecture Lead | UI | [genome/adr/ui/ADR-UI-WORKSPACE-002.md](../adr/ui/ADR-UI-WORKSPACE-002.md) |
| ADR-INITIALIZER-CORE-001 | ADR-INITIALIZER-CORE-001: Разрешение зависимостей через AppContext и граница владения | 1.0 | active | Architecture Lead | INITIALIZER | [genome/adr/initializer/ADR-INITIALIZER-CORE-001.md](../adr/initializer/ADR-INITIALIZER-CORE-001.md) |
| ADR-INITIALIZER-CORE-002 | ADR-INITIALIZER-CORE-002: Владелец жизненного цикла EventBus и закрытие legacy-bootstrap путей | 1.0 | active | Architecture Lead | INITIALIZER | [genome/adr/initializer/ADR-INITIALIZER-CORE-002.md](../adr/initializer/ADR-INITIALIZER-CORE-002.md) |
| ADR-GOVERNANCE-CONTRACT-001 | ADR-GOVERNANCE-CONTRACT-001: Введение типа артефакта `Contract` в Genome | 1.0 | active | Architecture Lead | GOVERNANCE | [genome/adr/governance/ADR-GOVERNANCE-CONTRACT-001.md](../adr/governance/ADR-GOVERNANCE-CONTRACT-001.md) |
| ADR-GOVERNANCE-HANDOFF-001 | ADR-GOVERNANCE-HANDOFF-001: Два маршрута передачи Git-патча | 4.0 | active | Architecture Lead | GOVERNANCE | [genome/adr/governance/ADR-GOVERNANCE-HANDOFF-001.md](../adr/governance/ADR-GOVERNANCE-HANDOFF-001.md) |
| ADR-GRAPH-SUBSTRATE-001 | ADR-GRAPH-SUBSTRATE-001: Классы и границы подложки для контура навигации по знаниям | 1.0 | active | Architecture Lead | GRAPH | [genome/adr/graph/ADR-GRAPH-SUBSTRATE-001.md](../adr/graph/ADR-GRAPH-SUBSTRATE-001.md) |
| ADR-DOC-SUBSTRATE-001 | ADR-DOC-SUBSTRATE-001: Граница truth/delivery в документационной подложке AIFE | 1.0 | active | Architecture Lead | DOC | [genome/adr/doc/ADR-DOC-SUBSTRATE-001.md](../adr/doc/ADR-DOC-SUBSTRATE-001.md) |
| ADR-DATA-FOUNDATION-001 | ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root | 1.1 | active | Architecture Lead | DATA | [genome/adr/data/ADR-DATA-FOUNDATION-001.md](../adr/data/ADR-DATA-FOUNDATION-001.md) |

**Total ADRs:** 17 (17 standalone)

<!-- END: AUTO-ADR-TABLE -->

## Статистика

- **Всего ADR:** 17 (17 standalone)
- **Active:** 16
- **Deprecated:** 1

## Протокол маршрутизации

Вход в архитектурные решения должен идти так:

`AGENTS.md` → `genome/registries/ADR_REGISTRY.md` → `genome/adr/**`

Для combined architecture work порядок такой:

`AGENTS.md` → `STANDARDS_REGISTRY.md` + `ADR_REGISTRY.md` → релевантные стандарты и ADR → task/review/implementation
