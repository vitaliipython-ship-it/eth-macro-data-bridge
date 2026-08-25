---
id: AIFE-SERVER-DATA-DEV-TZ-2026-08-24
title: "DEV_TZ: Серверная и информационная основа AIFE"
version: '0.1'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
category: architecture
doc_type: spec
language: ru
tags: [dev-tz, server, data, foundation, contracts, migration, scheduling, compliance]
---

# DEV_TZ: Серверная и информационная основа AIFE

## Physical Use Contract

```text
physical-use class: control-plane-evidence-only
CURRENT_DELIVERY_CLAIM=CONTROL_PLANE_ONLY_NO_RUNTIME_INSTALLATION
AIFE_SERVER_ROLE=GENERIC_EXECUTION_SCHEDULING_STORAGE_MECHANISM
DATA_BRIDGE_ETH_SEMANTIC_AUTHORITY=YES
AIFE_WORKSPACE_DIRECT_PHYSICAL_STORAGE_ACCESS=NO
PHYSICAL_BACKEND_IS_ETH_SEMANTIC_AUTHORITY=NO
SERVER_IMPLEMENTATION=NO
STORAGE_IMPLEMENTATION=NO
SCHEDULER_IMPLEMENTED=NO
MIGRATION_EXECUTED=NO
PHYSICAL_ACTIVATION_REQUIRES_SEPARATE_QUALIFICATION_AND_OWNER_AUTHORIZATION=YES
```

Этот DEV_TZ остаётся управляющим контрактом будущей реализации, а не физической
поставкой. AIFE Server должен предоставлять общий механизм исполнения, планирования и
жизненного цикла хранения; доменная семантика ETH, идентичности, нормализация,
валидация, финальность и правила разрешения остаются полномочиями Data Bridge.
Потребители AIFE Workspace используют будущие service/repository/gateway boundaries и
не получают прямого доступа к базе данных, объектному хранилищу или файловым путям.
Физический backend не становится доменным источником истины. Реализация runtime,
хранилища, планировщика и миграции этим F0-контуром не выполняется; любая будущая
physical activation требует отдельной проверки, квалификации и разрешения владельца.

## 1. Назначение и жёсткая граница

Этот DEV_TZ — долговечный единый источник планирования для последующей декомпозиции задач без
контекста чата. Он не разрешает реализацию серверного исполнения или физического хранения.

```text
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
SERVER_IMPLEMENTATION=NO
MIGRATION_EXECUTED=NO
SCHEDULER_IMPLEMENTED=NO
P2_IMPLEMENTATION=NO
R2_RESUMED=NO
PRODUCTION_ROUTE_CHANGED=NO
DATABASE_VENDOR_SELECTED=NO
TRANSPORT_SELECTED=NO
```

Архитектурные инварианты: один канонический серверный корень AIFE; не один монолит, контейнер
или база данных; горизонтальное масштабирование обязательно по замыслу; первоначально допустим
один сервер; публичный маршрут `AppContext` сохраняется; второй маршрут зависимостей или данных
не создаётся; семантика принадлежит домену.

## 2. Целевое владение

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS
ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
```

Потребители не получают прямые полномочия к БД, объектному хранилищу или файловым путям и не
выбирают узел, контейнер или физическую внутреннюю реализацию.

## 3. Устойчивость и публикация

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

Минимальная будущая цепочка:

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

Восстанавливаемое состояние одного узла не является единственной канонической истиной.
Принятая работа должна получить стабильную идентичность и устойчивую контрольную точку либо
промежуточное состояние до возможной потери исполнителя. Подтверждение публикации допускается
только после независимого чтения и регистрации в соответствии с будущим контрактом.

## 4. Целевое состояние физического корпуса данных

Цель миграции относится к физическим полезным данным и истории, а не к доменным полномочиям.
Будущий актуальный перечень может охватывать `data/**`, `history/**`, `archive/**`,
исторические данные `derivatives/**`, `options/**`, `liquidity/**`, ограниченную историю
Git WARM и объекты GitHub Release с глубокой историей.

```text
DATA_BRIDGE_EXISTING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_GROWING_CORPUS_MIGRATION_TARGET=YES
NEW_DATA_EVENTUALLY_PUBLISHED_TO_AIFE_MANAGED_STORAGE=YES
MIGRATION_NOW=NO
BULK_DELETE_NOW=NO
CURRENT_PRODUCTION_COLLECTION_CHANGE_NOW=NO
LEGACY_READABILITY_BREAK_ALLOWED=NO
```

## 5. Стратегия миграции накопленной истории

Примитивная схема `COPY_FILES → DELETE_SOURCE` запрещена. Будущая единица миграции должна
сохранять или доказывать доменную идентичность, идентичность ряда и наблюдения, временной
диапазон, состав, хэш содержимого, схему и версию, `effective_at`, `known_at`, происхождение,
семантику финальности и ревизий, а также каноническую читаемость.

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

Сначала доказывается корректная публикация новых входящих данных, затем выполняется обратное
заполнение накопленной истории.

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

Условия выхода F5M включают:

```text
MIGRATION_INVENTORY_FROZEN
SOURCE_IDENTITIES_VERIFIED
TARGET_IDENTITIES_VERIFIED
CONTENT_INTEGRITY_PASS
TIME_RANGE_COMPLETENESS_PASS
SEMANTIC_READ_PARITY_PASS
PROVENANCE_PRESERVED
INDEPENDENT_READBACK_PASS
LEGACY_READABILITY_PRESERVED
CUTOVER_OWNER_GATE_PASS
```

## 6. Полномочия планировщика и политики наступления срока

AIFE должен предоставлять общий механизм часов и вычисления наступившей работы, стабильную
идентичность работы, устойчивое состояние, эквивалент владения или аренды, контрольную точку,
повторы и восстановление, конечное состояние, подключаемую политику обработки пропущенного
слота, ограничение давления очереди и число исполнителей `1..N`. Домен определяет возможность,
периодичность, наступивший слот, допустимость обратного заполнения, финальность, источник,
значение пропуска и окно свежести. Значения `1m/5m/15m/1h/8h/daily` являются доменной
политикой, а не онтологией платформы.

```text
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
AIFE_SERVER_OWNS_GENERIC_WORK_EXECUTION=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
EXTERNAL_CRON_IS_CANONICAL_EXECUTION_AUTHORITY=NO
N8N_CANONICAL_SCHEDULER=NO
N8N_REQUIRED_FOR_PERIODIC_COLLECTION=NO
```

## 7. Модель периодической работы

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

Модель `worker → sleep(...) → collect` и независимый `cron` на каждом узле не являются
каноническими полномочиями. Повтор одной логической работы должен предотвращаться либо
сворачиваться идемпотентно.

```text
SAME_LOGICAL_SLOT_DUPLICATE_EXECUTION=PREVENT_OR_IDEMPOTENTLY_COLLAPSE
```

## 8. Роль внешней автоматизации n8n

`n8n` разрешён для уведомлений, Telegram, электронной почты, Slack, CRM, распространения
отчётов, ручных процессов аналитика и внешней бизнес-автоматизации. Он не владеет политикой
наступления срока рыночных данных, каноническим состоянием работы AIFE, живостью сервера или
периодическим сбором данных. Внешний или ручной запуск является только дополнительным входом.

## 9. Рестарт, пропущенные слоты и масштабирование

После перезапуска исполнение должно различать завершённые, выполняемые или повторяемые,
пропущенные, допустимые для обратного заполнения и просроченные по доменной политике слоты.

```text
SERVER_RESTART_DOES_NOT_ERASE_SCHEDULE_SEMANTICS=YES
```

`TaskManager.run_periodic_task` на закреплённом снимке AIFE — совместимый помощник, а не
действующий контракт планировщика. Перед реализацией эту границу нужно согласовать, чтобы не
создать второй маршрут.

## 10. Будущие Artifact Contracts

`CONTRACT-SERVER-WORK-001` должен рассмотреть: стабильную идентичность работы, домен,
возможность, тип работы, субъект или раздел, идентичность наступившего слота или расписания,
попытку, эквивалент владения или аренды, контрольную точку, повтор и восстановление, конечное
состояние, ссылку на политику и идентичность корреляции или трассировки.

`CONTRACT-DATA-PUBLICATION-001` должен связать логическую идентичность публикации, устойчивую
запись, границу адаптера хранения, независимое чтение, регистрацию, подтверждение,
идемпотентность и конечное состояние.

`CONTRACT-DATA-ACCESS-001` должен связать семантический запрос, домен, возможность, диапазон,
срез, политику, план разрешения и доступа, каноническое чтение или формирование результата,
происхождение, диагностику и отказ при неопределённости.

```text
SCHEDULING_BOUNDARY_MERGED_WITH_SERVER_WORK_CONTRACT=YES_CANDIDATE
SEPARATE_SCHEDULER_ARTIFACT_CONTRACT=NOT_REQUIRED_YET
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED=NO
CONTRACT_SERVER_WORK_FILE_CREATED=NO
```

## 11. Выравнивание стандартов данных

Закреплённый реестр фиксирует все шесть стандартов как `0.1.0 / draft`:

```text
STD-DATA-MGMT-001
STD-DATA-SCHEMA-001
STD-DATA-MIGRATION-001
STD-DATA-VALIDATION-001
STD-DATA-RETENTION-001
STD-DATA-BACKUP-001
```

Они не являются автоматически готовой обязательной базой для боевой реализации. До F2
требуется решение владельца `AS_IS|AMEND_REQUIRED|SPLIT_REQUIRED|MERGE_REQUIRED|DEFER`.

```text
DATA_STANDARDS_ALIGNMENT_REQUIRED=YES
DATA_STANDARDS_ALIGNMENT_BEFORE_F2=YES
DATA_STANDARDS_AUTO_APPROVED=NO
DATA_STANDARDS_AUTO_PROMOTED=NO
DATA_STANDARDS_IMPLEMENTATION_CAN_SILENTLY_OVERRIDE=NO
F2_ENTRY_REQUIRES_DATA_STANDARDS_DISPOSITION=YES
DATA_STANDARDS_ALIGNMENT_SELECTS_DATABASE_VENDOR=NO
```

## 12. Классификация каждого стандарта данных

- `STD-DATA-MGMT-001`: проверить разделение доменной семантики и физического хранения,
  различие устойчивости приёма и канонической истории, запрет единственной истины только на
  одном узле и классы `VOLATILE_PROCESS_STATE`, `NODE_LOCAL_RECOVERABLE_STATE`,
  `INGEST_DURABLE_STATE`, `CANONICAL_PUBLISHED_STATE`, `ARCHIVAL_STATE`.
- `STD-DATA-SCHEMA-001`: проверить идентичность, версию, совместимость и развитие схемы,
  ограничения и требования к индексированию, доменное владение и границу физического
  представления. Примеры SQLite/MongoDB/PostgreSQL не должны означать универсальный выбор БД.
  `DATA_SCHEMA_STANDARD_MUST_NOT_IMPLY_UNIVERSAL_DATABASE_VENDOR=YES`.
- `STD-DATA-MIGRATION-001`: различать `SCHEMA_MIGRATION`, `DATA_MIGRATION`,
  `PHYSICAL_BACKEND_MIGRATION`, `HISTORICAL_BACKFILL`, `AUTHORITY_OR_CUTOVER_MIGRATION`.
  F5M служит первым проверочным случаем; нужны перечень, сохранение идентичности, целостность,
  полнота, происхождение, независимое чтение, паритет чтения, обратимость, шлюз переключения и
  сохранение читаемости прежнего маршрута.
- `STD-DATA-VALIDATION-001`: разделить общую проверку AIFE и доменную проверку; покрыть
  идентичность, схему, целостность содержимого, публикацию, независимое чтение, происхождение и
  полноту миграции. Проверка, специфичная для ETH, остаётся доменной.
- `STD-DATA-RETENTION-001`: роли `HOT/WARM/COLD/ARCHIVAL/RETIREMENT/PURGE` должны оставаться
  логическими и не означать конкретного поставщика; решение об удержании учитывает полномочия,
  восстанавливаемость, состояние миграции, происхождение и шлюз выведения.
  `RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES`.
- `STD-DATA-BACKUP-001`: проверить область резервной копии и класс полномочий, целостность,
  RPO/RTO где применимо, независимое восстановление, проверку и репетицию восстановления,
  происхождение и неизменяемую либо удалённую копию там, где это обосновано.
  `BACKUP_EXISTS != RESTORE_IS_PROVEN`.

## 13. Соответствие стандартам API

Закреплённый набор `STD-API-DESIGN-001`, `STD-API-DOCS-001`, `STD-API-ERRORS-001`,
`STD-API-RATE-001`, `STD-API-VERSIONING-001` имеет `1.0.0 / approved`.

```text
API_STANDARDS_COMPLIANCE_REQUIRED=YES
API_STANDARDS_DEFAULT_ACTION=CONFORM
API_STANDARDS_IMPLEMENTATION_MAY_IGNORE=NO
API_STANDARD_AMENDMENT_ALLOWED=ONLY_IF_PROVEN_GAP_AND_OWNER_APPROVED
SEMANTIC_CONTRACT_FIRST=YES
TRANSPORT_SELECTION_AFTER_SEMANTIC_BOUNDARY=YES
API_COMPLIANCE_AFTER_TRANSPORT_APPLICABILITY_IS_KNOWN=YES
```

Если будет выбран HTTP/REST, будущая матрица должна проверить семантику URI и методов,
документирование публичного интерфейса, оболочку ошибок, идентичность клиента и ограничение
частоты, а также версионирование. Если gRPC, WebSocket или другой транспорт обнаруживает
разрыв применимости, нельзя изображать соответствие: сначала классифицируется разрыв и
получается решение владельца.

## 14. Соответствие требованиям безопасности

Закреплённый утверждённый контур включает `STD-SEC-AUTH-001`,
`STD-SEC-ENCRYPTION-001`, `STD-SEC-LOG-001`, `STD-SEC-PRINCIPLES-001`,
`STD-SEC-REVIEW-001`, `STD-SEC-SECRETS-001`, `STD-SEC-VULN-001`.

```text
SERVER_SECURITY_COMPLIANCE_REQUIRED=YES
SECURITY_COMPLIANCE_BEFORE_PRODUCTION_CAPABLE_PUBLIC_INTERFACE=YES
SECURITY_COMPLIANCE_EXECUTED=NO
```

Будущая реализация не должна вводить жёстко заданные учётные данные, учётные данные хранилища
или БД в Workspace/UI, обход аутентификации, секреты в журналах или доказательствах либо
аутентификацию транспорта вне утверждённого маршрута безопасности.

## 15. Соответствие требованиям журналирования

`STD-LOG-001` имеет `2.3.0 / approved`.

```text
SERVER_LOGGING_COMPLIANCE_REQUIRED=YES
STD_LOG_001_COMPLIANCE_REQUIRED=YES
LOGGING_COMPLIANCE_EXECUTED=NO
```

Отдельный серверный стандарт журналирования по умолчанию не создаётся.
`STD-MON-HEALTH-001` и `STD-MON-METRICS-001` остаются `0.1.0 / draft`; их выравнивание
требуется до боевой наблюдаемости, но относится к отдельному будущему рассмотрению.

## 16. Порядок: семантика → контракт → транспорт → соответствие → реализация

```text
F1_ARCHITECTURE_AUTHORITY_CURRENTIZATION
→ DATA_STANDARDS_ALIGNMENT_GATE
→ F1G_SERVER_DOMAIN_GOVERNANCE_EXTENSION_IF_STILL_REQUIRED
→ F2_MINIMUM_ARTIFACT_CONTRACTS
→ TRANSPORT_APPLICABILITY_OWNER_DECISION
→ API_SECURITY_LOGGING_COMPLIANCE_GATE
→ F3_SERVER_ROOT_SOURCE_SKELETON
```

```text
F3_PUBLIC_INTERFACE_ENTRY_REQUIRES_COMPLIANCE_DISPOSITION=YES
```

## 17. Обработка разрыва между стандартом и реальным вариантом использования

```text
USE_CASE
→ CONTRACT_REQUIREMENT
→ STANDARD_COMPLIANCE_CHECK
→ GAP_CLASSIFICATION
```

Допустимые классификации:

```text
IMPLEMENTATION_DEFECT
CONTRACT_DEFECT
STANDARD_GAP
STANDARD_NOT_APPLICABLE
OWNER_DECISION_REQUIRED
```

Только `STANDARD_GAP`, рассмотренный владельцем, может привести к изменению существующего
стандарта или созданию нового.

## 18. Правило создания новых стандартов

```text
NEW_STANDARD_DEFAULT_DECISION=DO_NOT_ADD
NEW_SERVER_STANDARD_CREATED=NO
```

Новый `STD-SERVER-*` допустим только при повторном использовании, межкомпонентной или
междоменной применимости, невозможности корректно расширить существующий стандарт и явном
разрешении владельца. `STD-SERVER-SCHEDULER-001`, `STD-SERVER-STORAGE-001`,
`STD-SERVER-WORKER-001`, `STD-SERVER-MIGRATION-001` сейчас не создаются.

## 19. Будущие задачи и входные условия

```text
DATA_STANDARDS_ALIGNMENT_TASK=AIFE-SERVER-DATA-FOUNDATION-DATA-STANDARDS-ALIGNMENT-V1
SERVER_DOMAIN_GOVERNANCE_TASK=AIFE-SERVER-DATA-FOUNDATION-SERVER-DOMAIN-GOVERNANCE-V1
INTERFACE_COMPLIANCE_TASK=AIFE-SERVER-DATA-FOUNDATION-API-SECURITY-LOGGING-COMPLIANCE-V1
DATA_STANDARDS_ALIGNMENT_GATE=PASS_OR_EXPLICIT_OWNER_APPROVED_DEFERRED_ITEM_WITH_REASON
F2_ENTRY_REQUIRES_DATA_STANDARDS_DISPOSITION=YES
API_APPLICABILITY_CLASSIFIED=YES_BEFORE_PUBLIC_INTERFACE_IMPLEMENTATION
SECURITY_COMPLIANCE_PLAN=PASS_REQUIRED
LOGGING_COMPLIANCE_PLAN=PASS_REQUIRED
```

## 20. Граница остановки

Эта задача не меняет стандарты данных, API, безопасности, журналирования или мониторинга; не
создаёт домен `SERVER`, файлы `Artifact Contract`, транспорт, базу данных, объектное хранилище,
Parquet, серверный код, код планировщика или поток `n8n`; не мигрирует корпус, не меняет текущую
частоту или маршрут сбора данных, не реализует P2 и не возобновляет R2.

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```
