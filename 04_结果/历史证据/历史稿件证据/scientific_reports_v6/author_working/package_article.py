"""Package article text/data/build sources separately from author review records."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    files=[ROOT/name for name in ['manuscript.md','manuscript.pdf','main.tex','supplementary.md','supplementary.tex','supplementary.pdf','references.bib','scientific-reports-brackets.csl','build.py','README.md']]
    for folder in ['figures','source_data','tables','scripts','supplement_data']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.name not in ['check_figures.py','validate_story.py']]
    files.append(ROOT/'author_working/tools/audit_panel_alignment.py')
    path=ROOT/'scientific_reports_v6_article_sources.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in sorted(set(files)):archive.write(p,p.relative_to(ROOT).as_posix())
        archive.writestr('BUILD_NOTE.txt','Editable text, figures and saved source values. Document projection: python scripts/prepare_story_tables.py; python scripts/build_figures.py; python build.py. Requires Python with Matplotlib/NumPy/PyMuPDF/Pillow, Pandoc and XeLaTeX. Research implementations are not executed by these commands.\n')
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert not any('/qa/' in n or 'REWRITE_NOTES' in n or 'AUTHOR_ITEMS' in n for n in archive.namelist())
        members=len(archive.namelist())
    record={'archive':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'members':members,'author_review_records_included':False}
    (ROOT/'author_working/qa/package_receipt.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(record)


if __name__=='__main__':main()
