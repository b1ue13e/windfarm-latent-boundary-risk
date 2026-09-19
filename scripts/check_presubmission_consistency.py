import re
import sys
from pathlib import Path

files = ['paper_tste_ieee.md', 'paper_tste_supplementary.md', 'standalone_ieee_package/main.tex']

patterns = {
    'strictly mandates': re.compile(r'strictly mandates', re.I),
    'proving that generic': re.compile(r'proving that generic', re.I),
    'only for language editing': re.compile(r'only for language editing', re.I),
    'p<0.05 paired with 0.062': re.compile(r'p\s*<\s*0\.05.*0\.062|0\.062.*p\s*<\s*0\.05', re.I),
    'p<0.01': re.compile(r'p\s*<\s*0\.01', re.I),
}

all_clean = True
for fname in files:
    path = Path(fname)
    if not path.exists():
        continue
    content = path.read_text(encoding='utf-8')
    print(f'=== Checking {fname} ===')
    for name, pat in patterns.items():
        matches = list(pat.finditer(content))
        if name == 'p<0.01':
            # Report provenance for every p<0.01 occurrence
            print(f'  [INFO] Found {len(matches)} occurrences of \"p<0.01\":')
            for m in matches:
                start = max(0, m.start() - 50)
                end = min(len(content), m.end() + 50)
                snippet = content[start:end].replace('\n', ' ')
                print(f'    ...{snippet}...')
        else:
            if matches:
                print(f'  [FAIL] Found {len(matches)} matches for \"{name}\":')
                all_clean = False
                for m in matches:
                    start = max(0, m.start() - 50)
                    end = min(len(content), m.end() + 50)
                    snippet = content[start:end].replace('\n', ' ')
                    print(f'    ...{snippet}...')
            else:
                print(f'  [PASS] {name}: 0 matches')

if all_clean:
    print('\nOVERALL CONSISTENCY CHECK: PASS')
    sys.exit(0)
else:
    print('\nOVERALL CONSISTENCY CHECK: FAIL')
    sys.exit(1)
