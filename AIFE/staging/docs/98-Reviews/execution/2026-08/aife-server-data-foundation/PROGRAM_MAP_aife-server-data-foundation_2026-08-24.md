---
id: AIFE-SERVER-DATA-PROGRAM-MAP-2026-08-24
title: "PROGRAM_MAP: AIFE Server/Data Foundation"
version: '0.1'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
category: architecture
doc_type: spec
language: ru
tags: [program-map, execution, server, data, foundation, scalability]
authority_reference:
  - AGENTS.md
  - genome/registries/STANDARDS_REGISTRY.md
  - genome/registries/ADR_REGISTRY.md
  - genome/registries/CONTRACTS_REGISTRY.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/governance/STD-GOVERNANCE-NAMING-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
---

# PROGRAM_MAP: AIFE Server/Data Foundation

## Program Identity

| Поле | Значение |
| --- | --- |
| Program | `AIFE_SERVER_DATA_FOUNDATION` |
| Scope-Slug | `aife-server-data-foundation` |
| Program-Type | `foundation-program` |
| Primary Goal | `MINIMAL_SCALABLE_AIFE_SERVER_SIDE_FOUNDATION` |
| Workspace Role | `TEST_AND_REAL_CONSUMER` |
| ETH Role | `FIRST_PROVING_DOMAIN` |
| Execution Root | `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/` |
| Current Gate | `F0_BRIDGE_AND_DURABLE_PLANNING_AUTHORITY_PENDING_STAGING_OWNER_INTEGRATION` |
| Physical Use Class | `control-plane-evidence-only` |
| Delivery Claim | `CONTROL_PLANE_ONLY_DELIVERY_BLOCKED` |

## Authority baseline

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_WORKTREE_CLEAN=true

STD_ARCH_PATTERNS_001=APPROVED_1_0_0
APP_CONTEXT_IS_SOLE_PUBLIC_RUNTIME_SURFACE=YES
DEPENDENCY_MANAGER_IS_INTERNAL_ONLY=YES
CORE_DATA_SUBSTRATE_EXISTS=YES
CORE_DATA_AREAS=models,repositories,adapters,uow

CONCRETE_DATABASE_OWNER_SELECTED=NO
ACTIVE_DATABASE_TOPOLOGY_ADR_EXISTS=NO
ACTIVE_SERVER_DATA_ARTIFACT_CONTRACT_EXISTS=NO

DATA_MANAGEMENT_STANDARDS_STATUS=DRAFT_0_1_0
API_STANDARD_SUITE_STATUS=APPROVED_1_0_0
LOGGING_STANDARD_STATUS=STD_LOG_001_APPROVED_2_3_0
SECURITY_STANDARDS_RELEVANT_STATUS=APPROVED
MON_HEALTH_METRICS_STATUS=DRAFT_0_1_0

CONTRACT_NAMING_STANDARD=STD-GOVERNANCE-NAMING-001_1.3.0_APPROVED
CONTRACT_AUTHORING_STANDARD=STD-GOVERNANCE-CONTRACT-001_1.1.0_APPROVED
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED_BY_F0=NO
```

Current canonical contract domain list in `STD-GOVERNANCE-CONTRACT-001` is
`DOC, ARCH, LOG, SEC, GOVERNANCE, API, DATA, MON, PERF, TEST, CHANGE`; `SERVER`
is absent. The intended future canonical ID `CONTRACT-SERVER-WORK-001` is
therefore preserved as owner intent but cannot be created or registered until a
separate owner-governance change admits `SERVER` into current AIFE contract
domain authority.

Data-management draft standards supply terminology/risk seams for schema,
migration, validation, retention and backup. Their SQLite/MongoDB examples are
**not** a production technology decision.

## Architectural baseline

Approved AIFE architecture constrains the future server integration:

```text
Presentation
→ Manager
→ Service
→ Repository/Gateway
→ Adapter
→ SERVER_BOUNDARY
→ AIFE_SERVER_ROOT
→ generic server mechanisms
→ domain integration
→ domain authority
```

`STD-ARCH-PATTERNS-001` remains authoritative for Manager/Service/Repository
ownership. `ADR-INITIALIZER-CORE-001` preserves `AppContext` as sole public
typed runtime surface and `DependencyManager` as internal bootstrap/lifecycle
registry.

```text
SECOND_AIFE_DATA_ROUTE=FORBIDDEN
SECOND_PUBLIC_DI_ROUTE=FORBIDDEN
WORKSPACE_INTERNAL_ARCHITECTURE_REWRITE_REQUIRED=NO
```

## Three primary questions

```text
QUESTION_1=HOW_DATA_IS_ACQUIRED_AND_DURABLY_STORED

QUESTION_2=HOW_PROVEN_ETH_D8_D9_D6_MECHANISMS_ARE_REUSED_AS_REFERENCE_WITHOUT_BECOMING_AIFE_PLATFORM_PRIMITIVES

QUESTION_3=HOW_AIFE_CONSUMERS_CONNECT_TO_AIFE_SERVER_ROOT_THROUGH_EXISTING_AIFE_ARCHITECTURAL_BOUNDARIES_WITH_HORIZONTAL_SCALE_BY_DESIGN
```

## Foundation decisions held by this candidate program

```text
AIFE_OWNS=GENERIC_EXECUTION_MECHANISMS+GENERIC_DURABLE_STATE_AND_RECOVERY+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_ABSTRACTION+GENERIC_DATA_ACCESS_INTERFACE+GENERIC_SERVER_OPERATIONS_FOUNDATION

DOMAIN_OWNS=DOMAIN_IDENTITIES+SOURCE_PROVIDER_SEMANTICS+NORMALIZATION_RULES+DOMAIN_FINALITY+DOMAIN_VALIDATION+DOMAIN_SPECIFIC_DERIVATIONS_AND_INTERPRETATION

ONE_CANONICAL_AIFE_SERVER_ROOT=YES
AIFE_SERVER_ROOT_IS_SEMANTIC_AUTHORITY=false
ONE_MONOLITH=NO
ONE_CONTAINER=NO
ONE_DATABASE=NO
HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
MULTI_NODE_IMPLEMENTATION_NOW=NO
INITIAL_ONE_SERVER=ALLOWED
FOUNDATION_FIRST=YES
BUILD_EVERYTHING_NOW=NO
```

## Ordered stages

| Stage | Name | Status | Dependency | Exit meaning |
| --- | --- | --- | --- | --- |
| F0 | `BRIDGE_AND_DURABLE_PLANNING_AUTHORITY` | `CURRENT / CANDIDATE_STAGED` | exact AIFE review package | Program Map + DEV_TZ + foundation ADR candidate + bridge binding |
| F1 | `SERVER_DATA_FOUNDATION_OWNER_ARCHITECTURE` | `NEXT_AFTER_TWO_STAGE_F0_OWNER_INTEGRATION` | staging owner integration + canonical AIFE owner integration | owner-approved architecture/ADR and exact current program route |
| F1G | `SERVER_CONTRACT_DOMAIN_OWNER_GOVERNANCE_GATE` | `BLOCKED / REQUIRED_IF_SERVER_STILL_UNREGISTERED` | F1 | canonical `SERVER` domain is owner-approved before `CONTRACT-SERVER-WORK-001` creation/registration |
| F2 | `MINIMUM_SERVER_DATA_CONTRACTS` | `BLOCKED` | F1 + F1G when required | minimum versioned semantic/runtime binding contracts, no technology selection |
| F3 | `AIFE_SERVER_ROOT_SOURCE_SKELETON` | `BLOCKED` | F2 | one reproducible operations root + bounded source skeleton, no production activation |
| F4 | `FIRST_DOMAIN_INTEGRATION_ETH` | `BLOCKED` | F3 | ETH as first proving domain without changing ETH semantic authority |
| F5 | `ETH_HIGH_CARDINALITY_P2_PHYSICAL_LIFECYCLE` | `BLOCKED` | F4 + separate ETH P2 authority | Object/Parquet may be implemented for ETH P2 only if owner-authorized |
| F6 | `AIFE_CONSUMER_INTEGRATION_AND_ACCEPTANCE` | `BLOCKED` | F4/F5 as required by use case | workspace consumes semantic contract, never physical storage |
| F7 | `PHYSICAL_AND_HORIZONTAL_SCALING_QUALIFICATION` | `BLOCKED` | F3-F6 | restart, second-worker, backend substitution and isolation proofs |
| F8 | `LATER_PRODUCTION_ACTIVATION_OR_CUTOVER` | `DEFERRED` | explicit owner gate after F7 | production authority transition, if separately authorized |

Stage names may be owner-refined only by explicit AIFE review; dependency order
must not silently change. `F1G` is a bounded governance sub-gate rather than a
program renumbering: `F1 → F1G (if required) → F2 → F3`.

## F0 owner handoff sequence

F0 has two distinct owner integrations and an open PR branch is not the durable
AIFE handoff authority:

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222
→ owner final review
→ owner merge into eth-macro-data-bridge/main
→ post-merge readback of durable AIFE/** carrier

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged durable bridge carrier
→ verify then-current AIFE workspace base
→ verify staged candidate hashes
→ exact-byte apply to canonical AIFE target paths
→ update real AIFE registry
→ run canonical AIFE validation
→ owner integration in AIFE

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

No F2 contract materialization starts in Phase A or Phase B.

## Question 1 — target lifecycle

```text
SOURCE
→ ACQUIRE
→ DOMAIN_NORMALIZE
→ DOMAIN_VALIDATE
→ INGEST_DURABLE
→ STAGE_OR_SPOOL
→ LOGICAL_PUBLICATION_UNIT
→ PUBLICATION_BOUNDARY
→ STORAGE_ADAPTER
→ DURABLE_BACKEND
→ INDEPENDENT_READBACK
→ CANONICAL_REGISTRATION
→ CANONICAL_ACK
→ SEMANTIC_ACCESS
```

Hard split:

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

A worker may die without accepted-data loss only after accepted work/input is
represented in durable recoverable state with stable identity. A node may be
replaced without canonical-history loss only when canonical history is
external/shared durable authority or can be restored from independent durable
authority. One node-local directory may never be the unique canonical truth.

## Question 2 — ETH reference, not platform ontology

Reference evidence is pinned to:

```text
DATA_BRIDGE_REFERENCE_COMMIT=6a431edc3c834070c3c67453cf111aa757d65b8b
RESEARCH_REFERENCE_COMMIT=6e2a629c91bbfdf1daf41a81583bae96ea67eb4f
D8_D9_D6_NAMES_ARE_AIFE_PLATFORM_PRIMITIVES=false
ETH_DATA_BRIDGE_REMAINS_MARKET_DATA_SEMANTIC_AUTHORITY=true
```

Reusable reference properties:

- stable work identity;
- lease/work ownership;
- checkpoint;
- durable pre-publication state;
- retry/recovery/backpressure;
- idempotency;
- deterministic storage-independent publication identity;
- whole-unit canonical ACK;
- independent readback;
- storage adapter/profile;
- semantic resolution;
- deterministic access plan;
- canonical reader;
- semantic/provenance receipt.

ETH-owned semantics remain ETH-owned: provider semantics, `series_id`,
`observation_id`, market finality, market gap/revision/provenance rules.

## Question 3 — consumer boundary and scale

Consumers remain on the existing AIFE architecture path and request semantics,
not storage:

```text
Presentation
→ Manager
→ Service
→ Repository/Gateway
→ Adapter
→ stable AIFE server semantic contract
→ domain capability
```

Forbidden:

```text
DIRECT_UI_TO_DATABASE=YES_FORBIDDEN
DIRECT_UI_TO_SERVER_FILESYSTEM=YES_FORBIDDEN
DIRECT_UI_TO_OBJECT_STORAGE=YES_FORBIDDEN
DIRECT_UI_TO_PARQUET_PATH=YES_FORBIDDEN
DIRECT_UI_TO_ETH_D6=YES_FORBIDDEN
DIRECT_UI_TO_PROVIDER=YES_FORBIDDEN
CONSUMER_SELECTS_NODE_HOSTNAME=NO
CONSUMER_SELECTS_CONTAINER=NO
```

Scale target is `WORKER_COUNT=1..N` across valid dimensions such as domain,
capability, source/provider, subject/partition, time range and work type.
Node-local unique canonical state is forbidden.

## AIFE server root role

One canonical operational/deployment root is required for reproducibility:

```text
deployment/
config/
services/
domains/
runtime/
staging/
logs/
evidence/
backups/
scripts/
runbooks/
```

This is a logical class model only. Exact filesystem names are not authorized
until the later source task after owner-approved architecture.

## Minimum pre-F3 Artifact Contract inventory

AIFE `Artifact Contract` is a named binding artifact, not a synonym for every
runtime schema. Contract proliferation is explicitly rejected.

| Conceptual candidate | Decision | Planned canonical owner artifact | Rationale |
| --- | --- | --- | --- |
| AIFE Server Capability Contract | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-SERVER-WORK-001` | capability identity/eligibility belongs in the bounded work boundary; separate contract adds no second-use value yet |
| AIFE Work Descriptor Contract | `REQUIRED_BEFORE_F3` | `CONTRACT-SERVER-WORK-001` | binds semantic work identity, ownership/lease-equivalent, checkpoint/retry/terminal state and capability reference |
| AIFE Durability State Contract | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-SERVER-WORK-001` + `CONTRACT-DATA-PUBLICATION-001` | ingest durability and publication durability are distinct but do not justify a third standalone Artifact Contract |
| AIFE Publication Contract | `REQUIRED_BEFORE_F3` | `CONTRACT-DATA-PUBLICATION-001` | binds logical publication identity, storage adapter, durable readback, registration and whole-unit ACK |
| AIFE Data Access Contract | `REQUIRED_BEFORE_F3` | `CONTRACT-DATA-ACCESS-001` | binds semantic request, resolution/access plan, canonical reader/materializer and fail-closed result |
| AIFE Provenance Receipt Contract | `MERGE_WITH_OTHER_CONTRACT` | `CONTRACT-DATA-ACCESS-001` | provenance receipt is inseparable from the semantic read/result boundary at first use |

Exact target registry for all three future Artifact Contracts:
`genome/registries/CONTRACTS_REGISTRY.md`.

`CONTRACT-SERVER-WORK-001` is an intended future canonical ID with `DOMAIN=SERVER`.
Its current state is:

```text
STATUS=PLANNED_CANONICAL_ID_PENDING_SERVER_DOMAIN_GOVERNANCE_EXTENSION
DOMAIN=SERVER
DOMAIN_STATUS=NOT_YET_CANONICALLY_REGISTERED
PRECONDITION=SERVER_DOMAIN_OWNER_GOVERNANCE_PASS
CONTRACT_SERVER_WORK_001_FILE_CREATED_BY_F0=NO
```

No contract file is created by F0.

## Technology decision boundary

```text
DATABASE_VENDOR_SELECTED=NO
POSTGRES_SELECTED=NO
MONGODB_SELECTED=NO
SQLITE_SELECTED_AS_CANONICAL_SERVER_DATABASE=NO
OBJECT_PARQUET_SELECTED_AS_AIFE_UNIVERSAL_STORAGE=NO
HIGH_CARDINALITY_RAW_TO_SQL_BY_DEFAULT=NO
TRANSPORT_SELECTED=NO
HTTP_SELECTED=NO
GRPC_SELECTED=NO
WEBSOCKET_SELECTED=NO
```

`OBJECT_BLOB_PLUS_PARQUET` is retained only as
`ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED`.

## Existing history boundary

```text
ETH_EXISTING_GITHUB_RELEASE_HISTORY_MIGRATION_NOW=NO
ETH_EXISTING_GIT_HOT_DATA_MIGRATION_NOW=NO
RESEARCH_WAVE_HISTORY_MIGRATION_NOW=NO
LEGACY_READABILITY_MUST_BE_PRESERVED=YES
```

Generic mechanisms may preserve identity/effective_at/known_at/version/
provenance/append/supersede/audit. AIFE does not need Elliott Wave semantics.

## Current ETH reference memory

At the reference boundary:

- D8 acquisition/runtime, lease/checkpoint/retry/recovery and SPOOL are proven;
- SQLite WAL is operational runtime state, not history authority;
- deterministic PublicationBatch + Publication Port + durability/readback +
  whole-batch canonical ACK are source/physical qualified;
- active semantic access remains resolver → ResolutionPlan v1 → reader;
- current physical profile uses bounded Git WARM + immutable GitHub Release
  COLD, without making Git semantic authority;
- P2 backend is not active;
- ETH R2 remains blocked on separate P2 lifecycle authority.

Corrected measured `data/**` provenance:

```text
DATA_BINANCE_PROVIDER_FILES=2848216_BYTES
DATA_KRAKEN_PROVIDER_FILES=91104_BYTES
DATA_PROVIDER_FILES_TOTAL=2939320_BYTES
DATA_MANIFEST=13251_BYTES
DATA_ROOT_TOTAL=2952571_BYTES

GIT_TREE_WRITES_CURRENT_NORMALIZED_AND_BOUNDED_HISTORY=YES
GIT_TREE_WRITES_HIGH_CARDINALITY_RAW_P2=NO_CURRENTLY
```

## Overengineering gate

```text
FOUNDATION_FIRST=true
EXTRACTION_BY_PROVEN_USE_CASE=true
NEW_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
```

Deferred by default: universal plugin manager, universal workflow DSL, global
event bus as data plane, service mesh, Kubernetes, Kafka, Redis, ClickHouse,
Timescale, Iceberg, Delta Lake, vector DB, feature store and one giant
all-domain database.

## Non-goals

F0 does not implement server runtime, mutate `AppContext`, mutate `core/data`,
select a database or transport, deploy containers, create storage, implement
ETH P2, resume ETH R2, migrate legacy history or activate production.

## Delivery classification

```text
PLANNING_PACKAGE_RESULT=PASS
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
USER_VALUE_PHYSICAL_DELIVERY=NOT_YET_DELIVERED
OPERATIONALIZATION=MISSING_BY_DESIGN_AT_F0
PHYSICAL_INTEGRATION_PROOF=NOT_APPLICABLE_YET
SERVER_IMPLEMENTATION=NO
PHYSICAL_DELIVERY=NO
```

This is not a planning-task failure. F0 delivers durable control-plane planning
and owner-integration bytes only; server/user-facing physical value belongs to
later authorized implementation/qualification stages.

## Next gates

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```

The next task owner-reviews the repaired PR #222, merges it into staging
repository `main` if all gates pass, performs post-merge readback, and stops.
Only the following task may consume that merged durable carrier, verify the
then-current AIFE workspace base, exact-byte apply Program Map + DEV_TZ + ADR,
update the real ADR registry, run canonical AIFE validation and stop.

After canonical AIFE integration the order is:

```text
F1 architecture authority currentization
→ F1G SERVER domain governance extension if still required
→ F2 minimum contracts
→ F3 server-root source skeleton
```

Neither owner-integration task starts F2/F3.
