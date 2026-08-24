---
title: "AIFE bridge — Server/Data Foundation planning carrier"
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-25
tags: [aife, bridge, server, data, planning, staging]
category: architecture
doc_type: readme
language: ru
---

# AIFE bridge — Server/Data Foundation planning carrier

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

`AIFE/` — bounded authoring staging + owner-integration carrier внутри
`vitaliipython-ship-it/eth-macro-data-bridge`. Он нужен только для подготовки
AIFE-native owner-candidates на exact проверенной AIFE базе, когда active
AIFE workspace не должен мутировать.

Этот root **не** становится AIFE authority, market-data authority, standards
registry, ADR registry или contracts registry. F0 является control-plane-only
planning delivery; server implementation/user-facing physical delivery намеренно
отсутствуют.

## Authority binding

Источник AIFE authority:

- review package: `AIFE_review_latest.zip`;
- SHA-256: `c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0`;
- AIFE HEAD: `1ed138c06881aaebf8e650fcc020cef570e31b6d`;
- AIFE TREE: `11f5cbc5f81836dddf0e854d3685418b53f22852`;
- entrypoint: `AGENTS.md`.

Machine binding: `integration/authority-binding.json`.

## Staging model

Owner-candidate сохраняется под exact будущим AIFE-relative path:

```text
AIFE/staging/<exact-AIFE-target-relative-path>
```

Current owner-candidates:

- `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/PROGRAM_MAP_aife-server-data-foundation_2026-08-24.md`;
- `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/DEV_TZ_aife-server-data-foundation_2026-08-24.md`;
- `genome/adr/data/ADR-DATA-FOUNDATION-001.md`.

Их staging bytes должны интегрироваться owner-ом без semantic rewrite.
`integration/manifest.json` фиксирует target path, registry requirement и
SHA-256 каждого candidate.

## SERVER contract-domain dependency

Future intended canonical contract remains `CONTRACT-SERVER-WORK-001` with
`DOMAIN=SERVER`. Current pinned AIFE contract-authoring authority does not yet
allow `SERVER`, therefore the file is not created by F0 and must remain blocked
until a separate canonical AIFE owner-governance extension passes. Silent
renaming to `DATA` or `ARCH` is forbidden.

## Two-stage owner handoff

```text
PHASE_A=STAGING_REPOSITORY_OWNER_INTEGRATION
PR_222 → owner review → merge into eth-macro-data-bridge/main → post-merge carrier readback

PHASE_B=CANONICAL_AIFE_OWNER_INTEGRATION
merged carrier → verify current AIFE base → verify hashes → exact-byte apply → real registry update → canonical validation → owner integration

STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

No F2 contract or F3 server implementation starts in either handoff phase.

## Non-authority support files

- `README.md` — navigation only;
- `integration/authority-binding.json` — exact source binding;
- `integration/manifest.json` — staging-to-owner carrier index, **не registry**;
- `evidence/planning-package-readback.md` — read-only qualification evidence.

## Explicit non-goals

Нет server runtime, database, object storage, Parquet, P2, R2 resume,
production activation, AIFE workspace mutation, copied AIFE standards,
copied registries или copied ETH source.
