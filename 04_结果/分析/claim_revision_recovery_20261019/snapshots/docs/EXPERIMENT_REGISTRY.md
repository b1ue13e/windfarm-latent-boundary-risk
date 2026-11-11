# EXPERIMENT_REGISTRY.md

**Status:** AUTHORITATIVE EXPERIMENT REGISTRY  
**Effective date:** 2026-09-21  
**Scientific contract:** `docs/SCIENTIFIC_CONTRACT.md`

This registry exists to prevent result-seeking experiment drift. An experiment is scientifically complete when it answers its registered question with auditable evidence, **not** when it produces a favorable direction.

## 1. Registration rule

Before running a new decisive experiment, create an entry with all fields below.

### Required fields

- **Experiment ID**
- **Question**
- **Contract claim tested**
- **Status**
- **Information set**
- **Training-only privileged information**
- **Frozen point forecast**
- **Frozen target**
- **Primary baseline**
- **Secondary baselines**
- **Primary estimand**
- **Primary metric**
- **Secondary metrics**
- **Population slices**
- **Unit of replication**
- **Uncertainty procedure**
- **Positive outcome interpretation**
- **Null/negative outcome interpretation**
- **Failure/invalidity conditions**
- **Artifacts to produce**
- **Decision after result**

The following fields are **immutable after first execution** unless the entry is versioned as a new experiment:

- primary estimand;
- primary baseline;
- primary metric;
- population definition;
- unit of replication;
- uncertainty procedure.

Changing any of them after viewing results requires a new Experiment ID.

---

## 2. Frozen experiment entries

### EXP-Q1-001 — Active-power minimal recoverability

**Question:** Can issue-time active-power consequence signals recover meaningful MPPT/pitch boundary information when deployment-time pitch is withheld?

**Contract claim tested:** Q1 Recoverability.

**Status:** COMPLETED / EVIDENCE FROZEN.

**Information set:** Same arrival-time pitch-withheld deployment information set used by the consequence-channel ablation.

**Training-only privileged information:** Historical regime/pitch supervision is allowed and must be disclosed.

**Frozen point forecast:** Not the primary object; decision analyses must reuse the repository frozen forecast contract.

**Frozen target:** Declared MPPT/pitch regime for recoverability; frozen residual shortfall for downstream decision metrics.

**Primary baseline:** Full consequence suite C1.

**Secondary baselines:** C3 reactive-only, C4 thermal-only, C5 direction/yaw-only, C6 wake-only, C9 active-power+wake.

**Primary estimand:** Incremental recoverability of active-power-only representation under pitch withholding.

**Primary metric:** Brier score + NMI jointly interpreted.

**Secondary metrics:** ARI, transition recall, downstream PSREI diagnostics.

**Population slices:** Full pitch-withheld test set and transition windows.

**Unit of replication:** Independent model random seed, n = 5.

**Uncertainty procedure:** Seed-level summary; downstream claims must use the corresponding registered bootstrap/paired procedure.

**Observed result:** C2 Active-Power-Only: Brier 0.0112, NMI 0.461, ARI 0.647, transition recall 62.9%.

**Positive outcome interpretation:** Active-power signature retains usable boundary information.

**Null/negative outcome interpretation:** If active power fails, the latent-boundary recoverability claim must rely on another pre-registered channel or be weakened.

**Failure/invalidity conditions:** Leakage, future Patv use, pitch present at deployment, or label construction entering test-time input.

**Artifacts:** `artifacts/channel_consequence_ablations.csv`, `docs/CONSEQUENCE_SIGNAL_MECHANISM.md`.

**Decision after result:** Treat active power as the dominant mediator. Do not claim complex spatio-temporal structure is necessary.

---

### EXP-Q1-002 — Incremental wake/context necessity

**Question:** Does wake/spatial context add material recoverability beyond active power alone?

**Contract claim tested:** Architecture/mechanism necessity.

**Status:** COMPLETED / NEGATIVE-LEANING.

**Information set:** Same as EXP-Q1-001.

**Primary baseline:** C2 Active-Power-Only.

**Primary challenger:** C9 Active Power + Wake.

**Primary estimand:** C9 minus C2 recoverability improvement.

**Primary metric:** NMI and Brier; ARI/transition recall secondary.

**Observed result:** C2 NMI 0.461/Brier 0.0112 vs C9 NMI 0.463/Brier 0.0114; current evidence does not establish a meaningful necessary wake increment.

**Positive outcome interpretation:** Only if a pre-specified uncertainty test establishes a material increment may wake context be promoted to a mechanism claim.

**Null/negative outcome interpretation:** Active power remains the minimum-sufficient recoverability explanation.

**Decision after result:** Preserve the simpler explanation.

---

### EXP-Q2-001 — Strong matched-baseline closure

> **2026-10-17 evidence-freeze status:** The original +523,044 kWh closure is historical/superseded for current numerical reporting. The latest imported snapshot is `artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/` and is the sole canonical candidate, not claim-ready pending deep action/block/statistical audit. See `docs/EVIDENCE_FREEZE_20261017.md`.

**Question:** Does posterior conditioning reduce reserve-screening PSREI relative to the strongest matched-information wind-speed-conditioned quantile policy?

**Contract claim tested:** Q2 Incremental decision value.

**Status:** CURRENT CANDIDATE IMPORTED / DEEP NUMERICAL AND STATISTICAL AUDIT PENDING. The scientific direction remains no established plant-wide cost superiority; do not call this registered closure claim-ready until the 2026-10-17 freeze audit is complete.

**Information set:** Same arrival-time deployment information.

**Frozen point forecast:** Canonical frozen point forecast from `docs/FIXED_TARGET_CONTRACT.md`.

**Frozen target:** Canonical shortfall residual target.

**Primary baseline:** Policy_B — Wind-Speed Binned Quantile.

**Primary challenger:** Policy_C — Posterior-Conditioned Quantile.

**Primary estimand:** `PSREI(Policy_C) - PSREI(Policy_B)`.

**Primary metric:** PSREI, kWh.

**Secondary metrics:** Reserve procurement, violation rate, shortage exposure.

**Population slices:** Full / Transition / Steady.

**Unit of replication:** Seed-level policy outputs, with the registered block-bootstrap analysis for time dependence.

**Historical closure (superseded for current numerical reporting):**

| Slice | Delta PSREI C-B | Interpretation |
|---|---:|---|
| Full | +523,044 kWh | Posterior is more costly |
| Transition | +112,704 kWh | Posterior is more costly |
| Steady | +410,340 kWh | Posterior is more costly |

The historical closure remains immutable provenance only. The current candidate snapshot is:

| Slice | Delta PSREI C-B | Current candidate interpretation |
|---|---:|---|
| Full | +445,639 kWh | Posterior is more costly in the imported snapshot |
| Transition | +71,204 kWh | Risk-shape trade-off; no cost superiority established |
| Steady | +374,436 kWh | Posterior is more costly in the imported snapshot |

The current candidate uses `artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/strong_baseline_closure_summary.csv` and its native interaction JSON. It has receipt/output-hash verification but still lacks completed independent action/block/statistical audit. Current interaction mean is -303,232 kWh with 95% interval [-597,953, +19,013] kWh, which crosses zero. Do not promote these values to claim-ready status until that audit closes.

**Positive outcome interpretation:** A negative delta with appropriate uncertainty would support cost superiority.

**Null/negative outcome interpretation:** Preserve the negative result; only risk-shape changes may be claimed.

**Failure/invalidity conditions:** Baseline uses weaker information, target differs, point forecast differs, or result is reported only against global quantile.

**Artifacts:** `artifacts/strong_baseline_closure_summary.csv`.

**Decision after result:** Plant-wide decision superiority is not supported in either the superseded historical closure or the current candidate snapshot. Transition results are risk-shape trade-offs, not cost optimality. Current claim remains pending the freeze audit.

---

### EXP-Q2-002 — Transition-vs-steady heterogeneity

> **2026-10-17 evidence-freeze status:** The old significant interaction is superseded for current inference. The latest imported interaction is -303,232 kWh with 95% interval [-597,953, +19,013] kWh, which crosses zero; the current heterogeneity claim is pending deep audit.

**Question:** Is the posterior-vs-wind-speed-bin gap different in transition windows than in steady operation?

**Contract claim tested:** Transition-localized risk-hedging interpretation.

**Status:** COMPLETED.

**Primary estimand:** `Delta_transition - Delta_steady`, where Delta is posterior minus wind-speed-bin PSREI.

**Primary metric:** PSREI interaction contrast.

**Uncertainty procedure:** Predefined bootstrap contrast.

**Historical result (superseded):** Mean interaction approximately -296,123 kWh; the old artifact's interval excluded zero. It is retained as provenance only. The latest imported interaction is -303,232.337659 kWh, 95% interval [-597,952.520900, +19,013.037806] kWh, empirical P(interaction <= 0) = 0.967; the interval crosses zero and this snapshot remains pending deep audit.

**Positive outcome interpretation:** The decision trade-off is heterogeneous across operating regimes.

**Null/negative outcome interpretation:** Do not claim transition localization.

**Decision after result:** Historical interaction evidence is superseded for current inference. No current transition-vs-steady heterogeneity claim is certified until the latest snapshot audit closes; even then it would not imply transition cost superiority.

**Artifacts:** `artifacts/strong_baseline_bootstrap_contrasts.csv`.

---

### EXP-Q3-001 — Minimum-sufficient deployment map

**Question:** Which method is sufficient at each observability tier?

**Contract claim tested:** Q3 Minimum-sufficient deployment boundary.

**Status:** SYNTHESIS OF FROZEN EVIDENCE.

**Primary comparison:**

1. Fresh state → physical rule.
2. Observable delay/drift → state-conditional recalibration.
3. Pitch withheld + transition-sensitive risk → consequence-based representation.
4. Steady/sparse/zero-shot → simple local baseline unless matched evidence supports complexity.

**Primary metric:** No single leaderboard metric. The decision is conditional on observability and the registered decision objective.

**Positive outcome interpretation:** A method is retained only within the information regime where it adds necessary value.

**Null/negative outcome interpretation:** Fall back to the simpler method.

**Decision after result:** This is a conditional decision map, not a model ranking. P2 stop rule: no further graph, MoE, or hidden-state architecture expansion is authorized before E04; any complex representation must earn deployment necessity through an independent matched-information decision result, not recoverability or risk-shape metrics alone.

**Formal selection criterion (registered for E04):** For an arrived information set $\mathcal{I}$, strong direct baseline $b_{\mathcal{I}}$, fixed-target PSREI $C_P$, violation rate $V_P$, and pre-registered complexity preorder, select the lowest-complexity feasible policy:

```text
m*(I,rho,epsilon_C,epsilon_V) = argmin Complexity(m)
subject to U_(1-alpha)[C_P(m)-C_P(b_I)] <= epsilon_C
           U_(1-alpha)[V_P(m)-V_P(b_I)] <= epsilon_V
           U_(1-alpha)[V_P(m)] <= v_max
```

The thresholds, candidate set, complexity preorder, replication unit, and one-sided uncertainty procedure must be frozen before test evaluation. `NO FEASIBLE POLICY` is a valid result.

**E04 execution result (Metis v4; current status: PARTIAL VERIFIED / REVIEW BLOCKED):** With the frozen protocol, the selector returned `NO FEASIBLE POLICY` on the WTB Full population. The local wind-speed baseline itself had absolute violation UCB 0.11419, above `v_max=0.10`; Posterior C, Validation-Frozen Hybrid D, and Boundary Hybrid D10 had absolute violation UCB 0.11731, 0.11418, and 0.11389, respectively. C/D/D10 also had positive PSREI UCB differences. This resolves the registered failure branch but does not select a complex model or certify a universal minimum-sufficient law. Full execution and selector evidence are archived in `e04-minimum-sufficient-selector-20261017 v3`; independent falsification review is runtime-blocked and remains required.

---

## 3. Open decisive experiments

### EXP-02 (EXP-Q1-003) — Zero-Privileged-Pitch Supervision Boundary Protocol (零特权历史监督下的代理标签边界识别与备用闭环)

**Question:** If blade pitch is never recorded or available in historical training data, can consequence signals alone recover boundary-relevant representations, and does this zero-privileged representation provide incremental decision value for downstream reserve screening beyond a strong local conditional baseline?

**Contract claim tested:** Current UNKNOWN: pitch-never-recorded setting and zero-privileged supervision boundary.

**Status:** CONCLUDED / EVIDENCE FROZEN (NO STABLE ZERO-PRIVILEGED ADVANTAGE ESTABLISHED; DEFICIT NOT ESTABLISHED; h=6 INSTABILITY OBSERVED; FALSIFICATION GUARDRAIL OBSERVED).

**Verdict provenance (F4 correction, 2026-10-13):** the earlier status text read "DEFICIT ESTABLISHED". That verdict was hardcoded and not derived from the frozen statistics, and it overstated the evidence: h=1 shows a favourable point estimate that is statistically inconclusive, while h=6 shows an unstable policy dominated by one catastrophic seed rather than a uniform deficit. The verdict is now computed from the frozen CSV by `scripts/exp02_verdict.py` and rendered by `scripts/run_exp02_zero_privileged_supervision.py`.

**Statistical semantics (F4 correction):** the bootstrap field `P(delta <= 0)` (formerly mislabelled `p_val_delta_psrei`) is an **empirical non-inferiority probability**, not a two-sided p-value. Because PSREI is a *cost*, a HIGHER value means the challenger was non-inferior (cheaper or equal) in that resample. The superseded reading — requiring `delta < 0` *and* `p < 0.05` — was directionally self-contradictory.

**Execution & Findings Summary (2026-10-11 Metis A100 Benchmark):**
- **Artifact:** `artifacts/zero_privileged_supervision_benchmark.csv` (SHA256 verified) & `docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md`.
- **Compute:** Executed on Metis cluster node (`NVIDIA A100-PCIE-40GB`, Python 3.11, PyTorch 2.11.0+cu128) across 5 random seeds (201–205), 2 horizons ($h=1, h=6$), and $B=2000$ cluster Block Bootstrap.
- **Protocol & Leakage Hard Assertions:** All 6 mandatory protocol corrections verified. Zero pitch channel variance in input tensors passed. Model checkpoint selection verified strictly pitch-independent (validation pinball loss).
- **Primary Estimand Empirical Outcomes:**
  - **Horizon $h=1$:**
    - Primary Baseline (Site-Local Wspd-Bins): $\text{PSREI} = 7.02\text{M kWh}$, Violation $= 7.33\%$.
    - Primary Challenger ($\epsilon=50\text{ kW}$): $\text{PSREI} = 6.66\text{M kWh}$, $\Delta\text{PSREI} = -365.9\text{k kWh}$ ($p = 0.880$, 95% bootstrap CI $[-763.5\text{k}, +152.0\text{k}]$ includes zero, no statistically significant gain).
    - Sensitivity Probe ($\epsilon=20\text{ kW}$): $\Delta\text{PSREI} = -354.4\text{k kWh}$ ($p = 0.884$).
    - Sensitivity Probe ($\epsilon=100\text{ kW}$): $\Delta\text{PSREI} = +516.9\text{k kWh}$ ($p = 0.702$, severe violation spike to $12.35\%$).
    - Secondary Baseline (Direct Consequence MLP): $\Delta\text{PSREI} = -335.4\text{k kWh}$ ($p = 0.842$).
    - Oracle Reference (Privileged STGQ): $\Delta\text{PSREI} = +376.2\text{k kWh}$ ($p = 0.123$, non-competitive upper ceiling).
  - **Horizon $h=6$:**
    - Primary Baseline (Site-Local Wspd-Bins): $\text{PSREI} = 14.80\text{M kWh}$, Violation $= 8.83\%$.
    - Primary Challenger ($\epsilon=50\text{ kW}$): $\text{PSREI} = 18.25\text{M kWh}$, $\Delta\text{PSREI} = +3435.5\text{k kWh}$ ($p = 0.484$, violation $16.73\%$, severe policy instability).
    - Sensitivity Probe ($\epsilon=20\text{ kW}$): $\Delta\text{PSREI} = +6.9\text{k kWh}$ ($p = 0.489$, violation $9.07\%$).
    - Sensitivity Probe ($\epsilon=100\text{ kW}$): $\Delta\text{PSREI} = +105.8\text{k kWh}$ ($p = 0.392$, violation $7.58\%$).
    - Secondary Baseline (Direct Consequence MLP): $\Delta\text{PSREI} = +7845.5\text{k kWh}$ ($p = 0.203$, violation $25.00\%$).
- **Secondary Held-Out Pitch Alignment Diagnostics (Strictly Post-Hoc):**
  - Held-out pitch NMI on test set: $0.257$ ($h=1, \epsilon=50$), $0.128$ ($h=6, \epsilon=50$), $0.096$ (Oracle STGQ).
  - Demonstrates that weak consequence reconstruction captures noisy statistical correlation with pitch transitions, but this does NOT translate into deployable downstream decision superiority.
- **Formal Scientific Conclusion (Falsification Guardrail Enforced):**
  > **"Under the zero-privileged supervision protocol, no stable decision advantage over simple local wind-speed conditioning was established. At h=1 the point estimate is favourable but statistically inconclusive; at h=6 the policy is unstable and dominated by a single catastrophic seed."**
  *(Strict boundary: It is NOT claimed that active power consequence carries no mutual information, nor that real wind farms do not need pitch telemetry. A uniform "deficit" is NOT established — the h=1 point estimate is favourable, and the h=6 mean is driven by one seed rather than by a consistent sign. The empirical `P(delta <= 0)` values are non-inferiority probabilities, not two-sided p-values.)*

**Information set & Zero-Privileged Supervision Protocol:**
- **Strict Absence of Pitch:** Blade pitch angle ($\beta, \texttt{Pab\_mean}, \texttt{Pab\_std}$) is strictly absent and masked across training features, validation features, calibration features, and deployment test features.
- **Strict Absence of Pitch Labels in Supervision:** No aerodynamic regime label derived from pitch may enter model supervision, loss functions, early stopping criteria, or model checkpoint selection.
- **Proxy Label Specification ($\tilde{Z}_t$):** An electromechanical consequence proxy label is defined as:
  $$\tilde{Z}_t = \mathbb{I}(v_t > v_{\text{rated}} \;\land\; P_{\text{atv}, t} < P_{\text{rated}} - \epsilon)$$
  *Protocol Correction 1 (Self-Supervised/Weak-Supervised Target Only):* Because active power $P_{\text{atv}}$ is also present in model inputs, $\tilde{Z}_t$ shares consequence signals with the input. Therefore, $\tilde{Z}_t$ is strictly treated as an auxiliary pre-frozen self-supervised or weakly supervised training target ($\mathcal{L}_{\text{proxy}}$), **NEVER as independent ground truth**. Reconstructing $\tilde{Z}_t$ merely verifies that the model learns the proxy construction rule and does not prove recovery of the underlying physical control state.
- **Preregistered Physical Parameters & Sensitivity Grid:**
  - $v_{\text{rated}} = 10.5\text{ m/s}$ (WTB 1.5 MW turbine nameplate rated wind speed).
  - $P_{\text{rated}} = 1500.0\text{ kW}$ (WTB 1.5 MW turbine nameplate rated active power).
  - Main tolerance margin: $\epsilon = 50.0\text{ kW}$ ($3.3\%$ of rated capacity).
  - Preregistered sensitivity grid: $\epsilon \in \{20.0, 50.0, 100.0\}\text{ kW}$, pre-frozen prior to execution to test threshold sensitivity without post-hoc selection.

**Model Hierarchy & Baseline Separation:**
- **Primary Baseline:** Site-Local Wspd-Bins (10-bin local wind-speed conditional quantile, operating under identical arrival-time information constraints without pitch).
- **Secondary Baseline:** Direct Consequence Quantile MLP (predicts reserve quantiles directly from active power and local SCADA consequence features without any regime supervision).
- **Primary Challenger:** Zero-Privileged Weakly-Supervised Model (incorporates pre-frozen auxiliary loss $\mathcal{L}_{\text{proxy}}$ from $\tilde{Z}_t$ into representation learning, but strictly zero pitch access).
- **Oracle Upper Reference (Non-Competitive):** Privileged STGQ-Modular ($\lambda_{\text{align}} = 5000.0$, trained with true historical pitch regime labels). *Explicitly demarcated as an unfair oracle upper ceiling, NOT a fair baseline comparator.*

**Estimand & Metric Hierarchy:**
- **Primary Estimand:** Downstream matched-budget reserve screening cost difference:
  $$\Delta\text{PSREI} = \text{PSREI}_{\text{challenger}} - \text{PSREI}_{\text{local\_wspd}}$$
  evaluated at canonical horizon $h=6$ and $h=1$ under identical Newsvendor quantile target $\tau = 0.90$ ($\rho = 10.0, \Delta t = 1/6\text{ h}$).
- **Secondary / Exploratory Metrics:**
  - Violation rate difference $\Delta V$ and procurement/shortage components.
  - *Secondary Evaluation Only:* Held-out physical pitch alignment (NMI, ARI, Brier score, and transition recall evaluated against true withheld pitch labels on the test set).
  - *Strict Wall:* Held-out pitch metrics are computed strictly post-hoc for diagnostic characterization; they are strictly prohibited from guiding model selection, learning rate decay, or early stopping.

**Hard Assertions & Leakage Verification Protocol:**
- Hard assertion in execution script verifying zero pitch channel variance and zero pitch feature leakage in `train`, `val`, `calib`, and `test` input tensors.
- Hard assertion confirming model selection criterion uses exclusively validation pinball loss or consequence prediction error, with zero dependency on pitch-derived metrics.

**Falsification Guardrail & Negative Outcome Interpretation:**
- If the zero-privileged challenger fails to achieve statistically significant decision improvement over Site-Local Wspd-Bins ($\Delta\text{PSREI} \ge 0$ with 95% bootstrap CI including zero), the scientific conclusion is strictly bounded:
  > **"Under the zero-privileged supervision protocol, consequence signals alone failed to recover a deployable decision function superior to simple local wind-speed conditioning."**
- **STRICT PROHIBITION:** It CANNOT be concluded that *"active-power consequence carries no information"* (since privileged training already established its mutual information), nor can it be concluded that *"real wind farms do not need pitch telemetry"*. The conclusion is restricted exclusively to the learning protocol's capacity to induce actionable decision policies without privileged supervision.

---

### EXP-01 — External-Farm Matched Direct-Quantile & No-Graph Control (外部场站相同信息集配对直接条件分位数对照)

**Question:** 在外部风场（Penmanshiel 14机运营风机[排除WT03]、Kelmarsh 6机）上，去除时空图交互的局部风速分箱基线是否同样足以完成备用筛查？跨场站迁移表示相较于该局部条件基准是否依然缺乏决策增益？

**Turbine Population Harmonization Note:** Penmanshiel 名义总风机数为 15 台 (WT01–WT15)，其中 WT03 在全评估时间段因长期硬件故障停运且遥测全空，依官方标准预处理协议（Zenodo 记录及 `docs/REPOSITORY_EVIDENCE_MAP.md:19`）严格剔除，故实际评估运营机组统一为 14 台。

**Contract claim tested:** External validity, Decision Sufficiency, and Spatial Redundancy Causality across Observability Regimes.

**Status:** FULL EXP-01 CLAIM PENDING ADJUDICATION. The original v1, corrected-v2 benchmark, and retrospective v3/v4 outputs are historical and are not reinstated as current decision evidence. The 2026-10-15 `deterministic_matched_transfer_v1` branch is the current bounded/canonical-limited external evidence only; it does not close the full experiment, certify raw retraining, or establish universal transfer. See `docs/EVIDENCE_FREEZE_20261017.md`.

**Information set:** 严格限制于到达时刻各场站本地观测到的 SCADA 特征（本地风速、功率、气温），pitch 在测试期完全扣留。

**Training-only privileged information:** Historical pitch/regime labels allowed at training time for representations requiring alignment; zero pitch observable at test/deployment time.

**Frozen point forecast:** Frozen site-specific canonical point forecasts matching evaluation protocol.

**Frozen target:** Frozen shortfall residual target $s_t = \max(\hat{y}_t - y_t, 0)$.

**Primary baseline:** Site-Local Wspd-Bins (各场站本地校准的 10-bin 风速条件分位数).

**Secondary baselines:** No-Graph Architectural Control (无图架构对照模型：单机输入相同本地 SCADA 特征、完全断开风机间空间图连接的单机 MLP，4,865 参数，见 `docs/NO_GRAPH_CONTROL_AUDIT.md`；非严格容量等价，属于拓扑消融对照）.

**Tested challengers:** 跨场站迁移的 STGQ-Modular (110,012 参数) 及本地微调的 STGQ-Modular.

**Endpoint Hierarchy & Multiple Comparisons Protocol:**
- **Primary Endpoint:** 每场站 $h=6$ 处的配对差分 $\Delta\text{PSREI}(h=6) = C_{\text{transferred}} - C_{\text{local\_wspd}}$，按场站分别计算。
- **Secondary / Exploratory Endpoints:** 短视界 $h=1$ 处的配对差分 $\Delta\text{PSREI}(h=1)$；Fine-tuned STGQ 及No-Graph 对照模型表现；违约率差分 $\Delta V$ 及采购缺额分量指标。
- **Multiple Comparisons Guardrail:** 明确本实验未进行跨场站、跨视界、跨模型的族全局显著性（FWER）合并声明。所有次要终点仅用于辅助机制剖析与稳健性佐证，严格避免数据窥探与假阳性推断。

**Primary metric:** $\Delta\text{PSREI}(h=6)$ (kWh).

**Secondary metrics:** 违约率差分 $\Delta V$ (%), 绝对 PSREI (kWh), 绝对违约率 $V$ (%), 备用采购量 (kWh), 缺额暴露量 (kWh).

**Population slices:** Penmanshiel (14 turbines) 与 Kelmarsh (6 turbines) 全测试集，分别评估，严禁合并样本。

**Unit of replication:** 5 随机种子 (201–205).

**Compute budget:** 约 2.5 GPU·h (NVIDIA A100-PCIE-40GB / RTX 4090 或等效环境）.

**Uncertainty procedure:** 场站级日聚类 Block Bootstrap ($B=2000$).

**Historical results (corrected v2; superseded/not reinstated for current numerical reporting):**
- **Penmanshiel (14 turbines)**:
  - $h=6$ (**Primary Endpoint**): Site-Local Wspd-Bins 13,742,849 kWh (16.59% viol); Transferred STGQ-Modular $\Delta\text{PSREI} = +5,321,915$ kWh ($p = 0.003$, significant cost penalty); Fine-tuned $\Delta\text{PSREI} = -3,527,228$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +16,880,326$ kWh ($p < 0.001$).
  - $h=1$ (*Secondary Endpoint*): Site-Local Wspd-Bins 13,330,750 kWh (14.61% viol); Transferred $\Delta\text{PSREI} = +6,571,777$ kWh ($p < 0.001$); Fine-tuned $\Delta\text{PSREI} = -2,642,687$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +19,591,859$ kWh ($p < 0.001$).
- **Kelmarsh (6 turbines)**:
  - $h=6$ (**Primary Endpoint**): Site-Local Wspd-Bins 3,131,041 kWh (11.80% viol); Transferred STGQ-Modular $\Delta\text{PSREI} = +435,684$ kWh ($p = 0.196$, no significant improvement); Fine-tuned $\Delta\text{PSREI} = -2,001$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +3,403,611$ kWh ($p < 0.001$).
  - $h=1$ (*Secondary Endpoint*): Site-Local Wspd-Bins 3,107,821 kWh (11.07% viol); Transferred $\Delta\text{PSREI} = +515,318$ kWh ($p = 0.181$); Fine-tuned $\Delta\text{PSREI} = +174,455$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +3,667,533$ kWh ($p < 0.001$).

**Positive outcome interpretation:** 若迁移表示在 Penmanshiel 上战胜本地 Wspd-Bins 且战胜 No-Graph 控制模型，则确立了复杂地形下空间尾流图迁移的因果决策价值。

**Null/negative outcome interpretation:** 若本地 Wspd-Bins 同样在外部场站战胜迁移表示，则将“状态可恢复不等于决策优越”及“简单基线充分性”推广为跨场站普遍规律。

**Historical scientific verdict (corrected v2; not current claim-ready evidence):** 结果具有场站异质性。Penmanshiel 的 Transferred STGQ 在主终点显著劣于 Site-Local Wspd-Bins；Kelmarsh 的差异为正但未达显著。该版本保留为历史结果，不能在当前冻结状态下重新作为最终外部主张。

**Current bounded branch:** `deterministic_matched_transfer_v1` (audit `artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json`) reports h=6 deltas of +6,322.70 kWh for Kelmarsh (CI crosses zero) and +356,014.40 kWh for Penmanshiel (positive cost penalty). This branch is bounded evidence with existing weights/local forecasts/calibration and evaluated windows; it is not a full EXP-01 closure. The original v2 and v4 numerical claims remain superseded or withdrawn according to `docs/EVIDENCE_FREEZE_20261017.md`.

**Scientific Claim Boundaries (严格禁止过度推断):**
1. **支持结论:** 在独立 site-specific frozen point forecast、相同到达时刻信息集、pitch 完全扣留和预注册 bootstrap 协议下，Penmanshiel 的 Transferred STGQ-Modular 在 h=6 主终点显著增加 PSREI；Kelmarsh 的正向差异未达显著。两个场站均未显示 Transferred STGQ 相对本地 10-bin 基线的显著正向决策改善。
2. **严禁推断:**
   - 严禁声称“所有外部风场都不需要图结构”；
   - 严禁声称“复杂地形不存在空间决策价值”；
   - 严禁声称“已经证明了跨场站普遍因果规律”。

**Failure/stopping conditions:** 若外部场站本地风速数据缺失率 > 20%，该场站停止评估（Penmanshiel 实测 0.63%，Kelmarsh 实测 2.10%，均顺利通过门槛）。

**Artifacts to produce:** 
- `artifacts/external_matched_control_benchmark.csv` (corrected v2, 80 行全数据结果; artifact `external-matched-control-benchmark v2`, SHA256 `596f46e0be8d71ab7a9965dbe4c481cc717b31c083fe288441a9ca9a39c3966e`; v1 superseded)
- `artifacts/no_graph_architecture_audit.json` (架构参数量与复杂度对比审计)
- `docs/NO_GRAPH_CONTROL_AUDIT.md` (架构参数与命名规范裁决文案)
- `artifacts/exp01_pitchmasked_v4/` (Retrospective repair v3/v4: verified WTB checkpoints, full Pab_mean & Pab_std withholding; artifact `exp01-pitchmasked-retrospective-v3 v2`; strictly retrospective, historical v2 retained byte-intact)
- `docs/PHASE2_EXP01_AND_JOINT_UNCERTAINTY_AUDIT.md` (Phase 2 retrospective protocol audit and joint uncertainty verification)

**Retrospective Repair Note (2026-10-14, Phase 2):**
为彻底消除 source checkpoint 仅靠目录名推断以及推理前 pitch 扣留不够彻底（仅屏蔽 Pab_mean 未显式屏蔽 Pab_std）的方法学隐患，Phase 2 进行了追溯性重计算（Retrospective Reanalysis）：
1. 强制断言 checkpoint metadata 内 `dataset == 'wtb'` 且 `num_nodes == 134`；
2. 在模型 forward 前，对历史特征 `x_hist`、特征掩码 `feature_mask_hist` 以及 `anchor_physics` 中的 `Pab_mean` 与 `Pab_std` 进行双重置零并增加非零断言；
3. 产物独立存放于 `artifacts/exp01_pitchmasked_v4/`（工件 `exp01-pitchmasked-retrospective-v3` v2），不覆盖历史 v2 CSV；
4. 追溯结果：Penmanshiel h=6 处 $\Delta\text{PSREI} = -315,400$ kWh (95% CI $[-1,590,024, +970,006]$, $P(\Delta \le 0) = 0.7084$)；Kelmarsh h=6 处 $\Delta\text{PSREI} = +352,434$ kWh (95% CI $[+59,970, +736,901]$, $P(\Delta \le 0) = 0.0074$)。场站间显著异质性依然保持，未证实跨场站正向决策迁移。

**Decision after result:** Preserve every historical result and its validity boundary. Current external decision claims remain pending adjudication; only the deterministic bounded branch may be cited for limited evidence, and no branch may be promoted to a universal transfer claim.

---

### EXP-Q2-003 — External-site matched direct-quantile closure

> **Status: RETIRED / SUPERSEDED by EXP-01 corrected v2 (2026-10-13).**
> This entry was registered before execution as the external-site closure question. It was subsequently
> answered by **EXP-01** (`docs/EXPERIMENT_REGISTRY.md` §EXP-01), which executed the external-site matched
> direct-quantile comparison (Site-Local Wspd-Bins primary baseline vs. transferred and fine-tuned
> STGQ-Modular, two farms evaluated separately, 5 seeds, hierarchical joint uncertainty).
> Retaining it as an open "PROPOSED / BLOCKED" entry alongside a completed EXP-01 created two conflicting
> statements of the same experiment's status in one authoritative registry (reverse-audit defect F6).
> This entry is therefore retired as a **duplicate of EXP-01** and must not be cited as an open experiment.
> The residual, genuinely unanswered sub-question — a same-information-set **site-local latent-state
> posterior** policy rather than a transferred representation — is not covered by EXP-01 and is recorded
> below as the only still-open part.

**Question:** On each external wind farm separately, does latent-state conditioning add value beyond a matched direct conditional quantile under the same information set?

**Contract claim tested:** External validity.

**Status:** RETIRED as a duplicate registration of EXP-01 (2026-10-13). The `site-local latent-state posterior challenger` arm remains **NOT EXECUTED**.

**Answered by:** EXP-01 corrected v2 — external-site matched direct-quantile closure executed with Site-Local Wspd-Bins as primary baseline; a statistically significant decision *gain* for transferred representations was not established at either farm (Penmanshiel h=6 significant cost penalty; Kelmarsh h=6 non-significant positive delta).

**Primary baseline:** Site-local matched direct quantile using the same deployment-time features.

**Primary challenger:** Site-local (not transferred) latent-state posterior policy — **this arm was never run**.

**Population:** Each site separately; no pooled headline estimand unless separately pre-registered.

**Primary metric:** Site-specific PSREI difference.

**Secondary metrics:** Violation, shortage, reserve procurement, calibration.

**Negative outcome interpretation:** Site remains a boundary probe; do not claim generalization.

**Decision after result:** Report positive, neutral, and negative sites separately.

---

### EXP-03 — Integer-step asynchronous packet arrival envelope

**Question:** Under an explicit out-of-order telemetry protocol, how does causal packet arrival and missingness alter PSREI relative to delay, and does the challenger remain comparable to Site-Local Wspd-Bins under the same arrival trace and missing mask?

**Contract claim tested:** Q2 Incremental decision value under asynchronous arrival; current UNKNOWN until execution.

**Status:** CONCLUDED UNDER HARDENED RECONCILED PROTOCOL (EXP-03-R; 2026-10-13).  
*(Historical note: The 2026-10-12 preliminary run was invalidated per `docs/EXP03_INVALIDATION_NOTICE.md` due to standardized proxy feature clipping and row-drop population collapse. All defects F1–F4 have been resolved in the hardened rerun).*

**Protocol Hardening & Rectification Summary:**
- **F1 Resolved:** All 5 SCADA feature channels consumed by models (including `Patv_hist`) are now symmetrically delayed in the causal simulator (`scripts/run_exp03_async_benchmark.py:164-183`).
- **F2 Resolved:** Physical proxy thresholds ($V_{\text{rated}}=10.5\text{ m/s}$, $P_{\text{rated}}=1500.0\text{ kW}$, $\epsilon=50.0\text{ kW}$) are computed on unstandardized physical features using `metadata.json.feature_stats` (`:67-88`).
- **F3 Resolved (population):** The evaluated dispatch-anchor population is constant at **408,937 cells** ($h=1$) / **408,939 cells** ($h=6$) across all delay steps $\tau \in [0, 6]$; no row-drop collapse. **Boundary — this is a fixed-population *LOCF-imputed* curve, not a fixed-population *fresh*-observation curve:** causal Last Observation Carried Forward raises `stale_fraction` from 0.0% at $\tau=0$ to **99.79%** at $\tau=6$ (with `drop_fraction` rising to 60.25%). At $\tau=6$ essentially every evaluated input is a carried-forward stale value, so the late-delay points measure degradation under near-total staleness rather than a partially-refreshed stream.
- **F4 PARTIALLY RESOLVED — provenance artifact is a SAMPLE, not the full grid (see F6 finding):** `artifacts/exp03_async/arrival_trace.jsonl` materializes 1,440 packets covering only **nodes 0–2 × the first 144 steps × $\tau=0$** (all `arrival_time == event_time`, i.e. zero delayed packets). It does **not** evidence the executed 7-delay × 5-seed × 2-horizon grid. `missing_mask.json` is a 48-element all-`false` placeholder. The digest written to `input_trace_hash.txt` (`18079b46…`) is an internal Python `hashlib` accumulator over `async_feat[:144,0,:]` and `dropped_mask[:144,0,:]` during execution (`:498,515-516,597`); it is **not** a SHA-256 of `arrival_trace.jsonl` (which hashes to `fcc119806e6bccad0f458a9cd6188c3150ece307ca0c63acd6b395d7904b3d9c`), and it is not recomputable from any archived artifact. Earlier wording calling it the "Full-Grid SHA-256 provenance hash of the full-grid arrival stream" was inaccurate and has been corrected. Packet-level provenance for the evaluated grid remains **OUTSTANDING**.

**Execution & Findings Summary (Hardened Reconciled Benchmark; 2026-10-13):**
- **Compute:** Executed across 5 random seeds (201–205), 2 horizons ($h=1, h=6$), and delay grid $\tau \in \{0, 1, 2, 3, 4, 5, 6\}$ (0 to 60 minutes) under strict causal buffer policy and information parity on 408,937 fixed test cells.
- **Trace Integrity:** Internal execution digest (NOT a full-grid provenance hash): `18079b46d01a399d47df681ec0fa48ab4a55bf0860c8bc99df2c15480bb13d49` — see the F4 boundary above.
- **Primary Estimand & Critical Point $\tau^*$ (Hierarchical Joint Bootstrap):**
  - $h=1$: $\tau^* = 1$ integer step (10 minutes). At $\tau=0$, $\text{Median } \Delta\text{PSREI} = -590.9\text{k kWh}$ (Joint 95% CI $[-1,142.5\text{k}, -34.9\text{k}]$, $P(\Delta \le 0)=0.985$). At $\tau \ge 1$, the joint 95% CI crosses zero ($\tau=1$: CI $[-977.2\text{k}, +128.5\text{k}]$, $P(\Delta \le 0)=0.897$; $\tau=6$: CI $[-416.2\text{k}, +635.7\text{k}]$, $P(\Delta \le 0)=0.239$).
  - $h=6$ (**Primary Endpoint**): $\tau^* = 0$ integer steps (0 minutes). At all delay levels $\tau \in [0, 6]$, the Joint 95% CI spans zero ($\tau=0$: $\text{Median } \Delta = -158.0\text{k kWh}$, CI $[-804.3\text{k}, +327.7\text{k}]$, $P(\Delta \le 0)=0.706$; $\tau=6$: $\text{Median } \Delta = -24.6\text{k kWh}$, CI $[-584.2\text{k}, +500.5\text{k}]$, $P(\Delta \le 0)=0.434$). No statistically significant decision gain over Site-Local Wspd-Bins is established.
- **Operating Target Sensitivity:**
  - $h=1$: Challenger violation rate remains safely controlled ($7.34\%$ at $\tau=0$ to $9.64\%$ at $\tau=6$), while Site-Local Wspd-Bins stays at $7.33\%\text{--}7.87\%$.
  - $h=6$: Challenger violation rate is $10.77\%\text{--}11.05\%$, while Site-Local Wspd-Bins stays well within target at $8.66\%\text{--}8.83\%$.
- **Falsification & Scientific Closure:** Reverse null confirmed under hardened protocol. Complex representation networks provide no hedge against telemetry latency. Simple local conditional baselines maintain superior violation control without spatial-telemetry sensitivity. Output is strictly bounded as a **synthetic asynchronous envelope** and not extrapolated to industrial fleet prevalence.

**Information set:** Integer dispatch steps ($t \in \mathbb{N}$, one step corresponds to 10-minute SCADA dispatch). Each packet explicitly stores `(event_time, arrival_time, channel_id, sequence_id)`. At dispatch step `t`, every model reads only packets with `arrival_time <= t`; packets arriving simultaneously are deterministically ordered by `(arrival_time, sequence_id, channel_id)`. Causal buffer drops packets later than finite `max_lateness` deadline without future backfill.

**Training-only privileged information:** None for the asynchronous arrival mechanism. Hidden pitch remains withheld wherever the matched deployment protocol requires it; no future target, future packet, or post-hoc arrival correction may enter inputs.

**Frozen point forecast:** The canonical frozen point forecast from `docs/FIXED_TARGET_CONTRACT.md`.

**Frozen target:** The canonical shortfall residual target `s_t = max(yhat_fixed - y, 0)`.

**Primary baseline:** Site-Local Wspd-Bins (10-bin conditional quantile) evaluated using the identical packet trace and identical missingness mask. Wspd-Bins receives the exact same asynchronous contamination and missingness as challenger models.

**Secondary baselines:** Challenger model (Zero-Privileged Representation Net) under the same trace/mask; synchronous-arrival control; optional no-packet-delay control only as a diagnostic reference.

**Primary estimand:** The paired PSREI-vs-delay curve $\Delta\text{PSREI}(\tau) = \text{PSREI}_{\text{challenger}}(\tau) - \text{PSREI}_{\text{local\_wspd}}(\tau)$ over the pre-registered delay grid $\tau \in \{0, 1, 2, 3, 4, 5, 6\}$, with $\tau^*$ defined as the smallest delay at which the curve's paired block-bootstrap 95% uncertainty interval excludes the zero-gain region ($\Delta\text{PSREI} \ge 0$). $\tau^*$ is not defined by a violation-rate threshold alone.

**Primary metric:** PSREI-vs-delay curve and critical crossover point $\tau^*$, reported by horizon ($h=1, h=6$) across 5 random seeds (201–205); no pooled headline estimand across heterogeneous farms unless registered separately.

**Secondary metrics:** Violation-rate-vs-delay, reserve procurement, shortage exposure, packet late/drop fractions, missingness by channel, and sensitivity of operating targets at 5%, 10%, and 15% violation. The 10% target is pre-registered as a nominal operational target corresponding to Newsvendor optimal quantile $q^* = 1 - 1/\rho = 0.90$ ($\rho=10.0$), not as the unique or axiomatic breakdown threshold.

**Population slices:** Full test population ($N=134$ turbines, $T=4981$ steps) plus pre-declared steady/transition diagnostic slices. Synthetic results are strictly labeled **synthetic asynchronous envelope** and cannot be extrapolated to industrial arrival-rate prevalence or real-world network outage frequency.

**Unit of replication:** Independent simulator seeds and model seeds (201–205), reported separately; temporal dependence handled with 35-day cluster Block Bootstrap ($B=2000$).

**Uncertainty procedure:** Frozen seed list and paired day-cluster bootstrap applied within each delay point; all methods share each realized trace and missing mask. No post-hoc threshold or favorable slice selection.

**Positive outcome interpretation:** A challenger curve that is lower than the local baseline across a pre-declared delay region, with uncertainty excluding zero at the registered points ($\Delta\text{PSREI}(\tau) < 0$, $p < 0.05$), supports incremental decision value only for that evaluated envelope.

**Null/negative outcome interpretation:** A flat or positive $\Delta\text{PSREI}(\tau)$ curve supports the simpler local baseline and leaves asynchronous decision superiority unestablished; it does not imply that industrial telemetry has the simulated arrival distribution.

**Failure/invalidity conditions:** Missing event/arrival/sequence fields; nondeterministic same-arrival ordering; any packet with `arrival_time > t` exposed at step `t`; future backfill; unequal traces or masks across methods; unreported drops; input trace hash absent or mismatched; absence of packet-level unit tests.

**Artifacts to produce:** `scripts/exp03_async_packet_protocol.py`, `tests/test_exp03_async_arrival.py`, `artifacts/exp03_async/arrival_trace.jsonl`, `artifacts/exp03_async/missing_mask.json`, `artifacts/exp03_async/protocol.json`, `artifacts/exp03_async/input_trace_hash.txt`, `artifacts/exp03_async/psrei_vs_delay.csv`, and `docs/EXP03_ASYNCHRONOUS_REPORT.md`.

**Decision after result:** Preserve negative/null results, label all synthetic outputs as an asynchronous envelope, and update the scientific contract only through a separately reviewed change.

---

## 4. Agent execution rules

For every new experiment:

1. Register first.
2. Freeze comparator and estimand before execution.
3. Run the experiment.
4. Record all outcomes, including negative and null results.
5. Do not change the scientific contract directly from a favorable result.
6. Invoke `scientific-falsifier`.
7. Only after falsification may a contract update be proposed.
8. A contract update must be a separate, reviewable commit.

## 5. Prohibited registry behavior

- no deleting negative experiments;
- no changing the primary baseline after seeing results;
- no replacing full-population results with a favorable slice;
- no using a weaker comparator because the stronger comparator loses;
- no changing significance procedures after inspecting p-values;
- no renaming a failed hypothesis into a “new contribution— without a new registered question.

## RERUN-20261015 — Registered raw-data replication and protocol correction

Status: REGISTERED / NOT YET EXECUTED at entry creation. Full frozen scope, information set, primary baseline, estimand, population, seeds, uncertainty procedures, failure conditions, artifact requirements and withdrawal rules are specified in docs/RAW_REPLAY_PROTOCOL_20261015.md. This campaign replays existing experiments and separates retrospective corrections from confirmatory evidence; no scientific claim ceiling or success threshold is changed. Newly detected corrections: channel h6 used residual index1 rather than5; hardcoded channel decision references were unmatched; asynchronous initial LOCF exposed a potentially unarrived value. Corrected outputs must be versioned and cannot overwrite historical arrays or inherit their scientific validity.

### RERUN-20261015 addendum before affected stages

See docs/REPLAY_CORRECTION_ADDENDUM_20261015.md for EXP02 physical-power scaler correction and external raw-window normalization correction, registered before those stages train/evaluate. None changes epsilon, primary comparator, decision threshold or seed count. Claim dispositions are explicitly recorded in docs/REPLAY_CLAIM_DISPOSITION_20261015.md. Withdrawal is not successful experimental reproduction.

### EXP01 v4 invalidation (2026-10-15)

The earlier retrospective repair note is superseded as a validity claim: archived forecasts refer to original chronological windows while v4 evaluates offset120/720-day targets. Integer anchors coincide but targets, masks and physical times differ. All v4 numerical decision claims and directions are withdrawn from current interpretation; old files remain immutable. See docs/EXP01_INVALIDATION_20261015.md and falsifier section13. New raw-window matched evaluation is NOT RUN yet. No older result is reinstated as valid by this notice.

### RAW-PHASE-FROZEN-V1

Registered corrected phase scan before execution: see REPLAY_CORRECTION_ADDENDUM_20261015.md.
Same canonical shortfall across models/delay, fixed raw-wind boundary diagnostic population,
matched auxiliary-head training targets/masks/anchors, ten-bin wind baseline, same-channel
physical calibration. Old mixed-target/moving-population curves remain historical only.
No positive result or numerical agreement with an old value is an acceptance criterion.

### RAW-FACTORIAL-MASKED-V1 and RAW-ACTIVE-POWER-V2

Registered before corrected execution in the Metis campaign. See the correction addendum:
factorial A/B use identically configured backbones differing only in alignment loss,
matched double-pitch-withheld inference and common canonical shortfalls. Primary
comparator K is ten wind bins; h6 primary, h1 secondary; full and fixed wind-boundary
populations reported together. All five seeds201–205, rho10 and validation q0.90 retained.
Five-epoch linear heads use up to20000 validation cells and descriptive seed mean/SD;
no significance is inferred from these summaries. Shuffled posterior/label controls
affect calibration and test, and unknown oracle labels use global reserve fallback.
Oracle arms remain non-deployable diagnostics; J aliases C and is not a separate method.
Active-power diagnostic retains its three epochs /200000-cell budget and all conditions;
transitions require two valid adjacent labels, and decision results are labelled as
valid-regime cohorts. No hardcoded positive direction, mechanism or thermal-omission
conclusion is permitted. Old inconsistent artifacts remain historical, not overwritten.

### METIS-RAW-20261015

Execution host change authorized by user before further training. Same corrected
protocol/configurations, seeds, targets, comparator and uncertainty procedures; isolated
cloud workspace, raw hashes checked, new raw preprocessing and fresh fits. Partial
local attempts remain archived as interrupted/completed-local, never mixed into a
homogeneous cloud five-seed result. No optimizer-resume claim: interrupted fits restart
from scratch. PBS jobs, environments, code/data hashes and receipts are evidence;
submission/queuing does not count as experiment execution or scientific completion.

### RAW-FACTORIAL-FOUR-CONDITIONS-V2 (2026-10-15, before execution)

Extends the still-unfinished factorial replay to its four original conditions:
clean, delay6, pitch_withheld, delay6_pitch_withheld; five seeds201–205 in each.
See docs/FACTORIAL_FOUR_CONDITIONS_PROTOCOL_20261015.md. Keep primary h6,
secondary h1, rho10, dt1/6h, validation q0.90 and the existing diagnostic wind-bin
comparator K. The information set of K is the physical wind read from the SAME
degraded anchor_physics batch seen by all three checkpoint families, never fresh
issue-time wind in a delayed arm. Both pitch features/masks and physical pitch
are withheld where specified; delays stall all features/masks/graph symmetrically.
Canonical shortfalls/masks/time/node and fixed ex-post boundary slice are shared
across all arms/conditions. This is a factorial diagnostic, not a claim that K
exploits fresh pitch or is the strongest baseline when pitch is available.
No architecture necessity/decision superiority follows merely from these controls.
Report all20 runs, descriptive seed mean/SD, reserve/shortage/cost/violations and
paired day-block arrays; no invented p-values or significance gate. Preserve old
single-condition output separately. Frozen running source tree remains unchanged;
the versioned extension source/protocol/config/receipt must be independently hashed.

### Factorial input-readiness scheduling addendum (before any condition run)
The numerical protocol is unchanged. docs/FACTORIAL_READINESS_SCHEDULING_20261015.md registers a dedicated PBS audit of all20 actual required model outputs and the one shared canonical residual/cache before replacing the blanket afterok(core) wait. Preserve software-test afterok and add audit afterok; do not release on file existence or favorable values. This removes unrelated channel/EXP02/EXP03 scheduling waits only, and does not waive any scientific claim gate, four-condition result, five-seed requirement or final review. Original dependency/metadata and the hashed addendum/audit/release records remain provenance.

### RAW-CORE-RETRY-IMPORT-V1 / FACTORIAL-UNEXECUTED-REQUEUE (before retry)
Core242595 failed at JSON serialization with NameError: json is not defined after
five-seed calculations; its output/log directory is retained as failed, never
certified. Correct only the missing standard-library import. Deploy the repaired
script and retry orchestration under metis_execution, leaving the frozen runtime
untouched. New strong-baseline output/log paths are required. Keep the original
command arguments, comparator, population, seeds, metrics and uncertainty. After
real PBS software checks, retry from verified completed weights/canonical data;
do not retrain, regenerate a second canonical target or claim optimizer resume.
Untouched channel/EXP02/EXP03 stages follow under PBS; failure blocks their chain.

Array242602 has four clean201-204 execution receipts with exit0, while the other
sixteen indices have no execution receipt. Full PBS terminal accounting is
incomplete (Exit_status absent); preserve it and do not infer successful completion
of the array. Keep the four completed artifacts and audit their hashes and row
coverage. Only the sixteen unexecuted indices may be resubmitted unchanged after
verifying original extension/dependency hashes and the actual242623 INPUTS_VERIFIED
report/exit0. Bind the new aggregate to the new array and all20 real per-run receipts.
Do not rerun or overwrite completed rows, weaken gates or infer a full-condition
result from the first four runs. Scheduler termination cause remains UNKNOWN until
adequate accounting supports it. This is execution recovery, not a new hypothesis.

### Factorial evidence arithmetic audit (before validator execution)
Validate the twenty real successful receipts and all deep output hashes, forty-four
unique cells per run, the exact canonical targets/masks/time/node and fixed boundary
population. Recompute CSV reserve, shortage, PSREI, violation and native paired daily
arrays from the saved per-cell actions using the same NumPy operations; require exact
round-trip values, without fitting a tolerance. Verify actual head checkpoints and
five-epoch histories/selected validation indices. Recompute the descriptive five-seed
summary from the full880 rows and require the same values. This is a read-only evidence
check in a PBS CPU allocation, not a new decisive experiment or a favorable-result gate.
Any mismatch is preserved and diagnosed; do not overwrite original outputs or change
the registered scientific thresholds, seeds, comparator or uncertainty procedure.
Per-run arithmetic uses round-trip CSV parsing. The aggregation-stage audit separately
replays the frozen summarizer's actual default pandas CSV parser before its groupby;
record any parser-induced representation differences explicitly. Exact comparisons
apply at each implemented stage; no fitted numerical tolerance or result change.
Before the validator runs, include exact CPU reconstruction of A/B actions from
the saved contexts and trained head weights with the original4096-cell batches
and clipping. Report any platform/inference mismatch as non-exact, without fitting
a tolerance or changing the stored actions/weights.

### RAW-EXTERNAL-TRANSFER-EVIDENCE-AUDIT-V1 (before execution)
Audit actual Metis transfer242600 without changing its methods/results. Require
real exit0/nonempty input/output receipts and source/raw-cache/model hashes. On
PBS GPU allocation, repeat the original pitch-masked forward with saved WTB
aligned_force weights for Kelmarsh/Penmanshiel201–205 and require exact saved-gate
agreement; any non-exact inference is retained and diagnosed, without fitted
tolerance. Reconstruct the same local frozen forecast/target/mask/time/node and
window identities, five posterior bins/ten wind quantile bins/q0.90/rho10/dt1/6.
Independently execute per-cell action/metric/native144-issue-block reconstruction,
20 seed rows and four joint statistics using original5000 resamples and RNG20261014.
Write a new audit tree with derived calibration/actions/residuals/blocks/bootstrap
draws; never overwrite original transfer CSV/NPY/NPZ or retrain weights to pass.
Replay each implemented arithmetic stage exactly. Report differences between
summed native paired contrasts and differences of separately summed costs as
operation-order observations, not a fitted acceptance threshold. The block unit
is consecutive144 eligible issue indices (last block may be partial), not a claim
that these align with natural-calendar/weather-event boundaries. Empirical
P(delta<=0) is not a two-sided p-value. No prior invalid EXP01 result is reinstated;
this audit supplies evidence only for the current registered raw-window replay.
The scope is frozen WTB gate weights with target-local normalization and validation
calibration, conditional on the same local frozen point-forecast product supplied
to both policies. This does not establish an entirely zero-shot pipeline or a
pitch-never-recorded/pitch-free forecasting pipeline.

### INFERENCE-EXACTNESS-FAILURE-DIAGNOSIS-V1 (before diagnostic execution)
External audit242736 failed the frozen exact gate comparison on Kelmarsh201/val.
Preserve its full stdout, source, inputs and non-exact output; current external
exact-reproduction certification is FAILED, not rescued by tolerance. Diagnose
the same frozen weights/cache/split by two original-helper GPU forwards in a
fresh default process and two in a fresh explicitly deterministic process
(CUBLAS_WORKSPACE_CONFIG=:4096:8, deterministic algorithms/cudnn on, benchmark/TF32
off). Record actual backend flags, environment, shapes, dtypes, exact mismatch
counts/max differences and all replay arrays. This is a numeric execution diagnosis,
not a new scientific performance claim. No seed count, comparator, target, metric,
uncertainty or exact-equality gate is weakened. No original gate/CSV is overwritten.
Only observed repeatability may motivate a separately registered execution repair;
old non-exact claims/results remain uncertified and retained. Do not attribute a
specific kernel or original unlogged backend setting without evidence.

### EXTERNAL-DETERMINISTIC-EXECUTION-REPAIR-V1 (before new production)
Actual PBS diagnosis242739 observed non-exact default repeated forwards on the
same Kelmarsh201/val inputs (49156 changed float32 values, max7.152557373046875e-7),
while the predeclared deterministic profile gave exact repeated forwards. This
does not certify other inputs or identify a particular kernel/original backend.
Keep failed242736 and the original matched_transfer tree permanently unchanged.

Create deterministic_matched_transfer_v1 in a new directory using the same
complete WTB/source and local forecast weights, raw windows, validation/test
populations, masks, posterior5/wind10 quantile bins, q0.90,rho10,dt1/6,
201–205 seeds and5000/RNG20261014 hierarchical procedure. Explicitly apply the
diagnosed deterministic execution profile before torch/CUDA initialization;
record all flags and code/input/environment hashes. This is an execution repair,
not a favorable-result trial. No retraining/resume or scientific gate relaxation.

The producer retains the original mathematical code; allowed source adaptations
are startup profile configuration, explicit workspace for out-of-tree deployment,
accurate preregistration/source-policy provenance and final manifests. Preflight
uses a PBS GPU allocation to execute an isolated real producer import/profile
smoke check without running its main experiment, in addition to input checks.
A separately allocated
GPU audit must reconstruct all20 gates/rows/native blocks/four joint statistics
under the SAME explicit profile and exact equality gate. Any failure is retained
and stops corresponding certification; no tolerance tuning. New outcomes cannot
retroactively certify old non-exact outputs or any full-paper/raw-training claim.
Before accepting the repair's unchanged-scientific-specification statement, a
separate PBS CPU comparison requires identical20 row keys, evaluated counts,
checkpoint/summary identities and exact non-neural wind-baseline costs/violations
between old and new versions. Archive all posterior/CI differences and raw-gate
differences as observations; unchanged argmax is not a decision-value gate. The
old version remains uncertified even if derived metrics happen to agree.


### RAW-DOWNSTREAM-PHASE-EXECUTION-REPAIR-V1 (registered2026-10-16 before retry)
ActualPBS242629 phase scan failed exact training-target comparison after two new heads. Complete failed attempt preserved. Direct saved-array diagnosis: same anchors/masks,925335 valid finite values exactly equal;16722 matching NaN placeholders all outside target mask. Default np.array_equal rejects matchingNaNs. New version requires identical anchors/masks/shapes,finite values on every original valid cell,identical nonfinite positions and whole-array equality with only co-located NaN placeholders equal;no value tolerance/no valid-cell drop,no scientific acceptance relaxation. Reject changed valid values,changed invalid finite values,misplacedNaNs,andanynonfinitevalidcell. Preserve original failed arrays/logs,never relabel the old attempt passed. Source-review correction before any retry: original frozen source already defines cond_id in the lead loop; the initial undefined-name diagnosis was mistaken and is withdrawn. Keep original condition naming, with no claimed NameError repair.
Keep all5seeds201–205,30lag×channel×horizon conditions,original models,shared canonical residuals/population,head150cachebatches/5epochs/lr0.001,validation-only calibration/iso-reliability,windbaseline/rho/q/dt/coveragegrid anduncertainty procedures unchanged. Fresh auxiliary heads only;no partialhead/optimizer resume. Independent seed-wise PBS jobs are execution parallelism;aggregate only exactfive unique seed outputs and fullgrid,never partialfamily. Record deterministic numeric flags beforetorch startup (sameexplicitprofile testedpreviously,not an oldoutput certification),source/environment/input/output/manifests andallactions/calibration/thresholdarrays. No crosshardware exacttraining promise.
Before release require actualPBS CPU deep input/software/realfailed-arrayguard checks,alloriginal model/canonical/cache/input hashesand matching receipts;GPUworkers must bind that actualF0preflight/report/package,verify no existing new output andCUDA allocation. Use separately hashed metis_execution tool,neveredit cloud frozen scripts/windfarm_moe. Registerstill-unexecuted supervision andactivepower asindependent stages using unchangedfrozen programs/CLI/default5seeds/3epochs where applicable under sameinputpreflight. New outputs/receipts only. Originallegacy singleconditionfactorial is not silently substituted for completedregisteredfourconditionV2;its coverage/version disposition remains explicitpendingreview.
Completedchannel/EXP02/EXP03/matchedbudget/rho stages will be deep-audited without rerunning successful calculations or treatingexit0asscience. Every negative/null/failedresult retained;no gate/contract/baseline/seed/population/metric/uncertainty modification to pass.

Phase retry evidence addendum before execution: save each condition's actualvalidation rawhead/gate/physicalfeatures,calibration bins/reserves/iso multipliers/abstention thresholds andalphas;testactions/frozenforecast/gate/physicalfeatures andabstention inputs/RNG accompanyresults. These additions onlyarchive real intermediates. Nonfinitecanonicalshortfall/wind orpolicyvalues on originalvalidcells hardstop before outputs;no filtering a method-specific population. Keep exact originalguard thresholds andcompletefiveseedgrid.

Preflight allocation clarification before execution: use PBS4CPU/64GB plus1GPU,so deep CPU hash/config/identity audits and actual deterministic CUDA/import smoke all run in an allocation. The five phase seed workers and two independent unexecuted families require this real preflight F0,not justsubmission. No login-node training or numericalexperiment.

### E05 — E04 selector stability/frequency diagnostic (2026-10-18)

**Question:** Under the frozen E04 WTB Full arrays and registered joint seed/block resampling rule, how often does the risk-constrained selector produce a feasible policy and a first selected policy?

**Status:** COMPLETED / INCONCLUSIVE / CONDITIONAL ON UNBOUND V4 ARRAYS.

**Protocol:** `alpha=0.05`, `epsilon_C=0 kWh`, `epsilon_V=0`, `v_max=0.10`, candidates `B<C<D<D10`, 5 training seeds x 35 daily blocks, 10,000 joint resamples, stability seed `20261018`. Frequency is diagnostic only and does not modify the E04 primary selector.

**Result:** `NO FEASIBLE` frequency `0.6464`; feasible frequencies `B=0.3523`, `C=0.0042`, `D=0.0001`, `D10=0.0002`; first-selection frequencies `B=0.3523`, `C=0.0013`, `D=0`, `D10=0`. The pre-registered `>=0.80` stability rule is not met by any first-selection frequency.

**Evidence:** `experiments/E05/results/selector_stability.json`, `experiments/E05/results/selector_stability.csv`, and artifact `e05-selector-stability-frequency-20261018 v3`. The receipt-bound run produced the current JSON/CSV SHA-256 values and frequency accounting passed.

**Interpretation ceiling:** This is a conditional diagnostic on the frozen local v4 arrays. The arrays lack an original replay execution receipt, so E05 does not repair E04 provenance or certify a minimum-sufficient policy. E04 remains `NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED` pending receipt/hash binding and independent falsification review.

### E07-HISTORICAL-ONLY-RECALIBRATION — draft only (prepared 2026-10-18)

**Status:** DRAFT / NOT EXECUTED / prospective collection and frozen policy/calibration manifests unbound. This is a proposed preregistration protocol, not an activated or completed registered experiment.

**Question:** Can the predesignated simple policy B_WR, using only historical wind/past60-power-ramp calibration, pass the unchanged cost, relative-violation and absolute-risk gates against original B0 on a new untouched WTB window?

**Design basis:** The complete five-seed slice comparison retains moderate-wind/steady-label/down-ramp localization after adding C, while revealing policy-specific high-block reordering. These are post-hoc observations, not proof that recalibration works. See `analyses/e04_complete_policy_comparison_20261018/REPORT.md` and `v2/`.

**Frozen proposal:** seeds201–205; h6/rho10/dt1/6; q*=0.90/alpha0.05/v_max0.10/epsilon_C0/epsilon_V0. B0/C0/D0/D10_0 remain untouched controls. All four receive pre-test global G or wind×past60-ramp WR offsets; only B_WR is primary. Secondary candidates cannot replace a failed primary on the same new test. Calibration uses the former E04 test solely as history before the new evaluation (anchors30275–35255, latest h6 target35261 plus label-arrival embargo). Proposed confirmation starts at35280 for5040 issue steps, same134-node WTB cohort; current data availability is UNKNOWN. No reuse of legacy test as new confirmation, no test-period updates.

**Method:** historical score s-r_base; Q0.90(method higher), then nonnegative upper95 bootstrap offset(method linear), 2000 common historical block draws/RNG20261022. WR uses original wind10 bins and arrived past60-power ramps (<-150/within±150/>150kW); require1000 cells and14 native blocks per seed, with wind/global fallbacks. No future ramp, true transition, pitch or high-test-block IDs in decisions. Freeze all corrections before new outcomes. Primary retains original E04 U95 gates and additionally shared-day U95, using their larger bound;20000 draws/RNG20261023. No cost-reference substitution or threshold relaxation.

**Evidence/activation boundary:** Full specification is `experiments/E07_history_only_recalibration/PREREGISTRATION_DRAFT.md`, machine draft `protocol.json`. Only protocol preparation occurred; no correction was fitted and no new performance result exists. Bind input/source/collection/numeric manifests before activation, preserve exact archived-action n/violation/cost checks, and retain every null/negative/failed outcome. No distribution-free coverage theorem is claimed for dependent/drifting data.

**2026-10-18 availability audit (no calibration):** The listed local/Metis roots contain the same334304460-byte WTB source (SHA256 `6cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667`),134 nodes and Day1–245. Fifteen local/two Metis WTB caches do not extend the actual time axis. The cache named future holds out the already-used E04 window. No structurally complete new35280–40343 source was found in the audited scopes; there is no positive unseen-window certification or confirmatory binding. Other-site archives are not substituted. Status remains draft/unexecuted; the protocol binds only the negative availability-audit receipt. Formal audit manifest: `analyses/e07_data_availability_audit_20261018/final/availability_manifest.json`. Missing future observations/clock-continuation/access/arrival evidence are explicitly recorded. Numeric gates and all scientific configuration sections remain unchanged. Unsearched storage is UNKNOWN, not proven empty.

### DECISION-INFORMATION-DEV-20261018 — authorized development, separate target

**Status:** AUTHORIZED_DEVELOPMENT / METIS_EXECUTION_STARTED; not confirmation, not E07 activation. User authorized implementation and Metis use after the first-principles adversarial review. Exact current task/configuration is `experiments/decision_information_development_20261018/protocol.json`; execution and failures are in its `execution_log.md`.

**Question/estimand:** Realizable flow comparisons on a new, lawfully earlier common-commitment residual task. Historical WTB Day1–245 remains previously inspected development material. Six information conditions, five seeds201–205; continuous pitch regression probe, simple/base-information and shuffled-label controls, compressed features, direct quantiles, and a privileged current-pitch diagnostic. No new graph/MoE. This does not replace or numerically update the historical canonical target.

**Boundaries:** Source-pitch supervision is explicitly allowed; no pitch-never-recorded claim. Common commitment generated from wind/power at issue−6 for issue+6; inputs use a common event-time window with unavailable slots masked, then historical-only constant fill with missingness indicators. Finite target mask does not filter by pitch/state. New exact archived-action accounting audit; common source/protocol/prepared/target/forecast/mask identity checks precede aggregation. Costs are normalized per valid turbine interval; five frozen instances share temporal block draws. Primary approximate interval family comprises42 costs at the registered three-day span. Other metrics/block spans are descriptive.

**Current execution evidence:** Initial remote preflight244598 failed on all-NaN sklearn1.9 binning; failure retained, no model output. Fixed preparation244599 passed42 remote tests and raw-source hash. Worker244600, action audit244601, remaining29-condition/seed array244602 and aggregate244603 have been submitted with afterok dependencies. Submission is not completion. Practical-effect threshold, independent confirmation and any revised near-optimal-complexity selector remain unbound/unexecuted; original E04 risk cap/zero tolerances/NO FEASIBLE POLICY remain unchanged.

**Completion addendum, 2026-10-18:** All30 runs and aggregation completed; Metis independently reconstructed2880 archived-action block arrays exactly, then export244609 completed. Local verification matched241 exported members and archive SHA256 `13fba6f0f96c3777e511bb177f7566ddc8fd6b37e1946cd946813f15c5234d15`. On the new development pitch-withheld task, B−A cost decreased7.6888%, while C−B decreased0.2071%; the latter improved only3/5seeds and its one-day sensitivity interval crosses zero. C−simple-score and C−shuffled-score multiplicity-adjusted intervals cross zero. B/C observed violations are11.5666%/11.4220%; no minimum-sufficiency/safety certification or E07 activation follows. This is a separate-target development observation, not a replacement for prior canonical evidence. Full result/limitations: `analyses/decision_information_execution_20261018/REPORT.md`.

### RISK-COST-FRONTIER-DEV-20261018 — completed development identification

User authorized first-principles design and continued Metis execution. Before execution, protocol froze historical offset fitting on Day176–192, selection on193–210, already-viewed evaluation on211–245 with h6+release maturity exclusions; rho10/q*=.90/v_max=.10 remain unchanged. Five offset levels [.90,.925,.95,.975,.99] are postprocessing actions, not relaxed caps. Seven existing deployable model families, six conditions and five frozen instances; no retraining. Risk requires every instance, not just their average. Joint approximate shared-block bounds cover instance risks and all mean-cost ratios; epsilon0/0.5/1/2/5% is a sensitivity curve, not changed E04 tolerances.

Sources/protocol: `experiments/risk_cost_frontier_development_20261018/`. Jobs244616–244620 completed preparation/historical/selection/evaluation/aggregate,244621 exported. 1260 stored-action array accounting checks passed on Metis. Main compact archive SHA256 `61b34640f4b3b360a7c548aacf31811755c871d5c53235e69544f8eb50cca8bf`,359 members verified locally. Main historical recipe identifies no candidate for pitch_withheld/fresh at epsilon<=5%; this failure remains.

### RISK-FRONTIER-MODEL-CLASS-AUDIT-20261018 — result-informed secondary diagnostic

Designed after inspecting the primary recipe and fixed-grid point summaries; not claimed preregistered for the same test. Separate protocol `experiments/risk_frontier_model_class_audit_20261018/protocol.json` retains all35 existing model/offset policies, caps and resources. Same q across all five instances; all8400 risk/ratio coordinates jointly assessed. No historical-choice gate in this retrospective capability task, no ex-ante or deployment claim. Job244622 completed; secondary archive SHA256 `6f7734fe3d4c856c055e5e94cc30a597f1def9f658328cc4760b6f085aacfd37`,11 members verified.

At epsilon2%, pitch_withheld/fresh/10–30min conditions identify B family across1/3/7-day blocks; the60min stress endpoint identifies B@.95 at epsilon5%. In pitch_withheld primary3-day analysis B@.925 has max-instance approximate risk UCB8.3208% and relative regret upper bound0.517817%. These are model-set and approximation bounded development observations; they cannot override primary recipe failure, certify independent confirmation, prove every B channel necessary or refute graph models. Full report: `analyses/risk_cost_frontier_execution_20261018/REPORT.md`. E04/E07 and old raw results remain unchanged.


### INFORMATION-SUBSET-DEV-20261019 — running frozen development extension

User authorized smaller information subsets, a second estimator, sample-size curves and independent source acquisition; no evaluation-based iterative tuning. Protocol: `experiments/information_subset_development_20261019/protocol.json`. Primary pitch-withheld grid is Common plus every nonempty W/P/Q subset crossed with1/6/36 last-arrived observations. Five other information conditions use six fixed subsets. Preset HGB and direct pinball MLP, seeds201–205, nested shared budget prefixes10k/40k/120k/360k (pressure120k/360k);1480 learned fits and30 persistence runs across550 workers. Common forecast already depends on wind/power: minimality is conditional reserve-layer minimality only. Fixed epochs scale compute with data. No new graphs/state architecture.

Sources18c9efc3; Metis16 preflight tests passed. NFS Errno122 write quota failure preserved; same numerical source/config rerun on verified writable Lustre. Both historical real-data checks completed, including360k MLP. Array244681 is running;244682 historical choice,244683 evaluation,244685 exact arithmetic audit,244684 joint envelope,244686 complete curves/compact export are success-dependent. Submission is not completion. No new risk/cost or minimum-model result is yet claimed. E04/E07/raw assets unchanged. Full failures/status: experiment execution_log.md.

### HILL-OF-TOWIE-CONFIRMATION-SOURCE-20261019 — source bound, download/qualification pending

Official Zenodo22662930/v2.1.0 source metadata and 9 published metadata MD5 verified. Before measurement acquisition, source binding SHA256 `4df5eca98530dc2777c92b83213fb0342829d7f926694615363b57cd5c2ddd76` froze2023 training,2024 calibration,2025 sealed confirmation, official annual archive sizes/MD5 and intervention retention. Opaque downloads are running on Lustre; partial NFS acquisition remains preserved. Actual2023/24 schema, UTC period-end clocks,21-node coordinates and missingness require allocated-node audit.2025 remains unparsed; no independent confirmation outcome or complete cohort qualification is claimed. A new farm cannot activate/replace original WTB E07. Full source/time/holdout boundaries: `experiments/independent_confirmation_20261019/decision_protocol.json` and `source_binding.json`.


**2026-10-19 extension status addendum:**96 local software tests and both existing consistency gates pass; no scientific certification follows. Scheduler concurrency changed12→16 (32CPU), no numerical/configuration tuning. Last successful read found321/550 historical manifests. Pre-evaluation necessity sidecar244688 uses existing all-pair lower bounds to exclude every strictly smaller policy; unresolved alternatives mean MINIMUM_UNRESOLVED. Original sufficient-set results/selector stay unchanged, finite condition/budget family only.

**Independent acquisition completion and QC:**All three official annual archives2023/2024/2025 (4665903339B) acquired and publisher MD5/size verified;2025.zip unlisted/unparsed. Strict raw-row uniqueness244687 failed and remains failed. Read-only244689 found230/231 cross-month duplicate groups per table/year with all consumed fields numerically equal and zero conflicts. New2885aac1 adapter244690 only on2023/24 requires unanimous consumed values across batches/months/years; any conflict rejects entire run. This is a physical-coordinate representation check, not deletion of unfavorable observations or change of prior failure. Final source-coordinate qualification still awaits receipt readback; no independent model confirmation or E07 activation. Client DNS/connectivity currently limits new state reads; PBS chains are already submitted.
