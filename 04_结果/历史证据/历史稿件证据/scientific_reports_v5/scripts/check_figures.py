"""Run installed deterministic figure-QA tools on final rendered exports."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]
TOOLS = Path.home()/".agents/skills/nature-figure/scripts"


def main():
    records=[]
    command=[sys.executable,'-X','utf8','-B',str(TOOLS/'validate_figure.py'),str(HERE/'scripts/build_figures.py'),'--json']
    source=subprocess.run(command,text=True,capture_output=True,encoding='utf-8')
    (HERE/'author_working/qa/figure_source_check.json').write_text(source.stdout)
    source.check_returncode()
    failed=[]
    for pdf in sorted((HERE/'figures').glob('*.pdf')):
        glyph=subprocess.run([sys.executable,'-X','utf8','-B',str(TOOLS/'audit_pdf_text.py'),str(pdf),'--min-pt','5','--json'],text=True,capture_output=True,encoding='utf-8')
        (HERE/'author_working'/'qa'/f'{pdf.stem}.glyph.json').write_text(glyph.stdout)
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(TOOLS/'audit_figure_collisions.py'),str(pdf),
                '--json-out',str(HERE/'author_working'/'qa'/f'{pdf.stem}.collision.json'),
                '--overlay-pdf',str(HERE/'author_working'/'qa'/f'{pdf.stem}.collision.pdf')],
                text=True,capture_output=True,encoding='utf-8')
        (HERE/'author_working'/'qa'/f'{pdf.stem}.collision.txt').write_text(result.stdout+result.stderr)
        record={'figure':pdf.name,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'glyph_exit':glyph.returncode,'collision_exit':result.returncode}
        records.append(record)
        if glyph.returncode or result.returncode:failed.append(pdf.name)
    (HERE/'author_working/qa/rendered_figure_checks.json').write_text(json.dumps({'records':records,'failed':failed},indent=2)+'\n')
    print(json.dumps({'records':records,'failed':failed}))
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
