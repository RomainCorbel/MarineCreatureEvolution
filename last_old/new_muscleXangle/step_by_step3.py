import pygame
import math

# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 1  
RIGIDITY_MUSCLE = 0.5 
DAMPING = 0.9

class Node:
    def __init__(self, x, y, is_muscle=False, amplitude=0.3, phase=0.0, period=120, nodes_ref=None, pause_max=False, pause_min=False, threshold=0.5):
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
        # 1. Mise à jour des muscles (Nodes articulés)
        for n in self.nodes:
                    if n.is_muscle:
                        raw_sin = math.sin(2 * math.pi * frame_count / n.period + n.phase)
                        threshold = n.threshold 
                        t = raw_sin
                        
                        # Gestion de la pause haute
                        if n.pause_max and raw_sin > threshold:
                            t = threshold
                        
                        # Gestion de la pause basse
                        elif n.pause_min and raw_sin < -threshold: # Utilise elif pour la propreté
                            t = -threshold
                        
                        n.target_angle = n.base_angle + (t * n.amplitude)
        # 2. Physique des OS (Edges) : Maintenir la longueur de 1.0
        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2) or 0.001
            
            # Loi de Hooke simple (longueur cible = 1.0)
            delta = (dist - 1.0) / dist
            fx, fy = dx * delta * RIGIDITY_BONE, dy * delta * RIGIDITY_BONE
            
            n1.vx += fx; n1.vy += fy
            n2.vx -= fx; n2.vy -= fy
# 3. Physique des MUSCLES (Angles) - Version Newtonienne
        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref # n_left, n_right
                
                # Vecteurs segments (Pivot -> Extrémités)
                dx_l, dy_l = n_l.x - n.x, n_l.y - n.y
                dx_r, dy_r = n_r.x - n.x, n_r.y - n.y
                
                dist_l = math.sqrt(dx_l**2 + dy_l**2) or 0.1
                dist_r = math.sqrt(dx_r**2 + dy_r**2) or 0.1

                # Angle actuel et écart
                angle_l = math.atan2(dy_l, dx_l)
                angle_r = math.atan2(dy_r, dx_r)
                current_angle = angle_r - angle_l
                
                # Correction pour l'angle (entre -pi et pi)
                diff = (n.target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
                torque_force = diff * RIGIDITY_MUSCLE
                
                # Forces perpendiculaires aux bras
                # F = torque / distance (pour que le moment soit constant)
                fl_x, fl_y = (math.sin(angle_l) * torque_force / dist_l), (-math.cos(angle_l) * torque_force / dist_l)
                fr_x, fr_y = (-math.sin(angle_r) * torque_force / dist_r), (math.cos(angle_r) * torque_force / dist_r)

                # ACTION sur les extrémités
                n_l.vx += fl_x; n_l.vy += fl_y
                n_r.vx += fr_x; n_r.vy += fr_y
                
                # RÉACTION sur le pivot (Somme des forces = 0)
                n.vx -= (fl_x + fr_x)
                n.vy -= (fl_y + fr_y)

        # 4. Intégration & Damping
        for n in self.nodes:
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

def spawn_pince():
    pivot = Node(0, 0, is_muscle=True, amplitude=0.9, period=240, pause_max=True, pause_min=False, threshold=0.5)
    node_gauche = Node(0, 1)
    node_droit = Node(1,0)
    # pivot = Node(0, 0, is_muscle=True, amplitude=1, period=240, pause_max=True, pause_min=False, threshold=0.5)
    # node_gauche = Node(0, 1)
    # node_droit = Node(0,-1)
    pivot.nodes_ref = (node_gauche, node_droit)
    angle1 = math.atan2(node_gauche.y - pivot.y, node_gauche.x - pivot.x)
    angle2 = math.atan2(node_droit.y - pivot.y, node_droit.x - pivot.x)
    pivot.base_angle = angle2 - angle1 # L'écartement initial
    edges = [
        Edge(0, 1), 
        Edge(0, 2)  
    ]
    return Creature([pivot, node_gauche, node_droit], edges)

def spawn_chenille():
    nodes = []
    edges = []
    num_segments = 5
    
    # 1. Création des Nodes
    for i in range(num_segments):
        # On les place à x = 0, 1, 2, 3... pour que la distance soit de 1
        # Seuls les nodes intérieurs (pas les extrémités) sont des muscles
        is_muscle = i > 0 and i < num_segments - 1
        
        # Décalage de phase pour l'effet d'onde
        phase_offset = i * 0.8 
        
        n = Node(x=float(i), y=0.0, 
                 is_muscle=is_muscle, 
                 amplitude=0.6, 
                 period=120, 
                 phase=phase_offset,
                 pause_max=True,   # Petite pause en extension
                 pause_min=False, 
                 threshold=0.6)
        nodes.append(n)

    # 2. Assignation des références pour les muscles
    # Un muscle a besoin du node à sa gauche et à sa droite pour calculer l'angle
    for i in range(1, num_segments - 1):
        nodes[i].nodes_ref = (nodes[i-1], nodes[i+1])
        # Calcul de l'angle initial (ici 180° car ils sont alignés)
        nodes[i].base_angle = math.pi 

    # 3. Création des Edges (les os de longueur 1)
    for i in range(num_segments - 1):
        edges.append(Edge(i, i + 1))

    return Creature(nodes, edges)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn_pince()
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