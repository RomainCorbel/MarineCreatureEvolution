import pygame
import math
### A chaque pas de temps, la créature peut maintenant toute seule appliquer des forces sur ces points. 
# En particulier, quand 2 points sont attachés aux même points, la créature doit avoir la possibilité de les serrer ensemble. Mais si on applique juste deux forces, il faut appliquer la première loi de newton 
# pour que la creature reste en place quand elle se contracte
# j ai aussi rajouté un quadrillage pour mieux visualiser les deplacements
# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
ZOOM = 100
RIGIDITY_BONE = 0.5
RIGIDITY_MUSCLE = 0.2
DAMPING = 0.99

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
    
    def update(self, frame_count= FPS):
            cycle_frame = frame_count % 120 
            
            # Le cosinus crée une oscillation fluide (0.3m à 1.0m)
            t = (math.cos(2 * math.pi * cycle_frame / 120) + 1) / 2
            
            for m in self.muscles:
                if not m.is_bone:
                    m.target_len = 0.3 + (1.0 - 0.3) * t

            # --- 2. PHYSIQUE (Newton : Action / Réaction) ---
            for m in self.muscles:
                n1, n2 = self.nodes[m.n_a], self.nodes[m.n_b]
                dx, dy = n2.x - n1.x, n2.y - n1.y
                dist = math.sqrt(dx**2 + dy**2) or 0.1
                
                # Calcul de l'écart élastique
                delta = (dist - m.target_len) / dist
                k = RIGIDITY_BONE if m.is_bone else RIGIDITY_MUSCLE
                
                # Force appliquée symétriquement
                fx, fy = dx * delta * k, dy * delta * k
                n1.vx += fx; n1.vy += fy
                n2.vx -= fx; n2.vy -= fy

            # --- 3. INTÉGRATION & DAMPING ---
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
    # 2 edges (os) de 1m + 1 muscle pour l'ouverture
    muscles = [
        Muscle(0, 1, is_bone=True),
        Muscle(0, 2, is_bone=True),
        Muscle(1, 2, is_bone=False),
    ]
    return Creature(nodes, muscles)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    creature = spawn()
    ox, oy = WIDTH // 2, HEIGHT // 2
    
    frame_count = 0 # <--- Compteur de frames pour le cycle de mouvement

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        # --- PHYSIQUE MANUELLE ---
        creature.update(frame_count) # <--- On passe le compteur
        frame_count += 1             # <--- On l'incrémente
        # --- RENDU ---
        screen.fill((5, 10, 20))
        for x in range(0, WIDTH, ZOOM):
            pygame.draw.line(screen, (255, 255, 255), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, ZOOM):
            pygame.draw.line(screen, (255, 255, 255), (0, y), (WIDTH, y))
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