---
id: ADR-DATA-FOUNDATION-001
title: "ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root"
version: '1.0'
status: proposed
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-24
category: architecture
doc_type: adr
language: ru
tags: [server, data, foundation, appcontext, storage, scalability]
related:
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/adr/initializer/ADR-INITIALIZER-CORE-001.md
  - genome/adr/comm/ADR-COMM-BUS-001.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_2026-08-24.md
---

# ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root

## Статус

**Предложено**. Этот ADR является owner-candidate и не становится canonical
AIFE authority до интеграции exact bytes в `genome/adr/data/ADR-DATA-FOUNDATION-001.md` и
регистрации owner-ом в `genome/registries/ADR_REGISTRY.md`.

## Контекст

AIFE уже имеет approved architectural pattern для `Manager → Service →
Repository`, существующий `core/data/{models,repositories,adapters,uow}` и
binding owner decision, по которому `AppContext` — единственная публичная
typed runtime surface, а `DependencyManager` — internal bootstrap/lifecycle
registry.

При этом current owner route не содержит активного Data Server ADR,
server/data Artifact Contract или owner-selected database topology. Data
Management standards `0.1.0` остаются draft; их technology examples не являются
production selection.

ETH Market Data предоставляет физически и source-level доказанную reference
implementation для work identity, lease/checkpoint/recovery, durable staging,
deterministic publication, independent readback, whole-unit ACK, storage
portability и semantic resolver/access-plan/reader route. Эти механизмы являются
evidence; названия D8/D9/D6 и market semantics не должны становиться AIFE
platform ontology.

## Решение

Принять foundation-level decisions:

```text
ONE_AIFE_SERVER_FOUNDATION=YES
ONE_CANONICAL_AIFE_SERVER_OPERATIONS_ROOT=YES
ONE_PHYSICAL_DATABASE_REQUIRED=NO
PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
SERVER_EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=NO
DOMAIN_SEMANTICS_REMAIN_DOMAIN_OWNED=YES

WORKSPACE_INTERNAL_ARCHITECTURE_REWRITE_REQUIRED=NO
EXISTING_AIFE_MANAGER_SERVICE_REPOSITORY_DATA_PATTERN_REUSED=YES
APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
SECOND_PUBLIC_DI_ROUTE=NO
SECOND_AIFE_DATA_ROUTE=NO

DIRECT_CONSUMER_STORAGE_ACCESS=NO
HORIZONTAL_SCALING_BY_DESIGN=YES
MULTI_NODE_IMPLEMENTATION_NOW_REQUIRED=NO

ETH_D8_D9_D6_ARE_AIFE_PRIMITIVES=NO
ETH_IS_FIRST_PROVING_DOMAIN=YES
```

### Canonical server operations root

AIFE должен иметь один canonical operational/deployment root для reproducible
server-side runtime.

Logical classes:

```text
deployment
config
services
domains
runtime
staging
logs
evidence
backups
scripts
runbooks
```

Эти имена задают logical classes, а не финальный filesystem layout. F3 может
уточнить exact paths после owner integration и minimum contracts.

```text
AIFE_SERVER_ROOT_IS_SEMANTIC_AUTHORITY=false
ONE_SERVER_ROOT_IMPLIES_ONE_MONOLITH=false
ONE_SERVER_ROOT_IMPLIES_ONE_CONTAINER=false
ONE_SERVER_ROOT_IMPLIES_ONE_DATABASE=false
```

Unique canonical high-cardinality history не может зависеть от выживания
одной node-local директории.

### Existing AIFE route is preserved

Future data/server access extends existing skeleton:

```text
Presentation / Workspace
→ Manager
→ Service
→ Repository or Gateway
→ Adapter
→ SERVER_BOUNDARY
→ AIFE_SERVER_ROOT
```

`STD-ARCH-PATTERNS-001` remains normative for ownership. All public runtime
dependencies remain resolved through `AppContext`; `DependencyManager` cannot
become a second public service/repository route.

Direct UI access to SQL, SQLite, MongoDB, PostgreSQL, Parquet path, object
storage, server filesystem, provider APIs or ETH D6 is forbidden.

### Generic mechanism vs domain semantics

AIFE foundation may own generic mechanisms for:

- work execution/ownership/retry/checkpoint;
- durable staging/recovery;
- logical publication lifecycle;
- storage adapter/profile;
- semantic data access boundary;
- provenance/diagnostics;
- server operations/reproducibility.

Domain remains authoritative for identities, source/provider semantics,
normalization, validation, finality and domain derivation/interpretation.

ETH Data Bridge therefore remains market-data semantic authority; AIFE does
not redefine `series_id`, `observation_id`, provider rules or market finality.

### Horizontal scale by design

Initial deployment may be one server and a simple container runtime.

Architecture must allow future `WORKER_COUNT=1..N` without changing semantic
request, domain identities, publication identity, storage semantic identity or
provenance meaning.

Minimum future work concepts are stable work unit, partition/shard,
lease/ownership equivalent, idempotency key, checkpoint, retry and terminal
state. This ADR does not implement a distributed coordinator.

### Publication and durability separation

The foundation must preserve:

```text
INGEST_DURABILITY != CANONICAL_HISTORY_DURABILITY
```

A generic publication path should eventually support deterministic logical
publication identity, storage adapter materialization, durability proof,
independent readback, canonical registration and whole-unit ACK. Local write
alone must not be interpreted as canonical publication solely because it is
inside `AIFE_SERVER_ROOT`.

### Consumer boundary

The stable consumer contract is semantic, domain-aware, backend-neutral,
node-neutral, versionable, fail-closed and returns provenance.

Transport is separate from semantics. This ADR selects none of HTTP, gRPC,
WebSocket, CLI/IPC or another transport.

## Rationale

This decision:

1. prevents a second runtime/data route beside current AIFE architecture;
2. preserves `AppContext` and Manager/Service/Repository ownership;
3. keeps workspace consumers storage- and node-neutral;
4. preserves domain authority instead of centralizing all semantics in the
   platform;
5. permits simple one-server rollout;
6. permits later horizontal scale without semantic rewrite;
7. uses proven ETH behavior as evidence without copying D8/D9/D6 ontology;
8. prevents server filesystem topology from becoming canonical data authority.

## Alternatives considered

### A. Make D8/D9/D6 generic AIFE platform names

Rejected. They are ETH-program names and carry domain/history context that
must not become platform semantics.

### B. Select one universal database now

Rejected. Current AIFE authority has no binding database topology decision,
Data standards are draft, and no measured cross-domain workload justifies a
universal store.

### C. Use direct workspace access to database/object files

Rejected. It bypasses Repository/Gateway/Adapter boundaries, leaks physical
storage into consumer semantics and blocks backend/node substitution.

### D. Build distributed infrastructure first

Rejected. Multi-node semantic readiness is required, but Kubernetes, Kafka,
distributed SQL, service mesh and similar mechanisms have no current measured
need.

### E. Reuse SystemControl client or EventBus as data plane

Rejected. `SystemControl` is a separate control-plane precedent; `EventBus` is
application coordination. Neither becomes high-volume data transport by this
decision.

## Explicit deferred decisions

This ADR does **not** choose:

```text
database vendor
object-storage vendor
container orchestrator
Kafka
Redis
ClickHouse
TimescaleDB
Iceberg
Delta Lake
gRPC
WebSocket
deployment cloud
load balancer
```

`OBJECT_BLOB_PLUS_PARQUET` remains an ETH P2 Research direction, not universal
AIFE storage.

## Consequences

### Positive

- one architecture route remains authoritative;
- server operations are reproducible without becoming semantic authority;
- future storage substitution does not leak into workspace contract;
- one-server implementation remains small;
- generic extraction is limited to proven reusable properties;
- multi-worker/multi-node evolution has explicit identity/ownership/durability
  seams.

### Constraints / costs

- F2 must define the minimum work/publication/access bindings before F3;
- node-local runtime state may need later migration when multi-node use becomes
  real;
- public transport selection, if needed, requires separate owner decision and
  compliance with approved API/security standards;
- final storage technology remains unresolved until workload evidence exists.

## Relationship to existing owner authority

Hard dependencies:

- `STD-ARCH-PATTERNS-001` — Manager/Service/Repository ownership and
  `AppContext` public runtime rule;
- `ADR-INITIALIZER-CORE-001` — sole public runtime resolution through
  `AppContext`, `DependencyManager` internal only;
- `STD-GOVERNANCE-ADR-001` + `STD-GOVERNANCE-NAMING-001` — this ADR's owner
  placement and identity;
- Data draft standards — terminology/risk input only;
- approved API/security/logging standards — future public interface and
  operations constraints.

This ADR does not supersede current owner artifacts.

## Implementation boundary

```text
SERVER_IMPLEMENTATION_AUTHORIZED=NO
DATABASE_CREATION_AUTHORIZED=NO
AIFE_WORKSPACE_MUTATION_AUTHORIZED=NO
P2_IMPLEMENTATION_AUTHORIZED=NO
R2_RESUME_AUTHORIZED=NO
PRODUCTION_ACTIVATION_AUTHORIZED=NO
```

Next owner action after this candidate package is exact-byte integration and
registry sync, not implementation.
