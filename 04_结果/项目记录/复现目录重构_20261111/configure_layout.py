"""Update live entry points after moving frozen evidence without editing it."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "04_结果/项目记录/复现目录重构_20261111"
ENGINE = ROOT / "02_代码/工程"
PAPER = ROOT / "01_当前论文/TSTE"
assert (OUT/"MIGRATION.json").exists()
changed = []

# Some historical logical parents contain both cached inputs and saved outputs.
# Add their canonical child exceptions so incremental Path joins remain correct.
mapping_file = ROOT/"04_结果/项目记录/目录迁移/path_map.json"
mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
cache_directory = ROOT/'03_数据/派生缓存/cache'
cache_directory.mkdir(parents=True,exist_ok=True)
mapping['artifacts/cache']='03_数据/派生缓存/cache'
mapping['02_公共资源/数据']='03_数据'
for old,new in list(mapping.items()):
    parts=old.split('/')
    for n in range(len(parts)-1,0,-1):
        parent='/'.join(parts[:n])
        if parent in mapping:
            joined=mapping[parent]+'/'+('/'.join(parts[n:]))
            if joined != new:
                mapping[joined]=new
mapping_file.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def write(p, text):
    before = p.read_text(encoding="utf-8") if p.exists() else None
    if before != text:
        if before is not None:
            backup = OUT/"source_before"/p.relative_to(ROOT)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(p.read_bytes())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        changed.append(p.relative_to(ROOT).as_posix())


replacements = {
    "02_公共资源/工程": "02_代码/工程", "03_论文交付/当前稿件_TSTE": "01_当前论文/TSTE",
    "02_公共资源/运行缓存": "04_结果/运行缓存",
    "02_公共资源/项目管理": "04_结果/项目记录",
    "02_公共资源/文献": "01_当前论文/参考文献",
    "99_历史归档/保留证据": "04_结果/历史证据",
}
for base in [ENGINE, PAPER]:
    for p in base.rglob("*.py"):
        text = p.read_text(encoding="utf-8-sig")
        new = text
        for old, replacement in replacements.items():
            new = new.replace(old, replacement)
        if new != text:
            write(p, new)

paths = ENGINE/"repo_paths.py"
text = paths.read_text(encoding="utf-8")
text = text.replace('return NativePath(__file__).resolve().parents[2]',
    'return next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())')
start = text.index('    for old, new in path_map().items():')
end = text.index('    return p', start)
text = text[:start] + '''    mapping = path_map()
    parts = rel.split("/")
    for length in range(len(parts), 0, -1):
        old = "/".join(parts[:length])
        if old in mapping:
            return root / mapping[old] / "/".join(parts[length:])
''' + text[end:]
write(paths, text)

p = ENGINE/"project.py"
text = p.read_text(encoding="utf-8")
text = text.replace('output = root / "04_结果/运行缓存/目录迁移验收/numbers"',
    'output = Path(os.environ["REPRODUCTION_OUTPUT_DIR"]) / "numbers" if "REPRODUCTION_OUTPUT_DIR" in os.environ else root / "04_结果/运行缓存/目录迁移验收/numbers"')
text = text.replace('env = dict(os.environ, PYTHONPATH=str(engineering) + os.pathsep + os.environ.get("PYTHONPATH", ""))',
    'env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(engineering), str(engineering / "scripts"), os.environ.get("PYTHONPATH", "")]))')
write(p, text)

# The scientific rules stay identical; only their live filesystem entry points change.
p = ROOT/"AGENTS.md"
text = p.read_text(encoding="utf-8")
for old, new in replacements.items():
    text = text.replace(old, new)
text = text.replace('python "02_代码/工程/project.py"', 'python project.py')
write(p, text)

# Rewrite working hyperlinks in the project board, not frozen audit records.
mapping = json.loads((ROOT/"04_结果/项目记录/目录迁移/path_map.json").read_text(encoding="utf-8"))
def mapped(path):
    parts = path.split('/')
    for n in range(len(parts), 0, -1):
        prefix = '/'.join(parts[:n])
        if prefix in mapping:
            return mapping[prefix] + ('/'+'/'.join(parts[n:]) if parts[n:] else '')
    return path
p = ROOT/"PROJECT.md"
text = p.read_text(encoding="utf-8")
def link(match):
    original = match.group(1)
    if '://' in original or original.startswith('#'):
        return match.group(0)
    target, _, anchor = original.partition('#')
    new = mapped(target)
    return '](' + new + ('#'+anchor if anchor else '') + ')'
text = re.sub(r'\]\(([^)]+)\)', link, text)
write(p, text)

write(ROOT/"pytest.ini", '''[pytest]
testpaths = 02_代码/工程/tests
pythonpath = 02_代码/工程
cache_dir = 04_结果/运行缓存/pytest_cache
''')
p = ROOT/".gitignore"
text = p.read_text(encoding="utf-8") + '''
# Reproduction layout: local raw data, tools and new runs are never staged implicitly.
03_数据/
02_代码/工具/
04_结果/运行缓存/
04_结果/复现运行/
04_结果/历史工作记录/
04_结果/项目记录/复现目录重构_20261111/index_before.bin
04_结果/项目记录/复现目录重构_20261111/source_before/
04_结果/项目记录/复现目录重构_20261111/path_map_before.json
04_结果/项目记录/复现目录重构_20261111/git_*
'''
write(p, text)

# Current QA scripts read the same inputs but direct fresh reports to the run dir.
p = PAPER/"qa/verify_draft.py"
text = p.read_text(encoding="utf-8")
text = text.replace('checks = []', '''import os
REPORT_DIR = Path(os.environ.get("REPRODUCTION_OUTPUT_DIR", str(BASE / "qa"))) / "draft"
if "REPRODUCTION_OUTPUT_DIR" not in os.environ:
    REPORT_DIR = BASE / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
checks = []''')
text = text.replace('(BASE/"qa"/f"{stem}_extracted.txt")', '(REPORT_DIR/f"{stem}_extracted.txt")')
text = text.replace('(BASE/"qa/FINAL_CHECKS.json")', '(REPORT_DIR/"FINAL_CHECKS.json")')
write(p, text)
p = PAPER/"qa/figure_rebuild_v14/verify_v14.py"
text = p.read_text(encoding="utf-8")
text = text.replace('checks = []', '''import os
REPORT_DIR = Path(os.environ["REPRODUCTION_OUTPUT_DIR"]) / "figures" if "REPRODUCTION_OUTPUT_DIR" in os.environ else Q
REPORT_DIR.mkdir(parents=True, exist_ok=True)
checks = []''')
text = text.replace('Q / "protected_inputs_cleanup_20261111.json"', 'Q / "protected_inputs_layout_20261111.json"')
text = text.replace('(Q/"FINAL_CHECKS.json").write_text', '(REPORT_DIR/"FINAL_CHECKS.json").write_text')
write(p, text)
old_manifest = PAPER/"qa/figure_rebuild_v14/protected_inputs_cleanup_20261111.json"
rows = json.loads(old_manifest.read_text(encoding="utf-8"))
new_rows = json.loads(json.dumps(rows))
instruction_change = {}
for row in new_rows:
    if row['path'] == '../../AGENTS.md':
        instruction_change = dict(before=row['sha256'], after=hashlib.sha256((ROOT/'AGENTS.md').read_bytes()).hexdigest(),
                                  scope="Only live path/command literals in AGENTS.md were updated; scientific rules unchanged")
        row['sha256'] = instruction_change['after']
assert all(old == new for old,new in zip(rows,new_rows) if old['path']!='../../AGENTS.md')
write(PAPER/"qa/figure_rebuild_v14/protected_inputs_layout_20261111.json", json.dumps(new_rows, indent=2))
(OUT/"INSTRUCTION_PATH_UPDATE.json").write_text(json.dumps(instruction_change,indent=2),encoding="utf-8")

# A maintained copy of the original report generator uses the shared resolver;
# the actual historical executing source remains untouched with the result bundle.
source = ROOT/"04_结果/实验/mainline_supplement_20261026/build_report.py"
text = source.read_text(encoding="utf-8")
text = text.replace('from pathlib import Path', 'from repo_paths import Path')
write(ROOT/"02_代码/实验复现/mainline_report.py", text)

(OUT/"LIVE_CODE_CHANGES.json").write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding="utf-8")
print("Updated live files:", len(changed), flush=True)
