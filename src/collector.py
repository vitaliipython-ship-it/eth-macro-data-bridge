from __future__ import annotations
import json, shutil, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from archive import update_archive
from deribit_history import collect_deribit_history
from event_window import refresh_event_manifest
from intelligence import collect_intelligence
from kraken_revision import observe_kraken_revisions
from sampled_history import persist_sampled_intelligence
from spot_history import append_native_history, build_consistency_report, build_manifest as build_history_manifest, migrate_archive_m5

SCHEMA_VERSION, COLLECTOR_VERSION = "2.0.0", "0.4.0"
ROOT = Path("data")
RAW = "https://raw.githubusercontent.com/vitaliipython-ship-it/eth-macro-data-bridge/main/"
BINANCE_URLS = ("https://data-api.binance.vision", "https://api.binance.com")
SYMBOLS = {"binance": ("ETHUSDT", "BTCUSDT", "ETHBTC"), "kraken": ("ETHUSD", "BTCUSD")}
BINANCE_LIMITS = {"5m": 3000, "15m": 3000, "1h": 2000, "4h": 1000, "1d": 730}
KRAKEN_LIMITS = {"5m": 288, "15m": 96, "1h": 72, "4h": 42, "1d": 90}
LIMITS_BY_PROVIDER = {"binance": BINANCE_LIMITS, "kraken": KRAKEN_LIMITS}
MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
COLUMNS = ["open_time_ms", "open", "high", "low", "close", "volume", "closed"]


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get(url, retries=3):
    error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/json", "User-Agent":"eth-macro-data-bridge/0.4"})
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read())
        except Exception as exc:
            error = exc; time.sleep(attempt + 1)
    raise RuntimeError(f"fetch failed for {url}: {error}")


def binance(symbol, interval, limit, now, *, anchor_ms=None):
    errors = []
    for base in BINANCE_URLS:
        try:
            rows = []
            remaining = limit
            end_time = int(anchor_ms) - 1 if anchor_ms is not None else None
            while remaining > 0:
                params = {"symbol":symbol, "interval":interval, "limit":min(1000, remaining)}
                if end_time is not None:
                    params["endTime"] = end_time
                page = get(f"{base}/api/v3/klines?{urllib.parse.urlencode(params)}")
                if not isinstance(page, list) or not page:
                    raise ValueError("short response")
                rows = page + rows
                remaining -= len(page)
                if remaining <= 0:
                    break
                end_time = int(page[0][0]) - 1
            if len(rows) < limit:
                raise ValueError("short response")
            rows = rows[-limit:]
            if any(int(rows[i][0]) >= int(rows[i+1][0]) for i in range(len(rows)-1)):
                raise ValueError("non-monotonic response")
            compact = []
            native = []
            for row in rows:
                closed = now > int(row[6])
                compact.append([int(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[5]),closed])
                if closed:
                    native.append([int(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[5]),int(row[6]),str(row[7]),int(row[8]),str(row[9]),str(row[10])])
            return base, compact, native
        except Exception as exc:
            errors.append(f"{base}: {exc}")
    raise RuntimeError("; ".join(errors))


def kraken(symbol, interval, limit, now, *, anchor_ms=None):
    minutes = MINUTES[interval]
    params = {"pair":symbol, "interval":minutes}
    if anchor_ms is not None:
        params["since"] = max(0, (int(anchor_ms) - (limit + 2) * minutes * 60_000) // 1000)
    query = urllib.parse.urlencode(params)
    raw = get(f"https://api.kraken.com/0/public/OHLC?{query}")
    if not isinstance(raw, dict) or raw.get("error"): raise ValueError(f"Kraken error: {raw.get('error')}")
    keys = [k for k in raw["result"] if k != "last"]
    if len(keys) != 1: raise ValueError("unexpected Kraken result")
    all_rows = raw["result"][keys[0]]
    parsed = []
    for i, row in enumerate(all_rows):
        opened = int(row[0])*1000
        close_time = opened + minutes*60000 - 1
        closed = i < len(all_rows)-1 and now > close_time
        if anchor_ms is None or opened < int(anchor_ms):
            parsed.append((row, opened, close_time, closed))
    selected = parsed[-limit:]
    if len(selected) < limit: raise ValueError("short response")
    compact = []
    native = []
    for row, opened, close_time, closed in selected:
        compact.append([opened,str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[6]),closed])
        if closed:
            native.append([opened,str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[5]),str(row[6]),int(row[7]),close_time])
    return keys[0], compact, native


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
    temp = path.with_suffix(".json.tmp"); temp.write_bytes(encoded); temp.replace(path)
    return len(encoded)


def collect():
    now = int(time.time()*1000); generated = iso(now)
    refresh_event_manifest(generated)
    if ROOT.exists(): shutil.rmtree(ROOT)
    migration = migrate_archive_m5()
    providers = {
        "binance":{"role":"PRIMARY_CRYPTO_OHLC","status":"PASS","errors":[],"symbols":{}},
        "kraken":{"role":"CORROBORATION_SPOT_OHLC","status":"PASS","errors":[],"symbols":{}}}
    for provider, symbols in SYMBOLS.items():
        for symbol in symbols:
            providers[provider]["symbols"][symbol] = {"intervals":{}}
            for interval, limit in LIMITS_BY_PROVIDER[provider].items():
                try:
                    source, candles, native = (binance if provider == "binance" else kraken)(symbol, interval, limit, now)
                    rel = f"data/{provider}/{symbol}/{interval}.json"
                    payload = {"schema_version":SCHEMA_VERSION,"provider":provider,"symbol":symbol,"interval":interval,
                               "generated_at_utc":generated,"source":source,"columns":COLUMNS,"candles":candles}
                    size = write(Path(rel), payload); closed = [r for r in candles if r[6]]
                    warm = append_native_history(provider, symbol, interval, native,
                        availability_status="PASS" if provider == "binance" else "PROVIDER_HISTORY_LIMIT")
                    providers[provider]["symbols"][symbol]["intervals"][interval] = {
                        "path":rel,"raw_url":RAW+rel,"candle_count":len(candles),"closed_candle_count":len(closed),"size_bytes":size,
                        "latest_candle_open_time_ms":candles[-1][0],"latest_candle_open_time_utc":iso(candles[-1][0]),
                        "latest_closed_candle_open_time_ms":closed[-1][0] if closed else None,
                        "latest_closed_candle_open_time_utc":iso(closed[-1][0]) if closed else None,
                        "d9_warm_rows_observed":warm["compatibility_rows_observed"],
                        "d9_native_rows_observed":warm["provider_native_rows_observed"]}
                except Exception as exc: providers[provider]["errors"].append(f"{symbol} {interval}: {exc}")
            try:
                _, _, weekly_native = (binance if provider == "binance" else kraken)(symbol, "1w", 16, now)
                append_native_history(provider, symbol, "1w", weekly_native,
                    availability_status="PASS" if provider == "binance" else "PROVIDER_HISTORY_LIMIT")
            except Exception as exc:
                providers[provider]["errors"].append(f"{symbol} 1w history: {exc}")
    if providers["binance"]["errors"]: providers["binance"]["status"] = "FAIL"
    if providers["kraken"]["errors"]: providers["kraken"]["status"] = "DEGRADED"
    status = "FAIL" if providers["binance"]["status"] == "FAIL" else ("DEGRADED" if providers["kraken"]["status"] == "DEGRADED" else "PASS")
    build_history_manifest(now)
    consistency = build_consistency_report(now)
    manifest = {"schema_version":SCHEMA_VERSION,"collector_version":COLLECTOR_VERSION,"generated_at_utc":generated,
        "generated_at_epoch_ms":now,"bridge_status":status,
        "freshness":{"collection_interval_minutes":60,"expected_max_age_minutes":70,"historical_5m_retention_candles":BINANCE_LIMITS["5m"]},
        "policy":{"authentication":"NONE","api_keys_required":False,"timezone":"UTC","canonical_entrypoint":"data/manifest.json"},
        "providers":providers}
    write(ROOT/"manifest.json", manifest)
    if status == "FAIL": raise RuntimeError("Primary Binance incomplete: " + " | ".join(providers["binance"]["errors"]))
    manifest["_d9_internal"] = {"archive_migration":migration,"consistency":consistency["status_counts"]}
    return manifest


if __name__ == "__main__":
    m=collect()
    d9=m.pop("_d9_internal")
    archive=update_archive(m, get, BINANCE_URLS)
    intelligence_started=int(time.time()*1000)
    intelligence=collect_intelligence(get, m["generated_at_epoch_ms"])
    deribit_history=collect_deribit_history(get, m["generated_at_epoch_ms"])
    kraken_provider=intelligence.get("derivatives",{}).get("providers",{}).get("kraken-futures",{})
    kraken_revisions=(
        observe_kraken_revisions(get, m["generated_at_epoch_ms"])
        if kraken_provider.get("status")=="PASS"
        else {"status":"NOT_RUN_UPSTREAM_PROVIDER_NOT_PASS","observed_series":0,"new_revision_evidence":0,"evidence_paths":[]}
    )
    intelligence_completed=int(time.time()*1000)
    sampled=persist_sampled_intelligence(
        intelligence,
        expected_ms=m["generated_at_epoch_ms"],
        started_ms=intelligence_started,
        completed_ms=intelligence_completed,
        target_cadence_seconds=3600,
    )
    print(f"BRIDGE_STATUS={m['bridge_status']}")
    print(f"BINANCE_STATUS={m['providers']['binance']['status']}")
    print(f"KRAKEN_STATUS={m['providers']['kraken']['status']}")
    print(f"GENERATED_AT={m['generated_at_utc']}")
    print("CANONICAL_ENTRYPOINT=data/manifest.json")
    print(f"ARCHIVE_STATUS={archive['integrity_status']}")
    print(f"ARCHIVE_TOTAL_CANDLES={archive['total_closed_candles']}")
    print(f"D9_SPOT_WARM_MIGRATION={d9['archive_migration']['status']}")
    print(f"D9_SPOT_WARM_MIGRATED_ROWS={d9['archive_migration']['rows']}")
    print(f"D9_SPOT_CONSISTENCY={json.dumps(d9['consistency'],separators=(',',':'))}")
    print(f"D9_DERIBIT_WARM_STATUS={deribit_history['status']}")
    print(f"D9_DERIBIT_WARM_SERIES={deribit_history['series']}")
    print(f"D9_KRAKEN_REVISION_OBSERVER={kraken_revisions['status']}")
    print(f"D9_KRAKEN_NEW_REVISION_EVIDENCE={kraken_revisions['new_revision_evidence']}")
    print(f"D9_SAMPLED_LEDGER={sampled['ledger_path']}")
    print(f"D9_SAMPLED_RUN_COUNT={sampled['run_count']}")
