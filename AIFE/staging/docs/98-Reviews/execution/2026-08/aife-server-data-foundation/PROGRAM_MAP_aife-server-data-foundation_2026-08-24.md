---
id: AIFE-SERVER-DATA-PROGRAM-MAP-2026-08-24
title: "Карта программы: Серверная и информационная основа AIFE"
version: '0.4'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-28
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
AIFE_DELIVERY_STATUS=F5P_DEPLOYMENT_ARCHITECTURE_RESEARCH_CANDIDATE_F5_IMPLEMENTATION_BLOCKED_PENDING_DEV_TZ
```

`STD-ARCH-PATTERNS-001` и `ADR-INITIALIZER-CORE-001` сохраняют действующий маршрут
`Presentation → Manager → Service → Repository/Gateway → Adapter`, а `AppContext` остаётся
единственной публичной типизированной поверхностью исполнения. F5R/F5P не реализуют server
runtime и не создают второй маршрут данных или зависимостей.

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
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES
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

Последовательность F0–F4 ниже сохранена как **HISTORICAL / SATISFIED** program lineage.
Она не является текущим требованием повторно пройти уже закрытые architecture-selection
gates. Текущая точка входа после F5P publication/readback closure — отдельный F5 DEV_TZ.

| Этап | Назначение | Обязательная зависимость |
| --- | --- | --- |
| F0 | `BRIDGE_AND_DURABLE_PLANNING_AUTHORITY` | historical/satisfied |
| F1 | `SERVER_DATA_FOUNDATION_OWNER_ARCHITECTURE` | historical/satisfied |
| F1G | `SERVER_CONTRACT_DOMAIN_OWNER_GOVERNANCE_GATE` | historical/satisfied |
| F2 | `MINIMUM_SERVER_DATA_CONTRACTS` | historical/satisfied |
| F3 | `AIFE_SERVER_ROOT_SOURCE_SKELETON` | historical/satisfied |
| F4 | `FIRST_DOMAIN_INTEGRATION_ETH` | historical/satisfied |
| F5P | `SERVER_WORKSPACE_AND_DEPLOYMENT_LAYOUT_GOVERNANCE` | F5R closure; publication/readback required |
| F5 | `NEW_INCOMING_PHYSICAL_LIFECYCLE_QUALIFICATION` | F5P closure + separate F5 DEV_TZ + owner execution authority |
| F5M | `EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER` | qualified F5 new physical route |
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
SCHEDULING_BOUNDARY=CONTRACT-SERVER-SCHEDULING-001
SCHEDULING_BOUNDARY_MERGED_WITH_SERVER_WORK_CONTRACT=NO
SEPARATE_SCHEDULER_ARTIFACT_CONTRACT=EXISTS_AND_REGISTERED
```

Существующий `TaskManager.run_periodic_task` остаётся совместимым helper, а каноническая
scheduling/due-materialization boundary уже принадлежит
`CONTRACT-SERVER-SCHEDULING-001`. Work и Execution сохраняют свои отдельные owner boundaries.

## Контур стандартов и соответствия

Архитектура не подгоняется под случайные свойства реализации. Черновые стандарты данных
выравниваются с одобренной архитектурой и доказанными требованиями, а утверждённые стандарты
API, безопасности и журналирования ограничивают будущую реализацию по умолчанию.

### Стандарты данных

После F5R semantic currentization шесть текущих DATA standards остаются `draft` и имеют
следующие owner versions:

```text
STD-DATA-MGMT-001=0.3.0/draft
STD-DATA-SCHEMA-001=0.3.0/draft
STD-DATA-MIGRATION-001=0.2.0/draft
STD-DATA-VALIDATION-001=0.2.0/draft
STD-DATA-RETENTION-001=0.3.0/draft
STD-DATA-BACKUP-001=0.3.0/draft
```

Исторический pre-F2 alignment gate закрыт опубликованным owner architecture route. DATA
standards не выбирают product/vendor, не переопределяют active ADR и не получают
автоматический `approved` status.

```text
DATA_STANDARDS_ALIGNMENT_REQUIRED=YES_SATISFIED_FOR_CURRENT_F5R_SCOPE
DATA_STANDARDS_ALIGNMENT_BEFORE_F2=HISTORICAL_SATISFIED
DATA_STANDARDS_AUTO_APPROVED=NO
DATA_STANDARDS_AUTO_PROMOTED=NO
DATA_STANDARDS_IMPLEMENTATION_CAN_SILENTLY_OVERRIDE=NO
DATA_STANDARDS_ARE_NOT_AUTO_PRODUCTION_AUTHORITY=YES
F2_ENTRY_REQUIRES_DATA_STANDARDS_DISPOSITION=HISTORICAL_SATISFIED
DATA_SCHEMA_STANDARD_MUST_NOT_IMPLY_UNIVERSAL_DATABASE_VENDOR=YES
RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES
BACKUP_EXISTS != RESTORE_IS_PROVEN
DATA_STANDARDS_ALIGNMENT_SELECTS_DATABASE_VENDOR=NO
SERVER_DATA_ARCHITECTURE_OWNER=ADR-DATA-FOUNDATION-001
```

Current owner semantics: `STD-DATA-MGMT-001` владеет generic lifecycle; schema standard
разделяет required Parquet bulk-tabular format и unselected product/layout; migration,
validation, retention и backup сохраняют domain authority split и active ADR precedence.

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
F3_PUBLIC_INTERFACE_ENTRY_REQUIRES_COMPLIANCE_DISPOSITION=HISTORICAL_SATISFIED
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

Домен `SERVER` уже допущен governance-стандартом. F5P добавляет один deployment contract,
не создавая parallel `CONTRACT-DATA-*` route и не меняя шесть существующих Server contracts.

```text
SERVER_DOMAIN_ADMITTED=YES
SERVER_CONTRACT_COUNT=7
CONTRACT_SERVER_WORK=CONTRACT-SERVER-WORK-001@0.1.0/draft
CONTRACT_SERVER_SCHEDULING=CONTRACT-SERVER-SCHEDULING-001@0.1.0/draft
CONTRACT_SERVER_EXECUTION=CONTRACT-SERVER-EXECUTION-001@0.2.0/draft
CONTRACT_SERVER_PUBLICATION=CONTRACT-SERVER-PUBLICATION-001@0.3.0/draft
CONTRACT_SERVER_STORAGE=CONTRACT-SERVER-STORAGE-001@0.3.0/draft
CONTRACT_SERVER_ACCESS=CONTRACT-SERVER-ACCESS-001@0.2.0/draft
CONTRACT_SERVER_DEPLOYMENT=CONTRACT-SERVER-DEPLOYMENT-001@0.1.0/draft
F5R_POST_PUBLICATION_REPAIR_CONTRACTS_AMENDED=STORAGE+PUBLICATION+EXECUTION
F5R_POST_PUBLICATION_REPAIR_CONTRACTS_REVIEWED_NO_CHANGE=WORK+SCHEDULING+ACCESS
F5P_EXISTING_SERVER_CONTRACTS_AMENDED=NONE
NEW_PARALLEL_SERVER_CONTRACT=NO
```

Current bindings remain divided by owner: Storage materializes bounded batching and
content-collision evidence; Publication owns idempotent/fail-closed same-target outcome;
Execution preserves current fencing plus the exact resolved reproducible read set. Access
continues to expose PIT/read-set identity without taking execution ownership. Deployment owns
only source→release→operational-root→activation→receipt→rollback binding.

## F5P workspace/deployment architecture

```text
F5P_RESEARCH=COMPLETE_CANDIDATE_PENDING_REMOTE_PUBLICATION_READBACK
F5P_FINAL_CLOSURE=PENDING_REMOTE_READBACK
FHS_LAYOUT_MODEL=AIFE_SERVICE_LAYOUT
CANONICAL_SERVER_SOURCE_ROOT=server/
APPLICATION_SERVICE_ROOT=server/application/
CONTROL_STATE_APPLICATION_OWNER=server/application/
CONTROL_STATE_PERSISTENCE_ABSTRACTION_OWNER=core/data/**
CONTROL_STATE_PERSISTENCE_ADAPTER_OWNER=core/data/adapters/**
CONTROL_STATE_IMPLEMENTATION_ROOT=DEV_TZ_IMPLEMENTATION_BOUND_WITH_CANONICAL_OWNER_CHAIN_DEFINED
CONTROL_STATE_SCHEMA_MIGRATION_OWNER=core/data/**
CONTROL_STATE_REUSES_CORE_DATA_SUBSTRATE=YES
NEW_GENERIC_PERSISTENCE_FRAMEWORK=NO
CONTROL_STATE_AND_BULK_STORAGE_OWNER_COLLAPSED=NO
CONTROL_STATE_SOURCE_PLACEMENT_REVIEW=PASS
```

The exact thin Server-specific persistence binding module remains DEV_TZ implementation-bound;
owner chain is already fixed and does not require a new `server/control/**` package or an
amendment to existing Work/Execution/Publication/Storage contracts.

### Canonical service filesystem

```text
CANONICAL_INSTALL_ROOT=/opt/aife
CANONICAL_RELEASE_ROOT=/opt/aife/releases
CURRENT_RELEASE_POINTER=/opt/aife/current
PREVIOUS_RELEASE_POINTER=/opt/aife/previous
CANONICAL_CONFIG_ROOT=/etc/aife
CANONICAL_SECRET_ROOT=/etc/aife/secrets
CANONICAL_STATE_ROOT=/var/lib/aife
CANONICAL_CONTROL_DB_PATH=/var/lib/aife/control/aife-control.sqlite3
CHECKPOINT_ROOT=/var/lib/aife/checkpoints
CANONICAL_SPOOL_ROOT=/var/spool/aife
INGEST_ROOT=/var/spool/aife/ingest
CANONICAL_CACHE_ROOT=/var/cache/aife
CANONICAL_DATA_ROOT=/var/lib/aife/data
CANONICAL_OBJECT_ROOT=/var/lib/aife/data/objects
CANONICAL_PARQUET_ROOT=/var/lib/aife/data/parquet
CANONICAL_MANIFEST_ROOT=/var/lib/aife/data/manifests
QUARANTINE_ROOT=/var/lib/aife/quarantine
CANONICAL_LOG_ROOT=/var/log/aife
CANONICAL_DEPLOYMENT_MAP_PATH=/etc/aife/deployment-map.json
CANONICAL_DEPLOYMENT_RECEIPT_ROOT=/var/lib/aife/deployments/receipts
CANONICAL_DEPLOYMENT_RECEIPT_PATH=/var/lib/aife/deployments/receipts/<deployment-id>.json
DATA_ROOT_MAY_BE_DEDICATED_MOUNT=YES
ROOT_FILESYSTEM_COLOCATION_REQUIRED=NO
DATA_MOUNT_PREFLIGHT_REQUIRED=YES
FREE_SPACE_PREFLIGHT_REQUIRED=YES
```

`/opt/aife` is the immutable release carrier only. Source, release, config/secrets,
transactional control state, spool/cache, bulk objects/Parquet/manifests and logs remain
separate physical classes. The deployment map declares logical roots, active release/control
backend and physical mount/storage backing so operators do not infer authority from paths.

### Installation, upgrade and rollback

```text
IMMUTABLE_RELEASE_MODEL=YES
DIRECT_PRODUCTION_EXECUTION_FROM_GIT_CHECKOUT=NO
PRODUCTION_UPDATE_BY_GIT_PULL=NO
ATOMIC_RELEASE_ACTIVATION=YES
DEPLOYMENT_MAP_REQUIRED=YES
DEPLOYMENT_RECEIPT_REQUIRED=YES
SILENT_DATABASE_DOWNGRADE=FORBIDDEN
```

Conceptual order:

```text
HOST_PREFLIGHT
→ SERVICE_ACCOUNT
→ DIRECTORY_LAYOUT
→ PERMISSIONS
→ MOUNT_AND_SPACE_PREFLIGHT
→ RELEASE_DIGEST_VERIFICATION
→ SIDE_BY_SIDE_IMMUTABLE_INSTALL
→ CONFIG_INSTALL
→ CONTROL_BACKEND_INIT
→ SCHEMA_COMPATIBILITY_OR_MIGRATION
→ SERVICE_REGISTRATION
→ PRE_ACTIVATION_VALIDATION
→ ATOMIC_ACTIVATION
→ HEALTH
→ WRITE_READBACK
→ DEPLOYMENT_RECEIPT
```

Code release identity, control schema identity, config identity and data generation identity
remain independent. Rollback must verify all applicable compatibility rather than silently
rolling database schema backwards.

## F5R owner publication и downstream gates

```text
F5R_RESEARCH=COMPLETE
F5R_DUAL_RESEARCH=COMPLETE
F5R_CONSOLIDATION=COMPLETE
F5R_OWNER_ARCHITECTURE_PUBLICATION=COMPLETE
F5R_GOVERNANCE_SEMANTIC_CURRENTIZATION=COMPLETE
F5R_GOVERNANCE_PUBLICATION_FINAL_CLOSURE=COMPLETE
P1_DUAL_RESEARCH_EVIDENCE=ACCEPTED
P1_RESEARCH_GATE=SATISFIED_BY_OWNER_DECISION
THIRD_RESEARCH_REQUIRED=NO

F5=NEXT_IMPLEMENTATION_PLANNING_AND_QUALIFICATION_STAGE
F5M=LATER_EXISTING_CORPUS_MIGRATION_AND_CUTOVER
F5M_DEPENDS_ON_QUALIFIED_F5=YES
F5_MASS_BACKFILL_AS_FIRST_ROUTE_TEST=FORBIDDEN
F5_RESEARCH_REQUIRED=NO
F5_OWNER_ARCHITECTURE_REQUIRED=NO
F5_GOVERNANCE_REPAIR_REQUIRED=NO
F5_DEV_TZ_CREATION_ALLOWED=YES_AS_NEXT_SEPARATE_OWNER_TASK_AFTER_F5P_REMOTE_CLOSURE
F5_DEV_TZ_CREATED=NO
F5_IMPLEMENTATION_ALLOWED=NO_PENDING_F5_DEV_TZ_AND_OWNER_EXECUTION_AUTHORITY
F5M_ALLOWED=NO
PRODUCTION_DEPLOYMENT_ALLOWED=NO
```

Measurement/expansion gates остаются открыты и не считаются сработавшими: object/blob product,
exact Parquet layout and compression, numeric throughput/latency SLO, numeric RPO/RTO and HA
topology выбираются/квалифицируются только в последующих owner-authorized contours. PostgreSQL
остаётся expansion candidate, требуемым перед shared multi-node control qualification;
DuckDB — preferred analytical/backtest candidate, но не F5 physical-storage closure dependency;
Iceberg/ClickHouse/Redis/broker/search/vector остаются deferred до documented triggers.

## Обязательная последовательность после канонической интеграции F0

Следующая цепочка сохраняется как **HISTORICAL program lineage** для уже завершённых F1–F4
и как current forward ordering начиная с F5P/F5. Она не возвращает текущую архитектуру к F3
selection authority.

```text
F1_ARCHITECTURE_AUTHORITY_CURRENTIZATION [HISTORICAL_SATISFIED]
→ DATA_STANDARDS_ALIGNMENT_GATE [HISTORICAL_SATISFIED]
→ F1G_SERVER_DOMAIN_GOVERNANCE_EXTENSION_COMPLETE [HISTORICAL_SATISFIED]
→ F2_MINIMUM_ARTIFACT_CONTRACTS [HISTORICAL_SATISFIED]
→ TRANSPORT_APPLICABILITY_OWNER_DECISION [HISTORICAL_SATISFIED]
→ API_SECURITY_LOGGING_COMPLIANCE_GATE [HISTORICAL_SATISFIED]
→ F3_SERVER_ROOT_SOURCE_SKELETON [HISTORICAL_SATISFIED]
→ F4_FIRST_DOMAIN_INTEGRATION_ETH [HISTORICAL_SATISFIED]
→ F5P_SERVER_WORKSPACE_AND_DEPLOYMENT_LAYOUT_GOVERNANCE [PUBLICATION_READBACK_PENDING]
→ F5_NEW_INCOMING_PHYSICAL_LIFECYCLE_QUALIFICATION
→ F5M_EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER
→ F6_F7_ACCEPTANCE_AND_QUALIFICATION
→ F8_ONLY_IF_SEPARATELY_AUTHORIZED
```

```text
DATA_STANDARDS_ALIGNMENT_TASK=AIFE-SERVER-DATA-FOUNDATION-DATA-STANDARDS-ALIGNMENT-V1
SERVER_DOMAIN_GOVERNANCE_STATUS=COMPLETE
INTERFACE_COMPLIANCE_TASK=AIFE-SERVER-DATA-FOUNDATION-API-SECURITY-LOGGING-COMPLIANCE-V1
NEXT_RECOMMENDED_TASK=OWNER_REVIEW_FINAL_REMOTE_F5P_ARCHITECTURE_THEN_CREATE_SEPARATE_F5_DEV_TZ
FOLLOWING_TASK=F5_IMPLEMENTATION_ONLY_AFTER_DEV_TZ_AND_OWNER_EXECUTION_AUTHORITY
```

F5P governance publication changes only F5P research/Program Map, one new deployment contract,
its owner registry row and canonical generated projections. It does not change F5R research,
ADR, DATA standards, six existing Server contracts, DEV_TZ, transport/backend runtime, server
source, tests, current collection route, F5/F5M data or production state.
