import math
import random
import params
from utils import intersect

class Node:
    def __init__(self, x, y):
        self.ix, self.iy = x, y
        self.x, self.y = x, y
        self.vx, self.vy = 0, 0
        self.radius = params.NODE_RADIUS

    def reset(self):
        self.x, self.y = self.ix, self.iy
        self.vx, self.vy = 0, 0

class Creature:
    def __init__(self, nodes, muscles):
        self.nodes, self.muscles = nodes, muscles
        self.fitness = 0

    def resolve_collisions(self):
        # 1. Collisions Nodes
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                n1, n2 = self.nodes[i], self.nodes[j]
                dx, dy = n2.x - n1.x, n2.y - n1.y
                dist = math.sqrt(dx**2 + dy**2)
                min_d = n1.radius + n2.radius
                if 0 < dist < min_d:
                    overlap = min_d - dist
                    n1.x -= (dx/dist) * overlap * 0.5
                    n1.y -= (dy/dist) * overlap * 0.5
                    n2.x += (dx/dist) * overlap * 0.5
                    n2.y += (dy/dist) * overlap * 0.5

        # 2. Anti-croisement des Edges
        for i in range(len(self.muscles)):
            for j in range(i + 1, len(self.muscles)):
                m1, m2 = self.muscles[i], self.muscles[j]
                if len({m1.n_center, m1.n_target, m2.n_center, m2.n_target}) < 4: continue
                
                a, b = self.nodes[m1.n_center], self.nodes[m1.n_target]
                c, d = self.nodes[m2.n_center], self.nodes[m2.n_target]
                
                if intersect(a, b, c, d):
                    mid1_x, mid1_y = (a.x+b.x)/2, (a.y+b.y)/2
                    mid2_x, mid2_y = (c.x+d.x)/2, (c.y+d.y)/2
                    rdx, rdy = mid2_x - mid1_x, mid2_y - mid1_y
                    rdist = math.sqrt(rdx**2 + rdy**2) or 0.1
                    for n in [a, b]: n.x -= rdx/rdist * 0.05; n.y -= rdy/rdist * 0.05
                    for n in [c, d]: n.x += rdx/rdist * 0.05; n.y += rdy/rdist * 0.05

    def update(self, timer):
        for m in self.muscles: m.apply_physics(self.nodes, timer)
        for n in self.nodes:
            n.vx *= params.DAMPING; n.vy *= params.DAMPING
            n.x += n.vx; n.y += n.vy
        self.resolve_collisions()

    def calculate_fitness(self):
        dist = sum(n.x for n in self.nodes) / len(self.nodes)
        n_muscles = len(self.muscles)
        energy = sum(m.energy_spent for m in self.muscles) + 1
        self.fitness = (dist * 100) / (energy * 0.05 + n_muscles * 2.0)
        return self.fitness

    def mutate(self):
        from movement import Muscle # Import local pour éviter boucle circulaire
        new_nodes = [Node(n.ix, n.iy) for n in self.nodes]
        new_muscles = [Muscle(m.n_center, m.n_target, m.freq, m.phase, m.amplitude) for m in self.muscles]
        
        for m in new_muscles:
            if random.random() < 0.2: m.phase += random.uniform(-0.5, 0.5)
            if random.random() < 0.1: m.amplitude = max(0.1, m.amplitude + random.uniform(-0.1, 0.1))
            if random.random() < 0.1: m.freq = max(0.05, m.freq + random.uniform(-0.02, 0.02))

        if random.random() < 0.08 and len(new_nodes) < 8:
            p_idx = random.randint(0, len(new_nodes)-1)
            angle = random.uniform(0, 6.28)
            new_node = Node(new_nodes[p_idx].ix + math.cos(angle)*params.SEGMENT_LENGTH, 
                            new_nodes[p_idx].iy + math.sin(angle)*params.SEGMENT_LENGTH)
            new_nodes.append(new_node)
            new_muscles.append(Muscle(p_idx, len(new_nodes)-1, 0.1, random.random()*6, 0.8))
        return Creature(new_nodes, new_muscles)