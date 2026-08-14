from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from archive import atomic_json, load_series, partition_path

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
                    entry.update({"actual_candle_open_time_ms":row[0],"ohlcv":row[1:6],"closed":True,
                                  "source_archive_path":partition_path(provider,symbol,datetime.fromtimestamp(row[0]/1000,timezone.utc).strftime("%Y-%m-%d")).as_posix()})
                window.append(entry)
    return window

def content_hash(window):
    return hashlib.sha256(json.dumps(window,sort_keys=True,separators=(",", ":")).encode()).hexdigest()

def register(definition: dict[str, Any]) -> dict[str, Any]:
    event_ms=parse_time(definition["event_time_utc"]); window=market_window(event_ms); digest=content_hash(window)
    dt=datetime.fromtimestamp(event_ms/1000,timezone.utc)
    path=Path("events")/f"{dt:%Y}"/f"{dt:%m}"/f"{dt:%d}"/f"{definition['event_id']}.json"
    payload={"schema_version":EVENT_VERSION,"event":definition,"market_window":window,"market_window_sha256":digest}
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
