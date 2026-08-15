import json
from decimal import Decimal
from pathlib import Path

MS={"5m":300000,"15m":900000,"1h":3600000,"4h":14400000,"1d":86400000,"1w":604800000}
def main():
    manifest=json.loads(Path("history/manifest.json").read_text()); assert manifest["schema_version"]=="1.0.0"
    assert len(manifest["series"])==30
    for item in manifest["series"]:
        root=Path("history")/item["provider"]/item["symbol"]/item["interval"]
        paths=sorted(root.rglob("*.json")); assert len(paths)==item["partition_count"]
        rows=[]
        for path in paths:
            payload=json.loads(path.read_text()); assert payload["provider"]==item["provider"] and payload["closed_only"] is True
            rows.extend(payload["records"])
        ts=[r[0] for r in rows]; assert ts==sorted(ts) and len(ts)==len(set(ts)) and len(rows)==item["row_count"]
        for r in rows:
            o,h,l,c=map(Decimal,r[1:5]); assert h>=max(o,l,c) and l<=min(o,h,c) and Decimal(str(r[5]))>=0
            assert r[0]%min(MS[item["interval"]],86400000)==0 and r[6]>=r[0]
    conflicts=0; overlaps=0
    for archive_path in Path("archive").rglob("binance/*-5m.json"):
        a=json.loads(archive_path.read_text()); symbol=a["symbol"]
        for row in a["candles"]:
            dt=__import__("datetime").datetime.fromtimestamp(row[0]/1000,__import__("datetime").timezone.utc)
            hp=Path("history/binance")/symbol/"5m"/f"{dt:%Y/%m/%d}.json"
            if hp.exists():
                match={x[0]:x for x in json.loads(hp.read_text())["records"]}.get(row[0])
                if match: overlaps+=1; conflicts+=match!=row
    assert overlaps and conflicts==0
    print("BACKFILL_VALIDATION=PASS\nMANIFEST_VALIDATION=PASS\nNO_DUPLICATES=PASS\nDUPLICATE_TIMESTAMPS=0")
    print("BACKFILL_LIVE_OVERLAP=PASS\nCONFLICT_COUNT=0\nNO_ARCHIVE_CONFLICT=PASS\nSCHEMA_COMPATIBILITY=PASS")
if __name__=="__main__":main()
