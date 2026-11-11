"""Save only the figure revision on its own branch, preserving the shared index."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import os
import subprocess
import tempfile

Q = Path(__file__).resolve().parent
B = Q.parents[1]
ROOT = Path(repository_root())
parent_ref = "refs/heads/codex/tste-results-style-v13-20261027"
target_ref = "refs/heads/codex/tste-figures-v14-20261028"


def git(*args, env=None, data=None):
    r = subprocess.run(["git", "-c", "core.fsmonitor=", *args], cwd=ROOT,
                       env=env, input=data, capture_output=True, timeout=90)
    if r.returncode:
        raise RuntimeError(r.stderr.decode("utf-8", errors="replace"))
    return r.stdout.decode("utf-8", errors="replace").strip()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


for f in [Q/"FINAL_CHECKS.json", B/"qa/FINAL_CHECKS.json"]:
    assert json.loads(f.read_text())["status"] == "PASS"
head = git("rev-parse", "HEAD")
parent = git("rev-parse", parent_ref)
idx = ROOT/".git/index"
index_before = sha(idx)
exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", target_ref], cwd=ROOT)
assert exists.returncode == 1, "Revision branch already exists; do not replace."
files = {B/p for p in ["README.md", "FIGURES_V14_README_CN.md", "manuscript.tex", "manuscript.md",
    "sections/methods_body.tex", "sections/result_figures_body.tex", "sections/results_body.tex",
    "figure_code/figures_v14.py", "figure_code/audit_panel_alignment.py", "figure_code/requirements_figures.txt"]}
files.update((B/"figures/v14").glob("*.svg"))
files.update(Q.glob("*.py"))
files.update(Q.glob("*.json"))
files.update(Q.glob("*.md"))
paths = sorted(p.relative_to(ROOT).as_posix() for p in files)
assert not any(p.endswith((".pdf", ".zip", ".png")) for p in paths)
with tempfile.TemporaryDirectory(prefix="tste-v14-index-") as td:
    env = dict(os.environ, GIT_INDEX_FILE=str(Path(td)/"index"))
    git("read-tree", parent, env=env)
    git("add", "--", *paths, env=env)
    changed = git("diff", "--cached", "--name-only", parent, env=env).splitlines()
    assert changed and all(p.startswith('"manuscripts/') or p.startswith("manuscripts/") for p in changed)
    tree = git("write-tree", env=env)
    message = ("Redesign TSTE architecture and real-result figures\n\n"
               "Separate information timing, request construction, matched telemetry effects, "
               "cross-year trade-offs and full calendar outcomes across five main figures. "
               "Preserve all recorded results and original intervals; no new experiments.\n")
    commit = git("commit-tree", tree, "-p", parent, data=message.encode("utf-8"), env=env)
    git("update-ref", target_ref, commit, "0"*40)
assert git("rev-parse", "HEAD") == head and sha(idx) == index_before
receipt = dict(branch=target_ref.removeprefix("refs/heads/"), commit=commit, parent=parent,
               changed_paths=len(changed), shared_head_and_index_unchanged=True,
               new_compiled_binaries_committed=False, pushed=False)
(Q/"GIT_SAVE.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
