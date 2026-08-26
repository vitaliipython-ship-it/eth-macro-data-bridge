---
title: "Владелец-слой genome"
id: DOC-10-ARCHITECTURE-TREE-PROJECT-CONTROL-GENOME
version: '0.2'
status: active
owner: Architecture Lead
created: 2026-06-04
updated: 2026-08-26
review_cycle_days: 90
next_review_due: 2026-09-02
tags: [architecture, tree]
category: architecture
doc_type: design
language: ru
authority_reference:
  - ../../architecture.md
---

# Владелец-слой genome

## Назначение

Дерево покрывает стандарты, ADR, контракты и реестры. Смысл каждого owner-артефакта уточняется через соответствующий реестр.

## Дерево

```text
genome/  # Владелец-слой стандартов, ADR, контрактов и реестров.
├── adr/  # Архитектурные решения.
│   ├── comm/  # Каталог comm; назначение уточняется по дочерним файлам.
│   │   ├── ADR-COMM-BUS-001.md  # Архитектурное решение: ADR-COMM-BUS-001: Выравнивание EventBus.
│   │   ├── ADR-COMM-ROUTER-001.md  # Архитектурное решение: ADR-COMM-ROUTER-001: Централизация жизненного цикла EventRouter.
│   │   └── comm.json  # JSON-конфигурация или данные: comm.
│   ├── doc/  # Каталог doc; назначение уточняется по дочерним файлам.
│   │   ├── ADR-DOC-SUBSTRATE-001.md  # Архитектурное решение: ADR-DOC-SUBSTRATE-001: Граница truth/delivery в документационной подложке AIFE.
│   │   └── doc.json  # JSON-конфигурация или данные: doc.
│   ├── governance/  # Каталог governance; назначение уточняется по дочерним файлам.
│   │   ├── ADR-GOVERNANCE-CONTRACT-001.md  # Архитектурное решение: ADR-GOVERNANCE-CONTRACT-001: Введение типа артефакта `Contract` в Genome.
│   │   └── governance.json  # JSON-конфигурация или данные: governance.
│   ├── graph/  # Каталог graph; назначение уточняется по дочерним файлам.
│   │   ├── ADR-GRAPH-SUBSTRATE-001.md  # Архитектурное решение: ADR-GRAPH-SUBSTRATE-001: Классы и границы подложки для контура навигации по знаниям.
│   │   └── graph.json  # JSON-конфигурация или данные: graph.
│   ├── initializer/  # Инициализация приложения, AppContext и жизненный цикл запуска.
│   │   ├── ADR-INITIALIZER-CONTEXT-001.md  # Архитектурное решение: ADR-INITIALIZER-CONTEXT-001: Шаблон AppContext для устранения R0913.
│   │   ├── ADR-INITIALIZER-CORE-001.md  # Архитектурное решение: ADR-INITIALIZER-CORE-001: Разрешение зависимостей через AppContext и граница владения.
│   │   ├── ADR-INITIALIZER-CORE-002.md  # Архитектурное решение: ADR-INITIALIZER-CORE-002: Владелец жизненного цикла EventBus и закрытие legacy-bootstrap путей.
│   │   ├── ADR-INITIALIZER-SYSTEM-001.md  # Архитектурное решение: ADR-INITIALIZER-SYSTEM-001: Архитектура инициализационной системы v2B.
│   │   ├── ADR-INITIALIZER-SYSTEM-002.md  # Архитектурное решение: ADR-INITIALIZER-SYSTEM-002: Устаревшая реализация инициализационной системы.
│   │   └── initializer.json  # JSON-конфигурация или данные: initializer.
│   ├── log/  # Каталог log; назначение уточняется по дочерним файлам.
│   │   ├── ADR-LOG-INJECTION-001.md  # Архитектурное решение: ADR-LOG-INJECTION-001: Выравнивание логирования через внедрение зависимостей.
│   │   └── log.json  # JSON-конфигурация или данные: log.
│   ├── security/  # Слой безопасности, валидации, сканирования и защитных правил.
│   │   ├── ADR-SECURITY-CAPABILITIES-001.md  # Архитектурное решение: ADR-SECURITY-CAPABILITIES-001: Запланированные возможности контура безопасности — категории событий `threat` и `compliance`.
│   │   └── security.json  # JSON-конфигурация или данные: security.
│   ├── ui/  # Интерфейс, рабочая область, панели, графики и визуальные компоненты.
│   │   ├── ADR-UI-CHART-001.md  # Архитектурное решение: ADR-UI-CHART-001: Выбор backend'а графиков — `pyqtgraph` (`realtime`) + `matplotlib` (`offline export`).
│   │   ├── ADR-UI-WORKSPACE-001.md  # Архитектурное решение: ADR-UI-WORKSPACE-001: Перераспределение владения взаимодействием с dock-панелями.
│   │   ├── ADR-UI-WORKSPACE-002.md  # Архитектурное решение: ADR-UI-WORKSPACE-002: Архитектурный фундамент каркаса рабочего пространства для MainWindow и границы объёма.
│   │   └── ui.json  # JSON-конфигурация или данные: ui.
│   └── README.md  # Обзор и маршрут чтения: genome/adr — канонический корень архитектурных решений AIFE.
├── contracts/  # Контракты между поверхностями и процессами.
│   ├── change/  # Именованные соглашения управления изменениями.
│   │   ├── CONTRACT-CHANGE-HANDOFF-001.md  # Контракт Task Contract authorization profile ↔ handoff manifest.
│   │   └── change.json  # Производный semantic catalog CHANGE-контрактов.
│   ├── doc/  # Каталог doc; назначение уточняется по дочерним файлам.
│   │   ├── CONTRACT-DOC-PRR-001.md  # Контракт: CONTRACT-DOC-PRR-001: PRR Integration Contract.
│   │   └── doc.json  # JSON-конфигурация или данные: doc.
│   └── server/  # Generic Server/Data mechanism contracts; доменная семантика остаётся у domain owners.
│       ├── CONTRACT-SERVER-ACCESS-001.md  # Generic semantic request/result access boundary.
│       ├── CONTRACT-SERVER-EXECUTION-001.md  # Distributed claim, lease, fencing and terminal authority contract.
│       ├── CONTRACT-SERVER-PUBLICATION-001.md  # Durable publication, read-back, registration and ACK lifecycle.
│       ├── CONTRACT-SERVER-SCHEDULING-001.md  # Generic scheduling, due computation and work materialization boundary.
│       ├── CONTRACT-SERVER-STORAGE-001.md  # Backend-neutral durable storage lifecycle capability contract.
│       ├── CONTRACT-SERVER-WORK-001.md  # Stable durable work identity/state and idempotency contract.
│       └── server.json  # Производный semantic catalog SERVER-контрактов.
├── registries/  # Реестры владельческих артефактов и маршрутов.
│   ├── ADR_REGISTRY.md  # Реестр: AIFE ADR Registry.
│   ├── CONTRACTS_REGISTRY.md  # Реестр: AIFE Contracts Registry.
│   ├── genome_registry.json  # JSON-конфигурация или данные: genome registry.
│   └── STANDARDS_REGISTRY.md  # Реестр: AIFE Standards Registry (Genome).
└── standards/  # Стандарты проекта.
    ├── api/  # Каталог api; назначение уточняется по дочерним файлам.
    │   ├── api.json  # JSON-конфигурация или данные: api.
    │   ├── README.md  # Обзор и маршрут чтения: API Standards (api/).
    │   ├── STD-API-DESIGN-001.md  # Стандарт: STD-API-DESIGN-001 — API Design Principles.
    │   ├── STD-API-DOCS-001.md  # Стандарт: STD-API-DOCS-001 — API Documentation.
    │   ├── STD-API-ERRORS-001.md  # Стандарт: STD-API-ERRORS-001 — API Error Response Format.
    │   ├── STD-API-RATE-001.md  # Стандарт: STD-API-RATE-001 — API Rate Limiting.
    │   └── STD-API-VERSIONING-001.md  # Стандарт: STD-API-VERSIONING-001 — API Versioning Strategy.
    ├── arch/  # Каталог arch; назначение уточняется по дочерним файлам.
    │   ├── arch.json  # JSON-конфигурация или данные: arch.
    │   ├── README.md  # Обзор и маршрут чтения: 🏛️ Architecture Standards (ARCH).
    │   ├── STD-ARCH-001.md  # Стандарт: 📐 Architecture Standards (STD-ARCH-001).
    │   ├── STD-ARCH-ASYNC-001.md  # Стандарт: STD-ARCH-ASYNC-001: Async/Await Best Practices.
    │   └── STD-ARCH-PATTERNS-001.md  # Стандарт: STD-ARCH-PATTERNS-001: Architectural Patterns.
    ├── async/  # Каталог async; назначение уточняется по дочерним файлам.
    │   └── README.md  # Обзор и маршрут чтения: Async Standards (async/).
    ├── change/  # Каталог change; назначение уточняется по дочерним файлам.
    │   ├── templates/  # Каталог templates; назначение уточняется по дочерним файлам.
    │   │   ├── README.md  # Обзор и маршрут чтения: Change Templates Index.
    │   │   ├── TEMPLATE_ADR_Architectural_Version.md  # Стандарт: ADR-NNN: <Title> Architecture.
    │   │   └── TEMPLATE_Hotfix_Postmortem.md  # Стандарт: 🔴 Hotfix Post-mortem: <Name>.
    │   ├── change.json  # JSON-конфигурация или данные: change.
    │   ├── README.md  # Обзор и маршрут чтения: Стандарты управления изменениями.
    │   └── STD-CHANGE-001.md  # Стандарт: STD-CHANGE-001: Классификация и жизненный цикл изменений.
    ├── data/  # Каталог data; назначение уточняется по дочерним файлам.
    │   ├── data.json  # JSON-конфигурация или данные: data.
    │   ├── README.md  # Обзор и маршрут чтения: 📊 Data Management Standards — Navigation Index.
    │   ├── STD-DATA-BACKUP-001.md  # Стандарт: STD-DATA-BACKUP-001 — Backup & Restore.
    │   ├── STD-DATA-MGMT-001.md  # Стандарт: STD-DATA-MGMT-001 — Data Management Principles.
    │   ├── STD-DATA-MIGRATION-001.md  # Стандарт: STD-DATA-MIGRATION-001 — Migration Process.
    │   ├── STD-DATA-RETENTION-001.md  # Стандарт: STD-DATA-RETENTION-001 — Data Retention Policy.
    │   ├── STD-DATA-SCHEMA-001.md  # Стандарт: STD-DATA-SCHEMA-001 — Database Schema Standards.
    │   └── STD-DATA-VALIDATION-001.md  # Стандарт: STD-DATA-VALIDATION-001 — Data Validation.
    ├── doc/  # Каталог doc; назначение уточняется по дочерним файлам.
    │   ├── diagrams/  # Каталог diagrams; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-DIAGRAMS-001.md  # Стандарт: STD-DOC-DIAGRAMS-001: Стандарт правила источника и экспорта диаграмм и критериев пригодности к чтению (`usable diagram`).
    │   ├── docstring/  # Каталог docstring; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-DOCSTRING-001.md  # Стандарт: AIFE Docstring Standards.
    │   ├── freshness/  # Каталог freshness; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-FRESHNESS-001.md  # Стандарт: STD-DOC-FRESHNESS-001: Стандарт матрицы изменений, актуальности и обязательного повторного чтения (`reread`).
    │   ├── help/  # Справочные ресурсы интерфейса.
    │   │   └── STD-DOC-HELP-001.md  # Стандарт: STD-DOC-HELP-001: Стандарт `runtime-help`, `developer-help`, `runtime-overlay` и навигации с возвратом к владельцу (`route-back`).
    │   ├── indexes/  # Каталог indexes; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-INDEX-001.md  # Стандарт: Стандарт: Машинно‑читаемые индексы документации (JSON).
    │   ├── instructions/  # Каталог instructions; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-INSTRUCTIONS-001.md  # Стандарт: Instructions Organization Standard.
    │   ├── legacy/  # Каталог legacy; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-LEGACY-001.md  # Стандарт: STD-DOC-LEGACY-001: Стандарт чтения классов `legacy`/`generated`/`residual`/`evidence`/`deferred` и трассируемости (`traceability`).
    │   ├── metadata/  # Каталог metadata; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-METADATA-001.md  # Стандарт: STD-DOC-METADATA-001: Стандарт метаданных Markdown.
    │   ├── placement/  # Каталог placement; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-PLACEMENT-001.md  # Стандарт: STD-DOC-PLACEMENT-001: Стандарт размещения документационных носителей по семействам.
    │   ├── readme/  # Каталог readme; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-README-001.md  # Стандарт: README Standards.
    │   ├── semantic/  # Папка стандартов профиля семантической документационной папки слоя.
    │   │   └── STD-DOC-SEMANTIC-001.md  # Стандарт: STD-DOC-SEMANTIC-001: профиль семантической документационной папки слоя.
    │   ├── substrate/  # Каталог substrate; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-SUBSTRATE-001.md  # Стандарт: STD-DOC-SUBSTRATE-001: Стандарт документационной подложки и границы между истиной и доставкой (`truth / delivery`).
    │   ├── terminology/  # Каталог terminology; назначение уточняется по дочерним файлам.
    │   │   └── STD-DOC-TERMINOLOGY-001.md  # Стандарт: STD-DOC-TERMINOLOGY-001: Стандарт терминологии, происхождения (`provenance`) и первого определения.
    │   ├── doc.json  # JSON-конфигурация или данные: doc.
    │   └── README.md  # Обзор и маршрут чтения: 📝 Стандарты документирования (DOC).
    ├── domain-specific/  # Каталог domain specific; назначение уточняется по дочерним файлам.
    │   ├── ai/  # Доменные стандарты AI/ML; не runtime-доказательство реализации моделей.
    │   │   └── README.md  # Обзор и маршрут чтения: AI/ML Standards (domain-specific/ai/).
    │   ├── blockchain/  # Runtime-слой блокчейн-интеграции.
    │   │   └── README.md  # Обзор и маршрут чтения: Blockchain Standards (domain-specific/blockchain/).
    │   └── README.md  # Обзор и маршрут чтения: Domain-Specific Standards.
    ├── events/  # Каталог events; назначение уточняется по дочерним файлам.
    │   └── README.md  # Обзор и маршрут чтения: Event Standards (events/).
    ├── governance/  # Каталог governance; назначение уточняется по дочерним файлам.
    │   ├── adr/  # Архитектурные решения.
    │   │   └── STD-GOVERNANCE-ADR-001.md  # Стандарт: Стандарт артефактов ADR.
    │   ├── contract/  # Каталог contract; назначение уточняется по дочерним файлам.
    │   │   └── STD-GOVERNANCE-CONTRACT-001.md  # Стандарт: Contract Authoring Standard.
    │   ├── hooks/  # Каталог hooks; назначение уточняется по дочерним файлам.
    │   │   ├── enforcement_heavy_rollout_playbook.md  # Стандарт: Playbook тяжёлой раскатки принудительного обеспечения.
    │   │   └── STD-GOVERNANCE-HOOKS-001.md  # Стандарт: STD-GOVERNANCE-HOOKS-001: Стандарт управления hook ecosystem.
    │   ├── improvement/  # Каталог improvement; назначение уточняется по дочерним файлам.
    │   │   └── STD-GOVERNANCE-IMPROVEMENT-001.md  # Стандарт: STD-GOVERNANCE-IMPROVEMENT-001 Standards Improvement Process.
    │   ├── metrics/  # Каталог metrics; назначение уточняется по дочерним файлам.
    │   │   └── STD-GOVERNANCE-METRICS-001.md  # Стандарт: STD-GOVERNANCE-METRICS-001: Стандарт управления метриками, порогами и политикой продвижения.
    │   ├── structural/  # Каталог structural; назначение уточняется по дочерним файлам.
    │   │   └── STD-GOVERNANCE-STRUCTURAL-001.md  # Стандарт: Structural Decomposition Standard.
    │   ├── governance.json  # JSON-конфигурация или данные: governance.
    │   ├── README.md  # Обзор и маршрут чтения: ⚖️ Индекс набора governance-стандартов.
    │   ├── STD-GOVERNANCE-AUTHORING-001.md  # Стандарт: Standard Authoring Template.
    │   ├── STD-GOVERNANCE-GENOME-001.md  # Стандарт: STD-GOVERNANCE-GENOME-001: Ядро управления знаниями, полномочия и ограничённая словарная база.
    │   ├── STD-GOVERNANCE-NAMING-001.md  # Стандарт: Стандарт именования канонических артефактов STD / ADR / CONTRACT.
    │   └── STD-GOVERNANCE-ROUTING-001.md  # Стандарт: STD-GOVERNANCE-ROUTING-001: Стандарт маршрута публикации у владельца и выбора носителя.
    ├── log/  # Каталог log; назначение уточняется по дочерним файлам.
    │   ├── log.json  # JSON-конфигурация или данные: log.
    │   ├── README.md  # Обзор и маршрут чтения: 🪵 Logging Standards (LOG).
    │   └── STD-LOG-001.md  # Стандарт: AIFE Logging Standards.
    ├── mon/  # Каталог mon; назначение уточняется по дочерним файлам.
    │   ├── mon.json  # JSON-конфигурация или данные: mon.
    │   ├── README.md  # Обзор и маршрут чтения: Monitoring Standards (mon/).
    │   ├── STD-MON-ALERTING-001.md  # Стандарт: STD-MON-ALERTING-001: Alerting.
    │   ├── STD-MON-BASE-001.md  # Стандарт: STD-MON-BASE-001: Принципы мониторинга.
    │   ├── STD-MON-DASHBOARD-001.md  # Стандарт: STD-MON-DASHBOARD-001: Dashboards.
    │   ├── STD-MON-HEALTH-001.md  # Стандарт: STD-MON-HEALTH-001: Health Checks.
    │   └── STD-MON-METRICS-001.md  # Стандарт: STD-MON-METRICS-001: Сбор метрик.
    ├── ops/  # Каталог ops; назначение уточняется по дочерним файлам.
    │   └── README.md  # Обзор и маршрут чтения: Operations Standards (ops/).
    ├── perf/  # Каталог perf; назначение уточняется по дочерним файлам.
    │   ├── perf.json  # JSON-конфигурация или данные: perf.
    │   ├── README.md  # Обзор и маршрут чтения: Performance Standards (perf/).
    │   ├── STD-PERF-BENCHMARK-001.md  # Стандарт: STD-PERF-BENCHMARK-001: Benchmarking.
    │   ├── STD-PERF-CACHING-001.md  # Стандарт: STD-PERF-CACHING-001: Caching.
    │   ├── STD-PERF-OPTIMIZATION-001.md  # Стандарт: STD-PERF-OPTIMIZATION-001: Optimization.
    │   └── STD-PERF-PROFILING-001.md  # Стандарт: STD-PERF-PROFILING-001: Profiling.
    ├── sec/  # Каталог sec; назначение уточняется по дочерним файлам.
    │   ├── README.md  # Обзор и маршрут чтения: Security Standards (sec/).
    │   ├── sec.json  # JSON-конфигурация или данные: sec.
    │   ├── STD-SEC-AUTH-001.md  # Стандарт: STD-SEC-AUTH-001: Стандарт аутентификации и авторизации.
    │   ├── STD-SEC-ENCRYPTION-001.md  # Стандарт: STD-SEC-ENCRYPTION-001: Стандарт шифрования данных.
    │   ├── STD-SEC-LOG-001.md  # Стандарт: STD-SEC-LOG-001: Стандарт security логирования.
    │   ├── STD-SEC-PRINCIPLES-001.md  # Стандарт: STD-SEC-PRINCIPLES-001 — Security Principles Standard.
    │   ├── STD-SEC-REVIEW-001.md  # Стандарт: STD-SEC-REVIEW-001: Стандарт security code review.
    │   ├── STD-SEC-SECRETS-001.md  # Стандарт: STD-SEC-SECRETS-001 — Secrets Management Standard.
    │   └── STD-SEC-VULN-001.md  # Стандарт: STD-SEC-VULN-001: Стандарт управления уязвимостями.
    ├── test/  # Каталог test; назначение уточняется по дочерним файлам.
    │   ├── README.md  # Обзор и маршрут чтения: Testing Standards (test/).
    │   ├── STD-TEST-COST-001.md  # Стандарт: STD-TEST-COST-001: Стандарт cheap-by-default governance для ordinary tests.
    │   ├── STD-TEST-COVERAGE-001.md  # Стандарт: STD-TEST-COVERAGE-001: Стандарт покрытия тестами кода.
    │   ├── STD-TEST-DATA-001.md  # Стандарт: STD-TEST-DATA-001: Стандарт управления тестовыми данными.
    │   ├── STD-TEST-EVIDENCE-001.md  # Стандарт: STD-TEST-EVIDENCE-001: Стандарт размещения и проверки доказательств измерений.
    │   ├── STD-TEST-PACKAGE-001.md  # Стандарт: STD-TEST-PACKAGE-001: Стандарт модели тестовых пакетов.
    │   ├── STD-TEST-PERF-001.md  # Стандарт: STD-TEST-PERF-001: Стандарт performance тестирования.
    │   ├── STD-TEST-STRATEGY-001.md  # Стандарт: STD-TEST-STRATEGY-001: Стандарт стратегии тестирования.
    │   └── test.json  # JSON-конфигурация или данные: test.
    ├── OWNERS_ALIASES.md  # Стандарт: Owners Aliases Reference.
    └── README.md  # Обзор и маршрут чтения: 📘 Standards (каноника).
```

## Правило чтения

Комментарии рядом с файлами дают короткую тематическую роль. Подробное поведение проверяется по коду, тестам и профильным документам.
