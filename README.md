# eth-macro-data-bridge

Read-only public market-data bridge for ETH Macro Watch.

## Purpose

GitHub Actions fetches public, no-auth OHLC data from:

- Binance: `ETHUSDT`, `BTCUSDT`, `ETHBTC`
- Kraken corroboration: `ETHUSD`, `BTCUSD`

The generated file is:

`data/market.json`

It contains recent `5m`, `15m`, `1h`, `4h`, and `1d` OHLC data so the
Macro Watch can reconstruct event windows such as PRE / release / +15m / +30m.

## Security

No exchange API keys, accounts, or trading permissions are used.

## Schedule

The collector runs hourly at minute `:35` UTC-clock cadence via GitHub Actions.
This is intentional: the Macro Watch runs at `:40`, while exchange OHLC
endpoints return historical candles, so a single hourly refresh is sufficient
to reconstruct the preceding hour without creating a commit every five minutes.

A manual `workflow_dispatch` trigger is also enabled for testing.

## Data authority

- Binance = primary crypto OHLC source.
- Kraken = corroboration source.
- `generated_at_utc` and candle timestamps must be checked for freshness.
- A current/open candle is explicitly marked with `"closed": false`.
