"""Read-only filesystem census; writes only under research_audit/."""
from __future__ import annotations
import collections
import csv
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research_audit'
ENV = {'.git', '.dl_env', '.dl_env313', '.era5_env', 'envs', '.agents', '.claude', '.dsh', '.workbuddy', 'Microsoft', 'NVIDIA Corporation'}

def main():
    OUT.mkdir(exist_ok=True)
    groups = collections.defaultdict(lambda: {'files': 0, 'bytes': 0})
    suffixes = collections.Counter()
    errors, research, links = [], [], []
    total = 0
    def error(e):
        errors.append({'path': str(e.filename), 'error': str(e)})
    with gzip.open(OUT / 'all_accessible_files.csv.gz', 'wt', encoding='utf-8', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['path', 'bytes', 'mtime_ns', 'scope', 'content_review'])
        for current, dirs, files in os.walk(ROOT, onerror=error, followlinks=False):
            if Path(current).parent == ROOT:
                print('CENSUS '+str(Path(current).relative_to(ROOT)), flush=True)
            dirs.sort(); files.sort()
            for name in dirs[:]:
                p = Path(current) / name
                if p.is_symlink() or p.is_junction():
                    links.append(str(p.relative_to(ROOT))); dirs.remove(name)
            for name in files:
                p = Path(current) / name
                rel = p.relative_to(ROOT)
                if rel.parts[0] == 'research_audit':
                    continue
                try:
                    st = p.stat()
                except OSError as exc:
                    errors.append({'path': str(rel), 'error': str(exc)}); continue
                scope = 'infrastructure_metadata_only' if rel.parts[0] in ENV else 'research_asset'
                writer.writerow([rel.as_posix(), st.st_size, st.st_mtime_ns, scope, 'NOT_CONTENT_REVIEWED_BY_CENSUS'])
                group = groups[rel.parts[0] if len(rel.parts)>1 else '<root>']
                group['files'] += 1; group['bytes'] += st.st_size
                suffixes[p.suffix.lower() or '<none>'] += 1
                total += 1
                if scope == 'research_asset':
                    research.append((rel.as_posix(), st.st_size, p.suffix.lower()))
    with (OUT / 'research_assets.csv').open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh); w.writerow(['path','bytes','suffix']); w.writerows(research)
    summary = {'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'root': str(ROOT), 'all_files': total, 'research_assets': len(research),
               'top_level': dict(sorted(groups.items())), 'suffix_counts': dict(suffixes.most_common()),
               'walk_errors': errors, 'unfollowed_links_or_junctions': links,
               'content_coverage': 'Metadata census only; explicit content reads are separately logged. No completeness claim about scientific interpretation.'}
    (OUT / 'inventory_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    history = subprocess.run(['git','log','--all','--date=iso-strict','--format=%H%x09%ad%x09%s'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
    (OUT/'git_history.tsv').write_text(history.stdout, encoding='utf-8')
    status = subprocess.run(['git','status','--porcelain=v1','-uno'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
    (OUT/'baseline_tracked_status.txt').write_text(status.stdout, encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('all_files','research_assets','walk_errors','unfollowed_links_or_junctions')}, ensure_ascii=False))
    print(json.dumps(summary['top_level'], ensure_ascii=False))

if __name__ == '__main__':
    main()
