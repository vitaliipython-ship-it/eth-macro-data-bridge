---
title: "RESEARCH: aife-server-data-foundation — general"
status: active
owner: Architecture Lead
created: 2026-08-27
updated: 2026-08-27
review_cycle_days: 30
next_review_due: 2026-09-26
category: architecture
doc_type: analysis
language: ru
tags: [research, general, server, data, storage, analytics, backtest, f5r]
---

# RESEARCH: aife-server-data-foundation — general

## 1. Краткий вывод

Этот документ материализует **первый independent ChatGPT/GPT run** для
`AIFE-SERVER-DATA-STORAGE-ANALYTICS-BACKTEST-ARCHITECTURE-RESEARCH-V1`.
Он является evidence-layer `local-candidate`, а не owner acceptance и не разрешение на F5.

Текущий first-agent candidate:

```text
ARCHITECTURE_STATUS=
local-candidate

MINIMUM_INITIAL_STACK=
PostgreSQL durable control plane
+ capability-based object/blob storage
+ immutable Parquet
+ versioned AIFE manifests
+ embedded DuckDB per worker

POSTGRESQL_ROLE=
REQUIRED_CONTROL_AND_SPARSE_DURABLE_METADATA;
REJECT_AS_DEFAULT_MULTI_TB_RAW_MARKET_DATA_STORE

ICEBERG_DECISION=
DEFER_PENDING_PROVEN_TRANSACTIONAL_TABLE_METADATA_NEED

CLICKHOUSE_DECISION=
DEFER_PENDING_REPRESENTATIVE_BENCHMARK_TRIGGER

REDIS_DECISION=
DEFER_OR_REJECT_REQUIRED_NOW

KAFKA_DECISION=
DEFER_OR_REJECT_REQUIRED_NOW

OPENSEARCH_DECISION=
DEFER_REQUIRED_NOW

VECTOR_DB_DECISION=
DEFER_REQUIRED_NOW

MEASURED_BASELINE=
INSUFFICIENT
```

Главный вывод не основан на популярности технологий. Он следует из уже существующей
AIFE/Data Bridge границы: domain владеет semantics и identities, Server владеет generic
work/publication/storage/access mechanisms, а physical backend обязан оставаться заменяемым.
Поэтому минимальный стек должен сначала закрыть durable control, immutable bulk storage,
analytical scan и replay correctness, не вводя преждевременно catalog/OLAP/cache/broker/search
services без доказанного риска.

## 2. Проверенная authority и точка программы

### 2.1 Repository / AIFE authority

Evidence-Class: `REPOSITORY/AIFE AUTHORITY`.

Fresh pre-materialization authority:

```text
REPOSITORY=
vitaliipython-ship-it/eth-macro-data-bridge

WIP_BRANCH=
agent/aife/server-data-foundation-wip

WIP_HEAD=
2b82c75a67ed7ce5cd87cae2ccf02f09677d200c

WIP_TREE=
2615dcd21570f0816be39c574b3b9f8ef1c1bc16

LAST_VERIFIED_STAGE=
F4_COMPLETE
```

Host root `AGENTS.md` устанавливает:

```text
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
PHYSICAL_STORAGE_BACKEND_IS_SEMANTIC_AUTHORITY=false
EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false

HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_VERSIONED_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

F4 checkpoint authority:

```text
F4_COMPLETE=YES
DATABASE_VENDOR_SELECTED=NO
OBJECT_STORE_VENDOR_SELECTED=NO
PRODUCTION_STORAGE_BACKEND_IMPLEMENTED=NO
PHYSICAL_WAREHOUSE_ACTIVATED=NO
PRODUCTION_STORAGE_STARTED=NO
MIGRATION_STARTED=NO
SERVER_DEPLOYMENT_STARTED=NO
F5_STARTED=NO
NEXT_CHECKPOINT=CHECKPOINT_F5_HIGH_CARDINALITY_PHYSICAL_STORAGE_LIFECYCLE
```

F4 также фиксирует authority split:

```text
ETH_DATA_BRIDGE_OWNS=
MARKET_DATA_SEMANTICS
+ PROVIDER_SEMANTICS
+ DOMAIN_IDENTITIES
+ NORMALIZATION
+ DOMAIN_VALIDATION
+ FINALITY
+ REVISION_RULES
+ GAP_RULES
+ DOMAIN_RESOLUTION_RULES

AIFE_SERVER_OWNS=
GENERIC_WORK_MECHANISMS
+ GENERIC_EXECUTION_OWNERSHIP
+ GENERIC_PUBLICATION
+ GENERIC_STORAGE_LIFECYCLE
+ GENERIC_ACCESS_MECHANISMS
```

AIFE governance authority была прочитана из canonical reference snapshot:

```text
AIFE_REVIEW_PACKAGE_SHA256=
c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0

AIFE_REFERENCE_HEAD=
1ed138c06881aaebf8e650fcc020cef570e31b6d

AIFE_REFERENCE_TREE=
11f5cbc5f81836dddf0e854d3685418b53f22852
```

Canonical artifact rules used:

- `Intent=gaps` → `TYPE=RESEARCH`;
- blank Focus → `classifier=general`;
- filename shape:
  `RESEARCH_aife-server-data-foundation_general_data-backend-architecture_2026-08-27_chatgpt-gpt.md`;
- per-agent materialized-and-protected rule;
- P1 blind review cannot be simulated by a second pass of the same agent identity;
- required YAML frontmatter and final `## Итоговое решение (контракт)` block.

Task-scoped owner authorization supplies the otherwise unpublished agent suffix:

```text
EXECUTION_TOOL=ChatGPT
MODEL_FAMILY=GPT
TASK_SCOPED_AGENT_SUFFIX=_chatgpt-gpt
TASK_SCOPED_AGENT_SUFFIX_AUTHORIZED=YES
GLOBAL_AIFE_SUFFIX_STATUS=NOT_YET_PUBLISHED
```

### 2.2 Evidence taxonomy

This artifact separates evidence classes explicitly:

| Evidence-Class | Meaning in this run |
| --- | --- |
| `REPOSITORY/AIFE AUTHORITY` | committed Data Bridge/WIP facts or canonical AIFE snapshot rules |
| `EXTERNAL PRIMARY EVIDENCE` | official exchange/project documentation |
| `MEASURED EVIDENCE` | actual representative measurements obtained for this decision |
| `INFERENCE` | architecture consequence derived from authority/evidence |
| `UNRESOLVED MEASUREMENT` | required measurement not available in current run |

No vendor benchmark is treated as independent measured evidence.

## 3. F4 → F5 architectural gap diagnosis

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`.

F4 intentionally ends before selecting a physical high-cardinality backend. The current program
therefore has a real decision gate between F4 and F5:

```text
F4
→ semantic/domain integration complete
→ generic Server lifecycle contracts present
→ physical high-cardinality backend intentionally unselected
→ F5 requires a versioned physical profile
```

First-agent verdict:

```text
F5R_GATE_REQUIRED=
YES

PROGRAM_MAP_ARCHITECTURE_GAP=
MISSING_CROSS_AIFE_DATA_BACKEND_RESEARCH_AND_DECISION_GATE
```

Reason: F5 is not blocked by a source defect. It is blocked because P2 lifecycle would otherwise
encode a backend/topology decision without cross-AIFE analysis of data classes, PIT, backtests,
failure domains, horizontal scaling, backup/restore and operational complexity.

This F5R gate is **inside the existing `aife-server-data-foundation` program**. It does not create
a second roadmap. The minimal semantic sequence remains:

```text
F4
→ F5R dual-agent research + consolidation + owner publication
→ F5
→ F5M
→ F6/F7
→ F8
```

## 4. AIFE-wide data-class matrix

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`.

Cardinality values below are qualitative unless repository evidence supplies a concrete fact.
They are not substituted for missing measurements.

| Class | Examples | Write / temporal pattern | Consistency / revision need | Primary query pattern | Candidate physical placement | Authority / rebuildability |
| --- | --- | --- | --- | --- | --- | --- |
| A. Durable operational/control state | work, slots, claims, leases, fencing, publication state, idempotency, inventory metadata, schedules, checkpoints | small/medium mutable transactional | strong ownership, atomic transitions, stale-fence rejection | point lookup, indexed state scan | PostgreSQL | durable control substrate; not domain semantics |
| B. High-cardinality raw market data | raw trades, aggTrades, liquidations, L2 deltas, L3/event data, HF derivatives/flow | append-heavy, bursty, high cardinality | source sequence/revision preserved; immutable after seal | time/instrument range scans, reconstruction | object/blob + Parquet + manifest | domain semantics remain Data Bridge; bytes durable |
| C. Regular/medium market history | OHLCV, OI, funding, options, liquidity, derived observations | periodic append/supersede by domain rules | revision and known/effective time required | range scan, aggregate, selective joins | object/Parquet; sparse catalog metadata in PostgreSQL | domain authority external to physical store |
| D. Analytical sparse history | Wave/Elliott/NEoWave state, alternatives, structures, patterns, regimes, events, hypotheses, scenarios | sparse append/revision | explicit known_at/version lineage | point/range by subject/time/version | PostgreSQL initially; object for large payloads | analytical semantic owner, not storage |
| E. News/source evidence | source identity, hashes, headline, published_at, known_at, revisions, permitted raw snapshots | append + source revision | known_at/first-observed and source revision critical | time/source/entity lookup; optional text search | PostgreSQL metadata + object snapshots where permitted | raw snapshot durable; search projection rebuildable |
| F. Derived analytical datasets | indicators, features, feature matrices, screening, signals | batch/stream derived, often large | method/version + source generation pinning | scans, joins, aggregation | Parquet/object + PostgreSQL metadata | rebuildable if inputs/methods pinned |
| G. Predictions / AI | model definitions, versions, artifacts, predictions, training/eval datasets, inference matrices | mixed: metadata mutable, artifacts immutable | model version and dataset generation required | registry lookup + large scan | PostgreSQL metadata + object/blob + Parquet | model artifacts durable; many matrices rebuildable |
| H. Strategy / experiment state | strategy definitions, parameters, experiments, metadata | transactional/sparse | versioned definitions and run identity | point lookup, experiment listing | PostgreSQL | durable control/semantic metadata |
| I. Backtesting | run identity, PIT inputs, traces, equity curves, orders/fills, metrics, sweeps | many independent runs; large derived output | pinned read-set + method/model version | large scans, aggregation, comparison | PostgreSQL run metadata + object/Parquet results; DuckDB per worker | outputs reproducible/rebuildable when inputs pinned |
| J. Search/retrieval projections | FTS, vector, semantic indices | derived/rebuildable | no semantic authority | search/retrieval | start with PostgreSQL FTS/batch index where sufficient; dedicated service deferred | projection/cache |
| K. Generic large blobs | model binaries, permitted source snapshots, generated artifacts, archives | immutable object write | content identity/checksum/version | identity lookup, streaming download | object/blob | durable substrate, not semantic authority |

Placement is intentionally mixed. `ONE_DATABASE=NO` is preserved without creating a mandatory
polyglot service fleet.

## 5. Workload and SLO requirement matrix

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE + UNRESOLVED MEASUREMENT`.

No numeric p50/p95 SLO is invented. Qualification must bind exact numeric thresholds later.

| Workload | Required correctness | Latency/throughput shape | Multi-writer | Failure requirement | Candidate mechanism | Numeric SLO status |
| --- | --- | --- | --- | --- | --- | --- |
| Work/claim/lease/fence transitions | atomic, stale-owner rejection | low-latency point operations | yes | restart-safe, idempotent | PostgreSQL | `UNRESOLVED_MEASUREMENT` |
| Publication state / ACK | exact identity and evidence binding | transactional, moderate volume | yes | retry-safe, no double ACK | PostgreSQL + storage readback | `UNRESOLVED_MEASUREMENT` |
| Raw trade/L2 ingestion | no silent gap/revision loss | sustained/bursty append | logically yes across partitions | partial upload and retry safe | bounded spool → batch → Parquet/object | `UNRESOLVED_MEASUREMENT` |
| OHLCV/OI/options history | immutable/sealed generation + revisions | range scans and aggregates | bounded | reproducible read-set | Parquet/object + manifests | `UNRESOLVED_MEASUREMENT` |
| Sparse analytical history | versioned known_at semantics | point/range | low/moderate | transaction durability | PostgreSQL | `UNRESOLVED_MEASUREMENT` |
| Large feature matrices | source/method pinned | large scan/join | batch writers | rebuildable | Parquet/object + DuckDB | `UNRESOLVED_MEASUREMENT` |
| PIT backtest | exact historical visibility | large scan + joins + aggregates | many independent workers | retry without semantic drift | pinned manifest + DuckDB worker | `UNRESOLVED_MEASUREMENT` |
| Parameter sweep | deterministic work identity | embarrassingly parallel where state-independent | yes across work IDs | independent retry | scheduler + N workers | `UNRESOLVED_MEASUREMENT` |
| Interactive OLAP | projection may be stale but labeled | concurrent analytical reads | read-heavy | projection loss non-semantic | DuckDB first; ClickHouse on trigger | `UNRESOLVED_MEASUREMENT` |
| Search/vector | projection semantics only | lookup/search | depends | rebuildable index | simpler local/PG first | `UNRESOLVED_MEASUREMENT` |

## 6. Current corpus / growth evidence

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + UNRESOLVED MEASUREMENT`.

Repository authority proves the presence of real classes and F4 fixtures:

```text
ROLLING_SPOT_MANIFEST=data/manifest.json
CLOSED_SPOT_HISTORY_SERIES=history/manifest.json
DERIVATIVES_METRIC_ARCHIVE=derivatives/manifest.json
OPTIONS_SURFACE_SNAPSHOT=options/manifest.json
LIQUIDITY_SNAPSHOT=liquidity/manifest.json

F4_REAL_DATA_BRIDGE_FIXTURES_USED=YES
F4_FIXTURE_PATH_COUNT=5
```

The reconciled Data Bridge status also records an accepted A1/A2 checkpoint containing 20 eligible
D8 observations and `PENDING→FORWARDED` completion. That is useful correctness evidence, but it is
**not** a capacity baseline for P2 or AIFE-wide storage.

The first-agent run did not obtain a trustworthy all-AIFE measurement for:

```text
current total bytes across all AIFE data classes
30/90/365-day growth
ingest p50/p95/peak
object size distribution
row distribution
partition cardinality
concurrent analytical scans
compaction amplification
restore throughput
```

Therefore:

```text
MEASURED_BASELINE=
INSUFFICIENT
```

This gap blocks performance-driven promotion of optional mechanisms such as ClickHouse and can
affect Iceberg/catalog decisions if actual multi-writer/table-scale metadata pressure appears.
It does **not** invalidate the minimum candidate whose core choices are correctness- and
simplicity-driven.

## 7. Exchange/public market-data architecture evidence

Evidence-Class: `EXTERNAL PRIMARY EVIDENCE`.

Only public protocol semantics are used. No claim is made about private exchange infrastructure.

### Binance

Official Spot WebSocket Market Streams documentation describes diff-depth updates carrying update
IDs and the local order-book reconstruction sequence based on buffering deltas, obtaining a REST
snapshot, reconciling `lastUpdateId` with event `U/u`, discarding stale updates and resynchronizing
when continuity is not satisfied.

Primary source:
`https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams`

Architecture consequence:

```text
snapshot alone is insufficient
delta alone is insufficient
source-native sequence identity must survive ingestion/storage
gap recovery is a semantic ingestion concern, not a database feature
```

### Deribit

Official order-book subscription documentation states that the first notification is a full
snapshot, later notifications are incremental updates, and each notification has `change_id`;
subsequent messages include `prev_change_id`. Equality with the previous `change_id` is the
continuity check.

Primary source:
`https://docs.deribit.com/subscriptions/orderbook/bookinstrument_nameinterval`

Architecture consequence: source continuity evidence must remain available after physical sealing,
compaction and replay.

### Coinbase

Official Exchange WebSocket documentation says consumers must handle sequence gaps/out-of-order
messages or use channels that guarantee delivery; the Level2 channel is documented as the easiest
way to keep an order book in sync and as guaranteeing all updates.

Primary sources:

- `https://docs.cdp.coinbase.com/exchange/websocket-feed/overview`
- `https://docs.cdp.coinbase.com/exchange/websocket-feed/channels`

Architecture consequence: transport delivery guarantees and reconstruction rules belong to the
producer/ingestion semantics. Storage cannot retroactively infer a dropped source event.

### Cross-source conclusion

The public evidence supports the existing Data Bridge/AIFE separation:

```text
PUBLIC_PROTOCOL_SEMANTICS
→ source sequence/revision/gap handling
→ domain accepted artifact
→ AIFE generic durable lifecycle
```

It does not support moving exchange-specific sequence logic into PostgreSQL, Iceberg, DuckDB or
ClickHouse.

## 8. AIFE semantic-vs-physical authority boundary

Evidence-Class: `REPOSITORY/AIFE AUTHORITY`.

The strongest invariant of this decision is:

```text
SEMANTIC_IDENTITY != PHYSICAL_LOCATOR
```

AIFE Server receives an already accepted domain artifact envelope. A backend migration may change:

```text
database
bucket
filesystem
object key layout
Parquet partitioning
catalog implementation
analytical projection
```

without changing:

```text
domain_artifact_identity
source_revision
content_identity
WorkId
publication identity
semantic receipt meaning
PIT visibility rules
```

This makes physical storage a durable substrate, not a semantic SSOT. No backend selected in F5 may
introduce a second ETH resolver, reader or catalog authority.

## 9. Bulk object/blob storage profile

Evidence-Class: `INFERENCE` constrained by Server Storage Contract.

Required capability class, not vendor:

```text
BULK_OBJECT_BACKEND_CLASS=
CAPABILITY_BASED_DURABLE_OBJECT_OR_BLOB_STORAGE
```

Required capabilities for F5 qualification:

- stable opaque object identity;
- immutable/versioned write pattern;
- checksum/content binding;
- independent read-back;
- safe retry/idempotent write identity;
- bounded inventory/listing;
- lifecycle/retention hooks;
- access control/encryption compatible with deployment policy;
- backup/restore path with clean-environment proof;
- conditional publication or equivalent conflict prevention where concurrent writers can collide.

Managed object storage, self-hosted S3-compatible storage and a simpler durable filesystem/blob
substrate are implementation profiles, not semantic contracts. Product choice is deferred until
deployment/capacity/failure requirements are measured.

A single local filesystem is **not** sufficient merely because F5 may initially run on one server:
a one-node profile still needs a backup/restore and failure model that does not make node-local path
a semantic locator.

## 10. Parquet physical representation and small-file implications

Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + INFERENCE`.

Apache Parquet official format documents:

- files contain row groups;
- row groups contain column chunks;
- file metadata records locations/metadata needed for selective reads;
- readers use metadata to locate relevant column chunks.

Primary sources:

- `https://parquet.apache.org/docs/file-format/`
- `https://parquet.apache.org/docs/concepts/`
- `https://parquet.apache.org/docs/file-format/metadata/`

The architectural benefit for AIFE is columnar scan/filter/aggregation over immutable sealed batches,
not one-object-per-event persistence.

Hard candidate rule:

```text
ONE_EVENT_OR_OBSERVATION_PER_OBJECT=
FORBIDDEN
```

Candidate lifecycle:

```text
accepted domain input
→ bounded durable spool
→ deterministic batch
→ deterministic physical object identity
→ Parquet write
→ seal
→ independent read-back
→ versioned manifest
→ canonical registration
→ ACK
```

Exact target file size is **not fixed in this research**. It must be benchmarked against the actual
row width, object-store request characteristics, pruning/selectivity and worker memory. A magic
128/256/512 MiB number would be an invented requirement.

Compaction is allowed only as:

```text
asynchronous
identity-preserving
provenance-preserving
non-semantic
```

and must produce a new physical generation/read-set rather than silently replacing the logical
history identity.

## 11. Versioned AIFE manifest model

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`.

AIFE already requires stable identity, independent read-back and backend-neutral storage ports.
The simplest F5 metadata model is therefore an AIFE-owned **versioned manifest** over immutable
objects.

Minimum manifest semantics for a sealed generation:

- generation/read-set identity;
- schema/version identity;
- complete object membership;
- object content/checksum identity;
- logical partition identity without exposing it as consumer semantic API;
- source/domain revision references sufficient for reconciliation;
- created/sealed time and relevant PIT visibility metadata;
- predecessor/supersession relationship where required;
- independent read-back status/evidence;
- producer/writer software revision;
- manifest content identity.

The manifest is not a second domain catalog. It is physical inventory and generation evidence used
after semantic resolution.

Multi-writer publication requires deterministic target identity and conflict/fencing rules.
If manifest transactions become complex enough to require table-level serializable metadata
operations, that becomes an Iceberg/transactional-catalog expansion trigger rather than a reason
to preemptively implement a custom lakehouse catalog.

## 12. Plain Parquet/manifests vs transactional metadata vs Iceberg

Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + INFERENCE`.

Compared profiles:

```text
PROFILE_A=
immutable sealed Parquet
+ versioned AIFE manifests

PROFILE_B=
PROFILE_A
+ transactional metadata/catalog in existing durable control substrate

PROFILE_C=
Parquet
+ Apache Iceberg table metadata/catalog
```

Apache Iceberg official specification adds table metadata, snapshots, manifests/manifest lists,
schema and partition configuration, and optimistic concurrency based on atomic metadata replacement.

Primary source:
`https://iceberg.apache.org/spec/`

Decision matrix:

| Capability | Profile A | Profile B | Profile C |
| --- | --- | --- | --- |
| Immutable object durability | yes | yes | yes |
| Exact generation/read-set pinning | AIFE manifest | AIFE manifest + transaction | Iceberg snapshot |
| Atomic publication | bounded manifest pointer/registration | strong transactional catalog | table metadata commit |
| Multi-writer collision handling | deterministic partitions/fencing; bounded | explicit DB transaction | Iceberg optimistic concurrency |
| Schema evolution | AIFE schema/version contract | same + catalog | native table metadata |
| Partition evolution | explicit new generation/layout | catalog-assisted | native Iceberg feature |
| PIT domain correctness | still external to storage | still external | still external |
| Operational surface | smallest | moderate | larger metadata/table-format lifecycle |
| Multi-engine interoperability | Parquet broadly readable | Parquet broadly readable | strong if engines implement Iceberg correctly |
| Upgrade/catalog complexity | low | medium | medium/high relative to A |
| Need proven now | yes | not yet | not yet |

First-agent conclusion:

```text
ARE_WE_REIMPLEMENTING_A_MEANINGFUL_PORTION_OF_ICEBERG=
NOT_PROVEN

ICEBERG_DECISION=
DEFER_PENDING_PROVEN_TRANSACTIONAL_TABLE_METADATA_NEED
```

Iceberg becomes a serious required candidate when measured reality proves one or more of:

- multiple independent writers need concurrent table-level commits beyond deterministic work
  partitioning/fencing;
- partition/schema evolution is frequent enough that AIFE manifests become a bespoke transaction
  system;
- snapshot expiration/manifest planning/object discovery becomes an operational bottleneck;
- multi-engine table semantics are a hard requirement;
- metadata recovery correctness is harder than adopting the open table format.

Data volume by itself is not such a trigger.

## 13. PostgreSQL role

Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + INFERENCE`.

PostgreSQL official documentation describes MVCC and transaction isolation for concurrent access.

Primary source:
`https://www.postgresql.org/docs/current/mvcc-intro.html`

The required role is:

```text
CONTROL_STATE_BACKEND=
POSTGRESQL

POSTGRESQL_ROLE=
REQUIRED_CONTROL_AND_SPARSE_DURABLE_METADATA;
REJECT_AS_DEFAULT_MULTI_TB_RAW_MARKET_DATA_STORE
```

Good-fit workloads:

- Work/slot/claim/lease/fencing state;
- publication state and idempotency;
- schedules/checkpoints;
- schema/generation/catalog metadata;
- sparse analytical history;
- strategy/experiment/run metadata;
- optional transactional manifest/catalog coordination.

Why not default raw P2 warehouse:

- raw P2 is append-heavy/high-cardinality and scan-oriented;
- Parquet/object separates cheap durable bulk from transactional control;
- using PostgreSQL for both roles creates larger backup/restore, vacuum/index/partition and
  operational coupling without a demonstrated benefit;
- the ability to store a large table does not prove it is the simplest AIFE physical profile.

PostgreSQL remains a single **control-plane substrate**, not the only storage technology.

## 14. PIT/history correctness model

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`.

Required PIT contract:

```text
known_at <= replay_cutoff
+
source-native revision/sequence evidence
+
pinned immutable generation/read-set
+
pinned method/model version
```

Storage-native snapshot/time-travel is insufficient by itself because a database snapshot cannot
recover:

- data the system did not know by the replay cutoff;
- a source sequence gap not captured during ingestion;
- the domain revision/finality policy;
- which model/method version produced a derived artifact.

A reproducible read must pin at least:

```text
source generation / manifest identity
schema/version identity
method/model version
replay cutoff
subject/universe
time range
```

Compaction, projection rebuild, new data arrival and schema evolution must not change the meaning of
an already pinned replay.

## 15. Backtesting architecture

Evidence-Class: `INFERENCE`.

Required model:

```text
BACKTEST_MODEL=
PINNED_IMMUTABLE_DATASET_GENERATION
+ PIT_CUTOFF
+ EMBEDDED_DUCKDB_PER_WORKER
+ INDEPENDENT_WORK_UNIT_PARTITIONING
+ IDEMPOTENT_RESULT_PUBLICATION
```

Control flow:

```text
AIFE scheduler/work ownership
→ durable WorkId + claim/lease/fence
→ resolve pinned input generation/read-set
→ execute one independent work unit
→ embedded DuckDB scans required Parquet
→ durable result object/metadata
→ independent read-back
→ idempotent publication
```

Safe horizontal partition axes:

```text
strategy/model version
parameter set
universe/instrument set
scenario
independent replay run
```

Hard restriction:

```text
TIME_SHARDING_STATEFUL_BACKTEST=
FORBIDDEN_UNLESS_CHECKPOINT_OR_STATE_TRANSFER_SEMANTICS_ARE_PROVEN
```

Splitting a stateful strategy by time can change indicator warmup, portfolio state, orders,
exposure, path-dependent fees and risk state. It is not an ordinary embarrassingly parallel axis.

## 16. Horizontal scaling 1→N→1

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`.

The architecture must allow:

```text
1 node
→ N nodes
→ 1 node
```

without changing semantic identity/public contracts.

Required seams:

- `NODE_ID_IS_NOT_SEMANTIC_IDENTITY`;
- stable logical WorkId;
- deterministic slot/work identity;
- durable claim/lease;
- fencing and stale-owner rejection;
- idempotent publication;
- deterministic storage identity;
- no process-memory SSOT;
- no node-local filesystem semantic locator;
- disposable/stateless workers where applicable;
- projections rebuildable from durable authority;
- unrelated work identities progress independently.

Therefore:

```text
MULTI_NODE_IMPLEMENTATION_NOW=
NO

MULTI_NODE_REWRITE_LATER=
NO
```

F5 needs horizontal **contracts/seams**, not cluster operations.

## 17. DuckDB per-worker model

Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + INFERENCE`.

DuckDB official documentation supports direct Parquet queries with parallel processing,
filter pushdown and reading only relevant columns. Its concurrency documentation emphasizes the
embedded/single-process model and cautions around shared-file multi-process writes.

Primary sources:

- `https://duckdb.org/docs/current/guides/file_formats/query_parquet`
- `https://duckdb.org/docs/current/connect/concurrency`

Decision:

```text
BACKTEST_QUERY_ENGINE=
DUCKDB_EMBEDDED_PER_WORKER

SHARED_DISTRIBUTED_DUCKDB_DATABASE=
REJECT_REQUIRED_NOW
```

Why per worker:

- no new always-on analytical service;
- local process failure maps cleanly to Work retry;
- immutable Parquet read-set is independently reproducible;
- each worker can apply memory/CPU limits;
- horizontal scale comes from AIFE work ownership, not a shared DuckDB write database.

Local cache is optional/rebuildable and cannot become authority.

## 18. ClickHouse acceleration gate

Evidence-Class: `INFERENCE + UNRESOLVED MEASUREMENT`.

Candidate role:

```text
INTERACTIVE_OLAP=
DUCKDB_OR_BOUNDED_MATERIALIZED_DATASETS_FIRST

CLICKHOUSE_ROLE=
REBUILDABLE_ANALYTICAL_PROJECTION_ONLY

CLICKHOUSE_DECISION=
DEFER_PENDING_REPRESENTATIVE_BENCHMARK_TRIGGER
```

Promotion trigger:

```text
CLICKHOUSE_REQUIRED_ONLY_IF=
representative concurrent analytical workloads
fail an owner-defined SLO with
object/Parquet + DuckDB + bounded materialized datasets
and the bottleneck cannot be removed by simpler partition/layout/query changes
```

No exact latency/concurrency threshold is invented because the current task lacks a measured
requirement. Loss of a future ClickHouse projection must not lose canonical history.

## 19. Redis/Kafka/OpenSearch/vector disposition

Evidence-Class: `INFERENCE`.

### Redis

```text
REDIS_DECISION=
DEFER_OR_REJECT_REQUIRED_NOW
```

No demonstrated risk requires a network cache over PostgreSQL plus bounded in-process/rebuildable
cache. Introduce only when measured latency/load shows the durable control plane cannot meet an
explicit cacheable access SLO.

### Kafka / broker

```text
KAFKA_DECISION=
DEFER_OR_REJECT_REQUIRED_NOW
```

Durable fan-out, independent consumer offsets and long stream replay are valid mechanisms, but the
current Server model already has Work, publication, storage, claims/leases/fencing and durable
retry semantics. A broker is required only if independent consumer fleets/fan-out/replay demand
cannot be expressed without coupling producers to consumers or overloading the control plane.

### OpenSearch / full-text

```text
OPENSEARCH_DECISION=
DEFER_REQUIRED_NOW
```

Start with PostgreSQL FTS or a batch/rebuildable index where adequate. Dedicated search service
requires a real search corpus/query/SLO gap.

### Vector database

```text
VECTOR_DB_DECISION=
DEFER_REQUIRED_NOW
```

No measured high-scale vector retrieval workload was established. Model/vector artifacts may be
stored durably without adopting a dedicated vector service.

## 20. Failure / HA / backup / restore analysis

Evidence-Class: `INFERENCE`; numeric RPO/RTO are `UNRESOLVED MEASUREMENT`.

Hard invariant:

```text
BACKUP_EXISTS != RESTORE_PROVEN
REPLICATION != BACKUP
```

| Failure | Semantic loss? | Candidate recovery | Manual action / proof |
| --- | --- | --- | --- |
| worker crash | no if Work/input/result not ACKed prematurely | lease expiry/fence, retry same WorkId | verify stale owner rejected |
| control process crash | no if PostgreSQL committed | restart process, resume durable state | inspect durable claims/publication state |
| server reboot | no by design | restart durable services/workers | read-back control + object state |
| PostgreSQL loss | potentially control loss | restore backup/PITR as owner policy defines | restore onto clean environment and reconcile object/manifest inventory |
| single disk loss | depends on selected physical profile | storage redundancy/restore | prove read-back after failure |
| object node/provider loss | potentially bulk data loss | replica/backup restore or provider recovery | verify object checksums + manifest completeness |
| network partition | no if fencing/idempotency correct | reject stale/ambiguous publication until reconciled | prove no double publication |
| partial upload | no canonical publication | discard/complete temporary object; retry stable identity | independent read-back before registration |
| writer retry | no | idempotent identity + conflict detection | exact object/manifest membership |
| duplicate write | no | same identity/digest becomes no-op or conflict | prove no semantic duplicate |
| stale fence | must not commit | fencing rejects stale owner | explicit failure test |
| catalog metadata loss | discoverability risk | restore catalog or rebuild where designed | reconcile against object manifests |
| projection loss | no | rebuild from canonical read-set | compare projection generation |
| ClickHouse loss if adopted | no | rebuild projection | no authority cutover |
| cache loss | no | refill/rebuild | none beyond health proof |
| compaction interruption | no | old generation stays readable; retry new generation | verify no pointer switch before complete readback |
| corrupted object | data loss unless redundant | checksum detect, restore replica/backup | exact digest/readback |
| credential rotation | availability risk | rotate independent credential domain | verify least-privilege read/write after rotation |
| clean-environment restore | must preserve semantic route | restore PostgreSQL + object/manifests + secrets/config | end-to-end resolver/access/readback proof |

HA topology (replicas, failover manager, object replication class) is not fixed by this research.
It requires owner RPO/RTO and deployment environment evidence. The architecture keeps those seams
without forcing multi-node deployment now.

## 21. Security, access and secrets implications

Evidence-Class: `INFERENCE`.

Minimum stack should minimize credential/failure domains:

- PostgreSQL credentials for control state;
- object/blob credentials for bulk data when backend requires them;
- worker identities receive least privilege for their assigned read/write capabilities;
- domain/provider credentials remain outside physical data-store semantics;
- manifests and object hashes are integrity evidence, not authorization;
- encryption-at-rest/in-transit follows the selected substrate and owner standards;
- backups must have separately verified access/restore controls;
- ClickHouse/Redis/Kafka/OpenSearch/vector adoption would each add credential, upgrade,
  monitoring and restore domains and therefore need a proven benefit.

## 22. Operational complexity and minimum-stack analysis

Evidence-Class: `INFERENCE`.

Counts below are **architecture service-class counts**, not measured production instance counts.
They assume Profile 2 metadata can use existing PostgreSQL. Product-specific HA may increase them.

| Profile | Durable service classes | Main credential domains | Backup/restore domains | Added failure/upgrade domains | Human/agent action impact | First-agent disposition |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 1. PostgreSQL + object/blob + Parquet + DuckDB embedded | 2 | 2 | 2 | control DB + object substrate | smallest; DuckDB is embedded | `REQUIRED_NOW candidate` |
| 2. Profile 1 + transactional metadata in PostgreSQL | 2 | 2 | 2 | more metadata transaction logic | moderate schema/transaction work | `DEFER` until multi-writer/catalog need |
| 3. PostgreSQL + object + Iceberg + DuckDB | 2+ depending catalog | 2+ | 2+ | table metadata/catalog/version lifecycle | higher engine/catalog discovery | `DEFER` |
| 4. Chosen durable substrate + ClickHouse projection | 3+ | 3+ | 3 if projection backup is chosen, otherwise rebuild proof | extra OLAP service | extra monitoring/upgrades/rebuild | `BLOCKED_ON_MEASUREMENT` |

Goal:

```text
MINIMUM_INITIAL_STACK_THAT_DOES_NOT_BLOCK_FUTURE_SCALE=
PROFILE_1_WITH_VERSIONED_AIFE_MANIFESTS
```

## 23. Benchmark / measurement gaps required for qualification

Evidence-Class: `UNRESOLVED MEASUREMENT`.

No production service was deployed and no benchmark was substituted with a vendor claim.

Required future F5 qualification measurements:

| Workload family | Required measurement | Environment/evidence |
| --- | --- | --- |
| raw trades / L2 deltas | sustained + peak ingest, rows/s, bytes/s, batch seal latency, object count | representative ETH P2 capture/replay |
| OHLCV/OI/funding/options | partition sizes, range scan throughput, selective filters | real representative history generations |
| Wave/news/sparse state | point/range latency and relational growth | representative PostgreSQL dataset |
| large feature matrices | scan/join/aggregate throughput, memory, spill, bytes read | representative Parquet corpus + DuckDB worker |
| PIT backtests | end-to-end run time, deterministic reread, cache cold/warm | pinned generation + method version |
| parameter sweeps | N-worker scale efficiency, claim contention, retry behavior | 1/N/1 worker matrix |
| interactive OLAP | concurrent reader latency/throughput | real dashboard/agent queries |
| multi-writer publication | conflict/fence/idempotency behavior | concurrent disjoint and colliding work IDs |
| compaction | input/output bytes, amplification, object-count reduction, interruption recovery | representative sealed partitions |
| restore | time to restore clean environment + exact readback | disposable clean recovery environment |

Exact missing baseline that must be collected:

```text
current total bytes across all AIFE data classes
30/90/365-day growth
ingest p50/p95/peak
object size distribution
row distribution
partition cardinality
concurrent analytical scans
compaction amplification
restore throughput
```

Decisions still blocked on measurements:

```text
CLICKHOUSE_PROMOTION
ICEBERG_PROMOTION_IF_METADATA_SCALE_OR_CONCURRENCY_IS_THE_DRIVER
CACHE_SERVICE_PROMOTION
BROKER_PROMOTION
DEDICATED_SEARCH_PROMOTION
HA_TOPOLOGY_AND_NUMERIC_RPO_RTO
```

## 24. Three-question mechanism review

Evidence-Class: `REPOSITORY/AIFE AUTHORITY + EXTERNAL PRIMARY EVIDENCE + INFERENCE`.

| Mechanism | 1. Реальный риск | 2. Более простой способ? | 3. Уменьшает действия? | Decision |
| --- | --- | --- | --- | --- |
| PostgreSQL | lost/ambiguous durable control transitions, concurrent claims, idempotency state | SQLite/process-local state does not satisfy future multi-process/node durable ownership without extra coordination | yes: one durable control substrate removes bespoke locking/state recovery | `REQUIRED_NOW` |
| Object/blob storage | high-cardinality bulk growth coupling to transactional DB/local node | plain local files only if durability/restore/location independence are proven; semantic path must stay opaque | yes: one bulk durability interface avoids universal DB and node-local authority | `REQUIRED_NOW` |
| Parquet | expensive scans/storage for large tabular history | row-oriented/raw JSON files are simpler to write but create scan/size cost; event-per-object is operationally worse | yes: standardized sealed batches reduce reader/storage work | `REQUIRED_NOW` |
| Versioned AIFE manifests | exact immutable read-set/discovery/readback/provenance across objects | directory listing alone cannot prove complete generation identity | yes: one bounded inventory/read-set removes ad-hoc discovery | `REQUIRED_NOW` |
| Iceberg | transactional table metadata, concurrent commits, schema/partition evolution | deterministic partitions + AIFE manifests, optionally PostgreSQL transaction | currently yes, simpler path exists and failure not proven | `DEFER` |
| DuckDB per worker | analytical/backtest scans without standing OLAP service | custom Python/Pandas scans can work but often add bespoke scan/SQL logic; DuckDB directly queries Parquet | yes: embedded engine removes service operations | `REQUIRED_NOW` |
| ClickHouse | high-concurrency analytical SLO failure | DuckDB + layout/pruning/materialized datasets | until benchmark says no, simpler path wins | `DEFER/BLOCKED_ON_MEASUREMENT` |
| Redis | control/read latency or hot cache load | PostgreSQL + bounded in-process/rebuildable cache | no demonstrated reduction now; adds service/credentials | `DEFER_OR_REJECT_REQUIRED_NOW` |
| Kafka/broker | durable fan-out + independent offsets + broker replay | AIFE Work/Publication/Storage claims/leases/fencing | no demonstrated need; would add operator surfaces | `DEFER_OR_REJECT_REQUIRED_NOW` |
| OpenSearch/full-text | high-scale text search SLO | PostgreSQL FTS or batch rebuildable index | simpler path available until measured gap | `DEFER` |
| Vector database | high-scale approximate/semantic vector retrieval | store vectors/artifacts in existing durable substrate, batch/embedded retrieval initially | no proven workload; service adds actions | `DEFER` |

No mechanism is promoted because it is “industry standard”, “enterprise-grade”, “scalable” or
“future-proof”.

## 25. Material findings

### FIND-001 — F5R is a real program gate

- Priority: `P1`
- Claim: F5 requires a backend decision gate after F4; the block is architectural, not a source bug.
- Evidence: F4 says backend/vendor/warehouse unselected, F5 not started; root AGENTS marks
  high-cardinality WARM/COLD blocked on versioned decision.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY`
- Risk: F5 could hard-code a physical topology without cross-AIFE evidence.
- Simpler-Alternative: start F5 with an arbitrary backend.
- Why-Simpler-Is-Or-Is-Not-Sufficient: insufficient; it would violate the explicit decision block.
- Impact-On-Agent-Actions: one research/owner gate now prevents repeated backend redesign later.
- Impact-On-Engineer-Actions: avoids implementation/redeployment churn.
- Decision-Consequence: `F5R_GATE_REQUIRED=YES`.
- Governance-Consequence: Program Map requires minimal F4→F5R→F5 amendment after consolidation.
- F5/F5M-Consequence: both remain blocked.

### FIND-002 — Semantic authority must remain outside physical storage

- Priority: `P1`
- Claim: storage backend may not become ETH/domain semantic authority.
- Evidence: root AGENTS + F4 domain/server authority split.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY`
- Risk: migration would rewrite identities/resolution semantics.
- Simpler-Alternative: expose bucket/table/path as consumer contract.
- Why-Simpler-Is-Or-Is-Not-Sufficient: operationally easy but violates portability and creates a
  second route.
- Impact-On-Agent-Actions: agents continue requesting semantics, not storage locators.
- Impact-On-Engineer-Actions: backend migration remains adapter/profile work.
- Decision-Consequence: all physical choices sit behind existing storage/access contracts.
- Governance-Consequence: stable bindings belong in Server contracts, not new domain authority.
- F5/F5M-Consequence: migration must preserve domain identity and readback semantics.

### FIND-003 — AIFE-wide measured scale baseline is insufficient

- Priority: `P1`
- Claim: no trustworthy all-class capacity/performance baseline was obtained.
- Evidence: missing bytes/growth/ingest/object/scan/restore measurements enumerated above.
- Evidence-Class: `UNRESOLVED MEASUREMENT`
- Risk: premature performance services become architecture by assumption.
- Simpler-Alternative: use vendor benchmarks or guessed growth.
- Why-Simpler-Is-Or-Is-Not-Sufficient: forbidden; not representative AIFE evidence.
- Impact-On-Agent-Actions: future qualification has a finite benchmark matrix.
- Impact-On-Engineer-Actions: avoids deploying services before a bottleneck exists.
- Decision-Consequence: `MEASURED_BASELINE=INSUFFICIENT`.
- Governance-Consequence: optional acceleration remains conditional.
- F5/F5M-Consequence: base lifecycle can proceed only after owner decision; acceleration cannot be
  mandatory on current evidence.

### FIND-004 — Object/blob + Parquet is the simplest credible bulk substrate

- Priority: `P1`
- Claim: high-cardinality and large analytical tables fit immutable object/blob storage with Parquet.
- Evidence: AIFE storage-portability boundary, Parquet official format, F5 P2 lifecycle needs.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY + EXTERNAL PRIMARY EVIDENCE + INFERENCE`
- Risk: per-event objects or universal relational storage increase operational/scan cost.
- Simpler-Alternative: plain files without structured columnar batching.
- Why-Simpler-Is-Or-Is-Not-Sufficient: insufficient for efficient broad analytical scans and
  standardized metadata/pruning.
- Impact-On-Agent-Actions: stable file format/read-set.
- Impact-On-Engineer-Actions: bounded batching instead of per-event persistence.
- Decision-Consequence: object/blob + immutable Parquet required in first-agent candidate.
- Governance-Consequence: physical profile should be captured by owner ADR/contracts.
- F5/F5M-Consequence: P2 lifecycle should seal deterministic Parquet generations.

### FIND-005 — Versioned AIFE manifests are sufficient metadata first

- Priority: `P1`
- Claim: a bounded manifest over immutable objects closes generation/read-set/discovery/readback
  needs without proving a full table-format requirement.
- Evidence: existing Server Storage/Publication contracts and deterministic identity rules.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`
- Risk: directory listing or mutable “latest” state cannot pin reproducible inputs.
- Simpler-Alternative: raw object listing.
- Why-Simpler-Is-Or-Is-Not-Sufficient: listing does not prove exact immutable membership/generation.
- Impact-On-Agent-Actions: one manifest resolves a complete physical read-set.
- Impact-On-Engineer-Actions: no separate catalog service at initial stage.
- Decision-Consequence: manifests required now.
- Governance-Consequence: stable manifest binding belongs in physical Server contract/profile.
- F5/F5M-Consequence: readback and migration operate on pinned generations.

### FIND-006 — Iceberg is not proven mandatory

- Priority: `P1`
- Claim: Iceberg features are relevant but current risks can be closed by simpler manifest/fencing
  mechanisms.
- Evidence: Iceberg official snapshot/manifest/concurrency model; no measured AIFE need for its full
  transactional table metadata.
- Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + UNRESOLVED MEASUREMENT + INFERENCE`
- Risk: adopting now adds table/catalog lifecycle without evidence.
- Simpler-Alternative: immutable Parquet + AIFE manifests; transactional PostgreSQL metadata if needed.
- Why-Simpler-Is-Or-Is-Not-Sufficient: currently sufficient; failure has not been proven.
- Impact-On-Agent-Actions: fewer metadata/catalog concepts to discover.
- Impact-On-Engineer-Actions: fewer upgrade/recovery surfaces.
- Decision-Consequence:
  `ICEBERG_DECISION=DEFER_PENDING_PROVEN_TRANSACTIONAL_TABLE_METADATA_NEED`.
- Governance-Consequence: owner ADR should name the expansion trigger.
- F5/F5M-Consequence: F5 does not require Iceberg.

### FIND-007 — PostgreSQL should be control plane, not default P2 warehouse

- Priority: `P1`
- Claim: PostgreSQL is required for transactional control/sparse metadata but not the default
  multi-terabyte raw store.
- Evidence: AIFE Work/Publication needs; PostgreSQL MVCC; bulk workload shape.
- Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + INFERENCE`
- Risk: universal DB couples transaction, scan, backup and capacity domains.
- Simpler-Alternative: PostgreSQL for all bytes.
- Why-Simpler-Is-Or-Is-Not-Sufficient: fewer technologies superficially, but larger operational
  coupling and no proven advantage for P2 scans.
- Impact-On-Agent-Actions: one DB for control semantics.
- Impact-On-Engineer-Actions: bulk growth handled independently.
- Decision-Consequence: exact `POSTGRESQL_ROLE` above.
- Governance-Consequence: ADR/profile must constrain the role.
- F5/F5M-Consequence: P2 raw lands in object/Parquet, not default PostgreSQL tables.

### FIND-008 — PIT correctness is not storage time travel

- Priority: `P1`
- Claim: reproducibility requires known-at cutoff, source revision/sequence, pinned generation and
  pinned method/model version.
- Evidence: Data Bridge revision/gap authority + PIT research contract.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY + INFERENCE`
- Risk: backtest uses information unavailable at historical decision time.
- Simpler-Alternative: pin only a database snapshot timestamp.
- Why-Simpler-Is-Or-Is-Not-Sufficient: snapshot cannot encode missing source/knowledge/model semantics.
- Impact-On-Agent-Actions: explicit replay contract.
- Impact-On-Engineer-Actions: compaction/projection changes become non-semantic.
- Decision-Consequence: exact PIT formula is mandatory.
- Governance-Consequence: stable PIT bindings need owner contract/standard alignment.
- F5/F5M-Consequence: physical generations must be pinnable and retained per policy.

### FIND-009 — Backtests scale through independent AIFE work, not a shared DuckDB database

- Priority: `P1`
- Claim: embedded DuckDB per worker is the simpler horizontal analytical model.
- Evidence: DuckDB official Parquet/concurrency docs + AIFE Work identity/fencing.
- Evidence-Class: `EXTERNAL PRIMARY EVIDENCE + REPOSITORY/AIFE AUTHORITY + INFERENCE`
- Risk: shared analytical DB becomes a new coordination/authority surface.
- Simpler-Alternative: per-worker embedded engine over immutable inputs.
- Why-Simpler-Is-Or-Is-Not-Sufficient: sufficient for current work-unit model.
- Impact-On-Agent-Actions: same Work/retry mechanics for 1 or N workers.
- Impact-On-Engineer-Actions: no OLAP cluster required initially.
- Decision-Consequence: `DUCKDB_EMBEDDED_PER_WORKER`.
- Governance-Consequence: horizontal seams should be preserved in execution/work contracts.
- F5/F5M-Consequence: storage layout must support partition pruning/parallel independent reads.

### FIND-010 — ClickHouse is an acceleration projection only

- Priority: `P2`
- Claim: ClickHouse cannot be required without a representative concurrent analytical benchmark gap.
- Evidence: no measured AIFE OLAP SLO failure.
- Evidence-Class: `UNRESOLVED MEASUREMENT + INFERENCE`
- Risk: premature service becomes accidental canonical store.
- Simpler-Alternative: Parquet + DuckDB + bounded materialized datasets.
- Why-Simpler-Is-Or-Is-Not-Sufficient: no evidence it fails yet.
- Impact-On-Agent-Actions: canonical reads stay independent of projection.
- Impact-On-Engineer-Actions: no extra OLAP service until justified.
- Decision-Consequence:
  `CLICKHOUSE_DECISION=DEFER_PENDING_REPRESENTATIVE_BENCHMARK_TRIGGER`.
- Governance-Consequence: ADR should preserve rebuildable-only boundary.
- F5/F5M-Consequence: no ClickHouse prerequisite.

### FIND-011 — Cache/broker/search/vector services are not required now

- Priority: `P2`
- Claim: Redis, Kafka, OpenSearch and vector DB lack a demonstrated current workload gap.
- Evidence: existing Server mechanisms + absence of measured requirement.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY + UNRESOLVED MEASUREMENT + INFERENCE`
- Risk: extra services, credentials, backups, monitoring and recovery procedures.
- Simpler-Alternative: PostgreSQL, in-process/rebuildable cache, AIFE Work/Publication, PostgreSQL FTS,
  batch/embedded retrieval.
- Why-Simpler-Is-Or-Is-Not-Sufficient: currently sufficient until a measured gap appears.
- Impact-On-Agent-Actions: fewer service-specific discovery routes.
- Impact-On-Engineer-Actions: smaller operational footprint.
- Decision-Consequence: defer/reject-required-now dispositions above.
- Governance-Consequence: expansion triggers, not immediate owner bindings.
- F5/F5M-Consequence: none are F5 prerequisites.

### FIND-012 — Owner architecture publication must follow dual-agent consolidation

- Priority: `P1`
- Claim: first-agent evidence cannot publish final architecture.
- Evidence: P1 dual-agent canonical investigate policy and current task boundary.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY`
- Risk: local candidate is mistaken for owner authority.
- Simpler-Alternative: accept this artifact directly.
- Why-Simpler-Is-Or-Is-Not-Sufficient: violates blind-review policy.
- Impact-On-Agent-Actions: one independent second run, then consolidation.
- Impact-On-Engineer-Actions: no implementation before conflict resolution.
- Decision-Consequence: `SECOND_BLIND_REVIEW_REQUIRED=YES`.
- Governance-Consequence: ADR/STD/CONTRACT/Program Map mutations remain forbidden now.
- F5/F5M-Consequence: blocked until second artifact + consolidation + owner publication.

### FIND-013 — ChatGPT/GPT suffix is task-scoped, not global policy

- Priority: `P1`
- Claim: `_chatgpt-gpt` is explicitly owner-authorized for this task but is not yet globally
  published AIFE naming authority.
- Evidence: current owner correct-course authority.
- Evidence-Class: `REPOSITORY/AIFE AUTHORITY` for canonical naming gap +
  `TASK-SCOPED OWNER AUTHORIZATION`.
- Risk: future investigations silently treat a bounded exception as global standard.
- Simpler-Alternative: mutate naming governance before this artifact.
- Why-Simpler-Is-Or-Is-Not-Sufficient: owner explicitly removed that change as a predecessor;
  follow-up remains required.
- Impact-On-Agent-Actions: current artifact can materialize without blocking.
- Impact-On-Engineer-Actions: global synchronization remains a separate three-file follow-up.
- Decision-Consequence: current filename is valid only under bounded authorization.
- Governance-Consequence:
  `GLOBAL_CHATGPT_AGENT_IDENTITY_GOVERNANCE=AMEND_REQUIRED`.
- F5/F5M-Consequence: no physical implementation consequence; governance hygiene only.

## 26. Minimum initial stack

First-agent candidate:

```text
MINIMUM_INITIAL_STACK=
PostgreSQL durable control plane
+ capability-based object/blob storage
+ immutable Parquet
+ versioned AIFE manifests
+ embedded DuckDB per worker
```

Exact required-now disposition:

```text
CONTROL_STATE_BACKEND=
REQUIRED_NOW: PostgreSQL

BULK_OBJECT_BACKEND_CLASS=
REQUIRED_NOW: capability-based durable object/blob storage

TABULAR_FILE_FORMAT=
REQUIRED_NOW: Parquet for large tabular datasets

METADATA_CATALOG_MODEL=
REQUIRED_NOW: versioned AIFE manifests
DEFER: separate transactional catalog service
OPTIONAL_LATER: PostgreSQL-backed transactional metadata when proven

ICEBERG=
DEFER

BACKTEST_QUERY_ENGINE=
REQUIRED_NOW: embedded DuckDB per worker

INTERACTIVE_OLAP=
DEFER dedicated service; use DuckDB/bounded materialized data first

CACHE=
DEFER_OR_REJECT_REQUIRED_NOW

MESSAGE_BROKER=
DEFER_OR_REJECT_REQUIRED_NOW

FULL_TEXT_SEARCH=
DEFER dedicated service; PostgreSQL FTS/batch projection first

VECTOR_SEARCH=
DEFER

MODEL_ARTIFACT_STORAGE=
REQUIRED_NOW: object/blob for large immutable artifacts + PostgreSQL metadata

NEWS_RAW_STORAGE=
permitted raw snapshots in object/blob; metadata/revisions in PostgreSQL

PIT_SNAPSHOT_BINDING=
REQUIRED_NOW: manifest/read-set + cutoff + revision + method/model version

COMPACTION_MODEL=
asynchronous identity/provenance-preserving non-semantic rewrite

BACKUP_MODEL=
backend-appropriate backups + separate canonical object/control evidence

RESTORE_MODEL=
clean-environment restore + reconciliation/readback proof

HA_MODEL=
seams required now; exact topology blocked on RPO/RTO and deployment evidence
```

## 27. Deferred mechanisms and expansion triggers

| Mechanism | Current disposition | Expansion trigger |
| --- | --- | --- |
| transactional metadata layer | `DEFER` | manifest pointer/multi-writer operations require atomic multi-object state beyond bounded registration |
| Iceberg | `DEFER` | proven concurrent table commits, schema/partition evolution burden, snapshot/catalog scale or hard multi-engine table semantics |
| ClickHouse | `DEFER/BLOCKED_ON_MEASUREMENT` | owner-defined concurrent OLAP SLO missed after simpler layout/query optimizations |
| Redis | `DEFER` | measured hot-read/coordination load cannot meet SLO with PG + local cache |
| Kafka/broker | `DEFER` | durable fan-out + independent offsets/replay across consumer fleets becomes a real requirement |
| OpenSearch | `DEFER` | text-search corpus/query SLO exceeds PG FTS/batch projection |
| vector DB | `DEFER` | real large-scale vector retrieval workload and SLO established |
| multi-node PostgreSQL HA | `DEFER topology` | owner RPO/RTO and failure model require it |
| self-hosted object cluster | `DEFER product choice` | deployment/cost/control requirements reject managed/simple substrate |

Future seams are required; future services are not.

## 28. ETH P2 / F5 implications

Existing F5 dependency:

```text
ETH-MARKET-DATA-P2-OBJECT-PARQUET-LIFECYCLE-AUTHORITY-V1
```

First-agent physical candidate:

```text
P2_BACKEND_CLASS=
CAPABILITY_BASED_DURABLE_OBJECT_OR_BLOB_STORAGE

P2_OBJECT_IDENTITY=
DETERMINISTIC_FROM_LOGICAL_PARTITION_GENERATION_AND_CONTENT_BINDING;
NOT_CONSUMER_SEMANTIC_IDENTITY

P2_PARTITION_MODEL=
DOMAIN_SERIES/TIME_BUCKET_AS_PHYSICAL_LAYOUT_INPUT
WITH_LAYOUT_VERSION;
EXACT_CARDINALITY_REQUIRES_F5_QUALIFICATION

P2_FILE_LAYOUT=
BOUNDED_BATCHED_PARQUET;
ONE_EVENT_PER_OBJECT_FORBIDDEN

P2_SEAL_MODEL=
WRITE
→ SEAL
→ INDEPENDENT_READBACK
→ VERSIONED_MANIFEST
→ CANONICAL_REGISTRATION
→ ACK

P2_MANIFEST_OR_TABLE_METADATA_MODEL=
VERSIONED_AIFE_MANIFESTS_REQUIRED_NOW;
ICEBERG_DEFERRED

P2_MULTI_WRITER_MODEL=
DISJOINT_DETERMINISTIC_WORK/PARTITION_OWNERSHIP
+ DURABLE_CLAIM/LEASE/FENCING
+ CONFLICT_DETECTION

P2_DEDUP_MODEL=
STABLE_LOGICAL_INPUT/CONTENT_IDENTITY
+ IDEMPOTENT_PUBLICATION

P2_CONFLICT_MODEL=
SAME_TARGET_DIFFERENT_CONTENT_FAIL_CLOSED

P2_COMPACTION_MODEL=
ASYNC_IDENTITY_PRESERVING_NEW_GENERATION

P2_READBACK_MODEL=
INDEPENDENT_CONTENT/MEMBERSHIP/PROVENANCE_VERIFICATION

P2_BACKUP_MODEL=
OBJECT_AND_CONTROL_BACKUP_WITHOUT_TREATING_REPLICATION_AS_BACKUP

P2_RESTORE_MODEL=
CLEAN_ENVIRONMENT_RESTORE
+ MANIFEST/OBJECT RECONCILIATION
+ ACCESS/READBACK PROOF

P2_MIGRATION_BOUNDARY=
FORWARD-ONLY_NEW_P2_PROFILE_FIRST;
F5M_HANDLES_EXISTING_CORPUS_CUTOVER_SEPARATELY

P2_F5_ENTRY_CRITERIA=
DUAL_AGENT_CONSOLIDATION
+ OWNER_ARCHITECTURE_PUBLICATION
+ REQUIRED_STD/CONTRACT/PROGRAM_MAP_BINDINGS
+ REPRESENTATIVE_F5_QUALIFICATION_PLAN
```

This research does not implement or activate P2.

## 29. Owner governance disposition

The following is a **first-agent candidate**, not final owner authority:

```text
ADR_DISPOSITION=
CREATE_REQUIRED_AFTER_DUAL_AGENT_CONSOLIDATION

STANDARD_DISPOSITION=
AMEND_OR_BIND_EXISTING_DATA_STANDARDS_AFTER_CONSOLIDATION
NO_NEW_BROAD_STANDARD_REQUIRED_BY_FIRST_RUN

ARTIFACT_CONTRACT_DISPOSITION=
AMEND_REQUIRED_AFTER_CONSOLIDATION_FOR_STABLE_SEMANTIC_BINDINGS

PROGRAM_MAP_DISPOSITION=
AMEND_REQUIRED_AFTER_DUAL_AGENT_CONSOLIDATION

CHATGPT_AGENT_NAMING_GOVERNANCE_DISPOSITION=
AMEND_REQUIRED
```

Canonical AIFE snapshot registry confirms these data standards exist as draft `0.1.0`:

- `STD-DATA-MGMT-001`;
- `STD-DATA-SCHEMA-001`;
- `STD-DATA-MIGRATION-001`;
- `STD-DATA-VALIDATION-001`;
- `STD-DATA-RETENTION-001`;
- `STD-DATA-BACKUP-001`.

Existing staged Server contracts include:

- `CONTRACT-SERVER-WORK-001`;
- `CONTRACT-SERVER-EXECUTION-001`;
- `CONTRACT-SERVER-PUBLICATION-001`;
- `CONTRACT-SERVER-STORAGE-001`;
- `CONTRACT-SERVER-ACCESS-001`.

### Диспозиция артефактов владельца

| Requirement | Correct Owner Class | Existing Artifact | Disposition | Why | Blocks F5R/F5? |
| --- | --- | --- | --- | --- | --- |
| one-time backend layering/topology decision | ADR | no matching final backend ADR found in canonical snapshot | `NEW_REQUIRED` after consolidation | architecture choice is AIFE-specific and one-time | F5 yes; current first-agent F5R no |
| data placement / authority-vs-projection | Standard | `STD-DATA-MGMT-001`, `STD-DATA-SCHEMA-001` draft | `AMEND_REQUIRED` or explicit binding after consolidation | reusable rule, not just ETH | F5 yes |
| migration/cutover evidence | Standard | `STD-DATA-MIGRATION-001` draft | `AMEND_REQUIRED` or bind | F5M needs identity/reconciliation boundary | F5M yes |
| validation/readback | Standard + Server contract | `STD-DATA-VALIDATION-001`, `CONTRACT-SERVER-STORAGE-001` | `AMEND_REQUIRED`/bind stable physical profile semantics | preserve independent readback and generation proof | F5 yes |
| retention/compaction | Standard | `STD-DATA-RETENTION-001` draft | `AMEND_REQUIRED` if current text lacks immutable generation/compaction rule | reusable lifecycle rule | F5/F5M yes |
| backup/restore | Standard | `STD-DATA-BACKUP-001` draft | `AMEND_REQUIRED` if clean restore proof not fully bound | backup is not restore proof | F5 qualification yes |
| work/publication/storage/access profile binding | Artifact Contract | Server contract family listed above | `AMEND_REQUIRED` after consolidation | named bindings between stable artifacts/profile | F5 yes |
| F4→F5R→F5 program gate | Program Map | existing program authority | `AMEND_REQUIRED` after consolidation | preserves correct predecessor relation | F5 yes |
| ChatGPT/GPT per-agent suffix | Prompt governance | three canonical prompt/coordination files | `AMEND_REQUIRED` follow-up | bounded exception is not global policy | no physical F5 block |

No Standard, ADR, Contract, registry or Program Map is mutated in this run.

## 30. ChatGPT naming governance finding

Current task-scoped identity:

```text
EXECUTION_TOOL=
ChatGPT

MODEL_FAMILY=
GPT

CURRENT_TASK_SUFFIX_STATUS=
EXPLICIT_OWNER_AUTHORIZED

TASK_SCOPED_AGENT_SUFFIX=
_chatgpt-gpt

GLOBAL_AIFE_SUFFIX_STATUS=
NOT_YET_PUBLISHED

GLOBAL_CHATGPT_AGENT_IDENTITY_GOVERNANCE=
AMEND_REQUIRED
```

Proposed exact synchronization targets for a separate owner-governance task:

```text
.github/prompts/includes/artifact-naming.md
.github/prompts/investigate.prompt.md
.github/agent-coordination.md
```

This finding does **not** authorize mutation of those files here and does not imply the suffix is
globally valid for future AIFE investigations.

## 31. Program Map disposition

First-agent disposition:

```text
PROGRAM_MAP_AMENDMENT=
REQUIRED_AFTER_DUAL_AGENT_CONSOLIDATION
```

Minimal semantic amendment only:

```text
F4
→ F5R
→ F5
```

F5R remains part of `aife-server-data-foundation`; no parallel roadmap is created.
F5M/F6/F7/F8 remain downstream as already modeled. This artifact does not edit Program Map.

## 32. Пакет решения владельца

This section is decision evidence/candidate, **not owner acceptance**.

```text
Decision-Scope=
AIFE Server/Data Foundation physical storage, analytics, PIT/backtesting,
horizontal scaling and ETH P2/F5 backend profile

Chosen-Minimum-Architecture=
PostgreSQL durable control plane
+ capability-based object/blob storage
+ immutable Parquet
+ versioned AIFE manifests
+ embedded DuckDB per worker

Rejected-Alternatives=
PostgreSQL as default multi-TB raw market warehouse
shared distributed DuckDB database
one-event-per-object storage
physical storage as semantic authority

Deferred-Mechanisms=
Iceberg
ClickHouse
Redis
Kafka/broker
OpenSearch
vector database
product-specific HA topology

Required-Now=
durable transactional control
stable work/claim/lease/fencing
immutable bulk objects
batched Parquet
versioned manifest/read-set
independent readback
PIT cutoff/revision/method pinning
per-worker analytical execution
idempotent publication
backup→restore proof contract

Required-Later-Only-On-Trigger=
transactional table metadata
Iceberg
OLAP projection
network cache
broker
dedicated search/vector service
multi-node HA topology

Evidence-Basis=
Data Bridge/WIP F4 authority
canonical AIFE governance snapshot
official Binance/Coinbase/Deribit protocol docs
official Parquet/Iceberg/DuckDB/PostgreSQL docs

Known-Unknowns=
AIFE-wide measured bytes/growth
ingest distribution
object/row/partition distribution
concurrent scan requirement
compaction amplification
restore throughput
numeric RPO/RTO

Residual-Risks=
first-agent-only architecture confidence
unmeasured performance/capacity
deployment-specific object/HA product selection
future multi-writer metadata pressure

Migration-Implications=
F5 establishes forward physical profile;
F5M separately reconciles legacy corpus/cutover;
no semantic identity rewrite

P2-Implications=
object/blob + Parquet + manifest lifecycle;
deterministic batching/sealing/readback;
Iceberg not prerequisite

Horizontal-Scaling-Implications=
1→N→1 through WorkId/claim/lease/fencing/idempotency;
no node-local semantic authority

Backtest-Implications=
pinned immutable generation + PIT cutoff + DuckDB per worker;
stateful time-sharding forbidden without checkpoint semantics

Operational-Complexity=
minimum durable service classes first;
optional services only after measured trigger

Owner-Artifact-Changes-Required=
ADR after dual consolidation;
bind/amend existing data standards;
amend stable Server contracts as needed;
minimal Program Map amendment;
separate global ChatGPT naming governance follow-up

Program-Map-Change-Required=
YES_AFTER_DUAL_AGENT_CONSOLIDATION

DEV-TZ-Readiness=
NO_FIRST_AGENT_ONLY
```

## 33. Required second-agent review

This ChatGPT/GPT run is one independent evidence stream only.

```text
FIRST_AGENT_IDENTITY=
_chatgpt-gpt

FIRST_AGENT_RESEARCH=
COMPLETE

SECOND_BLIND_REVIEW_REQUIRED=
YES

SECOND_AGENT_MUST_BE_GENUINELY_INDEPENDENT=
YES

SECOND_CHATGPT_SESSION_WITH_SAME_IDENTITY_COUNTS_AS_SECOND_BLIND_IDENTITY=
NO

_r2_COUNTS_AS_SECOND_IDENTITY=
NO

OWNER_ARCHITECTURE_PUBLICATION_ALLOWED=
NO

CONSOLIDATION_ALLOWED=
NO_UNTIL_SECOND_INDEPENDENT_ARTIFACT

DEV_TZ_ALLOWED=
NO

F5_ALLOWED=
NO

F5M_ALLOWED=
NO
```

The second agent must use the same `Scope-Slug=aife-server-data-foundation` and
`Topic-Slug=data-backend-architecture` while remaining blind to this per-agent artifact until the
canonical consolidation stage.

## Итоговое решение (контракт)

### Runtime Disposition
- Runtime-Oriented: yes
- Effective Closure: no
- Downstream Disposition: `Blocked`
- Why findings-only is insufficient: первый per-agent findings layer не может авторизовать physical backend, F5 runtime lifecycle или DEV_TZ без независимого P1 blind review, consolidation и owner publication.
- Required next contour: `Scope-Slug=aife-server-data-foundation`, `Topic-Slug=data-backend-architecture`, genuinely independent second `Mode=single` research run.
- Materialization target: будущий owner-published backend architecture/profile и последующий F5 `DEV_TZ`; в текущем run `N/A` как runtime delivery.
- Blocker, if any: `SECOND_BLIND_REVIEW_REQUIRED`

### Materialization Disposition
- Program Root: `AIFE_SERVER_DATA_FOUNDATION`
- Wave / Topic: `F5R / data-backend-architecture`
- Program-Setup Disposition: `blocker`
- Execution Root: `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/`
- Physical Use Class: `control-plane-evidence-only`
- Operational Surface Target: `N/A`
- Physical Integration Target: будущий F5 high-cardinality physical storage lifecycle; не materialized этим артефактом.
- Current Status: `blocked`
- Readiness Threshold Met: `no`
- DEV_TZ Outcome: `blocked`
- Delivery Claim Allowed: `no`
- Required Next Prompt: canonical `.github/prompts/investigate.prompt.md` with same scope/topic and genuinely independent execution context.
- Required Next Artifact: independent second per-agent `RESEARCH` artifact whose exact date and agent suffix are resolved from that genuinely independent execution context by canonical naming rules.
- Blocker: `SECOND_BLIND_REVIEW_REQUIRED`
- Why findings-only is forbidden here: backend/profile changes affect runtime storage, execution, PIT and F5; one local-candidate evidence file cannot become implementation authority.
- Why control-plane-only is not delivery: no production storage backend, server runtime, corpus migration, P2 activation or F5 implementation is created by this evidence artifact.

### 1. Статус темы
- Исследование по теме: ЗАКРЫТО для first-agent run; dual-agent topic НЕ ЗАКРЫТ
- Состояние волны: ЧАСТИЧНО
- Переход к `DEV_TZ`: ЗАПРЕЩЁН
- Архитектурный статус: `local-candidate` (локальный кандидат)

### 2. Граница контекстного пакета
- `Minimum-Packet`: canonical AIFE governance snapshot + fresh WIP/F4 authority + relevant Server contracts/data standards + official primary exchange/storage/engine evidence + this per-agent findings artifact.
- `Expansion-Trigger`: genuinely independent second blind research, then explicit consolidation; implementation context expands only after owner publication.
- `Expansion-Authority`: canonical dual-agent investigate/consolidation route and owner authorization.

### 3. Граница полномочий
- Переписывание маршрута владельца (`owner-route`): ЗАПРЕЩЕНО
- Собственная иерархия истины (`truth hierarchy`): ЗАПРЕЩЕНО
- Подмена опорного репозиторного доказательства (`repo-proof core`): ЗАПРЕЩЕНА

### 4. Масштабируемость решения
- `Scaling-Class`: ЛОКАЛЬНЫЙ КАНДИДАТ
- Ограничение локального удобства: design preserves 1→N→1 seams, but architecture confidence is limited to one independent agent run and lacks representative AIFE-wide performance/restore measurements.

### 5. Решение у владельца
- `STD`: НЕ ОПРЕДЕЛЁН
- `ADR`: УСЛОВНО ДОПУСТИМ
- `CONTRACT`: ВСПОМОГАТЕЛЬНЫЙ

### 6. Блокеры
- Блокеры исследования: НЕТ для завершения first-agent research; dual-agent closure still requires a second independent artifact.
- Блокеры решения: `SECOND_BLIND_REVIEW_REQUIRED`; owner publication cannot occur before consolidation.
- Ограничение перехода к `DEV_TZ`: independent second research → canonical consolidation → owner ADR/STD/CONTRACT/Program Map publication and read-back must precede any DEV_TZ authorization.

### 7. Обязательный следующий шаг

A) Следующее исследование:
- `Topic-Slug`: `data-backend-architecture`
- `Scope-Slug`: `aife-server-data-foundation`
- Причина: `OBTAIN_GENUINELY_INDEPENDENT_SECOND_AGENT_RESEARCH` для обязательного P1 blind review без чтения текущего per-agent artifact.

### 8. Явные запреты
- `OWNER_ARCHITECTURE_PUBLICATION`
- `ADR_PUBLICATION`
- `STANDARD_MUTATION`
- `ARTIFACT_CONTRACT_MUTATION`
- `PROGRAM_MAP_MUTATION`
- `DEV_TZ`
- `F5`
- `F5M`
- имитация второго independent review через второй ChatGPT/GPT session той же identity
- использование `_r2` как второй agent identity

```text
ARCHITECTURE_STATUS=
local-candidate

FIRST_AGENT_RESEARCH=
COMPLETE

FIRST_AGENT_ARTIFACT=
MATERIALIZED

SECOND_BLIND_REVIEW_REQUIRED=
YES

OWNER_ARCHITECTURE_PUBLICATION_ALLOWED=
NO

CONSOLIDATION_ALLOWED=
NO_UNTIL_SECOND_INDEPENDENT_ARTIFACT

DEV_TZ_ALLOWED=
NO

F5_ALLOWED=
NO

F5M_ALLOWED=
NO

ALLOWED_NEXT_PRACTICAL_STEP=
OBTAIN_GENUINELY_INDEPENDENT_SECOND_AGENT_RESEARCH

FORBIDDEN_NEXT_PRACTICAL_STEPS=
OWNER_ARCHITECTURE_PUBLICATION
ADR_PUBLICATION
STANDARD_MUTATION
ARTIFACT_CONTRACT_MUTATION
PROGRAM_MAP_MUTATION
DEV_TZ
F5
F5M
```
