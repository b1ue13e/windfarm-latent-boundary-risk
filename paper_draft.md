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
\Large\bfseries Boundary-Aware Routing for Wind-Power Operating Transitions with an ERA5 Observability Contrast\par
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
Wind-power forecast errors become most operationally costly near control transitions, where reserve schedules, ramp-risk alerts, and shortage exposure depend on whether a turbine is still in maximum power point tracking (MPPT) or has entered pitch control. This paper asks a narrow operational question: can a mixture-of-experts (MoE) gate be constrained to identify that operating boundary, and what forecasting and reserve-decision costs does this accountability impose? We build a directed-diffusion gated recurrent unit (GRU) encoder with a node-level MoE gate and constrain the gate with load balancing, regime-anchor alignment, graph smoothness, wake supervision, and boundary-focused forcing. The KDD Cup 2022 wind-farm supervisory control and data acquisition (SCADA) benchmark (WTB) is the main operating-boundary test; ERA5 reanalysis is used as an observability contrast where the thermodynamic marker is already visible through sensible heat flux. The synchronized strict-cache results separate three claims. First, Graph WaveNet and engineering lag-feature baselines provide the accuracy reference: Graph WaveNet reaches overall root mean squared error (RMSE) 225.74 +/- 2.60 and switch-window RMSE 228.12 +/- 3.23 across five seeds, while lag-feature LightGBM and XGBoost reach 227.12 / 232.24 and 227.88 / 233.07 in the same overall/switch metrics. Second, the boundary-forced router pays an RMSE price, with RMSE 236.13 +/- 8.41 and switch-window RMSE 239.86 +/- 8.85, but it recovers the WTB operating partition with gate-regime normalized mutual information/adjusted Rand index (NMI/ARI) 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371. Reloaded checkpoints reproduce the saved metrics; boundary-anchor removal collapses NMI/ARI by 0.7017 / 0.8593, wake-anchor removal is near-null, and temporal, spatial, and global placebos all reduce agreement. Third, reserve value is conditional on the operating window. At shortage-to-reserve cost ratio 10, Graph WaveNet/global-quantile reserve is the main full-sample system baseline, while the boundary-forced gate-bin policy is evaluated as a transition-window diagnostic. On MPPT-to-pitch boundary anchors, that gate-bin policy lowers total cost from 88.13M to 84.58M, violation rate from 0.1038 to 0.0900, and boundary shortage energy from 3.73M to 3.19M relative to the same model's global reserve policy, at the price of 1.85M additional reserve energy. Operator-facing slices show both value and risk: the MPPT-to-pitch slice lowers violation and shortage with more reserve, whereas high-ramp windows expose shortage increases when the gate-conditioned policy carries too little reserve. Gate lead-lag analysis also supports state detection rather than reliable advance warning: agreement with the new regime is 0.3636 three steps before the transition and 0.8008 at the transition. Kelmarsh/Penmanshiel external-site runs fail the pre-specified portability criterion and are reported as boundary-condition diagnostics. Local rated-wind/pitch recalibration recovers only limited test agreement, and a small calibration-window boundary/gate-map adaptation completes but does not restore robust held-out routing. The contribution is physical accountability of routing near wind-turbine operating transitions, with explicit evidence for its forecasting, reserve, and external-site limits.

\vspace{0.25em}
\noindent{\small\textbf{Keywords:} Wind-power operations; operating boundary; reserve decision; mixture of experts; regime routing; spatio-temporal graph learning.\par}

\normalsize

\vspace{0.55em}

# Introduction

Average error hides the part of forecasting that operators often care about most. In renewable-rich systems, the costly mistakes cluster in short transition windows, when the local response law changes faster than dispatch, reserves, curtailment, or turbine control can be retuned. In wind farms, this difficulty appears near the maximum power point tracking (MPPT)-to-pitch boundary and during wake-affected inflow shifts, where power stops following wind speed through one smooth mapping [@khodayar2019stwind; @zhou2024sdwpfdata; @haq2025windreview]. A parallel problem appears in the lower atmosphere: stable-to-convective transitions reorganize transport and surface forcing over short horizons that matter for subsequent prediction [@hersbach2020era5]. This paper treats those transition windows as the central forecasting problem.

Spatio-temporal graph forecasting has improved average predictive accuracy in many correlated systems. DCRNN, STGCN, Graph WaveNet, ASTGCN, AGCRN, and MTGNN show that graph propagation and temporal encoding capture asymmetric dependence and dynamic correlation better than dense sequence baselines [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn; @wu2020connecting]. Wind-forecasting work has brought the same idea to wake interaction, transport, and turbine coupling [@khodayar2019stwind; @park2019physicsinduced; @yu2020sgnn; @daenens2025offshore]. The evaluation habit has lagged behind the physics. Most benchmarks still reward overall mean absolute error (MAE), root mean squared error (RMSE), or mean absolute percentage error (MAPE), even when the operational failure is concentrated where the mechanism changes [@li2018dcrnn; @wu2019graphwavenet; @khodayar2019stwind; @daenens2025offshore]. Strong graph encoders improve the map; they do not decide which local map should own a transition.

Mixture-of-experts offers a different answer to heterogeneity. Classical and modern MoE models use routing to allocate different inputs to different predictors, which can increase effective capacity while keeping computation sparse [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch]. Recent sequence-forecasting work has started to import the same specialization idea into large time-series models [@shi2025timemoe]. In parallel, physics-guided learning has shown that prior knowledge can enter the pipeline through synthetic pretraining or feature construction. It can also enter through architecture design or physics-based losses and constraints [@karpatne2017tgds; @read2019pgdl; @park2019physicsinduced; @raissi2019pinn; @karniadakis2021piml; @parsa2025pimlreview]. Together, these lines of work show that specialization and physical prior can each help under heterogeneity, but they rarely meet at the routing layer itself.

The gap is at the gate. Regime-transition error is rarely evaluated as a first-class target, although average metrics can hide failure near operating boundaries [@khodayar2019stwind; @wu2020connecting; @daenens2025offshore]. Physics-guided models usually regularize latent states or outputs, while the routing decision remains governed by prediction loss [@raissi2019pinn; @karniadakis2021piml; @zehtabiyan2023physicsguided]. In control-confounded SCADA streams, that is enough to create a low-error gate with little mechanical meaning. This failure matters because the gate is the part of an MoE that assigns responsibility. If the gate cannot identify the operating boundary, expert specialization becomes a statistical convenience rather than an engineering explanation.

This study puts physical guidance into the routing decision. The model combines a directed-diffusion GRU encoder with a node-level MoE gate and routing losses for expert starvation, regime alignment, local graph consistency, wake exposure, and MPPT-to-pitch ambiguity. WTB and ERA5 are paired because they expose different levels of regime observability: WTB hides the aerodynamic boundary inside control action, while ERA5 makes the thermodynamic marker visible through sensible heat flux. The contribution is deliberately bounded. It reframes non-stationary graph forecasting as operating-boundary routing, places physical supervision at the router, benchmarks the resulting RMSE price against graph, transformer, persistence, power-curve, gradient-boosted lag, and LTSF-style baselines, tests reserve/ramp-risk relevance only in the transition window where the gate has an operational role, and turns the external Kelmarsh/Penmanshiel result into a boundary-condition experiment that tests whether local rated-wind/pitch recalibration is needed before a WTB boundary rule is reused.

# Related Work

## Spatio-temporal graph forecasting

Most spatio-temporal graph forecasting studies reach the same empirical result: once spatial dependence is encoded, average forecast error drops. DCRNN, STGCN, and Graph WaveNet established this pattern by combining graph propagation with recurrent or temporal-convolutional encoders [@li2018dcrnn; @yu2018stgcn; @wu2019graphwavenet]. ASTGCN, AGCRN, and MTGNN then relaxed the fixed-graph assumption and improved average accuracy through adaptive dependence learning [@guo2019astgcn; @bai2020agcrn; @wu2020connecting]. Wind-forecasting models use graph construction to represent wake interaction, transport, and turbine coupling [@park2019physicsinduced; @yu2020sgnn; @daenens2025offshore]. This literature gives the accuracy baseline that our model must face. It also leaves a routing question open at mechanism transitions.

## Mixture-of-experts and routing for sequence modeling

The MoE literature gives the natural modeling tool for heterogeneous response laws. Early adaptive and hierarchical MoE models showed how routing partitions the input space into regions served by different local experts [@jacobs1991adaptive; @jordan1994hierarchical]. Sparse-routing systems scaled this principle and exposed the familiar training failures: router collapse, expert starvation, and unstable load allocation [@shazeer2017outrageously; @fedus2022switch]. Recent sequence-forecasting models have brought the same specialization principle into time-series forecasting [@shi2025timemoe]. For physical regime shifts, a useful router must be judged against mechanism boundaries as well as validation loss.

## Physics-informed and physics-guided learning in spatio-temporal systems

Physics-guided learning has already shown many entry points for prior knowledge. Theory-guided data science and process-guided deep learning use synthetic data, feature construction, pretraining, and post-hoc constraints [@karpatne2017tgds; @read2019pgdl]. Physics-informed neural network (PINN)-style methods and later reviews extend the idea to optimization, architecture, and losses [@raissi2019pinn; @karniadakis2021piml; @parsa2025pimlreview]. In renewable and atmospheric applications, physics-induced graph neural networks (GNNs), lidar-assisted wind-field prediction, frequency-domain PINNs, and physics-guided wind-farm power models improve robustness or interpretability by injecting physical information into the model pipeline [@park2019physicsinduced; @zhang2021lidar; @li2025fdpinn; @zehtabiyan2023physicsguided]. This paper uses the prior at the router, where the responsibility assignment is made.

# Methodology

## Problem setup and notation

The forecasting task is written to separate two decisions that dense models often merge: predicting the future and deciding which local mapping should be active at the anchor time. Let $G=(V,E)$ denote a spatial graph with $N=|V|$ nodes. For each node $i \in V$ and time step $t$, we observe a feature vector $\mathbf{x}_{i,t} \in \mathbb{R}^{F}$ and predict a scalar target $y_{i,t} \in \mathbb{R}$. Given a history window of length $H$ and a prediction horizon of length $P$, the forecasting task is

$$
\hat{\mathbf{Y}}_{t+1:t+P} = \mathcal{F}\!\left(\mathbf{X}_{t-H+1:t}, \mathcal{A}_{t-H+1:t}\right),
$$

where $\mathbf{X}_{t-H+1:t} \in \mathbb{R}^{H \times N \times F}$ and $\mathcal{A}_{t-H+1:t}$ denotes either a time-varying directed graph sequence (WTB) or a static graph repeated over time (ERA5). Invalid or missing targets are excluded by a supervision mask.

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

which is later used as an auxiliary routing indicator.

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
[\texttt{Wspd}, \texttt{Pab\_mean}, s^{\mathrm{wake}}, \texttt{Patv}],
$$

whereas ERA5 uses

$$
\mathbf{a}_{i,t}^{\mathrm{ERA5}}
=
[\texttt{sshf}, \texttt{t2m}, \texttt{wind\_speed}, \Delta \texttt{sshf}].
$$

The difference reflects the observability contrast: WTB needs help to recover a partly hidden operating boundary, whereas ERA5 already exposes the relevant thermodynamic marker in the state.

![Physics-aligned regime-aware MoE. The two datasets share the same directed-diffusion GRU encoder and node-level MoE routing mechanism. WTB uses a dynamic wake graph and a boundary-focused forcing term, whereas ERA5 uses a Haversine-Gaussian graph and a thermodynamic regime anchor.](artifacts/paper_assets/figures/figure1_architecture.pdf){ width=95% }

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

A slightly favored expert can dominate early training and starve the others before regime-specific structure has time to emerge. A balancing term counteracts that early collapse. Let $\mathbf{g}_n$ denote the gate distribution for the $n$-th valid routed sample in a mini-batch of size $B$. The soft importance of expert $e$ is

$$
I_e = \frac{1}{B}\sum_{n=1}^{B} g_n^{(e)},
\qquad
P_e = \frac{I_e}{\sum_{r=1}^{E} I_r}.
$$

The empirical top-$K$ load is

$$
f_e = \frac{1}{B}\sum_{n=1}^{B}\mathbf{1}\!\left[e \in \mathrm{TopK}(\mathbf{g}_n)\right].
$$

The balancing loss is

$$
\mathcal{L}_{\mathrm{bal}} = E\sum_{e=1}^{E} f_e P_e - 1.
$$

This term prevents early expert starvation. Regime ownership is supplied by the alignment terms below.

### Regime-anchor alignment

Balanced expert usage can still produce a physically meaningless partition. The next term aligns the gate with the coarsest regime structure that can be identified with high confidence. Let $\mathbf{z}^{(1:C)}_{i,t}$ denote the first $C$ gate logits, and let $R_{i,t}$ and $M_{i,t}$ be the primary regime label and its validity mask. The alignment loss is

$$
\mathcal{L}_{\mathrm{align}}
=
\frac{1}{|\Omega|}
\sum_{(i,t)\in\Omega}
\mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right),
\qquad
\Omega=\{(i,t):M_{i,t}=1\},
$$

with inverse-frequency class weights estimated on the training split. Alignment stabilizes the coarse physical partition only where the labels are reliable.

### Boundary-focused forcing (WTB only)

The MPPT-to-pitch boundary in WTB remains ambiguous even after coarse regime alignment because control action partly masks the mechanical transition. A focused forcing term acts only on the most informative MPPT and pitch-control samples. Let

$$
Y^{\mathrm{force}}_{i,t} =
\begin{cases}
0, & R^{\mathrm{wtb}}_{i,t}=1,\\
1, & R^{\mathrm{wtb}}_{i,t}=2.
\end{cases}
$$

Using the MPPT-aligned and pitch-aligned expert logits, we define

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

where $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}\}$. This term concentrates the intervention on the mechanically important boundary.

### Wake auxiliary supervision and graph smoothness

After the MPPT-to-pitch boundary is repaired, wake-sensitive samples can still be mixed with non-wake samples inside the same operating regime. A wake auxiliary label identifies that residual ambiguity in WTB, while graph smoothness discourages noisy neighbor-to-neighbor gate jumps in both settings. The wake auxiliary loss is

$$
\mathcal{L}_{\mathrm{aux}}
=
\frac{1}{|\Omega_{\mathrm{wake}}|}
\sum_{(i,t)\in\Omega_{\mathrm{wake}}}
\mathrm{BCE}\!\left(z^{(\mathrm{wake})}_{i,t}, W_{i,t}\right),
$$

where $\Omega_{\mathrm{wake}}$ contains only MPPT and pitch-control samples for which the wake flag is defined. The smoothness term is

$$
\mathcal{L}_{\mathrm{smooth}}
=
\frac{
\sum_{i,j}\mathcal{A}_t(i,j)\lVert \mathbf{g}_{i,t}-\mathbf{g}_{j,t}\rVert_2^2
}{
\sum_{i,j}\mathcal{A}_t(i,j)
}.
$$

The auxiliary term is a WTB-specific repair for wake mixing, while the smoothness term encourages locally coherent routing without prescribing a global partition.

## Dataset-specific anchors and labels

The gate is not supervised everywhere. Instead, it is anchored only where the physical interpretation is clearest, and the ambiguous remainder is organized by prediction loss plus the routing regularizers.

### WTB operating regimes and wake labels

In WTB, the primary operating boundary is the transition from MPPT to pitch control. Let

$$
\bar{p}_{i,t} = \frac{1}{3}\left(p^{(1)}_{i,t}+p^{(2)}_{i,t}+p^{(3)}_{i,t}\right).
$$

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

Wake interference is handled separately because it is spatial. Let $q_{0.75}^{\mathrm{wake}}$ denote the upper-quartile threshold of the wake score over valid operating states in the training split. Then

$$
W_{i,t} =
\begin{cases}
1, & \text{if } s^{\mathrm{wake}}_{i,t} \ge q_{0.75}^{\mathrm{wake}} \ \land\ R^{\mathrm{wtb}}_{i,t} \in \{1,2\},\\
0, & \text{if } s^{\mathrm{wake}}_{i,t} < q_{0.75}^{\mathrm{wake}} \ \land\ R^{\mathrm{wtb}}_{i,t} \in \{1,2\},\\
\varnothing, & \text{otherwise.}
\end{cases}
$$

The exact thresholds are reported in the Appendix tables.

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

If sensible heat flux is unavailable, the same construction can fall back to an analogous rule based on the temporal gradient of 2 m temperature. The exact thresholds used in the reported experiments are again listed in the Appendix.

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

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in the Appendix so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strict-cache strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST across seeds 201--205, giving 20 completed baseline runs under the same strict anchor-valid cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same strict cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE focus on mechanism changes. Regime-wise RMSE locates the error reduction. Normalized mutual information (NMI), adjusted Rand index (ARI), usage entropy, and confusion matrices test whether the gate corresponds to physically interpretable structure.

Figure 2 gives the physical setting before the forecasting results are introduced.

![Dataset geometry and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and the retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split.](artifacts/paper_assets/figures/figure2_data_boundary.pdf){ width=97% }

# Results

## Overall performance

WTB delivers a hard accuracy result: the strongest graph and engineering forecasters beat the routed family under the synchronized strict-cache refresh. Graph WaveNet reaches overall RMSE 225.74 +/- 2.60 and switch-window RMSE 228.12 +/- 3.23 across seeds 201--205. PatchTST reaches 228.07 +/- 4.05 and 231.22 +/- 4.15. Graph Transformer reaches 235.38 +/- 5.15 and 237.06 +/- 5.78, while GAT-GRU reaches 236.59 +/- 7.80 and 240.17 +/- 8.50. Among engineering baselines, LightGBM lag features reach overall/switch RMSE 227.12 / 232.24, XGBoost lag features 227.88 / 233.07, a fitted physical power curve 241.02 / 245.37, persistence 243.23 / 246.61, and the DLinear-style LTSF readout 246.81 / 251.15. The boundary-forced router reaches overall RMSE 236.13 +/- 8.41, switch-window RMSE 239.86 +/- 8.85, and pitch-control RMSE 286.95 +/- 22.07 across seeds 201--205. The completed strict-cache leaderboard places the routed model outside a headline-error objective and motivates the narrower routing-recovery claim.

ERA5 makes the same separation sharper. A last-value persistence baseline gives the lowest headline error, with overall RMSE 0.7127 and switch-window RMSE 0.6814. Among learned ERA5 baselines, Graph WaveNet is best at 0.8417 +/- 0.0540, followed by the matched dense encoder at 0.8641 +/- 0.0690, physics-aligned MoE at 0.8735 +/- 0.0479, TCN at 0.8784 +/- 0.0286, PatchTST at 0.8817 +/- 0.0675, Unconstrained MoE at 0.9294 +/- 0.0451, and STGCN at 0.9893 +/- 0.1344. The forecasting tables set the terms of the paper: physics-aligned routing earns its value through interpretable responsibility. That value is only credible if the routing metrics improve under the same evaluation protocol.

The two WTB tables below are the submission-facing forecast evidence: the strict-cache neural leaderboard and the strict-cache engineering baseline panel. Both are tied to the final evidence package and avoid pre-strict-mask corrected-router rows.

```{=latex}
\input{artifacts/goal_tables_20260612/table_strict_cache_wtb_leaderboard_20260612.tex}
```

```{=latex}
\input{artifacts/operational_baselines_wtb_strictmask/table_wtb_operational_baselines.tex}
```

![Summary of forecasting and routing outcomes. Panels A and B compress the learned-model error comparison for WTB and ERA5, with ERA5 persistence shown as a deterministic reference. In WTB, the displayed corrected comparator is the boundary-forced routing variant; the deeper full stack is reported separately. Panels C and D summarize routing agreement through NMI and ARI.](artifacts/paper_assets/figures/figure3_summary_results.pdf){ width=96% }

## Transition-window and regime-slice performance

The difficult slices repeat the same separation between forecasting accuracy and routing evidence. In the completed strict-cache baseline rows, Graph WaveNet reaches switch-window RMSE 228.12 +/- 3.23 and pitch-control RMSE 282.67 +/- 31.41. PatchTST reaches switch-window RMSE 231.22 +/- 4.15 and pitch-control RMSE 277.21 +/- 19.30. Graph Transformer reaches switch-window RMSE 237.06 +/- 5.78 and pitch-control RMSE 280.50 +/- 35.98, while GAT-GRU reaches switch-window RMSE 240.17 +/- 8.50 and pitch-control RMSE 318.28 +/- 49.88. Under the strict anchor-valid mask, the boundary-forced router reaches pitch-control RMSE 286.95 +/- 22.07 and switch-window RMSE 239.86 +/- 8.85. These slice results support a mechanism-evidence update, not a headline-error claim. ERA5 again favors persistence. Among learned ERA5 models, Graph WaveNet gives the best overall and switch-window RMSE, while physics-aligned routing improves over Unconstrained MoE in the transition slice without beating the dense model or persistence on headline error. This is calibration around a visible thermodynamic boundary, not broad forecast repair.

The submission-facing slice evidence is therefore restricted to strict-cache rows and the boundary-slice audit below. We do not mix pre-strict corrected-router rows with the current strict-cache evaluation.

We therefore add a stricter boundary-slice audit directly from the saved strict-mask predictions and the strict cache physics. The audit isolates anchors within +/-1.0 m s$^{-1}$ of the rated-wind MPPT-to-pitch boundary and compares them with valid non-boundary MPPT/pitch anchors and with single-regime core slices. The boundary band is the hardest forecasting slice: RMSE is 321.17 +/- 21.31, which is 67.07 higher than the non-boundary valid slice (95% bootstrap interval 52.54 to 84.21), 67.46 higher than the MPPT core, and 50.01 higher than the pitch-control core. At the same time, the boundary band still carries mixed-regime routing structure, with NMI/ARI 0.6562 / 0.7766. This closes a narrower mechanism question: the strict-mask gate is not only globally aligned, but remains measurable at the operating boundary where prediction is hardest.

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_boundary_slice.tex}
```
```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_boundary_effects.tex}
```

## Routing evidence

Routing recovery is the positive result. Across five ERA5 seeds, Unconstrained MoE keeps high expert-usage entropy but near-zero routing agreement, with NMI/ARI of 0.0317 +/- 0.0219 / 0.0253 +/- 0.0626. Physics-aligned MoE raises those scores to 0.2100 +/- 0.0972 / 0.2279 +/- 0.1296. This is a modest but useful correction because the ERA5 marker is already visible in the input state. WTB shows the stronger effect after the strict anchor-valid rerun: the boundary-forced router reaches gate-regime NMI/ARI of 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 across seeds 201--205. The previous weak seed-204 behavior disappears under the strict cache, with seed 204 reaching NMI/ARI 0.8591 / 0.9060. Explicit gate correction therefore recovers a physically meaningful partition in the control-confounded setting, while the result remains bounded to the tested WTB/ERA5 settings.

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_seed_metrics.tex}
```

The current WTB mechanism table above is the submission-facing source for the corrected router. ERA5 routing values are used only as the observability contrast already summarized in the text and final evidence package.

Figure 4 makes the WTB repair visible in the operating plane. After correction, the dominant expert regions align with the MPPT and pitch-control structure, and the confusion matrices contract around the intended operating partition. The corrected gate becomes readable at the boundary that matters operationally, with the RMSE cost already quantified above.

![WTB routing diagnostics. Panel A maps the dominant expert in the $(Wspd, Pab_{mean})$ plane for the boundary-forced routing variant, with the sample cloud colored by physical operating regime. Panel B shows the binned gate redistribution against wind speed together with the mean pitch curve. Panels C and D compare the unconstrained and corrected confusion matrices.](artifacts/paper_assets/figures/figure4_routing_evidence.pdf){ width=97% }

Figure 5 traces the same contrast through time. In the WTB switch window, the boundary-forced router carries responsibility through the MPPT-to-pitch transition more coherently than the unconstrained gate. In ERA5, expert weights evolve with sensible heat flux and regime shading, as expected when the marker is already expressed in the state. The case studies tie the routing metrics to the physical mechanisms behind them.

![Dual case studies for correction and emergence. Panel A shows a local WTB switch window in which the boundary-forced routing variant remains stable while the dense and unconstrained models deviate more strongly near the MPPT-to-pitch transition; wind speed, pitch angle, and the dominant expert strip are plotted underneath. Panel B shows the ERA5 positive-control view, where sensible heat flux, regime shading, and expert weights evolve coherently over a selected week.](artifacts/paper_assets/figures/figure5_case_studies.pdf){ width=97% }

## Operational value and failure cases

The routing claim needs an energy-system consequence, not only a semantic score. We therefore turn the earlier reserve proxy into a conditional operating audit: from the saved WTB validation and test predictions, each model calibrates reserve levels on validation shortfall and is charged reserve cost plus a shortage penalty on test shortfall. The audit reports the quantities a reserve desk would inspect--total cost, violation rate, reserve energy, and shortage energy--and deliberately asks a local question. Does a gate-aware reserve rule change shortage exposure where the gate is supposed to matter, namely MPPT-to-pitch boundary anchors within +/-1.0 m s$^{-1}$ of rated wind? We count this as operating value only when the gate-aware policy improves total cost, violation rate, and shortage energy together in that boundary window.

At the main shortage-to-reserve cost ratio of 10, Graph WaveNet/global-quantile reserve is the principal energy-system baseline, with mean full-sample total cost $4.6407\times10^8$; Graph WaveNet/physical-bin reserve is reported alongside it as a physics-stratified system comparator. The boundary-forced router is not the cheapest full-sample reserve system. Its operational value appears in the boundary window. On boundary anchors, moving the same boundary-forced model from global reserve to a gate-bin reserve policy lowers mean total cost from 88.13M to 84.58M, violation rate from 0.1038 to 0.0900, and boundary shortage energy from 3.73M to 3.19M, while increasing reserve energy from 50.82M to 52.67M. The physical-bin policy is an oracle-style diagnostic and is slightly lower still, with 83.78M total cost and 3.05M shortage energy. On the full sample and non-boundary subset, however, the gate-bin policy can reduce reserve expenditure and total cost while raising violation and shortage relative to the same model's global policy. The system claim is therefore not that the gate produces a globally better reserve policy; it is that operating-boundary accountability changes the reserve-shortage tradeoff in the window where dispatch risk is physically concentrated.

Cost-ratio sensitivity makes the same boundary explicit. At ratio 2, the penalty is too low to buy reserve and the gate-bin boundary policy is identical to global reserve. At ratios 5 and 10, the boundary-forced gate-bin policy lowers same-model boundary shortage and violation relative to global reserve, with the ratio-10 operating point reducing shortage from 3.73M to 3.19M. At ratio 20 the advantage narrows to a small shortage reduction with almost unchanged violation. At ratio 50 the same-model global policy is safer and cheaper. This is the Applied Energy reading of the reserve result: the gate is a conditional reserve-allocation signal around the MPPT-to-pitch boundary, not a replacement for system-level stochastic reserve optimization.

We also export operator-facing slices that are closer to reserve desk language than the aggregate boundary/non-boundary split. The four slices are MPPT-to-pitch transitions, pitch-to-MPPT transitions, validation-calibrated high absolute ramp, and validation-calibrated low absolute ramp. For the boundary-forced router, gate-bin reserve reduces violation and shortage energy in the MPPT-to-pitch slice relative to the same model's global policy, but it pays an added reserve-cost price: 17.93M total cost, 0.1027 violation rate, and 0.69M shortage energy, compared with 16.33M, 0.1124, and 0.77M under global reserve. The low-ramp slice shows the cleaner cost/risk improvement, with gate-bin total cost 10.73M versus 11.24M and shortage energy 0.40M versus 0.44M. The pitch-to-MPPT and high-ramp slices are not gate-bin wins. In the high-ramp slice, gate-bin reserve reduces total cost slightly but raises violation from 0.0766 to 0.1253 and shortage energy from 1.06M to 2.51M because it carries much less reserve energy. This is why the reserve claim remains a boundary-window decision diagnostic rather than a global reserve-policy claim.

The three operational cases in the next table are included to prevent a common misreading. A correct gate can help allocate attention around the MPPT-to-pitch boundary, but it can also be misleading when the downstream forecast is bad or when a low-reserve gate-bin policy is applied to high-ramp windows.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table.} Operator-facing cases: when the boundary gate helps and when it misleads.}
\input{artifacts/applied_energy_diagnostics/table_operational_case_explanation.tex}
\end{table}
```

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table.} Boundary-window reserve audit for the WTB boundary-forced router at shortage-to-reserve cost ratio 10.}
\begin{tabular}{lrrrr}
\toprule
Reserve policy & Total cost & Violation rate & Reserve energy & Boundary shortage \\
\midrule
Global & 88.13M & 0.1038 & 50.82M & 3.73M \\
Physical-bin & 83.78M & 0.0880 & 53.26M & 3.05M \\
Gate-bin & 84.58M & 0.0900 & 52.67M & 3.19M \\
\bottomrule
\end{tabular}
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
\input{artifacts/decision_reserve_wtb_operational_windows/reserve_decision_boundary_slices.tex}
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
\input{artifacts/applied_energy_diagnostics/table_cost_ratio_sensitivity_readable.tex}
\end{table}
```

Lead-lag analysis gives the same operational boundary. Around physical regime switches, the corrected gate matches the new regime at rate 0.4066 six steps before the switch and 0.3636 three steps before it, then rises to 0.8008 at the switch and remains 0.6313/0.6094 three/six steps after it. This does not support an early-warning claim. It supports a narrower state-detection claim: the gate is most reliable once the transition is present, so the reserve experiment should be framed as boundary-aware reserve/ramp-risk conditioning rather than as advance prediction of the switch.

The reviewer-statistics pack reports the complementary failure mode. It contains 24 gate-correct high-error cases and 24 boundary gate-correct high-error cases, and the full lists are retained in the supplement. These rows are important because they separate the two parts of the model. In those samples, the router assigns the sample to the physically appropriate operating regime, but the expert forecast is still numerically poor. The usual pattern is a value-map failure near high-error boundary windows, not a collapse of mechanism responsibility. We therefore treat these cases as evidence for the paper's boundary condition: correct routing is necessary for mechanism interpretation, but it is not sufficient for accurate power prediction.

## Spatial and future holdout stress tests

The reviewer-facing spatial holdout tests whether the routing evidence survives when entire turbines are unavailable during training and validation. The east-node protocol holds out 27 of 134 turbines (20.15%). During training and validation, target and regime-valid entries for holdout nodes are masked; during testing, train-node targets are masked and evaluation is restricted to the held-out nodes. The guard reports `mask_policy_pass = true`, zero strict-anchor violations, 15/15 completed runs, and a passed mechanism gate. In this harder within-farm spatial transfer setting, the boundary-forced router reaches overall RMSE 233.87 +/- 2.84, switch-window RMSE 234.87 +/- 2.33, and NMI/ARI 0.8340 +/- 0.0958 / 0.8829 +/- 0.0875. Context-supervised routing is more accurate but less semantically aligned, with NMI/ARI 0.7479 +/- 0.0461 / 0.8084 +/- 0.0717. Anchor-only routing is semantically strong but less stable. The spatial intervention audit keeps the same interpretation as the in-sample strict-mask mechanism test: boundary-anchor removal causes a large NMI/ARI loss and a positive RMSE penalty, while wake-anchor removal remains near-null. This is not an out-of-site wind-farm result; it is a within-farm node-held-out stress test that checks whether the learned routing semantics extrapolate to unseen turbines.

```{=latex}
\input{artifacts/goal_tables_20260612/table_spatial_holdout_summary_20260612.tex}
```

The future-period holdout uses a pre-specified later WTB period with seeds 301--305 and evaluates only the holdout split. All 5/5 runs complete, the mechanism gate passes, and the downstream holdout mechanism intervention, placebo, boundary-slice, and reviewer statistics packs are present. The boundary-forced router reaches holdout overall RMSE 235.49 +/- 7.19, switch-window RMSE 239.93 +/- 7.27, and NMI/ARI 0.8352 +/- 0.0669 / 0.8870 +/- 0.0669. Together with the spatial holdout, this supports a bounded claim: the evidence is within-farm spatial and temporal stress validation of routing semantics, not a forecast guarantee and not evidence that the rule carries to a different wind farm without local testing.

```{=latex}
\input{artifacts/goal_tables_20260612/table_future_holdout_summary_20260612.tex}
```

## Ablation

The WTB ablation exposes a controllable accuracy-semantics frontier. The completed strict-cache 50-run ablation covers dense, unconstrained, balance-only, align-only, balance-align, boundary-forced, smoothed boundary-forced, context-aligned, anchor-only, and full variants across seeds 201--205, with the routing-control mechanism gate passed for the three routing variants. The submission-facing reading is deliberately paired: every ablation row must report RMSE together with NMI/ARI. With load balancing, regime alignment, and boundary forcing active, the selected corrected router reaches NMI/ARI 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371. Boundary forcing remains an interpretability intervention with a measured forecasting price rather than a free accuracy improvement.

The ablation claim is therefore the shape of the frontier, not a ranking headline. The current strict-cache guard records 50/50 expected runs complete and 15/15 routing-gate audited runs passed; the paper uses that guard to keep the ablation as evidence for the RMSE/NMI tradeoff.

Figure 6 visualizes this frontier. Unconstrained MoE sits in the low-semantics region. $L_{align}$ moves the gate sharply upward with a modest RMSE change. The force/smooth variants continue toward cleaner partitions while moving rightward on RMSE. The full physics-aligned MoE is the routed forecasting compromise; the boundary-forced variants occupy the semantic-repair end of the frontier.

![WTB accuracy-semantics tradeoff across routing variants. Circles show NMI and squares show ARI against overall RMSE. The frontier clarifies that stronger routing correction improves gate-regime agreement but can move the model away from the lowest forecast error.](artifacts/paper_assets/figures/figure6_ablation_tradeoff.pdf){ width=82% }

## Robustness and fairness checks

The robustness and fairness checks rule out two easy explanations for the WTB result. The in-family comparisons use multiple strict-mask seeds, and the routed in-family variants share the same parameter count, making a pure capacity explanation unlikely. The completed strict-cache baseline refresh sharpens the forecasting check: Graph WaveNet is lower than the boundary-forced router by about 10.39 RMSE on average, PatchTST is lower by about 8.06 RMSE, and Graph Transformer and GAT-GRU are close in error but do not change the routing-accountability result. The reviewer pack therefore supports the same qualitative reading as the mechanism tables: the method earns its value through gate-regime responsibility, not headline error dominance. The corresponding ERA5 RMSE difference between physics-aligned MoE and the dense encoder is small and uncertain, about 0.009 (-0.061 to 0.085), and the expanded ERA5 baseline panel shows that even the best learned baseline still trails persistence. The efficiency rows add one more cost: the boundary-forced router is slower than the full physics-aligned MoE. The robustness evidence therefore supports the routing-semantics claim and keeps the accuracy claim bounded.

The strict replay, intervention, placebo, and time-forward tables below are the current robustness evidence for the corrected-router claim.

We also add negative-control and intervention audits for the strict-mask WTB gate. The five-seed strict-mask set compares the actual operating labels with labels that should not preserve the MPPT-to-pitch boundary: an 18-step temporal shift, a one-day temporal shift, node permutation, within-time node shuffling, and global label shuffling. The boundary-forced router keeps high agreement with the actual labels (NMI/ARI 0.8716 +/- 0.0374 / 0.9166 +/- 0.0332 in the placebo summary). Actual labels exceed global shuffling by delta NMI/ARI 0.8716 / 0.9166, one-day temporal shift by 0.8324 / 0.8656, and node permutation by 0.3289 / 0.2825; all bootstrap intervals are positive. The per-seed placebo table shows that this separation is not carried by one lucky run: all five seeds retain large actual-vs-global and actual-vs-one-day-shift gaps. Spatial placebos remain partially aligned because turbines share fleet-level operating distributions, but the actual labels are still clearly separated.

The mechanism intervention gives the stronger test. Reloaded strict-mask checkpoints match their saved metrics for all five runs before intervention. Zeroing the boundary anchor raises overall RMSE by 2.6792 (95% bootstrap interval 0.7347 to 4.5598), raises switch-window RMSE by 2.9470 (0.7985 to 5.1213), and drops NMI/ARI by 0.7017 / 0.8593. The per-seed intervention table sharpens the interpretation. Boundary-anchor removal collapses NMI/ARI in every seed, but the RMSE penalty is heterogeneous: seeds 202 and 205 show near-zero or slightly negative RMSE deltas while still losing most of their routing agreement. The mechanism claim is therefore about gate responsibility, not an assertion that removing the anchor always worsens headline error. Zeroing the wake score is a near-null control: overall RMSE changes by 0.0031 (-0.0016 to 0.0110), and NMI/ARI drop by about 0.0010 / 0.0010. This moves the WTB claim beyond correlation or visualization: the gate depends on the intended boundary anchor, not on any arbitrary physical channel.

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_mechanism_effects.tex}
```

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_mechanism_per_seed.tex}
```

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_placebo_effects.tex}
```

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_placebo_per_seed.tex}
```

The same evidence stack is traceable to source files in \path{artifacts/strict_wtb_evidence_sources_20260609}, which contains per-seed CSV files, generated LaTeX tables, and a SHA256 manifest for the input and output artifacts.

## Time-forward stress test

A post-hoc time-forward test-slice audit asks whether the strict-mask evidence survives later test windows. The answer is split. Routing semantics remain stable: in the late test block, the corrected router keeps NMI/ARI 0.8661 +/- 0.0393 / 0.9079 +/- 0.0364, and late-minus-early NMI is +0.0068 with a 95% bootstrap interval from 0.0021 to 0.0127. Forecasting accuracy, however, worsens in the late block. Late-minus-early overall RMSE is +50.3454 (46.8137 to 54.1758), and switch-window RMSE is +63.3549 (60.7291 to 65.3319). The added distribution-shift diagnostics explain this as a boundary condition: the late block has higher mean target power (+52.70), a large regime-share shift (total variation 0.2983, Jensen-Shannon divergence 0.0539), lower mask-valid coverage (-0.1446), and a lower mean wind-speed anchor (-0.3028) but much larger pitch action (+13.9845 in mean Pab). The gate still tracks the physical partition, but the value map faces a different operating distribution. This audit therefore supports a routing-semantics claim while weakening any time-robust forecasting claim. It is a stress test on saved test predictions, not a replacement for an external dataset or a pre-specified future-period holdout.

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_time_forward.tex}
```

```{=latex}
\input{artifacts/strict_wtb_evidence_sources_20260609/generated/table_strict_wtb_late_shift_diagnostics.tex}
```

## Sensitivity checks

Table 8 tests whether WTB routing recovery depends on a single hand-picked boundary or one large loss weight. Across three-seed sweeps, changing $\lambda_{\mathrm{align}}$ from 2500 to 7500 keeps NMI in the 0.8255--0.8546 range, and changing $\lambda_{\mathrm{force}}$ from 5000 to 15000 keeps NMI in the 0.8091--0.8406 range. The new label-validity audit then re-labels the saved strict-cache gate outputs over the local grid rated-wind $\{10.0,10.5,11.0\}$ and pitch-threshold $\{1.5,2.0,2.5\}$ without retraining. The worst grid point still has NMI/ARI 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377, and the minimum shared-valid support is 0.9909. These rows are threshold/label validity checks and mask controls, not the semantic negative control. The semantic negative-control claim is reserved for `boundary_negative_controls_wtb` and the routing placebo audit, where deliberately incorrect or shifted labels are checked against the same intervention evidence. The main WTB result keeps the pre-specified operating-boundary rule.

```{=latex}
\input{artifacts/paper_assets/generated/table_8_wtb_sensitivity.tex}
```

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} WTB threshold/label validity audit for saved strict-cache gate outputs.}
\input{artifacts/threshold_label_validity_audit_wtb_strictmask/table_threshold_label_validity.tex}
\end{table}
```

## Claim boundary

```{=latex}
\begin{table}[t]
\centering
\footnotesize
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table 9.} Claim boundary for the current manuscript.}
\input{artifacts/applied_energy_diagnostics/table_claim_boundary_applied_energy.tex}
\end{table}
```

The external Kelmarsh/Penmanshiel result is a failed boundary-condition test, not a new-site success. The source guard completes 80/80 runs, both leave-one-farm-out directions, and the chronological sanity checks, but the default WTB boundary gives mean routing NMI 0.4877, below the pre-specified 0.50 external-site routing criterion; the rescue guard therefore forbids portability wording and records the safe fallback as within-WTB boundary routing evidence with external boundary-condition diagnostics. We add local recalibration only to explain the failure mode. For each routing run, the validation gate output selects a farm-specific rated-wind/pitch-threshold pair from the pre-specified grid, and that selected boundary is evaluated once on the test gate output. This does not retrain the forecaster and does not rescue an out-of-site mechanism claim. Overall default test NMI rises only from 0.1324 to 0.1491 after recalibration, a recovery of +0.0167. Kelmarsh chronological runs recover more agreement, but Penmanshiel chronological and the leave-one-farm-out settings remain weak, so the failure is not merely a shifted threshold.

The small calibration-window adaptation makes that boundary sharper. Using only each run's validation gate outputs, the diagnostic selects a local rated-wind/pitch pair and a majority-vote gate-to-regime map, then freezes both before evaluating held-out test gates. The guard completes 40/40 routing runs, but site-specific adaptation wording remains forbidden. Chronological adapted balanced accuracy averages 0.4787, below the 0.50 diagnostic threshold. Penmanshiel chronological improves from 0.4000 to about 0.5000 balanced accuracy, but Kelmarsh chronological declines and the leave-one-farm-out Penmanshiel-to-Kelmarsh setting collapses. The result is therefore a completed negative adaptation diagnostic: local boundary estimation is necessary, but this small window is not sufficient to restore robust usable routing at a new site.

The failure conditions are operationally informative. Kelmarsh has 6 Senvion MM92 turbines, whereas Penmanshiel has 14 retained Senvion MM82 turbines. Pitch-feature coverage and boundary support differ sharply, especially in leave-one-farm-out caches, and the regime shares move from WTB's 39.47% idle, 52.00% MPPT, and 8.53% pitch-control partition to Kelmarsh's MPPT-heavy chronological partition and Penmanshiel's larger pitch-control share. These differences in sensor fields, pitch observability, turbine geometry, farm scale, power-curve distribution, and label balance are exactly the conditions under which the WTB operating-boundary rule must be re-estimated and tested before any site-level claim.

```{=latex}
\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table.} Why external wind-farm portability failed and how the result is used.}
\input{artifacts/applied_energy_diagnostics/table_external_site_transfer_failure.tex}
\end{table}
```

# Discussion

The main result is a rule for using physics-aligned routing in wind-power operations: correction strength should scale with regime observability and with the operating decision that will consume the gate. ERA5 already exposes the regime marker through sensible heat flux and its temporal variation, and persistence is hard to beat on RMSE. In that setting, the corrected gate improves regime alignment over Unconstrained MoE without creating a better headline forecasting map. WTB is different. Wake interaction and blade-pitch control blur the MPPT-to-pitch boundary, so the router needs stronger repair to recover a useful partition. The WTB-ERA5 contrast is the paper's main scientific insight: the same routing prior has different value depending on how much of the physical boundary is already visible in the observations.

The price is explicit. Graph WaveNet is the most stable black-box WTB forecaster, while LightGBM and XGBoost lag-feature baselines show that simple engineering predictors remain highly competitive. Inside the routed family, the full physics-aligned MoE is the forecasting compromise, while the boundary-forced router is the semantic-repair variant. Regime-anchor alignment buys a large share of the partition recovery with a modest RMSE change. Boundary forcing buys a cleaner gate at a clear forecasting cost. That is the paper's practical claim: gate correction is a modeling choice with measurable error and reserve-policy tradeoffs.

For mechanism-aware forecasting studies, physics has to constrain the routing decision itself. Many physics-guided models act on outputs or latent states, which suits tasks where the goal is physical consistency after prediction. Here the decision is earlier: which local predictor takes responsibility near a mechanism change. The MPPT-to-pitch boundary is a physically meaningful stress point because it changes reserve shortage risk and ramp-risk interpretation even when fleet-level average error moves only modestly. Boundary-focused forcing encodes that stress point at the router. It sacrifices some RMSE to keep the gate from drifting into a semantically useless partition.

The method is appropriate when the operating boundary is part of the scientific question. Examples include turbine-control transitions, curtailment regimes, and geophysical stability states where the active mechanism matters, not only the scalar error. It is a poor choice for a pure leaderboard objective, for settings where persistence or a black-box graph model is already adequate, or for problems without a defensible regime anchor. In those cases, the extra routing losses add complexity without a clear mechanism-evidence return. The target use case is the middle ground: mechanism boundaries are important enough that interpretable responsibility can justify a measured forecasting penalty. This positioning also explains why the strongest claim is about controlled responsibility assignment rather than broad cross-dataset superiority.

# Limitations

The WTB correction depends on threshold-based pseudo-labels derived from wind speed and mean pitch angle. Those thresholds are physically motivated and consistent with the implemented data pipeline, but they impose a hand-crafted boundary definition. The method is boundary-aware regularized routing.

The comparison is bounded. Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, persistence, physical power curve, XGBoost/LightGBM lag features, and a DLinear-style LTSF readout provide completed strict-cache WTB forecasting baselines, and ERA5 is checked against persistence plus Graph WaveNet, STGCN, PatchTST, and TCN. The strict-anchor-mask rerun covers the selected WTB corrected router, replay, intervention, placebo, time-forward audits, a synchronized baseline refresh, a spatial node-held-out stress test, a future-period holdout, and the transition-window reserve audit. Market-level and dispatch-level reserve optimization, unit commitment, stochastic reserve optimization, larger general time-series backbones, and broader graph-transformer variants are outside the present benchmark. External wind-farm diagnostics are complete but fail the external-site routing criterion: the Kelmarsh/Penmanshiel guard reaches 80/80 completed runs in both leave-one-farm-out directions, while the default WTB boundary remains below the declared threshold. The added local recalibration table records how much agreement is recovered when rated-wind/pitch boundaries are re-estimated on validation gates and then fixed on test gates. The external taxonomy points to farm scale, turbine geometry, pitch observability, sensor-field coverage, power-curve differences, and regime-label imbalance as the main boundary conditions. The evidence therefore supports within-WTB spatial and temporal stress validation of routing semantics and operating-boundary reserve diagnostics, plus an external diagnostic of when those semantics need local boundary re-estimation.

The time-forward audit is not an external validation. It is a post-hoc split of saved WTB test predictions into contiguous anchor-time blocks. It shows that the strict-mask gate keeps its physical partition in the late block, but it also shows a large late-test RMSE increase. The failure case is therefore explicit: late-period distribution shift preserves routing agreement while degrading value prediction. This is an important boundary condition: the method currently supports routing semantics, not time-robust forecasting robustness.

The WTB ablation is scoped. The strict-cache 50-run ablation guard passes, but each cited row must report RMSE together with NMI/ARI. The ablation supports the observed accuracy-semantics tradeoff; it does not convert the routed model into the lowest-error predictor.

Statistical reliability is uneven across claim types. The completed strict-cache WTB baseline refresh provides five seeds each for Graph WaveNet, Graph Transformer, GAT-GRU, and PatchTST, and the selected boundary-forced router has five strict-cache seeds, five future-holdout seeds, and five seeds for each spatial-holdout routing comparator. ERA5 has five seeds for the in-family models and three seeds for the learned baselines. The engineering baselines and reserve-window audit are deterministic or sampled strict-cache diagnostics rather than five-seed neural families. Semantic negative controls are taken from `boundary_negative_controls_wtb`, and the mask/threshold sensitivity controls are reported as sensitivity checks only. The external Kelmarsh/Penmanshiel guard is complete at 80/80 but remains `within_wtb_only`; the recalibration and small-calibration-window adaptation diagnostics are therefore reported as boundary-condition analyses, not as new training results or external-site evidence. The strongest statistical claims are therefore the strict-mask replay-safe routing-recovery, mechanism-intervention, failure-case transparency, and within-WTB spatial/temporal stress claims.

The paper studies two observability settings. WTB and ERA5 are enough for the intended contrast between weakly and strongly expressed regime markers, with ERA5 serving as a positive/contrast control rather than as the main performance contribution. Applying the same interpretation to other industrial or geophysical systems will require re-estimating the operating boundary, checking sensor availability, and rerunning the routing gate before making a local mechanism claim.

# Conclusion

This paper turns non-stationary wind-power forecasting into a routing problem around operating transitions. The completed strict-cache WTB comparison gives a blunt accuracy result: strong graph, transformer, and lag-feature baselines achieve lower mean RMSE than the boundary-forced routed model. The strict-anchor-mask evidence then tests the selected router more severely: across five seeds it recovers the operating partition, passes checkpoint replay, fails under boundary-anchor removal, survives placebo controls, remains meaningful under spatial and future-period holdouts, and keeps routing semantics in late test windows. ERA5 carries the same lesson as an observability contrast: when the regime marker is visible and persistence is strong, physics-aligned routing improves gate-regime agreement more than headline forecasting accuracy.

The practical conclusion follows directly. When the regime marker is visible, routing regularization calibrates an already available partition. When the marker is partly hidden by control logic, physics guidance at the gate can repair a weakly identified partition and provide a transition-window reserve/ramp-risk signal, but it trades against forecast error and does not create a globally better reserve policy. Physical forecasting with multiple local response laws therefore needs supervision over responsibility as well as supervision over values. The completed external wind diagnostic shows that this responsibility claim must be re-established when turbine geometry, pitch observability, sensor fields, power curves, or label distributions change; a small validation-window adaptation did not restore robust held-out routing in Kelmarsh/Penmanshiel. The gate is part of the model's scientific claim, and the right question is whether that claim is worth its measured error, reserve, robustness, and efficiency costs in the target operating setting.

# Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work, the authors used OpenAI ChatGPT/Codex to support language editing, consistency checking, and submission-material drafting. After using these tools, the authors reviewed and edited the content as needed and take full responsibility for the content of the published article.

# Code and data availability

The experiments use four public source families: the KDD Cup 2022 wind-farm SCADA benchmark, ERA5 reanalysis fields, and the Kelmarsh and Penmanshiel wind-farm SCADA records. Source datasets remain available from their original providers. The release package records provider links, checksums, and reconstruction scripts rather than redistributing any source files whose original terms require provider-side access. The Kelmarsh and Penmanshiel sources are tracked in the reproducibility manifest as CC-BY-4.0 source-data guards and protocols; their completed 80-run guard, recalibration table, and small-calibration-window adaptation table are cited only as boundary-condition evidence because new-site portability is not claimed. The final evidence export includes table, figure, source-data, guard, and trace manifests; each submission-facing table or figure is linked to source files, seed lists, run tables, raw prediction paths, checkpoint hashes, and SHA256 hashes where file size permits. Code, configuration files, scripts, derived caches when licensing permits, model-weight/checkpoint hashes, seed-level CSV summaries, final figure source data, and evidence manifests can be released with the manuscript. Raw third-party data that cannot be redistributed will be accompanied by download instructions and rebuilding scripts. The one-command reproduction package rebuilds the strict evidence package, the engineering baseline panel, the transition-window reserve audit, the reserve guard, the external recalibration and small-calibration diagnostics, the final evidence manifest, and the reproducibility manifest with relative paths. The study uses turbine and atmospheric measurements only and involves no human participants or human-subject data.

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
