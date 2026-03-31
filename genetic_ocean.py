import pygame
import math
import random
import copy
import time
import subprocess
import os
import struct

# ============================================================
#  CONFIGURATION
# ============================================================
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 0.5
RIGIDITY_MUSCLE = 0.1
DAMPING = 0.7
SUBSTEPS = 50
FLOW_COEF = 8.0
FLOW_POWER = 2
FLOW_MAX = 0.3
DRAG = 0.16
INERTIA_GAIN = 0.4
INERTIA_DECAY = 0.92

# --- Genetic Algorithm ---
POP_SIZE = 100
NUM_GENERATIONS = 5
ELITE_COUNT = 50         # Selected via roulette
OFFSPRING_COUNT = 50     # Generated via crossover + mutation
MUTATION_PROBABILITY = 0.5 # Chance that an offspring is mutated
SIMULATION_DURATION = FPS * 10  # 10 seconds of physics per creature
WARMUP_FRAMES = FPS * 2        # Ignore first 2s for distance measurement
DISTANCE_DIVERGE = 8.0         # Discard if distance exceeds this

# --- Video ---
VIDEO_FPS = 30  # Output video framerate (lower than sim FPS to keep file small)
FRAME_SKIP = FPS // VIDEO_FPS  # Only record 1 frame every FRAME_SKIP sim frames

# ============================================================
#  CORE CLASSES
# ============================================================

class Node:
    def __init__(self, x, y, is_muscle=False, amplitude=0.3, phase=0.0,
                 period=120, duty_cycle=0.5):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.inertia_vx, self.inertia_vy = 0.0, 0.0
        self.is_muscle = is_muscle
        self.amplitude = amplitude
        self.phase = phase
        self.period = period
        self.duty_cycle = duty_cycle
        self.base_angle = 0.0
        self.target_angle = 0.0
        self.nodes_ref = None


class Edge:
    def __init__(self, n_a, n_b):
        self.n_a = n_a
        self.n_b = n_b
        self.length = 1.0


class Creature:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    def update(self, frame_count):
        for _ in range(SUBSTEPS):
            self._physics_step(frame_count)

    def _apply_collisions(self):
        collision_radius = 0.2
        repulsion_strength = 0.04
        for i, n in enumerate(self.nodes):
            for e in self.edges:
                if i == e.n_a or i == e.n_b:
                    continue
                n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
                ab = pygame.Vector2(n2.x - n1.x, n2.y - n1.y)
                ap = pygame.Vector2(n.x - n1.x, n.y - n1.y)
                seg_len_sq = ab.length_squared()
                if seg_len_sq == 0:
                    continue
                t = ap.dot(ab) / seg_len_sq
                t = max(0, min(1, t))
                closest = pygame.Vector2(n1.x + t * ab.x, n1.y + t * ab.y)
                dist_vec = pygame.Vector2(n.x - closest.x, n.y - closest.y)
                distance = dist_vec.length()
                if distance < collision_radius:
                    push_mag = (collision_radius - distance) * repulsion_strength
                    force = (dist_vec / (distance + 0.001)) * push_mag
                    n.vx += force.x;  n.vy += force.y
                    n1.vx -= force.x * (1 - t); n1.vy -= force.y * (1 - t)
                    n2.vx -= force.x * t;        n2.vy -= force.y * t

    def _physics_step(self, frame_count):
        for n in self.nodes:
            if n.is_muscle:
                phase_offset = n.phase / (2 * math.pi) * n.period
                t_in_cycle = (frame_count + phase_offset) % n.period
                close_dur = n.duty_cycle * n.period
                open_dur = n.period - close_dur
                if t_in_cycle < close_dur:
                    p = t_in_cycle / close_dur
                    t = -math.cos(math.pi * p)
                else:
                    p = (t_in_cycle - close_dur) / open_dur
                    t = math.cos(math.pi * p)
                n.target_angle = n.base_angle + t * n.amplitude

        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2) or 0.001
            delta = (dist - 1.0) / dist
            fx, fy = dx * delta * RIGIDITY_BONE, dy * delta * RIGIDITY_BONE
            n1.vx += fx; n1.vy += fy
            n2.vx -= fx; n2.vy -= fy

        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref
                dx_l, dy_l = n_l.x - n.x, n_l.y - n.y
                dx_r, dy_r = n_r.x - n.x, n_r.y - n.y
                dist_l = max(0.2, math.sqrt(dx_l**2 + dy_l**2))
                dist_r = max(0.2, math.sqrt(dx_r**2 + dy_r**2))
                angle_l = math.atan2(dy_l, dx_l)
                angle_r = math.atan2(dy_r, dx_r)
                current_angle = angle_r - angle_l
                diff = (n.target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
                torque_force = diff * RIGIDITY_MUSCLE
                fl_x = math.sin(angle_l) * torque_force / dist_l
                fl_y = -math.cos(angle_l) * torque_force / dist_l
                fr_x = -math.sin(angle_r) * torque_force / dist_r
                fr_y = math.cos(angle_r) * torque_force / dist_r
                n_l.vx += fl_x; n_l.vy += fl_y
                n_r.vx += fr_x; n_r.vy += fr_y
                n.vx -= (fl_x + fr_x); n.vy -= (fl_y + fr_y)

        self._apply_collisions()

        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            avg_vx = (n1.vx + n2.vx) / 2
            avg_vy = (n1.vy + n2.vy) / 2
            dx, dy = n2.x - n1.x, n2.y - n1.y
            length = math.sqrt(dx**2 + dy**2) or 0.001
            tx, ty = dx / length, dy / length
            nx, ny = -ty, tx
            v_par = avg_vx * tx + avg_vy * ty
            v_perp = avg_vx * nx + avg_vy * ny
            drag_x = (v_par * tx + v_perp * nx) * DRAG
            drag_y = (v_par * ty + v_perp * ny) * DRAG
            n1.vx -= drag_x; n1.vy -= drag_y
            n2.vx -= drag_x; n2.vy -= drag_y

        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref
                v1 = pygame.Vector2(n_l.x - n.x, n_l.y - n.y)
                v2 = pygame.Vector2(n_r.x - n.x, n_r.y - n.y)
                if v1.length() > 0 and v2.length() > 0:
                    dot_angle = v1.normalize().dot(v2.normalize())
                    dot_angle = max(-1.0, min(1.0, dot_angle))
                    angle_interne = math.acos(dot_angle)
                    efficiency = math.sin(angle_interne)
                    rel_vx = n_l.vx - n_r.vx
                    rel_vy = n_l.vy - n_r.vy
                    dot_product = ((n_l.x - n_r.x) * rel_vx +
                                   (n_l.y - n_r.y) * rel_vy)
                    mid_x = (v1.x + v2.x) / 2
                    mid_y = (v1.y + v2.y) / 2
                    dist = math.sqrt(mid_x**2 + mid_y**2) or 0.1
                    if dot_product < 0:
                        push_force = min((abs(dot_product) ** FLOW_POWER) *
                                         FLOW_COEF * efficiency, FLOW_MAX)
                        fx = -(mid_x / dist) * push_force
                        fy = -(mid_y / dist) * push_force
                    else:
                        suck_force = min((abs(dot_product) ** FLOW_POWER) *
                                         FLOW_COEF * efficiency, FLOW_MAX)
                        fx = (mid_x / dist) * suck_force
                        fy = (mid_y / dist) * suck_force
                    n.vx += fx; n.vy += fy
                    n.inertia_vx += fx * INERTIA_GAIN
                    n.inertia_vy += fy * INERTIA_GAIN

        max_v = 0.1
        for n in self.nodes:
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING


# ============================================================
#  CREATURE GENERATION / MUTATION / CROSSOVER
# ============================================================

def random_num_nodes():
    choices = list(range(3, 11))
    weights = [math.exp(-1.4 * i) for i in range(len(choices))]
    return random.choices(choices, weights=weights)[0]


def _build_adjacency(nodes, edges):
    connection_count = [0] * len(nodes)
    adj_list = [[] for _ in range(len(nodes))]
    for e in edges:
        connection_count[e.n_a] += 1
        connection_count[e.n_b] += 1
        adj_list[e.n_a].append(e.n_b)
        adj_list[e.n_b].append(e.n_a)
    return connection_count, adj_list


def _setup_muscle(n, adj_list, nodes, i):
    n.is_muscle = True
    n.amplitude = random.uniform(0.1, 1.0)
    n.phase = random.uniform(0, 2 * math.pi)
    n.period = random.randint(FPS, FPS * 5)
    n.duty_cycle = random.uniform(0.1, 0.4)
    ref_indices = adj_list[i][:2]
    n.nodes_ref = (nodes[ref_indices[0]], nodes[ref_indices[1]])
    angle1 = math.atan2(n.nodes_ref[0].y - n.y, n.nodes_ref[0].x - n.x)
    angle2 = math.atan2(n.nodes_ref[1].y - n.y, n.nodes_ref[1].x - n.x)
    n.base_angle = angle2 - angle1


def spawn_random_creature(num_nodes=None):
    if num_nodes is None:
        num_nodes = random_num_nodes()
    nodes = [Node(0, 0)]
    edges = []

    for i in range(1, num_nodes):
        connected = False
        for _ in range(200):
            parent_idx = random.randint(0, len(nodes) - 1)
            parent = nodes[parent_idx]
            angle = random.uniform(0, 2 * math.pi)
            new_x = parent.x + math.cos(angle)
            new_y = parent.y + math.sin(angle)
            if not any(math.sqrt((new_x - n.x)**2 + (new_y - n.y)**2) < 0.5
                       for n in nodes):
                nodes.append(Node(new_x, new_y))
                edges.append(Edge(parent_idx, i))
                connected = True
                break
        if not connected:
            nodes.append(Node(nodes[-1].x + 1.0, nodes[-1].y))
            edges.append(Edge(len(nodes) - 2, len(nodes) - 1))

    connection_count, adj_list = _build_adjacency(nodes, edges)
    for i, n in enumerate(nodes):
        if connection_count[i] >= 2:
            _setup_muscle(n, adj_list, nodes, i)
    return Creature(nodes, edges)


def recenter(creature):
    cx = sum(n.x for n in creature.nodes) / len(creature.nodes)
    cy = sum(n.y for n in creature.nodes) / len(creature.nodes)
    for n in creature.nodes:
        n.x -= cx; n.y -= cy


def reset_velocities(creature):
    for n in creature.nodes:
        n.vx = n.vy = 0.0
        n.inertia_vx = n.inertia_vy = 0.0


def centroid(creature):
    cx = sum(n.x for n in creature.nodes) / len(creature.nodes)
    cy = sum(n.y for n in creature.nodes) / len(creature.nodes)
    return cx, cy


def deep_copy_creature(creature):
    new_nodes = []
    for n in creature.nodes:
        nn = Node(n.x, n.y, n.is_muscle, n.amplitude, n.phase,
                  n.period, n.duty_cycle)
        nn.vx, nn.vy = n.vx, n.vy
        nn.inertia_vx, nn.inertia_vy = n.inertia_vx, n.inertia_vy
        nn.base_angle = n.base_angle
        nn.target_angle = n.target_angle
        new_nodes.append(nn)

    new_edges = [Edge(e.n_a, e.n_b) for e in creature.edges]

    old_to_idx = {id(n): i for i, n in enumerate(creature.nodes)}
    for i, n in enumerate(creature.nodes):
        if n.is_muscle and n.nodes_ref:
            idx_a = old_to_idx[id(n.nodes_ref[0])]
            idx_b = old_to_idx[id(n.nodes_ref[1])]
            new_nodes[i].nodes_ref = (new_nodes[idx_a], new_nodes[idx_b])

    return Creature(new_nodes, new_edges)


def mutate(creature):
    c = deep_copy_creature(creature)
    nodes, edges = c.nodes, c.edges
    reset_velocities(c)

    muscle_nodes = [n for n in nodes if n.is_muscle and n.nodes_ref]

    if muscle_nodes:
        pool = (['amplitude'] * 3 + ['duty_cycle'] * 3 +
                ['phase_break'] * 2 + ['add_node'] * 4 +
                ['remove_node'] * 2)
    else:
        pool = ['add_node']

    choice = random.choice(pool)

    if choice == 'amplitude':
        n = random.choice(muscle_nodes)
        n.amplitude = max(0.05, min(2.0, n.amplitude + random.uniform(-0.3, 0.3)))

    elif choice == 'duty_cycle':
        n = random.choice(muscle_nodes)
        n.duty_cycle = max(0.05, min(0.95, n.duty_cycle + random.uniform(-0.15, 0.15)))

    elif choice == 'phase_break':
        n = random.choice(muscle_nodes)
        n.phase = (n.phase + random.uniform(0.2, math.pi)) % (2 * math.pi)

    elif choice == 'add_node':
        if len(nodes) < 10:
            parent_idx = random.randint(0, len(nodes) - 1)
            parent = nodes[parent_idx]
            new_idx = len(nodes)
            placed = False
            for _ in range(100):
                angle = random.uniform(0, 2 * math.pi)
                nx_ = parent.x + math.cos(angle)
                ny_ = parent.y + math.sin(angle)
                if not any(math.sqrt((nx_ - nd.x)**2 + (ny_ - nd.y)**2) < 0.5
                           for nd in nodes):
                    new_node = Node(nx_, ny_)
                    nodes.append(new_node)
                    edges.append(Edge(parent_idx, new_idx))
                    conn, adj = _build_adjacency(nodes, edges)
                    for j, nd in enumerate(nodes):
                        if conn[j] >= 2 and not nd.is_muscle:
                            _setup_muscle(nd, adj, nodes, j)
                    placed = True
                    break
            if not placed and muscle_nodes:
                n = random.choice(muscle_nodes)
                n.amplitude = max(0.05, min(2.0, n.amplitude + random.uniform(-0.2, 0.2)))
        else:
            if muscle_nodes:
                n = random.choice(muscle_nodes)
                n.amplitude = max(0.05, min(2.0, n.amplitude + random.uniform(-0.2, 0.2)))

    elif choice == 'remove_node':
        conn, adj = _build_adjacency(nodes, edges)
        leaves = [i for i in range(len(nodes)) if conn[i] == 1 and len(nodes) > 3]
        if leaves:
            victim = random.choice(leaves)
            edges = [e for e in edges if e.n_a != victim and e.n_b != victim]
            nodes.pop(victim)
            for e in edges:
                if e.n_a > victim: e.n_a -= 1
                if e.n_b > victim: e.n_b -= 1
            conn, adj = _build_adjacency(nodes, edges)
            for i, nd in enumerate(nodes):
                nd.nodes_ref = None
                nd.is_muscle = False
                if conn[i] >= 2:
                    _setup_muscle(nd, adj, nodes, i)
            c = Creature(nodes, edges)

    return c


def crossover(parent_a, parent_b):
    child = deep_copy_creature(parent_a)
    muscles_b = [n for n in parent_b.nodes if n.is_muscle and n.nodes_ref]
    muscles_child = [n for n in child.nodes if n.is_muscle and n.nodes_ref]

    for i, mc in enumerate(muscles_child):
        if i < len(muscles_b):
            mb = muscles_b[i]
            alpha = random.uniform(0.3, 0.7)
            mc.amplitude = alpha * mc.amplitude + (1 - alpha) * mb.amplitude
            mc.duty_cycle = alpha * mc.duty_cycle + (1 - alpha) * mb.duty_cycle
            mc.phase = alpha * mc.phase + (1 - alpha) * mb.phase
            mc.period = int(alpha * mc.period + (1 - alpha) * mb.period)

    reset_velocities(child)
    recenter(child)
    return child


# ============================================================
#  HEADLESS SIMULATION (no rendering — pure fitness eval)
# ============================================================

def evaluate_fitness(creature):
    c = deep_copy_creature(creature)
    recenter(c)
    reset_velocities(c)

    max_pos = 20.0
    start_cx, start_cy = 0.0, 0.0

    for frame in range(SIMULATION_DURATION):
        c.update(frame)
        for n in c.nodes:
            n.vx += n.inertia_vx
            n.vy += n.inertia_vy
            n.inertia_vx *= INERTIA_DECAY
            n.inertia_vy *= INERTIA_DECAY

        if any(abs(n.x) > max_pos or abs(n.y) > max_pos or
               math.isnan(n.x) or math.isnan(n.vx) for n in c.nodes):
            return 0.0

        if frame == WARMUP_FRAMES:
            start_cx, start_cy = centroid(c)

    end_cx, end_cy = centroid(c)
    dist = math.sqrt((end_cx - start_cx)**2 + (end_cy - start_cy)**2)
    return dist if dist <= DISTANCE_DIVERGE else 0.0


# ============================================================
#  ROULETTE WHEEL SELECTION
# ============================================================

def roulette_select(population, fitnesses, k):
    epsilon = 1e-4
    adjusted = [f + epsilon for f in fitnesses]
    total = sum(adjusted)
    probabilities = [a / total for a in adjusted]

    cumulative = []
    s = 0.0
    for p in probabilities:
        s += p
        cumulative.append(s)

    selected = []
    for _ in range(k):
        r = random.random()
        for i, c in enumerate(cumulative):
            if r <= c:
                selected.append(population[i])
                break
    return selected


# ============================================================
#  VIDEO RENDERER (off-screen pygame -> ffmpeg -> mp4)
# ============================================================

def open_video_writer(output_path):
    """Open an ffmpeg process that accepts raw RGBA frames on stdin."""
    cmd = [
        'ffmpeg', '-y',                          # overwrite output
        '-f', 'rawvideo',
        '-pixel_format', 'rgb24',
        '-video_size', f'{WIDTH}x{HEIGHT}',
        '-framerate', str(VIDEO_FPS),
        '-i', '-',                                # read from stdin
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',                    # compatibility
        '-preset', 'fast',
        '-crf', '23',
        output_path
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def render_creature_to_video(creature, generation, fitness, gen_stats,
                             surface, font, ffmpeg_proc):
    """
    Simulate creature for SIMULATION_DURATION frames, drawing to an
    off-screen pygame surface and piping every FRAME_SKIP-th frame
    to ffmpeg as raw RGB bytes.
    """
    c = deep_copy_creature(creature)
    recenter(c)
    reset_velocities(c)

    for frame in range(SIMULATION_DURATION):
        c.update(frame)
        for n in c.nodes:
            n.vx += n.inertia_vx
            n.vy += n.inertia_vy
            n.inertia_vx *= INERTIA_DECAY
            n.inertia_vy *= INERTIA_DECAY

        # Only render frames we actually write to the video
        if frame % FRAME_SKIP != 0:
            continue

        # --- Camera follows the creature ---
        cx, cy = centroid(c)
        cam_x = WIDTH // 2 - cx * ZOOM
        cam_y = HEIGHT // 2 - cy * ZOOM

        # --- Draw onto off-screen surface ---
        surface.fill((15, 15, 25))

        # Grid
        grid_offset_x = int(cam_x) % ZOOM
        grid_offset_y = int(cam_y) % ZOOM
        for x in range(grid_offset_x, WIDTH, ZOOM):
            pygame.draw.line(surface, (40, 40, 55), (x, 0), (x, HEIGHT))
        for y in range(grid_offset_y, HEIGHT, ZOOM):
            pygame.draw.line(surface, (40, 40, 55), (0, y), (WIDTH, y))

        # Edges
        for e in c.edges:
            n1, n2 = c.nodes[e.n_a], c.nodes[e.n_b]
            p1 = (int(n1.x * ZOOM + cam_x), int(n1.y * ZOOM + cam_y))
            p2 = (int(n2.x * ZOOM + cam_x), int(n2.y * ZOOM + cam_y))
            pygame.draw.line(surface, (100, 150, 255), p1, p2, 5)

        # Nodes
        for n in c.nodes:
            color = (255, 100, 100) if n.is_muscle else (255, 255, 255)
            pos = (int(n.x * ZOOM + cam_x), int(n.y * ZOOM + cam_y))
            pygame.draw.circle(surface, color, pos, 8)

        # HUD
        seconds_left = (SIMULATION_DURATION - frame) // FPS
        hud = [
            f"Generation: {generation} / {NUM_GENERATIONS}",
            f"Best fitness: {fitness:.4f} u",
            f"Nodes: {len(c.nodes)}  |  Edges: {len(c.edges)}",
            f"Time left: {seconds_left}s",
            "",
            f"Avg fitness: {gen_stats['avg']:.4f}",
            f"Min fitness: {gen_stats['min']:.4f}",
            f"Max fitness: {gen_stats['max']:.4f}",
        ]
        for i, line in enumerate(hud):
            surf = font.render(line, True, (200, 200, 200))
            surface.blit(surf, (12, 12 + i * 24))

        # --- Write frame to ffmpeg ---
        raw = pygame.image.tobytes(surface, 'RGB')
        ffmpeg_proc.stdin.write(raw)


# ============================================================
#  MAIN — GENETIC ALGORITHM
# ============================================================

def main():
    print("=" * 60)
    print("  GENETIC ALGORITHM — Marine Creatures")
    print(f"  Population: {POP_SIZE} | Generations: {NUM_GENERATIONS}")
    print(f"  Elite (roulette): {ELITE_COUNT} | Offspring: {OFFSPRING_COUNT}")
    print(f"  Mutation prob: {MUTATION_PROBABILITY:.0%}")
    print("=" * 60)

    # --- Setup pygame (off-screen only, no window) ---
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font = pygame.font.SysFont(None, 26)

    # --- Open video file ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(script_dir, "evolution.mp4")
    ffmpeg_proc = open_video_writer(video_path)
    print(f"\n  Video will be saved to: {video_path}\n")

    # --- Generation 0: random population ---
    print("[Gen 0] Spawning initial population...")
    population = [spawn_random_creature() for _ in range(POP_SIZE)]

    for gen in range(NUM_GENERATIONS):
        t0 = time.time()

        # --- Evaluate fitness (headless) ---
        fitnesses = []
        for idx, creature in enumerate(population):
            f = evaluate_fitness(creature)
            fitnesses.append(f)
            if (idx + 1) % 50 == 0:
                elapsed = time.time() - t0
                print(f"  [Gen {gen}] Evaluated {idx+1}/{POP_SIZE} "
                      f"({elapsed:.1f}s)")

        # --- Stats ---
        best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        best_fitness = fitnesses[best_idx]
        best_creature = population[best_idx]
        avg_fitness = sum(fitnesses) / len(fitnesses)
        min_fitness = min(fitnesses)

        elapsed = time.time() - t0
        print(f"\n  [Gen {gen}] Done in {elapsed:.1f}s  |  "
              f"Best: {best_fitness:.4f}  Avg: {avg_fitness:.4f}  "
              f"Min: {min_fitness:.4f}")

        gen_stats = {
            'avg': avg_fitness,
            'min': min_fitness,
            'max': best_fitness,
        }

        # --- Render best creature into the video ---
        print(f"  [Gen {gen}] Rendering best creature to video...")
        render_creature_to_video(best_creature, gen, best_fitness,
                                 gen_stats, surface, font, ffmpeg_proc)

        # --- Selection: roulette wheel ---
        elite = roulette_select(population, fitnesses, ELITE_COUNT)
        next_population = [deep_copy_creature(c) for c in elite]

        # --- Offspring: crossover + optional mutation ---
        for _ in range(OFFSPRING_COUNT):
            parents = roulette_select(population, fitnesses, 2)
            child = crossover(parents[0], parents[1])
            if random.random() < MUTATION_PROBABILITY:
                child = mutate(child)
            recenter(child)
            reset_velocities(child)
            next_population.append(child)

        population = next_population
        print(f"  [Gen {gen}] Next generation ready ({len(population)} "
              f"creatures)\n")

    # --- Final generation best ---
    print("Evaluating final generation...")
    fitnesses = [evaluate_fitness(c) for c in population]
    best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
    best_fitness = fitnesses[best_idx]
    avg_fitness = sum(fitnesses) / len(fitnesses)
    print(f"  Final best fitness: {best_fitness:.4f}")
    render_creature_to_video(
        population[best_idx], NUM_GENERATIONS, best_fitness,
        {'avg': avg_fitness, 'min': min(fitnesses), 'max': best_fitness},
        surface, font, ffmpeg_proc)

    # --- Close video ---
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    pygame.quit()

    print("\n" + "=" * 60)
    print("  EVOLUTION COMPLETE")
    print(f"  Video saved: {video_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
