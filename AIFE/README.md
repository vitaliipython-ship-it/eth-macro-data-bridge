---
title: "AIFE — рабочая область разработки Server/Data Foundation"
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-08-30
tags: [aife, server, data, development, validation, staging, qualification]
category: architecture
doc_type: readme
language: ru
---

# AIFE — рабочая область разработки Server/Data Foundation

## Текущая роль

```text
CURRENT_WORKSPACE_ROLE=SERVER_DATA_DEVELOPMENT_VALIDATION_AND_FUTURE_INTEGRATION_STAGING
PRIMARY_WIP_STORAGE=GITHUB_DATA_BRIDGE_AIFE_TREE
REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
WIP_BRANCH=agent/aife/server-data-foundation-wip
AIFE_BRIDGE_IS_FINAL_AUTHORITY=false
REAL_AIFE_MUTATION=NO
REAL_AIFE_INTEGRATION=DEFERRED
AEB_GENERATION_ALLOWED_NOW=NO
```

`AIFE/` внутри Data Bridge является долговременной рабочей областью разработки,
проверки и подготовки будущей интеграции AIFE Server/Data Foundation. Она не является
канонической рабочей областью AIFE и не создаёт второй реестр, второй набор стандартов
или вторую семантическую authority.

Data Bridge сохраняет authority над ETH market semantics: provider semantics, stable
identities, normalization, finality, revision/gap rules и semantic resolution. Будущие
AIFE runtime/storage mechanisms владеют физическим исполнением и жизненным циклом хранения,
но **не** становятся ETH semantic authority.

## `AIFE/staging/**` — реальные будущие AIFE-файлы

В этой ветке разрешено разрабатывать реальные будущие файлы AIFE и тесты до их
канонической установки:

```text
IMPLEMENTATION_IN_AIFE_STAGING=ALLOWED
SERVER_SOURCE_DEVELOPMENT_IN_AIFE_STAGING=ALLOWED
TEST_SOURCE_IN_AIFE_STAGING=ALLOWED
```

Правило отображения пути является точным и единственным:

```text
AIFE/staging/<future-path>
→ strip prefix AIFE/staging/
→ <future-path>
```

То есть файл под `AIFE/staging/` обязан уже иметь тот относительный путь и те байты,
которые после будущей owner-authorized интеграции предназначены для canonical AIFE.
Control-файлы `AIFE/README.md`, `AIFE/integration/**` и `AIFE/evidence/**` принадлежат
Data Bridge workspace и в canonical AIFE overlay не переносятся.

## Канонический reference snapshot

Текущая compatibility-база остаётся неизменяемым reference snapshot:

```text
AIFE_REVIEW_PACKAGE=AIFE_review_latest.zip
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_REFERENCE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_REFERENCE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_REFERENCE_TRACKED_PATH_COUNT=3666
```

Snapshot нужен для reproducible compatibility validation. Он не является разрешением
на запись в реальный AIFE и не становится финальной базой будущего AEB: перед финальной
интеграцией требуется fresh canonical AIFE reconciliation.

## Канонический quality toolchain

Для проверок используется только уже поставленный canonical toolchain:

```text
TOOLCHAIN_PACKAGE_SHA256=36c64406c57f51c1dc810a64a3c1a599a39dce6f8a7d02ac1b9fd32a2ad5192d
TOOLCHAIN_ID=1b3f6d7281419ae7a692e9f3b69019c7ed13761ee51775ad8f37aa1f85b585eb
QUALITY_POLICY_ID=8c0004758ca1d5a6ddbf013a9a0069a927b9bf87fbb23cedd4f5927835d388b3
TOOLCHAIN_BUILD_COUNT=0
QUALIFICATION_BUILD_COUNT=0
BUILD_A_COUNT=0
BUILD_B_COUNT=0
```

Новая WIP-правка сама по себе не является основанием для rebuild toolchain.

## Обязательный путь до будущего AEB

```text
AIFE_CANONICAL_REFERENCE_SNAPSHOT
→ AUTHOR REAL FUTURE AIFE FILES IN AIFE/staging/**
→ CANONICAL TOOLCHAIN VALIDATION
→ IMPLEMENT SERVER/DATA FUNCTIONALITY
→ UNIT / CONTRACT / INTEGRATION TESTS
→ REAL SERVER QUALIFICATION
→ RESTART / FAILURE / RECOVERY PROOF
→ STORAGE / PUBLICATION / ACCESS PROOF
→ ETH DATA BRIDGE E2E PROOF
→ MULTI-WORKER / MULTI-NODE / HORIZONTAL QUALIFICATION AS APPLICABLE
→ PROVEN WORKING STATE
→ FRESH FINAL AIFE RECONCILIATION
→ BOUNDED <=128-PATH PATCH DECOMPOSITION
→ OWNER AUTHORIZATION
→ AEB GENERATION
→ FUTURE CANONICAL AIFE INTEGRATION
```

```text
SERVER_QUALIFICATION_BEFORE_AEB=REQUIRED
E2E_PROOF_BEFORE_AEB=REQUIRED
FUTURE_AEB_INPUTS=NOT_FINAL_UNTIL_PROVEN_WORKING_STATE
AEB_FROM_UNPROVEN_DESIGN=FORBIDDEN
AEB_BEFORE_SERVER_QUALIFICATION=FORBIDDEN
```

Поэтому текущая рабочая область может содержать design/source/test candidates и их
validation evidence, но не должна объявлять `SERVER_QUALIFIED`, `E2E_QUALIFIED` или
`FUTURE_AEB_ELIGIBLE` до фактического прохождения соответствующих gates.

## Текущая точка программы

F0–F4 и F5R/F5P сохранены как уже закрытая architecture/governance lineage. Текущий
bounded contour публикует отдельную owner execution authority поверх уже созданного и
owner-reviewed F5 implementation DEV_TZ; он не является новой архитектурной стадией и
не начинает F5 implementation.

```text
CURRENT_PROGRAM_FRONTIER=F5_C144_IMPLEMENTATION_IN_PROGRESS
F5R_ARCHITECTURE_RESEARCH=COMPLETE
F5P_WORKSPACE_DEPLOYMENT_GOVERNANCE=COMPLETE
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
F5M_ALLOWED=NO
F5M_STARTED=NO
PRODUCTION_DEPLOYMENT_ALLOWED=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
OWNER_AUTHORIZATION_CREATED=NO
AEB_CREATED=NO
AEB_GENERATION=NO
REAL_AIFE_MUTATION=NO
NEXT_OWNER_TASK=CONTINUE_F5_C144_IMPLEMENTATION
```

Отдельный F5 DEV_TZ и явная owner execution authority теперь присутствуют; сам F5 implementation
начат в bounded C-144 contour. F5M/backfill, production activation/cutover, AEB generation и real AIFE
integration остаются за отдельными последующими gates.

## Workspace publication transport

Этот раздел владеет human-readable policy публикации development workspace `AIFE/` в WIP-ветку
Data Bridge. Он определяет только transport frozen candidate bytes и не заменяет AEB,
`verified_handoff`, `authorized_execution_bundle`, Artifact Contract, ADR/STD или market-data
publication semantics.

```text
WORKSPACE_PUBLICATION_TRANSPORT_POLICY=ACTIVE
PUBLICATION_ROUTE_P1=SAME_ENVIRONMENT_NATIVE_FILE_BACKED_GIT
PUBLICATION_ROUTE_P2=OWNER_GITHUB_CODESPACES_RECEIVER
PUBLICATION_ROUTE_P3=FAIL_CLOSED_STOP

QUALIFIED_TOOLCHAIN_ENVIRONMENT_MAY_DIFFER_FROM_PUBLICATION_RECEIVER=YES
EXACT_BYTE_FREEZE_REQUIRED=YES
BYTE_COMPLETE_RECOVERY_OR_HANDOFF_REQUIRED=YES
EXTERNAL_SHA256_SIDECAR_REQUIRED=YES
RECEIVER_EXACT_BYTE_VERIFICATION_REQUIRED=YES
EXACT_CHANGED_PATH_SET_REQUIRED=YES
INDEX_GIT_BLOB_VERIFICATION_REQUIRED=YES
ONE_PARENT_SUCCESSOR_REQUIRED=YES
LAST_MOMENT_REMOTE_RACE_CHECK_REQUIRED=YES
FORCE_PUSH_ALLOWED=NO
FORCE_WITH_LEASE_ALLOWED=NO
INDEPENDENT_POST_PUBLICATION_REMOTE_READBACK_REQUIRED=YES
```

### Route selection

P1 допустим только когда **то же окружение**, которое владеет frozen candidate, имеет все четыре
publication capabilities ниже и task contract разрешает publication:

```text
FILE_BACKED_GIT=PASS
GITHUB_NETWORK=PASS
GITHUB_AUTHENTICATION=PASS
GITHUB_WRITE_ROUTE=PASS
```

Если хотя бы одна обязательная P1 capability недоступна, это не source/quality failure. Состояние
классифицируется как `PUBLICATION_HANDOFF_REQUIRED`, после чего выбирается P2; если P2 не может
быть безопасно выполнен, применяется P3 `FAIL_CLOSED_STOP`.

```text
DO_NOT_RETRY_UNAVAILABLE_NATIVE_GIT_ROUTE=YES
DO_NOT_ATTEMPT_LARGE_FILE_CONNECTOR_SERIALIZATION=YES
DO_NOT_USE_GITHUB_CONTENTS_API_MULTI_COMMIT_FALLBACK=YES
DO_NOT_REGENERATE_FROZEN_BYTES_FOR_TRANSPORT=YES
DO_NOT_USE_CREATE_BLOB_AS_LARGE_FILE_TEXTUAL_FALLBACK=YES
CODESPACES_HANDOFF_REQUIRED=YES
PUBLICATION_HANDOFF_REQUIRED_IS_IMPLEMENTATION_FAILED=NO
```

### Producer boundary

До P2 handoff producer уже обязан иметь:

```text
CANDIDATE_VALIDATION=PASS
EXACT_BYTE_FREEZE=PASS
EXPECTED_PATH_SET_FROZEN=YES
SIZE_SHA256_GIT_BLOB_RECORDED=YES
PRODUCER_GITHUB_PUBLICATION_AFTER_P2_SELECTION=FORBIDDEN
```

После выбора P2 producer создаёт byte-complete ZIP, внешний `.sha256` sidecar, manifest с exact
predecessor и file identities, deterministic receiver и одну copy/paste launch command. Producer
останавливается на `PASS_CANDIDATE_FROZEN_PENDING_CODESPACES_PUBLICATION` или task-specific
эквиваленте и не реконструирует candidate через connector serialization.

Owner handoff обязан раскрыть `CODESPACES_HANDOFF_ZIP`, `CODESPACES_HANDOFF_SHA256_SIDECAR` и
`CODESPACES_LAUNCH_COMMAND`. Owner открывает Codespace exact target repository, загружает ZIP и
sidecar в workspace root, запускает команду без редактирования и возвращает orchestrator весь
terminal output. Owner не реконструирует candidate files вручную.

### Codespaces receiver boundary

```text
CODESPACES_ROLE=BYTE_PRESERVING_GIT_PUBLICATION_RECEIVER
CODESPACES_IS_CANONICAL_TOOLCHAIN_PROFILE=NO
QUALITY_POLICY_OWNED_BY_PRODUCER_VALIDATION=YES
PUBLICATION_RECEIVER_MAY_RELAX_QUALITY_GATE=NO
PUBLICATION_RECEIVER_MAY_CHANGE_FROZEN_BYTES=NO
```

Без отдельной qualification-задачи Codespaces не регенерирует, не исправляет, не форматирует, не
нормализует line endings и не переосмысливает frozen candidate. Receiver использует candidate
bytes из handoff carrier и выполняет только publication proof: ZIP/sidecar и manifest identity,
size/SHA256/Git-blob verification, repository/predecessor/write-route proof, clean-worktree proof,
exact installation/diff/staging/index proof, один one-parent local commit, local commit byte
readback, last-moment race check, normal fast-forward push и post-push remote exact-byte/readback
report. Force и force-with-lease запрещены.

Required receiver terminal states:

```text
PASS_CODESPACES_EXACT_BYTE_PUBLICATION
STOP_BLOCKED_CODESPACES_GIT_WRITE_CAPABILITY
STOP_BLOCKED_CODESPACES_WORKTREE_NOT_CLEAN
STOP_BLOCKED_HANDOFF_SHA_MISMATCH
STOP_BLOCKED_REMOTE_AUTHORITY_CHANGED
STOP_BLOCKED_CANDIDATE_IDENTITY_MISMATCH
STOP_BLOCKED_UNEXPECTED_PATH_CHANGE
STOP_BLOCKED_INDEX_BLOB_MISMATCH
STOP_BLOCKED_REMOTE_BRANCH_CHANGED
STOP_BLOCKED_POST_PUBLICATION_REMOTE_READBACK_MISMATCH
```

После push должны выполняться:

```text
FINAL_HEAD=CANDIDATE_COMMIT
FINAL_PARENT=EXPECTED_PREDECESSOR
FINAL_PARENT_COUNT=1
SUCCESSOR_COMMIT_COUNT=1
FORCE_USED=NO
FORCE_WITH_LEASE_USED=NO
```

Где compare support доступен, независимый verifier также требует `STATUS=ahead`, `AHEAD_BY=1`,
`BEHIND_BY=0`, `TOTAL_COMMITS=1`.

Codespaces terminal PASS необходим, но недостаточен для canonical closure. После возврата terminal
output orchestrator independently fresh-read-ит GitHub и проверяет final HEAD/tree/parent,
parent/successor counts, exact changed paths, remote blobs/bytes и task-specific semantics. Только
после этого допускается `INDEPENDENT_REMOTE_PUBLICATION_ACCEPTANCE=PASS`.

### AEB and verified-handoff boundary

```text
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_IS_AEB=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_IS_VERIFIED_HANDOFF=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_REPLACES_AEB=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_REPLACES_CANONICAL_AIFE_PATCH_ROUTE=NO
```

Codespaces handoff публикует только Data Bridge `AIFE/` development workspace candidate в его WIP
branch. Future canonical AIFE integration по-прежнему требует отдельно authorized AEB /
verified-handoff governance. Если Codespaces должен стать full canonical toolchain qualification
environment, это требует отдельной `CODEX_OR_CODESPACES_TOOLCHAIN_PROFILE_QUALIFICATION` задачи.
