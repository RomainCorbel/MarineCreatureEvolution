import pygame
import math

# v10 : ajout de l'asymétrie temporelle des muscles (duty_cycle)
#       et de la force d'aspiration lors de l'ouverture des membres.

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
DRAG = 0.16  # Resistance de l'eau sur les membres

class Node:
    def __init__(self, x, y, is_muscle=False, amplitude=0.3, phase=0.0, period=120, duty_cycle=0.5):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
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
                        n.vx -= (mid_x / dist) * push_force
                        n.vy -= (mid_y / dist) * push_force
                    else:               # Ouverture : aspiration d'eau
                        suck_force = min((abs(dot_product) ** FLOW_POWER) * FLOW_COEF * efficiency, FLOW_MAX)
                        n.vx += (mid_x / dist) * suck_force
                        n.vy += (mid_y / dist) * suck_force
        # 6. Intégration avec Limitation de vitesse
        for n in self.nodes:
            # Clamp de la vitesse pour éviter les "téléportations"
            max_v = 0.1
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

import random
import math

def spawn_random_creature(num_nodes=10):
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

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn_random_creature(num_nodes=10)
    ox, oy = WIDTH // 2, HEIGHT // 2 # Centrage
    frame_count = 0 

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        creature.update(frame_count)
        frame_count += 1 

        screen.fill((15, 15, 25))
        for x in range(0, WIDTH, ZOOM):
            pygame.draw.line(screen, (150, 150, 150), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, ZOOM):
            pygame.draw.line(screen, (150, 150, 150), (0, y), (WIDTH, y))
        # -----------------------------
        # Dessin des os (Edges)
        for e in creature.edges:
            n1, n2 = creature.nodes[e.n_a], creature.nodes[e.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            pygame.draw.line(screen, (100, 150, 255), p1, p2, 5)

        # Dessin des joints (Nodes)
        for n in creature.nodes:
            color = (255, 100, 100) if n.is_muscle else (255, 255, 255)
            pos = (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy))
            pygame.draw.circle(screen, color, pos, 8)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()