---
title: "AIFE Server/Data Foundation — F1G: governance admission будущего server root"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
category: architecture
doc_type: report
language: ru
tags: [server, governance, f1g, packaging, quality, contracts]
authority_reference:
  - ../../../../../../AGENTS.md
  - ../../../../../../genome/standards/arch/STD-ARCH-001.md
  - ../../../../../../genome/standards/arch/STD-ARCH-PATTERNS-001.md
  - ../../../../../../genome/standards/governance/contract/STD-GOVERNANCE-CONTRACT-001.md
  - ../../../../../../pyproject.toml
  - ../../../../../../docs/10-Architecture/runtime/app_context_architecture.md
  - ../../../../../../docs/35-Core/README.md
related:
  - ../f1-architecture-currentization/ARCHITECTURE_CURRENTIZATION_aife-server-data-foundation_2026-08-25.md
---

# AIFE Server/Data Foundation — F1G governance admission

## 1. Authority и scope

```text
TASK_ID=AIFE-SERVER-DATA-PATCH-FACTORY-F1G-SERVER-GOVERNANCE-R01
CHECKPOINT=CHECKPOINT_F1G_SERVER_GOVERNANCE
PREDECESSOR_CHECKPOINT=CHECKPOINT_DATA_STANDARDS
PREDECESSOR_WIP_HEAD=381594104ad8270a5c4458f9f74e131a9b83fcb5
PREDECESSOR_WIP_TREE=dcf4bc931baefb542ccce1ace5a152dd15c5c879
F1_SERVER_SOURCE_ROOT=server/
SERVER_ROOT_KIND=TOP_LEVEL_PYTHON_PACKAGE
SERVER_SOURCE_ROOT_MATERIALIZED=NO
SERVER_IMPLEMENTATION_STARTED=NO
F2_CONTRACT_IMPLEMENTATION_STARTED=NO
```

F1G закрывает только governance gate. Он делает будущий `server/` законно допустимым,
но не создаёт каталог, `__init__.py`, runtime modules, adapters, workers, scheduler или deploy.

## 2. Discovered canonical owners

| Gate | Canonical owner | Decision |
| --- | --- | --- |
| top-level package root | `STD-ARCH-001` | минимальная amendment существующего approved owner |
| reusable runtime/DI boundary | `STD-ARCH-PATTERNS-001` + AppContext architecture | no-op; existing owner already sufficient |
| package/build/type/coverage roots | `pyproject.toml` | minimum config alignment |
| contract-domain governance | `STD-GOVERNANCE-CONTRACT-001` | admit `SERVER`; no fake contract/registry row |
| actual contract registry | `CONTRACTS_REGISTRY.md` | no-op until a concrete F2 contract exists |
| architecture-tree projection | canonical architecture-tree sync rules | no-op until `server/` is physically materialized |

## 3. Four-part gate

```text
STD_ARCH_PACKAGE_ROOT_ALIGNMENT=PASS
PYPROJECT_PACKAGE_DISCOVERY_ALIGNMENT=PASS
PYPROJECT_MUTATION_REQUIRED=YES
COVERAGE_TYPECHECK_LINT_ROOT_ALIGNMENT=PASS
SERVER_CONTRACT_DOMAIN_GOVERNANCE=PASS
F1G_SERVER_ROOT_ADMISSION_GATE=PASS
SERVER_ROOT_ADMITTED=YES
SERVER_ROOT_MATERIALIZED=NO
```

### Architecture root

`STD-ARCH-001` admits `server/` as an independent major semantic family, not `core/`,
not `deploy/` and not a dumping ground. `core/data/**` remains the lower generic
repository/session/UoW substrate. Public typed runtime exposure remains `AppContext` or an
explicitly approved transport adapter; `DependencyManager` remains internal.

### Packaging and quality

`pyproject.toml` adds future `server*` package discovery and `server` to mypy, pyright and
coverage source roots. Black/isort/pylint/pre-commit remain file-driven and no server-specific
exclude, suppression or threshold weakening is added.

```text
WHEN_SERVER_PACKAGE_IS_MATERIALIZED_LATER=PACKAGE_DISCOVERY_RECOGNIZES_IT
FUTURE_SERVER_SOURCE_CANNOT_EXIST_OUTSIDE_QUALITY_BOUNDARY=YES
PACKAGE_DISCOVERY_SERVER_READY=YES
QUALITY_SCOPE_SERVER_READY=YES
QUALITY_ESCAPE_HATCH_CREATED=NO
```

### SERVER contract domain

`STD-GOVERNANCE-CONTRACT-001` admits uppercase domain token `SERVER` and future canonical
`genome/contracts/server/`. No actual F2 contract and no synthetic registry row is created.

```text
SERVER_DOMAIN_ADMITTED=YES
SERVER_DOMAIN_IS_GENERIC_MECHANISM_AUTHORITY=YES
SERVER_DOMAIN_IS_ETH_SEMANTIC_AUTHORITY=NO
DATA_BRIDGE_REMAINS_ETH_SEMANTIC_AUTHORITY=YES
```

Generic SERVER contracts may later own work/scheduling/execution/publication/storage/access
and runtime/configuration-facing mechanisms. ETH provider semantics, market identities,
normalization, finality, revision/gap, domain due/retention and resolution semantics remain
with ETH Data Bridge.

## 4. Preserved owner boundaries

```text
APP_CONTEXT_TYPED_BOUNDARY_PRESERVED=YES
DEPENDENCY_MANAGER_PUBLIC_SERVICE_LOCATOR=NO
PARALLEL_DATA_SUBSTRATE_CREATED=NO
CORE_MANAGER_GLOBALIZED=NO
TASK_MANAGER_DURABLE_WORK_AUTHORITY=NO
PROCESS_ROLE_IMPLEMENTATION_STARTED=NO
HORIZONTAL_RUNTIME_IMPLEMENTATION_STARTED=NO
NEW_ARCH_STANDARD_COUNT=0
NEW_STD_SERVER_COUNT=0
```

`initializer/task_manager.py` remains an intra-process asyncio lifecycle helper. Future
process roles `CONTROL`, `WORKER`, `COMBINED_INITIAL_NODE` remain admissible design inputs but
are not implemented by this checkpoint.

## 5. Generated consequences

```text
GENERATED_CONSEQUENCES_DISCOVERED=YES
GENERATED_REQUIRED_CHANGE_COUNT=2
GENERATED_ARCH_CATALOG=genome/standards/arch/arch.json
GENERATED_GOVERNANCE_CATALOG=genome/standards/governance/governance.json
STANDARDS_REGISTRY_CHANGED=NO
GENOME_REGISTRY_CHANGED=NO
CONTRACTS_REGISTRY_CHANGED=NO
```

Owner-generated projections are determined by canonical generator output before candidate
freeze; this checkpoint does not guess them.

## 6. Five-question review

1. Future `server/` admissible without implementation: **PASS**.
2. Future source enters package/build/type/lint/coverage boundaries without bypass: **PASS**.
3. SERVER governance preserves generic-vs-domain authority: **PASS**.
4. Existing `core`, `initializer`, `deploy`, DATA standards and AppContext are not displaced: **PASS**.
5. Generated consequences: **PASS** — both required semantic catalogs are included; no other generated/registry change is required.

```text
F1G_FIVE_QUESTION_REVIEW=PASS
```

## 7. No-runtime boundary и next checkpoint

```text
DATABASE_VENDOR_SELECTED=NO
EXECUTION_TRANSPORT_SELECTED=NO
BACKUP_PROVIDER_SELECTED=NO
SERVER_IMPLEMENTATION_STARTED=NO
SERVER_SOURCE_ROOT_MATERIALIZED=NO
F2_CONTRACT_IMPLEMENTATION_STARTED=NO
SERVER_DEPLOYMENT_STARTED=NO
MIGRATION_EXECUTED=NO
D380_ACTIVATED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
NEXT_CHECKPOINT=CHECKPOINT_F2_MINIMUM_SERVER_ARTIFACT_CONTRACTS
```
