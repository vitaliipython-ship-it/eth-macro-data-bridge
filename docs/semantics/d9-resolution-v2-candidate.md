# D9.4 ResolutionPlan v2 / unified reader candidate

## Статус

```text
D9_4_SOURCE_CANDIDATE=QUALIFIED_ON_BRANCH
D9_ACTIVE=NO
ACTIVE_D6_ROUTE=UNCHANGED
ACTIVE_DEFAULT_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
SECOND_RESOLVER=NO
SECOND_READER_FAMILY=NO
SECOND_COMMITTED_CAPABILITY_CATALOG=NO
REMOTE_D9_3_D9_4_PUBLICATION_QUALIFICATION=NOT_RUN
```

Этот документ описывает **implementation-facing candidate**, а не activation record.
Planning authority остаётся в `eth-macro-research/docs/integrations/market-data-history-lifecycle-v1.md` и plan review.

## 1. Один semantic route

D9.4 расширяет существующие entrypoints:

```text
tools/capability_index.py
tools/history_access.py
```

Default остаётся D6/v1.

Явный source-candidate request v2:

```text
python tools/capability_index.py resolve <series_id> \
  --from <UTC> \
  --to <UTC> \
  --plan-version 2
```

Reader выбирает v1/v2 по `ResolutionPlan.schema_version`; отдельного COLD-only или non-OHLCV reader нет.

`history/capability-index-v2.json` намеренно не существует. Capability v2 является deterministic runtime projection из active v1 catalog + canonical manifests/collection ledger/revision/generation control plane.

## 2. Series semantics

V2 discriminator поддерживает:

```text
OHLCV
SCALAR_TIME_SERIES
STRUCTURED_TIME_SERIES
SNAPSHOT_SERIES
OPTION_SURFACE
ORDER_BOOK_SNAPSHOT
```

Coverage:

```text
FIXED_GRID
SAMPLED_SCHEDULE
EVENT_DRIVEN
```

Current D9.4 candidate реально квалифицирует `FIXED_GRID` и `SAMPLED_SCHEDULE`.

Kraken Futures profile не агрегирует разные revision classes в один semantic profile. `STRICT_OVERLAP_REQUIRED`, `WINDOW_ANCHORED_CUMULATIVE` и `PROVIDER_REVISABLE_SNAPSHOT` сохраняются из `derivatives/metric-semantics.json`.

## 3. Fixed-grid continuity

Для `FIXED_GRID`:

- expected grid начинается с `effective_start_ms`;
- leading provider-history boundary (`PROVIDER_HISTORY_LIMIT` / forward-only start) не классифицируется как internal gap;
- missing timestamp внутри доступного диапазона:
  - strict = `DATA_GAP`;
  - permissive = explicit degraded diagnostics;
- synthetic fill запрещён.

## 4. Sampled history

Текущие ledger-declared sampled capabilities:

```text
options.deribit-options.ETH.surface-snapshots
liquidity.orderbook-snapshots
derivatives.deribit-perpetual.current-snapshot
```

Physical WARM authority:

```text
history/collection-runs/**/runs.json
  → exact OBSERVED_STATE.snapshot_ref
  → exact SHA-256 / size bound resource
```

`COLLECTION_GAP` остаётся gap evidence. Reader не строит continuous grid и не копирует соседнее snapshot state.

Текущий Git high-cardinality snapshot plane — transitional. `contracts/d9-sealing-candidate.json` блокирует COLD sealing для high-cardinality snapshots до versioned Release-WARM либо D8 runtime-seam decision. D9.4 **не объявляет** unqualified Release-WARM authority.

## 5. COLD generations

Regular-grid v2 resolver умеет выбирать:

```text
legacy Release COLD
→ qualified D9 generation COLD
→ WARM tail
```

Candidate generation видима только при explicit `qualification_mode`; default authority её игнорирует.

`ACTIVE` generation допустима только если publication manifest уже содержит:

```text
publish_status=PASS
readback_status=PASS
size_match=PASS
sha256_match=PASS
overlap_proof=PASS
cross_boundary_semantic_read=PASS
activation_status=ACTIVE
release_immutable=true
```

D9.3 COLD assets v1.1 self-describing:

```text
market-data-cold-asset/1.1.0
record_encoding:
  POSITIONAL_COLUMNS
  TIMESTAMP_VALUE
  SNAPSHOT_OBJECT
```

Record encoding входит в successor generation fingerprint; WARM cleanup не требуется reader-у для декодирования immutable COLD bytes.

Sampled `SNAPSHOT_OBJECT` COLD reader path source-qualified synthetic fixture-ом. Physical sampled COLD resolver promotion остаётся blocked, пока high-cardinality sealing disabled by contract.

## 6. Point-in-time revisions

Для `PROVIDER_REVISABLE_SNAPSHOT` ResolutionPlan связывает:

- exact revision evidence resource SHA/size;
- `revision_id`;
- `effective_timestamp`;
- `known_at`;
- exact source observation resource SHA/size;
- `revision_of`;
- previous value fingerprint.

Reader применяет только revision, реально known к `cutoff_ms`. Source/evidence tamper fail-closed.

## 7. HOT / current policy

Default:

```text
FINALIZED_ONLY
```

`HOT_CURRENT_RESOURCE` принимается reader-ом только при:

```text
INCLUDE_CURRENT_PROVISIONAL
```

Observation и receipt маркируются provisional. Resolver пока не генерирует HOT physical segment, потому что D8 qualified runtime HOT seam остаётся `NOT_ACTIVE`.

## 8. Diagnostics / receipt

V2 reader возвращает:

- normalized observations;
- exact source descriptors;
- internal fixed-grid gaps;
- collection gaps;
- provider boundary evidence;
- revisions applied;
- overlap dedupe evidence;
- provisional/finalized state;
- `resolution_plan_sha256`;
- deterministic `output_sha256`;
- observation count.

## 9. Qualification boundary

Source qualification выполняется repository-owned GitHub Actions с real `actions/checkout`.

Source PASS не заменяет remote D9.3+D9.4 publication qualification.

До появления eligible COLD generation и repository-owned publication run:

```text
REMOTE_PUBLICATION_QUALIFICATION=NOT_RUN
D9_ACTIVE=NO
```

Обязательные future remote gates остаются:

```text
WORKFLOW_CHECKOUT=PASS
CANDIDATE_PUBLICATION=PASS
REMOTE_BINARY_READBACK=PASS
REMOTE_SIZE_MATCH=PASS
REMOTE_SHA256_MATCH=PASS
OVERLAP_PROOF=PASS
CROSS_BOUNDARY_SEMANTIC_READ=PASS
```
