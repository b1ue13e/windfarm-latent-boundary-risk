# Claim disposition during raw replay — 2026-10-15

Status: IN PROGRESS / NOT SCIENTIFICALLY CERTIFIED. This register does not replace the
scientific contract or delete historical evidence. Negative/null findings are preserved.

| Claim or result | Current disposition | Direct reason / replacement evidence |
|---|---|---|
| Complex model is required to identify the evaluated hidden discrete state | WITHDRAWN | Wind-only rule separates all 639,378 valid test labels; exclusion mask is part of this finding. FALSIFICATION_REPORT section11 |
| Channel h6 decision values | WITHDRAWN from valid h6 evidence | Historical code selected residual index1 instead of5; corrected runner and test_replay_integrity |
| Channel gain vs fixed direct-cost constants | WITHDRAWN as matched-baseline evidence | Constants did not recompute a matched comparator; new version computes same-target wind bins |
| 62.9% valid-transition recall | WITHDRAWN under that interpretation | Invalid adjacent labels contributed false boundary events; corrected and legacy denominators must both be archived |
| EXP02 correctly specified physical proxy conclusion | WITHDRAWN pending corrected run | Wrong power scaler; epsilon50 proxy labels differ on189 validation/24 test cells. Thresholds unchanged |
| EXP03 causal arrival curve and complete packet provenance | WITHDRAWN pending corrected run | Unarrived initial value and incomplete full-grid records; new simulator archives event/arrival/select/masks |
| Four of five seeds worse at every reserve budget | CORRECTED | Four seed averages are worse; only three are worse at every evaluated budget |
| External v2/v4 are valid current matched benchmarks | WITHDRAWN / INVALID v4 | v4 uses predictions and targets from different physical windows; v2 is not reinstated. New raw-window replay pending |
| NoGraph establishes graph causality; MoE is necessary | NOT ESTABLISHED | Capacity/training confounding and intervals crossing zero preserved |
| Global FULLY_REPRODUCIBLE certificate | WITHDRAWN | Cached artifact checks do not execute raw-data training; renamed verifier output without changing checks |
| Existing WTB full-cost posterior penalty | HISTORICAL ARTIFACT EVIDENCE; raw replay pending | Original CSV unmodified; new forecast/training/evaluation must complete before independent reproduction claims |
| External v4 values and confidence intervals | INVALID; retained as erroneous calculation records | Wrong-window targets are not a valid negative or positive transfer result. See EXP01_INVALIDATION_20261015.md |

Running evidence is under artifacts/raw_replay_20261015_v2. Every original manifest
entry remains in coverage.json with a separate execution status. Withdrawn is not
EXECUTED, REPRODUCED or PASSED. The current gate may fail because legitimate withdrawal
changes old text assertions; its thresholds must not be relaxed to obtain PASS.

The main manuscript, supplementary correction notice and cover-letter hold have been
updated. PDF compilation is a format check only. No submission or remote publication
is authorized by completion of these local edits.

Old dense/MoE phase-scan costs are not common-target decision evidence; old cross-delay curves do not hold boundary populations fixed. These interpretations are withdrawn. Same-condition physical recalibration comparisons retain their explicitly local scope. Corrected RAW-PHASE-FROZEN-V1 is registered before execution.
# External raw-transfer exactness gate failure —2026-10-15

PBS external audit242736 exited1: the saved WTB-source Kelmarsh201 validation
gate array was not exactly equal to the fresh forward using verified weights and
cache. The failing replay array, full stdout and source/input provenance are
retained. Any assertion that this external raw-transfer branch has passed exact
independent replay is withdrawn. Its numerical decision conclusions remain
UNCERTIFIED; no older invalid EXP01 result is reinstated. This does not negate the
already verified saved-artifact arithmetic of the separate four-condition family,
which was explicitly not a fresh backbone-inference certification.

The cause is UNKNOWN pending the registered repeated-forward diagnosis. Do not
describe this as rounding noise, a particular CUDA kernel defect, harmlessness,
scientific-direction agreement or acceptable tolerance without direct evidence.
The exact gate remains unchanged; any execution repair must be registered and
run as a new version while preserving this failed attempt.


## 新版本限定核对（不覆盖旧失败）—2026-10-15

注册诊断242739显示该固定输入的默认重复推理不精确相等，而显式确定性配置重复相等；具体核函数及原进程后台配置仍UNKNOWN。新deterministic_matched_transfer_v1经242741生产、242742全20行/4统计精确审计和242745来源/样本数/风速基线比较，实际均F/exit0。旧242736仍FAILED/UNCERTIFIED，旧精确复现结论不恢复。

新h=6结果：Kelmarsh Δ=+6322.69757537842kWh，95%区间[-31417.261400960288,46732.590610427855]；Penmanshiel Δ=+356014.397852834kWh，区间[162798.52059760567,566245.7208653128]。Δ=后验成本减风速基线；前者未建立成本改善，后者当前协议下成本惩罚。限定既有完整权重、当地固定预测、当地验证校准和当前窗口，不认证完整零样本或全论文。来源和全部h=1/h=6值见[限定证据报告](EXTERNAL_DETERMINISTIC_EVIDENCE_20261015.md)。
