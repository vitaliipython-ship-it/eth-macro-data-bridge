import argparse,json,time
from pathlib import Path
from archive import atomic_json
from collector import get

def main():
    p=argparse.ArgumentParser(); p.add_argument("--duration-minutes",type=int,required=True); p.add_argument("--sample-interval-seconds",type=int,required=True); p.add_argument("--symbols",default="ETHUSDT,BTCUSDT"); p.add_argument("--event-id",required=True); a=p.parse_args()
    if not 1<=a.duration_minutes<=90 or a.sample_interval_seconds<60: raise ValueError("burst caps violated")
    samples=[]; end=time.time()+a.duration_minutes*60
    while time.time()<end:
        timestamp=int(time.time()*1000); entry={"timestamp_ms":timestamp,"symbols":{}}
        for symbol in a.symbols.split(",")[:4]:
            entry["symbols"][symbol]={"spot_depth":get(f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"),
              "perp_depth":get(f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=20"),
              "perp_premium":get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"),
              "perp_open_interest":get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}")}
        samples.append(entry); time.sleep(a.sample_interval_seconds)
    path=Path("event-bursts")/a.event_id/f"{samples[0]['timestamp_ms']}.json"; atomic_json(path,{"schema_version":"1.0.0","event_id":a.event_id,"sample_interval_seconds":a.sample_interval_seconds,"samples":samples})
    print("EVENT_BURST_PATH="+path.as_posix())
if __name__=="__main__":main()
