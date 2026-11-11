"""Full-grid constructed-data acceptance; never loads original action archives."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from repo_paths import Path, repository_root
import platform
import sys
import time

ROOT=Path(repository_root())
sys.path.insert(0,str(ROOT))
import numpy as np
from windfarm_moe.budget_diagnostic_core import SEEDS,summarize_spans
from windfarm_moe.budget_sources import ARCHIVED_SPEC,qualify_arrays,file_sha256
from windfarm_moe.budget_runtime import evaluate_frozen_source,ResourceAdmissionError,execution_plan


def memory():
    try:
        import psutil
        info=psutil.Process().memory_info()
        return dict(rss_bytes=info.rss,peak_bytes=getattr(info,'peak_wset',info.rss),
                    peak_kind='Windows peak working set' if hasattr(info,'peak_wset') else 'RSS snapshot')
    except ImportError:return dict(rss_bytes=None,peak_bytes=None,peak_kind='UNAVAILABLE')


def dump(path,value):
    assert not path.exists(),'Preserve existing acceptance output: '+str(path)
    path.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def synthetic_grid():
    spec=ARCHIVED_SPEC
    anchors=np.arange(spec.anchor_start,spec.anchor_stop,dtype=np.int64)
    shape=(len(anchors),spec.n_nodes)
    mask=np.zeros(shape,bool);mask.flat[:spec.n_scored]=True
    category=(np.arange(shape[0])[:,None]+np.arange(shape[1])[None,:])%4
    day=(anchors//144-spec.first_day)[:,None]
    target=(category*3+day%3).astype(float)+.3141592653589793
    runs={}
    for seed in SEEDS:
        # Fixed recipes exercise nonconstant traces, not an expected benefit.
        p=(category*2+day%3+2).astype(float)+(seed-201)/8
        z=(category*3+(day+1)%3+1).astype(float)+(seed-201)/16
        runs[seed]=dict(anchors=anchors,mask=mask,P=p,Z=z,S=target,node_ids=tuple(range(spec.n_nodes)))
    return runs


def constructed_indices(span,patterns):
    rng=np.random.default_rng(20261025+span)
    templates=[]
    for _ in range(patterns):
        starts=rng.integers(0,35,size=(35+span-1)//span)
        templates.append(np.concatenate([(int(start)+np.arange(span))%35 for start in starts])[:35])
    # Intentional repeated configurations validate exact caching, not effective
    # statistical replication or real-draw diversity. All 20,000 IDs remain.
    return np.asarray([templates[i%patterns] for i in range(20000)],dtype=np.int64)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--patterns',type=int,default=40)
    parser.add_argument('--spans',type=int,nargs='+',default=[3,1,7])
    parser.add_argument('--dense-admission',action='store_true')
    parser.add_argument('--backend',choices=['scalar','vector_exact'],default='scalar')
    parser.add_argument('--max-exact-group-visits',type=int,default=10_000_000)
    parser.add_argument('--dense-profile',action='store_true')
    args=parser.parse_args()
    if not 1<=args.patterns<=20000 or set(args.spans)!={1,3,7}:raise ValueError('Use all fixed spans and declared positive synthetic pattern count')
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    if (out/'acceptance.json').exists():raise FileExistsError('Acceptance is immutable; choose a new output directory')
    started=time.perf_counter();runs=synthetic_grid()
    config=dict(mode='SYNTHETIC',shape=[5033,134],n_scored=672939,n_days=35,seeds=SEEDS,
        n_draws_per_span=20000,spans=args.spans,synthetic_draw_seeds=[20261025+s for s in args.spans],
        declared_patterns_per_span=args.patterns,selection_by_U_or_V=False,
        original_measurements_or_actions_read=False,
        actual_original_draws_read=False,training=False,dense_admission=args.dense_admission,
        backend=args.backend,max_exact_group_visits=args.max_exact_group_visits,dense_profile=args.dense_profile,
        command=sys.argv,python=sys.version,numpy=np.__version__,host=platform.node(),cpu=platform.processor(),
        started_utc=datetime.now(timezone.utc).isoformat())
    dump(out/'config.json',config)
    rows_by_span={};profiles={}
    rules_hash=file_sha256(ROOT/'research_audit/minimum_budget_diagnostic_plan_v2_20261022/RULES.json')
    for span in args.spans:
        begin=time.perf_counter()
        print('SYNTHETIC span',span,'source qualification',flush=True)
        indices=constructed_indices(span,args.patterns)
        source=qualify_arrays(runs,indices,spec=ARCHIVED_SPEC,mode='SYNTHETIC',rules_sha256=rules_hash,span=span)
        qualified=time.perf_counter()
        last=[0]
        def progress(item):
            count=item['unique_day_configs']
            if count==1 or count>=last[0]+10:
                print('SYNTHETIC span',span,'unique configurations',count,flush=True);last[0]=count
        result=evaluate_frozen_source(source,progress=progress,backend=args.backend,
                                     max_exact_group_visits=args.max_exact_group_visits)
        elapsed=time.perf_counter()-begin
        assert len(result.rows)==8 and len(result.trace['draw_to_config'])==20000
        assert set(result.metadata['seed_ids'])==set(SEEDS)
        rows_by_span[span]=result.rows
        profiles[span]=dict(seconds=elapsed,qualification_seconds=qualified-begin,memory=memory(),
            unique_day_configurations=result.metadata['unique_day_configurations'],
            unique_mapping_computations=result.metadata['unique_mapping_computations'],
            exact_group_counts=result.metadata['exact_group_counts'],
            interval_states={r.coordinate_id:r.interval_status for r in result.rows})
        dump(out/f'span{span}_intervals.json',[asdict(r) for r in result.rows])
        dump(out/f'span{span}_derivation.json',result.metadata)
        dump(out/f'span{span}_mapping_receipts.json',result.trace)
        print('SYNTHETIC span',span,'complete seconds',round(elapsed,3),flush=True)
    dense=None
    if args.dense_admission or args.dense_profile:
        begin=time.perf_counter();spec=ARCHIVED_SPEC
        a=np.arange(spec.anchor_start,spec.anchor_stop,dtype=np.int64)
        shape=(len(a),spec.n_nodes);m=np.zeros(shape,bool);m.flat[:spec.n_scored]=True
        values=np.arange(np.prod(shape),dtype=float).reshape(shape)
        dense_runs={s:dict(anchors=a,mask=m,P=(values+1)/512+(s-201)/8,
            Z=(values*7%10007)/128+1,S=(values%97)/16+.3141592653589793,
            node_ids=tuple(range(spec.n_nodes))) for s in SEEDS}
        idx=constructed_indices(3,20000)
        dense_source=qualify_arrays(dense_runs,idx,spec=spec,mode='SYNTHETIC',rules_sha256=rules_hash,span=3)
        try:
            evaluate_frozen_source(dense_source)
            raise AssertionError('Full-unique exact work should require explicit additional compute admission')
        except ResourceAdmissionError as exc:
            dense=dict(status='STOPPED_BEFORE_MAPPING_BY_DECLARED_TECHNICAL_WORK_BUDGET',
                plan=exc.plan,seconds=time.perf_counter()-begin,memory=memory(),
                group_counts={s:len(v[0]) for s,v in dense_source.groups.items()},
                scores_computed=False,scientific_null=False,thresholds_changed=False,
                note='This is a resource-admission result, not a measurement of dense full-run throughput')
        dump(out/'dense_admission.json',dense)
        if args.dense_profile:
            # Full unique-row dimension with one nonconstant day-count template,
            # repeated under all 20,000 declared IDs; never claimed as high draw diversity.
            dense_profiles={}
            for span in args.spans:
                t=time.perf_counter()
                subset=qualify_arrays(dense_runs,constructed_indices(span,1),spec=spec,mode='SYNTHETIC',rules_sha256=rules_hash,span=span)
                evaluated=evaluate_frozen_source(subset,backend=args.backend,max_exact_group_visits=args.max_exact_group_visits)
                dense_profiles[span]=dict(seconds=time.perf_counter()-t,unique_day_configs=evaluated.metadata['unique_day_configurations'],
                    n_scored=spec.n_scored,unique_groups=evaluated.metadata['exact_group_counts'],n_draws=20000,
                    distinct_draw_templates=1,memory=memory())
                dump(out/f'dense_span{span}_intervals.json',[asdict(r) for r in evaluated.rows])
                dump(out/f'dense_span{span}_derivation.json',evaluated.metadata)
                dump(out/f'dense_span{span}_mapping_receipts.json',evaluated.trace)
                print('DENSE SYNTHETIC span',span,'complete seconds',round(dense_profiles[span]['seconds'],3),flush=True)
            dump(out/'dense_profile.json',dense_profiles)
    summary=dict(status='FULL_GRID_AND_DRAW_COUNT_SYNTHETIC_PROFILE_COMPLETED',
        profiles=profiles,total_seconds=time.perf_counter()-started,memory=memory(),
        decisions=summarize_spans(rows_by_span),
        acceptance_scope='672939 cells, five fits, eight slots, 20000 declared synthetic draws per original span',
        limitations=['Only forty (or explicitly configured) distinct synthetic draw templates per span',
            'Exact row compression is high in this constructed profile; real-data compression and draw diversity remain unverified',
            'No real-action throughput or statistical coverage claim'],
        real_diagnostic_run=False,thresholds_changed=False,new_training=False,dense_resource_admission=dense)
    dump(out/'acceptance.json',summary)
    print('SYNTHETIC ACCEPTANCE COMPLETE; real diagnostic not run',flush=True)


if __name__=='__main__':main()
