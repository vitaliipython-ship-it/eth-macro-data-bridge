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

Common request validity is evaluated before deciding whether the request is a new admission or recovery of an exact durable cycle. Common validity still requires an exact UTC M5 boundary, the supported schema/fields, valid `trace_id`, and the unchanged future-skew policy.

Policy:

- exact UTC M5 boundary;
- future clock skew: at most 120 seconds, inclusive (`expected_ms - now_ms <= 120000`);
- `STALE_SLOT_SECONDS=1200` is the **NEW CYCLE admission bound only**;
- a missing/new cycle is admissible only while `now_ms - expected_ms <= 1200000`; at `+1 ms` it is `REQUEST_INVALID`;
- an exact already-durable nonterminal cycle is evaluated by the separate bounded recovery policy below and is not converted to `REQUEST_INVALID` merely because its legally acquired lease crossed the new-admission deadline;
- request body: at most 64 KiB;
- no raw provider payload is returned to the caller.

No recovery exception can create an arbitrary missing historical cycle. `FUTURE_SKEW_SECONDS` is not weakened by existing-cycle recovery.

## Deterministic slot/idempotency

`cycle_id = sha256(runtime_contract_version | M5 | expected_schedule_at)` with a stable `d8c-` prefix.

For one slot:

- a completed `PASS` keeps the existing replay semantics within the ordinary request admission window;
- a concurrent genuinely live owner returns `LOCK_BUSY`, including when the slot has aged beyond the new-admission boundary;
- a non-pass/non-terminal cycle has at most three persisted attempts;
- successful per-capability acquisition atomically writes global spool identity, an independent cycle-local checkpoint, and the bound ledger row before later capabilities or HOT promotion;
- retry reuses a checkpoint only when expected count, ordered membership hash, exact cycle-local payload integrity, and bound successful ledger evidence all pass; invalid/incomplete checkpoints are rejected as a whole and safely reacquired;
- restart recovers SQLite state without erasing expired ownership timing evidence needed by bounded recovery.

The in-process mutex only protects temporary process CWD while legacy provider functions write into isolated staging. It is not authority; slot ownership is SQLite-backed.

### New admission versus existing exact-cycle recovery

`STALE_SLOT_SECONDS` and existing-cycle recovery are deliberately different policies.

**NEW_ADMISSION**

```text
common request validation
→ normalize exact M5 slot
→ derive deterministic cycle_id
→ no exact durable cycle exists
→ if slot_age_ms <= 1_200_000: admission may proceed
→ if slot_age_ms > 1_200_000: REQUEST_INVALID
```

**EXISTING_EXACT_CYCLE_RECOVERY**

A stale request may enter recovery only when durable state proves all of:

```text
request.normalized_slot == cycles.slot
cycles.expected_at == request.normalized_slot
cycle_id_for(cycles.expected_at) == cycles.cycle_id
requested_cycle_id == cycles.cycle_id
canonical_slot == M5
state_schema_version == 2
runtime contract is compatible
cycles.status ∈ {STARTED,COLLECTED,QUALIFIED,RECOVERABLE}
```

Historical `source_revision` is provenance and is **not** required to equal the successor source SHA. Recovery does not rewrite the original cycle/checkpoint source provenance and does not run the successor under a falsified old `D8_SOURCE_REVISION`.

A live lease is authoritative first:

```text
lease_until >= now_ms  => LOCK_BUSY
lease_until <  now_ms  => lease is expired/recoverable evidence
```

The existing-cycle recovery anchor is the latest durable activity timestamp expressible by schema v2:

```text
RECOVERY_ANCHOR = max(
  cycles.started_at,
  cycles.completed_at when present,
  leases.acquired_at,
  leases.lease_until,
  cycle_checkpoints.created_at,
  capability_ledger.collected_at
)
```

The bounded recovery rule is:

```text
EXISTING_CYCLE_RECOVERY_SECONDS = 86400  # 24 hours
now_ms <= RECOVERY_ANCHOR + 86_400_000  => recovery eligible
now_ms >  RECOVERY_ANCHOR + 86_400_000  => REQUEST_INVALID / recovery expired
```

The deadline is inclusive. The anchor is lifecycle/ownership/checkpoint activity rather than original slot age. A legitimate heartbeat therefore can extend `lease_until` beyond `slot + STALE_SLOT_SECONDS` without destroying later crash recovery. Conversely, an abandoned ancient nonterminal cycle cannot be resurrected indefinitely. `MAX_ATTEMPTS=3` remains an independent, authoritative second bound.

Startup marks nonterminal cycles with no live lease `RECOVERABLE` but retains expired lease rows as durable timing evidence. No schema change is required: schema v2 already carries cycle timestamps, lease acquisition/expiry, checkpoint creation time, and ledger collection time.

Ownership transitions and attempt progression are decided inside the same SQLite `BEGIN IMMEDIATE` transaction. Two simultaneous retries after expiry cannot both increment the attempt or become owner. After takeover, heartbeat renewal, checkpoint writes, terminalization and explicit recoverable release require the current `owner_id` and current attempt. An old worker cannot renew, checkpoint, terminalize, or release a successor owner's cycle.

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
STATE_SCHEMA_VERSION=2
RUNTIME_STATE_ROOT=/var/lib/eth-macro-data-bridge   # container default
```

SQLite is the minimal backend that supplies atomic transactions, crash recovery, uniqueness, persistent lease state and explicit schema compatibility without introducing PostgreSQL/Redis/Kafka/RabbitMQ/MinIO. It is an implementation backend, not a second semantic market-data authority.

Logical areas:

- `HOT`: `sqlite.hot`
- `SPOOL`: `sqlite.spool`
- `LEDGER`: `sqlite.cycles` + `sqlite.capability_ledger`
- `LOCKS/LEASES`: `sqlite.leases`
- `CYCLE_CHECKPOINTS`: `sqlite.cycle_checkpoints` + `sqlite.cycle_checkpoint_observations`

SQLite uses WAL and `synchronous=FULL`. Schema v1 is migrated additively and idempotently to v2 without volume reset; any other incompatible version fails closed. The stale-window recovery repair does not introduce schema v3.

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

Lease fields include owner, acquisition time and lease expiry. `lease_until >= now` is live; equality is live. `lease_until < now` is expired. Terminal cycles release the lease. Explicit recoverable release converts the current owner's lease to expired timing evidence rather than deleting the last activity timestamp. Startup likewise does not erase expired lease evidence before bounded recovery is decided.

Heartbeat renewal is owner-bound and can renew only a still-live lease. A worker that wakes after its lease expired cannot resurrect ownership. Checkpoint persistence, terminalization and recoverable release are also current-owner/current-attempt operations, closing the stale-worker takeover race.

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

`/v1/readiness` checks runtime configuration, state schema compatibility, ledger/spool/lease tables, persistent state read/write and HOT metadata access. `active_leases` counts only `lease_until >= now`; retained expired recovery evidence is not reported as an active owner. A provider outage by itself does not make the process unready.

## Graceful shutdown

SIGTERM/SIGINT stops new cycle admission and shuts down the HTTP server while non-daemon request threads finish. Durable checkpoints and SQLite transactions make an interrupted/non-terminal cycle recoverable under the bounded existing-cycle policy.

## Container

Build:

```bash
docker build -f tools/d8/Dockerfile -t eth-macro-d8:<source-sha> .
```

The image uses a non-root UID/GID 10001, one internal port 8080, one persistent volume at `/var/lib/eth-macro-data-bridge`, SIGTERM and a health probe. No canonical registry currently exists in this repository, so source completion does not publish an image.

## Future shadow qualification — separate server task

A server agent may, only after merged source/CI qualification, perform a bounded `VPS_SHADOW` review: persistent volume, private network, token auth, health/readiness, mock sanity, live Binance Spot/USD-M, Kraken, Deribit, natural M5 cycles, same-slot retry, restart, resources/rate budget and D9 observation comparison. It must not mutate authority.

The stale-window recovery successor necessarily changes runtime admission/recovery bytes, so source CI is not a substitute for physical server proof. The preserved physical Cycle B must remain in place for the later server-side retest; the successor must use its real new source revision while preserving the historical source revision already stored in that cycle/checkpoint.

## Future production cutover gates

Cutover remains forbidden until a separate owner-approved task proves at least live shadow/provider matrix, multiple natural M5 cycles, live USD-M, idempotency, restart, D9 runtime→WARM forward path, consumer continuity, resource/rate budgets, n8n/alerting and rollback. Only then may a versioned control-plane transition disable the legacy GitHub schedule and activate VPS acquisition. Permanent dual authority is forbidden.


## Durable checkpoint v2: global dedup is not cycle membership

`STATE_SCHEMA_VERSION=2` repairs `D8_CROSS_CYCLE_DEDUP_CHECKPOINT_REPLAY_INCOMPLETE` while leaving `observation_id` unchanged. Three identities are deliberately separate:

1. market observation identity: `sha256(provider|series_id|provider_timestamp_at|payload_fingerprint)`;
2. global forwarding/dedup identity: one `sqlite.spool` row per `observation_id`;
3. cycle-local recovery evidence: `cycle_id + capability_id` checkpoint with ordered members and exact cycle-local normalized payloads.

A finalized observation can therefore be globally identical across Cycle A and Cycle B while both cycles retain checkpoint membership. The global spool keeps the first-seen envelope for the one forwarding identity; recovery does **not** read that envelope as later-cycle provenance. `cycle_checkpoint_observations.payload_json` is the durable authority for the exact later-cycle `canonical_cycle_id`, `canonical_slot`, `retrieved_at`, `known_at`, and `collected_at` values.

A successful checkpoint transaction binds the successful capability ledger row to `checkpoint_attempt`, `expected_count`, SHA-256 of the ordered observation-id list, SHA-256 of the ordered cycle-local payload list, and SHA-256 of canonical ledger evidence. Reuse requires every binding to pass. Missing member, corrupt payload, expected-count mismatch, membership hash mismatch, or ledger mismatch rejects the entire checkpoint; partial recovered observations are never mixed with provider reacquisition.

Migration from schema v1 is additive and idempotent: existing cycles, terminal PASS responses, HOT, global spool rows and PENDING/FORWARDED state, capability ledger, and leases are preserved. Because a v1 nonterminal checkpoint cannot prove complete cross-cycle membership, it is not fabricated into v2; its explicit policy is `SAFE_REACQUIRE`.

`mark_forwarded(observation_ids)` remains global and unambiguous: it transitions only the one global spool row for each observation. D9 remains inactive and no WARM/COLD/consumer cutover is introduced by this repair.
