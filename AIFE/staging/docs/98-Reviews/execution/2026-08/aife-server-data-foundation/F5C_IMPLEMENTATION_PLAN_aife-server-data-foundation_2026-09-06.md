---
id: AIFE-F5C-IMPLEMENTATION-PLAN-2026-09-06
title: "F5C: D6/D8/D9 reconciliation, durable acceptance and direct-WIP implementation contract"
version: '1.0'
status: frozen-preimplementation
owner: Architecture Lead
created: 2026-09-06
updated: 2026-09-06
category: architecture
doc_type: implementation-plan
language: ru
tags: [aife, server, f5c, acquisition, durability, d6, d8, d9, shadow]
---

# F5C — frozen preimplementation contract

## 1. Authority

```text
TASK_ID=AIFE-F5C-D6-D8-D9-RECONCILIATION-DURABLE-BOUNDARY-IMPLEMENTATION-PLANNING-R01
PREDECESSOR_HEAD=f086521e6fee3febe301029c5a18aee79786ba8b
PREDECESSOR_TREE=2d94cc53e85caf9e0d297888bcaaeff312318352
PROGRAM_MAP_VERSION=0.8

ACTIVE_SERVER_ENGINEERING_REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
ACTIVE_SERVER_ENGINEERING_BRANCH=agent/aife/server-data-foundation-wip
SEPARATE_AIFE_SERVER_REPOSITORY_REQUIRED_NOW=NO
INTERMEDIATE_SERVER_REPOSITORY_MIGRATION_REQUIRED_NOW=NO
F5_REIMPLEMENTATION_REQUIRED=NO
F5C_RUNTIME_IMPLEMENTATION_STARTED=NO
```

Этот документ является bounded implementation contract для следующей прямой F5C WIP-реализации.
Program Map 0.8 остаётся architecture authority; этот план не меняет production authority.

## 2. Physical source inventory

### F5 generic Server

| Механизм | Exact path / symbol | Фактическая роль |
| --- | --- | --- |
| Domain envelope | `AIFE/staging/server/integration/domain.py::DomainArtifactEnvelope` | domain-accepted metadata/reference boundary |
| F4/F5 binding | `AIFE/staging/server/integration/bindings.py::F5IncomingArtifactLifecycle` | Work→Attempt→Publication→Storage→Readback orchestration |
| Work/Attempt | `AIFE/staging/server/work/models.py` | generic stable Work/Attempt identities |
| Durable control | `AIFE/staging/core/data/adapters/sqlite_control.py::SQLiteServerControlRepository` | SQLite/WAL Work/Attempt/Publication/Generation state, claim/lease/fencing |
| Immutable storage | `AIFE/staging/server/storage/filesystem.py::QualifiedDataRootImmutableFilesystem` | content-addressed immutable write, file fsync, directory fsync, independent readback |
| Publication | `AIFE/staging/server/application/services.py::F5BoundedPublicationCoordinator` | generic publication lifecycle and registration |
| Runtime composition | `AIFE/staging/server/runtime/composition.py::ServerRuntimeDependencies` | generic dependency composition |
| Recovery | `AIFE/staging/server/runtime/recovery.py` | bounded restart/recovery behavior |
| Readiness | `AIFE/staging/server/runtime/readiness.py::evaluate_f5_readiness` | deployment-map/control/data-root/write-readback readiness |
| Deployment acceptance | `AIFE/staging/tests/integration/server/test_f5_permissions_and_deployment.py` | deployment identity/config/schema/backing fail-closed checks |

Existing F5 tests already separately cover contract flow, Data Bridge boundary, SQLite control,
publication integrity/recovery, backup/restore, permissions/deployment and vertical slice.

### D6

| Mechanism | Path | Disposition |
| --- | --- | --- |
| semantic capability/domain resolution | `tools/capability_index.py` | `RETAIN_AS_DOMAIN_OR_PROVIDER_ADAPTER` |
| exact physical materialization/integrity from already-resolved plan | `tools/history_access.py` | `GENERALIZE` behind AIFE Access/Storage |
| consumer wrapper | `tools/history_consumer.py` | `LEGACY_COMPATIBILITY_ONLY` until canonical consumer parity |

AIFE generic Access must consume an already domain-resolved identity/plan. It must not own market
revision/finality/gap/provider selection semantics.

### D8

| Mechanism | Path / symbol | Disposition |
| --- | --- | --- |
| provider acquisition family | `src/acquisition_core.py::CanonicalAcquisitionCore` | `RETAIN_AS_DOMAIN_OR_PROVIDER_ADAPTER` |
| Data Bridge→AIFE envelope adapter | `src/aife_server_adapter.py` | `REUSE_AS_IS_WITH_BOUNDED_EXTENSION` |
| observation normalization/identity | current logic in `src/d8_runtime.py::_normalize_observations` | `GENERALIZE` into one Data Bridge-owned reusable normalizer |
| D8 cycle/lease/spool runtime | `src/d8_runtime.py::D8Runtime` / `D8State` | `LEGACY_COMPATIBILITY_ONLY` during F5C shadow; generic runtime parts superseded by AIFE |
| SQLite PENDING/FORWARDED spool | `src/d8_runtime.py::D8State.checkpoint_capability/mark_forwarded` | `SUPERSEDE_BY_EXISTING_AIFE_MECHANISM` after C2+C5 proof |
| provider/domain due semantics | `contracts/d8-runtime-candidate.json` + Data Bridge policy | `RETAIN_AS_DOMAIN_OR_PROVIDER_ADAPTER` |
| GitHub WARM forwarding | `tools/publication_control_v2.py` + D8/D9 forwarder family | `RETAIN_AS_EXPORT_ADAPTER` |

D8 whole-runtime copy into AIFE Server Core is forbidden.

### D9

| Mechanism | Path | Disposition |
| --- | --- | --- |
| generation eligibility/completeness/finality | `tools/deep_history/history_sealer.py` and domain contracts | `RETAIN_AS_DOMAIN_OR_PROVIDER_ADAPTER` |
| generic immutable publication/readback/idempotency semantics | existing D9 publication behavior | `SUPERSEDE_BY_EXISTING_AIFE_MECHANISM` using F5 Publication/Storage |
| GitHub-specific WARM/COLD publication | `tools/publication_control_v2.py`, sealer/workflow | `RETAIN_AS_EXPORT_ADAPTER` |
| legacy GitHub history route | current D6/D9 route | `LEGACY_COMPATIBILITY_ONLY`, retirement only after F5M/F6/F7/F8 proof |

```text
D6_RECONCILIATION=PASS
D8_RECONCILIATION=PASS_WITH_PARTIAL_LIVE_VPS_PROVENANCE
D9_RECONCILIATION=PASS
D6_IS_AIFE_PLATFORM_PRIMITIVE=NO
D8_IS_AIFE_PLATFORM_PRIMITIVE=NO
D9_IS_AIFE_PLATFORM_PRIMITIVE=NO
```

## 3. D8 VPS provenance

Repository authority proves accepted physical A1/A2 evidence, including 20 observations,
canonical publication/readback, ACK, `PENDING→FORWARDED` and idempotent replay. The reconciled
status explicitly states that it is not a continuous live VPS probe and requires fresh server
readback before future physical mutation/qualification.

Historical handoff binds `RUNTIME_SOURCE_COMMIT=0284e485369ecda9281b8d505a3a0968b4baa701`
but marks it `SOURCE_CANDIDATE_NOT_DEPLOYED`. The current execution environment has no live VPS
readback channel, therefore current deployed source/image/config equivalence is not asserted.

```text
D8_VPS_PROVENANCE_STATUS=PARTIAL
D8_LIVE_READBACK_REQUIRED_BEFORE_C8=YES
D8_LIVE_READBACK_REQUIRED_BEFORE_C9=YES
CURRENT_GITHUB_D8_EQUALS_CURRENT_LIVE_VPS_D8_BY_DEFAULT=NO
```

This does not block C1–C7 because their source contract does not depend on claiming current VPS
byte equivalence. C8 must fail closed without fresh VPS provenance.

## 4. First durable acceptance

### Current gap

Current F5 Work persists `payload_reference`, not provider-result bytes. Therefore:

```text
PROVIDER_RESPONSE_RECEIVED_IS_DURABLE_ACCEPTANCE=NO
CURRENT_WORK_ACCEPTED_IS_PROVIDER_BYTES_DURABLE=NO
PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=CURRENTLY_OPEN_BOUNDED
```

### Frozen F5C boundary

Do not add a second spool/ledger. Reuse the existing immutable object store plus existing durable
Work repository.

```text
provider/source
→ Data Bridge provider/domain acquisition
→ normalization + validation
→ canonical accepted payload bytes
→ QualifiedDataRootImmutableFilesystem.write_immutable(
     payload,
     expected_digest=envelope.content_identity
   )
→ fsync(file)
→ atomic create-if-absent
→ fsync(directory)
→ independent readback/hash/size verification
→ SQLiteServerControlRepository.accept_work(
     ...,
     payload_reference=<deterministic immutable object reference>
   )
→ COMMIT
→ AIFE_DURABLY_ACCEPTED
→ READY/CLAIM/ATTEMPT
→ Publication
→ canonical registration/access/readback
```

The boundary is composite and becomes true only after BOTH the independently verified immutable
object and the durable Work binding exist.

```text
FIRST_DURABLE_ACCEPTANCE_BOUNDARY=
IMMUTABLE_OBJECT_DURABLE_READBACK_PLUS_DURABLE_WORK_BINDING_COMMIT

DURABLE_STATE_LOCATION=
CANONICAL_DATA_ROOT/objects + CANONICAL_CONTROL_DB_PATH

WRITE_OPERATION=
QualifiedDataRootImmutableFilesystem.write_immutable
+
SQLiteServerControlRepository.accept_work

COMMIT_FSYNC_SEMANTICS=
FILE_FSYNC+ATOMIC_CREATE+DIRECTORY_FSYNC+INDEPENDENT_READBACK
+
SQLITE_TRANSACTION_COMMIT_WAL

IDENTITY_KEY=
DomainArtifactEnvelope.content_identity
+
F5WorkIdentityInputs.logical_input_identity/work_id

REPLAY_SEMANTICS=
same payload digest -> immutable object idempotent readback;
same logical input tuple -> existing Work returned

DEDUPE_SEMANTICS=
content digest + stable logical input identity

FAILURE_BEFORE_BOUNDARY=
not accepted; no success/ACK may escape; retry same logical acquisition

FAILURE_AFTER_OBJECT_BEFORE_WORK=
object may be orphaned but is not accepted; retry is object-idempotent and must bind Work before success

FAILURE_AFTER_BOUNDARY=
accepted Work and exact bytes survive process/container/service restart

RECOVERY_ENTRYPOINT=
replay same logical acquisition/work identity through normal F5C acquisition service;
existing Work/Attempt recovery remains canonical

TARGET_PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=CLOSED_AT_F5C_ACCEPTANCE_BOUNDARY
```

No new `ingress_ledger`, queue, spool or storage authority is justified.

```text
D8_SPOOL_DISPOSITION=
SUPERSEDED_BY_EXISTING_AIFE_DURABLE_LIFECYCLE_AFTER_C2_C5_PROOF
```

Legacy D8 spool remains untouched until that proof; it is not deleted by C1–C5.

## 5. Generic Server / domain boundary

AIFE owns:
```text
GENERIC_COLLECTION_ACQUISITION_RUNTIME
GENERIC_EXECUTION
GENERIC_SCHEDULING
GENERIC_WORK_OWNERSHIP
GENERIC_DURABLE_RUNTIME_STATE
GENERIC_PUBLICATION_LIFECYCLE
GENERIC_STORAGE_LIFECYCLE
GENERIC_ACCESS_MECHANISMS
GENERIC_SERVER_OPERATIONS
```

Data Bridge/domain owns:
```text
PROVIDER_ENDPOINTS_AND_AUTH
MARKET_DATA_SEMANTICS
PROVIDER_SEMANTICS
DOMAIN_IDENTITIES
NORMALIZATION
VALIDATION
FINALITY
GAP_REVISION_RULES
DOMAIN_RESOLUTION_RULES
PROVIDER_SPECIFIC_PARSING
INSTRUMENT_SEMANTICS
DUE_POLICY_SEMANTICS
```

Generic Server acquisition accepts a protocol-level domain adapter result:
`DomainArtifactEnvelope + exact payload bytes`. No Binance/Kraken/Deribit/ETH branch is allowed
inside `AIFE/staging/server/**`.

```text
GENERIC_SERVER_DOMAIN_BOUNDARY=PASS
```

## 6. Second-source extensibility

Existing F5 core is provider-neutral, but a generic acquisition adapter protocol/runtime entrypoint
does not yet exist. Therefore current implementation requires an exact delta rather than claiming
a source-level PASS prematurely.

```text
SECOND_SOURCE_PROVIDER_EXTENSIBILITY=REQUIRES_EXACT_IMPLEMENTATION_DELTA
```

C1/C3/C5 must prove with two fake adapters/source identities that adding the second adapter does
not modify generic Work/Scheduling/Publication/Storage code or persistent schema.

## 7. Deployment reuse

No new deployment mechanism.

```text
DEPLOYMENT_REUSE_MODEL=PASS
IMMUTABLE_RELEASE_MODEL=YES
DIRECT_PRODUCTION_EXECUTION_FROM_GIT_CHECKOUT=NO
PRODUCTION_UPDATE_BY_GIT_PULL=NO
DEPLOYMENT_MAP_REQUIRED=YES
DEPLOYMENT_RECEIPT_REQUIRED=YES
ATOMIC_RELEASE_ACTIVATION=YES
```

C6–C8 path:
```text
exact current-WIP HEAD/TREE
→ materialize future-AIFE projection
→ immutable deployable release
→ deployment-map/config/state/storage binding
→ readiness
→ shadow activation
→ provider collection
→ durable acceptance
→ readback
→ restart/recovery
```

`test_f5_permissions_and_deployment.py` and `evaluate_f5_readiness()` are reused. Deployment source
is not changed in the frozen implementation path-set unless a physical C6 proof demonstrates a
coupled defect, in which case STOP rather than scope expansion.

## 8. Exact implementation path-set

The next implementation agent may mutate only these 12 paths:

| # | Path | Action | Purpose | Targeted proof |
| ---: | --- | --- | --- | --- |
| 1 | `AIFE/staging/server/acquisition/__init__.py` | ADD | export one generic acquisition boundary | import/API smoke |
| 2 | `AIFE/staging/server/acquisition/ports.py` | ADD | provider-neutral adapter protocol + acquired artifact result | two fake adapters |
| 3 | `AIFE/staging/server/acquisition/service.py` | ADD | generic acquisition orchestration + composite durable acceptance | failure-injection durability |
| 4 | `AIFE/staging/server/runtime/composition.py` | MODIFY | wire acquisition service into existing runtime dependencies | composition test |
| 5 | `AIFE/staging/server/integration/bindings.py` | MODIFY | reuse Work identity and bind durable object reference before ready/claim | exact Work/object binding |
| 6 | `src/d8_observation_normalizer.py` | ADD | single Data Bridge-owned pure D8 observation normalization seam | legacy/F5C parity |
| 7 | `src/d8_runtime.py` | MODIFY | delegate normalization to the shared domain normalizer; preserve legacy runtime behavior | existing D8 tests unchanged |
| 8 | `src/aife_server_adapter.py` | MODIFY | expose canonical payload bytes matching `content_identity` together with neutral envelope | byte/digest equality |
| 9 | `src/aife_f5c_acquisition_adapter.py` | ADD | Data Bridge provider/domain adapter using existing `CanonicalAcquisitionCore` without D8 spool ownership | bounded Binance Spot M5 adapter proof |
| 10 | `AIFE/staging/tests/integration/server/test_f5c_acquisition_durable_acceptance.py` | ADD | crash/replay/object/Work/restart acceptance proof | C2/C5 |
| 11 | `AIFE/staging/tests/integration/server/test_f5c_acquisition_extensibility.py` | ADD | two-source provider-neutral core proof | C1/C3 |
| 12 | `tests/d8/test_f5c_aife_acquisition_bridge.py` | ADD | Data Bridge normalizer/adapter parity and no legacy D8 regression | C3 |

```text
EXACT_IMPLEMENTATION_PATH_COUNT=12
```

No deployment script, SQLite schema, Storage port, Publication state machine, Scheduler contract,
D6 resolver, D9 sealer or GitHub publisher is in the mutation set. They are reused or remain
domain/export compatibility mechanisms.

If a materially coupled need outside the 12 paths is proven:
```text
STOP_CODE=F5C_ADDITIONAL_OUT_OF_SCOPE_COUPLED_INVARIANT_PROVEN
```

## 9. Initial real provider slice

The first shadow qualification is bounded to the existing Data Bridge acquisition family and
must not broaden generic Server semantics. The initial real source is the existing
`binance-spot.m5` capability produced by `CanonicalAcquisitionCore`; it may yield its current
domain-defined member set. Generic AIFE code sees only adapter results.

This does not activate production authority and does not change provider policy.

## 10. Checkpoints

### C1 — generic acquisition boundary
- ENTRY: F5 source qualified, no generic acquisition protocol.
- MUTATION: paths 1–4, 11.
- PASS: protocol is provider/domain-neutral; two fake adapters run without core rewrite.
- STOP: provider/ETH conditional enters Server Core.
- NEXT: C2.

### C2 — first durable acceptance
- ENTRY: C1 PASS.
- MUTATION: paths 3, 5, 10.
- PASS: object durable readback precedes Work commit; no success before both; crash injection proves no accepted Work can reference missing bytes.
- STOP: second spool/ledger appears necessary without physical proof.
- NEXT: C3.

### C3 — Data Bridge provider/domain adapter binding
- ENTRY: C2 PASS.
- MUTATION: paths 6–9, 12.
- PASS: D8 normalization has one implementation; legacy D8 behavior preserved; F5C adapter emits envelope+exact canonical bytes; no D8 spool ownership in generic AIFE.
- STOP: domain semantics must move into Server Core.
- NEXT: C4.

### C4 — Publication/Storage/Access reuse
- ENTRY: C3 PASS.
- MUTATION: only already-listed paths 3/5/10 if needed.
- PASS: accepted object proceeds through existing Publication/Storage/Generation/Access path; exact readback matches accepted bytes; no new publisher.
- STOP: existing F5 contract conflict.
- NEXT: C5.

### C5 — restart/replay/idempotency
- ENTRY: C4 PASS.
- MUTATION: paths 3/5/10/11/12 only.
- PASS: restart after durable boundary recovers without provider-result loss; same logical delivery collapses; stale claim/fencing remains fail-closed.
- STOP: durable acceptance requires new parallel authority.
- NEXT: C6.

### C6 — exact Git-bound deployable materialization
- ENTRY: C5 PASS and clean exact WIP HEAD/TREE.
- MUTATION: NONE by default.
- PASS: existing deployment contract/readiness can materialize exact future-AIFE paths into immutable release with deployment receipt/binding.
- STOP: `F5C_ADDITIONAL_OUT_OF_SCOPE_COUPLED_INVARIANT_PROVEN` if deployment code repair is physically required.
- NEXT: C7.

### C7 — Docker qualification
- ENTRY: C6 PASS.
- MUTATION: NONE unless a defect is within frozen 12-path scope.
- PASS: build/run, durable acceptance, readback, restart/replay, two-source generic proof.
- STOP: source defect outside frozen path-set or semantic boundary break.
- NEXT: C8.

### C8 — shadow-server deployment
- ENTRY: C7 PASS + fresh VPS D8/deployment provenance readback.
- MUTATION: server deployment only under separately permitted execution task; no repository scope expansion.
- PASS: exact Git-bound immutable release, health/readiness, isolated shadow, legacy authority unchanged.
- STOP: missing live provenance or deployment drift.
- NEXT: C9.

### C9 — real provider forward collection
- ENTRY: C8 PASS.
- MUTATION: runtime state only under separately permitted execution task.
- PASS: real `binance-spot.m5` adapter result reaches composite durable acceptance, existing publication/access, independent readback; no production authority.
- STOP: data loss/duplicate/identity/domain-coupling defect.
- NEXT: C10.

### C10 — bounded stability
- ENTRY: C9 PASS.
- MUTATION: runtime state/evidence only under separately permitted execution task.
- PASS: bounded repeated slots, restart/recovery, idempotency, resource/backpressure observations, no legacy authority change.
- STOP: instability or hidden coupling.
- NEXT: `F5C_FORWARD_COLLECTION_QUALIFIED`.

```text
IMPLEMENTATION_CHECKPOINT_COUNT=10
```

## 11. Three-question gate

```text
MECHANISM=NEW_D8_STYLE_SPOOL
REAL_RISK=provider-result loss before durable AIFE acceptance
SIMPLER_OPTION=YES_EXISTING_IMMUTABLE_OBJECT_STORE_PLUS_DURABLE_WORK_BINDING
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=DO_NOT_ADD

MECHANISM=NEW_RUNTIME_SCHEDULER
REAL_RISK=NONE_EXISTING_AIFE_SCHEDULING_WORK_BOUNDARY_ALREADY_EXISTS
SIMPLER_OPTION=REUSE_EXISTING
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=DO_NOT_ADD

MECHANISM=NEW_PUBLICATION_MECHANISM
REAL_RISK=NONE_EXISTING_F5_PUBLICATION_STORAGE_READBACK_ALREADY_QUALIFIED
SIMPLER_OPTION=REUSE_EXISTING
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=DO_NOT_ADD

MECHANISM=NEW_DEPLOYMENT_MECHANISM
REAL_RISK=NONE_PROVEN
SIMPLER_OPTION=REUSE_EXISTING_DEPLOYMENT_CONTRACT
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=DO_NOT_ADD

MECHANISM=GENERIC_ACQUISITION_PROTOCOL_AND_SERVICE
REAL_RISK=WITHOUT_IT_PROVIDER_EXECUTION_WOULD_COUPLE_GENERIC_SERVER_TO_DATA_BRIDGE_OR_D8_RUNTIME
SIMPLER_OPTION=NO_THIN_PROTOCOL_PLUS_SERVICE_IS_MINIMUM_NEUTRAL_SEAM
NEXT_AGENT_ACTION_COUNT=DECREASES
DECISION=ADD
```

## 12. Terminal planning state

```text
F5C_PREIMPLEMENTATION_PLANNING=PASS
D6_D8_D9_MECHANISM_RECONCILIATION=PASS_OR_BOUNDED_EXACT_GAPS
FIRST_DURABLE_ACCEPTANCE_CONTRACT=FROZEN
PROVIDER_TO_DURABLE_LOSS_WINDOW_MODEL=FROZEN
SERVER_DOMAIN_OWNERSHIP_BOUNDARY=FROZEN
DEPLOYMENT_AND_SHADOW_SERVER_ROUTE=FROZEN
EXACT_F5C_IMPLEMENTATION_PATH_SET=FROZEN
EXACT_F5C_CHECKPOINT_SEQUENCE=FROZEN

D8_VPS_PROVENANCE_STATUS=PARTIAL
CURRENT_PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=OPEN_BOUNDED
TARGET_PROVIDER_TO_DURABLE_STATE_LOSS_WINDOW=CLOSED_AT_F5C_ACCEPTANCE_BOUNDARY
D8_SPOOL_DISPOSITION=SUPERSEDED_AFTER_C2_C5_PROOF

CURRENT_WIP_BRANCH_REMAINS_ENGINEERING_CARRIER=YES
SEPARATE_AIFE_SERVER_REPOSITORY_REQUIRED_NOW=NO
F5_REIMPLEMENTATION_REQUIRED=NO
F5C_RUNTIME_IMPLEMENTATION_STARTED=NO
F5M_STARTED=NO
VPS_MUTATED=NO
SHADOW_SERVER_DEPLOYED=NO
PRODUCTION_CUTOVER=NO
CANONICAL_TOOLCHAIN_EXECUTED=NO
AEB_CREATED=NO

READY_FOR_F5C_DIRECT_WIP_IMPLEMENTATION=YES
NEXT_TASK=F5C_DIRECT_WIP_IMPLEMENTATION_C1_TO_C5_THEN_C6_C7_QUALIFICATION
```
