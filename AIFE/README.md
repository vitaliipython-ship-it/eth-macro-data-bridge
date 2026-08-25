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
CANONICAL_COMPATIBILITY_VALIDATION=PASS
FUTURE_AEB_INPUTS=READY
AIFE_DELIVERY_STATUS=CONTROL_PLANE_ONLY_DELIVERY_BLOCKED
PHYSICAL_DELIVERY=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
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
- `docs/98-Reviews/execution/2026-08/aife-server-data-foundation/README.md`;
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

## Целевое состояние данных и планирования

После готовности и квалификации серверной и информационной основы AIFE физический
корпус рыночных данных должен перейти под управляемый AIFE жизненный цикл хранения.
Это не устраняет `Data Bridge`: он сохраняет полномочия на семантику ETH, правила
поставщиков, идентичность, нормализацию, проверку, финальность и правила разрешения.
Целевой физический контур хранения при этом не должен оставаться основной ролью
`Data Bridge`.

```text
DATA_BRIDGE_DOMAIN_AUTHORITY_AFTER_MIGRATION=YES
DATA_BRIDGE_TARGET_PHYSICAL_WAREHOUSE=NO
DATA_BRIDGE_EXISTING_CORPUS_MIGRATION_TARGET=YES
DATA_BRIDGE_GROWING_CORPUS_MIGRATION_TARGET=YES
MIGRATION_EXECUTED=NO
LEGACY_READABILITY_PRESERVED=YES
CURRENT_PRODUCTION_ROUTE_CHANGED=NO
```

Предпочтительный будущий порядок: сначала квалифицировать публикацию новых входящих
данных в управляемое AIFE хранилище, затем выполнять контролируемое перенесение
накопленной истории с независимым чтением и доказательством полноты. Удаление прежних
байтов до доказательства переноса запрещено.

Периодические единицы серверной работы в целевом состоянии планируются общим механизмом
AIFE Server, а домен определяет семантику наступления срока. `n8n` может применяться для
внешней автоматизации, уведомлений и бизнес-процессов, но не является каноническим
планировщиком работы AIFE.

```text
AIFE_SERVER_OWNS_GENERIC_SCHEDULING=YES_CANDIDATE
DOMAIN_OWNS_DUE_POLICY_SEMANTICS=YES
N8N_CANONICAL_SCHEDULER=NO
N8N_REQUIRED_FOR_PERIODIC_COLLECTION=NO
SCHEDULER_IMPLEMENTED=NO
```

## Стандарты и обязательные шлюзы соответствия

Пакет теперь также фиксирует будущий порядок выравнивания стандартов и проверки
соответствия. Шесть текущих стандартов данных AIFE имеют статус `draft` и должны пройти
отдельное рассмотрение владельцем после канонической интеграции архитектуры, но до F2.
Утверждённые стандарты API, безопасности и журналирования, напротив, являются ограничениями
будущей реализации и применяются по умолчанию, если отдельный проверенный случай не требует
решения владельца об изменении стандарта.

```text
DATA_STANDARDS_ALIGNMENT_REQUIRED=YES
DATA_STANDARDS_ALIGNMENT_EXECUTED=NO
API_STANDARDS_COMPLIANCE_REQUIRED=YES
SERVER_SECURITY_COMPLIANCE_REQUIRED=YES
SERVER_LOGGING_COMPLIANCE_REQUIRED=YES
SEMANTIC_CONTRACT_FIRST=YES
TRANSPORT_SELECTED=NO
NEW_SERVER_STANDARD_CREATED=NO
DATA_STANDARDS_ARE_NOT_AUTO_PRODUCTION_AUTHORITY=YES
SERVER_DOMAIN_GOVERNANCE_SEPARATE=YES
NO_STANDARD_MUTATION_NOW=YES
NO_IMPLEMENTATION_NOW=YES
MIGRATION_SCHEDULING_DECISIONS_PRESERVED=YES
```

Стандарты не заменяют ADR и `Artifact Contract`: ADR фиксирует архитектурное решение,
стандарты задают общие обязательные правила, а контракты задают точные границы данных и
исполнения. Новые `STD-SERVER-*` по умолчанию не создаются.

## Текущая граница будущей интеграции

```text
PHASE_A_STAGING_OWNER_INTEGRATION=PASS_PR_222_MERGED
CURRENT_STAGE=PRE_AEB_CANONICAL_ARTIFACT_PREPARATION
CURRENT_STAGING_PR=228_DRAFT_NO_MERGE
FUTURE_INSTALL_ROUTE=VERIFIED_HANDOFF
FUTURE_AEB_TASK_CONTRACT_REQUIRED=YES
FUTURE_OWNER_AUTHORIZATION_REQUIRED=YES
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
STAGING_PR_OPEN_BRANCH_IS_NOT_DURABLE_AIFE_HANDOFF_AUTHORITY=true
```

`integration/aeb-input-plan.json` фиксирует прямые future inputs, намерение регистрации ADR,
generator-owned projections и обязательные receiver validation actions. Следующий отдельный
owner-authorized этап должен подготовить Task Contract / authorization / AEB; этот staging
контур не начинает F1/F2/F3 и не выполняет физическую интеграцию.

## Вспомогательные файлы без собственных полномочий

- `README.md` — только навигация;
- `integration/authority-binding.json` — точная привязка к исходной полномочной базе;
- `integration/manifest.json` — указатель промежуточного пакета для интеграции владельцем, **не реестр**;
- `integration/aeb-input-plan.json` — machine-readable модель будущих direct inputs, registration intent, generator actions и validation gates;
- `evidence/planning-package-readback.md` — доказательства проверки для чтения.

## Явные нецели

Нет серверного исполнения, реализации планировщика, потока `n8n`, миграции данных, базы данных, `Object Storage`, `Parquet`, P2, возобновления R2, активации боевого режима, изменения текущего маршрута сбора данных, изменения рабочей области AIFE, копий стандартов AIFE, копий реестров или копии исходного кода ETH.
