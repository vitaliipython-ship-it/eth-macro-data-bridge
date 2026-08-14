from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from decimal import Decimal
from archive import ARCHIVE_VERSION, BINANCE_COLUMNS, KRAKEN_COLUMNS, atomic_json, binance_analytics, load_series, partition_path

EVENT_VERSION="1.0.0"
CHECKPOINTS={"PRE_30":-30,"PRE_15":-15,"PRE_10":-10,"PRE_5":-5,"RELEASE":0,
             "PLUS_5":5,"PLUS_10":10,"PLUS_15":15,"PLUS_30":30,"PLUS_60":60}
DEFAULT_SYMBOLS={"binance":("ETHUSDT","BTCUSDT","ETHBTC"),"kraken":("ETHUSD","BTCUSD")}

def parse_time(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()*1000)

def market_window(event_ms: int, requested=DEFAULT_SYMBOLS) -> list[dict[str, Any]]:
    window=[]
    for provider,symbols in requested.items():
        for symbol in symbols:
            rows={row[0]:row for row in load_series(provider,symbol)}
            for name,offset in CHECKPOINTS.items():
                target=event_ms+offset*60_000; row=rows.get(target)
                entry={"provider":provider,"symbol":symbol,"interval":"5m","requested_checkpoint":name,
                       "requested_open_time_ms":target,"data_status":"AVAILABLE" if row else "MISSING"}
                if row:
                    columns=BINANCE_COLUMNS if provider=="binance" else KRAKEN_COLUMNS
                    native=dict(zip(columns,row)); path=partition_path(provider,symbol,datetime.fromtimestamp(row[0]/1000,timezone.utc).strftime("%Y-%m-%d"))
                    entry.update({"actual_candle_open_time_ms":row[0],"ohlcv":row[1:6] if provider=="binance" else row[1:5]+[row[6]],
                                  "activity":{k:native.get(k) for k in ("base_volume","volume","quote_volume","trade_count","taker_buy_base_volume","taker_buy_quote_volume","vwap") if k in native},
                                  "flow_analytics":binance_analytics(row) if provider=="binance" else None,"closed":True,
                                  "source_open_time_ms":row[0],"source_schema_version":ARCHIVE_VERSION,
                                  "source_archive_path":path.as_posix(),"source_partition_sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
                window.append(entry)
            available=[x for x in window if x["provider"]==provider and x["symbol"]==symbol and x["data_status"]=="AVAILABLE"]
            pre=next((x for x in available if x["requested_checkpoint"]=="PRE_30"),None)
            if pre:
                pre_close=Decimal(pre["ohlcv"][3]); pre_volume=Decimal(pre["activity"].get("base_volume",pre["activity"].get("volume","0")))
                pre_trades=Decimal(pre["activity"]["trade_count"])
                for entry in available:
                    volume=Decimal(entry["activity"].get("base_volume",entry["activity"].get("volume","0")))
                    trades=Decimal(entry["activity"]["trade_count"])
                    entry["derived_analytics"]={"derived":True,"formula_version":"1.0.0",
                        "price_return_from_pre":str(Decimal(entry["ohlcv"][3])/pre_close-1) if pre_close else None,
                        "volume_vs_pre":str(volume/pre_volume) if pre_volume else None,
                        "trade_count_vs_pre":str(trades/pre_trades) if pre_trades else None}
    return window

def content_hash(window):
    return hashlib.sha256(json.dumps(window,sort_keys=True,separators=(",", ":")).encode()).hexdigest()

def nearest_v4(event_ms:int)->dict[str,Any]:
    package={"derivatives":[],"options":None,"liquidity":None,"evidence":[]}
    for path in Path("derivatives/archive").rglob("*.json"):
        payload=json.loads(path.read_text()); eligible=[r for r in payload.get("records",[]) if r[0]<=event_ms]
        if eligible:
            row=eligible[-1]; package["derivatives"].append({"provider":payload["provider"],"instrument":payload["instrument"],"metric":payload["metric"],
              "source_timestamp":row[0],"event_offset_seconds":(row[0]-event_ms)//1000,"metric_status":"AVAILABLE","value":row[1:],
              "source_path":path.as_posix(),"source_schema_version":payload["schema_version"]})
    for domain,key in (("options/snapshots","options"),("liquidity/snapshots","liquidity")):
        candidates=[]
        for path in Path(domain).rglob("*.json"):
            payload=json.loads(path.read_text()); timestamp=payload["timestamp_ms"]
            if timestamp<=event_ms:candidates.append((timestamp,path,payload))
        if candidates:
            timestamp,path,payload=max(candidates,key=lambda x:x[0]); package[key]={"source_timestamp":timestamp,
              "event_offset_seconds":(timestamp-event_ms)//1000,"metric_status":"AVAILABLE","source_path":path.as_posix(),"data":payload}
    has_cvd=any(x["metric"]=="cvd" for x in package["derivatives"]); has_liq=any(x["metric"]=="liquidation-volume" for x in package["derivatives"])
    package["evidence"]=[{"label":"DERIVATIVES_FLOW_CONFIRMATION","status":"INSUFFICIENT" if not has_cvd else "AVAILABLE_NOT_CLASSIFIED","formula_version":"1.0.0"},
                         {"label":"LONG_LIQUIDATION_STRESS","status":"INSUFFICIENT" if not has_liq else "AVAILABLE_NOT_CLASSIFIED","formula_version":"1.0.0"}]
    return package

def register(definition: dict[str, Any]) -> dict[str, Any]:
    event_ms=parse_time(definition["event_time_utc"]); window=market_window(event_ms); digest=content_hash(window)
    dt=datetime.fromtimestamp(event_ms/1000,timezone.utc)
    path=Path("events")/f"{dt:%Y}"/f"{dt:%m}"/f"{dt:%d}"/f"{definition['event_id']}.json"
    payload={"schema_version":EVENT_VERSION,"event":definition,"market_window":window,"market_window_sha256":digest,"market_intelligence_v4":nearest_v4(event_ms)}
    atomic_json(path,payload)
    manifest_path=Path("events/manifest.json")
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {"schema_version":EVENT_VERSION,"events":[]}
    record={"event_id":definition["event_id"],"event_time_utc":definition["event_time_utc"],"priority":definition.get("priority"),
            "status":definition.get("status","REGISTERED"),"snapshot_status":"COMPLETE" if all(x["data_status"]=="AVAILABLE" for x in window) else "PARTIAL",
            "path":path.as_posix(),"market_window_sha256":digest}
    manifest["events"]=[x for x in manifest["events"] if x["event_id"]!=record["event_id"]]+[record]
    manifest["events"].sort(key=lambda x:x["event_time_utc"]); manifest["event_count"]=len(manifest["events"])
    manifest["latest_event"]=manifest["events"][-1]["event_id"] if manifest["events"] else None
    atomic_json(manifest_path,manifest)
    return payload

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("definition",type=Path); args=parser.parse_args()
    payload=register(json.loads(args.definition.read_text())); print("MARKET_WINDOW_SHA256="+payload["market_window_sha256"])

if __name__=="__main__": main()
