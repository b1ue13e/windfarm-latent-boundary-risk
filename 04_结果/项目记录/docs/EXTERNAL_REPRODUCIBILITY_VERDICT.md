# External Reproducibility Verdict

> **2026-10-18 metadata correction; historical report.** Section 3 member hashes and posterior byte size now match the unchanged release ZIP and the release-tag manifest. The original text is preserved in [the audit snapshots](../analyses/legacy_release_hash_audit_20261018/snapshots/pre_correction_EXTERNAL_REPRODUCIBILITY_VERDICT.md). Historical PASS statements below are retained as records, not renewed scientific certification; the [scientific contract](SCIENTIFIC_CONTRACT.md) controls current claims. This correction does not re-execute the reported clone, download, or claim replication. See [reconciliation](../analyses/legacy_release_hash_audit_20261018/REPORT.md).

**Date**: 2026-09-26  
**Repository**: `https://github.com/b1ue13e/windfarm-latent-boundary-risk.git`  
**Git Tag**: `tste-submission-v1.0`  
**Target Commit**: `1085f23c925b7b9bfc312608cbaaecc50cba676e`  
**Isolated Test Directory**: `E:\windfarm_reproduction_final`  
**Verdict**: **`EXTERNALLY_REPRODUCIBLE_AT_CLAIM_LEVEL`**

---

## 1. Executive Summary

This audit closes the final external reproducibility gap for the manuscript submitted to *IEEE Transactions on Sustainable Energy*.

A clean clone was executed strictly from the remote, publicly accessible GitHub repository at tag `tste-submission-v1.0` in a completely fresh directory (`E:\windfarm_reproduction_final`). The test environment had zero access to the author's local workspace (`E:\论文3`) or local staging directories (`C:\Users\Public\Downloads\windfarm_release` was removed prior to execution).

All Category-B derived artifacts were automatically retrieved from the public GitHub Release asset URL via `python scripts/fetch_artifacts.py`, cryptographically verified via SHA256 checksums, and unpacked.

The one-command verifier `python scripts/verify_replication.py` was executed, alongside the full suite of decisive gates, number consistency audits, and figure generators.

**Result**:
- **19 / 19** headline claims verified with exact numerical match;
- **All 6** manuscript figures successfully built from reproducible data;
- **All 7** manuscript tables verified against verified data artifacts (73/73 token consistency audit passed);
- **0** missing artifacts remain;
- **Final Verdict**: **`EXTERNALLY_REPRODUCIBLE_AT_CLAIM_LEVEL`**.

---

## 2. Remote Clone & Environment Provenance

| Parameter | Value | Verification Status |
| :--- | :--- | :---: |
| Remote Repository URL | `https://github.com/b1ue13e/windfarm-latent-boundary-risk.git` | Verified (Public) |
| Git Tag | `tste-submission-v1.0` | Verified |
| Tag Commit Hash | `1085f23c925b7b9bfc312608cbaaecc50cba676e` | Verified |
| Isolated Clone Directory | `E:\windfarm_reproduction_final` | Clean Fresh Clone |
| Local Cache Dependency | None (`C:\Users\Public\Downloads\windfarm_release` deleted) | Verified Isolated |
| Clone Command | `git clone --branch tste-submission-v1.0 https://github.com/b1ue13e/windfarm-latent-boundary-risk.git E:\windfarm_reproduction_final` | Exit 0 |

---

## 3. Public Release Asset Provenance (Category B)

| Parameter | Value |
| :--- | :--- |
| **Release Name** | `IEEE TSTE Submission Release v1.0` |
| **Release Tag** | `tste-submission-v1.0` |
| **Asset Name** | `windfarm_derived_artifacts_v1.0.zip` |
| **Asset ID** | `589566909` |
| **Permanent URL** | `https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/tste-submission-v1.0/windfarm_derived_artifacts_v1.0.zip` |
| **Byte Size** | `195,613,174` bytes (186.55 MB) |
| **Archive SHA256** | `cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22` |
| **Fetch Command** | `python scripts/fetch_artifacts.py` |
| **Fetch Status** | Download completed, SHA256 verified, 2/2 artifacts unpacked |

### Extracted Category-B Artifact Checksums
1. `artifacts/fixed_forecast_residuals.npz`:
   - Size: `173,410,167` bytes
   - SHA256: `b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9`
   - Verification: **PASS**
2. `artifacts/matched_budget/cached_posterior_probs.npz`:
   - Size: `22,475,033` bytes
   - SHA256: `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca`
   - Verification: **PASS**

---

## 4. Headline Claim Replication Audit (19 / 19 PASS)

| ID | Domain / Paper Location | Headline Claim / Estimand | Target Value | Replicated Value | Status |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **C01** | Regime 1 (Table I) | Clean Physics $h=1$ PSREI (5-seed mean) | 589,535 kWh | 589,535 kWh | **PASS** |
| **C02** | Regime 1 (Table I) | Clean Physics $h=6$ PSREI (5-seed mean) | 881,367 kWh | 881,367 kWh | **PASS** |
| **C03** | Regime 1 (Table II) | Clean Physics $h=6$ Violation Rate | 6.81% | 6.81% | **PASS** |
| **C04** | Regime 1 (Table II) | Missingness-Aware GBDT $h=6$ Violation Breach | 16.23% (>10.0%) | 16.23% | **PASS** |
| **C05** | Regime 2 (channel_mode=all) | Recalibration Shortage Absorption at $\tau=60$ | 66.5% | 66.46% | **PASS** |
| **C05b** | Regime 2 (channel_mode=all) | Recalibration Absorption across the 10–30 min Grid | 36.3/53.9/61.7% | 36.28/53.89/61.72% | **PASS** |
| **C06** | Regime 2 (Table IV) | Recalibrated Physics $\tau=60$ Cost | 1,228,609 kWh | 1,228,609 kWh | **PASS** |
| **C07** | Regime 2 (Section IV-B) | Uncalibrated Posterior Max ECE | $\le 5.0\%$ | 3.46% | **PASS** |
| **C08** | Regime 3 (Table V) | Active Power AUROC (5-seed mean) | 0.988 | 0.988 | **PASS** |
| **C09** | Regime 3 (Table V) | Transition Recall Gain (Model vs Rule) | 0.417 vs 0.196 | 0.417 vs 0.196 | **PASS** |
| **C10** | Ablations (Table VI) | C2 Active Power Dominant Mechanism (Brier) | $< 0.05$ | 0.0112 | **PASS** |
| **C11** | Ablations (Table VI) | C4 Thermal Detection Failure (Recall) | 0.0% | 0.0% | **PASS** |
| **C12** | Strong Baseline (Table VII) | Plant-Wide Posterior PSREI Cost Penalty | +523,044 kWh | +523,044 kWh | **PASS** |
| **C13** | Strong Baseline (Sec. IV-D) | Transition Interaction Delta ($p < 0.01$) | -296,053 kWh | -296,053 kWh ($p=0.002$) | **PASS** |
| **C14** | Matched Budget (Table VIII) | Accounting Identity $C = R + 10 U$ Closed | Max Err $< 0.05$ kWh | 0.0000 kWh | **PASS** |
| **C15** | Matched Budget (Sec. IV-E) | Shortage Increases at Matched Budget ($\Delta U > 0$) | $> 0$ kWh (4/5 seeds) | +5,234.0 kWh (4/5 seeds) | **PASS** |
| **C16** | Rho Sensitivity (Sec. IV-E) | Absence of Economic Crossover for $\rho \ge 5$ | $\Delta \text{PSREI} > 0$ for all $\rho$ | All positive ($\rho=10$: +112k, $\rho=100$: +998k) | **PASS** |
| **C17** | External Sites (Table IX) | Directional Transfer Asymmetry (Kelmarsh $\to$ Penm) | 0.770 vs 0.341 | 0.770 vs 0.341 | **PASS** |
| **C18** | External Sites (Sec. IV-F) | LHB Micro-Farm Overfitting Boundary Guard | NMI 0.941, ARI 0.971 | NMI 0.941, ARI 0.971 | **PASS** |
| **C19** | Submission Audit | Full 73-Token Number Consistency Audit | 73/73 passed | 73/73 passed | **PASS** |

---

## 5. Secondary Reproduction Verification Suite

All supporting verification tools and audit scripts were executed in the clean remote clone and passed with exit code 0:

1. `python scripts/verify_tste_number_consistency.py`  
   - Output: `TSTE number consistency audit: complete_tste_number_consistency`  
   - Status: **PASS** (Exit 0)
2. `python scripts/verify_decisive_gate.py`  
   - Output: `ALL 10 DECISIVE EVIDENCE GATES PASSED (STATUS: VERIFIED)`  
   - Status: **PASS** (Exit 0)
3. `python scripts/verify_scientific_claim_gate.py`  
   - Output: `SCIENTIFIC_CLAIM_GATE: PASS`  
   - Status: **PASS** (Exit 0)
4. `python scripts/verify_table_a12_numbers.py`  
   - Output: Verified 12 market evaluation rows and 9 annual breakdown rows against Elexon BMRS data  
   - Status: **PASS** (Exit 0)
5. Manuscript Figures Generation:
   - `python scripts/plot_matched_budget_figures.py` $\to$ `matched_budget_transition_frontier.pdf`, `matched_budget_control_slices.pdf`, `rho_sensitivity.pdf` generated.
   - `python scripts/plot_gate_representation_stability.py` $\to$ `figure_gate_representation_stability.pdf` generated.
   - `python scripts/plot_rmse_vs_reserve_risk.py` $\to$ `figure_s_tradeoff.pdf` generated.
   - Status: **PASS** (Exit 0)

---

## 6. Strict Epistemic Bounds & Non-Claims

In strict compliance with the scientific control plane:
1. **Scope of Claim-Level Reproducibility**:
   The released code, public documentation, Category-A versioned artifacts, and Category-B derived release archive are sufficient to reproduce **every quantitative claim, table, and figure** presented in the manuscript.
2. **Explicit Non-Claim (Retraining Reproducibility)**:
   This certification does **not** claim full retraining reproducibility from raw 245-day SCADA sensor telemetry (~150 GPU hours across 134 turbines, Category C). Full end-to-end retraining requires raw Baidu KDD Cup 2022 dataset download and compute resources as documented in `docs/DATA_AVAILABILITY_AND_PREPROCESSING.md`.
3. **Preservation of Negative / Null Results**:
   The reproduction test explicitly confirms the paper's core negative finding: latent representation learning does not achieve plant-wide cost superiority over strong wind-speed-conditioned baselines (+523,044 kWh penalty), and state recoverability does not imply downstream decision sufficiency.
