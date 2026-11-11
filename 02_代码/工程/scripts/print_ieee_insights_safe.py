import json
import sys
from repo_paths import Path, repository_root

# Force utf-8 standard output
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(repository_root())
data = json.loads((ROOT / 'literature/extracted_ieee_insights.json').read_text(encoding='utf-8'))

for tag, info in data.items():
    print("=" * 75)
    print(f"TAG: {tag} | File: {info.get('filename')} | Pages: {info.get('num_pages')}")
    print("\n--- FRONT SECTION (Title, Abstract, Intro start) ---")
    txt = info.get('start_excerpt', '').encode('utf-8', errors='ignore').decode('utf-8')
    # print up to 1200 chars
    print(txt[:1200])
    print("\n--- CONCLUDING SECTION (Conclusion, Discussions) ---")
    txt_end = info.get('end_excerpt', '').encode('utf-8', errors='ignore').decode('utf-8')
    print(txt_end[:800])
