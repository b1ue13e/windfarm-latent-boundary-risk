# Adversarial Reviewer Attack & First-Principles Defense Playbook

**Date**: 2026-09-19  
**Scope**: Definitive answers to the eight core reviewer-facing vulnerabilities before manuscript finalization.
**Protocol**: Every answer strictly provides:
1. **CLAIM**: Clear, unambiguous scientific statement.
2. **EVIDENCE**: Direct citations to repository artifacts, numerical outputs, test scripts, and data tables.
3. **LIMITATION**: Explicitly admitted scientific boundaries and failure cases.
4. **SAFE MANUSCRIPT WORDING**: Exact, non-triumphalist phrasing for publication.

---

### Q1. Is the paper fundamentally dependent on one site?

- **CLAIM**:  
  Yes, the empirical discovery and mechanistic identification of consequence-driven latent operating-boundary recovery are fundamentally established on the 134-turbine WTB complex. Five random training seeds (201--205) quantify training and optimization stochasticity; they do NOT constitute independent wind farms, microclimates, or physical replications.
- **EVIDENCE**:  
  - Primary identification environment: WTB 245-day 10-minute SCADA archive ($T=35{,}280, N=134, F=11$, KDD Cup 2022 benchmark) under 180/30/35-day train/val/test splits (`artifacts/cache_strictmask_trainweights/wtb_245d`).
  - Factorial latent-boundary ablations, channel consequence ablations, and fixed-target residual evaluations are conducted on WTB (`artifacts/fixed_forecast_residuals.npz`, `artifacts/channel_consequence_ablations.csv`).
- **LIMITATION**:  
  The learned neural representation parameters are site-specific and cannot be transferred zero-shot to external wind plants with different turbine models, hub heights, aerodynamic power curves, or wind regimes.
- **SAFE MANUSCRIPT WORDING**:  
  > “The primary aerodynamic mechanism is identified on the 134-turbine WTB benchmark complex, where five random seeds evaluate training stochasticity rather than independent physical environments. External sites probe transferability and delineate site-dependent boundary conditions rather than serving as uniform replications.”

---

### Q2. Do external sites reproduce the mechanism or merely bound transferability?

- **CLAIM**:  
  External sites do not provide uniform replication evidence; their observed effects are heterogeneous and primarily serve as external-validity boundary probes that establish where spatial graph modeling adds value and where it fails.
- **EVIDENCE**:  
  Detailed in `docs/SITE_MECHANISM_BOUNDARY_TABLE.md` and `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv`:
  1. **Penmanshiel (14 operational turbines, 8.6-year archive)**: POSITIVE BOUNDARY PROBE. STGQ reduces surrogate cost relative to the global quantile baseline ($-2.14\text{M kW}\cdot\text{h}$, 95% CI $[-3.25\text{M}, -1.36\text{M}]$, $p < 0.05$), matching continuous physical rules ($2{,}029\text{k kW}\cdot\text{h}$). Table IV compares STGQ against an unconditioned global baseline rather than matched external no-graph ablations, so external gains are not causally attributed to wake modeling alone.
  2. **Kelmarsh (6 turbines, 9-year archive)**: NEUTRAL PROBE. Minimal spatial wake redundancy across a 6-turbine micro-array yields a statistically neutral bootstrap difference of $-40\text{k kW}\cdot\text{h}$ (95% CI $[-204\text{k}, +172\text{k}]$, crossing zero, $p = 0.85$).
  3. **ENGIE La Haute Borne (4 turbines, 4-year archive)**: NEGATIVE / OVERFITTING BOUNDARY PROBE. Micro-farm graph convolutions overfit local terrain noise, incurring a $+43\text{k kW}\cdot\text{h}$ penalty (annual pooled) and $+1.01\text{M kW}\cdot\text{h}$ (quarterly rolling, 95% CI $[+0.29\text{M}, +1.76\text{M}]$) over scalar quantiles.
  4. **Directional Transfer Asymmetry**: Zero-shot cross-farm transfer exhibits extreme asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$).
- **LIMITATION**:  
  External farm tests do not demonstrate automatic cross-site generalization. Cross-site STGQ effects relative to the global quantile baseline are heterogeneous; the observed pattern is consistent with exploitable spatial redundancy as a possible moderator, while turbine count alone does not explain the variation.
- **SAFE MANUSCRIPT WORDING**:  
  > “Cross-site STGQ effects relative to the global quantile baseline are heterogeneous (Penmanshiel: positive; Kelmarsh: statistically neutral; La Haute Borne: negative overfitting boundary). The observed pattern is consistent with exploitable spatial redundancy as a possible moderator, while turbine count alone does not explain the variation. Because Table IV lacks matched external no-graph ablations, wake modeling is not causally isolated as the sole mechanism for external gains.”

---

### Q3. Are 14.98% and 16.23% genuinely different experimental scopes?

- **CLAIM**:  
  Yes. Both numbers are mathematically exact, reproducible values computed from the canonical baseline artifact (`artifacts/direct_quantile_baselines_summary.csv`), but they represent two distinct operational degradation scenarios for `B3_Quantile_GBDT` at $h=6$.
- **EVIDENCE**:  
  - Forensic trace in `docs/GBDT_METRIC_PROVENANCE.md` from `scripts/run_direct_quantile_baselines.py`:
    - Row 10: `clean` scenario ($\tau=0$, all 11 SCADA channels observed): $\text{Violation Rate} = 0.162345 \to \mathbf{16.23\%}$ ($\text{PSREI} = 15,665,275\text{ kW}\cdot\text{h}$).
    - Row 30: `pitch_withheld` scenario ($\tau=0$, blade pitch channels $P_{\text{ab}}$ masked): $\text{Violation Rate} = 0.149771 \to \mathbf{14.98\%}$ ($\text{PSREI} = 14,965,626\text{ kW}\cdot\text{h}$).
  - Both values breach the nominal 10% Newsvendor violation target ($q^* = 0.90$ induced by $\rho=10$; $16.23\% > 10.0\%$ and $14.98\% > 10.0\%$).
- **LIMITATION**:  
  Earlier textual summaries loosely quoted $16.23\%$ while discussing the pitch-withheld regime. This was a typographical scenario conflation in draft narrative, not a data forgery or code bug.
- **SAFE MANUSCRIPT WORDING**:  
  > “Shallow quantile tree baselines (B3 GBDT) breach the nominal 10% Newsvendor violation target ($q^* = 0.90$) at $h=6$, surging to a $16.23\%$ violation rate under clean telemetry and $14.98\%$ when blade pitch is withheld (exceeding the nominal 10% target in both conditions).”

---

### Q4. Does posterior conditioning beat a strong wind-speed-conditioned quantile baseline overall?

- **CLAIM**:  
  No. On the full operational test population, posterior conditioning does NOT outperform a strong empirical wind-speed-binned quantile baseline; it performs approximately $523\text{k kW}\cdot\text{h}$ worse (canonically defined as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p = 0.85$).
- **EVIDENCE**:  
  Evaluated across 5 seeds on 385,205 valid test cells in `artifacts/strong_baseline_closure_summary.csv` (`scripts/test_strong_baseline_closure.py`):
  - Policy B (Wind-Speed Bins, 10 bins): $\text{PSREI} = \mathbf{13,784,320} \pm 1,438,833\text{ kW}\cdot\text{h}$ (8.79% violation, 346,019 kWh shortage).
  - Policy C (Posterior-Conditioned): $\text{PSREI} = 14,307,364 \pm 1,787,258\text{ kW}\cdot\text{h}$ (9.08% violation, 412,829 kWh shortage).
  - Paired difference: $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = \mathbf{+523,044\text{ kW}\cdot\text{h}}$ ($p = 0.85$, 95% CI $[+233\text{k}, +830\text{k}]$).
- **LIMITATION**:  
  Machine learning models cannot beat direct observable physical wind-speed conditioning across the broad plant-wide envelope. In Region 2 (MPPT) where power obeys $P \propto v^3$, direct wind-speed binning is the minimum sufficient operational policy.
- **SAFE MANUSCRIPT WORDING**:  
  > “The learned latent-boundary posterior does not improve plant-wide reserve screening over a strong wind-speed-conditioned quantile baseline (canonically defined as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). The relative risk-cost trade-off becomes materially more favorable near operating transitions.”

---

### Q5. If not, exactly where does posterior information add value?

- **CLAIM**:  
  The relative risk-cost trade-off becomes materially more favorable near operating transitions ($\pm 3$ steps of boundary switching): posterior conditioning selectively reduces violation and shortage exposure near transitions, but this hedge remains more expensive under $\rho=10$ than wind-speed-binned quantile calibration ($\Delta = +112{,}704\text{ kW}\cdot\text{h}$, due to $+149{,}092\text{ kW}\cdot\text{h}$ higher reserve procurement).
- **EVIDENCE**:  
  - Slicing analysis in `docs/STRONG_BASELINE_CLOSURE.md`:
    - In Steady Windows ($63.74\%$ of test time): Posterior incurs a significant surrogate cost penalty of $+410,217\text{ kW}\cdot\text{h}$ ($p = 0.002$) over wind-speed bins.
    - In Transition Windows ($36.26\%$ of test time): The posterior penalty is compressed by nearly 75% to $+112,827\text{ kW}\cdot\text{h}$.
    - In Transition Windows, the posterior achieves a **lower violation rate** ($7.24\%$ vs. $8.36\%$) and **reduces unhedged shortage energy** ($86,592\text{ kW}\cdot\text{h}$ vs. $90,231\text{ kW}\cdot\text{h}$) compared to wind-speed bins.
  - Paired day-level cluster bootstrap over 35 observed test days confirms a statistically significant heterogeneity interaction:
    $$\Delta_{\text{transition}} - \Delta_{\text{steady}} = \mathbf{-296,123\text{ kW}\cdot\text{h}} \quad (p < 0.005).$$
- **LIMITATION**:  
  While the posterior provides superior risk hedging in transition windows (cutting shortage by $3.6\text{k kWh}$ and violations to $7.24\%$), doing so requires procuring more reserve headroom ($3.57\text{M}$ vs. $3.42\text{M kWh}$), so it does not yield net PSREI cost reduction under $\rho=10$.
- **SAFE MANUSCRIPT WORDING**:  
  > “The relative risk-cost trade-off becomes materially more favorable near operating transitions: posterior conditioning selectively reduces violation ($7.24\%$ vs. $8.36\%$) and shortage exposure ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$) near transitions, but this hedge remains more expensive under $\rho=10$ than wind-speed-binned quantile calibration. The significant interaction ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}123\text{ kW}\cdot\text{h}, p < 0.005$) establishes heterogeneity of the relative cost gap rather than a positive posterior cost advantage.”

---

### Q6. Could the 48.4% transition result merely reflect higher underlying losses?

- **CLAIM**:  
  Yes, if evaluated uncritically. Transition windows naturally exhibit larger point forecast errors and higher baseline losses. However, formal interaction testing proves that the posterior's performance profile shifts specifically in transition windows beyond mere proportional loss scaling.
- **EVIDENCE**:  
  - Loss concentration: Transition windows account for $36.26\%$ of observations and $33.0\%$ of global quantile loss ($5.33\text{M} / 16.13\text{M}$) and $31.3\%$ of wind-speed binned loss ($4.32\text{M} / 13.78\text{M}$).
  - Against unconditioned global quantiles, transition windows capture $48.38\%$ of total savings ($+892,535\text{ kW}\cdot\text{h}$ of $+1,825,410\text{ kW}\cdot\text{h}$, ratio $1.33\times$ its time share).
  - Against wind-speed bins, the interaction contrast $\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296,123\text{ kW}\cdot\text{h}$ ($p < 0.005$) demonstrates a structural model performance shift that cannot be explained by uniform error inflation.
- **LIMITATION**:  
  We explicitly concede that the raw "$48.4\%$ of total savings" metric is computed relative to an *unconditioned global quantile*, and does not prove that posterior conditioning outperforms wind-speed conditioning in transition windows.
- **SAFE MANUSCRIPT WORDING**:  
  > “Transition windows are not merely high-loss regions; formal interaction contrasts confirm they are the regions where secondary consequence signals alter tail risk allocations. However, we caution that raw transition savings percentages ($48.4\%$) reflect both underlying loss concentration and model sensitivity; relative to strong wind-speed binning, the posterior acts as a risk-hedging mechanism rather than a cost-reducing mechanism.”

---

### Q7. Does a deployable hybrid policy improve the full-population objective?

- **CLAIM**:  
  No. A deployable hybrid policy (using wind-speed conditioning in steady state and posterior conditioning when transition risk is indicated) achieves parity with wind-speed binning, but does not achieve a statistically significant improvement on the plant-wide objective ($+4,834\text{ kW}\cdot\text{h}$ difference, $p > 0.40$).
- **EVIDENCE**:  
  - Tested in `scripts/test_strong_baseline_closure.py` across 5 seeds:
    - Policy B (Wind-Speed Bins): $\text{PSREI} = \mathbf{13,784,320} \pm 1,438,833\text{ kW}\cdot\text{h}$.
    - Policy D (Validation-Frozen Deployable Hybrid): $\text{PSREI} = 13,789,154 \pm 1,434,721\text{ kW}\cdot\text{h}$.
    - Policy D10 (Pre-specified Band $|v-10.5| \le 1.0\text{ m/s}$): $\text{PSREI} = 13,801,696 \pm 1,438,458\text{ kW}\cdot\text{h}$.
  - Neither hybrid configuration delivers statistically detectable surrogate cost savings over the simpler Policy B.
- **LIMITATION**:  
  Because transition events comprise only $36.3\%$ of the time series and wind-speed binning is already well-calibrated, the switching overhead and conservative tail margin of the posterior prevent the hybrid policy from beating pure wind-speed binning plant-wide. The deployable hybrid policy remains statistically equivalent to wind-speed binning and must NOT be presented as an improvement.
- **SAFE MANUSCRIPT WORDING**:  
  > “A deployable hybrid policy that switches between wind-speed binning in steady states and posterior conditioning near boundary transitions matches wind-speed binning plant-wide ($13.79\text{M}$ vs. $13.78\text{M kW}\cdot\text{h}$, $p > 0.40$), but does not improve the overall objective. Wind-speed-binned quantile calibration therefore remains the operational minimum sufficient policy for plant-wide reserve sizing.”

---

### Q8. What remains novel after Zhao et al. 2026 already introduced physics-aware dynamic-graph MoE forecasting?

- **CLAIM**:  
  Our contribution does not lie in architectural novelty (graph MoE or physics-guided neural networks). Zhao et al. (IJEPES 2026) already explore this architectural family for symmetric point forecasting. Our contribution lies in an **information-theoretic and operational decision question**: establishing reliability boundaries under telemetry degradation, proving when recalibration suffices, diagnosing latent operating states from consequence SCADA channels, and testing whether recovered states alter asymmetric reserve-risk decisions.
- **EVIDENCE**:  
  - Concession of architectural neighborhood: Chenkai Zhao et al., *Int. J. Electr. Power Energy Syst.*, Vol. 176, 111769, 2026.
  - Falsification of MoE necessity: In our factorial ablations (Table~\ref{tab:h6-benchmark}), unrouted Dense GNNs achieve statistical parity with Routed MoE ($991\text{k}$ vs. $959\text{k kW}\cdot\text{h}$ on boundary slice, $p = 0.380$; $15.47\text{M}$ vs. $15.77\text{M kW}\cdot\text{h}$ full population). MoE routing is explicitly shown to be non-essential.
  - Consequence mechanism identification: Proving that active power curvature and variance ($C2$), rather than thermal ($C4$) or wake-only ($C3$) signals, recover the latent boundary under pitch withholding (`artifacts/channel_consequence_ablations.csv`).
- **LIMITATION**:  
  We explicitly disclaim any claim of proposing a novel neural network architecture, novel graph convolution, or novel mixture-of-experts routing layer.
- **SAFE MANUSCRIPT WORDING**:  
  > “Recent physics-aware dynamic-graph MoE models, such as Zhao et al. (2026), investigate whether architectural coupling of spatial graphs, physical guidance, and expert routing improves wind-power forecasting accuracy. We instead treat these components as diagnostic comparators and ask an information-and-decision question: when critical aerodynamic states become unobservable due to telemetry degradation, what information remains recoverable from secondary consequence channels, when is simple conditional recalibration sufficient without neural learning, and how recovered latent state information alters asymmetric reserve-shortfall decisions.”
