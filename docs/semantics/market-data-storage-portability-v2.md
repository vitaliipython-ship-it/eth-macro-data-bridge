# Market-data storage portability and canonical publication v2

```text
CONTRACT_ID=ETH-MARKET-DATA-STORAGE-PORTABILITY-V2
STATUS=SOURCE_IMPLEMENTED_PUBLICATION_PORT_MERGED_PHYSICAL_QUALIFICATION_PASS
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
CURRENT_PHYSICAL_BACKEND_PROFILE=GITHUB_FIRST_V1
```

## Назначение

Документ reconciles D8/D9 authority, storage и publication semantics после owner-accepted A1/A2 physical qualification. Canonical Publication Port source реализован, qualified/merged и физически квалифицирован на exact current-generation VPS_SHADOW evidence; это **не** активирует D8/D9, не меняет active D6 route, не активирует Binance USD-M provider authority и не разворачивает новый backend.

Machine authority остаётся `bridge-contract.json`; этот документ поясняет его contract fields и `contracts/d8-d9-forwarding-v1.json`. Current reconciled physical status фиксируется в `contracts/d8-a2-physical-qualification-status-v1.json`; `contracts/d8-shadow-post-reset-status-v1.json` остаётся historical predecessor snapshot и не переписывается под более поздние A1/A2 facts.

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

Current status contract records the accepted A2 observation point as `SPOOL/PENDING/FORWARDED=20/0/20`; this is `RECONCILED_SNAPSHOT_VALUES_NOT_CONTINUOUS_LIVE_STATE`, not continuous VPS truth. Fresh server readback is still required before future physical action.

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

Path/filesystem materialization remains classified as:

```text
CURRENT_PHYSICAL_PRIMITIVE
```

and is not D9 semantic authority.

## 5. Resolver/publication gap status

Merged local forwarder умеет создавать:

```text
<warm_root>/d8-origin/fixed-grid|sampled-schedule/<series-token>/YYYY/MM/DD.json
```

Arbitrary local/VPS paths по-прежнему не являются resolver authority. Source-level canonical publication/control-plane gap, выявленный до PR #118, закрыт merged Canonical Publication Port. Owner-accepted A2 evidence now also closes the real VPS_SHADOW physical qualification gap for the exact 20-member batch.

```text
D8_ORIGIN_LOCAL_FORWARDER=SOURCE_IMPLEMENTED
D8_ORIGIN_CANONICAL_PUBLICATION=SOURCE_IMPLEMENTED_QUALIFIED_MERGED_PHYSICAL_RUNTIME_QUALIFIED
D8_ORIGIN_RESOLVER_AUTHORITY=RECONCILED_CONTRACT_PHYSICALLY_QUALIFIED_NOT_ACTIVE
REAL_D8_VPS_RUNTIME_PUBLICATION=QUALIFIED
CANONICAL_PUBLICATION_QUALIFIED=true
PHYSICAL_VPS_D8_TO_D9_QUALIFIED=true
CROSS_TIER_SEMANTIC_READ_QUALIFIED=true
```

`NOT_ACTIVE` is deliberate: physical qualification != provider/runtime/D9 authority activation.

Запрещённые fixes остаются прежними: direct server path reader, second resolver, second reader, agent-visible filesystem locator, manual `d8-origin` stitching.

Canonical transition proven by A2:

```text
D8 checkpoint-v2 batch
→ canonical backend publication
→ independent remote read-back
→ backend/control-plane metadata
→ existing capability/resolver visibility
→ canonical ResolutionPlan
→ existing reader
→ CANONICAL_PUBLICATION_ACK
→ exact PENDING → FORWARDED
```

Old pre-reset `261` PENDING (`62` checkpoint-v2 eligible + `199` legacy pre-checkpoint-v2) remain forensic-only and were not restored or used for current qualification.

## 6. PublicationBatch

Canonical schema: `schema/history-publication-batch-v1.schema.json`.

Batch identity storage-independent. Она связывает ordered observation membership, membership hash, aggregate payload hash и target `WARM`. Selected backend profile and publication attempt identity are explicitly outside logical batch identity.

Canonical JSON primitive remains repository-owned `src/canonical_json.py`:

```text
UTF8=true
SORT_KEYS=true
COMPACT_SEPARATORS=true
ENSURE_ASCII=false
TRAILING_NEWLINE=false
CANONICAL_JSON_NONFINITE_POLICY=REJECT
ALLOW_NAN=false
```

`NaN`, `Infinity` и `-Infinity` не допускаются в canonical identity/hashing bytes и fail closed через stdlib `json.dumps(..., allow_nan=False)`.

```text
PARTIAL_ACK=false
DEFAULT_ACK_POLICY=FAIL_CLOSED_WHOLE_BATCH
GIT_COMMIT_PER_OBSERVATION=false

PUBLICATION_BATCH_REPOSITORY_IMPLEMENTATION_DETERMINISM=PASS
PUBLICATION_BATCH_INPUT_ORDER_INDEPENDENCE=PASS
PUBLICATION_BATCH_PREIMAGE_DETERMINISM=PASS
PUBLICATION_BATCH_INDEPENDENT_REFERENCE_RECOMPUTATION=PASS
PUBLICATION_BATCH_CROSS_LANGUAGE_DETERMINISM=NOT_REQUIRED_BY_CURRENT_SINGLE_RUNTIME_IMPLEMENTATION
```

Acquisition M5 cadence не определяет publication cadence. Bounded publication policy использует bounded max age/count/bytes/spool pressure без изменения lifecycle ontology.

## 7. Minimal History Publication / Write Port

Canonical Publication Port реализован и merged в PR #118. Он выполняет минимальную semantic boundary:

1. принять deterministic PublicationBatch;
2. материализовать через selected current backend profile;
3. получить backend durability evidence;
4. выполнить independent backend-appropriate verification/read-back;
5. проверить exact batch membership/content/integrity;
6. связать/опубликовать canonical control-plane metadata для existing resolver visibility;
7. вернуть whole-batch canonical ACK evidence.

Current source + physical status:

```text
PUBLICATION_PORT_STATUS=SOURCE_IMPLEMENTED_QUALIFIED_MERGED
SOURCE_QUALIFICATION_RUN=32318193771
A1_FRESH_CHECKPOINT_V2=PASS
A2_CANONICAL_PUBLICATION=PASS
A2_CANONICAL_ACK=PASS
A2_PENDING_TO_FORWARDED=PASS
A2_IDEMPOTENT_REPLAY=PASS
PHYSICAL_PUBLICATION_PORT_QUALIFICATION=PASS
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=true
NEXT_REQUIRED_STAGE=FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION
```

The accepted A2 identity is exact and remains byte-preserved:

```text
A2_BATCH_ID=pub-0e3a0d13c5ea7d46c50a13285a1c0372190123be620b92a7a2a062bf70ca5b42
A2_DATA_COMMIT=789d24c26af5cfd36b3be62a89093fd8becbc684
A2_CONTROL_COMMIT=f05a33df6bc661ed14941cb47487439f28f92d58
A2_MEMBER_COUNT=20
A2_MEMBERSHIP_SHA256=2f97f71630e8f42704e563c872356ef4212ae7a324286303506e0677ac796a3d
A2_PAYLOAD_SHA256=a2856c0ccc0610d87f796949c8dfa4046286e93cc164f95588438e9a402054b5
A2_CONTROL_BLOB=2cf28f2b4594eed0150cc79c31088ba2341e94d7
A2_RESOURCE_BLOB=80e54eaec28c78019839d67167917d520c68abc9
SECOND_LOGICAL_BATCH=NO
```

Replay was an exact already-present no-op: no new logical batch/resource/data commit/control entry, no provider reacquisition, no resource/control rewrite and no state mutation.

Current horizontal proof boundary remains:

```text
D8_CAPABILITY_ROUTING_HORIZONTAL_EXTENSIBILITY=PASS
D8_DUE_POLICY_DECLARATION_DERIVATION=PASS
FORWARDER_DECLARATION_DRIVEN_ROUTING=PASS
PUBLICATION_BATCH_BACKEND_ORTHOGONALITY=PASS
NEW_INSTRUMENT_SUPPORTED_FAMILY_ROUTING=PASS
NEW_METRIC_EXISTING_LIFECYCLE_ROUTING=PASS
END_TO_END_NEW_SERIES_PUBLICATION_RESOLVER_READER_EXTENSIBILITY=PASS_SOURCE_QUALIFICATION
```

Source acceptance after PR #118 remains:

```text
NEW_SERIES_END_TO_END_REQUIRES_SECOND_RESOLVER=NO
NEW_SERIES_END_TO_END_REQUIRES_SECOND_READER=NO
NEW_SERIES_END_TO_END_REQUIRES_NEW_HISTORY_SUBSYSTEM=NO
NEW_SERIES_END_TO_END_REQUIRES_NEW_PUBLICATION_PROTOCOL=NO
```

Generic plugin manager/factory/event bus is not created.

## 8. Canonical ACK

Production rule remains:

```text
D8 PENDING -> FORWARDED
IFF CANONICAL_PUBLICATION_ACK
```

ACK requires simultaneously:

- exact batch accepted by current canonical WARM backend;
- durability gate PASS;
- independent verification/read-back PASS;
- exact identity/order/payload/integrity binding PASS;
- resulting physical authority representable through canonical Data Bridge control plane/resolver route.

```text
LOCAL_FILESYSTEM_WRITE_SUFFICIENT_FOR_PRODUCTION_ACK=false
```

A2 physically exercised this exact rule for 20 observations and reached whole-batch ACK before `PENDING→FORWARDED`. Replay then proved already-present idempotency without a second logical batch or new GitHub mutation.

Publication credential boundary remains:

```text
D8_RUNTIME_AUTH=D8_RUNTIME_TOKEN
GITHUB_TOKEN_REQUIRED_INSIDE_D8_RUNTIME=false
PUBLICATION_CREDENTIALS_OWNER=SEPARATELY_AUTHORIZED_PUBLICATION_EXECUTOR_OR_ADAPTER
PUBLIC_D8_INGRESS_REQUIRED=false
```

## 9. ResolutionPlan v2

D9 v2 is not active, so contract/schema remains separated into:

```text
residence_role=HOT|WARM|COLD
adapter_profile=<versioned physical profile>
resource_ref=<opaque canonical resource identity>
physical_descriptor=<adapter-owned details>
integrity_evidence=<backend-specific proof>
```

Technology-specific `storage` in current candidate remains a **deprecated compatibility alias** until pre-activation implementation migration. It is not canonical future terminology and is not selected by the consumer. ResolutionPlan v3 is not created for this.

Active D6 ResolutionPlan v1 is unchanged.

## 10. Backend substitution

Mental test:

```text
GitHub WARM -> PostgreSQL WARM
```

May change adapter/profile, descriptors, migration/backfill tooling, durability proof and deployment. Do not change:

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

Historical mutable GitHub prerelease WARM assumption is `HISTORICAL_PLAN_DECISION_SUPERSEDED`; published prerelease immutability evidence forbids silently using it as a mutable backend.

## 12. D9 status

```text
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
D9_REAL_D8_RUNTIME_TO_CANONICAL_WARM=PHYSICAL_QUALIFICATION_PASS
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVATION=PENDING
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
ACTIVE_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
D9_V2_ACTIVE=false
```

Source implementation, repository/Actions source qualification, real runtime physical qualification and activation remain separate axes.

Current next-stage authority comes from `contracts/d9-sealing-candidate.json`:

```text
STATUS=CANDIDATE_NOT_ACTIVE
REGULAR_GRID_PERIOD_POLICY=COMPLETED_MONTH_ONLY
ACTIVE_PERIOD_SEALING=false
NEXT_REQUIRED_STAGE=FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION
REAL_D9_COLD_PHYSICAL_QUALIFICATION=BLOCKED_UNTIL_ELIGIBLE_GENERATION
```

No COLD/sealing gate is marked complete by A2 and activation is not authorized.

## 13. Server boundary

Accepted external server evidence now covers completed forensic preservation/reset/deployment plus A1/A2 physical qualification. VPS still is not market-data semantic authority and permanent D9 WARM volume is not required.

```text
OLD_PENDING_FORENSICALLY_PRESERVED=true
OLD_PENDING_RESTORE_AUTHORIZED=false
CONTROLLED_SHADOW_RESET=PASS
CURRENT_D8_PROFILE=VPS_SHADOW
CURRENT_STATE_SCHEMA_VERSION=2
CURRENT_SPOOL_TOTAL=20
CURRENT_PENDING_TOTAL=0
CURRENT_FORWARDED_TOTAL=20
CURRENT_STATE_FIELDS_SEMANTICS=RECONCILED_SNAPSHOT_VALUES_NOT_CONTINUOUS_LIVE_STATE
A1_FRESH_CHECKPOINT_V2=PASS
A2_CANONICAL_PUBLICATION=PASS
A2_CANONICAL_ACK=PASS
A2_PENDING_TO_FORWARDED=PASS
A2_IDEMPOTENT_REPLAY=PASS
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=true
PERMANENT_VPS_D9_WARM_REQUIRED=NO
VPS_IS_MARKET_DATA_AUTHORITY=false
EXISTING_SERVER_POSTGRES_REUSE_DECISION=NOT_MADE
```

The repository reconciliation does not mutate server/VPS/n8n state and does not call providers. Before any future physical action, current server state must be read again from server execution authority.

The next program predecessor is not another A1/A2 action: it is the first production-eligible completed generation under `COMPLETED_MONTH_ONLY`. After eligibility, a separately owner-authorized task may execute the existing immutable D9 COLD publication/read-back and real cross-boundary semantic qualification. This document does not authorize sealing, COLD publication, provider transition, cutover or activation.

Old pre-reset 261 PENDING remain forensic evidence and are not restored as live input without separate owner authorization.
