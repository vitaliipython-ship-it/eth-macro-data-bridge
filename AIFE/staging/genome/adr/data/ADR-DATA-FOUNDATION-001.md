---
id: ADR-DATA-FOUNDATION-001
title: "ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root"
version: '1.0'
status: proposed
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
category: architecture
doc_type: adr
language: ru
tags: [server, data, foundation, appcontext, storage, scalability]
related:
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
  - genome/adr/comm/ADR-COMM-BUS-001.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_2026-08-24.md
---

# ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root

## Статус

**Предложено.** ADR не становится канонической полномочной документацией AIFE до точной
интеграции владельцем и регистрации в `genome/registries/ADR_REGISTRY.md`.

## Контекст

AIFE уже имеет утверждённый `Manager → Service → Repository`, `core/data/**`, `AppContext`
как единственную публичную типизированную поверхность исполнения и внутренний
`DependencyManager`. Конкретная топология БД и активный server/data Artifact Contract не
выбраны. ETH Data Bridge доказал полезные механизмы идентичности работы, checkpoint/recovery,
публикации, readback и storage portability, но его D8/D9/D6 не становятся онтологией AIFE.

## Решение

```text
ONE_CANONICAL_AIFE_SERVER_ROOT=YES
ONE_MONOLITH=NO
ONE_CONTAINER=NO
ONE_DATABASE=NO
HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
INITIAL_ONE_SERVER=ALLOWED
MULTI_NODE_IMPLEMENTATION_NOW=NO
APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
SECOND_PUBLIC_DI_ROUTE=NO
SECOND_AIFE_DATA_ROUTE=NO
DOMAIN_OWNS_SEMANTICS=YES_CANDIDATE
PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
SERVER_EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=NO
DATABASE_VENDOR_SELECTED=NO
TRANSPORT_SELECTED=NO
```

AIFE владеет общими механизмами исполнения, планирования, устойчивого runtime state,
publication/storage lifecycle, access и server operations. Домен владеет идентичностями,
provider semantics, normalization, validation, finality, revision/gap и derivation semantics.

## Физический корпус Data Bridge

После готовности и квалификации основы существующий и продолжающий расти физический корпус
Data Bridge должен пройти контролируемый переход под управляемый AIFE storage lifecycle.
Data Bridge остаётся ETH semantic authority, но не целевым основным physical warehouse.

```text
DATA_BRIDGE_DOMAIN_AUTHORITY_PRESERVED=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
DATA_BRIDGE_EXISTING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_GROWING_CORPUS_MIGRATION_TARGET=YES
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
MIGRATION_EXECUTED=NO
DELETE_OLD_DATA_BEFORE_PROOF=NO
LEGACY_READABILITY_PRESERVED=YES
F5M_STAGE_PRESENT=YES
```

Миграция является data-lifecycle transition, а не `COPY_FILES → DELETE_SOURCE`. Новый
маршрут входящих данных квалифицируется раньше массового backfill; финальный cutover требует
inventory, identity/content/range completeness, provenance, independent readback,
semantic read parity, rollbackability и owner gate.

## Планирование работы

```text
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
AIFE_SERVER_OWNS_GENERIC_WORK_EXECUTION=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
N8N_CANONICAL_SCHEDULER=NO
N8N_REQUIRED_FOR_PERIODIC_COLLECTION=NO
N8N_EXTERNAL_AUTOMATION_ALLOWED=YES
ONE_CANONICAL_WORK_SCHEDULING_ROUTE=YES
SERVER_RESTART_DOES_NOT_ERASE_SCHEDULE_SEMANTICS=YES
```

AIFE предоставляет clock/due evaluation, stable work identity, durable state,
ownership/lease-equivalent, checkpoint, retry/recovery и terminal state; домен задаёт cadence,
slot, backfill/finality/provider/gap/freshness semantics. `TaskManager.run_periodic_task`
должен быть согласован как существующий compatibility seam до реализации, а не обходиться
вторым scheduler route.

## Контур стандартов и контрактов

Server/Data Foundation использует **существующий** контур стандартов AIFE; параллельная
вселенная `STD-SERVER-*` по умолчанию запрещена. Шесть стандартов данных `0.1.0 / draft`
требуют owner alignment/disposition до F2. Утверждённые API, Security и Logging standards
являются ограничениями реализации по умолчанию.

```text
DATA_STANDARDS_ALIGNMENT_REQUIRED=YES
DATA_STANDARDS_ALIGNMENT_EXECUTED=NO
F2_ENTRY_REQUIRES_DATA_STANDARDS_DISPOSITION=YES
API_STANDARDS_DEFAULT_ACTION=CONFORM
SERVER_SECURITY_COMPLIANCE_REQUIRED=YES
SERVER_LOGGING_COMPLIANCE_REQUIRED=YES
SEMANTIC_CONTRACT_FIRST=YES
TRANSPORT_SELECTED=NO
F3_PUBLIC_INTERFACE_ENTRY_REQUIRES_COMPLIANCE_DISPOSITION=YES
NEW_STANDARD_DEFAULT_DECISION=DO_NOT_ADD
NEW_SERVER_STANDARD_CREATED=NO
NO_STANDARD_MUTATION_NOW=YES
```

ADR, standards и Artifact Contracts имеют разные роли: ADR фиксирует архитектурное решение;
standards задают повторно используемые обязательные правила; contracts задают точные
runtime/data boundaries. Порядок: architecture authority → Data standards alignment →
SERVER-domain governance → F2 contracts → transport/applicability decision → applicable
API/Security/Logging compliance → source implementation.

## Последствия

- один AIFE architectural route сохраняется;
- семантика ETH не переносится в physical storage;
- новый storage backend и multi-node deployment не требуют изменения semantic contracts;
- draft Data standards не выбирают vendor и не становятся production authority автоматически;
- approved API/Security/Logging нельзя игнорировать ради удобства реализации;
- новый standard создаётся только при доказанном reusable gap и owner approval;
- F5M обязателен до retirement прежнего physical warehouse и финального storage cutover.

## Отложенные решения

Не выбираются database/object-storage vendor, HTTP/REST/gRPC/WebSocket/CLI/IPC, scheduler
library, queue, Kubernetes, Kafka, Redis, ClickHouse, TimescaleDB, Iceberg или Delta Lake.
`OBJECT_BLOB_PLUS_PARQUET` остаётся только `ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED`.

## Граница реализации

```text
SERVER_IMPLEMENTATION_AUTHORIZED=NO
SCHEDULER_IMPLEMENTATION_AUTHORIZED=NO
DATABASE_CREATION_AUTHORIZED=NO
MIGRATION_EXECUTION_AUTHORIZED=NO
AIFE_WORKSPACE_MUTATION_AUTHORIZED=NO
P2_IMPLEMENTATION_AUTHORIZED=NO
R2_RESUME_AUTHORIZED=NO
PRODUCTION_ACTIVATION_AUTHORIZED=NO
```
