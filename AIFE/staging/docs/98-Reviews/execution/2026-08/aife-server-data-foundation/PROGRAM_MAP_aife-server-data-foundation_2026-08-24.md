---
id: AIFE-SERVER-DATA-PROGRAM-MAP-2026-08-24
title: "Карта программы: Серверная и информационная основа AIFE"
version: '0.10'
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-09-06
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
  - docs/98-Reviews/execution/2026-08/aife-server-data-foundation/OWNER_AUTHORIZATION_aife-server-data-foundation_f5_2026-08-30.md
---

# Карта программы: Серверная и информационная основа AIFE

## 1. Полномочная база и текущий frontier

```text
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_REFERENCE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_REFERENCE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852

F5_PUBLISHED_WIP_HEAD=e6d35af62297a8d7c1119eae05c68df455091ea8
F5_PUBLISHED_WIP_TREE=9ce4b6a3ae593d32b5f48dd58c30531a7578effc
F5_PUBLISHED_STAGING_TREE=6233617119e107e91982e25b193465493b0c8ce4
F5_QUALIFIED_FUTURE_AIFE_TREE=e617aaf2f45d6f253732f9b6019a88bf72ca74f7
F5_DOCKER_D01_D22=22/22_PASS
F5_TECHNICAL_QUALIFICATION=PASS
F5_REAL_AIFE_CANONICAL_INTEGRATION=NO

AIFE_DELIVERY_STATUS=F5_TECHNICALLY_QUALIFIED_WIP_SOURCE_PUBLISHED_REAL_AIFE_NOT_INTEGRATED
CURRENT_PROGRAM_FRONTIER=F5C_C1_PASS_C2_OWNER_AUTHORIZATION_PENDING
F5C_PLANNING=PASS
F5C_IMPLEMENTATION_PLAN=AIFE/staging/docs/98-Reviews/execution/2026-08/aife-server-data-foundation/F5C_IMPLEMENTATION_PLAN_aife-server-data-foundation_2026-09-06.md
READY_FOR_F5C_DIRECT_WIP_IMPLEMENTATION=YES
F5C_STARTED=YES
F5C_C1_STATUS=PASS
F5C_C1_IMPLEMENTATION_HEAD=6bf87fcde89b6e585daa555d182153b6edf1b489
F5C_C1_IMPLEMENTATION_TREE=c662ad1060cfed7b7a3364f56aab328ed5bf51f1
F5C_C1_IMPLEMENTATION_PATH_COUNT=5
F5C_C1_OWNER_AUTHORIZATION=CONSUMED_PASS
F5C_C2_STATUS=NEXT_NOT_AUTHORIZED
READY_FOR_F5C_C2_OWNER_AUTHORIZATION=YES
F5C_C2_STARTED=NO
C2_FIRST_DURABLE_ACCEPTANCE_PASS=NO
F5M_STARTED=NO
REAL_AIFE_MUTATION=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
```

F5 остаётся доказанной physical foundation. F5C planning заморожен; C1 выполнен в разрешённом
5-path subset. Следующая program boundary — отдельная owner authorization на C2. C1 PASS не
является физическим proof frozen durable-acceptance design.

## 2. Три основных архитектурных вопроса

```text
QUESTION_1=HOW_DATA_IS_ACQUIRED_AND_DURABLY_STORED
QUESTION_2=HOW_PROVEN_ETH_D8_D9_D6_MECHANISMS_ARE_REUSED_AS_REFERENCE_WITHOUT_BECOMING_AIFE_PLATFORM_PRIMITIVES
QUESTION_3=HOW_AIFE_CONSUMERS_CONNECT_TO_AIFE_SERVER_ROOT_THROUGH_EXISTING_AIFE_ARCHITECTURAL_BOUNDARIES_WITH_HORIZONTAL_SCALE_BY_DESIGN
```

Все последующие механизмы и этапы должны существовать только если помогают отвечать на эти
вопросы без создания параллельной authority hierarchy.

## 3. Базовые инварианты AIFE Server

```text
ONE_CANONICAL_AIFE_SERVER_ROOT=YES
ONE_MONOLITH=NO
ONE_PROCESS=NO
ONE_CONTAINER=NO
ONE_DATABASE=NO

AIFE_SERVER_IS_GENERIC_PLATFORM=YES
AIFE_SERVER_IS_ETH_SPECIFIC=NO
AIFE_SERVER_IS_INSTRUMENT_SPECIFIC=NO
ETH_IS_FIRST_QUALIFIED_DOMAIN_NOT_PLATFORM_IDENTITY=YES

HORIZONTAL_SCALING_BY_DESIGN=MANDATORY
INITIAL_ONE_SERVER=ALLOWED
MULTI_NODE_IMPLEMENTATION_NOW=NO
DESIGN_FOR_SCALE_NOT_EQUAL_IMPLEMENT_SCALE_NOW=YES

APP_CONTEXT_PUBLIC_RUNTIME_ROUTE_PRESERVED=YES
SECOND_PUBLIC_DI_ROUTE=NO
SECOND_AIFE_DATA_ROUTE=NO
DATABASE_VENDOR_SELECTED=NO
TRANSPORT_SELECTED=NO
```

Generic contracts не должны навсегда предполагать один process, worker, container, server,
database implementation или process-local memory как authority. Текущий SQLite/WAL профиль
является квалифицированной one-server реализацией, а не вечным platform constraint.

## 4. Ownership: generic runtime против domain/provider semantics

```text
AIFE_OWNS=
GENERIC_COLLECTION_ACQUISITION_RUNTIME
+GENERIC_EXECUTION
+GENERIC_SCHEDULING
+GENERIC_WORK_OWNERSHIP
+GENERIC_DURABLE_RUNTIME_STATE
+GENERIC_PUBLICATION_LIFECYCLE
+GENERIC_STORAGE_LIFECYCLE
+GENERIC_ACCESS_MECHANISMS
+GENERIC_SERVER_OPERATIONS
+EXPORT_REPLICATION_ORCHESTRATION

SERVER_OWNS_PROVIDER_SEMANTICS=NO
SERVER_OWNS_DOMAIN_SEMANTICS=NO

ETH_DATA_BRIDGE_OWNS=
MARKET_DATA_SEMANTICS
+PROVIDER_SEMANTICS
+DOMAIN_IDENTITIES
+NORMALIZATION
+VALIDATION
+FINALITY
+GAP_REVISION_RULES
+DOMAIN_RESOLUTION_RULES
+PROVIDER_SPECIFIC_PARSING
+INSTRUMENT_SEMANTICS

DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
AIFE_PHYSICAL_STORAGE_IS_SEMANTIC_AUTHORITY=NO
```

Domain/provider adapters могут физически исполняться внутри AIFE Server deployment. Это не
переносит их domain/provider semantics в generic Server Core.

Целевой forward runtime:

```text
Provider / Source
→ Generic AIFE Collection / Acquisition Runtime
→ Domain + Provider Adapter
→ first durable acceptance
→ Work / execution lifecycle
→ Publication
→ AIFE-managed physical storage
→ independent readback / registration / access
→ optional export / replication targets
```

## 5. Current engineering WIP carrier — owner decision

До exact working Server Git freeze отдельный промежуточный `aife-server` repository НЕ создаётся.

```text
ACTIVE_SERVER_ENGINEERING_REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
ACTIVE_SERVER_ENGINEERING_BRANCH=agent/aife/server-data-foundation-wip

CURRENT_BRANCH_COVERS_F5C_DEVELOPMENT=YES
CURRENT_BRANCH_COVERS_SERVER_RUNTIME_QUALIFICATION=YES
CURRENT_BRANCH_COVERS_F5M_MIGRATION_DEVELOPMENT=YES
CURRENT_BRANCH_COVERS_F6_F7_QUALIFICATION_DEVELOPMENT=YES
CURRENT_BRANCH_COVERS_PRE_FREEZE_SERVER_STABILIZATION=YES
CURRENT_BRANCH_COVERS_FINAL_PATCH_SOURCE_FREEZE=YES

SEPARATE_AIFE_SERVER_REPOSITORY_REQUIRED_NOW=NO
INTERMEDIATE_SERVER_REPOSITORY_MIGRATION_REQUIRED_NOW=NO
SECOND_INTERMEDIATE_SERVER_SOURCE_AUTHORITY=NO

DATA_BRIDGE_REPOSITORY_IS_FINAL_AIFE_SERVER_AUTHORITY=NO
DATA_BRIDGE_REPOSITORY_IS_PERMANENT_SERVER_HOME=NO

CURRENT_BRANCH_ROLE=TEMPORARY_FULL_ENGINEERING_AND_QUALIFICATION_CARRIER_UNTIL_FINAL_CANONICAL_AIFE_INTEGRATION
```

`LONG_TERM_GENERIC_SERVER_DEVELOPMENT_IN_DATA_BRIDGE_REPO=NO` означает только, что Data Bridge
не является permanent canonical home Server source. Это НЕ означает запрет полноценно разработать,
развернуть, квалифицировать, мигрировать и стабилизировать Server contour в текущем WIP до freeze.

Реальный риск отдельного промежуточного repository сейчас не доказан: он добавляет source
transition, bootstrap, drift reconciliation и дополнительную точку рассинхронизации, не улучшая
runtime correctness. Поэтому:

```text
MECHANISM=SEPARATE_AIFE_SERVER_REPOSITORY_NOW
REAL_RISK=NONE_PROVEN
SIMPLER_OPTION=YES_REUSE_CURRENT_VERSIONED_WIP_CARRIER
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=DO_NOT_ADD
```

## 6. Future-path architecture во время разработки

Все файлы будущего AIFE Server уже во время WIP разработки создаются по будущим AIFE paths:

```text
AIFE/staging/<future-AIFE-path>
→ strip prefix AIFE/staging/
→ <future-AIFE-path>
```

```text
FUTURE_AIFE_PATH_LAYOUT_DURING_DEVELOPMENT=YES
TEMP_SERVER_TREE_THAT_REQUIRES_LATER_ARCHITECTURAL_REWRITE=NO
QUALIFIED_F5_REIMPLEMENTATION_REQUIRED=NO
F5_IS_SERVER_BOOTSTRAP_FOUNDATION=YES
```

Текущая ветка является source carrier, но `AIFE/staging/**` остаётся exact future-path projection.
Final patch route должен переносить уже стабилизированные future-path files, а не перепроектировать
структуру приложения.

## 7. Canonical Server contracts и deployment layout

Существующая contract family остаётся единственной generic Server boundary:

```text
CONTRACT_SERVER_WORK=CONTRACT-SERVER-WORK-001
CONTRACT_SERVER_SCHEDULING=CONTRACT-SERVER-SCHEDULING-001
CONTRACT_SERVER_EXECUTION=CONTRACT-SERVER-EXECUTION-001
CONTRACT_SERVER_PUBLICATION=CONTRACT-SERVER-PUBLICATION-001
CONTRACT_SERVER_STORAGE=CONTRACT-SERVER-STORAGE-001
CONTRACT_SERVER_ACCESS=CONTRACT-SERVER-ACCESS-001
CONTRACT_SERVER_DEPLOYMENT=CONTRACT-SERVER-DEPLOYMENT-001
NEW_PARALLEL_SERVER_CONTRACT_BY_DEFAULT=NO
```

Текущий service filesystem/deployment model сохраняется:

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
```

Наличие spool path не доказывает необходимость отдельной spool state machine.

Штатная deployment-семантика переиспользуется:

```text
IMMUTABLE_RELEASE_MODEL=YES
DIRECT_PRODUCTION_EXECUTION_FROM_GIT_CHECKOUT=NO
PRODUCTION_UPDATE_BY_GIT_PULL=NO
DEPLOYMENT_MAP_REQUIRED=YES
DEPLOYMENT_RECEIPT_REQUIRED=YES
ATOMIC_RELEASE_ACTIVATION=YES
```

F5C/F6/F7 не создают новый deployment mechanism, пока существующий deployment contract закрывает
source→release→operational-root→activation→receipt→rollback risk.

## 8. D6 / D8 / D9: reference mechanisms, не platform primitives

```text
D6_IS_AIFE_PLATFORM_PRIMITIVE=NO
D8_IS_AIFE_PLATFORM_PRIMITIVE=NO
D9_IS_AIFE_PLATFORM_PRIMITIVE=NO
D6_D8_D9_ARE_HISTORICAL_REFERENCES_NOT_PLATFORM_PRIMITIVES=YES
```

Каждый material mechanism получает одну disposition:

```text
REUSE_AS_IS
GENERALIZE
SUPERSEDE_BY_EXISTING_AIFE_MECHANISM
RETAIN_AS_DOMAIN_OR_PROVIDER_ADAPTER
RETAIN_AS_EXPORT_ADAPTER
LEGACY_COMPATIBILITY_ONLY
RETIRE_AFTER_CUTOVER
```

D8 provenance обязателен и frozen planning зафиксировал текущую границу:

```text
VPS_D8_DEPLOYMENT_PROVENANCE_REQUIRED=YES
VPS_D8_VS_REPOSITORY_SOURCE_RECONCILIATION_REQUIRED=YES
CURRENT_GITHUB_D8_EQUALS_QUALIFIED_VPS_D8_BY_DEFAULT=NO
CURRENT_GITHUB_D8_EQUALS_CURRENT_LIVE_VPS_D8_BY_DEFAULT=NO
D8_VPS_PROVENANCE_STATUS=PARTIAL
D8_LIVE_READBACK_REQUIRED_BEFORE_C8=YES
D8_LIVE_READBACK_REQUIRED_BEFORE_C9=YES
```

До физического C8/C9 действия нужна fresh exact relation:

```text
VPS deployed D8
↕
exact historical Git source revision
↕
current repository D8 lineage
```

Partial VPS provenance не блокирует C1–C7, но без fresh live readback C8/C9 fail-closed.
D6 generic physical/read mechanisms могут быть reused только после mechanism classification;
domain-specific revision/finality/gap/market resolution остаётся domain-owned.

## 9. First durable acceptance и судьба D8 spool

F5C planning заморозил первую durable boundary; C1 её НЕ реализует и runtime proof остаётся C2.

```text
PROVIDER_RESPONSE_RECEIVED_IS_DURABLE_ACCEPTANCE=NO
CURRENT_WORK_ACCEPTED_IS_PROVIDER_BYTES_DURABLE=NO
PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=CURRENTLY_OPEN_BOUNDED
FIRST_DURABLE_ACCEPTANCE_BOUNDARY=IMMUTABLE_OBJECT_DURABLE_READBACK_PLUS_DURABLE_WORK_BINDING_COMMIT
TARGET_PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=CLOSED_AT_F5C_ACCEPTANCE_BOUNDARY
D8_SPOOL_AUTOMATIC_REUSE=NO
FIRST_DURABLE_ACCEPTANCE_RUNTIME_PROOF=NOT_YET_C2
C2_FIRST_DURABLE_ACCEPTANCE_PASS=NO
```

Frozen boundary semantics:

```text
canonical accepted payload bytes
→ immutable object durable write
→ fsync file
→ atomic create
→ fsync directory
→ independent readback/hash verification
→ durable Work binding
→ SQLite transaction COMMIT
→ AIFE_DURABLY_ACCEPTED
```

Новый ingress ledger/spool не создаётся. D8 spool ещё не удаляется и считается superseded только
после физического доказательства C2+C5:

```text
D8_SPOOL_DISPOSITION=SUPERSEDED_BY_EXISTING_AIFE_DURABLE_LIFECYCLE_AFTER_C2_C5_PROOF
```

ETH-specific spool primitive запрещён.

## 10. F5C — generic acquisition/collection + production-shaped shadow producer

```text
F5C_STAGE_ID=F5C
F5C_STAGE_SEMANTIC_ID=GENERIC_ACQUISITION_AND_COLLECTION_RUNTIME_INTEGRATION
F5C_PLANNING_REQUIRED=NO
F5C_PLANNING=PASS
F5C_IMPLEMENTATION_PLAN=AIFE/staging/docs/98-Reviews/execution/2026-08/aife-server-data-foundation/F5C_IMPLEMENTATION_PLAN_aife-server-data-foundation_2026-09-06.md
READY_FOR_F5C_DIRECT_WIP_IMPLEMENTATION=YES
F5C_STARTED=YES
F5C_C1_STATUS=PASS
F5C_C1_IMPLEMENTATION_HEAD=6bf87fcde89b6e585daa555d182153b6edf1b489
F5C_C1_IMPLEMENTATION_TREE=c662ad1060cfed7b7a3364f56aab328ed5bf51f1
F5C_C1_IMPLEMENTATION_PATH_COUNT=5
F5C_C2_STATUS=NEXT_NOT_AUTHORIZED
READY_FOR_F5C_C2_OWNER_AUTHORIZATION=YES
F5C_C2_STARTED=NO
F5C_PRODUCTION_ACTIVATION=NO
```

C1 создал одну provider-neutral acquisition boundary: injected adapter → neutral
`DomainArtifactEnvelope` + exact payload bytes → generic acquisition service. C1 не пишет durable
object, не принимает Work, не публикует и не создаёт второй scheduler/storage authority.

F5C не требует промежуточного repository migration/bootstrap:

```text
F5C_USES_CURRENT_ENGINEERING_CARRIER=YES
F5C_REPOSITORY_MIGRATION_PREREQUISITE=NO
F5C_SEPARATE_AIFE_SERVER_REPOSITORY_PREREQUISITE=NO
```

Frozen implementation scope задаётся implementation plan и не дублируется здесь полностью:

```text
IMPLEMENTATION_SCOPE_FROZEN=YES
EXACT_IMPLEMENTATION_PATH_COUNT=12
IMPLEMENTATION_SCOPE_SOURCE=F5C_IMPLEMENTATION_PLAN_aife-server-data-foundation_2026-09-06.md
UNAPPROVED_SCOPE_EXPANSION=NO
ADDITIONAL_PATH_POLICY=STOP_IF_MATERIALLY_COUPLED_INVARIANT_PROVEN
ADDITIONAL_PATH_STOP_CODE=F5C_ADDITIONAL_OUT_OF_SCOPE_COUPLED_INVARIANT_PROVEN
```

Замороженная execution sequence и текущий checkpoint state:

```text
C1=GENERIC_ACQUISITION_BOUNDARY
C1_STATUS=PASS
C2=FIRST_DURABLE_ACCEPTANCE
C2_STATUS=NEXT_NOT_AUTHORIZED
C3=DATA_BRIDGE_PROVIDER_DOMAIN_ADAPTER_BINDING
C4=PUBLICATION_STORAGE_ACCESS_REUSE
C5=RESTART_REPLAY_IDEMPOTENCY
C6=EXACT_GIT_BOUND_DEPLOYABLE_MATERIALIZATION
C7=DOCKER_QUALIFICATION
C8=SHADOW_SERVER_DEPLOYMENT
C9=REAL_PROVIDER_FORWARD_COLLECTION
C10=BOUNDED_STABILITY
IMPLEMENTATION_CHECKPOINT_COUNT=10
```

C1 owner authorization из C1 Task Contract использована и завершена. C2 требует отдельной owner
authorization; D6/D8/D9 reconciliation и durable-boundary research не повторяются.

Server должен быть production-shaped с самого F5C:

```text
PRODUCTION_SHAPED_SERVER_FROM_F5C=YES
REAL_PROVIDER_CONNECTIONS=YES
REAL_STORAGE_LAYOUT=YES
REAL_RESTART_RECOVERY=YES
REAL_DURABILITY=YES
REAL_OBSERVABILITY=YES
REAL_DEPLOYMENT_LAYOUT=YES

SERVER_RUNTIME_ROLE=PRIMARY_CAPABLE_SHADOW_PRODUCER
SHADOW_SERVER_IS_PRODUCTION_AUTHORITY=NO
PRODUCTION_CUTOVER=NO
```

`PRIMARY_CAPABLE_SHADOW_PRODUCER` означает физически пригодный будущий основной producer без
authority cutover.

## 11. Штатное server deployment и exact Git binding

После локальной/Docker qualification требуется настоящий server deployment через существующую
AIFE deployment boundary.

```text
EXACT_ENGINEERING_GIT_HEAD_TREE
→ build/materialize deployable server release
→ immutable/side-by-side install where applicable
→ bind config/state/storage
→ start
→ health validation
→ real provider collection
→ durable write
→ independent readback
→ restart/recovery
→ bounded stability observation
```

```text
DEPLOYED_SERVER_MUST_BIND_EXACT_GIT_HEAD_TREE=YES
RANDOM_WORKING_DIRECTORY_COPY_IS_CANONICAL_DEPLOYMENT=NO
NEW_DEPLOYMENT_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
```

Эта Program Map currentization сама deployment не выполняет.

## 12. F5C forward collection — обязательный gate до F5M

```text
F5C_FORWARD_COLLECTION_QUALIFICATION_BEFORE_F5M=YES
F5M_ALLOWED_ONLY_AFTER_QUALIFIED_F5C_FORWARD_COLLECTION=YES
```

До F5M должны быть физически доказаны эквивалентные свойства:

```text
REAL_PROVIDER_COLLECTION=PASS
FIRST_DURABLE_ACCEPTANCE=PASS
PERSISTENT_STORAGE=PASS
INDEPENDENT_READBACK=PASS
RESTART_RECOVERY=PASS
DEDUPE_IDEMPOTENCY=PASS
BOUNDED_STABILITY=PASS
```

Неудачный F5C forward route не обходится массовым backfill.

## 13. F5M — controlled historical corpus migration

F5M начинается только после qualified forward collection.

```text
F5M_STAGE_ID=F5M
F5M_REQUIRES_QUALIFIED_FORWARD_COLLECTION_ROUTE=YES
MIGRATION_EXECUTED=NO

MIGRATION_BOUNDED=YES
MIGRATION_REVERSIBLE=YES
MIGRATION_READBACK_VERIFIED=YES
MIGRATION_IDENTITY_AWARE=YES
MIGRATION_SEMANTICS_PRESERVING=YES

LEGACY_DATA_DELETION=NO_BEFORE_MIGRATION_PROOF
LEGACY_READ_ROUTE_RETIREMENT=NO_BEFORE_READ_PARITY
ROLLBACK_PATH_REQUIRED=YES
```

F5M обязан проверить:

- completeness;
- identity preservation;
- ordering;
- revision/finality semantics;
- independent physical readback;
- restart/recovery;
- consumer equivalence там, где применимо.

Точный миграционный corpus определяется fresh в F5M; он не фиксируется этой картой заранее.

## 14. F6/F7 — full working Server acceptance

После F5C/F5M выполняется интегральная квалификация рабочего Server contour:

```text
F6_F7_COVER=
COLLECTION
+STORAGE
+ACCESS_READ
+RECOVERY
+CONCURRENCY
+FAILURE_HANDLING
+CONSUMER_BEHAVIOR
+MIGRATION_CORRECTNESS
+OPERATIONAL_STABILITY
+SCALABILITY_INVARIANTS
```

```text
HORIZONTAL_SCALING_BY_DESIGN=YES
MULTI_NODE_IMPLEMENTATION_NOW=NO
```

Новый distributed backend, queue, scheduler, cluster или orchestration product добавляется только
после доказанного trigger.

## 15. Development loop до exact freeze

До завершения working server contour:

```text
CANONICAL_PATCH_SYSTEM_PER_DEVELOPMENT_ITERATION=NO
CANONICAL_TOOLCHAIN_PER_DEVELOPMENT_ITERATION=NO
AEB_PER_DEVELOPMENT_ITERATION=NO
PORTABLE_PATCH_PER_DEVELOPMENT_ITERATION=NO
RECOVERY_ZIP_AS_PRIMARY_SOURCE_AUTHORITY=NO
GIT_HEAD_TREE_IS_PRIMARY_DEVELOPMENT_AUTHORITY=YES
DEVELOPMENT_CONTINUATION_AUTHORITY=GITHUB_EXACT_BRANCH_HEAD_TREE
ALL_NECESSARY_SOURCE_AND_PLANNING_STATE=COMMIT_AND_PUSH_TO_CURRENT_WIP

MANDATORY_RECOVERY_ZIP_PER_DEVELOPMENT_ITERATION=NO
RECOVERY_ZIP_IS_REQUIRED_FOR_NORMAL_GITHUB_CONTINUATION=NO
RECOVERY_ZIP_POLICY=EXCEPTION_ONLY
```

Recovery ZIP допускается только для отдельного доказанного риска:

```text
UNPUBLISHED_UNIQUE_BYTES
NON_REPOSITORY_PORTABLE_EVIDENCE
TEMPORARY_GITHUB_WRITE_CAPABILITY_FAILURE
CROSS_ENVIRONMENT_BINARY_TRANSPORT
```

Fresh external runtime state не является Recovery artifact:

```text
LIVE_VPS_STATE=FRESH_PHYSICAL_READBACK_REQUIRED
LIVE_VPS_STATE_FROM_OLD_RECOVERY_ZIP=FORBIDDEN
```

Reference/toolchain substrates вроде `AIFE_review_latest.zip` и
`AIFE_quality_toolchain_linux_x86_64_py311.zip` не копируются в новый Recovery ZIP после каждой
обычной Git iteration.

Inner loop:

```text
edit
→ targeted tests
→ commit
→ push current WIP
→ remote readback
→ Docker/runtime qualification where required
→ exact-Git-bound shadow deployment/qualification where required
→ next iteration
```

Можно отложить только несемантический style/docstring/typing/lint/metadata cleanup, который не
влияет на correctness/safety/clarity. Нельзя откладывать data loss, duplication, identity,
idempotency, lease/fencing, concurrency, ACK, restart/recovery, corruption, backpressure,
durable-acceptance, domain leakage или scalability-boundary defects.

## 16. Exact working Server Git freeze

Freeze разрешён только когда:

- F5C real forward collection qualified;
- production-shaped shadow server стабилен;
- F5M выполнена и подтверждена;
- F6/F7 прошли применимую full acceptance;
- working contour не имеет известных correctness blockers.

```text
EXACT_WORKING_SERVER_GIT_FREEZE=REQUIRED
FREEZE_IDENTITY=REPOSITORY+BRANCH+HEAD+TREE+PATH_SET

FREEZE_REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
FREEZE_BRANCH=agent/aife/server-data-foundation-wip
```

Exact HEAD/TREE фиксируются только в момент фактического freeze.

## 17. Final canonical AIFE integration boundary

Frozen working WIP — единственный source input final canonicalization.

```text
WORKING_SERVER_WIP
→ fresh canonical AIFE reconciliation
→ canonical AIFE patch system
→ canonical path placement
→ AIFE quality normalization
→ canonical AIFE toolchain
→ Candidate
→ Owner Authorization
→ FINAL AEB
→ receiver-side qualification
→ canonical AIFE workspace integration
→ canonical AIFE Git publication/integration
```

```text
FINAL_CANONICAL_PATCH_SYSTEM_REQUIRED=YES
FINAL_CANONICAL_TOOLCHAIN_REQUIRED=YES
FINAL_AEB_REQUIRED=YES
MAIN_INTEGRATION_ONLY_AFTER_FINAL_CANONICAL_PASS=YES
CANONICAL_AIFE_INTEGRATION_AFTER_WORKING_SERVER=YES
DATA_BRIDGE_WIP_REPLACES_FINAL_AIFE_PATCH_ROUTE=NO
```

Это единственная обязательная тяжёлая canonical quality boundary. Exact final AIFE base
определяется fresh в момент final integration.

## 18. Post-integration canonical Server redeploy / synchronization

Ранее квалифицированный WIP server не считается автоматически byte-equivalent каноническому AIFE
после patch normalization/integration.

```text
TESTED_WIP_SERVER_MUST_BE_RECONCILED_WITH_CANONICAL_AIFE_SERVER=YES
CANONICAL_POST_INTEGRATION_SERVER_REDEPLOY_REQUIRED=YES
```

Обязательная последовательность:

```text
canonical AIFE integrated source
→ canonical deployable server build/materialization
→ update/redeploy server through canonical deployment boundary
→ exact canonical source identity verification
→ health
→ real collection
→ durable write
→ independent readback
→ restart/recovery
→ behavior equivalence
```

Этот этап не является production cutover.

## 19. F8 — только отдельно авторизованный production cutover

```text
F8_PRODUCTION_CUTOVER_REQUIRES_SEPARATE_OWNER_AUTHORIZATION=YES
PRODUCTION_CUTOVER_AUTOMATIC=NO
```

Только после post-integration canonical server synchronization владелец может отдельно
авторизовать:

```text
PRIMARY_CAPABLE_SHADOW_PRODUCER
→ CANONICAL_AIFE_PRIMARY_PRODUCER
```

Controlled retirement старого producer/runtime разрешается только после подтверждённого cutover
и сохранения требуемого rollback/readability path.

## 20. GitHub / storage role

```text
GITHUB_IS_PRIMARY_HIGH_VOLUME_RUNTIME_DATA_WAREHOUSE=NO
GITHUB_IS_REQUIRED_FOR_CONTINUOUS_COLLECTION_RUNTIME=NO
SERVER_RUNTIME_AUTONOMY_FROM_GITHUB=YES
```

GitHub остаётся code/governance/config/contracts/evidence/export authority. Runtime collection и
durability не требуют synchronous GitHub availability. Export/replication может догонять позже.

## 21. Extensibility acceptance

```text
NEW_SOURCE_OR_INSTRUMENT_WITHOUT_SERVER_CORE_REWRITE=YES
NEW_SOURCE_OR_INSTRUMENT_REQUIRES_SERVER_CORE_REWRITE=NO
```

В F5C/F6/F7 это должен стать физическим acceptance test: второй source/provider/instrument
подключается через config + provider/domain adapter + capability registration без переписывания
generic Work/Scheduling/Publication/Storage Core.

## 22. Трёхвопросный architecture/process gate

Для каждого нового или сохраняемого mechanism:

1. Какой реальный риск он закрывает?
2. Можно ли закрыть этот риск существующим механизмом или проще?
3. Уменьшает ли решение число действий и точек рассинхронизации для следующего агента/инженера?

```text
NEW_MECHANISM_DEFAULT_DECISION=DO_NOT_ADD
NO_REAL_RISK=DO_NOT_ADD
SIMPLER_EQUAL_GUARANTEE_EXISTS=USE_SIMPLER_MECHANISM
UNJUSTIFIED_ACTION_STATE_HANDOFF_GROWTH=SIMPLIFY_OR_REMOVE
```

Минимально применять к:

```text
SEPARATE_AIFE_SERVER_REPOSITORY
SECOND_WIP_BRANCH
SECOND_STORAGE_LEDGER
D8_SPOOL
NEW_DEPLOYMENT_MECHANISM
NEW_MIGRATION_LEDGER
NEW_SERVER_PACKAGE_FORMAT
NEW_RUNTIME_SCHEDULER
NEW_PUBLICATION_MECHANISM
```

Current dispositions:

```text
SEPARATE_AIFE_SERVER_REPOSITORY=DO_NOT_ADD
SECOND_WIP_BRANCH=DO_NOT_ADD
D8_SPOOL=SUPERSEDED_BY_EXISTING_AIFE_DURABLE_LIFECYCLE_AFTER_C2_C5_PROOF
NEW_DEPLOYMENT_MECHANISM=DO_NOT_ADD_UNLESS_EXISTING_DEPLOYMENT_CONTRACT_PROVEN_INSUFFICIENT
NEW_MIGRATION_LEDGER=DO_NOT_ADD_UNLESS_EXISTING_DURABLE_STATE_CANNOT_EXPRESS_REQUIRED_PROOF
NEW_RUNTIME_SCHEDULER=DO_NOT_ADD
NEW_PUBLICATION_MECHANISM=DO_NOT_ADD_UNLESS_EXISTING_PUBLICATION_CONTRACT_PROVEN_INSUFFICIENT
```

## 23. Program sequence

```text
F0–F4 [HISTORICAL_SATISFIED]
→ F5P [SATISFIED]
→ F5 [TECHNICALLY_QUALIFIED]
→ F5C [C1 PASS; C2..C10 NEXT]
→ F5M [HISTORICAL DATA MIGRATION]
→ F6/F7 [FULL SERVER / CONSUMER / OPERATIONAL QUALIFICATION]
→ EXACT_WORKING_SERVER_GIT_FREEZE
→ FINAL_AIFE_PATCH_SYSTEM
→ CANONICAL_QUALITY_NORMALIZATION_AND_TOOLCHAIN
→ CANDIDATE / OWNER_AUTHORIZATION / FINAL_AEB
→ CANONICAL_AIFE_INTEGRATION
→ CANONICAL_AIFE_SERVER_REDEPLOY_AND_EQUIVALENCE
→ F8 [SEPARATELY_AUTHORIZED_PRODUCTION_CUTOVER]
```

```text
NEXT_OWNER_TASK=AUTHORIZE_F5C_C2_FIRST_DURABLE_ACCEPTANCE
NEXT_RECOMMENDED_TASK=F5C_C2_FIRST_DURABLE_ACCEPTANCE
```

## 24. Acceptance summary

```text
PROGRAM_MAP_CURRENTIZED=YES
PROGRAM_MAP_VERSION=0.10
PROGRAM_MAP_AND_F5C_PLAN_CONSISTENCY=PASS
PROGRAM_MAP_AND_README_CONSISTENCY=PASS
PROGRAM_MAP_AND_AEB_PLAN_CONSISTENCY=PASS
LIVE_AUTHORITY_CONSISTENCY=PASS

CURRENT_WIP_BRANCH_REMAINS_ENGINEERING_CARRIER=YES
SEPARATE_AIFE_SERVER_REPOSITORY_REQUIRED_NOW=NO
INTERMEDIATE_SERVER_REPOSITORY_MIGRATION_REQUIRED=NO
DATA_BRIDGE_REPOSITORY_IS_FINAL_AIFE_SERVER_AUTHORITY=NO

F5_REIMPLEMENTATION_REQUIRED=NO
F5C_PREIMPLEMENTATION_PLANNING=PASS
F5C_STARTED=YES
F5C_C1_STATUS=PASS
F5C_C1_IMPLEMENTATION_HEAD=6bf87fcde89b6e585daa555d182153b6edf1b489
F5C_C1_IMPLEMENTATION_TREE=c662ad1060cfed7b7a3364f56aab328ed5bf51f1
F5C_C1_IMPLEMENTATION_PATH_COUNT=5
F5C_C2_STATUS=NEXT_NOT_AUTHORIZED
READY_FOR_F5C_C2_OWNER_AUTHORIZATION=YES
F5C_C2_STARTED=NO
C2_FIRST_DURABLE_ACCEPTANCE_PASS=NO
EXACT_IMPLEMENTATION_PATH_COUNT=12
IMPLEMENTATION_CHECKPOINT_COUNT=10
FIRST_DURABLE_ACCEPTANCE_CONTRACT=FROZEN
FIRST_DURABLE_ACCEPTANCE_RUNTIME_PROOF=NOT_YET_C2
D8_VPS_PROVENANCE_STATUS=PARTIAL
D8_LIVE_READBACK_REQUIRED_BEFORE_C8=YES
D8_LIVE_READBACK_REQUIRED_BEFORE_C9=YES
F5C_FORWARD_COLLECTION_BEFORE_F5M=YES
PRODUCTION_SHAPED_SHADOW_SERVER=YES
SHADOW_SERVER_IS_PRODUCTION_AUTHORITY=NO
F5M_ONLY_AFTER_QUALIFIED_FORWARD_COLLECTION=YES

GITHUB_HEAD_TREE_IS_CONTINUATION_AUTHORITY=YES
RECOVERY_ZIP_REQUIRED_FOR_NORMAL_CONTINUATION=NO
RECOVERY_ZIP_POLICY=EXCEPTION_ONLY

EXACT_GIT_FREEZE_BEFORE_FINAL_PATCH_SYSTEM=YES
CANONICAL_PATCH_SYSTEM_PER_DEVELOPMENT_ITERATION=NO
CANONICAL_TOOLCHAIN_PER_DEVELOPMENT_ITERATION=NO
AEB_PER_DEVELOPMENT_ITERATION=NO

FINAL_CANONICAL_PATCH_SYSTEM_REQUIRED=YES
FINAL_CANONICAL_TOOLCHAIN_REQUIRED=YES
FINAL_AEB_REQUIRED=YES
CANONICAL_AIFE_INTEGRATION_AFTER_WORKING_SERVER=YES
CANONICAL_POST_INTEGRATION_SERVER_REDEPLOY_REQUIRED=YES
F8_PRODUCTION_CUTOVER_REQUIRES_SEPARATE_OWNER_AUTHORIZATION=YES

F5M_STARTED=NO
REAL_AIFE_MUTATION=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
```

Эта version 0.10 currentization фиксирует C1 PASS и следующий C2 owner gate. Она не выполняет
C2 implementation, Docker/VPS readback/mutation, F5M, real AIFE mutation, toolchain, patch/AEB
или production cutover.
