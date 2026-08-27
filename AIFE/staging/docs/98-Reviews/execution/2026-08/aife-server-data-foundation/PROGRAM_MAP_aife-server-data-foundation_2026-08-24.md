---
id: AIFE-SERVER-DATA-PROGRAM-MAP-2026-08-24
title: "Карта программы: Серверная и информационная основа AIFE"
version: '0.2'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-27
category: architecture
doc_type: spec
language: ru
tags: [program-map, execution, server, data, foundation, scalability]
authority_reference:
  - AGENTS.md
  - genome/registries/STANDARDS_REGISTRY.md
  - genome/registries/ADR_REGISTRY.md
  - genome/registries/CONTRACTS_REGISTRY.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/governance/STD-GOVERNANCE-NAMING-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
---

# Карта программы: Серверная и информационная основа AIFE

## Полномочная база и архитектурные ограничения

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_WORKTREE_CLEAN=true
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
DOMAIN_OWNS_SEMANTICS=YES
DATABASE_VENDOR_SELECTED=NO
TRANSPORT_SELECTED=NO
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
```

`STD-ARCH-PATTERNS-001` и `ADR-INITIALIZER-CORE-001` сохраняют действующий маршрут
`Presentation → Manager → Service → Repository/Gateway → Adapter`, а `AppContext` остаётся
единственной публичной типизированной поверхностью исполнения. F0 не реализует сервер и не
создаёт второй маршрут данных или зависимостей.

## Три основных вопроса

```text
QUESTION_1=HOW_DATA_IS_ACQUIRED_AND_DURABLY_STORED
QUESTION_2=HOW_PROVEN_ETH_D8_D9_D6_MECHANISMS_ARE_REUSED_AS_REFERENCE_WITHOUT_BECOMING_AIFE_PLATFORM_PRIMITIVES
QUESTION_3=HOW_AIFE_CONSUMERS_CONNECT_TO_AIFE_SERVER_ROOT_THROUGH_EXISTING_AIFE_ARCHITECTURAL_BOUNDARIES_WITH_HORIZONTAL_SCALE_BY_DESIGN
```

## Целевое распределение ответственности

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS
ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
ONE_CANONICAL_WORK_SCHEDULING_ROUTE=YES
N8N_CANONICAL_SCHEDULER=NO
N8N_REQUIRED_FOR_PERIODIC_COLLECTION=NO
N8N_EXTERNAL_AUTOMATION_ALLOWED=YES
```

После будущего переноса физического корпуса чтение концептуально сохраняет один маршрут:

```text
AIFE consumer
→ AIFE semantic access boundary
→ ETH domain integration
→ Data Bridge domain semantics/resolution
→ AIFE-managed physical storage mechanism
```

То есть AIFE предоставляет общий механизм доступа и хранения, а `Data Bridge` сохраняет
семантику ETH и доменное разрешение.

## Этапы программы

| Этап | Назначение | Обязательная зависимость |
| --- | --- | --- |
| F0 | `BRIDGE_AND_DURABLE_PLANNING_AUTHORITY` | текущий пакет планирования и двухэтапная интеграция владельцем |
| F1 | `SERVER_DATA_FOUNDATION_OWNER_ARCHITECTURE` | каноническая интеграция F0 в AIFE |
| F1G | `SERVER_CONTRACT_DOMAIN_OWNER_GOVERNANCE_GATE` | требуется, если `SERVER` всё ещё отсутствует в доменах контрактов |
| F2 | `MINIMUM_SERVER_DATA_CONTRACTS` | F1 + `DATA_STANDARDS_ALIGNMENT_GATE` + F1G при необходимости |
| F3 | `AIFE_SERVER_ROOT_SOURCE_SKELETON` | F2 + решение о применимости транспорта + `API_SECURITY_LOGGING_COMPLIANCE_GATE` |
| F4 | `FIRST_DOMAIN_INTEGRATION_ETH` | F3 |
| F5 | `ETH_HIGH_CARDINALITY_P2_PHYSICAL_LIFECYCLE` | F4 + отдельная полномочная документация ETH P2 |
| F5M | `ETH_EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER` | F5 + квалифицированный новый физический маршрут |
| F6/F7 | приёмка потребителя и физическая/горизонтальная квалификация | F4–F5M в зависимости от вида приёмки |
| F8 | поздняя активация или переключение | только отдельное разрешение владельца |

```text
F5M_STAGE_PRESENT=YES
F5M_REQUIRED_BEFORE_FINAL_PHYSICAL_WAREHOUSE_RETIREMENT=YES
F5M_REQUIRED_BEFORE_F8_FINAL_STORAGE_CUTOVER=YES
PARTIAL_CONSUMER_ACCEPTANCE=ALLOWED_ON_QUALIFIED_BOUNDED_DATASET
FULL_HISTORY_MIGRATION_ACCEPTANCE=REQUIRES_F5M
LEGACY_PHYSICAL_RETIREMENT_BEFORE_F5M=FORBIDDEN
```

## Целевое состояние физического корпуса данных

Накопленный и продолжающий накапливаться физический корпус `Data Bridge` должен после
готовности и квалификации основы перейти под управляемый AIFE жизненный цикл хранения.
Семантические полномочия ETH при этом не переносятся. Точный перечень миграции строится
заново в будущей задаче и может включать `data/**`, `history/**`, `archive/**`, исторические
слои `derivatives/**`, `options/**`, `liquidity/**`, ограниченную историю Git WARM и объекты
GitHub Release с глубокой историей.

```text
DATA_BRIDGE_EXISTING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_GROWING_CORPUS_MIGRATION_TARGET=YES
MIGRATION_EXECUTED=NO
CORRECT_FORWARD_COLLECTION_FIRST=YES
FULL_BACKFILL_BEFORE_NEW_ROUTE_CAN_EXIST=NO
DELETE_OLD_DATA_BEFORE_MIGRATION_PROOF=NO
DISABLE_LEGACY_READ_ROUTE_BEFORE_READ_PARITY=NO
CUTOVER_BEFORE_COMPLETENESS_PROOF=NO
MIGRATION_REQUIRES_INDEPENDENT_READBACK=YES
MIGRATION_REQUIRES_SEMANTIC_READABILITY_PROOF=YES
ROLLBACKABILITY_BEFORE_FINAL_RETIREMENT=REQUIRED
LEGACY_READABILITY_PRESERVED=YES
PRODUCTION_ROUTE_CHANGED=NO
```

Рекомендуемая последовательность будущего переноса:

```text
AIFE_STORAGE_FOUNDATION_READY
→ NEW_PHYSICAL_ROUTE_QUALIFIED
→ NEW_INCOMING_PUBLICATION_TO_AIFE_ROUTE
→ CONTROLLED_EXISTING_CORPUS_BACKFILL
→ INDEPENDENT_READBACK
→ COMPLETENESS_RECONCILIATION
→ SEMANTIC_READ_PARITY_PROOF
→ CANONICAL_PHYSICAL_ROUTE_CUTOVER
→ LEGACY_READABILITY_RETENTION
→ OWNER_AUTHORIZED_LEGACY_PHYSICAL_RETIREMENT
```

Сначала доказывается корректный маршрут новых входящих данных, затем переносится накопленная
история. Прежние байты и маршрут чтения нельзя выводить до доказательства полноты и паритета.

## Планирование периодической работы

Каноническая модель периодической работы:

```text
CLOCK
→ DUE_POLICY_EVALUATION
→ DETERMINISTIC_SLOT
→ STABLE_WORK_ID
→ DURABLE_WORK_STATE
→ WORKER_CLAIM
→ EXECUTION
→ CHECKPOINT
→ TERMINAL_STATE
```

AIFE владеет общим механизмом времени, устойчивого состояния, владения, повторов и
восстановления; домен определяет возможность, периодичность, слот, допустимость обратного
заполнения, финальность, источник, значение пропуска и окно свежести. Независимый `cron`
на каждом узле и `n8n` не являются полномочной моделью.

```text
SERVER_RESTART_DOES_NOT_ERASE_SCHEDULE_SEMANTICS=YES
SAME_LOGICAL_SLOT_DUPLICATE_EXECUTION=PREVENT_OR_IDEMPOTENTLY_COLLAPSE
SCHEDULING_BOUNDARY_MERGED_WITH_SERVER_WORK_CONTRACT=YES_CANDIDATE
SEPARATE_SCHEDULER_ARTIFACT_CONTRACT=NOT_REQUIRED_YET
```

Существующий `TaskManager.run_periodic_task` остаётся совместимым помощником, а не действующим
контрактом планировщика; перед реализацией эту границу нужно отдельно согласовать.

## Контур стандартов и соответствия

Архитектура не подгоняется под случайные свойства реализации. Черновые стандарты данных
выравниваются с одобренной архитектурой и доказанными требованиями, а утверждённые стандарты
API, безопасности и журналирования ограничивают будущую реализацию по умолчанию.

### Стандарты данных

Шесть текущих стандартов имеют `0.1.0 / draft`:
`STD-DATA-MGMT-001`, `STD-DATA-SCHEMA-001`, `STD-DATA-MIGRATION-001`,
`STD-DATA-VALIDATION-001`, `STD-DATA-RETENTION-001`, `STD-DATA-BACKUP-001`.
До F2 каждый должен получить решение владельца
`AS_IS|AMEND_REQUIRED|SPLIT_REQUIRED|MERGE_REQUIRED|DEFER`.

```text
DATA_STANDARDS_ALIGNMENT_REQUIRED=YES
DATA_STANDARDS_ALIGNMENT_BEFORE_F2=YES
DATA_STANDARDS_AUTO_APPROVED=NO
DATA_STANDARDS_AUTO_PROMOTED=NO
DATA_STANDARDS_IMPLEMENTATION_CAN_SILENTLY_OVERRIDE=NO
DATA_STANDARDS_ARE_NOT_AUTO_PRODUCTION_AUTHORITY=YES
F2_ENTRY_REQUIRES_DATA_STANDARDS_DISPOSITION=YES
DATA_SCHEMA_STANDARD_MUST_NOT_IMPLY_UNIVERSAL_DATABASE_VENDOR=YES
RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES
BACKUP_EXISTS != RESTORE_IS_PROVEN
DATA_STANDARDS_ALIGNMENT_SELECTS_DATABASE_VENDOR=NO
```

Будущее рассмотрение проверяет: классы состояния и разделение семантики с физическим
хранением в `STD-DATA-MGMT-001`; идентичность, версию и развитие схемы без привязки к
поставщику БД в `STD-DATA-SCHEMA-001`; различение миграции схемы, данных, физической
внутренней реализации, исторического обратного заполнения и переключения полномочий в
`STD-DATA-MIGRATION-001`; разделение общей и доменной проверки в
`STD-DATA-VALIDATION-001`; логические роли `HOT/WARM/COLD/ARCHIVAL/RETIREMENT/PURGE`
без автоматического удаления по возрасту в `STD-DATA-RETENTION-001`; доказуемое
независимое восстановление в `STD-DATA-BACKUP-001`.

### API, безопасность, журналирование и наблюдаемость

Набор `STD-API-DESIGN-001`, `STD-API-DOCS-001`, `STD-API-ERRORS-001`,
`STD-API-RATE-001`, `STD-API-VERSIONING-001` имеет `1.0.0 / approved`.
`STD-LOG-001` имеет `2.3.0 / approved`. Применимые `STD-SEC-AUTH-001`,
`STD-SEC-ENCRYPTION-001`, `STD-SEC-LOG-001`, `STD-SEC-PRINCIPLES-001`,
`STD-SEC-REVIEW-001`, `STD-SEC-SECRETS-001`, `STD-SEC-VULN-001` имеют статус
`approved`. `STD-MON-HEALTH-001` и `STD-MON-METRICS-001` остаются `0.1.0 / draft`.

```text
API_STANDARDS_COMPLIANCE_REQUIRED=YES
API_STANDARDS_DEFAULT_ACTION=CONFORM
API_STANDARDS_IMPLEMENTATION_MAY_IGNORE=NO
API_STANDARD_AMENDMENT_ALLOWED=ONLY_IF_PROVEN_GAP_AND_OWNER_APPROVED
SERVER_SECURITY_COMPLIANCE_REQUIRED=YES
SERVER_LOGGING_COMPLIANCE_REQUIRED=YES
LOGGING_STANDARD=STD-LOG-001
MONITORING_STANDARDS_STATUS=DRAFT
MONITORING_ALIGNMENT_REQUIRED_BEFORE_PRODUCTION_OBSERVABILITY=YES
SEMANTIC_CONTRACT_FIRST=YES
TRANSPORT_SELECTION_AFTER_SEMANTIC_BOUNDARY=YES
API_COMPLIANCE_AFTER_TRANSPORT_APPLICABILITY_IS_KNOWN=YES
F3_PUBLIC_INTERFACE_ENTRY_REQUIRES_COMPLIANCE_DISPOSITION=YES
```

Стандарты, ADR и `Artifact Contract` не взаимозаменяемы: ADR фиксирует архитектурное решение,
стандарты задают повторно используемые обязательства, а контракты — точные границы исполнения
и данных. Разрыв классифицируется одним из точных значений:

```text
IMPLEMENTATION_DEFECT
CONTRACT_DEFECT
STANDARD_GAP
STANDARD_NOT_APPLICABLE
OWNER_DECISION_REQUIRED
```

Новый `STD-SERVER-*` допустим только при доказанном повторно используемом разрыве и явном
разрешении владельца.

```text
NEW_STANDARD_DEFAULT_DECISION=DO_NOT_ADD
NEW_SERVER_STANDARD_CREATED=NO
SERVER_DOMAIN_GOVERNANCE_SEPARATE=YES
DATA_STANDARDS_ALIGNMENT_PUBLICATION=F5R_OWNER_BOUNDED
NO_IMPLEMENTATION_NOW=YES
MIGRATION_SCHEDULING_DECISIONS_PRESERVED=YES
```

## Канонические Server contracts

Домен `SERVER` уже допущен governance-стандартом и текущий owner layer содержит шесть
существующих contracts. F5R не создаёт новый parallel `CONTRACT-DATA-*` route.

```text
SERVER_DOMAIN_ADMITTED=YES
SERVER_CONTRACT_COUNT=6
CONTRACT_SERVER_WORK=CONTRACT-SERVER-WORK-001
CONTRACT_SERVER_SCHEDULING=CONTRACT-SERVER-SCHEDULING-001
CONTRACT_SERVER_EXECUTION=CONTRACT-SERVER-EXECUTION-001
CONTRACT_SERVER_PUBLICATION=CONTRACT-SERVER-PUBLICATION-001
CONTRACT_SERVER_STORAGE=CONTRACT-SERVER-STORAGE-001
CONTRACT_SERVER_ACCESS=CONTRACT-SERVER-ACCESS-001
F5R_CONTRACTS_AMENDED=STORAGE+PUBLICATION+ACCESS
F5R_CONTRACTS_REVIEWED_NO_CHANGE=WORK+EXECUTION+SCHEDULING
NEW_PARALLEL_SERVER_CONTRACT=NO
```

Work/Execution/Scheduling сохраняют уже опубликованные generic identity, claim/lease/fence
и due-materialization boundaries. Storage/Publication/Access получают только F5R bindings,
принадлежащие их существующей ответственности.

## F5R owner publication и downstream gates

```text
F5R_RESEARCH=COMPLETE
F5R_DUAL_RESEARCH=COMPLETE
F5R_CONSOLIDATION=COMPLETE
F5R_OWNER_ARCHITECTURE_PUBLICATION=COMPLETE_AFTER_THIS_TASK_PASSES
P1_DUAL_RESEARCH_EVIDENCE=ACCEPTED
P1_RESEARCH_GATE=SATISFIED_BY_OWNER_DECISION
THIRD_RESEARCH_REQUIRED=NO

F5=NEXT_IMPLEMENTATION_PLANNING_AND_QUALIFICATION_STAGE
F5M=LATER_EXISTING_CORPUS_MIGRATION_AND_CUTOVER
F5M_DEPENDS_ON_QUALIFIED_F5=YES
F5_MASS_BACKFILL_AS_FIRST_ROUTE_TEST=FORBIDDEN
F5_RESEARCH_REQUIRED=NO
F5_DEV_TZ_CREATION_ALLOWED=YES_AS_NEXT_STEP_AFTER_OWNER_PUBLICATION
F5_DEV_TZ_CREATED_BY_THIS_PUBLICATION=NO
F5_IMPLEMENTATION_ALLOWED_BY_THIS_PUBLICATION=NO
F5M_ALLOWED_BY_THIS_PUBLICATION=NO
PRODUCTION_DEPLOYMENT_ALLOWED_BY_THIS_PUBLICATION=NO
```

Measurement/expansion gates остаются открыты и не считаются сработавшими: object/blob product,
exact Parquet layout and compression, numeric throughput/latency SLO, numeric RPO/RTO and HA
topology выбираются/квалифицируются только в последующих owner-authorized contours. PostgreSQL
остаётся expansion candidate, требуемым перед shared multi-node control qualification;
DuckDB — preferred analytical/backtest candidate, но не F5 physical-storage closure dependency;
Iceberg/ClickHouse/Redis/broker/search/vector остаются deferred до documented triggers.

## Обязательная последовательность после канонической интеграции F0

```text
F1_ARCHITECTURE_AUTHORITY_CURRENTIZATION
→ DATA_STANDARDS_ALIGNMENT_GATE
→ F1G_SERVER_DOMAIN_GOVERNANCE_EXTENSION_COMPLETE
→ F2_MINIMUM_ARTIFACT_CONTRACTS
→ TRANSPORT_APPLICABILITY_OWNER_DECISION
→ API_SECURITY_LOGGING_COMPLIANCE_GATE
→ F3_SERVER_ROOT_SOURCE_SKELETON
→ F4_FIRST_DOMAIN_INTEGRATION_ETH
→ F5_ETH_HIGH_CARDINALITY_P2_PHYSICAL_LIFECYCLE
→ F5M_ETH_EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER
→ F6_F7_ACCEPTANCE_AND_QUALIFICATION
→ F8_ONLY_IF_SEPARATELY_AUTHORIZED
```

```text
DATA_STANDARDS_ALIGNMENT_TASK=AIFE-SERVER-DATA-FOUNDATION-DATA-STANDARDS-ALIGNMENT-V1
SERVER_DOMAIN_GOVERNANCE_STATUS=COMPLETE
INTERFACE_COMPLIANCE_TASK=AIFE-SERVER-DATA-FOUNDATION-API-SECURITY-LOGGING-COMPLIANCE-V1
NEXT_RECOMMENDED_TASK=CREATE_AND_OWNER_REVIEW_F5_IMPLEMENTATION_DEV_TZ
FOLLOWING_TASK=F5_IMPLEMENTATION_ONLY_AFTER_DEV_TZ_AND_OWNER_EXECUTION_AUTHORITY
```

F5R owner publication изменяет только governance owners и generated registry projections. Она
не меняет transport/backend runtime, server source, planner runtime, `n8n`, текущий collection
route, F5/F5M data или production state.
