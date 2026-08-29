# Semantic contract: Market Data Capability & Resolution v1

## Статус

`D6.1 / D6.2A / D6.2B / D6.3 / D6.4 QUALIFIED / PASS`

D6.4 activation authority:

```text
QUALIFIED_SOURCE_HEAD=f90215c6581b2157a219f55d7aba9ecef5bf10b2
QUALIFICATION_RUN=31962611123
QUALIFICATION_JOB=95202800848
BRIDGE_CONTRACT_VERSION=1.1.0
CAPABILITY_ROUTE_DECLARED=PASS
CAPABILITY_INDEX_READ=PASS
LEGACY_MANIFEST_ROUTE=PASS
CAPABILITY_RESOLUTION=PASS
RESOLUTION_PLAN_AUTHORITY=PASS
CAPABILITY_NO_GUESSED_PATHS=PASS
RELEASE_ASSET_DOWNLOAD=PASS
RELEASE_ASSET_SHA256=PASS
RELEASE_TO_HOT_TAIL_SEAM=PASS
NO_PROVIDER_SUBSTITUTION=PASS
CAPABILITY_CONSUMER_PROOF=PASS
CONSUMER_PROOF=PASS
DEEP_HISTORY_TESTS=PASS
```

D6.4 activation publication:

```text
ACTIVATION_COMMIT=a2b96ccd551990671020ea1cdb83dfd24cda15d4
EXACT_MAIN_CI_RUN=31962865562 SUCCESS
EXACT_MAIN_CI_JOB=95203434474 SUCCESS
EXACT_MAIN_OVERLAP_RUN=31962865549 SUCCESS
EXACT_MAIN_OVERLAP_JOB=95203434463 SUCCESS
PR=2 MERGED
```

`ACTIVATION_COMMIT` — implementation/route activation authority. Последующий docs-only status commit может двигать `main`, но не заменяет этот activation identity и не требует перепривязки historical provenance.

Первый activation run `31962567844` доказал новый network-backed consumer route, но обнаружил один stale pre-D6.4 regression test, который всё ещё требовал отсутствия capability path. Assertion был обновлён на active-route contract; production/resolver/reader semantics не ослаблялись.

## Public route после D6.4

Канонический production discovery/resolution route теперь:

```text
AGENTS.md
  → bridge-contract.json
  → canonical_paths.capability_index
  → history/capability-index.json
  → tools/capability_index.py list|describe|resolve
  → market-data-resolution-plan/1.0.0
  → canonical physical manifest(s)
  → tools/history_access.py slice
  → verified Git WARM / immutable GitHub Release bytes
```

`bridge-contract.json` остаётся **единственной route/provider-policy authority**. Capability index является derived semantic discovery projection и не становится byte authority.

## Authority hierarchy

```text
bridge-contract.json                         ← route/provider-policy authority
        │
        ├── history/capability-index.json    ← derived discovery index
        │        │
        │        └── read-only resolver
        │                  │
        ▼                  ▼
physical manifests                   ResolutionPlan
        │                                  │
        ├── history/release-manifest.json  │
        ├── declared domain manifests      │
        │                                  │
        ▼                                  ▼
immutable Release / declared Git bytes ← history_access.py
```

Exact asset name, URL, SHA-256, size и physical boundaries принадлежат manifests/Releases, а не capability index.

## Backward compatibility

D6.4 additive activation не удаляет прежние routes:

```text
spot_history_manifest=history/manifest.json
release_history_manifest=history/release-manifest.json
legacy_manifest_route.status=SUPPORTED_BACKWARD_COMPATIBLE
```

Existing consumers могут продолжать читать declared manifests. Новые semantic consumers должны начинать с `bridge-contract.json`, а не hard-code-ить index/Release layout самостоятельно.

## Stable semantic identity

Grammar v1:

```text
<domain>.<provider_id>.<instrument>.<series>[.<interval>]
```

Representative identities:

```text
spot.binance-spot.ETHUSDT.ohlcv.1h
spot.kraken-spot.ETHUSD.ohlcv.1d
derivatives.kraken-futures.PI_ETHUSD.funding
derivatives.kraken-futures.PI_ETHUSD.cvd
derivatives.deribit-perpetual.ETH-PERPETUAL.ohlcv.1h
options.deribit-options.ETH.dvol.1h
```

`series_id` не содержит filename, year partition, Release URL или storage backend.

Qualified v1 содержит 61 cold semantic series и 6 reusable profiles.

## Discovery != Resolution != Consumption

### Discovery

`history/capability-index.json` отвечает на вопросы о наличии series, provider policy, `history_mode`, availability и semantic routes. Он не копирует exact physical depth или asset inventory.

### Resolution

`tools/capability_index.py resolve` принимает:

```text
series_id + [start,end) [+ point-in-time cutoff]
```

и возвращает deterministic `market-data-resolution-plan/1.0.0`. Release names/URLs не строятся по шаблону: exact locator/SHA берутся только из canonical physical authority. Unknown series, provider-policy mismatch, unresolved gap/seam и future-known point-in-time partition fail closed.

### Consumption

`tools/history_access.py` принимает только validated `ResolutionPlan`. Reader не создаёт второй resolver, не делает provider fallback и не синтезирует missing candles. WARM/COLD bytes SHA-pinned; merge deterministic; duplicates/gaps диагностируются явно.

## S1 liquidity — additive semantic extension

`contracts/liquidity-s1-semantic-contract-v1.json` defines accepted non-runtime S1 semantics inside the same Market Data Foundation contour. It does not create a second catalog/resolver/reader/collector. Semantic depth requests (`target_bps=250/500`) are checked against existing canonical resource coverage before any future provider acquisition; provider-specific depth knobs are not agent request fields.

## History/depth semantics

`history_mode`:

- `MAX_AVAILABLE`;
- `PROVIDER_LIMITED`;
- `FORWARD_ONLY`;
- `FROZEN_REFERENCE`;
- `UNAVAILABLE`.

Historical options surface и order-book backfill не фабрикуются. Forward-only capabilities остаются forward-only.

## Provider policy

`bridge-contract.json` остаётся provider-policy authority. `contracts/provider-contracts.json` документирует provider/API source contracts и не подменяет policy registry.

Binance USDⓈ-M остаётся:

```text
STATUS=DISABLED_BY_POLICY
CURRENT_COLLECTION=DISABLED_BY_POLICY
NETWORK_CALLS=0
SIGNAL_VOTE=EXCLUDED
```

Frozen archive не становится active capability/signal source.

## Determinism и четыре hard guardrails

1. `ResolutionPlan` — единственная input authority D6.2B reader-а.
2. Catalog — только derived projection, не второй SSOT.
3. Никаких guessed/hardcoded Release routes; locator/SHA идут из physical manifests.
4. WARM/COLD merge и integrity остаются deterministic и доказуемыми.

`tools/capability_index.py build` делает только canonical local reads, не вызывает provider API и не скачивает Release assets. Обычный hourly collector не перестраивает capability index.

## D6.3 qualification, сохранённая D6.4

```text
SOURCE_HEAD=76a09841dad36800525e599446ec93f91fa1524c
LIVE_RUN=31957353588 SUCCESS
LIVE_JOB=95189884017 SUCCESS
REPOSITORY_CI_RUN=31957353590 SUCCESS
TARGETED_TESTS=13/13 PASS
M5_TO_H1=PASS
M5_TO_H4=PASS
PHYSICAL_COLD_WARM_SEAM=PASS
MULTI_PROVIDER_READER_RESOLVER=PASS
```

Binance H1 interval `2023-03-24T13:00:00Z` остаётся explicit provider-native halt: strict reader fail-closed, permissive режим может маркировать только этот доказанный gap как degraded; synthetic fill запрещён.

## D6.4 consumer proof

Existing `tools/validation/consumer_proof.py` после activation:

1. читает `bridge-contract.json`;
2. разрешает capability path только из contract;
3. подтверждает backward-compatible legacy manifest route;
4. вызывает public semantic resolver;
5. сверяет COLD segment `asset_id/name/url/sha256` с exact `history/release-manifest.json`;
6. скачивает representative immutable Release assets и проверяет size/SHA;
7. подтверждает release→HOT seam и no-provider-substitution.

Изменения `bridge-contract.json` теперь входят в path trigger `.github/workflows/validate-repository.yml`, поэтому route-authority change не может обойти repository consumer proof.

## Scope D6.4

D6.4 **не менял**:

- provider acquisition;
- hourly collector/cadence;
- immutable Releases/COLD packaging;
- market-data rows;
- server/runtime;
- ETH Macro Watch;
- Research routing contract.

Research migration относится только к D6.5.

## Команды

```bash
python tools/capability_index.py validate
python tools/capability_index.py list
python tools/capability_index.py describe spot.binance-spot.ETHUSDT.ohlcv.1h
python tools/capability_index.py resolve \
  spot.binance-spot.ETHUSDT.ohlcv.1h \
  --from 2022-06-18T00:00:00Z \
  --to 2022-06-19T00:00:00Z \
  --format json
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

## Следующий gate

**D6.5 = PENDING / NEXT.** Только после D6.4 merge + exact-main CI можно мигрировать `eth-macro-research` на новый semantic route. Research не копирует capability index и продолжает pin-ить exact bridge commit + фактически использованный manifest/resource/release asset SHA-256 как physical provenance.
