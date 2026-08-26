---
title: "AIFE Server/Data Foundation — read-back рабочей области разработки"
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-26
category: architecture
doc_type: report
language: ru
---

# AIFE Server/Data Foundation — read-back рабочей области разработки

## 1. Историческая линия

```text
CURRENT_TASK=AIFE-SERVER-DATA-DEVELOPMENT-WORKSPACE-CURRENTIZATION-V1
F0_DURABLE_PLANNING_PR=222
F0_DURABLE_PLANNING_MERGE=4567f8d7f725684ac591757a86293b39e54bc0bf
F0_CANONICAL_STAGING_PR=228
F0_CANONICAL_STAGING_MERGE=2d2899a32bf58dfd4a6de18a5557e9954bb8ae74
F1_LINEAGE=AIFE_SERVER_DATA_FOUNDATION_WIP
F1_RECONCILED_REFERENCE_TREE=32beeb1126e486bfa1986221ac842eef2948bd4f
F1_RECONCILIATION_PATCH_SHA256=c8914f140ee8f7722bf4cf946cd2562e0a3bec86f90ca0ae5723c5d9f623f8f2
```

F0 создал и квалифицировал planning/staging foundation. F1 затем актуализировал
архитектуру Server/Data и зафиксировал единый publication lifecycle и точную rollback
identity. Текущая задача не пересматривает эти решения; она создаёт долговременную
GitHub workspace, из которой продолжится дальнейшая разработка.

## 2. Текущая физическая модель

```text
CURRENT_WORKSPACE_ROLE=SERVER_DATA_DEVELOPMENT_VALIDATION_AND_FUTURE_INTEGRATION_STAGING
PRIMARY_WIP_STORAGE=GITHUB_DATA_BRIDGE_AIFE_TREE
REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
WIP_BRANCH=agent/aife/server-data-foundation-wip
WORKSPACE_ROOT=AIFE/
```

`AIFE/staging/**` хранит реальные будущие AIFE paths. После удаления префикса
`AIFE/staging/` получается exact future canonical AIFE target path. Остальные control/evidence
файлы `AIFE/**` являются только Data Bridge workspace metadata и в canonical AIFE overlay
не входят.

## 3. Canonical AIFE reference

```text
AIFE_REVIEW_PACKAGE=AIFE_review_latest.zip
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_TRACKED_PATH_COUNT=3666
REAL_AIFE_MUTATED=NO
```

Reference immutable и используется для compatibility overlay/validation. Перед будущей
канонической интеграцией требуется fresh reconciliation с актуальным AIFE main.

## 4. Восстановленные и принятые F1 bytes

```text
F1_FILE_COUNT=5
PATCH_FACTORY_README_SHA256=b7970005caf944a9e143d2b9aef855303406fcab48752287ff2ed79cdc05fb6a
PATCH_FACTORY_PLAN_SHA256=8454b7e1046c21335a69f907076400c106978a46c0bf36945349f93d491d251f
F1_README_SHA256=d11c623d085c51c4d3a574d1a0a498c83d9b7c64a8ad294efb461dce264a3234
F1_ARCHITECTURE_SHA256=c14181d9c4805d44f99f4fbfc4322199c3e3bbd992ddbf081f982214aefee4dc
DATA_STANDARDS_DISPOSITION_SHA256=2e979831673a96ab8aec35b7050b5e26efe8acc8fd3bddfd5d6fa7cde1b51551
F1_BYTE_IDENTITY=PASS
```

Нормативный publication lifecycle сохранён без изменения:

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

ACK требует одновременно `DURABLE_STORED`, `INDEPENDENT_READBACK_VERIFIED`,
`CANONICALLY_REGISTERED` и `IDENTITY_MATCH`. Rollback target:
`EXACT_PREVIOUS_ACCEPTED_DEPLOYMENT_REVISION`.

## 5. Currentization control plane

Четыре Data Bridge workspace control/evidence файла текущей задачей переводятся от
`immediate-AEB`/planning-only semantics к development-and-qualification semantics:

```text
IMPLEMENTATION_IN_AIFE_STAGING=ALLOWED
SERVER_SOURCE_DEVELOPMENT_IN_AIFE_STAGING=ALLOWED
TEST_SOURCE_IN_AIFE_STAGING=ALLOWED
SERVER_QUALIFICATION_BEFORE_AEB=REQUIRED
E2E_PROOF_BEFORE_AEB=REQUIRED
FUTURE_AEB_INPUTS=NOT_FINAL_UNTIL_PROVEN_WORKING_STATE
AEB_GENERATION_ALLOWED_NOW=NO
REAL_AIFE_INTEGRATION=DEFERRED
```

Exact bytes этих четырёх файлов замораживаются до remote write и включаются в новый
terminal recovery вместе с read-back receipt. Это закрывает предыдущий evidence/freeze gap.

## 6. Quality-toolchain boundary

```text
TOOLCHAIN_PACKAGE_SHA256=36c64406c57f51c1dc810a64a3c1a599a39dce6f8a7d02ac1b9fd32a2ad5192d
TOOLCHAIN_ID=1b3f6d7281419ae7a692e9f3b69019c7ed13761ee51775ad8f37aa1f85b585eb
QUALITY_POLICY_ID=8c0004758ca1d5a6ddbf013a9a0069a927b9bf87fbb23cedd4f5927835d388b3
TOOLCHAIN_BUILD_COUNT=0
QUALIFICATION_BUILD_COUNT=0
BUILD_A_COUNT=0
BUILD_B_COUNT=0
```

## 7. Что ещё не доказано

```text
SERVER_IMPLEMENTATION_STARTED=NO
SERVER_QUALIFIED=NO
RESTART_RECOVERY_PASS=NO
PUBLICATION_STORAGE_ACCESS_PASS=NO
ETH_E2E_PASS=NO
HORIZONTAL_QUALIFICATION_PASS=NO
FUTURE_AEB_ELIGIBLE=NO
AEB_CREATED=NO
D380_ACTIVATED=NO
REAL_AIFE_MUTATED=NO
```

Следовательно, текущая workspace publication не является runtime qualification и не
разрешает AEB.

## 8. Следующая граница

Только после успешной публикации exact 9-path candidate, remote byte read-back и required
validation следующий отдельный checkpoint может быть:

```text
NEXT_CHECKPOINT=CHECKPOINT_DATA_STANDARDS
CHECKPOINT_DATA_STANDARDS_STARTED=NO
```
