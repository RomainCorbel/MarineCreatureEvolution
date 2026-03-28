import pygame
import math

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1280, 720
FPS = 120
ZOOM = 30
RIGIDITY = 1
DAMPING = 0.85  # damping plus fort que l'inertie

# --- FONCTIONS UTILES ---
def draw_axes(screen, ox, oy):
    pygame.draw.line(screen, (100,0,0), (0,oy), (WIDTH,oy), 1)
    pygame.draw.line(screen, (0,100,0), (ox,0), (ox,HEIGHT), 1)
    for i in range(-10,11):
        pygame.draw.line(screen, (255,255,255), (ox+i*ZOOM, oy-5), (ox+i*ZOOM, oy+5),1)
        pygame.draw.line(screen, (255,255,255), (ox-5, oy+i*ZOOM), (ox+5, oy+i*ZOOM),1)

# --- CLASSES ---
class Node:
    def __init__(self, x, y, vx, vy):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.f_amplitude = 0.2
        self.f_angle = 0.0
        self.f_period = 2.0
        self.f_phase = 0.0

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
        self.prev_area = self.compute_triangle_area(0,1,2) if len(nodes)>=3 else 0.0
        self.prev_velocity = [0.0,0.0]  # pour inertie lissée

    def apply_local_force(self, target_idx, fx, fy):
        neighbors = self.adj[target_idx]
        self.nodes[target_idx].vx += fx
        self.nodes[target_idx].vy += fy
        if neighbors:
            rx, ry = -fx/len(neighbors), -fy/len(neighbors)
            for n_idx in neighbors:
                self.nodes[n_idx].vx += rx
                self.nodes[n_idx].vy += ry

    def compute_triangle_area(self, i0, i1, i2):
        n0,n1,n2 = self.nodes[i0], self.nodes[i1], self.nodes[i2]
        x1,y1 = n1.x-n0.x, n1.y-n0.y
        x2,y2 = n2.x-n0.x, n2.y-n0.y
        return 0.5*(x1*y2 - y1*x2)

    def update(self, dt):
        self.timer += dt

        # --- FORCES MUSCULAIRES ---
        for i,n in enumerate(self.nodes):
            oscillation = math.sin(2*math.pi*self.timer/n.f_period + n.f_phase)
            current_f = oscillation * n.f_amplitude
            fx = math.cos(n.f_angle)*current_f
            fy = math.sin(n.f_angle)*current_f
            self.apply_local_force(i, fx, fy)

        # --- RESSORTS ---
        for m in self.edges:
            n1,n2 = self.nodes[m.n_a], self.nodes[m.n_b]
            dx,dy = n2.x-n1.x, n2.y-n1.y
            dist = math.sqrt(dx*dx + dy*dy) or 1e-6
            delta = (dist - m.target_len)/dist
            f_x, f_y = dx*delta*RIGIDITY, dy*delta*RIGIDITY
            n1.vx += f_x; n1.vy += f_y
            n2.vx -= f_x; n2.vy -= f_y

        # --- PROPULSION FLUIDE ---
        if len(self.nodes)>=3:
            A = self.compute_triangle_area(0,1,2)
            min_area = 1e-4
            dA = 0 if abs(A)<min_area else (A-self.prev_area)/dt
            max_dA = 0.01
            dA = max(-max_dA, min(dA,max_dA))
            self.prev_area = A

            # centre de masse
            cm_x = sum(n.x for n in self.nodes)/3
            cm_y = sum(n.y for n in self.nodes)/3

            # vecteur "propulsion" : du centre vers le milieu des 2 nodes non central
            mid_x = (self.nodes[1].x + self.nodes[2].x)/2
            mid_y = (self.nodes[1].y + self.nodes[2].y)/2
            vec_x = mid_x - cm_x
            vec_y = mid_y - cm_y
            norm = math.sqrt(vec_x**2 + vec_y**2)
            if norm!=0:
                vec_x /= norm; vec_y /= norm
            else:
                vec_x, vec_y = 1.0, 0.0  # valeur par défaut

            # force fluide proportionnelle à dA, appliquée à tous les nodes
            k_fluid = 0.2
            fx = vec_x * k_fluid * dA
            fy = vec_y * k_fluid * dA
            for n in self.nodes:
                n.vx += fx
                n.vy += fy

            # --- INERTIE lissée sur dernière vitesse ---
            k_inertia = 0.1
            avg_vx = self.prev_velocity[0]
            avg_vy = self.prev_velocity[1]
            for n in self.nodes:
                n.vx += avg_vx * k_inertia
                n.vy += avg_vy * k_inertia

            # mise à jour de la vitesse moyenne pour prochaine frame
            vx_total = sum(n.vx for n in self.nodes)/len(self.nodes)
            vy_total = sum(n.vy for n in self.nodes)/len(self.nodes)
            self.prev_velocity = [vx_total, vy_total]

        # --- ANTI-COLLISION ---
        min_dist = 0.2
        for i in range(len(self.nodes)):
            for j in range(i+1,len(self.nodes)):
                n1,n2 = self.nodes[i], self.nodes[j]
                dx,dy = n2.x-n1.x, n2.y-n1.y
                dist = math.sqrt(dx*dx+dy*dy)
                if dist<min_dist and dist>0:
                    rep = 0.3*(min_dist-dist)
                    nx,ny = dx/dist, dy/dist
                    n1.vx -= nx*rep; n1.vy -= ny*rep
                    n2.vx += nx*rep; n2.vy += ny*rep

        # --- INTÉGRATION ---
        for n in self.nodes:
            n.x += n.vx
            n.y += n.vy
            n.vx *= DAMPING
            n.vy *= DAMPING

# --- SPAWN ---
def spawn():
    n0 = Node(0,0,0,0)
    n0.f_amplitude=0.003; n0.f_angle=math.pi/4; n0.f_period=10; n0.f_phase=0
    n1 = Node(0,1,0,0); n1.f_amplitude=0; n1.f_angle=math.pi/4; n1.f_period=5; n1.f_phase=0
    n2 = Node(1,0,0,0); n2.f_amplitude=0; n2.f_angle=3*math.pi/4; n2.f_period=5; n2.f_phase=0
    nodes=[n0,n1,n2]
    edges=[Edge(0,1), Edge(0,2)]
    return Creature(nodes,edges)

# --- MAIN ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH,HEIGHT))
    clock = pygame.time.Clock()
    creature = spawn()
    ox,oy = WIDTH//2, HEIGHT//2
    running=True
    while running:
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False
        dt=1/FPS
        creature.update(dt)

        screen.fill((5,10,20))
        draw_axes(screen,ox,oy)

        for m in creature.edges:
            n1,n2 = creature.nodes[m.n_a], creature.nodes[m.n_b]
            try:
                p1=(int(n1.x*ZOOM+ox), int(n1.y*ZOOM+oy))
                p2=(int(n2.x*ZOOM+ox), int(n2.y*ZOOM+oy))
                pygame.draw.line(screen,(80,150,255),p1,p2,5)
            except Exception as e:
                print("Drawing error:",e,n1.x,n1.y,n2.x,n2.y)

        for n in creature.nodes:
            try:
                px,py=int(n.x*ZOOM+ox),int(n.y*ZOOM+oy)
                pygame.draw.circle(screen,(255,255,255),(px,py),6)
            except:
                pass

        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__=="__main__":
    main()