"""Package existing writing artifacts only; do not build or execute experiments."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE=Path(__file__).resolve().parents[1]


def make_archive(path,files,relative_root=HERE):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in sorted(files):archive.write(p,arcname=p.relative_to(relative_root).as_posix())
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    code=HERE/'supplement_data/code_and_provenance'
    make_archive(HERE/'supplement_data/Supplementary_Data4_code_and_provenance.zip',[p for p in code.iterdir() if p.is_file()],relative_root=code)
    figures=list((HERE/'figures').glob('*'))+[HERE/'scripts/build_figures.py',HERE/'FIGURE_CONTRACT.md']
    figures += list((HERE/'source_data').glob('display_*.csv'))
    figures += [p for p in (HERE/'qa').glob('*.alignment.json')]
    figure_result=make_archive(HERE/'scientific_reports_figures_and_sources.zip',[p for p in figures if p.is_file()])
    files=[]
    for p in HERE.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts or 'build' in p.relative_to(HERE).parts:continue
        if p.suffix=='.zip' and p.name!='Supplementary_Data4_code_and_provenance.zip':continue
        if p.name.endswith('_contact_1.png') or '_contact_' in p.name or p.name=='figure_contact_sheet.png':continue
        if p.name in ['package_receipt.json','packaging_checks.json','DELIVERY_MANIFEST.json']:continue
        files.append(p)
    result=make_archive(HERE/'scientific_reports_review_draft_sources.zip',files)
    (HERE/'qa/package_receipt.json').write_text(json.dumps({'status':'LOCAL_REVIEW_ARTIFACTS_NOT_PUBLICLY_RELEASED',
        'archives':[figure_result,result],'full_package_files':len(files),'large_model_action_arrays_included':False,
        'source_and_stored_data_included':True,'research_executed':False},indent=2)+'\n')
    print(json.dumps({'archives':[figure_result,result],'files':len(files)}))


if __name__=='__main__':main()
