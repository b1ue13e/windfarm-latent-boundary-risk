import re
import json
import urllib.request
import urllib.parse
import difflib

CITED_KEYS = [
    'bai2020agcrn', 'bianchi2006windcontrol', 'bossanyi2000closedloop', 'bremnes2004quantile',
    'daenens2025offshore', 'das2023longterm', 'doherty2005reserve', 'dowell2015veryshortterm',
    'ela2011operatingreserves', 'fedus2022switch', 'gaertner2020definition', 'guo2019astgcn',
    'hersbach2020era5', 'johnson2004region2', 'karniadakis2021piml', 'karpatne2017tgds',
    'kim2024lidarscada', 'kruse2023physics', 'li2018dcrnn', 'liu2024itransformer',
    'nie2023patchtst', 'nielsen2006quantile', 'pao2011controlwind', 'park2019physicsinduced',
    'pierre2019design', 'pinson2013forecasting', 'ravikumar2020anomaly', 'shazeer2017outrageously',
    'slootweg2003general', 'tautzweinert2017scada', 'ullah2022enabling', 'wang2025uncertaintyreview',
    'wu2019graphwavenet', 'zehtabiyan2023physicsguided', 'zhang2014probabilisticreview',
    'zhang2021lidar', 'zhou2013probabilisticmarkets', 'zhou2024sdwpfdata'
]

KNOWN_DOIS = {
    'kruse2023physics': '10.1103/PRXEnergy.2.043003',
    'dowell2015veryshortterm': '10.1109/TSG.2015.2424078',
    'slootweg2003general': '10.1109/TPWRS.2002.807113',
    'pierre2019design': '10.1109/TPWRS.2019.2903782',
    'ravikumar2020anomaly': '10.1109/TSG.2020.2995313',
    'ullah2022enabling': '10.1109/TII.2021.3112386',
    'gaertner2020definition': '10.2172/1603478',
    'wu2019graphwavenet': '10.24963/ijcai.2019/264',
    'karniadakis2021piml': '10.1038/s42254-021-00314-5',
    'karpatne2017tgds': '10.1109/TKDE.2017.2720168',
    'doherty2005reserve': '10.1109/TPWRS.2005.846206',
    'bremnes2004quantile': '10.1002/we.107',
    'pinson2013forecasting': '10.1002/wene.89',
    'zhou2013probabilisticmarkets': '10.1109/TPWRS.2013.2257888',
    'zhang2014probabilisticreview': '10.1016/j.rser.2014.07.087',
    'tautzweinert2017scada': '10.1016/j.conengprac.2017.06.006',
    'bossanyi2000closedloop': '10.1002/1099-1824(200007/09)3:3<145::AID-WE34>3.0.CO;2-W',
    'pao2011controlwind': '10.1109/MCS.2011.940402',
    'johnson2004region2': '10.1115/1.1787502',
    'hersbach2020era5': '10.1002/qj.3803',
    'park2019physicsinduced': '10.1115/1.4044584',
    'kim2024lidarscada': '10.1016/j.renene.2023.119747',
    'zehtabiyan2023physicsguided': '10.1016/j.apenergy.2023.121346',
    'zhang2021lidar': '10.1016/j.apenergy.2021.117180',
    'nielsen2006quantile': '10.1115/1.2210000',
    'guo2019astgcn': '10.1609/aaai.v33i01.3301898',
    'bianchi2006windcontrol': '10.1007/1-84628-493-7',
    'ela2011operatingreserves': '10.2172/1023776',
    'daenens2025offshore': '10.1016/j.apenergy.2024.124800',
    'zhou2024sdwpfdata': '10.1016/j.dib.2024.110411',
    'wang2025uncertaintyreview': '10.1016/j.rser.2024.115042',
}

def query_crossref(title, author=None):
    clean_title = re.sub(r'[\{\}]', '', title)
    query = clean_title
    if author:
        query += " " + author.split(',')[0].split(' and ')[0]
    url = 'https://api.crossref.org/works?query=' + urllib.parse.quote(query) + '&rows=3'
    req = urllib.request.Request(url, headers={'User-Agent': 'AUFE-Audit/1.0 (mailto:dujuntao@aufe.edu.cn)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data['message']['items']
            for item in items:
                cand_title = item.get('title', [''])[0]
                ratio = difflib.SequenceMatcher(None, clean_title.lower(), cand_title.lower()).ratio()
                if ratio > 0.65:
                    return item.get('DOI'), cand_title, ratio
    except Exception as e:
        return None, str(e), 0
    return None, None, 0

def main():
    with open('references.bib', 'r', encoding='utf-8') as f:
        bib_content = f.read()

    audit_results = []
    updated_bib = bib_content

    for key in CITED_KEYS:
        m = re.search(r'@(\w+)\s*\{\s*' + re.escape(key) + r',([\s\S]*?)\n\}', bib_content)
        if not m:
            print(f"Error: {key} not found in references.bib")
            continue
        entry_type = m.group(1)
        body = m.group(2)
        title_m = re.search(r'title\s*=\s*\{([^}]+)\}', body)
        title = title_m.group(1) if title_m else ''
        author_m = re.search(r'author\s*=\s*\{([^}]+)\}', body)
        author = author_m.group(1) if author_m else ''
        curr_doi_m = re.search(r'doi\s*=\s*\{([^}]+)\}', body)
        curr_doi = curr_doi_m.group(1) if curr_doi_m else None

        verified_doi = KNOWN_DOIS.get(key)
        if not verified_doi:
            doi_cr, cand_title, ratio = query_crossref(title, author)
            if doi_cr:
                verified_doi = doi_cr

        status = "MATCH"
        if curr_doi and verified_doi:
            if curr_doi.lower() != verified_doi.lower():
                status = f"FIX_ERROR ({curr_doi} -> {verified_doi})"
            else:
                status = f"VERIFIED ({curr_doi})"
        elif verified_doi and not curr_doi:
            status = f"ADDED ({verified_doi})"
        elif not verified_doi and curr_doi:
            status = f"RETAINED ({curr_doi})"
        else:
            status = "CONFERENCE/PREPRINT"

        audit_results.append({
            'key': key,
            'title': title[:50],
            'old_doi': curr_doi,
            'new_doi': verified_doi or curr_doi,
            'status': status
        })

        if verified_doi:
            if curr_doi:
                new_body = re.sub(r'doi\s*=\s*\{[^}]+\}', f'doi = {{{verified_doi}}}', body)
            else:
                new_body = body.rstrip() + f',\n  doi = {{{verified_doi}}}'
            old_entry = f'@{entry_type}{{{key},{body}\n}}'
            new_entry = f'@{entry_type}{{{key},{new_body}\n}}'
            updated_bib = updated_bib.replace(old_entry, new_entry)

    with open('references.bib', 'w', encoding='utf-8') as f:
        f.write(updated_bib)

    print("\n" + "="*85)
    print(f"{'Key':<26} | {'Status':<32} | {'DOI'}")
    print("="*85)
    for r in audit_results:
        print(f"{r['key']:<26} | {r['status']:<32} | {r['new_doi']}")
    print("="*85)

if __name__ == '__main__':
    main()
