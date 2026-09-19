# Final Layout and LaTeX Overflow Audit Report

**Date:** 2026-09-19  
**Status:** ALL GATES PASSED (ZERO OVERFLOWS, ZERO WARNINGS, PES COMPLIANT)  
**Artifacts Audited:**
- Main IEEE Manuscript: `build/paper_tste_ieee.pdf` (from `paper_tste_ieee.md`)
- Supplementary Material: `build/paper_tste_supplementary.pdf` (from `paper_tste_supplementary.md`)

---

## 1. Executive Summary

This audit verifies that the IEEE Transactions on Sustainable Energy (TSTE) submission package satisfies all physical typesetting, layout, and visual compliance constraints without relying on font shrinking, artificial scaling, or unverified approximations.

| Verification Dimension | Standard / Threshold | Main Manuscript Result | Supplementary Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Overfull `\hbox`** | $\le 1.0\text{ pt}$ | **0 (0.00 pt)** | **0 (0.00 pt)** | **PASS** |
| **Overfull `\vbox`** | $\le 1.0\text{ pt}$ | **0 (0.00 pt)** | **0 (0.00 pt)** | **PASS** |
| **`tabularx` Warnings** | 0 warnings | **0 warnings** | **0 warnings** | **PASS** |
| **Page Budget** | $\le 10.0$ pages | **10.0 pages (exact)** | 43 pages (unconstrained) | **PASS** |
| **Minimum Text Font** | $\ge 8.0\text{ pt}$ ($7.97\text{ bp}$) | **$\ge 7.97\text{ bp}$** | $\ge 7.97\text{ bp}$ | **PASS** |
| **Table Body & Header** | $\ge 8.0\text{ pt}$ ($7.97\text{ bp}$) | **$7.97\text{ bp}$** | $7.97\text{ bp}$ | **PASS** |
| **References Font** | $\ge 8.0\text{ pt}$ ($7.97\text{ bp}$) | **$7.97\text{ bp}$** | $7.97\text{ bp}$ | **PASS** |
| **Figure 1 Text Font** | $\ge 8.0\text{ pt}$ ($7.97\text{ bp}$) | **$7.97\text{--}8.77\text{ bp}$** | N/A | **PASS** |
| **Banned Terms** | Zero occurrences | **0 occurrences** | **0 occurrences** | **PASS** |

---

## 2. Main IEEE Manuscript: Layout Overflows & Resolution

### 2.1 Initial Overflows Logged

In initial compilation runs, the following overfull boxes and layout warnings were detected:

1. **Table I (`tab:h6-benchmark`, lines 602--635 in `.tex`):**
   - *Reported Error:* `Overfull \hbox (100.93703pt too wide) in alignment at lines 602--635` and `Package tabularx Warning: X Columns too narrow (table too wide)`.
   - *Root Cause:* Table I was set inside a two-column `tabularx` with unconstrained multi-word headers (`Penalized Reserve Energy (kW*h)`, `Continuous Physical Quantile`, `Missingness-Aware GBDT`). The natural width of the numeric columns exceeded the available width, collapsing the `X` columns to negative or fractional widths and generating a $100.9\text{ pt}$ page-margin intrusion.
   - *Code Fix:* Converted from `tabularx` to `tabular*` spanning full page width `\textwidth` (`\begin{table*}[!t]`), wrapping long headers using multiline `\shortstack` cells (`\shortstack{Penalized Reserve\\Energy (kW$\cdot$h)}`), adjusting inter-column padding with `\setlength{\tabcolsep}{2.0pt}`, and setting `\renewcommand{\arraystretch}{0.90}`. Text font was preserved strictly at `\fontsize{8.0pt}{9.2pt}\selectfont`.
   - *Post-Fix Measurement:* **0.00 pt overflow**; `tabularx` warning eliminated.

2. **Table II (`tab:h6-paired`, lines 650--685 in `.tex`):**
   - *Reported Error:* `Overfull \hbox (29.77092pt too wide) in alignment`.
   - *Root Cause:* Long column titles (`Decision-Relevant Difference`, `95% Day-Block Cluster Bootstrap CI`, `Degraded Recall @ Step 6`) and wide difference strings exceeded column bounds.
   - *Code Fix:* Restructured header using two-tier `\shortstack` blocks (`\shortstack{Operational Hypothesis\\Contrast / Mechanism}`, `\shortstack{$\Delta\text{Reserve Cost}$ (kWh)\\Mean $\pm$ SD}`, `\shortstack{95\% Daily Cluster CI\\(1,000 Resamples)}`); tightened column padding to `1.5pt`.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

3. **Table IV (`tab:cross-farm`, lines 820--850 in `.tex`):**
   - *Reported Error:* `Overfull \hbox (37.84279pt too wide) in alignment`.
   - *Root Cause:* Unwrapped contrast labels and unconstrained baseline descriptions pushed natural table width past `\textwidth`.
   - *Code Fix:* Applied structured `\shortstack[l]` formatting to multi-line cell text and reduced padding to `2.2pt`.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

4. **Equation (2) (`eq:residual-quantile`, lines 480--483 in `.tex`):**
   - *Reported Error:* `Overfull \hbox (4.81372pt too wide) detected at line 483`.
   - *Root Cause:* Inline combination of quantile estimation function and minimization constraint `\hat{r}_{i,t} = \mathrm{MLP}_{\mathrm{res}}([\mathbf{h}_{i,t}; \, \mathbf{x}_{\mathrm{anchor}}]), \quad \text{minimized under } \mathcal{L}_{q^*}(s_{i,t}, \hat{r}_{i,t})` exceeded the single-column width of IEEE style ($\approx 245\text{ pt}$).
   - *Code Fix:* Split into a balanced two-line `aligned` environment:
     ```latex
     \begin{equation}
     \begin{aligned}
     \hat{r}_{i,t} = \mathrm{MLP}_{\mathrm{res}}([\mathbf{h}_{i,t}; \, \mathbf{x}_{\mathrm{anchor}}]), \\
     \text{minimized under } \mathcal{L}_{q^*}(s_{i,t}, \hat{r}_{i,t}),
     \end{aligned}
     \label{eq:residual-quantile}
     \end{equation}
     ```
   - *Post-Fix Measurement:* **0.00 pt overflow**.

5. **Equation (3) (`eq:multi-task-loss`, lines 501--504 in `.tex`):**
   - *Reported Error:* `Overfull \hbox (57.30783pt too wide) detected at line 504`.
   - *Root Cause:* Six multi-task loss terms written on a single line `\mathcal{L} = \mathcal{L}_{\mathrm{pred}} + \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}} + \dots` exceeded the $245\text{ pt}$ column boundary by $57.3\text{ pt}$.
   - *Code Fix:* Split into a two-line `aligned` equation:
     ```latex
     \begin{equation}
     \begin{aligned}
     \mathcal{L} = \mathcal{L}_{\mathrm{pred}} &+ \lambda_{\mathrm{align}}\mathcal{L}_{\mathrm{align}} + \lambda_{\mathrm{aux}}\mathcal{L}_{\mathrm{aux}} \\
     &+ \lambda_{\mathrm{smooth}}\mathcal{L}_{\mathrm{smooth}} + \lambda_{\mathrm{bal}}\mathcal{L}_{\mathrm{bal}} + \lambda_{\mathrm{force}}\mathcal{L}_{\mathrm{force}},
     \end{aligned}
     \label{eq:multi-task-loss}
     \end{equation}
     ```
   - *Post-Fix Measurement:* **0.00 pt overflow**.

---

## 3. Supplementary Material: Layout Overflows & Resolution

### 3.1 Initial Overflows Logged

The initial supplementary compilation produced 97 overfull hboxes and 2 tabularx warnings. Key drivers and fixes:

1. **Table A6c (lines 620--660):**
   - *Reported Error:* `Overfull \hbox (79.52985pt too wide)`.
   - *Root Cause:* Single monolithic table attempting to fit 10 wide columns for both Clean and Degraded regimes across `\textwidth`.
   - *Code Fix:* Split into two vertically stacked panels (Panel A: Nominal Telemetry, Panel B: Delayed Telemetry), each set to `\begin{tabular*}{\textwidth}` with wrapped column titles.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

2. **Table A9b & Table A9c (lines 880--940):**
   - *Reported Error:* `Overfull \hbox (24.71887pt too wide)`.
   - *Root Cause:* Long text strings in the observation condition column exceeding column allocation.
   - *Code Fix:* Converted to `tabularx` with an auto-wrapping `X` column for descriptions (`>{\raggedright\arraybackslash}X`).
   - *Post-Fix Measurement:* **0.00 pt overflow**.

3. **Table A11d (lines 1237--1252):**
   - *Reported Error:* `Overfull \hbox (23.60858pt too wide)`.
   - *Root Cause:* Column 1 ("Continuous pitch quantile (soft-pab)") and Column 8 ("Live physical sensor (Rule)") exceeded natural column widths.
   - *Code Fix:* Shortened headers, wrapped Column 1 strings with `\shortstack[l]`, and combined footprint/governance labels into concise designations.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

4. **Table A11-BESS (lines 1463--1483):**
   - *Reported Error:* `Overfull \hbox (28.07138pt too wide)`.
   - *Root Cause:* Wide Col 1 (`Delay-6 (60 min)`) and Col 2 (`Standalone Wind (No BESS)`, `\textbf{Wind + BESS Rolling MPC}`) strings pushed natural width past `\textwidth`.
   - *Code Fix:* Applied two-line `\shortstack[l]` wrappers to all entries in Col 1 (`\shortstack[l]{Delay-6\\(60 min)}`) and Col 2 (`\shortstack[l]{\textbf{Wind + BESS}\\\textbf{Rolling MPC}}`).
   - *Post-Fix Measurement:* **0.00 pt overflow**.

5. **Table A11-BESSb (lines 1500--1525):**
   - *Reported Error:* `Overfull \hbox (42.1524pt too wide)`.
   - *Root Cause:* Long unconstrained column headers (`Curtailment (MWh)`, `Shortage Mitigation`).
   - *Code Fix:* Wrapped headers with `\shortstack` and tuned `\tabcolsep` to `2.5pt`.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

6. **Figures A11-BESS1 & A11-BESS2 Paragraph Overflows:**
   - *Reported Error:* `Overfull \hbox (15.34007pt too wide) detected at line 1445`.
   - *Root Cause:* Subfigures placed inside a single-column `figure` environment with `0.48\textwidth` widths plus inter-image spacing, exceeding column width.
   - *Code Fix:* Converted both to full-width `figure*` environments with explicit width constraints (`0.92\textwidth` and `0.82\textwidth`).
   - *Post-Fix Measurement:* **0.00 pt overflow**.

7. **Table A11i & Table A12:**
   - *Reported Error:* `Overfull \hbox (18.9102pt too wide)` and `Overfull \hbox (74.20912pt too wide)`.
   - *Root Cause:* Long site names and wide Wasserstein metric headers.
   - *Code Fix:* Wrapped headers, separated Table A12 into Panel A / Panel B, tightened padding.
   - *Post-Fix Measurement:* **0.00 pt overflow**.

---

## 4. Verification Evidence & Automated Log Checks

Automated log inspection script output:

```python
=== build/paper_tste_ieee.log ===
Overfull hboxes (0): []
Tabularx warnings (0): []

=== build/paper_tste_supplementary.log ===
Overfull hboxes (0): []
Tabularx warnings (0): []
```

### Font Size Measurement Audit (PyMuPDF `fitz` extraction):
- Paper Title: `23.91 bp`
- Author Names: `10.96 bp`
- Body Text: `9.96 bp` (exact 10.0 pt)
- Headings: `9.72 bp` (exact 10.0 pt small-caps)
- Figure 1 Text: `7.97 bp`, `8.17 bp`, `8.57 bp`, `8.77 bp` (all $\ge 7.97\text{ bp} = 8.0\text{ pt}$)
- Table 1--4 Body & Headers: `7.97 bp` (exact 8.0 pt)
- References [1]--[30]: `7.97 bp` (exact 8.0 pt)
- Math Subscripts / Superscripts: `5.48 bp`, `5.98 bp`, `6.97 bp`, `7.37 bp` (standard TeX math script/scriptscript sizes)

### Final Layout Verdict:
**ALL LAYOUT GATES PASSED (0.00 pt overflow across entire submission package).**
