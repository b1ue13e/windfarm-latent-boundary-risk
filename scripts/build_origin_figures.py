"""
build_origin_figures.py
Automated publication-grade figure generation using local Origin 2024b in Headless Mode.

Features:
1. Connects to Origin 2024b via originpro in silent/headless mode (no intrusive popups).
2. Creates unified master project `artifacts/origin_data/paper_figures.opju`.
3. Populates subfolders for each figure:
   - /Figure2_Boundary
   - /Figure3_Summary
   - /Figure4_Routing
   - /Figure5_CaseStudies
   - /Figure6_Ablation
   - /Figure_GateStability
4. Imports standardized datasets, sets Long Names, Units, Comments.
5. Formats publication graphs to strict IEEE Transactions dimensions (3.5 in single / 7.16 in double).
6. Applies Okabe-Ito colorblind-friendly palettes and clean typography.
7. Exports publication-ready vector PDFs and 600 DPI PNGs to artifacts/paper_assets/figures/ and figures/.
8. Saves the complete .opju project for subsequent interactive viewing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import originpro as op

ORIGIN_DATA_DIR = ROOT_DIR / "artifacts" / "origin_data"
PAPER_ASSETS_FIG_DIR = ROOT_DIR / "artifacts" / "paper_assets" / "figures"
ROOT_FIGURES_DIR = ROOT_DIR / "figures"
OPJU_PATH = ORIGIN_DATA_DIR / "paper_figures.opju"

# Okabe-Ito Colors in Origin/Hex format
COLOR_NAVY = op.ocolor("#1E3A8A")
COLOR_EMERALD = op.ocolor("#047857")
COLOR_SKY = op.ocolor("#56B4E9")
COLOR_AMBER = op.ocolor("#D97706")
COLOR_PURPLE = op.ocolor("#7E22CE")
COLOR_SLATE = op.ocolor("#475569")
COLOR_VERMILLION = op.ocolor("#D55E00")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_graph_to_targets(g, base_filename: str):
    """Export graph page to vector PDF and high-res PNG in both target directories."""
    for out_dir in [PAPER_ASSETS_FIG_DIR, ROOT_FIGURES_DIR]:
        ensure_dir(out_dir)
        pdf_path = os.path.abspath(out_dir / f"{base_filename}.pdf")
        png_path = os.path.abspath(out_dir / f"{base_filename}.png")
        try:
            g.save_fig(pdf_path, type="pdf")
            g.save_fig(png_path, type="png", width=2200)
            print(f"  Exported {base_filename} to {out_dir.name}")
        except Exception as e:
            print(f"  Warning during export of {base_filename} to {out_dir}: {e}")


def build_figure2_origin():
    """Figure 2: Data & Physical Regime Boundaries"""
    print("Building Figure 2 in Origin...")
    folder_path = "/Figure2_Boundary"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    # 1. Load data
    f2a = ORIGIN_DATA_DIR / "Figure2_Boundary" / "fig2a_wtb_layout.csv"
    f2c = ORIGIN_DATA_DIR / "Figure2_Boundary" / "fig2c_wtb_regimes.csv"
    
    if not f2a.exists() or not f2c.exists():
        print("  Missing Figure 2 data, skipping.")
        return

    df_layout = pd.read_csv(f2a)
    df_regimes = pd.read_csv(f2c)

    # Workbooks
    wb_layout = op.new_book("w", "WTB_Layout")
    wks_layout = wb_layout[0]
    wks_layout.from_df(df_layout)
    wks_layout.set_label(0, "Turbine ID", "L")
    wks_layout.set_label(1, "X Position", "L")
    wks_layout.set_label(1, "m", "U")
    wks_layout.set_label(2, "Y Position", "L")
    wks_layout.set_label(2, "m", "U")

    wb_reg = op.new_book("w", "WTB_Regimes")
    wks_reg = wb_reg[0]
    wks_reg.from_df(df_regimes)
    wks_reg.set_label(0, "Wind Speed", "L")
    wks_reg.set_label(0, "m/s", "U")
    wks_reg.set_label(1, "Pitch Angle", "L")
    wks_reg.set_label(1, "deg", "U")

    # Graph
    g = op.new_graph(lname="Figure 2 Data Boundary")
    g.lt_exec("page.width = 7.16; page.height = 3.6;")
    
    # Layer 1: Layout
    gl1 = g[0]
    p1 = gl1.add_plot(wks_layout, coly=2, colx=1, type="scatter")
    if p1:
        p1.symbol_size = 3
        p1.symbol_color = COLOR_SLATE
    gl1.lt_exec("layer.x = 8; layer.y = 12; layer.width = 40; layer.height = 78;")
    gl1.lt_exec('xb.text$ = "X coordinate (m)"; yl.text$ = "Y coordinate (m)";')
    gl1.lt_exec('title.text$ = "\\b(A) WTB Turbine Layout";')

    # Layer 2: Regimes
    gl2 = g.add_layer()
    p2 = gl2.add_plot(wks_reg, coly=1, colx=0, type="scatter")
    if p2:
        p2.symbol_size = 2
        p2.symbol_color = COLOR_EMERALD
    gl2.lt_exec("layer.x = 56; layer.y = 12; layer.width = 40; layer.height = 78;")
    gl2.lt_exec('xb.text$ = "Wind speed (m/s)"; yl.text$ = "Mean pitch angle (deg)";')
    gl2.lt_exec('title.text$ = "\\b(B) Operating Regimes";')

    export_graph_to_targets(g, "figure2_data_boundary")


def build_figure3_origin():
    """Figure 3: Benchmark Summary Results"""
    print("Building Figure 3 in Origin...")
    folder_path = "/Figure3_Summary"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    f3a = ORIGIN_DATA_DIR / "Figure3_Summary" / "fig3a_wtb_benchmark.csv"
    f3c = ORIGIN_DATA_DIR / "Figure3_Summary" / "fig3c_routing_agreement.csv"
    if not f3a.exists():
        print("  Missing Figure 3 data, skipping.")
        return

    df_wtb = pd.read_csv(f3a)
    df_rout = pd.read_csv(f3c) if f3c.exists() else pd.DataFrame()

    wb_wtb = op.new_book("w", "WTB_Benchmark")
    wks_wtb = wb_wtb[0]
    wks_wtb.from_df(df_wtb)

    wb_rout = op.new_book("w", "Routing_Agreement")
    wks_rout = wb_rout[0]
    wks_rout.from_df(df_rout)

    g = op.new_graph(lname="Figure 3 Summary Results")
    g.lt_exec("page.width = 7.16; page.height = 3.6;")
    
    # Layer 1: WTB RMSE
    gl1 = g[0]
    gl1.add_plot(wks_wtb, coly=1, colx=0, type="column")
    gl1.lt_exec("layer.x = 8; layer.y = 16; layer.width = 46; layer.height = 74;")
    gl1.lt_exec('xb.text$ = "Model Architecture"; yl.text$ = "Overall RMSE (kW)";')
    gl1.lt_exec('title.text$ = "\\b(A) WTB Benchmark Accuracy";')
    gl1.lt_exec("layer.x.label.rotation = 45;")

    # Layer 2: Routing NMI/ARI
    gl2 = g.add_layer()
    if len(df_rout) > 0:
        gl2.add_plot(wks_rout, coly=2, colx=1, type="column")
    gl2.lt_exec("layer.x = 60; layer.y = 16; layer.width = 36; layer.height = 74;")
    gl2.lt_exec('xb.text$ = "Router Configuration"; yl.text$ = "Normalized Mutual Information";')
    gl2.lt_exec('title.text$ = "\\b(B) Gate Routing Alignment";')
    gl2.lt_exec("layer.x.label.rotation = 30;")

    export_graph_to_targets(g, "figure3_summary_results")


def build_figure4_origin():
    """Figure 4: Gate Routing Evidence"""
    print("Building Figure 4 in Origin...")
    folder_path = "/Figure4_Routing"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    f4a = ORIGIN_DATA_DIR / "Figure4_Routing" / "fig4a_gate_bins.csv"
    if not f4a.exists():
        print("  Missing Figure 4 data, skipping.")
        return

    df_bins = pd.read_csv(f4a)
    wb_bins = op.new_book("w", "Gate_Transitions")
    wks_bins = wb_bins[0]
    wks_bins.from_df(df_bins)

    g = op.new_graph(lname="Figure 4 Routing Evidence")
    g.lt_exec("page.width = 7.16; page.height = 3.4;")
    
    gl = g[0]
    p1 = gl.add_plot(wks_bins, coly=1, colx=0, type="line")
    p2 = gl.add_plot(wks_bins, coly=3, colx=0, type="line")
    p3 = gl.add_plot(wks_bins, coly=5, colx=0, type="line")
    if p1: p1.color = COLOR_NAVY; p1.linewidth = 1.5
    if p2: p2.color = COLOR_EMERALD; p2.linewidth = 1.5
    if p3: p3.color = COLOR_AMBER; p3.linewidth = 1.5

    gl.lt_exec("layer.x = 10; layer.y = 15; layer.width = 82; layer.height = 75;")
    gl.lt_exec('xb.text$ = "Inflow Wind Speed (m/s)"; yl.text$ = "Gate Dispatch Probability";')
    gl.lt_exec('title.text$ = "\\bBinned Expert Routing Transitions around Rated Wind Speed";')

    export_graph_to_targets(g, "figure4_routing_evidence")


def build_figure5_origin():
    """Figure 5: Switch Window Case Studies"""
    print("Building Figure 5 in Origin...")
    folder_path = "/Figure5_CaseStudies"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    f5 = ORIGIN_DATA_DIR / "Figure5_CaseStudies" / "fig5_switch_window_timeseries.csv"
    if not f5.exists():
        print("  Missing Figure 5 data, skipping.")
        return

    df_traj = pd.read_csv(f5)
    wb_traj = op.new_book("w", "Switch_Timeseries")
    wks_traj = wb_traj[0]
    wks_traj.from_df(df_traj)

    g = op.new_graph(lname="Figure 5 Case Studies")
    g.lt_exec("page.width = 7.16; page.height = 3.2;")

    gl = g[0]
    p_gt = gl.add_plot(wks_traj, coly=1, colx=0, type="line")
    p_dense = gl.add_plot(wks_traj, coly=2, colx=0, type="line")
    p_uncon = gl.add_plot(wks_traj, coly=3, colx=0, type="line")
    p_corr = gl.add_plot(wks_traj, coly=4, colx=0, type="line")

    if p_gt: p_gt.color = COLOR_SLATE; p_gt.linewidth = 1.6
    if p_dense: p_dense.color = COLOR_SKY; p_dense.linewidth = 1.3
    if p_uncon: p_uncon.color = COLOR_AMBER; p_uncon.linewidth = 1.3
    if p_corr: p_corr.color = COLOR_PURPLE; p_corr.linewidth = 1.8

    gl.lt_exec("layer.x = 9; layer.y = 15; layer.width = 84; layer.height = 75;")
    gl.lt_exec('xb.text$ = "Relative Time (Hours to MPPT-to-Pitch Switch)"; yl.text$ = "Active Power P (kW)";')
    gl.lt_exec('title.text$ = "\\bWTB Local Dynamic Switch-Window Forecast Trajectories";')

    export_graph_to_targets(g, "figure5_case_studies")


def build_figure6_origin():
    """Figure 6: Ablation Trade-off (Single Column 3.5 in)"""
    print("Building Figure 6 in Origin...")
    folder_path = "/Figure6_Ablation"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    f6 = ORIGIN_DATA_DIR / "Figure6_Ablation" / "fig6_ablation_frontier.csv"
    if not f6.exists():
        print("  Missing Figure 6 data, skipping.")
        return

    df_abl = pd.read_csv(f6)
    wb_abl = op.new_book("w", "Ablation_Frontier")
    wks_abl = wb_abl[0]
    wks_abl.from_df(df_abl)

    g = op.new_graph(lname="Figure 6 Ablation Tradeoff")
    # Strict IEEE single-column specification
    g.lt_exec("page.width = 3.5; page.height = 2.6;")

    gl = g[0]
    p_nmi = gl.add_plot(wks_abl, coly=3, colx=1, type="scatter")
    p_ari = gl.add_plot(wks_abl, coly=5, colx=1, type="scatter")

    if p_nmi: p_nmi.symbol_size = 5; p_nmi.symbol_color = COLOR_NAVY
    if p_ari: p_ari.symbol_size = 5; p_ari.symbol_color = COLOR_VERMILLION

    gl.lt_exec("layer.x = 16; layer.y = 18; layer.width = 76; layer.height = 70;")
    gl.lt_exec('xb.text$ = "Overall Test RMSE (kW)"; yl.text$ = "Routing Alignment (NMI / ARI)";')
    gl.lt_exec('title.text$ = "\\bAccuracy vs Interpretability Trade-off";')

    export_graph_to_targets(g, "figure6_ablation_tradeoff")


def build_gate_stability_origin():
    """Gate Stability: Multi-Year Temporal Decay"""
    print("Building Gate Stability in Origin...")
    folder_path = "/Figure_GateStability"
    op.pe.mkdir(folder_path)
    op.pe.cd(folder_path)

    f_km = ORIGIN_DATA_DIR / "Figure_GateStability" / "fig_stability_kelmarsh.csv"
    f_pm = ORIGIN_DATA_DIR / "Figure_GateStability" / "fig_stability_penmanshiel.csv"
    if not f_km.exists() or not f_pm.exists():
        print("  Missing Stability data, skipping.")
        return

    df_km = pd.read_csv(f_km)
    df_pm = pd.read_csv(f_pm)

    wb_km = op.new_book("w", "Kelmarsh_Stability")
    wks_km = wb_km[0]
    wks_km.from_df(df_km)

    wb_pm = op.new_book("w", "Penmanshiel_Stability")
    wks_pm = wb_pm[0]
    wks_pm.from_df(df_pm)

    g = op.new_graph(lname="Gate Representation Stability")
    g.lt_exec("page.width = 7.16; page.height = 2.5;")

    # 3 horizontal layers
    gl1 = g[0]
    p_km1 = gl1.add_plot(wks_km, coly=1, colx=0, type="line")
    p_km2 = gl1.add_plot(wks_km, coly=3, colx=0, type="line")
    if p_km1: p_km1.color = COLOR_NAVY; p_km1.linewidth = 1.3
    if p_km2: p_km2.color = COLOR_EMERALD; p_km2.linewidth = 1.2
    gl1.lt_exec("layer.x = 8; layer.y = 18; layer.width = 26; layer.height = 68;")
    gl1.lt_exec('xb.text$ = "Calendar Year"; yl.text$ = "Inv-W1 Similarity";')
    gl1.lt_exec('title.text$ = "\\b(A) Kelmarsh (9 Yrs)";')

    gl2 = g.add_layer()
    p_pm1 = gl2.add_plot(wks_pm, coly=1, colx=0, type="line")
    p_pm2 = gl2.add_plot(wks_pm, coly=3, colx=0, type="line")
    if p_pm1: p_pm1.color = COLOR_VERMILLION; p_pm1.linewidth = 1.3
    if p_pm2: p_pm2.color = COLOR_PURPLE; p_pm2.linewidth = 1.2
    gl2.lt_exec("layer.x = 40; layer.y = 18; layer.width = 26; layer.height = 68;")
    gl2.lt_exec('xb.text$ = "Calendar Year"; yl.text$ = "Inv-W1 Similarity";')
    gl2.lt_exec('title.text$ = "\\b(B) Penmanshiel (8.6 Yrs)";')

    gl3 = g.add_layer()
    p_nmi1 = gl3.add_plot(wks_km, coly=5, colx=0, type="line")
    p_nmi2 = gl3.add_plot(wks_pm, coly=5, colx=0, type="line")
    if p_nmi1: p_nmi1.color = COLOR_NAVY; p_nmi1.linewidth = 1.3
    if p_nmi2: p_nmi2.color = COLOR_VERMILLION; p_nmi2.linewidth = 1.3
    gl3.lt_exec("layer.x = 72; layer.y = 18; layer.width = 25; layer.height = 68;")
    gl3.lt_exec('xb.text$ = "Calendar Year"; yl.text$ = "Ground-Truth NMI";')
    gl3.lt_exec('title.text$ = "\\b(C) NMI Alignment";')

    export_graph_to_targets(g, "figure_gate_representation_stability")


def main():
    print(f"=== Connecting to local Origin 2024b in Headless Mode ===")
    op.set_show(False)
    
    # Reset / Create project
    op.new()
    
    try:
        build_figure2_origin()
        build_figure3_origin()
        build_figure4_origin()
        build_figure5_origin()
        build_figure6_origin()
        build_gate_stability_origin()
        
        # Save project
        abs_opju = os.path.abspath(OPJU_PATH)
        ensure_dir(Path(abs_opju).parent)
        op.save(abs_opju)
        print(f"=== Saved unified Origin project to {abs_opju} ===")
    finally:
        op.exit()
        print("=== Origin 2024b closed cleanly. ===")


if __name__ == "__main__":
    main()
