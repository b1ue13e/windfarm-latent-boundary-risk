import matplotlib.pyplot as plt
import numpy as np

# Set publication style font & settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.4), dpi=300)

# Data points: (Model Name, RMSE, Shortage MWh, Violation %, Boundary Recall, Marker, Color, Label Offset)
models = [
    {
        'name': 'iTransformer (SOTA Point)',
        'rmse': 224.34,
        'shortage': 82.5,  # Unconstrained blind spot
        'viol': 18.2,
        'recall': 0.152,
        'marker': 's',
        'color': '#7f7f7f',
        'offset1': (-45, 12),
        'offset2': (-45, -18)
    },
    {
        'name': 'Graph WaveNet',
        'rmse': 225.74,
        'shortage': 78.3,
        'viol': 16.9,
        'recall': 0.174,
        'marker': '^',
        'color': '#9467bd',
        'offset1': (-35, -18),
        'offset2': (-40, 10)
    },
    {
        'name': 'Joint Routed (Ours, Canonical)',
        'rmse': 229.93,
        'shortage': 53.9,
        'viol': 9.62,
        'recall': 0.416,
        'marker': '*',
        'color': '#d62728',
        'offset1': (-10, -20),
        'offset2': (-10, 10)
    },
    {
        'name': 'Frozen Backbone + Residual Q.',
        'rmse': 230.12,
        'shortage': 54.2,
        'viol': 9.55,
        'recall': 0.408,
        'marker': 'o',
        'color': '#1f77b4',
        'offset1': (10, 10),
        'offset2': (10, -18)
    },
    {
        'name': 'Boundary-Forced Router (Masked)',
        'rmse': 236.13,
        'shortage': 53.9,
        'viol': 9.62,
        'recall': 0.421,
        'marker': 'D',
        'color': '#ff7f0e',
        'offset1': (-50, 12),
        'offset2': (-50, 10)
    },
    {
        'name': 'Missingness-Aware GBDT',
        'rmse': 239.50,
        'shortage': 68.4,
        'viol': 8.36,
        'recall': 0.231,
        'marker': 'v',
        'color': '#8c564b',
        'offset1': (-55, -20),
        'offset2': (-55, -18)
    },
    {
        'name': 'Recalibrated Physics (State-Cond.)',
        'rmse': 285.40,
        'shortage': 57.0,
        'viol': 9.46,
        'recall': 0.312,
        'marker': 'p',
        'color': '#2ca02c',
        'offset1': (-60, 12),
        'offset2': (-60, 12)
    },
    {
        'name': 'Clean Physical Rule (Collapsed)',
        'rmse': 285.40,
        'shortage': 127.6,
        'viol': 24.02,
        'recall': 0.196,
        'marker': 'X',
        'color': '#e377c2',
        'offset1': (-75, -20),
        'offset2': (-70, -20)
    }
]

# Panel 1: RMSE vs Delay-6 Shortage Energy
ax1.grid(True, linestyle='--', alpha=0.45, color='#cccccc')
for m in models:
    size = 130 if m['marker'] in ['*', 'X'] else 90
    ax1.scatter(m['rmse'], m['shortage'], marker=m['marker'], color=m['color'], s=size, zorder=4, edgecolors='k', linewidth=0.6)
    ax1.annotate(m['name'], xy=(m['rmse'], m['shortage']), xytext=m['offset1'],
                 textcoords='offset points', fontsize=7.5, fontweight='bold' if 'Ours' in m['name'] or 'Recalibrated' in m['name'] else 'normal',
                 color='#111111', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

# Shaded regions for Panel 1
ax1.axhline(57.0, color='#2ca02c', linestyle=':', alpha=0.7, linewidth=1.2, label='Recalibrated Physics Baseline (57.0 MWh)')
ax1.axhline(100.0, color='red', linestyle='--', alpha=0.5, linewidth=1.0, label='Catastrophic Shortage Threshold')
ax1.fill_between([218, 292], 50, 60, color='#e8f5e9', alpha=0.5, zorder=1, label='Robust Reserve Envelope (< 60 MWh)')

# Arrow indicating non-RMSE optimal trade-off
ax1.annotate('Deliberately Non-RMSE-Optimal\n(+2.5% RMSE for -35% Shortage Risk)',
             xy=(229.93, 53.9), xytext=(242, 85),
             arrowprops=dict(facecolor='#d62728', shrink=0.08, width=1.2, headwidth=6),
             fontsize=8, fontweight='bold', color='#b71c1c',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffebee', edgecolor='#d62728', alpha=0.9))

ax1.set_xlabel('Whole-Sample Point Forecast RMSE (kW, Lower is Better)', fontsize=9, fontweight='bold')
ax1.set_ylabel(r'Delay-6 Reserve Shortage Exposure $\mathcal{S}$ (MWh, Lower is Better)', fontsize=9, fontweight='bold')
ax1.set_title('(A) Trade-Off: Average Point Accuracy vs. Degraded Shortage Risk', fontsize=10, fontweight='bold', pad=8)
ax1.set_xlim(220, 292)
ax1.set_ylim(45, 135)
ax1.legend(loc='upper right', fontsize=7.2, framealpha=0.9)

# Panel 2: RMSE vs Delay-6 Boundary Transition Recall
ax2.grid(True, linestyle='--', alpha=0.45, color='#cccccc')
for m in models:
    size = 130 if m['marker'] in ['*', 'X'] else 90
    ax2.scatter(m['rmse'], m['recall'], marker=m['marker'], color=m['color'], s=size, zorder=4, edgecolors='k', linewidth=0.6)
    ax2.annotate(m['name'], xy=(m['rmse'], m['recall']), xytext=m['offset2'],
                 textcoords='offset points', fontsize=7.5, fontweight='bold' if 'Ours' in m['name'] or 'Recalibrated' in m['name'] else 'normal',
                 color='#111111', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

# Shaded region for high recall
ax2.fill_between([218, 292], 0.38, 0.46, color='#e3f2fd', alpha=0.5, zorder=1, label='High Boundary Observability (Recall > 0.38)')
ax2.axhline(0.196, color='#e377c2', linestyle=':', alpha=0.8, linewidth=1.2, label='Collapsed Physics Recall (0.196)')

# Arrow indicating recall jump
ax2.annotate('Learned Representation:\n+112% Boundary Recall Recovery',
             xy=(229.93, 0.416), xytext=(242, 0.28),
             arrowprops=dict(facecolor='#1565c0', shrink=0.08, width=1.2, headwidth=6),
             fontsize=8, fontweight='bold', color='#0d47a1',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#e1f5fe', edgecolor='#1565c0', alpha=0.9))

ax2.set_xlabel('Whole-Sample Point Forecast RMSE (kW, Lower is Better)', fontsize=9, fontweight='bold')
ax2.set_ylabel('Delay-6 Boundary Regime Recall (Higher is Better)', fontsize=9, fontweight='bold')
ax2.set_title('(B) Trade-Off: Average Point Accuracy vs. Transition Observability', fontsize=10, fontweight='bold', pad=8)
ax2.set_xlim(220, 292)
ax2.set_ylim(0.10, 0.48)
ax2.legend(loc='lower right', fontsize=7.2, framealpha=0.9)

plt.tight_layout()

out_pdf = 'artifacts/final_evidence_package/export/figures/figure_s_tradeoff.pdf'
out_png = 'artifacts/final_evidence_package/export/figures/figure_s_tradeoff.png'
plt.savefig(out_pdf, format='pdf', bbox_inches='tight')
plt.savefig(out_png, format='png', dpi=300, bbox_inches='tight')
print(f'Successfully generated {out_pdf} and {out_png}')
