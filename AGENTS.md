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

`bridge-contract.json` — route/provider-policy/storage-portability machine authority. Capability index — derived discovery layer, не byte authority. `ResolutionPlan` — единственный input authority reader-а. Physical locator/size/SHA приходит только из canonical control plane после semantic resolution.

Агент задаёт `series_id`, range/observation identity, cutoff когда применимо, mode/policy и output format. Агент не задаёт Release tag, asset/path/URL/SHA locator, WARM/COLD/generation path, VPS filesystem path, database locator или provider URL.

## Storage portability boundary

Canonical contract identity:

```text
ETH-MARKET-DATA-STORAGE-PORTABILITY-V2
```

Implementation-facing semantics: `docs/semantics/market-data-storage-portability-v2.md`.

Hard invariant:

```text
MARKET_DATA_SEMANTIC_AUTHORITY=ETH_MACRO_DATA_BRIDGE
PHYSICAL_STORAGE_BACKEND_IS_SEMANTIC_AUTHORITY=false
EXECUTION_PLANE_IS_SEMANTIC_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false
```

`HOT/WARM/COLD` — logical residence roles. Current physical profile `GITHUB_FIRST_V1` не является eternal semantic ontology. Backend migration не должна менять `series_id`, `observation_id`, D8 envelope, resolver/reader public family или semantic receipt meaning.

D8 SQLite WAL — `OPERATIONAL_RUNTIME_STATE`, не D9 history authority.

Current post-reset VPS_SHADOW physical/status authority:

- machine status: `contracts/d8-shadow-post-reset-status-v1.json`;
- human semantics: `docs/semantics/d8-shadow-post-reset-authority-v1.md`.

Source/runtime behavior authority остаётся `contracts/d8-runtime-candidate.json`; historical exact-source handoff остаётся `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md` и не используется как current deployment-status SSOT.

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

1. `bridge-contract.json` — текущая machine route/provider/storage-portability authority.
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
13. `HOT/WARM/COLD` не означают Git/VPS/PostgreSQL/Release.
14. Local filesystem write/read-back сам по себе не даёт production D8→D9 ACK.
15. `one M5 observation → one git commit` запрещён.
16. Не создавать второй resolver/reader/catalog/API/market-data authority ради backend portability.

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
D9_TARGET_CONTRACT=ACCEPTED
D9_SOURCE_CONTOUR=PUBLICATION_PORT_IMPLEMENTED_AND_MERGED
D9_CANONICAL_PUBLICATION_SOURCE=QUALIFIED
D9_REAL_D8_RUNTIME_TO_CANONICAL_WARM=PHYSICAL_QUALIFICATION_PENDING
D9_PHYSICAL_CANONICAL_D8_PUBLICATION=NOT_QUALIFIED
D9_AUTHORITY=NOT_ACTIVE
D9_ACTIVE=NO
D9_ACTIVATION=PENDING

D8_AUTHORITY_ACTIVE=false
D8_VPS_SHADOW_RUNTIME=RUNNING_HEALTHY_NON_AUTHORITATIVE
CURRENT_D8_SOURCE=9336f75b4e6c49dcbc82252bc37a4bc45075f04f
CURRENT_D8_STATE_SCHEMA_VERSION=2
CURRENT_D8_SPOOL_TOTAL=0
CURRENT_D8_PENDING_TOTAL=0
CURRENT_D8_FORWARDED_TOTAL=0

ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
ACTIVE_RESOLUTION_PLAN=market-data-resolution-plan/1.0.0
D9_V2=SOURCE_CANDIDATE_NOT_ACTIVE
```

D9 v2 реализован как candidate в той же `tools/capability_index.py` / `tools/history_access.py` family, но default `--plan-version` остаётся v1. Не создавать второй resolver/catalog/reader и не считать v2 active без отдельной activation transition.

Storage-neutral v2 target разделяет `residence_role`, `adapter_profile`, opaque `resource_ref`, adapter-owned `physical_descriptor` и `integrity_evidence`. Technology-specific `storage` пока остаётся deprecated compatibility alias до pre-activation implementation migration; ResolutionPlan v3 ради этого не создаётся.

Полный operational status, agent examples, machine SSOT hierarchy, remaining physical gates и D9.5 provenance rules:

`docs/semantics/d9-operational-status-and-agent-usage-v1.md`.

Implementation-facing lifecycle background:

`docs/semantics/market-data-history-lifecycle-v1.md`.

Storage/publication reconciliation:

`docs/semantics/market-data-storage-portability-v2.md`.

## Почему D9 ещё не active

Source-level canonical Publication Port gap закрыт: merged PR #118 реализовал и квалифицировал путь `PublicationBatch → GITHUB_FIRST_V1 → remote durability/read-back → control-plane/resolver visibility → existing reader → CANONICAL_PUBLICATION_ACK`. Это repository/Actions source qualification, а не production VPS qualification.

Production D8 `PENDING→FORWARDED` по-прежнему требует `CANONICAL_PUBLICATION_ACK`:

```text
PublicationBatch
→ selected current canonical WARM backend
→ durability PASS
→ independent verification/read-back PASS
→ exact identity/integrity binding PASS
→ canonical control-plane/resolver visibility
→ ACK
```

Owner-authorized pre-production shadow preservation/reset/deployment transition завершён. Старые `261` PENDING (`62` checkpoint-v2 eligible + `199` legacy pre-checkpoint-v2) сохранены forensic-only; их restore не авторизован. Current clean VPS_SHADOW имеет schema v2 и `SPOOL/PENDING/FORWARDED=0/0/0`, normal provider acquisition после reset ещё не выполнялся.

Current program frontier:

```text
OLD_PRE_PRODUCTION_SHADOW
→ FORENSIC_PRESERVATION          COMPLETE
→ CONTROLLED_SHADOW_RESET        COMPLETE
→ CURRENT_D8_DEPLOYMENT          COMPLETE
→ CLEAN_VPS_SHADOW               COMPLETE
→ NEW_REAL_CHECKPOINT_V2_DATA    NEXT
→ PHYSICAL_PUBLICATION_PORT      PENDING
→ ACTIVATION                     NOT_AUTHORIZED
```

Следующий required stage больше **не** использует old pre-reset live SPOOL:

```text
NEXT_REQUIRED_STAGE=NEW_REAL_CHECKPOINT_V2_DATA
current D8 VPS_SHADOW
→ explicit real provider collection
→ new current-generation checkpoint-v2 evidence
→ non-zero eligible PENDING
→ STOP
→ separately owner-authorized canonical Publication Port physical qualification
```

`GITHUB_FIRST_V1` не требует `GITHUB_TOKEN` внутри D8 runtime. `VPS_SHADOW` продолжает использовать `D8_RUNTIME_TOKEN`; publication credentials принадлежат отдельно авторизованному publication executor/adapter. Public D8 ingress не требуется.

До отдельной Publication Port physical qualification и activation transition запрещено считать D8/D9 active или отключать legacy GitHub acquisition. Старые forensic PENDING не восстанавливать без отдельной owner authorization.

Regular-grid sealing по-прежнему использует `COMPLETED_MONTH_ONLY`; active-period sealing выключен. До D9 authority switch также нужны реальная eligible generation, deterministic sealing, immutable COLD publication/read-back, реальный legacy COLD → D9 COLD → WARM semantic read и отдельный activation PR.

Existing production sealer остаётся:

```text
.github/workflows/seal-history.yml
→ tools/deep_history/history_sealer.py detect
→ tools/deep_history/history_sealer.py publish
→ immutable candidate publication/read-back
```

Не писать второй sealer/publisher для COLD. Canonical D8→WARM Publication Port — отдельная bounded responsibility, не replacement sealer.

## D8 / high-cardinality boundary

```text
D8_AUTHORITY_ACTIVE=false
D8_VPS_SHADOW_RUNTIME=RUNNING_HEALTHY_NON_AUTHORITATIVE
D8_RUNTIME_STATE_BACKEND=SQLITE_WAL
D8_RUNTIME_STATE_ROLE=OPERATIONAL_RUNTIME_STATE
D8_RUNTIME_STATE_IS_HISTORY_AUTHORITY=false
VPS_IS_MARKET_DATA_AUTHORITY=false
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_VPS_TARGET=REQUIRED
BINANCE_USDM_VPS_RUNTIME=NOT_ACTIVE
BINANCE_USDM_ACTIVE_PROVIDER=false

HIGH_CARDINALITY_WARM_BACKEND=BLOCKED_VERSIONED_DECISION
HIGH_CARDINALITY_COLD=BLOCKED
```

Published GitHub prerelease оказался immutable; mutable-in-place Release assumption — `HISTORICAL_PLAN_DECISION_SUPERSEDED` и не используется как current backend decision.

PostgreSQL сейчас не разворачивается. Future migration path допустим только behind same semantic interface; наличие existing server PostgreSQL не означает reuse decision.

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

Не строить `StoragePluginManager`, generic persistence framework, Kafka/Redis/new warehouse или backend deployment без отдельного доказанного риска и versioned decision.

## D8 VPS unified acquisition runtime source candidate

- Canonical source contract: `contracts/d8-runtime-candidate.json`.
- Operational source semantics: `docs/semantics/d8-vps-unified-acquisition-runtime-v1.md`.
- Current physical/status contract: `contracts/d8-shadow-post-reset-status-v1.json`.
- Current post-reset semantics: `docs/semantics/d8-shadow-post-reset-authority-v1.md`.
- Storage/publication boundary: `docs/semantics/market-data-storage-portability-v2.md`.
- Historical server handoff: `docs/handoffs/d8-vps-runtime-integration-handoff-v1.md`.
- Entrypoint: `python -m d8_service`; container: `tools/d8/Dockerfile`.
- Source contract remains a source candidate and `VPS_ACTIVE` remains forbidden without a separate transition; its historical `NOT_DEPLOYED` labels do not override the separate current physical/status contract.
- Current VPS_SHADOW is running healthy and non-authoritative; this does not make D8 active.
- D8 does not change `D9_ACTIVE=NO`, `ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1`, the hourly GitHub production acquisition schedule, or Binance USD-M GitHub `DISABLED_BY_POLICY` / `network_calls=0`.
