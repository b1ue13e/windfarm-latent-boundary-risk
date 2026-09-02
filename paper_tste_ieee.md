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
  - \setlist[itemize]{leftmargin=1.6em}
  - \AtBeginEnvironment{CSLReferences}{\footnotesize}
---

\title{Auditable SCADA-Anchored Routing for Wind-Turbine Reserve Diagnosis at the MPPT-to-Pitch Boundary}

\author{%
\IEEEauthorblockN{Junyu Li and Juntao Du\IEEEauthorrefmark{1}}
\IEEEauthorblockA{School of Statistics and Applied Mathematics,
Anhui University of Finance and Economics, Bengbu 233030, China\\
\IEEEauthorrefmark{1}Corresponding author: \texttt{dujuntao@aufe.edu.cn}}
}

\maketitle

\begin{abstract}
Reserve screening near the maximum-power-point-tracking (MPPT) to blade-pitch transition requires an operating-state signal, but the confirming threshold stream can be delayed, incomplete or noisy. Existing wind-power forecasters reduce aggregate error, yet they rarely expose the control boundary that produced an individual forecast. We evaluate whether a SCADA-anchored mixture-of-experts gate can provide that missing audit record without using future active power. On the KDD Cup 2022 wind-farm benchmark, a class-weight rerun using training data only reaches an RMSE of 229.93, compared with 224.34 for iTransformer, while retaining mean gate alignment of NMI 0.721 and ARI 0.740. A signature-gate identifiability probe further shows that the boundary remains recoverable (NMI 0.561) even when the label-defining wind-speed and pitch-angle channels are withheld from the gate, and that this recovery collapses to chance (NMI 4e-6) when the same regime labels are permuted. The separately archived full-audit checkpoint has stronger alignment (NMI 0.872 and ARI 0.917) but a larger RMSE price (236.13), so the two evidence packages are kept distinct. With a six-step delay in the confirming label stream, the saved gate recalls 0.960 of early pitch-window cells, whereas the delayed threshold rule recalls 0.196. A simple issue-time anchor classifier achieves 1.000 recall and 0.879 precision on clean anchors; the contribution is therefore in-model route provenance rather than standalone detector superiority. At a shortage-to-reserve cost ratio of 10, gate-conditioned binning reduces same-router boundary-window shortage energy by 14.5\% and violation rate by 1.38 percentage points, but physical-bin and full-sample comparisons prevent a policy-optimality claim. Retraining on ENGIE La Haute Borne provides anchor-observable mechanism replication (NMI 0.941), whereas Kelmarsh and Penmanshiel fail the observability and held-out routing gates. The resulting contribution is a bounded diagnostic layer for transition-window reserve screening, not a replacement for low-RMSE forecasting or market dispatch.
\end{abstract}

\begin{IEEEkeywords}
Wind-turbine control boundary; SCADA-anchored routing; regime-aware forecasting; auditable routing; MPPT-to-pitch transition; mixture-of-experts.
\end{IEEEkeywords}

# Introduction

Wind-farm reserve screening near the transition from maximum power point tracking (MPPT) to blade-pitch control requires knowledge of the active control law. The confirming threshold stream, however, can arrive late, disappear during telemetry loss, or become unreliable after quality control. This matters because wind-power forecasting is operationally coupled to ramp exposure, reserve requirements and imbalance risk, rather than to aggregate error alone [@pinson2013forecasting; @doherty2005reserve; @wang2025uncertaintyreview]. In the MPPT region, active power responds strongly to wind-speed variation. Once pitch control becomes active near rated operation, the local response law changes. A small forecast error can therefore correspond to a different control state, even when the transition contributes little to fleet-average RMSE. A useful system should consequently expose the operating boundary associated with each forecast and remain interpretable when the confirming label stream degrades.

Recent spatio-temporal forecasters encode turbine coupling, wake interaction and sensor-rich wind-farm layouts with graph or attention mechanisms [@wu2019graphwavenet; @park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore]. They provide an appropriate accuracy reference, but a low-error encoder does not reveal whether a turbine is operating under an MPPT-like or pitch-control-like response law. Mixture-of-experts (MoE) models provide a natural language for heterogeneous response laws, although prediction loss alone does not guarantee a physically meaningful partition [@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @fedus2022switch]. The unresolved problem is therefore not another aggregate forecaster. It is an auditable assignment that links an issue-time route to a declared operating boundary and can be consumed by a reserve-risk diagnostic.

Here we treat the routing decision as the operating-boundary diagnostic. A node-level MoE gate is constrained by SCADA anchors, allowing each turbine-time assignment to be compared with a declared MPPT-to-pitch partition before future active-power outcomes are available. WTB is used as the control-confounded benchmark because the aerodynamic boundary is partly embedded in turbine-control action. ERA5 is retained as an observability contrast in which sensible heat flux exposes the thermodynamic marker [@hersbach2020era5]. ENGIE La Haute Borne provides a second anchor-observable SCADA farm for local mechanism replication, whereas Kelmarsh and Penmanshiel define deployment gates when pitch and boundary support are absent. The recovered route is then connected to validation-calibrated, test-frozen reserve diagnostics that report cost, violation rate, reserve energy and shortage energy. We compare gate-bin allocation with global and physical-bin empirical-quantile baselines. This design separates transition-window accountability from the forecasting leaderboard and from full dispatch optimisation.

The operator-facing workflow is intentionally narrow. At issue time, the model may use current SCADA anchors, historical active power, graph state and missingness masks, but it cannot use future active power. A confirmed regime label is treated as a separate stream because validation, telemetry or quality-control logic can delay it. We therefore report a modular forecaster-plus-classifier control rather than implying that the gate is the best standalone detector. The proposed advantage is narrower: one saved run links route probability, forecast residual, reserve bin and anchor evidence for each escalated cell. The router is consequently an in-model provenance layer, not an anchor-free discovery device or a replacement for a low-error forecaster.

This paper makes three bounded contributions. First, it defines SCADA-anchored routing as an auditable MPPT-to-pitch assignment whose semantics are fixed before test evaluation, and shows that the boundary remains identifiable when the label-defining wind-speed and pitch-angle channels are withheld from the gate. Second, it quantifies the consequence of delayed, incomplete and noisy confirmation labels while disclosing a stronger clean-anchor classifier control. Third, it connects the route to a validation-frozen boundary-window reserve screen and specifies the observability and held-out checks required before transfer. The training-only rerun provides the provenance-corrected RMSE guardrail, whereas the archived full-audit checkpoint carries the saved route and reserve artifacts; these evidence roles are reported separately. La Haute Borne is used as anchor-observable mechanism replication, not automatic cross-farm generalisation. The resulting system is a complementary diagnostic layer for an already-deployed forecaster, not a replacement for the forecasting leaderboard or market dispatch.

# Related Work

## From average wind-power accuracy to transition-window risk

Wind-power forecasting has progressed from site-specific statistical models to spatio-temporal architectures that represent ramps, uncertainty and spatial coupling [@pinson2013forecasting; @wang2025uncertaintyreview]. Graph models provide a strong accuracy reference by propagating information across the network [@wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn]. Wind-specific studies have further introduced wake-aware graphs, SCADA integration and physics-guided constraints [@park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore; @zehtabiyan2023physicsguided]. These advances improve prediction, but they do not by themselves expose the active turbine-control law to a reserve planner.

MoE routing can represent local response laws, but prediction loss alone does not determine whether the resulting partition has operating meaning [@shazeer2017outrageously; @fedus2022switch]. Physics-guided machine learning supplies general principles for introducing scientific constraints, while wind-turbine operating states remain limited by SCADA observability [@karpatne2017tgds; @karniadakis2021piml; @tautzweinert2017scada]. Our distinction is therefore the location of the constraint. Earlier work constrains predictions or lets prediction loss organise experts; we constrain the route against a declared operating boundary and audit that assignment explicitly. This framing makes no anchor-free discovery claim. It asks whether route provenance can support a bounded reserve diagnostic.

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

## Operating-boundary anchors and labels

The gate is not supervised everywhere. It is anchored where the physical interpretation is clearest, while ambiguous samples remain governed by prediction loss and routing regularisation. This design follows the theory-guided learning principle that scientific constraints should enter the learning problem at an identifiable interface [@karpatne2017tgds; @karniadakis2021piml]. The engineering layer defines what counts as a control regime and when that regime is observable from the data [@tautzweinert2017scada].

### WTB operating regimes

In WTB, the primary operating boundary is the transition from MPPT to pitch control. Let

$$
\bar{p}_{i,t} = \frac{1}{3}\left(p^{(1)}_{i,t}+p^{(2)}_{i,t}+p^{(3)}_{i,t}\right).
$$

The WTB column name `Pab` denotes blade pitch angle. We use $\bar{p}_{i,t}$, also reported as `Pab_mean` in tables and figures, for the three-blade pitch average. The regime labels use wind speed and mean pitch angle at the anchor time, not future active power.

Using a cut-in threshold $u_{\mathrm{idle}}$, a pitch-transition threshold $u_{\mathrm{rated}}$, and a pitch-angle threshold $p_{\mathrm{th}}$, and writing $w_{i,t}=\texttt{Wspd}_{i,t}$ for compactness, we define

$$
R^{\mathrm{wtb}}_{i,t} =
\begin{cases}
0, & w_{i,t}<u_{\mathrm{idle}} \quad \text{(idle)},\\
1, & u_{\mathrm{idle}}\le w_{i,t}\le u_{\mathrm{rated}},\ \bar{p}_{i,t}<p_{\mathrm{th}} \quad \text{(MPPT)},\\
2, & w_{i,t}>u_{\mathrm{rated}},\ \bar{p}_{i,t}\ge p_{\mathrm{th}} \quad \text{(pitch-control)},\\
3, & \text{otherwise} \quad \text{(transition)}.
\end{cases}
$$

Only the first three classes are used in direct alignment. Transition samples are retained for analysis but masked out of label supervision through

$$
M^{\mathrm{wtb}}_{i,t} = \mathbf{1}[R^{\mathrm{wtb}}_{i,t} \neq 3].
$$

The reported implementation uses $u_{\mathrm{idle}}=3.0$ m s$^{-1}$, $u_{\mathrm{rated}}=10.5$ m s$^{-1}$, and $p_{\mathrm{th}}=2.0^\circ$ (Appendix A). These thresholds are declared operating anchors, fixed before test evaluation and then audited by threshold-grid sensitivity checks; they are not universal turbine constants and are not selected by test-set NMI.

### ERA5 observability contrast (see Supplementary Material)

ERA5 is retained as a signal-expressive observability contrast where the stable-to-convective thermodynamic marker is directly visible through sensible heat flux. The detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A so that the main text remains focused on the WTB control-boundary accountability task.

## Shared architecture

### Physical graph construction

The graph is part of the physical problem specification. Directed diffusion is a natural representation when information propagates asymmetrically through a spatial network [@li2018dcrnn; @wu2019graphwavenet]. WTB therefore uses a directed wake graph: candidate turbine pairs are filtered by proximity, activated when an upstream turbine lies inside a wind-aligned downstream cone, weighted by streamwise and cross-stream decay, and pruned to the strongest inbound neighbours. This construction follows the broader use of wake and SCADA structure in physics-guided wind-power forecasting [@park2019physicsinduced; @zehtabiyan2023physicsguided]. The same directed weights define a wake score, which supplies the WTB wake auxiliary label on MPPT and pitch-control samples. ERA5 uses a symmetric Haversine-Gaussian $k_{\mathrm{nn}}$ graph because the thermodynamic regime marker is already visible in the observed state [@hersbach2020era5]. Appendix A gives the graph equations and constants.

### Directed-diffusion GRU encoder and node-level gate

The encoder is kept modest so that changes in performance can be traced to routing and regularisation rather than capacity. Each input window is concatenated with its feature-missingness mask before projection. Two directed diffusion blocks then aggregate self, inbound and outbound messages on each graph snapshot. This follows the diffusion-convolution principle used in spatio-temporal graph forecasting [@li2018dcrnn], while retaining separate inbound and outbound operators for the wind-aligned graph. Let $\mathbf{X}^{(\ell)}_{t}$ denote the node state at layer $\ell$ and time $t$. A diffusion block updates each node by

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

The difference reflects the observability contrast: WTB needs help to recover a partly hidden operating boundary, whereas ERA5 already exposes the relevant thermodynamic marker in the state. The active-power anchor is standardized from training-split statistics and is never filled from the prediction horizon.

### Routing stack and evidence boundary

This makes the routing stack an anchor-constrained diagnostic rather than an unsupervised operating-state discovery method. High gate-regime agreement means that the implemented router obeys the declared SCADA boundary under the available anchor set; it does not establish anchor-free regime recovery.

![Physics-aligned regime-aware MoE. The two datasets share the same directed-diffusion GRU encoder and node-level MoE routing mechanism. WTB uses a dynamic wake graph and a boundary-focused forcing term, whereas ERA5 uses a Haversine-Gaussian graph and a thermodynamic regime anchor.](artifacts/final_evidence_package/export/figures/figure1_architecture.pdf){ width=95% }

## Integration of Physical Constraints into Model Optimization

Prediction loss does not uniquely identify the gate when several experts can fit averaged dynamics similarly well [@shazeer2017outrageously; @fedus2022switch]. WTB makes this failure visible: inflow variation, wake disturbance, and pitch control are observed together, so a low-loss router can still ignore the operating boundary. We use routing regularizers for the specific failure modes that matter here. The total objective is

```{=latex}
\begin{align}
\mathcal{L} &= \mathcal{L}_{\mathrm{pred}}+ \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}}+ \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}}\nonumber\\\\
&\quad+ \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}}+ \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}}+ \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}},
\end{align}
```

with inactive terms set to zero. Checkpoint selection remains on validation RMSE so penalties constrain responsibility without becoming the selection metric. Exact weights are in Supplementary Appendix~A.

### Load balancing

A balancing term prevents early expert collapse before regime-specific structure has time to emerge. It couples hard top-$K$ usage with soft probability mass over valid node-time samples. Supplementary Appendix~A gives the exact expression; physical ownership is supplied only by the anchored alignment terms below.

### Regime-anchor alignment

The alignment term connects the first $C$ gate logits to the declared regime structure so that cross-seed statements such as "MPPT-aligned" refer to a fixed mapping rather than to post-hoc relabeling. With $\mathbf{z}^{(1:C)}_{i,t}$ denoting the anchored logits, $R_{i,t}$ the label, and $M_{i,t}$ the validity mask,
$$
\begin{aligned}
\mathcal{L}_{\mathrm{align}}
&= \frac{1}{|\Omega|}
\sum_{(i,t)\in\Omega}
\mathrm{CE}\!\left(\mathbf{z}^{(1:C)}_{i,t}, R_{i,t}\right),\\
\Omega&=\{(i,t):M_{i,t}=1\}.
\end{aligned}
$$
with inverse-frequency class weights. The released preprocessing code computes
these weights on the training split; the evidence package includes a
class-weight provenance audit and train-only sensitivity rerun for the frozen
strict-cache checkpoints. In that five-seed rerun, the boundary-forced router
keeps strong route recovery (NMI 0.721, ARI 0.740) while keeping the same
strict-mask evaluation boundary.

### Boundary-focused forcing (WTB only)

After coarse alignment the boundary remains partly masked by control action. A focused forcing term acts on MPPT and pitch-control samples only. With $Y^{\mathrm{force}}_{i,t}=\mathbf{1}[R^{\mathrm{wtb}}_{i,t}=2]$ for $R^{\mathrm{wtb}}_{i,t}\in\{1,2\}$,
$$\mathcal{L}_{\mathrm{force}} = \frac{1}{|\Omega_{\mathrm{force}}|}\sum_{(i,t)\in\Omega_{\mathrm{force}}}\mathrm{CE}\!\left(\left[z^{(\mathrm{mppt})}_{i,t}, z^{(\mathrm{pitch})}_{i,t}\right]^{\top}, Y^{\mathrm{force}}_{i,t}\right),$$
where $\Omega_{\mathrm{force}}=\{(i,t):R^{\mathrm{wtb}}_{i,t}\in\{1,2\}, M_{i,t}=1\}$. This term is not a lead-time switch predictor; it is a boundary identifiability regularizer for the issue-time operating state.

### Wake auxiliary supervision and graph smoothness

A wake auxiliary label identifies residual wake ambiguity inside MPPT and pitch-control samples, and a graph-smoothness penalty discourages noisy neighbor-to-neighbor gate jumps. Both formulas are in Supplementary Appendix~A.

## Operational reserve diagnostic protocol

The reserve diagnostic tests whether a physically auditable gate changes the reserve trade-off in the MPPT-to-pitch window after the point-forecast model has been trained. Quantile-based reserve rules are widely used to translate forecast error into operational decisions [@bremnes2004quantile; @nielsen2006quantile]. We adapt that logic to a deliberately narrower screening task. For each saved WTB run, validation predictions select reserve levels; test predictions are then evaluated once with those levels fixed. The protocol follows the same information boundary as an operator who calibrates a short-term reserve rule before using it on a later period.

Let $\hat{y}_{i,t}$ be the scheduled point forecast and $y_{i,t}$ the realized active power at an evaluated horizon cell. We define over-forecast shortfall as

$$
s_{i,t} = \max(\hat{y}_{i,t} - y_{i,t}, 0),
$$

because this is the error direction that leaves a reserve schedule exposed. For a reserve policy $b$ and empirical quantile $q$, the validation split estimates a reserve level

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

The selected $(b,q)$ rule is then frozen and applied to the test split. The reported test metrics are total cost $C$, violation rate $\Pr[s_{i,t}>r_b]$, reserve energy $\sum r_b\Delta t$, and shortage energy $\sum \max(s_{i,t}-r_b,0)\Delta t$. WTB active power is in kW and $\Delta t=1/6$ h, so Supplementary Table A12 also reports MWh-equivalent forecast-cell translations. These are not delivered market energy or settlement costs: a value written as 84.58M denotes 84.58 million reserve-cost-equivalent kWh cells, not currency.

The cost ratio $\rho$ is an energy-system assumption rather than an abstract tuning knob. If the marginal cost of carrying one unit of reserve energy is $C_r$, then $\rho=10$ charges one unit of residual shortage as $10C_r$. Ratios 5--10 represent moderate reliability settings such as transition-window scheduling or imbalance screening; ratios 20--50 represent scarcity-aware screening where shortage avoidance dominates local cost savings. The primary diagnostic compares Graph WaveNet/global, Graph WaveNet/physical-bin, boundary router/global, and boundary router/gate-bin policies. Only same-model global comparisons attribute gate-bin reserve effects to the learned router.

The market-facing use case is therefore a pre-dispatch reserve and imbalance-risk screening log rather than a settlement model: the saved run records route probability, reserve bin, selected quantile, residual shortfall, and anchor state for each escalated transition-window cell. A balancing desk can use this record to prioritize transition-window cells for operator review or reserve sensitivity checks before settlement exposure is known. A modular low-RMSE forecaster plus issue-time classifier can also emit a state flag; the extra value claimed here is narrower--same-run responsibility attached to the forecast residual and reserve slice, not superior clean-anchor classification or market-clearing profit.

To bound this diagnostic against a probabilistic reserve alternative, we additionally run validation-frozen empirical quantile baselines for the global and physical operating bins. These are not trained distributional forecasters; they are conformal-style shortfall reserves estimated on the validation split and evaluated once on the test split. The main reported boundary window is fixed at $\pm 1.0$ m s$^{-1}$ around rated wind and the main cost ratio is $\rho=10$, with sensitivity at $\rho \in \{2,5,10,20,50\}$. A separate toy operational-cost module reports reserve procurement plus $\rho$-weighted residual-shortage penalty and excludes optimal power flow, unit commitment, market clearing, delivery constraints, and price claims.


# Case Study Configuration and Operational Constraints

## Datasets and preprocessing

The experiment uses two observability settings, not two interchangeable benchmarks. WTB is the control-confounded case. The KDD Cup 2022 benchmark contains 134 turbines and 245 days of 10 min SCADA measurements [@zhou2024sdwpfdata]. Its role is to test whether a declared control boundary can be made auditable when inflow variation, wake disturbance and blade-pitch control are mixed in the same stream. The MPPT-to-pitch transition is therefore only indirectly visible from the aggregate forecast inputs.

The data are reorganized into synchronous tensors with $T=35{,}280$ time steps, $N=134$ turbines, and $F=11$ dynamic inputs. Missing inputs are forward-filled within turbine and then completed with training-set means. Invalid or non-positive active power is retained only through its mask so that the model still sees operational irregularity without treating those points as supervised targets.

ERA5 is the signal-expressive case. We use three archived months over a fixed $16 \times 16$ hourly patch [@hersbach2020era5]. Its role is not to provide a second wind-power leaderboard, but to contrast a setting in which the thermodynamic marker is directly visible through sensible heat flux. The retained tensor has $T=2208$ frames, $N=256$ nodes and eight input variables. Both datasets use the same history and horizon lengths, $H=36$ and $P=24$, so differences in performance cannot be attributed to unequal context length. The chronological split is 180/30/35 days for WTB and 1325/441/442 frames for ERA5.

## Techno-Economic Validation and Benchmarking Framework

The comparison has two layers. The first isolates the routing mechanism after shared-capacity explanations have been controlled. The dense baseline uses the same directed-diffusion GRU encoder and replaces the expert mixture with one dense prediction head. The unconstrained MoE adds routed capacity without physical correction. The corrected-routing comparator is dataset-specific: ERA5 uses the full corrected stack, whereas WTB uses the boundary-focused variant selected for gate recovery. Parameter budgets are matched within each dataset. This in-family comparison is necessary because MoE studies distinguish the effect of routing capacity from the effect of routing constraints [@jacobs1991adaptive; @shazeer2017outrageously; @fedus2022switch].

The second layer tests the RMSE price against stronger and more engineering-facing baselines. Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE are included for WTB [@nie2023patchtst; @liu2024itransformer; @das2023longterm], together with deterministic persistence, a fitted physical power-curve baseline, XGBoost and LightGBM lag-feature predictors, and a DLinear-style LTSF baseline. Graph WaveNet, STGCN, PatchTST, TCN, and a deterministic persistence predictor are included for ERA5. This split avoids using one comparison for two different claims. The in-family layer tests whether physical routing changes the learned partition under a fixed backbone. The baseline layer tests whether the routing intervention remains honest about forecast error when compared with established temporal, graph, and engineering predictors.

For compactness, the mechanism tables shorten the three in-family model names to **Dense (matched)**, **Unconstrained MoE**, and **Corrected routing comparator**. The main WTB forecasting table reports representative strong baselines, including the best strict-cache baseline used for the RMSE price, while the full neural, anchor-only, and engineering baseline records remain in the source tables. The ERA5 forecasting tables additionally report persistence and four learned external baselines. The in-family mechanism families are summarized in Supplementary Appendix~A so that the Results section can focus on evidence rather than model bookkeeping.

## Training protocol and evaluation metrics

All neural models use the same training protocol where the architecture permits it. We use AdamW, early stopping on validation RMSE, gradient clipping, and mixed-precision training on a single CUDA-enabled GPU. Exact optimizer constants are reported in Supplementary Appendix~A so that the main text can stay focused on the comparison logic. The WTB dense baseline, Unconstrained MoE, full physics-aligned MoE, and boundary-forced router are repeated across five strict-mask seeds. The synchronized strong-baseline refresh covers Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, and TiDE across seeds 201--205, giving 30 completed baseline runs under the same strict anchor-valid evaluation cache. The engineering WTB baselines are deterministic or sampled single-run readouts from the same frozen cache and are used to anchor practical forecast difficulty rather than to make a seed-level neural ranking. ERA5 main in-family models are repeated across five seeds, and the ERA5 learned baselines are repeated across three seeds. Thresholds and routing weights are set before test evaluation and then audited by sensitivity sweeps and boundary negative controls, so the main routing result is not selected by test-set NMI.

The metrics follow the claim. Overall MAE and RMSE measure forecasting accuracy. Switch-window MAE and RMSE use the evaluator's transition-window mask around regime changes. This is distinct from the later boundary-band audit, which isolates anchors within +/-1.0 m s$^{-1}$ of the WTB rated-wind MPPT-to-pitch boundary. Regime-wise RMSE locates the error reduction. Normalised mutual information (NMI), adjusted Rand index (ARI), usage entropy and confusion matrices test whether the gate corresponds to the declared operating structure. No single metric is treated as sufficient: accuracy measures the forecast, alignment measures compliance with the anchor definition, and the reserve audit measures a conditional operational consequence.

Figure 2 gives the operating-decision context before the forecasting results are introduced: graph geometry shows where forecast errors propagate, and the regime-anchor panels show which sensor-derived boundaries can support reserve diagnostics.

![Operating-decision context and physical regime anchors. (A) WTB turbine layout with the schematic wake cone and retained candidate radius used in the dynamic directed wake graph. (B) ERA5 16x16 patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{mean})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.](artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf){ width=97% }

# Evidence and Operational Boundary Diagnosis

The results are organised as an evidence ladder. We first establish the information boundary and the accuracy price of routing. We then test boundary recovery, intervention and holdout behaviour. Next, we quantify early-window recall when the confirming label stream is delayed or incomplete. Finally, we evaluate the reserve consequence and define deployment gates. This order distinguishes what the model predicts from what the route allows an operator to audit.

## Can the Gate Recover the Operating Boundary?

The first question is whether routing improves forecast accuracy. It does not. Across five WTB seeds, the boundary-forced router reaches RMSE 236.13 +/- 8.41, compared with 224.34 +/- 2.23 for iTransformer and 225.74 +/- 2.60 for Graph WaveNet. The router is therefore 11.79 RMSE units above iTransformer and 10.39 units above Graph WaveNet. The provenance-corrected train-only rerun reduces this gap to 5.59 units, with RMSE 229.93 +/- 2.50, but its route artifacts are not the same saved checkpoint used in the full operational audit. We consequently treat the routed forecaster as a diagnostic layer with an explicit accuracy price, not as a forecasting leaderboard replacement.

The second question is whether the selected boundary is a meaningful stress slice. Anchors within +/-1.0 m s$^{-1}$ of rated wind have RMSE 321.17 +/- 21.31, approximately 67 units above valid non-boundary MPPT/pitch anchors. The same band has mixed-regime structure, with NMI/ARI of 0.6562/0.7766. These observations motivate the reserve audit, but they do not show that routing caused the stress. ERA5 serves only as an observability contrast: the thermodynamic marker is directly visible there, so alignment can be examined separately from the WTB control-confounded case.

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{Operating-boundary recovery and mechanism checks.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.30\linewidth} >{\raggedright\arraybackslash}p{0.34\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Check & Metric & Result \\
\midrule
WTB boundary-forced router & Gate-regime NMI / ARI & 0.8716 +/- 0.0418 / 0.9166 +/- 0.0371 \\
Train-only class-weight rerun & Gate-regime NMI / ARI; overall RMSE & 0.7208 / 0.7398; 229.93 \\
WTB boundary-band audit & Boundary-band RMSE; mixed-regime NMI / ARI & 321.17 +/- 21.31; 0.6562 / 0.7766 \\
Boundary-anchor intervention & Overall RMSE change; NMI / ARI drop & +2.6792; 0.7017 / 0.8593 \\
WTB spatial and time holdouts & Held-out-node NMI / ARI; future-holdout NMI / ARI & 0.8340 / 0.8829; 0.8352 / 0.8870 \\
La Haute Borne re-trainability check & NMI / ARI & 0.9408 +/- 0.0336 / 0.9712 +/- 0.0201 \\
Threshold-grid audit & Worst-case saved-gate NMI / ARI & 0.8655 +/- 0.0429 / 0.9146 +/- 0.0377 \\
\bottomrule
\end{tabularx}
\end{table}
```

## Withheld-channel signature recovery

The route is then tested for circularity. If the gate merely replayed the threshold rule, removing the wind-speed and pitch-angle channels from the anchor should destroy alignment. Instead, a signature-gate probe zeros `Wspd` and `Pab_mean` at the anchor while retaining active power and the remaining consequence channels, and re-trains five seeds from a frozen strict cache. The gate still recovers the operating boundary with mean NMI 0.561 and ARI 0.635 (Table \ref{tab:signature-gate}; per-seed values in Supplementary Table A9b). Removing active power as well (`signature_core`) drops mean NMI to 0.367, with three of five seeds collapsing to a single expert; the non-power consequence channels therefore carry a weaker but non-zero signature. When the withheld-channel probe is repeated with permuted regime labels, NMI collapses to 4e-6, confirming that the 0.561 result is not an accidental correlation between input statistics and the threshold rule.

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{Signature-gate identifiability probe on WTB. The gate anchor never sees the withheld channels. All values are mean$\\pm$sd over five seeds; collapsed seeds are noted for `signature_core'.}
\label{tab:signature-gate}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.30\linewidth} >{\centering\arraybackslash}p{0.18\linewidth} >{\centering\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Probe & RMSE & NMI / ARI & Interpretation \\
\midrule
Canonical full-anchor & 229.93 & 0.7208 / 0.7398 & Train-only clean baseline \\
`signature_full' (no Wspd/Pab_mean) & 241.84 $\\pm$ 7.19 & 0.5613 $\\pm$ 0.0199 / 0.6347 $\\pm$ 0.0239 & Boundary recoverable from consequence channels \\
`signature_core' (no Wspd/Pab_mean/Patv) & 302.10 $\\pm$ 9.16 & 0.3671 $\\pm$ 0.0372 / 0.4342 $\\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds collapsed \\
`signature_full_shuffled' & 241.50 $\\pm$ 10.25 & 4.0e-6 $\\pm$ 2.1e-6 / $-$1.3e-5 $\\pm$ 5.3e-5 & Negative control: chance level under permuted labels \\
Unconstrained MoE & --- & 0.014 / --- & No declared-boundary supervision \\
\bottomrule
\end{tabularx}
\end{table}
```

The route then passes targeted falsification checks, with an important qualification. Zeroing the boundary anchors increases RMSE by 2.679 and reduces NMI/ARI by 0.702/0.859, whereas zeroing the wake score has a near-null effect. The result identifies the declared boundary anchors, rather than the wake auxiliary channel, as the load-bearing information source. Within WTB, alignment remains detectable on withheld turbines (NMI 0.834) and a future holdout (NMI 0.835). The signature-gate probe in Table~\\ref{tab:signature-gate} further shows that the boundary is recoverable even when the defining wind-speed and pitch-angle channels are withheld from the gate. On ENGIE La Haute Borne, retraining from scratch reaches NMI 0.941 and ARI 0.971 with directly observed pitch; this is anchor-observable re-trainability, not evidence for anchor-free discovery or cross-farm transfer. Kelmarsh and Penmanshiel remain deployment-gate failures because pitch observability and boundary-cell support are insufficient.

The third question is whether the route remains useful when the confirming label stream degrades. Under a six-step delay, the threshold rule recalls 0.196 of early pitch-window cells, whereas the saved gate recalls 0.960 and recovers about 566 cells per seed. At 50% label availability, rule recall is 0.508 and gate recall remains 0.960. The clean-anchor logistic classifier reaches 1.000 recall and 0.879 precision, above the gate precision of 0.759. These values should not be read as input-noise robustness for the gate: the gate values are the saved clean-route audit, whereas the degraded labels are applied to the comparator stream. The supported claim is therefore issue-time route provenance under degraded confirmation, not superior standalone detection.

This audit asks about a degraded confirmation stream, not clean-anchor classifier ranking. A modular low-RMSE forecaster plus live-anchor classifier and physical-bin reserve rule is a valid alternative when only a state flag is needed. Its missing piece is trainable route responsibility attached to each forecast, same-run route-conditioned residual/reserve slicing, and a single deployment object whose version, calibration, and monitoring state can be audited together. A direct Graph WaveNet+classifier-bin reserve control improves over Graph WaveNet/global (86.54M versus 88.80M) but trails physical-bin and boundary-gate references (84.31M and 84.58M; Supplementary Table A10c), so it is a tested modular control rather than a replacement for in-model responsibility. The route-evolution audit adds the dynamic check: gate matching to the new regime peaks at the transition step (0.815) and drops under three- and six-step lead shifts (0.361 and 0.405; Supplementary Table A10b). The anchor-only router has lower overall RMSE (233.46) and slightly higher NMI/ARI (0.8895/0.9219), but worse pitch-control RMSE (317.81 versus 286.95) and far larger 0.5-std boundary-anchor-noise degradation (105.56 versus 5.78).

We report the operating trade-off explicitly. A model receives citable degraded-label gain only after its route passes the physical-routing audit; otherwise the accountability gain is set to zero, even for an accurate or routed-capacity model. Under this rule iTransformer is the zero-RMSE-price anchor without an audited operating-state route, Unconstrained MoE fails the route audit (NMI 0.014), and the fully archived boundary-forced checkpoint is the complete operational-audit run that carries a larger historical RMSE cost for an audited issue-time route and +0.764 six-step-delay recall gain. The train-only class-weight rerun shows that the same routed operating layer can be kept within a 5.59-RMSE gap, while the legacy checkpoint remains the run with complete gate, prediction, and reserve artifacts. The logistic control is reported separately because it is a detector on live anchors, not a forecaster with routed attribution.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{1.05}
\caption{Label-degradation audit for early MPPT-to-pitch pitch-window detection.}
\label{tab:early-warning}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} >{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.13\linewidth} >{\centering\arraybackslash}p{0.13\linewidth} >{\centering\arraybackslash}X}
\toprule
Scenario & Setting & Gate & Rule & Gain \\
\midrule
Delay & 1 step & 0.960 & 0.655 & +0.305 \\
Delay & 3 steps & 0.960 & 0.381 & +0.579 \\
Delay & 6 steps & 0.960 & 0.196 & +0.764 \\
Availability & 75\% labels & 0.960 & 0.744 & +0.216 \\
Availability & 50\% labels & 0.960 & 0.508 & +0.452 \\
Availability & 25\% labels & 0.960 & 0.242 & +0.718 \\
Noise & Wspd 0.5, Pab 1.0 & 0.960 & 0.808 & +0.152 \\
Noise & Wspd 1.0, Pab 2.0 & 0.960 & 0.652 & +0.308 \\
\bottomrule
\end{tabularx}
\end{table}
```

The training-level anchor-stress guard keeps the leakage boundary visible. In the clean train-only rerun, removing \texttt{Patv} or \texttt{Pab\_mean} leaves mean NMI at 0.881 and 0.878, while lagging \texttt{Patv} and lagging pitch/wind give 0.763 and 0.684. These older ablations are reported with the same strict-cache protocol but under a different auxiliary-weight configuration from the signature-gate probe in Table~\\ref{tab:signature-gate}; the two probe families should not be numerically merged. The consistent finding is that the route is not a leakage artifact, but it remains a declared-anchor mechanism rather than anchor-free discovery.

![The WTB operating plane shows the main mechanism: after correction, the dominant routed responsibility changes around the rated-wind and pitch-control boundary instead of forming an arbitrary expert partition. The confusion matrices summarize the same recovery numerically.](artifacts/final_evidence_package/export/figures/figure4_routing_evidence.pdf){ width=97% }

## Boundary-Risk Vignette: Does the Gate Change Reserve Tradeoffs?

The reserve audit is a consequence check for the recovered route, not a dispatch optimizer. A validation-calibrated reserve screener is frozen and applied to later MPPT-to-pitch boundary cells, comparing global, physical-bin, and gate-bin quantile rules for Graph WaveNet and the boundary router.

At a shortage-to-reserve cost ratio of 10, gate-conditioned binning carries 3.6% more reserve than the same-router global rule, while shortage energy decreases by 14.5% and violation rate decreases by 1.38 percentage points. Seed-paired intervals support this same-router boundary comparison. The physical-bin reference remains competitive, and the full-sample cross-backbone uncertainty interval crosses zero. The result therefore supports a conditional transition-window diagnostic, not reserve-policy superiority.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.08}
\caption{Boundary-window reserve diagnostic and validation-frozen quantile baselines at cost ratio 10. Same-model gate-bin differences have seed-paired support; physical-bin and full-sample comparisons bound the claim.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.11\linewidth} >{\centering\arraybackslash}p{0.12\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Policy & Cost & Viol. & Reserve & Shortage & Reading \\
\midrule
Boundary/physical-bin & 83.78M & 0.0880 & 53.26M & 3.05M & Best same-router physical-bin reference \\
GWN/physical-bin & 84.31M & 0.0931 & 50.35M & 3.40M & Low-RMSE backbone reference \\
Boundary/gate-bin & 84.58M & 0.0900 & 52.67M & 3.19M & Gate diagnostic; same-model better than global \\
Boundary/global & 88.13M & 0.1038 & 50.82M & 3.73M & Same-model global rule \\
GWN/global & 88.80M & 0.1022 & 50.32M & 3.85M & Global low-RMSE reference \\
\bottomrule
\end{tabularx}
\end{table}
```

The useful reserve window is moderate rather than universal: ratios 5--10 favor gate-bin screening, ratio 50 favors the same-model global rule, and Graph WaveNet/physical-bin remains close at 84.31M. The boundary-slice proxy falls from 88.13M to 84.58M, which Supplementary Table A12 translates into about 540 avoided MWh-equivalent shortage cells and a 355k illustrative reserve-cost-scale marker at 100 EUR/MWh. The engineering value is an auditable triage signal for balancing/reserve review near the control boundary, not market revenue or system-wide dispatch value.


# Discussion

## Accuracy, accountability and deployment gates

The accuracy cost is not a secondary detail. iTransformer, Graph WaveNet and lag-feature baselines remain better whole-sample forecasters on WTB, and the routed model should therefore be paired with an established low-RMSE forecaster when aggregate prediction is the primary objective. Its narrower use is an accountable operating-state assignment for a boundary-specific decision. Time-forward testing further shows that stable routing semantics do not guarantee stable reserve value under distribution shift.

The external evidence is deliberately two-sided. La Haute Borne passes the anchor-observable replication check (NMI 0.941, ARI 0.971, with replay support in Supplementary Tables A8--A9). Kelmarsh and Penmanshiel do not authorise gate-bin reserve use because pitch observability and boundary coverage fail. Before a new farm uses the route, it must verify pitch or proxy observability, boundary-cell support, compatible geometry, local threshold estimation and a held-out routing pass. These gates are part of the method specification because SCADA-based condition monitoring is only as portable as the measured operating channels [@tautzweinert2017scada].

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption{External-site deployment gates identified by Kelmarsh/Penmanshiel testing.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\linewidth} >{\raggedright\arraybackslash}p{0.38\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Gate & Observed evidence & Required decision before reserve use \\
\midrule
Held-out routing criterion & Default WTB boundary gives mean external NMI 0.4877 and ARI 0.5112, below the 0.50 NMI criterion & Re-establish routing agreement locally \\
Local boundary recalibration & Average test NMI changes from 0.1324 to 0.1491 after validation-only recalibration & Treat threshold transfer as insufficient \\
Pitch/proxy observability & One transfer direction has no effective pitch-feature coverage or boundary cells & Require pitch channels or a validated proxy \\
Calibration-window adaptation & Small-window adaptation remains below the held-out balanced-accuracy threshold & Use calibration only after a held-out pass \\
Geometry and regime support & Farm scale, sensor fields, power curves, and regime shares differ across sites & Run a local evidence protocol before gate-bin reserve allocation \\
\bottomrule
\end{tabularx}
\end{table}
```

# Limitations

The WTB correction uses threshold pseudo-labels from wind speed and mean pitch angle, and those same channels appear in the gate anchor. The signature-gate probe shows that the boundary remains recoverable when these channels are withheld, because the control transition leaves a detectable signature in consequence channels such as active power, reactive power, blade-pitch dispersion and wake state. Nevertheless, the method still constrains a router to a declared operating boundary rather than discovering an anchor-free physical state, and the signature-gate evidence is currently limited to WTB. This is consistent with the observability requirement in physics-guided learning: a constraint cannot be interpreted independently of the measured variables that define it [@karniadakis2021piml; @zehtabiyan2023physicsguided]. The active-power anchor is also a timing constraint: inputs may contain $\texttt{Patv}_{t-H+1:t}$ and issue-time $\texttt{Patv}_{t}$, while targets begin at $\texttt{Patv}_{t+1:t+P}$.

The expert-regime language is tied to the implemented logit convention: anchored logits are interpretable under the declared mapping, whereas unassigned experts and wake auxiliary logits should not be overread as universal turbine states. The comparison is bounded to the implemented WTB baselines and validation-frozen empirical-quantile reserve checks. Trained quantile forecasters, scenario reserve, optimal power flow, unit commitment, market clearing and security-constrained reserve remain outside scope. This boundary keeps the reserve analysis aligned with the decision-oriented role of probabilistic forecasting without claiming a complete dispatch model [@bremnes2004quantile; @zhou2013probabilisticmarkets].

The strongest claims are five-seed WTB routing recovery, mechanism intervention, within-WTB spatial/temporal stress, La Haute Borne anchor-observable replication, and same-router boundary reserve diagnostics. Gate-alignment deltas versus the full MoE and cross-backbone reserve comparisons remain bounded diagnostics; automatic cross-farm reserve use is outside authorized claims unless observability and held-out routing gates pass.

# Conclusion

This study evaluated SCADA-anchored routing as an auditable operating-state layer for wind-turbine reserve screening near the MPPT-to-pitch boundary. The provenance-corrected rerun retained route alignment at NMI 0.721 and ARI 0.740 with RMSE 229.93, while a signature-gate probe showed that the boundary remains identifiable (NMI 0.561) when the label-defining wind-speed and pitch-angle channels are withheld from the gate, and that this signature collapses to chance when the labels are permuted. The separately archived full-audit checkpoint supplied stronger alignment and the saved reserve artifacts. The route recalled 0.960 of early pitch-window cells under a six-step delay, but a simple issue-time classifier remained a stronger clean-anchor detector. Same-router gate-bin screening reduced boundary-window shortage exposure at a moderate cost ratio, whereas physical-bin, full-sample and external-site checks limited the scope of that result. The contribution is therefore a traceable route-to-reserve diagnostic whose use depends on observable boundary channels and a held-out local deployment pass.

# AI Use Statement

The authors used OpenAI ChatGPT/Codex only for language editing, consistency checks, and submission-material drafting; all data, analyses, references, conclusions, and final text were reviewed and controlled by the authors.

# Code and data availability

The raw KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel SCADA datasets are public; raw third-party data are not redistributed. Code, configurations, releasable derived tables, figure data, and checkpoints will be made available with the article. The reproduction package covers WTB routing, reserve audit, anchor-stress cache/train/guard, early-warning label degradation, classifier control, class-weight provenance/sensitivity, external diagnostics, and evidence-freeze protocols. Results are statistically reproducible across declared seeds rather than bitwise deterministic across all GPU/CUDA environments. The analysis involves no human subjects.


# References {.unnumbered}

::: {#refs}
:::

\clearpage
