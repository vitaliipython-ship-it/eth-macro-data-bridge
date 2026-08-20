# D8 runtime state evolution v1

## Назначение

Этот документ задаёт bounded policy эволюции D8 operational runtime state. Machine authority — `contracts/d8-runtime-candidate.json#state`; runtime implementation остаётся в `src/d8_runtime.py`. D8 SQLite WAL — operational delivery state, а не D9 history authority и не market-data semantic authority.

Текущий machine state:

```text
CURRENT_STATE_SCHEMA_VERSION=2
STARTUP_COMPATIBILITY=MIGRATE_V1_TO_V2_FAIL_CLOSED_OTHERWISE
CURRENT_IMPLEMENTED_TRANSITION=v1→v2
```

Существующий `v1→v2` migration уже реализован в `D8State._init_db`: он аддитивно создаёт checkpoint-v2 tables, сохраняет legacy state и не синтезирует checkpoint evidence. Повторный startup идемпотентен. Unsupported/unknown stored versions fail closed.

## Два разных класса изменений

`HORIZONTAL_DATA_EXPANSION` — новые pair/instrument/provider/capability/metric/timeframe/series или изменение cardinality вроде order-book depth `100→400`. Сам по себе этот класс **не требует** D8 state-schema migration. Payload schema, если меняется, versioned своим data contract.

`RUNTIME_STATE_CONTRACT_EVOLUTION` — изменение SQLite tables/columns, primary/idempotency identity, spool/ACK state semantics, checkpoint/provenance requirements, serialized operational state или обязательных persisted invariants. Только этот класс может требовать `STATE_SCHEMA_VERSION_BUMP` и versioned migration.

## Three-question decision gate

Любой новый compatibility/migration mechanism обязан ответить:

1. `RISK_CLOSED` — какой конкретный production/operational failure предотвращается?
2. `SIMPLER_SAFE_ALTERNATIVE` — можно ли закрыть тот же риск проще с теми же гарантиями?
3. `OPERATIONAL_COMPLEXITY_DELTA` — уменьшится ли число ручных действий, специальных процедур и forensic решений для следующего агента/инженера?

Допустимые verdicts:

```text
IMPLEMENT_MIGRATION
USE_SIMPLER_SAFE_PATH
NO_STATE_ACTION_REQUIRED
FAIL_CLOSED_REQUIRE_SEPARATE_DECISION
```

`"может пригодиться"` не является основанием для migration.

## Version и migration policy

```text
STORED_VERSION == CURRENT_VERSION
→ NORMAL_STARTUP

STORED_VERSION < CURRENT_VERSION
→ только explicit ordered supported chain vN→vN+1
→ если transition отсутствует: FAIL_CLOSED

STORED_VERSION > CURRENT_VERSION
→ FAIL_CLOSED
```

Запрещены schema guessing, destructive auto-recreate, silent downgrade/reset и implicit compatibility. Future chain состоит только из versioned deterministic `vN→vN+1` transitions; каждый transition обязан быть retry-safe/idempotent, fail-closed и tested.

Текущий supported transition остаётся ровно `1→2`; эта policy task не добавляет новый runtime migration mechanism.

## Pre-mutation evidence и post-migration validation

Перед любой mutating production migration обязательны:

```text
PRE_MIGRATION_BACKUP_REQUIRED=YES
PRE_MIGRATION_STATE_FINGERPRINT_REQUIRED=YES
PRE_MIGRATION_VERSION_READBACK_REQUIRED=YES
```

Physical backup/reset procedure принадлежит server layer. VPS path, Docker volume и filesystem locator не становятся semantic authority.

После migration и до runtime startup должны пройти минимум:

```text
STATE_SCHEMA_VERSION=CURRENT
SQLITE_INTEGRITY=PASS
PENDING_IDENTITIES_PRESERVED=PASS
PENDING_PAYLOAD_BINDING_PRESERVED=PASS
ACK_STATE_PRESERVED=PASS
NO_SILENT_PENDING_DROP=PASS
NO_DUPLICATE_PENDING=PASS
NO_SYNTHETIC_STATE=PASS
```

Любой FAIL означает `RUNTIME_START=FORBIDDEN`.

## PENDING preservation

`PENDING` — operational delivery state. Production upgrade не может молча удалить, skip/reseed, вручную ACK-нуть или заменить provider reacquisition. Если есть `PENDING` и persisted-state contract реально требует schema evolution, допустимы только validated migration или fail-closed stop. `PENDING→FORWARDED` и `CANONICAL_PUBLICATION_ACK` semantics не меняются.

## Pre-production shadow reset exception

Controlled reset допустим только как более простой safe path для **pre-production shadow** и только при одновременном доказательстве:

```text
D8_AUTHORITY_ACTIVE=false
D9_AUTHORITY_ACTIVE=false
PRODUCTION_CUTOVER=false
STATE_IS_HISTORY_AUTHORITY=false
STATE_CLASS=PRE_PRODUCTION_SHADOW
OWNER_RESET_AUTHORIZATION=EXPLICIT
FORENSIC_BACKUP_CREATED=YES
FORENSIC_INVENTORY_CREATED=YES
FORENSIC_SHA256_RECORDED=YES
```

Тогда verdict может быть `FORENSIC_BACKUP_AND_CONTROLLED_SHADOW_RESET`. Эта policy сама reset не авторизует и не исполняет; physical action принадлежит server layer.

## Classification examples

| Case | Classification | Result |
| --- | --- | --- |
| New trading pair | `HORIZONTAL_DATA_EXPANSION` | `NO_STATE_ACTION_REQUIRED` |
| Order-book depth `100→400`, persisted contract unchanged | `HORIZONTAL_DATA_EXPANSION` | `NO_RUNTIME_STATE_MIGRATION_REQUIRED` |
| New futures provider/capability, persisted shape unchanged | `HORIZONTAL_DATA_EXPANSION` | `NO_RUNTIME_STATE_MIGRATION_REQUIRED` |
| Spool/checkpoint persisted contract changes | `RUNTIME_STATE_CONTRACT_EVOLUTION` | `STATE_SCHEMA_VERSION_BUMP_AND_MIGRATION_DECISION_REQUIRED` |
| Incompatible non-authoritative pre-production shadow state with forensic backup | `PRE_PRODUCTION_SHADOW` | `SIMPLER_SAFE_PATH_MAY_BE_CONTROLLED_RESET` |
| Production `PENDING` incompatible after schema bump | `RUNTIME_STATE_CONTRACT_EVOLUTION` | `MIGRATE_OR_FAIL_CLOSED; RESET_NOT_DEFAULT` |

## Current forensic motivation

Current server investigation observed `261` real `PENDING`: `62` checkpoint-v2 eligible and `199` legacy pre-checkpoint blocked. Эти числа — forensic snapshot, не product logic и не compatibility contract.

Three-question verdict для этого specific pre-production case:

```text
RISK_CLOSED=preserve pre-production forensic state before reset
SIMPLER_SAFE_ALTERNATIVE=backup + controlled shadow reset
OPERATIONAL_COMPLEXITY_DELTA=lower than permanent legacy compatibility branch
SPECIAL_LEGACY_COMPATIBILITY_IMPLEMENTATION=NOT_REQUIRED_BY_THIS_TASK
PREFERRED_OPERATIONAL_PATH=FORENSIC_BACKUP_THEN_OWNER_AUTHORIZED_SHADOW_RESET
```

Этот PR не читает и не мутирует real VPS state, не реализует compatibility для legacy `199`, не выполняет reset/reseed/drop и не активирует D8/D9.
