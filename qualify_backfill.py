import hashlib,subprocess,sys,time
from pathlib import Path

ROOTS=("history","derivatives/archive","derivatives/history-manifest.json","derivatives/deribit-history-manifest.json","options/archive","options/history-manifest.json")
def digest():
    out={}
    for root in ROOTS:
        p=Path(root); paths=[p] if p.is_file() else list(p.rglob("*.json"))
        for path in paths:out[path.as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return out
def main():
    cutoff=int(time.time()//3600*3600*1000)
    command=[sys.executable,"backfill.py","--as-of-ms",str(cutoff)]
    subprocess.run(command,check=True); first=digest(); subprocess.run(command,check=True); second=digest()
    changed=sum(first.get(k)!=v for k,v in second.items())+sum(k not in second for k in first)
    assert changed==0
    subprocess.run([sys.executable,"validate_history.py"],check=True)
    print("SAME_INPUT_CONTENT_DIFF=0\nDUPLICATE_EXPANSION=0\nCONFLICT_COUNT=0\nBACKFILL_IDEMPOTENT=PASS")
if __name__=="__main__":main()
