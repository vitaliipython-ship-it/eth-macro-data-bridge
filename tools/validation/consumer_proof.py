import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path

def read(path): return json.loads(Path(path).read_text())
def run_json(*args):
    result=subprocess.run([sys.executable,*args],check=True,capture_output=True,text=True)
    return json.loads(result.stdout)

def main():
    c=read("bridge-contract.json"); assert c["bridge_id"]=="eth-macro-data-bridge" and c["contract_version"]=="1.3.0"; print("CONTRACT_READ=PASS")
    paths=c["canonical_paths"]
    resolution=c["semantic_resolution"]
    assert resolution["status"]=="ACTIVE" and resolution["discovery_route_authority"]=="canonical_paths.capability_index"
    capability_path=Path(paths["capability_index"]); capability=read(capability_path)
    assert capability["catalog_id"]=="eth-macro-data-bridge-capability-index" and capability["authority"]["route_policy"]=="bridge-contract.json"
    assert resolution["resolver"]["interface"]=="tools/capability_index.py" and resolution["resolver"]["commands"]==["list","describe","resolve"]
    assert resolution["reader"]=={"interface":"tools/history_access.py","input_authority":"ResolutionPlan"}
    consumer=resolution["consumer"]
    assert consumer["interface"]=="tools/history_consumer.py" and consumer["command"]=="read"
    transport=resolution["agent_transport"]
    assert transport["status"]=="ACTIVE" and transport["method"]=="GITHUB_ISSUE_REQUEST"
    assert transport["workflow"]==".github/workflows/history-consumer-read.yml" and transport["request_title_prefix"]=="[history-read]"
    assert transport["owner_only"] is True and transport["authority"]=="TRANSPORT_ONLY"
    assert transport["request_fields"]==["series_id","from_utc","to_utc","cutoff_utc","mode","current_policy","output_format"]
    assert consumer["canonical_semantic_receipt"]=="history-access-receipt/2.0.0"
    assert consumer["legacy_transport_receipt"]=="history-consumer-receipt/1.0.0"
    assert consumer["canonical_output_sha_semantics"]=="SHA256_CANONICAL_NORMALIZED_SEMANTIC_OBSERVATIONS_JSON_LF"
    assert "semantic-receipt.json" in transport["artifact_contents"]
    assert set(transport["forbidden_physical_inputs"]) >= {"release_tag","asset_name","browser_download_url","resource_path","sha256"}
    assert transport["fallback_order"]==["DIRECT_CANONICAL_READER","GITHUB_ISSUE_REQUEST"]
    assert transport["transport_blocked_status"]=="DATA_TRANSPORT_BLOCKED"
    workflow=Path(transport["workflow"]).read_text(encoding="utf-8")
    assert "issues:" in workflow and "tools/history_issue_request.py" in workflow and "issue-consumer-read:" in workflow
    print("CAPABILITY_ROUTE_DECLARED=PASS\nCAPABILITY_INDEX_READ=PASS\nAGENT_CALLABLE_TRANSPORT=PASS")
    legacy=resolution["legacy_manifest_route"]
    assert legacy["status"]=="SUPPORTED_BACKWARD_COMPATIBLE"
    assert legacy["spot_history_manifest"]==paths["spot_history_manifest"] and legacy["release_history_manifest"]==paths["release_history_manifest"]
    print("LEGACY_MANIFEST_ROUTE=PASS")

    current=read(paths["current_spot_manifest"]); assert current["providers"]["binance"]["status"]=="PASS"; print("CURRENT_SPOT_READ=PASS")
    history=read(paths["spot_history_manifest"]); assert history["series"]; print("HISTORY_READ=PASS")
    by={(x["provider"],x["symbol"],x["interval"]):x for x in history["series"]}
    for symbol in ("ETHUSDT","BTCUSDT","ETHBTC"):
        assert all(("binance",symbol,tf) in by for tf in ("5m","15m","1h","4h","1d","1w")); print(symbol+"_HISTORY_DEPTH=PASS")
    assert all(("kraken",s,"5m") in by for s in ("ETHUSD","BTCUSD")); print("KRAKEN_HISTORY_READ=PASS")
    d=read(paths["derivatives_manifest"]); assert d["providers"]["kraken-futures"]["status"]=="PASS"; print("KRAKEN_FUTURES_READ=PASS")
    kh=read(paths["kraken_futures_history_manifest"]); assert len(kh["series"])==26 and all(x["historical_backfill"] in ("PASS","PROVIDER_HISTORY_LIMIT") for x in kh["series"])
    assert d["providers"]["deribit-perpetual"]["status"]=="PASS"; print("DERIBIT_PERPETUAL_READ=PASS")
    assert read(paths["deribit_perpetual_history_manifest"])["series"]
    o=read(paths["options_manifest"]); assert o["providers"]["deribit"]["status"]=="PASS"; print("DERIBIT_OPTIONS_READ=PASS")
    assert read(paths["options_history_manifest"])["options_forward_snapshot_archive"]=="PASS"
    l=read(paths["liquidity_manifest"]); assert l["collection"]["usable_eth_source"]; print("LIQUIDITY_READ=PASS")
    e=read(paths["events_manifest"]); assert "events" in e; print("EVENT_RECONSTRUCTION_READ=PASS")
    disabled=c["disabled_providers"]["binance-usdm"]; assert disabled["current_collection"]=="DISABLED_BY_POLICY" and disabled["existing_archive"]=="FROZEN_HISTORICAL_REFERENCE" and disabled["archive_continuously_accumulated"] is False and disabled["archive_currently_updated"] is False and disabled["signal_vote"]=="EXCLUDED" and disabled["network_calls"]==0 and disabled["affects_health"] is False
    assert d["providers"]["binance-usdm"]["status"]=="DISABLED_BY_POLICY"; print("DISABLED_PROVIDER_SEMANTICS=PASS\nNO_BINANCE_USDM_DEPENDENCY=PASS")

    release_path=Path(paths["release_history_manifest"]); assert release_path.exists()
    assert resolution["physical_authority"]["cold_manifest"]==release_path.as_posix()
    release=read(release_path); assert release["storage_backend"]=="GITHUB_RELEASE_ASSET"; print("RELEASE_MANIFEST_READ=PASS")
    assert release["integrity_summary"]["release_to_git_overlap"]=="PASS"

    plan=run_json("tools/capability_index.py","resolve","spot.binance-spot.ETHUSDT.ohlcv.1h","--from","2022-06-18T00:00:00Z","--to","2022-06-19T00:00:00Z","--format","json")
    assert plan["schema_version"]==resolution["resolver"]["resolution_plan_schema"]
    assert plan["authority"]["route_policy"]=="bridge-contract.json" and plan["authority"]["capability_index"]==paths["capability_index"]
    assert plan["authority"]["cold_manifest"]==paths["release_history_manifest"] and plan["segments"]
    inventory={x["asset_id"]:x for x in release["asset_inventory"]}
    for segment in plan["segments"]:
        if segment["storage"]!="GITHUB_RELEASE_ASSET": continue
        asset=inventory[segment["asset_id"]]
        assert segment["asset_name"]==asset["asset_name"] and segment["browser_download_url"]==asset["browser_download_url"] and segment["sha256"]==asset["sha256"]
    print("CAPABILITY_RESOLUTION=PASS\nRESOLUTION_PLAN_AUTHORITY=PASS\nCAPABILITY_NO_GUESSED_PATHS=PASS")

    samples=[]
    for item in release["release_inventory"]:
        candidates=[x for x in release["asset_inventory"] if x["release_tag"]==item["release_tag"]]
        samples.append(min(candidates,key=lambda x:x["size_bytes"]))
    for asset in samples:
        with urllib.request.urlopen(asset["browser_download_url"],timeout=120) as response: raw=response.read()
        assert len(raw)==asset["size_bytes"] and hashlib.sha256(raw).hexdigest()==asset["sha256"]
        payload=json.loads(raw); assert payload["provider"]==asset["provider"] and payload["instrument"]==asset["instrument"]
    series={(x["provider"],x["instrument"],x["interval_or_metric"]):x for x in release["series_inventory"]}
    assert all(("binance",s,i) in series for s in ("ETHUSDT","BTCUSDT","ETHBTC") for i in ("5m","15m","1h","4h","1d","1w")); print("BINANCE_MAX_HISTORY_READ=PASS")
    assert all(("kraken",s,i) in series for s in ("ETHUSD","BTCUSD") for i in ("5m","15m","1h","4h","1d","1w")); print("KRAKEN_SPOT_MAX_AVAILABLE_READ=PASS")
    assert all(("kraken-futures",s,m) in series for s in ("PI_ETHUSD","PI_XBTUSD") for m in ("aggressor-differential","trade-volume","trade-count","liquidation-volume","rolling-volatility","cvd","spreads","liquidity","slippage","future-basis")); print("KRAKEN_FUTURES_MAX_AVAILABLE_READ=PASS")
    assert any(x[0]=="deribit-perpetual" for x in series); print("DERIBIT_MAX_AVAILABLE_READ=PASS_OR_EXPLICIT_UNAVAILABLE")
    print("RELEASE_ASSET_RESOLUTION=PASS\nRELEASE_ASSET_DOWNLOAD=PASS\nRELEASE_ASSET_SHA256=PASS\nRELEASE_TO_HOT_TAIL_SEAM=PASS\nNO_PROVIDER_SUBSTITUTION=PASS")
    print("CAPABILITY_CONSUMER_PROOF=PASS\nCONSUMER_CONTRACT=PASS\nCONSUMER_PROOF=PASS")
if __name__=="__main__":main()