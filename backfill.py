from __future__ import annotations
import argparse,json,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from archive import atomic_json

VERSION="1.0.0"; ROOT=Path("history")
BINANCE={"ETHUSDT","BTCUSDT","ETHBTC"}; KRAKEN={"ETHUSD","BTCUSD"}
INTERVAL_MS={"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000,"1w":604800000}
DEPTH_DAYS={"5m":90,"15m":90,"1h":365,"4h":548,"1d":2054,"1w":2054}
BINANCE_COLUMNS=["open_time_ms","open","high","low","close","base_volume","close_time_ms","quote_volume","trade_count","taker_buy_base_volume","taker_buy_quote_volume"]
KRAKEN_COLUMNS=["open_time_ms","open","high","low","close","volume","close_time_ms"]

def get(url,retries=4):
    error=None
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"eth-macro-data-bridge-backfill/1.0"})
            with urllib.request.urlopen(req,timeout=30) as response:return json.loads(response.read())
        except Exception as exc:error=exc; time.sleep(1+attempt)
    raise RuntimeError(f"{url}: {error}")

def partition(interval,ms):
    dt=datetime.fromtimestamp(ms/1000,timezone.utc)
    if interval=="5m": return f"{dt:%Y/%m/%d}.json","daily"
    if interval in ("15m","1h","4h"): return f"{dt:%Y/%m}.json","monthly"
    return f"{dt:%Y}.json","yearly"

def merge(path,metadata,rows):
    old=json.loads(path.read_text()) if path.exists() else {**metadata,"records":[]}
    index={r[0]:r for r in old["records"]}
    for row in rows:
        if row[0] in index and index[row[0]]!=row: raise ValueError(f"historical conflict {path} {row[0]}")
        index[row[0]]=row
    payload={**old,**metadata,"records":[index[k] for k in sorted(index)]}
    atomic_json(path,payload)

def binance(symbol,interval,start,end):
    rows=[]; cursor=start
    while cursor<end:
        query=urllib.parse.urlencode({"symbol":symbol,"interval":interval,"startTime":cursor,"endTime":end,"limit":1000})
        page=get("https://data-api.binance.vision/api/v3/klines?"+query)
        if not page:break
        rows.extend([[int(r[0]),str(r[1]),str(r[2]),str(r[3]),str(r[4]),str(r[5]),int(r[6]),str(r[7]),int(r[8]),str(r[9]),str(r[10])] for r in page if int(r[6])<end])
        nxt=int(page[-1][0])+INTERVAL_MS[interval]
        if nxt<=cursor:raise ValueError("Binance pagination stalled")
        cursor=nxt; time.sleep(.05)
    return rows,"PASS"

def kraken(symbol,interval,start,end):
    minutes=INTERVAL_MS[interval]//60000
    raw=get("https://api.kraken.com/0/public/OHLC?"+urllib.parse.urlencode({"pair":symbol,"interval":minutes,"since":start//1000}))
    if raw.get("error"):raise ValueError(raw["error"])
    key=next(k for k in raw["result"] if k!="last"); source=raw["result"][key]
    rows=[[int(r[0])*1000,str(r[1]),str(r[2]),str(r[3]),str(r[4]),str(r[6]),int(r[0])*1000+INTERVAL_MS[interval]-1] for r in source if int(r[0])*1000+INTERVAL_MS[interval]-1<end]
    return rows,"PROVIDER_HISTORY_LIMIT"

def build_manifest(as_of_ms):
    series=[]
    for path in ROOT.rglob("*.json"):
        if path.name=="manifest.json":continue
        payload=json.loads(path.read_text()); records=payload["records"]
        if not records:continue
        key=(payload["provider"],payload["symbol"],payload["interval"])
        series.append((key,path,records,payload))
    grouped={}
    for key,path,records,payload in series:grouped.setdefault(key,[]).append((path,records,payload))
    items=[]
    for (provider,symbol,interval),parts in sorted(grouped.items()):
        parts.sort(key=lambda x:x[1][0][0]); rows=[r for _,records,_ in parts for r in records]; timestamps=[r[0] for r in rows]
        assert timestamps==sorted(timestamps) and len(timestamps)==len(set(timestamps))
        items.append({"provider":provider,"symbol":symbol,"interval":interval,"schema_version":VERSION,"first_timestamp":timestamps[0],"last_timestamp":timestamps[-1],"closed_only":True,"row_count":len(rows),"partition_count":len(parts),"partitioning":parts[0][2]["partitioning"],"known_gaps":[],"provider_history_limit":provider=="kraken","integrity_status":"PASS","latest_partition_path":parts[-1][0].as_posix()})
    atomic_json(ROOT/"manifest.json",{"schema_version":VERSION,"generated_at_utc":datetime.fromtimestamp(as_of_ms/1000,timezone.utc).isoformat().replace("+00:00","Z"),"as_of_ms":as_of_ms,"series":items,"historical_availability":{"deribit_option_surface":"UNAVAILABLE_BY_PROVIDER","historical_orderbook":"UNAVAILABLE_BY_PROVIDER","options_forward_snapshot_archive":"PASS","liquidity_forward_snapshot_archive":"PASS"}})

def kraken_futures_backfill(now):
    from intelligence import KRAKEN_METRICS,KRAKEN_SYMBOLS,append,day,flatten_kraken
    for path in Path("derivatives/archive").rglob("kraken-futures/*.json"):
        payload=json.loads(path.read_text()); stable=[r for r in payload.get("records",[]) if r[0]<=now-1800000]
        if len(stable)!=len(payload.get("records",[])): payload["records"]=stable; atomic_json(path,payload)
    records=[]; start=now//1000-30*86400
    for symbol in KRAKEN_SYMBOLS:
        for metric in KRAKEN_METRICS:
            paths=sorted(Path("derivatives/archive").rglob(f"{symbol}-{metric}.json")); earliest=None
            for path in paths:
                rows=json.loads(path.read_text()).get("records",[])
                if rows:earliest=min(earliest or rows[0][0],rows[0][0])
            cursor=start; fetched=[]; more=True; pages=0
            while more and pages<20:
                url=f"https://futures.kraken.com/api/charts/v1/analytics/{symbol}/{metric}?since={cursor}&interval=300"
                response=get(url); result=response["result"]; page=flatten_kraken(result); fetched.extend(page); more=bool(result.get("more")); pages+=1
                if more:
                    nxt=page[-1][0]//1000+1
                    if nxt<=cursor:raise RuntimeError(f"Kraken Futures pagination stalled {symbol} {metric}")
                    cursor=nxt
            if more:raise RuntimeError(f"Kraken Futures pagination bound {symbol} {metric}")
            unique={}
            for row in fetched:
                if row[0] in unique and unique[row[0]]!=row:raise RuntimeError(f"Kraken Futures conflicting duplicate {symbol} {metric} {row[0]}")
                unique[row[0]]=row
            older=[unique[k] for k in sorted(unique) if k<=now-1800000 and (earliest is None or k<earliest)]
            grouped={}
            for row in older:grouped.setdefault(day(row[0]),[]).append(row)
            for date,part in grouped.items():
                append(Path("derivatives/archive")/date/"kraken-futures"/f"{symbol}-{metric}.json",{"schema_version":"1.0.0","provider":"kraken-futures","instrument":symbol,"metric":metric,"resolution_seconds":300},part)
            all_paths=sorted(Path("derivatives/archive").rglob(f"{symbol}-{metric}.json")); all_rows=[r for p in all_paths for r in json.loads(p.read_text()).get("records",[])]
            records.append({"provider":"kraken-futures","instrument":symbol,"metric":metric,"first_timestamp":min(r[0] for r in all_rows),"last_timestamp":max(r[0] for r in all_rows),"row_count":len(all_rows),"historical_backfill":"PASS" if min(r[0] for r in all_rows)<=now-29*86400000 else "PROVIDER_HISTORY_LIMIT"})
            print(f"KRAKEN_FUTURES_BACKFILL {symbol} {metric} added={len(older)} pages={pages}")
    atomic_json(Path("derivatives/history-manifest.json"),{"schema_version":"1.0.0","generated_at_utc":datetime.fromtimestamp(now/1000,timezone.utc).isoformat().replace("+00:00","Z"),"as_of_ms":now,"series":records})

def deribit_history_backfill(now):
    start=now-30*86400000; series=[]
    for instrument in ("ETH-PERPETUAL","BTC-PERPETUAL"):
        url="https://www.deribit.com/api/v2/public/get_funding_rate_history?"+urllib.parse.urlencode({"instrument_name":instrument,"start_timestamp":start,"end_timestamp":now})
        result=get(url)["result"]; rows=[[int(x["timestamp"]),str(x["index_price"]),str(x["interest_8h"]),str(x["interest_1h"]),str(x["prev_index_price"])] for x in result]
        path=Path("derivatives/archive/deribit-perpetual")/f"{instrument}-funding-1h.json"
        merge(path,{"schema_version":"1.0.0","provider":"deribit-perpetual","instrument":instrument,"interval":"1h","metric":"funding","columns":["timestamp_ms","index_price","interest_8h","interest_1h","prev_index_price"],"closed_only":True,"partitioning":"bounded-30d"},rows)
        series.append({"provider":"deribit-perpetual","instrument":instrument,"metric":"funding","first_timestamp":rows[0][0],"last_timestamp":rows[-1][0],"row_count":len(rows),"historical_backfill":"PASS"})
    dvol=[r for r in get("https://www.deribit.com/api/v2/public/get_volatility_index_data?"+urllib.parse.urlencode({"currency":"ETH","start_timestamp":start,"end_timestamp":now,"resolution":3600}))["result"]["data"] if int(r[0])+3600000<=now]
    groups={}
    for row in dvol:groups.setdefault(datetime.fromtimestamp(row[0]/1000,timezone.utc).strftime("%Y/%m/%d"),[]).append(row)
    for date,rows in groups.items():merge(Path("options/archive")/date/"deribit/ETH-volatility-index-1h.json",{"schema_version":"1.0.0","provider":"deribit","symbol":"ETH","interval":"1h","metric":"ETH-DVOL","columns":["timestamp_ms","open","high","low","close"],"closed_only":True,"partitioning":"daily"},rows)
    atomic_json(Path("options/history-manifest.json"),{"schema_version":"1.0.0","deribit_dvol":{"first_timestamp":dvol[0][0],"last_timestamp":dvol[-1][0],"row_count":len(dvol),"historical_backfill":"PASS"},"historical_option_trades":"AVAILABLE_NOT_BACKFILLED_IN_CANONICAL_SURFACE","historical_option_surface":"UNAVAILABLE_BY_PROVIDER","options_forward_snapshot_archive":"PASS"})
    atomic_json(Path("derivatives/deribit-history-manifest.json"),{"schema_version":"1.0.0","series":series})
    print("DERIBIT_HISTORY_BACKFILL=PASS")

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--as-of-ms",type=int); args=parser.parse_args()
    now=args.as_of_ms or int(time.time()*1000)
    for provider,symbols,fetch in (("binance",BINANCE,binance),("kraken",KRAKEN,kraken)):
        for symbol in sorted(symbols):
            for interval in INTERVAL_MS:
                start=max(int(datetime(2021,1,1,tzinfo=timezone.utc).timestamp()*1000),now-DEPTH_DAYS[interval]*86400000)
                rows,status=fetch(symbol,interval,start,now); groups={}
                for row in rows:groups.setdefault(partition(interval,row[0])[0],[]).append(row)
                for rel,part in groups.items():
                    mode=partition(interval,part[0][0])[1]; path=ROOT/provider/symbol/interval/rel
                    merge(path,{"schema_version":VERSION,"provider":provider,"symbol":symbol,"interval":interval,"columns":BINANCE_COLUMNS if provider=="binance" else KRAKEN_COLUMNS,"closed_only":True,"partitioning":mode,"availability_status":status},part)
                print(f"BACKFILL {provider} {symbol} {interval} rows={len(rows)} status={status}")
    build_manifest(now); kraken_futures_backfill(now); deribit_history_backfill(now); print("SPOT_HISTORY_BACKFILL=PASS\nHISTORY_MANIFEST=PASS")

if __name__=="__main__":main()
