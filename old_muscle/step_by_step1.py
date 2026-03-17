import pygame
import math
### On definit les edges, nodes, update, ici il n y pas la physique qui garde le systeme solide si tous les edges n'ont pas la même vitesse
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100

class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy

class Muscle:
    def __init__(self, n_a, n_b, is_bone=True):
        self.n_a = n_a
        self.n_b = n_b
        self.is_bone = is_bone

class Creature:
    def __init__(self, nodes, muscles):
        self.nodes = nodes
        self.muscles = muscles

    def update(self):
            """Applique la vitesse aux positions de tous les nodes"""
            for n in self.nodes:
                n.x += n.vx
                n.y += n.vy
def spawn():
    # 3 nodes formant un angle de 60° (triangle équilatéral de 1m de côté)
    nodes = [
        Node(0, 0, 0.02, 0.01),                           # Sommet
        Node(math.cos(math.radians(240)), math.sin(math.radians(240)), 0.02, 0.01), # Pied 1 
        Node(math.cos(math.radians(300)), math.sin(math.radians(300)), 0.02, 0.01),  # Pied 2
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