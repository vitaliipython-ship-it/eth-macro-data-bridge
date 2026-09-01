---
title: "AIFE — qualified F5 provenance and transition workspace"
status: draft
owner: Architecture Lead
created: 2026-08-24
updated: 2026-09-02
tags: [aife, server, data, development, validation, staging, qualification]
category: architecture
doc_type: readme
language: ru
---

# AIFE — qualified F5 provenance and transition workspace

## Текущая роль

```text
CURRENT_WORKSPACE_ROLE=QUALIFIED_F5_PROVENANCE_AND_TRANSITION_WORKSPACE
CURRENT_DATA_BRIDGE_AIFE_ROLE=QUALIFIED_F5_PROVENANCE_AND_TRANSITION_WORKSPACE
PRIMARY_WIP_STORAGE=GITHUB_DATA_BRIDGE_AIFE_TREE
REPOSITORY=vitaliipython-ship-it/eth-macro-data-bridge
WIP_BRANCH=agent/aife/server-data-foundation-wip
AIFE_BRIDGE_IS_FINAL_AUTHORITY=false
LONG_TERM_GENERIC_SERVER_DEVELOPMENT_IN_DATA_BRIDGE_REPO=NO
FUTURE_GENERIC_SERVER_DEVELOPMENT=AIFE_GITHUB_DEDICATED_WIP_RESOLVED_IN_F5C_PLANNING
REAL_AIFE_MUTATION=NO
REAL_AIFE_INTEGRATION=DEFERRED
AEB_GENERATION_ALLOWED_NOW=NO
```

`AIFE/` внутри Data Bridge теперь является qualified F5 source/provenance carrier и
transition workspace. Это **не** долгосрочная рабочая область разработки generic AIFE Server.
Будущий Server development выполняется в dedicated WIP branch канонического GitHub repository
AIFE, exact repository/base/branch namespace для которого обязан fresh определить F5C planning.

Data Bridge сохраняет authority над ETH market semantics: provider semantics, stable
identities, normalization, finality, revision/gap rules и semantic resolution. Generic AIFE
runtime/storage mechanisms владеют физическим исполнением и жизненным циклом хранения, но
не становятся ETH semantic authority.

## `AIFE/staging/**` — qualified F5 provenance и transition bytes

Текущий staging tree сохраняет реальные qualified F5 future-AIFE bytes и transition inputs:

```text
IMPLEMENTATION_IN_AIFE_STAGING=QUALIFIED_F5_PROVENANCE_AND_TRANSITION_ONLY
SERVER_SOURCE_DEVELOPMENT_IN_AIFE_STAGING=NO_LONG_TERM_GENERIC_SERVER_DEVELOPMENT
TEST_SOURCE_IN_AIFE_STAGING=QUALIFIED_F5_PROVENANCE_AND_TRANSITION_ONLY
```

Правило отображения пути остаётся точным:

```text
AIFE/staging/<future-path>
→ strip prefix AIFE/staging/
→ <future-path>
```

Control-файлы `AIFE/README.md`, `AIFE/integration/**` и `AIFE/evidence/**` принадлежат Data Bridge
workspace и не являются canonical AIFE overlay inputs. Historical evidence не currentize-ится
только потому, что program frontier продвинулся.

## Канонический reference snapshot

```text
AIFE_REVIEW_PACKAGE=AIFE_review_latest.zip
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
AIFE_REFERENCE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
AIFE_REFERENCE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
AIFE_REFERENCE_TRACKED_PATH_COUNT=3666
```

Этот snapshot остаётся reproducible compatibility reference, но не final AEB base и не
разрешение на real-AIFE mutation. Финальная интеграция требует fresh canonical AIFE reconciliation.

## Development lifecycle и canonical quality boundary

Canonical toolchain остаётся обязательным финальным integration gate, но не является inner loop
активной Server разработки:

```text
CANONICAL_TOOLCHAIN_PER_DEVELOPMENT_ITERATION=NO
AEB_PER_DEVELOPMENT_ITERATION=NO
PORTABLE_PATCH_PER_DEVELOPMENT_ITERATION=NO
TARGETED_ENGINEERING_VALIDATION_DURING_DEVELOPMENT=YES
DOCKER_RUNTIME_VALIDATION_DURING_DEVELOPMENT=YES
SHADOW_SERVER_BEFORE_FINAL_CANONICALIZATION=YES
WORKING_SERVER_BEFORE_PATCH_SYSTEM=YES
FINAL_CANONICAL_PATCH_SYSTEM_REQUIRED=YES
FINAL_CANONICAL_TOOLCHAIN_REQUIRED=YES
FINAL_AEB_REQUIRED=YES
MAIN_INTEGRATION_ONLY_AFTER_FINAL_CANONICAL_PASS=YES
```

Будущий development loop:

```text
edit
→ targeted validation
→ commit
→ push AIFE WIP
→ Docker/runtime validation when applicable
→ next iteration
```

После owner-declared freeze функционально и физически квалифицированного server contour:

```text
WORKING_SERVER_CONTOUR
→ exact Git freeze
→ canonical patch system
→ AIFE quality normalization
→ canonical toolchain
→ Candidate
→ Owner Authorization
→ AEB
→ receiver qualification
→ canonical AIFE main integration
```

Нельзя откладывать до toolchain runtime/architecture defects: data loss, duplicate processing,
wrong Work identity, broken idempotency/claim/lease/fencing/concurrency/ACK/restart/recovery,
storage corruption, provider/domain leakage, unsafe backpressure или non-scalable owner boundary.
Нессемантический style/typing/lint/docstring/metadata cleanup может завершаться на final
canonicalization boundary, если не влияет на correctness, safety или clarity.

## Текущая точка программы

F0–F4 и F5R/F5P — historical/satisfied lineage. F5 implementation уже опубликован и технически
квалифицирован; real AIFE integration и production activation не выполнялись. Текущий frontier —
F5C planning.

```text
CURRENT_PROGRAM_FRONTIER=F5C_GENERIC_ACQUISITION_COLLECTION_RUNTIME_INTEGRATION_PLANNING
F5R_ARCHITECTURE_RESEARCH=COMPLETE
F5P_WORKSPACE_DEPLOYMENT_GOVERNANCE=COMPLETE
CANONICAL_C_TASK_ID=C-144
F5_TECHNICAL_QUALIFICATION=PASS
F5_PUBLISHED_WIP_HEAD=e6d35af62297a8d7c1119eae05c68df455091ea8
F5_PUBLISHED_WIP_TREE=9ce4b6a3ae593d32b5f48dd58c30531a7578effc
F5_QUALIFIED_FUTURE_AIFE_TREE=e617aaf2f45d6f253732f9b6019a88bf72ca74f7
F5_DOCKER_D01_D22=22/22_PASS
CURRENT_F5_RUNTIME_READINESS_STATUS=QUALIFIED_DISPOSABLE_DOCKER_PROFILE
CURRENT_F5_QUALIFICATION_STATUS=PASS
F5_REAL_AIFE_CANONICAL_INTEGRATION=NO
F5C_NEXT_PLANNING_STAGE=YES
F5C_STARTED=NO
F5M_ALLOWED=NO_UNTIL_QUALIFIED_F5C_FORWARD_COLLECTION
F5M_STARTED=NO
PRODUCTION_DEPLOYMENT_ALLOWED=NO
PRODUCTION_ACTIVATION=NO
PRODUCTION_CUTOVER=NO
AEB_CREATED=NO
AEB_GENERATION=NO
REAL_AIFE_MUTATION=NO
NEXT_OWNER_TASK=PLAN_F5C_GENERIC_ACQUISITION_AND_COLLECTION_RUNTIME_INTEGRATION+ESTABLISH_AIFE_SERVER_WIP_DEVELOPMENT_MODE
```

F5 не переписывается. F5C planning должен fresh определить canonical AIFE Git repository/base,
branch namespace и dedicated Server WIP, затем выполнить controlled exact qualified-F5 bootstrap.
Он также обязан определить first durable acceptance boundary, provider→durable-state loss window
и судьбу historical D8 spool; `provider response received` само по себе не считается durable AIFE
acceptance.

## Future AEB eligibility

`AIFE/integration/aeb-input-plan.json` описывает **future final canonical integration eligibility**,
а не текущий inner development workflow. Bounded F5 qualification не делает будущий полный Server
contour AEB-eligible автоматически.

```text
FINAL_AEB_ELIGIBILITY_REMAINS_FUTURE_GATE=YES
FINAL_COMPLETE_SERVER_CONTOUR_IMPLEMENTATION_COMPLETE=NO
FINAL_CANONICAL_TOOLCHAIN_PASS=NO
FINAL_AIFE_BASE_RECONCILIATION_PASS=NO
BOUNDED_PATCH_DECOMPOSITION_PASS=NO
FUTURE_AEB_ELIGIBLE=NO
```

## Workspace publication transport

Ниже описан только transport текущего Data Bridge F5 provenance/transition workspace. Он не является
будущим default development loop generic AIFE Server и не заменяет final AEB/canonical integration.

```text
WORKSPACE_PUBLICATION_TRANSPORT_POLICY=ACTIVE_FOR_DATA_BRIDGE_F5_PROVENANCE_TRANSITION
PUBLICATION_ROUTE_P1=SAME_ENVIRONMENT_NATIVE_FILE_BACKED_GIT
PUBLICATION_ROUTE_P2=OWNER_GITHUB_CODESPACES_RECEIVER
PUBLICATION_ROUTE_P3=FAIL_CLOSED_STOP

QUALIFIED_TOOLCHAIN_ENVIRONMENT_MAY_DIFFER_FROM_PUBLICATION_RECEIVER=YES
EXACT_BYTE_FREEZE_REQUIRED=YES
RECEIVER_EXACT_BYTE_VERIFICATION_REQUIRED=YES
EXACT_CHANGED_PATH_SET_REQUIRED=YES
INDEX_GIT_BLOB_VERIFICATION_REQUIRED=YES
ONE_PARENT_SUCCESSOR_REQUIRED=YES
LAST_MOMENT_REMOTE_RACE_CHECK_REQUIRED=YES
FORCE_PUSH_ALLOWED=NO
FORCE_WITH_LEASE_ALLOWED=NO
INDEPENDENT_POST_PUBLICATION_REMOTE_READBACK_REQUIRED=YES
```

P1 допустим только когда environment, владеющий frozen candidate, имеет required Git/network/auth
write capabilities и task contract разрешает publication. Если native route недоступен, отдельный
handoff допустим только если закрывает реальный byte-preservation risk; он не является обязательным
механизмом каждой будущей AIFE Git iteration.

```text
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_IS_AEB=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_IS_VERIFIED_HANDOFF=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_REPLACES_AEB=NO
CODESPACES_WORKSPACE_PUBLICATION_HANDOFF_REPLACES_CANONICAL_AIFE_PATCH_ROUTE=NO
```

Future canonical AIFE integration требует separately authorized final canonical route после
working/Docker/shadow qualification и exact Git freeze.
