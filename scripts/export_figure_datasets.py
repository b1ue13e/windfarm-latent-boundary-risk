"""
export_figure_datasets.py
Extract and standardize all plot datasets for IEEE TSTE paper figures:
- Figure 2: Data & physical regime boundaries (WTB layout, ERA5 mesh, WTB & ERA5 regime scatter)
- Figure 3: Benchmark summary results (WTB & ERA5 model metrics, routing agreement NMI/ARI)
- Figure 4: Routing evidence (binned gate transition curves, confusion matrices)
- Figure 5: Case studies (WTB switch-window time series)
- Figure 6: Ablation trade-off (Pareto frontier of RMSE vs NMI/ARI)
- Gate Stability: Multi-year representation stability (Wasserstein distance & NMI tracking)
Outputs stored in artifacts/origin_data/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from windfarm_moe.data import load_cache_bundle, CacheBundle
from windfarm_moe.paper import _select_run_dir, WTB_CORRECTED_DISPLAY_MODEL
from windfarm_moe.analysis import _load_eval_arrays, _load_confusion_matrix, _sample_indices, _wtb_regime_from_physics

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIGIN_DATA_DIR = ROOT_DIR / "artifacts" / "origin_data"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_mean_std(val_str: object) -> tuple[float, float]:
    text = str(val_str).replace("$\\pm$", "+/-").strip()
    if not text or text.lower() == "nan":
        return np.nan, np.nan
    if "+/-" in text:
        parts = text.split("+/-", 1)
        return float(parts[0].strip()), float(parts[1].strip())
    try:
        return float(text), 0.0
    except ValueError:
        return np.nan, np.nan


def export_figure2_data(wtb_bundle: CacheBundle, era5_bundle: CacheBundle, out_dir: Path) -> None:
    print("Exporting Figure 2 datasets...")
    fig2_dir = ensure_dir(out_dir / "Figure2_Boundary")

    # 1. Panel A: WTB layout coordinates & wake cone parameters
    coords = np.asarray(wtb_bundle.coords, dtype=np.float64)
    source_idx = int(np.argmin(np.linalg.norm(coords - coords.mean(axis=0, keepdims=True), axis=1)))
    max_distance = float(wtb_bundle.metadata["graph_config"]["max_distance"])
    cone_half_angle = float(wtb_bundle.metadata["graph_config"]["cone_half_angle_deg"])
    cone_heading = 18.0

    df_layout = pd.DataFrame({
        "Turbine_ID": np.arange(coords.shape[0]),
        "X_Coord_m": coords[:, 0],
        "Y_Coord_m": coords[:, 1],
        "Is_Source": (np.arange(coords.shape[0]) == source_idx).astype(int),
        "Source_X_m": coords[source_idx, 0],
        "Source_Y_m": coords[source_idx, 1],
        "Max_Distance_m": max_distance,
        "Cone_Half_Angle_deg": cone_half_angle,
        "Cone_Heading_deg": cone_heading,
    })
    df_layout.to_csv(fig2_dir / "fig2a_wtb_layout.csv", index=False)

    # 2. Panel B: ERA5 grid & mean SSHF
    patch_shape = tuple(int(v) for v in era5_bundle.metadata["patch_shape"])
    era_coords = np.asarray(era5_bundle.coords, dtype=np.float64)
    sshf_idx = era5_bundle.metadata["physics_names"].index("sshf")
    
    # Use training split bounds
    num_samples = era5_bundle.features.shape[0]
    train_end = int(num_samples * float(era5_bundle.metadata.get("train_ratio", 0.6)))
    mean_sshf = np.asarray(era5_bundle.physics[:train_end, :, sshf_idx], dtype=np.float64).mean(axis=0) / 1e5

    df_era_grid = pd.DataFrame({
        "Grid_Point_ID": np.arange(era_coords.shape[0]),
        "Latitude": era_coords[:, 0],
        "Longitude": era_coords[:, 1],
        "Mean_SSHF_1e5_J_m2": mean_sshf,
    })
    df_era_grid.to_csv(fig2_dir / "fig2b_era5_mesh.csv", index=False)

    # 3. Panel C: WTB Operating Regimes in (Wspd, Pab_mean)
    test_start = int(wtb_bundle.features.shape[0] * float(wtb_bundle.metadata.get("train_ratio", 0.6) + wtb_bundle.metadata.get("val_ratio", 0.2)))
    wtb_physics = np.asarray(wtb_bundle.physics[test_start:], dtype=np.float64)
    wspd = wtb_physics[..., wtb_bundle.metadata["physics_names"].index("Wspd")].reshape(-1)
    pab = wtb_physics[..., wtb_bundle.metadata["physics_names"].index("Pab_mean")].reshape(-1)
    regime = np.asarray(wtb_bundle.regime_primary[test_start:], dtype=np.int16).reshape(-1)
    
    sample_idx = _sample_indices(regime.size, 15000, seed=42)
    primary_names = list(wtb_bundle.metadata["primary_regime_names"])
    regime_names = [primary_names[r] if 0 <= r < len(primary_names) else "Unknown" for r in regime[sample_idx]]

    df_wtb_regimes = pd.DataFrame({
        "Wind_Speed_m_s": wspd[sample_idx],
        "Pitch_Angle_deg": pab[sample_idx],
        "Regime_ID": regime[sample_idx],
        "Regime_Name": regime_names,
    })
    df_wtb_regimes.to_csv(fig2_dir / "fig2c_wtb_regimes.csv", index=False)

    # 4. Panel D: ERA5 Regimes in (SSHF, Delta_SSHF)
    era_physics = np.asarray(era5_bundle.physics[train_end:], dtype=np.float64)
    sshf = era_physics[..., era5_bundle.metadata["physics_names"].index("sshf")].reshape(-1) / 1e5
    sshf_grad = era_physics[..., era5_bundle.metadata["physics_names"].index("sshf_grad")].reshape(-1) / 1e5
    era_regime = np.asarray(era5_bundle.regime_primary[train_end:], dtype=np.int16).reshape(-1)
    
    sample_idx_era = _sample_indices(era_regime.size, 15000, seed=7)
    era_names = list(era5_bundle.metadata["primary_regime_names"])
    era_regime_names = [era_names[r] if 0 <= r < len(era_names) else "Unknown" for r in era_regime[sample_idx_era]]

    df_era_regimes = pd.DataFrame({
        "SSHF_1e5_J_m2": sshf[sample_idx_era],
        "Delta_SSHF_1e5_J_m2": sshf_grad[sample_idx_era],
        "Regime_ID": era_regime[sample_idx_era],
        "Regime_Name": era_regime_names,
    })
    df_era_regimes.to_csv(fig2_dir / "fig2d_era5_regimes.csv", index=False)


def export_figure3_data(tables_dir: Path, out_dir: Path) -> None:
    print("Exporting Figure 3 datasets...")
    fig3_dir = ensure_dir(out_dir / "Figure3_Summary")

    # 1. Main benchmark table
    main_bench_csv = tables_dir / "table_main_benchmark.csv"
    if main_bench_csv.exists():
        df_bench = pd.read_csv(main_bench_csv)
        wtb_rows = []
        era5_rows = []
        for _, row in df_bench.iterrows():
            panel = str(row.get("Panel", "")).strip()
            model = str(row.get("Model", "")).strip()
            o_mean, o_std = _parse_mean_std(row.get("Overall RMSE"))
            s_mean, s_std = _parse_mean_std(row.get("Switch RMSE"))
            
            entry = {
                "Model": model,
                "Overall_RMSE_Mean": o_mean,
                "Overall_RMSE_Std": o_std,
                "Switch_RMSE_Mean": s_mean,
                "Switch_RMSE_Std": s_std,
            }
            if panel == "WTB":
                p_mean, p_std = _parse_mean_std(row.get("Pitch-control RMSE", row.get("Pitch RMSE", "")))
                entry["PitchControl_RMSE_Mean"] = p_mean
                entry["PitchControl_RMSE_Std"] = p_std
                wtb_rows.append(entry)
            elif panel == "ERA5":
                st_mean, st_std = _parse_mean_std(row.get("Stable-state RMSE", row.get("Stable RMSE", "")))
                entry["StableState_RMSE_Mean"] = st_mean
                entry["StableState_RMSE_Std"] = st_std
                era5_rows.append(entry)
        
        pd.DataFrame(wtb_rows).to_csv(fig3_dir / "fig3a_wtb_benchmark.csv", index=False)
        pd.DataFrame(era5_rows).to_csv(fig3_dir / "fig3b_era5_benchmark.csv", index=False)

    # 2. Routing quality table
    routing_csv = tables_dir / "table_routing_quality.csv"
    if routing_csv.exists():
        df_rout = pd.read_csv(routing_csv)
        rout_rows = []
        for _, row in df_rout.iterrows():
            dataset = str(row.get("Dataset", "")).strip()
            model = str(row.get("Model", "")).strip()
            nmi_mean, nmi_std = _parse_mean_std(row.get("NMI"))
            ari_mean, ari_std = _parse_mean_std(row.get("ARI"))
            rout_rows.append({
                "Dataset": dataset,
                "Model": model,
                "NMI_Mean": nmi_mean,
                "NMI_Std": nmi_std,
                "ARI_Mean": ari_mean,
                "ARI_Std": ari_std,
            })
        pd.DataFrame(rout_rows).to_csv(fig3_dir / "fig3c_routing_agreement.csv", index=False)


def export_figure4_data(wtb_bundle: CacheBundle, corrected_dir: Path, unconstrained_dir: Path, out_dir: Path) -> None:
    print("Exporting Figure 4 datasets...")
    fig4_dir = ensure_dir(out_dir / "Figure4_Routing")

    corrected = _load_eval_arrays(corrected_dir, "test")
    physics_names = list(wtb_bundle.metadata["physics_names"])
    wspd = np.asarray(corrected["anchor_physics"][..., physics_names.index("Wspd")], dtype=np.float64).reshape(-1)
    pab = np.asarray(corrected["anchor_physics"][..., physics_names.index("Pab_mean")], dtype=np.float64).reshape(-1)
    gate_prob = np.asarray(corrected["gate_prob"], dtype=np.float64).reshape(-1, corrected["gate_prob"].shape[-1])

    # 1. Binned gate transition curve
    x_min = 0.0
    x_max = float(np.nanpercentile(wspd, 99.5))
    bins = np.linspace(x_min, x_max, 25)
    centers = 0.5 * (bins[:-1] + bins[1:])
    
    bin_data = {"Wind_Speed_Center_m_s": centers}
    for e in range(gate_prob.shape[-1]):
        means = np.full(centers.shape, np.nan)
        stds = np.full(centers.shape, np.nan)
        for i in range(len(bins) - 1):
            mask = (wspd >= bins[i]) & (wspd < bins[i + 1])
            if mask.sum() >= 50:
                vals = gate_prob[mask, e]
                means[i] = float(np.nanmean(vals))
                stds[i] = float(np.nanstd(vals))
        bin_data[f"Expert_{e+1}_MeanProb"] = means
        bin_data[f"Expert_{e+1}_StdProb"] = stds

    mean_pitch = np.full(centers.shape, np.nan)
    for i in range(len(bins) - 1):
        mask = (wspd >= bins[i]) & (wspd < bins[i + 1])
        if mask.sum() >= 50:
            mean_pitch[i] = float(np.nanmean(pab[mask]))
    bin_data["Mean_Pitch_Angle_deg"] = mean_pitch
    
    pd.DataFrame(bin_data).to_csv(fig4_dir / "fig4a_gate_bins.csv", index=False)

    # 2. Confusion matrices
    conf_labels = ["Idle", "MPPT", "Pitch-control"]
    conf_uncon, _ = _load_confusion_matrix(unconstrained_dir, conf_labels)
    conf_corr, _ = _load_confusion_matrix(corrected_dir, conf_labels)

    df_conf_uncon = pd.DataFrame(conf_uncon, index=conf_labels, columns=[f"Pred_{c}" for c in conf_labels])
    df_conf_uncon.index.name = "Physical_Regime"
    df_conf_uncon.reset_index().to_csv(fig4_dir / "fig4b_confusion_unconstrained.csv", index=False)

    df_conf_corr = pd.DataFrame(conf_corr, index=conf_labels, columns=[f"Pred_{c}" for c in conf_labels])
    df_conf_corr.index.name = "Physical_Regime"
    df_conf_corr.reset_index().to_csv(fig4_dir / "fig4c_confusion_physics_aligned.csv", index=False)


def _safe_load_eval_arrays(run_dir: Path, split: str = "test") -> dict[str, np.ndarray]:
    metrics_dir = run_dir / f"{split}_metrics"
    arrays = {}
    for name in ["pred", "target", "mask", "regime_primary", "regime_primary_valid", "anchor_index", "anchor_physics", "gate_prob"]:
        f = metrics_dir / f"{name}.npy"
        if f.exists():
            arrays[name] = np.load(f)
    return arrays


def export_figure5_data(
    wtb_bundle: CacheBundle,
    dense_dir: Path,
    unconstrained_dir: Path,
    corrected_dir: Path,
    out_dir: Path,
) -> None:
    print("Exporting Figure 5 datasets...")
    fig5_dir = ensure_dir(out_dir / "Figure5_CaseStudies")

    dense = _safe_load_eval_arrays(dense_dir, "test")
    unconstrained = _safe_load_eval_arrays(unconstrained_dir, "test")
    corrected = _safe_load_eval_arrays(corrected_dir, "test")

    anchor_physics = np.asarray(corrected.get("anchor_physics"), dtype=np.float64)
    regime = _wtb_regime_from_physics(anchor_physics[..., 0], anchor_physics[..., 1])
    transition_mask = (regime[:-1] == 1) & (regime[1:] == 2)
    transition_counts = transition_mask.sum(axis=0)
    if int(transition_counts.max()) > 0:
        node_idx = int(np.argmax(transition_counts))
        center = int(np.where(transition_mask[:, node_idx])[0][0] + 1)
    else:
        node_idx = 0
        center = min(regime.shape[0] // 2, regime.shape[0] - 1)
    
    start = max(0, center - 36)
    end = min(regime.shape[0], center + 36)
    steps_per_hour = float(wtb_bundle.metadata.get("steps_per_hour", 6.0))
    x_hours = (np.arange(start, end) - center) / steps_per_hour

    # Target: from corrected array or directly from bundle using anchor_index
    if "target" in corrected:
        truth = np.asarray(corrected["target"][start:end, 0, node_idx], dtype=np.float64)
    else:
        anchor_idx = corrected["anchor_index"][start:end]
        truth = np.asarray(wtb_bundle.target[anchor_idx + 1, node_idx], dtype=np.float64)

    df_traj = pd.DataFrame({
        "Relative_Hours": x_hours,
        "Ground_Truth_kW": truth,
        "Dense_Pred_kW": np.asarray(dense["pred"][start:end, 0, node_idx], dtype=np.float64),
        "Unconstrained_MoE_kW": np.asarray(unconstrained["pred"][start:end, 0, node_idx], dtype=np.float64),
        "Physics_Aligned_MoE_kW": np.asarray(corrected["pred"][start:end, 0, node_idx], dtype=np.float64),
        "Physical_Regime": regime[start:end, node_idx],
        "Wind_Speed_m_s": anchor_physics[start:end, node_idx, 0],
        "Pitch_Angle_deg": anchor_physics[start:end, node_idx, 1],
    })
    df_traj.to_csv(fig5_dir / "fig5_switch_window_timeseries.csv", index=False)


def export_figure6_data(tables_dir: Path, out_dir: Path) -> None:
    print("Exporting Figure 6 datasets...")
    fig6_dir = ensure_dir(out_dir / "Figure6_Ablation")

    ablation_csv = tables_dir / "table_wtb_ablation.csv"
    if not ablation_csv.exists():
        print(f"Warning: {ablation_csv} not found.")
        return

    df_abl = pd.read_csv(ablation_csv)
    rows = []
    for _, row in df_abl.iterrows():
        model = str(row["Model"]).strip()
        if model == "Capacity-Matched Dense Diffusion-GRU":
            continue
        o_mean, o_std = _parse_mean_std(row.get("Overall RMSE"))
        s_mean, s_std = _parse_mean_std(row.get("Switch RMSE"))
        p_mean, p_std = _parse_mean_std(row.get("Pitch-control RMSE"))
        nmi_mean, nmi_std = _parse_mean_std(row.get("NMI"))
        ari_mean, ari_std = _parse_mean_std(row.get("ARI"))
        entropy_mean, entropy_std = _parse_mean_std(row.get("expert_usage_entropy", np.nan))

        rows.append({
            "Model": model,
            "Overall_RMSE_Mean": o_mean,
            "Overall_RMSE_Std": o_std,
            "NMI_Mean": nmi_mean,
            "NMI_Std": nmi_std,
            "ARI_Mean": ari_mean,
            "ARI_Std": ari_std,
            "Switch_RMSE_Mean": s_mean,
            "Switch_RMSE_Std": s_std,
            "PitchControl_RMSE_Mean": p_mean,
            "PitchControl_RMSE_Std": p_std,
            "Entropy_Mean": entropy_mean,
            "Entropy_Std": entropy_std,
        })
    pd.DataFrame(rows).to_csv(fig6_dir / "fig6_ablation_frontier.csv", index=False)


def export_gate_stability_data(out_dir: Path) -> None:
    print("Exporting Gate Stability datasets...")
    stab_dir = ensure_dir(out_dir / "Figure_GateStability")

    raw_csv = ROOT_DIR / "artifacts" / "multiyear_gate_representation_audit" / "gate_representation_decay_raw.csv"
    if not raw_csv.exists():
        print(f"Warning: {raw_csv} not found.")
        return

    df = pd.read_csv(raw_csv)
    for farm in ["kelmarsh", "penmanshiel"]:
        farm_df = df[df["farm"] == farm]
        summary = farm_df.groupby("calendar_year").agg({
            "inverse_wasserstein_pitch": ["mean", "std"],
            "inverse_wasserstein_all": ["mean", "std"],
            "nmi_ground_truth": ["mean", "std"],
        })
        years = summary.index
        out_df = pd.DataFrame({
            "Calendar_Year": years,
            "Inv_Wasserstein_Pitch_Mean": summary[("inverse_wasserstein_pitch", "mean")],
            "Inv_Wasserstein_Pitch_Std": summary[("inverse_wasserstein_pitch", "std")],
            "Inv_Wasserstein_All_Mean": summary[("inverse_wasserstein_all", "mean")],
            "Inv_Wasserstein_All_Std": summary[("inverse_wasserstein_all", "std")],
            "Ground_Truth_NMI_Mean": summary[("nmi_ground_truth", "mean")],
            "Ground_Truth_NMI_Std": summary[("nmi_ground_truth", "std")],
        })
        out_df.to_csv(stab_dir / f"fig_stability_{farm}.csv", index=False)


def main():
    print(f"=== Starting figure dataset extraction to {ORIGIN_DATA_DIR} ===")
    ensure_dir(ORIGIN_DATA_DIR)

    # 1. Load bundles
    wtb_cache_path = ROOT_DIR / "artifacts" / "cache" / "wtb_245d"
    era5_cache_path = ROOT_DIR / "artifacts" / "cache" / "era5_p16_m3"
    
    wtb_bundle = load_cache_bundle(wtb_cache_path)
    era5_bundle = load_cache_bundle(era5_cache_path)

    # 2. Export Figure 2
    export_figure2_data(wtb_bundle, era5_bundle, ORIGIN_DATA_DIR)

    # 3. Export Figure 3
    tables_dir = ROOT_DIR / "artifacts" / "paper_assets" / "tables"
    export_figure3_data(tables_dir, ORIGIN_DATA_DIR)

    # 4. Find key run dirs
    wtb_runs_csv = tables_dir / "wtb_test_aggregated_runs.csv"
    if wtb_runs_csv.exists():
        wtb_df = pd.read_csv(wtb_runs_csv)
        r_uncon = _select_run_dir(wtb_df, "Unconstrained MoE")
        r_corr = _select_run_dir(wtb_df, "MoE + L_bal + L_align + L_force")
        r_dense = _select_run_dir(wtb_df, "Capacity-Matched Dense Diffusion-GRU")

        if r_corr and r_uncon:
            export_figure4_data(wtb_bundle, r_corr, r_uncon, ORIGIN_DATA_DIR)
        
        if r_dense and r_uncon and r_corr:
            export_figure5_data(wtb_bundle, r_dense, r_uncon, r_corr, ORIGIN_DATA_DIR)

    # 5. Export Figure 6
    export_figure6_data(tables_dir, ORIGIN_DATA_DIR)

    # 6. Export Gate Stability
    export_gate_stability_data(ORIGIN_DATA_DIR)

    print("=== Figure dataset extraction complete! ===")


if __name__ == "__main__":
    main()
