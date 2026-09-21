import sys
import os
import re
import pypdf

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def audit_main_ieee_pdf(pdf_path: str):
    print(f'=== Auditing Main IEEE PDF: {pdf_path} ===')
    assert os.path.exists(pdf_path), f'File not found: {pdf_path}'
    
    reader = pypdf.PdfReader(pdf_path)
    num_pages = len(reader.pages)
    print(f'Total pages: {num_pages}')
    if num_pages > 10:
        raise AssertionError(f'Page budget violation: {num_pages} pages > 10 pages maximum!')
    
    full_text = ''
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ''
        full_text += f'\n--- PAGE {i+1} ---\n' + page_text
        
    required_phrase_specs = [
        ('13,883', [r'13,883']),
        ('boundary-active', [r'boundary-active']),
        ('site-dependent', [r'site-dependent']),
        ('not turbine count alone / turbine count alone does not explain', [r'not\s+turbine\s+count\s+alone', r'turbine\s+count\s+alone\s+does\s+not\s+explain']),
        ('explicit disclosure that pitch is available in training inputs but withheld in validation/test deployment', [r'explicit\s+disclosure\s+that\s+pitch\s+is\s+available\s+in\s+training\s+inputs\s+but\s+(?:withheld|with-\s*held)\s+in\s+validation/test\s+deployment', r'explicit\s+disclosure\s+that\s+pitch\s+is\s+available\s+in\s+training\s+inputs\s+but\s+withheld\s+in\s+validation/test\s+deployment'])
    ]
    
    print('\n--- Checking Required Phrases ---')
    missing = []
    for label, patterns in required_phrase_specs:
        matched = False
        for pat in patterns:
            pattern = re.compile(pat, re.IGNORECASE)
            if pattern.search(full_text):
                matched = True
                break
        if matched:
            print(f'  [PASS] Found required phrase match: {label!r}')
        else:
            print(f'  [FAIL] Missing required phrase: {label!r}')
            missing.append(label)
            
    if missing:
        raise AssertionError(f'Missing required phrases in PDF: {missing}')
        
    banned_phrases = [
        'Commercial benefit',
        'N < 20',
        'N >= 50',
        'N <= 6',
        'N >= 14',
        'decision value is maximized'
    ]
    
    print('\n--- Checking Banned Phrases ---')
    found_banned = []
    for phrase in banned_phrases:
        pattern = re.compile(re.escape(phrase).replace(r'\ ', r'\s+'), re.IGNORECASE)
        match = pattern.search(full_text)
        if match:
            print(f'  [FAIL] Found banned phrase: {phrase!r} at pos {match.start()}')
            found_banned.append(phrase)
        else:
            print(f'  [PASS] Confirmed absent: {phrase!r}')
            
    if found_banned:
        raise AssertionError(f'Banned phrases present in PDF: {found_banned}')
        
    print('\n--- Checking Headline Number Proximity Qualifiers ---')
    numbers = ['589,535', '881,367']
    for num in numbers:
        pattern = re.compile(re.escape(num))
        matches = list(pattern.finditer(full_text))
        print(f'Number {num} found {len(matches)} times:')
        for idx, m in enumerate(matches, 1):
            start = max(0, m.start() - 250)
            end = min(len(full_text), m.end() + 250)
            window = full_text[start:end]
            has_qualifier = ('13,883' in window) or ('boundary' in window.lower())
            status = 'PASS' if has_qualifier else 'FAIL'
            print(f'  [{status}] Occurrence #{idx} at index {m.start()}: qualifier present={has_qualifier}')
            if not has_qualifier:
                print(f'    Snippet without qualifier: {window!r}')
                raise AssertionError(f'Number {num} appears without adjacent boundary/13,883 qualifier!')
                
    print('\n[ALL IEEE PDF CHECKS PASSED]')

def audit_supplementary_pdf(pdf_path: str):
    print(f'\n=== Auditing Supplementary PDF: {pdf_path} ===')
    assert os.path.exists(pdf_path), f'File not found: {pdf_path}'
    
    reader = pypdf.PdfReader(pdf_path)
    print(f'Total pages: {len(reader.pages)}')
    
    full_text = ''
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ''
        full_text += f'\n--- PAGE {i+1} ---\n' + page_text
        
    banned_supp = [
        'economic reserve benefit',
        'economic value',
        'reserve pricing',
        'Commercial benefit'
    ]
    
    print('\n--- Checking Banned Phrases in Supplementary ---')
    found_banned = []
    for phrase in banned_supp:
        pattern = re.compile(re.escape(phrase).replace(r'\ ', r'\s+'), re.IGNORECASE)
        matches = list(pattern.finditer(full_text))
        if matches:
            print(f'  [FAIL] Found banned phrase: {phrase!r} ({len(matches)} occurrences)')
            found_banned.append(phrase)
        else:
            print(f'  [PASS] Confirmed absent: {phrase!r}')
            
    if found_banned:
        raise AssertionError(f'Banned phrases present in Supplementary PDF: {found_banned}')
        
    print('\n[ALL SUPPLEMENTARY PDF CHECKS PASSED]')

if __name__ == '__main__':
    main_pdf = 'build/paper_tste_ieee.pdf'
    supp_pdf = 'build/paper_tste_supplementary.pdf'
    
    try:
        audit_main_ieee_pdf(main_pdf)
        audit_supplementary_pdf(supp_pdf)
        print('\n=======================================================')
        print('VERIFICATION SUCCESS: ALL PDF ARTIFACT INTEGRITY CHECKS PASSED')
        print('=======================================================')
        sys.exit(0)
    except AssertionError as e:
        print(f'\n[VERIFICATION ERROR] {e}', file=sys.stderr)
        sys.exit(1)
