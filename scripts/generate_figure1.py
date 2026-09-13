import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_figure1(output_paths):
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.size'] = 6.5
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['axes.linewidth'] = 0.7

    # Compact single-column aspect ratio: 3.5 in wide by 2.2 in high
    fig, ax = plt.subplots(figsize=(3.5, 2.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    c_slate = '#1A365D'
    c_detector = '#9C4221'
    c_t1 = '#196F3D'
    c_t1_bg = '#E8F8F5'
    c_t2 = '#1B4F72'
    c_t2_bg = '#EBF5FB'
    c_t3 = '#5B2C6F'
    c_t3_bg = '#F4ECF7'

    # Top: SCADA Telemetry Stream Box
    top_box = patches.FancyBboxPatch((2, 81), 96, 16, boxstyle="round,pad=0.5,rounding_size=2",
                                    facecolor='#EDF2F7', edgecolor=c_slate, linewidth=0.9)
    ax.add_patch(top_box)
    ax.text(50, 91.5, 'Incoming SCADA Telemetry Stream', ha='center', va='center',
            fontsize=7.5, fontweight='bold', color=c_slate)
    ax.text(50, 84.5, r'Clean Telemetry $\mid$ Degraded Latency ($\tau \leq 20\,$min) $\mid$ Communication Loss ($\beta = \emptyset, \tau = 60\,$min)',
            ha='center', va='center', fontsize=5.6, color='#2D3748')

    # Arrow down
    ax.annotate('', xy=(50, 71), xytext=(50, 80),
                arrowprops=dict(arrowstyle="-|>", color=c_slate, lw=0.9, mutation_scale=8))

    # Middle: Observability & Freshness Detector Box
    det_box = patches.FancyBboxPatch((10, 59), 80, 12, boxstyle="round,pad=0.5,rounding_size=2",
                                     facecolor='#FEF9E7', edgecolor=c_detector, linewidth=0.9)
    ax.add_patch(det_box)
    ax.text(50, 66.5, 'Observability & Staleness Detector', ha='center', va='center',
            fontsize=7.2, fontweight='bold', color=c_detector)
    ax.text(50, 62, r'Verifies pitch register $\exists\beta$ and timestamp staleness $\tau$',
            ha='center', va='center', fontsize=5.7, color='#784212')

    # Three routing branches down
    # Branch 1 (left): Clean
    ax.annotate('', xy=(17, 47), xytext=(28, 58),
                arrowprops=dict(arrowstyle="-|>", color=c_t1, lw=0.8, mutation_scale=6))
    ax.text(14, 53.5, r'Clean: $\tau=0, \exists\beta$', ha='center', va='center',
            fontsize=5.2, fontweight='bold', color=c_t1)

    # Branch 2 (center): Latency <= 20 min
    ax.annotate('', xy=(50, 47), xytext=(50, 58),
                arrowprops=dict(arrowstyle="-|>", color=c_t2, lw=0.8, mutation_scale=6))
    ax.text(50, 53.5, r'$\tau \leq 20\,$min, $\exists\beta$', ha='center', va='center',
            fontsize=5.2, fontweight='bold', color=c_t2)

    # Branch 3 (right): Pitch withheld or severe delay
    ax.annotate('', xy=(83, 47), xytext=(72, 58),
                arrowprops=dict(arrowstyle="-|>", color=c_t3, lw=0.8, mutation_scale=6))
    ax.text(86, 53.5, r'$\beta=\emptyset$ or $\tau \to 60\,$m', ha='center', va='center',
            fontsize=5.2, fontweight='bold', color=c_t3)

    # Tier 1 Box (Left)
    t1_box = patches.FancyBboxPatch((1.5, 3), 30.5, 43, boxstyle="round,pad=0.5,rounding_size=2",
                                    facecolor=c_t1_bg, edgecolor=c_t1, linewidth=0.9)
    ax.add_patch(t1_box)
    ax.text(16.75, 42.5, 'Tier 1: Continuous\nPhysical Quantile', ha='center', va='center',
            fontsize=6.2, fontweight='bold', color=c_t1)
    t1_txt = (
        r"$\bullet$ Nominal $\tau=0$" + "\n"
        r"$\bullet$ 589.5k kW$\cdot$h" + "\n"
        r"$\bullet$ 6.8% violation" + "\n"
        r"$\bullet$ Zero ML compute" + "\n"
        r"$\bullet$ Deterministic rule"
    )
    ax.text(16.75, 23.5, t1_txt, ha='center', va='center', fontsize=5.4, color='#145A32', linespacing=1.2)
    ax.text(16.75, 7, '[Physics Optimal]', ha='center', va='center',
            fontsize=5.4, fontweight='bold', color=c_t1)

    # Tier 2 Box (Center)
    t2_box = patches.FancyBboxPatch((34.75, 3), 30.5, 43, boxstyle="round,pad=0.5,rounding_size=2",
                                    facecolor=c_t2_bg, edgecolor=c_t2, linewidth=0.9)
    ax.add_patch(t2_box)
    ax.text(50, 42.5, 'Tier 2: State-Cond.\nRecalibration', ha='center', va='center',
            fontsize=6.2, fontweight='bold', color=c_t2)
    t2_txt = (
        r"$\bullet$ $\tau \in [10, 20]\,$min" + "\n"
        r"$\bullet$ Full pitch $\beta$" + "\n"
        r"$\bullet$ Absorbs 55.3%" + "\n"
        r"  shortfall loss" + "\n"
        r"$\bullet$ Empirical $q_\tau(v)$"
    )
    ax.text(50, 23.5, t2_txt, ha='center', va='center', fontsize=5.4, color='#1B4F72', linespacing=1.2)
    ax.text(50, 7, '[Recalibration]', ha='center', va='center',
            fontsize=5.4, fontweight='bold', color=c_t2)

    # Tier 3 Box (Right)
    t3_box = patches.FancyBboxPatch((68, 3), 30.5, 43, boxstyle="round,pad=0.5,rounding_size=2",
                                    facecolor=c_t3_bg, edgecolor=c_t3, linewidth=0.9)
    ax.add_patch(t3_box)
    ax.text(83.25, 42.5, 'Tier 3: STGQ Modular\nResidual Head', ha='center', va='center',
            fontsize=6.2, fontweight='bold', color=c_t3)
    t3_txt = (
        r"$\bullet$ $\beta=\emptyset$ or $\tau=60$" + "\n"
        r"$\bullet$ 46.7k--68.6k saving" + "\n"
        r"$\bullet$ 9.7% violation" + "\n"
        r"$\bullet$ Recovers latent" + "\n"
        r"  operating state"
    )
    ax.text(83.25, 23.5, t3_txt, ha='center', va='center', fontsize=5.4, color='#512E5F', linespacing=1.2)
    ax.text(83.25, 7, '[ML Representation]', ha='center', va='center',
            fontsize=5.4, fontweight='bold', color=c_t3)

    plt.tight_layout(pad=0.08)
    for path in output_paths:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fig.savefig(path, format='pdf', bbox_inches='tight')
        print(f"Saved {path}")
    plt.close(fig)

if __name__ == '__main__':
    paths = [
        'standalone_ieee_package/figures/figure1_decision_boundaries.pdf',
        'figures/figure1_decision_boundaries.pdf',
        'artifacts/final_evidence_package/export/figures/figure1_decision_boundaries.pdf'
    ]
    create_figure1(paths)
