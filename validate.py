import json, sys
from datetime import datetime
from pathlib import Path

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

if __name__=="__main__":
    try: validate()
    except Exception as exc: print(f"VALIDATION=FAIL error={exc}",file=sys.stderr); raise
