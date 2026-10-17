import urllib.request
import urllib.parse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "literature/ieee_style_references"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_openalex_ieee(query_term, max_results=5):
    encoded_q = urllib.parse.quote(query_term)
    url = f"https://api.openalex.org/works?search={encoded_q}&filter=has_oa_accepted_or_published_version:true&per-page={max_results}&sort=relevance_score:desc"
    req = urllib.request.Request(url, headers=HEADERS)
    papers = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for item in data.get('results', []):
                title = item.get('title', '')
                doi = item.get('doi', '')
                year = item.get('publication_year')
                source = item.get('primary_location', {}).get('source', {}) or {}
                venue = source.get('display_name', '')
                best_oa = item.get('best_oa_location', {}) or {}
                pdf_url = best_oa.get('pdf_url', '')
                if not pdf_url:
                    pdf_url = item.get('open_access', {}).get('oa_url', '')
                
                # Check all locations if best_oa lacks direct pdf
                if not pdf_url or not pdf_url.endswith('.pdf'):
                    for loc in item.get('locations', []):
                        u = loc.get('pdf_url')
                        if u and u.endswith('.pdf'):
                            pdf_url = u
                            break

                authors = [a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])]
                papers.append({
                    'title': title,
                    'doi': doi,
                    'year': year,
                    'venue': venue,
                    'pdf_url': pdf_url,
                    'authors': authors
                })
    except Exception as e:
        print(f"Error querying OpenAlex: {e}")
    return papers

def download_pdf(url, dest_path):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if len(content) > 20000 and content.startswith(b'%PDF'):
                dest_path.write_bytes(content)
                return True, len(content)
            else:
                return False, f"Not a valid PDF (len={len(content)}, header={content[:10]})"
    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    queries = [
        "IEEE Transactions Sustainable Energy wind power reserve quantile",
        "IEEE Transactions Power Systems wind reserve sizing risk",
        "IEEE Transactions Sustainable Energy wind telemetry degraded missing",
        "probabilistic wind power forecasting conditional quantile IEEE Transactions"
    ]
    
    downloaded = []
    for q in queries:
        print(f"\n--- Searching: {q} ---")
        papers = search_openalex_ieee(q, max_results=6)
        for p in papers:
            title = p['title']
            venue = p['venue']
            pdf_url = p['pdf_url']
            doi = p['doi']
            year = p['year']
            print(f"Candidate: {title} ({year}) [{venue}]")
            print(f"  PDF: {pdf_url}")
            
            if not pdf_url or not (pdf_url.startswith('http://') or pdf_url.startswith('https://')):
                continue
                
            safe_title = "".join(c for c in title[:40] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            filename = f"{year}_{safe_title}.pdf"
            dest = OUT_DIR / filename
            
            if dest.exists() and dest.stat().st_size > 20000:
                print(f"  -> Already exists: {dest.name}")
                downloaded.append((title, venue, year, dest, doi))
                continue
                
            print(f"  -> Downloading to {dest.name}...")
            ok, msg = download_pdf(pdf_url, dest)
            if ok:
                print(f"  -> SUCCESS ({msg / 1024:.1f} KB)")
                downloaded.append((title, venue, year, dest, doi))
                time.sleep(1)
            else:
                print(f"  -> FAILED: {msg}")
                if dest.exists():
                    dest.unlink()
            
            if len(downloaded) >= 5:
                break
        if len(downloaded) >= 5:
            break

    print(f"\n==========================================")
    print(f"Total verified downloaded PDFs: {len(downloaded)}")
    for t, v, y, p, d in downloaded:
        print(f"- {y} | {t} | {v} | {p.name} ({p.stat().st_size / 1024:.1f} KB)")
