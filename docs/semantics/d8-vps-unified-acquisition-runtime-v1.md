# D8 VPS unified acquisition runtime v1

## Status and authority

`ETH-D8-VPS-UNIFIED-ACQUISITION-V1` adds one VPS-ready acquisition runtime to `eth-macro-data-bridge` as a **SOURCE_CANDIDATE_NOT_DEPLOYED**. It does not deploy anything and does not change market-data authority.

```text
D8_RUNTIME=SOURCE_CANDIDATE_NOT_DEPLOYED
D8_VPS_SHADOW=SOURCE_SUPPORTED_NOT_DEPLOYED
D8_VPS_ACTIVE=NOT_ALLOWED
D9_ACTIVE=NO
ACTIVE_DEFAULT_ROUTE=D6_RESOLUTION_PLAN_V1
VPS_IS_MARKET_DATA_AUTHORITY=false
PROVIDER_AUTHORITY_TRANSITION_ALLOWED=false
EXISTING_GITHUB_PRODUCTION_SCHEDULE_DISABLED=false
GITHUB_5M_SCHEDULER_CREATED=false
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
```

Machine authority for this candidate is `contracts/d8-runtime-candidate.json`. Existing `bridge-contract.json` active sections are intentionally unchanged.

## One provider/business-logic family

D8 does **not** introduce `vps_collector.py` or a second provider family. `src/acquisition_core.py` is a thin execution facade over the existing implementation:

```text
src/collector.py: binance(), kraken(), get()
src/intelligence.py: collect_binance(), collect_kraken(),
                     collect_deribit_perpetual(), collect_options(),
                     collect_liquidity(), depth_metrics()
                         ↓
                CanonicalAcquisitionCore
                         ↓
              D8 runtime storage adapter
```

The legacy GitHub collector keeps using the same functions and the same hourly workflow. D8 changes neither its cadence nor its Binance USD-M policy.

## Runtime service

Entrypoint:

```bash
python -m d8_service
```

Internal HTTP contract:

- `POST /v1/collect-cycle`
- `GET /v1/health`
- `GET /v1/readiness`
- internal port `8080`

The service is designed for a private Docker network. It has no public-DNS/Caddy requirement.

### Profiles

- `development`: non-authoritative; deterministic mock provider may be selected explicitly.
- `test`: non-authoritative; deterministic mock provider may be selected explicitly.
- `VPS_SHADOW`: non-authoritative; canonical providers only; internal bearer token required.
- `VPS_ACTIVE`: rejected by the D8 source candidate.

Authority mode is deployment configuration. It is never accepted in request JSON.

## Collect-cycle request

```json
{
  "schema_version": "eth-macro-d8-collect-cycle-request/1.0.0",
  "expected_schedule_at": "2026-08-17T20:00:00Z",
  "canonical_slot": "M5",
  "trace_id": "optional-orchestration-id"
}
```

Only those four fields are allowed. `provider`, `capability`, URL/route, symbol implementation, retry count, storage path and authority mode are rejected.

Policy:

- exact UTC M5 boundary;
- future clock skew: at most 120 seconds;
- stale retry window: 20 minutes;
- request body: at most 64 KiB;
- no raw provider payload is returned to the caller.

## Deterministic slot/idempotency

`cycle_id = sha256(runtime_contract_version | M5 | expected_schedule_at)` with a stable `d8c-` prefix.

For one slot:

- a completed `PASS` is replayed from the ledger without provider reacquisition;
- a concurrent live owner returns `LOCK_BUSY`;
- a non-pass/non-terminal cycle has at most three persisted attempts;
- successful per-capability acquisition is checkpointed to durable spool/ledger before later capabilities or HOT promotion;
- retry reuses the durable checkpoint instead of reacquiring a successful capability;
- restart recovers SQLite state; stale lease can be reclaimed after its bounded lease period.

The in-process mutex only protects temporary process CWD while legacy provider functions write into isolated staging. It is not authority; slot ownership is SQLite-backed.

## Repository-owned DUE policy

`d8-provider-due-policy/1.0.0`:

| Capability | Cadence | Shadow requirement |
|---|---:|---|
| Binance Spot M5 | 5m | required |
| Kraken Spot M5 | 5m | optional |
| Binance USD-M M5/current/higher-TF/depth | 5m | optional in shadow; source implemented |
| Deribit Perpetual current | 5m | optional |
| Liquidity current | 5m | optional |
| Kraken Futures analytics | 60m | optional |
| Deribit Options surface + ETH DVOL | 60m | optional |

The runtime returns `NOT_DUE` instead of pretending a skipped capability passed. n8n never selects providers or provider cadence.

Source request-count budget from current repository functions is bounded approximately as follows: normal M5 cycle `28` HTTP calls; top-of-hour cycle about `106` when Kraken analytics completes in one page per metric; Kraken analytics has a repository-bounded six-page pagination ceiling, making the top-of-hour structural upper bound about `236` calls. These are source estimates, not a live VPS guarantee; live shadow qualification must re-measure provider headers/rate behavior before any cutover.

## Binance USD-M boundary

The existing GitHub contour stays:

```text
BINANCE_USDM_GITHUB_RUNTIME=DISABLED_BY_POLICY
BINANCE_USDM_GITHUB_NETWORK_CALLS=0
BINANCE_USDM_ACTIVE_PROVIDER=false
```

D8 reuses the existing `collect_binance()` USD-M implementation and adds only the missing VPS-target observations through the same `get()`/normalization family: provider-native 1h/4h/1d klines and a bounded depth snapshot (`limit=100`). The existing collector already supplies 5m perp OHLCV, mark, index, basis/premium, open interest and funding data.

This makes VPS shadow connectivity testable later without activating Binance USD-M as authority.

## Persistent state decision

```text
STATE_BACKEND_DECISION=SQLITE_WAL_PERSISTENT_VOLUME
STATE_SCHEMA_VERSION=1
RUNTIME_STATE_ROOT=/var/lib/eth-macro-data-bridge   # container default
```

SQLite is the minimal backend that supplies atomic transactions, crash recovery, uniqueness, persistent lease state and explicit schema compatibility without introducing PostgreSQL/Redis/Kafka/RabbitMQ/MinIO. It is an implementation backend, not a second semantic market-data authority.

Logical areas:

- `HOT`: `sqlite.hot`
- `SPOOL`: `sqlite.spool`
- `LEDGER`: `sqlite.cycles` + `sqlite.capability_ledger`
- `LOCKS/LEASES`: `sqlite.leases`

SQLite uses WAL and `synchronous=FULL`. Startup fails closed if `state_schema_version` is incompatible.

## HOT

Transition:

```text
COLLECT → NORMALIZE → VALIDATE → DURABLE CHECKPOINT → QUALIFY → ATOMIC PROMOTE
```

Only an overall `PASS` can replace HOT. `DEGRADED` or `FAIL` preserves the previous qualified HOT. A reader cannot observe a partial cycle.

## Durable spool

Default hard cap: `134217728` bytes (128 MiB).

Policy:

- acquired observations are persisted before final promotion;
- identity key is deterministic `observation_id`;
- `PENDING` evidence is never silently expired before a future D9 forward ACK;
- after a future D9 forwarder explicitly ACKs an observation, it becomes `FORWARDED` and is eligible for purge after seven days;
- the hard byte cap includes pending and forwarded rows until purge;
- capacity exhaustion is explicit `SPOOL_FULL`; no silent drop;
- temporary provider staging is non-authoritative and swept on clean startup/retry.

This supplies a bounded, versioned high-cardinality seam candidate without relying on mutable GitHub Release assets.

## Ledger and lease

Per capability the ledger preserves cycle/slot/attempt, provider, source/provider timestamp, retrieved/known/collected timestamps, status/failure class, fingerprint, spool reference, promotion result, freshness/gap semantics and source/runtime revision.

Lease fields include owner, acquisition time and lease expiry. Terminal cycles release the lease. Expired leases are recoverable; a crash cannot block a slot indefinitely.

## Freshness and gaps

No synthetic fill is allowed. Missing data is an explicit collection gap/failure and never a previous value with a new timestamp. Runtime semantics distinguish `NOT_DUE`, provider failure, validation failure, collection gap and previous stale HOT. `known_at`/`retrieved_at` represent actual collection knowledge; provider timestamps are not retimestamped.

## D9 seam

D8 does not create a second D9 schema, resolver, reader or provider reacquisition path.

```text
qualified D8 observation
→ durable SQLite spool/ledger
→ D9 FIXED_GRID or SAMPLED_SCHEDULE representation
→ future declared WARM forwarder
→ existing D9 sealing path
```

The D8 envelope preserves provider/series identity, provider timestamp, `known_at`, finality, freshness, deterministic fingerprint and explicit collection-gap semantics. A future forwarder consumes durable observations; it must not call the provider again.

`D8_RUNTIME_TO_D9_WARM_SEAM=PASS_SOURCE_SEAM_NOT_DEPLOYED`. The production WARM forwarder and consumer cutover are not deployed or live-qualified by this task, therefore `D8_PRODUCTION_CUTOVER_SOURCE_READY=false` even though shadow deployment review may proceed.

High-cardinality decision:

```text
HIGH_CARDINALITY_D8_SEAM_DECISION=SUPPORTED_CANDIDATE
```

The candidate is versioned SQLite spool + ledger with deterministic observation identity/provenance, explicit forward ACK, seven-day post-ACK retention and hard byte backpressure. It is not active WARM authority.

Post-cutover conceptual consumer path, after a separate qualified cutover task:

```text
D8 qualified HOT/spool
→ D9 forward-history adapter
→ declared WARM
→ existing capability index / resolver
→ ResolutionPlan
→ existing history reader / consumer
```

## HTTP security

`VPS_SHADOW` requires `D8_RUNTIME_TOKEN` and uses `Authorization: Bearer ...`. Secrets have no repository defaults. The handler does not log authorization headers, cookies, request bodies or secret environment values. Arbitrary URL/shell/provider selection is absent.

## Health/readiness

`/v1/health` proves process/application state access.

`/v1/readiness` checks runtime configuration, state schema compatibility, ledger/spool/lease tables, persistent state read/write and HOT metadata access. A provider outage by itself does not make the process unready.

## Graceful shutdown

SIGTERM/SIGINT stops new cycle admission and shuts down the HTTP server while non-daemon request threads finish. Durable checkpoints and SQLite transactions make an interrupted/non-terminal cycle recoverable.

## Container

Build:

```bash
docker build -f tools/d8/Dockerfile -t eth-macro-d8:<source-sha> .
```

The image uses a non-root UID/GID 10001, one internal port 8080, one persistent volume at `/var/lib/eth-macro-data-bridge`, SIGTERM and a health probe. No canonical registry currently exists in this repository, so source completion does not publish an image.

## Future shadow qualification — separate server task

A server agent may, only after merged source/CI qualification, perform a bounded `VPS_SHADOW` review: persistent volume, private network, token auth, health/readiness, mock sanity, live Binance Spot/USD-M, Kraken, Deribit, natural M5 cycles, same-slot retry, restart, resources/rate budget and D9 observation comparison. It must not mutate authority.

## Future production cutover gates

Cutover remains forbidden until a separate owner-approved task proves at least live shadow/provider matrix, multiple natural M5 cycles, live USD-M, idempotency, restart, D9 runtime→WARM forward path, consumer continuity, resource/rate budgets, n8n/alerting and rollback. Only then may a versioned control-plane transition disable the legacy GitHub schedule and activate VPS acquisition. Permanent dual authority is forbidden.
