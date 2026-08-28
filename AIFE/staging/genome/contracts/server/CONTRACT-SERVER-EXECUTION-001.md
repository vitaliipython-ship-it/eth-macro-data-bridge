---
id: CONTRACT-SERVER-EXECUTION-001
domain: SERVER
title: "CONTRACT-SERVER-EXECUTION-001: Distributed Execution Ownership Contract"
version: "0.2.0"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-27
review_cycle_days: 180
next_review_due: 2027-02-23
category: standards
doc_type: contract
language: ru
tags: [contract, server, execution, claim, lease, fencing, worker]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - genome/contracts/server/CONTRACT-SERVER-SCHEDULING-001.md
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md

---

# CONTRACT-SERVER-EXECUTION-001: Distributed Execution Ownership Contract

## 1. Purpose

Определить implementation-neutral distributed ownership semantics для claim/lease/fencing так, чтобы горизонтальное исполнение не позволяло stale worker подтвердить durable terminal effect.

## 2. Scope

В scope: `CLAIM`, `LEASE`, `LEASE_EXPIRY`, `RENEWAL`, `FENCING_TOKEN`, `ATTEMPT`, optional `HEARTBEAT`, `RECLAIM`, duplicate execution boundary и terminalization.

Поддерживаемые process roles: `CONTROL`, `WORKER`, `COMBINED_INITIAL_NODE`. Роль процесса не меняет authority model.

Вне scope: конкретный lock service/database/broker, business/domain execution semantics и transport selection.

```text
IN_PROCESS_LOCK_IS_DURABLE_DISTRIBUTED_AUTHORITY=NO
STALE_WORKER_CAN_COMMIT_AFTER_FENCE_LOSS=NO
```

## 3. Core Rules

Canonical ownership relation:

```text
READY_WORK
→ ATOMIC_CLAIM
→ LEASE + MONOTONIC_FENCING_TOKEN + ATTEMPT
→ RUNNING
→ RENEW | EXPIRE/RECLAIM
→ TERMINALIZATION
```

Главный invariant:

```text
ONLY_CURRENT_FENCING_AUTHORITY_MAY_COMMIT_TERMINAL_EFFECT
```

Lease expiry делает старое владение недействительным. Новый claimant получает fencing authority, отличимый от stale authority. Heartbeat, если используется, является сигналом renewal/liveness, но не самостоятельной authority.

Duplicate execution может физически возникнуть при failure timing, поэтому durable effect обязан быть fence/idempotency guarded.

## 4. Authority Model

- Work contract владеет logical identity/state.
- Execution contract владеет текущим claim/lease/fence/attempt authority.
- Storage implementation атомарно хранит/сравнивает ownership state, но не меняет rule meaning.
- Publication и иные durable effect consumers обязаны проверять current fencing authority либо equivalent accepted ownership proof.

## 5. Naming Contract

`CLAIM_ID`, `LEASE_ID`, `FENCING_TOKEN` и `ATTEMPT_ID` должны однозначно ссылаться на `WORK_ID`. `FENCING_TOKEN` должен обеспечивать ordering/comparability sufficient to reject stale writers; конкретный primitive не задаётся.

## 6. Placement Contract

```text
genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
```

Future source projection: `server/execution/**` после F3 gate.

## 7. Agent Rules

1. Не реализовывать durable ownership только mutex/asyncio lock.
2. Перед terminal durable effect проверять актуальность fencing authority.
3. После lease loss worker обязан прекратить authority-bearing commits.
4. Reclaim создаёт новый current ownership generation.
5. CONTROL не становится скрытым single-process SSOT.

## 8. Acceptance Criteria

- claim/lease/fence/attempt различимы;
- stale token не может terminalize;
- lease expiry/reclaim restart-safe;
- duplicate worker execution не создаёт два accepted terminal effects;
- process role count 1→N не меняет contract semantics.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| Current fence required | Concurrency/integration test | stale-writer scenario | Server/Data owner | qualification |
| Atomic claim | Integration test | concurrent claim scenario | Server/Data owner | qualification |
| Lease expiry/reclaim | Recovery test | worker crash/restart | Server/Data owner | qualification |
| No process-memory authority | Architecture review | implementation boundary | Architecture Lead | checkpoint |

## 10. Failure and restart semantics

- worker crash: lease expires or is safely reclaimed; same logical work may continue with a new attempt/fence;
- stale worker: may finish local computation but cannot commit authority-bearing durable effect after fence loss;
- control restart: claim authority remains durable and independently readable;
- duplicate delivery: may reach multiple workers, but only current fence plus idempotency guard can accept terminal effect;
- renewal failure: worker transitions to non-authoritative state before terminal commit.

```text
RESTART_SEMANTICS_DEFINED=YES
FAILURE_SEMANTICS_DEFINED=YES
FENCING_MODEL_DEFINED=YES
```

## 11. Reproducible execution input binding

For PIT/replay/backtest-capable execution, one logical execution must remain bound to the
exact resolved input generation/read set selected for that execution. Retry may create a
new attempt/fence, but it must not silently reinterpret the same logical execution against a
newer current generation.

```text
EXECUTION_INPUT_BINDING=
EXACT_RESOLVED_READ_SET_OR_CONTENT_IDENTITY
+ EXACT_GENERATION_IDENTITY
+ REPLAY_CUTOFF_IF_APPLICABLE
+ METHOD_MODEL_STRATEGY_CONFIG_IDENTITY_IF_APPLICABLE

RETRY_SAME_LOGICAL_EXECUTION_SILENTLY_REBINDS_TO_NEW_CURRENT_GENERATION=NO
```

The domain owner remains authoritative for domain meaning of revisions/finality/gaps;
execution only preserves the resolved identities. Current fencing authority is still
required for authority-bearing durable effects.
