import pygame
import math

# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 100
RIGIDITY_BONE = 1  
RIGIDITY_MUSCLE = 0.5 
DAMPING = 0.99 

class Node:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0

class Edge:
    def __init__(self, n_a, n_b, nodes, is_bone=True, amplitude=0.3, phase=0.0, period=120):
        self.n_a = n_a
        self.n_b = n_b
        self.is_bone = is_bone
        
        # Propriétés de mouvement pour les muscles(ignorées si is_bone=True)
        self.amplitude = amplitude # % de contraction/extension (0.3 = 30%)
        self.phase = phase         # Décalage dans le temps (en radians)
        self.period = period       # Durée du cycle en frames (typiquement 120 pour 2 secondes à 60 FPS)
        # --- MESURE INITIALE ---
        # On calcule la distance au spawn pour définir la longueur de base du muscle. Parce que OUI les os font 1 par construction, mais pas les muscles qui doivent être mesurés
        n1, n2 = nodes[n_a], nodes[n_b]
        self.base_len = math.sqrt((n2.x - n1.x)**2 + (n2.y - n1.y)**2)

class Creature:
    def __init__(self, nodes, muscles):
        self.nodes = nodes
        self.muscles = muscles
    
    def update(self, frame_count):
        # 1. Mise à jour de la longueur cible (Muscle control)
        for m in self.muscles:
            if not m.is_bone:
                # Oscillation fluide autour de la longueur de base
                # Entre (base - amplitude) et (base + amplitude)
                t = math.sin(2 * math.pi * frame_count / m.period + m.phase)
                m.target_len = m.base_len * (1 + t * m.amplitude)
            else:
                m.target_len = m.base_len

        # 2. Physique (Newton : Action / Réaction interne)
        for m in self.muscles:
            n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2) or 0.001
            
            # Calcul de l'écart relatif
            delta = (dist - m.target_len) / dist
            k = RIGIDITY_BONE if m.is_bone else RIGIDITY_MUSCLE
            
            # Force appliquée (Loi de Hooke)
            fx, fy = dx * delta * k, dy * delta * k
            
            # Application symétrique pour respecter la 1ère loi de Newton (somme forces = 0)
            n1.vx += fx; n1.vy += fy
            n2.vx -= fx; n2.vy -= fy

        # 3. Intégration du mouvement & Damping
        for n in self.nodes:
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

def spawn_pince():
    # On définit les positions initiales
    # Pivot en (0,0), bras en (0,1) et (1,0)
    nodes = [
        Node(0, 0),     # 0: Pivot
        Node(-0.5, 1),  # 1: Pointe gauche
        Node(0.5, 1),   # 2: Pointe droite
    ]
    
    # La mesure automatique du Muscle va calculer base_len entre (1) et (2)
    edges = [
        Edge(0, 1, nodes, is_bone=True),  # Os gauche
        Edge(0, 2, nodes, is_bone=True),  # Os droit
        Edge(1, 2, nodes, is_bone=False, amplitude=0.6, period=240)  # Le muscle de fermeture entre les deux pointes
    ]
    return Creature(nodes, edges)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn_pince()
    ox, oy = WIDTH // 2, HEIGHT // 2
    frame_count = 0 

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        creature.update(frame_count)
        frame_count += 1 

        # --- RENDU ---
        screen.fill((5, 10, 20))
        
        # Quadrillage (sombre)
        for x in range(0, WIDTH, ZOOM):
            pygame.draw.line(screen, (250, 250, 250), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, ZOOM):
            pygame.draw.line(screen, (250, 250, 250), (0, y), (WIDTH, y))
            
        # Rendu des muscles et os
        for m in creature.muscles:
            n1, n2 = creature.nodes[m.n_a], creature.nodes[m.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            
            color = (100, 150, 255) if m.is_bone else (255, 80, 80)
            width = 6 if m.is_bone else 3
            pygame.draw.line(screen, color, p1, p2, width)

        # Rendu des articulations
        for n in creature.nodes:
            pygame.draw.circle(screen, (255, 255, 255), (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy)), 7)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()