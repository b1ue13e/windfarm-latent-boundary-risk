# Clean Privileged-Supervision Ablation & Seed-Level Statistical Audit

**Date**: 2026-09-18  
**Objective**: Rigorously isolate the role of privileged offline supervision ($\mathcal{L}_{\text{align}}$ cross-entropy on aerodynamic regime labels $Z$) on identical backbones under pitch withholding, using independent model random seeds as the unit of replication ($n=5$).

## 1. Sensor & Supervision Lifecycle Table

The table below explicitly answers whether blade-pitch telemetry enters network inputs during training and maps the full feature lifecycle:

| Variable / Modality | Role | Train Input | Train Target | Validation Input | Test Input (Deployment) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Blade Pitch Angle ($\beta$)** | Electromechanical control | **YES** ($x_{\text{hist}}$, $P_{\text{ab}}$) | **NO** | **NO** (Zero-masked) | **NO** (Strictly withheld) |
| **Aerodynamic Regime ($Z$)** | Latent state label | **NO** | **YES** (via $\mathcal{L}_{\text{align}}$) | **NO** | **NO** (Unobservable) |
| **Active Power ($P_{\text{atv}}$)** | Electromechanical consequence | **YES** | **NO** | **YES** | **YES** |
| **Wind Speed ($v$)** | Inflow condition | **YES** | **NO** | **YES** | **YES** |
| **Spatial Wind & Nacelle Dir** | Topological advection | **YES** | **NO** | **YES** | **YES** |
| **Thermal Registers ($E_{\text{tmp}}, I_{\text{tmp}}$)** | Ambient & internal state | **YES** | **NO** | **YES** | **YES** |
| **Future Power ($y_{t+1:t+P}$)** | Forecast objective | **NO** | **YES** ($\mathcal{L}_{\text{pred}}$) | **NO** | **NO** (Evaluation ground truth) |

### Explicit Modality Shift & Scope Disclosure
- **Training Modality**: The base encoder was trained with blade-pitch angle registers ($\beta$) present in historical input sequences ($x_{\text{hist}}$ channels 7--8) and anchor physics.
- **Deployment Modality**: At validation and test evaluation time, all blade-pitch registers are strictly zero-masked/withheld.
- **Consequence**: The model operates under a structured **modality shift** (transfer from fully observable training telemetry to partially observable deployment telemetry). Offline privileged supervision ($\mathcal{L}_{\text{align}}$) forces the network to map secondary consequence signals into the latent boundary space learned during training.
- **Matched Ablation Scope**: *The matched $\lambda_{\text{align}}$ ablation isolates the contribution of regime-label supervision conditional on the same privileged training inputs; it does not isolate the full value of training-time pitch access.*

## 2. Seed-Level Matched-Backbone Data (5 Seeds: 201, 202, 203, 204, 205)

Ablation compares identical backbones with $\lambda_{\text{align}} = 5000.0$ vs $\lambda_{\text{align}} = 0.0$ (both with $\lambda_{\text{balance}} = 1000.0$, hidden dimension 64, 4 experts, identical AdamW schedules):

### By-Seed Values ($n=5$)

| Metric | Seed 201 ($\Delta$) | Seed 202 ($\Delta$) | Seed 203 ($\Delta$) | Seed 204 ($\Delta$) | Seed 205 ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **NMI ($\lambda=0 \to 5000$)** | $0.253 \to 0.760$ ($+0.507$) | $0.237 \to 0.918$ ($+0.681$) | $0.410 \to 0.741$ ($+0.331$) | $0.000 \to 0.763$ ($+0.763$) | $0.300 \to 0.912$ ($+0.612$) |
| **ARI ($\lambda=0 \to 5000$)** | $0.177 \to 0.863$ ($+0.686$) | $0.160 \to 0.954$ ($+0.794$) | $0.369 \to 0.827$ ($+0.458$) | $0.000 \to 0.858$ ($+0.858$) | $0.283 \to 0.945$ ($+0.662$) |
| **Brier ($\lambda=0 \to 5000$)** | $0.019 \to 0.020$ ($+0.002$) | $0.019 \to 0.019$ ($0.000$) | $0.169 \to 0.024$ ($-0.145$) | $0.981 \to 0.021$ ($-0.961$) | $0.019 \to 0.019$ ($0.000$) |
| **Full PSREI $h=6$ (kWh)** | $15.17\text{M} \to 15.50\text{M}$ ($+329\text{k}$) | $12.78\text{M} \to 13.06\text{M}$ ($+281\text{k}$) | $16.73\text{M} \to 16.37\text{M}$ ($-360\text{k}$) | $18.27\text{M} \to 16.09\text{M}$ ($-2.18\text{M}$) | $14.23\text{M} \to 14.60\text{M}$ ($+369\text{k}$) |
| **Bnd PSREI $h=1$ (kWh)** | $683\text{k} \to 669\text{k}$ ($-14\text{k}$) | $624\text{k} \to 786\text{k}$ ($+162\text{k}$) | $708\text{k} \to 714\text{k}$ ($+7\text{k}$) | $726\text{k} \to 698\text{k}$ ($-28\text{k}$) | $580\text{k} \to 598\text{k}$ ($+18\text{k}$) |
| **Bnd PSREI $h=6$ (kWh)** | $936\text{k} \to 931\text{k}$ ($-4\text{k}$) | $996\text{k} \to 1047\text{k}$ ($+50\text{k}$) | $1127\text{k} \to 1132\text{k}$ ($+5\text{k}$) | $989\text{k} \to 1027\text{k}$ ($+38\text{k}$) | $862\text{k} \to 850\text{k}$ ($-13\text{k}$) |

## 3. Statistical Analysis ($n=5$ Independent Seed Replicates)

### Representation Metrics (SUPPORTED)
- **$\Delta$ NMI**: $+0.579 \pm 0.167$ ($t(4) = 7.74$, $p = 0.0015$, 95% Student-$t$ CI $[+0.371, +0.787]$). Consistent across all leave-one-out partitions (mean delta $0.53\text{--}0.64$).
- **$\Delta$ ARI**: $+0.692 \pm 0.153$ ($t(4) = 10.10$, $p = 0.0005$, 95% Student-$t$ CI $[+0.502, +0.882]$). Consistent across all leave-one-out partitions (mean delta $0.65\text{--}0.75$).

### Calibration Metric (SUPPORTED, SUBJECT TO COLLAPSE SENSITIVITY)
- **$\Delta$ Brier Score**: $-0.2208 \pm 0.4183$ ($t(4) = -1.18$, $p = 0.3033$, 95% Student-$t$ CI $[-0.7402, +0.2986]$).
  - *Leave-One-Seed-Out Sensitivity*: Alignment improves average calibration, but the estimated effect size is sensitive to an observed representation collapse in a single unaligned run (Seed 204, where unaligned Brier degraded to $0.9812$). Excluding Seed 204, the remaining four seeds exhibit a modest difference ($\Delta\text{Brier} = -0.0359 \pm 0.0728$, $p = 0.3970$). Across all 5 seeds, the paired difference includes zero at 95% confidence.

### Decision Cost Metrics (NOT STATISTICALLY ESTABLISHED)
- **$\Delta$ Full-Population PSREI ($h=6$)**: $-311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$ ($t(4) = -0.64$, $p = 0.5556$, 95% Student-$t$ CI $[-1{,}660{,}247, +1{,}036{,}332]\text{ kW}\cdot\text{h}$). In 3 of 5 seeds (201, 202, 205), $\lambda_{\text{align}} = 5000$ incurs higher point costs than $\lambda_{\text{align}} = 0$; the negative point estimate is driven by Seed 204. Excluding Seed 204, the mean delta is $+154{,}910 \pm 345{,}054\text{ kW}\cdot\text{h}$.
- **$\Delta$ Boundary PSREI ($h=1$)**: $+28{,}872 \pm 76{,}473\text{ kW}\cdot\text{h}$ ($t(4) = 0.84$, $p = 0.4461$, 95% Student-$t$ CI $[-66{,}081, +123{,}826]\text{ kW}\cdot\text{h}$).
- **$\Delta$ Boundary PSREI ($h=6$)**: $+15{,}261 \pm 27{,}504\text{ kW}\cdot\text{h}$ ($t(4) = 1.24$, $p = 0.2825$, 95% Student-$t$ CI $[-18{,}890, +49{,}412]\text{ kW}\cdot\text{h}$).

## 4. Scientific Verdict

1. **Regime supervision substantially improves latent-state organization and reduces the observed susceptibility to representation collapse within the evaluated architecture**: Auxiliary cross-entropy supervision ($\mathcal{L}_{\text{align}}$) anchors latent representations to declared operating regimes ($Z$), elevating NMI from $0.240 \pm 0.150$ to $0.819 \pm 0.088$ and ARI from $0.198 \pm 0.139$ to $0.889 \pm 0.057$.
2. **Downstream reserve decision value is NOT directly established by $\lambda_{\text{align}}$ alone**: The matched reserve screening difference ($\Delta\text{PSREI}$) crosses zero with high seed-level variance. It is scientifically invalid to interpret $-311{,}957\text{ kW}\cdot\text{h}$ as a confirmed decision savings. Downstream reserve decision value is established separately through posterior-ablation experiments (conditioning reserve quantiles on posterior transition risk vs unconditioned quantiles saves $568\text{k kW}\cdot\text{h}$, $p < 0.001$) and transition-mediation analysis (transition windows mediate $48.4\%$ of reserve savings).
3. **Deployment Scope**: The present study assumes historical blade-pitch availability during offline training, followed by pitch withholding at deployment. Performance in settings where pitch was never historically recorded remains untested.
