---
id: STD-DATA-RETENTION-001
domain: DATA
version: 0.3.0
title: STD-DATA-RETENTION-001 — Data Retention Policy
status: draft
owner: AIFE Standards Team
created: 2025-10-19
updated: 2026-08-27
tags: [data, retention, archival, retirement, purge, recoverability, compliance, P1]
category: standards
review_cycle_days: 180
next_review_due: 2027-02-23
doc_type: standard
language: ru
priority: P1
enforcement: Manual
related:
  - genome/standards/data/STD-DATA-MGMT-001.md
  - genome/standards/data/STD-DATA-MIGRATION-001.md
  - genome/standards/data/STD-DATA-BACKUP-001.md
  - docs/50-Security/README.md
phase: 2
---

# STD-DATA-RETENTION-001 — Data Retention Policy

**Статус:** 📝 **DRAFT**
**Версия:** 0.3.0
**Owner:** AIFE Standards Team

## 🧭 Карта смысловых блоков

| Смысловой блок | Носитель владельца | Класс `route-back` | Назначение |
| --- | --- | --- | --- |
| `identity_core` | YAML front matter | `artifact-level` | Идентичность стандарта |
| `lifecycle_roles` | `## Логические lifecycle roles` | `block-level` | HOT/WARM/COLD/ARCHIVAL/RETIREMENT/PURGE |
| `retention_policy` | `## Retention policy contract` | `block-level` | Policy без universal age hard-code |
| `purge_gates` | `## Retirement и purge gates` | `block-level` | Authority/recoverability/migration/legal gates |
| `authority_boundary` | `## Граница полномочий` | `block-level` | Domain policy vs physical lifecycle |

## Назначение

Стандарт определяет logical retention lifecycle и условия физического retirement/purge.
Возраст данных сам по себе никогда не является достаточным разрешением на удаление.

## Граница полномочий

Этот стандарт определяет **общие** требования AIFE к данным и физическому жизненному
циклу. Физическое размещение, durable storage или исполнение не создают доменную
семантическую власть.

```text
AIFE_OWNS=GENERIC_EXECUTION+GENERIC_SCHEDULING+GENERIC_WORK_OWNERSHIP+GENERIC_DURABLE_RUNTIME_STATE+GENERIC_PUBLICATION_LIFECYCLE+GENERIC_STORAGE_LIFECYCLE+GENERIC_ACCESS_MECHANISMS+GENERIC_SERVER_OPERATIONS
ETH_DATA_BRIDGE_OWNS=MARKET_DATA_SEMANTICS+PROVIDER_SEMANTICS+DOMAIN_IDENTITIES+NORMALIZATION+VALIDATION+FINALITY+GAP_REVISION_RULES+DOMAIN_RESOLUTION_RULES
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
AIFE_PHYSICAL_STORAGE_IS_ETH_SEMANTIC_AUTHORITY=NO
PHYSICAL_LOCATION_DEFINES_DOMAIN_TRUTH=NO
```

Для других доменов действует тот же принцип: generic AIFE mechanisms не подменяют
domain-owner semantics.

## Логические lifecycle roles

```text
HOT
WARM
COLD
ARCHIVAL
RETIREMENT
PURGE
```

| Роль | Общий смысл |
| --- | --- |
| `HOT` | активно используемый слой с требованиями низкой задержки, если они есть |
| `WARM` | доступный durable слой для обычного чтения/истории |
| `COLD` | редко используемый durable слой с более дорогим/медленным доступом |
| `ARCHIVAL` | долгосрочно сохраняемый слой с обязательной identity/integrity/recoverability |
| `RETIREMENT` | состояние, где revision/physical route больше не активен, но ещё не обязательно удалён |
| `PURGE` | необратимое физическое удаление после всех разрешающих gates |

Роль не выбирает конкретную технологию и не переносит semantic authority.

## Retention policy contract

Для каждого data class политика должна определить применимые:

```text
DATA_CLASS
DOMAIN_OWNER
RETENTION_OBJECTIVE
MINIMUM_REQUIRED_WINDOW
MAXIMUM_ALLOWED_WINDOW_IF_APPLICABLE
LEGAL_OR_POLICY_HOLD_RULES
TIER_TRANSITION_RULES
MIGRATION_BLOCKERS
RECOVERABILITY_REQUIREMENTS
RETIREMENT_GATE
PURGE_GATE
```

Не существует одного универсального набора дней для всех типов данных.

```text
RETENTION_IS_NOT_AUTOMATIC_DELETE_BY_AGE=YES
```

Domain owner может требовать более длительное сохранение, специфические finality/revision
windows или запрет purge. Generic AIFE policy не должна уменьшать эти требования.

## Tier transition

Переход `HOT → WARM → COLD → ARCHIVAL` может менять physical performance/cost profile,
но должен сохранять применимые:

- stable identity;
- integrity;
- provenance;
- required query/access capability;
- read-back proof;
- domain semantics;
- migration/cutover traceability.

Tier transition не является authority cutover сам по себе.

## Retirement и purge gates

`RETIREMENT` разрешён только если:

- соответствующий active route/revision больше не требуется;
- migration/cutover state не требует legacy readability;
- rollback window/target не опирается на retiring bytes;
- legal/policy hold отсутствует или явно разрешает transition;
- backup/restore policy не требует сохранить source как recoverability anchor.

`PURGE` разрешён только после отдельного gate:

```text
PURGE_REQUIRES_AUTHORITY_AND_RECOVERABILITY_GATE=YES
MIGRATION_OR_CUTOVER_STATE_CAN_BLOCK_RETIREMENT=YES
RESTORABILITY_CAN_BLOCK_PURGE=YES
```

Минимально проверяются:

```text
PURGE_GATE=
AUTHORITY_PASS
+ RETENTION_POLICY_PASS
+ LEGAL_HOLD_CLEAR
+ MIGRATION_CUTOVER_PASS
+ ROLLBACK_DEPENDENCY_CLEAR
+ RECOVERABILITY_PASS
+ IDENTITY_MATCH
```

Удаление до доказанного migration parity запрещено согласно
`STD-DATA-MIGRATION-001`.

## Legal/compliance boundary

Правовые и privacy требования могут устанавливать обязательный purge или минимальный
retention. Этот стандарт не заменяет security/privacy/legal owner. При конфликте
применяется более строгий разрешённый owner-policy route с явным evidence.

## Backup relation

Backup не является способом бесконечно обходить purge policy: retention должна
распространять owner decision на применимые backups, но фактический purge backup
допустим только при сохранении требуемой recoverability и compliance.

И наоборот, наличие backup не доказывает restorability; это определяет
`STD-DATA-BACKUP-001`.

## Publication relation

Retention не изменяет publication status задним числом. Канонически опубликованная
identity остаётся трассируемой даже после tiering/retirement в рамках требований
governance/audit. Standard не создаёт вторую publication state machine.

## Immutable generation retention и compaction

Канонические immutable generations не переписываются destructive in-place. Compaction,
repartitioning или layout optimization создаёт новую generation через copy-on-write,
сохраняет predecessor/manifest traceability и проходит publication/readback gates до
переключения current generation.

```text
DESTRUCTIVE_IN_PLACE_CANONICAL_REWRITE=FORBIDDEN
COMPACTION_MODEL=COPY_ON_WRITE_NEW_GENERATION
OLD_GENERATION_GC_BEFORE_NEW_GENERATION_PROOF=FORBIDDEN
```

Garbage collection старой generation разрешается только после retention, migration/cutover,
rollback, legal/policy hold и recoverability gates. Возраст или факт существования новой
копии сами по себе не разрешают удаление.

## Независимость от конкретной реализации

Ни один vendor, storage engine, queue, object store, database или scheduler transport
не является нормативно выбранным этим стандартом. Текущая Server/Data architecture уже
опубликована владельцем в `ADR-DATA-FOUNDATION-001`; этот стандарт не переоткрывает
исторические F3 selection gates и не выбирает product/vendor.

```text
VENDOR_NEUTRALITY=YES
DATABASE_VENDOR_SELECTED=NO
STORAGE_ENGINE_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
STANDARD_DOES_NOT_SELECT_PRODUCT_VENDOR=YES
STANDARD_DOES_NOT_OVERRIDE_ACTIVE_ADR=YES
SERVER_DATA_ARCHITECTURE_OWNER=ADR-DATA-FOUNDATION-001
PRODUCT_SELECTION_REMAINS_F5_QUALIFICATION_BOUND=YES
```

Конкретные adapters/products выбираются и квалифицируются только в последующем
owner-authorized F5 contour в рамках active ADR. Measurement-bound параметры и deferred
products не превращаются этим стандартом в mandatory dependencies.

## Проверка retention policy

- data class и owner известны;
- age rule не используется как единственный purge trigger;
- migration/cutover/rollback blockers учтены;
- legal holds учтены;
- recoverability доказуема;
- purge имеет отдельное authority decision;
- physical tier не меняет domain semantics.

## Changelog

- **2026-08-27:** currentized Server/Data architecture ownership to
  `ADR-DATA-FOUNDATION-001`; historical F3 selection gates are no longer current authority.
- **2026-08-27:** добавлены F5R rules для immutable generations, copy-on-write compaction
  и запрета premature generation GC/destructive rewrite.
- **2026-08-26:** retention отделён от purge; введены generic lifecycle roles,
  migration/cutover/recoverability blockers и запрет universal age-based deletion.
- **2025-10-19:** первоначальный draft.
