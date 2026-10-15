"""Continue registered decision diagnostics after raw WTB training/prediction finishes.

This process does not declare scientific completion or update manuscript numbers.
It waits for actual complete output manifests, and stops on upstream failure.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from raw_replay import run_command, verify_records
from replay_provenance import write_json


def main():
    root=ROOT/'artifacts/raw_replay_20261015_v2'
    done=root/'exp03/output_manifest.json'
    while not done.exists():
        records=[json.loads(p.read_text(encoding='utf-8')) for p in (root/'execution').glob('*/record.json')]
        failed=[r['name'] for r in records if r['status']=='FAILED']
        if failed:
            write_json(root/'downstream_status.json',{'status':'BLOCKED_UPSTREAM_FAILURE','failed':failed})
            raise RuntimeError(f'Upstream failure: {failed}')
        write_json(root/'downstream_status.json',{'status':'WAITING_FOR_UPSTREAM','scientific_completion':False})
        time.sleep(30)
    verify_records(json.loads(done.read_text(encoding='utf-8')))
    cache=root/'cache_wtb';res=root/'fixed_forecast_residuals.npz'
    inputs=[res,*sorted(cache.glob('*.npy')),cache/'metadata.json',
            *[root/f'models/dense_classifier/seed{s}/best_model.pt' for s in range(201,206)]]
    env={'RAW_REPLAY_CACHE':str(cache),'RAW_REPLAY_RESIDUALS':str(res),
         'RAW_REPLAY_POSTERIOR_PATTERN':str(root/'models/dense_classifier/seed{seed}'),
         'MATCHED_BUDGET_OUTPUT_DIR':str(root/'matched_budget')}
    for script,expected in [('run_matched_budget_frontier.py','frontier_auc_summary.csv'),
                            ('run_rho_sensitivity.py','reoptimized_rho_sensitivity.csv')]:
        run_command(root,Path(script).stem,[sys.executable,'-u',str(ROOT/'scripts'/script)],
                    inputs,[root/'matched_budget'/expected],env)
    run_command(root,'dense_phase_scan',[sys.executable,'-u','scripts/eval_single_task_dense_phase_scan.py',
        '--cache-dir',str(cache),'--routed-pat',str(root/'models/forecast/seed{seed}'),
        '--dense-pat',str(root/'models/dense/seed{seed}'),'--output-dir',str(root/'dense_phase_scan')],
        [*inputs,*[root/f'models/{family}/seed{s}/best_model.pt'
                   for family in ['forecast','dense'] for s in range(201,206)]],
        [root/'dense_phase_scan'/name for name in ['phase_scan_results_by_seed.csv',
            'phase_scan_risk_coverage_by_seed.csv','output_manifest.json']])
    write_json(root/'downstream_status.json',{'status':'EXECUTED_PENDING_AUDIT',
        'scientific_completion':False,'scope':'matched budget, rho sensitivity, dense phase scan only',
        'remaining':'Coverage.json still governs all unexecuted ancillary families; independent review required'})


if __name__=='__main__':main()
