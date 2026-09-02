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
Table A1 is designed to separate shared representation capacity from expert allocation, following the standard mixture-of-experts comparison logic [@jacobs1991adaptive; @shazeer2017outrageously].

\caption*{\textbf{Table A1.} In-family model comparison used for mechanism validation. Encoder capacity is held approximately fixed so that routing terms, rather than parameter count alone, explain the mechanism contrast.}
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


## Information boundary and channel roles {.unnumbered}

Table A2 makes the leakage and shared-anchor boundary explicit. The routing labels
and some gate anchors deliberately share wind-speed and pitch information; the
reported NMI/ARI therefore audits compliance with a declared SCADA boundary, not
anchor-free discovery.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A2.} Information boundary and channel-role audit.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Quantity & Label construction & Model input / gate anchor & Supervised target & Timing boundary \\
\midrule
\texttt{Wspd} & WTB regime label & history and issue-time anchor & no & $\leq t$ only \\
\texttt{Pab\_mean} & WTB regime label & history and issue-time anchor & no & $\leq t$ only \\
$\texttt{Patv}_{t-H+1:t}$ & no & historical input / issue-time status & no & $\leq t$ only \\
$\texttt{Patv}_{t+1:t+P}$ & no & no & yes & future target only \\
Wake score & auxiliary wake flag & graph-derived anchor & no & computed from issue-time graph \\
Declared regime label & alignment/forcing supervision & no test-time input & no & train/validation supervision only \\
Confirmed threshold stream & degraded-rule comparator & not a model input & no & delayed/missing/noisy in audit \\
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
\caption*{\textbf{Table A3.} Shared architecture, graph, and training constants used in the reported experiments. Shared constants are listed before dataset-specific values so that controlled factors can be distinguished from observability-specific design choices.}
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
\caption*{\textbf{Table A4.} Dataset-specific regime thresholds used to construct routing anchors. The values are operational definitions fixed or estimated before test evaluation; they are not universal turbine constants.}
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
The loss-weight table follows the physics-informed learning principle that a scientific constraint must be named and scaled explicitly [@karniadakis2021piml; @karpatne2017tgds].

\caption*{\textbf{Table A5.} Active routing-loss weights in the reported corrected models. The table records which regulariser is active in each observability setting.}
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

Table A6 separates the train-only RMSE guardrail from paired seed-level tests on the archived full-audit checkpoint. The iTransformer row is the displayed five-seed train-only guardrail gap; the Graph WaveNet and boundary-window rows are legacy full-audit paired/FDR audit rows and should not be read as the current RMSE guardrail.

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
Train-only RMSE guardrail vs iTransformer & 5.589 & -- & -- & Displayed guardrail gap for the provenance-corrected rerun; legacy full-audit checkpoint is separate \\
Legacy full-audit RMSE price vs Graph WaveNet & 9.029 & -- & <0.001 & Applies to the archived full-audit checkpoint, not the train-only RMSE guardrail \\
Legacy boundary-band RMSE price & 17.758 & -- & 0.001 & Boundary-window price for the archived full-audit checkpoint \\
Gate NMI vs full physics-aligned MoE & 0.040 & [0.008, 0.071] & 0.066 & Positive but not FDR-significant; cite as bounded mechanism contrast \\
Gate ARI vs full physics-aligned MoE & 0.035 & [-0.000, 0.078] & 0.126 & Positive but not FDR-significant; avoid superiority wording \\
Boundary quantile cost vs GWN physical bin & -0.263M & [-10.704M, 9.782M] & -- & CI crosses zero; reserve cost should remain a diagnostic claim \\
Boundary quantile violation vs GWN physical bin & 0.003 & [-0.011, 0.020] & -- & CI crosses zero; no universal reserve-policy optimality claim \\
\bottomrule
\end{tabularx}
\end{table}
```

## Class-weight sensitivity audit {.unnumbered}

Table A6b makes the class-weight provenance boundary explicit. The legacy strict-cache row is the originally frozen boundary-router checkpoint used for the headline audit; the train-only rerun recomputes alignment and pitch-forcing class weights from the training split only while preserving the same strict-mask evaluation protocol. The train-only rerun lowers NMI/ARI but remains above the routing-claim threshold.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A6b.} Class-weight sensitivity audit. Boundary-router rerun after recomputing alignment and pitch-forcing loss weights from the training split only.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Condition & Overall RMSE & Switch RMSE & Pitch RMSE & NMI & ARI \\
\midrule
Legacy strict-cache weights & 236.13 & 239.86 & 286.95 & 0.8716 & 0.9166 \\
Train-only weight rerun & 229.93 & 231.65 & 289.63 & 0.7208 & 0.7398 \\
Delta & -6.20 & -8.21 & 2.68 & -0.1508 & -0.1768 \\
\bottomrule
\end{tabular}%
}
\end{table}
```

## Outcome-channel sanity audit {.unnumbered}

Table A7 adds a bounded check for the shared-anchor concern. It does not use pitch-threshold labels to score the contrast. Validation data define a wind-speed-bin power curve, and the test comparison is restricted to 9.5--11.5 m s$^{-1}$ boundary anchors with fine wind-bin adjustment. This table is arranged as a sanity audit because SCADA studies must separate issue-time signals from the future outcomes they predict [@tautzweinert2017scada; @zhou2024sdwpfdata]. The result asks whether the recovered gate separates samples with different future active-power response, not whether it discovers a regime without anchors.

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

Table A8 records the go/no-go interpretation used for the external evidence. The first row is the cross-site mechanism replication: retrained on the ENGIE La Haute Borne farm, where blade pitch is directly observed in 99.2\% of cells, the routing mechanism recovers the declared boundary and clears the held-out criterion. The remaining rows map the failed or incomplete Kelmarsh/Penmanshiel signals to the deployment action that follows. The table is deliberately decision-shaped, with evidence, criterion and consequence in separate columns. It therefore supports a bounded two-sided claim: the mechanism replicates where the control boundary is observable, whereas direct gate-bin reserve use at the Kelmarsh/Penmanshiel pair remains unauthorised.

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
Cross-site mechanism replication (La Haute Borne) & Five-seed chronological routing NMI 0.941, ARI 0.971; pitch observed in 99.2\% of cells, no proxy & Held-out NMI $\geq$ 0.50 with observed pitch after parameters are frozen & Go: anchor-observable mechanism replicates on a second farm; do not claim anchor-free or automatic reserve transfer \\
Cross-site routing criterion & 80/80 runs complete; mean NMI 0.4877 below threshold 0.50; mean ARI 0.5112 & Held-out NMI $\geq$ 0.50 and balanced accuracy $\geq$ 0.50 after parameters are frozen & No-go for cross-farm router interpretation; cite as negative boundary-condition evidence \\
Local boundary recalibration & Default test NMI 0.1324 $\rightarrow$ recalibrated 0.1491 (delta +0.0167) & Rated wind, pitch threshold, boundary band, and gate-map selected on calibration only & Local threshold transfer is insufficient; re-estimate before use \\
Small-window adaptation & 40/40 routing runs adapted; chronological balanced accuracy 0.4787 below 0.50 & Small calibration windows must still pass the frozen held-out routing criterion & Calibration alone does not authorize external reserve use \\
Sensor and boundary support & Penmanshiel-to-Kelmarsh leave-one pitch-feature coverage 0.0000 and effective boundary cells 0 & Pre-declared calibration window with enough boundary cells, active power, availability mask, and pitch/proxy overlap & No physical-router interpretation without observability \\
External reserve-use decision & Upstream observability and held-out routing gates fail before external reserve allocation & Evaluate reserve only after observability and held-out routing gates pass & Withhold gate-bin reserve use outside WTB; report a deployment protocol only \\
\bottomrule
\end{tabularx}
\end{table}
```

## La Haute Borne anchor-observability replay audit {.unnumbered}

Table A9 audits the load-bearing channels behind the La Haute Borne cross-site mechanism replication. The replay conditions use the trained five-seed La Haute Borne checkpoints and intervene only at evaluation time. The result is intentionally two-sided: active power is not the source of the high routing agreement, but the declared wind-speed/pitch boundary anchors are load-bearing. This supports citing La Haute Borne as anchor-observable cross-site mechanism replication and blocks any anchor-free discovery or automatic cross-site reserve-use wording.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9.} La Haute Borne anchor-observability replay audit.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.31\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Replay condition & NMI & $\Delta$NMI & Interpretation \\
\midrule
Actual replay & 0.941 & 0.000 & reference five-seed route \\
Zero pitch anchor & 0.696 & 0.245 & partial alignment remains \\
Zero wind-speed anchor & 0.752 & 0.189 & partial alignment remains \\
Zero active-power anchor & 0.953 & -0.013 & active power is not load-bearing \\
Zero wind+pitch anchors & 0.001 & 0.940 & boundary alignment collapses \\
Randomize anchor physics & 0.028 & 0.913 & physical anchor mapping collapses \\
Wind-speed only & 0.752 & 0.189 & single-anchor partial control \\
Pitch only & 0.670 & 0.271 & single-anchor partial control \\
\bottomrule
\end{tabularx}
\end{table}
```

## Signature-gate identifiability probe {.unnumbered}

Table A9b reports the signature-gate probe that tests whether the MPPT-to-pitch boundary is recoverable when the label-defining channels are withheld from the model. The variants re-train five seeds from a frozen strict cache: `signature_full` removes \texttt{Wspd} and \texttt{Pab\_mean} from both encoder features and the gate anchor while retaining \texttt{Patv}; `signature_core` additionally removes \texttt{Patv}; the shuffled variants apply the same channel masks but permute valid regime labels so the input-label relationship is destroyed. Raw physics arrays are kept intact for evaluation only. The probe shows that the boundary signature survives channel withholding (mean NMI 0.561) and collapses to chance under label permutation (mean NMI 4e-6), ruling out accidental correlation between input statistics and the threshold rule. Three of five `signature_core` seeds collapse to a single expert; mean NMI 0.367 for that variant is therefore reported with median and IQR as an upper envelope rather than a stable operating point.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9b.} Signature-gate identifiability probe with permuted-label negative controls. Mean$\\pm$sd over five seeds.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.27\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.16\columnwidth} >{\centering\arraybackslash}p{0.16\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Probe & RMSE & NMI & ARI & Reading \\
\midrule
`signature_full' & 241.84 $\\pm$ 7.19 & 0.5613 $\\pm$ 0.0199 & 0.6347 $\\pm$ 0.0239 & Boundary recoverable from consequence channels \\
`signature_core' & 302.10 $\\pm$ 9.16 & 0.3671 $\\pm$ 0.0372 (median 0.3535) & 0.4342 $\\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds expert-collapsed \\
`signature_full_shuffled' & 241.50 $\\pm$ 10.25 & 4.0e-6 $\\pm$ 2.1e-6 & $-$1.3e-5 $\\pm$ 5.3e-5 & Chance level under permuted labels \\
`signature_core_shuffled' & --- & --- & --- & Negative control for the non-power signature \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Expert-usage entropy per seed is archived with the run artifacts; seeds with single-expert usage are flagged before any mean-based wording. The `signature_core_shuffled' row is reported in the reproduction package upon completion of its five-seed queue.
\end{table}
```

## Early-warning detection consequence {.unnumbered}

Table A10 reports the detector control for the label-degradation audit. The simple classifier is a validation-fit multinomial logistic regression on the same issue-time anchors. It matches or exceeds the gate on clean-anchor standalone detection, so the manuscript claims auditable in-model route attribution rather than classifier superiority. Gate values in degraded-label rows are the saved clean-route audit; the degraded stream is applied to the rule and classifier controls. Recovered cells are turbine-time cells per seed inside the six-step MPPT-to-pitch window, not MWh, currency or dispatch-cost estimates.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10.} Early-warning detector control under degraded threshold labels.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrrrr}
\toprule
Condition & Gate R & Gate P & Classifier R & Classifier P & Rule R & Rule P & Recovered cells \\
\midrule
Clean live anchors & 0.960 & 0.759 & 1.000 & 0.879 & 1.000 & 0.879 & -- \\
Delay, 6 steps & 0.960 & 0.759 & 1.000 & 0.879 & 0.196 & 0.342 & 565.6 $\pm$ 20.6 \\
50\% label availability & 0.960 & 0.759 & 1.000 & 0.879 & 0.508 & 0.877 & 334.6 $\pm$ 28.1 \\
Sensor noise, strongest & 0.960 & 0.759 & 0.885 & 0.758 & 0.652 & 0.804 & 227.8 $\pm$ 20.9 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize R/P denote recall and precision on early pitch-window cells. The simple classifier is a validation-fit logistic model on the same issue-time anchors; it is a detector control, not a routed forecaster. In sensor-noise rows, gate values are the saved clean-route audit; classifier/rule values are recomputed from noisy anchors.
\end{table}
```

## Gate route-evolution diagnostic {.unnumbered}

Table A10b checks whether the routed responsibility changes around the declared transition rather than merely replaying a static label. Matching to the new regime peaks at the transition step and drops under lead/lag shifts, supporting a route-evolution audit while not replacing the modular classifier control.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10b.} Gate route-evolution diagnostic around MPPT-to-pitch transitions.}
\begin{tabular}{rrrr}
\toprule
Lag step & Match rate & SD & Seeds \\
\midrule
-6 & 0.405 & 0.005 & 5 \\
-3 & 0.361 & 0.010 & 5 \\
+0 & 0.815 & 0.059 & 5 \\
+3 & 0.633 & 0.002 & 5 \\
+6 & 0.610 & 0.002 & 5 \\
\bottomrule
\end{tabular}
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.0}
\caption*{\textbf{Table A10c.} Modular classifier reserve control and responsibility-chain boundary.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
\toprule
Control & Result and claim boundary \\
\midrule
GWN+classifier-bin & 86.54M improves over GWN/global (88.80M) but trails physical-bin/gate-bin (84.31M/84.58M); paired modular-vs-gate CI crosses zero, so this is a tested modular control, not an in-model route-responsibility replacement. \\
\bottomrule
\end{tabularx}
\end{table}
```

## Reserve-policy claim-boundary audit {.unnumbered}

Table A11 is the compact reviewer-facing boundary audit. The same-router boundary comparison has seed-paired uncertainty support, while physical-bin, full-sample and cross-backbone comparisons still bound the claim away from policy optimality or market-dispatch value. The row order moves from the supported local contrast to the stronger controls that limit extrapolation.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11.} Reserve-policy claim-boundary audit.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.22\columnwidth}}
\toprule
Boundary & Key evidence & Limit \\
\midrule
Same-model boundary reserve effect & $\rho=10$: $\Delta$cost -3.55M [CI -4.65M,-2.45M]; $\Delta$viol. -0.0138 [CI -0.0203,-0.0072]; shortage -0.54M [CI -0.78M,-0.30M] & Same-model diagnostic; not cross-model optimal \\
Physical-bin quantile comparator & Boundary phys. 83.78M/0.0880; GWN phys. 84.31M/0.0931; gate 84.58M/0.0900 & Physical bins remain competitive \\
Cost-ratio applicability & Active at $\rho=5$--10; narrows at 20; $\rho=50$ favors global (+5.93M, +0.0035) & Moderate-cost window only \\
Full-sample system value & GWN/global 464.07M/0.0901; gate-bin 481.36M/0.1214 & No system-wide dispatch claim \\
Cross-backbone/full-sample uncertainty & $\Delta$cost +17.28M; 95\% CI [-52.09M,+87.95M]; p=0.752 & Not system-wide or cross-backbone \\
Operational scope & Validation-frozen shortfall quantiles; no OPF, unit commitment, market clearing, or prices & Screening audit only \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Same-model intervals are $n=5$ seed-paired bootstrap mean CIs for gate-bin minus same-router global at $\rho=10$.
\end{table}
```

## Engineering-unit reserve-value translation {.unnumbered}

Table A12 translates the reserve audit into MWh-equivalent forecast-cell accounting and an illustrative 100 EUR/MWh reserve-cost-scale marker. Its role is unit interpretation, not market valuation. Full decision links require probabilistic forecasts and system-level constraints beyond this screening protocol [@bremnes2004quantile; @zhou2013probabilisticmarkets].

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A12.} Engineering-unit reserve-value translation at $\rho=10$.}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.16\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth}}
\toprule
Comparison & $\Delta$ reserve & Avoided shortage & $\Delta$ cost & Cost-scale@100 \\
\midrule
Boundary gate-bin vs same-router global & +1846.9 & +539.8 & -3551.4 & -355k \\
Boundary gate-bin vs GWN physical-bin & +2319.2 & +205.6 & +262.9 & +26k \\
Boundary gate-bin vs GWN global full sample & +3148.2 & -1413.5 & +17283.2 & +1728k \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Values are MWh-equivalent forecast-cell accounting with $\Delta t=1/6$ h. Cost-scale@100 is an illustrative reserve-cost scale marker at 100 EUR/MWh, not market revenue, settlement value, OPF, or unit-commitment output. Use same-router/global as the bounded boundary-window diagnostic; physical-bin and full-sample rows block reserve superiority.
\end{table}
```


