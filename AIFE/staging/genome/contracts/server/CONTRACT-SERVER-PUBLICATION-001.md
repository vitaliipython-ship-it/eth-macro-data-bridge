---
id: CONTRACT-SERVER-PUBLICATION-001
domain: SERVER
title: "CONTRACT-SERVER-PUBLICATION-001: Durable Publication and ACK Contract"
version: "0.3.0"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2027-02-23
category: standards
doc_type: contract
language: ru
tags: [contract, server, publication, readback, registration, ack, idempotency]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md

---

# CONTRACT-SERVER-PUBLICATION-001: Durable Publication and ACK Contract

## 1. Purpose

Зафиксировать единственный generic publication lifecycle от validated domain input до durable read-back, canonical registration и ACK, не приравнивая physical write к публикации или domain truth.

## 2. Scope

Контракт связывает producer/domain input, durable ingest, staging, physical storage, independent read-back, canonical registration, identity match и ACK.

Вне scope: domain validation rules, backend vendor, transport protocol и provider semantics.

```text
ACK_BEFORE_DURABLE_READBACK=NO
PHYSICAL_WRITE_EQUALS_PUBLICATION=NO
PUBLICATION_EQUALS_DOMAIN_TRUTH=NO
```

## 3. Core Rules

Единственный lifecycle:

```text
VALIDATED_DOMAIN_INPUT
→ INGEST_DURABLE
→ STAGED
→ PUBLISHING
→ DURABLE_STORED
→ INDEPENDENT_READBACK_VERIFIED
→ CANONICALLY_REGISTERED
→ ACKED
```

ACK разрешён только при conjunction:

```text
DURABLE_STORED
+ INDEPENDENT_READBACK_VERIFIED
+ CANONICALLY_REGISTERED
+ IDENTITY_MATCH
```

Publication identity должна быть stable/idempotent across retry. Registration не заменяет read-back; read-back не заменяет registration.

## 4. Authority Model

- Domain/producer владеет validity и semantic identity входа.
- Publication contract владеет generic lifecycle progression и ACK eligibility.
- Storage contract владеет physical capability boundaries и stored-object/readback evidence.
- Canonical registry/index owner владеет registration mapping.
- Access contract читает accepted publication, но не меняет publication state.

## 5. Naming Contract

`PUBLICATION_ID` и `STORED_OBJECT_IDENTITY` должны иметь stable correlation с domain input identity и source revision. Retry использует тот же canonical publication identity, если semantic input identity не изменилась.

## 6. Placement Contract

```text
genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
```

Future source projection: `server/publication/**` после F3.

## 7. Agent Rules

1. Никогда не ACK сразу после write call.
2. Independent read-back должен идти через accepted read capability, а не только writer memory/result.
3. При retry сначала reconcile existing stored/registered identity.
4. Registration failure после successful storage остаётся незавершённой publication, а не ACK.
5. ACK failure после registration разрешает idempotent ACK retry без duplicate canonical registration.

## 8. Acceptance Criteria

- все восемь lifecycle states различимы;
- ACK gate реализует полный conjunction;
- read-back проверяет identity/content sufficient for accepted publication;
- interrupted publication restart-safe;
- retry не создаёт false duplicate canonical identity;
- domain semantics остаются у producer/domain authority.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| ACK conjunction | Contract/integration test | publication state-machine tests | Server/Data owner | every implementation change |
| Independent read-back | Integration test | writer-independent read path | Server/Data owner | qualification |
| Idempotent retry | Recovery test | interruption at each state | Server/Data owner | qualification |
| Domain authority preserved | Architecture review | semantic boundary | Architecture Lead | checkpoint |

## 10. Failure, restart and idempotency semantics

| Failure point | Required generic result |
| --- | --- |
| storage write succeeds, registration fails | remain before `CANONICALLY_REGISTERED`; retry/reconcile registration without duplicate object identity |
| registration succeeds, ACK fails | preserve registration; retry ACK idempotently |
| read-back mismatch | do not register/ACK; expose mismatch evidence and terminal/retry policy decision |
| process restart during publication | resume/reconcile from durable state and identities, not process memory |
| duplicate publication delivery | collapse against publication/idempotency identity |

```text
RESTART_SEMANTICS_DEFINED=YES
FAILURE_SEMANTICS_DEFINED=YES
IDEMPOTENCY_MODEL_DEFINED=YES
```

## 11. F5R generation publication binding

F5R уточняет publication identity без создания второй state machine. Publication должна
связать exact generation/manifest и применимые work/execution authorities:

```text
PUBLICATION_IDENTITY
IDEMPOTENCY_KEY_OR_IDENTITY
WORK_ID_IF_APPLICABLE
ATTEMPT_ID_IF_APPLICABLE
CURRENT_FENCING_AUTHORITY_IF_APPLICABLE
MANIFEST_IDENTITY
CURRENT_GENERATION_REFERENCE
DURABLE_WRITE_EVIDENCE
SEAL_EVIDENCE
INDEPENDENT_READBACK_EVIDENCE
REGISTRATION_EVIDENCE
ACK_EVIDENCE
```

Нормативный порядок сохраняется:

```text
DURABLE_WRITE
→ SEAL
→ INDEPENDENT_READBACK
→ TRANSACTIONAL_CURRENT_GENERATION_REGISTRATION
→ ACK
```

ACK до durable write/readback/registration запрещён. Stale attempt/fence не может изменить
current generation или подтвердить authority-bearing terminal publication effect.

## 12. Same-target content conflict semantics

Canonical publication outcome is determined from the stable logical publication target and
storage-owned content/collision evidence. Equivalent content may collapse idempotently;
content disagreement for the same logical target is a conflict, never a replacement policy.

```text
SAME_LOGICAL_TARGET+SAME_CONTENT=IDEMPOTENT_RETRY_OR_COLLAPSE
SAME_LOGICAL_TARGET+DIFFERENT_CONTENT=FAIL_CLOSED_CONFLICT
SILENT_OVERWRITE_ON_CONTENT_CONFLICT=FORBIDDEN
STALE_FENCED_EXECUTION_CAN_PUBLISH=NO
```

A fail-closed conflict must remain non-ACKed and expose conflict evidence. Publication does
not reinterpret domain content, and a valid current execution fence remains required for
any authority-bearing current-generation change.
