---
title: "RESEARCH CONSOLIDATED: aife-server-data-foundation — server workspace and deployment layout"
status: active
owner: Architecture Lead
created: 2026-08-28
updated: 2026-08-28
review_cycle_days: 30
next_review_due: 2026-09-27
category: architecture
doc_type: analysis
language: ru
tags: [research, consolidated, server, deployment, workspace, control-state, f5p]
---

# RESEARCH CONSOLIDATED: aife-server-data-foundation — server workspace and deployment layout

## 1. Executive conclusion

F5P фиксирует deployment/workspace architecture до отдельного F5 DEV_TZ, не создавая
runtime implementation. Исходный workspace и установленный runtime разделяются: source
остаётся в canonical `server/`, immutable release устанавливается side-by-side под
`/opt/aife/releases`, mutable service state живёт вне release, а bulk data имеет отдельную
логическую корневую привязку и может быть вынесена на dedicated mount без изменения
семантической identity.

```text
RESEARCH_STATUS=PASS
F5P_RESEARCH_STAGE=PRE_DEV_TZ_GOVERNANCE_ONLY
CANONICAL_SERVER_SOURCE_ROOT=server/
FHS_LAYOUT_MODEL=AIFE_SERVICE_LAYOUT
CONTROL_STATE_INITIAL_PROFILE=SQLITE_WAL_SINGLE_INITIAL_SERVER
CONTROL_STATE_EXPANSION_PROFILE=POSTGRESQL_REQUIRED_BEFORE_SHARED_MULTI_NODE_CONTROL_QUALIFICATION
BULK_STORAGE_REQUIRED_CAPABILITY=SHARED_DURABLE_IMMUTABLE_OBJECT_OR_BLOB
BULK_STORAGE_PRODUCT=UNSELECTED
BULK_TABULAR_FORMAT=PARQUET_REQUIRED
F5_DEV_TZ_CREATED=NO
F5_IMPLEMENTATION_ALLOWED=NO
F5M_ALLOWED=NO
PRODUCTION_DEPLOYMENT_ALLOWED=NO
```

## 2. Current workspace evidence

Pinned AIFE reference `c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0`
contains canonical reusable persistence substrate:

```text
core/data/models/
core/data/repositories/
core/data/uow/
core/data/adapters/
```

`STD-ARCH-PATTERNS-001` assigns persistence/query access to Repository, use-case
orchestration to Service, lifecycle/runtime orchestration to Manager, and preserves the
layered route:

```text
Presentation → Manager → Service → Repository/Gateway → Adapter
```

`ADR-INITIALIZER-CORE-001` keeps `AppContext` as the sole public typed runtime dependency
surface. `DependencyManager` remains internal bootstrap/lifecycle substrate.

Current staged Server source already contains:

```text
server/access/
server/application/
server/configuration/
server/execution/
server/integration/
server/publication/
server/runtime/
server/scheduling/
server/storage/
server/work/
```

No competing Server root or second generic data framework is justified.

## 3. Current deployment evidence

Pinned AIFE reference contains generic/historical deployment assets under `deploy/**`,
including Docker and compose examples. Their existence is not F5 deployment authority.
The observed source bind-mount style and source-tree database locator are incompatible with
the F5P release/state separation and therefore require compatibility review before reuse.

```text
LEGACY_DEPLOY_ASSETS_ARE_F5_AUTHORITY=NO
F5_REUSE_ALLOWED=ONLY_AFTER_EXPLICIT_COMPATIBILITY_REVIEW
SOURCE_BIND_MOUNT_AS_PRODUCTION_F5_MODEL=NO
CONTROL_DATABASE_IN_SOURCE_STYLE_TREE_AS_F5_MODEL=NO
```

## 4. F5R inherited invariants

F5P preserves accepted F5R decisions instead of reopening backend architecture:

- durable transactional control state and bulk immutable storage are distinct capabilities;
- initial control profile is SQLite/WAL on one server;
- shared multi-node control requires PostgreSQL qualification first;
- high-cardinality bulk storage is a shared durable immutable object/blob capability;
- Parquet is required for bulk tabular data while object-storage product remains unselected;
- exact file/row-group/partition sizing and numeric SLO/RPO/RTO remain measurement-bound;
- semantic identity never depends on database row, filesystem path, bucket or mount point;
- F5 qualifies bounded new incoming physical lifecycle before F5M migrates existing corpus.

## 5. External primary evidence carried forward

F5P does not reopen the resolved filesystem research. The selected model remains grounded in:

- Linux FHS 3.0: <https://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html>;
- systemd file hierarchy guidance: <https://www.freedesktop.org/software/systemd/man/latest/file-hierarchy.html>;
- SQLite WAL: <https://www.sqlite.org/wal.html>;
- SQLite Online Backup API: <https://www.sqlite.org/backup.html>;
- PostgreSQL file-location/configuration guidance:
  <https://www.postgresql.org/docs/current/runtime-config-file-locations.html>.

The FHS conclusion is intentionally narrow: `/opt/aife` is an immutable release carrier in
an AIFE service layout. F5P does not claim strict `/opt/<package>` projection compliance.

## 6. Server source skeleton

```text
CANONICAL_SERVER_SOURCE_ROOT=server/
BOOTSTRAP_SOURCE_ROOT=server/runtime/
APPLICATION_SERVICE_ROOT=server/application/
WORK_SOURCE_ROOT=server/work/
SCHEDULING_SOURCE_ROOT=server/scheduling/
EXECUTION_SOURCE_ROOT=server/execution/
PUBLICATION_SOURCE_ROOT=server/publication/
STORAGE_SOURCE_ROOT=server/storage/
ACCESS_SOURCE_ROOT=server/access/
DOMAIN_INTEGRATION_ROOT=server/integration/
CONFIGURATION_SOURCE_ROOT=server/configuration/
DEPLOYMENT_ASSET_ROOT=deploy/server/
INSTALLER_SOURCE_ROOT=deploy/server/installer/
SERVER_TEST_LAYOUT=UNIT:tests/unit/server/**;INTEGRATION:tests/integration/server/**
CREATE_THIRD_TEST_ROOT=NO
TEST_PLACEMENT_FOLLOWS_EXISTING_REPOSITORY_CONVENTION=YES
```

These are source ownership/projection locations. They are not Linux runtime filesystem
locations and this research creates no implementation files in them.

## 7. Application orchestration versus durable control persistence

Current `server/application/**` is an application-facing service composition boundary. It is
not a concrete transactional persistence framework. Current `server/storage/**` exposes
backend-neutral object/storage lifecycle capabilities such as durable object write, readback,
inventory, migration, retention, backup and restore. Those capabilities must not silently
absorb control-plane transactional persistence.

The reusable persistence substrate already exists in `core/data/**`:

- `repositories/**` owns generic persistence/query abstraction;
- `uow/**` owns commit/rollback transaction coordination;
- `adapters/**` owns backend/session adapter substrate;
- `models/**` may host generic persistence models when they are not Server business semantics.

The frozen owner chain is:

```text
CONTROL_STATE_APPLICATION_OWNER=server/application/
CONTROL_STATE_PERSISTENCE_ABSTRACTION_OWNER=core/data/**
CONTROL_STATE_PERSISTENCE_ADAPTER_OWNER=core/data/adapters/**
CONTROL_STATE_IMPLEMENTATION_ROOT=DEV_TZ_IMPLEMENTATION_BOUND_WITH_CANONICAL_OWNER_CHAIN_DEFINED
CONTROL_STATE_SCHEMA_MIGRATION_OWNER=core/data/**
CONTROL_STATE_REUSES_CORE_DATA_SUBSTRATE=YES
NEW_GENERIC_PERSISTENCE_FRAMEWORK=NO
CONTROL_STATE_AND_BULK_STORAGE_OWNER_COLLAPSED=NO
NEW_SERVER_CONTROL_ROOT_REQUIRED=NO
```

Work/Execution/Publication contracts retain semantic state authority. `core/data/**` owns
reusable persistence mechanics, not Work/Execution/Publication meaning. Future DEV_TZ may
choose the exact thin Server-specific module/binding location while remaining inside this
owner chain; this does not reopen architecture ownership.

### 7.1 Control placement review C1-C8

```text
C1_SERVER_STORAGE_CURRENTLY_OWNS_TRANSACTIONAL_CONTROL_PERSISTENCE=NO
C2_PUTTING_CONTROL_DB_ADAPTERS_IN_SERVER_STORAGE_WOULD_CONFUSE_CONTROL_AND_BULK=YES
C3_CORE_DATA_CAN_HOST_REUSABLE_TRANSACTIONAL_SUBSTRATE=YES
C4_SERVER_SPECIFIC_CONTROL_PERSISTENCE_NEEDS_THIN_BINDING_ABOVE_CORE_DATA=YES
C5_NEW_SERVER_CONTROL_PACKAGE_REQUIRED=NO
C6_LAYERED_ROUTE_PRESERVED=YES
C7_APP_CONTEXT_SOLE_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
C8_CONTROL_AND_BULK_RECOVERY_DOMAINS_REMAIN_SEPARATE=YES
CONTROL_STATE_SOURCE_PLACEMENT_REVIEW=PASS
```

## 8. Selected filesystem model

```text
FHS_LAYOUT_MODEL=AIFE_SERVICE_LAYOUT
OPT_AIFE_IS_IMMUTABLE_RELEASE_CARRIER_ONLY=YES
STRICT_OPT_PACKAGE_PROJECTION_COMPLIANCE_CLAIMED=NO
```

`AIFE_SERVICE_LAYOUT` deliberately uses standard service-state classes without claiming that
all mutable files are a strict projection of `/opt/aife`.

## 9. Canonical Linux deployment tree

```text
/opt/aife/
├── releases/
│   └── <release-id>/
├── current -> releases/<release-id>
└── previous -> releases/<release-id>

/etc/aife/
├── deployment-map.json
└── secrets/

/var/lib/aife/
├── control/
│   └── aife-control.sqlite3
├── checkpoints/
├── data/
│   ├── objects/
│   ├── parquet/
│   └── manifests/
├── quarantine/
└── deployments/
    └── receipts/
        └── <deployment-id>.json

/var/spool/aife/
└── ingest/

/var/cache/aife/

/var/log/aife/
```

```text
CANONICAL_INSTALL_ROOT=/opt/aife
CANONICAL_RELEASE_ROOT=/opt/aife/releases
CURRENT_RELEASE_POINTER=/opt/aife/current
PREVIOUS_RELEASE_POINTER=/opt/aife/previous
CANONICAL_CONFIG_ROOT=/etc/aife
CANONICAL_SECRET_ROOT=/etc/aife/secrets
CANONICAL_STATE_ROOT=/var/lib/aife
CANONICAL_CONTROL_DB_PATH=/var/lib/aife/control/aife-control.sqlite3
CHECKPOINT_ROOT=/var/lib/aife/checkpoints
CANONICAL_SPOOL_ROOT=/var/spool/aife
INGEST_ROOT=/var/spool/aife/ingest
CANONICAL_CACHE_ROOT=/var/cache/aife
CANONICAL_DATA_ROOT=/var/lib/aife/data
CANONICAL_OBJECT_ROOT=/var/lib/aife/data/objects
CANONICAL_PARQUET_ROOT=/var/lib/aife/data/parquet
CANONICAL_MANIFEST_ROOT=/var/lib/aife/data/manifests
QUARANTINE_ROOT=/var/lib/aife/quarantine
CANONICAL_LOG_ROOT=/var/log/aife
CANONICAL_DEPLOYMENT_MAP_PATH=/etc/aife/deployment-map.json
CANONICAL_DEPLOYMENT_RECEIPT_ROOT=/var/lib/aife/deployments/receipts
CANONICAL_DEPLOYMENT_RECEIPT_PATH=/var/lib/aife/deployments/receipts/<deployment-id>.json
```

## 10. Source, release, state and data separation

```text
DIRECT_PRODUCTION_EXECUTION_FROM_GIT_CHECKOUT=NO
PRODUCTION_UPDATE_BY_GIT_PULL=NO
RUNTIME_WRITES_TO_SOURCE_CHECKOUT=FORBIDDEN
RUNTIME_WRITES_TO_INSTALLED_RELEASE=FORBIDDEN
CONTROL_DB_INSIDE_SOURCE=FORBIDDEN
CONTROL_DB_INSIDE_RELEASE=FORBIDDEN
BULK_DATA_INSIDE_SOURCE=FORBIDDEN
BULK_DATA_INSIDE_RELEASE=FORBIDDEN
SECRETS_INSIDE_RELEASE=FORBIDDEN
LOGS_INSIDE_RELEASE=FORBIDDEN
IMMUTABLE_RELEASE_MODEL=YES
ATOMIC_RELEASE_ACTIVATION=YES
```

A source revision is input to a release build/install process, not a mutable runtime home.
Release identity, control schema identity, configuration identity and data-generation identity
remain different identities.

## 11. SQLite/WAL control profile

Initial F5 control state uses one host-local SQLite database in WAL mode at the declared
control locator. It owns durable records needed by Work/Execution/Publication orchestration,
not bulk market/history bytes.

```text
CONTROL_BACKEND_INITIAL=SQLITE_WAL
SQLITE_IS_BULK_DATA_WAREHOUSE=NO
SQLITE_CONTROL_STATE_NODE_LOCAL=YES
SQLITE_CONTROL_STATE_SHARED_N_NODE_AUTHORITY=NO
```

WAL/shm/temporary artifacts are part of the SQLite control recovery domain and must not be
moved independently from the database semantics. Backup/restore qualification must follow
SQLite-supported mechanisms rather than treating file copy while active as generic proof.

## 12. PostgreSQL expansion

PostgreSQL remains an expansion profile required before shared multi-node control
qualification. Moving control persistence from SQLite to PostgreSQL must preserve Work,
Attempt, Claim/Lease/Fence, Publication and current-generation identities; it may not change
bulk object/manifests or domain semantic identities.

```text
POSTGRESQL_REQUIRED_BEFORE_SHARED_MULTI_NODE_CONTROL_QUALIFICATION=YES
POSTGRESQL_IS_BULK_DATA_WAREHOUSE=NO
CONTROL_BACKEND_MIGRATION_PRESERVES_SEMANTIC_IDENTITY=YES
```

## 13. Bulk data and mount model

`CANONICAL_DATA_ROOT=/var/lib/aife/data` is a logical deployment root. Its physical backing may
be a dedicated filesystem/mount or a qualified shared object/blob adapter mapping without
changing consumer semantics.

```text
DATA_ROOT_MAY_BE_DEDICATED_MOUNT=YES
ROOT_FILESYSTEM_COLOCATION_REQUIRED=NO
DATA_MOUNT_PREFLIGHT_REQUIRED=YES
FREE_SPACE_PREFLIGHT_REQUIRED=YES
FILESYSTEM_PATH_IS_SEMANTIC_DATA_IDENTITY=NO
```

Mount/device/object backing is discoverable through the deployment map rather than guessed
from host layout.

## 14. Objects, Parquet and manifests

Bulk domains remain distinct:

- immutable native/source-fidelity objects under logical object root;
- Parquet bulk-tabular generations under logical Parquet root;
- immutable bounded versioned manifests under logical manifest root;
- transactional current-generation registration in control state.

One event per physical object is not the default model; exact batching/file/row-group and
partition sizing remain measurement-bound.

## 15. Spool, checkpoints and quarantine

`/var/spool/aife/ingest` is durable pending-work/ingest staging, not accepted canonical bulk
history. `/var/lib/aife/checkpoints` stores durable execution/progress checkpoints according
to owner policy. `/var/lib/aife/quarantine` isolates failed/unaccepted material and is not an
alternate authority.

## 16. Configuration and secrets

Configuration and secrets are independent from immutable releases:

```text
CONFIG_ROOT=/etc/aife
SECRET_ROOT=/etc/aife/secrets
CONFIG_IDENTITY_REQUIRED=YES
SECRET_BYTES_IN_RELEASE=FORBIDDEN
SECRET_BYTES_IN_DEPLOYMENT_RECEIPT=FORBIDDEN
```

A deployment binds a release to a configuration identity/digest. Secret references or
credential classes may be recorded; secret values may not be copied into manifests/receipts.

## 17. Deployment map

A machine-readable deployment map is required at `/etc/aife/deployment-map.json`.
It is operational discovery/configuration authority for one deployment, not domain semantic
authority.

Minimum fields/concepts:

```text
schema_version
release_root
current_release
previous_release
config_root
secret_root
state_root
control_backend
control_locator
control_schema_identity
checkpoint_root
spool_root
ingest_root
cache_root
logical_data_root
object_root
parquet_root
manifest_root
quarantine_root
log_root
mount_or_storage_binding
```

```text
DEPLOYMENT_MAP_REQUIRED=YES
OPERATOR_FILESYSTEM_GUESSING_REQUIRED=NO
```

## 18. Deployment receipt

Every install/upgrade/rollback attempt that reaches the deployment execution boundary must
produce durable evidence under
`/var/lib/aife/deployments/receipts/<deployment-id>.json`.

Expected evidence includes source head/tree, release identity/digest, configuration digest,
control backend/schema identity, persistent-root bindings, installation/migration result,
health/readback result, activation result, predecessor/rollback target where applicable, and
terminal outcome.

```text
DEPLOYMENT_RECEIPT_REQUIRED=YES
DEPLOYMENT_RECEIPT_IS_DOMAIN_SEMANTIC_AUTHORITY=NO
```

## 19. Install from zero

Conceptual installation order is frozen:

```text
HOST_PREFLIGHT
→ SERVICE_ACCOUNT
→ DIRECTORY_LAYOUT
→ PERMISSIONS
→ MOUNT_AND_SPACE_PREFLIGHT
→ RELEASE_DIGEST_VERIFICATION
→ SIDE_BY_SIDE_IMMUTABLE_INSTALL
→ CONFIG_INSTALL
→ CONTROL_BACKEND_INIT
→ SCHEMA_COMPATIBILITY_OR_MIGRATION
→ SERVICE_REGISTRATION
→ PRE_ACTIVATION_VALIDATION
→ ATOMIC_ACTIVATION
→ HEALTH
→ WRITE_READBACK
→ DEPLOYMENT_RECEIPT
```

Activation before required validation is forbidden. An interrupted install must be
reconcilable from immutable release identity, declared roots and durable deployment evidence.

## 20. Immutable release model

Each release has an immutable `release-id` and digest. Installing a new release creates a new
side-by-side directory; it does not mutate the old release or source checkout. `current` and
`previous` pointers are activation metadata, not release identity themselves.

## 21. Upgrade

Upgrade installs and validates a new immutable release before atomically changing active
release. Persistent state/data roots are reused by declared compatibility/migration rules and
must not be overwritten by release installation.

```text
CODE_RELEASE_IDENTITY_NE_CONTROL_SCHEMA_IDENTITY=YES
CODE_RELEASE_IDENTITY_NE_CONFIG_IDENTITY=YES
CODE_RELEASE_IDENTITY_NE_DATA_GENERATION_IDENTITY=YES
```

## 22. Rollback

Rollback must select an explicit predecessor release and verify that control schema,
configuration and data-generation compatibility permit the transition. A code pointer rollback
is not permission to silently downgrade a database schema.

```text
SILENT_DATABASE_DOWNGRADE=FORBIDDEN
ROLLBACK_TARGET_IDENTITY_REQUIRED=YES
```

## 23. Service account and permissions

Future installer must use a dedicated service identity and least-privilege ownership. Release
files are runtime-read-only; config/secrets/state/spool/cache/data/log roots receive only the
permissions required by their role. Exact UID/GID and OS packaging mechanism remain DEV_TZ or
host-profile details.

## 24. Logging and observability

Logs belong under `/var/log/aife` or the selected service logging sink while preserving the
approved logging standard. Runtime logs are never written into source or release directories.
Monitoring implementation remains downstream; F5P does not approve a new monitoring service.

## 25. Container boundary

Containers are optional execution packaging, not deployment authority.

```text
CONTAINERS_REQUIRED_FOR_INITIAL_F5=NO
DOCKER_COMPOSE_IS_CANONICAL_SERVER_AUTHORITY=NO
ANONYMOUS_PERSISTENT_DOCKER_VOLUME_ALLOWED=NO
CONTAINER_HOST_MOUNTS_MUST_BE_DECLARED_IN_DEPLOYMENT_MAP=YES
```

A containerized profile must bind the same logical config/state/spool/data/log roots and may
not hide persistent authority in anonymous volumes.

## 26. Backup and recovery domains

At minimum the following recovery domains remain explicit:

1. CONTROL_STATE — work/attempt/claim/lease/fence/publication/current-generation state;
2. BULK_DATA — immutable objects and Parquet generations;
3. MANIFESTS — immutable generation/manifests and reconciliation evidence;
4. CONFIG — non-secret configuration identity/content;
5. SECRETS — externalized credentials with separate handling;
6. DEPLOYMENT_EVIDENCE — deployment maps/receipts and release identity evidence.

```text
BACKUP_EXISTS_EQUALS_RESTORE_PROVEN=NO
REPLICATION_EQUALS_BACKUP=NO
CONTROL_AND_BULK_RECOVERY_DOMAINS_SEPARATE=YES
```

Restore qualification must prove semantic/readback reconciliation before authority resumes.

## 27. Node-local versus shared matrix

| Artifact/capability | Initial one-node profile | Future multi-node profile |
| --- | --- | --- |
| installed release | node-local immutable copy | immutable release per node/image |
| config | node-local declared config identity | centrally distributed/declared identity |
| secrets | node-local/managed secret binding | managed/shared secret authority |
| SQLite control state | node-local authoritative control DB | not shared-control authority |
| PostgreSQL control state | optional/not required | shared transactional control authority |
| spool | node-local bounded staging | node-local/partitioned staging |
| cache | node-local rebuildable | node-local or measured shared cache |
| logs | node-local sink/forwarding | per-node sink with centralized projection optional |
| bulk objects | logically shared durable capability | shared durable capability |
| Parquet | logically shared durable capability | shared durable capability |
| manifests | shared/independently readable | shared/independently readable |
| deployment receipts | durable per-deployment evidence | durable per-node/deployment evidence |

Changing 1→N→1 nodes changes execution/storage adapters and operational binding, not semantic
identity contracts.

## 28. Failure modes

- source workspace unavailable: installed immutable release continues without source mutation;
- interrupted release install: incomplete release stays inactive;
- failed activation: retain previous active release and emit failed receipt;
- SQLite process/host failure: recover from qualified control backup/reconciliation;
- stale worker: cannot commit terminal/publication effect after fencing loss;
- bulk object corruption: checksum/readback failure, restore or explicit rebuild policy;
- data mount absent/full: fail preflight or fail closed before canonical publication;
- config mismatch: fail pre-activation validation;
- rollback with incompatible schema: block rollback, never silently downgrade;
- container loss: declared host/shared persistence remains authoritative, not container layer.

## 29. Rejected alternatives

Rejected for F5P:

- runtime directly from Git checkout;
- `git pull` as production update mechanism;
- database or bulk history inside source/release trees;
- `server/storage/**` as a catch-all owner for transactional control persistence;
- a second generic Repository/UoW framework under `server/**`;
- new `server/control/**` package merely for naming symmetry;
- strict `/opt/<package>` compliance claim for the mixed service layout;
- anonymous persistent container volumes;
- product/vendor selection without qualification evidence.

## 30. Measurement-bound decisions

Still open for later qualified tasks:

- exact object/blob backend product;
- exact Parquet partition/file/row-group sizing and compression;
- numeric throughput/latency SLO;
- numeric RPO/RTO;
- PostgreSQL HA topology;
- exact service user IDs/OS package mechanism;
- whether a thin Server-specific control binding receives a dedicated submodule name.

None of these open measurements changes the frozen ownership or filesystem model.

## 31. Owner disposition

```text
RESEARCH_ARTIFACT=CREATE
CONTRACT-SERVER-DEPLOYMENT-001=CREATE
PROGRAM_MAP=AMEND
CONTRACTS_REGISTRY=AMEND
ADR-DATA-FOUNDATION-001=NO_CHANGE
DATA_STANDARDS=NO_CHANGE
EXISTING_SERVER_CONTRACTS=NO_CHANGE
NEW_STANDARD_COUNT=0
NEW_ADR_COUNT=0
NEW_CONTRACT_COUNT=1
```

The deployment relation passes the three-question Contract gate: no existing contract owns
it completely; it is stable across backend/container variants; and it binds multiple
artifacts/processes/roles.

## 32. Exact DEV_TZ inputs

A future separate F5 DEV_TZ can proceed without reopening deployment-layout research using:

- canonical source root and Server sub-root map;
- frozen control persistence owner chain;
- `AIFE_SERVICE_LAYOUT` paths;
- initial SQLite/WAL and PostgreSQL expansion boundary;
- deployment map/receipt schemas to be concretized;
- install/upgrade/rollback order;
- mount/space preflight requirements;
- protected distinction between control state and bulk object/Parquet/manifests;
- explicit measurement-bound items and qualification gates.

```text
F5_DEV_TZ_CREATION_ALLOWED=YES_AS_NEXT_SEPARATE_OWNER_TASK_AFTER_F5P_REMOTE_CLOSURE
F5_DEV_TZ_CREATED=NO
```

## 33. Research review Q1-Q26

```text
Q1_NO_SECOND_AIFE_DATA_FRAMEWORK=YES
Q2_SOURCE_RELEASE_STATE_DATA_SEPARATED=YES
Q3_PERSISTENT_CLASS_ROOTS_DETERMINISTIC=YES
Q4_ACTIVE_RELEASE_DISCOVERABLE=YES
Q5_ACTIVE_CONTROL_BACKEND_DISCOVERABLE=YES
Q6_UPDATE_PRESERVES_PERSISTENT_STATE=YES
Q7_ROLLBACK_DISTINGUISHES_RELEASE_SCHEMA_CONFIG_DATA=YES
Q8_SQLITE_TO_POSTGRESQL_EVOLUTION_PRESERVED=YES
Q9_BULK_STORAGE_BACKEND_PORTABLE=YES
Q10_FILESYSTEM_PATH_NOT_SEMANTIC_IDENTITY=YES
Q11_BACKUP_NOT_EQUAL_RESTORE_PROOF=YES
Q12_CONTAINER_NOT_HIDDEN_AUTHORITY=YES
Q13_APP_CONTEXT_ROUTE_PRESERVED=YES
Q14_CORE_DATA_REUSED_NOT_DUPLICATED=YES
Q15_INSTALLER_CAN_BE_IDEMPOTENT_RESTART_SAFE_BY_DESIGN=YES
Q16_DEV_TZ_DOES_NOT_NEED_LAYOUT_RESEARCH=YES
Q17_PERSISTENT_ARTIFACT_LOCATIONS_DETERMINISTIC=YES
Q18_TWO_AGENTS_CAN_CHOOSE_MATERIALLY_DIFFERENT_COMPLIANT_LAYOUTS=NO
Q19_OPERATOR_DISCOVERY_WITHOUT_FILESYSTEM_GUESSING=YES
Q20_DEPLOYMENT_DOES_NOT_MUTATE_SOURCE_WORKSPACE=YES
Q21_APPLICATION_ORCHESTRATION_DISTINCT_FROM_CONTROL_PERSISTENCE=YES
Q22_AIFE_SERVICE_LAYOUT_INTERNALLY_CONSISTENT=YES
Q23_DATA_ROOT_CAN_MOVE_WITHOUT_SEMANTIC_IDENTITY_CHANGE=YES
Q24_LOGICAL_DATA_ROOT_AND_BACKING_DISCOVERABLE=YES
Q25_CONTROL_PERSISTENCE_OWNERSHIP_UNAMBIGUOUS_AND_NOT_BULK=YES
Q26_DEV_TZ_CAN_IMPLEMENT_SQLITE_POSTGRES_ADAPTERS_WITHOUT_REOPENING_OWNERSHIP=YES
RESEARCH_REVIEW_Q1_Q26=PASS
```

## 34. Non-goals

This F5P task does not create or modify F5 DEV_TZ, control adapters, installer code, systemd
units, SQLite databases, PostgreSQL deployment, real server directories, runtime source,
tests, production deployment, F5 implementation, F5M migration or product selection.
