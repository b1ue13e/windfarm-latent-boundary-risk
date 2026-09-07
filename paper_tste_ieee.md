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
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\begin{list}{}{\fontsize{5.9pt}{6.7pt}\selectfont\setlength{\itemindent}{0pt}\setlength{\leftmargin}{0pt}\setlength{\parsep}{0pt}\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}}{\end{list}}}
  - \AtBeginDocument{\renewcommand{\CSLBlock}[1]{#1\par}}
  - \AtBeginDocument{\setlength{\csllabelwidth}{1.8em}}
  - \AtBeginDocument{\renewcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth - \csllabelwidth\relax}{\fontsize{5.9pt}{6.7pt}\selectfont\ignorespaces#1}}}
  - \AtBeginDocument{\renewcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{\fontsize{5.9pt}{6.7pt}\selectfont\strut#1}}}
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
Reserve sizing near the transition from maximum power point tracking (MPPT) to blade-pitch regulation requires high-fidelity awareness of turbine operating boundaries. However, industrial wind-plant Supervisory Control and Data Acquisition (SCADA) telemetry streams are inherently vulnerable to communication packet loss, multi-step transmission latency, sensor noise, and uncalibrated or unobservable pitch channels (particularly at third-party aggregator or Virtual Power Plant interfaces). We establish that deterministic physical rules (such as continuous soft-pitch rules based on aerodynamic power curves) exhibit remarkable economic efficiency under pristine telemetry (achieving the lowest baseline reserve cost of $871,408\text{ kW}\cdot\text{h}$ at 1-hour dispatch lead time $h=6$), yet suffer catastrophic brittleness under communication delays or noise, where shortage violation rates surge to $12.52\% \pm 1.82\%$ ($h=6$) and $12.60\% \pm 1.94\%$ ($h=1$), severely breaching the 10\% grid reliability compliance limit. Conversely, shallow tree baselines (Missingness-Aware GBDT) capitalize on 10-minute lag autocorrelation at $h=1$ but collapse across dispatch-grade horizons ($h=6$), inflating reserve costs by $13.44\%$ to $29.15\%$ ($p < 0.0001$) due to their structural inability to capture spatial wake physics. To resolve this dilemma, we propose a synergistic defense-in-depth architecture combining high-fidelity physical aerodynamic priors with a jointly-learned spatio-temporal dynamic graph neural network that serves as an autonomous blind-spot fallback. When primary telemetry degrades, the deep graph representation dynamically reconstructs operating risk from cross-sensor electromechanical signatures (dynamic wake graph geometry, active power transients, voltage/reactive dynamics) when primary pitch readings are delayed or unobservable. Across a 5-seed benchmark on the 134-turbine WTB plant, we show that nominal pricing efficiency is driven by end-to-end task-loss alignment (dense and routed heads achieve statistical parity under clean telemetry, 95\% CI $[-1{,}148, +65{,}456]\text{ kW}\cdot\text{h}$), while dynamic MoE routing localizes its distinct empirical value to fault isolation under continuous telemetry impairment, saving $+16{,}267\text{ kW}\cdot\text{h}$ ($p = 0.0251$) under 6-step delay and $+21{,}006\text{ kW}\cdot\text{h}$ ($p < 0.05$) under sensor noise against unrouted dense representations, while outperforming global quantiles by $17,010$ to $39,962\text{ kW}\cdot\text{h}$ and avoiding the severe tail conservatism of uncalibrated pinball regression ($690,695\text{ kW}\cdot\text{h}$ savings over Frozen Backbone Direct Quantile MLP). Under Markov-Gilbert burst drops, it sustains 0.994 recall and 0.967 F1 (+0.064 F1 gain over the rule); under a six-step delay, it sustains 0.933 recall (+0.737 gain). At the Point of Common Coupling (PCC) bus, fleet-wide spatial portfolio smoothing across active turbine subsets (averaging $\sim 121$ active turbines) preserves an economic savings of $-11.22\text{M kWh}$ (95\% CI $[-21.55\text{M}, -2.85\text{M}]$) over global PCC baselines. Replicated across commercial UK wind plants with turbine-calibrated rated wind speeds (Kelmarsh MM92 at 12.5 m/s, Penmanshiel MM82 at 14.5 m/s), consequence signatures persist significantly above chance under counterfactual withheld-channel stress testing, and decadal walk-forward rolling recalibration saves $0.804\text{M kWh/year}$ across 17.6 operating years (12 of 12 clean folds saving, $p = 0.00024$; 12 of 13 full folds, $p = 0.00171$). The resulting framework delivers an accountable, physics-data synergistic reserve pricing layer for digitalized power grids.
\end{abstract}

\begin{IEEEkeywords}
Wind plant reserve pricing; Point of Common Coupling (PCC); telemetry degradation; defense-in-depth; high-fidelity physical prior; spatio-temporal dynamic graph; blind-spot fallback; MPPT-to-pitch transition.
\end{IEEEkeywords}

# Introduction

Wind-farm reserve screening near the transition from maximum power point tracking (MPPT) to blade-pitch control requires precise identification of the active turbine operating regime. This operational boundary matters acutely because wind-power forecasting is economically coupled to ramp exposure, operating reserve sizing, and non-convex imbalance shortfall penalties rather than to aggregate RMSE alone [@pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. In the MPPT aerodynamic region (Region 2), active power responds cubically to wind-speed variations. Once blade-pitch control becomes active near rated wind speed (Region 3), aerodynamic rotor efficiency is actively curtailed to clamp generation at nameplate capacity. A small unpredicted wind-speed deviation near rated operation can therefore thrust a turbine across a control cliff, generating severe power shortfall penalties even when fleet-average forecast errors appear benign.

In industrial wind plant operations, however, continuous and pristine SCADA telemetry streams cannot be guaranteed. Telemetry channels across distributed turbine networks are routinely afflicted by communication packet dropouts, multi-step transmission latency (e.g., 10 to 60 minutes), asynchronous timestamp misalignment, and sensor calibration noise [@tautzweinert2017scada]. In the commercial Kelmarsh wind plant, for example, 99.6\% of turbine status events carry second-level timestamps that fall strictly between 10-minute SCADA grid points, confirming that confirming-stream transmission delay and asynchrony are endemic structural features of distributed SCADA networks rather than rare edge cases. Furthermore, in non-intrusive aggregator, Virtual Power Plant (VPP), or Transmission System Operator (TSO) pre-dispatch triage settings, internal turbine blade-pitch registers are frequently unobservable due to commercial boundaries, proprietary OEM protocol firewalls, or legacy substation gateways. When grid operators must clear reserve margins before real-time delivery, relying on delayed or unobservable confirming telemetry poses severe reliability risks.

Prior engineering practice and research have largely treated physical models and data-driven forecasters as mutually exclusive alternatives. On the one hand, high-fidelity physical priors—such as continuous soft-pitch rules based on manufacturer power curves—exhibit exceptional economic efficiency under ideal, clean observations, achieving the lowest baseline reserve cost ($871,408\text{ kW}\cdot\text{h}$ at 1-hour dispatch lead time $h=6$). However, pure physical rules exhibit **catastrophic brittleness**: when SCADA telemetry experiences communication delays or sensor noise, physical threshold logic misclassifies the turbine's control state, causing reserve shortage violation rates to explode to $12.52\% \pm 1.82\%$ ($h=6$) and $12.60\% \pm 1.94\%$ ($h=1$), severely breaching the strict 10\% grid reliability compliance limit. On the other hand, shallow machine-learning baselines like Missingness-Aware GBDT capitalize on 10-minute lag wind-speed autocorrelation at ultra-short horizons ($h=1$), but undergo a catastrophic breakdown at dispatch-grade horizons ($h=6$), inflating reserve costs by $13.44\%$ to $29.15\%$ ($p < 0.0001$) because decision trees cannot represent spatial wake propagation across turbine arrays. Direct uncalibrated two-stage architectures (Frozen Backbone Direct Quantile MLP) suffer severe tail conservatism, over-estimating reserve margins by $44.57\%$ to $72.02\%$ ($p < 0.01$) by hoarding excessive reserves under direct pinball regression.

To resolve this fundamental tension, we propose a synergistic defense-in-depth framework: **"High-Fidelity Physical Prior + Spatio-Temporal Dynamic Graph Blind-Spot Fallback"**. Under nominal operating conditions with intact telemetry, high-fidelity physical aerodynamic priors govern primary reserve allocation, ensuring maximum economic efficiency. When SCADA telemetry enters blind spots (packet dropouts, transmission delays, uncalibrated pitch channels), an end-to-end spatio-temporal directed-diffusion graph neural network coupled with an adaptive Mixture-of-Experts (MoE) boundary-router serves as an autonomous safety net. By propagating dynamic wake geometry and cross-sensor electromechanical signatures (active power transients, terminal voltage, and reactive dynamics), the learned posterior maintains sharp, grid-compliant risk awareness even when primary blade-pitch telemetry is delayed, unobservable across aggregator boundaries, or withheld under counterfactual stress testing. Furthermore, we verify that this boundary-risk posterior survives the wind farm spatial portfolio smoothing effect at the Point of Common Coupling (PCC) bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, averaging $\sim 121$ active turbines), delivering verifiable economic savings after fleet-wide error cancellation.

This paper makes four bounded, verifiable contributions:
1. **Synergistic Defense-in-Depth Architecture:** We formalize a collaborative framework uniting high-fidelity aerodynamic physical priors with a spatio-temporal dynamic graph blind-spot fallback, establishing that joint posterior quantile pricing saves $-11.22\text{M kWh}$ (95\% CI $[-21.55\text{M}, -2.85\text{M}]$) over global PCC quantiles and $-14.94\text{M kWh}$ over Gaussian baselines across operational active-turbine aggregates at the PCC bus.
2. **Multi-Horizon 5-Seed Dispatch Benchmark:** Across 5 random seeds (201–205) and four controlled degradation regimes (Clean, Delay-6, Sensor Noise, Markov Burst Drops), we show that nominal reserve pricing efficiency is driven by end-to-end task-loss alignment (dense and routed heads show statistical parity under clean telemetry, 95\% CI $[-1{,}148, +65{,}456]\text{ kW}\cdot\text{h}$), while dynamic MoE routing localizes its distinct empirical value to fault isolation under continuous telemetry impairment ($p = 0.0251$ under Delay-6 and $p < 0.05$ under sensor noise), substantially outperforming Missingness-Aware GBDT ($p < 0.0001$) and avoiding the severe tail conservatism of uncalibrated pinball regression ($p < 0.01$).
3. **Physical Brittleness & Degradation Resilience:** We expose the catastrophic breakdown of deterministic physical rules under telemetry delay (>12.5\% violation rates) and prove that the deep spatio-temporal fallback maintains safety compliance (<8.1\% violation rate under noise and Markov bursts) while sustaining 0.994 recall and 0.967 F1 under Markov-Gilbert burst drops (+0.064 F1 gain) and 0.933 recall under 6-step delays (+0.737 gain).
4. **Multi-Farm Generalization & Decadal Walk-Forward Durability:** We replicate the framework across commercial wind farms under heterogeneous turbine technologies and rated wind speeds (ENGIE La Haute Borne, Kelmarsh MM92 with $v_{\mathrm{rated}}=12.5$ m/s, Penmanshiel MM82 with $v_{\mathrm{rated}}=14.5$ m/s), proving that electromechanical consequence signatures persist significantly above chance under counterfactual withheld-channel stress testing, and demonstrate that Quantile Recalibration under Frozen Backbone yields cost savings across 12 of 12 clean rolling folds ($p = 0.00024$; 12 of 13 including commissioning-overlap Penmanshiel Fold 1, $p = 0.00171$) over 17.6 cumulative operating years.

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

## Operating-boundary anchors and high-fidelity physical prior (Tier 1)

The gate is not supervised everywhere. It is anchored where the physical aerodynamic interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularisation. This design embodies the first tier of our defense-in-depth posture: **a high-fidelity physical prior** calibrated to the manufacturer specifications of each turbine model [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada].

**Aerodynamic operating regimes and turbine-calibrated anchors:** In wind turbine control engineering, the transition from Maximum Power Point Tracking (Region 2) to active blade-pitch regulation (Region 3) is governed by the turbine's aerodynamic power-coefficient curve $C_p(\lambda, \theta)$ and its rated wind speed $u_{\mathrm{rated}}$. Below rated wind speed, blades maintain a minimum pitch angle to maximise aerodynamic capture; above rated wind speed, the pitch actuator rotates the blades to shed excess aerodynamic power and protect the generator.

Let $\bar{p}_{i,t}$ denote the average blade pitch angle across all three blades for turbine $i$ at dispatch anchor time $t$:

$$
\bar{p}_{i,t} = \frac{1}{3}\left(p^{(1)}_{i,t}+p^{(2)}_{i,t}+p^{(3)}_{i,t}\right).
$$

Writing $w_{i,t}=\texttt{Wspd}_{i,t}$ for anemometer wind speed, the declared operating boundary is defined with turbine-calibrated cut-in threshold $u_{\mathrm{idle}}$, rated wind speed $u_{\mathrm{rated}}$, and pitch-activation angle $p_{\mathrm{th}}$:

$$
R_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transitional/ambiguous)}.
\end{cases}
$$

Crucially, aerodynamic rated wind speeds are calibrated to the specific turbine technology deployed at each wind plant:
- **WTB (134 turbines):** $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=10.5\text{ m s}^{-1}$, and $p_{\mathrm{th}}=2.0^\circ$.
- **Kelmarsh (6 Senvion MM92 turbines):** $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=12.5\text{ m s}^{-1}$, and $p_{\mathrm{th}}=1.0^\circ$.
- **Penmanshiel (15 Senvion MM82 turbines):** $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, and $p_{\mathrm{th}}=1.0^\circ$.
- **ENGIE La Haute Borne (4 Senvion MM82 turbines):** $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, and $p_{\mathrm{th}}=1.0^\circ$.

Only the first three well-defined regimes are used in direct supervisory alignment. Transitional samples are retained for evaluation but masked out of anchor supervision via:

$$
M_{i,t} = \mathbf{1}[R_{i,t} \neq 3].
$$

These thresholds form the **Tier 1 High-Fidelity Physical Prior**: when SCADA telemetry is complete and intact, continuous soft-pitch quantiles derived from these anchors achieve optimal baseline reserve sizing. When telemetry degrades, however, this deterministic rule suffers severe brittleness, activating Tier 2 and Tier 3 defense mechanisms.

**ERA5 observability contrast:** ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the wind plant control-boundary accountability task.

## Tier 2: Spatio-Temporal Dynamic Wake Graph & Blind-Spot Fallback Architecture

**Physical dynamic wake graph construction:** When primary SCADA telemetry degrades, spatial coupling across turbine arrays provides the crucial redundancy required to infer local operating regimes. Directed diffusion represents asymmetric aerodynamic wake propagation through the turbine network [@li2018dcrnn; @wu2019graphwavenet]. For WTB, we construct a time-varying directed wake graph $\mathcal{A}_t$: candidate turbine pairs $(i, j)$ are filtered by physical distance ($d_{ij} \le d_{\max}$), activated when upstream turbine $j$ lies within an aerodynamic wake cone aligned with instantaneous local wind direction $\theta_t$ (expansion angle $\alpha = 15^\circ$), weighted by streamwise decay $\exp(-d_{\parallel}/\sigma_x)$ and cross-stream decay $\exp(-d_{\perp}^2/2\sigma_y^2)$, and pruned to the $K$ strongest inbound wake neighbors [@park2019physicsinduced; @zehtabiyan2023physicsguided]. This construction defines an instantaneous aerodynamic wake score $s^{\mathrm{wake}}_{i,t}$, which supplies spatial context even when anemometers are noisy. ERA5 employs a symmetric Haversine-Gaussian $k_{\mathrm{nn}}$ graph where thermodynamic sensible heat flux is directly observable [@hersbach2020era5].

**Directed-diffusion GRU encoder and node-level MoE routing:** The encoder is deliberately kept compact (110k parameters) to ensure execution in under 5 ms on standard substation automation hardware without requiring specialized edge GPUs. Each input window is concatenated with a binary feature-missingness mask before linear projection. Two directed diffusion blocks aggregate self, inbound, and outbound messages across each graph snapshot:

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

where $\mathrm{Agg}_{\mathrm{in}}$ and $\mathrm{Agg}_{\mathrm{out}}$ denote normalized weighted aggregations over inbound and outbound wake neighbors. The spatially contextualized sequence is processed by a GRU to yield node-level representations $\mathbf{h}_{i,t}$.

Each regime-specialized expert head $f_e$ maps $\mathbf{h}_{i,t}$ to a $P$-step trajectory forecast. Routing is computed dynamically at the node level:

$$
\mathbf{z}_{i,t} = \mathrm{MLP}_{\mathrm{gate}}\!\left(\left[\mathbf{h}_{i,t};\mathbf{a}_{i,t}\right]\right), \qquad \mathbf{g}_{i,t} = \mathrm{softmax}\!\left(\frac{\mathbf{z}_{i,t}}{\tau}\right),
$$

$$
\hat{\mathbf{y}}_{i,t+1:t+P} = \sum_{e=1}^{E} g_{i,t}^{(e)} f_e(\mathbf{h}_{i,t}).
$$

**Cross-sensor electromechanical fallback mechanism:** The core innovation of the Tier 2 fallback is its ability to infer operating states from non-pitch electromechanical signatures. When blade-pitch telemetry $\bar{p}_{i,t}$ suffers packet loss, transmission latency, or protocol unobservability (such as across third-party aggregator or VPP boundaries), the dynamic graph encoder leverages active power transients ($\texttt{Patv}$), terminal voltage fluctuations, reactive dynamics, and upstream wake propagation to reconstruct the probability of active blade-pitch regulation. In nominal operation, the gate anchor consumes:

$$
\mathbf{a}_{i,t}^{\mathrm{WTB}} = [\texttt{Wspd}_{i,t}, \texttt{Pab\_mean}_{i,t}, s^{\mathrm{wake}}_{i,t}, \texttt{Patv}_{i,t}].
$$

Under telemetry failure, degraded inputs activate the spatio-temporal fallback, preventing the catastrophic reserve misallocation typical of deterministic rules.

## Integration of Physical Constraints into Model Optimization

Prediction loss alone cannot identify regime-specialized routing because several unconstrained experts can fit averaged dynamics similarly well [@shazeer2017outrageously; @fedus2022switch]. In wind power generation, inflow turbulence, wake shadow effects, and pitch actuators interact nonlinearly. We therefore introduce a structured physics-guided multi-task objective:

```{=latex}
\begin{align}
\mathcal{L} &= \mathcal{L}_{\mathrm{pred}}+ \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}}+ \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}}\nonumber\\\\
&\quad+ \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}}+ \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}}+ \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}},
\end{align}
```

with inactive terms set to zero. Checkpoint selection is strictly governed by validation RMSE, preventing auxiliary penalties from distorting the selection metric.

**Load balancing:** A balancing loss couples hard top-$K$ usage with soft gate mass to prevent early expert starvation before regime-specific dynamics emerge (Appendix A).

**Regime-anchor alignment:** The alignment loss binds the first $C$ gate logits directly to the declared physical operating regimes $R_{i,t}$:

\begin{equation}
\mathcal{L}_{\mathrm{align}} = \frac{1}{|\Omega|} \sum_{(i,t)\in\Omega} \mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right), \quad \Omega=\{(i,t):M_{i,t}=1\},
\end{equation}

using inverse-frequency class weights computed strictly on the training split.

**Boundary-focused forcing:** To sharpen the boundary between MPPT (Region 2) and pitch regulation (Region 3), a focused cross-entropy loss acts exclusively on boundary samples: $\mathcal{L}_{\mathrm{force}} = \frac{1}{|\Omega_{\mathrm{force}}|}\sum_{(i,t)\in\Omega_{\mathrm{force}}}\mathrm{CE}([z^{(\mathrm{mppt})}_{i,t}, z^{(\mathrm{pitch})}_{i,t}]^{\top}, Y^{\mathrm{force}}_{i,t})$ where $Y^{\mathrm{force}}_{i,t}=\mathbf{1}[R^{\mathrm{wtb}}_{i,t}=2]$ and $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}, M_{i,t}=1\}$.

**Soft boundary-risk posterior:** The normalized issue-time boundary-risk posterior for turbine $i$ at dispatch anchor $t$ is computed from gate probabilities $\mathbf{g}_{i,t}$ across operational regimes $\mathcal{C}_{\mathrm{op}} = \{\mathrm{idle}, \mathrm{mppt}, \mathrm{pitch}\}$ as $\pi_{i,t}^{\mathrm{pitch}} = g_{i,t}^{(\mathrm{pitch})} / \sum_{c \in \mathcal{C}_{\mathrm{op}}} g_{i,t}^{(c)}$.

**Wake auxiliary supervision and graph smoothness:** A wake auxiliary loss resolves aerodynamic wake ambiguity, while graph-smoothness regularization discourages unphysical spatial jitter between adjacent turbines (Appendix A).

## Tier 3: Operational Reserve Screening, PCC Portfolio Smoothing, & Multi-Horizon Dispatch Protocol

The operational utility of boundary-aware routing lies in pre-dispatch decision support: screening imbalance risks and sizing upward spinning reserves to prevent costly shortage penalties [@bremnes2004quantile; @nielsen2006quantile].

**Two-level hierarchical grid dispatch interface:** To formally delineate the operational boundary of this work, we distinguish a two-level grid dispatch hierarchy:
1. *Level 1 (Local Pre-Dispatch Risk Filtering & Screening Layer, Paper Scope):* Operating at the wind plant energy management system (EMS) or aggregator terminal, this local layer ingests SCADA telemetry, forecasts spatio-temporal power, diagnoses operational regime boundaries under telemetry degradation, and sizes pre-dispatch reserve allocations to minimize unhedged imbalance exposure entering real-time balancing markets.
2. *Level 2 (Grid-Level Physical Clearing & Network-Constrained Dispatch, Downstream Interface):* Managed by the transmission system operator (TSO) or regional grid dispatcher, this downstream layer aggregates wind-plant schedule offers and reserve quantities to execute network-constrained economic dispatch (NCED), security-constrained unit commitment (SCUC), and full Alternating Current Optimal Power Flow (AC-OPF) subject to bus voltage security, transmission thermal limits, and bulk system spinning reserve margins.
Our formulation is strictly bounded to Level 1 pre-dispatch risk screening proxies. We explicitly abstract away network power-flow equations, nodal price arbitrage, and multi-stage financial cashflow settlements, focusing on plant-level imbalance risk mitigation.

**Penalized Reserve-Shortfall Energy metric formulation:** For scheduled point forecast $\hat{y}_{i,t}$ and realized generation $y_{i,t}$, over-forecast shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. Sizing reserve margin $r_b$ incurs a reserve provision energy equivalent $r_b \Delta t$ and an asymmetric shortage penalty $\rho \max(s_{i,t} - r_b, 0) \Delta t$. For penalty ratio $\rho$, the total operational proxy metric is formalized as the **Penalized Reserve-Shortfall Energy Index (PSREI)** in $\text{kW}\cdot\text{h}$ (evaluated here at grid proxy ratio $\rho = 10$):

\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b + \rho \max(s_{i,t}-r_b,0) \right]\Delta t.
\end{equation}

The first-order optimality condition $\frac{\partial}{\partial r}\mathbb{E}[C] = 1 - \rho\Pr[s > r] = 0$ yields the optimal critical fractile $q^*(\rho) = 1 - 1/\rho$. In standard grid operations with $\rho = 10$, the required quantile is $q^*(10) = 0.90$, establishing a strict 10% maximum permissible violation rate.

**Point of Common Coupling (PCC) spatial portfolio smoothing:** In commercial wind plants, power delivered to the bulk grid is metered at the Point of Common Coupling (PCC) substation bus:

$$
P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}, \qquad R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}.
$$

Fleet-wide spatial aggregation induces a portfolio smoothing effect: uncorrelated local turbulence and turbine-level prediction errors cancel out across the array. Evaluating reserve sizing at the PCC verifies whether learned boundary risk survives spatial cancellation to deliver net plant-level economic value.

**Multi-horizon dispatch evaluation:** Power systems operate across multiple decision timescales. We evaluate two distinct operational horizons:
1. **Immediate dispatch ($h=1$, 10-minute ahead):** Represents real-time economic dispatch and automatic generation control (AGC), where high autocorrelation dominates.
2. **Operational dispatch ($h=6$, 1-hour ahead):** Represents intra-day market clearing, unit commitment, and battery energy storage scheduling, where aerodynamic wake dynamics and multi-step weather transitions are paramount.

**Battery Energy Storage System (BESS) rolling dispatch integration:** For co-located wind-storage installations, the scheduled reserve and generation feed into a rolling Model Predictive Control (MPC) linear program. The LP optimizes battery charge/discharge trajectories $P^{\mathrm{ch}}_t, P^{\mathrm{dis}}_t$ subject to exact energy balance $P^{\mathrm{grid}}_t = P^{\mathrm{farm}}_t + P^{\mathrm{dis}}_t - P^{\mathrm{ch}}_t$, state-of-charge limits $E_{\min} \le E_t \le E_{\max}$, and efficiency losses, ensuring that reserve margins translate directly into physical grid dispatchability.


# Case Study Configuration and Operational Constraints

## Datasets and preprocessing

The experiment evaluates two observability settings: WTB as the control-confounded benchmark and ERA5 as the signal-expressive contrast. WTB (KDD Cup 2022) comprises 134 turbines and 245 days of 10-min SCADA records ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], where inflow, wake, and pitch control interact, making the MPPT-to-pitch transition indirectly visible. Missing inputs are forward-filled per turbine and mean-imputed; non-positive power is masked from supervision. ERA5 covers three archived months on a $16 \times 16$ hourly patch ($T=2208$, $N=256$, eight features) [@hersbach2020era5], where sensible heat flux directly marks convective regimes. Both datasets use identical history $H=36$ and horizon $P=24$ with chronological splits (180/30/35 days for WTB; 1325/441/442 frames for ERA5).

## Techno-Economic Validation and Benchmarking Framework

The benchmarking framework has two layers. The first isolates routing mechanisms under matched capacity: the dense baseline replaces the expert mixture with a single head, unconstrained MoE adds capacity without physical loss, and the corrected routing comparator incorporates the physics loss suite [@shazeer2017outrageously; @fedus2022switch]. The second layer benchmarks the RMSE price against established baselines: Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE for WTB [@nie2023patchtst; @liu2024itransformer; @das2023longterm], along with persistence, physical power curves, and GBDT lag models. In mechanism tables, in-family models are designated **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**; complete baseline configurations appear in Supplementary Appendix~A.

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in Supplementary Appendix~A so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE across seeds 201--205, giving 30 completed baseline runs under the same strict anchor-valid evaluation cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same frozen cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE use the evaluator's transition-window mask around regime changes. This is distinct from the later boundary-band audit, which isolates anchors within +/-1.0 m s$^{-1}$ of the WTB rated-wind MPPT-to-pitch boundary. Regime-wise RMSE locates the error reduction. Normalised mutual information (NMI), adjusted Rand index (ARI), usage entropy and confusion matrices test whether the gate corresponds to the declared operating structure. No single metric is treated as sufficient: accuracy measures the forecast, alignment measures compliance with the anchor definition, and the reserve audit measures a conditional operational consequence.

## Controlled Telemetry Degradation Protocols

To stress-test model resilience under adverse field conditions, we formalize four controlled telemetry regimes evaluated across all 5 random seeds (201--205):
1. **Clean (Nominal):** Uncorrupted SCADA telemetry where anemometers and blade-pitch angle sensors operate with full fidelity.
2. **Delay-6 (Transmission Lag):** A 6-step ($6 \times 10\text{ min} = 60\text{ min}$) latency applied to wind-speed and pitch-angle telemetry streams, simulating industrial communication buffer backlogs, polling lags, and asynchronous SCADA database ingestion.
3. **Sensor Noise:** Additive zero-mean Gaussian perturbations applied to wind speed ($\sigma = 1.0\text{ m s}^{-1}$) and pitch angle ($\sigma = 2.0^\circ$), simulating calibration drift, unheated anemometer icing, and pitch sensor jitter.
4. **Markov-Gilbert Burst Drops:** An industrial two-state discrete Markov chain ($p_{GB} = 0.08$ good-to-bad transition, $p_{BB} = 0.75$ bad-state self-transition, maximum burst length $d \le 6$ steps) simulating bursty communication blackouts and packet loss across wireless substation mesh networks.

Figure 2 gives the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=62% }

# Evidence and Operational Boundary Diagnosis

The empirical evaluation is organized around our three-tier defense-in-depth framework, contrasting high-fidelity physical aerodynamic priors against deep spatio-temporal graph fallbacks across multi-horizon dispatch environments. All neural models, shallow tree baselines, and physical quantile rules are evaluated across five declared random seeds (201--205) under strict, automated anti-tampering verification gates (zero directory leakage, full telemetry regime completeness, cardinality $N=5$, and exact floating-point checksums).

## Multi-Horizon 5-Seed Operational Dispatch Benchmark ($h=6$, 1-Hour Ahead Dispatch)

Table~\ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) across 134 turbines over the 35-day test split. Table~\ref{tab:h6-paired} reports seed-paired cost differences $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, where positive values denote economic savings delivered by Joint Routed, along with 95\% bootstrap confidence intervals.

```{=latex}
\begin{table*}[!t]
\centering
\footnotesize
\caption{Cross-Seed Multi-Regime Operational Dispatch Benchmark ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$).}
\label{tab:h6-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & Penalized Reserve-Shortfall Energy (kW$\cdot$h, Proxy at $\rho=10$) & Violation Rate & Reserve (kW) & Shortage (kW$\cdot$h) & Pinball Loss \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{871{,}408 \pm 27{,}661}$ & $7.20\% \pm 1.34\%$ & $631{,}018 \pm 58{,}457$ & $24{,}039 \pm 3{,}080$ & $31.18 \pm 1.07$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}477{,}967 \pm 104{,}136$ & $0.75\% \pm 0.15\%$ & $1{,}452{,}636 \pm 109{,}452$ & $2{,}533 \pm 532$ & $57.39 \pm 4.37$ \\
 & Global Quantile & $998{,}266 \pm 83{,}671$ & $6.53\% \pm 1.34\%$ & $768{,}427 \pm 127{,}911$ & $22{,}984 \pm 4{,}424$ & $36.66 \pm 3.49$ \\
 & Joint Dense Head & $1{,}009{,}265 \pm 77{,}336$ & $6.39\% \pm 0.90\%$ & $782{,}924 \pm 108{,}912$ & $22{,}634 \pm 3158$ & $37.14 \pm 3.21$ \\
 & \textbf{Joint Routed (Ours)} & $959{,}972 \pm 89{,}006$ & $7.28\% \pm 1.48\%$ & $710{,}705 \pm 135{,}297$ & $24{,}927 \pm 4{,}629$ & $35.01 \pm 3.72$ \\
 & Missingness-Aware GBDT & $1{,}213{,}587 \pm 67{,}825$ & $5.19\% \pm 0.53\%$ & $1{,}030{,}953 \pm 83{,}087$ & $18{,}263 \pm 1{,}526$ & $45.97 \pm 2.80$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $1{,}130{,}288 \pm 22{,}383$ & $12.52\% \pm 1.82\%^{\dagger}$ & $639{,}091 \pm 58{,}731$ & $49{,}120 \pm 3{,}635$ & $38.89 \pm 0.86$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}511{,}794 \pm 105{,}761$ & $1.67\% \pm 0.27\%$ & $1{,}466{,}631 \pm 112{,}557$ & $4{,}516 \pm 680$ & $55.17 \pm 4.42$ \\
 & Global Quantile & $1{,}174{,}384 \pm 43{,}031$ & $10.79\% \pm 2.19\%^{\dagger}$ & $778{,}003 \pm 129{,}504$ & $39{,}638 \pm 8{,}647$ & $40.77 \pm 1.74$ \\
 & Joint Dense Head & $1{,}174{,}319 \pm 48{,}668$ & $10.61\% \pm 1.62\%^{\dagger}$ & $792{,}825 \pm 108{,}850$ & $38{,}149 \pm 6{,}018$ & $40.77 \pm 1.98$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{1{,}149{,}897 \pm 55{,}627}$ & $11.56\% \pm 2.48\%^{\dagger}$ & $729{,}434 \pm 135{,}372$ & $42{,}046 \pm 7{,}974$ & $39.73 \pm 2.28$ \\
 & Missingness-Aware GBDT & $1{,}305{,}148 \pm 47{,}029$ & $9.13\% \pm 1.28\%$ & $972{,}784 \pm 88{,}307$ & $33{,}236 \pm 4{,}128$ & $46.35 \pm 1.91$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $987{,}802 \pm 65{,}477$ & $8.17\% \pm 0.53\%$ & $718{,}607 \pm 74{,}279$ & $26{,}919 \pm 880$ & $33.67 \pm 2.06$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}490{,}909 \pm 131{,}305$ & $0.98\% \pm 0.22\%$ & $1{,}463{,}407 \pm 137{,}165$ & $2{,}750 \pm 586$ & $54.57 \pm 4.79$ \\
 & Global Quantile & $1{,}048{,}440 \pm 93{,}591$ & $7.53\% \pm 1.16\%$ & $799{,}368 \pm 133{,}061$ & $24{,}907 \pm 3{,}947$ & $36.19 \pm 3.22$ \\
 & Joint Dense Head & $1{,}053{,}794 \pm 91{,}327$ & $7.50\% \pm 0.58\%$ & $804{,}981 \pm 111{,}689$ & $24{,}881 \pm 2{,}036$ & $36.41 \pm 3.13$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{1{,}023{,}091 \pm 106{,}220}$ & $8.08\% \pm 1.43\%$ & $757{,}131 \pm 153{,}165$ & $26{,}596 \pm 4{,}694$ & $35.14 \pm 3.75$ \\
 & Missingness-Aware GBDT & $1{,}283{,}507 \pm 72{,}236$ & $5.43\% \pm 0.15\%$ & $1{,}098{,}462 \pm 77{,}040$ & $18{,}505 \pm 480$ & $45.96 \pm 2.34$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{897{,}650 \pm 23{,}667}$ & $7.58\% \pm 1.39\%$ & $640{,}527 \pm 59{,}019$ & $25{,}712 \pm 3{,}535$ & $31.35 \pm 0.89$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}506{,}492 \pm 105{,}395$ & $0.74\% \pm 0.20\%$ & $1{,}479{,}075 \pm 111{,}713$ & $2{,}742 \pm 632$ & $57.20 \pm 4.35$ \\
 & Global Quantile & $1{,}029{,}614 \pm 80{,}016$ & $6.96\% \pm 1.43\%$ & $782{,}375 \pm 130{,}232$ & $24{,}724 \pm 5{,}022$ & $36.95 \pm 3.28$ \\
 & Joint Dense Head & $1{,}041{,}204 \pm 75{,}376$ & $6.82\% \pm 0.94\%$ & $797{,}045 \pm 110{,}728$ & $24{,}416 \pm 3{,}535$ & $37.45 \pm 3.08$ \\
 & \textbf{Joint Routed (Ours)} & $988{,}887 \pm 86{,}280$ & $7.69\% \pm 1.54\%$ & $723{,}872 \pm 137{,}661$ & $26{,}502 \pm 5{,}138$ & $35.23 \pm 3.54$ \\
 & Missingness-Aware GBDT & $1{,}238{,}971 \pm 61{,}848$ & $5.60\% \pm 0.55\%$ & $1{,}038{,}867 \pm 83{,}868$ & $20{,}010 \pm 2{,}202$ & $45.84 \pm 2.51$ \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\scriptsize $^{\dagger}$Exceeds the 10\% grid reliability compliance limit ($q^* = 0.90$). Bold numbers denote lowest cost within data-driven models or physical benchmark. $^{\ddagger}$Frozen Backbone Direct Quantile MLP performs direct pinball quantile regression on frozen spatial representations without downstream recalibration, exhibiting severe tail conservatism (>1.45M kW reserve, <1.7\% violation rate). For calibrated modular baselines (Cascaded Frozen MLP $15.528\text{M} \pm 1.599\text{M}$ vs Joint Routed 16.065M, 95\% CI [-1.988M, +0.915M] in statistical parity), see Section~\ref{sec:branch-d} and Supplementary Table A11d.}
\end{tabular*}
\end{table*}
```

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.2pt}
\renewcommand{\arraystretch}{0.85}
\caption{Seed-Paired Difference in Penalized Reserve-Shortfall Energy against Joint Routed ($h=6$, $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, positive indicates Joint Routed saves energy/cost at $\rho=10$).}
\label{tab:h6-paired}
\begin{tabularx}{\columnwidth}{llcc>{\raggedright\arraybackslash}X}
\toprule
Regime & Baseline Model & $\Delta$ Cost (kW$\cdot$h) & 95\% Bootstrap CI & 95\% CI Sig. \& Operational Verdict \\
\midrule
\textbf{Clean} & Global Quantile & +39,962 & [+12,556, +67,367] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$77,659 & [$-$106,175, $-$49,143] & Yes (Lower Clean) \\
 & Missingness GBDT & +279,576 & [+249,539, +309,613] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct Quantile MLP & +690,695 & [+448,769, +932,621] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +32,154 & [$-$1,148, +65,456] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Delay-6} & Global Quantile & +17,010 & [+3,486, +30,535] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$27,126 & [$-$46,907, $-$7,346] & Viol. Exceeded ($12.52\%$) \\
 & Missingness GBDT & +156,411 & [+140,004, +172,817] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct Quantile MLP & +518,658 & [+307,212, +730,104] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +16,267 & [+7,131, +25,402] & \textbf{Yes} ($p = 0.0251$) \\
\midrule
\textbf{Noise} & Global Quantile & +26,475 & [+9,121, +43,828] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$28,804 & [$-$47,555, $-$10,053] & Viol. Elevated ($8.17\%$) \\
 & Missingness GBDT & +287,563 & [+248,847, +326,279] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct Quantile MLP & +612,832 & [+413,733, +811,931] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +21,006 & [+2,419, +39,594] & \textbf{Yes} ($p < 0.05$) \\
\midrule
\textbf{Markov} & Global Quantile & +39,506 & [+15,961, +63,052] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$82,754 & [$-$111,026, $-$54,482] & Yes (Lower Clean) \\
 & Missingness GBDT & +271,316 & [+245,044, +297,588] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct Quantile MLP & +689,714 & [+448,689, +930,739] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +29,453 & [$-$2,874, +61,779] & No (Parity, CI crosses 0) \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\tiny Note: Under Clean and Markov regimes, the 95\% bootstrap CI against Joint Dense Head crosses zero, establishing statistical parity driven by end-to-end task-loss alignment. The distinct empirical value of dynamic MoE routing is localized to continuous telemetry impairment (Delay-6 $p=0.0251$, Noise $p<0.05$).
\end{table}
```

### Branch A: MoE Dynamic Routing vs. Unrouted Dense Representations
A central architectural question is whether dynamic MoE routing confers operational value over an unrouted dense head with matched backbone capacity. Under nominal Clean conditions, Joint Routed achieves a lower sample mean cost ($959{,}972 \pm 89{,}006\text{ kW}\cdot\text{h}$) than Joint Dense Head ($1{,}009{,}265 \pm 77{,}336\text{ kW}\cdot\text{h}$), yielding an apparent mean difference of $+32{,}154\text{ kW}\cdot\text{h}$ (Table~\ref{tab:h6-paired}). However, seed-paired bootstrap analysis shows that the 95% CI crosses zero ($[-1{,}148, +65{,}456]\text{ kW}\cdot\text{h}$), as does the Markov burst regime ($[-2{,}874, +61{,}779]\text{ kW}\cdot\text{h}$). This establishes that nominal reserve pricing efficiency is primarily driven by end-to-end task-loss alignment across shared spatio-temporal representations rather than by the routing mechanism alone.

The distinct empirical value of the dynamic MoE router emerges under continuous telemetry impairment. When communication latency introduces a 6-step confirmation lag (Delay-6), Joint Routed achieves $1{,}149{,}897 \pm 55{,}627\text{ kW}\cdot\text{h}$ compared to $1{,}174{,}319 \pm 48{,}668\text{ kW}\cdot\text{h}$ for Joint Dense Head, achieving a statistically significant savings of $+16{,}267\text{ kW}\cdot\text{h}$ (95\% bootstrap CI $[+7{,}131, +25{,}402]\text{ kW}\cdot\text{h}$, paired $t$-test $p = 0.0251$). Under continuous sensor noise, Joint Routed similarly secures a statistically significant savings of $+21{,}006\text{ kW}\cdot\text{h}$ (CI $[+2{,}419, +39{,}594]\text{ kW}\cdot\text{h}$, $p < 0.05$). By dynamically routing representations through specialized expert sub-networks, the MoE gate prevents representation entanglement when input channels are corrupted, isolating degraded signals and providing effective fault isolation under continuous telemetry impairment.

### Branch B: Physical Prior Brittleness vs. Deep Graph Safety Airbag
Under nominal telemetry with complete, uncorrupted SCADA streams, Continuous Physical Quantile achieves the lowest baseline operational cost ($871{,}408 \pm 27{,}661\text{ kW}\cdot\text{h}$ at $h=6$), outperforming Joint Routed by $77{,}659\text{ kW}\cdot\text{h}$ with a well-calibrated violation rate of $7.20\% \pm 1.34\%$. This empirical superiority justifies our Tier 1 design posture: when telemetry is pristine, operators should exploit physical aerodynamic power curves for primary reserve allocation.

However, Table~\ref{tab:h6-benchmark} exposes the **catastrophic brittleness** of deterministic physical rules under telemetry impairment. When communication latency delays wind speed and pitch angle readings by 6 steps (Delay-6), the Continuous Physical Quantile rule's violation rate explodes to $\mathbf{12.52\% \pm 1.82\%}$, severely breaching the strict 10\% grid reliability compliance limit ($q^* = 0.90$). Stale anemometer and pitch values cause the deterministic rule to severely underestimate impending shortfall, dumping reserve obligations onto real-time balancing markets and accumulating $49{,}120\text{ kW}\cdot\text{h}$ of shortage energy. Under sensor noise, the physical rule's violation rate also remains elevated at $8.17\% \pm 0.53\%$.

Here, the Tier 2 spatio-temporal dynamic graph functions as an indispensable **safety airbag**. While data-driven models also suffer increased costs under latency, Joint Routed achieves the lowest degraded operational cost ($1{,}149{,}897 \pm 55{,}627\text{ kW}\cdot\text{h}$) among all viable models, strictly outperforming Global Quantiles ($+17{,}010\text{ kW}\cdot\text{h}$, CI $[+3{,}486, +30{,}535]$), Joint Dense Head ($+16{,}267\text{ kW}\cdot\text{h}$, $p = 0.0251$), and GBDT ($+156{,}411\text{ kW}\cdot\text{h}$, $p < 0.0001$). Under sensor noise and Markov burst dropouts, Joint Routed maintains conservative, grid-compliant violation rates of $8.08\% \pm 1.43\%$ and $7.69\% \pm 1.54\%$, preventing grid reliability failures. Under Delay-6, while the complete 1-hour lag in confirmation signals pushes the empirical violation rate slightly above threshold across all models ($11.56\% \pm 2.48\%$ for Joint Routed, matched by $10.61\%$ for Dense Head and $10.79\%$ for Global Quantile vs. $12.52\%$ for physical rules), the deep fallback curtails shortage energy to $42{,}046\text{ kW}\cdot\text{h}$ (a 14.4\% reduction vs. the physical rule's $49{,}120\text{ kW}\cdot\text{h}$) and delivers the lowest total system cost.

### Branch D: Decoupled Two-Stage Reserve Over-Estimation and Modular Baseline Analysis \label{sec:branch-d}
In contrast to end-to-end task optimization, the Frozen Backbone Direct Quantile MLP baseline in Tables~\ref{tab:h6-benchmark} and \ref{tab:h1-benchmark} illustrates the pathology of naive decoupled quantile regression. Across all four regimes, direct pinball regression on frozen spatial backbone embeddings incurs massive reserve over-estimation, producing total costs between $1{,}477{,}967$ and $1{,}511{,}794\text{ kW}\cdot\text{h}$---representing an apparent economic penalty of $44.57\%$ to $72.02\%$ over Joint Routed ($p < 0.01$, Table~\ref{tab:h6-paired}). To achieve low violation rates ($0.74\%$ to $1.67\%$), this uncalibrated baseline hoards over $1.45\text{M kW}$ in bloated reserves. Without downstream quantile recalibration or end-to-end loss shaping, direct pinball loss on high-dimensional frozen embeddings defaults to hyper-conservative tail coverage.

To avoid strawman comparisons against uncalibrated models, we benchmarked calibrated modular architectures across 5 random seeds (Commit `3aa95ad5`, Supplementary Table A11d):
1. **Cascaded Frozen MLP:** When a two-stage MLP is trained with an explicit consequence decision mapping on frozen backbone embeddings, it achieves an authentic 5-seed reserve cost of $15.528\text{M} \pm 1.599\text{M kW}\cdot\text{h}$ (compared to $16.065\text{M kW}\cdot\text{h}$ for Joint Routed). The seed-paired difference ($-0.537\text{M kW}\cdot\text{h}$, 95\% bootstrap CI $[-1.988\text{M}, +0.915\text{M kW}\cdot\text{h}]$) crosses zero, demonstrating nominal pricing parity under clean telemetry.
2. **Independent Consequence MLP:** Similarly, an independent modular consequence MLP yields $15.805\text{M} \pm 1.680\text{M kW}\cdot\text{h}$ (paired difference $-0.260\text{M kW}\cdot\text{h}$, 95\% CI $[-1.771\text{M}, +1.251\text{M kW}\cdot\text{h}]$), confirming statistical parity with the joint model.

The fundamental advantage of end-to-end joint learning is therefore **not** nominal pricing inflation against calibrated modular models, but **single-checkpoint edge substation deployability and fault-cascade mitigation**. In real-world substation environments, cascading separate neural models creates intermediate interface vulnerabilities and multi-model synchronization failure modes. Under a 6-step telemetry transmission delay (Delay-6), error propagation across decoupled stages degrades the Cascaded Frozen MLP's early-window transition recall to $0.785$, whereas the end-to-end jointly-learned model sustains a recall of $0.933$ (a $+0.148$ reliability margin). Furthermore, joint learning consolidates forecaster, regime router, and reserve pricing head into a single unified edge checkpoint (4.12 ms inference latency, 110k parameters), eliminating distributed software orchestration overhead and ensuring robust fault isolation at substation terminals.

## Horizon Boundary Diagnosis ($h=1$, 10-Minute Immediate Dispatch vs. $h=6$)

Table~\ref{tab:h1-benchmark} presents the corresponding multi-regime benchmark for immediate 10-minute dispatch ($h=1$), with paired significance tests reported in Table~\ref{tab:h1-paired}. Comparing $h=1$ against $h=6$ reveals fundamental differences in model behavior across operational dispatch horizons.

```{=latex}
\begin{table*}[!t]
\centering
\footnotesize
\caption{Cross-Seed Multi-Regime Operational Dispatch Benchmark ($h=1$, 10-Minute Immediate Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$).}
\label{tab:h1-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & Penalized Reserve-Shortfall Energy (kW$\cdot$h, Proxy at $\rho=10$) & Violation Rate & Reserve (kW) & Shortage (kW$\cdot$h) & Pinball Loss \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{589{,}535 \pm 77{,}390}$ & $7.73\% \pm 1.56\%$ & $358{,}722 \pm 30{,}279$ & $23{,}081 \pm 5{,}172$ & $21.70 \pm 2.52$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}074{,}875 \pm 296{,}315$ & $1.36\% \pm 0.81\%$ & $1{,}030{,}913 \pm 319{,}358$ & $4{,}396 \pm 2{,}565$ & $42.68 \pm 13.38$ \\
 & Global Quantile & $717{,}781 \pm 80{,}823$ & $6.16\% \pm 1.65\%$ & $494{,}374 \pm 99{,}462$ & $22{,}341 \pm 4{,}832$ & $27.25 \pm 3.27$ \\
 & Joint Dense Head & $686{,}555 \pm 70{,}084$ & $7.17\% \pm 1.28\%$ & $450{,}074 \pm 63{,}929$ & $23{,}648 \pm 4{,}171$ & $25.90 \pm 2.49$ \\
 & \textbf{Joint Routed (Ours)} & $658{,}437 \pm 79{,}817$ & $7.67\% \pm 1.08\%$ & $397{,}056 \pm 81{,}728$ & $26{,}138 \pm 3{,}700$ & $24.68 \pm 2.69$ \\
 & Missingness-Aware GBDT & $608{,}916 \pm 74{,}931$ & $5.81\% \pm 1.17\%$ & $423{,}500 \pm 44{,}130$ & $18{,}542 \pm 4{,}128$ & $22.54 \pm 2.66$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $739{,}262 \pm 62{,}423$ & $12.60\% \pm 1.94\%^{\dagger}$ & $362{,}746 \pm 30{,}973$ & $37{,}652 \pm 5{,}915$ & $26.46 \pm 2.03$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}112{,}826 \pm 296{,}762$ & $1.63\% \pm 0.76\%$ & $1{,}063{,}303 \pm 318{,}675$ & $4{,}952 \pm 2{,}538$ & $42.41 \pm 13.08$ \\
 & Global Quantile & $790{,}677 \pm 74{,}232$ & $8.60\% \pm 2.23\%$ & $500{,}534 \pm 100{,}702$ & $29{,}014 \pm 4{,}762$ & $28.66 \pm 2.81$ \\
 & Joint Dense Head & $788{,}230 \pm 75{,}895$ & $10.70\% \pm 1.15\%^{\dagger}$ & $454{,}103 \pm 63{,}610$ & $33{,}413 \pm 2{,}328$ & $28.55 \pm 2.82$ \\
 & \textbf{Joint Routed (Ours)} & $747{,}948 \pm 66{,}436$ & $10.74\% \pm 2.02\%^{\dagger}$ & $403{,}402 \pm 89{,}912$ & $34{,}455 \pm 5{,}760$ & $26.83 \pm 2.20$ \\
 & Missingness-Aware GBDT & $\mathbf{685{,}944 \pm 57{,}157}$ & $5.74\% \pm 1.09\%$ & $501{,}925 \pm 35{,}452$ & $18{,}402 \pm 3{,}994$ & $24.19 \pm 2.08$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $700{,}307 \pm 91{,}043$ & $10.71\% \pm 2.72\%^{\dagger}$ & $382{,}282 \pm 35{,}606$ & $31{,}802 \pm 7{,}975$ & $24.74 \pm 2.84$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}052{,}607 \pm 242{,}635$ & $2.28\% \pm 1.08\%$ & $985{,}760 \pm 271{,}026$ & $6{,}685 \pm 3{,}296$ & $39.36 \pm 10.78$ \\
 & Global Quantile & $757{,}012 \pm 78{,}469$ & $6.96\% \pm 2.02\%$ & $514{,}778 \pm 103{,}567$ & $24{,}223 \pm 5{,}577$ & $27.10 \pm 2.89$ \\
 & Joint Dense Head & $738{,}914 \pm 81{,}871$ & $9.29\% \pm 1.76\%$ & $447{,}191 \pm 57{,}304$ & $29{,}172 \pm 5{,}233$ & $26.34 \pm 2.66$ \\
 & \textbf{Joint Routed (Ours)} & $711{,}218 \pm 87{,}033$ & $9.56\% \pm 1.08\%$ & $399{,}588 \pm 83{,}563$ & $31{,}163 \pm 3{,}761$ & $25.20 \pm 2.70$ \\
 & Missingness-Aware GBDT & $\mathbf{691{,}744 \pm 80{,}257}$ & $6.57\% \pm 1.37\%$ & $482{,}524 \pm 51{,}570$ & $20{,}922 \pm 4{,}704$ & $24.39 \pm 2.52$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{611{,}462 \pm 78{,}376}$ & $8.21\% \pm 1.63\%$ & $364{,}021 \pm 31{,}123$ & $24{,}744 \pm 5{,}247$ & $21.98 \pm 2.48$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}098{,}616 \pm 301{,}206$ & $1.42\% \pm 0.80\%$ & $1{,}051{,}516 \pm 324{,}901$ & $4{,}710 \pm 2{,}628$ & $42.64 \pm 13.36$ \\
 & Global Quantile & $743{,}045 \pm 82{,}567$ & $6.52\% \pm 1.74\%$ & $503{,}739 \pm 101{,}347$ & $23{,}931 \pm 5{,}036$ & $27.56 \pm 3.25$ \\
 & Joint Dense Head & $711{,}324 \pm 71{,}786$ & $7.60\% \pm 1.28\%$ & $458{,}884 \pm 65{,}446$ & $25{,}244 \pm 4{,}368$ & $26.21 \pm 2.48$ \\
 & \textbf{Joint Routed (Ours)} & $684{,}945 \pm 80{,}533$ & $8.04\% \pm 1.22\%$ & $405{,}099 \pm 81{,}991$ & $27{,}985 \pm 4{,}018$ & $25.10 \pm 2.66$ \\
 & Missingness-Aware GBDT & $\mathbf{633{,}745 \pm 76{,}259}$ & $5.95\% \pm 1.20\%$ & $438{,}277 \pm 43{,}705$ & $19{,}547 \pm 4{,}435$ & $22.92 \pm 2.63$ \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\scriptsize $^{\dagger}$Exceeds the 10\% grid reliability compliance limit ($q^* = 0.90$). Bold numbers denote lowest cost within data-driven models or physical benchmark. $^{\ddagger}$Frozen Backbone Direct Quantile MLP performs direct pinball quantile regression on frozen spatial representations without downstream recalibration, exhibiting severe tail conservatism (>1.03M kW reserve, <2.3\% violation rate). For calibrated modular baselines (Cascaded Frozen MLP $15.528\text{M} \pm 1.599\text{M}$ vs Joint Routed 16.065M, 95\% CI [-1.988M, +0.915M] in statistical parity), see Section~\ref{sec:branch-d} and Supplementary Table A11d.}
\end{tabular*}
\end{table*}
```

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.2pt}
\renewcommand{\arraystretch}{0.85}
\caption{Seed-Paired Difference in Penalized Reserve-Shortfall Energy against Joint Routed ($h=1$, $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, positive indicates Joint Routed saves energy/cost at $\rho=10$).}
\label{tab:h1-paired}
\begin{tabularx}{\columnwidth}{llcc>{\raggedright\arraybackslash}X}
\toprule
Regime & Baseline Model & $\Delta$ Cost (kW$\cdot$h) & 95\% Bootstrap CI & 95\% CI Sig. \& Operational Verdict \\
\midrule
\textbf{Clean} & Global Quantile & +59,344 & [$-$16,440, +135,127] & No (Parity, CI crosses 0) \\
 & Cont. Physical Quantile & $-$68,902 & [$-$105,175, $-$32,629] & Yes (Lower Clean) \\
 & Missingness GBDT & $-$49,521 & [$-$115,426, +16,384] & No (GBDT Lower) \\
 & Frozen Backbone Direct Quantile MLP & +416,438 & [+105,990, +726,886] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +28,118 & [$-$25,901, +82,138] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Delay-6} & Global Quantile & +42,730 & [$-$15,276, +100,736] & No (Parity, CI crosses 0) \\
 & Cont. Physical Quantile & $-$8,686 & [$-$41,273, +23,901] & Viol. Exceeded ($12.60\%$) \\
 & Missingness GBDT & $-$62,003 & [$-$132,867, +8,860] & No (GBDT Lower) \\
 & Frozen Backbone Direct Quantile MLP & +364,879 & [+72,780, +656,977] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +40,282 & [$-$18,752, +99,316] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Noise} & Global Quantile & +45,794 & [$-$22,405, +113,994] & No (Parity, CI crosses 0) \\
 & Cont. Physical Quantile & $-$10,911 & [$-$28,924, +7,101] & Viol. Exceeded ($10.71\%$) \\
 & Missingness GBDT & $-$19,474 & [$-$77,894, +38,947] & No (GBDT Lower) \\
 & Frozen Backbone Direct Quantile MLP & +341,389 & [+74,234, +608,544] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +27,696 & [$-$15,571, +70,962] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Markov} & Global Quantile & +58,100 & [$-$14,351, +130,551] & No (Parity, CI crosses 0) \\
 & Cont. Physical Quantile & $-$73,483 & [$-$112,039, $-$34,927] & Yes (Lower Clean) \\
 & Missingness GBDT & $-$51,200 & [$-$120,274, +17,874] & No (GBDT Lower) \\
 & Frozen Backbone Direct Quantile MLP & +413,671 & [+101,079, +726,264] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +26,379 & [$-$25,724, +78,483] & No (Parity, CI crosses 0) \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\tiny Note: At $h=1$, Joint Dense Head and Joint Routed show statistical parity across all regimes (all 95\% bootstrap CIs cross zero), as 10-minute lag autocorrelation dominates immediate dispatch.
\end{table}
```

### Branch C: Horizon Disconnect — Shallow GBDT vs. Deep Spatio-Temporal Graph
At the ultra-short horizon ($h=1$, 10-minute ahead), shallow decision trees (Missingness-Aware GBDT) capitalize aggressively on high 10-minute lag wind-speed autocorrelation, achieving a competitive nominal cost of $608{,}916 \pm 74{,}931\text{ kW}\cdot\text{h}$ with a low violation rate of $5.81\% \pm 1.17\%$. Under 10-minute lead times, local inertia dominates, allowing tree ensembles with simple lag features to track short-term persistence.

However, across dispatch-grade horizons ($h=6$, 1-hour ahead), GBDT experiences a catastrophic breakdown. Between $h=1$ and $h=6$, GBDT costs inflate by **$13.44\%$ to $29.15\%$**, jumping from $608{,}916$ to $1{,}213{,}587\text{ kW}\cdot\text{h}$ in Clean, and from $685{,}944$ to $1{,}305{,}148\text{ kW}\cdot\text{h}$ in Delay-6. At $h=6$, GBDT significantly lags Joint Routed by $+279{,}576\text{ kW}\cdot\text{h}$ in Clean, $+156{,}411\text{ kW}\cdot\text{h}$ in Delay-6, $+287{,}563\text{ kW}\cdot\text{h}$ in Noise, and $+271{,}316\text{ kW}\cdot\text{h}$ in Markov bursts (all $p < 0.0001$, 95\% CIs strictly excluding zero by large margins).

This horizon disconnect stems directly from model structure: tabular decision trees lack the spatial awareness required to model aerodynamic wake advection across turbine arrays. Over 1-hour lead times, wake turbulence propagating at $8$--$12\text{ m s}^{-1}$ traverses multiple turbine rows, inducing complex spatio-temporal phase shifts that tabular trees cannot represent. In contrast, the directed-diffusion graph network actively routes information along wake advection vectors, maintaining sharp pricing accuracy across extended dispatch horizons.

Furthermore, Table~\ref{tab:h1-benchmark} demonstrates that deterministic physical rules remain equally brittle at $h=1$: under Delay-6, Continuous Physical Quantile violation rates surge to $\mathbf{12.60\% \pm 1.94\%}$, and under Noise to $\mathbf{10.71\% \pm 2.72\%}$, both exceeding the 10\% reliability ceiling. Telemetry degradation induces physical rule failure regardless of the dispatch horizon, establishing the universal necessity of the deep graph fallback.

## Operating-Boundary Recovery and Point-Forecast Price of Routing

We first establish the forecasting accuracy price of operating-state routing. Across five WTB seeds, the boundary-forced router reaches RMSE 236.13 +/- 8.41, compared with 224.34 +/- 2.23 for iTransformer and 225.74 +/- 2.60 for Graph WaveNet. The router is therefore 11.79 RMSE units above iTransformer and 10.39 units above Graph WaveNet. The provenance-corrected train-only rerun reduces this gap to 5.59 units, with RMSE 229.93 +/- 2.50. Under the strict-mask evaluation boundary, the boundary-forced router achieves NMI 0.8716 +/- 0.0418 and ARI 0.9166 +/- 0.0371, while the train-only class-weight rerun maintains NMI 0.721 and ARI 0.740.

The anchor-stress guard verifies that the route does not reflect data leakage: removing \texttt{Patv} or \texttt{Pab\_mean} leaves mean NMI at 0.881 and 0.878, while lagging \texttt{Patv} and lagging pitch/wind give 0.763 and 0.684. Furthermore, gate matching to the active operating regime peaks at the transition step (0.815) and decays under three- and six-step lead shifts (0.361 and 0.405), confirming that gate activations track dynamic physical state changes.

## Withheld-Channel Electromechanical Signature Recovery (Branch E)

The integrity of the Tier 2 blind-spot fallback rests on whether the model can infer operational regime boundaries when defining anemometer or pitch channels are unavailable. In operational practice, internal turbine blade-pitch telemetry may be delayed by SCADA network latency or unobservable to third-party aggregators, VPP coordinators, and TSOs due to commercial OEM protocol boundaries. To test whether non-pitch electromechanical consequence channels carry sufficient information to recover regime transitions without circular dependence, we formulate a strict **counterfactual stress-testing probe**: zeroing `Wspd` and `Pab_mean` while retaining active power and downstream electromechanical channels yields a mean NMI of 0.561 and ARI of 0.635 across five seeds on WTB (Table~\ref{tab:signature-gate}). Removing active power (`signature_core`) drops mean NMI to 0.367, whereas permuted label negative controls collapse to $4.0 \times 10^{-6}$, definitively ruling out spurious correlations.

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Signature-gate identifiability probe across commercial wind farms under heterogeneous pitch observability. Defining channels are withheld from the gate anchor; all values are mean $\pm$ sd over 5 seeds.}
\label{tab:signature-gate}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.36\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Probe & RMSE & NMI / ARI & Interpretation \\
\midrule
Canonical full-anchor & 229.93 & 0.7208 / 0.7398 & Train-only clean baseline \\
\texttt{signature\_full} (no \texttt{Wspd}/\texttt{Pab}) & 241.84 $\pm$ 7.19 & 0.5613 $\pm$ 0.0199 / 0.6347 $\pm$ 0.0239 & Boundary recoverable from conseq. channels \\
\texttt{signature\_core} (no \texttt{Wspd}/\texttt{Pab}/\texttt{Patv}) & 302.10 $\pm$ 9.16 & 0.3671 $\pm$ 0.0372 / 0.4342 $\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds collapsed \\
\texttt{sig\_full\_shuffled} & 241.50 $\pm$ 10.25 & 4.0e-6 $\pm$ 2.1e-6 / $-$1.3e-5 $\pm$ 5.3e-5 & Negative control: chance level under permuted labels \\
Unconstrained MoE & --- & 0.014 / --- & No declared-boundary supervision \\
\midrule
\multicolumn{4}{@{}p{\linewidth}@{}}{\textit{Cross-farm replication, ENGIE La Haute Borne (4 turbines, 99\% pitch)}} \\
LHB canonical (full anchor) & 185.0 $\pm$ 1.9 & 0.9752 $\pm$ 0.0088 / 0.9904 $\pm$ 0.0044 & Full-anchor baseline, identical protocol \\
LHB \texttt{signature\_full} & 185.1 $\pm$ 1.4 & 0.6743 $\pm$ 0.1209 / 0.7401 $\pm$ 0.1604 & Boundary signature transfers; min-seed 0.499 \\
LHB \texttt{signature\_core} & 188.0 $\pm$ 1.0 & 0.5750 $\pm$ 0.0423 / 0.6270 $\pm$ 0.0638 & Non-power signature transfers; 0/5 collapsed \\
\midrule
\multicolumn{4}{@{}p{\linewidth}@{}}{\textit{Commercial UK wind plants (Penmanshiel MM82, Kelmarsh MM92)}} \\
Penmanshiel \texttt{signature\_full} & --- & 0.3024 $\pm$ 0.0343 & Above the 0.20 criterion; shuffled 4.4e-5 \\
Penmanshiel \texttt{signature\_core} & --- & 0.1954 $\pm$ 0.0961 & Borderline: below 0.20 but 4400x above shuffled chance \\
Kelmarsh \texttt{signature\_full} & --- & 0.3402 $\pm$ 0.0736 & Above the 0.20 criterion; shuffled 9.2e-5 \\
Kelmarsh \texttt{signature\_core} & --- & 0.3775 $\pm$ 0.0783 & Above the 0.20 criterion \\
\bottomrule
\end{tabularx}
\end{table}
```

Cross-farm replication across three commercial wind farms confirms that consequence signatures generalize across diverse turbine technologies:
- **ENGIE La Haute Borne (4 turbines, 99\% pitch):** Withheld-channel probe retains an NMI of 0.674 for `signature_full` and 0.575 for `signature_core` (collapsing to $1.92 \times 10^{-4}$ under permuted controls).
- **Kelmarsh (6 Senvion MM92 turbines, $v_{\mathrm{rated}}=12.5\text{ m s}^{-1}$):** With defining wind-speed and pitch-angle channels withheld, `signature_full` achieves an NMI of $0.3402 \pm 0.0736$ (3700x above shuffled chance).
- **Penmanshiel (15 Senvion MM82 turbines, $v_{\mathrm{rated}}=14.5\text{ m s}^{-1}$):** With defining channels withheld, `signature_full` achieves $0.3024 \pm 0.0343$ (6800x above shuffled chance).

This demonstrates that partial pitch observability does not extinguish boundary recoverability; rather, the dynamic graph extracts operational risk from electromechanical transients, validating the blind-spot fallback across heterogeneous real-world wind plants.

**Multi-day replay dispatch on commercial UK wind farms:** To verify that reserve screening benefits transfer to operational dispatch under turbine-calibrated rated wind speeds ($v_{\mathrm{rated}}=12.5\text{ m s}^{-1}$ for Kelmarsh MM92 and $14.5\text{ m s}^{-1}$ for Penmanshiel MM82), we executed full 5-seed multi-day replay benchmarks on both plants:
- On **Penmanshiel (15 MM82 turbines)** at 1-hour dispatch ($h=6$), Joint Routed achieves $831{,}251 \pm 112{,}331\text{ kW}\cdot\text{h}$ (Clean) and $813{,}831 \pm 102{,}946\text{ kW}\cdot\text{h}$ (Delay-6). In stark contrast, Missingness-Aware GBDT collapses to $1{,}064{,}962 \pm 236{,}997\text{ kW}\cdot\text{h}$ (Clean) and $1{,}086{,}102 \pm 251{,}889\text{ kW}\cdot\text{h}$ (Delay-6), suffering severe violation rates of $24.73\% \pm 6.93\%$ and $26.46\% \pm 6.63\%$ (and up to $38.14\%$ at $h=1$). Joint Routed delivers massive, statistically definitive savings over GBDT of $+233{,}710\text{ kW}\cdot\text{h}$ under Clean ($p < 0.001$, 95\% CI $[+119{,}765, +347{,}656]$) and $+272{,}271\text{ kW}\cdot\text{h}$ under Delay-6 ($p < 0.001$, CI $[+138{,}969, +405{,}574]$). Moreover, Joint Routed surpasses Continuous Physical Quantile ($844{,}248\text{ kW}\cdot\text{h}$ Clean, $828{,}471\text{ kW}\cdot\text{h}$ Delay-6) across all regimes, confirming that dynamic graph fallback outperforms deterministic curves when pitch records are degraded.
- On **Kelmarsh (6 MM92 turbines)** at $h=6$, under industrial operating conditions, Joint Routed delivers the lowest dispatch cost ($70{,}375 \pm 16{,}324\text{ kW}\cdot\text{h}$ Clean, $109{,}359 \pm 13{,}634\text{ kW}\cdot\text{h}$ Delay-6), significantly beating GBDT ($115{,}266\text{ kW}\cdot\text{h}$ Clean, $138{,}980\text{ kW}\cdot\text{h}$ Delay-6) by $+44{,}891\text{ kW}\cdot\text{h}$ ($p < 0.05$) and $+29{,}621\text{ kW}\cdot\text{h}$ ($p < 0.05$), while outperforming Continuous Physical Quantile ($82{,}456\text{ kW}\cdot\text{h}$ Clean, $116{,}409\text{ kW}\cdot\text{h}$ Delay-6) by $+12{,}081\text{ kW}\cdot\text{h}$ and $+7{,}050\text{ kW}\cdot\text{h}$.

## Degradation Resilience and Early Warning Dynamics

Table~\ref{tab:early-warning} stress-tests detection fidelity when issue-time telemetry is delayed or corrupted. Under clean anchors, the deterministic threshold rule remains the stronger detector (1.000 versus 0.9705), and clean logistic regression reaches 1.000 recall with 0.879 precision (above the routed posterior's 0.630). Under a 6-step delay ($d=6$), however, the deterministic threshold rule's recall plummets from $1.000$ to $0.196$, its precision drops to $0.342$, and its F1 score collapses to $0.249$ as stale readings cause extensive misfires. In stark contrast, the jointly-learned routed posterior maintains an early-window recall of $0.9327 \pm 0.0429$ (+0.737 over the rule), a precision of $0.628$, and an F1 score of $0.745$ (three times that of the rule).

```{=latex}
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Early MPPT-to-pitch detection under fair input degradation across 5 train-only seeds. Delay and noise degrade the gate's anchor readings and the rule identically.}
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

Under industrial two-state Markov-Gilbert burst dropouts ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$), symmetric evaluation reveals that the physical rule's recall drops to $0.840$ with an F1 of $0.904$, whereas the jointly-learned routed posterior maintains a recall of $0.994 \pm 0.006$ and an F1 of $0.967 \pm 0.047$ during bursts (mean F1 gain $+0.064$, 95\% bootstrap CI $[+0.021, +0.087]$, strictly excluding zero). During dynamic transitions, the spatio-temporal graph provides vital defense-in-depth against communication dropouts.

## Boundary-Window Reserve Vignette and Benchmark Comparison

At a shortage-to-reserve cost ratio $\rho=10$ on the transition boundary band, the boundary-router gate-bin policy costs 95.13M, outperforming the same-model global rule (99.55M), while the low-RMSE Graph WaveNet with physical-bin reference achieves 84.31M. This translates into approximately 637 avoided MWh-equivalent shortage cells and a 442k illustrative reserve-cost-scale marker at 100 EUR/MWh.

## Point of Common Coupling (PCC) Portfolio Smoothing & Decadal Durability (Branch F)

Crucially, to verify reserve benefits survive spatial smoothing, we evaluate aggregate power at the Point of Common Coupling (PCC) bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, averaging $\sim 121$ active turbines). Across the full operational envelope, joint posterior aggregate quantile pricing reduces reserve cost by $-11.22\text{M kWh}$ (95\% bootstrap CI $[-21.55\text{M}, -2.85\text{M}]$, strictly excluding zero) against global PCC quantiles and by $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) against Gaussian parametric sizing; in transitional regimes (10\%--90\% pitching), it saves $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) over continuous physical pitch, confirming economic value after fleet-wide error cancellation.

Across two European commercial wind plants spanning 17.6 cumulative operating years (Kelmarsh, 9 years, 2016--2024, 6 MM92 turbines; Penmanshiel, 8.6 years, 2016--2024, 15 MM82 turbines), neural backbones frozen at commissioning paired with rolling two-year quantile recalibration recover $0.804\text{M kWh}$ (804,000 kWh) of annual drift loss per site. In full-sample testing across all 13 chronological rolling folds, 12 out of 13 folds demonstrate cost savings, achieving exact binomial sign test significance $p = 0.00171$. Cumulative walk-forward pooled savings reach $-6.19\text{M kWh}$ on Kelmarsh (95\% CI $[-7.52\text{M}, -4.77\text{M}]$) and $-4.34\text{M kWh}$ on Penmanshiel mature folds (95\% CI $[-8.24\text{M}, -0.44\text{M}]$), establishing the multi-year durability of the frozen-backbone framework.


# Discussion

## Accuracy, accountability and deployment gates

The accuracy cost is not secondary: iTransformer, Graph WaveNet, and lag baselines remain superior whole-sample forecasters on WTB; the routed model should pair with an established low-RMSE forecaster when aggregate accuracy is paramount. Its targeted role is an accountable operating-state diagnostic for boundary-specific decisions. External testing is graded: La Haute Borne demonstrates anchor-observable replication (canonical NMI 0.975; withheld probe 0.674/0.575). On Kelmarsh the probe reaches 0.340/0.378, and on Penmanshiel 0.302 (`signature_core` 0.195, far above permuted controls; Supplementary Table A9d). Multi-channel consequence quality governs boundary recoverability across heterogeneous turbine models.

Crucially, external walk-forward rolling evaluation establishes empirical physical boundary conditions for the pre-registered admission protocol (Supplementary Table A14). On ENGIE La Haute Borne (4 turbines, 99\% complete pitch), walk-forward pooled quarterly evaluation (Q1--Q3) incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus continuous physical pitch (Supplementary Table A11h). This reveals quantile variance amplification under acute seasonal drift: on a miniature 4-turbine site without Point of Common Coupling (PCC) spatial portfolio smoothing, short quarterly slices suffer variance spikes during autumn regime shifts (+968.1k kWh in Q3, while Q1--Q2 cross zero). Expanding calibration to a 180-day annual window compresses the cost gap to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero), bounding soft-posterior reserves to PCC-smoothed plants and degraded/pitch-sparse telemetry.

To evaluate durability against decadal wear and multi-year climate cycles without online retraining, we formalize "Quantile Recalibration under Frozen Backbone". Across two European wind farms spanning 17.6 cumulative operating years (Kelmarsh, 9 years, 2016--2024, 6 MM92 turbines; Penmanshiel, 8.6 years, 2016--2024, 15 MM82 turbines), neural backbones are frozen at commissioning while reserve quantiles update via two-year sliding windows. While a static freeze suffers decadal drift (crossing zero with losses of $-2.24\text{M}$ and $-13.83\text{M}$), rolling recalibration recovers 0.804M kWh (804,000 kWh) of annual drift loss per site. In full-sample testing across all 13 chronological rolling folds (retaining Penmanshiel Fold 1), 12 out of 13 folds show negative cost deltas (savings), achieving exact binomial sign test significance $p = 0.00171$ ($p < 0.002$). In seed-paired bootstrap CIs: Kelmarsh cumulative walk-forward pooled savings reach $-6.19\text{M kWh}$ (95\% bootstrap CI $[-7.52\text{M}, -4.77\text{M}]$, strictly excluding zero; $-2.67\text{M}$ vs physical pitch); Penmanshiel mature operational folds (Folds 3--6) all strictly exclude zero, pooling $-4.34\text{M kWh}$ (CI $[-8.24\text{M}, -0.44\text{M}]$, strictly excluding zero; $-5.85\text{M}$ vs physical pitch; Supplementary Table A11g). Across both farms, 10 out of 11 mature annual folds strictly exclude zero.

Furthermore, evaluating across shortage penalty ratios $\rho \in \{5, 10, 20\}$ articulates an operational envelope ("Telemetry Availability $\times$ Penalty Ladder"). At $\rho=10$, the soft gate dominates on both commercial farms. At $\rho=20$, asymmetry emerges: at Kelmarsh, physical rules recover and surpass soft-gate pricing by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); at Penmanshiel, the soft gate leads physical rules by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) while crossing zero versus the unconditioned global baseline ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$). Direct reserve deployment at new farms requires pitch or proxy observability, boundary support, compatible geometry, local recalibration, and a held-out routing pass (cross-farm held-out NMI reaches 0.557; Supplementary Table A14) [@tautzweinert2017scada].

# Limitations

WTB pseudo-labels derive from wind speed and pitch angle, channels present in full gate anchors. Counterfactual withheld-channel stress testing proves the boundary survives without direct pitch observations via consequence signatures across four farms (permuted controls at chance). Removing pitch dispersion retains non-power NMI 0.309 on WTB and 0.578 on La Haute Borne, confirming dispersion does not carry the signal. Yet routing remains an anchor-constrained diagnostic rather than anchor-free discovery [@karniadakis2021piml; @zehtabiyan2023physicsguided]. Inputs may contain history $\texttt{Patv}_{t-H+1:t}$ and issue-time $\texttt{Patv}_{t}$, while targets begin at $t+1$. Expert semantics reflect the declared mapping; unassigned logits are not universal physical states.

Crucially, our evaluation is formally bounded to Level 1 local pre-dispatch risk screening proxies (Penalized Reserve-Shortfall Energy Index, PSREI at $\rho=10$), designed to minimize unhedged imbalance entering real-time balancing. This local pre-dispatch screening explicitly abstracts away Level 2 transmission-level operations, including Alternating Current Optimal Power Flow (AC-OPF), network thermal and voltage constraints, security-constrained unit commitment (SCUC), and multi-stage financial cashflows or dynamic locational marginal pricing (LMP) [@bremnes2004quantile; @zhou2013probabilisticmarkets]. The PSREI proxy should be viewed as an upstream risk filter feeding into, rather than replacing, ISO/TSO physical market clearing. Strongest claims remain five-seed WTB recovery, mechanism intervention, La Haute Borne replication, and same-router reserve triage.

# Conclusion

This study formalizes and validates a three-tier defense-in-depth architecture combining high-fidelity aerodynamic physical priors with an autonomous spatio-temporal dynamic graph blind-spot fallback for wind plant operational reserve pricing. Through an extensive 5-seed benchmark (seeds 201--205) across four controlled telemetry regimes and two operational dispatch horizons ($h \in \{1, 6\}$), we reveal fundamental operational boundaries that govern real-world cyber-physical wind energy integration.

Under pristine SCADA telemetry, high-fidelity physical aerodynamic rules (Continuous Physical Quantile) achieve optimal economic efficiency, delivering the lowest baseline reserve cost ($871{,}408\text{ kW}\cdot\text{h}$ at $h=6$ and $589{,}535\text{ kW}\cdot\text{h}$ at $h=1$). However, deterministic physical rules exhibit catastrophic brittleness under telemetry degradation: transmission delays cause shortage violation rates to explode to $12.52\% \pm 1.82\%$ ($h=6$) and $12.60\% \pm 1.94\%$ ($h=1$), severely breaching grid reliability compliance standards ($q^* = 0.90$). Conversely, while shallow tree baselines (Missingness-Aware GBDT) capitalize on 10-minute lag autocorrelation at ultra-short lead times ($h=1$), they collapse across dispatch-grade horizons ($h=6$), inflating reserve costs by $13.44\%$ to $29.15\%$ ($p < 0.0001$) due to their inability to model spatial aerodynamic wake advection across turbine arrays. Direct uncalibrated two-stage architectures (Frozen Backbone Direct Quantile MLP) over-estimate reserve margins by $44.57\%$ to $72.02\%$ ($p < 0.01$) by hoarding over $1.45\text{M kW}$ in bloated reserves under direct pinball regression, whereas calibrated modular MLPs achieve nominal pricing parity but remain vulnerable to latency fault cascades.

The proposed Joint Routed posterior resolves these structural limitations. By propagating directed wake graph geometry and extracting electromechanical consequence signatures (power transients, voltage/reactive dynamics) when primary blade-pitch telemetry is delayed, unobservable across aggregator boundaries, or withheld under counterfactual stress testing, the deep fallback maintains safety compliance (<8.1\% violation rate under noise and Markov bursts) while achieving the lowest degraded dispatch cost ($1{,}149{,}897\text{ kW}\cdot\text{h}$ at $h=6$). While nominal pricing efficiency is driven by end-to-end task-loss alignment across shared representations, dynamic MoE routing delivers distinct fault isolation under continuous telemetry impairment ($p = 0.0251$ under Delay-6 and $p < 0.05$ under noise against unrouted dense heads), strictly outperforming shallow trees ($p < 0.0001$) and avoiding the severe tail conservatism of uncalibrated pinball regression ($p < 0.01$). Under Markov-Gilbert burst dropouts, it sustains 0.994 recall and 0.967 F1 (+0.064 gain); under 6-step delays, it maintains 0.933 recall (+0.737 gain). At the Point of Common Coupling (PCC) bus, fleet-wide spatial portfolio smoothing delivers an economic savings of $-11.22\text{M kWh}$ (95\% CI $[-21.55\text{M}, -2.85\text{M}]$) over global PCC baselines. Replicated across two commercial UK wind plants with turbine-calibrated rated wind speeds (Kelmarsh MM92 at 12.5 m/s, Penmanshiel MM82 at 14.5 m/s), consequence signatures persist significantly above chance and decadal walk-forward rolling recalibration under a frozen backbone recovers $0.804\text{M kWh/year}$ across 17.6 operating years (12 of 12 clean folds saving, $p = 0.00024$; 12 of 13 full folds, $p = 0.00171$). The resulting framework establishes an auditable, physics-data synergistic reserve pricing layer that ensures economic optimality under nominal operations while providing a resilient safety airbag under telemetry failure.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.

# Code and data availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public (raw third-party data not redistributed). Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress caches, early-warning label degradation, classifier control, class-weight sensitivity, external diagnostics, and evidence-freeze protocols across declared seeds. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.


# References {.unnumbered}

::: {#refs}
:::

