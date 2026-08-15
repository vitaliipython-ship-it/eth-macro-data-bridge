# eth-macro-data-bridge

Public, no-auth market data for ETH Macro Watch and reproducible event studies.

## Entrypoints

- **LIVE CANONICAL ENTRYPOINT:** `data/manifest.json`
- **ARCHIVE CANONICAL ENTRYPOINT:** `archive/manifest.json`
- **EVENT REGISTRY ENTRYPOINT:** `events/manifest.json`
- **DERIVATIVES ENTRYPOINT:** `derivatives/manifest.json`
- **OPTIONS ENTRYPOINT:** `options/manifest.json`
- **LIQUIDITY ENTRYPOINT:** `liquidity/manifest.json`
- **DERIVED ANALYTICS ENTRYPOINT:** `analytics/manifest.json`

## Data layers

Authority hierarchy is **SPOT → DERIVATIVES → OPTIONS → LIQUIDITY → DERIVED ANALYTICS**. Provider files preserve raw/native facts; `analytics/` contains deterministic interpretation. Raw is never replaced by derived output, and providers are never silently averaged.

### HOT / ROLLING

The backward-compatible v2 layer remains at `data/{provider}/{symbol}/{interval}.json`. It contains compact rolling 5m, 15m, 1h, 4h and 1d datasets. A rolling latest candle no older than 10 minutes is useful as live context; older data is **STALE FOR LIVE**. Current candles have `closed=false`.

### APPEND-ONLY ARCHIVE

The v3.1 historical authority stores only CLOSED 5m candles, partitioned by UTC date:

```text
archive/YYYY/MM/DD/{provider}/{symbol}-5m.json
```

Existing `(provider, symbol, interval, open_time_ms)` records are never silently changed. A conflicting exchange response records reconciliation evidence and fails validation. Historical evidence does not become stale. Higher timeframes are deterministically aggregated from canonical M5 using UTC-aligned buckets.

Binance preserves `base_volume`, `close_time_ms`, `quote_volume`, `trade_count`, `taker_buy_base_volume`, and `taker_buy_quote_volume` in addition to OHLC. Base volume is the traded base asset (ETH for ETHUSDT); quote volume is quote-asset turnover (USDT for ETHUSDT). Trade count counts trades in the kline. Taker-buy fields measure aggressive-buy volume in base and quote units. They do **not** represent unique traders, order count, liquidations, or futures CVD.

Kraken preserves OHLC, VWAP, volume and trade count. Its documented final current/uncommitted OHLC row is never archived.

Sell volumes, taker-buy ratios, average trade size, returns, relative activity and event comparisons are deterministic derived analytics, not canonical market fields. Higher-timeframe Binance activity fields are summed before ratios are calculated. Kraken higher-timeframe VWAP is volume-weighted, never a simple average.

`ARCHIVE_BACKFILL_DAYS` controls bounded Binance backfill from 1 through 30 days and defaults to 7. Kraken uses its safe public OHLC window.

### EVENT SNAPSHOTS

`event_window.py` registers an explicit machine-readable event definition and resolves PRE/release/post checkpoints only from archived candles. It never discovers or invents events and never interpolates missing data. The immutable market payload receives a separate SHA-256 hash.

```bash
python event_window.py path/to/event-definition.json
```

Event definitions require `event_id` and `event_time_utc`; metadata such as name, timezone, priority, source and status remains producer-owned.

## Operation

The workflow runs hourly at `:35` and supports `workflow_dispatch`. One run refreshes rolling data, appends archive records, validates repeated-run invariants, and creates one data commit.

Collection cadence and historical resolution are distinct: collection is hourly while each run retrieves all new CLOSED M5 candles. Rolling data no older than 10 minutes is `LIVE_USABLE`; older rolling data is `STALE_FOR_LIVE`, while archived CLOSED candles remain `VALID_HISTORICAL`.

```bash
python collector.py
python validate.py
python qualify.py
```

Binance is the required primary source. Kraken is corroboration and may degrade independently. No exchange account, API key, credential, or trading permission is used.

## Future event-burst mode

The manual-only `Event market-data burst` workflow may temporarily collect bounded spot/perp books and leverage snapshots around an explicit event. Duration is capped at 90 minutes, interval at no less than 60 seconds, data stays in the runner until one final commit, and the baseline remains hourly.

## Market-intelligence domains

- `derivatives/`: Kraken Futures native 5m OI, flow, CVD, liquidation, positioning, volatility, basis, funding and liquidity analytics plus Deribit perpetual current state. Previously archived Binance USDⓈ-M data remains historical-only; its live collector is `DISABLED_BY_POLICY` and performs zero requests.
- `options/`: hourly Deribit ETH option surface, actual-Delta selected Greeks near 7/30/90-day targets, and historical ETH DVOL candles. Historical option surfaces are not fabricated.
- `liquidity/`: bounded hourly Binance spot/perp and Deribit ETH perpetual/selected-option books with spread, depth, imbalance and non-extrapolated slippage.
- `analytics/`: derived state and explicit provider labels. Binance kline taker flow is `BINANCE_SPOT_TAKER_FLOW_PROXY`, not exact CVD; Kraken Futures CVD is `KRAKEN_FUTURES_CVD_NATIVE`.

Hourly order-book snapshots are contextual and are not exact event liquidity unless timestamps match. 25D option metrics use actual provider delta; unavailable liquid candidates remain unavailable. Binance historical liquidations are explicitly unavailable because no reconstructable public REST history was confirmed.

Machine-readable endpoint contracts and official documentation links live in `provider-contracts.json`. All exchange routes are public/no-auth.

Health is provider-scoped. Binance Spot and its archive are mandatory; Kraken Futures and Deribit are the active derivatives authorities. Binance USDⓈ-M is `DISABLED_BY_POLICY`, excluded from network calls, errors, signals and health aggregation. Liquidity remains usable only when at least one provenance-labelled ETH source succeeds. Binance Spot depth prefers the official market-data-only `data-api.binance.vision` route and uses only documented Spot fallbacks. The stable consumer entrypoint is `bridge-contract.json`; extended history coverage is indexed by `history/manifest.json`.

Canonical Binance USD-M policy: `BINANCE_USDM_CURRENT_COLLECTION=DISABLED_BY_POLICY`, `BINANCE_USDM_EXISTING_ARCHIVE=FROZEN_HISTORICAL_REFERENCE`, `BINANCE_USDM_ARCHIVE_CONTINUOUSLY_ACCUMULATED=false`, `BINANCE_USDM_ARCHIVE_CURRENTLY_UPDATED=false`, and `BINANCE_USDM_SIGNAL_VOTE=EXCLUDED`.
