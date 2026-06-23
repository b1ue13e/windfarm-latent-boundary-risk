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
Wind turbine transitions from maximum power point tracking (MPPT) to blade-pitch control create concentrated reserve exposure that fleet-level forecasting accuracy metrics can miss: over-forecasts in this control window translate directly into unmet reserve requirements. We test whether supervisory control and data acquisition (SCADA) operating anchors can make a routed forecaster physically traceable enough for transition-window reserve diagnosis. The model uses a directed-diffusion gated recurrent unit with a node-level mixture-of-experts gate constrained by wind speed, blade-pitch angle, wake exposure, graph smoothness, and boundary-focused forcing. It is evaluated on the KDD Cup 2022 wind-farm SCADA benchmark (WTB), with ERA5 reanalysis retained as an observability contrast. At shortage-to-reserve cost ratio 10, gate-conditioned reserve binning reduces boundary-window violation rate from 10.38% to 9.00% and shortage energy from 3.73M to 3.19M normalized reserve-energy units relative to the same routed model with a global reserve rule, while carrying 1.85M additional reserve energy. The router recovers the MPPT-to-pitch operating partition with NMI/ARI of 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 across five WTB seeds, although Graph WaveNet remains the WTB accuracy reference (overall RMSE 225.74 +/- 2.60). Kelmarsh/Penmanshiel external-farm runs fail the pre-specified routing criterion after local recalibration. The result is therefore a within-WTB operating-boundary diagnostic for transition-window reserve risk, together with explicit sensor, boundary-support, and held-out-routing conditions for any new-site interpretation.

\vspace{0.25em}
\noindent{\small\textbf{Keywords:} Wind-power operations; operating boundary; reserve decision; mixture of experts; regime routing; spatio-temporal graph learning.\par}

\normalsize

\vspace{0.55em}

# Introduction

Reserve planning for wind-integrated power systems becomes most sensitive when a forecast error changes an operating decision rather than only a fleet-average error score. The maximum power point tracking (MPPT)-to-pitch transition is one such point. In the MPPT region, turbine power responds strongly to wind-speed variation; as pitch control activates near rated operation, the local power-response law changes and over-forecasts can become unmet reserve requirements. Because the transition occupies a smaller share of normal wind-farm operation, its effect can be diluted in whole-sample RMSE while still concentrating reserve exposure. A useful forecaster for this setting must therefore answer two questions together: how large is the error, and which control state generated the local response?

Spatio-temporal graph forecasters have reduced mean prediction error by modeling turbine coupling, wake interaction, and dynamic dependence [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @wu2020connecting]. Wind-specific graph and sensor-fusion models add wake structure, SCADA measurements, LiDAR, and offshore-layout information to improve physical relevance [@park2019physicsinduced; @yu2020sgnn; @kim2024lidarscada; @daenens2025offshore]. These models set the accuracy reference, but a low-error graph encoder does not by itself tell a reserve planner whether the current local map is MPPT-like or pitch-control-like. Mixture-of-experts (MoE) routing can separate heterogeneous response laws [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch; @shi2025timemoe], yet a gate trained only through prediction loss can specialize on partitions that have no operating meaning. The missing middle layer is an auditable routing assignment that identifies which physical response law is active at the anchor time and can then be used in reserve-risk diagnosis.

We make the routing decision itself the operating-boundary diagnostic. The model encodes local spatio-temporal context with a directed-diffusion GRU and uses a node-level MoE gate to allocate forecasts among local experts. Wind speed, mean blade-pitch angle, wake exposure, graph smoothness, and MPPT-to-pitch boundary forcing constrain the gate so that its assignment can be compared with the declared SCADA operating partition. WTB is the source control-boundary benchmark because the aerodynamic boundary is partly hidden inside turbine-control action; ERA5 is retained as an observability contrast where the thermodynamic marker is more directly visible through sensible heat flux. The recovered gate is then connected to a validation-calibrated, test-frozen reserve diagnostic that reports cost, violation rate, reserve energy, and shortage energy under declared shortage-to-reserve cost ratios.

This paper makes three contributions. First, gate-conditioned reserve binning turns the recovered operating assignment into a transition-window reserve diagnostic: at cost ratio 10 it reduces same-model boundary-window violation from 10.38% to 9.00% and shortage energy from 3.73M to 3.19M normalized units, while adding 1.85M reserve energy. Second, SCADA-anchored routing recovers the WTB MPPT-to-pitch partition with NMI/ARI of 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 across five seeds, and the agreement collapses under boundary-anchor removal while surviving placebo, spatial-holdout, and future-period stress checks. Third, the Kelmarsh/Penmanshiel external audit is reported as a deployment-safety result: it fails the pre-specified held-out routing criterion and identifies the sensor coverage, pitch observability, turbine geometry, and boundary-support conditions that must be locally verified before a new wind farm can use a gate-bin reserve rule.

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting has moved from single-site point prediction toward models that encode non-stationary weather, wake interaction, turbine coupling, ramps, and uncertainty information [@pinson2013forecasting; @gallego2015rampreview; @yang2025windprocess; @wang2025uncertaintyreview; @haq2025windreview]. Diffusion convolution, graph convolution, adaptive graph learning, and attention-based graph encoders provide strong references for spatial dependence across turbines or grid cells [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @wu2020connecting]. Wind-specific studies further use wake-aware graphs, SCADA fields, LiDAR, and offshore layouts to make that dependence physically meaningful [@park2019physicsinduced; @yu2020sgnn; @kim2024lidarscada; @daenens2025offshore]. These lines of work define the low-error baseline for this paper. Their remaining blind spot is operational rather than architectural: average accuracy does not identify the control-transition samples where reserve exposure is concentrated. Addressing that blind spot requires the routing assignment itself to carry operating-state meaning.

## Operating regimes, SCADA observability, and physical interpretability

Regime-aware modeling separates local response laws, but its value depends on whether the separation is physically interpretable. Early adaptive and hierarchical MoE models assigned inputs to local experts [@jacobs1991adaptive; @jordan1994hierarchical], and sparse modern MoE systems made routing scalable while exposing collapse, starvation, and load-allocation instability as practical risks [@shazeer2017outrageously; @fedus2022switch]. Recent sequence models bring the same specialization idea into time-series forecasting [@shi2025timemoe; @cao2026ecto; @tian2026arrow]. Physics-guided learning supplies the complementary principle that domain knowledge can constrain features, architectures, losses, probabilities, or post-hoc checks [@karpatne2017tgds; @read2019pgdl; @raissi2019pinn; @karniadakis2021piml; @zehtabiyan2023physicsguided; @parsa2025pimlreview; @gao2025physicsconstrained]. For wind turbines, the key observability issue is practical: operating-state labels depend on wind speed, pitch channels, active power, status masks, and turbine-specific power curves [@tautzweinert2017scada; @zhou2024sdwpfdata]. This paper differs from output-constrained physics-guided models by constraining the routing decision itself--the assignment of an operating instant to a local predictor--so downstream reserve logic can consume a physically traceable gate.

## Forecast-driven reserve allocation and risk diagnostics

Forecast value in power systems is realized through reserve, commitment, balancing, and trading decisions. Reserve studies show that variable generation changes operating-reserve requirements and that reserve demand should reflect uncertainty rather than a fixed margin [@doherty2005reserve; @ela2011operatingreserves]. Probabilistic and quantile wind-forecasting studies provide the statistical bridge from point predictions to decision risk [@bremnes2004quantile; @nielsen2006quantile; @zhang2014probabilisticreview; @wang2025uncertaintyreview], while trading and market studies connect forecast uncertainty to imbalance exposure and operating cost [@pinson2007trading; @wang2011unitcommitment; @zhou2013probabilisticmarkets]. This literature usually asks how much reserve should be carried given a forecast or uncertainty estimate. The present work asks the earlier diagnostic question: can the model identify the operating window in which reserve exposure is concentrated? That framing makes the reserve audit complementary to probabilistic dispatch and market-clearing studies rather than a substitute for them.

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

The gate is not supervised everywhere. It is anchored where the physical interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularization. This engineering layer defines what counts as a control regime and when that regime is observable from the data.

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

This makes the routing stack an anchor-constrained diagnostic, not an unsupervised operating-state discovery method. In WTB, `Wspd` and `Pab_mean` appear both in the gate anchor and in the pseudo-label rule used for alignment, so high gate-regime agreement should be read as evidence that the implemented router obeys a declared operating boundary. It does not prove that the boundary would be recovered from unrelated SCADA channels. The same caution applies to `Patv`: the current value is an issue-time status input, but without a retrained no-`Patv` or lagged-`Patv` ablation the evidence cannot separate how much of the gate comes from active-power telemetry versus wind-speed and pitch information. The result therefore supports auditable responsibility under the declared anchor set, not anchor-free regime discovery.

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

The cost ratio $\rho$ is an energy-system assumption rather than an abstract tuning knob. If the marginal cost of carrying one unit of reserve energy is $C_r$, then $\rho=10$ means that one unit of residual shortage is charged as $10C_r$. Ratios 5--10 represent moderate reliability settings such as transition-window scheduling or imbalance screening; ratios 20--50 represent scarcity-aware or emergency screening where shortage avoidance dominates local cost savings. Four policies are evaluated under this protocol: Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin. Only same-model global comparisons are used to attribute gate-bin reserve effects to the learned router. Graph WaveNet/global remains the full-sample low-RMSE system reference, and Graph WaveNet/physical-bin remains the simple physical-stratification baseline that tests how much can be gained without learned gates.

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

The second layer tests the RMSE price against stronger and more engineering-facing baselines. Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST are included for WTB, together with deterministic persistence, a fitted physical power-curve baseline, XGBoost and LightGBM lag-feature predictors, and a DLinear-style LTSF baseline. Graph WaveNet, STGCN, PatchTST, TCN, and a deterministic persistence predictor are included for ERA5. This split avoids using one comparison for two different claims. The in-family layer tests whether physical routing changes the learned partition under a fixed backbone. The baseline layer tests whether the routing intervention remains honest about forecast error when compared with established temporal, graph, and engineering predictors.

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

# Results and Discussion

## Forecasting Accuracy: Establishing the Baseline

Strong graph and lag-feature baselines establish an accuracy ceiling that the physics-constrained router does not match. Graph WaveNet reaches overall RMSE 225.74 +/- 2.60 on WTB, and LightGBM/XGBoost lag-feature baselines are similarly competitive at overall RMSE 227.12 and 227.88. The boundary-forced router reaches overall RMSE 236.13 +/- 8.41, a 10.39-unit penalty relative to Graph WaveNet. This gap quantifies the main engineering tradeoff: the router is not selected for whole-sample error minimization, but for accountable state assignment at an operating boundary.

ERA5 reinforces the same distinction. Persistence is the strongest headline reference, while Graph WaveNet is the lowest-RMSE learned model. Physics-aligned routing improves regime agreement relative to an unconstrained MoE, but it does not turn the learned model into the lowest-error ERA5 predictor. The forecasting results therefore set the terms for the rest of the article: any value of routing correction must appear through operating-regime accountability and reserve-risk diagnosis, not through a general forecasting leaderboard win.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_wtb_operational_baselines.tex}
```

![Summary of forecasting and routing outcomes. Panels A and B compress the learned-model error comparison for WTB and ERA5, with ERA5 persistence shown as a deterministic reference. In WTB, the displayed corrected comparator is the boundary-forced routing variant; the deeper full stack is reported separately. Panels C and D summarize routing agreement through NMI and ARI.](artifacts/final_evidence_package/export/figures/figure3_summary_results.pdf){ width=96% }

## Transition-Window and Regime-Slice Behavior

The MPPT-to-pitch boundary is the hardest WTB forecasting slice, which is exactly why average RMSE is not enough. In the strict boundary-band audit, anchors within +/-1.0 m s$^{-1}$ of the rated-wind boundary have RMSE 321.17 +/- 21.31, which is 67.07 higher than valid non-boundary MPPT/pitch anchors and roughly 50--67 units higher than the single-regime MPPT and pitch-control cores. The same boundary band still has measurable mixed-regime structure, with NMI/ARI 0.6562 / 0.7766. The transition window is therefore both a forecasting stress point and a meaningful routing target.

The broader regime slices keep the accuracy-accountability tradeoff visible. Graph WaveNet and PatchTST remain strong references in switch-window and pitch-control RMSE, while the boundary-forced router pays an error cost. That cost is not a defect hidden by the analysis; it is the price of forcing the model to keep responsibility aligned with a declared physical partition. The question becomes whether that partition changes the reserve tradeoff where the control law changes.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_boundary_slice.tex}
```

## Physics-Aligned Gate Recovery

Physics-anchored routing substantially recovers the WTB MPPT-to-pitch operating partition. Across five strict-mask WTB seeds, the boundary-forced router reaches gate-regime NMI/ARI of 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371. ERA5 shows a weaker but directionally consistent pattern: physics-aligned routing raises NMI/ARI from 0.0317 +/- 0.0219 / 0.0253 +/- 0.0626 for Unconstrained MoE to 0.2100 +/- 0.0972 / 0.2279 +/- 0.1296. This contrast is informative. When the regime marker is visible in the input state, routing correction calibrates an already expressed partition; when turbine-control action partly hides the boundary, stronger SCADA anchoring is needed.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_seed_metrics.tex}
```

The deterministic anchor-only router is a strong semantic baseline, not a straw comparison. It reaches slightly higher NMI/ARI than the trainable boundary-forced router (0.8895/0.9219 versus 0.8716/0.9166) and lower headline RMSE. The trainable router is justified only under a narrower requirement: the responsibility assignment must remain part of the forecast and reserve evaluation. Under 0.5-standard-deviation boundary-anchor noise, anchor-only overall RMSE degrades by 105.56, whereas the trainable router degrades by 5.78. Thus the learned gate is not a better fixed labeler; it is a more robust responsibility layer for an operating diagnostic.

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

Figure 4 makes the WTB repair visible in the operating plane. After correction, dominant expert regions align with the MPPT and pitch-control structure, and the confusion matrices contract around the intended partition. Figure 5 adds the temporal view: the WTB gate carries responsibility through a switch window, while the ERA5 gate evolves with sensible heat flux and regime shading. Together, these panels explain why the same routing prior has different value across the two observability settings.

![WTB routing diagnostics. Panel A maps the dominant expert in the $(Wspd, Pab_{mean})$ plane for the boundary-forced routing variant, with the sample cloud colored by physical operating regime. Panel B shows the binned gate redistribution against wind speed together with the mean pitch curve. Panels C and D compare the unconstrained and corrected confusion matrices.](artifacts/final_evidence_package/export/figures/figure4_routing_evidence.pdf){ width=97% }

![Dual case studies for correction and emergence. Panel A shows a local WTB switch window in which the boundary-forced routing variant remains stable while the dense and unconstrained models deviate more strongly near the MPPT-to-pitch transition; wind speed, pitch angle, and the dominant expert strip are plotted underneath. Panel B shows the ERA5 positive-control view, where sensible heat flux, regime shading, and expert weights evolve coherently over a selected week.](artifacts/final_evidence_package/export/figures/figure5_case_studies.pdf){ width=97% }

## Transition-Window Reserve Diagnostic

Gate-conditioned reserve binning improves the boundary-window cost-violation-shortage tradeoff at a measured reserve-energy price. Four policies isolate the source of the effect: Graph WaveNet/global is the low-RMSE system reference; Graph WaveNet/physical-bin tests physical stratification without a learned gate; boundary router/global isolates the routed model's forecast penalty with a flat reserve rule; and boundary router/gate-bin adds gate-conditioned allocation to the same routed predictor. The valid attribution is therefore same-model and local: does the learned gate improve the boundary router's reserve tradeoff near the MPPT-to-pitch transition?

At shortage-to-reserve cost ratio 10, the answer is yes for boundary anchors. Boundary router/gate-bin lowers same-model total cost from 88.13M to 84.58M, violation from 10.38% to 9.00%, and shortage energy from 3.73M to 3.19M normalized units, while reserve energy rises from 50.82M to 52.67M. In percentage terms, shortage energy falls by about 14.5% and reserve energy rises by about 3.6%. This does not make the routed model a full-sample reserve controller: Graph WaveNet/global remains the system reference, and boundary router/gate-bin raises full-sample violation relative to the same model's global rule. The useful claim is local to the transition window.

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

The cost-ratio sweep defines the operating envelope. At ratio 2, gate-bin allocation is not useful because the selected reserve quantile tolerates too much shortage. At ratios 5--10, it reduces boundary shortage and violation while carrying more reserve, which is the intended transition-window scheduling regime. At ratio 20 the gain narrows, and at ratio 50 the same-model global rule is safer and cheaper. The gate is therefore a conditional reserve-allocation signal, not a universal reserve policy.

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

The held-out coverage and sensitivity tables explain where the reserve result is reliable. At ratio 10, boundary router/gate-bin is closest to the intended coverage on boundary anchors, with realized coverage 0.910 and violation 0.0900. Horizon and time-of-day slices show that residual shortage is largest at late lead times and in the daytime anchor-index proxy. A horizon-specific empirical-quantile what-if lowers residual shortage in both Graph WaveNet and routed rows, indicating that lead-time calibration matters and that future comparisons should include trained quantile or distributional reserve baselines.

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

The same evidence can be read as a system-value envelope. The usable interval is the moderate cost-ratio range 5--10, where fewer boundary violations and less shortage are bought with finite additional reserve. This envelope is narrower than the model's routing success, which is important for practice: a gate can be physically meaningful without being the right downstream reserve rule under every cost assumption.

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

Operator-facing slices sharpen the same point. Gate-bin reserve helps the MPPT-to-pitch and low-ramp slices, but it is not a win in pitch-to-MPPT or high-ramp slices. The operational decision curve therefore places the routed model's RMSE penalty beside the reserve-risk benefit: the higher-RMSE router is considered only where fewer boundary shortages and violations are worth the reserve-energy cost.

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

Lead-lag and high-error audits define the limit of this reserve interpretation. The corrected gate aligns most strongly at and after the physical switch, not several steps before it, so the gate is a state diagnostic rather than a lead-time alarm. High-error cases show the complementary failure mode: the gate can assign the correct operating regime while the expert forecast remains numerically poor. Correct routing is therefore necessary for mechanism interpretation, but it is not sufficient for accurate power prediction.

## Stress Tests and Ablation Frontier

Routing semantics transfer to unseen turbines within WTB. Holding out 27 of 134 turbines during training and validation, the boundary-forced router reaches NMI/ARI 0.8340 +/- 0.0958 / 0.8829 +/- 0.0875 on the held-out nodes, with overall RMSE 233.87 +/- 2.84. A pre-specified later WTB holdout gives a similar temporal stress result: NMI/ARI 0.8352 +/- 0.0669 / 0.8870 +/- 0.0669 and overall RMSE 235.49 +/- 7.19. These tests support within-farm spatial and temporal robustness of routing semantics, while leaving value-prediction stability and new-farm transfer to separate checks.

The WTB proxy deployment drill tests whether the calibration workflow can be executed under held-out separation. A 2-day calibration window followed by future-period testing passes the held-out routing gate in all five seeds, with mean NMI/ARI 0.8397/0.8907 and balanced accuracy 0.9770. A 7-day east-turbine proxy also passes in all five seeds, with mean NMI/ARI 0.8272/0.8781 and balanced accuracy 0.9709. These are WTB-internal workflow demonstrations, not universal minimum calibration windows and not evidence of external-farm portability.

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

The drill also defines practical usability checks. Thresholds must be chosen on a pre-specified local grid and frozen before held-out testing. Calibration support depends on valid boundary cells and pitch observability, not elapsed days alone. If pitch channels or validated proxies are missing, the gate cannot be interpreted as a physical router; if high-ramp slices fail the reserve audit, the gate-bin rule should not be used for reserve allocation.

The ablation exposes a controllable accuracy-semantics frontier. Unconstrained MoE sits in the low-semantics region. Regime alignment moves the gate sharply upward in NMI/ARI with modest RMSE cost, while boundary forcing pushes further toward semantic repair at a clearer forecasting price. With load balancing, regime alignment, and boundary forcing active, the selected corrected router reaches NMI/ARI 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371. The ablation claim is therefore the shape of the RMSE/NMI frontier, not an accuracy ranking.

![WTB accuracy-semantics tradeoff across routing variants. Circles show NMI and squares show ARI against overall RMSE. The frontier clarifies that stronger routing correction improves gate-regime agreement but can move the model away from the lowest forecast error.](artifacts/final_evidence_package/export/figures/figure6_ablation_tradeoff.pdf){ width=82% }

The mechanism and fairness checks rule out two easy explanations for the WTB result. The in-family routed variants share model capacity, and the external baselines show that the routed model is not winning by hidden parameter count or speed. The compute-cost table adds the practical constraint: PatchTST is fastest, Graph WaveNet has the lowest strict-mask RMSE, and the routed models sit between them with about 110k trainable parameters and 13--14 s evaluation time for the strict test windows.

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

The intervention audit shows that the gate depends selectively on the intended boundary anchor. Zeroing the boundary anchor raises overall RMSE by 2.6792 and drops NMI/ARI by 0.7017 / 0.8593; zeroing the wake score is near-null, with overall RMSE change 0.0031 and NMI/ARI drop about 0.0010 / 0.0010. Placebo labels built from temporal shifts, node permutation, within-time shuffling, and global shuffling do not reproduce the actual-label agreement. These checks move the WTB claim beyond visualization: the gate is tied to the MPPT-to-pitch boundary rather than to arbitrary physical channels or shuffled label structure.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_mechanism_effects.tex}
```

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_placebo_effects.tex}
```

The time-forward audit gives the main failure case. Routing semantics remain stable in the late test block, with NMI/ARI 0.8661 +/- 0.0393 / 0.9079 +/- 0.0364, but forecasting accuracy worsens sharply: late-minus-early overall RMSE is +50.3454 and switch-window RMSE is +63.3549. The distribution-shift diagnostics show higher target power, larger pitch action, lower mask-valid coverage, and shifted regime shares. The gate still tracks the physical partition, but the value map faces a different operating distribution. This is a useful boundary condition: the method supports routing semantics more strongly than time-stable forecasting accuracy.

```{=latex}
\input{artifacts/final_evidence_package/export/tables/table_strict_wtb_late_shift_diagnostics.tex}
```

Sensitivity checks show that the routing result is not a single-threshold accident. Varying $\lambda_{\mathrm{align}}$ from 2500 to 7500 keeps NMI in the 0.8255--0.8546 range, and varying $\lambda_{\mathrm{force}}$ from 5000 to 15000 keeps NMI in the 0.8091--0.8406 range. Re-labeling saved strict-mask gate outputs over the local rated-wind/pitch grid gives worst-case NMI/ARI 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377 with minimum shared-valid support 0.9909. The audit is local to the tested grid and does not cover every turbine-control threshold, but it supports the pre-specified WTB operating-boundary rule.

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

## External Failure and Local Deployment Protocol

Kelmarsh/Penmanshiel external testing fails the pre-specified routing criterion, and this negative result is part of the contribution. The default WTB boundary gives mean external routing NMI 0.4877, below the 0.50 criterion. Validation-only local recalibration raises default test NMI only from 0.1324 to 0.1491 on average, and the small calibration-window adaptation remains below the held-out balanced-accuracy threshold. The failure is therefore not a simple threshold shift. It points to concrete deployment conditions: pitch/proxy coverage, boundary-cell support, turbine geometry, farm scale, power-curve distribution, sensor fields, and regime-label balance.

This external failure turns into a local evidence protocol. A new farm must first show pitch observability or a validated pitch proxy; then re-estimate rated wind, pitch threshold, boundary band, and gate-to-regime map on a local calibration period; and only then pass a held-out routing criterion before any gate-bin reserve rule is used. If the held-out gate fails, the result remains a boundary-condition diagnosis rather than a physical-router or reserve-control claim.

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

![New wind-farm evidence protocol. The protocol moves from sensor coverage to local boundary calibration, held-out routing, reserve audit, and finally bounded operating claims.](artifacts/final_evidence_package/export/figures/new_wind_farm_deployment_checklist.png){ width=94% }

The practical rule is now clear. Correction strength should scale with regime observability and with the operating decision that consumes the gate. ERA5 already exposes its regime marker, so routing correction improves alignment without changing the headline accuracy story. WTB hides part of the MPPT-to-pitch boundary inside control action, so stronger gate repair is justified only when its reserve-window diagnostic value exceeds the measured RMSE and reserve-energy cost. The method is appropriate when the operating boundary is part of the scientific question; it is not a substitute for the strongest black-box forecaster when the task is only mean-error minimization.

# Limitations

The WTB correction depends on threshold-based pseudo-labels derived from wind speed and mean pitch angle. Those same channels also appear in the gate anchor, so the method deliberately constrains the router to a declared operating boundary. The threshold audit and loss-weight sweep show local robustness, but they do not exhaust all anchor thresholds, wake-score cutoffs, wake-cone parameters, turbine-control settings, or retrained no-/lagged-anchor ablations. The method is boundary-aware regularized routing, not fully learned operating-state discovery.

The active-power anchor has a strict timing requirement. `Patv` is allowed only as the historical/anchor-time active-power measurement available when the forecast is issued; future active power remains the supervised target. This is a defensible SCADA forecasting convention, but it is also a portability constraint and a possible source of interpretive circularity. The current intervention evidence zeroes the boundary-anchor input and shows that routing agreement collapses, but it is not a retrained no-`Patv` or lagged-`Patv` ablation. Taken together with the missing wind-speed and pitch ablations above, the present evidence cannot claim to identify which part of the gate is pitch/wind observability, active-power status, or structure learned after anchoring. If a deployment environment delays active-power telemetry, changes channel definitions, or evaluates a decision before the current active-power value is available, the Patv anchor must be removed or lagged and the leakage, intervention, and reserve diagnostics must be rerun.

The expert-regime language is tied to the implemented logit convention. The first primary-regime logits are fixed to the operating labels during supervised alignment, which prevents seed-wise permutation for those anchored meanings. That makes cross-seed MPPT/pitch statements interpretable, but only for the anchored logits and only under the declared mapping. Unassigned experts and wake auxiliary logits should not be overread as universal turbine states.

The comparison is bounded. WTB includes graph, transformer, lag-feature, persistence, power-curve, and DLinear-style references, while ERA5 includes persistence and several learned baselines. Larger time-series backbones, broader graph-transformer variants, trained quantile-regression baselines, and scenario/distributional reserve methods are outside the present benchmark.

The reserve audit is deliberately narrower than power-system dispatch. It does not implement unit commitment, market clearing, a full probabilistic prediction-to-reserve pipeline, real dispatch integration, or a closed-loop operator simulation. The audit is therefore a normalized proxy decision: fixed empirical quantile bins are calibrated on validation shortfall and tested once on held-out predictions, with costs reported in normalized reserve-energy units rather than money. It is useful for ranking boundary-window risk tradeoffs under declared cost ratios, but it is not a market-price, delivery-constrained, or security-constrained dispatch study.

External wind-farm diagnostics fail the external-site routing criterion. The quasi-external drill shows that the calibration-to-held-out workflow can pass inside WTB, but it does not change the Kelmarsh/Penmanshiel conclusion. The evidence supports within-WTB spatial and temporal stress validation plus external diagnosis of when local boundary re-estimation is required.

The time-forward audit is not an external validation. It is a post-hoc split of saved WTB test predictions into contiguous anchor-time blocks. It shows that the strict-mask gate keeps its physical partition in the late block, but it also shows a large late-test RMSE increase. The failure case is therefore explicit: late-period distribution shift preserves routing agreement while degrading value prediction. This is an important boundary condition: the method currently supports routing semantics, not time-stable forecasting accuracy.

Statistical reliability is uneven across claim types. The strongest claims are the five-seed WTB routing-recovery, mechanism-intervention, and within-WTB spatial/temporal stress results. Engineering baselines, reserve-window diagnostics, and external adaptation checks are reported as deterministic or bounded diagnostics, not as broad superiority claims. WTB and ERA5 are sufficient for the intended weak-versus-visible observability contrast, but other industrial or geophysical systems require local boundary estimation and held-out routing checks.

# Conclusion

This paper treats non-stationary wind-power modeling as a routing-interpretability problem around operating transitions. Strong graph, transformer, and lag-feature baselines remain better mean-error forecasters than the boundary-forced router, but the selected router recovers the WTB MPPT-to-pitch partition, survives placebo and within-WTB spatial/temporal stress checks, and links that partition to a transition-window reserve diagnostic. At shortage-to-reserve cost ratio 10, gate-conditioned reserve binning reduces same-model boundary-window violation and shortage energy at a measured reserve-energy cost.

The practical conclusion is bounded. When the regime marker is visible, routing regularization calibrates an already available partition. When the marker is partly hidden by turbine-control action, physics guidance at the gate can repair a weakly identified partition and provide reserve/ramp-risk diagnosis, but it trades against forecast error and does not create a whole-sample reserve rule. Kelmarsh/Penmanshiel failure shows that this responsibility claim must be re-established when turbine geometry, pitch observability, sensor fields, power curves, or label distributions change. Until a new wind farm passes the local evidence protocol, the method should be described as within-WTB operating-boundary interpretability plus external failure-boundary diagnosis plus transition-window reserve diagnosis.

# Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work, the authors used OpenAI ChatGPT/Codex to support language editing, consistency checking, and submission-material drafting. After using these tools, the authors reviewed and edited the content as needed and take full responsibility for the content of the published article.

# Code and data availability

The experiments use four public source families: the KDD Cup 2022 wind-farm SCADA benchmark, ERA5 reanalysis fields, and the Kelmarsh and Penmanshiel wind-farm SCADA records. Source datasets remain available from their original providers; raw third-party data that cannot be redistributed will be accompanied by download instructions and rebuilding scripts. The release package can provide code, configuration files, derived artifacts when licensing permits, model checkpoints, seed-level summaries, final figure source data, and reproduction commands for the strict WTB evidence, transition-window reserve audit, quasi-external WTB drill, and external boundary diagnostics. The analysis uses turbine and atmospheric measurements only and involves no human participants or human-subject data.

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
