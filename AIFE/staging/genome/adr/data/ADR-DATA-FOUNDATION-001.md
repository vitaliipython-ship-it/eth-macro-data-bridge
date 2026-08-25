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

AIFE уже использует утверждённый маршрут `Manager → Service → Repository`, `core/data/**`,
`AppContext` как единственную публичную типизированную поверхность исполнения и внутренний
`DependencyManager`. Конкретная топология БД и активный `Artifact Contract` для серверных
данных не выбраны. ETH Data Bridge доказал полезные механизмы идентичности работы,
контрольных точек и восстановления, публикации, независимого чтения и переносимости хранения,
но D8/D9/D6 не становятся онтологией AIFE.

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

AIFE владеет общими механизмами исполнения, планирования, устойчивого состояния исполнения,
жизненного цикла публикации и хранения, доступа и серверных операций. Домен владеет
идентичностями, правилами поставщиков, нормализацией, проверкой, финальностью, правилами
ревизий и пропусков, а также доменными производными.

## Физический корпус Data Bridge

После готовности и квалификации основы существующий и продолжающий расти физический корпус
Data Bridge должен пройти контролируемый переход под управляемый AIFE жизненный цикл хранения.
Data Bridge остаётся семантическим полномочным источником ETH, но не целевым основным
физическим складом истории.

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

Миграция является переходом жизненного цикла данных, а не схемой
`COPY_FILES → DELETE_SOURCE`. Новый маршрут входящих данных квалифицируется раньше массового
обратного заполнения. Финальное переключение требует перечня миграции, доказательства
идентичности, целостности и полноты диапазонов, сохранения происхождения, независимого чтения,
семантического паритета чтения, обратимости и отдельного шлюза владельца.

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

AIFE предоставляет общий механизм часов и вычисления наступившей работы, стабильную
идентичность, устойчивое состояние, эквивалент владения или аренды, контрольную точку,
повторы, восстановление и конечное состояние. Домен задаёт периодичность, слот, допустимость
обратного заполнения, финальность, источник, трактовку пропусков и окно свежести.
`TaskManager.run_periodic_task` должен быть согласован как существующая граница совместимости
до реализации; обходить его вторым маршрутом планирования нельзя.

## Контур стандартов и контрактов

Server/Data Foundation использует **существующий** контур стандартов AIFE; параллельная
вселенная `STD-SERVER-*` по умолчанию запрещена. Шесть стандартов данных `0.1.0 / draft`
требуют отдельного выравнивания и решения владельца до F2. Утверждённые стандарты API,
безопасности и журналирования являются ограничениями будущей реализации по умолчанию.

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

ADR, стандарты и `Artifact Contract` имеют разные роли: ADR фиксирует архитектурное решение;
стандарты задают повторно используемые обязательные правила; контракты задают точные границы
исполнения и данных. Порядок: архитектурная полномочная база → выравнивание стандартов данных
→ правила домена `SERVER` → контракты F2 → решение о применимости транспорта → проверка
соответствия API, безопасности и журналирования → реализация исходного кода.

## Последствия

- сохраняется один архитектурный маршрут AIFE;
- семантика ETH не переносится в физическое хранилище;
- новая внутренняя реализация хранения и многоузловое развёртывание не требуют изменения
  семантических контрактов;
- черновые стандарты данных не выбирают поставщика и не становятся боевой полномочной базой
  автоматически;
- утверждённые стандарты API, безопасности и журналирования нельзя игнорировать ради удобства
  реализации;
- новый стандарт создаётся только при доказанном повторно используемом разрыве и разрешении
  владельца;
- F5M обязателен до выведения прежнего физического склада и финального переключения хранения.

## Отложенные решения

Не выбираются поставщик базы данных или объектного хранилища, HTTP/REST/gRPC/WebSocket/CLI/IPC,
библиотека планировщика, очередь, Kubernetes, Kafka, Redis, ClickHouse, TimescaleDB, Iceberg
или Delta Lake. `OBJECT_BLOB_PLUS_PARQUET` остаётся только
`ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED`.

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
