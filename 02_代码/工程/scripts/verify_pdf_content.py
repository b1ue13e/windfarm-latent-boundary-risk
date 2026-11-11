import os
import sys
import subprocess
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

root = str(os.environ.get("WINDFARM_REPO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
source_path = os.path.join(root, 'paper_tste_ieee.md')
pdf_paths = [
    os.path.join(root, 'build', 'paper_tste_ieee.pdf'),
    os.path.join(root, 'paper_tste_ieee.pdf'),
    os.path.join(root, 'standalone_ieee_package', 'main.pdf'),
    os.path.join(root, 'artifacts', 'tste_submission_package_ready', '01_MANUSCRIPT_PDF', 'manuscript_ieee_tste.pdf'),
]

print("=" * 70)
print("1. CURRENT GIT COMMIT HASH")
print("=" * 70)
res = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True)
print(res.stdout.strip())

print("\n" + "=" * 70)
print("2. EXACT ABSOLUTE PATH OF THE SOURCE FILE BEING COMPILED")
print("=" * 70)
print(source_path)

print("\n" + "=" * 70)
print("3. ACTUAL TITLE LINE FROM SOURCE")
print("=" * 70)
with open(source_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('\\title{'):
            print(line.strip())

print("\n" + "=" * 70)
print("4. ALL SECTION III-VII HEADINGS FROM SOURCE")
print("=" * 70)
with open(source_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        s = line.strip()
        if s.startswith('# ') or s.startswith('## '):
            if any(k in s for k in [
                'Problem Formulation', 'Level-1', 'Latent Operating', 'Aerodynamic Power',
                'Non-Neural', 'Latent State Recovery', 'Reserve-Tail', 'Architecture Variants',
                'Case Study', 'Datasets', 'Controlled Telemetry', 'Pre-Dispatch Risk Screening Framework',
                'Empirical Findings', 'Result 1', 'Result 2', 'Result 3', 'Result 4', 'Result 5', 'Result 6', 'Result 7',
                'Discussion', 'Limitations', 'Conclusion'
            ]):
                print(f"Line {i+1}: {s}")

print("\n" + "=" * 70)
print("5. SEARCH SOURCE FOR REQUIRED PHRASES")
print("=" * 70)
with open(source_path, 'r', encoding='utf-8') as f:
    src_text = f.read()

phrases = [
    "Price of Routing",
    "AGAINST STGQ-ROUTED",
    "Comparative Architecture Analysis",
    "When Aerodynamic States Become Latent"
]
for p in phrases:
    exact = src_text.count(p)
    ci = src_text.lower().count(p.lower())
    print(f"Phrase: '{p}' -> Exact: {exact}, Case-Insensitive: {ci}")

print("\n" + "=" * 70)
print("6. EXTRACT FIRST PAGE TEXT & SECTION V HEADINGS FROM NEW PDF")
print("=" * 70)
for pdf_path in pdf_paths:
    if not os.path.exists(pdf_path):
        print(f"MISSING: {pdf_path}")
        continue
    print(f"\n--- Checking: {pdf_path} ---")
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    p1 = reader.pages[0].extract_text()
    print("Page 1 Title Snippet:")
    lines = [l.strip() for l in p1.split('\n') if l.strip()]
    for l in lines[:6]:
        print("  ", l)
    
    print("\nSection V Headings Extracted from PDF:")
    full_pdf_text = ""
    for p_idx, page in enumerate(reader.pages):
        txt = page.extract_text()
        full_pdf_text += "\n" + txt
        for l in txt.split('\n'):
            s = l.strip()
            if 'Result ' in s or 'EMPIRICAL FINDINGS' in s.upper():
                print(f"  Page {p_idx+1}: {s}")

    print("\nPhrase search in compiled PDF:")
    for p in phrases:
        ci_found = p.lower() in full_pdf_text.lower()
        exact_found = p in full_pdf_text
        print(f"  '{p}' -> Exact: {exact_found}, Case-Insensitive: {ci_found}")

print("\n" + "=" * 70)
print("VERIFICATION SUMMARY COMPLETED")
print("=" * 70)
