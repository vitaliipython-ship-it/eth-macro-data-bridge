---
title: "RESEARCH CONSOLIDATED: aife-server-data-foundation — data-backend-architecture"
status: active
owner: Architecture Lead
created: 2026-08-27
updated: 2026-08-27
review_cycle_days: 30
next_review_due: 2026-09-26
category: architecture
doc_type: analysis
language: ru
tags: [research, consolidated, server, data, storage, analytics, backtest, f5r]
---

# RESEARCH CONSOLIDATED: aife-server-data-foundation — data-backend-architecture

## 1. Краткий итог

Эта сводка объединяет два уже материализованных независимых по execution-context исследования одной Task-Family. Она не является третьим исследованием, owner architecture publication, DEV_TZ или F5 implementation.

Консолидированный локальный кандидат:

```text
ARCHITECTURE_STATUS=local-candidate
CONTROL_STATE_REQUIRED_CAPABILITY=DURABLE_TRANSACTIONAL_CONTROL_STATE_WITH_STABLE_WORK_ATTEMPT_CLAIM_LEASE_FENCE_IDEMPOTENT_PUBLICATION_REGISTRATION
CONTROL_STATE_INITIAL_PROFILE=SQLITE_WAL_SINGLE_INITIAL_SERVER
CONTROL_STATE_EXPANSION_PROFILE=POSTGRESQL_PREFERRED_AND_REQUIRED_BEFORE_SHARED_MULTI_NODE_CONTROL_QUALIFICATION
BULK_STORAGE_REQUIRED_CAPABILITY=SHARED_DURABLE_IMMUTABLE_OBJECT_OR_BLOB
BULK_STORAGE_PRODUCT=UNSELECTED
TABULAR_FORMAT=PARQUET_REQUIRED_FOR_BULK_TABULAR
RAW_NATIVE_BLOB_PRESERVATION=ALLOWED_WHEN_REQUIRED_FOR_SOURCE_FIDELITY
MANIFEST_MODEL=IMMUTABLE_BOUNDED_VERSIONED_MANIFEST_PLUS_TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION
GENERAL_TRANSACTIONAL_CATALOG=DEFER
OPEN_TABLE_FORMAT=DEFER
ICEBERG=REFERENCE_CANDIDATE_ON_TRIGGER
ANALYTICAL_EXECUTION_SEAM=REQUIRED_ARCHITECTURALLY
DUCKDB=PREFERRED_CANDIDATE_NOT_F5_STORAGE_CLOSURE_DEPENDENCY
CLICKHOUSE=DEFER_BLOCKED_ON_MEASUREMENT
PIT=EXACT_INFORMATION_HORIZON_PLUS_EXACT_READ_SET
F5=QUALIFY_NEW_INCOMING_PHYSICAL_ROUTE_ON_BOUNDED_REPRESENTATIVE_DATA
F5M=LATER_CORPUS_MIGRATION_AND_CUTOVER
```

Реальных нерешённых расхождений между source artifacts после evidence-based consolidation нет. Остаются measurement- и owner-governance-bound вопросы: точный object backend product, numeric SLO/RPO/RTO, Parquet partition/file/row-group sizing, аналитический benchmark и будущие Iceberg/ClickHouse triggers.

## 2. Consolidation provenance

```text
TASK_FAMILY=AIFE-SERVER-DATA-STORAGE-ANALYTICS-BACKTEST-ARCHITECTURE-RESEARCH-V1
RUN_ID=F5R-CANONICAL-CONSOLIDATION-R01
MODE=consolidation
RESEARCH_MODE=CONSOLIDATION_OF_EXISTING_ACCEPTED_RESEARCH
NEW_INDEPENDENT_RESEARCH_RUN=NO
CONSOLIDATION_VERIFICATION=NO_NEW_BROAD_EXTERNAL_RESEARCH_REQUIRED
RESEARCH_BASE_HEAD=2b82c75a67ed7ce5cd87cae2ccf02f09677d200c
RESEARCH_BASE_TREE=2615dcd21570f0816be39c574b3b9f8ef1c1bc16
```

Сводка использует только два source Research artifacts, общий pinned repository base, canonical AIFE governance и уже присутствующие в source artifacts technical evidence. Новая broad external research волна не выполнялась.

## 3. Source artifact identities

| Source | Path | Size | SHA-256 | Git blob | Immutable in this task |
| --- | --- | ---: | --- | --- | --- |
| Research #1 | `AIFE/staging/docs/98-Reviews/research/2026-08/aife-server-data-foundation/RESEARCH_aife-server-data-foundation_general_data-backend-architecture_2026-08-27_chatgpt-gpt.md` | 71324 | `e56de1883e34dd191897dd3108f6732303ebe0cbc0ea63bd74ec02d800cd2033` | `d60aa5b16b9ee99838b0a88337ccc744b50ec99a` | yes |
| Research #2 | `AIFE/staging/docs/98-Reviews/research/2026-08/aife-server-data-foundation/RESEARCH_aife-server-data-foundation_independent-second-run_data-backend-architecture_2026-08-27_chatgpt-gpt.md` | 98559 | `3ba3990a1cf32d3b0b79897daa7169a614622878ef6b6ec730c00de5e39e1ecf` | `63e5ffd6ce9493e0d01345d17c0e41cf263dc7ca` | yes |

Оба source artifacts относятся к одному substantive base `2b82c75a… / 2615dcd2…`. Их исторические terminal states не переписываются этой консолидацией.

## 4. Owner admissibility decision

Материализуется точное task-scoped owner ruling:

```text
OWNER_DECISION_ID=F5R-P1-SAME-MODEL-INDEPENDENT-RESEARCH-ADMISSIBILITY-2026-08-27
TASK_SCOPED_OWNER_DECISION=YES
DECISION_SCOPE=THIS_TASK_FAMILY_ONLY
OWNER_DECISION=ACCEPT_TWO_GENUINELY_ISOLATED_SAME_MODEL_RESEARCH_RUNS_AS_SUFFICIENT_P1_DUAL_RESEARCH_EVIDENCE_FOR_THIS_TASK
FIRST_AND_SECOND_EXECUTION_CONTEXTS_ISOLATED=YES
SECOND_RUN_USED_FIRST_RESEARCH_AS_INPUT=NO
SECOND_RUN_USED_FIRST_RESEARCH_SUMMARY_AS_INPUT=NO
SECOND_RUN_USED_FIRST_RESEARCH_VERDICTS_AS_INPUT=NO
SAME_MODEL_FAMILY=YES
SAME_CANONICAL_AGENT_IDENTITY=YES
INDEPENDENCE_ACCEPTED_ON_EXECUTION_CONTEXT_AND_INFORMATION_ISOLATION=YES
DISTINCT_MODEL_FAMILY_REQUIRED_FOR_THIS_TASK=NO
DISTINCT_AGENT_SUFFIX_REQUIRED_FOR_THIS_TASK=NO
P1_DUAL_RESEARCH_EVIDENCE=ACCEPTED
P1_RESEARCH_GATE=SATISFIED_BY_OWNER_DECISION
THIRD_RESEARCH_REQUIRED=NO
CONSOLIDATION_ALLOWED=YES
GLOBAL_POLICY_CHANGE=NO
```

Это решение разрешает текущую consolidation только в этой Task-Family. Оно не меняет global AIFE dual-agent semantics и не является owner architecture approval.

## 5. Historical gate succession

Research #2 корректно зафиксировал состояние до task-scoped owner ruling:

```text
HISTORICAL_PRE_OWNER_DECISION_STATE=P1_DUAL_AGENT_GATE_NOT_FORMALLY_CLOSED
CANONICAL_DISTINCT_AGENT_REVIEW_AT_SOURCE_TIME=NO
```

После owner ruling действует successor state:

```text
TASK_SCOPED_OWNER_SUCCESSOR_DECISION=P1_RESEARCH_GATE_SATISFIED
P1_DUAL_RESEARCH_EVIDENCE=ACCEPTED
THIRD_RESEARCH_REQUIRED=NO
```

Это succession, а не ретроактивная коррекция source evidence.

## 6. Verified authority

```text
FRESH_INITIAL_WIP_HEAD=c5d4bd71705a4972c684774dc24a2ab391acb19a
FRESH_INITIAL_WIP_TREE=c45f8ecea9cd28a044fb34ba2f4937824bc9e794
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_REFERENCE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_REFERENCE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
TOOLCHAIN_PACKAGE_SHA256=36c64406c57f51c1dc810a64a3c1a599a39dce6f8a7d02ac1b9fd32a2ad5192d
TOOLCHAIN_ID=1b3f6d7281419ae7a692e9f3b69019c7ed13761ee51775ad8f37aa1f85b585eb
QUALITY_POLICY_ID=8c0004758ca1d5a6ddbf013a9a0069a927b9bf87fbb23cedd4f5927835d388b3
```

Canonical naming подтверждает topic-level consolidation filename без per-agent suffix: `RESEARCH_CONSOLIDATED_<scope_slug>_<topic_slug>_<date>.md`. Canonical final-block protocol применяется полностью.

Fresh WIP authority дополнительно содержит proposed `AIFE/staging/genome/adr/data/ADR-DATA-FOUNDATION-001.md`, уже охватывающий тот же Server/Data Foundation architecture boundary, и Program Map с `INITIAL_ONE_SERVER=ALLOWED`, `MULTI_NODE_IMPLEMENTATION_NOW=NO`, `F5=ETH_HIGH_CARDINALITY_P2_PHYSICAL_LIFECYCLE`, `F5M=ETH_EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER`.

## 7. Convergence matrix

Матрица включает все 47 обязательных topic dimensions из запуска.

| # | Topic | Classification | Consolidated result |
| ---: | --- | --- | --- |
| 1 | F4→F5 architecture gap | `CONVERGED` | F5 закрывает physical lifecycle P2, не переопределяя domain semantics. |
| 2 | semantic vs physical authority | `CONVERGED` | Domain/Data Bridge владеет semantics; Server/storage владеет generic physical lifecycle. |
| 3 | data-class model | `CONVERGED` | Нужна смешанная физическая модель для control, bulk tabular, raw blobs, derived/projection classes. |
| 4 | measured baseline | `PARTIALLY_CONVERGED` | Bounded repository corpus измерен, но AIFE-wide capacity/performance baseline остаётся недостаточным. |
| 5 | high-cardinality bulk storage | `CONVERGED` | Node-independent durable immutable bulk substrate требуется для P2. |
| 6 | object/blob capability | `CONVERGED` | Требуется capability class, а не преждевременный vendor binding. |
| 7 | Parquet | `CONVERGED` | Default для bulk tabular scan workloads. |
| 8 | native/raw blob preservation | `CONVERGED` | Raw/non-tabular evidence допускает immutable native/blob bytes, если табуляризация теряет evidence. |
| 9 | partitioning | `CONVERGED` | Логическая partition identity нужна; exact physical granularity и sizes — benchmark-bound. |
| 10 | small-file policy | `CONVERGED` | One-event-per-object запрещён как default; batching/sealing обязателен. |
| 11 | compaction | `CONVERGED` | Copy-on-write, asynchronous, provenance-preserving, non-semantic. |
| 12 | manifest model | `CONVERGED` | Immutable bounded versioned manifests фиксируют exact generation/read-set. |
| 13 | transactional catalog | `PARTIALLY_CONVERGED` | Минимальная transactional registration/current-pointer нужна; general custom catalog service пока не нужен. |
| 14 | Iceberg/open table format | `CONVERGED` | Не required now; trigger — table-format complexity/concurrency/evolution/metadata scale. |
| 15 | control-state backend | `DIVERGED` | Разделено на required capability и current implementation profile. |
| 16 | SQLite timing | `DIVERGED` | Принят как simplest initial single-node control substrate. |
| 17 | PostgreSQL timing | `DIVERGED` | Перенесён в mandatory expansion profile перед shared multi-node control или раньше по contention/HA trigger. |
| 18 | work/claims/leases/fencing | `CONVERGED` | Stable work ID, durable attempts, leases, monotonic fencing, stale rejection, idempotent publication. |
| 19 | analytical engine seam | `CONVERGED` | Embedded/process-local analytical execution предпочтительнее standing authority/service. |
| 20 | DuckDB timing | `DIVERGED` | Good fit/preferred candidate; не hard dependency F5 storage closure, нужен к analytical/backtest acceptance если simpler direct path не проходит benchmark. |
| 21 | standing analytical service | `CONVERGED` | Не initial requirement. |
| 22 | ClickHouse | `CONVERGED` | Deferred rebuildable projection; trigger только measured interactive/concurrent SLO failure. |
| 23 | cache/Redis | `CONVERGED` | Deferred до measured hot-read/cache requirement. |
| 24 | broker/Kafka/event bus | `CONVERGED` | Deferred до real durable fanout/offset/replay/decoupled-fleet requirement. |
| 25 | full-text/search | `CONVERGED` | Dedicated search deferred; projection/rebuild semantics only. |
| 26 | vector DB | `CONVERGED` | Deferred до explicit corpus/recall/latency workload. |
| 27 | PIT | `CONVERGED` | Storage time travel недостаточен; exact information horizon обязателен. |
| 28 | effective_at | `CONVERGED` | Обязательная temporal axis. |
| 29 | known_at | `CONVERGED` | Обязательная anti-lookahead temporal axis. |
| 30 | provider/source revision | `CONVERGED` | Обязательная часть reproducible read-set. |
| 31 | source sequence/gap evidence | `CONVERGED` | Preserve sequence/change/update IDs and gap/resync evidence where provider supplies them. |
| 32 | exact generation/read-set | `CONVERGED` | Backtest/analysis binds immutable generation and exact object/file inventory. |
| 33 | backtest decomposition | `CONVERGED` | Parallelize independent strategy/model/parameter/scenario/run axes. |
| 34 | stateful temporal sharding | `CONVERGED` | Forbidden without checkpoint/state-transfer/deterministic replay proof. |
| 35 | 1→N→1 scaling | `CONVERGED` | Node count must not change semantic/work/result identities or physical data format. |
| 36 | backup | `CONVERGED` | Authority domains backed up separately; replication is not backup. |
| 37 | restore | `CONVERGED` | Clean-environment restore + reconciliation + independent readback required. |
| 38 | HA | `CONVERGED` | Seams required; exact topology blocked on owner RPO/RTO and deployment evidence. |
| 39 | rebuildability classes | `CONVERGED` | Irreplaceable source evidence separated from rebuildable projections/derived data. |
| 40 | benchmark requirements | `CONVERGED` | Performance-dependent choices need representative AIFE benchmark and owner-defined SLO. |
| 41 | F5 scope | `CONVERGED` | Qualify new incoming physical lifecycle on bounded representative data. |
| 42 | F5M boundary | `CONVERGED` | Existing corpus migration/cutover remains later stage after F5 route qualification. |
| 43 | vendor selection | `CONVERGED` | Capability classes can be decided while products remain unselected/reference candidates. |
| 44 | ADR disposition | `DIVERGED` | Existing proposed ADR is the correct owner; AMEND_REQUIRED. |
| 45 | Standards disposition | `CONVERGED` | Amend existing DATA standards; no new broad parallel standard by default. |
| 46 | Artifact Contract disposition | `CONVERGED` | Amend existing Server/Data contracts with physical identity, manifest, PIT, readback, restore/qualification bindings. |
| 47 | Program Map disposition | `CONVERGED` | Amend after owner architecture publication to materialize F5/F5M gates and triggers. |

Итоговые количества:

```text
CONVERGED_TOPIC_COUNT=40
PARTIALLY_CONVERGED_TOPIC_COUNT=2
RESOLVED_DIVERGENCE_TOPIC_COUNT=5
UNRESOLVED_DIVERGENCE_COUNT=0
TOTAL_REQUIRED_TOPIC_COUNT=47
```

## 8. Divergence matrix

| # | Area | Research #1 | Research #2 | AIFE authority | Resolution | Why chosen | Residual trigger |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Measured baseline | `MEASURED_BASELINE=INSUFFICIENT` для AIFE-wide capacity/performance. | Repository-derived: 30 OHLC series, 176579 rows, 509 partitions, 25 rolling files, 2848828-byte bounded subset. | Program Map не содержит AIFE-wide throughput/growth/SLO baseline. | `PARTIALLY_CONVERGED`: оба утверждения истинны на разных уровнях. Bounded corpus baseline существует; AIFE-wide capacity/performance baseline недостаточен. | Никакой distributed/OLAP/table-format механизм нельзя продвигать только по bounded corpus counts. | Owner-defined representative benchmark. |
| 2 | Transactional metadata/catalog | Versioned manifests required; separate transactional catalog deferred/optional later. | Versioned manifests + transactional current-generation registration/pointer in control state required; general custom catalog deferred. | Publication lifecycle требует atomic registration/ACK, но не общего table catalog. | `PARTIALLY_CONVERGED`: минимальная transactional pointer/registration семантика required now внутри control state; отдельный general catalog service deferred. | Закрывает atomic publication без создания собственного table format. | Multi-writer table commits, schema/partition evolution, manifest planning scale. |
| 3 | Control-state backend | PostgreSQL required now for durable control/sparse metadata. | SQLite/WAL now; PostgreSQL best fit later for shared multi-node control. | `INITIAL_ONE_SERVER=ALLOWED`; `MULTI_NODE_IMPLEMENTATION_NOW=NO`; horizontal scale by design remains mandatory. | `RESOLVED_DIVERGENCE`: required now is backend-neutral durable transactional control capability; current default profile is SQLite/WAL on the initial server. | PostgreSQL now increases standing service/credentials/backup/HA actions without closing a current mandatory risk. | First shared multi-node control qualification, cross-node writers, measured SQLite contention or HA requirement. |
| 4 | SQLite timing | Not part of first minimum stack. | Required now as simplest single-node control substrate. | Pinned program explicitly permits one initial server; current D8/control evidence already uses SQLite/WAL semantics. | `RESOLVED_DIVERGENCE`: SQLite/WAL is current default implementation profile, not semantic contract. | No new standing DB service and no semantic rewrite later if identities/state transitions stay backend-neutral. | Same as control expansion trigger. |
| 5 | PostgreSQL timing | Required now. | Required later at first shared multi-node control qualification. | AIFE requires future horizontal seam, not multi-node deployment now. | `RESOLVED_DIVERGENCE`: PostgreSQL is preferred expansion candidate and becomes required before shared multi-node transactional control; owner product binding remains pending. | Delaying product deployment reduces operator work and does not change work/publication semantics. | Cross-node claims/leases/fencing/current-pointer writes; contention/HA SLO. |
| 6 | DuckDB timing | Embedded DuckDB per worker required now in minimum stack. | Good fit; required later for analytical/backtest plane unless direct Arrow/Python benchmark is sufficient; not F5 storage dependency. | F5 is physical storage lifecycle; analytical consumer acceptance is a separate requirement. | `RESOLVED_DIVERGENCE`: analytical execution seam required architecturally now, DuckDB is preferred candidate, but F5 physical closure does not require installing/using it. | Small transforms may use direct Python/Arrow; standing analytical service remains unnecessary. | Representative backtest/scan benchmark or start of analytical acceptance. |
| 7 | ADR owner | Create ADR after consolidation. | Amend proposed `ADR-DATA-FOUNDATION-001`. | Staged WIP already contains proposed `ADR-DATA-FOUNDATION-001` covering the same Server/Data Foundation decision boundary. | `RESOLVED_DIVERGENCE`: `OWNER_ADR_DISPOSITION=AMEND_REQUIRED`. | Amending the existing owner avoids duplicate architecture authorities. | Owner governance publication step. |

Все пять material divergences resolved; две partial-convergence зоны также сведены без скрытия исходного различия. Ни одна не требует третьего research run.

## 9. F4→F5 consolidated gap

Оба исследования сходятся: F4 уже закрепляет semantic authority split и generic lifecycle contracts. F5R нужен, потому что F5 иначе закодировал бы physical backend/layout/control/restore choices без versioned architecture decision.

Консолидированная граница:

```text
VALIDATED_DOMAIN_ARTIFACT
→ DURABLE_INGEST_OR_BOUNDED_SPOOL
→ DETERMINISTIC_BATCH_AND_PHYSICAL_IDENTITY
→ IMMUTABLE_OBJECT_OR_PARQUET_WRITE
→ SEAL
→ INDEPENDENT_READBACK_AND_CHECKSUM
→ IMMUTABLE_VERSIONED_MANIFEST
→ TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION
→ CANONICAL_REGISTRATION
→ ACK
```

Domain finality/revision/gap semantics остаются upstream. Physical storage не становится market-data authority.

## 10. Consolidated data-class model

| Class | Consolidated placement | Authority / rebuildability |
| --- | --- | --- |
| A. operational/control | durable transactional control substrate; SQLite/WAL initial, PostgreSQL expansion | operational authority; partially reconstructible |
| B. high-cardinality raw market | shared object/blob; Parquet where tabular, native immutable evidence where needed | source/domain evidence; often non-rebuildable |
| C. regular market history | object/blob + Parquet + manifest | domain history; revisions/generations preserved |
| D. sparse analytical history | control relational substrate for sparse metadata; object for large payload | analytical owner; versioned |
| E. news/source evidence | relational metadata + immutable raw snapshots where permitted | source evidence; often non-rebuildable |
| F. indicators/features | Parquet/object + lineage metadata | rebuildable if exact inputs/method retained |
| G. AI/prediction/model data | object/blob + Parquet; relational model/run metadata | mixed authority/rebuildability |
| H. strategy/experiment | durable control metadata + immutable configs/results | research/control authority |
| I. backtesting | run metadata in control substrate; bulk results in object/Parquet | reproducible with pinned read-set/config |
| J. search/retrieval | rebuildable projections | never semantic authority by default |
| K. generic blobs | immutable object/blob | per-artifact authority class |

`ONE_DATABASE=NO` сохраняется без обязательного polyglot service fleet.

## 11. Consolidated measured-baseline disposition

Research #2 предоставляет bounded repository-derived corpus baseline:

```text
CURRENT_BOUNDED_CORPUS_BASELINE=AVAILABLE
REGULAR_OHLC_SERIES=30
CLOSED_HISTORY_ROWS=176579
HISTORY_PARTITIONS=509
ROLLING_OHLC_FILES=25
VISIBLE_BINANCE_ROLLING_SUBSET_BYTES=2848828
```

Research #1 корректно отмечает отсутствие AIFE-wide capacity/performance evidence:

```text
AIFE_WIDE_CAPACITY_PERFORMANCE_BASELINE=INSUFFICIENT
GROWTH_30_90_365D=UNKNOWN
INGEST_P50_P95_PEAK=UNKNOWN
QUERY_CONCURRENCY=UNKNOWN
BACKTEST_SCAN_THROUGHPUT=UNKNOWN
RESTORE_THROUGHPUT=UNKNOWN
COMPACTION_AMPLIFICATION=UNKNOWN
```

Оба состояния одновременно истинны. Bounded corpus помогает проектировать representative benchmark, но не доказывает необходимость ClickHouse, Iceberg, broker, cache или distributed control deployment.

## 12. Semantic/physical boundary

Каноническая зависимость остаётся односторонней:

```text
DOMAIN_SEMANTICS_AND_IDENTITIES
→ VALIDATED_NEUTRAL_ARTIFACT_AND_PROVENANCE
→ GENERIC_SERVER_PHYSICAL_LIFECYCLE
```

Consumer contract не должен зависеть от S3 key, local pathname, SQLite rowid, PostgreSQL table name, DuckDB file path, ClickHouse part или Iceberg metadata file. Backend locators остаются opaque implementation references.

## 13. Bulk/object storage decision

```text
BULK_STORAGE_DECISION=REQUIRED_CAPABILITY_NOW
CAPABILITY=SHARED_DURABLE_IMMUTABLE_OBJECT_OR_BLOB
PRODUCT_BINDING=UNSELECTED
NODE_LOCAL_FILESYSTEM_AS_SOLE_P2_FOUNDATION=REJECTED
```

Минимальный capability profile: durable write/finalize, checksum/size, independent readback, immutable or conditional create/update semantics, inventory/listing, multipart/bounded upload, encryption, credential rotation, lifecycle/retention and clean restore qualification. “S3-compatible” label alone не считается semantic proof этих свойств.

## 14. Parquet/layout decision

```text
TABULAR_FORMAT_DECISION=PARQUET_REQUIRED_FOR_BULK_TABULAR
RAW_NATIVE_BLOB_PRESERVATION=ALLOWED_WHEN_SOURCE_FIDELITY_REQUIRES
PARTITION_IDENTITY=REQUIRED_NOW
EXACT_PARTITION_GRANULARITY=BLOCKED_ON_MEASUREMENT
EXACT_FILE_SIZE=BLOCKED_ON_MEASUREMENT
EXACT_ROW_GROUP_SIZE=BLOCKED_ON_MEASUREMENT
```

Parquet решает columnar scan/interoperability risk, но не заменяет transaction/catalog/PIT semantics.

## 15. Small-file/compaction decision

```text
ONE_EVENT_OR_OBSERVATION_PER_OBJECT=FORBIDDEN_AS_DEFAULT
BOUNDED_BATCH_AND_SEAL=REQUIRED
COMPACTION=COPY_ON_WRITE_ASYNC_PROVENANCE_PRESERVING_NON_SEMANTIC
IN_PLACE_CANONICAL_REWRITE=FORBIDDEN
```

Publication pointer переключается только после полного write/seal/readback нового generation. Прерывание compaction до switch не меняет canonical generation; старые объекты удаляются только отдельным retention/GC решением.

## 16. Manifest/catalog/open-table-format decision

Initial profile:

```text
MANIFEST_CATALOG_DECISION=
IMMUTABLE_BOUNDED_VERSIONED_MANIFEST
+ TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION_IN_CONTROL_STATE

GENERAL_CUSTOM_TRANSACTIONAL_CATALOG=DEFER
OPEN_TABLE_FORMAT_CAPABILITY=NOT_REQUIRED_NOW
ICEBERG_PRODUCT_STATUS=REFERENCE_CANDIDATE_ON_TRIGGER
```

Hard trigger, после которого custom metadata становится неприемлемым: AIFE начинает реализовывать значимую часть общего table format — concurrent table-level commits, snapshot mutation/expiry semantics, frequent schema/partition evolution, large manifest planning/pruning, general optimistic concurrency or multi-engine transactional table contract. Тогда предпочтителен open table format вместо дальнейшего роста bespoke metadata.

## 17. Control-state decision and timing

Разделяются четыре слоя.

```text
CONTROL_STATE_CAPABILITY_DECISION=REQUIRED_NOW
CONTROL_STATE_CAPABILITY=DURABLE_TRANSACTIONAL_STATE_FOR_WORK_ATTEMPTS_CLAIMS_LEASES_FENCING_IDEMPOTENCY_PUBLICATION_AND_CURRENT_GENERATION
CONTROL_STATE_INITIAL_PROFILE=SQLITE_WAL_SINGLE_INITIAL_SERVER
CONTROL_STATE_EXPANSION_PROFILE=POSTGRESQL_PREFERRED_CANDIDATE_AND_REQUIRED_BEFORE_SHARED_MULTI_NODE_CONTROL_QUALIFICATION
CONTROL_STATE_VENDOR_BINDING=OWNER_DECISION_PENDING
```

Backend-neutral должны остаться stable work/slot IDs, attempt identity, claim/lease semantics, monotonic fencing, stale-owner rejection, idempotency/publication state, generation/current-pointer semantics и consumer-facing references. SQLite path/rowid и PostgreSQL schema/table names не входят в semantic contract.

Delaying PostgreSQL до expansion trigger не требует semantic rewrite. Вводить standing DB service сейчас увеличивает deployment, credential, backup, monitoring, upgrade and HA actions при отсутствии обязательного multi-node runtime requirement.

## 18. PIT/history model

```text
PIT_DECISION=REQUIRED_CROSS_LAYER_CONTRACT
```

Exact replay identity включает как минимум: `effective_at`, `known_at`, provider/source revision, source sequence/update/change identity где доступно, gap/resync boundary, source generation/manifest, schema/layout version, replay cutoff, universe/time range, method/model/strategy version и exact read-set/content identity.

Storage-native snapshots или table time travel могут помочь физической адресации, но не заменяют historical knowability и semantic revision lineage.

## 19. Backtest execution/decomposition

Безопасные horizontal axes: strategy/model version, parameter set, scenario, independent run/seed и instrument/universe только при доказанной independence.

```text
TIME_SHARDING_STATEFUL_BACKTEST=FORBIDDEN_WITHOUT_CHECKPOINT_OR_STATE_TRANSFER_OR_DETERMINISTIC_REPLAY_PROOF
```

Один stateful run остаётся chronological, пока не материализована корректная boundary-state model.

## 20. Analytical engine decision and timing

```text
ANALYTICAL_EXECUTION_DECISION=EMBEDDED_PER_WORKER_EXECUTION_PREFERRED
ANALYTICAL_EXECUTION_SEAM_REQUIRED_NOW=YES_ARCHITECTURALLY
DUCKDB_GOOD_FIT=YES
DUCKDB_PRODUCT_STATUS=PREFERRED_CANDIDATE
DUCKDB_REQUIRED_FOR_F5_PHYSICAL_STORAGE_CLOSURE=NO
DIRECT_ARROW_PYTHON_ALLOWED_FOR_SMALL_TRANSFORMS=YES
DUCKDB_REQUIRED_BEFORE_ANALYTICAL_BACKTEST_ACCEPTANCE=CONDITIONAL_ON_REPRESENTATIVE_BENCHMARK_AND_WORKLOAD
SHARED_DISTRIBUTED_DUCKDB_DATABASE=REJECTED_REQUIRED_NOW
```

Analytical consumer seam должен быть предусмотрен сейчас, но F5 может доказать storage lifecycle без forcing DuckDB. Когда начинается real analytical/backtest acceptance, embedded DuckDB является default candidate; simpler direct path остаётся допустимым, если benchmark доказывает достаточность.

## 21. Horizontal 1→N→1 model

```text
NODE_ID_IS_NOT_SEMANTIC_IDENTITY
STABLE_WORK_ID=REQUIRED
DURABLE_ATTEMPTS=REQUIRED
LEASE_AND_FENCE=REQUIRED
STALE_WRITER_REJECTION=REQUIRED
IDEMPOTENT_PUBLICATION=REQUIRED
DETERMINISTIC_STORAGE_IDENTITY=REQUIRED
PROCESS_MEMORY_SSOT=FORBIDDEN
NODE_LOCAL_SEMANTIC_LOCATOR=FORBIDDEN
MULTI_NODE_IMPLEMENTATION_NOW=NO
MULTI_NODE_REWRITE_LATER=NO
```

1 node использует тот же logical work/publication model, что и N nodes. Масштабирование меняет число workers и при необходимости control backend implementation, но не domain semantics, object/read-set identity или bulk representation.

## 22. OLAP decision

```text
INTERACTIVE_OLAP_DECISION=DEFER_BLOCKED_ON_REPRESENTATIVE_WORKLOAD_AND_SLO_MEASUREMENT
CLICKHOUSE_PRODUCT_STATUS=REFERENCE_CANDIDATE_ONLY
CLICKHOUSE_ROLE_IF_ADOPTED=REBUILDABLE_ANALYTICAL_PROJECTION
```

Standing OLAP оправдан только если owner-defined concurrent/interactive SLO не выполняется object/Parquet + embedded execution + simpler layout/materialization optimizations.

## 23. Cache/broker/search/vector disposition

| Mechanism | Consolidated disposition | Expansion trigger |
| --- | --- | --- |
| Redis/shared cache | `DEFER` | measured hot-read latency/cost and valid invalidation model |
| Kafka/broker | `DEFER` | durable fanout + independent offsets/replay + decoupled consumer fleets |
| full-text service | `DEFER` | bounded relational/batch search fails real corpus/query SLO |
| vector DB | `DEFER` | explicit vector corpus/recall/latency workload and model lineage |

Все такие системы по умолчанию являются non-semantic projection/transport mechanisms.

## 24. Failure/HA/DR

Candidate обязан определять поведение при worker crash, control crash, reboot, object upload interruption, duplicate/retry, stale fence, catalog/manifest loss, projection loss, compaction interruption, corrupt object, credential rotation and clean restore.

```text
HA_SEAMS_REQUIRED_NOW=YES
EXACT_HA_TOPOLOGY=BLOCKED_ON_OWNER_RPO_RTO_AND_DEPLOYMENT_EVIDENCE
REPLICATION_IS_BACKUP=NO
```

Worker/projection loss не должен менять accepted semantic result; control/object authority loss требует restore + reconciliation before resuming canonical publication.

## 25. Backup/restore

Минимум два recovery domains:

1. control-state database;
2. immutable bulk object/manifest domain.

Rebuildable search/cache/OLAP projections являются отдельными restore/rebuild domains, но не authority by default.

```text
BACKUP_RESTORE_DECISION=CLEAN_ENVIRONMENT_RESTORE_RECONCILIATION_AND_INDEPENDENT_READBACK_REQUIRED
BACKUP_EXISTS_EQUALS_RESTORE_PROVEN=NO
REPLICATION_EQUALS_BACKUP=NO
```

F5 qualification должна доказать bounded restore; F5M должна повторно доказать restore/read parity после migration/cutover.

## 26. Operational-complexity comparison

| Profile | Standing services | Added credential/backup domains | Current risk closed | Consolidated disposition |
| --- | ---: | --- | --- | --- |
| SQLite + local FS + direct Python | 0 | host only | control durability, но не node-independent bulk | reject as complete P2 foundation |
| SQLite/WAL + shared object/blob + Parquet + manifests | storage API/service class; DB embedded | object + control backup | current F5 physical lifecycle with minimum surface | **CURRENT_DEFAULT_F5_PROFILE** |
| previous + embedded DuckDB workers | no new standing analytical service | no new authority backup | analytical/backtest scans | **PREFERRED_ANALYTICAL_PROFILE**, not F5 hard dependency |
| PostgreSQL + object/blob + Parquet + manifests | DB + storage | DB + object | shared multi-node control | **REQUIRED_EXPANSION_PROFILE** on trigger |
| PostgreSQL + object + Iceberg + ClickHouse + broker/cache/search/vector | many | many | hypothetical future risks | defer/reject initially |

Three-question result: consolidated required-now mechanisms each close a present correctness or portability risk; every deferred service has a simpler current alternative and an explicit expansion trigger.

## 27. Benchmark/qualification requirements

Representative disposable qualification должна измерять: batch encode/seal, upload/finalize, checksum/readback, conditional publication conflict, manifest planning/discovery, identity lookup, 1d/30d/365d scans, selected-column scans, joins/aggregations, object count, compaction amplification, control backup/restore, object inventory restore, 1→N→1 worker execution, duplicate delivery and stale-fence rejection.

Metrics: p50/p95 where applicable, rows/s, MiB/s, bytes read, CPU, max RSS, temp disk, object requests, files opened, planning time, restore throughput/time, retries, correctness hashes and operator recovery actions.

Until owner SLO exists, benchmark compares mechanisms but не изобретает arbitrary PASS thresholds.

## 28. Minimum consolidated architecture candidate

```text
CONSOLIDATED_MINIMUM_INITIAL_STACK=
SQLite/WAL single-node durable control substrate
+ shared durable object/blob capability
+ immutable Parquet for bulk tabular data
+ native immutable blobs where source fidelity requires
+ bounded immutable versioned manifests
+ transactional current-generation registration in control state

ANALYTICAL_EXTENSION=
embedded DuckDB per worker as preferred candidate when analytical/backtest acceptance begins

FUTURE_SHARED_CONTROL_EXTENSION=
PostgreSQL before shared multi-node transactional control qualification
```

Это минимальный стек, который закрывает current F5 correctness/portability risks и сохраняет upgrade seams без semantic rewrite.

## 29. Expansion triggers

| Expansion | Trigger | Before expansion evidence |
| --- | --- | --- |
| SQLite → PostgreSQL | shared cross-node claims/fences/current-pointer writes; measured contention; HA requirement | lifecycle/concurrency qualification + owner RPO/RTO where relevant |
| bounded manifests → open table format/Iceberg candidate | table-level concurrent writers; general snapshot mutation; frequent schema/partition evolution; manifest scale; multi-engine transactional requirement | representative metadata workload + explicit feature contract |
| direct Python/Arrow → DuckDB default | analytical/backtest scan/join workload exceeds simpler direct path | representative benchmark |
| embedded execution → ClickHouse | explicit interactive/concurrent SLO missed after simpler optimizations | real query mix benchmark |
| no shared cache → Redis candidate | measured hot-read bottleneck and valid invalidation model | hit-rate/latency/cost evidence |
| work table → broker | durable fanout/offset/replay/decoupled-fleet contract | producer/consumer failure semantics |
| no dedicated search → search/vector service | explicit corpus/query/recall/latency requirements | representative search benchmark |
| object product selection | F5 owner implementation contour | capability conformance + cost/compliance + restore proof |

## 30. F5/P2 implications

F5 owner contract/implementation later needs explicit physical fields for: backend capability/namespace, opaque storage ref, object identity/checksum/size, format/compression/encryption class, dataset/partition/layout/schema generation, manifest parent/current generation, writer/work/attempt/fence/idempotency identity, source revision/sequence, effective/known time, replay cutoff, durable-write/readback/registration/ACK evidence and backup/restore/qualification references.

```text
F5_SCOPE=NEW_INCOMING_HIGH_CARDINALITY_PHYSICAL_LIFECYCLE_QUALIFICATION
F5_MASS_BACKFILL=FORBIDDEN_AS_FIRST_ROUTE_TEST
F5_IMPLEMENTATION_ALLOWED_BY_THIS_TASK=NO
```

## 31. F5M boundary

```text
F5M_SCOPE=EXISTING_CORPUS_MIGRATION_AND_PHYSICAL_STORAGE_CUTOVER
F5M_DEPENDS_ON=QUALIFIED_F5_NEW_PHYSICAL_ROUTE
DELETE_LEGACY_BEFORE_PROOF=FORBIDDEN
CUTOVER_BEFORE_COMPLETENESS_AND_READ_PARITY=FORBIDDEN
F5M_IMPLEMENTATION_ALLOWED_BY_THIS_TASK=NO
```

Migration preserves domain provenance, exact accepted revisions/generations, independent readback, completeness reconciliation, semantic read parity and rollbackability.

## 32. Governance disposition

Fresh registry/staging authority resolves owner routes as follows:

| Owner artifact class | Consolidated disposition | Reason |
| --- | --- | --- |
| ADR | `AMEND_REQUIRED` | existing proposed `ADR-DATA-FOUNDATION-001` already owns this Server/Data Foundation architecture boundary; update it instead of creating a duplicate |
| Standards | `AMEND_REQUIRED` | existing DATA management/schema/migration/validation/retention/backup standards are the repeatable normative owners |
| Artifact/Server Contracts | `AMEND_REQUIRED` | existing storage/publication/access/work/execution contracts need additive physical identity, manifest, PIT, readback, restore and multi-writer bindings |
| Program Map | `AMEND_REQUIRED` | materialize F5R gate result, F5/F5M sequencing and expansion/qualification gates after owner architecture publication |

```text
NEW_BROAD_STANDARD_REQUIRED=NO
OWNER_ARCHITECTURE_PUBLICATION_EXECUTED_BY_THIS_TASK=NO
```

## 33. Consolidated findings

### CFIND-001

- **Status:** CONVERGED
- **Claim:** F5R подтверждает, что F5 закрывает physical lifecycle, а не переносит ETH/domain semantics в storage plane.
- **Research-1-Support:** Явно фиксирует semantic/physical split и F5R gate.
- **Research-2-Support:** Явно фиксирует F4→F5 physical lifecycle gap.
- **Authority:** Pinned AGENTS/F4/Program Map.
- **Evidence-Class:** REPOSITORY_DERIVED+CONSOLIDATION
- **Divergence-If-Any:** Нет.
- **Resolution:** Сохранить Data Bridge/domain semantic authority и реализовывать generic Server capabilities.
- **Simpler-Alternative:** Не создавать второй semantic route.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Existing boundary уже закрывает риск authority split.
- **Impact-On-Agent-Actions:** Исключает повторное domain research.
- **Impact-On-Engineer-Actions:** Сужает F5 до physical lifecycle.
- **Architecture-Consequence:** Second AIFE data route запрещён.
- **Governance-Consequence:** Physical fields/lifecycle only.
- **F5-Consequence:** Qualify only the new incoming generic physical lifecycle; do not redefine Data Bridge/domain semantics.
- **F5M-Consequence:** Migrate/cut over the existing corpus without changing domain semantics or creating a second semantic route.
- **Expansion-Trigger:** Нет.

### CFIND-002

- **Status:** CONVERGED
- **Claim:** Shared durable object/blob capability required now for high-cardinality bulk authority.
- **Research-1-Support:** Object/blob + Parquet minimum stack.
- **Research-2-Support:** Shared durable object/blob capability REQUIRED_NOW.
- **Authority:** Server storage/publication contracts + horizontal design.
- **Evidence-Class:** REPOSITORY_DERIVED+SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Требовать capability class; product остаётся unselected.
- **Simpler-Alternative:** Node-local filesystem.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Node-local path fails node-loss/shared-reader seam.
- **Impact-On-Agent-Actions:** Один backend qualification contour.
- **Impact-On-Engineer-Actions:** Не требуется будущая bulk-format migration ради N nodes.
- **Architecture-Consequence:** Vendor-neutral ADR amendment.
- **Governance-Consequence:** Qualify chosen backend capability.
- **F5-Consequence:** Select and qualify the actual object/blob backend for the new incoming route, including capability/cost/compliance/restore proof.
- **F5M-Consequence:** Backfill/migrate the existing corpus only after the F5 route/backend is qualified.
- **Expansion-Trigger:** F5 owner implementation contour with capability/TCO/compliance/restore evidence.

### CFIND-003

- **Status:** CONVERGED
- **Claim:** Parquet required now for bulk tabular classes; native immutable blobs remain allowed for fidelity-sensitive evidence.
- **Research-1-Support:** Parquet required; object/blob for large immutable/raw artifacts.
- **Research-2-Support:** Parquet default tabular; native blob retained where tabularization loses evidence.
- **Authority:** Workload shape + both research sources.
- **Evidence-Class:** SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Parquet for tabular, blob for non-tabular/raw fidelity.
- **Simpler-Alternative:** Single universal row/database representation.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Mixed representation is simpler and avoids semantic loss.
- **Impact-On-Agent-Actions:** Defines bounded schema/layout work.
- **Impact-On-Engineer-Actions:** Avoids import into standing warehouse.
- **Architecture-Consequence:** Schema/data standards amend, not new vendor standard.
- **Governance-Consequence:** Layout/version/readback proof.
- **F5-Consequence:** Qualify exact Parquet partition/file/row-group/compression/layout policy for new incoming data; keep native immutable blobs where source fidelity requires.
- **F5M-Consequence:** Preserve source evidence/domain provenance while migrating the historical corpus into the qualified layout.
- **Expansion-Trigger:** Exact layout measurement.

### CFIND-004

- **Status:** RESOLVED_DIVERGENCE
- **Claim:** Versioned manifests plus minimal transactional registration are required now; general custom catalog and Iceberg are deferred.
- **Research-1-Support:** Profile A manifests; transactional catalog and Iceberg not proven now.
- **Research-2-Support:** Manifest + transactional current pointer; general catalog defer; Iceberg on trigger.
- **Authority:** F4 atomic publication/registration/ACK semantics.
- **Evidence-Class:** SOURCE_CONVERGENCE+RESOLUTION
- **Divergence-If-Any:** Scope of transactional metadata.
- **Resolution:** Use immutable manifest as exact read-set and control-state transaction as atomic current-generation registration.
- **Simpler-Alternative:** Directory listing only.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Listing cannot prove coherent generation; full table format is unnecessary now.
- **Impact-On-Agent-Actions:** Bounds metadata work.
- **Impact-On-Engineer-Actions:** Avoids catalog service/upgrade burden.
- **Architecture-Consequence:** Contracts need manifest/current-pointer semantics.
- **Governance-Consequence:** Required in F5.
- **F5-Consequence:** Qualify immutable manifests plus transactional current-generation registration for incoming write/seal/readback/publication.
- **F5M-Consequence:** Retain generation mapping and exact accepted generations during corpus migration/cutover.
- **Expansion-Trigger:** Table-format complexity trigger.

### CFIND-005

- **Status:** RESOLVED_DIVERGENCE
- **Claim:** Durable transactional control semantics are required now, but PostgreSQL deployment is not.
- **Research-1-Support:** PostgreSQL required now.
- **Research-2-Support:** SQLite/WAL now, PostgreSQL later.
- **Authority:** Program Map allows one server and forbids requiring multi-node implementation now.
- **Evidence-Class:** REPOSITORY_DERIVED+RESOLUTION
- **Divergence-If-Any:** Backend timing.
- **Resolution:** SQLite/WAL current default; backend-neutral work/publication semantics; PostgreSQL before shared multi-node control.
- **Simpler-Alternative:** Deploy PostgreSQL immediately.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Immediate deployment adds service/backup/HA work without mandatory risk reduction.
- **Impact-On-Agent-Actions:** Next agent implements/qualifies one bounded initial substrate.
- **Impact-On-Engineer-Actions:** Lower initial operations; clear migration trigger.
- **Architecture-Consequence:** ADR records capability/profile/expansion split.
- **Governance-Consequence:** SQLite may close single-node F5 qualification.
- **F5-Consequence:** Qualify SQLite/WAL single-node durable control semantics for the incoming route, including work/attempt/claim/lease/fence/idempotent publication/current-generation state.
- **F5M-Consequence:** No control-backend expansion is required solely for corpus migration/cutover; F5M follows the qualified control/publication contract.
- **Expansion-Trigger:** Shared multi-node control or contention/HA trigger.

### CFIND-006

- **Status:** PARTIALLY_CONVERGED
- **Claim:** Bounded repository corpus facts exist, while AIFE-wide capacity/performance baseline remains insufficient.
- **Research-1-Support:** Declares measured baseline insufficient for capacity-driven promotions.
- **Research-2-Support:** Provides bounded corpus counts but keeps growth/concurrency/restore metrics UNKNOWN.
- **Authority:** Pinned manifests + absence of AIFE-wide SLO/growth evidence.
- **Evidence-Class:** REPOSITORY_DERIVED+UNRESOLVED_MEASUREMENT
- **Divergence-If-Any:** Apparent wording difference only.
- **Resolution:** Record both baseline levels separately.
- **Simpler-Alternative:** Infer future scale from current bounded corpus.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Would fabricate growth/SLO evidence.
- **Impact-On-Agent-Actions:** Next agent benchmarks only decisions whose trigger needs it.
- **Impact-On-Engineer-Actions:** Avoids premature distributed services.
- **Architecture-Consequence:** Program Map owner gate should name qualification measurement.
- **Governance-Consequence:** F5 can qualify correctness with bounded data.
- **F5-Consequence:** Use bounded representative data to qualify incoming-route correctness; do not treat the bounded corpus as AIFE-wide capacity proof.
- **F5M-Consequence:** Mass-migration sizing/backfill/cutover capacity remains measurement-bound to representative benchmark and owner SLO.
- **Expansion-Trigger:** Representative benchmark and owner SLO.

### CFIND-007

- **Status:** CONVERGED
- **Claim:** PIT correctness requires effective_at, known_at, source revision/sequence evidence and exact generation/read-set plus method/model/strategy versions.
- **Research-1-Support:** Explicit PIT contract and provider revision/gap evidence.
- **Research-2-Support:** Explicit information-horizon/read-set model and provider replacement evidence.
- **Authority:** Both research streams and Data Bridge semantic authority.
- **Evidence-Class:** SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Make PIT a cross-layer semantic binding independent of storage-native snapshots.
- **Simpler-Alternative:** Rely on storage time travel alone.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Storage snapshot cannot encode historical knowability or model/method versions.
- **Impact-On-Agent-Actions:** Prevents additional PIT research.
- **Impact-On-Engineer-Actions:** Provides deterministic replay identity.
- **Architecture-Consequence:** Standards/contracts require temporal/revision fields.
- **Governance-Consequence:** F5 fields/read-set semantics.
- **F5-Consequence:** Bind PIT/read-set fields for the new incoming route: effective_at, known_at, source revision/sequence/gap, exact generation/read-set, method/model/strategy version and replay cutoff.
- **F5M-Consequence:** Preserve prior accepted revisions/generations and PIT provenance during corpus migration/cutover.
- **Expansion-Trigger:** Нет; exact field schema owner contract step.

### CFIND-008

- **Status:** CONVERGED
- **Claim:** Stateful backtests must not be arbitrarily time-sharded; horizontalism uses independent work axes or proven checkpoints/state transfer.
- **Research-1-Support:** Time sharding forbidden absent checkpoint/replay proof.
- **Research-2-Support:** Same rule with explicit checkpoint/state-transfer options.
- **Authority:** Work/execution determinism and state dependence.
- **Evidence-Class:** SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Parallelize strategy/model/parameter/scenario/run axes first.
- **Simpler-Alternative:** Distributed temporal DAG.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Independent axes close scale need with much less correctness machinery.
- **Impact-On-Agent-Actions:** Simplifies scheduler requirements.
- **Impact-On-Engineer-Actions:** Avoids state-boundary bugs.
- **Architecture-Consequence:** Execution contract amendment later.
- **Governance-Consequence:** No hard F5 storage dependency.
- **F5-Consequence:** No hard F5 physical-storage dependency; F5 must preserve deterministic read-set/execution seams without authorizing stateful time sharding.
- **F5M-Consequence:** No direct corpus-migration/cutover dependency.
- **Expansion-Trigger:** Checkpointable/replayable state boundary.

### CFIND-009

- **Status:** RESOLVED_DIVERGENCE
- **Claim:** Embedded DuckDB is preferred analytical/backtest candidate, not F5 physical-storage closure dependency.
- **Research-1-Support:** DuckDB per worker required now.
- **Research-2-Support:** DuckDB good fit/later; direct Python/Arrow allowed.
- **Authority:** F5/F5M program boundaries and no measured interactive SLO.
- **Evidence-Class:** SOURCE_CONVERGENCE+RESOLUTION
- **Divergence-If-Any:** Timing only.
- **Resolution:** Define analytical execution seam now; require representative consumer acceptance later; use DuckDB unless simpler direct path proves sufficient.
- **Simpler-Alternative:** Install standing OLAP or force DuckDB during storage qualification.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Storage lifecycle can be proven without analytical engine deployment.
- **Impact-On-Agent-Actions:** Avoids unnecessary F5 work.
- **Impact-On-Engineer-Actions:** Keeps worker process stateless/retryable.
- **Architecture-Consequence:** ADR records preferred execution candidate and trigger.
- **Governance-Consequence:** Not hard dependency.
- **F5-Consequence:** DuckDB is not required for F5 physical-storage closure; F5 only preserves the analytical consumer seam.
- **F5M-Consequence:** No DuckDB-specific migration/cutover coupling; F5M follows storage completeness/read parity independently.
- **Expansion-Trigger:** Start analytical/backtest acceptance or direct-path benchmark failure.

### CFIND-010

- **Status:** CONVERGED
- **Claim:** ClickHouse/cache/broker/search/vector services are deferred until measured/contract triggers.
- **Research-1-Support:** All optional services deferred with explicit triggers.
- **Research-2-Support:** Same result and operational-burden reasoning.
- **Authority:** No pinned workload/SLO requiring them.
- **Evidence-Class:** SOURCE_CONVERGENCE+UNRESOLVED_MEASUREMENT
- **Divergence-If-Any:** Нет.
- **Resolution:** Use object/Parquet/control DB/process-local or rebuildable alternatives first.
- **Simpler-Alternative:** Deploy speculative standing services.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Adds credentials, backup, monitoring, failure and upgrade domains.
- **Impact-On-Agent-Actions:** Eliminates speculative integration tracks.
- **Impact-On-Engineer-Actions:** Reduces ops surface.
- **Architecture-Consequence:** Program Map/ADR should carry expansion triggers, not defaults.
- **Governance-Consequence:** No F5 dependency.
- **F5-Consequence:** No ClickHouse/cache/broker/search/vector dependency for F5 incoming physical-lifecycle qualification.
- **F5M-Consequence:** No such service is required for corpus migration/cutover; later projections remain rebuildable/deferred.
- **Expansion-Trigger:** Per-service explicit measured contract.

### CFIND-011

- **Status:** CONVERGED
- **Claim:** Backup, replication, HA and restore are distinct; recoverability requires clean-environment restore/reconciliation/readback.
- **Research-1-Support:** Backend-appropriate backups + clean restore proof; HA topology measurement-gated.
- **Research-2-Support:** Separate control/object recovery domains and clean restore sequence.
- **Authority:** AIFE backup/restore principles and storage/publication contracts.
- **Evidence-Class:** SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Qualify control DB and immutable object domain separately; rebuild projections.
- **Simpler-Alternative:** Treat replication or backup existence as recovery proof.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Does not test usable restored authority.
- **Impact-On-Agent-Actions:** Defines finite recovery qualification.
- **Impact-On-Engineer-Actions:** Reduces incident improvisation.
- **Architecture-Consequence:** STD-DATA-BACKUP/RETENTION + contracts amend.
- **Governance-Consequence:** F5 qualification includes restore/readback.
- **F5-Consequence:** F5 must prove bounded clean restore, reconciliation and independent readback for control and object authority domains.
- **F5M-Consequence:** Restore/read parity requalification.
- **Expansion-Trigger:** Owner RPO/RTO and deployment topology.

### CFIND-012

- **Status:** CONVERGED
- **Claim:** F5 qualifies the new incoming route before F5M migrates existing corpus.
- **Research-1-Support:** F5 physical route then F5M.
- **Research-2-Support:** Same explicit distinction.
- **Authority:** Pinned Program Map.
- **Evidence-Class:** REPOSITORY_DERIVED
- **Divergence-If-Any:** Нет.
- **Resolution:** Bounded representative F5 qualification first.
- **Simpler-Alternative:** Use mass backfill as first test.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Mass migration magnifies defects and complicates rollback.
- **Impact-On-Agent-Actions:** Keeps next task bounded.
- **Impact-On-Engineer-Actions:** Safer cutover path.
- **Architecture-Consequence:** Program Map amendment records research gate/triggers.
- **Governance-Consequence:** Incoming route qualification.
- **F5-Consequence:** Incoming route qualification.
- **F5M-Consequence:** Corpus inventory/backfill/parity/cutover.
- **Expansion-Trigger:** Owner architecture publication then F5 DEV_TZ in a later task.

### CFIND-013

- **Status:** RESOLVED_DIVERGENCE
- **Claim:** Existing proposed `ADR-DATA-FOUNDATION-001` is the owner for the consolidated architecture; a new competing ADR is not required.
- **Research-1-Support:** Suggested CREATE after consolidation.
- **Research-2-Support:** Suggested AMEND existing proposed ADR.
- **Authority:** Fresh WIP contains proposed ADR covering same Server/Data Foundation decision boundary.
- **Evidence-Class:** REPOSITORY_DERIVED+RESOLUTION
- **Divergence-If-Any:** Create vs amend.
- **Resolution:** `OWNER_ADR_DISPOSITION=AMEND_REQUIRED`.
- **Simpler-Alternative:** Create parallel ADR.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Duplicates authority and increases reconciliation cost.
- **Impact-On-Agent-Actions:** One owner governance target.
- **Impact-On-Engineer-Actions:** Less document drift.
- **Architecture-Consequence:** Amend existing ADR after owner review.
- **Governance-Consequence:** No direct implementation.
- **F5-Consequence:** No F5 implementation is authorized by this finding; F5 remains blocked until owner architecture publication and later DEV_TZ.
- **F5M-Consequence:** No migration action.
- **Expansion-Trigger:** Owner publication.

### CFIND-014

- **Status:** CONVERGED
- **Claim:** Existing DATA standards, Server contracts and Program Map need targeted amendment; no new broad parallel standard.
- **Research-1-Support:** Amend/bind existing standards/contracts/map.
- **Research-2-Support:** AMEND_REQUIRED for all three owner layers.
- **Authority:** Canonical registries + staged contracts/Program Map.
- **Evidence-Class:** REPOSITORY_DERIVED+SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Amend by owner role: repeatable rules in standards, binding fields in contracts, sequencing/gates in Program Map.
- **Simpler-Alternative:** Create new broad `STD-SERVER-*` family.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Existing owner families already cover the responsibilities.
- **Impact-On-Agent-Actions:** Clear next governance package.
- **Impact-On-Engineer-Actions:** Avoids duplicate standards.
- **Architecture-Consequence:** STD/CONTRACT/PROGRAM_MAP AMEND_REQUIRED.
- **Governance-Consequence:** Enables later DEV_TZ after publication.
- **F5-Consequence:** F5 remains blocked until owner amendments/publication enable the later DEV_TZ and bind the required physical-lifecycle contracts.
- **F5M-Consequence:** F5M remains gated behind a qualified F5 route; no migration/cutover is authorized here.
- **Expansion-Trigger:** Owner publication.

### CFIND-015

- **Status:** CONVERGED
- **Claim:** Product selection remains separate from architecture capability selection.
- **Research-1-Support:** Object/vendor unselected; optional product triggers.
- **Research-2-Support:** Capability class first; S3-compatible label not proof; vendor remains open.
- **Authority:** Existing ADR explicitly keeps database/object vendor unselected.
- **Evidence-Class:** REPOSITORY_DERIVED+SOURCE_CONVERGENCE
- **Divergence-If-Any:** Нет.
- **Resolution:** Record object backend `UNSELECTED`, PostgreSQL `PREFERRED_CANDIDATE` for expansion, Iceberg/ClickHouse `REFERENCE_CANDIDATE` on triggers.
- **Simpler-Alternative:** Bind vendors during research consolidation.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Would turn evidence convergence into procurement/deployment authority.
- **Impact-On-Agent-Actions:** Prevents vendor-specific implementation tasks now.
- **Impact-On-Engineer-Actions:** Allows independent TCO/capability qualification.
- **Architecture-Consequence:** Owner ADR may bind later.
- **Governance-Consequence:** Actual F5 backend selected/qualified only in owner-authorized implementation contour.
- **F5-Consequence:** Actual backend selection/qualification later.
- **F5M-Consequence:** Migration follows qualified backend.
- **Expansion-Trigger:** Capability/TCO/compliance/restore evidence.

### CFIND-016

- **Status:** CONVERGED
- **Claim:** Owner task-local decision accepts the two isolated same-model contexts as sufficient P1 research evidence without changing global dual-agent policy.
- **Research-1-Support:** Historical artifact required distinct-agent review before owner successor decision.
- **Research-2-Support:** Historical artifact recorded gate not formally closed.
- **Authority:** Current owner decision is explicit task-scoped authority.
- **Evidence-Class:** OWNER_TASK_INPUT+SUCCESSION
- **Divergence-If-Any:** Historical gate vs successor owner ruling.
- **Resolution:** Materialize succession only in consolidated artifact; do not rewrite source history.
- **Simpler-Alternative:** Edit old artifacts.
- **Why-Simpler-Is-Or-Is-Not-Sufficient:** Historical evidence must remain immutable.
- **Impact-On-Agent-Actions:** Consolidation can proceed now.
- **Impact-On-Engineer-Actions:** No source artifact rewrite.
- **Architecture-Consequence:** Global AIFE policy unchanged.
- **Governance-Consequence:** Owner architecture publication becomes allowed as next governance step only.
- **F5-Consequence:** No F5 permission is granted by the research admissibility ruling; owner architecture publication and later DEV_TZ are still required.
- **F5M-Consequence:** No F5M permission is granted; migration/cutover remains downstream of a qualified F5 route.
- **Expansion-Trigger:** None.

## 34. Owner decisions still required

Source divergence is fully resolved for the purpose of producing a local candidate, but owner governance and implementation qualification remain intentionally open:

- publish consolidated architecture into the existing proposed ADR and aligned owner artifacts;
- choose/qualify the actual object/blob product/deployment profile;
- bind numeric performance SLO, RPO and RTO;
- qualify exact Parquet partition/file/row-group/compression policy;
- decide whether direct Python/Arrow is sufficient for initial analytical acceptance or promote embedded DuckDB as the required execution implementation;
- keep Iceberg/ClickHouse/cache/broker/search/vector choices dormant until their documented triggers fire;
- materialize a later DEV_TZ only after owner architecture publication and owner-authorized execution planning.

These are not unresolved source-research divergences and do not block the next owner governance publication step.

## Итоговое решение (контракт)

### Runtime Disposition

- Runtime-Oriented: yes
- Effective Closure: no
- Downstream Disposition: `Blocked`
- Why findings-only is insufficient: consolidated research определяет local-candidate architecture, но canonical owner architecture artifacts ещё не опубликованы и execution authority отсутствует.
- Required next contour: owner review and publication of the consolidated F5R architecture in canonical governance artifacts.
- Materialization target: existing proposed `ADR-DATA-FOUNDATION-001` plus aligned DATA standards, Server/Data contracts and Program Map according to owner disposition.
- Blocker, if any: `OWNER_ARCHITECTURE_PUBLICATION_EXECUTED=NO`.

### Materialization Disposition

- Program Root: `aife-server-data-foundation`
- Wave / Topic: `F5R / data-backend-architecture`
- Program-Setup Disposition: `blocker`
- Execution Root: `AIFE/staging/docs/98-Reviews/execution/2026-08/aife-server-data-foundation/`
- Physical Use Class: `control-plane-evidence-only`
- Operational Surface Target: future F5 physical storage lifecycle after owner publication and DEV_TZ.
- Physical Integration Target: F5 P2 backend-neutral lifecycle, product binding deferred to owner-authorized implementation qualification.
- Current Status: `consolidation-complete-owner-publication-pending`
- Readiness Threshold Met: `no` for DEV_TZ/F5 execution; `yes` for owner architecture publication review.
- DEV_TZ Outcome: `blocked`
- Delivery Claim Allowed: `no`
- Required Next Prompt: owner governance publication task based on this consolidated artifact.
- Required Next Artifact: owner-amended ADR plus aligned owner-governance artifacts as authorized by the next task.
- Blocker: owner architecture publication has not executed.
- Why findings-only is forbidden here: runtime architecture needs canonical owner decision artifacts before implementation planning.
- Why control-plane-only is not delivery: no runtime/storage implementation, migration, deployment or production route changed.

### 1. Статус темы

- Исследование по теме: ЗАКРЫТО
- Состояние волны: ЧАСТИЧНО
- Переход к `DEV_TZ`: ЗАПРЕЩЁН
- Архитектурный статус: `local-candidate`
- `P1_DUAL_RESEARCH_EVIDENCE=ACCEPTED`
- `P1_RESEARCH_GATE=SATISFIED_BY_OWNER_DECISION`
- `THIRD_RESEARCH_REQUIRED=NO`
- `CONSOLIDATION=COMPLETE`
- `OWNER_ADMISSIBILITY_DECISION_MATERIALIZED=YES`
- `ARCHITECTURE_STATUS=local-candidate`
- `SOURCE_RESEARCH_1=AIFE/staging/docs/98-Reviews/research/2026-08/aife-server-data-foundation/RESEARCH_aife-server-data-foundation_general_data-backend-architecture_2026-08-27_chatgpt-gpt.md@d60aa5b16b9ee99838b0a88337ccc744b50ec99a`
- `SOURCE_RESEARCH_2=AIFE/staging/docs/98-Reviews/research/2026-08/aife-server-data-foundation/RESEARCH_aife-server-data-foundation_independent-second-run_data-backend-architecture_2026-08-27_chatgpt-gpt.md@63e5ffd6ce9493e0d01345d17c0e41cf263dc7ca`
- `CONSOLIDATED_ARCHITECTURE_CANDIDATE=SQLITE_WAL_CONTROL_INITIAL + SHARED_OBJECT_BLOB + PARQUET_NATIVE_BLOBS + VERSIONED_MANIFESTS_TRANSACTIONAL_POINTER; POSTGRESQL_SHARED_CONTROL_EXPANSION; DUCKDB_PREFERRED_ANALYTICAL_CANDIDATE`
- `UNRESOLVED_ARCHITECTURE_QUESTIONS=NO_UNRESOLVED_SOURCE_DIVERGENCE; PRODUCT_SLO_LAYOUT_AND_QUALIFICATION_DETAILS_REMAIN_MEASUREMENT_OR_OWNER_BOUND`
- `OWNER_ADR_DISPOSITION=AMEND_REQUIRED`
- `OWNER_STANDARD_DISPOSITION=AMEND_REQUIRED`
- `OWNER_ARTIFACT_CONTRACT_DISPOSITION=AMEND_REQUIRED`
- `PROGRAM_MAP_DISPOSITION=AMEND_REQUIRED`
- `OWNER_ARCHITECTURE_PUBLICATION_ALLOWED=YES_AS_NEXT_OWNER_GOVERNANCE_STEP`
- `OWNER_ARCHITECTURE_PUBLICATION_EXECUTED=NO`
- `DEV_TZ_ALLOWED=NO`
- `F5_ALLOWED=NO`
- `F5M_ALLOWED=NO`

### 2. Граница контекстного пакета

- `Minimum-Packet`: two immutable source Research artifacts + task-scoped owner admissibility decision + pinned shared research base + verified AIFE governance + relevant staged ADR/Program Map authority.
- `Expansion-Trigger`: owner begins canonical architecture publication or a measurement-gated mechanism reaches its explicit expansion trigger.
- `Expansion-Authority`: Architecture Lead / owner governance route.

### 3. Граница полномочий

- Переписывание маршрута владельца (`owner-route`): ЗАПРЕЩЕНО
- Собственная иерархия истины (`truth hierarchy`): ЗАПРЕЩЕНО
- Подмена опорного репозиторного доказательства (`repo-proof core`): ЗАПРЕЩЕНА
- `TASK_SCOPED_OWNER_DECISION=YES`
- `GLOBAL_POLICY_CHANGE=NO`

### 4. Масштабируемость решения

- `Scaling-Class`: УСЛОВНО ПЕРЕНОСИМО
- Ограничение локального удобства: initial SQLite/WAL profile допустим только потому, что semantic/control contracts остаются backend-neutral; до shared multi-node control обязателен PostgreSQL-or-equivalent owner-qualified expansion, при этом текущий evidence делает PostgreSQL preferred candidate.

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
- Блокеры решения: owner architecture publication не выполнена; actual backend product и numeric qualification values остаются owner/measurement-bound.
- Ограничение перехода к `DEV_TZ`: текущий topic/scope execution blocked до owner architecture publication.
- Согласованные части: semantic/physical boundary; object/blob + Parquet/native evidence; manifests; PIT; backtest decomposition; 1→N→1; backup/restore; deferred optional services; F5/F5M boundary.
- Расхождения: control implementation timing, DuckDB timing, bounded-vs-AIFE-wide baseline wording, minimal transactional pointer boundary и ADR create-vs-amend; все сведены в разделах 8, 11, 16, 17, 20 и 32.
- Общие слепые зоны консолидации: AIFE-wide growth/concurrency/restore measurements, exact object product/TCO, numeric SLO/RPO/RTO, exact file/partition sizing; они снижают certainty implementation profile, но не блокируют owner architecture publication.
- Влияние расхождений на следующий шаг: не блокируют
- Готовность к DEV_TZ: no
- Готовые к реализации части: N/A; implementation запрещена текущим Task-ID.
- Заблокированные части: DEV_TZ, F5, F5M, runtime/storage implementation, migration, deployment.
- Запрет на открытие нового sibling research вместо materialization: yes
- Риск зависнуть на research-only уровне: low
- Обещанные DEV_TZ из PROGRAM_MAP_*: текущий F5R artifact не материализует новый DEV_TZ; F5 execution planning остаётся downstream owner-governed contour.
- Материализованы: N/A
- Авторизованы, но ещё не записаны: N/A в рамках этого Task-ID.
- Легитимно заблокированы: F5/F5M execution artifacts до owner architecture publication.
- Где сломалась downstream chain: не сломалась; она намеренно остановлена на owner architecture publication gate.
- Следующий обязательный операторский ход: owner review and canonical governance publication of this consolidated F5R architecture.

### 7. Обязательный следующий шаг

B) Публикация у владельца:

- Owner должен рассмотреть consolidated local-candidate и материализовать принятое решение в существующем `ADR-DATA-FOUNDATION-001` и связанных canonical governance artifacts.
- `NEXT_EXACT_STEP=OWNER_REVIEW_AND_PUBLICATION_OF_CONSOLIDATED_F5R_ARCHITECTURE_IN_CANONICAL_GOVERNANCE_ARTIFACTS`

### 8. Явные запреты

- `THIRD_INDEPENDENT_RESEARCH`
- `SELF_APPROVAL_AS_OWNER_ARCHITECTURE`
- `ADR_MUTATION_BY_THIS_TASK`
- `STANDARD_MUTATION_BY_THIS_TASK`
- `ARTIFACT_CONTRACT_MUTATION_BY_THIS_TASK`
- `PROGRAM_MAP_MUTATION_BY_THIS_TASK`
- `DEV_TZ`
- `F5`
- `F5M`
- `AEB`
- `PRODUCTION_DEPLOYMENT`
