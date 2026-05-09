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
# CROSSOVER ENTRE DEUX PARENTS
############################################


def crossover(p1, p2):
    """
    Combine les muscles des deux parents.
    """

    # On garde la structure de p1 (plus simple)
    new_nodes = [Node(n.initial_x, n.initial_y) for n in p1.nodes]

    new_muscles = []

    for m1, m2 in zip(p1.muscles, p2.muscles):

        if random.random() < 0.5:
            chosen = m1
        else:
            chosen = m2

        new_muscles.append(copy.deepcopy(chosen))

    return Creature(new_nodes, new_muscles, ancestor_id=p1.ancestor_id)


############################################
# SELECTION STOCHASTIQUE (ROULETTE WHEEL)
############################################

def roulette_selection(population, k=2):
    """
    Sélectionne k individus via roulette wheel
    avec pression de sélection.
    """

    # 🔥 C'EST ICI
    fitnesses = [math.pow(c.fitness, 1.5) for c in population]

    total = sum(fitnesses)

    if total == 0:
        return random.sample(population, k)

    rel_fitness = [f / total for f in fitnesses]

    probs = []
    cumulative = 0
    for rf in rel_fitness:
        cumulative += rf
        probs.append(cumulative)

    selected = []

    for _ in range(k):
        r = random.random()
        for i, individual in enumerate(population):
            if r <= probs[i]:
                selected.append(individual)
                break

    return selected


############################################
# CREATION DE LA NOUVELLE GENERATION
############################################

def evolve_population(population):

    population.sort(key=lambda c: c.fitness, reverse=True)

    new_population = []

    # ELITE
    elite = population[0]
    for n in elite.nodes:
        n.reset()
    new_population.append(elite)

    ########################################
    # MODE 1 : ENFANTS UNIQUEMENT
    ########################################
    if params.EVOLUTION_MODE == "children_only":

        while len(new_population) < params.POPULATION_SIZE:

            parent1, parent2 = roulette_selection(population, 2)
            child = crossover(parent1, parent2)
            child = child.mutate()

            for n in child.nodes:
                n.reset()

            new_population.append(child)

    ########################################
    # MODE 2 : PARENTS + ENFANTS
    ########################################
    elif params.EVOLUTION_MODE == "parents_plus_children":

        # garder top 20% parents
        survivors = population[:int(0.2 * len(population))]

        for s in survivors:
            for n in s.nodes:
                n.reset()

        new_population.extend(survivors)

        while len(new_population) < params.POPULATION_SIZE:

            parent1, parent2 = roulette_selection(population, 2)
            child = crossover(parent1, parent2)
            child = child.mutate()

            for n in child.nodes:
                n.reset()

            new_population.append(child)

    ########################################
    # MODE 3 : HYBRIDE (RECOMMANDÉ 🔥)
    ########################################
    elif params.EVOLUTION_MODE == "hybrid":

        # 10% élite
        elites = population[:int(0.1 * len(population))]
        for e in elites:
            for n in e.nodes:
                n.reset()

        new_population.extend(elites)

        while len(new_population) < params.POPULATION_SIZE:

            r = random.random()

            # 70% reproduction
            if r < 0.7:
                parent1, parent2 = roulette_selection(population, 2)
                child = crossover(parent1, parent2)
                child = child.mutate()

            # 20% mutation pure
            elif r < 0.9:
                parent = random.choice(population)
                child = parent.mutate()

            # 10% random spawn (exploration)
            else:
                child = spawn(random.randint(0, params.POPULATION_SIZE))

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