"""Archive existing documents/materials only; never execute research code."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
MATERIAL_ROOT = ROOT/'research_audit/controlled_comparison_materials_20261020'


def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def materials():
    inventory=list(csv.DictReader((HERE/'review_package/materials_inventory.csv').open(encoding='utf-8-sig')))
    assert len(inventory)==403
    path=HERE/'scientific_reports_v2_review_materials.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for index,row in enumerate(inventory,1):
            relative=Path(row['archive_path']).relative_to('materials')
            source=(MATERIAL_ROOT/relative).resolve()
            if not source.is_relative_to(MATERIAL_ROOT.resolve()) or not source.is_file():raise ValueError('Material path not confined or absent')
            if source.stat().st_size!=int(row['bytes']):raise ValueError('Stored material size changed')
            archive.write(source,row['archive_path'])
            if index%50==0:print('Existing material members archived:',index,flush=True)
        for name in ['REVIEW_GUIDE.md','materials_inventory.csv','ACCESS_STATUS.json']:
            archive.write(HERE/'review_package'/name,'review_package/'+name)
    print('Local existing-material archive created:',path.name,path.stat().st_size,flush=True)


def sources():
    excluded={'qa/package_receipt.json','qa/packaging_checks.json','review_package/release_inventory.json'}
    files=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(HERE)
        if 'build' in relative.parts or '__pycache__' in relative.parts or 'rendered' in relative.parts:continue
        if relative.as_posix() in excluded:continue
        if path.suffix=='.zip' and relative.parts[0]!='supplement_data':continue
        files.append(path)
    manifest={p.relative_to(HERE).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}
    (HERE/'review_package/release_inventory.json').write_text(json.dumps({'scope':'Exact local review-source files; no public access or runtime claim','files':manifest},indent=2)+'\n',encoding='utf-8')
    files.append(HERE/'review_package/release_inventory.json')
    path=HERE/'scientific_reports_v2_review_sources.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        for f in files:archive.write(f,f.relative_to(HERE).as_posix())
    figure_files=list(sorted((HERE/'figures').glob('*')))+[HERE/'scripts/build_figures.py',HERE/'review_package/tools/audit_panel_alignment.py',HERE/'FIGURE_CONTRACT.md',HERE/'qa/figure_receipt.json']
    figure_files += list(sorted((HERE/'source_data').iterdir()))
    figure_path=HERE/'scientific_reports_v2_figures_and_sources.zip'
    with zipfile.ZipFile(figure_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for f in figure_files:
            if f.is_file():archive.write(f,f.relative_to(HERE).as_posix())
    material_path=HERE/'scientific_reports_v2_review_materials.zip'
    if material_path.is_file():
        with zipfile.ZipFile(material_path,'a',zipfile.ZIP_STORED,allowZip64=True) as archive:
            if path.name in archive.namelist():raise ValueError('Do not append duplicate source ZIP; rebuild materials instead')
            archive.write(path,path.name)
    packages=[p for p in [path,figure_path,material_path] if p.is_file()]
    receipt={'status':'LOCAL_ARCHIVES_CREATED_NOT_PUBLISHED','packages':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in packages},'source_file_count':len(files),'material_file_count':403,'research_executed':False}
    (HERE/'qa/package_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['materials','sources'])
    args=parser.parse_args()
    materials() if args.stage=='materials' else sources()
