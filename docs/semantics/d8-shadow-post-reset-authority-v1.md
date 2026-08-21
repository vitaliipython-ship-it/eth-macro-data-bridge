# D8 post-reset VPS_SHADOW authority reconciliation v1

## Назначение

Этот документ фиксирует current program/status view после завершённого owner-authorized forensic preservation, controlled shadow reset и deployment перехода. Machine repository status-snapshot authority — `contracts/d8-shadow-post-reset-status-v1.json`.

Это authority для program contract и reconciled physical status snapshot, **не** continuously refreshed live VPS probe. Live physical state authority остаётся server-side execution/readback и обязана быть заново прочитана перед любой следующей physical mutation или physical qualification.

Он не активирует D8/D9, не выполняет provider acquisition, не квалифицирует Publication Port и не меняет production authority.

## Принятый внешний physical result

```text
OLD_PRE_PRODUCTION_SHADOW_FORENSIC_PRESERVATION=PASS
OLD_PENDING_TOTAL=261
OLD_CHECKPOINT_V2_ELIGIBLE=62
OLD_LEGACY_PRE_CHECKPOINT_V2=199
OLD_PENDING_FORENSICALLY_PRESERVED=true
OLD_PENDING_RESTORE_AUTHORIZED=false

CONTROLLED_SHADOW_RESET=PASS
STATE_VOLUME_PRESERVED=true

CURRENT_D8_SOURCE=9336f75b4e6c49dcbc82252bc37a4bc45075f04f
CURRENT_D8_PROFILE=VPS_SHADOW
CURRENT_D8_RUNTIME=RUNNING_HEALTHY_NON_AUTHORITATIVE
CURRENT_STATE_SCHEMA_VERSION=2
CURRENT_SPOOL_TOTAL=0
CURRENT_PENDING_TOTAL=0
CURRENT_FORWARDED_TOTAL=0
NORMAL_PROVIDER_ACQUISITION_AFTER_RESET=NOT_RUN
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=false
```

`CURRENT_D8_RUNTIME` и `CURRENT_*` counts выше — reconciled snapshot values в принятой external observation point, а не continuous live assertions.

Старые `261` PENDING сохранены как forensic evidence до reset. Они не являются текущим live SPOOL и их restore не авторизован.

## Snapshot provenance и live-state boundary

```text
STATUS_SEMANTICS=RECONCILED_PHYSICAL_SNAPSHOT_NOT_LIVE_PROBE
LIVE_RUNTIME_STATUS_CONTINUOUSLY_VERIFIED=false
LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_MUTATION=true
LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_QUALIFICATION=true
SNAPSHOT_TIME_SEMANTICS=EXTERNAL_EXECUTION_TIMESTAMP_NOT_REPOSITORY_AUTHORITY

DATA_BRIDGE_REPOSITORY_AUTHORITY=PROGRAM_CONTRACT_AND_RECONCILED_STATUS
SERVER_EXECUTION_AUTHORITY=LIVE_PHYSICAL_STATE_READBACK
RECONCILED_STATUS_SNAPSHOT_IS_LIVE_PROBE=false
REPOSITORY_STATUS_CAN_AUTHORIZE_PHYSICAL_MUTATION_WITHOUT_LIVE_READBACK=false
LIVE_VPS_PATH_OR_FILESYSTEM_IS_SEMANTIC_MARKET_DATA_AUTHORITY=false

SERVER_SSOT_CLOSURE_HEAD=81522acededc94d52b4c73b8d6c254bd012a3034
SERVER_SSOT_CLOSURE_TREE=19f6edfcd7bf745ed099d1509782cf87ea857b29
EXECUTION_EVIDENCE_SHA256=f4ab6d04d59e41db05cef476502b9be405d9b36d89654f44c439bc74646b60e9
FORENSIC_DB_SHA256=8be1971e2a5f20ac2c00f57e3a1fc18cc973acca85f8cd06dfa14623351a9769
PENDING_STATE_FINGERPRINT_SHA256=d80197463db61ea2b3acce11094a4a3b7b0556a029711fb65a3994cbd1958177
```

Эти anchors — provenance/evidence bindings, а не semantic market-data authority. Repository-bound evidence не содержит authoritative execution observation timestamp, поэтому timestamp не изобретается.

## Current program frontier

```text
OLD_PRE_PRODUCTION_SHADOW
→ FORENSIC_PRESERVATION          COMPLETE
→ CONTROLLED_SHADOW_RESET        COMPLETE
→ CURRENT_D8_DEPLOYMENT          COMPLETE
→ CLEAN_VPS_SHADOW               COMPLETE
→ NEW_REAL_CHECKPOINT_V2_DATA    NEXT
→ PHYSICAL_PUBLICATION_PORT      PENDING
→ ACTIVATION                     NOT_AUTHORIZED
```

Следующий physical step — только создание нового current-generation evidence:

```text
current D8 VPS_SHADOW
→ explicit real provider collection
→ new current-generation checkpoint-v2 evidence
→ non-zero eligible PENDING
→ STOP
```

Перед этим step исполнитель обязан выполнить fresh live server readback. Committed repository snapshot не может сам по себе авторизовать physical mutation или считаться proof текущего live VPS state.

После STOP canonical Publication Port physical qualification требует отдельной owner authorization. Она не является частью этого reconciliation.

## Publication credential boundary

```text
D8_RUNTIME_AUTH=D8_RUNTIME_TOKEN
GITHUB_TOKEN_REQUIRED_INSIDE_D8_RUNTIME=false
PUBLICATION_CREDENTIALS_OWNER=SEPARATELY_AUTHORIZED_PUBLICATION_EXECUTOR_OR_ADAPTER
PUBLIC_D8_INGRESS_REQUIRED=false
```

`GITHUB_FIRST_V1` — current Publication Port backend profile, но это не означает, что D8 runtime должен владеть GitHub publication credentials. D8 VPS_SHADOW остаётся private authenticated runtime.

## Authority invariants

```text
D8_ACTIVE=false
D9_ACTIVE=false
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
VPS_IS_MARKET_DATA_AUTHORITY=false
LEGACY_GITHUB_PRODUCTION_ACQUISITION_ACTIVE=true
PRODUCTION_WARM_FORWARDER_DEPLOYED=false
PHYSICAL_VPS_D8_TO_D9_QUALIFIED=false
CROSS_TIER_SEMANTIC_READ_QUALIFIED=false
PRODUCTION_CUTOVER=false
PROVIDER_AUTHORITY_TRANSITION=false
POSTGRES_IMPLEMENTATION_NOW=false
PUBLIC_D8_INGRESS_REQUIRED=false
```

## Source и historical binding classification

`contracts/d8-runtime-candidate.json` остаётся source/runtime behavior contract. Его source-candidate/deployment labels не являются current VPS physical-status SSOT после отдельного server execution.

`docs/semantics/d8-vps-unified-acquisition-runtime-v1.md` остаётся implementation-facing source semantics и не переписывается под каждый deployment transition.

`docs/handoffs/d8-vps-runtime-integration-handoff-v1.md` сохраняется byte-for-byte как historical exact-source handoff. Его старые source SHA / schema-v1 / not-deployed labels являются historical binding, а не current deployment status.

Current reconciled physical/program status snapshot authority после этого reconciliation задаётся `contracts/d8-shadow-post-reset-status-v1.json` вместе с current program surfaces (`AGENTS.md`, forwarding contract и D9/storage status docs). Live VPS state authority остаётся server-side readback.

## Границы этой task

```text
PROVIDER_ACQUISITION_PERFORMED=NO
VPS_MUTATION=NO
N8N_MUTATION=NO
PHYSICAL_PUBLICATION_PORT_QUALIFICATION=NO
PRODUCTION_CUTOVER=NO
```

Никакие volatile VPS filesystem paths не кодируются как semantic authority.
