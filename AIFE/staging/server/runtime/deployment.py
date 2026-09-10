"""F5C C6 exact-Git -> immutable-release primitive; disposable roots only."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence
from uuid import uuid4

PROJECTION_PREFIXES=("AIFE/staging/","src/"); MANIFEST=".aife-release-manifest.json"
class DeploymentError(RuntimeError): pass
class GitIdentityMismatch(DeploymentError): pass
class UnsupportedGitEntry(DeploymentError): pass
class ProjectedPathCollision(DeploymentError): pass
class MaterializedByteMismatch(DeploymentError): pass
class ReleaseIdentityMismatch(DeploymentError): pass
class DeploymentReceiptMismatch(DeploymentError): pass
class ActivationError(DeploymentError): pass

@dataclass(frozen=True,slots=True)
class GitIdentity: head:str; tree:str
@dataclass(frozen=True,slots=True)
class ProjectedEntry:
    source_path:str; projected_path:str; mode:str; blob_oid:str; size:int; source_sha256:str; materialized_sha256:str
    @property
    def byte_identity_match(self)->bool: return self.source_sha256==self.materialized_sha256
@dataclass(frozen=True,slots=True)
class ReleasePlan:
    source_head:str; source_tree:str; release_id:str; release_digest:str; release_manifest_id:str
    entries:tuple[ProjectedEntry,...]; manifest:Mapping[str,object]
@dataclass(frozen=True,slots=True)
class DeploymentResult:
    git_identity:GitIdentity; release:ReleasePlan; release_path:Path; deployment_map_path:Path
    receipt_path:Path; receipt:Mapping[str,object]; predecessor_release_id:str|None

def _git(repo:Path,*args:str,text:bool=True)->str|bytes:
    p=subprocess.run(["git","-C",os.fspath(repo),*args],capture_output=True,check=False)
    if p.returncode: raise DeploymentError(p.stderr.decode(errors="replace").strip())
    return p.stdout.decode().strip() if text else p.stdout

def verify_exact_git_identity(repo_root:Path,expected_head:str,expected_tree:str)->GitIdentity:
    repo=Path(repo_root).resolve(); got=GitIdentity(str(_git(repo,"rev-parse","HEAD")),str(_git(repo,"rev-parse","HEAD^{tree}")))
    if got.head!=expected_head: raise GitIdentityMismatch(f"HEAD {got.head} != {expected_head}")
    if got.tree!=expected_tree: raise GitIdentityMismatch(f"TREE {got.tree} != {expected_tree}")
    return got

def _j(v:object)->bytes: return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def _sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def _fsyncdir(p:Path)->None:
    fd=os.open(p,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
    try: os.fsync(fd)
    finally: os.close(fd)
def _atomic_json(p:Path,v:Mapping[str,object])->None:
    p.parent.mkdir(parents=True,exist_ok=True); data=_j(v); fd,n=tempfile.mkstemp(prefix=f".{p.name}.",dir=p.parent); t=Path(n)
    try:
        with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(t,p); _fsyncdir(p.parent)
        if p.read_bytes()!=data: raise DeploymentError(f"JSON readback mismatch: {p}")
    finally:
        if t.exists(): t.unlink()
def _project(s:str)->str:
    prefix=next((candidate for candidate in PROJECTION_PREFIXES if s.startswith(candidate)),None)
    if prefix is None: raise DeploymentError(s)
    p=PurePosixPath(s[len(prefix):])
    if not str(p) or p.is_absolute() or ".." in p.parts: raise DeploymentError(s)
    return p.as_posix()
def _sources(repo:Path,i:GitIdentity)->list[tuple[str,str,str,bytes]]:
    raw=bytes(_git(repo,"ls-tree","-r","-z",i.head,"--","AIFE/staging","src",text=False)); out=[]; projected={}
    for rec in raw.split(b"\0"):
        if not rec: continue
        meta,rp=rec.split(b"\t",1); mb,kb,ob=meta.split(b" ",2); mode,kind,oid=mb.decode(),kb.decode(),ob.decode(); s=rp.decode()
        if kind!="blob" or mode not in {"100644","100755"}: raise UnsupportedGitEntry(f"{s}:{mode}:{kind}")
        p=_project(s)
        previous=projected.get(p)
        if previous is not None: raise ProjectedPathCollision(f"{p}:{previous}:{s}")
        projected[p]=s
        out.append((s,p,mode,bytes(_git(repo,"cat-file","blob",oid,text=False))))
    out.sort(key=lambda x:x[1])
    if not out: raise DeploymentError("empty projection")
    return out
def _digest(src:Sequence[tuple[str,str,str,bytes]])->str:
    h=hashlib.sha256()
    for _,p,m,b in src:
        for x in (p.encode(),m.encode(),b): h.update(len(x).to_bytes(8,"big")); h.update(x)
    return h.hexdigest()
def _make_manifest(i:GitIdentity,rid:str,digest:str,src:Sequence[tuple[str,str,str,bytes]])->tuple[dict[str,object],str]:
    core={"schema_version":"aife-release-manifest/1.0.0","source_head":i.head,"source_tree":i.tree,"release_id":rid,"release_digest":digest,
          "entries":[{"source_path":s,"projected_path":p,"git_mode":m,"size":len(b),"source_byte_sha256":_sha(b)} for s,p,m,b in src]}
    mid=_sha(_j(core)); return {**core,"release_manifest_id":mid},mid
def _entry_map(m:Mapping[str,object])->dict[str,Mapping[str,object]]:
    raw=m.get("entries")
    if not isinstance(raw,list): raise ReleaseIdentityMismatch("entries")
    out={}
    for x in raw:
        if not isinstance(x,dict) or not isinstance(x.get("projected_path"),str): raise ReleaseIdentityMismatch("entry")
        out[str(x["projected_path"])]=x
    return out

def verify_installed_release(path:Path,expected_manifest:Mapping[str,object])->None:
    try: obs=json.loads((path/MANIFEST).read_text())
    except Exception as e: raise ReleaseIdentityMismatch("manifest unavailable") from e
    if obs!=expected_manifest: raise ReleaseIdentityMismatch("manifest identity")
    for p,e in _entry_map(obs).items():
        f=path/p
        if not f.is_file() or f.is_symlink(): raise ReleaseIdentityMismatch(p)
        b=f.read_bytes()
        if len(b)!=e.get("size") or _sha(b)!=e.get("source_byte_sha256"): raise MaterializedByteMismatch(p)
    core=dict(obs); mid=core.pop("release_manifest_id",None)
    if not isinstance(mid,str) or _sha(_j(core))!=mid: raise ReleaseIdentityMismatch("manifest digest")

def materialize_immutable_release(repo_root:Path,*,expected_head:str,expected_tree:str,release_root:Path,release_id:str)->tuple[GitIdentity,ReleasePlan,Path]:
    if not release_id or "/" in release_id or release_id in {".",".."}: raise ReleaseIdentityMismatch("release_id")
    i=verify_exact_git_identity(repo_root,expected_head,expected_tree); src=_sources(Path(repo_root).resolve(),i); dg=_digest(src); man,mid=_make_manifest(i,release_id,dg,src)
    rr=Path(release_root); rr.mkdir(parents=True,exist_ok=True); rp=rr/release_id
    if rp.exists() or rp.is_symlink():
        if not rp.is_dir() or rp.is_symlink(): raise ReleaseIdentityMismatch("preexisting type")
        verify_installed_release(rp,man); ev=tuple(ProjectedEntry(s,p,m,"",len(b),_sha(b),_sha((rp/p).read_bytes())) for s,p,m,b in src)
        return i,ReleasePlan(i.head,i.tree,release_id,dg,mid,ev,man),rp
    st=Path(tempfile.mkdtemp(prefix=f".{release_id}.",dir=rr)); ev=[]
    try:
        for s,p,m,b in src:
            f=st/p; f.parent.mkdir(parents=True,exist_ok=True)
            with f.open("wb") as h: h.write(b); h.flush(); os.fsync(h.fileno())
            got=f.read_bytes()
            if got!=b: raise MaterializedByteMismatch(s)
            os.chmod(f,0o555 if m=="100755" else 0o444); ev.append(ProjectedEntry(s,p,m,"",len(b),_sha(b),_sha(got)))
        _atomic_json(st/MANIFEST,man); os.chmod(st/MANIFEST,0o444)
        for root,dirs,_ in os.walk(st,topdown=False):
            for d in dirs: os.chmod(Path(root)/d,0o555)
        os.chmod(st,0o555); os.replace(st,rp); _fsyncdir(rr); verify_installed_release(rp,man)
    finally:
        if st.exists():
            try: os.chmod(st,0o755)
            except OSError: pass
            shutil.rmtree(st,ignore_errors=True)
    return i,ReleasePlan(i.head,i.tree,release_id,dg,mid,tuple(ev),man),rp

def _pointer(p:Path)->Path|None: return p.resolve(strict=True) if p.is_symlink() else None
def _link(p:Path,target:Path)->None:
    p.parent.mkdir(parents=True,exist_ok=True); t=p.parent/f".{p.name}.{uuid4().hex}"
    try: os.symlink(os.fspath(target.resolve()),t); os.replace(t,p); _fsyncdir(p.parent)
    finally:
        if t.is_symlink() or t.exists(): t.unlink()
def activate_release(*,current_pointer:Path,previous_pointer:Path,candidate_release:Path,pre_activation_check:Callable[[],bool])->str|None:
    pred,oldprev=_pointer(current_pointer),_pointer(previous_pointer); pid=pred.name if pred else None
    try:
        if not pre_activation_check(): raise ActivationError("precondition")
        if not candidate_release.is_dir() or candidate_release.is_symlink(): raise ActivationError("candidate")
        if pred: _link(previous_pointer,pred)
        _link(current_pointer,candidate_release)
        if _pointer(current_pointer)!=candidate_release.resolve() or (pred and _pointer(previous_pointer)!=pred): raise ActivationError("readback")
        return pid
    except Exception:
        if pred: _link(current_pointer,pred)
        elif current_pointer.is_symlink() or current_pointer.exists(): current_pointer.unlink()
        if oldprev: _link(previous_pointer,oldprev)
        elif previous_pointer.is_symlink() or previous_pointer.exists(): previous_pointer.unlink()
        raise

def write_deployment_map(path:Path,payload:Mapping[str,object])->Mapping[str,object]:
    _atomic_json(path,payload); o=json.loads(path.read_text())
    if o!=payload: raise DeploymentError("map readback")
    return o

def build_deployment_map(*,release_root:Path,current_pointer:Path,previous_pointer:Path,plan:ReleasePlan,config_identity:str,control_backend_identity:str,control_schema_identity:str,persistent_roots:Mapping[str,str],backing_default:str="c6-disposable-backing")->dict[str,object]:
    return {"schema_version":"aife-deployment-map/1.0.0","release_root":os.fspath(release_root),"current_release":os.fspath(current_pointer),"previous_release":os.fspath(previous_pointer),"candidate_release_identity":plan.release_id,"active_release_identity":plan.release_id,"config_identity":config_identity,"control_backend_identity":control_backend_identity,"control_schema_id":control_schema_identity,"control_schema_identity":control_schema_identity,"control_schema_version":1,"backing_identity":persistent_roots.get("backing_identity",backing_default),"data_root":persistent_roots.get("data_root"),"persistent_roots_or_bindings":dict(sorted(persistent_roots.items())),"source_head":plan.source_head,"source_tree":plan.source_tree,"release_digest":plan.release_digest,"release_manifest_id":plan.release_manifest_id}

def readback_deployment_receipt(path:Path,*,expected_deployment_id:str,expected_receipt_id:str)->Mapping[str,object]:
    try: o=json.loads(path.read_text())
    except Exception as e: raise DeploymentReceiptMismatch("receipt unavailable") from e
    if o.get("deployment_id")!=expected_deployment_id or o.get("deployment_receipt_id")!=expected_receipt_id: raise DeploymentReceiptMismatch("receipt identity")
    req={"source_head","source_tree","release_id","release_digest","release_manifest_id","config_identity_or_digest","control_backend_identity","control_schema_identity","declared_persistent_roots_or_bindings","installation_result","validation_result","activation_result","terminal_outcome"}
    if req.difference(o): raise DeploymentReceiptMismatch("receipt fields")
    return o

def build_deployment_receipt(*,deployment_id:str,receipt_id:str,plan:ReleasePlan,config_identity:str,control_backend_identity:str,control_schema_identity:str,persistent_roots:Mapping[str,str],predecessor_release_id:str|None)->dict[str,object]:
    return {"schema_version":"aife-deployment-receipt/1.0.0","deployment_id":deployment_id,"deployment_receipt_id":receipt_id,"source_head":plan.source_head,"source_tree":plan.source_tree,"release_id":plan.release_id,"release_digest":plan.release_digest,"release_manifest_id":plan.release_manifest_id,"config_identity_or_digest":config_identity,"control_backend_identity":control_backend_identity,"control_schema_identity":control_schema_identity,"declared_persistent_roots_or_bindings":dict(sorted(persistent_roots.items())),"predecessor_or_rollback_target_if_applicable":predecessor_release_id,"domain_semantic_authority":False}

def write_deployment_receipt(path:Path,payload:Mapping[str,object])->Mapping[str,object]:
    _atomic_json(path,payload)
    return readback_deployment_receipt(path,expected_deployment_id=str(payload["deployment_id"]),expected_receipt_id=str(payload["deployment_receipt_id"]))

def execute_release_activation(*,plan:ReleasePlan,release_path:Path,deployment_map_path:Path,receipt_path:Path,current_pointer:Path,previous_pointer:Path,deployment_id:str,deployment_receipt_id:str,config_identity:str,control_backend_identity:str,control_schema_identity:str,persistent_roots:Mapping[str,str],pre_activation_check:Callable[[Mapping[str,object]],bool],backing_default:str="c6-disposable-backing")->tuple[Mapping[str,object],Mapping[str,object],str|None]:
    pred=_pointer(current_pointer); pid=pred.name if pred else None
    mapping=build_deployment_map(release_root=release_path.parent,current_pointer=current_pointer,previous_pointer=previous_pointer,plan=plan,config_identity=config_identity,control_backend_identity=control_backend_identity,control_schema_identity=control_schema_identity,persistent_roots=persistent_roots,backing_default=backing_default)
    write_deployment_map(deployment_map_path,mapping)
    base=build_deployment_receipt(deployment_id=deployment_id,receipt_id=deployment_receipt_id,plan=plan,config_identity=config_identity,control_backend_identity=control_backend_identity,control_schema_identity=control_schema_identity,persistent_roots=persistent_roots,predecessor_release_id=pid)
    try:
        if not pre_activation_check(mapping): raise ActivationError("precondition")
        pid=activate_release(current_pointer=current_pointer,previous_pointer=previous_pointer,candidate_release=release_path,pre_activation_check=lambda:True)
        base["predecessor_or_rollback_target_if_applicable"]=pid
        receipt=write_deployment_receipt(receipt_path,{**base,"installation_result":"PASS","validation_result":"PASS","activation_result":"PASS","terminal_outcome":"PASS"})
    except Exception as e:
        write_deployment_receipt(receipt_path,{**base,"installation_result":"PASS","validation_result":"FAIL","activation_result":"PRECONDITION_FAILED" if isinstance(e,ActivationError) else "FAIL","terminal_outcome":"FAIL"})
        raise
    return mapping,receipt,pid

def execute_disposable_deployment(repo_root:Path,*,expected_head:str,expected_tree:str,install_root:Path,release_id:str,deployment_id:str,deployment_receipt_id:str,config_identity:str,control_backend_identity:str,control_schema_identity:str,persistent_roots:Mapping[str,str],pre_activation_check:Callable[[Mapping[str,object]],bool])->DeploymentResult:
    root=Path(install_root).resolve(); rr=root/"releases"; mp=root/"config/deployment-map.json"; rp=root/"state/deployments/receipts"/f"{deployment_id}.json"
    i,plan,release=materialize_immutable_release(repo_root,expected_head=expected_head,expected_tree=expected_tree,release_root=rr,release_id=release_id)
    _mapping,rec,pid=execute_release_activation(plan=plan,release_path=release,deployment_map_path=mp,receipt_path=rp,current_pointer=root/"current",previous_pointer=root/"previous",deployment_id=deployment_id,deployment_receipt_id=deployment_receipt_id,config_identity=config_identity,control_backend_identity=control_backend_identity,control_schema_identity=control_schema_identity,persistent_roots=persistent_roots,pre_activation_check=pre_activation_check)
    return DeploymentResult(i,plan,release,mp,rp,rec,pid)

def _pred(root:Path)->tuple[str,Path]:
    rid="c6-predecessor-fixture"; p=root/"releases"/rid; p.mkdir(parents=True); f=p/"fixture.txt"; f.write_bytes(b"accepted predecessor fixture\n"); os.chmod(f,0o444); os.chmod(p,0o555); _link(root/"current",p); return rid,p
def qualify_checkout(repo_root:Path,expected_head:str,expected_tree:str)->dict[str,object]:
    i=verify_exact_git_identity(repo_root,expected_head,expected_tree)
    with tempfile.TemporaryDirectory(prefix="aife-c6-") as td:
        root=Path(td)/"install"; root.mkdir(); pred,predpath=_pred(root); data=Path(td)/"data"; data.mkdir(); roots={"data_root":os.fspath(data),"state_root":os.fspath(Path(td)/"state"),"spool_root":os.fspath(Path(td)/"spool"),"log_root":os.fspath(Path(td)/"log"),"backing_identity":"c6-disposable-backing"}; ready={"v":False}
        def check(m:Mapping[str,object])->bool:
            from server.configuration.models import F5ReadinessConfig
            from server.runtime.readiness import evaluate_f5_readiness
            c=F5ReadinessConfig(deployment_map_path=root/"config/deployment-map.json",expected_release_identity="c6-disposable-release",expected_config_identity="c6-config-v1",expected_backing_identity="c6-disposable-backing",minimum_free_bytes=1); ready["v"]=evaluate_f5_readiness(c,control_schema_check=lambda:None).ready
            return ready["v"] and m["source_head"]==expected_head and m["source_tree"]==expected_tree
        r=execute_disposable_deployment(repo_root,expected_head=expected_head,expected_tree=expected_tree,install_root=root,release_id="c6-disposable-release",deployment_id="c6-disposable-deployment",deployment_receipt_id="c6-disposable-receipt",config_identity="c6-config-v1",control_backend_identity="sqlite-c6-fixture",control_schema_identity="aife-server-control",persistent_roots=roots,pre_activation_check=check); rec=readback_deployment_receipt(r.receipt_path,expected_deployment_id="c6-disposable-deployment",expected_receipt_id="c6-disposable-receipt")
        if _pointer(root/"current")!=r.release_path.resolve() or _pointer(root/"previous")!=predpath.resolve(): raise ActivationError("pointer proof")
        if rec["source_head"]!=expected_head or rec["source_tree"]!=expected_tree or rec["release_digest"]!=r.release.release_digest or rec["release_manifest_id"]!=r.release.release_manifest_id: raise DeploymentReceiptMismatch("binding")
        return {"QUALIFIED_CHECKOUT_SHA":i.head,"QUALIFIED_CHECKOUT_TREE":i.tree,"ACTUAL_GIT_HEAD_MATCH":"PASS","ACTUAL_GIT_TREE_MATCH":"PASS","ACTUAL_CHECKOUT_SHA_MATCH":"PASS","PHYSICAL_IDENTITY_PROOF":"PASS","C6_EXECUTABLE_DEPLOYMENT_PRIMITIVE":"PASS","MATERIALIZED_PATH_COUNT":len(r.release.entries),"MATERIALIZED_SOURCE_BYTE_IDENTITY":"PASS" if all(x.byte_identity_match for x in r.release.entries) else "FAIL","IMMUTABLE_RELEASE_MATERIALIZATION":"PASS","RELEASE_IDENTITY":"PASS","RELEASE_ID":r.release.release_id,"RELEASE_DIGEST":r.release.release_digest,"RELEASE_MANIFEST_ID":r.release.release_manifest_id,"RELEASE_GIT_BINDING":"PASS","DEPLOYMENT_MAP_BINDING":"PASS","DEPLOYMENT_RECEIPT_BINDING":"PASS","DEPLOYMENT_RECEIPT_DURABLE_READBACK":"PASS","PREDECESSOR_RELEASE":pred,"CANDIDATE_RELEASE":r.release.release_id,"PRE_ACTIVATION_VALIDATION":"PASS" if ready["v"] else "FAIL","ATOMIC_POINTER_TRANSITION":"PASS","CURRENT_RESOLVES_TO_INTENDED_RELEASE":"PASS","PREVIOUS_RESOLVES_TO_PREDECESSOR":"PASS","POST_ACTIVATION_READBACK":"PASS","ATOMIC_RELEASE_ACTIVATION_PROOF":"PASS","F5_READINESS":"PASS" if ready["v"] else "FAIL","QUALIFICATION_IS_ACTIVATION":"NO","REAL_SERVER_ACTIVATION":"NO","SHADOW_ACTIVATION":"NO","PRODUCTION_ACTIVATION":"NO","projected_entries":[{"SOURCE_PATH":x.source_path,"PROJECTED_PATH":x.projected_path,"SOURCE_BYTE_SHA256":x.source_sha256,"MATERIALIZED_BYTE_SHA256":x.materialized_sha256,"BYTE_IDENTITY_MATCH":"PASS" if x.byte_identity_match else "FAIL"} for x in r.release.entries]}
def _print(e:Mapping[str,object])->None:
    for x in e.get("projected_entries",[]):
        if isinstance(x,dict): print("PROJECTED_ENTRY "+" ".join(f"{k}={v}" for k,v in x.items()))
    for k,v in e.items():
        if k!="projected_entries": print(f"{k}={v}")
def _cli(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True); q=s.add_parser("qualify"); q.add_argument("--repo-root",type=Path,required=True); q.add_argument("--expected-head",required=True); q.add_argument("--expected-tree",required=True); q.add_argument("--evidence-output",type=Path); a=p.parse_args(argv); e=qualify_checkout(a.repo_root,a.expected_head,a.expected_tree); _print(e)
    if a.evidence_output: _atomic_json(a.evidence_output,e)
    return 0
if __name__=="__main__": raise SystemExit(_cli())
