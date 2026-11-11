"""Project stored qualifications and predicate witnesses; no new inference."""
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((HERE / 'source_data' / name).read_text(encoding='utf-8'))


def write_table(name, columns, rows):
    text = '| ' + ' | '.join(columns) + ' |\n| ' + ' | '.join(['---']*len(columns)) + ' |\n'
    text += ''.join('| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)
    (HERE/'tables'/f'{name}.md').write_text(text, encoding='utf-8')
    with (HERE/'tables'/f'{name}.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle); writer.writerow(columns); writer.writerows(rows)
    return text


def main():
    original, later = load('M_original_summary.json'), load('M_controls_summary.json')
    protocol = load('M_protocol.json')
    thresholds = protocol['thresholds']
    assert thresholds['important_cost_gain'] == thresholds['substitution_margin'] == .01
    assert thresholds['risk_cap'] == .1 and thresholds['weighted_U_increment_over_Cstar'] == .001
    names = dict(zip(['F','FZ','O6','OP6','OZ6','OPZ6'],
                     ['Fresh','Fresh + pitch','Old','Old + power','Old + pitch','Old + power + pitch']))
    risk_rows = []
    for estimator in ['HGB','MLP']:
        for cell in names:
            key = f'{estimator}:{cell}'; old_index = original['labels'].index(key)
            old_upper = max(original['registered_intervals'][f'risk|{s}|{old_index}']['upper'] for s in range(5))
            values = [f'{100*old_upper:.4f}' + ('†' if not original['risk_qualified'][key] else '')]
            for recipe in ['Original','Common']:
                key2 = f'{recipe}:{key}'; index = later['labels'].index(key2)
                upper = max(later['interval'][f'risk|{s}|{index}']['upper'] for s in range(5))
                values.append(f'{100*upper:.4f}' + ('†' if not later['jointly_qualified'][key2] else ''))
            risk_rows.append([estimator,names[cell],*values])
    risk = write_table('tableS9', ['Estimator','Program','Original 154 (%)','Later Original 596 (%)','Common 596 (%)'], risk_rows)
    # Reproduce Boolean responsibilities from saved fields only. Bounds are not estimated here.
    pairs = {'fresh_state':('F','FZ','G'),'old_state':('O6','OZ6','G'),
             'old_power':('O6','OP6','G'),'P_premium_vs_Z':('OP6','OZ6','D'),
             'residual_state':('OP6','OPZ6','G'),'severity_P_vs_Z':('OZ6','OP6','G'),
             'severity_P_vs_PZ':('OPZ6','OP6','G')}
    guards = []
    route_check = {}
    def check_pair(prefix, route, branch, name, low=None, high=None, severity=False):
        a,b,kind = pairs[name]; passed = []
        for endpoint in [a,b]:
            field = f'jointly_qualified.{prefix}{endpoint}'
            value = later['jointly_qualified'][prefix+endpoint]
            guards.append([prefix[:-1],route,branch,name,'endpoint_qualification',field,'',value,'is_true',True,value])
            passed.append(value)
        if low is not None or high is not None:
            field = prefix+name+'|cost|'+kind
            obj = later['interval'][field]
            side,value,op,limit = ('lower',obj['lower'],'>',low) if low is not None else ('upper',obj['upper'],'<=',high)
            ok = value > limit if op == '>' else value <= limit
            guards.append([prefix[:-1],route,branch,name,'cost',f'interval.{field}.{side}','',value,op,limit,ok]);passed.append(ok)
        if severity:
            for s in range(5):
                field = prefix+name+'|instance_U|'+str(s); obj = later['interval'][field]; ok = obj['upper'] <= .001
                guards.append([prefix[:-1],route,branch,name,'signed_severity',f'interval.{field}.upper',201+s,obj['upper'],'<=',.001,ok]);passed.append(ok)
        return all(passed)
    summaries = []
    for recipe in ['Original','Common']:
        for estimator in ['HGB','MLP']:
            prefix = f'{recipe}:{estimator}:'
            aparts = [check_pair(prefix,'A',name,name,low=.01,severity=True) for name in ['fresh_state','residual_state']]
            bparts = [check_pair(prefix,'B',name,name,low=.01) for name in ['old_state','old_power']]
            bparts += [check_pair(prefix,'B',name,name,high=.01) for name in ['P_premium_vs_Z','residual_state']]
            bparts += [check_pair(prefix,'B',name,name,severity=True) for name in ['severity_P_vs_Z','severity_P_vs_PZ']]
            cparts = [check_pair(prefix,'C',name,name,high=.01) for name in ['fresh_state','old_state','residual_state']]
            calculated = {'A':any(aparts),'B':all(bparts),'C':all(cparts)}
            assert calculated == later['corrected_routes'][prefix[:-1]]
            route_check[prefix[:-1]] = calculated
            iv = later['interval']
            fresh = iv[prefix+'fresh_state|cost|G']; old = iv[prefix+'old_state|cost|G']; residual = iv[prefix+'residual_state|cost|G']
            if estimator == 'HGB':
                atext = f'Fresh and residual pitch cost-gain upper bounds are {100*fresh["upper"]:.4f}% and {100*residual["upper"]:.4f}%, below the 1% important-gain threshold.'
                rev = iv[prefix+'severity_P_vs_PZ|instance_U|3']
                btext = f'Old-pitch gain lower bound {100*old["lower"]:.4f}% does not exceed 1%; old-pitch endpoint unqualified. Removing pitch, fit204 severity interval [{rev["lower"]:.7f}, {rev["upper"]:.7f}] has lower bound above 0.001.'
            else:
                atext = f'Fresh and residual pitch gain lower bounds {100*fresh["lower"]:.4f}% and {100*residual["lower"]:.4f}% do not exceed 1%; important benefit is not established.'
                btext = f'Old-pitch gain lower bound {100*old["lower"]:.4f}% does not exceed 1%; residual-pitch gain upper bound {100*residual["upper"]:.4f}% exceeds the 1% substitution responsibility. Reverse severity bounds also do not qualify.'
            ctext = f'Old-pitch gain upper bound {100*old["upper"]:.4f}% exceeds 1%; uniformly low increment is unresolved.'
            summaries.extend([[recipe+' '+estimator,'A',atext],[recipe+' '+estimator,'B',btext],[recipe+' '+estimator,'C',ctext]])
    failure = write_table('tableS10',['Configuration','Claim','Representative stored failure witnesses'],summaries)
    with (HERE/'supplement_data/failure_guard_ledger.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(['configuration','route','branch','comparison','guard_type','source_field','fit_seed','stored_value','operator','original_limit','guard_passed']);writer.writerows(guards)
    (HERE/'qa/stored_predicate_check.json').write_text(json.dumps({'status':'MATCHES_ALL12_STORED_CORRECTED_ROUTES','family':596,'guard_rows':len(guards),'routes':route_check,'new_estimates':False,'thresholds_source':'source_data/M_protocol.json'},indent=2)+'\n',encoding='utf-8')
    literature_rows = [
        ['Pritchard [@pritchard2011]','Present-output quantiles and richer predictors; original reader and formula record.','Here: specified P/pitch refresh packages after a common forecast. No first-current-power claim.'],
        ['Iversen et al. [@iversen2017]','Latent dynamics and dynamic power curve; P versus P+wind observations. Author publisher PDF, relevant methods/tables.','Here: measured/recovered pitch and same-time P refresh; not a new latent-state principle.'],
        ['Kandemir et al. [@kandemir2026]','One-minute forecasting from seven SCADA predictors including blade angle, without autoregressive P; operation-based UQ and perturbation. Publisher PDF.','Here: direct P/Q history, fixed shortfall target, measured pitch versus P packages and recovered-score controls.'],
        ['Wang and Wang [@wang2026]','Public core: regime/horizon quantiles, conformal recalibration and reserve-relevant lower-bound violations. Publisher preview; final full methods unavailable.','Here: stated input-package and R/U/C/V task. Complete inputs and additional action comparisons remain unknown; no exclusion claim about the full article.'],
        ['Kometsi et al. [@kometsi2026]','SAFER calendar/generation states, CQR/ACI and block inference in public core. Final abstract and fixed author source commit; final article PDF unavailable.','Here: extra measured pitch versus a function of arrived inputs and historical supervision. Public code reading is not full-paper equivalence.'],
        ['Wen; Meng et al.; Stratigakos and Andrianesis [@wen2024; @meng2026; @stratigakos2026]','Adaptive or missing-data-tolerant forecasting, including power histories and availability patterns. Accepted/author texts; relevant methods and experiments.','Missing-data handling and informative P histories are established; here the target and incremental input packages differ.'],
        ['Bessa et al.; Zhao et al. [@bessa2011; @zhao2021]','Forecast quality/value and forecast-to-reserve evaluation have precedents. Bessa selected original sections; Zhao abstract/method index only.','Neither the quality/value distinction nor asymmetric loss is new here; no claims about uninspected full-paper analyses.']]
    literature = write_table('tableS7',['Prior work','Established scope and source basis','Bounded distinction'],literature_rows)
    clock_rows = [
        ['Point-fit consumed maximum index','1730194','Original 120,000-row saved sample, historical SHA256 matched.'],
        ['Last consumed point-input anchor','12946','35 + floor(1730194/134).'],
        ['Its target / assumed label release','12958 / 12959','Twelve-step target plus one-step release.'],
        ['First state-fit issue / nominal publication','12960 / 12954','Original stage start; publication=issue−6.'],
        ['First five state-fit issues','12960–12964','Their nominal publications are strictly earlier than release12959.'],
        ['Sixth state-fit issue','12965','Nominal publication12959 coincides with release; not strictly after.'],
        ['First decision-fit nominal publication','19434','After last point-fit label release, as are subsequent stages.']]
    clock = write_table('tableS8',['Quantity','Zero-based index/value','Interpretation'],clock_rows)
    sections = '''# Supplementary Methods: literature scope and clock qualification

**Supplementary Table S7. Closest-work responsibilities and reading limits.** Roles and complete metadata are retained in the literature matrix. These distinctions use known task definitions, not a global priority claim. SETA and SAFER final full-text overlap remains unverified. SAFER method-source commit is `3b0d501ce63425721c17d45cc76835af2846b24f`; source cells were read without execution or output retrieval.

'''+literature+'''
**Supplementary Table S8. Retrospective state-fit publication exception.** All coordinates and original rows are retained. The frozen source checks the final point-model label against the first state-fit issue, not its earlier nominal publication. The saved point-fit sample SHA256 is `9f1c3af8bc4345daca9cf637fbfac624cd65472b0f7e98928c347c226703b79d`.

'''+clock+'''
The point model's labels mature before the first state-fit issue, but not before all earliest nominal publications. We therefore treat those F values as retrospective historical training features. The retained model is not certified to have existed at each of those earlier publication times. No row deletion, retraining, recalibration or revised interval is performed. The effect of enforcing that stricter boundary on fitted probes and their later costs is unknown. Later decision-stage nominal publication is after the fitted-label boundary; this exception is not evidence of using future evaluation targets to train that forecast. The reconstruction study does not establish a fully replayed online-publication pipeline.

# Supplementary results: event qualification and failed combined claims

**Supplementary Table S9. Maximum fixed-fit development event upper bounds.** Values are percentages. Each entry is the maximum of five original per-fit upper bounds, used as a qualification witness rather than a new interval for a maximum. The original154 column uses its original qualification flag; later columns use the historical/development qualification flags of the596 diagnostic. A dagger denotes that source flag is false. Different families are not substituted for one another; a bound exceeding10% does not prove the population rate exceeds10%.

'''+risk+'''
**Supplementary Table S10. Failure witnesses for the twelve stored corrected-route outcomes.** All rows refer to the later596-coordinate family. A requires either fresh or residual pitch's important benefit; both alternatives fail. B requires its complete cost, endpoint and reverse-severity conjunction. C requires all three pitch contexts to have cost-gain upper bounds at most1% with qualified endpoints. The entries give representative reasons, not new criteria or a claim that every component fails. The complete204-row Boolean responsibility ledger is supplied separately with source fields. Common MLP qualifies all six native programs but still meets none of A/B/C. HGB's reverse-severity witness is an adverse finding for a specified replacement; MLP's unresolved bounds are not proof of no benefit. Severity entries use10ΔU/C*, not relative U change.

'''+failure
    path=HERE/'supplementary.md';text=path.read_text(encoding='utf-8')
    before,rest=text.split('<!-- REVISION_TABLES_BEGIN -->',1);_,after=rest.split('<!-- REVISION_TABLES_END -->',1)
    path.write_text(before+'<!-- REVISION_TABLES_BEGIN -->\n'+sections+'\n<!-- REVISION_TABLES_END -->'+after,encoding='utf-8')
    print('Stored risk, witness, clock and literature tables projected; no new statistics.')


if __name__ == '__main__':
    main()
