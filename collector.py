from __future__ import annotations
import json, shutil, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from archive import update_archive
from intelligence import collect_intelligence

SCHEMA_VERSION, COLLECTOR_VERSION = "2.0.0", "0.3.0"
ROOT = Path("data")
RAW = "https://raw.githubusercontent.com/vitaliipython-ship-it/eth-macro-data-bridge/main/"
BINANCE_URLS = ("https://data-api.binance.vision", "https://api.binance.com")
SYMBOLS = {"binance": ("ETHUSDT", "BTCUSDT", "ETHBTC"), "kraken": ("ETHUSD", "BTCUSD")}
LIMITS = {"5m": 288, "15m": 96, "1h": 72, "4h": 42, "1d": 90}
MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume", "closed"]

def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def get(url, retries=3):
    error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/json", "User-Agent":"eth-macro-data-bridge/0.2"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read())
        except Exception as exc:
            error = exc; time.sleep(attempt + 1)
    raise RuntimeError(f"fetch failed for {url}: {error}")

def binance(symbol, interval, limit, now):
    query = urllib.parse.urlencode({"symbol":symbol, "interval":interval, "limit":limit})
    errors = []
    for base in BINANCE_URLS:
        try:
            rows = get(f"{base}/api/v3/klines?{query}")
            if not isinstance(rows, list) or len(rows) < limit: raise ValueError("short response")
            return base, [[int(r[0]),str(r[1]),str(r[2]),str(r[3]),str(r[4]),str(r[5]),now > int(r[6])] for r in rows[-limit:]]
        except Exception as exc: errors.append(f"{base}: {exc}")
    raise RuntimeError("; ".join(errors))

def kraken(symbol, interval, limit, now):
    minutes = MINUTES[interval]
    query = urllib.parse.urlencode({"pair":symbol, "interval":minutes})
    raw = get(f"https://api.kraken.com/0/public/OHLC?{query}")
    if not isinstance(raw, dict) or raw.get("error"): raise ValueError(f"Kraken error: {raw.get('error')}")
    keys = [k for k in raw["result"] if k != "last"]
    if len(keys) != 1: raise ValueError("unexpected Kraken result")
    rows = raw["result"][keys[0]][-limit:]
    if len(rows) < limit: raise ValueError("short response")
    out = []
    for i, r in enumerate(rows):
        opened = int(r[0])*1000
        closed = i < len(rows)-1 and now > opened + minutes*60000-1
        out.append([opened,str(r[1]),str(r[2]),str(r[3]),str(r[4]),str(r[6]),closed])
    return keys[0], out

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
    temp = path.with_suffix(".json.tmp"); temp.write_bytes(encoded); temp.replace(path)
    return len(encoded)

def collect():
    now = int(time.time()*1000); generated = iso(now)
    if ROOT.exists(): shutil.rmtree(ROOT)
    providers = {
        "binance":{"role":"PRIMARY_CRYPTO_OHLC","status":"PASS","errors":[],"symbols":{}},
        "kraken":{"role":"CORROBORATION_SPOT_OHLC","status":"PASS","errors":[],"symbols":{}}}
    for provider, symbols in SYMBOLS.items():
        for symbol in symbols:
            providers[provider]["symbols"][symbol] = {"intervals":{}}
            for interval, limit in LIMITS.items():
                try:
                    source, candles = (binance if provider == "binance" else kraken)(symbol, interval, limit, now)
                    rel = f"data/{provider}/{symbol}/{interval}.json"
                    payload = {"schema_version":SCHEMA_VERSION,"provider":provider,"symbol":symbol,"interval":interval,
                               "generated_at_utc":generated,"source":source,"columns":COLUMNS,"candles":candles}
                    size = write(Path(rel), payload); closed = [r for r in candles if r[6]]
                    providers[provider]["symbols"][symbol]["intervals"][interval] = {
                        "path":rel,"raw_url":RAW+rel,"candle_count":len(candles),"closed_candle_count":len(closed),"size_bytes":size,
                        "latest_candle_open_time_ms":candles[-1][0],"latest_candle_open_time_utc":iso(candles[-1][0]),
                        "latest_closed_candle_open_time_ms":closed[-1][0] if closed else None,
                        "latest_closed_candle_open_time_utc":iso(closed[-1][0]) if closed else None}
                except Exception as exc: providers[provider]["errors"].append(f"{symbol} {interval}: {exc}")
    if providers["binance"]["errors"]: providers["binance"]["status"] = "FAIL"
    if providers["kraken"]["errors"]: providers["kraken"]["status"] = "DEGRADED"
    status = "FAIL" if providers["binance"]["status"] == "FAIL" else ("DEGRADED" if providers["kraken"]["status"] == "DEGRADED" else "PASS")
    manifest = {"schema_version":SCHEMA_VERSION,"collector_version":COLLECTOR_VERSION,"generated_at_utc":generated,
        "generated_at_epoch_ms":now,"bridge_status":status,
        "freshness":{"collection_interval_minutes":60,"expected_max_age_minutes":70,"historical_5m_retention_candles":288},
        "policy":{"authentication":"NONE","api_keys_required":False,"timezone":"UTC","canonical_entrypoint":"data/manifest.json"},
        "providers":providers}
    write(ROOT/"manifest.json", manifest)
    if status == "FAIL": raise RuntimeError("Primary Binance incomplete: " + " | ".join(providers["binance"]["errors"]))
    return manifest

if __name__ == "__main__":
    m=collect()
    archive=update_archive(m, get, BINANCE_URLS)
    collect_intelligence(get, m["generated_at_epoch_ms"])
    print(f"BRIDGE_STATUS={m['bridge_status']}")
    print(f"BINANCE_STATUS={m['providers']['binance']['status']}")
    print(f"KRAKEN_STATUS={m['providers']['kraken']['status']}")
    print(f"GENERATED_AT={m['generated_at_utc']}")
    print("CANONICAL_ENTRYPOINT=data/manifest.json")
    print(f"ARCHIVE_STATUS={archive['integrity_status']}")
    print(f"ARCHIVE_TOTAL_CANDLES={archive['total_closed_candles']}")
