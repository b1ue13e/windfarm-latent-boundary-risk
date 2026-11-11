import os,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
os.chdir(root)
assert os.environ.get('PBS_JOBID'), 'Allocated PBS job required'
p=json.loads((root/'experiments/decision_information_development_20261018/protocol.json').read_text())
grid=[(s,c) for s in p['seeds'] for c in p['conditions'] if (s,c)!=(201,'pitch_withheld')]
i=int(os.environ['PBS_ARRAY_INDEX'])
seed,condition=grid[i]
assert json.loads((root/'results/smoke_action_audit.json').read_text())['status']=='EXACT_ARCHIVED_ACTION_ACCOUNTING_PASS'
py='/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015/.venv/bin/python'
os.execv(py,[py,'-u','scripts/run_decision_information_development.py','run','--protocol','experiments/decision_information_development_20261018/protocol.json','--prepared','results/prepared','--output',f'results/runs/seed{seed}/{condition}','--seed',str(seed),'--condition',condition,'--threads','2'])
