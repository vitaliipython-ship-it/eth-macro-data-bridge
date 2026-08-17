import json
from decimal import Decimal
from pathlib import Path

MS={"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000,"1w":604800000}
KRAKEN_NATIVE_COLUMNS=["open_time_ms","open","high","low","close","vwap","volume","trade_count","close_time_ms"]


def kraken_compact(row):
    return [row[0],row[1],row[2],row[3],row[4],row[6],row[8]]


def main():
    manifest=json.loads(Path("history/manifest.json").read_text()); assert manifest["schema_version"]=="1.0.0"
    assert len(manifest["series"])==30
    d9_generated=manifest.get("d9_warm_status") is not None
    for item in manifest["series"]:
        root=Path("history")/item["provider"]/item["symbol"]/item["interval"]
        paths=sorted(root.rglob("*.json")); assert len(paths)==item["partition_count"]
        rows=[]; native_rows=[]
        for path in paths:
            payload=json.loads(path.read_text()); assert payload["provider"]==item["provider"] and payload["closed_only"] is True
            rows.extend(payload["records"])
            if payload.get("provider_native_records") is not None:
                assert item["provider"]=="kraken"
                assert payload.get("provider_native_columns")==KRAKEN_NATIVE_COLUMNS
                native=payload["provider_native_records"]; nts=[r[0] for r in native]
                assert nts==sorted(nts) and len(nts)==len(set(nts))
                compat={r[0]:r for r in payload["records"]}
                for row in native:
                    if row[0] in compat: assert kraken_compact(row)==compat[row[0]]
                native_rows.extend(native)
        ts=[r[0] for r in rows]; assert ts==sorted(ts) and len(ts)==len(set(ts)) and len(rows)==item["row_count"]
        for r in rows:
            o,h,l,c=map(Decimal,r[1:5]); assert h>=max(o,l,c) and l<=min(o,h,c) and Decimal(str(r[5]))>=0
            assert r[0]%min(MS[item["interval"]],86400000)==0 and r[6]>=r[0]
        if d9_generated and item["provider"]=="kraken":
            assert item.get("provider_native_enrichment_rows",0)==len(native_rows)
            assert native_rows, f"missing Kraken provider-native enrichment {item['symbol']} {item['interval']}"
    conflicts=0; overlaps=0; provider_overlaps={"binance":0,"kraken":0}
    for archive_path in Path("archive").glob("????/??/??/*/*-5m.json"):
        a=json.loads(archive_path.read_text()); symbol=a["symbol"]; provider=a["provider"]
        for row in a["candles"]:
            dt=__import__("datetime").datetime.fromtimestamp(row[0]/1000,__import__("datetime").timezone.utc)
            hp=Path("history")/provider/symbol/"5m"/f"{dt:%Y/%m/%d}.json"
            if hp.exists():
                payload=json.loads(hp.read_text()); match={x[0]:x for x in payload["records"]}.get(row[0])
                if match:
                    overlaps+=1; provider_overlaps[provider]+=1
                    expected=row if provider=="binance" else [row[0],row[1],row[2],row[3],row[4],row[6],row[0]+MS["5m"]-1]
                    conflicts+=match!=expected
    assert overlaps and conflicts==0
    if d9_generated:
        assert manifest["d9_warm_status"]=="DUAL_WRITE_CANDIDATE_NOT_ACTIVE"
        assert manifest["canonical_spot_warm_root"]=="history"
        assert provider_overlaps["binance"] and provider_overlaps["kraken"]
        consistency=json.loads(Path("history/consistency-latest.json").read_text())
        assert consistency["schema_version"]=="spot-history-consistency/1.0.0"
        assert consistency["status_counts"]["CONFLICT"]==0
        assert consistency["status_counts"]["EQUIVALENT"]>0
        print("D9_SPOT_WARM_VALIDATION=PASS")
        print("D9_KRAKEN_NATIVE_ENRICHMENT=PASS")
        print("D9_SPOT_CONSISTENCY=PASS")
    print("BACKFILL_VALIDATION=PASS\nMANIFEST_VALIDATION=PASS\nNO_DUPLICATES=PASS\nDUPLICATE_TIMESTAMPS=0")
    print("BACKFILL_LIVE_OVERLAP=PASS\nCONFLICT_COUNT=0\nNO_ARCHIVE_CONFLICT=PASS\nSCHEMA_COMPATIBILITY=PASS")


if __name__=="__main__":main()
