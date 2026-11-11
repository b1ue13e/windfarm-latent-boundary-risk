# Information-Set Contract & Telemetry Degradation Audit (Phase 2)

**Date**: 2026-09-18  
**Status**: VERIFIED & FROZEN  
**Manifest Path**: `artifacts/information_set_manifest.csv` (819 entries across 9 scenarios and 7 model families)

---

## 1. Mathematical Definition of the Deployable Information Set

For any dispatch issue time $t$ and operational degradation condition $d$, the **deployable information set** $\mathcal{I}_t^{(d)}$ is defined strictly as the set of all sensor measurements, actuator readings, dynamic graph topologies, and metadata that have genuinely arrived at the dispatch terminal at or before time $t$:

$$\mathcal{I}_t^{(d)} = \left\{ \mathbf{x}_{i, s}^{(d)}, \mathbf{m}_{i, s}^{(d)}, \mathbf{a}_{i, t}^{(d)}, \mathcal{A}_{s}^{(d)} \;\middle|\; i \in \{1,\dots,N\}, \; s \in \{t - H + 1, \dots, t\} \right\},$$

subject to the causal arrival mapping $\mathcal{T}_d(\cdot)$.

Under NO circumstances may any neural architecture, baseline, or physical heuristic access:
1. Contemporary readings $\mathbf{x}_{i, t}$ when condition $d$ specifies a transmission lag $\tau > 0$;
2. Unlagged historical tails $\mathbf{x}_{i, t - \tau + 1 : t}$ (which would constitute information leakage across time);
3. Unlagged wind direction $\theta_t$ for constructing dynamic wake adjacency graphs $\mathcal{A}_t$;
4. Blade pitch angle registers $\bar{p}_{i, t}$ when condition $d$ specifies pitch withholding;
5. Ground-truth regime labels $Z_{i, t}$ during online dispatch or test evaluation;
6. Future test-set realization targets $y_{i, t+1 : t+P}$ or test-set residual quantiles.

---

## 2. Specification across Degradation Regimes

### Regime A: Clean / Full Observability
- **Available Channels**: All 11 SCADA features ($\texttt{Wspd}, \texttt{Wdir}, \texttt{Etmp}, \texttt{Itmp}, \texttt{Ndir}, \texttt{Prtv}, \texttt{Patv}, \texttt{Pab\_mean}, \texttt{Pab\_std}, \dots$), dynamic wake graph $\mathcal{A}_t$, anchor tuple $\mathbf{a}_{i,t} = [\texttt{Wspd}_{i,t}, \texttt{Pab\_mean}_{i,t}, s^{\mathrm{wake}}_{i,t}, \texttt{Patv}_{i,t}]$.
- **Latency**: $\tau = 0$ (fresh arrival on 10-min SCADA polling grid).
- **History**: Full unlagged history $H=36$ ($t-35$ to $t$).
- **Calibration**: Nominal validation split ($\tau=0$).

### Regime B: Delayed / Full Channel Observability (Delay-$\tau$, $\tau \in \{10, 20, 30, 60\}\text{ min}$)
- **Available Channels**: All 11 SCADA channels, but all arrivals delayed by $\tau = d \times 10\text{ min}$ ($d \in \{1, 2, 3, 6\}$ steps).
- **Latency Transformation**:
  - Anchor telemetry: $\mathbf{a}_{i,t} \leftarrow \mathbf{a}_{i, t - d}$.
  - Historical sequence: Steps from $t - d + 1$ to $t$ have not arrived. Under the canonical `stalled` policy (sample-and-hold), $\mathbf{x}_{i, s} \leftarrow \mathbf{x}_{i, t - d}$ for all $s \in [t - d + 1, t]$.
  - Dynamic graph topology: $\mathcal{A}_s \leftarrow \mathcal{A}_{t - d}$ for all unarrived steps $s \in [t - d + 1, t]$.
  - Physical rule input: Strictly extracted from the lagged anchor: $w \leftarrow \texttt{Wspd}_{i, t - d}, \beta \leftarrow \texttt{Pab\_mean}_{i, t - d}$.

### Regime C: Pitch-Withheld ($\tau=0$, $\bar{p}$ Unobservable)
- **Available Channels**: 9 consequence and meteorological channels.
- **Unavailable Channels**: Collective pitch angle $\texttt{Pab\_mean}$ and pitch standard deviation $\texttt{Pab\_std}$ are strictly masked and set to $0.0$ across all historical and anchor inputs:
  $$\mathbf{x}_{i, s, \texttt{Pab}} = 0.0, \quad \mathbf{m}_{i, s, \texttt{Pab}} = 0.0, \quad \mathbf{a}_{i, t, \texttt{Pab}} = 0.0.$$
- **Latency**: $\tau = 0$ for remaining channels.
- **Physical Rule / Recalibration Input**: Pitch register unavailable; physical power curve evaluates fine pitch assumption ($\beta = 0^\circ$) or marginalizes over nominal pitch bins.

### Regime D: Delay + Pitch-Withheld (Delay-6 + $\bar{p}$ Unobservable)
- **Combination**: Both 60-minute latency stall ($d=6$) AND complete pitch withholding ($\bar{p} \equiv 0.0$).
- **Operational Reality**: Represents a catastrophic aggregator-firewall disconnection where telemetry is both stale and stripped of proprietary blade control registers.

### Regime E: Sensor Perturbation & Markov Burst Dropout
- **Sensor Noise**: Additive Gaussian perturbations $\mathcal{N}(0, \sigma_v^2)$ and $\mathcal{N}(0, \sigma_\beta^2)$ with $\sigma_v = 1.0\text{ m/s}, \sigma_\beta = 2.0^\circ$ scaled to normalized feature space via training-set variance.
- **Markov-Gilbert Dropout**: Two-state Markov chain ($p_{GB} = 0.08, p_{BB} = 0.75$) generating dynamic packet drop bursts with variable lags $d \in [0, 6]$ applied synchronously across history and anchor.

---

## 3. Seven Critical Audit Questions: Resolution & Evidence

| Audit Check | Potential Flaw / Risk | Codebase Status & Evidence | Verdict |
| :--- | :--- | :--- | :---: |
| **Q1: Contemporary `Patv` Leakage** | Did neural models see $\texttt{Patv}_t$ while physical rules saw $t-\tau$? | In legacy `fair_degradation_replay.py`, `anchor_physics[:, :, 3]` was unshifted. In `windfarm_moe/arrival_feed.py:L101-L113`, `target_corrupted = ("all",)` shifts all 4 physical channels and all feature channels synchronously. Both rules and models read identical lagged inputs. | **CLEAN / RESOLVED** |
| **Q2: Fresh Wind Direction in Graph** | Was instantaneous $\theta_t$ used to construct dynamic graph $\mathcal{A}_t$ under delay? | `windfarm_moe/arrival_feed.py:L236-L256` explicitly applies sample-and-hold stalling to `edge_index_hist` and `edge_weight_hist` for all steps $s \in [H - \tau, H - 1]$. | **CLEAN / RESOLVED** |
| **Q3: Graph Topology Asymmetry** | Did graph inputs contain information unavailable to physical baselines? | Physical rules evaluate on single-turbine or farm-aggregate inputs; graph models observe spatial array topology. In both cases, inputs reflect strictly $t-\tau$ telemetry. | **CLEAN / RESOLVED** |
| **Q4: Look-Ahead in Imputation** | Did forward-fill or mean imputation consume future observations? | `windfarm_moe/utils.py:L73-L84` uses `forward_fill_2d` with `np.maximum.accumulate` over preceding rows only. `fill_with_train_mean` uses `train_stop` index, strictly preventing future leakage. | **CLEAN / RESOLVED** |
| **Q5: Scaler Normalization Leakage** | Were standardization parameters fitted on validation or test sets? | `windfarm_moe/utils.py:L98-L103` computes `train_mean` and `train_std` strictly on `values[:train_stop]`. All transformations are frozen before validation/test. | **CLEAN / RESOLVED** |
| **Q6: Pitch Label Leakage** | Was true blade pitch used in test-time inference under pitch-withheld settings? | Ground-truth labels $Z_{i,t}$ are computed offline. In `UnifiedArrivalDataset`, withheld channels are zeroed and masked out completely in `x_hist`, `feature_mask_hist`, and `anchor_physics`. No test model accesses pitch registers. | **CLEAN / RESOLVED** |
| **Q7: Inter-Method Information Parity** | Were competing models tested on different input distributions? | All models in `scripts/decisive_fair_risk_benchmark.py` and `scripts/eval_single_task_dense_phase_scan.py` ingest the identical batch yielded by `UnifiedArrivalDataset`. Rule inputs are extracted from the batch via `extract_symmetric_rule_input`. | **CLEAN / RESOLVED** |

---

## 4. Contract Enforcement

Every subsequent experiment in this project (Phases 3 through 15) must ingest data strictly through `windfarm_moe/arrival_feed.py:UnifiedArrivalDataset`. Any bypass of this ingress layer immediately violates the Information-Set Contract and invalidates the resulting claims.
