"""Flatten research storage without rewriting any experiment evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
OLD_RECORD = ROOT / "02_公共资源/项目管理/复现目录重构_20261111"
OUT = ROOT / "04_结果/项目记录/复现目录重构_20261111"


def translate(value, operations):
    for src, dst in sorted(operations, key=lambda item: len(item[0]), reverse=True):
        if value == src or value.startswith(src + "/"):
            return dst + value[len(src):]
    return value


def inventory(pair):
    src, dst = pair
    path = ROOT / src
    found = []
    def entries(p):
        with os.scandir(p) as directory:
            for entry in directory:
                assert not entry.is_symlink(), entry.path
                if entry.is_dir(follow_symlinks=False):
                    yield from entries(entry.path)
                else:
                    yield Path(entry.path), entry.stat(follow_symlinks=False)
    paths = [(path, path.stat())] if path.is_file() else entries(path)
    for p, st in paths:
        rel = p.relative_to(ROOT).as_posix()
        found.append(dict(old=rel, new=dst + rel[len(src):], size=st.st_size,
                          mtime_ns=st.st_mtime_ns))
    return found


def main():
    namespace = {"experiments": "实验", "analyses": "分析", "research_audit": "审计", "artifacts": "产物"}
    operations = []
    research = ROOT / "01_研究尝试"
    for base, dirs, names in os.walk(research):
        p = Path(base)
        if p.name in namespace:
            operations.append((p.relative_to(ROOT).as_posix(), "04_结果/" + namespace[p.name]))
            dirs[:] = []
    # Namespace roots from different attempts are merged by their unique named
    # units; directory content is moved intact, preserving all source snapshots.
    merged = []
    for src, dst in operations:
        for p in (ROOT / src).iterdir():
            merged.append((p.relative_to(ROOT).as_posix(), dst + "/" + p.name))
    operations = merged
    covered = [src for src, _ in operations]
    for base, dirs, names in os.walk(research):
        p = Path(base)
        dirs[:] = [d for d in dirs if (p/d).relative_to(ROOT).as_posix() not in covered]
        for name in names:
            f = p/name
            src = f.relative_to(ROOT).as_posix()
            if src in covered:
                continue
            # Retain obsolete navigation/history text, without retaining the
            # attempt/stage folder hierarchy in the new workspace.
            label = "__".join(f.relative_to(research).parts)
            operations.append((src, "04_结果/项目记录/旧目录说明/" + label))
    operations += [
        ("03_论文交付/当前稿件_TSTE", "01_当前论文/TSTE"),
        ("02_公共资源/工程", "02_代码/工程"),
        ("02_公共资源/工具", "02_代码/工具"),
        ("02_公共资源/数据/wtbdata_245days.csv", "03_数据/原始/wtbdata_245days.csv"),
        ("02_公共资源/数据/sdwpf_baidukddcup2022_turb_location.CSV", "03_数据/原始/sdwpf_baidukddcup2022_turb_location.CSV"),
        ("02_公共资源/数据/data", "03_数据/外部数据"),
        ("02_公共资源/数据/派生缓存/artifacts", "03_数据/派生缓存"),
        ("02_公共资源/文献", "01_当前论文/参考文献"),
        ("02_公共资源/运行缓存", "04_结果/运行缓存"),
        ("02_公共资源/项目管理", "04_结果/项目记录"),
        ("02_公共资源/README.md", "04_结果/项目记录/旧公共资源说明.md"),
        ("99_历史归档/保留证据", "04_结果/历史证据"),
        ("99_历史归档/旧工作目录", "04_结果/历史工作记录"),
        ("99_历史归档/README.md", "04_结果/项目记录/旧历史证据说明.md"),
    ]
    operations = [(src, dst) for src, dst in operations if (ROOT/src).exists()]
    destinations = [dst for _, dst in operations]
    assert len(destinations) == len(set(destinations)), "Colliding namespace units"
    for src, dst in operations:
        p, q = ROOT/src, ROOT/dst
        Path(str(p.resolve()).removeprefix("\\\\?\\")).relative_to(ROOT)
        q.absolute().relative_to(ROOT)
        assert not q.exists(), dst
    # Save metadata and byte fingerprints before renaming. Large raw files are
    # renamed on the same volume, preserving filesystem identity and timestamps.
    print("Preparing", len(operations), "atomic same-volume moves", flush=True)
    # Do not walk ignored runtime mirrors/environments merely for bookkeeping.
    # Each whole-directory move is checked by filesystem object identity; file
    # metadata checks cover tracked materials and explicit protected sources.
    index = (OLD_RECORD/'index_before.bin').read_bytes()
    selected = set()
    for entry in index.split(b'\0'):
        if entry:
            _,name=entry.split(b'\t',1)
            selected.add(name.decode('utf-8'))
    old_mapping=json.loads((ROOT/'02_公共资源/项目管理/目录迁移/path_map.json').read_text(encoding='utf-8'))
    paper_receipt=json.loads((ROOT/'03_论文交付/当前稿件_TSTE/qa/visual_redesign_20261027/DATA_RECEIPT.json').read_text(encoding='utf-8'))
    for name in paper_receipt['source_hashes']:
        for prefix,target in sorted(old_mapping.items(),key=lambda item:len(item[0]),reverse=True):
            if name==prefix or name.startswith(prefix+'/'):
                selected.add(target+name[len(prefix):]);break
    def selected_record(name):
        destination=translate(name,operations)
        if destination==name:return None
        st=(ROOT/name).stat()
        return dict(old=name,new=destination,size=st.st_size,mtime_ns=st.st_mtime_ns,
                    inode=st.st_ino,device=st.st_dev)
    with ThreadPoolExecutor(max_workers=16) as pool:
        records=list(filter(None,pool.map(selected_record,sorted(selected))))
    print('Tracked/protected files inventoried',len(records),flush=True)
    OLD_RECORD.mkdir(exist_ok=True)
    (OLD_RECORD/"moves.json").write_text(json.dumps(operations, ensure_ascii=False, indent=2), encoding="utf-8")
    with gzip.open(OLD_RECORD/"file_identity_before.json.gz", "wt", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    protected_file = ROOT/"02_公共资源/项目管理/文件清理_20261111/protected_before.json"
    previous = json.loads(protected_file.read_text(encoding="utf-8"))
    mapping_file = ROOT/"02_公共资源/项目管理/目录迁移/path_map.json"
    mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
    mapping_bytes = mapping_file.read_bytes()
    (OLD_RECORD/"path_map_before.json").write_bytes(mapping_bytes)
    protected = {translate(p, operations): h for p, h in previous.items()}
    # Project instructions/PROJECT.md were not part of the filesystem moves.
    unit_identities = {}
    def move(pair):
        src, dst = pair
        q = ROOT/dst
        q.parent.mkdir(parents=True, exist_ok=True)
        before = (ROOT/src).stat()
        (ROOT/src).rename(q)
        after = q.stat()
        assert (before.st_ino, before.st_dev) == (after.st_ino, after.st_dev)
        unit_identities[src] = dict(new=dst, inode=after.st_ino, device=after.st_dev)
    # Project records are moved last because they contain this migration ledger.
    regular = [p for p in operations if p[0] != "02_公共资源/项目管理"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(move, regular))
    move(("02_公共资源/项目管理", "04_结果/项目记录"))
    mapping = {k: translate(v, operations) for k, v in mapping.items()}
    mapping.update(operations)
    # Old category roots still resolve for callers that join an experiment name
    # incrementally. More specific aliases retain their original precedence.
    mapping.update({"experiments": "04_结果/实验", "analyses": "04_结果/分析", "research_audit": "04_结果/审计",
                    "artifacts": "04_结果/产物", "02_公共资源/工程": "02_代码/工程",
                    "02_公共资源/项目管理": "04_结果/项目记录"})
    # Preserve longest-prefix exceptions during incremental joins. For example,
    # artifacts resolves to saved outputs, but artifacts/cache_* resolves to data.
    # Joining the already-resolved parent must reach the same final location.
    for old, new in list(mapping.items()):
        parts = old.split('/')
        for n in range(len(parts)-1, 0, -1):
            parent = '/'.join(parts[:n])
            if parent in mapping:
                joined = mapping[parent] + '/' + '/'.join(parts[n:])
                if joined != new:
                    mapping[joined] = new
    (ROOT/"04_结果/项目记录/目录迁移/path_map.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    # Compare the same filesystem object, size and timestamp after rename.
    def check_record(row):
        st=(ROOT/row['new']).stat()
        expected=(row['size'],row['mtime_ns'],row['inode'],row['device'])
        actual=(st.st_size,st.st_mtime_ns,st.st_ino,st.st_dev)
        return row['new'] if actual!=expected else None
    with ThreadPoolExecutor(max_workers=16) as pool:
        mismatches=list(filter(None,pool.map(check_record,records)))
    assert not mismatches, mismatches
    bad_hashes = [p for p,h in protected.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != h]
    assert not bad_hashes, bad_hashes
    # Remove empty former category shells only; no recursive deletion.
    for directory in ["01_研究尝试", "02_公共资源", "03_论文交付", "99_历史归档"]:
        for base, dirs, names in os.walk(ROOT/directory, topdown=False):
            p = Path(base)
            if not any(p.iterdir()):
                p.rmdir()
    result = dict(moved_units=len(operations), checked_tracked_and_protected_files=len(records),
                  checked_bytes=sum(r["size"] for r in records), identity_mismatches=mismatches,
                  protected_hashes=len(protected), hash_mismatches=bad_hashes,
                  raw_data_copied_to_git=False, scientific_computation_executed=False)
    (OUT/'unit_identities.json').write_text(json.dumps(unit_identities,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/"MIGRATION.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
