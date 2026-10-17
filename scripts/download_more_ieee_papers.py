import urllib.request
import urllib.parse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "literature/ieee_style_references"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "AcademicResearchAgent/2.0 (mailto:wind-reserve-research@edu.cn)"
}

def download_file(url, target_path):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if len(content) > 30000 and content.startswith(b'%PDF'):
                target_path.write_bytes(content)
                return True, len(content)
            else:
                return False, f"Invalid PDF (len={len(content)})"
    except Exception as e:
        return False, str(e)

# Direct known high-impact open access IEEE TSTE/TPWRS/PES papers and matched preprints
# 1. "Data-Driven Robust Operating Reserve Sizing with High Wind Power Penetration" (IEEE TPWRS / TSTE)
# 2. "Probabilistic Wind Power Forecasting Using Copula-Based Quantile Regression" (IEEE TSTE)
# 3. "Spatio-Temporal Wind Power Forecasting: From Physics-Informed to Deep Learning" (IEEE Transactions)
# 4. "Reserve Sizing with Conditional Quantile Forecasts of Wind Power"

candidates = [
    {
        "title": "Robust Operating Reserve Sizing for Wind-Integrated Power Systems",
        "search_term": "Robust Operating Reserve Sizing wind power IEEE Transactions on Power Systems",
    },
    {
        "title": "Probabilistic Wind Power Forecasting Using Nonparametric Quantile Regression",
        "search_term": "probabilistic wind power forecasting quantile regression IEEE Transactions on Sustainable Energy",
    },
    {
        "title": "Spatio-Temporal Graph Neural Networks for Wind Power Forecasting",
        "search_term": "spatio-temporal graph neural networks wind power forecasting IEEE Transactions on Sustainable Energy",
    },
    {
        "title": "Operational Reserve Allocation Under Wind Generation Uncertainty",
        "search_term": "operating reserve allocation wind uncertainty IEEE Transactions on Power Systems",
    }
]

print("Searching and downloading target IEEE papers...")
downloaded_count = 0

for item in candidates:
    term = item["search_term"]
    encoded = urllib.parse.quote(term)
    url = f"https://api.openalex.org/works?search={encoded}&filter=has_oa_accepted_or_published_version:true&per-page=5"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])
            for res in results:
                title = res.get('title', '')
                year = res.get('publication_year', 2020)
                venue = (res.get('primary_location', {}).get('source', {}) or {}).get('display_name', '')
                locations = res.get('locations', [])
                pdf_url = None
                for loc in locations:
                    u = loc.get('pdf_url')
                    if u and u.startswith('http') and ('.pdf' in u or 'download' in u or 'bitstream' in u or 'openaccess' in u):
                        pdf_url = u
                        break
                if not pdf_url:
                    u = res.get('open_access', {}).get('oa_url', '')
                    if u and u.startswith('http'):
                        pdf_url = u
                        
                if pdf_url:
                    safe_title = "".join(c for c in title[:45] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                    fname = f"{year}_{safe_title}.pdf"
                    target = OUT_DIR / fname
                    if target.exists() and target.stat().st_size > 30000:
                        print(f"Already exists: {fname}")
                        downloaded_count += 1
                        break
                    print(f"Found: {title} ({year}) [{venue}]")
                    print(f"  Attempting download from: {pdf_url}")
                    ok, msg = download_file(pdf_url, target)
                    if ok:
                        print(f"  -> SUCCESS: {fname} ({msg/1024:.1f} KB)")
                        downloaded_count += 1
                        time.sleep(1)
                        break
                    else:
                        print(f"  -> Failed: {msg}")
                        if target.exists(): target.unlink()
    except Exception as e:
        print(f"Error for term '{term}': {e}")
    time.sleep(1)

print(f"\nFinished. Total in {OUT_DIR}: {len(list(OUT_DIR.glob('*.pdf')))} PDFs.")
