import pygame
import math
# substepping
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 0.8 
RIGIDITY_MUSCLE = 0.1
DAMPING = 0.7
SUBSTEPS = 30

class Node:
    def __init__(self, x, y, is_muscle=False, amplitude=0.3, phase=0.0, period=120, nodes_ref=None, pause_max=False, pause_min=False, threshold=0.5, coef_pause = 0):
        self.x, self.y = x, y
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.is_muscle = is_muscle


        # Propriétés de mouvement (utilisées seulement si is_muscle est True)
        self.amplitude = amplitude  # Oscillation en radians (ex: 0.3 rad)
        self.phase = phase          # Décalage (offset)
        self.period = period        # Temps pour un cycle complet
        self.pause_max = pause_max  # True = s'arrête en haut
        self.pause_min = pause_min  # True = s'arrête en bas
        self.threshold = threshold    # Seuil pour les pauses
        self.coef_pause = coef_pause

        self.base_angle = 0.0
        self.target_angle = 0.0

        # --- MESURE INITIALE ---
        # Si on donne deux nodes de référence (n1, n2), on calcule l'angle formé par n1 -> self -> n2
        if is_muscle and nodes_ref and len(nodes_ref) == 2:
            n1, n2 = nodes_ref
            # On calcule l'angle relatif entre les deux segments connectés à ce joint
            angle1 = math.atan2(n1.y - self.y, n1.x - self.x)
            angle2 = math.atan2(n2.y - self.y, n2.x - self.x)
            self.base_angle = angle2 - angle1



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

    def _physics_step(self, frame_count):
        # 1. Mise à jour des cibles de muscles (une fois par step ou par frame)
        for n in self.nodes:
            if n.is_muscle:
                raw_sin = math.sin(2 * math.pi * frame_count / n.period + n.phase)
                t = raw_sin
                if n.pause_max and raw_sin > n.threshold:
                    t = n.threshold + (raw_sin - n.threshold) * n.coef_pause
                elif n.pause_min and raw_sin < -n.threshold:
                    t = -n.threshold + (raw_sin + n.threshold) * n.coef_pause
                
                n.target_angle = n.base_angle + (t * n.amplitude)

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

        # 4. Intégration avec Limitation de vitesse
        for n in self.nodes:
            # Clamp de la vitesse pour éviter les "téléportations"
            max_v = 0.5 
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

import random
import math

def spawn_random_creature(num_nodes=3):
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
            n.is_muscle = random.choice([True, False])
            if n.is_muscle:
                n.amplitude = random.uniform(0.1, 1.0)
                n.phase = random.uniform(0, 2 * math.pi)
                n.period = random.randint(FPS, FPS * 5)
                n.threshold = random.uniform(0.1, 0.9)
                n.coef_pause = random.uniform(0, 5)
                
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
    
    creature = spawn_random_creature(num_nodes=5)
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