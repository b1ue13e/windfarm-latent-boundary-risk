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
  - \linespread{0.94}
  - \setlist[itemize]{leftmargin=1.4em,nosep}
  - \setlist[enumerate]{leftmargin=1.4em,nosep,itemsep=0.2ex}
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\begin{list}{}{\fontsize{5.0pt}{5.7pt}\selectfont\setlength{\itemindent}{0pt}\setlength{\leftmargin}{0pt}\setlength{\parsep}{0pt}\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}}{\end{list}}}
  - \AtBeginDocument{\renewcommand{\CSLBlock}[1]{#1\par}}
  - \AtBeginDocument{\setlength{\csllabelwidth}{1.8em}}
  - \AtBeginDocument{\renewcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth - \csllabelwidth\relax}{\fontsize{5.0pt}{5.7pt}\selectfont\ignorespaces#1}}}
  - \AtBeginDocument{\renewcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{\fontsize{5.0pt}{5.7pt}\selectfont\strut#1}}}
  - \makeatletter
  - \def\section{\@startsection{section}{1}{\z@}{0.85ex plus 0.2ex minus 0.15ex}{0.3ex plus 0.1ex}{\normalfont\footnotesize\bfseries\centering\scshape}}
  - \def\subsection{\@startsection{subsection}{2}{\z@}{0.6ex plus 0.15ex minus 0.1ex}{0.2ex plus 0.1ex}{\normalfont\normalsize\itshape}}
  - \def\subsubsection{\@startsection{subsubsection}{3}{\z@}{0.45ex plus 0.15ex minus 0.1ex}{0.15ex plus 0.08ex}{\normalfont\footnotesize\itshape}}
  - \makeatother
  - \setcounter{topnumber}{4}
  - \setcounter{bottomnumber}{4}
  - \setcounter{totalnumber}{8}
  - \setcounter{dbltopnumber}{4}
  - \setlength{\abovedisplayskip}{2pt plus 1pt minus 1pt}
  - \setlength{\belowdisplayskip}{2pt plus 1pt minus 1pt}
  - \setlength{\abovedisplayshortskip}{1pt plus 1pt}
  - \setlength{\belowdisplayshortskip}{1pt plus 1pt}
  - \setlength{\floatsep}{2.0pt plus 1pt minus 1pt}
  - \setlength{\textfloatsep}{2.0pt plus 1pt minus 1pt}
  - \setlength{\intextsep}{2.0pt plus 1pt minus 1pt}
  - \setlength{\dblfloatsep}{2.0pt plus 1pt minus 1pt}
  - \setlength{\dbltextfloatsep}{2.0pt plus 1pt minus 1pt}
  - \setlength{\abovecaptionskip}{2pt plus 1pt minus 1pt}
  - \setlength{\belowcaptionskip}{1pt plus 1pt minus 1pt}
  - \renewcommand{\topfraction}{0.95}
  - \renewcommand{\bottomfraction}{0.95}
  - \renewcommand{\textfraction}{0.05}
  - \renewcommand{\floatpagefraction}{0.85}
  - \renewcommand{\dbltopfraction}{0.95}
  - \renewcommand{\dblfloatpagefraction}{0.85}
---

\title{Reliability Breakdown of Wind Turbine Operating Reserve Rules under Stale SCADA Telemetry and Boundary-Risk Posterior Diagnostics}

\author{%
\IEEEauthorblockN{Junyu Li and Juntao Du\IEEEauthorrefmark{1}}
\IEEEauthorblockA{School of Statistics and Applied Mathematics,
Anhui University of Finance and Economics, Bengbu 233030, China\\
\IEEEauthorrefmark{1}Corresponding author: \texttt{dujuntao@aufe.edu.cn}}
}

\maketitle

\begin{abstract}
Operating reserve sizing near the transition from maximum power point tracking (MPPT) to blade-pitch regulation relies heavily on accurate turbine operational state awareness. However, industrial Supervisory Control and Data Acquisition (SCADA) telemetry streams across distributed wind plants are routinely subject to transmission latency, packet dropouts, and unobservable pitch registers. We establish that while deterministic aerodynamic rules (continuous soft-pitch quantiles based on manufacturer power curves) deliver optimal reserve pricing efficiency under pristine telemetry ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, with well-calibrated violation rates of $\sim 6.8\%$), they exhibit severe reliability breakdown under controlled communication latency. When subject to a 6-step ($60\text{ min}$) transmission lag, clean-calibrated physical quantile rules experience a catastrophic surge in shortage violation rates to $24.0\% \pm 1.7\%$ ($h=1$) and $12.2\% \pm 1.2\%$ ($h=6$), severely breaching the nominal 10\% violation target ($q^* = 0.90$) set by the reserve screening index. Evaluated across a five-seed benchmark on the 134-turbine WTB plant under strictly frozen validation calibration, state-conditional recalibration of physical rules recovers violation to $10.7\%$ and cuts shortage from $127.6\text{ MWh}$ to $57.0\text{ MWh}$ ($55.3\%$ reduction, absorbing $\sim 95.8\%$ of total recoverable shortage), while jointly-learned spatio-temporal boundary-risk posteriors further reduce shortage to $53.9\text{ MWh}$ (a combined $57.7\%$ reduction, with a $5.4\%$ marginal gain over identically-calibrated physics) and double boundary detection recall over collapsed physical rules ($0.416$ vs. $0.196$). Crucially, our empirical audit establishes four structural boundaries: (1) learned posteriors do not provide an unconditional compliance guarantee under multi-step delays, yielding an empirical test violation rate of $10.6\% \pm 1.1\%$ (breaching the $10.0\%$ target in 4 of 5 seeds); (2) capacity-matched Dense and Mixture-of-Experts (MoE) architectures achieve statistical parity under Clean telemetry (cost ratio $1.045$, $p=0.380$), while decoupled modular representations (Frozen Backbone + Residual Quantile) achieve lower reserve cost ($1.284\text{M}$ vs. $1.412\text{M kW}\cdot\text{h}$) and compliant tail coverage ($9.7\%$ violation), highlighting that diagnostic reserve benefits are governed by global spatio-temporal feature representations and decoupled residual calibration rather than dynamic routing mechanisms, eliminating causal claims about multi-task supervision while preparing for explicit single-task versus multi-task representation ablations; (3) we delineate the three-way operational boundaries governing simple recalibration, learned representation, and conservative margin safeguards: under severe 60-min delay, condition-matching recalibration recovers fleet-average violation below the 10.0% target (9.46% for physics at 1.229M, 9.55% for Frozen at 1.284M, 9.62% for Routed at 1.274M), refuting prior claims of unconditional collapse, while inter-seed compliance remains strictly bounded at 3/5 seeds (60%), and uniform margin inflation Pareto-dominates heuristic selective abstention under missing pitch; and (4) cross-farm zero-shot evaluation exhibits marked directional asymmetry and model sensitivity across commercial plants: Kelmarsh-to-Penmanshiel achieves high alignment (NMI $0.752$--$0.770$), whereas Penmanshiel-to-Kelmarsh drops to $0.341$--$0.505$ (pooled mean NMI $0.557$), bounding reliable deployment to local chronological retraining (ENGIE La Haute Borne, NMI $= 0.941$). All reserve evaluations reflect an upstream Penalized Reserve-Shortfall Energy Index (PSREI) proxy rather than wholesale market cashflow settlements. This work re-anchors data-driven models from autonomous fallbacks into rigorous, accountable risk-diagnostic instruments for stale SCADA environments.
\end{abstract}

\begin{IEEEkeywords}
Wind turbine operating reserve; SCADA telemetry degradation; transmission latency; aerodynamic power curve; reliability breakdown; boundary-risk posterior; selective decision abstention; MPPT-to-pitch transition.
\end{IEEEkeywords}

# Introduction

Wind-farm reserve screening near the transition from maximum power point tracking (MPPT) to blade-pitch control requires precise identification of the active turbine operating regime. This operational boundary matters acutely because wind-power forecasting is economically coupled to ramp exposure, operating reserve sizing, and non-convex imbalance shortfall penalties rather than to aggregate RMSE alone [@pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. In the MPPT aerodynamic region (Region 2), active power responds cubically to wind-speed variations. Once blade-pitch control becomes active near rated wind speed (Region 3), aerodynamic rotor efficiency is actively curtailed to clamp generation at nameplate capacity. A small unpredicted wind-speed deviation near rated operation can therefore thrust a turbine across a control cliff, generating severe power shortfall penalties even when fleet-average forecast errors appear benign.

In industrial wind plant operations, however, continuous and pristine SCADA telemetry streams cannot be guaranteed. Telemetry channels across distributed turbine networks are routinely afflicted by communication packet dropouts, multi-step transmission latency (e.g., 10 to 60 minutes), asynchronous timestamp misalignment, and sensor calibration noise [@tautzweinert2017scada]. In the commercial Kelmarsh wind plant, for example, 99.6\% of turbine status events carry second-level timestamps that fall strictly between 10-minute SCADA grid points, confirming that confirming-stream SCADA events arrive asynchronously rather than aligned with regular 10-minute dispatch intervals. To evaluate reserve reliability under severe telemetry bottlenecks beyond asynchronous arrival, this paper conducts controlled multi-step transmission latency stress tests (e.g., 10 to 60 minutes). Furthermore, in non-intrusive aggregator, Virtual Power Plant (VPP), or Transmission System Operator (TSO) pre-dispatch triage settings, internal turbine blade-pitch registers are frequently unobservable due to commercial boundaries, proprietary OEM protocol firewalls, or legacy substation gateways. When grid operators must clear reserve margins before real-time delivery, relying on delayed or unobservable confirming telemetry poses severe reliability risks.

Prior engineering practice and research have largely treated physical aerodynamic models and data-driven forecasters as competing alternatives without mapping their operational failure boundaries under degraded communications. On the one hand, high-fidelity physical priors—such as continuous soft-pitch rules based on manufacturer power curves—exhibit exceptional economic efficiency under ideal, pristine SCADA observations, achieving the lowest baseline reserve cost ($589{,}535\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$). However, pure physical rules exhibit a **catastrophic reliability breakdown**: when SCADA telemetry experiences communication delays or sensor noise, stale pitch and anemometer readings cause deterministic threshold logic to misclassify operating states. Under a 6-step ($60\text{ min}$) transmission lag, clean-calibrated physical rule violation rates explode to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, severely breaching the nominal 10\% violation target ($q^* = 0.90$) set by the reserve screening index. On the other hand, shallow machine-learning baselines like Missingness-Aware GBDT capitalize on 10-minute lag wind-speed autocorrelation at ultra-short horizons ($h=1$), but undergo a severe breakdown at dispatch-grade horizons ($h=6$), inflating reserve costs by $13.44\%$ to $29.15\%$ ($p < 0.0001$) because tabular models cannot capture spatial wake advection across turbine arrays.

To address this challenge without over-promising autonomous safety, this paper investigates the **reliability breakdown boundaries of physical operating reserve rules under SCADA telemetry staleness and evaluates jointly-learned boundary-risk posteriors as relative mitigators and diagnostic signals**. Rather than framing neural networks as an unconditional "safety airbag" or asserting the architectural necessity of dynamic Mixture-of-Experts (MoE) routing, we demonstrate that physical rules are the rigorous empirical optimum when telemetry is fresh, while joint spatio-temporal learning provides vital relative risk mitigation when telemetry is stale. By capturing cross-sensor electromechanical transients (active power fluctuations, reactive dynamics, and dynamic wake geometry), learned posteriors preserve operational state awareness and curtail severe shortage energy, even when primary pitch channels are delayed, missing, or unobservable across aggregator boundaries. Crucially, through a frozen-calibration protocol on the 134-turbine WTB benchmark, we show that capacity-matched Dense and MoE heads achieve statistical parity in degraded pricing, while decoupled modular models achieve lower total cost and compliant tail coverage, demonstrating that operational diagnostic reserve benefits are governed by global spatio-temporal feature representations and decoupled residual calibration rather than dynamic routing mechanisms, eliminating unproven causal claims regarding multi-task supervision while explicitly motivating the single-task versus multi-task ablation.

This paper makes four bounded, verifiable contributions:
1. **Reliability Breakdown of Deterministic Physical Rules:** We expose the systematic breakdown of aerodynamic power-curve quantile rules under telemetry latency. Across 5 seeds on the 134-turbine WTB plant, a 6-step ($60\text{ min}$) latency causes clean-calibrated physical violation rates to surge from $6.8\%$ to $24.0\% \pm 1.7\%$ ($h=1$) and $12.2\%$ ($h=6$), severely breaching the nominal 10% violation target.
2. **Decisive Benchmark and MoE De-mystification:** Under causal feeds with validation calibration frozen before testing, physical rules are optimal under clean feeds ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$). Under stale feeds, state-conditional calibration absorbs most reliability loss ($10.7\%$ violation, $57.0\text{ MWh}$ shortage), while learned posteriors reach $10.6\% \pm 1.1\%$ violation and $53.9\text{ MWh}$ shortage. Decoupled modular architectures (Frozen Backbone + Residual Quantile) achieve superior performance ($1.284\text{M kW}\cdot\text{h}$, $9.68\%$ violation), establishing that diagnostic reserve benefits are driven by spatio-temporal feature representations and decoupled residual calibration rather than dynamic MoE routing.
3. **Disentangled Diagnostics & Safeguard Boundaries:** Disentangling calibration adaptation from learned representation reveals that state-conditional calibration recovers $95.8\%$ of recoverable shortage energy ($127.6 \to 57.0\text{ MWh}$, a $55.3\%$ reduction), while learned posteriors add a $5.4\%$ reduction ($57.0 \to 53.9\text{ MWh}$, combined $57.7\%$) and double state recall over collapsed physical rules ($0.416$ vs. $0.196$ under Delay-6). While condition-matching recalibration restores fleet-average violation below the $10.0\%$ target (with physics reaching $1.229\text{M}$ and $9.46\%$), inter-seed compliance is strictly bounded at $3/5$ seeds ($60\%$). We evaluate selective decision abstention against random and uniform margin inflation controls, proving that heuristic entropy scores fail to isolate tail risk and that uniform margin inflation Pareto-dominates selective rejection under missing pitch.
4. **Empirical Deployment Boundaries:** We delineate empirical generalization limits across commercial farms: mechanism replication holds under local retraining on ENGIE La Haute Borne (routing NMI $= 0.941$, ARI $= 0.971$), but zero-shot cross-farm transfer exhibits directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled $0.557$). All reserve savings represent an upstream PSREI operational risk proxy ($\rho=10$).

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

## Operating-Boundary Physical Anchors and Power-Curve Baseline

The supervisory anchor is not applied indiscriminately across all operating states. It is anchored where the physical aerodynamic interpretation is clearest, while ambiguous samples remain governed by prediction loss and spatial regularisation. This design provides the physical reference anchor: **a high-fidelity aerodynamic prior** calibrated to the manufacturer specifications of each turbine model [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada].

**Aerodynamic operating regimes and turbine-calibrated anchors:** In wind turbine control engineering, the transition from Maximum Power Point Tracking (Region 2) to active blade-pitch regulation (Region 3) is governed by the turbine's aerodynamic power-coefficient curve $C_p(\lambda, \theta)$ and its rated wind speed $u_{\mathrm{rated}}$. Below rated wind speed, blades maintain a minimum pitch angle to maximise aerodynamic capture; above rated wind speed, the pitch actuator rotates the blades to shed excess aerodynamic power and protect the generator.

Let $\bar{p}_{i,t} = \frac{1}{3}\sum_{k=1}^3 p^{(k)}_{i,t}$ denote the average blade pitch angle across all three blades for turbine $i$ at dispatch anchor time $t$. Writing $w_{i,t}=\texttt{Wspd}_{i,t}$ for anemometer wind speed, the declared operating boundary is defined with turbine-calibrated cut-in threshold $u_{\mathrm{idle}}$, rated wind speed $u_{\mathrm{rated}}$, and pitch-activation angle $p_{\mathrm{th}}$:

$$
R_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transitional/ambiguous)}.
\end{cases}
$$

Crucially, aerodynamic rated wind speeds are calibrated to the specific turbine technology at each wind plant: WTB (134 turbines: $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=10.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=2.0^\circ$), Kelmarsh (6 MM92 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=12.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$), Penmanshiel (15 MM82 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$), and ENGIE La Haute Borne (4 MM82 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$).

Only the first three well-defined regimes are used in direct supervisory alignment. Transitional samples are retained for evaluation but masked out of anchor supervision via $M_{i,t} = \mathbf{1}[R_{i,t} \neq 3]$.

These thresholds define the **Aerodynamic Power-Curve Baseline**: when SCADA telemetry is complete and intact, continuous soft-pitch quantiles derived from these anchors achieve optimal baseline reserve sizing. When telemetry degrades through communication latency or sensor corruption, however, this deterministic rule experiences severe reliability breakdown, requiring learned diagnostic representations.

**ERA5 observability contrast:** ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the wind plant control-boundary accountability task.

## Spatio-Temporal Dynamic Wake Graph and Boundary-Risk Posterior Formulation

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

```{=latex}
\begin{align}
\mathbf{z}_{i,t} &= \mathrm{MLP}_{\mathrm{gate}}\!\left(\left[\mathbf{h}_{i,t};\mathbf{a}_{i,t}\right]\right), \quad \mathbf{g}_{i,t} = \mathrm{softmax}\!\left(\mathbf{z}_{i,t}/\tau\right),\\
\hat{\mathbf{y}}_{i,t+1:t+P} &= \sum\nolimits_{e=1}^{E} g_{i,t}^{(e)} f_e(\mathbf{h}_{i,t}).
\end{align}
```

**Cross-sensor electromechanical diagnostic mechanism:** The operational utility of the spatio-temporal representation is its ability to infer operating states from non-pitch electromechanical signatures when primary telemetry is delayed or missing. When blade-pitch telemetry $\bar{p}_{i,t}$ suffers packet loss, transmission latency, or protocol unobservability (such as across third-party aggregator or VPP boundaries), the dynamic graph encoder leverages active power transients ($\texttt{Patv}$), terminal voltage fluctuations, reactive dynamics, and upstream wake propagation to reconstruct the probability of active blade-pitch regulation. In nominal operation, the boundary-risk head ingests $\mathbf{a}_{i,t}^{\mathrm{WTB}} = [\texttt{Wspd}_{i,t}, \texttt{Pab\_mean}_{i,t}, s^{\mathrm{wake}}_{i,t}, \texttt{Patv}_{i,t}]$. Under telemetry impairment, the learned spatio-temporal representation provides relative mitigation, curbing severe shortage volumes that compromise deterministic rules.

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

## Operational Reserve Screening, PCC Portfolio Smoothing, & Multi-Horizon Dispatch Protocol

The operational utility of boundary-aware routing lies in pre-dispatch decision support: screening imbalance risks and sizing upward spinning reserves to prevent costly shortage penalties [@bremnes2004quantile; @nielsen2006quantile].

**Two-level hierarchical grid dispatch interface:** To formally delineate the operational boundary of this work, we distinguish a two-level grid dispatch hierarchy:
1. *Level 1 (Local Pre-Dispatch Risk Filtering & Screening Layer, Paper Scope):* Operating at the wind plant energy management system (EMS) or aggregator terminal, this local layer ingests SCADA telemetry, forecasts spatio-temporal power, diagnoses operational regime boundaries under telemetry degradation, and sizes pre-dispatch reserve allocations to minimize unhedged imbalance exposure entering real-time balancing markets.
2. *Level 2 (Grid-Level Physical Clearing & Network-Constrained Dispatch, Downstream Interface):* Managed by the transmission system operator (TSO) or regional grid dispatcher, this downstream layer aggregates wind-plant schedule offers and reserve quantities to execute network-constrained economic dispatch (NCED), security-constrained unit commitment (SCUC), and full Alternating Current Optimal Power Flow (AC-OPF) subject to bus voltage security, transmission thermal limits, and bulk system spinning reserve margins.
Our formulation is strictly bounded to Level 1 pre-dispatch risk screening proxies. We explicitly abstract away network power-flow equations, nodal price arbitrage, and multi-stage financial cashflow settlements, focusing on plant-level imbalance risk mitigation.

**Penalized Reserve-Shortfall Energy metric formulation:** For scheduled point forecast $\hat{y}_{i,t}$ and realized generation $y_{i,t}$, over-forecast shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. Sizing reserve margin $r_b$ incurs a reserve provision energy equivalent $r_b \Delta t$ and an asymmetric shortage penalty $\rho \max(s_{i,t} - r_b, 0) \Delta t$. For penalty ratio $\rho$, the total operational proxy metric is formalized as the **Penalized Reserve-Shortfall Energy Index (PSREI)** in $\text{kW}\cdot\text{h}$ (evaluated here at grid proxy ratio $\rho = 10$):

\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b + \rho \max(s_{i,t}-r_b,0) \right]\Delta t.
\end{equation}

The first-order optimality condition $\frac{\partial}{\partial r}\mathbb{E}[C] = 1 - \rho\Pr[s > r] = 0$ yields the optimal critical fractile $q^*(\rho) = 1 - 1/\rho$. In standard reserve screening with $\rho = 10$, the required quantile is $q^*(10) = 0.90$, establishing a nominal 10% violation target set by the reserve screening index.

**Point of Common Coupling (PCC) spatial portfolio smoothing:** Power delivered to the bulk grid is metered at the Point of Common Coupling (PCC) bus: $P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}$ and $R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}$. Fleet-wide spatial aggregation induces a portfolio smoothing effect: uncorrelated local turbulence and turbine-level prediction errors cancel out across the array. Evaluating reserve sizing at the PCC verifies whether learned boundary risk survives spatial cancellation to deliver net plant-level economic value.

**Multi-horizon dispatch evaluation:** Power systems operate across multiple decision timescales. We evaluate two distinct operational horizons: (1) \textbf{Immediate dispatch} ($h=1$, 10-min ahead), representing real-time automatic generation control (AGC) dominated by autocorrelation; and (2) \textbf{Operational dispatch} ($h=6$, 1-hour ahead), representing intra-day clearing and storage scheduling where spatial wake dynamics and weather transitions are paramount.

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

To stress-test model resilience under adverse field conditions, we formalize four controlled telemetry regimes across all 5 seeds (201--205): (1) \textbf{Clean (Nominal):} uncorrupted SCADA telemetry; (2) \textbf{Delay-6 (Transmission Lag):} 6-step ($60\text{ min}$) latency on wind-speed and pitch-angle streams, simulating industrial buffer backlogs and asynchronous ingestion; (3) \textbf{Sensor Noise:} additive zero-mean Gaussian perturbations on wind speed ($\sigma = 1.0\text{ m s}^{-1}$) and pitch angle ($\sigma = 2.0^\circ$), simulating calibration drift and sensor jitter; and (4) \textbf{Markov-Gilbert Burst Drops:} two-state discrete Markov chain ($p_{GB} = 0.08, p_{BB} = 0.75, d \le 6$) simulating bursty communication blackouts.

Fig. 1 illustrates the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors: (A) WTB layout with wake cone geometry; (B) ERA5 patch with sensible heat flux; (C) WTB operating regimes in $(Wspd, Pab_{\mathrm{mean}})$ plane with MPPT-to-pitch boundary; (D) ERA5 thermodynamic regimes in $(sshf, \Delta sshf)$ plane.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=58% }

# Evidence and Operational Boundary Diagnosis

The empirical evaluation is organized around our three-tier defense-in-depth framework, contrasting high-fidelity physical aerodynamic priors against deep spatio-temporal graph fallbacks across multi-horizon dispatch environments. All neural models, shallow tree baselines, and physical quantile rules are evaluated across five declared random seeds (201--205) under strict, automated anti-tampering verification gates (zero directory leakage, full telemetry regime completeness, cardinality $N=5$, and exact floating-point checksums).

## Multi-Horizon 5-Seed Operational Dispatch Benchmark ($h=6$, 1-Hour Ahead Dispatch)

Table~\ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) across 134 turbines over the 35-day test split. Table~\ref{tab:h6-paired} reports seed-paired cost differences $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, where positive values denote economic savings delivered by Joint Routed, along with 95\% bootstrap confidence intervals.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{6.5pt}{7.5pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Cross-Seed Multi-Regime Operational Dispatch Benchmark under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data.}
\label{tab:h6-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & \shortstack{Penalized Reserve-Shortfall\\Energy (kW$\cdot$h, Proxy at $\rho=10$)} & Violation Rate & Reserve (kW) & Shortage (kW$\cdot$h) & Pinball Loss \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{881{,}367 \pm 95{,}741}$ & $6.81\% \pm 1.13\%$ & $653{,}738 \pm 72{,}557$ & $22{,}763 \pm 4{,}013$ & $31.41 \pm 2.66$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}649{,}721 \pm 285{,}682$ & $0.58\% \pm 0.26\%$ & $1{,}630{,}572 \pm 293{,}346$ & $1{,}915 \pm 958$ & $64.62 \pm 12.05$ \\
 & Global Quantile & $998{,}988 \pm 107{,}360$ & $6.46\% \pm 1.31\%$ & $771{,}304 \pm 95{,}661$ & $22{,}768 \pm 4{,}854$ & $36.50 \pm 3.41$ \\
 & Joint Dense Head & $991{,}181 \pm 110{,}211$ & $6.54\% \pm 1.04\%$ & $761{,}480 \pm 94{,}244$ & $22{,}970 \pm 4{,}121$ & $36.16 \pm 3.58$ \\
 & \textbf{Joint Routed (Ours)} & $959{,}027 \pm 103{,}290$ & $7.10\% \pm 1.17\%$ & $707{,}249 \pm 91{,}305$ & $25{,}178 \pm 4{,}816$ & $34.77 \pm 3.16$ \\
 & Missingness-Aware GBDT & $1{,}238{,}603 \pm 112{,}051$ & $4.50\% \pm 0.73\%$ & $1{,}085{,}168 \pm 118{,}015$ & $15{,}343 \pm 2{,}870$ & $46.85 \pm 3.48$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $1{,}136{,}466 \pm 84{,}101$ & $12.20\% \pm 1.25\%^{\dagger}$ & $662{,}335 \pm 73{,}483$ & $47{,}413 \pm 3{,}091$ & $38.85 \pm 2.06$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}682{,}251 \pm 284{,}323$ & $1.20\% \pm 0.52\%$ & $1{,}651{,}979 \pm 297{,}715$ & $3{,}027 \pm 1{,}594$ & $62.15 \pm 11.70$ \\
 & Global Quantile & $1{,}180{,}603 \pm 91{,}754$ & $10.85\% \pm 1.55\%^{\dagger}$ & $780{,}916 \pm 96{,}853$ & $39{,}969 \pm 6{,}087$ & $40.73 \pm 2.43$ \\
 & Joint Dense Head & $1{,}179{,}859 \pm 95{,}268$ & $11.04\% \pm 1.22\%^{\dagger}$ & $773{,}103 \pm 94{,}462$ & $40{,}676 \pm 4{,}788$ & $40.70 \pm 2.66$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{1{,}163{,}593 \pm 91{,}299}$ & $11.82\% \pm 1.64\%^{\dagger}$ & $720{,}015 \pm 92{,}196$ & $44{,}358 \pm 7{,}341$ & $40.01 \pm 2.54$ \\
 & Missingness-Aware GBDT & $1{,}320{,}003 \pm 93{,}135$ & $8.36\% \pm 0.97\%$ & $1{,}030{,}858 \pm 114{,}266$ & $28{,}915 \pm 4{,}469$ & $46.68 \pm 2.45$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $998{,}273 \pm 106{,}253$ & $7.59\% \pm 0.95\%$ & $746{,}697 \pm 82{,}474$ & $25{,}158 \pm 3{,}968$ & $33.97 \pm 2.78$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}639{,}909 \pm 242{,}922$ & $0.80\% \pm 0.28\%$ & $1{,}618{,}439 \pm 249{,}374$ & $2{,}147 \pm 953$ & $60.62 \pm 9.85$ \\
 & Global Quantile & $1{,}053{,}552 \pm 114{,}150$ & $7.48\% \pm 1.48\%$ & $802{,}361 \pm 99{,}513$ & $25{,}119 \pm 5{,}822$ & $36.26 \pm 3.24$ \\
 & Joint Dense Head & $1{,}048{,}083 \pm 115{,}181$ & $7.63\% \pm 1.13\%$ & $792{,}472 \pm 92{,}391$ & $25{,}561 \pm 4{,}643$ & $36.04 \pm 3.28$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{1{,}027{,}077 \pm 114{,}317}$ & $7.62\% \pm 1.09\%$ & $769{,}864 \pm 106{,}672$ & $25{,}721 \pm 3{,}963$ & $35.16 \pm 3.19$ \\
 & Missingness-Aware GBDT & $1{,}314{,}640 \pm 129{,}158$ & $4.66\% \pm 0.80\%$ & $1{,}160{,}329 \pm 137{,}650$ & $15{,}431 \pm 3{,}099$ & $47.11 \pm 3.87$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{907{,}871 \pm 96{,}820}$ & $7.20\% \pm 1.15\%$ & $663{,}875 \pm 73{,}821$ & $24{,}400 \pm 4{,}106$ & $31.59 \pm 2.61$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}680{,}339 \pm 289{,}602$ & $0.57\% \pm 0.25\%$ & $1{,}660{,}135 \pm 298{,}104$ & $2{,}020 \pm 992$ & $64.38 \pm 12.00$ \\
 & Global Quantile & $1{,}030{,}131 \pm 108{,}592$ & $6.87\% \pm 1.39\%$ & $785{,}305 \pm 97{,}397$ & $24{,}483 \pm 5{,}104$ & $36.78 \pm 3.35$ \\
 & Joint Dense Head & $1{,}020{,}078 \pm 112{,}195$ & $6.90\% \pm 1.07\%$ & $775{,}899 \pm 96{,}235$ & $24{,}418 \pm 4{,}246$ & $36.35 \pm 3.57$ \\
 & \textbf{Joint Routed (Ours)} & $990{,}625 \pm 104{,}487$ & $7.51\% \pm 1.22\%$ & $720{,}858 \pm 92{,}754$ & $26{,}977 \pm 5{,}183$ & $35.10 \pm 3.10$ \\
 & Missingness-Aware GBDT & $1{,}261{,}941 \pm 112{,}754$ & $4.88\% \pm 0.75\%$ & $1{,}094{,}730 \pm 120{,}612$ & $16{,}721 \pm 3{,}298$ & $46.62 \pm 3.40$ \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\tiny $^{\dagger}$Exceeds nominal 10\% violation target ($q^* = 0.90$). Bold numbers denote lowest cost. \textbf{Protocol Attribution:} Reports the \textit{Clean-Calibrated Operational Protocol} at $h=6$ (thresholds frozen on clean validation data); Continuous Physical Quantile collapses to 12.20\% violation under Delay-6. For the \textit{State-Conditional Validation-Calibrated Protocol} at immediate horizon ($h=1$), see Section~\ref{sec:branch-b}, where clean-calibrated physical rules collapse to 24.0\% violation under Delay-6 while state-conditional calibration mitigates violations to 10.7\% (physical) and 10.6\% (joint model). Test-set iso-multipliers ($\gamma_{\text{iso, test}}$) serve strictly as post-hoc diagnostics. $^{\ddagger}$Direct pinball regression on frozen embeddings exhibits severe tail conservatism (>1.63M kW reserve, <1.2\% violation). For calibrated modular baselines (Cascaded Frozen MLP $15.528\text{M} \pm 1.599\text{M}$ vs Joint Routed 16.065M in statistical parity), see Section~\ref{sec:branch-d}.}
\end{tabular*}
\end{table*}
```

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.2pt}{6.0pt}\selectfont
\setlength{\tabcolsep}{0.6pt}
\renewcommand{\arraystretch}{0.75}
\caption{Seed-Paired Difference in Penalized Reserve-Shortfall Energy against Joint Routed ($h=6$, $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, positive indicates Joint Routed saves energy/cost at $\rho=10$).}
\label{tab:h6-paired}
\begin{tabularx}{\columnwidth}{@{}llcc>{\raggedright\arraybackslash}X@{}}
\toprule
Regime & Baseline Model & $\Delta$ Cost (kW$\cdot$h) & 95\% Bootstrap CI & Sig. \& Operational Verdict \\
\midrule
\textbf{Clean} & Global Quantile & +39,962 & [+12,556, +67,367] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$77,659 & [$-$106,175, $-$49,143] & Yes (Lower Clean) \\
 & Missingness GBDT & +279,576 & [+249,539, +309,613] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct MLP & +690,695 & [+448,769, +932,621] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +32,154 & [$-$1,148, +65,456] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Delay-6} & Global Quantile & +17,010 & [+3,486, +30,535] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$27,126 & [$-$46,907, $-$7,346] & Viol. Exceeded ($12.52\%$) \\
 & Missingness GBDT & +156,411 & [+140,004, +172,817] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct MLP & +518,658 & [+307,212, +730,104] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +16,267 & [+7,131, +25,402] & \textbf{Yes} ($p = 0.0251$) \\
\midrule
\textbf{Noise} & Global Quantile & +26,475 & [+9,121, +43,828] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$28,804 & [$-$47,555, $-$10,053] & Viol. Elevated ($8.17\%$) \\
 & Missingness GBDT & +287,563 & [+248,847, +326,279] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct MLP & +612,832 & [+413,733, +811,931] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +21,006 & [+2,419, +39,594] & \textbf{Yes} ($p < 0.05$) \\
\midrule
\textbf{Markov} & Global Quantile & +39,506 & [+15,961, +63,052] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$82,754 & [$-$111,026, $-$54,482] & Yes (Lower Clean) \\
 & Missingness GBDT & +271,316 & [+245,044, +297,588] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct MLP & +689,714 & [+448,689, +930,739] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +29,453 & [$-$2,874, +61,779] & No (Parity, CI crosses 0) \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\tiny Note: Under Clean and Markov regimes, the 95\% bootstrap CI against Joint Dense Head crosses zero, establishing statistical parity driven by end-to-end task-loss alignment. The distinct empirical value of dynamic MoE routing is localized to continuous telemetry impairment (Delay-6 $p=0.0251$, Noise $p<0.05$).
\end{table}
```

### Branch A: MoE Dynamic Routing vs. Unrouted Dense Representations
A key architectural question is whether dynamic MoE routing confers essential operational value over unrouted dense heads of matched capacity. Under nominal Clean conditions, Joint Routed ($959{,}972 \pm 89{,}006\text{ kW}\cdot\text{h}$ at $h=6$; $660{,}990 \pm 80{,}749\text{ kW}\cdot\text{h}$ at $h=1$) and Joint Dense Head ($1{,}009{,}265 \pm 77{,}336\text{ kW}\cdot\text{h}$ at $h=6$; $690{,}614 \pm 71{,}031\text{ kW}\cdot\text{h}$ at $h=1$) achieve statistical parity: at $h=1$, the Dense/MoE cost ratio is $1.045$, and the seed-paired bootstrap 95% CI on cost difference ($+29{,}624\text{ kW}\cdot\text{h}$) crosses zero ($[-53{,}774, +113{,}023]\text{ kW}\cdot\text{h}$, $p=0.380$; Table~\ref{tab:h6-paired} at $h=6$ also crosses zero $[-1{,}148, +65{,}456]\text{ kW}\cdot\text{h}$), as does the Markov regime ($[-46{,}422, +139{,}671]\text{ kW}\cdot\text{h}$, $p=0.237$). Under persistent 6-step latency (Delay-6, $h=1$), Joint Routed yields a modest cost improvement over Joint Dense ($1{,}412{,}321$ vs. $1{,}491{,}958\text{ kW}\cdot\text{h}$; cost ratio $1.056$, paired difference $+79{,}637\text{ kW}\cdot\text{h}$, uncorrected $p=0.038$, non-significant under Bonferroni $\alpha=0.0125$) while maintaining virtually identical empirical violation rates ($10.6\% \pm 1.1\%$ for Routed vs. $10.5\% \pm 0.5\%$ for Dense). Crucially, decoupled modular representations (Branch D) achieve $9.7\% \pm 1.1\%$ violation in Delay-6 without expert routing, confirming that diagnostic reserve utility arises from shared spatio-temporal representations.

### Branch B: Physical Prior Breakdown under Telemetry Staleness and Relative Mitigation by Learned Posteriors \label{sec:branch-b}
Under uncorrupted SCADA telemetry, Continuous Physical Quantile achieves optimal baseline operational cost ($589{,}410 \pm 74{,}078\text{ kW}\cdot\text{h}$ at $h=1$ and $871{,}408 \pm 27{,}661\text{ kW}\cdot\text{h}$ at $h=6$) with well-calibrated violation rates ($7.20\% \pm 1.34\%$).

However, Table~\ref{tab:h6-benchmark} and frozen benchmarks expose a **catastrophic reliability breakdown** under telemetry staleness. Under a 6-step delay (Delay-6), clean-calibrated physical quantile rules experience a violation explosion to $\mathbf{24.0\% \pm 1.7\%}$ at $h=1$ and $\mathbf{12.52\% \pm 1.82\%}$ at $h=6$, breaching the nominal 10\% violation target ($q^* = 0.90$) and dumping $127.6\text{ MWh}$ of unhedged shortage onto real-time balancing ($49{,}120\text{ kW}\cdot\text{h}$ at $h=6$). Crucially, **disentangling calibration adaptation from model gains** reveals that adapting validation calibration to degraded states alone cuts shortage from $127.6\text{ MWh}$ ($24.0\%$ violation) to $57.0\text{ MWh}$ ($10.7\%$ violation), accounting for $55.3\%$ of the reduction. Joint Routed further curtails shortage to $53.9\text{ MWh}$ ($10.6\% \pm 1.1\%$ violation), delivering a marginal $5.4\%$ shortage reduction under matched state-conditional calibration (and a combined $57.7\%$ reduction vs. clean-calibrated physics) while saving $190{,}590\text{ kW}\cdot\text{h}$ in total cost. Learned representations thus provide **vital relative mitigation rather than unconditional compliance**: under frozen validation calibration, Delay-6 empirical violation settles at $10.6\% \pm 1.1\%$ at $h=1$ ($11.56\% \pm 2.48\%$ at $h=6$). While substantially cushioning physical rule collapse, learned models require conservative operating margins under multi-step latency.

### Branch D: Decoupled Two-Stage Reserve Over-Estimation and Modular Baseline Analysis \label{sec:branch-d}
In contrast to end-to-end task optimization, the Frozen Backbone Direct Quantile MLP in Table~\ref{tab:h6-benchmark} illustrates the pathology of naive decoupled quantile regression. Across all regimes, direct pinball regression on frozen spatial embeddings incurs massive reserve over-estimation ($1{,}477{,}967$ to $1{,}511{,}794\text{ kW}\cdot\text{h}$, a $44.57\%$ to $72.02\%$ penalty over Joint Routed, $p < 0.01$, Table~\ref{tab:h6-paired}), hoarding $>1.45\text{M kW}$ in bloated reserves.

Benchmarking calibrated modular architectures across 5 seeds (Supplementary Table A11d) resolves this:
1. **Cascaded Frozen MLP:** Trained with consequence decision mapping on frozen backbone embeddings, it achieves $15.528\text{M} \pm 1.599\text{M kW}\cdot\text{h}$ (vs. $16.065\text{M kW}\cdot\text{h}$ for Joint Routed; paired difference $-0.537\text{M}$, 95\% CI $[-1.988\text{M}, +0.915\text{M}]$ crosses zero).
2. **Independent Consequence MLP:** Yields $15.805\text{M} \pm 1.680\text{M kW}\cdot\text{h}$ (difference $-0.260\text{M}$, 95\% CI $[-1.771\text{M}, +1.251\text{M}]$), confirming statistical parity.
3. **Decoupled Residual Quantile Head:** In Delay-6 ($h=1$), Frozen Backbone + Residual Quantile achieves $1{,}284{,}098 \pm 114{,}629\text{ kW}\cdot\text{h}$ and $9.7\% \pm 1.1\%$ violation (60% seed pass rate), matching or slightly surpassing end-to-end MoE ($1{,}412{,}321\text{ kW}\cdot\text{h}$, $10.6\% \pm 1.1\%$).

Thus, diagnostic reserve benefits are not exclusive to MoE routing. Modular models with calibrated consequence mappings achieve equivalent reliability. Joint training's primary advantage is single-checkpoint edge deployment (110k parameters, $<5$ ms latency), eliminating multi-model synchronization overhead.

## Horizon Boundary Diagnosis ($h=1$, 10-Minute Immediate Dispatch vs. $h=6$)

Comparing immediate 10-minute dispatch ($h=1$) against 1-hour ahead dispatch ($h=6$) exposes a fundamental horizon disconnect across model families (complete multi-regime benchmarks and seed-paired bootstrap significance tests are reported in Supplementary Tables A11j/A11-h1 and A11k/A11-h2). At $h=1$, shallow decision trees (Missingness-Aware GBDT) capitalize aggressively on high 10-minute lag wind-speed autocorrelation, achieving the lowest data-driven nominal dispatch cost ($574{,}822 \pm 79{,}685\text{ kW}\cdot\text{h}$ in Clean with $7.6\%$ violation, outperforming all deep models). Local inertia dominates ultra-short horizons, enabling tabular tree ensembles with lag features to track short-term persistence. However, across dispatch-grade horizons ($h=6$), GBDT undergoes severe breakdown: its operational costs inflate by $13.44\%$ to $29.15\%$ (reaching $1{,}213{,}587\text{ kW}\cdot\text{h}$ in Clean and $1{,}305{,}148\text{ kW}\cdot\text{h}$ in Delay-6), trailing Joint Routed by $+156{,}411$ to $+287{,}563\text{ kW}\cdot\text{h}$ across all regimes ($p < 0.0001$, Table~\ref{tab:h6-paired}). Because tabular trees lack spatial awareness of aerodynamic wake advection propagating at $8$--$12\text{ m s}^{-1}$ across turbine rows, they cannot represent multi-turbine spatio-temporal phase shifts over 1-hour lead times.

Crucially, at $h=1$, Joint Dense Head and Joint Routed exhibit statistical parity across Clean, Noise, and Markov regimes, where bootstrap 95\% confidence intervals cross zero (Supplementary Table~A11-h2, e.g., $+29{,}624\text{ kW}\cdot\text{h}$, 95\% CI $[-53{,}774, +113{,}023]$, $p=0.380$ in Clean). In Delay-6, Joint Routed holds a modest cost advantage ($+79{,}637\text{ kW}\cdot\text{h}$, 95\% CI $[+7{,}055, +152{,}218]$, uncorrected $p=0.038$, non-significant under Bonferroni $\alpha=0.0125$) while matching empirical violation rates ($10.6\% \pm 1.1\%$ vs. $10.5\% \pm 0.5\%$). Finally, clean-calibrated Continuous Physical Quantile rules remain equally vulnerable across horizons, collapsing under Delay-6 to $24.0\% \pm 1.7\%$ violation at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, underscoring the universal vulnerability of unadapted physical rules to stale telemetry.

## Multidimensional Operational Boundaries and Selective Decision Abstention

To delineate the operational boundaries governing telemetry degradation, we scan across transmission delays $\tau \in \{0, 10, 20, 30, 60\}\text{ min}$, horizons $h \in \{1, 3, 6\}$, and pitch channel observabilities (\texttt{all} vs. \texttt{no\_pitch}) across all 5 seeds on the 134-turbine WTB plant (Table~\ref{tab:phase-scan}). This empirical trajectory establishes a rigorous **Three-Regime Operational Framework**:

1. **Regime I: Simple Recalibration Sufficient ($\tau = 0\text{ min}$ or mild delays under full observability):** Under fresh telemetry ($\tau=0$, \texttt{all}), deterministic continuous physical quantiles achieve the lowest operational reserve cost ($593{,}258 \pm 74{,}886\text{ kW}\cdot\text{h}$ at $h=1$, with well-calibrated $7.29\% \pm 1.42\%$ violation). Machine-learning representations incur reserve penalties without reliability gains ($663{,}347\text{ kW}\cdot\text{h}$ for modular frozen backbones, $+11.8\%$). When telemetry latency increases to $\tau \in [10, 30]\text{ min}$ with all channels observable, clean-calibrated physical rules collapse ($11.18\% \to 13.98\% \to 16.58\%$). However, state-conditional recalibration fully restores physical compliance ($7.1\%\text{--}7.5\%$ violation) at lower cost than neural models ($742{,}211\text{--}939{,}190\text{ kW}\cdot\text{h}$ vs. $786{,}366\text{--}987{,}760\text{ kW}\cdot\text{h}$), proving that simple recalibration is sufficient when all telemetry channels remain observable.
2. **Regime II: Learned Representation Advantage (Unobservable pitch channels / partial observability):** When blade-pitch telemetry is withheld across aggregator or OEM boundaries (\texttt{no\_pitch}), physical aerodynamic rules lose direct rotor state awareness. Recalibrated physics based solely on wind-speed binning inflates reserve costs ($824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$; $928{,}028\text{ kW}\cdot\text{h}$ at $\tau=10$; $1{,}010{,}530\text{ kW}\cdot\text{h}$ at $\tau=20$; $1{,}101{,}292\text{ kW}\cdot\text{h}$ at $\tau=30$; $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60$). In contrast, learned representations (\textit{Frozen Backbone + Residual Quantile}) reconstruct operating states from electromechanical transients (active/reactive power, rotor speed), achieving $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ cost reduction of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintaining consistent cost savings across all latencies ($866{,}753\text{ kW}\cdot\text{h}$ at $\tau=10$, $-61.3\text{k}$; $947{,}869\text{ kW}\cdot\text{h}$ at $\tau=20$, $-62.7\text{k}$; $1{,}054{,}592\text{ kW}\cdot\text{h}$ at $\tau=30$, $-46.7\text{k}$; $1{,}330{,}318\text{ kW}\cdot\text{h}$ at $\tau=60$, $-48.6\text{k}$).
3. **Regime III: Compound Breakdown and Conservative Safeguards ($\tau = 60\text{ min}$, Delay-6):** Under 60-minute latency, unadapted physical rules experience catastrophic collapse ($24.02\% \pm 1.69\%$ violation, dumping $127.6\text{ MWh}$ shortage). Crucially, fair condition-matching recalibration restores fleet-average violation below the $10.0\%$ target across all three model families ($9.46\%$ for physical rules, $9.55\%$ for Frozen Backbone, and $9.62\%$ for Joint Routed), with the recalibrated physical rule delivering the lowest operating cost ($1{,}228{,}609\text{ kW}\cdot\text{h}$). This directly refutes the prior assumption that multi-step SCADA latency unconditionally collapses all models or makes selective rejection mandatory to meet fleet-average compliance. However, fleet-average compliance conceals critical tail risk: across the 5 random seeds, every method achieves strictly a $3/5$ ($60\%$) seed compliance rate, as Seeds 201 and 203 experience residual breaches ($10.2\%\text{--}10.7\%$) across all architectures. In this severe telemetry regime, unconstrained neural optimization is vulnerable to tail risk.

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.2pt}{6.0pt}\selectfont
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.75}
\caption{Multidimensional operational progression across telemetry latency $\tau \in [0, 60]\text{ min}$ and pitch observability ($h=1$, 5-seed mean on WTB). Cost in kW$\cdot$h ($\rho=10$).}
\label{tab:phase-scan}
\begin{tabularx}{\columnwidth}{@{}ccccccc@{}}
\toprule
$\tau$ (min) & Pitch & \shortstack{Clean Physical\\Cost / Viol.} & \shortstack{Recal. Physical\\Cost / Viol.} & \shortstack{Frozen Backbone\\Cost / Viol.} & \shortstack{Joint Routed\\Cost / Viol.} & Operational Regime \\
\midrule
0 & All & $\mathbf{593{,}258}$ ($7.3\%$) & $\mathbf{593{,}258}$ ($7.3\%$) & $663{,}347$ ($6.1\%$) & $663{,}915$ ($7.3\%$) & Regime I (Physics Opt.) \\
0 & None & $961{,}024$ ($3.2\%$) & $824{,}393$ ($5.4\%$) & $\mathbf{755{,}794}$ ($5.8\%$) & $756{,}257$ ($6.4\%$) & Regime II (Repr. Adv.) \\
\midrule
10 & All & $753{,}606$ ($11.2\%^{\dagger}$) & $\mathbf{742{,}211}$ ($7.4\%$) & $786{,}366$ ($6.7\%$) & $789{,}094$ ($7.6\%$) & Regime I (Recal. Suff.) \\
10 & None & $1{,}008{,}743$ ($4.8\%$) & $928{,}028$ ($6.2\%$) & $\mathbf{866{,}753}$ ($6.1\%$) & $874{,}156$ ($6.6\%$) & Regime II (Repr. Adv.) \\
\midrule
20 & All & $896{,}198$ ($14.0\%^{\dagger}$) & $\mathbf{841{,}734}$ ($7.1\%$) & $875{,}838$ ($7.4\%$) & $879{,}750$ ($8.0\%$) & Regime I (Recal. Suff.) \\
20 & None & $1{,}062{,}646$ ($6.1\%$) & $1{,}010{,}530$ ($6.2\%$) & $\mathbf{947{,}869}$ ($6.7\%$) & $959{,}934$ ($7.1\%$) & Regime II (Repr. Adv.) \\
\midrule
30 & All & $1{,}069{,}266$ ($16.6\%^{\dagger}$) & $\mathbf{939{,}190}$ ($7.5\%$) & $987{,}760$ ($7.1\%$) & $990{,}091$ ($7.6\%$) & Regime I (Recal. Suff.) \\
30 & None & $1{,}138{,}774$ ($7.5\%$) & $1{,}101{,}292$ ($6.7\%$) & $\mathbf{1{,}054{,}592}$ ($6.4\%$) & $1{,}064{,}238$ ($6.7\%$) & Regime II (Repr. Adv.) \\
\midrule
60 & All & $1{,}656{,}285$ ($24.0\%^{\dagger}$) & $\mathbf{1{,}228{,}609}$ ($9.5\%$) & $1{,}283{,}855$ ($9.6\%$) & $1{,}274{,}047$ ($9.6\%$) & Regime III (Abstain / Inflat.) \\
60 & None & $1{,}437{,}280$ ($11.8\%^{\dagger}$) & $1{,}378{,}900$ ($9.0\%$) & $\mathbf{1{,}330{,}318}$ ($8.7\%$) & $1{,}331{,}840$ ($8.8\%$) & Regime II (Repr. Adv.) \\
\bottomrule
\multicolumn{7}{@{}p{\columnwidth}@{}}{\tiny $^{\dagger}$Exceeds nominal 10\% violation target ($q^*=0.90$). Bold indicates lowest compliant operational cost. Under $\tau=60\text{ min}$, by-seed compliance is $3/5$ seeds ($60\%$) across models.}
\end{tabularx}
\end{table}
```

To safeguard operations in Regime III without over-promising autonomous safety, we evaluate a **Selective Decision Abstention (Risk-Coverage Policy)**:
\begin{equation}
r_{i,t}^* = \begin{cases} 
\hat{r}_{i,t}^{\text{learned}}, & \text{if } U_{i,t} \le \theta_c \quad (\text{Accepted Prediction}), \\
r_{i,t}^{\text{fallback}}, & \text{if } U_{i,t} > \theta_c \quad (\text{Decision Abstention / Refusal}),
\end{cases}
\end{equation}
where $U_{i,t}$ denotes predictive uncertainty (entropy or quantile spread), and $\theta_c$ is calibrated on validation data to target coverage fraction $c \in [0.5, 1.0]$. The fallback reserve $r_{i,t}^{\text{fallback}}$ is defined by the conservative envelope:
\begin{equation}
r_{i,t}^{\text{fallback}} = \max\left(r_{i,t}^{\text{phys, recal}},\, [P_{\text{rated}} - \hat{P}_{i,t}]_0^{P_{\text{rated}}}\right),
\end{equation}
where $[x]_0^{P_{\text{rated}}} = \min(\max(x, 0), P_{\text{rated}})$ clamps available generation headroom against rated nameplate capacity ($P_{\text{rated}} = 1{,}500\text{ kW}$), lower-bounded by the condition-recalibrated aerodynamic quantile rule $r_{i,t}^{\text{phys, recal}}$. To audit this mechanism, Table~\ref{tab:risk-coverage} benchmarks selective abstention against two mandatory controls: **Random Abstention** (matching realized empirical coverage $\hat{c}$) and **Uniform Margin Inflation** (evaluated both as an ex-post equal-budget diagnostic benchmark matching total fleet reserve MWh, and as an ex-ante deployable policy with inflation multiplier $\alpha_{\text{val}}$ calibrated on validation data).

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.0pt}{6.0pt}\selectfont
\setlength{\tabcolsep}{1.0pt}
\renewcommand{\arraystretch}{0.75}
\caption{Risk-Coverage Selective Decision Abstention vs. Random and Uniform Controls under Delay-6 ($\tau=60\text{ min}$, $h=1$, 5-seed aggregate on WTB).}
\label{tab:risk-coverage}
\begin{tabularx}{\columnwidth}{@{}llccc@{}}
\toprule
Model & Target $c$ ($\hat{c}$) & \shortstack{Selective Abstention\\Fleet Viol. / Cost} & \shortstack{Random Control\\Fleet Viol. / Cost} & \shortstack{Uniform Inflation\\Fleet Viol. / Cost} \\
\midrule
\multicolumn{5}{@{}l}{\textit{Mode: All Channels Observable}} \\
Joint Routed & $1.00$ ($1.00$) & $9.62\%$ / $1{,}274{,}047$ & $9.62\%$ / $1{,}274{,}047$ & $9.62\%$ / $1{,}274{,}047$ \\
 & $0.90$ ($0.94$) & $9.44\%$ / $1{,}274{,}784$ & $9.50\%$ / $1{,}272{,}870$ & $9.45\%$ / $1{,}273{,}944$ \\
 & $0.80$ ($0.85$) & $9.14\%$ / $1{,}277{,}532$ & $9.36\%$ / $1{,}270{,}990$ & $9.24\%$ / $1{,}274{,}781$ \\
 & $0.50$ ($0.53$) & $8.54\%$ / $1{,}276{,}252$ & $8.78\%$ / $1{,}265{,}902$ & $8.80\%$ / $1{,}277{,}570$ \\
\midrule
Frozen Backbone & $1.00$ ($1.00$) & $9.52\%$ / $1{,}283{,}268$ & $9.52\%$ / $1{,}283{,}268$ & $9.52\%$ / $1{,}283{,}268$ \\
 & $0.90$ ($0.94$) & $9.30\%$ / $1{,}277{,}806$ & $9.36\%$ / $1{,}281{,}737$ & $9.36\%$ / $1{,}283{,}424$ \\
 & $0.80$ ($0.85$) & $9.01\%$ / $1{,}273{,}271$ & $9.28\%$ / $1{,}279{,}718$ & $9.16\%$ / $1{,}284{,}225$ \\
 & $0.50$ ($0.53$) & $8.37\%$ / $1{,}264{,}384$ & $8.76\%$ / $1{,}271{,}385$ & $8.78\%$ / $1{,}286{,}221$ \\
\midrule
\multicolumn{5}{@{}l}{\textit{Mode: No Pitch Telemetry (Withheld)}} \\
Frozen Backbone & $1.00$ ($1.00$) & $8.68\%$ / $1{,}331{,}356$ & $8.68\%$ / $1{,}331{,}356$ & $8.68\%$ / $1{,}331{,}356$ \\
 & $0.90$ ($0.92$) & $8.93\%$ / $1{,}343{,}555$ & $8.61\%$ / $1{,}334{,}006$ & $\mathbf{8.83\%}$ / $\mathbf{1{,}330{,}829}$ \\
 & $0.80$ ($0.84$) & $9.15\%$ / $1{,}350{,}059$ & $8.66\%$ / $1{,}337{,}746$ & $\mathbf{8.92\%}$ / $\mathbf{1{,}331{,}452}$ \\
 & $0.50$ ($0.55$) & $8.84\%$ / $1{,}371{,}729$ & $8.55\%$ / $1{,}353{,}405$ & $\mathbf{8.29\%}$ / $\mathbf{1{,}333{,}906}$ \\
\bottomrule
\multicolumn{5}{@{}p{\columnwidth}@{}}{\tiny Cost in kW$\cdot$h ($\rho=10$). Fleet target $q^*=0.90$ ($10\%$ viol). Note: In \textit{No Pitch}, uniform margin inflation strictly Pareto-dominates selective abstention: ex-post equal-budget uniform inflation achieves $8.29\%$ violation at $1{,}334\text{k kW}\cdot\text{h}$, and ex-ante validation-frozen inflation achieves $7.12\%$ violation at $1{,}348\text{k kW}\cdot\text{h}$ (both lower than selective abstention at $8.84\%$ and $1{,}372\text{k kW}\cdot\text{h}$).}
\end{tabularx}
\end{table}
```

The empirical audit reveals that **heuristic uncertainty scores (predictive entropy and quantile spread) fail to reliably isolate tail shortfall risk under severe telemetry staleness.** Under observable telemetry (\texttt{all}), target coverage $c=0.90$ yields a realized empirical coverage of $\hat{c} = 93.42\% \pm 0.81\%$, but selective abstention reduces fleet violation only marginally ($9.62\% \to 9.44\%$ for Joint Routed; $9.52\% \to 9.30\%$ for Frozen Backbone). This reduction is statistically indistinguishable from random abstention ($9.50\%$ and $9.36\%$, $p > 0.40$), while by-seed compliance remains strictly $3/5$ seeds ($60\%$), as Seed 201 accepted violation actually rises to $10.48\%$ (vs. $10.22\%$ unrejected). Crucially, under withheld pitch (\texttt{no\_pitch}), selective abstention is strictly Pareto-dominated by uniform margin inflation: at $c=0.50$, selective abstention costs $1{,}371{,}729\text{ kW}\cdot\text{h}$ ($8.84\%$ viol), whereas ex-post test-matched uniform margin inflation achieves lower violation ($8.29\%$) at lower total cost ($1{,}333{,}906\text{ kW}\cdot\text{h}$, saving $37{,}823\text{ kW}\cdot\text{h}$), and ex-ante validation-frozen inflation achieves $7.12\%$ violation at $1{,}348{,}361\text{ kW}\cdot\text{h}$ (saving $23{,}368\text{ kW}\cdot\text{h}$). Because stale SCADA telemetry corrupts both the point prediction and the uncertainty proxy, selective rejection incurs the penalty of bloated fallback reserves on safe turbines while missing true tail shortfalls. In industrial operations facing multi-step SCADA disruption, **uniform reserve margin inflation and aerodynamic physical fallbacks provide more reliable, cost-effective risk hedging than heuristic selective abstention.**


## Operating-Boundary Recovery and Point-Forecast Price of Routing

We first establish the forecasting accuracy price of operating-state routing. Across five WTB seeds, the boundary-forced router reaches RMSE 236.13 +/- 8.41, compared with 224.34 +/- 2.23 for iTransformer and 225.74 +/- 2.60 for Graph WaveNet. The router is therefore 11.79 RMSE units above iTransformer and 10.39 units above Graph WaveNet. The provenance-corrected train-only rerun reduces this gap to 5.59 units, with RMSE 229.93 +/- 2.50. Under the strict-mask evaluation boundary, the boundary-forced router achieves NMI 0.8716 +/- 0.0418 and ARI 0.9166 +/- 0.0371, while the train-only class-weight rerun maintains NMI 0.721 and ARI 0.740.

The anchor-stress guard verifies that the route does not reflect data leakage: removing \texttt{Patv} or \texttt{Pab\_mean} leaves mean NMI at 0.881 and 0.878, while lagging \texttt{Patv} and lagging pitch/wind give 0.763 and 0.684. Furthermore, gate matching to the active operating regime peaks at the transition step (0.815) and decays under three- and six-step lead shifts (0.361 and 0.405), confirming that gate activations track dynamic physical state changes.

## Withheld-Channel Electromechanical Signature Recovery (Branch E)

The integrity of the Tier 2 blind-spot fallback rests on whether the model can infer operational regime boundaries when defining anemometer or pitch channels are unavailable. In operational practice, internal turbine blade-pitch telemetry may be delayed by SCADA network latency or unobservable to third-party aggregators, VPP coordinators, and TSOs due to commercial OEM protocol boundaries. To test whether non-pitch electromechanical consequence channels carry sufficient information to recover regime transitions without circular dependence, we formulate a strict **counterfactual stress-testing probe**: zeroing `Wspd` and `Pab_mean` while retaining active power and downstream electromechanical channels yields a mean NMI of 0.561 and ARI of 0.635 across five seeds on WTB (Table~\ref{tab:signature-gate}). Removing active power (`signature_core`) drops mean NMI to 0.367, whereas permuted label negative controls collapse to $4.0 \times 10^{-6}$, definitively ruling out spurious correlations.

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.5pt}{6.3pt}\selectfont
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.80}
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

This demonstrates that partial pitch observability does not extinguish boundary recoverability; rather, the dynamic graph extracts operational risk signatures from electromechanical transients under site-specific training.

**Diagnostic dispatch replay under site-specific local retraining:** To examine how consequence representations behave when models are trained locally under site-specific rated wind speeds ($v_{\mathrm{rated}}=12.5\text{ m s}^{-1}$ for Kelmarsh MM92 and $14.5\text{ m s}^{-1}$ for Penmanshiel MM82), we executed 5-seed chronological dispatch replays on both plants:
- On **Penmanshiel (15 MM82 turbines)** at 1-hour dispatch ($h=6$), locally retrained Joint Routed yields $831{,}251 \pm 112{,}331\text{ kW}\cdot\text{h}$ (Clean) and $813{,}831 \pm 102{,}946\text{ kW}\cdot\text{h}$ (Delay-6). In comparison, Missingness-Aware GBDT exhibits severe degradation ($1{,}064{,}962 \pm 236{,}997\text{ kW}\cdot\text{h}$ Clean and $1{,}086{,}102 \pm 251{,}889\text{ kW}\cdot\text{h}$ Delay-6), with elevated violation rates of $24.73\% \pm 6.93\%$ and $26.46\% \pm 6.63\%$ (and up to $38.14\%$ at $h=1$). Locally retrained Joint Routed exhibits cost differences over GBDT of $+233{,}710\text{ kW}\cdot\text{h}$ under Clean ($p < 0.001$, 95\% CI $[+119{,}765, +347{,}656]$) and $+272{,}271\text{ kW}\cdot\text{h}$ under Delay-6 ($p < 0.001$, CI $[+138{,}969, +405{,}574]$), while Continuous Physical Quantile yields $844{,}248\text{ kW}\cdot\text{h}$ (Clean) and $828{,}471\text{ kW}\cdot\text{h}$ (Delay-6).
- On **Kelmarsh (6 MM92 turbines)** at $h=6$, locally retrained Joint Routed yields $70{,}375 \pm 16{,}324\text{ kW}\cdot\text{h}$ (Clean) and $109{,}359 \pm 13{,}634\text{ kW}\cdot\text{h}$ (Delay-6), versus $115{,}266\text{ kW}\cdot\text{h}$ and $138{,}980\text{ kW}\cdot\text{h}$ for GBDT ($+44{,}891\text{ kW}\cdot\text{h}$ and $+29{,}621\text{ kW}\cdot\text{h}$, $p < 0.05$), and $82{,}456\text{ kW}\cdot\text{h}$ and $116{,}409\text{ kW}\cdot\text{h}$ for Continuous Physical Quantile.

Crucially, these numerical comparisons reflect site-specific local model training and offline diagnostic replay, **not** zero-shot cross-farm reserve transfer or generalized fallbacks. As demonstrated by our external wind guard (`external_wind_guard.json`), zero-shot cross-farm transfer exhibits marked directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled mean NMI $0.557$). Operational reserve benefits cannot be assumed to transfer reliably across plants without local sensor calibration and within-plant training.

## Degradation Resilience and Early Warning Dynamics

Table~\ref{tab:early-warning} stress-tests detection fidelity when issue-time telemetry is delayed or corrupted under the Unified Arrival Layer. Under clean anchors, the deterministic threshold rule remains the stronger detector (1.000 versus 0.9705), and clean logistic regression reaches 1.000 recall with 0.879 precision (above the routed posterior's 0.630). Under a 6-step delay ($d=6$) with full-stream history shift (where both anchor readings and encoder history stall by 60 minutes), the deterministic threshold rule's recall collapses from $1.000$ to $0.196$, its precision drops to $0.342$, and its F1 score collapses to $0.249$. In contrast, the jointly-learned routed posterior maintains an early-window recall of $0.4170 \pm 0.1137$ (+0.221 over the rule, more than doubling detection sensitivity) and an F1 score of $0.3802$ (+0.131 over the rule). When telemetry stalls for 60 minutes, detection recall naturally attenuates from 0.971 to 0.417, but the spatio-temporal graph representations double the surviving resilience without any clean-history information leaks.

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.5pt}{6.3pt}\selectfont
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.80}
\caption{Early MPPT-to-pitch detection under fair input degradation (Unified Arrival Layer) across 5 train-only seeds. Full-stream history shift and anchor delay applied symmetrically to gate and rule.}
\label{tab:early-warning}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.22\linewidth} >{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}p{0.15\linewidth} >{\centering\arraybackslash}X}
\toprule
Scenario & Setting & Gate & Rule & Gain \\
\midrule
Clean anchors & --- & 0.9705 $\pm$ 0.0299 & 1.000 & $-$0.029 \\
Delay (fair) & 1 step & 0.8346 $\pm$ 0.0771 & 0.655 & +0.179 \\
Delay (fair) & 3 steps & 0.6200 $\pm$ 0.1209 & 0.381 & +0.239 \\
Delay (fair) & 6 steps & 0.4170 $\pm$ 0.1137 & 0.196 & +0.221 \\
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

Under industrial two-state Markov-Gilbert burst dropouts ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$) evaluated symmetrically across both anchor and encoder history channels, the stale threshold rule's recall drops to $0.840$ with an F1 of $0.904$, whereas the jointly-learned routed posterior sustains a recall of $0.962 \pm 0.023$ and an F1 of $0.925 \pm 0.042$ during bursts (mean F1 gain $+0.021$, 95\% bootstrap CI $[-0.014, +0.050]$). During dynamic transitions, the spatio-temporal graph provides vital defense-in-depth against communication dropouts.

## Boundary-Window Reserve Vignette and Benchmark Comparison

At a shortage-to-reserve cost ratio $\rho=10$ on the transition boundary band, the boundary-router gate-bin policy costs 95.13M, outperforming the same-model global rule (99.55M), while the low-RMSE Graph WaveNet with physical-bin reference achieves 84.31M. This translates into approximately 637 avoided MWh-equivalent shortage cells and a 442k illustrative reserve-cost-scale marker at 100 EUR/MWh.

## Point of Common Coupling (PCC) Portfolio Smoothing & Exploratory Longitudinal Drift Analysis (Branch F)

Crucially, to verify reserve behavior under spatial aggregation, we evaluate aggregate power at the Point of Common Coupling (PCC) bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, averaging $\sim 121$ active turbines). Across the full operational envelope, joint posterior aggregate quantile pricing reduces reserve cost by $-11.22\text{M kWh}$ (95\% bootstrap CI $[-21.55\text{M}, -2.85\text{M}]$, strictly excluding zero) against global PCC quantiles and by $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) against Gaussian parametric sizing; in transitional regimes (10\%--90\% pitching), it saves $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) over continuous physical pitch, confirming relative risk mitigation after fleet-wide error cancellation. We emphasize that all reported values represent the upstream PSREI operational risk proxy ($\rho=10$) rather than actual financial market cashflows.

Across two European commercial wind plants with longitudinal records (Kelmarsh, 9 years, 2016--2024, 6 MM92 turbines; Penmanshiel, 8.6 years, 2016--2024, 15 MM82 turbines), exploratory evaluations examined rolling two-year quantile recalibration. However, recent data-integrity audits have isolated two historical rolling folds exhibiting temporal train-test overlap. In the absence of a complete re-evaluation over fully isolated non-overlapping folds, these historical rolling runs must be interpreted strictly as an **exploratory diagnostic** demonstrating the operational mechanics of periodic quantile recalibration under multi-year climatological and sensor drift, rather than as validated proof of long-term durability or elimination of concept drift.

# Discussion

## Accuracy, accountability and deployment gates

The accuracy cost is not secondary: iTransformer, Graph WaveNet, and lag baselines remain superior whole-sample forecasters on WTB; the boundary model should pair with an established low-RMSE forecaster when aggregate accuracy is paramount. Its targeted role is an accountable operating-state diagnostic for boundary-specific decisions. External testing is strictly bounded: La Haute Borne demonstrates anchor-observable mechanism replication under local chronological training (five-seed routing NMI 0.941, ARI 0.971; canonical NMI 0.975; withheld probe 0.674/0.575). On Kelmarsh the probe reaches 0.340/0.378, and on Penmanshiel 0.302 (`signature_core` 0.195, far above permuted controls; Supplementary Table A9d).

Crucially, zero-shot cross-farm transfer exhibits pronounced directional asymmetry and model sensitivity across commercial plants: transferring from Kelmarsh to Penmanshiel achieves high boundary alignment (NMI $0.752$--$0.770$, ARI $0.735$--$0.761$), whereas transfer in the reverse direction from Penmanshiel to Kelmarsh drops sharply to NMI $0.341$--$0.505$ (with Physics-Aligned MoE falling to $0.341$). Although the pooled bidirectional mean NMI of $0.557$ nominally satisfies the aggregate $0.50$ criterion (`external_wind_guard.json`), this directional degradation confirms that zero-shot transfer cannot serve as a reliable drop-in solution across disparate turbine geometries without local sensor recalibration and within-plant retraining.

Furthermore, external walk-forward rolling evaluation establishes empirical physical boundary conditions for the pre-registered admission protocol (Supplementary Table A14). On ENGIE La Haute Borne (4 turbines, 99\% complete pitch), walk-forward pooled quarterly evaluation (Q1--Q3) incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus continuous physical pitch (Supplementary Table A11h). This reveals quantile variance amplification under acute seasonal drift: on a miniature 4-turbine site without Point of Common Coupling (PCC) spatial portfolio smoothing, short quarterly slices suffer variance spikes during autumn regime shifts (+968.1k kWh in Q3, while Q1--Q2 cross zero). Expanding calibration to a 180-day annual window compresses the cost gap to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero), bounding soft-posterior reserves to PCC-smoothed plants and degraded/pitch-sparse telemetry.

Evaluating across shortage penalty ratios $\rho \in \{5, 10, 20\}$ articulates an operational envelope ("Telemetry Availability $\times$ Penalty Ladder"). At $\rho=10$, learned posteriors dominate unconditioned baselines. At $\rho=20$, asymmetry emerges: at Kelmarsh, physical rules recover and surpass soft-gate pricing by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); at Penmanshiel, the soft gate leads physical rules by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) while crossing zero versus the unconditioned global baseline ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$). Direct reserve deployment at new farms requires pitch or proxy observability, boundary support, compatible geometry, local recalibration, and a held-out validation pass [@tautzweinert2017scada].

# Limitations

WTB pseudo-labels derive from wind speed and pitch angle, channels present in full gate anchors. Counterfactual withheld-channel stress testing proves the boundary survives without direct pitch observations via consequence signatures across four farms (permuted controls at chance). Removing pitch dispersion retains non-power NMI 0.309 on WTB and 0.578 on La Haute Borne, confirming dispersion does not carry the signal. Yet boundary identification remains an anchor-constrained diagnostic rather than anchor-free discovery [@karniadakis2021piml; @zehtabiyan2023physicsguided]. Inputs may contain history $\texttt{Patv}_{t-H+1:t}$ and issue-time $\texttt{Patv}_{t}$, while targets begin at $t+1$. Expert semantics reflect the declared mapping; unassigned logits are not universal physical states.

Crucially, our evaluation is formally bounded to Level 1 local pre-dispatch risk screening proxies (Penalized Reserve-Shortfall Energy Index, PSREI at $\rho=10$), designed to minimize unhedged imbalance entering real-time balancing. This local screening explicitly abstracts away Level 2 transmission operations, including AC-OPF, network thermal and voltage constraints, security-constrained unit commitment, and multi-stage market settlements [@bremnes2004quantile; @zhou2013probabilisticmarkets]. Strongest claims remain five-seed WTB recovery, mechanism intervention, La Haute Borne local replication, and same-router reserve triage.

# Conclusion

This study exposes the operational vulnerability and reliability breakdown of deterministic wind turbine operating reserve rules under SCADA telemetry degradation and evaluates jointly-learned boundary-risk posteriors as relative mitigators and diagnostic instruments. Across a 5-seed benchmark on the 134-turbine WTB plant, continuous aerodynamic quantile rules achieve optimal pricing efficiency under pristine telemetry ($589{,}410\text{ kW}\cdot\text{h}$ at $h=1$, $871{,}408\text{ kW}\cdot\text{h}$ at $h=6$), but undergo catastrophic collapse under a 6-step ($60\text{ min}$) delay, surging violation rates to $24.0\% \pm 1.7\%$ ($h=1$) and $12.52\% \pm 1.82\%$ ($h=6$).

Under frozen validation calibration, state-conditional recalibration of physical rules recovers violation to $10.7\%$ and cuts shortage from $127.6\text{ MWh}$ to $57.0\text{ MWh}$ ($55.3\%$ reduction), while learned boundary-risk posteriors provide an additional $5.4\%$ reduction to $53.9\text{ MWh}$ (a combined $57.7\%$ reduction) and double regime recall ($0.416$ vs. $0.196$ under Delay-6). However, the evidence firmly rejects deep neural models as an autonomous "safety airbag": under 6-step latency, test violations reach $10.6\% \pm 1.1\%$ ($>10\%$), requiring explicit operational safety margins. Furthermore, Dense and MoE heads achieve statistical parity in Clean (cost ratio $1.045$, $p=0.380$) with a modest Delay-6 margin (ratio $1.056$, uncorrected $p=0.038$), while modular architectures match tail reliability ($9.7\%$ violation), proving value arises from shared spatio-temporal representations rather than MoE routing. Finally, zero-shot cross-farm transfer exhibits directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled $0.557$), bounding reliable deployment to sites with local retraining (ENGIE La Haute Borne, NMI $= 0.941$). These findings reframe data-driven reserve models into rigorous, accountable diagnostic tools that delineate the physical and communication boundaries of smart grid operations.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.

# Code and data availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public (raw third-party data not redistributed). Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress caches, early-warning label degradation, classifier control, class-weight sensitivity, external diagnostics, and evidence-freeze protocols across declared seeds. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.


# References {.unnumbered}

::: {#refs}
:::

