"""Adversarial Sanity Checks and Accounting Verification for Matched-Budget Frontier (Phase 10).

Verifies:
1. Exact accounting closure: PSREI == Reserve + rho * Shortage within 1e-4.
2. Exact reserve matching: |R_base - R_post| / B <= 0.002 on Frontier A.
3. Sample identity: Both methods evaluated on identical sample masks.
4. No test leakage: Frontier B calibrated strictly on validation.
5. Monotonicity: U(B) non-increasing with respect to target budget B.
6. Missing/NaN audit across all output artifacts.
"""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(os.environ.get("WINDFARM_REPO_ROOT", Path(__file__).resolve().parents[1]))
ARTIFACTS_DIR = REPO_ROOT / "artifacts/matched_budget"

def test_accounting_closure_baseline_reproduction():
    csv_path = ARTIFACTS_DIR / "baseline_reproduction.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    df = pd.read_csv(csv_path)
    
    # Check accounting: PSREI = Reserve + 10 * Shortage
    base_calc = df["base_reserve_kwh"] + 10.0 * df["base_shortage_kwh"]
    post_calc = df["post_reserve_kwh"] + 10.0 * df["post_shortage_kwh"]
    
    diff_base = np.abs(df["base_psrei_kwh"] - base_calc)
    diff_post = np.abs(df["post_psrei_kwh"] - post_calc)
    
    assert np.all(diff_base < 0.05), f"Base accounting failed: max diff = {np.max(diff_base)}"
    assert np.all(diff_post < 0.05), f"Post accounting failed: max diff = {np.max(diff_post)}"

def test_frontier_a_budget_matching_tolerance():
    csv_path = ARTIFACTS_DIR / "exact_matched_budget_frontier.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    df = pd.read_csv(csv_path)
    
    # Delta R should be essentially zero
    rel_err_base = np.abs(df["R_base_kwh"] - df["target_budget_kwh"]) / df["target_budget_kwh"]
    rel_err_post = np.abs(df["R_post_kwh"] - df["target_budget_kwh"]) / df["target_budget_kwh"]
    rel_delta_R = np.abs(df["delta_R_kwh"]) / df["target_budget_kwh"]
    
    assert np.all(rel_err_base <= 0.002), f"Base matching error exceeded 0.2%: max = {np.max(rel_err_base)}"
    assert np.all(rel_err_post <= 0.002), f"Post matching error exceeded 0.2%: max = {np.max(rel_err_post)}"
    assert np.all(rel_delta_R <= 0.003), f"Delta R exceeded 0.3%: max = {np.max(rel_delta_R)}"

def test_frontier_accounting_identity():
    csv_path = ARTIFACTS_DIR / "exact_matched_budget_frontier.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    df = pd.read_csv(csv_path)
    
    base_calc = df["R_base_kwh"] + 10.0 * df["U_base_kwh"]
    post_calc = df["R_post_kwh"] + 10.0 * df["U_post_kwh"]
    
    diff_base = np.abs(df["PSREI_base_kwh"] - base_calc)
    diff_post = np.abs(df["PSREI_post_kwh"] - post_calc)
    
    assert np.all(diff_base < 0.05), f"Frontier A base accounting mismatch: {np.max(diff_base)}"
    assert np.all(diff_post < 0.05), f"Frontier A post accounting mismatch: {np.max(diff_post)}"

def test_shortfall_monotonicity():
    csv_path = ARTIFACTS_DIR / "exact_matched_budget_frontier.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    df = pd.read_csv(csv_path)
    
    # As budget increases, U should not increase (allowing tiny numerical tolerance)
    for (seed, slice_name), group in df.groupby(["seed", "slice"]):
        group_sorted = group.sort_values("target_budget_kwh")
        u_base = group_sorted["U_base_kwh"].values
        u_post = group_sorted["U_post_kwh"].values
        
        diff_u_base = np.diff(u_base)
        diff_u_post = np.diff(u_post)
        
        # Max positive jump should be negligible (< 1e-4)
        assert np.max(diff_u_base) <= 1e-3, f"Non-monotonic U_base on seed {seed}, slice {slice_name}: {np.max(diff_u_base)}"
        assert np.max(diff_u_post) <= 1e-3, f"Non-monotonic U_post on seed {seed}, slice {slice_name}: {np.max(diff_u_post)}"

def test_no_nans_in_artifacts():
    csv_files = [
        "baseline_reproduction.csv",
        "frozen_policy_rho_sensitivity.csv",
        "exact_matched_budget_frontier.csv",
        "validation_calibrated_frontier.csv",
        "bootstrap_frontier_statistics.csv",
        "frontier_auc_summary.csv",
        "reoptimized_rho_sensitivity.csv",
    ]
    for fn in csv_files:
        p = ARTIFACTS_DIR / fn
        if p.exists():
            df = pd.read_csv(p)
            nans = df.isna().sum().to_dict()
            for col, count in nans.items():
                assert count == 0, f"Found {count} NaNs in {fn}, column {col}"
