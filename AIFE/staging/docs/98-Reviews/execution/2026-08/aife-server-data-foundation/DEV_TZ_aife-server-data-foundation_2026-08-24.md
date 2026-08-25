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

## 1. Назначение и жёсткая граница

Этот DEV_TZ — durable SSOT для будущей декомпозиции без контекста чата. Он не разрешает
server/runtime/storage implementation.

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

Архитектурные инварианты: один canonical AIFE server root; не один monolith/container/database;
horizontal scaling mandatory by design; initial one server allowed; `AppContext` public route
preserved; no second DI/data route; domain owns semantics.

## 2. Целевое владение

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS
ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
```

Consumers не получают direct DB/object/path credentials и не выбирают node/container/backend.

## 3. Устойчивость и публикация

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

Минимальная будущая цепочка: `SOURCE → ACQUIRE → DOMAIN_NORMALIZE → DOMAIN_VALIDATE →
INGEST_DURABLE → STAGE_OR_SPOOL → LOGICAL_PUBLICATION_UNIT → PUBLICATION_BOUNDARY →
STORAGE_ADAPTER → DURABLE_BACKEND → INDEPENDENT_READBACK → CANONICAL_REGISTRATION →
CANONICAL_ACK → SEMANTIC_ACCESS`.

Node-local recoverable state не является unique canonical truth. Accepted work получает
stable identity и durable checkpoint/staging до потери worker. Publication ACK только после
independent readback/registration по будущему contract.

## 4. Целевое состояние физического корпуса данных

Migration target относится к physical payload/history, а не к domain authority. Future fresh
inventory может охватывать `data/**`, `history/**`, `archive/**`, derivatives/options/liquidity
historical payloads, Git-bounded WARM и GitHub Release/deep-history objects.

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

`COPY_FILES → DELETE_SOURCE` запрещён как модель. Future migration unit/proof сохраняет или
доказывает domain/series/observation identity, time range, membership, content hash,
schema/version, `effective_at`, `known_at`, provenance, finality/revision semantics и canonical
readability.

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

Сначала forward collection, затем backfill.

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

F5M exit: `MIGRATION_INVENTORY_FROZEN`, `SOURCE_IDENTITIES_VERIFIED`,
`TARGET_IDENTITIES_VERIFIED`, `CONTENT_INTEGRITY_PASS`, `TIME_RANGE_COMPLETENESS_PASS`,
`SEMANTIC_READ_PARITY_PASS`, `PROVENANCE_PRESERVED`, `INDEPENDENT_READBACK_PASS`,
`LEGACY_READABILITY_PRESERVED`, `CUTOVER_OWNER_GATE_PASS`.

## 6. Полномочия планировщика и политики наступления срока

AIFE mechanism owns clock/due evaluation, stable work ID, durable work state,
ownership/lease-equivalent, checkpoint, retry/recovery, terminal state, missed-slot policy hook,
backpressure and worker count `1..N`. Domain owns capability, cadence, due slot, backfill,
finality, provider/source, gap meaning and freshness window. Values `1m/5m/15m/1h/8h/daily`
are domain policy, not platform ontology.

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

Не использовать `worker → sleep(...) → collect` или uncoordinated cron per node как authority.
`SAME_LOGICAL_SLOT_DUPLICATE_EXECUTION=PREVENT_OR_IDEMPOTENTLY_COLLAPSE`.

## 8. Роль внешней автоматизации n8n

`n8n` разрешён для notifications, Telegram, email, Slack, CRM, report distribution, analyst
workflows и external business automation. Он не владеет market-data due policy, canonical AIFE
work state, server liveness или periodic collection. External/manual trigger — optional input.

## 9. Рестарт, пропущенные слоты и масштабирование

После restart runtime должен различать completed, in-progress/retry, missed, backfill-eligible и
expired-by-domain-policy slots. `SERVER_RESTART_DOES_NOT_ERASE_SCHEDULE_SEMANTICS=YES`.
`TaskManager.run_periodic_task` на pinned AIFE snapshot — compatibility helper, не active scheduler
contract; перед реализацией он подлежит reconciliation, чтобы не создать second route.

## 10. Будущие Artifact Contracts

`CONTRACT-SERVER-WORK-001` planned fields: stable work identity, domain, capability, work type,
subject/partition, due slot/schedule identity, attempt, ownership/lease-equivalent, checkpoint,
retry/recovery, terminal state, policy reference, correlation/trace identity.

`CONTRACT-DATA-PUBLICATION-001`: logical publication identity, durable write, storage adapter,
independent readback, registration, ACK, idempotency, terminal state.

`CONTRACT-DATA-ACCESS-001`: semantic request, domain/capability/range/cutoff/policy,
resolution/access plan, canonical read/materialization, provenance, diagnostics, fail-closed.

```text
SCHEDULING_BOUNDARY_MERGED_WITH_SERVER_WORK_CONTRACT=YES_CANDIDATE
SEPARATE_SCHEDULER_ARTIFACT_CONTRACT=NOT_REQUIRED_YET
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED=NO
CONTRACT_SERVER_WORK_FILE_CREATED=NO
```

## 11. Выравнивание стандартов данных

Pinned registry фиксирует все шесть как `0.1.0 / draft`:

```text
STD-DATA-MGMT-001
STD-DATA-SCHEMA-001
STD-DATA-MIGRATION-001
STD-DATA-VALIDATION-001
STD-DATA-RETENTION-001
STD-DATA-BACKUP-001
```

Они не являются автоматически готовой production binding authority. До F2 требуется owner
alignment/disposition `AS_IS|AMEND_REQUIRED|SPLIT_REQUIRED|MERGE_REQUIRED|DEFER`.

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

- `STD-DATA-MGMT-001`: проверить `DOMAIN_SEMANTICS != PHYSICAL_STORAGE`,
  `INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY`, node-local != canonical truth и классы
  `VOLATILE_PROCESS_STATE`, `NODE_LOCAL_RECOVERABLE_STATE`, `INGEST_DURABLE_STATE`,
  `CANONICAL_PUBLISHED_STATE`, `ARCHIVAL_STATE`.
- `STD-DATA-SCHEMA-001`: schema identity/version/compatibility/evolution/constraints/indexing,
  domain ownership и physical representation boundary; SQLite/MongoDB/PostgreSQL examples не
  должны означать universal vendor. `DATA_SCHEMA_STANDARD_MUST_NOT_IMPLY_UNIVERSAL_DATABASE_VENDOR=YES`.
- `STD-DATA-MIGRATION-001`: различать `SCHEMA_MIGRATION`, `DATA_MIGRATION`,
  `PHYSICAL_BACKEND_MIGRATION`, `HISTORICAL_BACKFILL`, `AUTHORITY_OR_CUTOVER_MIGRATION`;
  F5M — proving use case; требуются inventory, identity, integrity, completeness, provenance,
  readback, read parity, rollbackability, cutover gate, legacy readability.
- `STD-DATA-VALIDATION-001`: generic AIFE vs domain validation; identity/schema/content,
  publication/readback/provenance/migration completeness; ETH-specific validation domain-owned.
- `STD-DATA-RETENTION-001`: HOT/WARM/COLD/ARCHIVAL/RETIREMENT/PURGE — logical roles, не vendor;
  retention учитывает authority, restoreability, migration, provenance, retirement gate.
  `RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES`.
- `STD-DATA-BACKUP-001`: backup scope/authority class, integrity, RPO/RTO where applicable,
  independent restore, verification/rehearsal, lineage/provenance, immutable/offsite where justified.
  `BACKUP_EXISTS != RESTORE_IS_PROVEN`.

## 13. Соответствие стандартам API

Pinned API suite `STD-API-DESIGN-001`, `STD-API-DOCS-001`, `STD-API-ERRORS-001`,
`STD-API-RATE-001`, `STD-API-VERSIONING-001` — `1.0.0 / approved`.

```text
API_STANDARDS_COMPLIANCE_REQUIRED=YES
API_STANDARDS_DEFAULT_ACTION=CONFORM
API_STANDARDS_IMPLEMENTATION_MAY_IGNORE=NO
API_STANDARD_AMENDMENT_ALLOWED=ONLY_IF_PROVEN_GAP_AND_OWNER_APPROVED
SEMANTIC_CONTRACT_FIRST=YES
TRANSPORT_SELECTION_AFTER_SEMANTIC_BOUNDARY=YES
API_COMPLIANCE_AFTER_TRANSPORT_APPLICABILITY_IS_KNOWN=YES
```

If HTTP/REST chosen, future matrix covers URI/method semantics, documentation, error envelope,
client/rate semantics and versioning. If gRPC/WebSocket/other transport exposes an applicability
gap, do not fake compliance: classify the gap and obtain owner decision first.

## 14. Соответствие требованиям безопасности

Pinned approved contour includes `STD-SEC-AUTH-001`, `STD-SEC-ENCRYPTION-001`,
`STD-SEC-LOG-001`, `STD-SEC-PRINCIPLES-001`, `STD-SEC-REVIEW-001`,
`STD-SEC-SECRETS-001`, `STD-SEC-VULN-001`.

```text
SERVER_SECURITY_COMPLIANCE_REQUIRED=YES
SECURITY_COMPLIANCE_BEFORE_PRODUCTION_CAPABLE_PUBLIC_INTERFACE=YES
SECURITY_COMPLIANCE_EXECUTED=NO
```

Future implementation must not introduce hardcoded credentials, storage/database credentials in
Workspace/UI, auth bypass, secret material in logs/evidence or transport auth outside approved route.

## 15. Соответствие требованиям журналирования

`STD-LOG-001=2.3.0 / approved`.

```text
SERVER_LOGGING_COMPLIANCE_REQUIRED=YES
STD_LOG_001_COMPLIANCE_REQUIRED=YES
LOGGING_COMPLIANCE_EXECUTED=NO
```

Do not create second server logging standard by default. `STD-MON-HEALTH-001` and
`STD-MON-METRICS-001` remain `0.1.0 / draft`; monitoring alignment is required before
production observability but is a separate future review.

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

`F3_PUBLIC_INTERFACE_ENTRY_REQUIRES_COMPLIANCE_DISPOSITION=YES`.

## 17. Обработка разрыва между стандартом и реальным вариантом использования

```text
USE_CASE
→ CONTRACT_REQUIREMENT
→ STANDARD_COMPLIANCE_CHECK
→ GAP_CLASSIFICATION
```

Allowed: `IMPLEMENTATION_DEFECT`, `CONTRACT_DEFECT`, `STANDARD_GAP`,
`STANDARD_NOT_APPLICABLE`, `OWNER_DECISION_REQUIRED`. Только owner-reviewed `STANDARD_GAP`
может привести к amendment/new standard.

## 18. Правило создания новых стандартов

```text
NEW_STANDARD_DEFAULT_DECISION=DO_NOT_ADD
NEW_SERVER_STANDARD_CREATED=NO
```

Новый `STD-SERVER-*` допустим только при повторном использовании, межкомпонентной/междоменной
применимости, невозможности корректно расширить существующий standard и явном owner approval.
`STD-SERVER-SCHEDULER-001`, `STD-SERVER-STORAGE-001`, `STD-SERVER-WORKER-001`,
`STD-SERVER-MIGRATION-001` сейчас не создаются.

## 19. Future task identities и входные условия

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

## 20. Stop boundary

Эта задача не меняет Data/API/Security/Logging/Monitoring standards, не создаёт SERVER domain,
Artifact Contracts, transport, database, Object Storage/Parquet, server/scheduler/n8n code,
не мигрирует corpus, не меняет production cadence/route, не реализует P2 и не возобновляет R2.

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```
