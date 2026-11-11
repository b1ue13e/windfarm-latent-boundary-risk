"""Project frozen evidence only: no fitting, new inference, or resampling."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def select_coordinate(data, cid, left, right):
    records = [r for r in data['coordinates'] if r['id'] == cid]
    if len(records) != 1:
        raise ValueError('Coordinate must be unique: '+cid)
    r = records[0]
    names = data['policy_names']
    if names[r['definition']['left']] != left or names[r['definition']['right']] != right:
        raise ValueError('Coordinate policy identity mismatch')
    return r


def write_csv(p, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('x', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def main():
    a=argparse.ArgumentParser(); a.add_argument('--root',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True); args=a.parse_args()
    args.output.mkdir(exist_ok=False,parents=True)
    inputs={}
    def bind(rel):
        p=args.root/rel; inputs[str(p)]=sha(p); return p
    def read(rel):
        return json.loads(bind(rel).read_text(encoding='utf-8-sig'))
    bases=[('WTB_development_64654', 'experiments/conditional_refine_20261025_v2/recovered/results/campaign',
            ['REF','R0182_P','BR009_Z'],64654),
           ('WTB_development_88052','experiments/conditional_training_fourth_cell_20261025/recovered/results/campaign/step3',
            ['EM1_003_P'],88052)]
    points=[]; quals=[]; coords=[]
    for pop, rel, selected, size in bases:
        names=read(rel+'/all_policy_names.json')['names']
        path=bind(rel+'/all_daily_ledger.npz')
        with np.load(path) as z:
            ledger=z['ledger']; counts=z['counts']; days=z['day_ids']
            if ledger.shape!=(5,len(names),len(counts),4) or len(days)!=35 or counts.sum()!=672939:
                raise ValueError('Unexpected population/ledger coordinates')
            point=ledger.sum(axis=2).mean(axis=0)/counts.sum()
            for name in selected:
                v=point[names.index(name)]
                # Independent cost identity with explicit numerical tolerance; does not change raw data.
                if abs(v[0]-v[1]-10*v[2])>1e-8:
                    raise ValueError('Ledger C=R+10U identity failed')
                points.append(dict(population=pop,policy=name,C=v[0],R=v[1],U=v[2],V=v[3],
                                   estimator='original frozen policy procedure; not re-fitted in this projection',
                                   n_valid_per_fit=int(counts.sum()),n_days=len(days),fixed_fits='201;202;203;204;205',
                                   clock='original WTB issue211-245; mature feedback',
                                   unit='C/R/U: kWh-equivalent per valid turbine interval; V: fraction',
                                   source_file=str(path),source_sha256=inputs[str(path)],family_size=size,
                                   qualification_source='per-span original frozen family',selection_adjusted=False))
        for span in (1,3,7):
            source=rel+f'/inference_span{span}.json'; d=read(source)
            if d['family_size']!=size or d['policy_names']!=names or d['span']!=span:
                raise ValueError('Family identity differs')
            for name in selected:
                if name not in d['qualification']:
                    raise ValueError('Missing original qualification: '+name)
                quals.append(dict(population=pop,policy=name,span=span,family_size=size,
                                  baseline='REF',source_file=source,source_sha256=inputs[str(args.root/source)],
                                  **{k:('UNKNOWN' if v is None else v) for k,v in d['qualification'][name].items()}))
            if size==64654:
                for metric in ('D','U','V'):
                    r=select_coordinate(d,f'E:907:{metric}','BR009_Z','R0182_P')
                    coords.append(dict(population=pop,estimator='frozen BR/R182 procedures',span=span,
                                       family_size=size,left='BR009_Z',right='R0182_P',
                                       coordinate_id=r['id'],metric=metric,point=r['point'],lower=r['lower'],upper=r['upper'],
                                       status=r['status'],unit=r['unit'],source_file=source,
                                       source_sha256=inputs[str(args.root/source)]))
    m_rows=[]
    rel='analyses/praw_supplement_v3_execution_20261021'
    for filename in ('primary_comparisons.csv','all_endpoints.csv'):
        p=bind(rel+'/'+filename)
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        for r in rows:
            if r['population']!='M_primary_evaluation' or r['estimator'] not in ('HGB','MLP'):
                continue
            if r['comparison']=='Praw-minus-OZ6' or (r['arm'] in ('Praw','OZ6') and r['metric']=='absolute_V'):
                m_rows.append(dict(r,projection_source=str(p),projection_source_sha256=inputs[str(p)]))
    # Same rows appear in the primary convenience table and all-endpoint table;
    # require exact agreement and retain both provenance routes without doubling evidence.
    unique={}
    for r in m_rows:
        key=r['coordinate_id']
        if key in unique:
            if any(r.get(k)!=unique[key].get(k) for k in ('point','lower','upper','interval_status','population','source_file')):
                raise ValueError('Conflicting exported original rows')
        else:
            unique[key]=r
    m_rows=list(unique.values())
    if not m_rows or not all(any(r['comparison']=='Praw-minus-OZ6' and r['metric']=='D_C' and r['estimator']==e for r in m_rows) for e in ('HGB','MLP')):
        raise ValueError('Required original two-estimator cost coordinates missing')
    available=sorted(set(r['metric'] for r in m_rows))
    means_path=bind(rel+'/mean_metrics.csv')
    with means_path.open(encoding='utf-8-sig',newline='') as f:
        means=[dict(r,population='M_primary_evaluation',clock='original M frozen common forecast and target clock',
                    source_file=str(means_path),source_sha256=inputs[str(means_path)],
                    unit='C/R/U per valid turbine interval; V fraction')
               for r in csv.DictReader(f) if r['arm'] in ('Praw','OZ6')]
    towie=read('analyses/independent_confirmation_execution_20261019/derived/summary.json')
    write_csv(args.output/'WTB_POINTS.csv',points)
    write_csv(args.output/'WTB_ORIGINAL_QUALIFICATIONS.csv',quals)
    write_csv(args.output/'BR009_VS_R182_ORIGINAL_COORDINATES.csv',coords)
    write_csv(args.output/'M_PRAW_VS_OZ6_ORIGINAL_COORDINATES.csv',m_rows)
    write_csv(args.output/'M_ORIGINAL_POINT_METRICS.csv',means)
    after={p:sha(p) for p in inputs}
    if after!=inputs: raise ValueError('Protected original input changed')
    summary=dict(status='VERIFIED_ZERO_FIT_EVIDENCE_PROJECTION',new_fits=0,new_bootstrap=0,new_measurements=0,
                 points=points,qualifications=quals,BR_vs_R182_coordinates=coords,M_available_metrics=available,
                 towie_2025=towie,original_inputs_unchanged=True,inputs_sha256=inputs,
                 n_unique_M_coordinates=len(m_rows),span_interpretation='3 primary;1/7 sensitivity; not independent replications',
                 unknown='Missing or null fields remain UNKNOWN; no new p-values or CI construction',
                 limitation='No pooling across64654/88052/M/Towie; WTB development is not selection-adjusted confirmation',
                 utc=datetime.now(timezone.utc).isoformat(),argv=sys.argv,python=sys.version,numpy=np.__version__,
                 host=platform.node(),script_sha256=sha(__file__))
    (args.output/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    report=['# 零拟合证据汇总（已实际执行）','',
            '只读取既有日账、联合坐标和资格标签，未训练、推理、重采样或读取2026测量。每一原始输入均核对前后SHA。',
            '', '| 程序 | C | U | V | 统计族 |','|---|---:|---:|---:|---:|']
    for r in points: report.append(f"| {r['policy']} | {r['C']:.6f} | {r['U']:.6f} | {r['V']*100:.4f}% | {r['family_size']} |")
    report+=['','BR009−R182主3日原联合坐标：']
    for r in coords:
        if r['span']==3: report.append(f"- {r['coordinate_id']}: {r['point']:.9f} [{r['lower']:.9f}, {r['upper']:.9f}]，{r['unit']}。")
    report+=['','P侧25%固定混合EM1_003_P的资格从88052族读取；BR009/R182来自64654族。没有跨族重构区间。',
             'M人口原表Praw/OZ6保留两估计器、原分组/时钟/终点和H字段。H未闭合不改成通过。原比较坐标及单实例事件率见CSV。',
             'Towie2025主要q.95是固定参照成本非劣确认；次要q.925才是有限族最小性识别，二者不合并。',
             '',f'保护输入{len(inputs)}个，前后SHA全部一致。原35日与5个拟合不当作175个独立天气日。',
             '保留旧span3数值严格重放误差的既有审计边界；本投影不升级近似区间覆盖或科学认证。']
    (args.output/'REPORT_CN.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=summary['status'],points=points,inputs=len(inputs),M_coordinates=len(m_rows)),ensure_ascii=False))


if __name__=='__main__': main()
