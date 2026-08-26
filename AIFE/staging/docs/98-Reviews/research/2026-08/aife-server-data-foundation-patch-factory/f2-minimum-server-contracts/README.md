---
title: "AIFE Server/Data Foundation — F2: minimum generic SERVER contracts"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
category: architecture
doc_type: report
language: ru
tags: [server, data, f2, contracts, scheduling, execution, publication, storage, access]
authority_reference:
  - ../../../../../../AGENTS.md
  - ../../../../../../genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - ../../../../../../genome/registries/CONTRACTS_REGISTRY.md
  - ../../../../../../genome/standards/arch/STD-ARCH-001.md
  - ../f1g-server-governance/README.md
related:
  - ../f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
---

# AIFE Server/Data Foundation — F2 minimum generic SERVER contracts

## 1. Authority и no-runtime boundary

```text
TASK_ID=AIFE-SERVER-DATA-PATCH-FACTORY-F2-MINIMUM-SERVER-CONTRACTS-R01
CHECKPOINT=CHECKPOINT_F2_MINIMUM_SERVER_ARTIFACT_CONTRACTS
PREDECESSOR_CHECKPOINT=CHECKPOINT_F1G_SERVER_GOVERNANCE
PREDECESSOR_WIP_HEAD=4e53b834ce3294b7ae1f7160a91aecd40e1d3c76
PREDECESSOR_WIP_TREE=241fad08a3e14fe60c46722f5a4c13c58b77cead
SERVER_ROOT_ADMITTED=YES
SERVER_DOMAIN_ADMITTED=YES
F1G_SERVER_ROOT_ADMISSION_GATE=PASS
SERVER_ROOT_MATERIALIZED=NO
SERVER_IMPLEMENTATION_STARTED=NO
DATABASE_VENDOR_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
```

F2 материализует только semantic contract layer. Он не создаёт `server/**`, tests,
worker/scheduler/storage adapters, database/API/deployment source или runtime configuration.
Контракты остаются `0.1.0 / draft` внутри WIP staging; accepted F2 checkpoint фиксирует их
как обязательный implementation input для следующей разработки, но не выдаёт их за уже
интегрированные owner artifacts canonical AIFE main.

## 2. Exact minimum contract suite

| Contract | Boundary |
| --- | --- |
| `CONTRACT-SERVER-WORK-001` | stable durable work identity/state, attempt, provenance, idempotency |
| `CONTRACT-SERVER-SCHEDULING-001` | schedule definition, due computation, deterministic materialization |
| `CONTRACT-SERVER-EXECUTION-001` | claim, lease, renewal, fencing, reclaim, terminal authority |
| `CONTRACT-SERVER-PUBLICATION-001` | durable publication, independent read-back, registration, ACK |
| `CONTRACT-SERVER-STORAGE-001` | backend-neutral physical storage lifecycle capabilities |
| `CONTRACT-SERVER-ACCESS-001` | generic request/result/provenance/partial-error boundary |

```text
MINIMUM_SERVER_CONTRACT_COUNT=6
EXTRA_SERVER_CONTRACT_COUNT=0
```

## 3. Cross-contract lifecycle

```text
SCHEDULE_DEFINITION
→ DUE_COMPUTATION
→ DUE_WORK_MATERIALIZATION
→ STABLE_WORK_IDENTITY
→ READY
→ CLAIM + LEASE + FENCING_TOKEN + ATTEMPT
→ RUNNING
→ VALIDATED_DOMAIN_INPUT_OR_GENERIC_ACCEPTED_INPUT
→ INGEST_DURABLE
→ STAGED
→ PUBLISHING
→ DURABLE_STORED
→ INDEPENDENT_READBACK_VERIFIED
→ CANONICALLY_REGISTERED
→ ACKED
→ ACCESS_REQUEST
→ ACCEPTED_RESULT + RESULT_IDENTITY + SOURCE_REVISION + PROVENANCE
```

Scheduling определяет generic due/materialization, но не execution ownership. Execution
fencing защищает durable terminal effects. Publication контролирует ACK gate. Storage
предоставляет physical capabilities без semantic authority. Access выдаёт accepted result,
не меняя domain truth/finality.

```text
CROSS_CONTRACT_CONSISTENCY=PASS
CONTRADICTORY_NORMATIVE_RULES=0
CYCLIC_AUTHORITY_OWNERSHIP=NO
```

## 4. State ownership matrix

| State / identity | Authoritative owner | Derived projection / boundary |
| --- | --- | --- |
| work identity | `CONTRACT-SERVER-WORK-001` durable work record | scheduler/execution carry `WORK_ID` only |
| work lifecycle state | `CONTRACT-SERVER-WORK-001` | execution event may request transition; accepted durable state is owner |
| schedule definition record | `CONTRACT-SERVER-SCHEDULING-001` | domain policy payload/reference remains domain authority |
| next due identity | `CONTRACT-SERVER-SCHEDULING-001` | materialized work references it; execution does not recompute it |
| claim | `CONTRACT-SERVER-EXECUTION-001` ownership record | work state `CLAIMED` is derived from accepted claim transition |
| lease | `CONTRACT-SERVER-EXECUTION-001` | worker-local timer is not authority |
| fencing token | `CONTRACT-SERVER-EXECUTION-001` | consumers compare current token before durable terminal effect |
| attempt | `CONTRACT-SERVER-EXECUTION-001` | work keeps current/terminal attempt reference |
| publication state | `CONTRACT-SERVER-PUBLICATION-001` | storage/registry evidence gates transitions |
| stored object identity | `CONTRACT-SERVER-STORAGE-001` storage evidence | publication references identity but does not invent physical identity |
| canonical registration | designated canonical registration record under `CONTRACT-SERVER-PUBLICATION-001` | publication state `CANONICALLY_REGISTERED` is derived from verified registration evidence |
| ACK | `CONTRACT-SERVER-PUBLICATION-001` | allowed only after full ACK conjunction |
| access result identity | `CONTRACT-SERVER-ACCESS-001` | source revision/domain identity are referenced, not redefined |

```text
AMBIGUOUS_STATE_AUTHORITY_COUNT=0
```

## 5. Failure / restart semantics

| Scenario | Contract outcome |
| --- | --- |
| worker crash | lease expiry/reclaim enables new attempt/fence for same logical work |
| control restart | durable work/schedule/claim/publication state survives process loss |
| lease expiry | prior fence loses authority; stale worker cannot commit terminal effect |
| duplicate delivery | distinguish via work/publication idempotency identity; not automatically new work |
| retry | new attempt/eligibility timing for same work unless explicit policy creates new work |
| stale worker | local computation may finish, durable authority-bearing commit is rejected |
| publication interruption | reconcile durable publication state/identity before retry |
| storage succeeds, registration fails | remain pre-registration; retry registration without duplicate object identity |
| registration succeeds, ACK fails | preserve registration and retry ACK idempotently |
| read-back mismatch | no registration/ACK; expose mismatch evidence and policy decision |
| partial access failure | explicit partial/error result; never silently complete |

```text
RESTART_SEMANTICS_DEFINED=YES
FAILURE_SEMANTICS_DEFINED=YES
IDEMPOTENCY_MODEL_DEFINED=YES
FENCING_MODEL_DEFINED=YES
ONLY_CURRENT_FENCING_AUTHORITY_MAY_COMMIT_TERMINAL_EFFECT=YES
```

## 6. Authority split

```text
AIFE_SERVER_OWNS=
  GENERIC_WORK_MECHANISMS
  + GENERIC_SCHEDULING
  + GENERIC_EXECUTION_OWNERSHIP
  + GENERIC_PUBLICATION
  + GENERIC_STORAGE_LIFECYCLE
  + GENERIC_ACCESS_MECHANISMS

ETH_DATA_BRIDGE_OWNS=
  MARKET_DATA_SEMANTICS
  + PROVIDER_SEMANTICS
  + DOMAIN_IDENTITIES
  + NORMALIZATION
  + DOMAIN_VALIDATION
  + FINALITY
  + REVISION_GAP_RULES
  + DOMAIN_RESOLUTION_RULES

SERVER_DOMAIN_IS_ETH_SEMANTIC_AUTHORITY=NO
```

## 7. Registry / generated consequences

Fresh canonical generator discovery after six owner contracts and exact registry rows:

```text
CONTRACT_REGISTRATION_DISCOVERY=PASS
CONTRACTS_REGISTRY_CHANGED=YES
genome/contracts/server/server.json=REQUIRED_NEW_GENERATED_COMPANION
genome/registries/genome_registry.json=REQUIRED_MODIFIED_GENERATED_AGGREGATE
STANDARDS_REGISTRY_CHANGED=NO
OTHER_SEMANTIC_CATALOGS_CHANGED=NO
```

The generator reports eight live contracts and a new SERVER domain-bucket contract catalog.
No fake domain row, second registry or per-artifact JSON fleet is introduced.

## 8. Exact F2 operation map

```text
CONTRACT_PATH_COUNT=6
REGISTRY_PATH_COUNT=1
GENERATED_PATH_COUNT=3
CHECKPOINT_DOC_PATH_COUNT=1
CONTROL_PATH_COUNT=2
TOTAL_PATH_COUNT=13
UNRELATED_PATHS=NONE
```

The third derived path is `docs/10-Architecture/general/architecture-trees/project-control/genome-owner-layer-tree.md`, required by strict architecture-tree coverage once `genome/contracts/server/` exists.

Future-AIFE overlay contains the first eleven paths; the two Data Bridge control/evidence
files are not canonical overlay inputs.

## 9. Validation model

Canonical validation overlays all accumulated `AIFE/staging/**` onto the immutable AIFE
reference and checks metadata, naming/placement, required contract sections, registry and
references, generated sync, semantic catalogs, architecture boundaries, structural layout,
structural pressure, links and `git diff --check`.

Pre-existing corpus link debt is compared baseline-to-successor; only introduced broken links
may block F2.

## 10. Next boundary

```text
NEXT_CHECKPOINT=CHECKPOINT_F3_SERVER_SOURCE_SKELETON_AND_CORE_MECHANISMS
F3_STARTED=NO
SERVER_SOURCE_ROOT_MATERIALIZED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
```
