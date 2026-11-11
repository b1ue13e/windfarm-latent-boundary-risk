"""Read local supplied bytes/fields only; never execute an experimental module."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def stream_sha(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024*1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materials-archive',type=Path)
    args=parser.parse_args()
    manifest=json.loads((HERE/'release_inventory.json').read_text(encoding='utf-8'))
    failures=[]
    for name,record in manifest['files'].items():
        path=ROOT/name
        if not path.is_file():failures.append('missing:'+name);continue
        with path.open('rb') as handle:actual=stream_sha(handle)
        if actual!=record['sha256']:failures.append('sha256:'+name)
    protocol=json.loads((ROOT/'source_data/M_protocol.json').read_text(encoding='utf-8'))
    limits=protocol['thresholds']
    if not (limits['important_cost_gain']==.01 and limits['substitution_margin']==.01
            and limits['risk_cap']==.1 and limits['weighted_U_increment_over_Cstar']==.001):
        failures.append('original thresholds differ')
    summary=json.loads((ROOT/'source_data/M_controls_summary.json').read_text(encoding='utf-8'))
    routes=summary['corrected_routes']
    if len(routes)!=4 or any(any(x.values()) for x in routes.values()):failures.append('stored corrected routes differ')
    material_count=0
    if args.materials_archive:
        with (HERE/'materials_inventory.csv').open(encoding='utf-8-sig',newline='') as handle:
            rows=list(csv.DictReader(handle))
        with zipfile.ZipFile(args.materials_archive) as archive:
            names=set(archive.namelist())
            for row in rows:
                name=row['archive_path']
                if name not in names:failures.append('missing archive member:'+name);continue
                if archive.getinfo(name).file_size!=int(row['bytes']):failures.append('member size:'+name)
                with archive.open(name) as handle:actual=stream_sha(handle)
                if actual!=row['sha256']:failures.append('member hash:'+name)
                material_count+=1
        if len(rows)!=403:failures.append('material inventory does not contain403 selected files')
    print(json.dumps({'status':'FAIL' if failures else 'PASS_OFFLINE_BYTES_AND_STORED_FIELDS',
          'source_files_checked':len(manifest['files']),'material_members_checked':material_count,
          'failures':failures,'models_loaded':False,'experimental_modules_executed':False,
          'new_predictions_calibration_or_statistics':False},indent=2))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
