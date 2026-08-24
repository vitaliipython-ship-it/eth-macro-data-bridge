---
title: "Мост AIFE — пакет планирования серверной и информационной основы"
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
tags: [aife, bridge, server, data, planning, staging]
category: architecture
doc_type: readme
language: ru
---

# Мост AIFE — пакет планирования серверной и информационной основы

```text
AIFE_BRIDGE_IS_FINAL_AUTHORITY=false
FINAL_OWNER_AUTHORITY=E:\AIFE_Ecosystem\AIFE
BRIDGE_PURPOSE=AUTHOR_AIFE_NATIVE_CANDIDATES_OUTSIDE_ACTIVE_WORKSPACE_AND_INTEGRATE_LATER_WITHOUT_SEMANTIC_REWRITE
AIFE_STANDARD_FORK_CREATED=false
AIFE_SECOND_REGISTRY_CREATED=false
AIFE_SECOND_AUTHORITY_CREATED=false
PLANNING_PACKAGE_RESULT=PASS
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
PHYSICAL_DELIVERY=NO
```

## Назначение

`AIFE/` — ограниченный промежуточный контур подготовки и последующей интеграции владельцем внутри
`vitaliipython-ship-it/eth-macro-data-bridge`. Он нужен только для подготовки
AIFE-совместимых артефактов-кандидатов на точно проверенной базе AIFE, когда активную
рабочую область AIFE изменять нельзя.

Этот корень **не** становится полномочной базой AIFE, полномочным источником рыночных данных, реестром стандартов,
реестром ADR или реестром контрактов. F0 поставляет только планирование и доказательства
управляющего контура; реализация сервера и физическая ценность для пользователя намеренно
отсутствуют.

## Привязка к полномочной базе

Источник полномочной базы AIFE:

- пакет проверки: `AIFE_review_latest.zip`;
- SHA-256: `c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0`;
- AIFE HEAD: `1ed138c06881aaebf8e650fcc020cef570e31b6d`;
- AIFE TREE: `11f5cbc5f81836dddf0e854d3685418b53f22852`;
- точка входа: `AGENTS.md`.

Машинная привязка: `integration/authority-binding.json`.

## Модель промежуточного размещения

Артефакт-кандидат владельца сохраняется по точному будущему относительному пути AIFE:

```text
AIFE/staging/<exact-AIFE-target-relative-path>
```

Текущие артефакты-кандидаты владельца:

- `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md`;
- `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_2026-08-24.md`;
- `genome/adr/data/ADR-DATA-FOUNDATION-001.md`.

Их точные байты должны быть интегрированы владельцем без изменения смысла.
`integration/manifest.json` фиксирует целевой путь, необходимость регистрации и
SHA-256 каждого кандидата.

## Зависимость от домена контракта `SERVER`

Будущий канонический контракт сохраняет идентификатор `CONTRACT-SERVER-WORK-001` с
`DOMAIN=SERVER`. В зафиксированной полномочной базе AIFE домен `SERVER` пока не разрешён для
создания контрактов, поэтому F0 не создаёт файл этого контракта. Его создание должно
оставаться заблокированным до отдельного изменения правил управления AIFE, одобренного владельцем.
Тихое переименование домена в `DATA` или `ARCH` запрещено.

## Двухэтапная интеграция владельцем

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222 → owner review → merge into eth-macro-data-bridge/main → post-merge carrier readback

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged carrier → verify current AIFE base → verify hashes → exact-byte apply → real registry update → canonical validation → owner integration

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

Ни на одном из двух этапов интеграции не начинается создание контрактов F2 или
реализация сервера F3.

## Вспомогательные файлы без собственных полномочий

- `README.md` — только навигация;
- `integration/authority-binding.json` — точная привязка к исходной полномочной базе;
- `integration/manifest.json` — указатель промежуточного пакета для интеграции владельцем, **не реестр**;
- `evidence/planning-package-readback.md` — доказательства проверки для чтения.

## Явные нецели

Нет серверного исполнения, базы данных, `Object Storage`, `Parquet`, P2, возобновления R2,
активации боевого режима, изменения рабочей области AIFE, копий стандартов AIFE,
копий реестров или копии исходного кода ETH.
