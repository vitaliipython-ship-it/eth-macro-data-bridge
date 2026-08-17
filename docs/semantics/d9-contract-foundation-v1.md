# D9.1 Contract Foundation v1

## Статус

```text
D9_1_IMPLEMENTATION=CANDIDATE
D9_ACTIVE=NO
ACTIVE_D6_ROUTE_CHANGED=NO
```

Planning authority:
`vitaliipython-ship-it/eth-macro-research/docs/integrations/market-data-history-lifecycle-v1.md`.

Plan review authority:
`vitaliipython-ship-it/eth-macro-research/docs/integrations/market-data-history-lifecycle-plan-review-v1.md`.

Этот документ фиксирует implementation foundation D9.1. Он не активирует D9 и не меняет production authority текущего D6 route.

## Authority invariant

```text
SOURCE_AUTHORITY
= exact GitHub repository commit

GITHUB_CONNECTOR
= repository control/mutation transport

LOCAL_CONNECTOR_SNAPSHOT
= LOCAL_SOURCE_TEST_ENVIRONMENT / PRE_QUALIFICATION_ENVIRONMENT only

GITHUB_ACTIONS_CHECKOUT
= canonical repository physical qualification environment

GITHUB_RELEASE + declared canonical resources
= market-data physical authority according to bridge contract
```

Локальная connector-materialized workspace может доказывать compile/unit/schema/deterministic source behavior, но не может заявлять `CLEAN_CLONE`, `GIT_INTEGRATION`, workflow publication/read-back или remote SHA qualification.

## D9.1 candidate contracts

Additive successor contracts:

```text
schema/capability-index-v2.schema.json
schema/market-data-resolution-plan-v2.schema.json
schema/collection-run-ledger.schema.json
schema/provider-revision.schema.json
schema/history-generation.schema.json
```

Active v1 остаётся:

```text
bridge-contract.json contract_version = 1.2.0
semantic_resolution.status = ACTIVE
semantic_resolution.resolver.resolution_plan_schema = market-data-resolution-plan/1.0.0
history/capability-index.json schema_version = 1.0.0
```

`capability-index-v2.schema.json` описывает successor **того же** derived capability index. Второй catalog/SSOT не создаётся.

`warm_manifest_path` — successor semantic name. `hot_manifest_path` допускается только как compatibility alias до D9 activation.

## Shared history-store primitive

`src/history_store.py` ограничен общими invariants:

- canonical observation identity;
- atomic JSON write;
- append/idempotency;
- immutable identity conflict detection;
- qualified revision observation without silent base overwrite;
- deterministic ordering;
- partition SHA/size/count descriptor.

Он не является новым service/database/subsystem. D9.2 должен переводить существующие writers на этот primitive по одному bounded compatibility seam, сохраняя domain semantics.

## Design gate

### Q1. Какой риск закрывает?

Три существующих append implementations могут расходиться по conflict/idempotency semantics. D9.1 также должен заранее различать fixed-grid, sampled, revision и multi-generation physical semantics, чтобы D9.2-D9.4 не перегружали v1 неоднозначными полями.

### Q2. Можно ли проще?

Да: extraction одного small module + additive schemas проще нового DB, ingest service, второго resolver или второго catalog. Именно этот вариант принят.

### Q3. Уменьшает ли число действий следующего агента?

Да: одна shared append contract и одна successor semantic model уменьшают число domain-specific storage решений и сохраняют consumer flow `series_id + range + policies → resolver → ResolutionPlan → reader`.

## D9.1 acceptance

Canonical repository gate обязан выполняться GitHub Actions workflow с real `actions/checkout`.

```text
D9_1_CONTRACTS=PASS
D9_1_SCHEMA_REGRESSION=PASS
D6_V1_COMPATIBILITY=PASS
ACTIVE_ROUTE_UNCHANGED=PASS
```

До такого remote result документ остаётся candidate evidence.

## Future publication gates

Для D9.3/D9.4 локальные тесты не заменяют remote publication evidence. Required physical proof:

```text
WORKFLOW_CHECKOUT=PASS
CANDIDATE_PUBLICATION=PASS
REMOTE_BINARY_READBACK=PASS
REMOTE_SIZE_MATCH=PASS
REMOTE_SHA256_MATCH=PASS
OVERLAP_PROOF=PASS
CROSS_BOUNDARY_SEMANTIC_READ=PASS
```

Новая D9 COLD generation не становится active authority до combined D9.3+D9.4 semantic qualification.
