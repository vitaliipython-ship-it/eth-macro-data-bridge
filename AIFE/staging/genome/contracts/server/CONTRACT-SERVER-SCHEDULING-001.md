---
id: CONTRACT-SERVER-SCHEDULING-001
domain: SERVER
title: "CONTRACT-SERVER-SCHEDULING-001: Generic Scheduling and Due Materialization Contract"
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
tags: [contract, server, scheduling, due, retry, timezone]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md

---

# CONTRACT-SERVER-SCHEDULING-001: Generic Scheduling and Due Materialization Contract

## 1. Purpose

Определить generic scheduling boundary: вычислить, **когда** работа становится due, и детерминированно материализовать ссылку на logical work без исполнения domain logic и без владения execution.

## 2. Scope

В scope: `SCHEDULE_DEFINITION`, `DUE_COMPUTATION`, `DUE_IDENTITY`, `DUE_WORK_MATERIALIZATION`, one-shot, recurring, condition-produced work, retry/backoff и timezone-aware schedule metadata.

Вне scope: domain truth/finality, provider cadence semantics, сам execution claim, worker ownership и physical queue/backend.

```text
SCHEDULER_EXECUTES_DOMAIN_LOGIC_DIRECTLY=NO
SCHEDULE_IS_WORK_OWNERSHIP=NO
DUE_COMPUTATION_IS_DOMAIN_SEMANTIC_AUTHORITY=NO
```

## 3. Core Rules

Canonical separation:

```text
SCHEDULE_DEFINITION
→ DUE_COMPUTATION
→ DETERMINISTIC_DUE_IDENTITY
→ DUE_WORK_MATERIALIZATION
→ CONTRACT-SERVER-WORK-001
→ CONTRACT-SERVER-EXECUTION-001
```

Cardinality: одна schedule definition может породить N due identities; одна deterministic due identity должна collapse к одной logical work identity, если policy не объявляет иное.

Retry scheduling создаёт новый attempt timing для существующей logical work, а не новый work автоматически.

Condition-produced work допустима только если condition producer возвращает bounded due/materialization decision; scheduler не переопределяет meaning condition.

## 4. Authority Model

- Domain/owner policy определяет meaning расписания, freshness, допустимость backfill и финальность.
- SERVER scheduling mechanism исполняет generic time/due computation по переданной policy definition.
- Work contract владеет созданной logical work identity/state.
- Execution contract владеет claim/lease/fencing после READY.

Restart не должен менять identity уже вычисленного due slot.

## 5. Naming Contract

Schedule и due identities должны быть stable, opaque для transport и не зависеть от process/node. Timezone-aware definitions обязаны иметь explicit timezone/offset semantics; naive local-clock interpretation не является canonical identity.

## 6. Placement Contract

```text
genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
```

Future source projection: `server/scheduling/**` — только после F3.

## 7. Agent Rules

1. Отделять due computation от materialization и execution.
2. Не использовать независимый per-node cron как durable authority.
3. При restart пересчитывать due state относительно stable schedule/policy revision, не теряя уже materialized identities.
4. Backoff/retry связывать с existing work/attempt identity.
5. Не кодировать ETH provider/finality rules в generic scheduler.

## 8. Acceptance Criteria

- поддержаны one-shot/recurring/condition/retry semantics без backend choice;
- due identity deterministic для одинаковых canonical inputs;
- schedule restart не дублирует уже materialized logical work;
- execution ownership отсутствует в schedule authority;
- timezone interpretation explicit там, где schedule зависит от civil time.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| Due/execution separation | Contract test | scheduling boundary tests | Server/Data owner | every implementation change |
| Stable due identity | Property test | restart/duplicate materialization | Server/Data owner | qualification |
| Timezone explicitness | Static/contract review | schedule schema checks | Server/Data owner | every schedule model change |
| Domain authority preserved | Architecture review | semantic-boundary review | Architecture Lead | checkpoint |

## 10. Restart and retry semantics

- control-process restart: recomputation must converge on the same due identities;
- duplicate due observation: collapse through due/work idempotency identity;
- missed period: generic mechanism surfaces candidate due slots; domain policy decides whether materialization remains valid;
- retry/backoff: changes eligibility time/attempt scheduling, not logical work identity unless policy explicitly creates new work.

```text
RESTART_SEMANTICS_DEFINED=YES
IDEMPOTENCY_MODEL_DEFINED=YES
```
