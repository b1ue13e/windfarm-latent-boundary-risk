# External Release Metadata

**Release Version**: `v1.0`  
**Git Tag**: `tste-submission-v1.0`  
**Target Venue**: IEEE Transactions on Sustainable Energy (TSTE)  
**Effective Date**: 2026-09-26  
**License**: MIT / Open Research Access  

---

## 1. Release Bundle Specifications

| Attribute | Specification |
| :--- | :--- |
| **Archive Filename** | `windfarm_derived_artifacts_v1.0.zip` |
| **Permanent Download URL** | `https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/tste-submission-v1.0/windfarm_derived_artifacts_v1.0.zip` |
| **Release Webpage** | `https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/tag/tste-submission-v1.0` |
| **Exact Byte Size** | `195,613,174` bytes (186.55 MB) |
| **Cryptographic SHA256** | `cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22` |
| **Archive Format** | Standard Deflate ZIP (`.zip`) |

---

## 2. Packaged Category B Artifacts

This release bundle contains the two high-dimensional precomputed evaluation arrays (Category B) required to audit arrival-time information symmetry, evaluate matched-budget frontiers, and verify all 19 quantitative manuscript claims without retraining models:

### 2.1 Fixed Forecast Residuals
- **Path**: `artifacts/fixed_forecast_residuals.npz`
- **Exact Size**: `173,410,167` bytes
- **SHA256**: `b05b3751f45e2a2c1619623da3d038317769caec7d6a59b207eb4ea088e5d0d7`
- **Description**: Canonical frozen point forecasts, realized shortfall residuals, and boundary-active indices across 5 random seeds (201--205) and 6 dispatch horizons ($h \in \{1, 2, 3, 4, 5, 6\}$).
- **Generating Script**: `scripts/decisive_fair_risk_benchmark.py`

### 2.2 Cached Posterior Probabilities
- **Path**: `artifacts/matched_budget/cached_posterior_probs.npz`
- **Exact Size**: `22,475,033` bytes
- **SHA256**: `d40f0ddbaee7452d3a339dd8917e766fb31ec227242c7f078d46a48970e4e7e7`
- **Description**: Operating-boundary posterior probability distributions $\hat{\pi}_t$ across evaluated test sequences, used for matched-reserve-budget allocation ($B_{\text{common}}$) and $\rho$-sensitivity sweeps.
- **Generating Script**: `scripts/run_matched_budget_frontier.py`

---

## 3. Repository and Tag Compatibility

- **Repository**: `https://github.com/b1ue13e/windfarm-latent-boundary-risk.git`
- **Visibility**: Public
- **Tag**: `tste-submission-v1.0`
- **Branch**: `revision_topjournal_reconstruction`
- **Verification Workflow**:
  ```powershell
  # Clone public repository at release tag
  git clone --branch tste-submission-v1.0 https://github.com/b1ue13e/windfarm-latent-boundary-risk.git
  cd windfarm-latent-boundary-risk

  # Install requirements
  pip install -r requirements.txt

  # Fetch release bundle from permanent URL
  python scripts/fetch_artifacts.py

  # Run one-command replication auditor
  python scripts/verify_replication.py
  ```
- **Claim-Level Reproducibility Verdict**: `EXTERNALLY_REPRODUCIBLE_AT_CLAIM_LEVEL` (19/19 claims verified).
