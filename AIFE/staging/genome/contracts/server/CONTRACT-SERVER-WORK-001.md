---
id: CONTRACT-SERVER-WORK-001
domain: SERVER
title: "CONTRACT-SERVER-WORK-001: Generic Durable Work Contract"
version: "0.1.0"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
review_cycle_days: 180
next_review_due: 2027-02-22
category: standards
doc_type: contract
language: ru
tags: [contract, server, work, identity, lifecycle, idempotency]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
  - genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md

---

# CONTRACT-SERVER-WORK-001: Generic Durable Work Contract

## 1. Purpose

Зафиксировать generic durable work identity/state boundary, которую будущий AIFE Server может реализовать без присвоения доменной семантики payload, расписания или результата.

Целевая связь:

```text
DOMAIN_OR_GENERIC_REQUEST
→ STABLE_WORK_IDENTITY
→ DURABLE_WORK_STATE
→ EXECUTION_OWNERSHIP
→ TERMINAL_RESULT_REFERENCE
```

## 2. Scope

Контракт применяется к устойчивой идентичности и lifecycle generic work unit, передаваемой между scheduling, execution и publication mechanisms.

В scope входят `WORK_ID`, generic `WORK_TYPE`, `PAYLOAD_REFERENCE`, `CREATED_AT`, `STATE`, `ATTEMPT`, `OWNER/CLAIM_REFERENCE`, `IDEMPOTENCY_IDENTITY`, `PROVENANCE` и `TERMINAL_RESULT_REFERENCE`.

Не входят provider/domain payload semantics, ETH identities, normalization, finality, gap/revision rules, domain due policy и физическая схема хранения.

```text
PROCESS_MEMORY_IS_DURABLE_WORK_SSOT=NO
DOMAIN_PAYLOAD_SEMANTICS_OWNED_BY_SERVER=NO
```

## 3. Core Rules

Cardinality: один логический `WORK_ID` имеет одну текущую durable lifecycle projection и может иметь N execution attempts.

Минимальный lifecycle:

```text
PENDING
→ READY
→ CLAIMED
→ RUNNING
→ SUCCEEDED
   | FAILED
   | CANCELLED
```

Допустимые расширения состояния обязаны сохранять различие между логической работой и попыткой. Retry не создаёт новый logical work identity, если owner policy явно не определяет новый work.

Required fields:

| Field | Contract meaning |
| --- | --- |
| `WORK_ID` | стабильная identity логической работы |
| `WORK_TYPE` | generic bounded classification, не domain payload meaning |
| `PAYLOAD_REFERENCE` | ссылка/identity входа, а не обязательный inline payload |
| `CREATED_AT` | timezone-aware creation instant |
| `STATE` | текущая durable lifecycle state |
| `ATTEMPT` | монотонная identity попытки для той же logical work |
| `OWNER/CLAIM_REFERENCE` | ссылка на текущую execution ownership projection, если claim существует |
| `IDEMPOTENCY_IDENTITY` | ключ collapsing повторной доставки/повтора, где операция требует exactly-once-like effect |
| `PROVENANCE` | источник создания work и policy/revision references |
| `TERMINAL_RESULT_REFERENCE` | identity результата или terminal evidence, не domain reinterpretation |

## 4. Authority Model

- Work contract владеет generic identity/state shape.
- Scheduling владеет due computation и materialization trigger, но после materialization не владеет execution state.
- Execution владеет claim/lease/fence и попыткой исполнения.
- Domain владеет meaning payload, policy и semantic validity.
- Durable repository implementation хранит state, но не определяет его meaning вне этого contract suite.

Conflict precedence: exact accepted work identity/state contract → accepted scheduling/execution contracts → implementation projection. Domain semantics имеют precedence над generic interpretation payload.

## 5. Naming Contract

`WORK_ID` должен быть deterministic либо owner-issued и stable. Рекомендуемые identity inputs ограничены generic tuple:

```text
domain + capability + work_type + subject_partition + due_slot_or_request_identity + policy_revision_identity
```

Node id, process id и worker id не являются logical `WORK_ID`.

## 6. Placement Contract

Canonical owner artifact:

```text
genome/contracts/server/CONTRACT-SERVER-WORK-001.md
```

Будущая runtime projection относится к `server/work/**`, но F2 не создаёт этот root.

## 7. Agent Rules

1. Переиспользовать существующий `WORK_ID` для retry той же logical work.
2. Не хранить единственный authoritative work state только в process memory.
3. Не трактовать generic `WORK_TYPE` как право сервера определить domain semantics.
4. Не terminalize work без действующего execution authority, если работа claim/lease-governed.
5. Все state transitions должны оставлять provenance и attempt identity.

## 8. Acceptance Criteria

- все required fields представлены в implementation model либо явно derived;
- `PENDING/READY/CLAIMED/RUNNING/SUCCEEDED/FAILED/CANCELLED` различимы;
- retry сохраняет logical identity по умолчанию;
- terminal result имеет stable reference;
- process restart не стирает accepted work state;
- domain payload semantics не перенесены в SERVER authority.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| Stable logical work identity | Contract test | identity/state transition tests | Server/Data owner | every implementation change |
| Durable state outside process memory | Integration test | restart/read-back proof | Server/Data owner | qualification |
| Retry preserves identity | Contract test | duplicate/retry scenarios | Server/Data owner | every implementation change |
| Domain semantics remain external | Architecture review | authority-boundary review | Architecture Lead | checkpoint |

## 10. Failure, restart and idempotency semantics

- worker crash: durable work remains recoverable; active ownership follows execution lease expiry/reclaim contract;
- control restart: accepted work identities/states remain readable; restart does not mint replacement work by default;
- duplicate delivery: compare `WORK_ID`/`IDEMPOTENCY_IDENTITY`; do not infer new logical work from transport duplication;
- retry: increments/changes attempt identity, not logical work identity by default;
- terminal write interrupted: resulting state is reconciled from durable evidence before another terminal effect is accepted.

```text
RESTART_SEMANTICS_DEFINED=YES
IDEMPOTENCY_MODEL_DEFINED=YES
```
