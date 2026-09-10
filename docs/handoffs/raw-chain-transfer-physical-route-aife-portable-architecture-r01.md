# Raw chain-transfer physical route — AIFE-portable architecture R01

## 1. Machine identity and decision boundary

```text
TASK_FAMILY=ETH-UNIFIED-MONITORING-AND-SYNTHESIS
TASK_ID=ETH-MARKET-DATA-FOUNDATION-RAW-CHAIN-TRANSFER-PHYSICAL-FACT-ROUTE-AIFE-PORTABLE-ARCHITECTURE-AND-SCOPE-DECISION-R01
RUN_ID=ETH-UMS2-B2A-RAW-TRANSFER-4A-SOURCE-STORAGE-AIFE-PORTABILITY-DESIGN-R01
PRIMARY_DOMAIN=MARKET_DATA_FOUNDATION
OWNER_SELECTED_NEXT_GATE=4A_RAW_TRANSFER_PHYSICAL_FACT_ROUTE
SERIAL_PRIORITY_OVER_4B=NO
DOCUMENTATION_ARCHITECTURE_DECISION_ONLY=YES
RAW_TRANSFER_RUNTIME_IMPLEMENTED=NO
RAW_TRANSFER_FACT_ROUTE=NOT_IMPLEMENTED
RAW_TRANSFER_SEMANTIC_CONTRACT_REOPENED=NO
PROVIDER_NETWORK_EXECUTION=NO
AIFE_MUTATION=NO
B2B_MUTATION=NO
```

Этот handoff является durable implementation-facing decision authority для 4A. Он не активирует route, не выбирает production storage product, не меняет L0 semantic contract и не создаёт вторую market-data authority.

## 2. A — Fresh authority

```text
DATA_BRIDGE_MAIN_SHA=97e5b3915db1e8d88bb523f478acd7741bac32f2
DATA_BRIDGE_MAIN_TREE=1d8a170f15a3d35b307bd4fa497e03ade1b71a4a
BRANCH_CREATION_BASE_SHA=09c113cffac1d42e12af3270f310664586054a53
BRANCH_CREATION_BASE_TREE=4eac9efd8060ba82aa830c269843d1b42ed174a3
RESEARCH_MAIN_SHA=48a30bd1ee7ae194da1a0f22b0aed1f896ffe5a7
RESEARCH_MAIN_TREE=d3c0bb7e6e2b829e38def10d0faab83ad7feb0a1
AIFE_SERVER_WIP_BRANCH=agent/aife/server-data-foundation-wip
AIFE_SERVER_WIP_SHA=5ac7dc3afffeb5148c3fb2e7bcd39e9d102ff178
AIFE_SERVER_WIP_TREE=b8140c7cc2a35c8f1639ac7e899d508b05437aa2
PROMPT_DATA_BRIDGE_SNAPSHOT_SHA=ee5d0af68e5d6bcb16be09ba623d696157579c6b
PROMPT_TO_FRESH_DATA_BRIDGE_DRIFT=GENERATED_DATA_ONLY_NO_SEMANTIC_AUTHORITY_INTERSECTION
POST_BRANCH_CREATION_MAIN_DRIFT=GENERATED_DATA_ONLY_NO_SEMANTIC_AUTHORITY_INTERSECTION
AUTO_REBASE_EXECUTED=NO
```

Predecessor refs:

```text
RAW_TRANSFER_L0_CONTRACT=contracts/raw-chain-transfer-fact-semantic-contract-v1.json
RAW_TRANSFER_L0_SEMANTICS=docs/semantics/raw-chain-transfer-fact-semantic-contract-v1.md
RESOLUTION_PLAN_V2=schema/market-data-resolution-plan-v2.schema.json
CHAIN_REVISION_SCHEMA=schema/chain-canonicality-revision.schema.json
D8_D9_FORWARDING=contracts/d8-d9-forwarding-v1.json
STORAGE_PORTABILITY=bridge-contract.json#storage_portability
AIFE_STORAGE_CONTRACT=AIFE/staging/genome/contracts/server/CONTRACT-SERVER-STORAGE-001.md@agent/aife/server-data-foundation-wip
AIFE_DATA_FOUNDATION_ADR=AIFE/staging/genome/adr/data/ADR-DATA-FOUNDATION-001.md@agent/aife/server-data-foundation-wip
```

AIFE WIP — read-only engineering evidence. Future Data Bridge code MUST NOT import source from that branch; AIFE binding starts only after the relevant AIFE authority is integrated in its own lifecycle.

## 3. B — Current state and frozen semantics

```text
L0_BINDING_COMPLETE_OWNER_INTEGRATED=YES
RAW_TRANSFER_FACT_CAPABILITY_ID=blockchain.raw-transfer-facts
RAW_TRANSFER_FACT_OWNER=MARKET_DATA_FOUNDATION
RAW_TRANSFER_FACT_LAYER=L0_FACTUAL
RAW_TRANSFER_FACT_ANALYTICAL_STATE=NO
PHYSICAL_ROUTE_IMPLEMENTED=NO
RAW_TRANSFER_RUNTIME_ACTIVE=NO
RAW_TRANSFER_PROVIDER_SELECTION=DEFERRED
PROVIDER_SELECTED=NO
STORAGE_SELECTED=NO
D6_V1_DEFAULT_ROUTE_PRESERVED=YES
D9_GLOBAL_ACTIVE=NO
V2_GLOBAL_ACTIVE=NO
4B_B2B_STATE=UNCHANGED
```

Frozen semantics remain `STRUCTURED_TIME_SERIES + EVENT_DRIVEN + PROVISIONAL_ALLOWED_EXPLICITLY + CHAIN_CANONICALITY_REVISION` with `APPEND_ONLY_VERSIONED_CANONICALITY_STATE_WITH_PIT_CUTOFF`. Old observations are never overwritten/deleted and canonicality is not finality.

## 4. C — Source requirement matrix

Ethereum mainnet is the first physical scope. `transaction != transfer`, `log != all value transfers`, and `address != entity` are hard boundaries.

| Factual property | Source primitive | Historical/current | Coverage / PIT / failure rule |
| --- | --- | --- | --- |
| chain identity | `eth_chainId` | both | wrong chain rejects source profile |
| block height/hash/timestamp | discover `eth_getBlockByNumber`, then exact `eth_getBlockByHash` | archive + current | block hash anchors all components; mismatch/gap fails closed |
| transaction identity | full tx objects for exact block hash | archive + current | tx set must match receipts/traces |
| native ETH transfers | successful value-bearing `callTracer` tree frames | trace archive + current | every tx trace required; trace failure means block not covered |
| token transfers | exact-block receipts/logs | archive + current | receipts for every tx + declared parser coverage required |
| `transaction_hash` | block/receipt/trace binding | both | absent tx hash is outside this capability scope |
| `log_index` | receipt log index | both | exact receipt membership; conflict rejects |
| `trace_index` | tx-hash-bound deterministic call-tree path/preorder ordinal | both | stable under retry; malformed tree rejects |
| `transfer_index` | deterministic normalized ordering within tx | both | collision rejects |
| `event_time` | block timestamp | both | never replaced by collection time |
| `observation_known_at` | first durable observation/acquisition time for version | both | PIT cutoff uses this field |
| `PROVISIONAL` | fully covered canonical block above finalized head | current + overlap | incomplete block is never provisional evidence |
| `FINALIZED` | `finalized` head + same exact block hash | archive + current | cannot prove => remains provisional |
| canonicality revision | re-observe overlap height→hash | both | hash change emits existing revision evidence |
| source provenance | provider class/profile revision + component evidence | both | secrets excluded; provenance survives readback |
| zero-event coverage | BLOCK + RECEIPTS + TRACES complete for declared parser classes | both | empty without all components != zero |

Protocol-native balance credits that cannot satisfy the frozen required `transaction_hash` (for example consensus-layer withdrawals/rewards without a transaction) are outside this capability rather than assigned fabricated identities. Expanding to them requires a separate semantic decision.

### Declared initial transfer classes

```text
NATIVE_ETH_TRANSFER_SOURCE=SUCCESSFUL_VALUE_BEARING_CALLTRACER_FRAMES
TOKEN_TRANSFER_SOURCE=RECEIPT_LOGS
INITIAL_TOKEN_EVENT_COVERAGE=ERC20_TRANSFER;ERC721_TRANSFER;ERC1155_TRANSFER_SINGLE;ERC1155_TRANSFER_BATCH
NON_STANDARD_TOKEN_MOVEMENT_WITHOUT_DECLARED_EVENT_SEMANTICS=NOT_COVERED_NOT_ZERO
ENTITY_ATTRIBUTION=FORBIDDEN
USD_VALUE=FORBIDDEN
```

`callTracer` exposes the nested executed call tree and ETH `value`; `STATICCALL` and `DELEGATECALL` are not independently normalized as value transfers; successful value-bearing `CALL`, `CREATE`/`CREATE2` and `SELFDESTRUCT` frames are covered when their factual from/to/value semantics are present. Failed/reverted execution effects are excluded according to exact receipt/trace success evidence. Parser behavior is fixture-qualified rather than inferred from vendor branding.

## 5. D — Provider/source decision

```text
SOURCE_ARCHITECTURE_DECISION=BLOCK_HASH_BOUND_MANAGED_FULL_ARCHIVE_TRACE_CAPABLE_ETHEREUM_JSON_RPC
PRIMARY_PROVIDER_CLASS=MANAGED_ETHEREUM_FULL_ARCHIVE_TRACE_CAPABLE_JSON_RPC
PROVIDER_VENDOR=DEFERRED_OWNER_BILLING_CREDENTIAL_APPROVAL
OWNER_PROVIDER_DECISION_REQUIRED=YES_FOR_CREDENTIALLED_LIVE_QUALIFICATION_ONLY
RECOMMENDED_OPTION=ALCHEMY_ETHEREUM_MAINNET_MANAGED_ARCHIVE_DEBUG_RPC
FALLBACK_OPTION=QUICKNODE_ETHEREUM_MANAGED_ARCHIVE_TRACE_RPC
OWNER_DECISION_DIMENSION=PROVISION_ONE_CREDENTIALLED_PLAN_WITH_SUSTAINED_HISTORICAL_TRACE_THROUGHPUT_FOR_THE_BOUNDED_BACKFILL_WINDOW
PROVIDER_REPLACEABLE_WITHOUT_DOMAIN_REWRITE=true
```

The domain API is standard Ethereum block/receipt/debug-trace semantics, not an Alchemy SDK/API. Alchemy is the recommended first credentialled qualification endpoint because its current first-party docs expose `eth_getBlockReceipts`, `eth_getBlockByHash`, `debug_traceBlockByHash` with `callTracer`, and archive-data access on Ethereum. QuickNode is the single fallback because its Ethereum endpoint documents Debug + Trace APIs. Both still require an owner-controlled credential/plan decision; that commercial decision does not block network-free implementation qualification.

First-party references checked 2026-09-10:

- `https://www.alchemy.com/docs/chains/ethereum/ethereum-api-endpoints/eth-get-block-receipts`
- `https://www.alchemy.com/docs/chains/debug-api/debug-api-endpoints/debug-trace-block-by-hash`
- `https://www.alchemy.com/docs/what-is-archive-data-on-ethereum`
- `https://www.quicknode.com/docs/ethereum/api-overview`

Source-class comparison:

| Source class | Mandatory factual coverage | Portability | Decision |
| --- | --- | --- | --- |
| managed archive+trace JSON-RPC | block, receipts/logs, full call tree, current + history | high; endpoint/config replacement only | **SELECT** |
| non-archive/full RPC | historical trace state not guaranteed | high | reject for required backfill |
| indexer/transfers API | may hide parser/trace completeness behind vendor semantics | lower | fallback evidence source only, not primary |
| self-hosted archive node | sufficient if configured with trace history | high semantics, highest ops cost | future fallback, not initial route |

No silent provider fallback is allowed within one block acquisition: a provider failure produces `PROVIDER_UNAVAILABLE`/`COVERAGE_GAP`; retry replays the same logical block/range through the configured adapter.

## 6. E — Storage/publication decision

```text
CAN_EXISTING_DATA_BRIDGE_STORAGE_PUBLICATION_LIFECYCLE_BE_REUSED=PARTIAL
STORAGE_LIFECYCLE=EVENT_BLOCK_BUNDLES_AS_IMMUTABLE_CONTENT_PLUS_APPEND_ONLY_COVERAGE_AND_CANONICALITY_EVIDENCE_THROUGH_EXISTING_HOT_WARM_COLD_LIFECYCLE
EXISTING_D8_D9_REUSE=LOGICAL_LIFECYCLE+CONTENT_IDENTITY+WHOLE_BATCH_ACK+REMOTE_READBACK+CONTROL_PLANE_VISIBILITY+RESOLUTION_PLAN_V2+EXISTING_READER_FAMILY
NEW_STORAGE_FRAMEWORK_REQUIRED=NO
NEW_DATABASE_REQUIRED=NO
HIGH_CARDINALITY_WARM_BACKEND_PRODUCT_SELECTED_NOW=NO
```

Reuse is `PARTIAL`, not `YES`, for two physically proven gaps in current authority:

1. `bridge-contract.json#storage_portability.high_cardinality_warm_backend=BLOCKED_VERSIONED_DECISION`; the current GitHub-first WARM adapter is not silently promoted to a raw-transfer high-cardinality backend.
2. `market-data-resolution-plan-v2.schema.json#$defs.eventSeriesEvidence` currently accepts only `observations + canonicality_revisions`; it cannot carry durable zero-event/range coverage evidence. `HistoryPublicationBatch` also requires at least one observation, so an empty block cannot be truthfully represented as a proven zero by the existing observation batch alone.

The missing primitive is therefore **not a database**. It is one storage-neutral, immutable block-bundle/coverage representation plus a bounded extension of the existing v2 event resolver/reader path to consume that evidence from a canonical physical descriptor. The physical backend remains adapter-owned.

Target AIFE storage mapping is the already proven generic durable lifecycle: content-addressed immutable bytes + independent readback + durable Work/Publication/Generation control. Data Bridge continues to own transfer semantics, coverage interpretation, canonicality revisions and resolver selection.

```text
LOCAL_FILESYSTEM_WRITE_ALONE_IS_CANONICAL_PUBLICATION_ACK=false
GITHUB_GIT_PER_TRANSFER=false
SECOND_HISTORY_AUTHORITY=false
SECOND_RESOLVER=false
SECOND_READER=false
```

## 7. F — AIFE mapping and placement classification

```text
CURRENT_EXECUTION=REPOSITORY_NATIVE_QUALIFICATION_CARRIER
TARGET_EXECUTION=AIFE_SERVER
DOMAIN_REWRITE_ON_MIGRATION=NO
AIFE_CONTROL_PRIMITIVE_REUSE=FULL
FUTURE_AIFE_PLACEMENT_CLASS=EXISTING_GENERIC_SERVER_ACQUISITION_INTEGRATION_BINDING_WITH_DATA_BRIDGE_OWNED_DOMAIN_PROVIDER_ADAPTER
EXACT_FINAL_AIFE_PATH_REQUIRED_NOW=NO
```

Fresh AIFE authority explicitly states `AIFE_SERVER_OWNS_GENERIC_COLLECTION_RUNTIME=YES`, `AIFE_SERVER_OWNS_PROVIDER_SEMANTICS=NO`, `DOMAIN_PROVIDER_ADAPTERS_MAY_EXECUTE_INSIDE_AIFE_SERVER_DEPLOYMENT=YES` and `D8_DOMAIN_PROVIDER_LOGIC=RETAIN_AS_CANONICAL_DATA_BRIDGE_DOMAIN_PROVIDER_ADAPTER`. Therefore raw-transfer provider/domain code remains Data Bridge-owned; later AIFE integration binds it through the existing generic acquisition/domain envelope seams rather than copying D8 runtime or creating a blockchain-specific server framework.

```text
AIFE_WORK_MAPPING=ONE_DETERMINISTIC_CHAIN_RANGE_OR_BLOCK_COLLECTION_INPUT_TO_EXISTING_WORK_IDENTITY
AIFE_ATTEMPT_MAPPING=ONE_EXECUTION_OF_SAME_WORK_WITH_EXISTING_CLAIM_LEASE_FENCING_RECLAIM
AIFE_PUBLICATION_MAPPING=IMMUTABLE_BLOCK_BUNDLE_BYTES_PLUS_READBACK_THROUGH_EXISTING_PUBLICATION_STORAGE_LIFECYCLE
AIFE_GENERATION_MAPPING=VISIBLE_DURABLE_VERSION_OF_EXACT_DOMAIN_ARTIFACT_WITH_DATA_BRIDGE_SEMANTIC_REGISTRATION_REMAINING_EXTERNAL_DOMAIN_AUTHORITY
```

The migration seam is adapter rebinding only:

```text
RawTransferCollectionCore
  -> ProviderPort          repository qualification: fake/fixture RPC; target: credentialled Ethereum RPC adapter
  -> PublicationPort       repository qualification: deterministic test adapter; target: existing AIFE durable lifecycle binding
  -> Coverage/Checkpoint   domain evidence; execution ownership remains existing AIFE Work/Attempt
```

No Data Bridge source may import `AIFE/**` from the WIP branch. Exact `AIFE/staging/<future-AIFE-path> -> <future-AIFE-path>` materialization is deferred to the later AIFE integration task after canonical AIFE authority reconciliation.

## 8. G — Minimal ports/adapters and coverage/checkpoint semantics

Only these seams are required:

```text
ProviderPort.fetch_block_bundle(chain_id, block_ref) -> exact block + receipts + traces
PublicationPort.publish(block_bundle_bytes, content_identity, provenance) -> durable/readback ACK
RawTransferCollectionCore -> validates, normalizes, identities, coverage, finality, reorg evidence
EthereumJsonRpcProviderAdapter -> only Ethereum/source-specific implementation
```

`ProviderPort` is a narrow source seam, not a plugin manager. `PublicationPort` carries exact domain bytes and ACK semantics; it does not expose filesystem/database locators to the core.

Coverage identity is block-hash-bound:

```text
COVERAGE_KEY=(chain_id,block_height,block_hash,parser_policy_revision)
COVERAGE_COMPONENTS=BLOCK_BODY;ALL_TRANSACTION_RECEIPTS;ALL_TRANSACTION_TRACES;DECLARED_TOKEN_EVENT_PARSERS
COVERAGE_COMPLETE_IFF=ALL_REQUIRED_COMPONENTS_VERIFIED_FOR_EXACT_BLOCK_HASH
```

A covered block may contain zero normalized transfers. Such a block is `NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE`; it is never represented by a synthetic transfer row. Missing receipt/trace/parser completion yields `COVERAGE_GAP`; transport/auth/rate-limit failure yields `PROVIDER_UNAVAILABLE`; no acquisition attempt yields `SOURCE_NOT_OBSERVED`.

There is no second mutable cursor ledger. Incremental progress is derived from the highest contiguous **durably ACKed coverage** for the canonical chain view; the next forward range begins at the next height. Every non-finalized published height remains eligible for exact-height/hash re-observation until finalization. A changed canonical hash emits append-only `CHAIN_CANONICALITY_REVISION`; previous block bundles/transfers remain addressable.

```text
CHECKPOINT_COMMIT_BOUNDARY=AFTER_DURABLE_PUBLICATION_AND_READBACK_ACK
RETRY_BOUNDARY=SAME_LOGICAL_BLOCK_OR_RANGE
RETRY_CAN_CHANGE_PROVIDER_ATTEMPT_METADATA=YES
RETRY_CAN_CHANGE_LOGICAL_TRANSFER_IDENTITY=NO
BACKFILL_COMPLETE_IFF=EVERY_REQUESTED_HEIGHT_HAS_ACKED_COVERAGE_FOR_THE_SELECTED_PIT_VIEW
PARTIAL_RANGE_SUCCESS=NO_SILENT_ADVANCE_PAST_FIRST_UNCOVERED_HEIGHT
```

## 9. H — Three-question minimality table

| Proposed mechanism | REAL_RISK | SIMPLER_EXISTING_MECHANISM | ACTION_COUNT_EFFECT | DECISION |
| --- | --- | --- | --- | --- |
| narrow `ProviderPort` | vendor SDK/endpoint semantics leaking into core prevents AIFE/provider swap | no existing raw-transfer source seam on `main`; keep protocol in same core module | reduced | `ADD_MINIMAL` |
| Ethereum JSON-RPC adapter | Ethereum block/receipt/trace parsing is chain-specific | cannot place this in generic core | reduced | `ADD_MINIMAL` |
| second resolver | none; v2 event route already exists | `tools/resolution_v2.py` | increased | `REJECT` |
| second reader family | none; v2 reader already materializes event/reorg semantics | `tools/history_access_v2.py` + existing consumer | increased | `REJECT` |
| new storage/database framework | none; AIFE immutable storage/control and Data Bridge lifecycle already cover mechanics | existing AIFE Storage/Publication/Generation + D8/D9 lifecycle | increased | `REJECT` |
| new publication framework | none | narrow `PublicationPort` binding to existing lifecycle | increased | `REJECT` |
| new manifest family | no proven need for a second catalog/control SSOT | existing canonical physical descriptor/control-plane projection | increased | `REJECT` |
| durable coverage evidence in block bundle | empty event set cannot prove zero; current event evidence has no coverage member | no existing primitive can represent zero-event exact-block coverage | reduced | `ADD_MINIMAL` |
| separate coverage receipt file | none once coverage is content-bound inside immutable block bundle | block bundle evidence | increased | `REJECT` |
| queue / message bus | none for one-server bounded collection | AIFE Work/Attempt | increased | `REJECT` |
| scheduler | none; due/execution is generic AIFE responsibility | AIFE scheduling/Work | increased | `REJECT` |
| cursor/checkpoint ledger | duplicate mutable state and divergence risk | derive next height from contiguous ACKed coverage; AIFE Work persists attempts | reduced | `REUSE_EXISTING` |
| retry subsystem | provider/transient failures | existing Attempt/lease/fencing/reclaim; same logical range replay | reduced | `REUSE_EXISTING` |
| cache | no physical requirement | immutable durable publication/readback | increased | `REJECT` |
| service/daemon/microservice | no requirement before AIFE runtime binding | current qualification runner, later AIFE Server | increased | `REJECT` |
| minimal physical block-bundle schema | cross-process/AIFE byte contract and zero-coverage identity must be deterministic | no existing schema represents this physical evidence | same then reduced | `ADD_MINIMAL` |
| AIFE-specific raw-transfer abstraction | none | generic `AcquisitionAdapter`, Work, Attempt, Publication, Generation | increased | `REJECT` |

## 10. I — Exact bounded future implementation scope

The next Data Bridge implementation task is network-inactive and must stay within this proposed path set:

```text
FUTURE_IMPLEMENTATION_PATH_COUNT=8
ADD    src/raw_chain_transfer_core.py
ADD    src/ethereum_raw_transfer_rpc_adapter.py
ADD    schema/raw-chain-transfer-physical-block-bundle-v1.schema.json
MODIFY schema/market-data-resolution-plan-v2.schema.json
MODIFY tools/resolution_v2.py
MODIFY tools/history_access_v2.py
MODIFY bridge-contract.json
ADD    tests/deep_history/test_raw_chain_transfer_physical_route.py
```

| PATH | WHY_REQUIRED | EXISTING_PATH_REUSE_CHECK | THREE_QUESTION_RESULT |
| --- | --- | --- | --- |
| `src/raw_chain_transfer_core.py` | one portable core + narrow ports + deterministic identities/coverage/reorg normalization | no existing raw-transfer core; do not extend `CanonicalAcquisitionCore` with blockchain-specific framework state | PASS |
| `src/ethereum_raw_transfer_rpc_adapter.py` | Ethereum block/receipt/trace source adapter | existing provider adapters are market-specific and do not expose Ethereum execution traces | PASS |
| `schema/raw-chain-transfer-physical-block-bundle-v1.schema.json` | stable exact-byte bundle containing zero-capable coverage + observations + provenance | semantic contract is not a physical bundle schema; current PublicationBatch cannot represent empty coverage | PASS |
| `schema/market-data-resolution-plan-v2.schema.json` | add bounded coverage evidence/physical EVENT_DRIVEN shape | extend v2; no v3/new plan family | PASS |
| `tools/resolution_v2.py` | build/select physical raw-transfer event plan with PIT cutoff | extend existing resolver family | PASS |
| `tools/history_access_v2.py` | materialize bundle, coverage and canonicality revisions | extend existing reader family | PASS |
| `bridge-contract.json` | owner-integrated candidate must advertise source implementation without activating provider/D9/global v2 | existing machine SSOT; no new catalog | PASS |
| `tests/deep_history/test_raw_chain_transfer_physical_route.py` | T01–T35 positive/negative fixture proof | one focused suite; reuse existing fixtures/helpers where practical | PASS |

No AIFE path is part of that implementation PR. The later AIFE binding task consumes the already-qualified Data Bridge domain adapter after fresh canonical AIFE reconciliation; it does not move semantic ownership.

## 11. J — Future implementation validation matrix

```text
T01 PASS if capability remains blockchain.raw-transfer-facts.
T02 PASS if every output remains L0 factual and entity attribution is absent.
T03 PASS if fixture RPC block+receipts+traces produce every required factual field.
T04 PASS if transfer/observation identities are deterministic across replay/input ordering.
T05 PASS if native ETH value-bearing successful call frames normalize correctly.
T06 PASS if declared ERC20/ERC721/ERC1155 event fixtures normalize correctly.
T07 PASS if internal/trace coverage is explicit and a missing trace fails block coverage.
T08 PASS if fully covered non-finalized block may be PROVISIONAL.
T09 PASS if FINALIZED requires finalized-head evidence for the exact block hash.
T10 PASS if reorg produces append-only CHAIN_CANONICALITY_REVISION.
T11 PASS if superseded transfer bytes/identity remain addressable.
T12 PASS if pre-revision cutoff returns pre-reorg canonical view and future revision cannot leak.
T13 PASS if empty transfers without complete coverage never becomes proven zero.
T14 PASS if backfill completion requires ACKed coverage for every requested height.
T15 PASS if forward start is derived from highest contiguous ACKed coverage and provisional overlap is rechecked.
T16 PASS if any missing block/receipt/trace component fails closed with explicit coverage state.
T17 PASS if retry of same logical block/range cannot create duplicate logical observations.
T18 PASS if provider/source provenance and component identities survive durable publication/readback.
```
```text
T19 PASS if existing ResolutionPlan v2 is the only semantic plan family used.
T20 PASS if no second resolver is introduced.
T21 PASS if no second reader family is introduced.
T22 PASS if history/capability-index.json gains no fake availability row before real authority.
T23 PASS if global D9 remains inactive unless independently authorized.
T24 PASS if global v2 remains inactive unless independently authorized.
T25 PASS if D6/v1 default bytes and route remain unaffected.
T26 PASS if vendor endpoint/API key/plan does not appear in domain observation API or identity.
T27 PASS if filesystem/object-store/database locator does not appear in domain API/identity.
T28 PASS if GitHub run/issue/artifact state does not appear in domain API/identity.
T29 PASS if repository qualification PublicationPort can be replaced by AIFE binding without changing core tests/logic.
T30 PASS if identical logical provider fixture produces semantically equivalent bundle under repository and AIFE-style adapters.
T31 PASS if AIFE Work/Attempt/Publication/Generation mapping needs no new persistent framework.
T32 PASS if no blockchain-specific AIFE control repository/queue/scheduler is introduced.
T33 PASS if Research/B2b/entity-label paths remain untouched.
T34 PASS if Whale/entity/exchange/USD/directional analytical fields are absent.
T35 PASS if dependencies contain no Kafka/RabbitMQ/message bus/microservice requirement.
```

Additional negative proofs:

```text
WRONG_CHAIN_ID=REJECT
BLOCK_HASH_COMPONENT_MISMATCH=REJECT
RECEIPT_SET_INCOMPLETE=COVERAGE_GAP
TRACE_SET_INCOMPLETE=COVERAGE_GAP
UNKNOWN_TOKEN_EVENT=NOT_COVERED_NOT_ZERO
FAILED_OR_REVERTED_VALUE_EFFECT=NOT_EMITTED_AS_SUCCESSFUL_TRANSFER
DUPLICATE_IDENTITY_DIFFERENT_BYTES=REJECT
FUTURE_REVISION_AFTER_CUTOFF=IGNORED
PROVIDER_429_OR_TIMEOUT=PROVIDER_UNAVAILABLE_NO_CURSOR_ADVANCE
ZERO_TRANSFER_BLOCK_WITH_COMPLETE_COMPONENTS=NO_EVENTS_OBSERVED_WITH_PROVEN_COVERAGE
```

## 12. K — Stop conditions for implementation/qualification

Fail closed with the task contract's exact STOP class when any of these facts appears:

```text
RAW_TRANSFER_PHYSICAL_ROUTE_REQUIRES_L0_CONTRACT_REOPEN
  if required Ethereum transfer class cannot be represented without changing frozen L0 identity/fields.
RAW_TRANSFER_SOURCE_CANNOT_PROVE_COVERAGE
  if exact-block body + complete receipts + complete trace evidence cannot be obtained/verified.
RAW_TRANSFER_SOURCE_CANNOT_SUPPORT_REQUIRED_PIT_REORG_SEMANTICS
  if historical block-hash/revision evidence cannot be retained and cutoff-filtered.
RAW_TRANSFER_EXISTING_D8_D9_REUSE_UNRESOLVED
  if implementation would need a second resolver/reader instead of extending v2 event semantics.
RAW_TRANSFER_AIFE_PORTABILITY_CONFLICT
  if core requires GitHub, vendor SDK, storage locator or AIFE path knowledge.
RAW_TRANSFER_DUPLICATE_CONTROL_FRAMEWORK_REQUIRED
  if AIFE Work/Attempt/Publication/Generation cannot express execution without a new blockchain queue/control DB.
RAW_TRANSFER_ARCHITECTURE_SCOPE_EXPANSION_REQUIRED
  if implementation needs paths outside the bounded set before a new physically proven scope decision.
RAW_TRANSFER_ARCHITECTURE_VALIDATION_FAILED
  if any T01–T35 proof fails.
```

A provider credential/plan is deliberately not required for the network-free implementation candidate. Before any live qualification, owner must provision the single recommended managed archive+trace endpoint or explicitly choose the one fallback; no credential is stored in repository authority.

## 13. Scale-out invariants

```text
ETHEREUM_FIRST=true
MULTICHAIN_IMPLEMENTED_NOW=false
FUTURE_CHAIN_ADAPTER_EXTENSION_POSSIBLE=true
CAPABILITY_ID_STABLE=true
CHAIN_SPECIFIC_SOURCE_ADAPTERS_ALLOWED=true
CHAIN_SPECIFIC_DUPLICATE_DOMAIN_FRAMEWORK=false
```

## 14. Terminal architecture decision

```text
TASK_STATUS=PASS_PHYSICAL_ROUTE_ARCHITECTURE_AND_IMPLEMENTATION_SCOPE_DECIDED
RAW_TRANSFER_L0_BINDING_REOPENED=NO
RAW_TRANSFER_FACT_ROUTE=NOT_IMPLEMENTED
SOURCE_ARCHITECTURE_DECIDED=YES
PROVIDER_SOURCE_DECISION=OWNER_ONLY_DECISION_NARROWED_TO_ONE_EXACT_DIMENSION
STORAGE_PUBLICATION_LIFECYCLE_DECIDED=YES
EXISTING_STORAGE_LIFECYCLE_REUSED_WHERE_SUFFICIENT=YES
AIFE_SERVER_TARGET_EXECUTION_PLANE=YES
AIFE_SERVER_PORTABILITY=PASS
DOMAIN_CORE_PORTABLE=YES
SERVER_MIGRATION_BY_ADAPTER_REBINDING=YES
SERVER_MIGRATION_BY_DOMAIN_REWRITE=NO
SECOND_RESOLVER_REQUIRED=NO
SECOND_READER_REQUIRED=NO
SECOND_DATA_AUTHORITY_CREATED=NO
NEW_AIFE_CONTROL_FRAMEWORK_REQUIRED=NO
PREMATURE_MICROSERVICE_SPLIT=NO
B2B_STARTED=NO
4B_STATE=UNCHANGED
NEXT_EXACT_IMPLEMENTATION_SCOPE_READY=YES
```

```text
THREE_QUESTION_GATE=
Q1_REAL_RISK=INCOMPLETE_BLOCK_COMPONENTS_FALSE_ZERO;TRACE_OMISSION;REORG_PIT_LEAKAGE;NON_DURABLE_COVERAGE;VENDOR_OR_STORAGE_LOCK_IN;DUPLICATE_RUNTIME_AUTHORITY
Q2_SIMPLER_METHOD=REUSE_RESOLUTION_PLAN_V2_AND_EXISTING_READER;REUSE_D8_D9_LIFECYCLE_AND_AIFE_GENERIC_DURABILITY;ADD_ONLY_PROVIDER_ADAPTER_CORE_AND_ZERO_CAPABLE_BLOCK_BUNDLE_EVIDENCE
Q3_ACTION_REDUCTION=NEXT_AGENT_HAS_ONE_SOURCE_CLASS_ONE_RECOMMENDED_VENDOR_ONE_FALLBACK_ONE_8_PATH_SCOPE_AND_T01_T35_MATRIX;AIFE_MIGRATION_REBINDS_ADAPTERS_WITHOUT_DOMAIN_REWRITE
VERDICT=PASS
```

```text
NEXT_EXACT_ACTION=OWNER_REVIEW_AND_INTEGRATION_OF_THIS_ARCHITECTURE_DECISION_THEN_BOUNDED_RAW_TRANSFER_PHYSICAL_ROUTE_IMPLEMENTATION
OWNER_MERGE_REQUIRED=YES
OWNER_MERGE_EXECUTED=NO
```
