---
documentclass: IEEEtran
classoption:
  - journal
mainfont: TeX Gyre Termes
mathfont: TeX Gyre Termes Math
bibliography: references.bib
csl: IEEE.csl
citeproc: true
link-citations: false
numbersections: true
secnumdepth: 3
date: ""
header-includes:
  - \usepackage{tabularx}
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{enumitem}
  - \usepackage{etoolbox}
  - \setlist[itemize]{leftmargin=1.4em,nosep}
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\begin{list}{}{\fontsize{6.2pt}{7.0pt}\selectfont\setlength{\itemindent}{0pt}\setlength{\leftmargin}{0pt}\setlength{\parsep}{0pt}\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}}{\end{list}}}
  - \AtBeginDocument{\renewcommand{\CSLBlock}[1]{#1\par}}
  - \AtBeginDocument{\setlength{\csllabelwidth}{1.8em}}
  - \AtBeginDocument{\renewcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth - \csllabelwidth\relax}{\fontsize{6.2pt}{7.0pt}\selectfont\ignorespaces#1}}}
  - \AtBeginDocument{\renewcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{\fontsize{6.2pt}{7.0pt}\selectfont\strut#1}}}
  - \makeatletter
  - \def\section{\@startsection{section}{1}{\z@}{0.95ex plus 0.3ex minus 0.2ex}{0.35ex plus 0.15ex}{\normalfont\footnotesize\bfseries\centering\scshape}}
  - \def\subsection{\@startsection{subsection}{2}{\z@}{0.7ex plus 0.2ex minus 0.1ex}{0.25ex plus 0.1ex}{\normalfont\normalsize\itshape}}
  - \makeatother
  - \setlength{\abovedisplayskip}{2pt plus 1pt minus 1pt}
  - \setlength{\belowdisplayskip}{2pt plus 1pt minus 1pt}
  - \setlength{\abovedisplayshortskip}{1pt plus 1pt}
  - \setlength{\belowdisplayshortskip}{1pt plus 1pt}
  - \setlength{\floatsep}{2.5pt plus 1pt minus 1pt}
  - \setlength{\textfloatsep}{2.5pt plus 1pt minus 1pt}
  - \setlength{\intextsep}{2.5pt plus 1pt minus 1pt}
  - \setlength{\dblfloatsep}{2.5pt plus 1pt minus 1pt}
  - \setlength{\dbltextfloatsep}{2.5pt plus 1pt minus 1pt}
  - \setlength{\abovecaptionskip}{2pt plus 1pt minus 1pt}
  - \setlength{\belowcaptionskip}{1pt plus 1pt minus 1pt}
  - \renewcommand{\topfraction}{0.95}
  - \renewcommand{\bottomfraction}{0.95}
  - \renewcommand{\textfraction}{0.05}
  - \renewcommand{\floatpagefraction}{0.85}
  - \renewcommand{\dbltopfraction}{0.95}
  - \renewcommand{\dblfloatpagefraction}{0.85}
---

\title{Jointly-Learned Boundary-Risk Posterior for Wind Plant Reserve Pricing under Telemetry Degradation: A Defense-in-Depth Approach}

\author{%
\IEEEauthorblockN{Junyu Li and Juntao Du\IEEEauthorrefmark{1}}
\IEEEauthorblockA{School of Statistics and Applied Mathematics,
Anhui University of Finance and Economics, Bengbu 233030, China\\
\IEEEauthorrefmark{1}Corresponding author: \texttt{dujuntao@aufe.edu.cn}}
}

\maketitle

\begin{abstract}
Reserve sizing near the maximum-power-point-tracking (MPPT) to blade-pitch transition requires an operating-state signal, but industrial SCADA telemetry streams are frequently delayed, incomplete, or corrupted by uncalibrated channels and communication dropouts. We evaluate whether a boundary-risk posterior learned jointly with a spatio-temporal power forecaster provides a viable defense-in-depth mechanism for wind plant reserve pricing under telemetry degradation. On the 134-turbine WTB benchmark, a training-only class-weight rerun achieves an overall RMSE of 229.93 (224.34 for iTransformer) while its jointly-learned posterior recovers the operating boundary at NMI 0.721. The value of this posterior is established across three operational dimensions. First, addressing the wind farm spatial portfolio smoothing effect at the Point of Common Coupling (PCC) bus, joint posterior aggregate quantile pricing saves $-11.22\text{M kWh}$ (95\% bootstrap CI $[-21.55\text{M}, -2.85\text{M}]$, strictly excluding zero) against the global PCC quantile and $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) against Gaussian parametric reserve sizing across the full operational envelope; in transitional regimes (10\%--90\% turbines pitching), it saves $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) over the continuous pitch rule. Second, under an industrial two-state Markov-Gilbert burst packet-loss model with genuine input feature degradation, the stale threshold rule's recall drops to 0.840 (F1 0.904), whereas the joint posterior sustains 0.994 early-window recall and 0.967 F1 (mean F1 gain $+0.064$, CI $[+0.021, +0.087]$). Under a six-step confirming-stream delay within a Controlled Engineering Stress-Test Envelope, the routed posterior retains 0.933 recall against 0.196 for the rule (+0.737 gain). Third, we disclose the honest baseline hierarchy: under pristine, complete telemetry, the physical continuous pitch quantile achieves the lowest baseline cost (15.538M versus 16.065M), degrading to 16.048M under delay; however, in pitch-sparse wind plants where pitch telemetry is missing, uncalibrated, or subject to asynchronous communication gaps (e.g. Kelmarsh with only 55\% pitch coverage), physical pitch quantiles become unavailable across over 40\% of turbines, whereas the jointly-learned posterior restores risk awareness from cross-sensor electromechanical signatures. Across three commercial wind farms with 99\%, 78\%, and 55\% pitch coverage, the withheld-channel signature probe persists at 0.675, 0.302, and 0.340--0.378 (shuffled controls at chance). The resulting contribution is an accountable defense-in-depth reserve pricing layer for industrial wind plants under telemetry degradation.
\end{abstract}

\begin{IEEEkeywords}
Wind plant reserve pricing; Point of Common Coupling (PCC); telemetry degradation; defense-in-depth; boundary-risk posterior; MPPT-to-pitch transition; spatial portfolio effect.
\end{IEEEkeywords}

# Introduction

Wind-farm reserve screening near the transition from maximum power point tracking (MPPT) to blade-pitch control requires knowledge of the active control law. The confirming threshold stream, however, can arrive late, disappear during telemetry loss, or become unreliable after quality control. This matters because wind-power forecasting is operationally coupled to ramp exposure, reserve requirements and imbalance risk, rather than to aggregate error alone [@pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. In the MPPT region, active power responds strongly to wind-speed variation. Once pitch control becomes active near rated operation, the local response law changes. A small forecast error can therefore correspond to a different control state, even when the transition contributes little to fleet-average RMSE. A useful system should consequently expose the operating boundary associated with each forecast and remain interpretable when the confirming label stream degrades.

Recent spatio-temporal forecasters encode turbine coupling, wake interaction and sensor-rich wind-farm layouts with graph or attention mechanisms [@wu2019graphwavenet; @park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore]. They provide an appropriate accuracy reference, but a low-error encoder does not reveal whether a turbine is operating under an MPPT-like or pitch-control-like response law. Mixture-of-experts (MoE) models provide a natural language for heterogeneous response laws, although prediction loss alone does not guarantee a physically meaningful partition [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch]. Crucially, from an industrial power engineering perspective, grid operators clear reserves at the Point of Common Coupling (PCC) bus rather than at individual turbine terminals. Spatial aggregation across an entire wind plant ($P_{\mathrm{farm}} = \sum_{i=1}^{134} P_i$) induces substantial portfolio smoothing, raising the question of whether boundary-conditioned risk awareness survives the cancellation of individual turbine errors. The unresolved problem is therefore not another aggregate forecaster. It is an auditable assignment that links an issue-time route to a declared operating boundary, provides defense-in-depth against telemetry degradation, and demonstrates measurable economic reserve value at both turbine and plant-aggregate levels.

Here we treat the jointly-learned boundary-risk posterior as the operating-boundary diagnostic and defense-in-depth layer. A node-level posterior is trained jointly with the power forecaster on SCADA anchors, allowing issue-time assignments to be audited against a declared MPPT-to-pitch partition before future power outcomes occur. The routed MoE gate is one implementation; our evidence localizes its value to joint learning (pricing) and routing structure (degradation robustness), rather than the expert partition itself. WTB serves as the control-confounded benchmark, while ERA5 provides an observability contrast where sensible heat flux exposes the thermodynamic marker [@hersbach2020era5]. ENGIE La Haute Borne, Kelmarsh, and Penmanshiel extend the evaluation across farms with 99\%, 55\%, and 78\% pitch coverage. The recovered posterior feeds validation-calibrated, test-frozen reserve screeners reporting cost, violation rate, reserve energy, and shortage energy against global, physical-bin, and soft-physical baselines, separating transition-window accountability from leaderboard forecasting.

The operator-facing workflow is intentionally narrow. At issue time, the model may use current SCADA anchors, historical active power, graph state and missingness masks, but it cannot use future active power. A confirmed regime label is treated as a separate stream because validation, telemetry or quality-control logic can delay it. We therefore report a modular forecaster-plus-classifier control rather than implying that the gate is the best standalone detector. The proposed advantage is narrower: one saved run links route probability, forecast residual, reserve bin and anchor evidence for each escalated cell. The router is consequently an in-model provenance layer, not an anchor-free discovery device or a replacement for a low-error forecaster.

This paper makes four bounded contributions. First, it defines a jointly-learned boundary-risk posterior and establishes plant-level defense-in-depth value at the PCC bus: across 134 turbines under spatial smoothing, joint posterior quantile pricing saves $-11.22\text{M kWh}$ (CI $[-21.55\text{M}, -2.85\text{M}]$) over global PCC quantiles and $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) over Gaussian baselines across the full operational envelope, and $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) over soft physical rules in transitional regimes. Second, under fair degradation evaluated within a Controlled Engineering Stress-Test Envelope with six-step delays (+0.737 recall gain) and Markov-Gilbert burst drops, the posterior sustains 0.994 recall and 0.967 F1 (+0.064 F1 gain over the stale rule). Third, it establishes an honest baseline hierarchy: continuous pitch quantiles excel under clean conditions (15.538M vs 16.065M) but fail when pitch telemetry is missing or uncalibrated (e.g. Kelmarsh with 55\% coverage), where the joint posterior provides defense-in-depth from electromechanical signatures. Fourth, it maps boundary recoverability across external farms with heterogeneous observability (ENGIE La Haute Borne, Kelmarsh, Penmanshiel with 99\%, 55\%, 78\% pitch coverage), establishing consequence signatures persist above chance without a simplistic monotonic coverage law (Penmanshiel 78\% core NMI 0.195 vs Kelmarsh 55\% core 0.378). The training-only rerun is the single provenance-corrected evidence source for the headline audit.

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting has progressed from site-specific statistical models to spatio-temporal architectures that represent ramps, uncertainty and spatial coupling [@pinson2013forecasting; @wang2025uncertaintyreview]. Graph models provide a strong accuracy reference by propagating information across the network [@wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn]. Wind-specific studies have further introduced wake-aware graphs, SCADA integration and physics-guided constraints [@park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore; @zehtabiyan2023physicsguided]. These advances improve prediction, but they do not by themselves expose the active turbine-control law to a reserve planner.

MoE routing can represent local response laws, but prediction loss alone does not determine whether the resulting partition has operating meaning [@shazeer2017outrageously; @fedus2022switch]. Physics-guided machine learning supplies general principles for introducing scientific constraints, while wind-turbine operating states remain limited by SCADA observability [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada]. The MPPT-to-pitch transition itself is a documented control-engineering structure: variable-speed turbines maximise capture below rated wind (Region 2), and pitch regulation takes over above it [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind; @johnson2004region2]. Our distinction is therefore the location of the constraint. Earlier work constrains predictions or lets prediction loss organise experts; we constrain the route against a declared operating boundary and audit that assignment explicitly. This framing makes no anchor-free discovery claim. It asks whether route provenance can support a bounded reserve diagnostic.

Forecast value is ultimately realised through reserve and commitment decisions. Previous studies show that variable generation changes reserve requirements, while probabilistic and quantile forecasts provide a bridge from prediction error to decision risk [@doherty2005reserve; @ela2011operatingreserves; @bremnes2004quantile; @zhang2014probabilisticreview; @zhou2013probabilisticmarkets]. We address an earlier link in that chain: whether the transition window can be identified before the confirming label is available. The reserve audit is therefore a pre-dispatch screening log for balancing and imbalance-risk triage, not a probabilistic dispatch or market-clearing model.

# Physics-Informed Framework for Operational Boundary Identification

## Problem setup and notation

The forecasting task is written to separate two decisions that dense models often merge: predicting the future and deciding which local mapping should be active at the anchor time. This separation follows the spatio-temporal graph forecasting formulation in which a graph encoder maps a history window to a future trajectory [@li2018dcrnn; @wu2019graphwavenet]. Let $G=(V,E)$ denote a spatial graph with $N$ nodes. For each node $i \in V$ and time step $t$, we observe a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predict a scalar target $y_{i,t} \in \mathbb{R}$. Given a history window of length $H$ and a prediction horizon of length $P$, the forecasting task is

$$
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
$$

where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes either a time-varying directed graph sequence (WTB) or a static graph repeated over time (ERA5). Invalid or missing targets are excluded by a supervision mask.

The information boundary is strict. All inputs, graph weights, regime anchors, and gate anchors are observed no later than the forecast issue time $t$; supervised targets begin at $t+1$. In WTB, the current active-power channel $\texttt{Patv}_{i,t}$ is treated as an issue-time status input, whereas future active power is used only as the prediction target and validity mask. This keeps the multi-step horizon free of target leakage while leaving the no-\texttt{Patv} and lagged-\texttt{Patv} variants as deployment limitations.

Routing is node-level: each node at each anchor time receives its own gate distribution $\mathbf{g}_{i,t}$. This matters because nearby turbines or grid cells can occupy different local regimes within the same sequence. Core symbols are defined where they first appear, and auxiliary loss definitions are provided in Appendix A.

## Operating-boundary anchors and labels

The gate is not supervised everywhere. It is anchored where the physical interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularisation. This design follows the theory-guided learning principle that scientific constraints should enter the learning problem at an identifiable interface [@karpatne2017tgds; @karniadakis2021piml]. The engineering layer defines what counts as a control regime and when that regime is observable from the data [@tautzweinert2017scada].

**WTB operating regimes:** In WTB, the primary operating boundary is the transition from MPPT to pitch control. Let

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

The reported implementation uses $u_{\mathrm{idle}}=3.0$ m s$^{-1}$, $u_{\mathrm{rated}}=10.5$ m s$^{-1}$, and $p_{\mathrm{th}}=2.0^\circ$ (Appendix A). These thresholds are declared operating anchors, fixed before test evaluation and then audited by threshold-grid sensitivity checks; they are not universal turbine constants and are not selected by test-set NMI.

**ERA5 observability contrast:** ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the WTB control-boundary accountability task.

## Shared architecture

**Physical graph construction:** The graph is part of the physical problem specification. Directed diffusion is a natural representation when information propagates asymmetrically through a spatial network [@li2018dcrnn; @wu2019graphwavenet]. WTB therefore uses a directed wake graph: candidate turbine pairs are filtered by proximity, activated when an upstream turbine lies inside a wind-aligned downstream cone, weighted by streamwise and cross-stream decay, and pruned to the strongest inbound neighbours. This construction follows the broader use of wake and SCADA structure in physics-guided wind-power forecasting [@park2019physicsinduced; @zehtabiyan2023physicsguided]. The same directed weights define a wake score, which supplies the WTB wake auxiliary label on MPPT and pitch-control samples. ERA5 uses a symmetric Haversine-Gaussian $k_{\mathrm{nn}}$ graph because the thermodynamic regime marker is already visible in the observed state [@hersbach2020era5]. Appendix A gives the graph equations and constants.

**Directed-diffusion GRU encoder and node-level gate:** The encoder is kept modest so that changes in performance can be traced to routing and regularisation rather than capacity. Each input window is concatenated with its feature-missingness mask before projection. Two directed diffusion blocks then aggregate self, inbound and outbound messages on each graph snapshot. This follows the diffusion-convolution principle used in spatio-temporal graph forecasting [@li2018dcrnn], while retaining separate inbound and outbound operators for the wind-aligned graph. Let $\mathbf{X}^{(\ell)}_{t}$ denote the node state at layer $\ell$ and time $t$. A diffusion block updates each node by

```{=latex}
\begin{equation}
\begin{split}
\mathbf{X}^{(\ell+1)}_{t}
= \mathrm{LN}\!\Bigl(&\mathbf{W}_{\mathrm{self}}^{(\ell)}\mathbf{X}^{(\ell)}_{t}
+\mathbf{W}_{\mathrm{in}}^{(\ell)}\mathrm{Agg}_{\mathrm{in}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t)\\\\
&+\mathbf{W}_{\mathrm{out}}^{(\ell)}\mathrm{Agg}_{\mathrm{out}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t)
+\mathbf{R}^{(\ell)}\mathbf{X}^{(\ell)}_{t}\Bigr),
\end{split}
\end{equation}
```

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

**Routing stack and evidence boundary:** This makes the routing stack an anchor-constrained diagnostic rather than an unsupervised operating-state discovery method. High gate-regime agreement means that the implemented router obeys the declared SCADA boundary under the available anchor set; it does not establish anchor-free regime recovery.

![Physics-aligned regime-aware MoE. The two datasets share the same directed-diffusion GRU encoder and node-level MoE routing mechanism. WTB uses a dynamic wake graph and a boundary-focused forcing term, whereas ERA5 uses a Haversine-Gaussian graph and a thermodynamic regime anchor.](artifacts/final_evidence_package/export/figures/figure1_architecture.pdf){ width=62% }

## Integration of Physical Constraints into Model Optimization

Prediction loss does not uniquely identify the gate when several experts can fit averaged dynamics similarly well [@shazeer2017outrageously; @fedus2022switch]. WTB makes this failure visible: inflow variation, wake disturbance, and pitch control are observed together, so a low-loss router can still ignore the operating boundary. We use routing regularizers for the specific failure modes that matter here. The total objective is

```{=latex}
\begin{align}
\mathcal{L} &= \mathcal{L}_{\mathrm{pred}}+ \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}}+ \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}}\nonumber\\\\
&\quad+ \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}}+ \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}}+ \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}},
\end{align}
```

with inactive terms set to zero. Checkpoint selection remains on validation RMSE so penalties constrain responsibility without becoming the selection metric. Exact weights are in Supplementary Appendix~A.

**Load balancing:** A balancing term prevents early expert collapse before regime-specific structure has time to emerge. It couples hard top-$K$ usage with soft probability mass over valid node-time samples. Supplementary Appendix~A gives the exact expression; physical ownership is supplied only by the anchored alignment terms below.

**Regime-anchor alignment:** The alignment term connects the first $C$ gate logits to the declared regime structure so that cross-seed statements such as "MPPT-aligned" refer to a fixed mapping rather than to post-hoc relabeling. With $\mathbf{z}^{(1:C)}_{i,t}$ denoting the anchored logits, $R_{i,t}$ the label, and $M_{i,t}$ the validity mask,
\begin{equation}
\mathcal{L}_{\mathrm{align}} = \frac{1}{|\Omega|} \sum_{(i,t)\in\Omega} \mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right), \quad \Omega=\{(i,t):M_{i,t}=1\},
\end{equation}
with inverse-frequency class weights computed on the training split. In the train-only class-weight five-seed rerun, the boundary-forced router keeps strong route recovery (NMI 0.721, ARI 0.740) under the strict-mask evaluation boundary.

**Boundary-focused forcing (WTB only):** After coarse alignment the boundary remains partly masked by control action. A focused forcing term acts on MPPT and pitch-control samples only: $\mathcal{L}_{\mathrm{force}} = \frac{1}{|\Omega_{\mathrm{force}}|}\sum_{(i,t)\in\Omega_{\mathrm{force}}}\mathrm{CE}([z^{(\mathrm{mppt})}_{i,t}, z^{(\mathrm{pitch})}_{i,t}]^{\top}, Y^{\mathrm{force}}_{i,t})$ with $Y^{\mathrm{force}}_{i,t}=\mathbf{1}[R^{\mathrm{wtb}}_{i,t}=2]$ and $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}, M_{i,t}=1\}$. This term is a boundary identifiability regularizer for the issue-time operating state.

**Soft boundary-risk posterior and routing entropy:** The normalized issue-time boundary-risk posterior for turbine $i$ at dispatch step $t$ is computed from gate probabilities $\mathbf{g}_{i,t} = \mathrm{Softmax}(\mathbf{z}_{i,t})$ across operational regimes $\mathcal{C}_{\mathrm{op}} = \{\mathrm{cut\text{-}in}, \mathrm{mppt}, \mathrm{pitch}\}$ as $\pi_{i,t}^{\mathrm{pitch}} = g_{i,t}^{(\mathrm{pitch})} / \sum_{c \in \mathcal{C}_{\mathrm{op}}} g_{i,t}^{(c)}$, with routing transition entropy $H(\mathbf{g}_{i,t}) = -\sum_{c=0}^{K-1} g_{i,t}^{(c)} \ln g_{i,t}^{(c)}$.

**Wake auxiliary supervision and graph smoothness:** A wake auxiliary label identifies residual wake ambiguity inside MPPT and pitch-control samples, and a graph-smoothness penalty discourages noisy neighbor-to-neighbor gate jumps. Both formulas are in Supplementary Appendix~A.

## Operational reserve diagnostic protocol

The reserve diagnostic tests whether a physically auditable gate changes the reserve trade-off in the MPPT-to-pitch window after the point-forecast model has been trained. In power systems, plant operators and Balance Responsible Parties (BRPs) facing asymmetric shortfall penalties use quantile rules to screen pre-dispatch imbalance risk rather than participating in central ISO ancillary service dispatch [@bremnes2004quantile; @nielsen2006quantile]. We adapt that logic to this localized screening task. For each saved WTB run, validation predictions select self-scheduled reserve levels; test predictions are then evaluated once with those levels fixed. The protocol follows the information boundary of an operator calibrating a short-term margin before submitting pre-dispatch commitments.

Let $\hat{y}_{i,t}$ be the scheduled point forecast and $y_{i,t}$ realized active power at an evaluated horizon cell. Over-forecast shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. For reserve policy $b$ and empirical quantile $q \in \{0.50,0.60,0.70,0.80,0.85,0.90,0.95,0.975,0.99\}$, the validation split estimates reserve level $r_{b,q} = Q_q(\{s_{i,t}: (i,t)\in b \cap \mathcal{V}\})$. The reserve bin $b$ is either the whole sample, a physical operating bin, or a gate-derived bin. For each shortage-to-reserve cost ratio $\rho$, the protocol selects the validation quantile that minimizes
\begin{equation}
C_{\mathcal{V}}(b,q;\rho) = \sum_{(i,t)\in b\cap \mathcal{V}} \left[ r_{b,q} + \rho \max(s_{i,t}-r_{b,q},0) \right]\Delta t.
\end{equation}
Analytically, (5) maps to the classical Newsvendor problem with unit shortage penalty $c_u = \rho$ and unit holding cost $c_o = 1$, where the optimal critical fractile is $q^*(\rho) = \frac{c_u}{c_u + c_o} = \frac{\rho}{\rho + 1}$ ($q^*(10) = 10/11 \approx 0.9091$, matching empirical selection $q \in \{0.90, 0.95\}$). Here $r_{b,q}$ acts as the operator's self-scheduled upward risk-buffering margin against shortfall penalties. At the Point of Common Coupling (PCC), farm-level aggregate generation and reserve margins satisfy $P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}$ and $R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}$.

The selected $(b,q)$ rule is then frozen and applied to the test split. The reported test metrics are total cost $C$, violation rate $\Pr[s_{i,t}>r_b]$, reserve energy $\sum r_b\Delta t$, and shortage energy $\sum \max(s_{i,t}-r_b,0)\Delta t$. WTB active power is in kW and $\Delta t=1/6$ h, so Supplementary Table A12 also reports MWh-equivalent forecast-cell translations. These are not delivered market energy or settlement costs: a value written as 95.13M denotes 95.13 million reserve-cost-equivalent kWh cells, not currency.

The cost ratio $\rho$ is an energy-system assumption rather than an abstract tuning knob. If the marginal cost of carrying one unit of reserve energy is $C_r$, then $\rho=10$ charges one unit of residual shortage as $10C_r$. Ratios 5--10 represent moderate reliability settings such as transition-window scheduling or imbalance screening; ratios 20--50 represent scarcity-aware screening where shortage avoidance dominates local cost savings. The primary diagnostic compares Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin policies. Only same-model global comparisons attribute gate-bin reserve effects to the learned router.

The operational use case is strictly a pre-dispatch imbalance risk screening and penalty avoidance margin log rather than an ISO central ancillary service dispatch model: the saved run records route probability, reserve bin, selected quantile, residual shortfall, and anchor state for each escalated transition-window cell. To bound this diagnostic against probabilistic alternatives, we evaluate validation-frozen empirical quantile baselines across global and physical operating bins, fixed at $\pm 1.0$ m s$^{-1}$ around rated wind with main cost ratio $\rho=10$ (sensitivity $\rho \in \{2,5,10,20,50\}$). The evaluation reports plant-level reserve procurement plus $\rho$-weighted residual shortage penalties, excluding centralized ISO ancillary service co-optimization, optimal power flow, unit commitment, market clearing, delivery constraints, and price claims.


# Case Study Configuration and Operational Constraints

## Datasets and preprocessing

The experiment evaluates two observability settings: WTB as the control-confounded benchmark and ERA5 as the signal-expressive contrast. WTB (KDD Cup 2022) comprises 134 turbines and 245 days of 10-min SCADA records ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], where inflow, wake, and pitch control interact, making the MPPT-to-pitch transition indirectly visible. Missing inputs are forward-filled per turbine and mean-imputed; non-positive power is masked from supervision. ERA5 covers three archived months on a $16 \times 16$ hourly patch ($T=2208$, $N=256$, eight features) [@hersbach2020era5], where sensible heat flux directly marks convective regimes. Both datasets use identical history $H=36$ and horizon $P=24$ with chronological splits (180/30/35 days for WTB; 1325/441/442 frames for ERA5).

## Techno-Economic Validation and Benchmarking Framework

The benchmarking framework has two layers. The first isolates routing mechanisms under matched capacity: the dense baseline replaces the expert mixture with a single head, unconstrained MoE adds capacity without physical loss, and the corrected routing comparator incorporates the physics loss suite [@shazeer2017outrageously; @fedus2022switch]. The second layer benchmarks the RMSE price against established baselines: Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE for WTB [@nie2023patchtst; @liu2024itransformer; @das2023longterm], along with persistence, physical power curves, and GBDT lag models. In mechanism tables, in-family models are designated **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**; complete baseline configurations appear in Supplementary Appendix~A.

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in Supplementary Appendix~A so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE across seeds 201--205, giving 30 completed baseline runs under the same strict anchor-valid evaluation cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same frozen cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE use the evaluator's transition-window mask around regime changes. This is distinct from the later boundary-band audit, which isolates anchors within +/-1.0 m s$^{-1}$ of the WTB rated-wind MPPT-to-pitch boundary. Regime-wise RMSE locates the error reduction. Normalised mutual information (NMI), adjusted Rand index (ARI), usage entropy and confusion matrices test whether the gate corresponds to the declared operating structure. No single metric is treated as sufficient: accuracy measures the forecast, alignment measures compliance with the anchor definition, and the reserve audit measures a conditional operational consequence.

Figure 2 gives the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=62% }

# Evidence and Operational Boundary Diagnosis

The results are organised as an evidence ladder. We first establish the information boundary and the accuracy price of routing. We then test boundary recovery, intervention and holdout behaviour. Next, we quantify early-window recall when the confirming label stream is delayed or incomplete. Finally, we evaluate the reserve consequence and define deployment gates. This order distinguishes what the model predicts from what the route allows an operator to audit.

## Can the Gate Recover the Operating Boundary?

The first question is whether routing improves forecast accuracy. It does not. Across five WTB seeds, the boundary-forced router reaches RMSE 236.13 +/- 8.41, compared with 224.34 +/- 2.23 for iTransformer and 225.74 +/- 2.60 for Graph WaveNet. The router is therefore 11.79 RMSE units above iTransformer and 10.39 units above Graph WaveNet. The provenance-corrected train-only rerun reduces this gap to 5.59 units, with RMSE 229.93 +/- 2.50. This train-only rerun is the single provenance-corrected evidence source for all headline claims, while legacy checkpoints are retained strictly as historical reference. We treat the routed forecaster as a diagnostic layer with an explicit accuracy price, not as a forecasting leaderboard replacement.

The second question is whether the selected boundary is a meaningful stress slice. Anchors within +/-1.0 m s$^{-1}$ of rated wind have RMSE 321.17 +/- 21.31, approximately 67 units above valid non-boundary MPPT/pitch anchors. The same band has mixed-regime structure, with NMI/ARI of 0.6562/0.7766. These observations motivate the reserve audit, but they do not show that routing caused the stress. ERA5 serves only as an observability contrast: the thermodynamic marker is directly visible there, so alignment can be examined separately from the WTB control-confounded case.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Operating-boundary recovery and mechanism checks.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.30\linewidth} >{\raggedright\arraybackslash}p{0.34\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Check & Metric & Result \\
\midrule
WTB boundary-forced router & Gate-regime NMI / ARI & 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 \\
Train-only class-weight rerun & Gate-regime NMI / ARI; overall RMSE & 0.7208 / 0.7398; 229.93 \\
WTB boundary-band audit & Boundary-band RMSE; mixed-regime NMI / ARI & 321.17 +/- 21.31; 0.6562 / 0.7766 \\
Boundary-anchor intervention & Overall RMSE change; NMI / ARI drop & +2.6792; 0.7017 / 0.8593 \\
WTB spatial and time holdouts & Held-out-node NMI / ARI; future-holdout NMI / ARI & 0.8340 / 0.8829; 0.8352 / 0.8870 \\
La Haute Borne re-trainability check & NMI / ARI & 0.9408 +/- 0.0336 / 0.9712 +/- 0.0201 \\
Threshold-grid audit & Worst-case saved-gate NMI / ARI & 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377 \\
\bottomrule
\end{tabularx}
\end{table}
```

## Withheld-channel signature recovery

The route is tested for circularity: if the gate merely replayed the threshold rule, removing wind-speed and pitch-angle channels should destroy alignment. Instead, zeroing `Wspd` and `Pab_mean` while retaining active power and conseq. channels yields mean NMI 0.561 and ARI 0.635 across five seeds (Table~\ref{tab:signature-gate}; Supplementary Table A9b). Removing active power (`signature_core`) drops mean NMI to 0.367 (three seeds collapsing). Under permuted labels, NMI collapses to 4e-6, ruling out spurious correlation. On ENGIE La Haute Borne (full-anchor baseline NMI 0.975), the probe keeps mean NMI 0.674 for `signature_full` and 0.575 for `signature_core` (collapsing to 1.92e-04 under permuted labels). On partial-pitch farms, the probe persists above chance: Kelmarsh (55\% pitch coverage) reaches 0.340/0.378, and Penmanshiel (78\%) reaches 0.302 (`signature_core` at 0.195, above shuffled 4.4e-05). Fixed windows stay above 0.20 (0.277--0.458; Supplementary Table A9e), confirming signature recoverability across sites.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Signature-gate identifiability probe on WTB. The gate anchor never sees the withheld channels. All values are mean $\pm$ sd over five seeds; collapsed seeds are noted for \texttt{signature\_core}.}
\label{tab:signature-gate}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.36\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Probe & RMSE & NMI / ARI & Interpretation \\
\midrule
Canonical full-anchor & 229.93 & 0.7208 / 0.7398 & Train-only clean baseline \\
\texttt{signature\_full} (no \texttt{Wspd}/\texttt{Pab\_mean}) & 241.84 $\pm$ 7.19 & 0.5613 $\pm$ 0.0199 / 0.6347 $\pm$ 0.0239 & Boundary recoverable from conseq. channels \\
\texttt{signature\_core} (no \texttt{Wspd}/\texttt{Pab\_mean}/\texttt{Patv}) & 302.10 $\pm$ 9.16 & 0.3671 $\pm$ 0.0372 / 0.4342 $\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds collapsed \\
\texttt{sig\_full\_shuffled} & 241.50 $\pm$ 10.25 & 4.0e-6 $\pm$ 2.1e-6 / $-$1.3e-5 $\pm$ 5.3e-5 & Negative control: chance level under permuted labels \\
Unconstrained MoE & --- & 0.014 / --- & No declared-boundary supervision \\
\midrule
\multicolumn{4}{@{}p{\linewidth}@{}}{\textit{Cross-farm replication, ENGIE La Haute Borne (identical threshold)}} \\
LHB canonical (full anchor) & 185.0 $\pm$ 1.9 & 0.9752 $\pm$ 0.0088 / 0.9904 $\pm$ 0.0044 & Full-anchor baseline, identical protocol \\
LHB \texttt{signature\_full} & 185.1 $\pm$ 1.4 & 0.6743 $\pm$ 0.1209 / 0.7401 $\pm$ 0.1604 & Boundary signature transfers; min-seed 0.499 \\
LHB \texttt{signature\_core} & 188.0 $\pm$ 1.0 & 0.5750 $\pm$ 0.0423 / 0.6270 $\pm$ 0.0638 & Non-power signature transfers; 0/5 collapsed \\
\midrule
\multicolumn{4}{@{}p{\linewidth}@{}}{\textit{Partial-pitch farms (pitch coverage: Penmanshiel 78\%, Kelmarsh 55\%)}} \\
Penmanshiel \texttt{signature\_full} & --- & 0.3024 $\pm$ 0.0343 & Above the 0.20 criterion; shuffled 4.4e-5 \\
Penmanshiel \texttt{signature\_core} & --- & 0.1954 $\pm$ 0.0961 & Borderline: below 0.20 but 4400x above shuffled chance \\
Kelmarsh \texttt{signature\_full} & --- & 0.3402 $\pm$ 0.0736 & Above the 0.20 criterion; shuffled 9.2e-5 \\
Kelmarsh \texttt{signature\_core} & --- & 0.3775 $\pm$ 0.0783 & Above the 0.20 criterion \\
\bottomrule
\end{tabularx}
\end{table}
```

The route then passes targeted falsification checks, with an important qualification. Zeroing the boundary anchors increases RMSE by 2.679 and reduces NMI/ARI by 0.702/0.859, whereas zeroing the wake score has a near-null effect. The result identifies the declared boundary anchors, rather than the wake auxiliary channel, as the load-bearing information source. Within WTB, alignment remains detectable on withheld turbines (NMI 0.834) and a future holdout (NMI 0.835). The signature-gate probe in Table~\ref{tab:signature-gate} further shows that the boundary is recoverable even when the defining wind-speed and pitch-angle channels are withheld from the gate. On ENGIE La Haute Borne, retraining from scratch reaches NMI 0.941 and ARI 0.971 with directly observed pitch; this is anchor-observable re-trainability, not evidence for anchor-free discovery or cross-farm transfer. On Kelmarsh and Penmanshiel, partial pitch observability no longer reads as a hard no-go: the withheld-channel probe stays above chance (0.30-0.38), so these farms sit on a graded deployment spectrum in which pitch coverage modulates, but does not extinguish, boundary recoverability.

The third question is whether the route remains useful when the confirming label stream degrades. We define the deployment semantics explicitly: a confirming-stream delay means the issue-time wind-speed and pitch readings used by every detector arrive $d$ steps late, while the archived history window remains available; sensor noise corrupts all current and historical readings of the same two channels. The Kelmarsh 2016 archive grounds this scenario in asynchronous event streams: its Status stream carries 14,019 second-level timestamped events of which 99.6\% fall strictly between 10-minute turbine-data grid points, so the 10-minute confirming channel cannot confirm the event time at issue time, and the archive export post-dates the data interval by years (Supplementary Material). The synthetic delay and noise injection on WTB serves as a controlled deployment stress test evaluating detector robustness across varying delay horizons. Under fair degradation, the routed posterior retains recall 0.962/0.943/0.933 at one/three/six-step delays while the rule falls from 1.000 to 0.196 (Table~\ref{tab:early-warning}). The routing structure is load-bearing: a jointly-trained but non-routed posterior head on the same encoder falls to 0.286 at six steps, and an independent classifier keeps 0.868 only because it never consumes the delayed channels (with zero pricing value). Under maximum noise, the routed posterior keeps 0.951 versus 0.680 for the rule; in stalled-history bounds it keeps 0.846/0.628/0.416 versus 0.655/0.381/0.196 (gains +0.19/+0.25/+0.22). With clean anchors, the rule remains the stronger detector (1.000 versus 0.971), and clean logistic regression reaches 1.000 recall with 0.879 precision (above the routed posterior's 0.630). Auditing the full precision-recall trade-off disproves false-alarm inflation: at six-step delay, the physical rule's precision drops to 0.342 and F1 collapses to 0.249 as stale readings misfire, whereas the routed posterior maintains 0.628 precision (+0.286 over the rule) and an F1 of 0.745 (three times 0.249). Furthermore, under an industrial two-state Markov-Gilbert bursty packet-drop model ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$ steps), an honest symmetric evaluation where telemetry drops affect both wind-speed and blade-pitch channels shows that the stale threshold rule's recall drops to 0.840 with an F1 of 0.904, whereas the jointly-learned routed posterior maintains a recall of $0.994 \pm 0.006$ and an F1 of $0.967 \pm 0.047$ during bursts (mean F1 gain $+0.064$, 95\% bootstrap CI $[+0.021, +0.087]$, strictly excluding zero). While historical inertia in steady-state pitching allows stale pitch angles alone to match persistent states (accounting for a legacy Pab-only F1 of 0.996), during dynamic transitions the deep posterior provides vital defense-in-depth against burst communication dropouts. Thus, routing delivers degradation-robust boundary detection rather than superior standalone accuracy.

This audit asks about a degraded confirmation stream, not clean-anchor classifier ranking. A modular low-RMSE forecaster plus live-anchor classifier and physical-bin reserve rule is a valid alternative when only a state flag is needed, and we report it honestly: the Graph WaveNet+classifier-bin control costs 86.54M, which is lower than the boundary-router gate-bin at 95.13M because Graph WaveNet is the stronger forecaster, but it trails the same backbone's physical-bin reference (84.31M; Supplementary Table A10c). The in-model route is therefore not required to win the reserve leaderboard; its missing piece is trainable route responsibility attached to each forecast, same-run route-conditioned residual/reserve slicing, and a single deployment object whose version, calibration, and monitoring state can be audited together. The route-evolution audit adds the dynamic check: gate matching to the new regime peaks at the transition step (0.815) and drops under three- and six-step lead shifts (0.361 and 0.405; Supplementary Table A10b). The anchor-only router has lower overall RMSE (233.46) and slightly higher NMI/ARI (0.8895/0.9219), but worse pitch-control RMSE (317.81 versus 286.95) and far larger 0.5-std boundary-anchor-noise degradation (105.56 versus 5.78).

We report the operating trade-off explicitly. A model receives citable degraded-label gain only after its route passes the physical-routing audit; otherwise the accountability gain is set to zero, even for an accurate or routed-capacity model. Under this rule iTransformer is the zero-RMSE-price anchor without an audited operating-state route, Unconstrained MoE fails the route audit (NMI 0.014), and the train-only class-weight rerun is the single evidence source for the headline audit: RMSE 229.93, a six-step fair-degradation recall gain of +0.737, and the reserve diagnostics below, all drawn from the same five-seed provenance-corrected checkpoints. The logistic control is reported separately because it is a detector on live anchors, not a forecaster with routed attribution.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Early MPPT-to-pitch pitch-window detection under fair input degradation. Delay and noise degrade the gate's own anchor readings and the rule identically; mean $\pm$ sd over five train-only seeds. Availability rows degrade the confirming label stream only, which the gate does not consume at test time.}
\label{tab:early-warning}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.22\linewidth} >{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}X}
\toprule
Scenario & Setting & Gate & Rule & Gain \\
\midrule
Clean anchors & --- & 0.9705 $\pm$ 0.0299 & 1.000 & $-$0.029 \\
Delay (fair) & 1 step & 0.9622 $\pm$ 0.0306 & 0.655 & +0.307 \\
Delay (fair) & 3 steps & 0.9430 $\pm$ 0.0361 & 0.381 & +0.562 \\
Delay (fair) & 6 steps & 0.9327 $\pm$ 0.0429 & 0.196 & +0.737 \\
Noise (fair) & Wspd 0.5, Pab 1.0 & 0.9635 $\pm$ 0.0375 & 0.811 $\pm$ 0.016 & +0.152 \\
Noise (fair) & Wspd 1.0, Pab 2.0 & 0.9505 $\pm$ 0.0363 & 0.680 $\pm$ 0.019 & +0.271 \\
\midrule
Availability & 75\% labels & 0.971 & 0.744 & +0.227 \\
Availability & 50\% labels & 0.971 & 0.508 & +0.462 \\
Availability & 25\% labels & 0.971 & 0.242 & +0.729 \\
\bottomrule
\end{tabularx}
\end{table}
```

The training-level anchor-stress guard keeps the leakage boundary visible. In the clean train-only rerun, removing \texttt{Patv} or \texttt{Pab\_mean} leaves mean NMI at 0.881 and 0.878, while lagging \texttt{Patv} and lagging pitch/wind give 0.763 and 0.684. These older ablations are reported with the same strict-cache protocol but under a different auxiliary-weight configuration from the signature-gate probe in Table~\ref{tab:signature-gate}; the two probe families should not be numerically merged. The consistent finding is that the route is not a leakage artifact, but it remains a declared-anchor mechanism rather than anchor-free discovery.

![The WTB operating plane shows the main mechanism: after correction, the dominant routed responsibility changes around the rated-wind and pitch-control boundary instead of forming an arbitrary expert partition. The confusion matrices summarize the same recovery numerically.](artifacts/final_evidence_package/export/figures/figure4_routing_evidence.pdf){ width=62% }

## Boundary-Risk Vignette: Does the Gate Change Reserve Tradeoffs?

The reserve audit is a consequence check for the recovered route, evaluated as pre-dispatch imbalance risk screening and penalty avoidance margin rather than ISO central ancillary service dispatch. A validation-calibrated reserve screener is frozen and applied to later MPPT-to-pitch boundary cells, comparing global, physical-bin, and gate-bin quantile rules for Graph WaveNet and the boundary router.

At a shortage-to-reserve cost ratio of 10, gate-conditioned binning carries 1.95M more reserve than the same-router global rule, while shortage energy decreases by 16.9% (seed-paired mean difference -0.637M, CI [-0.976M, -0.300M]) and violation rate decreases by 1.45 percentage points (CI [-0.0220, -0.0073]). The same-model cost difference is -4.42M (CI [-7.36M, -1.27M]), and the parallel Physics-Aligned MoE family reproduces the direction (-4.26M, CI [-5.43M, -3.04M]). The physical-bin reference remains competitive, and the full-sample cross-backbone uncertainty interval crosses zero. The result therefore supports a conditional transition-window diagnostic, not reserve-policy superiority.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Boundary-window reserve diagnostic and validation-frozen quantile baselines at cost ratio 10, train-only class-weight checkpoints for both MoE families. Same-model gate-bin differences have seed-paired support; physical-bin and full-sample comparisons bound the claim.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.12\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Policy & Cost & Viol. & Reserve & Shortage & Reading \\
\midrule
Boundary/physical-bin & 93.82M & 0.1010 & --- & 3.697M & Best same-router physical-bin reference \\
GWN/physical-bin & 84.31M & 0.0931 & 50.35M & 3.40M & Low-RMSE backbone reference \\
Boundary/gate-bin & 95.13M & 0.1021 & --- & 3.767M & Gate diagnostic; same-model better than global \\
Boundary/global & 99.55M & 0.1167 & --- & 4.404M & Same-model global rule \\
Full-MoE/gate-bin & 91.62M & 0.0907 & --- & 3.328M & Physics-aligned family replicates direction \\
Full-MoE/global & 95.89M & 0.1014 & --- & 3.826M & Same-family global rule \\
GWN/global & 88.80M & 0.1022 & 50.32M & 3.85M & Global low-RMSE reference \\
\bottomrule
\end{tabularx}
\end{table}
```

The useful reserve window is moderate rather than universal: ratios 5--10 favor gate-bin screening, ratio 50 favors the same-model global rule, and Graph WaveNet/physical-bin remains close at 84.31M. The boundary-slice proxy falls from 99.55M to 95.13M, which Supplementary Table A12 translates into about 637 avoided MWh-equivalent shortage cells and a 442k illustrative reserve-cost-scale marker at 100 EUR/MWh. The engineering value is an auditable pre-dispatch screening and imbalance penalty avoidance margin near the control boundary, not centralized ISO ancillary service dispatch or market settlement value.

The modular-equivalence control quantifies what the in-model posterior adds on the same backbone. A validation-fit logistic classifier on issue-time anchors reproduces physical-bin reserve (16.190M versus 16.190M; seed-paired difference -68, CI [-112, -28]), beating the hard route (16.398M). The jointly-learned soft posterior reaches 16.065M, below the classifier by 125k (CI [-297k, +34k]) and below global by 568k (CI [-726k, -406k]; Supplementary Table A11c), with pinball gain 1.82 at $q{=}0.90$. The matched modular comparison in Table~\ref{tab:mechanism} localizes where this value comes from across seven architectures: an unrouted joint head prices at 16.076M (no detected difference from routed 16.065M), whereas a two-stage Cascaded Frozen MLP prices at 16.412M (trailing joint learning by 0.347M, CI [-0.385M, -0.052M]), and independent consequence models fail to price risk despite consequence awareness (Independent Consequence MLP at 17.340M, GBDT at 17.656M---1.28M to 1.59M worse than joint learning). This establishes that joint training with power residuals is indispensable for non-convex risk pricing, while the routing structure provides degradation resilience (recall 0.933 vs 0.286 under delay; 0.951 vs 0.724 under noise). Continuous pitch quantile achieves the lowest clean baseline (15.538M, degrading to 16.048M under delay). In pitch-sparse plants (e.g. Kelmarsh with 55\% pitch coverage), physical quantiles fail on >40\% of turbines, where the joint posterior restores risk awareness from electromechanical signatures. Computationally, the model has only 110k parameters (430 KB) and executes 134-turbine inference in 4.12 ms on a central substation workstation (<25 ms on an industrial PC CPU), consuming <1 kWh/year (<£220/year total plant OPEX, <£1.63/turbine/year), ruling out edge GPU hardware overhead.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.80}
\caption{Matched modular comparison: where the boundary-risk posterior's value comes from. Reserve costs are validation-frozen boundary-band totals at $\rho{=}10$ (mean over five seeds); degraded recall is early-window recall under a six-step confirming-stream delay applied identically to every detector.}
\label{tab:mechanism}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.36\columnwidth} >{\centering\arraybackslash}p{0.10\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}X}
\toprule
Pricing / detection method & Jointly trained & Channels & Reserve cost & Degraded recall \\
\midrule
Continuous pitch quantile (soft-pab) & no & physical & 15.538M & --$^{\dagger}$ \\
Threshold rule (physical-bin) & no & physical & 16.190M & 0.196 \\
Independent logistic classifier & no & physical & 16.190M & 0.885 (noise) \\
Cascaded Frozen MLP & partial & conseq. & 16.412M & 0.785 \\
Independent Consequence MLP & no & conseq. & 17.340M & 0.854 \\
Independent GBDT posterior & no & conseq. & 17.656M & 0.868 \\
Joint non-routed posterior head & yes & weak & 16.076M & 0.286 \\
Joint routed posterior (this work) & yes & weak & 16.065M & 0.933 \\
\midrule
Global quantile & -- & -- & 16.632M & 0.196 \\
\midrule
\multicolumn{5}{p{0.96\linewidth}}{\scriptsize $^{\dagger}$Soft-pab is a continuous quantile pricing rule; under clean telemetry it is the optimal baseline (15.538M), degrading to 16.048M under delay. In pitch-sparse plants (e.g. Kelmarsh with 55\% pitch coverage), physical pitch quantiles are missing on >40\% of turbines, where the joint posterior provides defense-in-depth.} \\
\bottomrule
\end{tabularx}
\end{table}
```

The same posterior stratifies forecast risk inside rule classes: on boundary rule-MPPT cells, gate pitch probability correlates with future power residual (Spearman 0.183, 95% CI [0.123, 0.227]), and routing margin correlates at 0.391 (CI [0.299, 0.482]). Disagreement is disclosed honestly: gate and rule disagree on 16.9% of cells, where the rule conditional mean fits better (MAE difference 753 kW; gate better on 5.3%, CI [3.0%, 7.7%]). The decision value therefore lives in the soft posterior, not in the hard route.

Crucially, to verify reserve benefits survive spatial smoothing, we evaluate aggregate power at the Point of Common Coupling (PCC) bus ($P_{\mathrm{farm}} = \sum_{i=1}^{134} P_i$). Across the full operational envelope, joint posterior aggregate quantile pricing reduces reserve cost by $-11.22\text{M kWh}$ (95\% bootstrap CI $[-21.55\text{M}, -2.85\text{M}]$, strictly excluding zero) against global PCC quantiles and by $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) against Gaussian parametric sizing; in transitional regimes (10\%--90\% pitching), it saves $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) over continuous physical pitch, confirming economic value after fleet-wide error cancellation.


# Discussion

## Accuracy, accountability and deployment gates

The accuracy cost is not secondary: iTransformer, Graph WaveNet, and lag baselines remain superior whole-sample forecasters on WTB; the routed model should pair with an established low-RMSE forecaster when aggregate accuracy is paramount. Its targeted role is an accountable operating-state diagnostic for boundary-specific decisions. External testing is graded: La Haute Borne demonstrates anchor-observable replication (canonical NMI 0.975; withheld probe 0.674/0.575). On Kelmarsh (55\% pitch) the probe reaches 0.340/0.378, and on Penmanshiel (78\%) 0.302 (`signature_core` 0.195, far above permuted controls; Supplementary Table A9d). Partial pitch observability modulates rather than eliminates boundary recoverability.

Crucially, external walk-forward rolling evaluation establishes empirical physical boundary conditions for the pre-registered admission protocol (Supplementary Table A14). On ENGIE La Haute Borne (4 turbines, 99\% complete pitch), walk-forward pooled quarterly evaluation (Q1--Q3) incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus continuous physical pitch (Supplementary Table A11h). This reveals quantile variance amplification under acute seasonal drift: on a miniature 4-turbine site without Point of Common Coupling (PCC) spatial portfolio smoothing, short quarterly slices suffer variance spikes during autumn regime shifts (+968.1k kWh in Q3, while Q1--Q2 cross zero). Expanding calibration to a 180-day annual window compresses the cost gap to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero), bounding soft-posterior reserves to PCC-smoothed plants and degraded/pitch-sparse telemetry.

To evaluate durability against decadal wear and multi-year climate cycles without online retraining, we formalize "Quantile Recalibration under Frozen Backbone". Across two European wind farms spanning 17.6 cumulative operating years (Kelmarsh, 9 years, 2016--2024, 6 MM92 turbines; Penmanshiel, 8.6 years, 2016--2024, 15 MM82 turbines), neural backbones are frozen at commissioning while reserve quantiles update via two-year sliding windows. While a static freeze suffers decadal drift (crossing zero with losses of $-2.24\text{M}$ and $-13.83\text{M}$), rolling recalibration recovers 0.804M kWh (804,000 kWh) of annual drift loss per site. In full-sample testing across all 13 chronological rolling folds (retaining Penmanshiel Fold 1), 12 out of 13 folds show negative cost deltas (savings), achieving exact binomial sign test significance $p = 0.00171$ ($p < 0.002$). In seed-paired bootstrap CIs: Kelmarsh cumulative walk-forward pooled savings reach $-6.19\text{M kWh}$ (95\% bootstrap CI $[-7.52\text{M}, -4.77\text{M}]$, strictly excluding zero; $-2.67\text{M}$ vs physical pitch); Penmanshiel mature operational folds (Folds 3--6) all strictly exclude zero, pooling $-4.34\text{M kWh}$ (CI $[-8.24\text{M}, -0.44\text{M}]$, strictly excluding zero; $-5.85\text{M}$ vs physical pitch; Supplementary Table A11g). Across both farms, 10 out of 11 mature annual folds strictly exclude zero.

Furthermore, evaluating across shortage penalty ratios $\rho \in \{5, 10, 20\}$ articulates an operational envelope ("Telemetry Availability $\times$ Penalty Ladder"). At $\rho=10$, the soft gate dominates on both commercial farms. At $\rho=20$, asymmetry emerges: at Kelmarsh (55\% pitch), physical rules recover and surpass soft-gate pricing by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); at Penmanshiel (78\% pitch), the soft gate leads physical rules by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) while crossing zero versus the unconditioned global baseline ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$). Direct reserve deployment at new farms requires pitch or proxy observability, boundary support, compatible geometry, local recalibration, and a held-out routing pass (cross-farm held-out NMI reaches 0.557; Supplementary Table A14) [@tautzweinert2017scada].

# Limitations

WTB pseudo-labels derive from wind speed and pitch angle, channels present in full gate anchors. Withheld-channel probes prove the boundary survives without them via consequence signatures across four farms (permuted controls at chance). Removing pitch dispersion retains non-power NMI 0.309 on WTB and 0.578 on La Haute Borne, confirming dispersion does not carry the signal. Yet routing remains an anchor-constrained diagnostic rather than anchor-free discovery [@karniadakis2021piml; @zehtabiyan2023physicsguided]. Inputs may contain history $\texttt{Patv}_{t-H+1:t}$ and issue-time $\texttt{Patv}_{t}$, while targets begin at $t+1$. Expert semantics reflect the declared mapping; unassigned logits are not universal physical states. Comparisons are bounded to empirical-quantile screening, excluding optimal power flow, unit commitment, and market settlement [@bremnes2004quantile; @zhou2013probabilisticmarkets]. Strongest claims remain five-seed WTB recovery, mechanism intervention, La Haute Borne replication, and same-router reserve triage.

# Conclusion

This study evaluated a jointly-learned boundary-risk posterior for wind-turbine reserve screening near the MPPT-to-pitch boundary, and localized its value with counterfactual controls. Evidence is consistent with shared representation via joint learning driving reserve risk pricing: the joint posterior beats the global quantile by 0.57M and an independent GBDT posterior by 1.6M, while a continuous physical pitch quantile remains the honest clean-observation baseline (15.538M). The routing structure provides degradation resilience: the routed posterior keeps 0.933 early-window recall at a six-step confirming-stream delay against 0.196 for the rule and 0.286 for a non-routed posterior head within a Controlled Engineering Stress-Test Envelope. The boundary stays identifiable when label-defining channels are withheld (NMI 0.561, chance under permuted labels), and this consequence signature persists across external farms under heterogeneous observability (La Haute Borne, Penmanshiel, and Kelmarsh with 99\%, 78\%, and 55\% pitch coverage) with negative controls everywhere, reflecting graded recoverability rather than a simplistic coverage law. Across 17.6 cumulative operating years on Kelmarsh and Penmanshiel, Quantile Recalibration under Frozen Backbone eliminates multi-year concept drift, yielding 12 out of 13 rolling folds with cost savings ($p = 0.00171$ under exact binomial sign test; 10 mature folds strictly excluding zero in seed bootstrap intervals, saving $-1.03\text{M}$ and $-2.03\text{M kWh/yr}$). The clean-anchor rule and a simple classifier remain stronger clean detectors. The resulting system is an auditable defense-in-depth screening layer whose use depends on a graded signature-strength check and a held-out local pass, providing robust reserve triage when telemetry degrades without attempting to displace low-RMSE point forecasting or market dispatch.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.

# Code and data availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public (raw third-party data not redistributed). Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress caches, early-warning label degradation, classifier control, class-weight sensitivity, external diagnostics, and evidence-freeze protocols across declared seeds. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.


# References {.unnumbered}

::: {#refs}
:::

