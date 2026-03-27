import math
import random
import copy
import params

class Node:
    def __init__(self, x, y):
        self.initial_x = x
        self.initial_y = y
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self.fx, self.fy = 0.0, 0.0

    def apply_force(self, fx, fy):
        self.fx += fx
        self.fy += fy

    def update(self):
        # Application des forces (Masse = 1 par simplification)
        self.vx += self.fx
        self.vy += self.fy
        
        # Friction globale de l'eau (Drag passif)
        self.vx *= 0.95
        self.vy *= 0.95
        
        self.x += self.vx
        self.y += self.vy
        
        # Reset des forces pour le prochain pas
        self.fx, self.fy = 0.0, 0.0

    def reset(self):
        self.x, self.y = self.initial_x, self.initial_y
        self.vx, self.vy = 0.0, 0.0
        self.fx, self.fy = 0.0, 0.0

class Muscle:
    def __init__(self, n_center, n_target, freq, phase, amplitude):
        self.n_center = n_center
        self.n_target = n_target
        self.freq = freq
        self.phase = phase
        self.amplitude = amplitude
        self.base_length = params.SEGMENT_LENGTH 
        self.energy_spent = 0.0

    def apply_physics(self, nodes, timer):
        node_a = nodes[self.n_center]
        node_b = nodes[self.n_target]
        
        # --- 1. LONGUEUR VOULUE (Contraction musculaire) ---
        # On limite l'amplitude pour que le membre ne change pas de taille
        cycle_time = 2 * math.pi * timer / params.GEN_DURATION
        target_len = self.base_length * (
            1.0 + math.sin(cycle_time * self.freq + self.phase) * self.amplitude * 0.01
        )
        
        # --- 2. CONTRAINTE DE RIGIDITÉ (Élastique très fort) ---
        dx = node_b.x - node_a.x
        dy = node_b.y - node_a.y
        dist = math.hypot(dx, dy) 
        
        rigidity = 0.9
        
        diff = (dist - target_len) / dist
        
        # Correction immédiate des forces
        fx = dx * diff * rigidity
        fy = dy * diff * rigidity
        
        node_a.apply_force(fx, fy)
        node_b.apply_force(-fx, -fy)
        
        self.energy_spent += abs(fx) + abs(fy)

        # --- 3. LOI 1 : PROPULSION PAR L'EAU (L'essentiel du mouvement) ---
        # On calcule la vitesse relative du membre par rapport à l'eau
        # On utilise la vitesse actuelle des nodes pour créer une force de réaction
        v_membr_x = (node_a.vx + node_b.vx) / 2
        v_membr_y = (node_a.vy + node_b.vy) / 2

        # Coefficient de pénétration dans l'eau
        # C'est cette force qui transforme le battement en propulsion
        water_resistance = 0.15 
        
        # Newton : l'eau pousse le membre dans le sens opposé à sa vitesse
        node_a.apply_force(-v_membr_x * water_resistance, -v_membr_y * water_resistance)
        node_b.apply_force(-v_membr_x * water_resistance, -v_membr_y * water_resistance)

class Creature:
    def __init__(self, nodes, muscles, ancestor_id=""):
        self.nodes = nodes
        self.muscles = muscles
        self.ancestor_id = ancestor_id
        self.fitness = 0.0
    
    ### COLLISIONS ET CONTRAINTES DE STRUCTURE ### pas utilisé
    def resolve_collisions(self):
            # Empecher les nodes de se chevaucher
            self.resolve_node_collisions()

            # Empecher les croisements de muscles autour d'un même node
            self.resolve_shared_node_crossings()

            # Empecher les croisements de segments indépendant
            self.resolve_edge_crossings()


    def resolve_node_collisions(self):
        for i in range(len(self.nodes)):
            for j in range(i+1, len(self.nodes)): #On compare tous les nodes entre eux
                n1 = self.nodes[i]
                n2 = self.nodes[j]

                dx = n2.x - n1.x
                dy = n2.y - n1.y

                dist = math.sqrt(dx*dx + dy*dy) #Calcul des distances entre les nodes
                min_dist = n1.radius + n2.radius

                if 0 < dist < min_dist: #Si dist entre nodes inf à somme des rayons, ils se chevauchent
                    overlap = min_dist - dist
                    nx = dx / dist #direction du chevauchement
                    ny = dy / dist
                    correction = overlap * 0.5 #on écarte les nodes dans la direction opposée au chevauchement
                    n1.x -= nx * correction
                    n1.y -= ny * correction
                    n2.x += nx * correction
                    n2.y += ny * correction


    def resolve_shared_node_crossings(self):
        connections = {}

        for m in self.muscles: #dictionnaire des connection --> quel muscle touche quel node?
            connections.setdefault(m.n_center, []).append(m)
            connections.setdefault(m.n_target, []).append(m)

        for node_idx, muscles in connections.items(): #items renvoie qqc comme (O,[M2, M0]) (muscles associés à chaque node)
            if len(muscles) < 2: #Si un seul muscle par node continue
                continue
            node = self.nodes[node_idx]
            angles = []

            for m in muscles:
                other_idx = m.n_target if m.n_center == node_idx else m.n_center
                other = self.nodes[other_idx]
                angle = math.atan2(other.y - node.y, other.x - node.x) #calcul l'angle entre deux segments reliés à un node commun
                angles.append((angle, other))

            angles.sort()
            min_angle = 0.2

            for i in range(len(angles)-1): #Repousse les muscles et nodes en cas de probleme de croisement
                a1, n1 = angles[i]
                a2, n2 = angles[i+1]
                if abs(a2 - a1) < min_angle:
                    dx = n2.x - n1.x
                    dy = n2.y - n1.y
                    dist = math.sqrt(dx*dx + dy*dy) or 0.1
                    push = 0.05
                    n1.x -= dx/dist * push
                    n1.y -= dy/dist * push
                    n2.x += dx/dist * push
                    n2.y += dy/dist * push


    def resolve_edge_crossings(self):
        for i in range(len(self.muscles)):
            for j in range(i + 1, len(self.muscles)):
                m1 = self.muscles[i]
                m2 = self.muscles[j]

                if len({m1.n_center, m1.n_target, m2.n_center, m2.n_target}) < 4: #cas traité précédemment
                    continue

                a = self.nodes[m1.n_center]
                b = self.nodes[m1.n_target]
                c = self.nodes[m2.n_center]
                d = self.nodes[m2.n_target]

                if intersect(a, b, c, d):
                    mid1x = (a.x + b.x) * 0.5
                    mid1y = (a.y + b.y) * 0.5
                    mid2x = (c.x + d.x) * 0.5
                    mid2y = (c.y + d.y) * 0.5
                    dx = mid2x - mid1x
                    dy = mid2y - mid1y
                    dist = math.sqrt(dx*dx + dy*dy) or 0.1
                    nx = dx / dist
                    ny = dy / dist
                    push = 0.08

                    for n in [a, b]:
                        n.x -= nx * push
                        n.y -= ny * push

                    for n in [c, d]:
                        n.x += nx * push
                        n.y += ny * push
    ### FIN DES COLLISIONS ET CONTRAINTES DE STRUCTURE ### Pas utilisé pour l'instant

    def apply_hydro_law_2(self):
        """
        Deuxième loi : Interaction entre membres. 
        Si deux muscles partagent un point, on regarde le changement d'angle 
        qui expulse l'eau entre eux.
        """
        for i in range(len(self.muscles)):
            for j in range(i + 1, len(self.muscles)):
                m1, m2 = self.muscles[i], self.muscles[j]
                
                # On cherche le point commun (articulation)
                shared = None
                other1, other2 = None, None
                
                if m1.n_center == m2.n_center: 
                    shared, other1, other2 = m1.n_center, m1.n_target, m2.n_target
                elif m1.n_target == m2.n_target:
                    shared, other1, other2 = m1.n_target, m1.n_center, m2.n_center
                
                if shared is not None:
                    # Calcul du mouvement de "pince" (expulsion d'eau)
                    # Si les points other1 et other2 se rapprochent, l'eau au centre est expulsée
                    n_s = self.nodes[shared]
                    n1 = self.nodes[other1]
                    n2 = self.nodes[other2]
                    
                    # Vecteurs des membres
                    v1 = (n1.x - n_s.x, n1.y - n_s.y)
                    v2 = (n2.x - n_s.x, n2.y - n_s.y)
                    
                    # On calcule la variation de l'aire du triangle (volume d'eau)
                    # Aire = 0.5 * |x1y2 - x2y1|
                    aire = 0.5 * abs(v1[0]*v2[1] - v1[1]*v2[0])
                    
                    # On applique une force de réaction sur le point partagé
                    # proportionnelle à la vitesse de compression de cette aire
                    expulsion_force = aire * 0.01 
                    # La direction est la bissectrice inverse de l'angle
                    n_s.apply_force(0, -expulsion_force) # Simplification directionnelle

    def update(self, timer):
        for m in self.muscles:
            m.apply_physics(self.nodes, timer)
        
        self.apply_hydro_law_2() # Ajout de la loi d'interaction
        
        for n in self.nodes:
            n.update()

    def calculate_fitness(self):
        # Utilisation de initial_x/y pour le calcul
        cx_ini = sum(n.initial_x for n in self.nodes) / len(self.nodes)
        cy_ini = sum(n.initial_y for n in self.nodes) / len(self.nodes)
        cx_act = sum(n.x for n in self.nodes) / len(self.nodes)
        cy_act = sum(n.y for n in self.nodes) / len(self.nodes)
        
        self.distance = math.hypot(cx_act - cx_ini, cy_act - cy_ini)
        
        n_muscles = len(self.muscles)
        self.energie_totale = sum(m.energy_spent for m in self.muscles)
        self.energie_normalisee = (self.energie_totale / n_muscles) if n_muscles > 0 else 0
        
        # On récompense la distance, on pénalise l'énergie
        self.fitness = self.distance / (self.energie_normalisee + 1.0)
        return self.fitness

    def mutate(self):
        new_nodes = [Node(n.initial_x, n.initial_y) for n in self.nodes]
        new_muscles = copy.deepcopy(self.muscles)
        
        # On reset l'énergie pour la nouvelle génération
        for m in new_muscles: m.energy_spent = 0
            
        m = random.choice(new_muscles)
        m.freq = max(0.1, min(5.0, m.freq + random.uniform(-0.05, 0.05)))
        m.amplitude = max(0.1, min(1.0, m.amplitude + random.uniform(-0.1, 0.1)))
        m.phase += random.uniform(-0.5, 0.5)
        
        return Creature(new_nodes, new_muscles, ancestor_id=self.ancestor_id)
