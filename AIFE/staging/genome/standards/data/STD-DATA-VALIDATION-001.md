---
id: STD-DATA-VALIDATION-001
domain: DATA
version: 0.2.0
title: STD-DATA-VALIDATION-001 — Data Validation
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-27
tags: [data, validation, integrity, provenance, readback, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-23
doc_type: standard
language: ru
priority: P1
enforcement: Automated
related:
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-SCHEMA-001.md
  - genome/standards/data/STD-DATA-MIGRATION-001.md
  - genome/standards/api/STD-API-ERRORS-001.md
phase: 2
---

# STD-DATA-VALIDATION-001 — Data Validation

**Статус:** 📝 **DRAFT**
**Версия:** 0.2.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность стандарта |
| `generic_validation` | `## Generic AIFE validation` | `block-level` | Общие envelope/schema/integrity/publication checks |
| `domain_validation` | `## Domain validation` | `block-level` | Владеющая доменная проверка |
| `validation_composition` | `## Композиция доказательств` | `block-level` | Когда generic и domain proof объединяются |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Запрет переноса domain authority |

## Назначение

Стандарт отделяет generic AIFE validation от domain validation. Framework-specific
библиотеки могут реализовывать часть checks, но не определяют универсальную семантику
валидности.

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

## Generic AIFE validation

Нормативная модель:

```text
AIFE_GENERIC_VALIDATION=
  envelope_identity
  + schema_version_compatibility
  + content_integrity
  + publication_state
  + readback_proof
  + provenance_presence
  + migration_completeness_proof
```

### `envelope_identity`

Проверяет stable artifact/record/container identity и отсутствие неоднозначного
разрешения объекта.

### `schema_version_compatibility`

Проверяет schema identity/version и требуемую compatibility class согласно
`STD-DATA-SCHEMA-001`.

### `content_integrity`

Проверяет digest/identity/record-set integrity достаточным для конкретного носителя
способом.

### `publication_state`

Проверяет допустимость состояния в единой publication state machine
`STD-DATA-MGMT-001`.

### `readback_proof`

Подтверждает independent read-back тех же данных/identity из целевого durable surface,
а не только success return write-операции.

### `provenance_presence`

Проверяет наличие требуемой информации о происхождении, source identity и применимых
transforms.

### `migration_completeness_proof`

Проверяет наличие и PASS completeness proof для migration/backfill, когда объект
появился в результате `STD-DATA-MIGRATION-001`.

## Domain validation

Нормативная граница:

```text
DOMAIN_VALIDATION=
  domain_identity
  + provider_semantics
  + normalization
  + finality
  + revision_gap_rules
```

Владелец домена может добавлять дополнительные domain-specific invariants, но generic
AIFE layer не должен угадывать или переписывать их.

Для ETH market data:

```text
ETH_VALIDATION_AUTHORITY=ETH_DATA_BRIDGE
ETH_VALIDATION_AUTHORITY_MOVES_TO_AIFE=NO
```

AIFE может проверить envelope/schema/integrity/publication/read-back, но не объявляет
provider candle final, symbol semantics правильной или gap/revision policy выполненной
без Data Bridge domain proof.

```text
AIFE_GENERIC_VALIDATION_REPLACES_DOMAIN_VALIDATION=NO
ETH_VALIDATION_AUTHORITY_MOVES_TO_AIFE=NO
```

## Композиция доказательств

Для data path, где требуются оба слоя:

```text
ACCEPTANCE_PROOF=
AIFE_GENERIC_VALIDATION_PASS
+ DOMAIN_VALIDATION_PASS
```

Порядок может зависеть от workflow, но final acceptance не должен скрывать, какой слой
проверил какое свойство.

Ошибки должны сохранять:

- validation layer (`GENERIC` или `DOMAIN`);
- rule/check identity;
- target identity;
- expected/observed state;
- evidence locator/receipt;
- retriable/non-retriable class, если это часть runtime contract.

## Связь с publication lifecycle

Generic validation не создаёт собственную state machine. Она проверяет допустимость
состояний:

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

ACK gate остаётся у `STD-DATA-MGMT-001`.

## Связь с migration

Migration completeness — отдельное доказательство от schema parse и content integrity.
Для historical backfill generic completeness проверяет inventory coverage; semantic
parity остаётся domain validation, если данные имеют domain semantics.

## Framework-independent implementation

Pydantic, JSON Schema, database constraints, typed models, custom validators или иные
libraries могут использоваться как implementation mechanisms. Ни одна из них не является
универсальным определением AIFE validation.

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

## Минимальный validation review

- проверяемая identity известна;
- schema version/compatibility разрешены;
- integrity proof относится к тем же данным;
- provenance присутствует;
- publication state допустим;
- independent read-back выполнен, если требуется;
- migration completeness выполнен, если применимо;
- domain validation выполнен именно domain owner-ом.

## Changelog

- **2026-08-27:** currentized Server/Data architecture ownership to
  `ADR-DATA-FOUNDATION-001`; historical F3 selection gates are no longer current authority.
- **2026-08-26:** явно разделены generic AIFE validation и domain validation; добавлены
  read-back, provenance и migration completeness proofs; framework semantics сделаны
  ненормативными.
- **2025-10-19:** первоначальный draft.
