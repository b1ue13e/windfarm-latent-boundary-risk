#!/usr/bin/env python3
"""One-Command External Replication Verifier (Phase 5).

Validates:
1. Presence of all required Category A and Category B artifacts from ARTIFACT_MANIFEST.json.
2. Cryptographic SHA256 integrity against ARTIFACT_MANIFEST.json.
3. Accounting identities and lightweight table recalculations.
4. Programmatic comparison of reproduced artifact values against headline manuscript claims:
   - C01: Clean Physics h=1 PSREI (589,535 kWh)
   - C02: Clean Physics h=6 PSREI (881,367 kWh)
   - C03: Clean Physics h=6 Violation Rate (6.81%)
   - C04: Missingness-Aware GBDT h=6 Breaches 10% Target (16.23% > 10.0%)
   - C05: Recalibration Shortage Absorption (55.3%)
   - C06: Recalibrated Physics tau=60 Cost (1,228,609 kWh)
   - C07: Uncalibrated Posterior Max ECE <= 5.0% (3.46%)
   - C08: Active Power AUROC (0.988)
   - C09: Transition Recall Gain (0.417 vs 0.196)
   - C10: C2 Active Power Dominant Mechanism Brier Score (0.0112 < 0.05)
   - C11: C4 Thermal Unable to Detect Fast Transitions (Recall 0.0%)
   - C12: Plant-Wide Posterior PSREI Penalty (+523,044 kWh)
   - C13: Transition Interaction Delta (-296,053 kWh, p = 0.002 < 0.01)
   - C14: Accounting Identity C = R + 10 U Closes Numerically (Max Err < 0.05 kWh)
   - C15: Shortage Increases at Matched Budget (+5,234 kWh, 4/5 seeds fail)
   - C16: Absence of Economic Crossover for rho >= 5 (Delta PSREI > 0)
   - C17: Directional Asymmetry (Kelmarsh->Penm 0.770 vs Penm->Kelmarsh 0.341)
   - C18: LHB Micro-Farm Overfitting Boundary Guard (NMI 0.941, ARI 0.971, +43k boundary)
5. Prints a structured PASS/FAIL verdict per quantitative claim.
6. Fails closed (exit code 1) if any claim fails or required evidence is missing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ReplicationAuditor:
    def __init__(self, root: Path, manifest_path: Path):
        self.root = root
        self.manifest_path = manifest_path
        self.claims: list[dict[str, object]] = []
        self.missing_files: list[str] = []
        self.checksum_failures: list[str] = []

    def record_claim(
        self,
        claim_id: str,
        section: str,
        claim_desc: str,
        target_val: float | str,
        actual_val: float | str,
        passed: bool,
        notes: str = "",
    ):
        self.claims.append({
            "claim_id": claim_id,
            "section": section,
            "description": claim_desc,
            "target": target_val,
            "actual": actual_val,
            "passed": passed,
            "notes": notes,
        })
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {claim_id} [{section}]: {claim_desc}")
        print(f"         Target: {target_val} | Replicated: {actual_val} {notes}")

    def verify_manifest_checksums(self) -> bool:
        print("\n--- Step 1: Validating Artifact Manifest & Cryptographic Hashes ---")
        if not self.manifest_path.exists():
            print(f"[FATAL] Manifest not found: {self.manifest_path}")
            return False

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        print(f"Loaded manifest with {len(manifest)} registered artifacts.")

        all_ok = True
        for item in manifest:
            rel = item["filename"]
            expected_sha = item["sha256"]
            cat = item.get("category", "A")
            fp = self.root / rel

            if not fp.exists():
                self.missing_files.append(f"{rel} (Category {cat})")
                print(f"  [MISSING] {rel} (Category {cat})")
                all_ok = False
                continue

            actual_sha = compute_sha256(fp)
            if actual_sha.lower() != expected_sha.lower():
                self.checksum_failures.append(f"{rel}: expected {expected_sha[:12]}, got {actual_sha[:12]}")
                print(f"  [HASH MISMATCH] {rel}")
                all_ok = False

        if all_ok:
            print(f"  [ALL {len(manifest)} ARTIFACTS VERIFIED WITH VALID SHA256]")
        else:
            print(f"  [FAILED] {len(self.missing_files)} missing, {len(self.checksum_failures)} checksum mismatches")
        return all_ok

    def audit_physics_baselines(self):
        print("\n--- Step 2: Auditing Regime 1 Physics Baselines (Table I & II) ---")
        # 1. Clean Physics h=1
        h1_path = self.root / "artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv"
        if h1_path.exists():
            with h1_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                phys_h1 = [
                    float(r["total_cost"])
                    for r in rows
                    if r.get("regime") == "clean" and r.get("model") == "Continuous Physical Quantile"
                ]
                if phys_h1:
                    avg_h1 = sum(phys_h1) / len(phys_h1)
                    # Manuscript states 589,535 kWh (5-seed mean)
                    passed = math.isclose(avg_h1, 589535.0, abs_tol=10.0)
                    self.record_claim("C01", "Regime 1", "Clean Physics h=1 PSREI (5-seed mean)", "589,535 kWh", f"{avg_h1:,.0f} kWh", passed)
                else:
                    self.record_claim("C01", "Regime 1", "Clean Physics h=1 PSREI", "589,535 kWh", "Row not found", False)
        else:
            self.record_claim("C01", "Regime 1", "Clean Physics h=1 PSREI", "589,535 kWh", "Missing artifact", False)

        # 2. Clean Physics h=6
        h6_path = self.root / "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv"
        if h6_path.exists():
            with h6_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                phys_h6 = [
                    float(r["total_cost"])
                    for r in rows
                    if r.get("regime") == "clean" and r.get("model") == "Continuous Physical Quantile"
                ]
                phys_h6_viol = [
                    float(r["violation_rate"])
                    for r in rows
                    if r.get("regime") == "clean" and r.get("model") == "Continuous Physical Quantile"
                ]
                if phys_h6 and phys_h6_viol:
                    avg_h6 = sum(phys_h6) / len(phys_h6)
                    avg_viol = (sum(phys_h6_viol) / len(phys_h6_viol)) * 100
                    passed_cost = math.isclose(avg_h6, 881367.0, abs_tol=10.0)
                    passed_viol = math.isclose(avg_viol, 6.81, abs_tol=0.05)
                    self.record_claim("C02", "Regime 1", "Clean Physics h=6 PSREI (5-seed mean)", "881,367 kWh", f"{avg_h6:,.0f} kWh", passed_cost)
                    self.record_claim("C03", "Regime 1", "Clean Physics h=6 Violation Rate", "6.81%", f"{avg_viol:.2f}%", passed_viol)
                else:
                    self.record_claim("C02", "Regime 1", "Clean Physics h=6", "881,367 kWh", "Rows not found", False)
        else:
            self.record_claim("C02", "Regime 1", "Clean Physics h=6", "881,367 kWh", "Missing artifact", False)

        # 3. Direct Quantile GBDT failure at h=6
        dq_path = self.root / "artifacts/direct_quantile_baselines_summary.csv"
        if dq_path.exists():
            with dq_path.open("r", encoding="utf-8-sig") as f:
                dq_rows = list(csv.DictReader(f))
                gbdt_row = next(
                    (r for r in dq_rows if r.get("condition") == "clean" and r.get("model_id") == "B3_Quantile_GBDT" and str(r.get("horizon_step")) == "6"),
                    None,
                )
                if gbdt_row:
                    viol = float(gbdt_row["violation_rate"])
                    passed = viol > 0.10  # Must breach nominal 10% target (16.23%)
                    self.record_claim("C04", "Regime 1", "Missingness-Aware GBDT h=6 Breaches 10% Target", ">10.0%", f"{viol * 100:.2f}%", passed)
                else:
                    self.record_claim("C04", "Regime 1", "GBDT h=6 Violation", ">10.0%", "Row not found", False)
        else:
            self.record_claim("C04", "Regime 1", "GBDT h=6 Violation", ">10.0%", "Missing artifact", False)

    def audit_recalibration(self):
        print("\n--- Step 3: Auditing Regime 2 Recalibration (Table III & IV) ---")
        ablation_path = self.root / "artifacts/single_task_dense_vs_multitask_moe_ablation.csv"
        if ablation_path.exists():
            with ablation_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                # Delay-6 h=1 physics breakdown: 127.55 MWh clean shortage, 57.07 MWh no-pitch shortage
                d6_all = next((r for r in rows if str(r.get("lag_steps")) == "6" and r.get("channel_mode") == "all"), None)
                d6_nopitch = next((r for r in rows if str(r.get("lag_steps")) == "6" and r.get("channel_mode") == "no_pitch"), None)
                if d6_all and d6_nopitch:
                    phys_clean_shortage = float(d6_all["phys_clean_shortage_mean"])
                    phys_nopitch_shortage = float(d6_nopitch["phys_clean_shortage_mean"])
                    recal_cost = float(d6_all["phys_recal_cost_mean"])
                    absorption = (1.0 - (phys_nopitch_shortage / phys_clean_shortage)) * 100
                    passed_abs = math.isclose(absorption, 55.3, abs_tol=0.5)
                    self.record_claim("C05", "Regime 2", "Recalibration Shortage Absorption", "55.3%", f"{absorption:.1f}%", passed_abs)
                    passed_cost = math.isclose(recal_cost, 1228609.0, abs_tol=10.0)
                    self.record_claim("C06", "Regime 2", "Recalibrated Physics tau=60 Cost", "1,228,609 kWh", f"{recal_cost:,.0f} kWh", passed_cost)
                else:
                    self.record_claim("C05", "Regime 2", "Recalibration absorption", "55.3%", "Missing row in ablation", False)
        else:
            self.record_claim("C05", "Regime 2", "Recalibration absorption", "55.3%", "Missing artifact", False)

        cal_path = self.root / "artifacts/posterior_calibration.csv"
        if cal_path.exists():
            with cal_path.open("r", encoding="utf-8-sig") as f:
                crows = list(csv.DictReader(f))
                max_ece = max(float(r["uncal_ece_mean"]) for r in crows if "uncal_ece_mean" in r)
                passed = max_ece <= 0.05  # ECE <= 5.0%
                self.record_claim("C07", "Regime 2", "Uncalibrated Posterior Max ECE <= 5.0%", "<= 5.0%", f"{max_ece * 100:.2f}%", passed)
        else:
            self.record_claim("C07", "Regime 2", "Posterior Calibration", "<= 5.0%", "Missing artifact", False)

    def audit_latent_boundary_and_channels(self):
        print("\n--- Step 4: Auditing Latent Boundary Recovery & Channel Ablations ---")
        # Active power anchor audit
        ap_path = self.root / "artifacts/active_power_anchor_audit.csv"
        if ap_path.exists():
            with ap_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                ap_rows = [r for r in rows if r.get("condition") == "A_Contemporaneous_Plus_Hist"]
                if ap_rows:
                    aurocs = [float(r["auroc"]) for r in ap_rows]
                    mean_auroc = sum(aurocs) / len(aurocs)
                    passed_auroc = math.isclose(mean_auroc, 0.988, abs_tol=0.005)
                    self.record_claim("C08", "Regime 3", "Active Power AUROC (5-seed mean)", 0.988, round(mean_auroc, 3), passed_auroc)
                else:
                    self.record_claim("C08", "Regime 3", "Active Power AUROC", 0.988, "Row missing", False)
        else:
            self.record_claim("C08", "Regime 3", "Active Power AUROC", 0.988, "Missing artifact", False)

        # Transition recall gain (0.417 vs 0.196)
        fair_path = self.root / "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv"
        if fair_path.exists():
            with fair_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                d6 = next((r for r in rows if r.get("condition") == "delay6"), None)
                if d6:
                    model_rec = float(d6["gate_recall_mean"])
                    rule_rec = float(d6["rule_recall_mean"])
                    passed = math.isclose(model_rec, 0.417, abs_tol=0.01) and math.isclose(rule_rec, 0.196, abs_tol=0.01)
                    self.record_claim("C09", "Regime 3", "Transition Recall Gain (Model vs Rule)", "0.417 vs 0.196", f"{model_rec:.3f} vs {rule_rec:.3f}", passed)
                else:
                    self.record_claim("C09", "Regime 3", "Transition Recall Gain", "0.417 vs 0.196", "Missing row", False)
        else:
            self.record_claim("C09", "Regime 3", "Transition Recall Gain", "0.417 vs 0.196", "Missing artifact", False)

        # C2 vs C4 channel consequence ablations
        ch_path = self.root / "artifacts/channel_consequence_ablations.csv"
        if ch_path.exists():
            with ch_path.open("r", encoding="utf-8-sig") as f:
                crows = list(csv.DictReader(f))
                c2 = next((r for r in crows if r.get("channel_group") == "C2_Active_Power_Only"), None)
                c4 = next((r for r in crows if r.get("channel_group") == "C4_Thermal_Only"), None)
                if c2 and c4:
                    c2_brier = float(c2["brier_score_mean"])
                    c4_recall = float(c4["transition_recall_mean"])
                    p_c2 = c2_brier < 0.05 and math.isclose(c2_brier, 0.0112, abs_tol=0.001)
                    p_c4 = math.isclose(c4_recall, 0.0, abs_tol=0.001)
                    self.record_claim("C10", "Ablations", "C2 Active Power Dominant Mechanism (Brier)", "< 0.05", round(c2_brier, 4), p_c2)
                    self.record_claim("C11", "Ablations", "C4 Thermal Unable to Detect Fast Transitions (Recall)", "0.0%", f"{c4_recall * 100:.1f}%", p_c4)
                else:
                    self.record_claim("C10", "Ablations", "C2 / C4 Consequence Ablations", "Present", "Missing rows", False)
        else:
            self.record_claim("C10", "Ablations", "C2 / C4 Consequence Ablations", "Present", "Missing artifact", False)

    def audit_strong_baseline_closure(self):
        print("\n--- Step 5: Auditing Strong Baseline Closure & Statistical Interaction ---")
        summary_path = self.root / "artifacts/strong_baseline_closure_summary.csv"
        contrasts_path = self.root / "artifacts/strong_baseline_bootstrap_contrasts.csv"

        if summary_path.exists():
            with summary_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                full_b = next((r for r in rows if r.get("population") == "Full" and r.get("policy_id") == "Policy_B"), None)
                full_c = next((r for r in rows if r.get("population") == "Full" and r.get("policy_id") == "Policy_C"), None)
                if full_b and full_c:
                    delta_full = float(full_c["psrei_mean_kwh"]) - float(full_b["psrei_mean_kwh"])
                    passed_delta = math.isclose(delta_full, 523044.0, abs_tol=10.0)
                    self.record_claim("C12", "Strong Baseline", "Plant-Wide Posterior PSREI Penalty (+523,044 kWh)", "+523,044 kWh", f"+{delta_full:,.0f} kWh", passed_delta)
                else:
                    self.record_claim("C12", "Strong Baseline", "Plant-Wide Posterior PSREI Penalty", "+523,044 kWh", "Missing rows", False)
        else:
            self.record_claim("C12", "Strong Baseline", "Plant-Wide Posterior PSREI Penalty", "+523,044 kWh", "Missing artifact", False)

        if contrasts_path.exists():
            with contrasts_path.open("r", encoding="utf-8-sig") as f:
                crows = list(csv.DictReader(f))
                mean_row = next((r for r in crows if r.get("seed") == "Mean"), None)
                if mean_row:
                    diff = float(mean_row["interaction_mean"])
                    pval = float(mean_row["interaction_pval"])
                    passed = math.isclose(diff, -296053.0, abs_tol=10.0) and pval < 0.01
                    self.record_claim("C13", "Strong Baseline", "Transition Interaction Delta (p < 0.01)", "-296,053 kWh (p<0.01)", f"{diff:,.0f} kWh (p={pval:.3f})", passed)
                else:
                    self.record_claim("C13", "Strong Baseline", "Transition Interaction Delta", "< 0", "Mean row not found", False)
        else:
            self.record_claim("C13", "Strong Baseline", "Transition Interaction Delta", "< 0", "Missing artifact", False)

    def audit_matched_budget_and_rho(self):
        print("\n--- Step 6: Auditing Matched-Budget Frontier & Rho Sensitivity ---")
        repro_path = self.root / "artifacts/matched_budget/baseline_reproduction.csv"
        if repro_path.exists():
            with repro_path.open("r", encoding="utf-8-sig") as f:
                rrows = list(csv.DictReader(f))
                all_closed = True
                max_err = 0.0
                for r in rrows:
                    c = float(r["base_psrei_kwh"])
                    res = float(r["base_reserve_kwh"])
                    short = float(r["base_shortage_kwh"])
                    id_err = abs(c - (res + 10.0 * short))
                    if id_err > max_err:
                        max_err = id_err
                    if id_err > 0.05 or r.get("accounting_closed") != "True":
                        all_closed = False
                self.record_claim("C14", "Matched Budget", "Accounting Identity C = R + 10 U Closes Numerically", "Max Err < 0.05 kWh", f"Max Err = {max_err:.4f} kWh", all_closed)
        else:
            self.record_claim("C14", "Matched Budget", "Accounting Identity", "Closed", "Missing artifact", False)

        frontier_auc_path = self.root / "artifacts/matched_budget/frontier_auc_summary.csv"
        if frontier_auc_path.exists():
            with frontier_auc_path.open("r", encoding="utf-8-sig") as f:
                frows = list(csv.DictReader(f))
                trans_rows = [r for r in frows if r.get("slice") == "Transition"]
                deltas = [float(r["mean_delta_U_kwh"]) for r in trans_rows]
                if deltas:
                    mean_delta = sum(deltas) / len(deltas)
                    n_fail = sum(1 for d in deltas if d > 0)
                    # Posterior increases shortage by +5,234 kWh on average; 4 of 5 seeds fail
                    passed_delta = mean_delta > 0 and n_fail == 4
                    self.record_claim("C15", "Matched Budget", "Shortage Increases at Matched Budget (Delta U > 0)", "> 0 kWh (4/5 seeds fail)", f"+{mean_delta:,.1f} kWh ({n_fail}/{len(deltas)} seeds)", passed_delta)
                else:
                    self.record_claim("C15", "Matched Budget", "Shortage Delta at Matched Budget", "> 0 kWh", "No data", False)
        else:
            self.record_claim("C15", "Matched Budget", "Shortage Delta at Matched Budget", "> 0 kWh", "Missing artifact", False)

        rho_path = self.root / "artifacts/matched_budget/reoptimized_rho_sensitivity.csv"
        if rho_path.exists():
            with rho_path.open("r", encoding="utf-8-sig") as f:
                rho_rows = list(csv.DictReader(f))
                # For all rho >= 5 (Transition slice, 5-seed mean), confirm absence of economic crossover (Delta PSREI > 0)
                mean_rows = [
                    r for r in rho_rows
                    if r.get("seed") == "Mean" and float(r.get("rho", 0)) >= 5.0 and r.get("slice") == "Transition"
                ]
                all_no_crossover = all(float(r["delta_PSREI_kwh"]) > 0 for r in mean_rows)
                tested_count = len(mean_rows)
                passed = all_no_crossover and tested_count > 0
                sample_deltas = f"rho=10: +{float(next(r['delta_PSREI_kwh'] for r in mean_rows if float(r['rho'])==10.0)):,.0f} kWh, rho=100: +{float(next(r['delta_PSREI_kwh'] for r in mean_rows if float(r['rho'])==100.0)):,.0f} kWh"
                self.record_claim("C16", "Rho Sensitivity", "Absence of Economic Crossover for rho >= 5 (Transition Mean)", "Delta PSREI > 0 for all rho in [5, 100]", f"{tested_count} conditions positive ({sample_deltas})", passed)
        else:
            self.record_claim("C16", "Rho Sensitivity", "Absence of Economic Crossover", "Verified", "Missing artifact", False)

    def audit_external_sites(self):
        print("\n--- Step 7: Auditing External-Site Transferability & Directional Asymmetry ---")
        run_status_path = self.root / "artifacts/external_wind_guard_windowfix/external_wind_run_status.csv"
        if run_status_path.exists():
            with run_status_path.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
                k_to_p_nmis = [
                    float(r["nmi"])
                    for r in rows
                    if r.get("model") == "Physics-Aligned MoE"
                    and r.get("farm") == "kelmarsh"
                    and r.get("target_farm") == "penmanshiel"
                    and r.get("split_id") == "leave-one-farm-out"
                    and r.get("nmi")
                ]
                p_to_k_nmis = [
                    float(r["nmi"])
                    for r in rows
                    if r.get("model") == "Physics-Aligned MoE"
                    and r.get("farm") == "penmanshiel"
                    and r.get("target_farm") == "kelmarsh"
                    and r.get("split_id") == "leave-one-farm-out"
                    and r.get("nmi")
                ]
                if k_to_p_nmis and p_to_k_nmis:
                    avg_k_to_p = sum(k_to_p_nmis) / len(k_to_p_nmis)
                    avg_p_to_k = sum(p_to_k_nmis) / len(p_to_k_nmis)
                    passed = math.isclose(avg_k_to_p, 0.770, abs_tol=0.01) and math.isclose(avg_p_to_k, 0.341, abs_tol=0.01)
                    self.record_claim("C17", "External Sites", "Directional Asymmetry (Kelmarsh->Penm vs reverse)", "0.770 vs 0.341", f"{avg_k_to_p:.3f} vs {avg_p_to_k:.3f}", passed)
                else:
                    self.record_claim("C17", "External Sites", "Directional Asymmetry", "0.770 vs 0.341", "Missing NMI runs", False)
        else:
            self.record_claim("C17", "External Sites", "Directional Asymmetry", "0.770 vs 0.341", "Missing artifact", False)

        lhb_path = self.root / "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json"
        if lhb_path.exists():
            ldata = json.loads(lhb_path.read_text(encoding="utf-8"))
            nmi = float(ldata.get("mean_nmi", 0))
            ari = float(ldata.get("mean_ari", 0))
            status = ldata.get("status")
            claim_gate = ldata.get("claim_gate")
            passed = (
                math.isclose(nmi, 0.941, abs_tol=0.01)
                and math.isclose(ari, 0.971, abs_tol=0.01)
                and status == "anchor_observable_replication_ready"
                and "passed" in claim_gate
            )
            self.record_claim("C18", "External Sites", "LHB Micro-Farm Overfitting Boundary Guard", "NMI 0.941, ARI 0.971", f"NMI {nmi:.3f}, ARI {ari:.3f} ({claim_gate})", passed)
        else:
            self.record_claim("C18", "External Sites", "LHB Overfitting Penalty", "NMI 0.941, ARI 0.971", "Missing artifact", False)

    def generate_report(self) -> int:
        print("\n" + "=" * 76)
        print("REPLICATION VERIFICATION AUDIT REPORT")
        print("=" * 76)
        total_claims = len(self.claims)
        passed_claims = sum(1 for c in self.claims if c["passed"])
        failed_claims = total_claims - passed_claims

        print(f"\nTotal Headline Claims Evaluated: {total_claims}")
        print(f"Passed: {passed_claims} | Failed: {failed_claims}")

        if self.missing_files:
            print(f"\nMissing Artifacts ({len(self.missing_files)}):")
            for mf in self.missing_files:
                print(f"  - {mf}")

        if self.checksum_failures:
            print(f"\nChecksum Mismatches ({len(self.checksum_failures)}):")
            for cf in self.checksum_failures:
                print(f"  - {cf}")

        if failed_claims == 0 and not self.missing_files and not self.checksum_failures:
            print("\nVERDICT: FULLY_REPRODUCIBLE (ALL 18 CLAIMS VERIFIED WITH EXIT 0)")
            return 0
        else:
            print(f"\nVERDICT: NOT_REPRODUCIBLE ({failed_claims} claims failed, {len(self.missing_files)} missing files)")
            return 1


def main():
    parser = argparse.ArgumentParser(description="End-to-End One-Command Replication Verifier.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root")
    parser.add_argument("--manifest", type=Path, default=None, help="Artifact manifest path")
    args = parser.parse_args()

    manifest_path = args.manifest or (args.root / "artifacts" / "ARTIFACT_MANIFEST.json")
    auditor = ReplicationAuditor(args.root, manifest_path)

    manifest_ok = auditor.verify_manifest_checksums()
    auditor.audit_physics_baselines()
    auditor.audit_recalibration()
    auditor.audit_latent_boundary_and_channels()
    auditor.audit_strong_baseline_closure()
    auditor.audit_matched_budget_and_rho()
    auditor.audit_external_sites()

    exit_code = auditor.generate_report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
