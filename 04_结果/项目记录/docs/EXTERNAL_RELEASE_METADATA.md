# External Release Metadata

> **Metadata corrected 2026-10-18; release bytes unchanged.** Corrected both member SHA256 values and qualified producer attributions using measured members, historical manifests and versioned source. [Reconciliation and corrected manifest](../analyses/legacy_release_hash_audit_20261018/REPORT.md); [original document](../analyses/legacy_release_hash_audit_20261018/snapshots/pre_correction_EXTERNAL_RELEASE_METADATA.md). The immutable release tag retains its historical document. E07 remains unactivated.

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

This historical release bundle contains exactly the two precomputed evaluation arrays below. Their identities are verified against the unchanged ZIP and release-tag manifest. Checksum agreement does not certify arrival-time causality, raw retraining, or all manuscript claims; current scientific interpretations remain governed by `docs/SCIENTIFIC_CONTRACT.md`.

### 2.1 Fixed Forecast Residuals
- **Path**: `artifacts/fixed_forecast_residuals.npz`
- **Exact Size**: `173,410,167` bytes
- **SHA256**: `b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9`
- **Description**: Canonical frozen point forecasts, realized shortfall residuals, and boundary-active indices across 5 random seeds (201--205) and 6 dispatch horizons ($h \in \{1, 2, 3, 4, 5, 6\}$).
- **Producer attribution (source-compatible, exact executed version UNKNOWN)**: `scripts/build_fixed_forecast_residuals.py` exists at the release tag and writes this path. The original document named `decisive_fair_risk_benchmark.py`; the release-tag manifest instead named the absent `run_fixed_target_contract.py`. The manifest attribution was corrected at `00c92f0b`. No hash-bound original generation receipt has been identified; see the reconciliation report.

### 2.2 Cached Posterior Probabilities
- **Path**: `artifacts/matched_budget/cached_posterior_probs.npz`
- **Exact Size**: `22,475,033` bytes
- **SHA256**: `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca`
- **Description**: Operating-boundary posterior probability distributions $\hat{\pi}_t$ across evaluated test sequences, used for matched-reserve-budget allocation ($B_{\text{common}}$) and $\rho$-sensitivity sweeps.
- **Producer attribution (manifest/source, exact executed version UNKNOWN)**: `scripts/run_matched_budget_frontier.py`. The campaign provenance records HEAD `621bb8b`, where this path is absent; the release-tag source is archived in Git but is not a proven execution snapshot.

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
- **Historical reported verdict**: `EXTERNALLY_REPRODUCIBLE_AT_CLAIM_LEVEL` (19/19 reported in the old audit). This metadata correction does not renew that verdict or upgrade current scientific certification.
