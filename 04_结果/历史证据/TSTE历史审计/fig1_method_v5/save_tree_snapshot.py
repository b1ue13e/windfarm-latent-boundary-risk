"""Save the touched tree without using the shared Git index."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib,json,subprocess
B=Path(__file__).resolve().parents[2];ROOT = Path(repository_root());Q=Path(__file__).resolve().parent
def git(*args,data=None):
    p=subprocess.run(['C:/Program Files/Git/mingw64/bin/git.exe','-c','core.fsmonitor=','-c','core.hooksPath=NUL',*args],cwd=ROOT,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
protected=[ROOT/'.git/index',ROOT/'.git/index.lock'];before=[digest(p) for p in protected];head=git('rev-parse','HEAD')
parent=git('rev-parse','refs/heads/codex/tste-fig1-method-v4-20261027').decode().strip()
ref='refs/heads/codex/tste-fig1-method-v5-20261027'
if subprocess.run(['git','show-ref','--verify','--quiet',ref],cwd=ROOT).returncode==0:raise RuntimeError('Snapshot already exists')
paths=[B/n for n in ['README.md','FIG1_METHOD_V5_README_CN.md','AUTHOR_NOTES_CN.md','manuscript.tex','manuscript.md','manuscript.pdf','manuscript_fig1_method_v5.pdf','figure_code/overview_v5.py','sections/methods_body.tex','qa/ACCEPTANCE.json','qa/BUILD_MANUSCRIPT.json','qa/FINAL_CHECKS.json','qa/manuscript_extracted.txt']]
paths.extend(p for p in (B/'figures/v5').glob('*') if p.is_file())
paths.extend(p for p in Q.glob('*') if p.is_file() and p.name not in ['GIT_SAVE.json','save_snapshot.py'])
names=[p.relative_to(ROOT).as_posix() for p in paths]
oids=git('hash-object','--no-filters','-w','--stdin-paths',data=(chr(10).join(names)+chr(10)).encode()).decode().splitlines()
assert len(oids)==len(names)
patch={}
for name,oid in zip(names,oids):
    node=patch;parts=name.split('/')
    for part in parts[:-1]:node=node.setdefault(part,{})
    node[parts[-1]]=oid
def edit(tree,delta):
    entries={}
    if tree:
        for row in git('ls-tree','-z',tree).split(bytes([0])):
            if not row:continue
            meta,name=row.split(bytes([9]),1);entries[name.decode('utf-8')]=tuple(meta.decode().split())
    for name,value in delta.items():
        entries[name]=('040000','tree',edit(entries[name][2] if name in entries else None,value)) if isinstance(value,dict) else ('100644','blob',value)
    data=b''.join(f'{m} {t} {o}'.encode()+bytes([9])+n.encode()+bytes([0]) for n,(m,t,o) in entries.items())
    return git('mktree','-z',data=data).decode().strip()
tree=edit(git('rev-parse',parent+'^{tree}').decode().strip(),patch)
commit=git('commit-tree',tree,'-p',parent,data=b'Place TSTE method figure on a continuous wind-farm background').decode().strip()
git('update-ref',ref,commit,'0'*40)
assert before==[digest(p) for p in protected] and git('rev-parse','HEAD')==head
r=dict(branch=ref.removeprefix('refs/heads/'),commit=commit,parent=parent,files=len(names),shared_index_unchanged=True,existing_lock_unchanged=True,checkout_unchanged=True,pushed=False)
(Q/'GIT_SAVE.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
