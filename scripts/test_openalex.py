import urllib.request
import urllib.parse
import json
import time
from pathlib import Path

# OpenAlex API is completely free and open, with no harsh rate limits for research
def search_openalex(query, max_results=5):
    encoded = urllib.parse.quote(query)
    url = f"https://api.openalex.org/works?search={encoded}&per-page={max_results}&filter=has_oa_accepted_or_published_version:true"
    headers = {"User-Agent": "AcademicResearchAgent/1.0 (mailto:academic-research@univ.edu)"}
    req = urllib.request.Request(url, headers=headers)
    papers = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for item in data.get('results', []):
                title = item.get('title', '')
                doi = item.get('doi', '')
                pub_year = item.get('publication_year')
                host_venue = item.get('primary_location', {}).get('source', {}).get('display_name', '')
                oa_url = item.get('open_access', {}).get('oa_url', '')
                best_oa = item.get('best_oa_location', {}) or {}
                pdf_url = best_oa.get('pdf_url', '') or oa_url
                authors = [a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])]
                papers.append({
                    'title': title,
                    'doi': doi,
                    'year': pub_year,
                    'venue': host_venue,
                    'pdf_url': pdf_url,
                    'authors': authors
                })
    except Exception as e:
        print(f"Error querying OpenAlex: {e}")
    return papers

if __name__ == '__main__':
    q = "wind power reserve sizing quantile regression IEEE"
    print(f"Searching OpenAlex for: {q}")
    results = search_openalex(q, 6)
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']} ({r['year']}) - Venue: {r['venue']}")
        print(f"    DOI: {r['doi']}")
        print(f"    PDF URL: {r['pdf_url']}")
