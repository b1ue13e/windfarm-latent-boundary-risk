# Provenance Audit: Elexon BMRS Market Data & Table A12 Sensitivity

**Date**: 2026-09-26  
**Target Table**: Supplementary Table A12 (Panel B) & Table A12b (Annual Breakdown)  
**Dataset**: UK Elexon BMRS Half-Hourly System Buy Prices (2016–2024)  
**Status**: VERIFIED & EPISTEMICALLY BOUNDED  
**Governing Standard**: `docs/SCIENTIFIC_CONTRACT.md`

---

## 1. Executive Summary & Epistemic Ceiling

This audit establishes the exact data provenance, processing pipeline, and methodological boundaries of the multi-year economic evaluation presented in Table A12.

### Strict Claim Ceiling:
1. **What Table A12 Is**:
   A **market-price-weighted economic sensitivity analysis** using 9 years ($N=157,804$ half-hour settlement periods) of historical UK Balancing Mechanism Reporting Service (BMRS) System Buy Prices (SBP). It evaluates how pre-computed physical reserve margins ($r_{i,t}$) and shortfall energy ($s_{i,t}$) translate into financial exposure under real-world price volatility.
2. **What Table A12 Is NOT**:
   - It is **NOT** a physical dispatch simulation.
   - It is **NOT** an active balancing market clearing or unit commitment replay.
   - It does **NOT** observe real-time reserve activations, bids/offers, or transmission constraints.
   - It does **NOT** "prove grid-operational superiority"; it **supports robustness under historical price variation**.

---

## 2. Data Acquisition & Raw Telemetry Provenance

| Parameter | Provenance Record |
| :--- | :--- |
| **Data Provider** | Elexon Ltd. (UK Electricity Market Balancing and Settlement Code Company) |
| **Service Name** | Elexon Insights Solution API (BMRS Modernized Platform) |
| **API Endpoint** | `https://data.elexon.co.uk/bmrs/api/v1/balancing/settlement/system-prices/{date}` |
| **Download Script** | [`scripts/download_elexon_prices.py`](file:///e:/论文3/scripts/download_elexon_prices.py) |
| **Archived File** | `artifacts/elexon_bmrs_imbalance/elexon_system_prices_2016_2024.csv` |
| **Acquisition Date** | September 5, 2026 (UTC) |
| **Date Range** | January 1, 2016 00:00 UTC to December 31, 2024 23:30 UTC (9 full calendar years, 3,288 days) |
| **Queried Variables** | `settlementDate` (YYYY-MM-DD), `settlementPeriod` (integer 1–48), `startTime` (UTC ISO-8601), `systemBuyPrice` (float, GBP/MWh), `systemSellPrice` (float, GBP/MWh), `netImbalanceVolume` (float, MWh), `priceDerivationCode` (string) |

---

## 3. Settlement Period Filtering & Provenance Accounting ($N = 157,804$)

### 3.1 Theoretical Period Count vs. Realized Period Count
- In the UK electricity market, each 24-hour day consists of 48 half-hour settlement periods.
- Over 9 calendar years (2016 through 2024), there are 3 leap years (2016, 2020, 2024: 366 days each) and 6 standard years (365 days each), totaling **3,288 days**.
- Nominal nominal expectation:
  $$3{,}288 \times 48 = 157{,}824 \text{ periods}$$

### 3.2 Clock Changes and Dropouts
1. **Daylight Saving Time (DST)**:
   - Clock springs forward in March (short day, 46 settlement periods: $-2$ periods/yr $\times 9 = -18$ periods).
   - Clock falls back in October (long day, 50 settlement periods: $+2$ periods/yr $\times 9 = +18$ periods).
   - Net annual DST period differential: exactly $0$.
2. **Missing / Unreported BMRS Intervals**:
   - Exactly **20 settlement periods** across the 9-year span were unrecorded or dropped during deduplication:
     $$157{,}824 - 20 = \mathbf{157{,}804} \text{ settlement periods}$$
3. **Completeness**:
   The final dataset contains exactly **157,804 unique `(settlementDate, settlementPeriod)` rows** (99.987% complete).

---

## 4. Price Statistics and Negative Price Treatment

### 4.1 Statistical Distribution (2016–2024)
- **Observations ($N$)**: 157,804 half-hours
- **Mean System Buy Price**: **£77.43 / MWh**
- **Standard Deviation**: £104.28 / MWh
- **Minimum SBP**: **-£185.33 / MWh** (extreme high wind generation / low system demand)
- **Median SBP**: £52.00 / MWh
- **99th Percentile**: £485.00 / MWh
- **Maximum SBP**: **£4,037.80 / MWh** (observed during the November 2021 European energy crisis)

### 4.2 Handling of Negative Prices
- Negative imbalance prices occur when the system operator must pay generators to reduce output or pay consumers to absorb excess energy.
- In `scripts/remote_dynamic_price_settlement_replay.py`:
  - **Raw Settlement**: Evaluates exact unclipped cashflows:
    $$\text{Shortfall Cashflow}(\text{GBP}) = \sum_t s_t \cdot \frac{\Delta t}{1000} \cdot \text{SBP}_t$$
    When SBP is negative, a generation shortfall theoretically earns negative penalty.
  - **Clamped Floor Sensitivity**: Evaluates a conservative robustness check clamping SBP to zero:
    $$\text{Shortfall Floor}(\text{GBP}) = \sum_t s_t \cdot \frac{\Delta t}{1000} \cdot \max(\text{SBP}_t, 0.0)$$
  - **Audit Finding**: Clamping negative prices produces $<0.2\%$ difference in net savings and does not alter the sign or statistical significance of any reported contrast in Table A12.

---

## 5. Mathematical Mapping: From Prices to PSREI Cashflow

### 5.1 Deterministic Reweighting Formulation
The simulation does **NOT** rerun turbine aerodynamics or re-dispatch generation in response to prices. Rather, pre-computed physical reserve procurement ($r_t$, in kW) and realized generation shortfall ($s_t = \max(\hat{y}_t - y_t - r_t, 0)$, in kW) from the frozen models are deterministically reweighted:

1. **Shortfall Energy Exposure**:
   $$\text{Shortage MWh}_t = s_t \cdot \left(\frac{10\text{ min}}{60\text{ min}}\right) \cdot \frac{1}{1000\text{ kW/MW}} = \frac{s_t}{6000}$$
2. **Reserve Capacity Commitment**:
   $$\text{Reserve MWh}_t = r_t \cdot \left(\frac{10\text{ min}}{60\text{ min}}\right) \cdot \frac{1}{1000\text{ kW/MW}} = \frac{r_t}{6000}$$
3. **Cashflow Mapping**:
   $$\text{Cashflow}_t(\text{GBP}) = \text{Reserve MWh}_t \cdot c_r + \text{Shortage MWh}_t \cdot \text{SBP}_t$$
4. **Parameter Mapping ($\rho$)**:
   $$\rho_t = \frac{\text{SBP}_t}{c_r}$$
   To evaluate nominal operational penalty ratios $\rho \in [5, 10, 20]$, $c_r$ is parameterized against the decadal mean price ($\mathbb{E}[\text{SBP}] \approx £77.43/\text{MWh}$):
   - $\rho = 10 \implies c_r \approx £7.74/\text{MWh}$ (nominal benchmark £15.00/MWh evaluated across scaled ratios).

---

## 6. What is Observed vs. What is Unobserved

| Operational Component | Observed in Elexon Dataset? | Methodological Treatment |
| :--- | :---: | :--- |
| **Half-Hourly System Buy Price (SBP)** | **YES** | Exact historical series from Elexon BMRS API |
| **System Sell Price (SSP)** | **YES** | Exact historical series (coincides with SBP under single cashout) |
| **Net Imbalance Volume (NIV)** | **YES** | Recorded for provenance auditing |
| **Actual Wind Farm Reserve Bid / Offer** | **NO** | Not modeled (unobserved) |
| **TSO Balancing Mechanism Acceptance (BOA)** | **NO** | Not modeled (unobserved) |
| **Transmission Line Power Flow / Thermal Limit** | **NO** | Not modeled (unobserved) |
| **Thermal Generator Re-Dispatch / Ramping** | **NO** | Not modeled (unobserved) |

---

## 7. Claim Ceiling & Submission Narrative Alignment

In strict compliance with epistemic consistency:
1. **Permitted Wording**:
   - *"Market-price-weighted economic sensitivity using historical Elexon imbalance prices."*
   - *"Evaluating pre-computed reserve margins against 157,804 settlement periods supports policy robustness under historical price variation."*
2. **Prohibited Wording**:
   - ~~"Real reserve dispatch validation"~~
   - ~~"Balancing-market replay"~~
   - ~~"Market validation"~~
   - ~~"Proves grid-operational superiority"~~
3. **Conclusion**:
   Table A12 is fully preserved as a valuable economic sensitivity check, with its scope strictly bounded to deterministic historical price weighting.
