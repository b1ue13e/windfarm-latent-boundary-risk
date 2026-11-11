"""Repair section-concatenation and citation conversion artifacts, once."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import re

root = Path(__file__).resolve().parents[1]
for name in ("introduction", "methods"):
    p = root / "sections" / f"{name}_body.tex"
    s = p.read_text(encoding="utf-8")
    if r"\n*** Add File:" in s:
        p.write_text(s.split(r"\n*** Add File:", 1)[0].rstrip()+"\n", encoding="utf-8")
for name in ("related_work", "study_design"):
    p = root / "sections" / f"{name}_body.tex"
    s = p.read_text(encoding="utf-8")
    starts = list(re.finditer(r"\\section\{", s))
    if len(starts) == 2:
        p.write_text(s[starts[1].start():], encoding="utf-8")
for p in (root / "sections").glob("*.tex"):
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\[(\\cite\{[^}]+\})\]", r"\1", s)
    p.write_text(s, encoding="utf-8")
print("Section integration repaired.")
