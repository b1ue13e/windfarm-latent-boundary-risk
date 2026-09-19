import re
import sys
from pathlib import Path

files = ['paper_tste_ieee.md', 'paper_tste_supplementary.md', 'standalone_ieee_package/main.tex']

patterns = {
    'strictly mandates': re.compile(r'strictly\s+mandates', re.I),
    'proving that generic': re.compile(r'proving\s+that\s+generic', re.I),
    'only for language editing': re.compile(r'only\s+for\s+language\s+editing', re.I),
    'p<0.05 paired with 0.062': re.compile(r'p\s*<\s*0\.05.*0\.062|0\.062.*p\s*<\s*0\.05', re.I),
    'p<0.01': re.compile(r'p\s*<\s*0\.01', re.I),
    'compliant / compliance': re.compile(r'\bcomplian(ce|t)\b', re.I),
    'requires local retraining': re.compile(r'requires\s+local\s+retraining', re.I),
    'mandates local retraining': re.compile(r'mandates\s+local\s+retraining', re.I),
    'graph convolutions overfit': re.compile(r'graph\s+convolutions?\s+overfit', re.I),
    'overfit localized terrain': re.compile(r'overfits?\s+localized\s+terrain', re.I),
    'overfit localized topography': re.compile(r'overfits?\s+localized\s+topography', re.I),
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
            print(f'  [INFO] Found {len(matches)} occurrences of "p<0.01":')
            for m in matches:
                start = max(0, m.start() - 50)
                end = min(len(content), m.end() + 50)
                snippet = content[start:end].replace('\n', ' ')
                print(f'    ...{snippet}...')
        else:
            if matches:
                print(f'  [FAIL] Found {len(matches)} matches for "{name}":')
                all_clean = False
                for m in matches:
                    start = max(0, m.start() - 50)
                    end = min(len(content), m.end() + 50)
                    snippet = content[start:end].replace('\n', ' ')
                    print(f'    ...{snippet}...')
            else:
                print(f'  [PASS] {name}: 0 matches')

# Check required phrases across main, supplementary, and standalone package
main_text = Path('paper_tste_ieee.md').read_text(encoding='utf-8')
supp_text = Path('paper_tste_supplementary.md').read_text(encoding='utf-8')
pkg_text = Path('standalone_ieee_package/main.tex').read_text(encoding='utf-8')

# 1. ABSTRACT BASELINE SCOPE check
abstract_scope_pat = re.compile(
    r'Relative\s+to\s+the\s+unadapted\s+physical\s+comparator\s+under\s+pitch\s+withholding,\s+'
    r'learned\s+representations\s+reduce\s+the\s+reserve-screening\s+surrogate\s+by\s+'
    r'.*?46\.7.*?68\.6.*?across\s+evaluated\s+latencies;\s+'
    r'however,\s+strong\s+wind-speed-conditioned\s+quantiles\s+remain\s+lower-cost\s+plant-wide\.',
    re.I | re.DOTALL
)
if abstract_scope_pat.search(main_text) and abstract_scope_pat.search(pkg_text):
    print('\nABSTRACT BASELINE SCOPE: PASS')
else:
    print('\nABSTRACT BASELINE SCOPE: FAIL')
    all_clean = False

# 2. NEWSVENDOR TARGET WORDING check
newsvendor_compliant_pat = re.compile(r'\bcomplian(ce|t)\b', re.I)
if (not newsvendor_compliant_pat.search(main_text) and
    not newsvendor_compliant_pat.search(supp_text) and
    not newsvendor_compliant_pat.search(pkg_text)):
    print('NEWSVENDOR TARGET WORDING: PASS')
else:
    print('NEWSVENDOR TARGET WORDING: FAIL')
    all_clean = False

# 3. CROSS-SITE CAUSAL WORDING check
req_asym_phrase = re.compile(
    r'directional\s+transfer\s+asymmetry.*?supports\s+site-specific\s+retraining\s+or\s+recalibration\s+rather\s+than\s+assuming\s+reliable\s+zero-shot\s+transfer',
    re.I | re.DOTALL
)
req_lhb_phrase = re.compile(
    r'LHB\s+exhibits\s+a\s+negative\s+transfer/overfitting\s+boundary,\s*consistent\s+with\s+limited\s+exploitable\s+spatial\s+redundancy\s+and\s+site-specific\s+heterogeneity',
    re.I | re.DOTALL
)

if (req_asym_phrase.search(main_text) and req_lhb_phrase.search(main_text) and
    req_asym_phrase.search(pkg_text) and req_lhb_phrase.search(pkg_text) and
    req_asym_phrase.search(supp_text) and req_lhb_phrase.search(supp_text)):
    print('CROSS-SITE CAUSAL WORDING: PASS')
else:
    print('CROSS-SITE CAUSAL WORDING: FAIL')
    all_clean = False

if all_clean:
    print('\nOVERALL CONSISTENCY CHECK: PASS')
    sys.exit(0)
else:
    print('\nOVERALL CONSISTENCY CHECK: FAIL')
    sys.exit(1)
