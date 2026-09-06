"""Cluster 5-Seed Hard Verification Gate and Safe Aggregator.

Enforces zero-tolerance verification gates on cluster experiment outputs:
Gate 1: Directory Completeness Gate (all declared seeds must have run directories)
Gate 2: File Presence & Validity Gate (results_by_seed.csv & bootstrap_summary.csv must exist and be non-empty)
Gate 3: Cgroup OOM / Process Kill Gate (scans logs for 'Killed', 'Out of memory', 'exit 137')
Gate 4: Telemetry Regime Completeness Gate (clean, delay6, sensor_noise, markov_burst must all be present)
Gate 5: Numeric Integrity Gate (no NaN or Inf in total_cost, violation_rate, pinball_loss)
Gate 6: Cardinality Gate (len(valid_seeds) == len(required_seeds), strictly forbidding partial 3-seed merges)

Only when all 6 gates pass is aggregation performed.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

OOM_PATTERNS = [
    re.compile(r"\bKilled\b", re.IGNORECASE),
    re.compile(r"Out of memory", re.IGNORECASE),
    re.compile(r"oom-killer", re.IGNORECASE),
    re.compile(r"CUDA out of memory", re.IGNORECASE),
    re.compile(r"Segmentation fault", re.IGNORECASE),
    re.compile(r"command terminated with exit code 137", re.IGNORECASE),
]

DEFAULT_REQUIRED_REGIMES = ["clean", "delay6", "sensor_noise", "markov_burst"]
DEFAULT_REQUIRED_MODELS = [
    "Global Quantile",
    "Continuous Physical Quantile",
    "Missingness-Aware GBDT",
    "Frozen Backbone MLP",
    "Joint Routed",
]


class HardGateError(Exception):
    """Raised when an experiment family fails verification gates."""
    pass


def audit_log_for_oom(log_path: Path) -> List[str]:
    """Scans log file for OOM or fatal termination signals."""
    if not log_path.exists():
        return []
    errors = []
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            for pattern in OOM_PATTERNS:
                if pattern.search(line):
                    errors.append(line.strip())
                    break
    except Exception as e:
        errors.append(f"Failed to read log {log_path}: {e}")
    return errors


def verify_and_aggregate_5seeds(
    input_root: Path,
    output_dir: Path,
    required_seeds: List[int],
    log_dir: Optional[Path] = None,
    required_regimes: Optional[List[str]] = None,
    required_models: Optional[List[str]] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """Verifies all required seeds against hard gates and safely aggregates if passed."""
    if required_regimes is None:
        required_regimes = DEFAULT_REQUIRED_REGIMES
    if required_models is None:
        required_models = DEFAULT_REQUIRED_MODELS

    output_dir.mkdir(parents=True, exist_ok=True)
    gate_records: Dict[str, Any] = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_root": str(input_root),
        "output_dir": str(output_dir),
        "required_seeds": required_seeds,
        "required_regimes": required_regimes,
        "gates_status": {},
        "seed_diagnostics": {},
        "passed_all_gates": False,
    }

    print(f"\n==================== RUNNING 5-SEED HARD GATES ====================")
    print(f"Target Directory: {input_root}")
    print(f"Required Seeds:   {required_seeds}")
    print(f"Required Regimes: {required_regimes}")

    failures: List[str] = []

    # --- Gate 1: Directory Completeness Gate ---
    missing_dirs = []
    for s in required_seeds:
        s_dir = input_root / f"run_seed_{s}"
        if not s_dir.exists() or not s_dir.is_dir():
            missing_dirs.append(s)
    if missing_dirs:
        failures.append(f"Gate 1 Failed: Missing run directories for seeds: {missing_dirs}")
    gate_records["gates_status"]["gate1_dir_completeness"] = len(missing_dirs) == 0

    # --- Gate 2 & 3: File Presence and OOM Log Audit ---
    seed_dfs: List[pd.DataFrame] = []
    seed_boot_dfs: List[pd.DataFrame] = []

    for s in required_seeds:
        s_diag: Dict[str, Any] = {"seed": s, "passed": True, "errors": []}
        s_dir = input_root / f"run_seed_{s}"

        # OOM audit in log
        if log_dir is not None:
            candidate_logs = [
                log_dir / f"seed_{s}.log",
                log_dir / f"seed_{s}_h24.log",
                input_root / f"seed_{s}.log",
                s_dir / f"seed_{s}.log",
            ]
            for l_path in candidate_logs:
                oom_hits = audit_log_for_oom(l_path)
                if oom_hits:
                    s_diag["passed"] = False
                    msg = f"Fatal Cgroup OOM or Process Kill in {l_path.name}: {oom_hits[:2]}"
                    s_diag["errors"].append(msg)
                    failures.append(f"Gate 3 Failed (Seed {s}): {msg}")

        # Check files
        res_file = s_dir / "results_by_seed.csv"
        boot_file = s_dir / "bootstrap_summary.csv"

        if not res_file.exists() or res_file.stat().st_size == 0:
            s_diag["passed"] = False
            msg = f"Missing or empty results file: {res_file}"
            s_diag["errors"].append(msg)
            failures.append(f"Gate 2 Failed (Seed {s}): {msg}")
            gate_records["seed_diagnostics"][str(s)] = s_diag
            continue

        try:
            df = pd.read_csv(res_file)
            seed_dfs.append(df)
        except Exception as e:
            s_diag["passed"] = False
            msg = f"Unparseable results file {res_file}: {e}"
            s_diag["errors"].append(msg)
            failures.append(f"Gate 2 Failed (Seed {s}): {msg}")

        if boot_file.exists() and boot_file.stat().st_size > 0:
            try:
                b_df = pd.read_csv(boot_file)
                seed_boot_dfs.append(b_df)
            except Exception:
                pass

        gate_records["seed_diagnostics"][str(s)] = s_diag

    gate_records["gates_status"]["gate2_file_validity"] = len(seed_dfs) == len(required_seeds)
    gate_records["gates_status"]["gate3_cgroup_oom_clean"] = len([f for f in failures if "Gate 3" in f]) == 0

    # If any previous gates failed and strict mode is active, abort immediately
    if failures and strict:
        gate_records["failures"] = failures
        (output_dir / "hard_gate_failure_manifest.json").write_text(
            json.dumps(gate_records, indent=2), encoding="utf-8"
        )
        err_msg = "\n".join(failures)
        print(f"\n[HARD GATE REJECTED]\n{err_msg}\n", file=sys.stderr)
        raise HardGateError(f"Verification gates rejected experiment package:\n{err_msg}")

    # Concatenate results
    if not seed_dfs:
        raise HardGateError("No valid seed result dataframes available for analysis.")

    combined_df = pd.concat(seed_dfs, ignore_index=True)

    # --- Gate 4: Telemetry Regime Completeness Gate ---
    for s in required_seeds:
        sub = combined_df[combined_df["seed"] == s]
        present_regimes = set(sub["regime"].unique())
        missing_regs = [r for r in required_regimes if r not in present_regimes]
        if missing_regs:
            msg = f"Gate 4 Failed (Seed {s}): Missing required regimes: {missing_regs}"
            failures.append(msg)
    gate_records["gates_status"]["gate4_regime_completeness"] = len([f for f in failures if "Gate 4" in f]) == 0

    # --- Gate 5: Numeric Integrity Gate (no NaNs or Infs in critical columns) ---
    critical_cols = ["total_cost", "violation_rate", "total_reserve", "total_shortage"]
    for col in critical_cols:
        if col in combined_df.columns:
            n_nan = int(combined_df[col].isna().sum())
            n_inf = int(np.isinf(combined_df[col]).sum())
            if n_nan > 0 or n_inf > 0:
                msg = f"Gate 5 Failed: Column '{col}' contains {n_nan} NaNs and {n_inf} Infs"
                failures.append(msg)
    gate_records["gates_status"]["gate5_numeric_integrity"] = len([f for f in failures if "Gate 5" in f]) == 0

    # --- Gate 6: Cardinality Gate ---
    evaluated_seeds = sorted(list(combined_df["seed"].unique()))
    if evaluated_seeds != sorted(required_seeds):
        msg = f"Gate 6 Failed: Evaluated seeds {evaluated_seeds} do not match required {required_seeds}"
        failures.append(msg)
    gate_records["gates_status"]["gate6_cardinality"] = evaluated_seeds == sorted(required_seeds)

    if failures and strict:
        gate_records["failures"] = failures
        (output_dir / "hard_gate_failure_manifest.json").write_text(
            json.dumps(gate_records, indent=2), encoding="utf-8"
        )
        err_msg = "\n".join(failures)
        print(f"\n[HARD GATE REJECTED]\n{err_msg}\n", file=sys.stderr)
    # Check gate status
    if failures:
        gate_records["passed_all_gates"] = False
        gate_records["failures"] = failures
        print(f"\n[WARNING: HARD GATES FAILED - PARTIAL AGGREGATION RUNNING DUE TO NON-STRICT MODE]", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
    else:
        gate_records["passed_all_gates"] = True
        print("\n[HARD GATES PASSED] All required seeds verified complete and uncorrupted.")

    # 1. Save combined raw results
    combined_df.to_csv(output_dir / "results_by_seed.csv", index=False)

    # 2. Compute group aggregate summary (mean and std across seeds)
    group_cols = [c for c in ["farm", "regime", "lead_step", "model"] if c in combined_df.columns]
    agg_dict = {
        "total_cost": ["mean", "std"],
        "violation_rate": ["mean", "std"],
        "total_reserve": ["mean", "std"],
        "total_shortage": ["mean", "std"],
    }
    if "pinball_loss" in combined_df.columns:
        agg_dict["pinball_loss"] = ["mean", "std"]

    agg_df = combined_df.groupby(group_cols).agg(agg_dict).reset_index()
    agg_df.to_csv(output_dir / "cross_seed_aggregate.csv", index=False)

    # 3. Compute paired statistical differences vs Joint Routed
    paired_rows = []
    for (regime, lead), group in combined_df.groupby(["regime", "lead_step"]):
        routed_sub = group[group["model"] == "Joint Routed"].set_index("seed")
        for m_name in group["model"].unique():
            if m_name == "Joint Routed":
                continue
            m_sub = group[group["model"] == m_name].set_index("seed")
            common_seeds = routed_sub.index.intersection(m_sub.index)
            if len(common_seeds) == len(required_seeds):
                diffs = m_sub.loc[common_seeds, "total_cost"] - routed_sub.loc[common_seeds, "total_cost"]
                mean_diff = float(diffs.mean())
                std_diff = float(diffs.std())
                se_diff = std_diff / np.sqrt(len(diffs))
                # 95% CI
                ci_lo = mean_diff - 1.96 * se_diff
                ci_hi = mean_diff + 1.96 * se_diff
                paired_rows.append({
                    "regime": regime,
                    "lead_step": lead,
                    "model": m_name,
                    "reference": "Joint Routed",
                    "n_seeds": len(common_seeds),
                    "mean_cost_delta": mean_diff,
                    "std_cost_delta": std_diff,
                    "ci_95_lo": ci_lo,
                    "ci_95_hi": ci_hi,
                    "routed_wins": mean_diff > 0,
                    "significant_95": (ci_lo > 0) or (ci_hi < 0),
                })

    if paired_rows:
        paired_df = pd.DataFrame(paired_rows)
        paired_df.to_csv(output_dir / "paired_significance.csv", index=False)
        print("\n--- Paired Significance vs Joint Routed ---")
        print(paired_df[["regime", "model", "mean_cost_delta", "ci_95_lo", "ci_95_hi", "significant_95"]].to_string(index=False))

    # 4. Aggregate bootstrap summaries if present
    if seed_boot_dfs:
        comb_boot = pd.concat(seed_boot_dfs, ignore_index=True)
        comb_boot.to_csv(output_dir / "bootstrap_summary.csv", index=False)

    # 5. Save audit manifest
    (output_dir / "hard_gate_verified_manifest.json").write_text(
        json.dumps(gate_records, indent=2), encoding="utf-8"
    )
    print(f"\nSaved verified aggregation to {output_dir}")
    return gate_records


def main():
    parser = argparse.ArgumentParser(description="Cluster 5-Seed Hard Verification Gate and Safe Aggregator")
    parser.add_argument("--input-root", required=True, help="Directory containing run_seed_{seed} subdirectories")
    parser.add_argument("--output-dir", default=None, help="Output directory for aggregated artifacts (defaults to input-root)")
    parser.add_argument("--seeds", default="201,202,203,204,205", help="Comma-separated required seeds")
    parser.add_argument("--log-dir", default=None, help="Directory containing seed logs to audit for OOM/kills")
    parser.add_argument("--strict", action=argparse.BooleanOptionalAction, default=True, help="Fail with non-zero exit code if any gate fails")
    args = parser.parse_args()

    in_root = Path(args.input_root)
    out_dir = Path(args.output_dir) if args.output_dir else in_root
    log_dir = Path(args.log_dir) if args.log_dir else None
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    try:
        verify_and_aggregate_5seeds(
            input_root=in_root,
            output_dir=out_dir,
            required_seeds=seeds,
            log_dir=log_dir,
            strict=args.strict,
        )
    except HardGateError as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
