---
title: "Incremental Telemetry for Wind-Power Shortfall Decisions under a Fixed Forecast Commitment"
author:
  - |
    Junyu Li and Juntao Du\
    \small School of Statistics and Applied Mathematics,\
    \small Anhui University of Finance and Economics, Bengbu 233030, China\
    \small Correspondence: Juntao Du, \texttt{dujuntao@aufe.edu.cn}
date: ""
lang: en-GB
documentclass: article
fontsize: 11pt
geometry: margin=25mm
mainfont: TeX Gyre Termes
mathfont: TeX Gyre Termes Math
bibliography: references.bib
csl: american-medical-association.csl
link-citations: true
numbersections: true
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{microtype}
  - \usepackage{caption}
  - \captionsetup{font=small,labelfont=bf}
  - \setlength{\emergencystretch}{3em}
  - \widowpenalty=10000
  - \clubpenalty=10000
  - \providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
abstract: |
  A supplied wind-power forecast can be held fixed to assess the consequences of additional inputs to a downstream shortfall learner. We compare registered input recipes under common targets, separating historical selection from retrospective finite-family identification. At Hill of Towie, 2023 fitting and 2024 calibration and selection were frozen before access to 2025 measurements. Adding current active power to the common forecast, clock and turbine identifier gave 0.5641% higher proxy cost than a frozen history-rich reference. This is mean loss across five fixed fits, with risk checked for each fit. The archived approximate joint cost interval, [0.3575%, 0.7708%], was within the prespecified 2% margin; the maximum event-rate upper bound was 6.2025%, below 10%. Mean uncovered shortfall nevertheless increased by 2.1843%. A separate predeclared full-family analysis identified another historical calibration: its worst paired-cost upper bound was 0.9742%, its maximum event-rate upper bound was 9.7699%, and all 15 strictly smaller candidates were excluded. The primary calibration was not certified in that broader family. A 134-turbine development study identified no finite-family minimum. These are qualifications under a working dependent-day resampling approximation, not validated population-coverage or deployment guarantees. They quantify an input-versus-consequence trade-off conditional on a fixed forecast; wind and power histories remain upstream. The exact two-feed interface's operational need and realised resource savings remain unestablished.
---

**Running title:** Fixed-forecast wind-power telemetry assessment

**Keywords:** wind power; telemetry; shortfall decisions; conditional quantiles; noninferiority; resource requirements.

**Practitioner points**

- When a forecast is held fixed, compare additional input recipes using their cost and shortfall consequences.
- Report event-rate qualification alongside the amount of uncovered shortfall.
- Distinguish historically selected recipes from retrospective finite-family candidates.

# Introduction

Wind-power forecasts support decisions about how much shortfall to prepare for. Insufficient preparation leaves an uncovered deficit, whereas excessive preparation incurs a procurement burden. Dynamic reserve methods therefore evaluate forecast uncertainty and realised errors, including methods that take supplied point forecasts as inputs rather than improve those forecasts themselves [@sun2022dynamicreserve]. This motivates a controlled design question: if a forecast is held fixed, which additional inputs does a downstream shortfall learner need to meet declared evaluation criteria? Holding the forecast fixed makes the consequences of changing those inputs comparable.

Current-power conditioning and comparisons of small and large input sets are established in probabilistic wind-power forecasting. Pritchard evaluated extra covariates using complete-year holdouts and showed that different forecast attributes need not improve together [@pritchard2011shortterm]. Phipps and colleagues compared the location of ensemble post-processing, including a simpler final-power step, while Dantas and Browell separated uncertainty sources across forecast horizons [@phipps2022postprocessing; @dantas2026seamless]. Sun and colleagues evaluated forecast-derived reserves using both coverage and exceedance amounts [@sun2022dynamicreserve]. These studies establish power conditioning, cross-year comparison, simpler downstream processing and consequence-based reserve evaluation as prior knowledge. Our empirical comparison fixes a supplied forecast and evaluates the additional raw input recipes of a particular shortfall learner under joint cost and event-rate criteria.

Decision-based feature selection and smaller acceptable subsets also have methodological precedents. Serrano and colleagues select features by validation newsvendor cost; Kowal defines acceptable near-optimal families and their smallest members [@serrano2024featureselection; @kowal2022subset]. We use existing estimators and a registered resource order, not a new feature-selection theory. The empirical question is whether a historical input-and-calibration choice retains its declared qualification across a year, and how that differs from the capability identified retrospectively within the frozen family. The second assessment must both qualify a candidate and exclude every strictly smaller registered candidate. An unresolved smaller alternative cannot be treated as excluded. Supplementary Table S8 compares the actual tasks and the remaining empirical contribution against these six precedents.

We investigate those questions in a controlled wind-power shortfall task. All reserve policies receive the same point-forecast commitment and are scored against the same future-power target. The primary input comparison withholds pitch from the reserve layer and varies the additional wind-speed, active-power and reactive-power measurements. At Hill of Towie, the entire historical fitting, calibration and selection procedure was completed and frozen before the project's first measurement access to the 2025 archive. The primary analysis tests one historically selected low-input policy against one frozen richer-input reference. A separately declared secondary analysis assesses the full registered calibration grid in the confirmation year. Earlier development results from a 134-turbine dataset provide a contrasting case in which minimum identification was not achieved.

In the recorded confirmation population, a recipe adding current active power alongside the shared forecast retained the declared fixed-reference qualification with five raw inputs rather than 112. Its cost and mean uncovered shortfall were higher. A different frozen calibration was sufficient and resource-minimal in the retrospective full-family assessment, even though it had not qualified for historical selection; the WTB development study retained minimum-identification failures. These results quantify the consequences and calibration dependence of input reduction, conditional on the supplied forecast, registered fitted family and declared criteria.

# Materials and methods

## Forecast commitment, target and action

Let $t$ denote the reserve decision time on a ten-minute, end-of-interval grid, and let $i$ identify a turbine. The common interface supplies one corresponding point forecast $F_{i,t}$ for power at $t+6$. Its upstream model uses 36 wind-speed and active-power observations ending at $t-6$. Thus the reserve decision has a six-step lead, while the forecast has a twelve-step lead from its latest upstream input. Fixing this commitment isolates changes to the downstream learner from changes to the point forecast. The interface is deliberately restricted to this one forecast, clock, identity and the declared telemetry; it is not asserted to contain every forecast, update or message that might have arrived in a real system.

This is a controlled two-feed interface: fresh upstream observations are assumed at the forecast's input time, and reserve-layer restrictions are imposed separately. Forecast-derived reserve methods motivate studying a supplied forecast as an input [@sun2022dynamicreserve]. AEMO's August 2023 overview documents a SCADA--forecast--dispatch chain with frequent forecast updates [@aemo2023awefs]. That different interface does not establish the exact $t-6/t+6$ access contract here, and the material examined provides no operational requirement for its 112-to-5 raw-input reduction. The interpretation remains an assessment of registered recipes conditional on a fixed commitment.

The nonnegative shortfall target and uncovered deficit are

$$
S_{i,t}=\max\{F_{i,t}-P_{i,t+6},0\},\qquad
U_{i,t}(m)=\max\{S_{i,t}-R_{i,t}(m),0\},
$$

where $P$ is active power and $R_{i,t}(m)\geq0$ is the reserve action of policy $m$, both expressed in kW. The loss and strict shortfall event are

$$
C_{i,t}(m)=\Delta\,[R_{i,t}(m)+\rho U_{i,t}(m)],\qquad
V_{i,t}(m)=\mathbf{1}\{S_{i,t}>R_{i,t}(m)\},
$$

with $\Delta=1/6$ hour and the fixed penalty ratio $\rho=10$. The reported mean cost is consequently a kWh-equivalent proxy per valid turbine interval. It is not a monetary settlement. The target is one future ten-minute observation, not cumulative energy delivered throughout the intervening hour. Summing turbine losses also differs from a net shortfall at a point of common coupling; neither network deliverability nor reserve-provider constraints are represented.

All policies are scored on the same set of finite future active-power targets. Finite zero and negative values remain in that population. Input missingness does not select a different evaluation population for different policies. This alignment prevents an apparently favourable input subset from benefiting simply because it is evaluated on easier or more complete records.

## Incremental inputs and registered policies

Every learned reserve policy receives the common forecast, sine and cosine of time of day, and a normalised turbine identifier. These are four common columns. The pitch-withheld family then adds each nonempty combination of wind speed ($W$), active power ($P$) and reactive power ($Q$), using the most recently available 1, 6 or 36 observations. Together with the common-input-only policy, this gives 22 subsets. A suffix denotes history length: P1 adds current active power; WPQ36 adds all three 36-step histories. Their selected raw input widths are 5 and 112, respectively. Historical imputation and estimator-specific missingness indicators are described in Supplementary Section S2.3; these raw widths do not describe all transformed model columns.

Two frozen estimator recipes are used for each subset: histogram gradient boosting (HGB) and a multilayer perceptron (MLP). Quantile regression supplies the underlying loss principle [@koenker1978regression]; the estimators are comparators, not proposed methodological contributions. Both recipes are fitted to the 0.90 quantile target. The HGB implementation follows the gradient-boosting approach available in scikit-learn [@friedman2001greedy; @pedregosa2011scikit]. Each recipe has five fixed training instances, with seeds 201--205. A deterministic active-power persistence policy provides a simpler reference. Its implementation and missing-input fallback are specified in Supplementary Section S1.2.

A signed calibration offset is fitted from historical residuals at each $q\in\{0.90,0.925,0.95,0.975,0.99\}$. An action is the nonnegative calibrated prediction. Importantly, $q$ labels the residual-offset calibration; it does not label a newly trained quantile model. The q=.95 primary candidate and q=.925 secondary candidate use the same fitted predictor and different historical offsets. The 44 learned recipes and persistence reference, crossed with five offsets, give 225 pitch-withheld policies. Five secondary information conditions use six prespecified subsets, producing 65 policies per condition. When pitch is available in these secondary conditions, its available history is shared by the learned policies; a label such as P1 therefore does not describe the same total information in every condition.

Resource requirements are ordered lexicographically by the registered tuple

$$
r(m)=(\text{additional telemetry channels},\ 
\text{learned predictor passes},\ 
\text{raw reserve input width}).
$$

For example, pitch-withheld P1/HGB has $r=(1,1,5)$. This is a functional order within the declared family. It does not rank all possible implementations, processing time, memory, communication payloads or physical sensor requirements. In particular, the common upstream forecast continues to use wind and power histories.

## Qualification against a fixed reference

Let $\bar C_m$ be cost averaged over recorded finite-target turbine intervals and then over the five fixed fitted instances, and let $V_{m,s}$ be the recorded event rate for fit $s$. These are descriptive statistics of the evaluation record. Write $\operatorname{UB}[\cdot]$ for the archived approximate upper bound, with its working-process interpretation given below. For a historically selected recipe $m$ and frozen reference $b$, confirmation under the declared procedure requires

$$
\operatorname{UB}\!\left[\frac{\bar C_m}{\bar C_b}-1\right]\leq0.02,
\qquad
\max_s \operatorname{UB}[V_{m,s}]\leq0.10,
\qquad
\max_s \operatorname{UB}[V_{b,s}]\leq0.10.
$$

The reference must also have qualified historically. These are prespecified research requirements: a 2% mean-cost noninferiority margin and a 10% strict-event-rate cap, not an operator-approved service agreement. Cost qualification concerns the mean loss across the five archived fits, while event-rate qualification applies to each fit. Averaging five losses is not the loss of an ensemble-averaged action; neither an ensemble deployment nor arbitrary future retraining is evaluated. The requirements do not separately constrain mean uncovered shortfall, so procurement, uncovered deficit and event frequency are reported alongside loss.

The fixed reference is selected historically from the WPQ36 HGB and MLP recipes after calibration choice. The reference with the lowest historical mean cost among historically risk-qualified choices is retained. The procedure preserves an explicit unqualified fallback if none passes, but that fallback cannot support risk-matched confirmation. No confirmation-year model is substituted for the frozen reference.

## Near-optimality and finite-family minimum identification

The secondary analysis asks a stronger, different question about the registered full-q family. A candidate must have event-rate upper bounds below the cap and a cost-ratio upper bound within the specified tolerance against every possibly risk-feasible competitor. A competitor remains possibly feasible unless at least one instance's event-rate lower bound exceeds the cap. Keeping unresolved competitors in this comparison prevents uncertain alternatives from disappearing merely because they have not qualified.

Among sufficient candidates, the least resource tuple is recorded with all ties. Calling that tuple an identified finite-family minimum additionally requires exclusion of every strictly smaller policy. A smaller candidate is excluded either by an event-rate lower bound above the cap, or by a cost-ratio lower bound above the tolerance relative to a risk-qualified witness. A candidate with inconclusive bounds is unresolved, not excluded. The outcomes are accordingly separated into no certified sufficient policy, sufficient policy with unresolved minimality, and identified finite-family minimum. The procedure concerns the registered candidate family only; it does not establish a minimum over arbitrary functions.

# Data and evaluation protocol

## Development and confirmation sources

The development analysis uses the public SDWPF dataset, referred to here as WTB, with 134 turbines on a ten-minute grid [@zhou2024sdwpfdata; @zhou2024sdwpfdataset]. Its evaluated 35-day window had already been viewed during development. It therefore supplies evidence about identification boundaries, not an independent test for newly formed explanations. Four nested fitting budgets, 10,000, 40,000, 120,000 and 360,000 rows, are evaluated for the pitch-withheld subsets; the secondary pressure comparisons use the registered smaller set of budgets and subsets. Increasing these budgets adds training rows, not independent evaluation weather periods.

The confirmation source is Hill of Towie version 2.1.0, a public archive covering 21 turbines [@clerc2026towie]. The study binds the 2023, 2024 and 2025 annual archives from that specific version. Time is interpreted as UTC interval end. Duplicate records are accepted only when all consumed raw fields agree; conflicting consumed values fail source qualification. Missing grid entries remain missing. Historical transformations, including pitch aggregation, are fixed before confirmation access. No turbine or timestamp is excluded on the basis of pitch availability, operating state, alarm or documented control interventions. This retains the source's operational mixture rather than claiming a homogeneous uncontrolled operating regime.

Table 1 summarises the common task and the primary comparison. The supplementary material provides the complete input lattice, estimator settings, population counts and source handling rules.

| Element | Registered specification |
|:--|:--|
| Primary source and period | Hill of Towie, 21 turbines; 2025 confirmation after 2023 fitting and 2024 calibration/selection |
| Common scoring population | 1,059,248 recorded finite future-power turbine intervals; zero and negative power retained; unrecorded targets not evaluated |
| Target and action | Shortfall at issue+6; nonnegative turbine-level reserve action; one ten-minute target |
| Shared information | Forecast based on 36 W/P observations through issue−6; reserve clock and turbine identifier |
| Historically selected candidate | P1/HGB/q=.95; current active power added; 5 raw learner columns |
| Frozen richer-input reference | WPQ36/HGB/q=.95; W/P/Q histories added; 112 raw learner columns |
| Primary requirements | Mean-cost ratio upper bound ≤2%; all five instance event-rate upper bounds ≤10% for both policies |
| Secondary responsibilities | Full-q finite-family identification; other information conditions and tolerances; 1/7-day block sensitivities |

Table: Task, population and information responsibilities of the primary comparison. W, P and Q denote wind speed, active power and reactive power. The upstream forecast is shared, so the learner column counts are incremental decision-layer quantities.

## Historical stages and actual freeze

The common point forecaster is fitted on January--June 2023, reserve predictors on July--December 2023, calibration offsets on January--June 2024, and calibration/policy choices on July--December 2024. Stage boundaries remove late issues whose future target and one-step release would not precede the next stage. The point-fitting boundary is also trimmed so its labels mature before the first reserve-stage forecast publication. Transformations and MLP scaling use the appropriate historical fitting stage, not confirmation observations.

Historical calibration choice first identifies, for each estimator/subset recipe, the lowest-cost q whose five event-rate upper bounds meet the cap. A failure to qualify is retained explicitly. The resulting historically chosen recipes are compared at the registered cost tolerances and resource order; all minimum-resource ties are retained. This selection uses neither 2025 outcomes nor a test-year reference winner.

The complete historical package and executable procedure were frozen and validated before a single release of measurement access to the 2025 archive on 19 October 2026. Figure 1 distinguishes this execution sequence from the dates represented by the data; the exact creation, validation and release records are given in Supplementary Section S5.2. The primary pitch-withheld selection was P1/HGB/q=.95, with WPQ36/HGB/q=.95 as its qualified reference. The full secondary q grid, information conditions and analysis responsibilities were also specified before release. No subsequent fit, calibration change or candidate expansion was used to obtain the reported confirmation findings.

![Shared information and the frozen cross-year evaluation. The upper panel separates the upstream forecast inputs from additional reserve-layer telemetry. Arrows describe data flow, not an identified physical causal mechanism. The lower panel shows the four historical stages and the 2025 confirmation period; actual historical freeze precedes the exclusive archive-release event. Reserve-layer delays are imposed conditions within a synthetic two-feed clock, not measured industrial arrival times.](figures/fig1_information_freeze.pdf){width=100%}

## Paired inference and secondary comparisons

The completed inference aggregates numerators and valid-target denominators by natural UTC day, retaining all turbines together. The same circular day-block draws are shared across policies, instances and information conditions. This preserves the paired weather sequence rather than treating turbines or training seeds as independent weather replications. Block-based inference addresses temporal dependence under assumptions about the underlying sequence [@kunsch1989jackknife]. Here, the primary block span is three days; one- and seven-day spans are separate sensitivity analyses.

The procedure uses 20,000 draws, alpha=.05, and a maximum-standardised-deviation envelope for the instance event rates and paired mean-cost ratios. The primary family contains the two frozen policies only. The broader secondary family spans all six information conditions and their complete registered q grids. Primary and secondary results consequently have different comparators and simultaneous envelopes; Supplementary Section S3 gives the complete coordinate accounting.

The finite-record means and rates are known once the recorded targets and fixed actions are given. Uncertainty statements concern a separate working interpretation: daily vectors of eligible counts, costs and events are treated as observations from a repeatable process under the same source and measurement regime. Its population counterparts are ratios of expected daily numerators to expected eligible counts, conditional on the frozen forecaster, access rule, reserve fits and offsets; Supplementary Section S3.1 gives the definitions. They are not empirical evidence that the actual year follows this process. The approximation requires sufficiently weak temporal dependence and a stable enough daily law for the chosen blocks. Annual seasonality, control changes and clustered missingness can violate these conditions; no nominal-coverage validation is available here.

Accordingly, qualifications are reported under the archived dependent-day approximation for the recorded-target setting. They are not confidence guarantees for the known finite-year statistics, unrecorded operating periods or a subsequent year. Primary and secondary families each use alpha=.05 separately; the article supplies no single joint 95% statement over both families and all block spans. The one- and seven-day sensitivities do not establish coverage. All tolerances within one secondary family reuse its same bounds.

Secondary tolerances are 0%, 0.5%, 1%, 2% and 5%. The five secondary information conditions retain pitch and impose reserve-layer delays of 0, 10, 20, 30 or 60 minutes. They are stress comparisons with a partial input lattice. Their frequency in commercial systems is not inferred. We separately report confirmation of fixed historical choices and retrospective full-family capability in 2025, including no-selection and nonconfirmation outcomes.

# Results

## A low-input policy meets the fixed-reference requirements at a positive cost premium

The historically selected P1/HGB/q=.95 recipe satisfied the registered primary requirements against WPQ36/HGB/q=.95 under the archived approximation. This assessment uses mean cost across five fixed fits and event rate for each fit on the recorded 2025 targets. Mean costs were 67.020403 and 66.644430 kWh-equivalent per valid turbine interval, respectively. The paired cost premium was **+0.5641%**, with an approximate joint interval of **[+0.3575%, +0.7708%]**. Its upper endpoint was below the prespecified 2% margin (Figure 2a). The interval is positive: the result is qualification at that margin, with higher cost, rather than a cost reduction.

All five fixed candidate instances also satisfied the event-rate requirement. The maximum candidate upper bound was **6.2025%**, compared with **6.2004%** for the reference; both were below 10% (Figure 2b). These are instance-specific bounds under the shared-day envelope, not uncertainty estimates from five independent years. Together with the historical qualification of the reference, they support the specified fixed-reference confirmation. They do not compare the candidate with every policy in the larger q family.

![Primary confirmation of P1/HGB/q=.95 against the frozen WPQ36/HGB/q=.95 reference. The cost panel shows the paired five-instance mean-cost premium and its archived approximate joint interval, with zero and the prespecified 2% margin marked. The event-rate panel shows each fixed instance's point estimate and bounds for both policies, with the 10% cap. All results use the same 1,059,248 valid turbine intervals and primary three-day shared-block envelope. Training instances are not independent weather replications.](figures/fig2_primary_confirmation.pdf){width=100%}

## Similar procurement and event frequency conceal higher uncovered shortfall

The archived point accounting shows where the cost premium arose. Average reserve procurement changed only slightly, from 49.299980 to 49.297089 interval-equivalent units, while mean uncovered shortfall increased from 1.734445 to 1.772331 (Table 2). The latter is a **2.1843% increase**, with positive point differences in all five instances. These accounting values have no additional severity-specific confidence interval; they should not be presented as a new significance test.

The mean strict-event rate was almost unchanged, decreasing from 5.533378% to 5.531339%, a difference of approximately −0.002039 percentage points. Thus the small reduction in event frequency did not imply a reduction in uncovered amount. The loss decomposition $\bar C=\overline{\Delta R}+10\overline{\Delta U}$ assigns the larger uncovered amount a direct cost consequence. Reporting only whether the event-rate cap was met would conceal that trade-off.

| Quantity | WPQ36/HGB/q=.95 | P1/HGB/q=.95 | Candidate minus reference |
|:--|--:|--:|--:|
| Procurement, $\overline{\Delta R}$ | 49.299980 | 49.297089 | −0.002890 |
| Uncovered shortfall, $\overline{\Delta U}$ | 1.734445 | 1.772331 | +0.037886 |
| Proxy cost, $\bar C$ | 66.644430 | 67.020403 | +0.375973 |
| Strict-event rate (%) | 5.533378 | 5.531339 | −0.002039 pp |

Table: Archived primary-comparison point accounting, averaged over the five fixed instances on the common population. Procurement and uncovered shortfall are kWh per valid turbine interval; cost is kWh-equivalent per valid turbine interval with penalty ratio 10. Differences are calculated before rounding. These rows do not supply new marginal confidence intervals. The paired cost interval is reported separately in Figure 2; pp denotes percentage points.

## A different calibration identifies a finite-family resource minimum

The predeclared secondary full-q analysis identified **P1/HGB/q=.925** as a resource-minimal sufficient policy in the pitch-withheld family at the 2% tolerance. Its mean cost was 65.739232, its maximum instance event-rate upper bound was 9.7699%, and its resource tuple was $(1,1,5)$. All 15 strictly smaller registered policies were excluded: two through risk lower bounds above the cap and 13 through cost lower bounds relative to risk-qualified witnesses (Figure 3; Supplementary Table S4).

The cost-sufficiency step precedes those exclusions. The archived worst paired-cost upper bound across all possibly feasible competitors was **0.9742%** for q=.925, below 2%. For the primary q=.95 recipe it was **3.5178%**, above 2% (Figure 3a); its maximum event-rate upper bound in this broader family was 6.7049% (Figure 3b). Both worst cost upper bounds were controlled by PQ36/HGB/q=.90, which was only possibly feasible, not risk-qualified. Its maximum event-rate upper bound was 11.5257%. The reference status of this competitor therefore cannot be described as established feasibility or established superior performance.

The distinction does not depend only on that uncertain competitor: q=.95 also lacked a cost upper bound within 2% against the qualified PQ6/PQ36/WPQ36 recipes at q=.925. Their corresponding cost lower bounds remained below 2%, so the result is **failure to certify**, not proof that the true cost premium exceeds 2%. For the 15 smaller-policy exclusions, the PQ6 and PQ36 witnesses at q=.925 were risk-qualified, with maximum upper bounds of 9.7564% and 9.6598%. Their stored cost lower bounds and qualification fields are supplied together in the supplementary evidence tables.

This result is distinct from the primary confirmation. The primary q=.95 policy was **not in the full-q 2% sufficient set**. It passed against the frozen q=.95 reference, but that does not establish near-optimality against all possibly feasible policies and calibration levels. The secondary q=.925 result identifies a capability within a family whose fits and offsets were already frozen; it does not show that historical selection chose that minimum in advance. The two results can coexist without changing either requirement.

The historical selection explains why q=.925 was not the primary choice. Its 2024 selection-period event-rate upper bounds ranged from 11.0174% to 11.0719%, failing the 10% qualification criterion despite its lower point cost. The q=.95 calibration qualified historically. The confirmation-year capability of q=.925 is a retrospective result, not permission to replace that original selection. These records explain a change in qualification across stages, not its physical cause.

The resource minimum concerns the declared lexicographic order, not uniqueness among all functions or all equally resource-intensive implementations. The 15 smaller candidates comprise the registered common-input-only learned recipes and the persistence reference across their calibration levels. Excluding them does not exclude every conceivable constant, rule-based or alternative learned policy. The full list of witnesses is provided so the scope of minimum identification can be checked directly.

![Secondary finite-family qualification under pitch withholding at the 2% tolerance. Panel a shows the stored worst paired-cost upper bound across possibly feasible competitors for q=.925 and the historical primary choice q=.95; these are upper bounds, not point estimates or newly estimated intervals. The diamond marks the secondary candidate and the star the historical choice. Panel b shows maximum fit-specific event-rate upper bounds under the same 74,500-coordinate secondary envelope. The dashed lines mark the original 2% and 10% criteria. Panel c accounts for all 15 strictly smaller candidates, with two risk exclusions and 13 cost-witness exclusions. The worst cost competitor is possibly feasible rather than risk-qualified; the witnesses for cost exclusion are qualified. Failure of an upper bound to pass does not prove a true cost excess. These secondary results are distinct from the primary 14-coordinate comparison in Figure 2.](figures/fig3_secondary_minimality.pdf){width=100%}

## Minimum identification depends on the evaluated setting and tolerance

The full secondary grid did not always identify a minimum. Across six conditions, five tolerances and three block spans, 46 of the 90 dependent assessments identified a finite-family minimum, 26 retained unresolved smaller alternatives, and 18 had no certified sufficient policy. Figure 4 shows classifications for the three-day secondary analysis; the complete one- and seven-day classifications appear in the supplement. These counts describe a sensitivity grid sharing the same data, not a success rate across independent operational trials.

For the pitch-withheld 2% secondary result, both the one- and seven-day analyses identified the same resource minimum. Their maximum instance risk upper bounds were 9.6015% and 9.8752%, respectively. This stability concerns the registered classification under those block choices. It does not prove the nominal temporal coverage or eliminate uncertainty from annual operating changes.

The fixed-history-set secondary assessments had a different responsibility: 63 were confirmed, 24 had no historical selection, and three did not establish confirmation. All three nonconfirmations concerned the same 30-minute-delay, 0.5%-tolerance setting under the three block spans. They are not three independent failures. HGB/MLP ties at the 5% margin were retained, so the results also do not establish universal dominance of a non-neural estimator.

The WTB development study supplies a clear nonidentification case. Across 14 registered condition/budget settings and two analysis responsibilities, all 28 three-day, 2% assessments contained risk-qualified policies, but none certified a sufficient candidate. At the prespecified 5% sensitivity margin, the historical-recipe analysis found a current P/Q HGB candidate for all four pitch-withheld training budgets. Nevertheless, across all 420 dependent development assessments, 367 had no certified sufficient policy and 53 left smaller alternatives unresolved; **none identified finite-family minimality**. Failure to identify a minimum is not proof that no useful low-input policy exists. The data sources, fitting budgets, weather windows and candidate families differ, so their contrasting outcomes do not isolate a physical or sample-size explanation.

![Identification boundaries in the completed evaluation grids. The Hill of Towie panel distinguishes identified finite-family minima, unresolved minimality and no certified sufficient policy for the primary three-day block span. The WTB panel displays only registered condition/budget cells for the 2% analysis; unrun budget cells are marked separately. Its historical-recipe and full-q assessments both fail to certify sufficiency in the displayed settings. Colours encode classifications, not effect sizes or independent replication counts; complete sensitivity cases are supplied in the supplementary source tables.](figures/fig4_identification_boundary.pdf){width=100%}

\clearpage

# Discussion

## What the results add to telemetry decisions

At Hill of Towie, reducing the registered reserve learner from 112 raw inputs to five retained fixed-reference qualification under the archived approximation. Keeping all three downstream histories was not required for that fitted recipe to pass those particular criteria. The upstream wind and power histories remain available to both recipes, and Table 2 identifies the increased uncovered amount accompanying the reduction. The result thus supplies a quantified comparison of downstream input designs conditional on an unchanged forecast. It does not establish the intrinsic information content of a channel, nor isolate redundant information from estimation and optimisation effects in the two fixed learners.

The practical magnitude is a trade-off rather than an unqualified improvement. The P1 learner consumes five columns instead of 112, but its proxy cost is higher and its uncovered shortfall amount increases. Whether a user would accept that exchange depends on an actual constraint on the reserve interface and on which consequences matter. The present 2% and 10% limits define the research comparison; they do not establish that an operator accepts those consequences. The event-rate and shortfall decomposition is therefore central to interpreting the input reduction, rather than an optional diagnostic.

The implementation also does not realise all of the resource reductions suggested by the learner widths. It builds the common 148-column feature matrix before selecting a subset, and the shared point forecaster still consumes its original inputs. Archived fit times and model-file sizes cannot establish controlled online latency or end-to-end cost savings. The evidence supports a smaller functional input specification for this learner, not a measured reduction in network traffic, peak memory, energy consumption or sensor expenditure.

## Qualification is not minimum identification

The q=.95 and q=.925 findings quantify how historical selection and retrospective capability can differ. The more conservative offset qualified historically, whereas q=.925 did not; in 2025 the latter qualified and the former lacked full-family cost certification. The direct upper-bound comparisons in Figure 3 make this a checkable consequence of the frozen calibration choices and comparison rules. They do not establish why risk qualification changed or identify a new physical wind-farm mechanism. Reporting only the secondary winner would replace the original question, while reporting only the primary pass would omit the broader family comparison.

This separation complements, rather than replaces, earlier work on quantile conditioning, dynamic reserves and decision-based variable selection [@pritchard2011shortterm; @sun2022dynamicreserve; @serrano2024featureselection]. The additional knowledge here is the observed cross-year premium, its severity decomposition, and the explicit smaller-candidate exclusions in a common wind-power task. The WTB nonidentification results show why finding a low-resource qualified candidate is insufficient evidence of a true minimum. The different outcomes cannot be interpreted as a universal rule favouring current power, HGB, a particular history length or a particular calibration.

## Scope of inference and application

The confirmation concerns one year at one farm, conditional on five fixed fitted instances and finite future-power observations. The annual archive was sealed for this project's original frozen comparison, rather than being globally unseen public data. Subsequent use of that year to develop another explanation would require a different confirmation claim. Retaining this distinction preserves the original temporal separation without granting perpetual independent-test status to the same observations.

The temporal bounds depend on the working repeatable-day process described in Methods. A finite-year average is observed; coverage of a population counterpart additionally requires that process approximation. Seasons, persistent weather, control changes and clustered missingness may invalidate it. Agreement across one-, three- and seven-day blocks is sensitivity evidence for the registered classification, not a validation of nominal coverage. Separate turbines and seed instances do not create independent years, and the mean loss over fits is not an ensemble-action loss.

Finally, the outcome is a turbine-level shortfall proxy under a controlled single-forecast, two-feed clock. General forecast-derived reserve practice does not establish this exact access contract. The operator and source material examined here does not establish why this downstream interface must retain that forecast version, why channel count should take priority over other resources, or what benefit the raw-input reduction would realise. These remain application gaps. The comparison also omits plant-level netting, network limits and reserve activation constraints, so it cannot certify deliverability or economic value. Its supported use is to assess registered input recipes against an explicitly supplied commitment and stated consequences.

# Conclusions

This study assessed additional input recipes for a fixed wind-power forecast and shortfall task. After historical fitting, calibration and selection were frozen, the recipe adding current active power to a shared forecast, clock and turbine identifier passed the original fixed-reference procedure on recorded Hill of Towie targets. Assessed by mean cost across five archived fits and risk for each fit, its cost was 0.5641% higher, with an approximate upper bound of 0.7708% against the 2% margin; its maximum event-rate upper bound was 6.2025%. Mean uncovered shortfall increased by 2.1843%, so qualification did not improve every consequence.

A separate predeclared secondary analysis qualified another historical calibration, with worst cost upper bound 0.9742%, maximum event-rate upper bound 9.7699% and all 15 smaller registered candidates excluded. The primary calibration was not certified in that full family; the WTB development study identified no finite-family minimum. These classifications use a working dependent-day approximation whose nominal coverage is unvalidated. The empirical contribution is a quantified input-versus-consequence comparison and the separation of historical selection from retrospective capability in this fixed interface. Operational need, realised resource benefits and deployment acceptability remain open.

# Data and code availability {.unnumbered}

The public data sources are SDWPF and Hill of Towie version 2.1.0 [@zhou2024sdwpfdata; @clerc2026towie]. Only the already acquired 2023--2025 Hill of Towie archives are used here. A companion review package assembles existing statistical aggregates, relevant settings, calibration choices, loss accounts, exclusion witnesses and portable verification code. It supports checking the reported decisions and figure-source quantities from completed outputs without raw measurements, model inference or resampling. Original weights, full actions and fitting indices are not included; their earlier manifests do not establish current local availability. Reproducing training or the original bootstrap is a different responsibility requiring the original data and research environment. The package is prepared locally for review; a permanent public deposit and author-approved release terms remain to be assigned. It is not represented as an already public, end-to-end reproduction archive.

# References {.unnumbered}

::: {#refs}
:::
