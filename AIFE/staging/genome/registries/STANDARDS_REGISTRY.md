---
id: STANDARDS-REGISTRY-GENOME-AIFE
title: AIFE Standards Registry (Genome)
owner: AIFE Standards Team
status: active
version: '1.0'
created: 2025-11-06
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2026-10-31
category: standards
doc_type: index
language: ru
---

# AIFE Standards Registry (Genome)

Полный реестр стандартов AIFE. После миграции в genome (2025-11-06) это основной источник истины для всех стандартов.

## Навигация

- **Главный README:** [genome/standards/README.md](../standards/README.md)
- **Реестр ADR:** [ADR_REGISTRY.md](./ADR_REGISTRY.md)
- **Реестр контрактов:** [CONTRACTS_REGISTRY.md](./CONTRACTS_REGISTRY.md)
- **Стандарт метаданных со связями:** [STD-DOC-METADATA-001.md](../standards/doc/metadata/STD-DOC-METADATA-001.md) — владеющий словарь `lineage`, `authority-reference`, `companion`, `alias/history`, `redirect/history-trace` и поясняющего `related`; этот реестр только зеркалирует чтение маршрута и статуса и возвращает читателя к владеющему артефакту.
- **JSON экспорт:** [genome_registry.json](./genome_registry.json)
- **Ядро управления знаниями:** [STD-GOVERNANCE-GENOME-001.md](../standards/governance/STD-GOVERNANCE-GENOME-001.md) — первый маршрут чтения для ядра управления знаниями; матрица полномочий и размещения, разделение канонического и производного слоёв и ограничённая словарная база читаются внутри этого же стандарта, без отдельной записи для словарной базы.

## Примечание о производном JSON-слое

- Текущий обязательный производный JSON-носитель для периметра реестров = `genome/registries/genome_registry.json`.
- Он строится только через `scripts/standards/registry_generator.py`.
- Этот реестр участвует в генерации как owner-backed input и route/mirror carrier в явной цепочке `owner artifact -> registry row -> generated entry`.
- Если строка реестра расходится с owner-артефактом, generated JSON не должен молча уносить этот drift дальше: рассинхрон обязан чиниться в owner/registry слое.
- Отдельные JSON-носители по одной записи на стандарт (`per-artifact`) текущим контуром не разрешены.

## Примечание о семантике связей

- Этот реестр остаётся авторитетным только для маршрута, статуса, версии,
  владельца, домена и канонической ссылки на стандарт.
- Смысл связей `lineage`, `authority-reference`, `companion`, `alias/history`, `redirect/history-trace` и поясняющего `related` читается через `STD-DOC-METADATA-001.md` и YAML-метаданные самого владеющего артефакта, а не из поясняющего текста или автотаблицы этого реестра.
- Если запись стандарта участвует в чтении `lineage` или
  `authority-reference`, реестр должен только вернуть читателя к живому
  артефакту. Показательный случай `lineage` в семействе стандартов читается во владеющем артефакте через `genome/standards/async/README.md` и `genome/standards/arch/STD-ARCH-ASYNC-001.md`, а не через строку реестра.

## Реестр стандартов

<!-- BEGIN: AUTO-STANDARDS-TABLE -->
<!-- Эта таблица генерируется автоматически. Не редактировать вручную! -->

| ID | Name | Version | Status | Owner Team | Domain | Link |
|----|------|---------|--------|------------|--------|------|
| STD-API-DESIGN-001 | STD-API-DESIGN-001 — API Design Principles | 1.0.0 | approved | AIFE Standards Team | API | [genome/standards/api/STD-API-DESIGN-001.md](../standards/api/STD-API-DESIGN-001.md) |
| STD-API-DOCS-001 | STD-API-DOCS-001 — API Documentation | 1.0.0 | approved | AIFE Standards Team | API | [genome/standards/api/STD-API-DOCS-001.md](../standards/api/STD-API-DOCS-001.md) |
| STD-API-ERRORS-001 | STD-API-ERRORS-001 — API Error Response Format | 1.0.0 | approved | AIFE Standards Team | API | [genome/standards/api/STD-API-ERRORS-001.md](../standards/api/STD-API-ERRORS-001.md) |
| STD-API-RATE-001 | STD-API-RATE-001 — API Rate Limiting | 1.0.0 | approved | AIFE Standards Team | API | [genome/standards/api/STD-API-RATE-001.md](../standards/api/STD-API-RATE-001.md) |
| STD-API-VERSIONING-001 | STD-API-VERSIONING-001 — API Versioning Strategy | 1.0.0 | approved | AIFE Standards Team | API | [genome/standards/api/STD-API-VERSIONING-001.md](../standards/api/STD-API-VERSIONING-001.md) |
| STD-ARCH-001 | 📐 Architecture Standards (STD-ARCH-001) | 1.1.0 | approved | AIFE Architecture Team | ARCH | [genome/standards/arch/STD-ARCH-001.md](../standards/arch/STD-ARCH-001.md) |
| STD-ARCH-ASYNC-001 | STD-ARCH-ASYNC-001: Async/Await Best Practices | 0.1.0 | proposed | AIFE Standards Team | ARCH | [genome/standards/arch/STD-ARCH-ASYNC-001.md](../standards/arch/STD-ARCH-ASYNC-001.md) |
| STD-ARCH-PATTERNS-001 | STD-ARCH-PATTERNS-001: Architectural Patterns | 1.0.0 | approved | AIFE Standards Team | ARCH | [genome/standards/arch/STD-ARCH-PATTERNS-001.md](../standards/arch/STD-ARCH-PATTERNS-001.md) |
| STD-CHANGE-001 | STD-CHANGE-001: Классификация и жизненный цикл изменений | 2.0.0 | approved | AIFE Standards Team | CHANGE | [genome/standards/change/STD-CHANGE-001.md](../standards/change/STD-CHANGE-001.md) |
| STD-CHANGE-HANDOFF-001 | STD-CHANGE-HANDOFF-001: Маршруты передачи Git-патча | 3.9.0 | approved | AIFE Standards Team | CHANGE | [genome/standards/change/STD-CHANGE-HANDOFF-001.md](../standards/change/STD-CHANGE-HANDOFF-001.md) |
| STD-DATA-BACKUP-001 | STD-DATA-BACKUP-001 — Backup & Restore | 0.2.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-BACKUP-001.md](../standards/data/STD-DATA-BACKUP-001.md) |
| STD-DATA-MGMT-001 | STD-DATA-MGMT-001 — Data Management Principles | 0.2.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-MGMT-001.md](../standards/data/STD-DATA-MGMT-001.md) |
| STD-DATA-MIGRATION-001 | STD-DATA-MIGRATION-001 — Migration Process | 0.1.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-MIGRATION-001.md](../standards/data/STD-DATA-MIGRATION-001.md) |
| STD-DATA-RETENTION-001 | STD-DATA-RETENTION-001 — Data Retention Policy | 0.2.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-RETENTION-001.md](../standards/data/STD-DATA-RETENTION-001.md) |
| STD-DATA-SCHEMA-001 | STD-DATA-SCHEMA-001 — Database Schema Standards | 0.2.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-SCHEMA-001.md](../standards/data/STD-DATA-SCHEMA-001.md) |
| STD-DATA-VALIDATION-001 | STD-DATA-VALIDATION-001 — Data Validation | 0.1.0 | draft | AIFE Standards Team | DATA | [genome/standards/data/STD-DATA-VALIDATION-001.md](../standards/data/STD-DATA-VALIDATION-001.md) |
| STD-DOC-DIAGRAMS-001 | STD-DOC-DIAGRAMS-001: Стандарт правила источника и экспорта диаграмм и критериев пригодности к чтению (`usable diagram`) | 0.2.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/diagrams/STD-DOC-DIAGRAMS-001.md](../standards/doc/diagrams/STD-DOC-DIAGRAMS-001.md) |
| STD-DOC-DOCSTRING-001 | AIFE Docstring Standards | 1.4.1 | approved | Documentation Team | DOC | [genome/standards/doc/docstring/STD-DOC-DOCSTRING-001.md](../standards/doc/docstring/STD-DOC-DOCSTRING-001.md) |
| STD-DOC-FRESHNESS-001 | STD-DOC-FRESHNESS-001: Стандарт матрицы изменений, актуальности и обязательного повторного чтения (`reread`) | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/freshness/STD-DOC-FRESHNESS-001.md](../standards/doc/freshness/STD-DOC-FRESHNESS-001.md) |
| STD-DOC-HELP-001 | STD-DOC-HELP-001: Стандарт `runtime-help`, `developer-help`, `runtime-overlay` и навигации с возвратом к владельцу (`route-back`) | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/help/STD-DOC-HELP-001.md](../standards/doc/help/STD-DOC-HELP-001.md) |
| STD-DOC-INDEX-001 | Стандарт: Машинно‑читаемые индексы документации (JSON) | 0.2.0 | draft | AIFE Standards Team | DOC | [genome/standards/doc/indexes/STD-DOC-INDEX-001.md](../standards/doc/indexes/STD-DOC-INDEX-001.md) |
| STD-DOC-INSTRUCTIONS-001 | Instructions Organization Standard | 1.3.0 | approved | Documentation Team | DOC | [genome/standards/doc/instructions/STD-DOC-INSTRUCTIONS-001.md](../standards/doc/instructions/STD-DOC-INSTRUCTIONS-001.md) |
| STD-DOC-LEGACY-001 | STD-DOC-LEGACY-001: Стандарт чтения классов `legacy`/`generated`/`residual`/`evidence`/`deferred` и трассируемости (`traceability`) | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/legacy/STD-DOC-LEGACY-001.md](../standards/doc/legacy/STD-DOC-LEGACY-001.md) |
| STD-DOC-METADATA-001 | STD-DOC-METADATA-001: Стандарт метаданных Markdown | 1.8.0 | approved | Documentation Team | DOC | [genome/standards/doc/metadata/STD-DOC-METADATA-001.md](../standards/doc/metadata/STD-DOC-METADATA-001.md) |
| STD-DOC-PLACEMENT-001 | STD-DOC-PLACEMENT-001: Стандарт размещения документационных носителей по семействам | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/placement/STD-DOC-PLACEMENT-001.md](../standards/doc/placement/STD-DOC-PLACEMENT-001.md) |
| STD-DOC-README-001 | README Standards | 1.1.0 | approved | Documentation Team | DOC | [genome/standards/doc/readme/STD-DOC-README-001.md](../standards/doc/readme/STD-DOC-README-001.md) |
| STD-DOC-SEMANTIC-001 | STD-DOC-SEMANTIC-001: Стандарт семантической документационной папки слоя | 0.1.3 | approved | Documentation Team | DOC | [genome/standards/doc/semantic/STD-DOC-SEMANTIC-001.md](../standards/doc/semantic/STD-DOC-SEMANTIC-001.md) |
| STD-DOC-SUBSTRATE-001 | STD-DOC-SUBSTRATE-001: Стандарт документационной подложки и границы между истиной и доставкой (`truth / delivery`) | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/substrate/STD-DOC-SUBSTRATE-001.md](../standards/doc/substrate/STD-DOC-SUBSTRATE-001.md) |
| STD-DOC-TERMINOLOGY-001 | STD-DOC-TERMINOLOGY-001: Стандарт терминологии, происхождения (`provenance`) и первого определения | 0.1.0 | approved | AIFE Standards Team | DOC | [genome/standards/doc/terminology/STD-DOC-TERMINOLOGY-001.md](../standards/doc/terminology/STD-DOC-TERMINOLOGY-001.md) |
| STD-GOVERNANCE-ADR-001 | Стандарт артефактов ADR | 1.0.0 | approved | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/adr/STD-GOVERNANCE-ADR-001.md](../standards/governance/adr/STD-GOVERNANCE-ADR-001.md) |
| STD-GOVERNANCE-AUTHORING-001 | Standard Authoring Template | 1.0.0 | approved | AIFE Standards Team | GOVERNANCE | [genome/standards/governance/STD-GOVERNANCE-AUTHORING-001.md](../standards/governance/STD-GOVERNANCE-AUTHORING-001.md) |
| STD-GOVERNANCE-CONTRACT-001 | Contract Authoring Standard | 1.1.0 | approved | AIFE Standards Team | GOVERNANCE | [genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md](../standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md) |
| STD-GOVERNANCE-GENOME-001 | STD-GOVERNANCE-GENOME-001: Ядро управления знаниями, полномочия и ограничённая словарная база | 1.0.0 | approved | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/STD-GOVERNANCE-GENOME-001.md](../standards/governance/STD-GOVERNANCE-GENOME-001.md) |
| STD-GOVERNANCE-HOOKS-001 | STD-GOVERNANCE-HOOKS-001: Стандарт управления hook ecosystem | 1.0.0 | approved | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/hooks/STD-GOVERNANCE-HOOKS-001.md](../standards/governance/hooks/STD-GOVERNANCE-HOOKS-001.md) |
| STD-GOVERNANCE-IMPROVEMENT-001 | STD-GOVERNANCE-IMPROVEMENT-001 Standards Improvement Process | 1.3.0 | proposed | Quality Team | GOVERNANCE | [genome/standards/governance/improvement/STD-GOVERNANCE-IMPROVEMENT-001.md](../standards/governance/improvement/STD-GOVERNANCE-IMPROVEMENT-001.md) |
| STD-GOVERNANCE-METRICS-001 | STD-GOVERNANCE-METRICS-001: Стандарт управления метриками, порогами и политикой продвижения | 1.0.0 | draft | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/metrics/STD-GOVERNANCE-METRICS-001.md](../standards/governance/metrics/STD-GOVERNANCE-METRICS-001.md) |
| STD-GOVERNANCE-NAMING-001 | Стандарт именования канонических артефактов STD / ADR / CONTRACT | 1.3.0 | approved | AIFE Standards Team | GOVERNANCE | [genome/standards/governance/STD-GOVERNANCE-NAMING-001.md](../standards/governance/STD-GOVERNANCE-NAMING-001.md) |
| STD-GOVERNANCE-ROUTING-001 | STD-GOVERNANCE-ROUTING-001: Стандарт маршрута публикации у владельца и выбора носителя | 1.2.1 | draft | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/STD-GOVERNANCE-ROUTING-001.md](../standards/governance/STD-GOVERNANCE-ROUTING-001.md) |
| STD-GOVERNANCE-STRUCTURAL-001 | Structural Decomposition Standard | 0.1.0 | draft | AIFE Architecture Team | GOVERNANCE | [genome/standards/governance/structural/STD-GOVERNANCE-STRUCTURAL-001.md](../standards/governance/structural/STD-GOVERNANCE-STRUCTURAL-001.md) |
| STD-LOG-001 | AIFE Logging Standards | 2.3.0 | approved | Communication Team | LOG | [genome/standards/log/STD-LOG-001.md](../standards/log/STD-LOG-001.md) |
| STD-MON-ALERTING-001 | STD-MON-ALERTING-001: Alerting | 0.1.0 | draft | Quality Team | MON | [genome/standards/mon/STD-MON-ALERTING-001.md](../standards/mon/STD-MON-ALERTING-001.md) |
| STD-MON-BASE-001 | STD-MON-BASE-001: Принципы мониторинга | 0.1.0 | draft | Quality Team | MON | [genome/standards/mon/STD-MON-BASE-001.md](../standards/mon/STD-MON-BASE-001.md) |
| STD-MON-DASHBOARD-001 | STD-MON-DASHBOARD-001: Dashboards | 0.1.0 | draft | Quality Team | MON | [genome/standards/mon/STD-MON-DASHBOARD-001.md](../standards/mon/STD-MON-DASHBOARD-001.md) |
| STD-MON-HEALTH-001 | STD-MON-HEALTH-001: Health Checks | 0.1.0 | draft | Quality Team | MON | [genome/standards/mon/STD-MON-HEALTH-001.md](../standards/mon/STD-MON-HEALTH-001.md) |
| STD-MON-METRICS-001 | STD-MON-METRICS-001: Сбор метрик | 0.1.0 | draft | Quality Team | MON | [genome/standards/mon/STD-MON-METRICS-001.md](../standards/mon/STD-MON-METRICS-001.md) |
| STD-PERF-BENCHMARK-001 | STD-PERF-BENCHMARK-001: Benchmarking | 0.1.0 | draft | Quality Team | PERF | [genome/standards/perf/STD-PERF-BENCHMARK-001.md](../standards/perf/STD-PERF-BENCHMARK-001.md) |
| STD-PERF-CACHING-001 | STD-PERF-CACHING-001: Caching | 0.1.0 | draft | Quality Team | PERF | [genome/standards/perf/STD-PERF-CACHING-001.md](../standards/perf/STD-PERF-CACHING-001.md) |
| STD-PERF-OPTIMIZATION-001 | STD-PERF-OPTIMIZATION-001: Optimization | 0.1.0 | draft | Quality Team | PERF | [genome/standards/perf/STD-PERF-OPTIMIZATION-001.md](../standards/perf/STD-PERF-OPTIMIZATION-001.md) |
| STD-PERF-PROFILING-001 | STD-PERF-PROFILING-001: Profiling | 0.1.0 | draft | Quality Team | PERF | [genome/standards/perf/STD-PERF-PROFILING-001.md](../standards/perf/STD-PERF-PROFILING-001.md) |
| STD-SEC-AUTH-001 | STD-SEC-AUTH-001: Стандарт аутентификации и авторизации | 1.0.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-AUTH-001.md](../standards/sec/STD-SEC-AUTH-001.md) |
| STD-SEC-ENCRYPTION-001 | STD-SEC-ENCRYPTION-001: Стандарт шифрования данных | 1.0.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-ENCRYPTION-001.md](../standards/sec/STD-SEC-ENCRYPTION-001.md) |
| STD-SEC-LOG-001 | STD-SEC-LOG-001: Стандарт security логирования | 1.0.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-LOG-001.md](../standards/sec/STD-SEC-LOG-001.md) |
| STD-SEC-PRINCIPLES-001 | STD-SEC-PRINCIPLES-001 — Security Principles Standard | 1.0.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-PRINCIPLES-001.md](../standards/sec/STD-SEC-PRINCIPLES-001.md) |
| STD-SEC-REVIEW-001 | STD-SEC-REVIEW-001: Стандарт проверки безопасности кода | 1.1.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-REVIEW-001.md](../standards/sec/STD-SEC-REVIEW-001.md) |
| STD-SEC-SECRETS-001 | STD-SEC-SECRETS-001 — Secrets Management Standard | 1.0.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-SECRETS-001.md](../standards/sec/STD-SEC-SECRETS-001.md) |
| STD-SEC-VULN-001 | STD-SEC-VULN-001: Стандарт управления уязвимостями | 1.1.0 | approved | Security Team | SEC | [genome/standards/sec/STD-SEC-VULN-001.md](../standards/sec/STD-SEC-VULN-001.md) |
| STD-TEST-COST-001 | STD-TEST-COST-001: Стандарт cheap-by-default governance для ordinary tests | 1.0.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-COST-001.md](../standards/test/STD-TEST-COST-001.md) |
| STD-TEST-COVERAGE-001 | STD-TEST-COVERAGE-001: Стандарт покрытия тестами кода | 1.0.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-COVERAGE-001.md](../standards/test/STD-TEST-COVERAGE-001.md) |
| STD-TEST-DATA-001 | STD-TEST-DATA-001: Стандарт управления тестовыми данными | 1.1.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-DATA-001.md](../standards/test/STD-TEST-DATA-001.md) |
| STD-TEST-EVIDENCE-001 | STD-TEST-EVIDENCE-001: Стандарт размещения и проверки доказательств измерений | 1.0.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-EVIDENCE-001.md](../standards/test/STD-TEST-EVIDENCE-001.md) |
| STD-TEST-PACKAGE-001 | STD-TEST-PACKAGE-001: Стандарт модели тестовых пакетов | 1.1.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-PACKAGE-001.md](../standards/test/STD-TEST-PACKAGE-001.md) |
| STD-TEST-PERF-001 | STD-TEST-PERF-001: Стандарт performance тестирования | 1.1.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-PERF-001.md](../standards/test/STD-TEST-PERF-001.md) |
| STD-TEST-STRATEGY-001 | STD-TEST-STRATEGY-001: Стандарт стратегии тестирования | 1.0.0 | approved | QA Team | TEST | [genome/standards/test/STD-TEST-STRATEGY-001.md](../standards/test/STD-TEST-STRATEGY-001.md) |
| STD-TEST-TOOLCHAIN-001 | STD-TEST-TOOLCHAIN-001: Стандарт автономного quality toolchain | 1.10.0 | approved | AIFE Architecture Team | TEST | [genome/standards/test/STD-TEST-TOOLCHAIN-001.md](../standards/test/STD-TEST-TOOLCHAIN-001.md) |

**Total standards:** 64

<!-- END: AUTO-STANDARDS-TABLE -->

## Статистика

- **Всего стандартов:** 60
- **Approved:** 39
- **Proposed:** 2
- **Draft:** 19

## История миграции

- **2025-11-06:** Полная миграция из docs/94-Standards/ в genome/standards/
- Все ссылки обновлены (54 замены в 33 файлах)
- Старая директория сохранена только с redirect файлом
