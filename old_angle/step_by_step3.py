import pygame
import math
### j ai ajouté la possibilité d'ajouter des forces aux nodes, un test interactif, et le principe d action reaction pour que le systeme reste solide même si les edges n'ont pas tous la même vitesse
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY = 1
DAMPING = 0.98

def draw_axes(screen, ox, oy):
    pygame.draw.line(screen, (100, 0, 0), (0, oy), (WIDTH, oy), 1)
    pygame.draw.line(screen, (0, 100, 0), (ox, 0), (ox, HEIGHT), 1)
    for i in range(-10, 11):
        pygame.draw.line(screen, (255, 255, 255), (ox + i * ZOOM, oy - 5), (ox + i * ZOOM, oy + 5), 1)
        pygame.draw.line(screen, (255, 255, 255), (ox - 5, oy + i * ZOOM), (ox + 5, oy + i * ZOOM), 1)

class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy

class Edge:
    def __init__(self, n_a, n_b):
        self.n_a = n_a
        self.n_b = n_b
        self.target_len = 1

class Creature:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
        # On pré-calcule la liste d'adjacence
        self.adj = [[] for _ in range(len(nodes))]
        for e in edges:
            self.adj[e.n_a].append(e.n_b)
            self.adj[e.n_b].append(e.n_a)

    def apply_local_force(self, target_idx, fx, fy):
        neighbors = self.adj[target_idx]
        
        # Action
        self.nodes[target_idx].vx += fx
        self.nodes[target_idx].vy += fy

        # Réaction (Newton)
        rx, ry = -fx / len(neighbors), -fy / len(neighbors)
        for n_idx in neighbors:
            self.nodes[n_idx].vx += rx
            self.nodes[n_idx].vy += ry

    def update(self):
            # 1. Calcul des forces des edges (ressorts)
            for m in self.edges:
                n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
                dx = n2.x - n1.x
                dy = n2.y - n1.y
                dist = math.sqrt(dx**2 + dy**2)
                delta = (dist - m.target_len) / (dist if dist > 0 else 1)
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
                n.vx *= DAMPING 
                n.vy *= DAMPING
def spawn(): 
    nodes = [
        Node(0, 0, 0, 0),                       
        Node(0, 1, 0, 0),              
        Node(1, 0,  0, 0),  
    ]
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
        creature.update()
        keys = pygame.key.get_pressed()
        force = 0.05
        if keys[pygame.K_LEFT]:  creature.apply_local_force(0, -force, 0)
        if keys[pygame.K_RIGHT]: creature.apply_local_force(0, force, 0)
        if keys[pygame.K_UP]:    creature.apply_local_force(0, 0, -force)
        if keys[pygame.K_DOWN]:  creature.apply_local_force(0, 0, force)
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