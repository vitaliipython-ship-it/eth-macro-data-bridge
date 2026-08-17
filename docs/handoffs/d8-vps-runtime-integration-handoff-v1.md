# D8 VPS runtime integration handoff v1

## Exact source binding

```text
TASK_ID=ETH-D8-VPS-UNIFIED-ACQUISITION-V1
RUNTIME_SOURCE_COMMIT=0284e485369ecda9281b8d505a3a0968b4baa701
RUNTIME_SOURCE_TREE=8f862cf3668747c25ec296a35453de3bceea2327
RUNTIME_CONTRACT_VERSION=eth-macro-d8-runtime/1.0.0
STATE_SCHEMA_VERSION=1
STATUS=SOURCE_CANDIDATE_NOT_DEPLOYED
```

The values above bind the server handoff to the exact D8 source/container commit that passed both the D8 qualification workflow and the existing repository validation workflow. This handoff authorizes only `ai-revenue-lab` integration/shadow-deployment review, never production cutover.

## Build and start

Build deterministically from the exact source checkout:

```bash
docker build -f tools/d8/Dockerfile -t eth-macro-d8:${RUNTIME_SOURCE_COMMIT} .
```

Private-network shadow start template:

```bash
docker run -d \
  --name eth-macro-d8-shadow \
  --network <private-docker-network> \
  --mount type=volume,src=<persistent-volume>,dst=/var/lib/eth-macro-data-bridge \
  -e D8_RUNTIME_PROFILE=VPS_SHADOW \
  -e D8_PROVIDER_MODE=canonical \
  -e D8_SOURCE_REVISION=${RUNTIME_SOURCE_COMMIT} \
  -e D8_RUNTIME_TOKEN \
  eth-macro-d8:${RUNTIME_SOURCE_COMMIT}
```

Do not add public ingress. n8n should reach the container through the private Docker network.

## Service contract

```text
INTERNAL_PORT=8080
HEALTH=GET /v1/health
READINESS=GET /v1/readiness
COLLECT=POST /v1/collect-cycle
AUTH=Bearer token in VPS_SHADOW
PERSISTENT_MOUNT=/var/lib/eth-macro-data-bridge
```

Required environment:

- `D8_RUNTIME_PROFILE=VPS_SHADOW`
- `D8_PROVIDER_MODE=canonical`
- `D8_RUNTIME_TOKEN=<secret>`
- `D8_SOURCE_REVISION=<exact merged runtime source SHA>`

Optional bounded configuration:

- `RUNTIME_STATE_ROOT` (container default `/var/lib/eth-macro-data-bridge`)
- `D8_RUNTIME_REVISION`
- `D8_SPOOL_MAX_BYTES` (default 134217728)
- `D8_SPOOL_RETENTION_SECONDS` (default 604800 after forward ACK)
- `D8_LEASE_SECONDS` (default 240; accepted 30..600)
- `D8_OWNER_ID`
- `D8_INTERNAL_PORT` (default 8080)

Secret variables: only `D8_RUNTIME_TOKEN` is required by this source candidate. Never place it in image, repository, command history artifact, log or n8n workflow export.

## n8n contract

Mental model:

```text
Cron / schedule
→ compute expected UTC M5 boundary
→ POST /v1/collect-cycle
→ inspect compact terminal status
→ retry the SAME slot only
→ alert on FAIL or sustained DEGRADED
```

Example:

```http
POST /v1/collect-cycle
Authorization: Bearer <secret>
Content-Type: application/json

{
  "schema_version":"eth-macro-d8-collect-cycle-request/1.0.0",
  "expected_schedule_at":"2026-08-17T20:00:00Z",
  "canonical_slot":"M5",
  "trace_id":"n8n-execution-id"
}
```

Compact response shape:

```json
{
  "schema_version":"eth-macro-d8-collect-cycle-response/1.0.0",
  "cycle_id":"d8c-...",
  "canonical_slot":"M5",
  "expected_schedule_at":"2026-08-17T20:00:00.000Z",
  "started_at":"...",
  "completed_at":"...",
  "runtime_revision":"eth-macro-d8-runtime/1.0.0",
  "source_revision":"<source-sha>",
  "overall_status":"PASS",
  "provider_statuses":{},
  "capability_statuses":{},
  "freshness_summary":{},
  "collection_gap_summary":{"gap_count":0,"synthetic_fill":false},
  "spool_status":"DURABLE",
  "ledger_status":"TERMINAL",
  "errors":[]
}
```

n8n must not call providers, choose provider cadence/routes, normalize payloads, manage HOT/WARM, write market facts, perform fallback or pass `mode=active`.

### Timeout/retry

Use an HTTP timeout no greater than the configured lease horizon; recommended initial integration timeout is 210 seconds with the default 240-second lease. If transport fails, retry **the same expected M5 slot**, never fabricate a newer slot for the missed cycle. A terminal PASS replays without reacquisition; a live owner returns HTTP 409 / `LOCK_BUSY`. Runtime allows at most three persisted attempts for a non-pass slot and rejects retries after the 20-minute stale window.

## Due/provider matrix

- Binance Spot M5: every 5m, required.
- Kraken Spot M5: every 5m, optional.
- Binance USD-M: every 5m in `VPS_SHADOW`; 5m perp OHLCV, native 1h/4h/1d, mark/index/basis, OI, funding, depth snapshot. Source implemented, not active provider.
- Deribit perpetual: every 5m, optional.
- liquidity current: every 5m, optional.
- Kraken Futures analytics: hourly, optional.
- Deribit Options + ETH DVOL: hourly, optional, one shared acquisition.

GitHub Binance USD-M remains `DISABLED_BY_POLICY` and GitHub network calls remain zero.

## State/recovery

Backend is SQLite/WAL on the persistent volume. Four logical areas are HOT, SPOOL, LEDGER and LEASES. `STATE_SCHEMA_VERSION=1`; incompatible/corrupt state makes readiness fail closed.

A capability result is durably checkpointed before final promotion. On retry, a successful checkpoint is reused without provider reacquisition. HOT promotion occurs only for overall PASS and is a single SQLite transaction; DEGRADED/FAIL retains old HOT. Pending spool evidence is retained until future D9 forward ACK; forwarded evidence is purge-eligible after seven days. Hard cap is 128 MiB and `SPOOL_FULL` fails explicitly.

## D9/history and consumer continuity

```text
D8 observation
→ durable spool/ledger
→ D9 FIXED_GRID/SAMPLED_SCHEDULE forward representation
→ future WARM adapter
→ existing D9 sealing
```

No provider reacquisition, second resolver or second data authority is allowed. Observation identity/fingerprint, provider time, known_at, finality, freshness and collection-gap semantics are preserved.

```text
D8_RUNTIME_TO_D9_WARM_SEAM=PASS_SOURCE_SEAM_NOT_DEPLOYED
D8_PRODUCTION_CUTOVER_SOURCE_READY=false
```

The source seam exists, but a production WARM forwarder/live consumer continuity has not been deployed/qualified. Therefore the server agent must not disable the GitHub schedule merely because the HTTP service is healthy.

Post-cutover consumer path after a future separately qualified transition:

```text
D8 qualified HOT/spool
→ D9 forward-history adapter
→ declared WARM
→ existing capability index/resolver
→ ResolutionPlan
→ existing history reader/consumer
```

High-cardinality decision is `SUPPORTED_CANDIDATE`: versioned SQLite spool, deterministic IDs/provenance, explicit forward ACK, post-ACK retention, hard-cap backpressure. It is not active WARM authority.

## Source qualification sizing evidence

Local deterministic source test on the development executor (Python 3.13 host, mock provider) measured approximately:

```text
SINGLE_MOCK_CYCLE_SECONDS≈0.05
IDLE_RSS≈110 MiB
POST_CYCLE_RSS≈111 MiB
SQLITE_INCREMENT≈11.6 KiB/cycle in deterministic compact fixture
SQLITE_FIXED_GRID_ESTIMATE≈3.35 MiB/day for 288 fixture cycles
```

Container CI on the exact bound source measured approximately 18.55 MiB RSS after the first mock cycle and 18.01 MiB after restart/replay. These are source-test measurements, not VPS guarantees. Future VPS shadow must re-measure memory/runtime/state using live provider payloads. Structural network-call estimate is `28` on a normal M5 slot and about `106` on a typical top-of-hour slot; repository-bounded Kraken pagination yields a conservative top-of-hour ceiling around `236` calls. Live provider rate-budget proof remains a required shadow gate.

## Binance USD-M live shadow instructions — future server task only

1. Keep `VPS_SHADOW`; never enable active mode.
2. Confirm GitHub collector still reports USD-M `DISABLED_BY_POLICY` / zero calls.
3. Invoke a natural M5 slot through `/v1/collect-cycle`.
4. Verify USD-M capability evidence includes M5, higher TF, current mark/index/basis/OI/funding and depth.
5. Compare overlapping spot/derivatives semantics against current GitHub data without changing authority.
6. Restart the container with the same volume and replay the same slot; verify no duplicate/reacquire after PASS.
7. Record runtime, RSS, state growth, request counts, errors and provider response/rate headers.

## Rollback expectation

Before production cutover, rollback of shadow is simply: stop/remove the shadow container while preserving or archiving its isolated volume as evidence. The current GitHub acquisition and D6 consumer route continue unchanged, so no authority restoration is needed.

A future production cutover requires a separate rollback plan that can re-enable the legacy schedule only under the cutover task's explicit authority controls.

## Explicit boundaries

```text
SHADOW_DEPLOYMENT_ALLOWED=true   # only after source/CI merge qualification
PRODUCTION_CUTOVER_ALLOWED=false
PROVIDER_AUTHORITY_TRANSITION_ALLOWED=false
VPS_MUTATION_BY_D8_TASK=false
N8N_MUTATION_BY_D8_TASK=false
AI_REVENUE_LAB_MUTATION_BY_D8_TASK=false
D9_ACTIVATION=false
D6_ROUTE_CHANGED=false
GITHUB_SCHEDULE_CHANGED=false
BINANCE_USDM_POLICY_ACTIVATED=false
```
