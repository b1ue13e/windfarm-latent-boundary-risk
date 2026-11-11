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
  - \AtBeginDocument{\renewenvironment{CSLReferences}[2]{\par\addvspace{0.4ex}\begin{list}{}{\fontsize{7.8pt}{8.8pt}\selectfont\setlength{\itemindent}{0pt}\setlength{\leftmargin}{1.4em}\setlength{\parsep}{0pt}\setlength{\itemsep}{0.05ex}\setlength{\parskip}{0pt}}}{\end{list}}}
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

\title{Information Value and Decision Sufficiency under Degraded Wind-Turbine SCADA Telemetry}

\author{%
\IEEEauthorblockN{Junyu Li and Juntao Du\IEEEauthorrefmark{1}}
\IEEEauthorblockA{School of Statistics and Applied Mathematics,
Anhui University of Finance and Economics, Bengbu 233030, China\\
\IEEEauthorrefmark{1}Corresponding author: \texttt{dujuntao@aufe.edu.cn}}
}

\maketitle

\begin{abstract}
Reserve-risk screening requires evidence about decisions as well as operating-state recovery. We study incremental telemetry value and distinguish risk-constrained decision sufficiency from resource minimality under fixed arrived information. A controlled development study on 134 WTB turbines compares 22 input subsets, two direct quantile estimators and four nested training-row budgets under pitch withholding, with prespecified pressure comparisons in five additional information conditions. The common forecast and shortfall target are fixed across policies; representation metrics are not interpreted as decision-value evidence. Across 1,480 learned fits and five frozen seeds, every primary three-day condition/budget comparison contains risk-qualified policies, but none establishes two-percent near-optimality. At the predeclared five-percent sensitivity margin, current active/reactive power with histogram boosting is a sufficient candidate under pitch withholding at all four budgets. However, smaller alternatives remain unresolved: none of 420 declared decision cases identifies resource minimality. Historical state-recovery, physical-rule and recalibration diagnostics are reported separately and do not establish a deployment hierarchy or representation necessity. Independent source archives have been acquired, but held-out external model confirmation remains unexecuted. These results support bounded sufficiency assessment and explicit nonidentification rather than a certified minimum-model map.
\end{abstract}

\begin{IEEEkeywords}
Wind power reserve, SCADA telemetry degradation, latent operating boundary, state-conditional recalibration, conditional quantiles, resource minimality, consequence-based recovery.
\end{IEEEkeywords}



# Introduction

In bulk power system operations, real-time generation shortfalls incur severe asymmetric shortage penalties relative to surplus headroom; conventional symmetric metrics like root-mean-square error (RMSE) mask severe tail shortfall events that govern operating reserve adequacy in Level-1 pre-dispatch screening [@dowell2015veryshortterm; @kruse2023physics; @pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. This operational vulnerability concentrates near the aerodynamic demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3). Near rated inflow velocity, local power sensitivity transitions abruptly from a steep cubic trajectory ($\partial P / \partial v \propto v^2$) toward zero as pitch actuators shed aerodynamic lift [@slootweg2003general; @gaertner2020definition]. An operating-state change can alter the conditional shortfall distribution. Whether stale inputs or a particular rule implementation explain an observed violation increase must be tested separately; the boundary mechanism alone does not identify the cause.

This vulnerability is exacerbated by telemetry degradation in commercial Supervisory Control and Data Acquisition (SCADA) systems, including gateway serialization overhead, packet queuing backlogs, and intermittent cellular transmission jitter [@tautzweinert2017scada; @ullah2022enabling]. In operational archives (such as Kelmarsh), 99.6\% of discrete turbine status transitions occur between standard 10-minute polling boundaries. Furthermore, in third-party aggregator and Virtual Power Plant (VPP) triage, blade-pitch availability is treated here as an imposed evaluation condition; its commercial prevalence is not established. When delayed or missing measurements enter physical power equations, dispatch systems clear reserve margins against obsolete operating points. With pitch withheld, the control register is unavailable, but the evaluated valid regime labels remain separable by fresh wind speed; consequence-signal classification therefore tests redundant information rather than necessary latent-state recovery ($Z_t \to P_t, Q_t, \text{trajectory}$).

Aerodynamic curves and deep neural networks provide different candidate reserve-screening policies [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. Their information freshness and calibration conditions must be made explicit before comparing decision losses. Rather than asking which model achieves marginal predictive gains, bulk power system operations require answering a foundational engineering question:
\begin{equation}
\boxed{
\begin{gathered}
\text{Which arrived information is sufficient} \\
\text{for a low-resource reserve decision?}
\end{gathered}
}
\label{eq:core-question}
\end{equation}

We separate three questions: $\text{Observability} \to \text{Recoverability} \to \text{Decision Sufficiency}$. A state score computed from available measurements supplies no new contemporaneous sensor information conditional on its fitted parameters; its potential advantage concerns estimation or representation and requires a same-information decision comparison. The 134-turbine WTB benchmark provides development evidence, while existing European transfer results retain their separately bounded scope. Graph and mixture-of-experts formulations are implementation comparators, with no established routing necessity. The paper makes three bounded contributions:

1. **Decision-information assessment:** We compare declared input subsets and direct estimators under a common arrived-information clock, forecast commitment, finite-target population and asymmetric loss. Nested row budgets help expose estimator and training-budget sensitivity; they do not add independent weather days.
2. **Sufficiency with a minimality check:** We distinguish passing joint risk/cost requirements from proving every lower-resource alternative inadequate. Both the historical-choice family and a secondary fixed-q capability grid may return no identified policy. These are finite-family, tolerance-dependent assessments, not universal ranking laws.
3. **A bounded empirical finding:** Low-resource candidates can satisfy a five-percent development criterion without establishing the two-percent criterion or minimum resource requirements. Historical recovery and recalibration results are retained as diagnostics. External source qualification is a prerequisite for a future frozen confirmation, not evidence that confirmation has succeeded.


# Related Work

## From Average Wind-Power Accuracy to Transition-Window Risk

Spatio-temporal graph neural networks (STGNNs) advance multi-step wind plant forecasting by modeling spatial cross-correlations and wake advection [@daenens2025offshore; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn], with physics-informed extensions incorporating wake and boundary constraints [@park2019physicsinduced; @kim2024lidarscada; @zehtabiyan2023physicsguided]. While these architectures reduce plant-wide $L_2$ error, continuous trajectory minimization obscures discrete turbine operating state transitions between MPPT (Region 2) and pitch regulation (Region 3) that govern reserve-screening adequacy [@bossanyi2000closedloop; @bianchi2006windcontrol; @pao2011controlwind].

Recent physics-aware dynamic-graph mixture-of-experts (MoE) architectures, such as that of Zhao et al. [@zhao2026physicsaware], test whether coupling spatial learning, physical guidance, and expert routing improves point forecasting accuracy. Rather than iterating on forecasting network topologies, our formulation isolates the upstream information-and-decision problem: when critical aerodynamic states become unobservable due to telemetry degradation, what regime information remains recoverable from secondary consequence channels, when non-neural conditional recalibration suffices without parameter updates, and whether the recovered latent state alters asymmetric reserve-shortfall decisions. Probabilistic forecasts translate predictive uncertainty into reserve allocation [@dowell2015veryshortterm; @kruse2023physics; @bremnes2004quantile]. We address this operational triage problem: screening aerodynamic transition risks under degraded SCADA telemetry prior to market clearing, functioning strictly as a Level-1 pre-dispatch proxy while abstracting downstream transmission constraints.



# Problem Formulation and Latent Operating-Boundary Framework

## Level-1 Pre-Dispatch Risk Screening and Asymmetric Decision Problem (PSREI)

Operating reserve screening functions as a pre-dispatch risk assessment mechanism to mitigate costly real-time generation imbalances [@bremnes2004quantile; @nielsen2006quantile].

\textbf{Hierarchical grid dispatch interface:} Our formulation is strictly bounded to Level 1 pre-dispatch operating reserve screening proxies at the plant EMS or aggregator terminal, abstracting Level 2 bulk transmission AC-OPF and wholesale balancing settlements.

\textbf{Penalized Reserve-Shortfall Energy Index (PSREI):} Let $\hat{y}^{\mathrm{fixed}}_{i,t}$ be the canonical scheduled point forecast, frozen before reserve-policy evaluation and shared across all compared policies, and let $y_{i,t}$ be realized generation. Shortfall is $s_{i,t} = \max(\hat{y}^{\mathrm{fixed}}_{i,t} - y_{i,t}, 0)$. For upward reserve $r_b$ and dimensionless penalty-to-procurement ratio $\rho \equiv c_u / c_r$ (balancing marginal unserved shortage penalty $c_u$ against marginal reserve capacity cost $c_r$), the \textbf{Penalized Reserve-Shortfall Energy Index (PSREI)} in $\text{kW}\cdot\text{h}$ is:
\begin{equation}
C(r_b; \rho) = \sum_{(i,t)} \left[ r_b(i,t) + \rho \max\left(\hat{y}^{\mathrm{fixed}}_{i,t} - y_{i,t} - r_b(i,t), \, 0\right) \right]\Delta t.
\label{eq:psrei}
\end{equation}
Differentiating $\mathbb{E}[C(r_b; \rho)]$ yields the first-order condition $\partial \mathbb{E}[C]/\partial r_b = 1 - \rho \Pr[s_{i,t} > r_b] = 0$, giving the Newsvendor critical fractile $q^*(\rho) = 1 - 1/\rho$ [@dowell2015veryshortterm]. For $\rho=10$, $q^* = 0.90$, establishing a nominal 10\% violation target.

\textbf{Loss geometry and pinball quantile head:} Point forecasting minimizes symmetric $L_2$ loss converging to conditional mean $\mathbb{E}[y \mid \mathbf{x}]$, which departs from upper quantiles in asymmetric operations ($\rho=10$). Upward reserve margin $\hat{r}_{i,t}$ covering the frozen shortfall target $s_{i,t} = \max(\hat{y}^{\mathrm{fixed}}_{i,t} - y_{i,t}, 0)$ is estimated via pinball loss:
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
The evaluated label construction uses the fixed thresholds stored in the canonical cache metadata: $u_{\mathrm{idle}}=3.0\text{ m/s}$, $u_{\mathrm{rated}}=10.5\text{ m/s}$ and $p_{\mathrm{th}}=2.0^\circ$ for WTB and the inspected external caches. These are operational label definitions in this experiment, not independently verified manufacturer-specific thresholds. Supervised alignment excludes ambiguous class $Z=3$.

Under pristine telemetry, $\bar{p}_{i,t}$ and $w_{i,t}$ are known, so $Z_{i,t}$ is directly observable. Under transmission latency $\tau > 0$ or when blade-pitch registers are withheld across aggregator interfaces, the control register itself ceases to be accessible at deployment, while its dynamical electromechanical consequences ($Z_t \to P_t, Q_t, \text{trajectory}$) remain partially preserved in arrived SCADA feeds. However, withholding pitch does not make the evaluated discrete labels unidentifiable: conditional on the declared validity mask, fresh wind-speed intervals separate all three valid classes. Ambiguous excluded cells are outside this result. The representation is consequently a supervised surrogate, not evidence of discovering a hidden physical state. The central inferential object is the soft operating-boundary posterior:
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

\textbf{Physical dynamic wake graph \& encoder:} For WTB, time-varying directed wake graphs $\mathcal{A}_t$ link turbine pairs within aerodynamic wake cones ($\alpha = 25^\circ$) weighted by streamwise and cross-stream decay [@park2019physicsinduced; @zehtabiyan2023physicsguided]. A directed-diffusion GRU encoder within a 110,012-parameter forecasting model aggregates messages via:
\begin{equation}
\begin{aligned}
\mathbf{X}^{(\ell+1)}_{t} = \mathrm{LN}\Big(&\mathbf{W}_{\mathrm{self}}^{(\ell)}\mathbf{X}^{(\ell)}_{t} +\mathbf{W}_{\mathrm{in}}^{(\ell)}\mathrm{Agg}_{\mathrm{in}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) \\
&+\mathbf{W}_{\mathrm{out}}^{(\ell)}\mathrm{Agg}_{\mathrm{out}}(\mathbf{X}^{(\ell)}_{t},\mathcal{A}_t) +\mathbf{R}^{(\ell)}\mathbf{X}^{(\ell)}_{t}\Big),
\end{aligned}
\label{eq:diffusion}
\end{equation}
and extracts node-level representations $\mathbf{h}_{i,t}$. When blade pitch $\bar{p}_{i,t}$ is withheld, the encoder estimates the declared regime posterior $p(Z_{i,t} \mid \mathbf{X}_{\le t})$ from secondary consequence channels: active power transients ($\texttt{Patv}_{i,t}$), electrical responses, and dynamic wake advection, strictly excluding $\texttt{Pab\_mean}_{i,t}$.


The primary wind-speed-versus-posterior comparison uses the 87,067-parameter dense-classifier variant, whereas external transfer uses the 110,012-parameter MoE variant. The unrouted dense forecasting control has115,240 parameters and is approximately, not exactly, capacity matched. The channel ablation is a separate MLP probe using latest, mean, standard deviation and maximum history features. It is not an intervention on the full spatio-temporal encoder. The strong-baseline decision comparison freezes the point forecast, calibrates five posterior-probability bins or ten wind-speed bins on validation shortfalls, and evaluates their 0.90 quantiles on identical test targets. Those comparisons must not be described as one end-to-end quantile network.

## Reserve-Tail Estimation and Residual Quantile Sizing

To study balancing exposure, reserve margins target the asymmetric shortfall distribution rather than symmetric point forecasts, separating: (1) posterior operating-state inference $\pi_{i,t}^{\mathrm{pitch}} = p(Z_{i,t} = 2 \mid \mathbf{X}_{\le t})$; (2) scheduled point forecasting $\hat{\mathbf{y}}_{i,t+1:t+P}$; and (3) reserve-tail quantile sizing $\hat{r}_{i,t} = Q_{0.90}(s_{i,t} \mid \mathbf{X}_{\le t})$.

One historical uncalibrated neural pinball recipe exhibits tail conservatism (>1.6M kW reserve, <1.2\% violation, Table \ref{tab:h6-benchmark}). The evaluated residual formulation decouples estimation: point trajectories $\hat{\mathbf{y}}$ anchor nominal expectations, while upward reserve margins $\hat{r}_{i,t}$ are estimated conditionally on forecast residuals:
\begin{equation}
\begin{aligned}
\hat{r}_{i,t} = \mathrm{MLP}_{\mathrm{res}}([\mathbf{h}_{i,t}; \, \mathbf{x}_{\mathrm{anchor}}]), \\
\text{minimized under } \mathcal{L}_{q^*}(s_{i,t}, \hat{r}_{i,t}),
\end{aligned}
\label{eq:residual-quantile}
\end{equation}
or binned empirically over held-out validation residuals conditioned on latent posterior $\pi_{i,t}^{\mathrm{pitch}}$.

## Risk-Constrained Sufficiency and Resource Minimality

The phrase ``minimum sufficient'' is used here as a conditional, risk-constrained model-selection criterion rather than a universal ranking law. Let $\mathcal{M}(\mathcal{I}_t^{(d)})$ be the admissible reserve policies measurable with respect to the arrived information set, and let $b_{\mathcal{I}}$ be the strongest pre-registered direct conditional baseline under that same information set. With the canonical frozen point forecast $\hat{y}^{\mathrm{fixed}}$ and common shortfall target $s_t=\max(\hat{y}^{\mathrm{fixed}}_t-y_t,0)$, define $C_P(m)$ as fixed-target PSREI and $V_P(m)$ as the violation rate on population $P$. For pre-registered $\alpha$, cost tolerance $\epsilon_C$, violation tolerance $\epsilon_V$, absolute violation cap $v_{\max}$, and complexity preorder $\operatorname{Complexity}(m)$, select

\begin{equation}
\begin{gathered}
m^*=\arg\min_{m\in\mathcal{M}(\mathcal{I})} \operatorname{Complexity}(m)\\
\text{subject to}\\
\begin{aligned}
U_{1-\alpha}[C_P(m)-C_P(b_{\mathcal{I}})]&\le\epsilon_C,\\
U_{1-\alpha}[V_P(m)-V_P(b_{\mathcal{I}})]&\le\epsilon_V,\\
U_{1-\alpha}[V_P(m)]&\le v_{\max}.
\end{aligned}
\end{gathered}
\label{eq:conditional-min-sufficient}
\end{equation}

Here $U_{1-\alpha}$ is the one-sided UCB under the registered seed/block unit. E04 froze $\alpha=0.05$, $\epsilon_C=\epsilon_V=0$, $v_{\max}=0.10$, and $q^*=0.90$. On WTB Full, all four B/C/D/D10 policies exceeded the absolute violation UCB cap and the selector returned ``no feasible policy.'' B/C/D/D10 denote wind-speed bins, posterior quantiles and two hybrid policies, not an architecture ranking. No model is certified minimum-sufficient or safe for deployment; tolerances remain unchanged. The conditional rule is falsifiable, not a universal law. E07 remains inactive. Selecting the lowest-resource policy among those passing upper-bound gates establishes only the lowest-resource qualified candidate. A claim of finite-family minimality additionally requires ruling out every strictly smaller candidate, using a risk lower bound above the cap or a cost-ratio lower bound beyond the declared margin relative to a risk-qualified witness. Failure to qualify a smaller candidate is not evidence that it is inadequate.


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

Fig. 1 separates information regimes and their unresolved decision tests; it is not an operational dispatch gate.

\begin{figure}[t]
\centering
\fbox{\parbox{0.92\columnwidth}{\small\raggedright
\textbf{Arrived information $\mathcal{I}_t$}\\[2pt]
Fresh wind and pitch $\longrightarrow$ evaluate physical rules.\\[2pt]
Observable delayed channels $\longrightarrow$ evaluate historical recalibration.\\[2pt]
Pitch withheld $\longrightarrow$ test consequence information against direct local quantiles.\\[2pt]
\textbf{For every candidate:} matched frozen targets, paired uncertainty and the absolute risk cap.\\[2pt]
\textbf{E04: no feasible policy. E07: inactive.}
}}
\caption{Conceptual information and evidence checks. Candidate families are hypotheses for comparison; the diagram neither certifies a deployment route nor converts regime recoverability into decision value.}
\label{fig:decision-boundaries}
\end{figure}


## Pre-Dispatch Risk Screening Framework and Resampling Hierarchy

The declared backbone recipe uses AdamW, validation-RMSE stopping, clipping and training mixed precision across seeds 201--205; auxiliary probes and quantile heads have distinct budgets. This recipe does not bind every historical execution environment or establish evaluation precision. Validation calibration precedes the declared test replay; complete historical input and execution binding remains unverified. Uncertainty is experiment-specific: earlier diagnostics report 1,000 paired block-bootstrap draws, whereas E04/E05 follow their own registered resampling. The 35 native test blocks start from the first issue anchor at 144-step intervals, not calendar-day boundaries. Five seeds measure initialization variation, not independent farms or test periods.



# Empirical Findings: Minimum Sufficient Modeling Across Observability Regimes

## Regime 1: Fresh Observable Telemetry $\to$ Deterministic Aerodynamics and Operational Breakdown Boundaries (RQ1)

Table \ref{tab:h6-benchmark} summarizes the multi-day replay dispatch benchmark for 1-hour ahead operational dispatch ($h=6$) evaluated on the boundary-active operating slice ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations across 134 turbines over the 35-day test split) under nominal clean telemetry. Table \ref{tab:h6-paired} reports seed-paired hypothesis tests and mechanism ablations across operational regimes, along with 95\% confidence intervals from a paired daily cluster bootstrap over the 35 observed test days (1,000 resamples).

\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{0.90}
\caption{Cross-Seed Multi-Regime Pre-Dispatch Reserve Screening Benchmark on Boundary-Active Operating Regimes under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Boundary-Band Events ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations, 35 Test Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data. Commensurate plant-wide full-population baselines ($N=408{,}939$ cells) range from $14.0\text{M}$ to $16.5\text{M kW}\cdot\text{h}$ (see text and Metric-Scope Registry).}
\label{tab:h6-benchmark}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccccc@{}}
\toprule
Regime & Evaluated Model & \shortstack{Penalized Reserve\\Energy (kW$\cdot$h)} & \shortstack{Violation\\Rate} & \shortstack{Reserve Energy\\(kW$\cdot$h)} & \shortstack{Shortage Energy\\(kW$\cdot$h)} & \shortstack{Pinball\\Loss} \\
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
\raggedright\fontsize{8.0pt}{8.8pt}\selectfont Note: 95\% CIs from paired daily cluster bootstrap over 35 observed test days (144 steps/cluster, 1,000 Monte Carlo resamples). $^{\ast\ast}p<0.01, ^{\ast}p<0.05$. $^{\dagger}$Physical rule breaches nominal 10\% violation target ($12.20\%$). The reported test does not establish a dynamic MoE routing advantage ($p=0.380$); it does not prove equivalence or absence of any advantage.
\end{table}

The historical boundary-band evaluation reports favorable point costs for deterministic aerodynamics under fresh telemetry; it does not establish selector-certified operational sufficiency. Under pristine telemetry ($\tau = 0$), Continuous Physical Quantile achieves the lowest surrogate reserve screening cost within the active boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cell observations) among all evaluated methods ($589{,}535 \pm 77{,}390\text{ kW}\cdot\text{h}$ at immediate dispatch $h=1$ and $881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with observed $\sim 6.8\%$ violation). It outperforms both unrouted dense networks (STGQ-Dense: $991{,}181\text{ kW}\cdot\text{h}$) and dynamically routed architectures (STGQ-Routed: $959{,}027\text{ kW}\cdot\text{h}$) by $8.1\%\text{--}11.1\%$. As confirmed in Table \ref{tab:h6-paired}, Continuous Physical Quantile achieves a $-77{,}659\text{ kW}\cdot\text{h}$ advantage over neural representations, with a 95\% daily cluster bootstrap confidence interval (1,000 paired resamples over 35 observed days) strictly excluding zero ($[-106{,}175, -49{,}143]$). When inflow wind speed and blade pitch angle are fresh and directly observable, deterministic aerodynamic equations yield the lowest evaluated surrogate reserve screening cost. This historical contrast does not by itself attribute the difference to neural variance or establish that a representation is unnecessary under other information conditions.

Table \ref{tab:h6-benchmark} reports a historical sensitivity to stale inputs. The following cubic explanation is illustrative and does not isolate the implementation-level cause of the reported violations; empirical rule construction and any rated-power truncation require separate checks. Transmission delays of 10--30 minutes introduce latency drift between true inflow and evaluated registers. Under a 60-minute latency contingency stress test (Delay-6), which serves as an asymptotic reliability breakdown stress endpoint rather than an industrial prevalence claim, physical equations evaluate stale state tuples $(v_{t-\tau}, \beta_{t-\tau})$. Near rated wind speed, the localized slope discontinuity (\ref{eq:sensitivity-cliff}) amplifies delayed-inflow errors: turbines that have crossed into active blade-pitch regulation ($Z_t = 2$) are evaluated with obsolete fine pitch ($\beta_{t-\tau} \approx 0^\circ$), illustrating an unadapted cubic extrapolation along the trajectory (\ref{eq:stale-phys}). Unadapted physical quantile violation rates surge from $6.81\%$ to $24.02\% \pm 1.69\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$ ($1{,}136{,}466\text{ kW}\cdot\text{h}$), breaching the nominal 10\% Newsvendor target ($q^* = 0.90$) and leaving $127.55\text{ MWh}$ of unhedged generation shortfall across the array.


## Regime 2: Stale but Observable Telemetry $\to$ Non-Neural Recalibration Absorbs Drift (RQ2)

When telemetry channels remain observable under transmission delays, condition-matched state-conditional recalibration (\ref{eq:recalib}) adjusts quantile margins using held-out validation residuals undergoing the identical delay. As shown in Table \ref{tab:phase-scan}, state-conditional recalibration absorbs $36.3\%$ of within-condition shortage loss at $\tau = 10\text{ min}$ ($37.7 \to 24.0\text{ MWh}$), $53.9\%$ at $\tau = 20\text{ min}$ ($51.8 \to 23.9\text{ MWh}$), and $61.7\%$ at $\tau = 30\text{ min}$ ($69.1 \to 26.4\text{ MWh}$), holding fleet violation at $7.1\%$--$7.5\%$ and a surrogate reserve cost of $1{,}228{,}609\text{ kW}\cdot\text{h}$ at the $h=1$ contingency endpoint. The historical scan reports the following point contrast for recalibrated physical curves and neural models (STGQ-Routed: $1{,}274{,}047\text{ kW}\cdot\text{h}$; STGQ-Modular: $1{,}283{,}855\text{ kW}\cdot\text{h}$).

\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{4.0pt}
\renewcommand{\arraystretch}{0.90}
\caption{Historical diagnostic scan across telemetry latency $\tau \in [0, 60]\text{ min}$ and pitch observability on boundary-active regimes ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cells, $h=1$, 5-seed mean on WTB; nominal $\tau=0$ baseline $593{,}258\text{ kW}\cdot\text{h}$ aligns within $0.6\%$ of the primary frozen $589{,}535\text{ kW}\cdot\text{h}$ boundary benchmark). Penalized reserve energy in kW$\cdot$h ($\rho=10$).}
\label{tab:phase-scan}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}ccccccc@{}}
\toprule
$\tau$ (min) & Pitch & \shortstack{Clean Phys.\\Metric (Viol.)} & \shortstack{Recal. Phys.\\Metric (Viol.)} & \shortstack{STGQ-Mod.\\Metric (Viol.)} & \shortstack{STGQ-Rout.\\Metric (Viol.)} & \shortstack{Operational\\Regime} \\
\midrule
0 & All & $\mathbf{593{,}258}$ ($7.3\%$) & $\mathbf{593{,}258}$ ($7.3\%$) & $663{,}347$ ($6.1\%$) & $663{,}915$ ($7.3\%$) & Historical diagnostic \\
0 & None & $961{,}024$ ($3.2\%$) & $824{,}393$ ($5.4\%$) & $\mathbf{755{,}794}$ ($5.8\%$) & $756{,}257$ ($6.4\%$) & Historical diagnostic \\
\midrule
10 & All & $753{,}606$ ($11.2\%^{\dagger}$) & $\mathbf{742{,}211}$ ($7.4\%$) & $786{,}366$ ($6.7\%$) & $789{,}094$ ($7.6\%$) & Historical diagnostic \\
10 & None & $1{,}008{,}743$ ($4.8\%$) & $928{,}028$ ($6.2\%$) & $\mathbf{866{,}753}$ ($6.1\%$) & $874{,}156$ ($6.6\%$) & Historical diagnostic \\
\midrule
20 & All & $896{,}198$ ($14.0\%^{\dagger}$) & $\mathbf{841{,}734}$ ($7.1\%$) & $875{,}838$ ($7.4\%$) & $879{,}750$ ($8.0\%$) & Historical diagnostic \\
20 & None & $1{,}062{,}646$ ($6.1\%$) & $1{,}010{,}530$ ($6.2\%$) & $\mathbf{947{,}869}$ ($6.7\%$) & $959{,}934$ ($7.1\%$) & Historical diagnostic \\
\midrule
30 & All & $1{,}069{,}266$ ($16.6\%^{\dagger}$) & $\mathbf{939{,}190}$ ($7.5\%$) & $987{,}760$ ($7.1\%$) & $990{,}091$ ($7.6\%$) & Historical diagnostic \\
30 & None & $1{,}138{,}774$ ($7.5\%$) & $1{,}101{,}292$ ($6.7\%$) & $\mathbf{1{,}054{,}592}$ ($6.4\%$) & $1{,}064{,}238$ ($6.7\%$) & Historical diagnostic \\
\midrule
60 & All & $1{,}656{,}285$ ($24.0\%^{\dagger}$) & $\mathbf{1{,}228{,}609}$ ($9.5\%$) & $1{,}283{,}855$ ($9.6\%$) & $1{,}274{,}047$ ($9.6\%$) & Historical diagnostic \\
60 & None & $1{,}437{,}280$ ($11.8\%^{\dagger}$) & $1{,}378{,}900$ ($9.0\%$) & $\mathbf{1{,}330{,}318}$ ($8.7\%$) & $1{,}331{,}840$ ($8.8\%$) & Historical diagnostic \\
\bottomrule
\multicolumn{7}{@{}p{\textwidth}@{}}{\fontsize{8.0pt}{9.0pt}\selectfont $^{\dagger}$Exceeds nominal 10\% violation target ($q^*=0.90$). Bold reproduces the original descriptive point metric; neither boldface nor a point violation below ten percent certifies sufficiency. Cross-model targets and cross-delay populations differ in this historical scan. Under $\tau=60\text{ min}$, target satisfaction is $3/5$ seeds ($60\%$) across models.}
\end{tabular*}
\end{table*}

A historical mismatched calibration matrix across test latencies $\tau_{\mathrm{test}} \in [0, 60]\text{ min}$ and calibration horizons $\tau_{\mathrm{cal}} \in [0, 60]\text{ min}$ describes the evaluated sensitivity to calibration mismatch; it does not establish a general operational boundary. Recalibrating at $\tau_{\mathrm{cal}} = 10\text{ min}$ withstands latency drift up to $\tau_{\mathrm{test}} = 20\text{ min}$ while maintaining target-satisfying tail coverage ($8.2\%\text{--}9.1\%$ violation), but breaks down when staleness surges to $\tau_{\mathrm{test}} = 60\text{ min}$ ($13.8\%$ violation). Within the corresponding observable-channel diagnostic, state-conditional recalibration recovers $36.3\%$--$66.5\%$ of the observed shortage loss across the evaluated latency grid ($127.6 \to 42.8\text{ MWh}$ at the $60$-min contingency endpoint, a $66.5\%$ absorption at $9.5\%$ violation) without updating network weights.


The historical delay scan uses condition-specific forecasts and an arrival-wind-selected boundary population. Its clean-versus-recalibrated physics comparison shares targets and masks within a condition, but comparisons across delays mix forecast and population changes. Older dense/MoE phase-scan costs also used different shortfall targets. Those fixed-target/fixed-population interpretations are withdrawn. The corrected replay freezes canonical shortfalls and physical-time boundary cells across methods and conditions, and retains a ten-bin wind-speed comparator.

## Regime 3: Pitch Withheld: Information Sufficiency $\to$ Consequence-Based State Recovery and Decision Boundaries (RQ2) \label{sec:withheld-channel}

The role of consequence-based state recovery is examined when blade-pitch telemetry is withheld across aggregator boundaries (\texttt{no\_pitch}, Table \ref{tab:phase-scan}). Under pitch unobservability, physical rules and recalibration schemes lose direct state awareness, inflating recalibrated screening penalties from $824{,}393\text{ kW}\cdot\text{h}$ at $\tau=0$ to $1{,}378{,}900\text{ kW}\cdot\text{h}$ at $\tau=60\text{ min}$.

Under this regime, the control register is unobservable at deployment, while its electromechanical consequences ($Z_t \to P_t, Q_t, \text{trajectory}$) remain partially recorded in arrived SCADA feeds. Learned representations (STGQ-Modular) reconstruct operating states from secondary consequences under \textbf{offline privileged supervision}.

We provide an explicit disclosure that pitch is available in training inputs but \mbox{withheld} in validation/test deployment: blade-pitch registers ($\beta$) were present in historical training buffers ($x_{\text{hist}}$ channels 7--8) and anchor physics, while pitch was strictly zero-masked and withheld during validation and testing. Trained using historically available pitch information that is withheld at deployment, offline privileged supervision improves latent-state organization and reduces representation collapse, while matched ablations do not establish an independent downstream reserve-cost gain (paired difference $\Delta \text{PSREI} = -312\text{k} \pm 1{,}086\text{k kW}\cdot\text{h}$, 95% bootstrap CI $[-1.31\text{M}, +0.34\text{M}]$, crossing zero).

Empirical consequence-channel identifiability audits disentangle the recovery mechanism: contemporaneous active power is the strongest evaluated predictor ($\text{AUROC} = 0.988$), while lagged trajectories and non-power consequence channels retain partial additional state information, and thermal channels contribute negligible high-frequency boundary information for 10-minute dispatch.

As detailed in Table \ref{tab:phase-scan}, STGQ-Modular achieves $755{,}794\text{ kW}\cdot\text{h}$ at $\tau=0$ (an $8.3\%$ saving of $68{,}599\text{ kW}\cdot\text{h}$ over recalibrated physics) and maintains the reported reserve-screening comparison against condition-matched recalibrated physics as a historical diagnostic only; no transition diagnostic is used as current decision evidence.

\textbf{Separation of Information Recoverability and Decision Value:} State recoverability does not imply universal decision superiority. Operational validation separates three distinct claims: (i) \textit{Operating-state discrimination} (AUROC $> 0.94$, NMI $0.461$, ARI $0.647$); (ii) \textit{Probabilistic calibration of $P(Z \mid \mathcal{I}_t^{(d)})$} (bulk ECE $\le 3.46\%$, satisfying the $5\%$ screening gate; tail $\text{MCE} \approx 0.75\text{--}0.85$); and (iii) \textit{Reserve-decision value}. Against a strong observable wind-speed-conditioned quantile baseline (10 bins, $13.78\text{M kW}\cdot\text{h}$ plant-wide), posterior conditioning does not reduce plant-wide reserve screening costs (latest imported candidate $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +445{,}639\text{ kW}\cdot\text{h}$; pending deep audit). The latest candidate does not certify a separate steady-state superiority or transition-localized heterogeneity claim; the prior slice-specific estimates are historical pending re-audit. Thus, strong wind-speed-conditioned quantiles remain lower-cost plant-wide.

The latest candidate reports a transition-slice penalty of $+71{,}204\text{ kW}\cdot\text{h}$ relative to site-local wind-speed bins. The imported transition-versus-steady interaction is $-303{,}232\text{ kW}\cdot\text{h}$ with 95\% interval $[-597{,}953, +19{,}013]\text{ kW}\cdot\text{h}$, crossing zero. These values are pending deep audit and do not establish transition-localized decision superiority.

The historical matched-budget frontier is retained as a diagnostic artifact but is not used as current claim evidence while the imported strong-baseline candidate undergoes deep audit. Its prior transition-localized allocation interpretation is therefore treated as pending rather than decisive.

Dynamic Newsvendor re-optimization across $\rho \in [5, 100]$ (Fig. \ref{fig:rho-sensitivity}) exhibits no economic crossover, as high conditional tail variance forces severe reserve over-procurement ($+1.10\text{M kWh}$ at $\rho=100$). Recovering the latent boundary does not establish reserve-allocation superiority over strong observable wind-speed conditioning.


\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,keepaspectratio]{figures/matched_budget_transition_frontier.pdf}
\caption{Historical matched-budget frontier diagnostic in transition windows. The artifact is retained for provenance, but its prior allocation interpretation is not used as current claim evidence while the imported strong-baseline candidate undergoes deep audit.}
\label{fig:matched-budget}
\end{figure}

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,keepaspectratio]{figures/matched_budget_control_slices.pdf}
\caption{Re-optimized penalty-ratio sensitivity ($\rho \in [2, 100]$). In transition windows, baseline dominance widens from $+22.4$k kWh ($\rho=5$) to $+998.2$k kWh ($\rho=100$). Plant-wide, baseline is preferred across the entire evaluated range. Posterior advantage at $\rho=2$ (transition only) vanishes for all $\rho \ge 5$.}
\label{fig:rho-sensitivity}
\end{figure}

## Supporting Evidence and Falsification of Alternative Explanations (RQ3) \label{sec:modular-baseline}

Historical modular diagnostics report $9.7\%$ violation and no detected advantage of heuristic abstention over uniform margin expansion ($p > 0.40$). These point metrics do not certify the risk cap, causal attribution to joint learning or routing equivalence under common frozen targets. Classification accuracy alone does not establish reserve decision value.

External decision-value conclusions from the retrospective EXP-01 v4 calculation are withdrawn because its forecasts and targets came from physical windows shifted by 120 days (Kelmarsh) or 720 days (Penmanshiel). The corrected-v2 benchmark is superseded and not reinstated as the current matched-decision result. The current bounded evidence is the deterministic_matched_transfer_v1 branch: at $h=6$, the posterior-minus-local-wind-bin PSREI deltas are $+6.3\text{k kW}\cdot\text{h}$ for Kelmarsh (interval crossing zero) and $+356.0\text{k kW}\cdot\text{h}$ for Penmanshiel. This branch uses existing weights and local frozen forecasts/calibration, does not certify complete raw retraining, and does not close the full EXP-01 claim.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,keepaspectratio]{figures/figure5_case_studies.pdf}
\caption{Case-study view of the WTB local control-boundary switch window and the ERA5 weekly thermodynamic positive control. Panel A shows a WTB MPPT-to-pitch transition window (ground-truth active power, dense and boundary-forced router predictions, driving wind speed and pitch, and dominant-expert assignment); Panel B shows ERA5 mean surface sensible heat flux against weekly expert gate weights. This figure illustrates mechanism behavior on the primary site and does not compare cross-site reserve costs; the external-site comparisons are reported numerically in the text and in the supplementary site ledger.}
\label{fig:case-studies}
\end{figure}




## Controlled Information-Subset Development Study

A separate controlled task tests input reduction without replacing the historical canonical experiment. A common synthetic forecast uses wind/power through six ten-minute steps before reserve issue and targets power six steps after issue. Its nominal publication clock assumes fresh upstream forecaster inputs; imposed delays concern reserve-layer telemetry, not an end-to-end delayed forecasting system. The policy-fit, offset-fit, selection and evaluation periods are WTB days 136--175, 176--192, 193--210 and 211--245, with target plus one-step release maturity exclusions. All finite future-power targets are retained, including zero/negative net export; no pitch or operating-state filter changes the population.

Under pitch withholding, the input grid contains common forecast/clock/turbine-ID features alone and all seven nonempty wind/active/reactive subsets crossed with 1/6/36 last-arrived readings. Five additional information conditions use six fixed subsets as pressure tests. Preset HGB and direct pinball MLP estimators use five seeds and shared nested prefixes of 10k/40k/120k/360k historical rows; pressure tests use 120k/360k. All learn the nominal0.90 quantile. Five prespecified signed-offset levels are fitted before selection, one q is chosen per candidate across all seeds, and the candidates remain frozen during evaluation. Model-family identification is a retrospective development assessment, not an ex-ante architecture choice.

The shared-day maximum-standardized bootstrap uses 20,000 draws, a primary three-day span and one-/seven-day sensitivities. Each span jointly covers 252,500 instance-risk and paired mean-cost-ratio coordinates. Every one of the 28 primary-span condition/budget/analysis cases contains risk-qualified candidates, but none satisfies the two-percent near-optimality criterion. At the predeclared five-percent sensitivity margin, the historical-choice family identifies PQ1/HGB under pitch withholding at all four budgets (Table\ref{tab:subset-candidate}). This result does not establish minimality: the cost-ratio lower bounds and risk lower bounds cannot exclude all smaller alternatives. Across 420 declared decision cases, 367 have no sufficient candidate and 53 have unresolved smaller policies; none identifies a finite-family minimum. These cases share data and are not independent replications.

\begin{table}[t]
\centering
\caption{Pitch-withheld PQ1/HGB candidates under the primary three-day, five-percent development criterion. PQ1 adds current active/reactive power to the common forecast/clock/ID. Cost is mean kWh-equivalent loss per valid turbine interval; risk is the maximum-instance joint upper bound. All four remain minimum-unresolved.}
\label{tab:subset-candidate}
\begin{tabular}{rrrr}
\toprule
Fit rows & Cost & Risk UCB & Smaller unresolved \\
\midrule
10k & 32.747 & 8.34\% & 13/21 \\
40k & 32.648 & 9.05\% & 15/21 \\
120k & 32.638 & 8.37\% & 15/21 \\
360k & 32.670 & 8.60\% & 14/21 \\
\bottomrule
\end{tabular}
\end{table}

The single-step candidate does not prove wind or trajectories universally redundant: wind/power already enter the common upstream forecast, and the MLP recipe does not reproduce all HGB behavior. More training rows also increase optimizer updates without adding evaluation weather days. Neither universal neural inferiority nor asymptotic saturation is established. Full settings, all cases, historical choices and the source-qualified but unexecuted external confirmation are documented in the supplementary material.

# Discussion

The evidence does not establish a deployment hierarchy assigning fresh telemetry to physics, observable delay to recalibration and missing pitch to representations. Historical physical-rule and recalibration results describe their evaluated conditions; recovery metrics and non-significant routing tests do not establish representation necessity or equivalence. The controlled study instead asks which historically calibrated candidates meet declared requirements and whether smaller alternatives can be excluded.

A failed identification can coexist with risk-qualified policies. In the new study, all primary-span groups contain such policies, while simultaneous relative-cost uncertainty prevents the two-percent criterion. Increasing training-row density leaves the same 35 evaluation weather days; this design cannot guarantee narrower decision intervals or isolate a unique cause such as calibration, optimization or drift. The five-percent results are prespecified sensitivity analyses, not a relaxation adopted after observing failure.

\textit{Historical comparison:} The latest imported strong-baseline snapshot reports a full-population posterior penalty of $+445{,}639\text{ kW}\cdot\text{h}$ relative to site-local wind-speed bins. Its transition-slice penalty is $+71{,}204\text{ kW}\cdot\text{h}$, and the imported transition-versus-steady interaction is $-303{,}232\text{ kW}\cdot\text{h}$ with 95\% interval $[-597{,}953, +19{,}013]\text{ kW}\cdot\text{h}$, crossing zero. These values are pending deep numerical and statistical audit; they support no plant-wide posterior cost superiority and do not establish transition-localized heterogeneity. The historical closure and its slice-specific interaction are superseded provenance only. Because the current interaction interval crosses zero, no transition-localized heterogeneity or relative penalty attenuation is promoted to a current claim. A deployable hybrid policy is not certified to differ from wind-speed binning; the current candidate snapshot remains pending audit. The reported routing comparisons do not establish an advantage; neither routing equivalence nor universal redundancy is demonstrated.

\textit{External scope:} The deterministic_matched_transfer_v1 branch uses existing weights and local frozen forecasts/calibration; its h=6 posterior-minus-local-wind-bin deltas are $+6.3\text{k kW}\cdot\text{h}$ for Kelmarsh (interval crossing zero) and $+356.0\text{k kW}\cdot\text{h}$ for Penmanshiel. It does not close the full EXP-01 claim. Corrected-v2 is superseded/not reinstated; v4 is invalidated by physical-window mismatch. The newly acquired Hill of Towie archives have not supplied an independent model-confirmation result. The held-out archive must remain sealed until the entire historical analysis and selection package is frozen. No PCC procurement, storage deliverability or field-safety conclusion follows from turbine-level surrogate losses.

# Limitations

The empirical findings are bounded by four operational and experimental scope conditions:

\textit{1) Synthetic Stress:} Impairments are evaluated under synthetic stress ($10\text{--}30\text{ min}$ backlogs, 60-min latency, Gilbert-Elliott dropouts); field units may exhibit sensor icing or individual pitch actions outside supervisory records.

\textit{2) Risk Surrogacy:} Evaluation operates at Level-1 pre-dispatch operating reserve screening via the PSREI newsvendor surrogate ($\rho=10$), abstracting Level-2 bulk transmission AC-OPF and balancing settlements.

\textit{3) Horizon Scope:} Benchmarks use a 35-day continuous test split across five random seeds (201--205), omitting multi-annual climatological cycles. Rated wind speeds vary by model ($12.5\text{ m/s}$ on MM92 vs. $14.5\text{ m/s}$ on MM82), requiring OEM calibration.

\textit{4) Deployment Boundaries:} EXP-01 v4 is invalidated by physical-window mismatch; its numerical cost differences and intervals are withdrawn from current conclusions. Historical EXP-02 also requires replay because its physical proxy labels used mismatched normalization statistics. These failures leave the corresponding decision questions unresolved. Historical pitch availability during training must remain distinguished from pitch-never-recorded deployment scenarios.

# Conclusion

This study separates state recoverability, decision sufficiency and resource minimality in wind-turbine reserve-risk screening. Historical recovery metrics do not establish incremental decision value, and the latest imported strong-baseline snapshot reports a full-population posterior penalty under its separately bounded, pending-audit scope. In the completed controlled development study, risk-qualified policies exist but no primary-span condition/budget case satisfies two-percent near-optimality. At the predeclared five-percent margin, current active/reactive power with HGB supplies a sufficient pitch-withheld candidate across four row budgets, yet smaller alternatives remain unresolved. No finite-family minimum is identified. Estimator and row-budget sensitivity prevent a universal model ranking, while independent source acquisition is not independent model confirmation. The supported contribution is therefore a bounded information-and-decision assessment with explicit nonidentification. Representation necessity, a reliable deployment map, PCC economic value and external confirmation remain open. E04 selected no feasible policy; E07 remains inactive.

# Acknowledgment {.unnumbered}

The authors acknowledge the use of OpenAI ChatGPT and Codex for assistance in drafting and refining prose across Sections I--VII, formatting IEEE LaTeX macros, and developing automated verification scripts. All mathematical derivations, experimental designs, empirical results, and scientific interpretations were developed by the authors, who take full responsibility for the contents of this paper.

\textbf{Code and Data Availability:} Raw SCADA datasets (WTB, ENGIE La Haute Borne, Kelmarsh, Penmanshiel) are publicly available. The separately acquired Hill of Towie archives are described at \url{https://zenodo.org/records/22662930}; historical source preparation is complete, while the 2025 archive remains unparsed and independent model confirmation is unexecuted. Code, manifests, and verification suites are available at \url{https://github.com/b1ue13e/windfarm-latent-boundary-risk}. Archived arrays support bounded accounting and diagnostic checks, but historical weight, complete-input and numerical-environment bindings remain incomplete. The original rented compute instance has been reported destroyed, and its investigation has stopped. File hashes do not certify end-to-end reproduction or deployment safety; the supplementary material and repository reproducibility statement specify the frozen gaps. E07 remains inactive.
# References

::: {#refs}
:::
