"""Stream an independent shared-block interval reconstruction from daily sums."""
import argparse,hashlib,json,math,time
from repo_paths import Path, repository_root
import numpy as np
from threadpoolctl import threadpool_limits


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--study-dir',type=Path,default=Path('experiments/mixture_closed_loop_20261024'))
    args=parser.parse_args();root=args.study_dir;p=root/'recovered/results/campaign'
    archive=np.load(p/'all_daily_ledger.npz');data=archive['ledger'];counts=archive['counts']
    started=time.process_time();results=[]
    with threadpool_limits(limits=1):
        for span in [3,1,7]:
            stored=json.loads((p/f'inference_span{span}.json').read_text())
            starts=np.random.default_rng(20261022).integers(0,35,size=(20000,math.ceil(35/span)))
            draw_ids=((starts[:,:,None]+np.arange(span))%35).reshape(20000,-1)[:,:35]
            weights=np.column_stack([(draw_ids==d).sum(axis=1) for d in range(35)]).astype(float)
            population=weights@counts;denominators={};maximum=np.zeros(20000);rows=[];se_error=0
            for row in stored['coordinates']:
                if row['status']!='ESTIMABLE_APPROX':continue
                d=row['definition'];left,right,fit,metric=(d[k] for k in ['left','right','fit','metric'])
                column=0 if metric=='D' else 2 if metric=='H' else ['C','R','U','V'].index(metric)
                fits=list(range(5)) if fit is None else [fit]
                daily=data[fits,left,:,column].mean(axis=0)
                if right is not None:daily=daily-data[fits,right,:,column].mean(axis=0)
                denominator=population
                if metric=='D':
                    if right not in denominators:denominators[right]=weights@data[:,right,:,0].mean(axis=0)
                    denominator=denominators[right]
                assert np.all(denominator>0)
                scale=10/42.058880543674675 if metric=='H' else 1.
                samples=scale*(weights@daily)/denominator
                sd=float(np.std(samples,ddof=1));se_error=max(se_error,abs(sd-row['standard_error']))
                assert sd>0
                maximum=np.maximum(maximum,np.abs(samples-row['point'])/sd)
                rows.append((row,sd))
            # Independent order-statistic implementation of method='higher'.
            critical=float(np.sort(maximum)[math.ceil(.95*(len(maximum)-1))])
            max_error=abs(critical-stored['critical_value'])
            for row,sd in rows:
                lo=row['point']-critical*sd;hi=row['point']+critical*sd
                if row['domain'][0] is not None:lo=max(lo,row['domain'][0])
                if row['domain'][1] is not None:hi=min(hi,row['domain'][1])
                max_error=max(max_error,abs(lo-row['lower']),abs(hi-row['upper']))
            assert max_error<1e-8 and se_error<1e-9
            digest=hashlib.sha256(draw_ids.astype('<i8').tobytes()).hexdigest()
            assert digest==stored['bootstrap_indices_sha256']
            results.append(dict(span=span,estimable_coordinates=len(rows),critical_value=critical,
                max_interval_or_critical_difference=max_error,max_standard_error_difference=se_error,
                draw_hash=digest,source_production_statistics_imported=False))
    result=dict(status='INDEPENDENT_INTERVAL_REPLAY_MATCHES',checks=results,
        cpu_seconds=time.process_time()-started,coverage_certified=False,selection_adjusted=False,
        original_results_modified=False)
    (root/'INTERVAL_REPLAY_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
