---
documentclass: article
classoption:
  - 11pt
geometry:
  - a4paper
  - margin=1in
mainfont: TeX Gyre Termes
mathfont: TeX Gyre Termes Math
bibliography: references.bib
csl: IEEE.csl
citeproc: true
link-citations: true
numbersections: true
secnumdepth: 3
date: ""
header-includes:
  - \usepackage[most]{tcolorbox}
  - \usepackage{enumitem}
  - \usepackage{tabularx}
  - \usepackage{booktabs}
  - \usepackage{caption}
  - \usepackage{float}
  - \usepackage{etoolbox}
  - \usepackage{xcolor}
  - \setlength{\parskip}{0.45em}
  - \setlength{\parindent}{1.2em}
  - \setlist[itemize]{leftmargin=1.6em}
  - \captionsetup[table]{font=small, labelfont=bf, labelsep=period, skip=4pt}
  - \definecolor{aegray}{HTML}{6E6E6E}
  - \definecolor{aelight}{HTML}{F3F4F6}
  - \definecolor{aeline}{HTML}{D7D9DC}
  - \definecolor{aecite}{HTML}{7A3EF0}
---

\begin{center}
\begin{minipage}{0.94\textwidth}
\centering
\Large\bfseries SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting\par
\vspace{0.6em}
\normalsize Junyu Li\textsuperscript{a}\qquad Juntao Du\textsuperscript{a,*}\par
\vspace{0.35em}
\small \textsuperscript{a} School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu, 233030, China\par
\end{minipage}
\end{center}

\vspace{0.05em}

\noindent{\scriptsize *Corresponding author.\par}
\noindent{\scriptsize Email addresses: \texttt{ljylikezmn999@gmail.com} (Junyu Li), \texttt{dujuntao@aufe.edu.cn} (Juntao Du)\par}

\vspace{0.35em}

\noindent{\small\bfseries Abstract\par}
\vspace{0.18em}
\small
Wind-farm reserve screening near the MPPT-to-pitch transition depends on knowing which control law is active, yet the threshold label that identifies it can be delayed, missing, or noisy exactly where over-forecasts create shortage exposure. We make this control-boundary assignment auditable and keep it usable when the label stream degrades, through SCADA-anchored, regime-aware routing. A node-level mixture-of-experts gate is constrained by operating anchors so each turbine-time route can be checked against a declared MPPT-to-pitch partition and issued, before future active power is observed, as a real-time operating-state diagnostic. On the KDD Cup 2022 benchmark, the boundary-forced router recovers the declared partition (NMI about 0.87, ARI about 0.92). Its operational value is robustness to label degradation: because the route reads live SCADA anchors rather than a confirmed threshold stream, it retains 0.960 early pitch-window recall under a six-step label delay while the delayed threshold rule falls to 0.196, and stays at 0.960 under 50% label availability versus 0.508 for the available-label rule. This auditable route has an explicitly reported accuracy trade-off (overall RMSE 236.13 versus 224.34 for iTransformer, the lowest-RMSE strict-cache forecasting baseline) and exposes transition-window reserve risk: at shortage-to-reserve cost ratio 10, gate-conditioned binning lowers same-router boundary-window shortage energy by 14.5% while carrying about 3.6% more reserve. The recovery is not specific to one benchmark: retrained on the independent ENGIE La Haute Borne farm, the router recovers the declared boundary at five-seed NMI 0.941; replay audits rule out active-power feedback (Patv-zero NMI 0.953) and show joint wind-speed/pitch anchors are load-bearing (joint-zero NMI 0.001). The Kelmarsh/Penmanshiel farms, lacking pitch observability, define the conditions cross-site transfer requires--sensor coverage, pitch observability, local boundary re-estimation, and a held-out routing check. The contribution is an auditable, label-degradation-robust control-boundary routing framework with quantified operating value, a measured accuracy trade-off, second-farm recovery, and explicit transfer conditions.

\vspace{0.25em}
\noindent{\small\textbf{Keywords:} Wind-turbine control boundary; SCADA-anchored routing; regime-aware forecasting; auditable routing; MPPT-to-pitch transition; mixture-of-experts.\par}

\normalsize

\vspace{0.55em}

# Highlights {.unnumbered}

- SCADA anchors make the MPPT-to-pitch control boundary auditable through routing.
- Regime gates recover the declared partition (NMI 0.87) at a measured RMSE cost.
- The gate keeps early pitch-window recall under delayed or missing threshold labels.
- Validation-frozen quantile baselines bound any reserve-policy claim honestly.
- Boundary recovers on a second anchor-observable farm; external gaps set gates.

# Nomenclature {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Nomenclature.} Core symbols, variables, and abbreviations.}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Symbol or term & Meaning \\
\midrule
$G=(V,E)$ & Wind-farm or grid graph with nodes $V$ and edges $E$ \\
$N$ & Number of turbines or grid nodes \\
$H$, $P$ & Input history length and forecast horizon length \\
$\mathbf{x}_{i,t}$, $y_{i,t}$ & Node feature vector and scalar active-power target \\
$\hat{y}_{i,t}$ & Forecasted active power at an evaluated horizon cell \\
$\bar{p}_{i,t}$ & Mean blade-pitch angle, reported as \texttt{Pab\_mean} \\
$\mathbf{g}_{i,t}$ & Node-level gate probability vector \\
$R_{i,t}$ & Declared primary operating-regime anchor label \\
$s_{i,t}$ & Over-forecast shortfall, $\max(\hat{y}_{i,t}-y_{i,t},0)$ \\
$r_{b,q}$ & Validation-calibrated reserve for bin $b$ and quantile $q$ \\
$\rho$ & Shortage-to-reserve cost ratio \\
$C$ & Normalized reserve procurement plus residual-shortage cost \\
MPPT & Maximum power point tracking \\
SCADA & Supervisory control and data acquisition \\
NMI, ARI & Normalized mutual information and adjusted Rand index \\
\bottomrule
\end{tabularx}
\end{table}
```

# Introduction

Wind-farm reserve screening near the transition from maximum power point tracking (MPPT) to blade-pitch control depends on knowing which control law is currently active, yet the threshold label that identifies it can arrive late, go missing, or turn noisy exactly where over-forecasts create shortage exposure. This makes the transition both operationally decisive and poorly observed: a forecaster must answer not only how large the error is, but which operating state generated the local response. In the MPPT region, power responds strongly to wind-speed variation; as pitch control activates near rated operation, the local power-response law changes. A small forecast error near rated wind can cross a different control law, yet the transition occupies a smaller share of normal operation, so its effect can be diluted in fleet-average RMSE while still concentrating local risk. A useful forecasting system for this setting must therefore expose the operating boundary that produced each forecast and stay usable when the label stream degrades, not only report aggregate accuracy.

State-of-the-art spatio-temporal forecasters now model turbine coupling, wake interaction, dynamic dependence, and sensor-rich wind-farm layouts [@wu2019graphwavenet; @park2019physicsinduced; @yu2020sgnn; @kim2024lidarscada; @daenens2025offshore]. These models set the accuracy reference, but a low-error graph encoder does not by itself tell a reserve planner whether the current local map is MPPT-like or pitch-control-like. Mixture-of-experts (MoE) routing can separate heterogeneous response laws, yet a gate trained only through prediction loss can specialize on partitions that have no operating meaning [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch; @shi2025timemoe]. The missing middle layer is an auditable routing assignment that identifies which physical response law is active at the anchor time and can then be used in reserve-risk diagnosis.

We make the routing decision itself the operating-boundary diagnostic. A node-level MoE gate is constrained by SCADA operating anchors so that each turbine-time assignment can be compared with a declared MPPT-to-pitch partition and issued before future active-power outcomes are observed. This supports degraded-label reserve screening: when thresholds are late, incomplete, or noisy, the operator still has a signal for early pitch-control entry. WTB is the source control-boundary benchmark because the aerodynamic boundary is partly hidden inside turbine-control action; ERA5 is retained as an observability contrast where the thermodynamic marker is more directly visible through sensible heat flux. The recovered gate is connected to validation-calibrated, test-frozen reserve diagnostics that report cost, violation rate, reserve energy, and shortage energy under declared shortage-to-reserve cost ratios. We further compare gate-bin reserve allocation with validation-frozen global and physical-bin quantile baselines. This positioning deliberately separates transition-window accountability from the conventional forecasting leaderboard and from claims of full dispatch optimality.

This paper makes three contributions. First, it introduces SCADA-anchored regime-aware routing as an auditable MPPT-to-pitch assignment whose semantics are fixed by operating anchors rather than post-hoc expert interpretation. Second, it quantifies degraded-label operating value: the gate keeps early pitch-window recall at 0.960 under six-step label delay and 50% label availability, while threshold rules fall to 0.196 and 0.508. Third, it delivers this operating-state layer at an explicitly priced and bounded cost rather than as a free lunch: the route improves a same-model boundary-window reserve rule at moderate cost ratios while carrying a measured 11.79-RMSE-unit price relative to the best strict-cache forecasting baseline, is checked against graph, Transformer, MLP-style, lag-feature, power-curve, persistence, DLinear-style, and quantile baselines, recovers the declared boundary on a second independent anchor-observable farm (ENGIE La Haute Borne, five-seed routing NMI 0.941), and converts the Kelmarsh/Penmanshiel coverage gaps into explicit deployment conditions rather than claiming automatic cross-farm generalization. The framing throughout is a complementary diagnostic layer for an already-deployed low-RMSE forecaster, not a replacement on the forecasting leaderboard.

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting has moved from single-site prediction toward spatio-temporal graph models that encode physical sources of error. Reviews identify ramp and uncertainty as recurrent operational risks [@pinson2013forecasting; @wang2025uncertaintyreview], while graph mechanisms provide the accuracy reference [@wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn]. Wind-specific extensions add wake-aware graphs, SCADA fields, and physics-guided constraints [@park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore]. The remaining gap is diagnostic: these models set the low-error benchmark, but they do not make the active turbine-control law visible to a reserve planner.

Regime-aware MoE routing separates local response laws, yet prediction loss alone need not produce a physically meaningful partition [@shazeer2017outrageously; @fedus2022switch; @shi2025timemoe]. Physics-guided learning offers the missing constraint principle [@karpatne2017tgds; @karniadakis2021piml; @parsa2025pimlreview], but for wind turbines that principle must pass through SCADA observability: operating-state labels depend on wind speed, pitch, and active power [@tautzweinert2017scada; @zhou2024sdwpfdata]. The distinction we draw is where the physics enters: prior MoE and physics-guided forecasters constrain the prediction output or let prediction loss organize the experts, whereas we constrain the routing decision itself against a declared operating boundary. The gate assignment, not only the forecast, is therefore the audited object, and downstream reserve logic can consume it as a physically traceable signal.

Forecast value is realized through reserve and commitment decisions. Reserve studies show that variable generation changes requirements [@doherty2005reserve; @ela2011operatingreserves], while quantile methods bridge point forecasts to decision risk [@bremnes2004quantile; @zhang2014probabilisticreview]. The diagnostic question here is earlier in the chain: which operating window concentrates reserve exposure, and can the forecast model reveal that window through a physically auditable route assignment? The proposed reserve audit is complementary to probabilistic dispatch and market-clearing models.

# Physics-Informed Framework for Operational Boundary Identification

## Problem setup and notation

The forecasting task is written to separate two decisions that dense models often merge: predicting the future and deciding which local mapping should be active at the anchor time. Let $G=(V,E)$ denote a spatial graph with $N=|V|$ nodes. For each node $i \in V$ and time step $t$, we observe a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predict a scalar target $y_{i,t} \in \mathbb{R}$. Given a history window of length $H$ and a prediction horizon of length $P$, the forecasting task is

$$
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
$$

where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes either a time-varying directed graph sequence (WTB) or a static graph repeated over time (ERA5). Invalid or missing targets are excluded by a supervision mask.

The information boundary is strict. All inputs, graph weights, regime anchors, and gate anchors are observed no later than the forecast issue time $t$; supervised targets begin at $t+1$. In WTB, the current active-power channel $\texttt{Patv}_{i,t}$ is treated as an issue-time status input, whereas future active power is used only as the prediction target and validity mask. This keeps the multi-step horizon free of target leakage while leaving the no-\texttt{Patv} and lagged-\texttt{Patv} variants as deployment limitations.

Routing is node-level: each node at each anchor time receives its own gate distribution $\mathbf{g}_{i,t}$. This matters because nearby turbines or grid cells can occupy different local regimes within the same sequence. Core notation is listed before the Introduction; auxiliary loss definitions are provided in Appendix A.

## Operating-boundary anchors and labels

The gate is not supervised everywhere. It is anchored where the physical interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularization. This engineering layer defines what counts as a control regime and when that regime is observable from the data.

### WTB operating regimes

In WTB, the primary operating boundary is the transition from MPPT to pitch control. Let

$$
\bar{p}_{i,t} = \frac{1}{3}\left(p^{(1)}_{i,t}+p^{(2)}_{i,t}+p^{(3)}_{i,t}\right).
$$

The WTB column name `Pab` denotes blade pitch angle. We use $\bar{p}_{i,t}$, also reported as `Pab_mean` in tables and figures, for the three-blade pitch average. The regime labels use wind speed and mean pitch angle at the anchor time, not future active power.

Using a cut-in threshold $u_{\mathrm{idle}}$, a pitch-transition threshold $u_{\mathrm{rated}}$, and a pitch-angle threshold $p_{\mathrm{th}}$, and writing $w_{i,t}=\texttt{Wspd}_{i,t}$ for compactness, we define

$$
R^{\mathrm{wtb}}_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transition)}.
\end{cases}
$$

Only the first three classes are used in direct alignment. Transition samples are retained for analysis but masked out of label supervision through

$$
M^{\mathrm{wtb}}_{i,t} = \mathbf{1}[R^{\mathrm{wtb}}_{i,t} \neq 3].
$$

The reported implementation uses $u_{\mathrm{idle}}=3.0$ m s$^{-1}$, $u_{\mathrm{rated}}=10.5$ m s$^{-1}$, and $p_{\mathrm{th}}=2.0^\circ$ (Appendix A). These thresholds are operating anchors rather than universal turbine constants.

### ERA5 observability contrast (see Supplementary Material)

ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the WTB control-boundary accountability task.

## Shared architecture

### Physical graph construction

The graph is part of the physical problem specification. WTB uses a directed wake graph: candidate turbine pairs are filtered by proximity, activated when an upstream turbine lies inside a wind-aligned downstream cone, weighted by streamwise and cross-stream decay, and pruned to the strongest inbound neighbors. The same directed weights define a wake score, which supplies the WTB wake auxiliary label on MPPT and pitch-control samples. ERA5 uses a symmetric Haversine-Gaussian $k_{\mathrm{nn}}$ graph because the thermodynamic regime marker is already visible in the observed state. Appendix A gives the graph equations and constants.

### Directed-diffusion GRU encoder and node-level gate

The encoder is kept modest so that changes in performance can be traced to routing and regularization. Each input window is concatenated with its feature-missingness mask before projection. Two directed diffusion blocks then aggregate self, inbound, and outbound messages on each graph snapshot. Let $\mathbf{X}^{(\ell)}_{t}$ denote the node state at layer $\ell$ and time $t$. A diffusion block updates each node by

$$
\mathbf{X}^{(\ell+1)}_{t}
=
\mathrm{LN}\!\left(
\mathbf{W}_{\mathrm{self}}^{(\ell)}\mathbf{X}^{(\ell)}_{t}
+
\mathbf{W}_{\mathrm{in}}^{(\ell)}\mathrm{Agg}_{\mathrm{in}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t)
+
\mathbf{W}_{\mathrm{out}}^{(\ell)}\mathrm{Agg}_{\mathrm{out}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t)
+
\mathbf{R}^{(\ell)}\mathbf{X}^{(\ell)}_{t}
\right),
$$

where $\mathrm{Agg}_{\mathrm{in}}$ and $\mathrm{Agg}_{\mathrm{out}}$ are weighted sums over inbound and outbound neighbors. The spatially updated sequence is then processed by a GRU to produce a node-wise context vector $\mathbf{h}_{i,t}$.

Each expert head $f_e$ maps $\mathbf{h}_{i,t}$ to a $P$-step forecast. Routing remains dense during the forward pass. Every expert contributes, but its contribution is weighted by the soft gate distribution. The gate receives both the learned context and a small physics anchor,

$$
\mathbf{z}_{i,t}
=
\mathrm{MLP}_{\mathrm{gate}}\!\left(
\left[\mathbf{h}_{i,t};\mathbf{a}_{i,t}\right]
\right),
\qquad
\mathbf{g}_{i,t} = \mathrm{softmax}\!\left(\frac{\mathbf{z}_{i,t}}{\tau}\right),
$$

and the forecast is

$$
\hat{\mathbf{y}}_{i,t+1:t+P}
=
\sum_{e=1}^{E} g_{i,t}^{(e)} f_e(\mathbf{h}_{i,t}).
$$

WTB uses the anchor

$$
\mathbf{a}_{i,t}^{\mathrm{WTB}}
=
[\texttt{Wspd}_{i,t}, \texttt{Pab\_mean}_{i,t}, s^{\mathrm{wake}}_{i,t}, \texttt{Patv}_{i,t}],
$$

whereas ERA5 uses

$$
\mathbf{a}_{i,t}^{\mathrm{ERA5}}
=
[\texttt{sshf}_{i,t}, \texttt{t2m}_{i,t}, \texttt{wind\_speed}_{i,t}, \Delta \texttt{sshf}_{i,t}].
$$

The difference reflects the observability contrast: WTB needs help to recover a partly hidden operating boundary, whereas ERA5 already exposes the relevant thermodynamic marker in the state. The active-power anchor is standardized from training-split statistics and is never filled from the prediction horizon.

### Routing stack and evidence boundary

This makes the routing stack an anchor-constrained diagnostic rather than an unsupervised operating-state discovery method. High gate-regime agreement means that the implemented router obeys the declared SCADA boundary under the available anchor set; it does not establish anchor-free regime recovery.

![Physics-aligned regime-aware MoE. The two datasets share the same directed-diffusion GRU encoder and node-level MoE routing mechanism. WTB uses a dynamic wake graph and a boundary-focused forcing term, whereas ERA5 uses a Haversine-Gaussian graph and a thermodynamic regime anchor.](artifacts/final_evidence_package/export/figures/figure1_architecture.pdf){ width=95% }

## Integration of Physical Constraints into Model Optimization

Prediction loss does not uniquely identify the gate when several experts can fit averaged dynamics similarly well [@shazeer2017outrageously; @fedus2022switch]. WTB makes this failure visible: inflow variation, wake disturbance, and pitch control are observed together, so a low-loss router can still ignore the operating boundary. We use routing regularizers for the specific failure modes that matter here. The total objective is

$$
\mathcal{L}
=
\mathcal{L}_{\mathrm{pred}}
+
\lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}}
+
\lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}}
+
\lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}}
+
\lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}}
+
\lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}},
$$

with inactive terms set to zero. Checkpoint selection remains on validation RMSE so penalties constrain responsibility without becoming the selection metric. Exact weights are in Appendix A.

### Load balancing

A balancing term prevents early expert collapse before regime-specific structure has time to emerge. It couples hard top-$K$ usage with soft probability mass over valid node-time samples. Appendix A gives the exact expression; physical ownership is supplied only by the anchored alignment terms below.

### Regime-anchor alignment

The alignment term connects the first $C$ gate logits to the declared regime structure so that cross-seed statements such as "MPPT-aligned" refer to a fixed mapping rather than to post-hoc relabeling. With $\mathbf{z}^{(1:C)}_{i,t}$ denoting the anchored logits, $R_{i,t}$ the label, and $M_{i,t}$ the validity mask,
$$
\begin{aligned}
\mathcal{L}_{\mathrm{align}}
&= \frac{1}{|\Omega|}
\sum_{(i,t)\in\Omega}
\mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right),\\
\Omega&=\{(i,t):M_{i,t}=1\}.
\end{aligned}
$$
with inverse-frequency class weights on the training split.

### Boundary-focused forcing (WTB only)

After coarse alignment the boundary remains partly masked by control action. A focused forcing term acts on MPPT and pitch-control samples only. With $Y^{\mathrm{force}}_{i,t}=\mathbf{1}[R^{\mathrm{wtb}}_{i,t}=2]$ for $R^{\mathrm{wtb}}_{i,t}\in\{1,2\}$,
$$\mathcal{L}_{\mathrm{force}} = \frac{1}{|\Omega_{\mathrm{force}}|}\sum_{(i,t)\in\Omega_{\mathrm{force}}}\mathrm{CE}\!\left(\left[z^{(\mathrm{mppt})}_{i,t}, z^{(\mathrm{pitch})}_{i,t}\right]^{\top}, Y^{\mathrm{force}}_{i,t}\right),$$
where $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}, M_{i,t}=1\}$. This term is not a lead-time switch predictor; it is a boundary identifiability regularizer for the issue-time operating state.

### Wake auxiliary supervision and graph smoothness

A wake auxiliary label identifies residual wake ambiguity inside MPPT and pitch-control samples, and a graph-smoothness penalty discourages noisy neighbor-to-neighbor gate jumps. Both formulas are in Appendix A.

## Operational reserve diagnostic protocol

The reserve diagnostic tests whether a physically auditable gate changes the reserve tradeoff in the MPPT-to-pitch window after the point-forecast model has been trained. For each saved WTB run, validation predictions select reserve levels; test predictions are then evaluated once with those levels fixed. The protocol follows the same information boundary as an operator who calibrates a short-term reserve rule before using it on a later period.

Let $\hat{y}_{i,t}$ be the scheduled point forecast and $y_{i,t}$ the realized active power at an evaluated horizon cell. We define over-forecast shortfall as

$$
s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0),
$$

because this is the error direction that leaves a reserve schedule exposed. For a reserve policy $b$ and empirical quantile $q$, the validation split estimates a reserve level

$$
r_{b,q} = Q_q\!\left(\{s_{i,t}: (i,t)\in b,\ (i,t)\in \mathcal{V}\}\right),
$$

where $Q_q$ is an empirical quantile and $\mathcal{V}$ is the validation split. The grid is fixed before test evaluation:

$$
q \in \{0.50,0.60,0.70,0.80,0.85,0.90,0.95,0.975,0.99\}.
$$

The reserve bin $b$ is either the whole sample, a physical operating bin, or a gate-derived bin. For each shortage-to-reserve cost ratio $\rho$, the protocol selects the validation quantile that minimizes

$$
C_{\mathcal{V}}(b,q;\rho)
=
\sum_{(i,t)\in b\cap \mathcal{V}}
\left[
r_{b,q} + \rho \max(s_{i,t}-r_{b,q},0)
\right]\Delta t.
$$

The selected $(b,q)$ rule is then frozen and applied to the test split. The reported test metrics are total cost $C$, violation rate $\Pr[s_{i,t}>r_b]$, reserve energy $\sum r_b\Delta t$, and shortage energy $\sum \max(s_{i,t}-r_b,0)\Delta t$. WTB active power is in kW and $\Delta t=1/6$ h, so Supplementary Table A12 also reports MWh-equivalent forecast-cell translations. These are not delivered market energy or settlement costs: a value written as 84.58M denotes 84.58 million reserve-cost-equivalent kWh cells, not currency.

The cost ratio $\rho$ is an energy-system assumption rather than an abstract tuning knob. If the marginal cost of carrying one unit of reserve energy is $C_r$, then $\rho=10$ charges one unit of residual shortage as $10C_r$. Ratios 5--10 represent moderate reliability settings such as transition-window scheduling or imbalance screening; ratios 20--50 represent scarcity-aware screening where shortage avoidance dominates local cost savings. The primary diagnostic compares Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin policies. Only same-model global comparisons attribute gate-bin reserve effects to the learned router.

To bound this diagnostic against a probabilistic reserve alternative, we additionally run validation-frozen empirical quantile baselines for the global and physical operating bins. These are not trained distributional forecasters; they are conformal-style shortfall reserves estimated on the validation split and evaluated once on the test split. The main reported boundary window is fixed at $\pm 1.0$ m s$^{-1}$ around rated wind and the main cost ratio is $\rho=10$, with sensitivity at $\rho \in \{2,5,10,20,50\}$. A separate toy operational-cost module reports reserve procurement plus $\rho$-weighted residual-shortage penalty and excludes optimal power flow, unit commitment, market clearing, delivery constraints, and price claims.

```{=latex}
\begingroup
\footnotesize
\setlength{\fboxsep}{5pt}
\noindent\fbox{\begin{minipage}{0.96\linewidth}
\textbf{Reserve diagnostic algorithm.}
Input saved validation/test point forecasts, targets, masks, physical anchors, and gate outputs.
Compute over-forecast shortfall on valid cells.
Form global, physical-bin, and gate-bin reserve groups on validation outputs only.
For each cost ratio and group, select the empirical shortfall quantile that minimizes validation reserve-plus-shortage cost.
Freeze the selected reserve levels and evaluate them once on test cells.
Aggregate cost, violation rate, reserve energy, and shortage energy over full, boundary, transition, ramp, horizon-bucket, and time-of-day slices.
Report horizon-specific empirical-quantile rows only as a post-hoc what-if.
Compare validation-frozen global and physical-bin quantile reserves as bounded probabilistic baselines.
Report toy operating cost only as reserve procurement plus shortage penalty, not as dispatch.
\end{minipage}}
\par
\endgroup
```

# Case Study Configuration and Operational Constraints

## Datasets and preprocessing

The experiment uses two observability settings, not two interchangeable benchmarks. WTB is the control-confounded case. The KDD Cup 2022 benchmark contains 134 turbines and 245 days of 10 min SCADA measurements [@zhou2024sdwpfdata]. The MPPT-to-pitch transition is only indirectly visible because inflow variation, wake disturbance, and blade-pitch control are mixed in the same stream.

The data are reorganized into synchronous tensors with $T=35{,}280$ time steps, $N=134$ turbines, and $F=11$ dynamic inputs. Missing inputs are forward-filled within turbine and then completed with training-set means. Invalid or non-positive active power is retained only through its mask so that the model still sees operational irregularity without treating those points as supervised targets.

ERA5 is the signal-expressive case. We use three archived months over a fixed $16 \times 16$ hourly patch [@hersbach2020era5]. Sensible heat flux and its temporal variation make the stable-to-convective transition directly observable. The retained tensor has $T=2208$ frames, $N=256$ nodes, and eight input variables. Both datasets use the same history and horizon lengths, $H=36$ and $P=24$, so differences in performance cannot be attributed to unequal context length. The chronological split is 180/30/35 days for WTB and 1325/441/442 frames for ERA5.

## Techno-Economic Validation and Benchmarking Framework

The comparison has two layers. The first isolates the routing mechanism after shared-capacity explanations have been controlled. The dense baseline uses the same directed-diffusion GRU encoder and replaces the expert mixture with one dense prediction head. The unconstrained MoE adds routed capacity without physical correction. The corrected-routing comparator is dataset-specific: ERA5 uses the full corrected stack, while WTB uses the boundary-focused variant selected for gate recovery. Parameter budgets are matched in WTB and near-matched in ERA5, where the dense model has 103,272 parameters and the routed models have 103,843 parameters.

The second layer tests the RMSE price against stronger and more engineering-facing baselines. Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE are included for WTB [@nie2023patchtst; @liu2024itransformer; @das2023longterm], together with deterministic persistence, a fitted physical power-curve baseline, XGBoost and LightGBM lag-feature predictors, and a DLinear-style LTSF baseline. Graph WaveNet, STGCN, PatchTST, TCN, and a deterministic persistence predictor are included for ERA5. This split avoids using one comparison for two different claims. The in-family layer tests whether physical routing changes the learned partition under a fixed backbone. The baseline layer tests whether the routing intervention remains honest about forecast error when compared with established temporal, graph, and engineering predictors.

For compactness, the mechanism tables shorten the three in-family model names to **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**. The main WTB forecasting table reports representative strong baselines, including the best strict-cache baseline used for the RMSE price; Supplementary Table A13 gives the expanded strict-cache set with Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, TiDE, the full physics-aligned MoE, and the WTB boundary-forced router. Engineering baselines built from persistence, power curves, gradient-boosted lag features, and a DLinear-style LTSF readout are retained in the source tables. The ERA5 forecasting tables additionally report persistence and four learned external baselines. The in-family mechanism families are summarized in Appendix A so that the Results section can focus on evidence rather than model bookkeeping.

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in the Appendix so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE across seeds 201--205, giving 30 completed baseline runs under the same strict anchor-valid evaluation cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same frozen cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE use the evaluator's transition-window mask around regime changes. This is distinct from the later boundary-band audit, which isolates anchors within +/-1.0 m s$^{-1}$ of the WTB rated-wind MPPT-to-pitch boundary. Regime-wise RMSE locates the error reduction. Normalized mutual information (NMI), adjusted Rand index (ARI), usage entropy, and confusion matrices test whether the gate corresponds to physically interpretable structure.

Figure 2 gives the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=97% }

# Evidence and Operational Boundary Diagnosis

The results follow the operating decision that motivates the paper: can a route replace a degraded threshold stream in the MPPT-to-pitch window, and what accuracy trade-off does that issue-time signal carry? We first test boundary recovery and falsification checks, then quantify early pitch-window recall under delayed, missing, and noisy labels. We then ask whether the audited gate changes a validation-frozen reserve rule, and finally state the deployment gates for new wind farms.

## Can the Gate Recover the Operating Boundary?

SCADA-anchored routing recovers the WTB MPPT-to-pitch partition strongly enough to make the gate an auditable operating-boundary signal. Across five WTB seeds, the boundary-forced router reaches NMI about 0.87 and ARI about 0.92 against the declared labels. The accuracy reference remains explicit: iTransformer reaches overall RMSE 224.34 +/- 2.23, Graph WaveNet reaches 225.74 +/- 2.60, and the boundary-forced router reaches 236.13 +/- 8.41. The intended operating point is therefore not leaderboard replacement, but an additional issue-time state signal for the transition window.

The boundary itself is a meaningful diagnostic target. Anchors within +/-1.0 m s$^{-1}$ of rated wind have RMSE 321.17 +/- 21.31, roughly 67 units above valid non-boundary MPPT/pitch anchors. The same boundary band has mixed-regime structure (NMI/ARI 0.6562/0.7766), so it is both a forecasting stress point and a natural reserve-risk window. ERA5 provides the positive observability contrast: when the regime marker is directly visible through sensible heat flux, routing correction improves alignment without changing the headline accuracy story.

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{Operating-boundary recovery and mechanism checks.}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.30\linewidth} >{\raggedright\arraybackslash}p{0.34\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Check & Metric & Result \\
\midrule
WTB boundary-forced router & Gate-regime NMI / ARI & 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 \\
WTB boundary-band audit & Boundary-band RMSE; mixed-regime NMI / ARI & 321.17 +/- 21.31; 0.6562 / 0.7766 \\
Boundary-anchor intervention & Overall RMSE change; NMI / ARI drop & +2.6792; 0.7017 / 0.8593 \\
WTB spatial and time holdouts & Held-out-node NMI / ARI; future-holdout NMI / ARI & 0.8340 / 0.8829; 0.8352 / 0.8870 \\
La Haute Borne positive-control replay & NMI / ARI; Patv-zero NMI; wind+pitch-zero NMI & 0.9408 +/- 0.0336 / 0.9712 +/- 0.0201; 0.953; 0.001 \\
Threshold-grid audit & Worst-case saved-gate NMI / ARI & 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377 \\
\bottomrule
\end{tabularx}
\end{table}
```

The diagnostic survives the main falsification checks. Zeroing the intended boundary anchor sharply reduces gate-regime agreement, whereas zeroing the wake score is near-null. Placebo labels do not reproduce the actual-label agreement. The spatial and future-period holdouts are the within-WTB generalization evidence for the routing claim, and they directly address whether a single benchmark can support it: the gate recovers the declared boundary at NMI 0.834 on turbines withheld from training and 0.835 on a held-out future period, so the recovered semantics transfer to unseen nodes and unseen time rather than fitting the specific turbines or window used for training, and threshold sweeps preserve the same routing structure. The recovery is not specific to WTB: retrained from scratch on an independent farm--the ENGIE La Haute Borne open SCADA benchmark, a different operator and country with directly observed blade pitch (99.2\% of cells, no proxy)--the same boundary-forced routing reaches five-seed chronological NMI 0.941 and ARI 0.971, clearing the 0.50 held-out routing criterion and slightly exceeding the WTB recovery. A replay audit makes the second-site role explicit: zeroing active power leaves the La Haute Borne NMI at 0.953, whereas jointly zeroing wind speed and pitch collapses it to 0.001 (Supplementary Table A9). Thus La Haute Borne is cited as an anchor-observable positive-control replication, not as anchor-free discovery. Within-WTB generalization and this second-farm recovery are the routing claim; the Kelmarsh/Penmanshiel farms, where pitch observability and boundary-cell coverage are insufficient, are reported separately as the deployment-gate failure that defines the conditions cross-site recovery requires rather than folded into the routing claim.

The central operating result is that the gate keeps the early pitch-control warning alive when the threshold label stream degrades. We audit saved five-seed gates around MPPT-to-pitch transitions after delaying threshold labels, dropping label availability, and recomputing labels under sensor noise. Table~\ref{tab:early-warning} reports recall on early pitch-control cells, and Supplementary Table A10 converts the audit into detected and missed turbine-time cells. With a six-step delay, the threshold rule recalls only 0.196 of early pitch cells, whereas the gate recalls 0.960 and recovers about 566 early pitch-window cells per seed. With 50% label availability, the rule recalls 0.508 while the gate remains at 0.960. Under the strongest sensor-noise setting, the threshold rule drops to 0.652 recall and the saved gate is unchanged. This is the operational meaning of auditability: the gate preserves a transition-window diagnostic when the label stream is delayed, incomplete, or noisy.

We anticipate the natural objection that this comparison is unfair because it degrades the threshold label while leaving the gate input intact, and we control for it directly. That asymmetry is the operating point rather than an artifact of it: a confirmed threshold label requires the wind-speed and pitch crossing to be observed, validated, and recorded, so it is exactly what arrives late, drops out, or is corrupted under sensor faults; the gate instead consumes the live SCADA anchor channels that are present at issue time whenever the turbine is instrumented. The operational question is therefore not whether two identical inputs are scored differently, but whether an issue-time route can stand in for a degraded confirmation stream--the substitution an operator actually faces. To show that the gate is not merely exploiting clean anchors, we separately degrade the anchor channels themselves: removing \texttt{Patv} or \texttt{Pab\_mean}, and lagging \texttt{Patv} or both pitch and wind speed, keeps the five-seed routing means above the 0.65 NMI threshold (Table~\ref{tab:anchor-stress}), so the diagnostic degrades gracefully under anchor corruption rather than collapsing. The early-warning advantage thus reflects an availability gap that survives realistic anchor noise, not an unmatched-information comparison.

We report the operating trade-off explicitly. A model receives citable degraded-label gain only after its route passes the physical-routing audit; otherwise the accountability gain is set to zero, even for an accurate or routed-capacity model. Under this rule iTransformer is the zero-RMSE-price anchor without an audited operating-state route, Unconstrained MoE fails the route audit (NMI 0.014), and the boundary-forced router is the only current point that exchanges an 11.79-RMSE trade-off for +0.764 six-step-delay recall gain (Fig.~\ref{fig:accountability-tradeoff}).

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{1.05}
\caption{Label-degradation audit for early MPPT-to-pitch pitch-window detection.}
\label{tab:early-warning}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} >{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.13\linewidth} >{\centering\arraybackslash}p{0.13\linewidth} >{\centering\arraybackslash}X}
\toprule
Scenario & Setting & Gate & Rule & Gain \\
\midrule
Delay & 1 step & 0.960 & 0.655 & +0.305 \\
Delay & 3 steps & 0.960 & 0.381 & +0.579 \\
Delay & 6 steps & 0.960 & 0.196 & +0.764 \\
Availability & 75\% labels & 0.960 & 0.744 & +0.216 \\
Availability & 50\% labels & 0.960 & 0.508 & +0.452 \\
Availability & 25\% labels & 0.960 & 0.242 & +0.718 \\
Noise & Wspd 0.5, Pab 1.0 & 0.960 & 0.808 & +0.152 \\
Noise & Wspd 1.0, Pab 2.0 & 0.960 & 0.652 & +0.308 \\
\bottomrule
\end{tabularx}
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{Anchor-observability stress: 245d WTB test routing recovery.}
\label{tab:anchor-stress}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.32\linewidth} >{\centering\arraybackslash}p{0.18\linewidth} >{\centering\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Variant & Mean NMI & Mean ARI & Reading \\
\midrule
Remove \texttt{Patv} & 0.881 & 0.912 & single-channel removal passes \\
Remove \texttt{Pab\_mean} & 0.878 & 0.928 & single-channel removal passes \\
Lag \texttt{Patv} & 0.763 & 0.769 & delayed active power passes \\
Lag pitch/wind & 0.684 & 0.720 & degraded but above 0.65 NMI \\
\bottomrule
\end{tabularx}
\end{table}
```

The training-level anchor-stress guard has been completed across five seeds. Four strict-cache variants were derived from the 245-day WTB training set, trained across seeds 201--205, and evaluated against the declared MPPT-to-pitch labels; the cache-level leakage guard passed with all 20 training runs completed, so the derived variants raise no leakage warning. The table reports the test-set NMI/ARI scores. Removing \texttt{Patv} or \texttt{Pab\_mean} individually leaves the gate essentially intact (mean 0.881 and 0.878, respectively). Lagging \texttt{Patv} lowers one seed but the five-seed mean remains above the 0.65 threshold (0.763). Lagging both \texttt{Pab\_mean} and \texttt{Wspd} also lowers one seed, yet the five-seed mean crosses the threshold (0.684). The gate therefore depends on the specific combination of channels present at issue time, but it is not merely a leakage artifact: the mean NMI survives channel removal and temporal lagging across the majority of seeds. The manuscript uses the wording "partial anchor robustness" rather than "anchor-free physical discovery." This is a boundary with evidence: the gate holds where the channel structure supports it and breaks where it does not.

![The WTB operating plane shows the main mechanism: after correction, the dominant routed responsibility changes around the rated-wind and pitch-control boundary instead of forming an arbitrary expert partition. The confusion matrices summarize the same recovery numerically.](artifacts/final_evidence_package/export/figures/figure4_routing_evidence.pdf){ width=97% }

![The time-series case studies show why observability matters. The WTB gate tracks a turbine-control switch that is partly hidden inside SCADA control action, whereas the ERA5 gate follows a more directly observed thermodynamic marker.](artifacts/final_evidence_package/export/figures/figure5_case_studies.pdf){ width=97% }

## Boundary-Risk Vignette: Does the Gate Change Reserve Tradeoffs?

The reserve audit is a consequence check for the recovered route, not a standalone dispatch optimizer. A validation-calibrated short-term reserve screener is applied to later turbine-time cells near the MPPT-to-pitch boundary. A global rule treats all boundary cells as one pool; a gate-conditioned rule carries a different reserve level when the audited route indicates pitch-control entry. Four policies separate the effects: Graph WaveNet/global (low-RMSE reference), Graph WaveNet/physical-bin (physical stratification without learned gate), Boundary router/global (routed model with single reserve rule), and Boundary router/gate-bin (gate-conditioned allocation on the same routed predictor).

At shortage-to-reserve cost ratio 10, gate-conditioned binning exchanges about 3.6% additional reserve energy for a 14.5% reduction in shortage energy and a 1.38 percentage-point reduction in boundary-window violation relative to the same routed model with a global rule. The comparison is deliberately same-model: the reserve change is attributed to gate-conditioned allocation, not to a different forecasting backbone. Physical-bin quantile baselines remain competitive and can be lower-cost, so the defensible claim is attributional: the gate exposes a transition-window reserve-risk mechanism and improves a same-model global reserve rule at moderate cost ratios. Supplementary Tables A11--A12 record the wording boundary and engineering-unit translation.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.08}
\caption{Boundary-window reserve outcomes and validation-frozen quantile baselines at cost ratio 10.}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.12\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Policy & Cost & Viol. & Reserve & Shortage & Reading \\
\midrule
Boundary/physical-bin & 83.78M & 0.0880 & 53.26M & 3.05M & Best same-router physical-bin reference \\
GWN/physical-bin & 84.31M & 0.0931 & 50.35M & 3.40M & Low-RMSE backbone reference \\
Boundary/gate-bin & 84.58M & 0.0900 & 52.67M & 3.19M & Gate diagnostic; same-model better than global \\
Boundary/global & 88.13M & 0.1038 & 50.82M & 3.73M & Same-model global rule \\
GWN/global & 88.80M & 0.1022 & 50.32M & 3.85M & Global low-RMSE reference \\
\bottomrule
\end{tabularx}
\end{table}
```

The useful reserve window is moderate rather than universal. At low shortage penalty, the validation-selected quantile tolerates too much residual shortage for gate-bin allocation to matter; at ratios 5--10, the gate lowers boundary shortage and violation while carrying more reserve; at ratio 50, the same-model global rule is safer and cheaper. The toy operational-cost proxy is intentionally small: reserve procurement cost plus $\rho$ times residual shortage energy. On the boundary slice the gate-bin rule reduces the same-model global proxy from 88.13M to 84.58M; Supplementary Table A12 translates this into about 540 avoided MWh-equivalent shortage cells and -355k EUR at an illustrative 100 EUR/MWh carrying cost. Graph WaveNet/physical-bin remains close at 84.31M, and on the full sample Graph WaveNet/global is lower-cost, so the paper does not claim system-wide dispatch value. Cost-ratio sensitivity, paired full-sample uncertainty, and operational-slice tables are kept as supplementary evidence.

![Accountability value versus forecasting RMSE price. Citable degraded-label gain is assigned only after the physical-routing audit passes. \label{fig:accountability-tradeoff}](artifacts/final_evidence_package/export/figures/accountability_tradeoff_curve.pdf){ width=90% }

![The decision curve places the reserve benefit beside the measured RMSE price. Gate-conditioned allocation is attractive only where the transition-window shortage reduction is worth the added reserve energy.](artifacts/final_evidence_package/export/figures/operational_decision_curve.png){ width=92% }

## What Are the Costs and Deployment Gates?

The accuracy cost is real and should be read as part of the design. iTransformer, Graph WaveNet, and lag-feature baselines remain better whole-sample forecasters on WTB. The routed model is used when an operator or analyst needs an accountable operating-state assignment that can feed a boundary-specific decision, not when the sole target is minimum average error. Time-forward testing gives the same message in another form: late-period routing agreement remains high, but late-test RMSE rises sharply, showing that stable semantics do not guarantee stable value prediction under distribution shift.

The external evidence has two sides. Where the control boundary is observed, the mechanism transfers as an anchor-observable positive control: retrained on the independent ENGIE La Haute Borne farm, the boundary-forced router recovers the declared partition at five-seed NMI 0.941 and ARI 0.971, well clear of the 0.50 held-out criterion, and the replay audit rules out active-power feedback while confirming wind-speed/pitch anchors as the load-bearing boundary evidence (Supplementary Tables A8--A9). Where pitch observability or boundary coverage is missing, it does not: the Kelmarsh/Penmanshiel checks do not authorize direct gate-bin reserve use because they fail the same criterion. Together they make transfer a testable condition rather than an assumption: before a new farm uses the route, it must verify pitch or proxy observability, boundary-cell support, compatible turbine geometry, local threshold estimation, and a held-out routing pass--the checks La Haute Borne passes and the Kelmarsh/Penmanshiel pair fails. The method exports an evidence protocol, not a promise of automatic transfer.

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{External-site deployment gates identified by Kelmarsh/Penmanshiel testing.}
\begin{tabularx}{0.98\linewidth}{>{\raggedright\arraybackslash}p{0.28\linewidth} >{\raggedright\arraybackslash}p{0.38\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Gate & Observed evidence & Required decision before reserve use \\
\midrule
Held-out routing criterion & Default WTB boundary gives mean external NMI 0.4877, below the 0.50 criterion & Re-establish routing agreement locally \\
Local boundary recalibration & Average test NMI changes from 0.1324 to 0.1491 after validation-only recalibration & Treat threshold transfer as insufficient \\
Pitch/proxy observability & One transfer direction has no effective pitch-feature coverage or boundary cells & Require pitch channels or a validated proxy \\
Calibration-window adaptation & Small-window adaptation remains below the held-out balanced-accuracy threshold & Use calibration only after a held-out pass \\
Geometry and regime support & Farm scale, sensor fields, power curves, and regime shares differ across sites & Run a local evidence protocol before gate-bin reserve allocation \\
\bottomrule
\end{tabularx}
\end{table}
```

The WTB internal proxy drill shows the minimum evidence sequence: verify sensor coverage, re-estimate local boundary and gate-to-regime map, pass held-out routing, then run the reserve diagnostic. Stronger gate repair is justified only when the reserve-window benefit exceeds the measured RMSE and reserve-energy cost.

![The new-site protocol turns external failure into a practical safety check: sensor coverage, local boundary calibration, held-out routing, and reserve audit must all pass before gate-conditioned reserve allocation is used.](artifacts/final_evidence_package/export/figures/new_wind_farm_deployment_checklist.png){ width=94% }

# Limitations

The WTB correction depends on threshold-based pseudo-labels derived from wind speed and mean pitch angle. Those same channels also appear in the gate anchor, so the method deliberately constrains the router to a declared operating boundary. The outcome-channel audit in Supplementary Table A7 mitigates, but does not eliminate, this shared-anchor concern. The La Haute Borne replay audit makes the same boundary visible at the second site: active power is not load-bearing, but the joint wind-speed/pitch anchor is. The label-degradation audit shows value under delayed, missing, or noisy labels, but it should not be read as anchor-free physical discovery or as a general future-label switch predictor. The claim is boundary-aware regularized routing that remains useful when the operational label stream degrades.

The active-power anchor has a strict timing requirement. `Patv` is allowed only as the historical/anchor-time active-power measurement available when the forecast is issued; future active power remains the supervised target. This is a defensible SCADA forecasting convention, but it is also a portability constraint. The five-seed anchor-stress evidence in Table~\ref{tab:anchor-stress} shows that removing `Patv` or `Pab_mean` individually leaves the gate essentially intact, while lagging both channels lowers the mean NMI but still crosses the 0.65 threshold. If a deployment environment delays active-power telemetry or changes channel definitions, the Patv anchor must be removed or lagged and the leakage, intervention, and reserve diagnostics must be rerun.

The expert-regime language is tied to the implemented logit convention. The first primary-regime logits are fixed to the operating labels during supervised alignment, which prevents seed-wise permutation for those anchored meanings. That makes cross-seed MPPT/pitch statements interpretable, but only for the anchored logits and only under the declared mapping. Unassigned experts and wake auxiliary logits should not be overread as universal turbine states.

The comparison is bounded. WTB includes graph, Transformer, MLP-style, lag-feature, persistence, power-curve, DLinear-style references, and validation-frozen empirical quantile reserve baselines, while ERA5 includes persistence and several learned baselines. Broader graph-transformer variants, trained quantile-regression forecasters, scenario reserve, distributional reserve, and security-constrained reserve methods are outside the present benchmark.

The reserve audit is a normalized proxy: fixed empirical quantile bins calibrated on validation shortfall and tested once on held-out predictions. It ranks boundary-window tradeoffs under declared cost ratios, but it is not a market-price or security-constrained dispatch study. Cross-site recovery is demonstrated on one additional anchor-observable farm (La Haute Borne) and is not claimed beyond the conditions it requires; the Kelmarsh/Penmanshiel pair fails the held-out routing criterion and identifies the sensor coverage, pitch observability, local boundary re-estimation, and held-out routing checks that must pass before cross-farm use. The time-forward audit shows that late-period distribution shift preserves routing agreement while degrading value prediction: the method supports routing semantics, not time-stable forecasting accuracy.

Statistical reliability is uneven (Supplementary Table A6). The strongest claims are the five-seed WTB routing-recovery, mechanism-intervention, and within-WTB spatial/temporal stress results; gate-alignment deltas versus the full MoE and boundary-window reserve-cost comparisons remain bounded diagnostics, not superiority claims.

# Conclusion

This paper addresses a practical wind-farm forecasting failure mode: the MPPT-to-pitch label stream can degrade exactly when reserve screening needs an operating-state signal. SCADA-anchored regime-aware routing turns the node-level gate into an auditable control-boundary assignment. The boundary-forced router recovers the declared WTB MPPT-to-pitch partition (NMI about 0.87, ARI about 0.92), keeps 0.960 early pitch-window recall under a six-step label delay while the delayed threshold rule falls to 0.196, and exposes transition-window reserve risk. This operating-state signal has a measured accuracy trade-off: overall RMSE 236.13 versus 224.34 for the best strict-cache forecasting baseline. Validation-frozen quantile baselines, Supplementary Table A6, and Kelmarsh/Penmanshiel deployment gates keep the claim bounded. The contribution is an auditable MPPT-to-pitch routing tool with degraded-label value, RMSE price, and explicit transfer conditions.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only to support language editing, consistency checking, and submission-material drafting. The tools were not used to generate data, run analyses, create references, or determine scientific conclusions. The authors reviewed and edited all content and take full responsibility for the manuscript.

# Code and data availability

The raw datasets are publicly available: KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA records. Raw third-party data are not redistributed. Code, configuration files, releasable derived tables, figure data, and model checkpoints will be made available with the article. The reproduction package includes end-to-end scripts for the WTB routing analysis, reserve audit, anchor-stress cache/train/guard protocol, anchor-stress early-warning label-degradation audit, and external boundary diagnostics. The provenance package lists the anchor-stress cache/train/guard and early-warning protocols as mandatory. The analysis involves no human subjects.

\clearpage

# References {.unnumbered}

::: {#refs}
:::

\clearpage

# Appendix A. Training and implementation details {.unnumbered}

## Training loop summary {.unnumbered}

```text
Algorithm A1  Physics-aligned MoE training
Input: history windows X, graph sequence A, targets Y, primary regime anchors R,
       auxiliary wake labels W (WTB only), model parameters theta
for each minibatch do
    Build node-level graph context from the precomputed graph tensors
    Encode X with the directed-diffusion GRU to obtain node context H
    Compute gate logits Z and soft routing probabilities G
    Compute expert forecasts and aggregate them with G
    Evaluate L_pred
    If MoE mode is active:
        add L_bal on top-K routing statistics
        add L_align on valid primary regime anchors
        if WTB: add L_force on MPPT/pitch samples
        if WTB: add L_aux on wake labels
        add L_smooth on the final graph snapshot
    Update theta with AdamW and mixed precision
end for
Select the checkpoint with the best validation RMSE
```

## Model-family and supplementary evidence index {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\small
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.1}
\caption*{\textbf{Table A1.} In-family model comparison used for mechanism validation.}
\begin{tabularx}{0.98\textwidth}{>{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.20\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth}}
\toprule
Model & Routing & Extra terms & Params & Role \\
\midrule
Dense (matched) & Single dense head & None & WTB 110,012 / ERA5 103,272 & Shared-mapping reference \\
Unconstrained MoE & Node-level soft gate & Prediction loss only & WTB 110,012 / ERA5 103,843 & Routed-capacity control \\
Corrected routing comparator & Node-level soft gate & WTB boundary-forced: $L_{bal}+L_{align}+L_{force}$; ERA5: full corrected stack & WTB 110,012 / ERA5 103,843 & Accountability comparator \\
\bottomrule
\end{tabularx}
\end{table}
```

## Auxiliary losses {.unnumbered}

Let $\mathcal{B}$ denote the routed samples after masks, with $B=|\mathcal{B}|$. The soft importance and normalized share of expert $e$ are $I_e = \frac{1}{B}\sum_{n=1}^{B} g_n^{(e)}$ and $P_e = I_e / \sum_{r} I_r$. The top-$K$ load is $f_e = \frac{1}{B}\sum_{n=1}^{B}\mathbf{1}[e \in \mathrm{TopK}(\mathbf{g}_n)]$, giving
$$\mathcal{L}_{\mathrm{bal}} = E\sum_{e=1}^{E} f_e P_e - 1.$$
For WTB wake supervision,
$$\mathcal{L}_{\mathrm{aux}} = \frac{1}{|\Omega_{\mathrm{wake}}|}\sum_{(i,t)\in\Omega_{\mathrm{wake}}}\mathrm{BCE}(z^{(\mathrm{wake})}_{i,t}, W_{i,t}),$$
where $\Omega_{\mathrm{wake}}$ contains only MPPT and pitch-control samples with defined wake flags. The graph-smoothness penalty is
$$\mathcal{L}_{\mathrm{smooth}} = \frac{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)\lVert\mathbf{g}_{i,t}-\mathbf{g}_{j,t}\rVert_2^2}{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)+\epsilon}.$$

## Graph construction details {.unnumbered}

For WTB, the downstream unit vector is $\mathbf{u}_{i,t}=[\sin(\theta_{i,t}+\pi), \cos(\theta_{i,t}+\pi)]^{\top}$. With $\Delta\mathbf{p}_{ij}=\mathbf{p}_j-\mathbf{p}_i$, the streamwise and cross-stream distances are $d^{\parallel}_{ij,t}=\Delta\mathbf{p}_{ij}^{\top}\mathbf{u}_{i,t}$ and $d^{\perp}_{ij,t}=|\Delta p^x_{ij}u^y_{i,t}-\Delta p^y_{ij}u^x_{i,t}|$. A candidate edge activates when
$$\mathbb{I}^{\mathrm{cone}}_{ij,t}=\mathbf{1}\!\left[d^{\parallel}_{ij,t}>0\;\land\;\arctan\!\left(\frac{d^{\perp}_{ij,t}}{\max(d^{\parallel}_{ij,t},10^{-6})}\right)\le\phi\right].$$
The wake weight is $\tilde{\mathcal{A}}_t(i,j)=\exp(-d^{\parallel}_{ij,t}/\alpha)\exp(-|d^{\perp}_{ij,t}|/\beta)\mathbb{I}^{\mathrm{cone}}_{ij,t}$. If wind direction is missing, fall back to $\mathcal{A}^{\mathrm{static}}(i,j)=\exp(-\lVert\Delta\mathbf{p}_{ij}\rVert_2/d_{\max})$. Only the strongest $M$ inbound weights are retained. The wake score and flag are $s^{\mathrm{wake}}_{i,t}=\sum_{j}\mathcal{A}_t(i,j)$ and
$$W_{i,t}=\begin{cases}1,&s^{\mathrm{wake}}_{i,t}\ge q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\0,&s^{\mathrm{wake}}_{i,t}<q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\\varnothing,&\text{otherwise.}\end{cases}$$

For ERA5, the retained symmetric graph uses a Gaussian kernel on great-circle distances:
$$\mathcal{A}(i,j)=\exp\!\left(-\frac{d_{ij}^2}{2\sigma^2}\right)\mathbf{1}[j\in\mathcal{N}_{k_{\mathrm{nn}}}(i)\;\text{or}\;i\in\mathcal{N}_{k_{\mathrm{nn}}}(j)],$$
where $\sigma$ is the median retained neighbor distance on the training graph.

## Shared constants {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A3.} Shared architecture, graph, and training constants used in the reported experiments.}
\begin{tabularx}{0.98\textwidth}{>{\raggedright\arraybackslash}p{0.30\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}X}
\toprule
Item & WTB & ERA5 & Role \\
\midrule
History / horizon $(H,P)$ & $(36,24)$ & $(36,24)$ & Input and forecast lengths \\
Gate softmax temperature $\tau$ & 0.7 & 0.7 & Soft routing sharpness \\
Top-$K$ in $L_{\mathrm{bal}}$ & 1 & 1 & Balancing statistic only \\
Hidden size $d$ & 64 & 64 & Shared encoder width \\
$k_{\mathrm{nn}}$ candidates & 8 & 8 & Initial neighborhood size \\
Maximum candidate radius $d_{\max}$ & 1500 m & not used & WTB proximity fallback / candidate filter \\
Wake-cone half-angle $\phi$ & $25^\circ$ & not used & WTB downstream activation \\
Streamwise decay $\alpha$ & 1200 m & not used & WTB wake attenuation \\
Cross-stream decay $\beta$ & 400 m & not used & WTB wake attenuation \\
Retained inbound edges $M$ & 5 & symmetric $k_{\mathrm{nn}}$ graph & Final graph sparsity \\
Optimizer & AdamW & AdamW & Shared optimizer \\
Learning rate & $2 \times 10^{-3}$ & $2 \times 10^{-3}$ & Shared schedule \\
Weight decay & $10^{-4}$ & $10^{-4}$ & Shared regularization \\
Batch size & 16 & 16 & Shared mini-batch size \\
Gradient clipping & 1.0 & 1.0 & Shared training stabilization \\
\bottomrule
\end{tabularx}
\end{table}
```

## Dataset-specific thresholds and routing weights {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A4.} Dataset-specific regime thresholds used to construct routing anchors.}
\begin{tabularx}{0.98\textwidth}{>{\raggedright\arraybackslash}p{0.28\textwidth} >{\raggedright\arraybackslash}p{0.24\textwidth} >{\raggedright\arraybackslash}X}
\toprule
Dataset & Threshold & Value and meaning \\
\midrule
WTB & $u_{\mathrm{idle}}$ & 3.0 m s$^{-1}$, idle / active split \\
WTB & $u_{\mathrm{rated}}$ & 10.5 m s$^{-1}$, MPPT / pitch boundary \\
WTB & $p_{\mathrm{th}}$ & 2.0 deg, pitch-angle threshold \\
WTB & $q_{0.75}^{\mathrm{wake}}$ & 1.0690, upper-quartile wake-score threshold \\
ERA5 & $\varepsilon_{\mathrm{sshf}}$ & 169,116, 10th percentile of $|\texttt{sshf}|$ on the training split \\
ERA5 & $q_{0.95}^{\Delta}$ & 458,287.125, 95th percentile of $|\Delta\texttt{sshf}|$ on the training split \\
\bottomrule
\end{tabularx}
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A5.} Active routing-loss weights in the reported corrected models.}
\begin{tabularx}{0.90\textwidth}{>{\raggedright\arraybackslash}p{0.18\textwidth} >{\centering\arraybackslash}p{0.18\textwidth} >{\centering\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}X}
\toprule
Weight & WTB & ERA5 & Role \\
\midrule
$\lambda_{\mathrm{bal}}$ & 1000 & 0.01 & Expert-usage stabilization \\
$\lambda_{\mathrm{align}}$ & 5000 & 0.2 & Coarse regime alignment \\
$\lambda_{\mathrm{force}}$ & 10000 & 0 & Boundary-focused forcing \\
$\lambda_{\mathrm{aux}}$ & 250 & 0 & Wake-sensitive auxiliary routing \\
$\lambda_{\mathrm{smooth}}$ & 0.05 & 0.05 & Local routing coherence \\
\bottomrule
\end{tabularx}
\end{table}
```

## Statistical claim boundaries {.unnumbered}

Table A6 records the reviewer-facing statistical boundary used for wording. The RMSE price versus Graph WaveNet is FDR-significant, gate-alignment deltas versus the full physics-aligned MoE are positive but not FDR-significant, and boundary-window quantile reserve comparisons have bootstrap intervals crossing zero. These tests are why the main text uses price, diagnostic, and bounded-claim language rather than forecast- or reserve-superiority wording.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A6.} Statistical claim boundaries used for reviewer-facing wording.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.11\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Claim & Estimate & 95\% CI & $p_{\mathrm{BH}}$ & Wording consequence \\
\midrule
Accuracy price vs Graph WaveNet & 9.029 & -- & <0.001 & Boundary router is significantly worse on headline RMSE \\
Boundary-band accuracy price & 17.758 & -- & 0.001 & The price also appears in the boundary window \\
Gate NMI vs full physics-aligned MoE & 0.040 & [0.008, 0.071] & 0.066 & Positive but not FDR-significant; cite as bounded mechanism contrast \\
Gate ARI vs full physics-aligned MoE & 0.035 & [-0.000, 0.078] & 0.126 & Positive but not FDR-significant; avoid superiority wording \\
Boundary quantile cost vs GWN physical bin & -0.263M & [-10.704M, 9.782M] & -- & CI crosses zero; reserve cost should remain a diagnostic claim \\
Boundary quantile violation vs GWN physical bin & 0.003 & [-0.011, 0.020] & -- & CI crosses zero; no universal reserve-policy optimality claim \\
\bottomrule
\end{tabularx}
\end{table}
```

## Outcome-channel sanity audit {.unnumbered}

Table A7 adds a bounded check for the shared-anchor concern. It does not use pitch-threshold labels to score the contrast: validation data define a wind-speed-bin power curve, and the test-set comparison is restricted to 9.5--11.5 m s$^{-1}$ boundary anchors with fine wind-bin adjustment. The result asks whether the recovered gate separates samples with different future active-power response, not whether it discovers a regime without anchors.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A7.} Outcome-channel sanity audit for the shared-anchor concern.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Check & Five-seed summary & Interpretation \\
\midrule
Boundary cells per seed & 3276 MPPT / 10465 pitch & 9.5--11.5 m s$^{-1}$ test anchors \\
Future mean power & 100.0 $\pm$ 17.5 kW & Pitch-gate minus MPPT-gate after wind-bin adjustment \\
Power-curve residual & 100.0 $\pm$ 17.5 kW & Validation wind-bin power curve only; no pitch label used \\
Future power ramp & 81.8 $\pm$ 24.7 kW & Mean late-horizon minus early-horizon power \\
Anchor-time Patv & -44.1 $\pm$ 32.5 kW & Current active power is not driving the same positive contrast \\
Residual claim boundary & sanity check only & Mitigates circularity concern; does not prove anchor-free discovery \\
\bottomrule
\end{tabularx}
\end{table}
```

## External-site deployment-gate audit {.unnumbered}

Table A8 records the go/no-go interpretation used for the external evidence. The first row is the positive control: retrained on the ENGIE La Haute Borne farm, where blade pitch is directly observed in 99.2\% of cells, the routing mechanism recovers the declared boundary and clears the held-out criterion. The remaining rows map the failed or incomplete Kelmarsh/Penmanshiel signals to the deployment action that follows. The table therefore supports a bounded but two-sided claim: the mechanism transfers where the control boundary is observable, while direct gate-bin reserve use at the Kelmarsh/Penmanshiel pair remains a screening protocol rather than an authorized transfer.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A8.} External-site deployment-gate audit and wording boundary.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.20\columnwidth} >{\raggedright\arraybackslash}p{0.33\columnwidth} >{\raggedright\arraybackslash}p{0.22\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Gate & Observed external evidence & Go/no-go rule & Claim consequence \\
\midrule
Cross-site recovery (La Haute Borne) & Five-seed chronological routing NMI 0.941, ARI 0.971; pitch observed in 99.2\% of cells, no proxy & Held-out NMI $\geq$ 0.50 with observed pitch after parameters are frozen & Go: boundary recovers where pitch is observable; cite as positive cross-site control \\
Cross-site routing criterion & 80/80 runs complete; mean NMI 0.4877 below threshold 0.50; mean ARI 0.5112 & Held-out NMI $\geq$ 0.50 and balanced accuracy $\geq$ 0.50 after parameters are frozen & No-go for cross-farm router interpretation; cite as negative boundary-condition evidence \\
Local boundary recalibration & Default test NMI 0.1324 $\rightarrow$ recalibrated 0.1491 (delta +0.0167) & Rated wind, pitch threshold, boundary band, and gate-map selected on calibration only & Local threshold transfer is insufficient; re-estimate before use \\
Small-window adaptation & 40/40 routing runs adapted; chronological balanced accuracy 0.4787 below 0.50 & Small calibration windows must still pass the frozen held-out routing criterion & Calibration alone does not authorize external reserve use \\
Sensor and boundary support & Penmanshiel-to-Kelmarsh leave-one pitch-feature coverage 0.0000 and effective boundary cells 0 & Pre-declared calibration window with enough boundary cells, active power, availability mask, and pitch/proxy overlap & No physical-router interpretation without observability \\
External reserve-use decision & Upstream gates do not pass before reserve allocation is evaluated & Transition-window shortage and violation improve at acceptable reserve-energy cost & Withhold gate-bin reserve use outside WTB; report a deployment protocol only \\
\bottomrule
\end{tabularx}
\end{table}
```

## La Haute Borne anchor-observability replay audit {.unnumbered}

Table A9 audits the load-bearing channels behind the La Haute Borne positive control. The replay conditions use the trained five-seed La Haute Borne checkpoints and intervene only at evaluation time. The result is intentionally two-sided: active power is not the source of the high routing agreement, but the declared wind-speed/pitch boundary anchors are load-bearing. This supports citing La Haute Borne as an anchor-observable positive-control replication and blocks any anchor-free discovery wording.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9.} La Haute Borne anchor-observability replay audit.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.31\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Replay condition & NMI & $\Delta$NMI & Interpretation \\
\midrule
Actual replay & 0.941 & 0.000 & reference five-seed route \\
Zero pitch anchor & 0.696 & 0.245 & partial alignment remains \\
Zero wind-speed anchor & 0.752 & 0.189 & partial alignment remains \\
Zero active-power anchor & 0.953 & -0.013 & active power is not load-bearing \\
Zero wind+pitch anchors & 0.001 & 0.940 & boundary alignment collapses \\
Randomize anchor physics & 0.028 & 0.913 & physical anchor mapping collapses \\
Wind-speed only & 0.752 & 0.189 & single-anchor partial control \\
Pitch only & 0.670 & 0.271 & single-anchor partial control \\
\bottomrule
\end{tabularx}
\end{table}
```

## Early-warning detection consequence {.unnumbered}

Table A10 reports the cell-count version of the label-degradation audit. Counts are turbine-time cells per seed inside the six-step MPPT-to-pitch window; they are not MWh, currency, or dispatch-cost estimates. The purpose is narrower: it shows how many early pitch-window cells the gate preserves when a threshold-label rule is delayed, incomplete, or noisy.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A10.} Early-warning detection consequence under degraded threshold labels.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\columnwidth} >{\centering\arraybackslash}p{0.22\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\centering\arraybackslash}X}
\toprule
Condition & Gate detected / missed & Degraded rule detected / missed & Recovered cells \\
\midrule
Delay, 1 step & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 485.0 $\pm$ 0.0 / 255.0 $\pm$ 0.0 & 225.6 $\pm$ 20.6 \\
Delay, 3 steps & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 282.0 $\pm$ 0.0 / 458.0 $\pm$ 0.0 & 428.6 $\pm$ 20.6 \\
Delay, 6 steps & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 145.0 $\pm$ 0.0 / 595.0 $\pm$ 0.0 & 565.6 $\pm$ 20.6 \\
50\% label availability & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 376.0 $\pm$ 10.4 / 364.0 $\pm$ 10.4 & 334.6 $\pm$ 28.1 \\
25\% label availability & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 179.0 $\pm$ 7.9 / 561.0 $\pm$ 7.9 & 531.6 $\pm$ 22.9 \\
Sensor noise, strongest & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 482.8 $\pm$ 11.0 / 257.2 $\pm$ 11.0 & 227.8 $\pm$ 20.9 \\
\bottomrule
\end{tabularx}
\end{table}
```

## Reserve-policy claim-boundary audit {.unnumbered}

Table A11 consolidates the reserve evidence used for wording. It separates the same-model boundary-window diagnostic from claims that the experiments do not support. Costs are normalized reserve-energy proxy units, not currency, market prices, or security-constrained dispatch costs.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A11.} Reserve-policy claim-boundary audit.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.22\columnwidth} >{\raggedright\arraybackslash}p{0.36\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Boundary & Evidence & Wording rule \\
\midrule
Same-model boundary reserve effect & At rho=10, gate-bin vs same-router global: Delta cost -3.55M, Delta viol. -0.0138, reserve +1.85M, shortage -0.54M. & Claim a same-predictor transition-window diagnostic; do not present this as a cross-backbone reserve win. \\
Physical-bin quantile comparator & Boundary/physical-bin 83.78M, viol. 0.0880; GWN/physical-bin 84.31M, viol. 0.0931; Boundary/gate-bin 84.58M, viol. 0.0900. & Say physical-bin baselines are competitive and sometimes lower-cost; avoid gate-bin optimality wording. \\
Cost-ratio applicability & rho=2 inactive; rho=5 to 10 lowers boundary cost and violation; rho=20 narrows; rho=50 favors global (+5.93M, viol. +0.0035). & Claim moderate-cost transition-window value only; do not assert a universal shortage-penalty policy. \\
Full-sample system value & Full sample at rho=10: GWN/global 464.07M, viol. 0.0901; Boundary/gate-bin 481.36M, viol. 0.1214. & Do not claim system-wide dispatch value or reserve superiority; keep the consequence bounded to the boundary slice. \\
Seed-level uncertainty & Full-sample paired total-cost delta +17.28M, 95\% CI [-52.09M, +87.95M], perm. p=0.752. & Use bounded diagnostic language; do not cite the reserve audit as a statistically settled improvement. \\
Operational scope & Costs are normalized reserve-energy proxy units from validation-frozen shortfall quantiles; OPF, unit commitment, delivery constraints, market clearing, and prices are excluded. & Use as a screening audit for reserve exposure, not as a market or security-constrained dispatch study. \\
\bottomrule
\end{tabularx}
\end{table}
```

## Engineering-unit reserve-value translation {.unnumbered}

Table A12 provides the engineering-unit translation of the main reserve audit. The conversion uses the WTB active-power unit (kW) and the cache time step ($\Delta t=1/6$ h), so reserve and shortage totals become rolling forecast-cell MWh-equivalent values. The EUR column is a scenario translation under an assumed reserve carrying cost of 100 EUR/MWh. It is included to make the operational scale legible, not to claim market settlement, OPF, unit commitment, or security-constrained dispatch value.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.06}
\caption*{\textbf{Table A12.} Engineering-unit reserve-value translation at $\rho=10$.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Comparison & $\Delta$ reserve MWh-eq. & Avoided shortage MWh-eq. & $\Delta$ cost MWh-eq. & $\Delta$ EUR at 100/MWh & Wording \\
\midrule
Boundary gate-bin vs same-router global & +1846.9 & +539.8 & -3551.4 & -355k & Use as bounded boundary-window value, not cross-backbone superiority. \\
Boundary gate-bin vs GWN physical-bin & +2319.2 & +205.6 & +262.9 & +26k & Shows gate-bin is close to a strong physical-bin comparator; not a lower-cost claim. \\
Boundary gate-bin vs GWN global full sample & +3148.2 & -1413.5 & +17283.2 & +1728k & Blocks system-wide dispatch or full-sample reserve-superiority wording. \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize MWh-eq. denotes forecast-cell MWh-equivalent accounting from kW active-power shortfall and $\Delta t=1/6$ h. EUR values are scenario translations under an assumed reserve carrying cost of 100 EUR/MWh; they are not market-settlement, OPF, or unit-commitment results.
\end{table}
```
