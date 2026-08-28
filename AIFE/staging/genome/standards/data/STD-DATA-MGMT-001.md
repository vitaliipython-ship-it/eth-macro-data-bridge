---
id: STD-DATA-MGMT-001
domain: DATA
version: 0.3.0
title: STD-DATA-MGMT-001 — Data Management Principles
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-27
tags: [data, management, lifecycle, ownership, quality, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-23
doc_type: standard
language: ru
priority: P1
enforcement: Manual
related:
  - genome/standards/data/STD-DATA-SCHEMA-001.md
  - genome/standards/data/STD-DATA-MIGRATION-001.md
  - genome/standards/data/STD-DATA-VALIDATION-001.md
  - genome/standards/data/STD-DATA-RETENTION-001.md
  - genome/standards/data/STD-DATA-BACKUP-001.md
phase: 2
---

# STD-DATA-MGMT-001 — Data Management Principles

**Статус:** 📝 **DRAFT**
**Версия:** 0.3.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность, статус и владелец стандарта |
| `durability_model` | `## Классы устойчивости` | `block-level` | Общая модель устойчивости состояния |
| `publication_lifecycle` | `## Канонический publication lifecycle` | `block-level` | Единственная общая state machine публикации |
| `management_operations` | `## Управленческие операции` | `block-level` | Граница ingest/storage/publication/retention/purge |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Разделение физической и доменной власти |
| `proof_requirements` | `## Контроль и доказательства` | `block-level` | Обязательные доказательства переходов |

## Назначение

Стандарт задаёт общие правила управления жизненным циклом данных в AIFE: как
классифицировать устойчивость, отделять ingest от publication, определять владельца
физического состояния, регистрировать идентичность и безопасно выполнять retention,
retirement и purge.

Он не определяет доменную истину конкретного набора данных и не выбирает backend.

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

## Классы устойчивости

AIFE использует следующие общие классы:

| Класс | Смысл | Что не следует из класса |
| --- | --- | --- |
| `VOLATILE_PROCESS_STATE` | состояние процесса, потеря которого допустима по контракту | не является durable или published |
| `NODE_LOCAL_RECOVERABLE_STATE` | локально восстанавливаемое состояние узла | не является канонической публикацией |
| `INGEST_DURABLE_STATE` | вход принят и устойчиво сохранён с identity/integrity binding | не является канонически опубликованным |
| `CANONICAL_PUBLISHED_STATE` | данные прошли обязательный publication lifecycle и зарегистрированы | не означает автоматический purge предыдущих копий |
| `ARCHIVAL_STATE` | долговременный слой, сохраняющий обязательную идентичность и восстановимость | не означает потерю semantic authority owner |

```text
DURABLE_DOES_NOT_EQUAL_CANONICAL=YES
STORED_DOES_NOT_EQUAL_ACKED=YES
PHYSICAL_STORAGE_DOES_NOT_OWN_DOMAIN_SEMANTICS=YES
```

Переход между классами должен быть явным, наблюдаемым и доказуемым. Простое копирование
байтов или наличие файла не повышает класс устойчивости.

## Канонический publication lifecycle

Для generic publication применяется **одна** общая state machine:

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

`ACKED` разрешён только при одновременном выполнении:

```text
ACK_REQUIRES=
DURABLE_STORED
+ INDEPENDENT_READBACK_VERIFIED
+ CANONICALLY_REGISTERED
+ IDENTITY_MATCH
```

Ни один соседний DATA-стандарт не должен создавать конкурирующую publication state
machine. Доменные правила валидности и finality исполняются до/вокруг этой общей модели
владельцем домена.

```text
PUBLICATION_MODEL_COUNT=1
```

## Управленческие операции

### `INGEST_ACCEPTANCE`

Приём входа фиксирует source/domain identity, provenance, schema identity и content
integrity. Он не доказывает publication.

### `DURABLE_STORAGE`

Устойчивое хранение требует подтверждаемого content identity и класса хранения.
Повторное чтение должно проверять не только доступность, но и identity/integrity.

### `CANONICAL_PUBLICATION`

Публикация выполняется только по единой state machine выше. Физический write не является
publication сам по себе.

### `REGISTRATION`

Регистрация связывает опубликованную identity с каноническим индексом/реестром/каталогом
того контура, который имеет право её регистрировать. Registry не получает domain semantics
только потому, что содержит locator.

### `ACK`

ACK — terminal confirmation конкретной publication identity. Он запрещён до durable
storage, independent read-back, canonical registration и identity match.

### `RETENTION`

Retention определяет допустимое сохранение, tiering и срок жизни, но не является
разрешением на purge. Подробности задаёт `STD-DATA-RETENTION-001`.

### `RETIREMENT`

Retirement прекращает использование конкретной физической/логической revision только после
выполнения migration/cutover и recoverability gates.

### `PURGE`

Purge — отдельное необратимое действие и требует явной политики, authority, доказательства
recoverability/retention/legal-hold state и отсутствия блокирующего migration/cutover state.

```text
PURGE_REQUIRES_EXPLICIT_POLICY_GATE=YES
PURGE_REQUIRES_AUTHORITY_GATE=YES
PURGE_IS_NOT_IMPLIED_BY_RETENTION=YES
```

## Идентичность управления и rollback

Для mutable operational contour должна существовать точная identity accepted deployment:

```text
ROLLBACK_TARGET_IDENTITY=EXACT_PREVIOUS_ACCEPTED_DEPLOYMENT_REVISION
```

Минимальная binding-модель:

```text
SOURCE_COMMIT_TREE
+ ARTIFACT_DIGEST
+ BUILD_OR_TOOLCHAIN_IDENTITY
+ RUNTIME_CONFIG_DIGEST
+ MIGRATION_COMPATIBILITY_IDENTITY
```

Rollback не означает «вернуться к похожей конфигурации»: target должен быть
однозначно идентифицируемым и совместимым с data/migration state.

## Контроль и доказательства

Для переходов, влияющих на durability/publication/retirement/purge, evidence должен
содержать применимые:

- source/target identity;
- content integrity digest;
- provenance;
- publication state;
- independent read-back;
- registration identity;
- retention/legal-hold state;
- migration/cutover state;
- rollback target;
- actor/authority и timestamp.

## Взаимодействие с соседними стандартами

- `STD-DATA-SCHEMA-001` определяет schema/compatibility identity.
- `STD-DATA-MIGRATION-001` определяет migration, backfill, cutover и rollback gates.
- `STD-DATA-VALIDATION-001` разделяет generic validation и domain validation.
- `STD-DATA-RETENTION-001` определяет lifecycle roles и purge gates.
- `STD-DATA-BACKUP-001` доказывает backup/restore recoverability.

## Immutable generation management

Для bulk physical data канонический lifecycle использует bounded immutable generations.
Каждая опубликованная generation должна иметь immutable versioned manifest, который
однозначно связывает exact object/read-set identity. Выбор текущей generation является
отдельной transactional control-state операцией; directory listing или «последний файл»
не являются current-generation authority.

```text
IMMUTABLE_BOUNDED_VERSIONED_MANIFESTS=REQUIRED
TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION=REQUIRED
DIRECTORY_LISTING_IS_CURRENT_GENERATION_AUTHORITY=NO
ACK_BEFORE_DURABLE_WRITE_READBACK_REGISTRATION=FORBIDDEN
```

Физический backend остаётся заменяемым. Manifest/current-generation lifecycle не даёт
storage plane права менять domain semantics и не выбирает object-store product.

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
```

Конкретные adapters/products выбираются и квалифицируются только в последующем
owner-authorized F5 contour в рамках active ADR. Measurement-bound параметры и deferred
products не превращаются этим стандартом в mandatory dependencies.

## Changelog

- **2026-08-27:** currentized Server/Data architecture ownership to
  `ADR-DATA-FOUNDATION-001`; historical F3 selection gates are no longer current authority.
- **2026-08-27:** опубликованы reusable F5R rules для immutable bounded generations,
  versioned manifests и transactional current-generation registration.
- **2026-08-26:** уточнены durability classes, единый publication lifecycle,
  authority boundary, retirement/purge gates и exact rollback binding.
- **2025-10-19:** первоначальный draft.
