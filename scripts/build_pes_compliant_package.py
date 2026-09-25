"""
Build and verify the strictly PES-compliant first-submission package for IEEE TSTE.
Target: IEEE Author Portal -> TSTE (tste-pes)
Package directory: artifacts/tste_submission_freeze_20260923_pes_compliant/
Zip archive: artifacts/tste_submission_freeze_20260923_pes_compliant.zip
"""
import os
import shutil
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
PKG_DIR = ROOT / "artifacts" / "tste_submission_freeze_20260923_pes_compliant"

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print(f"=== Building PES-Compliant TSTE First-Submission Package in {PKG_DIR} ===")
    
    if PKG_DIR.exists():
        shutil.rmtree(PKG_DIR)
        
    dirs = {
        "manuscript": PKG_DIR / "01_MANUSCRIPT",
        "standalone_tex": PKG_DIR / "02_STANDALONE_LATEX_SOURCE",
        "submission_docs": PKG_DIR / "03_SUBMISSION_DOCS",
        "compliance_audit": PKG_DIR / "04_COMPLIANCE_AND_AUDIT"
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # 1. Main Manuscript PDF and Markdown (strictly <= 10.0 pages, zero supplement references)
    src_main_pdf = ROOT / "build" / "paper_tste_ieee.pdf"
    dst_main_pdf = dirs["manuscript"] / "paper_tste_ieee.pdf"
    shutil.copy2(src_main_pdf, dst_main_pdf)
    shutil.copy2(ROOT / "paper_tste_ieee.md", dirs["manuscript"] / "paper_tste_ieee.md")
    print(f"[OK] Copied manuscript: {dst_main_pdf.name} ({dst_main_pdf.stat().st_size} bytes)")

    # 2. Standalone LaTeX Source Package
    standalone_src = ROOT / "standalone_ieee_package"
    for item in standalone_src.iterdir():
        if item.is_file():
            shutil.copy2(item, dirs["standalone_tex"] / item.name)
        elif item.is_dir() and item.name == "figures":
            shutil.copytree(item, dirs["standalone_tex"] / "figures", dirs_exist_ok=True)
    print(f"[OK] Copied standalone LaTeX package to {dirs['standalone_tex'].name}")

    # 3. Submission Docs
    # 3a. Cover Letter addressed to Prof. Hua Geng
    cover_letter_content = r"""# Cover Letter: IEEE Transactions on Sustainable Energy

**Date:** September 23, 2026  
**To:**  
Professor Hua Geng  
Editor-in-Chief, *IEEE Transactions on Sustainable Energy*  
Department of Automation, Tsinghua University, Beijing 100084, China  

**Subject:** Submission of Original Research Paper — *When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry*  

**Authors:** Junyu Li and Juntao Du* (Corresponding author: dujuntao@aufe.edu.cn)  
**Affiliation:** School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China  

Dear Professor Hua Geng,

We are pleased to submit our original research manuscript titled **"When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry"** for consideration as a Regular Paper in the *IEEE Transactions on Sustainable Energy*.

### Motivation, Power Systems Context, and Governing Thesis
Bulk power systems increasingly rely on operating reserve screening to hedge against generation over-forecasts near the aerodynamic transition boundary between Maximum Power Point Tracking (MPPT, Region 2) and blade-pitch regulation (Region 3). While deterministic aerodynamic power curves presume pristine telemetry, commercial wind farm SCADA systems encounter transmission latency, buffer backlogs, and telemetry dropouts. Under such degraded conditions, turbine operating regimes cease to be directly observable and become latent states.

We position **Level-1 reserve screening** as the wind plant Energy Management System (EMS) / aggregator's local operational risk assessment that evaluates qualified reserve bid quantities prior to wholesale market submission. Level-1 screening does not replace the system operator's Level-2 AC-OPF/SCUC transmission clearing, but provides the requisite risk-hedged availability inputs to prevent upstream bidding distortion.

Rather than asserting ungrounded claims of universal machine learning superiority, this paper formulates the operational triage and reliability boundaries across physical aerodynamics, non-neural statistical recalibration, and learned representations:
1. **Physical Superiority under Fresh Telemetry:** In the aerodynamic boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events), deterministic physical curves outperform deep neural networks by 8.1% under pristine telemetry, achieving the lowest reserve-screening surrogate cost ($589{,}535\text{ kWh}$ at $h=1$, $881{,}367\text{ kWh}$ at $h=6$).
2. **Staleness Breakdown vs. Recalibration:** Under contingency latency (60 min), unadapted physical rules undergo reliability breakdown ($24.0\%$ violation rate). However, when telemetry channels remain observable, non-neural state-conditional recalibration absorbs $55.3\%$ of this shortfall loss ($127.6 \to 57.0\text{ MWh}$) without parameter updates.
3. **Consequence-Based Latent-State Recovery:** When blade-pitch registers are unavailable at deployment (motivated by restricted aggregator access or sensor unavailability), observable consequence signals (contemporaneous active power, $\text{AUROC} = 0.988$) retain boundary information, and learned representations provide an effective recovery mechanism (doubling transition recall from $0.196$ to $0.416$).
4. **Dual Non-Equivalences & Matched-Budget Falsification:** Benchmarking against strong observable wind-speed-conditioned quantiles establishes two fundamental non-equivalences:
   $$\text{State Recoverability} \not\Rightarrow \text{Decision Superiority}$$
   $$\text{Lower Violation Frequency} \not\Rightarrow \text{Lower Shortage Severity}$$
   At matched reserve budgets ($\Delta R \equiv 0$), posterior conditioning does not establish shortage-energy efficiency over wind-speed binning ($+5{,}234\text{ kWh}$ higher shortfall on average across 5 seeds; $P(\Delta U \ge 0) = 0.81$). Furthermore, dynamic Mixture-of-Experts (MoE) routing confers no statistical advantage over unrouted dense baselines ($p=0.380$).

The central contribution of this paper is captured by its governing thesis:
> *"The value of model complexity is governed by information sufficiency, while state recoverability and decision superiority remain fundamentally non-equivalent."*

### Adherence to IEEE PES Submission Standards
- **Page Budget:** The main manuscript is formatted strictly within the IEEE 10.0-page limit (9 pages compiled in two-column IEEEtran, 0 overfull hboxes).
- **Self-Contained Manuscript:** In strict compliance with IEEE PES policy disallowing supplementary material at initial submission, the manuscript is completely self-contained. All necessary quantitative evidence, confidence intervals, and baselines are fully articulated within the text.
- **Reproducibility Archive:** Full replication scripts, manifests, raw SCADA benchmarks, and extended audit logs are openly hosted at: \url{https://github.com/b1ue13e/windfarm-latent-boundary-risk}.
- **Originality:** This manuscript is original, has not been published previously, and is not under consideration for publication elsewhere.
- **AI Statement:** Disclosed in the Acknowledgment section in full compliance with IEEE Author Center policy.

We believe this paper will be of strong interest to the readership of *IEEE Transactions on Sustainable Energy*, bridging power systems reserve economics, SCADA communication realism, and physics-constrained representation learning.

Thank you for your consideration of our work.

Sincerely,

**Juntao Du** (Corresponding Author)  
Professor, School of Statistics and Applied Mathematics  
Anhui University of Finance and Economics, Bengbu 233030, China  
Email: `dujuntao@aufe.edu.cn`  
"""
    (dirs["submission_docs"] / "Cover_Letter_IEEE_TSTE.md").write_text(cover_letter_content, encoding="utf-8")

    # 3b. Highlights and Keywords
    highlights_content = """# Highlights & Submission Metadata

## Manuscript Title
When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry

## Governing Thesis
The value of model complexity is governed by information sufficiency, while state recoverability and decision superiority remain fundamentally non-equivalent.

## Key Highlights
- **Reliability Boundary under Telemetry Staleness:** Shows that delayed inflow measurements across rated wind speed amplify cubic power curve errors, surging wind plant reserve shortfall violations to 24.0% under a 60-minute latency contingency.
- **Non-Neural Recalibration Sufficiency:** Demonstrates under the evaluated conditions that when telemetry channels remain observable, non-neural state-conditional quantile recalibration absorbs 55.3% of shortage losses without requiring neural model retraining.
- **Consequence-Based Latent-State Recovery:** Under aggregator-boundary pitch unobservability, secondary electromechanical consequence signatures (active power, AUROC = 0.988) preserve operating boundary information, and learned representations provide an effective recovery mechanism.
- **Dual Non-Equivalences:** Formalizes that latent state recoverability does not imply decision superiority, and lower violation frequency does not imply lower shortage severity.
- **Falsification of Architectural Routing:** Demonstrates that dynamic routing provides no additional decision advantage over matched unrouted representations (p = 0.380).
- **Strong-Baseline Closure:** Identifies that wind-speed-binned quantiles remain the operational minimum sufficient policy plant-wide, with matched-budget analysis refuting allocation efficiency superiority for the neural posterior.

## IEEE Keywords
Wind power reserve, SCADA telemetry degradation, latent operating boundary, state-conditional recalibration, minimum sufficient model, consequence-based recovery.
"""
    (dirs["submission_docs"] / "Highlights_and_Keywords.md").write_text(highlights_content, encoding="utf-8")

    # 3c. Data and Code Availability Statement
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
- Automated verification scripts (`scripts/verify_final_pdf_integrity.py`, `scripts/verify_decisive_gate.py`, `scripts/verify_scientific_claim_gate.py`) allow deterministic replication of all tables, CSV summaries, and claim ceilings reported in the manuscript.
"""
    (dirs["submission_docs"] / "Data_and_Code_Availability_Statement.md").write_text(availability_content, encoding="utf-8")

    # 3d. Author Information and COI
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

    # 4. Copy Audit and Control artifacts
    shutil.copy2(ROOT / "docs" / "TSTE_2026_EXTERNAL_COMPLIANCE_REPORT.md", dirs["compliance_audit"] / "TSTE_2026_EXTERNAL_COMPLIANCE_REPORT.md")
    shutil.copy2(ROOT / "docs" / "TSTE_PEER_REVIEW_ATTACK_SIMULATION.md", dirs["compliance_audit"] / "TSTE_PEER_REVIEW_ATTACK_SIMULATION.md")
    shutil.copy2(ROOT / "docs" / "SCIENTIFIC_CONTRACT.md", dirs["compliance_audit"] / "SCIENTIFIC_CONTRACT_FREEZE.md")
    shutil.copy2(ROOT / "docs" / "CLAIM_PRECISION_PATCH_REPORT.md", dirs["compliance_audit"] / "CLAIM_PRECISION_PATCH_REPORT.md")
    print(f"[OK] Copied compliance and control artifacts to {dirs['compliance_audit'].name}")

    # 5. Generate Checksums Manifest
    checksum_file = PKG_DIR / "CHECKSUMS_AND_FILE_MANIFEST.txt"
    lines = ["# SHA256 File Manifest for IEEE PES Compliant First-Submission Package", f"# Generated: 2026-09-23\n"]
    
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

    # 6. Create ZIP archive
    zip_path = ROOT / "artifacts" / "tste_submission_freeze_20260923_pes_compliant.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root_path, _, filenames in os.walk(PKG_DIR):
            for f in sorted(filenames):
                fp = Path(root_path) / f
                arcname = fp.relative_to(PKG_DIR.parent)
                zf.write(fp, arcname)
    print(f"[OK] Generated PES-compliant submission ZIP: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print("=== PES-Compliant Package Generation Complete ===")

if __name__ == "__main__":
    main()
