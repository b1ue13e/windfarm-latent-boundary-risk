"""Build both manuscripts using the existing XeLaTeX/BibTeX installation."""
from pathlib import Path
import os
import shutil
import subprocess
import json
import re
import argparse

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)
env = os.environ.copy()
env["BIBINPUTS"] = str(ROOT) + os.pathsep + env.get("BIBINPUTS", "")
records = []
parser = argparse.ArgumentParser()
parser.add_argument("--quick", action="store_true", help="Two TeX passes using the existing bibliography")
parser.add_argument("--document", choices=("manuscript", "supplementary"))
args = parser.parse_args()
for stem in ((args.document,) if args.document else ("manuscript", "supplementary")):
    tex = ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
           "-output-directory=build", f"{stem}.tex"]
    commands = (tex, tex) if args.quick else (tex, ["bibtex", f"build/{stem}"], tex, tex)
    for i, cmd in enumerate(commands, 1):
        run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True)
        log = ROOT / "qa" / f"{stem}_{'quick' if args.quick else 'pass'}{i}.txt"
        log.write_bytes(run.stdout + run.stderr)
        records.append(dict(document=stem, command=cmd, exit_code=run.returncode,
                            log=log.name))
        if run.returncode:
            print((run.stdout + run.stderr).decode("utf-8", errors="replace")[-6000:])
            raise SystemExit(run.returncode)
    final = (BUILD / f"{stem}.log").read_text(encoding="utf-8", errors="replace")
    bad = re.findall(r"(?:LaTeX Warning: (?:Citation|Reference).*?undefined[^\n]*|Overfull [^\n]*|LaTeX Font Warning:[^\n]*)", final)
    records.append(dict(document=stem, final_warnings=bad))
    shutil.copy2(BUILD / f"{stem}.pdf", ROOT / f"{stem}.pdf")
    print(f"{stem}: PDF generated; {len(bad)} final warnings")
receipt_name = f"BUILD_{args.document.upper()}.json" if args.document else "BUILD_RECEIPT.json"
(ROOT / "qa" / receipt_name).write_text(
    json.dumps(records, indent=2), encoding="utf-8")
