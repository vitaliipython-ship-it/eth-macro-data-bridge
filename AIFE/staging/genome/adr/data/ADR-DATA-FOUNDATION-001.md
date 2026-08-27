---
id: ADR-DATA-FOUNDATION-001
title: "ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root"
version: '1.1'
status: active
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2027-02-23
category: architecture
doc_type: adr
language: ru
tags: [server, data, foundation, appcontext, storage, scalability, f5r]
related:
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-SCHEMA-001.md
  - genome/standards/data/STD-DATA-BACKUP-001.md
  - genome/standards/data/STD-DATA-RETENTION-001.md
  - genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
---

# ADR-DATA-FOUNDATION-001: Граница AIFE Server/Data Foundation и масштабируемый server-root

## Статус

**Active.** Владелец публикует уже завершённую F5R architecture consolidation как
каноническое архитектурное решение. Это решение не является разрешением на F5/F5M
implementation или production activation.

Owner evidence:

- `RESEARCH_CONSOLIDATED_aife-server-data-foundation_data-backend-architecture_2026-08-27.md`;
- owner admissibility decision `F5R-P1-SAME-MODEL-INDEPENDENT-RESEARCH-ADMISSIBILITY-2026-08-27`;
- `P1_RESEARCH_GATE=SATISFIED_BY_OWNER_DECISION`;
- `THIRD_RESEARCH_REQUIRED=NO`.

## Контекст и граница полномочий

AIFE предоставляет generic execution, scheduling, durable control state, publication,
storage lifecycle и access mechanisms. Domain owner сохраняет domain identities,
provider/source semantics, normalization, finality, revision/gap rules и semantic
resolution. Физическое хранилище, server execution plane и generated catalogs не становятся
semantic authority.

```text
DOMAIN_OWNS_SEMANTICS=YES
PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
SERVER_EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=NO
SECOND_AIFE_DATA_ROUTE=NO
APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
```

## Топология

```text
ONE_CANONICAL_AIFE_SERVER_ROOT=YES
ONE_MONOLITH=NO
ONE_CONTAINER=NO
ONE_DATABASE=NO
HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
INITIAL_ONE_SERVER=ALLOWED
MULTI_NODE_IMPLEMENTATION_NOW=NO
```

Начальный deployment profile может быть одним сервером. Семантика work/publication/access
не должна зависеть от node identity и обязана сохранять модель `1 → N → 1` без смены
контрактов.

## Durable control state

Нормативно требуется capability, а не vendor:

```text
REQUIRED_CAPABILITY=DURABLE_TRANSACTIONAL_BACKEND_NEUTRAL_CONTROL_STATE
INITIAL_PROFILE=SQLITE_WAL_SINGLE_INITIAL_SERVER
EXPANSION_PROFILE=POSTGRESQL_PREFERRED_CANDIDATE_AND_REQUIRED_BEFORE_SHARED_MULTI_NODE_CONTROL_QUALIFICATION
POSTGRESQL_IS_SEMANTIC_CONTRACT=NO
```

SQLite/WAL допустим для bounded single-node F5 qualification. Переход к shared multi-node
control обязан произойти до соответствующей multi-node qualification; конкретная PostgreSQL
топология, HA и эксплуатационные параметры остаются отдельной implementation/qualification
задачей.

## Bulk physical data

```text
BULK_STORAGE_CAPABILITY=SHARED_DURABLE_IMMUTABLE_OBJECT_OR_BLOB
OBJECT_STORAGE_PRODUCT=UNSELECTED
TABULAR_FORMAT=PARQUET_REQUIRED_FOR_BULK_TABULAR
RAW_NATIVE_BLOBS=ALLOWED_WHEN_SOURCE_FIDELITY_REQUIRES
```

Object/blob backend выбирается позже по capability, TCO, compliance, failure-domain и
restore evidence. Точный partitioning, file size, row-group size и compression параметры
measurement-bound и этим ADR не фиксируются.

## Generation и publication

```text
IMMUTABLE_BOUNDED_VERSIONED_MANIFESTS=REQUIRED
TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION=REQUIRED
ACK_BEFORE_DURABLE_WRITE_READBACK_REGISTRATION=FORBIDDEN
DIRECTORY_LISTING_IS_COHERENT_GENERATION_PROOF=NO
```

Manifest связывает exact accepted read-set/generation. Current generation меняется только
транзакционно после durable write, seal/integrity evidence и independent readback. Полный
custom catalog service не требуется.

## Analytical profile

```text
ANALYTICAL_EXECUTION=EMBEDDED_PER_WORKER_PREFERRED
DUCKDB=PREFERRED_CANDIDATE_NOT_F5_PHYSICAL_STORAGE_CLOSURE_DEPENDENCY
DIRECT_PYTHON_ARROW_SMALL_TRANSFORMS=ALLOWED
CLICKHOUSE=DEFER_MEASUREMENT_GATED_REBUILDABLE_PROJECTION
```

DuckDB может быть выбран на analytical/backtest acceptance, если direct Python/Arrow path
недостаточен. Standing OLAP service не является F5 dependency; rebuildable projection не
получает semantic authority.

## Open table format и optional services

```text
ICEBERG=DEFER_REFERENCE_CANDIDATE_ON_EXPLICIT_TRIGGER
CUSTOM_GENERAL_TABLE_CATALOG=DEFER
REDIS=DEFER
KAFKA_OR_BROKER=DEFER
FULL_TEXT_SEARCH=DEFER
VECTOR_DB=DEFER
```

Expansion triggers:

- Iceberg/open-table layer — когда manifest-only lifecycle уже не покрывает доказанную
  multi-writer/table-evolution/partition-evolution complexity;
- ClickHouse — когда representative interactive OLAP benchmark не выполняет owner SLO;
- Redis — когда measured shared-cache/coordination contract нельзя закрыть process-local или
  durable-control mechanisms;
- broker — когда доказана необходимость decoupled durable event delivery, которую текущая
  work/publication model не закрывает проще;
- full-text/vector service — только при появлении отдельного consumer contract и измеренного
  workload.

## Point-in-time и replay binding

PIT correctness не выводится из storage snapshot alone. Для применимых data/read/backtest
операций обязательна связка:

```text
PIT_BINDING=
EFFECTIVE_AT
+ KNOWN_AT
+ PROVIDER_OR_SOURCE_REVISION
+ SOURCE_SEQUENCE_CHANGE_OR_UPDATE_IDENTITY
+ GAP_OR_RESYNC_EVIDENCE
+ EXACT_GENERATION_OR_READ_SET
+ SCHEMA_OR_LAYOUT_VERSION
+ REPLAY_CUTOFF
+ METHOD_MODEL_OR_STRATEGY_VERSION
```

Domain owner определяет domain meaning revision/finality/gap evidence; generic SERVER
сохраняет и транспортирует binding без reinterpretation.

## Backtesting и horizontal execution

Независимые run/parameter/scenario axes могут распределяться горизонтально. Stateful time
sharding запрещён, пока не доказано состояние на границе shard:

```text
STATEFUL_TIME_SHARDING=FORBIDDEN_WITHOUT_CHECKPOINT_STATE_TRANSFER_OR_DETERMINISTIC_REPLAY_PROOF
NODE_ID_IS_SEMANTIC_IDENTITY=NO
```

Existing `CONTRACT-SERVER-WORK-001` и `CONTRACT-SERVER-EXECUTION-001` уже владеют stable
work/attempt/claim/lease/fence/idempotency semantics; этот ADR не дублирует их правила.

## Backup, restore и recoverability

```text
BACKUP_EXISTS_EQUALS_RESTORE_PROVEN=NO
REPLICATION_EQUALS_BACKUP=NO
CLEAN_ENVIRONMENT_RESTORE_RECONCILIATION_READBACK=REQUIRED
```

Durable control state и immutable object/blob authority являются отдельными recovery domains.
F5 qualification обязана доказать bounded clean-environment restore, reconciliation и
independent readback. Numeric RPO/RTO и exact HA topology остаются owner implementation /
qualification bound.

## F5 и F5M

```text
F5=NEW_INCOMING_PHYSICAL_LIFECYCLE_QUALIFICATION
F5M=EXISTING_CORPUS_MIGRATION_BACKFILL_PARITY_CUTOVER
F5M_REQUIRES_QUALIFIED_F5_ROUTE=YES
F5_MASS_BACKFILL_AS_FIRST_ROUTE_TEST=FORBIDDEN
```

Сначала на bounded representative data квалифицируется новый incoming physical lifecycle.
Только затем F5M инвентаризирует и переносит existing corpus, доказывает completeness,
independent readback, semantic read parity, rollback readiness и выполняет owner-authorized
cutover. Legacy readability сохраняется до завершения proof gates.

## Открытые implementation-bound решения

Этим ADR намеренно **не выбираются**:

- exact object/blob product или cloud/provider;
- exact Parquet partition/file/row-group/compression parameters;
- numeric throughput/latency SLO;
- numeric RPO/RTO;
- exact HA topology.

Они имеют статус `MEASUREMENT_BOUND`, `OWNER_IMPLEMENTATION_BOUND` или
`QUALIFICATION_BOUND` и не могут быть выведены из текущего research как уже принятые.

## Последствия

- Server/Data Foundation получает один owner architecture route без competing ADR;
- capability selection отделена от product selection;
- F5 остаётся bounded qualification нового incoming route;
- F5M остаётся отдельной migration/cutover стадией;
- DATA standards и SERVER contracts уточняют reusable rules/bindings, но не становятся
  вторым architecture owner;
- generated registries/catalogs остаются projection owner artifacts, а не semantic truth.

## Граница реализации

```text
F5_RESEARCH_REQUIRED=NO
F5_OWNER_ARCHITECTURE_REQUIRED=NO_AFTER_THIS_OWNER_PUBLICATION
F5_DEV_TZ_CREATED=NO
F5_IMPLEMENTATION_ALLOWED=NO_PENDING_F5_DEV_TZ_AND_OWNER_EXECUTION_AUTHORITY
F5M_ALLOWED=NO
DATABASE_CREATION_AUTHORIZED=NO
MIGRATION_EXECUTION_AUTHORIZED=NO
PRODUCTION_ACTIVATION_AUTHORIZED=NO
```
