"""Save a bounded content-addressed Git snapshot without using the shared index."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import os
import subprocess
import zlib

B=Path(__file__).resolve().parents[2];ROOT = Path(repository_root());Q=Path(__file__).resolve().parent
GIT="C:/Program Files/Git/mingw64/bin/git.exe"
def git(*args):
    p=subprocess.run([GIT,"-c","core.fsmonitor=","-c","core.hooksPath=NUL",*args],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    if p.returncode:raise RuntimeError(p.stderr.decode("utf-8",errors="replace"))
    return p.stdout
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
gitdir=Path(git("rev-parse","--absolute-git-dir").decode().strip())
assert gitdir.resolve()==(ROOT/".git").resolve()
protected=[gitdir/"index",gitdir/"index.lock"]
before=[digest(p) for p in protected];head=git("rev-parse","HEAD")
parent=git("rev-parse","refs/heads/codex/tste-fig1-scene-v6-20261027").decode().strip()
ref="refs/heads/codex/tste-fig1-integrated-v7-20261027"
if subprocess.run([GIT,"show-ref","--verify","--quiet",ref],cwd=ROOT).returncode==0:
    raise RuntimeError("Snapshot ref already exists; refusing overwrite")
def object_write(kind,data):
    payload=kind.encode()+b" "+str(len(data)).encode()+bytes([0])+data
    oid=hashlib.sha1(payload).hexdigest()
    path=gitdir/"objects"/oid[:2]/oid[2:]
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        temp=path.with_name(path.name+f".integrated-v7-{os.getpid()}.tmp")
        with temp.open("xb") as f:f.write(zlib.compress(payload))
        os.replace(temp,path)
    return oid
paths=[B/n for n in ["README.md","AUTHOR_NOTES_CN.md","FIG1_INTEGRATED_V7_README_CN.md",
    "manuscript.tex","manuscript.md","manuscript.pdf","manuscript_fig1_integrated_v7.pdf",
    "manuscript_fig1_integrated_v7_page2.pdf","figure_code/overview_v7.py",
    "sections/methods_body.tex","qa/ACCEPTANCE.json","qa/BUILD_MANUSCRIPT.json",
    "qa/FINAL_CHECKS.json","qa/manuscript_extracted.txt"]]
paths.extend(p for p in (B/"figures/v7").rglob("*") if p.is_file())
paths.extend(p for p in Q.glob("*") if p.is_file() and p.suffix in [".py",".md",".json",".txt"] and p.name!="GIT_SAVE.json")
patch={}
for p in paths:
    parts=p.relative_to(ROOT).parts;node=patch
    for part in parts[:-1]:node=node.setdefault(part,{})
    node[parts[-1]]=object_write("blob",p.read_bytes())
def tree_edit(old,delta):
    entries={}
    if old:
        for row in git("ls-tree","-z",old).split(bytes([0])):
            if not row:continue
            info,name=row.split(bytes([9]),1)
            mode,kind,oid=info.decode().split()
            entries[name.decode("utf-8")]=(mode,kind,oid)
    for name,value in delta.items():
        if isinstance(value,dict):
            child=tree_edit(entries[name][2] if name in entries else None,value)
            entries[name]=("40000","tree",child)
        else:entries[name]=("100644","blob",value)
    ordered=sorted(entries.items(),key=lambda e:(e[0]+("/" if e[1][1]=="tree" else "")).encode())
    data=b"".join(format(int(mode,8),"o").encode()+b" "+name.encode()+bytes([0])+bytes.fromhex(oid)
        for name,(mode,kind,oid) in ordered)
    return object_write("tree",data)
tree=tree_edit(git("rev-parse",parent+"^{tree}").decode().strip(),patch)
author=git("var","GIT_AUTHOR_IDENT").strip()
committer=git("var","GIT_COMMITTER_IDENT").strip()
data=(b"tree "+tree.encode()+b"\nparent "+parent.encode()+b"\nauthor "+author+
    b"\ncommitter "+committer+b"\n\nIntegrate telemetry, estimation and calibration inside the Figure 1 workstation\n")
commit=object_write("commit",data)
assert git("cat-file","-t",commit).strip()==b"commit"
git("update-ref",ref,commit,"0"*40)
assert before==[digest(p) for p in protected] and git("rev-parse","HEAD")==head
r=dict(status="SAVED",branch=ref.removeprefix("refs/heads/"),commit=commit,parent=parent,
    files=len(paths),shared_index_unchanged=True,existing_lock_unchanged=True,checkout_unchanged=True,pushed=False)
(Q/"GIT_SAVE.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print(json.dumps(r,indent=2))
