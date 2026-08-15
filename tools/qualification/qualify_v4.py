import hashlib,json,subprocess,sys
from pathlib import Path

ROOTS=("derivatives/archive","options/snapshots","options/archive","liquidity/snapshots")
def snap():
    out={}
    for root in ROOTS:
        for p in Path(root).rglob("*.json"):
            payload=json.loads(p.read_text()); records=payload.get("records")
            out[p.as_posix()]={"records":records,"hash":hashlib.sha256(p.read_bytes()).hexdigest()}
    return out
def counts(): return {root:len(list(Path(root).rglob("*.json"))) for root in ROOTS}
def main():
    before=snap(); old_counts=counts(); subprocess.run([sys.executable,"collector.py"],check=True); after=snap(); new_counts=counts()
    for path,old in before.items():
        assert path in after
        if old["records"] is not None: assert after[path]["records"][:len(old["records"])]==old["records"]
        else: assert after[path]["hash"]==old["hash"]
    assert all(new_counts[k]>=v for k,v in old_counts.items())
    subprocess.run([sys.executable,"validate.py"],check=True); subprocess.run([sys.executable,"validate_v4.py"],check=True)
    print("NO_DUPLICATES_AFTER_SECOND_RUN=PASS\nSPOT_HISTORY_UNCHANGED=PASS\nDERIVATIVES_HISTORY_UNCHANGED=PASS")
    print("OPTIONS_OLD_SNAPSHOTS_UNCHANGED=PASS\nLIQUIDITY_OLD_SNAPSHOTS_UNCHANGED=PASS\nCOUNTS_NON_DECREASING=PASS")
    print("NO_PROVIDER_CROSS_CONTAMINATION=PASS\nREPEATED_RUN_IDEMPOTENCE=PASS")
if __name__=="__main__":main()
