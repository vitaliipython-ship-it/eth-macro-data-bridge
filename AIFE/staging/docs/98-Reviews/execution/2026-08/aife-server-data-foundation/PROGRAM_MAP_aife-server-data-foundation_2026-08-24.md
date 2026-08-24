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
AIFE_OWNS=GENERIC_EXECUTION_MECHANISMS+GENERIC_DURABLE_STATE_AND_RECOVERY+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_ABSTRACTION+GENERIC_DATA_ACCESS_INTERFACE+GENERIC_SERVER_OPERATIONS_FOUNDATION

DOMAIN_OWNS=DOMAIN_IDENTITIES+SOURCE_PROVIDER_SEMANTICS+NORMALIZATION_RULES+DOMAIN_FINALITY+DOMAIN_VALIDATION+DOMAIN_SPECIFIC_DERIVATIONS_AND_INTERPRETATION

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
| F6 | `AIFE_CONSUMER_INTEGRATION_AND_ACCEPTANCE` | `BLOCKED` | F4/F5 по требованиям варианта использования | рабочая область использует семантический контракт и никогда не обращается к физическому хранилищу напрямую |
| F7 | `PHYSICAL_AND_HORIZONTAL_SCALING_QUALIFICATION` | `BLOCKED` | F3-F6 | доказаны перезапуск, второй исполнитель, замена внутренней реализации и изоляция отказов |
| F8 | `LATER_PRODUCTION_ACTIVATION_OR_CUTOVER` | `DEFERRED` | явный шлюз владельца после F7 | переход полномочий боевого режима, если он отдельно разрешён |

Названия этапов могут уточняться только владельцем через явный обзор AIFE; порядок
зависимостей нельзя менять скрытно. `F1G` — ограниченный подшлюз правил управления, а не
перенумерация программы: `F1 → F1G (если требуется) → F2 → F3`.

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

F0 не реализует серверное исполнение, не изменяет `AppContext` или `core/data`, не
выбирает базу данных или транспорт, не развёртывает контейнеры, не создаёт хранилище, не
реализует ETH P2, не возобновляет ETH R2, не мигрирует прежнюю историю и не активирует
боевой режим.

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
```

Ни одна из двух задач интеграции владельцем не начинает F2/F3.
