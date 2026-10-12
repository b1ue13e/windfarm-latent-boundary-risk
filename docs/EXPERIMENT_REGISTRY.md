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

**Question:** Does posterior conditioning reduce reserve-screening PSREI relative to the strongest matched-information wind-speed-conditioned quantile policy?

**Contract claim tested:** Q2 Incremental decision value.

**Status:** COMPLETED / NEGATIVE FOR PLANT-WIDE COST SUPERIORITY.

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

**Observed result:**

| Slice | Delta PSREI C-B | Interpretation |
|---|---:|---|
| Full | +523,044 kWh | Posterior is more costly |
| Transition | +112,704 kWh | Posterior is more costly |
| Steady | +410,340 kWh | Posterior is more costly |

In transition windows, posterior violation is 7.24% vs 8.36% and shortage is 86,592 vs 90,231 kWh, while reserve procurement rises to 3,567,090 vs 3,417,998 kWh.

**Positive outcome interpretation:** A negative delta with appropriate uncertainty would support cost superiority.

**Null/negative outcome interpretation:** Preserve the negative result; only risk-shape changes may be claimed.

**Failure/invalidity conditions:** Baseline uses weaker information, target differs, point forecast differs, or result is reported only against global quantile.

**Artifacts:** `artifacts/strong_baseline_closure_summary.csv`.

**Decision after result:** Plant-wide decision superiority is not supported. Transition result is risk hedging, not cost optimality.

---

### EXP-Q2-002 — Transition-vs-steady heterogeneity

**Question:** Is the posterior-vs-wind-speed-bin gap different in transition windows than in steady operation?

**Contract claim tested:** Transition-localized risk-hedging interpretation.

**Status:** COMPLETED.

**Primary estimand:** `Delta_transition - Delta_steady`, where Delta is posterior minus wind-speed-bin PSREI.

**Primary metric:** PSREI interaction contrast.

**Uncertainty procedure:** Predefined bootstrap contrast.

**Observed result:** Mean interaction approximately -296,123 kWh; current bootstrap CI excludes zero and reported p = 0.002 in the frozen contrast artifact.

**Positive outcome interpretation:** The decision trade-off is heterogeneous across operating regimes.

**Null/negative outcome interpretation:** Do not claim transition localization.

**Decision after result:** Heterogeneity is supported; this does not imply transition cost superiority.

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

**Decision after result:** This is a conditional decision map, not a model ranking.

---

## 3. Open decisive experiments

### EXP-02 (EXP-Q1-003) — Zero-Privileged-Pitch Supervision Boundary Protocol (零特权历史监督下的代理标签边界识别与备用闭环)

**Question:** If blade pitch is never recorded or available in historical training data, can consequence signals alone recover boundary-relevant representations, and does this zero-privileged representation provide incremental decision value for downstream reserve screening beyond a strong local conditional baseline?

**Contract claim tested:** Current UNKNOWN: pitch-never-recorded setting and zero-privileged supervision boundary.

**Status:** CONCLUDED / EVIDENCE FROZEN (DEFICIT ESTABLISHED; FALSIFICATION GUARDRAIL OBSERVED).

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
  > **"Under the zero-privileged supervision protocol, consequence signals alone failed to recover a deployable decision function superior to simple local wind-speed conditioning."**
  *(Strict boundary: It is NOT claimed that active power consequence carries no mutual information, nor that real wind farms do not need pitch telemetry. The deficit is strictly established for the unprivileged learning protocol).*

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

**Status:** COMPLETED / EVIDENCE FROZEN (corrected v2; original v1 superseded).

**Information set:** 严格限制于到达时刻各场站本地观测到的 SCADA 特征（本地风速、功率、气温），pitch 在测试期完全扣留。

**Training-only privileged information:** Historical pitch/regime labels allowed at training time for representations requiring alignment; zero pitch observable at test/deployment time.

**Frozen point forecast:** Frozen site-specific canonical point forecasts matching evaluation protocol.

**Frozen target:** Frozen shortfall residual target $s_t = \max(\hat{y}_t - y_t, 0)$.

**Primary baseline:** Site-Local Wspd-Bins (各场站本地校准的 10-bin 风速条件分位数).

**Secondary baselines:** No-Graph Architectural Control (无图架构对照模型：单机输入相同本地 SCADA 特征、完全断开风机间空间图连接的单机 MLP，4,865 参数，见 `docs/NO_GRAPH_CONTROL_AUDIT.md`；非严格容量等价，属于拓扑消融对照).

**Tested challengers:** 跨场站迁移的 STGQ-Modular (110,012 参数) 及本地微调的 STGQ-Modular.

**Endpoint Hierarchy & Multiple Comparisons Protocol:**
- **Primary Endpoint:** 每场站 $h=6$ 处的配对差分 $\Delta\text{PSREI}(h=6) = C_{\text{transferred}} - C_{\text{local\_wspd}}$，按场站分别计算。
- **Secondary / Exploratory Endpoints:** 短视界 $h=1$ 处的配对差分 $\Delta\text{PSREI}(h=1)$；Fine-tuned STGQ 及 No-Graph 对照模型表现；违约率差分 $\Delta V$ 及采购/缺额分量指标。
- **Multiple Comparisons Guardrail:** 明确本实验未进行跨场站、跨视界、跨模型的族全局显著性（FWER）合并声明。所有次要终点仅用于辅助机制剖析与稳健性佐证，严格避免数据窥探与假阳性推断。

**Primary metric:** $\Delta\text{PSREI}(h=6)$ (kWh).

**Secondary metrics:** 违约率差分 $\Delta V$ (%), 绝对 PSREI (kWh), 绝对违约率 $V$ (%), 备用采购量 (kWh), 缺额暴露量 (kWh).

**Population slices:** Penmanshiel (14 turbines) 与 Kelmarsh (6 turbines) 全测试集，分别评估，严禁合并样本。

**Unit of replication:** 5 随机种子 (201–205).

**Compute budget:** 约 2.5 GPU·h (NVIDIA A100-PCIE-40GB / RTX 4090 或等效环境).

**Uncertainty procedure:** 场站级日聚类 Block Bootstrap ($B=2000$).

**Observed results (corrected v2; independent site-frozen point forecasts):**
- **Penmanshiel (14 turbines)**:
  - $h=6$ (**Primary Endpoint**): Site-Local Wspd-Bins 13,742,849 kWh (16.59% viol); Transferred STGQ-Modular $\Delta\text{PSREI} = +5,321,915$ kWh ($p = 0.003$, significant cost penalty); Fine-tuned $\Delta\text{PSREI} = -3,527,228$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +16,880,326$ kWh ($p < 0.001$).
  - $h=1$ (*Secondary Endpoint*): Site-Local Wspd-Bins 13,330,750 kWh (14.61% viol); Transferred $\Delta\text{PSREI} = +6,571,777$ kWh ($p < 0.001$); Fine-tuned $\Delta\text{PSREI} = -2,642,687$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +19,591,859$ kWh ($p < 0.001$).
- **Kelmarsh (6 turbines)**:
  - $h=6$ (**Primary Endpoint**): Site-Local Wspd-Bins 3,131,041 kWh (11.80% viol); Transferred STGQ-Modular $\Delta\text{PSREI} = +435,684$ kWh ($p = 0.196$, no significant improvement); Fine-tuned $\Delta\text{PSREI} = -2,001$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +3,403,611$ kWh ($p < 0.001$).
  - $h=1$ (*Secondary Endpoint*): Site-Local Wspd-Bins 3,107,821 kWh (11.07% viol); Transferred $\Delta\text{PSREI} = +515,318$ kWh ($p = 0.181$); Fine-tuned $\Delta\text{PSREI} = +174,455$ kWh (exploratory); No-Graph Architectural Control $\Delta\text{PSREI} = +3,667,533$ kWh ($p < 0.001$).

**Positive outcome interpretation:** 若迁移表示在 Penmanshiel 上战胜本地 Wspd-Bins 且战胜 No-Graph 控制模型，则确立了复杂地形下空间尾流图迁移的因果决策价值。

**Null/negative outcome interpretation:** 若本地 Wspd-Bins 同样在外部场站战胜迁移表示，则将“状态可恢复不等于决策优越”及“简单基线充分性”推广为跨场站普遍规律。

**Scientific verdict (corrected v2):** 结果具有场站异质性。Penmanshiel 的 Transferred STGQ 在主终点显著劣于 Site-Local Wspd-Bins；Kelmarsh 的差异为正但未达显著。因而不能继续使用原 v1 的“两个场站均无显著差异”结论，也不能将结果升级为普遍因果规律。

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
- `docs/NO_GRAPH_CONTROL_AUDIT.md` (架构参数与命名规范裁决文档)

**Decision after result:** Record empirical benchmark in scientific ledger; update external site claims and decision boundary table without altering frozen baseline definitions.

---

### EXP-Q2-003 — External-site matched direct-quantile closure

**Question:** On each external wind farm separately, does latent-state conditioning add value beyond a matched direct conditional quantile under the same information set?

**Contract claim tested:** External validity.

**Status:** PROPOSED / BLOCKED UNTIL MATCHED PROTOCOL IS FIXED.

**Primary baseline:** Site-local matched direct quantile using the same deployment-time features.

**Primary challenger:** Site-local or transferred latent-state posterior policy.

**Population:** Each site separately; no pooled headline estimand unless separately pre-registered.

**Primary metric:** Site-specific PSREI difference.

**Secondary metrics:** Violation, shortage, reserve procurement, calibration.

**Negative outcome interpretation:** Site remains a boundary probe; do not claim generalization.

**Decision after result:** Report positive, neutral, and negative sites separately.

---

### EXP-03 — Integer-step asynchronous packet arrival envelope

**Question:** Under an explicit out-of-order telemetry protocol, how does causal packet arrival and missingness alter PSREI relative to delay, and does the challenger remain comparable to Site-Local Wspd-Bins under the same arrival trace and missing mask?

**Contract claim tested:** Q2 Incremental decision value under asynchronous arrival; current UNKNOWN until execution.

**Status:** REGISTERED / BLOCKED UNTIL PROTOCOL TESTS AND INPUT HASH ARE FROZEN.

**Information set:** Integer dispatch steps. Each packet stores `(event_time, arrival_time, channel_id, sequence_id)`. At step `t`, every model reads only packets with `arrival_time <= t`; packets are ordered by `(arrival_time, sequence_id, channel_id)` for simultaneous arrivals.

**Training-only privileged information:** None for the asynchronous arrival mechanism. Hidden pitch remains withheld wherever the matched deployment protocol requires it; no future target, future packet, or post-hoc arrival correction may enter inputs.

**Frozen point forecast:** The canonical frozen point forecast from `docs/FIXED_TARGET_CONTRACT.md`.

**Frozen target:** The canonical shortfall residual target `s_t = max(yhat_fixed - y, 0)`.

**Primary baseline:** Site-Local Wspd-Bins evaluated using the identical packet trace and identical missingness mask.

**Secondary baselines:** Challenger model under the same trace/mask; synchronous-arrival control; optional no-packet-delay control only as a diagnostic reference.

**Primary estimand:** The paired PSREI-vs-delay curve `Delta_PSREI(tau) = PSREI_challenger(tau) - PSREI_local_wspd(tau)` over the pre-registered delay grid, with `tau*` defined as the smallest delay at which the curve's uncertainty interval excludes the zero-gain region under the declared criterion. `tau*` is not defined by a violation-rate threshold alone.

**Primary metric:** PSREI-vs-delay curve and critical point `tau*`, reported separately by farm and horizon; no pooled headline estimand unless registered separately.

**Secondary metrics:** Violation-rate-vs-delay, reserve procurement, shortage exposure, packet late/drop fractions, missingness by channel, and sensitivity of operating targets at 5%, 10%, and 15% violation. The 10% target is pre-registered as an operating target because `q*=0.90`, not as the unique breakdown threshold.

**Population slices:** Each external farm separately; full test population plus any pre-declared steady/transition diagnostic slices. Synthetic results are labeled **synthetic asynchronous envelope** and cannot be interpreted as industrial arrival-rate prevalence.

**Unit of replication:** Independent simulator seeds and model seeds, reported separately; temporal dependence handled with the registered day/block procedure for the underlying data.

**Uncertainty procedure:** Frozen seed list and paired day-cluster bootstrap applied within each delay point; all methods share each realized trace and missing mask. No post-hoc threshold or favorable slice selection.

**Positive outcome interpretation:** A challenger curve that is lower than the local baseline across a pre-declared delay region, with uncertainty excluding zero at the registered points, supports incremental decision value only for that farm/protocol.

**Null/negative outcome interpretation:** A flat or worse curve supports the simpler local baseline and leaves asynchronous decision superiority unestablished; it does not imply that industrial telemetry has the simulated arrival distribution.

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
- no renaming a failed hypothesis into a “new contribution” without a new registered question.
