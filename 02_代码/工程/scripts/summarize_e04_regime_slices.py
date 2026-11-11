"""Pool accepted E04 slice counts; never pool incomplete policy seed grids."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from repo_paths import Path, repository_root


def pool_rows(rows, complete_policies):
    grouped = {}
    means = ('mean_reserve_kw', 'mean_shortfall_kw', 'mean_forecast_error_kw')
    for row in rows:
        if row['policy'] not in complete_policies:
            continue
        key = (row['policy'], row['axis'], row['group'])
        stats = grouped.setdefault(key, {'n': 0, 'violations': 0, 'signed_excess_count': 0., 'shortage_kwh': 0.,
                                        **{name: 0. for name in means}})
        n = int(row['n'])
        stats['n'] += n
        stats['violations'] += int(row['violations'])
        for name in ('signed_excess_count', 'shortage_kwh'):
            stats[name] += float(row[name])
        for name in means:
            stats[name] += n * float(row[name])
    result = []
    for (policy, axis, group), stats in sorted(grouped.items()):
        for name in means:
            stats[name] /= stats['n']
        result.append({'policy': policy, 'axis': axis, 'group': group, **stats,
                       'violation_rate': stats['violations'] / stats['n']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('Summary output must be a new directory')
    alignment_path = args.input_dir / 'alignment.json'
    slices_path = args.input_dir / 'slices_by_seed.csv'
    alignment = json.loads(alignment_path.read_text(encoding='utf-8'))
    if not alignment.get('inputs_unchanged'):
        raise ValueError('Time-step diagnostic did not complete its integrity check')
    complete = [p for p in ('B', 'C', 'D', 'D10')
                if all(alignment['closures'][str(s)].get(p, {}).get('cost_exact') for s in (201,202,203,204,205))]
    with slices_path.open(encoding='utf-8', newline='') as handle:
        rows = pool_rows(list(csv.DictReader(handle)), complete)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / 'pooled_slices.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {'complete_policy_seed_grids': complete,
               'incomplete_policies_excluded_from_pooled_analysis': [p for p in ('B','C','D','D10') if p not in complete],
               'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (alignment_path, slices_path)},
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'pooled_rows': rows,
               'scope': 'Descriptive counts and weighted means; repeated seed cells are not independent observations'}
    (args.output_dir / 'pooled_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete_policies': complete, 'pooled_rows': len(rows)}, indent=2))


if __name__ == '__main__':
    main()
