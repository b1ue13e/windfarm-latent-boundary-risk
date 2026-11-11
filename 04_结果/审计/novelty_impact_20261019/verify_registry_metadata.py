"""Verify every registered DOI independently against public Crossref metadata."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
import datetime as dt
import difflib
import hashlib
import json
import re
import sys

OUT=Path(__file__).resolve().parent

def norm(x):return re.sub(r'[^a-z0-9]','',x.lower())

def fetch(p):
    if not p['doi']:
        return dict(id=p['id'],status='NO_DOI_DECLARED',source=p['url'])
    url='https://api.crossref.org/works/'+quote(p['doi'],safe='')
    try:
        with urlopen(Request(url,headers={'User-Agent':'ResearchAuditMetadata/1.0'}),timeout=25) as f:raw=f.read()
        m=json.loads(raw)['message'];title=m.get('title',[''])[0]
        score=difflib.SequenceMatcher(None,norm(title),norm(p['title'])).ratio()
        return dict(id=p['id'],doi=p['doi'],url=url,status='TITLE_MATCH' if score>.94 else 'REVIEW_TITLE_MISMATCH',
            title=title,expected_title=p['title'],title_similarity=score,bytes_sha256=hashlib.sha256(raw).hexdigest(),
            authors=m.get('author'),published=m.get('published'),print_date=m.get('published-print'),
            online=m.get('published-online'),venue=m.get('container-title'),volume=m.get('volume'),
            issue=m.get('issue'),pages=m.get('page'),article_number=m.get('article-number'),raw_message=m)
    except Exception as e:
        return dict(id=p['id'],doi=p['doi'],status='FETCH_FAILED',error=type(e).__name__+': '+str(e))

def main():
    path=OUT/'prior_art_registry.json';before=hashlib.sha256(path.read_bytes()).hexdigest()
    papers=json.loads(path.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,papers))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    record=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),python=sys.version,argv=sys.argv,
        registry_sha256=before,results=results,
        scope='DOI/title metadata verification, not validation of article methods or original publication-version equivalence')
    (OUT/'registry_metadata_verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([dict(id=r['id'],status=r['status'],title=r.get('title')) for r in results],ensure_ascii=False))
    assert all(r['status'] in ('TITLE_MATCH','NO_DOI_DECLARED') for r in results)

if __name__=='__main__':main()
