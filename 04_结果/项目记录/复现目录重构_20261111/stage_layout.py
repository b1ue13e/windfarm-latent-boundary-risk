"""Stage only this physical reorganization, preserving original tracked blobs."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json

ROOT = Path(__file__).resolve().parents[3]
RECORD = Path(__file__).resolve().parent
GIT = "C:/Program Files/Git/mingw64/bin/git.exe"
COMMAND = [GIT, "-c", "core.fsmonitor=", "-c", "core.longpaths=true", "-c", "diff.renames=false", "-c", "core.fscache=true"]


def run(args, data=None):
    result = subprocess.run(COMMAND + args, input=data, cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


assert run(["rev-parse", "HEAD"]).decode().strip() == "502574a531ac399ceebff045e33f7de1a2f854d2"
assert not run(["diff-index", "--cached", "--no-renames", "--name-only", "HEAD"]).strip()
base = {}
for entry in (RECORD / "index_before.bin").read_bytes().split(b"\0"):
    if entry:
        meta, path = entry.split(b"\t", 1)
        mode, oid, stage = meta.split()
        assert stage == b"0"
        base[path.decode("utf-8")] = (mode.decode(), oid.decode())
moves = sorted(json.loads((RECORD / "moves.json").read_text(encoding="utf-8")), key=lambda row: len(row[0]), reverse=True)
fixes = {r["old"]: r["new"] for r in json.loads((RECORD / "navigation_asset_moves.json").read_text(encoding="utf-8"))}


def physical_destination(old):
    # Logical aliases can have the same spelling as a real root file (pytest.ini).
    # Git renames follow the physical move ledger, not the legacy I/O namespace.
    for source, target in moves:
        if old == source or old.startswith(source + "/"):
            new = target + old[len(source):]
            return fixes.get(new, new)
    return old


targets, moved = {}, []
for old, meta in base.items():
    new = physical_destination(old)
    assert (ROOT / new).is_file(), (old, new)
    if new in targets:
        assert targets[new] == meta, (old, new)
    targets[new] = meta
    if old != new:
        moved.append((old, new))
changed = set(json.loads((RECORD / "LIVE_CODE_CHANGES.json").read_text(encoding="utf-8")))
changed.update([
    "README.md", "README.en.md", "project.py", "复现说明.md", "02_代码/reproduction.py", "02_代码/README.md",
    "03_数据/README.md", "04_结果/README.md", "01_当前论文/TSTE/README.md", "01_当前论文/TSTE/FIGURES_V14_README_CN.md",
    "02_代码/工程/README.md", "02_代码/工程/repo_paths.py", "02_代码/工程/tests/test_repository_paths.py",
    "04_结果/项目记录/目录迁移/README.md", ".gitignore",
])
for file in RECORD.iterdir():
    if file.is_file() and file.name not in {"index_before.bin", "path_map_before.json"} and not file.name.startswith("git_"):
        changed.add(file.relative_to(ROOT).as_posix())
changed = sorted(p for p in changed if (ROOT / p).is_file())
assert not any(p.startswith("03_数据/") and p != "03_数据/README.md" for p in changed)


def hash_file(path):
    return run(["hash-object", "-w", "--path=" + path, "--stdin"], (ROOT / path).read_bytes()).decode().strip()


print("Reusing", len(moved), "moved blobs; writing", len(changed), "live edits and records", flush=True)
with ThreadPoolExecutor(max_workers=12) as pool:
    for path, oid in zip(changed, pool.map(hash_file, changed)):
        targets[path] = (targets.get(path, ("100644", ""))[0], oid)
updates = []
for old in base:
    if old not in targets:
        updates.append(("0 " + "0" * 40 + "\t" + old + "\0").encode("utf-8"))
for path, (mode, oid) in sorted(targets.items()):
    updates.append((mode + " " + oid + "\t" + path + "\0").encode("utf-8"))
run(["update-index", "-z", "--index-info"], b"".join(updates))
staged = [p.decode("utf-8") for p in run(["diff", "--cached", "--no-renames", "--name-only", "-z"]).split(b"\0") if p]
assert not any(p.startswith("03_数据/") and p != "03_数据/README.md" for p in staged)
source_paths = [p for p in changed if p.endswith(".py")] + ["README.md", "复现说明.md"]
run(["diff", "--cached", "--check", "--", *source_paths])
report = dict(status="PASS", staged_paths=len(staged), moved_tracked_paths=len(moved), raw_datasets_excluded=True,
              existing_blobs_reused=True, unrelated_unstaged_file_content_preserved=True)
path = RECORD / "STAGING.json"
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
relative = path.relative_to(ROOT).as_posix()
oid = hash_file(relative)
run(["update-index", "--add", "--cacheinfo", "100644," + oid + "," + relative])
print(json.dumps(report, indent=2), flush=True)
