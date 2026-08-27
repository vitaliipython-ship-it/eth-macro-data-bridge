---
title: "RESEARCH: aife-server-data-foundation — independent-second-run"
status: active
owner: Architecture Lead
created: 2026-08-27
updated: 2026-08-27
review_cycle_days: 30
next_review_due: 2026-09-26
category: architecture
doc_type: analysis
language: ru
tags: [research, independent-second-run, server, data, storage, analytics, backtest, f5r]
---

## 1. Краткий вывод

Самостоятельный вывод этого run: F4 уже закрыл **семантическую** границу между ETH Data Bridge и generic Server, а F5 должен закрыть прежде всего **physical lifecycle** high-cardinality P2 без переноса market semantics в storage/execution plane. На pinned commit нет измерений, которые оправдывают standing OLAP, message broker, shared multi-node control DB или open table format как обязательные компоненты F5.

Минимальный initial architecture candidate, который не требует будущей смены semantic contracts:

1. **shared durable object/blob storage capability class** для immutable bulk bytes, с checksums, conditional create/update, independent readback, inventory/listing, multipart, encryption, lifecycle и clean-restore qualification;
2. **Parquet** для regular market history, features, bulk analytical/training/backtest tables и иных columnar scan workloads; native/blob representation остаётся допустимой для данных, которые нельзя корректно нормализовать в tabular form без потери source evidence;
3. **bounded/versioned immutable publication manifests** + transactional pointer/registration в control state; custom metadata жёстко ограничено и не должно перерасти в самодельный table format;
4. **SQLite/WAL как current simplest single-node control substrate** для F5 qualification; **PostgreSQL — best fit, но required later**, когда появляется реальная shared multi-node control plane с concurrent claims/leases/fencing/publication metadata;
5. **embedded DuckDB** — хороший analytical/backtest engine поверх Parquet/object storage без standing service; он не обязан быть частью closure самого F5 physical-storage checkpoint;
6. **ClickHouse, Iceberg, Redis/cache, broker, search и vector DB** — не initial requirements. Для каждого задан measured/contract trigger.

Ключевой PIT-вывод: storage-native snapshots/time travel недостаточны для replay correctness. Реплей должен быть привязан к `effective_at`, `known_at`, provider/source revision, stream sequence/update identity, exact generation/read-set, method/model/strategy versions и replay cutoff. Это особенно важно потому, что exchange streams имеют explicit sequence/gap semantics, а provider bulk archives могут позднее быть исправлены и заменены.

**Architecture status:** `local-candidate`. Это research artifact, не owner decision и не разрешение на F5/F5M implementation.

## 2. Research provenance

### 2.1 Independence boundary

`INDEPENDENT_RESEARCH_CONTEXT_COMPROMISED=NO`.

Этот run не использовал previous research artifacts, summaries, critiques, first-run technology verdicts или project-memory conclusions по этой Task-Family. Входы были ограничены:

- verified canonical AIFE snapshot;
- pinned repository authority на `2b82c75a67ed7ce5cd87cae2ccf02f09677d200c` / tree `2615dcd21570f0816be39c574b3b9f8ef1c1bc16`;
- canonical AIFE governance из snapshot;
- official external primary technical documentation;
- выводы текущего run.

Историческое упоминание направления `OBJECT_BLOB_PLUS_PARQUET` внутри pinned ADR не принималось как verdict: ADR является частью разрешённой pinned authority, но технологическое решение текущего run получено заново после data/workload/temporal/failure/scale анализа.

### 2.2 Evidence classes

- **MEASURED** — фактически измерено в disposable/local research environment текущего run.
- **REPOSITORY_DERIVED** — точное число или факт, вычисленный из pinned repository bytes/manifest.
- **PROVIDER_DOCUMENTED** — прямо заявлено официальной документацией внешнего provider/technology.
- **ESTIMATED** — аналитическая оценка, не выдаваемая за measurement.
- **UNKNOWN** — evidence в pinned authority отсутствует; значение не выдумывается.

### 2.3 Repository primary evidence

Все ссылки ниже логически закреплены за exact commit `2b82c75a67ed7ce5cd87cae2ccf02f09677d200c`:

- `AGENTS.md`
- `AIFE/README.md`
- `AIFE/staging/docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md`
- `AIFE/staging/docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f4-eth-data-bridge-integration/README.md`
- `AIFE/staging/genome/adr/data/ADR-DATA-FOUNDATION-001.md`
- `AIFE/staging/genome/contracts/server/CONTRACT-SERVER-{WORK,SCHEDULING,EXECUTION,PUBLICATION,STORAGE,ACCESS}-001.md`
- `history/manifest.json`, `history/release-manifest.json`, `data/manifest.json`, `derivatives/manifest.json`, `options/manifest.json`, `liquidity/manifest.json`.

### 2.4 Official external primary-source register

| Subject | Official primary source | Use in this research |
|---|---|---|
| Binance Spot diff-depth reconstruction | <https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md> | `U/u/lastUpdateId`, snapshot+delta reconstruction, gap/resync |
| Binance public bulk archive | <https://github.com/binance/binance-public-data/blob/master/README.md> | daily/monthly archives, `.CHECKSUM`, archive replacements after corrections |
| Deribit order-book subscription | <https://docs.deribit.com/subscriptions/orderbook/bookinstrument_nameinterval> | full first snapshot, incremental updates, `change_id/prev_change_id` |
| Deribit notifications/gap handling | <https://docs.deribit.com/articles/notifications> | missed-update detection and re-subscribe/resync |
| Deribit historical chart endpoint | <https://docs.deribit.com/api-reference/upcoming/market-data/public-get_tradingview_chart_data> | provider-documented time-bounded historical OHLC endpoint |
| Coinbase Advanced Trade WebSocket channels | <https://docs.cdp.coinbase.com/coinbase-business/advanced-trade-apis/websocket/websocket-channels> | Level2 snapshot/update semantics, delivery/in-sync guidance, sequence-bearing messages |
| Coinbase product candles | <https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/products/get-product-candles> | time-bounded candle retrieval and provider limit |
| Apache Parquet file format | <https://parquet.apache.org/docs/file-format/> | row groups, column chunks, footer metadata |
| Apache Parquet page index | <https://parquet.apache.org/docs/file-format/pageindex/> | min/max/page skipping semantics |
| DuckDB guides | <https://duckdb.org/docs/current/guides/overview> | direct Parquet and cloud/object reads |
| DuckDB S3 Parquet import | <https://duckdb.org/docs/current/guides/network_cloud_storage/s3_import> | direct object-backed Parquet scan path |
| Apache Iceberg format specification | <https://github.com/apache/iceberg/blob/main/format/spec.md> | committed snapshots, serializable isolation goals, metadata scaling/evolution |
| Apache Iceberg evolution | <https://github.com/apache/iceberg/blob/main/docs/docs/evolution.md> | schema and partition evolution |
| SQLite WAL | <https://www.sqlite.org/wal.html> | same-host WAL requirement and network-filesystem limitation |
| PostgreSQL `SELECT` locking | <https://www.postgresql.org/docs/current/sql-select.html> | row locking and `SKIP LOCKED` queue-like use |
| Amazon S3 consistency model | <https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html> | representative object-store consistency capability evidence |
| Amazon S3 conditional writes | <https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html> | `If-None-Match`/`If-Match`, conditional publication capability |
| Amazon S3 checksums | <https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html> | upload/download integrity and multipart checksums |
| ClickHouse S3 integration | <https://clickhouse.com/integrations/amazon_s3> | standing/local OLAP candidate can query object data; not evidence of AIFE requirement |

AWS S3 documentation используется как **representative capability evidence**, а не как vendor selection. Любой будущий S3-compatible backend должен быть отдельно квалифицирован по фактическим semantics; слово “compatible” не является proof эквивалентной consistency/durability/checksum behavior.

## 3. Verified authority

### 3.1 Canonical AIFE package

- `AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0` — **MEASURED**, archive SHA matched sidecar and expected value.
- `_review_manifest.json` binds `review_head_commit=1ed138c06881aaebf8e650fcc020cef570e31b6d` and `head_tree=11f5cbc5f81836dddf0e854d3685418b53f22852`.
- Exact object carrier was imported into an isolated verifier; `git show -s --format=%T 1ed138c...` returned exactly `11f5cbc5f81836dddf0e854d3685418b53f22852` — **MEASURED**.

Canonical governance read from the verified snapshot:

`AGENTS.md`, `AGENTS_ARTIFACTS.md`, `AGENTS_PATCH_GUIDE.md`, `.github/prompts/investigate.prompt.md`, artifact naming/final-block/canonical-context/runtime-disposition/program-control includes, `.github/agent-coordination.md`, and the STANDARDS/ADR/CONTRACTS registries.

Governance interpretation relevant here: registry-first; chat is not authority; research may produce an artifact but not owner decisions; external claims must prefer primary evidence; final contract must be explicit; no repository/runtime mutation is implied by research.

### 3.2 Canonical quality toolchain

- `TOOLCHAIN_PACKAGE_SHA256=36c64406c57f51c1dc810a64a3c1a599a39dce6f8a7d02ac1b9fd32a2ad5192d` — exact package/sidecar match.
- `TOOLCHAIN_ID=1b3f6d7281419ae7a692e9f3b69019c7ed13761ee51775ad8f37aa1f85b585eb`.
- `QUALITY_POLICY_ID=8c0004758ca1d5a6ddbf013a9a0069a927b9bf87fbb23cedd4f5927835d388b3`.
- receipt: Tier 1 PASS, Tier 2 PASS, Tier 3 PASS, Tier 4 `external_required`.
- `TOOLCHAIN_BUILD_COUNT=0`, `QUALIFICATION_BUILD_COUNT=0`, `BUILD_A_COUNT=0`, `BUILD_B_COUNT=0`.

Toolchain был только identity/evidence input; rebuild и qualification build не выполнялись.

### 3.3 Pinned Data Bridge authority

GitHub commit object was read explicitly at:

- `RESEARCH_BASE_HEAD=2b82c75a67ed7ce5cd87cae2ccf02f09677d200c`
- `RESEARCH_BASE_TREE=2615dcd21570f0816be39c574b3b9f8ef1c1bc16`

Current branch HEAD, later WIP и post-base commits не использовались как substantive input.

Pinned `AGENTS.md` устанавливает boundary: **agent requests semantics, not storage**. D8 SQLite WAL — operational/control state, а high-cardinality WARM/COLD backend на base остаётся versioned decision. Storage/execution plane не становится market-data authority.

## 4. F4→F5 architecture gap

F4 уже задаёт lifecycle:

`VALIDATED_DOMAIN_INPUT → INGEST_DURABLE → STAGED → PUBLISHING → DURABLE_STORED → INDEPENDENT_READBACK_VERIFIED → CANONICALLY_REGISTERED → ACKED`.

F4 одновременно фиксирует отрицательные границы: production storage не начат; migration не начата; server deployment не начат; F5 не начат; AEB отсутствует; реальный AIFE не мутирован. Следующий checkpoint — high-cardinality physical storage lifecycle.

Следовательно, gap не в provider semantics и не в повторном проектировании D8/D9 identities. Gap состоит в том, чтобы доказуемо определить:

- где физически лежат immutable high-cardinality bytes;
- как определяется physical/content identity;
- как batch/partition/file становится sealed;
- как write переходит в verified/registered/ACK state;
- как publication остаётся idempotent при retry/duplicate/stale writer;
- как 1→N→1 не меняет semantic identity;
- как bulk data, control state, manifests/catalog и projections восстанавливаются из clean environment;
- когда простая metadata схема перестаёт быть достаточной и требует table format/shared DB/OLAP.

F5 не должен “улучшать” domain semantics. Он должен materialize generic Server capabilities уже определённые storage/publication/work/execution/access contracts.

## 5. Data-class matrix

### 5.1 Write/cardinality/temporal/read model

| Class | Write pattern / cardinality / size evidence | Immutability & revision | Temporal identity | Main reads | Multi-writer need |
|---|---|---|---|---|---|
| A. operational/control state | small-to-moderate transactional rows; current exact future row count **UNKNOWN** | mutable state machine with appendable attempts/audit | due slot, attempt times, lease expiry; `known_at` where publication state changes | point lookup, queue/claim scans, state transitions | no for initial 1-node; yes at N-node shared control |
| B. high-cardinality raw market data | append/snapshot/delta; retained byte growth **UNKNOWN**; current liquidity snapshots prove wide depth payloads | immutable after seal; preserve provider sequence/revision | event/effective time + collector known time + source sequence | replay, range scan, instrument/time subset | ingestion may scale later; publication must fence concurrent writers |
| C. regular market history | append/sealed partitions; **176,579 rows**, **509 partitions** repository-derived | closed candles immutable per accepted source revision; corrections create new revision/generation | candle effective interval + `known_at` + source revision | time-range scans, aggregates, cross-instrument joins | one logical publication writer sufficient initially |
| D. sparse analytical history | low-rate append; pinned Kraken analytics shows sparse segments around ~12 records in observed windows | derived, versioned by method/input | effective time + known time + method version | time-range, joins to market history | low; single publication writer initially |
| E. news/source evidence | document/blob + metadata; exact corpus size **UNKNOWN** | original evidence immutable; provider updates/retractions are new revisions | published/effective + first-known/ingested + source revision | evidence lookup, temporal joins, later full-text | low initially; duplicate/dedup identity required |
| F. indicators/features | batch/stream derived tables; size **UNKNOWN** | rebuildable if exact inputs + method version retained | feature effective time + computation known time | scans/joins/training | parallel builders safe only on disjoint deterministic work identity |
| G. AI/prediction/model/training datasets | potentially large bulk snapshots; current scale **UNKNOWN** | dataset snapshot immutable; model/artifact version immutable | dataset cutoff/known horizon + model version | broad scans, sampling, joins | independent dataset/run writers later |
| H. strategy/experiment state | transactional metadata + immutable configs/results | mutable lifecycle, immutable versioned config | run created/known/effective cutoff | point joins, status, lineage | N workers later require shared claims/fencing |
| I. backtest metadata and bulk outputs | metadata small; result curves/trades/logs can be bulk; scale **UNKNOWN** | run identity immutable; outputs immutable per attempt/result | replay cutoff + run/model/strategy versions | metadata point lookup + bulk scans/aggregates | many independent runs can publish concurrently if identities disjoint |
| J. search/full-text/vector projections | rebuilt from authoritative source classes; scale **UNKNOWN** | projection is disposable/rebuildable | projection generation known time | search/vector lookup | independent rebuild workers possible later |
| K. generic immutable blobs | arbitrary payload/evidence/model binaries; scale **UNKNOWN** | content-addressed or checksum-bound immutable object | produced/known + source/provenance | by identity, occasional range/stream | multi-writer collision must resolve by conditional/idempotent identity |

### 5.2 Retention / authority / recovery model

Numeric RPO/RTO targets are not present in pinned evidence and therefore are **UNKNOWN**, not invented.

| Class | Retention direction | Semantic authority | RPO disposition | RTO disposition | Backup / restore | Rebuildability |
|---|---|---|---|---|---|---|
| A | task/audit policy governed | Server operational authority | numeric target UNKNOWN; accepted terminal/ACK state should not be silently lost | UNKNOWN | transactional backup + clean restore/reconcile | partial only; in-flight/audit state may not be safely inferred |
| B | source/value dependent; raw non-reproducible streams may need long retention | domain source evidence | zero-loss intent is reasonable for accepted non-reproducible evidence, but no numeric SLO is pinned | UNKNOWN | object durability + independent backup/restore policy | often **not** rebuildable for missed live deltas/snapshots |
| C | historical long-lived | accepted domain history | source may be re-fetchable but provider corrections mean exact prior accepted bytes matter | UNKNOWN | object inventory/checksum + restore proof | partially rebuildable, not guaranteed byte-identical later |
| D | method/research dependent | derived | loss can be tolerated only if exact inputs/method retained | UNKNOWN | backup may be lighter if rebuild proof exists | usually rebuildable |
| E | evidence/audit dependent | source evidence | strong protection for evidence that may disappear/change upstream | UNKNOWN | immutable blob + metadata restore | often not fully rebuildable |
| F | feature lineage dependent | derived | rebuildable class | UNKNOWN | retain lineage; selective backup optional by cost | yes if all inputs/code/version exist |
| G | experiment/reproducibility dependent | dataset/model artifact may be research authority | numeric UNKNOWN | UNKNOWN | snapshot + model artifact backup where rebuild cost/irreproducibility high | variable |
| H | experiment audit | control/research authority | numeric UNKNOWN | UNKNOWN | DB + immutable config/result restore | lifecycle state only partially reconstructible |
| I | reproducibility retention | run/result authority | numeric UNKNOWN | UNKNOWN | metadata DB + bulk output object restore | outputs may be recomputable but expensive |
| J | short-to-medium projection lifetime | never semantic authority | can be lost | workload-dependent | backup usually unnecessary if rebuild is proven | yes |
| K | per artifact class | content evidence | per authority class | UNKNOWN | object backup/restore according to authority | variable |

### 5.3 Schema and layout implication

A single physical technology does not need to represent all classes identically. The minimal split is semantic, not vendor-driven:

- transactional mutable control rows → relational control substrate;
- immutable bulk/tabular facts → object/blob + Parquet;
- immutable non-tabular evidence/model/blob → object/blob native bytes;
- rebuildable search/vector/cache → projections, never authority.

## 6. Workload/SLO matrix

| Workload | Correctness/Semantic SLO already evidenced | Performance SLO evidence | Architectural consequence |
|---|---|---|---|
| durable ingestion | writer result alone is insufficient; independent readback before registration/ACK | ingest p50/p95/peak **UNKNOWN** | choose capability class with durable write + readback + checksum; benchmark throughput |
| control claims/leases | atomic claim, lease, fencing, stale owner cannot commit | control TPS/concurrency **UNKNOWN** | SQLite enough for 1-node; PostgreSQL trigger at shared N-node |
| regular history reads | no silent revision mixing; stable result identity/source revision | 1d/30d/365d scan latency **UNKNOWN** | columnar immutable files + manifest first; no standing OLAP requirement yet |
| PIT replay | exact information horizon and read-set must be reproducible | replay throughput **UNKNOWN** | temporal metadata contract is mandatory regardless of storage engine |
| large backtests | deterministic identity/output, retry isolation | wall-clock target, parallelism, RAM ceiling **UNKNOWN** | embedded workers + object/Parquet; benchmark before distributed query service |
| interactive analytics | correctness same as bulk reads | concurrent users, p95 latency, freshness **UNKNOWN** | ClickHouse/standing OLAP `BLOCKED_ON_MEASUREMENT` |
| compaction | canonical generation must never point to partial output | amplification/target object sizes **UNKNOWN** | copy-on-write + new generation; tune only by benchmark |
| clean restore | `BACKUP_EXISTS != RESTORE_PROVEN` | restore throughput/RTO **UNKNOWN** | separate restore proof for control DB and object data |
| search/vector | projection may be rebuilt; provenance must point to authoritative source | query volume/latency/recall **UNKNOWN** | no dedicated engine initially |

The available SLO evidence is therefore primarily **semantic**. Performance expansion cannot be justified by hypothetical TB/year, concurrency or latency values that the repository does not contain.

## 7. Measured baseline

### 7.1 Repository-derived corpus evidence

Pinned `history/manifest.json` gives a concrete, bounded regular-history baseline:

- 30 regular OHLC series: Binance `3 symbols × 6 intervals = 18`; Kraken `2 symbols × 6 intervals = 12` — **REPOSITORY_DERIVED**.
- 176,579 closed history rows — **REPOSITORY_DERIVED**:
  - Binance: 53,307 rows per symbol × 3 = 159,921;
  - Kraken: 8,329 rows per symbol × 2 = 16,658.
- 509 history manifest partitions — **REPOSITORY_DERIVED**:
  - Binance: 149 per symbol × 3 = 447;
  - Kraken: 31 per symbol × 2 = 62.
- earliest regular Binance daily timestamp: `2021-01-01T00:00:00Z`;
- latest observed closed 5m history timestamp in manifest: `2026-08-25T21:50:00Z`;
- observed regular-history time span between those bounds: ~2062.91 days — timestamp-derived, not growth-rate evidence.
- manifest states `closed_only=true`, `known_gaps=[]`, integrity PASS, `history_storage=GITHUB_RELEASE_ASSET`, and D9 warm status `DUAL_WRITE_CANDIDATE_NOT_ACTIVE`.

Pinned `data/manifest.json`:

- collection interval 60 min; expected max age 70 min — **REPOSITORY_DERIVED configuration evidence**.
- 3,000 retained 5m candles and 3,000 retained 15m candles per visible Binance symbol; lower counts for larger intervals according to manifest.
- 25 logical rolling OHLC files across visible Binance/Kraken instrument/interval combinations — **REPOSITORY_DERIVED**.
- exact visible Binance rolling OHLC subset: **2,848,828 bytes** across 15 files — **REPOSITORY_DERIVED**, recomputed from manifest size fields.

Pinned options/liquidity/derivatives manifests additionally show distinct data-shape classes:

- Deribit option surface: `option_count=816`, `selected_count=12`, `requests=51` in the pinned snapshot — **REPOSITORY_DERIVED**.
- liquidity snapshot has Binance 100 bids + 100 asks per instrument in depth-truncated raw examples; current snapshot counts include Binance spot 2 and Deribit 9 — **REPOSITORY_DERIVED**.
- Kraken derivatives analytics history is sparse compared with regular OHLC and contains short small record sets in observed archival windows — **REPOSITORY_DERIVED qualitative class evidence**.

### 7.2 What is not measured

The following remain **UNKNOWN**:

- 30/90/365-day byte growth;
- retained order-book delta growth;
- ingest p50/p95/peak;
- future TB/year;
- query concurrency;
- backtest scan throughput;
- restore throughput;
- compaction amplification;
- control-state write contention at N nodes;
- interactive OLAP p95 target.

These unknowns directly block claims that a distributed database, OLAP cluster, broker or Iceberg catalog is already mandatory.

## 8. External market-data evidence

### 8.1 Binance

Official Spot documentation defines order-book reconstruction around source sequence identity: diff-depth messages carry first/final update IDs (`U`, `u`), the client buffers deltas, obtains a REST snapshot with `lastUpdateId`, selects the first compatible buffered event, applies updates in order, and reinitializes when a gap is detected. This is provider-documented evidence that sequence identity is not an implementation convenience; it is part of correct state reconstruction.

Binance public bulk-data documentation publishes checksums and explicitly records cases where archived files are replaced later after discovered data issues. Therefore an AIFE artifact must distinguish “same provider/date/symbol path” from “same accepted source revision/content identity.” A later provider archive replacement must not silently rewrite the information set used by an earlier backtest.

### 8.2 Deribit

Official order-book subscription documentation states that the first notification is a full snapshot and later notifications are incremental. `change_id` and `prev_change_id` detect missed updates; mismatch requires re-subscription/resynchronization. Different channels may also have different delivery timing/order characteristics.

Deribit also exposes time-bounded public chart data for OHLC-style retrieval, but public API availability is not evidence of Deribit’s private backend architecture and is not used as such.

### 8.3 Coinbase

Official Advanced Trade WebSocket Level2 documentation describes snapshot/update messages for maintaining the order book and recommends Level2 when an in-sync book is required. Sequence-bearing messages/heartbeats provide transport/order evidence; historical candle endpoints are time-bounded and provider-limited. Again, public protocol behavior informs AIFE ingestion/replay requirements but says nothing about Coinbase’s internal storage choice.

### 8.4 Cross-provider consequence

Across all three providers the common invariant is not a database vendor. It is the need to persist enough source identity to prove which information was observable and in what order. At minimum, high-fidelity stream evidence must retain provider/instrument/channel identity, source event time, collector known time, source sequence/change/update identity when provided, snapshot generation/reconstruction boundary, gap/resync events and content/checksum identity.

## 9. Semantic/physical boundary

The architecture must preserve a one-way dependency:

**Domain semantics → neutral artifact identity/provenance → Server physical lifecycle**.

Storage does not decide whether a candle is final, whether an order-book gap is acceptable, how provider revisions are interpreted, or what constitutes a valid market-data observation. The Data Bridge/domain decides those semantics and provides a validated envelope. Server then owns durable physical placement, readback, canonical registration, execution scheduling, claims/fencing and access by semantic identity.

The physical layer may know:

- object/checksum/size/layout;
- manifest generation;
- schema/layout version;
- backend capability identity;
- storage locator as an opaque internal reference;
- publication attempt/fencing token;
- backup/restore state.

The consumer contract must not require S3 keys, local file paths, SQLite rowids, PostgreSQL table names, DuckDB-specific paths or ClickHouse parts. These are implementation details behind a stable access/result identity.

This separation is what makes future SQLite→PostgreSQL, custom-manifest→Iceberg or DuckDB→another analytical engine changes possible without semantic rewrite.

## 10. Bulk storage

### 10.1 Required capability class

High-cardinality bulk storage requires a **shared durable immutable-object capability**, not a named vendor. The minimum capability contract is:

- durable write/finalize;
- content checksum and size verification;
- independent readback after write;
- immutable or conditionally-created object identity;
- list/inventory/discovery sufficient for restore reconciliation;
- multipart/bounded large-object upload;
- conditional publication operation or an equivalent compare-and-set boundary;
- encryption at rest/in transit and rotatable credentials;
- lifecycle/retention controls;
- access from horizontally scaled workers without node-local semantic paths;
- documented backup/replication assumptions and a separately proven restore path.

AWS S3 is evidence that such primitives exist in a managed object API: strong post-write GET/LIST semantics, atomic single-key replacement, conditional writes and stored checksums are documented. But AIFE must qualify whichever backend is actually selected.

### 10.2 Mechanism comparison

| Mechanism | Risk closed | Simpler alternative | Decision |
|---|---|---|---|
| node-local durable filesystem | simplest durable bytes on one node | none simpler | **REJECT as sole P2 foundation**: node loss/horizontal access would make physical identity node-bound |
| shared/network filesystem | shared namespace across nodes | object API | **OPTIONAL/DEFER**: can work if durability/locking/readback/backup semantics are proven, but does not automatically simplify immutable publication |
| object/blob storage capability | node-independent immutable bytes and horizontal readers | local FS | **REQUIRED_NOW** for F5 physical architecture candidate |
| managed object service | reduces self-hosted storage operations | self-hosted object service | **OPTIONAL vendor deployment choice**; selection needs cost/location/compliance/restore evidence |
| self-hosted object service | local control, S3-like API possible | managed service | **DEFER as default**: adds service, upgrade, disk, HA, backup and credential domains without pinned requirement |

### 10.3 Physical identity

A canonical object should be addressable by stable internal object identity derived from dataset/logical artifact + generation + content checksum, while the backend key remains an implementation field. Retrying the same logical publication with the same bytes must converge; competing bytes for the same immutable logical identity must conflict explicitly rather than overwrite silently.

## 11. Tabular representation

**Parquet is REQUIRED_NOW as the default representation for regular/bulk tabular history**, not because a vendor benchmark says so, but because the workload is dominated by immutable temporal tables, column subsets, range scans, aggregates and joins.

Apache Parquet provides:

- column-oriented chunks grouped into row groups;
- file metadata/footer describing column locations;
- per-group/page statistics and optional page indexes that can support predicate/page skipping;
- compression by column/chunk;
- broad multi-engine interoperability.

Parquet does **not** provide:

- multi-file atomic transaction/publication;
- a canonical current snapshot pointer;
- concurrent-writer conflict resolution;
- logical table schema/partition evolution across files;
- work claims/fencing;
- AIFE PIT semantics.

Those belong to publication metadata/control contracts or, after a later trigger, an open table format.

Other representations remain justified per data class:

- native JSON/binary evidence for provider payloads where byte fidelity matters;
- generic blob for documents/models/media;
- Arrow as an in-memory interchange boundary, not the long-lived storage authority by default.

Exact codec, partition columns, target file size and row-group size are `BLOCKED_ON_MEASUREMENT`; they must be benchmarked with AIFE-shaped data rather than copied from generic defaults.

## 12. Small-files/compaction

The unsafe extreme is one event/snapshot per tiny canonical object forever. It amplifies LIST/planning calls, footer opens, metadata operations and compaction burden. The opposite unsafe extreme is giant mutable files with long uncommitted windows.

Initial mechanism:

1. collect/stage bounded input batches under a work identity;
2. build immutable candidate file(s);
3. close/seal file only after deterministic content/schema checks;
4. upload/finalize object;
5. verify checksum + independent readback;
6. publish a new manifest generation;
7. atomically advance the current-generation registration only after all new objects are verified;
8. ACK only after canonical registration.

Compaction is **copy-on-write**, never in-place mutation of canonical data:

`old generation → read immutable inputs → write new compacted objects → verify → publish new generation → switch pointer → retain old generation until retention/GC safety window`.

Failure before pointer switch leaves the old generation canonical. Failure after a valid atomic switch is recoverable because the new generation was already readback-verified. Old objects are not deleted as part of the atomic publication action.

Compaction trigger variables to measure:

- objects scanned per representative query;
- average/percentile object size;
- row groups per query;
- planning/list latency;
- read/write amplification;
- compaction wall time and temporary-space multiplier.

No exact 64/128/256 MiB target is asserted as AIFE fact; such values may be benchmark candidates only.

## 13. Manifest/catalog/table-format

### 13.1 A — immutable files + bounded/versioned custom manifests

Strengths: minimal service count; transparent bytes; exact read-set; easy clean-room inspection; compatible with one logical publication writer; can bind checksums, schema/layout version and provenance without standing catalog.

Required constraints:

- manifests themselves immutable and versioned;
- exact object list + checksums + sizes;
- generation identity and parent generation;
- explicit schema/layout version;
- deterministic dataset/partition identity;
- atomic current-generation pointer/registration in transactional control state;
- conflict/idempotency rules;
- no hidden rewrite of an already published generation.

Decision: **REQUIRED_NOW**.

### 13.2 B — immutable files + transactional custom catalog

A relational catalog can improve multi-writer registration and bounded lookup, but it creates a risk: repeated additions of snapshot lineage, partition evolution, file pruning metadata, compaction bookkeeping and multi-engine transaction semantics can silently become a bespoke table format.

Decision: control-state registration is useful, but a general custom transactional catalog is **DEFER** unless exact lookup/concurrency measurements require it.

### 13.3 C — Apache Iceberg

Iceberg officially specifies committed snapshots, serializable-isolation goals, metadata/manifest planning, schema evolution and partition evolution. These capabilities are valuable when AIFE truly needs:

- multiple concurrent writers to the same logical table;
- general snapshot history/time travel for physical table states;
- frequent schema evolution without file rewrite;
- partition-spec evolution;
- large manifest/file counts needing structured pruning/planning;
- multiple independent query engines requiring one transactional table contract.

Decision: **REQUIRED_LATER on trigger**, not initial F5 requirement.

### 13.4 IS_CUSTOM_METADATA_REIMPLEMENTING_A_TABLE_FORMAT?

**Answer: partially, but not necessarily improperly.** A bounded immutable publication manifest with exact files/checksums/generation is a much smaller mechanism than a general table format and directly closes AIFE publication/read-set risk. It becomes unacceptable reimplementation when it starts growing general snapshot mutation semantics, schema/partition evolution, optimistic concurrent table commits, delete/update semantics, large-scale manifest pruning/compaction planning, or multi-engine transactional catalog behavior. At that boundary the simpler long-term action is to adopt an open table format such as Iceberg rather than extend custom metadata.

## 14. Control-state backend

### 14.1 WHAT_BACKEND_IS_BEST_FIT

For the eventual **shared multi-node transactional control plane**, PostgreSQL is the best-fit candidate among mechanisms examined. It provides server-mediated transactions/locking and queue-like row-claim patterns; PostgreSQL documentation explicitly notes `SKIP LOCKED` can avoid contention among multiple consumers of a queue-like table (while warning it is not a general consistent-view mechanism).

### 14.2 WHEN_IT_IS_REQUIRED

PostgreSQL is **not required to close single-node F5 physical storage qualification**. Pinned Program Map explicitly allows initial one-server operation and says multi-node implementation now is not required. SQLite/WAL remains the simpler current substrate for operational/control state on one host.

SQLite documentation also defines the expansion boundary clearly: WAL requires processes on the same host and does not work as a shared multi-host WAL database over a network filesystem. Therefore direct shared SQLite is not the horizontal control solution.

### 14.3 Decision

`SQLITE_REQUIRED_NOW_FOR_SINGLE_NODE_F5_QUALIFICATION; POSTGRESQL_BEST_FIT_AND_REQUIRED_AT_FIRST_SHARED_MULTI_NODE_CONTROL_QUALIFICATION`.

PostgreSQL trigger occurs when any of these becomes real:

- more than one independent server node must atomically claim/renew/fence shared work;
- publication registration/current-generation pointer has concurrent cross-node writers;
- single-writer SQLite contention fails a measured SLO;
- HA requirement requires database service failover rather than host-local control state.

The contracts must stay backend-neutral so this migration changes physical implementation, not work/publication semantics.

## 15. PIT/history

### 15.1 Required temporal axes

Replay-correct records/read sets need more than event time:

- `effective_at` — when fact is effective in market/domain time;
- `known_at` — when AIFE could actually have known/accepted it;
- provider/source revision;
- source sequence/update/change identity where protocol provides one;
- snapshot/reconstruction generation;
- canonical publication generation and exact read-set manifest;
- content checksum;
- method version;
- feature version;
- model version;
- strategy version;
- replay cutoff/information horizon;
- provenance/acceptance evidence.

### 15.2 Why storage-native time travel is insufficient

A physical table snapshot can answer “which files were in this physical table snapshot?” It cannot by itself answer:

- whether a provider correction was known at the historical decision time;
- whether the backtest accidentally used a later source revision;
- whether an order-book gap had already been detected/resynced;
- which method/model/strategy code version produced a derived feature;
- what external evidence/news was actually available;
- which replay cutoff excluded future information.

Binance archive replacement evidence makes this concrete: later bytes for the same historical period can differ from the bytes previously available. Therefore `known_at`/source revision must be semantic metadata independent of storage snapshot time.

### 15.3 PIT contract

A backtest/research run must resolve a **versioned exact read set** before execution. Workers may cache/read physical files, but all results bind to the same read-set/generation ID and replay cutoff. A later compaction that preserves logical rows may create a different physical generation; either the old generation stays addressable for reproducibility or a verified equivalence/migration proof must bridge the identities.

## 16. Analytical/backtest execution

### 16.1 Direct Python / Arrow / Pandas-style execution

Good for domain transforms, model code, small/medium materializations, feature engineering and library interoperability. It has the fewest moving parts, but large joins/scans can force excessive memory materialization and bespoke partition orchestration if used as the only analytical substrate.

Decision: **OPTIONAL/GOOD_FIT for transforms**, not sole large-scan engine.

### 16.2 Embedded DuckDB

DuckDB official docs support direct Parquet queries and direct S3/object-backed Parquet access. Its embedded process model matches AIFE worker isolation: each analytical/backtest worker can open an engine locally, query immutable read-set files and terminate without introducing a standing analytical service or another authoritative database.

Decision: **GOOD_FIT; REQUIRED_LATER for the analytical/backtest execution plane unless a representative benchmark proves a still simpler direct-Arrow path sufficient. It is not required merely to close F5 storage lifecycle.**

Required worker controls:

- fixed exact read-set/generation;
- bounded CPU/RAM/temp-disk;
- deterministic strategy/model/config identity;
- attempt isolation;
- worker crash/retry with same logical work ID, new attempt;
- fenced publication of results;
- output checksum/result identity.

### 16.3 Standing analytical database

A standing OLAP database adds service lifecycle, credentials, backup/restore, upgrades, monitoring, ingest synchronization and a second physical representation. That cost is justified only by a real interactive/concurrent workload or by benchmark failure of embedded scans.

Decision: **not required in F5**.

## 17. Horizontal backtests

Safe initial horizontal decomposition uses independence boundaries that do not require cross-worker mutable temporal state:

- strategy version;
- model version;
- parameter sets;
- scenario sets;
- independent runs/seeds where semantics permit;
- instruments/universe partitions only when strategy dependency graph declares them independent;
- independent read-only research jobs.

Time is **not automatically a safe shard axis**. Stateful strategies can carry positions, cash, risk state, rolling-window state, execution assumptions and model state across time boundaries.

For a stateful temporal shard to be safe it requires one of:

1. complete versioned checkpoint state at shard boundary, bound to exact read-set/method/strategy/model versions;
2. deterministic state transfer from predecessor with fencing and one accepted predecessor state;
3. deterministic replay from a prior trusted checkpoint through the boundary.

Otherwise chronological execution within one stateful run must remain sequential while parallelism occurs across independent run/parameter/scenario/universe axes.

This is intentionally simpler than distributed temporal DAG orchestration and minimizes next-agent actions.

## 18. 1→N→1 scaling

A valid candidate must retain the same logical identities when worker/node count changes.

### Invariants

- stable logical work ID independent of process/node;
- durable attempt records;
- lease owner + expiry + monotonic fencing token;
- stale owner cannot publish after losing fence;
- deterministic/idempotent publication identity;
- immutable physical object identity by content/generation;
- process memory is never durable SSOT;
- node-local paths never enter semantic consumer contracts;
- worker-local cache/projection is rebuildable;
- restart/node loss cannot change accepted logical result identity;
- N→1 requires fewer workers, not a data-format rewrite.

### 1 node

SQLite/WAL control + object/blob bulk + Parquet/manifests. Worker claims may be simple but still use the same semantic attempt/fence model so later scale does not redefine state transitions.

### N nodes

Switch control implementation to PostgreSQL/shared transactional service. Object data already shared; workers independently read immutable manifests/files. Claims/leases/fencing become cross-node transactional operations. The bulk format does not change.

### Back to 1 node

One server/worker set continues against the same shared bulk objects and control schema. No semantic downgrade is allowed. PostgreSQL may remain deployed; reverting physically to SQLite is a separate migration choice, not necessary for the N→1 semantic proof.

## 19. Interactive OLAP

ClickHouse is a credible **mechanism** for high-concurrency low-latency analytical workloads and can query S3/object data, but pinned AIFE evidence does not contain the workload/SLO that would make a standing ClickHouse service necessary.

`INTERACTIVE_OLAP_DECISION=DEFER_BLOCKED_ON_REPRESENTATIVE_WORKLOAD_AND_SLO_MEASUREMENT`.

Trigger candidates:

- explicit product/research contract for interactive p95/p99 latency;
- sustained multi-user concurrency that embedded workers cannot satisfy;
- repeated scans whose cost exceeds a defined threshold despite Parquet pruning/partitioning;
- freshness/serving requirement that justifies a continuously maintained projection;
- benchmark showing lower total operational cost than scaled embedded workers for the real query mix.

If adopted later, ClickHouse should normally be treated as a **serving/analytical projection**, not the sole semantic authority for raw source evidence or PIT lineage. Bulk object/manifests remain a stable interchange/recovery boundary unless a later owner ADR explicitly changes that architecture.

## 20. Cache/broker/search/vector

| Mechanism | Real risk it could close | Simpler current alternative | Authority/rebuildability | Decision / trigger |
|---|---|---|---|---|
| cache/Redis-like | repeated expensive hot reads / shared ephemeral coordination | process-local cache + DB/object reads | cache never authority; rebuildable | **DEFER** until hit-rate/latency/cost measurement proves need |
| message broker | external fanout, backpressure, durable cross-service event distribution | durable work table + polling/claims | broker must not replace work/result authority silently | **DEFER** until a real event contract/fanout workload exists |
| full-text search engine | news/evidence text discovery at scale | metadata filters + direct scan initially | projection; rebuildable from source evidence | **DEFER** until search workload/SLO exists |
| vector DB | nearest-neighbor retrieval over embeddings | batch vector files/in-process library for small scale | projection; embeddings/model versioned; rebuildable if source/model retained | **DEFER** until corpus/query/recall/latency requirement measured |

Adding any of these “for future scale” would increase service, credential, monitoring, backup and failure domains before it reduces a proven human/agent action. That fails the three-question test now.

## 21. Failure/HA/DR

| Failure | Required behavior | Candidate mechanism |
|---|---|---|
| worker crash | logical work survives; retry uses new attempt | durable control row + attempt record |
| control process crash | restart reconstructs state from durable DB, not memory | SQLite WAL now / PostgreSQL later |
| reboot | no accepted result depends on RAM-only state | durable DB + immutable object refs |
| control DB loss | restore + reconcile before authority resumes | DB backup + object-manifest inventory + restore proof |
| disk/node loss | bulk data remains accessible from another node/path | shared object/blob capability |
| object loss/corruption | detect via checksum/inventory; restore or explicitly rebuild if authority permits | checksum + backup/replication + restore workflow |
| network failure during upload | partial upload never becomes canonical | multipart staging/finalize; no manifest registration until verified |
| partial upload | orphan is non-canonical and GC-able | immutable candidate object + manifest publication boundary |
| duplicate delivery | converge or explicit conflict, no double semantic artifact | deterministic idempotency/content identity |
| stale writer | cannot advance publication after fence loss | monotonic fencing token checked at commit/registration |
| catalog/manifest loss | reconstruct/discover immutable generations and reconcile control pointer | object inventory + manifest backup/retention |
| compaction interruption | old generation remains valid; incomplete new generation is orphan | copy-on-write compaction |
| projection loss | rebuild from authoritative objects/manifests | projection generation + rebuild job |
| credential rotation | new credentials without changing semantic identity | secret indirection/managed credentials; no secret in artifact refs |
| clean-environment restore | fresh environment can re-establish data/control authority and verify readback | documented restore sequence + independent validation |

HA is deliberately not equated with backup. Replication can keep a service available while replicating accidental deletion/corruption. Backup can exist but be unusable. Both require distinct proofs.

## 22. Backup/restore

### 22.1 Separate domains

At minimum there are two authoritative recovery domains:

1. **control-state DB** — work, attempts, claims/fencing state, publication registrations/current-generation pointers, terminal/ACK evidence;
2. **bulk immutable object domain** — source evidence, Parquet partitions, manifests, blobs, analytical outputs.

Search/vector/cache projections form additional *rebuild* domains but do not need authority-grade backup if rebuild is proven and RTO permits.

### 22.2 Clean restore sequence

A clean-environment proof should execute conceptually:

1. provision an empty isolated control substrate and storage access;
2. restore control backup into isolated DB;
3. inventory immutable object/manifests from restored/available bulk storage;
4. verify object checksums/sizes for selected and sampled/full policy scope;
5. verify every canonical manifest references available verified objects;
6. verify current-generation pointers and publication/ACK states are consistent;
7. re-run independent readback using consumer-side path, not the producer’s open handle;
8. rebuild disposable projections;
9. run representative semantic access/replay checks;
10. only then declare restore proven.

`BACKUP_EXISTS != RESTORE_PROVEN` and `REPLICATION != BACKUP` are hard invariants.

### 22.3 Rebuildability classes

Rebuildability must be explicit per artifact. A derived indicator may be rebuildable; a live order-book delta missed at source is not. A historical provider archive may be re-downloadable but later replaced, so it is not guaranteed to reproduce the prior accepted byte/revision. This changes backup priority even when nominal data type is the same.

## 23. Operational complexity

The comparison counts *domains*, not merely binaries. Exact production service count depends on managed/self-hosted deployment and is therefore expressed as relative architecture cost.

| Stack | External standing services | Credential domains | Backup/restore domains | Failure/upgrade/monitoring burden | Human/next-agent actions | Verdict |
|---|---:|---|---|---|---|---|
| S0: SQLite + local FS + Python | 0 | host | DB + host disk | low until node/disk loss; no shared bulk access | low now, high future migration/recovery | **REJECT as P2 foundation** |
| S1: SQLite + shared object/blob + Parquet + bounded manifests + embedded DuckDB | usually 1 storage service/API; DB/engine embedded | object + host/control secrets | control DB + object domain | lowest stack satisfying shared bulk lifecycle; analytics process-local | minimum initial operational surface | **RECOMMENDED initial** |
| S2: PostgreSQL + object/blob + Parquet + manifests + embedded DuckDB | usually 2 | DB + object | DB + object | additional DB HA/upgrades/monitoring | justified at N-node shared control | **REQUIRED_LATER** |
| S3: PostgreSQL + object + Iceberg catalog + standing ClickHouse + broker/cache/search/vector | many | many | multiple authority/projection domains | highest | many install/config/backup/restore/upgrade decisions | **REJECT/DEFER initially** |

S1 is preferred because it solves the current physical problem while preserving upgrade seams to S2/Iceberg/OLAP. It does not require a future semantic rewrite; only capability implementations change behind the same work/storage/publication/access contracts.

## 24. Benchmark requirements

Performance-dependent decisions cannot be settled from semantics alone. The benchmark is therefore a **qualification requirement**, not a vendor benchmark substitution.

### 24.1 Dataset matrix

Use disposable copies/replays only:

- pinned regular OHLC corpus (current 176,579-row baseline);
- replayed/captured raw order-book snapshot+delta traces with preserved source sequence/gap events;
- sparse derivatives analytics;
- representative feature table;
- representative backtest trades/equity/events outputs;
- synthetic scale multipliers may be used to explore thresholds but must be labeled **SYNTHETIC**, never AIFE measured growth.

### 24.2 Layout matrix

Benchmark combinations of:

- partition keys: provider/instrument/date and less granular alternatives;
- candidate target object sizes/time windows;
- Parquet row-group sizes;
- compression codecs;
- manifest cardinality;
- single-file vs compacted generations.

Candidate numerical values such as 64/128/256 MiB may be test points only, not architecture facts.

### 24.3 Operation matrix

Measure:

- batch encode/seal throughput;
- multipart upload/finalize;
- checksum/readback latency;
- conditional publish conflict behavior;
- manifest discovery/planning;
- point identity lookup;
- 1d/30d/365d range scan;
- selected-column scans;
- cross-instrument joins;
- aggregations/window functions;
- cold-object reads;
- compaction and interruption recovery;
- object/manifest inventory restore;
- control DB backup/restore;
- 1→N→1 worker execution over the same exact read-set;
- duplicate delivery and stale-fence publication rejection.

### 24.4 Metrics

Record p50/p95/peak where applicable, scan MiB/s, rows/s, bytes read, CPU, max RSS, temp disk, object/LIST/HEAD requests, files opened, manifest planning time, compaction read/write amplification, restore time/throughput, retries, correctness hashes and number of human recovery actions.

### 24.5 Decision gates

Until an owner-approved SLO exists, results establish comparative capability but not arbitrary PASS thresholds. Specific expansion decisions remain `BLOCKED_ON_MEASUREMENT`:

- ClickHouse/standing OLAP;
- target Parquet file/row-group sizing;
- need for Iceberg due manifest scale;
- PostgreSQL due contention (multi-node semantic trigger can require it even before performance trigger);
- cache/broker/search/vector services.

## 25. Three-question review

Каждый substantial mechanism проверен тремя вопросами: какой реальный риск закрывает; можно ли проще; уменьшает ли он действия следующего агента/инженера. Поля ниже намеренно включают operational burden.

### 25.1 Shared durable object/blob capability

- **Real-Risk:** Node loss and horizontal readers must not bind bulk authority to one host; partial uploads need a durable publication boundary.
- **Evidence:** Pinned F4/storage/publication contracts + S3 primary capability evidence.
- **Simpler-Alternative:** Node-local filesystem.
- **Why-Simpler-Succeeds-Or-Fails:** Local FS is simpler but fails node-independent access and disk/node-loss boundary.
- **New-Service-Count:** 1 storage service/API class (deployment-specific)
- **Credential-Domains:** object-storage credential domain
- **Backup-Domains:** object domain
- **Failure-Domains:** object service/network + control reference
- **Steady-State-Human-Actions:** low after automation
- **Recovery-Human-Actions:** restore/inventory/readback procedure
- **Next-Agent-Actions:** qualify backend capabilities; define opaque refs
- **Authority-Class:** physical authority substrate
- **Rebuildability:** varies by data class
- **Expansion-Trigger:** none; required now
- **Decision:** `REQUIRED_NOW`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.2 Parquet

- **Real-Risk:** Large immutable temporal tables need efficient column/range scans without importing into a standing DB.
- **Evidence:** Repository data classes + Apache Parquet primary docs.
- **Simpler-Alternative:** JSON/CSV/native rows.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler text formats preserve bytes but increase scan/decode cost and lose standardized column statistics for bulk tabular workloads.
- **New-Service-Count:** 0
- **Credential-Domains:** none additional
- **Backup-Domains:** same object domain
- **Failure-Domains:** file-format/read-library
- **Steady-State-Human-Actions:** very low
- **Recovery-Human-Actions:** read files with independent engine
- **Next-Agent-Actions:** define schema/layout version and benchmark layout
- **Authority-Class:** physical tabular representation
- **Rebuildability:** yes for derived; source dependent
- **Expansion-Trigger:** if bulk tabular scans disappear
- **Decision:** `REQUIRED_NOW`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.3 Bounded versioned manifest

- **Real-Risk:** Multi-file publication must expose one exact verified generation and read set.
- **Evidence:** F4 publication lifecycle + access no-revision-mixing requirement.
- **Simpler-Alternative:** Directory listing/glob only.
- **Why-Simpler-Succeeds-Or-Fails:** Listing alone cannot prove a coherent generation or exact accepted read set across partial/compacting writes.
- **New-Service-Count:** 0
- **Credential-Domains:** none additional
- **Backup-Domains:** object + control DB
- **Failure-Domains:** metadata consistency
- **Steady-State-Human-Actions:** low
- **Recovery-Human-Actions:** reconcile manifests with object inventory/control pointer
- **Next-Agent-Actions:** define manifest schema and current-pointer rules
- **Authority-Class:** physical publication authority
- **Rebuildability:** manifest itself must be protected
- **Expansion-Trigger:** table-format feature growth
- **Decision:** `REQUIRED_NOW`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.4 SQLite/WAL control

- **Real-Risk:** Single-node durable work/publication state must survive process restart.
- **Evidence:** Pinned Program Map permits one server; D8/contract semantics; SQLite WAL docs.
- **Simpler-Alternative:** In-memory/process files.
- **Why-Simpler-Succeeds-Or-Fails:** Memory is not durable SSOT; ad-hoc files complicate atomic state transitions.
- **New-Service-Count:** 0
- **Credential-Domains:** host/control secret domain
- **Backup-Domains:** control DB
- **Failure-Domains:** host/disk/DB
- **Steady-State-Human-Actions:** low
- **Recovery-Human-Actions:** restore DB + reconcile objects
- **Next-Agent-Actions:** preserve backend-neutral schema/semantics
- **Authority-Class:** operational control authority
- **Rebuildability:** partly
- **Expansion-Trigger:** shared multi-node control or measured contention
- **Decision:** `REQUIRED_NOW`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.5 PostgreSQL shared control

- **Real-Risk:** N nodes require transactional shared claims/leases/fencing/publication registration.
- **Evidence:** Execution/work contracts + PostgreSQL locking docs + SQLite same-host limit.
- **Simpler-Alternative:** Shared SQLite/network filesystem.
- **Why-Simpler-Succeeds-Or-Fails:** SQLite WAL cannot be shared multi-host; network-file locking is not the intended substrate.
- **New-Service-Count:** 1 DB service
- **Credential-Domains:** DB credentials
- **Backup-Domains:** control DB
- **Failure-Domains:** DB service/HA/network
- **Steady-State-Human-Actions:** moderate
- **Recovery-Human-Actions:** DB restore/failover/reconcile
- **Next-Agent-Actions:** migration/qualification at N-node trigger
- **Authority-Class:** operational control authority
- **Rebuildability:** partly
- **Expansion-Trigger:** first shared multi-node control qualification
- **Decision:** `REQUIRED_LATER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.6 Embedded DuckDB

- **Real-Risk:** Workers need bounded SQL scans/joins over Parquet/object data without standing OLAP service.
- **Evidence:** DuckDB official Parquet/object docs + workload shape.
- **Simpler-Alternative:** Direct Python/Arrow/Pandas only.
- **Why-Simpler-Succeeds-Or-Fails:** Direct path may suffice for small work; large joins/scans can become bespoke memory/orchestration work. Benchmark decides exact requirement.
- **New-Service-Count:** 0
- **Credential-Domains:** object credentials reused
- **Backup-Domains:** none additional
- **Failure-Domains:** worker process
- **Steady-State-Human-Actions:** low
- **Recovery-Human-Actions:** restart/retry worker
- **Next-Agent-Actions:** build representative backtest benchmark
- **Authority-Class:** execution mechanism, not data authority
- **Rebuildability:** stateless engine
- **Expansion-Trigger:** analytical/backtest execution starts and direct path is insufficient
- **Decision:** `REQUIRED_LATER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.7 Apache Iceberg

- **Real-Risk:** General multi-writer snapshot evolution and large metadata planning can outgrow bounded manifests.
- **Evidence:** Iceberg primary spec/evolution docs.
- **Simpler-Alternative:** Bounded manifest + transactional pointer.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler mechanism succeeds while publication is single-writer/bounded and schema/partition evolution is limited.
- **New-Service-Count:** catalog-dependent; at least metadata/catalog domain
- **Credential-Domains:** catalog/object credentials
- **Backup-Domains:** catalog metadata + object
- **Failure-Domains:** catalog/engine compatibility
- **Steady-State-Human-Actions:** moderate-high
- **Recovery-Human-Actions:** restore catalog/metadata + object reconciliation
- **Next-Agent-Actions:** measure trigger; do not extend custom manifest into table format
- **Authority-Class:** physical table metadata
- **Rebuildability:** data files survive; metadata must be protected
- **Expansion-Trigger:** concurrent table writers/schema+partition evolution/manifest scale/multi-engine transactions
- **Decision:** `REQUIRED_LATER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.8 Standing ClickHouse

- **Real-Risk:** Interactive concurrent OLAP may need pre-indexed/standing execution.
- **Evidence:** ClickHouse primary docs show capability; AIFE workload/SLO evidence absent.
- **Simpler-Alternative:** Embedded DuckDB/direct Parquet workers.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler path avoids service/replication/backup/sync domains and is sufficient until measured otherwise.
- **New-Service-Count:** 1+
- **Credential-Domains:** OLAP + object
- **Backup-Domains:** OLAP projection + source object
- **Failure-Domains:** OLAP service/cluster
- **Steady-State-Human-Actions:** moderate-high
- **Recovery-Human-Actions:** rebuild or restore projection
- **Next-Agent-Actions:** run representative concurrency/latency benchmark
- **Authority-Class:** rebuildable analytical projection by default
- **Rebuildability:** yes if object source retained
- **Expansion-Trigger:** explicit interactive SLO + benchmark failure
- **Decision:** `BLOCKED_ON_MEASUREMENT`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.9 Cache

- **Real-Risk:** Repeated hot reads might waste compute/I/O.
- **Evidence:** No current measured cache workload.
- **Simpler-Alternative:** process-local cache/no cache.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler path avoids consistency and eviction service; sufficient until measured misses dominate.
- **New-Service-Count:** 0 now; 1 if shared cache
- **Credential-Domains:** none now
- **Backup-Domains:** none authoritative
- **Failure-Domains:** none/process
- **Steady-State-Human-Actions:** low
- **Recovery-Human-Actions:** rebuild
- **Next-Agent-Actions:** measure repeated-read profile
- **Authority-Class:** projection only
- **Rebuildability:** yes
- **Expansion-Trigger:** measured latency/cost/hit-rate trigger
- **Decision:** `DEFER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.10 Message broker

- **Real-Risk:** Cross-service fanout/backpressure may need durable event distribution.
- **Evidence:** No pinned event-contract/fanout requirement.
- **Simpler-Alternative:** durable work table + scheduler/polling/claims.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler work semantics already cover bounded job execution without introducing a second delivery authority.
- **New-Service-Count:** 1+
- **Credential-Domains:** broker credentials
- **Backup-Domains:** broker if durable + control
- **Failure-Domains:** broker/network
- **Steady-State-Human-Actions:** moderate
- **Recovery-Human-Actions:** broker recovery/replay
- **Next-Agent-Actions:** define real event contract first
- **Authority-Class:** transport, not semantic authority
- **Rebuildability:** depends
- **Expansion-Trigger:** external fanout/backpressure/streaming contract
- **Decision:** `DEFER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

### 25.11 Search/vector services

- **Real-Risk:** Specialized retrieval may later need indexes.
- **Evidence:** No current search/vector SLO/corpus measurement.
- **Simpler-Alternative:** direct metadata/text scans or in-process library for bounded corpora.
- **Why-Simpler-Succeeds-Or-Fails:** Simpler projection avoids new authority and service until workload exists.
- **New-Service-Count:** 0 now; 1-2 later
- **Credential-Domains:** projection service credentials
- **Backup-Domains:** normally rebuild domain
- **Failure-Domains:** projection service
- **Steady-State-Human-Actions:** low now
- **Recovery-Human-Actions:** rebuild from source
- **Next-Agent-Actions:** measure workload and define projection lineage
- **Authority-Class:** projection only
- **Rebuildability:** yes if source/model retained
- **Expansion-Trigger:** explicit product/search/vector SLO
- **Decision:** `DEFER`
- **Impact on actions:** решение принято так, чтобы не добавлять standing service/config/restore work раньше доказанного риска; следующий агент получает конкретный trigger вместо speculative deployment work.

## 26. Minimum architecture candidate

### 26.1 Candidate C1 — minimum initial stack without future semantic rewrite

**Control plane**

- SQLite/WAL on the single initial server for work/scheduling/attempts/claims/fencing/publication registration/current-generation pointer.
- Schema and APIs remain capability/identity based; no local pathname/SQLite-row identity leaks into consumer contract.

**Bulk authority plane**

- shared durable object/blob storage capability;
- immutable objects with checksum/size/content identity;
- backend-qualified conditional write/finalize/readback/listing/multipart/encryption/lifecycle semantics;
- Parquet for bulk tabular classes; native immutable blobs where source fidelity requires it.

**Publication metadata**

- immutable bounded versioned manifests stored with bulk data;
- each manifest binds exact file/object set, checksums, schema/layout version, generation, parent, temporal/provenance identities;
- transactional current-generation registration/pointer in control state;
- single logical writer per dataset/generation initially; duplicates are idempotent, conflicting bytes reject.

**Analytical plane**

- embedded DuckDB in isolated analytical/backtest workers as the default scale-up path for Parquet/object scans;
- direct Python/Arrow/Pandas permitted for small transforms and model code;
- no standing OLAP required initially.

**Scale seam**

- first real N-node shared-control qualification migrates control backend to PostgreSQL;
- bulk files/manifests remain unchanged;
- workers continue to read the same logical generations.

**Evolution seam**

- bounded manifests remain until table-format triggers occur;
- then migrate metadata semantics to Iceberg rather than incrementally reimplement general table-format features.

This candidate has the smallest initial service/credential/backup surface among mechanisms that satisfy node-independent bulk storage and the existing F4 publication lifecycle.

## 27. Expansion triggers

| Mechanism to add/change | Exact trigger class | Evidence required before decision |
|---|---|---|
| SQLite → PostgreSQL | first shared N-node control qualification; concurrent cross-node claims/fences/publication pointer; or measured SQLite contention | contract scenario + lifecycle tests; optionally throughput/concurrency benchmark |
| bounded manifest → Iceberg | concurrent writers to same table; general snapshot mutation; schema/partition evolution; large manifest planning; multi-engine transactional catalog | representative metadata scale + explicit feature requirement |
| embedded DuckDB/direct files → standing ClickHouse | explicit interactive concurrency/latency/freshness SLO unmet by embedded path | AIFE representative query benchmark, not vendor benchmark |
| no cache → shared cache | repeated authoritative reads have measured latency/cost hot spot and cache materially reduces it | hit-rate/profile/latency benchmark + invalidation model |
| work table → broker/event bus | real cross-service fanout/backpressure/durable event-stream contract | producer/consumer contract and failure/replay semantics |
| no search engine → full-text service | news/evidence corpus + query/SLO make scans inadequate | corpus/query benchmark; projection rebuild proof |
| no vector DB → vector service | retrieval product requirement with corpus, recall and latency target | representative embedding/query benchmark + model/version lineage |
| managed ↔ self-hosted object backend | cost/compliance/location/control requirement outweighs operator burden | capability qualification + TCO + backup/restore + failure exercise |
| compaction policy tuning | object/file count causes measurable planning/read penalty | file-count/read-amplification benchmark |

Expansion must be one-way semantically: adding a service may improve execution/serving, but it may not redefine domain truth or invalidate historical replay identity.

## 28. F5/P2 implications

Future F5 needs explicit **physical authority fields** without implementing them in this run.

### 28.1 Backend capability / physical identity

- `backend_capability_class`
- `backend_instance_or_namespace_identity`
- stable opaque `storage_ref`
- `physical_object_identity`
- content checksum algorithm/value
- size bytes
- media/encoding/compression
- encryption/key-class reference (never secret value)

### 28.2 Partition / layout / seal

- dataset/data-class identity
- provider/domain artifact identity link
- partition model + partition values
- file/layout version
- schema version
- row-group/chunking policy version
- seal generation ID
- immutable/sealed state and seal evidence

### 28.3 Manifest/catalog / multi-writer

- manifest/catalog generation ID
- parent generation
- exact object/read-set inventory
- current-generation pointer identity
- writer/work/attempt identity
- fencing token/evidence
- idempotency key
- declared multi-writer mode
- duplicate/conflict disposition
- compaction parent/input generation refs

### 28.4 Temporal/provenance

- source/provider revision
- source sequence/update/change ID where applicable
- `effective_at`
- `known_at`
- produced/observed/validated timestamps
- replay cutoff/information horizon
- method/model/strategy version refs where applicable
- provenance/acceptance evidence refs

### 28.5 Readback / registration / ACK

- durable-write evidence
- checksum evidence
- independent-readback evidence and observed identity
- canonical registration identity
- publication generation
- ACK state/evidence
- explicit identity comparison result

### 28.6 Backup / restore / migration / qualification

- retention class
- backup reference + generation
- replication status separate from backup status
- restore-proof reference/status
- inventory reconciliation status
- migration source/target physical identities
- migration checkpoint/cutover boundary
- backend capability qualification version
- benchmark suite/version
- qualification criteria IDs
- clean-environment restore proof

### 28.7 F5 vs F5M

F5 should establish and qualify the incoming physical lifecycle on bounded representative data. F5M remains a later corpus migration/cutover concern. Mass backfill must not become the mechanism by which the incoming route is first tested.

## 29. Governance disposition

Registry-first analysis finds no justification for parallel duplicate governance families.

| Owner area | Disposition | Reason |
|---|---|---|
| ADR | `AMEND_REQUIRED` | proposed Data Foundation ADR should, after independence review/consolidation, capture capability-class choice, initial/later control backend split, bounded-manifest/Iceberg trigger and non-requirement of standing OLAP/broker by default |
| Standards | `AMEND_REQUIRED` | existing data backup/retention/schema standards need explicit multi-domain restore, immutable object/readback and PIT/revision-aware requirements; prefer amendment over new `STD-SERVER-*` duplication |
| Artifact/Server contracts | `AMEND_REQUIRED` | storage/publication/access contracts are semantically sound but F5 needs additive physical authority/qualification/restore fields and explicit multi-writer/manifest boundaries |
| Program Map | `AMEND_REQUIRED` | after owner acceptance, F5/P2 decision and expansion triggers should be reflected in the program path; current pinned map correctly leaves vendor/backend undecided |

No ADR, standard, contract, Program Map, DEV_TZ or owner artifact was mutated by this run.

## 30. Findings

### FIND-001

- **Priority:** P1
- **Claim:** F4→F5 gap is physical lifecycle, not provider/domain semantics.
- **Evidence:** Pinned F4 checkpoint + Server contracts + Data Bridge AGENTS boundary.
- **Evidence-Class:** `REPOSITORY_DERIVED`
- **Risk:** Reopening semantics would create duplicate authorities and drift.
- **Simpler-Alternative:** Implement physical lifecycle behind neutral contracts.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Sufficient because F4 already defines domain/Server ownership and ACK boundary.
- **Impact-On-Agent-Actions:** Removes semantic redesign tasks.
- **Impact-On-Engineer-Actions:** Keeps engineering focused on storage/publication qualification.
- **Decision-Consequence:** F5 should bind physical authority fields, not redefine market truth.
- **Governance-Consequence:** Narrow ADR/contract amendment only.
- **F5/F5M-Consequence:** F5 yes; F5M later migration.

### FIND-002

- **Priority:** P1
- **Claim:** Current measured corpus does not justify a heavyweight distributed/OLAP stack.
- **Evidence:** 176,579 regular rows, 509 partitions, 2,848,828-byte visible Binance rolling subset; growth/concurrency unknown.
- **Evidence-Class:** `REPOSITORY_DERIVED`
- **Risk:** Premature services create more failure/credential/restore work than proven benefit.
- **Simpler-Alternative:** Object+Parquet+embedded execution.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Meets current semantics and leaves expansion triggers.
- **Impact-On-Agent-Actions:** Avoids multi-service bootstrap.
- **Impact-On-Engineer-Actions:** Avoids premature HA/upgrade/monitoring domains.
- **Decision-Consequence:** Standing OLAP/broker/cache are not initial requirements.
- **Governance-Consequence:** Record trigger-driven disposition.
- **F5/F5M-Consequence:** F5 can stay minimal.

### FIND-003

- **Priority:** P1
- **Claim:** Source sequence/change/update identities are required for high-fidelity replay provenance.
- **Evidence:** Binance U/u/lastUpdateId; Deribit change_id/prev_change_id; Coinbase sequence-bearing Level2/feed docs.
- **Evidence-Class:** `PROVIDER_DOCUMENTED`
- **Risk:** Without source order/gap identity, reconstructed books can be silently wrong.
- **Simpler-Alternative:** Store source IDs/gap/resync evidence with archived batches.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** No database feature can reconstruct missing source order after the fact.
- **Impact-On-Agent-Actions:** Makes replay requirements explicit for next agent.
- **Impact-On-Engineer-Actions:** Avoids reverse-engineering stream continuity later.
- **Decision-Consequence:** Add source-sequence fields where domain supplies them.
- **Governance-Consequence:** Contract/physical authority amendment.
- **F5/F5M-Consequence:** F5 fields; F5M migration must preserve available sequence evidence.

### FIND-004

- **Priority:** P1
- **Claim:** Storage-native time travel is insufficient for PIT correctness.
- **Evidence:** Provider archive corrections + semantic method/model/cutoff requirements.
- **Evidence-Class:** `PROVIDER_DOCUMENTED+INFERENCE`
- **Risk:** Backtests can leak future revisions or later model/data knowledge.
- **Simpler-Alternative:** Exact versioned read-set + known_at/source revision/method/model/strategy/cutoff.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** It directly expresses information horizon independent of storage technology.
- **Impact-On-Agent-Actions:** Prevents next agent from equating table snapshot with PIT.
- **Impact-On-Engineer-Actions:** Defines deterministic replay evidence.
- **Decision-Consequence:** PIT is a cross-layer contract.
- **Governance-Consequence:** Standards/contracts need temporal identity additions.
- **F5/F5M-Consequence:** F5 read-set fields; F5M preserves historical revisions.

### FIND-005

- **Priority:** P1
- **Claim:** Shared durable object/blob storage is the minimum bulk physical capability for node-independent P2.
- **Evidence:** F4 lifecycle + storage contract + horizontal design requirement; S3 representative capability docs.
- **Evidence-Class:** `REPOSITORY_DERIVED+PROVIDER_DOCUMENTED`
- **Risk:** Local disk binds authority to a node and complicates N-node reads/node loss.
- **Simpler-Alternative:** Node-local filesystem.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Fails horizontal access/node-loss boundary.
- **Impact-On-Agent-Actions:** Gives next agent one capability qualification instead of redesigning paths.
- **Impact-On-Engineer-Actions:** Reduces migration work when scaling nodes.
- **Decision-Consequence:** Select capability class now, vendor later.
- **Governance-Consequence:** ADR/contract amendment.
- **F5/F5M-Consequence:** F5 must qualify backend; F5M later backfills.

### FIND-006

- **Priority:** P1
- **Claim:** Parquet is the best initial bulk tabular representation, but not a transaction/catalog layer.
- **Evidence:** Workload class + Apache Parquet format/page-index docs.
- **Evidence-Class:** `PROVIDER_DOCUMENTED+INFERENCE`
- **Risk:** Text/native row files increase scan cost; treating Parquet as a table transaction system creates correctness gap.
- **Simpler-Alternative:** Parquet + separate publication manifest.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Closes scan/interop need while keeping atomic publication explicit.
- **Impact-On-Agent-Actions:** Standardizes physical layout work.
- **Impact-On-Engineer-Actions:** Avoids standing DB import pipeline.
- **Decision-Consequence:** Parquet required for bulk tabular classes.
- **Governance-Consequence:** Schema/layout standard amendment.
- **F5/F5M-Consequence:** F5 layout qualification.

### FIND-007

- **Priority:** P1
- **Claim:** A bounded versioned manifest is sufficient initially and must have a hard stop before table-format reimplementation.
- **Evidence:** F4 atomic publication/readback/registration semantics + Iceberg feature set.
- **Evidence-Class:** `REPOSITORY_DERIVED+PROVIDER_DOCUMENTED`
- **Risk:** Directory listing is incoherent; an overgrown custom catalog recreates Iceberg badly.
- **Simpler-Alternative:** Immutable manifest + atomic pointer now; Iceberg later on explicit trigger.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Smallest mechanism covering coherent generation/read set.
- **Impact-On-Agent-Actions:** Bounds metadata implementation tasks.
- **Impact-On-Engineer-Actions:** Avoids premature catalog service while defining future migration seam.
- **Decision-Consequence:** Custom manifest now; Iceberg on trigger.
- **Governance-Consequence:** ADR/contract amendment.
- **F5/F5M-Consequence:** F5 defines manifest; F5M uses generation mapping.

### FIND-008

- **Priority:** P1
- **Claim:** SQLite is sufficient now; PostgreSQL is best fit later for shared multi-node control.
- **Evidence:** Program Map 1-node allowed; SQLite WAL same-host limitation; PostgreSQL queue-like locking.
- **Evidence-Class:** `REPOSITORY_DERIVED+PROVIDER_DOCUMENTED`
- **Risk:** Installing Postgres now adds service burden; sharing SQLite across nodes violates its model.
- **Simpler-Alternative:** Backend-neutral control contract with SQLite→Postgres trigger.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Preserves semantics while minimizing current operations.
- **Impact-On-Agent-Actions:** One clear migration trigger.
- **Impact-On-Engineer-Actions:** Avoids unnecessary DB ops before N-node need.
- **Decision-Consequence:** WHAT_BACKEND_IS_BEST_FIT and WHEN_REQUIRED are distinct.
- **Governance-Consequence:** ADR/Program Map amendment.
- **F5/F5M-Consequence:** F5 may qualify SQLite; N-node phase requires Postgres qualification.

### FIND-009

- **Priority:** P1
- **Claim:** Embedded analytical execution is a better initial fit than a standing analytical DB.
- **Evidence:** DuckDB direct Parquet/S3 docs; no pinned interactive SLO.
- **Evidence-Class:** `PROVIDER_DOCUMENTED+REPOSITORY_DERIVED`
- **Risk:** Standing service duplicates storage/ingest/backup before workload exists.
- **Simpler-Alternative:** Embedded DuckDB; direct Arrow/Python for small transforms.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** No service lifecycle and reads canonical immutable data directly.
- **Impact-On-Agent-Actions:** Less deployment/config work.
- **Impact-On-Engineer-Actions:** Fewer credentials/backup/HA domains.
- **Decision-Consequence:** DuckDB good fit; F5 storage closure need not install it.
- **Governance-Consequence:** ADR/Program Map can note execution path.
- **F5/F5M-Consequence:** Later analytical/backtest checkpoint, not F5 hard dependency.

### FIND-010

- **Priority:** P1
- **Claim:** Stateful backtests cannot be arbitrarily time-sharded.
- **Evidence:** State/position/path-dependence reasoning + deterministic execution contract.
- **Evidence-Class:** `INFERENCE`
- **Risk:** Boundary shards can see impossible state or future leakage.
- **Simpler-Alternative:** Parallelize independent run/model/parameter/scenario axes; keep time sequential unless checkpoint/state transfer is proven.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Simplest safe decomposition.
- **Impact-On-Agent-Actions:** Avoids distributed temporal coordinator tasks.
- **Impact-On-Engineer-Actions:** Reduces correctness debugging.
- **Decision-Consequence:** Backtest scheduler needs dependency/state contract for temporal shards.
- **Governance-Consequence:** Future execution standard/contract amendment.
- **F5/F5M-Consequence:** No F5 implementation effect; architecture field for later execution.

### FIND-011

- **Priority:** P1
- **Claim:** 1→N→1 requires stable work/result/physical identities and fencing independent of node count.
- **Evidence:** Work/execution/publication contracts.
- **Evidence-Class:** `REPOSITORY_DERIVED`
- **Risk:** Scale changes could otherwise alter truth, duplicate outputs or permit stale commits.
- **Simpler-Alternative:** Stable logical work ID + attempts + leases/fence + immutable objects/manifests.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Already aligns with pinned contracts and needs no distributed framework now.
- **Impact-On-Agent-Actions:** Defines invariant once.
- **Impact-On-Engineer-Actions:** Avoids replatforming data format at scale.
- **Decision-Consequence:** Bulk layout stays stable across node count.
- **Governance-Consequence:** Contract amendment only for physical refs.
- **F5/F5M-Consequence:** F5 must not introduce node-local semantic paths.

### FIND-012

- **Priority:** P1
- **Claim:** Backup and restore are at least two authority domains and restore must be proven clean-room.
- **Evidence:** AIFE hard boundary + control/object split.
- **Evidence-Class:** `REPOSITORY_DERIVED+INFERENCE`
- **Risk:** A backup may be corrupt/incomplete; replication may replicate deletion; control/object states may diverge.
- **Simpler-Alternative:** Separate DB and object restore proof + reconciliation/readback.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Directly tests recovery rather than inferring it.
- **Impact-On-Agent-Actions:** Gives next agent an exact restore sequence.
- **Impact-On-Engineer-Actions:** Reduces incident-time improvisation.
- **Decision-Consequence:** Restore qualification is part of physical architecture.
- **Governance-Consequence:** Backup standard amendment required.
- **F5/F5M-Consequence:** F5 qualification should include clean restore; F5M must re-prove after migration.

### FIND-013

- **Priority:** P2
- **Claim:** Non-reproducible source evidence deserves stronger protection than rebuildable projections.
- **Evidence:** Live stream gaps/provider replacements vs derived feature rebuildability.
- **Evidence-Class:** `PROVIDER_DOCUMENTED+INFERENCE`
- **Risk:** Uniform retention/backup policy wastes resources or loses irreplaceable evidence.
- **Simpler-Alternative:** Authority/rebuildability class per artifact.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** More precise and simpler than treating every byte equally.
- **Impact-On-Agent-Actions:** Reduces unnecessary backup/projection tasks.
- **Impact-On-Engineer-Actions:** Focuses operator effort on irreplaceable data.
- **Decision-Consequence:** Retention/backup should be class-aware.
- **Governance-Consequence:** Standards amendment.
- **F5/F5M-Consequence:** F5 metadata needs authority/rebuildability class.

### FIND-014

- **Priority:** P2
- **Claim:** Cache, broker, full-text and vector DB have no current mandatory workload.
- **Evidence:** Pinned contracts/manifests contain no measured trigger.
- **Evidence-Class:** `REPOSITORY_DERIVED`
- **Risk:** Speculative services expand operational surface.
- **Simpler-Alternative:** No service/process-local/rebuildable projection until measured.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Satisfies current use without new authority domains.
- **Impact-On-Agent-Actions:** Eliminates four speculative integration tracks.
- **Impact-On-Engineer-Actions:** Fewer services/upgrades/backups.
- **Decision-Consequence:** All DEFER with explicit triggers.
- **Governance-Consequence:** Program Map/ADR should resist speculative default stack.
- **F5/F5M-Consequence:** No F5 dependency.

### FIND-015

- **Priority:** P1
- **Claim:** F5 requires explicit physical authority fields and qualification evidence.
- **Evidence:** Storage/publication contracts define lifecycle but leave backend/layout physical identity open.
- **Evidence-Class:** `REPOSITORY_DERIVED`
- **Risk:** Without physical identity/seal/manifest/readback fields, ACK cannot be independently audited after migration/recovery.
- **Simpler-Alternative:** Additive physical field set defined in section 28.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Extends existing contracts rather than creates duplicate system.
- **Impact-On-Agent-Actions:** Gives F5 implementer a bounded schema task.
- **Impact-On-Engineer-Actions:** Makes recovery/audit deterministic.
- **Decision-Consequence:** F5 contract amendment required after owner review.
- **Governance-Consequence:** Artifact-contract disposition AMEND_REQUIRED.
- **F5/F5M-Consequence:** Direct F5 input; F5M consumes same identities.

### FIND-016

- **Priority:** P1
- **Claim:** Performance-dependent technology choices are blocked on representative AIFE measurement.
- **Evidence:** Unknown growth, ingest p95, concurrency, restore throughput, compaction amplification.
- **Evidence-Class:** `UNKNOWN`
- **Risk:** Fabricated scale assumptions would hard-code unjustified architecture.
- **Simpler-Alternative:** Benchmark matrix with explicit metrics/decision triggers.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Produces evidence rather than estimates.
- **Impact-On-Agent-Actions:** Next agent runs one bounded benchmark instead of debating vendors.
- **Impact-On-Engineer-Actions:** Engineering decisions become measurable.
- **Decision-Consequence:** ClickHouse/layout sizing/cache and some Iceberg triggers remain blocked.
- **Governance-Consequence:** Program Map should include qualification gate.
- **F5/F5M-Consequence:** F5 can qualify physical route; later expansions measured.

### FIND-017

- **Priority:** P2
- **Claim:** “S3-compatible” label is not sufficient backend qualification evidence.
- **Evidence:** AWS documents specific consistency/conditional/checksum semantics; compatibility implementations may vary.
- **Evidence-Class:** `PROVIDER_DOCUMENTED+INFERENCE`
- **Risk:** Assumed semantics can break conditional publication/readback correctness.
- **Simpler-Alternative:** Capability-test the actual selected backend.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** A small conformance suite is simpler than vendor assumption debugging.
- **Impact-On-Agent-Actions:** Adds one finite qualification task.
- **Impact-On-Engineer-Actions:** Reduces production correctness incidents.
- **Decision-Consequence:** Vendor selection remains open; capability class is authoritative.
- **Governance-Consequence:** ADR/contract qualification fields.
- **F5/F5M-Consequence:** F5 must test actual backend.

### FIND-018

- **Priority:** P1
- **Claim:** The architecture can defer vendor selection while still making a concrete F5 decision.
- **Evidence:** Pinned Program Map intentionally leaves vendor open; capability needs are derivable from contracts/workloads.
- **Evidence-Class:** `REPOSITORY_DERIVED+INFERENCE`
- **Risk:** Vendor-first decision couples semantics to deployment and can block independence review.
- **Simpler-Alternative:** Specify capability class + qualification criteria + expansion triggers.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** This is enough to implement neutral interfaces later without deciding procurement now.
- **Impact-On-Agent-Actions:** Reduces vendor-specific tasks in F5 planning.
- **Impact-On-Engineer-Actions:** Separates engineering contract from deployment/TCO decision.
- **Decision-Consequence:** Architecture candidate is concrete but vendor-neutral.
- **Governance-Consequence:** ADR amendment records capability classes.
- **F5/F5M-Consequence:** F5 chooses/qualifies actual provider in owner-authorized implementation stage.

## Итоговое решение (контракт)

### Runtime Disposition

- Runtime-Oriented: yes
- Effective Closure: no
- Downstream Disposition: `Blocked`
- Why findings-only is insufficient: P1 runtime architecture требует отдельного distinct-agent review gate и owner consolidation.
- Required next contour: `aife-server-data-foundation / F5R / data-backend-architecture` review-gate resolution.
- Materialization target: будущий owner-reviewed consolidated F5R carrier; этот artifact остаётся research evidence.
- Blocker, if any: `P1_DUAL_AGENT_GATE=NOT_FORMALLY_CLOSED`.

### Materialization Disposition

- Program Root: `aife-server-data-foundation`
- Wave / Topic: `F5R / data-backend-architecture`
- Program-Setup Disposition: `blocker`
- Execution Root: `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/`
- Physical Use Class: `control-plane-evidence-only`
- Operational Surface Target: `N/A`
- Physical Integration Target: `N/A`
- Current Status: `blocked`
- Readiness Threshold Met: `no`
- DEV_TZ Outcome: `blocked`
- Delivery Claim Allowed: `no`
- Required Next Prompt: `N/A`
- Required Next Artifact: distinct-agent F5R evidence; затем owner-authorized consolidation artifact
- Blocker: `CANONICAL_DISTINCT_AGENT_REVIEW=NO`; `P1_DUAL_AGENT_GATE=NOT_FORMALLY_CLOSED`
- Why findings-only is forbidden here: same-identity independent context не закрывает P1 distinct-agent gate.
- Why control-plane-only is not delivery: runtime/storage/owner artifacts не изменены.

### 1. Статус темы

- Исследование по теме: ЗАКРЫТО
- Состояние волны: ЧАСТИЧНО
- Переход к `DEV_TZ`: ЗАПРЕЩЁН
- Архитектурный статус: `local-candidate` (локальный кандидат)
- `RESEARCH_RUN=INDEPENDENT_SECOND_RUN`
- `REPOSITORY_BASE_HEAD=2b82c75a67ed7ce5cd87cae2ccf02f09677d200c`
- `REPOSITORY_BASE_TREE=2615dcd21570f0816be39c574b3b9f8ef1c1bc16`
- `SECOND_CONTEXT_INDEPENDENT_RESEARCH=YES`
- `CANONICAL_AGENT_IDENTITY=_chatgpt-gpt`
- `CANONICAL_DISTINCT_AGENT_REVIEW=NO`
- `P1_DUAL_AGENT_GATE=NOT_FORMALLY_CLOSED`
- `REPOSITORY_MUTATION_BY_RESEARCH_RUN=NO`
- `OWNER_ARTIFACT_MUTATION=NO`
- `DEV_TZ_ALLOWED=NO`
- `F5_ALLOWED=NO`
- `F5M_ALLOWED=NO`

### 2. Граница контекстного пакета

- `Minimum-Packet`: pinned repository authority + canonical AIFE governance + этот second-context artifact + distinct-agent gate evidence.
- `Expansion-Trigger`: explicit orchestration/owner review-gate resolution.
- `Expansion-Authority`: orchestrator / owner governance.

### 3. Граница полномочий

- Переписывание маршрута владельца (`owner-route`): ЗАПРЕЩЕНО
- Собственная иерархия истины (`truth hierarchy`): ЗАПРЕЩЕНО
- Подмена опорного репозиторного доказательства (`repo-proof core`): ЗАПРЕЩЕНА

### 4. Масштабируемость решения

- `Scaling-Class`: ЛОКАЛЬНЫЙ КАНДИДАТ
- Ограничение локального удобства: 1→N→1 seams остаются candidate до P1 gate resolution и owner consolidation.

### 5. Решение у владельца

- `STD`: ТРЕБУЕТСЯ
- `ADR`: ТРЕБУЕТСЯ
- `CONTRACT`: ВСПОМОГАТЕЛЬНЫЙ
- `OWNER_ADR_DISPOSITION=AMEND_REQUIRED`
- `OWNER_STANDARD_DISPOSITION=AMEND_REQUIRED`
- `OWNER_ARTIFACT_CONTRACT_DISPOSITION=AMEND_REQUIRED`
- `PROGRAM_MAP_DISPOSITION=AMEND_REQUIRED`

### 6. Блокеры

- Блокеры исследования: НЕТ
- Блокеры решения: `CANONICAL_DISTINCT_AGENT_REVIEW=NO`; `P1_DUAL_AGENT_GATE=NOT_FORMALLY_CLOSED`.
- Ограничение перехода к `DEV_TZ`: review-gate resolution и последующая owner-authorized consolidation обязательны.

### 7. Обязательный следующий шаг

A) Следующее исследование:

- `Topic-Slug`: `data-backend-architecture`
- `Scope-Slug`: `aife-server-data-foundation`
- Причина: `RETURN_SECOND_RESEARCH_TO_ORCHESTRATION_FOR_REVIEW_GATE_RESOLUTION_AND_LATER_CONSOLIDATION`; при сохранении P1 distinct-agent requirement получить genuinely distinct canonical-agent research evidence.

### 8. Явные запреты

- `SELF_CONSOLIDATION`
- `OWNER_ARCHITECTURE_PUBLICATION`
- `ADR_MUTATION`
- `STANDARD_MUTATION`
- `ARTIFACT_CONTRACT_MUTATION`
- `PROGRAM_MAP_MUTATION`
- `DEV_TZ`
- `F5`
- `F5M`
- `CONSOLIDATION_ALLOWED=NO` до отдельного review-gate resolution.
