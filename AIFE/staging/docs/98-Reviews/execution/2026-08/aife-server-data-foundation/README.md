---
title: "Контур Server/Data Foundation — навигация F0"
status: draft
owner: Architecture Lead
created: 2026-08-25
updated: 2026-08-25
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
  - ../../../../../genome/adr/data/ADR-DATA-FOUNDATION-001.md
---

# Контур Server/Data Foundation — навигация F0

## Назначение

Этот каталог связывает управляющие артефакты F0 для будущей интеграции
Server/Data Foundation в AIFE. Он является execution-scope навигацией и сам по
себе не считается физической поставкой.

## Артефакты

- [Program Map](PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md) — карта стадий и архитектурных границ.
- [DEV_TZ](DEV_TZ_aife-server-data-foundation_2026-08-24.md) — долговечный контракт планирования и physical-use boundary.
- [ADR-DATA-FOUNDATION-001](../../../../../genome/adr/data/ADR-DATA-FOUNDATION-001.md) — кандидат архитектурного решения по Server/Data Foundation.

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
