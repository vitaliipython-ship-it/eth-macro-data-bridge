---
id: CONTRACT-SERVER-STORAGE-001
domain: SERVER
title: "CONTRACT-SERVER-STORAGE-001: Generic Storage Lifecycle Port Contract"
version: "0.1.0"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
review_cycle_days: 180
next_review_due: 2027-02-22
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
