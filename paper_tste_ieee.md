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
Operating reserve screening near the demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3) is governed by acute asymmetric shortfall risk: generation over-forecasts incur severe balancing penalties relative to surplus energy headroom. Deterministic aerodynamic power curves presume fresh, fully observable telemetry; however, commercial SCADA systems routinely encounter transmission latency, packet serialization dropouts, and aggregator-boundary pitch unobservability. Under degraded telemetry, turbine operating regimes cease to be directly observable and become latent states. Across multi-seed benchmarks on the 134-turbine WTB commercial plant and multi-year data from three European facilities, this paper investigates whether machine learning provides universal utility or conditional advantage under telemetry degradation.

Under pristine telemetry, deterministic physical rules achieve the lowest reserve-screening surrogate cost in the aerodynamic boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events) among all evaluated approaches ($589{,}535\text{ kW}\cdot\text{h}$ at 10-minute dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with $\sim 6.8\%$ violation), outperforming deep neural networks by $8.1\%$. Under a 60-minute latency contingency, unadapted physical rules undergo severe reliability breakdown, surging violation rates to $24.0\% \pm 1.7\%$ at $h=1$ and leaving $127.6\text{ MWh}$ of unhedged shortfall. Crucially, when telemetry channels remain observable, simple state-conditional recalibration absorbs $55.3\%$ of this shortage loss ($127.6 \to 57.0\text{ MWh}$) without neural representation learning. Learned representations acquire demonstrable utility only under deployment-time partial observability where blade-pitch registers are withheld: trained using historically available pitch information that is withheld at deployment, representations infer latent operating states from secondary electromechanical and spatio-temporal consequences (combining contemporaneous active-power diagnosis with dynamical trajectory tracking and wake context), doubling transition-window recall ($0.416$ vs. $0.196$). Relative to the unadapted physical comparator under pitch withholding, learned representations reduce the reserve-screening surrogate by $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across evaluated latencies; however, strong wind-speed-conditioned quantiles remain lower-cost plant-wide. Dynamic Mixture-of-Experts routing confers no statistical advantage over unrouted dense baselines ($p=0.380$), while decoupled modular architectures match tail reliability ($9.7\%$ violation). Furthermore, heuristic selective decision abstention fails to outperform random rejection, being Pareto-dominated by uniform reserve margin expansion. These findings establish that machine learning is valuable not as a universal replacement for aerodynamic rules, but as a conditional latent-state inference mechanism when critical physical states become unobservable.
\end{abstract}

\begin{IEEEkeywords}
Wind turbine operating reserve; SCADA telemetry degradation; partial observability; latent operating boundary; transmission latency; aerodynamic power curve; reliability breakdown; reserve-risk screening; state-conditional recalibration; MPPT-to-pitch transition.
\end{IEEEkeywords}



# Introduction

In bulk power system operations, real-time generation shortfalls incur severe asymmetric shortage penalties relative to surplus headroom; conventional symmetric metrics like root-mean-square error (RMSE) mask severe tail shortfall events that govern operating reserve adequacy in Level-1 pre-dispatch screening [@dowell2015veryshortterm; @kruse2023physics; @pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. This operational vulnerability concentrates near the aerodynamic demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3). Near rated inflow velocity, local power sensitivity transitions abruptly from a steep cubic trajectory ($\partial P / \partial v \propto v^2$) toward zero as pitch actuators shed aerodynamic lift [@slootweg2003general; @gaertner2020definition]. When operating states shift across this threshold unannounced, deterministic power curves over-extrapolate generation into Region 3, precipitating severe unhedged reserve deficits.

This vulnerability is exacerbated by telemetry degradation in commercial Supervisory Control and Data Acquisition (SCADA) systems, including gateway serialization overhead, packet queuing backlogs, and intermittent cellular transmission jitter [@tautzweinert2017scada; @ullah2022enabling]. In operational archives (such as Kelmarsh), 99.6\% of discrete turbine status transitions occur between standard 10-minute polling boundaries. Furthermore, in third-party aggregator and Virtual Power Plant (VPP) triage, blade-pitch registers are frequently restricted across commercial protocol firewalls. When delayed or missing measurements enter physical power equations, dispatch systems clear reserve margins against obsolete operating points. Under degraded telemetry, the turbine operating regime becomes a partially observed latent state.

Existing literature treats aerodynamic curves and deep neural networks as competing paradigms [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided], overlooking their distinct operational boundaries under information freshness constraints. Under pristine SCADA telemetry, deterministic aerodynamic quantile curves achieve the lowest reserve-screening surrogate cost within the active boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell events) among all evaluated methods ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, with target-satisfying $\sim 6.8\%$ violation), saving $8.1\%$ ($-77{,}659\text{ kW}\cdot\text{h}$) over neural architectures. However, deterministic rules undergo severe reliability breakdown under telemetry staleness: under a 60-minute synthetic latency contingency stress test [@pierre2019design; @ravikumar2020anomaly], clean-calibrated physical violation rates surge to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, breaching the nominal 10\% Newsvendor target ($q^* = 0.90$) and leaving $127.6\text{ MWh}$ of unhedged shortfall exposure.

To address this operational vulnerability, we investigate:
*When direct aerodynamic state measurements become stale or unavailable, can consequential spatio-temporal SCADA signals recover an operating-boundary posterior that remains dependable for asymmetric reserve-shortfall screening?*

The 134-turbine WTB site serves as the primary mechanism-identification environment (with five random seeds quantifying training stochasticity rather than independent physical replications), while multi-year evaluations on three external European facilities (ENGIE La Haute Borne, Kelmarsh, Penmanshiel) probe transferability and delineate site-dependent boundary conditions. This paper does not claim a novel graph or MoE architecture; instead, it delivers four verifiable contributions:

1. **Empirical Reliability Boundary under Telemetry Staleness**: We identify an empirical reliability boundary for aerodynamic reserve rules under telemetry staleness and partial state observability, showing that cubic sensitivity transitions amplify delayed-inflow errors and surge violation rates to $24.0\% \pm 1.7\%$.
2. **Separation of Recalibration from Information Loss**: We separate distributional recalibration from genuine information loss, showing that under full channel observability, simple state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) without updating neural weights.
3. **Transition-Localized Risk Reallocation under Latent-State Uncertainty**: We test recovered operating-state information against a strong wind-speed-conditioned quantile baseline. The posterior does not reduce plant-wide PSREI, but near operating transitions it reduces shortage and violation exposure at additional reserve cost, revealing a localized risk-hedging rather than cost-dominance effect. Wind-speed binning remains the plant-wide minimum sufficient policy, while a deployable validation-frozen hybrid policy remains statistically equivalent to wind-speed binning.
4. **Characterization of Multi-Site Failure Boundaries**: We characterize failure boundaries across telemetry conditions and external sites, including negative (LHB) and neutral (Kelmarsh) transfer results. Cross-site STGQ effects relative to the global quantile baseline are heterogeneous; the observed pattern is consistent with exploitable spatial redundancy as a possible moderator (not turbine count alone), while turbine count alone does not explain the variation.



# Related Work

## From Average Wind-Power Accuracy to Transition-Window Risk

Spatio-temporal graph neural networks (STGNNs) advance multi-step wind plant forecasting by modeling spatial cross-correlations and wake advection [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn], with physics-informed extensions incorporating wake and boundary constraints [@park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. While these architectures reduce plant-wide $L_2$ error, continuous trajectory minimization obscures discrete turbine operating state transitions between MPPT (Region 2) and pitch regulation (Region 3) that govern spinning reserve adequacy [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind]. 

Recent physics-aware dynamic-graph MoE models, such as Zhao et al. [@zhao2026physicsaware], ask whether architectural coupling of spatial learning, physical guidance, and expert routing improves wind-power forecasting accuracy. We explicitly concede this architectural neighborhood and treat such components as diagnostic comparators rather than claiming graph, MoE, or physics-guided neural architecture novelty. Instead, we ask an information-and-decision question: when critical aerodynamic states become unobservable due to telemetry degradation, what information remains recoverable from secondary consequence channels, when is simple conditional recalibration sufficient without neural learning, and whether the recovered latent state changes asymmetric reserve-risk decisions. Probabilistic forecasts monetize uncertainty through reserve procurement [@dowell2015veryshortterm; @kruse2023physics; @bremnes2004quantile]. We address this upstream bottleneck: screening aerodynamic transition risks under degraded SCADA telemetry prior to market clearing, functioning strictly as a Level-1 pre-dispatch triage proxy while abstracting downstream transmission constraints.



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

Under pristine telemetry, $\bar{p}_{i,t}$ and $w_{i,t}$ are known, so $Z_{i,t}$ is directly observable. Under transmission latency $\tau > 0$ or when pitch registers are withheld across aggregator interfaces, $Z_{i,t}$ becomes a \textbf{partially observed latent state}. The central inferential object is the soft operating-boundary posterior:
\begin{equation}
p(Z_{i,t} \mid \mathbf{X}_{\le t}),
\label{eq:posterior-dist}
\end{equation}
inferred from historical and spatial consequence channels.


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
Because output clamps at $P_{\mathrm{rated}}$, this stale evaluation produces severe over-forecast error $\hat{P}_{\mathrm{phys}}(t) - P_{\mathrm{rated}} \gg 0$, surging empirical violation rates to $24.0\% \pm 1.7\%$ under Delay-6 ($\rho=10$).


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

\textbf{Explicit Methodological Notice:} $\mathcal{L}_{\mathrm{align}}$ acts strictly as an \textbf{operating-regime prior} embedded into representation space. The neural backpropagation pipeline contains no quantile loss, pinball penalty, or Newsvendor decision loss. Checkpoint selection is strictly governed by validation RMSE. Quantile reserve margins are calibrated on held-out validation residuals or estimated by the decoupled residual head, yielding a jointly represented boundary posterior rather than an end-to-end decision posterior.



# Case Study Configuration and Operational Constraints

## Datasets and Preprocessing

Empirical evaluation spans the 134-turbine WTB benchmark and the ERA5 thermodynamic contrast patch. WTB (KDD Cup 2022) comprises 134 turbines over 245 days of 10-minute SCADA telemetry ($T=35{,}280$, $N=134$, $F=11$) [@zhou2024sdwpfdata], with chronological 180/30/35-day train/val/test splits ($H=36, P=24$). ERA5 covers three archived months on a $16 \times 16$ grid ($T=2208$, $N=256$, 8 features) [@hersbach2020era5] under 1325/441/442 splits. Multi-year SCADA records from three European commercial wind plants (ENGIE La Haute Borne, Kelmarsh, Penmanshiel) provide diverse turbine architectures for cross-farm evaluation.


## Controlled Telemetry Degradation Protocols and Realism Mapping

To evaluate resilience under communication stress, we simulate three degradation tiers across five seeds (201--205): (1) \textbf{Tier 1 (Nominal Polling, $0\text{--}10\text{ min}$, Clean)}: fresh SCADA on 10-min grid (IEC 61400-25); (2) \textbf{Tier 2 (Plausible Degraded Telemetry, $10\text{--}30\text{ min}$, Delay-1 to 3)}: transmission lags from substation buffer backlogs [@ullah2022enabling]; and (3) \textbf{Tier 3 (Contingency Stress Envelope, $60\text{ min}$, Delay-6)}: a 6-step synthetic lag evaluating asymptotic physical breakdown [@pierre2019design; @ravikumar2020anomaly]. Perturbations include additive Gaussian noise ($\sigma_v = 1.0\text{ m/s}, \sigma_\beta = 2.0^\circ$) and a two-state Markov burst dropout chain ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$) [@ullah2022enabling].

Fig.~1 illustrates the causal decision failure mechanism and the three-tier operational recovery hierarchy across telemetry degradation regimes.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,keepaspectratio]{figures/figure1_decision_boundaries.pdf}
\caption{Causal decision failure and information recovery hierarchy under SCADA telemetry degradation. Panel A: Physical mechanism and staleness breakdown at rated cut-off, showing how telemetry staleness turns the operating regime $Z_t$ into a latent variable, precipitating cubic extrapolation errors and severe reserve shortfalls (24.0\% violation, 127.6 MWh deficit). Panel B: Three-tier information-centric recovery hierarchy, routing fresh telemetry to Tier 1 deterministic physical rules, observable delay to Tier 2 state-conditional recalibration, and pitch-withheld/contingency telemetry to Tier 3 learned latent representations (STGQ-Modular). Panel C: Empirical mechanism falsification and negative results, showing that dynamic MoE routing yields no advantage over unrouted dense/modular architectures ($p=0.380$) and heuristic selective abstention fails to beat random rejection.}
\label{fig:decision-boundaries}
\end{figure}


## Pre-Dispatch Risk Screening Framework and Resampling Hierarchy

All neural architectures share an identical training protocol using AdamW with early stopping on validation RMSE, gradient clipping, and mixed-precision execution across five random seeds (201--205). Strong baselines (Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, TiDE) repeat across seeds 201--205 under identical evaluation caches. To eliminate data leakage, the sequential dataflow $\mathcal{D}_{\mathrm{train}} \to \mathcal{D}_{\mathrm{val}} \to \text{Freeze} \to \mathcal{D}_{\mathrm{test}}$ freezes quantile offsets $\hat{r}(k)$ prior to test replay. We report 5-seed initialization statistics alongside operational 95\% confidence intervals computed via a paired daily cluster bootstrap over the 35 observed test days (144 ten-minute steps per daily cluster), using 1,000 Monte Carlo bootstrap resamples (where resampled replicates reflect bootstrap draws rather than independent observational units).



# Empirical Findings and Hypothesis Testing

## Result 1: Physics under Fresh Telemetry (RQ1)

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

The empirical evidence directly challenges the presumption that deep neural architectures universally outperform physical models. Under pristine telemetry ($\tau = 0$), Continuous Physical Quantile achieves the lowest surrogate reserve screening cost within the active boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations) among all evaluated methods ($589{,}535 \pm 77{,}390\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with target-satisfying $\sim 6.8\%$ violation). It substantially outperforms both unrouted dense networks (STGQ-Dense: $991{,}181\text{ kW}\cdot\text{h}$) and dynamically routed architectures (STGQ-Routed: $959{,}027\text{ kW}\cdot\text{h}$). As confirmed in Table~\ref{tab:h6-paired}, Continuous Physical Quantile achieves a $-77{,}659\text{ kW}\cdot\text{h}$ advantage over neural representations, with a 95\% daily cluster bootstrap confidence interval (1,000 paired resamples over 35 observed days) strictly excluding zero ($[-106{,}175, -49{,}143]$). 

This finding establishes that when inflow wind speed and blade pitch angle are fresh and directly observable, deterministic aerodynamic equations yield the lowest evaluated surrogate reserve screening cost. Neural networks, lacking hard physical saturation bounds, introduce unnecessary variance under nominal telemetry.


## Result 2: Stale-State Boundary Failure (RQ1) \label{sec:physical-breakdown}

While deterministic physical rules excel under fresh data, Table~\ref{tab:h6-benchmark} exposes their \textbf{severe reliability breakdown} under telemetry staleness. Under a 60-minute latency contingency stress test (Delay-6), deterministic physical curves evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. Near rated wind speed, the localized slope discontinuity (\ref{eq:sensitivity-cliff}) amplifies delayed-inflow errors: turbines that have crossed into active blade-pitch regulation ($Z_t = 2$) are evaluated with obsolete fine pitch ($\beta_{t-\tau} \approx 0^\circ$), over-extrapolating power output along the steep cubic trajectory (\ref{eq:stale-phys}).

Consequently, unadapted physical quantile violation rates surge from $6.81\%$ to $24.02\% \pm 1.69\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, breaching the nominal 10\% Newsvendor target ($q^* = 0.90$). This breakdown leaves $127.55\text{ MWh}$ of unhedged generation shortfall across the array. This delineates the exact operational reliability boundary of deterministic aerodynamic rules: when transmission latency delays state observation, physical rules cease to provide dependable reserve screening.


## Result 3: Recalibration under Full Observability (RQ2)

When telemetry channels remain observable under transmission delays, condition-matched state-conditional recalibration (\ref{eq:recalib}) adjusts quantile margins using held-out validation residuals undergoing the identical delay. As shown in Table~\ref{tab:phase-scan}, state-conditional recalibration absorbs $55.3\%$ of the shortage loss ($127.55 \to 57.01\text{ MWh}$), restoring fleet violation to $9.46\%$ and achieving a surrogate reserve cost of $1{,}228{,}609\text{ kW}\cdot\text{h}$ at $h=1$. In fact, recalibrated physical curves outperform all neural models under full observability (STGQ-Routed: $1{,}274{,}047\text{ kW}\cdot\text{h}$; STGQ-Modular: $1{,}283{,}855\text{ kW}\cdot\text{h}$).

To establish the operational limits of recalibration under communication drift, we evaluate a mismatched calibration matrix across test latencies $\tau_{\mathrm{test}} \in [0, 60]\text{ min}$ and calibration horizons $\tau_{\mathrm{cal}} \in [0, 60]\text{ min}$ (Supplementary Table~A11l). Recalibrating at $\tau_{\mathrm{cal}} = 10\text{ min}$ withstands latency drift up to $\tau_{\mathrm{test}} = 20\text{ min}$ while maintaining target-satisfying tail coverage ($8.2\%\text{--}9.1\%$ violation). However, recalibration breaks down when staleness surges to $\tau_{\mathrm{test}} = 60\text{ min}$ ($13.8\%$ violation). This demonstrates that under full channel observability, distribution drift alone does not justify deep representation learning: simple state-conditional recalibration recovers a substantial share of the observed shortage loss ($55.3\%$, $127.6 \to 57.0\text{ MWh}$).


## Result 4: Learned Recovery under Pitch Unobservability (RQ2) \label{sec:withheld-channel}

The targeted utility of machine learning emerges when blade-pitch telemetry is withheld across aggregator boundaries (\texttt{no\_pitch}, Table~\ref{tab:phase-scan}). Under pitch unobservability, physical rules and recalibration schemes lose direct state awareness, inflating recalibrated screening penalties from $824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$ to $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60\text{ min}$. 

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

In contrast, learned representations (STGQ-Modular) reconstruct operating states from secondary consequences under \textbf{offline privileged supervision}. Specifically, we provide an explicit disclosure that pitch is available in training inputs but withheld in validation/test deployment: blade-pitch registers ($\beta$) were present in historical training buffers ($x_{\text{hist}}$ channels 7--8) and anchor physics, while pitch was strictly zero-masked and withheld during validation and testing. Offline privileged supervision ($\mathcal{L}_{\text{align}}$ cross-entropy on aerodynamic regime labels $Z$) forces secondary consequence channels to reconstruct the latent boundary space. A clean matched-backbone ablation ($\lambda_{\text{align}}=5000.0$ vs. $0.0$, 5 seeds) confirms that regime supervision improves latent-state organization and reduces representation collapse (NMI $0.819 \pm 0.088$ vs. $0.240 \pm 0.150$, paired $\Delta = +0.579 \pm 0.167$, $p=0.0015$, 95% CI $[+0.371, +0.787]$; ARI $0.889 \pm 0.057$ vs. $0.198 \pm 0.139$, paired $\Delta = +0.692 \pm 0.153$, $p=0.0005$, 95% CI $[+0.502, +0.882]$). For posterior calibration, supervision improves Brier score ($0.020 \pm 0.002$ vs. $0.241 \pm 0.419$, paired $\Delta = -0.221 \pm 0.418$), though sensitive to representation collapse in Seed 204 (Brier $0.981$; excluding Seed 204 yields $\Delta = -0.036 \pm 0.073$, 5-seed 95% CI $[-0.740, +0.299]$, $p=0.303$). Downstream reserve decision value is evaluated separately, as privileged supervision alone yields an unestablished cost delta ($-311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$ plant-wide, $p=0.556$; $+15{,}261 \pm 27{,}504\text{ kW}\cdot\text{h}$ on the boundary slice, $p=0.283$; Table~A6c). Crucially, this matched ablation isolates regime-label supervision conditional on privileged training inputs, without isolating training-time pitch access itself. Furthermore, empirical identifiability audits (Table~A7b and Registry) disentangle the recovery mechanism: (1) \emph{Active power signature}: instantaneous power $P_{\text{atv}, t}$ provides primary state resolution (Condition A: $59.7\%$ precision, $63.1\%$ recall, F1 $0.613$, FPR $0.8\%$, AUROC $0.988$), while historical trajectory $P_{\text{atv}, <t}$ retains $40.3\%$ recall and lag-1 $P_{\text{atv}, t-1}$ achieves $58.8\%$, confirming genuine dynamical tracking beyond instantaneous readout; (2) \emph{Consequence suite without current active power}: withholding contemporaneous active power (Condition D) shifts the detector to an asymmetric, high-recall operating point ($82.2\%$ recall, $33.4\%$ precision, F1 $0.475$, FPR $3.2\%$, AUROC $0.975$), confirming that the remaining non-active-power consequence suite retains some collectively recoverable state information; and (3) \emph{Thermal invariance}: conditional ablation of thermal channels ($E_{\text{tmp}}, I_{\text{tmp}}$) yields negligible discrimination change ($\Delta\text{AUROC} = +0.006$, $\Delta\text{F1} = -0.010$, $\Delta\text{Brier} = -0.0008$), confirming that slow thermal dynamics fail to contribute incremental high-frequency boundary information for 10-minute dispatch.

As detailed in Table~\ref{tab:phase-scan}, STGQ-Modular achieves $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ saving of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintains consistent reserve screening reductions of $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across all latencies, doubling transition-window recall ($0.416$ vs. $0.196$). 

\textbf{Disentangling Discrimination, Calibration, and Decision Value:} Operational validation separates three distinct claims: (i) \textit{Operating-state discrimination} (AUROC $> 0.94$, NMI $0.461$, ARI $0.647$); (ii) \textit{Probabilistic calibration of $P(Z \mid \mathcal{I}_t^{(d)})$} (bulk ECE $\le 3.46\%$, satisfying the $5\%$ screening gate; tail $\text{MCE} \approx 0.75\text{--}0.85$); and (iii) \textit{Reserve-decision value}. Crucially, against a strong observable wind-speed-conditioned quantile baseline (10 bins, $13.78\text{M kW}\cdot\text{h}$ plant-wide), posterior conditioning does not reduce plant-wide reserve screening costs ($14.31\text{M kW}\cdot\text{h}$, defined canonically as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). In steady operation ($63.7\%$ of test time), wind-speed binning serves as the operational minimum sufficient model, outperforming the posterior by $+410{,}340\text{ kW}\cdot\text{h}$ ($p=0.002$). The relative risk-cost trade-off becomes materially more favorable near operating transitions ($\pm 3$ steps, $36.3\%$ of records): posterior conditioning selectively reduces violation ($7.24\%$ vs. $8.36\%$) and shortage exposure ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$), but this hedge remains more expensive under $\rho=10$ than wind-speed-binned quantile calibration ($\Delta = +112{,}704\text{ kW}\cdot\text{h}$, driven by $+149{,}092\text{ kW}\cdot\text{h}$ greater reserve procurement). The significant paired day-level cluster bootstrap interaction ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}123\text{ kW}\cdot\text{h}, p < 0.005$) establishes heterogeneity of the relative cost gap rather than a positive posterior cost advantage. Transition windows are not merely high-loss regions; they are the regions where recovered latent-state information selectively hedges tail risk at added reserve expense. While transition windows capture $48.4\%$ of savings relative to an unconditioned global baseline, this unconditioned fraction reflects high baseline loss concentration ($33.0\%$) alongside model sensitivity; relative to wind-speed bins, the posterior acts as a localized risk hedge. A deployable validation-frozen hybrid policy matches wind-speed binning plant-wide ($13.79\text{M}$ vs. $13.78\text{M kW}\cdot\text{h}, p > 0.40$), confirming that machine learning provides conditional regime risk hedging rather than universal cost dominance.


## Result 5: Classification Accuracy Does Not Equal Reserve Value (RQ3)

A critical question in operational machine learning is whether higher classification accuracy translates directly into lower reserve screening costs. To interrogate this hypothesis, we benchmark an independent sequence classifier (Graph WaveNet coupled to a live-anchor classifier) against joint representation models using empirical records from completed control benchmarks (\texttt{modular\_classifier\_reserve\_summary.csv}).

Under nominal telemetry, the independent classifier achieves perfect transition recall ($1.000$) and high precision ($0.879$), surpassing the joint boundary router ($0.960$ recall, $0.758$ precision). However, when evaluated on pre-dispatch reserve screening, the independent classifier incurs a surrogate reserve cost of $86{,}536{,}321\text{ kW}\cdot\text{h}$ ($9.54\%$ violation). Across all five training seeds, the independent classifier incurred higher surrogate cost than the physical-bin baseline ($84{,}314{,}353\text{ kW}\cdot\text{h}$, $9.31\%$ violation; mean paired difference $+2.22\text{M kW}\cdot\text{h}$; paired $t$-test $p=0.0013$, 95\% CI $[+1.66\text{M}, +2.63\text{M}]$). Because $n=5$ limits the resolution of exact non-parametric inference, the corresponding exact Wilcoxon test yields the theoretical floor $p=0.0625$ (Supplementary Table~A10c). Against the joint boundary-forced router ($84{,}577{,}217\text{ kW}\cdot\text{h}$, $9.00\%$ violation), the independent classifier exhibits higher mean cost ($+1.96\text{M kW}\cdot\text{h}$), though its paired seed difference crosses zero ($[-8.18\text{M}, +12.71\text{M}]$, $p=0.757$).

This operational penalty occurs because discrete classification errors in independent models are decoupled from forecast residual magnitudes. Independent classifiers frequently misclassify regimes during steep wind-speed ramps where forecast residuals are largest, incurring disproportionately severe Newsvendor penalties. In contrast, joint representation models couple latent state awareness directly with spatio-temporal feature embeddings, ensuring that regime uncertainty is reflected in residual quantile sizing. This demonstrates that classification accuracy is not equivalent to reserve screening value.


## Result 6: MoE Mechanism Falsification (RQ3) \label{sec:modular-baseline}

Benchmarking capacity-matched neural architectures directly tests whether dynamic Mixture-of-Experts routing provides operational benefits over unrouted dense representations. Across all evaluated conditions, the hypothesis that dynamic expert routing is the source of reserve screening improvements is \textbf{falsified}:

\textit{1) Clean Telemetry:} At $h=1$, STGQ-Dense and STGQ-Routed achieve statistical parity ($690{,}614$ vs. $660{,}990\text{ kW}\cdot\text{h}$, ratio $1.045$; seed-paired difference $+29{,}624\text{ kW}\cdot\text{h}$, 95\% CI $[-53{,}774, +113{,}023]$, $p=0.380$). At $h=6$, the paired difference $+32{,}154\text{ kW}\cdot\text{h}$ likewise crosses zero ($[-1{,}148, +65{,}456]$, Table~\ref{tab:h6-paired}).

\textit{2) Multi-Horizon Seed Analysis:} In multi-horizon dispatch reserve-screening records across seeds 201--205 (\texttt{dense\_pricing\_by\_seed.csv}), the 5-seed mean surrogate cost for soft-gate-binning is $16.065\text{M kW}\cdot\text{h}$ compared to $16.076\text{M kW}\cdot\text{h}$ for soft-dense-binning (a difference of $< 0.07\%$). In fact, dense classification achieves lower surrogate cost than gated MoE in three out of five seeds (Seeds 203, 204, and 205).

\textit{3) Decoupled Modular Architecture:} STGQ-Modular (a decoupled architecture pairing frozen spatio-temporal representations with a dedicated residual quantile head) achieves $1{,}284{,}098 \pm 114{,}629\text{ kW}\cdot\text{h}$ and $9.7\% \pm 1.1\%$ violation under Delay-6 at $h=1$ (Table~\ref{tab:phase-scan}), matching or outperforming STGQ-Routed ($1{,}412{,}321\text{ kW}\cdot\text{h}$, $10.6\% \pm 1.1\%$).

\textbf{Point-Forecast Price of Operating-Regime Awareness:} In point forecasting, the boundary-aware model achieves an RMSE of $236.13 \pm 8.41$, compared with $224.34 \pm 2.23$ for iTransformer and $225.74 \pm 2.60$ for Graph WaveNet. This architecture \textbf{intentionally trades point-forecast RMSE}: it accepts a $+2.5\%$ whole-sample error margin to embed operating-regime awareness and mitigate severe tail shortfalls. Unconstrained models trigger $78.3\text{--}82.5\text{ MWh}$ of unhedged exposure, whereas boundary-aware representations restrict exposure to $53.9\text{ MWh}$ (a $31\%\text{--}35\%$ reduction).

These findings confirm that the operational benefit stems from consequence-based latent state representation and calibrated residual quantile estimation, not from dynamic expert specialization.


## Result 7: Deployment, Abstention, and Cross-Farm Boundaries \label{sec:cross-farm}

\textbf{Failure of Heuristic Selective Abstention:} Benchmarking selective decision abstention against random rejection and uniform reserve margin expansion (Supplementary Table~A10f) reveals that heuristic uncertainty scores ($U = \Delta r + 50 H(\pi)$) fail under multi-step latency: selective refusal at confidence threshold $c=0.90$ yields a fleet violation rate of $9.44\%$, which is statistically indistinguishable from random rejection ($9.50\%$, $p > 0.40$). In contrast, uniform reserve margin expansion achieves an $8.29\%$ violation rate while saving $37{,}823\text{ kW}\cdot\text{h}$, strictly Pareto-dominating heuristic refusal. Stale telemetry degrades both point forecasts and uncertainty estimators, showing that the tested heuristic uncertainty score does not reliably identify unsafe operating states under the evaluated prolonged-latency setting.

\textbf{External-Validity Boundary Probes and Local Retraining:} Table~\ref{tab:cross-farm} benchmarks pre-dispatch reserve screening performance across four commercial wind farms under local retraining. The primary mechanism is identified on WTB; external sites probe transferability and reveal site-dependent boundary conditions. Five random seeds quantify training stochasticity rather than independent physical replications. The three external European facilities must not be presented as uniform replication evidence: their observed effects are heterogeneous (Penmanshiel: positive; Kelmarsh: statistically neutral; LHB: negative overfitting boundary). 

\begin{table}[!htbp]
\centering
\fontsize{8.0pt}{8.9pt}\selectfont
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{0.92}
\caption{Site $\times$ Mechanism External Validity Boundary Probes across Four Commercial Wind Farms under Local Retraining (5 Seeds 201--205, $\rho=10$).}
\label{tab:cross-farm}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}l c c c c c@{}}
\toprule
Farm & Units & \shortstack{Phys.\\(kW$\cdot$h)} & \shortstack{Global\\(kW$\cdot$h)} & \shortstack{STGQ\\(kW$\cdot$h)} & \shortstack{$\Delta\text{PSREI}$ vs. Global\\95\% Bootstrap CI} \\
\midrule
\textbf{WTB} & 134 & 842k & 893k & 855k & $-$38k [$-$67k, $-$12k]$^{\ast}$ \\
\textbf{LHB} & 4 & 185k & 188k & 231k & +43k [$-$29k, +141k] \\
\textbf{Kelmarsh} & 6 & 1,025k & 1,065k & 1,025k & $-$40k [$-$204k, +172k] \\
\textbf{Penmanshiel} & 14 & 2,029k & 4,167k & 2,029k & $-$2.14M [$-$3.25M, $-$1.36M]$^{\ast}$ \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{8.8pt}\selectfont Note: $^{\ast}p < 0.05$. Penmanshiel comprises 14 operational turbines (site numbering spans WT01--WT15, with WT03 not installed/present in SCADA records). LHB exhibits local overfitting; Kelmarsh is neutral; WTB and Penmanshiel show significant reductions relative to the global quantile baseline under local retraining. Table~\ref{tab:cross-farm} compares STGQ against an unconditioned global quantile rather than matched external no-graph ablations, so external gains are not causally attributed to wake modeling alone. External sites probe transferability rather than uniform replication (see Supplementary Material Table~A8 for the complete Site $\times$ Mechanism specification).
\end{table}

Cross-site STGQ effects relative to the global quantile baseline are heterogeneous. The observed pattern is consistent with exploitable spatial redundancy as a possible moderator (not turbine count alone), while turbine count alone does not explain the variation: in facilities with deeper cluster layouts (WTB, Penmanshiel), STGQ achieves substantial reserve-screening surrogate reduction relative to the global quantile baseline ($\Delta\text{PSREI} = -38\text{k}$ and $-2.14\text{M kW}\cdot\text{h}$, both $p < 0.05$), although continuous physical quantile curves match or slightly edge STGQ ($842\text{k}$ and $2{,}029\text{k kW}\cdot\text{h}$). Conversely, on micro-arrays or sparse layouts (Kelmarsh, LHB), STGQ yields a neutral bootstrap difference on Kelmarsh ($-40\text{k kW}\cdot\text{h}$, 95\% CI crossing zero), while LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity ($+43\text{k kW}\cdot\text{h}$ penalty, $[-28.7\text{k}, +141.2\text{k}]$). Because Table~\ref{tab:cross-farm} compares STGQ against an unconditioned global baseline rather than a matched external no-graph ablation, these comparisons do not by themselves establish that spatial wake modeling causally drives external-site improvements. Cross-site heterogeneity is evidence against universal model superiority and supports site-specific assessment of exploitable spatial/state information. Furthermore, zero-shot cross-farm transfer exhibits pronounced directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$). These results support site-specific retraining or recalibration for the evaluated farms rather than assuming reliable zero-shot transfer.

\textbf{Point of Common Coupling (PCC) Portfolio Smoothing:} Aggregating turbine power flows at the PCC bus ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_t} P_{i,t}$, $\sim 121$ turbines) unlocks spatial diversification: turbulence cancels across the array, leaving boundary transitions as primary reserve risk. Diversification concentrates in transitional regimes (10\%--90\% pitching), saving $-1.33\text{M kW}\cdot\text{h}$ (CI $[-1.68\text{M}, -1.07\text{M}]$) over continuous physical pitch; longitudinal records (Kelmarsh, 9 years; Penmanshiel, 8.6 years) confirm operational recalibration under drift.



# Discussion: Minimum Sufficient Model Complexity \label{sec:discussion}

The empirical findings establish an operational principle of \textbf{Minimum Sufficient Model Complexity} governed by channel observability and telemetry freshness:

\textit{1) Physics under Fresh Telemetry:} Deterministic aerodynamic curves evaluate pristine telemetry ($\tau = 0$) with asymptotic power conservation ($\partial P / \partial v \propto v^2$ below rated speed, $P \equiv P_{\mathrm{rated}}$ above rated speed). Avoiding out-of-distribution neural variance, they achieve the lowest evaluated surrogate reserve screening cost within the boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events: $589.5\text{k}\text{--}881.4\text{k kW}\cdot\text{h}$, target-satisfying $\sim 6.8\%$ violation; Tables~\ref{tab:h6-benchmark} and~\ref{tab:phase-scan}), where deep representations are superfluous.

\textit{2) Recalibration under Observability:} Under observable latency ($10\text{--}30\text{ min}$), state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$) and maintains violation rates below the nominal 10\% target ($7.1\%\text{--}7.5\%$) without updating neural weights. Static recalibration breaks down only under contingency horizons ($\tau = 60\text{ min}$, Table~A11l, $13.8\%$ violation) as cubic extrapolation errors exceed static margins.

\textit{3) Learned Recovery under Pitch Withholding:} Decisive utility emerges when blade-pitch telemetry is withheld (\texttt{no\_pitch}), where physical rules inflate penalties to $1{,}378{,}900\text{ kW}\cdot\text{h}$. The spatio-temporal encoder reconstructs latent regimes from secondary consequence channels (active power divergence, electrical transients, spatial wake advection; $0.302\text{--}0.674$ NMI), saving $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$.

\textit{4) Posterior Decision Relevance and Baseline Bounds:} Posterior conditioning does not reduce plant-wide reserve procurement costs over strong wind-speed-binned quantiles ($\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). While direct wind-speed binning serves as the plant-wide and steady-state minimum sufficient policy ($+410{,}340\text{ kW}\cdot\text{h}$ steady advantage, $p=0.002$), the relative risk-cost trade-off becomes materially more favorable near operating transitions ($\pm 3$ steps): posterior conditioning selectively reduces violation ($7.24\%$ vs. $8.36\%$) and shortage exposure ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$), but this hedge remains more expensive under $\rho=10$ than wind-speed binning ($\Delta = +112{,}704\text{ kW}\cdot\text{h}$). The significant interaction contrast ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}123\text{ kW}\cdot\text{h}, p < 0.005$) establishes heterogeneity of the relative cost gap rather than a positive posterior cost advantage. A deployable hybrid policy remains statistically equivalent to wind-speed binning ($13.79\text{M}$ vs. $13.78\text{M kW}\cdot\text{h}$, $p > 0.40$) and must not be presented as an improvement. Crucially, dynamic MoE routing provides no measurable advantage over unrouted dense baselines (ratio $1.045$, $p=0.380$; seed delta $< 0.07\%$), while modular regression (STGQ-Modular) matches tail reliability ($9.7\%$ violation).

\textit{5) Industrial Deployment Guardrails:} (i) \emph{Spatial value}: cross-site STGQ effects relative to global quantiles are heterogeneous; the pattern is consistent with exploitable spatial redundancy as a possible moderator (not turbine count alone), while turbine count alone does not explain variation. STGQ reduces surrogate cost relative to global quantiles on WTB and Penmanshiel ($p < 0.05$), while LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity ($+43\text{k kW}\cdot\text{h}$ penalty); (ii) \emph{Local retraining}: directional transfer asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. $0.34$) supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer; (iii) \emph{Abstention limits}: selective refusal fails under latency ($p > 0.40$), favoring uniform margin expansion.

# Limitations

We delineate four foundational limitations of this study:

\textit{1) Synthetic Stress:} Impairments are evaluated under synthetic stress ($10\text{--}30\text{ min}$ backlogs, 60-min latency, Gilbert-Elliott dropouts); field units may exhibit sensor icing or individual pitch actions outside supervisory records.

\textit{2) Risk Surrogacy:} Evaluation operates at Level-1 pre-dispatch operating reserve screening via the PSREI newsvendor surrogate ($\rho=10$), abstracting Level-2 bulk transmission AC-OPF and balancing settlements.

\textit{3) Horizon Scope:} Benchmarks use a 35-day continuous test split across five random seeds (201--205), omitting multi-annual climatological cycles. Rated wind speeds vary by model ($12.5\text{ m/s}$ on MM92 vs. $14.5\text{ m/s}$ on MM82), requiring OEM calibration.

\textit{4) Deployment Boundaries:} Cross-site STGQ effects relative to the global quantile baseline remain heterogeneous, consistent with exploitable spatial redundancy as a possible moderator rather than turbine count alone; LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity ($+43\text{k kW}\cdot\text{h}$ penalty). Because Table~\ref{tab:cross-farm} lacks matched external no-graph controls, wake modeling is not causally isolated as the sole mechanism for external gains. Directional transfer asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$) supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer. The study assumes historical blade-pitch availability during offline training, followed by pitch withholding at deployment. Performance in settings where pitch was never recorded remains untested.

# Conclusion

This study repositions machine learning in reserve screening to a targeted conditional inference mechanism under telemetry degradation. First, under fresh telemetry, deterministic aerodynamic power curves minimize surrogate reserve penalties within the boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events: $589{,}535\text{ kW}\cdot\text{h}$ at $h=1$, $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, $\sim 6.8\%$ violation), collapsing only under unadapted latency ($24.0\%$ violation). Second, under observable delays, state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$). When blade pitch is withheld, learned representations infer latent regimes from secondary consequences, saving $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ and doubling transition recall ($0.416$ vs. $0.196$). Third, dynamic MoE routing confers no statistical advantage over unrouted architectures ($p=0.380$). Dispatch systems should deploy deterministic rules under clean telemetry, recalibration under observable drift, and learned representations when critical control states are unobservable.

# Declarations {.unnumbered}

\textbf{AI Use Statement:} The authors used OpenAI ChatGPT and Codex for drafting, formatting, and prose refinement, and for developing audit scripts. All scientific hypotheses, mathematical formulations, experimental designs, data processing, statistical analyses, findings, and final approval remain the sole responsibility of the authors.

\textbf{Code and Data Availability:} Raw SCADA datasets (WTB, ENGIE La Haute Borne, Kelmarsh, Penmanshiel) are public. Code, manifests, derived tables, and checkpoints are provided in the replication repository across declared seeds. The analysis involves no human subjects.
# References {.unnumbered}

::: {#refs}
:::
