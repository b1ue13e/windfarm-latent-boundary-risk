"""Plot archived results; primary and retrospective families stay distinct."""
from pathlib import Path
import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'analyses/independent_confirmation_execution_20261019/recovered/results/aggregate'
OUT=ROOT/'research_audit/figures'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    primary=json.loads((BASE/'primary.json').read_text())
    env=primary['bounds']['groups'][0]
    g=json.loads((BASE/'secondary_span3.json').read_text())['results'][0]
    assert g['condition']=='pitch_withheld'
    plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,(a,b)=plt.subplots(1,2,figsize=(10.5,4.6),gridspec_kw={'width_ratios':[.85,1.6]})
    pt=env['relative_ratio_point'][0][1]*100
    lo=env['relative_ratio_lower'][0][1]*100;hi=env['relative_ratio_upper'][0][1]*100
    a.axhspan(0,2,color='#0072B2',alpha=.06)
    a.axhline(0,color='0.4',lw=.8);a.axhline(2,color='#D55E00',ls='--',lw=1)
    a.errorbar([0],[pt],yerr=[[pt-lo],[hi-pt]],fmt='o',color='#0072B2',capsize=6,ms=7)
    a.text(.12,pt,f'{pt:.3f}%\n[{lo:.3f}, {hi:.3f}]',va='center')
    a.text(-.35,2.07,'Frozen 2% margin',color='#D55E00',fontsize=9)
    a.set(xlim=(-.55,.85),ylim=(-.25,2.55),xticks=[0],xticklabels=['P1/HGB/q.95'],
        ylabel='Mean cost relative to frozen reference (%)',title='A  Primary fixed-reference confirmation')
    a.text(.03,.95,'Both maximum risk UCBs < 6.21%\n14-coordinate approximate envelope',
        transform=a.transAxes,va='top',fontsize=8)
    x=np.asarray(g['risk_upper'],float).max(axis=0)*100;y=np.asarray(g['mean_cost'])
    rows=[]
    for i,label in enumerate(g['labels']):
        b.scatter(x[i],y[i],s=15,color='0.65',alpha=.5,edgecolors='none')
        rows.append(dict(label=label,max_instance_risk_upper_pct=x[i],mean_cost=y[i],family='secondary_74500_coordinates'))
    b.axvline(10,color='#D55E00',ls='--',lw=1);b.text(10.13,140,'10% risk cap',rotation=90,va='top',fontsize=8)
    specs=[('P1/HGB/q0.925','#009E73','*',(9,1),'P1/HGB/q.925\nsecondary minimum'),
        ('P1/HGB/q0.95','#0072B2','o',(-64,26),'P1/HGB/q.95'),
        ('WPQ36/HGB/q0.95','#D55E00','s',(-84,-21),'Frozen full-input reference'),
        ('Common/HGB/q0.925','#000000','D',(8,0),'Common/HGB/q.925'),
        ('P1/Persistence/q0.925','#CC79A7','^',(-124,7),'Persistence/q.925')]
    for label,color,marker,xytext,text in specs:
        i=g['labels'].index(label)
        b.scatter(x[i],y[i],s=65 if marker!='*' else 120,color=color,marker=marker,edgecolors='white',linewidths=.5,zorder=4)
        b.annotate(text,(x[i],y[i]),xytext=xytext,textcoords='offset points',fontsize=8,
            arrowprops=dict(arrowstyle='-',color=color,lw=.6),color=color)
    b.set(xlim=(0,15.5),ylim=(57,147),xlabel='Maximum instance risk upper bound (%)',
        ylabel='Mean surrogate cost (kWh-equivalent / valid interval)',title='B  Secondary frozen full-q family (225 policies)')
    fig.subplots_adjust(left=.08,right=.98,bottom=.23,top=.88,wspace=.48)
    fig.text(.08,.075,'Hill of Towie 2025, 5 frozen instances, 365 shared days, 1,059,248 valid intervals. Three-day block bounds.\n'
        'Panels use different joint families; their UCBs differ. Secondary q.925 was not the primary historical choice.\n'
        'Both policies use a common upstream forecast trained on wind/power. No field-safety or universal-minimum claim.',fontsize=8)
    for ext in ('png','pdf','svg'):
        fig.savefig(OUT/f'core_evidence.{ext}',dpi=300)
    with (OUT/'core_evidence_source.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    plt.close(fig)
    print('Saved core_evidence PNG/PDF/SVG and 225-policy source table.')

if __name__=='__main__':main()
