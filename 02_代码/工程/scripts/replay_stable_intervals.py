"""Independent scalar-contrast replay of a frozen stable-arithmetic family."""
from repo_paths import Path, repository_root
import argparse,json,math,time,hashlib
import numpy as np
from threadpoolctl import threadpool_limits


def check_one(data,counts,stored):
    span=stored['span'];n=stored['n_boot'];seed=stored['resampling_seed']
    starts=np.random.default_rng(seed).integers(0,35,size=(n,math.ceil(35/span)))
    ids=((starts[...,None]+np.arange(span))%35).reshape(n,-1)[:,:35]
    weights=np.column_stack([(ids==day).sum(axis=1) for day in range(35)]).astype(float)
    assert hashlib.sha256(ids.astype('<i8').tobytes()).hexdigest()==stored['bootstrap_indices_sha256']
    population=weights@counts;denom_cache={};maximum=np.zeros(n);rows=[];max_se=0.
    for row in stored['coordinates']:
        if row['status']!='ESTIMABLE_APPROX':continue
        d=row['definition'];metric=d['metric'];col=0 if metric=='D' else 2 if metric=='H' else ['C','R','U','V'].index(metric)
        fits=list(range(5)) if d['fit'] is None else [d['fit']]
        # Use scalar compensated summation of each input paired contrast,
        # independently of the production tensor reductions.
        daily=np.array([math.fsum(float(data[f,d['left'],day,col])-(0. if d['right'] is None else float(data[f,d['right'],day,col])) for f in fits)/len(fits) for day in range(35)])
        denominator=population
        if metric=='D':
            right=d['right']
            if right not in denom_cache:
                baseline=np.array([math.fsum(float(data[f,right,day,0]) for f in range(5))/5 for day in range(35)])
                denom_cache[right]=weights@baseline
            denominator=denom_cache[right]
        assert np.all(denominator>0)
        scale=10/42.058880543674675 if metric=='H' else 1.
        samples=scale*(weights@daily)/denominator;sd=float(np.std(samples,ddof=1))
        assert sd>0
        max_se=max(max_se,abs(sd-row['standard_error']))
        maximum=np.maximum(maximum,abs(samples-row['point'])/sd);rows.append((row,sd))
    critical=float(np.sort(maximum)[math.ceil(.95*(n-1))]);critical_error=abs(critical-stored['critical_value']);bound_error=0.
    for row,sd in rows:
        lo=row['point']-critical*sd;hi=row['point']+critical*sd
        if row['domain'][0] is not None:lo=max(lo,row['domain'][0])
        if row['domain'][1] is not None:hi=min(hi,row['domain'][1])
        bound_error=max(bound_error,abs(lo-row['lower']),abs(hi-row['upper']))
    assert critical_error<1e-8 and bound_error<1e-8 and max_se<1e-9
    return dict(span=span,estimable_coordinates=len(rows),critical_error=critical_error,max_bound_error=bound_error,
        max_standard_error_difference=max_se,original_tolerances_unchanged=True,production_statistics_function_imported=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Independent replay output already exists')
    z=np.load(a.results/'all_daily_ledger.npz');start=time.process_time()
    with threadpool_limits(limits=1):
        checks=[check_one(z['ledger'],z['counts'],json.loads((a.results/f'inference_span{s}.json').read_text())) for s in [3,1,7]]
    result=dict(status='INDEPENDENT_STABLE_CONTRAST_REPLAY_MATCHES',checks=checks,cpu_seconds=time.process_time()-start,
        coverage_certified=False,selection_adjusted=False,original_results_modified=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
