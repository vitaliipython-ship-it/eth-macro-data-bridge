# D8 VPS HOT Boundary v1

## Статус

```text
D8_DEPENDENCY=CAPTURED
D8_RUNTIME_IMPLEMENTED=NO
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_VPS_TARGET=REQUIRED
BINANCE_USDM_VPS_RUNTIME=NOT_ACTIVE
BINANCE_USDM_ACTIVE_PROVIDER=false
VPS_HOT_SEAM_CONTRACT=READY
```

Этот документ уточняет границу ETH-D8 / ETH-D9. Он не разворачивает VPS runtime и не активирует Binance USDⓈ-M.

## Runtime ownership

D8 владеет near-real-time acquisition/runtime plane:

- VPS runtime;
- target acquisition cadence approximately 5 minutes;
- provider connectivity;
- Binance USDⓈ-M acquisition route;
- runtime health/freshness;
- bounded runtime spool, если он потребуется;
- secure/read-only HOT transport toward the canonical Data Bridge consumer;
- restart/recovery/runtime supervision.

D9 владеет semantic/durable lifecycle plane:

- semantic identity;
- HOT/WARM/COLD lifecycle semantics;
- durable HOT → WARM transition;
- WARM → COLD sealing;
- multi-generation history;
- capability index / resolver / ResolutionPlan / reader;
- integrity, gap and revision semantics;
- provenance and historical continuity.

VPS runtime не становится market-data authority. Authority остаётся у canonical Data Bridge contracts, canonical manifests/resources и qualified observations/provenance.

## Binance USDⓈ-M policy

Текущее отключение scoped только к GitHub-hosted acquisition runtime:

```text
current_collection = DISABLED_BY_POLICY
network_calls = 0
signal_vote = EXCLUDED
```

Target state:

```text
VPS target = REQUIRED
VPS runtime = NOT_ACTIVE until separate D8 qualification
activation = separate versioned control-plane provider-policy transition
historical evidence = PRESERVED
```

D9 не имеет права включать Binance USDⓈ-M network calls в GitHub Actions collector, делать provider fallback или объявлять provider ACTIVE.

## Target Binance USDⓈ-M families

Successor capability model должен позволять отдельную semantic registration минимум для ETHUSDT perpetual:

- OHLCV 5m;
- intentionally collected provider-native higher TF;
- mark price;
- index price;
- premium/basis;
- open interest;
- funding;
- order-book/depth snapshots;
- прочие provider-native derivatives observations только после отдельного semantic review.

Историческая доступность не синтезируется. Не backfillable series получают `FORWARD_ONLY` либо другую explicit availability semantics.

## HOT authority seam

Canonical semantic flow остаётся единым:

```text
semantic request
→ capability index
→ canonical resolver
→ ResolutionPlan
→ canonical reader
→ COLD + WARM + qualified HOT observations
→ diagnostics/provenance
```

Для future VPS HOT source агент не задаёт и Research object не хранит:

- VPS hostname;
- VPS filesystem path;
- provider URL;
- transport implementation.

`ResolutionPlan v2` может содержать `HOT_CURRENT_RESOURCE`, но его `physical_descriptor` обязан ссылаться на canonical authority, а locator/transport authority остаётся `CANONICAL_CONTROL_PLANE`.

## Cadence and gap semantics

Approximate 5-minute cadence — acquisition target, не обещание exact wall-clock execution. Collection run evidence включает:

- `expected_schedule_at`;
- `collection_started_at`;
- `collection_completed_at`;
- provider timestamp when available;
- `known_at`;
- `retrieved_at`;
- status;
- freshness.

Пропущенный cycle маркируется `COLLECTION_GAP`; synthetic fill запрещён.

## Forbidden online transport

Не является target design:

```text
GitHub Actions every 5m → collect → commit → push
```

и не является target design:

```text
VPS every 5m → git commit/push every observation
```

GitHub остаётся source/control/qualification/CI/Release/provenance plane, но не primary 5-minute acquisition scheduler.

## D8 qualification gate

До activation должны существовать отдельные доказательства:

```text
VPS_PROVIDER_CONNECTIVITY=PASS
BINANCE_USDM_5M_COLLECTION=PASS
RUNTIME_RESTART_RECOVERY=PASS
FRESHNESS_SEMANTICS=PASS
COLLECTION_GAP_SEMANTICS=PASS
HOT_TRANSPORT_INTEGRITY=PASS
NO_DIRECT_AGENT_PROVIDER_ACCESS=PASS
NO_SECOND_DATA_AUTHORITY=PASS
```

Только затем отдельный versioned provider-policy transition может дать:

```text
BINANCE_USDM_VPS_RUNTIME=ACTIVE
```
