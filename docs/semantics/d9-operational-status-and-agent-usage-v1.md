# D9 operational status и canonical agent usage v1

## Назначение

Этот документ фиксирует post-implementation human/agent view ETH-D9. Он объясняет текущее состояние и безопасный маршрут потребления данных, но **не является machine authority** и не активирует D9.

Current portability status (post-A2 reconciliation):

```text
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
D9_REAL_D8_RUNTIME_TO_CANONICAL_WARM=PHYSICAL_QUALIFICATION_PASS
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
RESOLUTION_PLAN_V2_TARGET_CONTRACT_RECONCILED=YES
RESOLUTION_PLAN_V2_SCHEMA_TRANSITION_DEFINED=YES
RESOLUTION_PLAN_V2_RUNTIME_MIGRATION=PENDING_PRE_ACTIVATION
RESOLUTION_PLAN_V2_ACTIVE=NO
D6_RESOLUTION_PLAN_V1_ACTIVE=YES

D8_STATUS_SEMANTICS=RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE
D8_LIVE_RUNTIME_STATUS_CONTINUOUSLY_VERIFIED=false
D8_LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_ACTION=true
D8_AUTHORITY_ACTIVE=false
CURRENT_D8_STATE_SCHEMA_VERSION=2
CURRENT_D8_SPOOL_TOTAL=20
CURRENT_D8_PENDING_TOTAL=0
CURRENT_D8_FORWARDED_TOTAL=20
A1_FRESH_CHECKPOINT_V2=PASS
A2_CANONICAL_PUBLICATION=PASS
A2_CANONICAL_ACK=PASS
A2_PENDING_TO_FORWARDED=PASS
A2_IDEMPOTENT_REPLAY=PASS
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=true
NEXT_REQUIRED_STAGE=FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION
```

Current reconciled machine status view is `contracts/d8-a2-physical-qualification-status-v1.json`. It records accepted A1/A2 physical evidence and is not a continuously refreshed VPS probe. The predecessor `contracts/d8-shadow-post-reset-status-v1.json` remains an immutable historical post-reset reconciliation snapshot with its earlier `0/0/0`, `NEXT/PENDING` observation point; it must not be read as current status after accepted A2 qualification. Fresh server-side live readback remains mandatory before any future physical mutation or physical qualification.

Каноническое состояние на момент documentation closure 2026-08-17 ниже сохранено как исторический documentation-closure snapshot:

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

Source implementation, repository/Actions source qualification, real runtime physical qualification and active authority status remain independent axes. Publication Port source and physical A1/A2 qualification are complete; production authority is still not switched.

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
- D9.5 — Research provenance successor с `SEMANTIC_RECEIPT` при сохранении `LEGACY_PHYSICAL`;
- Canonical Publication Port — PR #118: deterministic PublicationBatch → GITHUB_FIRST_V1 → remote durability/read-back → exact integrity binding → control-plane/resolver visibility → existing reader → whole-batch `CANONICAL_PUBLICATION_ACK`.

Source qualification run `32318193771` proved Publication Port source semantics and remote GitHub behavior. Separate owner-accepted A1/A2 physical evidence now proves the real VPS_SHADOW → canonical WARM path for the exact 20-member batch, including whole-batch ACK, `PENDING→FORWARDED`, and idempotent replay.

Old pre-reset physical evidence remains preserved: `261` PENDING (`62` checkpoint-v2 eligible + `199` legacy pre-checkpoint-v2) are forensic-only, restore remains unauthorized, and they were not used as A1/A2 qualification input.

Это **не** означает, что D9 COLD generations уже являются active authority или что production WARM forwarder deployed.

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

A1/A2 physical WARM qualification is no longer a remaining gate. Accepted facts now include:

```text
NEW_REAL_CHECKPOINT_V2_DATA=COMPLETE
PHYSICAL_PUBLICATION_PORT=QUALIFIED
CANONICAL_PUBLICATION_ACK=PASS
PENDING_TO_FORWARDED=PASS
IDEMPOTENT_REPLAY=PASS
```

Physical qualification is not activation. D8/D9 remain inactive, Binance USD-M remains `DISABLED_BY_POLICY`, legacy GitHub production acquisition remains active, production WARM forwarding is not scheduled/deployed, and D6/ResolutionPlan v1 remains default.

The next real predecessor comes from `contracts/d9-sealing-candidate.json`:

```text
STATUS=CANDIDATE_NOT_ACTIVE
REGULAR_GRID_PERIOD_POLICY=COMPLETED_MONTH_ONLY
ACTIVE_PERIOD_SEALING=false
NEXT_REQUIRED_STAGE=FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION
REAL_D9_COLD_PHYSICAL_QUALIFICATION=BLOCKED_UNTIL_ELIGIBLE_GENERATION
```

Only after a production-eligible completed generation exists may a separately owner-authorized COLD qualification execute:

1. freeze exact eligible WARM source;
2. deterministic Build A/B;
3. immutable D9 COLD publication;
4. remote binary read-back;
5. exact remote asset membership;
6. remote size match;
7. remote SHA-256 match;
8. real semantic read through legacy COLD → D9 COLD → WARM without hidden gap/duplicates/substitution;
9. separate minimal activation PR only after PASS;
10. post-activation semantic qualification.

Old `261` PENDING remain forensic evidence and are not restored or consumed by this route.

`GITHUB_FIRST_V1` publication does not require `GITHUB_TOKEN` inside D8 runtime. `VPS_SHADOW` authentication remains `D8_RUNTIME_TOKEN`; publication credentials belong to a separately authorized publication executor/adapter. Public D8 ingress is not required.

## Текущая календарная граница

Эта calendar example относится к August 2026 и **не является вечным hard-coded contract**.

Machine policy в `contracts/d9-sealing-candidate.json`:

```text
REGULAR_GRID_PERIOD_POLICY=COMPLETED_MONTH_ONLY
ACTIVE_PERIOD_SEALING=false
regular_grid_default_finalization_lag_seconds=86400
PROVIDER_REVISABLE_SNAPSHOT revision lag=172800
effective_cutoff_rule=MAX_APPLICABLE_CONSTRAINT
```

August 2026 active/incomplete до period boundary:

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

After the first actually eligible generation, the next COLD contour is to execute this repository-owned route, verify remote publication, then perform the real D9.3+D9.4 cross-boundary read. That future physical task is not executed by status reconciliation.

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
- liquidity S1 architecture machine owner: `contracts/liquidity-s1-semantic-contract-v1.json` (`runtime_active=false`, additive, no D6/D9 activation);
- D8 current reconciled A1/A2 physical-qualification snapshot authority: `contracts/d8-a2-physical-qualification-status-v1.json`;
- historical post-reset predecessor snapshot: `contracts/d8-shadow-post-reset-status-v1.json`;
- live D8 physical state authority before physical action: server-side execution/readback;
- D8 source/runtime behavior authority: `contracts/d8-runtime-candidate.json`;
- D8→D9 publication/ACK boundary: `contracts/d8-d9-forwarding-v1.json`;
- D9 sealing/activation candidate policy: `contracts/d9-sealing-candidate.json`;
- schema authorities: D9 schemas under `schema/`;
- semantic resolver: `tools/capability_index.py`;
- reader: `tools/history_access.py`;
- consumer adapter: `tools/history_consumer.py`;
- WARM→COLD sealer: `tools/deep_history/history_sealer.py`;
- production sealer workflow: `.github/workflows/seal-history.yml`;
- Research route authority: `eth-macro-research/research-contract.json`;
- Research provenance schema: `eth-macro-research/control/schemas/market-data-ref.schema.json`.

Historical `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md` remains an exact source-binding handoff and is not current VPS deployment-status authority.

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
D8_STATUS_SEMANTICS=RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE
D8_LIVE_RUNTIME_STATUS_CONTINUOUSLY_VERIFIED=false
D8_LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_ACTION=true
D8_AUTHORITY_ACTIVE=false
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
| Canonical Publication Port source | Data Bridge PR #118; run 32318193771 | source + real GitHub remote proof PASS | source merged/qualified |
| D8 state evolution policy | Data Bridge PR #130 | versioned state policy merged | no activation |
| Owner-authorized VPS_SHADOW reset/deploy | external server execution evidence | forensic preservation + controlled reset + deployment PASS | historical predecessor snapshot |
| A1 fresh checkpoint-v2 | owner-accepted server evidence | 20 current-generation observations PASS | qualified, not activation |
| A2 physical canonical publication | batch `pub-0e3a…`; accepted server evidence | durability/read-back/resolver/reader/ACK/PENDING→FORWARDED/replay PASS | physically qualified, not active authority |

## Remaining gates

| Capability | Source | Active | Remaining gate |
|---|---|---|---|
| Canonical D8→WARM Publication Port | PASS / MERGED / PHYSICALLY QUALIFIED | NO | no WARM physical qualification gate remains; activation still separate |
| Real D8 VPS→canonical WARM | PHYSICAL PASS | NO | no activation implied; future operations require fresh live readback |
| Regular grid D9 | PASS | NO | first eligible completed production generation + real COLD publication/read-back + cross-boundary proof + activation PR |
| D9 COLD remote publication | implemented | NOT_RUN | blocked until production-eligible completed generation exists |
| Real D9.3+D9.4 cross-boundary | implemented qualification route | NOT_RUN | requires real published D9 COLD generation |
| Activation | source-ready | NOT_RUN | requires all production COLD gates PASS and separate owner transition |
| WARM cleanup | implemented as disabled | NOT_RUN / NOT_YET_ALLOWED | continuity/overlap/cross-boundary + retention/subsequent-cycle gates |
| High cardinality | partial source support | BLOCKED | versioned backend or qualified runtime seam decision |
| D8 VPS | deployed VPS_SHADOW | NOT_ACTIVE | A1/A2 physically qualified; no authority activation |
| Binance USD-M | A1 physical evidence exists | NOT_ACTIVE | normal mode remains DISABLED_BY_POLICY; separate provider-policy transition required |

Known non-blocking follow-up: `D9-POLICY-DUPLICATION-001` (MEDIUM) — Kraken stabilization literal duplication; это отдельный refactor, не activation gate.

## Operational conclusion

```text
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
REAL_D8_VPS_PUBLICATION_QUALIFIED=YES
CANONICAL_PUBLICATION_QUALIFIED=true
PHYSICAL_VPS_D8_TO_D9_QUALIFIED=true
CROSS_TIER_SEMANTIC_READ_QUALIFIED=true
PHYSICAL_PUBLICATION_PORT_E2E_QUALIFIED=true
PRODUCTION_WARM_FORWARDER_DEPLOYED=false
CURRENT_ACTIVE_AUTHORITY=D6_RESOLUTION_PLAN_V1
D9_V2_STATUS=SOURCE_QUALIFIED_NOT_ACTIVE
D8_ACTIVE=NO
D9_ACTIVE=NO

D8_STATUS_SEMANTICS=RECONCILED_ACCEPTED_PHYSICAL_EVIDENCE_NOT_LIVE_PROBE
D8_LIVE_SERVER_READBACK_REQUIRED_BEFORE_PHYSICAL_ACTION=true
OLD_PRE_PRODUCTION_SHADOW=HISTORICAL
FORENSIC_PRESERVATION=COMPLETE
CONTROLLED_SHADOW_RESET=COMPLETE
CURRENT_D8_DEPLOYMENT=COMPLETE
CLEAN_VPS_SHADOW=COMPLETE
NEW_REAL_CHECKPOINT_V2_DATA=COMPLETE
PHYSICAL_PUBLICATION_PORT=QUALIFIED
FIRST_PRODUCTION_ELIGIBLE_COMPLETED_GENERATION=NEXT
REAL_D9_COLD_PHYSICAL_QUALIFICATION=BLOCKED_UNTIL_ELIGIBLE_GENERATION
ACTIVATION=NOT_AUTHORIZED
```

Next program stage is **not** another D8/A2 action. It is the first production-eligible completed generation under the current sealing policy. After eligibility, a separately owner-authorized `REAL_D9_COLD_PHYSICAL_QUALIFICATION` task may execute the existing sealer/publication/read-back/cross-boundary route. This reconciliation does not execute sealing, COLD publication, provider transition, cutover or activation.
