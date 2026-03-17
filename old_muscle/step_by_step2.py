import pygame
import math
### On ajoute la physique des liens
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY_BONE = 0.2
RIGIDITY_MUSCLE = RIGIDITY_BONE
DAMPING = 0.9 # <+1 sinon on diverge car on ajoute du mouvement a chaque fois

class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy

class Muscle:
    def __init__(self, n_a, n_b, is_bone=True):
        self.n_a = n_a
        self.n_b = n_b
        self.target_len = target_len = 1.0  # Longueur cible du muscle (1m par défaut)
        self.is_bone = is_bone  # Par défaut, on considère que c'est un os rigide

class Creature:
    def __init__(self, nodes, muscles):
        self.nodes = nodes
        self.muscles = muscles

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

            # 1. Calcul des forces des muscles (ressorts)
            for m in self.muscles:
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
                force_multiplier = RIGIDITY_BONE if m.is_bone else RIGIDITY_MUSCLE
                
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
    # nodes = [
    #     Node(0, 0, -0.02, -0.01),                           # Sommet
    #     Node(math.cos(math.radians(240)), math.sin(math.radians(240)), 0.02, 0.01), # Pied 1  # ne pas mettre de vitesse trop importante pour eviter les oscillation elastiques
    # ]

    # # 2 edges (os) de 1m + 1 muscle pour l'ouverture
    # muscles = [
    #     Muscle(0, 1, is_bone=True),
    # ]
    nodes = [
        Node(0, 0, 0.1, -0.02),                           # Sommet
        Node(math.cos(math.radians(240)), math.sin(math.radians(240)), 0.05, 0), # Pied 1 
        Node(math.cos(math.radians(300)), math.sin(math.radians(300)), 0.05, 0.03),  # Pied 2
    ]
    # 2 edges (os) de 1m + 1 muscle pour l'ouverture
    muscles = [
        Muscle(0, 1, is_bone=True),
        Muscle(0, 2, is_bone=True),
        Muscle(1, 2, is_bone=False)
    ]
    return Creature(nodes, muscles)

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

        for m in creature.muscles:
            n1, n2 = creature.nodes[m.n_a], creature.nodes[m.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            
            color = (80, 150, 255) if m.is_bone else (255, 50, 50)
            pygame.draw.line(screen, color, p1, p2, 5 if m.is_bone else 2)

        for n in creature.nodes:
            pygame.draw.circle(screen, (255, 255, 255), (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy)), 6)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()