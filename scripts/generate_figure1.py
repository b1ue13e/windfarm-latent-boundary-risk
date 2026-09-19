import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_figure1(output_paths):
    # Set high-grade scientific styling
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
    plt.rcParams['mathtext.fontset'] = 'dejavusans'
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['axes.linewidth'] = 0.8

    # IEEE single-column exact width: 3.5 in (252 pt) by 3.1 in (223.2 pt)
    fig = plt.figure(figsize=(3.5, 3.1), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Okabe-Ito & High-End Publication Palette
    c_telemetry = '#1E3A8A'      # Deep Navy
    c_telemetry_bg = '#F8FAFC'
    c_detector = '#B45309'       # Amber / Ochre
    c_detector_bg = '#FFFBEB'

    c_t1 = '#047857'             # Emerald / Teal (Tier 1: Physics)
    c_t1_bg = '#F0FDF4'
    c_t1_badge = '#DCFCE7'

    c_t2 = '#0284C7'             # Ocean Blue (Tier 2: Recalibration)
    c_t2_bg = '#F0F9FF'
    c_t2_badge = '#E0F2FE'

    c_t3 = '#7E22CE'             # Deep Purple (Tier 3: STGQ Modular ML)
    c_t3_bg = '#FAF5FF'
    c_t3_badge = '#F3E8FF'

    # 1. Top Box: SCADA Telemetry Stream
    top_box = patches.FancyBboxPatch((1.5, 78.0), 97.0, 20.5, boxstyle='round,pad=0.2,rounding_size=2.0',
                                    facecolor=c_telemetry_bg, edgecolor='#94A3B8', linewidth=0.85)
    ax.add_patch(top_box)
    ax.text(50, 93.8, 'Incoming SCADA Telemetry Stream', ha='center', va='center',
            fontsize=8.8, fontweight='bold', color=c_telemetry)
    ax.text(50, 87.2, r'Inputs: Wind Speed $v$, Power $P$, Pitch $\beta$, Time $t$',
            ha='center', va='center', fontsize=8.0, color='#334155')
    ax.text(50, 81.8, r'Clean ($\tau=0$) $\mid$ Latency ($\tau \leq 20\,$m) $\mid$ Drop ($\beta=\emptyset$)',
            ha='center', va='center', fontsize=8.0, color='#475569')

    # Arrow from top to detector
    ax.annotate('', xy=(50, 68.0), xytext=(50, 78.0),
                arrowprops=dict(arrowstyle='-|>', color='#475569', lw=1.0, mutation_scale=8))

    # 2. Middle Box: Observability & Staleness Gate
    det_box = patches.FancyBboxPatch((6.0, 55.5), 88.0, 12.5, boxstyle='round,pad=0.2,rounding_size=2.0',
                                     facecolor=c_detector_bg, edgecolor='#F59E0B', linewidth=0.85)
    ax.add_patch(det_box)
    ax.text(50, 63.8, 'Observability & Staleness Gate', ha='center', va='center',
            fontsize=8.6, fontweight='bold', color=c_detector)
    ax.text(50, 58.2, r'Audits Pitch Register $\exists\beta$ and Latency $\tau$',
            ha='center', va='center', fontsize=8.0, color='#92400E')

    # 3. Three Decision Routing Branches
    # Left Branch (Tier 1)
    ax.annotate('', xy=(17.5, 46.5), xytext=(28.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t1, lw=0.9, mutation_scale=6.5))
    ax.text(17.5, 50.2, r'$\tau = 0, \ \exists\beta$', ha='center', va='center',
            fontsize=8.0, fontweight='bold', color=c_t1,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='#FFFFFF', edgecolor=c_t1, lw=0.6))

    # Center Branch (Tier 2)
    ax.annotate('', xy=(50.0, 46.5), xytext=(50.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t2, lw=0.9, mutation_scale=6.5))
    ax.text(50.0, 50.2, r'$\tau \leq 20\,$m, $\exists\beta$', ha='center', va='center',
            fontsize=8.0, fontweight='bold', color=c_t2,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='#FFFFFF', edgecolor=c_t2, lw=0.6))

    # Right Branch (Tier 3)
    ax.annotate('', xy=(82.5, 46.5), xytext=(72.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t3, lw=0.9, mutation_scale=6.5))
    ax.text(82.5, 50.2, r'$\beta=\emptyset$ or $\tau \geq 60\,$m', ha='center', va='center',
            fontsize=8.0, fontweight='bold', color=c_t3,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='#FFFFFF', edgecolor=c_t3, lw=0.6))

    # 4. Three Response Tier Cards
    def draw_tier_card(x_left, width, title, subtitle, bullets, badge_txt, c_brand, c_bg, c_badge):
        card = patches.FancyBboxPatch((x_left, 1.5), width, 44.0, boxstyle='round,pad=0.2,rounding_size=2.0',
                                      facecolor=c_bg, edgecolor=c_brand, linewidth=0.9)
        ax.add_patch(card)

        header = patches.FancyBboxPatch((x_left, 38.8), width, 6.7, boxstyle='round,pad=0.1,rounding_size=1.8',
                                        facecolor=c_brand, edgecolor=c_brand, linewidth=0.5)
        ax.add_patch(header)
        x_mid = x_left + width / 2.0
        ax.text(x_mid, 42.1, title, ha='center', va='center',
                fontsize=8.2, fontweight='bold', color='#FFFFFF')

        ax.text(x_mid, 35.2, subtitle, ha='center', va='center',
                fontsize=8.0, fontweight='bold', color=c_brand)

        ax.plot([x_left + 1.5, x_left + width - 1.5], [31.5, 31.5], color=c_brand, lw=0.4, alpha=0.4)

        y_start = 27.0
        for i, b in enumerate(bullets):
            ax.text(x_left + 2.0, y_start - i * 4.9, b, ha='left', va='center',
                    fontsize=8.0, color='#1E293B')

        badge = patches.FancyBboxPatch((x_left + 1.5, 2.5), width - 3.0, 5.5, boxstyle='round,pad=0.1,rounding_size=1.5',
                                       facecolor=c_badge, edgecolor=c_brand, linewidth=0.6)
        ax.add_patch(badge)
        ax.text(x_mid, 5.2, badge_txt, ha='center', va='center',
                fontsize=8.0, fontweight='bold', color=c_brand)

    t1_bullets = [
        r'• Nominal $\tau = 0$',
        '• 6.8% violation',
        '• Zero ML cost',
        '• IEC 61400 rule'
    ]
    draw_tier_card(1.5, 31.0, 'Tier 1: Physical', 'Continuous Quantile', t1_bullets, '[Lowest Cost]',
                   c_t1, c_t1_bg, c_t1_badge)

    t2_bullets = [
        r'• $\tau \leq 20\,$min',
        r'• Pitch $\exists\beta$',
        '• Absorbs 55% loss',
        r'• Empirical $q_\tau(v)$'
    ]
    draw_tier_card(34.5, 31.0, 'Tier 2: Recalibrate', 'State-Conditional', t2_bullets, '[Recalibration]',
                   c_t2, c_t2_bg, c_t2_badge)

    t3_bullets = [
        r'• $\beta = \emptyset$ or $\tau \geq 60\,$m',
        '• 9.7% violation',
        '• Saves 46k–68k',
        '• Latent recovery'
    ]
    draw_tier_card(67.5, 31.0, 'Tier 3: STGQ-Mod', 'Residual Head', t3_bullets, '[Representation]',
                   c_t3, c_t3_bg, c_t3_badge)

    for path in output_paths:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fig.savefig(path, format='pdf')
        print(f"Saved {path}")
    plt.close(fig)

if __name__ == '__main__':
    paths = [
        'standalone_ieee_package/figures/figure1_decision_boundaries.pdf',
        'figures/figure1_decision_boundaries.pdf',
        'artifacts/final_evidence_package/export/figures/figure1_decision_boundaries.pdf'
    ]
    create_figure1(paths)
