# Intra-observation extrema-order evidence v1

## Статус и authority

```text
CONTRACT_ID=ETH-MARKET-DATA-INTRA-OBSERVATION-EXTREMA-ORDER-EVIDENCE-V1
CAPABILITY_ID=market-data.intra-observation-extrema-order-evidence
MACHINE_AUTHORITY=contracts/intra-observation-extrema-order-evidence-v1.json
OWNER_DOMAIN=MARKET_DATA_FOUNDATION
STATUS=ACCEPTED_ARCHITECTURE_CONTRACT_NOT_RUNTIME_ACTIVE
RUNTIME_ACTIVE=NO
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
RESEARCH_MUTATION=NO
WAVE_SEMANTICS_IN_DATA_BRIDGE=NO
```

Контракт описывает generic market fact: можно ли физически доказать, что high parent observation наступил раньше low, low раньше high, либо порядок не различим/не доказан на доступной canonical evidence. Downstream consumer может валидировать и ссылаться на факт, но не может создавать второй ordering authority.

## Проблема

Один OHLC interval хранит high и low, но сам по себе не доказывает порядок их возникновения. Запрещены `UNKNOWN -> HIGH_BEFORE_LOW`, `UNKNOWN -> LOW_BEFORE_HIGH`, caller choice, сортировка по цене и assumed candle path.

Canonical result states:

```text
HIGH_BEFORE_LOW
LOW_BEFORE_HIGH
ORDER_NOT_MATERIALLY_DISTINCT
UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE
```

`PIT_INELIGIBLE` — отдельное eligibility-состояние: физически корректная evidence не используется для knowledge replay раньше своего `known_at_utc`.

## Иерархия physical proof

Порядок выбора фиксирован:

```text
LEVEL_1=EXISTING_CANONICAL_LOWER_TIMEFRAME_OBSERVATIONS
LEVEL_2=EXISTING_PROVIDER_NATIVE_ORDERED_EVENT_OR_SEQUENCE_EVIDENCE
LEVEL_3=NEW_BOUNDED_EVENT_LEVEL_CAPABILITY_IF_SEPARATELY_AUTHORIZED
```

V1 физически доказан на LEVEL_1 и не требует full raw-event archive. LEVEL_2/LEVEL_3 нужны только как возможный successor для случаев, которые остаются unresolved на самом мелком доступном canonical child interval.

```text
FULL_RAW_TRADE_ARCHIVE_DEFAULT=FORBIDDEN
FULL_RAW_TRADE_ARCHIVE_REQUIRES_SEPARATE_VALUE_GATE=YES
FULL_HISTORY_EVENT_BACKFILL_REQUIRED_NOW=NO
```

## Lower-timeframe proof

Parent и child evidence должны быть получены через canonical route:

```text
bridge-contract.json
-> history/capability-index.json
-> tools/capability_index.py
-> ResolutionPlan
-> tools/history_consumer.py / tools/history_access.py
-> semantic receipt
```

Proof допустим только при одновременном выполнении условий:

- parent и child принадлежат одному provider/instrument semantic identity;
- value semantics и unit совпадают;
- child resolution строго мельче parent resolution;
- ordered child window полностью покрывает parent interval без gaps;
- parent high точно присутствует в canonical child evidence;
- parent low точно присутствует в canonical child evidence;
- все используемые observations finalized и provenance-bound;
- earliest qualifying occurrence каждого parent extrema вычисляется из complete child window, а не выбирается consumer-ом;
- если earliest high и earliest low попали в один smallest available child interval, порядок остаётся unresolved.

Repeated extrema используют только:

```text
EARLIEST_PHYSICALLY_PROVABLE_OCCURRENCE_OF_PARENT_HIGH
EARLIEST_PHYSICALLY_PROVABLE_OCCURRENCE_OF_PARENT_LOW
```

Consumer не выбирает occurrence и не может подавать winner как truth.

## Реальный canonical proof

Bounded feasibility выполнен на exact Data Bridge head:

```text
HEAD=c0dda1fab7b711db74f7a756fe15eceddd0bac6a
PARENT_SERIES=spot.binance-spot.ETHUSDT.ohlcv.1h
CHILD_SERIES=spot.binance-spot.ETHUSDT.ohlcv.5m
RANGE=[2026-08-01T00:00:00Z,2026-09-01T00:00:00Z)
PARENT_OBSERVATIONS=744
CHILD_OBSERVATIONS=8928
PARENT_EXTREMA_MATCH_COUNT=744
DETERMINISTIC_ORDER_COUNT=734
UNRESOLVED_SAME_CHILD_COUNT=10
REPEATED_EXTREMA_PARENT_COUNT=65
```

Canonical semantic evidence:

```text
PARENT_SEMANTIC_RECEIPT_SHA256=4bd8153b0f88c0269fbadfa268ad3a671c775429c33d774af7066c36ce15e727
PARENT_RESOLUTION_PLAN_SHA256=fc8a462cccc6886e362c73695a974f87718bca9f92be95b7ecdad189510df7ae
PARENT_SEMANTIC_OUTPUT_SHA256=b1259b7ef5c4aec0d7522e3cd273ffc4f69b6c901708d2eae49c00df422b80f7
CHILD_SEMANTIC_RECEIPT_SHA256=ebf4b68bbad836a908a091368b8dec32fa8b279dee330f766376c30c86d2954d
CHILD_RESOLUTION_PLAN_SHA256=4624d7590d53715144b712adb4a07a5a3af0eac68461b8ad6a8f1b3eee3082b5
CHILD_SEMANTIC_OUTPUT_SHA256=a788dfa18fbca859b4bd05daef21069bf81554b4ec584680299e270f40308ac5
```

### HIGH_BEFORE_LOW

```text
PARENT_START=2026-08-01T05:00:00Z
PARENT_HIGH=1871.05000000
PARENT_LOW=1865.34000000
PARENT_OBSERVATION_FINGERPRINT=sha256:737059a44fa0581f73201253ba42aba92723519ce01a6b03af9ce75536680f0a
CHILD_WINDOW_FINGERPRINT=sha256:c2d5844b321877bd191f8cfcab2cf71da0f92ece7b0802086ff3ea0de29b0eae
EARLIEST_HIGH_CHILD=2026-08-01T05:10:00Z
EARLIEST_LOW_CHILD=2026-08-01T05:40:00Z
RESULT=HIGH_BEFORE_LOW
CALLER_ORDER_ASSERTION_USED=NO
```

High повторяется также в child `05:15`, но occurrence selection остаётся deterministic: используется earliest physically provable occurrence `05:10`.

### LOW_BEFORE_HIGH

```text
PARENT_START=2026-08-01T00:00:00Z
PARENT_HIGH=1867.64000000
PARENT_LOW=1862.38000000
PARENT_OBSERVATION_FINGERPRINT=sha256:be5ae65e31f0fd48190d59afffc33eef8ee3194a9052cbe520afabe3852d488c
CHILD_WINDOW_FINGERPRINT=sha256:564a437f62c30041315905d000708d5c789187aeea096a7f38e715f29833f250
EARLIEST_LOW_CHILD=2026-08-01T00:00:00Z
EARLIEST_HIGH_CHILD=2026-08-01T00:45:00Z
RESULT=LOW_BEFORE_HIGH
CALLER_ORDER_ASSERTION_USED=NO
```

### Same-smallest-child ambiguity

```text
PARENT_START=2026-08-01T10:00:00Z
PARENT_HIGH=1869.11000000
PARENT_LOW=1863.10000000
PARENT_OBSERVATION_FINGERPRINT=sha256:bc7f8402fd8a32a43b65e4e6fe57ea4b1883bda85a2529e30de737cc644845df
CHILD_WINDOW_FINGERPRINT=sha256:813d67e5fdb74abca200a1e5b6bb61c47221106520caf72cdc7ac7d144ac5cfa
HIGH_CHILD=2026-08-01T10:00:00Z
LOW_CHILD=2026-08-01T10:00:00Z
SHARED_CHILD_FINGERPRINT=sha256:c800965a3e847483f49015540da6c110ad2278b8caf2af0ccadfde64c36a1208
RESULT=UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE
GUESSED_ORDER_USED=NO
```

Этот case является нормальным fail-closed результатом V1 и не требует немедленного raw-tape program.

## Carrier identity

Carrier связывает минимум:

```text
contract_id
capability_id
provider_id
instrument_id
parent_series_id
parent_observation_ref
parent_interval_start_utc
parent_interval_end_utc
parent_high
parent_low
value_semantics
unit
ordering_evidence_source
proof_granularity
finality
event_effective_at
evidence_available_at_utc
known_at_utc
evidence_fingerprint
carrier_fingerprint
provenance
```

Для lower-TF proof дополнительно обязательны `child_series_id`, `child_interval`, complete ordered `supporting_child_observation_refs`, `child_window_fingerprint`, `earliest_parent_high_occurrence`, `earliest_parent_low_occurrence`.

`parent_observation_ref` и child refs являются deterministic references на canonical series/time/observation fingerprint. Физические storage locator/path/release tag не являются consumer input authority.

## Same timestamp / provider sequence

Если event-level successor когда-либо используется и high/low source events имеют одинаковый timestamp, строгий порядок допустим только через provider-native sequence/trade/event identity, который сам квалифицирован provider contract-ом. Без такого secondary order результат `UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE`.

Запрещены lexical JSON order, caller array position, сортировка по цене и local ingestion arrival order без explicit source binding.

## Flat interval

```text
IF parent_high == parent_low:
    ORDER=ORDER_NOT_MATERIALLY_DISTINCT
```

Для одного price value не создаётся фиктивная HIGH-before-LOW chronology. Parent identity/value/provenance остаются обязательными, но child order proof не требуется.

## PIT / knowledge

Контракт различает:

```text
EVENT_EFFECTIVE_AT
EVIDENCE_AVAILABLE_AT
KNOWN_AT
QUERY_CUTOFF
```

Source market time никогда не masquerade как knowledge time. Если historical canonical route не хранит exact row-level availability timestamp, implementation не backdate-ит его до candle close; используется фактическое carrier readback/materialization time как conservative availability bound. `known_at_utc >= evidence_available_at_utc`; для knowledge replay требуется `known_at_utc <= query_cutoff_utc`, иначе `PIT_INELIGIBLE`.

Manifest publication time не подменяет row known-at, а event time не подменяет evidence availability.

## Fingerprint

`evidence_fingerprint` — SHA-256 canonical compact UTF-8 JSON с sorted object keys; ordered child/event arrays сохраняют semantic chronology. Он включает market/source identity, parent identity/extrema, complete evidence binding, result и semantic receipt identity.

Не входят local path, hostname, GitHub run/issue transport identity, caller list order и local ingestion arrival order. `carrier_fingerprint` дополнительно связывает PIT envelope, чтобы knowledge-state carrier нельзя было silently backdate.

## Event-level feasibility и value gate

Existing provider descriptions подтверждают, что некоторые provider-native trade/event families имеют timestamps и иногда sequence/trade IDs, но active generic canonical raw price-event tape для этой capability сейчас не создан. V1 не активирует provider и не выполняет network probe/backfill.

```text
DOES_GENERIC_CARRIER_REQUIRE_FULL_RAW_EVENT_STORAGE=NO
CAN_LOWER_TF_PROVE_A_USEFUL_SUBSET=YES
CAN_SAME_CHILD_INTERVAL_REMAIN_FAIL_CLOSED=YES
IS_EVENT_LEVEL_SOURCE_REQUIRED_FOR_UNRESOLVED_CASES=YES
IS_FULL_HISTORY_EVENT_BACKFILL_REQUIRED_NOW=NO
EVENT_LEVEL_SUCCESSOR=OPTIONAL_FOR_COVERAGE
```

Если позже ценность покрытия unresolved cases оправдает bounded event-level capability, она проходит отдельный owner value gate. Full historical raw tape не является default solution.

## Consumer boundary

```text
DOWNSTREAM_MAY_VALIDATE_AND_REFERENCE_ORDER_EVIDENCE=YES
DOWNSTREAM_MAY_INVENT_ORDER=NO
DOWNSTREAM_MAY_REINTERPRET_UNRESOLVED_AS_BOOLEAN=NO
ORDER_EVIDENCE_IS_MARKET_FACT=YES
WAVE_SEMANTICS_IN_DATA_BRIDGE=NO
```

Контракт не содержит Elliott/NEoWave/monowave/Rule-of-Neutrality/Rules-of-Observation/structural-termination semantics. Downstream domain самостоятельно решает, что делать с доказанным market fact.

## Activation boundary

```text
RUNTIME_ACTIVE=NO
PROVIDER_ACTIVATION_CHANGED=NO
NEW_COLLECTOR=NO
NEW_READER=NO
NEW_RESOLVER=NO
CAPABILITY_INDEX_RUNTIME_WRITER_CHANGED=NO
BULK_RAW_TRADE_INGESTION=NO
HISTORICAL_BULK_BACKFILL=NO
STORAGE_AUTHORITY_CHANGED=NO
D8_D9_ACTIVATION=NO
RESEARCH_MUTATION=NO
AIFE_MUTATION=NO
```

Следующий gate после owner merge этого architecture contract — downstream specification repair может ссылаться на owner-integrated Data Bridge authority; runtime implementation carrier-а остаётся отдельным явно авторизуемым task, если downstream требуется executable production materialization, а не только contract-bound evidence semantics.

## Exact fingerprint canonicalization companion

Machine authority for byte-exact fingerprint preimages is additive and lives at:

```text
CONTRACT_ID=ETH-MARKET-DATA-INTRA-OBSERVATION-EXTREMA-ORDER-EVIDENCE-FINGERPRINT-CANONICALIZATION-V1
PATH=contracts/intra-observation-extrema-order-evidence-fingerprint-canonicalization-v1.json
REFERENCE_VALIDATOR=tools/intra_observation_extrema_order_evidence.py:validate_carrier_fingerprints
PARENT_CONTRACT_MUTATED=NO
RUNTIME_ACTIVE=NO
```

The original V1 contract remains the parent market-fact semantics authority. The companion makes only its fingerprint preimage and validation boundary executable. Canonical JSON bytes are UTF-8 `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` with no whitespace, BOM, trailing newline, Unicode normalization, duplicate object keys, NaN or Infinity. Object-key insertion order is not authority; ordered semantic arrays are preserved exactly.

### Exact lower-timeframe evidence preimage

For `HIGH_BEFORE_LOW`, `LOW_BEFORE_HIGH`, and lower-timeframe `UNRESOLVED_INSUFFICIENT_GRANULARITY_OR_SOURCE_EVIDENCE`, the evidence fingerprint preimage is exactly:

```json
{
  "contract_id": "carrier.contract_id",
  "capability_id": "carrier.capability_id",
  "provider_id": "carrier.provider_id",
  "instrument_id": "carrier.instrument_id",
  "parent_series_id": "carrier.parent_series_id",
  "parent_observation_ref": "carrier.parent_observation_ref",
  "parent_high": "carrier.parent_high",
  "parent_low": "carrier.parent_low",
  "child_or_event_evidence_bindings": {
    "child_series_id": "carrier.child_series_id",
    "child_interval": "carrier.child_interval",
    "supporting_child_observation_refs": "carrier.supporting_child_observation_refs",
    "child_window_fingerprint": "carrier.child_window_fingerprint",
    "earliest_parent_high_occurrence": "carrier.earliest_parent_high_occurrence",
    "earliest_parent_low_occurrence": "carrier.earliest_parent_low_occurrence"
  },
  "derived_result": "carrier.derived_result",
  "provenance_receipt_identity": {
    "parent_semantic_receipt_sha256": "carrier.provenance.parent_semantic_receipt_sha256",
    "parent_resolution_plan_sha256": "carrier.provenance.parent_resolution_plan_sha256",
    "parent_semantic_output_sha256": "carrier.provenance.parent_semantic_output_sha256",
    "child_semantic_receipt_sha256": "carrier.provenance.child_semantic_receipt_sha256",
    "child_resolution_plan_sha256": "carrier.provenance.child_resolution_plan_sha256",
    "child_semantic_output_sha256": "carrier.provenance.child_semantic_output_sha256",
    "parent_observation_fingerprint": "carrier.provenance.parent_observation_fingerprint",
    "child_window_fingerprint": "carrier.provenance.child_window_fingerprint"
  }
}
```

No additional carrier fields enter that preimage. `supporting_child_observation_refs` preserves physical semantic chronology and is never lexically, numerically, by-price, or by-hash sorted. Reordering that array changes the evidence fingerprint.

### Exact flat evidence preimage

For the V1 flat condition `parent_high == parent_low` with `ORDER_NOT_MATERIALLY_DISTINCT`, the exact evidence preimage keeps the same top-level identity but uses an empty evidence-binding object and parent-only provenance:

```json
{
  "contract_id": "carrier.contract_id",
  "capability_id": "carrier.capability_id",
  "provider_id": "carrier.provider_id",
  "instrument_id": "carrier.instrument_id",
  "parent_series_id": "carrier.parent_series_id",
  "parent_observation_ref": "carrier.parent_observation_ref",
  "parent_high": "carrier.parent_high",
  "parent_low": "carrier.parent_low",
  "child_or_event_evidence_bindings": {},
  "derived_result": "carrier.derived_result",
  "provenance_receipt_identity": {
    "parent_semantic_receipt_sha256": "carrier.provenance.parent_semantic_receipt_sha256",
    "parent_resolution_plan_sha256": "carrier.provenance.parent_resolution_plan_sha256",
    "parent_semantic_output_sha256": "carrier.provenance.parent_semantic_output_sha256",
    "parent_observation_fingerprint": "carrier.provenance.parent_observation_fingerprint"
  }
}
```

A non-flat parent claiming `ORDER_NOT_MATERIALLY_DISTINCT` fails closed. Lower-timeframe unresolved evidence uses the same complete lower-timeframe payload as resolved lower-timeframe evidence; only `derived_result` differs.

### Exact carrier identity and PIT eligibility

The carrier fingerprint preimage is exactly:

```json
{
  "evidence_fingerprint": "recomputed_evidence_fingerprint",
  "pit_envelope": {
    "event_effective_at": "carrier.event_effective_at",
    "evidence_available_at_utc": "carrier.evidence_available_at_utc",
    "known_at_utc": "carrier.known_at_utc"
  }
}
```

The evidence fingerprint is recomputed from the authoritative preimage; the caller value is not trusted. `query_cutoff_utc` is eligibility-only and never part of immutable carrier identity. `finality` is validated separately and is not part of the PIT envelope. The same carrier can therefore be `PIT_INELIGIBLE` at an earlier query cutoff and eligible at a later cutoff without changing either fingerprint. `known_at_utc >= evidence_available_at_utc` remains mandatory; knowledge backdating fails closed.

Exact event-level fingerprint preimage is not authorized by this companion. Event-level validation without a separately owner-integrated profile fails closed as `EVENT_LEVEL_FINGERPRINT_PROFILE_NOT_AUTHORIZED`; this companion creates no provider reader, producer, event tape, historical backfill, resolver, storage authority, or runtime activation.

The companion contains four frozen machine test vectors with exact carrier subset, evidence payload, canonical UTF-8 JSON text, evidence fingerprint, carrier payload, and carrier fingerprint. These vectors are the cross-language determinism anchor; the Python helper is a reference implementation, not the semantic authority.
