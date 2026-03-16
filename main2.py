import pygame
import params
from creature import Node, Creature, Muscle
from utils import describe_creature, save_creature_to_csv
import random
import math


############################################
# SPAWN INITIAL DES CREATURES
############################################

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


############################################
# SELECTION STOCHASTIQUE (ROULETTE WHEEL)
############################################

def select_parent(population):
    """
    Sélection stochastique basée sur la fitness.

    Principe :
    Chaque créature possède une probabilité proportionnelle
    à sa fitness.

    P(i) = fitness_i / somme_des_fitness

    On simule cela avec une roulette :

    1) on calcule la somme des fitness
    2) on tire un nombre aléatoire entre 0 et cette somme
    3) on parcourt la population jusqu'à dépasser ce nombre
    """

    total_fitness = sum(c.fitness for c in population)

    # tirage aléatoire dans la roulette
    pick = random.uniform(0, total_fitness)

    current = 0

    for creature in population:

        current += creature.fitness

        if current >= pick:
            return creature

    return population[-1]


############################################
# CREATION DE LA NOUVELLE GENERATION
############################################

def evolve_population(population):

    new_population = []

    # ELITISM : on garde le meilleur individu
    population.sort(key=lambda c: c.fitness, reverse=True)

    elite = population[0]
    new_population.append(elite)

    for n in elite.nodes:
        n.reset()

    # création du reste de la population
    while len(new_population) < params.POPULATION_SIZE:

        parent = select_parent(population)

        child = parent.mutate()

        for n in child.nodes:
            n.reset()

        new_population.append(child)

    return new_population


############################################
# MAIN LOOP
############################################

def main():

    pygame.init()

    screen = pygame.display.set_mode(
        (params.WINDOW_WIDTH, params.WINDOW_HEIGHT)
    )

    clock = pygame.time.Clock()

    population = [spawn(i) for i in range(params.POPULATION_SIZE)]

    gen = 0
    timer = 0

    display_leader = population[0]

    while True:

        screen.fill(params.COLOR_BG)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                return

        ############################################
        # SIMULATION PHYSIQUE
        ############################################

        for c in population:
            c.update(timer)

        ############################################
        # AFFICHAGE DU LEADER
        ############################################

        zoom = 100
        ox = 400
        oy = 360

        for m in display_leader.muscles:

            n1 = display_leader.nodes[m.n_center]
            n2 = display_leader.nodes[m.n_target]

            pygame.draw.line(
                screen,
                params.COLOR_MUSCLE,
                (int(n1.x * zoom + ox), int(n1.y * zoom + oy)),
                (int(n2.x * zoom + ox), int(n2.y * zoom + oy)),
                8,
            )

        for n in display_leader.nodes:

            pygame.draw.circle(
                screen,
                params.COLOR_NODE,
                (int(n.x * zoom + ox), int(n.y * zoom + oy)),
                max(2, int(params.NODE_RADIUS * zoom)),
            )

        pygame.display.flip()
        clock.tick(params.FPS)

        timer += 1

        ############################################
        # FIN DE GENERATION
        ############################################

        if timer > params.GEN_DURATION:

            # calcul fitness
            for c in population:
                c.calculate_fitness()

            population.sort(key=lambda c: c.fitness, reverse=True)

            best_creature = population[0]

            print(f"\n{'='*40}")
            print(f"GENERATION {gen}")
            print(describe_creature(best_creature))
            print(f"{'='*40}\n")

            ############################################
            # SAUVEGARDE CSV
            ############################################

            for rank, creature in enumerate(population):

                save_creature_to_csv(
                    creature,
                    gen,
                    ranking=rank + 1
                )

            ############################################
            # EVOLUTION (SWISS CHEESE)
            ############################################

            population = evolve_population(population)

            display_leader = population[0]

            gen += 1
            timer = 0


if __name__ == "__main__":
    main()