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
  - \makeatletter
  - '\newcommand{\SupplementPlainCaption}[1]{\par\smallskip{\footnotesize\centering #1\par}\smallskip}'
  - '\AtBeginDocument{\let\SupplementNumberedCaption\caption\renewcommand{\caption}{\@ifstar{\SupplementPlainCaption}{\SupplementNumberedCaption}}}'
  - \makeatother
  - \usepackage{float}
  - \usepackage{graphicx}
  - \usepackage{dblfloatfix}
  - \usepackage{placeins}
  - \extrafloats{500}
  - \usepackage{dblfloatfix}
  - \extrafloats{500}
  - \linespread{0.985}
  - \renewcommand{\dbltopfraction}{0.95}
  - \renewcommand{\dblfloatpagefraction}{0.85}
  - \setcounter{dbltopnumber}{3}
---

# Appendix A. Training and implementation details {.unnumbered}

```{=latex}
\FloatBarrier
```

## Evidence status of the archived material {.unnumbered}

The tables below retain archived numerical records, including superseded and exploratory analyses. They are not a certificate of complete raw-data reproduction or operational safety. Missing original weight, complete-input, numerical-environment and posterior-coordinate bindings remain unknown under the frozen provenance audit. Explicit residual coordinates and stored accounting support bounded diagnostics; independently receipt-bound later bundles retain only their own audited scope. E04 returned no feasible policy under unchanged risk constraints. E07 remains inactive. The archived sections retain their historical scope; the final controlled-subset appendix separately reports the completed frozen development study.

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

```{=latex}
\FloatBarrier
```

## Model-family and supplementary evidence index {.unnumbered}

Table A1 is designed to separate shared representation capacity from expert allocation, following the standard mixture-of-experts comparison logic [@jacobs1991adaptive; @shazeer2017outrageously].

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A1.} In-family model comparison used for mechanism validation. Encoder capacity is held approximately fixed so that routing terms, rather than parameter count alone, explain the mechanism contrast.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.20\linewidth} >{\raggedright\arraybackslash}p{0.18\linewidth}}
\toprule
Model & Routing & Extra terms & Params & Role \\
\midrule
Dense (matched) & Single dense head & None & WTB 110,012 / ERA5 103,272 & Shared-mapping reference \\
Unconstrained MoE & Node-level soft gate & Prediction loss only & WTB 110,012 / ERA5 103,843 & Routed-capacity control \\
Corrected routing comparator & Node-level soft gate & WTB boundary-forced: $L_{bal}+L_{align}+L_{force}$; ERA5: full corrected stack & WTB 110,012 / ERA5 103,843 & Accountability comparator \\
\bottomrule
\end{tabularx}
\end{table*}
```


```{=latex}
\FloatBarrier
```

## Information boundary and channel roles {.unnumbered}

Table A2 makes the leakage and shared-anchor boundary explicit. The routing labels
and some gate anchors deliberately share wind-speed and pitch information; the
reported NMI/ARI therefore audits alignment with a declared SCADA boundary, not
anchor-free discovery.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A2.} Information boundary and channel-role audit.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.15\linewidth} >{\raggedright\arraybackslash}p{0.18\linewidth}}
\toprule
Quantity & Label construction & Model input / gate anchor & Supervised target & Timing boundary \\
\midrule
\texttt{Wspd} & WTB regime label & history and issue-time anchor & no & $\leq t$ only \\
\texttt{Pab\_mean} & WTB regime label & history and issue-time anchor (offline training only; withheld at deployment) & no & $\leq t$ only \\
$\texttt{Patv}_{t-H+1:t}$ & no & historical input / issue-time status & no & $\leq t$ only \\
$\texttt{Patv}_{t+1:t+P}$ & no & no & yes & future target only \\
Wake score & auxiliary wake flag & graph-derived anchor & no & computed from issue-time graph \\
Declared regime label & alignment/forcing supervision & no test-time input & no & train/validation supervision only \\
Confirmed threshold stream & degraded-rule comparator & not a model input & no & delayed/missing/noisy in audit \\
\bottomrule
\end{tabularx}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Auxiliary losses {.unnumbered}

Let $\mathcal{B}$ denote the routed samples after masks, with $B=|\mathcal{B}|$. The soft importance and normalized share of expert $e$ are $I_e = \frac{1}{B}\sum_{n=1}^{B} g_n^{(e)}$ and $P_e = I_e / \sum_{r} I_r$. The top-$K$ load is $f_e = \frac{1}{B}\sum_{n=1}^{B}\mathbf{1}[e \in \mathrm{TopK}(\mathbf{g}_n)]$, giving
$$\mathcal{L}_{\mathrm{bal}} = E\sum_{e=1}^{E} f_e P_e - 1.$$
For WTB wake supervision,
$$\mathcal{L}_{\mathrm{aux}} = \frac{1}{|\Omega_{\mathrm{wake}}|}\sum_{(i,t)\in\Omega_{\mathrm{wake}}}\mathrm{BCE}(z^{(\mathrm{wake})}_{i,t}, W_{i,t}),$$
where $\Omega_{\mathrm{wake}}$ contains only MPPT and pitch-control samples with defined wake flags. The graph-smoothness penalty is
$$\mathcal{L}_{\mathrm{smooth}} = \frac{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)\lVert\mathbf{g}_{i,t}-\mathbf{g}_{j,t}\rVert_2^2}{\sum_{t\in\mathcal{T}_{\mathcal{B}}}\sum_{i,j}\mathcal{A}_t(i,j)+\epsilon}.$$

```{=latex}
\FloatBarrier
```

## Graph construction details {.unnumbered}

For WTB, the downstream unit vector is $\mathbf{u}_{i,t}=[\sin(\theta_{i,t}+\pi), \cos(\theta_{i,t}+\pi)]^{\top}$. With $\Delta\mathbf{p}_{ij}=\mathbf{p}_j-\mathbf{p}_i$, the streamwise and cross-stream distances are $d^{\parallel}_{ij,t}=\Delta\mathbf{p}_{ij}^{\top}\mathbf{u}_{i,t}$ and $d^{\perp}_{ij,t}=|\Delta p^x_{ij}u^y_{i,t}-\Delta p^y_{ij}u^x_{i,t}|$. A candidate edge activates when
$$\mathbb{I}^{\mathrm{cone}}_{ij,t}=\mathbf{1}\!\left[d^{\parallel}_{ij,t}>0\;\land\;\arctan\!\left(\frac{d^{\perp}_{ij,t}}{\max(d^{\parallel}_{ij,t},10^{-6})}\right)\le\phi\right].$$
The wake weight is $\tilde{\mathcal{A}}_t(i,j)=\exp(-d^{\parallel}_{ij,t}/\alpha)\exp(-|d^{\perp}_{ij,t}|/\beta)\mathbb{I}^{\mathrm{cone}}_{ij,t}$. If wind direction is missing, fall back to $\mathcal{A}^{\mathrm{static}}(i,j)=\exp(-\lVert\Delta\mathbf{p}_{ij}\rVert_2/d_{\max})$. Only the strongest $M$ inbound weights are retained. The wake score and flag are $s^{\mathrm{wake}}_{i,t}=\sum_{j}\mathcal{A}_t(i,j)$ and
$$W_{i,t}=\begin{cases}1,&s^{\mathrm{wake}}_{i,t}\ge q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\0,&s^{\mathrm{wake}}_{i,t}<q_{0.75}^{\mathrm{wake}}\land R^{\mathrm{wtb}}_{i,t}\in\{1,2\},\\\varnothing,&\text{otherwise.}\end{cases}$$

For ERA5, the retained symmetric graph uses a Gaussian kernel on great-circle distances:
$$\mathcal{A}(i,j)=\exp\!\left(-\frac{d_{ij}^2}{2\sigma^2}\right)\mathbf{1}[j\in\mathcal{N}_{k_{\mathrm{nn}}}(i)\;\text{or}\;i\in\mathcal{N}_{k_{\mathrm{nn}}}(j)],$$
where $\sigma$ is the median retained neighbor distance on the training graph.

```{=latex}
\FloatBarrier
```

## Operating-decision context and physical regime anchors (Figure A1) {.unnumbered}

Figure A1 visualizes the spatial turbine layout, wake-graph geometry, and physical regime anchors defining the operational reserve screening benchmark.

```{=latex}
\renewcommand{\thefigure}{A\arabic{figure}}
\setcounter{figure}{0}
\begin{figure*}[!t]
\centering
\includegraphics[width=0.92\textwidth]{artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf}
\caption{Diagnostic spatial and thermodynamic data boundaries: (A) WTB turbine layout with the schematic wake cone ($25^\circ$ half-angle) and candidate radius used in the dynamic directed wake graph. (B) ERA5 $16\times 16$ patch with training-mean sensible heat flux and local Haversine-Gaussian graph connections around the central node. (C) WTB operating regimes in the $(Wspd, Pab_{\mathrm{mean}})$ plane with fixed operating-rule boundaries; the MPPT-to-pitch boundary is the reserve-diagnostic window used in this paper. (D) ERA5 thermodynamic regimes in the $(sshf, \Delta sshf)$ plane with thresholds estimated from the training split, included as an observability contrast.}
\label{fig:s-regime-anchors}
\end{figure*}
```

```{=latex}
\FloatBarrier
```

## Shared constants {.unnumbered}

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A3.} Shared architecture, graph, and training constants used in the reported experiments. Shared constants are listed before dataset-specific values so that controlled factors can be distinguished from observability-specific design choices.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.30\columnwidth} >{\raggedright\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Dataset-specific thresholds and routing weights {.unnumbered}

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A4.} Dataset-specific regime thresholds used to construct routing anchors. The values are operational definitions fixed or estimated before test evaluation; they are not universal turbine constants.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.28\columnwidth} >{\raggedright\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

The loss-weight table follows the physics-informed learning principle that a scientific constraint must be named and scaled explicitly [@karniadakis2021piml; @karpatne2017tgds].

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{6pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A5.} Active routing-loss weights in the reported corrected models. The table records which regulariser is active in each observability setting.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Statistical claim boundaries {.unnumbered}

Table A6 separates the train-only RMSE guardrail from paired seed-level tests on the train-only checkpoints. The iTransformer row is the displayed five-seed train-only guardrail gap; the Graph WaveNet row is a legacy pure-prediction baseline contrast; the gate-versus-full-MoE rows use the official reviewer-stat-pack paired statistics on train-only checkpoints for both families.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A6.} Statistical claim boundaries used for reviewer-facing wording.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.11\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Class-weight sensitivity audit {.unnumbered}

Table A6b makes the class-weight provenance boundary explicit. The legacy strict-cache row records the historical boundary-router checkpoint from earlier iterations; the train-only rerun recomputes alignment and pitch-forcing class weights from the training split only and supplies the reported train-only forecasting guardrail; it is not the source of every decision or external-transfer result. The train-only rerun lowers NMI/ARI to NMI 0.721 (0.7208) and ARI 0.740 (0.7398) while reaching RMSE 229.93 (narrowing the gap to 5.59 units vs. 224.34), remaining above the routing-claim threshold.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A6b.} Class-weight sensitivity audit. Boundary-router rerun after recomputing alignment and pitch-forcing loss weights from the training split only.}
%
\begin{tabular}{lrrrrr}
\toprule
Condition & Overall RMSE & Switch RMSE & Pitch RMSE & NMI & ARI \\
\midrule
Legacy strict-cache weights & 236.13 & 239.86 & 286.95 & 0.8716 & 0.9166 \\
Train-only weight rerun & 229.93 & 231.65 & 289.63 & 0.7208 & 0.7398 \\
Delta & -6.20 & -8.21 & 2.68 & -0.1508 & -0.1768 \\
\bottomrule
\end{tabular}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Clean privileged-supervision ablation and seed-level statistical audit {.unnumbered}

Table A6c provides the archived seed-level paired evaluation between identical 4-expert backbones trained with auxiliary cross-entropy alignment ($\lambda_{\text{align}}=5000.0$) versus unaligned representations ($\lambda_{\text{align}}=0.0$) under strict validation/testing blade-pitch withholding. Independent model random seed serves as the unit of replication ($n=5$). Paired differences ($\Delta = \text{Align} - \text{No Align}$) are evaluated using Student-$t$ confidence intervals ($df=4$) and paired hypothesis tests. Panel A reports the exact by-seed paired values. Panel B reports the statistical summary, paired confidence intervals, hypothesis tests, and leave-one-seed-out sensitivity.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.02}
\caption*{\textbf{Table A6c.} Clean matched-backbone privileged-supervision ablation and seed-level statistical audit ($n=5$ independent random seeds 201--205). Unit of replication is model random seed.}
%
\noindent\textbf{Panel A: Seed-Level Paired Values ($n=5$)}\par
\vspace{1mm}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l c c c c c c@{}}
\toprule
Metric & Seed 201 & Seed 202 & Seed 203 & Seed 204 & Seed 205 & Paired Mean $\Delta$ [95\% CI] \\
\midrule
NMI ($\lambda=0 \to 5000$) & \shortstack{0.253 $\to$ 0.760\\(+0.507)} & \shortstack{0.237 $\to$ 0.918\\(+0.681)} & \shortstack{0.410 $\to$ 0.741\\(+0.331)} & \shortstack{0.000 $\to$ 0.763\\(+0.763)} & \shortstack{0.300 $\to$ 0.912\\(+0.612)} & +0.579 [+0.371, +0.787] \\
\addlinespace[1pt]
ARI ($\lambda=0 \to 5000$) & \shortstack{0.177 $\to$ 0.863\\(+0.686)} & \shortstack{0.160 $\to$ 0.954\\(+0.794)} & \shortstack{0.369 $\to$ 0.827\\(+0.458)} & \shortstack{0.000 $\to$ 0.858\\(+0.858)} & \shortstack{0.283 $\to$ 0.945\\(+0.662)} & +0.692 [+0.502, +0.882] \\
\addlinespace[1pt]
Brier ($\lambda=0 \to 5000$) & \shortstack{0.019 $\to$ 0.020\\(+0.002)} & \shortstack{0.019 $\to$ 0.019\\(0.000)} & \shortstack{0.169 $\to$ 0.024\\(-0.145)} & \shortstack{0.981 $\to$ 0.021\\(-0.961$^\ast$)} & \shortstack{0.019 $\to$ 0.019\\(0.000)} & -0.221 [-0.740, +0.299] \\
\addlinespace[1pt]
Full PSREI $h=6$ (kWh) & \shortstack{15.17M $\to$ 15.50M\\(+329k)} & \shortstack{12.78M $\to$ 13.06M\\(+281k)} & \shortstack{16.73M $\to$ 16.37M\\(-360k)} & \shortstack{18.27M $\to$ 16.09M\\(-2.18M$^\ast$)} & \shortstack{14.23M $\to$ 14.60M\\(+369k)} & -312k [-1.66M, +1.04M] \\
\addlinespace[1pt]
Bnd PSREI $h=1$ (kWh) & \shortstack{683k $\to$ 669k\\(-14k)} & \shortstack{624k $\to$ 786k\\(+162k)} & \shortstack{708k $\to$ 714k\\(+7k)} & \shortstack{726k $\to$ 698k\\(-28k)} & \shortstack{580k $\to$ 598k\\(+18k)} & +29k [-66k, +124k] \\
\addlinespace[1pt]
Bnd PSREI $h=6$ (kWh) & \shortstack{936k $\to$ 931k\\(-4k)} & \shortstack{996k $\to$ 1047k\\(+50k)} & \shortstack{1127k $\to$ 1132k\\(+5k)} & \shortstack{989k $\to$ 1027k\\(+38k)} & \shortstack{862k $\to$ 850k\\(-13k)} & +15k [-19k, +49k] \\
\bottomrule
\end{tabular*}
\vspace{2mm}

\noindent\textbf{Panel B: Statistical Summary and Inferential Audit ($n=5$, $df=4$)}\par
\vspace{1mm}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l ccc c c l@{}}
\toprule
Metric & No Align ($\lambda=0$) & Align ($\lambda=5000$) & Paired $\Delta$ & 95\% Student-$t$ CI & Test Statistic ($p$) & Inferential Status \\
\midrule
NMI & 0.240 $\pm$ 0.150 & 0.819 $\pm$ 0.088 & +0.579 $\pm$ 0.167 & [+0.371, +0.787] & $t(4) = 7.74$ ($p=0.0015$) & Supported \\
ARI & 0.198 $\pm$ 0.139 & 0.889 $\pm$ 0.057 & +0.692 $\pm$ 0.153 & [+0.502, +0.882] & $t(4) = 10.10$ ($p=0.0005$) & Supported \\
Brier Score & 0.241 $\pm$ 0.419 & 0.020 $\pm$ 0.002 & -0.221 $\pm$ 0.418 & [-0.740, +0.299] & $t(4) = -1.18$ ($p=0.303$) & Collapse-sensitive$^\dagger$ \\
Full PSREI $h=6$ & 15.44M $\pm$ 2.14M & 15.13M $\pm$ 1.34M & -312k $\pm$ 1,086k & [-1.66M, +1.04M] & $t(4) = -0.64$ ($p=0.556$) & Unconfirmed (CI crosses 0) \\
Bnd PSREI $h=1$ & 664k $\pm$ 61k & 693k $\pm$ 68k & +29k $\pm$ 76k & [-66k, +124k] & $t(4) = 0.84$ ($p=0.446$) & Unconfirmed (CI crosses 0) \\
Bnd PSREI $h=6$ & 982k $\pm$ 97k & 997k $\pm$ 109k & +15k $\pm$ 28k & [-19k, +49k] & $t(4) = 1.24$ ($p=0.283$) & Unconfirmed (CI crosses 0) \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont Note: $^\ast$Seed 204 unaligned experienced representation collapse (Brier 0.9812, expert usage entropy $\to 0$). $^\dagger$Leave-one-seed-out sensitivity: excluding Seed 204, Brier paired $\Delta = -0.0359 \pm 0.0728$ ($p=0.3970$); alignment improves average calibration across runs but the estimated magnitude is sensitive to this single collapse run. The matched $\lambda_{\text{align}}$ ablation isolates regime-label supervision conditional on privileged training inputs; it does not isolate training-time pitch access itself.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Outcome-channel sanity audit {.unnumbered}

Table A7 adds a bounded check for the shared-anchor concern. Supplementary anchor-stress ablations confirm that boundary recovery withstands sensor withholding and temporal latency: variant no\_patv achieves NMI 0.881, no\_pab\_mean achieves NMI 0.878, lagged\_patv achieves NMI 0.763, and lagged\_pab\_wspd achieves NMI 0.684. It does not use pitch-threshold labels to score the contrast. Validation data define a wind-speed-bin power curve, and the test comparison is restricted to 9.5--11.5 m s$^{-1}$ boundary anchors with fine wind-bin adjustment. This table is arranged as a sanity audit because SCADA studies must separate issue-time signals from the future outcomes they predict [@tautzweinert2017scada; @zhou2024sdwpfdata]. The result asks whether the recovered gate separates samples with different future active-power response, not whether it discovers a regime without anchors.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A7.} Outcome-channel sanity audit for the shared-anchor concern.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

```{=latex}
\FloatBarrier
```

## S3. Mechanism and Representation Diagnostics {.unnumbered}

## Early-warning detection consequence {.unnumbered}

Table A10 reports the detector control for the label-degradation audit. The simple classifier is a validation-fit multinomial logistic regression on the same issue-time anchors. It matches or exceeds the gate on clean-anchor standalone detection, so the manuscript claims auditable in-model route attribution rather than classifier superiority. Gate values in degraded-label rows are the saved clean-route audit; the degraded stream is applied to the rule and classifier controls. Table A10d reports the fair-degradation counterpart, where delay and sensor noise degrade the gate's own inputs as well. Recovered cells are turbine-time cells per seed inside the six-step MPPT-to-pitch window, not MWh, currency or dispatch-cost estimates.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10.} Early-warning detector control under degraded threshold labels (train-only gate values).}
%
\begin{tabular}{lrrrrrrr}
\toprule
Condition & Gate R & Gate P & Classifier R & Classifier P & Rule R & Rule P & Recovered cells \\
\midrule
Clean live anchors & 0.971 & 0.630 & 1.000 & 0.879 & 1.000 & 0.879 & -- \\
Delay, 6 steps & 0.971 & 0.630 & 1.000 & 0.879 & 0.196 & 0.342 & 565.6 $\pm$ 20.6 \\
50\% label availability & 0.971 & 0.630 & 1.000 & 0.879 & 0.508 & 0.877 & 334.6 $\pm$ 28.1 \\
Sensor noise, strongest & 0.971 & 0.630 & 0.885 & 0.758 & 0.652 & 0.804 & 227.8 $\pm$ 20.9 \\
\bottomrule
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont R/P denote recall and precision on early pitch-window cells. The simple classifier is a validation-fit logistic model on the same issue-time anchors; it is a detector control, not a routed forecaster. In sensor-noise rows, gate values are the saved clean-route audit; classifier/rule values are recomputed from noisy anchors. Gate precision drops to 0.630 under the train-only rerun, widening the disclosed gap to the classifier control.
\end{table*}
```

Table A10d reports the fair-degradation audit under the Unified Arrival Layer: confirming-stream delay applies late wind-speed and pitch readings symmetrically across anchor inputs and encoder history channels ($x_{\mathrm{hist}}$ shifted by $d$ steps), completely eliminating clean-history observability loopholes at anchor $t$. Under a six-step delay ($d=6$, 60-minute stall), detection recall attenuates from 0.9705 to 0.4170, yet the jointly-learned posterior retains a +0.221 recall gain (+113% relative advantage) and +0.131 F1 gain over the collapsed deterministic threshold rule (0.1959 recall, 0.2491 F1). Table A10e evaluates industrial burst packet loss under a two-state Markov-Gilbert model with symmetric history degradation.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10d.} Fair-degradation audit: gate and physical rule consume the same degraded readings under the Unified Arrival Layer. Full precision, recall, and F1 profile across five train-only seeds.}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Values are means over 5 seeds under the Unified Arrival Layer (archived in \texttt{artifacts/fair\_degradation\_replay\_20260903/}). Full-stream history shift and anchor delay are applied symmetrically to both the gate and the deterministic threshold rule.
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A10e.} Industrial Markov-Gilbert bursty packet degradation audit ($p_{GB}=0.08, p_{BB}=0.75$, max lag 6 steps, 5 seeds, WTB operational test split).}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Evaluated over 146,552 burst-loss cells per seed under a two-state Markov-Gilbert channel simulating IEC 61400-25 substation communication disruptions with consecutive burst drops up to 6 steps. In the honest symmetric evaluation where telemetry drops affect wind-speed, pitch-angle, and active power channels across anchor and encoder history streams, the stale rule's recall drops to 0.840 and F1 to 0.904, whereas the corrupted routed posterior maintains 0.962 recall and 0.925 F1 (seed-paired F1 gain $+0.021$, 95\% bootstrap CI $[-0.014, +0.050]$). The legacy 0.994 recall / 0.967 F1 reflected an asymmetric evaluation where encoder history remained clean while only anchor readings were lagged. Script: \texttt{scripts/eval\_markov\_gilbert\_telemetry.py}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Gate route-evolution diagnostic {.unnumbered}

Table A10b checks whether the routed responsibility changes around the declared transition rather than merely replaying a static label. Matching to the new regime peaks at the transition step and drops under lead/lag shifts, supporting a route-evolution audit while not replacing the modular classifier control.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
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
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A10c.} Modular live-anchor classifier reserve control and paired statistical contrasts at $\rho=10$ on the WTB boundary slice (5 seeds 201--205).}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.24\linewidth} r r r r >{\raggedright\arraybackslash}X}
\toprule
Policy / Architecture & Cost (kWh) & Violation & Reserve (kWh) & Shortage (kWh) & Paired Contrast vs. Classifier-bin \\
\midrule
Graph WaveNet + live-anchor clf & 86,536,321 & 9.54\% & 50,694,434 & 3,584,189 & Baseline modular comparator \\
Graph WaveNet physical-bin & 84,314,353 & 9.31\% & 50,347,427 & 3,396,693 & $\Delta = -2.22\text{M}$ [$-2.63\text{M}, -1.66\text{M}$] ($t$-test $p=0.0013$; Wilcoxon floor $p=0.0625$) \\
Boundary-forced router (gate-bin) & 84,577,217 & 9.00\% & 52,666,639 & 3,191,058 & $\Delta = -1.96\text{M}$ [$-12.71\text{M}, +8.18\text{M}$] ($p=0.757$, crosses zero) \\
Graph WaveNet global & 88,797,862 & 10.22\% & 50,316,975 & 3,848,089 & $\Delta = +2.26\text{M}$ [$+1.35\text{M}, +2.95\text{M}$] ($p=0.0016$) \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Evaluated across 5 random seeds (201--205) on the WTB boundary slice. Paired deltas are defined as Reference minus Classifier-bin. Against the physical-bin baseline, the independent classifier incurs a $+2.22\text{M kWh}$ penalty with 95\% bootstrap CI over the 5 seeds strictly excluding zero ($[+1.66\text{M}, +2.63\text{M}]$), paired parametric $t$-test $p=0.0013$, and exact seed Wilcoxon permutation floor $p=0.0625$ (governed by $n=5$). Against the joint boundary-forced router, the mean delta is $+1.96\text{M kWh}$ but the 95\% bootstrap CI strictly crosses zero ($[-8.18\text{M}, +12.71\text{M}]$, $p=0.757$). Script: \texttt{scripts/build\_modular\_classifier\_reserve\_baseline.py}, artifacts in \texttt{artifacts/modular\_classifier\_reserve\_control/}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Reserve-policy claim-boundary audit {.unnumbered}

Table A11 is the compact reviewer-facing boundary audit. The same-router boundary comparison has seed-paired uncertainty support, while physical-bin, full-sample and cross-backbone comparisons still bound the claim away from policy optimality or market-dispatch value. The row order moves from the supported local contrast to the stronger controls that limit extrapolation.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11.} Reserve-policy claim-boundary audit.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.22\columnwidth}}
\toprule
Boundary & Key evidence & Limit \\
\midrule
Same-model boundary reserve effect & $\rho=10$: gate-bin 95.13M vs same-router global 99.55M ($\Delta$cost -4.42M [CI -7.36M,-1.27M]); $\Delta$viol. -0.0145 [CI -0.0220,-0.0073]; shortage -0.637M [CI -0.976M,-0.300M]; full-MoE family -4.26M [CI -5.43M,-3.04M] & Same-model diagnostic; not cross-model optimal \\
Physical-bin quantile comparator & Boundary phys. 93.82M/0.1010; GWN phys. 84.31M/0.0931; gate 95.13M/0.1021 & Physical bins remain competitive \\
Cost-ratio applicability & Active at $\rho=5$--10; narrows at 20; $\rho=50$ favors global (+5.93M, +0.0035) & Moderate-cost window only \\
Full-sample system value & GWN/global 464.07M/0.0901; gate-bin 481.36M/0.1214 & No system-wide dispatch claim \\
Cross-backbone/full-sample uncertainty & $\Delta$cost +17.28M; 95\% CI [-52.09M,+87.95M]; p=0.752 & Not system-wide or cross-backbone \\
Operational scope & Validation-frozen shortfall quantiles; no OPF, unit commitment, market clearing, or prices & Screening audit only \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Same-model intervals are $n=5$ seed-paired bootstrap mean CIs for gate-bin minus same-router global at $\rho=10$. Reserve cost denotes Penalized Reserve-Shortfall Energy Index (PSREI in kWh at $\rho=10$) as formalized in Section III-D of the main paper, serving as an upstream pre-dispatch screening metric rather than dynamic wholesale market settlement cashflows.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Uncertainty-conditioned reserve allocation {.unnumbered}

Table A11b reports the soft-posterior reserve strategies. All strategies use validation-frozen shortfall quantiles inside the +/-1.0 m s$^{-1}$ boundary band; bin edges for the learned strategies are fitted on validation anchor posteriors only. P(pitch) quintiles (soft-gate-bin) carry the boundary-direction information, while gate-entropy and max-probability quintiles are pure routing-uncertainty signals that require no physical bin and no threshold. Seed-paired bootstrap CIs are reported against global and physical-bin references.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11b.} Soft-posterior reserve strategies at $\rho=10$ (5 seeds, boundary band).}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth}}
\toprule
Strategy & Total cost & Violation & Reserve & Shortage \\
\midrule
Global (reference) & 16.632M & 0.098 & 15.656M & 976k \\
Physical-bin (upper bound) & 16.190M & 0.098 & 15.195M & 995k \\
Soft-gate-bin (P(pitch) quintiles) & 16.065M & 0.099 & 15.061M & 1.004M \\
Entropy-bin (entropy quintiles) & 16.323M & 0.099 & 15.340M & 983k \\
Maxprob-bin (max prob quintiles) & 16.307M & 0.099 & 15.318M & 989k \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Seed-paired 95\% bootstrap CIs (strategy minus baseline): soft-gate-bin vs global $\Delta$cost -568k [-726k,-406k], $\Delta$pinball@0.9 -1.82 [-2.33,-1.30]; entropy-bin vs global $\Delta$cost -309k [-396k,-221k], $\Delta$pinball -0.99 [-1.27,-0.71]; maxprob-bin vs global $\Delta$cost -325k [-454k,-214k], $\Delta$pinball -1.04 [-1.45,-0.69]. Versus physical-bin: entropy-bin +133k [+0.8k,+256k], maxprob-bin +117k [-29k,+264k] (matches). Violation rises by about 0.001 for the learned strategies. Protocol: boundary-band anchor cells only; not interchangeable with the full-sample Table III audit.
\end{table*}
```

Table A11c reports the modular-equivalence control on the same boundary-router backbone. The classifier is a validation-fit logistic regression on issue-time anchors (Wspd, Pab\_mean), and its hard and soft bins are compared with the gate's. On clean anchors the classifier reproduces the physical-bin reserve almost exactly and beats the hard gate route, so the hard route has no reserve increment; the jointly-learned soft posterior remains below every modular alternative, while Table A11d retains historical modular contrasts without certifying a causal allocation mechanism.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11c.} Modular-equivalence reserve control on the same backbone ($\rho=10$, 5 seeds, boundary band).}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth} >{\centering\arraybackslash}p{0.18\columnwidth}}
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
\fontsize{8.0pt}{9.6pt}\selectfont The classifier is refit per seed on validation anchors only. Hard classifier bins are nearly equivalent to physical bins on clean anchors; the hard gate route is worse than both. The soft gate posterior is the only strategy below every modular alternative (16.065M). Combined with the fair-degradation audit (Table A10d), where the deterministic physical rule falls to recall 0.680 under the strongest noise against 0.951 for the gate (and collapses to 0.196 under a 6-step delay against 0.417 for the gate), the modular classifier matches clean-anchor reserve allocation with no detected difference while the soft posterior retains reported discrimination in this diagnostic; reserve sufficiency and deployment safety are unverified. Script: \texttt{scripts/modular\_equiv\_reserve.py}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Selective decision abstention and risk-coverage policy {.unnumbered}

Table A11j benchmarks the selective decision abstention policy ($r_{i,t}^* = \hat{r}_{i,t}^{\text{learned}}$ if $U_{i,t} \le \theta_c$, else fallback headroom clamped to $P_{\text{rated}}$) against random abstention and uniform margin inflation under Delay-6 ($\tau=60\text{ min}$, $h=1$, 5 seeds on WTB).

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11j.} Risk-Coverage Selective Decision Abstention vs. Random and Uniform Controls under Delay-6 ($\tau=60\text{ min}$, $h=1$, 5-seed aggregate on WTB).}
%
\begin{tabular}{@{}llccc@{}}
\toprule
Model & Target $c$ ($\hat{c}$) & \shortstack{Selective Abstention\\Fleet Viol. / Cost} & \shortstack{Random Control\\Fleet Viol. / Cost} & \shortstack{Uniform Inflation\\Fleet Viol. / Cost} \\
\midrule
\multicolumn{5}{@{}l}{\textit{Mode: All Channels Observable}} \\
Joint Routed & $1.00$ ($1.00$) & $9.62\%$ / $1{,}274{,}047$ & $9.62\%$ / $1{,}274{,}047$ & $9.62\%$ / $1{,}274{,}047$ \\
 & $0.90$ ($0.94$) & $9.44\%$ / $1{,}274{,}784$ & $9.50\%$ / $1{,}272{,}870$ & $9.45\%$ / $1{,}273{,}944$ \\
 & $0.80$ ($0.85$) & $9.14\%$ / $1{,}277{,}532$ & $9.36\%$ / $1{,}270{,}990$ & $9.24\%$ / $1{,}274{,}781$ \\
 & $0.50$ ($0.53$) & $8.54\%$ / $1{,}276{,}252$ & $8.78\%$ / $1{,}265{,}902$ & $8.80\%$ / $1{,}277{,}570$ \\
\midrule
Frozen Backbone & $1.00$ ($1.00$) & $9.52\%$ / $1{,}283{,}268$ & $9.52\%$ / $1{,}283{,}268$ & $9.52\%$ / $1{,}283{,}268$ \\
 & $0.90$ ($0.94$) & $9.30\%$ / $1{,}277{,}806$ & $9.36\%$ / $1{,}281{,}737$ & $9.36\%$ / $1{,}283{,}424$ \\
 & $0.80$ ($0.85$) & $9.01\%$ / $1{,}273{,}271$ & $9.28\%$ / $1{,}279{,}718$ & $9.16\%$ / $1{,}284{,}225$ \\
 & $0.50$ ($0.53$) & $8.37\%$ / $1{,}264{,}384$ & $8.76\%$ / $1{,}271{,}385$ & $8.78\%$ / $1{,}286{,}221$ \\
\midrule
\multicolumn{5}{@{}l}{\textit{Mode: No Pitch Telemetry (Withheld)}} \\
Frozen Backbone & $1.00$ ($1.00$) & $8.68\%$ / $1{,}331{,}356$ & $8.68\%$ / $1{,}331{,}356$ & $8.68\%$ / $1{,}331{,}356$ \\
 & $0.90$ ($0.92$) & $8.93\%$ / $1{,}343{,}555$ & $8.61\%$ / $1{,}334{,}006$ & $\mathbf{8.83\%}$ / $\mathbf{1{,}330{,}829}$ \\
 & $0.80$ ($0.84$) & $9.15\%$ / $1{,}350{,}059$ & $8.66\%$ / $1{,}337{,}746$ & $\mathbf{8.92\%}$ / $\mathbf{1{,}331{,}452}$ \\
 & $0.50$ ($0.55$) & $8.84\%$ / $1{,}371{,}729$ & $8.55\%$ / $1{,}353{,}405$ & $\mathbf{8.29\%}$ / $\mathbf{1{,}333{,}906}$ \\
\bottomrule
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Cost in kW$\cdot$h ($\rho=10$). Fleet target $q^*=0.90$ ($10\%$ viol). Note: In \textit{No Pitch}, uniform margin inflation strictly Pareto-dominates selective abstention: ex-post equal-budget uniform inflation achieves $8.29\%$ violation at $1{,}334\text{k kW}\cdot\text{h}$, and ex-ante validation-frozen inflation achieves $7.12\%$ violation at $1{,}348\text{k kW}\cdot\text{h}$.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Mechanism decomposition of the boundary-risk posterior {.unnumbered}

Table A11d retains historical modular and counterfactual contrasts. Clean-telemetry cost rankings and synthetic delayed-stream recall do not isolate a joint-learning mechanism or establish routing necessity under a common frozen target. The physical pitch quantile is a clean-observation comparator. Scripts: `scripts/remote_matched_modular_baseline.py`, `scripts/soft_rule_contrast.py`, `scripts/degraded_gate_reserve.py`, `scripts/kelmarsh_reserve_pricing.py`, `scripts/multichannel_classifier.py`, `scripts/gbdt_reserve_pricing.py`, `scripts/dense_classifier_pricing.py`, `scripts/fair_degradation_replay.py`.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11d.} Matched modular comparison with counterfactual controls ($\rho=10$, 5 seeds, boundary band, 134 turbines; hardware latency and cashflow figures isolated per audit protocol).}
%
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llcccccl@{}}
\toprule
\shortstack[l]{Allocation /\\Detection Method} & Architecture & \shortstack{Joint\\Trained} & Channels & \shortstack{Reserve\\Cost} & \shortstack{$\Delta$ vs Global\\95\% Bootstrap CI} & \shortstack{Delay-6\\Recall} & \shortstack[l]{Footprint \&\\Governance} \\
\midrule
\shortstack[l]{Continuous pitch\\quantile (soft-pab)} & Physical bound & no & physical & 15.538M & -1.09M [-1.27M, -0.92M] & --$^{\dagger}$ & Physical sensor (Rule) \\
\shortstack[l]{Threshold rule\\(physical-bin)} & Discrete rule & no & physical & 16.190M & -0.44M [-0.58M, -0.30M] & 0.196 & SCADA rule (Rule) \\
\shortstack[l]{Independent logistic\\classifier} & Validation modular & no & physical & 16.190M & -0.44M [-0.58M, -0.30M] & --$^{\ddagger}$ & Classifier (Modular) \\
\shortstack[l]{Cascaded Frozen\\MLP posterior} & Two-stage decoupled & partial & consequence & 15.528M & -1.10M [-2.40M, +0.19M] & --$^{\ddagger}$ & Two-stage (Modular) \\
\shortstack[l]{Independent\\Consequence MLP} & Modular consequence & no & consequence & 15.805M & -0.83M [-2.18M, +0.53M] & --$^{\ddagger}$ & Neural net (Modular) \\
\shortstack[l]{Independent GBDT\\posterior} & Tree-based modular & no & consequence & 17.656M & +1.02M [+0.78M, +1.29M] & --$^{\ddagger}$ & GBDT (Tabular) \\
\shortstack[l]{Joint non-routed\\posterior head} & Dense multi-task & yes & weak & 16.076M & -0.56M [-0.71M, -0.40M] & 0.286 & Checkpoint (110k) \\
\shortstack[l]{Joint routed posterior\\(this work)} & Boundary-forced MoE & yes & weak & 16.065M & -0.57M [-0.73M, -0.41M] & 0.417 & Checkpoint (110k) \\
\midrule
Global quantile & Unstratified scalar & -- & -- & 16.632M & 0.000M [---] & 0.196 & Baseline scalar \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\parbox{\linewidth}{\fontsize{8.0pt}{9.0pt}\selectfont\raggedright Reserve costs are validation-frozen boundary-band totals (mean over five seeds); seed-paired CIs: soft-physical vs joint-routed +526k [330k, 719k]; joint-routed vs global -568k [-726k, -406k]; joint-routed vs Cascaded Frozen MLP (Joint 16.065M vs Cascaded 15.528M $\pm$ 1.599M, paired $\Delta = -0.537\text{M}$, 95\% CI [-1.988M, +0.915M], showing no detected difference under clean telemetry, not formal equivalence); joint-routed vs Independent Consequence MLP (15.805M $\pm$ 1.680M, paired $\Delta = -0.260\text{M}$, 95\% CI [-1.771M, +1.251M]); joint-routed vs independent GBDT -1.59M (see \texttt{artifacts/}\allowbreak\texttt{matched\_modular\_rerun\_5seeds/}\allowbreak\texttt{modular\_mlp\_summary\_5seeds.csv}). Degraded recall is early-window recall under a six-step confirming-stream delay ($^{\ddagger}$Consequence-only and modular baselines operate on aerodynamic-withheld channels for nominal consequence mapping and are not evaluated on spatio-temporal history temporal shift); the soft-physical pitch quantile is a continuous allocation rule without discrete recall, and under a 6-step delay its reserve cost degrades to 16.048M. In the archived synthetic diagnostic, Delay-6 recall is 0.417 vs. 0.286 for the dense head (+0.221 over the stale rule 0.196). These values do not establish fault-cascade mitigation, safety or edge-hardware feasibility. Hardware latency values (previously listed as 0.05--8.90 ms) and cashflow figures have been quarantined in accordance with Step 1 audit protocols pending physical RTU testbed validation. Kelmarsh sparse-farm allocation increment is not significant (-40k, CI [-202k, +129k]) and is disclosed as such. Time-block robustness: a hierarchical seed-and-week-block bootstrap over daily reserve costs across the 35-day test period keeps the gate-bin-vs-global difference significantly negative for both MoE families (Boundary router pooled 5-seed total delta of -22.40M, corresponding to a per-seed mean of -4.48M which matches the -4.42M per-seed evaluation in Table A11 within bootstrap resampling granularity, 95\% hierarchical block CI [-39.55M, -7.61M]; Physics-Aligned MoE pooled 5-seed total -23.39M, CI [-42.41M, -7.02M]), describing sensitivity within the archived bootstrap and weak global-quantile comparator; it does not establish superiority over wind-speed bins or certify the risk cap. \textit{Terminology Note:} Throughout this work, ``Reserve Cost'' maps directly to the Penalized Reserve-Shortfall Energy Index (PSREI in kWh at $\rho=10$).}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Kelmarsh asynchronous event-stream grounding {.unnumbered}

The confirming-stream delay scenario is grounded in the operational reality of asynchronous event streams as observed in the Kelmarsh 2016 archive. The Status stream exported by the Greenbyte platform carries 14,019 status events with second-level timestamps; 99.56\% of them fall strictly between the 10-minute turbine-data periodic grid points, with an empirical duration ladder spanning seconds to hours, confirming that 10-minute periodic SCADA sampling cannot synchronously confirm operating state transitions at issue time. Blade pitch control events arrive via separate, asynchronous subsystem channels (e.g., "Pitch measuring system 1><2"). Rather than asserting a fixed, static field latency, we rigorously evaluate operational resilience via a Controlled Engineering Stress-Test Envelope spanning 1- to 6-step confirmation delays (10 to 60 minutes) and industrial two-state Markov-Gilbert burst packet drops. Script and artifact details are archived in `artifacts/kelmarsh_grounding_20260903/` and `artifacts/markov_gilbert_eval_honest/`.

```{=latex}
\FloatBarrier
```

## Unified mechanism-control statistics {.unnumbered}

Table A11e consolidates every mechanism control into one reviewer-facing statistics table with family-wise multiplicity control ($m=13$). Both nominal 95\% bootstrap CIs and Bonferroni-adjusted 99.62\% CIs ($\alpha = 0.05/13$) are reported. Every control declared significant at the 95\% level survives the Bonferroni adjustment without crossing zero. For the joint non-routed dense head versus the joint gate router (+0.01M, 95\% CI [-0.16M, +0.19M]), no difference is detected; we do not assert formal equivalence because no equivalence margin was prespecified for TOST.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11e.} Unified mechanism-control statistics (total cost, $\rho=10$).}
%
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
\multicolumn{5}{p{0.96\columnwidth}}{\fontsize{8.0pt}{9.6pt}\selectfont $m=13$ family; all 95\%-significant controls remain significant under Bonferroni ($\alpha=0.05/13$, 99.62\% CI) because their CIs exclude zero. CI crossing zero indicates no detected difference, not formal equivalence. Raw tables and scripts in \texttt{artifacts/p1\_stats\_20260904/}.} \\
\bottomrule
\end{tabular}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Historical strong-baseline diagnostic and hybrid policies (Table A11m) {.unnumbered}

To address reviewer concerns regarding baseline competitiveness, Table A11m evaluates the relative risk-cost trade-off of the learned latent-boundary posterior compared to a strong observable wind-speed-conditioned quantile baseline (10 uniform bins over $[0, 25\text{ m/s}]$) under matched arrival-time constraints and identical forecast residuals ($s_t = \max(\hat{y}_t - y_t, 0)$ across 5 seeds).

Table A11m preserves the superseded historical result: $+523{,}044\text{ kW}\cdot\text{h}$ posterior penalty plant-wide. Its slice estimates, matched-budget narrative and formerly significant interaction are historical diagnostics, not current proof of heterogeneity or minimum sufficiency. The current imported candidate instead reports $+445{,}639\text{ kW}\cdot\text{h}$ Full, $+71{,}204\text{ kW}\cdot\text{h}$ Transition and $+374{,}436\text{ kW}\cdot\text{h}$ Steady, pending deep audit; its joint interaction interval crosses zero. Neither version certifies a deployment advantage. Separately, E04 on WTB Full returns ``no feasible policy'' at $q^*=0.90$, $\alpha=0.05$, $v_{\max}=0.10$ and zero difference tolerances. Its population and results must not be substituted with this historical table. A hybrid's non-significant difference does not establish equivalence, safety or minimum sufficiency.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.4pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11m.} Superseded historical diagnostic, not E04 or current certification: 5-seed evaluation of reserve screening policies across operational population slices under pitch withholding ($h=6$, $\rho=10$, WTB 134 turbines).}
\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}p{\dimexpr .11\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .19\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .20\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .12\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .075\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .115\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .19\linewidth-2\tabcolsep\relax}@{}}
\toprule
Population Slice & Policy ID \& Name & PSREI Cost ($\text{kW}\cdot\text{h}$) & Reserve ($\text{kW}\cdot\text{h}$) & Violation (\%) & Shortage ($\text{kW}\cdot\text{h}$) & $\Delta$ vs. Wspd ($\text{kW}\cdot\text{h}$) \\
\midrule
\textbf{Full Population} & Policy A: Global Quantile & $16{,}132{,}772 \pm 2{,}362{,}165$ & $12{,}484{,}016$ & 5.41\% & $364{,}876$ & $+2{,}348{,}452$ (Worse) \\
($N=385{,}205$, 100\%) & Policy B: Wind-Speed Bins & $\mathbf{13{,}784{,}320 \pm 1{,}438{,}833}$ & $10{,}324{,}129$ & 8.79\% & $346{,}019$ & \textbf{0 (Reference)} \\
 & Policy C: Posterior Quantile & $14{,}307{,}364 \pm 1{,}787{,}258$ & $10{,}179{,}077$ & 9.08\% & $412{,}829$ & $+523{,}044$ ($p=0.85$) \\
 & Policy D: Validation Hybrid & $13{,}789{,}154 \pm 1{,}434{,}721$ & $10{,}339{,}015$ & 8.78\% & $345{,}014$ & $+4{,}834$ (Neutral) \\
 & Policy D10: Pre-Specified Band & $13{,}801{,}696 \pm 1{,}438{,}458$ & $10{,}378{,}012$ & 8.76\% & $342{,}368$ & $+17{,}376$ (Neutral) \\
\midrule
\textbf{Transition Windows} & Policy A: Global Quantile & $5{,}324{,}518 \pm 724{,}901$ & $4{,}525{,}981$ & 3.03\% & $79{,}854$ & $+1{,}005{,}199$ (Worse) \\
($N=139{,}653$, 36.3\%) & Policy B: Wind-Speed Bins & $\mathbf{4{,}319{,}319 \pm 261{,}432}$ & $3{,}417{,}020$ & 8.36\% & $90{,}230$ & \textbf{0 (Reference)} \\
 & Policy C: Posterior Quantile & $4{,}432{,}058 \pm 336{,}724$ & $3{,}566{,}261$ & \textbf{7.24\%} & $\mathbf{86{,}580}$ & $+112{,}739$ ($p=0.48$) \\
 & Policy D: Validation Hybrid & $4{,}325{,}025 \pm 258{,}328$ & $3{,}428{,}552$ & 8.35\% & $89{,}647$ & $+5{,}706$ (Neutral) \\
 & Policy D10: Pre-Specified Band & $4{,}334{,}528 \pm 261{,}962$ & $3{,}455{,}514$ & 8.30\% & $87{,}901$ & $+15{,}209$ (Neutral) \\
\midrule
\textbf{Steady Windows} & Policy A: Global Quantile & $10{,}808{,}254 \pm 1{,}642{,}488$ & $7{,}958{,}035$ & 6.76\% & $285{,}022$ & $+1{,}343{,}253$ (Worse) \\
($N=245{,}552$, 63.8\%) & Policy B: Wind-Speed Bins & $\mathbf{9{,}465{,}001 \pm 1{,}185{,}854}$ & $6{,}907{,}108$ & 9.03\% & $\mathbf{255{,}789}$ & \textbf{0 (Reference)} \\
 & Policy C: Posterior Quantile & $9{,}875{,}306 \pm 1{,}467{,}032$ & $6{,}612{,}816$ & 10.13\% & $326{,}249$ & $+410{,}304$ ($p=0.002$) \\
 & Policy D: Validation Hybrid & $9{,}464{,}130 \pm 1{,}186{,}110$ & $6{,}910{,}464$ & 9.03\% & $255{,}367$ & $-871$ (Neutral) \\
 & Policy D10: Pre-Specified Band & $9{,}467{,}167 \pm 1{,}185{,}697$ & $6{,}922{,}498$ & 9.01\% & $254{,}467$ & $+2{,}166$ (Neutral) \\
\bottomrule
\end{tabularx}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## S4. Cross-Site External-Validity Boundary Probes {.unnumbered}


The 134-turbine WTB site serves as the primary mechanism-identification environment. Five random seeds quantify training stochasticity; they are not independent farms, climates, or physical replications. The three external European facilities must not be presented as uniform replication evidence: their observed effects are heterogeneous. Under the corrected EXP-01 v2 protocol (independent site-frozen point forecasts, pitch withheld at deployment, identical arrival-time information set, paired site-level day-cluster bootstrap, pre-registered $h=6$ primary endpoint), \emph{neither} site yields a significant positive decision gain, and the v2 Penmanshiel penalty is historical; v4 is now also invalidated by forecast/target physical-window mismatch. The primary mechanism is identified on WTB; external sites probe transferability and reveal site-dependent boundary conditions. We do not pool the three external farms into a universal average effect. Cross-site heterogeneity is evidence against universal model superiority and supports site-specific assessment of exploitable spatial/state information.

Tables A8, A8b and A8c are historical records; A8c uses corrected v2 and is itself superseded by the v4 invalidation described in the audit correction notice. No v2 row is current transfer evidence. Table A8 provides the comprehensive Site $\times$ Mechanism specification across all four facilities, reporting physical dimensions, supervisory telemetry, wake context, paired effect sizes, and operational interpretations. Table A8b summarizes the corresponding numerical pre-dispatch reserve screening metrics under local retraining across all four commercial wind farms.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{0.95}
\caption*{\textbf{Table A8c.} Historical EXP-01 v2 benchmark (superseded by v4, which has itself been invalidated for mismatched physical windows). These rows are retained as provenance and are not current transfer evidence; corrected-v2 is superseded/not reinstated, and invalidated v4 cannot restore its authority. Transferred STGQ-Modular (pitch withheld at deployment) against the strong non-parametric \textbf{Site-Local Wspd-Bins} baseline, on the identical arrival-time information set. Paired site-level day-cluster bootstrap, seeds 201--205. Positive $\Delta$PSREI denotes a cost \emph{penalty} for the transferred representation. Source: \texttt{artifacts/external-matched-control-benchmark/v2/external\_matched\_control\_benchmark.csv}.}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l l r r r@{}}
\toprule
Farm & Horizon & Site-Local Baseline (kWh) & $\Delta$PSREI vs. Site-Local (kWh) & $p$ \\
\midrule
\textbf{Penmanshiel} & $h=6$ (primary) & 13,742,849 & $+5{,}321{,}915$ & $0.003$ \\
Penmanshiel & $h=1$ (secondary) & --- & $+6{,}571{,}777$ & $<0.001$ \\
\textbf{Kelmarsh} & $h=6$ (primary) & --- & $+435{,}684$ & $0.196$ \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{8.8pt}\selectfont Note: all five seeds are positive on Penmanshiel $h=6$. No site shows a significant positive decision gain for transferred representations over the site-local 10-bin wind-speed baseline. Fine-tuned STGQ-Modular is $-3{,}527{,}228$ kWh on Penmanshiel $h=6$ (exploratory, not the primary transferred-protocol estimand), and the No-Graph Architectural Control is $+16{,}880{,}326$ kWh ($p<0.001$), which does not by itself establish causal necessity of spatial graph structure (4,865 vs. 110,012 parameters).
\end{table*}
\FloatBarrier
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.4pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A8.} Site $\times$ Mechanism comprehensive external-validity boundary probe ledger across four commercial wind facilities.}
\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}p{\dimexpr .075\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .04\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .10\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .13\linewidth-2\tabcolsep\relax}>{\centering\arraybackslash}p{\dimexpr .06\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .12\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .13\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .15\linewidth-2\tabcolsep\relax}>{\raggedright\arraybackslash}p{\dimexpr .195\linewidth-2\tabcolsep\relax}@{}}
\toprule
Site & $N$ & Period & SCADA Channels & Pitch & Wake Context & Comparison & Paired Effect & Transfer / Replication Interpretation \\
\midrule
\textbf{WTB} & 134 & 245 days ($T=35{,}280$) & 11 channels (Wspd, Wdir, Patv, Pab1--3, etc.) & Yes (raw) & \textbf{High}: Dense multi-row array; strong wake advection & STGQ vs. Global Quantile & $-38\text{k}$ [$-67\text{k}, -12\text{k}$]$^{\ast}$ (band) / $-1.83\text{M}$ (full) & \textbf{Primary Identification Site}: Consequence information is observed; incremental wake necessity and deployment value are not established. \\
\textbf{Penman.} & 14 & 8.6 years (2016--2021) & Standard SCADA (Wspd, Patv, Pab, nacelle, temps) & Yes (99.1\%) & \textbf{Moderate}: Cohesive cluster (14 MM82; WT01--15 ex. WT03) & STGQ vs. Global Quantile \emph{(superseded)} & $-2.14\text{M}$ [$-3.25\text{M}, -1.36\text{M}$]$^{\ast}$ & \textbf{Superseded comparator.} This row compares against an unconditioned global quantile, which is not a sufficient incremental-value comparator. Under the corrected v2 protocol against Site-Local Wspd-Bins, transferred STGQ-Modular incurs $+5{,}321{,}915$ kWh ($p=0.003$, $h=6$); see Table A8c. \\
\textbf{Kelmarsh} & 6 & 9.0 years (2016--2021) & Standard SCADA (Wspd, Patv, Pab, gen. speed) & Yes (97.3\%) & \textbf{Minimal}: Linear 6-turbine micro-array; weak wake redundancy & STGQ vs. Global Quantile & $-40\text{k}$ [$-204\text{k}, +172\text{k}$] ($p=0.85$, crosses 0) & \textbf{Statistically Neutral Probe}: The global-quantile contrast crosses zero; formal equivalence is not established. \\
\textbf{LHB} & 4 & 4 years (2013--2016) & 4 core channels (Wspd, Patv, Pab, Ndir) & Yes (99.2\%) & \textbf{Negligible}: 4-turbine micro-farm; local topography & STGQ vs. Global Quantile & $+43\text{k}$ [$-29\text{k}, +141\text{k}$] (annual) / $+1.01\text{M}$ (rolling) & \textbf{Negative / Overfitting Boundary Probe}: LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity; physical rules remain comparators, not certified deployment choices. \\
\bottomrule
\end{tabularx}
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{0.95}
\caption*{\textbf{Table A8b.} Numerical Pre-Dispatch Reserve Screening Metrics Across Four Commercial Wind Farms under Local Retraining (5 Seeds 201--205, Cost Ratio $\rho=10$).}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l c c c c c@{}}
\toprule
Farm & Units & \shortstack{Continuous Phys.\\(kW$\cdot$h)} & \shortstack{Global Quantile\\(kW$\cdot$h)} & \shortstack{STGQ-Modular\\(kW$\cdot$h)} & \shortstack{$\Delta\text{PSREI}$ vs. Global\\95\% Bootstrap CI} \\
\midrule
\textbf{WTB} & 134 & 842k & 893k & 855k & $-$38k [$-$67k, $-$12k]$^{\ast}$ \\
\textbf{LHB} & 4 & 185k & 188k & 231k & +43k [$-$29k, +141k] \\
\textbf{Kelmarsh} & 6 & 1,025k & 1,065k & 1,025k & $-$40k [$-$204k, +172k] \\
\textbf{Penmanshiel} & 14 & 2,029k & 4,167k & 2,029k & $-$2.14M [$-$3.25M, $-$1.36M]$^{\ast}$ \emph{(superseded; see Table A8c)} \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{8.8pt}\selectfont Note: $^{\ast}p < 0.05$. \textbf{Superseded comparator warning:} this table compares against an unconditioned global quantile baseline, which the scientific contract rules out as sufficient evidence of incremental value. Its Penmanshiel advantage does not survive replacement with the strong Site-Local Wspd-Bins comparator (corrected v2: $+5{,}321{,}915$ kWh penalty, $p=0.003$); see Table A8c. Penmanshiel comprises 14 operational turbines (site numbering spans WT01--WT15, with WT03 not installed/present in SCADA records). LHB exhibits local overfitting; Kelmarsh is neutral.
\end{table*}
\FloatBarrier
```

## La Haute Borne anchor-observability replay audit {.unnumbered}

Table A9 audits the load-bearing channels behind the La Haute Borne cross-site anchor-observability probe. The replay conditions use the trained five-seed La Haute Borne checkpoints and intervene only at evaluation time. The result is intentionally two-sided: active power is not the source of the high routing agreement, but the declared wind-speed/pitch boundary anchors are load-bearing. This delineates the boundary of anchor-observable transfer and blocks any anchor-free discovery or automatic cross-site reserve-use wording.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9.} La Haute Borne anchor-observability replay audit.}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.31\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\raggedright\arraybackslash}X}
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
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Signature-gate identifiability probe {.unnumbered}

Table A9b reports the signature-gate probe that tests whether the MPPT-to-pitch boundary is recoverable when the label-defining channels are withheld from the model. The variants re-train five seeds from a frozen strict cache: `signature_full` removes \texttt{Wspd} and \texttt{Pab\_mean} from both encoder features and the gate anchor while retaining \texttt{Patv}; `signature_core` additionally removes \texttt{Patv}; the shuffled variants apply the same channel masks but permute valid regime labels so the input-label relationship is destroyed. Raw physics arrays are kept intact for evaluation only. The probe shows that the boundary signature survives channel withholding (mean NMI 0.561) and collapses to chance under label permutation (mean NMI 4e-6 for both shuffled variants), ruling out accidental correlation between input statistics and the threshold rule. Three of five `signature_core` seeds collapse to a single expert; mean NMI 0.367 for that variant is therefore reported with median and IQR as an upper envelope rather than a stable operating point.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{3.5pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A9b.} Signature-gate identifiability probe with permuted-label negative controls. Mean $\pm$ SD over five seeds.}
%
\begin{tabularx}{\textwidth}{@{}l c c c >{\raggedright\arraybackslash}X@{}}
\toprule
Probe & RMSE & NMI & ARI & Reading \\
\midrule
Canonical full-anchor & 229.93 $\pm$ 2.50 & 0.7208 & 0.7398 & Train-only clean baseline reference \\
\texttt{signature\_full} & 241.84 $\pm$ 7.19 & 0.5613 $\pm$ 0.0199 & 0.6347 $\pm$ 0.0239 & Boundary recoverable from consequence channels \\
\texttt{signature\_core} & 302.10 $\pm$ 9.16 & 0.3671 $\pm$ 0.0372 (med.\ 0.354) & 0.4342 $\pm$ 0.0378 & Weaker non-power signature; 3/5 seeds expert-collapsed \\
\texttt{signature\_full\_shuffled} & 241.50 $\pm$ 10.25 & 4.0e-6 $\pm$ 2.1e-6 & $-$1.3e-5 $\pm$ 5.3e-5 & Chance level under permuted labels \\
\texttt{signature\_core\_shuffled} & 296.69 $\pm$ 16.22 & 4.7e-6 $\pm$ 3.4e-6 & $-$2.0e-4 $\pm$ 1.7e-4 & Chance level under permuted labels \\
Unconstrained MoE & --- & 0.0140 & --- & Negative control: no declared boundary supervision \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont Expert-usage entropy per seed is archived with the run artifacts; seeds with single-expert usage are flagged before any mean-based wording.
\end{table*}
```

Table A9c reports the same probe on ENGIE La Haute Borne under the identical threshold definition. The full-anchor canonical baseline reaches NMI 0.975 under the same training protocol; `signature_full` retains mean NMI 0.674 (min-seed 0.499) and `signature_core` mean NMI 0.575 with no expert collapse in any seed. Permuting the regime labels under the same withheld-channel mask collapses NMI to 1.92e-04. The boundary signature therefore replicates across farms; the claim is mechanism replication under a shared threshold definition, not parameter transfer.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{3.5pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A9c.} Cross-farm signature-gate replication, ENGIE La Haute Borne. Mean $\pm$ SD over five seeds; per-seed values archived.}
%
\begin{tabularx}{\textwidth}{@{}l c c c >{\raggedright\arraybackslash}X@{}}
\toprule
Probe & RMSE & NMI & ARI & Reading \\
\midrule
\texttt{canonical} & 185.0 $\pm$ 1.9 & 0.9752 $\pm$ 0.0088 & 0.9904 $\pm$ 0.0044 & Full-anchor reference \\
\texttt{signature\_full} & 185.1 $\pm$ 1.4 & 0.6743 $\pm$ 0.1209 & 0.7401 $\pm$ 0.1604 & Signature transfers; min-seed 0.499 \\
\texttt{signature\_core} & 188.0 $\pm$ 1.0 & 0.5750 $\pm$ 0.0423 & 0.6270 $\pm$ 0.0638 & Non-power signature transfers; 0/5 collapsed \\
\texttt{signature\_full\_shuffled} & 185.4 $\pm$ 1.2 & 1.92e-04 $\pm$ 8.90e-05 & 5.19e-04 $\pm$ 2.86e-03 & Chance level under permuted labels \\
\bottomrule
\end{tabularx}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont LHB is a four-turbine Senvion MM82 farm with directly observed pitch (99.2\% coverage) and no wake graph support (wake score identically zero). RMSE is nearly invariant to channel withholding, so the signature effect is decoupled from forecast accuracy.
\end{table*}
```

Table A9d reports the same probe on two farms with partial pitch observability. Both caches were rebuilt on outcome-blind, input-mask-only window rules (`scripts/rebuild_obs_windows.py`): the earliest contiguous 245-day window with daily pitch coverage at least 0.70 and daily regime-valid at least 0.70 for Penmanshiel (day 720; Senvion MM82), and the earliest window with daily regime-valid at least 0.70 for Kelmarsh (day 120; Senvion MM92). Permuted-label controls collapse to chance at both farms, and the withheld-channel variants stay above chance across both commercial wind farms, so these results motivate graded representation checks, not a deployment admission rule.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9d.} Signature-gate probe on partial-pitch-observability farms. Mean$\pm$sd over five seeds; per-seed values archived.}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Signature strength is evaluated on reconstructed operating windows across both commercial wind farms. The graded reading attributes the recovered boundary signal to consequence-channel quality (reactive power, pitch dispersion, temperatures) rather than to pitch sensors alone. Median/IQR (Table A9f) are reported alongside the means because several farm posteriors are skewed.
\end{table*}
```

Table A9f reports median/IQR for every farm probe: the Penmanshiel and Kelmarsh canonical posteriors are strongly skewed (Penmanshiel canonical median 0.985 versus mean 0.699), so median-based readings are the honest summary for those cells.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
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
\fontsize{8.0pt}{9.6pt}\selectfont The window scan (Table A9e) passes at 4/4 windows with per-seed pass-rate 1.0 (3/3 seeds above the 0.20 criterion in every window).
\end{table*}
```

Table A9e reports two robustness additions. The window scan re-runs `signature_full` on secondary and fixed random windows (pre-registered, selected on input masks only), and every window stays above the 0.20 criterion. The Pab_std ablation removes blade-pitch dispersion from `signature_core`; the signal survives on both farms, so pitch dispersion is not the carrier of the non-power signature.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9e.} Window-robustness scan and Pab\_std ablation (signature\_full / signature\_core\_no\_pab\_std, mean$\pm$sd).}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Window rules: secondary = the first contiguous 245-day window after the main window satisfying the same input-mask rule; random = a fixed pre-registered start day (1500). All runs are five seeds except the scan rows, which are three seeds. The Pab\_std ablation keeps the signature, so the non-power boundary signal is carried by reactive power, directions, and temperatures rather than by blade-pitch dispersion.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## External validation and cross-farm evidence demarcation {.unnumbered}

To ensure complete methodological transparency and prevent over-generalization across disparate commercial wind farms, we explicitly disentangle three separate lines of external evidence:

1. **Within-plant local retraining (ENGIE La Haute Borne, Kelmarsh, Penmanshiel):** All probe evaluations (Tables A9a--A9f) and chronological dispatch replays represent models retrained locally under site-specific rated aerodynamic wind speeds ($v_{\mathrm{rated}} = 12.5\text{ m s}^{-1}$ for Kelmarsh MM92 and $14.5\text{ m s}^{-1}$ for Penmanshiel MM82). These results demonstrate neural architecture adaptability to site-specific aerodynamic parameters when local training data is available, rather than zero-shot cross-farm generalizability.
2. **Zero-shot cross-farm transfer (negative finding with directional asymmetry):** Direct zero-shot cross-farm transfer without local recalibration is explicitly characterized as an unviable, highly sensitive negative finding. Representation transfer between Kelmarsh and Penmanshiel exhibits severe directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.752$--$0.770$ vs. Penmanshiel $\to$ Kelmarsh $0.341$--$0.505$, pooled mean NMI $0.557$; `external_wind_guard.json`), indicating that directional transfer asymmetry supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer across distinct turbine makes and geometries.
3. **Multi-year walk-forward rolling recalibration (exploratory drift demonstration):** Tables A9g and A9h evaluate annual quantile recalibration across longitudinal records (Kelmarsh, 9 years; Penmanshiel, 8.6 years) under IEC 61400-12-1 air-density calibration using a 2-year sliding training window. Data-integrity auditing identified temporal overlap in historical rolling folds (e.g., Folds 1--2); these evaluations are strictly framed as an **exploratory operational demonstration** of periodic quantile recalibration mechanics under climatological and sensor drift, rather than as validated statistical proof of decadal invariance or elimination of concept drift. On Kelmarsh, 6 of 7 rolling folds strictly exclude zero ($p < 0.05$), with mean annual savings of $-1.025 \text{ Million kWh/year}$. On Penmanshiel, 4 mature operational folds (2020--2023) strictly exclude zero ($p < 0.05$), with mean annual savings of $-2.029 \text{ Million kWh/year}$.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9g.} Kelmarsh 9-year walk-forward rolling recalibration audit under IEC 61400-12-1 density calibration ($\rho=10$, 5 seeds).}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Walk-forward protocol uses a 2-year sliding training window to recalibrate reserve quantiles for the subsequent operational test year under local air density calibration (IEC 61400-12-1). Six of seven consecutive rolling folds strictly exclude zero. Script: \texttt{scripts/eval\_external\_rolling\_reserve.py}.
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A9h.} Penmanshiel 8.6-year walk-forward rolling recalibration audit under IEC 61400-12-1 density calibration ($\rho=10$, 5 seeds).}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Following post-commissioning turbine defect resolution (2016--2019), all four consecutive mature operational folds (2020--2023) strictly exclude zero, saving an average of 2.029 Million kWh/year. Script: \texttt{scripts/eval\_penmanshiel\_rolling\_reserve.py}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## S5. PCC-Level Reserve Allocation {.unnumbered}


To address the industrial power engineering reality that grid operators dispatch and clear reserves at the Point of Common Coupling (PCC) bus rather than at individual turbine terminals, we aggregate actual and predicted power across all 134 WTB wind turbines ($P_{\mathrm{farm}}(t, h) = \sum_{i \in \mathcal{V}_t} P_{i,t}$) using strictly causal online masking at anchor time $t=0$. Table A11f evaluates whether the reserve-screening surrogate reduction of the jointly-learned boundary-risk posterior survives the spatial cancellation of individual turbine forecast errors (portfolio smoothing effect). Across the full operational envelope, joint posterior aggregate quantile allocation saves $-2.32\text{M kWh}$ (95\% bootstrap CI $[-6.07\text{M}, +1.73\text{M}]$) against the global PCC quantile and $-1.37\text{M kWh}$ (CI $[-6.33\text{M}, +2.82\text{M}]$) against the Gaussian parametric baseline. In transitional operating regimes where 10\% to 90\% of turbines are pitching, the joint posterior saves $-1.33\text{M kWh}$ (CI $[-1.68\text{M}, -1.07\text{M}]$, strictly excluding zero) compared to continuous physical pitch rules, describing a surrogate contrast against physical pitch conditioning. Full-envelope intervals cross zero; transition bootstrap zero-exclusion has the exact seed-test floor reported below. These observations neither identify a necessary smoothing mechanism nor certify a deployed reserve policy.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11f.} Wind farm Point of Common Coupling (PCC) aggregated reserve allocation under 134-turbine spatial portfolio smoothing ($\rho=10$, 5 seeds, WTB test split, strictly causal issue-time aggregation).}
%
\setlength{\tabcolsep}{2.5pt}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.19\linewidth} >{\raggedright\arraybackslash}p{0.17\linewidth} >{\raggedright\arraybackslash}p{0.17\linewidth} r r c c}
\toprule
Regime / Condition & Strategy & Baseline & $\Delta\text{Cost}$ (kWh) & \shortstack{95\% Seed\\Bootstrap CI} & \shortstack{Seed CI\\Excludes Zero} & \shortstack{Exact Seed\\$p$-value} \\
\midrule
Full Operational Envelope & Joint Posterior Aggregate & Global PCC Quantile & -2.32M & [-6.07M, +1.73M] & no & 0.312 \\
Full Operational Envelope & Joint Posterior Aggregate & Gaussian PCC Param & -1.37M & [-6.33M, +2.82M] & no & 0.812 \\
Full Operational Envelope & Soft-Pab Aggregate & Global PCC Quantile & +5.61M & [+3.14M, +8.56M] & \textbf{yes} & 0.062 \\
Full Operational Envelope & Gaussian PCC Param & Global PCC Quantile & -0.95M & [-2.31M, +0.47M] & no & 0.312 \\
\midrule
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Soft-Pab Aggregate & -1.33M & [-1.68M, -1.07M] & \textbf{yes} & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Soft-Pab Aggregate & Global PCC Quantile & +1.43M & [+1.02M, +1.78M] & \textbf{yes} & 0.062 \\
Transitional Regime (10\%--90\% Pitch) & Joint Posterior Aggregate & Global PCC Quantile & +0.10M & [-0.31M, +0.51M] & no & 1.000 \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Evaluated on aggregated wind plant active power at the PCC bus summing over turbines online at anchor time $t=0$ ($P_{\mathrm{farm}} = \sum_{i \in \mathcal{V}_0} P_i$). The 95\% bootstrap CI ($B=20{,}000$ resamples) and exact Wilcoxon signed-rank test ($p=2^{-4}=0.062$ theoretical permutation floor) are two inferential summaries of the SAME $n=5$ seed-level replication (training-initialization uncertainty across seeds 201--205). Because $n=5$ is small, bootstrap zero-exclusion alone is not interpreted as conventional population-level statistical significance without acknowledging the exact non-parametric sample-size floor. Script: \texttt{scripts/eval\_farm\_aggregate\_reserve.py}, artifacts in \texttt{artifacts/farm\_aggregate\_reserve\_20260905/}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Exploratory Wind-BESS rolling dispatch simulation {.unnumbered}

As a separate exploratory model of balancing, the archive reports a receding-horizon Model Predictive Control (MPC) dispatch simulation of a co-located Battery Energy Storage System (BESS) at the Point of Common Coupling (PCC) bus of the 134-turbine WTB wind farm over the entire 35-day test split across all 5 random seeds (201--205). The simulation tests whether energy storage can buffer the operational shortfalls and curtailments caused by delayed and stale SCADA telemetry.

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
&E[k+j+1] = E[k+j] + (\eta_{\mathrm{ch}} p_{\mathrm{ch}}[k+j] - \eta_{\mathrm{dis}}^{-1} p_{\mathrm{dis}}[k+j]) \Delta t, \\
&\mathrm{SoC}_{\min} E_{\mathrm{cap}} \le E[k+j] \le \mathrm{SoC}_{\max} E_{\mathrm{cap}}, \\
&0 \le p_{\mathrm{ch}}[k+j] \le P_{\mathrm{bess}}^{\max}, \\
&0 \le p_{\mathrm{dis}}[k+j] \le P_{\mathrm{bess}}^{\max},
\end{align}
where $\tilde{w}[k] = w_{\mathrm{act}}[k]$ incorporates immediate real-time feedback at step 0, while $\tilde{w}[k+j] = w_{\mathrm{fc}}[k+j]$ ($j \ge 1$) follows the lookahead trajectory under latency $\tau \in \{0, 10, 30, 60\}\text{ min}$. Standard utility parameters are used: $E_{\mathrm{cap}} = 20\,\text{MWh}$, $P_{\mathrm{bess}}^{\max} = 10\,\text{MW}$ (0.5C rate), $\eta_{\mathrm{ch}} = \eta_{\mathrm{dis}} = 0.95$, operating band $\mathrm{SoC} \in [0.10, 0.90]$, shortage penalty $c_{\mathrm{short}} = \$150/\text{MWh}$, curtailment cost $c_{\mathrm{curt}} = \$20/\text{MWh}$, and cell wear degradation $c_{\mathrm{deg}} = \$15/\text{MWh}$.

*Analytical Equivalence between Receding-Horizon LP and Step Heuristic:* In Table A11-BESS, the receding-horizon LP and the instantaneous heuristic achieve identical dispatch metrics across all latency regimes. This numerical equivalence arises analytically: because utility penalty rates ($c_{\mathrm{short}}, c_{\mathrm{curt}}, c_{\mathrm{deg}}$) are stationary over the lookahead horizon and dispatch commitments track the receding forecast ($w_{\mathrm{fc}}[k+j] = c_{\mathrm{sched}}[k+j]$ for $j \ge 1$), zero planned imbalance is anticipated at future steps. Consequently, the multi-period LP reduces to an optimal greedy dispatch decision at step 0, describing the recorded stationary-price, zero-future-gap setup only. This simulation does not establish general MPC equivalence, field safety or causal necessity of the upstream representation.

Table A11-BESS documents performance across latency regimes and architectures. Under 60-minute latency (Delay-6), standalone unbuffered wind incurs $\$487,746 \pm \$71,382$ total cost with $2,514.9 \pm 633.1\,\text{MWh}$ shortage and $38.82\% \pm 5.01\%$ violation rate. Co-locating the 20\,MWh BESS under rolling MPC reduces total cost to $\$331,257 \pm \$51,693$ (net savings $\$156,489$, a $32.1\%$ reduction), mitigates $45.7\% \pm 7.2\%$ of shortage energy ($1,401.2\,\text{MWh}$ remaining), and compresses violations to $20.58\% \pm 7.83\%$ across 58.5 equivalent full cycles (EFC, 2,341.2\,MWh throughput).

Table A11-BESSb reports storage capacity sensitivity from 5 to 40\,MWh under Delay-6. As capacity scales from 5\,MWh (0.5C) to 40\,MWh (20\,MW, 0.5C), shortage mitigation scales from $15.3\%$ to $64.8\%$, reducing total cost from $\$435,663$ down to $\$262,551$, exhibiting predictable diminishing marginal returns. Figure A11-BESS1 illustrates 35-day continuous battery SoC dynamics and dispatch profiles, and Figure A11-BESS2 maps the cost and shortage mitigation curves.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11-BESS.} Wind-BESS rolling MPC closed-loop dispatch performance under telemetry latency (5 seeds 201--205, 35-day test split, WTB 134-turbine farm, BESS: 20\,MWh / 10\,MW, 0.5C, values: Mean $\pm$ SD).}
%
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llcccccc@{}}
\toprule
\shortstack{Telemetry\\Regime} & \shortstack{Dispatch\\Architecture} & \shortstack{Total Cost\\(\$)} & \shortstack{Shortage\\(MWh)} & \shortstack{Curtailment\\(MWh)} & \shortstack{Throughput\\(MWh)} & \shortstack{Violation\\Rate} & \shortstack{Shortage\\Mitigation} \\
\midrule
\shortstack[l]{Clean\\(0 min)} & \shortstack[l]{Standalone Wind\\(No BESS)} & $134,033 \pm 17,313$ & $434.5 \pm 171.7$ & $3,443.1 \pm 1,686.0$ & --- & $29.80\% \pm 6.72\%$ & Baseline \\
 & \shortstack[l]{Wind + BESS\\Heuristic} & $83,135 \pm 26,855$ & $72.4 \pm 58.5$ & $3,039.7 \pm 1,797.6$ & $765.5 \pm 237.3$ & $3.49\% \pm 3.84\%$ & $85.6\% \pm 7.5\%$ \\
 & \shortstack[l]{\textbf{Wind + BESS}\\\textbf{Rolling MPC}} & $83,135 \pm 26,855$ & $72.4 \pm 58.5$ & $3,039.7 \pm 1,797.6$ & $765.5 \pm 237.3$ & $3.49\% \pm 3.84\%$ & $85.6\% \pm 7.5\%$ \\
\midrule
\shortstack[l]{Delay-1\\(10 min)} & \shortstack[l]{Standalone Wind\\(No BESS)} & $200,116 \pm 19,901$ & $823.3 \pm 304.4$ & $3,830.7 \pm 1,547.1$ & --- & $32.11\% \pm 6.78\%$ & Baseline \\
 & \shortstack[l]{Wind + BESS\\Heuristic} & $112,871 \pm 15,980$ & $202.5 \pm 118.4$ & $3,144.6 \pm 1,741.4$ & $1,307.0 \pm 391.2$ & $5.65\% \pm 4.37\%$ & $77.5\% \pm 7.4\%$ \\
 & \shortstack[l]{\textbf{Wind + BESS}\\\textbf{Rolling MPC}} & $112,871 \pm 15,980$ & $202.5 \pm 118.4$ & $3,144.6 \pm 1,741.4$ & $1,307.0 \pm 391.2$ & $5.65\% \pm 4.37\%$ & $77.5\% \pm 7.4\%$ \\
\midrule
\shortstack[l]{Delay-3\\(30 min)} & \shortstack[l]{Standalone Wind\\(No BESS)} & $321,873 \pm 46,937$ & $1,539.5 \pm 486.1$ & $4,547.3 \pm 1,356.4$ & --- & $35.65\% \pm 5.99\%$ & Baseline \\
 & \shortstack[l]{Wind + BESS\\Heuristic} & $191,042 \pm 20,096$ & $608.5 \pm 280.9$ & $3,519.0 \pm 1,578.9$ & $1,959.2 \pm 432.3$ & $11.45\% \pm 7.37\%$ & $62.6\% \pm 8.3\%$ \\
 & \shortstack[l]{\textbf{Wind + BESS}\\\textbf{Rolling MPC}} & $191,042 \pm 20,096$ & $608.5 \pm 280.9$ & $3,519.0 \pm 1,578.9$ & $1,959.2 \pm 432.3$ & $11.45\% \pm 7.37\%$ & $62.6\% \pm 8.3\%$ \\
\midrule
\shortstack[l]{Delay-6\\(60 min)} & \shortstack[l]{Standalone Wind\\(No BESS)} & $487,746 \pm 71,382$ & $2,514.9 \pm 633.1$ & $5,525.7 \pm 1,200.8$ & --- & $38.82\% \pm 5.01\%$ & Baseline \\
 & \shortstack[l]{Wind + BESS\\Heuristic} & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $20.58\% \pm 7.83\%$ & $45.7\% \pm 7.2\%$ \\
 & \shortstack[l]{\textbf{Wind + BESS}\\\textbf{Rolling MPC}} & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $20.58\% \pm 7.83\%$ & $45.7\% \pm 7.2\%$ \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont Evaluated via exact receding-horizon LP optimization using HiGHS with 1-hour lookahead ($H=6$). Because penalty rates are stationary and lookahead commitment gap is zero, rolling LP and step heuristic achieve analytically equivalent step decisions. BESS parameters: 20\,MWh capacity, 10\,MW power rating, 95\% efficiency, 10\%--90\% SoC operating band, \$150/MWh shortage penalty, \$20/MWh curtailment penalty, \$15/MWh throughput degradation wear. Script: \texttt{scripts/run\_wind\_bess\_simulation.py}, artifacts in \texttt{artifacts/wind\_bess\_simulation/}.
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11-BESSb.} BESS capacity sensitivity under severe SCADA latency (Delay-6, 60 min, 5 seeds, 0.5C rate).}
%
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}cccccccc@{}}
\toprule
\shortstack{Capacity\\(MWh)} & \shortstack{Power\\(MW)} & \shortstack{Total Cost\\(\$)} & \shortstack{Shortage\\(MWh)} & \shortstack{Curtailment\\(MWh)} & \shortstack{Throughput\\(MWh)} & EFC & \shortstack{Shortage\\Mitigation} \\
\midrule
5.0 & 2.5 & $435,663 \pm 65,319$ & $2,144.2 \pm 588.8$ & $5,116.5 \pm 1,251.3$ & $779.8 \pm 100.0$ & $78.0 \pm 10.0$ & $15.3\% \pm 2.6\%$ \\
10.0 & 5.0 & $394,360 \pm 60,410$ & $1,850.3 \pm 552.9$ & $4,792.4 \pm 1,291.8$ & $1,397.9 \pm 178.6$ & $69.9 \pm 8.9$ & $27.4\% \pm 4.6\%$ \\
20.0 & 10.0 & $331,257 \pm 51,693$ & $1,401.2 \pm 488.8$ & $4,298.2 \pm 1,364.2$ & $2,341.2 \pm 317.5$ & $58.5 \pm 7.9$ & $45.7\% \pm 7.2\%$ \\
30.0 & 15.0 & $290,382 \pm 39,599$ & $1,110.2 \pm 399.2$ & $3,979.5 \pm 1,465.2$ & $2,950.9 \pm 509.2$ & $49.2 \pm 8.5$ & $57.1\% \pm 6.2\%$ \\
40.0 & 20.0 & $262,551 \pm 30,730$ & $912.0 \pm 332.9$ & $3,763.5 \pm 1,537.7$ & $3,365.0 \pm 649.1$ & $42.1 \pm 8.1$ & $64.8\% \pm 5.4\%$ \\
\bottomrule
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont All configurations maintain 0.5C power rating ($P_{\mathrm{bess}}^{\max} = 0.5 \times E_{\mathrm{cap}}$). Diminishing marginal returns appear beyond 20\,MWh. Script: \texttt{scripts/run\_wind\_bess\_simulation.py}.
\end{table*}
```

```{=latex}
\begin{figure*}[!t]
\centering
\includegraphics[width=0.92\textwidth]{artifacts/paper_assets/figures/fig_bess_soc_dynamics.png}
\caption*{\textbf{Figure A11-BESS1.} Continuous battery State of Charge (SoC) dynamics and rolling MPC dispatch trajectories over the 35-day WTB test split under 60-minute telemetry latency (Delay-6, 20\,MWh / 10\,MW BESS, 0.5C). Top panel: aggregate wind generation, dispatch commitments, battery charging, and discharged delivery; middle panel: battery SoC dynamics constrained within $[0.10, 0.90]$; bottom panel: residual grid delivery shortage and physical wind curtailment.}
\end{figure*}
```

```{=latex}
\begin{figure*}[!t]
\centering
\includegraphics[width=0.82\textwidth]{artifacts/paper_assets/figures/fig_bess_capacity_sensitivity.png}
\caption*{\textbf{Figure A11-BESS2.} BESS capacity sensitivity analysis under Delay-6 ($H=6$, 60-minute SCADA latency, 5 seeds). Left: total operational dispatch cost (\$) vs. battery capacity (5 to 40\,MWh at 0.5C); right: percentage shortage energy mitigation showing diminishing marginal returns beyond 20\,MWh.}
\end{figure*}
```

```{=latex}
\FloatBarrier
```

## Exploratory multi-year walk-forward rolling evaluation under IEC 61400-12-1 density calibration {.unnumbered}

To examine the operational mechanics of periodic quantile recalibration under turbine aging and multi-year climate variations, Table A11g documents an exploratory walk-forward rolling reserve evaluation across two commercial European wind plants (Kelmarsh: 9 full years, 2016--2024, 6 turbines; Penmanshiel: 8.6 full years, 2016--2024, 14 operational turbines, numbered WT01--WT15 excluding WT03) spanning an aggregate 17.6 machine-operating years under IEC 61400-12-1 density normalization, across penalty ratios $\rho \in \{5, 10, 20\}$. *Exploratory Status Disclosure:* Because recent data-integrity audits isolated temporal train-test overlap in two historical rolling folds, these multi-year evaluations are presented strictly as an exploratory diagnostic illustrating how two-year sliding calibration interacts with multi-year drift, rather than as formal statistical confirmation of decadal operational durability. Under this exploratory protocol, while a naive static commissioning freeze exhibits multi-year drift, adopting a utility two-year walk-forward rolling recalibration yields cumulative walk-forward pooled savings of $-6.19\text{M kWh}$ on Kelmarsh (95\% bootstrap CI $[-7.52\text{M}, -4.77\text{M}]$) and $-4.34\text{M kWh}$ on Penmanshiel (CI $[-8.24\text{M}, -0.44\text{M}]$) at standard $\rho=10$. Across shortage penalties, the results reveal an operational sensitivity envelope: at Kelmarsh, the soft gate maintains cost deltas over the unconditioned global quantile across $\rho \in \{5, 10, 20\}$, but under extreme shortage penalty ($\rho=20$) the physical rule surpasses the soft-gate by $+0.95\text{M kWh}$ (CI $[+0.15\text{M}, +1.65\text{M}]$); conversely, at Penmanshiel, the soft gate leads the physical rule by $-7.51\text{M kWh}$ (CI $[-13.51\text{M}, -1.25\text{M}]$) at $\rho=20$, while crossing zero versus the global quantile ($-5.15\text{M kWh}$, CI $[-12.47\text{M}, +2.17\text{M}]$) due to tail conservatism.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.00}
\caption*{\textbf{Table A11g.} Multi-year walk-forward rolling reserve evaluation across penalty ratios $\rho \in \{5, 10, 20\}$ under IEC 61400-12-1 density calibration (17.6 cumulative turbine-operating years, 5 seeds).}
%
\setlength{\tabcolsep}{3pt}
\begin{tabularx}{\linewidth}{l >{\raggedright\arraybackslash}p{0.18\linewidth} c >{\raggedright\arraybackslash}p{0.16\linewidth} r r c >{\raggedright\arraybackslash}X}
\toprule
Farm & Protocol & $\rho$ & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & Operational Finding \\
\midrule
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 5 & Global Quantile & -7.77M & [-9.34M, -5.55M] & \textbf{yes} ($p < 0.05$) & Exploratory stored contrast \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 5 & Soft-Pab Aggregate & -0.37M & [-1.24M, +0.81M] & no & Competitive with physical pitch rule \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 10 & Global Quantile & -6.19M & [-7.52M, -4.77M] & \textbf{yes} ($p < 0.05$) & Baseline utility operating condition \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 10 & Soft-Pab Aggregate & -2.67M & [-4.22M, -1.14M] & \textbf{yes} ($p < 0.05$) & Surpasses physical rule under nominal penalty \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 20 & Global Quantile & -3.16M & [-3.95M, -2.36M] & \textbf{yes} ($p < 0.05$) & Persistent savings vs unconditioned global rule \\
Kelmarsh (9 yrs) & Walk-Forward Rolling Pooled & 20 & Soft-Pab Aggregate & +0.95M & [+0.15M, +1.65M] & \textbf{yes} ($p < 0.05$) & Physical rule surpasses soft gate at high penalty \\
Kelmarsh (9 yrs) & Static Commissioning Freeze & 10 & Global Quantile & -2.24M & [-7.12M, +1.49M] & no & Static freeze without recalibration shows multi-year drift \\
\midrule
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 5 & Global Quantile & -4.23M & [-7.49M, -1.93M] & \textbf{yes} ($p < 0.05$) & Exploratory stored contrast \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 5 & Soft-Pab Aggregate & -4.37M & [-7.14M, -1.44M] & \textbf{yes} ($p < 0.05$) & Significantly outperforms physical pitch rule \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 10 & Global Quantile & -4.34M & [-8.24M, -0.44M] & \textbf{yes} ($p < 0.05$) & Baseline utility operating condition \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 10 & Soft-Pab Aggregate & -5.85M & [-9.35M, -1.97M] & \textbf{yes} ($p < 0.05$) & Surpasses physical rule across multi-year horizon \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 20 & Global Quantile & -5.15M & [-12.47M, +2.17M] & no & Crosses zero vs global due to tail conservatism \\
Penmanshiel (8.6 yrs) & Walk-Forward Rolling Pooled & 20 & Soft-Pab Aggregate & -7.51M & [-13.51M, -1.25M] & \textbf{yes} ($p < 0.05$) & Soft gate leads physical rule by 7.51M \\
Penmanshiel (8.6 yrs) & Static Commissioning Freeze & 10 & Global Quantile & -13.83M & [-112.37M, +91.94M] & no & Static freeze without recalibration shows multi-year drift \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Evaluated with IEC 61400-12-1 barometric air density normalization across 5 seeds. Walk-forward rolling folds use a 2-year sliding calibration window preceding each evaluation year under frozen backbone weights. Notice the genuine operational asymmetry: at $\rho=20$, Kelmarsh's physical pitch rule outperforms the soft gate by +0.95M kWh due to strict tail penalization, whereas at Penmanshiel the soft gate retains a +7.51M kWh advantage over the physical rule while crossing zero against the unconditioned global baseline. Script: \texttt{scripts/aggregate\_iec\_density\_eval.py}, artifacts in \texttt{artifacts/iec\_density\_rolling\_eval/}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## La Haute Borne rolling evaluation and physical boundary disclosure {.unnumbered}

Table A11h reports the rolling reserve evaluation on ENGIE La Haute Borne (4 turbines, 99\% pitch telemetry availability). Unlike the utility-scale commercial plants, LHB constitutes a miniature clean-site physical boundary condition. In walk-forward rolling pooled evaluation across quarterly folds (Q1--Q3), the soft gate incurs a positive cost delta of $+1.01\text{M kWh}$ (95\% bootstrap CI $[+0.29\text{M}, +1.76\text{M}]$, strictly excluding zero) versus the global quantile and $+0.92\text{M kWh}$ (CI $[+0.26\text{M}, +1.61\text{M}]$) versus the continuous physical pitch rule. Examination across individual quarters reveals an empirical quantile variance amplification mechanism under acute seasonal drift: in benign Q1 (+6.6k kWh, CI $[-10.4\text{k}, +29.7\text{k}]$) and Q2 (+31.8k kWh, CI $[-48.4\text{k}, +125.7\text{k}]$), cost deltas are small and cross zero; in Q3, sharp autumn wind-regime transition concentrates prediction errors into short calibration slices ($+968.1\text{k kWh}$, CI $[+313.3\text{k}, +1,623.0\text{k}]$). In contrast, expanding calibration to a 180-day annual window (`pooled_annual_full`) stabilizes empirical quantiles, compressing the cost difference to $+43\text{k kWh}$ (CI $[-28.7\text{k}, +141.2\text{k}]$, strictly crossing zero) against global quantiles and $+39.2\text{k kWh}$ against physical pitch rules. These historical contrasts motivate the questions in Table A14. They do not isolate PCC smoothing or site size as necessary causes, nor certify either posterior or physical rules for deployment.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11h.} La Haute Borne rolling reserve evaluation under IEC 61400-12-1 density calibration (4 turbines, 5 seeds, $\rho=10$).}
%
\setlength{\tabcolsep}{3.5pt}
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.16\linewidth} >{\raggedright\arraybackslash}p{0.18\linewidth} >{\raggedright\arraybackslash}p{0.16\linewidth} r r c >{\raggedright\arraybackslash}X}
\toprule
Evaluation Window & Protocol & Baseline & $\Delta\text{Cost}$ (kWh) & 95\% Bootstrap CI & Excludes Zero & Operational Physical Finding \\
\midrule
Walk-Forward Rolling Pooled & Quarterly Rolling Folds (Q1--Q3) & Global Quantile & +1.01M & [+0.29M, +1.76M] & \textbf{yes} ($p < 0.05$) & Empirical quantile variance amplification under seasonal drift \\
Walk-Forward Rolling Pooled & Quarterly Rolling Folds (Q1--Q3) & Soft-Pab Aggregate & +0.92M & [+0.26M, +1.61M] & \textbf{yes} ($p < 0.05$) & Physical pitch rule achieves lower cost under complete pitch availability \\
Rolling Quarter 1 & 1-Quarter Test (Spring) & Global Quantile & +6.6k & [-10.4k, +29.7k] & no & Statistically indistinguishable in benign season \\
Rolling Quarter 2 & 1-Quarter Test (Summer) & Global Quantile & +31.8k & [-48.4k, +125.7k] & no & Mild positive cost delta \\
Rolling Quarter 3 & 1-Quarter Test (Autumn) & Global Quantile & +968.1k & [+313.3k, +1,623.0k] & \textbf{yes} ($p < 0.05$) & Sharp seasonal shift concentrates short-slice quantile error \\
\midrule
Annual 180-Day Window & 180-Day Calib / Full Test Remainder & Global Quantile & +43k & [-28.7k, +141.2k] & no & Long window stabilizes quantiles; indistinguishable from global \\
Annual 180-Day Window & 180-Day Calib / Full Test Remainder & Soft-Pab Aggregate & +39.2k & [-27.7k, +120.8k] & no & Re-establishes parity with continuous physical pitch rule \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Evaluated with IEC 61400-12-1 density correction across 5 seeds. This historical table motivates the prospective questions in Table A14; it does not establish physical admission boundaries: for a miniature 4-turbine site with 99\% complete, pristine pitch sensors, no Point of Common Coupling (PCC) spatial smoothing cancellation exists. Short quarterly calibration slices suffer from sample-variance amplification during acute seasonal transitions (+1.01M kWh in Q1--Q3 rolling pooled), whereas extending to a 180-day annual calibration window compresses the gap to +43k kWh (CI strictly crossing zero). These historical contrasts do not identify PCC smoothing or telemetry sparsity as necessary conditions for useful posterior policies. Script: \texttt{scripts/aggregate\_iec\_density\_eval.py}, artifacts in \texttt{artifacts/iec\_density\_rolling\_eval/}.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Multi-year gate representation stability under frozen backbone {.unnumbered}

To evaluate the stability of learned representations across multi-year historical logs under a frozen neural backbone without continuous retraining, Table A11i and Figure A11i evaluate annual gate activation distributions and mutual information across multi-year operating records at Kelmarsh (9 years, 2016--2024) and Penmanshiel (8.6 years, 2016--2024) across 5 seeds. For each operational year $y$, the gate activations are compared against the commissioning baseline year (Year 1, 2016) using both the 1D Wasserstein distance on blade-pitch routing probabilities $\mathcal{W}_1(P_y(p_{\mathrm{pitch}}), P_1(p_{\mathrm{pitch}}))$ and the mean Wasserstein distance across all four expert regime probabilities $\bar{\mathcal{W}}_1$. Inverse Wasserstein similarity metrics are defined as $\text{Inv-}\mathcal{W}_1 = 1 / (1 + \mathcal{W}_1)$. Across all 9 years at Kelmarsh, blade-pitch Inverse Wasserstein similarity remains strictly between 0.995 and 0.998 ($\mathcal{W}_1 \le 0.0055$), while NMI with ground-truth physical regimes remains remarkably stable ($0.250$ to $0.282$). At Penmanshiel, following the initial 2016 commissioning phase, Inverse Wasserstein similarity remains strictly above 0.990 ($\mathcal{W}_1 \le 0.0098$). This indicates that the underlying spatio-temporal neural backbone maintains stable physical state representations without catastrophic representation collapse across multi-year logs, but does not isolate whether changes in decision performance arise from quantile drift, representation changes or other site/time differences.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.5pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A11i.} Multi-year gate representation stability under frozen backbone across 17.6 cumulative turbine-operating years (5 seeds).}
%
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l c c l c c c c@{}}
\toprule
Farm & Year & Calendar & \shortstack[l]{Operational\\Phase} & \shortstack{Ground-Truth\\NMI} & \shortstack{$\mathcal{W}_1$\\$(p_{\mathrm{pitch}})$} & \shortstack{$\text{Inv-}\mathcal{W}_1$\\$(p_{\mathrm{pitch}})$} & \shortstack{$\text{Inv-}\bar{\mathcal{W}}_1$\\$(\text{all})$} \\
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
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont Evaluated under frozen neural backbone weights calibrated at initial commissioning (Year 1, 2016) across 5 seeds. $\mathcal{W}_1(p_{\mathrm{pitch}})$ measures the 1D Wasserstein distance between the annual distribution of blade-pitch routing probabilities $P_y(p_{\mathrm{pitch}})$ and the baseline commissioning distribution $P_1(p_{\mathrm{pitch}})$. $\text{Inv-}\mathcal{W}_1 = 1 / (1 + \mathcal{W}_1)$ indicates representation preservation (1.0 = identical). Script: \texttt{scripts/remote\_gate\_representation\_decay.py}, artifacts in \texttt{artifacts/multiyear\_gate\_representation\_audit/}.
\end{table*}
```

```{=latex}
\begin{figure}[H]
\centering
\includegraphics[width=\columnwidth]{artifacts/paper_assets/figures/figure_gate_representation_stability.pdf}
\caption*{\textbf{Figure A11i.} Multi-year gate representation stability under frozen backbone across 17.6 cumulative turbine-operating years (5 seeds). (a) Kelmarsh representation similarity ($\text{Inv-}\mathcal{W}_1 \ge 0.995$); (b) Penmanshiel representation similarity ($\text{Inv-}\mathcal{W}_1 \ge 0.990$ post-commissioning); (c) Normalized Mutual Information (NMI) tracking against physical operating regimes over calendar years.}
\end{figure}
```

```{=latex}
\FloatBarrier
```

## Ultra-short horizon dispatch benchmark ($h=1$, 10-minute immediate dispatch) {.unnumbered}

Table A11j (Table A11-h1) reports the multi-regime operational dispatch benchmark at $h=1$ across all five random seeds (201--205) on the 134-turbine WTB test split, and Table A11k (Table A11-h2) provides the corresponding seed-paired bootstrap difference statistics against Joint Routed.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{1.8pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11j (Table A11-h1).} Cross-Seed Multi-Regime Operational Dispatch Benchmark ($h=1$, 10-Minute Immediate Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$).}
%
\setlength{\tabcolsep}{3.5pt}
\begin{tabularx}{\linewidth}{l >{\raggedright\arraybackslash}p{0.18\linewidth} c c c c >{\raggedright\arraybackslash}X}
\toprule
Regime & Evaluated Model & Penalized Reserve-Shortfall Energy & Violation Rate & Reserve & Shortage & Pinball Loss \\
 & & (kW$\cdot$h, Proxy at $\rho=10$) & & (MWh) & (MWh) & \\
\midrule
\textbf{Clean} & Continuous Physical Quantile & $\mathbf{589{,}535 \pm 77{,}390}$ & $7.73\% \pm 1.56\%$ & $358{,}722 \pm 30{,}279$ & $23{,}081 \pm 5{,}172$ & $21.70 \pm 2.52$ \\
 & Frozen-Embedding Direct Quantile MLP & $1{,}074{,}875 \pm 296{,}315$ & $1.36\% \pm 0.81\%$ & $1{,}030{,}913 \pm 319{,}358$ & $4{,}396 \pm 2{,}565$ & $42.68 \pm 13.38$ \\
 & Global Quantile & $717{,}781 \pm 80{,}823$ & $6.16\% \pm 1.65\%$ & $494{,}374 \pm 99{,}462$ & $22{,}341 \pm 4{,}832$ & $27.25 \pm 3.27$ \\
 & Joint Dense Head & $686{,}555 \pm 70{,}084$ & $7.17\% \pm 1.28\%$ & $450{,}074 \pm 63{,}929$ & $23{,}648 \pm 4{,}171$ & $25.90 \pm 2.49$ \\
 & \textbf{Joint Routed (Ours)} & $658{,}437 \pm 79{,}817$ & $7.67\% \pm 1.08\%$ & $397{,}056 \pm 81{,}728$ & $26{,}138 \pm 3{,}700$ & $24.68 \pm 2.69$ \\
 & Missingness-Aware GBDT & $608{,}916 \pm 74{,}931$ & $5.81\% \pm 1.17\%$ & $423{,}500 \pm 44{,}130$ & $18{,}542 \pm 4{,}128$ & $22.54 \pm 2.66$ \\
\midrule
\textbf{Delay-6} & Continuous Physical Quantile & $739{,}262 \pm 62{,}423$ & $12.60\% \pm 1.94\%^{\dagger}$ & $362{,}746 \pm 30{,}973$ & $37{,}652 \pm 5{,}915$ & $26.46 \pm 2.03$ \\
 & Frozen-Embedding Direct Quantile MLP & $1{,}112{,}826 \pm 296{,}762$ & $1.63\% \pm 0.76\%$ & $1{,}063{,}303 \pm 318{,}675$ & $4{,}952 \pm 2{,}538$ & $42.41 \pm 13.08$ \\
 & Global Quantile & $790{,}677 \pm 74{,}232$ & $8.60\% \pm 2.23\%$ & $500{,}534 \pm 100{,}702$ & $29{,}014 \pm 4{,}762$ & $28.66 \pm 2.81$ \\
 & Joint Dense Head & $788{,}230 \pm 75{,}895$ & $10.70\% \pm 1.15\%^{\dagger}$ & $454{,}103 \pm 63{,}610$ & $33{,}413 \pm 2{,}328$ & $28.55 \pm 2.82$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{747{,}948 \pm 66{,}436}$ & $10.74\% \pm 2.02\%^{\dagger}$ & $403{,}402 \pm 89{,}912$ & $34{,}455 \pm 5{,}760$ & $26.83 \pm 2.20$ \\
 & Missingness-Aware GBDT & $685{,}944 \pm 57{,}157$ & $5.74\% \pm 1.09\%$ & $501{,}925 \pm 35{,}452$ & $18{,}402 \pm 3{,}994$ & $24.19 \pm 2.08$ \\
\midrule
\textbf{Noise} & Continuous Physical Quantile & $700{,}307 \pm 91{,}043$ & $10.71\% \pm 2.72\%^{\dagger}$ & $382{,}282 \pm 35{,}606$ & $31{,}802 \pm 7{,}975$ & $24.74 \pm 2.84$ \\
 & Frozen-Embedding Direct Quantile MLP & $1{,}052{,}607 \pm 242{,}635$ & $2.28\% \pm 1.08\%$ & $985{,}760 \pm 271{,}026$ & $6{,}685 \pm 3{,}296$ & $39.36 \pm 10.78$ \\
 & Global Quantile & $757{,}012 \pm 78{,}469$ & $6.96\% \pm 2.02\%$ & $514{,}778 \pm 103{,}567$ & $24{,}223 \pm 5{,}577$ & $27.10 \pm 2.89$ \\
 & Joint Dense Head & $738{,}914 \pm 81{,}871$ & $9.29\% \pm 1.76\%$ & $447{,}191 \pm 57{,}304$ & $29{,}172 \pm 5{,}233$ & $26.34 \pm 2.66$ \\
 & \textbf{Joint Routed (Ours)} & $\mathbf{711{,}218 \pm 87{,}033}$ & $9.56\% \pm 1.08\%$ & $399{,}588 \pm 83{,}563$ & $31{,}163 \pm 3{,}761$ & $25.20 \pm 2.70$ \\
 & Missingness-Aware GBDT & $691{,}744 \pm 80{,}257$ & $6.57\% \pm 1.37\%$ & $482{,}524 \pm 51{,}570$ & $20{,}922 \pm 4{,}704$ & $24.39 \pm 2.52$ \\
\midrule
\textbf{Markov} & Continuous Physical Quantile & $\mathbf{611{,}462 \pm 78{,}376}$ & $8.21\% \pm 1.63\%$ & $364{,}021 \pm 31{,}123$ & $24{,}744 \pm 5{,}247$ & $21.98 \pm 2.48$ \\
 & Frozen-Embedding Direct Quantile MLP & $1{,}098{,}616 \pm 301{,}206$ & $1.42\% \pm 0.80\%$ & $1{,}051{,}516 \pm 324{,}901$ & $4{,}710 \pm 2{,}628$ & $42.64 \pm 13.36$ \\
 & Global Quantile & $743{,}045 \pm 82{,}567$ & $6.52\% \pm 1.74\%$ & $503{,}739 \pm 101{,}347$ & $23{,}931 \pm 5{,}036$ & $27.56 \pm 3.25$ \\
 & Joint Dense Head & $711{,}324 \pm 71{,}786$ & $7.60\% \pm 1.28\%$ & $458{,}884 \pm 65{,}446$ & $25{,}244 \pm 4{,}368$ & $26.21 \pm 2.48$ \\
 & \textbf{Joint Routed (Ours)} & $684{,}945 \pm 80{,}533$ & $8.04\% \pm 1.22\%$ & $405{,}099 \pm 81{,}991$ & $27{,}985 \pm 4{,}018$ & $25.10 \pm 2.66$ \\
 & Missingness-Aware GBDT & $633{,}745 \pm 76{,}259$ & $5.95\% \pm 1.20\%$ & $438{,}277 \pm 43{,}705$ & $19{,}547 \pm 4{,}435$ & $22.92 \pm 2.63$ \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont $^{\dagger}$Exceeds the nominal 10\% violation target ($q^* = 0.90$) set by the reserve screening index. Bold numbers denote lowest operational cost. Evaluated under clean-calibrated validation thresholds across 5 random seeds (201--205).
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A11k (Table A11-h2).} Seed-Paired Difference in Penalized Reserve-Shortfall Energy against Joint Routed ($h=1$, $\Delta\text{Cost} = \text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Joint Routed}}$, positive indicates Joint Routed saves cost at $\rho=10$).}
%
\setlength{\tabcolsep}{3.5pt}
\begin{tabularx}{\linewidth}{l >{\raggedright\arraybackslash}p{0.20\linewidth} c c >{\raggedright\arraybackslash}X}
\toprule
Regime & Baseline Model & $\Delta$ Cost (kW$\cdot$h) & 95\% Bootstrap CI & 95\% CI Sig. \& Operational Finding \\
\midrule
\textbf{Clean} & Global Quantile & +59{,}344 & [-16{,}440, +135{,}127] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -68{,}902 & [-105{,}175, -32{,}629] & Yes (Baseline lower) \\
 & Missingness-Aware GBDT & -49{,}521 & [-115{,}426, +16{,}384] & No (Baseline lower) \\
 & Frozen-Embedding Direct Quantile MLP & +416{,}438 & [+105{,}990, +726{,}886] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +28{,}118 & [-25{,}901, +82{,}138] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Delay-6} & Global Quantile & +42{,}730 & [-15{,}276, +100{,}736] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -8{,}686 & [-41{,}273, +23{,}901] & Viol. Exceeded ($>10\%$) \\
 & Missingness-Aware GBDT & -62{,}003 & [-132{,}867, +8{,}860] & No (Baseline lower) \\
 & Frozen-Embedding Direct Quantile MLP & +364{,}879 & [+72{,}780, +656{,}977] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +40{,}282 & [-18{,}752, +99{,}316] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Noise} & Global Quantile & +45{,}794 & [-22{,}405, +113{,}994] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -10{,}911 & [-28{,}924, +7{,}101] & Viol. Exceeded ($>10\%$) \\
 & Missingness-Aware GBDT & -19{,}474 & [-77{,}894, +38{,}947] & No (Baseline lower) \\
 & Frozen-Embedding Direct Quantile MLP & +341{,}389 & [+74{,}234, +608{,}544] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +27{,}696 & [-15{,}571, +70{,}962] & No (Parity, CI crosses 0) \\
\midrule
\textbf{Markov} & Global Quantile & +58{,}100 & [-14{,}351, +130{,}551] & No (Parity, CI crosses 0) \\
 & Continuous Physical Quantile & -73{,}483 & [-112{,}039, -34{,}927] & Yes (Baseline lower) \\
 & Missingness-Aware GBDT & -51{,}200 & [-120{,}274, +17{,}874] & No (Baseline lower) \\
 & Frozen-Embedding Direct Quantile MLP & +413{,}671 & [+101{,}079, +726{,}264] & Yes ($p < 0.05$) \\
 & Joint Dense Head & +26{,}379 & [-25{,}724, +78{,}483] & No (Parity, CI crosses 0) \\
\bottomrule
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Note: At $h=1$, Joint Dense Head and Joint Routed show statistical parity in Clean ($p = 0.380$), Noise ($p = 0.300$), and Markov ($p = 0.237$) where bootstrap 95\% CIs cross zero. In Delay-6, Routed holds a modest cost advantage ($+79{,}637\text{ kW}\cdot\text{h}$, $^*p=0.038$), though non-significant under Bonferroni threshold $\alpha=0.0125$. Decoupled modular model (Frozen Backbone + Residual Quantile) achieves $9.68\%$ violation rate.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Engineering-unit reserve-value translation and exploratory price-weighted forecast loss {.unnumbered}

Table A12 translates the reserve audit into MWh-equivalent forecast-cell accounting and evaluates exploratory multi-year price-weighted forecast loss under historical UK Elexon BMRS half-hourly dynamic settlement prices (2016--2024, 17.6 cumulative machine-operating years across 5 seeds). Panel A reports the controlled engineering-unit benchmark on the WTB test split at $\rho=10$ under an illustrative 100 EUR/MWh reserve-cost marker [@bremnes2004quantile; @zhou2013probabilisticmarkets]. Panel B evaluates this screening protocol under historical market price series by replaying every test cell against its contemporaneous half-hourly System Buy Price ($P_{\mathrm{SBP}} \in [-£185.33, +£4,037.80]/\text{MWh}$, 157,804 settlement periods) under utility two-year walk-forward rolling recalibration with frozen backbone weights across Kelmarsh (9 full years, 6 turbines) and Penmanshiel (8.6 full years, 14 turbines). In alignment with Cover Letter Note 6 and Quarantine Item Q-03, these values are formally characterized as exploratory price-weighted forecast loss metrics rather than realized wholesale market settlement cashflows, as they do not simulate dynamic market clearing, transmission-constrained dispatch, or single-delivery moment settlement. Crucially, because data-integrity auditing isolated temporal overlap in two historical rolling folds, these multi-year metrics are treated strictly as an exploratory operational sensitivity analysis rather than validated proof of decadal durability. Table A12b details the annual price-weighted loss breakdown across calendar years (2016--2024), highlighting the empirical market impact during extreme energy crisis volatility. Across all 13 rolling walk-forward folds, 13 out of 13 exhibit positive net price-weighted loss savings ($p = 0.000122 < 0.0002$ under exact binomial sign test; 10 folds strictly excluding zero in 95\% bootstrap intervals), achieving multi-year pooled net price-weighted savings of +£134.0k on Kelmarsh and +£187.1k on Penmanshiel (+£321.2k combined).

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.2pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.03}
\caption*{\textbf{Table A12.} Engineering-unit translation and exploratory price-weighted forecast loss evaluation under UK Elexon BMRS half-hourly System Buy Prices (2016--2024, 17.6 cumulative machine-operating years, 5 seeds).}
%
\noindent\textbf{Panel A: Benchmark engineering-unit forecast-cell translation ($\rho=10$, WTB test split)}\par
\vspace{1mm}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l c c r r r c l@{}}
\toprule
Comparison (vs Soft-Gate-Bin) & Subset & \shortstack{$\Delta$ Reserve\\(MWh)} & \shortstack{Avoided\\Shortage} & \shortstack{$\Delta$ Cost\\(MWh)} & \shortstack{Cost-Scale\\@100 (EUR)} & 95\% CI & \shortstack[l]{Operational\\Interpretation} \\
\midrule
Boundary gate-bin vs same-router global & boundary & +1950 & +637 & -4420 & -442k & negative & Transition triage value \\
Boundary gate-bin vs GWN physical-bin & boundary & +2319.2 & +205.6 & +262.9 & +26k & competitive & Strong physical-bin parity \\
Boundary gate-bin vs GWN global full & full & +3148.2 & -1413.5 & +17283.2 & +1728k & positive delta & Blocks full-sample claim \\
\bottomrule
\end{tabular*}
\vspace{2mm}

\noindent\textbf{Panel B: Walk-forward rolling pooled exploratory price-weighted forecast loss under historical UK Elexon BMRS SBP (2016--2024)}\par
\vspace{1mm}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llcrrrcr@{}}
\toprule
\shortstack[l]{Farm \& Cumulative Years\\(vs Soft-Gate-Bin)} & \shortstack[l]{Baseline\\Comparator} & $\rho$ & \shortstack{Avoided\\Shortage} & \shortstack{Price-Wt.\\Shortage Diff} & \shortstack{Net Savings\\(£ GBP)} & \shortstack{95\% Bootstrap CI\\(£ GBP)} & \shortstack{Value /\\Turb-Yr} \\
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
\end{tabular*}
\vspace{1mm}
\raggedright\fontsize{8.0pt}{9.0pt}\selectfont Values in Panel A are MWh-equivalent forecast-cell accounting with $\Delta t=1/6$ h under an illustrative 100 EUR/MWh marker. In Panel B, figures are exploratory price-weighted forecast loss metrics rather than realized wholesale market settlement cashflows (aligning with Cover Letter Note 6 and Quarantine Item Q-03), replaying every test cell against contemporaneous UK Elexon BMRS half-hourly System Buy Prices (£/MWh, 157,804 periods spanning 2016--2024, mean £77.43/MWh, range [-£185.33, +£4,037.80]/MWh). Shortfall penalty savings represent avoided price-weighted imbalance loss ($\sum \Delta\text{Shortage}_{\mathrm{MWh}} \times P_{\mathrm{SBP}}$); net savings include reserve capacity procurement cost at $c_{\mathrm{res}} = £15/\text{MWh}$. Bootstrap intervals ($^*$ = strictly excluding zero) use 20,000 paired resamples across 5 seeds. Across all 13 rolling walk-forward folds, 13 out of 13 exhibit positive net price-weighted savings ($p = 0.000122 < 0.0002$ under exact binomial sign test).
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.2pt}
\renewcommand{\arraystretch}{1.06}
\caption*{\textbf{Table A12b.} Decadal annual exploratory price-weighted loss breakdown and energy crisis price sensitivity across calendar years (2016--2024, 5 seeds, Kelmarsh vs Global Quantile, $\rho=10$).}
%
\setlength{\tabcolsep}{3pt}
\begin{tabularx}{\linewidth}{c >{\raggedright\arraybackslash}X r r r r r c}
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
\end{tabularx}\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Annual sensitivity breakdown replaying the frozen neural backbone against contemporaneous Elexon System Buy Prices under commissioning static freeze ($P_{\mathrm{SBP}}$ calendar mean and maximum). In 8 out of 9 calendar years, the soft gate achieves statistically significant positive net price-weighted savings (strictly excluding zero). In 2022, peak gas and balancing power prices (£200.08/MWh mean, £4,035.98/MWh max) penalized unhedged residual variations under frozen static quantiles (-£4.0k). Crucially, under utility two-year walk-forward rolling recalibration (Table A12 Panel B), Year 7 (Fold 5) achieves +£12.4k net price-weighted savings (CI [+£9.5k, +£15.5k], strictly excluding zero), and all 13 out of 13 rolling folds achieve positive net savings ($p = 0.000122$), recording exploratory price-weighted contrasts. Temporal overlap in historical folds and unverified settlement integration prevent claims of robust market protection or realized revenue.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Substation computational footprint and operational expenditure audit {.unnumbered}

> **[GOVERNANCE ISOLATION NOTICE]**: In accordance with the Step 1 evidence-base audit protocol (`isolation_manifest.json`), hardware execution timing (4.12 ms GPU / 21.8 ms IPC CPU), runtime RAM claims (<1.5 MB), and cashflow revenue conversions (£/GBP) are exploratory proxy estimates uncalibrated on physical RTU industrial testbeds or verified market settlement pipelines. They are strictly quarantined and superseded by rigorous physical engineering units (MWh reserve/shortage and normalized cost regret under strict iso-reliability). Only the parameter count (110,012 parameters, ~430 KB in float32) is verified from checkpoint artifacts.

To address potential computational feasibility in field deployments, Table A12c presents the theoretical parameter footprint on standard wind farm central substation supervisory infrastructure. In industrial wind power operations, telemetry streams from all 134 turbines are aggregated over the wind farm optical fiber ring network and processed at the central substation Supervisory Control and Data Acquisition (SCADA) / Energy Management System (EMS) terminal.

The 110,012 parameters imply approximately 430 KB of float32 parameter storage, excluding activations and runtime overhead. This alone does not establish SCADA/EMS deployment feasibility. Physical deployment on industrial hardware will require verified on-chip profiler logs and physical RTU measurement in subsequent experimental phases.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A12c.} Computational footprint audit across central substation supervisory infrastructure (134 turbines, 10-minute dispatch interval; latency and cashflows isolated per audit protocol).}
%
\begin{tabular}{lll}
\toprule
Engineering Parameter & Value & Industrial Dispatch Context \\
\midrule
Model parameter count & 110,012 parameters & Single integrated checkpoint ($\sim$430 KB in float32, verified) \\
Storage footprint & 430 KB & Resides in memory/cache without paging \\
Inference latency & [Quarantined] & Theoretical proxy (4.12 ms GPU / 21.8 ms CPU) isolated pending RTU testbed \\
Runtime RAM residency & [Quarantined] & Unprofiled runtime allocation isolated pending memory profiler audit \\
Dispatch interval & 10 minutes (600 seconds) & Standard 10-min SCADA historian logging grid (IEC 61400-25 context) \\
Candidate integration & Central substation SCADA/EMS & Concept only; hardware and safety unvalidated \\
Energy / Cashflow Metrics & [Quarantined] & Commercial cashflow (£/GBP) isolated; evaluated via engineering MWh \\
\bottomrule
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont Single-checkpoint execution avoids separate model orchestration overhead. All hardware execution times and cashflow figures are quarantined pending dedicated physical testbed measurements.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Complete forecasting benchmark {.unnumbered}

Table A13 reports the full WTB and ERA5 benchmark used for the RMSE-price guardrail. The two MoE rows are the train-only class-weight reruns; the remaining rows are the archived strict-mask baselines. The displayed guardrail is the 5.59 RMSE gap between the train-only boundary router and iTransformer.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.6pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A13.} Complete forecasting benchmark (WTB RMSE in kW; ERA5 normalised flux RMSE).}
%
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
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont The two train-only MoE rows are the provenance-corrected reruns used for the headline guardrail; their MAE and switch statistics are available in the archived run tables. The legacy MoE rows remain listed for provenance transparency only.
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Questions for local assessment before any reserve use {.unnumbered}

Table A14 lists questions motivated by archived cross-farm diagnostics. Passing representation checks does not certify reserve sufficiency, risk limits or deployment safety.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{2.0pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table A14.} Diagnostic assessment questions; no deployment admission is certified.}
%
\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{0.28\linewidth} >{\raggedright\arraybackslash}p{0.38\linewidth} >{\raggedright\arraybackslash}X}
\toprule
Question & Archived observation & Interpretation boundary \\
\midrule
Withheld-channel signature & LHB 0.675; Penmanshiel 0.302 (core 0.195 borderline); Kelmarsh 0.340-0.378; shuffled controls at chance at every farm & Grade farms by signature strength; no binary observability no-go \\
Held-out routing criterion & Cross-farm held-out NMI 0.557 passes the 0.50 criterion in aggregate but is direction-dependent (0.341 in one direction) & Re-establish routing agreement locally and report per-direction values \\
Local boundary recalibration & Validation-only recalibration moves test NMI only marginally & Treat threshold transfer as insufficient \\
Pitch/proxy observability & Farms with partial pitch coverage recover the boundary above chance & Assess pitch/proxy validity separately; no reserve-grade certificate \\
Geometry and regime support & Farm scale, sensor fields, power curves, and regime shares differ across sites & Run a local evidence protocol before gate-bin reserve allocation \\
PCC portfolio smoothing and site scale & LHB miniature 4-turbine site exhibits quantile sample-variance amplification (+1.01M kWh in short quarterly slices vs +43k kWh in 180-day window); WTB 134 turbines saves -2.32M kWh at PCC bus (-1.33M kWh in transitional regime) & Assess local comparators and risk constraints; these diagnostics certify neither a smoothing mechanism nor a deployment route \\
\bottomrule
\end{tabularx}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## ERA5 observability contrast {.unnumbered}

The ERA5 contrast tests a setting in which the physical marker is directly visible. Three archived months of hourly data over a fixed $16\times16$ patch are reorganised into a $T{=}2208$-frame tensor with $N{=}256$ nodes and eight input variables. The thermodynamic regime label separates stable from convective near-surface states using sensible heat flux and its local time delta: convective samples have positive afternoon flux anomaly, stable samples do not; the label is available at 60\% coverage and enters only alignment supervision. The gate anchor is $[\texttt{sshf}, \texttt{t2m}, \texttt{wind\_speed}, \Delta\texttt{sshf}]$, and the graph is a static Haversine-Gaussian $k_{\mathrm{nn}}$ structure because no wake directionality is defined on a grid. The same directed-diffusion GRU and node-level MoE are trained with the full corrected stack; the contrast result is that Physics-Aligned MoE achieves NMI $0.210 \pm 0.109$ against an unconstrained collapse of $0.032 \pm 0.025$ under thermodynamic observability (`table_routing_quality.csv`), showing that supervision retains partial alignment under direct thermodynamic observation whereas unconstrained gating collapses. The ERA5 rows in Table A13 and the shared-architecture table carry the numerical record; ERA5 is not used for any reserve or deployment claim.

```{=latex}
\FloatBarrier
```

## Compute disclosure {.unnumbered}

The WTB boundary router has 110,012 parameters. The earlier disclosure reported approximately 445 s per epoch, stopping at 6-9 epochs and roughly 6-7 GPU-hours per five-seed family. These are retained as historical estimates, not verified cross-environment runtime guarantees. The former blanket statement that all neural runs used an RTX 4090 with one numerical profile is unsupported by complete execution receipts. Saved checkpoints, arrays, recovered entry-point text and partial logs do not bind every original run to its hardware, dependencies, weights, complete inputs and backend settings. Training mixed precision also does not establish the precision used for each archived evaluation. End-to-end reproduction across all declared seeds and experiment families remains unverified.

## Reproducibility scope and frozen provenance gaps {.unnumbered}

The historical source investigation is frozen as of 2026-10-18. The original rented grokking compute instance has been reported destroyed, and its investigation has stopped. A prior strict host-identity check rejected a changed key before authentication; no remote file-system evidence was obtained through that attempt. Scoped local searches did not recover the original auxiliary-evaluation receipts. Missing generation-time bindings remain unknown rather than being reconstructed from later checkpoints or repository commits.

Direct checks support the identity of the two legacy release members, stored accounting, and explicit residual anchors, targets and masks relative to the extant cache. The posterior archive contains probabilities without direct per-value coordinate provenance; source-compatible order, matching lengths and aggregate metrics do not certify historical alignment. All ten auxiliary-prediction comparisons with the legacy residual forecasts remain non-exact. A documented batch-size difference makes numerical execution a plausible explanation, but missing original weight, complete-input and backend-state bindings prevent unique attribution. The original validation/test support asymmetry is preserved; its calibration and decision impact remains untested. The first downstream accounting assertion occurred after posterior-cache saving; present-array accounting diagnostics do not independently certify cache semantics or the exact historical failure.

These assets remain usable for explicitly bounded diagnostic observations, not as certificates of complete raw-data reproduction, causal mechanisms or deployment safety. Later receipt-bound E04/E06 bundles retain their separately audited scope and do not retrospectively authenticate the legacy generation chain. The original no-feasible-policy outcome and all risk and exact-matching thresholds are retained. E07 remains an inactive, unexecuted protocol with no eligible unseen confirmation window bound; the old test is not reused as confirmation. Detailed evidence classes and immutable prior-document snapshots are indexed in the repository files \texttt{manuscript/REPRODUCIBILITY.md} and \texttt{docs/HISTORICAL\_PROVENANCE\_FREEZE\_20261018.md}. This documentation freeze does not confer scientific certification.

```{=latex}
\FloatBarrier
```

## Historical RMSE and degraded-risk diagnostic (Figure S1) {.unnumbered}

Figure S1 redraws the eight literal records in the historical plotting script, without executing the producer or recomputing model outputs. These constants lack independent execution binding. Safety-envelope, Pareto and percentage-gain annotations have been removed; no common-target reserve advantage is established.

```{=latex}
\begin{figure*}[t!]
\centering
\includegraphics[width=\textwidth]{analyses/manuscript_provenance_pdf_audit_20261018/figures/figure_s1_historical_literals.pdf}
\caption*{\textbf{Figure S1.} Historical plotting literals, not certified model-output evidence. All eight records are retained exactly from \texttt{scripts/plot\_rmse\_vs\_reserve\_risk.py}; only labels, layout and annotations change. The script is parsed as text, not executed. Uncertainty is unavailable in these records, so no error bars or significance are inferred. Model-specific targets prevent a common-target Pareto or causal interpretation. The original annotated graphic is preserved in the versioned assets; neither version certifies reserve safety, deployment feasibility or end-to-end reproduction.}
\end{figure*}
```

```{=latex}
\FloatBarrier
```

## SCADA communication realism and latency stress modeling {.unnumbered}

In utility-scale wind plants, supervisory control and data acquisition systems stream turbine telemetry over hierarchical topologies conforming to IEC 61400-25 standards. The following synthetic scenarios are motivated by communication failure modes; their field frequency and delay distribution remain unknown:
1. *Substation ring-buffer backlogs and cellular jitter ($10\text{--}30\text{ min}$ delays):* In remote onshore and offshore arrays, wireless long-haul cellular links (e.g., LTE/satellite backup) can suffer intermittent bandwidth saturation, transport-layer packet serialization overhead, and gateway retransmission timeouts [@ullah2022enabling]. In the commercial Kelmarsh SCADA dataset, $99.6\%$ of discrete status change events occur between standard 10-minute reporting ticks, indicating that aerodynamic transitions frequently unfold inside reporting intervals; this statistic does not identify the underlying communication-delay distribution.
2. *Contingency outage-envelope stress conditions ($60\text{ min}$ latency, Delay-6):* A 6-step ($60\text{ min}$) fixed shift represents a deliberate worst-case operational stress test. Rather than asserting that routine telemetry experiences 1-hour delays, this contingency upper envelope simulates extended packet queuing storms, fiber-loop cuts triggering failover routing, or primary substation gateway crashes requiring cold reboots [@pierre2019design; @ravikumar2020anomaly]. Evaluating this asymptotic upper bound delineates the failure threshold of deterministic physical rules and tests the resilience limit of data-driven representations.
3. *Non-uniform and asynchronous packet dropouts:* While fixed discrete shifts establish deterministic worst-case bounds, real-world networks exhibit non-uniform temporal degradation. To represent this stochastic behavior, we evaluate: (i) two-state Markov-Gilbert burst dropouts ($p_{GB}=0.08, p_{BB}=0.75, d \le 6$) simulating wireless blackout fading; and (ii) withheld-channel experiments simulating administrative firewalls where primary blade-pitch registers are permanently masked across commercial OEM boundaries.

```{=latex}
\FloatBarrier
```

## Appendix B. Historical reference registry {.unnumbered}

Tables B1 and B2 preserve the earlier reference directory and its recorded metadata. They are historical documentation, not a complete certification of the current bibliography. This manuscript/PDF audit does not renew the earlier blanket reference-verification claim or modify the stored registry entries.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table B1. Historical Reference Directory (Part 1: Refs [1]--[19]).}}
%
\setlength{\tabcolsep}{4pt}
\begin{tabular}{rlll}
\toprule
\textbf{Ref} & \textbf{Author (Year)} & \textbf{Venue} & \textbf{Recorded DOI / Registry} \\
\midrule
{[1]} & Dowell (2016) & IEEE Trans. Smart Grid & \texttt{10.1109/TSG.2015.2424078} \\
{[2]} & Kruse (2023) & PRX Energy & \texttt{10.1103/PRXEnergy.2.043003} \\
{[3]} & Pinson (2013) & Statistical Science & \texttt{10.1214/13-sts445} \\
{[4]} & Doherty (2005) & IEEE Trans. Power Syst.. & \texttt{10.1109/TPWRS.2005.846206} \\
{[5]} & Wang (2025) & Applied Energy & \texttt{10.1016/j.apenergy.2025.126234} \\
{[6]} & Slootweg (2003) & IEEE Trans. Power Syst.. & \texttt{10.1109/TPWRS.2002.807113} \\
{[7]} & Gaertner (2020) & National Renewable Ene.. & \texttt{10.2172/1603478} \\
{[8]} & Tautz-Weinert (2017) & IET Renewable Power Ge.. & \texttt{10.1049/iet-rpg.2016.0248} \\
{[9]} & Ullah (2022) & IEEE Trans. Industrial.. & \texttt{10.1109/TII.2021.3112386} \\
{[10]} & Pierre (2019) & IEEE Trans. Power Syst.. & \texttt{10.1109/TPWRS.2019.2903782} \\
{[11]} & Ravikumar (2024) & IEEE Trans. Smart Grid & \texttt{10.1109/TSG.2020.2995313} \\
{[12]} & Daenens (2025) & Wind Energy Science & \texttt{10.5194/wes-10-1137-2025} \\
{[13]} & Wu (2019) & Proc. 28th Internation.. & \texttt{10.24963/ijcai.2019/264} \\
{[14]} & Guo (2019) & Proc. AAAI Conference .. & \texttt{10.1609/aaai.v33i01.3301898} \\
{[15]} & Bai (2020) & Advances in Neural Inf.. & \textit{Proceedings} \\
{[16]} & Park (2019) & Energy & \texttt{10.1016/j.energy.2019.115883} \\
{[17]} & Kim (2024) & Applied Energy & \texttt{10.1016/j.apenergy.2024.123882} \\
{[18]} & Zehtabiyan-Rezaie (2023) & PRX Energy & \texttt{10.1103/PRXEnergy.2.013009} \\
{[19]} & Zhang (2021) & Applied Energy & \texttt{10.1016/j.apenergy.2021.116641} \\
\bottomrule
\end{tabular}
\end{table*}
```

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.05}
\caption*{\textbf{Table B2. Historical Reference Directory (Part 2: Refs [20]--[38]).}}
%
\setlength{\tabcolsep}{4pt}
\begin{tabular}{rlll}
\toprule
\textbf{Ref} & \textbf{Author (Year)} & \textbf{Venue} & \textbf{Recorded DOI / Registry} \\
\midrule
{[20]} & Shazeer (2017) & Int. Conf. Learning Re.. & \textit{Proceedings} \\
{[21]} & Fedus (2022) & Journal of Machine Lea.. & \textit{Proceedings} \\
{[22]} & Karpatne (2017) & IEEE Trans. Knowledge .. & \texttt{10.1109/TKDE.2017.2720168} \\
{[23]} & Karniadakis (2021) & Nature Reviews Physics & \texttt{10.1038/s42254-021-00314-5} \\
{[24]} & Bossanyi (2000) & Wind Energy & \texttt{10.1002/we.34} \\
{[25]} & Bianchi (2006) & Springer & \texttt{10.1007/1-84628-493-7} \\
{[26]} & Pao (2011) & IEEE Control Systems M.. & \texttt{10.1109/MCS.2010.939962} \\
{[27]} & Johnson (2004) & Journal of Solar Energ.. & \texttt{10.1115/1.1792653} \\
{[28]} & Ela (2011) & National Renewable Ene.. & \texttt{10.2172/1023095} \\
{[29]} & Bremnes (2004) & Wind Energy & \texttt{10.1002/we.107} \\
{[30]} & Zhang (2014) & Renewable and Sustaina.. & \texttt{10.1016/j.rser.2014.01.033} \\
{[31]} & Zhou (2013) & Wind Energy & \texttt{10.1002/we.1496} \\
{[32]} & Li (2018) & Int. Conf. Learning Re.. & \textit{Proceedings} \\
{[33]} & Hersbach (2020) & Quarterly Journal of t.. & \texttt{10.1002/qj.3803} \\
{[34]} & Nielsen (2006) & Wind Energy & \texttt{10.1002/we.180} \\
{[35]} & Zhou (2024) & Scientific Data & \texttt{10.1038/s41597-024-03427-5} \\
{[36]} & Nie (2023) & Int. Conf. Learning Re.. & \textit{Proceedings} \\
{[37]} & Liu (2024) & Int. Conf. Learning Re.. & \textit{Proceedings} \\
{[38]} & Das (2023) & Transactions on Machin.. & \textit{Proceedings} \\
\bottomrule
\end{tabular}
\end{table*}
```

```{=latex}
\FloatBarrier
```

## Mismatched recalibration matrix under latency drift (Table A11l) {.unnumbered}

Table A11l evaluates the sensitivity of state-conditional physical recalibration when the calibration latency condition $\tau_{\mathrm{cal}}$ mismatches the actual online operational latency $\tau_{\mathrm{test}}$ ($h=1$, 5-seed mean on 134-turbine WTB test split, $\rho=10$). The results establish that recalibrating under $\tau_{\mathrm{cal}} = 10\,$min withstands operational latency drift up to $\tau_{\mathrm{test}} = 20\,$min ($8.2\%\text{--}9.1\%$ violation), but breaks down if staleness surges to $60\,$min ($13.8\%$ violation), delineating where simple recalibration ceases to buffer degradation without machine learning representation recovery.

```{=latex}
\begin{table*}[!t]
\centering
\fontsize{8.0pt}{9.6pt}\selectfont
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.08}
\caption*{\textbf{Table A11l.} $4\times 4$ Mismatched Recalibration Matrix across Test Latency $\tau_{\mathrm{test}} \in [0, 60]\,\text{min}$ and Calibration Horizon $\tau_{\mathrm{cal}} \in [0, 60]\,\text{min}$ ($h=1$, 5 Seeds on WTB, Cost Ratio $\rho=10$). Format: Penalized Reserve Screening Energy ($\text{kW}\cdot\text{h}$) / Violation Rate (\%).}
%
\begin{tabular}{lcccc}
\toprule
Calibration Protocol ($\tau_{\mathrm{cal}}$) & $\tau_{\mathrm{test}} = 0\,\text{min}$ & $\tau_{\mathrm{test}} = 10\,\text{min}$ & $\tau_{\mathrm{test}} = 20\,\text{min}$ & $\tau_{\mathrm{test}} = 60\,\text{min}$ \\
\midrule
$\tau_{\mathrm{cal}} = 0\,\text{min}$ (Clean-Calibrated) & \textbf{593,258} (7.3\%) & 753,606 (11.2\%$^\dagger$) & 896,198 (14.0\%$^\dagger$) & 1,656,285 (24.0\%$^\dagger$) \\
$\tau_{\mathrm{cal}} = 10\,\text{min}$ & 621,450 (6.5\%) & \textbf{742,211} (7.4\%) & 868,320 (8.7\%) & 1,384,510 (13.8\%$^\dagger$) \\
$\tau_{\mathrm{cal}} = 20\,\text{min}$ & 658,120 (5.9\%) & 769,480 (6.8\%) & \textbf{841,734} (7.1\%) & 1,312,870 (12.1\%$^\dagger$) \\
$\tau_{\mathrm{cal}} = 60\,\text{min}$ (Contingency-Calibrated) & 782,340 (4.6\%) & 854,120 (5.8\%) & 931,460 (6.9\%) & \textbf{1,228,609} (9.5\%) \\
\midrule
Matched Recalibration ($\tau_{\mathrm{cal}} = \tau_{\mathrm{test}}$) & 593,258 (7.3\%) & 742,211 (7.4\%) & 841,734 (7.1\%) & 1,228,609 (9.5\%) \\
STGQ-Modular (Learned Residual) & 663,347 (6.1\%) & 786,366 (6.7\%) & 875,838 (7.4\%) & 1,273,560 (9.5\%) \\
\bottomrule
\end{tabular}
\vspace{1mm}
\fontsize{8.0pt}{9.6pt}\selectfont $^\dagger$Exceeds nominal 10.0\% violation target ($q^*=0.90$). Diagonal elements represent matched state-conditional recalibration. Off-diagonal elements characterize latency drift. Under $\tau_{\mathrm{cal}}=10\,\text{min}$, tail violation remains below the nominal 10\% violation target ($<10\%$) up to $\tau_{\mathrm{test}}=20\,\text{min}$ but collapses under $\tau_{\mathrm{test}}=60\,\text{min}$, establishing the empirical breakdown boundary.
\end{table*}
```



# Audit correction and withdrawal notice (2026-10-15)

The channel MLP decision output historically labelled h=6 actually indexed h=2 residuals; that h=6 decision result is withdrawn. Its historical direct-cost references were fixed constants, not matched wind-speed baselines, so their incremental-value interpretation is withdrawn. The earlier 62.9% transition recall included boundaries induced by invalid adjacent labels; it is withdrawn as a valid-regime transition recall and retained only as a historical unmasked diagnostic. Corrected runs archive both denominator definitions. These defects do not by themselves invalidate separately masked NMI/ARI metrics.

EXP03 historical results do not have full-grid arrival provenance and used a potentially unarrived first observation for LOCF initialization. The historical asynchronous decision curve is withdrawn as causal arrival-time evidence. Corrected execution starts at standardized zero before any arrival, archives full traces, and reports one simulator trace per delay shared by model seeds. A first upper CI bound reaching zero denotes loss of demonstrated advantage, not demonstrated inferiority.

The invalidated historical EXP01 v4 calculation is recorded in \path{artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_joint_statistics.csv}. At h=6, Penmanshiel has Delta=-315399.62 kWh, 95% CI [-1590023.53,970006.32]; Kelmarsh has Delta=352433.95 kWh, 95% CI [59969.70,736901.18]. These v4 numbers and intervals are withdrawn as matched decision evidence because forecasts and targets refer to different physical windows. Earlier v2 rows remain historical only; no older version is substituted as a valid result.

Full raw-data reproduction remains unverified and is not certified; this documentation/PDF revision starts no replay. Withdrawn claims do not count as successfully reproduced experiments. See docs/RAW_REPLAY_PROTOCOL_20261015.md and the versioned execution receipts.


The 2026-10-15 source-level audit supersedes the prior authority assigned to EXP01 v4: saved forecast targets match original chronological data, while the evaluation target windows are shifted by120/720 days. All v4 cost directions and uncertainty claims are invalidated. See docs/EXP01_INVALIDATION_20261015.md.


# Target and population correction for delay scans

Historical dense/MoE phase scans used separate model-derived shortfalls, while delay conditions selected boundary cells using delayed wind. Their common-target architecture and fixed-population latency interpretations are withdrawn; stored numbers remain historical diagnostics. Clean/recalibrated physics comparisons within a single condition share the same target and mask and retain that local scope. RAW-PHASE-FROZEN-V1 fixes shortfalls and boundary populations across all arms and includes the ten-bin wind-speed comparator. Auxiliary heads retain the declared150 cached batches and5 training epochs, using shared frozen targets, validity masks and identical sampled anchors. No corrected result is reported before execution.


# Completed Controlled Subset Study and Claim Boundary

This appendix reports a separate development task completed after the historical diagnostics. It does not replace the historical canonical forecast, reinstate withdrawn comparisons, or activate the original WTB E07 continuation. The comparison was frozen before evaluation. All original failures, q levels, margins, seeds and outputs are preserved.

## Information, chronology and estimation

The raw WTB file has 134 turbines and 245 index days. An HGB point forecaster fitted on days 1--90 constructs a nonnegative synthetic commitment from event data ending at issue minus six for power at issue plus six. Its nominal publication time assumes a fresh upstream wind/power feed; the imposed delays apply to reserve-layer telemetry. No observed publication/arrival log or end-to-end latency validation is claimed. The same commitment, target and finite future-power mask are used by all candidates. Reserve models fit on days 136--175; signed offsets use 176--192, q selection 193--210, and development evaluation 211--245. Final issues are excluded until the target plus one-step release precedes the following stage. Days 91--135 are not used by these direct models. Zero and negative net power are retained. Historical pitch supervision in earlier state-probe studies is distinct from this direct-model comparison.

The primary pitch-withheld grid is Common plus 7 nonempty combinations of W/P/Q crossed with 1/6/36 readings. Common is the earlier wind/power-based commitment, issue clock sine/cosine and turbine ID. Available pitch history is shared in the five pitch-observed pressure conditions, which compare Common/P1/WP1/WP6/WP36/WPQ36 at 120k/360k. A last-arrived length L ends at issue minus delay, truncated at issue minus 35; event windows are never shifted backwards. The persistent reference uses the commitment minus last-arrived power, floored at zero, then the same calibration family. It ignores clock/ID/pitch and is not an equal-input estimator control.

HGB uses 100 iterations, 15 leaves, minimum leaf 50, learning rate 0.08 and L2=1. The MLP uses hidden widths 64/32, 80 fixed epochs, batch 2048, AdamW learning rate 0.001 and weight decay 0.0001. It minimizes exact 0.90 pinball loss on a linear output; clipping occurs only for the action. MLP mean/std imputation, full missing indicators and target scaling use only the actual historical fit rows. HGB retains its registered historical constant-zero imputation/indicators. Per seed, all candidates share one permutation and nested 10k/40k/120k/360k prefixes over the unchanged training calendar. Row density and training computation increase together; no pure sample-efficiency claim follows. Five identical copies of the deterministic persistence policy do not create independent weather replications.

## Frozen policy families and inference

Offsets are signed higher-quantiles of shortfall minus nonnegative raw prediction, at q=0.90/0.925/0.95/0.975/0.99. The operational loss ratio remains 10 and the absolute violation cap 0.10. For each candidate, historical selection chooses one shared q across five seeds among those passing the historical simultaneous risk criterion, minimizing seed-mean selection loss. No qualifying q leaves an explicitly unqualified 0.99 diagnostic. The primary evaluation assesses these historically selected policies; the secondary analysis assesses the entire predeclared q grid. The model-family identified set is retrospective even in the primary analysis.

All seeds, turbines, candidates and conditions share circular natural-index-day bootstrap draws. Mean cost is conditional on the five fitted instances; risk applies to each instance. There are 20,000 draws, primary span 3 and sensitivity spans 1/7. Each span jointly includes 252,500 coordinates: four 225-policy groups and ten 65-policy groups, each with five-instance risks and all paired cost ratios. This differs from the earlier 35-policy/8,400-coordinate diagnostic; changed candidates, samples and multiplicity prevent interpreting their outcomes as the same experiment reversing. Bounds are dependent-data approximations, without a distribution-free finite-sample safety guarantee. Cost-curve bands are marginal descriptive intervals, not the joint bounds used in decisions.

An identified sufficient policy must satisfy the cap and its upper relative cost regret against every possibly feasible competitor. Resource order is incremental channel count, predictor passes and raw feature width; equal-resource HGB/MLP candidates remain tied. This ordering is conditional on the shared upstream forecast and is not an end-to-end compute or sensor ranking. Epsilon=0/0.5/1/2/5 percent is a frozen sensitivity curve, not a field-approved engineering margin.

## Sufficiency and the exclusion of smaller policies

A minimum within the statistically qualified set is not automatically a true minimum within the finite family. For each identified sufficient policy, the additional audit considers every strictly smaller alternative j. It can exclude j only if some instance risk lower bound exceeds the cap, or if a risk-qualified witness k satisfies a paired lower cost ratio C(j)/C(k)-1 greater than epsilon. Historical nonqualification does not prove true infeasibility. The same all-pair joint event covers adaptive witness choice; each block span remains a separate sensitivity analysis. If any smaller policy remains unresolved, minimality is not identified.

All 28 primary-span condition/budget/analysis cases contain risk-qualified candidates but none establishes two-percent near-optimality. At five percent, seven primary and seven secondary cases identify sufficient sets, with different case membership. In particular, the primary pitch-withheld analysis identifies PQ1/HGB/q0.925 at all four budgets; the 40k secondary full-q analysis identifies no candidate even at five percent. None of 420 decision cases identifies finite-family minimality: 367 have no sufficient candidate and 53 have unresolved smaller alternatives. These are repeated assessments of shared data, not 420 independent experiments. The principle that richer information can be ignored by an ideal decision function is not refuted by failure of finite fitted-policy identification.

At 360k under pitch withholding, P1/HGB/q0.925 has cost 33.637629, PQ1/HGB/q0.925 has 32.670107 and WPQ36/HGB/q0.925 has 32.783686 kWh-equivalent per valid interval. P1's point cost relative to PQ1 is 2.9615 percent, with joint approximate interval [-2.2175,8.1405] percent; its risk upper bound is 7.7554 percent. Thus P1 cannot be certified within a five-percent cost margin by that contrast, but cannot be excluded as insufficient either. This gap directly illustrates why the two-channel sufficient candidate is not an identified minimum.

The MLP has higher point cost in 83 of 88 matched pitch-withheld subset/budget comparisons and lower cost in 5; these counts do not establish universal estimator superiority. Strictly nonmonotone curves number 17/22 for HGB and 15/22 for MLP. Under the different definition of failing to improve monotonically, both number 17/22; two MLP curves monotonically worsen. All 740 MLP fits retain 80 finite training-loss entries and end below their initial training loss, which verifies execution but not removal of approximation or optimization error. No sample saturation, pure information-theoretic sufficiency or universal neural inferiority is established.

## Execution and independent source qualification

The complete run contains 550 historical bundles, 550 evaluation bundles, 1,480 learned fits and 30 persistence runs. Metis exactly reconstructed 45,300 stored-action block arrays. The compact export contains 4,461 individually verified members; its exact byte checksum is retained in the repository recovery manifest. A separate necessity receipt binds the aggregate, source and pre-evaluation guard; an independent read-only audit reproduced all 420 classifications. Full models, fit indices and raw action arrays remain on Metis. Existing claim/number gates check their declared consistency scope and do not certify these new statistical or deployment claims.

Official Hill of Towie v2.1.0 archives for 2023/2024/2025 have been acquired with publisher size/MD5 and SHA256 checks. The physical time convention is UTC ten-minute period END; all21 turbine IDs are retained. The original strict raw-row-uniqueness check failed. A separate audit found 230/231 cross-month duplicate groups per table/year with equal consumed fields; the failure is preserved. Historical preparation then accepted only unanimous consumed values across chunks, months and years; any conflict would reject the entire run. Original source rows were not rewritten or selectively removed. The new 2023/24 coordinate function has 105,265 times, 21 turbines and four channels, zero consumed-value conflicts, and preserves 505,609 negative-power cells. Eligible future-target counts are 544,177/553,075/548,163/554,408 for point fit/policy fit/offset fit/selection. These are data-qualification counts, not model-performance results.

The 2025 archive remains unparsed by this study. A 2024-file observation ending exactly 2025-01-01T00:00 describes the preceding historical interval and does not enter future scored training/selection targets. Independent model confirmation requires a complete executable historical analysis/choice package frozen before test unlock; it is unexecuted. This new farm does not replace the missing original WTB continuation or activate E07. The current claim is bounded development sufficiency with unresolved resource minimality.
