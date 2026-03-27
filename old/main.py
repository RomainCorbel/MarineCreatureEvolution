import pygame
import params
from creature import Node, Creature, Muscle
from utils import describe_creature, save_creature_to_csv
import random
import math

def spawn(index):

    num_nodes = random.randint(2, 4)
    nodes = [Node(0, 0)]

    for i in range(1, num_nodes):

        angle = random.uniform(0, 2 * math.pi)
        dist = params.SEGMENT_LENGTH

        new_x = nodes[0].x + math.cos(angle) * dist
        new_y = nodes[0].y + math.sin(angle) * dist

        nodes.append(Node(new_x, new_y))

    muscles = []

    for i in range(1, num_nodes):

        target = random.randint(0, i - 1)

        muscles.append(
            Muscle(
                n_center=target,
                n_target=i,
                freq=random.uniform(0.1, 0.5),
                phase=random.uniform(0, 2 * math.pi),
                amplitude=random.uniform(0.3, 1.0),
            )
        )

    ancestor_label = f"{index+1}/{params.POPULATION_SIZE}"

    return Creature(nodes, muscles, ancestor_id=ancestor_label)

def main():
    pygame.init()
    screen = pygame.display.set_mode((params.WINDOW_WIDTH, params.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    
    # Population initiale
    population = [spawn(i) for i in range(params.POPULATION_SIZE)]
    gen, timer = 0, 0
    
    # On choisit arbitrairement le premier pour la Gen 0 TO DO: faire mieux que ça
    display_leader = population[0]

    while True: # un tourne sur le timer jusqu a depasser la durée de la génération, puis on évolue et on recommence
        screen.fill(params.COLOR_BG)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        # 1. CALCUL : Physique pour TOUTE la population
        for c in population: # pour chaque temps, on calcul pour outes les créatures de la generation.
            c.update(timer)
        
        # 2. RENDU : Affichage uniquement du leader
        zoom, ox, oy = 100, 400, 360
        for m in display_leader.muscles:
            n1, n2 = display_leader.nodes[m.n_center], display_leader.nodes[m.n_target]
            pygame.draw.line(screen, params.COLOR_MUSCLE, 
                             (int(n1.x * zoom + ox), int(n1.y * zoom + oy)), 
                             (int(n2.x * zoom + ox), int(n2.y * zoom + oy)), 8)
          
        for n in display_leader.nodes:
            pygame.draw.circle(screen, params.COLOR_NODE, 
                               (int(n.x * zoom + ox), int(n.y * zoom + oy)), 
                               max(2, int(params.NODE_RADIUS * zoom)))

        pygame.display.flip()
        clock.tick(60)
        
        timer += 1
        
        # 3. CHANGEMENT DE GÉNÉRATION
        if timer > params.GEN_DURATION:
            # On trie TOUTE la population par fitness
            for c in population:
                c.calculate_fitness()
            population.sort(key=lambda c: c.fitness, reverse=True)
            
            best_creature = population[0]
            print(f"\n{'='*30}")
            print(f"RÉSULTATS GÉNÉRATION {gen}")
            print(describe_creature(best_creature)) # Utilise ta fonction utils
            print(f"{'='*30}\n")

            # --- LA SAUVEGARDE CSV ---
            for rank, creature in enumerate(population):
                save_creature_to_csv(creature, gen, ranking=rank+1)

            # --- ÉVOLUTION ---
            survivors = population[:params.POPULATION_SIZE//2]
            new_gen = []
            for s in survivors:
                # On reset le parent
                for n in s.nodes: n.reset()
                s.energy_spent = 0 
                new_gen.append(s)
                
                # On crée l'enfant muté
                child = s.mutate()
                # On s'assure que l'enfant est aussi reset pour son premier test
                for n in child.nodes: n.reset()
                new_gen.append(child)
            
            # On met à jour la population et le champion d'affichage
            population = new_gen
            display_leader = population[0] # On affichera le champion au prochain tour
            gen += 1
            timer = 0

if __name__ == "__main__":
    main()