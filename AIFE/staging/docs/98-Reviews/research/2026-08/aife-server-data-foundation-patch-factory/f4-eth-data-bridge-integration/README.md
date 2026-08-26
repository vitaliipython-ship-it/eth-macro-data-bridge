---
title: "AIFE Server/Data Foundation — F4: ETH Data Bridge integration"
status: draft
owner: Architecture Lead
created: 2026-08-26
updated: 2026-08-26
category: architecture
doc_type: report
language: ru
tags: [server, data, f4, eth, integration, publication, access, replay, revision]
authority_reference:
  - ../../../../../../AGENTS.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-WORK-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-EXECUTION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-PUBLICATION-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md
  - ../../../../../../genome/contracts/server/CONTRACT-SERVER-ACCESS-001.md
  - ../f3-server-source-skeleton-core-mechanisms/README.md
---

# AIFE Server/Data Foundation — F4: ETH Data Bridge integration

## 1. Authority и checkpoint boundary

```text
TASK_ID=AIFE-SERVER-DATA-PATCH-FACTORY-F4-ETH-DATA-BRIDGE-INTEGRATION-R01
CHECKPOINT=CHECKPOINT_F4_ETH_DATA_BRIDGE_INTEGRATION
PREDECESSOR_CHECKPOINT=CHECKPOINT_F3_SERVER_SOURCE_SKELETON_AND_CORE_MECHANISMS
PREDECESSOR_WIP_HEAD=555ba32f3928db507fd29b7c0dcea49116773e82
PREDECESSOR_WIP_TREE=74c041c1005a52c7a8b7707291ad8dbaa9f4a0bf
DATA_BRIDGE_INTEGRATION_DISCOVERY=PASS
SERVER_DEPLOYMENT_STARTED=NO
MIGRATION_STARTED=NO
F5_STARTED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
```

F4 связывает уже принятую Data Bridge domain output с generic F3 Server/Data foundation. F4 не
переносит market/provider semantics в будущий AIFE Server и не создаёт второй Data Bridge
resolver/reader/publication authority.

## 2. Fresh Data Bridge discovery

Repository discovery выполнялся от exact accepted predecessor, а не по chat-схеме. Фактически
подтверждены следующие output/evidence classes:

```text
ROLLING_SPOT_MANIFEST=data/manifest.json
CLOSED_SPOT_HISTORY_SERIES=history/manifest.json
D8_RUNTIME_OBSERVATION=src/d8_d9_forwarder.py
D8_PUBLICATION_BATCH=schema/history-publication-batch-v1.schema.json
DERIVATIVES_METRIC_ARCHIVE=derivatives/manifest.json
OPTIONS_SURFACE_SNAPSHOT=options/manifest.json
LIQUIDITY_SNAPSHOT=liquidity/manifest.json
CANONICAL_PUBLICATION_ACK=src/history_publication_port.py
```

Data Bridge repository authority already owns and validates `observation_id`, `series_id`,
`fingerprint`, `validation_status`, `finality`, provider timestamp, provenance, source revision,
gap/revision/lifecycle routing and canonical publication identity. Publication ACK requires all of:

```text
REMOTE_DURABILITY
REMOTE_READBACK
EXACT_BATCH_MEMBERSHIP
EXACT_PAYLOAD_BINDING
INTEGRITY_BINDING
CONTROL_PLANE_VISIBILITY
RESOLVER_VISIBILITY
READER_MATERIALIZATION
```

Server therefore consumes only the accepted result of those decisions.

## 3. Domain / Server authority split

```text
ETH_DATA_BRIDGE_OWNS=
MARKET_DATA_SEMANTICS
+ PROVIDER_SEMANTICS
+ DOMAIN_IDENTITIES
+ NORMALIZATION
+ DOMAIN_VALIDATION
+ FINALITY
+ REVISION_RULES
+ GAP_RULES
+ DOMAIN_RESOLUTION_RULES

AIFE_SERVER_OWNS=
GENERIC_WORK_MECHANISMS
+ GENERIC_EXECUTION_OWNERSHIP
+ GENERIC_PUBLICATION
+ GENERIC_STORAGE_LIFECYCLE
+ GENERIC_ACCESS_MECHANISMS

SERVER_REVALIDATES_MARKET_SEMANTICS=NO
SERVER_RENORMALIZES_MARKET_DATA=NO
SERVER_CHANGES_FINALITY=NO
SERVER_INVENTS_ETH_IDENTITY=NO
SERVER_DOMAIN_IS_ETH_SEMANTIC_AUTHORITY=NO
```

ETH/provider-specific adaptation остаётся Data Bridge-owned в `src/aife_server_adapter.py`.
Future AIFE `server/**` содержит только neutral envelope и generic bindings.

## 4. Neutral domain input envelope

`server/integration/domain.py` вводит минимальный opaque boundary:

```text
DOMAIN_ARTIFACT_IDENTITY
DOMAIN_ARTIFACT_TYPE
SOURCE_REVISION
CONTENT_IDENTITY
PAYLOAD_REFERENCE
PROVENANCE_REFERENCE
ACCEPTANCE_EVIDENCE_REFERENCE
VALIDATED_AT
PRODUCED_AT
OBSERVED_AT (optional)
```

Envelope не содержит provider, instrument, pair, market finality state, normalization formula,
gap policy, revision policy или domain payload. Server не читает payload, чтобы сформировать
identity/publication/access binding.

```text
DOMAIN_INPUT_ENVELOPE=PASS
DOMAIN_PAYLOAD_REINTERPRETED_BY_SERVER=NO
```

## 5. Data Bridge-owned adapter

`src/aife_server_adapter.py` — единственный F4 source вне `AIFE/**`. Он знает Data Bridge field
names и переводит уже domain-accepted metadata в neutral Server envelope. Для D8 observation он
требует только accepted boundary `validation_status=PASS`, переносит существующие
`observation_id`, `series_id`, `provenance.source_revision`, timestamp/reference identity и считает
content identity canonical JSON hash всего уже принятого observation envelope.

Adapter намеренно не пересчитывает Data Bridge `observation_id`, fingerprint, finality, route,
provider normalization, gaps или revision semantics: эти проверки уже принадлежат существующему
Data Bridge producer/forwarding contour.

```text
DATA_BRIDGE_HOST_ADAPTER_PATH_COUNT=1
ETH_SPECIFIC_CODE_INSIDE_FUTURE_AIFE_GENERIC_SERVER=NO
EXISTING_COLLECTION_SEMANTICS_CHANGED=NO
EXISTING_NORMALIZATION_SEMANTICS_CHANGED=NO
EXISTING_FINALITY_SEMANTICS_CHANGED=NO
EXISTING_GAP_REVISION_SEMANTICS_CHANGED=NO
```

## 6. Domain → Work identity

`server/integration/bindings.py` формирует deterministic input identity из opaque triple:

```text
DOMAIN_ARTIFACT_IDENTITY
+ SOURCE_REVISION
+ CONTENT_IDENTITY
```

Из него выводятся stable logical `WorkId`, idempotency identity, publication identity и stored
object identity. Поэтому replay одного accepted artifact сохраняет logical identity, retry может
использовать новый F3 execution attempt при том же logical work, а новая domain revision или новое
content identity получает отличимый Server input identity.

```text
DOMAIN_TO_WORK_MAPPING=PASS
REPLAY_IDEMPOTENT=YES
REVISION_IDENTITY_PRESERVED=YES
```

## 7. Publication / storage / read-back binding

F4 использует неизменённый F3 lifecycle:

```text
VALIDATED_DOMAIN_INPUT
→ INGEST_DURABLE
→ STAGED
→ PUBLISHING
→ DURABLE_STORED
→ INDEPENDENT_READBACK_VERIFIED
→ CANONICALLY_REGISTERED
→ ACKED
```

`DURABLE_STORED` требует exact object/content evidence. Independent read-back дополнительно
сверяет source revision и provenance. Canonical registration обязана ссылаться на тот же stored
object. ACK остаётся F3 four-proof conjunction и не создаёт новую publication identity при retry.

```text
ETH_PUBLICATION_BINDING=PASS
ACK_BEFORE_READBACK=NO
DATABASE_VENDOR_SELECTED=NO
OBJECT_STORE_VENDOR_SELECTED=NO
PRODUCTION_STORAGE_BACKEND_IMPLEMENTED=NO
PHYSICAL_WAREHOUSE_ACTIVATED=NO
```

## 8. Access binding

`access_result_from_domain()` публикует только identity projection:

- domain artifact identity;
- opaque artifact type;
- source revision;
- content identity;
- provenance reference;
- payload reference;
- optional snapshot identity.

Payload не загружается и не нормализуется повторно.

```text
ACCESS_RESULT_PRESERVES_DOMAIN_IDENTITY=YES
ACCESS_LAYER_RENORMALIZES_DOMAIN_DATA=NO
```

## 9. Representative real Data Bridge fixtures

F4 test fixtures зафиксированы из actual predecessor repository metadata:

| Class | Repository source | Authority identity/evidence used |
| --- | --- | --- |
| Spot OHLCV/history | `history/manifest.json` | ETHUSDT 5m closed history, `integrity_status=PASS`, exact latest partition |
| Derivatives | `derivatives/manifest.json` | PI_ETHUSD open-interest archive descriptor and freshness |
| Options | `options/manifest.json` | latest Deribit surface, DVOL path, option counts and analytics |
| Liquidity | `liquidity/manifest.json` | accepted ETHUSDT snapshot including already domain-normalized notional metadata |
| Publication identity | `contracts/d8-a2-physical-qualification-status-v1.json` | accepted A2 batch, membership/payload hashes, remote byte preservation, ACK and idempotent replay |

```text
REAL_DATA_BRIDGE_FIXTURES_USED=YES
SYNTHETIC_ONLY_INTEGRATION_PROOF=NO
FIXTURE_PATH_COUNT=5
```

Synthetic D8-shaped test input используется только для доказательства adapter boundary: он
намеренно содержит opaque semantic tokens, чтобы доказать отсутствие повторной semantic
валидации в Server. Representative integration proof не является synthetic-only.

## 10. Replay / revision / failure proofs

F4 tests покрывают:

1. same artifact replay;
2. duplicate delivery;
3. domain source revision change;
4. durable storage без ACK;
5. storage success / registration mismatch;
6. registration success / ACK failure and retry;
7. independent read-back mismatch;
8. stale execution fence;
9. provenance preservation;
10. access result identity preservation.

```text
REPLAY_TESTS=PASS
REVISION_TESTS=PASS
PUBLICATION_FAILURE_TESTS=PASS
READBACK_TESTS=PASS
F3_CONTRACT_TESTS=PASS
F3_CROSS_MODULE_TESTS=PASS
```

## 11. No-domain-leakage audit

Static/AST audit всего future AIFE `server/**` даёт:

```text
IMPORT_CYCLES=0
BINANCE_SEMANTIC_IMPORTS_IN_SERVER=0
KRAKEN_SEMANTIC_IMPORTS_IN_SERVER=0
DERIBIT_SEMANTIC_IMPORTS_IN_SERVER=0
ETH_PAIR_SPECIFIC_BRANCHES_IN_GENERIC_SERVER=0
DOMAIN_FINALITY_LOGIC_IN_GENERIC_SERVER=0
```

Таким образом generic Server integration остается reusable для другого domain producer с тем же
accepted-artifact boundary.

## 12. Exact F4 operation map

```text
SERVER_SOURCE_PATH_COUNT=3
DATA_BRIDGE_HOST_ADAPTER_PATH_COUNT=1
TEST_PATH_COUNT=3
FIXTURE_PATH_COUNT=5
EXISTING_INTEGRATION_PATH_COUNT=0
GENERATED_PATH_COUNT=3
CHECKPOINT_DOC_PATH_COUNT=1
CONTROL_PATH_COUNT=2
TOTAL_PATH_COUNT=18
HARD_MAX_CHANGED_PATHS=128
UNRELATED_PATHS=NONE
```

`AIFE/staging/**` является future-AIFE projection. Data Bridge host adapter, host test/fixtures и
two `AIFE/integration|evidence` controls не overlay-ятся в canonical AIFE reference.

## 13. Source quality and accumulated validation

Pre-freeze source proof:

```text
F4_TARGETED_TESTS=PASS
F4_F3_COMBINED_TEST_COUNT=39
F4_INTEGRATION_TESTS=PASS
F4_REPLAY_TESTS=PASS
F4_TYPECHECK=PASS
F4_LINT=PASS
F4_FORMAT_CHECK=PASS
F4_IMPORT_CHECK=PASS
F3_REGRESSION=PASS
MYPY_SOURCE_FILE_COUNT=35
PYLINT_SCORE=10.00/10
```

Canonical accumulated AIFE validation overlays `AIFE/staging/**` over immutable
`AIFE_review_latest.zip` and validates F0 + F1 + DATA + F1G + F2 + F3 + F4 together. Terminal
receipt records the final architecture/structural/metadata/link/read-back results after generated
projection and control bytes are frozen.

## 14. Next boundary

F4 does not select or activate physical high-cardinality storage. It does not deploy Server,
migrate corpus, activate D8/D9, retire legacy storage or run horizontal worker qualification.

```text
PRODUCTION_STORAGE_STARTED=NO
MIGRATION_STARTED=NO
SERVER_DEPLOYMENT_STARTED=NO
F5_STARTED=NO
AEB_CREATED=NO
REAL_AIFE_MUTATED=NO
NEXT_CHECKPOINT=CHECKPOINT_F5_HIGH_CARDINALITY_PHYSICAL_STORAGE_LIFECYCLE
```
