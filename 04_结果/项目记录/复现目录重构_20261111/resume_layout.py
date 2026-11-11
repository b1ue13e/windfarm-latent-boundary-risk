"""Finish directory moves recorded before a transient Windows rename failure."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT/'02_公共资源/项目管理/复现目录重构_20261111'
OUT = ROOT/'04_结果/项目记录/复现目录重构_20261111'
RECORD = OLD if OLD.exists() else OUT
moves = json.loads((RECORD/'moves.json').read_text(encoding='utf-8'))
with gzip.open(RECORD/'file_identity_before.json.gz','rt',encoding='utf-8') as f:
    records=json.load(f)
mapping=json.loads((RECORD/'path_map_before.json').read_text(encoding='utf-8'))
ordered=sorted(moves,key=lambda row:len(row[0]),reverse=True)
def translate(name):
    for old,new in ordered:
        if name==old or name.startswith(old+'/'):return new+name[len(old):]
    return name
identities=[]
failures=[]
def move(row):
    old,new=row;p=ROOT/old;q=ROOT/new
    if not p.exists():
        assert q.exists(),new
        return
    if q.exists() and old=='02_公共资源/项目管理':
        for child in list(p.iterdir()):
            move((old+'/'+child.name,new+'/'+child.name))
        if not any(p.iterdir()):p.rmdir()
        return
    assert not q.exists(),new
    before=p.stat()
    q.parent.mkdir(parents=True,exist_ok=True)
    try:p.rename(q)
    except OSError as exc:
        failures.append(dict(old=old,new=new,error=str(exc)));return
    after=q.stat()
    assert (before.st_ino,before.st_dev)==(after.st_ino,after.st_dev)
    identities.append(dict(old=old,new=new,inode=after.st_ino,device=after.st_dev))
regular=[row for row in moves if row[0]!='02_公共资源/项目管理']
with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(move,regular))
print('Remaining rename failures',len(failures),flush=True)
if failures:
    (RECORD/'rename_failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(1)
move(('02_公共资源/项目管理','04_结果/项目记录'))
mapping={old:translate(new) for old,new in mapping.items()}
mapping.update(moves)
mapping.update({'experiments':'04_结果/实验','analyses':'04_结果/分析','research_audit':'04_结果/审计','artifacts':'04_结果/产物'})
(ROOT/'04_结果/项目记录/目录迁移/path_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check(row):
    if row['new']=='04_结果/项目记录/目录迁移/path_map.json':
        # This live index is intentionally updated; its original bytes are saved
        # separately as path_map_before.json, outside frozen scientific records.
        return None
    st=(ROOT/row['new']).stat()
    actual=(st.st_size,st.st_mtime_ns,st.st_ino,st.st_dev)
    expected=(row['size'],row['mtime_ns'],row['inode'],row['device'])
    return row['new'] if actual!=expected else None
with ThreadPoolExecutor(max_workers=16) as pool:bad=list(filter(None,pool.map(check,records)))
assert not bad,bad
previous=json.loads((ROOT/'04_结果/项目记录/文件清理_20261111/protected_before.json').read_text(encoding='utf-8'))
protected={translate(p):h for p,h in previous.items()}
hash_bad=[p for p,h in protected.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert not hash_bad,hash_bad
for folder in ['01_研究尝试','02_公共资源','03_论文交付','99_历史归档']:
    for base,ds,fs in os.walk(ROOT/folder,topdown=False):
        p=Path(base)
        if not any(p.iterdir()):p.rmdir()
result=dict(moved_units=len(moves),checked_tracked_and_protected_files=len(records),identity_mismatches=bad,
            protected_hashes=len(protected),hash_mismatches=hash_bad,scientific_computation_executed=False,
            raw_data_copied_to_git=False,remaining_renames_verified_by_unit_identity=len(identities),
            note='Original Windows rename interruption retained; tracked files and protected evidence verified against pre-move identities.')
(OUT/'unit_identities.json').write_text(json.dumps(identities,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'MIGRATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
