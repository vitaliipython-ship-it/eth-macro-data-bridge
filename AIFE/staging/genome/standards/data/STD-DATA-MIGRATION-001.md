---
id: STD-DATA-MIGRATION-001
domain: DATA
version: 0.1.0
title: STD-DATA-MIGRATION-001 — Migration Process
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-26
tags: [data, migration, backfill, cutover, rollback, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-22
doc_type: standard
language: ru
priority: P1
enforcement: Automated
related:
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-SCHEMA-001.md
  - genome/standards/data/STD-DATA-VALIDATION-001.md
  - genome/standards/data/STD-DATA-BACKUP-001.md
  - genome/standards/data/STD-DATA-RETENTION-001.md
phase: 2
---

# STD-DATA-MIGRATION-001 — Migration Process

**Статус:** 📝 **DRAFT**
**Версия:** 0.1.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность стандарта |
| `migration_types` | `## Виды миграции` | `block-level` | Нормативная классификация migrations |
| `migration_contract` | `## Контракт миграции` | `block-level` | Identity/inventory/provenance/integrity/completeness |
| `cutover_rollback` | `## Cutover и rollback` | `block-level` | Условия переключения и возврата |
| `proof_requirements` | `## Доказательство завершения` | `block-level` | Independent read-back и parity |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Сохранение domain authority |

## Назначение

Стандарт определяет единый generic процесс schema/data/backend migration, исторического
backfill и authority/cutover migration. Миграция считается завершённой не по факту
копирования, а по доказательству identity, integrity, completeness, independent read-back,
parity и выполнению cutover/rollback gates.

## Граница полномочий

Этот стандарт определяет **общие** требования AIFE к данным и физическому жизненному
циклу. Физическое размещение, durable storage или исполнение не создают доменную
семантическую власть.

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS
ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
AIFE_PHYSICAL_STORAGE_IS_ETH_SEMANTIC_AUTHORITY=NO
PHYSICAL_LOCATION_DEFINES_DOMAIN_TRUTH=NO
```

Для других доменов действует тот же принцип: generic AIFE mechanisms не подменяют
domain-owner semantics.


## Виды миграции

Каждая операция должна быть классифицирована как один или несколько типов:

```text
SCHEMA_MIGRATION
DATA_MIGRATION
PHYSICAL_BACKEND_MIGRATION
HISTORICAL_BACKFILL
AUTHORITY_OR_CUTOVER_MIGRATION
```

### `SCHEMA_MIGRATION`

Изменение schema identity/compatibility. Должно связывать source/target schema и
compatibility proof согласно `STD-DATA-SCHEMA-001`.

### `DATA_MIGRATION`

Преобразование или перенос конкретного data inventory между представлениями/структурами.

### `PHYSICAL_BACKEND_MIGRATION`

Перенос физического корпуса между storage backends без автоматического переноса domain
semantic authority.

### `HISTORICAL_BACKFILL`

Дозагрузка или восстановление исторического диапазона. Требует inventory coverage,
provenance, gap/completeness proof и domain validation для соответствующего домена.

### `AUTHORITY_OR_CUTOVER_MIGRATION`

Изменение активного physical route или owner binding. Требует отдельного cutover gate;
простая доступность target не означает смену authority.

## Контракт миграции

Для каждой применимой migration фиксируются:

```text
MIGRATION_ID
MIGRATION_TYPE
SOURCE_IDENTITY
TARGET_IDENTITY
SOURCE_INVENTORY
TARGET_EXPECTED_INVENTORY
PROVENANCE
INTEGRITY_METHOD
COMPLETENESS_CRITERIA
READBACK_METHOD
PARITY_CRITERIA
ROLLBACK_CONDITIONS
CUTOVER_CONDITIONS
LEGACY_READABILITY_REQUIREMENTS
```

Inventory должен быть bounded и проверяемым: range, partitions, objects, records,
artifact set или другой canonical scope. Формулировка «все данные» без разрешимой
границы недостаточна.

## Последовательность

Базовый маршрут:

```text
DECLARE_SOURCE_TARGET_IDENTITY
→ FREEZE_INVENTORY_AND_PRECONDITIONS
→ VALIDATE_SOURCE
→ EXECUTE_OR_REHEARSE_MIGRATION
→ VERIFY_TARGET_INTEGRITY
→ INDEPENDENT_READBACK
→ COMPLETENESS_PROOF
→ DOMAIN_PARITY_PROOF_IF_APPLICABLE
→ ROLLBACK_READINESS
→ CUTOVER_GATE_IF_APPLICABLE
→ POST_CUTOVER_OBSERVATION
→ RETIREMENT_GATE
```

Физическая migration может быть многоволновой; каждая волна должна иметь predecessor
identity и собственный receipt.

## Доказательство завершения

```text
MIGRATION_COMPLETION_REQUIRES=
TARGET_IDENTITY_MATCH
+ INTEGRITY_PASS
+ COMPLETENESS_PASS
+ INDEPENDENT_READBACK_PASS
+ PARITY_PASS_IF_APPLICABLE
+ ROLLBACK_READINESS_PASS
```

```text
MIGRATION_COMPLETION_BY_COPY_ONLY=NO
DELETE_OLD_DATA_BEFORE_PROOF=NO
CUTOVER_BEFORE_PARITY_PROOF=NO
```

Parity для domain data должен проверяться через domain-owner semantics. Generic AIFE
validation не может объявить ETH market history semantically equivalent без Data Bridge.

## Cutover и rollback

Cutover разрешён только если:

- target identity однозначна;
- completeness/integrity/read-back PASS;
- domain parity PASS, когда применимо;
- active readers/writers и transition window определены;
- rollback target доступен и совместим;
- legacy readability policy выполнена;
- отдельный authority/cutover decision разрешает переход.

Rollback target:

```text
ROLLBACK_TARGET_IDENTITY=EXACT_PREVIOUS_ACCEPTED_DEPLOYMENT_REVISION
```

Binding:

```text
SOURCE_COMMIT_TREE
+ ARTIFACT_DIGEST
+ BUILD_OR_TOOLCHAIN_IDENTITY
+ RUNTIME_CONFIG_DIGEST
+ MIGRATION_COMPATIBILITY_IDENTITY
```

Нельзя откатываться к «последней известной хорошей» конфигурации без точной identity.

## Legacy readability и retirement

Legacy bytes/route сохраняются читаемыми до тех пор, пока migration/cutover policy не
разрешит retirement. `STD-DATA-RETENTION-001` не может автоматически удалить legacy
данные только по возрасту, если migration proof или rollback window ещё открыты.

## Publication lifecycle

Migration standard не создаёт отдельную publication state machine. Если target должен
стать канонически опубликованным, используется единственная модель
`STD-DATA-MGMT-001`; ACK не разрешён до durable storage, independent read-back,
canonical registration и identity match.

## Независимость от конкретной реализации

Ни один vendor, storage engine, queue, object store, database или scheduler transport
не является нормативно выбранным этим стандартом.

```text
DATABASE_VENDOR_SELECTED=NO
STORAGE_ENGINE_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
```

SQLite, MongoDB, PostgreSQL, Redis, S3, Parquet, Kafka, NATS, RabbitMQ и другие
технологии допустимы только как **ненормативные примеры или будущие профили** после
отдельного архитектурного выбора. Конкретные решения остаются за
`F3_BACKEND_SELECTION_GATE`, `F3_EXECUTION_TRANSPORT_GATE` и
`F3_TRANSPORT_AND_COMPLIANCE_GATE`.


## Проверка миграции

Минимальный review должен ответить:

- source/target identity совпадают с планом;
- inventory полный и воспроизводимый;
- provenance сохранён;
- integrity и independent read-back выполнены;
- gaps/duplicates/transforms объяснимы;
- parity доказан owner-правилами домена;
- rollback реально достижим;
- cutover не разрушает legacy readability раньше разрешённого момента.

## Changelog

- **2026-08-26:** добавлены пять migration classes, first-class historical backfill и
  physical backend migration, completeness/read-back/parity/cutover/rollback gates.
- **2025-10-19:** первоначальный draft.
