"""Bounded readability/schema survey; no scientific conclusion from file format."""
from pathlib import Path
import collections
import csv
import json
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_audit'

def header(f):
    version=np.lib.format.read_magic(f)
    if version==(1,0):shape,fortran,dtype=np.lib.format.read_array_header_1_0(f)
    else:shape,fortran,dtype=np.lib.format.read_array_header_2_0(f)
    return dict(shape=shape,dtype=str(dtype),object_dtype=bool(dtype.hasobject),fortran=fortran)

def main():
    counts=collections.Counter();errors=[];rows=[]
    with (OUT/'research_assets.csv').open(encoding='utf-8-sig',newline='') as file:
        assets=list(csv.DictReader(file))
    for i,r in enumerate(assets):
        p=ROOT/r['path'];suffix=r['suffix'];status='NOT_CONTENT_PARSED';detail='Metadata census only; binary/text content not interpreted'
        try:
            if suffix in ('.json','.ipynb'):
                if int(r['bytes'])>50*1024*1024:
                    status='NOT_PARSED_SIZE_BOUND';detail='JSON >50MiB skipped explicitly'
                else:
                    value=json.loads(p.read_text(encoding='utf-8-sig'))
                    status='JSON_SYNTAX_READABLE';detail=json.dumps(dict(type=type(value).__name__,top_keys=list(value)[:25] if isinstance(value,dict) else None),ensure_ascii=False)
            elif suffix=='.csv':
                with p.open(encoding='utf-8-sig',newline='') as file:
                    fields=next(csv.reader(file),[])
                status='CSV_FIRST_RECORD_READABLE';detail=json.dumps(fields,ensure_ascii=False)[:4000]
            elif suffix=='.npy':
                with p.open('rb') as file:detail=json.dumps(header(file))
                status='NPY_HEADER_ONLY'
            elif suffix=='.npz':
                with zipfile.ZipFile(p) as archive:
                    description={}
                    for name in archive.namelist():
                        if name.endswith('.npy'):
                            with archive.open(name) as file:description[name]=header(file)
                    detail=json.dumps(description,ensure_ascii=False)[:12000]
                status='NPZ_ARRAY_HEADERS_ONLY'
        except Exception as e:
            status='READ_OR_PARSE_ERROR';detail=type(e).__name__+': '+str(e)
            errors.append(dict(path=r['path'],error=detail))
        counts[status]+=1
        rows.append(dict(path=r['path'],bytes=r['bytes'],status=status,detail=detail))
        if (i+1)%10000==0:print('SCHEMA',i+1,flush=True)
    with (OUT/'asset_readability.csv').open('w',encoding='utf-8-sig',newline='') as file:
        w=csv.DictWriter(file,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    (OUT/'asset_readability_summary.json').write_text(json.dumps(dict(total=len(rows),counts=dict(counts),errors=errors,
        warning='Syntax/header survey is not experimental/content validity review. CSV only first record; NPY/NPZ only headers; torch/pickle never deserialized.'),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(total=len(rows),counts=dict(counts),n_errors=len(errors)),ensure_ascii=False))

if __name__=='__main__':main()
