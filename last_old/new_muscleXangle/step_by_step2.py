import pygame
import math
# il faut pouvoir avoir plusieurs types d oscillation ==> fourier
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 1  
RIGIDITY_MUSCLE = 0.5 
DAMPING = 0.99 

class Node:
    def __init__(self, x, y, is_muscle=False, components=None, nodes_ref=None):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.is_muscle = is_muscle

        # Liste de dicts : [{"amp": 0.3, "phi": 0.0, "per": 120}, ...]
        self.components = components if components else []
        
        self.base_angle = 0.0
        self.target_angle = 0.0
        self.nodes_ref = nodes_ref

        if is_muscle and nodes_ref and len(nodes_ref) == 2:
            n1, n2 = nodes_ref
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
        # 1. Fourier : Somme des oscillations pour l'angle cible
        for n in self.nodes:
            if n.is_muscle:
                oscillation = 0
                for c in n.components:
                    oscillation += math.sin(2 * math.pi * frame_count / c['per'] + c['phi']) * c['amp']
                n.target_angle = n.base_angle + oscillation

        # 2. Physique des OS (Ressorts de distance)
        for e in self.edges:
            n1, n2 = self.nodes[e.n_a], self.nodes[e.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2) or 0.001
            delta = (dist - e.length) / dist
            fx, fy = dx * delta * RIGIDITY_BONE, dy * delta * RIGIDITY_BONE
            n1.vx += fx; n1.vy += fy
            n2.vx -= fx; n2.vy -= fy

        # 3. Physique des MUSCLES (Action/Réaction Newtonienne)
        for n in self.nodes:
            if n.is_muscle and n.nodes_ref:
                n_l, n_r = n.nodes_ref
                dx_l, dy_l = n_l.x - n.x, n_l.y - n.y
                dx_r, dy_r = n_r.x - n.x, n_r.y - n.y
                dist_l = math.sqrt(dx_l**2 + dy_l**2) or 0.1
                dist_r = math.sqrt(dx_r**2 + dy_r**2) or 0.1

                angle_l, angle_r = math.atan2(dy_l, dx_l), math.atan2(dy_r, dx_r)
                current_angle = angle_r - angle_l
                
                diff = (n.target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
                torque_force = diff * RIGIDITY_MUSCLE
                
                # Forces perpendiculaires (F = Torque / Bras de levier)
                fl_x, fl_y = (math.sin(angle_l) * torque_force / dist_l), (-math.cos(angle_l) * torque_force / dist_l)
                fr_x, fr_y = (-math.sin(angle_r) * torque_force / dist_r), (math.cos(angle_r) * torque_force / dist_r)

                n_l.vx += fl_x; n_l.vy += fl_y
                n_r.vx += fr_x; n_r.vy += fr_y
                n.vx -= (fl_x + fr_x)
                n.vy -= (fl_y + fr_y)

        # 4. Intégration
        for n in self.nodes:
            n.x += n.vx; n.y += n.vy
            n.vx *= DAMPING; n.vy *= DAMPING

def spawn_meduse():
    # Définition d'un cycle asymétrique (Fourier)
    # Fondamentale + Harmonique déphasée = Contraction brusque / Relâchement lent
    cycle_meduse = [
        {"amp": 0.6, "phi": 0, "per": 240},       # Mouvement de base
        {"amp": 0.6, "phi": math.pi/2, "per": 240} # Harmonique pour l'asymétrie
    ]
    
    pivot = Node(0, 0, is_muscle=True, components=cycle_meduse)
    n_gauche = Node(0, 1)
    n_droit = Node(0,-1)

    pivot.nodes_ref = (n_gauche, n_droit)
    # Recalcul de l'angle de base après l'attribution des refs
    a1 = math.atan2(n_gauche.y, n_gauche.x)
    a2 = math.atan2(n_droit.y, n_droit.x)
    pivot.base_angle = a2 - a1
    
    return Creature([pivot, n_gauche, n_droit], [Edge(0, 1), Edge(0, 2)])
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    creature = spawn_meduse()
    ox, oy = WIDTH // 2, HEIGHT // 2
    frame_count = 0 

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        creature.update(frame_count)
        frame_count += 1 

        screen.fill((10, 15, 30))
        for e in creature.edges:
            n1, n2 = creature.nodes[e.n_a], creature.nodes[e.n_b]
            pygame.draw.line(screen, (80, 120, 255), 
                             (n1.x*ZOOM+ox, n1.y*ZOOM+oy), (n2.x*ZOOM+ox, n2.y*ZOOM+oy), 4)
        for n in creature.nodes:
            color = (255, 100, 100) if n.is_muscle else (255, 255, 255)
            pygame.draw.circle(screen, color, (int(n.x*ZOOM+ox), int(n.y*ZOOM+oy)), 6)

        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()