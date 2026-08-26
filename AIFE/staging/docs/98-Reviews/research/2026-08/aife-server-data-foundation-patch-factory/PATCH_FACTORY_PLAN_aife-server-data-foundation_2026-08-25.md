---
title: "AIFE Server/Data Foundation — многоволновая стратегия разработки патчами"
status: draft
owner: Architecture Lead
created: 2026-08-25
updated: 2026-08-25
category: architecture
doc_type: analysis
language: ru
tags: [server, data, patch-factory, waves, recovery, verified-handoff]
authority_reference:
  - ../../../../../AGENTS.md
  - ../../../../../AGENTS_ARTIFACTS.md
  - ../../../../../AGENTS_PATCH_GUIDE.md
  - ../../../../../.aife/file_placement_rules.json
  - ../../../../../scripts/dev/verified_patch_handoff/scope_budget.py
  - ../../../../../.aife/schemas/verified_patch_handoff_manifest.schema.json
related:
  - README.md
---

# AIFE Server/Data Foundation — многоволновая стратегия разработки патчами

## Статус и физическое назначение

```text
PROGRAM=AIFE_SERVER_DATA_FOUNDATION
PATCH_FACTORY_MODEL=SNAPSHOT_DRIVEN_INCREMENTAL_PATCH_LINEAGE
physical-use class=agent-operator-workflow-improvement
PLANNING_ONLY=true
NO_CANONICAL_EXECUTION_AUTHORIZATION=true
NO_SERVER_RUNTIME_DELIVERY=true
```

Этот документ является долговременной инструкцией для будущих агентов генерации патчей.
Он предотвращает создание чрезмерно больших кандидатов, превышение канонических лимитов
путей, потерю границ волн, случайную работу в реальной рабочей области владельца, зависимость
архитектуры от контекста чата, преждевременную привязку к финальной базе и прямое создание
AEB до обязательной сверки.

Документ сам по себе не поставляет серверное исполнение и не открывает активный контур
`docs/98-Reviews/execution/**`.

## 1. Основа разработки

Текущая предварительная линия начинается от независимо проверенного неизменяемого снимка проверки (`review snapshot`):

```text
AIFE_REVIEW_PACKAGE=AIFE_review_latest.zip
AIFE_REVIEW_PACKAGE_SHA256=c8a019b373964405e52b5899608d24b734ab3986eefb2c58886ee6fdb444a5a0
BASE_HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
BASE_TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
TRACKED_PATH_COUNT=3666
WORKTREE_CLEAN=true
DEVELOPMENT_ON_REAL_AIFE_WORKSPACE=NO
PERMANENT_SECOND_CLONE=NO
SOURCE_SUBSTRATE=IMMUTABLE_AIFE_REVIEW_SNAPSHOT
TEMPORARY_MATERIALIZATION=DISPOSABLE_ONLY
PATCH_IS_DURABLE_SOURCE_DELTA=YES
```

Временное развёртывание снимка разрешено только как уничтожаемая среда изменения и проверки.
Оно не является канонической рабочей областью, не является полномочным источником проекта и не
должно превращаться в постоянный второй клон (`clone`). После замораживания патча и набора восстановления (`recovery`) такую среду
можно удалить.

Пути вида `E:\AIFE_Ecosystem\AIFE` и `E:\AIFE_Ecosystem\AIFE-transfer` относятся к
отдельному контуру приёмки и установки у владельца и не являются основой текущей разработки
патчей.

## 2. Канонический цикл одной волны

```text
IMMUTABLE_BASE_SNAPSHOT
→ DISPOSABLE_MATERIALIZATION
→ APPLY_PREDECESSOR_WIP_STATE
→ PRE_MUTATION_OPERATION_MAP
→ IMPLEMENT_ONE_BOUNDED_WAVE
→ TARGETED_STATIC_VALIDATION
→ CANONICAL_VALIDATORS
→ FREEZE_INCREMENTAL_PATCH
→ FREEZE_CUMULATIVE_WIP_RECOVERY
→ INDEPENDENT_IDENTITY_READBACK
→ DISCARD_DISPOSABLE_ENVIRONMENT
→ NEXT_WAVE
```

Каждая волна обязана иметь точную идентичность предшественника (`predecessor`). Следующий патч нельзя переносить
на «примерно тот же» tree или скрыто менять базу между волнами.

## 3. Две параллельные формы состояния

### 3.1. Накопительная линия WIP

```text
BASE
+
WAVE_01
+
WAVE_02
+
...
+
WAVE_N
=
CURRENT_PROVISIONAL_WIP_RESULT
```

Накопительное состояние WIP нужно для полного восстановления, исследования совокупного
результата и последующей сверки после изменения канонического `main`.

### 3.2. Инкрементальные волны установки

```text
BASE_0
→ PATCH_01
→ TREE_01

TREE_01
→ PATCH_02
→ TREE_02

TREE_02
→ PATCH_03
→ TREE_03
```

Инкрементальная цепочка нужна для будущей ограниченной канонической интеграции. Каждый
`PATCH_N` обязан быть рассчитан именно относительно `TREE_(N-1)`.

## 4. Канонические лимиты области

Fresh-read `scripts/dev/verified_patch_handoff/scope_budget.py` задаёт абсолютный предел
`128` канонических операций. Rename использует два физических носителя пути, поэтому
физический точный набор путей (`exact_path_set`) ограничен `2 * 128 = 256`, но это не расширяет бюджет операций.
Схема `verified_handoff` ограничивает размер патча значением `33554432` байт.

```text
VERIFIED_HANDOFF_CHANGED_PATH_MAX=128
EXACT_PATH_SET_MAX=256
PATCH_SIZE_MAX_BYTES=33554432
PROGRAM_TARGET_CHANGED_PATHS_PER_WAVE=60..100
PROGRAM_SOFT_WARNING_PATHS=>100
PROGRAM_HARD_PATH_STOP=>128
```

Ключевое различие:

```text
128=MAX_REAL_CHANGED_PATH_OPERATIONS_PER_VERIFIED_HANDOFF
256=MAX_PHYSICAL_EXACT_PATH_SET_CAPACITY_FOR_RENAME_CARRIERS
256_IS_NOT_ADDITIONAL_CHANGED_PATH_CAPACITY=true
```

Перед каждой исходной волной обязателен предварительный `operation map`.

## 5. Модель бюджета путей

Полный бюджет волны считается так:

```text
SOURCE_PATHS
+
TEST_PATHS
+
DOC_PATHS
+
GOVERNANCE_PATHS
+
REGISTRY_PATHS
+
GENERATED_PATHS
=
TOTAL_CHANGED_PATH_COUNT
```

Если `PROJECTED_TOTAL_CHANGED_PATHS > 100`, агент обязан проверить возможность смыслового
разделения. Если `PROJECTED_TOTAL_CHANGED_PATHS > 128`, выполнение останавливается с
`STOP_PATCH_PATH_LIMIT_EXCEEDED`.

Запрещено обходить превышение лимита исключением тестов, реестров или производных сопроводительных файлов
из расчёта. Все реально изменяемые пути входят в бюджет.

## 6. Начальная карта волн программы

Эта карта задаёт стартовую декомпозицию программы. Она может уточняться новыми доказательствами
из репозитория, но жёсткие лимиты, цепочка предшественников (`predecessor chaining`) и обязательная сверка сохраняются
независимо от точного числа волн.

| Волна | Этап программы | Планировочная граница |
| --- | --- | --- |
| `W0` | F0 | планирование и канонические полномочия основы F0 |
| `W1` | F1 | актуализация архитектуры |
| `W2` | Data Standards Alignment | решение по действующим стандартам данных до F2 |
| `W3` | F1G | регистрация управленческого домена `SERVER` |
| `W4` | F2 | контракт Work / Scheduling |
| `W5` | F2 | контракт публикации (`Publication`) |
| `W6` | F2 | контракт доступа (`Access`) |
| `W7` | F3 | ядро Server, корень исходников и жизненный цикл процесса |
| `W8` | F3 | исполнение, планирование и устойчивое состояние работы |
| `W9` | F3 | механизмы публикации, хранения и доступа |
| `W10` | F4 | интеграция адаптера ETH Data Bridge |
| `W11+` | F5 | P2: физический жизненный цикл высококардинальных данных; дробить при необходимости |
| `W12+` | F5M | миграция существующего и растущего корпуса данных; дробить при необходимости |
| `W13+` | F6 | приёмка потребителя |
| `W14+` | F7 | теневая VPS-квалификация, горизонтальное масштабирование, перезапуск и длительная проверка |
| `W15+` | F8 | атомарная производственная активация, стабилизация, вывод прежнего физического хранилища (`legacy physical warehouse`) и сквозное закрытие E2E |

```text
SEMANTIC_COHERENCE_BEATS_FIXED_WAVE_COUNT=YES
PATH_LIMIT_BEATS_DESIRE_TO_KEEP_ONE_STAGE_ONE_PATCH=YES
```

Номер волны может увеличиваться без изменения протокола: одна волна остаётся ограниченной
смысловой единицей с собственными `operation map`, патчем, деревом результата (`result tree`) и набором восстановления (`recovery`).

## 7. Граница F0 / D-380

```text
D380=F0_CANONICAL_EXECUTION_CONTOUR_BOOTSTRAP
D380_IS_NOT=WHOLE_F1_TO_F8_IMPLEMENTATION_TASK
D380_STATE=PROVISIONAL
D380_ACTIVE=NO
D380_ALLOWED_ONCE=NO
D380_IMPLEMENTATION_AUTHORIZATION=NO
```

Патчи F1+ можно предварительно разрабатывать заранее, но они не становятся каноническими
полномочиями реализации без соответствующего Task Contract и перехода авторизации владельца.
Этот планировочный артефакт не активирует `D-380`.

## 8. Параллельная работа с I-1071/I-1072

Текущая предварительная линия Server/Data строится от:

```text
HEAD=1ed138c06881aaebf8e650fcc020cef570e31b6d
TREE=11f5cbc5f81836dddf0e854d3685418b53f22852
SERVER_DATA_DEVELOPMENT_NOW=ALLOWED_PROVISIONAL
FINAL_CANONICAL_BASE_BINDING_NOW=FORBIDDEN
WAIT_FOR_I1071_I1072_BEFORE_FINAL_BASE_BINDING=true
```

После установки I-1071/I-1072 обязателен новый цикл:

```text
FRESH_AIFE_AUTHORITY
→ NEW_HEAD_AND_TREE
→ AUTHORITY_DRIFT_REVIEW
→ REPLAY_RECONCILE_CUMULATIVE_SERVER_DATA_WIP
→ REGENERATE_REGISTRY_AND_GENERATED_OUTPUTS
→ RERUN_CANONICAL_VALIDATIONS
→ REBUILD_INCREMENTAL_WAVE_CHAIN
→ ONLY_THEN_CANONICAL_AUTHORIZATION_AND_AEB
```

Старые предварительные `RESULT_TREE` нельзя считать финальными после изменения канонического
`main`. Если повторное применение выявляет смысловой конфликт, агент обязан остановиться и
разрешить его явно, а не скрыто подгонять патч.

## 9. Идентичности линии патчей

Для каждой предварительной волны разработки обязательно сохраняются:

```text
PROGRAM=AIFE_SERVER_DATA_FOUNDATION
LINEAGE=AIFE_SERVER_DATA_FOUNDATION_WIP
WAVE_ID=<wave>
BASE_HEAD=<sha>
BASE_TREE=<sha>
PREDECESSOR_RESULT_TREE=<sha>
CURRENT_RESULT_TREE=<sha>
INCREMENTAL_PATCH_SHA256=<sha256>
CUMULATIVE_WIP_PATCH_SHA256=<sha256>
OPERATION_MAP_SHA256=<sha256>
CHANGED_PATH_COUNT=<count>
PATH_CLASS_COUNTS=<source/tests/docs/governance/registry/generated>
VALIDATION_STATUS=<state>
RECOVERY_ID=<id>
```

Этого набора должно быть достаточно, чтобы продолжить работу без памяти чата.

## 10. Протокол восстановления

Для каждой устойчивой точки волны сохраняется логический набор:

```text
<lineage>_<wave>_WIP_RECOVERY_<revision>.zip
<lineage>_<wave>_WIP_RECOVERY_<revision>.zip.sha256
<incremental-patch>.patch
<incremental-patch>.patch.sha256
<machine-recovery-record>.json
<operation-map>.json
<validation-receipt>
```

Физическое место хранения является транспортной деталью конкретной среды выполнения и не
является архитектурным полномочием. Recovery не должен жёстко встраивать локальные пути
владельца в семантику программы.

## 11. Граница patch-factory / AEB

```text
PATCH_FACTORY=DEVELOPMENT_AND_CANDIDATE_GENERATION_MECHANISM
AEB=CANONICAL_AUTHORIZED_INSTALLATION_CARRIER
```

Цикл разработки:

```text
SOURCE_REPAIR
→ TARGETED_STATIC_PROOF
→ PATCH_FREEZE
→ RECOVERY
→ NEXT_WAVE
```

Будущий цикл канонической интеграции:

```text
FINAL_RECONCILED_CANDIDATE
→ OWNER_AUTHORIZATION
→ VERIFIED_HANDOFF
→ AEB
→ RECEIVER_EXECUTION
→ INDEPENDENT_FACTUAL_REVIEW
```

AEB не создаётся после каждого изменения исходников. Нельзя объединять всю программу
F1→F8 в один чрезмерно большой AEB.

## 12. Последовательная каноническая интеграция

Для каждой финальной волны интеграции:

```text
EXACT_PREDECESSOR_CANONICAL_HEAD_TREE
→ EXACT_OPERATION_MAP
→ BOUNDED_CANDIDATE
→ CANONICAL_VALIDATION
→ OWNER_AUTHORIZATION
→ VERIFIED_HANDOFF_OR_AEB
→ RECEIVER_EXECUTION
→ INDEPENDENT_FACTUAL_REVIEW
```

Если тот же канонический контур исполнения допускает следующую готовую волну, применяется
последовательный `owner_authorization_transition`: предыдущий `allowed_once` должен быть
`consumed`, после чего создаётся ровно один новый `allowed_once` для точного следующего
кандидата. На завершающей волне применяется `owner_authorization_finalize` согласно актуальным
полномочиям.

Авторизацию предыдущего патча нельзя переносить на новый патч и дерево результата (`result tree`).

## 13. Политика канонического quality toolchain

Текущая каноническая основа (`substrate`):

```text
TOOLCHAIN_PACKAGE_SHA256=36c64406c57f51c1dc810a64a3c1a599a39dce6f8a7d02ac1b9fd32a2ad5192d
TOOLCHAIN_ID=1b3f6d7281419ae7a692e9f3b69019c7ed13761ee51775ad8f37aa1f85b585eb
QUALITY_POLICY_ID=8c0004758ca1d5a6ddbf013a9a0069a927b9bf87fbb23cedd4f5927835d388b3
TOOLCHAIN_BUILD_COUNT=0
QUALIFICATION_BUILD_COUNT=0
BUILD_A_COUNT=0
BUILD_B_COUNT=0
```

Существующий `toolchain` используется как основа там, где это разрешено текущей границей
процесса. Новая ревизия WIP сама по себе не является причиной его пересборки.

Если дефект найден во время цикла разработки, исправляется исходник или кандидат (`source/candidate`), выполняются
целевые, статические и канонические проверки и создаётся новая ревизия кандидата. Toolchain
не перестраивается для маскировки дефекта исходников.

## 14. Будущий принцип полномочий исходников

```text
CANONICAL_AIFE_WORKSPACE=SOURCE_AUTHORITY_AT_OWNER_INSTALL_STAGE
AIFE_SERVER_SOURCE=FUTURE_CANONICAL_SUBTREE_WITHIN_AIFE
AIFE_SERVER_RUNTIME=DEPLOYED_PROJECTION_OF_QUALIFIED_SOURCE
SERVER_SIDE_MANUAL_SOURCE_DIVERGENCE=FORBIDDEN
```

Точная физическая структура будущего корня исходников Server определяется более поздними
полномочиями F1/F3. Этот документ её не создаёт.

## 15. Границы остановки и слияния (`merge`)

Для текущего планировочного кандидата:

```text
GITHUB_PR_MODE=DRAFT_ONLY
MERGE=NO
AIFE_MAIN_MUTATION=NO
D380_ACTIVATION=NO
F1_SOURCE_IMPLEMENTATION=NO
AEB_CREATED=NO
```

Для каждой будущей волны разработки остановка наступает после freeze инкрементального патча,
накопительного набора восстановления (`recovery`) и квитанции проверки (`validation receipt`). Для канонической интеграции точки остановки и
действия владельца определяют актуальные `Task Contract` и полномочия `handoff`.

До сверки после I-1071/I-1072 запрещено финально связывать Server/Data candidates с
канонической базой, авторизацией владельца (`owner authorization`) или AEB.
