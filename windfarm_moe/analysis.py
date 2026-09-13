from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import patches
from matplotlib.colors import BoundaryNorm, ListedColormap
from sklearn.manifold import TSNE

from .data import CacheBundle
from .utils import ensure_dir, load_json, save_json


WTB_CORRECTED_DISPLAY_MODEL = "Boundary-forced router"
WTB_FULL_CORRECTED_SOURCE = "priority2_full_corrected_family"


PAPER_REGIME_COLORS = {
    "idle": "#475569",
    "stable": "#475569",
    "mppt": "#047857",
    "pitch_control": "#D55E00",
    "convective": "#D55E00",
    "transition": "#7E22CE",
}
PAPER_MODEL_COLORS = {
    "Capacity-Matched Dense Diffusion-GRU": "#56B4E9",
    "Unconstrained MoE": "#D97706",
    "Physics-Aligned MoE": "#047857",
    WTB_CORRECTED_DISPLAY_MODEL: "#047857",
    "Graph WaveNet": "#1E3A8A",
    "GAT-GRU": "#0891b2",
    "Graph Transformer": "#7E22CE",
    "PatchTST": "#2563eb",
    "STGCN": "#0f766e",
    "TCN": "#dc2626",
    "Persistence": "#111827",
}
PAPER_EXPERT_COLORS = ["#1E3A8A", "#047857", "#D97706", "#7E22CE"]
FIGURE3_MODEL_COLORS = {
    "Capacity-Matched Dense Diffusion-GRU": "#56B4E9",
    "Unconstrained MoE": "#D97706",
    "Physics-Aligned MoE": "#047857",
    WTB_CORRECTED_DISPLAY_MODEL: "#047857",
    "Graph WaveNet": "#1E3A8A",
    "GAT-GRU": "#0891b2",
    "Graph Transformer": "#7E22CE",
    "PatchTST": "#2563eb",
    "STGCN": "#0f766e",
    "TCN": "#dc2626",
    "Persistence": "#111827",
}


def apply_manuscript_style() -> None:
    sns.set_theme(style="ticks", context="paper")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.titlesize": 7.8,
            "axes.labelsize": 7.0,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.0,
            "legend.title_fontsize": 6.2,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.75,
            "grid.color": "#e5e7eb",
            "grid.linewidth": 0.5,
            "grid.alpha": 0.4,
            "lines.linewidth": 1.3,
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        }
    )


def _style_axis(ax: plt.Axes, *, grid_axis: str = "both") -> None:
    ax.set_facecolor("white")
    ax.grid(True, axis=grid_axis, color="#e5e7eb", linewidth=0.5, alpha=0.35, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333333")
    ax.spines["bottom"].set_color("#333333")
    ax.spines["left"].set_linewidth(0.75)
    ax.spines["bottom"].set_linewidth(0.75)
    ax.tick_params(direction="in", length=3.0, width=0.6)


def _save_figure_variants(fig: plt.Figure, base_path: Path | str, png_dpi: int = 600) -> Path:
    base_path = Path(base_path)
    ensure_dir(base_path.parent)
    pdf_path = base_path.with_suffix(".pdf")
    svg_path = base_path.with_suffix(".svg")
    png_path = base_path.with_suffix(".png")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(svg_path, format="svg", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png_path, format="png", dpi=png_dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return pdf_path


def _split_bounds(bundle: CacheBundle, split: str) -> tuple[int, int]:
    start, end = bundle.metadata["split_bounds"][split]
    return int(start), int(end)


def _sample_indices(size: int, max_points: int, seed: int = 42) -> np.ndarray:
    if size <= max_points:
        return np.arange(size, dtype=np.int64)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(size, size=max_points, replace=False))


def _format_regime_label(name: str) -> str:
    mapping = {
        "idle": "Idle",
        "mppt": "MPPT",
        "pitch_control": "Pitch-control",
        "transition": "Transition",
        "stable": "Stable",
        "convective": "Convective",
    }
    return mapping.get(name, name.replace("_", " ").title())


def _wtb_regime_from_physics(wspd: np.ndarray, pab: np.ndarray) -> np.ndarray:
    regime = np.full(wspd.shape, 3, dtype=np.int16)
    regime[wspd < 3.0] = 0
    regime[(wspd >= 3.0) & (wspd <= 10.5) & (pab < 2.0)] = 1
    regime[(wspd > 10.5) & (pab >= 2.0)] = 2
    return regime


def _mean_by_model(df: pd.DataFrame, model_order: list[str], metric: str) -> list[float]:
    values = []
    for model in model_order:
        model_df = df.loc[df["model"] == model].copy()
        if (
            model == "Physics-Aligned MoE"
            and ("dataset" not in model_df.columns or model_df["dataset"].astype(str).str.lower().eq("wtb").all())
            and "run_dir" in model_df.columns
            and model_df["run_dir"].astype(str).str.contains(WTB_FULL_CORRECTED_SOURCE, case=False, na=False).any()
        ):
            model_df = model_df[
                model_df["run_dir"].astype(str).str.contains(WTB_FULL_CORRECTED_SOURCE, case=False, na=False)
            ].copy()
        subset = pd.to_numeric(model_df[metric], errors="coerce").dropna()
        values.append(float(subset.mean()) if not subset.empty else np.nan)
    return values


def _contiguous_segments(labels: np.ndarray) -> list[tuple[int, int, int]]:
    if labels.size == 0:
        return []
    segments: list[tuple[int, int, int]] = []
    start = 0
    current = int(labels[0])
    for idx in range(1, labels.size):
        value = int(labels[idx])
        if value != current:
            segments.append((start, idx, current))
            start = idx
            current = value
    segments.append((start, labels.size, current))
    return segments


def _load_confusion_matrix(run_dir: Path, labels: list[str]) -> tuple[np.ndarray, list[str]]:
    metrics = load_json(run_dir / "test_metrics" / "metrics.json")
    conf = np.asarray(metrics.get("gate_alignment", {}).get("confusion_matrix", []), dtype=np.int64)
    if conf.size == 0:
        raise RuntimeError(f"No confusion matrix found in {run_dir}.")
    return conf, labels[: conf.shape[0]]


def _load_eval_arrays(run_dir: Path, split: str) -> dict[str, np.ndarray]:
    metrics_dir = run_dir / f"{split}_metrics"
    arrays = {}
    for name in [
        "pred",
        "target",
        "mask",
        "regime_primary",
        "regime_primary_valid",
        "anchor_index",
        "anchor_physics",
        "gate_prob",
        "regime_aux",
        "regime_aux_valid",
    ]:
        p = metrics_dir / f"{name}.npy"
        if p.exists():
            arrays[name] = np.load(p)
    return arrays


def _masked_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    safe_pred = np.nan_to_num(pred.astype(np.float64), nan=0.0)
    safe_target = np.nan_to_num(target.astype(np.float64), nan=0.0)
    weight = mask.astype(np.float64)
    denom = max(weight.sum(), 1.0)
    mae = (np.abs(safe_pred - safe_target) * weight).sum() / denom
    rmse = np.sqrt((((safe_pred - safe_target) ** 2) * weight).sum() / denom)
    return {"mae": float(mae), "rmse": float(rmse)}


def _select_wtb_node(bundle: CacheBundle, requested_turbid: int | None) -> int:
    if requested_turbid is None:
        return 0
    node_ids = bundle.node_ids.astype(int).tolist()
    if requested_turbid in node_ids:
        return node_ids.index(requested_turbid)
    raise ValueError(f"TurbID {requested_turbid} not found in cache.")


def _select_pitch_expert(gate_prob: np.ndarray, regime_primary: np.ndarray) -> int:
    pitch_mask = regime_primary == 2
    if not pitch_mask.any():
        return int(np.argmax(gate_prob.mean(axis=(0, 1))))
    means = []
    for expert_idx in range(gate_prob.shape[-1]):
        expert_values = gate_prob[..., expert_idx][pitch_mask]
        means.append(float(expert_values.mean()) if expert_values.size else -np.inf)
    return int(np.argmax(means))


def _plot_wtb_gate_vs_wspd(
    arrays: dict[str, np.ndarray],
    bundle: CacheBundle,
    output_dir: Path,
    turbid: int | None,
) -> None:
    gate_prob = arrays["gate_prob"]
    node_idx = _select_wtb_node(bundle, turbid)
    expert_idx = _select_pitch_expert(gate_prob, arrays["regime_primary"])
    physics_names = bundle.metadata["physics_names"]
    wspd_idx = physics_names.index("Wspd")
    pab_idx = physics_names.index("Pab_mean")

    wspd = arrays["anchor_physics"][:, node_idx, wspd_idx]
    pab = arrays["anchor_physics"][:, node_idx, pab_idx]
    regime = arrays["regime_primary"][:, node_idx]
    gate = gate_prob[:, node_idx, expert_idx]
    df = pd.DataFrame({"Wspd": wspd, "GateProb": gate, "Pab_avg": pab, "Regime": regime})
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    colors = {0: "#1f77b4", 1: "#2ca02c", 2: "#d62728", 3: "#7f7f7f"}

    fig, ax1 = plt.subplots(figsize=(9, 6))
    sns.scatterplot(
        data=df,
        x="Wspd",
        y="GateProb",
        hue="Regime",
        palette=colors,
        s=14,
        alpha=0.55,
        linewidth=0,
        ax=ax1,
    )
    ax1.set_xlabel("Wind Speed (m/s)")
    ax1.set_ylabel(f"Gate {expert_idx + 1} Probability")
    ax1.set_title("WTB Gate Probability vs Wind Speed with Pitch Overlay")
    ax1.grid(True, alpha=0.25)

    bin_edges = np.linspace(df["Wspd"].min(), df["Wspd"].max(), 25)
    df["Wspd_bin"] = pd.cut(df["Wspd"], bins=bin_edges, include_lowest=True)
    grouped = df.groupby("Wspd_bin", observed=False)["Pab_avg"].median().reset_index()
    grouped["bin_center"] = [interval.mid for interval in grouped["Wspd_bin"]]
    ax2 = ax1.twinx()
    ax2.plot(grouped["bin_center"], grouped["Pab_avg"], color="black", linewidth=2.0, label="Median Pab_avg")
    ax2.set_ylabel("Median Pab_avg (deg)")
    ax2.legend(loc="upper center")
    ax1.legend(title="Op Regime", labels=bundle.metadata["primary_regime_names"], loc="upper left")
    fig.tight_layout()
    fig.savefig(output_dir / "gate_vs_wspd_pab.png", dpi=180)
    plt.close(fig)


def _plot_wtb_timeseries(
    arrays: dict[str, np.ndarray],
    bundle: CacheBundle,
    output_dir: Path,
    turbid: int | None,
) -> None:
    gate_prob = arrays["gate_prob"]
    node_idx = _select_wtb_node(bundle, turbid)
    physics_names = bundle.metadata["physics_names"]
    wspd = arrays["anchor_physics"][:, node_idx, physics_names.index("Wspd")]
    pab = arrays["anchor_physics"][:, node_idx, physics_names.index("Pab_mean")]
    threshold_hits = np.where((wspd[1:] >= 11.0) & (wspd[:-1] < 11.0))[0]
    center = int(threshold_hits[0] + 1) if threshold_hits.size else min(len(wspd) // 2, len(wspd) - 1)
    start = max(0, center - 36)
    end = min(len(wspd), center + 36)
    x = np.arange(start, end)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(x, wspd[start:end], color="tab:blue", label="Wspd")
    axes[0].axhline(11.0, color="gray", linestyle="--", linewidth=1)
    axes[0].set_ylabel("Wspd")
    axes[0].legend(loc="upper left")

    axes[1].plot(x, pab[start:end], color="tab:red", label="Pab_avg")
    axes[1].axhline(2.0, color="gray", linestyle="--", linewidth=1)
    axes[1].set_ylabel("Pab_avg")
    axes[1].legend(loc="upper left")

    for expert_idx in range(gate_prob.shape[-1]):
        axes[2].plot(x, gate_prob[start:end, node_idx, expert_idx], label=f"Expert {expert_idx + 1}")
    axes[2].set_ylabel("Gate prob")
    axes[2].set_xlabel("Anchor time index")
    axes[2].legend(loc="upper right", ncol=2)
    axes[2].grid(True, alpha=0.25)
    fig.suptitle("WTB Regime Switch Window Around Rated Wind Speed")
    fig.tight_layout()
    fig.savefig(output_dir / "wtb_switch_window.png", dpi=180)
    plt.close(fig)


def _plot_era5_flux_vs_gate(arrays: dict[str, np.ndarray], bundle: CacheBundle, output_dir: Path) -> None:
    gate_prob = arrays["gate_prob"]
    physics_names = bundle.metadata["physics_names"]
    flux_idx = physics_names.index("sshf")
    flux = arrays["anchor_physics"][:, :, flux_idx].mean(axis=1)
    window = min(168, flux.shape[0])
    start = 0
    end = window
    x = np.arange(window)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(x, flux[start:end], color="tab:orange", linewidth=1.8)
    axes[0].axhline(0.0, color="gray", linestyle="--", linewidth=1)
    axes[0].set_ylabel("Mean SSHF")
    axes[0].set_title("ERA5 Weekly Sensible Heat Flux vs Expert Weights")
    axes[0].grid(True, alpha=0.25)

    for expert_idx in range(gate_prob.shape[-1]):
        axes[1].plot(x, gate_prob[start:end, :, expert_idx].mean(axis=1), label=f"Expert {expert_idx + 1}")
    zero_cross = np.where(np.signbit(flux[start + 1 : end]) != np.signbit(flux[start:end - 1]))[0] + 1
    for idx in zero_cross:
        axes[1].axvline(idx, color="gray", linestyle=":", alpha=0.35)
    axes[1].set_ylabel("Mean gate prob")
    axes[1].set_xlabel("Hour in selected week")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "flux_vs_gate_week.png", dpi=180)
    plt.close(fig)


def _export_usage_and_entropy(
    arrays: dict[str, np.ndarray],
    bundle: CacheBundle,
    output_dir: Path,
) -> None:
    gate_prob = arrays["gate_prob"]
    usage = gate_prob.mean(axis=(0, 1))
    usage = usage / np.clip(usage.sum(), 1e-12, None)
    regime_names = bundle.metadata["primary_regime_names"]
    num_experts = gate_prob.shape[-1]
    regime_ids = arrays["regime_primary"].reshape(-1)
    gate_flat = gate_prob.reshape(-1, num_experts)
    routing_entropy = -(gate_flat * np.log(np.clip(gate_flat, 1e-12, None))).sum(axis=1)
    entropy_rows = []
    usage_rows = [{"expert": f"expert_{idx + 1}", "usage": float(value)} for idx, value in enumerate(usage)]
    for regime_id, regime_name in enumerate(regime_names):
        selector = regime_ids == regime_id
        if not np.any(selector):
            continue
        regime_gate = gate_flat[selector]
        regime_usage = regime_gate.mean(axis=0)
        regime_usage = regime_usage / np.clip(regime_usage.sum(), 1e-12, None)
        for idx, value in enumerate(regime_usage):
            usage_rows.append(
                {
                    "regime": regime_name,
                    "expert": f"expert_{idx + 1}",
                    "usage": float(value),
                }
            )
        entropy_rows.append(
            {
                "regime": regime_name,
                "mean_entropy": float(routing_entropy[selector].mean()),
                "std_entropy": float(routing_entropy[selector].std()),
            }
        )

    usage_df = pd.DataFrame(usage_rows)
    entropy_df = pd.DataFrame(entropy_rows)
    usage_df.to_csv(output_dir / "expert_usage_by_regime.csv", index=False)
    entropy_df.to_csv(output_dir / "routing_entropy_by_regime.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=usage_df.dropna(subset=["regime"]), x="regime", y="usage", hue="expert", ax=ax)
    ax.set_title("Expert Usage by Physical Regime")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "expert_usage_by_regime.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(data=entropy_df, x="regime", y="mean_entropy", ax=ax, color="#2563eb")
    ax.set_title("Routing Entropy by Physical Regime")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "routing_entropy_by_regime.png", dpi=180)
    plt.close(fig)


def _plot_gate_embedding(
    arrays: dict[str, np.ndarray],
    bundle: CacheBundle,
    output_dir: Path,
    max_points: int = 6000,
) -> None:
    gate_prob = arrays["gate_prob"]
    num_experts = gate_prob.shape[-1]
    gate_flat = gate_prob.reshape(-1, num_experts)
    regime_flat = arrays["regime_primary"].reshape(-1)
    valid = np.isfinite(gate_flat).all(axis=1)
    gate_flat = gate_flat[valid]
    regime_flat = regime_flat[valid]
    if gate_flat.shape[0] == 0:
        return
    if gate_flat.shape[0] > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(gate_flat.shape[0], size=max_points, replace=False)
        gate_flat = gate_flat[idx]
        regime_flat = regime_flat[idx]
    perplexity = max(5, min(30, gate_flat.shape[0] // 20))
    coords = TSNE(n_components=2, init="pca", learning_rate="auto", perplexity=perplexity, random_state=42).fit_transform(gate_flat)
    df = pd.DataFrame({"x": coords[:, 0], "y": coords[:, 1], "regime": regime_flat})
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.scatterplot(data=df, x="x", y="y", hue="regime", palette="tab10", s=16, linewidth=0, alpha=0.65, ax=ax)
    ax.set_title("Gate Embedding Projection")
    ax.set_xlabel("t-SNE 1")
    ax.set_ylabel("t-SNE 2")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_dir / "gate_embedding_tsne.png", dpi=180)
    plt.close(fig)


def _compare_runs(
    run_arrays: dict[str, np.ndarray],
    baseline_arrays: dict[str, np.ndarray],
    bundle: CacheBundle,
    output_dir: Path,
) -> None:
    primary_names = bundle.metadata["primary_regime_names"]
    switch_window = 3 * int(bundle.metadata.get("steps_per_hour", 6))
    comparisons = []
    for name, arrays in [("moe", run_arrays), ("dense", baseline_arrays)]:
        comparisons.append({"model": name, "slice": "overall", **_masked_metrics(arrays["pred"], arrays["target"], arrays["mask"])})
        for regime_id, regime_name in enumerate(primary_names):
            regime_mask = arrays["mask"] * (arrays["regime_primary"] == regime_id)[:, None, :]
            comparisons.append({"model": name, "slice": regime_name, **_masked_metrics(arrays["pred"], arrays["target"], regime_mask)})
        switch_selector = np.zeros_like(arrays["regime_primary"], dtype=bool)
        if arrays["regime_primary"].shape[0] > 1:
            changes = arrays["regime_primary"][1:] != arrays["regime_primary"][:-1]
            rows, nodes = np.where(changes)
            for row, node in zip(rows, nodes):
                lo = max(0, row + 1 - switch_window)
                hi = min(arrays["regime_primary"].shape[0], row + 2 + switch_window)
                switch_selector[lo:hi, node] = True
        comparisons.append(
            {
                "model": name,
                "slice": "switch_window",
                **_masked_metrics(arrays["pred"], arrays["target"], arrays["mask"] * switch_selector[:, None, :]),
            }
        )
    df = pd.DataFrame(comparisons)
    df.to_csv(output_dir / "dense_vs_moe_regime_comparison.csv", index=False)
    save_json(output_dir / "dense_vs_moe_regime_comparison.json", {"rows": df.to_dict(orient="records")})

    plot_df = df[df["slice"].isin(["overall", "switch_window"])]
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=plot_df, x="slice", y="rmse", hue="model", ax=ax)
    ax.set_title("Dense vs MoE RMSE on Overall and Switch Windows")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "dense_vs_moe_switch_comparison.png", dpi=180)
    plt.close(fig)


def analyze_gates(
    bundle: CacheBundle,
    run_dir: Path | str,
    dataset: str,
    split: str = "test",
    baseline_run_dir: Path | str | None = None,
    turbid: int | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    run_dir = Path(run_dir)
    output_dir = ensure_dir(output_dir or (run_dir / f"{split}_analysis"))
    arrays = _load_eval_arrays(run_dir, split)

    if dataset == "wtb":
        if "gate_prob" not in arrays:
            raise RuntimeError("WTB gate analysis requires gate_prob.npy from a MoE run.")
        _plot_wtb_gate_vs_wspd(arrays, bundle, output_dir, turbid)
        _plot_wtb_timeseries(arrays, bundle, output_dir, turbid)
        _export_usage_and_entropy(arrays, bundle, output_dir)
        _plot_gate_embedding(arrays, bundle, output_dir)
    elif dataset == "era5":
        if "gate_prob" not in arrays:
            raise RuntimeError("ERA5 gate analysis requires gate_prob.npy from a MoE run.")
        _plot_era5_flux_vs_gate(arrays, bundle, output_dir)
        _export_usage_and_entropy(arrays, bundle, output_dir)
        _plot_gate_embedding(arrays, bundle, output_dir)
    else:
        raise ValueError(f"Unsupported dataset: {dataset}")

    metrics_path = run_dir / f"{split}_metrics" / "metrics.json"
    if metrics_path.exists():
        target = output_dir / "regime_wise_metrics.json"
        target.write_text(metrics_path.read_text(encoding="utf-8"), encoding="utf-8")
    csv_path = run_dir / f"{split}_metrics" / "regime_wise_metrics.csv"
    if csv_path.exists():
        (output_dir / "regime_wise_metrics.csv").write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")

    if baseline_run_dir is not None:
        baseline_arrays = _load_eval_arrays(Path(baseline_run_dir), split)
        _compare_runs(arrays, baseline_arrays, bundle, output_dir)
    return output_dir


def build_manuscript_figure2_data_boundary(
    wtb_bundle: CacheBundle,
    era5_bundle: CacheBundle,
    output_base: Path | str,
) -> Path:
    apply_manuscript_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.8), dpi=600)
    fig.subplots_adjust(hspace=0.32, wspace=0.28, left=0.08, right=0.96, top=0.94, bottom=0.08)

    # Panel A: WTB layout and wake-cone sketch.
    ax = axes[0, 0]
    coords = np.asarray(wtb_bundle.coords, dtype=np.float64)
    source_idx = int(np.argmin(np.linalg.norm(coords - coords.mean(axis=0, keepdims=True), axis=1)))
    source = coords[source_idx]
    max_distance = float(wtb_bundle.metadata["graph_config"]["max_distance"])
    cone_half_angle = float(wtb_bundle.metadata["graph_config"]["cone_half_angle_deg"])
    cone_heading = 18.0
    ax.scatter(coords[:, 0], coords[:, 1], s=22, color="#d1d5db", edgecolors="none", alpha=0.95)
    ax.scatter(
        source[0],
        source[1],
        s=110,
        color=PAPER_MODEL_COLORS["Physics-Aligned MoE"],
        edgecolors="#111827",
        linewidths=0.9,
        zorder=4,
    )
    ax.add_patch(
        patches.Circle(
            tuple(source),
            radius=max_distance,
            linewidth=1.0,
            linestyle="--",
            edgecolor="#9ca3af",
            facecolor="none",
            zorder=2,
        )
    )
    ax.add_patch(
        patches.Wedge(
            tuple(source),
            r=max_distance * 0.9,
            theta1=cone_heading - cone_half_angle,
            theta2=cone_heading + cone_half_angle,
            facecolor=PAPER_MODEL_COLORS["Physics-Aligned MoE"],
            edgecolor=PAPER_MODEL_COLORS["Physics-Aligned MoE"],
            alpha=0.16,
            linewidth=1.2,
            zorder=1,
        )
    )
    arrow_end = source + np.array(
        [np.cos(np.deg2rad(cone_heading)), np.sin(np.deg2rad(cone_heading))],
        dtype=np.float64,
    ) * (max_distance * 0.82)
    ax.annotate(
        "",
        xy=tuple(arrow_end),
        xytext=tuple(source),
        arrowprops=dict(arrowstyle="->", linewidth=1.8, color="#111827"),
    )
    ax.text(
        source[0] + max_distance * 0.12,
        source[1] + max_distance * 0.42,
        "wake cone\n(25° half-angle)",
        fontsize=8.2,
        color="#374151",
    )
    ax.text(
        source[0] - max_distance * 0.65,
        source[1] - max_distance * 0.98,
        "candidate radius = 1.5 km\nparallel decay · cross-stream decay",
        fontsize=8.0,
        color="#6b7280",
    )
    ax.set_title("A. WTB turbine layout and wake-cone rule", loc="left")
    ax.set_xlabel("X coordinate (m)")
    ax.set_ylabel("Y coordinate (m)")
    ax.set_aspect("equal", adjustable="box")
    _style_axis(ax)

    # Panel B: ERA5 patch map with local graph connections.
    ax = axes[0, 1]
    patch_shape = tuple(int(v) for v in era5_bundle.metadata["patch_shape"])
    era_coords = np.asarray(era5_bundle.coords, dtype=np.float64)
    lat = era_coords[:, 0].reshape(patch_shape)
    lon = era_coords[:, 1].reshape(patch_shape)
    sshf_idx = era5_bundle.metadata["physics_names"].index("sshf")
    train_start, train_end = _split_bounds(era5_bundle, "train")
    mean_sshf = np.asarray(era5_bundle.physics[train_start:train_end, :, sshf_idx], dtype=np.float64).mean(axis=0)
    mean_sshf = mean_sshf.reshape(patch_shape) / 1e5
    mesh = ax.pcolormesh(lon, lat, mean_sshf, shading="nearest", cmap="magma", alpha=0.90)
    center_idx = int(np.argmin(np.linalg.norm(era_coords - era_coords.mean(axis=0, keepdims=True), axis=1)))
    center_point = era_coords[center_idx]
    neighbors = np.asarray(era5_bundle.edge_index[0, center_idx], dtype=np.int64)
    neighbors = np.unique(neighbors[neighbors >= 0])
    for neighbor in neighbors:
        nb_point = era_coords[int(neighbor)]
        ax.plot(
            [center_point[1], nb_point[1]],
            [center_point[0], nb_point[0]],
            color="#ffffff",
            linewidth=1.0,
            alpha=0.55,
            zorder=3,
        )
    ax.scatter(era_coords[:, 1], era_coords[:, 0], s=12, color="#ffffff", alpha=0.28, edgecolors="none", zorder=2)
    ax.scatter(
        center_point[1],
        center_point[0],
        s=70,
        color=PAPER_MODEL_COLORS["Physics-Aligned MoE"],
        edgecolors="#111827",
        linewidths=0.8,
        zorder=4,
    )
    cbar = fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Train-mean SSHF ($10^5$ J m$^{-2}$)", fontsize=8.2)
    ax.set_title("B. ERA5 16×16 patch and local graph", loc="left")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    _style_axis(ax)

    # Panel C: WTB regime definition in wind-speed / pitch space.
    ax = axes[1, 0]
    test_start, test_end = _split_bounds(wtb_bundle, "test")
    wtb_physics = np.asarray(wtb_bundle.physics[test_start:test_end], dtype=np.float64)
    wspd = wtb_physics[..., wtb_bundle.metadata["physics_names"].index("Wspd")].reshape(-1)
    pab = wtb_physics[..., wtb_bundle.metadata["physics_names"].index("Pab_mean")].reshape(-1)
    regime = np.asarray(wtb_bundle.regime_primary[test_start:test_end], dtype=np.int16).reshape(-1)
    sample_idx = _sample_indices(regime.size, 50000, seed=42)
    wspd = wspd[sample_idx]
    pab = pab[sample_idx]
    regime = regime[sample_idx]
    primary_names = list(wtb_bundle.metadata["primary_regime_names"])
    for regime_id, regime_name in enumerate(primary_names):
        selector = regime == regime_id
        if not np.any(selector):
            continue
        ax.scatter(
            wspd[selector],
            pab[selector],
            s=8,
            alpha=0.20,
            color=PAPER_REGIME_COLORS.get(regime_name, "#9ca3af"),
            edgecolors="none",
            rasterized=True,
            label=_format_regime_label(regime_name),
        )
    ax.axvline(3.0, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axvline(10.5, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axhline(2.0, color="#6b7280", linestyle=":", linewidth=1.2)
    ax.set_xlim(0.0, float(np.nanpercentile(wspd, 99.5)) * 1.02)
    ax.set_ylim(0.0, max(5.0, float(np.nanpercentile(pab, 99.5)) * 1.02))
    ax.set_title("C. WTB operating regimes in $(Wspd, Pab_{mean})$", loc="left")
    ax.set_xlabel("Wind speed (m s$^{-1}$)")
    ax.set_ylabel("Mean pitch angle (deg)")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    _style_axis(ax)

    # Panel D: ERA5 regime definition in sshf / gradient space.
    ax = axes[1, 1]
    test_start, test_end = _split_bounds(era5_bundle, "test")
    era_physics = np.asarray(era5_bundle.physics[test_start:test_end], dtype=np.float64)
    sshf = era_physics[..., era5_bundle.metadata["physics_names"].index("sshf")].reshape(-1) / 1e5
    sshf_grad = era_physics[..., era5_bundle.metadata["physics_names"].index("sshf_grad")].reshape(-1) / 1e5
    era_regime = np.asarray(era5_bundle.regime_primary[test_start:test_end], dtype=np.int16).reshape(-1)
    sample_idx = _sample_indices(era_regime.size, 50000, seed=7)
    sshf = sshf[sample_idx]
    sshf_grad = sshf_grad[sample_idx]
    era_regime = era_regime[sample_idx]
    era_names = list(era5_bundle.metadata["primary_regime_names"])
    for regime_id, regime_name in enumerate(era_names):
        selector = era_regime == regime_id
        if not np.any(selector):
            continue
        ax.scatter(
            sshf[selector],
            sshf_grad[selector],
            s=8,
            alpha=0.20,
            color=PAPER_REGIME_COLORS.get(regime_name, "#9ca3af"),
            edgecolors="none",
            rasterized=True,
            label=_format_regime_label(regime_name),
        )
    eps = float(era5_bundle.metadata["regime_meta"]["eps"]) / 1e5
    shock_q95 = float(era5_bundle.metadata["regime_meta"]["shock_q95"]) / 1e5
    ax.axvline(-eps, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axvline(eps, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axhline(-shock_q95, color="#6b7280", linestyle=":", linewidth=1.2)
    ax.axhline(shock_q95, color="#6b7280", linestyle=":", linewidth=1.2)
    ax.set_title("D. ERA5 thermodynamic regimes in $(sshf, \\Delta sshf)$", loc="left")
    ax.set_xlabel("Surface sensible heat flux ($10^5$ J m$^{-2}$)")
    ax.set_ylabel("$\\Delta sshf$ ($10^5$ J m$^{-2}$)")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    _style_axis(ax)
    return _save_figure_variants(fig, output_base)


def build_manuscript_figure3_summary_results(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_base: Path | str,
) -> Path:
    apply_manuscript_style()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.2), dpi=600)
    fig.subplots_adjust(hspace=0.38, wspace=0.28, left=0.08, right=0.96, top=0.88, bottom=0.08)

    wtb_model_order = [
        "Graph WaveNet",
        "Graph Transformer",
        "GAT-GRU",
        "Physics-Aligned MoE",
        "PatchTST",
        "Capacity-Matched Dense Diffusion-GRU",
        "Unconstrained MoE",
        WTB_CORRECTED_DISPLAY_MODEL,
    ]
    era5_model_order = [
        "Persistence",
        "Graph WaveNet",
        "Graph Transformer",
        "GAT-GRU",
        "STGCN",
        "PatchTST",
        "TCN",
        "Capacity-Matched Dense Diffusion-GRU",
        "Physics-Aligned MoE",
        "Unconstrained MoE",
    ]
    wtb_routed_order = ["Unconstrained MoE", WTB_CORRECTED_DISPLAY_MODEL]
    era5_routed_order = ["Unconstrained MoE", "Physics-Aligned MoE"]

    wtb_metrics = [
        ("overall_rmse", "Overall RMSE"),
        ("switch_rmse", "Switch RMSE"),
        ("pitch_control_rmse", "Pitch-control RMSE"),
    ]
    era5_metrics = [
        ("overall_rmse", "Overall RMSE"),
        ("switch_rmse", "Switch RMSE"),
        ("stable_rmse", "Stable-state RMSE"),
    ]

    def _grouped_bars(
        ax: plt.Axes,
        df: pd.DataFrame,
        model_order: list[str],
        metrics: list[tuple[str, str]],
        title: str,
    ) -> None:
        x = np.arange(len(metrics))
        width = min(0.12, 0.72 / max(len(model_order), 1))
        offsets = (np.arange(len(model_order)) - (len(model_order) - 1) / 2.0) * width
        for idx, model in enumerate(model_order):
            values = _mean_by_model(df, [model], metrics[0][0])  # placeholder to preserve order
            values = [
                _mean_by_model(df, [model], metric_name)[0]
                for metric_name, _ in metrics
            ]
            ax.bar(
                x + offsets[idx],
                values,
                width=width,
                color=FIGURE3_MODEL_COLORS.get(model, "#6b7280"),
                label=model,
                alpha=0.92,
            )
        ax.set_xticks(x)
        ax.set_xticklabels([label for _, label in metrics], rotation=12, ha="right")
        ax.set_ylabel("RMSE")
        ax.set_title(title, loc="left")
        _style_axis(ax, grid_axis="y")

    _grouped_bars(axes[0, 0], wtb_df, wtb_model_order, wtb_metrics, "A. WTB strong baselines set the accuracy ceiling")
    _grouped_bars(axes[0, 1], era5_df, era5_model_order, era5_metrics, "B. ERA5 persistence and learned baselines")

    dataset_labels = ["WTB", "ERA5"]
    x = np.arange(len(dataset_labels))
    width = 0.28
    for axis, metric, title in [
        (axes[1, 0], "nmi", "C. Routing agreement measured by NMI"),
        (axes[1, 1], "ari", "D. Routing agreement measured by ARI"),
    ]:
        model_pairs = [
            ("Unconstrained MoE", "Unconstrained MoE"),
            (WTB_CORRECTED_DISPLAY_MODEL, "Physics-Aligned MoE"),
        ]
        for idx, (wtb_model, era5_model) in enumerate(model_pairs):
            values = [
                _mean_by_model(wtb_df, [wtb_model], metric)[0],
                _mean_by_model(era5_df, [era5_model], metric)[0],
            ]
            axis.bar(
                x + (idx - 0.5) * width,
                values,
                width=width,
                color=FIGURE3_MODEL_COLORS[era5_model if idx == 1 else wtb_model],
                label="Corrected routing" if idx == 1 else "Unconstrained MoE",
                alpha=0.92,
            )
        axis.set_xticks(x)
        axis.set_xticklabels(dataset_labels)
        axis.set_ylabel(metric.upper())
        axis.set_title(title, loc="left")
        _style_axis(axis, grid_axis="y")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.995))
    for ax in axes.ravel():
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()
    return _save_figure_variants(fig, output_base)


def build_manuscript_figure4_routing_evidence(
    wtb_bundle: CacheBundle,
    corrected_run_dir: Path | str,
    unconstrained_run_dir: Path | str,
    output_base: Path | str,
) -> Path:
    apply_manuscript_style()
    corrected_run_dir = Path(corrected_run_dir)
    unconstrained_run_dir = Path(unconstrained_run_dir)
    corrected = _load_eval_arrays(corrected_run_dir, "test")
    unconstrained = _load_eval_arrays(unconstrained_run_dir, "test")
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.5), dpi=600)
    fig.subplots_adjust(hspace=0.42, wspace=0.28, left=0.08, right=0.94, top=0.92, bottom=0.08)

    physics_names = list(wtb_bundle.metadata["physics_names"])
    wspd = np.asarray(corrected["anchor_physics"][..., physics_names.index("Wspd")], dtype=np.float64).reshape(-1)
    pab = np.asarray(corrected["anchor_physics"][..., physics_names.index("Pab_mean")], dtype=np.float64).reshape(-1)
    regime = _wtb_regime_from_physics(wspd, pab).reshape(-1)
    gate_prob = np.asarray(corrected["gate_prob"], dtype=np.float64).reshape(-1, corrected["gate_prob"].shape[-1])

    # Panel A: dominant expert boundary map.
    ax = axes[0, 0]
    x_min = 0.0
    x_max = float(np.nanpercentile(wspd, 99.5))
    y_min = 0.0
    y_max = max(5.0, float(np.nanpercentile(pab, 99.5)))
    x_edges = np.linspace(x_min, x_max, 27)
    y_edges = np.linspace(y_min, y_max, 25)
    dominant_grid = np.full((len(y_edges) - 1, len(x_edges) - 1), np.nan)
    for x_idx in range(len(x_edges) - 1):
        x_mask = (wspd >= x_edges[x_idx]) & (wspd < x_edges[x_idx + 1])
        for y_idx in range(len(y_edges) - 1):
            selector = x_mask & (pab >= y_edges[y_idx]) & (pab < y_edges[y_idx + 1])
            if int(selector.sum()) < 30:
                continue
            dominant_grid[y_idx, x_idx] = int(np.argmax(gate_prob[selector].mean(axis=0)))
    masked_grid = np.ma.masked_invalid(dominant_grid)
    cmap = ListedColormap(PAPER_EXPERT_COLORS[: gate_prob.shape[-1]])
    norm = BoundaryNorm(np.arange(-0.5, gate_prob.shape[-1] + 0.5, 1.0), cmap.N)
    ax.pcolormesh(x_edges, y_edges, masked_grid, cmap=cmap, norm=norm, shading="auto", alpha=0.30)
    sample_idx = _sample_indices(wspd.shape[0], 40000, seed=13)
    for regime_id, regime_name in enumerate(wtb_bundle.metadata["primary_regime_names"]):
        selector = regime[sample_idx] == regime_id
        if not np.any(selector):
            continue
        ax.scatter(
            wspd[sample_idx][selector],
            pab[sample_idx][selector],
            s=7,
            alpha=0.14,
            color=PAPER_REGIME_COLORS.get(regime_name, "#9ca3af"),
            edgecolors="none",
            rasterized=True,
            label=_format_regime_label(regime_name),
        )
    ax.axvline(3.0, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axvline(10.5, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.axhline(2.0, color="#6b7280", linestyle=":", linewidth=1.2)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel("Wind speed (m s$^{-1}$)")
    ax.set_ylabel("Mean pitch angle (deg)")
    ax.set_title("A. Corrected routing boundary in $(Wspd, Pab_{mean})$", loc="left")
    _style_axis(ax)

    # Panel B: binned gate transition curve.
    ax = axes[0, 1]
    bins = np.linspace(x_min, x_max, 25)
    centers = 0.5 * (bins[:-1] + bins[1:])
    for expert_idx in range(gate_prob.shape[-1]):
        means = np.full(centers.shape, np.nan)
        q25 = np.full(centers.shape, np.nan)
        q75 = np.full(centers.shape, np.nan)
        for idx in range(len(bins) - 1):
            selector = (wspd >= bins[idx]) & (wspd < bins[idx + 1])
            if int(selector.sum()) < 50:
                continue
            values = gate_prob[selector, expert_idx]
            means[idx] = float(np.nanmean(values))
            q25[idx] = float(np.nanpercentile(values, 25))
            q75[idx] = float(np.nanpercentile(values, 75))
        ax.plot(centers, means, color=PAPER_EXPERT_COLORS[expert_idx], label=f"Expert {expert_idx + 1}")
        ax.fill_between(centers, q25, q75, color=PAPER_EXPERT_COLORS[expert_idx], alpha=0.12)
    ax.axvline(10.5, color="#6b7280", linestyle="--", linewidth=1.1)
    ax.set_xlabel("Wind speed (m s$^{-1}$)")
    ax.set_ylabel("Gate probability")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("B. Binned gate redistribution around rated wind", loc="left")
    _style_axis(ax)
    ax2 = ax.twinx()
    mean_pab = []
    for idx in range(len(bins) - 1):
        selector = (wspd >= bins[idx]) & (wspd < bins[idx + 1])
        mean_pab.append(float(np.nanmean(pab[selector])) if int(selector.sum()) >= 50 else np.nan)
    ax2.plot(centers, mean_pab, color="#111827", linestyle="--", linewidth=2.0, label="Mean pitch")
    ax2.set_ylabel("Mean pitch angle (deg)")
    ax2.grid(False)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
        handles1 + handles2,
        labels1 + labels2,
        frameon=False,
        ncol=3,
        loc="lower center",
        bbox_to_anchor=(0.52, 1.05),
        columnspacing=1.2,
        handlelength=1.7,
    )

    # Panels C and D: confusion matrices.
    conf_labels = ["Idle", "MPPT", "Pitch-control"]
    conf_a, _ = _load_confusion_matrix(unconstrained_run_dir, conf_labels)
    conf_b, _ = _load_confusion_matrix(corrected_run_dir, conf_labels)
    cmap = sns.light_palette("#421b7b", as_cmap=True)
    for axis, conf, title in [
        (axes[1, 0], conf_a, "C. Unconstrained routing collapses"),
        (axes[1, 1], conf_b, "D. Physics-aligned routing restores structure"),
    ]:
        sns.heatmap(
            conf,
            annot=True,
            fmt="d",
            cmap=cmap,
            cbar=False,
            linewidths=0.5,
            linecolor="white",
            xticklabels=conf_labels,
            yticklabels=conf_labels,
            ax=axis,
        )
        axis.set_xlabel("Predicted gate state")
        axis.set_ylabel("Physical regime")
        axis.set_title(title, loc="left")
        axis.tick_params(axis="x", rotation=20)
        axis.tick_params(axis="y", rotation=0)
    return _save_figure_variants(fig, output_base)


def build_manuscript_figure5_case_studies(
    wtb_bundle: CacheBundle,
    dense_run_dir: Path | str,
    unconstrained_run_dir: Path | str,
    corrected_run_dir: Path | str,
    era5_bundle: CacheBundle,
    era5_corrected_run_dir: Path | str,
    output_base: Path | str,
) -> Path:
    apply_manuscript_style()
    dense = _load_eval_arrays(Path(dense_run_dir), "test")
    unconstrained = _load_eval_arrays(Path(unconstrained_run_dir), "test")
    corrected = _load_eval_arrays(Path(corrected_run_dir), "test")
    era5 = _load_eval_arrays(Path(era5_corrected_run_dir), "test")

    fig = plt.figure(figsize=(7.16, 4.6), dpi=600)
    fig.subplots_adjust(top=0.93, bottom=0.09, left=0.08, right=0.97)
    outer = fig.add_gridspec(1, 2, width_ratios=[1.08, 1.0], wspace=0.24)

    # Panel A: WTB local switch window.
    left = outer[0, 0].subgridspec(3, 1, height_ratios=[2.7, 1.35, 0.40], hspace=0.24)
    ax_a1 = fig.add_subplot(left[0, 0])
    ax_a2 = fig.add_subplot(left[1, 0], sharex=ax_a1)
    ax_a3 = fig.add_subplot(left[2, 0], sharex=ax_a1)

    anchor_physics = np.asarray(corrected["anchor_physics"], dtype=np.float64)
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
    x_hours = (np.arange(start, end) - center) / float(wtb_bundle.metadata["steps_per_hour"])

    if "target" in corrected:
        truth = np.asarray(corrected["target"][start:end, 0, node_idx], dtype=np.float64)
    else:
        truth = np.asarray(wtb_bundle.target[corrected["anchor_index"][start:end] + 1, node_idx], dtype=np.float64)
    dense_pred = np.asarray(dense["pred"][start:end, 0, node_idx], dtype=np.float64)
    unconstrained_pred = np.asarray(unconstrained["pred"][start:end, 0, node_idx], dtype=np.float64)
    corrected_pred = np.asarray(corrected["pred"][start:end, 0, node_idx], dtype=np.float64)
    ax_a1.plot(x_hours, truth, color="#111827", label="Ground truth")
    ax_a1.plot(x_hours, dense_pred, color=PAPER_MODEL_COLORS["Capacity-Matched Dense Diffusion-GRU"], label="Dense")
    ax_a1.plot(x_hours, unconstrained_pred, color=PAPER_MODEL_COLORS["Unconstrained MoE"], label="Unconstrained MoE")
    ax_a1.plot(
        x_hours,
        corrected_pred,
        color=PAPER_MODEL_COLORS[WTB_CORRECTED_DISPLAY_MODEL],
        label="Boundary-forced router",
    )
    ax_a1.axvline(0.0, color="#6b7280", linestyle="--", linewidth=1.1)
    ax_a1.set_ylabel("Patv (kW)")
    ax_a1.set_title("A. WTB local switch-window forecast comparison", loc="left")
    _style_axis(ax_a1)
    ax_a1.tick_params(axis="x", labelbottom=False)
    ax_a1.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
        bbox_to_anchor=(0.00, 1.02),
        columnspacing=1.2,
        handlelength=1.8,
        fontsize=8.2,
    )

    physics_names = list(wtb_bundle.metadata["physics_names"])
    wspd = np.asarray(corrected["anchor_physics"][start:end, node_idx, physics_names.index("Wspd")], dtype=np.float64)
    pab = np.asarray(corrected["anchor_physics"][start:end, node_idx, physics_names.index("Pab_mean")], dtype=np.float64)
    ax_a2.plot(x_hours, wspd, color="#2563eb", label="Wind speed")
    ax_a2.axhline(10.5, color="#6b7280", linestyle="--", linewidth=1.0)
    ax_a2.set_ylabel("Wspd (m s$^{-1}$)")
    ax_a2_twin = ax_a2.twinx()
    ax_a2_twin.plot(x_hours, pab, color=PAPER_REGIME_COLORS["pitch_control"], linestyle="-", label="Pitch")
    ax_a2_twin.axhline(2.0, color="#6b7280", linestyle=":", linewidth=1.0)
    ax_a2_twin.set_ylabel("Pitch (deg)")
    _style_axis(ax_a2)
    ax_a2_twin.grid(False)
    ax_a2.tick_params(axis="x", labelbottom=False)
    handles1, labels1 = ax_a2.get_legend_handles_labels()
    handles2, labels2 = ax_a2_twin.get_legend_handles_labels()
    ax_a2.legend(
        handles1 + handles2,
        labels1 + labels2,
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.18),
        ncol=2,
        columnspacing=1.0,
        handlelength=1.7,
        fontsize=8.2,
    )

    dominant_expert = np.argmax(np.asarray(corrected["gate_prob"][start:end, node_idx], dtype=np.float64), axis=-1)
    expert_strip = dominant_expert[np.newaxis, :]
    ax_a3.imshow(
        expert_strip,
        aspect="auto",
        cmap=ListedColormap(PAPER_EXPERT_COLORS[: corrected["gate_prob"].shape[-1]]),
        vmin=-0.5,
        vmax=corrected["gate_prob"].shape[-1] - 0.5,
        extent=[x_hours[0], x_hours[-1], 0.0, 1.0],
    )
    ax_a3.set_yticks([])
    ax_a3.set_ylabel("Expert")
    ax_a3.set_xlabel("Anchor offset (hours)")
    for spine in ax_a3.spines.values():
        spine.set_visible(False)
    ax_a3.grid(False)

    # Panel B: ERA5 weekly positive-control view.
    right = outer[0, 1].subgridspec(3, 1, height_ratios=[2.0, 2.1, 0.40], hspace=0.24)
    ax_b1 = fig.add_subplot(right[0, 0])
    ax_b2 = fig.add_subplot(right[1, 0], sharex=ax_b1)
    ax_b3 = fig.add_subplot(right[2, 0], sharex=ax_b1)

    sshf_idx = era5_bundle.metadata["physics_names"].index("sshf")
    flux = np.asarray(era5["anchor_physics"][..., sshf_idx], dtype=np.float64).mean(axis=1) / 1e5
    mean_gate = np.asarray(era5["gate_prob"], dtype=np.float64).mean(axis=1)
    regime_majority = np.asarray(
        [np.bincount(row.astype(np.int64), minlength=3).argmax() for row in np.asarray(era5["regime_primary"], dtype=np.int16)],
        dtype=np.int64,
    )
    window = min(168, flux.shape[0])
    x = np.arange(window)
    regime_segments = _contiguous_segments(regime_majority[:window])
    era5_names = list(era5_bundle.metadata["primary_regime_names"])
    for start_idx, end_idx, regime_id in regime_segments:
        regime_name = era5_names[int(regime_id)]
        shade_color = PAPER_REGIME_COLORS.get(regime_name, "#e5e7eb")
        ax_b1.axvspan(start_idx, end_idx, color=shade_color, alpha=0.10, linewidth=0)
        ax_b2.axvspan(start_idx, end_idx, color=shade_color, alpha=0.10, linewidth=0)
    ax_b1.plot(x, flux[:window], color="#111827")
    ax_b1.axhline(0.0, color="#6b7280", linestyle="--", linewidth=1.0)
    zero_cross = np.where(np.signbit(flux[1:window]) != np.signbit(flux[: window - 1]))[0] + 1
    for idx in zero_cross:
        ax_b1.axvline(idx, color="#6b7280", linestyle=":", linewidth=0.9, alpha=0.6)
        ax_b2.axvline(idx, color="#6b7280", linestyle=":", linewidth=0.9, alpha=0.6)
    ax_b1.set_ylabel("Mean SSHF ($10^5$ J m$^{-2}$)")
    ax_b1.set_title("B. ERA5 weekly SSHF and expert weights", loc="left")
    _style_axis(ax_b1)
    ax_b1.tick_params(axis="x", labelbottom=False)

    for expert_idx in range(mean_gate.shape[-1]):
        ax_b2.plot(x, mean_gate[:window, expert_idx], color=PAPER_EXPERT_COLORS[expert_idx], label=f"Expert {expert_idx + 1}")
    ax_b2.set_ylabel("Mean gate probability")
    ax_b2.set_ylim(-0.02, 1.02)
    ax_b2.tick_params(axis="x", labelbottom=False)
    ax_b2.legend(
        frameon=False,
        ncol=min(4, mean_gate.shape[-1]),
        loc="upper left",
        bbox_to_anchor=(0.0, 1.18),
        columnspacing=1.0,
        handlelength=1.7,
        fontsize=8.2,
    )
    _style_axis(ax_b2)

    argmax_expert = np.argmax(mean_gate[:window], axis=1)
    ax_b3.imshow(
        argmax_expert[np.newaxis, :],
        aspect="auto",
        cmap=ListedColormap(PAPER_EXPERT_COLORS[: mean_gate.shape[-1]]),
        vmin=-0.5,
        vmax=mean_gate.shape[-1] - 0.5,
        extent=[0, window - 1, 0.0, 1.0],
    )
    ax_b3.set_yticks([])
    ax_b3.set_ylabel("Expert")
    ax_b3.set_xlabel("Hour in selected week")
    for spine in ax_b3.spines.values():
        spine.set_visible(False)
    ax_b3.grid(False)
    return _save_figure_variants(fig, output_base)


def build_manuscript_figure6_ablation_tradeoff(
    wtb_ablation: pd.DataFrame,
    output_base: Path | str,
) -> Path:
    apply_manuscript_style()
    if wtb_ablation.empty:
        raise ValueError("WTB ablation table is empty; cannot build Figure 6.")
    required = {"Model", "Overall RMSE", "NMI", "ARI"}
    missing = required.difference(wtb_ablation.columns)
    if missing:
        raise ValueError(f"WTB ablation table is missing columns: {sorted(missing)}")

    def _metric_mean(value: object) -> float:
        text = str(value).replace("$\\pm$", "+/-").strip()
        if not text or text.lower() == "nan":
            return np.nan
        return float(text.split("+/-", 1)[0].strip())

    rows = []
    for _, row in wtb_ablation.iterrows():
        model = str(row["Model"])
        if model == "Capacity-Matched Dense Diffusion-GRU":
            continue
        rows.append(
            {
                "model": model,
                "overall_rmse": _metric_mean(row["Overall RMSE"]),
                "nmi": _metric_mean(row["NMI"]),
                "ari": _metric_mean(row["ARI"]),
            }
        )
    plot_df = pd.DataFrame(rows).dropna(subset=["overall_rmse"])
    if plot_df.empty:
        raise ValueError("WTB ablation table has no plottable rows for Figure 6.")

    fig, ax = plt.subplots(figsize=(3.5, 2.7), dpi=600)
    fig.subplots_adjust(left=0.16, right=0.95, top=0.90, bottom=0.16)
    color_map = {
        "Unconstrained MoE": FIGURE3_MODEL_COLORS["Unconstrained MoE"],
        "MoE + L_bal": "#8e97d0",
        "MoE + L_align": "#2a9d8f",
        "MoE + L_bal + L_align": "#6a994e",
        "MoE + L_bal + L_align + L_force": FIGURE3_MODEL_COLORS[WTB_CORRECTED_DISPLAY_MODEL],
        "MoE + L_bal + L_align + L_force + L_smooth": "#b7791f",
        "Physics-Aligned MoE": FIGURE3_MODEL_COLORS["Physics-Aligned MoE"],
    }
    short_labels = {
        "Unconstrained MoE": "MoE only",
        "MoE + L_bal": "$L_{bal}$",
        "MoE + L_align": "$L_{align}$",
        "MoE + L_bal + L_align": "$L_{bal}+L_{align}$",
        "MoE + L_bal + L_align + L_force": "$+L_{force}$",
        "MoE + L_bal + L_align + L_force + L_smooth": "$+L_{smooth}$",
        "Physics-Aligned MoE": "Full",
    }
    for _, row in plot_df.iterrows():
        model = row["model"]
        color = color_map.get(model, "#6b7280")
        ax.scatter(row["overall_rmse"], row["nmi"], s=64, marker="o", color=color, edgecolor="white", linewidth=0.8)
        ax.scatter(row["overall_rmse"], row["ari"], s=64, marker="s", color=color, edgecolor="white", linewidth=0.8, alpha=0.88)
        ax.annotate(
            short_labels.get(model, model),
            (row["overall_rmse"], row["nmi"]),
            textcoords="offset points",
            xytext=(5, 5),
            fontsize=8.2,
        )
    ax.set_title("WTB accuracy-semantics tradeoff across routing variants", loc="left")
    ax.set_xlabel("Overall RMSE")
    ax.set_ylabel("Gate-regime agreement")
    ax.set_ylim(-0.04, 1.02)
    ax.scatter([], [], s=64, marker="o", color="#4b5563", label="NMI")
    ax.scatter([], [], s=64, marker="s", color="#4b5563", label="ARI")
    ax.legend(frameon=False, loc="lower right")
    _style_axis(ax, grid_axis="both")
    return _save_figure_variants(fig, output_base)
