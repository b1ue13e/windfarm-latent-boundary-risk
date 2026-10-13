"""Hierarchical and Joint Uncertainty Bootstrap Module for Multi-Seed Time-Series Experiments.

This module resolves Issue 1 & Issue 5 of the scientific evidence audit:
1. Replaces improper arithmetic averaging of per-seed bootstrap CIs/p-values with
   a statistically valid Two-Level Hierarchical Block Bootstrap that simultaneously
   captures Model Training Stochasticity (Seed) and Temporal Block Correlation (Daily Clusters).
2. Computes first-class stability and risk metrics:
   - Joint 95% Bootstrap Confidence Interval
   - Joint Empirical Superiority Probability P(Delta <= 0)
   - Median Paired Difference (robust to single-seed blowups)
   - Seed Failure / Catastrophic Run Rate (percentage of seeds with runaway violation/cost)
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd


def compute_hierarchical_joint_bootstrap(
    seed_block_deltas: Dict[int, np.ndarray],
    seed_block_counts: Optional[Dict[int, np.ndarray]] = None,
    n_boot: int = 2000,
    two_stage_resample: bool = True,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Computes a statistically valid joint bootstrap inference across multiple model seeds

    and time-cluster blocks.

    Args:
        seed_block_deltas: Dict mapping seed -> array of shape (n_blocks,) containing the
            pre-aggregated block-level metric difference (e.g., Challenger Cost - Baseline Cost).
        seed_block_counts: Optional Dict mapping seed -> array of shape (n_blocks,) containing
            valid sample counts per block (for weighted rate calculations).
        n_boot: Number of bootstrap iterations (default: 2000).
        two_stage_resample: If True, performs two-stage resampling:
            Stage 1: Resample time blocks with replacement.
            Stage 2: Resample model seeds with replacement (or average over all seeds under resampled time blocks).
        random_seed: Seed for reproducibility.

    Returns:
        Dict containing:
            - joint_mean: Point estimate of average difference across seeds and time.
            - joint_median: Median difference across seeds.
            - joint_ci_95: [lower, upper] 95% confidence interval covering joint uncertainty.
            - joint_p_non_inferior: Empirical probability P(Joint Delta <= 0). Because the
              compared metrics (PSREI, shortage cost) are COSTS, this is a non-inferiority
              probability, NOT a two-sided p-value: a HIGHER value means the challenger was
              cheaper or equal in that resample. The legacy key
              ``joint_p_val_superiority`` is retained as an alias for callers/tests.
            - seed_estimates: Dict mapping seed -> individual mean difference.
            - catastrophic_run_rate: Fraction of seeds classified as catastrophic runs.
    """
    rng = np.random.default_rng(random_seed)
    seeds = list(seed_block_deltas.keys())
    n_seeds = len(seeds)
    if n_seeds == 0:
        raise ValueError("seed_block_deltas cannot be empty")

    n_blocks = len(seed_block_deltas[seeds[0]])
    for s in seeds:
        if len(seed_block_deltas[s]) != n_blocks:
            raise ValueError(f"Seed {s} has {len(seed_block_deltas[s])} blocks, expected {n_blocks}")

    # Matrix of shape (n_seeds, n_blocks)
    delta_matrix = np.array([seed_block_deltas[s] for s in seeds], dtype=np.float64)

    # Point estimates per seed
    seed_means = delta_matrix.sum(axis=1)  # sum over blocks
    seed_estimates = {seeds[i]: float(seed_means[i]) for i in range(n_seeds)}
    overall_mean = float(np.mean(seed_means))
    overall_median = float(np.median(seed_means))

    # Two-level Hierarchical Bootstrap
    # Block sampling indices: shape (n_boot, n_blocks)
    block_indices = rng.integers(0, n_blocks, size=(n_boot, n_blocks))

    # Compute block sums for each seed under resampled blocks
    # resampled_block_sums shape: (n_boot, n_seeds)
    resampled_block_sums = np.zeros((n_boot, n_seeds), dtype=np.float64)
    for i in range(n_seeds):
        resampled_block_sums[:, i] = delta_matrix[i][block_indices].sum(axis=1)

    if two_stage_resample and n_seeds > 1:
        # Also resample model seeds to reflect epistemic uncertainty over seed draws
        seed_resample_idx = rng.integers(0, n_seeds, size=(n_boot, n_seeds))
        joint_boot_dist = np.take_along_axis(resampled_block_sums, seed_resample_idx, axis=1).mean(axis=1)
    else:
        # Fixed-seed ensemble: average over the fixed set of seeds under block resampling
        joint_boot_dist = resampled_block_sums.mean(axis=1)

    ci_low = float(np.quantile(joint_boot_dist, 0.025))
    ci_high = float(np.quantile(joint_boot_dist, 0.975))
    # P(delta <= 0) for a COST metric: higher => challenger non-inferior (cheaper/equal).
    p_non_inferior = float(np.mean(joint_boot_dist <= 0.0))

    return {
        "joint_mean": overall_mean,
        "joint_median": overall_median,
        "joint_std": float(np.std(seed_means, ddof=1)) if n_seeds > 1 else 0.0,
        "joint_ci_95": [ci_low, ci_high],
        "joint_p_non_inferior": p_non_inferior,
        # Legacy alias (superseded naming; kept so existing callers keep working).
        "joint_p_val_superiority": p_non_inferior,
        "seed_estimates": seed_estimates,
        "n_seeds": n_seeds,
        "n_blocks": n_blocks,
        "boot_samples": joint_boot_dist,
    }


def compute_catastrophic_failure_rate(
    violation_rates_pct: List[float],
    cost_deltas: List[float],
    viol_threshold: float = 15.0,
    cost_sd_multiplier: float = 3.0,
) -> Dict[str, Any]:
    """Calculates the catastrophic run rate across random seeds.

    A run is deemed catastrophic if:
    1. Downstream violation rate explodes (> viol_threshold, default 15% for 10% nominal target)
    2. Or cost penalty exceeds median + cost_sd_multiplier * MAD/IQR.
    """
    n_runs = len(violation_rates_pct)
    if n_runs == 0:
        return {"catastrophic_rate": 0.0, "failed_seeds_count": 0, "n_total": 0}

    viols = np.array(violation_rates_pct)
    costs = np.array(cost_deltas)

    # Violation explosion check
    viol_failures = viols > viol_threshold

    # Cost divergence check (e.g. > 3x typical positive penalty)
    med_cost = np.median(costs)
    mad_cost = np.median(np.abs(costs - med_cost))
    if mad_cost > 0:
        cost_failures = costs > (med_cost + cost_sd_multiplier * (1.4826 * mad_cost))
    else:
        cost_failures = np.zeros(n_runs, dtype=bool)

    combined_failures = viol_failures | cost_failures
    n_failed = int(np.sum(combined_failures))

    return {
        "catastrophic_rate": float(n_failed / n_runs),
        "failed_runs_count": n_failed,
        "total_runs": n_runs,
        "failed_mask": combined_failures.tolist(),
    }
