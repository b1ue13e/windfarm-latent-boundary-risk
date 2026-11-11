"""Read-only primary literature retrieval; never reads or downloads measurement data."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime, hashlib, json, requests, fitz

ROOT = Path(__file__).resolve().parent
READ = ROOT.parent / 'literature_reading'
READ.mkdir(exist_ok=True)
DOIS = [
 ('mlwa', '10.1016/j.mlwa.2026.100957'),
 ('seta', '10.1016/j.seta.2026.105438'),
 ('safer', '10.1016/j.egyai.2026.100900'),
 ('wen2024', '10.1016/j.energy.2024.131544'),
 ('meng2026', '10.1109/TSTE.2025.3611370'),
 ('stratigakos2026', '10.1109/TSG.2025.3620957'),
 ('pritchard2011', '10.1002/we.416'),
 ('phipps2022', '10.1002/we.2736'),
 ('dantas2026', '10.1002/we.70079'),
 ('zhao2021', '10.1109/TPWRS.2021.3053847'),
 ('sun2022', '10.1063/5.0087144'),
 ('sophia2011', '10.1002/we.444'),
]
PDFS = [
 ('meng2026_accepted', 'https://ira.lib.polyu.edu.hk/bitstream/10397/117725/1/Meng_Probabilistic_Wind_Power.pdf'),
 ('stratigakos2026_accepted', 'https://discovery.ucl.ac.uk/id/eprint/10215885/1/Learning_Data-Driven_Uncertainty_Set_Partitions_for_Robust_and_Adaptive_Energy_Forecasting_with_Missing_Data.pdf'),
 ('wen2024_arxiv_v3', 'https://arxiv.org/pdf/2305.14662v3'),
 ('wen2025_arxiv_v2', 'https://arxiv.org/pdf/2403.03631v2'),
]

def get_one(kind, name, url):
    rec = dict(kind=kind, name=name, requested_url=url,
               accessed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        r=requests.get(url, timeout=45, headers={'User-Agent':'ScientificLiteratureAudit/1.0'})
        rec.update(status=r.status_code, final_url=r.url, bytes=len(r.content),
                   content_type=r.headers.get('Content-Type'), sha256=hashlib.sha256(r.content).hexdigest())
        if kind=='crossref' and r.status_code==200:
            out=ROOT / (name+'_crossref.json')
            out.write_text(json.dumps(r.json(),ensure_ascii=False,indent=2),encoding='utf-8')
            m=r.json()['message']
            rec['summary']={k:m.get(k) for k in ['DOI','title','author','container-title','volume','issue','page','published','published-online','published-print','created','link']}
        elif kind=='pdf' and r.status_code==200 and r.content.startswith(b'%PDF'):
            out=READ / (name+'.pdf'); out.write_bytes(r.content)
            doc=fitz.open(out)
            (READ/(name+'.txt')).write_text('\n\n'.join(f'=== PDF PAGE {i+1} ===\n'+p.get_text() for i,p in enumerate(doc)),encoding='utf-8')
            rec['pages']=len(doc)
        else:
            rec['outcome']='not_full_text'
    except Exception as e: rec['error']=str(e)
    return rec

jobs=[('crossref',n,'https://api.crossref.org/works/'+doi) for n,doi in DOIS]+[('pdf',n,u) for n,u in PDFS]
with ThreadPoolExecutor(max_workers=4) as pool: records=list(pool.map(lambda a:get_one(*a),jobs))
(ROOT/'ACCESS_RECEIPTS.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
for r in records:
    print(json.dumps({k:r.get(k) for k in ['name','status','bytes','pages','outcome','error']},ensure_ascii=False))
