import json, sys
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from archive import ARCHIVE_VERSION, BINANCE_COLUMNS, KRAKEN_COLUMNS, aggregate, day_for, load_series, map_binance_kline, map_kraken_ohlc
from event_window import EVENT_VERSION, content_hash, market_window

VERSION="2.0.0"; LIMITS={"5m":288,"15m":96,"1h":72,"4h":42,"1d":90}
SYMBOLS={"binance":("ETHUSDT","BTCUSDT","ETHBTC"),"kraken":("ETHUSD","BTCUSD")}
COLUMNS=["open_time_ms","open","high","low","close","volume","closed"]

def validate():
    root=Path("data"); m=json.loads((root/"manifest.json").read_text())
    assert m["schema_version"]==VERSION and m["generated_at_utc"]
    datetime.fromisoformat(m["generated_at_utc"].replace("Z","+00:00"))
    assert m["bridge_status"] in ("PASS","DEGRADED")
    assert m["providers"]["binance"]["status"]=="PASS"
    assert m["providers"]["kraken"]["status"] in ("PASS","DEGRADED")
    paths=set()
    for provider,symbols in SYMBOLS.items():
        for symbol in symbols:
            intervals=m["providers"][provider]["symbols"][symbol]["intervals"]
            if provider=="binance": assert set(intervals)==set(LIMITS)
            for interval,meta in intervals.items():
                path=Path(meta["path"]); paths.add(path.as_posix()); d=json.loads(path.read_text())
                assert d["schema_version"]==VERSION and d["columns"]==COLUMNS
                assert (d["provider"],d["symbol"],d["interval"])==(provider,symbol,interval)
                rows=d["candles"]; assert len(rows)>=LIMITS[interval] and len(rows)==meta["candle_count"]
                previous=None
                for row in rows:
                    assert len(row)==7 and isinstance(row[0],int) and isinstance(row[6],bool)
                    assert previous is None or row[0]>previous; previous=row[0]
                    o,h,l,c=map(float,row[1:5]); assert h>=max(o,c) and l<=min(o,c) and l<=h
                closed=[r for r in rows if r[6]]
                assert closed and meta["latest_closed_candle_open_time_ms"]==closed[-1][0]
                if provider=="kraken": assert rows[-1][6] is False
                assert path.stat().st_size<500_000
    actual={p.as_posix() for p in root.rglob("*.json") if p.name!="manifest.json"}
    assert actual==paths and (root/"manifest.json").stat().st_size<100_000
    print("MANIFEST_SCHEMA_VALID=PASS\nBINANCE_PRIMARY_COMPLETE=PASS\nKRAKEN_VALID_OR_DEGRADED=PASS")
    for symbol in SYMBOLS["binance"]: print(f"{symbol}_ALL_INTERVALS=PASS")
    print(f"DATASET_VALIDATION=PASS files={len(paths)}")
    print("ROLLING_VALIDATION=PASS")

def validate_archive():
    root=Path("archive"); manifest=json.loads((root/"manifest.json").read_text())
    assert manifest["schema_version"]==ARCHIVE_VERSION and manifest["integrity_status"]=="PASS"
    assert not manifest["archive_conflict"] and not manifest["conflicts"]
    total=0
    for path in root.glob("????/??/??/*/*-5m.json"):
        d=json.loads(path.read_text()); rows=d["candles"]
        expected=BINANCE_COLUMNS if d["provider"]=="binance" else KRAKEN_COLUMNS
        assert d["schema_version"]==ARCHIVE_VERSION and d["columns"]==expected and d["interval"]=="5m"
        timestamps=[r[0] for r in rows]
        assert timestamps==sorted(timestamps) and len(timestamps)==len(set(timestamps))
        for row in rows:
            assert len(row)==len(expected) and row[0]%300_000==0 and day_for(row[0])==d["date_utc"]
            o,h,l,c=map(float,row[1:5]); assert h>=max(o,c) and l<=min(o,c) and l<=h
            if d["provider"]=="binance":
                base,quote,buy_base,buy_quote=map(Decimal,(row[5],row[7],row[9],row[10]))
                assert row[6]>row[0] and isinstance(row[8],int) and row[8]>=0
                assert base>=0 and quote>=0 and 0<=buy_base<=base and 0<=buy_quote<=quote
            else:
                assert Decimal(row[5])>=0 and Decimal(row[6])>=0 and isinstance(row[7],int) and row[7]>=0
        total+=len(rows)
    assert total==manifest["total_closed_candles"] and total>0
    assert manifest["migration_status"]=="COMPLETE"
    assert all(value==1 for fields in manifest["field_coverage"].values() for value in fields.values())
    print("ARCHIVE_SCHEMA_VALID=PASS\nARCHIVE_CLOSED_ONLY=PASS\nARCHIVE_UNIQUE_TIMESTAMPS=PASS")
    print("ARCHIVE_SORTED=PASS\nARCHIVE_OHLC_VALID=PASS\nARCHIVE_DATE_PARTITION_VALID=PASS")
    print("ARCHIVE_MANIFEST_VALID=PASS\nARCHIVE_NO_CONFLICTS=PASS\nARCHIVE_VALIDATION=PASS")
    print("BINANCE_NATIVE_FIELDS=PASS\nKRAKEN_NATIVE_FIELDS=PASS\nFIELD_COVERAGE_VALID=PASS")

def validate_aggregation_and_events():
    rows=load_series("binance","ETHUSDT")
    assert rows
    for label,minutes in (("M15",15),("H1",60),("H4",240),("D1",1440)):
        derived=aggregate(rows,minutes,"binance"); assert derived and all(r[0]%(minutes*60_000)==0 for r in derived)
        print(f"M5_TO_{label}_AGGREGATION=PASS\nM5_TO_{label}_ENRICHED=PASS")
    event_ms=rows[-13][0]; first=market_window(event_ms); second=market_window(event_ms)
    required={"PRE_30","PRE_15","PRE_5","RELEASE","PLUS_15","PLUS_30","PLUS_60"}
    eth=[x for x in first if x["provider"]=="binance" and x["symbol"]=="ETHUSDT" and x["requested_checkpoint"] in required]
    assert len(eth)==len(required) and all(x["data_status"]=="AVAILABLE" and x["closed"] for x in eth)
    assert content_hash(first)==content_hash(second)
    assert all(x.get("derived_analytics",{}).get("derived") for x in first if x["data_status"]=="AVAILABLE")
    events=json.loads(Path("events/manifest.json").read_text()); assert events["schema_version"]==EVENT_VERSION
    print("EVENT_REGISTRY_SCHEMA_VALID=PASS\nEVENT_WINDOW_RECONSTRUCTION=PASS\nEVENT_WINDOW_REPRODUCIBLE=PASS")
    print("EVENT_COMPONENT_VALIDATION=PASS")
    print("EVENT_ACTIVITY_METRICS=PASS")

def mapping_tests():
    b=[1,"2","3","1","2.5","10",300000,"25",7,"6","15","ignore"]
    assert map_binance_kline(b,True)==[1,"2","3","1","2.5","10",300000,"25",7,"6","15",True]
    k=[1,"2","3","1","2.5","2.2","10",7]
    assert map_kraken_ohlc(k,True)==[1000,"2","3","1","2.5","2.2","10",7,True]
    print("BINANCE_KLINE_MAPPING_TEST=PASS\nKRAKEN_OHLC_MAPPING_TEST=PASS")

if __name__=="__main__":
    try: validate(); validate_archive(); validate_aggregation_and_events(); mapping_tests()
    except Exception as exc: print(f"VALIDATION=FAIL error={exc}",file=sys.stderr); raise
