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
  - \usepackage{graphicx}
  - \usepackage{tabularx}
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{enumitem}
  - \usepackage{etoolbox}
  - \setlist[itemize]{leftmargin=1.4em,nosep}
  - \setlist[enumerate]{leftmargin=1.4em,nosep,itemsep=0.2ex}
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\begin{list}{}{\scriptsize\setlength{\itemindent}{0pt}\setlength{\leftmargin}{0pt}\setlength{\parsep}{0pt}\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}}{\end{list}}}
  - \AtBeginDocument{\renewcommand{\CSLBlock}[1]{#1\par}}
  - \AtBeginDocument{\setlength{\csllabelwidth}{1.8em}}
  - \AtBeginDocument{\renewcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth - \csllabelwidth\relax}{\scriptsize\ignorespaces#1}}}
  - \AtBeginDocument{\renewcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{\scriptsize\strut#1}}}
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

\title{When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry}

\author{%
\IEEEauthorblockN{Junyu Li and Juntao Du\IEEEauthorrefmark{1}}
\IEEEauthorblockA{School of Statistics and Applied Mathematics,
Anhui University of Finance and Economics, Bengbu 233030, China\\
\IEEEauthorrefmark{1}Corresponding author: \texttt{dujuntao@aufe.edu.cn}}
}

\maketitle

\begin{abstract}
Operating reserve screening near the demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3) is governed by acute asymmetric shortfall risk: generation over-forecasts incur severe balancing penalties relative to surplus energy headroom. Deterministic aerodynamic power curves presume fresh and fully observable telemetry; however, commercial Supervisory Control and Data Acquisition (SCADA) systems routinely encounter transmission latency, packet serialization dropouts, and aggregator-boundary pitch unobservability. Under degraded telemetry, the current operating regime of a turbine ceases to be directly observable and becomes a latent state. Across multi-seed benchmarks on the 134-turbine WTB commercial plant and multi-year evaluations over three European wind facilities, this paper investigates whether machine learning provides universal superiority or conditional utility under information degradation. 

Under pristine telemetry, deterministic physical rules achieve the lowest reserve-screening surrogate cost among all evaluated approaches ($589{,}535\text{ kW}\cdot\text{h}$ at 10-minute dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with $\sim 6.8\%$ violation), outperforming deep neural networks. Under a 60-minute latency contingency, unadapted physical rules undergo catastrophic reliability breakdown, surging violation rates to $24.0\% \pm 1.7\%$ at $h=1$ and leaving $127.6\text{ MWh}$ of unhedged shortfall. Crucially, when telemetry channels remain observable, simple state-conditional recalibration absorbs $55.3\%$ of this shortage loss ($127.6 \to 57.0\text{ MWh}$) without neural representation learning. Learned representations acquire demonstrable utility only when blade-pitch registers are withheld: by inferring latent operating states from secondary electromechanical and spatio-temporal consequences (active/reactive responses and wake context), learned representations reduce reserve screening cost by $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across latencies and double transition-window recall ($0.416$ vs. $0.196$). Dynamic Mixture-of-Experts routing confers no statistical advantage over unrouted dense baselines ($p=0.380$), while decoupled modular architectures match tail reliability ($9.7\%$ violation). Furthermore, heuristic selective decision abstention fails to outperform random rejection, being Pareto-dominated by uniform reserve margin expansion. These findings establish that machine learning is valuable not as a universal replacement for aerodynamic rules, but as a conditional latent-state inference mechanism when critical physical states become unobservable.
\end{abstract}

\begin{IEEEkeywords}
Wind turbine operating reserve; SCADA telemetry degradation; partial observability; latent operating boundary; transmission latency; aerodynamic power curve; reliability breakdown; reserve-risk screening; state-conditional recalibration; MPPT-to-pitch transition.
\end{IEEEkeywords}



# Introduction

In bulk power system operations, real-time generation shortfalls incur severe asymmetric shortage penalties relative to surplus energy headroom; consequently, conventional symmetric error metrics like root-mean-square error (RMSE) mask catastrophic tail shortfall events that govern operating reserve adequacy in Level-1 pre-dispatch screening [@dowell2015veryshortterm; @kruse2023physics; @pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. This operational vulnerability is acutely concentrated near the aerodynamic demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3). Near rated inflow velocity, under the idealized rated-power regulation approximation, local aerodynamic power sensitivity transitions abruptly from a steep cubic trajectory ($\partial P / \partial v \propto v^2$) toward zero as pitch actuators rotate the blades to shed aerodynamic lift [@slootweg2003general; @gaertner2020definition]. When turbine operating states shift across this threshold unannounced, deterministic power curves over-extrapolate generation into Region 3, precipitating severe unhedged reserve deficits.

This operational vulnerability is severely exacerbated by telemetry degradation in commercial Supervisory Control and Data Acquisition (SCADA) systems. Industrial SCADA architectures experience gateway serialization overhead, packet queuing backlogs, and intermittent cellular transmission jitter [@tautzweinert2017scada; @ullah2022enabling]. In operational commercial archives (such as the Kelmarsh wind plant), 99.6\% of discrete turbine status transitions occur strictly between standard 10-minute polling boundaries. Furthermore, in third-party aggregator, Virtual Power Plant (VPP), and Transmission System Operator (TSO) triage, primary blade-pitch angle registers are frequently restricted or unobservable across commercial protocol firewalls. When delayed or missing sensor measurements are fed into deterministic physical power equations, dispatch systems clear reserve margins against obsolete operating points. Under such conditions, the fundamental operational uncertainty is not merely: *"What will the future inflow velocity be?"* It is first and foremost: *"Has the turbine already crossed the aerodynamic operating boundary into a different control regime?"* Under degraded telemetry, the turbine operating regime becomes a partially observed latent state.

Existing literature treats physics-based aerodynamic curves and deep neural networks as competing, mutually exclusive paradigms, pursuing either pure data-driven forecasting or physics-informed regularization [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. This framing overlooks their distinct operational boundaries under information freshness constraints. Under pristine SCADA telemetry, deterministic aerodynamic quantile curves calibrated to turbine specifications achieve the lowest reserve-screening surrogate cost among all evaluated methods ($589{,}535\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with compliant $\sim 6.8\%$ violation). However, deterministic rules undergo catastrophic reliability breakdown when subjected to telemetry staleness: under a 60-minute synthetic latency contingency stress test [@pierre2019design; @ravikumar2020anomaly], clean-calibrated physical violation rates surge to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, breaching the nominal 10\% Newsvendor target ($q^* = 0.90$) and leaving $127.6\text{ MWh}$ of unhedged shortfall exposure. 

To resolve this operational failure, we fundamentally reconstruct the role of machine learning around one central scientific question:
*When direct aerodynamic state measurements become stale or unavailable, can consequential spatio-temporal SCADA signals recover a soft operating-boundary posterior that remains dependable for asymmetric reserve-shortfall screening?*

Across 5-seed benchmarks on the 134-turbine WTB commercial plant and multi-year cross-farm evaluations across three European wind plants (ENGIE La Haute Borne, Kelmarsh, Penmanshiel), this paper establishes an empirical operational boundary framework delivering three verifiable insights:

1. **Identification of the Physical Reliability Boundary (RQ1)**: We expose the failure mechanism of deterministic aerodynamic rules under transmission staleness, demonstrating that cubic sensitivity cliff transitions amplify delayed-inflow errors and surge violation rates to $24.0\%$. We bound the operational horizon where deterministic physical rules remain dependable.
2. **Disentangling Recalibration from Latent Representation Recovery (RQ2)**: We show that under full channel observability, simple state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) at lower computational cost than neural networks. Learned representations acquire demonstrable superiority only when blade-pitch registers are withheld, reconstructing hidden operating regimes from electromechanical transients and spatial wake context, reducing reserve screening cost by $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ across latencies and doubling transition recall ($0.416$ vs. $0.196$).
3. **Decision Relevance of the Boundary Posterior and Falsification of MoE Routing (RQ3)**: We verify that reserve-screening gains stem from embedding latent boundary awareness into shared spatio-temporal representations and residual quantile estimation, rather than from dynamic Mixture-of-Experts (MoE) routing. STGQ-Routed achieves statistical parity with unrouted dense baselines (cost ratio $1.045$, $p=0.380$), while decoupled modular architectures match tail reliability ($9.7\%$ violation). Furthermore, we document an informative negative result: heuristic selective decision abstention fails to outperform random rejection, being Pareto-dominated by uniform reserve expansion.



# Related Work

## From Average Wind-Power Accuracy to Transition-Window Risk

Spatio-temporal graph neural networks (STGNNs) have advanced multi-step wind plant forecasting by modeling spatial cross-correlations and dynamic wake advection across turbine arrays [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn]. Physics-informed extensions integrate engineering wake models and aerodynamic boundary penalties to constrain continuous forecast trajectories [@park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. While these architectures reduce plant-wide $L_2$ error, continuous trajectory minimization obscures discrete turbine operating state transitions between MPPT (Region 2) and blade-pitch regulation (Region 3) that govern spinning reserve adequacy [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind]. 

Dynamic mixture-of-experts (MoE) routing has been proposed to partition complex feature spaces into localized functional sub-models [@shazeer2017outrageously; @fedus2022switch], but unconstrained gating lacks physical interpretability and fails to address the latent nature of turbine operating states under telemetry staleness. In power system operations, probabilistic forecasts monetize uncertainty through reserve procurement [@dowell2015veryshortterm; @kruse2023physics; @bremnes2004quantile]. This paper addresses an upstream operational bottleneck: screening aerodynamic transition risks under degraded SCADA telemetry prior to market clearing. The resulting reserve evaluation functions strictly as a Level-1 pre-dispatch screening log for balancing-risk triage, abstracting away downstream transmission network power-flow constraints and multi-stage market cashflows.



# Problem Formulation and Latent Operating-Boundary Framework

## Level-1 Pre-Dispatch Risk Screening and Asymmetric Newsvendor Loss (PSREI)

Operating reserve screening functions as a pre-dispatch risk assessment mechanism to mitigate costly real-time generation imbalances [@bremnes2004quantile; @nielsen2006quantile]. 

\textbf{Two-level hierarchical grid dispatch interface:} To define the operational boundaries of this work, we formalize a two-level grid dispatch hierarchy: \emph{Level 1} (Local Pre-Dispatch Risk Filtering \& Screening Layer, Paper Scope), operating at the wind plant Energy Management System (EMS) or aggregator terminal to ingest SCADA telemetry, forecast spatio-temporal power, diagnose operational regime boundaries under telemetry degradation, and size pre-dispatch reserve allocations mitigating unhedged balancing exposure; and \emph{Level 2} (Grid-Level Physical Clearing \& Network-Constrained Dispatch, Downstream Interface), managed by the TSO to execute network-constrained economic dispatch (NCED), unit commitment, and full AC-OPF subject to bus voltage security, transmission thermal limits, and bulk reserve margins. Our formulation is strictly bounded to Level 1 pre-dispatch risk screening proxies, abstracting away transmission network power-flow constraints and wholesale market cashflow settlements.

\textbf{Penalized Reserve-Shortfall Energy Index (PSREI):} For scheduled point forecast $\hat{y}_{i,t}$ and realized generation $y_{i,t}$, over-forecast shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. Sizing upward reserve margin $r_b$ incurs a reserve procurement energy equivalent $r_b \Delta t$ and an asymmetric shortage penalty $\rho \max(s_{i,t} - r_b, 0) \Delta t$. For penalty ratio $\rho$, the total operational proxy metric is formalized as the \textbf{Penalized Reserve-Shortfall Energy Index (PSREI)} in $\text{kW}\cdot\text{h}$ (evaluated at representative proxy ratio $\rho = 10$, alongside sensitivity evaluations across $\rho \in \{5, 10, 20\}$):
\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b(i,t) + \rho \max\left(\hat{y}_{i,t} - y_{i,t} - r_b(i,t), \, 0\right) \right]\Delta t.
\label{eq:psrei}
\end{equation}
PSREI is a decision-oriented risk surrogate targeting pre-dispatch shortage mitigation rather than financial market settlement. Differentiating $\mathbb{E}[C(r_b; \rho)]$ with respect to reserve margin $r_b$ yields the first-order optimality condition $\partial \mathbb{E}[C]/\partial r_b = 1 - \rho \Pr[s_{i,t} > r_b] = 0$, giving the classical Newsvendor critical fractile $q^*(\rho) = 1 - 1/\rho$ [@dowell2015veryshortterm]. For our representative proxy ratio $\rho=10$, $q^*(10) = 0.90$, establishing a nominal 10\% violation target.

\textbf{Loss geometry and pinball quantile head:} Conventional point forecasting optimizes symmetric quadratic loss $\mathcal{L}_{L_2}(y, \hat{y}) = (y - \hat{y})^2$, whose Bayes-optimal predictor converges to conditional expectation $\mathbb{E}[y \mid \mathbf{x}]$. In bounded wind power regimes with non-Gaussian transition densities, the conditional mean systematically departs from upper conditional quantiles, while balancing operations ($\rho = 10$) penalize generation shortfalls ten times more heavily than surplus headroom. Upward reserve margin $\hat{r}_{i,t}$ required to cover shortfall residual $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$ is estimated via asymmetric pinball loss:
\begin{equation}
\mathcal{L}_q(s, \hat{r}) = (s - \hat{r})\left(q - \mathbf{1}[s < \hat{r}]\right) = \begin{cases} q (s - \hat{r}), & s \ge \hat{r}, \\ (1-q)(\hat{r} - s), & s < \hat{r}. \end{cases}
\label{eq:pinball}
\end{equation}
Setting $q = q^* = 0.90$ aligns training with the Newsvendor condition: Bayes-optimal prediction converges to conditional shortfall quantile $\hat{r}^* = Q_{0.90}(s \mid \mathbf{x})$, targeting a nominal 10\% exceedance probability [@dowell2015veryshortterm; @kruse2023physics].

\textbf{PCC portfolio smoothing \& multi-horizon dispatch:} Power delivered to the bulk grid is metered at the Point of Common Coupling (PCC) bus: $P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}$ and $R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}$. Aggregating decentralized turbine power flows at the PCC bus unlocks spatial portfolio diversification: localized high-frequency aerodynamic turbulence cancels out across the array, leaving boundary regime shifts as the primary source of unhedged reserve risk. We evaluate two distinct operational horizons: (1) \textbf{Immediate dispatch} ($h=1$, 10-min ahead), representing real-time economic dispatch (RTED) dominated by autocorrelation; and (2) \textbf{Operational dispatch} ($h=6$, 1-hour ahead), representing intra-day clearing and storage scheduling where spatial wake dynamics and weather transitions are paramount.


## Latent Operating Regimes: MPPT, Pitch Regulation, and Demarcation Boundaries

Let $G=(V,E)$ denote a turbine array spatial graph with $N$ nodes. For each turbine $i \in V$ at discrete time step $t$, the system observes a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predicts active power $y_{i,t} \in \mathbb{R}$. Given observation history $H$ and forward horizon $P$, the forecast mapping is:
\begin{equation}
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
\label{eq:forecast-mapping}
\end{equation}
where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes a time-varying directed graph sequence (WTB) or static graph repeated over time (ERA5). We enforce a strict causal boundary: all input features, graph adjacency structures, and supervisory anchors depend solely on telemetry available at or before dispatch anchor $t$, with target trajectories commencing strictly at $t+1$. In WTB, instantaneous active power $\texttt{Patv}_{i,t}$ serves solely as an anchor-time operational status indicator, preventing look-ahead leakage.

At any dispatch time $t$, turbine $i$ operates in a discrete aerodynamic control regime governed by local inflow wind speed $w_{i,t} = \texttt{Wspd}_{i,t}$ and collective blade pitch angle $\bar{p}_{i,t} = \frac{1}{3}\sum_{k=1}^3 p^{(k)}_{i,t}$:
\begin{equation}
Z_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-regulated)},\\
3, & \text{otherwise} \quad \text{(transitional/ambiguous)}.
\end{cases}
\label{eq:regimes}
\end{equation}
Thresholds are calibrated to turbine specifications: WTB (134 turbines: $u_{\mathrm{idle}}=3.0\text{ m/s}$, $u_{\mathrm{rated}}=10.5\text{ m/s}$, $p_{\mathrm{th}}=2.0^\circ$), Kelmarsh (6 MM92 turbines: $3.0\text{ m/s}, 12.5\text{ m/s}, 1.0^\circ$), Penmanshiel (15 MM82 turbines: $3.0\text{ m/s}, 14.5\text{ m/s}, 1.0^\circ$), and ENGIE La Haute Borne (4 MM82 turbines: $3.0\text{ m/s}, 14.5\text{ m/s}, 1.0^\circ$). Only well-defined regimes ($Z_{i,t} \in \{0,1,2\}$) provide direct supervisory alignment; transitional samples are masked via $M_{i,t} = \mathbf{1}[Z_{i,t} \neq 3]$.

Under pristine and complete telemetry, $\bar{p}_{i,t}$ and $w_{i,t}$ are known, so $Z_{i,t}$ is directly observable. However, when transmission latency $\tau > 0$ delays the SCADA stream or when blade-pitch registers are restricted across aggregator interfaces, $Z_{i,t}$ ceases to be directly observable and becomes a \textbf{partially observed latent state}. The central inferential object of the operational system is the soft operating-boundary posterior:
\begin{equation}
p(Z_{i,t} \mid \mathbf{X}_{\le t}),
\label{eq:posterior-dist}
\end{equation}
which must be inferred from historical and spatial consequence channels.


## Aerodynamic Power Conversion and the Stale-State Control Cliff

In variable-speed wind turbine aerodynamics, mechanical power captured from inflow air is governed by $P_{\mathrm{mech}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), \beta(t)) v^3(t)$, where $\rho_{\mathrm{air}} \approx 1.225\text{ kg/m}^3$, $R$ is rotor radius, $v(t)$ is wind speed, $\beta(t)$ is blade pitch angle, and $\lambda(t) = \omega_r(t) R / v(t)$ is tip-speed ratio. Standard aeroelastic turbine models approximate $C_p(\lambda, \beta)$ via non-linear empirical polynomials [@slootweg2003general; @gaertner2020definition] (formalized in Supplementary Appendix~A). 

Turbine dynamics are partitioned by rated wind speed $u_{\mathrm{rated}}$: in Region 2 (MPPT, $u_{\mathrm{idle}} \le v \le u_{\mathrm{rated}}$), blades maintain optimal fine pitch $\beta \approx 0^\circ$ yielding cubic power growth $P(v) \propto v^3$; in Region 3 (Pitch regulation, $u_{\mathrm{rated}} < v \le u_{\mathrm{cut-out}}$), the pitch controller rotates blades to shed lift, clamping electrical output at nameplate capacity $P_{\mathrm{rated}}$. In idealized aerodynamic representations, this transition exhibits a localized slope discontinuity [@slootweg2003general]:
\begin{equation}
\left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^-} = \frac{3}{2} \rho_{\mathrm{air}} \pi R^2 C_{p,\max} u_{\mathrm{rated}}^2 \gg 0, \quad \left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^+} \approx 0.
\label{eq:sensitivity-cliff}
\end{equation}

When SCADA telemetry experiences latency $\tau > 0$, deterministic aerodynamic curves evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. If the turbine crosses from Region 2 into Region 3 during the latency interval ($Z_{t-\tau} = 1$ while $Z_t = 2$), the delayed pitch register remains at fine pitch $\beta_{t-\tau} \approx 0^\circ$. Consequently, the deterministic aerodynamic rule evaluates an obsolete operating point, extrapolating power along the steep cubic slope:
\begin{equation}
\hat{P}_{\mathrm{phys}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), 0^\circ) v^3(t) \gg P_{\mathrm{rated}}.
\label{eq:stale-phys}
\end{equation}
Because the actual turbine output is clamped at $P_{\mathrm{rated}}$, this stale evaluation produces a severe over-forecast error $\hat{P}_{\mathrm{phys}}(t) - P_{\mathrm{rated}} \gg 0$. In pre-dispatch reserve screening with asymmetric penalty ratio $\rho=10$, this unhedged over-forecast produces catastrophic shortage penalties, driving empirical violation rates to $24.0\% \pm 1.7\%$ under Delay-6. This establishes the deterministic physical power-curve baseline and exposes its structural failure mode under stale telemetry.


## The Non-Neural Baseline: State-Conditional Quantile Recalibration

Before introducing neural representation learning, it is necessary to establish the non-neural limit of adaptation. To evaluate whether distribution drift induced by latency can be absorbed by lightweight non-neural statistical correction, we formalize state-conditional quantile recalibration.

Given delayed telemetry $\mathbf{s}_{i,t-\tau} = (w_{i,t-\tau}, \bar{p}_{i,t-\tau})$, we partition the state space into $K$ operational bins $\{\mathcal{B}_k\}_{k=1}^K$ defined by cut-in, rated wind speed, and pitch thresholds ($Z_{i,t-\tau} = k$). To eliminate data leakage, empirical quantile reserve margins $\hat{r}(k)$ are calibrated strictly on held-out validation residuals $\mathcal{D}_k^{\mathrm{val}}$:
\begin{equation}
\hat{r}(k) = \inf \left\{ r \in \mathbb{R} : \frac{1}{|\mathcal{D}_k^{\mathrm{val}}|} \sum_{(i,t) \in \mathcal{D}_k^{\mathrm{val}}} \mathbf{1}\left[ \hat{y}^{\mathrm{phys}}_{i,t} - y_{i,t} \le r \right] \ge q^* \right\},
\label{eq:recalib}
\end{equation}
where $\mathcal{D}_k^{\mathrm{val}} = \{(i,t) \in \mathcal{D}_{\mathrm{val}} : \mathbf{s}_{i,t-\tau} \in \mathcal{B}_k\}$ and $q^* = 1 - 1/\rho = 0.90$. 

We formalize two distinct calibration protocols: (1) \textit{Clean-Frozen Calibration}, where reserve margins $\hat{r}^{\mathrm{clean}}(k)$ are calibrated exclusively on nominal clean validation data ($\tau = 0$) and strictly frozen prior to deployment, quantifying unadapted vulnerability under latency ($\tau > 0$); and (2) \textit{Condition-Matched Validation Calibration}, where for a known delay $\tau$, reserve margins $\hat{r}(k; \tau)$ are re-estimated on held-out validation residuals undergoing the identical delay $\tau$, establishing a non-neural benchmark that absorbs distribution drift under full channel observability. Observing delayed telemetry in bin $\mathcal{B}_k$ yields reserve allocation $\hat{r}_{i,t} = \hat{r}(k)$. 

Crucially, state-conditional recalibration is strictly an \textbf{information-preserving correction}: it recalibrates the residual mapping conditional on observed state bins, but it cannot synthesize missing physical state information when critical channels are withheld. When primary blade-pitch telemetry $\bar{p}_{i,t}$ is withheld, the physical state cannot be binned accurately, causing recalibration to deteriorate.


## Latent State Recovery from Spatio-Temporal Consequence Channels

\textbf{Physical dynamic wake graph:} When primary SCADA telemetry degrades or pitch registers are withheld, spatial coupling across turbine arrays provides physical redundancy to infer local operating regimes [@wu2019graphwavenet; @li2018dcrnn]. For WTB, we construct a time-varying directed wake graph $\mathcal{A}_t$: candidate turbine pairs $(i, j)$ are filtered by physical distance ($d_{ij} \le d_{\max}$), activated when upstream turbine $j$ lies within an aerodynamic wake cone aligned with instantaneous local wind direction $\theta_t$ (half-angle $\alpha = 25^\circ$), weighted by streamwise decay $\exp(-d_{\parallel}/\sigma_x)$ and cross-stream decay $\exp(-d_{\perp}^2/2\sigma_y^2)$, and pruned to the $K$ strongest inbound wake neighbors [@park2019physicsinduced; @zehtabiyan2023physicsguided]. This defines an instantaneous aerodynamic wake score $s^{\mathrm{wake}}_{i,t}$, providing spatial context even during anemometer corruption.

\textbf{Directed-diffusion GRU encoder:} With 110k parameters and an average single-window execution time of $3.8\text{ ms}$ in desktop benchmarking, the encoder features a compact parameter footprint suitable for local substation computing envelopes. Two directed diffusion blocks aggregate self, inbound, and outbound messages across each graph snapshot:
\begin{equation}
\begin{aligned}
\mathbf{X}^{(\ell+1)}_{t} = \mathrm{LN}\Big(&\mathbf{W}_{\mathrm{self}}^{(\ell)}\mathbf{X}^{(\ell)}_{t} +\mathbf{W}_{\mathrm{in}}^{(\ell)}\mathrm{Agg}_{\mathrm{in}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) \\
&+\mathbf{W}_{\mathrm{out}}^{(\ell)}\mathrm{Agg}_{\mathrm{out}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) +\mathbf{R}^{(\ell)}\mathbf{X}^{(\ell)}_{t}\Big),
\end{aligned}
\label{eq:diffusion}
\end{equation}
where $\mathrm{Agg}_{\mathrm{in}}$ and $\mathrm{Agg}_{\mathrm{out}}$ denote normalized weighted aggregations over inbound and outbound wake neighbors. A GRU then extracts node-level representations $\mathbf{h}_{i,t}$.

\textbf{Cross-sensor electromechanical consequence mechanism:} When blade-pitch telemetry $\bar{p}_{i,t}$ suffers packet loss, transmission latency, or protocol unobservability across aggregator boundaries, the dynamic graph encoder leverages secondary consequence channels to infer the latent operating regime $p(Z_{i,t} \mid \mathbf{X}_{\le t})$:
1. \emph{Active power transients} ($\texttt{Patv}_{i,t}$): Divergence between active power output and inflow velocity reflects aerodynamic torque shedding;
2. \emph{Electrical and reactive responses}: Variations in terminal voltage and reactive power dynamics signal transition-region control action;
3. \emph{Spatial wake context}: Dynamic wake advection across upstream and downstream turbines provides spatial corroboration of boundary crossing.

In nominal operation, the boundary head ingests $\mathbf{a}_{i,t}^{\mathrm{WTB}} = [\texttt{Wspd}_{i,t}, \texttt{Pab\_mean}_{i,t}, s^{\mathrm{wake}}_{i,t}, \texttt{Patv}_{i,t}]$. Under pitch-withheld conditions, $\texttt{Pab\_mean}_{i,t}$ is strictly excluded, and the representation learns to reconstruct $Z_{i,t}$ from secondary consequences alone.


## Boundary Posterior and Residual Quantile Consequence Model

The framework maintains an explicit mathematical separation among three distinct inferential objects:
1. \textbf{Posterior operating-regime inference}:
   $\pi_{i,t}^{\mathrm{pitch}} = p(Z_{i,t} = 2 \mid \mathbf{X}_{\le t})$, inferring the probability of active blade-pitch regulation;
2. \textbf{Point power trajectory forecasting}:
   $\hat{\mathbf{y}}_{i,t+1:t+P} = \mathbb{E}[\mathbf{y}_{i,t+1:t+P} \mid \mathbf{X}_{\le t}]$, providing the scheduled dispatch profile;
3. \textbf{Reserve-tail quantile estimation}:
   $\hat{r}_{i,t} = Q_{q^*}(s_{i,t} \mid \mathbf{X}_{\le t})$, sizing upward reserve to cover asymmetric shortfall exposure $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$ at $q^* = 0.90$.

In the decoupled modular architecture (STGQ-Modular), upward reserve is directly estimated by pairing frozen spatio-temporal representations $\mathbf{h}_{i,t}$ with physical anchors in a dedicated residual quantile head:
\begin{equation}
\hat{r}_{i,t} = \mathrm{MLP}_{\mathrm{res}}([\mathbf{h}_{i,t}; \mathbf{x}_{\mathrm{anchor}}]),
\label{eq:modular-res-head}
\end{equation}
optimized via pinball loss ($q^*=0.90$). Alternatively, in posterior-binned policies, the soft posterior $\pi_{i,t}^{\mathrm{pitch}}$ defines quantile binning thresholds over validation residuals to allocate empirical reserve margins.


## Architectural Comparators and Prior-Alignment Optimization

To interrogate the structural mechanism responsible for reserve-screening gains, we benchmark three architectural configurations under matched parameter capacity:
1. \textbf{STGQ-Modular}: A decoupled architecture pairing frozen spatio-temporal backbone representations $\mathbf{h}_{i,t}$ with a dedicated residual quantile head estimating reserve margins $\hat{r}_{i,t}$ via pinball loss ($q^*=0.90$);
2. \textbf{STGQ-Dense}: An unrouted baseline coupling spatial graph embeddings $\mathbf{h}_{i,t}$ to a shared linear projection for point forecasts $\hat{\mathbf{y}}_{i,t+1:t+P}$ and a joint dense quantile head;
3. \textbf{STGQ-Routed}: An architectural comparator evaluating dynamic Mixture-of-Experts (MoE) routing, where gating logits $\mathbf{z}_{i,t} = \mathrm{MLP}_{\mathrm{gate}}([\mathbf{h}_{i,t}; \mathbf{a}_{i,t}])$ compute soft routing weights $\mathbf{g}_{i,t} = \mathrm{softmax}(\mathbf{z}_{i,t}/\tau_{\mathrm{gate}})$ to combine specialized expert outputs $\hat{\mathbf{y}}_{i,t+1:t+P} = \sum_{e=1}^E g_{i,t}^{(e)} f_e(\mathbf{h}_{i,t})$.

The models are trained with a multi-task objective combining multi-step trajectory prediction loss $\mathcal{L}_{\mathrm{pred}}$ with auxiliary physical regularizers:
\begin{equation}
\mathcal{L} = \mathcal{L}_{\mathrm{pred}} + \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}} + \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}} + \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}} + \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}} + \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}},
\label{eq:multi-task-loss}
\end{equation}
where $\mathcal{L}_{\mathrm{align}}$ anchors routing/classification logits to declared regimes $Z_{i,t}$ on unmasked samples ($M_{i,t}=1$) using train-only inverse-frequency weights; $\mathcal{L}_{\mathrm{force}}$ sharpens discrimination between MPPT and pitch regulation; $\mathcal{L}_{\mathrm{bal}}$ is an expert-balancing regularizer used exclusively for the routed comparator to prevent expert collapse; and $\mathcal{L}_{\mathrm{aux}}$ with $\mathcal{L}_{\mathrm{smooth}}$ enforce spatial wake consistency.

\textbf{Explicit Methodological Notice:} We emphasize that $\mathcal{L}_{\mathrm{align}}$ acts strictly as an \textbf{operating-regime prior} embedded into the shared representation space; $\mathcal{L}_{\mathrm{bal}}$ serves solely as a routing regularizer. \textbf{The neural backpropagation pipeline contains no quantile loss, pinball penalty, or Newsvendor decision loss.} Model checkpoint selection is strictly governed by validation RMSE, preventing auxiliary penalties from distorting prediction accuracy. All quantile reserve margins are calibrated on held-out validation residuals or estimated by the decoupled residual quantile head. Therefore, the learned posterior is a \emph{jointly represented boundary posterior} rather than an end-to-end posterior calibrated directly under dispatch decision loss.



# Case Study Configuration and Operational Constraints

## Datasets and Preprocessing

Empirical evaluation spans two contrasting observability settings: the 134-turbine WTB commercial wind plant benchmark and the ERA5 thermodynamic contrast patch. WTB (KDD Cup 2022) comprises 134 wind turbines and 245 days of continuous 10-minute SCADA telemetry ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], where turbulent inflow, wake propagation, and turbine pitch regulation interact nonlinearly, rendering the MPPT-to-pitch transition indirectly observable. Missing inputs are forward-filled per turbine and mean-imputed; non-positive power values are masked out of supervision. ERA5 covers three archived months on a $16 \times 16$ spatial grid ($T=2208$, $N=256$, eight features) [@hersbach2020era5], where surface sensible heat flux directly marks convective regimes. Both datasets adopt an observation history of $H=36$ and a prediction horizon of $P=24$ under chronological train/validation/test splits (180/30/35 days for WTB; 1325/441/442 frames for ERA5). In addition, multi-year SCADA records from three European commercial wind plants (ENGIE La Haute Borne, Kelmarsh, Penmanshiel) provide diverse turbine architectures for cross-farm evaluation.


## Controlled Telemetry Degradation Protocols and Realism Mapping

To stress-test reserve screening resilience under adverse communication conditions, we evaluate controlled counterfactual telemetry degradation protocols alongside sensor perturbation controls across all five seeds (201--205): (1) \textbf{Tier 1 (Nominal SCADA Polling, $0\text{--}10\text{ min}$, Clean):} fresh telemetry on the 10-min SCADA grid (IEC 61400-25); (2) \textbf{Tier 2 (Plausible Degraded Telemetry, $10\text{--}30\text{ min}$, Delay-1 to Delay-3):} communication latencies induced by substation ring-buffer backlogs and lossy cellular retransmissions [@ullah2022enabling]; and (3) \textbf{Tier 3 (Contingency Stress-Test Upper Envelope, $60\text{ min}$, Delay-6):} a 6-step ($60\text{ min}$) synthetic transmission lag evaluated strictly as an upper contingency stress envelope (simulating gateway failures or cyber-physical storms) [@pierre2019design; @ravikumar2020anomaly] to establish the asymptotic breakdown boundary of unadapted physical rules. Sensor perturbation controls comprise additive Gaussian noise ($\sigma_v = 1.0\text{ m/s}, \sigma_\beta = 2.0^\circ$) and a two-state Markov-Gilbert burst dropout chain ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$) simulating transient wireless dropouts [@ullah2022enabling; @ravikumar2020anomaly].

Fig.~1 illustrates the causal decision failure mechanism and the three-tier operational recovery hierarchy across telemetry degradation regimes.

\begin{figure}[t]
\centering
\includegraphics[width=0.88\columnwidth,keepaspectratio]{figures/figure1_decision_boundaries.pdf}
\caption{Causal decision failure and information recovery hierarchy under SCADA telemetry degradation. Panel A: Physical mechanism and staleness breakdown at rated cut-off, showing how telemetry staleness turns the operating regime $Z_t$ into a latent variable, precipitating cubic extrapolation errors and severe reserve shortfalls (24.0\% violation, 127.6 MWh deficit). Panel B: Three-tier information-centric recovery hierarchy, routing fresh telemetry to Tier 1 deterministic physical rules, observable delay to Tier 2 state-conditional recalibration, and pitch-withheld/contingency telemetry to Tier 3 learned latent representations (STGQ-Modular). Panel C: Empirical mechanism falsification and negative results, showing that dynamic MoE routing yields no advantage over unrouted dense/modular architectures ($p=0.380$) and heuristic selective abstention fails to beat random rejection.}
\label{fig:decision-boundaries}
\end{figure}


## Pre-Dispatch Risk Screening Framework and Resampling Hierarchy

All neural architectures share an identical training protocol using AdamW with early stopping on validation RMSE, gradient clipping, and mixed-precision execution on a single GPU across five strict-mask random seeds (201--205). Strong baselines (Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, TiDE) repeat across seeds 201--205 (30 completed runs under identical evaluation caches). To eliminate data leakage, the experimental pipeline strictly enforces a sequential three-split dataflow: $\mathcal{D}_{\mathrm{train}} \xrightarrow{\text{train } \theta} \mathcal{D}_{\mathrm{val}} \xrightarrow{\text{calibrate } \hat{r}(k)} \text{Freeze } \{\theta, \hat{r}\} \xrightarrow{\text{causal replay}} \mathcal{D}_{\mathrm{test}}$. Quantile offsets $\hat{r}(k)$ are estimated strictly on held-out validation residuals $\mathcal{D}_{\mathrm{val}}$ and frozen prior to test replay.

We establish a dual-level resampling hierarchy: (1) \textit{Model Initialization Robustness}, reporting mean $\pm$ standard deviation across five random seeds (201--205); and (2) \textit{Operational Time-Series Uncertainty}, evaluating operational risk metrics via a day-block bootstrap over the 35 test days (1,000 resamples of 144-step daily blocks, preserving diurnal cycles and serial autocorrelation) to construct empirical 95\% confidence intervals and paired difference distributions. Evaluation spans: point accuracy (MAE/RMSE, switch-window RMSE within $\pm 1.0\text{ m/s}$ of rated wind speed); physical regime alignment (NMI, ARI, gate entropy); and operational reserve consequence (PSREI reserve-shortfall surrogate cost, empirical violation rate, unhedged shortage MWh).



# Empirical Findings and Hypothesis Testing

## Result 1: Pristine Telemetry Favors Deterministic Physical Rules (RQ1)

Table~\ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) across 134 turbines over the 35-day test split under nominal clean telemetry. Table~\ref{tab:h6-paired} reports seed-paired screening metric differences $\Delta\text{Screening Metric} = \text{Screening}_{\text{Baseline}} - \text{Screening}_{\text{STGQ-Routed}}$, along with 95\% bootstrap confidence intervals.

\begin{table*}[!t]
\centering
\fontsize{6.5pt}{7.5pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{0.85}
\caption{Cross-Seed Multi-Regime Pre-Dispatch Reserve Screening Benchmark under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data.}
\label{tab:h6-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & \shortstack{Penalized Reserve-Shortfall\\Energy (kW$\cdot$h, Proxy at $\rho=10$)} & Violation Rate & Reserve (kW) & Shortage (kW$\cdot$h) & Pinball Loss \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{881{,}367 \pm 95{,}741}$ & $6.81\% \pm 1.13\%$ & $653{,}738 \pm 72{,}557$ & $22{,}763 \pm 4{,}013$ & $31.41 \pm 2.66$ \\
 & Frozen-Embedding Direct Quantile MLP$^{\ddagger}$ & $1{,}649{,}721 \pm 285{,}682$ & $0.58\% \pm 0.26\%$ & $1{,}630{,}572 \pm 293{,}346$ & $1{,}915 \pm 958$ & $64.62 \pm 12.05$ \\
 & Global Quantile & $998{,}988 \pm 107{,}360$ & $6.46\% \pm 1.31\%$ & $771{,}304 \pm 95{,}661$ & $22{,}768 \pm 4{,}854$ & $36.50 \pm 3.41$ \\
 & STGQ-Dense & $991{,}181 \pm 110{,}211$ & $6.54\% \pm 1.04\%$ & $761{,}480 \pm 94{,}244$ & $22{,}970 \pm 4{,}121$ & $36.16 \pm 3.58$ \\
 & STGQ-Routed & $959{,}027 \pm 103{,}290$ & $7.10\% \pm 1.17\%$ & $707{,}249 \pm 91{,}305$ & $25{,}178 \pm 4{,}816$ & $34.77 \pm 3.16$ \\
 & Missingness-Aware GBDT & $1{,}238{,}603 \pm 112{,}051$ & $4.50\% \pm 0.73\%$ & $1{,}085{,}168 \pm 118{,}015$ & $15{,}343 \pm 2870$ & $46.85 \pm 3.48$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $1{,}136{,}466 \pm 84{,}101$ & $12.20\% \pm 1.25\%^{\dagger}$ & $662{,}335 \pm 73{,}483$ & $47{,}413 \pm 3{,}091$ & $38.85 \pm 2.06$ \\
 & Frozen-Embedding Direct Quantile MLP$^{\ddagger}$ & $1{,}682{,}251 \pm 284{,}323$ & $1.20\% \pm 0.52\%$ & $1{,}651{,}979 \pm 297{,}715$ & $3{,}027 \pm 1{,}594$ & $62.15 \pm 11.70$ \\
 & Global Quantile & $1{,}180{,}603 \pm 91{,}754$ & $10.85\% \pm 1.55\%^{\dagger}$ & $780{,}916 \pm 96{,}853$ & $39{,}969 \pm 6{,}087$ & $40.73 \pm 2.43$ \\
 & STGQ-Dense & $1{,}179{,}859 \pm 95{,}268$ & $11.04\% \pm 1.22\%^{\dagger}$ & $773{,}103 \pm 94{,}462$ & $40{,}676 \pm 4{,}788$ & $40.70 \pm 2.66$ \\
 & STGQ-Routed & $1{,}163{,}593 \pm 91{,}299$ & $11.82\% \pm 1.64\%^{\dagger}$ & $720{,}015 \pm 92{,}196$ & $44{,}358 \pm 7{,}341$ & $40.01 \pm 2.54$ \\
 & Missingness-Aware GBDT & $1{,}320{,}003 \pm 93{,}135$ & $8.36\% \pm 0.97\%$ & $1{,}030{,}858 \pm 114{,}266$ & $28{,}915 \pm 4{,}469$ & $46.68 \pm 2.45$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $\mathbf{998{,}273 \pm 106{,}253}$ & $7.59\% \pm 0.95\%$ & $746{,}697 \pm 82{,}474$ & $25{,}158 \pm 3{,}968$ & $33.97 \pm 2.78$ \\
 & Frozen-Embedding Direct Quantile MLP$^{\ddagger}$ & $1{,}639{,}909 \pm 242{,}922$ & $0.80\% \pm 0.28\%$ & $1{,}618{,}439 \pm 249{,}374$ & $2{,}147 \pm 953$ & $60.62 \pm 9.85$ \\
 & Global Quantile & $1{,}053{,}552 \pm 114{,}150$ & $7.48\% \pm 1.48\%$ & $802{,}361 \pm 99{,}513$ & $25{,}119 \pm 5{,}822$ & $36.26 \pm 3.24$ \\
 & STGQ-Dense & $1{,}048{,}083 \pm 115{,}181$ & $7.63\% \pm 1.13\%$ & $792{,}472 \pm 92{,}391$ & $25{,}561 \pm 4{,}643$ & $36.04 \pm 3.28$ \\
 & STGQ-Routed & $1{,}027{,}077 \pm 114{,}317$ & $7.62\% \pm 1.09\%$ & $769{,}864 \pm 106{,}672$ & $25{,}721 \pm 3{,}963$ & $35.16 \pm 3.19$ \\
 & Missingness-Aware GBDT & $1{,}314{,}640 \pm 129{,}158$ & $4.66\% \pm 0.80\%$ & $1{,}160{,}329 \pm 137{,}650$ & $15{,}431 \pm 3{,}099$ & $47.11 \pm 3.87$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{907{,}871 \pm 96{,}820}$ & $7.20\% \pm 1.15\%$ & $663{,}875 \pm 73{,}821$ & $24{,}400 \pm 4{,}106$ & $31.59 \pm 2.61$ \\
 & Frozen-Embedding Direct Quantile MLP$^{\ddagger}$ & $1{,}680{,}339 \pm 289{,}602$ & $0.57\% \pm 0.25\%$ & $1{,}660{,}135 \pm 298{,}104$ & $2{,}020 \pm 992$ & $64.38 \pm 12.00$ \\
 & Global Quantile & $1{,}030{,}131 \pm 108{,}592$ & $6.87\% \pm 1.39\%$ & $785{,}305 \pm 97{,}397$ & $24{,}483 \pm 5{,}104$ & $36.78 \pm 3.35$ \\
 & STGQ-Dense & $1{,}020{,}078 \pm 112{,}195$ & $6.90\% \pm 1.07\%$ & $775{,}899 \pm 96{,}235$ & $24{,}418 \pm 4{,}246$ & $36.35 \pm 3.57$ \\
 & STGQ-Routed & $990{,}625 \pm 104{,}487$ & $7.51\% \pm 1.22\%$ & $720{,}858 \pm 92{,}754$ & $26{,}977 \pm 5{,}183$ & $35.10 \pm 3.10$ \\
 & Missingness-Aware GBDT & $1{,}261{,}941 \pm 112{,}754$ & $4.88\% \pm 0.75\%$ & $1{,}094{,}730 \pm 120{,}612$ & $16{,}721 \pm 3{,}298$ & $46.62 \pm 3.40$ \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\tiny $^{\dagger}$Exceeds nominal 10\% violation target ($q^* = 0.90$). Bold numbers denote lowest surrogate screening metric. \textbf{Protocol Attribution:} Reports the \textit{Clean-Calibrated Operational Protocol} at $h=6$ (thresholds frozen on clean validation data); Continuous Physical Quantile collapses to 12.20\% violation under Delay-6. For the \textit{State-Conditional Validation-Calibrated Protocol} at immediate horizon ($h=1$), see Section~\ref{sec:physical-breakdown}, where clean-calibrated physical rules collapse to 24.0\% violation under Delay-6 while state-conditional calibration mitigates violations to 10.7\% (physical) and 10.6\% (joint model). Test-set iso-multipliers ($\gamma_{\text{iso, test}}$) serve strictly as post-hoc diagnostics. $^{\ddagger}$Frozen-Embedding Direct Quantile MLP evaluates naive uncalibrated pinball regression on frozen representations, exhibiting severe tail conservatism (>1.63M kW reserve, <1.2\% violation). In contrast, the calibrated residual architecture (STGQ-Modular, Section~\ref{sec:modular-baseline}, Table~\ref{tab:phase-scan}) and calibrated modular baselines (Cascaded Frozen MLP $15.528\text{M} \pm 1.599\text{M}$ vs STGQ-Routed 16.065M with no statistically detectable difference) resolve this pathology.}
\end{tabular*}
\end{table*}

\begin{table}[!htbp]
\centering
\fontsize{5.2pt}{6.0pt}\selectfont
\setlength{\tabcolsep}{0.6pt}
\renewcommand{\arraystretch}{0.75}
\caption{Seed-Paired Difference in Penalized Reserve-Shortfall Energy against STGQ-Routed ($h=6$, $\Delta\text{Screening Metric} = \text{Screening}_{\text{Baseline}} - \text{Screening}_{\text{STGQ-Routed}}$, positive indicates STGQ-Routed reduces surrogate reserve screening penalty at $\rho=10$).}
\label{tab:h6-paired}
\begin{tabularx}{\columnwidth}{@{}llcc>{\raggedright\arraybackslash}X@{}}
\toprule
Regime & Baseline Model & \shortstack{$\Delta\text{Screening}$\\$\text{Metric (kW}\cdot\text{h)}$} & 95\% Bootstrap CI & Sig. \& Operational Verdict \\
\midrule
\textbf{Clean} & Global Quantile & +39,962 & [+12,556, +67,367] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Cont. Physical\\Quantile} & $-$77,659 & [$-$106,175, $-$49,143] & Physical rule lower metric (95\% CI excludes zero) \\
 & Missingness GBDT & +279,576 & [+249,539, +309,613] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Frozen-Embedding\\Direct Quantile MLP} & +690,695 & [+448,769, +932,621] & Tail-conservative Direct MLP \\
 & STGQ-Dense & +32,154 & [$-$1,148, +65,456] & Inconclusive difference (95\% CI includes zero) \\
\midrule
\textbf{Delay-6} & Global Quantile & +17,010 & [+3,486, +30,535] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Cont. Physical\\Quantile} & $-$27,126 & [$-$46,907, $-$7,346] & Target exceeded ($12.20\%$ viol.) \\
 & Missingness GBDT & +156,411 & [+140,004, +172,817] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Frozen-Embedding\\Direct Quantile MLP} & +518,658 & [+307,212, +730,104] & Tail-conservative Direct MLP \\
 & STGQ-Dense & +16,267 & [+7,131, +25,402] & Supported reduction (95\% CI excludes zero) \\
\midrule
\textbf{Noise} & Global Quantile & +26,475 & [+9,121, +43,828] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Cont. Physical\\Quantile} & $-$28,804 & [$-$47,555, $-$10,053] & Physical rule lower metric (95\% CI excludes zero) \\
 & Missingness GBDT & +287,563 & [+248,847, +326,279] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Frozen-Embedding\\Direct Quantile MLP} & +612,832 & [+413,733, +811,931] & Tail-conservative Direct MLP \\
 & STGQ-Dense & +21,006 & [+2,419, +39,594] & Supported reduction (95\% CI excludes zero) \\
\midrule
\textbf{Markov} & Global Quantile & +39,506 & [+15,961, +63,052] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Cont. Physical\\Quantile} & $-$82,754 & [$-$111,026, $-$54,482] & Physical rule lower metric (95\% CI excludes zero) \\
 & Missingness GBDT & +271,316 & [+245,044, +297,588] & Supported reduction (95\% CI excludes zero) \\
 & \shortstack[l]{Frozen-Embedding\\Direct Quantile MLP} & +689,714 & [+448,689, +930,739] & Tail-conservative Direct MLP \\
 & STGQ-Dense & +29,453 & [$-$2,874, +61,779] & Inconclusive difference (95\% CI includes zero) \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\tiny Note: Statistical verdicts are based on empirical 95\% confidence intervals computed via day-block cluster bootstrap over the 35 test days (1,000 resamples of complete diurnal blocks). Supported reduction denotes 95\% CI strictly excluding zero; Inconclusive difference denotes 95\% CI including zero (indicating insufficient evidence of an operational difference resulting from shared representation learning).
\end{table}

The empirical evidence directly challenges the presumption that deep neural architectures universally outperform physical models. Under pristine telemetry ($\tau = 0$), Continuous Physical Quantile achieves the lowest surrogate reserve screening cost among all evaluated methods ($589{,}535 \pm 77{,}390\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with compliant $\sim 6.8\%$ violation). It substantially outperforms both unrouted dense networks (STGQ-Dense: $991{,}181\text{ kW}\cdot\text{h}$) and dynamically routed architectures (STGQ-Routed: $959{,}027\text{ kW}\cdot\text{h}$). As confirmed in Table~\ref{tab:h6-paired}, the seed-paired difference between Continuous Physical Quantile and STGQ-Routed is $-77{,}659\text{ kW}\cdot\text{h}$, with a 95\% block bootstrap confidence interval strictly excluding zero ($[-106{,}175, -49{,}143]$). 

This finding establishes that when inflow wind speed and blade pitch angle are fresh and directly observable, deterministic aerodynamic equations provide optimal reserve screening. Neural networks, lacking hard physical saturation bounds, introduce unnecessary variance under nominal telemetry.


## Result 2: Telemetry Staleness Triggers Boundary Breakdown (RQ1) \label{sec:physical-breakdown}

While deterministic physical rules excel under fresh data, Table~\ref{tab:h6-benchmark} exposes their \textbf{catastrophic reliability breakdown} under telemetry staleness. Under a 60-minute latency contingency stress test (Delay-6), deterministic physical curves evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. Near rated wind speed, the localized slope discontinuity (\ref{eq:sensitivity-cliff}) amplifies delayed-inflow errors: turbines that have crossed into active blade-pitch regulation ($Z_t = 2$) are evaluated with obsolete fine pitch ($\beta_{t-\tau} \approx 0^\circ$), over-extrapolating power output along the steep cubic trajectory (\ref{eq:stale-phys}).

Consequently, unadapted physical quantile violation rates surge from $6.81\%$ to $24.02\% \pm 1.69\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, breaching the nominal 10\% Newsvendor target ($q^* = 0.90$). This breakdown leaves $127.55\text{ MWh}$ of unhedged generation shortfall across the array. This delineates the exact operational reliability boundary of deterministic aerodynamic rules: when transmission latency delays state observation, physical rules cease to provide dependable reserve screening.


## Result 3: Full Observability Drift Is Resolved by Recalibration (RQ2)

When telemetry channels remain observable under transmission delays, condition-matched state-conditional recalibration (\ref{eq:recalib}) adjusts quantile margins using held-out validation residuals undergoing the identical delay. As shown in Table~\ref{tab:phase-scan}, state-conditional recalibration absorbs $55.3\%$ of the shortage loss ($127.55 \to 57.01\text{ MWh}$), restoring fleet violation to $9.46\%$ and achieving a surrogate reserve cost of $1{,}228{,}609\text{ kW}\cdot\text{h}$ at $h=1$. In fact, recalibrated physical curves outperform all neural models under full observability (STGQ-Routed: $1{,}274{,}047\text{ kW}\cdot\text{h}$; STGQ-Modular: $1{,}283{,}855\text{ kW}\cdot\text{h}$).

To establish the operational limits of recalibration under communication drift, we evaluate a mismatched calibration matrix across test latencies $\tau_{\mathrm{test}} \in [0, 60]\text{ min}$ and calibration horizons $\tau_{\mathrm{cal}} \in [0, 60]\text{ min}$ (Supplementary Table~A11l). Recalibrating at $\tau_{\mathrm{cal}} = 10\text{ min}$ withstands latency drift up to $\tau_{\mathrm{test}} = 20\text{ min}$ while maintaining compliant tail coverage ($8.2\%\text{--}9.1\%$ violation). However, recalibration breaks down when staleness surges to $\tau_{\mathrm{test}} = 60\text{ min}$ ($13.8\%$ violation). This demonstrates that under full channel observability, distribution drift alone does not justify deep representation learning: simple state-conditional recalibration captures the vast majority of recoverable value.


## Result 4: Pitch Unobservability Demands Latent State Representation (RQ2) \label{sec:withheld-channel}

The indispensable role of machine learning emerges when blade-pitch telemetry is withheld across aggregator boundaries (\texttt{no\_pitch}, Table~\ref{tab:phase-scan}). Under pitch unobservability, physical rules and recalibration schemes lose direct state awareness, inflating recalibrated screening penalties from $824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$ to $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60\text{ min}$. 

\begin{table}[!htbp]
\centering
\fontsize{4.8pt}{5.5pt}\selectfont
\setlength{\tabcolsep}{0.4pt}
\renewcommand{\arraystretch}{0.75}
\caption{Multidimensional operational progression across telemetry latency $\tau \in [0, 60]\text{ min}$ and pitch observability ($h=1$, 5-seed mean on WTB; nominal $\tau=0$ baseline $593{,}258\text{ kW}\cdot\text{h}$ aligns within $0.6\%$ of the primary frozen $589{,}535\text{ kW}\cdot\text{h}$ benchmark). Penalized reserve energy in kW$\cdot$h ($\rho=10$).}
\label{tab:phase-scan}
\begin{tabularx}{\columnwidth}{@{}ccccccc@{}}
\toprule
$\tau$ (min) & Pitch & \shortstack{Clean Phys.\\Metric (Viol.)} & \shortstack{Recal. Phys.\\Metric (Viol.)} & \shortstack{STGQ-Mod.\\Metric (Viol.)} & \shortstack{STGQ-Rout.\\Metric (Viol.)} & \shortstack{Operational\\Regime} \\
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
60 & All & $1{,}656{,}285$ ($24.0\%^{\dagger}$) & $\mathbf{1{,}228{,}609}$ ($9.5\%$) & $1{,}283{,}855$ ($9.6\%$) & $1{,}274{,}047$ ($9.6\%$) & Regime III (Tail Risk) \\
60 & None & $1{,}437{,}280$ ($11.8\%^{\dagger}$) & $1{,}378{,}900$ ($9.0\%$) & $\mathbf{1{,}330{,}318}$ ($8.7\%$) & $1{,}331{,}840$ ($8.8\%$) & Regime II (Repr. Adv.) \\
\bottomrule
\multicolumn{7}{@{}p{\columnwidth}@{}}{\tiny $^{\dagger}$Exceeds nominal 10\% violation target ($q^*=0.90$). Bold indicates lowest compliant surrogate screening metric. Under $\tau=60\text{ min}$, by-seed compliance is $3/5$ seeds ($60\%$) across models.}
\end{tabularx}
\end{table}

In contrast, learned representations (STGQ-Modular) reconstruct operating states from secondary electromechanical and spatio-temporal consequences:
1. \emph{Active power divergence}: Rotor aerodynamic torque shedding is inferred from the relationship between active power $\texttt{Patv}$ and inflow velocity;
2. \emph{Electrical transients}: Reactive power fluctuations and voltage dynamics signal pitch control actions;
3. \emph{Wake context}: Upstream operating states propagate downstream through dynamic wake advection.

As detailed in Table~\ref{tab:phase-scan}, STGQ-Modular achieves $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ saving of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintains consistent reserve screening reductions of $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across all latencies. Furthermore, learned representations double transition-window recall ($0.416$ vs. $0.196$ for degraded physics). This confirms that representation learning provides essential utility when primary aerodynamic state variables are withheld.


## Result 5: Operating-Regime Classification Accuracy Does Not Equal Decision Value (RQ3)

A critical question in operational machine learning is whether superior classification accuracy translates directly into superior reserve screening performance. To interrogate this hypothesis, we benchmark an independent sequence classifier (Graph WaveNet coupled to a live-anchor classifier) against joint representation models using empirical records from completed control benchmarks (\texttt{modular\_classifier\_reserve\_summary.csv}).

Under nominal telemetry, the independent classifier achieves perfect transition recall ($1.000$) and high precision ($0.879$), surpassing the joint boundary router ($0.960$ recall, $0.758$ precision). However, when evaluated on pre-dispatch reserve screening, the independent classifier incurs a surrogate reserve cost of $86{,}536{,}321\text{ kW}\cdot\text{h}$ ($9.54\%$ violation). It significantly trails both the joint boundary-forced router ($84{,}577{,}217\text{ kW}\cdot\text{h}$, $9.00\%$ violation) and the physical-bin baseline ($84{,}314{,}353\text{ kW}\cdot\text{h}$, $9.31\%$ violation) by over $2.22\text{M kW}\cdot\text{h}$ ($p < 0.01$).

This operational penalty occurs because discrete classification errors in independent models are decoupled from forecast residual magnitudes. Independent classifiers frequently misclassify regimes during steep wind-speed ramps where forecast residuals are largest, incurring disproportionately severe Newsvendor penalties. In contrast, joint representation models couple latent state awareness directly with spatio-temporal feature embeddings, ensuring that regime uncertainty is reflected in residual quantile sizing. This proves that classification accuracy is not equivalent to reserve screening value.


## Result 6: Mechanism Falsification: Dynamic MoE Routing Confers No Statistical Advantage (RQ3) \label{sec:modular-baseline}

Benchmarking capacity-matched neural architectures directly tests whether dynamic Mixture-of-Experts routing provides operational benefits over unrouted dense representations. Across all evaluated conditions, the hypothesis that dynamic expert routing is the source of reserve screening improvements is \textbf{falsified}:

1. \textbf{Clean Telemetry}: At $h=1$, STGQ-Dense and STGQ-Routed achieve statistical parity ($690{,}614$ vs. $660{,}990\text{ kW}\cdot\text{h}$, ratio $1.045$; seed-paired difference $+29{,}624\text{ kW}\cdot\text{h}$, 95\% CI $[-53{,}774, +113{,}023]$, $p=0.380$). At $h=6$, the paired difference $+32{,}154\text{ kW}\cdot\text{h}$ likewise crosses zero ($[-1{,}148, +65{,}456]$, Table~\ref{tab:h6-paired}).
2. \textbf{Multi-Horizon Seed Analysis}: In multi-horizon dispatch reserve-screening records across seeds 201--205 (\texttt{dense\_pricing\_by\_seed.csv}), the 5-seed mean surrogate cost for soft-gate-binning is $16.065\text{M kW}\cdot\text{h}$ compared to $16.076\text{M kW}\cdot\text{h}$ for soft-dense-binning (a difference of $< 0.07\%$). In fact, dense classification achieves lower surrogate cost than gated MoE in three out of five seeds (Seeds 203, 204, and 205).
3. \textbf{Decoupled Modular Architecture}: STGQ-Modular (a decoupled architecture pairing frozen spatio-temporal representations with a dedicated residual quantile head) achieves $1{,}284{,}098 \pm 114{,}629\text{ kW}\cdot\text{h}$ and $9.7\% \pm 1.1\%$ violation under Delay-6 at $h=1$ (Table~\ref{tab:phase-scan}), matching or outperforming STGQ-Routed ($1{,}412{,}321\text{ kW}\cdot\text{h}$, $10.6\% \pm 1.1\%$).

\textbf{Point-Forecast Price of Operating-Regime Awareness:} In point forecasting, the boundary-aware model achieves an RMSE of $236.13 \pm 8.41$, compared with $224.34 \pm 2.23$ for iTransformer and $225.74 \pm 2.60$ for Graph WaveNet. This architecture is \textbf{deliberately non-RMSE-optimal}: it trades a $+2.5\%$ whole-sample error margin to embed operating-regime awareness and prevent catastrophic tail shortfalls. Unconstrained models trigger $78.3\text{--}82.5\text{ MWh}$ of unhedged exposure, whereas boundary-aware representations restrict exposure to $53.9\text{ MWh}$ (a $31\%\text{--}35\%$ reduction).

These findings confirm that the operational benefit stems from consequence-based latent state representation and calibrated residual quantile estimation, not from dynamic expert specialization.


## Result 7: Deployment Boundaries: Failed Generic Abstention and Cross-Farm Limits \label{sec:cross-farm}

\textbf{Failure of Heuristic Selective Abstention:} Benchmarking selective decision abstention against random rejection and uniform reserve margin expansion (Supplementary Table~A10f) reveals that heuristic uncertainty scores ($U = \Delta r + 50 H(\pi)$) fail under multi-step latency: selective refusal at confidence threshold $c=0.90$ yields a fleet violation rate of $9.44\%$, which is statistically indistinguishable from random rejection ($9.50\%$, $p > 0.40$). In contrast, uniform reserve margin expansion achieves an $8.29\%$ violation rate while saving $37{,}823\text{ kW}\cdot\text{h}$, strictly Pareto-dominating heuristic refusal. Stale telemetry degrades both point forecasts and uncertainty estimators, proving that generic predictive uncertainty cannot identify unsafe operating states under prolonged telemetry degradation.

\textbf{Cross-Farm Scalability and Local Retraining:} Table~\ref{tab:cross-farm} benchmarks pre-dispatch reserve screening performance across four commercial wind farms under local retraining. 

\begin{table}[!htbp]
\centering
\fontsize{5.0pt}{5.9pt}\selectfont
\setlength{\tabcolsep}{0.8pt}
\renewcommand{\arraystretch}{0.88}
\caption{Cross-Farm Pre-Dispatch Reserve Screening Performance across Four Commercial Wind Farms under Local Retraining (5 Seeds 201--205, $\rho=10$).}
\label{tab:cross-farm}
\begin{tabularx}{\columnwidth}{@{}l c ccc >{\centering\arraybackslash}p{2.3cm} >{\raggedright\arraybackslash}X@{}}
\toprule
\shortstack[l]{Farm} & \shortstack[c]{Turbines /\\Model} & \shortstack[c]{Phys. Recal.\\(kW$\cdot$h)} & \shortstack[c]{Global\\Quantile} & \shortstack[c]{STGQ Local\\Retrain} & \shortstack[c]{$\Delta\text{PSREI}$ vs. Global\\[95\% CI]} & \shortstack[l]{Operational\\Finding} \\
\midrule
\textbf{WTB} & \shortstack{134 /\\GW 1.5M} & 841,734 & 893,462 & 855,462 & $-$38k [$-$67k, $-$12k] & Supported reserve reduction ($p < 0.05$) \\
\textbf{LHB} & \shortstack{4 /\\MM82} & 185,100 & 188,400 & 231,400 & +43k [$-$28.7k, +141.2k] & Overfitting boundary (CI includes zero) \\
\textbf{Kelmarsh} & \shortstack{6 /\\MM92} & 1,025,000 & 1,065,000 & 1,025,000 & $-$40k [$-$204k, +172k] & Neutral (CI crosses zero; recal. suffices) \\
\textbf{Penmanshiel} & \shortstack{14 /\\MM82} & 2,029,000 & 4,167,000 & 2,029,000 & $-$2.14M [$-$3.25M, $-$1.36M] & Commercial benefit ($p < 0.05$; $2.14$M saved) \\
\bottomrule
\end{tabularx}
\end{table}

In utility-scale arrays (WTB, 134 turbines; Penmanshiel, 14 turbines), spatial wake modeling delivers substantial reserve screening improvements ($\Delta\text{PSREI} = -38\text{k}$ and $-2.14\text{M kW}\cdot\text{h}$, both $p < 0.05$). Conversely, on micro-farms (Kelmarsh, 6 turbines; LHB, 4 turbines), spatial wake redundancy is absent: Kelmarsh yields a neutral bootstrap difference ($-40\text{k kW}\cdot\text{h}$, 95\% CI crossing zero), while LHB exposes an \textbf{overfitting boundary} where graph convolutions overfit localized terrain features ($+43\text{k kW}\cdot\text{h}$ penalty, $[-28.7\text{k}, +141.2\text{k}]$). Furthermore, zero-shot cross-farm transfer exhibits pronounced directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$). Reliable industrial deployment strictly mandates site-specific local retraining.

\textbf{Point of Common Coupling (PCC) Portfolio Smoothing:} Aggregating decentralized turbine power flows at the PCC bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, $\sim 121$ active turbines) unlocks spatial portfolio diversification: high-frequency turbulence cancels across the array, leaving boundary transitions as the primary reserve risk. Diversification concentrates heavily in transitional regimes (10\%--90\% pitching), saving $-1.33\text{M kW}\cdot\text{h}$ (CI $[-1.68\text{M}, -1.07\text{M}]$) over continuous physical pitch. Longitudinal records across Kelmarsh (9 years) and Penmanshiel (8.6 years) confirm operational recalibration under climatological drift.



# Discussion: The Principle of Minimum Sufficient Model Complexity \label{sec:discussion}

The empirical findings presented in Section V dismantle the conventional dichotomy between pure physical modeling and unconstrained deep learning. By treating turbine operating regimes as partially observed latent states under degraded telemetry, this study establishes an operational principle of \textbf{Minimum Sufficient Model Complexity} governed by channel observability and telemetry freshness:

### A. What Information Does Physics Require?
Deterministic aerodynamic power curves rely on a foundational assumption: the immediate availability of inflow wind speed $v_t$ and blade-pitch angle $\beta_t$. Under pristine telemetry ($\tau = 0$, full observability), physical rules directly evaluate the aerodynamic operating point. Because physical curves enforce strict asymptotic power-conservation bounds ($\partial P / \partial v \propto v^2$ below rated speed and $P \equiv P_{\mathrm{rated}}$ above rated speed), they do not suffer from the out-of-distribution variance that plagues neural models. As evidenced in Table~\ref{tab:h6-benchmark} and Table~\ref{tab:phase-scan}, continuous physical quantiles consistently achieve the lowest surrogate reserve screening costs ($589.5\text{k}\text{--}881.4\text{k kW}\cdot\text{h}$, with compliant $\sim 6.8\%$ violation), outperforming complex graph architectures. When primary physical state variables are fresh and directly observable, deep representation learning is methodologically superfluous and operationally sub-optimal.

### B. When Does Recalibration Break Down?
When transmission latency delays telemetry by 10 to 30 minutes, deterministic physical rules evaluated on stale tuples $(v_{t-\tau}, \beta_{t-\tau})$ begin to misclassify the operating state. However, as long as blade-pitch registers remain observable, the underlying information required to resolve the operating regime is preserved in the delayed channel history. Under these conditions, state-conditional recalibration absorbs $55.3\%$ of the shortage loss ($127.6 \to 57.0\text{ MWh}$) and maintains compliant violation rates ($7.1\%\text{--}7.5\%$) without updating neural weights. 

Offline recalibration breaks down only when staleness reaches contingency horizons ($\tau = 60\text{ min}$, Table A11l, where violations reach $13.8\%$). In this extreme regime, the extrapolation error across the cubic sensitivity cliff exceeds the buffer capacity of static quantile adjustments, creating an operational necessity for dynamic state tracking.

### C. What Does the Learned Representation Actually Know?
The decisive empirical advantage of representation learning emerges when blade-pitch telemetry is withheld (\texttt{no\_pitch}). Under pitch unobservability, physical rules and recalibration schemes lose direct awareness of whether the rotor is actively shedding lift. 

The spatio-temporal encoder resolves this latent ambiguity by extracting consequential signatures from remaining SCADA channels:
1. \textbf{Electromechanical Transients}: Divergence between active power output and inflow velocity reflects aerodynamic torque shedding;
2. \textbf{Electrical and Reactive Responses}: Variations in generator torque and reactive dynamics signal transition-region control action;
3. \textbf{Spatial Wake Context}: Upstream turbine operating regimes propagate downstream via dynamic wake advection, providing redundant topological evidence of boundary crossing.

Counterfactual probe benchmarks across four commercial wind plants (WTB, LHB, Kelmarsh, Penmanshiel; Tables A9b–A9f) confirm that secondary consequence channels sustain substantial mutual information with the true physical regime ($0.302\text{--}0.674$ NMI), whereas permuted-label negative controls collapse to chance ($< 10^{-4}$).

### D. Decision Relevance of the Posterior and the MoE Diagnostic
A pivotal methodological insight of this work is that operating-regime classification accuracy is not synonymous with reserve-screening performance. An independent classifier operating on live anchors can achieve high transition recall ($1.000$) yet fail to deliver reserve savings ($86.54\text{M kW}\cdot\text{h}$ vs. $84.31\text{M kW}\cdot\text{h}$ for physical baselines) because its discrete prediction errors are decoupled from the magnitude of forecast residuals. 

Reserve screening improvements require embedding latent boundary awareness into shared spatio-temporal representations and residual quantile estimation. 

Crucially, dynamic Mixture-of-Experts routing provides no measurable operational benefit over unrouted dense baselines (Dense/Routed cost ratio $1.045$, $p = 0.380$; seed-by-seed cost difference $< 0.07\%$). The decoupled modular architecture (STGQ-Modular) achieves equivalent tail protection ($9.7\%$ violation in Delay-6) without routing overhead. Thus, the operational value originates from consequence-based latent state representation and calibrated residual estimation, not from dynamic expert specialization.

### E. Industrial Deployment Boundaries and Scalability
System operators must observe three firm deployment guardrails established by our empirical diagnostics:
1. \textbf{Array Scale Sensitivity}: On large utility-scale wind arrays (WTB, Penmanshiel), spatio-temporal wake modeling delivers substantial reserve savings ($-38\text{k}$ to $-2.14\text{M kW}\cdot\text{h}$, $p < 0.05$). On compact micro-farms (LHB, 4 turbines), spatial wake redundancy is absent, causing graph convolutions to overfit local terrain ($+43\text{k kW}\cdot\text{h}$ penalty).
2. \textbf{Local Retraining Mandate}: Zero-shot cross-farm transfer exhibits pronounced directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. reverse $0.34$), proving that models must be retrained or locally calibrated to site-specific turbine geometries.
3. \textbf{Abstention Realism}: Heuristic selective decision abstention fails to beat random rejection under multi-step latency. Operators facing severe telemetry outages should rely on uniform reserve margin expansion rather than heuristic refusal scores.



# Limitations

To provide industrial practitioners and system operators with a defensible, transparent boundary of applicability, we delineate four foundational limitations of this study:

*1) Synthetic Stress versus Industrial Telemetry Contingencies:*
Telemetry impairments in our primary benchmarks are modeled via controlled synthetic processes: 10--30\,min delays represent buffer backlogs, while 60-min latency and Gilbert-Elliott Markov dropouts are evaluated as severe contingency stress bounds rather than everyday steady-state telemetry. Furthermore, ground-truth operating regimes on WTB rely on anemometer wind speed and collective pitch pseudo-labels. While counterfactual withheld-channel tests prove that aerodynamic regime boundaries are recoverable from secondary consequence signatures across four commercial plants, field-deployed turbines may experience non-stationary instrumentation drift, sensor icing, or uncoordinated individual pitch control actions not captured in our supervisory SCADA feeds.

*2) Risk Metric Surrogacy and Unmodeled Grid Dynamics:*
Our evaluation operates strictly at Level-1 pre-dispatch operating reserve screening. The penalized reserve shortfall index (PSREI at $\rho=10$) serves as a localized newsvendor risk surrogate. This abstraction intentionally omits Level-2 bulk transmission power-flow physics (full AC-OPF constraints, line thermal congestion, voltage stability limits), dynamic unit commitment of thermal reserves, Locational Marginal Prices (LMPs), and two-settlement wholesale market cashflow balancing. Realized operational balancing savings will necessarily depend on specific system-wide balancing market structures and penalty tariffs.

*3) Horizon, Sample Size, and Aerodynamic Calibration Tolerances:*
Empirical benchmarks are bounded to a 35-day continuous test split across five neural random seeds (201--205). While capturing diurnal transitions and winter storm fronts, this window does not encompass full multi-annual climatological cycles or seasonal air-density shifts. Moreover, aerodynamic parameters exhibit OEM-specific calibration tolerances: rated wind speeds range from $12.5\text{ m/s}$ (Senvion MM92) to $14.5\text{ m/s}$ (Senvion MM82) and cut-in transitions differ across turbine controllers. Model thresholds calibrated for one OEM cannot be directly transferred without recalibrating cut-in and rated demarcation boundaries.

*4) Field Deployment Overhead and Cross-Farm Overfitting Boundaries:*
Real-time substation edge deployment requires balancing neural inference latency and online regime classification latency against supervisory RTU polling cycles for state-conditional recalibration. While the modular residual head requires minimal computational overhead, spatial graph convolutions overfit localized topography on small arrays (LHB, 4 turbines, $+43\text{k kW}\cdot\text{h}$ penalty). Zero-shot cross-farm transfer exhibits pronounced directional asymmetry (NMI $0.557$ pooled; Supplementary Tables~A8--A9d), establishing that reliable deployment strictly demands site-specific local retraining rather than uncalibrated cross-site transfer.



# Conclusion

This study has fundamentally repositioned machine learning in wind plant operating reserve screening from a presumed universal replacement for physical models to a targeted, conditional inference mechanism under telemetry degradation. Through rigorous 5-seed empirical evaluations across the 134-turbine WTB commercial plant and multi-year data from three European facilities, we establish three primary conclusions:

First, under fresh and fully observable SCADA telemetry, deterministic aerodynamic power curves minimize surrogate reserve screening penalties ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, $\sim 6.8\%$ violation), outperforming deep neural networks. Deterministic rules experience catastrophic reliability breakdown only when telemetry staleness forces them to extrapolate across the cubic-to-flat sensitivity cliff near rated wind speed, surging violations to $24.0\%$.

Second, when telemetry channels remain observable under transmission delays, simple state-conditional recalibration absorbs $55.3\%$ of shortage exposure ($127.6 \to 57.0\text{ MWh}$) without neural representation learning. Learned representations acquire demonstrable utility only when blade-pitch registers become unobservable: by inferring latent operating states from secondary electromechanical and spatio-temporal consequence channels, learned representations outperform recalibrated physical rules by $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across all latencies and double transition recall ($0.416$ vs. $0.196$).

Third, dynamic Mixture-of-Experts routing confers no statistically detectable advantage over unrouted dense or modular architectures ($p = 0.380$), while decoupled modular residual regression matches tail reliability ($9.7\%$ violation). Furthermore, heuristic selective decision abstention is Pareto-dominated by uniform reserve margin expansion under persistent latency.

Consequently, modern wind plant dispatch systems should not seek to deploy universal deep neural networks across all operational regimes. Instead, dispatchers should implement an observability-aware division of labor: deploying deterministic aerodynamic rules under clean telemetry, lightweight recalibration under observable drift, and reserving learned latent-state representations for regimes where critical physical states are unobservable.



# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.



# Code and Data Availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public (raw third-party data not redistributed). Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress caches, early-warning label degradation, classifier control, class-weight sensitivity, external diagnostics, and evidence-freeze protocols across declared seeds. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.



# References {.unnumbered}

::: {#refs}
:::
