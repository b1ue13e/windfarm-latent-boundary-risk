# IEEE Power & Energy Society (PES) / TSTE 2026 Author Compliance Audit Report

**Date:** 2026-09-23  
**Target Venue:** *IEEE Transactions on Sustainable Energy* (TSTE)  
**Submission Portal:** IEEE Author Portal $\to$ TSTE (`tste-pes`) $\to$ ScholarOne backend  
**Target Editor-in-Chief:** Professor Hua Geng (Department of Automation, Tsinghua University)  
**Evaluated Package:** `artifacts/tste_submission_freeze_20260923_pes_compliant/` and `tste_submission_freeze_20260923_pes_compliant.zip`  

---

## 1. Executive Summary & Regulatory Finding

Following the May 2026 update to the **IEEE Power & Energy Society (PES) Author's Kit**, an exhaustive external-compliance audit was conducted against official PES Transactions submission rules.

### Key Regulatory Requirements Identified:
1. **No Supplementary Material Allowed at First Submission**:
   - Official PES Rule: *"PES does not allow the submission of supplementary material."* (Under *Upload Manuscript* step in IEEE Author Portal / ScholarOne).
   - *Impact on Prior Freeze Package:* The 44-page Supplementary Material PDF (`paper_tste_supplementary.pdf`) cannot be uploaded as a formal peer-review file. Furthermore, the main manuscript cannot rely on external "Supplementary Table A..." or "Supplementary Section S..." citations to establish its claims.
2. **Strict 10-Page Standard Length**:
   - PES Transactions first submissions are limited to 10 pages maximum (including references and bios).
3. **Abstract Length & Self-Containment**:
   - PES Author's Kit mandates an abstract of approximately 150–200 words that is fully self-contained. The prior draft was 385 words (resembling a mini results section).
4. **AI-Generated Text Disclosure Location**:
   - PES 2026 Author Kit & IEEE Author Center policy explicitly require AI disclosure to be placed in the **Acknowledgment** section (not a standalone Declarations section), identifying the AI tool (OpenAI ChatGPT and Codex) and the specific sections/content it assisted with.
5. **Direct Leadership Address in Cover Letter**:
   - Current TSTE Editor-in-Chief is Professor Hua Geng (Tsinghua University). The Cover Letter must be addressed directly to Prof. Hua Geng, eliminating unsupported narrative certainty and deleting outdated references to 44-page supplementary materials or table counts.

---

## 2. Compliance Refactoring Actions Executed

### Action A: Complete Elimination of Supplementary Citations (100% Self-Contained)
Every citation to "Supplementary Table A...", "Supplementary Section S...", and "Table A..." was purged from `paper_tste_ieee.md`. All quantitative evidence was made self-contained inline:
- **Consequence-Channel Attribution (Table A7b):** Maintained directly inline in Section IV-C: Contemporaneous active power is the dominant mediator ($\text{AUROC} = 0.988$), lagged trajectories and non-power consequence channels retain partial state information, and thermal channels contribute negligible high-frequency boundary information.
- **Privileged Supervision Matched Ablation (Table A6c):** Grounded directly inline with the exact 95% bootstrap confidence interval: $\Delta \text{PSREI} = -312\text{k} \pm 1{,}086\text{k kW}\cdot\text{h}$, 95% CI $[-1.31\text{M}, +0.34\text{M}]$, crossing zero across seeds.
- **Cross-Site External Validity (Table A8):** Compressed into a self-contained empirical synthesis in Section IV-D and Limitations: Penmanshiel saves $-2.14\text{M kW}\cdot\text{h}$ ($p < 0.05$), Kelmarsh 6-turbine array is neutral at $-40\text{k kW}\cdot\text{h}$ ($p=0.85$), and La Haute Borne exhibits a $+43\text{k kW}\cdot\text{h}$ overfitting penalty, confirming that turbine count alone does not explain cross-site variation.
- **PCC Bus-Level Aggregation (Table A11f):** Embedded directly inline in Section IV-D: Spatial smoothing cancels high-frequency turbulence while preserving coherent boundary transition risks.
- **Public Replication Archive:** Extended audit logs and raw experimental records are designated as an open-access reproducibility repository (\url{https://github.com/b1ue13e/windfarm-latent-boundary-risk}), not submission supplementary material.

### Action B: Abstract Compression to 193 Words
The Abstract in `paper_tste_ieee.md` was compressed from 385 words to exactly **193 words**, strictly satisfying the 150–200 word IEEE PES requirement while preserving all required quantitative anchors:
1. Governing question: minimum sufficient model under SCADA observability regimes.
2. Regime 1 (Fresh $\to$ Physics): Boundary band ($|v-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$), $589{,}535\text{ kWh}$ at $h=1$, $881{,}367\text{ kWh}$ at $h=6$, outperforming neural networks by 8.1%.
3. Regime 2 (Stale $\to$ Recalibration): 10–30 min delays, non-neural recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$).
4. Regime 3 (Pitch Unobservable $\to$ Consequence Recovery): Active power $\text{AUROC} = 0.988$; learned representations double transition recall ($0.416$ vs $0.196$) and save $46.7\text{k}\text{--}68.6\text{k kW}\cdot\text{h}$ over unadapted physics.
5. Recoverability $\ne$ Decision Superiority: Wind-speed quantiles remain lower-cost plant-wide; matched-budget evaluations confirm lower violation frequency is offset by deeper residual shortfalls.

### Action C: AI Disclosure Realignment to Acknowledgment
Relocated the disclosure from `# Declarations` to `# Acknowledgment`, naming OpenAI ChatGPT and Codex, specifying assistance with drafting/refining prose across Sections I–VII, formatting IEEE LaTeX macros, and developing automated verification scripts, with full authorial responsibility.

### Action D: Cover Letter & Highlights Professionalization
- Addressed directly to **Professor Hua Geng**, Editor-in-Chief.
- Formulated the **Governing Thesis**:
  > *"The value of model complexity is governed by information sufficiency, while state recoverability and decision superiority remain fundamentally non-equivalent."*
- Formulated the **Two-Level Power Systems Division of Labor**: Level-1 pre-dispatch screening at plant EMS feeds qualified availability bounds into the ISO's Level-2 AC-OPF/SCUC transmission clearing.
- Removed unsupported narrative certainty regarding multi-OEM barriers: framed as "motivated by restricted aggregator access or sensor unavailability".
- Purged "44-page Supplementary Material" and "42 audited tables".
- Replaced "Proves" in Highlights with "Shows/Demonstrates under the evaluated conditions", and corrected MoE claims to "dynamic routing provides no additional decision advantage over matched unrouted representations".

### Action E: Semantic Cleanup in Section IV-C
Replaced *"The targeted utility of machine learning emerges..."* with *"The role of consequence-based state recovery is examined when blade-pitch telemetry is withheld across aggregator boundaries..."* to align perfectly with the falsification finding.

---

## 3. Compliance Verification Checklist

| Compliance Item | Regulatory Requirement | Status in Package | Verification Evidence |
|---|---|:---:|---|
| **Manuscript Page Length** | $\le 10.0$ pages maximum | **PASS** | `build/paper_tste_ieee.pdf` compiles to **9 pages** (0 overfull hboxes). |
| **Supplementary Material** | No supplementary uploaded | **PASS** | 0 supplementary files in submission package; 0 citations in main text. |
| **Abstract Length** | $\approx 150\text{--}200$ words | **PASS** | Exactly **193 words**, fully self-contained. |
| **AI Disclosure** | Located in Acknowledgment | **PASS** | Section `# Acknowledgment` discloses ChatGPT/Codex across Sec. I–VII. |
| **Cover Letter Recipient** | Current EiC Prof. Hua Geng | **PASS** | Explicitly addressed to Prof. Hua Geng (Tsinghua University). |
| **Tone & Claims** | Evidence-grounded, zero overclaims | **PASS** | Governed by dual non-equivalences; no "proves" or "optimal". |
| **Automated Gates** | All scripts exit code 0 | **PASS** | `verify_final_pdf_integrity.py`, `verify_decisive_gate.py`, `verify_scientific_claim_gate.py`, `pytest` all PASS. |

---

## 4. Package Artifacts Overview (`artifacts/tste_submission_freeze_20260923_pes_compliant/`)

- `01_MANUSCRIPT/`: `paper_tste_ieee.pdf` (9 pages, camera-ready), `paper_tste_ieee.md`
- `02_STANDALONE_LATEX_SOURCE/`: `main.tex`, `IEEEtran.cls`, `TUptm.fd`, `references.bib`, and `figures/`
- `03_SUBMISSION_DOCS/`: `Cover_Letter_IEEE_TSTE.md`, `Highlights_and_Keywords.md`, `Data_and_Code_Availability_Statement.md`, `Author_Bio_and_COI.md`
- `04_COMPLIANCE_AND_AUDIT/`: `TSTE_2026_EXTERNAL_COMPLIANCE_REPORT.md`, `TSTE_PEER_REVIEW_ATTACK_SIMULATION.md`, `SCIENTIFIC_CONTRACT_FREEZE.md`, `CLAIM_PRECISION_PATCH_REPORT.md`
- `CHECKSUMS_AND_FILE_MANIFEST.txt`: Full cryptographic SHA256 checksums of all 18 files.
- `artifacts/tste_submission_freeze_20260923_pes_compliant.zip`: Clean 1.58 MB archive ready for direct upload to the IEEE Author Portal.
