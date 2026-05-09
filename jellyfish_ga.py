"""
jellyfish_ga.py — Genetic Algorithm for fixed-topology jellyfish (méduse)

Topology (Λ shape, bell at top, arms hanging below):

        MUSCLE(1)           ← bell apex, the single muscle node
       /         \
   arm_L(0)   arm_R(2)      ← arm endpoints

Genome: amplitude · period · duty_cycle · arm_angle · arm_length
Fitness: displacement^1.5 / (energy^0.5 + ε)
"""

import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys, csv, math, random, time, subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from multiprocessing import Pool, cpu_count

# ============================================================
#  PHYSICS
# ============================================================
FPS             = 120
RIGIDITY_BONE   = 0.5
RIGIDITY_MUSCLE = 0.1
DAMPING         = 0.7
SUBSTEPS        = 30
FLOW_COEF       = 8.0
FLOW_POWER      = 2
FLOW_MAX        = 0.3
DRAG            = 0.16
INERTIA_GAIN    = 0.4
INERTIA_DECAY   = 0.92
MAX_V           = 0.1
MAX_DIVERGE     = 20.0

# ============================================================
#  SIMULATION
# ============================================================
SIMULATION_DURATION = FPS * 15   # 15 s of physics
WARMUP_FRAMES       = FPS * 3    # first 3 s ignored for distance

# ============================================================
#  FITNESS
# ============================================================
FITNESS_DIST_EXP   = 1.5
FITNESS_ENERGY_EXP = 0.5
ENERGY_EPSILON     = 1.0
MIN_DISPLACEMENT   = 0.05
# ============================================================
#  GENOME
#  index: 0=amplitude  1=period  2=duty_cycle  3=arm_angle  4=arm_length
# ============================================================
GENOME_KEYS   = ['amplitude', 'period', 'duty_cycle', 'arm_angle', 'arm_length']
GENOME_IS_INT = [False,        True,     False,         False,       False]
GENOME_MIN    = np.array([0.05,  FPS//2,  0.05,  0.30,  0.30], dtype=np.float64)
GENOME_MAX    = np.array([2.00,  FPS*4,   0.95,  2.60,  1.50], dtype=np.float64) * 2 
# ============================================================
#  GA
# ============================================================
prop_elit = 0.05
prop_inject = 0.1
POP_SIZE             = 50
NUM_GENERATIONS      = 20
ELITE_COUNT          = int(POP_SIZE * prop_elit)
TOURNAMENT_SIZE      = 5
CROSSOVER_PROB       = 0.65
MUTATION_PROB        = 0.80
MUT_PARAM_PROB       = 0.70
MUTATION_SCALE_INIT  = 1.00
MUTATION_SCALE_FINAL = 0.04
RANDOM_INJECT        = int(POP_SIZE * prop_inject)
STAGNATION_LIMIT     = 15
STAGNATION_THRESHOLD = 1.005

# ============================================================
#  VIDEO
# ============================================================
WIDTH, HEIGHT = 1280, 720
ZOOM          = 100
VIDEO_FPS     = 30
FRAME_SKIP    = FPS // VIDEO_FPS

# ============================================================
#  PARALLEL
# ============================================================
NUM_WORKERS         = max(1, cpu_count() - 1)
EVAL_PROGRESS_CHUNK = 10

# Fixed node indices for the 3-node medusa
_M  = 1   # MUSCLE
_RL = 0   # left  arm
_RR = 2   # right arm


# ============================================================
#  PROGRESS HELPERS
# ============================================================

def fmt_time(s):
    s = int(s)
    if s < 3600:
        return f"{s//60:02d}:{s%60:02d}"
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

def progress_bar(cur, tot, w=28):
    f = int(w * cur / max(tot, 1))
    return f"[{'█'*f}{'░'*(w-f)}] {100*cur/max(tot,1):5.1f}%"

def clear_line():
    sys.stdout.write("\r" + " " * 130 + "\r")
    sys.stdout.flush()


# ============================================================
#  GENOME UTILITIES
# ============================================================

def random_genome():
    g = np.random.uniform(GENOME_MIN, GENOME_MAX)
    for i, is_int in enumerate(GENOME_IS_INT):
        if is_int:
            g[i] = float(round(g[i]))
    return g

def clip_genome(g):
    g = np.clip(g, GENOME_MIN, GENOME_MAX)
    for i, is_int in enumerate(GENOME_IS_INT):
        if is_int:
            g[i] = float(round(g[i]))
    return g

def genome_to_dict(g):
    return {k: (int(g[i]) if GENOME_IS_INT[i] else float(g[i]))
            for i, k in enumerate(GENOME_KEYS)}


# ============================================================
#  MEDUSA BUILDER
# ============================================================

def build_medusa(g):
    gd      = genome_to_dict(g)
    alpha   = gd['arm_angle']
    arm_len = gd['arm_length']
    half_a  = alpha / 2.0

    # Arm unit vectors pointing downward from MUSCLE
    arm_L_dir = np.array([-math.sin(half_a), -math.cos(half_a)])
    arm_R_dir = np.array([+math.sin(half_a), -math.cos(half_a)])

    MUSCLE_pos = np.array([0.0, 0.0])
    arm_L_pos  = arm_L_dir * arm_len
    arm_R_pos  = arm_R_dir * arm_len

    nodes_xy  = np.array([arm_L_pos, MUSCLE_pos, arm_R_pos], dtype=np.float64)
    edges     = np.array([[0,1],[1,2]], dtype=np.int32)
    edge_rest = np.array([arm_len, arm_len], dtype=np.float64)

    # Base angle at MUSCLE between the two arm directions
    base_angle = (math.atan2(float(arm_R_dir[1]), float(arm_R_dir[0]))
                - math.atan2(float(arm_L_dir[1]), float(arm_L_dir[0])))

    return {
        'genome'        : g.copy(),
        'nodes_xy'      : nodes_xy,
        'nodes_v'       : np.zeros((3, 2), dtype=np.float64),
        'nodes_inertia' : np.zeros((3, 2), dtype=np.float64),
        'edges'         : edges,
        'edge_rest'     : edge_rest,
        'base_angle'    : base_angle,
        'target_angle'  : base_angle,
        'amplitude'     : float(gd['amplitude']),
        'period'        : int(gd['period']),
        'duty_cycle'    : float(gd['duty_cycle']),
        'energy_muscle' : 0.0,
        'energy_drag'   : 0.0,
    }


# ============================================================
#  PHYSICS ENGINE
# ============================================================

def physics_step(c, frame):
    xy      = c['nodes_xy']
    v       = c['nodes_v']
    inertia = c['nodes_inertia']
    edges   = c['edges']
    rest    = c['edge_rest']
    a_idx   = edges[:, 0]
    b_idx   = edges[:, 1]

    # 1 — Muscle target angle
    t_in  = frame % c['period']
    c_dur = c['duty_cycle'] * c['period']
    o_dur = c['period'] - c_dur
    if t_in < c_dur:
        t_val = -math.cos(math.pi * t_in / max(c_dur, 1e-9))
    else:
        t_val =  math.cos(math.pi * (t_in - c_dur) / max(o_dur, 1e-9))
    c['target_angle'] = c['base_angle'] + t_val * c['amplitude']

    # 2 — Edge spring forces (per-edge rest length)
    d     = xy[b_idx] - xy[a_idx]
    dist  = np.linalg.norm(d, axis=1)
    ds    = np.where(dist > 0, dist, 1e-3)
    delta = (ds - rest) / ds
    f     = d * (delta * RIGIDITY_BONE)[:, None]
    np.add.at(v, a_idx,  f)
    np.add.at(v, b_idx, -f)

    # 3 — Muscle torque (single muscle at node _M)
    dl     = xy[_RL] - xy[_M]
    dr     = xy[_RR] - xy[_M]
    dist_l = max(0.2, math.sqrt(float(dl @ dl)))
    dist_r = max(0.2, math.sqrt(float(dr @ dr)))
    ang_l  = math.atan2(float(dl[1]), float(dl[0]))
    ang_r  = math.atan2(float(dr[1]), float(dr[0]))
    cur    = ang_r - ang_l
    diff   = (c['target_angle'] - cur + math.pi) % (2*math.pi) - math.pi
    torque = diff * RIGIDITY_MUSCLE
    c['energy_muscle'] += RIGIDITY_MUSCLE * diff * diff

    fl_x =  math.sin(ang_l) * torque / dist_l
    fl_y = -math.cos(ang_l) * torque / dist_l
    fr_x = -math.sin(ang_r) * torque / dist_r
    fr_y =  math.cos(ang_r) * torque / dist_r

    v[_RL, 0] += fl_x;             v[_RL, 1] += fl_y
    v[_RR, 0] += fr_x;             v[_RR, 1] += fr_y
    v[_M,  0] -= (fl_x + fr_x);    v[_M,  1] -= (fl_y + fr_y)

    # 4 — Node-segment collisions (vectorised, 5×4 pairs)
    P1   = xy[a_idx]; P2 = xy[b_idx]; AB = P2 - P1
    AB_sq  = np.sum(AB*AB, axis=1)
    AB_ss  = np.where(AB_sq > 0, AB_sq, 1.0)
    AP     = xy[:, None, :] - P1[None]
    t_p    = np.clip(np.sum(AP * AB[None], axis=2) / AB_ss, 0.0, 1.0)
    closest = P1[None] + t_p[:, :, None] * AB[None]
    diff_v  = xy[:, None, :] - closest
    dist_c  = np.linalg.norm(diff_v, axis=2)

    ni     = np.arange(3)
    not_ep = (ni[:, None] != a_idx[None]) & (ni[:, None] != b_idx[None])
    active = not_ep & (dist_c < 0.2) & (dist_c > 0)
    if active.any():
        ds2   = np.where(dist_c > 0, dist_c, 1e-3)
        pmag  = (0.2 - dist_c) * 0.04
        force = diff_v / ds2[:, :, None] * pmag[:, :, None]
        force = np.where(active[:, :, None], force, 0.0)
        v += force.sum(axis=1)
        np.subtract.at(v, a_idx, (force * (1-t_p)[:,:,None]).sum(axis=0))
        np.subtract.at(v, b_idx, (force *    t_p[:,:,None]).sum(axis=0))

    # 5 — Drag (anisotropic, per edge)
    d2    = xy[b_idx] - xy[a_idx]
    avg_v = 0.5 * (v[a_idx] + v[b_idx])
    le    = np.linalg.norm(d2, axis=1)
    ls    = np.where(le > 0, le, 1e-3)
    tan   = d2 / ls[:, None]
    nor   = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
    v_par  = np.sum(avg_v * tan, axis=1)
    v_perp = np.sum(avg_v * nor, axis=1)
    drag   = (v_par[:, None]*tan + v_perp[:, None]*nor) * DRAG
    c['energy_drag'] += float(np.sum(DRAG * (v_par**2 + v_perp**2)))
    np.subtract.at(v, a_idx, drag)
    np.subtract.at(v, b_idx, drag)

    # 6 — Jet propulsion (fluid flow from single muscle)
    v1 = xy[_RL] - xy[_M]
    v2 = xy[_RR] - xy[_M]
    l1 = math.sqrt(float(v1 @ v1))
    l2 = math.sqrt(float(v2 @ v2))
    if l1 > 0 and l2 > 0:
        v1n = v1 / l1; v2n = v2 / l2
        dot_a = float(np.clip(v1n @ v2n, -1.0, 1.0))
        eff   = math.sin(math.acos(dot_a))
        rel_v = v[_RL] - v[_RR]
        dp    = float((xy[_RL] - xy[_RR]) @ rel_v)
        mid   = 0.5 * (v1 + v2)
        dm    = max(0.1, math.sqrt(float(mid @ mid)))
        fmag  = min((abs(dp)**FLOW_POWER) * FLOW_COEF * eff, FLOW_MAX)
        sign  = -1.0 if dp < 0 else 1.0
        force = (mid / dm) * (sign * fmag)
        v[_M]       += force
        inertia[_M] += force * INERTIA_GAIN

    # 7 — Integrate
    np.clip(v, -MAX_V, MAX_V, out=v)
    xy += v
    v  *= DAMPING


def creature_update(c, frame):
    for _ in range(SUBSTEPS):
        physics_step(c, frame)


# ============================================================
#  FITNESS EVALUATION
# ============================================================

def _evaluate(genome):
    """Returns (fitness, displacement, total_energy)."""
    c = build_medusa(genome)
    start_pos = np.zeros(2)

    for frame in range(SIMULATION_DURATION):
        creature_update(c, frame)
        c['nodes_v']       += c['nodes_inertia']
        c['nodes_inertia'] *= INERTIA_DECAY

        if (np.any(np.abs(c['nodes_xy']) > MAX_DIVERGE) or
                np.any(np.isnan(c['nodes_xy']))):
            return 0.0, 0.0, 0.0

        if frame == WARMUP_FRAMES:
            start_pos = c['nodes_xy'].mean(axis=0).copy()

    end_pos      = c['nodes_xy'].mean(axis=0)
    displacement = float(np.linalg.norm(end_pos - start_pos))
    energy       = c['energy_muscle'] + c['energy_drag']

    if displacement < MIN_DISPLACEMENT:
        return 0.0, float(displacement), float(energy)

    fitness = (displacement ** FITNESS_DIST_EXP) / (energy ** FITNESS_ENERGY_EXP + ENERGY_EPSILON)
    return float(fitness), float(displacement), float(energy)


def _eval_worker(args):
    idx, genome = args
    f, d, e = _evaluate(genome)
    return idx, f, d, e


def evaluate_population(pool, genomes, gen):
    total = len(genomes)
    fitnesses = [0.0] * total
    disps     = [0.0] * total
    energies  = [0.0] * total
    start     = time.time()
    done      = 0
    chunk     = max(1, total // (NUM_WORKERS * 8))

    for idx, f, d, e in pool.imap_unordered(_eval_worker,
                                             list(enumerate(genomes)),
                                             chunksize=chunk):
        fitnesses[idx] = f
        disps[idx]     = d
        energies[idx]  = e
        done += 1
        if done % EVAL_PROGRESS_CHUNK == 0 or done == total:
            elapsed = time.time() - start
            eta     = (total - done) / max(done / max(elapsed, 1e-6), 1e-6)
            sys.stdout.write(
                f"\r  Eval G{gen+1:2d} {progress_bar(done, total)}"
                f"  {done}/{total}  {fmt_time(elapsed)} → ETA {fmt_time(eta)}"
            )
            sys.stdout.flush()
    clear_line()
    return fitnesses, disps, energies


# ============================================================
#  GENETIC OPERATORS
# ============================================================

def _mut_scale(gen):
    t = gen / max(NUM_GENERATIONS - 1, 1)
    return MUTATION_SCALE_INIT * (1 - t) + MUTATION_SCALE_FINAL * t


def mutate(g, gen):
    g      = g.copy()
    scale  = _mut_scale(gen)
    sigmas = (GENOME_MAX - GENOME_MIN) * 0.10 * scale
    for i in range(len(g)):
        if random.random() < MUT_PARAM_PROB:
            g[i] += random.gauss(0, float(sigmas[i]))
    return clip_genome(g)


def crossover(ga, gb):
    alpha = random.uniform(0.3, 0.7)
    return clip_genome(alpha * ga + (1.0 - alpha) * gb)


def tournament_select(genomes, fitnesses, k=1):
    out = []
    n   = len(genomes)
    for _ in range(k):
        idxs   = random.sample(range(n), min(TOURNAMENT_SIZE, n))
        winner = max(idxs, key=lambda i: fitnesses[i])
        out.append(genomes[winner].copy())
    return out[0] if k == 1 else out


# ============================================================
#  NEXT GENERATION BUILDER
# ============================================================

def build_next_generation(genomes, fitnesses, gen):
    sorted_idx = np.argsort(-np.array(fitnesses))
    next_pop   = []

    for i in sorted_idx[:ELITE_COUNT]:
        next_pop.append(genomes[int(i)].copy())

    n_offspring = POP_SIZE - ELITE_COUNT - RANDOM_INJECT
    while len(next_pop) < ELITE_COUNT + n_offspring:
        if random.random() < CROSSOVER_PROB:
            pa, pb = tournament_select(genomes, fitnesses, k=2)
            child  = crossover(pa, pb)
        else:
            child  = tournament_select(genomes, fitnesses).copy()
        if random.random() < MUTATION_PROB:
            child = mutate(child, gen)
        next_pop.append(child)

    for _ in range(RANDOM_INJECT):
        next_pop.append(random_genome())

    return next_pop[:POP_SIZE]


# ============================================================
#  VIDEO RENDERER
# ============================================================

def open_video(path):
    return subprocess.Popen(
        ['ffmpeg', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
         '-video_size', f'{WIDTH}x{HEIGHT}', '-framerate', str(VIDEO_FPS),
         '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
         '-preset', 'fast', '-crf', '20', path],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def _draw_mini_chart(surface, history, cur_gen_idx, x, y, sfont, w=200, h=120):
    import pygame
    bests = history['best']
    if not bests:
        return
    pygame.draw.rect(surface, (18, 22, 40), (x-4, y-22, w+8, h+32))
    surface.blit(sfont.render("Fitness (best/gen)", True, (120, 140, 165)), (x, y-18))
    max_f = max(bests) or 1.0
    bw    = max(1, w // max(len(bests), 1))
    for gi, bf in enumerate(bests):
        bh    = max(1, int(h * bf / max_f))
        color = (55, 215, 105) if gi == cur_gen_idx else (28, 88, 48)
        pygame.draw.rect(surface, color, (x + gi * bw, y + h - bh, max(bw-1, 1), bh))
    surface.blit(sfont.render(f"G1  →  G{len(bests)}", True, (75, 88, 110)),
                 (x, y + h + 4))


def render_generation(genome, gen_label, fitness, displacement, energy,
                      history, surface, font, ffmpeg_proc):
    import pygame
    c     = build_medusa(genome)
    gd    = genome_to_dict(genome)
    sfont = pygame.font.SysFont(None, 19)
    trail = []

    node_colors = [(110,195,255), (255,65,65), (110,195,255)]
    node_radii  = [8, 11, 8]

    for frame in range(SIMULATION_DURATION):
        creature_update(c, frame)
        c['nodes_v']       += c['nodes_inertia']
        c['nodes_inertia'] *= INERTIA_DECAY

        if frame % FRAME_SKIP != 0:
            continue

        xy       = c['nodes_xy']
        centroid = xy.mean(axis=0)
        trail.append(centroid.copy())
        if len(trail) > 250:
            trail.pop(0)

        cam_x = WIDTH  // 2 - centroid[0] * ZOOM
        cam_y = HEIGHT // 2 - centroid[1] * ZOOM

        surface.fill((11, 13, 22))

        # Grid
        for gx in range(int(cam_x) % ZOOM, WIDTH, ZOOM):
            pygame.draw.line(surface, (22, 28, 46), (gx, 0), (gx, HEIGHT))
        for gy in range(int(cam_y) % ZOOM, HEIGHT, ZOOM):
            pygame.draw.line(surface, (22, 28, 46), (0, gy), (WIDTH, gy))

        # Trail
        n_t = len(trail)
        for i in range(1, n_t):
            a = i / n_t
            col = (int(30*a), int(100*a), int(255*a))
            p1 = (int(trail[i-1][0]*ZOOM+cam_x), int(trail[i-1][1]*ZOOM+cam_y))
            p2 = (int(trail[i][0]  *ZOOM+cam_x), int(trail[i][1]  *ZOOM+cam_y))
            pygame.draw.line(surface, col, p1, p2, 2)

        # Edges
        for a, b in c['edges']:
            p1 = (int(xy[a,0]*ZOOM+cam_x), int(xy[a,1]*ZOOM+cam_y))
            p2 = (int(xy[b,0]*ZOOM+cam_x), int(xy[b,1]*ZOOM+cam_y))
            pygame.draw.line(surface, (70, 130, 240), p1, p2, 5)

        # Nodes
        for i in range(3):
            pos = (int(xy[i,0]*ZOOM+cam_x), int(xy[i,1]*ZOOM+cam_y))
            pygame.draw.circle(surface, node_colors[i], pos, node_radii[i])

        # HUD
        freq_hz = FPS / gd['period']
        hud = [
            f"Generation   {gen_label} / {NUM_GENERATIONS}",
            f"Fitness      {fitness:.5f}",
            f"Displacement {displacement:.3f} units",
            f"Energy       {energy:.3f}",
            "",
            "Genome:",
            f"Amplitude     {gd['amplitude']:.3f} rad",
            f"Frequency     {freq_hz:.2f} Hz  ({gd['period']} fr)",
            f"Duty cycle    {gd['duty_cycle']:.3f}  "
              + ('(fast close)' if gd['duty_cycle'] < 0.35 else
                 '(slow close)' if gd['duty_cycle'] > 0.65 else '(balanced)'),
            f"Arm angle     {math.degrees(gd['arm_angle']):.1f}°",
            f"Arm length    {gd['arm_length']:.3f}",
            "",
            f"Time  {frame // FPS:.0f} s / {SIMULATION_DURATION // FPS} s",
        ]
        for i, line in enumerate(hud):
            surf = font.render(line, True, (185, 202, 228))
            surface.blit(surf, (14, 14 + i * 26))

        # Mini chart
        cur_idx = len(history['best']) - 1
        _draw_mini_chart(surface, history, cur_idx,
                         WIDTH - 228, HEIGHT - 175, sfont)

        ffmpeg_proc.stdin.write(pygame.image.tobytes(surface, 'RGB'))


# ============================================================
#  MATPLOTLIB PLOTS
# ============================================================

def _param_band(ax, pop_vals_list, gens, best_line, color):
    """IQR shaded band + best line for one parameter."""
    for gi, vals in enumerate(pop_vals_list):
        if len(vals) == 0:
            continue
        q25, q75 = np.percentile(vals, [25, 75])
        ax.fill_between([gi, gi+1], [q25]*2, [q75]*2, alpha=0.22, color=color)
    ax.plot(gens, best_line, color=color, lw=2, label='Best')
    ax.legend(fontsize=8)


def save_plots(history, script_dir, timestamp):
    gens = list(range(len(history['best'])))
    if not gens:
        return

    pb  = np.array(history['best_genome'])   # (n_gens, 5)
    ag  = history['all_genomes']             # list of (pop,5) arrays
    af  = [np.array(x) for x in history['all_fitnesses']]
    ad  = [np.array(x) for x in history['all_displacements']]
    ae  = [np.array(x) for x in history['all_energies']]

    # arm_angle in degrees for display
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
    p = os.path.join(script_dir, f"plot_fitness_{timestamp}.png")
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
    p = os.path.join(script_dir, f"plot_params_{timestamp}.png")
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
    p = os.path.join(script_dir, f"plot_exploration_{timestamp}.png")
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
    p = os.path.join(script_dir, f"plot_pareto_{timestamp}.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    # ── 5. Summary panel 2×3 ─────────────────────────────────────────
    fig = plt.figure(figsize=(18, 10))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.44, wspace=0.34)

    # [0,0] Fitness evolution
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(gens, history['best'], '#2ecc71', lw=2, marker='o', ms=3, label='Best')
    ax.plot(gens, history['avg'],  '#3498db', lw=1.5, ls='--', label='Avg')
    ax.plot(gens, history['min'],  '#e74c3c', lw=1.5, ls=':',  label='Min')
    ax.fill_between(gens, history['avg'], history['best'], alpha=0.12, color='#2ecc71')
    ax.set_title('Fitness Evolution', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='Fitness')
    ax.legend(fontsize=9); ax.grid(alpha=0.3); ax.set_ylim(bottom=0)

    # [0,1] Amplitude
    ax = fig.add_subplot(gs[0, 1])
    _param_band(ax, pop_vals(0), gens, pb_deg[:, 0], colors[0])
    ax.set_title('Amplitude (rad)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='rad'); ax.grid(alpha=0.3)

    # [0,2] Duty cycle
    ax = fig.add_subplot(gs[0, 2])
    _param_band(ax, pop_vals(2), gens, pb_deg[:, 2], colors[2])
    ax.set_title('Duty Cycle', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation'); ax.grid(alpha=0.3)

    # [1,0] Arm angle
    ax = fig.add_subplot(gs[1, 0])
    _param_band(ax, pop_vals(3), gens, pb_deg[:, 3], colors[3])
    ax.set_title('Arm Angle (°)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='degrees'); ax.grid(alpha=0.3)

    # [1,1] Frequency
    ax = fig.add_subplot(gs[1, 1])
    best_hz = FPS / pb[:, 1]
    pop_hz  = [FPS / g[:, 1] for g in ag]
    _param_band(ax, pop_hz, gens, best_hz, colors[1])
    ax.set_title('Frequency (Hz)', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='Hz'); ax.grid(alpha=0.3)

    # [1,2] Arm length
    ax = fig.add_subplot(gs[1, 2])
    _param_band(ax, pop_vals(4), gens, pb_deg[:, 4], colors[4])
    ax.set_title('Arm Length', fontweight='bold', fontsize=11)
    ax.set(xlabel='Generation', ylabel='units'); ax.grid(alpha=0.3)

    fig.suptitle('Jellyfish GA — Evolution Summary\n'
                 '(shaded band = population IQR, line = best individual)',
                 fontsize=13, fontweight='bold', y=1.02)
    p = os.path.join(script_dir, f"plot_summary_{timestamp}.png")
    fig.savefig(p, dpi=150, bbox_inches='tight'); plt.close(fig); paths.append(p)

    print("  Plots saved:")
    for pp in paths[:-1]:
        print(f"    {pp}")
    print(f"    {paths[-1]}  ← summary panel")


# ============================================================
#  CSV EXPORT
# ============================================================

def save_csv(history, script_dir, timestamp, silent=False):
    path = os.path.join(script_dir, f"evolution_{timestamp}.csv")
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['gen', 'best_fitness', 'avg_fitness', 'min_fitness',
                         'best_energy', 'avg_energy', 'min_energy',
                         'best_distance', 'avg_distance', 'min_distance',
                         'member', 'amplitude', 'period', 'duty_cycle',
                         'arm_angle_deg', 'arm_length',
                         'member_fitness', 'member_distance', 'member_energy'])
        for i, genomes in enumerate(history['all_genomes']):
            fitnesses = history['all_fitnesses'][i]
            disps     = history['all_displacements'][i]
            energies  = history['all_energies'][i]
            gen_summary = [
                i+1,
                f"{history['best'][i]:.6f}",
                f"{history['avg'][i]:.6f}",
                f"{history['min'][i]:.6f}",
                f"{max(energies):.6f}",
                f"{sum(energies)/len(energies):.6f}",
                f"{min(energies):.6f}",
                f"{max(disps):.6f}",
                f"{sum(disps)/len(disps):.6f}",
                f"{min(disps):.6f}",
            ]
            for j, g in enumerate(genomes):
                gd = genome_to_dict(g)
                writer.writerow(gen_summary + [
                    j+1,
                    f"{gd['amplitude']:.4f}",
                    gd['period'],
                    f"{gd['duty_cycle']:.4f}",
                    f"{math.degrees(gd['arm_angle']):.2f}",
                    f"{gd['arm_length']:.4f}",
                    f"{fitnesses[j]:.6f}",
                    f"{disps[j]:.6f}",
                    f"{energies[j]:.6f}",
                ])
    if not silent:
        print(f"  CSV  saved: {path}")


# ============================================================
#  MAIN
# ============================================================

def main():
    import pygame
    total_start = time.time()

    print("=" * 72)
    print("  JELLYFISH GA  —  Fixed-topology méduse optimizer")
    print(f"  Population: {POP_SIZE}  |  Generations: {NUM_GENERATIONS}")
    print(f"  Workers: {NUM_WORKERS}  |  Substeps: {SUBSTEPS}  |  Sim: {SIMULATION_DURATION//FPS}s")
    print(f"  Genome bounds:")
    for i, k in enumerate(GENOME_KEYS):
        lo = math.degrees(GENOME_MIN[i]) if k == 'arm_angle' else GENOME_MIN[i]
        hi = math.degrees(GENOME_MAX[i]) if k == 'arm_angle' else GENOME_MAX[i]
        unit = '°' if k == 'arm_angle' else ('fr' if k == 'period' else '')
        print(f"    {k:<12} [{lo:.2f}, {hi:.2f}] {unit}")
    print(f"  Fitness: disp^{FITNESS_DIST_EXP} / (energy^{FITNESS_ENERGY_EXP} + {ENERGY_EPSILON})")
    print("=" * 72)

    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font    = pygame.font.SysFont(None, 26)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp  = time.strftime("%Y%m%d_%H%M%S")
    video_dir  = os.path.join(script_dir, f"videos_{timestamp}")
    os.makedirs(video_dir, exist_ok=True)
    print(f"  Videos → {video_dir}/evolution_{timestamp}_genXXX.mp4\n")

    history = {
        'best': [], 'avg': [], 'min': [],
        'best_genome': [],
        'all_genomes': [], 'all_fitnesses': [],
        'all_displacements': [], 'all_energies': [],
    }

    print("[Init] Spawning initial population...", flush=True)
    population = [random_genome() for _ in range(POP_SIZE)]

    pool           = Pool(processes=NUM_WORKERS)
    best_ever      = 0.0
    best_g_ever    = population[0].copy()
    best_d_ever    = 0.0
    best_e_ever    = 0.0
    stagnation     = 0
    last_gen_done  = 0

    try:
        for gen in range(NUM_GENERATIONS):
            gen_start = time.time()
            print(f"{'─'*72}")
            print(f"  GENERATION {gen+1:2d} / {NUM_GENERATIONS}", flush=True)

            fitnesses, disps, energies = evaluate_population(pool, population, gen)

            fit_arr  = np.array(fitnesses)
            best_idx = int(np.argmax(fit_arr))
            best_f   = float(fit_arr[best_idx])
            avg_f    = float(fit_arr.mean())
            min_f    = float(fit_arr.min())
            best_g   = population[best_idx]
            best_d   = disps[best_idx]
            best_e   = energies[best_idx]

            improved = best_f > best_ever * STAGNATION_THRESHOLD
            if improved:
                best_ever   = best_f
                best_g_ever = best_g.copy()
                best_d_ever = best_d
                best_e_ever = best_e
                stagnation  = 0
                tag = " ★ new best"
            else:
                stagnation += 1
                tag = f"  [stagnating {stagnation}/{STAGNATION_LIMIT}]"

            history['best'].append(best_f)
            history['avg'].append(avg_f)
            history['min'].append(min_f)
            history['best_genome'].append(best_g.copy())
            history['all_genomes'].append(np.array(population))
            history['all_fitnesses'].append(list(fitnesses))
            history['all_displacements'].append(list(disps))
            history['all_energies'].append(list(energies))

            gd        = genome_to_dict(best_g)
            scale_now = _mut_scale(gen)
            nonzero   = int(np.sum(fit_arr > 0))

            print(f"  Best:  {best_f:.5f}{tag}")
            print(f"  Avg:   {avg_f:.5f}  |  Min: {min_f:.5f}  |  Active: {nonzero}/{POP_SIZE}")
            print(f"  Genome: ampl={gd['amplitude']:.3f}  "
                  f"period={gd['period']}fr({FPS/gd['period']:.2f}Hz)  "
                  f"dc={gd['duty_cycle']:.3f}  "
                  f"angle={math.degrees(gd['arm_angle']):.1f}°  "
                  f"len={gd['arm_length']:.3f}")
            print(f"  disp={best_d:.3f}  mut_scale={scale_now:.3f}  "
                  f"gen_time={fmt_time(time.time()-gen_start)}", flush=True)

            print(f"  Rendering...", end='', flush=True)
            gen_video_path = os.path.join(video_dir, f"evolution_{timestamp}_gen{gen+1:03d}.mp4")
            gen_proc = open_video(gen_video_path)
            render_generation(best_g, gen+1, best_f, best_d, best_e,
                              history, surface, font, gen_proc)
            gen_proc.stdin.close(); gen_proc.wait()
            print(f" done → {os.path.basename(gen_video_path)}")
            save_csv(history, script_dir, timestamp, silent=True)

            last_gen_done = gen

            if stagnation >= STAGNATION_LIMIT:
                print(f"\n  *** Early stop: no improvement for {STAGNATION_LIMIT} generations ***")
                break

            if gen == NUM_GENERATIONS - 1:
                break

            population = build_next_generation(population, fitnesses, gen)

        # Final champion render (best ever, may differ from last gen best)
        print(f"\n{'═'*72}")
        print("  FINAL CHAMPION — rendering best-ever genome...")
        champ_video_path = os.path.join(video_dir, f"evolution_{timestamp}_champion.mp4")
        champ_proc = open_video(champ_video_path)
        render_generation(best_g_ever, f"{last_gen_done+1}★", best_ever, best_d_ever, best_e_ever,
                          history, surface, font, champ_proc)
        champ_proc.stdin.close(); champ_proc.wait()
        print(f"  Champion video → {os.path.basename(champ_video_path)}")
        print(f"  Best ever fitness: {best_ever:.5f}")
        gd = genome_to_dict(best_g_ever)
        print(f"  Champion genome:")
        print(f"    amplitude  = {gd['amplitude']:.4f} rad")
        print(f"    period     = {gd['period']} frames  ({FPS/gd['period']:.3f} Hz)")
        print(f"    duty_cycle = {gd['duty_cycle']:.4f}  "
              f"({'fast-close jet' if gd['duty_cycle'] < 0.3 else 'balanced'})")
        print(f"    arm_angle  = {math.degrees(gd['arm_angle']):.2f}°")
        print(f"    arm_length = {gd['arm_length']:.4f}")

    finally:
        pool.close(); pool.join()
        pygame.quit()

    elapsed = time.time() - total_start
    save_csv(history, script_dir, timestamp)

    print(f"\n{'═'*72}")
    print("  EVOLUTION COMPLETE")
    print(f"  Total time : {fmt_time(elapsed)}")
    print(f"  Videos     : {video_dir}/")
    print(f"{'═'*72}")


if __name__ == '__main__':
    main()