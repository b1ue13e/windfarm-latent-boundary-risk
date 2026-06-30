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
numbersections: false
date: ""
header-includes:
  - \usepackage{tabularx}
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{graphicx}
---

# Appendix A. Training and implementation details {.unnumbered}

## Training loop summary {.unnumbered}

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

## Model-family and supplementary evidence index {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A1.} In-family model comparison used for mechanism validation.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Model & Routing & Extra terms & Params & Role \\
\midrule
Dense (matched) & Single dense head & None & WTB 110,012 / ERA5 103,272 & Shared-mapping reference \\
Unconstrained MoE & Node-level soft gate & Prediction loss only & WTB 110,012 / ERA5 103,843 & Routed-capacity control \\
Corrected routing comparator & Node-level soft gate & WTB boundary-forced: $L_{bal}+L_{align}+L_{force}$; ERA5: full corrected stack & WTB 110,012 / ERA5 103,843 & Accountability comparator \\
\bottomrule
\end{tabular}%
}
\end{table}
```

## Auxiliary losses {.unnumbered}

Let $\mathcal{B}$ denote the routed samples after masks, with $B=|\mathcal{B}|$. The soft importance and normalized share of expert $e$ are $I_e = \frac{1}{B}\sum_{n=1}^{B} g_n^{(e)}$ and $P_e = I_e / \sum_{r} I_r$. The top-$K$ load is $f_e = \frac{1}{B}\sum_{n=1}^{B}\mathbf{1}[e \in \mathrm{TopK}(\mathbf{g}_n)]$, giving
$$\mathcal{L}_{\mathrm{bal}} = E\sum_{e=1}^{E} f_e P_e - 1.$$
For WTB wake supervision,
$$\mathcal{L}_{\mathrm{aux}} = \frac{1}{|\Omega_{\mathrm{wake}}|}\sum_{(i,t)\in\Omega_{\mathrm{wake}}}\mathrm{BCE}(z^{(\mathrm{wake})}_{i,t}, W_{i,t}),$$
where $\Omega_{\mathrm{wake}}$ contains only MPPT and pitch-control samples with defined wake flags. The graph-smoothness penalty is
$$\mathcal{L}_{\mathrm{smooth}} = \frac{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)\lVert\mathbf{g}_{i,t}-\mathbf{g}_{j,t}\rVert_2^2}{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)+\epsilon}.$$

## Graph construction details {.unnumbered}

For WTB, the downstream unit vector is $\mathbf{u}_{i,t}=[\sin(\theta_{i,t}+\pi), \cos(\theta_{i,t}+\pi)]^{\top}$. With $\Delta\mathbf{p}_{ij}=\mathbf{p}_j-\mathbf{p}_i$, the streamwise and cross-stream distances are $d^{\parallel}_{ij,t}=\Delta\mathbf{p}_{ij}^{\top}\mathbf{u}_{i,t}$ and $d^{\perp}_{ij,t}=|\Delta p^x_{ij}u^y_{i,t}-\Delta p^y_{ij}u^x_{i,t}|$. A candidate edge activates when
$$\mathbb{I}^{\mathrm{cone}}_{ij,t}=\mathbf{1}\!\left[d^{\parallel}_{ij,t}>0\;\land\;\arctan\!\left(\frac{d^{\perp}_{ij,t}}{\max(d^{\parallel}_{ij,t},10^{-6})}\right)\le\phi\right].$$
The wake weight is $\tilde{\mathcal{A}}_t(i,j)=\exp(-d^{\parallel}_{ij,t}/\alpha)\exp(-|d^{\perp}_{ij,t}|/\beta)\mathbb{I}^{\mathrm{cone}}_{ij,t}$. If wind direction is missing, fall back to $\mathcal{A}^{\mathrm{static}}(i,j)=\exp(-\lVert\Delta\mathbf{p}_{ij}\rVert_2/d_{\max})$. Only the strongest $M$ inbound weights are retained. The wake score and flag are $s^{\mathrm{wake}}_{i,t}=\sum_{j}\mathcal{A}_t(i,j)$ and
$$W_{i,t}=\begin{cases}1,&s^{\mathrm{wake}}_{i,t}\ge q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\0,&s^{\mathrm{wake}}_{i,t}<q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\\varnothing,&\text{otherwise.}\end{cases}$$

For ERA5, the retained symmetric graph uses a Gaussian kernel on great-circle distances:
$$\mathcal{A}(i,j)=\exp\!\left(-\frac{d_{ij}^2}{2\sigma^2}\right)\mathbf{1}[j\in\mathcal{N}_{k_{\mathrm{nn}}}(i)\;\text{or}\;i\in\mathcal{N}_{k_{\mathrm{nn}}}(j)],$$
where $\sigma$ is the median retained neighbor distance on the training graph.

## Shared constants {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A3.} Shared architecture, graph, and training constants used in the reported experiments.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.30\columnwidth} >{\raggedright\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}X}
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

## Dataset-specific thresholds and routing weights {.unnumbered}

```{=latex}
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A4.} Dataset-specific regime thresholds used to construct routing anchors.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\columnwidth} >{\raggedright\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
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
\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A5.} Active routing-loss weights in the reported corrected models.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}X}
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

## Statistical claim boundaries {.unnumbered}

Table A6 records the reviewer-facing statistical boundary used for wording. The RMSE price versus Graph WaveNet is FDR-significant, gate-alignment deltas versus the full physics-aligned MoE are positive but not FDR-significant, and boundary-window quantile reserve comparisons have bootstrap intervals crossing zero. These tests are why the main text uses price, diagnostic, and bounded-claim language rather than forecast- or reserve-superiority wording.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A6.} Statistical claim boundaries used for reviewer-facing wording.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.11\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Claim & Estimate & 95\% CI & $p_{\mathrm{BH}}$ & Wording consequence \\
\midrule
Accuracy price vs Graph WaveNet & 9.029 & -- & <0.001 & Boundary router is significantly worse on headline RMSE \\
Boundary-band accuracy price & 17.758 & -- & 0.001 & The price also appears in the boundary window \\
Gate NMI vs full physics-aligned MoE & 0.040 & [0.008, 0.071] & 0.066 & Positive but not FDR-significant; cite as bounded mechanism contrast \\
Gate ARI vs full physics-aligned MoE & 0.035 & [-0.000, 0.078] & 0.126 & Positive but not FDR-significant; avoid superiority wording \\
Boundary quantile cost vs GWN physical bin & -0.263M & [-10.704M, 9.782M] & -- & CI crosses zero; reserve cost should remain a diagnostic claim \\
Boundary quantile violation vs GWN physical bin & 0.003 & [-0.011, 0.020] & -- & CI crosses zero; no universal reserve-policy optimality claim \\
\bottomrule
\end{tabularx}
\end{table}
```

## Outcome-channel sanity audit {.unnumbered}

Table A7 adds a bounded check for the shared-anchor concern. It does not use pitch-threshold labels to score the contrast: validation data define a wind-speed-bin power curve, and the test-set comparison is restricted to 9.5--11.5 m s$^{-1}$ boundary anchors with fine wind-bin adjustment. The result asks whether the recovered gate separates samples with different future active-power response, not whether it discovers a regime without anchors.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A7.} Outcome-channel sanity audit for the shared-anchor concern.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Check & Five-seed summary & Interpretation \\
\midrule
Boundary cells per seed & 3276 MPPT / 10465 pitch & 9.5--11.5 m s$^{-1}$ test anchors \\
Future mean power & 100.0 $\pm$ 17.5 kW & Pitch-gate minus MPPT-gate after wind-bin adjustment \\
Power-curve residual & 100.0 $\pm$ 17.5 kW & Validation wind-bin power curve only; no pitch label used \\
Future power ramp & 81.8 $\pm$ 24.7 kW & Mean late-horizon minus early-horizon power \\
Anchor-time Patv & -44.1 $\pm$ 32.5 kW & Current active power is not driving the same positive contrast \\
Residual claim boundary & sanity check only & Mitigates circularity concern; does not prove anchor-free discovery \\
\bottomrule
\end{tabularx}
\end{table}
```

## External-site deployment-gate audit {.unnumbered}

Table A8 records the go/no-go interpretation used for the external evidence. The first row is the positive control: retrained on the ENGIE La Haute Borne farm, where blade pitch is directly observed in 99.2\% of cells, the routing mechanism recovers the declared boundary and clears the held-out criterion. The remaining rows map the failed or incomplete Kelmarsh/Penmanshiel signals to the deployment action that follows. The table therefore supports a bounded but two-sided claim: the mechanism transfers where the control boundary is observable, while direct gate-bin reserve use at the Kelmarsh/Penmanshiel pair remains a screening protocol rather than an authorized transfer.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A8.} External-site deployment-gate audit and wording boundary.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.20\columnwidth} >{\raggedright\arraybackslash}p{0.33\columnwidth} >{\raggedright\arraybackslash}p{0.22\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Gate & Observed external evidence & Go/no-go rule & Claim consequence \\
\midrule
Cross-site recovery (La Haute Borne) & Five-seed chronological routing NMI 0.941, ARI 0.971; pitch observed in 99.2\% of cells, no proxy & Held-out NMI $\geq$ 0.50 with observed pitch after parameters are frozen & Go: boundary recovers where pitch is observable; cite as positive cross-site control \\
Cross-site routing criterion & 80/80 runs complete; mean NMI 0.4877 below threshold 0.50; mean ARI 0.5112 & Held-out NMI $\geq$ 0.50 and balanced accuracy $\geq$ 0.50 after parameters are frozen & No-go for cross-farm router interpretation; cite as negative boundary-condition evidence \\
Local boundary recalibration & Default test NMI 0.1324 $\rightarrow$ recalibrated 0.1491 (delta +0.0167) & Rated wind, pitch threshold, boundary band, and gate-map selected on calibration only & Local threshold transfer is insufficient; re-estimate before use \\
Small-window adaptation & 40/40 routing runs adapted; chronological balanced accuracy 0.4787 below 0.50 & Small calibration windows must still pass the frozen held-out routing criterion & Calibration alone does not authorize external reserve use \\
Sensor and boundary support & Penmanshiel-to-Kelmarsh leave-one pitch-feature coverage 0.0000 and effective boundary cells 0 & Pre-declared calibration window with enough boundary cells, active power, availability mask, and pitch/proxy overlap & No physical-router interpretation without observability \\
External reserve-use decision & Upstream gates do not pass before reserve allocation is evaluated & Transition-window shortage and violation improve at acceptable reserve-energy cost & Withhold gate-bin reserve use outside WTB; report a deployment protocol only \\
\bottomrule
\end{tabularx}
\end{table}
```

## Early-warning detection consequence {.unnumbered}

Table A9 reports the cell-count version of the label-degradation audit. Counts are turbine-time cells per seed inside the six-step MPPT-to-pitch window; they are not MWh, currency, or dispatch-cost estimates. The purpose is narrower: it shows how many early pitch-window cells the gate preserves when a threshold-label rule is delayed, incomplete, or noisy.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A9.} Early-warning detection consequence under degraded threshold labels.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\columnwidth} >{\centering\arraybackslash}p{0.22\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\centering\arraybackslash}X}
\toprule
Condition & Gate detected / missed & Degraded rule detected / missed & Recovered cells \\
\midrule
Delay, 1 step & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 485.0 $\pm$ 0.0 / 255.0 $\pm$ 0.0 & 225.6 $\pm$ 20.6 \\
Delay, 3 steps & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 282.0 $\pm$ 0.0 / 458.0 $\pm$ 0.0 & 428.6 $\pm$ 20.6 \\
Delay, 6 steps & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 145.0 $\pm$ 0.0 / 595.0 $\pm$ 0.0 & 565.6 $\pm$ 20.6 \\
50\% label availability & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 376.0 $\pm$ 10.4 / 364.0 $\pm$ 10.4 & 334.6 $\pm$ 28.1 \\
25\% label availability & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 179.0 $\pm$ 7.9 / 561.0 $\pm$ 7.9 & 531.6 $\pm$ 22.9 \\
Sensor noise, strongest & 710.6 $\pm$ 20.6 / 29.4 $\pm$ 20.6 & 482.8 $\pm$ 11.0 / 257.2 $\pm$ 11.0 & 227.8 $\pm$ 20.9 \\
\bottomrule
\end{tabularx}
\end{table}
```

## Reserve-policy claim-boundary audit {.unnumbered}

Table A10 consolidates the reserve evidence used for wording. It separates the same-model boundary-window diagnostic from claims that the experiments do not support. Costs are normalized reserve-energy proxy units, not currency, market prices, or security-constrained dispatch costs.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A10.} Reserve-policy claim-boundary audit.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.22\columnwidth} >{\raggedright\arraybackslash}p{0.36\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Boundary & Evidence & Wording rule \\
\midrule
Same-model boundary reserve effect & At rho=10, gate-bin vs same-router global: Delta cost -3.55M, Delta viol. -0.0138, reserve +1.85M, shortage -0.54M. & Claim a same-predictor transition-window diagnostic; do not present this as a cross-backbone reserve win. \\
Physical-bin quantile comparator & Boundary/physical-bin 83.78M, viol. 0.0880; GWN/physical-bin 84.31M, viol. 0.0931; Boundary/gate-bin 84.58M, viol. 0.0900. & Say physical-bin baselines are competitive and sometimes lower-cost; avoid gate-bin optimality wording. \\
Cost-ratio applicability & rho=2 inactive; rho=5 to 10 lowers boundary cost and violation; rho=20 narrows; rho=50 favors global (+5.93M, viol. +0.0035). & Claim moderate-cost transition-window value only; do not assert a universal shortage-penalty policy. \\
Full-sample system value & Full sample at rho=10: GWN/global 464.07M, viol. 0.0901; Boundary/gate-bin 481.36M, viol. 0.1214. & Do not claim system-wide dispatch value or reserve superiority; keep the consequence bounded to the boundary slice. \\
Seed-level uncertainty & Full-sample paired total-cost delta +17.28M, 95\% CI [-52.09M, +87.95M], perm. p=0.752. & Use bounded diagnostic language; do not cite the reserve audit as a statistically settled improvement. \\
Operational scope & Costs are normalized reserve-energy proxy units from validation-frozen shortfall quantiles; OPF, unit commitment, delivery constraints, market clearing, and prices are excluded. & Use as a screening audit for reserve exposure, not as a market or security-constrained dispatch study. \\
\bottomrule
\end{tabularx}
\end{table}
```

## Engineering-unit reserve-value translation {.unnumbered}

Table A11 provides the engineering-unit translation of the main reserve audit. The conversion uses the WTB active-power unit (kW) and the cache time step ($\Delta t=1/6$ h), so reserve and shortage totals become rolling forecast-cell MWh-equivalent values. The EUR column is a scenario translation under an assumed reserve carrying cost of 100 EUR/MWh. It is included to make the operational scale legible, not to claim market settlement, OPF, unit commitment, or security-constrained dispatch value.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.06}
\caption*{\textbf{Table A11.} Engineering-unit reserve-value translation at $\rho=10$.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Comparison & $\Delta$ reserve MWh-eq. & Avoided shortage MWh-eq. & $\Delta$ cost MWh-eq. & $\Delta$ EUR at 100/MWh & Wording \\
\midrule
Boundary gate-bin vs same-router global & +1846.9 & +539.8 & -3551.4 & -355k & Use as bounded boundary-window value, not cross-backbone superiority. \\
Boundary gate-bin vs GWN physical-bin & +2319.2 & +205.6 & +262.9 & +26k & Shows gate-bin is close to a strong physical-bin comparator; not a lower-cost claim. \\
Boundary gate-bin vs GWN global full sample & +3148.2 & -1413.5 & +17283.2 & +1728k & Blocks system-wide dispatch or full-sample reserve-superiority wording. \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize MWh-eq. denotes forecast-cell MWh-equivalent accounting from kW active-power shortfall and $\Delta t=1/6$ h. EUR values are scenario translations under an assumed reserve carrying cost of 100 EUR/MWh; they are not market-settlement, OPF, or unit-commitment results.
\end{table}
```
```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A12.} Expanded WTB strict-cache forecasting baselines (mean $\pm$ std across seeds where repeated runs are available).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Model & Overall RMSE & Overall MAE & Switch RMSE & Switch MAE & n \\
\midrule
Graph WaveNet & 225.74 +/- 2.60 & 160.09 +/- 2.00 & 228.12 +/- 3.23 & 159.83 +/- 1.41 & 5 \\
Graph Transformer & 235.38 +/- 5.15 & 165.97 +/- 1.63 & 237.06 +/- 5.78 & 164.82 +/- 2.08 & 5 \\
GAT-GRU & 236.59 +/- 7.80 & 167.31 +/- 4.37 & 240.17 +/- 8.50 & 167.71 +/- 4.79 & 5 \\
PatchTST & 228.07 +/- 4.05 & 164.00 +/- 4.09 & 231.22 +/- 4.15 & 164.47 +/- 4.40 & 5 \\
iTransformer & 224.34 +/- 2.23 & 160.88 +/- 4.45 & 228.80 +/- 2.54 & 162.94 +/- 4.47 & 5 \\
TiDE & 227.31 +/- 3.05 & 160.43 +/- 4.55 & 231.48 +/- 2.86 & 161.62 +/- 4.58 & 5 \\
Physics-Aligned MoE & 241.42 +/- 4.28 & 169.49 +/- 2.44 & 242.60 +/- 6.07 & 167.77 +/- 4.19 & 5 \\
Boundary-forced router & 236.13 +/- 8.41 & 166.42 +/- 5.54 & 239.86 +/- 8.85 & 166.98 +/- 6.75 & 5 \\
\bottomrule
\end{tabular}%
}
\end{table}
```

