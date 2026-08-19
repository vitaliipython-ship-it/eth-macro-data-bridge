# D9 operational status и canonical agent usage v1

## Назначение

Этот документ фиксирует post-implementation human/agent view ETH-D9. Он объясняет текущее состояние и безопасный маршрут потребления данных, но **не является machine authority** и не активирует D9.

Current portability correction (2026-08-19):

```text
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=COMPLETE_WITH_PUBLICATION_PORTABILITY_GAP_IDENTIFIED
D9_CANONICAL_D8_PUBLICATION=NOT_IMPLEMENTED
D9_AUTHORITY=NOT_ACTIVE
RESOLUTION_PLAN_V2_TARGET_CONTRACT_RECONCILED=YES
RESOLUTION_PLAN_V2_SCHEMA_TRANSITION_DEFINED=YES
RESOLUTION_PLAN_V2_RUNTIME_MIGRATION=PENDING_PRE_ACTIVATION
RESOLUTION_PLAN_V2_ACTIVE=NO
D6_RESOLUTION_PLAN_V1_ACTIVE=YES
```

The 2026-08-17 block below is retained as a historical documentation-closure snapshot.

Каноническое состояние на момент documentation closure 2026-08-17:

```text
D9_1=PASS
D9_2=PASS
D9_3_SOURCE=PASS
D9_4_SOURCE=PASS
D9_5_SOURCE=PASS
D9_SOURCE_CONTOUR=COMPLETE

D9_ACTIVE=NO
REGULAR_GRID_D9_AUTHORITY=NOT_ACTIVE
ACTIVE_D6_ROUTE=ACTIVE
ACTIVE_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
D9_V2_STATUS=SOURCE_QUALIFIED_NOT_ACTIVE
DEFAULT_ACTIVE=false
```

Source implementation status и active authority status — разные оси. D9 source contour завершён, но production authority не переключена.

## Что D9 фактически реализовал

D9 расширяет существующую ONLINE → HISTORY lifecycle без второго resolver, второго committed catalog или второго reader family:

```text
CURRENT / HOT
      │ FORWARD ARCHIVING
      ▼
HISTORY / WARM
      │ verified SEALING
      ▼
HISTORY / COLD
```

Реализованы и source-qualified:

- D9.1 — successor contracts/schemas/shared lifecycle primitives;
- D9.2 — HOT→WARM для существующих qualified providers, collection-run ledger и revision evidence;
- D9.3 — atomic WARM→COLD candidate sealing, finalization/revision-lag policy, immutable successor semantics и remote publication/read-back machinery;
- D9.4 — ResolutionPlan v2 candidate и typed reader semantics в тех же public resolver/reader entrypoints;
- D9.5 — Research provenance successor с `SEMANTIC_RECEIPT` при сохранении `LEGACY_PHYSICAL`.

Это **не** означает, что D9 COLD generations уже являются active authority.

## Что active прямо сейчас

Текущий default route остаётся D6 / ResolutionPlan v1:

```text
Agent
→ AGENTS.md
→ bridge-contract.json
→ canonical_paths.capability_index
→ tools/capability_index.py
→ ResolutionPlan v1
→ tools/history_access.py
→ canonical manifests/resources
→ verified WARM / legacy COLD
→ normalized output
→ diagnostics
→ receipt
```

`tools/capability_index.py` поддерживает v1 и v2, но CLI default `--plan-version` остаётся `1`. `tools/history_access.py` понимает обе версии плана, однако v2 выбирается только когда сам ResolutionPlan имеет v2 discriminator.

Ключевой принцип:

> **AGENT REQUESTS SEMANTICS, NOT STORAGE.**

## Что задаёт агент

Агент формулирует semantic request:

- `series_id`;
- range `[from,to)` или поддерживаемую observation identity;
- `cutoff` для PIT, когда применимо;
- mode/current policy, когда поддерживается выбранной plan version;
- output format.

Агент **не задаёт и не угадывает**:

- Release tag;
- asset name / asset id;
- resource path;
- GitHub URL;
- SHA locator;
- WARM path;
- legacy COLD path;
- D9 generation path;
- VPS filesystem path;
- provider URL.

Physical locator появляется только после canonical semantic resolution.

## Agent-callable transport сегодня

Current hosted agent transport уже существует:

```text
GitHub Issue: [history-read]
→ .github/workflows/history-consumer-read.yml
→ tools/history_consumer.py
→ canonical resolver
→ ResolutionPlan v1
→ canonical reader
→ receipt + diagnostics + ephemeral artifact
```

Issue, workflow run и ephemeral artifact — **TRANSPORT / EVIDENCE**, не market-data authority.

Если canonical reader/hosted adapter невозможно выполнить, результат:

```text
DATA_TRANSPORT_BLOCKED
```

Не разрешается заменять canonical history прямым provider API или угадывать physical storage.

## Практические semantic requests

### Example A — regular historical OHLCV

Current default D6/v1 request:

```json
{
  "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
  "from_utc": "2026-08-01T00:00:00Z",
  "to_utc": "2026-08-08T00:00:00Z",
  "cutoff_utc": null,
  "mode": "strict",
  "output_format": "csv"
}
```

Назначение: finalized regular historical candles без physical locator.

### Example B — lower-TF pivot reconstruction

Current default D6/v1 request:

```json
{
  "series_id": "spot.binance-spot.ETHUSDT.ohlcv.5m",
  "from_utc": "2025-08-24T18:30:00Z",
  "to_utc": "2025-08-24T20:00:00Z",
  "cutoff_utc": null,
  "mode": "strict",
  "output_format": "csv"
}
```

Назначение: узкий M5 slice для Wave/PIVOT evidence. Агент не определяет storage partition.

### Example C — D9 v2 candidate PIT/revisable semantics

Это **candidate-semantics example, не текущий default route** до activation:

```json
{
  "series_id": "derivatives.kraken-futures.PI_ETHUSD.open-interest",
  "from_utc": "2026-08-16T00:00:00Z",
  "to_utc": "2026-08-17T00:00:00Z",
  "cutoff_utc": "2026-08-17T00:00:00Z",
  "mode": "strict",
  "current_policy": "FINALIZED_ONLY",
  "output_format": "json"
}
```

`cutoff` ограничивает point-in-time knowledge. `current_policy` относится к v2 resolver semantics; normal production consumer до D9 activation остаётся на v1/default contract. Никакой Release/VPS/provider locator в request не передаётся.

## D9 v2 successor semantics

D9.4 уже source-qualified:

- `market-data-resolution-plan/2.0.0`;
- `FIXED_GRID`;
- `SAMPLED_SCHEDULE`;
- explicit `COLLECTION_GAP`;
- PIT provider revisions;
- multi-generation D9 COLD candidate composition;
- COLD→WARM composition;
- optional explicit provisional/current inclusion;
- deterministic plan/output receipt/fingerprint;
- typed non-OHLCV/sampled observations.

Но:

```text
DEFAULT_ROUTE=V1
D9_V2=SOURCE_QUALIFIED_CANDIDATE
D9_ACTIVE=NO
```

После будущей activation внешний mental model агента не меняется:

```text
series_id + semantic request
→ same resolver family
→ ResolutionPlan
→ same reader family
```

Изменится только canonical internal physical resolution:

```text
legacy COLD + D9 COLD generations + WARM
(+ qualified provisional HOT only when explicitly requested and active)
```

Storage всё равно не выбирает агент.

## Почему D9 ещё не active

Причина — **production physical activation gate**, а не отсутствие implementation.

До переключения authority нужны реальные доказательства:

1. production-eligible completed generation;
2. exact frozen WARM source;
3. deterministic Build A/B;
4. immutable D9 COLD publication;
5. remote binary read-back;
6. exact remote asset membership;
7. remote size match;
8. remote SHA-256 match;
9. real semantic read через legacy COLD → D9 COLD → WARM без hidden gap/duplicates/substitution;
10. отдельный minimal activation PR;
11. post-activation semantic qualification.

До этого legacy D6 authority остаётся active.

## Текущая календарная граница

Это объяснение относится к состоянию на 2026-08-17 и **не является вечным hard-coded contract**.

Machine policy в `contracts/d9-sealing-candidate.json`:

```text
REGULAR_GRID_PERIOD_POLICY=COMPLETED_MONTH_ONLY
ACTIVE_PERIOD_SEALING=false
regular_grid_default_finalization_lag_seconds=86400
PROVIDER_REVISABLE_SNAPSHOT revision lag=172800
effective_cutoff_rule=MAX_APPLICABLE_CONSTRAINT
```

August 2026 ещё active/incomplete:

```text
PERIOD_END=2026-09-01T00:00:00Z
EARLIEST_THEORETICAL_BOUNDARY=2026-09-03T00:00:00Z
```

Это **не обещание publication**. Реальная eligibility дополнительно требует complete expected membership, applicable revision evidence/stabilization, source consistency и PASS результата sealer `detect`.

## Production sealer уже существует

Не создавать второй publisher workflow.

Canonical publication route:

```text
.github/workflows/seal-history.yml
→ tools/deep_history/history_sealer.py detect
→ tools/deep_history/history_sealer.py publish
→ immutable remote candidate publication
→ remote read-back / membership / size / SHA checks
→ history/generations/* + history/generation-index.json candidate metadata
```

Workflow сохраняет `history/release-manifest.json` как legacy authority, не очищает WARM и не активирует D9.

После первой реально eligible generation следующий этап — выполнить этот repository-owned route, проверить remote publication, затем реальный D9.3+D9.4 cross-boundary read и только после PASS открыть отдельный activation PR.

## D9.5 Research provenance

Research поддерживает две совместимые формы market-data provenance:

- `LEGACY_PHYSICAL` — историческая physical provenance остаётся валидной;
- `SEMANTIC_RECEIPT` — future materialization может использовать structured semantic authority без обязательного manifest/resource path.

`SEMANTIC_RECEIPT` содержит как минимум:

- exact Data Bridge head;
- `series_id`;
- exact request identity;
- `resolution_plan_sha256`;
- `output_sha256`;
- `observation_count`;
- finality;
- revision/PIT context, когда применимо.

Issue number, workflow run, artifact и Release evidence — transport/forensic evidence, не semantic authority. Historical Research objects не fake-migrate.

## Machine SSOT hierarchy

Human docs объясняют authority, но не переопределяют её.

- route/provider policy authority: `bridge-contract.json`;
- D9 sealing/activation candidate policy: `contracts/d9-sealing-candidate.json`;
- schema authorities: D9 schemas under `schema/`;
- semantic resolver: `tools/capability_index.py`;
- reader: `tools/history_access.py`;
- consumer adapter: `tools/history_consumer.py`;
- WARM→COLD sealer: `tools/deep_history/history_sealer.py`;
- production sealer workflow: `.github/workflows/seal-history.yml`;
- Research route authority: `eth-macro-research/research-contract.json`;
- Research provenance schema: `eth-macro-research/control/schemas/market-data-ref.schema.json`.

## Forbidden agent behavior

Запрещено:

- сканировать Git tree в поиске нужного candle file;
- выводить year/month partition из даты;
- угадывать Release tag/asset/path/URL;
- вручную выбирать legacy COLD vs WARM vs D9 COLD;
- обращаться к provider как replacement при canonical route failure;
- копировать raw market history в Research;
- читать VPS filesystem для разрешения historical market data;
- считать transport identity market-data authority.

Правильно: semantic resolver first. Если canonical execution недоступен — `DATA_TRANSPORT_BLOCKED`.

## High-cardinality и D8

High-cardinality остаётся отдельным bounded blocker:

```text
D9_2_HIGH_CARDINALITY_WARM_RELEASE=BLOCKED
HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_PENDING_VERSIONED_BACKEND_OR_D8_RUNTIME_SEAM_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

Причина: published GitHub prerelease фактически immutable; mutable-in-place backend assumption не используется. D9 sealing contract держит high-cardinality COLD sealing disabled fail-closed.

D8 boundary:

```text
D8_VPS_RUNTIME=NOT_ACTIVE
VPS_IS_MARKET_DATA_AUTHORITY=false
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_VPS_TARGET=REQUIRED
BINANCE_USDM_VPS_RUNTIME=NOT_ACTIVE
BINANCE_USDM_ACTIVE_PROVIDER=false
```

D9 documentation не активирует D8 или Binance USD-M.

## Evidence matrix

PR — forensic pointer на implementation/qualification history; machine authority остаётся current repository state.

| Stage | Forensic pointer | Result | Authority status |
|---|---|---|---|
| D9 planning / lifecycle target | Data Bridge PR #31; Research PR #2, #3 | accepted planning/docs | not activation |
| D9.1 | Data Bridge PR #33 | source + Actions PASS | candidate, D6 unchanged |
| D9.2 | Data Bridge PR #34 | source/live existing-provider PASS | candidate, D6 unchanged |
| D9.3 | Data Bridge PR #63 | atomic sealing/finalization/PIT source PASS | candidate COLD only |
| D9.4 | Data Bridge PR #67 | v2 resolver/reader candidate PASS | v1 remains default |
| D9.5 | Research PR #6 | semantic provenance integration PASS | Research compatibility, no D9 activation |

## Remaining gates

| Capability | Source | Active | Remaining gate |
|---|---|---|---|
| Regular grid D9 | PASS | NO | first eligible completed production generation + real publication/read-back + cross-boundary proof + activation PR |
| Remote publication | implemented | NOT_RUN | no eligible completed production generation yet |
| Real D9.3+D9.4 cross-boundary | implemented qualification route | NOT_RUN | requires real published D9 COLD generation |
| Activation | source-ready | NOT_RUN | requires all production gates PASS |
| WARM cleanup | implemented as disabled | NOT_RUN / NOT_YET_ALLOWED | publication + continuity/overlap/cross-boundary + retention/subsequent-cycle gates |
| High cardinality | partial source support | BLOCKED | versioned backend or qualified D8 runtime seam decision |
| D8 VPS | contract seam captured | NOT_ACTIVE | separate D8 qualification |
| Binance USD-M | historical evidence preserved | NOT_ACTIVE | GitHub runtime disabled; qualified VPS provider-policy transition required |

Known non-blocking follow-up: `D9-POLICY-DUPLICATION-001` (MEDIUM) — Kraken stabilization literal duplication; это отдельный refactor, не activation gate.

## Operational conclusion

```text
D9_SOURCE_CONTOUR=COMPLETE
CURRENT_ACTIVE_AUTHORITY=D6_RESOLUTION_PLAN_V1
D9_V2_STATUS=SOURCE_QUALIFIED_NOT_ACTIVE
D9_ACTIVE=NO
WHY_NOT_ACTIVE=FIRST_REAL_D9_COLD_PRODUCTION_GENERATION_AND_CROSS_BOUNDARY_PROOF_NOT_YET_AVAILABLE
```

Следующий physical stage:

```text
first actual eligible completed generation
→ immutable D9 COLD publication
→ remote read-back / SHA / size / membership proof
→ real legacy COLD → D9 COLD → WARM semantic read
→ separate activation PR
```
