---
title: "AIFE Server/Data Foundation — F3: source skeleton and core mechanisms"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
category: architecture
doc_type: report
language: ru
tags: [server, data, f3, source, work, scheduling, execution, publication, storage, access]
authority_reference:
  - ../../../../../../AGENTS.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
  - ../f2-minimum-server-contracts/README.md
related:
  - ../f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
---

# AIFE Server/Data Foundation — F3: source skeleton and core mechanisms

## 1. Authority и implementation boundary

```text
TASK_ID=AIFE-SERVER-DATA-PATCH-FACTORY-F3-SOURCE-SKELETON-CORE-MECHANISMS-R01
CHECKPOINT=CHECKPOINT_F3_SERVER_SOURCE_SKELETON_AND_CORE_MECHANISMS
PREDECESSOR_CHECKPOINT=CHECKPOINT_F2_MINIMUM_SERVER_ARTIFACT_CONTRACTS
PREDECESSOR_WIP_HEAD=fec845a747af827f2559880a7f7b63be716bd469
PREDECESSOR_WIP_TREE=030068b43aaed22106157cd497e427c759ca7622
SERVER_ROOT=server/
PHYSICAL_WIP_ROOT=AIFE/staging/server/
SERVER_ROOT_MATERIALIZED=YES
SERVER_IMPLEMENTATION_STARTED=YES
ETH_INTEGRATION_STARTED=NO
SERVER_DEPLOYMENT_STARTED=NO
MIGRATION_STARTED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
```

F3 — первый физический source checkpoint Server/Data Foundation. Он материализует только
backend-neutral Python 3.11 foundation и contract-driven tests. Production database, queue,
network API, storage adapter, scheduler loop, multiprocess orchestration и ETH Data Bridge
integration не выбираются и не реализуются.

## 2. Exact source layout

```text
server/
├── __init__.py
├── _validation.py
├── access/
│   ├── __init__.py
│   └── models.py
├── application/
│   ├── __init__.py
│   └── services.py
├── configuration/
│   ├── __init__.py
│   └── models.py
├── execution/
│   ├── __init__.py
│   └── models.py
├── publication/
│   ├── __init__.py
│   └── models.py
├── runtime/
│   ├── __init__.py
│   └── composition.py
├── scheduling/
│   ├── __init__.py
│   └── models.py
├── storage/
│   ├── __init__.py
│   └── ports.py
└── work/
    ├── __init__.py
    └── models.py
```

`security/` и `observability/` не создаются пустыми placeholder-пакетами: текущий F3 scope не
требует от них отдельной реализации. Поэтому skeleton отражает только реально используемые
responsibility boundaries.

```text
SERVER_SOURCE_PATH_COUNT=20
EMPTY_PLACEHOLDER_MODULE_COUNT=0
```

## 3. Module → F2 contract map

| F3 module | Normative input | Responsibility |
| --- | --- | --- |
| `server/work/models.py` | `CONTRACT-SERVER-WORK-001` | immutable logical work identity, lifecycle, attempt/idempotency/provenance references, transition validation |
| `server/scheduling/models.py` | `CONTRACT-SERVER-SCHEDULING-001` | timezone-aware schedule definition, deterministic due identity, due/materialization separation, retry decision boundary |
| `server/execution/models.py` | `CONTRACT-SERVER-EXECUTION-001` | claim/lease/attempt/fence value objects, expiry/renew/reclaim, current-fence terminal authority |
| `server/publication/models.py` | `CONTRACT-SERVER-PUBLICATION-001` | publication state machine, identity/read-back/registration evidence, four-proof ACK gate |
| `server/storage/ports.py` | `CONTRACT-SERVER-STORAGE-001` | narrow async capability protocols for ingest/write/read-back/identity/inventory/migration/retention/backup/restore |
| `server/access/models.py` | `CONTRACT-SERVER-ACCESS-001` | generic typed query/filter/result identity/revision/provenance/pagination/partial/error boundary |
| `server/application/services.py` | all six | application-facing async service protocols without concrete backend |
| `server/runtime/composition.py` | architecture/F1G | typed non-global runtime dependency surface prepared for future `AppContext` composition |
| `server/configuration/models.py` | execution/scheduling | process-role and lease/retry timing value types only |
| `server/_validation.py` | shared pure mechanism | non-empty/timezone/stable-identity validation helpers without domain semantics |

```text
WORK_IMPLEMENTATION=PASS
SCHEDULING_IMPLEMENTATION=PASS
EXECUTION_IMPLEMENTATION=PASS
PUBLICATION_IMPLEMENTATION=PASS
STORAGE_PORTS=PASS
ACCESS_BOUNDARY=PASS
```

## 4. State and failure decisions

WORK preserves `WORK_ID` across retry by default while execution attempts receive distinct
`AttemptId`. Illegal lifecycle transitions are rejected. No process-local memory is declared as
future durable authority.

SCHEDULING constructs `DueIdentity` deterministically from schedule identity, policy revision,
timezone-aware due instant and slot semantics. Due computation does not claim execution and does
not directly execute work.

EXECUTION models lease/fencing authority so an expired or superseded fence cannot authorize a
terminal durable effect. Reclaim advances authority generation and produces a new fence/attempt
boundary for the same logical work.

PUBLICATION preserves the accepted lifecycle:

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

ACK is allowed only when durable storage, independent read-back, canonical registration and exact
identity match are all present. A read-back mismatch blocks ACK. Interruption before ACK remains
reconcilable and retryable without creating a second publication identity.

```text
RESTART_MODEL_IMPLEMENTABLE=YES
FAILURE_MODEL_IMPLEMENTABLE=YES
ONLY_CURRENT_FENCING_AUTHORITY_MAY_COMMIT_TERMINAL_EFFECT=YES
STALE_WORKER_CAN_COMMIT_AFTER_FENCE_LOSS=NO
```

## 5. Ports and no-backend decisions

Storage is split into narrow async `Protocol` capabilities rather than one storage god-interface.
No concrete database/object-store/filesystem implementation appears in public Server/Data models.
Application services are also async protocols, while `ServerRuntimeDependencies` is a frozen typed
composition value object rather than a singleton or service locator.

```text
DATABASE_VENDOR_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
FILESYSTEM_AS_PRODUCTION_AUTHORITY=NO
PARQUET_AS_UNIVERSAL_BACKEND=NO
NO_GLOBAL_SINGLETON_RUNTIME=YES
NO_HIDDEN_SERVICE_LOCATOR=YES
APP_CONTEXT_INTEGRATION_PREPARED=YES
APP_CONTEXT_ACTUAL_GLOBAL_REWIRE=DEFERRED
PARALLEL_DATA_SUBSTRATE_CREATED=NO
CORE_MANAGER_GLOBALIZED=NO
TASK_MANAGER_PROMOTED_TO_DURABLE_SCHEDULER=NO
DEPENDENCY_MANAGER_PUBLIC_SERVICE_LOCATOR=NO
```

## 6. Process roles

`server.configuration.ProcessRole` defines only the future role identities:

```text
CONTROL
WORKER
COMBINED_INITIAL_NODE
```

There is no process manager, supervisor, worker pool or distributed scheduler loop in F3.

```text
PROCESS_ROLE_TYPES_DEFINED=YES
HORIZONTAL_RUNTIME_STARTED=NO
```

## 7. Contract-driven tests

F3 materializes eight tests under repository-native future AIFE layout:

```text
tests/unit/server/test_work.py
tests/unit/server/test_scheduling.py
tests/unit/server/test_execution.py
tests/unit/server/test_publication.py
tests/unit/server/test_storage.py
tests/unit/server/test_access.py
tests/unit/server/test_runtime_composition.py
tests/integration/server/test_contract_flow.py
```

The unit suite proves valid/invalid work transitions, logical-identity-preserving retry,
timezone-aware deterministic due identities, fence loss/reclaim semantics, publication order and
ACK gates, capability-bounded storage protocols, access identity/provenance and explicit partial
results. The integration proof composes the generic flow without importing ETH/provider semantics.

```text
TEST_PATH_COUNT=8
CONTRACT_DRIVEN_TESTS=PASS
CROSS_MODULE_TESTS=PASS
ETH_DOMAIN_IMPORT_COUNT=0
IMPORT_CYCLES=0
```

## 8. Repository-derived integration consequences

F3 does not change `pyproject.toml`: F1G already admitted `server*` to package discovery and quality
scope. Two existing repository control policies require narrow updates:

1. `.aife/architecture_tree_sync_rules.json` adds the top-level `server/**` runtime/product zone
   and its dedicated `server-tree` surface.
2. `.aife/file_placement_rules.json` admits `tests/unit/server` in the existing structural-layout
   allow/required set.

Architecture projections are updated for the new source and test surfaces:

```text
docs/10-Architecture/general/architecture-trees/root/root-tree.md
docs/10-Architecture/general/architecture-trees/root/module-directories.md
docs/10-Architecture/general/architecture-trees/runtime/server-tree.md
docs/10-Architecture/general/architecture-trees/tooling/tests-verification-tree.md
```

## 9. Exact F3 operation map

```text
SERVER_SOURCE_PATH_COUNT=20
TEST_PATH_COUNT=8
EXISTING_INTEGRATION_PATH_COUNT=2
GENERATED_PATH_COUNT=4
CHECKPOINT_DOC_PATH_COUNT=1
CONTROL_PATH_COUNT=2
TOTAL_PATH_COUNT=37
HARD_MAX_CHANGED_PATHS=128
UNRELATED_PATHS=NONE
```

The two Data Bridge control/evidence files are publication metadata and are not canonical AIFE
overlay inputs. All other F3 paths project through `AIFE/staging/**` by stripping the staging
prefix.

## 10. Quality and accumulated compatibility

Targeted Python quality uses only the supplied canonical toolchain substrate, Python 3.11 runtime
and repository-native checks. No toolchain or qualification build is performed.

```text
F3_TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=21
F3_TYPECHECK=PASS
F3_LINT=PASS
F3_FORMAT_CHECK=PASS
F3_IMPORT_CHECK=PASS
CONTRACT_REGISTRY=PASS
CONTRACT_REFERENCES=PASS
REGISTRY_GENERATOR_CHECK=PASS
OWNER_GENERATED_SYNC=PASS
SEMANTIC_CATALOGS=PASS
ARCHITECTURE_TREE_SYNC=PASS
STRUCTURAL_LAYOUT=PASS
STRUCTURAL_PRESSURE=PASS
AIFE_COMPATIBILITY_VALIDATION=PASS
DATA_BRIDGE_VALIDATION=PASS_BY_PATH_NON_INTERFERENCE_AND_ACCEPTED_PREDECESSOR_HOST_GATES
F3_SOURCE_VALIDATION=PASS
TOOLCHAIN_VERIFY=PASS
INTRODUCED_REQUIRED_ERRORS=0
F2_ACCEPTED_BROKEN_LINKS=519
F3_SUCCESSOR_BROKEN_LINKS=503
TARGETED_CHANGED_FILE_LINKS=PASS
INTRODUCED_BROKEN_LINKS=0
TOOLCHAIN_BUILD_COUNT=0
QUALIFICATION_BUILD_COUNT=0
BUILD_A_COUNT=0
BUILD_B_COUNT=0
```

Accumulated validation projects all authoritative `AIFE/staging/**` over immutable
`AIFE_review_latest.zip` (`c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0`)
and checks F0 + F1 + DATA + F1G + F2 + F3 together.

## 11. No-ETH boundary and deferred work

No F3 source imports or names Binance, Deribit, Kraken, ETHUSDT, market finality, normalization or
provider retry semantics. F4 owns Data Bridge integration. Storage migration and existing-corpus
transition remain later lifecycle checkpoints; production qualification/deployment and AEB remain
outside this task.

```text
ETH_INTEGRATION_STARTED=NO
SERVER_DOMAIN_IS_ETH_SEMANTIC_AUTHORITY=NO
SERVER_DEPLOYMENT_STARTED=NO
MIGRATION_STARTED=NO
F4_STARTED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
NEXT_CHECKPOINT=CHECKPOINT_F4_ETH_DATA_BRIDGE_INTEGRATION
```
