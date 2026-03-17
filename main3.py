import pygame
import params
import random
from creature3 import Node, Creature, Muscle
import math
# Paramètre de stabilité
SUB_STEPS = 30

# def spawn(index):
#     # num_nodes = random.randint(3, 5)
#     num_nodes = 3 # On fixe à 3 pour une structure simple (triangle)
#     nodes = [Node(0, 0)] # Le premier point est à l'origine
    
#     # On place les points suivants à 1m de distance
#     for i in range(1, num_nodes):
#         angle = random.uniform(0, 2 * math.pi)
#         prev_node = nodes[i-1]
#         # Nouveau point = ancien point + vecteur de 1.0m
#         new_x = prev_node.x + math.cos(angle)
#         new_y = prev_node.y + math.sin(angle)
#         nodes.append(Node(new_x, new_y))
    
#     muscles = []
#     # OS : On relie les points pour former la structure (chaîne)
#     for i in range(num_nodes - 1):
#         muscles.append(Muscle(i, i+1, nodes, is_bone=True))
        
#     # MUSCLE (Rouge) : On connecte deux points éloignés pour créer le mouvement
#     # Exemple : entre le premier et le dernier point
#     targets = [random.uniform(0.9, 1.1) for _ in range(5)]
#     muscles.append(Muscle(0, num_nodes-1, nodes, 
#                           clock_speed=random.uniform(0.01, 0.04), 
#                           targets=targets, is_bone=False))

#     return Creature(nodes, muscles, f"G0_{index}")
def spawn(index):
    # 1. On crée les points en chaîne (Os = 1.0m)
    num_nodes = 3
    nodes = [Node(0, 0)]
    for i in range(1, num_nodes):
        angle = random.uniform(0, 2 * math.pi)
        # On force la distance à 1.0 pour les OS
        new_x = nodes[i-1].x + math.cos(angle)
        new_y = nodes[i-1].y + math.sin(angle)
        nodes.append(Node(new_x, new_y))
    
    muscles = []
    # 2. On installe les OS (Rigides, base_len sera 1.0)
    for i in range(num_nodes - 1):
        muscles.append(Muscle(i, i+1, nodes, is_bone=True))
        
    # 3. On installe le MUSCLE (Souple, base_len sera calculée entre 0 et 2)
    # Ici, la base_len ne sera PAS forcément 1.0, elle dépend de l'angle !
    targets = [random.uniform(0.95, 1.05) for _ in range(5)]
    muscles.append(Muscle(0, num_nodes-1, nodes, 
                          clock_speed=random.uniform(0.01, 0.04), 
                          targets=targets, is_bone=False))

    return Creature(nodes, muscles, f"G0_{index}")

def main():
    pygame.init()
    screen = pygame.display.set_mode((params.WINDOW_WIDTH, params.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    
    population = [spawn(i) for i in range(params.POPULATION_SIZE)]
    gen, timer = 0, 0
    display_leader = population[0]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

# --- PHYSIQUE ---
        sub_step_dt = 1.0 / SUB_STEPS
        for _ in range(SUB_STEPS):
            for c in population:
                # On passe un timer qui avance par petites fractions
                c.update(timer, params.DAMPING)
            timer += sub_step_dt # On avance de 0.2 si SUB_STEPS = 5
    
        # --- RENDU ---
        screen.fill(params.COLOR_BG)
        zoom, ox, oy = 100, params.WINDOW_WIDTH // 2, params.WINDOW_HEIGHT // 2
        
        # Dessin du leader (meilleur de la gen précédente)
        for m in display_leader.muscles:
                    n1 = display_leader.nodes[m.n_a]
                    n2 = display_leader.nodes[m.n_b]
                    
                    p1 = (int(n1.x * zoom + ox), int(n1.y * zoom + oy))
                    p2 = (int(n2.x * zoom + ox), int(n2.y * zoom + oy))

                    if m.is_bone:
                        # OS : Couleur habituelle (bleu/blanc), trait épais
                        pygame.draw.line(screen, params.COLOR_MUSCLE, p1, p2, 6)
                    else:
                        # MUSCLE : Rouge, trait plus fin pour voir la tension
                        pygame.draw.line(screen, (255, 50, 50), p1, p2, 2)
        
        for n in display_leader.nodes:
            pygame.draw.circle(screen, params.COLOR_NODE, 
                               (int(n.x*zoom+ox), int(n.y*zoom+oy)), 5)

        pygame.display.flip()
        clock.tick(60)
        
        # --- ÉVOLUTION ---
        if timer > params.GEN_DURATION:
            for c in population: c.calculate_fitness()
            population.sort(key=lambda c: c.fitness, reverse=True)
            
            print(f"GEN {gen} | Meilleur Score: {population[0].fitness:.2f}")
            
            # Sélection (Top 50%)
            survivors = population[:params.POPULATION_SIZE // 2]
            new_gen = []
            for s in survivors:
                # On remet à zéro la position pour la nouvelle génération
                for n in s.nodes: n.reset()
                new_gen.append(s) # Le parent
                new_gen.append(s.mutate()) # L'enfant muté
            
            population = new_gen
            display_leader = population[0]
            gen += 1
            timer = 0

    pygame.quit()

if __name__ == "__main__":
    main()