"""Save this revision without changing the shared checkout or Git index."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import hashlib
import json
import os
import subprocess
import tempfile

B = Path(__file__).resolve().parents[2]
ROOT = Path(repository_root())
Q = Path(__file__).resolve().parent
parent_ref = "refs/heads/codex/tste-fig1-v3-20261027"
target_ref = "refs/heads/codex/tste-fig1-method-v4-20261027"

def git(*args, env=None, data=None):
    p = subprocess.run(["git", *args], cwd=ROOT, env=env, input=data,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", errors="replace"))
    return p.stdout.decode("utf-8", errors="replace").strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

protected = [ROOT / ".git/index", ROOT / ".git/index.lock"]
before = {str(p): digest(p) for p in protected}
head = git("rev-parse", "HEAD")
parent = git("rev-parse", parent_ref)
exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", target_ref], cwd=ROOT)
if exists.returncode == 0:
    raise RuntimeError("Snapshot branch already exists; refusing to overwrite it.")

relative = [
    "README.md", "FIG1_METHOD_V4_README_CN.md", "manuscript.tex", "manuscript.md",
    "manuscript.pdf", "manuscript_fig1_method_v4.pdf", "figure_code/overview_v4.py",
    "figures/v4", "source_data/v4", "sections/methods_body.tex",
    "sections/result_figures_body.tex", "sections/study_design_body.tex",
    "sections/results_body.tex", "qa/ACCEPTANCE.json", "qa/BUILD_MANUSCRIPT.json",
    "qa/FINAL_CHECKS.json", "qa/manuscript_extracted.txt", "qa/fig1_method_v4"
]
paths = [str((B / p).relative_to(ROOT)) for p in relative]
with tempfile.TemporaryDirectory(prefix="tste-method-v4-") as task_tmp:
    env = dict(os.environ, GIT_INDEX_FILE=str(Path(task_tmp) / "task.index"))
    git("read-tree", parent, env=env)
    git("add", "--", *paths, env=env)
    changes = git("diff", "--cached", "--name-status", parent, env=env)
    assert changes and not any(line.startswith("D\t") for line in changes.splitlines())
    tree = git("write-tree", env=env)
    message = "Expand telemetry-to-reserve construction in TSTE Figure 1\n\nShow the quantile estimator, historical residual correction and recorded request example; integrate the figure in the seven-page manuscript.\n"
    commit = git("commit-tree", tree, "-p", parent, env=env, data=message.encode())
    git("update-ref", target_ref, commit, "0" * 40)
after = {str(p): digest(p) for p in protected}
assert before == after and git("rev-parse", "HEAD") == head
receipt = dict(branch=target_ref.removeprefix("refs/heads/"), commit=commit,
               parent=parent, changed_paths=len(changes.splitlines()),
               shared_index_unchanged=True, existing_lock_unchanged=True,
               checkout_unchanged=True, pushed=False)
(Q / "GIT_SAVE.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
