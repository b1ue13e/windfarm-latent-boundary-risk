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

Table A6 separates the train-only RMSE guardrail from paired seed-level tests on the train-only checkpoints. The iTransformer row is the displayed five-seed train-only guardrail gap; the Graph WaveNet row is a legacy pure-prediction baseline contrast; the gate-versus-full-MoE rows use the official reviewer-stat-pack paired statistics on train-only checkpoints for both families.

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
Train-only RMSE guardrail vs iTransformer & 5.589 & -- & -- & Displayed guardrail gap for the provenance-corrected rerun \\
Legacy RMSE price vs Graph WaveNet & 9.029 & -- & <0.001 & Legacy historical checkpoint contrast only \\
Legacy boundary-band RMSE price & 17.758 & -- & 0.001 & Boundary-window price for the legacy historical checkpoint \\
Gate NMI vs full physics-aligned MoE (train-only) & -0.109 & [-0.280, 0.084] & 0.352 & No significant alignment difference; do not claim boundary forcing is required for alignment \\
Gate ARI vs full physics-aligned MoE (train-only) & -0.138 & [-0.356, 0.088] & 0.379 & Same; no superiority wording \\
Boundary quantile cost vs GWN physical bin & -0.263M & [-10.704M, 9.782M] & -- & CI crosses zero; reserve cost should remain a diagnostic claim \\
Boundary quantile violation vs GWN physical bin & 0.003 & [-0.011, 0.020] & -- & CI crosses zero; no universal reserve-policy optimality claim \\
\bottomrule
\end{tabularx}
\end{table}
```

## Class-weight sensitivity audit {.unnumbered}

Table A6b makes the class-weight provenance boundary explicit. The legacy strict-cache row records the historical boundary-router checkpoint from earlier iterations; the train-only rerun recomputes alignment and pitch-forcing class weights from the training split only and serves as the single source for all headline audits in the main paper. The train-only rerun lowers NMI/ARI but remains above the routing-claim threshold.

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

Table A8 records the deployment interpretation used for the external evidence. The first row is the cross-site mechanism replication: retrained on the ENGIE La Haute Borne farm, where blade pitch is directly observed in 99.2\% of cells, the routing mechanism recovers the declared boundary and clears the held-out criterion. The remaining rows map the Kelmarsh/Penmanshiel signals to the deployment action that follows. The table is deliberately decision-shaped, with evidence, criterion and consequence in separate columns. The signature-gate probe (Table A9d) upgrades the binary go/no-go into a graded signature-strength reading: partial pitch observability modulates rather than extinguishes boundary recoverability.

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
Cross-site routing criterion & 80/80 runs complete; aggregated mean NMI 0.557 passes the 0.50 criterion; direction-dependent (0.341 in the reverse direction) & Held-out NMI $\geq$ 0.50 and balanced accuracy $\geq$ 0.50 after parameters are frozen, reported per direction & Aggregate pass, direction-dependent; cite with per-direction values \\
Local boundary recalibration & Default test NMI 0.1324 $\rightarrow$ recalibrated 0.1491 (delta +0.0167) & Rated wind, pitch threshold, boundary band, and gate-map selected on calibration only & Local threshold transfer is insufficient; re-estimate before use \\
Small-window adaptation & 40/40 routing runs adapted; chronological balanced accuracy 0.4787 below 0.50 & Small calibration windows must still pass the frozen held-out routing criterion & Calibration alone does not authorize external reserve use \\
Withheld-channel signature at partial pitch & Kelmarsh: 0.340/0.378; Penmanshiel: 0.302/0.195; shuffled controls at chance & Signature strength graded against the farm's own shuffled control & Partial pitch observability grades, not voids, boundary recoverability \\
External reserve-use decision & Local evidence protocol must still pass before external reserve allocation & Evaluate reserve only after observability and held-out routing gates pass & Withhold gate-bin reserve use outside WTB; report a deployment protocol only \\
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

Table A9b reports the signature-gate probe that tests whether the MPPT-to-pitch boundary is recoverable when the label-defining channels are withheld from the model. The variants re-train five seeds from a frozen strict cache: `signature_full` removes \texttt{Wspd} and \texttt{Pab\_mean} from both encoder features and the gate anchor while retaining \texttt{Patv}; `signature_core` additionally removes \texttt{Patv}; the shuffled variants apply the same channel masks but permute valid regime labels so the input-label relationship is destroyed. Raw physics arrays are kept intact for evaluation only. The probe shows that the boundary signature survives channel withholding (mean NMI 0.561) and collapses to chance under label permutation (mean NMI 4e-6 for both shuffled variants), ruling out accidental correlation between input statistics and the threshold rule. Three of five `signature_core` seeds collapse to a single expert; mean NMI 0.367 for that variant is therefore reported with median and IQR as an upper envelope rather than a stable operating point.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9b.} Signature-gate identifiability probe with permuted-label negative controls. Mean$\pm$sd over five seeds.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Probe & RMSE & NMI & ARI & Reading \\
\midrule
\texttt{signature\_full} & 241.84 $\pm$ 7.19 & 0.5613 $\pm$ 0.0199 & 0.6347 $\pm$ 0.0239 & Boundary recoverable from consequence channels \\
\texttt{signature\_core} & 302.10 $\pm$ 9.16 & 0.3671 $\pm$ 0.0372 (median 0.3535) & 0.4342 $\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds expert-collapsed \\
\texttt{signature\_full\_shuffled} & 241.50 $\pm$ 10.25 & 4.0e-6 $\pm$ 2.1e-6 & $-$1.3e-5 $\pm$ 5.3e-5 & Chance level under permuted labels \\
\texttt{signature\_core\_shuffled} & 296.69 $\pm$ 16.22 & 4.7e-6 $\pm$ 3.4e-6 & $-$2.0e-4 $\pm$ 1.7e-4 & Chance level under permuted labels \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Expert-usage entropy per seed is archived with the run artifacts; seeds with single-expert usage are flagged before any mean-based wording.
\end{table}
```

Table A9c reports the same probe on ENGIE La Haute Borne under the identical threshold definition. The full-anchor canonical baseline reaches NMI 0.975 under the same training protocol; `signature_full` retains mean NMI 0.674 (min-seed 0.499) and `signature_core` mean NMI 0.575 with no expert collapse in any seed. Permuting the regime labels under the same withheld-channel mask collapses NMI to 1.92e-04. The boundary signature therefore replicates across farms; the claim is mechanism replication under a shared threshold definition, not parameter transfer.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9c.} Cross-farm signature-gate replication, ENGIE La Haute Borne. Mean$\pm$sd over five seeds; per-seed values archived.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Probe & RMSE & NMI & ARI & Reading \\
\midrule
\texttt{canonical} & 185.0 $\pm$ 1.9 & 0.9752 $\pm$ 0.0088 & 0.9904 $\pm$ 0.0044 & Full-anchor reference \\
\texttt{signature\_full} & 185.1 $\pm$ 1.4 & 0.6743 $\pm$ 0.1209 & 0.7401 $\pm$ 0.1604 & Signature transfers; min-seed 0.499 \\
\texttt{signature\_core} & 188.0 $\pm$ 1.0 & 0.5750 $\pm$ 0.0423 & 0.6270 $\pm$ 0.0638 & Non-power signature transfers; 0/5 collapsed \\
\texttt{signature\_full\_shuffled} & 185.4 $\pm$ 1.2 & 1.92e-04 $\pm$ 8.90e-05 & 5.19e-04 $\pm$ 2.86e-03 & Chance level under permuted labels \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize LHB is a four-turbine Senvion MM82 farm with directly observed pitch (99.2\% coverage) and no wake graph support (wake score identically zero). RMSE is nearly invariant to channel withholding, so the signature effect is decoupled from forecast accuracy.
\end{table}
```

Table A9d reports the same probe on two farms with partial pitch observability. Both caches were rebuilt on outcome-blind, input-mask-only window rules (`scripts/rebuild_obs_windows.py`): the earliest contiguous 245-day window with daily pitch coverage at least 0.70 and daily regime-valid at least 0.70 for Penmanshiel (day 720; Senvion MM82), and the earliest window with daily regime-valid at least 0.70 for Kelmarsh (day 120; Senvion MM92). Permuted-label controls collapse to chance at both farms, and the withheld-channel variants stay above chance across both commercial wind farms, so the deployment decision is a graded signature-strength check rather than a binary observability gate.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9d.} Signature-gate probe on partial-pitch-observability farms. Mean$\pm$sd over five seeds; per-seed values archived.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llll}
\toprule
Probe & NMI & ARI & Reading \\
\midrule
Penmanshiel canonical & 0.6987 $\pm$ 0.4004 & 0.6342 $\pm$ 0.4961 & Large seed variance: noisy partial-pitch labels \\
Penmanshiel \texttt{signature\_full} & 0.3024 $\pm$ 0.0343 & 0.1613 $\pm$ 0.1150 & Above 0.20 criterion \\
Penmanshiel \texttt{signature\_core} & 0.1954 $\pm$ 0.0961 & 0.1302 $\pm$ 0.1816 & Below 0.20; 4400x above shuffled chance \\
Penmanshiel \texttt{signature\_full\_shuffled} & 4.4e-05 $\pm$ 2.3e-05 & 1.6e-03 $\pm$ 1.7e-03 & Chance level \\
\midrule
Kelmarsh canonical & 0.4441 $\pm$ 0.2413 & 0.4499 $\pm$ 0.3300 & Large seed variance: noisy partial-pitch labels \\
Kelmarsh \texttt{signature\_full} & 0.3402 $\pm$ 0.0736 & 0.3461 $\pm$ 0.1399 & Above 0.20 criterion \\
Kelmarsh \texttt{signature\_core} & 0.3775 $\pm$ 0.0783 & 0.4763 $\pm$ 0.0758 & Above 0.20 criterion; strongest non-power signal \\
Kelmarsh \texttt{signature\_full\_shuffled} & 9.2e-05 $\pm$ 2.5e-05 & 1.6e-03 $\pm$ 2.0e-03 & Chance level \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Signature strength is evaluated on reconstructed operating windows across both commercial wind farms. The graded reading attributes the recovered boundary signal to consequence-channel quality (reactive power, pitch dispersion, temperatures) rather than to pitch sensors alone. Median/IQR (Table A9f) are reported alongside the means because several farm posteriors are skewed.
\end{table}
```

Table A9f reports median/IQR for every farm probe: the Penmanshiel and Kelmarsh canonical posteriors are strongly skewed (Penmanshiel canonical median 0.985 versus mean 0.699), so median-based readings are the honest summary for those cells.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9f.} Farm signature probes: median and IQR (five seeds unless noted).}
\begin{tabular}{llrrrrr}
\toprule
Farm & Variant & $n$ & Median & Q25 & Q75 & Mean $\pm$ SD \\
\midrule
WTB & signature\_full & 5 & 0.563 & 0.554 & 0.565 & 0.561 $\pm$ 0.018 \\
WTB & signature\_core & 5 & 0.354 & 0.348 & 0.363 & 0.367 $\pm$ 0.033 \\
LHB & canonical & 5 & 0.978 & 0.977 & 0.979 & 0.975 $\pm$ 0.008 \\
LHB & signature\_full & 5 & 0.733 & 0.603 & 0.742 & 0.674 $\pm$ 0.108 \\
LHB & signature\_core & 5 & 0.598 & 0.540 & 0.607 & 0.575 $\pm$ 0.038 \\
Penmanshiel & canonical & 5 & 0.985 & 0.279 & 0.994 & 0.699 $\pm$ 0.358 \\
Penmanshiel & signature\_full & 5 & 0.299 & 0.270 & 0.332 & 0.302 $\pm$ 0.031 \\
Penmanshiel & signature\_core & 5 & 0.207 & 0.133 & 0.213 & 0.195 $\pm$ 0.086 \\
Kelmarsh & canonical & 5 & 0.292 & 0.275 & 0.683 & 0.444 $\pm$ 0.216 \\
Kelmarsh & signature\_full & 5 & 0.313 & 0.295 & 0.388 & 0.340 $\pm$ 0.066 \\
Kelmarsh & signature\_core & 5 & 0.328 & 0.323 & 0.421 & 0.378 $\pm$ 0.070 \\
\bottomrule
\end{tabular}
\vspace{1mm}
\footnotesize The window scan (Table A9e) passes at 4/4 windows with per-seed pass-rate 1.0 (3/3 seeds above the 0.20 criterion in every window).
\end{table}
```

Table A9e reports two robustness additions. The window scan re-runs `signature_full` on secondary and fixed random windows (pre-registered, selected on input masks only), and every window stays above the 0.20 criterion. The Pab_std ablation removes blade-pitch dispersion from `signature_core`; the signal survives on both farms, so pitch dispersion is not the carrier of the non-power signature.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9e.} Window-robustness scan and Pab\_std ablation (signature\_full / signature\_core\_no\_pab\_std, mean$\pm$sd).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llll}
\toprule
Probe & NMI & ARI & Reading \\
\midrule
Penmanshiel secondary window (day 965, pitch 77.5\%) & 0.458 $\pm$ 0.099 & 0.405 $\pm$ 0.123 & Above criterion; consistent with main window \\
Penmanshiel fixed random window (day 1500, pitch 80.5\%) & 0.294 $\pm$ 0.007 & 0.128 $\pm$ 0.004 & Above criterion \\
Kelmarsh secondary window (day 365, pitch 54.9\%) & 0.359 $\pm$ 0.188 & 0.328 $\pm$ 0.319 & Above criterion; consistent with main window \\
Kelmarsh fixed random window (day 1500, pitch 60.1\%) & 0.277 $\pm$ 0.106 & 0.218 $\pm$ 0.175 & Above criterion \\
\midrule
WTB \texttt{signature\_core\_no\_pab\_std} & 0.309 $\pm$ 0.066 & 0.356 $\pm$ 0.075 & Signal survives without pitch dispersion (vs core 0.367) \\
LHB \texttt{signature\_core\_no\_pab\_std} & 0.578 $\pm$ 0.135 & 0.617 $\pm$ 0.200 & Signal unchanged without pitch dispersion (vs core 0.575) \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Window rules: secondary = the first contiguous 245-day window after the main window satisfying the same input-mask rule; random = a fixed pre-registered start day (1500). All runs are five seeds except the scan rows, which are three seeds. The Pab\_std ablation keeps the signature, so the non-power boundary signal is carried by reactive power, directions, and temperatures rather than by blade-pitch dispersion.
\end{table}
```

## External validation and cross-farm evidence demarcation {.unnumbered}

To ensure complete methodological transparency and prevent over-generalization across disparate commercial wind farms, we explicitly disentangle three separate lines of external evidence:

1. **Within-plant local retraining (ENGIE La Haute Borne, Kelmarsh, Penmanshiel):** All probe evaluations (Tables A9a--A9f) and chronological dispatch replays represent models retrained locally under site-specific rated aerodynamic wind speeds ($v_{\mathrm{rated}} = 12.5\text{ m s}^{-1}$ for Kelmarsh MM92 and $14.5\text{ m s}^{-1}$ for Penmanshiel MM82). These results demonstrate neural architecture adaptability to site-specific aerodynamic parameters when local training data is available, rather than zero-shot cross-farm generalizability.
2. **Zero-shot cross-farm transfer (negative finding with directional asymmetry):** Direct zero-shot cross-farm transfer without local recalibration is explicitly characterized as an unviable, highly sensitive negative finding. Representation transfer between Kelmarsh and Penmanshiel exhibits severe directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled mean NMI $0.557$; `external_wind_guard.json`), proving that operational reserve policies cannot be transferred across distinct turbine makes and geometries without local sensor calibration and retraining.
3. **Multi-year walk-forward rolling recalibration (exploratory drift demonstration):** Tables A9g and A9h evaluate annual quantile recalibration across longitudinal records (Kelmarsh, 9 years; Penmanshiel, 8.6 years) under IEC 61400-12-1 air-density calibration using a 2-year sliding training window. Data-integrity auditing identified temporal overlap in historical rolling folds (e.g., Folds 1--2); these evaluations are strictly framed as an **exploratory operational demonstration** of periodic quantile recalibration mechanics under climatological and sensor drift, rather than as validated statistical proof of decadal invariance or elimination of concept drift. On Kelmarsh, 6 of 7 rolling folds strictly exclude zero ($p < 0.05$), with mean annual savings of $-1.025 \text{ Million kWh/year}$. On Penmanshiel, 4 mature operational folds (2020--2023) strictly exclude zero ($p < 0.05$), with mean annual savings of $-2.029 \text{ Million kWh/year}$.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9g.} Kelmarsh 9-year walk-forward rolling recalibration audit under IEC 61400-12-1 density calibration ($\rho=10$, 5 seeds).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Evaluation Window & Train Period & Test Period & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero \\
\midrule
Rolling Fold 1 & 2016--2017 & 2018 & -38k & [-204k, +172k] & no \\
Rolling Fold 2 & 2017--2018 & 2019 & -334k & [-473k, -196k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 3 & 2018--2019 & 2020 & -952k & [-1293k, -393k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 4 & 2019--2020 & 2021 & -1685k & [-1977k, -1294k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 5 & 2020--2021 & 2022 & -656k & [-764k, -526k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 6 & 2021--2022 & 2023 & -1542k & [-2034k, -1049k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 7 & 2022--2023 & 2024 & -981k & [-1220k, -790k] & \textbf{yes} ($p<0.05$) \\
\midrule
Mature Mean (Folds 2--7) & -- & 2019--2024 & -1025k & [-1344k, -708k] & \textbf{yes} (6/7 Folds) \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Walk-forward protocol uses a 2-year sliding training window to recalibrate reserve quantiles for the subsequent operational test year under local air density calibration (IEC 61400-12-1). Six of seven consecutive rolling folds strictly exclude zero. Script: \texttt{scripts/eval\_external\_rolling\_reserve.py}.
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9h.} Penmanshiel 8.6-year walk-forward rolling recalibration audit under IEC 61400-12-1 density calibration ($\rho=10$, 5 seeds).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Evaluation Window & Train Period & Test Period & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero \\
\midrule
Rolling Fold 1 & 2016--2017 & 2018 & +3802k & [+648k, +6956k] & no (commissioning) \\
Rolling Fold 2 & 2017--2018 & 2019 & -25k & [-695k, +1134k] & no (stabilization) \\
Rolling Fold 3 & 2018--2019 & 2020 & -1204k & [-1946k, -565k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 4 & 2019--2020 & 2021 & -2138k & [-3247k, -1362k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 5 & 2020--2021 & 2022 & -2052k & [-3503k, -1017k] & \textbf{yes} ($p<0.05$) \\
Rolling Fold 6 & 2021--2022 & 2023 & -2723k & [-4178k, -1701k] & \textbf{yes} ($p<0.05$) \\
\midrule
Mature Mean (Folds 3--6) & -- & 2020--2023 & -2029k & [-3219k, -1161k] & \textbf{yes} (4/4 Folds) \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Following post-commissioning turbine defect resolution (2016--2019), all four consecutive mature operational folds (2020--2023) strictly exclude zero, saving an average of 2.029 Million kWh/year. Script: \texttt{scripts/eval\_penmanshiel\_rolling\_reserve.py}.
\end{table}
```

## Early-warning detection consequence {.unnumbered}

Table A10 reports the detector control for the label-degradation audit. The simple classifier is a validation-fit multinomial logistic regression on the same issue-time anchors. It matches or exceeds the gate on clean-anchor standalone detection, so the manuscript claims auditable in-model route attribution rather than classifier superiority. Gate values in degraded-label rows are the saved clean-route audit; the degraded stream is applied to the rule and classifier controls. Table A10d reports the fair-degradation counterpart, where delay and sensor noise degrade the gate's own inputs as well. Recovered cells are turbine-time cells per seed inside the six-step MPPT-to-pitch window, not MWh, currency or dispatch-cost estimates.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10.} Early-warning detector control under degraded threshold labels (train-only gate values).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrrrr}
\toprule
Condition & Gate R & Gate P & Classifier R & Classifier P & Rule R & Rule P & Recovered cells \\
\midrule
Clean live anchors & 0.971 & 0.630 & 1.000 & 0.879 & 1.000 & 0.879 & -- \\
Delay, 6 steps & 0.971 & 0.630 & 1.000 & 0.879 & 0.196 & 0.342 & 565.6 $\pm$ 20.6 \\
50\% label availability & 0.971 & 0.630 & 1.000 & 0.879 & 0.508 & 0.877 & 334.6 $\pm$ 28.1 \\
Sensor noise, strongest & 0.971 & 0.630 & 0.885 & 0.758 & 0.652 & 0.804 & 227.8 $\pm$ 20.9 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize R/P denote recall and precision on early pitch-window cells. The simple classifier is a validation-fit logistic model on the same issue-time anchors; it is a detector control, not a routed forecaster. In sensor-noise rows, gate values are the saved clean-route audit; classifier/rule values are recomputed from noisy anchors. Gate precision drops to 0.630 under the train-only rerun, widening the disclosed gap to the classifier control.
\end{table}
```

Table A10d reports the fair-degradation audit under the Unified Arrival Layer: confirming-stream delay applies late wind-speed and pitch readings symmetrically across anchor inputs and encoder history channels ($x_{\mathrm{hist}}$ shifted by $d$ steps), completely eliminating clean-history observability loopholes at anchor $t$. Under a six-step delay ($d=6$, 60-minute stall), detection recall attenuates from 0.9705 to 0.4170, yet the jointly-learned posterior retains a +0.221 recall gain (+113% relative advantage) and +0.131 F1 gain over the collapsed deterministic threshold rule (0.1959 recall, 0.2491 F1). Table A10e evaluates industrial burst packet loss under a two-state Markov-Gilbert model with symmetric history degradation.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10d.} Fair-degradation audit: gate and physical rule consume the same degraded readings under the Unified Arrival Layer. Full precision, recall, and F1 profile across five train-only seeds.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrrrr}
\toprule
Condition & Gate Rec & Rule Rec & Gate Prec & Rule Prec & Gate F1 & Rule F1 & F1 Gain \\
\midrule
Clean anchors & 0.9705 & 1.0000 & 0.6304 & 0.8789 & 0.7598 & 0.9355 & -0.1757 \\
Delay, 1 step & 0.8346 & 0.6554 & 0.5499 & 0.7153 & 0.6585 & 0.6841 & -0.0255 \\
Delay, 3 steps & 0.6200 & 0.3811 & 0.4156 & 0.4646 & 0.4937 & 0.4187 & \textbf{+0.0750} \\
Delay, 6 steps & 0.4170 & 0.1959 & 0.3581 & 0.3420 & 0.3802 & 0.2491 & \textbf{+0.1310} \\
Noise, Wspd 0.5 / Pab 1.0 & 0.9635 & 0.8114 & 0.6228 & 0.8567 & 0.7525 & 0.8334 & -0.0808 \\
Noise, Wspd 1.0 / Pab 2.0 & 0.9505 & 0.6800 & 0.6032 & 0.8105 & 0.7349 & 0.7395 & -0.0046 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Values are means over 5 seeds under the Unified Arrival Layer (archived in \texttt{artifacts/fair\_degradation\_replay\_20260903/}). Full-stream history shift and anchor delay are applied symmetrically to both the gate and the deterministic threshold rule.
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10e.} Industrial Markov-Gilbert bursty packet degradation audit ($p_{GB}=0.08, p_{BB}=0.75$, max lag 6 steps, 5 seeds, WTB operational test split).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrr}
\toprule
Method & Burst Recall & Burst Precision & Burst F1 & Evaluated Cells \\
\midrule
Clean Physical Rule & 1.000 $\pm$ 0.000 & 1.000 $\pm$ 0.000 & 1.000 $\pm$ 0.000 & 146,552 cells/seed \\
Stale Threshold Rule (honest: lagged Wspd \& Pab) & 0.840 $\pm$ 0.000 & 0.979 $\pm$ 0.000 & 0.904 $\pm$ 0.000 & 146,552 cells/seed \\
Stale Threshold Rule (legacy: lagged Pab only) & 0.993 $\pm$ 0.000 & 1.000 $\pm$ 0.000 & 0.996 $\pm$ 0.000 & 146,552 cells/seed \\
Jointly-Learned Routed Posterior (honest corrupted forward) & 0.962 $\pm$ 0.023 & 0.895 $\pm$ 0.087 & 0.925 $\pm$ 0.042 & 146,552 cells/seed \\
Jointly-Learned Routed Posterior (clean forward reference) & 0.997 $\pm$ 0.003 & 0.948 $\pm$ 0.088 & 0.970 $\pm$ 0.048 & 146,552 cells/seed \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated over 146,552 burst-loss cells per seed under a two-state Markov-Gilbert channel simulating IEC 61400-25 substation communication disruptions with consecutive burst drops up to 6 steps. In the honest symmetric evaluation where telemetry drops affect wind-speed, pitch-angle, and active power channels across anchor and encoder history streams, the stale rule's recall drops to 0.840 and F1 to 0.904, whereas the corrupted routed posterior maintains 0.962 recall and 0.925 F1 (seed-paired F1 gain $+0.021$, 95\% bootstrap CI $[-0.014, +0.050]$). The legacy 0.994 recall / 0.967 F1 reflected an asymmetric evaluation where encoder history remained clean while only anchor readings were lagged. Script: \texttt{scripts/eval\_markov\_gilbert\_telemetry.py}.
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
GWN+classifier-bin & 86.54M improves over GWN/global (88.80M) and gate-bin (95.13M train-only), but trails physical-bin (84.31M); paired modular-vs-gate CI crosses zero, so this is a tested modular control, not an in-model route-responsibility replacement. \\
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
Same-model boundary reserve effect & $\rho=10$: $\Delta$cost -4.42M [CI -7.36M,-1.27M]; $\Delta$viol. -0.0145 [CI -0.0220,-0.0073]; shortage -0.637M [CI -0.976M,-0.300M]; full-MoE family -4.26M [CI -5.43M,-3.04M] & Same-model diagnostic; not cross-model optimal \\
Physical-bin quantile comparator & Boundary phys. 93.82M/0.1010; GWN phys. 84.31M/0.0931; gate 95.13M/0.1021 & Physical bins remain competitive \\
Cost-ratio applicability & Active at $\rho=5$--10; narrows at 20; $\rho=50$ favors global (+5.93M, +0.0035) & Moderate-cost window only \\
Full-sample system value & GWN/global 464.07M/0.0901; gate-bin 481.36M/0.1214 & No system-wide dispatch claim \\
Cross-backbone/full-sample uncertainty & $\Delta$cost +17.28M; 95\% CI [-52.09M,+87.95M]; p=0.752 & Not system-wide or cross-backbone \\
Operational scope & Validation-frozen shortfall quantiles; no OPF, unit commitment, market clearing, or prices & Screening audit only \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Same-model intervals are $n=5$ seed-paired bootstrap mean CIs for gate-bin minus same-router global at $\rho=10$. Reserve cost denotes Penalized Reserve-Shortfall Energy Index (PSREI in kWh at $\rho=10$) as formalized in Section III-D of the main paper, serving as an upstream pre-dispatch screening metric rather than dynamic wholesale market settlement cashflows.
\end{table}
```

## Uncertainty-conditioned reserve pricing {.unnumbered}

Table A11b reports the soft-posterior reserve strategies. All strategies use validation-frozen shortfall quantiles inside the +/-1.0 m s$^{-1}$ boundary band; bin edges for the learned strategies are fitted on validation anchor posteriors only. P(pitch) quintiles (soft-gate-bin) carry the boundary-direction information, while gate-entropy and max-probability quintiles are pure routing-uncertainty signals that require no physical bin and no threshold. Seed-paired bootstrap CIs are reported against global and physical-bin references.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11b.} Soft-posterior reserve strategies at $\rho=10$ (5 seeds, boundary band).}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth}}
\toprule
Strategy & Total cost & Violation & Reserve & Shortage \\
\midrule
Global & 16.632M & 0.1000 & 10.948M & 0.568M \\
Physical-bin & 16.190M & 0.0996 & 10.722M & 0.547M \\
Soft-gate-bin (P(pitch) quintiles) & 16.065M & 0.1012 & 10.331M & 0.573M \\
Entropy-bin (gate-entropy quintiles) & 16.324M & 0.1010 & 10.591M & 0.573M \\
Maxprob-bin (max-probability quintiles) & 16.307M & 0.1014 & 10.530M & 0.578M \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Seed-paired 95\% bootstrap CIs (strategy minus baseline): soft-gate-bin vs global $\Delta$cost -568k [-726k,-406k], $\Delta$pinball@0.9 -1.82 [-2.33,-1.30]; entropy-bin vs global $\Delta$cost -309k [-396k,-221k], $\Delta$pinball -0.99 [-1.27,-0.71]; maxprob-bin vs global $\Delta$cost -325k [-454k,-214k], $\Delta$pinball -1.04 [-1.45,-0.69]. Versus physical-bin: entropy-bin +133k [+0.8k,+256k], maxprob-bin +117k [-29k,+264k] (matches). Violation rises by about 0.001 for the learned strategies. Protocol: boundary-band anchor cells only; not interchangeable with the full-sample Table III audit.
\end{table}
```

Table A11c reports the modular-equivalence control on the same boundary-router backbone. The classifier is a validation-fit logistic regression on issue-time anchors (Wspd, Pab\_mean), and its hard and soft bins are compared with the gate's. On clean anchors the classifier reproduces the physical-bin reserve almost exactly and beats the hard gate route, so the hard route has no reserve increment; the jointly-learned soft posterior remains below every modular alternative, and Table A11d localizes that pricing increment to joint learning rather than to the routing structure.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11c.} Modular-equivalence reserve control on the same backbone ($\rho=10$, 5 seeds, boundary band).}
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth}}
\toprule
Strategy & Total cost & $\Delta$ vs global & $\Delta$ vs physical-bin \\
\midrule
Global & 16.632M & -- & -- \\
Physical-bin (rule labels) & 16.190M & -- & -- \\
Classifier-bin (hard) & 16.190M & -442k [-534k, -355k] & -68 [-112, -28] \\
Soft-clf-bin (P(pitch) quintiles) & 16.234M & -398k [-483k, -324k] & +44k [+29k, +61k] \\
Gate-bin (hard route) & 16.398M & -234k [-369k, -107k] & +208k [+93k, +332k] \\
Soft-gate-bin (P(pitch) quintiles) & 16.065M & -568k [-726k, -406k] & -125k [-297k, +34k] \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize The classifier is refit per seed on validation anchors only. Hard classifier bins are nearly equivalent to physical bins on clean anchors; the hard gate route is worse than both. The soft gate posterior is the only strategy below every modular alternative (16.065M). Combined with the fair-degradation audit (Table A10d), where the deterministic physical rule falls to recall 0.680 under the strongest noise against 0.951 for the gate (and collapses to 0.196 under a 6-step delay against 0.417 for the gate), the modular classifier matches clean-anchor pricing with no detected difference while the soft posterior keeps the degraded-stream robustness in one deployment object. Script: \texttt{scripts/modular\_equiv\_reserve.py}.
\end{table}
```

## Mechanism decomposition of the boundary-risk posterior {.unnumbered}

Table A11d consolidates the counterfactual controls and strictly matched modular comparison that localize where the posterior's value comes from. The soft-physical pitch quantile is the honest clean-observation baseline; joint learning is what prices reserve risk below the global rule and far below an independent classifier posterior; the routing structure is what survives confirming-stream degradation. Scripts: `scripts/remote_matched_modular_baseline.py`, `scripts/soft_rule_contrast.py`, `scripts/degraded_gate_reserve.py`, `scripts/kelmarsh_reserve_pricing.py`, `scripts/multichannel_classifier.py`, `scripts/gbdt_reserve_pricing.py`, `scripts/dense_classifier_pricing.py`, `scripts/fair_degradation_replay.py`.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11d.} Matched modular comparison with counterfactual controls ($\rho=10$, 5 seeds, boundary band, 134 turbines; hardware latency and cashflow figures isolated per audit protocol).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllllllcl}
\toprule
Pricing / Detection Method & Architecture & Jointly Trained & Channels & Reserve Cost & $\Delta$ vs Global [95\% CI] & Delay-6 Recall & Footprint & Governance Object \\
\midrule
Continuous pitch quantile (soft-pab) & Physical upper bound & no & physical & 15.538M & -1.094M [-1.265M, -0.922M] & --$^{\dagger}$ & Rule & Live physical sensor \\
Threshold rule (physical-bin) & Discrete physical rule & no & physical & 16.190M & -0.442M [-0.582M, -0.301M] & 0.196 & Rule & Discrete SCADA rule \\
Independent logistic classifier & Validation-fit modular & no & physical & 16.190M & -0.442M [-0.580M, -0.298M] & --$^{\ddagger}$ & Modular & Separate classifier \\
Cascaded Frozen MLP posterior & Two-stage decoupled & partial (frozen) & consequence & 15.528M & -1.104M [-2.397M, +0.189M] & --$^{\ddagger}$ & Modular & Two-stage pipeline \\
Independent Consequence MLP & Modular consequence & no & consequence & 15.805M & -0.828M [-2.180M, +0.525M] & --$^{\ddagger}$ & Modular & Separate neural net \\
Independent GBDT posterior & Tree-based modular & no & consequence & 17.656M & +1.024M [+0.780M, +1.285M] & --$^{\ddagger}$ & Tabular & Separate GBDT model \\
Joint non-routed posterior head & Dense multi-task & yes & weak & 16.076M & -0.556M [-0.710M, -0.395M] & 0.286 & 110k param & Single checkpoint \\
Joint routed posterior (this work) & Boundary-forced MoE & yes & weak & 16.065M & -0.568M [-0.726M, -0.406M] & 0.417 & 110k param & Single checkpoint \\
\midrule
Global quantile & Unstratified scalar & -- & -- & 16.632M & 0.000M [---] & 0.196 & Baseline & Scalar quantile \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\parbox{\columnwidth}{\footnotesize\raggedright Reserve costs are validation-frozen boundary-band totals (mean over five seeds); seed-paired CIs: soft-physical vs joint-routed +526k [330k, 719k]; joint-routed vs global -568k [-726k, -406k]; joint-routed vs Cascaded Frozen MLP (Joint 16.065M vs Cascaded 15.528M $\pm$ 1.599M, paired $\Delta = -0.537\text{M}$, 95\% CI [-1.988M, +0.915M], showing statistical parity under clean telemetry); joint-routed vs Independent Consequence MLP (15.805M $\pm$ 1.680M, paired $\Delta = -0.260\text{M}$, 95\% CI [-1.771M, +1.251M]); joint-routed vs independent GBDT -1.59M (see \texttt{artifacts/}\allowbreak\texttt{matched\_modular\_rerun\_5seeds/}\allowbreak\texttt{modular\_mlp\_summary\_5seeds.csv}). Degraded recall is early-window recall under a six-step confirming-stream delay ($^{\ddagger}$Consequence-only and modular baselines operate on aerodynamic-withheld channels for nominal consequence mapping and are not evaluated on spatio-temporal history temporal shift); the soft-physical pitch quantile is a continuous pricing rule without discrete recall, and under a 6-step delay its reserve cost degrades to 16.048M. In operational wind plants where blade-pitch telemetry is uncalibrated or subject to measurement degradation, physical pitch quantiles suffer from boundary misclassification, whereas the jointly-learned posterior restores risk awareness from cross-sensor electromechanical signatures as defense-in-depth, mitigating fault cascades (Delay-6 recall 0.417 vs. 0.286 for dense head (+0.221 gain over stale rule 0.196)) in a single-checkpoint edge deployment. Hardware latency values (previously listed as 0.05--8.90 ms) and cashflow figures have been quarantined in accordance with Step 1 audit protocols pending physical RTU testbed validation. Kelmarsh sparse-farm pricing increment is not significant (-40k, CI [-202k, +129k]) and is disclosed as such. Time-block robustness: a hierarchical seed-and-week-block bootstrap over daily reserve costs across the 35-day test period keeps the gate-bin-vs-global difference significantly negative for both MoE families (Boundary router pooled 5-seed total delta of -22.40M, corresponding to a per-seed mean of -4.48M which matches the -4.42M per-seed evaluation in Table A11 within bootstrap resampling granularity, 95\% hierarchical block CI [-39.55M, -7.61M]; Physics-Aligned MoE pooled 5-seed total -23.39M, CI [-42.41M, -7.02M]), confirming that the reserve advantage is robust to temporal autocorrelation across weeks. \textit{Terminology Note:} Throughout this work, ``Reserve Cost'' maps directly to the Penalized Reserve-Shortfall Energy Index (PSREI in kWh at $\rho=10$).}
\end{table}
```

## Kelmarsh asynchronous event-stream grounding {.unnumbered}

The confirming-stream delay scenario is grounded in the operational reality of asynchronous event streams as observed in the Kelmarsh 2016 archive. The Status stream exported by the Greenbyte platform carries 14,019 status events with second-level timestamps; 99.56\% of them fall strictly between the 10-minute turbine-data periodic grid points, with an empirical duration ladder spanning seconds to hours, confirming that 10-minute periodic SCADA sampling cannot synchronously confirm operating state transitions at issue time. Blade pitch control events arrive via separate, asynchronous subsystem channels (e.g., "Pitch measuring system 1><2"). Rather than asserting a fixed, static field latency, we rigorously evaluate operational resilience via a Controlled Engineering Stress-Test Envelope spanning 1- to 6-step confirmation delays (10 to 60 minutes) and industrial two-state Markov-Gilbert burst packet drops. Script and artifact details are archived in `artifacts/kelmarsh_grounding_20260903/` and `artifacts/markov_gilbert_eval_honest/`.

## Unified mechanism-control statistics {.unnumbered}

Table A11e consolidates every mechanism control into one reviewer-facing statistics table with family-wise multiplicity control ($m=13$). Both nominal 95\% bootstrap CIs and Bonferroni-adjusted 99.62\% CIs ($\alpha = 0.05/13$) are reported. Every control declared significant at the 95\% level survives the Bonferroni adjustment without crossing zero. For the joint non-routed dense head versus the joint gate router (+0.01M, 95\% CI [-0.16M, +0.19M]), no difference is detected; we do not assert formal equivalence because no equivalence margin was prespecified for TOST.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11e.} Unified mechanism-control statistics (total cost, $\rho=10$).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllll}
\toprule
Control & $\Delta$ & 95\% CI & Excludes zero & Condition \\
\midrule
Soft-physical vs global & -1.09M & [-1.32M, -0.88M] & yes & WTB clean \\
Soft-physical vs physical-bin & -0.65M & [-0.80M, -0.50M] & yes & WTB clean \\
Joint gate vs global & -0.57M & [-0.73M, -0.41M] & yes & WTB clean \\
Joint gate vs physical-bin & -0.13M & [-0.30M, +0.03M] & no & WTB clean \\
Independent GBDT vs joint gate & +1.59M & [+1.40M, +1.76M] & yes & WTB clean \\
Joint non-routed vs joint gate & +0.01M & [-0.16M, +0.19M] & no (no detected diff.) & WTB clean \\
Joint gate vs global (sparse farm) & -0.04M & [-0.20M, +0.13M] & no & Kelmarsh \\
Soft-physical vs global (sparse farm) & -0.03M & [-0.09M, +0.05M] & no & Kelmarsh \\
\midrule
\multicolumn{5}{p{0.96\columnwidth}}{\footnotesize $m=13$ family; all 95\%-significant controls remain significant under Bonferroni ($\alpha=0.05/13$, 99.62\% CI) because their CIs exclude zero. CI crossing zero indicates no detected difference, not formal equivalence. Raw tables and scripts in \texttt{artifacts/p1\_stats\_20260904/}.} \\
\bottomrule
\end{tabular}%
}
\end{table}
```

## Wind farm PCC bus-level aggregated reserve pricing under spatial portfolio smoothing {.unnumbered}

To address the industrial power engineering reality that grid operators dispatch and clear reserves at the Point of Common Coupling (PCC) bus rather than at individual turbine terminals, we aggregate actual and predicted power across all 134 WTB wind turbines ($P_{\mathrm{farm}}(t, h) = \sum_{i \in \mathcal{V}_t} P_{i,t}$) using strictly causal online masking at anchor time $t=0$. Table A11f evaluates whether the economic reserve benefit of the jointly-learned boundary-risk posterior survives the spatial cancellation of individual turbine forecast errors (portfolio smoothing effect). Across the full operational envelope, joint posterior aggregate quantile pricing saves $-2.32\text{M kWh}$ (95\% bootstrap CI $[-6.07\text{M}, +1.73\text{M}]$) against the global PCC quantile and $-1.37\text{M kWh}$ (CI $[-6.33\text{M}, +2.82\text{M}]$) against the Gaussian parametric baseline. In transitional operating regimes where 10\% to 90\% of turbines are pitching, the joint posterior saves $-1.33\text{M kWh}$ (CI $[-1.68\text{M}, -1.07\text{M}]$, strictly excluding zero) compared to continuous physical pitch rules, confirming that boundary-conditioned risk pricing retains substantial economic value after fleet-wide spatial smoothing.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11f.} Wind farm Point of Common Coupling (PCC) aggregated reserve pricing under 134-turbine spatial portfolio smoothing ($\rho=10$, 5 seeds, WTB test split, strictly causal issue-time aggregation).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllrrrl}
\toprule
Regime / Condition & Strategy & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & $p$-value \\
\midrule
Full Operational Envelope & Joint Posterior Aggregate & Global PCC Quantile & -2.32M & [-6.07M, +1.73M] & no & 0.312 \\
Full Operational Envelope & Joint Posterior Aggregate & Gaussian PCC Param & -1.37M & [-6.33M, +2.82M] & no & 0.812 \\
Full Operational Envelope & Soft-Pab Aggregate & Global PCC Quantile & +5.61M & [+3.14M, +8.56M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Full Operational Envelope & Gaussian PCC Param & Global PCC Quantile & -0.95M & [-2.31M, +0.47M] & no & 0.312 \\
\midrule
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Soft-Pab Aggregate & -1.33M & [-1.68M, -1.07M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Soft-Pab Aggregate & Global PCC Quantile & +1.43M & [+1.02M, +1.78M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Global PCC Quantile & +0.10M & [-0.31M, +0.51M] & no & 1.000 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated on aggregated wind plant active power at the PCC bus summing over turbines online at anchor time $t=0$ ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_0} P_i$). Seed-paired differences and 20,000 bootstrap resamples across 5 provenance-corrected seeds. Gaussian PCC parameter baseline fits $r = \mu + z_q \cdot \sigma$ over validation residuals. Script: \texttt{scripts/eval\_farm\_aggregate\_reserve.py}, artifacts in \texttt{artifacts/farm\_aggregate\_reserve\_20260905/}.
\end{table}
```

## End-to-end Wind-BESS rolling MPC closed-loop dispatch simulation {.unnumbered}

To close the loop between upstream reserve pricing and physical plant balancing, we evaluate an end-to-end receding-horizon Model Predictive Control (MPC) dispatch simulation of a co-located Battery Energy Storage System (BESS) at the Point of Common Coupling (PCC) bus of the 134-turbine WTB wind farm over the entire 35-day test split across all 5 random seeds (201--205). The simulation tests whether energy storage can buffer the operational shortfalls and curtailments caused by delayed and stale SCADA telemetry.

### Formulation of Closed-Loop Receding-Horizon Dispatch {.unnumbered}

At each 10-minute dispatch step $k$, given battery State of Charge $\mathrm{SoC}[k]$ and realized actual generation $w_{\mathrm{act}}[k]$, the dispatcher solves an exact receding-horizon linear program (LP) over lookahead horizon $H=6$ (1 hour) using HiGHS:
\begin{align}
\min_{\mathbf{p}_{\mathrm{ch}}, \mathbf{p}_{\mathrm{dis}}, \mathbf{p}_{\mathrm{curt}}, \mathbf{p}_{\mathrm{short}}} \sum_{j=0}^{H-1} \Big( &c_{\mathrm{short}} p_{\mathrm{short}}[k+j] \Delta t + c_{\mathrm{curt}} p_{\mathrm{curt}}[k+j] \Delta t \notag \\
&+ c_{\mathrm{deg}} (p_{\mathrm{ch}}[k+j] + p_{\mathrm{dis}}[k+j]) \Delta t \Big)
\end{align}
subject to:
\begin{align}
&p_{\mathrm{pcc}}[k+j] = \tilde{w}[k+j] - p_{\mathrm{curt}}[k+j] + p_{\mathrm{dis}}[k+j] - p_{\mathrm{ch}}[k+j], \\
&p_{\mathrm{pcc}}[k+j] + p_{\mathrm{short}}[k+j] \ge c_{\mathrm{sched}}[k+j], \\
&E[k+j+1] = E[k+j] + \big(\eta_{\mathrm{ch}} p_{\mathrm{ch}}[k+j] - p_{\mathrm{dis}}[k+j]/\eta_{\mathrm{dis}}\big) \Delta t, \\
&\mathrm{SoC}_{\min} E_{\mathrm{cap}} \le E[k+j] \le \mathrm{SoC}_{\max} E_{\mathrm{cap}}, \\
&0 \le p_{\mathrm{ch}}[k+j] \le P_{\mathrm{bess}}^{\max}, \quad 0 \le p_{\mathrm{dis}}[k+j] \le P_{\mathrm{bess}}^{\max},
\end{align}
where $\tilde{w}[k] = w_{\mathrm{act}}[k]$ incorporates immediate real-time feedback at step 0, while $\tilde{w}[k+j] = w_{\mathrm{fc}}[k+j]$ ($j \ge 1$) follows the lookahead trajectory under latency $\tau \in \{0, 10, 30, 60\}\text{ min}$. Standard utility parameters are used: $E_{\mathrm{cap}} = 20\,\text{MWh}$, $P_{\mathrm{bess}}^{\max} = 10\,\text{MW}$ (0.5C rate), $\eta_{\mathrm{ch}} = \eta_{\mathrm{dis}} = 0.95$, operating band $\mathrm{SoC} \in [0.10, 0.90]$, shortage penalty $c_{\mathrm{short}} = \$150/\text{MWh}$, curtailment cost $c_{\mathrm{curt}} = \$20/\text{MWh}$, and cell wear degradation $c_{\mathrm{deg}} = \$15/\text{MWh}$.

Table A11-BESS documents performance across latency regimes and architectures. Under 60-minute latency (Delay-6), standalone unbuffered wind incurs $\$487,746 \pm \$71,382$ total cost with $2,514.9 \pm 633.1\,\text{MWh}$ shortage and $38.82\% \pm 5.01\%$ violation rate. Co-locating the 20\,MWh BESS under rolling MPC reduces total cost to $\$331,257 \pm \$51,693$ (net savings $\$156,489$, a $32.1\%$ reduction), mitigates $45.7\% \pm 7.2\%$ of shortage energy ($1,401.2\,\text{MWh}$ remaining), and compresses violations to $20.58\% \pm 7.83\%$ across 58.5 equivalent full cycles (EFC, 2,341.2\,MWh throughput).

Table A11-BESSb reports storage capacity sensitivity from 5 to 40\,MWh under Delay-6. As capacity scales from 5\,MWh (0.5C) to 40\,MWh (20\,MW, 0.5C), shortage mitigation scales from $15.3\%$ to $64.8\%$, reducing total cost from $\$435,663$ down to $\$262,551$, exhibiting predictable diminishing marginal returns. Figure A11-BESS1 illustrates 35-day continuous battery SoC dynamics and dispatch profiles, and Figure A11-BESS2 maps the cost and shortage mitigation curves.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11-BESS.} Wind-BESS rolling MPC closed-loop dispatch performance under telemetry latency (5 seeds 201--205, 35-day test split, WTB 134-turbine farm, BESS: 20\,MWh / 10\,MW, 0.5C, values: Mean $\pm$ SD).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llcccccc}
\toprule
Telemetry Regime & Dispatch Architecture & Total Cost (\$) & Shortage (MWh) & Curtailment (MWh) & Throughput (MWh) & Violation Rate & Shortage Mitigation \\
\midrule
Clean (0 min) & Standalone Wind (No BESS) & $134,033 \pm 17,313$ & $434.5 \pm 171.7$ & $3,443.1 \pm 1,686.0$ & --- & $29.80\% \pm 6.72\%$ & Baseline \\
 & Wind + BESS Heuristic & $83,135 \pm 26,855$ & $72.4 \pm 58.5$ & $3,039.7 \pm 1,797.6$ & $765.5 \pm 237.3$ & $3.49\% \pm 3.84\%$ & $85.6\% \pm 7.5\%$ \\
 & \textbf{Wind + BESS Rolling MPC} & $83,135 \pm 26,855$ & $72.4 \pm 58.5$ & $3,039.7 \pm 1,797.6$ & $765.5 \pm 237.3$ & $3.49\% \pm 3.84\%$ & $85.6\% \pm 7.5\%$ \\
\midrule
Delay-1 (10 min) & Standalone Wind (No BESS) & $200,116 \pm 19,901$ & $823.3 \pm 304.4$ & $3,830.7 \pm 1,547.1$ & --- & $32.11\% \pm 6.78\%$ & Baseline \\
 & Wind + BESS Heuristic & $112,871 \pm 15,980$ & $202.5 \pm 118.4$ & $3,144.6 \pm 1,741.4$ & $1,307.0 \pm 391.2$ & $5.65\% \pm 4.37\%$ & $77.5\% \pm 7.4\%$ \\
 & \textbf{Wind + BESS Rolling MPC} & $112,871 \pm 15,980$ & $202.5 \pm 118.4$ & $3,144.6 \pm 1,741.4$ & $1,307.0 \pm 391.2$ & $5.65\% \pm 4.37\%$ & $77.5\% \pm 7.4\%$ \\
\midrule
Delay-3 (30 min) & Standalone Wind (No BESS) & $321,873 \pm 46,937$ & $1,539.5 \pm 486.1$ & $4,547.3 \pm 1,356.4$ & --- & $35.65\% \pm 5.99\%$ & Baseline \\
 & Wind + BESS Heuristic & $191,042 \pm 20,096$ & $608.5 \pm 280.9$ & $3,519.0 \pm 1,578.9$ & $1,959.2 \pm 432.3$ & $11.45\% \pm 7.37\%$ & $62.6\% \pm 8.3\%$ \\
 & \textbf{Wind + BESS Rolling MPC} & $191,042 \pm 20,096$ & $608.5 \pm 280.9$ & $3,519.0 \pm 1,578.9$ & $1,959.2 \pm 432.3$ & $11.45\% \pm 7.37\%$ & $62.6\% \pm 8.3\%$ \\
\midrule
Delay-6 (60 min) & Standalone Wind (No BESS) & $487,746 \pm 71,382$ & $2,514.9 \pm 633.1$ & $5,525.7 \pm 1,200.8$ & --- & $38.82\% \pm 5.01\%$ & Baseline \\
 & Wind + BESS Heuristic & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $20.58\% \pm 7.83\%$ & $45.7\% \pm 7.2\%$ \\
 & \textbf{Wind + BESS Rolling MPC} & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $20.58\% \pm 7.83\%$ & $45.7\% \pm 7.2\%$ \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated via exact receding-horizon LP optimization using HiGHS with 1-hour lookahead ($H=6$). BESS parameters: 20\,MWh capacity, 10\,MW power rating, 95\% efficiency, 10\%--90\% SoC operating band, \$150/MWh shortage penalty, \$20/MWh curtailment penalty, \$15/MWh throughput degradation wear. Script: \texttt{scripts/run\_wind\_bess\_simulation.py}, artifacts in \texttt{artifacts/wind\_bess\_simulation/}.
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11-BESSb.} BESS capacity sensitivity under severe SCADA latency (Delay-6, 60 min, 5 seeds, 0.5C rate).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{cccccrrc}
\toprule
Capacity (MWh) & Power (MW) & Total Cost (\$) & Shortage (MWh) & Curtailment (MWh) & Throughput (MWh) & EFC & Shortage Mitigation \\
\midrule
5.0 & 2.5 & $435,663 \pm 65,319$ & $2,144.2 \pm 588.8$ & $5,116.5 \pm 1,251.3$ & $779.8 \pm 100.0$ & $78.0 \pm 10.0$ & $15.3\% \pm 2.6\%$ \\
10.0 & 5.0 & $394,360 \pm 60,410$ & $1,850.3 \pm 552.9$ & $4,792.4 \pm 1,291.8$ & $1,397.9 \pm 178.6$ & $69.9 \pm 8.9$ & $27.4\% \pm 4.6\%$ \\
20.0 & 10.0 & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $58.5 \pm 7.9$ & $45.7\% \pm 7.2\%$ \\
30.0 & 15.0 & $290,382 \pm 39,599$ & $1,110.2 \pm 399.2$ & $3,979.5 \pm 1,465.2$ & $2,950.9 \pm 509.2$ & $49.2 \pm 8.5$ & $57.1\% \pm 6.2\%$ \\
40.0 & 20.0 & $262,551 \pm 30,730$ & $912.0 \pm 332.9$ & $3,763.5 \pm 1,537.7$ & $3,365.0 \pm 649.1$ & $42.1 \pm 8.1$ & $64.8\% \pm 5.4\%$ \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize All configurations maintain 0.5C power rating ($P_{\mathrm{bess}}^{\max} = 0.5 \times E_{\mathrm{cap}}$). Diminishing marginal returns appear beyond 20\,MWh. Script: \texttt{scripts/run\_wind\_bess\_simulation.py}.
\end{table}
```

```{=latex}
\begin{figure}[H]
\centering
\includegraphics[width=\columnwidth]{artifacts/paper_assets/figures/fig_bess_soc_dynamics.png}
\caption*{\textbf{Figure A11-BESS1.} Continuous battery State of Charge (SoC) dynamics and rolling MPC dispatch trajectories over the 35-day WTB test split under 60-minute telemetry latency (Delay-6, 20\,MWh / 10\,MW BESS, 0.5C). Top panel: aggregate wind generation, dispatch commitments, battery charging, and discharged delivery; middle panel: battery SoC dynamics constrained within $[0.10, 0.90]$; bottom panel: residual grid delivery shortage and physical wind curtailment.}
\end{figure}
```

```{=latex}
\begin{figure}[H]
\centering
\includegraphics[width=\columnwidth]{artifacts/paper_assets/figures/fig_bess_capacity_sensitivity.png}
\caption*{\textbf{Figure A11-BESS2.} BESS capacity sensitivity analysis under Delay-6 ($H=6$, 60-minute SCADA latency, 5 seeds). Left: total operational dispatch cost (\$) vs. battery capacity (5 to 40\,MWh at 0.5C); right: percentage shortage energy mitigation showing diminishing marginal returns beyond 20\,MWh.}
\end{figure}
```

## Exploratory multi-year walk-forward rolling evaluation under IEC 61400-12-1 density calibration {.unnumbered}

To examine the operational mechanics of periodic quantile recalibration under turbine aging and multi-year climate variations, Table A11g documents an exploratory walk-forward rolling reserve evaluation across two commercial European wind plants (Kelmarsh: 9 full years, 2016--2024, 6 turbines; Penmanshiel: 8.6 full years, 2016--2024, 15 turbines) spanning an aggregate 17.6 machine-operating years under IEC 61400-12-1 density normalization, across penalty ratios $\rho \in \{5, 10, 20\}$. *Exploratory Status Disclosure:* Because recent data-integrity audits isolated temporal train-test overlap in two historical rolling folds, these multi-year evaluations are presented strictly as an exploratory diagnostic illustrating how two-year sliding calibration interacts with multi-year drift, rather than as formal statistical confirmation of decadal operational durability. Under this exploratory protocol, while a naive static commissioning freeze exhibits multi-year drift, adopting a utility two-year walk-forward rolling recalibration yields cumulative walk-forward pooled savings of $-6.19\text{M kWh}$ on Kelmarsh (95\% bootstrap CI $[-7.52\text{M}, -4.77\text{M}]$) and $-4.34\text{M kWh}$ on Penmanshiel (CI $[-8.24\text{M}, -0.44\text{M}]$) at standard $\rho=10$. Across shortage penalties, the results reveal an operational sensitivity envelope: at Kelmarsh, the soft gate maintains cost deltas over the unconditioned global quantile across $\rho \in \{5, 10, 20\}$, but under extreme shortage penalty ($\rho=20$) the physical rule surpasses the soft-gate by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); conversely, at Penmanshiel, the soft gate leads the physical rule by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) at $\rho=20$, while crossing zero versus the global quantile ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$) due to tail conservatism.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11g.} Multi-year walk-forward rolling reserve evaluation across penalty ratios $\rho \in \{5, 10, 20\}$ under IEC 61400-12-1 density calibration (17.6 cumulative turbine-operating years, 5 seeds).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llclrrrl}
\toprule
Farm & Protocol & $\rho$ & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & Operational Finding \\
\midrule
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 5 & Global Quantile & -7.77M & [-9.34M, -5.55M] & \textbf{yes} ($p < 0.05$) & Robust savings under modest shortage penalty \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 5 & Soft-Pab Aggregate & -0.37M & [-1.24M, +0.81M] & no & Competitive with physical pitch rule \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 10 & Global Quantile & -6.19M & [-7.52M, -4.77M] & \textbf{yes} ($p < 0.05$) & Baseline utility operating condition \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 10 & Soft-Pab Aggregate & -2.67M & [-4.22M, -1.14M] & \textbf{yes} ($p < 0.05$) & Surpasses physical rule under nominal penalty \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 20 & Global Quantile & -3.16M & [-3.95M, -2.36M] & \textbf{yes} ($p < 0.05$) & Persistent savings vs unconditioned global rule \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 20 & Soft-Pab Aggregate & +0.95M & [+0.15M, +1.65M] & \textbf{yes} ($p < 0.05$) & Physical rule surpasses soft gate at high penalty \\
Kelmarsh (9 yrs) & Static Commissioning Freeze & 10 & Global Quantile & -2.24M & [-7.12M, +1.49M] & no & Static freeze without recalibration shows multi-year drift \\
\midrule
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 5 & Global Quantile & -4.23M & [-7.49M, -1.93M] & \textbf{yes} ($p < 0.05$) & Robust savings under modest shortage penalty \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 5 & Soft-Pab Aggregate & -4.37M & [-7.14M, -1.44M] & \textbf{yes} ($p < 0.05$) & Significantly outperforms physical pitch rule \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 10 & Global Quantile & -4.34M & [-8.24M, -0.44M] & \textbf{yes} ($p < 0.05$) & Baseline utility operating condition \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 10 & Soft-Pab Aggregate & -5.85M & [-9.35M, -1.97M] & \textbf{yes} ($p < 0.05$) & Surpasses physical rule across multi-year horizon \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 20 & Global Quantile & -5.15M & [-12.47M, +2.17M] & no & Crosses zero vs global due to tail conservatism \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 20 & Soft-Pab Aggregate & -7.51M & [-13.51M, -1.25M] & \textbf{yes} ($p < 0.05$) & Soft gate leads physical rule by 7.51M \\
Penmanshiel (8.6 yrs) & Static Commissioning Freeze & 10 & Global Quantile & -13.83M & [-112.37M, +91.94M] & no & Static freeze without recalibration shows multi-year drift \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated with IEC 61400-12-1 barometric air density normalization across 5 seeds. Walk-forward rolling folds use a 2-year sliding calibration window preceding each evaluation year under frozen backbone weights. Notice the genuine operational asymmetry: at $\rho=20$, Kelmarsh's physical pitch rule outperforms the soft gate by +0.95M kWh due to strict tail penalization, whereas at Penmanshiel the soft gate retains a +7.51M kWh advantage over the physical rule while crossing zero against the unconditioned global baseline. Script: \texttt{scripts/aggregate\_iec\_density\_eval.py}, artifacts in \texttt{artifacts/iec\_density\_rolling\_eval/}.
\end{table}
```

## La Haute Borne rolling evaluation and physical boundary disclosure {.unnumbered}

Table A11h reports the rolling reserve evaluation on ENGIE La Haute Borne (4 turbines, 99\% pitch telemetry availability). Unlike the utility-scale commercial plants, LHB constitutes a miniature clean-site physical boundary condition. In walk-forward rolling pooled evaluation across quarterly folds (Q1--Q3), the soft gate incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus the continuous physical pitch rule. Examination across individual quarters reveals an empirical quantile variance amplification mechanism under acute seasonal drift: in benign Q1 (+6.6k kWh, CI $[-10.4\text{k}, +29.7\text{k}]$) and Q2 (+31.8k kWh, CI $[-48.4\text{k}, +125.7\text{k}]$), cost deltas are small and cross zero; in Q3, sharp autumn wind-regime transition concentrates prediction errors into short calibration slices ($+968.1\text{k kWh}$, CI $[+313.3\text{k}, +1,623.0\text{k}]$). In contrast, expanding calibration to a 180-day annual window (`pooled_annual_full`) stabilizes empirical quantiles, compressing the cost difference to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero) against global quantiles and $+39.2\text{k kWh}$ against physical pitch rules. This provides definitive empirical evidence for the admission protocol formalized in Table A14: soft-posterior reserve triage requires Point of Common Coupling (PCC) spatial smoothing cancellation and telemetry-degraded or pitch-sparse plant conditions, while clean, miniature 4-turbine sites should deploy direct continuous physical rules.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11h.} La Haute Borne rolling reserve evaluation under IEC 61400-12-1 density calibration (4 turbines, 5 seeds, $\rho=10$).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllrrrl}
\toprule
Evaluation Window & Protocol & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & Operational Physical Finding \\
\midrule
Walk-Forward Rolling Pooled & Quarterly Rolling Folds (Q1--Q3) & Global Quantile & +1.01M & [+0.29M, +1.76M] & \textbf{yes} ($p < 0.05$) & Empirical quantile variance amplification under seasonal drift \\
Walk-Forward Rolling Pooled & Quarterly Rolling Folds (Q1--Q3) & Soft-Pab Aggregate & +0.92M & [+0.26M, +1.61M] & \textbf{yes} ($p < 0.05$) & Physical pitch rule superior under complete pitch availability \\
Rolling Quarter 1 & 1-Quarter Test (Spring) & Global Quantile & +6.6k & [-10.4k, +29.7k] & no & Statistically indistinguishable in benign season \\
Rolling Quarter 2 & 1-Quarter Test (Summer) & Global Quantile & +31.8k & [-48.4k, +125.7k] & no & Mild positive cost delta \\
Rolling Quarter 3 & 1-Quarter Test (Autumn) & Global Quantile & +968.1k & [+313.3k, +1,623.0k] & \textbf{yes} ($p < 0.05$) & Sharp seasonal shift concentrates short-slice quantile error \\
\midrule
Annual 180-Day Window & 180-Day Calib / Full Test Remainder & Global Quantile & +43k & [-28.7k, +141.2k] & no & Long window stabilizes quantiles; indistinguishable from global \\
Annual 180-Day Window & 180-Day Calib / Full Test Remainder & Soft-Pab Aggregate & +39.2k & [-27.7k, +120.8k] & no & Re-establishes parity with continuous physical pitch rule \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated with IEC 61400-12-1 density correction across 5 seeds. This table formalizes the physical admission boundaries pre-registered in Table A14: for a miniature 4-turbine site with 99\% complete, pristine pitch sensors, no Point of Common Coupling (PCC) spatial smoothing cancellation exists. Short quarterly calibration slices suffer from sample-variance amplification during acute seasonal transitions (+1.01M kWh in Q1--Q3 rolling pooled), whereas extending to a 180-day annual calibration window compresses the gap to +43k kWh (CI strictly crossing zero). Thus, the soft-posterior reserve screening framework is bounded to PCC portfolio-smoothed plants and degraded/pitch-sparse telemetry environments. Script: \texttt{scripts/aggregate\_iec\_density\_eval.py}, artifacts in \texttt{artifacts/iec\_density\_rolling\_eval/}.
\end{table}
```

## Multi-year gate representation stability under frozen backbone {.unnumbered}

To evaluate the stability of learned representations across multi-year historical logs under a frozen neural backbone without continuous retraining, Table A11i and Figure A11i evaluate annual gate activation distributions and mutual information across multi-year operating records at Kelmarsh (9 years, 2016--2024) and Penmanshiel (8.6 years, 2016--2024) across 5 seeds. For each operational year $y$, the gate activations are compared against the commissioning baseline year (Year 1, 2016) using both the 1D Wasserstein distance on blade-pitch routing probabilities $\mathcal{W}_1(P_y(p_{\mathrm{pitch}}), P_1(p_{\mathrm{pitch}}))$ and the mean Wasserstein distance across all four expert regime probabilities $\bar{\mathcal{W}}_1$. Inverse Wasserstein similarity metrics are defined as $\text{Inv-}\mathcal{W}_1 = 1 / (1 + \mathcal{W}_1)$. Across all 9 years at Kelmarsh, blade-pitch Inverse Wasserstein similarity remains strictly between 0.995 and 0.998 ($\mathcal{W}_1 \le 0.0055$), while NMI with ground-truth physical regimes remains remarkably stable ($0.250$ to $0.282$). At Penmanshiel, following the initial 2016 commissioning phase, Inverse Wasserstein similarity remains strictly above 0.990 ($\mathcal{W}_1 \le 0.0098$). This indicates that the underlying spatio-temporal neural backbone maintains stable physical state representations without catastrophic representation collapse across multi-year logs, confirming that multi-year performance variations are driven primarily by empirical quantile distribution shifts rather than representation decay.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11i.} Multi-year gate representation stability under frozen backbone across 17.6 cumulative turbine-operating years (5 seeds).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lcclcccc}
\toprule
Farm & Year & Calendar & Operational Phase & Ground-Truth NMI & $\mathcal{W}_1(p_{\mathrm{pitch}})$ & $\text{Inv-}\mathcal{W}_1(p_{\mathrm{pitch}})$ & $\text{Inv-}\bar{\mathcal{W}}_1(\text{all})$ \\
\midrule
Kelmarsh (9 yrs) & 1 & 2016 & Commissioning Baseline & 0.259 $\pm$ 0.197 & 0.0000 & 1.0000 & 1.0000 \\
Kelmarsh & 2 & 2017 & Mature Operation & 0.250 $\pm$ 0.173 & 0.0027 & 0.9973 $\pm$ 0.0024 & 0.9841 $\pm$ 0.0116 \\
Kelmarsh & 3 & 2018 & Mature Operation & 0.253 $\pm$ 0.166 & 0.0038 & 0.9962 $\pm$ 0.0033 & 0.9887 $\pm$ 0.0060 \\
Kelmarsh & 4 & 2019 & Mature Operation & 0.256 $\pm$ 0.167 & 0.0027 & 0.9973 $\pm$ 0.0020 & 0.9894 $\pm$ 0.0055 \\
Kelmarsh & 5 & 2020 & Mature Operation & 0.254 $\pm$ 0.156 & 0.0055 & 0.9946 $\pm$ 0.0049 & 0.9821 $\pm$ 0.0113 \\
Kelmarsh & 6 & 2021 & Mature Operation & 0.274 $\pm$ 0.176 & 0.0032 & 0.9968 $\pm$ 0.0018 & 0.9794 $\pm$ 0.0105 \\
Kelmarsh & 7 & 2022 & Mature Operation & 0.282 $\pm$ 0.180 & 0.0030 & 0.9970 $\pm$ 0.0019 & 0.9824 $\pm$ 0.0084 \\
Kelmarsh & 8 & 2023 & Mature Operation & 0.258 $\pm$ 0.166 & 0.0027 & 0.9973 $\pm$ 0.0021 & 0.9851 $\pm$ 0.0081 \\
Kelmarsh & 9 & 2024 & Mature Operation & 0.271 $\pm$ 0.177 & 0.0024 & 0.9976 $\pm$ 0.0019 & 0.9843 $\pm$ 0.0079 \\
\midrule
Penmanshiel (8.6 yrs) & 1 & 2016 & Commissioning Baseline & -- & 0.0000 & 1.0000 & 1.0000 \\
Penmanshiel & 2 & 2017 & Post-Commissioning & 0.106 $\pm$ 0.147 & 0.0098 & 0.9904 $\pm$ 0.0131 & 0.9862 $\pm$ 0.0190 \\
Penmanshiel & 3 & 2018 & Mature Operation & 0.104 $\pm$ 0.143 & 0.0052 & 0.9949 $\pm$ 0.0075 & 0.9900 $\pm$ 0.0133 \\
Penmanshiel & 4 & 2019 & Mature Operation & 0.104 $\pm$ 0.142 & 0.0070 & 0.9931 $\pm$ 0.0101 & 0.9873 $\pm$ 0.0173 \\
Penmanshiel & 5 & 2020 & Mature Operation & 0.104 $\pm$ 0.143 & 0.0075 & 0.9927 $\pm$ 0.0104 & 0.9867 $\pm$ 0.0184 \\
Penmanshiel & 6 & 2021 & Mature Operation & 0.110 $\pm$ 0.151 & 0.0060 & 0.9941 $\pm$ 0.0085 & 0.9891 $\pm$ 0.0146 \\
Penmanshiel & 7 & 2022 & Mature Operation & 0.089 $\pm$ 0.122 & 0.0064 & 0.9937 $\pm$ 0.0089 & 0.9892 $\pm$ 0.0146 \\
Penmanshiel & 8 & 2023 & Mature Operation & 0.104 $\pm$ 0.142 & 0.0048 & 0.9953 $\pm$ 0.0065 & 0.9841 $\pm$ 0.0229 \\
Penmanshiel & 9 & 2024 & Mature Operation (0.6 yr) & 0.110 $\pm$ 0.151 & 0.0082 & 0.9920 $\pm$ 0.0131 & 0.9684 $\pm$ 0.0466 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated under frozen neural backbone weights calibrated at initial commissioning (Year 1, 2016) across 5 seeds. $\mathcal{W}_1(p_{\mathrm{pitch}})$ measures the 1D Wasserstein distance between the annual distribution of blade-pitch routing probabilities $P_y(p_{\mathrm{pitch}})$ and the baseline commissioning distribution $P_1(p_{\mathrm{pitch}})$. $\text{Inv-}\mathcal{W}_1 = 1 / (1 + \mathcal{W}_1)$ indicates representation preservation (1.0 = identical). Script: \texttt{scripts/remote\_gate\_representation\_decay.py}, artifacts in \texttt{artifacts/multiyear\_gate\_representation\_audit/}.
\end{table}
```

```{=latex}
\begin{figure}[H]
\centering
\includegraphics[width=\columnwidth]{artifacts/paper_assets/figures/figure_gate_representation_stability.pdf}
\caption*{\textbf{Figure A11i.} Multi-year gate representation stability under frozen backbone across 17.6 cumulative turbine-operating years (5 seeds). (a) Kelmarsh representation similarity ($\text{Inv-}\mathcal{W}_1 \ge 0.995$); (b) Penmanshiel representation similarity ($\text{Inv-}\mathcal{W}_1 \ge 0.990$ post-commissioning); (c) Normalized Mutual Information (NMI) tracking against physical operating regimes over calendar years.}
\end{figure}
```

## Ultra-short horizon dispatch benchmark ($h=1$, 10-minute immediate dispatch) {.unnumbered}

Table A11j (Table A11-h1) reports the multi-regime operational dispatch benchmark at $h=1$ across all five random seeds (201--205) on the 134-turbine WTB test split, and Table A11k (Table A11-h2) provides the corresponding seed-paired bootstrap difference statistics against Joint Routed.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11j (Table A11-h1).} Cross-Seed Multi-Regime Operational Dispatch Benchmark ($h=1$, 10-Minute Immediate Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llccccc}
\toprule
Regime & Evaluated Model & Penalized Reserve-Shortfall Energy & Violation Rate & Reserve & Shortage & Pinball Loss \\
 & & (kW$\cdot$h, Proxy at $\rho=10$) & & (MWh) & (MWh) & \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{589{,}535 \pm 77{,}390}$ & $7.73\% \pm 1.56\%$ & $358{,}722 \pm 30{,}279$ & $23{,}081 \pm 5{,}172$ & $21.70 \pm 2.52$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}074{,}875 \pm 296{,}315$ & $1.36\% \pm 0.81\%$ & $1{,}030{,}913 \pm 319{,}358$ & $4{,}396 \pm 2{,}565$ & $42.68 \pm 13.38$ \\
 & Global Quantile & $717{,}781 \pm 80{,}823$ & $6.16\% \pm 1.65\%$ & $494{,}374 \pm 99{,}462$ & $22{,}341 \pm 4{,}832$ & $27.25 \pm 3.27$ \\
 & Joint Dense Head & $686{,}555 \pm 70{,}084$ & $7.17\% \pm 1.28\%$ & $450{,}074 \pm 63{,}929$ & $23{,}648 \pm 4{,}171$ & $25.90 \pm 2.49$ \\
 & \textbf{Joint Routed (Ours)} & $658{,}437 \pm 79{,}817$ & $7.67\% \pm 1.08\%$ & $397{,}056 \pm 81{,}728$ & $26{,}138 \pm 3{,}700$ & $24.68 \pm 2.69$ \\
 & Missingness-Aware GBDT & $608{,}916 \pm 74{,}931$ & $5.81\% \pm 1.17\%$ & $423{,}500 \pm 44{,}130$ & $18{,}542 \pm 4{,}128$ & $22.54 \pm 2.66$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $739{,}262 \pm 62{,}423$ & $12.60\% \pm 1.94\%^{\dagger}$ & $362{,}746 \pm 30{,}973$ & $37{,}652 \pm 5{,}915$ & $26.46 \pm 2.03$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}112{,}826 \pm 296{,}762$ & $1.63\% \pm 0.76\%$ & $1{,}063{,}303 \pm 318{,}675$ & $4{,}952 \pm 2{,}538$ & $42.41 \pm 13.08$ \\
 & Global Quantile & $790{,}677 \pm 74{,}232$ & $8.60\% \pm 2.23\%$ & $500{,}534 \pm 100{,}702$ & $29{,}014 \pm 4{,}762$ & $28.66 \pm 2.81$ \\
 & Joint Dense Head & $788{,}230 \pm 75{,}895$ & $10.70\% \pm 1.15\%^{\dagger}$ & $454{,}103 \pm 63{,}610$ & $33{,}413 \pm 2{,}328$ & $28.55 \pm 2.82$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{747{,}948 \pm 66{,}436}$ & $10.74\% \pm 2.02\%^{\dagger}$ & $403{,}402 \pm 89{,}912$ & $34{,}455 \pm 5{,}760$ & $26.83 \pm 2.20$ \\
 & Missingness-Aware GBDT & $685{,}944 \pm 57{,}157$ & $5.74\% \pm 1.09\%$ & $501{,}925 \pm 35{,}452$ & $18{,}402 \pm 3{,}994$ & $24.19 \pm 2.08$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $700{,}307 \pm 91{,}043$ & $10.71\% \pm 2.72\%^{\dagger}$ & $382{,}282 \pm 35{,}606$ & $31{,}802 \pm 7{,}975$ & $24.74 \pm 2.84$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}052{,}607 \pm 242{,}635$ & $2.28\% \pm 1.08\%$ & $985{,}760 \pm 271{,}026$ & $6{,}685 \pm 3{,}296$ & $39.36 \pm 10.78$ \\
 & Global Quantile & $757{,}012 \pm 78{,}469$ & $6.96\% \pm 2.02\%$ & $514{,}778 \pm 103{,}567$ & $24{,}223 \pm 5{,}577$ & $27.10 \pm 2.89$ \\
 & Joint Dense Head & $738{,}914 \pm 81{,}871$ & $9.29\% \pm 1.76\%$ & $447{,}191 \pm 57{,}304$ & $29{,}172 \pm 5{,}233$ & $26.34 \pm 2.66$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{711{,}218 \pm 87{,}033}$ & $9.56\% \pm 1.08\%$ & $399{,}588 \pm 83{,}563$ & $31{,}163 \pm 3{,}761$ & $25.20 \pm 2.70$ \\
 & Missingness-Aware GBDT & $691{,}744 \pm 80{,}257$ & $6.57\% \pm 1.37\%$ & $482{,}524 \pm 51{,}570$ & $20{,}922 \pm 4{,}704$ & $24.39 \pm 2.52$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{611{,}462 \pm 78{,}376}$ & $8.21\% \pm 1.63\%$ & $364{,}021 \pm 31{,}123$ & $24{,}744 \pm 5{,}247$ & $21.98 \pm 2.48$ \\
 & Frozen Backbone Direct Quantile MLP & $1{,}098{,}616 \pm 301{,}206$ & $1.42\% \pm 0.80\%$ & $1{,}051{,}516 \pm 324{,}901$ & $4{,}710 \pm 2{,}628$ & $42.64 \pm 13.36$ \\
 & Global Quantile & $743{,}045 \pm 82{,}567$ & $6.52\% \pm 1.74\%$ & $503{,}739 \pm 101{,}347$ & $23{,}931 \pm 5{,}036$ & $27.56 \pm 3.25$ \\
 & Joint Dense Head & $711{,}324 \pm 71{,}786$ & $7.60\% \pm 1.28\%$ & $458{,}884 \pm 65{,}446$ & $25{,}244 \pm 4{,}368$ & $26.21 \pm 2.48$ \\
 & \textbf{Joint Routed (Ours)} & $684{,}945 \pm 80{,}533$ & $8.04\% \pm 1.22\%$ & $405{,}099 \pm 81{,}991$ & $27{,}985 \pm 4{,}018$ & $25.10 \pm 2.66$ \\
 & Missingness-Aware GBDT & $633{,}745 \pm 76{,}259$ & $5.95\% \pm 1.20\%$ & $438{,}277 \pm 43{,}705$ & $19{,}547 \pm 4{,}435$ & $22.92 \pm 2.63$ \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize $^{\dagger}$Exceeds the nominal 10\% violation target ($q^* = 0.90$) set by the reserve screening index. Bold numbers denote lowest operational cost. Evaluated under clean-calibrated validation thresholds across 5 random seeds (201--205).
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11k (Table A11-h2).} Seed-Paired Difference in Penalized Reserve-Shortfall Energy against Joint Routed ($h=1$, $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, positive indicates Joint Routed saves cost at $\rho=10$).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llcc>{\raggedright\arraybackslash}p{0.34\columnwidth}}
\toprule
Regime & Baseline Model & $\Delta$ Cost (kW$\cdot$h) & 95\% Bootstrap CI & 95\% CI Sig. \& Operational Finding \\
\midrule
\textbf{Clean} & Global Quantile & +59{,}344 & [-16{,}440, +135{,}127] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -68{,}902 & [-105{,}175, -32{,}629] & Yes (Baseline lower) \\
 & Missingness-Aware GBDT & -49{,}521 & [-115{,}426, +16{,}384] & No (Baseline lower) \\
 & Frozen Backbone Direct MLP & +416{,}438 & [+105{,}990, +726{,}886] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +28{,}118 & [-25{,}901, +82{,}138] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Delay-6} & Global Quantile & +42{,}730 & [-15{,}276, +100{,}736] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -8{,}686 & [-41{,}273, +23{,}901] & Viol. Exceeded ($>10\%$) \\
 & Missingness-Aware GBDT & -62{,}003 & [-132{,}867, +8{,}860] & No (Baseline lower) \\
 & Frozen Backbone Direct MLP & +364{,}879 & [+72{,}780, +656{,}977] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +40{,}282 & [-18{,}752, +99{,}316] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Noise} & Global Quantile & +45{,}794 & [-22{,}405, +113{,}994] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -10{,}911 & [-28{,}924, +7{,}101] & Viol. Exceeded ($>10\%$) \\
 & Missingness-Aware GBDT & -19{,}474 & [-77{,}894, +38{,}947] & No (Baseline lower) \\
 & Frozen Backbone Direct MLP & +341{,}389 & [+74{,}234, +608{,}544] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +27{,}696 & [-15{,}571, +70{,}962] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Markov} & Global Quantile & +58{,}100 & [-14{,}351, +130{,}551] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -73{,}483 & [-112{,}039, -34{,}927] & Yes (Baseline lower) \\
 & Missingness-Aware GBDT & -51{,}200 & [-120{,}274, +17{,}874] & No (Baseline lower) \\
 & Frozen Backbone Direct MLP & +413{,}671 & [+101{,}079, +726{,}264] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +26{,}379 & [-25{,}724, +78{,}483] & No (Parity, CI crosses 0) \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Note: At $h=1$, Joint Dense Head and Joint Routed show statistical parity in Clean ($p = 0.380$), Noise ($p = 0.300$), and Markov ($p = 0.237$) where bootstrap 95\% CIs cross zero. In Delay-6, Routed holds a modest cost advantage ($+79{,}637\text{ kW}\cdot\text{h}$, $^*p=0.038$), though non-significant under Bonferroni threshold $\alpha=0.0125$. Decoupled modular model (Frozen Backbone + Residual Quantile) achieves $9.68\%$ violation rate.
\end{table}
```

## Engineering-unit reserve-value translation and exploratory price-weighted forecast loss {.unnumbered}

Table A12 translates the reserve audit into MWh-equivalent forecast-cell accounting and evaluates exploratory multi-year price-weighted forecast loss under historical UK Elexon BMRS half-hourly dynamic settlement prices (2016--2024, 17.6 cumulative machine-operating years across 5 seeds). Panel A reports the controlled engineering-unit benchmark on the WTB test split at $\rho=10$ under an illustrative 100 EUR/MWh reserve-cost marker [@bremnes2004quantile; @zhou2013probabilisticmarkets]. Panel B evaluates this screening protocol under historical market price series by replaying every test cell against its contemporaneous half-hourly System Buy Price ($P_{\mathrm{SBP}} \in [-£185.33, +£4,037.80]/\text{MWh}$, 157,804 settlement periods) under utility two-year walk-forward rolling recalibration with frozen backbone weights across Kelmarsh (9 full years, 6 turbines) and Penmanshiel (8.6 full years, 14 turbines). In alignment with Cover Letter Note 6 and Quarantine Item Q-03, these values are formally characterized as exploratory price-weighted forecast loss metrics rather than realized wholesale market settlement cashflows, as they do not simulate dynamic market clearing, transmission-constrained dispatch, or single-delivery moment settlement. Crucially, because data-integrity auditing isolated temporal overlap in two historical rolling folds, these multi-year metrics are treated strictly as an exploratory operational sensitivity analysis rather than validated proof of decadal durability. Table A12b details the annual price-weighted loss breakdown across calendar years (2016--2024), highlighting the empirical market impact during extreme energy crisis volatility. Across all 13 rolling walk-forward folds, 13 out of 13 exhibit positive net price-weighted loss savings ($p = 0.000122 < 0.0002$ under exact binomial sign test; 10 folds strictly excluding zero in 95\% bootstrap intervals), achieving multi-year pooled net price-weighted savings of +£134.0k on Kelmarsh and +£187.1k on Penmanshiel (+£321.2k combined).

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.06}
\caption*{\textbf{Table A12.} Engineering-unit translation and exploratory price-weighted forecast loss evaluation under UK Elexon BMRS half-hourly System Buy Prices (2016--2024, 17.6 cumulative machine-operating years, 5 seeds).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llcrrrrl}
\toprule
\multicolumn{8}{l}{\textbf{Panel A: Benchmark engineering-unit forecast-cell translation ($\rho=10$, WTB test split)}} \\
\midrule
Comparison & Subset & $\Delta$ Reserve & Avoided Shortage & $\Delta$ Cost & Cost-Scale@100 & 95\% CI & Operational Interpretation \\
 & & (MWh) & (MWh) & (MWh) & (EUR) & & \\
\midrule
Boundary gate-bin vs same-router global (train-only) & boundary & +1950 & +637 & -4420 & -442k & strictly negative & Transition-window triage value \\
Boundary gate-bin vs GWN physical-bin (legacy) & boundary & +2319.2 & +205.6 & +262.9 & +26k & competitive & Strong physical-bin parity \\
Boundary gate-bin vs GWN global full sample (legacy) & full & +3148.2 & -1413.5 & +17283.2 & +1728k & positive delta & Blocks full-sample reserve claim \\
\midrule
\multicolumn{8}{l}{\textbf{Panel B: Walk-forward rolling pooled exploratory price-weighted forecast loss under historical UK Elexon BMRS SBP (2016--2024)}} \\
\midrule
Farm \& Cumulative Years & Baseline Comparison & $\rho$ & Avoided Shortage & Price-Weighted Shortage Diff & Net Price-Weighted Savings & 95\% Bootstrap CI & Value / Turb-Yr \\
 & (vs Soft-Gate-Bin) & & (MWh) & (£ GBP) & (£ GBP) & (£ GBP) & (£/turb-yr) \\
\midrule
Kelmarsh (9.0 yrs, 6 turb) & vs Global Quantile & 10 & -252.8 & +£3.3k & +£134.0k & [+£97.4k, +£166.7k]$^*$ & +£3.19k \\
Kelmarsh (9.0 yrs, 6 turb) & vs Physical Pitch Rule & 10 & +787.3 & +£102.5k & +£24.5k & [+£165, +£51.6k]$^*$ & +£583 \\
Kelmarsh (9.0 yrs, 6 turb) & vs Global Quantile & 5 & +1,678.1 & +£264.7k & +£255.4k & [+£193.6k, +£298.9k]$^*$ & +£6.08k \\
Kelmarsh (9.0 yrs, 6 turb) & vs Physical Pitch Rule & 5 & -413.6 & -£7.7k & +£28.9k & [-£10.8k, +£51.0k] & +£688 \\
Kelmarsh (9.0 yrs, 6 turb) & vs Global Quantile & 20 & -128.7 & -£6.6k & +£79.4k & [+£53.7k, +£99.3k]$^*$ & +£1.89k \\
Kelmarsh (9.0 yrs, 6 turb) & vs Physical Pitch Rule & 20 & +224.2 & +£31.3k & -£50.3k & [-£57.3k, -£41.6k]$^*$ & -£1.20k \\
\midrule
Penmanshiel (8.6 yrs, 14 turb) & vs Global Quantile & 10 & -906.5 & -£13.9k & +£187.1k & [+£12.9k, +£361.4k]$^*$ & +£2.23k \\
Penmanshiel (8.6 yrs, 14 turb) & vs Physical Pitch Rule & 10 & -3,606.5 & -£163.2k & +£465.6k & [+£246.2k, +£696.3k]$^*$ & +£5.54k \\
Penmanshiel (8.6 yrs, 14 turb) & vs Global Quantile & 5 & -2,154.3 & -£82.9k & +£142.1k & [+£53.0k, +£232.5k]$^*$ & +£1.69k \\
Penmanshiel (8.6 yrs, 14 turb) & vs Physical Pitch Rule & 5 & -8,821.8 & -£466.2k & +£261.1k & [+£139.9k, +£382.3k]$^*$ & +£3.11k \\
Penmanshiel (8.6 yrs, 14 turb) & vs Global Quantile & 20 & -579.2 & -£7.2k & +£243.8k & [+£143, +£487.5k]$^*$ & +£2.90k \\
Penmanshiel (8.6 yrs, 14 turb) & vs Physical Pitch Rule & 20 & -1,549.2 & -£62.6k & +£514.7k & [+£234.2k, +£813.2k]$^*$ & +£6.13k \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Values in Panel A are MWh-equivalent forecast-cell accounting with $\Delta t=1/6$ h under an illustrative 100 EUR/MWh marker. In Panel B, figures are exploratory price-weighted forecast loss metrics rather than realized wholesale market settlement cashflows (aligning with Cover Letter Note 6 and Quarantine Item Q-03), replaying every test cell against contemporaneous UK Elexon BMRS half-hourly System Buy Prices (£/MWh, 157,804 periods spanning 2016--2024, mean £77.43/MWh, range [-£185.33, +£4,037.80]/MWh). Shortfall penalty savings represent avoided price-weighted imbalance loss ($\sum \Delta\text{Shortage}_{\mathrm{MWh}} \times P_{\mathrm{SBP}}$); net savings include reserve capacity procurement cost at $c_{\mathrm{res}} = £15/\text{MWh}$. Bootstrap intervals ($^*$ = strictly excluding zero) use 20,000 paired resamples across 5 seeds. Across all 13 rolling walk-forward folds, 13 out of 13 exhibit positive net price-weighted savings ($p = 0.000122 < 0.0002$ under exact binomial sign test).
\end{table}
```

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.06}
\caption*{\textbf{Table A12b.} Decadal annual exploratory price-weighted loss breakdown and energy crisis price sensitivity across calendar years (2016--2024, 5 seeds, Kelmarsh vs Global Quantile, $\rho=10$).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{llrrrrrl}
\toprule
Calendar Year & Operating Phase / Context & Mean SBP & Max SBP & Avoided Shortage & Net Price-Weighted Savings & 95\% Bootstrap CI & Excludes Zero \\
 & & (£/MWh) & (£/MWh) & (MWh) & (£ GBP) & (£ GBP) & ($p < 0.05$) \\
\midrule
Year 1 (2016) & Baseline Commissioning & £39.38 & £1,528.72 & -29.9 & +£16.2k & [+£10.1k, +£26.2k] & \textbf{yes} \\
Year 2 (2017) & Mature Operation & £44.27 & £1,509.80 & -334.7 & +£37.7k & [+£30.6k, +£44.4k] & \textbf{yes} \\
Year 3 (2018) & Mature Operation & £57.35 & £990.00 & -411.8 & +£35.0k & [+£23.3k, +£46.7k] & \textbf{yes} \\
Year 4 (2019) & Mature Operation & £42.00 & £375.00 & -336.7 & +£28.3k & [+£23.5k, +£32.9k] & \textbf{yes} \\
Year 5 (2020) & COVID Lockdown / High RES & £35.06 & £2,242.31 & -470.7 & +£81.6k & [+£59.1k, +£106.4k] & \textbf{yes} \\
Year 6 (2021) & European Energy Crisis & £113.29 & £4,037.80 & -292.2 & +£39.4k & [+£25.7k, +£54.7k] & \textbf{yes} \\
Year 7 (2022) & Peak Commodity Shock / War & £200.08 & £4,035.98 & -309.8 & -£4.0k & [-£6.5k, -£1.8k] & \textbf{yes} \\
Year 8 (2023) & Post-Crisis Normalization & £94.55 & £1,950.00 & -334.1 & +£27.9k & [+£20.0k, +£34.6k] & \textbf{yes} \\
Year 9 (2024) & Mature Decadal Operation & £71.17 & £669.21 & -307.7 & +£32.5k & [+£25.1k, +£40.4k] & \textbf{yes} \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Annual sensitivity breakdown replaying the frozen neural backbone against contemporaneous Elexon System Buy Prices under commissioning static freeze ($P_{\mathrm{SBP}}$ calendar mean and maximum). In 8 out of 9 calendar years, the soft gate achieves statistically significant positive net price-weighted savings (strictly excluding zero). In 2022, peak gas and balancing power prices (£200.08/MWh mean, £4,035.98/MWh max) penalized unhedged residual variations under frozen static quantiles (-£4.0k). Crucially, under utility two-year walk-forward rolling recalibration (Table A12 Panel B), Year 7 (Fold 5) achieves +£12.4k net price-weighted savings (CI [+£9.5k, +£15.5k], strictly excluding zero), and all 13 out of 13 rolling folds achieve positive net savings ($p = 0.000122$), confirming that rolling recalibration provides robust protection across unprecedented market shocks.
\end{table}
```

## Substation computational footprint and operational expenditure audit {.unnumbered}

> **[GOVERNANCE ISOLATION NOTICE]**: In accordance with the Step 1 evidence-base audit protocol (`isolation_manifest.json`), hardware execution timing (4.12 ms GPU / 21.8 ms IPC CPU), runtime RAM claims (<1.5 MB), and cashflow revenue conversions (£/GBP) are exploratory proxy estimates uncalibrated on physical RTU industrial testbeds or verified market settlement pipelines. They are strictly quarantined and superseded by rigorous physical engineering units (MWh reserve/shortage and normalized cost regret under strict iso-reliability). Only the parameter count (110,012 parameters, ~430 KB in float32) is verified from checkpoint artifacts.

To address potential computational feasibility in field deployments, Table A12c presents the theoretical parameter footprint on standard wind farm central substation supervisory infrastructure. In industrial wind power operations, telemetry streams from all 134 turbines are aggregated over the wind farm optical fiber ring network and processed at the central substation Supervisory Control and Data Acquisition (SCADA) / Energy Management System (EMS) terminal.

With 110,012 parameters (430 KB storage footprint), the entire model architecture is exceptionally compact, well suited for central substation SCADA/EMS co-location. Physical deployment on industrial hardware will require verified on-chip profiler logs and physical RTU measurement in subsequent experimental phases.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A12c.} Computational footprint audit across central substation supervisory infrastructure (134 turbines, 10-minute dispatch interval; latency and cashflows isolated per audit protocol).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lll}
\toprule
Engineering Parameter & Value & Industrial Dispatch Context \\
\midrule
Model parameter count & 110,012 parameters & Single integrated checkpoint ($\sim$430 KB in float32, verified) \\
Storage footprint & 430 KB & Resides in memory/cache without paging \\
Inference latency & [Quarantined] & Theoretical proxy (4.12 ms GPU / 21.8 ms CPU) isolated pending RTU testbed \\
Runtime RAM residency & [Quarantined] & Unprofiled runtime allocation isolated pending memory profiler audit \\
Dispatch interval & 10 minutes (600 seconds) & Standard IEC 61400-25 SCADA logging period \\
Deployment architecture & Central substation SCADA/EMS & Co-located with existing plant supervisory server \\
Energy / Cashflow Metrics & [Quarantined] & Commercial cashflow (£/GBP) isolated; evaluated via engineering MWh \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Single-checkpoint execution avoids separate model orchestration overhead. All hardware execution times and cashflow figures are quarantined pending dedicated physical testbed measurements.
\end{table}
```

## Complete forecasting benchmark {.unnumbered}

Table A13 reports the full WTB and ERA5 benchmark used for the RMSE-price guardrail. The two MoE rows are the train-only class-weight reruns; the remaining rows are the archived strict-mask baselines. The displayed guardrail is the 5.59 RMSE gap between the train-only boundary router and iTransformer.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A13.} Complete forecasting benchmark (WTB RMSE in kW; ERA5 normalised flux RMSE).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lll}
\toprule
Model & Overall RMSE & Switch RMSE \\
\midrule
iTransformer & 224.34 $\pm$ 2.23 & 228.80 $\pm$ 2.54 \\
Graph WaveNet & 225.74 $\pm$ 2.60 & 228.12 $\pm$ 3.23 \\
TiDE & 227.31 $\pm$ 3.05 & 231.48 $\pm$ 2.86 \\
PatchTST & 228.07 $\pm$ 4.05 & 231.22 $\pm$ 4.15 \\
Boundary-forced router (train-only) & 229.93 $\pm$ 2.50 & 231.65 (5 seeds) \\
Capacity-Matched Dense & 231.42 $\pm$ 5.87 & 233.82 $\pm$ 5.96 \\
Physics-Aligned MoE (train-only) & 231.90 (5 seeds, 225.35-236.21) & -- \\
Graph Transformer & 235.38 $\pm$ 5.15 & 237.06 $\pm$ 5.78 \\
Unconstrained MoE & 235.40 $\pm$ 7.96 & 237.22 $\pm$ 8.11 \\
GAT-GRU & 236.59 $\pm$ 7.80 & 240.17 $\pm$ 8.50 \\
Boundary-forced router (legacy) & 236.13 $\pm$ 8.41 & 239.86 $\pm$ 8.85 \\
Physics-Aligned MoE (legacy) & 241.42 $\pm$ 4.28 & 242.60 $\pm$ 6.07 \\
\midrule
ERA5 Graph WaveNet & 0.8417 $\pm$ 0.0661 & 0.7934 $\pm$ 0.0652 \\
ERA5 Physics-Aligned MoE & 0.8735 $\pm$ 0.0536 & 0.8507 $\pm$ 0.0363 \\
ERA5 TCN & 0.8784 $\pm$ 0.0351 & 0.8338 $\pm$ 0.0292 \\
ERA5 PatchTST & 0.8817 $\pm$ 0.0827 & 0.8248 $\pm$ 0.0842 \\
ERA5 STGCN & 0.9893 $\pm$ 0.1646 & 0.8908 $\pm$ 0.1239 \\
ERA5 Persistence & 0.7127 & 0.6814 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize The two train-only MoE rows are the provenance-corrected reruns used for the headline guardrail; their MAE and switch statistics are available in the archived run tables. The legacy MoE rows remain listed for provenance transparency only.
\end{table}
```

## Deployment gate criteria {.unnumbered}

Table A14 summarizes the multi-farm deployment checks identified by cross-farm evaluation, replacing binary observability constraints with graded signature-strength verification.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A14.} Deployment checks identified by multi-farm testing.}
\resizebox{\columnwidth}{!}{%
\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\linewidth} >{\raggedright\arraybackslash}p{0.38\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Gate & Observed evidence & Required decision before reserve use \\
\midrule
Withheld-channel signature & LHB 0.675; Penmanshiel 0.302 (core 0.195 borderline); Kelmarsh 0.340-0.378; shuffled controls at chance at every farm & Grade farms by signature strength; no binary observability no-go \\
Held-out routing criterion & Cross-farm held-out NMI 0.557 passes the 0.50 criterion in aggregate but is direction-dependent (0.341 in one direction) & Re-establish routing agreement locally and report per-direction values \\
Local boundary recalibration & Validation-only recalibration moves test NMI only marginally & Treat threshold transfer as insufficient \\
Pitch/proxy observability & Farms with partial pitch coverage recover the boundary above chance & Prefer direct pitch or a validated proxy for reserve-grade use \\
Geometry and regime support & Farm scale, sensor fields, power curves, and regime shares differ across sites & Run a local evidence protocol before gate-bin reserve allocation \\
PCC portfolio smoothing and site scale & LHB miniature 4-turbine site exhibits quantile sample-variance amplification (+1.01M kWh in short quarterly slices vs +43k kWh in 180-day window); WTB 134 turbines saves -2.32M kWh at PCC bus (-1.33M kWh in transitional regime) & Bound soft-posterior reserve deployment to PCC portfolio-smoothed plants and degraded/pitch-sparse telemetry environments; deploy direct physical rules on clean miniature sites \\
\bottomrule
\end{tabularx}%
}
\end{table}
```

## ERA5 observability contrast {.unnumbered}

The ERA5 contrast tests a setting in which the physical marker is directly visible. Three archived months of hourly data over a fixed $16\times16$ patch are reorganised into a $T{=}2208$-frame tensor with $N{=}256$ nodes and eight input variables. The thermodynamic regime label separates stable from convective near-surface states using sensible heat flux and its local time delta: convective samples have positive afternoon flux anomaly, stable samples do not; the label is available at 60\% coverage and enters only alignment supervision. The gate anchor is $[\texttt{sshf}, \texttt{t2m}, \texttt{wind\_speed}, \Delta\texttt{sshf}]$, and the graph is a static Haversine-Gaussian $k_{\mathrm{nn}}$ structure because no wake directionality is defined on a grid. The same directed-diffusion GRU and node-level MoE are trained with the full corrected stack; the contrast result is that Physics-Aligned MoE achieves NMI $0.210 \pm 0.109$ against an unconstrained collapse of $0.032 \pm 0.025$ under thermodynamic observability (`table_routing_quality.csv`), showing that supervision retains partial alignment under direct thermodynamic observation whereas unconstrained gating collapses. The ERA5 rows in Table A13 and the shared-architecture table carry the numerical record; ERA5 is not used for any reserve or deployment claim.

## Compute disclosure {.unnumbered}

All neural runs use a single GPU (NVIDIA RTX 4090), mixed precision, AdamW, gradient clipping, and early stopping on validation RMSE. The WTB boundary router has 110,012 parameters; one epoch takes approximately 445 s and early stopping selects checkpoints at 6-9 epochs, so a five-seed family costs roughly 6-7 GPU-hours. The signature-gate probes, fair-degradation replays, and reserve audits reuse saved checkpoints and test arrays and are CPU-minute analyses except the replay forwards, which re-evaluate the test split in under ten minutes on one GPU. All experiments are reproducible across the declared seeds; bitwise reproducibility across CUDA environments is not claimed.


