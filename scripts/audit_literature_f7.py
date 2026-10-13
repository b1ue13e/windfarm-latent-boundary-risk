#!/usr/bin/env python3
"""
F7 Issue Forensic Audit Script:
1. Verify DOI-to-title mismatches in literature/literature_matrix.csv
2. Inspect literature/top_journal_papers/*.pdf for generated "Literature Benchmark Brief" covers
3. Verify arXiv:2405.01234 mismatch in docs/MIMIR_INGESTION_AND_AUDIT_REPORT.md and research_wiki.json
"""

import os
import sys
import csv
import json
import urllib.request
import xml.etree.ElementTree as ET
import pypdf

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def audit_doi_title_mismatches():
    csv_path = os.path.join(REPO_ROOT, "literature", "literature_matrix.csv")
    if not os.path.exists(csv_path):
        print(f"[ERROR] {csv_path} not found.")
        return []

    target_rows = [2, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 25, 27, 28, 29, 30, 31, 32, 33]
    mismatches = []
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            if idx in target_rows:
                doi = row.get("doi", "").strip()
                csv_title = row.get("title", "").strip()
                paper_id = row.get("paper_id", "").strip()
                
                # Query CrossRef API
                real_title = None
                crossref_url = f"https://api.crossref.org/works/{doi}"
                req = urllib.request.Request(
                    crossref_url,
                    headers={"User-Agent": "ResearchAudit/1.0 (mailto:audit@example.org)"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        titles = data.get("message", {}).get("title", [])
                        if titles:
                            real_title = titles[0].strip()
                except Exception as e:
                    real_title = f"FETCH_ERROR ({e})"
                
                is_match = False
                if real_title and not real_title.startswith("FETCH_ERROR"):
                    clean_csv = "".join(c for c in csv_title.lower() if c.isalnum())
                    clean_real = "".join(c for c in real_title.lower() if c.isalnum())
                    is_match = (clean_csv in clean_real or clean_real in clean_csv)
                
                mismatches.append({
                    "row": idx,
                    "paper_id": paper_id,
                    "doi": doi,
                    "csv_title": csv_title,
                    "real_title": real_title,
                    "is_match": is_match
                })
    return mismatches

def audit_pdf_assets():
    pdf_dir = os.path.join(REPO_ROOT, "literature", "top_journal_papers")
    if not os.path.exists(pdf_dir):
        print(f"[ERROR] {pdf_dir} not found.")
        return []

    results = []
    pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])
    for fname in pdf_files:
        fpath = os.path.join(pdf_dir, fname)
        is_brief = False
        first_page_text = ""
        try:
            reader = pypdf.PdfReader(fpath)
            if len(reader.pages) > 0:
                first_page_text = reader.pages[0].extract_text() or ""
                if "Literature Benchmark Brief" in first_page_text or "Benchmark Brief" in first_page_text:
                    is_brief = True
        except Exception as e:
            first_page_text = f"READ_ERROR: {e}"
        
        results.append({
            "filename": fname,
            "is_brief": is_brief,
            "snippet": first_page_text[:150].replace("\n", " ")
        })
    return results

def audit_arxiv_2405_01234():
    arxiv_id = "2405.01234"
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "ResearchAudit/1.0"})
    real_title = None
    real_summary = None
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read().decode("utf-8")
            root = ET.fromstring(xml_data)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")
            if entry is not None:
                real_title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip().replace("\n", " ")
                real_summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip().replace("\n", " ")
    except Exception as e:
        real_title = f"FETCH_ERROR: {e}"
    
    return {
        "arxiv_id": arxiv_id,
        "real_title": real_title,
        "real_summary": real_summary
    }

if __name__ == "__main__":
    print("=== 1. Checking arXiv:2405.01234 ===")
    arxiv_res = audit_arxiv_2405_01234()
    print(f"ID: {arxiv_res['arxiv_id']}")
    print(f"Real Title: {arxiv_res['real_title']}")
    print(f"Real Summary: {arxiv_res['real_summary'][:200]}...")
    
    print("\n=== 2. Auditing literature/top_journal_papers PDFs ===")
    pdf_results = audit_pdf_assets()
    total_pdfs = len(pdf_results)
    brief_count = sum(1 for r in pdf_results if r["is_brief"])
    print(f"Total PDFs: {total_pdfs}")
    print(f"PDFs with 'Literature Benchmark Brief' first page: {brief_count}")
    print(f"Original/External PDFs: {total_pdfs - brief_count}")
    
    print("\n=== 3. Auditing literature/literature_matrix.csv DOI Mismatches ===")
    mismatches = audit_doi_title_mismatches()
    mismatch_count = sum(1 for m in mismatches if not m["is_match"])
    print(f"Audited Target Rows: {len(mismatches)}")
    print(f"Confirmed Mismatched / Problematic Rows: {mismatch_count}")
    for m in mismatches:
        status = "MATCH" if m["is_match"] else "MISMATCH"
        print(f"Row {m['row']:2d} [{status}]: {m['paper_id']}")
        print(f"  CSV Title : {m['csv_title']}")
        print(f"  Real Title: {m['real_title']}")
        print(f"  DOI       : {m['doi']}")
