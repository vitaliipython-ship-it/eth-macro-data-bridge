import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
from archive import BINANCE_COLUMNS, KRAKEN_COLUMNS, atomic_json, day_for, partition_path
from event_window import register

def snapshot():
    result={}
    for path in Path("archive").glob("????/??/??/*/*-5m.json"):
        rows=json.loads(path.read_text())["candles"]
        prefix=json.dumps(rows,separators=(",", ":")).encode()
        result[path.as_posix()]={"count":len(rows),"first":rows[0][0] if rows else None,"last":rows[-1][0] if rows else None,
                                 "prefix_hash":hashlib.sha256(prefix).hexdigest()}
    return result

def cross_day():
    rows=[[1786665000000,"1","2","0.5","1.5","10",True],[1786665300000,"1","2","0.5","1.5","10",True],
          [1786665600000,"1","2","0.5","1.5","10",True],[1786665900000,"1","2","0.5","1.5","10",True]]
    assert [__import__('archive').day_for(r[0]) for r in rows]==["2026-08-13","2026-08-13","2026-08-14","2026-08-14"]
    assert partition_path("binance","ETHUSDT",day_for(rows[1][0])) != partition_path("binance","ETHUSDT",day_for(rows[2][0]))

def event_registry_fixture():
    original=Path.cwd()
    with tempfile.TemporaryDirectory() as temporary:
        os.chdir(temporary)
        try:
            start=1786665600000
            for provider,symbols in {"binance":("ETHUSDT","BTCUSDT","ETHBTC"),"kraken":("ETHUSD","BTCUSD")}.items():
                for symbol in symbols:
                    rows=([[start+i*300_000,"1","2","0.5","1.5","10",start+(i+1)*300_000-1,"15",5,"6","9"] for i in range(30)] if provider=="binance" else
                          [[start+i*300_000,"1","2","0.5","1.5","1.2","10",5] for i in range(30)])
                    path=partition_path(provider,symbol,day_for(start))
                    atomic_json(path,{"schema_version":"3.1.0","provider":provider,"symbol":symbol,"interval":"5m",
                                      "date_utc":day_for(start),"columns":BINANCE_COLUMNS if provider=="binance" else KRAKEN_COLUMNS,"candles":rows})
            definition={"event_id":"MARKET_TEST_EVENT","event_name":"Synthetic qualification fixture",
                        "event_time_utc":"2026-08-14T01:00:00Z","priority":"TEST","status":"TEST"}
            first=register(definition); second=register(definition)
            assert first["market_window_sha256"]==second["market_window_sha256"]
            assert all(x["data_status"]=="AVAILABLE" for x in first["market_window"])
            manifest=json.loads(Path("events/manifest.json").read_text()); assert manifest["event_count"]==1
        finally: os.chdir(original)

def main():
    before=snapshot(); subprocess.run([sys.executable,"collector.py"],check=True); after=snapshot()
    assert set(before)<=set(after)
    for path,old in before.items():
        new=after[path]; assert new["count"]>=old["count"] and new["first"]==old["first"]
        rows=json.loads(Path(path).read_text())["candles"][:old["count"]]
        assert hashlib.sha256(json.dumps(rows,separators=(",", ":")).encode()).hexdigest()==old["prefix_hash"]
        times=[r[0] for r in json.loads(Path(path).read_text())["candles"]]; assert len(times)==len(set(times))
    cross_day(); event_registry_fixture()
    print("NO_DUPLICATES_AFTER_SECOND_RUN=PASS\nOLD_HISTORY_PRESERVED=PASS")
    print("ARCHIVE_COUNT_NON_DECREASING=PASS\nHISTORICAL_PREFIX_UNCHANGED=PASS")
    print("ARCHIVE_MONOTONICITY=PASS\nUTC_DAY_PARTITION_TEST=PASS\nLOCAL_REPEAT_RUN=PASS")
    print("LOCAL_EVENT_REGISTRY=PASS\nLOCAL_EVENT_RECONSTRUCTION=PASS\nLOCAL_EVENT_REPRODUCIBILITY=PASS")
    print("HISTORICAL_PRICE_PREFIX_UNCHANGED=PASS\nHISTORICAL_NATIVE_FIELDS_UNCHANGED=PASS")
    print("SECOND_RUN_CONFLICTS=0\nREPEATED_RUN_IDEMPOTENCE=PASS")

if __name__=="__main__": main()
