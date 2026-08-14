from __future__ import annotations
import json, time, urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from archive import atomic_json

VERSION="1.0.0"; RAW="https://raw.githubusercontent.com/vitaliipython-ship-it/eth-macro-data-bridge/main/"
BINANCE_SYMBOLS=("ETHUSDT","BTCUSDT"); KRAKEN_SYMBOLS=("PI_ETHUSD","PI_XBTUSD")
BINANCE_USDM_BASES=("https://fapi.binance.com",)
BINANCE_SPOT_DEPTH_BASES=("https://data-api.binance.vision","https://api.binance.com","https://api-gcp.binance.com","https://api1.binance.com","https://api2.binance.com","https://api3.binance.com","https://api4.binance.com")
KRAKEN_METRICS=("open-interest","aggressor-differential","trade-volume","trade-count","liquidation-volume",
 "rolling-volatility","long-short-ratio","cvd","spreads","liquidity","slippage","future-basis","funding")

def iso(ms:int)->str: return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def day(ms:int)->str: return datetime.fromtimestamp(ms/1000,timezone.utc).strftime("%Y/%m/%d")
def append(path:Path, metadata:dict[str,Any], records:list[Any], key=lambda x:x[0]):
    old=json.loads(path.read_text()) if path.exists() else {**metadata,"records":[]}
    index={key(row):row for row in old["records"]}
    for row in records:
        identity=key(row)
        if identity in index and index[identity]!=row: raise ValueError(f"historical conflict {path} {identity}")
        index[identity]=row
    old.update(metadata); old["records"]=[index[k] for k in sorted(index)]; atomic_json(path,old)
    return len(old["records"])

def depth_metrics(book:dict[str,Any], timestamp:int, provider:str, instrument:str)->dict[str,Any]:
    bids=[[Decimal(str(p)),Decimal(str(q))] for p,q,*_ in book["bids"]]; asks=[[Decimal(str(p)),Decimal(str(q))] for p,q,*_ in book["asks"]]
    assert bids==sorted(bids,reverse=True) and asks==sorted(asks)
    best_bid,best_ask=bids[0][0],asks[0][0]; mid=(best_bid+best_ask)/2
    out={"schema_version":VERSION,"provider":provider,"instrument":instrument,"timestamp_ms":timestamp,
         "best_bid":str(best_bid),"best_ask":str(best_ask),"mid_price":str(mid),"spread_absolute":str(best_ask-best_bid),
         "spread_bps":str((best_ask-best_bid)/mid*10000),"depth":{},"slippage":{},"raw":{"bids":[[str(x),str(y)] for x,y in bids[:20]],"asks":[[str(x),str(y)] for x,y in asks[:20]]}}
    for bps in (10,25,50):
        bid=sum(p*q for p,q in bids if p>=mid*(1-Decimal(bps)/10000)); ask=sum(p*q for p,q in asks if p<=mid*(1+Decimal(bps)/10000)); total=bid+ask
        out["depth"][str(bps)]={"bid_quote":str(bid),"ask_quote":str(ask),"imbalance":str((bid-ask)/total) if total else None}
    for notional in (10000,100000,1000000):
        out["slippage"][str(notional)]={"buy_bps":walk(asks,Decimal(notional),mid,True),"sell_bps":walk(bids,Decimal(notional),mid,False)}
    return out

def walk(levels,notional,mid,buy):
    remaining=notional; base=Decimal(0)
    for price,qty in levels:
        take=min(remaining,price*qty); base+=take/price; remaining-=take
        if remaining<=0: break
    if remaining>0 or not base:return None
    average=notional/base; return str(((average-mid)/mid if buy else (mid-average)/mid)*10000)

def collect_binance(get,now):
    base=BINANCE_USDM_BASES[0]; generated=iso(now); instruments={}; requests=0
    fetched={}; failures=[]
    for symbol in BINANCE_SYMBOLS:
        endpoints={"klines":f"/fapi/v1/klines?symbol={symbol}&interval=5m&limit=500","premiumIndex":f"/fapi/v1/premiumIndex?symbol={symbol}","openInterest":f"/fapi/v1/openInterest?symbol={symbol}","fundingRate":f"/fapi/v1/fundingRate?symbol={symbol}&limit=100","openInterestHist":f"/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=500"}
        fetched[symbol]={}
        for name,path in endpoints.items():
            try: fetched[symbol][name]=get(base+path)
            except Exception as exc: failures.append(f"{symbol} {name} {base}: {type(exc).__name__}: {exc}")
            requests+=1
    if failures: raise RuntimeError(" | ".join(failures))
    for symbol in BINANCE_SYMBOLS:
        klines=fetched[symbol]["klines"]
        closed=[[int(r[0]),str(r[1]),str(r[2]),str(r[3]),str(r[4]),str(r[5]),int(r[6]),str(r[7]),int(r[8]),str(r[9]),str(r[10])] for r in klines if now>int(r[6])]
        byday={}
        for row in closed: byday.setdefault(day(row[0]),[]).append(row)
        for date,rows in byday.items(): append(Path("derivatives/archive")/date/"binance-usdm"/f"{symbol}-perp-5m.json",
          {"schema_version":VERSION,"provider":"binance-usdm","instrument":symbol,"metric":"perp-kline","columns":["open_time_ms","open","high","low","close","base_volume","close_time_ms","quote_volume","trade_count","taker_buy_base_volume","taker_buy_quote_volume"]},rows)
        premium=fetched[symbol]["premiumIndex"]; oi=fetched[symbol]["openInterest"]
        funding=fetched[symbol]["fundingRate"]; oih=fetched[symbol]["openInterestHist"]
        funding_rows=[[int(x["fundingTime"]),str(x["fundingRate"]),str(x.get("markPrice"))] for x in funding]
        oi_rows=[[int(x["timestamp"]),str(x["sumOpenInterest"]),str(x["sumOpenInterestValue"])] for x in oih]
        for metric,rows,columns in (("funding",funding_rows,["funding_time_ms","funding_rate","mark_price"]),("open-interest",oi_rows,["timestamp_ms","sum_open_interest","sum_open_interest_value"])):
            grouped={}
            for row in rows: grouped.setdefault(day(row[0]),[]).append(row)
            for date,part in grouped.items(): append(Path("derivatives/archive")/date/"binance-usdm"/f"{symbol}-{metric}.json",{"schema_version":VERSION,"provider":"binance-usdm","instrument":symbol,"metric":metric,"columns":columns},part)
        instruments[symbol]={"latest_kline_path":f"derivatives/archive/{day(closed[-1][0])}/binance-usdm/{symbol}-perp-5m.json","latest":{
          "timestamp_ms":int(premium["time"]),"mark_price":str(premium["markPrice"]),"index_price":str(premium["indexPrice"]),
          "basis_absolute":str(Decimal(premium["markPrice"])-Decimal(premium["indexPrice"])),"basis_bps":str((Decimal(premium["markPrice"])/Decimal(premium["indexPrice"])-1)*10000),
          "funding_rate":str(premium["lastFundingRate"]),"open_interest":str(oi["openInterest"])}}
    return {"status":"PASS","remote_access":True,"route":base,"instruments":instruments,"historical_liquidations":"UNAVAILABLE","requests":requests}

def flatten_kraken(result):
    ts=result["timestamp"]; data=result["data"]
    if isinstance(data,list): return [[int(t)*1000 if int(t)<10**12 else int(t),data[i]] for i,t in enumerate(ts)]
    keys=[]
    def walk(prefix,obj):
        if isinstance(obj,dict):
            for k,v in obj.items(): walk(prefix+[k],v)
        elif isinstance(obj,list): keys.append((".".join(prefix),obj))
    walk([],data)
    return [[int(t)*1000 if int(t)<10**12 else int(t),{k:v[i] for k,v in keys}] for i,t in enumerate(ts)]

def collect_kraken(get,now):
    since=int(now/1000)-7*86400; instruments={}; requests=1
    discovered=get("https://futures.kraken.com/derivatives/api/v3/instruments")["instruments"]
    available={x["symbol"] for x in discovered if x.get("tradeable")}
    for symbol in KRAKEN_SYMBOLS:
        if symbol not in available: raise ValueError(f"Kraken instrument unavailable: {symbol}")
        metrics={}
        for metric in KRAKEN_METRICS:
            url=f"https://futures.kraken.com/api/charts/v1/analytics/{symbol}/{metric}?since={since}&interval=300"
            response=get(url); requests+=1
            if response.get("errors"): raise ValueError(f"Kraken {symbol} {metric}: {response['errors']}")
            rows=flatten_kraken(response["result"]); grouped={}
            for row in rows: grouped.setdefault(day(row[0]),[]).append(row)
            paths=[]
            for date,part in grouped.items():
                path=Path("derivatives/archive")/date/"kraken-futures"/f"{symbol}-{metric}.json"; paths.append(path)
                append(path,{"schema_version":VERSION,"provider":"kraken-futures","instrument":symbol,"metric":metric,"resolution_seconds":300},part)
            metrics[metric]={"path":paths[-1].as_posix() if paths else None,"record_count":len(rows),"latest":rows[-1] if rows else None}
        instruments[symbol]={"metrics":metrics}
    return {"status":"PASS","instruments":instruments,"requests":requests}

def deribit(url,get): return get("https://www.deribit.com/api/v2/public/"+url)["result"]
def collect_options(get,now):
    instruments=deribit("get_instruments?currency=ETH&kind=option&expired=false",get); summaries=deribit("get_book_summary_by_currency?currency=ETH&kind=option",get)
    definitions={x["instrument_name"]:x for x in instruments}; summary={x["instrument_name"]:x for x in summaries}; underlying=Decimal(str(next(iter(summaries))["underlying_price"]))
    expiries=sorted({x["expiration_timestamp"] for x in instruments}); targets=[]
    for days in (7,30,90): targets.append(min(expiries,key=lambda x:abs(x-now-days*86400000)))
    selected=[]; requests=2
    for expiry in sorted(set(targets)):
        candidates=sorted([x for x in instruments if x["expiration_timestamp"]==expiry],key=lambda x:abs(Decimal(str(x["strike"]))-underlying))[:16]
        tickers=[]
        for item in candidates:
            ticker=deribit("ticker?instrument_name="+urllib.parse.quote(item["instrument_name"]),get); requests+=1
            tickers.append({**item,"ticker":ticker})
        for option_type,target_delta in (("call",Decimal("0.25")),("put",Decimal("-0.25"))):
            typed=[x for x in tickers if x["option_type"]==option_type and x["ticker"].get("greeks")]
            if typed:selected.append(min(typed,key=lambda x:abs(Decimal(str(x["ticker"]["greeks"]["delta"]))-target_delta)))
        for option_type in ("call","put"):
            typed=[x for x in tickers if x["option_type"]==option_type]
            if typed:selected.append(min(typed,key=lambda x:abs(Decimal(str(x["strike"]))-underlying)))
    surface=[]
    for name,item in definitions.items():
        s=summary.get(name,{})
        surface.append([int(item["expiration_timestamp"]),str(item["strike"]),item["option_type"],s.get("open_interest") or 0,s.get("volume") or 0,s.get("bid_price"),s.get("ask_price"),s.get("mid_price"),s.get("mark_price"),s.get("mark_iv")])
    snapshot=Path("options/snapshots")/day(now)/f"{now}.json"; atomic_json(snapshot,{"schema_version":VERSION,"provider":"deribit","timestamp_ms":now,"scope":"FULL_ACTIVE_CHAIN_COMPACT","instrument_key":"ETH-{expiration_timestamp}-{strike}-{C|P}","discovered_option_count":len(definitions),"columns":["expiration_timestamp","strike","option_type","open_interest","volume_24h","best_bid","best_ask","mid","mark","mark_iv"],"options":surface,
      "selected_greeks":[{"instrument_name":x["instrument_name"],"expiry":x["expiration_timestamp"],"actual_dte":(x["expiration_timestamp"]-now)/86400000,"strike":x["strike"],"option_type":x["option_type"],"greeks":x["ticker"].get("greeks"),"mark_iv":x["ticker"].get("mark_iv")} for x in selected]})
    start=now-30*86400000; dvol=deribit(f"get_volatility_index_data?currency=ETH&start_timestamp={start}&end_timestamp={now}&resolution=60",get)["data"]
    byday={}
    for row in dvol: byday.setdefault(day(int(row[0])),[]).append(row)
    for date,rows in byday.items(): append(Path("options/archive")/date/"deribit/ETH-volatility-index.json",{"schema_version":VERSION,"provider":"deribit","metric":"ETH-DVOL","resolution_minutes":60,"columns":["timestamp_ms","open","high","low","close"]},rows)
    calls=[r for r in surface if r[2]=="call"]; puts=[r for r in surface if r[2]=="put"]
    analytics={"total_call_oi":str(sum(Decimal(str(x[3])) for x in calls)),"total_put_oi":str(sum(Decimal(str(x[3])) for x in puts)),
      "put_call_oi_ratio":str(sum(Decimal(str(x[3])) for x in puts)/sum(Decimal(str(x[3])) for x in calls)) if sum(Decimal(str(x[3])) for x in calls) else None}
    return {"status":"PASS","latest_surface":snapshot.as_posix(),"dvol_latest_path":f"options/archive/{day(now)}/deribit/ETH-volatility-index.json","option_count":len(surface),"selected_count":len(selected),"analytics":analytics,"requests":requests+1}

def fetch_first(get,bases,path):
    errors=[]
    for base in bases:
        try:return get(base+path),base
        except Exception as exc: errors.append(f"{base}: {type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(errors))

def collect_liquidity(get,now,selected_options,kraken_status):
    entries=[]; providers={}; requests=0
    def provider(name,fn):
        nonlocal requests
        try:
            rows,route,count=fn(); requests+=count; entries.extend(rows)
            providers[name]={"status":"PASS","route":route,"snapshot_count":len(rows),"error":None}
        except Exception as exc:
            providers[name]={"status":"DEGRADED","route":None,"snapshot_count":0,"error":f"{type(exc).__name__}: {exc}"}
    def spot():
        rows=[]; route=None
        for symbol in BINANCE_SYMBOLS:
            book,used=fetch_first(get,BINANCE_SPOT_DEPTH_BASES,f"/api/v3/depth?symbol={symbol}&limit=100"); route=used
            rows.append(depth_metrics(book,now,"binance-spot",symbol))
        return rows,route,2
    def futures():
        rows=[]
        for symbol in BINANCE_SYMBOLS:
            book,used=fetch_first(get,BINANCE_USDM_BASES,f"/fapi/v1/depth?symbol={symbol}&limit=100")
            rows.append(depth_metrics(book,now,"binance-usdm",symbol))
        return rows,used,2
    def deribit_books():
        rows=[]; names=["ETH-PERPETUAL"]+(selected_options or [])[:8]
        for name in names:
            book=deribit("get_order_book?depth=20&instrument_name="+urllib.parse.quote(name),get)
            rows.append(depth_metrics(book,now,"deribit",name))
        return rows,"https://www.deribit.com/api/v2/public",len(names)
    provider("binance-spot",spot); provider("binance-usdm",futures); provider("deribit",deribit_books)
    providers["kraken-futures-analytics"]={"status":kraken_status,"route":"https://futures.kraken.com/api/charts/v1/analytics","snapshot_count":0,"error":None if kraken_status=="PASS" else "Kraken Futures analytics unavailable"}
    usable_eth=any(x["instrument"] in ("ETHUSDT","ETH-PERPETUAL") for x in entries)
    status="PASS" if all(x["status"]=="PASS" for x in providers.values()) else ("DEGRADED" if usable_eth else "FAIL")
    path=Path("liquidity/snapshots")/day(now)/f"{now}.json"; atomic_json(path,{"schema_version":VERSION,"timestamp_ms":now,"snapshots":entries,"context":"HOURLY_CONTEXT_ONLY"})
    return {"status":status,"providers":providers,"latest_path":path.as_posix(),"snapshot_count":len(entries),"usable_eth_source":usable_eth,"requests":requests}

def health_policy(spot_status,binance_usdm_status,kraken_futures_status,deribit_status,liquidity_status):
    if spot_status!="PASS" or kraken_futures_status!="PASS" or deribit_status!="PASS": return "FAIL"
    return "PASS" if binance_usdm_status==liquidity_status=="PASS" else "DEGRADED"

def collect_intelligence(get,now):
    errors=[]
    def safe(name,fn):
        try:return fn()
        except Exception as exc: errors.append(f"{name}: {exc}"); return {"status":"DEGRADED","error":str(exc),"requests":0}
    b=safe("binance-usdm",lambda:collect_binance(get,now)); k=safe("kraken-futures",lambda:collect_kraken(get,now)); o=safe("deribit",lambda:collect_options(get,now))
    if b["status"]!="PASS": b.update({"remote_access":False,"route":BINANCE_USDM_BASES[0],"degradation_reason":b.get("error")})
    selected=[]
    if o.get("latest_surface"):
        selected=[x["instrument_name"] for x in json.loads(Path(o["latest_surface"]).read_text()).get("selected_greeks",[])]
    l=safe("liquidity",lambda:collect_liquidity(get,now,selected,k["status"]))
    derivatives={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{"binance-usdm":b["status"],"kraken-futures":k["status"]},"providers":{"binance-usdm":b,"kraken-futures":k},"available_metrics":["perp_ohlcv","mark","index","basis","funding","open_interest","aggressor_differential","cvd","liquidations","long_short","volatility","liquidity","slippage"],"errors":errors}
    options={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{"deribit":o["status"]},"providers":{"deribit":o},"freshness_minutes":90,"errors":errors}
    liquidity={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{x:y["status"] for x,y in l.get("providers",{}).items()},"providers":l.get("providers",{}),"collection":l,"errors":errors}
    latest={}; evidence=[]
    for symbol in BINANCE_SYMBOLS:
        try:
            spot=[r for r in json.loads(Path(f"data/binance/{symbol}/5m.json").read_text())["candles"] if r[-1]][-2:]
            perp_path=Path(b["instruments"][symbol]["latest_kline_path"]); perp=json.loads(perp_path.read_text())["records"][-2:]
            oi_paths=sorted(Path("derivatives/archive").rglob(f"{symbol}-open-interest.json")); oi=json.loads(oi_paths[-1].read_text())["records"][-2:]
            spot_ret=Decimal(spot[-1][4])/Decimal(spot[-2][4])-1; perp_ret=Decimal(perp[-1][4])/Decimal(perp[-2][4])-1
            oi_change=Decimal(oi[-1][1])-Decimal(oi[-2][1]); price_change=Decimal(perp[-1][4])-Decimal(perp[-2][4])
            regime=("PRICE_UP_" if price_change>=0 else "PRICE_DOWN_")+("OI_UP" if oi_change>=0 else "OI_DOWN")
            latest[symbol]={"spot_return":str(spot_ret),"perp_return":str(perp_ret),"open_interest_change_abs":str(oi_change),
              "open_interest_change_pct":str(oi_change/Decimal(oi[-2][1])) if Decimal(oi[-2][1]) else None,"oi_price_regime":regime,
              "basis_bps":b["instruments"][symbol]["latest"]["basis_bps"],"funding_current":b["instruments"][symbol]["latest"]["funding_rate"],
              "formula_version":"1.0.0","derived":True,"sources":[perp_path.as_posix(),oi_paths[-1].as_posix(),f"data/binance/{symbol}/5m.json"]}
            evidence.append({"label":"LEVERAGE_EXPANSION" if oi_change>=0 else "LEVERAGE_CONTRACTION","status":"SUPPORTED","provider":"binance-usdm","instrument":symbol,"timestamp_ms":now,"confidence":"MECHANICAL","required_fields":["perp_price","open_interest"],"formula_version":"1.0.0"})
        except Exception as exc: errors.append(f"analytics {symbol}: {exc}")
    spot=json.loads(Path("data/manifest.json").read_text())["providers"]["binance"]["status"]
    overall=health_policy(spot,b["status"],k["status"],o["status"],l["status"])
    analytics={"schema_version":VERSION,"generated_at_utc":iso(now),"raw_is_not_derived":True,"spot_taker_flow_label":"BINANCE_SPOT_TAKER_FLOW_PROXY","kraken_cvd_label":"KRAKEN_FUTURES_CVD_NATIVE","latest":latest,"evidence":evidence,"options":o.get("analytics"),"overall_data_plane_status":overall,"errors":errors}
    for path,payload in (("derivatives/manifest.json",derivatives),("options/manifest.json",options),("liquidity/manifest.json",liquidity),("analytics/manifest.json",analytics)): atomic_json(Path(path),payload)
    print("BINANCE_USDM_STATUS="+b["status"]); print("BINANCE_USDM_ERROR="+str(b.get("error") or "")); print("KRAKEN_FUTURES_STATUS="+k["status"]); print("KRAKEN_FUTURES_ERROR="+str(k.get("error") or "")); print("DERIBIT_STATUS="+o["status"]); print("DERIBIT_ERROR="+str(o.get("error") or "")); print("LIQUIDITY_STATUS="+l["status"]); print("LIQUIDITY_ERROR="+str(l.get("error") or ""))
    print("DERIVATIVES_STATUS="+("PASS" if b["status"]==k["status"]=="PASS" else "DEGRADED")); print("OPTIONS_STATUS="+o["status"]); print("OVERALL_DATA_PLANE_STATUS="+analytics["overall_data_plane_status"])
    return {"derivatives":derivatives,"options":options,"liquidity":liquidity,"analytics":analytics}
