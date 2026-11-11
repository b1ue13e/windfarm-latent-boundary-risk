"""Package the figure assets and commit only this revision using a separate index."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import os
import subprocess
import zipfile

Q = Path(__file__).resolve().parent
B = Q.parents[1]
ROOT = Path(repository_root())
PARENT = "5c1bf502b2a8813be95559258000f62574a8fbd9"
REF = "refs/heads/codex/tste-results-style-v13-20261027"

bundle = [B / "RESULTS_STYLE_V13_README_CN.md", B / "figure_code/results_v13.py"]
bundle += [p for folder in ["figures/v12", "figures/v13"] for p in (B / folder).glob("fig*.*")
           if p.suffix in [".pdf", ".svg", ".png"]]
bundle += sorted((B / "source_data/v2").glob("*.csv"))
with zipfile.ZipFile(B / "tste_results_style_v13.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in bundle:
        archive.write(path, path.relative_to(B).as_posix())
print("Editable figure bundle:", len(bundle), "files", flush=True)

env = os.environ.copy()
env["GIT_INDEX_FILE"] = str(Q / "snapshot.index")
env["GIT_OPTIONAL_LOCKS"] = "0"

def git(*args, stdin=None, plain=False):
    p = subprocess.run(["git", "-c", "core.fsmonitor=", "-c", "core.hooksPath=NUL", *args],
                       input=stdin, cwd=ROOT, env=os.environ.copy() if plain else env,
                       capture_output=True, timeout=90)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", errors="replace"))
    return p.stdout

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

gitdir = Path(git("rev-parse", "--absolute-git-dir", plain=True).decode().strip())
protected = [gitdir / "index", gitdir / "index.lock"]
before = [sha(p) for p in protected]
head = git("rev-parse", "HEAD", plain=True)
exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", REF], cwd=ROOT).returncode == 0
if exists:
    raise RuntimeError("Snapshot branch already exists; refusing to overwrite")
paths = [B / p for p in ["README.md", "AUTHOR_NOTES_CN.md", "RESULTS_STYLE_V13_README_CN.md",
         "manuscript.tex", "manuscript.md", "manuscript.pdf", "manuscript_results_style_v13.pdf",
         "manuscript_layout_pages_1_4_v13.png", "manuscript_layout_pages_5_7_v13.png",
         "sections/result_figures_body.tex", "figure_code/results_v13.py", "qa/ACCEPTANCE.json",
         "qa/BUILD_MANUSCRIPT.json", "qa/FINAL_CHECKS.json", "qa/manuscript_extracted.txt"]]
paths += sorted((B / "figures/v13").glob("fig*.*"))
paths += [p for p in Q.iterdir() if p.is_file() and p.suffix in [".py", ".md", ".json", ".txt"]
          and p.name != "GIT_SAVE.json"]
git("read-tree", PARENT)
git("add", "-f", "--", *[p.relative_to(ROOT).as_posix() for p in paths])
tree = git("write-tree").decode().strip()
commit = git("commit-tree", tree, "-p", PARENT,
             stdin=b"Unify results figure typography, stroke hierarchy and panel spacing\n").decode().strip()
git("update-ref", REF, commit, "0" * 40)
assert before == [sha(p) for p in protected]
assert head == git("rev-parse", "HEAD", plain=True)
r = dict(status="SAVED", branch=REF.removeprefix("refs/heads/"), commit=commit, parent=PARENT,
         files=len(paths), shared_index_unchanged=True, existing_lock_unchanged=True,
         checkout_unchanged=True, pushed=False)
(Q / "GIT_SAVE.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
(Q / "snapshot.index").unlink()
print(json.dumps(r, indent=2))
