import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time
from pathlib import Path

NS = "{http://www.w3.org/2005/Atom}"

def search_arxiv(query, max_results=10):
    encoded_query = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_data = resp.read()
    root = ET.fromstring(xml_data)
    papers = []
    for entry in root.findall(f"{NS}entry"):
        aid = entry.findtext(f"{NS}id", "").split("/abs/")[-1].split("v")[0]
        title = (entry.findtext(f"{NS}title", "") or "").strip().replace("\n", " ")
        summary = (entry.findtext(f"{NS}summary", "") or "").strip().replace("\n", " ")
        authors = [a.findtext(f"{NS}name", "") for a in entry.findall(f"{NS}author")]
        published = entry.findtext(f"{NS}published", "")[:10]
        journal_ref = entry.findtext("{http://arxiv.org/schemas/atom}journal_ref", "")
        comment = entry.findtext("{http://arxiv.org/schemas/atom}comment", "")
        pdf_url = f"https://arxiv.org/pdf/{aid}.pdf"
        papers.append({
            "id": aid,
            "title": title,
            "summary": summary,
            "authors": authors,
            "published": published,
            "journal_ref": journal_ref,
            "comment": comment,
            "pdf_url": pdf_url
        })
    return papers

if __name__ == "__main__":
    queries = [
        'all:"wind power" AND all:"reserve sizing" AND all:"quantile"',
        'all:"operating reserve" AND all:"wind" AND all:"probabilistic"',
        'all:"wind power" AND all:"spatio-temporal" AND all:"graph" AND all:"quantile"',
        'all:"SCADA" AND all:"wind" AND all:"missing" OR all:"delay" AND all:"power"'
    ]
    all_papers = {}
    for q in queries:
        print(f"Searching: {q}")
        try:
            res = search_arxiv(q, max_results=5)
            for p in res:
                all_papers[p["id"]] = p
            time.sleep(1)
        except Exception as e:
            print(f"Error on {q}: {e}")

    print(f"Total unique papers found: {len(all_papers)}")
    for aid, p in list(all_papers.items())[:10]:
        print(f"[{aid}] {p['title'][:80]}... ({p['published']}) [Journal/Comment: {p['journal_ref'] or p['comment']}]")
