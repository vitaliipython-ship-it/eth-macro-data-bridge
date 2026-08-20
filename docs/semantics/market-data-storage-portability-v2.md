# Market-data storage portability and canonical publication v2

```text
CONTRACT_ID=ETH-MARKET-DATA-STORAGE-PORTABILITY-V2
STATUS=SOURCE_IMPLEMENTED_PUBLICATION_PORT_MERGED_PHYSICAL_QUALIFICATION_PENDING
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
CURRENT_PHYSICAL_BACKEND_PROFILE=GITHUB_FIRST_V1
```

## Назначение

Документ reconciles D8/D9 authority, storage и publication semantics до дальнейшей physical deployment qualification. Canonical Publication Port source уже реализован, квалифицирован и merged; это не активирует D8/D9, не меняет active D6 route и не разворачивает новый backend.

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

## 5. Resolver/publication gap status

Merged local forwarder умеет создавать:

```text
<warm_root>/d8-origin/fixed-grid|sampled-schedule/<series-token>/YYYY/MM/DD.json
```

Arbitrary local/VPS paths по-прежнему не являются resolver authority. Source-level canonical publication/control-plane gap, выявленный до PR #118, закрыт merged Canonical Publication Port: current GITHUB_FIRST_V1 adapter публикует deterministic PublicationBatch, выполняет remote durability/read-back и связывает результат с existing capability/resolver/reader family.

```text
D8_ORIGIN_LOCAL_FORWARDER=SOURCE_IMPLEMENTED
D8_ORIGIN_CANONICAL_PUBLICATION=SOURCE_IMPLEMENTED_QUALIFIED_MERGED
D8_ORIGIN_RESOLVER_AUTHORITY=RECONCILED_CONTRACT_NOT_PHYSICALLY_QUALIFIED
REAL_D8_VPS_RUNTIME_PUBLICATION=NOT_YET_QUALIFIED
```

Запрещённые fixes остаются прежними: direct server path reader, second resolver, second reader, agent-visible filesystem locator, manual `d8-origin` stitching.

Canonical transition:

```text
D8 batch
→ canonical backend publication
→ backend/control-plane metadata
→ existing capability/resolver-visible authority
→ canonical ResolutionPlan
→ existing reader
```

Repository/Actions source qualification этого перехода уже PASS. Реальный preserved D8 PENDING SPOOL → canonical WARM physical shadow proof остаётся отдельным gate.

## 6. PublicationBatch

Canonical schema: `schema/history-publication-batch-v1.schema.json`.

Batch identity storage-independent. Она связывает ordered observation membership, membership hash, aggregate payload hash и target `WARM`. Selected backend profile и publication attempt identity явно находятся вне logical batch identity.

Canonical JSON primitive остаётся repository-owned `src/canonical_json.py`:

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

```text
PUBLICATION_PORT_STATUS=SOURCE_IMPLEMENTED_QUALIFIED_MERGED
SOURCE_QUALIFICATION_RUN=32318193771
NEXT_SOURCE_TASK=NONE_SOURCE_IMPLEMENTATION_COMPLETE
NEXT_REQUIRED_STAGE=PHYSICAL_SHADOW_QUALIFICATION
```

Qualification доказала bounded batching, already-present retry, crash-after-remote-before-ACK recovery, CAS generated-drift retry, conflict/no-overwrite, remote durability/read-back, exact membership/payload/integrity binding, control-plane/resolver visibility, existing-reader materialization и whole-batch canonical ACK. Test-only additional series прошла тот же Publication Port → capability index → existing resolver → ResolutionPlan → existing reader path без второго subsystem.

Текущая horizontal proof boundary:

```text
D8_CAPABILITY_ROUTING_HORIZONTAL_EXTENSIBILITY=PASS
D8_DUE_POLICY_DECLARATION_DERIVATION=PASS
FORWARDER_DECLARATION_DRIVEN_ROUTING=PASS
PUBLICATION_BATCH_BACKEND_ORTHOGONALITY=PASS
NEW_INSTRUMENT_SUPPORTED_FAMILY_ROUTING=PASS
NEW_METRIC_EXISTING_LIFECYCLE_ROUTING=PASS
END_TO_END_NEW_SERIES_PUBLICATION_RESOLVER_READER_EXTENSIBILITY=PASS_SOURCE_QUALIFICATION
```

Source acceptance после PR #118:

```text
NEW_SERIES_END_TO_END_REQUIRES_SECOND_RESOLVER=NO
NEW_SERIES_END_TO_END_REQUIRES_SECOND_READER=NO
NEW_SERIES_END_TO_END_REQUIRES_NEW_HISTORY_SUBSYSTEM=NO
NEW_SERIES_END_TO_END_REQUIRES_NEW_PUBLICATION_PROTOCOL=NO
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

Source qualification доказала эти semantics на repository-owned GITHUB_FIRST_V1 remote proof. Она не доказывает production execution из реального VPS runtime/PENDING SPOOL.

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
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
D9_REAL_D8_RUNTIME_TO_CANONICAL_WARM=PHYSICAL_QUALIFICATION_PENDING
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=NOT_QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVATION=PENDING
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
```

Source implementation, repository/Actions source qualification, real runtime physical qualification и activation — разные оси.

## 13. Server boundary

Server snapshot подтверждает D8 persistent SQLite operational volume и не требует permanent D9 WARM semantic volume.

```text
PERMANENT_VPS_D9_WARM_REQUIRED=NO
VPS_IS_MARKET_DATA_AUTHORITY=false
EXISTING_SERVER_POSTGRES_REUSE_DECISION=NOT_MADE
```

Эта source/status task не изменяет `CORE/ai-revenue-lab` и не выполняет VPS commands/deployment.

Следующий physical proof должен использовать preserved real PENDING SPOOL в отдельном owner-authorized `VPS_SHADOW` qualification. Он обязан доказать реальный D8 runtime → canonical backend publication → independent remote verification → resolver/reader visibility → ACK → `PENDING→FORWARDED` без reset/reseed/clear SPOOL. Source Publication Port при этом уже реализован и не требует повторной реализации или remote source requalification.
