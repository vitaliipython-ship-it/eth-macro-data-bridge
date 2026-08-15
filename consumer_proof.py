import json
from pathlib import Path

def read(path): return json.loads(Path(path).read_text())
def main():
    c=read("bridge-contract.json"); assert c["bridge_id"]=="eth-macro-data-bridge"; print("CONTRACT_READ=PASS")
    current=read(c["canonical_paths"]["current_spot_manifest"]); assert current["providers"]["binance"]["status"]=="PASS"; print("CURRENT_SPOT_READ=PASS")
    history=read(c["canonical_paths"]["spot_history_manifest"]); assert history["series"]; print("HISTORY_READ=PASS")
    by={(x["provider"],x["symbol"],x["interval"]):x for x in history["series"]}
    for symbol in ("ETHUSDT","BTCUSDT","ETHBTC"):
        assert all(("binance",symbol,tf) in by for tf in ("5m","15m","1h","4h","1d","1w")); print(symbol+"_HISTORY_DEPTH=PASS")
    assert all(("kraken",s,"5m") in by for s in ("ETHUSD","BTCUSD")); print("KRAKEN_HISTORY_READ=PASS")
    d=read(c["canonical_paths"]["derivatives_manifest"]); assert d["providers"]["kraken-futures"]["status"]=="PASS"; print("KRAKEN_FUTURES_READ=PASS")
    kh=read(c["canonical_paths"]["kraken_futures_history_manifest"]); assert len(kh["series"])==26 and all(x["historical_backfill"] in ("PASS","PROVIDER_HISTORY_LIMIT") for x in kh["series"])
    assert d["providers"]["deribit-perpetual"]["status"]=="PASS"; print("DERIBIT_PERPETUAL_READ=PASS")
    assert read(c["canonical_paths"]["deribit_perpetual_history_manifest"])["series"]
    o=read(c["canonical_paths"]["options_manifest"]); assert o["providers"]["deribit"]["status"]=="PASS"; print("DERIBIT_OPTIONS_READ=PASS")
    assert read(c["canonical_paths"]["options_history_manifest"])["options_forward_snapshot_archive"]=="PASS"
    l=read(c["canonical_paths"]["liquidity_manifest"]); assert l["collection"]["usable_eth_source"]; print("LIQUIDITY_READ=PASS")
    e=read(c["canonical_paths"]["events_manifest"]); assert "events" in e; print("EVENT_RECONSTRUCTION_READ=PASS")
    disabled=c["disabled_providers"]["binance-usdm"]; assert disabled["current_collection"]=="DISABLED_BY_POLICY" and disabled["existing_archive"]=="FROZEN_HISTORICAL_REFERENCE" and disabled["archive_continuously_accumulated"] is False and disabled["archive_currently_updated"] is False and disabled["signal_vote"]=="EXCLUDED" and disabled["network_calls"]==0 and disabled["affects_health"] is False
    assert d["providers"]["binance-usdm"]["status"]=="DISABLED_BY_POLICY"; print("DISABLED_PROVIDER_SEMANTICS=PASS\nNO_BINANCE_USDM_DEPENDENCY=PASS")
    print("CONSUMER_CONTRACT=PASS\nCONSUMER_PROOF=PASS")
if __name__=="__main__":main()
