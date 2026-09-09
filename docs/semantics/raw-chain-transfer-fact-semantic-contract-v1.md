# Raw chain-transfer factual semantic contract v1

## Статус и authority

```text
CONTRACT_ID=ETH-RAW-CHAIN-TRANSFER-FACT-SEMANTIC-CONTRACT-V1
SCHEMA_VERSION=eth-raw-chain-transfer-fact-semantic-contract/1.0.0
MACHINE_AUTHORITY=contracts/raw-chain-transfer-fact-semantic-contract-v1.json
CAPABILITY_ID=blockchain.raw-transfer-facts
OWNER_DOMAIN=MARKET_DATA_FOUNDATION
IMPLEMENTATION_AUTHORITY=vitaliipython-ship-it/eth-macro-data-bridge
LAYER=L0_FACTUAL
ANALYTICAL_STATE=NO
RUNTIME_ACTIVE=NO
RAW_TRANSFER_FACT_ROUTE=NOT_IMPLEMENTED
RAW_TRANSFER_PROVIDER_SELECTION=DEFERRED
```

Machine contract — канонический semantic owner. Этот документ является implementation-facing projection. Capability ID фиксирует provider-neutral factual identity, но не создаёт runtime series, provider route, storage route или запись в `history/capability-index.json`.

## ResolutionPlan semantics

```text
PLAN_SCHEMA=market-data-resolution-plan/2.0.0
SERIES_KIND=STRUCTURED_TIME_SERIES
COVERAGE_SEMANTICS=EVENT_DRIVEN
FINALITY_POLICY=PROVISIONAL_ALLOWED_EXPLICITLY
REVISION_POLICY=CHAIN_CANONICALITY_REVISION
CHAIN_REORG_MODEL=APPEND_ONLY_VERSIONED_CANONICALITY_STATE_WITH_PIT_CUTOFF
GLOBAL_V2_ACTIVATION=NO
D9_GLOBAL_ACTIVATION=NO
```

Explicit-v2 semantics используются только как capability requirement. Active D6/v1 route остаётся default.

## L0 factual observation

Обязательные factual fields: `observation_id`, `chain_id`, `transaction_hash`, `transfer_identity`, `block_height`, `block_hash`, `event_time`, `observation_known_at`, `source_address`, `destination_address`, `asset_identity`, `native_quantity`, `native_quantity_unit`, `finality`, `source_provenance`.

`log_index`, `trace_index`, `transfer_index` являются nullable/applicable identity components. `TRANSFER_IDENTITY=DETERMINISTIC_FROM_CHAIN_NATIVE_FACTUAL_IDENTITY_COMPONENTS`; entity interpretation никогда не входит в factual identity.

## Asset и address boundary

Поддерживаются `NATIVE_ASSET` и `TOKEN_ASSET`. Token factual identity сохраняет `chain_id` и `contract_address`; provider-native asset identifier допустим только как supplemental factual identifier. USD valuation не принадлежит L0.

```text
ADDRESS != ENTITY
ADDRESS != EXCHANGE
ADDRESS != WHALE
RAW_TRANSFER_FACT_DOES_NOT_IMPLY_ENTITY_ATTRIBUTION=true
ENTITY_ATTRIBUTION_OWNER=ONCHAIN_ANALYTICS
```

Entity/exchange/Whale labels, accumulation/distribution, entity positions, directional interpretation и forensic scores запрещены в L0.

## Finality, canonicality и PIT

Observation states: `PROVISIONAL`, `FINALIZED`. Canonicality — отдельная ось. Reorg не удаляет и не перезаписывает factual observation; append-only `CHAIN_CANONICALITY_REVISION` меняет canonical view, а superseded transfer остаётся addressable.

PIT cutoff использует только evidence, для которого `observation_known_at <= query_cutoff` и `revision_known_at <= query_cutoff`. Future reorg knowledge leakage запрещён.

## Coverage / completeness

```text
ABSENCE_OF_TRANSFER_WITHOUT_COVERAGE_PROOF_IS_ZERO=false
NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE
!= SOURCE_NOT_OBSERVED
!= COVERAGE_GAP
!= PROVIDER_UNAVAILABLE
!= UNKNOWN
```

Ни missing source, ни coverage gap не преобразуются в нулевой transfer count/value.

## Provider, storage и runtime boundary

```text
PROVIDER_SELECTED=NO
RPC_SELECTED=NO
INDEXER_SELECTED=NO
API_KEY_CONTRACT_CREATED=NO
NETWORK_CALLS_ADDED=0
STORAGE_SELECTED=NO
HISTORY_CAPABILITY_INDEX_RUNTIME_ROW_CREATED=NO
FAKE_AVAILABILITY_STATUS_CREATED=NO
```

Provider/source authority и acquisition route — отдельный будущий Market Data task. До него `WHALE_RAW_TRANSFER_FACT_ROUTE_GAP=OPEN`, а B2b не начинается.
