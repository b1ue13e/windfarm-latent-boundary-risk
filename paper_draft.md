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
csl: elsevier-harvard.csl
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
\Large\bfseries Operating-Boundary Routing Accountability and Transition-Window Reserve Diagnostics for Wind-Power Transitions\par
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
Wind-power forecasts become operationally valuable when they change how much reserve an operator carries, not merely when they lower a fleet-wide error score. This paper studies the maximum power point tracking (MPPT)-to-pitch transition, where blade-pitch control changes the local power response and over-forecasts can become reserve violations. We ask whether supervisory control and data acquisition (SCADA) operating anchors can make a routed forecaster physically traceable enough for transition-window reserve diagnosis. The KDD Cup 2022 wind-farm SCADA benchmark (WTB) is the source control-boundary test; ERA5 is an observability contrast. A directed-diffusion gated recurrent unit with a node-level mixture-of-experts gate is constrained by wind-speed and pitch-based regime anchors, graph smoothness, wake supervision, and boundary-focused forcing so that gate-level operating-regime alignment is tested, not only prediction error. On MPPT-to-pitch boundary anchors, a frozen validation-to-test gate-bin reserve rule at shortage-to-reserve cost ratio 10 lowers same-model total cost from 88.13M to 84.58M normalized reserve-energy cost units, violation rate from 0.1038 to 0.0900, and shortage energy from 3.73M to 3.19M, while adding 1.85M reserve energy. The measured engineering tradeoff is that Graph WaveNet remains the WTB accuracy reference (overall RMSE 225.74 +/- 2.60), whereas the boundary-aware router prioritizes physically traceable state assignment (NMI/ARI 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371). Kelmarsh/Penmanshiel runs fail the pre-specified external-site routing criterion after local recalibration, so the result is WTB-internal boundary interpretability, external failure-boundary diagnosis, and transition-window reserve diagnosis rather than a transferable reserve controller.

\vspace{0.25em}
\noindent{\small\textbf{Keywords:} Wind-power operations; operating boundary; reserve decision; mixture of experts; regime routing; spatio-temporal graph learning.\par}

\normalsize

\vspace{0.55em}

# Introduction

High wind penetration makes wind-power forecasting valuable at the point where forecast errors change reserve and dispatch decisions. System operators do not buy accuracy for its own sake; they buy enough flexible reserve to cover renewable uncertainty without paying avoidable reserve, shortage, imbalance, or curtailment costs [@doherty2005reserve; @ela2011operatingreserves; @pinson2013forecasting; @wang2025uncertaintyreview]. Forecast value is therefore measured at the interface between a prediction and an operating decision: unit commitment, reserve procurement, market balancing, trading, or reliability screening [@pinson2007trading; @wang2011unitcommitment; @zhou2013probabilisticmarkets]. This paper studies that interface at the maximum power point tracking (MPPT)-to-pitch boundary. In this window, blade-pitch control changes the local power-response law, so an over-forecast can directly become a reserve violation. The evaluated WTB operating partition is dominated by MPPT operation but contains a smaller pitch-control share, making the transition sparse enough to be missed by average metrics and important enough to expose reserve planning. We therefore report not only RMSE, but also cost, violation rate, reserve energy, and shortage energy under a declared shortage-to-reserve cost ratio of 10.

Existing forecasting models provide strong accuracy references but do not tell an operator which physical response law is active at a control transition. Spatio-temporal graph neural networks encode turbine coupling, wake interaction, and dynamic dependence [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @wu2020connecting], and recent wind studies use SCADA, LiDAR, physical graphs, and offshore layouts to improve wind-power prediction [@khodayar2019stwind; @park2019physicsinduced; @yu2020sgnn; @kim2024lidarscada; @daenens2025offshore]. These methods can define the low-error baseline, but they do not assign a physically traceable local map at the MPPT-to-pitch boundary. Mixture-of-experts (MoE) routing is a natural tool for heterogeneous response laws [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch; @shi2025timemoe], yet prediction-loss-driven routing can specialize without physical meaning. Physics-guided learning adds constraints through features, losses, architectures, or priors [@karpatne2017tgds; @read2019pgdl; @raissi2019pinn; @karniadakis2021piml; @zehtabiyan2023physicsguided; @parsa2025pimlreview; @gao2025physicsconstrained], but those constraints usually act on outputs or latent states rather than on the routing decision that downstream reserve logic would consume.

This study makes the routing decision itself an operating-regime diagnostic. The model encodes local spatio-temporal context with a directed-diffusion GRU and uses a node-level MoE gate to allocate forecasts among local experts. The gate is constrained by wind-speed and pitch-angle anchors from SCADA, graph smoothness, wake supervision, and boundary-focused forcing, so the learned assignment can be compared with the declared MPPT-to-pitch operating partition. WTB is the main control-boundary benchmark because the aerodynamic boundary is partly hidden inside turbine control action; ERA5 is retained as an observability contrast where the thermodynamic marker is more directly visible through sensible heat flux. The recovered gate is then connected to a frozen validation-to-test reserve diagnostic that reports cost, violation rate, reserve energy, and shortage energy together. Kelmarsh/Penmanshiel external-site experiments are deliberately framed as failure-boundary diagnostics: they test whether the WTB operating rule can be reused after local recalibration, and they show when local sensor coverage, turbine geometry, and boundary support are insufficient.

The paper makes three contributions ordered by their operating value. First, it provides gate-level operating-regime alignment inside WTB: the boundary-aware router recovers the MPPT-to-pitch partition with NMI/ARI 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371, and removing boundary anchors collapses that agreement. Second, it turns the recovered state assignment into a transition-window reserve diagnostic: on MPPT-to-pitch boundary anchors, the gate-bin policy lowers same-model total cost from 88.13M to 84.58M normalized reserve-energy cost units, violation rate from 0.1038 to 0.0900, and shortage energy from 3.73M to 3.19M, at the price of 1.85M extra reserve energy. Third, it reports external wind-farm failure as deployment safety evidence rather than as a hidden limitation: the completed Kelmarsh/Penmanshiel audit fails the pre-specified external-site routing criterion after local recalibration, showing that WTB-internal physical interpretability must be re-established before the gate is used at a new site.

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting is operationally useful when it supports decisions under variability, not only when it reduces a fleet-wide error score. Reviews and forecasting studies emphasize that wind power is driven by non-stationary weather, wake interaction, turbine coupling, ramp events, changing control states, and the quality of uncertainty information available to operators [@pinson2013forecasting; @gallego2015rampreview; @yang2025windprocess; @wang2025uncertaintyreview; @haq2025windreview]. Spatio-temporal graph models address part of this difficulty by encoding dependence across turbines or locations [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @wu2020connecting], and wind-specific graph or sensor-fusion models use wake structure, SCADA, LiDAR, and offshore layouts to represent turbine coupling more directly [@park2019physicsinduced; @yu2020sgnn; @kim2024lidarscada; @daenens2025offshore]. These models define the accuracy baselines for this paper. The open issue is narrower: a low-error graph encoder may still fail to identify the operating transition where reserve and ramp-risk decisions become most sensitive.

## Operating regimes, SCADA observability, and physical interpretability

Regime-aware modeling provides a way to separate local response laws, but the separation must be physically interpretable at the routing level. Early adaptive and hierarchical MoE models partitioned inputs among local experts [@jacobs1991adaptive; @jordan1994hierarchical], and modern sparse MoE systems made routing scalable while exposing collapse, starvation, and unstable load allocation as practical failure modes [@shazeer2017outrageously; @fedus2022switch]. Recent sequence-forecasting and state-conditioned routing work imports this specialization idea into time-series settings [@shi2025timemoe; @cao2026ecto; @tian2026arrow]. Physics-guided learning offers the complementary principle: theory can enter through features, pretraining, architecture, losses, probability constraints, or post-hoc checks [@karpatne2017tgds; @read2019pgdl; @raissi2019pinn; @karniadakis2021piml; @parsa2025pimlreview; @gao2025physicsconstrained]. For wind turbines, SCADA observability matters because operating-state labels depend on sensor coverage, pitch channels, availability masks, and turbine-specific power curves [@tautzweinert2017scada; @zhou2024sdwpfdata]. Prior work therefore explains why operating regimes can be sensor- and turbine-specific. This paper asks a different question: whether those SCADA-derived regime anchors can constrain the MoE gate so that the forecast model produces a physically traceable state assignment near a control boundary.

## Forecast-driven reserve allocation and risk diagnostics

Forecast value in power systems is usually realized through reserve, commitment, balancing, and trading decisions. Reserve studies show that variable generation changes operating-reserve requirements and that reserve demand should reflect uncertainty rather than a fixed margin [@doherty2005reserve; @ela2011operatingreserves]. Probabilistic wind forecasting, quantile forecasting, and predictive-uncertainty reviews provide the statistical bridge from point forecasts to decision risk [@bremnes2004quantile; @nielsen2006quantile; @zhang2014probabilisticreview; @wang2025uncertaintyreview], while trading and market studies connect wind forecast uncertainty to operating costs and imbalance exposure [@pinson2007trading; @wang2011unitcommitment; @zhou2013probabilisticmarkets]. This literature motivates reserve-aware evaluation, but the present study is deliberately narrower than market clearing, unit commitment, or a trained probabilistic forecast-to-reserve pipeline.

The reserve diagnostic used here is an empirical, validation-frozen operating test. It converts held-out forecast shortfall into reserve bins using validation quantiles, then reports total cost, violation rate, reserve energy, and shortage energy under declared shortage-to-reserve cost ratios. This point-forecast empirical-quantile rule is simpler than calibrated predictive distributions, scenario optimization, or security-constrained dispatch, and it should not be interpreted as a production reserve optimizer. Its purpose is diagnostic: to test whether a physically traceable MPPT-to-pitch gate changes the cost-violation-shortage tradeoff exactly where the turbine control law changes.

## Gap summary

Existing research is strong at two ends of the pipeline. One end provides accurate spatio-temporal forecasters and physics-guided predictors; the other explains how wind forecast uncertainty should affect reserve and market decisions. The missing middle layer is an operating diagnostic that identifies which physical response law is active at a control-transition boundary and then connects that diagnosis to transition-window reserve cost, violation, reserve energy, and shortage energy. When a router cannot distinguish MPPT operation from pitch-control operation, the operator lacks a physical basis for reserve binning in the window where reserve exposure is concentrated. This paper fills that interface inside WTB and treats external wind-farm failure as a boundary-condition diagnosis, not as evidence of direct site transfer.

# Methodology

## Problem setup and notation

The forecasting task is written to separate two decisions that dense models often merge: predicting the future and deciding which local mapping should be active at the anchor time. Let $G=(V,E)$ denote a spatial graph with $N=|V|$ nodes. For each node $i \in V$ and time step $t$, we observe a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predict a scalar target $y_{i,t} \in \mathbb{R}$. Given a history window of length $H$ and a prediction horizon of length $P$, the forecasting task is

$$
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
$$

where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes either a time-varying directed graph sequence (WTB) or a static graph repeated over time (ERA5). Invalid or missing targets are excluded by a supervision mask.

The time index is part of the information boundary. All inputs, graph weights, regime anchors, and gate anchors are observed no later than the anchor time $t$; the supervised targets begin at $t+1$. In WTB, active power appears both as a historical SCADA channel and as the future target. The historical/anchor value $\texttt{Patv}_{i,t}$ may enter the gate because it is observed at the forecast issue time, but $\texttt{Patv}_{i,t+\tau}$ for $\tau \ge 1$ is used only as the held-out prediction target and its validity mask. The gate is therefore allowed to use the current turbine operating status, not future power. This convention avoids target leakage in the multi-step horizon, but it also narrows the interpretation: without a separate no-\texttt{Patv} or lagged-\texttt{Patv} ablation, the recovered gate should not be read as proving that the router reconstructs the MPPT-to-pitch boundary independently of active-power telemetry.

Table 1 lists the notation used in the routing and loss definitions. Routing is node-level: each node at each anchor time receives its own gate distribution $\mathbf{g}_{i,t}$. This is essential because nearby turbines or grid cells can move into different local regimes within the same sequence.

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table 1.} Core notation used in the routing and loss definitions.}
\begin{tabularx}{0.98\textwidth}{>{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.18\textwidth}}
\toprule
Symbol & Meaning & Dimension \\
\midrule
$\mathbf{x}_{i,t}$ & Node feature vector at node $i$, time $t$ & $\mathbb{R}^{F}$ \\
$\mathbf{X}_{t-H+1:t}$ & Input history window & $\mathbb{R}^{H \times N \times F}$ \\
$y_{i,t}$ & Scalar target & $\mathbb{R}$ \\
$\bar{p}_{i,t}$ & Mean blade-pitch angle (\texttt{Pab\_mean}) in WTB & scalar \\
$\texttt{Patv}_{i,t}$ & Active power observed at anchor time; future values are prediction targets & scalar \\
$\mathbf{h}_{i,t}$ & Encoded node context & $\mathbb{R}^{d}$ \\
$\mathbf{a}_{i,t}$ & Physics anchor vector used by the gate & $\mathbb{R}^{q}$ \\
$\mathbf{z}_{i,t}$ & Gate logits & $\mathbb{R}^{E}$ \\
$\mathbf{g}_{i,t}$ & Gate probabilities after softmax & $\mathbb{R}^{E}$ \\
$f_e(\cdot)$ & Expert-$e$ prediction head & $\mathbb{R}^{d} \rightarrow \mathbb{R}^{P}$ \\
$R_{i,t}$ & Primary regime anchor label & discrete \\
$W_{i,t}$ & Auxiliary wake flag in WTB & $\{0,1\}$ \\
$\mathcal{A}_t(i,j)$ & Edge weight from node $j$ to node $i$ at time $t$ & scalar \\
$E$ & Number of experts & scalar \\
$K$ & Top-$K$ used in the balancing loss & scalar \\
\bottomrule
\end{tabularx}
\end{table}
```

## Operating-boundary anchors and labels

The gate is not supervised everywhere. It is anchored where the physical interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularization. This is the engineering layer of the method: before defining a network, the paper defines what counts as a control regime and when that regime is observable from the data.

### WTB operating regimes

In WTB, the primary operating boundary is the transition from MPPT to pitch control. Let

$$
\bar{p}_{i,t} = \frac{1}{3}\left(p^{(1)}_{i,t}+p^{(2)}_{i,t}+p^{(3)}_{i,t}\right).
$$

The WTB column name `Pab` denotes blade pitch angle. We use $\bar{p}_{i,t}$, also reported as `Pab_mean` in tables and figures, for the three-blade pitch average. This is separate from `Patv`, the active-power channel and prediction target, and from `Wspd`, the nacelle wind-speed channel. The regime labels below use wind speed and mean pitch angle at the anchor time, not future active power.

Using a cut-in threshold $u_{\mathrm{idle}}$, a pitch-transition threshold $u_{\mathrm{rated}}$, and a pitch-angle threshold $p_{\mathrm{th}}$, we define

$$
R^{\mathrm{wtb}}_{i,t} =
\begin{cases}
0, & \text{if } \texttt{Wspd}_{i,t} < u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & \text{if } u_{\mathrm{idle}} \le \texttt{Wspd}_{i,t} \le u_{\mathrm{rated}} \ \land\ \bar{p}_{i,t} < p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & \text{if } \texttt{Wspd}_{i,t} > u_{\mathrm{rated}} \ \land\ \bar{p}_{i,t} \ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transition)}.
\end{cases}
$$

Only the first three classes are used in direct alignment. Transition samples are retained for analysis but masked out of label supervision through

$$
M^{\mathrm{wtb}}_{i,t} = \mathbf{1}[R^{\mathrm{wtb}}_{i,t} \neq 3].
$$

These thresholds are operating anchors, not universal turbine constants. The reported WTB implementation uses $u_{\mathrm{idle}}=3.0$ m s$^{-1}$, $u_{\mathrm{rated}}=10.5$ m s$^{-1}$, and $p_{\mathrm{th}}=2.0^\circ$, with the exact table repeated in the Appendix. They are treated as site- and sensor-specific choices that must be re-estimated before a new-farm interpretation. The threshold audit and local-boundary recalibration evidence test whether the saved gates survive nearby rated-wind and pitch-threshold changes, but they do not exhaust all cut-in, rated-wind, pitch-angle, wake-score, or turbine-control alternatives.

### ERA5 thermodynamic regimes

In ERA5, the anchor is built around the stable-to-convective transition. Surface sensible heat flux changes sign across that transition, and large flux gradients mark disturbed periods. Let $\Delta \texttt{sshf}_{i,t} = \texttt{sshf}_{i,t} - \texttt{sshf}_{i,t-1}$. We use a small-margin threshold $\varepsilon_{\mathrm{sshf}}$ for $|\texttt{sshf}|$. We also use a high-quantile threshold $q_{0.95}^{\Delta}$ for $|\Delta\texttt{sshf}|$. The regime label is then defined by

$$
R^{\mathrm{era5}}_{i,t} =
\begin{cases}
0, & \text{if } \texttt{sshf}_{i,t} > \varepsilon_{\mathrm{sshf}} \ \land\ |\Delta \texttt{sshf}_{i,t}| \le q_{0.95}^{\Delta} \quad \text{(convective)},\\
1, & \text{if } \texttt{sshf}_{i,t} < -\varepsilon_{\mathrm{sshf}} \ \land\ |\Delta \texttt{sshf}_{i,t}| \le q_{0.95}^{\Delta} \quad \text{(stable)},\\
2, & \text{otherwise} \quad \text{(transition/anomalous)}.
\end{cases}
$$

If sensible heat flux is unavailable, the same construction can fall back to an analogous rule based on the temporal gradient of 2 m temperature. The exact thresholds used in the reported experiments are listed in the Appendix.

## Shared architecture

### Physical graph construction

The graph is part of the physical problem specification. In WTB, it exposes likely wake pathways. In ERA5, it preserves geographically local dependence because the thermodynamic regime marker is already visible in the state. Exact graph constants are listed in the Appendix tables.

For WTB, each turbine has a fixed coordinate $\mathbf{p}_i=(x_i,y_i)$. A candidate set is first built by retaining the $k_{\mathrm{nn}}$ nearest turbines within a maximum radius $d_{\max}$. Let $\Delta \mathbf{p}_{ij}=\mathbf{p}_j-\mathbf{p}_i$ and let $\theta_{i,t}$ denote the local meteorological wind-from direction. The downstream unit vector is

$$
\mathbf{u}_{i,t} =
\begin{bmatrix}
\sin(\theta_{i,t} + \pi) \\
\cos(\theta_{i,t} + \pi)
\end{bmatrix}.
$$

which gives the streamwise and cross-stream distances

$$
d^{\parallel}_{ij,t} = \Delta \mathbf{p}_{ij}^{\top}\mathbf{u}_{i,t},
\qquad
d^{\perp}_{ij,t} = \left| \Delta p^x_{ij} u^y_{i,t} - \Delta p^y_{ij} u^x_{i,t} \right|.
$$

An edge is activated only when turbine $j$ falls inside a downstream cone,

$$
\mathbb{I}^{\mathrm{cone}}_{ij,t} =
\mathbf{1}\!\left[
d^{\parallel}_{ij,t} > 0
\ \land\
\arctan\!\left(\frac{d^{\perp}_{ij,t}}{\max(d^{\parallel}_{ij,t}, 10^{-6})}\right)
\leq \phi
\right],
$$

and the resulting wake weight is

$$
\tilde{\mathcal{A}}_t(i,j) =
\exp\!\left(-\frac{d^{\parallel}_{ij,t}}{\alpha}\right)
\exp\!\left(-\frac{|d^{\perp}_{ij,t}|}{\beta}\right)
\mathbb{I}^{\mathrm{cone}}_{ij,t},
$$

If wind direction is missing, the implementation falls back to a static proximity weight

$$
\mathcal{A}^{\mathrm{static}}(i,j)=\exp\!\left(-\frac{\lVert \Delta \mathbf{p}_{ij}\rVert_2}{d_{\max}}\right).
$$

Only the strongest $M$ inbound weights are retained for each target and time step. The same weights define a wake score,

$$
s^{\mathrm{wake}}_{i,t} = \sum_{j} \mathcal{A}_t(i,j),
$$

which is later used as an auxiliary routing indicator. Wake interference is handled separately from the MPPT-to-pitch label because it is spatial. Let $q_{0.75}^{\mathrm{wake}}$ denote the upper-quartile threshold of the wake score over valid operating states in the training split. Then

$$
W_{i,t} =
\begin{cases}
1, & \text{if } s^{\mathrm{wake}}_{i,t} \ge q_{0.75}^{\mathrm{wake}} \ \land\ R^{\mathrm{wtb}}_{i,t} \in \{1,2\},\\
0, & \text{if } s^{\mathrm{wake}}_{i,t} < q_{0.75}^{\mathrm{wake}} \ \land\ R^{\mathrm{wtb}}_{i,t} \in \{1,2\},\\
\varnothing, & \text{otherwise.}
\end{cases}
$$

ERA5 uses a simpler graph because the main uncertainty is local transport over the retained patch. Each grid point is treated as a node with geographic coordinate $(\varphi_i,\lambda_i)$, and the great-circle distance is computed by the Haversine formula

$$
d_{ij} = 2 R \arctan\!\left(
\frac{\sqrt{a_{ij}}}{\sqrt{1-a_{ij}}}
\right),
$$

where $R=6371$ km and

$$
a_{ij} =
\sin^2\!\left(\frac{\varphi_j-\varphi_i}{2}\right)
+
\cos(\varphi_i)\cos(\varphi_j)\sin^2\!\left(\frac{\lambda_j-\lambda_i}{2}\right).
$$

We then retain a symmetric $k_{\mathrm{nn}}$-nearest-neighbor graph and define

$$
\mathcal{A}(i,j) =
\exp\!\left(
-\frac{d_{ij}^2}{2\sigma^2}
\right)\mathbf{1}[j \in \mathcal{N}_{k_{\mathrm{nn}}}(i) \ \text{or}\ i \in \mathcal{N}_{k_{\mathrm{nn}}}(j)],
$$

where $\sigma$ is the median retained neighbor distance on the training graph. The design is intentionally simpler than WTB because the ERA5 regime marker is already visible in the observed state.

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

The difference reflects the observability contrast: WTB needs help to recover a partly hidden operating boundary, whereas ERA5 already exposes the relevant thermodynamic marker in the state. The active-power anchor is the observed value at the issue time, equivalent to a status input in a rolling SCADA forecast. It is standardized using training-split statistics and is never filled from the prediction horizon. This makes the router operationally admissible only when current active-power telemetry is available before the forecast is issued. If an operator's dispatch cutoff does not make current active power available, the same protocol must drop or lag this anchor and rerun the leakage, intervention, and reserve checks before interpreting the gate physically.

### Routing stack and evidence boundary

This makes the routing stack an anchor-constrained diagnostic, not an unsupervised operating-state discovery method. In WTB, `Wspd` and `Pab_mean` appear both in the gate anchor and in the pseudo-label rule used for alignment, so high gate-regime agreement should be read as evidence that the implemented router obeys a declared operating boundary. It does not prove that the boundary would be recovered from unrelated SCADA channels. The same caution applies to `Patv`: the current value is an issue-time status input, but without a retrained no-`Patv` or lagged-`Patv` ablation the paper cannot separate how much of the gate comes from active-power telemetry versus wind-speed and pitch information. The evidence therefore supports auditable responsibility under the declared anchor set, not anchor-free regime discovery.

![Physics-aligned regime-aware MoE. The two datasets share the same directed-diffusion GRU encoder and node-level MoE routing mechanism. WTB uses a dynamic wake graph and a boundary-focused forcing term, whereas ERA5 uses a Haversine-Gaussian graph and a thermodynamic regime anchor.](artifacts/final_evidence_package/export/figures/figure1_architecture.pdf){ width=95% }

## Physics-aligned routing regularizers

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

with inactive terms set to zero in settings where they are not used. Exact weights are listed in the Appendix.

The training loop is straightforward despite the loss stack. Each mini-batch starts from the history window and the graph sequence, builds the node-level graph context, and encodes the sequence with the directed-diffusion GRU. The gate then combines the encoded context with the physics anchor, produces node-level routing probabilities, and aggregates the expert forecasts. The prediction loss is always evaluated first. Active routing losses then add expert-usage stabilization, regime-anchor alignment, the WTB MPPT/pitch forcing term, wake auxiliary supervision, and graph smoothness only in the settings where those terms are declared. Checkpoint selection remains based on validation RMSE, so the routing penalties constrain responsibility without becoming the validation-selection metric.

### Prediction objective

The prediction loss remains the anchor of the optimization, because a routing correction that stops serving the forecast defeats the purpose of the model. We retain the masked mean-squared-error loss

$$
\mathcal{L}_{\mathrm{pred}}
=
\frac{
\sum_{i,t,\tau} m^{y}_{i,t+\tau}\left(\hat{y}_{i,t+\tau}-y_{i,t+\tau}\right)^2
}{
\sum_{i,t,\tau} m^{y}_{i,t+\tau}
},
$$

where $m^{y}_{i,t+\tau}$ is the target-validity mask. All routing regularizers remain subordinate to this prediction objective.

### Load balancing

A slightly favored expert can dominate early training and starve the others before regime-specific structure has time to emerge. A balancing term counteracts that early collapse. It follows the same practical role as Switch-style load and importance penalties [@fedus2022switch], but it is written in the notation of node-time routing rather than sequence-token routing. Let $\mathcal{B}$ denote the routed node-anchor samples in a mini-batch after target and anchor masks are applied, and let $B=|\mathcal{B}|$. For the $n$-th sample in this set, the soft importance of expert $e$ is

$$
I_e = \frac{1}{B}\sum_{n=1}^{B} g_n^{(e)},
\qquad
P_e = \frac{I_e}{\sum_{r=1}^{E} I_r}.
$$

The empirical top-$K$ load is

$$
f_e = \frac{1}{B}\sum_{n=1}^{B}\mathbf{1}\!\left[e \in \mathrm{TopK}(\mathbf{g}_n)\right].
$$

The balancing loss couples hard usage and soft probability mass:

$$
\mathcal{L}_{\mathrm{bal}} = E\sum_{e=1}^{E} f_e P_e - 1.
$$

This statistic is computed per mini-batch over valid node-time samples and averaged by the optimizer over training steps. When the hard Top-$K$ load $f_e$ and the soft share $P_e$ are both close to uniform, $E\sum_e f_eP_e$ is close to one and the penalty is small. The term is therefore a training stabilizer, not a claim about optimal expert allocation or physical ownership. Regime ownership is supplied only by the anchored alignment terms below.

### Regime-anchor alignment

Balanced expert usage can still produce a physically meaningless partition. The next term aligns the gate with the coarsest regime structure that can be identified with high confidence. Let $\mathbf{z}^{(1:C)}_{i,t}$ denote the first $C$ gate logits, and let $R_{i,t}$ and $M_{i,t}$ be the primary regime label and its validity mask. The mapping from primary regime labels to the first $C$ logits is fixed by construction: for WTB, idle, MPPT, and pitch-control correspond to logits 1--3; for ERA5, stable, transition, and convective correspond to logits 1--3. This supervised index convention breaks the usual MoE label-permutation symmetry only for the anchored logits. Any extra expert logits remain unassigned unless they are used by the wake auxiliary term. The alignment loss is

$$
\mathcal{L}_{\mathrm{align}}
=
\frac{1}{|\Omega|}
\sum_{(i,t)\in\Omega}
\mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right),
\qquad
\Omega=\{(i,t):M_{i,t}=1\},
$$

with inverse-frequency class weights estimated on the training split. Alignment stabilizes the coarse physical partition only where the labels are reliable. The fixed index convention is an implementation constraint, not a post-hoc naming step: it deliberately breaks permutation symmetry for the anchored logits during training so that responsibility can be audited across seeds. The price is scope. The method cannot claim to discover every alternative data-driven partition that an unconstrained MoE might find; cross-seed statements such as "MPPT-aligned" or "pitch-aligned" refer only to this declared mapping and are not inferred after training by relabeling experts.

### Boundary-focused forcing (WTB only)

The MPPT-to-pitch boundary in WTB remains ambiguous even after coarse regime alignment because control action partly masks the mechanical transition. A focused forcing term acts only on the most informative MPPT and pitch-control samples. Let

$$
Y^{\mathrm{force}}_{i,t} =
\begin{cases}
0, & R^{\mathrm{wtb}}_{i,t}=1,\\
1, & R^{\mathrm{wtb}}_{i,t}=2.
\end{cases}
$$

Using the MPPT-aligned and pitch-aligned expert logits fixed above, we define

$$
\mathcal{L}_{\mathrm{force}}
=
\frac{1}{|\Omega_{\mathrm{force}}|}
\sum_{(i,t)\in\Omega_{\mathrm{force}}}
\mathrm{CE}\!\left(
\begin{bmatrix}
z^{(\mathrm{mppt})}_{i,t}\\
z^{(\mathrm{pitch})}_{i,t}
\end{bmatrix},
Y^{\mathrm{force}}_{i,t}
\right),
$$

where $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}, M_{i,t}=1\}$. This term concentrates the intervention on high-confidence MPPT and pitch-control anchors already visible at the issue time. It increases routing identifiability around the boundary after the operating state is expressed in the SCADA channels; it is not designed or evaluated as a lead-time switch predictor.

### Wake auxiliary supervision and graph smoothness

After the MPPT-to-pitch boundary is repaired, wake-sensitive samples can still be mixed with non-wake samples inside the same operating regime. A wake auxiliary label identifies that residual ambiguity in WTB, while graph smoothness discourages noisy neighbor-to-neighbor gate jumps in both settings. The wake auxiliary loss is

$$
\mathcal{L}_{\mathrm{aux}}
=
\frac{1}{|\Omega_{\mathrm{wake}}|}
\sum_{(i,t)\in\Omega_{\mathrm{wake}}}
\mathrm{BCE}\!\left(z^{(\mathrm{wake})}_{i,t}, W_{i,t}\right),
$$

where $\Omega_{\mathrm{wake}}$ contains only MPPT and pitch-control samples for which the wake flag is defined. The wake flag is a thresholded auxiliary view of the continuous wake score, using the training-split upper quartile reported in the Appendix; the continuous score still enters the anchor vector. This threshold is a pragmatic high-exposure label rather than a complete wake model, and its sensitivity is treated as part of the threshold-limited evidence boundary. The smoothness term is computed on the graph snapshot associated with the anchor time,

$$
\mathcal{L}_{\mathrm{smooth}}
=
\frac{
\sum_{t \in \mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)\lVert \mathbf{g}_{i,t}-\mathbf{g}_{j,t}\rVert_2^2
}{
\sum_{t \in \mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j) + \epsilon
}.
$$

Here $\mathcal{T}_{\mathcal{B}}$ is the set of anchor times represented in the mini-batch, and $\epsilon$ prevents division by zero if a graph has no retained edges. The auxiliary term is a WTB-specific repair for wake mixing, while the smoothness term encourages locally coherent routing without prescribing a global partition. This is a bias toward neighbor-consistent responsibility, not a physical law. In disturbed inflow or local-wake conditions, it may smooth over real turbine-level heterogeneity, so wake-specific failures are checked separately rather than treated as solved by graph smoothness.

## Operational reserve diagnostic protocol

The reserve diagnostic is a frozen validation-to-test procedure, not a dispatch simulator or probabilistic forecasting benchmark. Its purpose is to test whether a physically auditable gate changes the reserve tradeoff in the MPPT-to-pitch window after the point-forecast model has already been trained. For each saved WTB run, validation predictions are used only to select reserve levels; test predictions are then evaluated once with those reserve levels fixed. The protocol therefore follows the same information boundary as an operator who calibrates a short-term reserve rule before using it on a later operating period.

Let $\hat{y}_{i,t}$ be the scheduled point forecast and $y_{i,t}$ the realized active power at an evaluated horizon cell. We define over-forecast shortfall as

$$
s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0),
$$

because this is the error direction that leaves a reserve schedule exposed. The quantiles below are empirical quantiles of point-forecast shortfall, not outputs of a trained quantile-regression or distributional forecaster. For a reserve policy $b$ and quantile $q$, the validation split estimates a reserve level

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

The selected $(b,q)$ rule is then frozen and applied to the test split. The reported test metrics are total cost $C$, violation rate $\Pr[s_{i,t}>r_b]$, reserve energy $\sum r_b\Delta t$, and shortage energy $\sum \max(s_{i,t}-r_b,0)\Delta t$. All totals are reported in normalized reserve-energy cost units. Thus a value written as 84.58M denotes 84.58 million normalized reserve-energy cost units, not currency.

The cost ratio $\rho$ is an energy-system assumption rather than an abstract tuning knob. If the marginal cost of carrying one unit of reserve energy is $C_r$, then $\rho=10$ means that one unit of residual shortage is charged as $10C_r$. Ratios 5--10 represent moderate reliability settings such as transition-window scheduling or imbalance screening; ratios 20--50 represent scarcity-aware or emergency screening where shortage avoidance dominates local cost savings. The paper evaluates four policies under this protocol: Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin. Only same-model global comparisons are used to attribute gate-bin reserve effects to the learned router. Graph WaveNet/global remains the full-sample low-RMSE system reference, and Graph WaveNet/physical-bin remains the simple physical-stratification baseline that tests how much can be gained without learned gates.

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
Report horizon-specific empirical-quantile rows only as a post-hoc what-if; no probabilistic model is trained.
\end{minipage}}
\par
\endgroup
```

# Experimental Setup

## Datasets and preprocessing

The experiment uses two observability settings, not two interchangeable benchmarks. WTB is the control-confounded case. The KDD Cup 2022 benchmark contains 134 turbines and 245 days of 10 min SCADA measurements [@zhou2024sdwpfdata]. The MPPT-to-pitch transition is only indirectly visible because inflow variation, wake disturbance, and blade-pitch control are mixed in the same stream.

The data are reorganized into synchronous tensors with $T=35{,}280$ time steps, $N=134$ turbines, and $F=11$ dynamic inputs. Missing inputs are forward-filled within turbine and then completed with training-set means. Invalid or non-positive active power is retained only through its mask so that the model still sees operational irregularity without treating those points as supervised targets.

ERA5 is the signal-expressive case. We use three archived months over a fixed $16 \times 16$ hourly patch [@hersbach2020era5]. Sensible heat flux and its temporal variation make the stable-to-convective transition directly observable. The retained tensor has $T=2208$ frames, $N=256$ nodes, and eight input variables. Both datasets use the same history and horizon lengths, $H=36$ and $P=24$, so differences in performance cannot be attributed to unequal context length. The chronological split is 180/30/35 days for WTB and 1325/441/442 frames for ERA5.

## In-family comparison protocol

The comparison has two layers. The first isolates the routing mechanism after shared-capacity explanations have been controlled. The dense baseline uses the same directed-diffusion GRU encoder and replaces the expert mixture with one dense prediction head. The unconstrained MoE adds routed capacity without physical correction. The corrected-routing comparator is dataset-specific: ERA5 uses the full corrected stack, while WTB uses the boundary-focused variant selected for gate recovery. Parameter budgets are matched in WTB and near-matched in ERA5, where the dense model has 103,272 parameters and the routed models have 103,843 parameters.

The second layer tests the RMSE price against stronger and more engineering-facing baselines. Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST are included for WTB, together with deterministic persistence, a fitted physical power-curve baseline, XGBoost and LightGBM lag-feature predictors, and a DLinear-style LTSF baseline. Graph WaveNet, STGCN, PatchTST, TCN, and a deterministic persistence predictor are included for ERA5. This split keeps the paper from using one comparison for two different claims. The in-family layer tests whether physical routing changes the learned partition under a fixed backbone. The baseline layer tests whether the routing intervention remains honest about forecast error when compared with established temporal, graph, and engineering predictors.

For compactness, the mechanism tables shorten the three in-family model names to **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**. The WTB forecasting tables additionally report Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, the full physics-aligned MoE, the WTB boundary-forced router, and engineering baselines built from persistence, power curves, gradient-boosted lag features, and a DLinear-style LTSF readout. The ERA5 forecasting tables additionally report persistence and four learned external baselines. The in-family mechanism families are summarized in Table 2.

```{=latex}
\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.1}
\caption*{\textbf{Table 2.} In-family model comparison used for mechanism validation in the current encoder family.}
\begin{tabularx}{0.98\textwidth}{>{\raggedright\arraybackslash}p{0.18\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.20\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth}}
\toprule
Model & Routing & Extra terms & Params & Role \\
\midrule
Dense (matched) & Single dense head & None & WTB 110,012 / ERA5 103,272 & Shared-mapping reference \\
Unconstrained MoE & Node-level soft gate & Prediction loss only & WTB 110,012 / ERA5 103,843 & Tests whether routed capacity alone is enough \\
Corrected routing comparator & Node-level soft gate & WTB boundary-forced: $L_{bal}+L_{align}+L_{force}$; ERA5: full corrected stack & WTB 110,012 / ERA5 103,843 & Dataset-specific corrected-routing comparator \\
\bottomrule
\end{tabularx}
\end{table}
```

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in the Appendix so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST across seeds 201--205, giving 20 completed baseline runs under the same strict anchor-valid evaluation cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same frozen cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE use the evaluator's transition-window mask around regime changes. This is distinct from the later boundary-band audit, which isolates anchors within +/-1.0 m s$^{-1}$ of the WTB rated-wind MPPT-to-pitch boundary. Regime-wise RMSE locates the error reduction. Normalized mutual information (NMI), adjusted Rand index (ARI), usage entropy, and confusion matrices test whether the gate corresponds to physically interpretable structure.

Figure 2 gives the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=97% }

# Results

## Overall performance

WTB delivers a hard accuracy result: the strongest graph and engineering forecasters beat the routed family under the synchronized strict-mask refresh. Here and in the baseline tables, "switch-window" refers to the precomputed transition-window mask, not to the rated-wind boundary-band audit below. Graph WaveNet reaches overall RMSE 225.74 +/- 2.60 and switch-window RMSE 228.12 +/- 3.23 across seeds 201--205. PatchTST reaches 228.07 +/- 4.05 and 231.22 +/- 4.15. Graph Transformer reaches 235.38 +/- 5.15 and 237.06 +/- 5.78, while GAT-GRU reaches 236.59 +/- 7.80 and 240.17 +/- 8.50. Among engineering baselines, LightGBM lag features reach overall/switch RMSE 227.12 / 232.24, XGBoost lag features 227.88 / 233.07, a fitted physical power curve 241.02 / 245.37, persistence 243.23 / 246.61, and the DLinear-style LTSF readout 246.81 / 251.15. The boundary-forced router reaches overall RMSE 236.13 +/- 8.41, switch-window RMSE 239.86 +/- 8.85, and pitch-control RMSE 286.95 +/- 22.07 across seeds 201--205. The completed strict-mask leaderboard places the routed model outside a headline-error objective and motivates the narrower routing-recovery claim.

ERA5 makes the same separation sharper. A last-value persistence baseline gives the lowest headline error, with overall RMSE 0.7127 and switch-window RMSE 0.6814. Among learned ERA5 baselines, Graph WaveNet has the lowest learned-model RMSE at 0.8417 +/- 0.0540, followed by the matched dense encoder at 0.8641 +/- 0.0690, physics-aligned MoE at 0.8735 +/- 0.0479, TCN at 0.8784 +/- 0.0286, PatchTST at 0.8817 +/- 0.0675, Unconstrained MoE at 0.9294 +/- 0.0451, and STGCN at 0.9893 +/- 0.1344. The forecasting tables set the terms of the paper: physics-aligned routing earns its value through interpretable responsibility. That value is only credible if the routing metrics improve under the same evaluation protocol.

The forecast evidence is restricted to the current frozen evaluation split and artifact package. The text reports the completed neural leaderboard, and the table below provides the engineering baseline panel. The corrected-router seed table is reported in the routing-evidence section, where it supports the operating-regime alignment claim rather than a leaderboard claim.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_wtb_operational_baselines.tex}
```

![Summary of forecasting and routing outcomes. Panels A and B compress the learned-model error comparison for WTB and ERA5, with ERA5 persistence shown as a deterministic reference. In WTB, the displayed corrected comparator is the boundary-forced routing variant; the deeper full stack is reported separately. Panels C and D summarize routing agreement through NMI and ARI.](artifacts/final_evidence_package/export/figures/figure3_summary_results.pdf){ width=96% }

## Transition-window and regime-slice performance

The difficult slices repeat the same separation between forecasting accuracy and routing evidence. In the completed strict-mask baseline rows, Graph WaveNet reaches switch-window RMSE 228.12 +/- 3.23 and pitch-control RMSE 282.67 +/- 31.41. PatchTST reaches switch-window RMSE 231.22 +/- 4.15 and pitch-control RMSE 277.21 +/- 19.30. Graph Transformer reaches switch-window RMSE 237.06 +/- 5.78 and pitch-control RMSE 280.50 +/- 35.98, while GAT-GRU reaches switch-window RMSE 240.17 +/- 8.50 and pitch-control RMSE 318.28 +/- 49.88. Under the strict anchor-valid mask, the boundary-forced router reaches pitch-control RMSE 286.95 +/- 22.07 and switch-window RMSE 239.86 +/- 8.85. These slice results support a mechanism-evidence update, not a headline-error claim. ERA5 again favors persistence. Among learned ERA5 models, Graph WaveNet gives the lowest overall and switch-window RMSE, while physics-aligned routing improves over Unconstrained MoE in the transition slice without beating the dense model or persistence on headline error. This is calibration around a visible thermodynamic boundary, not broad forecast repair.

The slice evidence is therefore restricted to the frozen strict-mask rows and the boundary-slice audit below.

We therefore add a stricter boundary-slice audit directly from the saved strict-mask predictions and the strict cache physics. The audit isolates anchors within +/-1.0 m s$^{-1}$ of the rated-wind MPPT-to-pitch boundary and compares them with valid non-boundary MPPT/pitch anchors and with single-regime core slices. The boundary band is the hardest forecasting slice: RMSE is 321.17 +/- 21.31, which is 67.07 higher than the non-boundary valid slice (95% bootstrap interval 52.54 to 84.21), 67.46 higher than the MPPT core, and 50.01 higher than the pitch-control core. At the same time, the boundary band still carries mixed-regime routing structure, with NMI/ARI 0.6562 / 0.7766. This closes a narrower mechanism question: the strict-mask gate is not only globally aligned, but remains measurable at the operating boundary where prediction is hardest.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_boundary_slice.tex}
```

## Routing evidence

Routing recovery is the positive result. Across five ERA5 seeds, Unconstrained MoE keeps high expert-usage entropy but near-zero routing agreement, with NMI/ARI of 0.0317 +/- 0.0219 / 0.0253 +/- 0.0626. Physics-aligned MoE raises those scores to 0.2100 +/- 0.0972 / 0.2279 +/- 0.1296. This is a modest but useful correction because the ERA5 marker is already visible in the input state. WTB shows the stronger effect after the strict anchor-valid rerun: the boundary-forced router reaches gate-regime NMI/ARI of 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 across seeds 201--205. The previous weak seed-204 behavior disappears under the strict cache, with seed 204 reaching NMI/ARI 0.8591 / 0.9060. Explicit gate correction therefore recovers a physically meaningful partition in the control-confounded setting, while the result remains bounded to the tested WTB/ERA5 settings.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_seed_metrics.tex}
```

Anchor-only routing is not a straw baseline. A deterministic rule built from the physical anchor reaches slightly higher strict-test semantic agreement than the trainable boundary-forced router (NMI/ARI 0.8895/0.9219 versus 0.8716/0.9166), and it also has lower headline RMSE. The proposed model is therefore not claimed to be a better semantic rule in isolation. Its advantage is narrower: it keeps trainable MoE responsibility assignment coupled to the forecast and reserve evaluation, lowers strict pitch-control RMSE relative to anchor-only, and is much less brittle when boundary-anchor channels are corrupted. Under 0.5-standard-deviation boundary-anchor noise, anchor-only overall RMSE degradation is 105.56, whereas the trainable router degrades by 5.78. This is the answer to the rule-based-router concern: if a site only needs a fixed labeler, anchor-only is strong; if the gate must remain part of a forecast/reserve model under sensor noise and held-out turbine stress, trainable responsibility matters.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Anchor-only and rule-based router comparison on strict-mask WTB.}
\input{artifacts/final_evidence_package/export/tables/table_anchor_only_rule_router_main.tex}
\end{table}
```

The current WTB mechanism table above is the evidence source for the corrected router. ERA5 routing values are used only as the observability contrast already summarized in the text and artifact package.

Figure 4 makes the WTB repair visible in the operating plane. After correction, the dominant expert regions align with the MPPT and pitch-control structure, and the confusion matrices contract around the intended operating partition. The corrected gate becomes readable at the boundary that matters operationally, with the RMSE cost already quantified above.

![WTB routing diagnostics. Panel A maps the dominant expert in the $(Wspd, Pab_{mean})$ plane for the boundary-forced routing variant, with the sample cloud colored by physical operating regime. Panel B shows the binned gate redistribution against wind speed together with the mean pitch curve. Panels C and D compare the unconstrained and corrected confusion matrices.](artifacts/final_evidence_package/export/figures/figure4_routing_evidence.pdf){ width=97% }

Figure 5 traces the same contrast through time. In the WTB switch window, the boundary-forced router carries responsibility through the MPPT-to-pitch transition more coherently than the unconstrained gate. In ERA5, expert weights evolve with sensible heat flux and regime shading, as expected when the marker is already expressed in the state. The case studies tie the routing metrics to the physical mechanisms behind them.

![Dual case studies for correction and emergence. Panel A shows a local WTB switch window in which the boundary-forced routing variant remains stable while the dense and unconstrained models deviate more strongly near the MPPT-to-pitch transition; wind speed, pitch angle, and the dominant expert strip are plotted underneath. Panel B shows the ERA5 positive-control view, where sensible heat flux, regime shading, and expert weights evolve coherently over a selected week.](artifacts/final_evidence_package/export/figures/figure5_case_studies.pdf){ width=97% }

## Operational value and failure cases

The routing claim needs an energy-system consequence, not only a semantic score. A high gate NMI is useful only if it changes the tradeoff an operator actually sees in a transition window: how much reserve energy is carried, how often the scheduled reserve is violated, and how much shortage energy remains when the turbine crosses from MPPT into pitch control. The reserve diagnostic defined in the Method section applies that test to saved WTB validation and test predictions. It reports total cost, violation rate, reserve energy, and shortage energy across shortage-to-reserve cost ratios for four policies: Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin. The paired uncertainty check below is deliberately conservative and does not support a stable whole-sample reserve advantage over Graph WaveNet/global with five paired seeds. The reserve result should therefore be read through the boundary-window tradeoff, not as a full-sample policy win. Because the reserve levels are empirical shortfall quantiles from point forecasts, the table is also not a comparison to calibrated probabilistic, CRPS-scored, quantile-regression, scenario, or distributional reserve baselines.

These four policies answer different decisions and should not be ranked as substitute forecasters. Graph WaveNet/global is the low-RMSE system reference: one reserve quantile is calibrated for the whole sample, so it tests what a strong black-box forecaster can do without boundary stratification. Graph WaveNet/physical-bin keeps the same strong forecaster but calibrates reserve by physical operating bins, answering whether a simple physics-stratified reserve rule already captures the transition-window effect. Boundary router/global uses the higher-RMSE routed model with one global reserve quantile, isolating the cost of using the accountable router without gate-specific reserve allocation. Boundary router/gate-bin adds gate-conditioned reserve bins to that same routed model, so its only legitimate attribution question is whether the learned gate improves the same routed predictor's transition-window reserve tradeoff relative to its own global reserve rule.

At the main shortage-to-reserve cost ratio of 10, the full-sample result still favors Graph WaveNet/global as the system reference: its total cost is 464.07M normalized reserve-energy cost units with RMSE 225.74. The boundary-forced router has a 10.39 RMSE engineering tradeoff relative to that accuracy reference. Gate-bin reserve does not erase that tradeoff and does not become the preferred full-sample reserve rule: on the full sample it lowers same-model cost by carrying less reserve, but violation rises from 0.0857 to 0.1214 and shortage rises from 17.64M to 19.02M. The useful result is local and has the form of a reserve envelope. On boundary anchors, the boundary router/gate-bin policy lowers same-model total cost from 88.13M to 84.58M, violation from 0.1038 to 0.0900, and shortage from 3.73M to 3.19M, while reserve energy rises from 50.82M to 52.67M. The operational gain is therefore a 0.0138 absolute violation reduction and 0.54M lower boundary shortage, bought with 1.85M additional reserve energy. Graph WaveNet/physical-bin remains the strongest physics-stratified boundary baseline at 84.31M total cost and 3.40M shortage. Thus the gate-bin result is not an accuracy result; it is a boundary-window reserve allocation that buys lower shortage and fewer violations at a measured reserve-energy price.

```{=latex}
\begingroup
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\noindent\begin{minipage}{\linewidth}
\captionof*{table}{\textbf{Table.} Dispatch/reserve main table at shortage-to-reserve cost ratio 10.}
\input{artifacts/final_evidence_package/export/tables/table_dispatch_reserve_main.tex}
\end{minipage}
\par
\endgroup
```

The cost ratio gives the reserve audit its energy-system meaning. A ratio of 2 means that one unit of residual shortage is charged as two units of reserve energy, so the optimizer tolerates more shortage and selects the median shortfall quantile. Ratios 5 and 10 represent a moderate reliability preference, such as transition-window scheduling where shortage or imbalance is expensive enough to justify extra reserve but not so expensive that the safest global rule dominates every local allocation. Ratios 20 and 50 represent scarcity-aware dispatch, high imbalance penalties, or emergency reliability screening where the decision rule must prioritize very low violation and shortage rates over local cost savings. Under this reading, the win/loss boundary is explicit. At ratio 2, the selected reserve quantile is 0.50 and the gate-bin boundary policy does not buy reserve. At ratios 5 and 10, gate-bin is usable relative to the same model's global reserve because it reduces boundary shortage and violation while carrying more reserve. At ratio 20, the benefit narrows into a cost-only tradeoff: shortage falls slightly but violation is effectively unchanged. At ratio 50, gate-bin falls outside the acceptable region because the same-model global policy is safer and cheaper. The gate is therefore a conditional reserve-allocation signal around the MPPT-to-pitch boundary, not a replacement for unit commitment, market clearing, or system-level stochastic reserve optimization.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Energy-system interpretation of shortage-to-reserve cost ratios.}
\input{artifacts/final_evidence_package/export/tables/table_cost_ratio_energy_system_assumptions.tex}
\end{table}
```

The validation-selected quantiles are also checked on held-out coverage. At ratio 10, all four displayed policies select an average target coverage near 0.90, but realized coverage differs by subset and policy. The boundary router/gate-bin policy is closest to the target on boundary anchors, with realized coverage 0.910 and violation 0.0900, whereas its full-sample realized coverage falls to 0.879 and exposes the same full-sample risk noted above. This table is a reliability diagnostic for the reserve rule; it is not a calibrated distributional forecast, and it does not replace comparisons to quantile-regression or scenario-based reserve methods.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Held-out coverage check for validation-selected reserve quantiles at shortage-to-reserve cost ratio 10.}
\input{artifacts/final_evidence_package/export/tables/table_reserve_coverage_reliability.tex}
\end{table}
```

Two post-hoc sensitivity checks make the reserve boundary more explicit. First, the boundary router/gate-bin rule is re-read on cell-level horizon and time-of-day slices using validation-frozen empirical shortfall quantiles. The late horizon bucket carries the largest residual shortage and violation rate, and the 12:00--18:00 anchor-index proxy bucket is also riskier than the night/evening buckets. The time-of-day labels use the WTB 10 min anchor index modulo 144 rather than a farm-local market clock, so they are a diagnostic proxy only. Second, a horizon-specific empirical-quantile what-if recalibrates empirical quantiles by horizon bucket without training a quantile model. It lowers residual shortage in both Graph WaveNet and routed rows, which shows that the pooled-horizon reserve rule is sensitive to lead-time calibration. This supports adding trained quantile-regression, CRPS-scored distributional, or scenario reserve baselines in future work; it does not strengthen the main gate-bin policy claim.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Post-hoc horizon and time-of-day reserve sensitivity for the boundary router/gate-bin policy at shortage-to-reserve cost ratio 10.}
\input{artifacts/final_evidence_package/export/tables/table_reserve_horizon_time_sensitivity.tex}
\end{table}
```

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Horizon-specific empirical-quantile what-if. This recalibrates empirical shortfall quantiles by horizon bucket without training a probabilistic forecaster.}
\input{artifacts/final_evidence_package/export/tables/table_reserve_horizon_quantile_whatif.tex}
\end{table}
```

The same result can be read as a system-value envelope. The gate-bin policy is reserve-active only when the shortage penalty is high enough to make boundary shortages matter but not so high that the safer global policy dominates. In this experiment, that usable range is the moderate cost-ratio interval 5--10 because both endpoints show the same operational pattern: fewer boundary violations and less boundary shortage, bought with a finite increase in reserve energy. At ratio 5, the gate-bin policy lowers same-model boundary cost by 1.95M, violation by 0.0170, and shortage by 0.82M, while adding 2.17M reserve energy. At ratio 10, it lowers same-model boundary cost by 3.55M, violation by 0.0138, and shortage by 0.54M, while adding 1.85M reserve energy. At ratio 20 the benefit is no longer a clear reliability gain, and at ratio 50 the gate-bin policy is outside the acceptable region because it raises cost, violation, and shortage relative to the same-model global policy. This is the system claim: the gate marks a transition-window reserve tradeoff region, not a universally preferred reserve controller.

```{=latex}
\begingroup
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\noindent\begin{minipage}{\linewidth}
\captionof*{table}{\textbf{Table.} Boundary-window reserve value envelope for the gate-bin policy. Positive reserve means additional reserve energy relative to the same routed model with a global reserve rule.}
\input{artifacts/final_evidence_package/export/tables/table_system_value_envelope.tex}
\end{minipage}
\par
\endgroup
```

We also export operator-facing slices that are closer to reserve desk language than the aggregate boundary/non-boundary split. The four slices are MPPT-to-pitch transitions, pitch-to-MPPT transitions, validation-calibrated high absolute ramp, and validation-calibrated low absolute ramp. For the boundary-forced router, gate-bin reserve reduces violation and shortage energy in the MPPT-to-pitch slice relative to the same model's global policy, but it pays an added reserve-cost price: 17.93M total cost, 0.1027 violation rate, and 0.69M shortage energy, compared with 16.33M, 0.1124, and 0.77M under global reserve. The low-ramp slice shows the cleaner cost/risk improvement, with gate-bin total cost 10.73M versus 11.24M and shortage energy 0.40M versus 0.44M. The pitch-to-MPPT and high-ramp slices are not gate-bin wins. In the high-ramp slice, gate-bin reserve reduces total cost slightly but raises violation from 0.0766 to 0.1253 and shortage energy from 1.06M to 2.51M because it carries much less reserve energy. This is why the reserve claim remains a boundary-window decision diagnostic rather than a global reserve-policy claim.

The operational decision curve puts the RMSE penalty and reserve-risk tradeoff in one view. It overlays boundary-window shortage energy across cost ratios with the boundary router/gate-bin reserve energy and its fixed RMSE penalty relative to Graph WaveNet/global. The higher-RMSE routed model is considered only for a transition-window reserve decision and only inside the envelope where fewer boundary shortages and violations are worth the extra reserve. Outside that envelope, the lower-RMSE Graph WaveNet/global or Graph WaveNet/physical-bin policy remains the more appropriate system reference.

![Operator-facing workflow for the reserve audit. SCADA fields define the local operating boundary, the boundary router assigns MPPT-to-pitch responsibility, the reserve-bin policy is calibrated on validation shortfall and frozen before test, and the reported outputs are cost, violation, reserve energy, and shortage energy.](artifacts/final_evidence_package/export/figures/boundary_reserve_system_workflow.png){ width=94% }

![Operational decision curve for the WTB boundary window. The chart places the boundary router's RMSE penalty against Graph WaveNet/global beside reserve energy and shortage-energy changes across shortage-to-reserve cost ratios. The figure explains the restricted decision logic: the routed model is not chosen for average error, but examined for a boundary-window reserve tradeoff that is acceptable only in the moderate cost-ratio envelope.](artifacts/final_evidence_package/export/figures/operational_decision_curve.png){ width=92% }

The three operational cases in the next table are included to prevent a common misreading. A correct gate can help allocate attention around the MPPT-to-pitch boundary, but it can also be misleading when the downstream forecast is bad or when a low-reserve gate-bin policy is applied to high-ramp windows.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table.} Operator-facing cases: when the boundary gate helps and when it misleads.}
\input{artifacts/final_evidence_package/export/tables/table_operational_case_explanation.tex}
\end{table}
```

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Boundary-window operational reserve slices at shortage-to-reserve cost ratio 10.}
\resizebox{\linewidth}{!}{%
\input{artifacts/final_evidence_package/export/tables/reserve_decision_boundary_slices.tex}
}
\end{table}
```

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Boundary-window cost-ratio sensitivity in reserve-system language.}
\input{artifacts/final_evidence_package/export/tables/table_cost_ratio_sensitivity_readable.tex}
\end{table}
```

The paired uncertainty table is intentionally conservative. It compares full-sample reserve outcomes against Graph WaveNet/global using seed-paired differences with bootstrap intervals and a sign-permutation check. These rows do not show a stable whole-sample cost advantage for the routed policies; the intervals are wide with five seeds. The reserve benefit is therefore the boundary-window operational pattern above, while the whole-sample comparison remains a diagnostic check.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Paired uncertainty for full-sample reserve metrics versus Graph WaveNet/global.}
\input{artifacts/final_evidence_package/export/tables/table_reserve_paired_statistics.tex}
\end{table}
```

Lead-lag analysis gives the same operational boundary. Around physical regime switches, the corrected gate matches the new regime at rate 0.4066 six steps before the switch and 0.3636 three steps before it, then rises to 0.8008 at the switch and remains 0.6313/0.6094 three/six steps after it. This pattern supports state detection at the transition, not a lead-time alarm. The reserve experiment should therefore be framed as boundary-aware reserve/ramp-risk conditioning after the boundary is expressed in the state.

The reviewer-statistics pack reports the complementary failure mode. It contains 24 gate-correct high-error cases and 24 boundary gate-correct high-error cases, and the full lists are retained in the supplement. These rows are important because they separate the two parts of the model. In those samples, the router assigns the sample to the physically appropriate operating regime, but the expert forecast is still numerically poor. The usual pattern is a value-map failure near high-error boundary windows, not a collapse of mechanism responsibility. We therefore treat these cases as evidence for the paper's boundary condition: correct routing is necessary for mechanism interpretation, but it is not sufficient for accurate power prediction.

## Spatial and future holdout stress tests

The spatial holdout tests whether the routing evidence survives when entire turbines are unavailable during training and validation. The east-node protocol holds out 27 of 134 turbines (20.15%). During training and validation, target and regime-valid entries for holdout nodes are masked; during testing, train-node targets are masked and evaluation is restricted to the held-out nodes. The protocol records `mask_policy_pass = true`, zero strict-anchor violations, 15/15 completed runs, and a passed mechanism gate. In this harder within-farm spatial transfer setting, the boundary-forced router reaches overall RMSE 233.87 +/- 2.84, switch-window RMSE 234.87 +/- 2.33, and NMI/ARI 0.8340 +/- 0.0958 / 0.8829 +/- 0.0875. Context-supervised routing is more accurate but less semantically aligned, with NMI/ARI 0.7479 +/- 0.0461 / 0.8084 +/- 0.0717. Anchor-only routing is semantically strong but less stable. The spatial intervention audit keeps the same interpretation as the in-sample strict-mask mechanism test: boundary-anchor removal causes a large NMI/ARI loss and a positive RMSE penalty, while wake-anchor removal remains near-null. This is not an out-of-site wind-farm result; it is a within-farm node-held-out stress test that checks whether the learned routing semantics extrapolate to unseen turbines.

The future-period holdout uses a pre-specified later WTB period with seeds 301--305 and evaluates only the holdout split. All 5/5 runs complete, the mechanism gate passes, and the downstream holdout mechanism intervention, placebo, boundary-slice, and reviewer statistics packs are present. The boundary-forced router reaches holdout overall RMSE 235.49 +/- 7.19, switch-window RMSE 239.93 +/- 7.27, and NMI/ARI 0.8352 +/- 0.0669 / 0.8870 +/- 0.0669. This pre-specified future holdout is the main temporal stress evidence. The later post-hoc time-forward slice in the next robustness block is used only as failure analysis for distribution shift. Together with the spatial holdout, the future holdout supports a bounded claim: the evidence is within-farm spatial and temporal stress validation of routing semantics, not a value-prediction guarantee and not evidence that the rule carries to a different wind farm without local testing. The holdout summaries are retained as source-trace evidence in the final manifest rather than re-input from the older goal-table directory.

We add a positive deployment-drill result at exactly the level supported by the evidence. The drill is not Kelmarsh/Penmanshiel transfer and it does not undo the external failure reported below. It asks whether a deployable workflow can be executed inside WTB under stricter separation: use a small calibration window to select rated wind, pitch threshold, boundary support, and the gate-to-regime map; freeze those choices; then evaluate held-out routing once. In the future-period proxy, a 2-day calibration window followed by the future holdout passes in all 5/5 seeds, with mean held-out NMI/ARI 0.8397/0.8907 and balanced accuracy 0.9770. In the east-turbine proxy, a 7-day calibration window on held-out turbines also passes in all 5/5 seeds, with mean held-out NMI/ARI 0.8272/0.8781 and balanced accuracy 0.9709. The 2-day and 7-day windows are WTB proxy settings, not universal minimum durations for a new farm. The result proves an operational procedure inside the WTB envelope: local calibration window -> boundary re-estimation -> frozen held-out routing test. It does not prove that the WTB rule migrates to a new farm.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Quasi-external deployment drill inside WTB: calibration-only boundary/gate-map selection followed by held-out testing.}
\input{artifacts/final_evidence_package/export/tables/table_quasi_external_deployment_drill.tex}
\end{table}
```

This drill also defines the operator-facing usability checks. Threshold choice is restricted to a pre-specified local grid and must be frozen before the held-out test. Calibration support is checked by the number of valid boundary cells, not only by elapsed days. The effective minimum calibration window is therefore governed by boundary-cell support, pitch observability or a validated pitch proxy, and a frozen held-out routing criterion. If pitch channels are missing, the site may use a documented pitch proxy only after showing overlap with wind speed, active power, and availability masks; otherwise the gate cannot be given a physical-router interpretation. If rated wind differs across turbine models, the rated-wind grid is estimated locally rather than copied from WTB. If SCADA gaps or availability masks remove too many boundary cells, the output is a data-coverage failure, not a weak positive site result. Finally, reserve use requires a separate high-ramp slice check because the gate-bin rule can reduce total cost by carrying too little reserve in ramp-heavy windows.

## Ablation

The WTB ablation exposes a controllable accuracy-semantics frontier. The completed strict-mask 50-run ablation covers dense, unconstrained, balance-only, align-only, balance-align, boundary-forced, smoothed boundary-forced, context-aligned, anchor-only, and full variants across seeds 201--205, with the routing-control mechanism check passed for the three routing variants. The reading is deliberately paired: every ablation row must report RMSE together with NMI/ARI. With load balancing, regime alignment, and boundary forcing active, the selected corrected router reaches NMI/ARI 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371. Boundary forcing remains an interpretability intervention with a measured forecasting price rather than a free accuracy improvement.

The ablation claim is therefore the shape of the frontier, not a ranking headline. The current strict-mask artifact records 50/50 expected runs complete and 15/15 routing-gate checked runs passed; the paper uses that record to keep the ablation as evidence for the RMSE/NMI tradeoff.

Figure 6 visualizes this frontier. Unconstrained MoE sits in the low-semantics region. $L_{align}$ moves the gate sharply upward with a modest RMSE change. The force/smooth variants continue toward cleaner partitions while moving rightward on RMSE. The full physics-aligned MoE is the routed forecasting compromise; the boundary-forced variants occupy the semantic-repair end of the frontier.

![WTB accuracy-semantics tradeoff across routing variants. Circles show NMI and squares show ARI against overall RMSE. The frontier clarifies that stronger routing correction improves gate-regime agreement but can move the model away from the lowest forecast error.](artifacts/final_evidence_package/export/figures/figure6_ablation_tradeoff.pdf){ width=82% }

## Robustness and fairness checks

The stress and fairness checks rule out two easy explanations for the WTB result. The in-family comparisons use multiple strict-mask seeds, and the routed in-family variants share the same parameter count, making a pure capacity explanation unlikely. The completed baseline refresh sharpens the forecasting check: Graph WaveNet is lower than the boundary-forced router by about 10.39 RMSE on average, PatchTST is lower by about 8.06 RMSE, and Graph Transformer and GAT-GRU are close in error but do not change the routing-semantics result. The evidence supports the same qualitative reading as the mechanism tables: the method earns its value through gate-regime responsibility, not headline error dominance. The corresponding ERA5 RMSE difference between physics-aligned MoE and the dense encoder is small and uncertain, about 0.009 (-0.061 to 0.085), and the expanded ERA5 baseline panel shows that even the lowest-RMSE learned baseline still trails persistence. The compute-cost table adds one more constraint: PatchTST is fastest, Graph WaveNet is slower but has the lowest strict-mask RMSE, and the routed models sit between them with about 110k trainable parameters and 13--14 s evaluation time for the strict test windows. These checks therefore support the routing-semantics claim and keep the accuracy and operating-scope claims bounded.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Parameters, training cost, and inference speed on strict-mask WTB runs.}
\input{artifacts/final_evidence_package/export/tables/table_compute_deployment_cost.tex}
\end{table}
```

The strict replay, intervention, placebo, and time-forward tables below are the current stress evidence for the corrected-router claim.

We also add negative-control and intervention audits for the strict-mask WTB gate. The five-seed strict-mask set compares the actual operating labels with labels that should not preserve the MPPT-to-pitch boundary: an 18-step temporal shift, a one-day temporal shift, node permutation, within-time node shuffling, and global label shuffling. The boundary-forced router keeps high agreement with the actual labels (NMI/ARI 0.8716 +/- 0.0374 / 0.9166 +/- 0.0332 in the placebo summary). Actual labels exceed global shuffling by delta NMI/ARI 0.8716 / 0.9166, one-day temporal shift by 0.8324 / 0.8656, and node permutation by 0.3289 / 0.2825; all bootstrap intervals are positive. The per-seed placebo table shows that this separation is not carried by one lucky run: all five seeds retain large actual-vs-global and actual-vs-one-day-shift gaps. Spatial placebos remain partially aligned because turbines share fleet-level operating distributions, but the actual labels are still clearly separated.

The mechanism intervention gives the stronger test. Reloaded strict-mask checkpoints match their saved metrics for all five runs before intervention. Zeroing the boundary anchor raises overall RMSE by 2.6792 (95% bootstrap interval 0.7347 to 4.5598), raises switch-window RMSE by 2.9470 (0.7985 to 5.1213), and drops NMI/ARI by 0.7017 / 0.8593. The per-seed intervention table sharpens the interpretation. Boundary-anchor removal collapses NMI/ARI in every seed, but the RMSE penalty is heterogeneous: seeds 202 and 205 show near-zero or slightly negative RMSE deltas while still losing most of their routing agreement. The mechanism claim is therefore about gate responsibility, not an assertion that removing the anchor always worsens headline error. Zeroing the wake score is a near-null control: overall RMSE changes by 0.0031 (-0.0016 to 0.0110), and NMI/ARI drop by about 0.0010 / 0.0010. This moves the WTB claim beyond correlation or visualization: the gate depends on the intended boundary anchor, not on any arbitrary physical channel.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_mechanism_effects.tex}
```

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_placebo_effects.tex}
```

The same evidence stack is traceable to the exported source-data files in \path{artifacts/final_evidence_package/export}, including per-seed CSV files, protocol records, and SHA256 manifests.

## Time-forward stress test

A post-hoc time-forward test-slice audit asks whether the strict-mask evidence survives later test windows. The answer is split. Routing semantics remain stable: in the late test block, the corrected router keeps NMI/ARI 0.8661 +/- 0.0393 / 0.9079 +/- 0.0364, and late-minus-early NMI is +0.0068 with a 95% bootstrap interval from 0.0021 to 0.0127. Forecasting accuracy, however, worsens in the late block. Late-minus-early overall RMSE is +50.3454 (46.8137 to 54.1758), and switch-window RMSE is +63.3549 (60.7291 to 65.3319). The added distribution-shift diagnostics explain this as a boundary condition: the late block has higher mean target power (+52.70), a large regime-share shift (total variation 0.2983, Jensen-Shannon divergence 0.0539), lower mask-valid coverage (-0.1446), and a lower mean wind-speed anchor (-0.3028) but much larger pitch action (+13.9845 in mean Pab). The gate still tracks the physical partition, but the value map faces a different operating distribution. This audit therefore supports a routing-semantics claim while weakening any time-stable forecasting claim. It is a stress test on saved test predictions, not a replacement for an external dataset or a pre-specified future-period holdout.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_late_shift_diagnostics.tex}
```

## Sensitivity checks

Table 8 tests whether WTB routing recovery depends on a single hand-picked boundary or one large loss weight. Across three-seed sweeps, changing $\lambda_{\mathrm{align}}$ from 2500 to 7500 keeps NMI in the 0.8255--0.8546 range, and changing $\lambda_{\mathrm{force}}$ from 5000 to 15000 keeps NMI in the 0.8091--0.8406 range. The label-validity audit then re-labels the saved strict-mask gate outputs over the local grid rated-wind $\{10.0,10.5,11.0\}$ and pitch-threshold $\{1.5,2.0,2.5\}$ without retraining. The worst grid point still has NMI/ARI 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377, and the minimum shared-valid support is 0.9909. This is a local rated-wind/pitch robustness readout, not a system-wide threshold sweep: $u_{\mathrm{idle}}$, wake-score thresholds, turbine-specific control curves, and wider rated-wind/pitch grids remain untested. These rows are threshold/label validity checks and mask controls, not the semantic negative control. The semantic negative-control claim is reserved for `boundary_negative_controls_wtb` and the routing placebo audit, where deliberately incorrect or shifted labels are checked against the same intervention evidence. The main WTB result keeps the pre-specified operating-boundary rule.

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} WTB threshold/label validity audit for saved strict-mask gate outputs.}
\input{artifacts/final_evidence_package/export/tables/table_threshold_label_validity.tex}
\end{table}
```

The external Kelmarsh/Penmanshiel result is a failed boundary-condition test, and this negative result is one of the contributions of the paper. The source audit completes 80/80 runs, including both leave-one-farm-out directions and chronological checks, and it asks whether the default WTB operating boundary can be read on external farms. It cannot: the default WTB boundary gives mean routing NMI 0.4877, below the pre-specified 0.50 external-site routing criterion. The external farms show that an operating-boundary rule cannot be reused before local observability and boundary support are checked. In deployment terms, this is a fail-fast safety gate rather than a hidden generalization claim: if the local boundary cannot be recovered on held-out data, the router must be treated as a diagnostic warning and not as a reserve-control signal. We add validation-only local recalibration only to explain that failure mode. For each routing run, the validation gate output selects a farm-specific rated-wind/pitch-threshold pair from the pre-specified grid, and that selected boundary is evaluated once on the test gate output. This does not retrain the forecaster and does not rescue an out-of-site mechanism claim. Overall default test NMI rises only from 0.1324 to 0.1491 after recalibration, a recovery of +0.0167. Kelmarsh chronological runs recover more agreement, but Penmanshiel chronological and the leave-one-farm-out settings remain weak, so the failure is not merely a shifted threshold. The postmortem points to concrete boundary conditions rather than an unexplained error: pitch/proxy coverage differs from WTB, effective boundary cells can be sparse, control-state shares are imbalanced, farm scale and layout are smaller, turbine types and power curves differ, and the available sensor fields do not recreate the WTB anchor set. The practical message is protective: the boundary diagnostic prevents misdeployment when sensor fields, turbine geometry, or regime support do not match the WTB operating envelope.

The small calibration-window adaptation makes that boundary sharper. This 40/40 diagnostic is a second external test, separate from the WTB proxy drill: using only each external run's validation gate outputs, it selects a local rated-wind/pitch pair and a majority-vote gate-to-regime map, then freezes both before evaluating held-out test gates. Chronological adapted balanced accuracy averages 0.4787, below the 0.50 diagnostic threshold. Penmanshiel chronological improves from 0.4000 to about 0.5000 balanced accuracy, but its adapted NMI remains 0.0000; Kelmarsh chronological declines, and the leave-one-farm-out Penmanshiel-to-Kelmarsh setting collapses. Therefore none of the external farms clears the positive held-out routing criterion after local calibration. The result is a completed negative adaptation diagnostic: local boundary estimation is necessary, but this small window is not sufficient to recover usable routing at a new site.

The failure conditions are operationally informative. Kelmarsh has 6 Senvion MM92 turbines, whereas Penmanshiel has 14 retained Senvion MM82 turbines. Pitch-feature coverage and boundary support differ sharply, especially in leave-one-farm-out caches, and the regime shares move from WTB's 39.47% idle, 52.00% MPPT, and 8.53% pitch-control partition to Kelmarsh's MPPT-heavy chronological partition and Penmanshiel's larger pitch-control share. These differences in sensor fields, pitch observability, turbine geometry, farm scale, power-curve distribution, and label balance are exactly the conditions under which the WTB operating-boundary rule must be re-estimated and tested before any site-level claim.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Why external wind-farm boundary transfer failed and how the result is used.}
\input{artifacts/final_evidence_package/export/tables/table_external_site_transfer_failure.tex}
\end{table}
```

## Local evidence protocol for a new wind farm

The external failure leads to a local evidence protocol rather than a site-transfer claim. A new wind farm must pass three evidence gates before the router can be interpreted physically. First, the site must pass a pitch-observability gate: wind speed, active power, turbine status or availability masks, and pitch-related channels must be present with enough valid overlap to construct MPPT and pitch-control labels. The minimum calibration window is not a transferable number of days. It is the smallest pre-declared window that contains enough effective boundary cells, pitch observability or a validated pitch proxy, and a frozen held-out routing check; if pitch is sparse, the window must be extended until those conditions are met. If mean pitch, blade-pitch channels, or a reliable pitch proxy are absent in the intended operating window, the boundary label is not identifiable and the router remains a statistical diagnostic.

Second, the site must pass a local-boundary-support gate. Rated wind speed, pitch threshold, boundary band, and gate-to-regime map must be re-estimated on a local calibration period, then frozen before held-out testing; selecting them on the test period would convert the protocol into a retrospective explanation. The calibration period must contain enough boundary cells, not only idle or MPPT-heavy operation. If local support is too sparse, the result may still be reported as a data-coverage diagnostic, but the WTB-derived boundary rule must not be reused as a physical explanation.

Third, the site must pass a held-out routing criterion before the gate is interpreted as a physical boundary signal. The frozen gate-to-regime map, rated-wind threshold, pitch threshold, and boundary band must clear held-out NMI >= 0.50 and balanced accuracy >= 0.50, or a stricter site-specific criterion declared before test evaluation. The local idle/MPPT/pitch shares should also be compared with the WTB operating envelope, and transition-window shortage, violation rate, reserve energy, and high-ramp slices must be recomputed before any gate-bin reserve rule is used. A new site passes the protocol only if the held-out gate clears the pre-specified routing criterion and the reserve audit improves shortage and violations in the intended transition window at an acceptable reserve-energy cost. If any gate fails, the result remains a boundary-condition diagnosis; physical routing interpretation, new-farm operating evidence, and gate-bin reserve use are not supported.

![New wind-farm evidence protocol. The protocol moves from sensor coverage to local boundary calibration, held-out routing, reserve audit, and finally bounded operating claims.](artifacts/final_evidence_package/export/figures/new_wind_farm_deployment_checklist.png){ width=94% }

# Discussion

The main result is a rule for using physics-aligned routing in wind-power operations: correction strength should scale with regime observability and with the operating decision that will consume the gate. ERA5 already exposes the regime marker through sensible heat flux and its temporal variation, and persistence is hard to beat on RMSE. In that setting, the corrected gate improves regime alignment over Unconstrained MoE without creating a lower-error headline map. WTB is different. Wake interaction and blade-pitch control blur the MPPT-to-pitch boundary, so the router needs stronger repair to recover a useful partition. The WTB-ERA5 contrast is the paper's main scientific insight: the same routing prior has different value depending on how much of the physical boundary is already visible in the observations.

The price is explicit. Graph WaveNet is the most stable black-box WTB forecaster, while LightGBM and XGBoost lag-feature baselines show that simple engineering predictors remain highly competitive. Inside the routed family, the full physics-aligned MoE is the forecasting compromise, while the boundary-forced router is the semantic-repair variant. Regime-anchor alignment buys a large share of the partition recovery with a modest RMSE change. Boundary forcing buys a cleaner gate at a clear forecasting cost. That is the paper's practical claim: gate correction is a modeling choice with measurable error and reserve-policy tradeoffs.

For mechanism-aware forecasting studies, physics has to constrain the routing decision itself. Many physics-guided models act on outputs or latent states, which suits tasks where the goal is physical consistency after prediction. Here the decision is earlier: which local predictor takes responsibility near a mechanism change. The MPPT-to-pitch boundary is a physically meaningful stress point because it changes reserve shortage risk and ramp-risk interpretation even when fleet-level average error moves only modestly. Boundary-focused forcing encodes that stress point at the router. It sacrifices some RMSE to keep the gate from drifting into a semantically useless partition.

The method is appropriate when the operating boundary is part of the scientific question. Examples include turbine-control transitions, curtailment regimes, and geophysical stability states where the active mechanism matters, not only the scalar error. It is a poor choice for a pure leaderboard objective, for settings where persistence or a black-box graph model is already adequate, or for problems without a defensible regime anchor. In those cases, the extra routing losses add complexity without a clear mechanism-evidence return. The target use case is the middle ground: mechanism boundaries are important enough that interpretable responsibility can justify a measured error penalty. This positioning also explains why the strongest claim is about controlled responsibility assignment rather than broad cross-dataset superiority.

# Limitations

The WTB correction depends on threshold-based pseudo-labels derived from wind speed and mean pitch angle. Those same channels also appear in the gate anchor, so the method deliberately constrains the router to a declared operating boundary. The reported threshold audit re-labels saved gate outputs over a local rated-wind/pitch grid and the lambda sweep varies the two dominant routing weights, so the main result is not a single-point artifact. The coverage is still partial: it does not exhaust all anchor thresholds, loss weights, wake-score cutoffs, wake-cone parameters, or turbine-control settings. It also lacks retrained no-\texttt{Pab\_mean}, no-\texttt{Wspd}, lagged-\texttt{Pab\_mean}, and lagged-\texttt{Wspd} ablations. The method is boundary-aware regularized routing, not a fully learned operating-state discovery system, and it cannot separate observable-anchor responsibility from structure learned through other SCADA channels.

The active-power anchor has a strict timing requirement. `Patv` is allowed only as the historical/anchor-time active-power measurement available when the forecast is issued; future active power remains the supervised target. This is a defensible SCADA forecasting convention, but it is also a portability constraint and a possible source of interpretive circularity. The current intervention evidence zeroes the boundary-anchor input and shows that routing agreement collapses, but it is not a retrained no-`Patv` or lagged-`Patv` ablation. Taken together with the missing wind-speed and pitch ablations above, the present evidence cannot claim to identify which part of the gate is pitch/wind observability, active-power status, or structure learned after anchoring. If a deployment environment delays active-power telemetry, changes channel definitions, or evaluates a decision before the current active-power value is available, the Patv anchor must be removed or lagged and the leakage, intervention, and reserve diagnostics must be rerun.

The expert-regime language is tied to the implemented logit convention. The first primary-regime logits are fixed to the operating labels during supervised alignment, which prevents seed-wise permutation for those anchored meanings. That makes cross-seed MPPT/pitch statements interpretable, but only for the anchored logits and only under the declared mapping. Unassigned experts and wake auxiliary logits should not be overread as universal turbine states.

The comparison is bounded. Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, persistence, physical power curve, XGBoost/LightGBM lag features, and a DLinear-style LTSF readout provide completed strict-mask WTB forecasting baselines, and ERA5 is checked against persistence plus Graph WaveNet, STGCN, PatchTST, and TCN. The strict-anchor-mask rerun covers the selected WTB corrected router, replay, intervention, placebo, time-forward audits, a synchronized baseline refresh, a spatial node-held-out stress test, a future-period holdout, a quasi-external WTB deployment drill, and the transition-window reserve audit. Larger general time-series backbones, broader graph-transformer variants, trained quantile-regression baselines, and scenario/distributional forecasters are outside the present benchmark.

The reserve audit is deliberately narrower than power-system dispatch. The study does not implement unit commitment, market clearing, a full probabilistic prediction-to-reserve pipeline, real dispatch integration, or a closed-loop operator simulation. The audit is therefore a normalized proxy decision: fixed empirical quantile bins are calibrated on validation shortfall and tested once on held-out predictions, with costs reported in normalized reserve-energy units rather than money. It is useful for ranking boundary-window risk tradeoffs under declared cost ratios, but it is not a market-price, delivery-constrained, or security-constrained dispatch study.

External wind-farm diagnostics are complete but fail the external-site routing criterion. The Kelmarsh/Penmanshiel audit reaches 80/80 completed runs in both leave-one-farm-out directions, while the default WTB boundary remains below the declared threshold. The added local recalibration table records how much agreement is recovered when rated-wind/pitch boundaries are re-estimated on validation gates and then fixed on test gates. The quasi-external drill shows that the calibration-to-held-out workflow can pass inside WTB, but it does not change the external-farm conclusion. The external taxonomy points to farm scale, turbine geometry, pitch observability, sensor-field coverage, power-curve differences, and regime-label imbalance as the main boundary conditions. The evidence therefore supports within-WTB spatial and temporal stress validation of routing semantics and operating-boundary reserve diagnostics, plus an external diagnostic of when those semantics need local boundary re-estimation.

The time-forward audit is not an external validation. It is a post-hoc split of saved WTB test predictions into contiguous anchor-time blocks. It shows that the strict-mask gate keeps its physical partition in the late block, but it also shows a large late-test RMSE increase. The failure case is therefore explicit: late-period distribution shift preserves routing agreement while degrading value prediction. This is an important boundary condition: the method currently supports routing semantics, not time-stable forecasting accuracy.

The WTB ablation is scoped. The strict-mask 50-run ablation record is complete, but each cited row must report RMSE together with NMI/ARI. The ablation supports the observed accuracy-semantics tradeoff; it does not convert the routed model into the lowest-error predictor.

Statistical reliability is uneven across claim types. The completed strict-mask WTB baseline refresh provides five seeds each for Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST, and the selected boundary-forced router has five strict-mask seeds, five future-holdout seeds, and five seeds for each spatial-holdout routing comparator. ERA5 has five seeds for the in-family models and three seeds for the learned baselines. The quasi-external WTB deployment drill has five future-period seeds and five east-turbine seeds, but it remains a proxy workflow test. The engineering baselines and reserve-window audit are deterministic or sampled strict-mask diagnostics rather than five-seed neural families. Semantic negative controls are taken from `boundary_negative_controls_wtb`, and the mask/threshold sensitivity controls are reported as sensitivity checks only. The external Kelmarsh/Penmanshiel audit is complete at 80/80 but remains negative for new-site routing; the recalibration and small-calibration-window adaptation diagnostics are therefore reported as boundary-condition analyses, not as new training results or external-site evidence. The strongest statistical claims are therefore the strict-mask replay-safe routing-recovery, mechanism-intervention, failure-case transparency, and within-WTB spatial/temporal stress claims.

The paper studies two observability settings. WTB and ERA5 are enough for the intended contrast between weakly and strongly expressed regime markers, with ERA5 serving as a positive/contrast control rather than as the main performance contribution. Applying the same interpretation to other industrial or geophysical systems will require re-estimating the operating boundary, checking sensor availability, and rerunning the routing gate before making a local mechanism claim.

# Conclusion

This paper treats non-stationary wind-power modeling as a routing-interpretability problem around operating transitions. The completed strict-mask WTB comparison gives a blunt accuracy result: strong graph, transformer, and lag-feature baselines achieve lower mean RMSE than the boundary-forced routed model. The strict-anchor-mask evidence then tests the selected router more severely: across five seeds it recovers the operating partition, passes checkpoint replay, fails under boundary-anchor removal, survives placebo controls, remains meaningful under spatial and future-period holdouts, and keeps routing semantics in late test windows. The quasi-external WTB drill adds one positive operational procedure: a small calibration window can re-estimate the local boundary and gate map, freeze them, and pass a held-out future or held-out east-turbine test. This is within-WTB spatial and temporal stress evidence plus workflow evidence, not evidence for a new wind farm. ERA5 carries the same lesson as an observability contrast: when the regime marker is visible and persistence is strong, physics-aligned routing improves gate-regime agreement more than headline forecasting accuracy.

The practical conclusion follows directly. When the regime marker is visible, routing regularization calibrates an already available partition. When the marker is partly hidden by control logic, physics guidance at the gate can repair a weakly identified partition and provide a transition-window reserve/ramp-risk diagnostic, but it trades against forecast error and does not create a whole-sample reserve rule. Physical forecasting with multiple local response laws therefore needs supervision over responsibility as well as supervision over values. The completed external wind diagnostic shows that this responsibility claim must be re-established when turbine geometry, pitch observability, sensor fields, power curves, or label distributions change; a small validation-window adaptation did not clear the held-out routing criterion in Kelmarsh/Penmanshiel. The gate is part of the model's scientific claim, and the right question is whether that claim is worth its measured error, reserve, stress-test, and efficiency costs in the target operating setting. Until a new wind farm passes the local evidence protocol, the method should be described only as within-WTB operating-boundary interpretability plus external failure-boundary diagnosis plus transition-window reserve diagnosis.

# Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work, the authors used OpenAI ChatGPT/Codex to support language editing, consistency checking, and submission-material drafting. After using these tools, the authors reviewed and edited the content as needed and take full responsibility for the content of the published article.

# Code and data availability

The experiments use four public source families: the KDD Cup 2022 wind-farm SCADA benchmark, ERA5 reanalysis fields, and the Kelmarsh and Penmanshiel wind-farm SCADA records. Source datasets remain available from their original providers. The release package records provider links, checksums, and reconstruction scripts rather than redistributing any source files whose original terms require provider-side access. The Kelmarsh and Penmanshiel sources are tracked in the reproducibility manifest as CC-BY-4.0 source-data protocols; their completed 80-run audit, recalibration table, and small-calibration-window adaptation table are cited only as boundary-condition evidence because new-site reuse is not claimed. The final evidence export includes table, figure, source-data, protocol, and trace manifests; each manuscript table or figure is linked to source files, seed lists, run tables, raw prediction paths, checkpoint hashes, and SHA256 hashes where file size permits. The table, figure, and source-artifact indices in \path{artifacts/final_evidence_package/manifest/evidence_manifest_final.json} are the source/checksum authority for the manuscript artifacts, including the Applied Energy reserve diagnostics, bounded-claim table, quasi-external WTB deployment drill, and external-site diagnostics. The reproducibility manifest in \path{artifacts/reproducibility_manifest_final/reproducibility_manifest.json} reports 53/53 required files present, complete strict model weights, a recorded Python/CUDA environment, and no active experiment gaps. Code, configuration files, scripts, derived caches when licensing permits, model-weight/checkpoint hashes, seed-level CSV summaries, final figure source data, and evidence manifests can be released with the manuscript. Raw third-party data that cannot be redistributed will be accompanied by download instructions and rebuilding scripts. The one-command reproduction package rebuilds the strict evidence package, the engineering baseline panel, the transition-window reserve audit, the reserve protocol, the quasi-external WTB deployment drill, the external recalibration and small-calibration diagnostics, the final evidence manifest, and the reproducibility manifest with relative paths. The study uses turbine and atmospheric measurements only and involves no human participants or human-subject data.

# Appendix A. Training and implementation details

## Training loop summary

The optimization procedure is identical across runs except for the routing penalties that are activated in each setting and the anchor labels that are available.

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

## Shared constants

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A1.} Shared architecture, graph, and training constants used in the reported experiments.}
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

## Dataset-specific thresholds and routing weights

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A2.} Dataset-specific regime thresholds used to construct routing anchors.}
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
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A3.} Active routing-loss weights in the reported corrected models.}
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
