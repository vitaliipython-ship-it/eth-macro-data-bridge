---
id: CONTRACT-SERVER-STORAGE-001
domain: SERVER
title: "CONTRACT-SERVER-STORAGE-001: Generic Storage Lifecycle Port Contract"
version: "0.3.0"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2027-02-23
category: standards
doc_type: contract
language: ru
tags: [contract, server, storage, durable, readback, migration, backup, restore]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md

---

# CONTRACT-SERVER-STORAGE-001: Generic Storage Lifecycle Port Contract

## 1. Purpose

Определить backend-neutral storage lifecycle ports, необходимые work/publication/access mechanisms, без выбора универсального database/object-store vendor и без переноса domain semantic authority в physical storage.

## 2. Scope

Обязательные capability boundaries:

`INGEST_DURABLE_WRITE`, `DURABLE_OBJECT_WRITE`, `READBACK`, `LIST/INVENTORY`, `IDENTITY_LOOKUP`, `MIGRATION_SOURCE`, `MIGRATION_TARGET`, `RETENTION_STATE`, `BACKUP_REFERENCE`, `RESTORE_REFERENCE`.

Вне scope: PostgreSQL/SQLite/MongoDB/Redis/S3/Parquet как normative universal backend, конкретная schema/SDK и domain meaning stored bytes.

```text
DATABASE_VENDOR_SELECTED=NO
OBJECT_STORE_VENDOR_SELECTED=NO
PHYSICAL_STORAGE_IS_DOMAIN_SEMANTIC_AUTHORITY=NO
```

## 3. Core Rules

Ports описывают capability + identity + evidence, а не implementation technology.

```text
WRITE_REQUEST + OBJECT_IDENTITY
→ DURABLE_WRITE_EVIDENCE
→ READBACK_BY_INDEPENDENT_READ_CAPABILITY
→ IDENTITY/CONTENT_VERIFICATION
```

`LIST/INVENTORY` и `IDENTITY_LOOKUP` не являются заменой semantic access query. Migration source/target обязаны сохранять source identity/provenance и поддерживать independent verification. `BACKUP_REFERENCE` без successful restore proof не означает recoverability.

## 4. Authority Model

- Storage владеет physical durability/capability/evidence.
- Publication владеет publication state и ACK eligibility.
- Domain владеет semantic identity/finality/validation.
- Retention state выражает generic lifecycle role; policy owner решает domain/legal retention meaning.
- Backup/restore evidence не меняет canonical domain truth.

## 5. Naming Contract

Stored object, inventory item, backup and restore references должны быть stable, opaque to backend where possible и включать/ссылаться на source revision/provenance sufficient for reconciliation.

## 6. Placement Contract

```text
genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
```

Future source projection: `server/storage/**` поверх/совместно с существующим `core/data/**` substrate, без второго параллельного repository framework.

## 7. Agent Rules

1. Определять adapters только после backend-selection gate.
2. Не выдавать table/bucket/path как semantic API consumer contract.
3. Поддерживать independent read-back отдельно от writer result.
4. Migration не завершать без identity/completeness/reconciliation evidence.
5. Backup считать proven только после restore/read-back proof, соответствующего owner policy.

## 8. Acceptance Criteria

- все десять capability boundaries имеют typed/explicit implementation mapping;
- backend может быть заменён без изменения contract-level semantic API;
- read-back и identity lookup поддерживают publication proof;
- migration/backup/restore имеют provenance;
- никакой vendor не закреплён как universal normative backend.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| Backend-neutral ports | Architecture review | adapter/port review | Architecture Lead | backend change |
| Independent read-back | Integration test | write/read separation | Server/Data owner | qualification |
| Migration identity preservation | Migration test | source-target reconciliation | Server/Data owner | each migration |
| Restore proof | Recovery test | backup→restore→readback | Operations/Data owner | qualification |

## 10. Failure and restart semantics

- write result lost after durable success: reconcile by stable identity/readback before retry;
- inventory partial failure: surface partial/error state, never silently declare completeness;
- migration interruption: resume from durable migration checkpoint/reference without deleting source;
- backup interruption: incomplete backup is not recoverable authority;
- restore interruption: canonical route remains unchanged until restore/read-back qualification succeeds.

```text
RESTART_SEMANTICS_DEFINED=YES
FAILURE_SEMANTICS_DEFINED=YES
```

## 11. F5R physical identity binding

Storage boundary для F5/F5M обязан экспонировать backend-neutral identity/evidence,
достаточные для publication, migration, restore и exact readback. Минимальный binding:

```text
OPAQUE_STORAGE_REFERENCE
CONTENT_OR_OBJECT_IDENTITY
CHECKSUM_OR_EQUIVALENT_INTEGRITY
SIZE
FORMAT
COMPRESSION_CLASS_IF_APPLICABLE
ENCRYPTION_CLASS_IF_ALREADY_REQUIRED_BY_SECURITY_OWNER
DATASET_IDENTITY
PARTITION_IDENTITY_IF_APPLICABLE
SCHEMA_OR_LAYOUT_GENERATION
MANIFEST_IDENTITY
MANIFEST_PARENT_IF_APPLICABLE
CURRENT_GENERATION_REFERENCE
DURABLE_WRITE_EVIDENCE
SEAL_EVIDENCE
INDEPENDENT_READBACK_EVIDENCE
BACKUP_REFERENCE_IF_APPLICABLE
RESTORE_QUALIFICATION_REFERENCE_IF_APPLICABLE
```

Bulk storage capability is `SHARED_DURABLE_IMMUTABLE_OBJECT_OR_BLOB`; exact product remains
unselected. `Parquet` is required for bulk tabular classes while native immutable blobs are
allowed for source-fidelity cases. These fields do not expose table/bucket/path as consumer
semantic authority.

## 12. Bounded batching and content-collision evidence

Bulk physical objects are bounded batches, not one event or observation per object by
default. Exact sizing remains an implementation/measurement concern rather than a semantic
constant of this contract.

```text
BULK_PHYSICAL_OBJECT_MODEL=BOUNDED_BATCHED_OBJECTS
ONE_EVENT_PER_OBJECT_AS_DEFAULT=FORBIDDEN
BATCH_SIZE=NOT_HARDCODED
TARGET_FILE_SIZE=MEASUREMENT_BOUND
ROW_GROUP_SIZE=MEASUREMENT_BOUND
PARTITION_GRANULARITY=MEASUREMENT_BOUND
```

Storage must expose content/object identity and collision evidence sufficient for the
publication owner to distinguish an idempotent retry from a content conflict at the same
logical target. Storage does not decide the canonical conflict outcome.

```text
SAME_LOGICAL_TARGET_COLLISION_EVIDENCE=CONTENT_IDENTITY_REQUIRED
STORAGE_DECIDES_CANONICAL_CONFLICT_OUTCOME=NO
```
