# Suggested Additional Experiments and Roadmap for Subsequent Studies
## Target: IEEE Transactions on Sustainable Energy (TSTE)
**Artifact ID**: `09_suggested_additional_experiments.md`  
**Date**: September 2026  

---

## 1. Overview & Prioritization Matrix

To support potential Major Revision requests during the peer review process or guide follow-up research cycles, this document outlines four prioritized experimental expansions.

| Priority | Proposed Campaign | Objective & Scientific Value | Required Resources & Tools | Estimated Feasibility |
|:---:|:---|:---|:---|:---:|
| **P1** | Substation Edge RTU / Microcontroller Benchmark | Measure true C/C++ inference latency and memory on ARM Cortex-M7 / Raspberry Pi CM4 | Embedded toolchain, ONNX Runtime, hardware timer | **High** (1–2 weeks) |
| **P2** | Level-2 Multi-Bus AC-OPF Grid Clearing | Evaluate whether upstream Level-1 PSREI reserve reductions translate into bulk transmission congestion relief | Matpower / pandapower, IEEE 39-bus / 118-bus | **Medium** (2–3 weeks) |
| **P3** | Multi-Year Continuous SCADA Walk-Forward | Expand the Kelmarsh/Penmanshiel multi-year evaluation to 5+ non-overlapping annual folds | Additional historical SCADA archives, GPU compute | **Medium** (2 weeks) |
| **P4** | Co-Simulation with Active Wake Steering (Yaw Control) | Investigate how dynamic yaw offsets alter the directed wake advection graph topology | FLORIS wake simulator, dynamic graph updates | **Long-term** (1–2 months) |

---

## 2. Detailed Experimental Campaign Protocols

### Campaign 1: Embedded Substation Hardware-in-the-Loop Benchmark (Priority 1)
- **Problem**: Reviewers may scrutinize the "sub-5 ms / sub-megabyte" claim as being measured solely on desktop workstations.
- **Protocol**:
  1. Export the trained 110k-parameter STGQ PyTorch model to ONNX and quantized INT8 / FP16 formats.
  2. Flash onto an ARM Cortex-M7 microcontroller (e.g., STM32H7, 480 MHz, 1 MB RAM) and a Raspberry Pi Compute Module 4 (1.5 GHz ARM Cortex-A72).
  3. Feed 10-minute SCADA telemetry frames via serial/Ethernet modbus protocols.
  4. Measure execution wall-clock time, dynamic RAM allocation, and power consumption.
- **Anticipated Outcome**: Verify that inference requires $<15\text{ ms}$ on Cortex-M7 and $<2\text{ ms}$ on CM4, definitively demonstrating edge viability.

---

### Campaign 2: Downstream Level-2 Network-Constrained AC-OPF Co-Simulation (Priority 2)
- **Problem**: Power systems reviewers often ask: *"How do upstream wind plant reserve savings impact downstream nodal marginal prices (LMP) and branch thermal limits?"*
- **Protocol**:
  1. Connect the 134-turbine WTB wind plant to Bus 18 of the IEEE 39-bus New England test system.
  2. Implement a multi-period AC Optimal Power Flow (AC-OPF) solver using `pandapower` or `PyPSA` under 10-minute dispatch steps.
  3. Compare total system balancing generation cost and branch thermal overload incidents when reserves are cleared using:
     (a) Baseline static physical curves;
     (b) State-conditional recalibration;
     (c) Proposed STGQ decoupled residual quantiles.
- **Anticipated Outcome**: Demonstrate that STGQ reserve sizing eliminates transmission line thermal contingency overloads caused by unhedged aerodynamic transition shortfalls.

---

### Campaign 3: Continuous Multi-Year Walk-Forward without Temporal Overlap (Priority 3)
- **Problem**: Address the limitation noted in Supplementary Table A11g regarding two historical rolling folds with partial temporal overlap.
- **Protocol**:
  1. Ingest continuous 5-year SCADA records from Kelmarsh (2016–2020) and Penmanshiel (2016–2020).
  2. Partition strictly into non-overlapping chronological blocks: Year 1–2 (Train/Val), Year 3 (Test), Year 4 (Test), Year 5 (Test).
  3. Audit annual seasonal drift, blade degradation, and sensor recalibration intervals without overlapping validation windows.
- **Anticipated Outcome**: Solidify the empirical proof that periodic two-year recalibration is sufficient to track long-term climatological and sensor drift.
