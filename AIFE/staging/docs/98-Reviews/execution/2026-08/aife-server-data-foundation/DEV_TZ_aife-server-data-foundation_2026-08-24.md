---
id: AIFE-SERVER-DATA-DEV-TZ-2026-08-24
title: "DEV_TZ: Серверная и информационная основа AIFE V1"
version: '0.1'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
category: architecture
doc_type: spec
language: ru
tags: [dev-tz, server, data, foundation, durability, publication, access, scalability]
authority_reference:
  - AGENTS.md
  - genome/registries/STANDARDS_REGISTRY.md
  - genome/registries/ADR_REGISTRY.md
  - genome/registries/CONTRACTS_REGISTRY.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/governance/STD-GOVERNANCE-NAMING-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
related:
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - genome/adr/data/ADR-DATA-FOUNDATION-001.md
---

# DEV_TZ: Серверная и информационная основа AIFE V1

## Статус

```text
Task-Family=AIFE_SERVER_DATA_FOUNDATION
Current-Stage=F0_STAGED_CANDIDATE_GOVERNANCE_REPAIR_BEFORE_STAGING_OWNER_INTEGRATION
Package-Role=DURABLE_OWNER_PLANNING_CANDIDATE
Execution-Allowed=NO_SERVER_IMPLEMENTATION
Physical-Use-Class=control-plane-evidence-only
Physical-Delivery-Claim=NO
Planning-Package-Result=PASS
AIFE-Delivery-Status=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
```

Этого DEV_TZ достаточно для декомпозиции последующих работ, одобренных владельцем,
без опоры на чат. До интеграции в канонический AIFE документ не является полномочной
документацией боевого контура.

## Полномочная база и текущие фактические ограничения

Точная исходная базовая линия:

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_WORKTREE_CLEAN=true
```

Проверенная текущая полномочная документация AIFE:

- `STD-ARCH-PATTERNS-001` `1.0.0` имеет статус `approved`;
- `ADR-INITIALIZER-CORE-001` `1.0` — текущее решение владельца для публичной границы исполнения/DI;
- `AppContext` — единственная публичная типизированная поверхность исполнения;
- `DependencyManager` используется только как внутренний механизм запуска и жизненного цикла;
- существует каноническая топология `core/data/`: `models/`, `repositories/`, `adapters/`, `uow/`;
- стандарты управления данными (`Data Management`) `STD-DATA-MGMT/SCHEMA/MIGRATION/VALIDATION/RETENTION/BACKUP-001` имеют версию `0.1.0` и статус `draft`;
- стандарты проектирования/документирования/ошибок/ограничения частоты/версионирования API (`API Design/Docs/Errors/Rate/Versioning`) версии `1.0.0` имеют статус `approved`;
- `STD-LOG-001` версии `2.3.0` имеет статус `approved`; соответствующие стандарты безопасности (`Security`) также имеют статус `approved`;
- `STD-MON-HEALTH-001` и `STD-MON-METRICS-001` версии `0.1.0` имеют статус `draft`;
- активного ADR по топологии базы данных/серверных данных нет;
- активного именованного артефакта привязки (`Artifact Contract`) для серверного контура и данных нет;
- `STD-GOVERNANCE-NAMING-001` `1.3.0` со статусом `approved` задаёт грамматику `CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>`;
- `STD-GOVERNANCE-CONTRACT-001` `1.1.0` со статусом `approved` сейчас допускает домены контрактов `DOC, ARCH, LOG, SEC, GOVERNANCE, API, DATA, MON, PERF, TEST, CHANGE`;
- `SERVER` сейчас не разрешён как канонический домен контракта.

Черновые стандарты данных дают только терминологию и границы рисков. Их примеры
SQLite/MongoDB не выбирают базы данных для боевого контура.

## Зависимость от правил управления доменом контракта `SERVER`

Намерение владельца сохраняется без скрытой смысловой подмены:

```text
CANONICAL_FUTURE_CONTRACT_ID=CONTRACT-SERVER-WORK-001
KEEP_SERVER_DOMAIN_SEMANTICS=YES
RENAME_SERVER_TO_DATA=NO
RENAME_SERVER_TO_ARCH=NO
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED_BY_F0=NO
CONTRACT_SERVER_WORK_001_FILE_CREATED_BY_F0=NO
```

`CONTRACT-SERVER-WORK-001` можно создать **только если** `SERVER` разрешён действующими
на тот момент каноническими правилами AIFE. Если на границе F1/F2 домен всё ещё
отсутствует, исполнитель обязан остановиться до создания контракта, выполнить отдельную
задачу расширения правил управления, разрешённую владельцем и обновляющую канонические
правила именования/доменов AIFE, и лишь затем возобновить F2. Запасной вариант в виде
`CONTRACT-DATA-WORK-*` или `CONTRACT-ARCH-WORK-*` запрещён.

```text
CONTRACT_SERVER_WORK_001_CAN_BE_MATERIALIZED=
IFF_SERVER_DOMAIN_IS_CANONICALLY_ALLOWED_BY_CURRENT_AIFE_GOVERNANCE

IF_SERVER_DOMAIN_NOT_ALLOWED=
STOP_BEFORE_CONTRACT_CREATION
→ SEPARATE_OWNER_GOVERNANCE_EXTENSION
→ CANONICAL_AIFE_NAMING_DOMAIN_AUTHORITY_UPDATE
→ RESUME_F2
```

## Контракт физического использования

```text
physical-use class: control-plane-evidence-only
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
USER_VALUE_PHYSICAL_DELIVERY=NOT_YET_DELIVERED
OPERATIONALIZATION=MISSING_BY_DESIGN_AT_F0
PHYSICAL_INTEGRATION_PROOF=NOT_APPLICABLE_YET
```

Этот артефакт задаёт будущую декомпозицию и интеграцию владельцем. Он не заявляет
физическую поставку и не может закрыть F3+ без `Physical Integration Proof`.
`CONTROL_PLANE_ONLY_DELIVERY_BLOCKED` — классификация поставки, а не ошибка пакета
планирования F0.

## Контракт поведения

Будущая основа должна:

1. сохранять существующий публичный маршрут исполнения AIFE и распределение ответственности;
2. отделять общий механизм исполнения, хранения и доступа от семантики домена;
3. делать принятую работу восстанавливаемой до того, как временный исполнитель может потерять владение;
4. различать устойчивость при приёме и устойчивость канонической публикации/истории;
5. сохранять запросы рабочей области семантическими, независимыми от внутренней реализации и узла;
6. допускать развёртывание на одном сервере без смысловых изменений при последующем
   переходе к нескольким исполнителям/узлам;
7. не добавлять новый механизм без доказанного варианта использования.

## Контракт основы реализации

Будущая работа с исходным кодом должна расширять, а не обходить:

```text
Presentation / Workspace
→ Manager
→ Service
→ Repository or Gateway
→ Adapter
→ SERVER_BOUNDARY
→ AIFE_SERVER_ROOT
```

Точные имена классов/интерфейсов остаются отложенными до решений владельца на F2/F3.

Жёсткие ограничения:

```text
APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
DEPENDENCY_MANAGER_SECOND_PUBLIC_ROUTE=NO
SECOND_AIFE_DATA_ROUTE=NO
WORKSPACE_INTERNAL_ARCHITECTURE_MUTATION=NO
DIRECT_UI_TO_DATABASE=NO
DIRECT_UI_TO_STORAGE=NO
```

## Инварианты

```text
AIFE_OWNS_GENERIC_MECHANISM=YES_CANDIDATE
DOMAIN_OWNS_SEMANTICS=YES_CANDIDATE
D8_D9_D6_NAMES_ARE_AIFE_PLATFORM_PRIMITIVES=false
PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=false
SERVER_EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false

ONE_CANONICAL_AIFE_SERVER_ROOT=YES
ONE_SERVER_ROOT_IMPLIES_ONE_MONOLITH=false
ONE_SERVER_ROOT_IMPLIES_ONE_CONTAINER=false
ONE_SERVER_ROOT_IMPLIES_ONE_DATABASE=false

HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
INITIAL_ONE_SERVER=ALLOWED
MULTI_NODE_NOW=NOT_REQUIRED
NODE_LOCAL_UNIQUE_CANONICAL_TRUTH=FORBIDDEN
```

## Вопрос 1 — получение данных и устойчивое хранение

Требуемый концептуальный жизненный цикл:

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

### Классы состояния

| Класс состояния | Назначение | Может быть локальным для узла? | Допустима потеря? |
| --- | --- | --- | --- |
| `VOLATILE_PROCESS_STATE` | временное состояние исполнения в памяти | да | да до приёма; после приёма не может быть единственной записью |
| `NODE_LOCAL_RECOVERABLE_STATE` | локальное состояние узла, которое можно пересоздать или восстановить | да | да, если оно независимо пересоздаваемо/восстанавливаемо |
| `INGEST_DURABLE_STATE` | владение, контрольная точка и промежуточное состояние для повтора принятой работы | локальное или общее — по реализации | нет до безопасной публикации или конечного решения |
| `CANONICAL_PUBLISHED_STATE` | устойчивый зарегистрированный результат, принадлежащий домену | не может существовать только на одном узле | нет |
| `ARCHIVAL_STATE` | запечатанный/неизменяемый долгосрочный полномочный источник, когда он требуется | внешний/общий либо независимо восстанавливаемый | определяется правилами восстановления и хранения |

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

### Семантика завершения исполнителя и замены узла

```text
CAN_A_WORKER_DIE_WITHOUT_DATA_LOSS=
YES_IF_ACCEPTED_WORK_HAS_STABLE_IDENTITY_AND_DURABLE_CHECKPOINT_OR_STAGING

CAN_A_NODE_BE_REPLACED_WITHOUT_CANONICAL_HISTORY_LOSS=
YES_IF_CANONICAL_HISTORY_IS_EXTERNAL_SHARED_OR_INDEPENDENTLY_RESTORABLE

CAN_STORAGE_BACKEND_CHANGE_WITHOUT_WORKSPACE_API_CHANGE=
YES_IF_SEMANTIC_IDENTITIES_PUBLICATION_IDENTITY_ACCESS_AND_PROVENANCE_REMAIN_STABLE
```

### Граница SQL

SQL-подобные хранилища в будущем могут владеть:

- управляющим состоянием;
- состоянием аренды/владения;
- контрольными точками;
- метаданными публикации;
- каталогом/индексом;
- недавним компактным состоянием.

Этот DEV_TZ не выбирает их для необработанной истории высокой кардинальности.

```text
HIGH_CARDINALITY_RAW_TO_SQL_BY_DEFAULT=NO
POSTGRES_CONTROL=DEFER_UNTIL_MEASURED_OR_EXISTING_AIFE_REQUIREMENT
```

## Вопрос 2 — выделение общего из доказанного эталона ETH

Эталонные коммиты:

```text
DATA_BRIDGE=6a431edc3c834070c3c67453cf111aa757d65b8b
RESEARCH=6e2a629c91bbfdf1daf41a81583bae96ea67eb4f
```

Уровни выделения:

```text
LEVEL_1_INVARIANT=safe generic property
LEVEL_2_CONTRACT_PATTERN=candidate requiring AIFE owner definition and/or second-use validation
LEVEL_3_DOMAIN_IMPLEMENTATION=remain domain owned
```

### Подробная матрица выделения

| Механизм ETH | Текущий владелец / доказательство | Доменный вход | Общий инвариант | Уровень | Рекомендация |
| --- | --- | --- | --- | --- | --- |
| Исполнение получения данных D8 | `Data Bridge`; исходный код + доказательства `VPS_SHADOW` | семантика поставщика/возможности | исполнение работы отделено от семантических полномочий | L2 | только общий шаблон исполнения приёма данных |
| Политика наступления срока | `Data Bridge`; декларативная/фиксированная сетка | ритм рынка/правила поставщика | политика срока и допустимости принадлежит возможности | L2 | сохранить место политики, не копировать рыночную схему |
| Идентичность цикла/работы | `Data Bridge`; стабильные циклы | рыночный слот/возможность | стабильная идентичность работы переживает повтор | L1 | переиспользовать инвариант |
| Аренда владения | `Data Bridge`; восстановление исполнения | ключ цикла/возможности | одна ограниченная область владения на единицу работы | L1/L2 | общий эквивалент контракта аренды |
| `checkpoint-v2` | `Data Bridge`; привязка к целостности | состав наблюдений/полезная нагрузка | прогресс принятой работы связан с точным доказательством входа | L2 | общий шаблон контрольной точки, новая схема AIFE |
| Состояние `SQLite WAL` | `Data Bridge`; физически проверено | таблицы исполнения D8 | операционное состояние не является полномочным источником истории | L1 | переиспользовать разделение ролей, а не выбор внутренней реализации |
| `SPOOL` | `Data Bridge`; устойчивые `PENDING/FORWARDED` | конверты наблюдений | устойчивое промежуточное состояние до публикации | L1/L2 | общее понятие промежуточного состояния |
| Повтор/восстановление | `Data Bridge`; семантика сбоя/повтора | состояние поставщика/цикла | повторы сохраняют идентичность и не дублируют полномочные источники | L1 | переиспользовать инвариант |
| Ограничение обратного давления | `Data Bridge`; ограниченная политика очереди/публикации | ритм получения | давление должно быть ограничено и завершаться ошибкой при неопределённости | L2 | определять параметры только при втором подтверждённом использовании |
| Конфликт неизменяемой идентичности | `Data Bridge`; отказ при неопределённости | идентичность наблюдения | один логический ID не может скрыто менять содержимое | L1 | общий инвариант |
| `PublicationBatch` | `Data Bridge`; детерминированно | элементы рынка | логическая идентичность публикации не зависит от внутренней реализации/попытки | L1/L2 | основа для контракта публикации AIFE |
| `HistoryPublicationPort` | `Data Bridge`; квалифицировано по исходному коду и физически | доменные роли WARM/COLD | публикация через Adapter + устойчивость + независимое чтение + регистрация | L2 | общая граница публикации |
| Профиль внутренней реализации | `Data Bridge`; текущий `GITHUB_FIRST_V1` | физический выбор Git/Release | физическая реализация выбирается за семантической границей | L1/L2 | профиль адаптера хранения |
| Каноническое `ACK` | `Data Bridge`; физическое доказательство всей партии | точный состав наблюдений | конечная передача только после устойчивого зарегистрированного подтверждения всей единицы | L1 | переиспользовать инвариант |
| Разрешитель D6 | `Data Bridge`; активен | рыночные серии/финальность | семантический запрос внутри разрешается в физические ресурсы | L2 | общий шаблон семантического разрешения |
| `ResolutionPlan` | `Data Bridge`; активен v1 | поля рыночного запроса | детерминированный план доступа отделяет запрос от физических указателей | L1/L2 | общий шаблон плана доступа к данным |
| Читатель истории | `Data Bridge`; активен | формирование рыночного результата | канонический читатель использует план доступа, а не произвольные пути | L2 | общая граница читателя/формирования результата |
| Семантическая квитанция | `Data Bridge`; активна | рыночный результат/происхождение | результат несёт происхождение и диагностику | L1/L2 | включить в контракт доступа к данным |

### Полномочия домена

```text
ETH_PROVIDER_SEMANTICS=DOMAIN_OWNED
ETH_SERIES_ID=DOMAIN_OWNED
ETH_OBSERVATION_ID=DOMAIN_OWNED
MARKET_FINALITY=DOMAIN_OWNED
MARKET_GAP_REVISION_SEMANTICS=DOMAIN_OWNED
ETH_DATA_BRIDGE_REMAINS_MARKET_DATA_SEMANTIC_AUTHORITY=YES
SECOND_ETH_MARKET_DATA_AUTHORITY=NO
```

Исходный код ETH в AIFE не копируется.

## Шлюз архитектурной ценности

Каждый новый примитив платформы должен фиксировать:

```text
RISK=<real proven problem>
SIMPLER_PATH=<can the current domain-owned mechanism remain until second use>
NEXT_AGENT_ACTION_REDUCTION=<does genericization reduce implementation/operation steps>
```

Если доказательства отсутствуют:

```text
NEW_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
```

## Кандидат минимального описания работы

AIFE требуется ограниченное описание работы, достаточное для горизонтального владения,
а не язык описания рабочих процессов.

Семантические поля-кандидаты для рассмотрения на F2:

- стабильная идентичность работы;
- домен;
- возможность;
- тип работы;
- субъект/раздел;
- запрошенный семантический диапазон, где применимо;
- попытка;
- срок наступления/крайний срок, где применимо;
- ссылки на входные данные;
- ссылка на политику;
- идентичность корреляции/трассировки.

Ни одно поле не является окончательным до обзора владельцем
`CONTRACT-SERVER-WORK-001` и прохождения требуемого шлюза управления доменом `SERVER`.

Явно запрещены: универсальный DSL рабочих процессов и глобальная шина событий как
общая инфраструктура исполнения работ.

## Вопрос 3 — контракт потребителя с серверным контуром

Требуемые свойства:

```text
SEMANTIC_NOT_PHYSICAL
DOMAIN_AWARE
BACKEND_NEUTRAL
NODE_NEUTRAL
VERSIONABLE
FAIL_CLOSED
PROVENANCE_RETURNED
```

Концептуальные семейства операций для оценки на F2/F3:

- обнаружение возможностей;
- семантическое чтение данных;
- чтение результата и его происхождения;
- отправка работы, только для работ, выполняемых серверным контуром;
- состояние работы, только если существует отправка работы;
- состояние здоровья.

Отмена остаётся `DEFER`, пока её не потребует реальный длительный вариант использования.

Транспорт явно отделён:

```text
SEMANTIC_CONTRACT != HTTP_GRPC_CLI_IPC_TRANSPORT
HTTP_SELECTED=NO
GRPC_SELECTED=NO
WEBSOCKET_SELECTED=NO
TRANSPORT_SELECTED=NO
```

Если в будущем будет выбран публичный транспорт, применяются утверждённые стандарты
AIFE по проектированию API (`API Design`), версионированию (`Versioning`), ошибкам (`Errors`), ограничению частоты (`Rate Limiting`) и документации (`Documentation`), если владелец явно
не одобрил исключение.

### Запреты прямого доступа

```text
DIRECT_UI_TO_SQL=NO
DIRECT_UI_TO_POSTGRES=NO
DIRECT_UI_TO_MONGODB=NO
DIRECT_UI_TO_SQLITE=NO
DIRECT_UI_TO_PARQUET=NO
DIRECT_UI_TO_OBJECT_STORAGE=NO
DIRECT_UI_TO_SERVER_FILESYSTEM=NO
DIRECT_UI_TO_ETH_D6=NO
DIRECT_UI_TO_PROVIDER=NO
DIRECT_UI_TO_CONTAINER=NO
DIRECT_UI_TO_NODE_HOSTNAME=NO
```

## Плоскость данных != управляющая плоскость

`SystemControlManager` / `SysControlClient` служат архитектурным прецедентом только
для жизненного цикла внешнего клиента.

```text
SYSTEM_CONTROL_CLIENT_IS_FUTURE_DATA_CLIENT=NO
CONTROL_PLANE=SEPARATE_SEMANTICS
DATA_ACCESS_PLANE=SEPARATE_SEMANTICS
```

Существующий `EventBus` остаётся механизмом координации приложения. Он может передавать
крупнозернистые события жизненного цикла, например `connected`/`disconnected`/`request-completed`/
`request-failed`/`health-changed`, но:

```text
EVENT_BUS_IS_HIGH_VOLUME_MARKET_DATA_TRANSPORT=NO
```

## Логическая модель серверного корня AIFE

Требуется один воспроизводимый корень операций:

| Логический класс | Класс состояния | Нужна резервная копия | Следствие для горизонтального масштаба |
| --- | --- | --- | --- |
| `deployment` | воспроизводимое/настроенное | только исходный код/конфигурация | одинаковая структура на N узлах |
| `config` | внедряемое/версионируемое | да, где является полномочным | конфигурация не зависит от узла |
| `services` | воспроизводимые развёртываемые артефакты | пересборка, а не резервирование состояния исполнения | допускаются независимые реплики |
| `domains` | версионируемая регистрация/профиль домена | да | регистрация домена не привязана к узлу |
| `runtime` | локальное восстанавливаемое или общее управляющее состояние | выборочно | нет уникальной канонической истории на одном узле |
| `staging` | устойчивое при приёме там, где этого требует принятие | зависит от восстановления | требуются владение и идемпотентность |
| `logs` | операционные доказательства | по политике хранения | агрегация может развиваться позже |
| `evidence` | устойчивые доказательства аудита/квалификации | да | полномочные доказательства не должны жить только на одном узле |
| `backups` | материал восстановления | да, предпочтительно внешний | единственная копия не может находиться вместе с отказавшим узлом |
| `scripts` | воспроизводимые операции | под контролем исходного кода | одинаково на всех узлах |
| `runbooks` | операционная документация | под контролем исходного кода | не зависит от узла |

Точная структура файловой системы отложена до F3 после интеграции владельцем.

## Основа горизонтального масштабирования

Минимальные понятия распределённой работы:

```text
WORK_UNIT
PARTITION_OR_SHARD
LEASE_OR_OWNERSHIP
IDEMPOTENCY_KEY
CHECKPOINT
RETRY
TERMINAL_STATE
```

На F0-F2 распределённый координатор не реализуется.

| Компонент | Предпочтительный класс состояния | Масштабируется до N? | Общие кандидаты для разделения | Идемпотентность/владение | Устойчивая зависимость | Эталон / пробел |
| --- | --- | --- | --- | --- | --- | --- |
| Получение данных | горизонтально без состояния + устойчивое состояние исполнения | да | домен/возможность/источник/субъект/раздел | ID работы + аренда + контрольная точка | состояние приёма/промежуточное состояние | доказано в ETH; пробел схемы AIFE |
| Публикация | горизонтально без состояния + общее устойчивое состояние публикации | да | логическая единица публикации/раздел | ID публикации + подтверждение всей единицы | устойчивая внутренняя реализация/управляющие метаданные | доказано в ETH; пробел контракта AIFE |
| Чтение | горизонтально без состояния | да | семантический запрос/раздел ресурса | детерминированный план/идентичность чтения | каноническое хранилище/каталог | шаблон доказан в ETH; пробел API AIFE |
| Производное вычисление | предпочтительно горизонтально без состояния | да | домен/возможность/субъект/диапазон | отпечаток входа + версия | канонические входы/политика выхода | общий будущий пробел |
| Управление | сначала допустим временный одиночный экземпляр, позже логически общее | позже | пространство имён работы/домен | CAS/аренда/конечное состояние | устойчивое управляющее состояние | требуется решение владельца AIFE |

Будущие переходы `ONE_NODE → MULTIPLE_NODES → ORCHESTRATOR` не должны менять
семантику запросов рабочей области, идентичность доменных данных, идентичность публикации,
семантическую идентичность хранения или смысл происхождения данных.

## Граница профиля домена

Будущий ограниченный профиль домена может объявлять:

- `domain_id`;
- возможности;
- адаптеры поставщиков/источников;
- семантику нормализации/идентичности/проверки;
- требуемую семантику/класс хранения;
- интеграцию читателя/формирования результата;
- правила происхождения данных.

```text
DOMAIN_REQUESTS_STORAGE_SEMANTICS=YES
DOMAIN_SELECTS_BUCKET_OR_PATH=NO
DOMAIN_SELECTS_SERVER_NODE=NO
```

Выбор физической внутренней реализации остаётся ответственностью платформы и политики хранения.

## Разделение класса данных и роли хранения

```text
OPERATIONAL_RUNTIME_STATE
!= CANONICAL_PUBLISHED_DATA
!= ARCHIVAL_DATA
!= DOMAIN_ANALYTICAL_HISTORY
!= REBUILDABLE_CACHE
```

`Object/Blob + Parquet` не является хранилищем для всего AIFE. Он сохраняется только как
текущее одобренное владельцем исследовательское направление для будущего ETH P2 высокой кардинальности.

```text
OBJECT_PARQUET_SELECTED_AS_AIFE_UNIVERSAL_STORAGE=NO
ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED=YES
```

## Существующая история и аналитическая семантика

Миграция не является предварительным условием:

```text
ETH_EXISTING_GITHUB_RELEASE_HISTORY_MIGRATION_NOW=NO
ETH_EXISTING_GIT_HOT_DATA_MIGRATION_NOW=NO
RESEARCH_WAVE_HISTORY_MIGRATION_NOW=NO
LEGACY_READABILITY_MUST_BE_PRESERVED=YES
```

Общая история может поддерживать `identity`, `effective_at`, `known_at`, `version`,
`provenance`, `append`, `supersede`, `audit`. Интерпретацией владеет домен.

```text
WAVE_PUBLISHED_STATE_MUST_PERSIST=YES
WAVE_PRIMARY_HISTORY_MUST_PERSIST=YES
WAVE_ALTERNATIVE_HISTORY_MUST_PERSIST=YES
WAVE_PREDECESSOR_OVERWRITE=FORBIDDEN
AIFE_PLATFORM_NEEDS_TO_UNDERSTAND_ELLIOTT_WAVE_SEMANTICS=NO
```

## Граница безопасности и секретов

Учётные данные поставщика, хранилища, управления сервером и рабочей области нельзя
объединять в один универсальный секрет.

```text
PROVIDER_CREDENTIALS
!= STORAGE_CREDENTIALS
!= SERVER_CONTROL_CREDENTIALS
!= WORKSPACE_AUTHENTICATION
```

Использование из рабочей области не должно требовать секретов поставщика/хранилища.
Будущая реализация следует утверждённым стандартам безопасности и секретов.

## Основа наблюдаемости

Минимальные общие сигналы для определения на F2/F3 без выбора поставщика технологии:

- состояние здоровья;
- состояние исполнителя;
- давление промежуточного состояния/очереди;
- последний успех/сбой;
- количество повторов;
- состояние контрольной точки;
- состояние публикации;
- состояние независимого чтения из хранилища;
- диагностика запроса потребителя.

`STD-MON-HEALTH-001` и `STD-MON-METRICS-001` имеют статус `draft`; они дают
терминологию, но не выбирают обязательную технологию наблюдаемости.

## Основа восстановления и операций

Будущие операционные действия `AIFE_SERVER_ROOT`:

```text
STATUS
HEALTH
LOGS
START
STOP
BACKUP
RESTORE
VALIDATE
UPGRADE
ROLLBACK
```

Для каждого действия позже необходимо определить затрагиваемое каноническое состояние и устойчивые доказательства.
F0 не реализует команды.

## Требования к областям отказа

Проектирование должно предотвращать:

```text
ONE_FAILED_PROVIDER_STOPS_ALL_DOMAINS
ONE_FAILED_WORKER_LOSES_CANONICAL_DATA
ONE_NODE_FAILURE_DESTROYS_HISTORY
ONE_BAD_PUBLICATION_PARTIALLY_ACKS_BATCH
ONE_WORKSPACE_CAN_BYPASS_DATA_AUTHORITY
```

Ожидаемые измерения изоляции: домен, возможность, источник/поставщик, единица работы,
раздел, единица публикации и запрос потребителя.

## Минимальный перечень именованных артефактов привязки (`Artifact Contract`)

До F3 предлагаются только три именованных артефакта привязки (`Artifact Contract`) владельца:

1. `CONTRACT-SERVER-WORK-001` — объединяет возможность + описание работы +
   устойчивую при приёме привязку владения/контрольной точки/повтора/конечного состояния.
2. `CONTRACT-DATA-PUBLICATION-001` — логическая единица публикации + адаптер хранения
   + устойчивость/независимое чтение/регистрация + подтверждение всей единицы.
3. `CONTRACT-DATA-ACCESS-001` — семантический запрос + план доступа +
   читатель/формирование результата + квитанция происхождения.

Для `CONTRACT-SERVER-WORK-001` действует особое состояние управления:

```text
STATUS=PLANNED_CANONICAL_ID_PENDING_SERVER_DOMAIN_GOVERNANCE_EXTENSION
DOMAIN=SERVER
DOMAIN_STATUS=NOT_YET_CANONICALLY_REGISTERED
PRECONDITION=SERVER_DOMAIN_OWNER_GOVERNANCE_PASS
CREATION_ALLOWED_NOW=NO
```

Классификация:

| Кандидат | Решение |
| --- | --- |
| Контракт серверных возможностей AIFE | `MERGE_WITH_OTHER_CONTRACT` |
| Контракт описания работы AIFE | `REQUIRED_BEFORE_F3` |
| Контракт устойчивого состояния AIFE | `MERGE_WITH_OTHER_CONTRACT` |
| Контракт публикации AIFE | `REQUIRED_BEFORE_F3` |
| Контракт доступа к данным AIFE | `REQUIRED_BEFORE_F3` |
| Контракт квитанции происхождения AIFE | `MERGE_WITH_OTHER_CONTRACT` |

Этот DEV_TZ не создаёт ни одного именованного артефакта привязки (`Artifact Contract`). На F2 необходимо повторно
проверить, достаточно ли конкретна именованная связь для создания каждого контракта;
если нет, её следует оставить как `Runtime/Task Contract`, а не создавать артефакт
`CONTRACT-*`. Для `CONTRACT-SERVER-WORK-001` такая проверка выполняется только после
`SERVER_DOMAIN_OWNER_GOVERNANCE_PASS`.

## Будущие роли приёмки рабочей областью

На F0 не выполнять:

- тест обнаружения потребителем;
- тест семантического чтения;
- тест отправки работы, если F3 предоставляет такую возможность;
- тест квитанции происхождения;
- тест отказа при неопределённости;
- тест замены внутренней реализации;
- тест перезапуска узла;
- тест владения/идемпотентности со вторым исполнителем.

Рабочие области являются потребителями приёмки, а не вторым полномочным источником.

## Матрица трассируемости

| Требование | Класс источника | ID источника | Версия/SHA | Статус | Примечания |
| --- | --- | --- | --- | --- | --- |
| Распределение ответственности Manager/Service/Repository | `EXISTING_AIFE_AUTHORITY` | `STD-ARCH-PATTERNS-001` | `1.0.0` | `approved` | обязательный повторно используемый шаблон AIFE |
| Единственный публичный маршрут исполнения через AppContext | `EXISTING_AIFE_AUTHORITY` | `ADR-INITIALIZER-CORE-001` | `1.0` | `current owner decision` | DependencyManager остаётся внутренним |
| Каноническая топология `core/data` | `EXISTING_AIFE_AUTHORITY` | `STD-ARCH-PATTERNS-001` | `1.0.0` | `approved` | models/repositories/adapters/uow |
| Грамматика ID контракта | `EXISTING_AIFE_AUTHORITY` | `STD-GOVERNANCE-NAMING-001` | `1.3.0` | `approved` | `CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>` |
| Текущий словарь доменов контрактов | `EXISTING_AIFE_AUTHORITY` | `STD-GOVERNANCE-CONTRACT-001` | `1.1.0` | `approved` | `SERVER` отсутствует; до `CONTRACT-SERVER-WORK-001` требуется отдельное расширение правил управления владельцем |
| Термины схемы/миграции/проверки/хранения/резервирования данных | `EXISTING_AIFE_AUTHORITY` | набор `STD-DATA-*` | `0.1.0` | `draft` | терминология и риски, без выбора технологии боевого контура |
| Правила управления публичным API | `EXISTING_AIFE_AUTHORITY` | набор `STD-API-*` | `1.0.0` | `approved` | применяются, если позже будет выбран публичный транспорт API |
| Безопасность/секреты/логирование | `EXISTING_AIFE_AUTHORITY` | `STD-SEC-*`, `STD-LOG-001` | `approved versions` | `approved` | без объединения секретов |
| Эталон идентичности работы/аренды/контрольной точки/повтора | `ETH_PROVEN_REFERENCE_EVIDENCE` | контракты `Data Bridge` D8 | `6a431edc3c834070c3c67453cf111aa757d65b8b` | `reference` | доказательство, а не полномочная документация владельца AIFE |
| Эталон `PublicationBatch`/`Port`/`ACK`/независимого чтения | `ETH_PROVEN_REFERENCE_EVIDENCE` | пересылка/переносимость хранения `Data Bridge` | `6a431edc3c834070c3c67453cf111aa757d65b8b` | `source+physical qualified` | доказательство, а не правила именования AIFE |
| Эталон семантического разрешителя/плана доступа/читателя/квитанции | `ETH_PROVEN_REFERENCE_EVIDENCE` | маршрут `Data Bridge` D6 | `6a431edc3c834070c3c67453cf111aa757d65b8b` | `active reference` | сохранить принцип семантики вместо физического пути |
| Направление P2 `Object/Parquet` | `ETH_PROVEN_REFERENCE_EVIDENCE` | `Unified History/PIT/Backtest SSOT` | `6e2a629c91bbfdf1daf41a81583bae96ea67eb4f` | одобренное исследовательское направление, не реализовано | не универсальное хранилище AIFE |
| Один канонический корень серверных операций AIFE | `NEW_AIFE_OWNER_DECISION_CANDIDATE` | `ADR-DATA-FOUNDATION-001` | `1.0 proposed` | `candidate` | требуется интеграция владельцем |
| Горизонтальное масштабирование по замыслу | `NEW_AIFE_OWNER_DECISION_CANDIDATE` | `ADR-DATA-FOUNDATION-001` | `1.0 proposed` | `candidate` | многосерверная реализация отложена |
| Точная физическая структура серверного корня | `DEFERRED` | F3 | `n/a` | `deferred` | только после интеграции ADR/контрактов владельцем |
| Поставщик базы данных | `DEFERRED` | выбор технологии | `n/a` | `deferred` | требуется измеренная необходимость / решение владельца |
| Технология транспорта | `DEFERRED` | решение по транспорту | `n/a` | `deferred` | сначала семантический контракт |

## Декомпозиция от контрактов

### F0 — устойчивое планирование и передача владельцу

F0 завершается только после двух отдельных этапов интеграции владельцем:

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222
→ owner final review
→ merge into eth-macro-data-bridge/main
→ post-merge readback of durable AIFE/** carrier

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged carrier
→ verify then-current AIFE base
→ verify candidate hashes
→ exact-byte apply to AIFE target paths
→ update real AIFE registry
→ canonical AIFE validation
→ AIFE owner integration

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

Ни один этап не начинает F2 или F3.

### F1 — архитектура серверной и информационной основы у владельца

**Контракт поведения:** после интеграций F0 актуализировать интегрированные `Program Map`,
DEV_TZ и `ADR-DATA-FOUNDATION-001` как каноническую архитектурную полномочную документацию AIFE.

**Инварианты:** нет реализации исполнения в исходном коде; нет выбора БД/транспорта;
нет изменения смысла байтов кандидата без явного обзора исправления владельцем.

**План доказательства:** проверить актуальные на тот момент AIFE HEAD/TREE, SHA-256
кандидатов, целевые пути, строку реестра, метаданные, ссылки и каноническую проверку.

**Критерии приёмки:** байты артефактов владельца интегрированы, реестр ADR синхронизирован,
проверка PASS, скрытого второго полномочного источника нет.

### F1G — шлюз правил управления владельцем для домена контракта `SERVER`

Если после F1 `SERVER` всё ещё отсутствует в актуальном каноническом словаре доменов
контрактов AIFE, до F2 необходимо выполнить отдельное расширение правил управления,
разрешённое владельцем. F1G может обновить канонические правила именования/доменов в
собственной области; этот DEV_TZ такого изменения не выполняет.

**Критерии приёмки:** до создания или регистрации `CONTRACT-SERVER-WORK-001`
доказано `SERVER_DOMAIN_OWNER_GOVERNANCE_PASS=true`.

### F2 — минимальные контракты серверного контура и данных

**Контракт поведения:** определить только минимальные именованные привязки, уменьшающие
неопределённость до создания исходного каркаса.

**Контракт основы реализации:** кода исполнения нет; контракты проходят через
`CONTRACTS_REGISTRY.md`.

**Инварианты:** максимальный начальный набор — три запланированных контракта выше; каждый
обязан пройти шлюз архитектурной ценности; `CONTRACT-SERVER-WORK-001` остаётся
заблокированным до прохождения F1G, когда он требуется.

**План доказательства:** обзор от реестра + проверка метаданных/именования +
согласованность между файлами.

**Критерии приёмки:** для F3 существуют достаточные именованные границы, при этом
решение по базе данных или транспорту не принято.

### F3 — исходный каркас серверного корня

После F2 требуется отдельное разрешение. Этап может создать воспроизводимую структуру
исходного кода/операций и минимальные интерфейсы, но не может сам разрешить развёртывание
в боевом контуре.

## План доказательства для этого пакета планирования

Квалификация F0 должна доказать:

- точные SHA, HEAD, TREE пакета проверки AIFE и чистое состояние;
- чтение реестров и соответствующих артефактов владельца начиная с полномочной документации;
- известны целевые пути AIFE;
- согласованность статуса/типа метаданных;
- зависимость домена контракта `SERVER` записана без скрытого переименования предполагаемого контракта;
- нет копии реестра/стандарта/исходного кода ETH;
- не выбраны БД или транспорт;
- нет изменения исполнения/сервера/хранилища;
- записаны хэши точных промежуточных кандидатов владельца;
- область промежуточного репозитория ограничена `AIFE/**`;
- применимая к документации/JSON каноническая проверка `Data Bridge` остаётся успешной;
- PR содержит только `AIFE/**`;
- поставка F0 классифицирована как только управляющий контур, а не физическая реализация;
- двухэтапная передача владельцу задана явно.

## Критерии приёмки

```text
AIFE_REVIEW_PACKAGE_SHA256=PASS
AIFE_HEAD_TREE=PASS
AIFE_AUTHORITY_ROUTE_READ=PASS
PROGRAM_MAP_EXISTS=PASS
DEV_TZ_EXISTS=PASS
FOUNDATION_ADR_CANDIDATE_EXISTS=PASS
AUTHORITY_BINDING_EXISTS=PASS
INTEGRATION_MANIFEST_EXISTS=PASS
ALL_OWNER_CANDIDATE_TARGET_PATHS_KNOWN=PASS
ALL_OWNER_CANDIDATE_TARGET_REGISTRIES_KNOWN_OR_NOT_APPLICABLE=PASS
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
CONTRACT_SERVER_WORK_FILE_CREATED=NO
PLANNING_PACKAGE_RESULT=PASS
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
PHYSICAL_DELIVERY=NO
NO_SECOND_AIFE_REGISTRY=PASS
NO_STANDARD_FORK=PASS
NO_ETH_SOURCE_FORK=PASS
NO_DATABASE_VENDOR_SELECTED=PASS
NO_TRANSPORT_SELECTED=PASS
NO_SERVER_IMPLEMENTATION=PASS
HORIZONTAL_SCALING_BY_DESIGN=PASS
```

## Отложенные технологии

По умолчанию отложено до измеренной необходимости / решения владельца:

- универсальный менеджер плагинов;
- общая фабрика поставщиков для всего;
- универсальный DSL рабочих процессов;
- глобальная шина событий высокой интенсивности;
- сервисная сетка (`service mesh`);
- Kubernetes;
- Kafka;
- Redis;
- ClickHouse;
- TimescaleDB;
- Iceberg;
- Delta Lake;
- векторная база данных;
- хранилище признаков (`feature store`);
- единая огромная база данных для всех доменов.

## Граница остановки

После исправленного промежуточного PR F0 и контрольного чтения:

```text
SERVER_IMPLEMENTATION=NO
AIFE_WORKSPACE_MUTATION=NO
DATABASE_CREATION=NO
CONTAINER_DEPLOYMENT=NO
OBJECT_STORAGE_CREATION=NO
P2_IMPLEMENTATION=NO
R2_RESUME=NO
```

Только следующая последовательность задач владельца:

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```

После этих интеграций владельцем: актуализация архитектурной полномочной документации F1 → расширение
правил управления доменом `SERVER` на F1G, если оно всё ещё требуется → минимальные
контракты F2 → исходный каркас серверного корня F3.
