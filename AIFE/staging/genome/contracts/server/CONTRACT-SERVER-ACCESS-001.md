---
id: CONTRACT-SERVER-ACCESS-001
domain: SERVER
title: "CONTRACT-SERVER-ACCESS-001: Generic Semantic Access Boundary Contract"
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
tags: [contract, server, access, query, provenance, freshness, pagination]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation-patch-factory/f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
related:
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md

---

# CONTRACT-SERVER-ACCESS-001: Generic Semantic Access Boundary Contract

## 1. Purpose

Определить generic read/query/access boundary для accepted published data так, чтобы consumer получал explicit result identity, provenance и failure semantics без доступа к backend internals и без silent domain renormalization.

## 2. Scope

В scope: `REQUEST`, `QUERY/FILTER`, `RESULT_SET`, `RESULT_IDENTITY`, `SOURCE_REVISION`, `FRESHNESS/SNAPSHOT_IDENTITY` где применимо, `PROVENANCE`, `PARTIAL_RESULT/ERROR`, `PAGINATION/CURSOR` где применимо.

Вне scope: изменение finality, создание domain identity, renormalization provider payload, backend table/bucket/path contract.

```text
ACCESS_LAYER_RENORMALIZES_DOMAIN_DATA=NO
ACCESS_LAYER_CHANGES_FINALITY=NO
ACCESS_LAYER_INVENTS_DOMAIN_IDENTITY=NO
```

## 3. Core Rules

Canonical relation:

```text
REQUEST
→ DOMAIN/CAPABILITY RESOLUTION INPUT
→ QUERY/FILTER PLAN
→ CANONICAL ACCEPTED READ
→ RESULT_SET + RESULT_IDENTITY + SOURCE_REVISION + PROVENANCE
```

Partial result не маскируется как complete. Cursor/pagination identity должна быть привязана к query/snapshot semantics sufficient to avoid silent mixing revisions.

Access может использовать storage capabilities, но physical locator остаётся implementation detail.

## 4. Authority Model

- Domain integration владеет domain resolution, finality и semantic interpretation.
- SERVER access владеет generic request/result envelope, pagination/failure signaling и routing through accepted capabilities.
- Storage владеет physical read/inventory mechanics.
- Publication/registration владеет accepted canonical identities, которые access может ссылочно экспонировать.

## 5. Naming Contract

`RESULT_IDENTITY` должна быть stable для конкретного accepted query/snapshot result или явно non-stable с documented semantics. `SOURCE_REVISION` и provenance не должны выводиться из wall-clock response time, если owner revision доступна.

## 6. Placement Contract

```text
genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
```

Future source projection: `server/access/**` после F3 transport applicability decision.

## 7. Agent Rules

1. Не renormalize domain records на generic access layer.
2. Не менять finality/freshness flags без domain authority.
3. На ambiguous domain resolution fail closed или вернуть explicit ambiguity/error.
4. Partial result маркировать как partial и перечислять unavailable partitions/reasons где возможно.
5. Pagination/cursor не смешивает incompatible source revisions silently.

## 8. Acceptance Criteria

- request/result/provenance/revision/failure fields различимы;
- partial result не выглядит complete;
- backend locator не становится consumer semantic contract;
- domain finality/identity остаются неизменёнными;
- query across restart/retry имеет explicit snapshot/revision behavior.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| No renormalization/finality mutation | Contract test | domain fixture parity | Server/Data + domain owner | every implementation change |
| Provenance/revision exposure | Integration test | query result assertions | Server/Data owner | qualification |
| Partial/error explicitness | Contract test | degraded read scenarios | Server/Data owner | qualification |
| Cursor revision safety | Contract test | pagination across revisions | Server/Data owner | when pagination exists |

## 10. Failure and restart semantics

- partial storage/read failure: return explicit partial/error state; do not silently omit failed scope;
- stale/missing snapshot: surface freshness/revision diagnostic according to domain policy;
- access process restart: no semantic state may exist only in cursor process memory if cursor is intended to survive restart;
- duplicate request: may reuse cached/accepted result only if identity/revision policy proves equivalence;
- ambiguous canonical registration: fail closed rather than inventing domain identity.

```text
RESTART_SEMANTICS_DEFINED=YES
FAILURE_SEMANTICS_DEFINED=YES
IDEMPOTENCY_MODEL_DEFINED=YES
```
