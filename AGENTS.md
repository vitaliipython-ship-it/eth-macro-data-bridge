# AGENTS.md

## Назначение

Это первая и каноническая semantic точка входа для любого агента, который читает или изменяет `eth-macro-data-bridge`. Репозиторий является authority рыночных фактов; Elliott/NEoWave, гипотезы, сценарии и интерпретация принадлежат `eth-macro-research`.

Канонический язык документации — **русский**. Machine identifiers, provider names, schema fields, paths и commands сохраняются на английском.

## Канонический market-data route

Главный принцип: **AGENT REQUESTS SEMANTICS, NOT STORAGE**.

Не начинать с provider path, Release tag, asset filename, URL или Git tree scan.

Текущий active/default route:

```text
AGENTS.md
→ bridge-contract.json
→ canonical_paths.capability_index
→ semantic capability discovery
→ tools/capability_index.py
→ ResolutionPlan v1
→ tools/history_access.py
→ canonical manifests/resources
→ verified WARM / legacy COLD
→ normalized output
→ diagnostics
→ receipt
```

`bridge-contract.json` — route/provider-policy authority. Capability index — derived discovery layer, не byte authority. `ResolutionPlan` — единственный input authority reader-а. Physical locator/size/SHA приходит только из canonical control plane после semantic resolution.

Агент задаёт `series_id`, range/observation identity, cutoff когда применимо, mode/policy и output format. Агент не задаёт Release tag, asset/path/URL/SHA locator, WARM/COLD/generation path, VPS filesystem path или provider URL.

## Agent-callable historical read

Preferred local adapter текущего D6/v1 route:

```bash
python tools/history_consumer.py read \
  --series-id spot.binance-spot.ETHUSDT.ohlcv.1h \
  --from 2025-04-09T00:00:00Z \
  --to 2025-08-25T00:00:00Z \
  --mode strict \
  --format csv \
  --output candles.csv \
  --plan-output resolution-plan.json \
  --diagnostics-output diagnostics.json \
  --receipt-output receipt.json
```

`tools/history_consumer.py` не второй resolver: он вызывает canonical resolver и передаёт полученный `ResolutionPlan` canonical reader-у.

### Hosted connector transport

Если local reader недоступен, использовать `bridge-contract.json.semantic_resolution.agent_transport`:

```text
GitHub Issue: [history-read]
→ .github/workflows/history-consumer-read.yml
→ tools/history_consumer.py
→ resolver → ResolutionPlan → reader
→ receipt + diagnostics + ephemeral artifact
```

Issue/workflow/artifact — transport/evidence, не market-data authority. В request допустимы только semantic fields; asset/release/path/URL/SHA запрещены.

Если canonical transports недоступны:

```text
DATA_TRANSPORT_BLOCKED
```

Не заменять canonical history прямым provider API. Provider API может быть только отдельной corroboration, не replacement authority.

## Hard guardrails

1. `bridge-contract.json` — текущая machine route/provider authority.
2. `ResolutionPlan` — reader input authority.
3. Capability catalog/index — derived projection, не второй SSOT.
4. Не угадывать и не hard-code-ить Release/storage routes.
5. Никаких synthetic gap fills и silent provider substitution.
6. Runtime/Actions/VPS transport не становится market-data authority.
7. Raw market history не копируется в Research.
8. Binance USDⓈ-M остаётся `DISABLED_BY_POLICY`, пока contract явно не изменён после отдельной D8 qualification.
9. Historical options/order-book backfill не фабрикуется.
10. Immutable Release не переписывается in-place.
11. D9 source completeness не означает D9 activation.
12. Human docs не переопределяют machine contracts/schemas/runtime.

## D6 / D9 status

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=QUALIFIED/PASS/ACTIVE
D6.5=QUALIFIED/PASS/MERGED
D6.6=NEXT/PENDING/CLOSURE_COMPATIBILITY
AGENT_RUNTIME_HISTORY_TRANSPORT=ACTIVE

D9_1=PASS
D9_2=PASS
D9_3_SOURCE=PASS
D9_4_SOURCE=PASS
D9_5_SOURCE=PASS
D9_SOURCE_CONTOUR=COMPLETE

D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVE=NO
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
ACTIVE_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
D9_V2=SOURCE_QUALIFIED_CANDIDATE
D9_ACTIVATION=PENDING_FIRST_REAL_PRODUCTION_COLD_QUALIFICATION
```

D9 v2 уже реализован в тех же `tools/capability_index.py` / `tools/history_access.py`, но default `--plan-version` остаётся v1. Не создавать второй resolver/catalog/reader и не считать v2 active без отдельной activation transition.

Полный operational status, agent examples, machine SSOT hierarchy, remaining physical gates и D9.5 provenance rules:

`docs/semantics/d9-operational-status-and-agent-usage-v1.md`.

Implementation-facing lifecycle background:

`docs/semantics/market-data-history-lifecycle-v1.md`.

## Почему D9 ещё не active

Причина — production physical gate, а не незавершённый source contour.

Regular-grid D9 использует `COMPLETED_MONTH_ONLY`; active-period sealing выключен. До authority switch нужны реальная eligible generation, frozen WARM source, deterministic sealing, immutable publication, remote read-back/membership/size/SHA proof, реальный legacy COLD → D9 COLD → WARM semantic read и отдельный activation PR.

Production publisher уже существует:

```text
.github/workflows/seal-history.yml
→ tools/deep_history/history_sealer.py detect
→ tools/deep_history/history_sealer.py publish
→ immutable candidate publication/read-back
```

Не писать второй publisher.

## D8 / high-cardinality boundary

```text
D8_VPS_RUNTIME=NOT_ACTIVE
VPS_IS_MARKET_DATA_AUTHORITY=false
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_VPS_TARGET=REQUIRED
BINANCE_USDM_VPS_RUNTIME=NOT_ACTIVE
BINANCE_USDM_ACTIVE_PROVIDER=false

HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_PENDING_VERSIONED_BACKEND_OR_D8_RUNTIME_SEAM_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

Published GitHub prerelease оказался immutable; mutable-in-place Release assumption не использовать.

## Provider/history semantics

`history_mode` values:

```text
MAX_AVAILABLE
PROVIDER_LIMITED
FORWARD_ONLY
FROZEN_REFERENCE
UNAVAILABLE
```

Known Binance H1 `2023-03-24T13:00:00Z` provider-native no-trading gap остаётся fail-closed в strict mode; synthetic candle запрещён.

## Выполнение и validation

```bash
python -m compileall -q src tools tests
PYTHONPATH=src:tools/deep_history python tools/validation/validate.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_v4.py
PYTHONPATH=src:tools/deep_history python tools/validation/validate_history.py
PYTHONPATH=src:tools/deep_history python tools/validation/consumer_proof.py
python tools/capability_index.py validate
python -m unittest discover -s tests/deep_history -p 'test_*.py' -v
```

Network-backed historical materialization и production sealing qualification остаются отдельными repository-owned workflows.

## Ownership boundaries

Без отдельной authority-changing task не изменять:

- collector/cadence/provider acquisition;
- `bridge-contract.json` activation/default route;
- immutable COLD assets;
- raw/generated market rows;
- server/VPS acquisition plane;
- D8/Binance USD-M provider policy;
- Research wave/hypothesis/current objects;
- WARM retention/cleanup.

Новый mechanism допускается только если закрывает доказанный operational risk, проще существующих вариантов и уменьшает ручную работу следующего агента/инженера.

## D8 VPS unified acquisition runtime source candidate

- Canonical source contract: `contracts/d8-runtime-candidate.json`.
- Operational source semantics: `docs/semantics/d8-vps-unified-acquisition-runtime-v1.md`.
- Server handoff: `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md`.
- Entrypoint: `python -m d8_service`; container: `Dockerfile.d8`.
- Status: `SOURCE_CANDIDATE_NOT_DEPLOYED`; VPS shadow source supported, VPS_ACTIVE forbidden by candidate.
- D8 does not change `D9_ACTIVE=NO`, `ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1`, the hourly GitHub production acquisition schedule, or Binance USD-M GitHub `DISABLED_BY_POLICY` / `network_calls=0`.
