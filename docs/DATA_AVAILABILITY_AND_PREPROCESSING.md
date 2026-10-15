# Data Availability and Preprocessing Guide

**Date**: 2026-09-25  
**Version**: 1.0 (Freeze Release)

This document provides official public sources, licenses, cryptographic specifications, and exact preprocessing instructions for all raw datasets used across the investigation.

---

## 1. Overview of Evaluated Facilities

| Dataset Identifier | Turbine Architecture | Array Size ($N$) | Telemetry Duration | Sampling Resolution | Primary Observability Role |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **WTB (SDWPF / KDD Cup 2022)** | 1.5 MW Commercial Turbines | 134 | 245 indexed days; calendar dates not verified from the CSV | 10 minutes | Primary mechanism identification; boundary band $|v-10.5| \le 1.0$ m/s |
| **Kelmarsh** | Senvion MM92 (2.05 MW) | 6 | Local archives named 2016--2024; fixed245-day evaluation window | 10 minutes | External validity probe; compact layout, low spatial wake redundancy |
| **Penmanshiel** | Senvion MM82 (2.05 MW) | 14 operational (WT01--WT15 ex. WT03) | Local archives named 2016--2024; fixed245-day evaluation window | 10 minutes | External validity probe; complex terrain, high wake interaction |
| **ENGIE La Haute Borne (LHB)** | Senvion MM82 (2.05 MW) | 4 | Local archive named 2017--2020; evaluated245-day window | 10 minutes | Transferability failure boundary; small-farm diagnostic; raw replay pending |
| **ERA5 Reanalysis** | ECMWF Reanalysis v5 | 256 cells ($16 \times 16$) | 3 continuous months (2,208 hrs) | 1 hour | Thermodynamic surface sensible heat flux convective contrast |

---

## 2. Public Dataset Sources & Acquisition

### 2.1 SDWPF / Baidu KDD Cup 2022 (WTB)
- **Official Host**: Baidu AI Studio / KDD Cup 2022 Wind Power Forecasting Challenge
- **Canonical Repository**: [https://aistudio.baidu.com/competition/detail/166/0/introduction](https://aistudio.baidu.com/competition/detail/166/0/introduction)
- **License**: CC BY-NC-SA 4.0 / Open Benchmark Access
- **Files Required**:
  - `wtbdata_245days.csv` (~1.2 GB raw SCADA text)
  - `sdwpf_baidukddcup2022_turb_location.CSV` (Array spatial coordinate mapping)
- **Direct CLI Placement**: Place both files directly into the repository root.

### 2.2 Kelmarsh Wind Plant
- **Official Host**: Zenodo (OpenOA Benchmark Archive)
- **DOI**: [10.5281/zenodo.5841834](https://doi.org/10.5281/zenodo.5841834)
- **Curated By**: EDF Renewables & National Renewable Energy Laboratory (NREL)
- **License**: Creative Commons Attribution 4.0 International

### 2.3 Penmanshiel Wind Plant
- **Official Host**: Zenodo (OpenOA Benchmark Archive)
- **DOI**: [10.5281/zenodo.5944505](https://doi.org/10.5281/zenodo.5944505)
- **Curated By**: Cubico Sustainable Investments & NREL
- **Operational Notes**: 14 operational turbines analyzed (numbered WT01 to WT15; WT03 is permanently decommissioned and omitted from spatial graphs).

### 2.4 ENGIE La Haute Borne (LHB)
- **Official Host**: ENGIE Open Data / Zenodo
- **DOI**: [10.5281/zenodo.4764632](https://doi.org/10.5281/zenodo.4764632)
- **Turbines**: 4 units (R80711, R80721, R80736, R80790)

### 2.5 ECMWF ERA5 Thermodynamic Grid
- **Official Host**: Copernicus Climate Change Service (C3S) Climate Data Store (CDS)
- **API**: `cdsapi` service for single-level reanalysis parameters:
  - Surface sensible heat flux (`sshf`)
  - Boundary layer height (`blh`)
  - Convective available potential energy (`cape`)
  - Friction velocity (`zust`)

---

## 3. Preprocessing and Cache Reconstruction

Preprocessing converts raw CSVs into memory-mapped NumPy arrays with chronological train/val/test splits, strictly enforcing causal information symmetry and non-forward lookahead.

### Step 1: Preprocess WTB Telemetry
```powershell
python main.py preprocess --root-dir . --dataset wtb
```
Outputs the default cache to `artifacts/cache/wtb_245d/`. Signature variants and train-only weights require explicit additional transformations:
- `features.npy`: Shape `(35280, 134, 11)`
- `target.npy`: Active power realization `(35280, 134)`
- `target_mask.npy`: Target validity flags `(35280, 134)`

### Step 2: Preprocess External Facilities
```powershell
python main.py external-wind-preprocess --root-dir . --farm kelmarsh
python main.py external-wind-preprocess --root-dir . --farm penmanshiel
python main.py external-wind-preprocess --root-dir . --farm la_haute_borne
```

### Note on Replication Shortcuts
Cached Category B arrays permit only bounded re-evaluation of archived claims. They do not verify raw-data preprocessing or neural training. Complete reproduction remains unverified until the registered raw replay succeeds; see `RAW_REPLAY_PROTOCOL_20261015.md`. No runtime guarantee is made.

### Category B Release Bundle Metadata
- **Permanent URL**: [https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/tste-submission-v1.0/windfarm_derived_artifacts_v1.0.zip](https://github.com/b1ue13e/windfarm-latent-boundary-risk/releases/download/tste-submission-v1.0/windfarm_derived_artifacts_v1.0.zip)
- **Git Tag**: `tste-submission-v1.0`
- **Archive Size**: `195,613,174` bytes (186.55 MB)
- **SHA256**: `cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22`
- **Complete Details**: See [`docs/EXTERNAL_RELEASE_METADATA.md`](EXTERNAL_RELEASE_METADATA.md)

