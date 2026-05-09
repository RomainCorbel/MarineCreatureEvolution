import pygame
import math
import random

WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY = 0.5
DAMPING = 0.98


def draw_axes(screen, ox, oy):
    pygame.draw.line(screen, (100, 0, 0), (0, oy), (WIDTH, oy), 1)
    pygame.draw.line(screen, (0, 100, 0), (ox, 0), (ox, HEIGHT), 1)


def normalize(x, y):
    norm = math.sqrt(x*x + y*y)
    if norm == 0:
        return 0, 0
    return x/norm, y/norm


class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy

        # Force parameters
        self.f_amplitude = 0.0
        self.f_period = 1.0
        self.f_phase = 0.0

        # NEW
        self.force_edges = None  # (idx1, idx2)
        self.force_mode = "avg"  # "avg" or "perp"


class Edge:
    def __init__(self, n_a, n_b):
        self.n_a = n_a
        self.n_b = n_b
        self.target_len = 1


class Creature:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

        self.adj = [[] for _ in range(len(nodes))]
        for e in edges:
            self.adj[e.n_a].append(e.n_b)
            self.adj[e.n_b].append(e.n_a)

        self.timer = 0.0

    def apply_local_force(self, target_idx, fx, fy):
        neighbors = self.adj[target_idx]

        self.nodes[target_idx].vx += fx
        self.nodes[target_idx].vy += fy

        if len(neighbors) == 0:
            return

        rx, ry = -fx / len(neighbors), -fy / len(neighbors)
        for n_idx in neighbors:
            self.nodes[n_idx].vx += rx
            self.nodes[n_idx].vy += ry

    def compute_force_direction(self, node_idx):
        node = self.nodes[node_idx]

        if node.force_edges is None:
            return 0, 0

        i, j = node.force_edges
        ni = self.nodes[i]
        nj = self.nodes[j]
        n0 = node

        # vectors from node to neighbors
        v1 = normalize(ni.x - n0.x, ni.y - n0.y)
        v2 = normalize(nj.x - n0.x, nj.y - n0.y)

        if node.force_mode == "avg":
            dx = v1[0] + v2[0]
            dy = v1[1] + v2[1]
            return normalize(dx, dy)

        elif node.force_mode == "perp":
            dx = v1[0] - v2[0]
            dy = v1[1] - v2[1]
            # perpendicular
            return normalize(-dy, dx)

        return 0, 0

    def update(self, dt):
        self.timer += dt

        # --- Forces cycliques ---
        for i, n in enumerate(self.nodes):
            if n.f_amplitude == 0 or n.force_edges is None:
                continue

            oscillation = math.sin(2 * math.pi * self.timer / n.f_period + n.f_phase)
            current_f = oscillation * n.f_amplitude

            dx, dy = self.compute_force_direction(i)

            fx = dx * current_f
            fy = dy * current_f

            self.apply_local_force(i, fx, fy)

        # --- Ressorts ---
        for m in self.edges:
            n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = math.sqrt(dx**2 + dy**2)
            delta = (dist - m.target_len) / (dist if dist > 0 else 1)

            f_x, f_y = dx * delta * RIGIDITY, dy * delta * RIGIDITY

            n1.vx += f_x
            n1.vy += f_y
            n2.vx -= f_x
            n2.vy -= f_y

        # --- Intégration ---
        for n in self.nodes:
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING


# -------------------------
# RANDOM SPAWN
# -------------------------

def random_spawn():
    # --- géométrie triangle ---
    angle = random.uniform(0.5, 2.5)

    n0 = Node(0, 0, 0, 0)
    n1 = Node(1, 0, 0, 0)
    n2 = Node(math.cos(angle), math.sin(angle), 0, 0)

    nodes = [n0, n1, n2]
    edges = [Edge(0, 1), Edge(0, 2)]

    creature = Creature(nodes, edges)

    # --- seul n0 a deux edges ---
    n0.f_amplitude = random.uniform(0.001, 0.01)
    n0.f_period = random.uniform(2.0, 10.0)
    n0.f_phase = random.uniform(0, 2 * math.pi)

    # choisir les deux voisins
    n0.force_edges = (1, 2)

    # mode aléatoire
    n0.force_mode = random.choice(["avg", "perp"])

    return creature


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    creature = random_spawn()

    ox, oy = WIDTH // 2, HEIGHT // 2

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        dt = 1 / FPS
        creature.update(dt)

        screen.fill((5, 10, 20))
        draw_axes(screen, ox, oy)

        for m in creature.edges:
            n1, n2 = creature.nodes[m.n_a], creature.nodes[m.n_b]
            p1 = (int(n1.x * ZOOM + ox), int(n1.y * ZOOM + oy))
            p2 = (int(n2.x * ZOOM + ox), int(n2.y * ZOOM + oy))
            pygame.draw.line(screen, (80, 150, 255), p1, p2, 5)

        for n in creature.nodes:
            pygame.draw.circle(
                screen,
                (255, 255, 255),
                (int(n.x * ZOOM + ox), int(n.y * ZOOM + oy)),
                6,
            )

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()