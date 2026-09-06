import json
import tempfile
import unittest
from pathlib import Path
from tools.deep_history import kraken_spot_ohlcvt_backfill as backfill

TARGET=1782172800000
AUG15=1786752000000

def candidate(ts, step, volume="10", trades=5):
    return [ts,"100","110","90","105",volume,trades,ts+step-1]

def write_warm(root, interval, rows):
    path=Path(root)/"history"/"kraken"/"ETHUSD"/interval/"fixture.json"; path.parent.mkdir(parents=True,exist_ok=True)
    compat=[[r[0],r[1],r[2],r[3],r[4],r[5],r[7]] for r in rows]
    native=[[r[0],r[1],r[2],r[3],r[4],r[4],r[5],r[6],r[7]] for r in rows]
    path.write_text(json.dumps({"records":compat,"provider_native_records":native}))
    return path

class R13Tests(unittest.TestCase):
    def test_exact_warm_row_repaired(self):
        payload=json.loads(Path("history/kraken/ETHUSD/1d/2026.json").read_text())
        core=next(r for r in payload["records"] if r[0]==TARGET); native=next(r for r in payload["provider_native_records"] if r[0]==TARGET)
        self.assertEqual([TARGET,"1726.12","1734.46","1633.10","1665.12","26130.92616972",1782259199999],core)
        self.assertEqual([TARGET,"1726.12","1734.46","1633.10","1665.12","1671.12","26130.92616972",16902,1782259199999],native)

    def test_full_bucket_eligibility_is_coverage_based(self):
        day=86_400_000; cutoff=AUG15+11*3_600_000
        self.assertEqual((True,"FULL_SOURCE_COVERAGE"),backfill._warm_overlap_eligibility(candidate(AUG15-day,day),"1d",cutoff))
        self.assertEqual((False,"PARTIAL_SOURCE_COVERAGE"),backfill._warm_overlap_eligibility(candidate(AUG15,day),"1d",cutoff))
        five=300_000
        self.assertEqual((True,"FULL_SOURCE_COVERAGE"),backfill._warm_overlap_eligibility(candidate(cutoff-five,five),"5m",cutoff))
        self.assertEqual((False,"PARTIAL_SOURCE_COVERAGE"),backfill._warm_overlap_eligibility(candidate(cutoff,five),"5m",cutoff))

    def test_partial_buckets_skipped_and_full_conflict_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); day=86_400_000; cutoff=3*day+11*3_600_000
            daily=[candidate(i*day,day) for i in range(4)]; five=300_000; m5=[candidate(cutoff-3*five+i*five,five) for i in range(4)]
            write_warm(root,"1d",daily); write_warm(root,"5m",m5)
            result=backfill.verify_warm_overlap_records({"1d":daily,"5m":m5},root,coverage_end_ms=cutoff)
            self.assertEqual(3,result["overlaps"]["1d"]); self.assertEqual(1,result["partial_buckets_skipped"]["1d"])
            self.assertEqual(3,result["overlaps"]["5m"]); self.assertEqual(1,result["partial_buckets_skipped"]["5m"])
            p=root/"history/kraken/ETHUSD/1d/fixture.json"; payload=json.loads(p.read_text()); payload["records"][0][5]="999"; p.write_text(json.dumps(payload))
            with self.assertRaisesRegex(RuntimeError,"POSTTRADE_PRODUCTION_WARM_OVERLAP_CONFLICT"):
                backfill.verify_warm_overlap_records({"1d":daily,"5m":m5},root,coverage_end_ms=cutoff)

if __name__=="__main__": unittest.main()
