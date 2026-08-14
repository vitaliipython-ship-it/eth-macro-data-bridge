# eth-macro-data-bridge

Public, no-auth market data for ETH Macro Watch and reproducible event studies.

## Entrypoints

- **LIVE CANONICAL ENTRYPOINT:** `data/manifest.json`
- **ARCHIVE CANONICAL ENTRYPOINT:** `archive/manifest.json`
- **EVENT REGISTRY ENTRYPOINT:** `events/manifest.json`

## Data layers

### HOT / ROLLING

The backward-compatible v2 layer remains at `data/{provider}/{symbol}/{interval}.json`. It contains compact rolling 5m, 15m, 1h, 4h and 1d datasets. A rolling latest candle no older than 10 minutes is useful as live context; older data is **STALE FOR LIVE**. Current candles have `closed=false`.

### APPEND-ONLY ARCHIVE

The v3 historical authority stores only CLOSED 5m candles, partitioned by UTC date:

```text
archive/YYYY/MM/DD/{provider}/{symbol}-5m.json
```

Existing `(provider, symbol, interval, open_time_ms)` records are never silently changed. A conflicting exchange response records reconciliation evidence and fails validation. Historical evidence does not become stale. Higher timeframes are deterministically aggregated from canonical M5 using UTC-aligned buckets.

`ARCHIVE_BACKFILL_DAYS` controls bounded Binance backfill from 1 through 30 days and defaults to 7. Kraken uses its safe public OHLC window.

### EVENT SNAPSHOTS

`event_window.py` registers an explicit machine-readable event definition and resolves PRE/release/post checkpoints only from archived candles. It never discovers or invents events and never interpolates missing data. The immutable market payload receives a separate SHA-256 hash.

```bash
python event_window.py path/to/event-definition.json
```

Event definitions require `event_id` and `event_time_utc`; metadata such as name, timezone, priority, source and status remains producer-owned.

## Operation

The workflow runs hourly at `:35` and supports `workflow_dispatch`. One run refreshes rolling data, appends archive records, validates repeated-run invariants, and creates one data commit.

```bash
python collector.py
python validate.py
python qualify.py
```

Binance is the required primary source. Kraken is corroboration and may degrade independently. No exchange account, API key, credential, or trading permission is used.
