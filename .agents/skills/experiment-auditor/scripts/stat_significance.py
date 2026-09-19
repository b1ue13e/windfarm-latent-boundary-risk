#!/usr/bin/env python3
"""
stat_significance.py - Top-Tier Conference Statistical Significance & LaTeX Table Generator
Usage:
    python stat_significance.py --ours 0.88 0.89 0.87 0.89 0.88 --baseline 0.81 0.82 0.80 0.83 0.81 --name "OursMethod" --baseline_name "DMD-Net"
"""

import sys
import math
import argparse
from typing import List, Tuple

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def compute_mean_std(data: List[float]) -> Tuple[float, float]:
    n = len(data)
    if n == 0:
        return 0.0, 0.0
    mean = sum(data) / n
    if n == 1:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    std = math.sqrt(variance)
    return mean, std

def paired_t_test(a: List[float], b: List[float]) -> Tuple[float, float]:
    """Calculates paired t-statistic and approximate two-tailed p-value."""
    n = len(a)
    if n != len(b) or n < 2:
        return 0.0, 1.0
    
    diffs = [x - y for x, y in zip(a, b)]
    mean_d, std_d = compute_mean_std(diffs)
    
    if std_d == 0:
        return float("inf"), 0.0
    
    t_stat = mean_d / (std_d / math.sqrt(n))
    df = n - 1
    
    # Approximating two-tailed p-value via rational approximation
    z = abs(t_stat) * (1 - 1 / (4 * df))
    p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))
    p_val = max(1e-6, min(1.0, p_val))
    return t_stat, p_val

def format_latex_row(name: str, mean: float, std: float, is_best: bool, p_val: float = None) -> str:
    val_str = f"{mean:.2f} \\pm {std:.2f}"
    if is_best:
        val_str = f"\\mathbf{{{val_str}}}"
        if p_val is not None:
            if p_val < 0.01:
                val_str += "^{*\\!*}"
            elif p_val < 0.05:
                val_str += "^{*}"
    return f"{name:<20} & {val_str} \\\\"

def main():
    parser = argparse.ArgumentParser(description="Compute TopConf 5-seed statistics and significance.")
    parser.add_argument("--ours", nargs="+", type=float, help="Values from our method (e.g. 5 seeds)")
    parser.add_argument("--baseline", nargs="+", type=float, help="Values from baseline method (e.g. 5 seeds)")
    parser.add_argument("--name", type=str, default="Ours", help="Name of our method")
    parser.add_argument("--baseline_name", type=str, default="Baseline", help="Name of baseline method")
    args = parser.parse_args()

    if not args.ours or not args.baseline:
        print("[Demo Run with 5 Seeds]")
        args.ours = [0.882, 0.891, 0.875, 0.889, 0.884]
        args.baseline = [0.812, 0.825, 0.804, 0.829, 0.818]

    m_ours, s_ours = compute_mean_std(args.ours)
    m_base, s_base = compute_mean_std(args.baseline)

    t_stat, p_val = paired_t_test(args.ours, args.baseline)
    improvement = ((m_ours - m_base) / abs(m_base)) * 100

    print("=" * 65)
    print("TopConf Statistical Rigor & Significance Analysis (5+ Seeds)")
    print("=" * 65)
    print(f"  {args.name:<18}: Mean = {m_ours:.4f}, Std = {s_ours:.4f} (Seeds = {len(args.ours)})")
    print(f"  {args.baseline_name:<18}: Mean = {m_base:.4f}, Std = {s_base:.4f} (Seeds = {len(args.baseline)})")
    print("-" * 65)
    print(f"  Relative Gain     : {improvement:+.2f}%")
    print(f"  Paired t-statistic: {t_stat:.3f}")
    sig_text = "(** p < 0.01)" if p_val < 0.01 else ("(* p < 0.05)" if p_val < 0.05 else "(Not Significant)")
    print(f"  Two-tailed p-value: {p_val:.4e} {sig_text}")
    print("=" * 65)
    print("\nReady-to-use LaTeX Table Rows:")
    print("-" * 65)
    print(format_latex_row(args.baseline_name, m_base, s_base, is_best=False))
    print(format_latex_row(args.name, m_ours, s_ours, is_best=True, p_val=p_val))
    print("-" * 65)
    print("Note: Add '\\textsuperscript{*} $p<0.05$, \\textsuperscript{**} $p<0.01$ (paired t-test)' to caption.")
    print("=" * 65)

if __name__ == "__main__":
    main()

