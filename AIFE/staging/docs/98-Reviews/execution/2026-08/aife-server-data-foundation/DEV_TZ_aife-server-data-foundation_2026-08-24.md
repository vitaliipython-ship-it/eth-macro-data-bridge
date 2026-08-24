---
id: AIFE-SERVER-DATA-DEV-TZ-2026-08-24
title: "DEV_TZ: AIFE Server / Data Foundation V1"
version: '0.1'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
category: architecture
doc_type: spec
language: ru
tags: [dev-tz, server, data, foundation, durability, publication, access, scalability]
authority_reference:
  - AGENTS.md
  - genome/registries/STANDARDS_REGISTRY.md
  - genome/registries/ADR_REGISTRY.md
  - genome/registries/CONTRACTS_REGISTRY.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/governance/STD-GOVERNANCE-NAMING-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
related:
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - genome/adr/data/ADR-DATA-FOUNDATION-001.md
---

# DEV_TZ: AIFE Server / Data Foundation V1

## Status

```text
Task-Family=AIFE_SERVER_DATA_FOUNDATION
Current-Stage=F0_STAGED_CANDIDATE_GOVERNANCE_REPAIR_BEFORE_STAGING_OWNER_INTEGRATION
Package-Role=DURABLE_OWNER_PLANNING_CANDIDATE
Execution-Allowed=NO_SERVER_IMPLEMENTATION
Physical-Use-Class=control-plane-evidence-only
Physical-Delivery-Claim=NO
Planning-Package-Result=PASS
AIFE-Delivery-Status=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
```

This DEV_TZ is sufficient to decompose later owner-approved work without chat.
It is not production authority until integrated into canonical AIFE.

## Authority and current as-built constraints

Exact source baseline:

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_WORKTREE_CLEAN=true
```

Verified current AIFE authority:

- `STD-ARCH-PATTERNS-001` `1.0.0` approved;
- `ADR-INITIALIZER-CORE-001` `1.0` is current owner decision for public runtime/DI boundary;
- `AppContext` is the sole public typed runtime surface;
- `DependencyManager` is internal bootstrap/lifecycle only;
- canonical `core/data/` topology exists: `models/`, `repositories/`, `adapters/`, `uow/`;
- Data Management standards `STD-DATA-MGMT/SCHEMA/MIGRATION/VALIDATION/RETENTION/BACKUP-001` are all `0.1.0 draft`;
- API Design/Docs/Errors/Rate/Versioning standards are all approved `1.0.0`;
- `STD-LOG-001` is approved `2.3.0`; relevant Security standards are approved;
- `STD-MON-HEALTH-001` and `STD-MON-METRICS-001` are draft `0.1.0`;
- no active database/server-data topology ADR exists;
- no active server/data Artifact Contract exists;
- `STD-GOVERNANCE-NAMING-001` `1.3.0` approved defines `CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>` grammar;
- `STD-GOVERNANCE-CONTRACT-001` `1.1.0` approved currently permits contract domains `DOC, ARCH, LOG, SEC, GOVERNANCE, API, DATA, MON, PERF, TEST, CHANGE`;
- `SERVER` is not currently an allowed canonical contract domain.

Draft data standards are terminology/risk input only. Their SQLite/MongoDB
examples do not select production databases.

## SERVER contract-domain governance dependency

Owner intent is preserved without silent semantic substitution:

```text
CANONICAL_FUTURE_CONTRACT_ID=CONTRACT-SERVER-WORK-001
KEEP_SERVER_DOMAIN_SEMANTICS=YES
RENAME_SERVER_TO_DATA=NO
RENAME_SERVER_TO_ARCH=NO
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
SERVER_DOMAIN_EXTENSION_PERFORMED_BY_F0=NO
CONTRACT_SERVER_WORK_001_FILE_CREATED_BY_F0=NO
```

`CONTRACT-SERVER-WORK-001` can be materialized **iff** `SERVER` is canonically
allowed by then-current AIFE governance. If it is still absent at the F1/F2
boundary, the executor must stop before contract creation, run a separate
owner-authorized governance extension that updates canonical AIFE naming/domain
authority, and only then resume F2. No `CONTRACT-DATA-WORK-*` or
`CONTRACT-ARCH-WORK-*` fallback is allowed.

```text
CONTRACT_SERVER_WORK_001_CAN_BE_MATERIALIZED=
IFF_SERVER_DOMAIN_IS_CANONICALLY_ALLOWED_BY_CURRENT_AIFE_GOVERNANCE

IF_SERVER_DOMAIN_NOT_ALLOWED=
STOP_BEFORE_CONTRACT_CREATION
→ SEPARATE_OWNER_GOVERNANCE_EXTENSION
→ CANONICAL_AIFE_NAMING_DOMAIN_AUTHORITY_UPDATE
→ RESUME_F2
```

## Physical Use Contract

```text
physical-use class: control-plane-evidence-only
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
USER_VALUE_PHYSICAL_DELIVERY=NOT_YET_DELIVERED
OPERATIONALIZATION=MISSING_BY_DESIGN_AT_F0
PHYSICAL_INTEGRATION_PROOF=NOT_APPLICABLE_YET
```

This artifact controls future decomposition and owner integration. It does not
claim physical delivery and cannot close F3+ without `Physical Integration
Proof`. `CONTROL_PLANE_ONLY_DELIVERY_BLOCKED` is a delivery classification, not
a failure of the F0 planning package.

## Behavior Contract

The future foundation must:

1. preserve the existing AIFE public runtime route and ownership pattern;
2. separate generic execution/storage/access mechanism from domain semantics;
3. make accepted work recoverable before volatile workers can lose ownership;
4. distinguish ingest durability from canonical publication/history durability;
5. keep workspace requests semantic, backend-neutral and node-neutral;
6. make one-server deployment possible without semantic changes for later
   multiple workers/nodes;
7. avoid adding a new mechanism unless a proven use case requires it.

## Implementation Substrate Contract

Future source work must extend, not bypass:

```text
Presentation / Workspace
→ Manager
→ Service
→ Repository or Gateway
→ Adapter
→ SERVER_BOUNDARY
→ AIFE_SERVER_ROOT
```

Exact class/interface names remain deferred to F2/F3 owner decisions.

Hard constraints:

```text
APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
DEPENDENCY_MANAGER_SECOND_PUBLIC_ROUTE=NO
SECOND_AIFE_DATA_ROUTE=NO
WORKSPACE_INTERNAL_ARCHITECTURE_MUTATION=NO
DIRECT_UI_TO_DATABASE=NO
DIRECT_UI_TO_STORAGE=NO
```

## Invariants

```text
AIFE_OWNS_GENERIC_MECHANISM=YES_CANDIDATE
DOMAIN_OWNS_SEMANTICS=YES_CANDIDATE
D8_D9_D6_NAMES_ARE_AIFE_PLATFORM_PRIMITIVES=false
PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=false
SERVER_EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false

ONE_CANONICAL_AIFE_SERVER_ROOT=YES
ONE_SERVER_ROOT_IMPLIES_ONE_MONOLITH=false
ONE_SERVER_ROOT_IMPLIES_ONE_CONTAINER=false
ONE_SERVER_ROOT_IMPLIES_ONE_DATABASE=false

HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
INITIAL_ONE_SERVER=ALLOWED
MULTI_NODE_NOW=NOT_REQUIRED
NODE_LOCAL_UNIQUE_CANONICAL_TRUTH=FORBIDDEN
```

## Question 1 — acquisition and durable storage

Required conceptual lifecycle:

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

### State classes

| State class | Meaning | May be node-local? | Loss allowed? |
| --- | --- | --- | --- |
| `VOLATILE_PROCESS_STATE` | in-memory transient execution | yes | yes before acceptance; not sole record after acceptance |
| `NODE_LOCAL_RECOVERABLE_STATE` | cache/restartable local state | yes | yes if independently rebuildable/restorable |
| `INGEST_DURABLE_STATE` | ownership/checkpoint/staging needed to retry accepted work | local or shared by implementation | no before safe publication/terminal disposition |
| `CANONICAL_PUBLISHED_STATE` | durable registered domain-owned result | not uniquely node-local | no |
| `ARCHIVAL_STATE` | sealed/immutable long-term authority when required | external/shared or independently restorable | governed by recoverability/retention |

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

### Death/replacement semantics

```text
CAN_A_WORKER_DIE_WITHOUT_DATA_LOSS=
YES_IF_ACCEPTED_WORK_HAS_STABLE_IDENTITY_AND_DURABLE_CHECKPOINT_OR_STAGING

CAN_A_NODE_BE_REPLACED_WITHOUT_CANONICAL_HISTORY_LOSS=
YES_IF_CANONICAL_HISTORY_IS_EXTERNAL_SHARED_OR_INDEPENDENTLY_RESTORABLE

CAN_STORAGE_BACKEND_CHANGE_WITHOUT_WORKSPACE_API_CHANGE=
YES_IF_SEMANTIC_IDENTITIES_PUBLICATION_IDENTITY_ACCESS_AND_PROVENANCE_REMAIN_STABLE
```

### SQL boundary

SQL-like stores may later own:

- control state;
- leases/ownership state;
- checkpoints;
- publication metadata;
- catalog/index;
- recent compact state.

They are not selected by this DEV_TZ for high-cardinality raw history.

```text
HIGH_CARDINALITY_RAW_TO_SQL_BY_DEFAULT=NO
POSTGRES_CONTROL=DEFER_UNTIL_MEASURED_OR_EXISTING_AIFE_REQUIREMENT
```

## Question 2 — extraction from proven ETH reference

Reference commits:

```text
DATA_BRIDGE=6a431edc3c834070c3c67453cf111aa757d65b8b
RESEARCH=6e2a629c91bbfdf1daf41a81583bae96ea67eb4f
```

Extraction levels:

```text
LEVEL_1_INVARIANT=safe generic property
LEVEL_2_CONTRACT_PATTERN=candidate requiring AIFE owner definition and/or second-use validation
LEVEL_3_DOMAIN_IMPLEMENTATION=remain domain owned
```

### Detailed extraction matrix

| ETH mechanism | Current owner / proof | Domain-specific input | Generic invariant | Level | Recommendation |
| --- | --- | --- | --- | --- | --- |
| D8 acquisition runtime | Data Bridge; source + VPS_SHADOW evidence | provider/capability semantics | work execution separated from semantic authority | L2 | generic ingestion runtime pattern only |
| due policy | Data Bridge; declaration-driven/fixed-grid | market cadence/provider rules | capability-owned due/eligibility policy | L2 | preserve policy slot, do not copy market schema |
| cycle/work identity | Data Bridge; stable cycles | market slot/capability | stable work identity survives retry | L1 | reuse invariant |
| lease | Data Bridge; runtime recovery | cycle/capability key | one bounded owner per work unit | L1/L2 | generic lease-equivalent contract |
| checkpoint-v2 | Data Bridge; integrity-bound | observation membership/payload | accepted work progress bound to exact input evidence | L2 | generic checkpoint pattern, new AIFE schema |
| SQLite WAL state | Data Bridge; physically exercised | D8 runtime tables | operational state is not history authority | L1 | reuse role separation, not backend choice |
| SPOOL | Data Bridge; durable PENDING/FORWARDED | observation envelopes | durable pre-publication staging | L1/L2 | generic staging concept |
| retry/recovery | Data Bridge; crash/replay semantics | provider/cycle state | retries preserve identity and do not duplicate authority | L1 | reuse invariant |
| backpressure | Data Bridge; bounded spool/publication policy | acquisition cadence | pressure must be bounded/fail-closed | L2 | define only when second use requires parameters |
| immutable identity conflict | Data Bridge; fail-closed | observation identity | same logical ID cannot silently change content | L1 | generic invariant |
| PublicationBatch | Data Bridge; deterministic | market members | logical publication identity independent of backend/attempt | L1/L2 | base for AIFE publication contract |
| HistoryPublicationPort | Data Bridge; source+physical qualified | WARM/COLD domain roles | publication through adapter + durability + readback + registration | L2 | generic publication boundary |
| backend profile | Data Bridge; `GITHUB_FIRST_V1` current | physical Git/Release choices | physical backend selected behind semantic boundary | L1/L2 | storage adapter profile |
| canonical ACK | Data Bridge; whole-batch physical proof | exact observation membership | terminal forwarding only after whole-unit durable registered ACK | L1 | reuse invariant |
| D6 resolver | Data Bridge; active | market series/finality | semantic request resolves to physical resources internally | L2 | generic semantic resolution pattern |
| ResolutionPlan | Data Bridge; active v1 | market request fields | deterministic access plan separates request from locators | L1/L2 | generic data access plan pattern |
| history reader | Data Bridge; active | market materialization | canonical reader consumes access plan, not ad-hoc paths | L2 | generic reader/materializer boundary |
| semantic receipt | Data Bridge; active | market output/provenance | result carries provenance/diagnostics | L1/L2 | merge into data access contract |

### Domain ownership

```text
ETH_PROVIDER_SEMANTICS=DOMAIN_OWNED
ETH_SERIES_ID=DOMAIN_OWNED
ETH_OBSERVATION_ID=DOMAIN_OWNED
MARKET_FINALITY=DOMAIN_OWNED
MARKET_GAP_REVISION_SEMANTICS=DOMAIN_OWNED
ETH_DATA_BRIDGE_REMAINS_MARKET_DATA_SEMANTIC_AUTHORITY=YES
SECOND_ETH_MARKET_DATA_AUTHORITY=NO
```

No ETH source is copied into AIFE.

## Architecture value gate

Every new platform primitive must record:

```text
RISK=<real proven problem>
SIMPLER_PATH=<can the current domain-owned mechanism remain until second use>
NEXT_AGENT_ACTION_REDUCTION=<does genericization reduce implementation/operation steps>
```

If evidence is absent:

```text
NEW_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
```

## Minimal Work Descriptor candidate

AIFE needs a bounded work description sufficient for horizontal ownership, not
a workflow language.

Candidate semantic slots for F2 review:

- stable work identity;
- domain;
- capability;
- work type;
- subject/partition;
- requested semantic range where applicable;
- attempt;
- due/deadline where applicable;
- input references;
- policy reference;
- correlation/trace identity.

No field is final until `CONTRACT-SERVER-WORK-001` owner review and the required
`SERVER` domain governance gate has passed.

Explicitly forbidden: universal workflow DSL and global event bus as generic
work fabric.

## Question 3 — consumer to server contract

Required properties:

```text
SEMANTIC_NOT_PHYSICAL
DOMAIN_AWARE
BACKEND_NEUTRAL
NODE_NEUTRAL
VERSIONABLE
FAIL_CLOSED
PROVENANCE_RETURNED
```

Conceptual operation families to evaluate in F2/F3:

- capability discovery;
- semantic data read;
- provenance/result read;
- work submission, only for server-executed work;
- work status, only if work submission exists;
- health.

Cancellation is `DEFER` until a real long-running use case requires it.

Transport is explicitly separate:

```text
SEMANTIC_CONTRACT != HTTP_GRPC_CLI_IPC_TRANSPORT
HTTP_SELECTED=NO
GRPC_SELECTED=NO
WEBSOCKET_SELECTED=NO
TRANSPORT_SELECTED=NO
```

If a future public transport is selected, approved AIFE API Design,
Versioning, Errors, Rate Limiting and Documentation standards apply unless an
owner-approved exception exists.

### Direct access prohibitions

```text
DIRECT_UI_TO_SQL=NO
DIRECT_UI_TO_POSTGRES=NO
DIRECT_UI_TO_MONGODB=NO
DIRECT_UI_TO_SQLITE=NO
DIRECT_UI_TO_PARQUET=NO
DIRECT_UI_TO_OBJECT_STORAGE=NO
DIRECT_UI_TO_SERVER_FILESYSTEM=NO
DIRECT_UI_TO_ETH_D6=NO
DIRECT_UI_TO_PROVIDER=NO
DIRECT_UI_TO_CONTAINER=NO
DIRECT_UI_TO_NODE_HOSTNAME=NO
```

## Data plane != control plane

`SystemControlManager` / `SysControlClient` are architectural precedent for an
external-client lifecycle only.

```text
SYSTEM_CONTROL_CLIENT_IS_FUTURE_DATA_CLIENT=NO
CONTROL_PLANE=SEPARATE_SEMANTICS
DATA_ACCESS_PLANE=SEPARATE_SEMANTICS
```

Existing `EventBus` remains application coordination mechanism. It may carry
coarse lifecycle events such as connected/disconnected/request-completed/
request-failed/health-changed, but:

```text
EVENT_BUS_IS_HIGH_VOLUME_MARKET_DATA_TRANSPORT=NO
```

## AIFE Server Root logical model

One reproducible operations root is required:

| Logical class | State class | Backup required | Horizontal implication |
| --- | --- | --- | --- |
| `deployment` | reproducible/configured | source/config only | same layout on N nodes |
| `config` | injected/versioned | yes where authoritative | node-neutral configuration |
| `services` | reproducible deployable artifacts | rebuild, not runtime backup | independent replicas allowed |
| `domains` | versioned domain registration/profile | yes | domain registration not node-bound |
| `runtime` | node-local recoverable or shared control | selective | no unique canonical history |
| `staging` | ingest durable where acceptance requires | recovery-dependent | ownership/idempotency required |
| `logs` | operational evidence | retention policy | aggregation can evolve later |
| `evidence` | durable audit/qualification evidence | yes | authoritative evidence not one-node-only |
| `backups` | restore material | yes, preferably external | sole copy cannot live with failed node |
| `scripts` | reproducible operations | source controlled | same on all nodes |
| `runbooks` | operational docs | source controlled | node-neutral |

Exact filesystem layout is deferred to F3 after owner integration.

## Horizontal scale foundation

Minimum distributed-work concepts:

```text
WORK_UNIT
PARTITION_OR_SHARD
LEASE_OR_OWNERSHIP
IDEMPOTENCY_KEY
CHECKPOINT
RETRY
TERMINAL_STATE
```

No distributed coordinator is implemented in F0-F2.

| Component | Preferred state class | Can scale to N? | Generic shard candidates | Idempotency/ownership | Durable dependency | Reference / gap |
| --- | --- | --- | --- | --- | --- | --- |
| Acquisition | stateless-horizontal + durable execution state | yes | domain/capability/source/subject/partition | work ID + lease + checkpoint | ingest state/staging | ETH proven; AIFE schema gap |
| Publication | stateless-horizontal + shared durable publication state | yes | logical publication unit/partition | publication ID + whole-unit ACK | durable backend/control metadata | ETH proven; AIFE contract gap |
| Read | stateless-horizontal | yes | semantic request/resource partition | deterministic plan/read identity | canonical storage/catalog | ETH pattern proven; AIFE API gap |
| Derivation | stateless-horizontal preferred | yes | domain/capability/subject/range | input fingerprint + version | canonical inputs/output policy | general future gap |
| Control | singleton temporary allowed initially, logically shared later | later | work namespace/domain | CAS/lease/terminal state | durable control state | AIFE owner decision needed |

Future transitions `ONE_NODE → MULTIPLE_NODES → ORCHESTRATOR` must not change
workspace request semantics, domain data identity, publication identity,
storage semantic identity or provenance meaning.

## Domain profile boundary

A future bounded domain profile may declare:

- `domain_id`;
- capabilities;
- provider/source adapters;
- normalization/identity/validation semantics;
- requested storage semantics/class;
- reader/materializer integration;
- provenance rules.

```text
DOMAIN_REQUESTS_STORAGE_SEMANTICS=YES
DOMAIN_SELECTS_BUCKET_OR_PATH=NO
DOMAIN_SELECTS_SERVER_NODE=NO
```

Physical backend selection remains platform/storage-policy owned.

## Data class / storage-role separation

```text
OPERATIONAL_RUNTIME_STATE
!= CANONICAL_PUBLISHED_DATA
!= ARCHIVAL_DATA
!= DOMAIN_ANALYTICAL_HISTORY
!= REBUILDABLE_CACHE
```

Object/Blob + Parquet is not AIFE-wide storage. It is retained only as the
current owner-approved Research direction for future ETH high-cardinality P2.

```text
OBJECT_PARQUET_SELECTED_AS_AIFE_UNIVERSAL_STORAGE=NO
ETH_P2_APPROVED_RESEARCH_DIRECTION_NOT_IMPLEMENTED=YES
```

## Existing history and analytical semantics

No migration is prerequisite:

```text
ETH_EXISTING_GITHUB_RELEASE_HISTORY_MIGRATION_NOW=NO
ETH_EXISTING_GIT_HOT_DATA_MIGRATION_NOW=NO
RESEARCH_WAVE_HISTORY_MIGRATION_NOW=NO
LEGACY_READABILITY_MUST_BE_PRESERVED=YES
```

Generic history may support `identity`, `effective_at`, `known_at`, `version`,
`provenance`, `append`, `supersede`, `audit`. Domain owns interpretation.

```text
WAVE_PUBLISHED_STATE_MUST_PERSIST=YES
WAVE_PRIMARY_HISTORY_MUST_PERSIST=YES
WAVE_ALTERNATIVE_HISTORY_MUST_PERSIST=YES
WAVE_PREDECESSOR_OVERWRITE=FORBIDDEN
AIFE_PLATFORM_NEEDS_TO_UNDERSTAND_ELLIOTT_WAVE_SEMANTICS=NO
```

## Security / secret boundary

Never combine provider, storage, server-control and workspace credentials into
one universal secret.

```text
PROVIDER_CREDENTIALS
!= STORAGE_CREDENTIALS
!= SERVER_CONTROL_CREDENTIALS
!= WORKSPACE_AUTHENTICATION
```

Workspace consumption must not require provider/storage secrets. Future
implementation follows approved security/secrets standards.

## Observability foundation

Minimum generic signals to define in F2/F3 without choosing a vendor:

- health;
- worker status;
- staging/spool pressure;
- last success/failure;
- retry count;
- checkpoint state;
- publication status;
- storage readback status;
- consumer request diagnostics.

`STD-MON-HEALTH-001` and `STD-MON-METRICS-001` are draft; they are terminology
input, not a binding observability technology selection.

## Recovery / operations foundation

Future `AIFE_SERVER_ROOT` operational actions:

```text
STATUS
HEALTH
LOGS
START
STOP
BACKUP
RESTORE
VALIDATE
UPGRADE
ROLLBACK
```

Each action must later define touched canonical state and durable evidence.
F0 does not implement commands.

## Failure-domain requirements

The design must prevent:

```text
ONE_FAILED_PROVIDER_STOPS_ALL_DOMAINS
ONE_FAILED_WORKER_LOSES_CANONICAL_DATA
ONE_NODE_FAILURE_DESTROYS_HISTORY
ONE_BAD_PUBLICATION_PARTIALLY_ACKS_BATCH
ONE_WORKSPACE_CAN_BYPASS_DATA_AUTHORITY
```

Expected isolation dimensions: domain, capability, source/provider, work unit,
partition, publication unit and consumer request.

## Minimum Artifact Contract inventory

Only three owner Artifact Contracts are proposed before F3:

1. `CONTRACT-SERVER-WORK-001` — merges capability + Work Descriptor +
   ingest durable ownership/checkpoint/retry/terminal-state binding.
2. `CONTRACT-DATA-PUBLICATION-001` — logical publication unit + storage adapter
   + durability/readback/registration + whole-unit ACK.
3. `CONTRACT-DATA-ACCESS-001` — semantic request + access plan +
   reader/materializer + provenance receipt.

`CONTRACT-SERVER-WORK-001` has special governance state:

```text
STATUS=PLANNED_CANONICAL_ID_PENDING_SERVER_DOMAIN_GOVERNANCE_EXTENSION
DOMAIN=SERVER
DOMAIN_STATUS=NOT_YET_CANONICALLY_REGISTERED
PRECONDITION=SERVER_DOMAIN_OWNER_GOVERNANCE_PASS
CREATION_ALLOWED_NOW=NO
```

Classification:

| Candidate | Decision |
| --- | --- |
| AIFE Server Capability Contract | `MERGE_WITH_OTHER_CONTRACT` |
| AIFE Work Descriptor Contract | `REQUIRED_BEFORE_F3` |
| AIFE Durability State Contract | `MERGE_WITH_OTHER_CONTRACT` |
| AIFE Publication Contract | `REQUIRED_BEFORE_F3` |
| AIFE Data Access Contract | `REQUIRED_BEFORE_F3` |
| AIFE Provenance Receipt Contract | `MERGE_WITH_OTHER_CONTRACT` |

No Artifact Contract is created by this DEV_TZ. F2 must revalidate whether the
named binding relationship is sufficiently concrete before materializing each
contract; if not, keep it as Runtime/Task Contract rather than creating a
`CONTRACT-*` artifact. For `CONTRACT-SERVER-WORK-001`, that review occurs only
after `SERVER_DOMAIN_OWNER_GOVERNANCE_PASS`.

## Future workspace acceptance roles

Do not execute in F0:

- consumer discovery test;
- semantic read test;
- work submission test if F3 exposes work submission;
- provenance receipt test;
- fail-closed test;
- backend substitution test;
- node restart test;
- second-worker ownership/idempotency test.

Workspaces are acceptance consumers, not second authorities.

## Traceability matrix

| Requirement | Source class | Source ID | Version/SHA | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Manager/Service/Repository ownership | EXISTING_AIFE_AUTHORITY | `STD-ARCH-PATTERNS-001` | `1.0.0` | approved | reusable mandatory AIFE pattern |
| AppContext sole public runtime route | EXISTING_AIFE_AUTHORITY | `ADR-INITIALIZER-CORE-001` | `1.0` | current owner decision | DependencyManager remains internal |
| canonical `core/data` topology | EXISTING_AIFE_AUTHORITY | `STD-ARCH-PATTERNS-001` | `1.0.0` | approved | models/repositories/adapters/uow |
| Contract ID grammar | EXISTING_AIFE_AUTHORITY | `STD-GOVERNANCE-NAMING-001` | `1.3.0` | approved | `CONTRACT-<DOMAIN>-<QUALIFIER>-<NNN>` |
| Current contract domain vocabulary | EXISTING_AIFE_AUTHORITY | `STD-GOVERNANCE-CONTRACT-001` | `1.1.0` | approved | `SERVER` absent; separate owner governance extension required before `CONTRACT-SERVER-WORK-001` |
| Data schema/migration/validation/retention/backup terms | EXISTING_AIFE_AUTHORITY | `STD-DATA-*` suite | `0.1.0` | draft | terminology/risk input, no production technology choice |
| API public-interface governance | EXISTING_AIFE_AUTHORITY | `STD-API-*` suite | `1.0.0` | approved | applies if public API transport is later chosen |
| security/secrets/logging | EXISTING_AIFE_AUTHORITY | `STD-SEC-*`, `STD-LOG-001` | approved versions | approved | no secret unification |
| work identity/lease/checkpoint/retry reference | ETH_PROVEN_REFERENCE_EVIDENCE | Data Bridge D8 contracts | `6a431edc3c834070c3c67453cf111aa757d65b8b` | reference | evidence, not AIFE owner authority |
| PublicationBatch/Port/ACK/readback reference | ETH_PROVEN_REFERENCE_EVIDENCE | Data Bridge forwarding/storage portability | `6a431edc3c834070c3c67453cf111aa757d65b8b` | source+physical qualified | evidence, not AIFE naming |
| semantic resolver/access-plan/reader/receipt reference | ETH_PROVEN_REFERENCE_EVIDENCE | Data Bridge D6 route | `6a431edc3c834070c3c67453cf111aa757d65b8b` | active reference | preserve semantic-not-physical principle |
| P2 Object/Parquet direction | ETH_PROVEN_REFERENCE_EVIDENCE | Unified History/PIT/Backtest SSOT | `6e2a629c91bbfdf1daf41a81583bae96ea67eb4f` | approved Research direction, not implemented | not universal AIFE storage |
| one canonical AIFE server operations root | NEW_AIFE_OWNER_DECISION_CANDIDATE | `ADR-DATA-FOUNDATION-001` | `1.0 proposed` | candidate | owner integration required |
| horizontal scaling by design | NEW_AIFE_OWNER_DECISION_CANDIDATE | `ADR-DATA-FOUNDATION-001` | `1.0 proposed` | candidate | multi-node implementation deferred |
| exact physical server-root layout | DEFERRED | F3 | n/a | deferred | only after ADR/contracts owner integration |
| database vendor | DEFERRED | technology selection | n/a | deferred | measured need / owner decision required |
| transport technology | DEFERRED | transport decision | n/a | deferred | semantic contract first |

## Contract-first decomposition

### F0 — durable planning and owner handoff

F0 completes only after two separate owner-integration phases:

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222
→ owner final review
→ merge into eth-macro-data-bridge/main
→ post-merge readback of durable AIFE/** carrier

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged carrier
→ verify then-current AIFE base
→ verify candidate hashes
→ exact-byte apply to AIFE target paths
→ update real AIFE registry
→ canonical AIFE validation
→ AIFE owner integration

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

Neither phase starts F2 or F3.

### F1 — Server/Data Foundation owner architecture

**Behavior Contract:** currentize the integrated Program Map, DEV_TZ and
`ADR-DATA-FOUNDATION-001` as canonical AIFE architecture authority after F0
owner integrations.

**Invariants:** no source runtime implementation; no DB/transport selection;
no semantic rewrite of staged candidate bytes unless owner explicitly reviews
a repair.

**Proof Plan:** verify then-current AIFE HEAD/TREE, candidate SHA-256, target
paths, registry row, metadata, links and canonical validation.

**Acceptance Criteria:** owner artifact bytes integrated, ADR registry synced,
validation PASS, no hidden second authority.

### F1G — SERVER contract-domain owner governance gate

If `SERVER` remains absent from then-current canonical AIFE contract domain
vocabulary after F1, execute a separate owner-authorized governance extension
before F2. F1G may update canonical naming/domain authority through its own
scope; this DEV_TZ does not perform that change.

**Acceptance Criteria:** `SERVER_DOMAIN_OWNER_GOVERNANCE_PASS` is demonstrably
true before `CONTRACT-SERVER-WORK-001` creation or registration.

### F2 — Minimum server/data contracts

**Behavior Contract:** define only the minimum named bindings that reduce
ambiguity before source skeleton.

**Implementation Substrate Contract:** no runtime code; contracts route through
`CONTRACTS_REGISTRY.md`.

**Invariants:** maximum initial set = three planned contracts above; each must
pass the architecture value gate; `CONTRACT-SERVER-WORK-001` remains blocked
until F1G passes when required.

**Proof Plan:** registry-first review + metadata/naming validation + cross-file
consistency.

**Acceptance Criteria:** sufficient named boundaries exist for F3, with no
database or transport decision.

### F3 — server-root source skeleton

Must be separately authorized after F2. It may create reproducible source/
operations structure and minimal interfaces, but cannot self-authorize
production deployment.

## Proof Plan for this planning package

F0 qualification must prove:

- exact AIFE review package SHA, HEAD, TREE and clean status;
- authority-first reading of registries and relevant owner artifacts;
- AIFE-native target paths known;
- metadata status/type consistency;
- `SERVER` contract-domain dependency recorded without silently renaming the intended contract;
- no copied registry/standard/ETH source;
- no DB or transport selection;
- no runtime/server/storage mutation;
- hashes recorded for exact staged owner candidates;
- staging-only repository scope `AIFE/**`;
- Data Bridge canonical validation applicable to docs/JSON remains green;
- PR contains only `AIFE/**`;
- F0 delivery is classified as control-plane-only, not physical implementation;
- two-stage owner handoff is explicit.

## Acceptance Criteria

```text
AIFE_REVIEW_PACKAGE_SHA256=PASS
AIFE_HEAD_TREE=PASS
AIFE_AUTHORITY_ROUTE_READ=PASS
PROGRAM_MAP_EXISTS=PASS
DEV_TZ_EXISTS=PASS
FOUNDATION_ADR_CANDIDATE_EXISTS=PASS
AUTHORITY_BINDING_EXISTS=PASS
INTEGRATION_MANIFEST_EXISTS=PASS
ALL_OWNER_CANDIDATE_TARGET_PATHS_KNOWN=PASS
ALL_OWNER_CANDIDATE_TARGET_REGISTRIES_KNOWN_OR_NOT_APPLICABLE=PASS
SERVER_DOMAIN_CURRENTLY_REGISTERED=NO
SERVER_DOMAIN_GOVERNANCE_EXTENSION_REQUIRED=YES
CONTRACT_SERVER_WORK_FILE_CREATED=NO
PLANNING_PACKAGE_RESULT=PASS
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
PHYSICAL_DELIVERY=NO
NO_SECOND_AIFE_REGISTRY=PASS
NO_STANDARD_FORK=PASS
NO_ETH_SOURCE_FORK=PASS
NO_DATABASE_VENDOR_SELECTED=PASS
NO_TRANSPORT_SELECTED=PASS
NO_SERVER_IMPLEMENTATION=PASS
HORIZONTAL_SCALING_BY_DESIGN=PASS
```

## Deferred technology

Deferred by default until measured need / owner decision:

- universal plugin manager;
- generic provider factory for everything;
- universal workflow DSL;
- global high-volume event bus;
- service mesh;
- Kubernetes;
- Kafka;
- Redis;
- ClickHouse;
- TimescaleDB;
- Iceberg;
- Delta Lake;
- vector DB;
- feature store;
- one giant all-domain database.

## Stop boundary

After repaired F0 staging PR and readback:

```text
SERVER_IMPLEMENTATION=NO
AIFE_WORKSPACE_MUTATION=NO
DATABASE_CREATION=NO
CONTAINER_DEPLOYMENT=NO
OBJECT_STORAGE_CREATION=NO
P2_IMPLEMENTATION=NO
R2_RESUME=NO
```

Next owner-task sequence only:

```text
NEXT_RECOMMENDED_TASK=AIFE-SERVER-DATA-FOUNDATION-STAGING-OWNER-INTEGRATION-V1
FOLLOWING_TASK=AIFE-SERVER-DATA-FOUNDATION-AIFE-OWNER-INTEGRATION-V1
```

After those owner integrations: F1 architecture authority currentization → F1G
`SERVER` domain governance extension if still required → F2 minimum contracts →
F3 server-root source skeleton.
