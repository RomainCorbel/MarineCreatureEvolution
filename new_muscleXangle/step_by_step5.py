import pygame
import math
# more complicated creature, hand built
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 1  
RIGIDITY_MUSCLE = 0.1
DAMPING = 0.7

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
        # 1. Mise à jour des muscles (Nodes articulés)
        for n in self.nodes:
                    if n.is_muscle:
                        raw_sin = math.sin(2 * math.pi * frame_count / n.period + n.phase)
                        threshold = n.threshold 
                        coef_pause = n.coef_pause
                        t = raw_sin
                        
                        # Gestion de la pause haute
                        if n.pause_max and raw_sin > threshold:
                            # On ralentit la progression au-delà du seuil, si coef pause < 1, 
                            t = threshold + (raw_sin - threshold) * coef_pause # 0 c est arret complet, 1 c'est aucun arret, entre 0 et 1 c est ralentissement, entre 1 et plus c'est acceleration

                        # Gestion de la pause basse
                        elif n.pause_min and raw_sin < -threshold: # Utilise elif pour la propreté
                            # On ralentit la progression en dessous du seuil négatif
                            # (raw_sin + threshold) est la distance parcourue sous le seuil
                            t = -threshold + (raw_sin + threshold) * coef_pause
                        
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

# def spawn_creature():
#     n1 = Node(1, 0)
#     n2 = Node(0, 0, is_muscle=True, amplitude=0.1, period=360)
#     n3 = Node(0, 1, is_muscle=True, amplitude=0.1, period=360)
#     n4 = Node(0, 2)
    
#     # Configuration des articulations (angles de référence)
#     # n0 contrôle l'écart entre n1 et n2
#     n2.nodes_ref = (n1, n3)
#     n2.base_angle = math.atan2
    
#     # n1 contrôle l'écart entre n0 et n3 (flexion de la colonne)
#     n3.nodes_ref = (n2, n4)
#     n3.base_angle = math.atan2(

#     # Définition des connexions physiques (Edges)
#     edges = [
#         Edge(0, 1), # Segment vertical bas
#         Edge(0, 2), # Segment horizontal
#         Edge(1, 3)  # Segment vertical haut
#     ]
    
#     return Creature([n0, n1, n2, n3], edges)
def spawn_creature():
    import math
    
    # 1. Définition des Nodes (Coordonnées : x, y)
    n0 = Node(1, 0) # Index 0
    n1 = Node(0, 0, is_muscle=True, amplitude=0.7, period=360) # Index 1
    n2 = Node(0, 1, is_muscle=True, amplitude=0.5, period=120) # Index 2
    n3 = Node(0, 2) # Index 3
    
    # 2. Configuration des muscles (Calcul des angles de repos)
    # n1 (pivot à 0,0) regarde n0 (1,0) et n2 (0,1)
    n1.nodes_ref = (n0, n2)
    n1.base_angle = math.atan2(n2.y - n1.y, n2.x - n1.x) - \
                    math.atan2(n0.y - n1.y, n0.x - n1.x)
    
    # n2 (pivot à 0,1) regarde n1 (0,0) et n3 (0,2)
    n2.nodes_ref = (n1, n3)
    n2.base_angle = math.atan2(n3.y - n2.y, n3.x - n2.x) - \
                    math.atan2(n1.y - n2.y, n1.x - n2.x)
    
    # 3. Définition des connexions physiques (Edges)
    # On relie les points pour former la structure
    edges = [
        Edge(0, 1), # Relie (1,0) à (0,0)
        Edge(1, 2), # Relie (0,0) à (0,1)
        Edge(2, 3)  # Relie (0,1) à (0,2)
    ]
    
    # 4. Retourne la créature avec la liste ordonnée des nodes
    return Creature([n0, n1, n2, n3], edges)
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn_creature()
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