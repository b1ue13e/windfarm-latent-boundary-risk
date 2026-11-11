"""Bounded synthetic differential benchmarks; no real action archives or RNG reuse."""
import argparse,csv,json,platform,sys,time
from dataclasses import asdict
from fractions import Fraction as F
from repo_paths import Path, repository_root
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
from windfarm_moe.budget_diagnostic_core import SEEDS,map_pair,score_pair
from windfarm_moe.budget_vector_exact import PreparedActions,map_pair_fast,score_pair_fast,exact_sum


def data(seed,n):
    rng=np.random.default_rng(seed)
    p=rng.random(n)*100;z=rng.random(n)*100;s=rng.random(n)*120
    w=rng.integers(0,4,n);w[0]=1
    return p,z,s,w


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    if (out/'benchmark.json').exists():raise FileExistsError('Preserve earlier benchmark')
    started=time.perf_counter();results=[]
    for n in (2048,8192,672939):
        for seed in SEEDS:
            p,z,s,w=data(seed,n);prep=(PreparedActions.make(p),PreparedActions.make(z))
            if n==672939 and seed==201:
                t=time.perf_counter();reference_sum=sum((F.from_float(float(x))*int(v) for x,v in zip(p,w) if v),F())
                assert exact_sum(p,w)==reference_sum
                print('Full unique exact sum equals scalar rational oracle; seconds',round(time.perf_counter()-t,3),flush=True)
            for anchor in ('P','Z'):
                for method in ('M','S'):
                    old=None;old_seconds=None
                    if n<=8192:
                        t=time.perf_counter();a=map_pair(p,z,anchor,method,w);old=score_pair(s,a.P,a.Z);old_seconds=time.perf_counter()-t
                    t=time.perf_counter();b=map_pair_fast(p,z,anchor,method,w,prepared=prep);new=score_pair_fast(s,b.P,b.Z);new_seconds=time.perf_counter()-t
                    if old is not None:
                        assert asdict(old)==asdict(new)
                        for x,y in zip((a.P,a.Z),(b.P,b.Z)):
                            assert x.ideal_coefficient==y.ideal_coefficient and x.coefficient==y.coefficient
                            assert x.residual==y.residual
                            np.testing.assert_array_equal(x.actions,y.actions)
                    assert new.U is not None and new.V is not None
                    results.append(dict(n=n,seed=seed,anchor=anchor,method=method,reference_seconds=old_seconds,
                        vector_seconds=new_seconds,speedup=old_seconds/new_seconds if old_seconds is not None else None,
                        exact_differential=old is not None,status=new.U_state+'/'+new.V_state))
            print('Synthetic unique n',n,'seed',seed,'completed',flush=True)
    import psutil
    mem=psutil.Process().memory_info()
    report=dict(mode='SYNTHETIC_HIGH_UNIQUENESS_ONLY',results=results,total_seconds=time.perf_counter()-started,
        python=sys.version,numpy=np.__version__,host=platform.node(),cpu=platform.processor(),
        peak_bytes=getattr(mem,'peak_wset',mem.rss),new_training=False,real_budget_diagnostic=False,
        full_20000_draw_high_unique_cartesian_run=False)
    (out/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    with (out/'benchmark.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    print('Bounded differential and full-unique single-setting benchmark complete',flush=True)


if __name__=='__main__':main()
