"""Read all archived historical/confirmation blocks into a plain audit ledger."""
from pathlib import Path
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'analyses/independent_confirmation_execution_20261019/recovered/results'
rows, protected = [], {}
for stage in ('historical', 'evaluate'):
    for worker in range(550):
        p = BASE / stage / str(worker)
        meta = json.loads((p / 'metadata.json').read_text())
        task = meta['task']
        fp = p / 'blocks.npz'
        protected[str(fp.relative_to(ROOT))] = hashlib.sha256(fp.read_bytes()).hexdigest()
        with np.load(fp) as archive:
            for qi, q in enumerate((.9, .925, .95, .975, .99)):
                n = int(archive[f'{qi}__count'].sum())
                cost = float(archive[f'{qi}__loss_sum'].sum())
                v = int(archive[f'{qi}__violation_sum'].sum())
                rows.append(dict(stage=stage, worker=worker, **task, q=q,
                    label=f"{task['subset']}/{task['estimator']}/q{q}",
                    resource=json.dumps(meta['resource']), n_valid=n,
                    n_day_blocks=len(archive[f'{qi}__count']), cost_total_kwh_equivalent=cost,
                    mean_cost_kwh_equivalent=cost/n, violations=v, violation_rate=v/n,
                    reserve_total_kwh=float(archive[f'{qi}__reserve_sum'].sum()),
                    shortage_total_kwh=float(archive[f'{qi}__shortage_sum'].sum()),
                    artifact=str(fp.relative_to(ROOT)),
                    status='VERIFIED_FROM_ARCHIVED_DAY_BLOCKS_NOT_RAW_ACTIONS'))
with (OUT/'all_worker_quantile_points.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
for name, digest in protected.items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
(OUT/'ledger_points_receipt.json').write_text(json.dumps(dict(
    utc=datetime.now(timezone.utc).isoformat(), command='python research_audit/working/rigor/ledger_points.py',
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    rows=len(rows), source_arrays=1100, numpy=np.__version__, python=sys.version,
    inputs_sha256=protected, no_fit=True, no_inference=True, no_resampling=True),indent=2),encoding='utf-8')
print(json.dumps(dict(rows=len(rows), path=str(OUT/'all_worker_quantile_points.csv'), fields=list(rows[0])),indent=2))
