---
title: "Контур Server/Data Foundation — execution navigation"
status: draft
owner: Architecture Lead
created: 2026-08-25
updated: 2026-08-30
category: architecture
doc_type: index
language: ru
tags: [execution, server, data, foundation, aife, staging]
scope_slug: aife-server-data-foundation
authority_reference:
  - ../../../../../AGENTS.md
  - ../../../../../AGENTS_ARTIFACTS.md
  - ./PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md
  - ./DEV_TZ_aife-server-data-foundation_2026-08-24.md
  - ./DEV_TZ_aife-server-data-foundation_f5_2026-08-29.md
  - ./PRR_aife-server-data-foundation_f5_2026-08-29.md
  - ./OWNER_AUTHORIZATION_aife-server-data-foundation_f5_2026-08-30.md
  - ../../../../../genome/adr/data/ADR-DATA-FOUNDATION-001.md
---

# Контур Server/Data Foundation — execution navigation

## Назначение

Этот каталог связывает historical F0 foundation planning и текущий F5 implementation DEV_TZ governance contour. Он является execution-scope навигацией и сам по себе не считается physical/runtime поставкой.

## Артефакты

- [Program Map](PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md) — карта стадий и архитектурных границ.
- [Historical foundation DEV_TZ](DEV_TZ_aife-server-data-foundation_2026-08-24.md) — historical foundation/control-plane planning; не является F5 implementation DEV_TZ.
- [F5 implementation DEV_TZ](DEV_TZ_aife-server-data-foundation_f5_2026-08-29.md) — owner-reviewed implementation contract для bounded F5 slice.
- [F5 owner-review PRR](PRR_aife-server-data-foundation_f5_2026-08-29.md) — primary byte-bound owner review текущего F5 DEV_TZ.
- [F5 C-144 Owner Authorization](OWNER_AUTHORIZATION_aife-server-data-foundation_f5_2026-08-30.md) — отдельная owner execution authority для bounded implementation; implementation начат в owner-authorized bounded C-144 contour.
- [ADR-DATA-FOUNDATION-001](../../../../../genome/adr/data/ADR-DATA-FOUNDATION-001.md) — кандидат архитектурного решения по Server/Data Foundation.

## Current F5 governance state

```text
HISTORICAL_FOUNDATION_DEV_TZ_PRESERVED=YES
CURRENT_PROGRAM_FRONTIER=F5_C144_IMPLEMENTATION_IN_PROGRESS
HISTORICAL_FOUNDATION_DEV_TZ_IS_F5_IMPLEMENTATION_DEV_TZ=NO
F5_IMPLEMENTATION_DEV_TZ_NAVIGATION_PRESENT=YES
F5_OWNER_REVIEW_PRR_NAVIGATION_PRESENT=YES
DUPLICATE_DEV_TZ_AUTHORITY=NO
CANONICAL_C_TASK_ID=C-144
F5_IMPLEMENTATION_DEV_TZ_CREATED=YES
F5_IMPLEMENTATION_DEV_TZ_OWNER_REVIEWED=YES
F5_IMPLEMENTATION_DEV_TZ_OWNER_REVIEW=PASS
OWNER_EXECUTION_AUTHORIZATION_CREATED=YES
OWNER_EXECUTION_AUTHORITY_GRANTED=YES
F5_IMPLEMENTATION_STARTED=YES
F5_IMPLEMENTATION_ALLOWED=YES_OWNER_AUTHORIZED_IN_PROGRESS
CURRENT_F5_RUNTIME_READINESS_STATUS=NOT_EVALUATED_PRE_IMPLEMENTATION
CURRENT_F5_QUALIFICATION_STATUS=NOT_RUN
F5M_STARTED=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
AEB_GENERATION=NO
REAL_AIFE_MUTATION=NO
NEXT_OWNER_TASK=CONTINUE_F5_C144_IMPLEMENTATION
```

## Граница AIFE и Data Bridge

AIFE предоставляет общий серверный механизм исполнения, планирования и хранения.
Data Bridge сохраняет полномочия на семантику ETH market data. Будущий физический
backend AIFE не становится доменным источником истины, а Data Bridge не остаётся
целевым основным физическим warehouse.

## Будущая AEB-интеграция

Staging-копии предназначены для последующей установки через отдельно
авторизованный канонический AIFE handoff/AEB route. Намерение регистрации ADR,
generator-owned projections и обязательные validation actions фиксируются в
`AIFE/integration/aeb-input-plan.json` в Data Bridge carrier и не исполняются этим README.

## Граница поставки

Runtime, server, scheduler, storage и migration в этом F0-контуре не реализованы.
Физическая интеграция и активация требуют отдельных owner authorization,
qualification и terminal proof.
