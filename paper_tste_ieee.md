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
  - \linespread{0.895}
  - \AtBeginDocument{\fontsize{9.4pt}{10.8pt}\selectfont}
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
Operating reserve screening near the demarcation boundary between maximum power point tracking (MPPT, Region 2) and blade-pitch regulation (Region 3) is critical for imbalance risk mitigation and frequency security in wind-integrated power systems. However, industrial Supervisory Control and Data Acquisition (SCADA) telemetry is routinely afflicted by communication queuing delays, packet serialization dropouts, and unobservable pitch registers. While deterministic aerodynamic power-curve quantile rules achieve the lowest PSREI reserve-screening cost under pristine telemetry ($589{,}535\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with $\sim 6.8\%$ violation), they exhibit systematic reliability breakdown under communication latency. Under a 6-step ($60\text{ min}$) synthetic transmission lag, the steep change in local control sensitivity near rated wind speed amplifies stale-state estimation errors, driving physical rule violation rates to $24.0\% \pm 1.7\%$ ($h=1$) and $12.2\% \pm 1.2\%$ ($h=6$), severely breaching the nominal 10\% violation target ($q^* = 0.90$), corresponding to $127.6\text{ MWh}$ of unhedged shortfall exposure in the balancing-risk proxy. To defend against telemetry staleness, we formulate a Cyber-Physical Operational Boundary Framework under Information Freshness Constraints, coupling time-varying directed wake graphs with multi-task boundary-risk posteriors that exploit non-pitch electromechanical transients for blind-spot state reconstruction. Evaluated across a five-seed benchmark on the 134-turbine WTB plant under strictly frozen validation calibration, state-conditional recalibration recovers physical violation to $10.7\%$ (cutting shortage to $57.0\text{ MWh}$), while joint spatio-temporal posteriors further compress shortage to $53.9\text{ MWh}$ (a combined $57.7\%$ reduction) and double boundary recall over collapsed physical rules ($0.417$ vs. $0.196$). Capacity-matched dense and routed architectures achieve statistical parity under clean telemetry (cost ratio $1.045$, $p=0.380$), while decoupled modular representations (Frozen Backbone + Residual Quantile) achieve lower reserve cost ($1.284\text{M kW}\cdot\text{h}$) and compliant tail coverage ($9.7\%$ violation). Withheld-channel counterfactual stress testing confirms robust regime recovery under unobservable pitch (NMI $0.561$), and Point of Common Coupling (PCC) aggregation demonstrates net plant-level portfolio smoothing. These empirical boundaries establish an accountable pre-dispatch risk diagnostic framework for cyber-resilient grid reserve management, delineating operational trade-offs between unadapted physical rules, state-conditional recalibration, and learned spatio-temporal posteriors under telemetry degradation.
\end{abstract}

\begin{IEEEkeywords}
Wind turbine operating reserve; SCADA telemetry degradation; transmission latency; aerodynamic power curve; reliability breakdown; boundary-risk posterior; selective decision abstention; MPPT-to-pitch transition.
\end{IEEEkeywords}

# Introduction

In power system balancing operations, generation deficit incurs severe asymmetric shortage penalties relative to surplus energy; consequently, quadratic loss metrics like RMSE obscure critical tail shortfall events that dictate operational balancing reliability [@dowell2015veryshortterm; @kruse2023physics; @pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. Wind-farm operating reserve screening near the demarcation boundary between maximum power point tracking (MPPT, Region 2) and blade-pitch regulation (Region 3) is critical for system frequency security. At this boundary, local control sensitivity undergoes a steep change: the governing aerodynamic objective shifts from cubic power capture to active blade-pitch aerodynamic dissipation [@slootweg2003general; @gaertner2020definition]. Deterministic power-curve models embody an inherent vulnerability near rated inflow velocities: minor unobserved perturbations cause piecewise control laws to trigger premature or delayed pitch actuation, precipitating severe unhedged energy shortfall penalties.

In industrial wind plant operations, SCADA telemetry streams across distributed turbine networks are routinely afflicted by communication queuing delays, packet serialization overhead, and asynchronous timestamp skews [@tautzweinert2017scada; @ullah2022enabling]. In the commercial Kelmarsh plant, for example, 99.6\% of turbine status events carry timestamps falling strictly between 10-minute SCADA grid boundaries, demonstrating that operational state transitions regularly unfold within reporting blind spots. To systematically assess reserve vulnerabilities under extreme communication backlog, buffer congestion, and gateway dropouts [@ullah2022enabling; @pierre2019design; @ravikumar2020anomaly], this paper evaluates controlled synthetic transmission latency stress tests from 10 to 60 minutes. Furthermore, in third-party aggregator, Virtual Power Plant (VPP), and Transmission System Operator (TSO) pre-dispatch triage, primary blade-pitch registers are frequently unobservable due to commercial boundaries and proprietary OEM protocol firewalls. Feeding stale or missing sensor measurements into deterministic physical mappings precipitates severe misclassification, compelling pre-dispatch algorithms to clear reserve margins against obsolete operating points.

Existing operational paradigms treat physical aerodynamic curves and data-driven models as mutually exclusive alternatives, neglecting their complementary operational boundaries under communication stress. Under pristine SCADA telemetry, high-fidelity physical priors—specifically continuous soft-pitch quantiles derived from manufacturer power curves—deliver the lowest PSREI reserve-screening cost ($589{,}535\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with $\sim 6.8\%$ violation). However, deterministic physical rules exhibit systematic reliability breakdown under telemetry staleness: stale pitch and anemometer readings cause severe over-extrapolations near rated wind speed. Under a 6-step ($60\text{ min}$) transmission lag, clean-calibrated physical rule violation rates surge to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, severely breaching the nominal 10\% violation target ($q^* = 0.90$) set by the reserve screening index, corresponding to $127.6\text{ MWh}$ of unhedged shortfall exposure under the balancing-risk proxy. Conversely, shallow machine-learning baselines like Missingness-Aware GBDT exploit 10-minute lag wind-speed autocorrelation at ultra-short horizons ($h=1$), but undergo severe breakdown across dispatch-grade horizons ($h=6$), inflating reserve costs by $13.44\%$ to $29.15\%$ ($p < 0.0001$) because tabular models cannot capture spatial wake advection propagating across turbine arrays [@daenens2025offshore].

To resolve this operational tension, we formulate a **Cyber-Physical Operational Boundary Framework under Information Freshness Constraints**. The framework demonstrates that deterministic physical rules achieve the lowest PSREI cost among evaluated methods when telemetry is fresh, whereas joint spatio-temporal learning provides robust defense when telemetry is degraded. By capturing cross-sensor electromechanical signatures (active power fluctuations, reactive dynamics, and dynamic wake geometry), learned posteriors preserve operational regime awareness and curtail severe shortage volumes, even when primary pitch channels are unobservable. Under a strict frozen-calibration protocol on the 134-turbine WTB benchmark, capacity-matched Dense and Mixture-of-Experts (MoE) heads achieve statistical parity in degraded reserve screening, while decoupled modular models achieve lower total cost and compliant tail coverage, demonstrating that diagnostic reserve benefits originate from shared spatio-temporal representations and decoupled residual calibration rather than dynamic routing mechanisms.

This paper makes four bounded, verifiable contributions:
1. **Reliability Breakdown of Deterministic Physical Rules:** We expose the systematic breakdown of aerodynamic power-curve quantile rules under telemetry latency. Across 5 seeds on the 134-turbine WTB plant, a 6-step ($60\text{ min}$) latency causes clean-calibrated physical violation rates to surge from $6.8\%$ to $24.0\% \pm 1.7\%$ ($h=1$) and $12.2\%$ ($h=6$), severely breaching the nominal 10% violation target.
2. **Decisive Benchmark and MoE De-mystification:** Under causal feeds with validation calibration frozen before testing, physical rules achieve the lowest PSREI reserve-screening cost under clean feeds ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$). Under stale feeds, state-conditional calibration absorbs most reliability loss ($10.7\%$ violation, $57.0\text{ MWh}$ shortage), while learned posteriors reach $10.6\% \pm 1.1\%$ violation and $53.9\text{ MWh}$ shortage. Decoupled modular architectures (Frozen Backbone + Residual Quantile) achieve lower reserve cost ($1.284\text{M kW}\cdot\text{h}$) and compliant tail coverage ($9.68\%$ violation), establishing that diagnostic reserve benefits are driven by spatio-temporal feature representations and decoupled residual calibration rather than dynamic MoE routing.
3. **Disentangled Diagnostics & Safeguard Boundaries:** Disentangling calibration adaptation from learned representation reveals that state-conditional calibration recovers $95.8\%$ of recoverable shortage energy ($127.6 \to 57.0\text{ MWh}$, a $55.3\%$ reduction), while learned posteriors add a $5.4\%$ reduction ($57.0 \to 53.9\text{ MWh}$, combined $57.7\%$) and double state recall over collapsed physical rules ($0.416$ vs. $0.196$ under Delay-6). While condition-matching recalibration restores fleet-average violation below the $10.0\%$ target (with physics reaching $1.229\text{M}$ and $9.46\%$), inter-seed compliance is strictly bounded at $3/5$ seeds ($60\%$). We evaluate selective decision abstention against random and uniform margin inflation controls, showing that heuristic entropy scores fail to isolate tail risk and that uniform margin inflation Pareto-dominates selective rejection under missing pitch.
4. **Empirical Deployment Boundaries:** We delineate empirical generalization limits across commercial farms: mechanism replication holds under local retraining on ENGIE La Haute Borne (routing NMI $= 0.941$, ARI $= 0.971$), but zero-shot cross-farm transfer exhibits directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled $0.557$). All reserve savings represent an upstream PSREI operational risk proxy ($\rho=10$).

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting has progressed from site-specific statistical models to spatio-temporal architectures that represent ramps, uncertainty and spatial coupling [@dowell2015veryshortterm; @pinson2013forecasting; @wang2025uncertaintyreview]. Graph models provide a strong accuracy reference by propagating information across the network [@wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn]. Wind-specific studies have further introduced wake-aware graphs, SCADA integration and physics-guided constraints [@park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore; @zehtabiyan2023physicsguided; @zhang2021lidar]. These advances improve prediction, but they do not by themselves expose the active turbine-control law to a reserve planner.

MoE routing can represent local response laws, but prediction loss alone does not determine whether the resulting partition has operating meaning [@shazeer2017outrageously; @fedus2022switch]. Physics-guided machine learning supplies general principles for introducing scientific constraints, while wind-turbine operating states remain limited by SCADA observability [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada]. The MPPT-to-pitch transition itself is a documented control-engineering structure: variable-speed turbines maximise capture below rated wind (Region 2), and pitch regulation takes over above it [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind; @johnson2004region2; @slootweg2003general; @gaertner2020definition]. Our distinction is therefore the location of the constraint. Earlier work constrains predictions or lets prediction loss organise experts; we formulate a cyber-physical boundary framework where aerodynamic transitions are explicitly audited against telemetry age and queuing degradation [@pierre2019design; @ravikumar2020anomaly; @ullah2022enabling].

Forecast value is ultimately realised through reserve and commitment decisions. Previous studies show that variable generation changes reserve requirements, while probabilistic and quantile forecasts provide a bridge from prediction error to decision risk [@doherty2005reserve; @ela2011operatingreserves; @bremnes2004quantile; @zhang2014probabilisticreview; @zhou2013probabilisticmarkets; @dowell2015veryshortterm; @kruse2023physics]. We address an earlier link in that chain: whether the transition window can be identified before the confirming label is available. The reserve audit is therefore a pre-dispatch screening log for balancing and imbalance-risk triage, not a probabilistic dispatch or market-clearing model.

# Cyber-Physical Operational Boundary Framework under Information Freshness Constraints

## Problem setup and notation

The forecasting task is written to separate two decisions that dense models often merge: predicting the future and deciding which local mapping should be active at the anchor time. This separation follows the spatio-temporal graph forecasting formulation in which a graph encoder maps a history window to a future trajectory [@li2018dcrnn; @wu2019graphwavenet]. Let $G=(V,E)$ denote a spatial graph with $N$ nodes. For each node $i \in V$ and time step $t$, we observe a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predict a scalar target $y_{i,t} \in \mathbb{R}$. Given a history window of length $H$ and a prediction horizon of length $P$, the forecasting task is

$$
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
$$

where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes either a time-varying directed graph sequence (WTB) or a static graph repeated over time (ERA5). Invalid or missing targets are excluded by a supervision mask.

The information boundary is strict. All inputs, graph weights, regime anchors, and gate anchors are observed no later than the forecast issue time $t$; supervised targets begin at $t+1$. In WTB, the current active-power channel $\texttt{Patv}_{i,t}$ is treated as an issue-time status input, whereas future active power is used only as the prediction target and validity mask. This keeps the multi-step horizon free of target leakage while leaving the no-\texttt{Patv} and lagged-\texttt{Patv} variants as deployment limitations.

Routing is node-level: each node at each anchor time receives its own gate distribution $\mathbf{g}_{i,t}$. This matters because nearby turbines or grid cells can occupy different local regimes within the same sequence. Key variables are indexed by turbine $i$, anchor time $t$, and prediction horizon step $p \in \{1, \dots, P\}$; auxiliary loss formulations are detailed in Supplementary Appendix\ A.

## Operating-Boundary Physical Anchors and Power-Curve Baseline

The supervisory anchor is not applied indiscriminately across all operating states. It is anchored where the physical aerodynamic interpretation is clearest, while ambiguous samples remain governed by prediction loss and spatial regularisation. This design provides the physical reference anchor: **a high-fidelity aerodynamic prior** calibrated to the manufacturer specifications of each turbine model [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada].

**Aerodynamic power conversion and non-linear $C_p$ formulation:** In variable-speed wind turbine aerodynamics, mechanical power captured by the rotor from inflow air is governed by [@slootweg2003general; @gaertner2020definition]:
\begin{equation}
P_{\mathrm{mech}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), \beta(t)) \cdot v^3(t),
\end{equation}
where $\rho_{\mathrm{air}} \approx 1.225\text{ kg/m}^3$ is air density, $R$ is rotor radius, $v(t)$ is hub-height effective wind speed, and $\beta(t)$ is blade pitch angle. The tip-speed ratio (TSR) is $\lambda(t) = \omega_r(t) R / v(t)$, with rotor mechanical angular velocity $\omega_r(t)$. According to standard aeroelastic turbine models [@slootweg2003general; @gaertner2020definition], rotor power efficiency $C_p(\lambda, \beta)$ is approximated by:
\begin{equation}
C_p(\lambda, \beta) = c_1 \left( \frac{c_2}{\lambda_i} - c_3 \beta - c_4 \right) \exp\left(-\frac{c_5}{\lambda_i}\right) + c_6 \lambda,
\end{equation}
with $\frac{1}{\lambda_i} = \frac{1}{\lambda + 0.08\beta} - \frac{0.035}{\beta^3 + 1}$. Coefficients $\{c_1, \dots, c_6\}$ define aerodynamic conversion efficiency up to Betz's theoretical limit.

**Control cliff and derivative discontinuity:** Wind turbine operating dynamics are partitioned by rated wind speed $u_{\mathrm{rated}}$:
1. *Region 2 (MPPT, $u_{\mathrm{idle}} \le v \le u_{\mathrm{rated}}$):* Blades maintain optimal fine pitch $\beta = \beta_{\mathrm{opt}} \approx 0^\circ$ to sustain peak power coefficient $C_{p,\max}$. Generator counter-torque controls rotor speed to track optimal TSR $\lambda_{\mathrm{opt}}$, producing cubic power growth $P(v) \propto v^3$.
2. *Region 3 (Pitch regulation, $u_{\mathrm{rated}} < v \le u_{\mathrm{cut-out}}$):* Generator electromagnetic torque is locked at rated level while the pitch controller rotates blades to shed aerodynamic lift, clamping electrical output at nameplate capacity $P_{\mathrm{rated}}$, subject to first-order actuator lag and slew limits $\dot{\beta}(t) = \mathrm{sat}_{\dot{\beta}_{\max}}\!\left( (\beta_{\mathrm{cmd}}(t) - \beta(t)) / \tau_{\mathrm{pitch}} \right)$ [@slootweg2003general; @gaertner2020definition].

Near the rated transition boundary $v = u_{\mathrm{rated}}$, local control sensitivity undergoes a steep change: the marginal aerodynamic power response drops sharply from a large positive slope to zero:
\begin{equation}
\left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^-} = \frac{3}{2} \rho_{\mathrm{air}} \pi R^2 C_{p,\max} u_{\mathrm{rated}}^2 \gg 0, \quad \left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^+} = 0.
\end{equation}
When SCADA telemetry experiences transmission latency $\tau > 0$, deterministic physical rules evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. When actual inflow wind shifts into Region 3 while delayed pitch readings remain at $\beta = 0^\circ$, this steep sensitivity change amplifies stale-state estimation errors: the deterministic curve over-extrapolates generation,
\begin{equation}
\hat{P}_{\mathrm{phys}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), 0^\circ) \cdot v^3(t) \gg P_{\mathrm{rated}},
\end{equation}
driving shortage violation rates to $24.0\% \pm 1.7\%$ under Delay-6.

**Aerodynamic operating regimes and turbine-calibrated anchors:** Let $\bar{p}_{i,t} = \frac{1}{3}\sum_{k=1}^3 p^{(k)}_{i,t}$ denote average blade pitch angle across all three blades for turbine $i$ at dispatch anchor time $t$, and $w_{i,t}=\texttt{Wspd}_{i,t}$ anemometer wind speed. The declared operating boundary is defined with turbine-calibrated cut-in threshold $u_{\mathrm{idle}}$, rated wind speed $u_{\mathrm{rated}}$, and pitch-activation angle $p_{\mathrm{th}}$:

$$
R_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transitional/ambiguous)}.
\end{cases}
$$

Aerodynamic rated wind speeds are calibrated to the specific turbine technology at each wind plant: WTB (134 turbines: $u_{\mathrm{idle}}=3.0\text{ m s}^{-1}$, $u_{\mathrm{rated}}=10.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=2.0^\circ$), Kelmarsh (6 MM92 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=12.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$), Penmanshiel (15 MM82 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$), and ENGIE La Haute Borne (4 MM82 turbines: $u_{\mathrm{idle}}=3.0$, $u_{\mathrm{rated}}=14.5\text{ m s}^{-1}$, $p_{\mathrm{th}}=1.0^\circ$).

Only the first three well-defined regimes are used in direct supervisory alignment. Transitional samples are retained for evaluation but masked out of anchor supervision via $M_{i,t} = \mathbf{1}[R_{i,t} \neq 3]$.

These thresholds define the **Aerodynamic Power-Curve Baseline**: when SCADA telemetry is complete and intact, continuous soft-pitch quantiles derived from these anchors achieve the lowest baseline reserve-screening cost. When telemetry degrades through communication latency or sensor corruption, however, this deterministic rule experiences severe reliability breakdown, requiring learned diagnostic representations.

**ERA5 observability contrast:** ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the wind plant control-boundary accountability task.

## Spatio-Temporal Dynamic Wake Graph and Boundary-Risk Posterior Formulation

**Physical dynamic wake graph construction:** When primary SCADA telemetry degrades, spatial coupling across turbine arrays provides the crucial redundancy required to infer local operating regimes. Directed diffusion represents asymmetric aerodynamic wake propagation through the turbine network [@li2018dcrnn; @wu2019graphwavenet]. For WTB, we construct a time-varying directed wake graph $\mathcal{A}_t$: candidate turbine pairs $(i, j)$ are filtered by physical distance ($d_{ij} \le d_{\max}$), activated when upstream turbine $j$ lies within an aerodynamic wake cone aligned with instantaneous local wind direction $\theta_t$ (half-angle $\alpha = 25^\circ$), weighted by streamwise decay $\exp(-d_{\parallel}/\sigma_x)$ and cross-stream decay $\exp(-d_{\perp}^2/2\sigma_y^2)$, and pruned to the $K$ strongest inbound wake neighbors [@park2019physicsinduced; @zehtabiyan2023physicsguided]. This construction defines an instantaneous aerodynamic wake score $s^{\mathrm{wake}}_{i,t}$, which supplies spatial context even when anemometers are noisy. ERA5 employs a symmetric Haversine-Gaussian $k_{\mathrm{nn}}$ graph where thermodynamic sensible heat flux is directly observable [@hersbach2020era5].

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

**Penalized Reserve-Shortfall Energy metric and Newsvendor derivation:** For scheduled point forecast $\hat{y}_{i,t}$ and realized generation $y_{i,t}$, over-forecast shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. Sizing upward reserve margin $r_b$ incurs a reserve procurement energy equivalent $r_b \Delta t$ and an asymmetric shortage penalty $\rho \max(s_{i,t} - r_b, 0) \Delta t$. For penalty ratio $\rho$, the total operational proxy metric is formalized as the **Penalized Reserve-Shortfall Energy Index (PSREI)** in $\text{kW}\cdot\text{h}$ (evaluated here at grid proxy ratio $\rho = 10$):
\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b(i,t) + \rho \max\left(\hat{y}_{i,t} - y_{i,t} - r_b(i,t), \, 0\right) \right]\Delta t.
\end{equation}
Taking the expectation with respect to shortfall distribution $F_S(s) = \Pr[s \le s_0]$ and differentiating with respect to reserve margin $r_b$ yields the first-order optimality condition [@dowell2015veryshortterm; @kruse2023physics]:
\begin{equation}
\frac{\partial \mathbb{E}[C(r_b; \rho)]}{\partial r_b} = 1 - \rho \cdot \Pr\left[ s_{i,t} > r_b \right] = 0 \implies \Pr\left[ s_{i,t} \le r_b \right] = 1 - \frac{1}{\rho}.
\end{equation}
The optimal reserve margin therefore corresponds to the classical Newsvendor critical fractile [@dowell2015veryshortterm]:
\begin{equation}
q^*(\rho) = 1 - \frac{1}{\rho}.
\end{equation}
For the representative proxy ratio $\rho=10$ adopted in this study, the optimal fractile is $q^*(10) = 1 - 1/10 = 0.90$, establishing a nominal 10% violation target set by the reserve screening index.

**Loss geometry: $L_2$ conditional mean vs. Pinball 90th-quantile on shortfall residual:** Conventional point forecasting optimizes symmetric quadratic loss $\mathcal{L}_{L_2}(y, \hat{y}) = (y - \hat{y})^2$, whose Bayes-optimal predictor converges to the conditional expectation $\mathbb{E}[y \mid \mathbf{x}]$ [@dowell2015veryshortterm]. In bounded wind power regimes $y \in [0, P_{\mathrm{rated}}]$ with non-Gaussian and bimodal transition densities, the conditional mean systematically departs from upper conditional quantiles. Furthermore, $L_2$ error treats positive and negative prediction deviations symmetrically, whereas grid balancing economics ($\rho = 10$) penalizes generation shortfalls ten times more heavily than surplus headroom.

To bridge scheduled point forecasts with operational risk hedging, the dispatch architecture first generates point forecast $\hat{y}_{i,t} = f(\mathbf{x}_{i,t})$ and observes realization $y_{i,t}$, inducing the non-negative shortfall residual $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. The upward reserve margin $\hat{r}_{i,t}$ required to cover this residual is estimated via the asymmetric pinball loss at quantile $q$:
\begin{equation}
\mathcal{L}_q(s, \hat{r}) = (s - \hat{r})\left(q - \mathbf{1}[s < \hat{r}]\right) = \begin{cases} q (s - \hat{r}), & s \ge \hat{r} \quad (\text{unhedged shortage}), \\ (1-q)(\hat{r} - s), & s < \hat{r} \quad (\text{surplus reserve headroom}), \end{cases}
\end{equation}
which penalizes unhedged deficit by weight $q$ and reserve holding excess by $1-q$. Setting $q = q^* = 0.90$ aligns the training objective with the Newsvendor first-order condition derived above: the Bayes-optimal predictor converges to the 90th conditional quantile of shortfall $\hat{r}^* = Q_{0.90}(s \mid \mathbf{x})$, targeting a nominal conditional exceedance probability of $\Pr[s > \hat{r} \mid \mathbf{x}] = 1 - q^* = 0.10$ under the Bayes-optimal quantile formulation [@dowell2015veryshortterm; @kruse2023physics]. This formalizes the theoretical underpinning of our downstream Residual Quantile Head.



**Point of Common Coupling (PCC) spatial portfolio smoothing:** Power delivered to the bulk grid is metered at the Point of Common Coupling (PCC) bus: $P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}$ and $R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}$. Fleet-wide spatial aggregation induces a portfolio smoothing effect: uncorrelated local turbulence and turbine-level prediction errors cancel out across the array. Evaluating reserve sizing at the PCC verifies whether learned boundary risk survives spatial cancellation to deliver net plant-level economic value.

**Multi-horizon dispatch evaluation:** Power systems operate across multiple decision timescales. We evaluate two distinct operational horizons: (1) \textbf{Immediate dispatch} ($h=1$, 10-min ahead), representing real-time automatic generation control (AGC) dominated by autocorrelation; and (2) \textbf{Operational dispatch} ($h=6$, 1-hour ahead), representing intra-day clearing and storage scheduling where spatial wake dynamics and weather transitions are paramount.

**Battery Energy Storage System (BESS) rolling dispatch interface:** For co-located wind-storage configurations, scheduled reserve margins and generation forecasts can interface with a rolling Model Predictive Control (MPC) linear program to illustrate downstream operational dispatchability. This formulation serves strictly as an illustrative operational interface demonstrating how reserve margins feed into battery charge/discharge trajectories ($P^{\mathrm{ch}}_t, P^{\mathrm{dis}}_t$) under state-of-charge limits ($E_{\min} \le E_t \le E_{\max}$) and round-trip efficiency constraints. We explicitly do not claim physical validation of electrochemical battery cell degradation, lifecycle capital replacement costs, or wholesale electricity market cashflow settlements; the paper's analytical evaluation and empirical benchmark endpoints remain anchored strictly to the upstream Penalized Reserve-Shortfall Energy Index (PSREI).


# Case Study Configuration and Operational Constraints

## Datasets and preprocessing

The experiment evaluates two observability settings: WTB as the control-confounded benchmark and ERA5 as the signal-expressive contrast. WTB (KDD Cup 2022) comprises 134 turbines and 245 days of 10-min SCADA records ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], where inflow, wake, and pitch control interact, making the MPPT-to-pitch transition indirectly visible. Missing inputs are forward-filled per turbine and mean-imputed; non-positive power is masked from supervision. ERA5 covers three archived months on a $16 \times 16$ hourly patch ($T=2208$, $N=256$, eight features) [@hersbach2020era5], where sensible heat flux directly marks convective regimes. Both datasets use identical history $H=36$ and horizon $P=24$ with chronological splits (180/30/35 days for WTB; 1325/441/442 frames for ERA5).

## Techno-Economic Validation and Benchmarking Framework

The benchmarking framework evaluates two complementary axes: (1) isolating routing mechanisms under matched parameter capacity (Dense single-head baseline, Unconstrained MoE, and Physics-Aligned MoE comparator) [@shazeer2017outrageously; @fedus2022switch]; and (2) benchmarking forecasting accuracy and reserve cost against established spatio-temporal baselines (Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE) [@nie2023patchtst; @liu2024itransformer; @das2023longterm], alongside persistence, deterministic aerodynamic curves, and GBDT lag models. In mechanism comparisons, in-family architectures are designated **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**; baseline configurations are detailed in Supplementary Appendix\ A.

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in Supplementary Appendix\ A so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE across seeds 201--205, giving 30 completed baseline runs under the same strict anchor-valid evaluation cache. Deterministic engineering baselines (persistence, physical curves) are evaluated on the frozen cache to anchor practical dispatch difficulty alongside five-seed neural models. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

Evaluation metrics span three operational criteria: (1) point forecasting accuracy (overall MAE/RMSE and switch-window RMSE within $\pm 1.0\text{ m s}^{-1}$ of rated wind); (2) physical regime alignment (normalized mutual information, adjusted Rand index, and gate usage entropy); and (3) operational reserve consequence (PSREI cost, empirical violation rate, and unhedged shortage MWh under the Newsvendor proxy).

## Controlled Telemetry Degradation Protocols

To stress-test model resilience under adverse field conditions, we formalize four controlled telemetry regimes across all 5 seeds (201--205): (1) \textbf{Clean (Nominal):} uncorrupted SCADA telemetry; (2) \textbf{Delay-6 (Worst-Case Communication Stress Test, Upper Envelope):} 6-step ($60\text{ min}$) controlled synthetic latency on wind-speed and pitch-angle streams, representing a conservative severity bound on severe communication backlog, buffer congestion, serialization queuing, and gateway outage cascades in industrial IoT telemetry [@ullah2022enabling; @pierre2019design]; this 60-min scenario is evaluated as a deliberate stress-test upper envelope to delineate worst-case physical rule vulnerability; (3) \textbf{Sensor Noise:} additive zero-mean Gaussian perturbations on wind speed ($\sigma = 1.0\text{ m s}^{-1}$) and pitch angle ($\sigma = 2.0^\circ$), simulating calibration drift and sensor jitter; and (4) \textbf{Markov-Gilbert Burst Drops:} two-state discrete Markov chain ($p_{GB} = 0.08, p_{BB} = 0.75, d \le 6$) simulating bursty communication blackouts [@ullah2022enabling; @ravikumar2020anomaly].

Fig. 1 illustrates the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors: (A) WTB layout with wake cone geometry (25° half-angle); (B) ERA5 patch with sensible heat flux; (C) WTB operating regimes in $(Wspd, Pab_{\mathrm{mean}})$ plane with MPPT-to-pitch boundary; (D) ERA5 thermodynamic regimes in $(sshf, \Delta sshf)$ plane.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=58% }

# Evidence and Operational Boundary Diagnosis

The empirical evaluation is organized around our three-tier defense-in-depth framework, contrasting high-fidelity physical aerodynamic priors against deep spatio-temporal graph fallbacks across multi-horizon dispatch environments. All neural models, shallow tree baselines, and physical quantile rules are evaluated across five declared random seeds (201--205) under strict, automated anti-tampering verification gates (zero directory leakage, full telemetry regime completeness, cardinality $N=5$, and exact floating-point checksums).

## Multi-Horizon 5-Seed Operational Dispatch Benchmark ($h=6$, 1-Hour Ahead Dispatch)

Table\ \ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) across 134 turbines over the 35-day test split. Table\ \ref{tab:h6-paired} reports seed-paired cost differences $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, where positive values denote economic savings delivered by Joint Routed, along with 95\% bootstrap confidence intervals.

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
\multicolumn{7}{@{}p{\textwidth}@{}}{\tiny $^{\dagger}$Exceeds nominal 10\% violation target ($q^* = 0.90$). Bold numbers denote lowest cost. \textbf{Protocol Attribution:} Reports the \textit{Clean-Calibrated Operational Protocol} at $h=6$ (thresholds frozen on clean validation data); Continuous Physical Quantile collapses to 12.20\% violation under Delay-6. For the \textit{State-Conditional Validation-Calibrated Protocol} at immediate horizon ($h=1$), see Section~\ref{sec:physical-breakdown}, where clean-calibrated physical rules collapse to 24.0\% violation under Delay-6 while state-conditional calibration mitigates violations to 10.7\% (physical) and 10.6\% (joint model). Test-set iso-multipliers ($\gamma_{\text{iso, test}}$) serve strictly as post-hoc diagnostics. $^{\ddagger}$Direct pinball regression on frozen embeddings exhibits severe tail conservatism (>1.63M kW reserve, <1.2\% violation). For calibrated modular baselines (Cascaded Frozen MLP $15.528\text{M} \pm 1.599\text{M}$ vs Joint Routed 16.065M in statistical parity), see Section~\ref{sec:modular-baseline}.}
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
 & Cont. Physical Quantile & $-$27,126 & [$-$46,907, $-$7,346] & Viol. Exceeded ($12.20\%$) \\
 & Missingness GBDT & +156,411 & [+140,004, +172,817] & Yes ($p < 0.0001$) \\
 & Frozen Backbone Direct MLP & +518,658 & [+307,212, +730,104] & Yes ($p < 0.01$) \\
 & Joint Dense Head & +16,267 & [+7,131, +25,402] & \textbf{Yes} ($p = 0.0251$) \\
\midrule
\textbf{Noise} & Global Quantile & +26,475 & [+9,121, +43,828] & Yes ($p < 0.05$) \\
 & Cont. Physical Quantile & $-$28,804 & [$-$47,555, $-$10,053] & Viol. ($7.59\%$) \\
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

### Comparative Architecture Analysis: Dynamic Routing versus Dense Representations
A central architectural question is whether dynamic MoE routing confers essential operational value over unrouted dense heads of matched capacity. Under nominal Clean conditions, Joint Routed ($959{,}027 \pm 103{,}290\text{ kW}\cdot\text{h}$ at $h=6$; $660{,}990 \pm 80{,}749\text{ kW}\cdot\text{h}$ at $h=1$) and Joint Dense Head ($991{,}181 \pm 110{,}211\text{ kW}\cdot\text{h}$ at $h=6$; $690{,}614 \pm 71{,}031\text{ kW}\cdot\text{h}$ at $h=1$) achieve statistical parity: at $h=6$, the seed-paired cost difference is $+32{,}154\text{ kW}\cdot\text{h}$ (bootstrap 95% CI $[-1{,}148, +65{,}456]\text{ kW}\cdot\text{h}$ crossing zero, Table\ \ref{tab:h6-paired}); at $h=1$, the Dense/MoE cost ratio is $1.045$, and the seed-paired bootstrap 95% CI on cost difference ($+29{,}624\text{ kW}\cdot\text{h}$) likewise crosses zero ($[-53{,}774, +113{,}023]\text{ kW}\cdot\text{h}$, $p=0.380$), as does the Markov regime ($[-46{,}422, +139{,}671]\text{ kW}\cdot\text{h}$, $p=0.237$). Under persistent 6-step latency (Delay-6, $h=1$), Joint Routed yields a modest cost improvement over Joint Dense ($1{,}412{,}321$ vs. $1{,}491{,}958\text{ kW}\cdot\text{h}$; cost ratio $1.056$, paired difference $+79{,}637\text{ kW}\cdot\text{h}$, uncorrected $p=0.038$, non-significant under Bonferroni $\alpha=0.0125$) while maintaining virtually identical empirical violation rates ($10.6\% \pm 1.1\%$ for Routed vs. $10.5\% \pm 0.5\%$ for Dense). Decoupled modular representations (Section\ \ref{sec:modular-baseline}) achieve $9.7\% \pm 1.1\%$ violation in Delay-6 without expert routing, confirming that diagnostic reserve utility arises from shared spatio-temporal representations.

### Reliability Breakdown of Deterministic Physical Rules under Stale Telemetry \label{sec:physical-breakdown}
Under uncorrupted SCADA telemetry, Continuous Physical Quantile achieves the lowest baseline PSREI cost ($589{,}535 \pm 74{,}886\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$ at $h=6$) with well-calibrated violation rates ($6.81\% \pm 1.13\%$ at $h=6$).

However, Table\ \ref{tab:h6-benchmark} and frozen benchmarks expose a **systematic reliability breakdown** under telemetry staleness. Under a 6-step delay (Delay-6), clean-calibrated physical quantile rules experience a violation explosion to $\mathbf{24.0\% \pm 1.7\%}$ at $h=1$ and $\mathbf{12.20\% \pm 1.25\%}$ at $h=6$, breaching the nominal 10\% violation target ($q^* = 0.90$) and inflating operational reserve costs to $1{,}136{,}466 \pm 84{,}101\text{ kW}\cdot\text{h}$ at $h=6$ (incurring $47{,}413 \pm 3{,}091\text{ kW}\cdot\text{h}$ of unhedged shortage) and $1{,}656{,}285\text{ kW}\cdot\text{h}$ at $h=1$ (leaving $127.6\text{ MWh}$ of unhedged shortfall exposure in the balancing proxy). Quantitative decomposition reveals that adapting validation calibration to degraded states alone cuts shortage from $127.6\text{ MWh}$ ($24.0\%$ violation) to $57.0\text{ MWh}$ ($10.7\%$ violation), accounting for $55.3\%$ of the reduction and recovering physical reserve cost to $1{,}228{,}609 \pm 71{,}940\text{ kW}\cdot\text{h}$ ($h=1$ condition-recalibrated, $9.46\%$ fleet violation). Joint Routed further curtails shortage to $53.9\text{ MWh}$ ($10.6\% \pm 1.1\%$ violation), delivering an additional $5.4\%$ shortage reduction under matched state-conditional calibration (and a combined $57.7\%$ reduction vs. clean-calibrated physics) while saving $190{,}590\text{ kW}\cdot\text{h}$ in total cost. Learned representations thus establish an effective diagnostic defense against telemetry latency: under frozen validation calibration, Delay-6 empirical violation settles at $10.6\% \pm 1.1\%$ at $h=1$ ($11.82\% \pm 1.64\%$ at $h=6$). While substantially cushioning physical rule collapse, learned models operate within bounded empirical envelopes under multi-step latency.

### Decoupled Modular Architectures and Tail Conservatism Analysis \label{sec:modular-baseline}
In contrast to end-to-end task optimization, the Frozen Backbone Direct Quantile MLP in Table\ \ref{tab:h6-benchmark} illustrates the pathology of naive decoupled quantile regression. Across all regimes, direct pinball regression on frozen spatial embeddings incurs massive reserve over-estimation ($1{,}477{,}967$ to $1{,}511{,}794\text{ kW}\cdot\text{h}$, a $44.57\%$ to $72.02\%$ penalty over Joint Routed, $p < 0.01$, Table\ \ref{tab:h6-paired}), hoarding $>1.45\text{M kW}$ in bloated reserves.

Benchmarking calibrated modular architectures across 5 seeds (Supplementary Table\ A11d) resolves this:
1. **Cascaded Frozen MLP:** Trained with consequence decision mapping on frozen backbone embeddings, it achieves $15.528\text{M} \pm 1.599\text{M kW}\cdot\text{h}$ (vs. $16.065\text{M kW}\cdot\text{h}$ for Joint Routed; paired difference $-0.537\text{M}$, 95\% CI $[-1.988\text{M}, +0.915\text{M}]$ crosses zero).
2. **Independent Consequence MLP:** Yields $15.805\text{M} \pm 1.680\text{M kW}\cdot\text{h}$ (difference $-0.260\text{M}$, 95\% CI $[-1.771\text{M}, +1.251\text{M}]$), confirming statistical parity.
3. **Decoupled Residual Quantile Head:** In Delay-6 ($h=1$), Frozen Backbone + Residual Quantile achieves $1{,}284{,}098 \pm 114{,}629\text{ kW}\cdot\text{h}$ and $9.7\% \pm 1.1\%$ violation (60% seed pass rate), matching or slightly surpassing end-to-end MoE ($1{,}412{,}321\text{ kW}\cdot\text{h}$, $10.6\% \pm 1.1\%$).

Consequently, diagnostic reserve benefits do not require dynamic MoE routing: modular architectures with calibrated consequence mappings deliver equivalent tail reliability. The primary advantage of end-to-end joint training is unified single-checkpoint deployment on substation edge devices (110k parameters, $<5\text{ ms}$ inference), eliminating multi-model synchronization overhead.

## Horizon Boundary Diagnosis ($h=1$, 10-Minute Immediate Dispatch vs. $h=6$)

Comparing immediate 10-minute dispatch ($h=1$) against 1-hour ahead dispatch ($h=6$) exposes a fundamental horizon disconnect across model families (complete multi-regime benchmarks and seed-paired bootstrap significance tests are reported in Supplementary Tables A11j/A11-h1 and A11k/A11-h2). At $h=1$, shallow decision trees (Missingness-Aware GBDT) capitalize aggressively on high 10-minute lag wind-speed autocorrelation, achieving the lowest data-driven nominal dispatch cost ($574{,}822 \pm 79{,}685\text{ kW}\cdot\text{h}$ in Clean with $7.6\%$ violation, outperforming all deep models). Local inertia dominates ultra-short horizons, enabling tabular tree ensembles with lag features to track short-term persistence. However, across dispatch-grade horizons ($h=6$), GBDT undergoes severe breakdown: its operational costs inflate by $13.44\%$ to $29.15\%$ (reaching $1{,}238{,}603\text{ kW}\cdot\text{h}$ in Clean and $1{,}320{,}003\text{ kW}\cdot\text{h}$ in Delay-6), trailing Joint Routed by $+156{,}411$ to $+287{,}563\text{ kW}\cdot\text{h}$ across all regimes ($p < 0.0001$, Table\ \ref{tab:h6-paired}). Because tabular trees lack spatial awareness of aerodynamic wake advection propagating at $8$--$12\text{ m s}^{-1}$ across turbine rows, they cannot represent multi-turbine spatio-temporal phase shifts over 1-hour lead times.

At immediate horizon $h=1$, Joint Dense Head and Joint Routed exhibit statistical parity across Clean, Noise, and Markov regimes, where bootstrap 95\% confidence intervals cross zero (Supplementary Table\ A11-h2, e.g., $+29{,}624\text{ kW}\cdot\text{h}$, 95\% CI $[-53{,}774, +113{,}023]$, $p=0.380$ in Clean). In Delay-6, Joint Routed holds a modest cost advantage ($+79{,}637\text{ kW}\cdot\text{h}$, 95\% CI $[+7{,}055, +152{,}218]$, uncorrected $p=0.038$, non-significant under Bonferroni $\alpha=0.0125$) while matching empirical violation rates ($10.6\% \pm 1.1\%$ vs. $10.5\% \pm 0.5\%$). Across both horizons, unadapted physical rules exhibit shared vulnerability to telemetry staleness, collapsing under Delay-6 to $24.0\% \pm 1.7\%$ violation at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, confirming that aerodynamic power curves require dynamic state adaptation under communication latency.

## Multidimensional Operational Boundaries and Selective Decision Abstention

To delineate the operational boundaries governing telemetry degradation, we scan across transmission delays $\tau \in \{0, 10, 20, 30, 60\}\text{ min}$, horizons $h \in \{1, 3, 6\}$, and pitch channel observabilities (\texttt{all} vs. \texttt{no\_pitch}) across all 5 seeds on the 134-turbine WTB plant (Table\ \ref{tab:phase-scan}). This empirical trajectory delineates a **Three-Regime Operational Framework**:

1. **Regime I: Simple Recalibration Sufficient ($\tau = 0\text{ min}$ or mild delays under full observability):** Under fresh telemetry ($\tau=0$, \texttt{all}), deterministic continuous physical quantiles achieve the lowest operational reserve cost ($593{,}258 \pm 74{,}886\text{ kW}\cdot\text{h}$ at $h=1$ across the phase-scan sweep, aligning within $0.6\%$ of the primary $589{,}535\text{ kW}\cdot\text{h}$ benchmark, with well-calibrated $7.29\% \pm 1.42\%$ violation). Machine-learning representations incur reserve penalties without reliability gains ($663{,}347\text{ kW}\cdot\text{h}$ for modular frozen backbones, $+11.8\%$). When telemetry latency increases to $\tau \in [10, 30]\text{ min}$ with all channels observable, clean-calibrated physical rules collapse ($11.18\% \to 13.98\% \to 16.58\%$). However, state-conditional recalibration fully restores physical compliance ($7.1\%\text{--}7.5\%$ violation) at lower cost than neural models ($742{,}211\text{--}939{,}190\text{ kW}\cdot\text{h}$ vs. $786{,}366\text{--}987{,}760\text{ kW}\cdot\text{h}$), demonstrating that simple recalibration is sufficient when all telemetry channels remain observable.
2. **Regime II: Learned Representation Advantage (Unobservable pitch channels / partial observability):** When blade-pitch telemetry is withheld across aggregator or OEM boundaries (\texttt{no\_pitch}), physical aerodynamic rules lose direct rotor state awareness. Recalibrated physics based solely on wind-speed binning inflates reserve costs ($824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$; $928{,}028\text{ kW}\cdot\text{h}$ at $\tau=10$; $1{,}010{,}530\text{ kW}\cdot\text{h}$ at $\tau=20$; $1{,}101{,}292\text{ kW}\cdot\text{h}$ at $\tau=30$; $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60$). In contrast, learned representations (\textit{Frozen Backbone + Residual Quantile}) reconstruct operating states from electromechanical transients (active/reactive power, rotor speed), achieving $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ cost reduction of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintaining consistent cost savings across all latencies ($866{,}753\text{ kW}\cdot\text{h}$ at $\tau=10$, $-61.3\text{k}$; $947{,}869\text{ kW}\cdot\text{h}$ at $\tau=20$, $-62.7\text{k}$; $1{,}054{,}592\text{ kW}\cdot\text{h}$ at $\tau=30$, $-46.7\text{k}$; $1{,}330{,}318\text{ kW}\cdot\text{h}$ at $\tau=60$, $-48.6\text{k}$).
3. **Regime III: Compound Breakdown and Conservative Safeguards ($\tau = 60\text{ min}$, Delay-6):** Under 60-minute latency, unadapted physical rules experience systematic collapse ($24.02\% \pm 1.69\%$ violation, incurring $127.6\text{ MWh}$ of unhedged shortfall exposure). Condition-matching recalibration restores fleet-average violation below the $10.0\%$ target across all three model families ($9.46\%$ for physical rules, $9.55\%$ for Frozen Backbone, and $9.62\%$ for Joint Routed), with the recalibrated physical rule delivering the lowest operating cost ($1{,}228{,}609\text{ kW}\cdot\text{h}$). This directly refutes the prior assumption that multi-step SCADA latency unconditionally collapses all models or makes selective rejection mandatory to meet fleet-average compliance. However, fleet-average compliance conceals critical tail risk: across the 5 random seeds, every method achieves strictly a $3/5$ ($60\%$) seed compliance rate, as Seeds 201 and 203 experience residual breaches ($10.2\%\text{--}10.7\%$) across all architectures. In this severe telemetry regime, unconstrained neural optimization is vulnerable to tail risk.

```{=latex}
\begin{table}[!htbp]
\centering
\fontsize{5.2pt}{6.0pt}\selectfont
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.75}
\caption{Multidimensional operational progression across telemetry latency $\tau \in [0, 60]\text{ min}$ and pitch observability ($h=1$, 5-seed mean on WTB; nominal $\tau=0$ baseline $593{,}258\text{ kW}\cdot\text{h}$ aligns within $0.6\%$ of the primary frozen $589{,}535\text{ kW}\cdot\text{h}$ benchmark). Cost in kW$\cdot$h ($\rho=10$).}
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

To safeguard operations in Regime III under communication stress, analogous to wide-area power system controllers where telemetry delays trigger watchdog-governed fallbacks [@pierre2019design] or anomaly mitigations [@ravikumar2020anomaly], we evaluate a **Selective Decision Abstention (Risk-Coverage Policy)**:
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
where $[x]_0^{P_{\text{rated}}} = \min(\max(x, 0), P_{\text{rated}})$ clamps available generation headroom against rated nameplate capacity ($P_{\text{rated}} = 1{,}500\text{ kW}$), lower-bounded by the condition-recalibrated aerodynamic quantile rule $r_{i,t}^{\text{phys, recal}}$. To audit this mechanism, Table\ \ref{tab:risk-coverage} benchmarks selective abstention against two mandatory controls: **Random Abstention** (matching realized empirical coverage $\hat{c}$) and **Uniform Margin Inflation** (evaluated both as an ex-post equal-budget diagnostic benchmark matching total fleet reserve MWh, and as an ex-ante deployable policy with inflation multiplier $\alpha_{\text{val}}$ calibrated on validation data).

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

The empirical audit reveals that **heuristic uncertainty scores (predictive entropy and quantile spread) fail to reliably isolate tail shortfall risk under severe telemetry staleness.** Under observable telemetry (\texttt{all}), target coverage $c=0.90$ yields a realized empirical coverage of $\hat{c} = 93.42\% \pm 0.81\%$, but selective abstention reduces fleet violation only marginally ($9.62\% \to 9.44\%$ for Joint Routed; $9.52\% \to 9.30\%$ for Frozen Backbone). This reduction is statistically indistinguishable from random abstention ($9.50\%$ and $9.36\%$, $p > 0.40$), while by-seed compliance remains strictly $3/5$ seeds ($60\%$), as Seed 201 accepted violation actually rises to $10.48\%$ (vs. $10.22\%$ unrejected). Under withheld pitch (\texttt{no\_pitch}), selective abstention is strictly Pareto-dominated by uniform margin inflation: at $c=0.50$, selective abstention costs $1{,}371{,}729\text{ kW}\cdot\text{h}$ ($8.84\%$ viol), whereas ex-post test-matched uniform margin inflation achieves lower violation ($8.29\%$) at lower total cost ($1{,}333{,}906\text{ kW}\cdot\text{h}$, saving $37{,}823\text{ kW}\cdot\text{h}$), and ex-ante validation-frozen inflation achieves $7.12\%$ violation at $1{,}348{,}361\text{ kW}\cdot\text{h}$ (saving $23{,}368\text{ kW}\cdot\text{h}$). Because stale SCADA telemetry corrupts both the point prediction and the uncertainty proxy, selective rejection incurs the penalty of bloated fallback reserves on safe turbines while missing true tail shortfalls. In industrial operations facing multi-step SCADA disruption, **uniform reserve margin inflation and aerodynamic physical fallbacks provide more reliable, cost-effective risk hedging than heuristic selective abstention.**


## Operating-Boundary Recovery and Point-Forecast Price of Routing

Evaluating point-forecasting accuracy across five WTB seeds, the boundary-forced router achieves an overall RMSE of 236.13 +/- 8.41, compared with 224.34 +/- 2.23 for iTransformer and 225.74 +/- 2.60 for Graph WaveNet (a margin of 11.79 units vs. iTransformer and 10.39 units vs. Graph WaveNet). Provenance-corrected train-only class weighting narrows this gap to 5.59 units (reaching 229.93 +/- 2.50). While unconstrained models optimize solely for whole-sample RMSE, they lack operating-state awareness and suffer severe reliability degradation under telemetry impairments. In contrast, the boundary-forced router preserves physical state alignment, achieving NMI 0.8716 +/- 0.0418 and ARI 0.9166 +/- 0.0371 under strict masking (NMI 0.721 and ARI 0.740 under train-only supervision).

Input ablation stress guards confirm that routing fidelity does not arise from target leakage: withholding \texttt{Patv} or \texttt{Pab\_mean} preserves mean NMI at 0.881 and 0.878, while lagging \texttt{Patv} and lagging pitch/wind yield 0.763 and 0.684. In addition, gate matching to the active operating regime peaks at the transition step (0.815) and attenuates under three- and six-step lead shifts (0.361 and 0.405), confirming that gate activations track dynamic physical state transitions.

## Withheld-Channel Electromechanical Signature Recovery

The integrity of the Tier 2 blind-spot fallback rests on whether the model can infer operational regime boundaries when defining anemometer or pitch channels are unavailable. In operational practice, internal turbine blade-pitch telemetry may be delayed by SCADA network latency or unobservable to third-party aggregators, VPP coordinators, and TSOs due to commercial OEM protocol boundaries. To test whether non-pitch electromechanical consequence channels carry sufficient information to recover regime transitions without circular dependence, we formulate a strict **counterfactual stress-testing probe**: zeroing `Wspd` and `Pab_mean` while retaining active power and downstream electromechanical channels yields a mean NMI of 0.561 and ARI of 0.635 across five seeds on WTB (Table\ \ref{tab:signature-gate}). Removing active power (`signature_core`) drops mean NMI to 0.367, whereas permuted label negative controls collapse to $4.0 \times 10^{-6}$, definitively ruling out spurious correlations.

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

To prevent over-generalization and evaluate external deployment boundaries, we strictly disentangle three disparate lines of external empirical evidence across commercial plants:

1. **Within-plant local retraining (ENGIE La Haute Borne & UK dual-farm replication):** Models trained and evaluated locally under site-specific rated aerodynamic parameters demonstrate that the neural architecture adapts to distinct turbine technologies, confirming that consequence signatures are recoverable from electromechanical transients without direct pitch observation:
- **ENGIE La Haute Borne (4 turbines, 99\% pitch, $v_{\mathrm{rated}}=14.5\text{ m s}^{-1}$):** Withheld-channel probe retains an NMI of 0.674 for `signature_full` and 0.575 for `signature_core` (collapsing to $1.92 \times 10^{-4}$ under permuted controls; five-seed routing NMI 0.941, ARI 0.971).
- **Kelmarsh (6 Senvion MM92 turbines, $v_{\mathrm{rated}}=12.5\text{ m s}^{-1}$):** With defining wind-speed and pitch-angle channels withheld, `signature_full` achieves an NMI of $0.3402 \pm 0.0736$ (3700x above shuffled chance). In 5-seed local chronological dispatch replay at $h=6$, locally retrained Joint Routed yields $70{,}375 \pm 16{,}324\text{ kW}\cdot\text{h}$ (Clean) and $109{,}359 \pm 13{,}634\text{ kW}\cdot\text{h}$ (Delay-6), outperforming GBDT ($+44{,}891\text{ kW}\cdot\text{h}$ and $+29{,}621\text{ kW}\cdot\text{h}$, $p < 0.05$) and continuous physical quantiles ($82{,}456\text{ kW}\cdot\text{h}$ and $116{,}409\text{ kW}\cdot\text{h}$).
- **Penmanshiel (15 Senvion MM82 turbines, $v_{\mathrm{rated}}=14.5\text{ m s}^{-1}$):** With defining channels withheld, `signature_full` achieves $0.3024 \pm 0.0343$ (6800x above shuffled chance). In local dispatch replay at $h=6$, locally retrained Joint Routed yields $831{,}251 \pm 112{,}331\text{ kW}\cdot\text{h}$ (Clean) and $813{,}831 \pm 102{,}946\text{ kW}\cdot\text{h}$ (Delay-6), versus GBDT ($1{,}064{,}962\text{ kW}\cdot\text{h}$ and $1{,}086{,}102\text{ kW}\cdot\text{h}$, $p < 0.001$), where GBDT experiences severe violation inflation ($24.7\%$ to $26.5\%$).
These empirical findings demonstrate model architecture adaptability to site-specific aerodynamic rated parameters under local retraining, rather than uncalibrated zero-shot cross-farm generalizability.

2. **Directional transfer boundaries across disparate wind plants:** In contrast to local chronological retraining, direct zero-shot cross-farm transfer without site-specific recalibration reveals pronounced directional transfer sensitivity. As audited by our pre-registered external wind guard (`external_wind_guard.json`), transferring representations from Kelmarsh to Penmanshiel preserves moderate boundary alignment (NMI $0.752$--$0.770$), whereas reverse transfer from Penmanshiel to Kelmarsh yields NMI $0.341$--$0.505$ (pooled bidirectional mean NMI $0.557$). This directional asymmetry demonstrates that aerodynamic operating boundaries are intimately coupled to turbine rotor dimensions and local wake topographies, establishing that reliable multi-farm deployment requires site-specific sensor calibration and local retraining.

3. **Longitudinal multi-year operational stability:** Across decadal longitudinal archives (Kelmarsh, 9 years; Penmanshiel, 8.6 years), walk-forward evaluations examine periodic quantile recalibration under multi-year climatological drift and turbine component aging. These longitudinal evaluations demonstrate the operational mechanics of periodic schedule recalibration across multi-year operating horizons, establishing empirical baselines for long-term fleet management under environmental drift.

## Degradation Resilience and Early Warning Dynamics

Table\ \ref{tab:early-warning} stress-tests detection fidelity when issue-time telemetry is delayed or corrupted under the Unified Arrival Layer. Under clean anchors, the deterministic threshold rule remains the stronger detector (1.000 versus 0.9705), and clean logistic regression reaches 1.000 recall with 0.879 precision (above the routed posterior's 0.630). Under a 6-step delay ($d=6$) with full-stream history shift (where both anchor readings and encoder history stall by 60 minutes), the deterministic threshold rule's recall collapses from $1.000$ to $0.196$, its precision drops to $0.342$, and its F1 score collapses to $0.249$. In contrast, the jointly-learned routed posterior maintains an early-window recall of $0.4170 \pm 0.1137$ (+0.221 over the rule, more than doubling detection sensitivity) and an F1 score of $0.3802$ (+0.131 over the rule). When telemetry stalls for 60 minutes, detection recall naturally attenuates from 0.971 to 0.417, but the spatio-temporal graph representations double the surviving resilience without any clean-history information leaks.

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

## Point of Common Coupling (PCC) Portfolio Smoothing & Exploratory Longitudinal Drift Analysis

To verify reserve behavior under spatial aggregation, we evaluate aggregate power at the Point of Common Coupling (PCC) bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, averaging $\sim 121$ active turbines). Across the full operational envelope, joint posterior aggregate quantile pricing reduces reserve cost by $-2.32\text{M kWh}$ (95\% bootstrap CI $[-6.07\text{M}, 1.73\text{M}]$) against global PCC quantiles and by $-1.37\text{M kWh}$ (CI $[-6.33\text{M}, 2.82\text{M}]$) against Gaussian parametric sizing; in transitional regimes (10\%--90\% pitching), it saves $-1.33\text{M kWh}$ (CI $[-1.68\text{M}, -1.07\text{M}]$, strictly excluding zero) over continuous physical pitch, confirming relative risk mitigation after fleet-wide error cancellation. Furthermore, closing the loop with physical storage, receding-horizon Model Predictive Control (MPC) dispatch with a co-located battery energy storage system (BESS, 20\,MWh / 10\,MW) reduces Delay-6 dispatch cost by 32.1\% (\$487,746 to \$331,257) and cuts shortage energy by 45.7\% (2,514.9 to 1,401.2\,MWh; Supplementary Table\ A11-BESS). We emphasize that reported upstream values represent the PSREI risk proxy ($\rho=10$) rather than wholesale financial settlement cashflows.

Across two European commercial wind plants with longitudinal records (Kelmarsh, 9 years, 2016--2024, 6 MM92 turbines; Penmanshiel, 8.6 years, 2016--2024, 15 MM82 turbines), exploratory evaluations examine periodic quantile recalibration under multi-year climatological drift and turbine aging. These longitudinal evaluations illustrate the operational mechanics of periodic schedule recalibration across decadal operating horizons, establishing empirical baselines for long-term fleet management.

# Discussion

## Accuracy, accountability and deployment gates

The operational role of the boundary-aware architecture is a specialized diagnostic for reserve risk screening rather than an unconstrained whole-sample point predictor. When bulk energy scheduling operates under pristine SCADA telemetry, unconstrained spatio-temporal architectures (Graph WaveNet, iTransformer) deliver superior aggregate accuracy; conversely, when telemetry is delayed, corrupted, or pitch-withheld, boundary-risk posteriors provide indispensable diagnostic defense. To ensure rigorous external validation, we strictly disentangle three lines of empirical evidence:
(a) **Cross-farm directional transfer boundaries:** Direct zero-shot transfer across disparate commercial plants exhibits pronounced directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$, ARI $0.735$--$0.761$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.341$--$0.505$, pooled bidirectional mean NMI $0.557$; `external_wind_guard.json`), confirming that unadapted cross-farm deployment is circumscribed by local aerodynamic geometry, and that reliable multi-site transfer requires site-specific sensor recalibration.
(b) **Within-plant local retraining:** Local chronological training across ENGIE La Haute Borne (five-seed routing NMI 0.941, ARI 0.971; canonical NMI 0.975; withheld probe 0.674/0.575), Kelmarsh (probe 0.340/0.378), and Penmanshiel (probe 0.302, `signature_core` 0.195; Supplementary Table\ A9d) confirms neural architectural adaptability to site-specific aerodynamic rated speeds.
(c) **Longitudinal rolling walk-forward evaluation:** Across longitudinal multi-year records (Kelmarsh, 9 years; Penmanshiel, 8.6 years), periodic 2-year sliding window evaluations characterize operational recalibration mechanics under climatological drift, tracking parameter evolution over decadal operating horizons.

External walk-forward rolling evaluation establishes empirical physical boundary conditions for the pre-registered admission protocol (Supplementary Table\ A14). On ENGIE La Haute Borne (4 turbines, 99\% complete pitch), walk-forward pooled quarterly evaluation (Q1--Q3) incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus continuous physical pitch (Supplementary Table\ A11h). This reveals quantile variance amplification under acute seasonal drift: on a miniature 4-turbine site without Point of Common Coupling (PCC) spatial portfolio smoothing, short quarterly slices suffer variance spikes during autumn regime shifts (+968.1k kWh in Q3, while Q1--Q2 cross zero). Expanding calibration to a 180-day annual window compresses the cost gap to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero), bounding soft-posterior reserves to PCC-smoothed plants and degraded/pitch-sparse telemetry.

Evaluating across shortage penalty ratios $\rho \in \{5, 10, 20\}$ articulates an operational envelope ("Telemetry Availability $\times$ Penalty Ladder"). At $\rho=10$, learned posteriors dominate unconditioned baselines. At $\rho=20$, asymmetry emerges: at Kelmarsh, physical rules recover and surpass soft-gate pricing by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); at Penmanshiel, the soft gate leads physical rules by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) while crossing zero versus the unconditioned global baseline ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$). Direct reserve deployment at new farms requires pitch or proxy observability, boundary support, compatible geometry, local recalibration, and a held-out validation pass [@tautzweinert2017scada].

# Limitations

WTB pseudo-labels derive from wind speed and pitch angle, channels present in full gate anchors. Counterfactual withheld-channel stress testing confirms that the boundary survives without direct pitch observations via consequence signatures across four farms (permuted controls at chance). Removing pitch dispersion retains non-power NMI 0.309 on WTB and 0.578 on La Haute Borne, confirming dispersion does not carry the signal. Yet boundary identification remains an anchor-constrained diagnostic rather than anchor-free discovery [@karniadakis2021piml; @zehtabiyan2023physicsguided]. Inputs may contain history $\texttt{Patv}_{t-H+1:t}$ and issue-time $\texttt{Patv}_{t}$, while targets begin at $t+1$. Expert semantics reflect the declared mapping; unassigned logits are not universal physical states.

Our analytical evaluation is formally bounded to Level 1 local pre-dispatch risk screening proxies (Penalized Reserve-Shortfall Energy Index, PSREI at $\rho=10$), designed to minimize unhedged imbalance entering real-time balancing. This local screening explicitly abstracts away Level 2 transmission operations, including AC-OPF, network thermal and voltage constraints, security-constrained unit commitment, and multi-stage market settlements [@bremnes2004quantile; @zhou2013probabilisticmarkets]. Strongest claims remain five-seed WTB recovery, mechanism intervention, La Haute Borne local replication, and same-router reserve triage.

# Conclusion

This study exposes the operational vulnerability and reliability breakdown of deterministic wind turbine operating reserve rules under SCADA telemetry degradation and evaluates jointly-learned boundary-risk posteriors as relative mitigators and diagnostic instruments. Across a 5-seed benchmark on the 134-turbine WTB plant, continuous aerodynamic quantile rules achieve the lowest PSREI reserve-screening cost under pristine telemetry ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$), but undergo systematic reliability collapse under a 6-step ($60\text{ min}$) delay, surging violation rates to $24.0\% \pm 1.7\%$ ($h=1$) and $12.20\% \pm 1.25\%$ ($h=6$). Under Delay-6, Continuous Physical Quantile reaches $1{,}136{,}466 \pm 84{,}101\text{ kW}\cdot\text{h}$ at $h=6$ and $1{,}228{,}609 \pm 71{,}940\text{ kW}\cdot\text{h}$ at $h=1$ under condition-matching recalibration.

Under frozen validation calibration, state-conditional recalibration of physical rules recovers violation to $10.7\%$ and cuts shortage from $127.6\text{ MWh}$ to $57.0\text{ MWh}$ ($55.3\%$ reduction), while learned boundary-risk posteriors provide an additional $5.4\%$ reduction to $53.9\text{ MWh}$ (a combined $57.7\%$ reduction) and double regime recall ($0.416$ vs. $0.196$ under Delay-6). However, data-driven representations alone do not provide unconditional fail-safe operation: under 6-step latency, empirical violation rates settle at $10.6\% \pm 1.1\%$, demonstrating that learned models substantially alleviate, but cannot completely eliminate, reserve breakdown without conservative margin safeguards. Capacity-matched Dense and MoE heads achieve statistical parity in Clean (cost ratio $1.045$, $p=0.380$) with a modest Delay-6 margin (ratio $1.056$, uncorrected $p=0.038$), while modular architectures match tail reliability ($9.7\%$ violation), indicating that operational value originates from shared spatio-temporal representations rather than dynamic routing. Direct zero-shot cross-farm transfer exhibits directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled $0.557$), bounding reliable deployment to sites with local retraining (ENGIE La Haute Borne, NMI $= 0.941$). These findings reframe data-driven reserve models into rigorous, accountable diagnostic tools that delineate the physical and communication boundaries of smart grid operations.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.

# Code and data availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public (raw third-party data not redistributed). Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress caches, early-warning label degradation, classifier control, class-weight sensitivity, external diagnostics, and evidence-freeze protocols across declared seeds. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.


# References {.unnumbered}

::: {#refs}
:::

