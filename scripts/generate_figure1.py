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

    # IEEE single-column exact aspect ratio: 3.5 in wide by 2.5 in high
    fig, ax = plt.subplots(figsize=(3.5, 2.5), dpi=300)
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
    top_box = patches.FancyBboxPatch((2.0, 78.5), 96.0, 19.5, boxstyle='round,pad=0.2,rounding_size=2.5',
                                    facecolor=c_telemetry_bg, edgecolor='#94A3B8', linewidth=0.85)
    ax.add_patch(top_box)
    ax.text(50, 93.5, 'Incoming SCADA Telemetry Stream', ha='center', va='center',
            fontsize=8.0, fontweight='bold', color=c_telemetry)
    ax.text(50, 87.2, r'Inputs: Wind Speed $v$, Active Power $P$, Blade Pitch $\beta$, Timestamp $t$',
            ha='center', va='center', fontsize=6.3, color='#334155')
    ax.text(50, 82.2, r'Regimes: Clean ($\tau=0$) $\mid$ Degraded ($\tau \leq 20\,$m) $\mid$ Contingency ($\beta=\emptyset, \tau=60\,$m)',
            ha='center', va='center', fontsize=5.8, color='#475569')

    # Arrow from top to detector
    ax.annotate('', xy=(50, 68.0), xytext=(50, 78.5),
                arrowprops=dict(arrowstyle='-|>', color='#475569', lw=1.0, mutation_scale=8))

    # 2. Middle Box: Observability & Staleness Gate
    det_box = patches.FancyBboxPatch((11.0, 55.5), 78.0, 12.5, boxstyle='round,pad=0.2,rounding_size=2.5',
                                     facecolor=c_detector_bg, edgecolor='#F59E0B', linewidth=0.85)
    ax.add_patch(det_box)
    ax.text(50, 63.8, 'Observability & Staleness Gate', ha='center', va='center',
            fontsize=7.4, fontweight='bold', color=c_detector)
    ax.text(50, 58.5, r'Audits Pitch Register $\exists\beta$ and Timestamp Freshness $\tau$',
            ha='center', va='center', fontsize=6.2, color='#92400E')

    # 3. Three Decision Routing Branches
    # Branch 1 (Left to Tier 1)
    ax.annotate('', xy=(17.25, 46.5), xytext=(28.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t1, lw=0.9, mutation_scale=6.5))
    ax.text(17.25, 50.0, r'$\tau = 0, \ \exists\beta$', ha='center', va='center',
            fontsize=5.8, fontweight='bold', color=c_t1,
            bbox=dict(boxstyle='round,pad=0.18', facecolor='#FFFFFF', edgecolor=c_t1, lw=0.6))

    # Branch 2 (Center to Tier 2)
    ax.annotate('', xy=(50.0, 46.5), xytext=(50.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t2, lw=0.9, mutation_scale=6.5))
    ax.text(50.0, 50.0, r'$\tau \leq 20\,$m, $\exists\beta$', ha='center', va='center',
            fontsize=5.8, fontweight='bold', color=c_t2,
            bbox=dict(boxstyle='round,pad=0.18', facecolor='#FFFFFF', edgecolor=c_t2, lw=0.6))

    # Branch 3 (Right to Tier 3)
    ax.annotate('', xy=(82.75, 46.5), xytext=(72.0, 55.5),
                arrowprops=dict(arrowstyle='-|>', color=c_t3, lw=0.9, mutation_scale=6.5))
    ax.text(82.75, 50.0, r'$\beta=\emptyset$ or $\tau \geq 60\,$m', ha='center', va='center',
            fontsize=5.8, fontweight='bold', color=c_t3,
            bbox=dict(boxstyle='round,pad=0.18', facecolor='#FFFFFF', edgecolor=c_t3, lw=0.6))

    # 4. Three Response Tier Cards
    def draw_tier_card(x_left, width, title, subtitle, bullets, badge_txt, c_brand, c_bg, c_badge):
        # Card Body
        card = patches.FancyBboxPatch((x_left, 2.5), width, 43.0, boxstyle='round,pad=0.2,rounding_size=2.5',
                                      facecolor=c_bg, edgecolor=c_brand, linewidth=0.9)
        ax.add_patch(card)

        # Card Header Banner
        header = patches.FancyBboxPatch((x_left, 38.5), width, 7.0, boxstyle='round,pad=0.1,rounding_size=2.0',
                                        facecolor=c_brand, edgecolor=c_brand, linewidth=0.5)
        ax.add_patch(header)
        x_mid = x_left + width / 2.0
        ax.text(x_mid, 42.0, title, ha='center', va='center',
                fontsize=6.7, fontweight='bold', color='#FFFFFF')

        # Subtitle
        ax.text(x_mid, 34.8, subtitle, ha='center', va='center',
                fontsize=6.1, fontweight='bold', color=c_brand)

        # Subtle divider rule
        ax.plot([x_left + 2.0, x_left + width - 2.0], [31.5, 31.5], color=c_brand, lw=0.4, alpha=0.4)

        # Bullet items
        y_start = 27.5
        for i, b in enumerate(bullets):
            ax.text(x_left + 2.5, y_start - i * 4.6, b, ha='left', va='center',
                    fontsize=5.7, color='#1E293B')

        # Status Badge Pill at bottom
        badge = patches.FancyBboxPatch((x_left + 2.5, 4.0), width - 5.0, 5.2, boxstyle='round,pad=0.1,rounding_size=1.5',
                                       facecolor=c_badge, edgecolor=c_brand, linewidth=0.6)
        ax.add_patch(badge)
        ax.text(x_mid, 6.6, badge_txt, ha='center', va='center',
                fontsize=5.6, fontweight='bold', color=c_brand)

    # Tier 1 Card
    t1_bullets = [
        r'• Nominal $\tau = 0$',
        '• 6.8% tail violation',
        '• Zero ML overhead',
        '• IEC 61400 rule'
    ]
    draw_tier_card(2.0, 30.5, 'Tier 1: Physical', 'Continuous Quantile', t1_bullets, '[Physics Optimal]',
                   c_t1, c_t1_bg, c_t1_badge)

    # Tier 2 Card
    t2_bullets = [
        r'• $\tau \in [10, 20]\,$min',
        r'• Pitch retained ($\exists\beta$)',
        '• Absorbs 55.3% loss',
        r'• Empirical $q_\tau(v)$'
    ]
    draw_tier_card(34.75, 30.5, 'Tier 2: Recalibrate', 'State-Conditional', t2_bullets, '[Recalibration]',
                   c_t2, c_t2_bg, c_t2_badge)

    # Tier 3 Card
    t3_bullets = [
        r'• $\beta = \emptyset$ or $\tau \geq 60\,$m',
        '• 9.7% tail violation',
        '• Saves 46k–68k kWh',
        '• Latent state recovery'
    ]
    draw_tier_card(67.5, 30.5, 'Tier 3: STGQ-Mod', 'Residual Head', t3_bullets, '[Representation]',
                   c_t3, c_t3_bg, c_t3_badge)

    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)

    for path in output_paths:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fig.savefig(path, format='pdf', bbox_inches='tight', pad_inches=0.02)
        print(f"Saved {path}")
    plt.close(fig)

if __name__ == '__main__':
    paths = [
        'standalone_ieee_package/figures/figure1_decision_boundaries.pdf',
        'figures/figure1_decision_boundaries.pdf',
        'artifacts/final_evidence_package/export/figures/figure1_decision_boundaries.pdf'
    ]
    create_figure1(paths)
