---
id: AIFE-SERVER-DATA-PROGRAM-MAP-2026-08-24
title: "Карта программы: Серверная и информационная основа AIFE"
version: '0.1'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
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

## Идентификация программы

| Поле | Значение |
| --- | --- |
| Программа (`Program`) | `AIFE_SERVER_DATA_FOUNDATION` |
| Идентификатор области (`Scope-Slug`) | `aife-server-data-foundation` |
| Тип программы (`Program-Type`) | `foundation-program` |
| Основная цель (`Primary Goal`) | `MINIMAL_SCALABLE_AIFE_SERVER_SIDE_FOUNDATION` |
| Роль рабочей области (`Workspace Role`) | `TEST_AND_REAL_CONSUMER` |
| Роль ETH (`ETH Role`) | `FIRST_PROVING_DOMAIN` |
| Корень исполнения (`Execution Root`) | `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/` |
| Текущий шлюз (`Current Gate`) | `F0_BRIDGE_AND_DURABLE_PLANNING_AUTHORITY_PENDING_STAGING_OWNER_INTEGRATION` |
| Класс физического использования (`Physical Use Class`) | `control-plane-evidence-only` |
| Классификация поставки (`Delivery Claim`) | `CONTROL_PLANE_ONLY_DELIVERY_BLOCKED` |

## Базовая линия полномочной документации

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_WORKTREE_CLEAN=true

STD_ARCH_PATTERNS_001=APPROVED_1_0_0
APP_CONTEXT_IS_SOLE_PUBLIC_RUNTIME_SURFACE=YES
DEPENDENCY_MANAGER_IS_INTERNAL_ONLY=YES
CORE_DATA_SUBSTRATE_EXISTS=YES
CORE_DATA_AREAS=models,repositories,adapters,uow

CONCRETE_DATABASE_OWNER_SELECTED=NO
ACTIVE_DATABASE_TOPOLOGY_ADR_EXISTS=NO
ACTIVE_SERVER_DATA_ARTIFACT_CONTRACT_EXISTS=NO

DATA_MANAGEMENT_STANDARDS_STATUS=DRAFT_0_1_0
API_STANDARD_SUITE_STATUS=APPROVED_1_0_0
LOGGING_STANDARD_STATUS=STD_LOG_001_APPROVED_2_3_0
SECURITY_STANDARDS_RELEVANT_STATUS=APPROVED
MON_HEALTH_METRICS_STATUS=DRAFT_0_1_0

CONTRACT_NAMING_STANDARD=STD-GOVERNANCE-NAMING-001_1.3.0_APPROVED
CONTRACT_AUTHORING_STANDARD=STD-GOVERNANCE-CONTRACT-001_1.1.0_APPROVED
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED_BY_F0=NO
```

Текущий канонический список доменов контрактов в `STD-GOVERNANCE-CONTRACT-001`:
`DOC, ARCH, LOG, SEC, GOVERNANCE, API, DATA, MON, PERF, TEST, CHANGE`; `SERVER`
в нём отсутствует. Поэтому будущий канонический идентификатор
`CONTRACT-SERVER-WORK-001` сохраняется как намерение владельца, но не может быть
создан или зарегистрирован, пока отдельное изменение правил управления владельцем не
добавит `SERVER` в действующие полномочные правила доменов контрактов AIFE.

Черновые стандарты управления данными задают терминологию и границы рисков для
схемы, миграции, проверки, хранения и резервного копирования. Примеры SQLite/MongoDB
в них **не** являются выбором технологии для боевого контура.

## Архитектурная базовая линия

Утверждённая архитектура AIFE задаёт ограничения для будущей интеграции серверного контура:

```text
Presentation
→ Manager
→ Service
→ Repository/Gateway
→ Adapter
→ SERVER_BOUNDARY
→ AIFE_SERVER_ROOT
→ generic server mechanisms
→ domain integration
→ domain authority
```

`STD-ARCH-PATTERNS-001` остаётся нормативным источником распределения
ответственности Manager/Service/Repository. `ADR-INITIALIZER-CORE-001` сохраняет
`AppContext` как единственную публичную типизированную поверхность исполнения, а
`DependencyManager` — как внутренний реестр запуска и жизненного цикла.

```text
SECOND_AIFE_DATA_ROUTE=FORBIDDEN
SECOND_PUBLIC_DI_ROUTE=FORBIDDEN
WORKSPACE_INTERNAL_ARCHITECTURE_REWRITE_REQUIRED=NO
```

## Три основных вопроса

```text
QUESTION_1=HOW_DATA_IS_ACQUIRED_AND_DURABLY_STORED

QUESTION_2=HOW_PROVEN_ETH_D8_D9_D6_MECHANISMS_ARE_REUSED_AS_REFERENCE_WITHOUT_BECOMING_AIFE_PLATFORM_PRIMITIVES

QUESTION_3=HOW_AIFE_CONSUMERS_CONNECT_TO_AIFE_SERVER_ROOT_THROUGH_EXISTING_AIFE_ARCHITECTURAL_BOUNDARIES_WITH_HORIZONTAL_SCALE_BY_DESIGN
```

## Решения основы, закрепляемые программой-кандидатом

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS

ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES

DOMAIN_OWNS_SEMANTICS=YES_CANDIDATE
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
DATA_BRIDGE_TARGET_ROLE_AS_PRIMARY_PHYSICAL_HISTORY_WAREHOUSE=NO
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
ONE_CANONICAL_WORK_SCHEDULING_ROUTE=YES

ONE_CANONICAL_AIFE_SERVER_ROOT=YES
AIFE_SERVER_ROOT_IS_SEMANTIC_AUTHORITY=false
ONE_MONOLITH=NO
ONE_CONTAINER=NO
ONE_DATABASE=NO
HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
MULTI_NODE_IMPLEMENTATION_NOW=NO
INITIAL_ONE_SERVER=ALLOWED
FOUNDATION_FIRST=YES
BUILD_EVERYTHING_NOW=NO
```

## Последовательность этапов

| Этап | Имя | Статус | Зависимость | Критерий выхода |
| --- | --- | --- | --- | --- |
| F0 | `BRIDGE_AND_DURABLE_PLANNING_AUTHORITY` | `CURRENT / CANDIDATE_STAGED` | точный пакет проверки AIFE | `Program Map` + `DEV_TZ` + кандидат ADR основы + привязка моста |
| F1 | `SERVER_DATA_FOUNDATION_OWNER_ARCHITECTURE` | `NEXT_AFTER_TWO_STAGE_F0_OWNER_INTEGRATION` | интеграция владельцем в промежуточный репозиторий + каноническая интеграция владельцем в AIFE | архитектура/ADR одобрены владельцем и зафиксирован точный текущий маршрут программы |
| F1G | `SERVER_CONTRACT_DOMAIN_OWNER_GOVERNANCE_GATE` | `BLOCKED / REQUIRED_IF_SERVER_STILL_UNREGISTERED` | F1 | канонический домен `SERVER` одобрен владельцем до создания/регистрации `CONTRACT-SERVER-WORK-001` |
| F2 | `MINIMUM_SERVER_DATA_CONTRACTS` | `BLOCKED` | F1 + F1G, когда он требуется | минимальные версионируемые контракты семантической привязки и привязки исполнения без выбора технологии |
| F3 | `AIFE_SERVER_ROOT_SOURCE_SKELETON` | `BLOCKED` | F2 | один воспроизводимый корень операций + ограниченный исходный каркас без активации боевого режима |
| F4 | `FIRST_DOMAIN_INTEGRATION_ETH` | `BLOCKED` | F3 | ETH используется как первый проверочный домен без изменения его семантических полномочий |
| F5 | `ETH_HIGH_CARDINALITY_P2_PHYSICAL_LIFECYCLE` | `BLOCKED` | F4 + отдельная полномочная документация ETH P2 | `Object/Parquet` может быть реализован только для ETH P2 и только при отдельном разрешении владельца |
| F5M | `ETH_EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER` | `BLOCKED` | F5 + квалифицированный новый физический маршрут | заморожен перечень миграции, подтверждены идентичности и целостность, полнота диапазонов, семантический паритет чтения, происхождение данных, независимое чтение, сохранена читаемость прежнего маршрута и пройден шлюз владельца на переключение |
| F6 | `AIFE_CONSUMER_INTEGRATION_AND_ACCEPTANCE` | `BLOCKED` | F4/F5 для `PARTIAL_CONSUMER_ACCEPTANCE`; F5M для `FULL_HISTORY_MIGRATION_ACCEPTANCE` | рабочая область использует семантический контракт и никогда не обращается к физическому хранилищу напрямую; полная историческая приёмка требует завершённого F5M |
| F7 | `PHYSICAL_AND_HORIZONTAL_SCALING_QUALIFICATION` | `BLOCKED` | F3-F6 | доказаны перезапуск, второй исполнитель, замена внутренней реализации и изоляция отказов |
| F8 | `LATER_PRODUCTION_ACTIVATION_OR_CUTOVER` | `DEFERRED` | явный шлюз владельца после F7 | переход полномочий боевого режима, если он отдельно разрешён |

Названия этапов могут уточняться только владельцем через явный обзор AIFE; порядок
зависимостей нельзя менять скрытно. `F1G` — ограниченный подшлюз правил управления, а не
перенумерация программы: `F1 → F1G (если требуется) → F2 → F3`.

`F5M` — ограниченный подэтап миграции существующего физического корпуса, а не
перенумерация F0–F8. Частичная приёмка потребителя на ограниченном квалифицированном
наборе может начаться до завершения полной исторической миграции, но окончательное
выведение прежнего физического хранилища и финальное переключение хранения запрещены
до F5M.

```text
F5M_REQUIRED_BEFORE_FINAL_PHYSICAL_WAREHOUSE_RETIREMENT=YES
F5M_REQUIRED_BEFORE_F8_FINAL_STORAGE_CUTOVER=YES
PARTIAL_CONSUMER_ACCEPTANCE=ALLOWED_ON_QUALIFIED_BOUNDED_DATASET
FULL_HISTORY_MIGRATION_ACCEPTANCE=REQUIRES_F5M
LEGACY_PHYSICAL_RETIREMENT_BEFORE_F5M=FORBIDDEN
```

## Последовательность передачи F0 владельцу

F0 включает две разные интеграции владельцем, а открытая ветка PR не является
устойчивой полномочной основой передачи AIFE:

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222
→ owner final review
→ owner merge into eth-macro-data-bridge/main
→ post-merge readback of durable AIFE/** carrier

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged durable bridge carrier
→ verify then-current AIFE workspace base
→ verify staged candidate hashes
→ exact-byte apply to canonical AIFE target paths
→ update real AIFE registry
→ run canonical AIFE validation
→ owner integration in AIFE

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

Ни на этапе A, ни на этапе B создание контрактов F2 не начинается.

## Вопрос 1 — целевой жизненный цикл

```text
SOURCE
→ ACQUIRE
→ DOMAIN_NORMALIZE
→ DOMAIN_VALIDATE
→ INGEST_DURABLE
→ STAGE_OR_SPOOL
→ LOGICAL_PUBLICATION_UNIT
→ PUBLICATION_BOUNDARY
→ STORAGE_ADAPTER
→ DURABLE_BACKEND
→ INDEPENDENT_READBACK
→ CANONICAL_REGISTRATION
→ CANONICAL_ACK
→ SEMANTIC_ACCESS
```

Жёсткое разделение:

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

Исполнитель может завершиться без потери принятых данных только после того, как принятая
работа/вход представлены в устойчивом восстанавливаемом состоянии со стабильной
идентичностью. Узел можно заменить без потери канонической истории только тогда, когда
каноническая история хранится во внешнем или общем устойчивом полномочном источнике либо восстанавливается
из независимого устойчивого полномочного источника. Локальный каталог одного узла никогда не может быть
единственной канонической истиной.

### Целевое состояние физического корпуса данных

`Data Bridge` остаётся семантическим полномочным источником ETH, но после квалификации
серверной основы не должен оставаться целевым основным физическим складом истории.
Накопленный и продолжающий накапливаться корпус физических слоёв полезной нагрузки и истории должен
быть контролируемо переведён под управляемый AIFE жизненный цикл хранения.

Кандидаты на будущий перечень миграции концептуально включают физическую историю в
`data/**`, `history/**`, `archive/**`, исторические слои `derivatives/**`, `options/**`,
`liquidity/**`, ограниченную историю `Git WARM` и объекты `GitHub Release`/глубокой истории. Этот
список не является неизменяемым перечнем миграции: точный состав должен быть заново
построен и заморожен в будущей задаче на актуальном состоянии.

```text
MIGRATE_EXISTING_DATA_BRIDGE_PHYSICAL_CORPUS_TO_AIFE_MANAGED_STORAGE=YES
MIGRATE_CURRENTLY_ACCUMULATING_DATA=YES
NEW_DATA_EVENTUALLY_PUBLISHED_TO_AIFE_MANAGED_STORAGE=YES
DATA_BRIDGE_DOMAIN_AUTHORITY_AFTER_MIGRATION=YES
DATA_BRIDGE_PROVIDER_DOMAIN_LOGIC_AFTER_MIGRATION=YES
DATA_BRIDGE_NORMALIZATION_VALIDATION_AFTER_MIGRATION=YES
DATA_BRIDGE_PHYSICAL_WAREHOUSE_ROLE_AFTER_FINAL_CUTOVER=NO
MIGRATION_NOW=NO
BULK_DELETE_NOW=NO
CURRENT_PRODUCTION_COLLECTION_CHANGE_NOW=NO
```

Миграция является переходом жизненного цикла данных, а не схемой
`COPY_FILES → DELETE_SOURCE`. Будущая единица миграции должна сохранять или
доказывать, где применимо: доменную идентичность, `series_id`, `observation_id`,
временной диапазон, состав, хэш содержимого, схему/версию, `effective_at`,
`known_at`, происхождение данных, финальность/ревизии и каноническую читаемость.

Предпочтительная последовательность:

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

Сначала должна быть доказана корректная будущая публикация новых входящих данных, затем
выполняется обратное заполнение накопленной истории.

```text
CORRECT_FORWARD_COLLECTION_FIRST=YES
FULL_BACKFILL_BEFORE_NEW_ROUTE_CAN_EXIST=NO
DELETE_OLD_DATA_BEFORE_MIGRATION_PROOF=NO
DISABLE_LEGACY_READ_ROUTE_BEFORE_READ_PARITY=NO
CUTOVER_BEFORE_COMPLETENESS_PROOF=NO
MIGRATION_REQUIRES_INDEPENDENT_READBACK=YES
MIGRATION_REQUIRES_SEMANTIC_READABILITY_PROOF=YES
ROLLBACKABILITY_BEFORE_FINAL_RETIREMENT=REQUIRED
```

## Вопрос 2 — ETH как эталон, а не онтология платформы

Доказательная база эталона привязана к:

```text
DATA_BRIDGE_REFERENCE_COMMIT=6a431edc3c834070c3c67453cf111aa757d65b8b
RESEARCH_REFERENCE_COMMIT=6e2a629c91bbfdf1daf41a81583bae96ea67eb4f
D8_D9_D6_NAMES_ARE_AIFE_PLATFORM_PRIMITIVES=false
ETH_DATA_BRIDGE_REMAINS_MARKET_DATA_SEMANTIC_AUTHORITY=true
```

Повторно используемые свойства эталона:

- стабильная идентичность работы;
- аренда/владение работой;
- контрольная точка;
- устойчивое состояние до публикации;
- повтор, восстановление и ограничение давления очереди;
- идемпотентность;
- детерминированная идентичность публикации, независимая от хранилища;
- каноническое подтверждение всей единицы публикации;
- независимое чтение после записи;
- адаптер/профиль хранения;
- семантическое разрешение;
- детерминированный план доступа;
- канонический читатель;
- семантическая квитанция результата и происхождения данных.

Семантика, принадлежащая ETH, остаётся в ETH: правила поставщиков, `series_id`,
`observation_id`, финальность рынка, правила пропусков, ревизий и происхождения данных.

Целевой маршрут после будущей физической миграции сохраняет семантическую роль
`Data Bridge` и не создаёт второй ETH-разрешитель:

```text
AIFE consumer
→ AIFE semantic access boundary
→ ETH domain integration
→ Data Bridge domain semantics/resolution
→ AIFE-managed physical storage mechanism
```

Физическое хранилище AIFE не становится семантическим полномочным источником, а
`Data Bridge` не устраняется после миграции.

## Вопрос 3 — граница потребителя и масштабирование

Потребители остаются на существующем архитектурном маршруте AIFE и запрашивают
семантику, а не физическое хранение:

```text
Presentation
→ Manager
→ Service
→ Repository/Gateway
→ Adapter
→ stable AIFE server semantic contract
→ domain capability
```

Запрещено:

```text
DIRECT_UI_TO_DATABASE=YES_FORBIDDEN
DIRECT_UI_TO_SERVER_FILESYSTEM=YES_FORBIDDEN
DIRECT_UI_TO_OBJECT_STORAGE=YES_FORBIDDEN
DIRECT_UI_TO_PARQUET_PATH=YES_FORBIDDEN
DIRECT_UI_TO_ETH_D6=YES_FORBIDDEN
DIRECT_UI_TO_PROVIDER=YES_FORBIDDEN
CONSUMER_SELECTS_NODE_HOSTNAME=NO
CONSUMER_SELECTS_CONTAINER=NO
```

Цель масштабирования — `WORKER_COUNT=1..N` по допустимым измерениям: домен,
возможность, источник/поставщик, субъект/раздел, временной диапазон и тип работы.
Уникальное каноническое состояние, существующее только на одном узле, запрещено.

### Планирование периодической серверной работы

Целевой общий механизм AIFE Server отвечает за вычисление наступивших работ,
устойчивую идентичность и состояние работы, владение, повторы, восстановление и
исполнение на `WORKER_COUNT=1..N`. Домен задаёт семантику того, **что** считается
наступившим: возможности, периодичность/слот, допустимость обратного заполнения,
финальность, источник, трактовку пропусков и окно свежести.

Каноническая модель:

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

`worker → sleep(...) → collect` и независимый `cron` на каждом узле не являются
канонической моделью. `n8n`/внешний `cron` могут быть внешними источниками событий или
бизнес-автоматизацией, но не владеют каноническим состоянием периодической работы.

```text
AIFE_SERVER_OWNS_GENERIC_WORK_EXECUTION=YES_CANDIDATE
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
EXTERNAL_CRON_IS_CANONICAL_EXECUTION_AUTHORITY=NO
N8N_IS_CANONICAL_AIFE_SCHEDULER=NO
N8N_REQUIRED_FOR_PERIODIC_DATA_COLLECTION=NO
N8N_ALLOWED_AS_EXTERNAL_WORKFLOW_AUTOMATION=YES
EXTERNAL_TRIGGER=OPTIONAL_INPUT
CANONICAL_PERIODIC_SCHEDULING_AUTHORITY=AIFE_SERVER_PLUS_DOMAIN_DUE_POLICY
SERVER_RESTART_DOES_NOT_ERASE_SCHEDULE_SEMANTICS=YES
SAME_LOGICAL_SLOT_DUPLICATE_EXECUTION=PREVENT_OR_IDEMPOTENTLY_COLLAPSE
```

На точном снимке AIFE уже существует `TaskManager.run_periodic_task` как сохранённый
совместимый помощник для возможных периодических работ, но он не является действующим
контрактом планировщика. Будущая реализация обязана сначала исследовать и согласовать эту
границу совместимости, а не создавать параллельный второй маршрут планирования.

## Роль серверного корня AIFE

Для воспроизводимости требуется один канонический корень операций и развёртывания:

```text
deployment/
config/
services/
domains/
runtime/
staging/
logs/
evidence/
backups/
scripts/
runbooks/
```

Это только модель логических классов. Точные имена в файловой системе не разрешены
до последующей задачи с исходным кодом после одобрения архитектуры владельцем.

## Минимальный перечень `Artifact Contract` до F3

В AIFE `Artifact Contract` — именованный артефакт привязки, а не синоним каждой
схемы исполнения. Избыточное размножение контрактов явно отклонено.

| Концептуальный кандидат | Решение | Планируемый канонический артефакт владельца | Обоснование |
| --- | --- | --- | --- |
| Контракт серверных возможностей AIFE | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-SERVER-WORK-001` | идентичность и допустимость возможности относятся к ограниченной границе работы; отдельный контракт пока не даёт ценности для второго использования |
| Контракт описания работы AIFE | `REQUIRED_BEFORE_F3` | `CONTRACT-SERVER-WORK-001` | связывает семантическую идентичность работы, эквивалент владения/аренды, контрольную точку, повтор, конечное состояние и ссылку на возможность |
| Контракт устойчивого состояния AIFE | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-SERVER-WORK-001` + `CONTRACT-DATA-PUBLICATION-001` | устойчивость при приёме и устойчивость публикации различаются, но не оправдывают третий самостоятельный именованный артефакт привязки (`Artifact Contract`) |
| Контракт публикации AIFE | `REQUIRED_BEFORE_F3` | `CONTRACT-DATA-PUBLICATION-001` | связывает логическую идентичность публикации, адаптер хранения, устойчивое независимое чтение, регистрацию и подтверждение всей единицы |
| Контракт доступа к данным AIFE | `REQUIRED_BEFORE_F3` | `CONTRACT-DATA-ACCESS-001` | связывает семантический запрос, план разрешения/доступа, канонический читатель/формирование результата и отказ при неопределённости |
| Контракт квитанции происхождения AIFE | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-DATA-ACCESS-001` | квитанция происхождения неотделима от границы семантического чтения/результата при первом использовании |

Точный целевой реестр для всех трёх будущих именованных артефактов привязки (`Artifact Contract`):
`genome/registries/CONTRACTS_REGISTRY.md`.

`CONTRACT-SERVER-WORK-001` — будущий канонический идентификатор с `DOMAIN=SERVER`.
Его текущее состояние:

```text
STATUS=PLANNED_CANONICAL_ID_PENDING_SERVER_DOMAIN_GOVERNANCE_EXTENSION
DOMAIN=SERVER
DOMAIN_STATUS=NOT_YET_CANONICALLY_REGISTERED
PRECONDITION=SERVER_DOMAIN_OWNER_GOVERNANCE_PASS
CONTRACT_SERVER_WORK_001_FILE_CREATED_BY_F0=NO
```

Планируемая область `CONTRACT-SERVER-WORK-001` должна также рассмотреть
идентичность наступившего слота/расписания как часть той же границы работы:

```text
SERVER_WORK_PLANNED_FIELDS=
stable_work_identity,domain,capability,work_type,subject_partition,due_slot_schedule_identity,attempt,ownership_lease_equivalent,checkpoint,retry_recovery,terminal_state,policy_reference,correlation_trace_identity

SCHEDULING_BOUNDARY_MERGED_WITH_SERVER_WORK_CONTRACT=YES_CANDIDATE
SEPARATE_SCHEDULER_ARTIFACT_CONTRACT=NOT_REQUIRED_YET
SEPARATE_SCHEDULER_CONTRACT_CREATED=NO
```

F0 не создаёт ни одного файла контракта.

## Граница технологических решений

```text
DATABASE_VENDOR_SELECTED=NO
POSTGRES_SELECTED=NO
MONGODB_SELECTED=NO
SQLITE_SELECTED_AS_CANONICAL_SERVER_DATABASE=NO
OBJECT_PARQUET_SELECTED_AS_AIFE_UNIVERSAL_STORAGE=NO
HIGH_CARDINALITY_RAW_TO_SQL_BY_DEFAULT=NO
TRANSPORT_SELECTED=NO
HTTP_SELECTED=NO
GRPC_SELECTED=NO
WEBSOCKET_SELECTED=NO
```

`OBJECT_BLOB_PLUS_PARQUET` сохраняется только как
`ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED`.

## Граница существующей истории

```text
ETH_EXISTING_GITHUB_RELEASE_HISTORY_MIGRATION_NOW=NO
ETH_EXISTING_GIT_HOT_DATA_MIGRATION_NOW=NO
RESEARCH_WAVE_HISTORY_MIGRATION_NOW=NO
LEGACY_READABILITY_MUST_BE_PRESERVED=YES
```

Текущие запреты на миграцию **сейчас** не отменяют целевое решение о будущей
контролируемой миграции после готовности основы.

```text
DATA_BRIDGE_EXISTING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_GROWING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_DOMAIN_AUTHORITY_PRESERVED=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
MIGRATION_EXECUTED=NO
LEGACY_READABILITY_PRESERVED=YES
DELETE_OLD_DATA_BEFORE_PROOF=NO
F5M_STAGE_PRESENT=YES
```

Общие механизмы могут сохранять `identity`/`effective_at`/`known_at`/`version`/
`provenance`/`append`/`supersede`/`audit`. Платформе AIFE не требуется понимать семантику волн Эллиотта.

## Текущее состояние эталона ETH

На границе эталона:

- для D8 доказаны получение данных/исполнение, аренда, контрольные точки, повторы, восстановление и SPOOL;
- SQLite WAL — операционное состояние исполнения, а не полномочная история;
- детерминированные `PublicationBatch` + `Publication Port` + устойчивость/независимое чтение +
  каноническое подтверждение всей партии квалифицированы на уровне исходного кода и физического контура;
- активный семантический доступ остаётся по маршруту разрешение → `ResolutionPlan v1` → читатель;
- текущий физический профиль использует ограниченный Git WARM + неизменяемый GitHub Release
  COLD, не превращая Git в семантический полномочный источник;
- внутренняя реализация P2 не активна;
- ETH R2 остаётся заблокированным до отдельной полномочной документации жизненного цикла P2.

Исправленные измеренные данные о происхождении `data/**`:

```text
DATA_BINANCE_PROVIDER_FILES=2848216_BYTES
DATA_KRAKEN_PROVIDER_FILES=91104_BYTES
DATA_PROVIDER_FILES_TOTAL=2939320_BYTES
DATA_MANIFEST=13251_BYTES
DATA_ROOT_TOTAL=2952571_BYTES

GIT_TREE_WRITES_CURRENT_NORMALIZED_AND_BOUNDED_HISTORY=YES
GIT_TREE_WRITES_HIGH_CARDINALITY_RAW_P2=NO_CURRENTLY
```

## Шлюз против избыточного усложнения

```text
FOUNDATION_FIRST=true
EXTRACTION_BY_PROVEN_USE_CASE=true
NEW_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
```

По умолчанию отложены: универсальный менеджер плагинов, универсальный язык описания
рабочих процессов, глобальная шина событий как плоскость данных, сервисная сетка (`service mesh`), Kubernetes,
`Kafka`, `Redis`, `ClickHouse`, `TimescaleDB`, `Iceberg`, `Delta Lake`, векторная база, хранилище признаков (`feature store`) и
единая огромная база данных для всех доменов.

## Нецели

F0 не реализует серверное исполнение или планировщик, не изменяет `AppContext` или `core/data`, не выбирает базу данных или транспорт, не развёртывает контейнеры, не создаёт хранилище, не реализует ETH P2, не возобновляет ETH R2, не выполняет перенос истории, не меняет текущую частоту/маршрут сбора данных, не создаёт поток `n8n` и не активирует боевой режим.

## Классификация поставки

```text
PLANNING_PACKAGE_RESULT=PASS
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
USER_VALUE_PHYSICAL_DELIVERY=NOT_YET_DELIVERED
OPERATIONALIZATION=MISSING_BY_DESIGN_AT_F0
PHYSICAL_INTEGRATION_PROOF=NOT_APPLICABLE_YET
SERVER_IMPLEMENTATION=NO
PHYSICAL_DELIVERY=NO
```

Это не ошибка задачи планирования. F0 поставляет только устойчивое планирование
управляющего контура и байты для интеграции владельцем; физическая серверная ценность для
пользователя относится к последующим отдельно разрешённым этапам реализации и квалификации.

## Следующие шлюзы

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```

Следующая задача выполняет финальный обзор владельцем исправленного PR #222, при
успешном прохождении всех шлюзов объединяет его с `main` промежуточного репозитория, выполняет
чтение после объединения и останавливается. Только следующая за ней задача может
использовать объединённый устойчивый пакет, проверить актуальную на тот момент базу
рабочей области AIFE, применить точные байты `Program Map` + `DEV_TZ` + `ADR`, обновить реальный
реестр ADR, выполнить каноническую проверку AIFE и остановиться.

После канонической интеграции в AIFE порядок следующий:

```text
F1 architecture authority currentization
→ F1G SERVER domain governance extension if still required
→ F2 minimum contracts
→ F3 server-root source skeleton
→ F4 first ETH domain integration
→ F5 ETH P2 physical lifecycle when separately authorized
→ F5M ETH existing corpus migration and physical storage cutover
→ F6/F7 acceptance and qualification
→ F8 only when separately authorized
```

Ни одна из двух задач интеграции владельцем не начинает F2/F3.
