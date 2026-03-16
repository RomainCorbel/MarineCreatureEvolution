import math
import random
import params
from utils import intersect

class Muscle:
    def __init__(self, n_center, n_target, freq, phase, amplitude):
        self.n_center = n_center
        self.n_target = n_target
        self.freq = freq
        self.phase = phase
        self.amplitude = amplitude
        self.length = params.SEGMENT_LENGTH
        self.energy_spent = 0

    def apply_physics(self, nodes, timer):
        nc, nt = nodes[self.n_center], nodes[self.n_target]
        
        # 1. Rotation forcée
        target_angle = math.sin(timer * self.freq + self.phase) * self.amplitude
        dx, dy = nt.x - nc.x, nt.y - nc.y
        current_angle = math.atan2(dy, dx)
        diff = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
        
        torque = diff * 0.3
        self.energy_spent += abs(torque) * self.freq

        # 2. Propulsion Newtonienne
        perp_x, perp_y = -dy / self.length, dx / self.length
        push = torque * params.WATER_DENSITY
        nt.vx += perp_x * push
        nt.vy += perp_y * push
        nc.vx -= perp_x * push
        nc.vy -= perp_y * push

        # 3. Contrainte de distance rigide
        new_dx, new_dy = nt.x - nc.x, nt.y - nc.y
        new_dist = math.sqrt(new_dx**2 + new_dy**2)
        if new_dist == 0: return
        corr = (self.length - new_dist) / new_dist
        nt.x += new_dx * corr * 0.5
        nt.y += new_dy * corr * 0.5
        nc.x -= new_dx * corr * 0.5
        nc.y -= new_dy * corr * 0.5

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

    # def calculate_fitness(self):
    #     dist = sum(n.x for n in self.nodes) / len(self.nodes)
    #     n_muscles = len(self.muscles)
    #     energy = sum(m.energy_spent for m in self.muscles) + 1
    #     self.fitness = (dist * 100) / (energy * 0.05 + n_muscles * 2.0)
    #     return self.fitness

    def calculate_fitness(self):
        # 1. Centre de masse initial (ix, iy)
        cx_ini = sum(n.ix for n in self.nodes) / len(self.nodes)
        cy_ini = sum(n.iy for n in self.nodes) / len(self.nodes)
        
        # 2. Centre de masse actuel (x, y)
        cx_act = sum(n.x for n in self.nodes) / len(self.nodes)
        cy_act = sum(n.y for n in self.nodes) / len(self.nodes)
        
        # 3. Distance euclidienne (Pythagore)
        distance = math.sqrt((cx_act - cx_ini)**2 + (cy_act - cy_ini)**2)
        
        # 4. Énergie normalisée (inchangée)
        n_muscles = len(self.muscles)
        energie_totale = sum(m.energy_spent for m in self.muscles)
        energie_normalisee = (energie_totale / n_muscles) if n_muscles > 0 else 0
        
        # 5. Fitness : Ratio Distance / Effort
        self.fitness = distance / (energie_normalisee + 1.0)
        
        return self.fitness

    def mutate(self):
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