---
id: STD-DATA-BACKUP-001
domain: DATA
version: 0.3.0
title: STD-DATA-BACKUP-001 — Backup & Restore
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-27
tags: [data, backup, restore, recovery, integrity, rpo, rto, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-23
doc_type: standard
language: ru
priority: P1
enforcement: Automated
related:
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-RETENTION-001.md
  - genome/standards/data/STD-DATA-MIGRATION-001.md
  - docs/85-Operations/README.md
phase: 2
---

# STD-DATA-BACKUP-001 — Backup & Restore

**Статус:** 📝 **DRAFT**
**Версия:** 0.3.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность стандарта |
| `backup_states` | `## Состояния доказательства` | `block-level` | Exists/integrity/restore/rehearsal |
| `backup_contract` | `## Backup contract` | `block-level` | Scope/identity/RPO/RTO/copies |
| `restore_contract` | `## Restore contract` | `block-level` | Target/validation/proof binding |
| `rehearsal` | `## Restore rehearsal` | `block-level` | Обязательное доказательство восстановимости |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Backup не владеет domain truth |

## Назначение

Стандарт задаёт vendor-independent требования к backup и restore. Наличие backup-файла
или successful backup job не является доказательством восстановимости.

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

## Состояния доказательства

```text
BACKUP_EXISTS
BACKUP_INTEGRITY_VERIFIED
RESTORE_EXECUTED
RESTORE_VERIFIED
RESTORE_REHEARSAL_PROVEN
```

Эти состояния не взаимозаменяемы.

```text
BACKUP_EXISTS != RESTORE_IS_PROVEN
RESTORE_REHEARSAL_REQUIRED=YES
RESTORE_PROOF_MUST_BIND_BACKUP_IDENTITY=YES
```

`BACKUP_EXISTS` означает только наличие заявленного backup artifact.
`BACKUP_INTEGRITY_VERIFIED` связывает artifact с digest/identity.
`RESTORE_EXECUTED` подтверждает попытку materialization.
`RESTORE_VERIFIED` подтверждает корректность конкретного restored target.
`RESTORE_REHEARSAL_PROVEN` означает воспроизводимый end-to-end restore proof в
контролируемом rehearsal контуре.

## Backup contract

Для каждого backup class определяются:

```text
BACKUP_ID
BACKUP_SCOPE
SOURCE_IDENTITY
SOURCE_REVISION_OR_DATA_IDENTITY
CREATED_AT
INTEGRITY_METHOD
RPO_OBJECTIVE
RTO_OBJECTIVE
COPY_TOPOLOGY
OFF_NODE_REQUIRED_IF_APPLICABLE
OFF_SITE_REQUIRED_IF_APPLICABLE
IMMUTABILITY_REQUIRED_IF_APPLICABLE
RETENTION_POLICY_REF
RESTORE_TARGET_CLASS
VALIDATION_METHOD
```

Backup scope должен быть bounded: database/schema/partition/artifact set/range/config
bundle или другой воспроизводимый inventory.

## Source identity

Backup обязан связываться с исходным состоянием. Для runtime/config/data применяются
соответствующие identities; если recovery должен вернуть accepted deployment, target
связывается с:

```text
ROLLBACK_TARGET_IDENTITY=EXACT_PREVIOUS_ACCEPTED_DEPLOYMENT_REVISION
```

и применимым binding:

```text
SOURCE_COMMIT_TREE
+ ARTIFACT_DIGEST
+ BUILD_OR_TOOLCHAIN_IDENTITY
+ RUNTIME_CONFIG_DIGEST
+ MIGRATION_COMPATIBILITY_IDENTITY
```

Backup без достаточной source identity не может считаться доказанным recovery carrier.

## Integrity

Integrity proof должен обнаруживать повреждение/подмену применимым способом и связывать
проверку с `BACKUP_ID`. Размер > 0, наличие archive или successful upload недостаточны.

При encryption/signing ключевой material и процедура восстановления должны быть частью
recovery readiness, но конкретная cryptographic implementation выбирается отдельным
security owner route.

## RPO и RTO

- `RPO` задаёт допустимую потерю данных/состояния относительно recovery point.
- `RTO` задаёт целевое время восстановления service/data capability.

Значения определяются data/service class и owner policy. Стандарт не задаёт один
универсальный interval backup для всего AIFE.

## Copy topology и immutability

Off-node/off-site/immutable copies требуются там, где threat/failure model показывает,
что node-local или mutable copy не выдерживает ожидаемый failure domain.

Требование выражается capability/assurance class, а не обязательным vendor.

## Restore contract

Restore должен фиксировать:

```text
BACKUP_ID
RESTORE_TARGET_IDENTITY
RESTORE_ENVIRONMENT
RESTORE_STARTED_AT
RESTORE_COMPLETED_AT
INTEGRITY_VERDICT
SCHEMA_COMPATIBILITY_VERDICT
MIGRATION_COMPATIBILITY_VERDICT
GENERIC_VALIDATION_VERDICT
DOMAIN_VALIDATION_VERDICT_IF_APPLICABLE
INDEPENDENT_VALIDATION_EVIDENCE
```

Restore в production-like target разрешается только при соблюдении соответствующего
change/authorization contract; rehearsal не является production activation.

## Restore rehearsal

Каждый backup class, от которого зависит recovery, должен иметь периодическую или
event-triggered rehearsal policy. Rehearsal обязан доказать не только extraction, но и
полезную восстановимость требуемого inventory/capability.

Минимум:

```text
REHEARSAL=
SELECT_EXACT_BACKUP_ID
→ VERIFY_BACKUP_INTEGRITY
→ MATERIALIZE_ISOLATED_TARGET
→ VERIFY_SCHEMA_AND_MIGRATION_COMPATIBILITY
→ RUN_GENERIC_VALIDATION
→ RUN_DOMAIN_VALIDATION_IF_APPLICABLE
→ VERIFY_EXPECTED_INVENTORY
→ RECORD_RPO_RTO_EVIDENCE
→ FREEZE_RECEIPT
```

## Migration и retention relation

Backup/restore не заменяет migration completeness/parity proof. При backend migration
backup может быть rollback/recovery input, но cutover разрешает `STD-DATA-MIGRATION-001`.

Retention/purge должен учитывать required restore points. `RESTORABILITY_CAN_BLOCK_PURGE`
согласно `STD-DATA-RETENTION-001`.

## Publication relation

Restored bytes не становятся автоматически canonical published state. После restore
применяются требуемые validation/publication gates. ACK не восстанавливается только по
наличию backup metadata.

## Control/object recovery domains

Transactional control state и immutable object/blob corpus являются разными recovery
authority domains и квалифицируются отдельно, даже если deployment объединяет их на одном
initial server. Репликация и HA не являются backup proof.

```text
REPLICATION_EQUALS_BACKUP=NO
HA_EQUALS_BACKUP=NO
CONTROL_AND_OBJECT_RECOVERY_DOMAINS_SEPARATE=YES
```

Для Server/Data Foundation обязательное restore evidence включает clean-environment
materialization, reconciliation между control registration/manifests и restored object
inventory, затем independent readback. Наличие backup или replica без этого доказательства
не закрывает recoverability.

Точные numeric RPO/RTO и HA topology остаются owner/measurement bound.

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
BACKUP_PROVIDER_SELECTED=NO
STANDARD_DOES_NOT_SELECT_PRODUCT_VENDOR=YES
STANDARD_DOES_NOT_OVERRIDE_ACTIVE_ADR=YES
SERVER_DATA_ARCHITECTURE_OWNER=ADR-DATA-FOUNDATION-001
PRODUCT_SELECTION_REMAINS_F5_QUALIFICATION_BOUND=YES
```

Конкретные adapters/products выбираются и квалифицируются только в последующем
owner-authorized F5 contour в рамках active ADR. Measurement-bound параметры и deferred
products не превращаются этим стандартом в mandatory dependencies.

## Ненормативные implementation examples

Filesystem snapshots, database-native backups, object-store copies, logical dumps,
block-level snapshots и content-addressed archives допустимы как implementation profiles.
Cron, S3, SQLite, MongoDB или конкретные filesystem paths не являются обязательными
универсальными механизмами.

## Changelog

- **2026-08-27:** currentized Server/Data architecture ownership to
  `ADR-DATA-FOUNDATION-001`; historical F3 selection gates are no longer current authority.
- **2026-08-27:** добавлены F5R recovery rules: replication/HA != backup, separate
  control/object domains и clean restore + reconciliation + independent readback.
- **2026-08-26:** backup/restore сделан vendor-independent; разделены exists/integrity/
  restore/rehearsal states, введены backup identity binding, RPO/RTO и independent restore
  proof.
- **2025-10-19:** первоначальный draft.
