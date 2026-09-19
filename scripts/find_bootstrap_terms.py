import os
import re

patterns = [
    r'day-block', r'day block', r'1,?000\s*day', r'B\s*=\s*1,?000',
    r'bootstrap.*resample', r'resample.*bootstrap', r'cluster.*bootstrap',
    r'block.*bootstrap'
]

regex = re.compile('|'.join(patterns), re.IGNORECASE)

matches = []
TARGET_DIRS = ['docs', 'scripts', 'standalone_ieee_package']
ROOT_FILES = ['paper_tste_ieee.md', 'paper_tste_supplementary.md', 'DECISIVE_EXPERIMENT_REPORT.md', 'RESEARCH_VERDICT.md', 'UPDATED_MANUSCRIPT_CHANGELOG.md', 'AGENTS.md', 'README.md']

file_list = [f for f in ROOT_FILES if os.path.exists(f)]
for d in TARGET_DIRS:
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith(('.md', '.tex', '.py', '.txt', '.json')):
                file_list.append(os.path.join(root, f))

for path in file_list:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
            for i, line in enumerate(fp, 1):
                if regex.search(line):
                    matches.append((path, i, line.strip()))
    except Exception as e:
        pass

for path, i, line in matches:
    print(f'{path}:{i}: {line[:120]}')
