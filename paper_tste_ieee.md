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
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\par\addvspace{0.8ex}\begin{list}{}{\fontsize{8.0pt}{9.2pt}\selectfont\setlength{\itemindent}{0pt}\setlength{\leftmargin}{1.5em}\setlength{\parsep}{0pt}\setlength{\itemsep}{0.2ex}\setlength{\parskip}{0pt}}}{\end{list}}}
  - \AtBeginDocument{\renewcommand{\CSLBlock}[1]{#1\par}}
  - \AtBeginDocument{\setlength{\csllabelwidth}{1.5em}}
  - \AtBeginDocument{\renewcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth - \csllabelwidth\relax}{\fontsize{8.0pt}{9.2pt}\selectfont\ignorespaces#1}}}
  - \AtBeginDocument{\renewcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{\fontsize{8.0pt}{9.2pt}\selectfont\strut#1}}}
  - \makeatletter
  - \def\section{\@startsection{section}{1}{\z@}{0.75ex plus 0.15ex minus 0.1ex}{0.25ex plus 0.08ex}{\normalfont\footnotesize\bfseries\centering\scshape}}
  - \def\subsection{\@startsection{subsection}{2}{\z@}{0.5ex plus 0.1ex minus 0.08ex}{0.18ex plus 0.06ex}{\normalfont\small\itshape}}
  - \def\subsubsection{\@startsection{subsubsection}{3}{\z@}{0.4ex plus 0.1ex minus 0.08ex}{0.12ex plus 0.05ex}{\normalfont\footnotesize\itshape}}
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
Operating reserve screening near the wind turbine MPPT-to-pitch boundary is governed by acute asymmetric shortfall penalties. While deterministic power curves presume pristine telemetry, commercial SCADA feeds routinely encounter communication latency and aggregator-boundary pitch unobservability. Across 134-turbine commercial benchmarks, this paper addresses a single governing question: \textit{what is the minimum sufficient model under changing SCADA observability regimes?} We resolve three operational regimes: (1) \textbf{Fresh telemetry}: In the boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events), deterministic aerodynamic rules achieve the lowest reserve-screening surrogate cost ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$), outperforming neural networks by $8.1\%$. (2) \textbf{Stale telemetry}: Under 10--30 minute delays, non-neural state-conditional recalibration absorbs $55.3\%$ of shortage losses ($127.6 \to 57.0\text{ MWh}$) without parameter updates. (3) \textbf{Pitch unobservable}: Observable consequence signals (active power $\text{AUROC} = 0.988$) preserve boundary information; learned representations (trained using historically available pitch information that is withheld at deployment) double transition recall ($0.416$ vs. $0.196$) and reduce screening surrogate costs by $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ over unadapted physics. However, state recoverability is not sufficient for downstream reserve-decision superiority: strong wind-speed-conditioned quantiles remain lower-cost plant-wide, and matched-budget evaluations confirm that lower transition violation frequency is offset by deeper residual shortfalls.
\end{abstract}

\begin{IEEEkeywords}
Wind power reserve, SCADA telemetry degradation, latent operating boundary, state-conditional recalibration, minimum sufficient model, consequence-based recovery.
\end{IEEEkeywords}



# Introduction

In bulk power system operations, real-time generation shortfalls incur severe asymmetric shortage penalties relative to surplus headroom; conventional symmetric metrics like root-mean-square error (RMSE) mask severe tail shortfall events that govern operating reserve adequacy in Level-1 pre-dispatch screening [@dowell2015veryshortterm; @kruse2023physics; @pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. This operational vulnerability concentrates near the aerodynamic demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3). Near rated inflow velocity, local power sensitivity transitions abruptly from a steep cubic trajectory ($\partial P / \partial v \propto v^2$) toward zero as pitch actuators shed aerodynamic lift [@slootweg2003general; @gaertner2020definition]. When operating states shift across this threshold unannounced, deterministic power curves over-extrapolate generation into Region 3, precipitating severe unhedged reserve deficits.

This vulnerability is exacerbated by telemetry degradation in commercial Supervisory Control and Data Acquisition (SCADA) systems, including gateway serialization overhead, packet queuing backlogs, and intermittent cellular transmission jitter [@tautzweinert2017scada; @ullah2022enabling]. In operational archives (such as Kelmarsh), 99.6\% of discrete turbine status transitions occur between standard 10-minute polling boundaries. Furthermore, in third-party aggregator and Virtual Power Plant (VPP) triage, blade-pitch registers are frequently restricted across commercial protocol firewalls. When delayed or missing measurements enter physical power equations, dispatch systems clear reserve margins against obsolete operating points. Under degraded telemetry, the turbine operating regime becomes a partially observed latent state: the control register itself is unobservable at deployment, while its electromechanical consequences remain partially observable in arrived SCADA feeds ($Z_t \to P_t, Q_t, \text{trajectory}$).

Existing literature frequently treats aerodynamic curves and deep neural networks as competing predictive paradigms [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided], overlooking their distinct operational boundaries under information freshness constraints. Rather than asking which model achieves marginal predictive gains, bulk power system operations require answering a foundational engineering question:
\begin{equation}
\boxed{
\begin{gathered}
\text{What is the minimum sufficient model} \\
\text{under changing telemetry observability?}
\end{gathered}
}
\label{eq:core-question}
\end{equation}

To resolve this question, we structure our investigation across three distinct information regimes, bounded by an operational non-equivalence principle:
\begin{itemize}
\item \textbf{Fresh and observable $\to$ Physics}: Under pristine SCADA telemetry, deterministic aerodynamic quantile curves achieve the lowest reserve-screening surrogate cost within the active boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell events) among all evaluated methods ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, with target-satisfying $\sim 6.8\%$ violation), saving $8.1\%$ ($-77{,}659\text{ kW}\cdot\text{h}$) over neural architectures.
\item \textbf{Stale but observable $\to$ Recalibration}: Operational delays of 10--30 minutes exhibit distribution drift where non-neural state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) without updating network weights. A 60-minute latency contingency serves strictly as an asymptotic reliability breakdown stress endpoint ($24.0\% \pm 1.7\%$ violation at $h=1$) rather than a claim of normal industrial prevalence.
\item \textbf{Critical state unobservable $\to$ Consequence recovery}: When blade pitch is withheld, observable electromechanical consequence signals ($Z_t \to P_t, Q_t, \text{trajectory}$) retain latent boundary information, allowing learned representations to double transition recall ($0.416$ vs. $0.196$) and reduce reserve screening penalties by $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ over unadapted physical curves.
\item \textbf{Boundary Conditions ($\text{Recoverability} \not\Rightarrow \text{Decision Superiority}$, $\text{Lower Violation Frequency} \not\Rightarrow \text{Lower Shortage Severity}$)}: Reconstructing the hidden boundary does not establish downstream reserve-decision superiority: strong wind-speed-conditioned quantiles remain lower-cost plant-wide ($+523{,}044\text{ kW}\cdot\text{h}$ posterior penalty). The raw violation-rate reduction ($7.24\%$ vs. $8.36\%$) is partly associated with greater reserve procurement ($+149{,}241\text{ kW}\cdot\text{h}$); under matched reserve budgets ($\Delta R \equiv 0$), posterior conditioning does not improve shortage-energy efficiency, as lower violation frequency is offset by deeper residual uncovered shortfalls.
\end{itemize}

The 134-turbine WTB site serves as the primary mechanism-identification environment (with five random seeds quantifying training stochasticity rather than independent physical replications), while multi-year evaluations on three external European facilities (ENGIE La Haute Borne, Kelmarsh, Penmanshiel) probe transferability and delineate site-dependent boundary conditions. Treating spatio-temporal graph and mixture-of-experts formulations as established diagnostic baselines, this investigation establishes three substantive contributions across SCADA observability regimes:

1. **Regime 1 — Aerodynamic Sufficiency and Reliability Breakdown**: We establish that deterministic physical rules are the minimum sufficient and lowest-cost model under fresh observable telemetry in the boundary band ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$). Operational latencies of 10--30 min expose the onset of cubic extrapolation errors, while a 60-min contingency lag demonstrates asymptotic reliability breakdown ($24.0\% \pm 1.7\%$ violation, $127.6\text{ MWh}$ deficit).
2. **Regime 2 — Sufficiency of Non-Neural Recalibration under Observable Drift**: We decouple telemetry staleness from genuine channel missingness, demonstrating that under full channel observability, non-neural state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) without parameter updates.
3. **Regime 3 — Consequence-Based State Recovery and Decision Boundary**: When blade pitch is withheld at deployment, observable electromechanical consequences retain information about the latent operating boundary ($Z_t \to P_t, Q_t, \text{trajectory}$, doubling transition recall from $0.196$ to $0.416$). Learned representations provide one recovery mechanism, but state recoverability is not sufficient for downstream reserve-decision superiority: strong wind-speed-conditioned quantiles remain lower-cost plant-wide, and matched-budget frontiers show that lower transition violation frequency is partly associated with greater reserve procurement while residual shortage severity increases.

Additional falsification and cross-site analyses test whether these findings depend on routing architecture, selective abstention, or uniform transfer assumptions across commercial facilities (where turbine count alone does not explain cross-site variation).



# Related Work

## From Average Wind-Power Accuracy to Transition-Window Risk

Spatio-temporal graph neural networks (STGNNs) advance multi-step wind plant forecasting by modeling spatial cross-correlations and wake advection [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn], with physics-informed extensions incorporating wake and boundary constraints [@park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. While these architectures reduce plant-wide $L_2$ error, continuous trajectory minimization obscures discrete turbine operating state transitions between MPPT (Region 2) and pitch regulation (Region 3) that govern spinning reserve adequacy [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind]. 

Recent physics-aware dynamic-graph mixture-of-experts (MoE) architectures, such as that of Zhao et al. [@zhao2026physicsaware], test whether coupling spatial learning, physical guidance, and expert routing improves point forecasting accuracy. Rather than iterating on forecasting network topologies, our formulation isolates the upstream information-and-decision problem: when critical aerodynamic states become unobservable due to telemetry degradation, what regime information remains recoverable from secondary consequence channels, when non-neural conditional recalibration suffices without parameter updates, and whether the recovered latent state alters asymmetric reserve-shortfall decisions. Probabilistic forecasts translate predictive uncertainty into reserve allocation [@dowell2015veryshortterm; @kruse2023physics; @bremnes2004quantile]. We address this operational triage problem: screening aerodynamic transition risks under degraded SCADA telemetry prior to market clearing, functioning strictly as a Level-1 pre-dispatch proxy while abstracting downstream transmission constraints.



# Problem Formulation and Latent Operating-Boundary Framework

## Level-1 Pre-Dispatch Risk Screening and Asymmetric Decision Problem (PSREI)

Operating reserve screening functions as a pre-dispatch risk assessment mechanism to mitigate costly real-time generation imbalances [@bremnes2004quantile; @nielsen2006quantile].

\textbf{Hierarchical grid dispatch interface:} Our formulation is strictly bounded to Level 1 pre-dispatch operating reserve screening proxies at the plant EMS or aggregator terminal, abstracting Level 2 bulk transmission AC-OPF and wholesale balancing settlements.

\textbf{Penalized Reserve-Shortfall Energy Index (PSREI):} For scheduled forecast $\hat{y}_{i,t}$ and realized generation $y_{i,t}$, shortfall is $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$. For upward reserve $r_b$ and penalty ratio $\rho$, the \textbf{Penalized Reserve-Shortfall Energy Index (PSREI)} in $\text{kW}\cdot\text{h}$ is:
\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b(i,t) + \rho \max\left(\hat{y}_{i,t} - y_{i,t} - r_b(i,t), \, 0\right) \right]\Delta t.
\label{eq:psrei}
\end{equation}
Differentiating $\mathbb{E}[C(r_b; \rho)]$ yields the first-order condition $\partial \mathbb{E}[C]/\partial r_b = 1 - \rho \Pr[s_{i,t} > r_b] = 0$, giving the Newsvendor critical fractile $q^*(\rho) = 1 - 1/\rho$ [@dowell2015veryshortterm]. For $\rho=10$, $q^* = 0.90$, establishing a nominal 10\% violation target.

\textbf{Loss geometry and pinball quantile head:} Point forecasting minimizes symmetric $L_2$ loss converging to conditional mean $\mathbb{E}[y \mid \mathbf{x}]$, which departs from upper quantiles in asymmetric operations ($\rho=10$). Upward reserve margin $\hat{r}_{i,t}$ covering shortfall $s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0)$ is estimated via pinball loss:
\begin{equation}
\mathcal{L}_q(s, \hat{r}) = (s - \hat{r})\left(q - \mathbf{1}[s < \hat{r}]\right) = \begin{cases} q (s - \hat{r}), & s \ge \hat{r}, \\ (1-q)(\hat{r} - s), & s < \hat{r}. \end{cases}
\label{eq:pinball}
\end{equation}
Setting $q = q^* = 0.90$ aligns training with the Newsvendor condition: Bayes-risk-minimizing prediction converges to conditional shortfall quantile $\hat{r}^* = Q_{0.90}(s \mid \mathbf{x})$ [@dowell2015veryshortterm; @kruse2023physics].

\textbf{PCC portfolio smoothing \& dispatch horizons:} Net power at the Point of Common Coupling (PCC) bus aggregates turbine outputs ($P_{\mathrm{farm}, t} = \sum_{i=1}^M P_{i,t}$, $R_{\mathrm{farm}, t} = \sum_{i=1}^M R_{i,t}$), where turbulence cancels across the array, leaving boundary transitions as dominant unhedged risk. We evaluate immediate dispatch ($h=1$, 10-min ahead) dominated by serial autocorrelation, and operational dispatch ($h=6$, 1-hour ahead) where spatial wake dynamics govern decisions.


## Latent Operating Regimes: MPPT, Pitch Regulation, and Demarcation Boundaries

Let $G=(V,E)$ denote a turbine array spatial graph with $N$ nodes. For each turbine $i \in V$ at time step $t$, the system observes feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predicts active power $y_{i,t} \in \mathbb{R}$. Given observation history $H$ and horizon $P$, the forecast mapping is:
\begin{equation}
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
\label{eq:forecast-mapping}
\end{equation}
where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes the graph adjacency sequence. We enforce strict causal boundaries: all input features, graph adjacency structures, and supervisory anchors depend solely on telemetry available at or before dispatch anchor $t$, with target trajectories commencing strictly at $t+1$. In WTB, instantaneous active power $\texttt{Patv}_{i,t}$ serves solely as an anchor-time operational status indicator, preventing look-ahead leakage.

At dispatch time $t$, turbine $i$ operates in a discrete aerodynamic control regime governed by inflow wind speed $w_{i,t} = \texttt{Wspd}_{i,t}$ and collective blade pitch angle $\bar{p}_{i,t} = \frac{1}{3}\sum_{k=1}^3 p^{(k)}_{i,t}$:
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
Thresholds follow turbine specifications: WTB (134 turbines: $u_{\mathrm{idle}}=3.0\text{ m/s}$, $u_{\mathrm{rated}}=10.5\text{ m/s}$, $p_{\mathrm{th}}=2.0^\circ$), Kelmarsh (6 MM92: $3.0\text{ m/s}, 12.5\text{ m/s}, 1.0^\circ$), Penmanshiel (14 operational MM82, numbered WT01--WT15 excluding WT03: $3.0\text{ m/s}, 14.5\text{ m/s}, 1.0^\circ$), and ENGIE La Haute Borne (4 MM82: $3.0\text{ m/s}, 14.5\text{ m/s}, 1.0^\circ$). Supervised alignment masks ambiguous transitions ($Z_{i,t}=3$) via $M_{i,t} = \mathbf{1}[Z_{i,t} \neq 3]$.

Under pristine telemetry, $\bar{p}_{i,t}$ and $w_{i,t}$ are known, so $Z_{i,t}$ is directly observable. Under transmission latency $\tau > 0$ or when blade-pitch registers are withheld across aggregator interfaces, the control register itself ceases to be accessible at deployment, while its dynamical electromechanical consequences ($Z_t \to P_t, Q_t, \text{trajectory}$) remain partially preserved in arrived SCADA feeds. Hence, $Z_{i,t}$ is a \textbf{control-state latent variable} rather than an unobservable physical process. The central inferential object is the soft operating-boundary posterior:
\begin{equation}
p(Z_{i,t} \mid \mathbf{X}_{\le t}),
\label{eq:posterior-dist}
\end{equation}
inferred from historical trajectory, active-power transients, and spatial wake consequence channels.


## Aerodynamic Power Conversion and the Stale-State Control Boundary

Mechanical power captured from inflow air is governed by $P_{\mathrm{mech}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), \beta(t)) v^3(t)$, where $\rho_{\mathrm{air}} \approx 1.225\text{ kg/m}^3$, $R$ is rotor radius, $v(t)$ is wind speed, $\beta(t)$ is pitch angle, and $\lambda(t) = \omega_r(t) R / v(t)$ is tip-speed ratio [@slootweg2003general; @gaertner2020definition]. In Region 2 (MPPT, $u_{\mathrm{idle}} \le v \le u_{\mathrm{rated}}$), blades maintain nominal fine pitch $\beta \approx 0^\circ$ yielding cubic power growth $P(v) \propto v^3$; in Region 3 (Pitch regulation, $u_{\mathrm{rated}} < v \le u_{\mathrm{cut-out}}$), the pitch controller rotates blades to shed lift, clamping electrical output at nameplate capacity $P_{\mathrm{rated}}$:
\begin{equation}
\left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^-} = \frac{3}{2} \rho_{\mathrm{air}} \pi R^2 C_{p,\max} u_{\mathrm{rated}}^2 \gg 0, \quad \left. \frac{\partial P}{\partial v} \right|_{v \to u_{\mathrm{rated}}^+} \approx 0.
\label{eq:sensitivity-cliff}
\end{equation}

When SCADA telemetry experiences latency $\tau > 0$, aerodynamic curves evaluate stale tuples $(v_{t-\tau}, \beta_{t-\tau})$. If the turbine enters Region 3 during the latency window ($Z_{t-\tau} = 1$ while $Z_t = 2$), the delayed pitch register remains at fine pitch $\beta_{t-\tau} \approx 0^\circ$. Consequently, the aerodynamic rule extrapolates power along the cubic trajectory:
\begin{equation}
\hat{P}_{\mathrm{phys}}(t) = \frac{1}{2} \rho_{\mathrm{air}} \pi R^2 C_p(\lambda(t), 0^\circ) v^3(t) \gg P_{\mathrm{rated}}.
\label{eq:stale-phys}
\end{equation}
Because output clamps at $P_{\mathrm{rated}}$, this stale evaluation produces severe over-forecast error $\hat{P}_{\mathrm{phys}}(t) - P_{\mathrm{rated}} \gg 0$, surging empirical violation rates to $24.0\% \pm 1.7\%$ under Delay-6 ($\rho=10$), which acts as an asymptotic reliability breakdown stress endpoint.


## The Non-Neural Baseline: State-Conditional Quantile Recalibration

To evaluate whether latency-induced drift can be absorbed by non-neural statistical correction, we formalize state-conditional quantile recalibration. Given delayed telemetry $\mathbf{s}_{i,t-\tau} = (w_{i,t-\tau}, \bar{p}_{i,t-\tau})$, we partition the state space into $K$ bins $\{\mathcal{B}_k\}_{k=1}^K$ defined by cut-in, rated wind speed, and pitch thresholds ($Z_{i,t-\tau} = k$). To eliminate data leakage, empirical quantile reserve margins $\hat{r}(k)$ are calibrated strictly on held-out validation residuals $\mathcal{D}_k^{\mathrm{val}}$:
\begin{equation}
\hat{r}(k) = \inf \left\{ r \in \mathbb{R} : \frac{1}{|\mathcal{D}_k^{\mathrm{val}}|} \sum_{(i,t) \in \mathcal{D}_k^{\mathrm{val}}} \mathbf{1}\left[ \hat{y}^{\mathrm{phys}}_{i,t} - y_{i,t} \le r \right] \ge q^* \right\},
\label{eq:recalib}
\end{equation}
where $\mathcal{D}_k^{\mathrm{val}} = \{(i,t) \in \mathcal{D}_{\mathrm{val}} : \mathbf{s}_{i,t-\tau} \in \mathcal{B}_k\}$ and $q^* = 1 - 1/\rho = 0.90$.

We evaluate two calibration protocols: (1) \textit{Clean-Frozen Calibration}, where margins $\hat{r}^{\mathrm{clean}}(k)$ are calibrated on clean validation data ($\tau = 0$) and strictly frozen; and (2) \textit{Condition-Matched Calibration}, where for a known delay $\tau$, margins $\hat{r}(k; \tau)$ are re-estimated on held-out validation residuals with matching delay $\tau$. Recalibration is an \textbf{information-preserving correction}: it updates residual margins conditional on observed bins, but cannot synthesize missing state information when blade pitch is withheld.


## Latent State Recovery from Spatio-Temporal Consequence Channels

\textbf{Physical dynamic wake graph \& encoder:} For WTB, time-varying directed wake graphs $\mathcal{A}_t$ link turbine pairs within aerodynamic wake cones ($\alpha = 25^\circ$) weighted by streamwise and cross-stream decay [@park2019physicsinduced; @zehtabiyan2023physicsguided]. A compact directed-diffusion GRU encoder (110k parameters, $3.8\text{ ms}$ single-window execution) aggregates messages via:
\begin{equation}
\begin{aligned}
\mathbf{X}^{(\ell+1)}_{t} = \mathrm{LN}\Big(&\mathbf{W}_{\mathrm{self}}^{(\ell)}\mathbf{X}^{(\ell)}_{t} +\mathbf{W}_{\mathrm{in}}^{(\ell)}\mathrm{Agg}_{\mathrm{in}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) \\
&+\mathbf{W}_{\mathrm{out}}^{(\ell)}\mathrm{Agg}_{\mathrm{out}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) +\mathbf{R}^{(\ell)}\mathbf{X}^{(\ell)}_{t}\Big),
\end{aligned}
\label{eq:diffusion}
\end{equation}
and extracts node-level representations $\mathbf{h}_{i,t}$. When blade pitch $\bar{p}_{i,t}$ is unobservable, the encoder infers latent regime $p(Z_{i,t} \mid \mathbf{X}_{\le t})$ from secondary consequence channels: active power transients ($\texttt{Patv}_{i,t}$), electrical responses, and dynamic wake advection, strictly excluding $\texttt{Pab\_mean}_{i,t}$.


## Reserve-Tail Estimation and Residual Quantile Sizing

To shield operations from balancing exposure, reserve margins target the asymmetric shortfall distribution rather than symmetric point forecasts, separating: (1) posterior operating-state inference $\pi_{i,t}^{\mathrm{pitch}} = p(Z_{i,t} = 2 \mid \mathbf{X}_{\le t})$; (2) scheduled point forecasting $\hat{\mathbf{y}}_{i,t+1:t+P}$; and (3) reserve-tail quantile sizing $\hat{r}_{i,t} = Q_{0.90}(s_{i,t} \mid \mathbf{X}_{\le t})$.

Directly estimating extreme quantiles on raw power trajectories via uncalibrated neural pinball regression introduces severe tail conservatism (>1.6M kW reserve, <1.2\% violation, Table~\ref{tab:h6-benchmark}). To resolve this pathology, estimation is decoupled: point trajectories $\hat{\mathbf{y}}$ anchor nominal expectations, while upward reserve margins $\hat{r}_{i,t}$ are estimated conditionally on forecast residuals:
\begin{equation}
\begin{aligned}
\hat{r}_{i,t} = \mathrm{MLP}_{\mathrm{res}}([\mathbf{h}_{i,t}; \, \mathbf{x}_{\mathrm{anchor}}]), \\
\text{minimized under } \mathcal{L}_{q^*}(s_{i,t}, \hat{r}_{i,t}),
\end{aligned}
\label{eq:residual-quantile}
\end{equation}
or binned empirically over held-out validation residuals conditioned on latent posterior $\pi_{i,t}^{\mathrm{pitch}}$.


## Architecture Variants as Mechanism Ablations

To test whether dynamic Mixture-of-Experts (MoE) routing provides operational value over unrouted representations, we formulate three matched-capacity variants:
1. \textbf{STGQ-Modular} (Decoupled Canonical): Pairs frozen spatio-temporal representations $\mathbf{h}_{i,t}$ with a dedicated residual quantile head;
2. \textbf{STGQ-Dense} (Unrouted Joint): Couples spatial embeddings $\mathbf{h}_{i,t}$ directly to a shared linear projection for point forecasts $\hat{\mathbf{y}}$ and a joint dense quantile head;
3. \textbf{STGQ-Routed} (Dynamic MoE): Evaluates dynamic MoE routing [@shazeer2017outrageously; @fedus2022switch] combining expert predictions $\hat{\mathbf{y}}_{i,t+1:t+P} = \sum_{e=1}^E g_{i,t}^{(e)} f_e(\mathbf{h}_{i,t})$.

Training minimizes:
\begin{equation}
\begin{aligned}
\mathcal{L} = \mathcal{L}_{\mathrm{pred}} &+ \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}} + \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}} \\
&+ \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}} + \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}} + \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}},
\end{aligned}
\label{eq:multi-task-loss}
\end{equation}
where $\mathcal{L}_{\mathrm{align}}$ anchors logits to declared regimes $Z_{i,t}$ on unmasked samples ($M_{i,t}=1$); $\mathcal{L}_{\mathrm{force}}$ sharpens boundary discrimination; $\mathcal{L}_{\mathrm{bal}}$ balances expert utilization; and $\mathcal{L}_{\mathrm{aux}}, \mathcal{L}_{\mathrm{smooth}}$ enforce spatial wake consistency.

\textbf{Operating-Regime Representation Prior:} The auxiliary loss $\mathcal{L}_{\mathrm{align}}$ acts as an operating-regime prior embedded into representation space. The neural backpropagation pipeline contains no quantile loss, pinball penalty, or Newsvendor decision loss. Checkpoint selection is strictly governed by validation RMSE. Quantile reserve margins are calibrated on held-out validation residuals or estimated by the decoupled residual head, yielding a jointly represented boundary posterior rather than an end-to-end decision posterior.



# Case Study Configuration and Operational Constraints

## Datasets and Preprocessing

Empirical evaluation spans the 134-turbine WTB benchmark and the ERA5 thermodynamic contrast patch. WTB (KDD Cup 2022) comprises 134 turbines over 245 days of 10-minute SCADA telemetry ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], with chronological 180/30/35-day train/val/test splits ($H=36, P=24$). ERA5 covers three archived months on a $16 \times 16$ grid ($T=2208$, $N=256$, 8 features) [@hersbach2020era5] under 1325/441/442 splits. Multi-year SCADA records from three European commercial wind plants (ENGIE La Haute Borne, Kelmarsh, Penmanshiel) provide diverse turbine architectures for cross-farm evaluation.


## Controlled Telemetry Degradation Protocols and Realism Mapping

To evaluate resilience under communication stress, we simulate three degradation tiers across five seeds (201--205): (1) \textbf{Tier 1 (Nominal Polling, $0\text{--}10\text{ min}$, Clean)}: fresh SCADA on 10-min grid (IEC 61400-25); (2) \textbf{Tier 2 (Plausible Degraded Telemetry, $10\text{--}30\text{ min}$, Delay-1 to 3)}: transmission lags from substation buffer backlogs [@ullah2022enabling], characterizing the operational transition regime; and (3) \textbf{Tier 3 (Contingency Stress Envelope, $60\text{ min}$, Delay-6)}: a 6-step synthetic lag evaluating asymptotic physical breakdown [@pierre2019design; @ravikumar2020anomaly] as a stress endpoint rather than an industrial prevalence claim. Perturbations include additive Gaussian noise ($\sigma_v = 1.0\text{ m/s}, \sigma_\beta = 2.0^\circ$) and a two-state Markov burst dropout chain ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$) [@ullah2022enabling].

Fig.~1 illustrates the causal decision failure mechanism and the three-tier operational recovery hierarchy across telemetry degradation regimes.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,keepaspectratio]{figures/figure1_decision_boundaries.pdf}
\caption{Conceptual architecture of the minimum sufficient modeling principle across three telemetry observability regimes. Incoming SCADA feeds enter an Observability \& Staleness Gate that routes decisions to the least complex sufficient model: Tier 1 routes fresh observable telemetry ($\tau=0, \exists\beta$) to deterministic aerodynamic rules ([Lowest Cost], $6.8\%$ violation); Tier 2 routes observable operational delays ($\tau \le 20\text{ min}, \exists\beta$) to state-conditional recalibration, absorbing $55.3\%$ of shortage loss without neural retraining; Tier 3 routes pitch-withheld or contingency telemetry ($\beta=\emptyset$ or $\tau \ge 60\text{ min}$) to learned consequence representations (STGQ-Modular), recovering latent regimes while preserving the central boundary condition that recoverability does not imply plant-wide decision superiority.}
\label{fig:decision-boundaries}
\end{figure}


## Pre-Dispatch Risk Screening Framework and Resampling Hierarchy

All neural architectures share an identical training protocol using AdamW with early stopping on validation RMSE, gradient clipping, and mixed-precision execution across five random seeds (201--205). Strong baselines (Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, TiDE) repeat across seeds 201--205 under identical evaluation caches. To eliminate data leakage, the sequential dataflow $\mathcal{D}_{\mathrm{train}} \to \mathcal{D}_{\mathrm{val}} \to \text{Freeze} \to \mathcal{D}_{\mathrm{test}}$ freezes quantile offsets $\hat{r}(k)$ prior to test replay. We report 5-seed initialization statistics alongside operational 95\% confidence intervals computed via a paired daily cluster bootstrap over the 35 observed test days (144 ten-minute steps per daily cluster), using 1,000 Monte Carlo bootstrap resamples (where resampled replicates reflect bootstrap draws rather than independent observational units).



# Empirical Findings: Minimum Sufficient Modeling Across Observability Regimes

## Regime 1: Fresh Observable Telemetry $\to$ Deterministic Aerodynamics and Operational Breakdown Boundaries (RQ1)

Table~\ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) evaluated on the boundary-active operating slice ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations across 134 turbines over the 35-day test split) under nominal clean telemetry. Table~\ref{tab:h6-paired} reports seed-paired hypothesis tests and mechanism ablations across operational regimes, along with 95\% confidence intervals from a paired daily cluster bootstrap over the 35 observed test days (1,000 resamples).

\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{0.90}
\caption{Cross-Seed Multi-Regime Pre-Dispatch Reserve Screening Benchmark on Boundary-Active Operating Regimes under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Boundary-Band Events ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations, 35 Test Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data. Commensurate plant-wide full-population baselines ($N=408{,}939$ cells) range from $14.0\text{M}$ to $16.5\text{M kW}\cdot\text{h}$ (see text and Metric-Scope Registry).}
\label{tab:h6-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & \shortstack{Penalized Reserve\\Energy (kW$\cdot$h)} & \shortstack{Violation\\Rate} & \shortstack{Reserve\\(kW)} & \shortstack{Shortage\\(kW$\cdot$h)} & \shortstack{Pinball\\Loss} \\
\midrule
\textbf{Clean (boundary)} & Continuous Physical Quantile & $\mathbf{881{,}367 \pm 95{,}741}$ & $6.81\% \pm 1.13\%$ & $653{,}738 \pm 72{,}557$ & $22{,}763 \pm 4{,}013$ & $31.41 \pm 2.66$ \\
 & \shortstack[l]{Direct Quantile MLP$^{\ddagger}$} & $1{,}649{,}721 \pm 285{,}682$ & $0.58\% \pm 0.26\%$ & $1{,}630{,}572 \pm 293{,}346$ & $1{,}915 \pm 958$ & $64.62 \pm 12.05$ \\
 & Global Quantile & $998{,}988 \pm 107{,}360$ & $6.46\% \pm 1.31\%$ & $771{,}304 \pm 95{,}661$ & $22{,}768 \pm 4{,}854$ & $36.50 \pm 3.41$ \\
 & STGQ-Dense & $991{,}181 \pm 110{,}211$ & $6.54\% \pm 1.04\%$ & $761{,}480 \pm 94{,}244$ & $22{,}970 \pm 4{,}121$ & $36.16 \pm 3.58$ \\
 & STGQ-Routed & $959{,}027 \pm 103{,}290$ & $7.10\% \pm 1.17\%$ & $707{,}249 \pm 91{,}305$ & $25{,}178 \pm 4{,}816$ & $34.77 \pm 3.16$ \\
 & \shortstack[l]{Missingness-Aware GBDT} & $1{,}238{,}603 \pm 112{,}051$ & $4.50\% \pm 0.73\%$ & $1{,}085{,}168 \pm 118{,}015$ & $15{,}343 \pm 2870$ & $46.85 \pm 3.48$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $1{,}136{,}466 \pm 84{,}101$ & $12.20\% \pm 1.25\%^{\dagger}$ & $662{,}335 \pm 73{,}483$ & $47{,}413 \pm 3{,}091$ & $38.85 \pm 2.06$ \\
 & \shortstack[l]{Direct Quantile MLP$^{\ddagger}$} & $1{,}682{,}251 \pm 284{,}323$ & $1.20\% \pm 0.52\%$ & $1{,}651{,}979 \pm 297{,}715$ & $3{,}027 \pm 1{,}594$ & $62.15 \pm 11.70$ \\
 & Global Quantile & $1{,}180{,}603 \pm 91{,}754$ & $10.85\% \pm 1.55\%^{\dagger}$ & $780{,}916 \pm 96{,}853$ & $39{,}969 \pm 6{,}087$ & $40.73 \pm 2.43$ \\
 & STGQ-Dense & $1{,}179{,}859 \pm 95{,}268$ & $11.04\% \pm 1.22\%^{\dagger}$ & $773{,}103 \pm 94{,}462$ & $40{,}676 \pm 4{,}788$ & $40.70 \pm 2.66$ \\
 & STGQ-Routed & $1{,}163{,}593 \pm 91{,}299$ & $11.82\% \pm 1.64\%^{\dagger}$ & $720{,}015 \pm 92{,}196$ & $44{,}358 \pm 7{,}341$ & $40.01 \pm 2.54$ \\
 & \shortstack[l]{Missingness-Aware GBDT} & $1{,}320{,}003 \pm 93{,}135$ & $8.36\% \pm 0.97\%$ & $1{,}030{,}858 \pm 114{,}266$ & $28{,}915 \pm 4{,}469$ & $46.68 \pm 2.45$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $\mathbf{998{,}273 \pm 106{,}253}$ & $7.59\% \pm 0.95\%$ & $746{,}697 \pm 82{,}474$ & $25{,}158 \pm 3{,}968$ & $33.97 \pm 2.78$ \\
 & \shortstack[l]{Direct Quantile MLP$^{\ddagger}$} & $1{,}639{,}909 \pm 242{,}922$ & $0.80\% \pm 0.28\%$ & $1{,}618{,}439 \pm 249{,}374$ & $2{,}147 \pm 953$ & $60.62 \pm 9.85$ \\
 & Global Quantile & $1{,}053{,}552 \pm 114{,}150$ & $7.48\% \pm 1.48\%$ & $802{,}361 \pm 99{,}513$ & $25{,}119 \pm 5{,}822$ & $36.26 \pm 3.24$ \\
 & STGQ-Dense & $1{,}048{,}083 \pm 115{,}181$ & $7.63\% \pm 1.13\%$ & $792{,}472 \pm 92{,}391$ & $25{,}561 \pm 4{,}643$ & $36.04 \pm 3.28$ \\
 & STGQ-Routed & $1{,}027{,}077 \pm 114{,}317$ & $7.62\% \pm 1.09\%$ & $769{,}864 \pm 106{,}672$ & $25{,}721 \pm 3{,}963$ & $35.16 \pm 3.19$ \\
 & \shortstack[l]{Missingness-Aware GBDT} & $1{,}314{,}640 \pm 129{,}158$ & $4.66\% \pm 0.80\%$ & $1{,}160{,}329 \pm 137{,}650$ & $15{,}431 \pm 3{,}099$ & $47.11 \pm 3.87$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{907{,}871 \pm 96{,}820}$ & $7.20\% \pm 1.15\%$ & $663{,}875 \pm 73{,}821$ & $24{,}400 \pm 4{,}106$ & $31.59 \pm 2.61$ \\
 & \shortstack[l]{Direct Quantile MLP$^{\ddagger}$} & $1{,}680{,}339 \pm 289{,}602$ & $0.57\% \pm 0.25\%$ & $1{,}660{,}135 \pm 298{,}104$ & $2{,}020 \pm 992$ & $64.38 \pm 12.00$ \\
 & Global Quantile & $1{,}030{,}131 \pm 108{,}592$ & $6.87\% \pm 1.39\%$ & $785{,}305 \pm 97{,}397$ & $24{,}483 \pm 5{,}104$ & $36.78 \pm 3.35$ \\
 & STGQ-Dense & $1{,}020{,}078 \pm 112{,}195$ & $6.90\% \pm 1.07\%$ & $775{,}899 \pm 96{,}235$ & $24{,}418 \pm 4{,}246$ & $36.35 \pm 3.57$ \\
 & STGQ-Routed & $990{,}625 \pm 104{,}487$ & $7.51\% \pm 1.22\%$ & $720{,}858 \pm 92{,}754$ & $26{,}977 \pm 5{,}183$ & $35.10 \pm 3.10$ \\
 & \shortstack[l]{Missingness-Aware GBDT} & $1{,}261{,}941 \pm 112{,}754$ & $4.88\% \pm 0.75\%$ & $1{,}094{,}730 \pm 120{,}612$ & $16{,}721 \pm 3{,}298$ & $46.62 \pm 3.40$ \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\fontsize{8.0pt}{9.0pt}\selectfont $^{\dagger}$Exceeds nominal 10\% violation target ($q^* = 0.90$). Bold indicates lowest surrogate metric. \textbf{Scope \& Reconciliation:} Evaluated at $h=6$ strictly across boundary-band cells ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$, $\sim 2.4\%$ of test split); Continuous Physical Quantile achieves lowest cost ($881{,}367\text{ kW}\cdot\text{h}$) but collapses to 12.20\% violation under Delay-6. Full-population ($N=408{,}939$) direct quantiles achieve $14.0\text{M}\text{--}16.5\text{M kW}\cdot\text{h}$ at $h=6$ and $6.49\text{M}\text{--}8.05\text{M}$ at $h=1$ (Section~\ref{sec:modular-baseline}; incommensurate scopes). $^{\ddagger}$Frozen-Embedding Direct Quantile MLP evaluates uncalibrated pinball regression on frozen representations; calibrated STGQ-Modular resolves this conservatism.}
\end{tabular*}
\end{table*}

\begin{table}[!htbp]
\centering
\fontsize{8.0pt}{8.9pt}\selectfont
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{0.88}
\caption{Seed-Paired Operational Hypothesis Tests and Mechanism Ablation Contrasts ($h=6$, 1-Hour Ahead Dispatch, Cost Ratio $\rho=10$).}
\label{tab:h6-paired}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}llcc@{}}
\toprule
Regime & Evaluated Contrast & \shortstack{$\Delta\text{PSREI}$\\(kW$\cdot$h)} & \shortstack{95\% Daily Cluster CI\\(1,000 Resamples)} \\
\midrule
\textbf{Clean} & Cont. Phys. (Rule) & $-$77,659 & [$-$106.2k, $-$49.1k]$^{\ast\ast}$ \\
 & STGQ-Dense vs. Routed & +32,154 & [$-$1.1k, +65.5k] \\
 & Global Quantile & +39,962 & [+12.6k, +67.4k]$^{\ast}$ \\
 & Missingness GBDT & +279,576 & [+249.5k, +309.6k]$^{\ast}$ \\
 & Direct MLP (Pinball) & +690,695 & [+448.8k, +932.6k]$^{\ast\ast}$ \\
\midrule
\textbf{Delay-6} & Cont. Phys. (Breakdown) & $-$27,126 & [$-$46.9k, $-$7.3k]$^{\dagger}$ \\
 & STGQ-Dense vs. Routed & +16,267 & [+7.1k, +25.4k]$^{\ast}$ \\
 & Global Quantile & +17,010 & [+3.5k, +30.5k]$^{\ast}$ \\
 & Missingness GBDT & +156,411 & [+140.0k, +172.8k]$^{\ast}$ \\
 & Direct MLP (Pinball) & +518,658 & [+307.2k, +730.1k]$^{\ast\ast}$ \\
\midrule
\textbf{Noise} & Cont. Phys. (Robust) & $-$28,804 & [$-$47.6k, $-$10.1k]$^{\ast}$ \\
 & STGQ-Dense vs. Routed & +21,006 & [+2.4k, +39.6k]$^{\ast}$ \\
 & Global Quantile & +26,475 & [+9.1k, +43.8k]$^{\ast}$ \\
 & Missingness GBDT & +287,563 & [+248.8k, +326.3k]$^{\ast}$ \\
 & Direct MLP (Pinball) & +612,832 & [+413.7k, +811.9k]$^{\ast\ast}$ \\
\midrule
\textbf{Markov} & Cont. Phys. (Rule) & $-$82,754 & [$-$111.0k, $-$54.5k]$^{\ast\ast}$ \\
 & STGQ-Dense vs. Routed & +29,453 & [$-$2.9k, +61.8k] \\
 & Global Quantile & +39,506 & [+16.0k, +63.1k]$^{\ast}$ \\
 & Missingness GBDT & +271,316 & [+245.0k, +297.6k]$^{\ast}$ \\
 & Direct MLP (Pinball) & +689,714 & [+448.7k, +930.7k]$^{\ast\ast}$ \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{8.8pt}\selectfont Note: 95\% CIs from paired daily cluster bootstrap over 35 observed test days (144 steps/cluster, 1,000 Monte Carlo resamples). $^{\ast\ast}p<0.01, ^{\ast}p<0.05$. $^{\dagger}$Physical rule breaches nominal 10\% violation target ($12.20\%$). Dynamic MoE routing advantage over unrouted dense architecture is falsified ($p=0.380$).
\end{table}

The empirical evidence directly establishes the operational sufficiency of deterministic aerodynamics under fresh observable telemetry. Under pristine telemetry ($\tau = 0$), Continuous Physical Quantile achieves the lowest surrogate reserve screening cost within the active boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations) among all evaluated methods ($589{,}535 \pm 77{,}390\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with target-satisfying $\sim 6.8\%$ violation). It outperforms both unrouted dense networks (STGQ-Dense: $991{,}181\text{ kW}\cdot\text{h}$) and dynamically routed architectures (STGQ-Routed: $959{,}027\text{ kW}\cdot\text{h}$) by $8.1\%\text{--}11.1\%$. As confirmed in Table~\ref{tab:h6-paired}, Continuous Physical Quantile achieves a $-77{,}659\text{ kW}\cdot\text{h}$ advantage over neural representations, with a 95\% daily cluster bootstrap confidence interval (1,000 paired resamples over 35 observed days) strictly excluding zero ($[-106{,}175, -49{,}143]$). When inflow wind speed and blade pitch angle are fresh and directly observable, deterministic aerodynamic equations yield the lowest evaluated surrogate reserve screening cost. Neural networks, lacking hard physical saturation bounds, introduce unnecessary variance under nominal telemetry.

However, Table~\ref{tab:h6-benchmark} exposes the operational reliability boundary of physical rules when telemetry becomes stale. In real SCADA networks, transmission delays of 10--30 minutes introduce latency drift between true inflow and evaluated registers. Under a 60-minute latency contingency stress test (Delay-6), which serves as an asymptotic reliability breakdown stress endpoint rather than an industrial prevalence claim, physical equations evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. Near rated wind speed, the localized slope discontinuity (\ref{eq:sensitivity-cliff}) amplifies delayed-inflow errors: turbines that have crossed into active blade-pitch regulation ($Z_t = 2$) are evaluated with obsolete fine pitch ($\beta_{t-\tau} \approx 0^\circ$), over-extrapolating power output along the steep cubic trajectory (\ref{eq:stale-phys}). Consequently, unadapted physical quantile violation rates surge from $6.81\%$ to $24.02\% \pm 1.69\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$ ($1{,}136{,}466\text{ kW}\cdot\text{h}$), breaching the nominal 10\% Newsvendor target ($q^* = 0.90$) and leaving $127.55\text{ MWh}$ of unhedged generation shortfall across the array.


## Regime 2: Stale but Observable Telemetry $\to$ Non-Neural Recalibration Absorbs Drift (RQ2)

When telemetry channels remain observable under transmission delays, condition-matched state-conditional recalibration (\ref{eq:recalib}) adjusts quantile margins using held-out validation residuals undergoing the identical delay. As shown in Table~\ref{tab:phase-scan}, state-conditional recalibration absorbs $55.3\%$ of the shortage loss ($127.55 \to 57.01\text{ MWh}$), restoring fleet violation to $9.46\%$ and achieving a surrogate reserve cost of $1{,}228{,}609\text{ kW}\cdot\text{h}$ at $h=1$. Under full channel observability, recalibrated physical curves outperform all neural models (STGQ-Routed: $1{,}274{,}047\text{ kW}\cdot\text{h}$; STGQ-Modular: $1{,}283{,}855\text{ kW}\cdot\text{h}$).

\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{4.0pt}
\renewcommand{\arraystretch}{0.90}
\caption{Multidimensional operational progression across telemetry latency $\tau \in [0, 60]\text{ min}$ and pitch observability on boundary-active regimes ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cells, $h=1$, 5-seed mean on WTB; nominal $\tau=0$ baseline $593{,}258\text{ kW}\cdot\text{h}$ aligns within $0.6\%$ of the primary frozen $589{,}535\text{ kW}\cdot\text{h}$ boundary benchmark). Penalized reserve energy in kW$\cdot$h ($\rho=10$).}
\label{tab:phase-scan}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}ccccccc@{}}
\toprule
$\tau$ (min) & Pitch & \shortstack{Clean Phys.\\Metric (Viol.)} & \shortstack{Recal. Phys.\\Metric (Viol.)} & \shortstack{STGQ-Mod.\\Metric (Viol.)} & \shortstack{STGQ-Rout.\\Metric (Viol.)} & \shortstack{Operational\\Regime} \\
\midrule
0 & All & $\mathbf{593{,}258}$ ($7.3\%$) & $\mathbf{593{,}258}$ ($7.3\%$) & $663{,}347$ ($6.1\%$) & $663{,}915$ ($7.3\%$) & Regime I (Lowest Cost) \\
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
\multicolumn{7}{@{}p{\textwidth}@{}}{\fontsize{8.0pt}{9.0pt}\selectfont $^{\dagger}$Exceeds nominal 10\% violation target ($q^*=0.90$). Bold indicates lowest target-satisfying surrogate screening metric. Under $\tau=60\text{ min}$, target satisfaction is $3/5$ seeds ($60\%$) across models.}
\end{tabular*}
\end{table*}

To establish the operational limits of recalibration under communication drift, we evaluate a mismatched calibration matrix across test latencies $\tau_{\mathrm{test}} \in [0, 60]\text{ min}$ and calibration horizons $\tau_{\mathrm{cal}} \in [0, 60]\text{ min}$. Recalibrating at $\tau_{\mathrm{cal}} = 10\text{ min}$ withstands latency drift up to $\tau_{\mathrm{test}} = 20\text{ min}$ while maintaining target-satisfying tail coverage ($8.2\%\text{--}9.1\%$ violation). However, recalibration breaks down when staleness surges to $\tau_{\mathrm{test}} = 60\text{ min}$ ($13.8\%$ violation). This demonstrates that under full channel observability, distribution drift does not require neural representation learning: state-conditional recalibration recovers $55.3\%$ of the observed shortage loss ($127.6 \to 57.0\text{ MWh}$) without updating network weights.


## Regime 3: Critical State Unobservable $\to$ Consequence-Based State Recovery and Decision Boundaries (RQ2) \label{sec:withheld-channel}

The role of consequence-based state recovery is examined when blade-pitch telemetry is withheld across aggregator boundaries (\texttt{no\_pitch}, Table~\ref{tab:phase-scan}). Under pitch unobservability, physical rules and recalibration schemes lose direct state awareness, inflating recalibrated screening penalties from $824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$ to $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60\text{ min}$. 

Under this regime, the control register is unobservable at deployment, while its electromechanical consequences ($Z_t \to P_t, Q_t, \text{trajectory}$) remain partially recorded in arrived SCADA feeds. Learned representations (STGQ-Modular) reconstruct operating states from secondary consequences under \textbf{offline privileged supervision}.

We provide an explicit disclosure that pitch is available in training inputs but \mbox{withheld} in validation/test deployment: blade-pitch registers ($\beta$) were present in historical training buffers ($x_{\text{hist}}$ channels 7--8) and anchor physics, while pitch was strictly zero-masked and withheld during validation and testing. Trained using historically available pitch information that is withheld at deployment, offline privileged supervision improves latent-state organization and reduces representation collapse, while matched ablations do not establish an independent downstream reserve-cost gain (paired difference $\Delta \text{PSREI} = -312\text{k} \pm 1{,}086\text{k kW}\cdot\text{h}$, 95% bootstrap CI $[-1.31\text{M}, +0.34\text{M}]$, crossing zero).

Empirical consequence-channel identifiability audits disentangle the recovery mechanism: contemporaneous active power is the dominant mediator ($\text{AUROC} = 0.988$), while lagged trajectories and non-power consequence channels retain partial additional state information, and thermal channels contribute negligible high-frequency boundary information for 10-minute dispatch.

As detailed in Table~\ref{tab:phase-scan}, STGQ-Modular achieves $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ saving of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintains consistent reserve screening reductions of $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across all latencies, doubling transition-window recall ($0.416$ vs. $0.196$). 

\textbf{Separation of Information Recoverability and Decision Value:} State recoverability does not imply universal decision superiority. Operational validation separates three distinct claims: (i) \textit{Operating-state discrimination} (AUROC $> 0.94$, NMI $0.461$, ARI $0.647$); (ii) \textit{Probabilistic calibration of $P(Z \mid \mathcal{I}_t^{(d)})$} (bulk ECE $\le 3.46\%$, satisfying the $5\%$ screening gate; tail $\text{MCE} \approx 0.75\text{--}0.85$); and (iii) \textit{Reserve-decision value}. Against a strong observable wind-speed-conditioned quantile baseline (10 bins, $13.78\text{M kW}\cdot\text{h}$ plant-wide), posterior conditioning does not reduce plant-wide reserve screening costs ($14.31\text{M kW}\cdot\text{h}$, defined canonically as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). In steady operation ($63.8\%$ of test time), wind-speed binning serves as the operational minimum sufficient model, outperforming the posterior by $+410{,}304\text{ kW}\cdot\text{h}$ ($p=0.002$). Thus, strong wind-speed-conditioned quantiles remain lower-cost plant-wide.

The relative risk-cost trade-off shifts near operating transitions ($\pm 3$ steps, $36.3\%$ of records, $N=139{,}653$): frozen posterior conditioning yields lower raw violation ($7.24\%$ vs. $8.36\%$) and lower raw shortage ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$), but requires $+149{,}241\text{ kW}\cdot\text{h}$ greater reserve procurement, incurring a $+112{,}739\text{ kW}\cdot\text{h}$ net surrogate penalty under $\rho=10$ ($\rho_{\text{break}} \approx 40.89$). The raw violation-rate reduction is partly associated with greater reserve procurement. Decisive matched-budget frontier analysis across the common reserve support ($\mathcal{B}_{\text{common}} = [1.95\text{M}, 4.77\text{M}]\text{ kW}\cdot\text{h}$) demonstrates that at identical reserve budgets ($\Delta R \equiv 0$), posterior conditioning does not improve shortage-energy efficiency: lower violation frequency, where present, is offset by deeper residual uncovered shortfalls ($+5{,}234\text{ kW}\cdot\text{h}$ higher uncovered shortage on average across 5 seeds; strictly higher in 4 of 5 seeds across all evaluated budgets; 95\% paired day-cluster bootstrap CI $[-7{,}200, +1{,}904\text{ kW}\cdot\text{h}]$ for Seed 201, with bootstrap probability $P(\Delta U \ge 0) = 0.81$, confirming that matched-budget superiority is not established). Furthermore, dynamic Newsvendor re-optimization across $\rho \in [5, 100]$ exhibits no economic crossover, as high conditional tail variance forces severe reserve over-procurement ($+1.10\text{M kWh}$ at $\rho=100$). Recovering the latent boundary does not establish reserve-allocation superiority over strong observable wind-speed conditioning.


## Supporting Evidence and Falsification of Alternative Explanations (RQ3) \label{sec:modular-baseline}

Diagnostic analyses attribute the observed operational gains to specific representation mechanisms rather than routing complexity. The observed reserve-screening benefit is attributable to consequence-based representation and calibrated quantile sizing rather than dynamic expert routing, with modular architectures matching tail reliability ($9.7\%$ violation). In point forecasting, whole-sample error is decoupled from tail shortfall exposure. Furthermore, classification accuracy alone does not translate into reserve decision value: discrete classification errors concentrate during steep ramps where residuals compound Newsvendor penalties, with tail risk reduction effectively governed by uniform reserve-margin expansion rather than heuristic abstention scoring ($p > 0.40$). External evaluations across four commercial facilities reveal heterogeneous, site-dependent information regimes (STGQ reduces surrogate cost relative to global quantiles on WTB and Penmanshiel by $-2.14\text{M kW}\cdot\text{h}$, $p < 0.05$, matches the Kelmarsh 6-turbine array at $-40\text{k kW}\cdot\text{h}$, $p=0.85$, and incurs a $+43\text{k kW}\cdot\text{h}$ overfitting penalty on La Haute Borne, where turbine count alone does not explain cross-site variation), supporting site-specific assessment rather than universal transfer claims. Finally, portfolio aggregation at the Point of Common Coupling confirms that spatial smoothing cancels high-frequency turbulence while preserving coherent boundary transition risks.




# Discussion: Minimum Sufficient Model Complexity \label{sec:discussion}

The empirical findings establish an operational principle of \textbf{Minimum Sufficient Model Complexity}: when critical telemetry is unavailable, latent operating states may remain recoverable from observable consequence signals. Whether learned representations are necessary for that recovery, and whether recovered state information improves downstream decisions, are separate empirical questions. Dispatch operations should deploy the least complex model sufficient for the arriving information regime:

\textit{1) Fresh and Observable $\to$ Physics:} Deterministic aerodynamic curves evaluate pristine telemetry ($\tau = 0$) with asymptotic power conservation ($\partial P / \partial v \propto v^2$ below rated speed, $P \equiv P_{\mathrm{rated}}$ above rated speed). Avoiding out-of-distribution neural variance, they achieve the lowest evaluated surrogate reserve screening cost within the boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events: $589.5\text{k}\text{--}881.4\text{k kW}\cdot\text{h}$, target-satisfying $\sim 6.8\%$ violation; Tables~\ref{tab:h6-benchmark} and~\ref{tab:phase-scan}), rendering deep representations superfluous.

\textit{2) Stale but Observable $\to$ Recalibration:} Under observable operational latency ($10\text{--}30\text{ min}$), state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) and maintains violation rates below the nominal 10\% target ($7.1\%\text{--}7.5\%$) without updating neural weights. Static recalibration breaks down only under contingency horizons ($\tau = 60\text{ min}$, $13.8\%$ violation), which acts as a synthetic reliability breakdown stress endpoint rather than an industrial prevalence claim.

\textit{3) Critical State Unobservable $\to$ Consequence Recovery:} When blade-pitch telemetry is withheld (\texttt{no\_pitch}), physical rules lose direct state awareness and inflate penalties to $1{,}378{,}900\text{ kW}\cdot\text{h}$. Observable electromechanical consequences retain boundary information ($Z_t \to P_t, Q_t, \text{trajectory}$, $0.302\text{--}0.674$ NMI), where learned representations provide one effective mechanism for state recovery, saving $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ over unadapted physical curves.

\textit{4) Operational Decision Boundary:} Posterior conditioning does not reduce plant-wide reserve procurement costs over strong wind-speed-binned quantiles ($\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). While direct wind-speed binning serves as the plant-wide and steady-state minimum sufficient policy ($+410{,}304\text{ kW}\cdot\text{h}$ steady advantage, $p=0.002$), the relative risk-cost trade-off shifts near operating transitions ($\pm 3$ steps): posterior conditioning alters the operating point by procuring $+149{,}241\text{ kW}\cdot\text{h}$ additional reserve ($7.24\%$ vs. $8.36\%$ violation, leaving a $+112{,}739\text{ kW}\cdot\text{h}$ net surrogate penalty under $\rho=10$), but matched-budget frontiers confirm that at identical reserve expenditure, posterior conditioning fails to establish an allocation advantage ($+5{,}234\text{ kW}\cdot\text{h}$ higher shortage across 5 seeds, with 4 of 5 seeds showing higher shortfall across the common budget support; lower violation frequency is offset by deeper residual shortfalls). The significant interaction contrast ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}053\text{ kW}\cdot\text{h}, p = 0.002$) establishes heterogeneity of the relative cost gap rather than a positive posterior cost advantage. A deployable hybrid policy remains statistically equivalent to wind-speed binning ($13.79\text{M}$ vs. $13.78\text{M kW}\cdot\text{h}$, $p > 0.40$). Increasing routing complexity is not the operative source of value under the tested observability regimes, with modular regression (STGQ-Modular) matching tail reliability ($9.7\%$ violation) without dynamic routing overhead.

\textit{5) Industrial Deployment Guardrails:} (i) \emph{External heterogeneity}: external evaluations across four commercial wind farms reveal heterogeneous information regimes rather than uniform transfer superiority. STGQ reduces surrogate cost relative to global quantiles on WTB and Penmanshiel ($p < 0.05$), while Kelmarsh is neutral and LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy as a possible moderator (not turbine count alone), while turbine count alone does not explain the variation; (ii) \emph{Local retraining}: directional transfer asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. $0.34$) supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer; (iii) \emph{Reserve protection}: tail risk mitigation under latency is effectively governed by uniform reserve margin expansion rather than heuristic rejection scoring ($p > 0.40$).

# Limitations

The empirical findings are bounded by four operational and experimental scope conditions:

\textit{1) Synthetic Stress:} Impairments are evaluated under synthetic stress ($10\text{--}30\text{ min}$ backlogs, 60-min latency, Gilbert-Elliott dropouts); field units may exhibit sensor icing or individual pitch actions outside supervisory records.

\textit{2) Risk Surrogacy:} Evaluation operates at Level-1 pre-dispatch operating reserve screening via the PSREI newsvendor surrogate ($\rho=10$), abstracting Level-2 bulk transmission AC-OPF and balancing settlements.

\textit{3) Horizon Scope:} Benchmarks use a 35-day continuous test split across five random seeds (201--205), omitting multi-annual climatological cycles. Rated wind speeds vary by model ($12.5\text{ m/s}$ on MM92 vs. $14.5\text{ m/s}$ on MM82), requiring OEM calibration.

\textit{4) Deployment Boundaries:} Cross-site STGQ effects relative to the global quantile baseline remain heterogeneous, consistent with exploitable spatial redundancy as a possible moderator rather than turbine count alone; LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity. Because external benchmarks evaluate unconditioned global quantiles without matched external no-graph controls, wake modeling is not causally isolated as the sole mechanism for external gains. Directional transfer asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$) supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer. The study assumes historical blade-pitch availability during offline training, followed by pitch withholding at deployment. Performance in settings where pitch was never recorded remains untested.

# Conclusion

This study repositions machine learning in reserve screening from an indiscriminate forecasting tool to a targeted conditional inference mechanism governed by SCADA observability regimes. Telemetry degradation creates a hierarchy of sufficiency: \textit{use the least complex model sufficient for the arriving information regime. When critical telemetry is unavailable, latent operating states may remain recoverable from observable consequence signals; whether learned representations are necessary for that recovery, and whether recovered state information improves downstream decisions, are separate empirical questions.} First, under fresh telemetry, deterministic aerodynamic power curves minimize surrogate reserve penalties within the boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events: $589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, $\sim 6.8\%$ violation), collapsing only under unadapted latency ($24.0\%$ violation). Second, under observable delays, state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) without updating neural weights. Third, when blade pitch is withheld, observable consequences retain operating regime information, saving $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ over unadapted physics and doubling transition recall ($0.416$ vs. $0.196$). However, neither state recoverability nor lower violation frequency guarantees superior reserve decisions: strong wind-speed-conditioned quantiles remain lower-cost plant-wide, and matched-budget analysis demonstrates that lower transition violation frequency is partly volume-driven and offset by deeper residual shortfalls. Finally, increasing routing complexity is not the operative source of value under the tested observability regimes. The evaluated evidence supports deterministic rules under clean telemetry, recalibration under observable drift, and consequence-based recovery when critical telemetry is missing, while reserve sizing decisions remain governed by direct observable conditioning.

# Acknowledgment {.unnumbered}

The authors acknowledge the use of OpenAI ChatGPT and Codex for assistance in drafting and refining prose across Sections I--VII, formatting IEEE LaTeX macros, and developing automated verification scripts. All mathematical derivations, experimental designs, empirical results, and scientific interpretations were developed by the authors, who take full responsibility for the contents of this paper.

\textbf{Code and Data Availability:} Raw SCADA datasets (WTB, ENGIE La Haute Borne, Kelmarsh, Penmanshiel) are publicly available. Open-source replication code, manifests, and verification suites are available at \url{https://github.com/b1ue13e/windfarm-latent-boundary-risk}.
# References {.unnumbered}

::: {#refs}
:::
