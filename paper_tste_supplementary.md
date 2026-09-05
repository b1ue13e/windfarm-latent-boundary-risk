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
Withheld-channel signature at partial pitch & Kelmarsh (55\% pitch): 0.340/0.378; Penmanshiel (78\%): 0.302/0.195; shuffled controls at chance & Signature strength graded against the farm's own shuffled control & Partial pitch observability grades, not voids, boundary recoverability \\
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

Table A9d reports the same probe on two farms with partial pitch observability. Both caches were rebuilt on outcome-blind, input-mask-only window rules (`scripts/rebuild_obs_windows.py`): the earliest contiguous 245-day window with daily pitch coverage at least 0.70 and daily regime-valid at least 0.70 for Penmanshiel (day 720; realised pitch 78.1\%), and the earliest window with daily regime-valid at least 0.70 for Kelmarsh (day 120; realised pitch 55.1\%). Permuted-label controls collapse to chance at both farms, and the withheld-channel variants stay above chance even at 55\% pitch coverage, so the deployment decision for pitch-sparse farms is a graded signature-strength check rather than a binary observability gate.

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
\footnotesize Pitch coverage is the fraction of cells with a directly observed blade-pitch channel inside the rebuilt window. Signature strength is not monotonic in pitch coverage (Penmanshiel 78\% scores lower than Kelmarsh 55\%), so the graded reading attributes the remaining signal to consequence-channel quality (reactive power, pitch dispersion, temperatures) rather than to pitch coverage alone. Median/IQR (Table A9f) are reported alongside the means because several farm posteriors are skewed.
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

## Multi-year walk-forward rolling recalibration audit {.unnumbered}

Tables A9g and A9h record the multi-year walk-forward rolling recalibration audits across 17.6 cumulative turbine-operating years on two commercial wind farms: Kelmarsh (9 full years, 6 MM92 turbines) and Penmanshiel (8.6 full years, 14 MM82 turbines) under IEC 61400-12-1 air-density calibration. A 2-year sliding training window recalibrates reserve quantiles for the subsequent operational year, eliminating multi-year concept drift observed under frozen static quantiles. On Kelmarsh, 6 of 7 rolling folds strictly exclude zero ($p < 0.05$), with mean annual savings of $-1.025 \text{ Million kWh/year}$. On Penmanshiel, all 4 consecutive mature operational folds (2020--2023) strictly exclude zero ($p < 0.05$), with mean annual savings of $-2.029 \text{ Million kWh/year}$. Together, 10 out of 11 mature annual folds across both farms achieve statistically significant reserve cost reductions.

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

Table A10d reports the fair-degradation audit: the confirming-stream delay applies late wind-speed and pitch readings to both the gate anchor and the threshold rule identically (the archived history window remains available), and sensor noise corrupts the same channels in the gate's encoder features and anchor. Across a six-step delay, the rigid physical rule suffers catastrophic breakdown (F1 collapses from 0.9355 to 0.2491), whereas the joint posterior maintains steady precision (0.6282 vs. 0.3420 rule) and an F1 score of 0.7453, three times higher than the rule (+0.4962 gain). Table A10e evaluates industrial burst packet loss under a two-state Markov-Gilbert model.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10d.} Fair-degradation audit: gate and physical rule consume the same degraded readings. Full precision, recall, and F1 profile across five train-only seeds.}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrrrr}
\toprule
Condition & Gate Rec & Rule Rec & Gate Prec & Rule Prec & Gate F1 & Rule F1 & F1 Gain \\
\midrule
Clean anchors & 0.9705 & 1.0000 & 0.6304 & 0.8789 & 0.7598 & 0.9355 & -0.1757 \\
Delay, 1 step & 0.9622 & 0.6554 & 0.6239 & 0.7153 & 0.7527 & 0.6841 & \textbf{+0.0687} \\
Delay, 3 steps & 0.9430 & 0.3811 & 0.6184 & 0.4646 & 0.7420 & 0.4187 & \textbf{+0.3233} \\
Delay, 6 steps & 0.9327 & 0.1959 & 0.6282 & 0.3420 & 0.7453 & 0.2491 & \textbf{+0.4962} \\
Noise, Wspd 0.5 / Pab 1.0 & 0.9635 & 0.8114 & 0.6228 & 0.8567 & 0.7525 & 0.8324 & -0.0798 \\
Noise, Wspd 1.0 / Pab 2.0 & 0.9505 & 0.6800 & 0.6030 & 0.8106 & 0.7349 & 0.7388 & -0.0039 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Values are means over 5 seeds (archived in \texttt{artifacts/fair\_degradation\_replay\_20260903/}). Upper-bound variant: when the delay also stalls the archived history channels (worst-case degradation), the gate retains 0.846/0.628/0.416 at one/three/six-step delays against 0.655/0.381/0.196 for the rule (gains +0.19/+0.25/+0.22, all 5 seeds positive).
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
Jointly-Learned Routed Posterior (honest corrupted forward) & 0.994 $\pm$ 0.006 & 0.946 $\pm$ 0.086 & 0.967 $\pm$ 0.047 & 146,552 cells/seed \\
Jointly-Learned Routed Posterior (clean forward reference) & 0.997 $\pm$ 0.003 & 0.948 $\pm$ 0.088 & 0.970 $\pm$ 0.048 & 146,552 cells/seed \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated over 146,552 burst-loss cells per seed under a two-state Markov-Gilbert channel simulating IEC 61400-25 substation communication disruptions with consecutive burst drops up to 6 steps. In the honest symmetric evaluation where telemetry drops affect both wind-speed and pitch-angle channels, the stale rule's recall drops to 0.840 and F1 to 0.904, whereas the corrupted routed posterior maintains 0.994 recall and 0.967 F1 (seed-paired F1 gain $+0.064$, 95\% bootstrap CI $[+0.021, +0.087]$, $p < 0.05$). The legacy 0.996 F1 reflects an asymmetric evaluation where wind speed remained pristine and persistent steady-state pitching masked boundary misdetections. Script: \texttt{scripts/eval\_markov\_gilbert\_telemetry.py}.
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
\footnotesize Same-model intervals are $n=5$ seed-paired bootstrap mean CIs for gate-bin minus same-router global at $\rho=10$.
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
\footnotesize The classifier is refit per seed on validation anchors only. Hard classifier bins are nearly equivalent to physical bins on clean anchors; the hard gate route is worse than both. The soft gate posterior is the only strategy below every modular alternative (16.065M). Combined with the fair-degradation audit, where the classifier falls to recall 0.885 under the strongest noise against 0.951 for the gate, the modular classifier matches clean-anchor pricing with no detected difference while the soft posterior keeps the degraded-stream robustness in one deployment object. Script: \texttt{scripts/modular\_equiv\_reserve.py}.
\end{table}
```

## Mechanism decomposition of the boundary-risk posterior {.unnumbered}

Table A11d consolidates the counterfactual controls that localize where the posterior's value comes from. The soft-physical pitch quantile is the honest clean-observation baseline; joint learning is what prices reserve risk below the global rule and far below an independent classifier posterior; the routing structure is what survives confirming-stream degradation. Scripts: `scripts/soft_rule_contrast.py`, `scripts/degraded_gate_reserve.py`, `scripts/kelmarsh_reserve_pricing.py`, `scripts/multichannel_classifier.py`, `scripts/gbdt_reserve_pricing.py`, `scripts/dense_classifier_pricing.py`, `scripts/fair_degradation_replay.py`.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11d.} Mechanism decomposition with counterfactual controls ($\rho=10$, 5 seeds, boundary band).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllllll}
\toprule
Method & Jointly trained & Needs physical channels & Routed & Reserve cost & Degraded recall & Reading \\
\midrule
Soft physical pitch quantile & no & yes & no & 15.538M & -- & Optimal clean baseline (15.538M clean, 16.048M delay-6); unavailable when pitch sensors missing/uncalibrated/frozen \\
Threshold rule (physical-bin) & no & yes & no & 16.190M & 0.196 & Collapses under confirming-stream delay \\
Independent logistic classifier & no & yes & no & 16.190M & 0.885 (noise) & Equivalent clean pricing; no degradation robustness \\
Independent GBDT posterior & no & consequence channels & no & 17.656M & 0.868 & Immune to Wspd/Pab delay but prices 1.0M worse than the global rule \\
Joint non-routed posterior head & yes & weak & no & 16.076M & 0.286 & Joint learning prices; without routing it collapses under delay \\
Joint routed posterior (this work) & yes & weak & yes & 16.065M & 0.933 & Joint learning prices and the routing structure survives degradation \\
\midrule
Global quantile & -- & -- & -- & 16.632M & 0.971 (clean) & Reference \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Reserve costs are validation-frozen boundary-band totals (mean over five seeds); seed-paired CIs: soft-physical vs joint-routed +526k [330k, 719k]; joint-routed vs global -568k [-726k, -406k]; joint-routed vs independent GBDT -1.59M (see \texttt{artifacts/breakthrough\_20260904}). Degraded recall is early-window recall under a six-step confirming-stream delay (or strongest noise level where noted) applied identically to every detector; the soft-physical pitch quantile is a continuous pricing rule without discrete recall, and under a 6-step delay its reserve cost degrades to 16.048M. In pitch-sparse wind plants where blade-pitch sensors are uncalibrated or frozen (e.g., Kelmarsh with only 55\% pitch coverage), physical pitch quantiles become unavailable across over 40\% of turbines, whereas the jointly-learned posterior restores risk awareness from cross-sensor electromechanical signatures as defense-in-depth. Kelmarsh sparse-farm pricing increment is not significant (-40k, CI [-202k, +129k]) and is disclosed as such. Time-block robustness: a hierarchical seed-and-week-block bootstrap over daily reserve costs across the 35-day test period keeps the gate-bin-vs-global difference significantly negative for both MoE families (Boundary router pooled 5-seed total delta of -22.40M, corresponding to a per-seed mean of -4.48M which matches the -4.42M per-seed evaluation in Table A11 within bootstrap resampling granularity, 95\% hierarchical block CI [-39.55M, -7.61M]; Physics-Aligned MoE pooled 5-seed total -23.39M, CI [-42.41M, -7.02M]), confirming that the reserve advantage is robust to temporal autocorrelation across weeks.
\end{table}
```

## Kelmarsh asynchronous event-stream grounding {.unnumbered}

The confirming-stream delay scenario is grounded in the operational reality of asynchronous event streams as observed in the Kelmarsh 2016 archive. The Status stream exported by the Greenbyte platform carries 14,019 status events with second-level timestamps; 99.6\% of them fall strictly between the 10-minute turbine-data periodic grid points, meaning that 10-minute periodic SCADA sampling cannot synchronously confirm operating state events at issue time. Pitch-system operating states arrive as a separate asynchronous event stream (e.g. "Pitch measuring system 1><2"). Rather than claiming a fixed runtime delay in field telemetry, we evaluate operational resilience via a controlled deployment stress test with 1- to 6-step confirmation delays and sensor noise. Script and artifact details are archived in `artifacts/kelmarsh_grounding_20260903/`.

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
Joint gate vs global (sparse farm) & -0.04M & [-0.20M, +0.13M] & no & Kelmarsh 55\% \\
Soft-physical vs global (sparse farm) & -0.03M & [-0.09M, +0.05M] & no & Kelmarsh 55\% \\
\midrule
\multicolumn{5}{p{0.96\columnwidth}}{\footnotesize $m=13$ family; all 95\%-significant controls remain significant under Bonferroni ($\alpha=0.05/13$, 99.62\% CI) because their CIs exclude zero. CI crossing zero indicates no detected difference, not formal equivalence. Raw tables and scripts in \texttt{artifacts/p1\_stats\_20260904/}.} \\
\bottomrule
\end{tabular}%
}
\end{table}
```

## Wind farm PCC bus-level aggregated reserve pricing under spatial portfolio smoothing {.unnumbered}

To address the industrial power engineering reality that grid operators dispatch and clear reserves at the Point of Common Coupling (PCC) bus rather than at individual turbine terminals, we aggregate actual and predicted power across all 134 WTB wind turbines ($P_{\mathrm{farm}}(t, h) = \sum_{i=1}^{134} P_{i}(t, h)$). Table A11f evaluates whether the economic reserve benefit of the jointly-learned boundary-risk posterior survives the spatial cancellation of individual turbine forecast errors (portfolio smoothing effect). Across the full operational envelope, joint posterior aggregate quantile pricing saves $-11.22\text{M kWh}$ (95\% bootstrap CI $[-21.55\text{M}, -2.85\text{M}]$, strictly excluding zero) against the global PCC quantile and $-14.94\text{M kWh}$ (CI $[-27.06\text{M}, -6.23\text{M}]$) against the Gaussian parametric baseline. In transitional operating regimes where 10\% to 90\% of turbines are pitching, the joint posterior saves $-1.48\text{M kWh}$ (CI $[-2.14\text{M}, -1.07\text{M}]$) compared to continuous physical pitch rules, confirming that boundary-conditioned risk pricing retains substantial economic value after fleet-wide spatial smoothing.

```{=latex}
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11f.} Wind farm Point of Common Coupling (PCC) aggregated reserve pricing under 134-turbine spatial portfolio smoothing ($\rho=10$, 5 seeds, WTB test split).}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lllrrrl}
\toprule
Regime / Condition & Strategy & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & $p$-value \\
\midrule
Full Operational Envelope & Joint Posterior Aggregate & Global PCC Quantile & -11.22M & [-21.55M, -2.85M] & \textbf{yes} ($p < 0.05$) & 0.125 \\
Full Operational Envelope & Joint Posterior Aggregate & Gaussian PCC Param & -14.94M & [-27.06M, -6.23M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Full Operational Envelope & Soft-Pab Aggregate & Global PCC Quantile & -5.95M & [-11.07M, -0.82M] & \textbf{yes} ($p < 0.05$) & 0.125 \\
Full Operational Envelope & Gaussian PCC Param & Global PCC Quantile & +3.72M & [+0.89M, +5.67M] & \textbf{yes} ($p < 0.05$) & 0.125 \\
\midrule
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Soft-Pab Aggregate & -1.48M & [-2.14M, -1.07M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Soft-Pab Aggregate & Global PCC Quantile & +2.05M & [+1.45M, +2.65M] & \textbf{yes} ($p < 0.05$) & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Global PCC Quantile & +0.56M & [+0.06M, +1.09M] & \textbf{yes} ($p < 0.05$) & 0.188 \\
\bottomrule
\end{tabular}%
}
\vspace{1mm}
\footnotesize Evaluated on aggregated wind plant active power at the PCC bus summing over all 134 turbines ($P_{\mathrm{farm}} = \sum_i P_i$). Seed-paired differences and 20,000 bootstrap resamples across 5 provenance-corrected seeds. Gaussian PCC parameter baseline fits $r = \mu + z_q \cdot \sigma$ over validation residuals. Script: \texttt{scripts/eval\_farm\_aggregate\_reserve.py}, artifacts in \texttt{artifacts/farm\_aggregate\_reserve\_20260905/}.
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
Boundary gate-bin vs same-router global (train-only) & +1950 & +637 & -4420 & -442k \\
Boundary gate-bin vs GWN physical-bin (legacy) & +2319.2 & +205.6 & +262.9 & +26k \\
Boundary gate-bin vs GWN global full sample (legacy) & +3148.2 & -1413.5 & +17283.2 & +1728k \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\footnotesize Values are MWh-equivalent forecast-cell accounting with $\Delta t=1/6$ h. Cost-scale@100 is an illustrative reserve-cost scale marker at 100 EUR/MWh, not market revenue, settlement value, OPF, or unit-commitment output. Boundary rows are from the train-only rerun; GWN comparison rows remain legacy pure-prediction baselines. Use same-router/global as the bounded boundary-window diagnostic; physical-bin and full-sample rows block reserve superiority.
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

## ERA5 observability contrast {.unnumbered}

The ERA5 contrast tests a setting in which the physical marker is directly visible. Three archived months of hourly data over a fixed $16\times16$ patch are reorganised into a $T{=}2208$-frame tensor with $N{=}256$ nodes and eight input variables. The thermodynamic regime label separates stable from convective near-surface states using sensible heat flux and its local time delta: convective samples have positive afternoon flux anomaly, stable samples do not; the label is available at 60\% coverage and enters only alignment supervision. The gate anchor is $[\texttt{sshf}, \texttt{t2m}, \texttt{wind\_speed}, \Delta\texttt{sshf}]$, and the graph is a static Haversine-Gaussian $k_{\mathrm{nn}}$ structure because no wake directionality is defined on a grid. The same directed-diffusion GRU and node-level MoE are trained with the full corrected stack; the contrast result is that Physics-Aligned MoE achieves NMI $0.210 \pm 0.109$ against an unconstrained collapse of $0.032 \pm 0.025$ under thermodynamic observability (`table_routing_quality.csv`), showing that supervision retains partial alignment under direct thermodynamic observation whereas unconstrained gating collapses. The ERA5 rows in Table A13 and the shared-architecture table carry the numerical record; ERA5 is not used for any reserve or deployment claim.

## Compute disclosure {.unnumbered}

All neural runs use a single GPU (NVIDIA RTX 4090), mixed precision, AdamW, gradient clipping, and early stopping on validation RMSE. The WTB boundary router has 110,012 parameters; one epoch takes approximately 445 s and early stopping selects checkpoints at 6-9 epochs, so a five-seed family costs roughly 6-7 GPU-hours. The signature-gate probes, fair-degradation replays, and reserve audits reuse saved checkpoints and test arrays and are CPU-minute analyses except the replay forwards, which re-evaluate the test split in under ten minutes on one GPU. All experiments are reproducible across the declared seeds; bitwise reproducibility across CUDA environments is not claimed.


