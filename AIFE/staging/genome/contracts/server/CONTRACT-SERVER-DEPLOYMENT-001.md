---
id: CONTRACT-SERVER-DEPLOYMENT-001
domain: SERVER
title: "CONTRACT-SERVER-DEPLOYMENT-001: Immutable Release and Deployment Binding Contract"
version: "0.1.0"
status: draft
owner: Architecture Lead
created: 2026-08-28
updated: 2026-08-28
review_cycle_days: 180
next_review_due: 2027-02-24
category: standards
doc_type: contract
language: ru
tags: [contract, server, deployment, release, activation, rollback, receipt]
authority_reference:
  - genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - genome/standards/arch/STD-ARCH-001.md
  - genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - genome/adr/data/ADR-DATA-FOUNDATION-001.md
  - docs/98-Reviews/research/2026-08/aife-server-data-foundation/RESEARCH_CONSOLIDATED_aife-server-data-foundation_server-workspace-deployment-layout_2026-08-28.md
related:
  - genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
---

# CONTRACT-SERVER-DEPLOYMENT-001: Immutable Release and Deployment Binding Contract

## 1. Purpose

Зафиксировать reusable Server deployment binding от exact source revision до immutable
installed release, declared runtime roots, pre-activation validation, activation evidence,
upgrade и rollback без переноса Work/Storage/Publication или domain semantics в deployment.

Canonical relation:

```text
SOURCE_REVISION
→ IMMUTABLE_RELEASE + RELEASE_MANIFEST
→ INSTALLED_RELEASE
→ CONFIG_IDENTITY + DECLARED_PERSISTENT_ROOTS + CONTROL_BACKEND_IDENTITY
→ PRE_ACTIVATION_VALIDATION
→ ATOMIC_ACTIVATION
→ HEALTH_AND_READBACK
→ DEPLOYMENT_RECEIPT
→ UPGRADE_OR_EXPLICIT_ROLLBACK
```

## 2. Scope

В scope входят source/release identity, side-by-side installation, configuration identity,
persistent-root declaration, active control-backend discovery, mount/storage binding,
pre-activation validation, activation, deployment receipt, upgrade и rollback.

Вне scope: Work lifecycle, scheduling policy, claim/lease/fencing semantics, publication state
machine, generic storage lifecycle, access semantics, domain/ETH identity/finality,
object-storage product, Parquet sizing, PostgreSQL HA topology и backup vendor.

```text
DEPLOYMENT_OWNS_WORK_SEMANTICS=NO
DEPLOYMENT_OWNS_PUBLICATION_SEMANTICS=NO
DEPLOYMENT_OWNS_STORAGE_LIFECYCLE=NO
DEPLOYMENT_OWNS_DOMAIN_SEMANTICS=NO
PRODUCT_SELECTION_BY_DEPLOYMENT_CONTRACT=NO
```

## 3. Core Rules

A release is immutable after verification and installation. Runtime writes never target source
or installed release directories. Mutable state, config, secrets, spool, cache, bulk data and
logs use declared persistent roots independent from release identity.

```text
IMMUTABLE_RELEASE_MODEL=YES
DIRECT_PRODUCTION_EXECUTION_FROM_GIT_CHECKOUT=NO
PRODUCTION_UPDATE_BY_GIT_PULL=NO
RUNTIME_WRITES_TO_SOURCE_CHECKOUT=FORBIDDEN
RUNTIME_WRITES_TO_INSTALLED_RELEASE=FORBIDDEN
ACTIVATION_BEFORE_REQUIRED_VALIDATION=FORBIDDEN
ATOMIC_RELEASE_ACTIVATION=YES
```

Activation is eligible only after exact release digest, configuration identity, control
backend/schema compatibility, declared persistent-root/mount preflight, health and applicable
write/readback validation are proven.

A deployment never equates these identities:

```text
CODE_RELEASE_IDENTITY
!= CONTROL_SCHEMA_IDENTITY
!= CONFIG_IDENTITY
!= DATA_GENERATION_IDENTITY
```

## 4. Authority Model

- Source repository owns source revision identity and source architecture.
- Deployment contract owns binding of source revision to installed immutable release,
  declared operational roots, activation and deployment evidence.
- `server/application/**` owns application/use-case orchestration.
- `core/data/**` owns reusable repository/UoW/persistence adapter substrate for control state.
- Work/Execution/Publication contracts own the meaning of their durable control states.
- Storage contract owns generic physical object/storage lifecycle capabilities.
- Domain owner owns semantic identities/finality/validation.
- Deployment map is operational discovery/configuration authority, not domain semantic truth.
- Deployment receipt is execution evidence, not domain semantic truth.

Control-state transactional persistence and bulk object/blob storage remain separate recovery
and capability domains.

## 5. Naming Contract

Each deployment must use stable identities for:

```text
SOURCE_REVISION
RELEASE_ID
RELEASE_DIGEST
RELEASE_MANIFEST_ID
CONFIG_IDENTITY_OR_DIGEST
CONTROL_BACKEND_IDENTITY
CONTROL_SCHEMA_IDENTITY
DEPLOYMENT_ID
DEPLOYMENT_RECEIPT_ID
ROLLBACK_TARGET_RELEASE_ID_IF_APPLICABLE
```

`current` and `previous` filesystem links are activation pointers and must not be used as
release identity. A physical path or mount name is not data semantic identity.

## 6. Placement Contract

Canonical AIFE service layout:

```text
INSTALL_ROOT=/opt/aife
RELEASE_ROOT=/opt/aife/releases
CURRENT_RELEASE_POINTER=/opt/aife/current
PREVIOUS_RELEASE_POINTER=/opt/aife/previous
CONFIG_ROOT=/etc/aife
SECRET_ROOT=/etc/aife/secrets
STATE_ROOT=/var/lib/aife
CONTROL_DB_PATH=/var/lib/aife/control/aife-control.sqlite3
CHECKPOINT_ROOT=/var/lib/aife/checkpoints
SPOOL_ROOT=/var/spool/aife
INGEST_ROOT=/var/spool/aife/ingest
CACHE_ROOT=/var/cache/aife
DATA_ROOT=/var/lib/aife/data
OBJECT_ROOT=/var/lib/aife/data/objects
PARQUET_ROOT=/var/lib/aife/data/parquet
MANIFEST_ROOT=/var/lib/aife/data/manifests
QUARANTINE_ROOT=/var/lib/aife/quarantine
LOG_ROOT=/var/log/aife
DEPLOYMENT_MAP_PATH=/etc/aife/deployment-map.json
DEPLOYMENT_RECEIPT_ROOT=/var/lib/aife/deployments/receipts
DEPLOYMENT_RECEIPT_PATH=/var/lib/aife/deployments/receipts/<deployment-id>.json
```

```text
FHS_LAYOUT_MODEL=AIFE_SERVICE_LAYOUT
OPT_AIFE_IS_IMMUTABLE_RELEASE_CARRIER_ONLY=YES
STRICT_OPT_PACKAGE_PROJECTION_COMPLIANCE_CLAIMED=NO
DATA_ROOT_MAY_BE_DEDICATED_MOUNT=YES
ROOT_FILESYSTEM_COLOCATION_REQUIRED=NO
DATA_MOUNT_PREFLIGHT_REQUIRED=YES
FREE_SPACE_PREFLIGHT_REQUIRED=YES
```

## 7. Agent Rules

1. Do not run production directly from a source checkout or mutate a verified release.
2. Install a new release side-by-side and activate only after required validation.
3. Resolve active release, persistent roots and control backend through the deployment map,
   not filesystem guessing.
4. Never put control DB, bulk data, secrets or logs inside source/release directories.
5. Keep control-state persistence and bulk storage as separate capability/recovery domains.
6. Reuse canonical `core/data/**` repository/UoW/adapter substrate; do not create a second
   generic persistence framework under Server.
7. Do not create `server/control/**` merely for naming symmetry; exact thin binding is
   implementation-bound after the owner chain is fixed.
8. A dedicated bulk-data mount is allowed only when the deployment map declares its backing
   and preflight proves availability/capacity.
9. Containers may package execution but may not hide persistent authority in anonymous
   volumes.
10. Rollback requires explicit predecessor release and schema/config/data compatibility;
    silent database downgrade is forbidden.
11. Persist a deployment receipt for terminal install/upgrade/rollback evidence.
12. Never record secret values in release manifests, deployment maps intended for general
    readback, or deployment receipts.

## 8. Acceptance Criteria

The deployment binding is accepted only when:

- exact source revision and release digest are known;
- immutable side-by-side release installation is proven;
- configuration identity is explicit;
- all persistent roots and physical/mount backing are declared;
- active control backend/schema identity is discoverable;
- required mount/free-space/permission preflight passes;
- required schema compatibility/migration succeeds before activation;
- pre-activation health and applicable write/readback pass;
- activation is atomic or has explicit fail-safe semantics;
- deployment receipt records terminal evidence;
- rollback target and compatibility are explicit;
- source/release directories remain unmodified by runtime state;
- deployment does not change domain semantic identity.

## 9. Enforcement & Compliance

| Requirement | Enforcement Type | Control Mechanism | Owner | Check Frequency |
| --- | --- | --- | --- | --- |
| Immutable release and digest | Installer/integration | digest + readback proof | Server Operations | every deployment |
| Persistent-root separation | Static/integration | deployment-map validation | Server/Data owner | every deployment |
| Control backend discovery | Contract/integration | deployment-map readback | Server/Data owner | every deployment |
| Pre-activation gate | Integration | health/schema/write-readback checks | Server Operations | every activation |
| Rollback compatibility | Recovery test | explicit predecessor + schema/config checks | Server Operations | every rollback path change |
| No hidden container authority | Architecture/integration | declared mount inspection | Server Operations | every container profile change |
| Deployment receipt | Integration | durable receipt readback | Server Operations | every deployment |

## 10. Deployment map and receipt

`/etc/aife/deployment-map.json` must expose the current operational binding sufficiently for
an operator/agent to discover release roots, active release, config/secret/state/spool/cache/
data/log roots, active control backend/locator/schema and physical mount/storage binding.

The deployment receipt at
`/var/lib/aife/deployments/receipts/<deployment-id>.json` records source head/tree,
release identity/digest, config digest, control backend/schema, persistent-root bindings,
installation/migration/health/readback/activation results and rollback target if applicable.

Neither artifact creates domain semantic authority.

## 11. Install, upgrade and rollback lifecycle

Canonical install ordering:

```text
HOST_PREFLIGHT
→ SERVICE_ACCOUNT
→ DIRECTORY_LAYOUT
→ PERMISSIONS
→ MOUNT_AND_SPACE_PREFLIGHT
→ RELEASE_DIGEST_VERIFICATION
→ SIDE_BY_SIDE_IMMUTABLE_INSTALL
→ CONFIG_INSTALL
→ CONTROL_BACKEND_INIT
→ SCHEMA_COMPATIBILITY_OR_MIGRATION
→ SERVICE_REGISTRATION
→ PRE_ACTIVATION_VALIDATION
→ ATOMIC_ACTIVATION
→ HEALTH
→ WRITE_READBACK
→ DEPLOYMENT_RECEIPT
```

Upgrade follows the same side-by-side pattern. Rollback selects an explicit predecessor and
must fail closed when control schema/config/data compatibility cannot be proven.

```text
SILENT_DATABASE_DOWNGRADE=FORBIDDEN
ROLLBACK_TARGET_IDENTITY_REQUIRED=YES
```

## 12. Container and mount boundary

Containers are optional and cannot redefine deployment authority:

```text
CONTAINERS_REQUIRED_FOR_INITIAL_F5=NO
DOCKER_COMPOSE_IS_CANONICAL_SERVER_AUTHORITY=NO
ANONYMOUS_PERSISTENT_DOCKER_VOLUME_ALLOWED=NO
CONTAINER_HOST_MOUNTS_MUST_BE_DECLARED_IN_DEPLOYMENT_MAP=YES
```

The logical `DATA_ROOT` may be backed by a dedicated mount/shared qualified storage binding;
changing its physical backing does not change semantic identities or consumer contracts.

## 13. Failure, restart and recovery semantics

- interrupted installation leaves the new release inactive and restart/reconcile uses stable
  release/deployment identities;
- activation failure preserves/re-establishes the last accepted active release and emits
  failure evidence;
- missing/full data backing fails mount/space preflight or publication closed;
- control DB loss requires qualified restore and reconciliation before authority resumes;
- bulk-data corruption is handled by checksum/readback plus its own restore/rebuild policy;
- config mismatch blocks activation;
- rollback with incompatible schema blocks rather than downgrading silently;
- restart must resolve active release and backend through declared deployment state, not RAM.

```text
CONTROL_AND_BULK_RECOVERY_DOMAINS_SEPARATE=YES
BACKUP_EXISTS_EQUALS_RESTORE_PROVEN=NO
REPLICATION_EQUALS_BACKUP=NO
```
