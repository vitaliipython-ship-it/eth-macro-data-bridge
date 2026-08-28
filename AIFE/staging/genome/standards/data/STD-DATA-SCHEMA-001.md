---
id: STD-DATA-SCHEMA-001
domain: DATA
version: 0.3.0
title: STD-DATA-SCHEMA-001 — Database Schema Standards
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-27
tags: [data, schema, database, compatibility, integrity, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-23
doc_type: standard
language: ru
priority: P1
enforcement: Manual
related:
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-MIGRATION-001.md
  - genome/standards/data/STD-DATA-VALIDATION-001.md
phase: 2
---

# STD-DATA-SCHEMA-001 — Database Schema Standards

**Статус:** 📝 **DRAFT**
**Версия:** 0.3.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность стандарта |
| `schema_identity` | `## Идентичность схемы` | `block-level` | Schema/version/content binding |
| `compatibility` | `## Совместимость` | `block-level` | Forward/backward и migration compatibility |
| `capabilities` | `## Требования к данным и запросам` | `block-level` | Типы, ограничения, query/index capabilities |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Generic schema vs domain semantics |

## Назначение

Стандарт задаёт vendor-independent требования к структуре данных: идентичности схемы,
версии, совместимости, ограничениям полей/типов, integrity binding и требуемым
query/index capabilities.

Он не выбирает database/storage vendor и не определяет доменную истину.

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

## Идентичность схемы

Каждый persisted/publication artifact, для которого применима схема, должен иметь
однозначно разрешаемую schema identity. Минимальная модель:

```text
SCHEMA_IDENTITY=
SCHEMA_NAME_OR_ID
+ SCHEMA_VERSION
+ COMPATIBILITY_CLASS
+ CONTENT_INTEGRITY_BINDING
```

Если формат допускает несколько schema families, identity должна также включать family
или namespace, достаточный для однозначного разрешения.

Schema version не должна выводиться из имени конкретной БД, таблицы, bucket, collection
или filesystem path.

## Совместимость

Для каждого изменения схемы необходимо классифицировать применимые свойства:

- backward compatibility — новый consumer читает ранее допустимые данные;
- forward compatibility — предыдущий допустимый consumer обрабатывает новые данные в
  рамках явно разрешённой стратегии;
- full/bidirectional compatibility — когда контракт требует обе стороны;
- breaking change — требует migration/cutover plan;
- migration compatibility — допустимость чтения/записи во время переходного окна.

Нельзя объявлять совместимость только по успешному schema parse. Должны учитываться
required/optional fields, defaults, enums, units, nullability, semantic constraints и
consumer expectations.

## Поля, типы и ограничения

Нормативные schema requirements описывают **смысловые capabilities**, а не конкретный
DDL/ORM/API:

- стабильная идентичность записи/объекта;
- тип и диапазон;
- обязательность/опциональность;
- единицы и нормализация, если применимо;
- uniqueness;
- referential/relationship constraints;
- ordering/time semantics, если они являются частью generic contract;
- content integrity binding;
- provenance fields или links, если требуются соседними стандартами.

Domain-specific constraints (например provider finality или market symbol semantics)
остаются у владельца домена.

## Требования к запросам и индексированию

Стандарт может требовать capability вида:

```text
LOOKUP_BY_STABLE_ID
RANGE_BY_TIME
ORDERED_SCAN
UNIQUENESS_ENFORCEMENT
PARTITION_OR_SHARD_ADDRESSABILITY
POINT_IN_TIME_READ
```

Способ реализации этих capabilities не задаётся. Index, partition, materialized view,
key-value projection, object prefix или иной механизм может быть выбран позже, если
обеспечивает требуемую семантику и доказательство.

## Schema/version migration binding

Любое breaking или потенциально breaking изменение должно связать:

```text
SOURCE_SCHEMA_IDENTITY
TARGET_SCHEMA_IDENTITY
MIGRATION_IDENTITY
COMPATIBILITY_PROOF
ROLLBACK_COMPATIBILITY
```

Процедура migration определяется `STD-DATA-MIGRATION-001`. Нельзя повышать schema
revision так, чтобы физические данные стали неразрешимыми или rollback стал неявно
невозможен.

## Content integrity

Schema validation и content integrity — разные свойства. Успешная проверка структуры
не доказывает, что прочитаны те же байты/записи, которые были записаны или опубликованы.

Применимый artifact должен иметь digest/identity или эквивалентный механизм, позволяющий
связать write, read-back и migration proof с тем же содержанием.

## Publication compatibility

Schema standard не создаёт собственную state machine. Он совместим с
`STD-DATA-MGMT-001`:

```text
VALIDATED_DOMAIN_INPUT
→ INGEST_DURABLE
→ STAGED
→ PUBLISHING
→ DURABLE_STORED
→ INDEPENDENT_READBACK_VERIFIED
→ CANONICALLY_REGISTERED
→ ACKED
```

Schema compatibility является одним из входных доказательств, но не заменяет
read-back/registration/ACK gates.

## Bulk representation и PIT binding

Для high-cardinality bulk tabular classes каноническая physical representation обязана
поддерживать Parquet. Native immutable blobs разрешены там, где преобразование в tabular
форму уменьшает source fidelity или уничтожает обязательное evidence. Это правило не
выбирает object-store product, partition granularity, target file size, row-group size или
compression parameters: они остаются measurement/qualification bound.

```text
BULK_TABULAR_FORMAT=PARQUET_REQUIRED
RAW_NATIVE_BLOBS=ALLOWED_WHEN_SOURCE_FIDELITY_REQUIRES
PHYSICAL_LAYOUT_VERSION_REQUIRED=YES
```

Для point-in-time/replay-capable datasets schema/layout contract должен позволять связать
применимые поля:

```text
EFFECTIVE_AT
KNOWN_AT
PROVIDER_OR_SOURCE_REVISION
SOURCE_SEQUENCE_OR_CHANGE_UPDATE_IDENTITY
GAP_OR_RESYNC_EVIDENCE
EXACT_GENERATION_AND_READ_SET
SCHEMA_OR_LAYOUT_VERSION
REPLAY_CUTOFF
METHOD_MODEL_STRATEGY_VERSION
```

Storage-native snapshot/time-travel не заменяет эту information-horizon identity.

## Независимость от конкретной реализации

Ни один vendor, storage engine, queue, object store, database или scheduler transport
не является нормативно выбранным этим стандартом. Текущая Server/Data architecture уже
опубликована владельцем в `ADR-DATA-FOUNDATION-001`; этот стандарт не переоткрывает
исторические F3 selection gates и не выбирает product/vendor.

```text
VENDOR_NEUTRALITY=YES
DATABASE_VENDOR_SELECTED=NO
STORAGE_ENGINE_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
STANDARD_DOES_NOT_SELECT_PRODUCT_VENDOR=YES
STANDARD_DOES_NOT_OVERRIDE_ACTIVE_ADR=YES
SERVER_DATA_ARCHITECTURE_OWNER=ADR-DATA-FOUNDATION-001
PRODUCT_SELECTION_REMAINS_F5_QUALIFICATION_BOUND=YES
PARQUET_AS_BULK_TABULAR_FORMAT=ARCHITECTURE_REQUIRED
PARQUET_PRODUCT_OR_STORAGE_VENDOR=NOT_APPLICABLE
OBJECT_STORAGE_PRODUCT=UNSELECTED
PARQUET_LAYOUT_PARAMETERS=MEASUREMENT_AND_F5_QUALIFICATION_BOUND
```

`Parquet` здесь является обязательным bulk-tabular **форматом**, а не выбранным vendor или
storage product. Object/blob product остаётся unselected. Exact partition granularity,
target file size, row-group size и compression parameters остаются measurement/F5
qualification bound. Другие конкретные adapters/products могут выбираться только в
последующем owner-authorized F5 contour в рамках active ADR.

## Ненормативные профили

Конкретные DDL, ORM, JSON Schema, Avro/Protobuf schema, database collections, object
layouts и implementation-specific storage profiles могут документироваться отдельными
profile/implementation артефактами. Они не должны превращаться в универсальную норму этого
стандарта или переопределять architecture-required bulk-tabular Parquet format.

## Changelog

- **2026-08-27:** currentized Server/Data architecture ownership to
  `ADR-DATA-FOUNDATION-001` and removed the contradiction that treated required Parquet as
  merely an unselected future option; product/layout choices remain qualification-bound.
- **2026-08-27:** добавлены F5R requirements для Parquet/native immutable representation,
  physical layout versioning и PIT/replay read-set binding.
- **2026-08-26:** нормативная модель отвязана от конкретных database vendors; добавлены
  schema identity, compatibility classes, capability-based indexing и integrity binding.
- **2025-10-19:** первоначальный draft.
