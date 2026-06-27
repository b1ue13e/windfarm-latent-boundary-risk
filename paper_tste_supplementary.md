---
documentclass: IEEEtran
classoption:
  - journal
mainfont: TeX Gyre Termes
mathfont: TeX Gyre Termes Math
bibliography: references.bib
csl: elsevier-numbered.csl
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
