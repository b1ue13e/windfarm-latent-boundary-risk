"""End-to-End Wind-BESS Rolling MPC Dispatch Simulation Script.

Executes physical battery energy storage system (BESS) rolling-horizon MPC
closed-loop dispatch simulation across the 5 WTB seeds (201--205) under
nominal clean and delayed SCADA telemetry (Delay-0, Delay-1, Delay-3, Delay-6).

Evaluates:
1. Battery capacity & power rating sizing (5--40 MWh)
2. Receding-horizon Model Predictive Control (MPC) with HiGHS LP solver
3. Physical curtailment and shortage mitigation under stale telemetry
4. State of Charge (SoC) dynamics and battery throughput degradation wear
5. Comparative techno-economic savings over unbuffered wind generation
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.decision.bess_rolling_dispatch import (
    BESSConfig,
    DispatchStepResult,
    DispatchTrajectoryResult,
    WindBESSRollingOptimizer,
)
from scripts.eval_farm_aggregate_reserve import aggregate_farm_pcc_causal, resolve_seeds

# Optional plotting
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MATPLOTLIB = True
except ImportError:
    HAVE_MATPLOTLIB = False


DT_HOURS = 1.0 / 6.0  # 10 minutes


def run_simulation_for_seed(
    suite_dir: Path,
    seed: int,
    delays: List[int],
    capacities: List[float],
    c_rate: float = 0.5,
    mpc_lookahead: int = 6,
    default_capacity: float = 20.0,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Runs BESS dispatch simulations for a single random seed across delays and capacities."""
    t_dir = suite_dir / f"wtb_full_seed{seed}" / "test_metrics"
    t_pred = np.load(t_dir / "pred.npy")        # (N, 24, 134) kW
    t_target = np.load(t_dir / "target.npy")    # (N, 24, 134) kW
    t_mask = np.load(t_dir / "mask.npy") > 0.5  # (N, 24, 134) bool

    # 1. Causal farm-level aggregation at PCC bus
    P_pred_causal, P_target, valid_step, _, active_count = aggregate_farm_pcc_causal(
        t_pred, t_target, t_mask, min_active_turbines=50
    )

    # Convert from kW to MW at immediate dispatch horizon (step h=0, 10 min)
    wind_actual_mw = P_target[:, 0] / 1000.0
    wind_forecast_clean_mw = P_pred_causal[:, 0] / 1000.0
    N = len(wind_actual_mw)

    # In case of missing target points, fill with 0.0
    wind_actual_mw = np.nan_to_num(wind_actual_mw, nan=0.0, posinf=0.0, neginf=0.0)
    wind_forecast_clean_mw = np.nan_to_num(wind_forecast_clean_mw, nan=0.0, posinf=0.0, neginf=0.0)

    records: List[Dict[str, Any]] = []
    sample_trajectory_data: Dict[str, Any] = {}

    # 2. Main delay sweep with default capacity (e.g. 20 MWh / 10 MW)
    default_p_rating = default_capacity * c_rate
    cfg_default = BESSConfig(
        capacity_mwh=default_capacity,
        power_rating_mw=default_p_rating,
        dt_hours=DT_HOURS,
    )
    opt_default = WindBESSRollingOptimizer(cfg_default)

    for d in delays:
        delay_mins = d * 10
        # Form delayed commitment and forecast
        if d == 0:
            commit_sched_mw = wind_forecast_clean_mw.copy()
            fc_delayed_mw = wind_forecast_clean_mw.copy()
        else:
            commit_sched_mw = np.empty_like(wind_forecast_clean_mw)
            commit_sched_mw[:d] = wind_forecast_clean_mw[0]
            commit_sched_mw[d:] = wind_forecast_clean_mw[:-d]

            fc_delayed_mw = np.empty_like(wind_forecast_clean_mw)
            fc_delayed_mw[:d] = wind_forecast_clean_mw[0]
            fc_delayed_mw[d:] = wind_forecast_clean_mw[:-d]

        # Mode A: Unbuffered Wind (No BESS)
        diff = wind_actual_mw - commit_sched_mw
        unbuf_shortage_mw = np.maximum(-diff, 0.0)
        unbuf_curtail_mw = np.maximum(diff, 0.0)
        unbuf_shortage_mwh = float(np.sum(unbuf_shortage_mw) * DT_HOURS)
        unbuf_curtail_mwh = float(np.sum(unbuf_curtail_mw) * DT_HOURS)
        unbuf_cost_short = unbuf_shortage_mwh * cfg_default.shortage_penalty_per_mwh
        unbuf_cost_curt = unbuf_curtail_mwh * cfg_default.curtailment_penalty_per_mwh
        unbuf_total_cost = unbuf_cost_short + unbuf_cost_curt
        unbuf_viol_rate = float(np.mean(unbuf_shortage_mw > 1e-4))

        records.append({
            "seed": seed,
            "delay_steps": d,
            "delay_mins": delay_mins,
            "capacity_mwh": 0.0,
            "power_rating_mw": 0.0,
            "dispatch_mode": "unbuffered_wind",
            "total_cost": unbuf_total_cost,
            "cost_shortage": unbuf_cost_short,
            "cost_curtail": unbuf_cost_curt,
            "cost_degradation": 0.0,
            "shortage_mwh": unbuf_shortage_mwh,
            "curtailment_mwh": unbuf_curtail_mwh,
            "bess_throughput_mwh": 0.0,
            "equivalent_full_cycles": 0.0,
            "violation_rate": unbuf_viol_rate,
            "mean_soc": 0.0,
            "min_soc": 0.0,
            "max_soc": 0.0,
            "std_soc": 0.0,
            "cost_savings": 0.0,
            "cost_reduction_pct": 0.0,
            "avoided_shortage_mwh": 0.0,
            "avoided_curtail_mwh": 0.0,
            "shortage_mitigation_pct": 0.0,
        })

        # Mode B: BESS Fast Heuristic
        traj_heur = opt_default.simulate_trajectory(wind_actual_mw, commit_sched_mw, mode="heuristic")
        socs_heur = [r.soc_end for r in traj_heur.step_results]
        heur_savings = unbuf_total_cost - traj_heur.total_cost
        heur_pct = (heur_savings / unbuf_total_cost * 100.0) if unbuf_total_cost > 0 else 0.0
        heur_avoid_short = unbuf_shortage_mwh - traj_heur.shortage_mwh
        heur_avoid_curt = unbuf_curtail_mwh - traj_heur.curtailment_mwh
        heur_short_mit_pct = (heur_avoid_short / unbuf_shortage_mwh * 100.0) if unbuf_shortage_mwh > 0 else 0.0

        records.append({
            "seed": seed,
            "delay_steps": d,
            "delay_mins": delay_mins,
            "capacity_mwh": default_capacity,
            "power_rating_mw": default_p_rating,
            "dispatch_mode": "bess_heuristic",
            "total_cost": traj_heur.total_cost,
            "cost_shortage": traj_heur.cost_shortage,
            "cost_curtail": traj_heur.cost_curtail,
            "cost_degradation": traj_heur.cost_degradation,
            "shortage_mwh": traj_heur.shortage_mwh,
            "curtailment_mwh": traj_heur.curtailment_mwh,
            "bess_throughput_mwh": traj_heur.bess_throughput_mwh,
            "equivalent_full_cycles": traj_heur.equivalent_full_cycles,
            "violation_rate": traj_heur.violation_rate,
            "mean_soc": float(np.mean(socs_heur)),
            "min_soc": float(np.min(socs_heur)),
            "max_soc": float(np.max(socs_heur)),
            "std_soc": float(np.std(socs_heur)),
            "cost_savings": heur_savings,
            "cost_reduction_pct": heur_pct,
            "avoided_shortage_mwh": heur_avoid_short,
            "avoided_curtail_mwh": heur_avoid_curt,
            "shortage_mitigation_pct": heur_short_mit_pct,
        })

        # Mode C: BESS Rolling MPC
        traj_mpc = opt_default.simulate_rolling_mpc(
            wind_actual_mw, fc_delayed_mw, commit_sched_mw, lookahead_steps=mpc_lookahead
        )
        socs_mpc = [r.soc_end for r in traj_mpc.step_results]
        mpc_savings = unbuf_total_cost - traj_mpc.total_cost
        mpc_pct = (mpc_savings / unbuf_total_cost * 100.0) if unbuf_total_cost > 0 else 0.0
        mpc_avoid_short = unbuf_shortage_mwh - traj_mpc.shortage_mwh
        mpc_avoid_curt = unbuf_curtail_mwh - traj_mpc.curtailment_mwh
        mpc_short_mit_pct = (mpc_avoid_short / unbuf_shortage_mwh * 100.0) if unbuf_shortage_mwh > 0 else 0.0

        records.append({
            "seed": seed,
            "delay_steps": d,
            "delay_mins": delay_mins,
            "capacity_mwh": default_capacity,
            "power_rating_mw": default_p_rating,
            "dispatch_mode": "bess_rolling_mpc",
            "total_cost": traj_mpc.total_cost,
            "cost_shortage": traj_mpc.cost_shortage,
            "cost_curtail": traj_mpc.cost_curtail,
            "cost_degradation": traj_mpc.cost_degradation,
            "shortage_mwh": traj_mpc.shortage_mwh,
            "curtailment_mwh": traj_mpc.curtailment_mwh,
            "bess_throughput_mwh": traj_mpc.bess_throughput_mwh,
            "equivalent_full_cycles": traj_mpc.equivalent_full_cycles,
            "violation_rate": traj_mpc.violation_rate,
            "mean_soc": float(np.mean(socs_mpc)),
            "min_soc": float(np.min(socs_mpc)),
            "max_soc": float(np.max(socs_mpc)),
            "std_soc": float(np.std(socs_mpc)),
            "cost_savings": mpc_savings,
            "cost_reduction_pct": mpc_pct,
            "avoided_shortage_mwh": mpc_avoid_short,
            "avoided_curtail_mwh": mpc_avoid_curt,
            "shortage_mitigation_pct": mpc_short_mit_pct,
        })

        # Save trajectory for seed 201 Delay-6 for plotting
        if seed == 201 and d == 6:
            sample_trajectory_data = {
                "wind_actual_mw": [r.p_wind for r in traj_mpc.step_results[:288]], # 48 hours
                "commit_sched_mw": [r.p_commit for r in traj_mpc.step_results[:288]],
                "p_charge_mw": [r.p_charge for r in traj_mpc.step_results[:288]],
                "p_discharge_mw": [r.p_discharge for r in traj_mpc.step_results[:288]],
                "p_shortage_mw": [r.p_shortage for r in traj_mpc.step_results[:288]],
                "p_curtail_mw": [r.p_curtail for r in traj_mpc.step_results[:288]],
                "soc": [r.soc_end for r in traj_mpc.step_results[:288]],
            }

    # 3. Capacity sensitivity sweep under Delay-6 (most severe condition)
    capacity_records: List[Dict[str, Any]] = []
    d6 = 6
    commit_d6 = np.empty_like(wind_forecast_clean_mw)
    commit_d6[:d6] = wind_forecast_clean_mw[0]
    commit_d6[d6:] = wind_forecast_clean_mw[:-d6]
    fc_d6 = commit_d6.copy()

    # Unbuffered reference under Delay-6
    diff_d6 = wind_actual_mw - commit_d6
    unbuf_sh_d6 = float(np.sum(np.maximum(-diff_d6, 0.0)) * DT_HOURS)
    unbuf_cost_d6 = unbuf_sh_d6 * 150.0 + float(np.sum(np.maximum(diff_d6, 0.0)) * DT_HOURS) * 20.0

    for cap in capacities:
        pr = cap * c_rate
        cfg_cap = BESSConfig(capacity_mwh=cap, power_rating_mw=pr, dt_hours=DT_HOURS)
        opt_cap = WindBESSRollingOptimizer(cfg_cap)
        traj_cap = opt_cap.simulate_rolling_mpc(wind_actual_mw, fc_d6, commit_d6, lookahead_steps=mpc_lookahead)
        savings = unbuf_cost_d6 - traj_cap.total_cost
        pct = (savings / unbuf_cost_d6 * 100.0) if unbuf_cost_d6 > 0 else 0.0
        sh_mit = ((unbuf_sh_d6 - traj_cap.shortage_mwh) / unbuf_sh_d6 * 100.0) if unbuf_sh_d6 > 0 else 0.0

        capacity_records.append({
            "seed": seed,
            "delay_steps": 6,
            "capacity_mwh": cap,
            "power_rating_mw": pr,
            "c_rate": c_rate,
            "total_cost": traj_cap.total_cost,
            "shortage_mwh": traj_cap.shortage_mwh,
            "curtailment_mwh": traj_cap.curtailment_mwh,
            "bess_throughput_mwh": traj_cap.bess_throughput_mwh,
            "equivalent_full_cycles": traj_cap.equivalent_full_cycles,
            "violation_rate": traj_cap.violation_rate,
            "mean_soc": traj_cap.mean_soc,
            "cost_savings": savings,
            "cost_reduction_pct": pct,
            "shortage_mitigation_pct": sh_mit,
        })

    return records, capacity_records, sample_trajectory_data


def generate_latex_table(df_summary: pd.DataFrame, out_path: Path) -> None:
    """Generates publication-ready IEEE LaTeX table from simulation summary."""
    lines = [
        r"\begin{table*}[!t]",
        r"\centering",
        r"\fontsize{7.0pt}{8.2pt}\selectfont",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\renewcommand{\arraystretch}{0.90}",
        r"\caption{Wind-BESS Rolling MPC Closed-Loop Dispatch Performance under Telemetry Latency (5 Seeds 201--205, 35-Day Test Split, WTB 134-Turbine Farm, BESS: 20\,MWh / 10\,MW, 0.5C). Values: Mean $\pm$ Standard Deviation.}",
        r"\label{tab:bess-dispatch}",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llcccccc@{}}",
        r"\toprule",
        r"Telemetry Regime & Dispatch Architecture & Total Cost (\$) & Shortage (MWh) & Curtailment (MWh) & Throughput (MWh) & Violation Rate & Shortage Mitigation \\",
        r"\midrule",
    ]

    regime_map = {
        0: "Clean (0 min)",
        1: "Delay-1 (10 min)",
        3: "Delay-3 (30 min)",
        6: "Delay-6 (60 min)",
    }
    mode_map = {
        "unbuffered_wind": "Standalone Wind (No BESS)",
        "bess_heuristic": "Wind + BESS Heuristic",
        "bess_rolling_mpc": r"\textbf{Wind + BESS Rolling MPC}",
    }

    for d in [0, 1, 3, 6]:
        r_label = regime_map[d]
        sub = df_summary[df_summary["delay_steps"] == d]
        first = True
        for m in ["unbuffered_wind", "bess_heuristic", "bess_rolling_mpc"]:
            row = sub[sub["dispatch_mode"] == m]
            if row.empty:
                continue
            r = row.iloc[0]
            m_label = mode_map[m]
            prefix = r_label if first else ""
            first = False

            cost_str = f"${r['total_cost_mean']:,.0f} \\pm {r['total_cost_std']:,.0f}$"
            sh_str = f"${r['shortage_mwh_mean']:,.1f} \\pm {r['shortage_mwh_std']:,.1f}$"
            curt_str = f"${r['curtailment_mwh_mean']:,.1f} \\pm {r['curtailment_mwh_std']:,.1f}$"
            tp_str = f"${r['bess_throughput_mwh_mean']:,.1f} \\pm {r['bess_throughput_mwh_std']:,.1f}$" if r["bess_throughput_mwh_mean"] > 0 else "---"
            viol_str = f"${r['violation_rate_mean']*100:.2f}\\% \\pm {r['violation_rate_std']*100:.2f}\\%$"
            mit_str = f"${r['shortage_mitigation_pct_mean']:.1f}\\% \\pm {r['shortage_mitigation_pct_std']:.1f}\\%$" if m != "unbuffered_wind" else "Baseline"

            lines.append(f"{prefix} & {m_label} & {cost_str} & {sh_str} & {curt_str} & {tp_str} & {viol_str} & {mit_str} \\\\")
        if d != 6:
            lines.append(r"\midrule")

    lines.extend([
        r"\bottomrule",
        r"\multicolumn{8}{@{}p{\textwidth}@{}}{\tiny Evaluated using exact receding-horizon LP optimization via HiGHS with 1-hour lookahead ($H=6$). Because penalty rates are stationary and lookahead commitment gap is zero, rolling LP and step heuristic achieve analytically equivalent step decisions. BESS parameters: 20\,MWh capacity, 10\,MW power rating, 95\% charge/discharge efficiency, 10\%--90\% SoC operating band, \$150/MWh shortage penalty, \$20/MWh curtailment penalty, \$15/MWh throughput degradation wear.}",
        r"\end{tabular*}",
        r"\end{table*}",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")


def plot_figures(sample_traj: Dict[str, Any], df_cap_summary: pd.DataFrame, out_dir: Path) -> None:
    """Generates IEEE TSTE style figures illustrating SoC dynamics and capacity trade-offs."""
    if not HAVE_MATPLOTLIB or not sample_traj:
        return

    # Figure 1: 48-hour SoC dynamics and dispatch trajectory under Delay-6
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True, dpi=300)
    steps = np.arange(len(sample_traj["wind_actual_mw"]))
    hours = steps * (10.0 / 60.0)

    # Panel 1: Power profile
    ax0 = axes[0]
    ax0.plot(hours, sample_traj["wind_actual_mw"], "k-", lw=1.2, label=r"Actual Wind $P_{\mathrm{actual}}$")
    ax0.plot(hours, sample_traj["commit_sched_mw"], "r--", lw=1.0, label=r"Stale Commitment $P_{\mathrm{commit}}$ (Delay-6)")
    ax0.set_ylabel("Power (MW)", fontsize=9)
    ax0.legend(loc="upper right", frameon=True, fontsize=8)
    ax0.grid(True, ls=":", alpha=0.6)
    ax0.set_title("(a) Wind-BESS PCC Dispatch Power Balancing under 6-Step SCADA Latency", fontsize=10, fontweight="bold")

    # Panel 2: Battery Charge / Discharge
    ax1 = axes[1]
    ax1.plot(hours, sample_traj["p_charge_mw"], color="forestgreen", lw=1.0, label=r"BESS Charge $P_{\mathrm{ch}}$ (MW)")
    ax1.plot(hours, sample_traj["p_discharge_mw"], color="darkorange", lw=1.0, label=r"BESS Discharge $P_{\mathrm{dis}}$ (MW)")
    ax1.plot(hours, sample_traj["p_shortage_mw"], color="crimson", lw=0.8, ls="-.", label=r"Remaining Shortage (MW)")
    ax1.set_ylabel("BESS Power (MW)", fontsize=9)
    ax1.legend(loc="upper right", frameon=True, fontsize=8)
    ax1.grid(True, ls=":", alpha=0.6)
    ax1.set_title("(b) BESS Charge/Discharge Action and Residual Imbalance", fontsize=10)

    # Panel 3: Battery SoC
    ax2 = axes[2]
    soc_pct = np.array(sample_traj["soc"]) * 100.0
    ax2.plot(hours, soc_pct, color="royalblue", lw=1.2, label=r"BESS State of Charge (SoC)")
    ax2.axhline(90.0, color="gray", ls="--", lw=0.8, label=r"Upper Bound (90\%)")
    ax2.axhline(10.0, color="gray", ls="--", lw=0.8, label=r"Lower Bound (10\%)")
    ax2.set_ylabel("SoC (%)", fontsize=9)
    ax2.set_xlabel("Time Horizon (Hours)", fontsize=9)
    ax2.set_ylim(0, 100)
    ax2.legend(loc="lower right", frameon=True, fontsize=8)
    ax2.grid(True, ls=":", alpha=0.6)
    ax2.set_title("(c) BESS State of Charge (SoC) Dynamics", fontsize=10)

    plt.tight_layout()
    fig_path = out_dir / "fig_bess_soc_dynamics.png"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"Saved SoC dynamics figure to {fig_path}")

    # Figure 2: Capacity Pareto Sensitivity Curve
    if not df_cap_summary.empty:
        fig, ax1 = plt.subplots(figsize=(7, 4.5), dpi=300)
        caps = df_cap_summary["capacity_mwh"]
        savings = df_cap_summary["cost_savings_mean"] / 1000.0
        mit = df_cap_summary["shortage_mitigation_pct_mean"]
        viol = df_cap_summary["violation_rate_mean"] * 100.0

        color = "tab:blue"
        ax1.set_xlabel("BESS Installed Capacity (MWh) [0.5C Power Rating]", fontsize=10)
        ax1.set_ylabel("Operational Cost Savings (k$)", color=color, fontsize=10)
        ax1.plot(caps, savings, color=color, marker="o", lw=1.5, label="Net Cost Savings (k$)")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.grid(True, ls=":", alpha=0.6)

        ax2 = ax1.twinx()
        color2 = "tab:red"
        ax2.set_ylabel("Shortage Violation Rate (%)", color=color2, fontsize=10)
        ax2.plot(caps, viol, color=color2, marker="s", ls="--", lw=1.5, label="Shortage Violation Rate (%)")
        ax2.tick_params(axis="y", labelcolor=color2)

        plt.title("BESS Sizing Sensitivity and Shortage Mitigation (Delay-6)", fontsize=11, fontweight="bold")
        plt.tight_layout()
        fig_cap_path = out_dir / "fig_bess_capacity_sensitivity.png"
        plt.savefig(fig_cap_path, bbox_inches="tight")
        plt.close()
        print(f"Saved capacity sensitivity figure to {fig_cap_path}")


def main():
    parser = argparse.ArgumentParser(description="Run End-to-End Wind-BESS Rolling MPC Dispatch Simulation.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--suite-dir", default="artifacts/trainweight_full_rerun_20260830", help="Path to seed suite.")
    parser.add_argument("--output-dir", default="artifacts/wind_bess_simulation", help="Output directory.")
    parser.add_argument("--seeds", default="201,202,203,204,205", help="Comma-separated random seeds.")
    parser.add_argument("--delays", default="0,1,3,6", help="Comma-separated delay steps.")
    parser.add_argument("--capacities", default="5,10,20,30,40", help="Comma-separated battery capacities (MWh).")
    parser.add_argument("--c-rate", type=float, default=0.5, help="Battery C-rate (power = cap * c_rate).")
    parser.add_argument("--mpc-lookahead", type=int, default=6, help="MPC lookahead horizon in steps.")
    parser.add_argument("--default-capacity", type=float, default=20.0, help="Default battery capacity (MWh).")
    args = parser.parse_args()

    root = Path(args.repo_root)
    suite = (root / args.suite_dir).resolve()
    out = (root / args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    delays = [int(d.strip()) for d in args.delays.split(",") if d.strip()]
    capacities = [float(c.strip()) for c in args.capacities.split(",") if c.strip()]

    actual_seeds = resolve_seeds(suite, seeds)
    print("==========================================================================")
    print("=== Wind-BESS Rolling MPC Closed-Loop Dispatch Simulation ===")
    print("==========================================================================")
    print(f"Suite Directory:    {suite}")
    print(f"Output Directory:   {out}")
    print(f"Seeds:              {actual_seeds}")
    print(f"Delays (steps):     {delays} (0 to 60 mins)")
    print(f"Capacities (MWh):   {capacities}")
    print(f"Default BESS:       {args.default_capacity} MWh / {args.default_capacity * args.c_rate} MW")
    print(f"MPC Lookahead:      {args.mpc_lookahead} steps (1 hour)")

    all_records: List[Dict[str, Any]] = []
    all_capacity_records: List[Dict[str, Any]] = []
    sample_traj: Dict[str, Any] = {}

    print(f"\nExecuting {len(actual_seeds)} seeds in parallel via ProcessPoolExecutor...", flush=True)
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(actual_seeds), os.cpu_count() or 1)) as executor:
        futures = {
            executor.submit(
                run_simulation_for_seed,
                suite,
                s,
                delays,
                capacities,
                args.c_rate,
                args.mpc_lookahead,
                args.default_capacity,
            ): s
            for s in actual_seeds
        }
        for future in concurrent.futures.as_completed(futures):
            s = futures[future]
            try:
                recs, cap_recs, s_traj = future.result()
                print(f"  [+] Seed {s} finished successfully ({len(recs)} runs).", flush=True)
                all_records.extend(recs)
                all_capacity_records.extend(cap_recs)
                if s_traj and not sample_traj:
                    sample_traj = s_traj
            except Exception as e:
                print(f"  [-] Seed {s} failed with error: {e}", flush=True)
                raise

    # 1. Raw runs per seed
    df_raw = pd.DataFrame(all_records)
    raw_csv = out / "bess_dispatch_raw_by_seed.csv"
    df_raw.to_csv(raw_csv, index=False)
    print(f"\nSaved raw per-seed dispatch records to {raw_csv}")

    # 2. Aggregated summary across 5 seeds
    group_cols = ["delay_steps", "delay_mins", "dispatch_mode", "capacity_mwh", "power_rating_mw"]
    metrics = [
        "total_cost", "cost_shortage", "cost_curtail", "cost_degradation",
        "shortage_mwh", "curtailment_mwh", "bess_throughput_mwh", "equivalent_full_cycles",
        "violation_rate", "mean_soc", "min_soc", "max_soc", "std_soc",
        "cost_savings", "cost_reduction_pct", "avoided_shortage_mwh", "avoided_curtail_mwh",
        "shortage_mitigation_pct"
    ]
    agg_funcs = {m: ["mean", "std"] for m in metrics}
    df_summary = df_raw.groupby(group_cols).agg(agg_funcs).reset_index()
    # Flatten multiindex columns
    df_summary.columns = [
        f"{c[0]}_{c[1]}" if c[1] else c[0] for c in df_summary.columns
    ]
    summary_csv = out / "bess_dispatch_summary.csv"
    df_summary.to_csv(summary_csv, index=False)
    print(f"Saved aggregated summary to {summary_csv}")

    # 3. Capacity sensitivity summary
    df_cap_raw = pd.DataFrame(all_capacity_records)
    cap_group = ["delay_steps", "capacity_mwh", "power_rating_mw", "c_rate"]
    cap_metrics = [
        "total_cost", "shortage_mwh", "curtailment_mwh", "bess_throughput_mwh",
        "equivalent_full_cycles", "violation_rate", "cost_savings", "cost_reduction_pct",
        "shortage_mitigation_pct"
    ]
    df_cap_summary = df_cap_raw.groupby(cap_group).agg({m: ["mean", "std"] for m in cap_metrics}).reset_index()
    df_cap_summary.columns = [
        f"{c[0]}_{c[1]}" if c[1] else c[0] for c in df_cap_summary.columns
    ]
    cap_csv = out / "bess_capacity_sensitivity.csv"
    df_cap_summary.to_csv(cap_csv, index=False)
    print(f"Saved capacity sensitivity summary to {cap_csv}")

    # 4. Generate LaTeX Table
    tex_path = out / "table_bess_dispatch.tex"
    generate_latex_table(df_summary, tex_path)
    print(f"Saved LaTeX table to {tex_path}")

    # 5. Generate Figures
    plot_figures(sample_traj, df_cap_summary, out)

    # 6. Guard JSON for verification
    guard_data = {
        "status": "bess_simulation_completed",
        "seeds": actual_seeds,
        "delays": delays,
        "capacities": capacities,
        "c_rate": args.c_rate,
        "mpc_lookahead": args.mpc_lookahead,
        "default_bess": {
            "capacity_mwh": args.default_capacity,
            "power_rating_mw": args.default_capacity * args.c_rate,
        },
        "highlights_delay6_mpc": {},
    }

    # Extract highlights for Delay-6 Rolling MPC
    row_d6_mpc = df_summary[
        (df_summary["delay_steps"] == 6) & (df_summary["dispatch_mode"] == "bess_rolling_mpc")
    ].iloc[0]
    row_d6_unbuf = df_summary[
        (df_summary["delay_steps"] == 6) & (df_summary["dispatch_mode"] == "unbuffered_wind")
    ].iloc[0]

    guard_data["highlights_delay6_mpc"] = {
        "unbuffered_total_cost": float(row_d6_unbuf["total_cost_mean"]),
        "mpc_total_cost": float(row_d6_mpc["total_cost_mean"]),
        "cost_savings": float(row_d6_mpc["cost_savings_mean"]),
        "cost_reduction_pct": float(row_d6_mpc["cost_reduction_pct_mean"]),
        "unbuffered_violation_rate": float(row_d6_unbuf["violation_rate_mean"]),
        "mpc_violation_rate": float(row_d6_mpc["violation_rate_mean"]),
        "unbuffered_shortage_mwh": float(row_d6_unbuf["shortage_mwh_mean"]),
        "mpc_shortage_mwh": float(row_d6_mpc["shortage_mwh_mean"]),
        "shortage_mitigation_pct": float(row_d6_mpc["shortage_mitigation_pct_mean"]),
        "bess_throughput_mwh": float(row_d6_mpc["bess_throughput_mwh_mean"]),
        "equivalent_full_cycles": float(row_d6_mpc["equivalent_full_cycles_mean"]),
    }

    guard_json = out / "bess_dispatch_guard.json"
    guard_json.write_text(json.dumps(guard_data, indent=2), encoding="utf-8")
    print(f"Saved guard metadata to {guard_json}")

    print("\n==========================================================================")
    print("=== Wind-BESS Delay-6 Operational Mitigation Highlights ===")
    print("==========================================================================")
    print(f"Unbuffered Wind Total Cost:    ${guard_data['highlights_delay6_mpc']['unbuffered_total_cost']:,.0f}")
    print(f"Wind + BESS MPC Total Cost:    ${guard_data['highlights_delay6_mpc']['mpc_total_cost']:,.0f}")
    print(f"Net Operational Savings:       ${guard_data['highlights_delay6_mpc']['cost_savings']:,.0f} ({guard_data['highlights_delay6_mpc']['cost_reduction_pct']:.1f}%)")
    print(f"Shortage Energy Mitigation:    {guard_data['highlights_delay6_mpc']['unbuffered_shortage_mwh']:,.1f} MWh -> {guard_data['highlights_delay6_mpc']['mpc_shortage_mwh']:,.1f} MWh ({guard_data['highlights_delay6_mpc']['shortage_mitigation_pct']:.1f}%)")
    print(f"Violation Rate Reduction:      {guard_data['highlights_delay6_mpc']['unbuffered_violation_rate']*100:.2f}% -> {guard_data['highlights_delay6_mpc']['mpc_violation_rate']*100:.2f}%")
    print(f"BESS 35-Day Energy Throughput: {guard_data['highlights_delay6_mpc']['bess_throughput_mwh']:,.1f} MWh ({guard_data['highlights_delay6_mpc']['equivalent_full_cycles']:.1f} EFC)")


if __name__ == "__main__":
    main()
