import pygame
import math
### introduction de la dimension cyclique
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY = 0.5
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

        self.f_amplitude = 0.2  # Force max (0.0 à 1.0)
        self.f_angle = 0.0      # Direction de la force (en radians)
        self.f_period = 2.0     # Durée d'un cycle complet (en secondes)
        self.f_phase = 0.0      # Déphasage (pour que tous les nœuds ne poussent pas en même temps)
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
        self.timer = 0.0

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

    def update(self, dt):
            self.timer += dt # dt est le temps écoulé (ex: 1/60)
            for i, n in enumerate(self.nodes):
                        # 1. Calcul de la force cyclique continue
                        # Oscille entre -1 et 1, puis multiplié par l'amplitude (ex: 0.2)
                        # On utilise 2*pi pour que la période soit réellement en secondes
                        oscillation = math.sin(2 * math.pi * self.timer / n.f_period + n.f_phase)
                        current_f = oscillation * n.f_amplitude
                        
                        # 2. Application de la force dans la direction choisie
                        fx = math.cos(n.f_angle) * current_f
                        fy = math.sin(n.f_angle) * current_f
                        
                        # Cette force va alternativement pousser et tirer le nœud
                        self.apply_local_force(i, fx, fy)
            # 2. Physique des ressorts (ton code actuel)
            for m in self.edges:
                # ... calcul des forces edges (inchangé)
                n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
                dx, dy = n2.x - n1.x, n2.y - n1.y
                dist = math.sqrt(dx**2 + dy**2)
                delta = (dist - m.target_len) / (dist if dist > 0 else 1)
                f_x, f_y = dx * delta * RIGIDITY, dy * delta * RIGIDITY
                n1.vx += f_x; n1.vy += f_y
                n2.vx -= f_x; n2.vy -= f_y

            # 3. Intégration du mouvement (ton code actuel)
            for n in self.nodes:
                n.x += n.vx; n.y += n.vy
                n.vx *= DAMPING; n.vy *= DAMPING 
def spawn(): 
    n0 = Node(0, 0, 0, 0)
    n0.f_amplitude = 0.003
    n0.f_angle = math.pi/4 # Pousse vers le haut NB : l'angle est en radians, 0 = droite, pi/2 = bas, -pi/2 = haut, et ca veut dire que c est un angle absolue qui ne depend pas de l'orientation de la creature
    n0.f_period = 5.0       # Rapide
    n0.f_phase = 0

    n1 = Node(0, 1, 0, 0)
    n1.f_amplitude = 0
    n1.f_angle = math.pi/4  # Pousse en diagonale (droite-haut)
    n1.f_period = 5.0       # Lent
    n1.f_phase = 0    # En décalage
    
    n2 = Node(1, 0, 0, 0) 
    n2.f_amplitude = 0
    n2.f_angle = 3*math.pi/4  # Pousse en diagonale (gauche-bas) 
    n2.f_period = 5.0       # Lent
    n2.f_phase = 0    # En décalage

    nodes = [n0, n1, n2]
    edges = [Edge(0, 1), Edge(0, 2)]
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
        dt = 1/FPS # Environ 0.016s pour 60 FPS
        creature.update(dt)
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