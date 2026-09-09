import subprocess, tempfile, unittest
from pathlib import Path
from pr_effective_integration_requalification import (
    RequalificationError, build_local_synthetic, checkout_synthetic,
    require_final_main_unchanged, validate_dispatch_inputs,
    validate_pr_metadata, verify_existing_binding,
)
ROOT=Path(__file__).resolve().parents[2]
WORKFLOW=ROOT/'.github/workflows/qualify-pr-effective-integration.yml'
REPO='vitaliipython-ship-it/eth-macro-data-bridge'; HEAD='2'*40; BASE='1'*40

class LateBoundRequalificationTests(unittest.TestCase):
    def git(self,r,*a):
        return subprocess.run(['git','-C',str(r),*a],check=True,capture_output=True,text=True).stdout.strip()
    def repo(self):
        t=tempfile.TemporaryDirectory(); r=Path(t.name); self.git(r,'init','-q'); self.git(r,'config','user.name','q'); self.git(r,'config','user.email','q@example.invalid')
        (r/'seed').write_text('seed\n'); self.git(r,'add','seed'); self.git(r,'commit','-q','-m','base'); b=self.git(r,'rev-parse','HEAD'); return t,r,b
    def pair(self):
        t,r,b=self.repo(); (r/'main').write_text('main\n'); self.git(r,'add','main'); self.git(r,'commit','-q','-m','main'); m=self.git(r,'rev-parse','HEAD')
        self.git(r,'checkout','-q','--detach',b); (r/'head').write_text('head\n'); self.git(r,'add','head'); self.git(r,'commit','-q','-m','head'); h=self.git(r,'rev-parse','HEAD'); return t,r,b,m,h
    def meta(self,**kw):
        d={'number':873,'state':'open','merged':False,'head':{'sha':HEAD,'ref':'agent/x','repo':{'full_name':REPO}},'base':{'sha':BASE,'ref':'main','repo':{'full_name':REPO}}}
        for k,v in kw.items():
            if k.startswith('head_'): d['head'][k[5:]]=v
            elif k.startswith('base_'): d['base'][k[5:]]=v
            else: d[k]=v
        return d
    def test_01_dispatch_requires_pr_number_and_exact_head_sha(self):
        self.assertEqual(validate_dispatch_inputs('873',HEAD),(873,HEAD)); s=WORKFLOW.read_text(); self.assertIn('workflow_dispatch:',s); self.assertIn('pr_number:',s); self.assertIn('expected_pr_head_sha:',s); self.assertGreaterEqual(s.count('required: true'),2)
    def test_02_closed_pr_rejected(self):
        with self.assertRaises(RequalificationError): validate_pr_metadata(self.meta(state='closed'),repository=REPO,expected_pr_head_sha=HEAD)
    def test_03_merged_pr_rejected(self):
        for merged in (True, None):
            with self.subTest(merged=merged):
                with self.assertRaises(RequalificationError): validate_pr_metadata(self.meta(merged=merged),repository=REPO,expected_pr_head_sha=HEAD)
    def test_04_wrong_expected_head_rejected(self):
        with self.assertRaises(RequalificationError): validate_pr_metadata(self.meta(),repository=REPO,expected_pr_head_sha='3'*40)
    def test_05_non_main_base_rejected(self):
        with self.assertRaises(RequalificationError): validate_pr_metadata(self.meta(base_ref='dev'),repository=REPO,expected_pr_head_sha=HEAD)
    def test_06_fork_pr_rejected(self):
        with self.assertRaises(RequalificationError): validate_pr_metadata(self.meta(head_repo={'full_name':'x/y'}),repository=REPO,expected_pr_head_sha=HEAD)
    def test_07_clean_pair_produces_local_two_parent_synthetic(self):
        t,r,b,m,h=self.pair()
        with t: p=build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h); self.assertEqual(len(self.git(r,'show','-s','--format=%P',p['PR_EFFECTIVE_INTEGRATION_SHA']).split()),2)
    def test_08_parent1_is_exact_effective_base(self):
        t,r,b,m,h=self.pair()
        with t: self.assertEqual(build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h)['SYNTHETIC_PARENT_1_SHA'],m)
    def test_09_parent2_is_exact_pr_head(self):
        t,r,b,m,h=self.pair()
        with t: self.assertEqual(build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h)['SYNTHETIC_PARENT_2_SHA'],h)
    def test_10_merge_conflict_fails_closed(self):
        t,r,b=self.repo()
        with t:
            (r/'seed').write_text('main\n'); self.git(r,'add','seed'); self.git(r,'commit','-q','-m','main'); m=self.git(r,'rev-parse','HEAD'); self.git(r,'checkout','-q','--detach',b); (r/'seed').write_text('head\n'); self.git(r,'add','seed'); self.git(r,'commit','-q','-m','head'); h=self.git(r,'rev-parse','HEAD')
            with self.assertRaisesRegex(RequalificationError,'LATE_BOUND_PR_EFFECTIVE_INTEGRATION_CONFLICT'): build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h)
    def test_11_existing_binding_accepts_correct_synthetic(self):
        t,r,b,m,h=self.pair()
        with t:
            s=build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h); p=verify_existing_binding(repo=r,event_base_sha=b,expected_pr_head_sha=h,synthetic_sha=s['PR_EFFECTIVE_INTEGRATION_SHA'],current_main_sha=m,current_pr_head_sha=h); self.assertEqual(p['PR_EFFECTIVE_INTEGRATION_BINDING'],'PASS')
    def test_12_existing_binding_rejects_wrong_head(self):
        t,r,b,m,h=self.pair()
        with t:
            s=build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h)
            with self.assertRaises(RequalificationError): verify_existing_binding(repo=r,event_base_sha=b,expected_pr_head_sha=b,synthetic_sha=s['PR_EFFECTIVE_INTEGRATION_SHA'],current_main_sha=m,current_pr_head_sha=b)
    def test_13_qualification_checkout_is_exact_synthetic_sha_and_tree(self):
        t,r,b,m,h=self.pair()
        with t:
            s=build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h); q=checkout_synthetic(r,s['PR_EFFECTIVE_INTEGRATION_SHA'],s['PR_EFFECTIVE_INTEGRATION_TREE']); self.assertEqual(q['ACTUAL_CHECKOUT_SHA_MATCH'],'PASS'); self.assertEqual(q['ACTUAL_CHECKOUT_TREE_MATCH'],'PASS')
    def test_14_final_main_unchanged_permits_pass(self): require_final_main_unchanged(qualified_base_sha=HEAD,final_main_sha=HEAD)
    def test_15_final_main_drift_fails_owner_readiness(self):
        with self.assertRaises(RequalificationError): require_final_main_unchanged(qualified_base_sha=BASE,final_main_sha=HEAD)
    def test_16_retry_requires_no_ref_or_pr_mutation(self):
        t,r,b,m,h=self.pair()
        with t:
            before=self.git(r,'for-each-ref','--format=%(refname):%(objectname)','refs/heads'); build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h); build_local_synthetic(r,effective_base_sha=m,pr_head_sha=h); self.assertEqual(before,self.git(r,'for-each-ref','--format=%(refname):%(objectname)','refs/heads'))
    def test_17_workflow_has_read_only_permissions(self):
        s=WORKFLOW.read_text(); self.assertIn('permissions:\n  contents: read\n  pull-requests: read',s); [self.assertNotIn(x,s) for x in ('contents: write','pull-requests: write','issues: write','actions: write')]
    def test_18_workflow_has_no_remote_ref_publication_path(self):
        s=WORKFLOW.read_text(); [self.assertNotIn(x,s) for x in ('git push','gh pr ','gh issue ','refs/heads/qualification','git tag')]
    def test_19_workflow_evidence_path_outside_repository_root(self):
        s=WORKFLOW.read_text()
        self.assertNotIn('EVIDENCE_PATH: ${{ runner.temp }}/pr-effective-integration-qualification.json',s)
        self.assertNotIn('EVIDENCE_PATH: pr-effective-integration-qualification.json',s)
        self.assertIn('$RUNNER_TEMP/pr-effective-integration-qualification.json',s)
        self.assertIn('EVIDENCE_PATH=$EVIDENCE_PATH',s)
        self.assertIn('$GITHUB_ENV',s)
    def test_20_workflow_evidence_postprocessor_reuses_env_path(self):
        s=WORKFLOW.read_text(); self.assertIn('import json, os, re',s); self.assertIn('Path(os.environ["EVIDENCE_PATH"])',s); self.assertNotIn("Path('pr-effective-integration-qualification.json')",s); self.assertGreaterEqual(s.count('--evidence-path "$EVIDENCE_PATH"'),2); self.assertIn('if [[ -f "$EVIDENCE_PATH" ]]',s)
if __name__=='__main__': unittest.main()
