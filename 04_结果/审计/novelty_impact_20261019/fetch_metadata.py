"""Verify public metadata without treating metadata as scientific content."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
import datetime as dt
import hashlib
import json
import platform
import sys

OUT=Path(__file__).resolve().parent
DOIS=['10.1002/we.416','10.1063/5.0087144','10.1016/j.ejor.2024.01.025',
      '10.3982/ECTA5771','10.1214/24-AOAS1998','10.1109/TPWRS.2020.2975246',
      '10.1016/j.energy.2024.131544','10.1109/TPWRS.2021.3053847',
      '10.1016/j.omega.2025.103508','10.1016/j.ejor.2024.03.020']

def fetch(doi):
    url='https://api.crossref.org/works/'+quote(doi,safe='')
    try:
        req=Request(url,headers={'User-Agent':'ResearchAuditMetadata/1.0'})
        with urlopen(req,timeout=25) as response:raw=response.read()
        m=json.loads(raw)['message']
        return dict(doi=doi,url=url,status='METADATA_VERIFIED',sha256=hashlib.sha256(raw).hexdigest(),
            title=m.get('title'),authors=m.get('author'),published=m.get('published'),
            online=m.get('published-online'),print_date=m.get('published-print'),
            venue=m.get('container-title'),volume=m.get('volume'),issue=m.get('issue'),page=m.get('page'),
            references=m.get('reference',[]),license=m.get('license'),raw_message=m)
    except Exception as e:
        return dict(doi=doi,url=url,status='FETCH_FAILED',error=type(e).__name__+': '+str(e))

def main():
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,DOIS))
    receipt=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),argv=sys.argv,python=sys.version,
        platform=platform.platform(),records=records,
        scope='Public bibliographic metadata only. Not proof that original methods/experiments were read.')
    (OUT/'crossref_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([dict(doi=x['doi'],status=x['status'],title=x.get('title')) for x in records],ensure_ascii=False))

if __name__=='__main__':main()
