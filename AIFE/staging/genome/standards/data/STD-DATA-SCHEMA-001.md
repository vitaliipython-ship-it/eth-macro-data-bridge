---
id: STD-DATA-SCHEMA-001
domain: DATA
version: 0.1.0
title: STD-DATA-SCHEMA-001 — Database Schema Standards
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-26
tags: [data, schema, database, compatibility, integrity, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-22
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
**Версия:** 0.1.0
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


## Ненормативные профили

Конкретные DDL, ORM, JSON Schema, Avro/Protobuf schema, database collections, object
layouts и columnar formats могут документироваться отдельными profile/implementation
артефактами. Они не должны превращаться в универсальную норму этого стандарта.

## Changelog

- **2026-08-26:** нормативная модель отвязана от конкретных database vendors; добавлены
  schema identity, compatibility classes, capability-based indexing и integrity binding.
- **2025-10-19:** первоначальный draft.
