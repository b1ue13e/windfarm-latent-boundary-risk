import re, urllib.request, urllib.parse, json, time, socket

socket.setdefaulttimeout(4)

with open('references.bib', 'r', encoding='utf-8') as fb:
    bib_text = fb.read()

with open('paper_tste_ieee.md', 'r', encoding='utf-8') as fm:
    text_main = fm.read()
with open('paper_tste_supplementary.md', 'r', encoding='utf-8') as fs:
    text_supp = fs.read()

cites_main = set(re.findall(r'@([a-zA-Z0-9_-]+)', text_main)) - {'aufe', 'startsection'}
cites_supp = set(re.findall(r'@([a-zA-Z0-9_-]+)', text_supp)) - {'aufe', 'startsection', '0', '100'}
all_cites = sorted(cites_main | cites_supp)

blocks = re.split(r'\n@', bib_text)
entries = {}
for block in blocks:
    block = block.strip()
    if not block:
        continue
    if not block.startswith('@'):
        block = '@' + block
    m = re.match(r'@(\w+)\s*\{\s*([^,]+),', block)
    if not m:
        continue
    etype, key = m.groups()
    tm = re.search(r'title\s*=\s*\{([^\{\}]+(?:\{[^\}]+\}[^\{\}]*)*)\}', block)
    am = re.search(r'author\s*=\s*\{([^\{\}]+(?:\{[^\}]+\}[^\{\}]*)*)\}', block)
    vm = re.search(r'(journal|booktitle|publisher|institution)\s*=\s*\{([^\{\}]+(?:\{[^\}]+\}[^\{\}]*)*)\}', block)
    dm = re.search(r'doi\s*=\s*\{([^\{\}]+)\}', block)
    ym = re.search(r'year\s*=\s*\{([^\{\}]+)\}', block)
    entries[key] = {
        'type': etype,
        'key': key,
        'title': tm.group(1).replace('{', '').replace('}', '') if tm else '',
        'author': am.group(1) if am else '',
        'venue': vm.group(2) if vm else '',
        'doi': dm.group(1) if dm else '',
        'year': ym.group(1) if ym else ''
    }

def query_crossref(title, author=''):
    q = title + ' ' + author.split(',')[0]
    encoded_q = urllib.parse.quote(q.strip())
    url = 'https://api.crossref.org/works?query.bibliographic=' + encoded_q + '&rows=2'
    req = urllib.request.Request(url, headers={'User-Agent': 'BibAuditor/2.0 (mailto:academic_verify@example.com)'})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('message', {}).get('items', [])
            if items:
                top = items[0]
                return {
                    'doi': top.get('DOI', ''),
                    'container': (top.get('container-title') or [''])[0],
                    'title': (top.get('title') or [''])[0],
                    'volume': top.get('volume', ''),
                    'issue': top.get('issue', ''),
                    'page': top.get('page', ''),
                    'year': (top.get('issued', {}).get('date-parts') or [[None]])[0][0],
                    'type': top.get('type', ''),
                    'publisher': top.get('publisher', '')
                }
    except Exception as e:
        return {'error': str(e)}
    return {}

# clear jsonl
with open('scripts/bib_audit_results.jsonl', 'w', encoding='utf-8') as f:
    pass

results = []
for idx, key in enumerate(all_cites):
    entry = entries.get(key)
    if not entry:
        continue
    title = entry['title']
    author = entry['author']
    cr = query_crossref(title, author)
    res = {
        'idx': idx + 1,
        'key': key,
        'entry_type': entry['type'],
        'bib_title': title,
        'bib_author': author,
        'bib_venue': entry['venue'],
        'bib_doi': entry['doi'],
        'bib_year': entry['year'],
        'cr': cr
    }
    results.append(res)
    with open('scripts/bib_audit_results.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(res, ensure_ascii=False) + '\n')
    
    cr_doi = cr.get('doi', 'NO_DOI')
    cr_venue = cr.get('container') or cr.get('publisher') or 'NO_VENUE'
    status = 'MATCH' if (entry['doi'] and entry['doi'].lower() == cr_doi.lower()) else 'MISMATCH/NEW'
    print(f'[{idx+1:02d}/{len(all_cites)}] {key:25} | {status:12} | BIB: {entry["venue"][:18]} / {entry["doi"][:20]} | CR: {cr_venue[:20]} / {cr_doi}', flush=True)
    time.sleep(0.05)

with open('scripts/bib_audit_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print('Audit complete, written to scripts/bib_audit_results.json', flush=True)
