---
title: "Server/Data foundation: исходное дерево"
id: DOC-10-ARCHITECTURE-TREE-SERVER
version: '0.1'
status: active
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
review_cycle_days: 90
next_review_due: 2026-11-24
tags: [architecture, tree, server, data]
category: architecture
doc_type: design
language: ru
authority_reference:
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
---

# Server/Data foundation: исходное дерево

## Назначение

Дерево покрывает первый физический `server/` package. Оно является навигационной
проекцией F2-контрактов, а не отдельным источником семантики. F3 реализует
backend-neutral модели, чистые переходы состояния, узкие порты и typed composition;
F4 добавляет только neutral accepted-domain envelope/bindings. ETH/provider adaptation остаётся
за пределами будущего generic AIFE Server source.

## Дерево

```text
server/  # Backend-neutral Server/Data foundation; доменная семантика остаётся у домена.
├── __init__.py  # Публичный package boundary: ProcessRole и typed runtime dependencies.
├── _validation.py  # Общие pure guards для non-empty values, aware datetime и deterministic identities.
├── access/  # CONTRACT-SERVER-ACCESS-001: typed query/result boundary без transport/API backend.
│   ├── __init__.py  # Публичные ACCESS value objects и result envelope.
│   └── models.py  # Filters, result/source/snapshot/provenance identity, pagination и explicit partial/error semantics.
├── application/  # Application-facing async protocols; не второй DI/service-locator route.
│   ├── __init__.py  # Публичный typed service bundle.
│   └── services.py  # Узкие async service protocols для work/scheduling/execution/publication/access.
├── configuration/  # Минимальные reusable role/timing types, не production configuration system.
│   ├── __init__.py  # Публичные process-role и timing configuration values.
│   └── models.py  # CONTROL/WORKER/COMBINED_INITIAL_NODE и deterministic lease/retry timing.
├── execution/  # CONTRACT-SERVER-EXECUTION-001: claim/lease/fencing/reclaim authority.
│   ├── __init__.py  # Публичная EXECUTION boundary.
│   └── models.py  # Claim, lease expiry, fencing token, renewal/reclaim и stale-fence rejection.
├── integration/  # Neutral accepted-domain boundary; доменная семантика и адаптация остаются у domain owner.
│   ├── __init__.py  # Публичные domain-envelope и generic binding types/functions.
│   ├── bindings.py  # Deterministic domain→WORK/PUBLICATION/STORAGE/ACCESS identity bindings без payload reinterpretation.
│   └── domain.py  # Opaque domain identity/type/revision/hash/provenance/acceptance/payload/timing envelope.
├── publication/  # CONTRACT-SERVER-PUBLICATION-001: единственный publication lifecycle и ACK gate.
│   ├── __init__.py  # Публичная PUBLICATION boundary.
│   └── models.py  # Восемь состояний, strict transition order и four-proof ACK conjunction.
├── runtime/  # Typed composition seam для будущего AppContext integration.
│   ├── __init__.py  # Публичная runtime composition boundary.
│   ├── composition.py  # Lifecycle protocol и immutable dependency container без singleton/global state.
│   ├── readiness.py  # Изолированные F5 readiness predicates без запуска реального server readiness.
│   └── recovery.py  # Bounded backup/restore и reconciliation orchestration для persisted F5 control/object state.
├── scheduling/  # CONTRACT-SERVER-SCHEDULING-001: deterministic due identity и materialization boundary.
│   ├── __init__.py  # Публичная SCHEDULING boundary.
│   └── models.py  # Schedule definition, timezone-aware due identity и retry/backoff decision.
├── storage/  # CONTRACT-SERVER-STORAGE-001: backend-neutral capability ports.
│   ├── __init__.py  # Публичные STORAGE capabilities и typed evidence values.
│   ├── filesystem.py  # Qualified DATA_ROOT immutable filesystem adapter с atomic create, fsync и independent readback.
│   └── ports.py  # Десять narrow async protocols, сгруппированных только для composition.
└── work/  # CONTRACT-SERVER-WORK-001: durable logical-work model без physical persistence.
    ├── __init__.py  # Публичная WORK boundary.
    └── models.py  # WorkId/WorkType/state machine, attempt separation и idempotent retry identity.
```

## Архитектурная граница

`server/` не выбирает PostgreSQL/Redis/S3/queue/HTTP и не импортирует ETH/provider
семантику. F4 generic integration не содержит provider-specific branch/finality/normalization
logic. `AppContext` остаётся будущей единственной публичной composition surface;
`DependencyManager`, `CoreManager` и `TaskManager` не получают новой durable authority.
