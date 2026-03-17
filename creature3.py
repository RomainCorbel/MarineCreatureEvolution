import math
import random
import params

class Node:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = self.fx = self.fy = 0.0
        self.orig_x, self.orig_y = x, y

    def apply_force(self, fx, fy):
        self.fx += fx
        self.fy += fy

    def update(self, damping):
        self.vx = (self.vx + self.fx) * damping
        self.vy = (self.vy + self.fy) * damping
        self.x += self.vx
        self.y += self.vy
        self.fx = self.fy = 0.0

    def reset(self):
        self.x, self.y = self.orig_x, self.orig_y
        self.vx = self.vy = 0.0
class Muscle:
    def __init__(self, n_a, n_b, nodes, clock_speed=0, targets=None, is_bone=True):
        self.n_a = n_a
        self.n_b = n_b
        self.is_bone = is_bone
        self.targets = targets if targets else [1.0]
        self.clock_speed = clock_speed
        
        # --- CALCUL DYNAMIQUE DE LA LONGUEUR AU REPOS ---
        na, nb = nodes[n_a], nodes[n_b]
        dx, dy = nb.x - na.x, nb.y - na.y
        self.base_len = math.hypot(dx, dy) 
        
        # On définit la rigidité selon le rôle
        if self.is_bone:
            self.rigidity = 0.4  # L'os ne doit pas bouger
        else:
            self.rigidity = 0.05 # Le muscle est élastique
    def apply_physics(self, nodes, timer):
            na, nb = nodes[self.n_a], nodes[self.n_b]
            dx, dy = nb.x - na.x, nb.y - na.y
            dist = math.hypot(dx, dy) or 0.01
            
            # --- LOGIQUE DIFFÉRENCIÉE ---
            if self.is_bone:
                # L'os veut toujours faire sa base_len initiale
                target_len = self.base_len
            else:
                # Le muscle suit son cycle d'oscillation
                t = (timer * self.clock_speed) % len(self.targets)
                target_len = self.base_len * self.targets[int(t)]

            # Calcul de la force de ressort
            f_spring = (dist - target_len) * self.rigidity

            # Damping interne (amortissement de la vitesse relative)
            v_rel_x = nb.vx - na.vx
            v_rel_y = nb.vy - na.vy
            v_rel = (v_rel_x * dx + v_rel_y * dy) / dist
            
            damp_factor = 0.8 if self.is_bone else 0.2
            f_damping = v_rel * damp_factor

            f_total = f_spring + f_damping
            
            # Application des forces
            fx, fy = (dx / dist) * f_total, (dy / dist) * f_total
            na.apply_force(fx, fy)
            nb.apply_force(-fx, -fy)

class Creature:
    def __init__(self, nodes, muscles, ancestor_id=""):
        self.nodes = nodes
        self.muscles = muscles
        self.ancestor_id = ancestor_id
        self.fitness = 0.0
    def update(self, timer, damping):
            for m in self.muscles:
                m.apply_physics(self.nodes, timer) # Plus besoin de params.RIGIDITY
            
            self.apply_water_physics()
            
            for n in self.nodes:
                n.update(damping)

    def apply_water_physics(self):
        # On applique la traînée sur chaque segment (OS)
        for m in self.muscles:
            if not m.is_bone: continue
            n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
            
            # Vecteur segment
            dx, dy = n2.x - n1.x, n2.y - n1.y
            L = math.hypot(dx, dy) or 0.1
            nx, ny = -dy/L, dx/L # Normale
            
            # Vitesse moyenne
            vx, vy = (n1.vx + n2.vx)/2, (n1.vy + n2.vy)/2
            
            # Projection de la vitesse sur la normale
            v_norm = vx * nx + vy * ny
            
            # Force opposée (traînée)
            drag_f = -v_norm * params.WATER_DENSITY * L
            
            n1.apply_force(nx * drag_f, ny * drag_f)
            n2.apply_force(nx * drag_f, ny * drag_f)

    def calculate_fitness(self):
        # Fitness basée sur la distance parcourue vers la droite
        avg_x = sum(n.x for n in self.nodes) / len(self.nodes)
        self.fitness = max(0.0001, avg_x)

    def mutate(self):
        import copy
        child = copy.deepcopy(self)
        for m in child.muscles:
            if not m.is_bone:
                m.clock_speed += random.uniform(-0.02, 0.02)
                m.targets = [max(0.3, min(2.0, t + random.uniform(-0.1, 0.1))) for t in m.targets]
        return child