# Market-data storage portability and canonical publication v2

```text
CONTRACT_ID=ETH-MARKET-DATA-STORAGE-PORTABILITY-V2
STATUS=SOURCE_RECONCILIATION_CANDIDATE_NOT_ACTIVE
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
CURRENT_PHYSICAL_BACKEND_PROFILE=GITHUB_FIRST_V1
```

## Назначение

Документ reconciles D8/D9 authority, storage и publication semantics до дальнейшей physical deployment qualification. Он не активирует D8/D9, не меняет active D6 route и не разворачивает новый backend.

Machine authority остаётся `bridge-contract.json`; этот документ поясняет его contract fields и `contracts/d8-d9-forwarding-v1.json`.

## 1. Пять независимых слоёв

```text
semantic/logical authority
!= lifecycle residence role
!= publication/ACK state
!= physical storage backend
!= execution/deployment plane
```

Data Bridge владеет market-data semantic authority. GitHub, VPS, Docker volume, filesystem, PostgreSQL, ClickHouse и object storage — physical/execution mechanisms. Они не становятся semantic authority сами по себе.

## 2. Lifecycle

```text
CURRENT=HOT
HISTORY=WARM+COLD
FORWARD_ARCHIVING=HOT_TO_WARM
SEALING=WARM_TO_COLD
```

HOT/WARM/COLD — backend-neutral residence roles.

Current physical profile:

```text
CURRENT_PHYSICAL_BACKEND_PROFILE=GITHUB_FIRST_V1
REGULAR_GRID_CURRENT_WARM_BACKEND=DECLARED_DATA_BRIDGE_GIT_RESOURCES
CURRENT_COLD_BACKEND=QUALIFIED_IMMUTABLE_GITHUB_RELEASE_ASSETS
```

Эти technologies не входят в semantic ontology.

## 3. D8 operational state

```text
D8_RUNTIME_STATE_BACKEND=SQLITE_WAL
D8_RUNTIME_STATE_ROLE=OPERATIONAL_RUNTIME_STATE
D8_RUNTIME_STATE_IS_D9_HISTORY_AUTHORITY=false
```

SQLite хранит HOT/SPOOL/cycles/ledger/checkpoints/leases/recovery evidence. Его возможная замена — отдельная runtime-state migration axis и не связана автоматически с D9 history backend migration.

## 4. Existing D8→D9 source primitive

`src/d8_d9_forwarder.py`, `src/d8_d9_forwarder_integrity.py` и `src/history_store.py` сохраняют полезные guarantees:

- exact storage-independent `observation_id`;
- checkpoint-v2 source binding;
- no provider reacquisition/fallback/synthetic fill;
- immutable identity conflict fail-closed;
- at-least-once forwarding semantics;
- effectively-once local observation identity;
- crash-before-write / crash-after-write-before-ACK retry semantics;
- lifecycle/gap evidence preservation.

Но Path/filesystem materialization классифицируется как:

```text
CURRENT_PHYSICAL_PRIMITIVE
```

а не как D9 semantic authority.

## 5. Confirmed resolver gap

Merged local forwarder умеет создавать:

```text
<warm_root>/d8-origin/fixed-grid|sampled-schedule/<series-token>/YYYY/MM/DD.json
```

Canonical D9 v2 resolver authority строится из declared control-plane resources (`warm_manifest_path`, generation/release metadata, collection-run control evidence) и не сканирует arbitrary VPS filesystems.

```text
D8_ORIGIN_LOCAL_FORWARDER=SOURCE_IMPLEMENTED
D8_ORIGIN_CANONICAL_PUBLICATION=NOT_YET_IMPLEMENTED
D8_ORIGIN_RESOLVER_AUTHORITY=RECONCILED_CONTRACT_NOT_PHYSICALLY_QUALIFIED
```

Запрещённые fixes: direct server path reader, second resolver, second reader, agent-visible filesystem locator, manual `d8-origin` stitching.

Required transition:

```text
D8 batch
→ canonical backend publication
→ backend/control-plane metadata
→ existing capability/resolver-visible authority
→ canonical ResolutionPlan
→ existing reader
```

## 6. PublicationBatch

Canonical schema: `schema/history-publication-batch-v1.schema.json`.

Batch identity storage-independent. Она связывает ordered observation membership, membership hash, aggregate payload hash, target `WARM`, selected current backend profile и publication attempt identity.

```text
PARTIAL_ACK=false
DEFAULT_ACK_POLICY=FAIL_CLOSED_WHOLE_BATCH
GIT_COMMIT_PER_OBSERVATION=false
```

Acquisition M5 cadence не определяет publication cadence. Bounded publication policy позже может использовать max age/count/bytes/spool pressure без изменения lifecycle ontology.

## 7. Minimal History Publication / Write Port

В текущей задаче определяется только минимальная semantic boundary:

1. принять deterministic PublicationBatch;
2. материализовать через selected current backend profile;
3. получить backend durability evidence;
4. выполнить independent backend-appropriate verification/read-back;
5. проверить exact batch membership/content/integrity;
6. связать/опубликовать canonical control-plane metadata для existing resolver visibility;
7. вернуть durable publication evidence.

```text
PUBLICATION_PORT_STATUS=CONTRACT_DEFINED_IMPLEMENTATION_NEXT
NEXT_SOURCE_TASK=ETH-D8-D9-CANONICAL-PUBLICATION-PORT-V1
```

Generic plugin manager/factory/event bus не создаётся.

## 8. Canonical ACK

Production rule:

```text
D8 PENDING -> FORWARDED
IFF CANONICAL_PUBLICATION_ACK
```

ACK требует одновременно:

- exact batch принят current canonical WARM backend;
- durability gate PASS;
- independent verification/read-back PASS;
- exact identity/order/payload/integrity binding PASS;
- resulting physical authority representable through canonical Data Bridge control plane/resolver route.

```text
LOCAL_FILESYSTEM_WRITE_SUFFICIENT_FOR_PRODUCTION_ACK=false
```

Crash after backend commit but before canonical ACK оставляет D8 PENDING. Retry должен verify exact already-published batch и завершить ACK без duplicate identity.

## 9. ResolutionPlan v2

D9 v2 не active, поэтому contract/schema мигрирует к разделению:

```text
residence_role=HOT|WARM|COLD
adapter_profile=<versioned physical profile>
resource_ref=<opaque canonical resource identity>
physical_descriptor=<adapter-owned details>
integrity_evidence=<backend-specific proof>
```

Technology-specific `storage` в текущем candidate сохраняется как **deprecated compatibility alias**, чтобы не ломать существующий v2 reader/tests до implementation migration. Он не является canonical future terminology и не выбирается consumer-ом. ResolutionPlan v3 ради этого не создаётся.

Active D6 ResolutionPlan v1 не изменяется.

## 10. Backend substitution

Mental test:

```text
GitHub WARM -> PostgreSQL WARM
```

Могут измениться adapter/profile, descriptors, migration/backfill tooling, durability proof и deployment. Не меняются:

- semantic request;
- `series_id`;
- `observation_id`;
- D8 observation envelope;
- D9 lifecycle;
- canonical resolver family;
- canonical reader family;
- normalized result semantics;
- `history-access-receipt/2.0.0` semantic meaning.

```text
BACKEND_SUBSTITUTION_TEST=PASS
POSTGRES_IMPLEMENTATION_NOW=NO
POSTGRES_MIGRATION_PATH_DEFINED=YES
EXISTING_SERVER_POSTGRES_REUSE_DECISION=NOT_MADE
```

## 11. High-cardinality

```text
HIGH_CARDINALITY_LOGICAL_MODEL=PRESERVED
HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_VERSIONED_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

Historical mutable GitHub prerelease WARM assumption is `HISTORICAL_PLAN_DECISION_SUPERSEDED`; published prerelease immutability evidence запрещает тихо использовать её как mutable backend.

## 12. D9 status

```text
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=COMPLETE_WITH_PUBLICATION_PORTABILITY_GAP_IDENTIFIED
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=NOT_QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVATION=PENDING
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
```

Source completeness, physical qualification и activation не смешиваются.

## 13. Server boundary

Server snapshot подтверждает D8 persistent SQLite operational volume и не требует permanent D9 WARM semantic volume.

```text
PERMANENT_VPS_D9_WARM_REQUIRED=NO
VPS_IS_MARKET_DATA_AUTHORITY=false
EXISTING_SERVER_POSTGRES_REUSE_DECISION=NOT_MADE
```

Source task не изменяет `CORE/ai-revenue-lab` и не выполняет VPS commands/deployment.

Qualification-only local VPS WARM root не является следующим production proof: он повторил бы source/CI local semantics, но не доказал canonical GitHub publication, remote durability, resolver visibility или canonical ACK. Preserved real SPOOL остаётся для later physical qualification после implementation `ETH-D8-D9-CANONICAL-PUBLICATION-PORT-V1`.
