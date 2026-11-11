"""Check the narrative against existing results without executing research code."""
from pathlib import Path
import csv
import hashlib
import json
import re

HERE=Path(__file__).resolve().parents[1]
QA=HERE/'author_working/qa'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((HERE/'source_data'/name).read_text(encoding='utf-8'))


def main():
    import fitz
    text=(HERE/'manuscript.md').read_text(encoding='utf-8')
    si=(HERE/'supplementary.md').read_text(encoding='utf-8')
    normal=text.replace('−','-').replace('–','-')
    si_normal=si.replace('−','-').replace('–','-')
    checks=[]
    def check(name,ok,source):checks.append({'check':name,'passed':bool(ok),'evidence':source})
    def number(value,decimals,source):
        token=f'{value:.{decimals}f}'
        # Secondary complete intervals may live in SI rather than interrupt prose.
        si_token=f'{value:.4f}'
        location='main' if token in normal else 'supplement' if si_token in si_normal else None
        check('stored_number:'+source,location is not None,{'value':value,'display':token,'source':source,'location':location})
    original,later=load('M_original_summary.json'),load('M_controls_summary.json')
    for est,comp in [('HGB','old_power'),('HGB','old_state'),('HGB','P_premium_vs_Z'),('MLP','P_premium_vs_Z'),('HGB','fresh_state')]:
        kind='D' if comp=='P_premium_vs_Z' else 'G';key=f'{est}:{comp}|cost|{kind}'
        for bound,value in original['registered_intervals'][key].items():
            if bound in ['point','lower','upper']:number(100*value,2,'M_original_summary.'+key+'.'+bound)
    for est in ['HGB','MLP']:
        key=f'Common:{est}:P_premium_vs_Z|cost|D'
        for bound in ['point','lower','upper']:number(100*later['interval'][key][bound],2,'M_controls_summary.'+key+'.'+bound)
    rs=load('R_paired_intervals.json')
    for index in [0,3,12,15]:
        r=rs[index];number(r['point'],3,f'R_paired_intervals[{index}].point')
        for j,v in enumerate(r['simultaneous_ci']):number(v,3,f'R_paired_intervals[{index}].simultaneous_ci[{j}]')
    key='Common:HGB:residual_state|cost|G';r=later['interval'][key]
    for value,side in [(-r['point'],'point'),(-r['upper'],'lower'),(-r['lower'],'upper')]:number(100*value,2,key+'.cost_difference_'+side)
    ai,bi=[later['labels'].index('Common:HGB:'+x) for x in ['OP6','OPZ6']]
    for metric in ['R','U']:
        a,b=[later['mean_metrics'][metric][i] for i in [ai,bi]]
        number(abs(100*(b-a)/a),2,'Common:HGB:relative_'+metric)
    for cell in ['OPZ6','Match_residual_state']:
        number(later['mean_metrics']['R'][later['labels'].index('Common:HGB:'+cell)],3,'Common:HGB:'+cell+'.R')
    number(100*later['mean_metrics']['V'][later['labels'].index('Common:HGB:Match_residual_state')],2,'Historical_match.event_frequency')
    check('all_joint_results_retained',not any(v for row in later['corrected_routes'].values() for v in row.values())
          and 'Neither estimator under either calibration procedure satisfied any of the joint input-selection requirements' in text,
          'Twelve original false criteria remain false and are stated in Results/SI')
    joint=list(csv.reader((HERE/'tables/tableS7.csv').open(encoding='utf-8-sig')))
    check('twelve_joint_outcomes_in_SI',sum(c=='Not established' for row in joint for c in row)==12,joint)
    limits=load('M_protocol.json')['thresholds']
    check('original_limits_unchanged',limits['important_cost_gain']==limits['substitution_margin']==.01
          and limits['risk_cap']==.1 and limits['weighted_U_increment_over_Cstar']==.001,limits)
    check('negative_controls_and_variation_retained',all(s in text for s in ['one-day interval crossed zero','Three of five fits','Neither cost contrast separated these features','increased cost by 1.720','higher observed event frequency, rising from 10.15% to 11.57%','weighted-shortfall interval included zero','match did not persist in evaluation']),
          'Small-score instability, compression loss, event increase, learner difference and matching failure remain in the story')
    check('material_design_facts_retained',all(s in text for s in ['earliest six issue times','first five issues and coincident with the sixth','retrospective','previously analysed weather period','its equally sized mask differs','effect of enforcing a stricter publication boundary has not been estimated']),
          'Essential design facts remain in Methods, without execution/audit narration')
    check('pinball_definition_retained','10\\ell_{0.90}(S-r)' in text,'Scientific loss definition remains; no scoring-principle novelty claim')
    check('imposed_information_age_stated','Information ages are imposed by masking recorded observations.' in text,'Controlled input ages are not observed communication-delay frequencies')
    forbidden=['SHA256','checksum','manifest','corrected_routes','SR-01','SR-08','guard ledger','20,000-draw matrices were not persisted','source packets','manuscript preparation generated','not submitted','not_submission_ready','403 previously','external reviewer access','scientific gate','no new matrices were generated','original fits and outputs are retained']
    check('internal_record_language_absent',not [x for x in forbidden if x.lower() in (text+'\n'+si).lower()],forbidden)
    check('no_missing_literature_access_story','final fulltext' not in si.lower() and 'full-text overlap' not in si.lower(),'Source-access status belongs to author working records, not scientific conclusions')
    a=text.split('abstract: |\n',1)[1].split('\n---',1)[0]
    words=lambda s:re.findall(r"\b\w+(?:[-’']\w+)*\b",s)
    check('abstract_under200',len(words(a))<=200,len(words(a)))
    check('keywords_six',text.split('**Keywords:** ',1)[1].split('\n',1)[0].count(';')==5,'Six keyword phrases')
    citekeys=set(re.findall(r'@([a-z]+\d{4})\b',text+si))
    bibkeys=set(re.findall(r'@(?:article|misc)\{([^,]+),',(HERE/'references.bib').read_text(encoding='utf-8')))
    check('citation_identities',citekeys==bibkeys,{'cited':sorted(citekeys),'bibliography':sorted(bibkeys)})
    source=json.loads((QA/'source_receipt.json').read_text())
    check('original_source_copies',all(sha(HERE/r['copy'])==r['sha256'] for r in source['files']),'Unchanged original source file hashes')
    fig=json.loads((QA/'figure_receipt.json').read_text())
    fields=fig['plotted_fields']
    check('all_measurement_contrasts_displayed',sum(r['figure']=='fig2' for r in fields)==20,'Four panels times five paired comparisons')
    check('all_reconstruction_points_displayed',sum(r['figure']=='fig3' and 'record_index' in r for r in fields)==6
          and sum(r['figure']=='fig3' and 'displayed_value' in r for r in fields)==15,'Six cost contrasts and fifteen original MSE points')
    rendered=json.loads((QA/'rendered_figure_checks.json').read_text())
    check('figure_rendering',not rendered['failed'] and all(sha(HERE/'figures'/r['figure'])==r['sha256'] for r in rendered['records']),rendered)
    receipt=json.loads((QA/'build_receipt.json').read_text())
    check('compiled_inputs_current',all(sha(HERE/p)==h for p,h in receipt['inputs'].items()),'Exact manuscript/SI/table/figure inputs')
    documents={}
    for stem in ['manuscript','supplementary']:
        doc=fitz.open(HERE/(stem+'.pdf'));outside=[]
        for i,page in enumerate(doc):
            outside += [(i+1,w[4]) for w in page.get_text('words') if w[0]<-1 or w[1]<-1 or w[2]>page.rect.width+1 or w[3]>page.rect.height+1]
        check('page_bounds:'+stem,not outside,outside)
        documents[stem]={'pages':len(doc),'sha256':sha(HERE/(stem+'.pdf'))};doc.close()
    captions=re.findall(r'!\[(.*?)\]\(figures/[^)]+\.pdf\)',text+si,flags=re.S)
    check('figure_caption_limits',len(captions)==5 and all(len(words(c))<=350 for c in captions),[len(words(c)) for c in captions])
    failed=[r for r in checks if not r['passed']]
    result={'status':'FAIL' if failed else 'PASS_NARRATIVE_SOURCE_AND_BUILD_CHECKS','checks':checks,'failed':failed,'documents':documents,'abstract_words':len(words(a)),'new_research':False}
    (QA/'story_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(checks),'failed':failed,'documents':documents,'abstract_words':len(words(a))},ensure_ascii=False))
    if failed:raise SystemExit(1)


if __name__=='__main__':main()
