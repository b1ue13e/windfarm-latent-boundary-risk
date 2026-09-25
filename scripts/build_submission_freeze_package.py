"""
Build and verify the ScholarOne-ready submission package for IEEE TSTE.
Creates: artifacts/tste_submission_freeze_20260921/
"""
import os
import shutil
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
PKG_DIR = ROOT / "artifacts" / "tste_submission_freeze_20260921"

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print(f"=== Building TSTE Submission Freeze Package in {PKG_DIR} ===")
    
    # 1. Prepare directory structure
    dirs = {
        "manuscript": PKG_DIR / "01_MANUSCRIPT",
        "supplementary": PKG_DIR / "02_SUPPLEMENTARY",
        "submission_docs": PKG_DIR / "03_SUBMISSION_DOCS",
        "audit_control": PKG_DIR / "04_AUDIT_AND_CONTROL"
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # 2. Copy Manuscript files
    src_main_pdf = ROOT / "build" / "paper_tste_ieee.pdf"
    if not src_main_pdf.exists():
        src_main_pdf = ROOT / "paper_tste_ieee.pdf"
    dst_main_pdf = dirs["manuscript"] / "paper_tste_ieee.pdf"
    shutil.copy2(src_main_pdf, dst_main_pdf)
    shutil.copy2(ROOT / "paper_tste_ieee.md", dirs["manuscript"] / "paper_tste_ieee.md")
    print(f"[OK] Copied manuscript: {dst_main_pdf.name} ({dst_main_pdf.stat().st_size} bytes)")

    # 3. Copy Supplementary files
    src_supp_pdf = ROOT / "build" / "paper_tste_supplementary.pdf"
    if not src_supp_pdf.exists():
        src_supp_pdf = ROOT / "paper_tste_supplementary.pdf"
    dst_supp_pdf = dirs["supplementary"] / "paper_tste_supplementary.pdf"
    shutil.copy2(src_supp_pdf, dst_supp_pdf)
    shutil.copy2(ROOT / "paper_tste_supplementary.md", dirs["supplementary"] / "paper_tste_supplementary.md")
    print(f"[OK] Copied supplementary: {dst_supp_pdf.name} ({dst_supp_pdf.stat().st_size} bytes)")

    # 4. Create Submission Docs
    # 4a. Cover Letter
    cover_letter_content = r"""# Cover Letter: IEEE Transactions on Sustainable Energy

**Date:** September 21, 2026  
**To:**  
Editor-in-Chief  
*IEEE Transactions on Sustainable Energy*  

**Subject:** Submission of Original Research Paper — *When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry*  

**Authors:** Junyu Li and Juntao Du* (Corresponding author: dujuntao@aufe.edu.cn)  
**Affiliation:** School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China  

Dear Editor-in-Chief and Editorial Board,

We are pleased to submit our original research manuscript titled **"When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry"** for consideration as a Regular Paper in the *IEEE Transactions on Sustainable Energy*.

### Motivation and Core Scientific Focus
Bulk power systems increasingly rely on operating reserve screening to hedge against catastrophic generation over-forecasts near the aerodynamic transition boundary between Maximum Power Point Tracking (MPPT, Region 2) and blade-pitch regulation (Region 3). While deterministic aerodynamic power curves presume pristine telemetry, commercial wind farm SCADA systems frequently experience transmission latency, packet serialization dropouts, and aggregator-boundary pitch unobservability. Under such degraded conditions, turbine operating regimes cease to be directly observable and become latent states.

Rather than presenting an ungrounded claim of universal machine learning superiority, this paper formulates the operational triage and reliability boundaries across physical aerodynamics, non-neural statistical recalibration, and learned representations:
1. **Physical Superiority under Fresh Telemetry:** In the aerodynamic boundary band ($|v_{\\text{phys}}-10.5|\\le 1.0\\text{ m/s}$, $N=13{,}883$ events), deterministic physical curves outperform deep neural networks by 8.1% under pristine telemetry, achieving the lowest reserve-screening surrogate cost.
2. **Staleness Breakdown vs. Recalibration:** Under contingency latency (60 min), unadapted physical rules suffer reliability collapse ($24.0\%$ violation rate). However, when channels remain observable, non-neural state-conditional recalibration absorbs $55.3\\%$ of this shortfall loss without parameter updates.
3. **Targeted Representation Utility under Pitch Withholding:** When blade-pitch registers are withheld across aggregator firewalls, learned representations reconstruct operating regimes from secondary consequence signatures (active power divergence, trajectory tracking, and wake advection), reducing surrogate costs by $46.7\\text{k}\\text{--}68.6\\text{k kW}\\cdot\\text{h}$ over unadapted physics.
4. **Negative Results and Mechanism Falsification:** Benchmarking against strong observable wind-speed-conditioned quantiles reveals that posterior conditioning acts as a transition-localized risk hedge rather than a plant-wide cost reducer. Furthermore, dynamic Mixture-of-Experts (MoE) routing confers no statistical advantage over unrouted dense baselines ($p=0.380$), and heuristic selective abstention is Pareto-dominated by uniform reserve margin expansion.

### Adherence to IEEE TSTE Standards
- **Page Budget:** The main manuscript is formatted strictly within the IEEE 10.0-page limit (10 pages including references).
- **Supplementary Material:** A comprehensive 44-page Supplementary Material document is provided containing full derivation details, 42 audited tables, seed-by-seed records, and cross-site empirical transfer analyses.
- **Originality:** This manuscript is original, has not been published previously, and is not under consideration for publication elsewhere.
- **AI Statement:** Complies with IEEE guidelines on generative AI tools.

We believe this paper will be of strong interest to the readership of *IEEE Transactions on Sustainable Energy*, bridging power systems reserve economics, SCADA communication realism, and physics-constrained representation learning.

Thank you for your consideration of our work.

Sincerely,

**Juntao Du** (Corresponding Author)  
Professor, School of Statistics and Applied Mathematics  
Anhui University of Finance and Economics, Bengbu 233030, China  
Email: `dujuntao@aufe.edu.cn`  
"""
    (dirs["submission_docs"] / "Cover_Letter_IEEE_TSTE.md").write_text(cover_letter_content, encoding="utf-8")

    # 4b. Highlights and Keywords
    highlights_content = """# Highlights & Submission Metadata

## Manuscript Title
When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry

## Key Highlights
- **Reliability Boundary under Telemetry Staleness:** Establishes that delayed inflow measurements across rated wind speed amplify cubic power curve errors, surging wind plant reserve shortfall violations to 24.0% under a 60-minute latency contingency.
- **Non-Neural Recalibration Sufficiency:** Proves that when telemetry channels remain observable, non-neural state-conditional quantile recalibration absorbs 55.3% of shortage losses without requiring neural model retraining.
- **Consequence-Based Latent-State Recovery:** Under aggregator-boundary pitch unobservability, learned representations recover operating boundary states from secondary electromechanical and active-power consequence signatures, doubling transition recall.
- **Falsification of Architectural Routing:** Demonstrates that dynamic Mixture-of-Experts (MoE) routing yields no statistical advantage over unrouted dense baselines (p = 0.380), establishing that reserve improvements stem from latent-state awareness rather than dynamic expert routing.
- **Negative Finding on Selective Abstention:** Proves that heuristic selective abstention fails to beat random rejection under communication latency, being Pareto-dominated by uniform reserve margin expansion.
- **Strong-Baseline Closure:** Identifies that wind-speed-binned quantiles remain the minimum sufficient policy plant-wide, with posterior conditioning serving as a transition-localized tail-risk hedge at higher reserve procurement.

## IEEE Keywords
Wind turbine operating reserve; SCADA telemetry degradation; partial observability; latent operating boundary; transmission latency; aerodynamic power curve; reliability breakdown; reserve-risk screening; state-conditional recalibration; MPPT-to-pitch transition.
"""
    (dirs["submission_docs"] / "Highlights_and_Keywords.md").write_text(highlights_content, encoding="utf-8")

    # 4c. Data and Code Availability Statement
    availability_content = """# Data and Code Availability Statement

## 1. Raw SCADA Datasets
All raw wind-turbine SCADA datasets used in this paper are publicly accessible:
1. **WTB (134-Turbine Commercial Farm):** Sourced from the Baidu KDD Cup 2022 Spatial Dynamic Wind Power Forecasting Challenge (SDWPF). Publicly archived: https://github.com/PaddlePaddle/PaddleSpatial/tree/main/research/SDWPF.
2. **Kelmarsh Commercial Wind Farm (6 MM92 Turbines):** Open SCADA operational records provided by Cubico Sustainable Investments under CC-BY 4.0 license via Zenodo: https://zenodo.org/record/5841834.
3. **Penmanshiel Commercial Wind Farm (14 Operational MM82 Turbines):** Open SCADA operational records provided by Cubico Sustainable Investments via Zenodo: https://zenodo.org/record/5940509.
4. **ENGIE La Haute Borne Wind Farm (4 MM82 Turbines):** Open SCADA records provided by ENGIE via the Open Data portal: https://opendata-renewables.engie.com/.
5. **ERA5 Atmospheric Reanalysis:** ECMWF ERA5 hourly single-level atmospheric reanalysis data: https://cds.climate.copernicus.eu/.

## 2. Replication Code, Manifests, and Checkpoints
- Complete preprocessing pipelines, information-set contracts, fixed forecast residuals, model training scripts, and evaluation suites are archived in the project repository: https://github.com/b1ue13e/windfarm-latent-boundary-risk.
- Automated verification scripts (`scripts/verify_final_pdf_integrity.py`, `scripts/verify_decisive_gate.py`, `scripts/verify_scientific_claim_gate.py`) allow deterministic, one-click replication of all tables, CSV summaries, and claim ceilings reported in the manuscript.
"""
    (dirs["submission_docs"] / "Data_and_Code_Availability_Statement.md").write_text(availability_content, encoding="utf-8")

    # 4d. Author Bio and COI
    bio_content = """# Author Information and Conflict of Interest Declaration

## Authors
1. **Junyu Li**
   School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China.
2. **Juntao Du** (Corresponding Author)
   Professor, School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China.
   Email: dujuntao@aufe.edu.cn

## Conflict of Interest
The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Ethical Statement
This study does not involve any human subjects or animal experiments.
"""
    (dirs["submission_docs"] / "Author_Bio_and_COI.md").write_text(bio_content, encoding="utf-8")

    # 5. Copy Audit and Control artifacts
    shutil.copy2(ROOT / "docs" / "SCIENTIFIC_CONTRACT.md", dirs["audit_control"] / "SCIENTIFIC_CONTRACT_FREEZE.md")
    shutil.copy2(ROOT / "docs" / "EXPERIMENT_REGISTRY.md", dirs["audit_control"] / "EXPERIMENT_REGISTRY_FREEZE.md")
    shutil.copy2(ROOT / "docs" / "TSTE_SUBMISSION_DESK_REJECT_AUDIT_20260921.md", dirs["audit_control"] / "TSTE_SUBMISSION_DESK_REJECT_AUDIT.md")
    shutil.copy2(ROOT / "artifacts" / "strong_baseline_closure_summary.csv", dirs["audit_control"] / "strong_baseline_closure_summary.csv")
    print(f"[OK] Copied control artifacts to {dirs['audit_control'].name}")

    # 6. Generate Checksums Manifest
    checksum_file = PKG_DIR / "CHECKSUMS_AND_FILE_MANIFEST.txt"
    lines = ["# SHA256 File Manifest for IEEE TSTE Submission Freeze Package", f"# Generated: 2026-09-21\n"]
    
    all_files = []
    for root_path, _, filenames in os.walk(PKG_DIR):
        for f in sorted(filenames):
            if f == "CHECKSUMS_AND_FILE_MANIFEST.txt" or f.endswith(".zip"):
                continue
            fp = Path(root_path) / f
            rel = fp.relative_to(PKG_DIR)
            digest = sha256_file(fp)
            lines.append(f"{digest}  {rel.as_posix()}")
            all_files.append(fp)
            
    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Wrote checksums manifest: {len(all_files)} files")

    # 7. Create ZIP archive
    zip_path = ROOT / "artifacts" / "TSTE_SUBMISSION_PACKAGE_20260921.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root_path, _, filenames in os.walk(PKG_DIR):
            for f in sorted(filenames):
                fp = Path(root_path) / f
                arcname = fp.relative_to(PKG_DIR.parent)
                zf.write(fp, arcname)
    print(f"[OK] Generated submission ZIP: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print("=== Submission Freeze Package Generation Complete ===")

if __name__ == "__main__":
    main()
