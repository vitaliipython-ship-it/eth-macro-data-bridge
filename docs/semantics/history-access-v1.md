# Historical Data Access v1 — as built

## Статус

```text
D6.1=QUALIFIED/PASS
D6.2A=QUALIFIED/PASS
D6.2B=QUALIFIED/PASS
D6.3=QUALIFIED/PASS
D6.4=QUALIFIED/PASS/ACTIVE
D6.5=QUALIFIED/PASS/MERGED
AGENT_RUNTIME_HISTORY_TRANSPORT=ACTIVE
```

Historical Data Access является production consumer dependency для Research/wave-analysis. Planning authority находится в `eth-macro-research`; implementation authority — в этом репозитории.

## Authority model

```text
bridge-contract.json
→ active capability discovery
→ semantic resolver
→ validated ResolutionPlan
→ canonical physical manifest/resource
→ immutable COLD Release / declared WARM Git bytes
→ plan-only reader
→ normalized rows + diagnostics
```

Hard invariants:

1. `ResolutionPlan` — единственный reader input authority.
2. Capability index — derived discovery, не byte authority.
3. Release asset locator/size/SHA только manifest-driven.
4. WARM/COLD merge deterministic; bytes SHA-pinned.
5. No synthetic gap fill / silent provider substitution.

## One-step consumer

`tools/history_consumer.py read` принимает `series_id + [from,to) + optional cutoff + mode + format`, вызывает существующий resolver и передаёт его `ResolutionPlan` существующему `history_access` reader. Новый resolver/storage authority не создаётся.

## Agent runtime transport

Есть два эквивалентных transport способа поверх одной authority:

```text
DIRECT_CANONICAL_READER
GITHUB_ISSUE_REQUEST
```

`workflow_dispatch` остаётся доступен человеку/CLI, но ChatGPT connector может не иметь dispatch primitive. Поэтому `bridge-contract.json.semantic_resolution.agent_transport` объявляет owner-only Issue transport как agent-callable invocation.

### Issue request

Title:

```text
[history-read] <description>
```

Body — только JSON:

```json
{
  "series_id": "spot.binance-spot.ETHUSDT.ohlcv.1h",
  "from_utc": "2025-04-09T00:00:00Z",
  "to_utc": "2025-08-25T00:00:00Z",
  "cutoff_utc": null,
  "mode": "strict",
  "output_format": "csv"
}
```

Request parser запрещает physical route inputs (`release_tag`, `asset_name`, `asset_id`, URL, resource path, SHA). После materialization workflow публикует Issue receipt и ephemeral artifact:

```text
candles.csv|json
resolution-plan.json
diagnostics.json
receipt.json
history-consumer.log
```

Artifact — transport output, не canonical market-data authority.

### Failure semantics

```text
RESOLUTION_FAILED       semantic series/range не разрешён
DATA_TRANSPORT_BLOCKED  canonical transport недоступен
READER_FAILED           integrity/schema/gap/duplicate failure
PASS                    strict verified materialization
DEGRADED                только explicit permissive mode с diagnostics
```

Direct provider fallback запрещён. Provider API может использоваться только как separate corroboration.

## Runtime qualification authority

Предыдущая network-backed qualification доказала physical COLD reads:

```text
RUNTIME_RUN=31964240112 SUCCESS
RUNTIME_JOB=95206826960 SUCCESS
wave-h4-leg              912/912   PASS gaps=0 duplicates=0
wave-h1-leg             3648/3648  PASS gaps=0 duplicates=0
pivot-m5                 576/576   PASS gaps=0 duplicates=0
cold-2022-m5           41760/41760 PASS gaps=0 duplicates=0
kraken-spot-h1              1/1    PASS
deribit-perpetual-h1        1/1    PASS
COLD_BINARY_TRANSPORT=PASS
HISTORY_MATERIALIZER=PASS
```

Agent-callable Issue transport должен дополнительно квалифицироваться реальным post-merge Issue request, после чего его run/artifact являются transport evidence, но не заменяют physical provenance внутри `ResolutionPlan`/receipt.

## Wave-agent usage

Для structural reconstruction:

```text
H4 broad structure
→ H1 refinement / ordering
→ narrow M5 only around ambiguous pivots
```

Consumer не должен знать year partitions, Release tags, asset filenames или WARM/COLD boundary. Он задаёт только semantic identity и time range.
