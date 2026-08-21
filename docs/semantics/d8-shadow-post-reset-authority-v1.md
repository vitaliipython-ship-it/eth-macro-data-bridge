# D8 post-reset VPS_SHADOW authority reconciliation v1

## Назначение

Этот документ фиксирует current program/status view после завершённого owner-authorized forensic preservation, controlled shadow reset и deployment перехода. Machine status authority — `contracts/d8-shadow-post-reset-status-v1.json`.

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

Старые `261` PENDING сохранены как forensic evidence до reset. Они не являются текущим live SPOOL и их restore не авторизован.

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

Current physical/status authority после этого reconciliation задаётся `contracts/d8-shadow-post-reset-status-v1.json` вместе с current program surfaces (`AGENTS.md`, forwarding contract и D9/storage status docs).

## Границы этой task

```text
PROVIDER_ACQUISITION_PERFORMED=NO
VPS_MUTATION=NO
N8N_MUTATION=NO
PHYSICAL_PUBLICATION_PORT_QUALIFICATION=NO
PRODUCTION_CUTOVER=NO
```

Никакие volatile VPS filesystem paths не кодируются как semantic authority.
