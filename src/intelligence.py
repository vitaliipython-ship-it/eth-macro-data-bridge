from __future__ import annotations
import json, time, urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from archive import atomic_json
from history_store import append_partition

VERSION="1.0.0"; RAW="https://raw.githubusercontent.com/vitaliipython-ship-it/eth-macro-data-bridge/main/"
BINANCE_SYMBOLS=("ETHUSDT","BTCUSDT"); KRAKEN_SYMBOLS=("PI_ETHUSD","PI_XBTUSD")
BINANCE_USDM_BASES=("https://fapi.binance.com",)
KRAKEN_METRICS=("open-interest","aggressor-differential","trade-volume","trade-count","liquidation-volume",
 "rolling-volatility","long-short-ratio","cvd","spreads","liquidity","slippage","future-basis","funding")
KRAKEN_D8_OVERLAP_MS=6*3600000
DVOL_D8_OVERLAP_MS=24*3600000

def iso(ms:int)->str: return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def day(ms:int)->str: return datetime.fromtimestamp(ms/1000,timezone.utc).strftime("%Y/%m/%d")
def append(path:Path, metadata:dict[str,Any], records:list[Any], key=lambda x:x[0]):
    append_partition(path,metadata,records,key=key)
    return len(json.loads(path.read_text())["records"])

def depth_metrics(book:dict[str,Any], timestamp:int, provider:str, instrument:str, normalization="BASE_X_PRICE", underlying_price=None)->dict[str,Any]:
    bids=[[Decimal(str(p)),Decimal(str(q))] for p,q,*_ in book["bids"]]; asks=[[Decimal(str(p)),Decimal(str(q))] for p,q,*_ in book["asks"]]
    assert bids==sorted(bids,reverse=True) and asks==sorted(asks)
    best_bid,best_ask=bids[0][0],asks[0][0]; mid=(best_bid+best_ask)/2
    if normalization=="USD_AMOUNT": native_unit="USD"; normalized_unit="USD"; formula="amount_usd"; confidence="HIGH"; value=lambda p,q:q
    elif normalization=="OPTION_UNDERLYING_X_PRICE_X_INDEX" and underlying_price:
        native_unit="UNDERLYING_COIN"; normalized_unit="USD"; formula="amount_underlying*option_price_underlying*underlying_index_usd"; confidence="HIGH"; u=Decimal(str(underlying_price)); value=lambda p,q:p*q*u
    elif normalization=="OPTION_UNDERLYING_X_PRICE_X_INDEX":
        native_unit="UNDERLYING_COIN"; normalized_unit="UNAVAILABLE"; formula="UNAVAILABLE_WITHOUT_UNDERLYING_INDEX"; confidence="NONE"; value=lambda p,q:q
    else: native_unit="BASE_ASSET"; normalized_unit="QUOTE_ASSET"; formula="amount_base*price_quote_per_base"; confidence="HIGH"; value=lambda p,q:p*q
    out={"schema_version":VERSION,"provider":provider,"instrument":instrument,"timestamp_ms":timestamp,"native_amount_unit":native_unit,"normalized_notional_unit":normalized_unit,"normalization_formula":formula,"normalization_confidence":confidence,
         "best_bid":str(best_bid),"best_ask":str(best_ask),"mid_price":str(mid),"spread_absolute":str(best_ask-best_bid),
         "spread_bps":str((best_ask-best_bid)/mid*10000),"depth":{},"slippage":{},"usd_slippage_status":"AVAILABLE" if normalized_unit=="USD" else "UNAVAILABLE","raw_level_count":{"bids":len(bids),"asks":len(asks)},"raw":{"bids":[[str(x),str(y)] for x,y in bids],"asks":[[str(x),str(y)] for x,y in asks]}}
    for bps in (10,25,50):
        bid_levels=[(p,q) for p,q in bids if p>=mid*(1-Decimal(bps)/10000)]; ask_levels=[(p,q) for p,q in asks if p<=mid*(1+Decimal(bps)/10000)]
        bid=sum(value(p,q) for p,q in bid_levels); ask=sum(value(p,q) for p,q in ask_levels); total=bid+ask
        reached=bids[-1][0]<=mid*(1-Decimal(bps)/10000) and asks[-1][0]>=mid*(1+Decimal(bps)/10000)
        out["depth"][str(bps)]={"bid_quote":str(bid),"ask_quote":str(ask),"imbalance":str((bid-ask)/total) if total else None,"coverage_target_bps":bps,"book_reached_target":reached,"status":"COMPLETE" if reached else "TRUNCATED"}
    for notional in (10000,100000,1000000):
        out["slippage"][str(notional)]={"buy_bps":walk(asks,Decimal(notional),mid,True,value),"sell_bps":walk(bids,Decimal(notional),mid,False,value),"unit":normalized_unit}
    return out

def walk(levels,notional,mid,buy,value=lambda p,q:p*q):
    remaining=notional; weighted=Decimal(0); amount=Decimal(0)
    for price,qty in levels:
        level=value(price,qty); take=min(remaining,level); fraction=take/level if level else 0; weighted+=price*qty*fraction; amount+=qty*fraction; remaining-=take
        if remaining<=0: break
    if remaining>0 or not amount:return None
    average=weighted/amount; return str(((average-mid)/mid if buy else (mid-average)/mid)*10000)

def collect_binance(get,now):
    base=BINANCE_USDM_BASES[0]; instruments={}; requests=0
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
        if not closed: raise ValueError(f"Binance USD-M no closed kline: {symbol}")
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
        known=iso(now)
        funding_descriptors=[{"fundingTime":int(x["fundingTime"]),"fundingRate":str(x["fundingRate"]),"markPrice":None if x.get("markPrice") is None else str(x.get("markPrice")),"instrument":symbol,"known_at":known,"provenance":{"provider":"binance-usdm","provider_route":base,"source_endpoint":"fundingRate"}} for x in funding]
        oi_descriptors=[{"timestamp":int(x["timestamp"]),"sumOpenInterest":str(x["sumOpenInterest"]),"sumOpenInterestValue":str(x["sumOpenInterestValue"]),"instrument":symbol,"known_at":known,"provenance":{"provider":"binance-usdm","provider_route":base,"source_endpoint":"openInterestHist"}} for x in oih]
        instruments[symbol]={"latest_kline_path":f"derivatives/archive/{day(closed[-1][0])}/binance-usdm/{symbol}-perp-5m.json","open_interest_history_rows":oi_descriptors,"funding_history_rows":funding_descriptors,"latest":{
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

def refresh_kraken_history_manifest(now,root=Path("derivatives/archive")):
    series=[]
    for symbol in KRAKEN_SYMBOLS:
        for metric in KRAKEN_METRICS:
            rows=[]
            for path in sorted(root.rglob(f"{symbol}-{metric}.json")): rows.extend(json.loads(path.read_text()).get("records",[]))
            if not rows: raise RuntimeError(f"missing Kraken archive series {symbol} {metric}")
            rows.sort(key=lambda row:row[0]); timestamps=[row[0] for row in rows]
            if len(timestamps)!=len(set(timestamps)): raise RuntimeError(f"duplicate Kraken archive timestamp {symbol} {metric}")
            series.append({"provider":"kraken-futures","instrument":symbol,"metric":metric,"first_timestamp":timestamps[0],"last_timestamp":timestamps[-1],"row_count":len(rows),"historical_backfill":"PASS"})
    atomic_json(Path("derivatives/history-manifest.json"),{"schema_version":VERSION,"generated_at_utc":iso(now),"as_of_ms":now,"series":series})
    return series

def collect_kraken(get,now):
    since=int(now/1000)-7*86400; instruments={}; requests=1
    discovered=get("https://futures.kraken.com/derivatives/api/v3/instruments")["instruments"]
    available={x["symbol"] for x in discovered if x.get("tradeable")}
    for symbol in KRAKEN_SYMBOLS:
        if symbol not in available: raise ValueError(f"Kraken instrument unavailable: {symbol}")
        metrics={}
        for metric in KRAKEN_METRICS:
            existing_paths=sorted(Path("derivatives/archive").rglob(f"{symbol}-{metric}.json")); existing_tail=None; existing_latest=None; existing_latest_path=None
            for existing_path in existing_paths:
                existing_records=json.loads(existing_path.read_text()).get("records",[])
                if existing_records and (existing_tail is None or existing_records[-1][0]>existing_tail): existing_tail=existing_records[-1][0]; existing_latest=existing_records[-1]; existing_latest_path=existing_path
            cursor=max(since,(existing_tail//1000)+1 if existing_tail else since); rows=[]; pages=0; more=True
            while more and pages<6:
                url=f"https://futures.kraken.com/api/charts/v1/analytics/{symbol}/{metric}?since={cursor}&interval=300"
                response=get(url); requests+=1; pages+=1
                if response.get("errors"): raise ValueError(f"Kraken {symbol} {metric}: {response['errors']}")
                result=response["result"]; page=flatten_kraken(result); rows.extend(page); more=bool(result.get("more"))
                if more:
                    if not page or page[-1][0]//1000+1<=cursor: raise ValueError(f"Kraken {symbol} {metric}: pagination stalled")
                    cursor=page[-1][0]//1000+1
            if more: raise ValueError(f"Kraken {symbol} {metric}: pagination exceeded bounded 6 pages")
            unique={}
            for row in rows:
                if row[0] in unique and unique[row[0]]!=row: raise RuntimeError(f"Kraken conflicting duplicate {symbol} {metric} {row[0]}")
                unique[row[0]]=row
            fetched_rows=[unique[key] for key in sorted(unique)]; current_tail=fetched_rows[-1] if fetched_rows else existing_latest
            rows=[r for r in fetched_rows if r[0]<=now-1800000]; grouped={}
            for row in rows: grouped.setdefault(day(row[0]),[]).append(row)
            paths=[]
            for date,part in grouped.items():
                path=Path("derivatives/archive")/date/"kraken-futures"/f"{symbol}-{metric}.json"; paths.append(path)
                append(path,{"schema_version":VERSION,"provider":"kraken-futures","instrument":symbol,"metric":metric,"resolution_seconds":300},part)
            tail_row=current_tail; metric_path=paths[-1] if paths else existing_latest_path
            age=max(0,(now-tail_row[0])//1000) if tail_row else None
            freshness="LIVE_USABLE" if age is not None and age<=600 else ("RECENT_CONTEXT" if age is not None and age<=1800 else "STALE_FOR_CURRENT")
            eligible_rows=[r for r in rows if r[0]>=now-KRAKEN_D8_OVERLAP_MS]
            metrics[metric]={"path":metric_path.as_posix() if metric_path else None,"record_count":len(rows),"eligible_rows":eligible_rows,"eligible_overlap_ms":KRAKEN_D8_OVERLAP_MS,"latest":tail_row,"first_timestamp":rows[0][0] if rows else (tail_row[0] if tail_row else None),"last_timestamp":tail_row[0] if tail_row else None,"data_age_seconds":age,"more":more,"freshness_status":freshness,"pages":pages}
        instruments[symbol]={"metrics":metrics}
    refresh_kraken_history_manifest(now)
    return {"status":"PASS","instruments":instruments,"requests":requests}

def deribit(url,get): return get("https://www.deribit.com/api/v2/public/"+url)["result"]
def collect_options(get,now):
    instruments=deribit("get_instruments?currency=ETH&kind=option&expired=false",get); summaries=deribit("get_book_summary_by_currency?currency=ETH&kind=option",get)
    definitions={x["instrument_name"]:x for x in instruments}; summary={x["instrument_name"]:x for x in summaries}; underlying=Decimal(str(next(iter(summaries))["underlying_price"]))
    expiries=sorted({x["expiration_timestamp"] for x in instruments}); targets=[]
    for days in (7,30,90): targets.append(min(expiries,key=lambda x:abs(x-now-days*86400000)))
    selected=[]; requests=2
    target_days_by_expiry={expiry:days for days,expiry in zip((7,30,90),targets)}
    for expiry in sorted(set(targets)):
        candidates=sorted([x for x in instruments if x["expiration_timestamp"]==expiry],key=lambda x:abs(Decimal(str(x["strike"]))-underlying))[:16]
        tickers=[]
        for item in candidates:
            ticker=deribit("ticker?instrument_name="+urllib.parse.quote(item["instrument_name"]),get); requests+=1
            tickers.append({**item,"ticker":ticker})
        for option_type,target_delta in (("call",Decimal("0.25")),("put",Decimal("-0.25"))):
            typed=[x for x in tickers if x["option_type"]==option_type and x["ticker"].get("greeks")]
            if typed:selected.append({**min(typed,key=lambda x:abs(Decimal(str(x["ticker"]["greeks"]["delta"]))-target_delta)),"selection":"25d","target_days":target_days_by_expiry[expiry],"target_delta":str(target_delta)})
        for option_type in ("call","put"):
            typed=[x for x in tickers if x["option_type"]==option_type]
            if typed:selected.append({**min(typed,key=lambda x:abs(Decimal(str(x["strike"]))-underlying)),"selection":"atm","target_days":target_days_by_expiry[expiry]})
    surface=[]
    for name,item in definitions.items():
        s=summary.get(name,{})
        surface.append([int(item["expiration_timestamp"]),str(item["strike"]),item["option_type"],s.get("open_interest") or 0,s.get("volume") or 0,s.get("bid_price"),s.get("ask_price"),s.get("mid_price"),s.get("mark_price"),s.get("mark_iv"),s.get("underlying_price"),s.get("underlying_index"),s.get("interest_rate"),s.get("volume_usd")])
    selected_greeks=[{"instrument_name":x["instrument_name"],"expiry":x["expiration_timestamp"],"target_days":x["target_days"],"selection":x["selection"],"target_delta":x.get("target_delta"),"actual_dte":(x["expiration_timestamp"]-now)/86400000,"strike":x["strike"],"option_type":x["option_type"],"greeks":x["ticker"].get("greeks"),"mark_iv":x["ticker"].get("mark_iv"),"underlying_price":x["ticker"].get("underlying_price"),"underlying_index":x["ticker"].get("underlying_index"),"interest_rate":x["ticker"].get("interest_rate")} for x in selected]
    snapshot=Path("options/snapshots")/day(now)/f"{now}.json"; atomic_json(snapshot,{"schema_version":VERSION,"provider":"deribit","timestamp_ms":now,"scope":"FULL_ACTIVE_CHAIN_COMPACT","instrument_key":"ETH-{expiration_timestamp}-{strike}-{C|P}","discovered_option_count":len(definitions),"columns":["expiration_timestamp","strike","option_type","open_interest","volume_24h","best_bid","best_ask","mid","mark","mark_iv","underlying_price","underlying_index","interest_rate","volume_usd"],"options":surface,"selected_greeks":selected_greeks})
    start=now-30*86400000; dvol=[r for r in deribit(f"get_volatility_index_data?currency=ETH&start_timestamp={start}&end_timestamp={now}&resolution=3600",get)["data"] if int(r[0])+3600000<=now]
    byday={}
    for row in dvol: byday.setdefault(day(int(row[0])),[]).append(row)
    for date,rows in byday.items(): append(Path("options/archive")/date/"deribit/ETH-volatility-index-1h.json",{"schema_version":VERSION,"provider":"deribit","metric":"ETH-DVOL","resolution_seconds":3600,"columns":["timestamp_ms","open","high","low","close"]},rows)
    calls=[r for r in surface if r[2]=="call"]; puts=[r for r in surface if r[2]=="put"]
    call_oi=sum(Decimal(str(x[3])) for x in calls); put_oi=sum(Decimal(str(x[3])) for x in puts); call_vol=sum(Decimal(str(x[4])) for x in calls); put_vol=sum(Decimal(str(x[4])) for x in puts)
    analytics={"total_call_oi":str(call_oi),"total_put_oi":str(put_oi),"put_call_oi_ratio":str(put_oi/call_oi) if call_oi else None,"total_call_volume":str(call_vol),"total_put_volume":str(put_vol),"put_call_volume_ratio":str(put_vol/call_vol) if call_vol else None}
    for days in (7,30,90):
        chosen=[x for x in selected if x["target_days"]==days]; atm=[x for x in chosen if x["selection"]=="atm"]
        analytics[f"atm_iv_{days}d"] = str(sum(Decimal(str(x["ticker"]["mark_iv"])) for x in atm)/len(atm)) if atm else None
        analytics[f"actual_dte_{days}d"] = (chosen[0]["expiration_timestamp"]-now)/86400000 if chosen else None
        c=next((x for x in chosen if x["selection"]=="25d" and x["option_type"]=="call"),None); p=next((x for x in chosen if x["selection"]=="25d" and x["option_type"]=="put"),None)
        if c and p:
            civ=Decimal(str(c["ticker"]["mark_iv"])); piv=Decimal(str(p["ticker"]["mark_iv"])); atmiv=Decimal(str(analytics[f"atm_iv_{days}d"]))
            analytics[f"25d_{days}d"]={"call_iv":str(civ),"put_iv":str(piv),"call_actual_delta":str(c["ticker"]["greeks"]["delta"]),"put_actual_delta":str(p["ticker"]["greeks"]["delta"]),"call_delta_error":str(abs(Decimal(str(c["ticker"]["greeks"]["delta"]))-Decimal("0.25"))),"put_delta_error":str(abs(Decimal(str(p["ticker"]["greeks"]["delta"]))+Decimal("0.25"))),"risk_reversal":str(civ-piv),"butterfly":str((civ+piv)/2-atmiv)}
    analytics["iv_term_structure"]={str(d):analytics.get(f"atm_iv_{d}d") for d in (7,30,90)}
    if analytics.get("25d_30d"):
        selected_25d=analytics["25d_30d"]; analytics.update({"25d_call_iv":selected_25d["call_iv"],"25d_put_iv":selected_25d["put_iv"],"25d_call_actual_delta":selected_25d["call_actual_delta"],"25d_put_actual_delta":selected_25d["put_actual_delta"],"25d_risk_reversal":selected_25d["risk_reversal"],"25d_butterfly":selected_25d["butterfly"]})
    selected_option_names=[]
    for row in selected_greeks:
        name=row["instrument_name"]
        if name not in selected_option_names: selected_option_names.append(name)
    dvol_rows=[r for r in dvol if int(r[0])>=now-DVOL_D8_OVERLAP_MS]
    return {"status":"PASS","latest_surface":snapshot.as_posix(),"dvol_latest_path":f"options/archive/{day(now)}/deribit/ETH-volatility-index-1h.json","dvol_rows":dvol_rows,"dvol_overlap_ms":DVOL_D8_OVERLAP_MS,"selected_option_names":selected_option_names,"option_count":len(surface),"selected_count":len(selected),"analytics":analytics,"requests":requests+1}

def collect_deribit_perpetual(get,now):
    instruments={}
    for name in ("ETH-PERPETUAL","BTC-PERPETUAL"):
        ticker=deribit("ticker?instrument_name="+name,get); stats=ticker.get("stats") or {}; age=max(0,(now-int(ticker["timestamp"]))//1000)
        instruments[name]={"timestamp_ms":int(ticker["timestamp"]),"data_age_seconds":age,"freshness_status":"LIVE_USABLE" if age<=600 else ("RECENT_CONTEXT" if age<=1800 else "STALE_FOR_CURRENT"),"mark_price":ticker.get("mark_price"),"index_price":ticker.get("index_price"),"open_interest":ticker.get("open_interest"),"current_funding":ticker.get("current_funding"),"funding_8h":ticker.get("funding_8h"),"volume_24h":stats.get("volume"),"volume_usd_24h":stats.get("volume_usd")}
    return {"status":"PASS","route":"https://www.deribit.com/api/v2/public/ticker","instruments":instruments,"requests":2}

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
    def futures():
        rows=[]
        for symbol in BINANCE_SYMBOLS:
            book,used=fetch_first(get,BINANCE_USDM_BASES,f"/fapi/v1/depth?symbol={symbol}&limit=100"); rows.append(depth_metrics(book,now,"binance-usdm",symbol))
        return rows,used,2
    def deribit_books():
        rows=[]; names=["ETH-PERPETUAL"]+(selected_options or [])[:8]
        for name in names:
            book=deribit("get_order_book?depth=20&instrument_name="+urllib.parse.quote(name),get)
            mode="USD_AMOUNT" if name.endswith("PERPETUAL") else "OPTION_UNDERLYING_X_PRICE_X_INDEX"
            rows.append(depth_metrics(book,now,"deribit",name,mode,book.get("underlying_price")))
        return rows,"https://www.deribit.com/api/v2/public",len(names)
    providers["binance-spot"]={"status":"PASS","route":"CANONICAL_G2A_S3_DURABLE_BASELINE","snapshot_count":0,"error":None,"network_calls":0,"legacy_fixed_100_network_calls":0}
    providers["binance-usdm"]={"status":"DISABLED_BY_POLICY","route":None,"snapshot_count":0,"error":None,"network_calls":0}
    provider("deribit",deribit_books)
    providers["kraken-futures-analytics"]={"status":kraken_status,"route":"https://futures.kraken.com/api/charts/v1/analytics","snapshot_count":0,"error":None if kraken_status=="PASS" else "Kraken Futures analytics unavailable"}
    usable_eth=any(x["instrument"] in ("ETHUSDT","ETH-PERPETUAL") for x in entries)
    active=[x for x in providers.values() if x["status"]!="DISABLED_BY_POLICY"]
    status="PASS" if all(x["status"]=="PASS" for x in active) else ("DEGRADED" if usable_eth else "FAIL")
    path=Path("liquidity/snapshots")/day(now)/f"{now}.json"; atomic_json(path,{"schema_version":VERSION,"timestamp_ms":now,"snapshots":entries,"context":"HOURLY_CONTEXT_ONLY"})
    return {"status":status,"providers":providers,"latest_path":path.as_posix(),"snapshots":entries,"snapshot_count":len(entries),"usable_eth_source":usable_eth,"requests":requests}

def health_policy(spot_status,binance_usdm_status,kraken_futures_status,deribit_status,liquidity_status):
    if spot_status!="PASS" or kraken_futures_status!="PASS" or deribit_status!="PASS": return "FAIL"
    return "PASS" if binance_usdm_status in ("PASS","DISABLED_BY_POLICY") and liquidity_status=="PASS" else "DEGRADED"

def collect_intelligence(get,now):
    derivative_errors=[]; option_errors=[]; liquidity_errors=[]; analytics_errors=[]
    def safe(name,fn,domain_errors):
        try:return fn()
        except Exception as exc: domain_errors.append(f"{name}: {exc}"); return {"status":"DEGRADED","error":str(exc),"requests":0}
    b={"status":"DISABLED_BY_POLICY","current_collection":"DISABLED_BY_POLICY","network_calls":0,"error":None,"existing_archive":"FROZEN_HISTORICAL_REFERENCE","archive_continuously_accumulated":False,"archive_currently_updated":False,"signal_vote":"EXCLUDED","historical_archive_preserved":True,"runtime_scope":"CURRENT_GITHUB_HOSTED_ACQUISITION_ONLY","vps_target":"REQUIRED","vps_runtime":"NOT_ACTIVE","policy_reason":"GitHub-hosted runtime is not the qualified production acquisition route; future Binance USD-M activation requires separate D8 VPS qualification"}; k=safe("kraken-futures",lambda:collect_kraken(get,now),derivative_errors); dp=safe("deribit-perpetual",lambda:collect_deribit_perpetual(get,now),derivative_errors); o=safe("deribit-options",lambda:collect_options(get,now),option_errors)
    selected=list(o.get("selected_option_names") or [])
    l=safe("liquidity",lambda:collect_liquidity(get,now,selected,k["status"]),liquidity_errors)
    derivatives={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{"binance-usdm":b["status"],"kraken-futures":k["status"],"deribit-perpetual":dp["status"]},"providers":{"binance-usdm":b,"kraken-futures":k,"deribit-perpetual":dp},"available_metrics":["perp_ohlcv","mark","index","basis","funding","open_interest","aggressor_differential","cvd","liquidations","long_short","volatility","liquidity","slippage"],"errors":derivative_errors}
    options={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{"deribit":o["status"]},"providers":{"deribit":o},"freshness_minutes":90,"errors":option_errors}
    liquidity={"schema_version":VERSION,"generated_at_utc":iso(now),"provider_status":{x:y["status"] for x,y in l.get("providers",{}).items()},"providers":l.get("providers",{}),"collection":l,"errors":liquidity_errors}
    latest={}; evidence=[]
    for symbol in BINANCE_SYMBOLS if b["status"]=="PASS" else ():
        try:
            spot=[r for r in json.loads(Path(f"data/binance/{symbol}/5m.json").read_text())["candles"] if r[-1]][-2:]
            perp_path=Path(b["instruments"][symbol]["latest_kline_path"]); perp=json.loads(perp_path.read_text())["records"][-2:]
            oi_paths=sorted(Path("derivatives/archive").rglob(f"{symbol}-open-interest.json")); oi=json.loads(oi_paths[-1].read_text())["records"][-2:]
            spot_ret=Decimal(spot[-1][4])/Decimal(spot[-2][4])-1; perp_ret=Decimal(perp[-1][4])/Decimal(perp[-2][4])-1
            oi_change=Decimal(oi[-1][1])-Decimal(oi[-2][1]); price_change=Decimal(perp[-1][4])-Decimal(perp[-2][4])
            regime=("PRICE_UP_" if price_change>=0 else "PRICE_DOWN_")+("OI_UP" if oi_change>=0 else "OI_DOWN")
            latest[symbol]={"spot_return":str(spot_ret),"perp_return":str(perp_ret),"open_interest_change_abs":str(oi_change),"open_interest_change_pct":str(oi_change/Decimal(oi[-2][1])) if Decimal(oi[-2][1]) else None,"oi_price_regime":regime,"basis_bps":b["instruments"][symbol]["latest"]["basis_bps"],"funding_current":b["instruments"][symbol]["latest"]["funding_rate"],"formula_version":"1.0.0","derived":True,"sources":[perp_path.as_posix(),oi_paths[-1].as_posix(),f"data/binance/{symbol}/5m.json"]}
            evidence.append({"label":"LEVERAGE_EXPANSION" if oi_change>=0 else "LEVERAGE_CONTRACTION","status":"SUPPORTED","provider":"binance-usdm","instrument":symbol,"timestamp_ms":now,"confidence":"MECHANICAL","required_fields":["perp_price","open_interest"],"formula_version":"1.0.0"})
        except Exception as exc: analytics_errors.append(f"binance-usdm analytics {symbol}: {exc}")
    kraken_latest={symbol:{metric:data["latest"] for metric,data in value["metrics"].items() if data.get("freshness_status") in ("LIVE_USABLE","RECENT_CONTEXT")} for symbol,value in k.get("instruments",{}).items()}
    if kraken_latest: latest["kraken-futures"]={"analytics_provider":"KRAKEN_FUTURES_NATIVE","analytics_freshness":"LIVE_USABLE" if all(m["freshness_status"]=="LIVE_USABLE" for v in k["instruments"].values() for m in v["metrics"].values()) else "RECENT_CONTEXT","analytics_available_metrics":sorted(next(iter(k["instruments"].values()))["metrics"]),"instruments":kraken_latest}
    if dp.get("instruments"): latest["deribit-perpetual"]={"analytics_provider":"DERIBIT_PERPETUAL_CURRENT","analytics_freshness":"LIVE_USABLE" if all(x["freshness_status"]=="LIVE_USABLE" for x in dp["instruments"].values()) else "RECENT_CONTEXT","analytics_available_metrics":["mark_price","index_price","open_interest","current_funding","funding_8h","volume_24h","volume_usd_24h"],"instruments":dp["instruments"]}
    spot=json.loads(Path("data/manifest.json").read_text())["providers"]["binance"]["status"]
    overall=health_policy(spot,b["status"],k["status"],o["status"],l["status"])
    analytics_providers=[x["analytics_provider"] for x in latest.values() if isinstance(x,dict) and x.get("analytics_provider")]
    analytics_metrics=sorted({metric for x in latest.values() if isinstance(x,dict) for metric in x.get("analytics_available_metrics",[])})
    analytics_freshness="LIVE_USABLE" if analytics_providers and all(x.get("analytics_freshness")=="LIVE_USABLE" for x in latest.values() if isinstance(x,dict) and x.get("analytics_provider")) else "RECENT_CONTEXT"
    analytics={"schema_version":VERSION,"generated_at_utc":iso(now),"raw_is_not_derived":True,"spot_taker_flow_label":"BINANCE_SPOT_TAKER_FLOW_PROXY","kraken_cvd_label":"KRAKEN_FUTURES_CVD_NATIVE","analytics_provider":analytics_providers,"analytics_freshness":analytics_freshness,"analytics_available_metrics":analytics_metrics,"latest":latest,"evidence":evidence,"options":o.get("analytics"),"overall_data_plane_status":overall,"upstream_provider_health":derivatives["provider_status"],"errors":analytics_errors}
    for path,payload in (("derivatives/manifest.json",derivatives),("options/manifest.json",options),("liquidity/manifest.json",liquidity),("analytics/manifest.json",analytics)): atomic_json(Path(path),payload)
    print("BINANCE_USDM_STATUS="+b["status"]); print("BINANCE_USDM_ERROR="+str(b.get("error") or "")); print("KRAKEN_FUTURES_STATUS="+k["status"]); print("KRAKEN_FUTURES_ERROR="+str(k.get("error") or "")); print("DERIBIT_STATUS="+o["status"]); print("DERIBIT_ERROR="+str(o.get("error") or "")); print("LIQUIDITY_STATUS="+l["status"]); print("LIQUIDITY_ERROR="+str(l.get("error") or ""))
    print("ANALYTICS_PROVIDER="+",".join(analytics_providers)); print("ANALYTICS_FRESHNESS="+analytics_freshness); print("ANALYTICS_AVAILABLE_METRICS="+",".join(analytics_metrics))
    print("DERIVATIVES_STATUS="+("PASS" if k["status"]==dp["status"]=="PASS" else "DEGRADED")); print("OPTIONS_STATUS="+o["status"]); print("OVERALL_DATA_PLANE_STATUS="+analytics["overall_data_plane_status"])
    return {"derivatives":derivatives,"options":options,"liquidity":liquidity,"analytics":analytics}
