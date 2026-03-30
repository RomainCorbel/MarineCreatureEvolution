import pygame
import math

# v12 : mutations après 10 secondes de simulation.

# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 0.5 
RIGIDITY_MUSCLE = 0.1
DAMPING = 0.7
SUBSTEPS = 50
FLOW_COEF  = 8.0  # Force d'expulsion et d'aspiration des membres
FLOW_POWER = 2    # Exposant de la vitesse : 1=lineaire, 2=quadratique (amplifie l'asymetrie)
FLOW_MAX   = 0.3  # Force maximale par substep (evite la divergence)
DRAG = 0.16          # Resistance de l'eau sur les membres
INERTIA_GAIN  = 0.4  # Fraction de la force convertie en inertie
INERTIA_DECAY = 0.92 # Vitesse de dissipation de l'inertie (proche de 1 = lente)

class Node:
    def __init__(self, x, y, is_muscle=False, amplitude=0.3, phase=0.0, period=120, duty_cycle=0.5):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.inertia_vx, self.inertia_vy = 0.0, 0.0
        self.is_muscle = is_muscle

        # Propriétés de mouvement (utilisées seulement si is_muscle est True)
        self.amplitude = amplitude  # Oscillation en radians
        self.phase = phase          # Décalage de phase [0, 2*pi]
        self.period = period        # Durée d'un cycle complet (frames)
        self.duty_cycle = duty_cycle  # Fraction du cycle pour la fermeture [0,1]
                                      # < 0.5 : fermeture rapide / ouverture lente
                                      # > 0.5 : fermeture lente / ouverture rapide

        self.base_angle = 0.0
        self.target_angle = 0.0




class Edge:
    def __init__(self, n_a, n_b):
        self.n_a = n_a
        self.n_b = n_b
        self.length = 1.0  # Toutes les arêtes font exactement 1 uni
class Creature:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
    
    def update(self, frame_count):
        # On répète la physique plusieurs fois par frame
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
                    
                    # Vecteurs pour calcul de distance
                    ab = pygame.Vector2(n2.x - n1.x, n2.y - n1.y)
                    ap = pygame.Vector2(n.x - n1.x, n.y - n1.y)
                    
                    # Projection (t) pour trouver le point le plus proche
                    seg_len_sq = ab.length_squared()
                    if seg_len_sq == 0: continue
                    
                    t = ap.dot(ab) / seg_len_sq
                    t = max(0, min(1, t)) 
                    
                    closest = pygame.Vector2(n1.x + t * ab.x, n1.y + t * ab.y)
                    dist_vec = pygame.Vector2(n.x - closest.x, n.y - closest.y)
                    distance = dist_vec.length()
                    
                    if distance < collision_radius:
                        # print(distance)
                        # 1. Calcul de l'intensité de la force (Pression)
                        push_mag = (collision_radius - distance) * repulsion_strength
                        force = (dist_vec / (distance+0.001)) * push_mag
                        
                        # 2. ACTION : Le Node subit la force
                        n.vx += force.x
                        n.vy += force.y
                        
                        # 3. RÉACTION : Le segment subit l'exact opposé (-force)
                        # On distribue selon la règle du levier :
                        # Si t=0 (proche n1), n1 prend tout. Si t=1 (proche n2), n2 prend tout.
                        n1.vx -= force.x * (1 - t)
                        n1.vy -= force.y * (1 - t)
                        n2.vx -= force.x * t
                        n2.vy -= force.y * t
    def _physics_step(self, frame_count):
        # 1. Mise à jour des cibles de muscles (une fois par step ou par frame)
        for n in self.nodes:
            if n.is_muscle:
                phase_offset = n.phase / (2 * math.pi) * n.period
                t_in_cycle = (frame_count + phase_offset) % n.period
                close_dur = n.duty_cycle * n.period
                open_dur  = n.period - close_dur

                if t_in_cycle < close_dur:
                    p = t_in_cycle / close_dur          # [0, 1]
                    t = -math.cos(math.pi * p)          # -1 -> +1 (fermeture)
                else:
                    p = (t_in_cycle - close_dur) / open_dur  # [0, 1]
                    t = math.cos(math.pi * p)           # +1 -> -1 (ouverture)

                n.target_angle = n.base_angle + t * n.amplitude

        # 2. Physique des OS
        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2) or 0.001
            delta = (dist - 1.0) / dist
            fx, fy = dx * delta * RIGIDITY_BONE, dy * delta * RIGIDITY_BONE
            n1.vx += fx; n1.vy += fy
            n2.vx -= fx; n2.vy -= fy

        # 3. Physique des MUSCLES
        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref
                dx_l, dy_l = n_l.x - n.x, n_l.y - n.y
                dx_r, dy_r = n_r.x - n.x, n_r.y - n.y
                
                # Sécurité : distance mini pour éviter division par zéro
                dist_l = max(0.2, math.sqrt(dx_l**2 + dy_l**2))
                dist_r = max(0.2, math.sqrt(dx_r**2 + dy_r**2))

                angle_l = math.atan2(dy_l, dx_l)
                angle_r = math.atan2(dy_r, dx_r)
                current_angle = angle_r - angle_l
                
                diff = (n.target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
                torque_force = diff * RIGIDITY_MUSCLE
                
                # Application des forces
                fl_x, fl_y = (math.sin(angle_l) * torque_force / dist_l), (-math.cos(angle_l) * torque_force / dist_l)
                fr_x, fr_y = (-math.sin(angle_r) * torque_force / dist_r), (math.cos(angle_r) * torque_force / dist_r)

                n_l.vx += fl_x; n_l.vy += fl_y
                n_r.vx += fr_x; n_r.vy += fr_y
                n.vx -= (fl_x + fr_x); n.vy -= (fl_y + fr_y)
        # 3.2 Apply colision
        self._apply_collisions()

        # 4. Trainee (isotrope pour l'instant mais possibilité de changer en anisotrope plus tard)
        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            avg_vx = (n1.vx + n2.vx) / 2
            avg_vy = (n1.vy + n2.vy) / 2

            # Direction du membre
            dx, dy = n2.x - n1.x, n2.y - n1.y
            length = math.sqrt(dx**2 + dy**2) or 0.001
            tx, ty = dx / length, dy / length  # tangente (axe du membre)
            nx, ny = -ty, tx                   # normale (perpendiculaire)

            # Decomposition de la vitesse en composantes parallele et perpendiculaire
            v_par  = avg_vx * tx + avg_vy * ty
            v_perp = avg_vx * nx + avg_vy * ny

            drag_x = (v_par * tx + v_perp * nx) * DRAG
            drag_y = (v_par * ty + v_perp * ny) * DRAG

            n1.vx -= drag_x; n1.vy -= drag_y
            n2.vx -= drag_x; n2.vy -= drag_y
# 5. PHYSIQUE DE L'EAU (Loi 2 : Expulsion de volume avec seuil d'angle)
        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref
                v1 = pygame.Vector2(n_l.x - n.x, n_l.y - n.y)
                v2 = pygame.Vector2(n_r.x - n.x, n_r.y - n.y)

                if v1.length() > 0 and v2.length() > 0:
                    # 1. Calcul de l'angle actuel entre les deux membres
                    dot_angle = v1.normalize().dot(v2.normalize())
                    # Clamp pour éviter les erreurs de calcul de acos
                    dot_angle = max(-1.0, min(1.0, dot_angle))
                    angle_interne = math.acos(dot_angle) 

                    # 2. Facteur d'efficacité : Max à 0 rad, décroît vers 0 à 180° (pi rad)
                    # On peut utiliser une courbe en cosinus pour une transition douce
                    efficiency = math.sin(angle_interne)
                    
                    # 3. Calcul de la vitesse de rapprochement
                    rel_vx = n_l.vx - n_r.vx
                    rel_vy = n_l.vy - n_r.vy
                    dot_product = (n_l.x - n_r.x) * rel_vx + (n_l.y - n_r.y) * rel_vy

                    mid_x = (v1.x + v2.x) / 2
                    mid_y = (v1.y + v2.y) / 2
                    dist = math.sqrt(mid_x**2 + mid_y**2) or 0.1

                    if dot_product < 0: # Fermeture : expulsion d'eau
                        push_force = min((abs(dot_product) ** FLOW_POWER) * FLOW_COEF * efficiency, FLOW_MAX)
                        fx, fy = -(mid_x / dist) * push_force, -(mid_y / dist) * push_force
                        n.vx += fx; n.vy += fy
                        n.inertia_vx += fx * INERTIA_GAIN
                        n.inertia_vy += fy * INERTIA_GAIN
                    else:               # Ouverture : aspiration d'eau
                        suck_force = min((abs(dot_product) ** FLOW_POWER) * FLOW_COEF * efficiency, FLOW_MAX)
                        fx, fy = (mid_x / dist) * suck_force, (mid_y / dist) * suck_force
                        n.vx += fx; n.vy += fy
                        n.inertia_vx += fx * INERTIA_GAIN
                        n.inertia_vy += fy * INERTIA_GAIN
        # 6. Intégration avec Limitation de vitesse
        for n in self.nodes:
            # Clamp de la vitesse pour éviter les "téléportations"
            max_v = 0.1
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

import random
import math

def random_num_nodes():
    # Weights decay exponentially: 3 has the most chance, 10 the least
    choices = list(range(3, 11))
    weights = [math.exp(-1.4 * i) for i in range(len(choices))]
    return random.choices(choices, weights=weights)[0]

def spawn_random_creature(num_nodes=None):
    if num_nodes is None:
        num_nodes = random_num_nodes()
    nodes = []
    edges = []
    
    # 1. Placement des Nodes (Garantir distance = 1)
    # On commence à (0,0)
    nodes.append(Node(0, 0))
    
    # On ajoute les autres nodes en se connectant à un node existant
    for i in range(1, num_nodes):
        connected = False
        while not connected:
            parent_idx = random.randint(0, len(nodes) - 1)
            parent = nodes[parent_idx]
            
            # On choisit un angle aléatoire (ex: multiples de 90° ou totalement libre)
            # Ici on laisse libre pour plus de variété :
            angle = random.uniform(0, 2 * math.pi)
            new_x = parent.x + math.cos(angle)
            new_y = parent.y + math.sin(angle)
            
            # Vérification : ne pas spawner deux nodes exactement au même endroit
            too_close = any(math.sqrt((new_x - n.x)**2 + (new_y - n.y)**2) < 0.5 for n in nodes)
            
            if not too_close:
                nodes.append(Node(new_x, new_y))
                edges.append(Edge(parent_idx, i)) # L'index dans la liste
                connected = True

    # 2. Identification des muscles
    # On compte combien d'edges sont connectés à chaque node
    connection_count = [0] * len(nodes)
    adj_list = [[] for _ in range(len(nodes))]
    for e in edges:
        connection_count[e.n_a] += 1
        connection_count[e.n_b] += 1
        adj_list[e.n_a].append(e.n_b)
        adj_list[e.n_b].append(e.n_a)

    # 3. Paramétrage aléatoire des Nodes
    for i, n in enumerate(nodes):
        # Condition : Muscle seulement si exactement 2 connexions (ou plus)
        if connection_count[i] >= 2:
            # n.is_muscle = random.choice([True, False])
            n.is_muscle = True
            if n.is_muscle:
                n.amplitude  = random.uniform(0.1, 1.0)
                n.phase      = random.uniform(0, 2 * math.pi)
                n.period     = random.randint(FPS, FPS * 5)
                n.duty_cycle = random.uniform(0.1, 0.4)   # fermeture rapide par defaut
                
                # Choix des deux nodes de référence pour le muscle
                # On prend les deux premiers voisins dans la liste d'adjacence
                ref_indices = adj_list[i][:2]
                n.nodes_ref = (nodes[ref_indices[0]], nodes[ref_indices[1]])
                
                # Calcul de l'angle de base initial
                angle1 = math.atan2(n.nodes_ref[0].y - n.y, n.nodes_ref[0].x - n.x)
                angle2 = math.atan2(n.nodes_ref[1].y - n.y, n.nodes_ref[1].x - n.x)
                n.base_angle = angle2 - angle1
    return Creature(nodes, edges)

def _setup_muscle_params(n, adj_list, nodes, i):
    """Set muscle parameters on node n (used by spawn and add_node mutation)."""
    n.amplitude  = random.uniform(0.1, 1.0)
    n.phase      = random.uniform(0, 2 * math.pi)
    n.period     = random.randint(FPS, FPS * 5)
    n.duty_cycle = random.uniform(0.1, 0.4)
    ref_indices  = adj_list[i][:2]
    n.nodes_ref  = (nodes[ref_indices[0]], nodes[ref_indices[1]])
    angle1 = math.atan2(n.nodes_ref[0].y - n.y, n.nodes_ref[0].x - n.x)
    angle2 = math.atan2(n.nodes_ref[1].y - n.y, n.nodes_ref[1].x - n.x)
    n.base_angle = angle2 - angle1

def mutate(creature):
    """Apply one random mutation to the creature and return a new Creature."""
    import copy
    nodes = copy.deepcopy(creature.nodes)
    edges = copy.deepcopy(creature.edges)

    # Reset velocities / inertia so the mutated creature starts stable
    for n in nodes:
        n.vx = n.vy = 0.0
        n.inertia_vx = n.inertia_vy = 0.0

    # Collect nodes that are muscles (have nodes_ref set)
    muscle_nodes = [n for n in nodes if n.is_muscle and hasattr(n, 'nodes_ref') and n.nodes_ref]

    # Weights: amplitude 30%, duty_cycle 30%, phase_break 20%, add_node 20%
    if muscle_nodes:
        mutation_pool = ['amplitude', 'amplitude', 'amplitude',
                         'duty_cycle', 'duty_cycle', 'duty_cycle',
                         'phase_break', 'phase_break',
                         'add_node', 'add_node']
    else:
        mutation_pool = ['add_node']

    choice = random.choice(mutation_pool)

    if choice == 'amplitude':
        n = random.choice(muscle_nodes)
        delta = random.uniform(-0.3, 0.3)
        n.amplitude = max(0.05, min(2.0, n.amplitude + delta))

    elif choice == 'duty_cycle':
        n = random.choice(muscle_nodes)
        delta = random.uniform(-0.15, 0.15)
        n.duty_cycle = max(0.05, min(0.95, n.duty_cycle + delta))

    elif choice == 'phase_break':
        # Shift the phase of one muscle, changing when it starts/ends its cycle
        n = random.choice(muscle_nodes)
        n.phase = (n.phase + random.uniform(0.2, math.pi)) % (2 * math.pi)

    elif choice == 'add_node':
        if len(nodes) < 10:
            # Pick a random existing node as parent
            parent_idx = random.randint(0, len(nodes) - 1)
            parent = nodes[parent_idx]
            new_idx = len(nodes)

            # Find a free angle
            for _ in range(100):
                angle = random.uniform(0, 2 * math.pi)
                nx_ = parent.x + math.cos(angle)
                ny_ = parent.y + math.sin(angle)
                if not any(math.sqrt((nx_ - n.x)**2 + (ny_ - n.y)**2) < 0.5 for n in nodes):
                    new_node = Node(nx_, ny_)
                    nodes.append(new_node)
                    edges.append(Edge(parent_idx, new_idx))

                    # Recompute adjacency to decide if nodes become muscles
                    connection_count = [0] * len(nodes)
                    adj_list = [[] for _ in range(len(nodes))]
                    for e in edges:
                        connection_count[e.n_a] += 1
                        connection_count[e.n_b] += 1
                        adj_list[e.n_a].append(e.n_b)
                        adj_list[e.n_b].append(e.n_a)

                    for i, nd in enumerate(nodes):
                        if connection_count[i] >= 2 and not nd.is_muscle:
                            nd.is_muscle = True
                            _setup_muscle_params(nd, adj_list, nodes, i)
                    break
        # If already at max nodes, do a small amplitude tweak instead
        else:
            if muscle_nodes:
                n = random.choice(muscle_nodes)
                n.amplitude = max(0.05, min(2.0, n.amplitude + random.uniform(-0.2, 0.2)))

    return Creature(nodes, edges)

def recenter(creature):
    """Translate all nodes so their centroid is at (0, 0)."""
    cx = sum(n.x for n in creature.nodes) / len(creature.nodes)
    cy = sum(n.y for n in creature.nodes) / len(creature.nodes)
    for n in creature.nodes:
        n.x -= cx
        n.y -= cy

def centroid(creature):
    cx = sum(n.x for n in creature.nodes) / len(creature.nodes)
    cy = sum(n.y for n in creature.nodes) / len(creature.nodes)
    return cx, cy

SIMULATION_DURATION = FPS * 10  # 10 seconds per simulation round

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

    DISTANCE_DIVERGE = 8.0  # Max plausible distance; beyond this the creature is discarded

    creature = spawn_random_creature()
    ox, oy = WIDTH // 2, HEIGHT // 2
    frame_count = 0
    generation = 0
    last_mutation = "none (initial spawn)"
    last_mutation_result = ""

    # The best creature found so far (kept as the parent for all mutations)
    import copy
    best_creature = copy.deepcopy(creature)
    best_distance = 0.0

    start_cx, start_cy = centroid(creature)
    distance_start_cx, distance_start_cy = start_cx, start_cy
    last_gen_distance = 0.0
    max_distance = 0.0
    max_distance_gen = 0
    distance_this_gen = 0.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        creature.update(frame_count)
        for n in creature.nodes:
            n.vx += n.inertia_vx
            n.vy += n.inertia_vy
            n.inertia_vx *= INERTIA_DECAY
            n.inertia_vy *= INERTIA_DECAY
        frame_count += 1

        # Détection de divergence physique : respawn propre si instable
        max_pos = 20.0
        diverged = any(abs(n.x) > max_pos or abs(n.y) > max_pos or
                       math.isnan(n.x) or math.isnan(n.vx)
                       for n in creature.nodes)

        # Snapshot centroid at 2s to use as the distance reference
        if frame_count == FPS * 2:
            distance_start_cx, distance_start_cy = centroid(creature)

        def _reset_from_best():
            nonlocal creature, frame_count, generation, start_cx, start_cy
            nonlocal distance_start_cx, distance_start_cy, last_gen_distance
            candidate = mutate(best_creature)
            recenter(candidate)
            creature = candidate
            frame_count = 0
            generation += 1
            cx, cy = centroid(creature)
            start_cx, start_cy = cx, cy
            distance_start_cx, distance_start_cy = cx, cy
            last_gen_distance = 0.0

        if diverged:
            last_mutation_result = "diverged (physics) — retry from best"
            _reset_from_best()
            last_mutation = f"mutation (gen {generation}, retry)"

        # Après 10 secondes : évaluer et décider
        elif frame_count >= SIMULATION_DURATION:
            last_gen_distance = math.sqrt((centroid(creature)[0] - distance_start_cx)**2 +
                                          (centroid(creature)[1] - distance_start_cy)**2)

            if last_gen_distance > DISTANCE_DIVERGE:
                # Distance suspiciously large — discard and retry from best
                last_mutation_result = f"discarded (dist {last_gen_distance:.2f} > {DISTANCE_DIVERGE}) — retry"
                _reset_from_best()
                last_mutation = f"mutation (gen {generation}, retry)"

            elif last_gen_distance > best_distance:
                # Improvement — keep this creature as the new best
                prev_best = best_distance
                best_distance = last_gen_distance
                best_creature = copy.deepcopy(creature)
                if last_gen_distance > max_distance:
                    max_distance = last_gen_distance
                    max_distance_gen = generation
                last_mutation_result = f"kept (dist {last_gen_distance:.2f} > prev {prev_best:.2f})"
                _reset_from_best()
                last_mutation = f"mutation (gen {generation})"

            else:
                # Regression — discard mutant, retry from best
                last_mutation_result = f"discarded (dist {last_gen_distance:.2f} <= best {best_distance:.2f}) — retry"
                _reset_from_best()
                last_mutation = f"mutation (gen {generation}, retry)"

        # Distance from the 2s-mark centroid position (0 during warmup, frozen in last second)
        if FPS * 2 <= frame_count < SIMULATION_DURATION - FPS:
            cx, cy = centroid(creature)
            distance_this_gen = math.sqrt((cx - distance_start_cx)**2 + (cy - distance_start_cy)**2)

        # --- Dessin ---
        screen.fill((15, 15, 25))
        for x in range(0, WIDTH, ZOOM):
            pygame.draw.line(screen, (40, 40, 55), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, ZOOM):
            pygame.draw.line(screen, (40, 40, 55), (0, y), (WIDTH, y))

        for e in creature.edges:
            n1, n2 = creature.nodes[e.n_a], creature.nodes[e.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            pygame.draw.line(screen, (100, 150, 255), p1, p2, 5)

        for n in creature.nodes:
            color = (255, 100, 100) if n.is_muscle else (255, 255, 255)
            pos = (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy))
            pygame.draw.circle(screen, color, pos, 8)

        # HUD
        seconds_left = (SIMULATION_DURATION - frame_count) // FPS
        hud_lines = [
            f"Generation: {generation}",
            f"Nodes: {len(creature.nodes)}",
            f"Last mutation: {last_mutation}",
            f"Result: {last_mutation_result}",
            f"Best distance: {best_distance:.2f} u",
            f"Next mutation in: {seconds_left}s",
            f"Distance (this gen): {distance_this_gen:.2f} u",
            f"Distance (last gen): {last_gen_distance:.2f} u",
            f"Distance max: {max_distance:.2f} u (gen {max_distance_gen})",
        ]
        for i, line in enumerate(hud_lines):
            surf = font.render(line, True, (200, 200, 200))
            screen.blit(surf, (12, 12 + i * 26))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()