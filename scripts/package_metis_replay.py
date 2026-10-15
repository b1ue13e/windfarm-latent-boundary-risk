"""Create a minimal runtime source archive and immutable cloud input manifest.

No Git credentials, local SSH/deploy scripts, historical weights or local fits included.
"""
from __future__ import annotations
import ast
import argparse
import json
from pathlib import Path
import re
import subprocess
import zipfile
from replay_provenance import file_record,sha256,write_json

ROOT=Path(__file__).resolve().parents[1]
TESTS=['test_replay_integrity','test_external_wind','test_exp02_protocol',
       'test_exp03_async_arrival','test_f4_verdict_regression','test_f4_hierarchical_bootstrap']
ENTRYPOINTS=['metis_replay','raw_replay','replay_provenance','replay_after_wtb',
    'replay_external_raw','replay_external_train','repair_exp01_pitch_withheld_v3',
    'build_train_weight_cache','build_fixed_forecast_residuals','test_strong_baseline_closure',
    'run_channel_consequence_ablations','run_exp02_zero_privileged_supervision',
    'run_exp03_async_benchmark','run_matched_budget_frontier','run_rho_sensitivity',
    'eval_single_task_dense_phase_scan','run_clean_privileged_supervision_ablation',
    'run_active_power_anchor_audit','replay_factorial']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'artifacts/metis_deployment_20261015')
    out=parser.parse_args().output_dir.resolve()
    if not out.is_relative_to(ROOT/'artifacts'):raise ValueError('Package must stay in artifacts')
    out.mkdir(exist_ok=True)
    package=out/'source.zip'
    if package.exists():raise FileExistsError('Do not overwrite a deployed source archive')
    paths={ROOT/'main.py',ROOT/'requirements.txt',ROOT/'scripts/metis_replay.py',
        ROOT/'scripts/metis_replay.pbs',ROOT/'scripts/replay_external_raw.py',
        ROOT/'scripts/replay_external_train.py'}
    paths.update(ROOT/'tests'/f'{s}.py' for s in TESTS)
    paths.update(ROOT/'scripts'/f'{s}.py' for s in ENTRYPOINTS)
    paths.update((ROOT/'windfarm_moe').rglob('*.py'))
    pending=list(paths)
    while pending:
        p=pending.pop()
        if p.suffix!='.py':continue
        code=p.read_text(encoding='utf-8-sig')
        names=[]
        for node in ast.walk(ast.parse(code)):
            if isinstance(node,ast.Import):names.extend(n.name for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:names.append(node.module)
        candidates=[]
        for n in names:
            candidates.extend([ROOT/(n.replace('.','/')+'.py'),ROOT/'scripts'/(n.split('.')[0]+'.py')])
        candidates.extend(ROOT/s for s in re.findall(r'scripts/[A-Za-z0-9_]+\.py',code))
        for q in candidates:
            if q.is_file() and q not in paths:paths.add(q);pending.append(q)
    for p in paths:
        if p.suffix=='.py' and re.search(r'(?i)(?:password|passwd|access_token)\s*=\s*[\'\"][^\'\"]+',p.read_text(encoding='utf-8-sig')):
            raise ValueError('Runtime dependency contains a credential-like literal; redact securely before packaging: '+str(p.relative_to(ROOT)))
    paths.update(ROOT/p for p in ['docs/SCIENTIFIC_CONTRACT.md','docs/EXPERIMENT_REGISTRY.md',
        'docs/RAW_REPLAY_PROTOCOL_20261015.md','docs/REPLAY_CORRECTION_ADDENDUM_20261015.md',
        'experiments/replay_20261015/frozen_wtb_configs.json',
        'experiments/replay_20261015/frozen_external_configs.json','artifacts/ARTIFACT_MANIFEST.json'])
    reference=ROOT/'artifacts/cache_strictmask_trainweights/wtb_245d'
    paths.update(reference/p for p in ['target.npy','target_mask.npy','regime_primary.npy',
        'regime_primary_valid.npy','time_index.npy'])
    mapping={f:f'artifacts/raw_replay_external_20261015/{f}' for f in ['la_haute_borne','kelmarsh','penmanshiel']}
    write_json(out/'metis_cache_map.json',mapping)
    input_records=[dict(relative_path=str(p.relative_to(ROOT)).replace('\\','/'),
        bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(paths)]
    input_records.append(dict(relative_path='metis_cache_map.json',bytes=(out/'metis_cache_map.json').stat().st_size,
        sha256=sha256(out/'metis_cache_map.json')))
    raw=[ROOT/'wtbdata_245days.csv',ROOT/'sdwpf_baidukddcup2022_turb_location.CSV']
    raw.extend(p for p in (ROOT/'data/external_wind').rglob('*') if p.is_file() and p.suffix.lower() in ('.csv','.zip'))
    # These expected hashes were frozen when local raw preprocessing actually read
    # the files. Metis independently hashes every transferred byte against them.
    # Do not call this a new local full-data hash pass.
    receipts=[ROOT/'artifacts/raw_replay_20261015_v2/frozen_protocol.json',
        ROOT/'artifacts/raw_replay_external_20261015/la_haute_borne/provenance.json',
        ROOT/'artifacts/raw_replay_external_20261015/kelmarsh/provenance.json',
        ROOT/'artifacts/raw_replay_external_retry1_20261015/penmanshiel/provenance.json']
    frozen_inputs={}
    for receipt in receipts:
        r=json.loads(receipt.read_text(encoding='utf-8'))
        frozen_inputs.update({str(Path(x['path']).resolve()):x for x in r.get('inputs',r.get('raw_wtb',[]))})
    raw_records=[]
    for p in raw:
        r=frozen_inputs[str(p.resolve())]
        if p.stat().st_size!=r['bytes']:raise ValueError('Raw size changed since recorded preprocessing: '+str(p))
        raw_records.append(dict(relative_path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=r['bytes'],sha256=r['sha256']))
    write_json(out/'metis_input_manifest.json',input_records+raw_records)
    write_json(out/'deployment.json',{'upstream_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_files':len(paths),'archive_scope':'explicit runtime dependencies + tests + frozen protocols/configs + historical target identity; no local fitted weights',
        'cloud_root':'/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015',
        'raw_files':raw_records,'expected_raw_hash_origin':[file_record(p) for p in receipts],
        'raw_validation':'Expected hashes from prior raw-read receipts; full independent byte hashing required on Metis before execution',
        'scientific_completion':False})
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
        for name in ['metis_cache_map.json','metis_input_manifest.json','deployment.json']:z.write(out/name,name)
    write_json(out/'source_archive_manifest.json',file_record(package))
    print('PACKAGED',len(paths),'runtime files;',len(raw),'raw inputs; archive bytes',package.stat().st_size)


if __name__=='__main__':main()
