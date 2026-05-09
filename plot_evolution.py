"""
plot_evolution.py — Generate all plots from a saved evolution CSV.

Usage:
    python plot_evolution.py                        # picks latest CSV in same folder
    python plot_evolution.py evolution_XYZ.csv      # explicit file
"""

import sys, os, csv, math, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ============================================================
#  CONSTANTS (must match jellyfish_ga.py)
# ============================================================
FPS        = 120
GENOME_MIN = np.array([0.05, FPS//2, 0.05, 0.30, 0.30], dtype=np.float64)
GENOME_MAX = np.array([2.00, FPS*4,  0.95, 2.60, 1.50], dtype=np.float64)


# ============================================================
#  CSV READER
# ============================================================

def load_csv(path):
    """Return a history dict reconstructed from the CSV."""
    history = {
        'best': [], 'avg': [], 'min': [],
        'best_genome': [],
        'all_genomes': [], 'all_fitnesses': [],
        'all_displacements': [], 'all_energies': [],
    }

    by_gen = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            g = int(row['gen'])
            if g not in by_gen:
                by_gen[g] = {
                    'best_fitness': float(row['best_fitness']),
                    'avg_fitness':  float(row['avg_fitness']),
                    'min_fitness':  float(row['min_fitness']),
                    'members': [],
                }
            by_gen[g]['members'].append({
                'amplitude':    float(row['amplitude']),
                'period':       float(row['period']),
                'duty_cycle':   float(row['duty_cycle']),
                'arm_angle':    math.radians(float(row['arm_angle_deg'])),
                'arm_length':   float(row['arm_length']),
                'fitness':      float(row['member_fitness']),
                'distance':     float(row['member_distance']),
                'energy':       float(row['member_energy']),
            })

    for g in sorted(by_gen):
        info    = by_gen[g]
        members = info['members']

        history['best'].append(info['best_fitness'])
        history['avg'].append(info['avg_fitness'])
        history['min'].append(info['min_fitness'])

        genomes   = np.array([[m['amplitude'], m['period'], m['duty_cycle'],
                               m['arm_angle'], m['arm_length']] for m in members])
        fitnesses = [m['fitness']  for m in members]
        disps     = [m['distance'] for m in members]
        energies  = [m['energy']   for m in members]

        best_idx = int(np.argmax(fitnesses))
        history['best_genome'].append(genomes[best_idx])
        history['all_genomes'].append(genomes)
        history['all_fitnesses'].append(fitnesses)
        history['all_displacements'].append(disps)
        history['all_energies'].append(energies)

    return history


# ============================================================
#  PLOT HELPERS
# ============================================================

def _param_band(ax, pop_vals_list, gens, best_line, color):
    for gi, vals in enumerate(pop_vals_list):
        if len(vals) == 0:
            continue
        q25, q75 = np.percentile(vals, [25, 75])
        ax.fill_between([gi, gi+1], [q25]*2, [q75]*2, alpha=0.22, color=color)
    ax.plot(gens, best_line, color=color, lw=2, label='Best')
    ax.legend(fontsize=8)


# ============================================================
#  PLOTS
# ============================================================

def save_plots(history, out_dir, timestamp):
    gens = list(range(len(history['best'])))
    if not gens:
        print("No generations found — nothing to plot.")
        return

    pb  = np.array(history['best_genome'])   # (n_gens, 5)
    ag  = history['all_genomes']
    af  = [np.array(x) for x in history['all_fitnesses']]
    ad  = [np.array(x) for x in history['all_displacements']]
    ae  = [np.array(x) for x in history['all_energies']]

    pb_deg       = pb.copy()
    pb_deg[:, 3] = np.degrees(pb_deg[:, 3])

    labels  = ['Amplitude (rad)', 'Period (fr)', 'Duty cycle', 'Arm angle (°)', 'Arm length']
    colors  = ['#e67e22', '#3498db', '#9b59b6', '#1abc9c', '#e74c3c']
    lo_disp = [GENOME_MIN[0], GENOME_MIN[1], GENOME_MIN[2],
               math.degrees(GENOME_MIN[3]), GENOME_MIN[4]]
    hi_disp = [GENOME_MAX[0], GENOME_MAX[1], GENOME_MAX[2],
               math.degrees(GENOME_MAX[3]), GENOME_MAX[4]]

    def pop_vals(pi):
        out = []
        for g_arr in ag:
            v = g_arr[:, pi].copy()
            if pi == 3:
                v = np.degrees(v)
            out.append(v)
        return out

    paths = []

    # ── 1. Fitness evolution ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(gens, history['best'], '#2ecc71', lw=2, marker='o', ms=4, label='Best')
    ax.plot(gens, history['avg'],  '#3498db', lw=1.5, ls='--',        label='Average')
    ax.plot(gens, history['min'],  '#e74c3c', lw=1.5, ls=':',         label='Minimum')
    ax.fill_between(gens, history['avg'], history['best'], alpha=0.12, color='#2ecc71')
    ax.fill_between(gens, history['min'], history['avg'],  alpha=0.08, color='#e74c3c')
    ax.set(xlabel='Generation', ylabel='Fitness',
           title='Fitness Evolution — Jellyfish GA')
    ax.legend(fontsize=11); ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    fig.tight_layout()
    p = os.path.join(out_dir, f"plot_fitness_{timestamp}.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    # ── 2. Parameter trajectory of best individual ────────────────────
    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
    for i, (ax, label, color) in enumerate(zip(axes, labels, colors)):
        ax.plot(gens, pb_deg[:, i], color=color, lw=2, marker='o', ms=3)
        ax.axhline(lo_disp[i], color='gray', ls=':', lw=1, alpha=0.5)
        ax.axhline(hi_disp[i], color='gray', ls=':', lw=1, alpha=0.5)
        ax.set_ylim(lo_disp[i]*0.85, hi_disp[i]*1.08)
        ax.set_title(label, fontweight='bold', fontsize=10)
        ax.set_xlabel('Generation', fontsize=9)
        ax.grid(True, alpha=0.3)
    fig.suptitle("Best Individual — Parameter Trajectory over Generations",
                 fontsize=12, fontweight='bold')
    fig.tight_layout()
    p = os.path.join(out_dir, f"plot_params_{timestamp}.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    # ── 3. Population exploration — violin per generation ────────────
    fig, axes = plt.subplots(1, 5, figsize=(21, 5))
    cmap = plt.cm.cool
    for i, (ax, label, color) in enumerate(zip(axes, labels, colors)):
        data = pop_vals(i)
        vp   = ax.violinplot(data, positions=gens,
                             showmedians=True, showextrema=True, widths=0.7)
        for pc in vp['bodies']:
            pc.set_facecolor(cmap(0.55)); pc.set_alpha(0.42)
        vp['cmedians'].set_color('white'); vp['cmedians'].set_linewidth(1.5)
        ax.plot(gens, pb_deg[:, i], color=color, lw=2, zorder=5, label='Best')
        ax.set_ylim(lo_disp[i]*0.82, hi_disp[i]*1.10)
        ax.set_title(label, fontweight='bold', fontsize=10)
        ax.set_xlabel('Generation', fontsize=9)
        ax.grid(True, alpha=0.25, axis='y')
        ax.legend(fontsize=8)
        if len(gens) <= 20:
            ax.set_xticks(gens[::max(1, len(gens)//10)])
    fig.suptitle("Parameter Exploration per Generation  "
                 "(violin = population, line = best individual)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    p = os.path.join(out_dir, f"plot_exploration_{timestamp}.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    # ── 4. Displacement–Energy Pareto + fitness distribution ─────────
    fd = ad[-1]; fe = ae[-1]; ff = af[-1]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sc = axes[0].scatter(fd, fe, c=ff, cmap='plasma', s=55,
                         alpha=0.75, edgecolors='none')
    fig.colorbar(sc, ax=axes[0], label='Fitness')
    bi = int(np.argmax(ff))
    axes[0].scatter([fd[bi]], [fe[bi]], c='lime', s=220, marker='*',
                    zorder=5, label=f'Best (f={ff[bi]:.4f})')
    axes[0].set(xlabel='Displacement (units)', ylabel='Total energy',
                title='Last Generation: Displacement vs Energy')
    axes[0].legend(fontsize=10); axes[0].grid(True, alpha=0.3)

    nonzero = ff[ff > 0]
    axes[1].hist(nonzero, bins=min(20, max(len(nonzero)//2+1, 2)),
                 color='#3498db', edgecolor='white', linewidth=0.5)
    if len(nonzero):
        axes[1].axvline(ff.max(), color='#e74c3c', lw=2, ls='--',
                        label=f'Best: {ff.max():.5f}')
        axes[1].axvline(nonzero.mean(), color='#2ecc71', lw=1.5, ls=':',
                        label=f'Avg >0: {nonzero.mean():.5f}')
    axes[1].set(xlabel='Fitness', ylabel='Count',
                title='Last Generation: Fitness Distribution')
    axes[1].legend(fontsize=10); axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    p = os.path.join(out_dir, f"plot_pareto_{timestamp}.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    # ── 5. Summary panel 2×3 ─────────────────────────────────────────
    fig = plt.figure(figsize=(18, 10))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.44, wspace=0.34)

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(gens, history['best'], '#2ecc71', lw=2, marker='o', ms=3, label='Best')
    ax.plot(gens, history['avg'],  '#3498db', lw=1.5, ls='--', label='Avg')
    ax.plot(gens, history['min'],  '#e74c3c', lw=1.5, ls=':',  label='Min')
    ax.fill_between(gens, history['avg'], history['best'], alpha=0.12, color='#2ecc71')
    ax.set_title('Fitness Evolution', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='Fitness')
    ax.legend(fontsize=9); ax.grid(alpha=0.3); ax.set_ylim(bottom=0)

    ax = fig.add_subplot(gs[0, 1])
    _param_band(ax, pop_vals(0), gens, pb_deg[:, 0], colors[0])
    ax.set_title('Amplitude (rad)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='rad'); ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[0, 2])
    _param_band(ax, pop_vals(2), gens, pb_deg[:, 2], colors[2])
    ax.set_title('Duty Cycle', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation'); ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[1, 0])
    _param_band(ax, pop_vals(3), gens, pb_deg[:, 3], colors[3])
    ax.set_title('Arm Angle (°)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='degrees'); ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[1, 1])
    best_hz = FPS / pb[:, 1]
    pop_hz  = [FPS / g[:, 1] for g in ag]
    _param_band(ax, pop_hz, gens, best_hz, colors[1])
    ax.set_title('Frequency (Hz)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='Hz'); ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[1, 2])
    _param_band(ax, pop_vals(4), gens, pb_deg[:, 4], colors[4])
    ax.set_title('Arm Length', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='units'); ax.grid(alpha=0.3)

    fig.suptitle('Jellyfish GA — Evolution Summary\n'
                 '(shaded band = population IQR, line = best individual)',
                 fontsize=13, fontweight='bold', y=1.02)
    p = os.path.join(out_dir, f"plot_summary_{timestamp}.png")
    fig.savefig(p, dpi=150, bbox_inches='tight'); plt.close(fig); paths.append(p)

    print("Plots saved:")
    for pp in paths[:-1]:
        print(f"  {pp}")
    print(f"  {paths[-1]}  ← summary panel")


# ============================================================
#  MAIN
# ============================================================

def find_latest_csv(folder):
    pattern = os.path.join(folder, "evolution_*.csv")
    files   = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(script_dir, csv_path)
    else:
        csv_path = find_latest_csv(script_dir)
        if csv_path is None:
            print("No evolution_*.csv found. Pass a path as argument.")
            sys.exit(1)
        print(f"Using latest CSV: {os.path.basename(csv_path)}")

    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)

    timestamp = os.path.basename(csv_path).replace("evolution_", "").replace(".csv", "")

    print(f"Loading {os.path.basename(csv_path)}...")
    history = load_csv(csv_path)
    n_gens  = len(history['best'])
    n_pop   = len(history['all_fitnesses'][0]) if history['all_fitnesses'] else 0
    print(f"  {n_gens} generations, {n_pop} individuals each")

    plots_dir = os.path.join(script_dir, f"plots_{timestamp}")
    os.makedirs(plots_dir, exist_ok=True)

    print("Generating plots...")
    save_plots(history, plots_dir, timestamp)


if __name__ == '__main__':
    main()
