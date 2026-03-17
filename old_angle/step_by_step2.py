import pygame
import math
### On ajoute la physique des liens
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY = 0.5
DAMPING = 0.98 # <+1 sinon on diverge car on ajoute du mouvement a chaque fois

def draw_axes(screen, ox, oy):
    # Axe X (Horizontal) - Rouge sombre
    pygame.draw.line(screen, (100, 0, 0), (0, oy), (WIDTH, oy), 1)
    # Axe Y (Vertical) - Vert sombre
    pygame.draw.line(screen, (0, 100, 0), (ox, 0), (ox, HEIGHT), 1)

    # Petits traits de graduation tous les 1m (ZOOM)
    for i in range(-10, 11):
        # Graduations X
        pygame.draw.line(screen, (255, 255, 255), (ox + i * ZOOM, oy - 5), (ox + i * ZOOM, oy + 5), 1)
        # Graduations Y
        pygame.draw.line(screen, (255, 255, 255), (ox - 5, oy + i * ZOOM), (ox + 5, oy + i * ZOOM), 1)

class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy

class Edge:
    def __init__(self, n_a, n_b):
        self.n_a = n_a
        self.n_b = n_b
        self.target_len = target_len = 1.0  # Longueur cible du muscle (1m par défaut)

class Creature:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    # def update(self):
    #         """Applique la vitesse aux positions de tous les nodes"""
    #         for n in self.nodes:
    #             n.x += n.vx
    #             n.y += n.vy
    def update(self):
            
# --- PHYSIQUE MASSE-RESSORT ---
# 1. On calcule l'écart (delta) entre la distance actuelle et la cible (1m)
# 2. Cet écart génère une force : si trop long, ça tire ; si trop court, ça pousse
# 3. On applique +Force sur Node1 et -Force sur Node2 (Action/Réaction de Newton)
# 4. On ajoute la force à la vitesse (F=ma, avec m=1) pour créer l'inertie
# 5. La vitesse déplace la position, puis on l'amortit (Damping) pour simuler la friction

            # 1. Calcul des forces des edges (ressorts)
            for m in self.edges:
                n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
                
                # Distance actuelle entre les deux points
                dx = n2.x - n1.x
                dy = n2.y - n1.y
                dist = math.sqrt(dx**2 + dy**2)
                
                # Différence entre distance réelle et cible
                # Si dist < target_len, delta est négatif (pousse)
                # Si dist > target_len, delta est positif (tire)
                delta = (dist - m.target_len) / (dist if dist > 0 else 1)
                
                # On applique la force sur la vitesse des nodes
                # On multiplie par RIGIDITY (plus fort pour les os)
                force_multiplier = RIGIDITY
                
                fx = dx * delta * force_multiplier
                fy = dy * delta * force_multiplier
                
                n1.vx += fx
                n1.vy += fy
                n2.vx -= fx
                n2.vy -= fy

            # 2. Application du mouvement et amortissement
            for n in self.nodes:
                n.x += n.vx
                n.y += n.vy
                n.vx *= DAMPING  # Amortissement (Damping) pour éviter que ça explose
                n.vy *= DAMPING
def spawn():
    nodes = [
        Node(0, 0, 0, 0),                           # Sommet, il faut bien veiller à spawn les nodes a 1 de distance, sinon on donne de l'énergie avant de commencer quoi que ce soit et ca va pas du tout!
        Node(0, 1, 0, -0.02),                           # GOOD TO KNOW: y va vers le beau car ca marche comme ca pour les pixels
        Node(1, 0,  0, 0),  
    ]
    # 2 edges (os) de 1m + 1 muscle pour l'ouverture
    edges = [
        Edge(0, 1),
        Edge(0, 2),
    ]
    return Creature(nodes, edges)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn()
    ox, oy = WIDTH // 2, HEIGHT // 2

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        # --- PHYSIQUE MANUELLE ---
        creature.update()

        # --- RENDU ---
        screen.fill((5, 10, 20))
        draw_axes(screen, ox, oy)
        for m in creature.edges:
            n1, n2 = creature.nodes[m.n_a], creature.nodes[m.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            
            color = (80, 150, 255)
            pygame.draw.line(screen, color, p1, p2, 5)

        for n in creature.nodes:
            pygame.draw.circle(screen, (255, 255, 255), (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy)), 6)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()