# Clean-Clone Reproducibility Audit

**Date**: 2026-09-25  
**Test Directory**: `E:\windfarm_clean_clone_test`  
**Source Commit**: `4a79b09` (`chore(reproducibility): commit frozen decisive results, matched-budget campaign, and compliance reports before clean clone audit`)  
**Audit Status**: COMPLETED (FAILURES IDENTIFIED & CATALOGED)

---

## 1. Executive Summary

A fresh, isolated clone of the repository was created at `E:\windfarm_clean_clone_test` containing strictly the committed files from Git.
Every manuscript verification and entry command from `README.md` and `.agents/verification_manifest.json` was executed in the clean directory.

Out of 9 evaluated verification and execution workflows, **2 passed** (`tests/test_smoke.py + test_paper.py`, and `scripts/verify_scientific_claim_gate.py`), while **7 failed**.
Failures were systematically traced to six distinct root causes:
1. Missing artifacts excluded by `.gitignore` (`artifacts/` directory);
2. Large unversioned artifacts (`fixed_forecast_residuals.npz`, 173 MB);
3. Hardcoded absolute Windows paths (`E:/论文3`, `E:\MiKTeX`, `C:\texlive`);
4. Missing raw public datasets (`wtbdata_245days.csv`);
5. Undocumented runtime dependencies (`pypdf`, root `requirements.txt`, system `pandoc`/`xelatex`);
6. Implicit cached build outputs (`build/paper_tste_ieee.pdf`).

---

## 2. Command-by-Command Audit Results

| Command | Status | Exit Code | Failure Mechanism | Root Cause Category |
| :--- | :---: | :---: | :--- | :--- |
| `python main.py preprocess --root-dir .` | **FAIL** | 1 | `FileNotFoundError: wtbdata_245days.csv` | Missing Public Data / `.gitignore` exclusion |
| `python main.py train ... --max-days 3` | **FAIL** | 1 | `FileNotFoundError: wtbdata_245days.csv` | Missing Public Data / Implicit Cache Dependency |
| `python -m pytest tests/test_smoke.py tests/test_paper.py` | **PASS** | 0 | 31/31 unit tests pass | N/A (Self-contained) |
| `powershell -File scripts/build_paper_ieee.ps1` | **FAIL** | 1 | `Pandoc not found` / missing `tools/` binary | Undocumented Environment / Local Path |
| `python scripts/verify_final_pdf_integrity.py` | **FAIL** | 1 | `FileNotFoundError: build/paper_tste_ieee.pdf` | Implicit Cached Object / Hardcoded `build/` |
| `python scripts/verify_decisive_gate.py` | **FAIL** | 1 | 9 missing artifacts in `artifacts/` and `build/` | Missing Artifacts / Large Artifacts |
| `python scripts/verify_tste_number_consistency.py` | **FAIL** | 1 | `FileNotFoundError: artifacts/.../anchor_stress...csv` | Missing Artifacts (`.gitignore` exclusion) |
| `python scripts/verify_scientific_claim_gate.py` | **PASS** | 0 | Control files and strong-baseline CSVs present | N/A (Tracked in commit `4a79b09`) |
| `python .agents/scripts/verify_gate.py` | **FAIL** | 1 | 3/4 manifest commands failed | Downstream Cascade |

---

## 3. Detailed Failure Breakdown by Root Cause

### 3.1 Missing Artifacts & `.gitignore` Exclusions
- **Symptom**: `scripts/verify_decisive_gate.py` reports 7 missing artifacts under `artifacts/`:
  - `artifacts/information_set_manifest.csv` (133 KB)
  - `artifacts/direct_quantile_baselines_summary.csv` (5.9 KB)
  - `artifacts/factorial_boundary_ablation_summary.csv` (12.8 KB)
  - `artifacts/posterior_calibration.csv` (3.0 KB)
  - `artifacts/channel_consequence_ablations.csv` (3.6 KB)
  - `artifacts/mediation_analysis.csv` (3.0 KB)
  - `artifacts/active_power_anchor_audit.csv` (13 KB)
- **Symptom**: `scripts/verify_tste_number_consistency.py` fails looking for:
  - `artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv`
  - `artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv`
  - `artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv`
  - `artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv`
  - `artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv`
  - `artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv`
  - `artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv`
  - `artifacts/anchor_stress_guard/anchor_stress_summary.csv`
  - `artifacts/external_wind_guard_windowfix/external_wind_guard.json`
  - `artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json`
  - `artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json`
- **Root Cause**: `.gitignore` line 18 explicitly ignores `artifacts/`. While individual older files were tracked, newly produced and decisive artifacts were blocked from Git tracking.

### 3.2 Large Essential Precomputed Artifacts
- **Symptom**: `artifacts/fixed_forecast_residuals.npz` (173.4 MB) is required by `scripts/verify_decisive_gate.py` to audit arrival-time information symmetry and residual distribution across 5 seeds and 6 horizons.
- **Symptom**: `artifacts/matched_budget/cached_posterior_probs.npz` (22.5 MB) is required to re-evaluate the matched-budget frontier.
- **Root Cause**: Excluded from Git due to repository size constraints (>100 MB), but not previously backed by an automated public release retrieval mechanism (`scripts/fetch_artifacts.py`).

### 3.3 Absolute Local Paths & Machine Dependence
- **Symptom**: Multiple production scripts contain hardcoded Windows drive letters and paths:
  - `Path("e:/论文3")` in `scripts/build_pes_compliant_package.py`, `scripts/build_submission_freeze_package_20260923.py`, `scripts/plot_matched_budget_figures.py`, `scripts/run_matched_budget_frontier.py`, `scripts/run_rho_sensitivity.py`, `scripts/test_strong_baseline_closure.py`, `scripts/retrieve_cluster_artifacts.py`, and `tests/test_matched_budget_accounting.py`.
  - `r'E:\论文3'` in `scripts/verify_pdf_content.py`.
  - `E:\MiKTeX\miktex\bin\x64\xelatex.exe` and `C:\texlive\2025\bin\windows\xelatex.exe` in `scripts/build_paper_ieee.ps1`, `scripts/build_paper.ps1`, and `scripts/compile_and_check_pages.py`.
  - `tools\pandoc-3.9.0.2\pandoc.exe` in `scripts/build_paper_ieee.ps1`.
- **Root Cause**: Developer local convenience during iterative paper drafting without relative path normalization (`Path(__file__).resolve().parents[...]`).

### 3.4 Missing Raw Public Data
- **Symptom**: `main.py preprocess` fails on missing `wtbdata_245days.csv`.
- **Root Cause**: Raw dataset is 245-day continuous telemetry (~1.2 GB raw) from Baidu KDD Cup 2022. It is correctly `.gitignore`d, but the clean clone lacked:
  - Clear official download URL;
  - Automated checksum check;
  - Decoupling of verification from raw data preprocessing (manuscript verification should evaluate derived artifacts without requiring raw 24-hour training).

### 3.5 Undocumented Runtime Environment
- **Symptom**: Python environment lacked `pypdf` (which is imported by PDF audit scripts).
- **Symptom**: Root repository lacked a consolidated `requirements.txt` (`requirements-ci.txt` only listed 3 packages).
- **Symptom**: External tools `pandoc` and `xelatex` were assumed present in author-specific folders rather than checked dynamically in `PATH` or declared as prerequisites.

### 3.6 Implicit Cached Objects & Build Folder Expectations
- **Symptom**: `scripts/verify_final_pdf_integrity.py` and `scripts/verify_decisive_gate.py` checked `build/paper_tste_ieee.pdf` and `build/paper_tste_supplementary.pdf`.
- **Root Cause**: `build/` is gitignored. However, canonical compiled PDFs are committed at the repository root (`paper_tste_ieee.pdf`, `paper_tste_supplementary.pdf`) and in `standalone_ieee_package/main.pdf`. Verification scripts failed to inspect the committed release PDFs when `build/` was absent.

---

## 4. Remediation Action Plan

1. **Phase 2**: Create `artifacts/ARTIFACT_MANIFEST.json` with cryptographic SHA256 hashes, generating scripts, upstream inputs, and claim mappings for every manuscript headline number.
2. **Phase 3**: Purge all hardcoded `e:/论文3`, `E:\MiKTeX`, and absolute drive paths. Standardize on `REPO_ROOT = Path(__file__).resolve().parents[...]` and environment variable overrides (`WINDFARM_DATA_DIR`, `WINDFARM_ARTIFACTS_DIR`).
3. **Phase 4**: Classify all artifacts:
   - Category A (Small, essential tables < 5 MB): Track directly in Git.
   - Category B (Large, essential arrays > 5 MB): Package via `scripts/package_release_artifacts.py` and fetch via `scripts/fetch_artifacts.py`.
   - Category C (Regenerable tables): Implement deterministic generation commands.
   - Category D (Raw datasets): Document sources in `docs/DATA_AVAILABILITY_AND_PREPROCESSING.md`.
4. **Phase 5**: Implement `scripts/verify_replication.py` to perform one-command, fail-closed replication of every manuscript claim.
5. **Phase 6**: Update `README.md` with the exact 5-step replication workflow.
6. **Phase 7**: Re-test in fresh directory `E:\windfarm_clean_clone_test` to confirm `FULLY_REPRODUCIBLE`.
