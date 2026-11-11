"""Format existing scientific result tables for the narrative manuscript."""
from pathlib import Path
import csv
import json
import re

HERE=Path(__file__).resolve().parents[1]


def rows(name):
    with (HERE/'source_data/table_inputs'/name).open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.reader(handle))


def md(data):
    return '| '+' | '.join(data[0])+' |\n| '+' | '.join(['---']*len(data[0]))+' |\n'+''.join('| '+' | '.join(r)+' |\n' for r in data[1:])


def main():
    common=json.loads((HERE/'source_data/M_controls_summary.json').read_text())
    data=[['Estimator','Input','R','U','C','V (%)']]
    for est in ['HGB','MLP']:
        for cell,label in [('OP6','Power update'),('OPZ6','Power + pitch update')]:
            i=common['labels'].index('Common:'+est+':'+cell)
            data.append([est,label,*[f"{common['mean_metrics'][k][i]:.3f}" for k in ['R','U','C']],f"{100*common['mean_metrics']['V'][i]:.2f}"])
    with (HERE/'tables/table1.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        csv.writer(handle).writerows(data)
    body=[r'\begin{table}[H]',r'\centering',
          r'\caption*{\textbf{Table 1. Action consequences after a power refresh.} Five-fit means under the shared calibration level. Procurement $R$ and uncovered shortfall $U$ are proxy kWh per valid turbine-interval; cost $C$ is kWh-equivalent and $V$ is event frequency. Both input configurations satisfy the event upper-bound requirement for each estimator.}',
          r'\small',r'\begin{tabular}{llrrrr}',r'\toprule',
          r'Estimator & Input & $R$ & $U$ & $C$ & $V$ (\%) \\',r'\midrule']
    for row in data[1:]:body.append(' & '.join(row)+r' \\')
    body.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}'])
    (HERE/'tables/table1.tex').write_text('\n'.join(body)+'\n',encoding='utf-8')
    # Keep complete original result rows, changing reader-facing labels only.
    old_names={'Original':'Individual','Common':'Shared'}
    tables={}
    for name in ['tableS2','tableS3','tableS4','tableS5','tableS6']:
        data=rows(name+'.csv')
        if name in ['tableS2','tableS3','tableS6']:
            for r in data[1:]:r[0]=old_names.get(r[0],r[0])
        if name=='tableS4':
            labels={'B-A':'Direct histories − base','C-B':'Recovered pitch − direct histories','C-WindScore':'Recovered pitch − base-score control',
                    'C-ShuffledScore':'Recovered pitch − shuffled-score control','E-B':'Compressed head − direct histories','D-B':'Measured pitch − direct histories'}
            for r in data[1:]:r[0]=labels[r[0]]
        tables[name]=md(data)
        (HERE/'tables'/f'{name}.md').write_text(tables[name],encoding='utf-8')
        with (HERE/'tables'/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as handle:csv.writer(handle).writerows(data)
    joint=[['Estimator','Calibration','Pitch benefit','Power substitution','Uniformly small pitch increment']]
    for e in ['HGB','MLP']:
        for recipe in ['Original','Common']:
            flags=common['corrected_routes'][recipe+':'+e]
            joint.append([e,old_names[recipe],*['Established' if flags[k] else 'Not established' for k in ['A','B','C']]])
    tables['tableS7']=md(joint)
    (HERE/'tables/tableS7.md').write_text(tables['tableS7'],encoding='utf-8')
    with (HERE/'tables/tableS7.csv').open('w',encoding='utf-8-sig',newline='') as handle:csv.writer(handle).writerows(joint)
    risk=rows('tableS9.csv')
    risk[0]=['Estimator','Input','Individual primary (%)','Individual expanded (%)','Shared (%)']
    tables['tableS8']=md(risk)
    (HERE/'tables/tableS8.md').write_text(tables['tableS8'],encoding='utf-8')
    with (HERE/'tables/tableS8.csv').open('w',encoding='utf-8-sig',newline='') as handle:csv.writer(handle).writerows(risk)
    interval_rows=json.loads((HERE/'source_data/R_paired_intervals.json').read_text())
    complete=[r for r in interval_rows if r['metric']=='loss_sum' and r['block_span']==3]
    assert len(complete)==42
    with (HERE/'source_data/R_all_primary_cost_contrasts.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(complete[0]));writer.writeheader();writer.writerows(complete)
    header=(HERE/'scripts/supplement_header.txt').read_text(encoding='utf-8')
    sections='''
# Supplementary Methods

## Information sets and populations

The source is SDWPF version2, comprising245 days of ten-minute measurements from134 turbines [@sdwpf2024]. Wind, active power, reactive power and mean blade angle define the physical inputs. The angle is available when all three blade measurements are finite. Finite power targets, including zero and negative export, are retained.

Every model receives the common forecast, issue-clock sine/cosine and normalised turbine identifier. In the measurement comparison, Fresh uses36 wind/active/reactive-power slots and six power summaries. Old masks the latest six slots without extending the window backwards. The summaries are the mean, population standard deviation, six-point least-squares slope, one-step difference, six-step difference and forecast-minus-last-power over the last arrived endpoints. Missing required observations make the corresponding summary missing. A power refresh adds current power, forecast-minus-current-power and current-minus-last-old-power. A pitch refresh adds the current three-blade mean.

The main measurement population requires finite future power, current power and all three current pitch values, producing671,538 cells per fit. Fitting and offset estimation use finite future targets; historical selection and evaluation use the main common population. An all-future-target population is supplied with the complete results. No change of population is used to compare input configurations.

In reconstruction, the base has40 raw columns: common4 plus36 wind-history values. Adding active- and reactive-power histories gives112. The pitch-supervised regressor uses these direct inputs to predict current pitch; the base-input control predicts the same target, and the shuffled control uses a historical permutation of pitch targets. Adding any score or measured current pitch gives113 decision inputs. The compressed head uses the40 base inputs and one recovered score, but generating that score still requires the direct histories.

Reconstruction decisions use672,939 finite-future-power cells. Pitch error uses finite-current-pitch cells; its count is also672,939, but its mask is different. Prediction error and decision loss therefore describe different target-validity populations. Additional comparisons use fresh or delayed histories with arrived pitch, as specified in Supplementary Data1. The wind-bin reference uses last-arrived wind and a global missing fallback; it has a restricted information set.

## Chronology and fitting

**Supplementary Table S1. Historical stages and evaluation periods.** Index intervals are zero-based and half-open. The point model predicts twelve steps ahead of its input endpoint; subsequent decision targets are six steps ahead of issue. Ends account for a one-step label release. The reconstruction pitch-fit forecast features at the beginning of that historical stage are retrospective with respect to nominal publication, as described below.

| Stage | Comparison | Dataset days | Issue indices |
|---|---|---|---|
| Point-model fit | Shared | 1–90 | [35,12947) |
| Pitch-regressor fit | Reconstruction | 91–135 | [12960,19433) |
| Decision-model fit | Both | 136–175 | [19440,25193) |
| Residual-offset fit | Reconstruction | 176–210 | [25200,30233) |
| Residual-offset fit | Measurement | 176–192 | [25200,27641) |
| Offset selection | Measurement | 193–210 | [27648,30233) |
| Evaluation | Both | 211–245 | [30240,35273) |

The point model's final consumed target is at12958 and its assumed release is12959. The first pitch-fit issue is12960 and its nominal forecast publication is12954. Publications for the first five issue times precede that release, and the sixth coincides. These six issue times are treated as retrospective historical feature fitting rather than an online-publication simulation. Later decision-stage publications follow the fitted-label boundary. The effect of a stricter historical trim has not been evaluated.

HGB uses100 boosting iterations, maximum15 leaves, minimum leaf size50, learning rate0.08, L2 regularisation1.0 and no early stopping. Point and pitch regressors use squared-error loss; decision heads use0.90 quantile loss. A training-fitted constant-zero imputer retains empty features and adds indicators. Reconstruction uses at most100,000 pitch-fit and120,000 decision-fit rows per fixed fit; measurement uses360,000 decision-fit rows. Shared row samples preserve pairing across the compared inputs.

The MLP has hidden layers of64 and32 ReLU units and trains for80 epochs with batch size2,048, AdamW learning rate0.001 and weight decay0.0001. Finite means/scales and missing indicators are derived from training data. The target scale is the larger of training-target standard deviation and one; initial output bias uses the training0.90 quantile on that scale. Five fits use seeds201–205. Computation used two CPU threads, Python3.11.16, NumPy2.4.6, scikit-learn1.9.1 and the recorded PyTorch2.11 environment for the MLP. Global training-quantile and fresh-power-persistence controls are included in the complete measurement results.

## Calibration and loss

Raw decision predictions are clipped at zero. A historical signed residual quantile $b_q=Q_q(S-a)$ calibrates the final action $r=\\max(a+b_q,0)$. Reconstruction uses $q=0.90$. Measurement individual calibration selects among0.90,0.925,0.95,0.975 and0.99. A level must satisfy all five historical event upper bounds; eligible levels minimise mean historical cost, breaking exact ties towards the higher level. Shared calibration fixes the smallest common qualifying level,0.925. The learner's training quantile remains0.90.

For pinball loss $\\ell_\\tau(u)=u(\\tau-\\mathbf1\\{u<0\\})$, the decision cost satisfies $C=(S+10\\ell_{0.90}(S-r))/6$. Thus absolute paired cost differences are rescaled pinball-loss differences on a common target. Relative cost contrasts use the stated reference-cost denominator. Figure4's procurement and weighted-shortfall quantities instead use the historical reference $C^*=40.04664774157611$.

Historical procurement controls apply a clipped signed constant shift to the model without added pitch. The shift matches mean procurement on days176–192 for every base/pitch offset pair, using no shortfall outcomes, then is evaluated without rematching. It may be negative when the pitch model buys less. Equal nominal quantiles and historical matching do not imply equal evaluation-period procurement.

## Temporal inference and joint criteria

Let $L_{sdk}$ be the total cost for fixed fit $s$, natural weather day $d$ and model $k$, with common valid count $N_d$. For block-draw multiplicities $w_{bd}$, the pooled draw is

$$
\\bar C_{bk}=\\frac{\\sum_d w_{bd}(\\sum_{s=1}^{5}L_{sdk}/5)}{\\sum_d w_{bd}N_d}.
$$

Per-fit event rates retain each fit's own event numerator. Candidates share the same draw; turbines and fits are not resampled as independent weather replicates. There are20,000 circular block draws, primarily spanning three natural dataset days, with one- and seven-day sensitivities. The analyses share the same35-day evaluation period.

Reconstruction uses Bonferroni percentile intervals for42 primary cost contrasts: seven pairs in six arrival conditions. Other endpoints and block spans are descriptive sensitivities. The primary measurement family contains70 per-fit risks,14 cost contrasts and70 signed severity coordinates, for154. Its historical family contains350 risks and100 cost coordinates. The expanded measurement comparison contains180 risks and52 comparisons, each contributing mean cost, five per-fit severity, mean shortfall and mean procurement coordinates, for596; its historical qualification family has1,100 risks. The maximum absolute bootstrap deviation, standardised by each coordinate's bootstrap standard deviation, supplies the simultaneous multiplier at alpha0.05. Non-algebraic zero-variance coordinates remain unbounded; risk bounds are clipped to probability limits. These are within-family approximations conditional on the fixed fitted models and retrospective analysis.

Three joint requirements retain their development thresholds. Important pitch benefit requires either the fresh-pitch or post-power pitch comparison to have qualified endpoints, a cost-gain lower bound above1%, and all five forward signed severity upper bounds at most0.001. Power substitution requires qualified endpoints, cost-gain lower bounds above1% for both older-history updates, a power-versus-pitch cost-premium upper bound at most1%, a residual-pitch cost-gain upper bound at most1%, and reverse severity upper bounds at most0.001 for replacing pitch by power and removing pitch after power. Uniformly small pitch increment requires qualified endpoints and cost-gain upper bounds at most1% in all three pitch contexts. Event qualification requires every fit's historical/evaluation responsibility to satisfy the10% upper-bound limit. Signed severity is $10(U_{\\rm candidate}-U_{\\rm reference})/C^*$.

# Supplementary Results

**Supplementary Table S2. Measurement configurations and action consequences.** Five-fit means on the common671,538-cell population. Cost is kWh-equivalent per cell; procurement and shortfall are proxy kWh per cell; event frequency is a percentage. Qualification uses the expanded comparison's endpoint requirements. Individual and shared refer to calibration; $q$ is the residual-offset level.

'''+tables['tableS2']+'''
**Supplementary Table S3. Measurement cost contrasts.** $G=(C_A-C_B)/C_A$ is the reference-to-added-input reduction; $D$ is power-minus-pitch cost relative to the pitch-update cost. Values are percentages with simultaneous intervals. The individual primary family154 and expanded family596 are reported separately; neither changes the point-cost ordering. Main Figure2 displays cost differences, reversing the sign and interval endpoints of $G$.

'''+tables['tableS3']+'''
**Supplementary Table S4. Reconstruction cost contrasts across temporal block lengths.** Units are kWh-equivalent per valid turbine-interval. Three-day bounds are the primary42-contrast cost family; one- and seven-day bounds are sensitivities. All six pitch-withheld comparisons are retained. The full42 primary contrasts and other endpoints accompany Supplementary Data1.

'''+tables['tableS4']+'''
![**Supplementary Figure S1. Temporal-block sensitivity of reconstruction results.** Paired cost differences and approximate95% interval endpoints for one-, three- and seven-day blocks. **a**, Direct histories and compression. **b**, Recovered/measured pitch and score controls on a smaller labelled scale. The three-day cost family is primary. Small pitch increments are not equally resolved at every block length.](figures/figS1_block_sensitivity.pdf){width=100%}

**Supplementary Table S5. Pitch reconstruction errors for the five fitted instances.** Mean squared error is in degree squared. The three columns use pitch targets with direct inputs, pitch targets with base inputs, or shuffled pitch targets with direct inputs. No error interval is inferred from the five points. This population is defined by finite current pitch and differs from the future-power-valid cost population.

'''+tables['tableS5']+'''
**Supplementary Table S6. Historical procurement matching in the evaluation period.** The control matches the pitch-added model's mean procurement in the historical offset period, then transfers without evaluation-period rematching. Cost, procurement, shortfall and event units follow TableS2. This is a historical constant-shift control, not an adaptive power-only policy.

'''+tables['tableS6']+'''
Historical matching did not establish equal-budget allocation value or matched-power sufficiency in any of the12 state-pair/estimator/calibration cases. For shared HGB after a power refresh, the matched model's event frequency reached20.07%, compared with5.00% for the pitch-added model, while procurement also differed. Shared MLP qualified the compared models on risk but its allocation/shortfall bounds remained unresolved. A restricted constant-increment calculation additionally shows that a uniform nonnegative increase in a fixed baseline action cannot reproduce all HGB shortfall changes at the observed mean procurement increment; this restriction does not exclude adaptive power-only calibration or another power learner.

**Supplementary Table S7. Joint criteria across estimators and calibration procedures.** These are combined cost, event and severity requirements, not tests that every component effect is zero. Important pitch benefit, power substitution and uniformly small pitch increment are defined in Supplementary Methods. Each configuration uses the same evaluation weather.

'''+tables['tableS7']+'''
The causes differ. In HGB, fresh/post-power pitch cost-gain upper bounds are below the1% important-benefit margin, whereas the old-history pitch upper bound permits a larger gain. Removing pitch after a power refresh also has adverse severity evidence: one shared-calibration fitted instance has $10\\Delta U/C^*$ interval [0.0028221,0.0124244], whose lower bound exceeds0.001. Individual calibration gives [0.0029770,0.0125835] for that instance. Common-calibration MLP qualifies all six main configurations on event risk but still meets none of the combined requirements; its cost/severity uncertainty is not the same as the HGB adverse bound. No direct measured-pitch-minus-recovered-score interval is available, so their separate contrasts against direct histories do not establish their ranking.

**Supplementary Table S8. Per-fit event qualification.** Each value is the maximum of five per-fit development upper bounds, in percent. A dagger denotes failure of the corresponding qualification. Primary and expanded families remain separate. A failed upper bound is not proof that population event probability exceeds10%.

'''+tables['tableS8']+'''
# Supplementary Data

Supplementary Data1 contains the full reconstruction comparisons, including other arrival conditions and metrics. Supplementary Data2 contains measurement results under individual calibration; Data3 contains the expanded shared-calibration and procurement-control comparisons. Figure/table source values and implementation specifications accompany these data. The original SDWPF measurements remain available from their versioned public source.

# Supplementary references

::: {#refs}
:::
'''
    # Space ordinary prose quantities without touching equations or citation keys.
    protected=re.split(r'(\$\$.*?\$\$|\$[^$\n]*\$|@[a-z]+\d{4})',sections,flags=re.S)
    for i in range(0,len(protected),2):
        part=protected[i].replace('TableS','Table S')
        part=re.sub(r'(?<=[a-z])(?=\d)',' ',part)
        part=re.sub(r'(?<=\d)(?=[A-Za-z])',' ',part)
        protected[i]=part
    (HERE/'supplementary.md').write_text(header+''.join(protected),encoding='utf-8')
    print('Scientific result tables and supplement formatted from existing fields.')


if __name__=='__main__':main()
