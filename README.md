# eth-macro-data-bridge

Read-only public market-data bridge for ETH Macro Watch.

## Canonical entrypoint

**CANONICAL ENTRYPOINT = `data/manifest.json`**

Read the small manifest first, then fetch only the required compact interval file from its `raw_url`. The superseded monolithic `data/market.json` is intentionally absent; v2 has one unambiguous authority. Stable paths use `data/{provider}/{symbol}/{interval}.json`.

Rows follow the declared compact layout: `open_time_ms, open, high, low, close, volume, closed`.

## Sources and semantics

- Binance (`ETHUSDT`, `BTCUSDT`, `ETHBTC`) is the required primary source.
- Kraken (`ETHUSD`, `BTCUSD`) is optional corroboration; an outage degrades but does not fail the bridge.
- No account, API key, credential, or trading permission is used.
- `closed=false` means current/in-progress. Kraken's final uncommitted row is always current.
- Each hourly refresh retains 288 five-minute candles for event-window reconstruction.

## Operation

The workflow runs hourly at `:35` and supports `workflow_dispatch`.

```bash
python collector.py
python validate.py
```

Validation covers required counts, increasing timestamps, OHLC invariants, closed semantics, manifest consistency, and file-size ceilings.
