---
id: AIFE-SERVER-DATA-FOUNDATION-F5-IMPLEMENTATION-DEV-TZ-2026-08-29
title: "DEV_TZ: F5 new incoming physical lifecycle qualification"
version: '1.0'
status: draft
owner: Architecture Lead
created: 2026-08-29
updated: 2026-08-29
category: architecture
doc_type: spec
language: ru
tags: [dev-tz, f5, server, data, sqlite, publication, storage, access, recovery]
authority_reference:
  - AGENTS.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PRR_f5-pre-dev-tz-minimum-implementation-profile_2026-08-28.md
  - genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
  - genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
  - genome/contracts/server/CONTRACT-SERVER-DEPLOYMENT-001.md
---

# DEV_TZ: F5 new incoming physical lifecycle qualification

## Physical Use Contract

```text
physical-use class: control-plane-evidence-only
CURRENT_DELIVERY_CLAIM=DEV_TZ_AND_OWNER_REVIEW_ONLY_NO_RUNTIME_INSTALLATION
F5_SOURCE_IMPLEMENTATION=NO
RUNTIME_IMPLEMENTATION=NO
DATABASE_CREATION=NO
REAL_STORAGE_WRITE=NO
READINESS_EXECUTION=NO
QUALIFICATION_EXECUTION=NO
PRODUCTION_ACTIVATION=NO
AEB_CREATION=NO
OWNER_EXECUTION_AUTHORITY_GRANTED=NO
```

This artifact defines the future implementation contract only. Any runtime, persistence,
filesystem or qualification behavior described below is a requirement for the separately
authorized implementation task, not evidence that it has already happened.

## 1. Authority, task identity and hard stop

Этот документ является отдельным implementation contract для F5. Он материализует
архитектурные решения, но сам не разрешает source/runtime implementation.

```text
TASK_ID=C-144
CANONICAL_C_TASK_ID=C-144
DEV_TZ_PATH=docs/98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_f5_2026-08-29.md
PRIMARY_PRR_PATH=docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PRR_aife-server-data-foundation_f5_2026-08-29.md
F5_STAGE_ID=F5
F5_STAGE_SEMANTIC_ID=NEW_INCOMING_PHYSICAL_LIFECYCLE_QUALIFICATION
F5_CANONICAL_WAVE_SLUG=f5
F5_CANONICAL_TZ_SLUG=f5
F5_INITIAL_PROFILE=ONE_SERVER
F5_SCOPE=ONE_BOUNDED_NEW_INCOMING_ETH_VERTICAL_SLICE
F5_FORWARD_DATA_ONLY=YES
F5M_BACKFILL=OUT_OF_SCOPE
F5M_SCOPE=OUT_OF_SCOPE
EXISTING_CORPUS_MIGRATION=OUT_OF_SCOPE
MULTI_NODE_IMPLEMENTATION=OUT_OF_SCOPE
HORIZONTAL_DESIGN_COMPATIBILITY=REQUIRED
PRODUCTION_CUTOVER_SCOPE=OUT_OF_SCOPE
PRODUCTION_ACTIVATION_SCOPE=OUT_OF_SCOPE
CONTROL_BACKEND_INITIAL=SQLITE_WAL
OBJECT_STORE_VENDOR_SELECTED=NO
OWNER_EXECUTION_AUTHORITY_GRANTED=NO
F5_IMPLEMENTATION_STARTED=NO
CURRENT_F5_RUNTIME_READINESS_STATUS=NOT_EVALUATED_PRE_IMPLEMENTATION
CURRENT_F5_QUALIFICATION_STATUS=NOT_RUN
AEB_GENERATION=NO
REAL_AIFE_MUTATION=NO
```

`C-144` — первый свободный canonical C-ID после `C-143` в pinned Program Control.
Он считается consumed созданием этого DEV_TZ, но выполнение `C-144` начинается только
после отдельного owner execution authorization.

Canonical Program Control materialization is part of the same governance candidate:

```text
C144_BACKLOG_REGISTRATION_REQUIRED=YES
C144_BACKLOG_STATUS=Backlog
C144_IMPLEMENTATION_STARTED=NO
C144_OWNER_EXECUTION_AUTHORITY_GRANTED=NO
```

## 2. Authority boundary

```text
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+REVISION_GAP_RULES+DOMAIN_RESOLUTION_RULES
AIFE_OWNS=GENERIC_WORK_EXECUTION+SCHEDULING+EXECUTION_OWNERSHIP+DURABLE_RUNTIME_STATE+PUBLICATION_LIFECYCLE+PHYSICAL_STORAGE_LIFECYCLE+ACCESS_MECHANISMS+SERVER_OPERATIONS
PHYSICAL_STORAGE_BACKEND_IS_SEMANTIC_AUTHORITY=false
EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false
PHYSICAL_LOCATOR_IS_DOMAIN_IDENTITY=NO
```

F5 начинает только от уже принятого доменом `F4 DomainArtifactEnvelope`. AIFE не
нормализует его заново, не меняет finality и не выводит domain identity из filesystem path,
object key, SQLite row id или времени исполнения.

## 3. Owner layering

```text
CONTROL_STATE_APPLICATION_OWNER=server/application/**
CONTROL_STATE_PERSISTENCE_ABSTRACTION_OWNER=core/data/**
CONTROL_STATE_PERSISTENCE_ADAPTER_OWNER=core/data/adapters/**
CONTROL_STATE_SCHEMA_MIGRATION_OWNER=core/data/**
CONTROL_STATE_REUSES_CORE_DATA_SUBSTRATE=YES
SECOND_REPOSITORY_UOW_FRAMEWORK=FORBIDDEN
SECOND_PERSISTENCE_ABSTRACTION=FORBIDDEN
SECOND_GENERIC_PERSISTENCE_FRAMEWORK=FORBIDDEN
SERVER_CONTROL_PACKAGE_BY_DEFAULT=FORBIDDEN
```

`server/application/**` оркестрирует use-case. `core/data/**` предоставляет единственную
persistence/UoW seam. `server/work|execution|publication/**` владеют meaning состояний,
а SQLite adapter только сохраняет и атомарно сравнивает эти состояния.

## 4. Selected bounded F5 slice and Parquet decision

Selected slice: один уже domain-validated immutable `DomainArtifactEnvelope`, чей
`payload_reference` указывает на opaque source-fidelity bytes. F5 квалифицирует полный
physical lifecycle этих bytes без AIFE-side semantic row transformation.

```text
F5_SLICE_KIND=DOMAIN_VALIDATED_OPAQUE_IMMUTABLE_ARTIFACT
F5_SLICE_CARDINALITY=ONE_LOGICAL_ARTIFACT_PER_WORK
F5_SLICE_REQUIRES_AIFE_TABULAR_TRANSFORM=NO
PARQUET_WRITER_REQUIRED_FOR_F5=NO
PARQUET_WRITER_TRIGGER=ONLY_WHEN_OWNER_SELECTED_DOMAIN_ARTIFACT_CLASS_IS_EXPLICITLY_BULK_TABULAR_AND_DOMAIN_OWNED_SCHEMA_MAPPING_IS_AVAILABLE
PARQUET_DEPENDENCY_ADDED_BY_F5=NO
```

Причина: превращать opaque ETH payload в строки без domain-owned schema mapping означало бы
перенести semantic decision в AIFE. Требование `PARQUET_REQUIRED_FOR_BULK_TABULAR` сохраняется,
но текущий bounded source-fidelity slice не является таким преобразованием.

## 5. End-to-end lifecycle contract

```text
F4_DOMAIN_ARTIFACT_ENVELOPE
→ DETERMINISTIC_WORK_IDENTITY
→ DURABLE_WORK
→ DURABLE_ATTEMPT
→ DETERMINISTIC_SCHEDULING_SLOT_IF_APPLICABLE
→ ATOMIC_CLAIM
→ LEASE
→ MONOTONIC_FENCING_TOKEN
→ BOUNDED_EXECUTION
→ STABLE_PUBLICATION_IDENTITY
→ DURABLE_PHYSICAL_WRITE
→ INDEPENDENT_READBACK
→ CANONICAL_REGISTRATION
→ CURRENT_GENERATION_UPDATE_IF_APPLICABLE
→ ACK
→ EXACT_ACCESS_READBACK
→ RESTART_RETRY_RECOVERY_PROOF
```

Для каждой границы применяются одинаковые поля:

| Boundary | Owner | Input | Output | Persisted state | Transaction boundary | Idempotency | Failure/retry/recovery | Test evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Envelope→Work | `server/integration` + `server/application` | accepted envelope + policy/slot | stable Work identity | `work` | T1 | duplicate identity collapses | mismatch fails closed | work + boundary tests |
| Work→Attempt | `server/application` + `core/data` | READY Work | Attempt/claim | `attempt`, `work` | T2 | attempt sequence per Work | atomic loser has no authority | SQLite concurrency |
| Lease/Fence | `server/execution` + `core/data` | current Attempt | current authority | `attempt` | T2/T3 | fence monotonic | expiry→new attempt/fence | F07/F08/F25 |
| Execution→Publication | `server/application` + `server/publication` | current fence + envelope | Publication | `publication` | T4 | stable Publication ID | stale fence rejected | lifecycle tests |
| Physical write | `server/storage` | Publication + payload ref | write evidence + locator | publication evidence | external write then T5 evidence record | content-addressed object | reconcile by checksum | write/readback tests |
| Readback | `server/storage` | locator + checksum | independent evidence | publication evidence | T5 | repeatable read | mismatch blocks registration | F02/F22 |
| Registration | `server/publication` + `core/data` | readback + current fence | generation registration | `publication_generation`, pointer | T6 | same target/content collapse | conflict/no overwrite | F03/F05/F06/F19 |
| ACK | `server/publication` + `core/data` | full predecessor evidence | ACKED | `publication` | T7 | repeat ACK collapses | illegal ACK rejected | F04/F26 |
| Access | `server/access` | exact request identity | exact bytes/evidence | no new authority | read transaction | exact same request same target | missing/mismatch fail closed | F20 |
| Recovery | `server/runtime` + `core/data` | backup + registered objects | reconciled state | restore evidence | isolated restore | exact backup identity | authority remains closed until proof | F21/F22 |

## 6. Exact Work identity and model

Canonical deterministic encoding is UTF-8 canonical JSON with sorted keys and separators
`(',', ':')`; absent scheduling slot is literal `"DIRECT"`. Hash is lowercase SHA-256 hex.

```text
WORK_KIND=F5_INCOMING_ARTIFACT_PUBLICATION
WORK_ID_INPUTS=F5_STAGE_ID+WORK_KIND+DOMAIN_ARTIFACT_IDENTITY+SOURCE_REVISION+CONTENT_IDENTITY+SCHEDULING_SLOT_IDENTITY_OR_DIRECT+POLICY_REVISION_IDENTITY
WORK_ID=work:f5:v1:<sha256(canonical-json(WORK_ID_INPUTS))>
LOGICAL_INPUT_IDENTITY=<same canonical tuple without node/process/worker identity>
IDEMPOTENCY_CONSTRAINT=UNIQUE(LOGICAL_INPUT_IDENTITY)
SAME_LOGICAL_INPUT=>SAME_LOGICAL_WORK
NODE_ID_IN_WORK_ID=NO
PROCESS_ID_IN_WORK_ID=NO
WORKER_ID_IN_WORK_ID=NO
```

Exact minimum fields:

```text
WORK_ID
WORK_KIND
LOGICAL_INPUT_IDENTITY
SCHEDULING_SLOT_IDENTITY_WHERE_APPLICABLE
PAYLOAD_REFERENCE
PROVENANCE_REFERENCE
POLICY_REVISION_IDENTITY
CREATED_AT
STATE
ATTEMPT_RELATION
TERMINAL_STATE
FAILURE_STATE
IDEMPOTENCY_CONSTRAINT
```

Immutable after durable acceptance: Work ID inputs, logical input identity, payload reference,
provenance reference, policy revision and scheduling slot. Duplicate insert with exact same
immutable tuple returns existing Work. Same `LOGICAL_INPUT_IDENTITY` with different immutable
bytes/refs is a conflict and fails closed. Retry creates a new Attempt, not a new Work.

Work states remain contract-compatible:

```text
PENDING→READY→CLAIMED→RUNNING→SUCCEEDED|FAILED|CANCELLED
```

Terminal Work cannot return to non-terminal state. A failed **Attempt** is not automatically a
failed **Work**. For the bounded F5 profile the retry policy is exact:

```text
MAX_AUTOMATIC_ATTEMPTS_PER_WORK=3
RETRYABLE_ATTEMPT_FAILURE=ATTEMPT_TERMINATES_FAILED_OR_ABANDONED+WORK_RETURNS_TO_READY_WITH_SAME_WORK_ID
NON_RETRYABLE_IDENTITY_SCHEMA_COLLISION_OR_ILLEGAL_ACK_FAILURE=WORK_TERMINATES_FAILED
RETRY_BUDGET_EXHAUSTED=WORK_TERMINATES_FAILED
CANCELLED_WORK_IS_RETRYABLE=NO
RETRY_CREATES_NEW_ATTEMPT=YES
RETRY_CREATES_NEW_WORK=NO
```

Infrastructure crash/lease loss/I/O-unavailable classes are retryable when no fail-closed
identity/schema/collision condition exists. Recovery reads durable state; it never mints
replacement Work because a process restarted.

## 7. Attempt, claim, lease and fencing

```text
ATTEMPT_ID=attempt:f5:v1:<sha256(canonical-json(WORK_ID,ATTEMPT_NO))>
ATTEMPT_NO=MONOTONIC_INTEGER_PER_WORK_STARTING_AT_1
CLAIM_ID=claim:f5:v1:<ATTEMPT_ID>
CLAIM_OWNER=OPAQUE_RUNTIME_WORKER_INSTANCE_IDENTITY
LEASE_ACQUIRED_AT=UTC_AWARE_TIMESTAMP
LEASE_EXPIRES_AT=UTC_AWARE_TIMESTAMP
FENCING_TOKEN=MONOTONIC_INTEGER_PER_WORK_STARTING_AT_1
ATTEMPT_STATE=CLAIMED|RUNNING|SUCCEEDED|FAILED|ABANDONED
STARTED_AT=UTC_AWARE_TIMESTAMP_OR_NULL
TERMINATED_AT=UTC_AWARE_TIMESTAMP_OR_NULL
TERMINAL_REASON=BOUNDED_TEXT_OR_NULL
```

Atomic claim is T2 `BEGIN IMMEDIATE`: verify Work eligible; verify no unexpired current attempt;
allocate `ATTEMPT_NO=max+1` and `FENCING_TOKEN=max+1`; insert Attempt; update Work to CLAIMED;
commit. SQLite's single writer serialization is the bounded one-server arbitration mechanism.

```text
LEASE_DEFAULT_DURATION_SECONDS=60
LEASE_RENEWAL_TARGET_SECONDS_BEFORE_EXPIRY=20
LEASE_RENEWAL_REQUIRES_CURRENT_FENCE=YES
LEASE_RENEWAL_AFTER_EXPIRY=FORBIDDEN
RECLAIM_REQUIRES_EXPIRED_OR_EXPLICITLY_ABANDONED_ATTEMPT=YES
RECLAIM_CREATES_NEW_ATTEMPT=YES
RECLAIM_CREATES_STRICTLY_NEWER_FENCE=YES
OLDER_FENCE_CANNOT_MUTATE_STATE_AFTER_NEWER_FENCE=YES
CONCURRENT_CLAIM_RACE=ONE_CURRENT_CLAIMANT
PROCESS_LOCAL_MUTEX_IS_DURABLE_AUTHORITY=NO
```

Any terminal Work transition, publication registration/current-generation change or ACK must
compare Work+Attempt+current fencing token inside the same control transaction. Loss of renewal
makes the worker non-authoritative before any authority-bearing commit.

## 8. SQLite/WAL control state

```text
CONTROL_DB_PATH=/var/lib/aife/control/aife-control.sqlite3
SQLITE_CONNECTION_OWNER=ONE_CONNECTION_PER_CORE_DATA_UNIT_OF_WORK
SQLITE_CROSS_THREAD_SHARED_CONNECTION=FORBIDDEN
SQLITE_JOURNAL_MODE=WAL
SQLITE_SYNCHRONOUS=FULL
SQLITE_FOREIGN_KEYS=ON
SQLITE_BUSY_TIMEOUT_MS=5000
SQLITE_WRITE_TRANSACTION_MODE=BEGIN_IMMEDIATE
SQLITE_READER_CONCURRENCY=MULTIPLE_READERS_ALLOWED
SQLITE_WRITER_CONCURRENCY=ONE_SERIALIZED_WRITER
CONTROL_SCHEMA_ID=aife-server-control
CONTROL_SCHEMA_INITIAL_VERSION=1
SCHEMA_VERSION_AUTHORITY=schema_metadata+PRAGMA_user_version_cross_check
SILENT_SCHEMA_DOWNGRADE=FORBIDDEN
```

### 8.1 `schema_metadata`

```text
TABLE=schema_metadata
PRIMARY_KEY=schema_name
FIELDS=schema_name TEXT; schema_version INTEGER; compatibility_class TEXT; migration_id TEXT; applied_at TEXT
CHECK_CONSTRAINTS=schema_version>=1; compatibility_class IN('F5_V1')
UNIQUE_CONSTRAINTS=PRIMARY_KEY(schema_name)
INDEXES=PRIMARY_KEY_ONLY
VERSION_FIELDS=schema_version,migration_id
```

Exactly one authoritative row for `aife-server-control`; it must equal `PRAGMA user_version`.
Mismatch is corruption/incompatibility and fails closed.

### 8.2 `work`

```text
TABLE=work
PRIMARY_KEY=work_id
FOREIGN_KEYS=NONE
UNIQUE_CONSTRAINTS=UNIQUE(logical_input_identity)
CHECK_CONSTRAINTS=state IN(PENDING,READY,CLAIMED,RUNNING,SUCCEEDED,FAILED,CANCELLED)
INDEXES=idx_work_state_created_at(state,created_at)
STATE_FIELDS=state,terminal_state,failure_state
TIMESTAMP_FIELDS=created_at,updated_at,terminal_at
VERSION_FIELDS=record_version
```

Required columns additionally include `work_kind`, `scheduling_slot_identity`,
`payload_reference`, `provenance_reference`, `policy_revision_identity`, and immutable input
digest. `record_version` is incremented on accepted state mutation and may be used for
optimistic diagnostic comparison; fencing remains execution authority.

### 8.3 `attempt`

```text
TABLE=attempt
PRIMARY_KEY=attempt_id
FOREIGN_KEYS=work_id→work.work_id ON DELETE RESTRICT
UNIQUE_CONSTRAINTS=UNIQUE(work_id,attempt_no); UNIQUE(work_id,fencing_token)
CHECK_CONSTRAINTS=attempt_no>=1; fencing_token>=1; state IN(CLAIMED,RUNNING,SUCCEEDED,FAILED,ABANDONED); lease_expires_at>lease_acquired_at
INDEXES=idx_attempt_work_state(work_id,state); idx_attempt_lease_expiry(state,lease_expires_at)
STATE_FIELDS=state,terminal_reason
TIMESTAMP_FIELDS=lease_acquired_at,lease_expires_at,started_at,terminated_at
VERSION_FIELDS=fencing_token,attempt_no
```

`claim_owner`, `claim_id` and `lease_id` are persisted. There can be historical attempts, but
T2 guarantees one current non-expired authority.

### 8.4 `publication`

```text
TABLE=publication
PRIMARY_KEY=publication_id
FOREIGN_KEYS=work_id→work.work_id; attempt_id→attempt.attempt_id
UNIQUE_CONSTRAINTS=UNIQUE(logical_target_identity)
CHECK_CONSTRAINTS=state IN(INGEST_DURABLE,STAGED,PUBLISHING,DURABLE_STORED,INDEPENDENT_READBACK_VERIFIED,CANONICALLY_REGISTERED,ACKED,FAILED,CONFLICTED)
INDEXES=idx_publication_work(work_id); idx_publication_state(state); idx_publication_target(logical_target_identity)
STATE_FIELDS=state,failure_reason
TIMESTAMP_FIELDS=created_at,updated_at,acked_at
VERSION_FIELDS=registration_fencing_token
```

Immutable identity fields: domain artifact identity, source revision, content checksum,
logical target identity, Work ID. Physical locator is metadata and may only be set from durable
write evidence. Readback/registration/ACK evidence are separate columns/references.

### 8.5 `publication_generation`

```text
TABLE=publication_generation
PRIMARY_KEY=(generation_scope_identity,generation_identity)
FOREIGN_KEYS=publication_id→publication.publication_id ON DELETE RESTRICT
UNIQUE_CONSTRAINTS=UNIQUE(generation_scope_identity,generation_no); UNIQUE(publication_id)
CHECK_CONSTRAINTS=generation_no>=1
INDEXES=idx_generation_publication(publication_id)
STATE_FIELDS=NONE
TIMESTAMP_FIELDS=registered_at
VERSION_FIELDS=generation_no,registration_fencing_token
```

For the bounded slice `generation_scope_identity` is the opaque
`DomainArtifactIdentity.value`; `generation_identity` is
`gen:f5:v1:<sha256(artifact_identity,source_revision,content_identity)>`. It is physical
registration identity, not a replacement for domain revision/finality.

### 8.6 `publication_current_generation`

```text
TABLE=publication_current_generation
PRIMARY_KEY=generation_scope_identity
FOREIGN_KEYS=(generation_scope_identity,generation_identity)→publication_generation
UNIQUE_CONSTRAINTS=PRIMARY_KEY(generation_scope_identity)
CHECK_CONSTRAINTS=generation_no>=1
INDEXES=PRIMARY_KEY_ONLY
STATE_FIELDS=generation_identity,generation_no
TIMESTAMP_FIELDS=updated_at
VERSION_FIELDS=generation_no,registration_fencing_token
```

Pointer update is T6 and accepts only `new_generation_no >= current_generation_no`; equality is
allowed only for exact same generation/publication idempotent reconciliation. Lower or conflicting
equality fails closed.

## 9. Control transactions

```text
T1_WORK_ACCEPTANCE=BEGIN_IMMEDIATE→INSERT_OR_EXACT_RECONCILE_WORK→COMMIT
T2_ATOMIC_CLAIM=BEGIN_IMMEDIATE→CHECK_ELIGIBILITY_AND_LEASE→ALLOCATE_ATTEMPT_AND_FENCE→INSERT_ATTEMPT→UPDATE_WORK→COMMIT
T3_LEASE_RENEWAL=BEGIN_IMMEDIATE→COMPARE_CURRENT_FENCE_AND_EXPIRY→EXTEND_OR_REJECT→COMMIT
T4_TERMINAL_ATTEMPT=BEGIN_IMMEDIATE→COMPARE_CURRENT_FENCE→UPDATE_ATTEMPT_AND_WORK→COMMIT
T5_PUBLICATION_EVIDENCE=BEGIN_IMMEDIATE→COMPARE_CURRENT_FENCE→ADVANCE_ONE_VALID_PUBLICATION_STATE→COMMIT
T6_CANONICAL_REGISTRATION=BEGIN_IMMEDIATE→COMPARE_FENCE+READBACK_IDENTITY→INSERT_GENERATION→MONOTONIC_POINTER_UPDATE→SET_CANONICALLY_REGISTERED→COMMIT
T7_ACK=BEGIN_IMMEDIATE→REQUIRE_DURABLE+READBACK+REGISTRATION+IDENTITY_MATCH+CURRENT_FENCE→SET_ACKED→COMMIT
```

External filesystem write/readback is never held inside a long SQLite transaction. Durable
evidence is reconciled into T5 afterwards using stable identities.

## 10. Schema migration decision

Three-question test:

```text
MIGRATION_FRAMEWORK_OR_TOOLING=CONDITIONAL_NOW
PROVEN_RISK=REPEATABLE_SCHEMA_TRANSITION_AND_COMPATIBILITY
SIMPLER_SOLUTION=EXPLICIT_VERSIONED_STDLIB_SQLITE3_MIGRATION_FUNCTIONS
SIMPLER_SOLUTION_SUFFICIENT_FOR_F5=YES
DOWNSTREAM_BURDEN_REDUCED_BY_FRAMEWORK_NOW=NO
STDLIB_SQLITE3_ALLOWED=YES
SQLALCHEMY_REQUIRED=NO_UNLESS_PROVEN
ALEMBIC_REQUIRED=NO_UNLESS_PROVEN
F5_SCHEMA_MIGRATION_IMPLEMENTATION=BOUNDED_EXPLICIT_0_TO_1_INITIALIZATION_AND_LINEAR_N_TO_N_PLUS_1_FUNCTIONS
GENERIC_MIGRATION_FRAMEWORK_TRIGGER=TWO_OR_MORE_SIMULTANEOUSLY_SUPPORTED_NONTRIVIAL_UPGRADE_PATHS_OR_NONLINEAR_MIGRATION_GRAPH_PROVEN_BY_DEPLOYMENT_REQUIREMENT
```

Each migration verifies source version, runs in an explicit transaction, updates
`schema_metadata` and `PRAGMA user_version` together, then validates target identity. No down
migration is executed automatically. Incompatible older code blocks activation.

## 11. Scheduling

```text
SCHEDULER_AUTHORITY=CONTRACT-SERVER-SCHEDULING-001
SECOND_SCHEDULER=FORBIDDEN
CRON_OR_SYSTEMD_TIMER_IS_SEMANTIC_SCHEDULING_AUTHORITY=NO
DETERMINISTIC_SLOT_IDENTITY=slot:f5:v1:<sha256(canonical-json(schedule_definition_identity,nominal_due_at_utc,timezone_identity,policy_revision_identity))>
DUE_WORK_CREATION=T1_WORK_ACCEPTANCE_WITH_SLOT_IDENTITY
DUPLICATE_SLOT_COLLAPSE=EXACT_SLOT+EXACT_LOGICAL_INPUT→SAME_WORK_ID
MISFIRE_OR_RESTART=RECOMPUTE_CANDIDATE_SLOT_IDENTITIES_THEN_COLLAPSE_ALREADY_MATERIALIZED_WORK
F24_DUPLICATE_DETERMINISTIC_SLOT=>SAME_LOGICAL_WORK_ID
```

Domain/owner policy decides whether a missed candidate slot is still valid; scheduler does not
backfill ETH history on its own.

## 12. Publication state machine and identities

```text
PUBLICATION_ID=pub:f5:v1:<sha256(canonical-json(work_id,domain_artifact_identity,source_revision,content_identity))>
LOGICAL_TARGET_IDENTITY=target:f5:v1:<sha256(canonical-json(domain_artifact_identity,source_revision))>
PUBLICATION_STATE_MACHINE=INGEST_DURABLE→STAGED→PUBLISHING→DURABLE_STORED→INDEPENDENT_READBACK_VERIFIED→CANONICALLY_REGISTERED→ACKED
ACK_GATE=DURABLE_WRITE+INDEPENDENT_READBACK+CANONICAL_REGISTRATION+IDENTITY_MATCH+CURRENT_FENCING_AUTHORITY
ILLEGAL_ACK=FAIL_CLOSED
SAME_TARGET+SAME_BYTES=IDEMPOTENT_COLLAPSE
SAME_TARGET+DIFFERENT_BYTES=REJECT_COLLISION_NO_OVERWRITE_NO_ACK
```

ACK never follows a writer return directly. State transition must be monotonic; restart reads
persisted state and reconciles only the next legal transition.

## 13. Thin physical storage port

The existing `server/storage/ports.py` remains the contract surface and is narrowed/extended
only as needed to support:

```text
WRITE_IMMUTABLE_OBJECT
READ_EXACT_OBJECT
READBACK_VERIFY
EXISTS_OR_IDENTITY_CHECK
LIST_OR_RESOLVE_ONLY_IF_REQUIRED
STORAGE_PLUGIN_MANAGER=FORBIDDEN
```

Bounded F5 adapter is a filesystem-backed immutable object adapter under declared DATA_ROOT:

```text
F5_STORAGE_ADAPTER=QUALIFIED_DATA_ROOT_IMMUTABLE_FILESYSTEM
CANONICAL_OBJECT_ROOT=/var/lib/aife/data/objects
PHYSICAL_OBJECT_LOCATOR=sha256/<digest[0:2]>/<full_sha256_digest>
LOCATOR_ROLE=IMPLEMENTATION_METADATA_ONLY
WRITE_ALGORITHM=CREATE_TEMP_IN_SAME_FILESYSTEM→WRITE→FLUSH→FSYNC_FILE→ATOMIC_RENAME_IF_ABSENT→FSYNC_PARENT
EXISTING_SAME_DIGEST=VERIFY_SIZE_AND_DIGEST_THEN_COLLAPSE
EXISTING_DIFFERENT_CONTENT_FOR_LOGICAL_TARGET=PUBLICATION_CONFLICT_NO_OVERWRITE
INDEPENDENT_READBACK=NEW_READ_HANDLE→RECOMPUTE_SHA256_AND_SIZE→COMPARE_IDENTITY
```

The adapter never receives authority to derive provider/source/domain identity.

## 14. Access, PIT and exact replay

```text
PIT_IDENTITY=effective_at+known_at+provider_or_source_revision+stream_sequence_or_update_id_where_applicable+generation_or_read_set_identity+method_model_strategy_version_where_applicable+replay_cutoff_where_applicable
LATEST_ROW_IS_EXACT_REPLAY_IDENTITY=NO
LATEST_FILE_IS_EXACT_REPLAY_IDENTITY=NO
CURRENT_OBJECT_PATH_IS_EXACT_REPLAY_IDENTITY=NO
STORAGE_NATIVE_SNAPSHOT_REPLACES_DOMAIN_REPLAY_IDENTITY=NO
```

F5 extends the neutral envelope only with opaque domain-owned replay identity fields where they
are already available; AIFE does not calculate them. Exact access flow:

```text
EXACT_REQUEST
→ DOMAIN_RESOLVES_SEMANTIC_IDENTITY
→ CONTROL_REPOSITORY_RESOLVES_EXACT_REGISTERED_GENERATION
→ EXACT_PHYSICAL_LOCATOR
→ NEW_READ_HANDLE
→ CHECKSUM+CONTENT+SOURCE_REVISION_IDENTITY_VERIFICATION
→ RESULT
```

`EXACT_GENERATION` request never falls back to current. Current-read mode, if explicitly
requested, resolves the transactional current-generation pointer first and returns that exact
identity in the result.

## 15. Deployment layout and service identity

```text
RELEASE_ROOT=/opt/aife/releases/<release-id>
CURRENT_RELEASE_POINTER=/opt/aife/releases/current
PREVIOUS_RELEASE_POINTER=/opt/aife/releases/previous
DEPLOYMENT_MAP=/etc/aife/deployment-map.json
SECRET_ROOT=/etc/aife/secrets
CONTROL_DB=/var/lib/aife/control/aife-control.sqlite3
DATA_ROOT=/var/lib/aife/data
DEPLOYMENT_RECEIPTS=/var/lib/aife/deployments/receipts/<deployment-id>.json
CHECKPOINT_ROOT=/var/lib/aife/checkpoints
QUARANTINE_ROOT=/var/lib/aife/quarantine
SPOOL_ROOT=/var/spool/aife
CACHE_ROOT=/var/cache/aife
LOG_ROOT=/var/log/aife
SERVICE_ACCOUNT_NAME=aife
SERVICE_GROUP_NAME=aife
SERVICE_ACCOUNT_TYPE=DEDICATED_NON_LOGIN_RUNTIME_ACCOUNT
SERVICE_ACCOUNT_LOGIN_ALLOWED=NO
SERVICE_ACCOUNT_ROOT_REQUIRED=NO
ACTIVE_RELEASE_POINTER_TYPE=REGULAR_RELEASE_ID_POINTER_FILE
ACTIVE_RELEASE_POINTER_CONTENT=EXACT_RELEASE_ID
ROOT_RUNTIME_REQUIRED=NO
INTERACTIVE_HOME_DEPENDENCY=FORBIDDEN
```

Exact permissions:

| Surface | Owner | Group | Mode | Runtime rule |
| --- | --- | --- | --- | --- |
| `/opt/aife` and `/opt/aife/releases` dirs | `root` | `root` | `0755` | service read/execute only |
| release dir | `root` | `root` | `0755` | immutable after install |
| release regular files | `root` | `root` | `0644` | no runtime write |
| release executables | `root` | `root` | `0755` | no runtime write |
| `/opt/aife/releases/current` pointer file | `root` | `root` | `0644` | atomic replace with release-id content |
| `/opt/aife/releases/previous` pointer file | `root` | `root` | `0644` | atomic replace with prior release-id content |
| `/etc/aife` | `root` | `aife` | `0750` | service read/traverse |
| deployment map | `root` | `aife` | `0640` | service read only |
| ordinary config files | `root` | `aife` | `0640` | service read only |
| `/etc/aife/secrets` | `root` | `aife` | `0750` | no world access |
| secret files | `root` | `aife` | `0640` | group read only; no logs/receipts |
| `/var/lib/aife/control` | `aife` | `aife` | `0750` | runtime control owner |
| control DB | `aife` | `aife` | `0640` | runtime read/write |
| SQLite `-wal`/`-shm` | `aife` | `aife` | `0640` | runtime read/write |
| `/var/lib/aife/data` and object subdirs | `aife` | `aife` | `0750` | publication-authorized write |
| immutable object files | `aife` | `aife` | `0640` | no overwrite after seal |
| deployment receipt dirs | `root` | `aife` | `0750` | deployment executor write |
| deployment receipt files | `root` | `aife` | `0640` | service/operator read |
| `/var/spool/aife` | `aife` | `aife` | `0750` | only if SPOOL trigger fires |
| `/var/lib/aife/checkpoints` | `aife` | `aife` | `0750` | only if CHECKPOINT trigger fires |
| `/var/lib/aife/quarantine` | `aife` | `aife` | `0750` | only if QUARANTINE trigger fires |
| `/var/cache/aife` | `aife` | `aife` | `0750` | disposable runtime cache |
| `/var/log/aife` | `aife` | `aife` | `0750` | log files `0640` |

```text
WORLD_WRITABLE_RUNTIME_STATE=FORBIDDEN
WORLD_READABLE_SECRETS=FORBIDDEN
0777=FORBIDDEN
```

## 16. Readiness requirements — future only

No readiness test is executed by creation of this DEV_TZ.

```text
CURRENT_F5_RUNTIME_READINESS_STATUS=NOT_EVALUATED_PRE_IMPLEMENTATION
CURRENT_F5_QUALIFICATION_STATUS=NOT_RUN
READINESS_REQUIRES_DEPLOYMENT_MAP_READABLE=YES
READINESS_REQUIRES_ACTIVE_RELEASE_IDENTITY_MATCH=YES
READINESS_REQUIRES_EXPECTED_CONFIG_IDENTITY_MATCH=YES
READINESS_REQUIRES_CONTROL_BACKEND_OPENABLE=YES
READINESS_REQUIRES_CONTROL_SCHEMA_COMPATIBLE=YES
READINESS_REQUIRES_DATA_ROOT_PRESENT=YES
READINESS_REQUIRES_EXPECTED_BACKING_IDENTITY_MATCH_WHERE_APPLICABLE=YES
READINESS_REQUIRES_DATA_ROOT_WRITABLE=YES
READINESS_REQUIRES_DATA_ROOT_FREE_SPACE_PREFLIGHT=YES
READINESS_REQUIRES_BOUNDED_DURABLE_WRITE_PROBE=YES
READINESS_REQUIRES_INDEPENDENT_READBACK_PROBE=YES
FALSE_PRE_IMPLEMENTATION_RUNTIME_PASS_CLAIMS=0
```

The write probe uses a dedicated non-domain probe identity, writes bounded bytes through the
same storage port, independently reads/checksums them, and cleans only the probe object under
an explicit cleanup rule. It never produces a market-data publication or ACK.

## 17. Backup and restore proof

```text
CONTROL_DB_BACKUP_RESTORE_PROOF=REQUIRED
REFERENCED_BULK_OBJECT_READBACK_AFTER_RESTORE=REQUIRED
PUBLICATION_CURRENT_GENERATION_RECONCILIATION_AFTER_RESTORE=REQUIRED
CONTROL_BACKUP_METHOD=PYTHON_STDLIB_SQLITE3_CONNECTION_BACKUP_API
CONTROL_BACKUP_ARTIFACT=/var/lib/aife/control/backups/<backup-id>.sqlite3
RESTORE_REHEARSAL_TARGET=/var/lib/aife/control/restore-rehearsal/<restore-id>/aife-control.sqlite3
RESTORE_NEVER_OVERWRITES_ACTIVE_DB_DURING_REHEARSAL=YES
```

Backup procedure: exact schema identity → `sqlite3.Connection.backup` to new bounded artifact →
close target → SHA-256 + SQLite `integrity_check` → freeze backup identity. Restore proof:
materialize to isolated path → open with `foreign_keys=ON` → verify `schema_metadata` +
`user_version` + integrity → enumerate canonical registrations/current pointers → independently
read referenced immutable objects and compare checksums → prove current-generation
reconciliation. Corrupt/unavailable active control DB remains fail-closed until separately
authorized replacement from qualified restore. No full HA/DR is designed here.

## 18. Conditional mechanisms — exact triggers

```text
PER_MECHANISM_RECORD_COUNT=41
REQUIRED_NOW_COUNT=15
CONDITIONAL_NOW_COUNT=5
DEFERRED_COUNT=9
FORBIDDEN_NOW_COUNT=12
```

| Conditional mechanism | F5 decision | Exact trigger |
| --- | --- | --- |
| SPOOL | NOT_TRIGGERED | trigger only if accepted producer handoff must survive independently before Work+payload reference can reach durable object route because bounded backpressure would otherwise lose accepted input |
| CHECKPOINTS | NOT_TRIGGERED | trigger only if one Work cannot be safely retried from start within bounded qualification window and deterministic resumable intermediate progress is proven necessary |
| QUARANTINE | NOT_TRIGGERED | trigger only if domain/retention policy requires preserving rejected physical bytes beyond fail-closed evidence; it never becomes alternate semantic authority |
| PARQUET_WRITER | NOT_TRIGGERED | trigger only for owner-selected bulk-tabular artifact class with domain-owned schema mapping; current opaque native slice does not qualify |
| MIGRATION_FRAMEWORK_OR_TOOLING | NOT_TRIGGERED_GENERIC_FRAMEWORK | trigger generic framework only for at least two simultaneously supported nontrivial upgrade paths or a non-linear migration graph; F5 uses explicit versioned stdlib migrations |

```text
MECHANISM=MIGRATION_FRAMEWORK_OR_TOOLING
CLASSIFICATION=CONDITIONAL_NOW
RISK=SCHEMA_TRANSITION_REPEATABILITY
SIMPLER_ALTERNATIVE=BOUNDED_VERSIONED_SCRIPT
SIMPLER_ALTERNATIVE_SUFFICIENT=YES_UNLESS_BOUND_SLICE_PROVES_NEED
DOWNSTREAM_ACTION_REDUCTION=AVOID_GENERIC_MIGRATION_FRAMEWORK
RATIONALE=ONLY_IF_SCHEMA_EVOLVES
```

All 15 `REQUIRED_NOW`, 9 `DEFERRED` and 12 `FORBIDDEN_NOW` classifications remain unchanged
from the pre-DEV_TZ PRR. No unresolved implementer-choice placeholder remains.

## 19. Failure/recovery matrix F01-F26

| ID | Failure | Owner layer | Source path | Persisted state | Expected retry/recovery | Mode | Test | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | crash before durable write | server/application/\*\* | server/application/services.py | Work=PENDING\|READY; Publication=INGEST_DURABLE\|STAGED | retry same Work/Publication identity | RESUME | tests/integration/server/test_f5_publication_recovery.py | retry before write; identity stable |
| F02 | crash after write before readback | server/publication/\*\* + server/storage/\*\* | server/publication/models.py + server/storage/filesystem.py | Publication=DURABLE_STORED; durable object exists | independent readback then continue; NO_ACK | RESUME | tests/integration/server/test_f5_publication_recovery.py | no ACK before readback |
| F03 | crash after readback before registration | server/publication/\*\* + core/data/\*\* | server/publication/models.py + core/data/repositories/server_control.py | Publication=INDEPENDENT_READBACK_VERIFIED | resume registration; no duplicate object | RESUME | tests/integration/server/test_f5_publication_recovery.py | single registration for stable publication |
| F04 | crash after registration before ACK | server/publication/\*\* + core/data/\*\* | server/publication/models.py + core/data/repositories/server_control.py | Publication=CANONICALLY_REGISTERED | idempotent ACK only | RESUME | tests/integration/server/test_f5_publication_recovery.py | registration preserved; ACK retry only |
| F05 | same target + same bytes | server/publication/\*\* | server/publication/models.py | existing target+content identity | idempotent collapse | RESUME | tests/unit/server/test_publication.py | same publication/result identity |
| F06 | same target + different bytes | server/publication/\*\* | server/publication/models.py | conflict evidence; existing target differs | reject collision; no overwrite; no ACK | FAIL_CLOSED | tests/unit/server/test_publication.py | conflict evidence and non-ACK state |
| F07 | lease expiry/reclaim | server/execution/\*\* + core/data/\*\* | server/execution/models.py + core/data/repositories/server_control.py | expired Attempt/lease; Work non-terminal | new attempt + strictly newer fence | RESUME | tests/integration/server/test_f5_sqlite_control.py | new fence > old; old authority invalid |
| F08 | stale fence | server/execution/\*\* + core/data/\*\* | server/execution/models.py + core/data/repositories/server_control.py | Attempt has older fence than current | reject authority-bearing mutation | FAIL_CLOSED | tests/integration/server/test_f5_sqlite_control.py | older fence cannot terminalize/register |
| F09 | restart pending work | core/data/\*\* + server/application/\*\* | core/data/repositories/server_control.py + server/application/services.py | durable non-terminal Work | re-read and resume eligible state | RESUME | tests/integration/server/test_f5_vertical_slice.py | restart preserves Work identity/state |
| F10 | restart partial publication | core/data/\*\* + server/publication/\*\* | core/data/repositories/server_control.py + server/publication/models.py | durable Publication state | reconcile stored evidence and resume exact next state | RESUME | tests/integration/server/test_f5_publication_recovery.py | no lifecycle regression/duplication |
| F11 | DATA_ROOT missing/unmounted | server/runtime/\*\* | server/runtime/readiness.py | readiness evidence unavailable | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_permissions_and_deployment.py | DATA_ROOT present/backing predicate false |
| F12 | DATA_ROOT unwritable | server/runtime/\*\* | server/runtime/readiness.py | write capability absent | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_permissions_and_deployment.py | writability predicate false |
| F13 | DATA_ROOT insufficient space | server/runtime/\*\* | server/runtime/readiness.py | free-space preflight below bounded-probe requirement | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_permissions_and_deployment.py | space predicate false before write |
| F14 | control DB unavailable | core/data/\*\* | core/data/adapters/sqlite_control.py | connection/open failure | no claim/register/ACK; expose failure | FAIL_CLOSED | tests/integration/server/test_f5_sqlite_control.py | control operations fail closed |
| F15 | control schema incompatible | core/data/\*\* + server/runtime/\*\* | core/data/adapters/sqlite_schema.py + server/runtime/readiness.py | schema identity/version incompatible | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_sqlite_control.py | compatibility predicate false |
| F16 | control DB corrupt/unusable | core/data/\*\* + server/runtime/\*\* | core/data/adapters/sqlite_control.py + server/runtime/recovery.py | integrity/open check fails | restore + reconcile required before authority resumes | FAIL_CLOSED | tests/integration/server/test_f5_backup_restore.py | no work/ACK until qualified restore |
| F17 | deployment-map mismatch | server/configuration/\*\* + server/runtime/\*\* | server/configuration/models.py + server/runtime/readiness.py | declared roots/release/control identity mismatch | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_permissions_and_deployment.py | exact deployment-map binding required |
| F18 | release/config/schema mismatch | server/runtime/\*\* | server/runtime/readiness.py | identity tuple mismatch | block readiness/activation | FAIL_CLOSED | tests/integration/server/test_f5_permissions_and_deployment.py | all expected identities must match |
| F19 | retry after newer generation | server/publication/\*\* + core/data/\*\* | server/publication/models.py + core/data/repositories/server_control.py | current generation newer than retry target | no regression; stale retry cannot change current | FAIL_CLOSED | tests/integration/server/test_f5_publication_recovery.py | generation monotonicity |
| F20 | historical generation read | server/access/\*\* + core/data/\*\* | server/access/models.py + core/data/repositories/server_control.py | exact requested generation identity | exact read or explicit failure; never current fallback | FAIL_CLOSED | tests/integration/server/test_f5_vertical_slice.py | historical checksum/identity exact |
| F21 | control backup restore | server/runtime/\*\* + core/data/\*\* | server/runtime/recovery.py + core/data/adapters/sqlite_control.py | exact backup/schema identity | restore isolated DB, validate, reconcile before use | FAIL_CLOSED | tests/integration/server/test_f5_backup_restore.py | restore proof binds exact backup |
| F22 | bulk object after restore | server/storage/\*\* + server/runtime/\*\* | server/storage/filesystem.py + server/runtime/recovery.py | registered object locator/checksum | independent exact checksum readback | FAIL_CLOSED | tests/integration/server/test_f5_backup_restore.py | referenced object readable and exact |
| F23 | incompatible rollback/schema downgrade | core/data/\*\* + server/runtime/\*\* | core/data/adapters/sqlite_schema.py + server/runtime/readiness.py | installed code expects incompatible older schema | block; no silent downgrade | FAIL_CLOSED | tests/integration/server/test_f5_sqlite_control.py | downgrade rejected |
| F24 | duplicate deterministic scheduling slot | server/scheduling/\*\* + server/work/\*\* | server/scheduling/models.py + server/work/models.py | same schedule/policy/slot/logical input | derive same Work ID; duplicate insert collapses | RESUME | tests/unit/server/test_scheduling.py | duplicate slot => same logical work |
| F25 | concurrent claim race | core/data/\*\* + server/execution/\*\* | core/data/repositories/server_control.py + server/execution/models.py | two claimants for READY/expired work | one transaction wins; loser no authority | FAIL_CLOSED | tests/integration/server/test_f5_sqlite_control.py | ONE_CURRENT_CLAIMANT |
| F26 | illegal ACK | server/publication/\*\* + core/data/\*\* | server/publication/models.py + core/data/repositories/server_control.py | missing durable/readback/registration/identity evidence | reject ACK without state change | FAIL_CLOSED | tests/unit/server/test_publication.py | ACK predecessor conjunction enforced |

```text
FAILURE_RECOVERY_CASE_COUNT=26
FAILURE_RECOVERY_CASE_UNIQUE_COUNT=26
OLDER_FENCE_CANNOT_MUTATE_STATE_AFTER_NEWER_FENCE=YES
CURRENT_GENERATION_MONOTONICITY=REQUIRED
HISTORICAL_EXACT_READ=EXACT_OR_FAIL_CLOSED
EXACT_READ_OR_FAIL_CLOSED=YES
ILLEGAL_ACK=FAIL_CLOSED
```

## 20. Exact proposed test paths

Only existing roots are used:

```text
SERVER_UNIT_TEST_ROOT=tests/unit/server/**
SERVER_INTEGRATION_TEST_ROOT=tests/integration/server/**
CREATE_THIRD_TEST_ROOT=NO
tests/server/**=FORBIDDEN
```

Planned proof paths are exactly the test paths in the implementation map below. Existing test
files are extended where an owner surface already exists; new files are created only for SQLite
persistence, readiness, publication recovery, restore and bounded end-to-end concerns that would
otherwise mix unrelated proof families.

## 21. Machine-readable implementation map

Future canonical path is the target AIFE path; staged path is the Data Bridge overlay carrier.

```text
IMPLEMENTATION_PATH_RECORD_COUNT=32
ABSOLUTE_SAFETY_CAP=128
F5_SPECIFIC_PLANNED_PATH_COUNT=32
PATH_BUDGET_STATUS=BOUNDED_BELOW_CAP_BUT_FUTURE_AEB_MUST_RECOUNT_FULL_CUMULATIVE_STAGING_DIFF
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-01|OWNER_LAYER=server/work/**|FUTURE_CANONICAL_PATH=server/work/models.py|STAGED_PATH=AIFE/staging/server/work/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-WORK-001|TEST_FAMILY=work identity/idempotency|FAILURE_CASE_BINDING=F01,F09,F24|ACCEPTANCE_GATE=F5-I1 unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-02|OWNER_LAYER=server/scheduling/**|FUTURE_CANONICAL_PATH=server/scheduling/models.py|STAGED_PATH=AIFE/staging/server/scheduling/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-SCHEDULING-001|TEST_FAMILY=deterministic slot|FAILURE_CASE_BINDING=F24|ACCEPTANCE_GATE=F5-I3 unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-03|OWNER_LAYER=server/execution/**|FUTURE_CANONICAL_PATH=server/execution/models.py|STAGED_PATH=AIFE/staging/server/execution/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-EXECUTION-001|TEST_FAMILY=attempt/claim/lease/fence|FAILURE_CASE_BINDING=F07,F08,F25|ACCEPTANCE_GATE=F5-I3 concurrency PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-04|OWNER_LAYER=server/publication/**|FUTURE_CANONICAL_PATH=server/publication/models.py|STAGED_PATH=AIFE/staging/server/publication/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-PUBLICATION-001|TEST_FAMILY=publication lifecycle|FAILURE_CASE_BINDING=F02,F03,F04,F05,F06,F19,F26|ACCEPTANCE_GATE=F5-I5 publication PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-05|OWNER_LAYER=server/storage/**|FUTURE_CANONICAL_PATH=server/storage/ports.py|STAGED_PATH=AIFE/staging/server/storage/ports.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-STORAGE-001|TEST_FAMILY=storage port contract|FAILURE_CASE_BINDING=F02,F06,F22|ACCEPTANCE_GATE=F5-I4 port PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-06|OWNER_LAYER=server/storage/**|FUTURE_CANONICAL_PATH=server/storage/filesystem.py|STAGED_PATH=AIFE/staging/server/storage/filesystem.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTRACT-SERVER-STORAGE-001|TEST_FAMILY=bounded filesystem adapter|FAILURE_CASE_BINDING=F02,F05,F06,F22|ACCEPTANCE_GATE=F5-I4 durable write/readback PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-07|OWNER_LAYER=server/access/**|FUTURE_CANONICAL_PATH=server/access/models.py|STAGED_PATH=AIFE/staging/server/access/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-ACCESS-001|TEST_FAMILY=exact Access/PIT|FAILURE_CASE_BINDING=F20|ACCEPTANCE_GATE=F5-I6 exact-read PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-08|OWNER_LAYER=server/application/**|FUTURE_CANONICAL_PATH=server/application/services.py|STAGED_PATH=AIFE/staging/server/application/services.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=SERVER owner layering + contract suite|TEST_FAMILY=bounded lifecycle orchestration|FAILURE_CASE_BINDING=F01,F09,F10,F26|ACCEPTANCE_GATE=F5-I5 orchestration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-09|OWNER_LAYER=server/runtime/**|FUTURE_CANONICAL_PATH=server/runtime/composition.py|STAGED_PATH=AIFE/staging/server/runtime/composition.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-DEPLOYMENT-001|TEST_FAMILY=composition only|FAILURE_CASE_BINDING=F14,F17,F18|ACCEPTANCE_GATE=F5-I7 composition PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-10|OWNER_LAYER=server/runtime/**|FUTURE_CANONICAL_PATH=server/runtime/readiness.py|STAGED_PATH=AIFE/staging/server/runtime/readiness.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTRACT-SERVER-DEPLOYMENT-001|TEST_FAMILY=future readiness predicates|FAILURE_CASE_BINDING=F11,F12,F13,F15,F17,F18|ACCEPTANCE_GATE=F5-I7 readiness tests PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-11|OWNER_LAYER=server/runtime/**|FUTURE_CANONICAL_PATH=server/runtime/recovery.py|STAGED_PATH=AIFE/staging/server/runtime/recovery.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=STD-DATA-BACKUP-001|TEST_FAMILY=backup/restore/reconciliation|FAILURE_CASE_BINDING=F16,F21,F22|ACCEPTANCE_GATE=F5-I7 restore proof PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-12|OWNER_LAYER=server/configuration/**|FUTURE_CANONICAL_PATH=server/configuration/models.py|STAGED_PATH=AIFE/staging/server/configuration/models.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-DEPLOYMENT-001|TEST_FAMILY=deployment-map/config identity|FAILURE_CASE_BINDING=F17,F18|ACCEPTANCE_GATE=F5-I7 config validation PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-13|OWNER_LAYER=server/integration/**|FUTURE_CANONICAL_PATH=server/integration/domain.py|STAGED_PATH=AIFE/staging/server/integration/domain.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-ACCESS-001 + F4 authority|TEST_FAMILY=opaque replay identity carrier|FAILURE_CASE_BINDING=F20|ACCEPTANCE_GATE=F5-I6 domain-boundary PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-14|OWNER_LAYER=server/integration/**|FUTURE_CANONICAL_PATH=server/integration/bindings.py|STAGED_PATH=AIFE/staging/server/integration/bindings.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=F4 DomainArtifactEnvelope boundary|TEST_FAMILY=envelope->logical work binding|FAILURE_CASE_BINDING=F01,F24|ACCEPTANCE_GATE=F5-I8 boundary PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-15|OWNER_LAYER=core/data/repositories/**|FUTURE_CANONICAL_PATH=core/data/repositories/server_control.py|STAGED_PATH=AIFE/staging/core/data/repositories/server_control.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=Work+Execution+Publication persistence abstraction|TEST_FAMILY=SQLite-independent control repository|FAILURE_CASE_BINDING=F03,F04,F07,F08,F09,F10,F19,F25,F26|ACCEPTANCE_GATE=F5-I2 repository contract PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-16|OWNER_LAYER=core/data/adapters/**|FUTURE_CANONICAL_PATH=core/data/adapters/sqlite_control.py|STAGED_PATH=AIFE/staging/core/data/adapters/sqlite_control.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTROL_BACKEND_INITIAL=SQLITE_WAL|TEST_FAMILY=SQLite connection/UoW adapter|FAILURE_CASE_BINDING=F14,F16,F21,F25|ACCEPTANCE_GATE=F5-I2 SQLite integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-17|OWNER_LAYER=core/data/**|FUTURE_CANONICAL_PATH=core/data/adapters/sqlite_schema.py|STAGED_PATH=AIFE/staging/core/data/adapters/sqlite_schema.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=STD-DATA-SCHEMA-001 + STD-DATA-MIGRATION-001|TEST_FAMILY=bounded schema versioning|FAILURE_CASE_BINDING=F15,F23|ACCEPTANCE_GATE=F5-I1 schema tests PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-18|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_work.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_work.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-WORK-001|TEST_FAMILY=work identity/state tests|FAILURE_CASE_BINDING=F01,F09,F24|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-19|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_scheduling.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_scheduling.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-SCHEDULING-001|TEST_FAMILY=slot tests|FAILURE_CASE_BINDING=F24|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-20|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_execution.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_execution.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-EXECUTION-001|TEST_FAMILY=lease/fence tests|FAILURE_CASE_BINDING=F07,F08,F25|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-21|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_publication.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_publication.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-PUBLICATION-001|TEST_FAMILY=publication/ACK tests|FAILURE_CASE_BINDING=F02,F03,F04,F05,F06,F19,F26|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-22|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_storage.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_storage.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-STORAGE-001|TEST_FAMILY=storage capability tests|FAILURE_CASE_BINDING=F02,F06,F22|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-23|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_access.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_access.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=CONTRACT-SERVER-ACCESS-001|TEST_FAMILY=exact access tests|FAILURE_CASE_BINDING=F20|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-24|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_control_persistence.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_control_persistence.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTROL_BACKEND_INITIAL=SQLITE_WAL|TEST_FAMILY=schema/repository transaction tests|FAILURE_CASE_BINDING=F14,F15,F23,F25|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-25|OWNER_LAYER=tests/unit/server/**|FUTURE_CANONICAL_PATH=tests/unit/server/test_readiness.py|STAGED_PATH=AIFE/staging/tests/unit/server/test_readiness.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTRACT-SERVER-DEPLOYMENT-001|TEST_FAMILY=readiness predicate tests|FAILURE_CASE_BINDING=F11,F12,F13,F17,F18|ACCEPTANCE_GATE=unit PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-26|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_contract_flow.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_contract_flow.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=Server contract suite|TEST_FAMILY=end-to-end contract transitions|FAILURE_CASE_BINDING=F01-F10,F19,F26|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-27|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_data_bridge_boundary.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_data_bridge_boundary.py|EXPECTED_CHANGE_TYPE=MODIFY|CONTRACT_BINDING=F4 semantic authority|TEST_FAMILY=domain boundary parity|FAILURE_CASE_BINDING=F20|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-28|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_f5_sqlite_control.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_f5_sqlite_control.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=SQLite control profile|TEST_FAMILY=claim/schema/concurrency|FAILURE_CASE_BINDING=F07,F08,F14,F15,F23,F25|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-29|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_f5_publication_recovery.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_f5_publication_recovery.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=Publication+Storage contracts|TEST_FAMILY=publication crash matrix|FAILURE_CASE_BINDING=F02,F03,F04,F05,F06,F10,F19,F26|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-30|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_f5_backup_restore.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_f5_backup_restore.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=STD-DATA-BACKUP-001|TEST_FAMILY=control/object restore|FAILURE_CASE_BINDING=F16,F21,F22|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-31|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_f5_permissions_and_deployment.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_f5_permissions_and_deployment.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=CONTRACT-SERVER-DEPLOYMENT-001|TEST_FAMILY=layout/permissions/readiness|FAILURE_CASE_BINDING=F11,F12,F13,F17,F18|ACCEPTANCE_GATE=integration PASS
IMPLEMENTATION_ITEM=OBLIGATION_ID=F5O-32|OWNER_LAYER=tests/integration/server/**|FUTURE_CANONICAL_PATH=tests/integration/server/test_f5_vertical_slice.py|STAGED_PATH=AIFE/staging/tests/integration/server/test_f5_vertical_slice.py|EXPECTED_CHANGE_TYPE=ADD|CONTRACT_BINDING=F5 bounded slice|TEST_FAMILY=full lifecycle/restart/access|FAILURE_CASE_BINDING=F01-F10,F19,F20,F24-F26|ACCEPTANCE_GATE=F5-I8 bounded E2E PASS
```

No convenience path is authorized outside this map without owner review. A later implementation
executor may reduce path count by proving a planned new path unnecessary, but may not redirect
ownership or create a parallel framework.

## 22. Implementation phasing

| Phase | Input authority | Source paths | Test paths | Preconditions | Output | Acceptance | Stop boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F5-I1 FOUNDATION_TYPES_AND_CONTROL_SCHEMA | DEV_TZ + Work/Data schema contracts | work models + sqlite schema | unit work/control | owner execution authority | exact Work/schema v1 | deterministic identity + schema tests | no runtime activation |
| F5-I2 DURABLE_WORK_ATTEMPT_REPOSITORY | I1 | core/data repository + SQLite adapter | control unit/integration | schema v1 | durable Work/Attempt repository | restart + transaction proof | no scheduling execution outside tests |
| F5-I3 SCHEDULING_CLAIM_LEASE_FENCING | I2 + scheduling/execution contracts | scheduling/execution models | unit + SQLite concurrency | durable repository | slot/claim/lease/fence | F07/F08/F24/F25 | no publication yet |
| F5-I4 STORAGE_PORT_AND_BOUNDED_ADAPTER | Storage contract + F5 slice | storage ports/filesystem | storage unit/integration | data root test fixture | immutable write/readback | checksum + collision evidence | no canonical registration |
| F5-I5 PUBLICATION_READBACK_REGISTRATION_ACK | I2-I4 | publication + application | publication recovery/contract flow | current fence + storage | full publication lifecycle | F02-F06/F19/F26 | no Access qualification yet |
| F5-I6 ACCESS_EXACT_READ_IDENTITY | I5 + Access contract | access + integration envelope | access/boundary/vertical | canonical registration | exact generation read | F20 exact-or-fail | no backfill |
| F5-I7 READINESS_BACKUP_RESTORE_AND_RECOVERY | I2-I6 + deployment/backup | runtime/config/recovery | readiness/deployment/restore | bounded implementation complete | future readiness + restore mechanisms | F11-F18/F21-F23 | no production activation |
| F5-I8 BOUNDED_VERTICAL_SLICE_INTEGRATION_AND_QUALIFICATION_PREPARATION | I1-I7 | existing mapped source only | `test_f5_vertical_slice.py` + mapped suites | all prior PASS | qualification-ready bounded slice | lifecycle restart/retry/recovery tests | qualification still separate; no F5M/prod |

## 23. Future executor fail-closed conditions

```text
REMOTE_AUTHORITY_DRIFT=STOP
DEV_TZ_BYTE_IDENTITY_MISMATCH=STOP
OWNER_REVIEW_BINDING_MISMATCH=STOP
TASK_ID_CONFLICT=STOP
OWNER_PATH_CONFLICT=STOP
SECOND_PERSISTENCE_FRAMEWORK_REQUIRED=STOP
UNRESOLVED_SCHEMA_ARCHITECTURE_DECISION=STOP
UNRESOLVED_ACK_SEMANTICS=STOP
UNRESOLVED_FENCING_SEMANTICS=STOP
UNRESOLVED_ACCESS_IDENTITY=STOP
UNRESOLVED_SERVICE_PERMISSION_MATRIX=STOP
F5M_SCOPE_LEAK=STOP
PRODUCTION_SCOPE_LEAK=STOP
AEB_REQUIRED_PREMATURELY=STOP
PATH_BUDGET_UNBOUNDED=STOP
```

Any required deviation from schema/state-machine/owner paths above is an owner architecture
change, not implementer discretion.

## 24. DEV_TZ self-diagnostic

```text
SD01_F5_vs_F5M_boundary=PASS
SD02_one_bounded_incoming_slice=PASS
SD03_forward_only=PASS
SD04_no_existing_corpus_migration=PASS
SD05_no_production_cutover=PASS
SD06_Data_Bridge_semantic_authority=PASS
SD07_physical_locator_not_domain_identity=PASS
SD08_execution_plane_not_semantic_authority=PASS
SD09_owner_layer_application=PASS
SD10_owner_layer_core_data=PASS
SD11_core_data_reused=PASS
SD12_no_second_repository_uow=PASS
SD13_no_second_persistence_abstraction=PASS
SD14_no_server_control_default=PASS
SD15_Work_ID_exact_derivation=PASS
SD16_same_logical_input_same_work=PASS
SD17_duplicate_creation_semantics=PASS
SD18_Work_restart_semantics=PASS
SD19_Work_retry_semantics=PASS
SD20_retryable_attempt_does_not_terminalize_work=PASS
SD21_Work_terminalization=PASS
SD22_Attempt_ID_exact=PASS
SD23_atomic_claim=PASS
SD24_lease_renewal=PASS
SD25_lease_expiry_reclaim=PASS
SD26_monotonic_fencing=PASS
SD27_stale_worker_rejection=PASS
SD28_concurrent_claim_one_winner=PASS
SD29_SQLite_WAL_selected=PASS
SD30_SQLite_busy_timeout_exact=PASS
SD31_foreign_keys_on=PASS
SD32_schema_tables_complete=PASS
SD33_schema_constraints_complete=PASS
SD34_schema_indexes_complete=PASS
SD35_schema_version_mechanism=PASS
SD36_migration_three_question_decision=PASS
SD37_no_SQLAlchemy_required=PASS
SD38_no_Alembic_required=PASS
SD39_deterministic_slot_identity=PASS
SD40_F24_duplicate_slot=PASS
SD41_publication_state_machine=PASS
SD42_ACK_predecessor_gate=PASS
SD43_illegal_ACK_fail_closed=PASS
SD44_same_target_same_bytes_collapse=PASS
SD45_same_target_diff_bytes_collision=PASS
SD46_storage_port_minimal=PASS
SD47_backend_neutrality=PASS
SD48_Parquet_bounded_decision=PASS
SD49_PIT_identity_complete=PASS
SD50_exact_historical_access=PASS
SD51_deployment_layout_frozen=PASS
SD52_release_pointer_exact_path=PASS
SD53_service_account_aife=PASS
SD54_permission_matrix_exact=PASS
SD55_no_0777=PASS
SD56_readiness_future_only=PASS
SD57_qualification_not_run=PASS
SD58_backup_restore_bounded=PASS
SD59_control_and_object_restore_reconciled=PASS
SD60_F01_F26_mapped=PASS
SD61_test_roots_exact=PASS
SD62_implementation_paths_exact=PASS
SD63_conditional_triggers_exact=PASS
SD64_path_budget_bounded=PASS
SD65_no_AEB=PASS
SD66_no_runtime_mutation=PASS
SD67_Task_ID_C144_exact=PASS
SD68_C144_backlog_sync=PASS
SD69_owner_review_path_exact=PASS
SD70_scope_current_state_separated=PASS
SD71_workspace_README_frontier_currentized=PASS
SD72_execution_README_navigation_currentized=PASS
DEV_TZ_SELF_DIAGNOSTIC_CHECK_COUNT=72
DEV_TZ_SELF_DIAGNOSTIC_FAIL_COUNT=0
DEV_TZ_SELF_DIAGNOSTIC=PASS
HIDDEN_IMPLEMENTER_ARCHITECTURE_DECISIONS_REMAINING=NONE_MATERIAL_FOR_F5_IMPLEMENTATION
```

## 25. Current-state truth and stop boundary

```text
F5_PRE_DEV_TZ_PROFILE=COMPLETE
F5_CANONICAL_NAMING_BINDING=FROZEN
F5_SERVICE_IDENTITY_BINDING=FROZEN
F5_IMPLEMENTATION_DEV_TZ_CREATED=YES
F5_IMPLEMENTATION_DEV_TZ_OWNER_REVIEWED=YES
F5_IMPLEMENTATION_DEV_TZ_OWNER_REVIEW=PASS
OWNER_EXECUTION_AUTHORITY_GRANTED=NO
F5_IMPLEMENTATION_STARTED=NO
F5_IMPLEMENTATION_ALLOWED=NO_PENDING_SEPARATE_OWNER_EXECUTION_AUTHORITY
CURRENT_F5_RUNTIME_READINESS_STATUS=NOT_EVALUATED_PRE_IMPLEMENTATION
CURRENT_F5_QUALIFICATION_STATUS=NOT_RUN
F5M_STARTED=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
AEB_GENERATION=NO
REAL_AIFE_MUTATION=NO
NEXT_OWNER_TASK=GRANT_SEPARATE_F5_IMPLEMENTATION_EXECUTION_AUTHORITY
```
